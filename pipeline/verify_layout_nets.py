#!/usr/bin/env python3
"""CI gate: prove a board layout's drawn wiring is ELECTRICALLY EQUIVALENT to
the amp's verified netlist.

This is the check that upgrades a layout from a careful drawing to *provably
correct connectivity*. `check_layouts.py` proves a layout renders and reads
cleanly; this proves the wires actually go where the simulated circuit says
they do. No existing layout tool (DIYLC included) does this — a layout editor
knows nothing of the amp's netlist.

------------------------------------------------------------------------------
WHAT "electrically equivalent" means here
------------------------------------------------------------------------------
The netlist (`netlist.cir`) is a DC-operating-point model: it deliberately
omits DC-open and DC-transparent parts (coupling/bypass/tone/filter caps, grid
stoppers), the power-supply front end (PT + rectifier + reservoir, replaced by
an ideal source at B+1), and transformer winding DCR (plate node = B+). The
layout is the full physical board. So we cannot demand a naive 1:1 net match;
we build BOTH graphs and prove the layout, restricted to what the netlist
models, is *isomorphic* to the netlist — every modelled component's terminals
land on the same nodes, no accidental shorts, no missing joins — while every
part the netlist abstracts away is accounted for honestly (never silently).

The mapping is solved, not assumed:
  * tube socket pins ANCHOR nodes via basing (plate/grid/cathode/screen ->
    subckt pin order), with the section<->triode-half assignment SOLVED;
  * two-terminal parts have unknown a/b<->node orientation — resolved by
    CONSTRAINT PROPAGATION from the anchors to a globally consistent whole;
  * transformer leads, the speaker jack, and grid stoppers that the netlist
    abstracts are reconciled through an explicit, reviewable `net_map` block in
    layout.yaml (data, not code heuristics).

------------------------------------------------------------------------------
SCOPE (printed every run, honestly)
------------------------------------------------------------------------------
Heaters (twisted runs), the pilot lamp, the power-transformer HT/AC secondary,
and the rectifier are NOT in netlist.cir; they are an annotation layer, excluded
by EXPLICIT rules — never by widening an exclusion to bury a failure. The
checker prints how many runs it checked and how many it excluded and why, and
which netlist elements have no discrete board part (pots modelled as grid-leak
resistors, input grid leaks mounted at the jacks).

------------------------------------------------------------------------------
VERDICT + GATE
------------------------------------------------------------------------------
Per amp: PASS/FAIL with per-net diffs in builder language (extra connection /
missing connection / wrong terminal). An amp whose layout.yaml carries
`wiring_claim: verified` is HARD-GATED (a failure fails CI); an amp without the
claim is report-only. Mirrors the `verification.status: verified` netlist gate.

Run it (imports render_layouts, so pipeline/ must be on sys.path):
    python3 pipeline/render_layouts.py            # (re)generate SVGs first
    cd pipeline && python3 verify_layout_nets.py  # check all amps
    python3 verify_layout_nets.py --analyze 5e3   # dump graphs for one amp
    python3 verify_layout_nets.py --selftest      # planted-fault mutation test
"""
from __future__ import annotations

import copy
import math
import sys
from itertools import product
from pathlib import Path

import yaml

from render_layouts import (
    Renderer,
    load_bom,
    primary_value,
    tube_slug,
)

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
TUBES = ROOT / "reference" / "tubes"

# Tube elements that are never part of the DC signal netlist (heaters, dead
# pins). A signal pin is anything else (plate/grid/cathode/screen/anode).
_NONSIGNAL_ELEMENTS = {"heater", "heater-ct", "filament", "nc"}

# .subckt header pin-name -> canonical role. The netlist matches a tube pin to a
# subckt argument by POSITION; the header names tell us which role each position
# is, and basing tells us which physical pin carries that role.
_ROLE_OF_HEADER = {
    "P": "plate", "A": "plate", "PLATE": "plate", "ANODE": "plate",
    "G": "grid", "G1": "grid", "GRID": "grid",
    "G2": "screen", "SCREEN": "screen",
    "K": "cathode", "CATH": "cathode", "CATHODE": "cathode",
}
_ROLE_OF_ELEMENT = {
    "plate": "plate", "grid": "grid", "cathode": "cathode",
    "screen-grid": "screen", "screen": "screen",
    "diode-plate": "plate", "anode": "plate",
}


