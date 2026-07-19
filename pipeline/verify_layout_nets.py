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
checker prints how many runs it checked and how many it excluded and why; the
full tube accounting (every bottle anchored / rectifier excluded / UNANCHORED);
which netlist elements have no discrete board part (pots modelled as grid-leak
resistors, input grid leaks mounted at the jacks); and — loudly — the board
terminals inside the UNVERIFIED control-network island the netlist abstracts.

------------------------------------------------------------------------------
GATE HARDENING (2026-07-19) — closing the adversarial-audit escapes
------------------------------------------------------------------------------
An audit planted 26 faults; 12 escaped. Each escape is now closed at the level
that makes it impossible, not patched at the symptom:

  H1  valve-alias  a valve printed under its EU name ('ECC83 (12AX7)') resolves
      to its basing slug ('12ax7') via resolve_tube_slug (data-driven from every
      reference/tubes YAML's `also_known_as`). Basing-not-found for a tube on a
      claimed amp is a HARD FAILURE, never a silent skip.
  H2  anchoring    netlist bottles bind to sockets by id, else by unique tube
      TYPE (_resolve_bottles) — a function-named instance (XPIA) still anchors,
      so a naming convention can't defeat the check.
  H3  accounting   EVERY netlist tube is anchored / declared-excluded (rectifier)
      / UNANCHORED, and the tally prints regardless; UNANCHORED on a claimed amp
      fails CI.
  H4  island       the pot/mixer/tone control networks the netlist abstracts are
      declared terminal-by-terminal ("unverified island"), so a mis-lugged pot
      ground can't hide in silence.
  H5/H6  the DATA fix: netlist.cir now carries the signal-path parts it used to
      omit — PI-plate→output-grid coupling caps, output-tube grid leaks, grid
      stoppers — so the isomorphism check covers inter-stage routing and push-
      pull phase NATIVELY (a coupler on the wrong grid, or crossed PI outputs,
      is now a WRONG TERMINAL). DC-open caps / no-grid-current leaks don't move
      the op point (verified against voltages.yaml, not assumed).
  H7  twisted      a style:twisted (heater) run is validated to land on heater
      pins; a signal run relabelled 'twisted' to duck the check is a HARD FAILURE.
  H8  anchors      each net_map anchor is re-solved with it removed and labelled
      CONSTRAINING or REDUNDANT, so an inert anchor can't masquerade as support.

ROUND-2 RE-AUDIT CLOSURE (2026-07-19) — three further escapes:
  PP  phantom-pin  pin anchors/checks thread BOTTLE->SOCKET (_solve): a function-
      named bottle (PI) now anchors its real socket terminal (V3.pin6), not a
      phantom 'PI.pin6' that exists on no board net. Full-path selftest.
  EN  enumeration  EVERY terminal of EVERY non-modelled two-lead part and EVERY
      pot lug is enumerated (_enumerate_unchecked) with its net, tagged 'placement
      not DC-checked', REGARDLESS of net — so a mis-lugged pot ground or a bias
      resistor on a live rail can't hide by landing on a netlist-carrying net.
  SH  shrink       every DC-open cap with both leads on named DC nodes is now in
      netlist.cir (couplers + cathode-bypass, all 8 amps); op point unmoved.

------------------------------------------------------------------------------
VERDICT + GATE
------------------------------------------------------------------------------
Per amp: PASS/FAIL with per-net diffs in builder language (extra connection /
missing connection / wrong terminal / unanchored tube / twisted-on-signal-pin).
An amp whose layout.yaml carries `wiring_claim: verified` is HARD-GATED (a
failure fails CI); an amp without the claim is report-only. Mirrors the
`verification.status: verified` netlist gate.

Run it (imports render_layouts, so pipeline/ must be on sys.path):
    python3 pipeline/render_layouts.py            # (re)generate SVGs first
    cd pipeline && python3 verify_layout_nets.py  # check all amps
    python3 verify_layout_nets.py --analyze 5e3   # dump graphs + tube anchoring
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
    category,
    load_bom,
    load_tube_heater_pins,
    primary_value,
    resolve_tube_slug,
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
    """Split a netlist X-instance label into (bottle, section).

      XV1A -> ('V1', 'A');  XV2 -> ('V2', None);  XPIA -> ('PI', 'A')

    A trailing A/B/C/D is a triode-half SECTION only when it follows a
    multi-character stem (so a lone 'A'/'B' bottle isn't mangled). The stem no
    longer has to end in a digit — 'PIA'/'PIB' (a phase-inverter labelled by
    function, not socket number) must split to bottle 'PI' so the robust
    bottle->socket resolver can still anchor it (H2). Anchoring never relies on
    the bottle string alone: _resolve_bottles() cross-references by socket id and
    tube type, and an unresolved bottle on a claimed amp is a hard failure (H3),
    so a misleading label can neither defeat anchoring nor pass silently."""
    if (label and label[-1] in ("A", "B", "C", "D") and len(label) >= 3
            and not label[:-1].isdigit()):
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
            slug = resolve_tube_slug(primary_value(R.bom_for(it["ref"])["value"]))
            print(f"  {it['id']} ({slug}): {load_basing(slug)}")

    print(f"\n=== {amp_id}: TUBE ANCHORING (netlist bottle -> socket) ===")
    basing_inv, bottle_socket, unresolved, excluded_sockets, _sk = \
        _tube_anchoring(comps, R)
    for bottle, sid in sorted(bottle_socket.items()):
        print(f"  {bottle} -> socket {sid}  (anchored: {sorted(basing_inv.get(bottle, {}).values())} pins)")
    for sid, why in excluded_sockets:
        print(f"  socket {sid}: EXCLUDED — {why}")
    for bottle, why in unresolved:
        print(f"  {bottle}: UNRESOLVED — {why}")
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
        self.anchor_class: dict = {}      # net_map anchor -> CONSTRAINING|REDUNDANT (H8)


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


def _sockets(R: Renderer) -> dict:
    """socket id -> {slug, part, ref, value, heater_pins} for every off-board
    tube, using the EU/US-aware slug resolver (H1) so a valve printed under its
    European name ('ECC83 (12AX7)') still resolves to its basing ('12ax7')."""
    out = {}
    for it in R.offboard:
        if it.get("kind") == "tube" and it.get("ref"):
            rec = R.bom_for(it["ref"])
            val = primary_value(rec["value"])
            slug = resolve_tube_slug(val)
            out[it["id"]] = {
                "slug": slug,
                "part": str(rec.get("part", "")),
                "ref": it["ref"],
                "value": val,
                "heater_pins": load_tube_heater_pins(slug),
            }
    return out


def _resolve_bottles(comps, sockets: dict) -> tuple[dict, list, list]:
    """Map every netlist tube BOTTLE to a physical socket, robustly (H2/H3).

    Returns (bottle_socket, unresolved, excluded_sockets):
      bottle_socket    netlist-bottle -> socket-id
      unresolved       [(bottle, reason)] bottles that anchor to no socket
      excluded_sockets [(socket_id, reason)] tube sockets with NO netlist device
                       (rectifiers / PS front-end tubes abstracted to the rail)

    A netlist bottle binds to a socket by (1) exact id match — the socket basing
    is authoritative even when the SPICE model differs (a 6L6G socket runs the
    5881 model); (2) failing that, a unique unbound socket of the same tube TYPE,
    so a function-named instance (XPIA) still lands on its socket without relying
    on the label. Anything left over is UNRESOLVED — a hard failure on a claimed
    amp (never a silent skip). A non-rectifier socket with no netlist device is
    also unresolved coverage (a whole signal tube left unmodelled)."""
    xbottles: dict = {}
    for c in comps:
        if c.kind != "X":
            continue
        info = xbottles.setdefault(c.bottle, {"sections": set(), "slug": None})
        info["sections"].add(c.section)
        if info["slug"] is None:
            info["slug"] = resolve_tube_slug(c.subckt)
    bound_sockets: set = set()
    bottle_socket: dict = {}
    unresolved: list = []
    for bottle in xbottles:                       # pass 1: exact socket-id match
        if bottle in sockets:
            bottle_socket[bottle] = bottle
            bound_sockets.add(bottle)
    for bottle, info in xbottles.items():         # pass 2: unique type match
        if bottle in bottle_socket:
            continue
        cands = [sid for sid, meta in sockets.items()
                 if sid not in bound_sockets and meta["slug"] == info["slug"]]
        if len(cands) == 1:
            bottle_socket[bottle] = cands[0]
            bound_sockets.add(cands[0])
        elif not cands:
            unresolved.append((bottle,
                f"no socket id '{bottle}' and no unbound '{info['slug']}' socket "
                f"to cross-reference"))
        else:
            unresolved.append((bottle,
                f"ambiguous — {len(cands)} unbound '{info['slug']}' sockets "
                f"({', '.join(sorted(cands))}); label the instance with its socket id"))
    excluded_sockets: list = []
    for sid, meta in sockets.items():
        if sid in bound_sockets:
            continue
        if "rectifier" in meta["part"].lower():
            excluded_sockets.append((sid,
                f"{meta['value']} rectifier — not in the DC netlist "
                f"(PT+rectifier+reservoir abstracted to the ideal rail)"))
        else:
            unresolved.append((f"socket:{sid}",
                f"socket {sid} ({meta['value']}) carries no netlist device — a "
                f"signal tube left unmodelled"))
    return bottle_socket, unresolved, excluded_sockets


def _tube_anchoring(comps, R: Renderer):
    """Resolve every netlist tube to a socket + basing (H1/H2/H3). Returns
    (basing_inv, bottle_socket, unresolved, excluded_sockets, sockets), with
    basing_inv keyed by NETLIST BOTTLE: bottle -> (role,unit)->pin."""
    sockets = _sockets(R)
    bottle_socket, unresolved, excluded_sockets = _resolve_bottles(comps, sockets)
    basing_inv: dict = {}
    for bottle, sid in list(bottle_socket.items()):
        b = load_basing(sockets[sid]["slug"])
        if b:
            basing_inv[bottle] = _invert_basing(b)
        else:
            unresolved.append((bottle,
                f"socket {sid} tube '{sockets[sid]['slug']}' has no basing in "
                f"reference/tubes — cannot anchor"))
            del bottle_socket[bottle]
    return basing_inv, bottle_socket, unresolved, excluded_sockets, sockets


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


def _check_layout(amp_id: str, layout: dict, bom: dict, net_map=None,
                  netlist_path: "Path | None" = None) -> Result:
    """Solve one layout (in-memory) against its netlist and return the best
    Result. Shared by check_amp, the mutation self-test, and the H8 anchor
    classifier. `net_map` overrides layout['net_map'] when given (the classifier
    passes a copy with one anchor removed); `netlist_path` overrides the amp's
    netlist.cir (the phantom-pin self-test feeds a function-named-bottle variant
    to prove anchoring binds to the SOCKET, not the bottle label). A fresh
    Renderer/LayoutGraph/UF is built each call so union-find state never leaks
    between trials."""
    R = Renderer(copy.deepcopy(layout), bom, amp_id)
    LG = LayoutGraph(R)
    uf = LG.uf
    comps, nodes = parse_netlist(netlist_path or ROOT / "amps" / amp_id / "netlist.cir")
    if net_map is None:
        net_map = layout.get("net_map") or {}
    unplaced = net_map.get("netlist_unplaced") or {}
    part_terms = _part_terms(R)

    # -- contractions declared in net_map (honest, reviewable) --------------
    _apply_netmap_unions(LG, uf, net_map, part_terms)

    # -- tube anchoring: EU/US alias (H1) + robust bottle->socket (H2/H3) ----
    basing_inv, bottle_socket, unresolved, excluded_sockets, sockets = \
        _tube_anchoring(comps, R)
    anchoring = {"bottle_socket": bottle_socket, "unresolved": unresolved,
                 "excluded_sockets": excluded_sockets, "sockets": sockets,
                 "basing_inv": basing_inv}

    # section<->triode-half assignment is unknown; enumerate the small space.
    xcomps = [c for c in comps if c.kind == "X"]
    by_bottle: dict = {}
    for c in xcomps:
        by_bottle.setdefault(c.bottle, []).append(c)
    choices = []   # list of (bottle, [(section_comp, unit), ...]) option-lists
    for bottle, secs in by_bottle.items():
        if bottle not in basing_inv:
            continue  # unresolved tube — accounted as a hard failure in _solve
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
                       part_terms, basing_inv, assignment, unplaced, anchoring)
        score = len(trial.errors)
        if best is None or score < best[0]:
            best = (score, trial)
        if score == 0:
            break
    res = best[1]
    res.ok = not res.errors
    return res