# ============================================================================
# union-find
# ============================================================================
class UF:
    def __init__(self):
        self.parent: dict = {}

    def add(self, x):
        self.parent.setdefault(x, x)

    def find(self, x):
        self.add(x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb
        return self.find(a)

    def members(self) -> dict:
        out: dict = {}
        for x in list(self.parent):
            out.setdefault(self.find(x), []).append(x)
        return out


# ============================================================================
# layout net graph (physical connectivity)
# ============================================================================
GND = "GND"


def _as_rc(pt):
    """A bare list endpoint is [row, col] (see render_layouts.resolve)."""
    return float(pt[0]), float(pt[1])


def _pt_seg_dist_rc(p, a, b):
    (pr, pc), (ar, ac), (br, bc) = p, a, b
    vr, vc = br - ar, bc - ac
    wr, wc = pr - ar, pc - ac
    denom = vr * vr + vc * vc
    t = 0.0 if denom < 1e-12 else max(0.0, min(1.0, (wr * vr + wc * vc) / denom))
    return math.hypot(pr - (ar + t * vr), pc - (ac + t * vc))


class LayoutGraph:
    """Union-find over physical terminals -> layout nets.

    Terminal identities mirror render_layouts.resolve() exactly:
      board part eyelet     REF.a / REF.b   (unioned to its eyelet node)
      off-board 2-lead part REF.a / REF.b   (kind: part)
      tube socket pin       V1.pin6
      pot lug               VR1.lug2
      jack                  JI / JI.tip / JI.sleeve
      transformer lead      T2.blue
      bare eyelet [r,c]     -> GND if on the ground bus, else eyelet node @r,c
    Joins: every run joins its two endpoints (vias are the same wire); the
    ground bus is one net; two leads in the same board eyelet are joined; a
    component's own two leads are never joined directly.
    """

    def __init__(self, R: Renderer):
        self.R = R
        self.uf = UF()
        self.errors: list[str] = []
        # eyelet coordinate -> which part leads land there (for share reporting)
        self.eyelet_leads: dict = {}
        self.bus_segs = self._bus_segments()
        self._build()

    # -- endpoint -> canonical terminal identity ----------------------------
    def _bus_segments(self):
        segs = []
        for spec in self.R.bus:
            a, b = spec.get("from"), spec.get("to")
            if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
                segs.append((_as_rc(a), _as_rc(b)))
        return segs

    def _on_bus(self, r, c):
        for a, b in self.bus_segs:
            if _pt_seg_dist_rc((r, c), a, b) < 0.25:
                return True
        return False

    def term(self, ep, ctx=""):
        """Canonical terminal id for a run/bus endpoint, or None on a bad ref
        (the error is also recorded; render_layouts would have failed first)."""
        R = self.R
        if isinstance(ep, (list, tuple)):
            if len(ep) != 2:
                self.errors.append(f"{ctx}: bad eyelet endpoint {ep!r}")
                return None
            r, c = _as_rc(ep)
            if self._on_bus(r, c):
                return GND
            return f"@{r:g},{c:g}"
        if not isinstance(ep, str):
            self.errors.append(f"{ctx}: bad endpoint {ep!r}")
            return None
        if "." not in ep:
            it = R.off_by_id.get(ep)
            if it is None:
                self.errors.append(f"{ctx}: unknown endpoint '{ep}'")
                return None
            return ep  # jack body / bare off-board id
        name, suffix = ep.split(".", 1)
        if name in R.part_by_ref:
            return f"{name}.{suffix}"  # board part eyelet
        it = R.off_by_id.get(name)
        if it is None:
            self.errors.append(f"{ctx}: unknown endpoint '{ep}'")
            return None
        return f"{name}.{suffix}"  # tube pin / pot lug / jack pin / xfmr lead / off-board part

    def _eyelet_node(self, r, c):
        return f"@{float(r):g},{float(c):g}"

    def _build(self):
        R = self.R
        # board parts: each lead joins its eyelet node (this realizes
        # eyelet-sharing: two leads in one eyelet share a net).
        for p in R.parts:
            ref = p.get("ref")
            if ref is None:
                continue
            for ab in ("a", "b"):
                if ab not in p:
                    continue
                r, c = _as_rc(p[ab])
                node = self._eyelet_node(r, c)
                self.uf.union(f"{ref}.{ab}", node)
                self.eyelet_leads.setdefault(node, []).append(f"{ref}.{ab}")
        # runs
        for i, spec in enumerate(R.runs):
            ta = self.term(spec.get("from"), f"run[{i}].from")
            tb = self.term(spec.get("to"), f"run[{i}].to")
            if ta is not None and tb is not None:
                self.uf.union(ta, tb)
        # (the ground bus is a single net rooted at GND; runs onto it were
        # already mapped to GND by term())

    # -- queries ------------------------------------------------------------
    def net(self, term):
        return self.uf.find(term)

    def nets(self) -> dict:
        return self.uf.members()


# ============================================================================
# netlist model
# ============================================================================
class Comp:
    __slots__ = ("ref", "kind", "nodes", "value", "subckt", "inst", "bottle",
                 "section", "roles")

    def __init__(self, ref, kind, nodes, value=None, subckt=None):
        self.ref = ref
        self.kind = kind          # 'R' | 'C' | 'L' | 'V' | 'I' | 'X'
        self.nodes = nodes        # ordered node names
        self.value = value
        self.subckt = subckt      # for X: subckt name
        self.inst = None          # for X: instance label without leading X (V1A)
        self.bottle = None        # for X: physical bottle (V1)
        self.section = None       # for X: 'A' | 'B' | None
        self.roles = {}           # for X: role -> node  (plate/grid/cathode/screen)


def _subckt_roles(name: str) -> list[str] | None:
    """Ordered roles for a subckt's pins, read from models/<name>.inc header."""
    path = MODELS / f"{name.lower()}.inc"
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        s = line.strip()
        if s.lower().startswith(".subckt"):
            toks = s.split()[1:]  # drop .subckt
            # toks[0] = subckt name, rest = pin names
            return [_ROLE_OF_HEADER.get(t.upper(), t.lower()) for t in toks[1:]]
    return None


def _split_inst(label: str):
    """XV1A -> bottle 'V1', section 'A'; XV2 -> 'V2', None; XV3 -> 'V3', None."""
    if label and label[-1] in ("A", "B", "C", "D") and label[:-1] and label[:-1][-1].isdigit():
        return label[:-1], label[-1]
    return label, None


def parse_netlist(path: Path) -> tuple[list[Comp], set]:
    comps: list[Comp] = []
    nodes: set = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line[0] in "*.":
            continue
        toks = line.split()
        head = toks[0]
        k = head[0].upper()
        if k in ("R", "C", "L"):
            if len(toks) < 4:
                continue
            n1, n2 = toks[1], toks[2]
            comps.append(Comp(head, k, [n1, n2], value=toks[3]))
            nodes.update((n1, n2))
        elif k in ("V", "I"):
            if len(toks) < 3:
                continue
            n1, n2 = toks[1], toks[2]
            comps.append(Comp(head, k, [n1, n2]))
            nodes.update((n1, n2))
        elif k == "X":
            sub = toks[-1]
            nds = toks[1:-1]
            c = Comp(head, "X", nds, subckt=sub)
            c.inst = head[1:]
            c.bottle, c.section = _split_inst(c.inst)
            roles = _subckt_roles(sub)
            if roles and len(roles) == len(nds):
                c.roles = {roles[i]: nds[i] for i in range(len(nds))}
            comps.append(c)
            nodes.update(nds)
    return comps, nodes


def load_basing(slug: str) -> dict | None:
    """pin(int) -> {'role': canonical, 'unit': int|None} for signal pins only."""
    path = TUBES / f"{slug}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    pins = ((data.get("basing") or {}).get("pins") or {})
    out: dict = {}
    for k, meta in pins.items():
        try:
            num = int(k)
        except (TypeError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        el = str(meta.get("element", "")).lower()
        if el in _NONSIGNAL_ELEMENTS:
            continue
        role = _ROLE_OF_ELEMENT.get(el)
        if role is None:
            continue
        out[num] = {"role": role, "unit": meta.get("unit")}
    return out or None


# ============================================================================
# analysis dump (--analyze)
# ============================================================================
def analyze(amp_id: str) -> int:
    amp_dir = ROOT / "amps" / amp_id
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    R = Renderer(layout, bom, amp_id)
    LG = LayoutGraph(R)

    print(f"=== {amp_id}: LAYOUT NET GRAPH ===")
    nets = LG.nets()
    # order nets by size desc for readability
    for root, members in sorted(nets.items(), key=lambda kv: -len(kv[1])):
        terms = sorted(m for m in members if not m.startswith("@"))
        eyelets = sorted(m for m in members if m.startswith("@"))
        if not terms and root == GND:
            terms = ["GND"]
        tag = "GND" if root == GND else ""
        print(f"  net{tag}: {terms}  eyelets={eyelets}")

    print(f"\n=== {amp_id}: SHARED EYELETS (>=2 part leads) ===")
    any_share = False
    for node, leads in sorted(LG.eyelet_leads.items()):
        if len(leads) >= 2:
            any_share = True
            print(f"  {node}: {leads}")
    if not any_share:
        print("  (none)")

    print(f"\n=== {amp_id}: NETLIST ===")
    comps, nodes = parse_netlist(amp_dir / "netlist.cir")
    print(f"  nodes: {sorted(nodes)}")
    for c in comps:
        if c.kind == "X":
            print(f"  {c.ref}: bottle={c.bottle} section={c.section} "
                  f"subckt={c.subckt} roles={c.roles}")
        else:
            print(f"  {c.ref} ({c.kind}): {c.nodes} {c.value or ''}")

    print(f"\n=== {amp_id}: TUBE BASING (signal pins) ===")
    for it in R.offboard:
        if it.get("kind") == "tube" and it.get("ref"):
            slug = tube_slug(primary_value(R.bom_for(it["ref"])["value"]))
            print(f"  {it['id']} ({slug}): {load_basing(slug)}")
    return 0


# ============================================================================
# equivalence solver + verdict
# ============================================================================
class Result:
    def __init__(self, amp_id):
        self.amp_id = amp_id
        self.claim = False
        self.ok = False
        self.errors: list[str] = []       # per-net diffs (builder language)
        self.scope: list[str] = []        # honest coverage lines
        self.info: list[str] = []         # declared reconciliations


def _invert_basing(basing: dict) -> dict:
    """pin->{role,unit}  ==>  (role, unit)->pin."""
    out = {}
    for pin, meta in basing.items():
        out[(meta["role"], meta["unit"])] = pin
    return out


def _part_terms(R: Renderer) -> dict:
    """ref -> (terminal_a, terminal_b) for every 2-lead part (board or off-board
    kind:part) — the parts a netlist R/C/L can be matched against."""
    terms = {}
    for ref in R.part_by_ref:
        terms[ref] = (f"{ref}.a", f"{ref}.b")
    for it in R.offboard:
        if it.get("kind") == "part" and "id" in it:
            terms[it["id"]] = (f"{it['id']}.a", f"{it['id']}.b")
    return terms


def _bottle_of(R: Renderer) -> dict:
    """netlist bottle id (V1/V2/...) -> reference/tubes slug, from the offboard
    tube of the same id."""
    out = {}
    for it in R.offboard:
        if it.get("kind") == "tube" and it.get("ref"):
            out[it["id"]] = tube_slug(primary_value(R.bom_for(it["ref"])["value"]))
    return out


def _apply_netmap_unions(LG: "LayoutGraph", uf: UF, net_map: dict, part_terms: dict):
    """Apply the reviewable net_map contractions to the layout graph:
      * series_bridge parts (DC-transparent grid stoppers) -> short their leads;
      * anchors that name the SAME netlist node -> a declared DC bridge, so the
        co-anchored terminals are one net (e.g. the OT primary DCR the netlist
        omits, or the OT-secondary DCR folded into ground).
    Ground ("0") is seeded with the bus sentinel so an anchor to ground (the
    speaker/NFB return) collapses onto the bus rather than reading as a split."""
    for ref in (net_map.get("series_bridge") or {}):
        if ref in part_terms:
            uf.union(*part_terms[ref])
    by_node: dict = {"0": [GND]}
    for term, node in (net_map.get("anchors") or {}).items():
        t = LG.term(term, f"net_map anchor {term}")
        if t is not None:
            by_node.setdefault(str(node), []).append(t)
    for _node, terms in by_node.items():
        for t in terms[1:]:
            uf.union(terms[0], t)


def _run_terminal_names(R: Renderer, spec) -> list[str]:
    """The raw endpoint strings of a run (for scope classification)."""
    out = []
    for key in ("from", "to"):
        ep = spec.get(key)
        if isinstance(ep, str):
            out.append(ep)
    return out


def check_amp(amp_id: str, verbose: bool = True) -> Result:
    amp_dir = ROOT / "amps" / amp_id
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    R = Renderer(layout, bom, amp_id)
    LG = LayoutGraph(R)
    uf = LG.uf
    comps, nodes = parse_netlist(amp_dir / "netlist.cir")
    res = Result(amp_id)
    res.claim = str(layout.get("wiring_claim", "")).lower() == "verified"

    net_map = layout.get("net_map") or {}
    unplaced = net_map.get("netlist_unplaced") or {}
    part_terms = _part_terms(R)
    bottle_slug = _bottle_of(R)

    # -- contractions declared in net_map (honest, reviewable) --------------
    _apply_netmap_unions(LG, uf, net_map, part_terms)

    # -- tube basing --------------------------------------------------------
    basing_inv = {}   # bottle -> (role,unit)->pin
    for bottle, slug in bottle_slug.items():
        b = load_basing(slug)
        if b:
            basing_inv[bottle] = _invert_basing(b)

    # section<->triode-half assignment is unknown; enumerate the small space.
    xcomps = [c for c in comps if c.kind == "X"]
    by_bottle: dict = {}
    for c in xcomps:
        by_bottle.setdefault(c.bottle, []).append(c)
    choices = []   # list of (bottle, [(section_comp, unit), ...]) option-lists
    for bottle, secs in by_bottle.items():
        if bottle not in basing_inv:
            continue  # rectifier / PS front-end tube, not modelled — skip
        units = sorted({u for (_r, u) in basing_inv[bottle] if u is not None})
        if len(secs) > 1 and units:
            secs_sorted = sorted(secs, key=lambda c: c.section or "")
            perms = []
            from itertools import permutations
            for perm in permutations(units, len(secs_sorted)):
                perms.append(list(zip(secs_sorted, perm)))
            choices.append((bottle, perms))
        else:
            choices.append((bottle, [[(s, None) for s in secs]]))

    option_lists = [opts for (_b, opts) in choices]
    best = None
    for combo in (product(*option_lists) if option_lists else [()]):
        assignment = {}
        for per_bottle in combo:
            for (sec, unit) in per_bottle:
                assignment[id(sec)] = unit
        trial = _solve(amp_id, layout, R, LG, uf, comps, nodes, net_map,
                       part_terms, basing_inv, assignment, unplaced)
        score = len(trial.errors)
        if best is None or score < best[0]:
            best = (score, trial)
        if score == 0:
            break
    res = best[1]
    res.ok = not res.errors
    if verbose:
        _print_result(res)
    return res


def _solve(amp_id, layout, R, LG, uf, comps, nodes, net_map, part_terms,
           basing_inv, assignment, unplaced) -> Result:
    res = Result(amp_id)
    res.claim = str(layout.get("wiring_claim", "")).lower() == "verified"
    anchors = net_map.get("anchors") or {}

    M: dict = {}                 # net root -> netlist node (first binding)
    cause: dict = {}             # net root -> readable cause of M[root]
    assigns: dict = {}           # net root -> {node: cause}  (for shorts)

    def assign(term, node, why):
        r = uf.find(term)
        assigns.setdefault(r, {}).setdefault(node, why)
        if r not in M:
            M[r] = node
            cause[r] = why

    # anchors: ground bus, net_map, tube pins
    assign(GND, "0", "ground bus")
    for term, node in anchors.items():
        t = LG.term(term, "net_map")
        if t is not None:
            assign(t, str(node), f"net_map anchor {term}")
    for c in comps:
        if c.kind != "X" or c.bottle not in basing_inv:
            continue
        unit = assignment.get(id(c))
        for role, node in c.roles.items():
            pin = basing_inv[c.bottle].get((role, unit))
            if pin is None:
                pin = basing_inv[c.bottle].get((role, None))
            if pin is None:
                continue
            assign(f"{c.bottle}.pin{pin}", node, f"{c.bottle}.pin{pin} ({role})")

    # constraint propagation across 2-terminal components present on the board
    two_term = [c for c in comps if c.kind in ("R", "C", "L") and c.ref in part_terms]
    changed = True
    while changed:
        changed = False
        for c in two_term:
            ta, tb = part_terms[c.ref]
            ra, rb = uf.find(ta), uf.find(tb)
            n1, n2 = c.nodes
            ma, mb = M.get(ra), M.get(rb)
            if ma is not None and mb is None:
                other = n2 if ma == n1 else (n1 if ma == n2 else None)
                if other is not None:
                    assign(tb, other, f"through {c.ref}")
                    changed = True
            elif mb is not None and ma is None:
                other = n2 if mb == n1 else (n1 if mb == n2 else None)
                if other is not None:
                    assign(ta, other, f"through {c.ref}")
                    changed = True

    node_name = _node_labeler(nodes)

    # ---- (1) shorts: a layout net carrying two different netlist nodes -----
    for r, nd in assigns.items():
        if len(nd) > 1:
            members = sorted(m for m in uf.members().get(r, []) if not m.startswith("@"))
            got = sorted(nd.keys())
            where = _describe_merge(LG, uf, r)
            res.errors.append(
                f"EXTRA CONNECTION: {' and '.join(node_name(n) for n in got)} are the "
                f"same net but the netlist keeps them apart{where}. "
                f"[{', '.join(f'{n}<-{nd[n]}' for n in got)}]")

    # ---- (2) wrong terminal: a modelled component lands on wrong nodes ------
    for c in comps:
        if c.kind not in ("R", "C", "L"):
            continue
        if c.ref not in part_terms:
            continue    # coverage handled below
        ta, tb = part_terms[c.ref]
        ra, rb = uf.find(ta), uf.find(tb)
        ma, mb = M.get(ra), M.get(rb)
        want = {c.nodes[0], c.nodes[1]}
        got = {ma, mb}
        if None in got:
            miss = ta if ma is None else tb
            res.errors.append(
                f"UNMAPPED: {c.ref} lead {miss} is not on any netlist node "
                f"(expected {node_name(c.nodes[0])}/{node_name(c.nodes[1])})")
        elif got != want:
            res.errors.append(
                f"WRONG TERMINAL: {c.ref} is wired {node_name(ma)}<->{node_name(mb)} "
                f"but the netlist has it {node_name(c.nodes[0])}<->{node_name(c.nodes[1])}")

    # ---- (3) tube pins on the wrong node -----------------------------------
    for c in comps:
        if c.kind != "X" or c.bottle not in basing_inv:
            continue
        unit = assignment.get(id(c))
        for role, node in c.roles.items():
            pin = basing_inv[c.bottle].get((role, unit)) or basing_inv[c.bottle].get((role, None))
            if pin is None:
                continue
            r = uf.find(f"{c.bottle}.pin{pin}")
            got = M.get(r)
            if got is not None and got != node:
                res.errors.append(
                    f"WRONG TERMINAL: {c.bottle}.pin{pin} ({c.inst} {role}) is on "
                    f"{node_name(got)} but the netlist puts it on {node_name(node)}")

    # ---- (4) missing connection: a node split across >1 layout net ----------
    node_roots: dict = {}
    for r, n in M.items():
        node_roots.setdefault(n, []).append(r)
    for n, roots in node_roots.items():
        if len(roots) > 1:
            groups = []
            for r in roots:
                mem = sorted(m for m in uf.members().get(r, []) if not m.startswith("@"))
                groups.append(mem)
            res.errors.append(
                f"MISSING CONNECTION: netlist node {node_name(n)} is realised as "
                f"{len(roots)} separate board nets that are never joined: "
                f"{' | '.join('{' + ', '.join(g) + '}' for g in groups)}")

    # ---- (5) coverage of netlist components --------------------------------
    modelled_refs = {c.ref for c in comps if c.kind in ("R", "C", "L")}
    for c in comps:
        if c.kind == "V":
            res.info.append(f"source {c.ref} ({node_name(c.nodes[0])}) — PS front end, "
                            f"not on the board (PT+rectifier+reservoir abstracted to an ideal rail)")
            continue
        if c.kind not in ("R", "C", "L"):
            continue
        if c.ref not in part_terms:
            if c.ref in unplaced:
                res.info.append(f"{c.ref} — {unplaced[c.ref]}")
            else:
                res.errors.append(
                    f"MISSING COMPONENT: netlist {c.ref} "
                    f"({node_name(c.nodes[0])}<->{node_name(c.nodes[1])}) has no board part "
                    f"and is not declared in net_map.netlist_unplaced")

    # ---- (6) honest scope report -------------------------------------------
    _scope_report(res, R, LG, uf, M, comps, basing_inv, part_terms, modelled_refs)
    return res


def _node_labeler(nodes):
    def name(n):
        return "ground" if n == "0" else n
    return name


def _describe_merge(LG, uf, root) -> str:
    """Point at the shared eyelet (if any) that fused two nodes into one net."""
    for node, leads in LG.eyelet_leads.items():
        if len(leads) >= 2 and uf.find(node) == root:
            return f" at board eyelet {node[1:]} ({' + '.join(leads)})"
    return ""


def _scope_report(res, R, LG, uf, M, comps, basing_inv, part_terms, modelled_refs):
    # runs: checked vs excluded (and why)
    rect_tubes = set()
    for it in R.offboard:
        if it.get("kind") == "tube" and it["id"] not in {c.bottle for c in comps if c.kind == "X" and c.bottle in basing_inv}:
            rect_tubes.add(it["id"])
    pilot_ids = {it["id"] for it in R.offboard if it.get("kind") == "part" and it.get("glyph") == "lamp"}
    pt_ids = {it["id"] for it in R.offboard if it.get("kind") in ("xfmr", "choke")}

    checked = 0
    excl = {"heater (twisted 6.3 V pair)": 0, "pilot lamp": 0,
            "power transformer / rectifier (AC + HT, abstracted to the rail)": 0,
            "out-of-DC-scope node (coupling-cap far side / speaker)": 0}
    for i, spec in enumerate(R.runs):
        if str(spec.get("style", "")).lower() == "twisted":
            excl["heater (twisted 6.3 V pair)"] += 1
            continue
        names = _run_terminal_names(R, spec)
        base_ids = {n.split(".")[0] for n in names}
        ta = LG.term(spec.get("from"), "")
        tb = LG.term(spec.get("to"), "")
        if base_ids & pilot_ids:
            excl["pilot lamp"] += 1
        elif base_ids & pt_ids and not _anchored_xfmr(spec, R):
            # a transformer run is in DC scope only when its lead(s) are named in
            # net_map anchors (e.g. the OT primary -> B+1); otherwise it is the
            # PT / rectifier AC + HT side, abstracted to the ideal rail.
            excl["power transformer / rectifier (AC + HT, abstracted to the rail)"] += 1
        elif base_ids & rect_tubes:
            excl["power transformer / rectifier (AC + HT, abstracted to the rail)"] += 1
        elif ta is not None and tb is not None and M.get(uf.find(ta)) is not None \
                and M.get(uf.find(tb)) is not None:
            checked += 1
        else:
            excl["out-of-DC-scope node (coupling-cap far side / speaker)"] += 1

    total = len(R.runs)
    res.scope.append(f"runs: {checked} checked against the netlist / "
                     f"{total - checked} excluded of {total} total")
    for k, v in excl.items():
        if v:
            res.scope.append(f"    excluded {v}: {k}")
    # netlist coverage
    n_mod = len([c for c in comps if c.kind in ('R', 'C', 'L')])
    n_matched = len([c for c in comps if c.kind in ('R', 'C', 'L') and c.ref in part_terms])
    n_tubes = len([c for c in comps if c.kind == "X" and c.bottle in basing_inv])
    res.scope.append(f"netlist: {n_matched}/{n_mod} R/C/L matched to board parts, "
                     f"{n_tubes} tube section(s) anchored by basing")
    # net_map reconciliations — the load-bearing, human-reviewable declarations
    # the gate was handed. Echo them at check-time so a reviewer reading CI logs
    # sees exactly what was anchored/bridged, never just a bare PASS.
    net_map = R.layout.get("net_map") or {}
    anchors = net_map.get("anchors") or {}
    bridges = net_map.get("series_bridge") or {}
    if anchors or bridges:
        res.scope.append(f"net_map: {len(anchors)} anchor(s) + {len(bridges)} "
                         f"series-bridge(s) applied (reviewable in layout.yaml):")
        for term, node in anchors.items():
            res.scope.append(f"    anchor  {term} := {'ground' if str(node) == '0' else node}")
        for ref in bridges:
            res.scope.append(f"    bridge  {ref} (DC-transparent part, leads shorted)")


def _anchored_xfmr(spec, R) -> bool:
    """True if every transformer-lead endpoint of this run is named in net_map
    anchors (so the run is in DC scope), else False."""
    net_map = (R.layout.get("net_map") or {})
    anchors = net_map.get("anchors") or {}
    for key in ("from", "to"):
        ep = spec.get(key)
        if isinstance(ep, str) and "." in ep:
            name = ep.split(".")[0]
            it = R.off_by_id.get(name)
            if it and it.get("kind") in ("xfmr", "choke") and ep not in anchors:
                return False
    return True


def _print_result(res: Result):
    tag = "claims wiring_claim: verified" if res.claim else "report-only (no wiring_claim)"
    head = "PASS" if res.ok else "FAIL"
    print(f"\n=== {res.amp_id}: {head} — {tag} ===")
    for s in res.scope:
        print(f"  scope | {s}")
    for s in res.info:
        print(f"  note  | {s}")
    if res.errors:
        for e in res.errors:
            print(f"  DIFF  | {e}")
    else:
        print("  layout wiring is electrically equivalent to the netlist "
              "(within the documented DC scope)")


# ============================================================================
# mutation self-test — a gate that can't catch planted faults is decoration
# ============================================================================
def selftest() -> int:
    """On a copy of 5f1's layout, assert the checker FAILS each planted fault:
    two endpoints swapped, a run deleted, a run rerouted to a wrong lug/pin."""
    base_dir = ROOT / "amps" / "5f1"
    layout0 = yaml.safe_load((base_dir / "layout.yaml").read_text())
    bom = load_bom(base_dir)

    baseline = _check_in_memory(layout0, bom)
    print("selftest baseline (unmutated 5f1):",
          "PASS" if baseline.ok else "FAIL " + str(baseline.errors))
    if not baseline.ok:
        print("  !! baseline must pass before mutations are meaningful")
        return 1

    cases = []

    # (a) two endpoints swapped: swap a real signal run's target to a sibling
    #     pin — V1B plate feed R7.a rerouted so plate load lands on the cathode.
    m1 = copy.deepcopy(layout0)
    for run in m1["runs"]:
        if run.get("from") == "V1.pin1" and run.get("to") == "R7.a":
            run["to"] = "R6.a"   # V1B plate -> cathode node instead of plate load
            break
    cases.append(("run rerouted to a wrong lug/pin (V1B plate -> cathode node)", m1))

    # (b) a run deleted: drop the 6V6 grid-leak-to-grid run.
    m2 = copy.deepcopy(layout0)
    m2["runs"] = [r for r in m2["runs"]
                  if not (r.get("from") == "R9.a" and r.get("to") == "V2.pin5")]
    cases.append(("a run deleted (6V6 grid leak R9 -> grid)", m2))

    # (c) two endpoints swapped: exchange the two 12AX7 triode-halves' cathode
    #     feeds (V1A<->V1B), so each cathode lands on the other's bias resistor.
    #     No triode-half relabelling can reconcile it (the plates/grids pin the
    #     halves), so it must be caught — unlike flipping a symmetric part's own
    #     two leads, which is a true electrical no-op.
    m3 = copy.deepcopy(layout0)
    for run in m3["runs"]:
        if run.get("from") == "V1.pin8" and run.get("to") == "R4.a":
            run["from"] = "V1.pin3"
        elif run.get("from") == "V1.pin3" and run.get("to") == "R6.a":
            run["from"] = "V1.pin8"
    cases.append(("two endpoints swapped (V1A/V1B cathode feeds exchanged)", m3))

    # (d) a run rerouted to an adjacent wrong pin: 6V6 cathode feed to pin7
    #     (a heater pin) instead of pin8 — lands the cathode on the wrong node.
    m4 = copy.deepcopy(layout0)
    for run in m4["runs"]:
        if run.get("from") == "V2.pin8" and run.get("to") == "R8.a":
            run["from"] = "V2.pin3"   # cathode feed moved to the plate pin
            break
    cases.append(("run rerouted to an adjacent wrong pin (6V6 cathode -> plate pin 3)", m4))

    passed = 0
    for label, mutant in cases:
        r = _check_in_memory(mutant, bom)
        caught = not r.ok
        print(f"  {'CAUGHT' if caught else 'MISSED'}: {label}")
        if caught and r.errors:
            print(f"           -> {r.errors[0]}")
        passed += 1 if caught else 0
    ok = passed == len(cases)
    print(f"\nselftest: {passed}/{len(cases)} planted faults caught"
          + ("" if ok else "  !! GATE IS LEAKY"))
    return 0 if ok else 1


def _check_in_memory(layout, bom) -> Result:
    """check_amp() equivalent that takes an in-memory layout (for the selftest);
    mirrors check_amp but skips disk reads and printing."""
    amp_id = "5f1"
    R = Renderer(copy.deepcopy(layout), bom, amp_id)
    LG = LayoutGraph(R)
    uf = LG.uf
    comps, nodes = parse_netlist((ROOT / "amps" / amp_id / "netlist.cir"))
    net_map = layout.get("net_map") or {}
    part_terms = _part_terms(R)
    bottle_slug = _bottle_of(R)
    _apply_netmap_unions(LG, uf, net_map, part_terms)
    basing_inv = {}
    for bottle, slug in bottle_slug.items():
        b = load_basing(slug)
        if b:
            basing_inv[bottle] = _invert_basing(b)
    xcomps = [c for c in comps if c.kind == "X"]
    by_bottle: dict = {}
    for c in xcomps:
        by_bottle.setdefault(c.bottle, []).append(c)
    from itertools import permutations
    option_lists = []
    for bottle, secs in by_bottle.items():
        if bottle not in basing_inv:
            continue
        units = sorted({u for (_r, u) in basing_inv[bottle] if u is not None})
        if len(secs) > 1 and units:
            secs_sorted = sorted(secs, key=lambda c: c.section or "")
            option_lists.append([list(zip(secs_sorted, p)) for p in permutations(units, len(secs_sorted))])
        else:
            option_lists.append([[(s, None) for s in secs]])
    best = None
    for combo in (product(*option_lists) if option_lists else [()]):
        assignment = {}
        for pb in combo:
            for (sec, unit) in pb:
                assignment[id(sec)] = unit
        trial = _solve(amp_id, layout, R, LG, uf, comps, nodes, net_map,
                       part_terms, basing_inv, assignment,
                       net_map.get("netlist_unplaced") or {})
        # NOTE: uf is mutated by _solve only via reads; safe across trials
        if best is None or len(trial.errors) < len(best.errors):
            best = trial
        if not trial.errors:
            break
    best.ok = not best.errors
    return best


# ============================================================================
# entry
# ============================================================================
def main(argv: list[str]) -> int:
    if argv and argv[0] == "--analyze":
        return analyze(argv[1])
    if argv and argv[0] == "--selftest":
        return selftest()
    only = None
    if argv and argv[0] == "--amp":
        only = argv[1]
    amp_dirs = sorted(d for d in (ROOT / "amps").iterdir()
                      if d.is_dir() and d.name != "_template"
                      and (d / "layout.yaml").exists()
                      and (d / "netlist.cir").exists())
    hard_fail = 0
    report_only_fail = 0
    checked = 0
    for d in amp_dirs:
        if only and d.name != only:
            continue
        res = check_amp(d.name, verbose=True)
        checked += 1
        if not res.ok:
            if res.claim:
                hard_fail += 1
            else:
                report_only_fail += 1
    print(f"\n{'=' * 70}")
    print(f"checked {checked} amp(s): {hard_fail} claiming wiring_claim:verified FAILED "
          f"(blocking), {report_only_fail} report-only with diffs")
    if hard_fail:
        print("BLOCKING: an amp claims its wiring is verified but it is not "
              "electrically equivalent to the netlist.")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