def check_amp(amp_id: str, verbose: bool = True) -> Result:
    amp_dir = ROOT / "amps" / amp_id
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    res = _check_layout(amp_id, layout, bom)
    # H8: classify each net_map anchor CONSTRAINING vs REDUNDANT by re-solving
    # with it removed and asking whether the verdict changed.
    res.anchor_class = _classify_anchors(amp_id, layout, bom, res)
    if verbose:
        _print_result(res)
    return res


def _classify_anchors(amp_id: str, layout: dict, bom: dict, baseline: Result) -> dict:
    """For each net_map anchor: re-solve with it removed; CONSTRAINING if the
    error set changes, REDUNDANT if the verdict is identical without it (H8)."""
    net_map = layout.get("net_map") or {}
    anchors = net_map.get("anchors") or {}
    out: dict = {}
    base_errs = sorted(baseline.errors)
    for term in anchors:
        nm = copy.deepcopy(net_map)
        nm["anchors"] = {t: v for t, v in anchors.items() if t != term}
        trial = _check_layout(amp_id, layout, bom, net_map=nm)
        out[term] = "REDUNDANT" if sorted(trial.errors) == base_errs else "CONSTRAINING"
    return out


def _solve(amp_id, layout, R, LG, uf, comps, nodes, net_map, part_terms,
           basing_inv, assignment, unplaced, anchoring=None) -> Result:
    res = Result(amp_id)
    res.claim = str(layout.get("wiring_claim", "")).lower() == "verified"
    anchors = net_map.get("anchors") or {}
    # PHANTOM-PIN FIX: a netlist bottle carries a FUNCTION name (XPIA -> bottle
    # 'PI') that need not match its physical socket id; _resolve_bottles cross-
    # references it to the real socket (PI -> V3). The board's terminal identity
    # is the SOCKET pin ('V3.pin6'), never the bottle ('PI.pin6'), so every pin
    # anchor/check below must resolve bottle -> socket before forming the term,
    # or it silently anchors a phantom that doesn't exist on the board.
    bottle_socket = (anchoring or {}).get("bottle_socket", {})

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
        sid = bottle_socket.get(c.bottle, c.bottle)   # bottle -> physical socket
        for role, node in c.roles.items():
            pin = basing_inv[c.bottle].get((role, unit))
            if pin is None:
                pin = basing_inv[c.bottle].get((role, None))
            if pin is None:
                continue
            assign(f"{sid}.pin{pin}", node, f"{sid}.pin{pin} ({role})")

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
        sid = bottle_socket.get(c.bottle, c.bottle)   # bottle -> physical socket
        for role, node in c.roles.items():
            pin = basing_inv[c.bottle].get((role, unit)) or basing_inv[c.bottle].get((role, None))
            if pin is None:
                continue
            r = uf.find(f"{sid}.pin{pin}")
            got = M.get(r)
            if got is not None and got != node:
                res.errors.append(
                    f"WRONG TERMINAL: {sid}.pin{pin} ({c.inst} {role}) is on "
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

    # ---- (5b) EVERY netlist tube must anchor (H3) — never a silent skip -----
    anchoring = anchoring or {}
    for bottle, why in anchoring.get("unresolved", []):
        res.errors.append(
            f"UNANCHORED TUBE: {bottle} — {why}. A tube the netlist models must "
            f"anchor to a socket by basing, or the amp's wiring past it is unchecked.")

    # ---- (5c) twisted (heater) runs must land on heater pins (H7) -----------
    _check_twisted_heaters(res, R, anchoring.get("sockets", {}))

    # ---- (6) honest scope report -------------------------------------------
    _scope_report(res, R, LG, uf, M, comps, basing_inv, part_terms, modelled_refs,
                  anchoring)
    # ---- (7) declare the unverified control-network island (H4) ------------
    _declare_island(res, R, LG, uf, M, anchoring)
    # ---- (8) enumerate EVERY unchecked terminal — the completeness backstop
    #      that closes the two round-2 HIGH escapes (a non-modelled lead / pot
    #      lug landing on a netlist-carrying net was silently accepted). ------
    _enumerate_unchecked(res, R, uf, M, comps, part_terms, anchoring, node_name)
    return res


def _check_twisted_heaters(res, R, sockets: dict):
    """A style:twisted run is EXCLUDED from equivalence checking as a heater run;
    validate that self-declaration (H7) — every tube endpoint of a twisted run
    must be a heater/filament pin. A signal pin on a twisted run is a hard error
    (a signal run cannot be hidden from the gate by relabelling it 'twisted')."""
    for i, spec in enumerate(R.runs):
        if str(spec.get("style", "")).lower() != "twisted":
            continue
        for key in ("from", "to"):
            ep = spec.get(key)
            if not (isinstance(ep, str) and "." in ep):
                continue
            name, suffix = ep.split(".", 1)
            meta = sockets.get(name)
            if meta is None:
                continue                    # not a modelled tube socket
            digits = "".join(ch for ch in suffix if ch.isdigit())
            if not digits:
                continue
            pin = int(digits)
            heaters = meta.get("heater_pins")
            if heaters is not None and pin not in heaters:
                res.errors.append(
                    f"TWISTED RUN ON A SIGNAL PIN: run[{i}] is styled 'twisted' "
                    f"(excluded as a heater run) but lands on {name}.pin{pin}, "
                    f"which is not a heater pin ({sorted(heaters)} per basing). "
                    f"Relabelling a signal run 'twisted' cannot hide it from the gate.")


def _declare_island(res, R, LG, uf, M, anchoring=None):
    """H4 — name the board terminals electrically inside the UNVERIFIED control
    network (the pot / mixer / tone island the DC netlist abstracts). These are
    the nets carrying named terminals that anchor to NO netlist node and are not
    part of the heater / PT / rectifier / speaker annotation layer (already
    declared in the excluded-runs tally). Declared loudly, terminal-by-terminal,
    so the scope says exactly what is not machine-checked rather than staying
    silent — the silence is precisely what let a mis-lugged pot ground hide."""
    anchoring = anchoring or {}
    # annotation-layer base ids whose nets are declared elsewhere, not islands
    annot_ids = {it["id"] for it in R.offboard if it.get("kind") in ("xfmr", "choke")}
    annot_ids |= {it["id"] for it in R.offboard
                  if it.get("kind") == "part" and it.get("glyph") == "lamp"}
    annot_ids |= {it["id"] for it in R.offboard if it.get("kind") == "jack"
                  and it["id"].upper().startswith(("SPK", "SPEAK", "OUT"))}
    annot_ids |= {sid for sid, _why in anchoring.get("excluded_sockets", [])}
    twisted_roots: set = set()
    for spec in R.runs:
        if str(spec.get("style", "")).lower() == "twisted":
            for key in ("from", "to"):
                t = LG.term(spec.get(key), "")
                if t is not None:
                    twisted_roots.add(uf.find(t))
    # gather every net's members once, then classify per-net
    members = uf.members()
    islands: list = []
    for root, mem in members.items():
        if M.get(root) is not None:            # anchored to a netlist node
            continue
        if root in twisted_roots:              # heater annotation layer
            continue
        named = sorted(m for m in mem if not m.startswith("@") and m != GND)
        if not named:
            continue
        if any(m.split(".")[0] in annot_ids for m in named):   # PT/rect/speaker
            continue
        islands.append(named)
    if islands:
        n_terms = sum(len(g) for g in islands)
        res.scope.append(
            f"unverified island: {len(islands)} control-network net(s) "
            f"({n_terms} board terminals) carry no netlist node — the "
            f"pot/mixer/tone-stack wiring the DC netlist abstracts, NOT machine-checked:")
        for g in sorted(islands, key=lambda g: (-len(g), g)):
            res.scope.append(f"    island net: {{{', '.join(g)}}}")


_BOM_ROLE_CACHE: dict = {}


def _bom_roles(amp_id: str) -> dict:
    """ref -> role string, straight from bom.yaml (the role render's load_bom
    drops). Cached — used to classify a non-modelled part into an enumeration
    heading (a 'bias' role is the abstracted negative-supply front end)."""
    if amp_id not in _BOM_ROLE_CACHE:
        raw = yaml.safe_load((ROOT / "amps" / amp_id / "bom.yaml").read_text()) or {}
        _BOM_ROLE_CACHE[amp_id] = {
            it["ref"]: str(it.get("role", ""))
            for it in (raw.get("items") or [])
            if it.get("ref") and it["ref"] != "—"}
    return _BOM_ROLE_CACHE[amp_id]


# enumeration headings — every non-DC-checked terminal lands in exactly one
_UC_CTRL = "control networks (pots / mixers / tone-stack resistors)"
_UC_DCOPEN = "DC-open parts (coupling / bypass / tone / filter caps)"
_UC_BIAS = "abstracted bias supply (negative-grid front end: RB*/C15/D1 class)"
_UC_PTAC = "PT-AC / rectifier / pilot (annotation layer, abstracted to the rail)"
_UC_HEAT = "heaters (twisted 6.3 V pairs, annotation layer)"


def _enumerate_unchecked(res, R, uf, M, comps, part_terms, anchoring, node_name):
    """Close the two round-2 HIGH escapes. The unverified-island declaration only
    lists nets carrying NO netlist node, so a non-modelled part's lead — or a pot
    lug — landing on a net that ALREADY carries one (a rail, a cathode, ground)
    vanished into silence: a mis-lugged pot ground or a bias resistor dropped on a
    live rail simply did not appear. This enumerates EVERY terminal of EVERY non-
    modelled two-lead part and EVERY pot lug, tagged 'placement not DC-checked',
    with the net each sits on — REGARDLESS of that net — grouped under explicit
    headings. The DC netlist verifies only the modelled parts (whose placement IS
    checked terminal-for-terminal); everything here is drawn from the sources but
    not machine-checked, and is named so silence can never read as coverage."""
    anchoring = anchoring or {}
    modelled = {c.ref for c in comps if c.kind in ("R", "C", "L")}
    roles = _bom_roles(R.amp_id)
    members = uf.members()

    def netdesc(t):
        root = uf.find(t)
        node = M.get(root)
        if node is not None:
            return f"on the '{node_name(node)}' net [carries a netlist node]"
        mem = sorted(m for m in members.get(root, [])
                     if not m.startswith("@") and m != t and m != GND)
        if not mem:
            return "on an isolated net"
        head = ", ".join(mem[:3]) + ("…" if len(mem) > 3 else "")
        return f"on an unchecked island net {{{head}}}"

    def bucket(cat, role):
        if "bias" in (role or "").lower():
            return _UC_BIAS
        if cat in ("electro", "film", "mica"):
            return _UC_DCOPEN
        return _UC_CTRL                       # resistors / diodes / misc controls

    groups: dict = {h: [] for h in (_UC_CTRL, _UC_DCOPEN, _UC_BIAS, _UC_PTAC, _UC_HEAT)}
    n_terms = 0
    seen: set = set()

    def add_two_lead(ref, off_board):
        nonlocal n_terms
        if ref in modelled or ref in seen:
            return
        seen.add(ref)
        it = R.off_by_id.get(ref) if off_board else None
        role = roles.get(ref, "")
        cat = category((R.bom.get(ref) or {}).get("part", ""))   # no error pollution
        ta, tb = part_terms.get(ref, (f"{ref}.a", f"{ref}.b"))
        if it is not None and it.get("glyph") == "lamp":
            groups[_UC_PTAC].append(f"{ref} (pilot lamp): a {netdesc(ta)}; b {netdesc(tb)}")
            n_terms += 2
            return
        tag = f"{ref} ({role or cat}{', off-board' if off_board else ''})"
        groups[bucket(cat, role)].append(f"{tag}: a {netdesc(ta)}; b {netdesc(tb)}")
        n_terms += 2

    for p in R.parts:
        if p.get("ref"):
            add_two_lead(p["ref"], off_board=False)
    for it in R.offboard:
        if it.get("kind") == "part":
            add_two_lead(it["id"], off_board=True)

    # every pot lug — pots are NEVER discrete netlist devices, so all three lugs
    # are unchecked regardless of what each lands on (this is where the mis-lugged
    # ground used to hide).
    for it in R.offboard:
        if it.get("kind") != "pot":
            continue
        pid = it["id"]
        lugs = "; ".join(f"lug{n} {netdesc(f'{pid}.lug{n}')}" for n in (1, 2, 3))
        groups[_UC_CTRL].append(f"{pid} ({it.get('label', pid)} pot): {lugs}")
        n_terms += 3

    # annotation-layer runs, counted (their nets are the excluded run tally): the
    # PT/rectifier AC+HT side and the twisted heater pairs.
    n_twist = sum(1 for s in R.runs if str(s.get("style", "")).lower() == "twisted")
    if n_twist:
        groups[_UC_HEAT].append(
            f"{n_twist} twisted heater run(s) — validated onto heater/filament "
            f"pins (H7), excluded from DC equivalence")
    pt_ids = sorted(it["id"] for it in R.offboard if it.get("kind") in ("xfmr", "choke"))
    rect_ids = sorted(sid for sid, _why in anchoring.get("excluded_sockets", []))
    if pt_ids or rect_ids:
        bits = []
        if pt_ids:
            bits.append("transformer/choke " + ", ".join(pt_ids))
        if rect_ids:
            bits.append("rectifier socket " + ", ".join(rect_ids))
        groups[_UC_PTAC].append("; ".join(bits) + " — AC/HT side abstracted to the ideal rail")

    res.scope.append(
        f"unchecked terminals — placement NOT DC-checked, enumerated so silence "
        f"never reads as coverage ({n_terms} terminal(s); the netlist verifies "
        f"only the modelled parts, terminal-for-terminal):")
    for head in (_UC_CTRL, _UC_DCOPEN, _UC_BIAS, _UC_PTAC, _UC_HEAT):
        if not groups[head]:
            continue
        res.scope.append(f"    {head}:")
        for line in sorted(groups[head]):
            res.scope.append(f"        {line}")


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


def _scope_report(res, R, LG, uf, M, comps, basing_inv, part_terms, modelled_refs,
                  anchoring=None):
    anchoring = anchoring or {}
    bottle_socket = anchoring.get("bottle_socket", {})
    excluded_sockets = anchoring.get("excluded_sockets", [])
    unresolved = anchoring.get("unresolved", [])
    # runs: checked vs excluded (and why). A "rect tube" for run-exclusion is any
    # off-board tube socket NOT bound to a netlist device (rectifier / abstracted).
    bound_socket_ids = set(bottle_socket.values())
    rect_tubes = {it["id"] for it in R.offboard
                  if it.get("kind") == "tube" and it["id"] not in bound_socket_ids}
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
    # tube accounting (H3): every netlist device is anchored, and every socket is
    # anchored / declared-excluded (rectifier) / UNANCHORED — printed regardless.
    n_bottles = len(bottle_socket)
    n_excl = len(excluded_sockets)
    n_unres = len(unresolved)
    res.scope.append(f"tubes: {n_bottles} netlist bottle(s) anchored to sockets, "
                     f"{n_excl} socket(s) declared-excluded, {n_unres} UNANCHORED")
    for bottle, sid in sorted(bottle_socket.items()):
        via = "id" if bottle == sid else "type x-ref"
        res.scope.append(f"    anchored  {bottle} -> socket {sid} (by {via})")
    for sid, why in excluded_sockets:
        res.scope.append(f"    excluded  socket {sid}: {why}")
    for bottle, why in unresolved:
        res.scope.append(f"    UNANCHORED {bottle}: {why}")
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
        extra = ""
        # H8: annotate each net_map anchor CONSTRAINING vs REDUNDANT (does the
        # verdict change with it removed?) so a reviewer sees which anchors
        # actually hold the verdict up and which are echoed but inert.
        if s.lstrip().startswith("anchor  ") and res.anchor_class:
            term = s.split("anchor  ", 1)[1].split(" :=", 1)[0].strip()
            if term in res.anchor_class:
                extra = f"  [{res.anchor_class[term]}]"
        print(f"  scope | {s}{extra}")
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
def _load_layout(amp_id: str):
    d = ROOT / "amps" / amp_id
    return yaml.safe_load((d / "layout.yaml").read_text()), load_bom(d)


def _reroute(layout: dict, frm, to, new_from=None, new_to=None):
    """Deep-copy `layout` and rewrite the first run matching (frm -> to)."""
    m = copy.deepcopy(layout)
    for run in m.get("runs", []):
        if run.get("from") == frm and run.get("to") == to:
            if new_from is not None:
                run["from"] = new_from
            if new_to is not None:
                run["to"] = new_to
            break
    return m


def selftest() -> int:
    """A gate that can't catch planted faults is decoration. This plants the
    adversarial audit's EXACT faults — one per proven hole class (H1..H8) — and
    asserts each is caught (or, for the naming/anchoring holes, that the robust
    resolver anchors what a misleading label used to hide). CI runs it."""
    fails: list[str] = []
    print("=== baselines (must PASS before mutations mean anything) ===")
    for amp in ("5f1", "5f6a", "jtm45", "5f4"):
        layout, bom = _load_layout(amp)
        r = _check_layout(amp, layout, bom)
        print(f"  {amp}: {'PASS' if r.ok else 'FAIL ' + str(r.errors[:2])}")
        if not r.ok:
            fails.append(f"baseline {amp} must pass")
    if fails:
        for f in fails:
            print(f"  !! {f}")
        return 1

    l5f1, b5f1 = _load_layout("5f1")
    l6a, b6a = _load_layout("5f6a")
    ljtm, bjtm = _load_layout("jtm45")

    caught_cases: list[tuple[str, str, Result]] = []   # (hole, label, result)

    def case(hole, label, amp, layout, bom):
        r = _check_layout(amp, layout, bom)
        caught_cases.append((hole, label, r))

    # ---- original topological faults (kept) -------------------------------
    case("core", "run rerouted to a wrong pin (V1B plate -> cathode node)", "5f1",
         _reroute(l5f1, "V1.pin1", "R7.a", new_to="R6.a"), b5f1)
    m = copy.deepcopy(l5f1)
    m["runs"] = [r for r in m["runs"]
                 if not (r.get("from") == "R9.a" and r.get("to") == "V2.pin5")]
    case("core", "a run deleted (6V6 grid leak R9 -> grid)", "5f1", m, b5f1)
    m = copy.deepcopy(l5f1)
    for run in m["runs"]:
        if run.get("from") == "V1.pin8" and run.get("to") == "R4.a":
            run["from"] = "V1.pin3"
        elif run.get("from") == "V1.pin3" and run.get("to") == "R6.a":
            run["from"] = "V1.pin8"
    case("core", "two endpoints swapped (V1A/V1B cathode feeds exchanged)", "5f1", m, b5f1)

    # ---- H1 valve-alias: an ECC83 socket now anchors, so a wrong-pin on it is
    #      caught (before the alias fix, jtm45's whole ECC83 preamp/PI was
    #      silently skipped and this landed nowhere). --------------------------
    case("H1", "ECC83 (aliased) plate load moved plate->cathode pin", "jtm45",
         _reroute(ljtm, "V1.pin6", "RL1.b", new_from="V1.pin8"), bjtm)

    # ---- H5 coupler to the WRONG output grid (now modelled as C8/C9) --------
    case("H5", "PI->output coupler C8 rerouted to the V5 grid", "5f6a",
         _reroute(l6a, "C8.b", "V4.pin5", new_to="V5.pin5"), b6a)

    # ---- H6 crossed PI outputs (swap the two PI-plate coupler feeds) --------
    m = copy.deepcopy(l6a)
    for run in m["runs"]:
        if run.get("from") == "V3.pin1" and run.get("to") == "C8.a":
            run["to"] = "C9.a"
        elif run.get("from") == "V3.pin6" and run.get("to") == "C9.a":
            run["to"] = "C8.a"
    case("H6", "crossed PI outputs (C8/C9 plate feeds swapped)", "5f6a", m, b6a)

    # ---- H7 a signal run relabelled style:twisted (would remove it from the
    #      equivalence check as a 'heater' run) — must land on heater pins ----
    m = copy.deepcopy(l5f1)
    for run in m["runs"]:
        if run.get("from") == "R9.a" and run.get("to") == "V2.pin5":
            run["style"] = "twisted"      # V2.pin5 is a 6V6 grid, not a heater pin
            break
    case("H7", "signal run relabelled 'twisted' (6V6 grid, not a heater pin)", "5f1", m, b5f1)

    passed = 0
    for hole, label, r in caught_cases:
        caught = not r.ok
        print(f"  [{hole}] {'CAUGHT' if caught else 'MISSED'}: {label}")
        if caught and r.errors:
            print(f"          -> {r.errors[0]}")
        passed += 1 if caught else 0
    n_mut = len(caught_cases)
    ok_mut = passed == n_mut

    # ---- H2/H3 robust anchoring: exercise the resolver directly ------------
    print("=== H2/H3 bottle->socket resolver ===")
    def _fakecomp(bottle, section, subckt):
        c = Comp(f"X{bottle}{section or ''}", "X", [], subckt=subckt)
        c.bottle, c.section = bottle, section
        return c
    def _fakesock(slug, part="Preamp tube", value=None):
        return {"slug": slug, "part": part, "ref": "?", "value": value or slug,
                "heater_pins": load_tube_heater_pins(slug)}
    # a function-named PI ('PI' from XPIA/XPIB) must still anchor to socket V3 by
    # type cross-reference, though its label matches no socket id (H2).
    comps_h2 = [_fakecomp("V1", "A", "12AY7"), _fakecomp("V1", "B", "12AY7"),
                _fakecomp("V2", "A", "12AX7"), _fakecomp("V2", "B", "12AX7"),
                _fakecomp("PI", "A", "12AX7"), _fakecomp("PI", "B", "12AX7")]
    socks_h2 = {"V1": _fakesock("12ay7"), "V2": _fakesock("12ax7"),
                "V3": _fakesock("12ax7"), "V6": _fakesock("gz34", "Rectifier tube")}
    bs, unres, excl = _resolve_bottles(comps_h2, socks_h2)
    h2_ok = bs.get("PI") == "V3" and not unres
    print(f"  [H2] function-named 'PI' -> socket {bs.get('PI')} "
          f"(cross-referenced by type): {'OK' if h2_ok else 'FAIL'}")
    h2b_ok = any(sid == "V6" for sid, _ in excl)
    print(f"  [H2] rectifier socket V6 declared-excluded: {'OK' if h2b_ok else 'FAIL'}")
    # an unanchorable bottle (no socket id, no type match) must be UNRESOLVED,
    # never silently skipped (H3).
    comps_h3 = [_fakecomp("VX", None, "EL34")]
    socks_h3 = {"V1": _fakesock("12ax7")}
    _bs3, unres3, _e3 = _resolve_bottles(comps_h3, socks_h3)
    h3_ok = any(b == "VX" for b, _ in unres3)
    print(f"  [H3] unanchorable EL34 bottle 'VX' -> UNRESOLVED: {'OK' if h3_ok else 'FAIL'}")
    # and a non-rectifier socket with no netlist device is a hard coverage hole
    _bs3b, unres3b, _e3b = _resolve_bottles([_fakecomp("V1", None, "12AX7")],
                                            {"V1": _fakesock("12ax7"),
                                             "V2": _fakesock("6v6gt", "Power tube")})
    h3b_ok = any(b == "socket:V2" for b, _ in unres3b)
    print(f"  [H3] unmodelled signal socket V2 -> UNRESOLVED: {'OK' if h3b_ok else 'FAIL'}")

    # ---- PHANTOM-PIN full path: a FUNCTION-named bottle must anchor to the
    #      physical SOCKET, not to a 'bottle.pin' terminal that isn't on the
    #      board. Rename 5f1's XV1A/XV1B to XPREA/XPREB — bottle 'PRE' matches no
    #      socket id, so it resolves to the unique 12AX7 socket V1 by type x-ref
    #      (H2). The board's terminals are 'V1.pinN'. Before the fix the solver
    #      anchored 'PRE.pinN' (a phantom that exists on no net), which (a) split
    #      every V1 node between the phantom and the real pin — so the CORRECT
    #      wiring failed spuriously — and (b) left V1's real pins unchecked, so a
    #      broken V1 wire escaped. The fix threads bottle->socket, so correct
    #      wiring PASSES and a broken V1 pin is caught ON THE REAL SOCKET. ------
    print("=== phantom-pin: function-named bottle anchors to the real socket ===")
    import os
    import tempfile
    fn_src = ((ROOT / "amps" / "5f1" / "netlist.cir").read_text()
              .replace("XV1A", "XPREA").replace("XV1B", "XPREB"))
    _fh = tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False)
    _fh.write(fn_src)
    _fh.close()
    fn_path = Path(_fh.name)
    try:
        r_fn_ok = _check_layout("5f1", l5f1, b5f1, netlist_path=fn_path)
        # break V1B plate (pin 1): reroute its plate-load feed onto the cathode
        r_fn_break = _check_layout("5f1", _reroute(l5f1, "V1.pin1", "R7.a",
                                                   new_to="R6.a"),
                                   b5f1, netlist_path=fn_path)
    finally:
        os.unlink(fn_path)
    pp_base_ok = r_fn_ok.ok
    pp_break_caught = (not r_fn_break.ok) and any("V1.pin" in e for e in r_fn_break.errors)
    print(f"  [PP] function-named 'PRE' anchors socket V1; correct wiring PASSES: "
          f"{'OK' if pp_base_ok else 'FAIL ' + str(r_fn_ok.errors[:2])}")
    print(f"  [PP] broken V1 pin on the function-named bottle is CAUGHT on the "
          f"real socket: {'OK' if pp_break_caught else 'FAIL'}")
    if pp_break_caught:
        print(f"          -> {next(e for e in r_fn_break.errors if 'V1.pin' in e)}")

    # ---- H4 the unverified control-network island is declared (not silent) --
    print("=== H4 unverified-island declaration ===")
    r6a = _check_layout("5f6a", l6a, b6a)
    island_lines = [s for s in r6a.scope if "island net:" in s]
    island_blob = " ".join(island_lines)
    h4_ok = bool(island_lines) and ("VR" in island_blob or "RM" in island_blob)
    print(f"  [H4] 5f6a island declares {len(island_lines)} control net(s) "
          f"incl. pot/mixer terminals: {'OK' if h4_ok else 'FAIL'}")

    # ---- H8 anchors classified CONSTRAINING vs REDUNDANT -------------------
    print("=== H8 anchor CONSTRAINING/REDUNDANT classification ===")
    cls = _classify_anchors("5f6a", l6a, b6a, r6a)
    # a deliberately redundant anchor (a filter-cap lead to the node it already
    # sits on) must read REDUNDANT; a real OT-plate anchor must read CONSTRAINING.
    l6a_red = copy.deepcopy(l6a)
    l6a_red.setdefault("net_map", {}).setdefault("anchors", {})["C11.a"] = "BP1"
    r6a_red = _check_layout("5f6a", l6a_red, b6a)
    cls_red = _classify_anchors("5f6a", l6a_red, b6a, r6a_red)
    h8_red_ok = cls_red.get("C11.a") == "REDUNDANT"
    h8_con_ok = cls.get("T3.blue") == "CONSTRAINING"
    print(f"  [H8] injected redundant anchor C11.a:=BP1 -> {cls_red.get('C11.a')} "
          f"({'OK' if h8_red_ok else 'FAIL'})")
    print(f"  [H8] OT-plate anchor T3.blue:=BP1 -> {cls.get('T3.blue')} "
          f"({'OK' if h8_con_ok else 'FAIL'})")

    # ---- enumeration backstop: silent mis-placements must SURFACE ----------
    #      A mis-lugged pot ground and a bias resistor dropped on a live rail are
    #      NON-modelled placements: they split no netlist node, so the equivalence
    #      check cannot (and should not) raise a DIFF. They must instead appear in
    #      the enumerated unchecked-terminal report — the fix for the two round-2
    #      HIGHs, where such leads landing on a netlist-carrying net were silent.
    print("=== enumeration surfaces silent mis-placements (pot ground / bias rail) ===")
    # (1) mis-lug the Middle-pot ground (VR5.lug1) off the ground bus onto the B+1
    #     rail (C11.a). No netlist node is split -> no DIFF -> must show as VR5 on 'BP1'.
    l_poterr = copy.deepcopy(l6a)
    for run in l_poterr["runs"]:
        if run.get("from") == "VR5.lug1" and isinstance(run.get("to"), list):
            run["to"] = "C11.a"
            break
    r_poterr = _check_layout("5f6a", l_poterr, b6a)
    pot_surfaced = any("VR5" in s and "BP1" in s for s in r_poterr.scope)
    print(f"  [ENUM] mis-lugged Middle-pot ground -> report shows VR5 on 'BP1': "
          f"{'OK' if pot_surfaced else 'FAIL'}"
          + ("" if r_poterr.ok else "  (+ raised a DIFF)"))
    # (2) drop the bias series resistor RB1's input lead from the PT bias tap onto
    #     the B+1 rail (C11.a). RB1 is unmodelled -> no DIFF -> must show as RB1 on 'BP1'.
    l_biaserr = copy.deepcopy(l6a)
    for run in l_biaserr["runs"]:
        if run.get("from") == "PT.red-blue" and run.get("to") == "RB1.a":
            run["from"] = "C11.a"
            break
    r_biaserr = _check_layout("5f6a", l_biaserr, b6a)
    bias_surfaced = any("RB1" in s and "BP1" in s for s in r_biaserr.scope)
    print(f"  [ENUM] bias resistor RB1 dropped on the B+1 rail -> report shows "
          f"RB1 on 'BP1': {'OK' if bias_surfaced else 'FAIL'}"
          + ("" if r_biaserr.ok else "  (+ raised a DIFF)"))

    unit_ok = all([h2_ok, h2b_ok, h3_ok, h3b_ok, h4_ok, h8_red_ok, h8_con_ok,
                   pp_base_ok, pp_break_caught, pot_surfaced, bias_surfaced])
    all_ok = ok_mut and unit_ok
    print(f"\nselftest: {passed}/{n_mut} planted-fault mutations caught; "
          f"resolver/island/anchor unit checks {'all OK' if unit_ok else 'FAILED'}"
          + ("" if all_ok else "  !! GATE IS LEAKY"))
    return 0 if all_ok else 1


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
