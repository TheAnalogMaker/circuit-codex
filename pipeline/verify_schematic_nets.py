#!/usr/bin/env python3
"""CI gate: prove a SCHEMATIC's drawn wiring is ELECTRICALLY EQUIVALENT to the
amp's netlist.

The schematic is the artifact a visitor reads first, and until now it was the
one drawing with no connectivity proof at all. `check_schematics.py` is grammar
and geometry (kiutils round-trip, overlap, sheet furniture); `validate.py`
compares designator SETS; `check_tonestack_wiring.py` proves one sub-network on
16 of 38 amps. Nothing compared the drawn net structure to `netlist.cir` — so a
mis-placed wire produced a perfectly valid file that draws a different circuit,
and a copy-pasted phase-inverter mis-wire shipped under a verified badge
(docs/reviews/2026-09-02-schematic-layout-pipeline-deepdive.md §1.3 found it on
six sheets by geometry; this gate finds the same short on eight).

This is the schematic-side twin of `verify_layout_nets.py` and deliberately
mirrors it: build BOTH graphs, solve the mapping rather than assume it, and
declare every abstraction as reviewable DATA instead of burying it in code.

------------------------------------------------------------------------------
WHAT "electrically equivalent" means here
------------------------------------------------------------------------------
`netlist.cir` is a DC-operating-point model. It omits the power-supply front end
(PT + rectifier + reservoir, replaced by an ideal source at the first rail),
transformer winding DCR (plate node == B+), the pot / tone / mixer control
networks, and every cap with a lead inside one of those networks. The schematic
draws the whole amp. So a naive net-for-net match is impossible; instead we
prove the schematic, RESTRICTED TO WHAT THE NETLIST MODELS, is isomorphic to the
netlist: every modelled element's terminals on the same node, no accidental
shorts, no missing joins.

The mapping is solved, not assumed:

  * tube symbols ANCHOR nodes. Unlike the layout — where a socket pin has to be
    resolved through `reference/tubes/<slug>.yaml` basing — a schematic tube
    symbol is drawn per SECTION and its pins are ROLES by construction
    (`cx:TRIODE` 1=P 2=G 3=K, `cx:PENTODE` 1=P 2=G1 3=G2 4=K, `cx:DIODE_TUBE`
    1=A 2=K, from the `LIB` text in schematic_lib.py). The netlist's X element
    lists its nodes in the subckt's declared pin order (`models/<tube>.inc`
    `.subckt 6V6GT P G2 G1 K`), which `verify_layout_nets._subckt_roles` already
    turns into role->node. Role->pin then needs no search and no half-assignment
    enumeration: `XV1A` binds to the symbol lettered `V1A`.
  * two-terminal parts (R / C / L) have unknown pin-1/pin-2 <-> node
    ORIENTATION. A resistor's ends are interchangeable, and `cx:C` carries no
    polarity marks (an electrolytic's + end is not modelled on the sheet or in
    the netlist), so both are matched UNORDERED and resolved by constraint
    propagation from the anchors to one globally consistent whole. If polarity
    is ever drawn, this is the assumption to revisit. The one polarity the
    sheets DO draw, a diode's, is checked separately (RECTIFIER POLARITY).
  * ground: the corpus draws every ground return as a global label `GND`, so
    that one net anchors netlist node `0`. A sheet without a `GND` label is a
    hard failure, never a silent skip.
  * everything the netlist abstracts is reconciled through explicit, reviewable
    data — never a heuristic (see `sch_map` below).

------------------------------------------------------------------------------
DATA, NOT GUESSES — what the amp declares
------------------------------------------------------------------------------
Two sources, in this order:

1. `amps/<id>/layout.yaml` `net_map`, REUSED for the keys whose meaning is
   drawing-independent (a fact about the netlist, not about a board):
     `series_bridge`     a DC-transparent part the netlist omits (grid stopper);
                         the netlist node runs THROUGH it, so its two ends are
                         one node on any drawing.
     `netlist_unplaced`  a netlist element realised by a control rather than a
                         discrete two-lead part (a pot modelled as a grid leak).
     `excluded_tubes`    a socket the DC netlist legitimately omits (a tremolo
                         oscillator has no static operating point).
   Reused entries are printed with their provenance so a reviewer can see the
   layout is doing the explaining.

2. `amps/<id>/sch_map.yaml`, OPTIONAL, schematic-specific (see
   docs/schematic-nets.md for the schema):
     `anchors`           terminal -> netlist node, for a terminal the netlist
                         gives no node to reach on its own (a transformer
                         winding whose DCR the netlist omits, a secondary folded
                         into ground). Two terminals anchored to the SAME node
                         declare the DC bridge the netlist collapses.
     `series_bridge`     as above, for a DC-transparent part the layout has no
                         reason to name (a stopper mounted at a socket lug is
                         not a board part, but it IS drawn).
     `symbols`           netlist ref/instance -> schematic reference, when the
                         drawing letters the same device differently (`RCHOKE`
                         drawn as `L1`; a cathodyne `XPIA` drawn as `V4A`).
     `element_pins`      netlist ref -> the two schematic terminals that realise
                         it, when the symbol has more than two pins (which two
                         pot lugs carry the modelled grid-leak path).
     `netlist_undrawn`   netlist element with no symbol on the sheet — reported
                         in coverage, never a failure, exactly like the layout's
                         `netlist_unplaced`.
     `winding_labels`    global label -> the transformer terminal it stands for
                         (ht_a / ht_b / tap / bias), on a sheet that letters a
                         lead instead of drawing its transformer pin; read by
                         UNFED RECTIFIER, never inferred from a name.
     `schematic_claim`   `verified` opts the sheet into HARD gating.

A declaration never widens to bury a failure, and it never rots unnoticed
either. An UNdeclared undrawn element is a hard finding. A declaration in the
sheet's own sch_map.yaml that names nothing on the sheet — a `symbols` target,
an `anchors` terminal, an `element_pins` pair, a `series_bridge` designator, a
`winding_labels` name — is a STALE DECLARATION finding, named as the stale line it is rather than left to
surface as some downstream element's MISSING SYMBOL. A declaration REUSED from
layout.yaml that does not apply here is a scope line instead, because it was
written about a board and may legitimately have no counterpart on a sheet.
Every reconciliation that WAS applied is echoed in `--report`.

------------------------------------------------------------------------------
WHAT IT REPORTS (each line is something a fixer can act on)
------------------------------------------------------------------------------
  MERGED         one drawn net carries two netlist nodes  -> a short
  SPLIT          one netlist node drawn as >1 net         -> a missing join
  UNREALISED     a netlist node no drawn net carries      -> usually a MERGE's
                 far side; named separately so it cannot vanish
  NODE MISMATCH  a node that is neither merged nor split but whose modelled
                 membership differs from the netlist's (a dangling lead)
  WRONG TERMINAL a modelled element drawn across the wrong pair of nodes
  SHORTED        a modelled element whose two pins are on ONE drawn net
  UNMAPPED       a modelled element's lead on a net carrying no netlist node
  MISSING SYMBOL a netlist element with no schematic symbol, undeclared
  STALE DECL.    an sch_map.yaml declaration that names nothing on this sheet
  REVERSED DIODE a cx:DIODE_SS drawn the wrong way round, judged against the
                 SIGN the netlist gives the supply it sits on (below)
  SHORTED WINDING a winding whose two ends the drawing puts on one net, read
                 on the nets AS DRAWN, before any declared contraction (below)
  UNFED RECTIFIER a rectifier whose AC side reaches no transformer winding
                 (below)
  (coverage)     every schematic symbol with no netlist element is enumerated,
                 tagged "not DC-checked", so what is NOT proven is stated out
                 loud rather than trusted in silence.

------------------------------------------------------------------------------
SHORTED WINDINGS — read on the nets AS DRAWN
------------------------------------------------------------------------------
The netlist models no winding, and this gate joins what it is told to: an
sch_map anchor that puts both OT primary ends on BP1 merges them ON PURPOSE
(the DC model omits the winding's resistance). So a drawing that shorts a
winding passed: on 2026-09-10 the 5F1 drew its OT primary as a wire from PRI_P
to PRI_B, and 16 of 24 power transformers had their mains primary shorted by a
global label lettered MAINS on both leads. SHORTED WINDING reads each winding
in WINDINGS by the symbol's own pin names, on the nets as drawn and before any
contraction, and fails when its two ends are one net: joined by a wire, by two
labels of one name, or through a fuse or a switch in its drawn position (the
6G5's primary closed on itself from one MAINS label through switch, fuse and
winding back to the same name). A centre tap is not an end: CT to ground or to
B+ is how a winding is used. A CT on one net with an end shorts half the
winding and is named as that half. Hard-fails a claimed sheet.

------------------------------------------------------------------------------
RECTIFIER POLARITY — a physical fact the equivalence proof cannot see
------------------------------------------------------------------------------
A diode's orientation is recorded only by its symbol's rotation (`cx:DIODE_SS`
pin 1 = A, pin 2 = K), and the netlist models no diode, so everything above is
blind to it: on 2026-09-10, 25 of 68 sheet diodes were drawn backwards under
clean verdicts. The netlist does fix the SIGN of every supply. Each diode
terminal whose net carries a modelled node is judged against that node's
simulated volts by the rule the board gate shares
(`verify_layout_nets.judge_diode`), and the part is REVERSED if
  * its cathode sits below -5 V (a negative supply is fed from an ANODE),
  * its anode sits above +50 V (B+ is taken off a CATHODE), or
  * both ends are modelled and V(anode) - V(cathode) > 1 V (forward-biased at
    DC between two nodes the netlist holds apart).
Volts come from reference/op-points.yaml, else the netlist's own ideal source
to ground (a rail's simulated voltage IS its source value); node 0 is 0 V. A
supply's first node often sits behind parts the netlist does not model (a bias
row's resistor and trim pot, an HT standby switch or choke), so a terminal on
no modelled node inherits one through `supply_walk`, which crosses only
POLARITY_WALK_LIBS parts carrying no netlist element, uses what it reaches only
when those nodes agree in sign, and prints the path. A diode nothing decides is
listed as "polarity not checked" with its reason, and counted, every run.
REVERSED DIODE is a finding like any other: it hard-fails a claimed sheet.

------------------------------------------------------------------------------
RECTIFIER FEED — polarity's blind spot
------------------------------------------------------------------------------
Polarity knows which side of ground a supply sits on, not that a winding feeds
it: at e4e59fa the 6G5 drew four diodes whose AC corners all sat on ground, and
polarity read two of them "confirmed". Each diode the model gives a role
(`verify_layout_nets.rectifier_role`: exactly one end on a supply, HT above
+50 V or bias below -5 V) is walked from its OTHER end, its AC side, to a
transformer winding: across POLARITY_WALK_LIBS parts and the other diodes of
its own stack or bridge (diodes sharing a net that is neither ground nor a
modelled node), never into ground or a DC node. It is fed when the walk
reaches a cx:PT pin other than the centre tap, or a global label that
sch_map.yaml `winding_labels` declares as a winding terminal the sheet's
transformer symbol has no pin for (16 sheets draw no transformer). Names are
never inferred, and a declaration for a terminal the drawn transformer does
carry is a STALE DECLARATION. Otherwise UNFED RECTIFIER, a finding like any
other. A diode with no role
is walked as part of a stack- or bridge-mate that has one, or listed as not
checked.

------------------------------------------------------------------------------
VERDICT + GATE
------------------------------------------------------------------------------
An amp whose `sch_map.yaml` carries `schematic_claim: verified` is HARD-GATED; an
amp without the claim is report-only. Mirrors `wiring_claim` on the layout side
and `verification.status` on the netlist side: verified is earned, never granted.
`--strict` fails on any finding on any amp (use it once the corpus is green).

    python3 pipeline/verify_schematic_nets.py              # check all sheets
    python3 pipeline/verify_schematic_nets.py 5e3 ab763    # named sheets
    python3 pipeline/verify_schematic_nets.py --report     # + coverage detail
    python3 pipeline/verify_schematic_nets.py --analyze 5e3   # node <-> net dump
    python3 pipeline/verify_schematic_nets.py --selftest   # planted-fault test
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from sch_nets import Nets, _key, _on_segment
from verify_layout_nets import (diode_groups, inherit_node, judge_diode,
                                judge_feed, node_volts, parse_netlist,
                                rectifier_role, supply_walk)

ROOT = Path(__file__).resolve().parent.parent
AMPS = ROOT / "amps"

# ---------------------------------------------------------------------------
# symbol contracts, read off schematic_lib.LIB (pin NUMBERS are roles by
# construction — the drawings hide pin numbers, so these are positional).
# ---------------------------------------------------------------------------
TUBE_ROLE_PINS = {
    "cx:TRIODE":     {"plate": "1", "grid": "2", "cathode": "3"},
    "cx:PENTODE":    {"plate": "1", "grid": "2", "screen": "3", "cathode": "4"},
    "cx:DIODE_TUBE": {"plate": "1", "cathode": "2"},
}
# lib_ids a netlist R/C/L may bind to without an explicit element_pins entry:
# exactly the two-lead passives. Anything else (a pot, a can cap, a winding)
# must name its two terminals in sch_map.element_pins — a 3+ pin symbol has no
# unambiguous "the two ends", and guessing one is how a gate starts lying.
TWO_TERM_LIBS = {"cx:R", "cx:C", "cx:CHOKE", "cx:DIODE_SS", "cx:FUSE",
                 "cx:SWITCH", "cx:LAMP"}
GND_LABEL = "GND"
# The one POLARISED two-lead symbol: schematic_lib.LIB draws cx:DIODE_SS with
# pin 1 = A (anode) and pin 2 = K (cathode, the band). Unlike R and C its two
# ends are NOT interchangeable, and the symbol's rotation is the only place the
# drawing records which end is which.
DIODE_LIB = "cx:DIODE_SS"
DIODE_PINS = {"anode": "1", "cathode": "2"}
# What a polarity walk may cross from a diode terminal whose net carries no
# netlist node, to the supply node behind it: parts that conduct DC and carry
# no netlist element. Every pin of a pot is one DC body (track ends + wiper).
# Never a capacitor (DC-open), a transformer (a winding is a source), a tube,
# a lamp, a jack, or another diode.
POLARITY_WALK_LIBS = {"cx:R", "cx:POT", "cx:POT_TAP", "cx:CHOKE", "cx:FUSE",
                      "cx:SWITCH"}
# Every winding a transformer-type symbol draws, by the symbol's own pin NAMES
# (schematic_lib.LIB), as (winding, end, end, the winding this is half of). A
# centre tap is not an end: CT to ground or CT to B+ is how a winding is used,
# never a finding, while a CT on one net with an END shorts half the winding.
# Names resolve to numbers through the sheet's own lib_symbols, so a
# renumbered symbol cannot quietly aim this table at the wrong pins.
WINDINGS = {
    "cx:PT": [("primary", "PRI_1", "PRI_2", None),
              ("HT secondary", "HT_A", "HT_B", None),
              ("HT secondary's A half", "HT_A", "HT_CT", "HT secondary"),
              ("HT secondary's B half", "HT_B", "HT_CT", "HT secondary")],
    "cx:OT_SE": [("primary", "PRI_P", "PRI_B", None),
                 ("secondary", "SEC_H", "SEC_C", None)],
    "cx:OT_PP": [("primary", "PRI_A", "PRI_B", None),
                 ("primary's A half", "PRI_A", "CT", "primary"),
                 ("primary's B half", "PRI_B", "CT", "primary"),
                 ("secondary", "SEC_H", "SEC_C", None)],
    "cx:TANK": [("input coil", "IN_H", "IN_C", None),
                ("output coil", "OUT_H", "OUT_C", None)],
    "cx:CHOKE": [("winding", "1", "2", None)],
}
# Parts that close a loop at DC with no drop, so a winding's two ends joined
# THROUGH them are still one node: a fuse, and a switch in the position the
# sheet draws it (the DC netlist models the amp in play).
WINDING_CLOSERS = {"cx:FUSE", "cx:SWITCH"}
# The winding terminals a sheet may letter as a global label instead of
# drawing its transformer's pin, each with the cx:PT pin it stands for (None:
# the symbol has no pin for it, as for a separate bias winding). WHICH label
# stands for which terminal is declared per sheet in sch_map.yaml
# `winding_labels`, never inferred from a name: 16 sheets draw no power
# transformer, and the AB763-Twin and AB763 Super letter a bias tap their
# transformer symbol lacks.
WINDING_TERMINALS = {"ht_a": "HT_A", "ht_b": "HT_B", "tap": "HT_TAP",
                     "bias": None}


# ---------------------------------------------------------------------------
# amp data
# ---------------------------------------------------------------------------
def amp_ids() -> list[str]:
    """Every amp with BOTH a netlist and a schematic (the gate's population)."""
    out = []
    for d in sorted(AMPS.iterdir()):
        if d.is_dir() and (d / "netlist.cir").exists() and (d / "schematic.kicad_sch").exists():
            out.append(d.name)
    return out


def load_layout_net_map(amp_id: str) -> dict:
    path = AMPS / amp_id / "layout.yaml"
    if not path.exists():
        return {}
    return (yaml.safe_load(path.read_text()) or {}).get("net_map") or {}


def load_sch_map(amp_id: str) -> dict:
    path = AMPS / amp_id / "sch_map.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


# ---------------------------------------------------------------------------
# schematic graph
# ---------------------------------------------------------------------------
class SchGraph:
    """`sch_nets.Nets` plus the symbol table the equivalence check needs."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.nets = Nets(self.path)
        self.lib: dict = {}       # reference -> lib_id
        for sym in self.nets.sch.schematicSymbols:
            ref = None
            for prop in sym.properties:
                if prop.key == "Reference":
                    ref = prop.value
            if ref is not None:
                self.lib.setdefault(ref, sym.libId)

    def term(self, name: str):
        return self.nets.terminal(name)

    def join(self, a: str, b: str) -> bool:
        return self.nets.join(a, b)

    def members(self) -> dict:
        return self.nets.nets()

    def all_terminals(self) -> list[str]:
        return sorted(f"{r}.{n}" for r, pins in self.nets.pins.items() for n in pins)


# ---------------------------------------------------------------------------
# result
# ---------------------------------------------------------------------------
class Result:
    def __init__(self, amp_id: str):
        self.amp_id = amp_id
        self.claim = False
        self.ok = False
        self.errors: list[str] = []    # findings, in builder language
        self.info: list[str] = []      # declared reconciliations, applied
        self.scope: list[str] = []     # honest coverage
        self.classes: dict = {}        # class -> count
        # node -> (drawn modelled terminals, missing fixed, pairs that miss it,
        #          unexpected terminals) — the per-node membership table
        self.node_diff: dict = {}
        self.polarity: list = []       # judge_diode() verdict per cx:DIODE_SS
        self.graph = None              # the solved SchGraph and its net root ->
        self.node_of_root: dict = {}   #   netlist node map (for --analyze / tests)


def _bump(res: Result, cls: str, line: str):
    res.errors.append(f"{cls}: {line}")
    res.classes[cls] = res.classes.get(cls, 0) + 1


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------
def check_amp(amp_id: str, sch_path: "Path | None" = None,
              sch_map: "dict | None" = None) -> Result:
    """Solve one sheet against its netlist. `sch_path` overrides the amp's
    schematic (the mutation self-test feeds a planted-fault copy); `sch_map`
    overrides the sidecar."""
    res = Result(amp_id)
    amp_dir = AMPS / amp_id
    comps, nodes = parse_netlist(amp_dir / "netlist.cir")
    net_map = load_layout_net_map(amp_id)
    sm = load_sch_map(amp_id) if sch_map is None else sch_map
    res.claim = str(sm.get("schematic_claim", "")).lower() == "verified"

    G = SchGraph(sch_path or amp_dir / "schematic.kicad_sch")
    members_of = G.members

    # -- 0. shorted windings, on the nets AS DRAWN --------------------------
    # Before any contraction below: an anchor that co-locates both OT primary
    # ends on BP1 JOINS them, which is how the 5F1's shorted primary passed.
    sym_map = {str(k): str(v) for k, v in (sm.get("symbols") or {}).items()}
    _check_windings(res, G, {sym_map.get(c.ref, c.ref) for c in comps
                             if c.kind in ("R", "C", "L")})

    # -- 1. declared contractions ------------------------------------------
    # DC-transparent series parts: the netlist node runs THROUGH them.
    bridges: dict = {}
    for ref, why in (net_map.get("series_bridge") or {}).items():
        bridges[ref] = (why, "layout net_map.series_bridge")
    for ref, why in (sm.get("series_bridge") or {}).items():
        bridges[ref] = (why, "sch_map.series_bridge")
    for ref, (why, src) in sorted(bridges.items()):
        if ref not in G.nets.pins:
            # A declaration the SHEET's own sch_map.yaml makes is stale — it was
            # written about this drawing and no longer matches it. A declaration
            # REUSED from layout.yaml may legitimately not apply here (a board
            # part the sheet abstracts), so that one is scope, not a finding.
            if src.startswith("sch_map"):
                _bump(res, "STALE DECLARATION",
                      f"sch_map.series_bridge[{ref}] names no symbol on this sheet "
                      f"— nothing bridged. Delete it, or correct the designator.")
            else:
                res.scope.append(f"series_bridge {ref} names no symbol on this sheet "
                                 f"(declared in {src}) — nothing bridged")
            continue
        if G.join(f"{ref}.1", f"{ref}.2"):
            res.info.append(f"bridged {ref} (DC-transparent, {src}): {why}")
        else:
            res.scope.append(f"series_bridge {ref}: symbol has no pins 1/2 — "
                             f"not bridged ({src})")

    # Anchors: terminal -> node. Co-anchoring to one node declares the DC bridge
    # the netlist collapses (an OT primary whose DCR is omitted).
    anchors: dict = {}
    for term, node in (sm.get("anchors") or {}).items():
        anchors[str(term)] = str(node)
    by_node: dict = {}
    # Ground is seeded with the GND label, so an anchor to node 0 — an OT
    # secondary whose DCR the netlist folds into ground, the NFB return —
    # collapses ONTO the ground net instead of reading as a second net that
    # happens to carry node 0. Same seeding as verify_layout_nets' ground bus.
    if G.term(f"<{GND_LABEL}>") is not None:
        by_node["0"] = [f"<{GND_LABEL}>"]
    for term, node in anchors.items():
        if G.term(term) is None:
            _bump(res, "STALE DECLARATION",
                  f"sch_map.anchors[{term}] -> {node} names no pin or label on "
                  f"this sheet — not applied. Correct the terminal, or delete it.")
            continue
        by_node.setdefault(node, []).append(term)
    for node, terms in sorted(by_node.items()):
        for other in terms[1:]:
            G.join(terms[0], other)
        if len(terms) > 1:
            res.info.append(f"anchored {', '.join(sorted(terms))} to node {node} "
                            f"(declared DC bridge — the netlist collapses what sits "
                            f"between them)")
        elif terms[0] in anchors:
            res.info.append(f"anchored {terms[0]} to node {node}")

    # -- 2. element -> symbol binding --------------------------------------
    symbols = {str(k): str(v) for k, v in (sm.get("symbols") or {}).items()}
    element_pins = {str(k): [str(t) for t in v]
                    for k, v in (sm.get("element_pins") or {}).items()}
    undrawn = dict(sm.get("netlist_undrawn") or {})
    unplaced = dict(net_map.get("netlist_unplaced") or {})

    # A `symbols` entry redirects the lookup for a netlist element to a
    # differently-lettered symbol. When its TARGET no longer exists the lookup
    # lands nowhere, and reporting only "netlist X has no symbol" is actively
    # misleading — the element may well be on the sheet under its own name, and
    # the stale redirect is what hid it (this cost a debug cycle when a fixer
    # renamed ab763's V1 to V1A). So the stale mapping is named first, as a
    # STALE DECLARATION, and the redirected element is then skipped rather than
    # mis-reported. It is never repaired by falling back to the netlist name:
    # a declaration is data a reviewer owns, and silently working around a
    # wrong one is how a map rots unnoticed.
    stale_symbols: set = set()
    for src, dst in sorted(symbols.items()):
        if dst in G.lib:
            continue
        stale_symbols.add(src)
        hint = (f" The sheet does letter a symbol '{src}', so the mapping is "
                f"probably just obsolete — delete it."
                if src in G.lib else
                f" Neither '{dst}' nor '{src}' is on the sheet.")
        _bump(res, "STALE DECLARATION",
              f"sch_map.symbols[{src}] -> {dst} names no symbol on this sheet, so "
              f"netlist {src} was looked up and not found.{hint}")

    tube_terms: dict = {}     # netlist X comp -> {role: terminal}
    part_terms: dict = {}     # netlist R/C/L ref -> (terminal_a, terminal_b)
    modelled_terms: set = set()

    for c in comps:
        if c.kind == "X":
            if c.inst in stale_symbols:
                continue      # already named as a STALE DECLARATION above
            ref = symbols.get(c.inst, c.inst)
            lib = G.lib.get(ref)
            if lib is None:
                _missing(res, c.inst, c, undrawn, unplaced, "tube")
                continue
            roles = TUBE_ROLE_PINS.get(lib)
            if roles is None:
                _bump(res, "MISSING SYMBOL",
                      f"netlist tube {c.inst} is drawn as {ref} ({lib}), which is "
                      f"not a tube symbol — declare the real symbol in "
                      f"sch_map.symbols")
                continue
            tm = {}
            for role, node in c.roles.items():
                pin = roles.get(role)
                if pin is None or pin not in G.nets.pins.get(ref, {}):
                    _bump(res, "MISSING SYMBOL",
                          f"netlist {c.inst} needs a {role} pin but symbol {ref} "
                          f"({lib}) has none")
                    continue
                tm[role] = f"{ref}.{pin}"
            tube_terms[id(c)] = tm
            modelled_terms.update(tm.values())
        elif c.kind in ("R", "C", "L"):
            if c.ref in element_pins:
                terms = element_pins[c.ref]
                if len(terms) != 2 or any(G.term(t) is None for t in terms):
                    _bump(res, "STALE DECLARATION",
                          f"sch_map.element_pins[{c.ref}] = {terms} does not name "
                          f"two terminals this sheet carries — {c.ref} is unchecked")
                    continue
                part_terms[c.ref] = (terms[0], terms[1])
                modelled_terms.update(terms)
                res.info.append(f"{c.ref} realised by {terms[0]} / {terms[1]} "
                                f"(sch_map.element_pins)")
                continue
            if c.ref in stale_symbols:
                continue      # already named as a STALE DECLARATION above
            ref = symbols.get(c.ref, c.ref)
            lib = G.lib.get(ref)
            if lib is None:
                _missing(res, c.ref, c, undrawn, unplaced, "part")
                continue
            if lib not in TWO_TERM_LIBS:
                _bump(res, "MISSING SYMBOL",
                      f"netlist {c.ref} is drawn as {ref} ({lib}), a symbol with "
                      f"no unambiguous two ends — name the two terminals in "
                      f"sch_map.element_pins")
                continue
            ta, tb = f"{ref}.1", f"{ref}.2"
            if G.term(ta) is None or G.term(tb) is None:
                _bump(res, "MISSING SYMBOL",
                      f"symbol {ref} for netlist {c.ref} has no pins 1/2")
                continue
            part_terms[c.ref] = (ta, tb)
            modelled_terms.update((ta, tb))

    # -- 3. anchor + propagate ---------------------------------------------
    M: dict = {}          # net root -> netlist node (first binding wins)
    assigns: dict = {}    # net root -> {node: why}  (>1 node == a short)

    def assign(root, node, why) -> bool:
        """Bind a NET ROOT (never a terminal name — a terminal's root moves as
        declared contractions are applied) to a netlist node. Returns True only
        when this call bound the root for the first time, which is what makes
        the propagation loop below terminate: a re-assignment records the
        conflict for the MERGED report but never counts as progress."""
        if root is None:
            return False
        assigns.setdefault(root, {}).setdefault(node, why)
        if root in M:
            return False
        M[root] = node
        return True

    gnd = G.term(f"<{GND_LABEL}>")
    if gnd is None:
        _bump(res, "MISSING SYMBOL",
              f"the sheet carries no <{GND_LABEL}> label — netlist node 0 has "
              f"nothing to anchor to, so nothing downstream of ground is checked")
    else:
        assign(gnd, "0", f"<{GND_LABEL}> label")

    for term, node in anchors.items():
        assign(G.term(term), node, f"sch_map anchor {term}")

    for c in comps:
        if c.kind != "X" or id(c) not in tube_terms:
            continue
        for role, term in tube_terms[id(c)].items():
            assign(G.term(term), c.roles[role], f"{term} ({c.inst} {role})")

    two_term = [c for c in comps if c.kind in ("R", "C", "L") and c.ref in part_terms]
    changed = True
    while changed:
        changed = False
        for c in two_term:
            ta, tb = part_terms[c.ref]
            ra, rb = G.term(ta), G.term(tb)
            n1, n2 = c.nodes
            ma, mb = M.get(ra), M.get(rb)
            if ma is not None and mb is None:
                other = n2 if ma == n1 else (n1 if ma == n2 else None)
                if other is not None:
                    changed |= assign(rb, other, f"through {c.ref}")
            elif mb is not None and ma is None:
                other = n2 if mb == n1 else (n1 if mb == n2 else None)
                if other is not None:
                    changed |= assign(ra, other, f"through {c.ref}")

    # -- 3b. rectifier polarity ---------------------------------------------
    # Which way round a diode is drawn is recorded ONLY by its symbol's rotation,
    # and the DC netlist models no diode, so nothing above can see it: 25 of 68
    # sheet diodes were backwards on 2026-09-10 under clean verdicts. The
    # netlist does fix the SIGN of every supply, so each diode terminal whose net
    # carries a modelled node is judged against that node's simulated volts, by
    # the one rule both drawing gates share (verify_layout_nets.judge_diode).
    # A supply's first node often sits behind series parts the netlist does not
    # model (a bias row's resistor and trim pot, an HT standby switch or choke),
    # so a terminal on no modelled node inherits one through supply_walk, which
    # crosses only POLARITY_WALK_LIBS parts that carry no netlist element.
    res.graph, res.node_of_root = G, M
    volts = node_volts(amp_id)
    modelled_refs = {t.rpartition(".")[0] for t in modelled_terms}
    pol_mem = members_of()

    def neighbours(root):
        for m in pol_mem.get(root, ()):
            if m.startswith("<"):
                continue
            sref, _, num = m.rpartition(".")
            if sref in modelled_refs or G.lib.get(sref) not in POLARITY_WALK_LIBS:
                continue
            for onum in G.nets.pins.get(sref, {}):
                if onum != num:
                    yield sref, G.term(f"{sref}.{onum}")

    def locate(term):
        root = G.term(term)
        if root is None or M.get(root) is not None:
            return (term, M.get(root))
        found, note = inherit_node(supply_walk(root, M.get, neighbours), volts)
        return (term, found[0], found[1]) if found else (term, None, (), note)

    for ref in sorted(G.lib):
        if G.lib[ref] != DIODE_LIB:
            continue
        ta, tk = f"{ref}.{DIODE_PINS['anode']}", f"{ref}.{DIODE_PINS['cathode']}"
        p = judge_diode(ref, locate(ta), locate(tk), volts)
        res.polarity.append(p)
        if p["verdict"] == "REVERSED":
            _bump(res, "REVERSED DIODE",
                  f"{ref} is drawn the wrong way round: {p['why']}. "
                  f"[{p['desc']}] Turn the symbol through 180 degrees.")

    # -- 3c. rectifier feed --------------------------------------------------
    # Polarity knows which side of ground a supply sits on, not that a winding
    # feeds it (the 6G5's base sheet: a bridge on ground, two diodes
    # "confirmed"). Each diode the model gives a role is walked from its AC side
    # to a transformer winding.
    _check_feeds(res, G, M, modelled_refs, pol_mem,
                 sm.get("winding_labels") or {})

    # -- 4. findings --------------------------------------------------------
    mem = members_of()

    def modelled_on(root) -> list:
        return sorted(t for t in mem.get(root, ()) if t in modelled_terms)

    def show(root) -> str:
        m = mem.get(root, [])
        model = [t for t in m if t in modelled_terms]
        rest = [t for t in m if t not in modelled_terms]
        shown = sorted(model) + sorted(rest)[:4]
        tail = "" if len(shown) >= len(m) else f", +{len(m) - len(shown)} more"
        return "{" + ", ".join(shown) + tail + "}"

    # (a) MERGED — one drawn net carrying two netlist nodes.
    merged_nodes: set = set()
    for root in sorted(assigns, key=lambda r: str(r)):
        nd = assigns[root]
        if len(nd) < 2:
            continue
        merged_nodes.update(nd)
        got = sorted(nd)
        _bump(res, "MERGED",
              f"netlist nodes {' and '.join(got)} are drawn as ONE net — a short "
              f"the netlist does not have. Net {show(root)}. "
              f"[{'; '.join(f'{n} <- {nd[n]}' for n in got)}]")

    # (b) SPLIT — one netlist node drawn as several nets that never join.
    node_roots: dict = {}
    for root, node in M.items():
        node_roots.setdefault(node, []).append(root)
    split_nodes: set = set()
    for node in sorted(node_roots):
        roots = node_roots[node]
        if len(roots) < 2:
            continue
        split_nodes.add(node)
        frags = " | ".join(show(r) for r in sorted(roots, key=lambda r: str(r)))
        _bump(res, "SPLIT",
              f"netlist node {node} is drawn as {len(roots)} separate nets that "
              f"are never joined: {frags}")

    # (c) UNREALISED — a node no drawn net carries at all.
    realised = set(M.values())
    for node in sorted(nodes):
        if node in realised:
            continue
        touch = sorted(_node_terminals(node, comps, tube_terms, part_terms))
        _bump(res, "UNREALISED",
              f"netlist node {node} is on no drawn net — the netlist puts "
              f"{', '.join(touch) if touch else 'no modelled terminal'} on it "
              f"(usually the far side of a MERGED pair)")

    # (d) per-node membership diff, orientation-agnostic. Only the residue the
    #     per-component lines below do not already name reaches here, because a
    #     node is in exactly one of {merged, split, unrealised, this, clean}.
    res.node_diff = {}
    for node in sorted(nodes):
        fixed, pairs = _node_expectation(node, comps, tube_terms, part_terms)
        got: set = set()
        for root in node_roots.get(node, []):
            got.update(modelled_on(root))
        missing = sorted(fixed - got)
        satisfied: set = set()
        absent: list = []
        for ref, ta, tb in pairs:
            on = [t for t in (ta, tb) if t in got]
            if on:
                satisfied.update(on)     # both ends on it is the SHORTED case
            else:
                absent.append(ref)
        extra = sorted(got - fixed - satisfied)
        res.node_diff[node] = (sorted(fixed | satisfied), missing, absent, extra)
        if node in merged_nodes or node in split_nodes or node not in realised:
            continue
        if not (missing or absent or extra):
            continue
        bits = []
        if missing:
            bits.append(f"missing {', '.join(missing)}")
        if absent:
            bits.append("neither end of " + ", ".join(sorted(absent)) + " reaches it")
        if extra:
            bits.append(f"unexpected {', '.join(extra)}")
        _bump(res, "NODE MISMATCH",
              f"netlist node {node}: {'; '.join(bits)} "
              f"(drawn as {' | '.join(show(r) for r in node_roots.get(node, []))})")

    # (e) per-component: wrong terminal / shorted / unmapped / dangling.
    for c in two_term:
        ta, tb = part_terms[c.ref]
        ra, rb = G.term(ta), G.term(tb)
        ma, mb = M.get(ra), M.get(rb)
        if ra == rb:
            _bump(res, "SHORTED",
                  f"{c.ref}'s two leads ({ta}, {tb}) are on ONE drawn net but the "
                  f"netlist has it {c.nodes[0]}<->{c.nodes[1]} — the part is "
                  f"shorted out. Net {show(ra)}")
            continue
        for term, m, root in ((ta, ma, ra), (tb, mb, rb)):
            if m is not None:
                continue
            dangling = len(mem.get(root, ())) < 2
            _bump(res, "UNMAPPED",
                  f"{c.ref} lead {term} is on no netlist node "
                  f"(expected {c.nodes[0]}/{c.nodes[1]}); "
                  + ("that pin is DANGLING — nothing else sits on its net"
                     if dangling else f"its net is {show(root)}"))
        if ma is not None and mb is not None and {ma, mb} != set(c.nodes):
            _bump(res, "WRONG TERMINAL",
                  f"{c.ref} is drawn {ma}<->{mb} but the netlist has it "
                  f"{c.nodes[0]}<->{c.nodes[1]}")

    for c in comps:
        if c.kind != "X" or id(c) not in tube_terms:
            continue
        for role, term in sorted(tube_terms[id(c)].items()):
            root = G.term(term)
            got = M.get(root)
            want = c.roles[role]
            if got is None:
                dangling = len(mem.get(root, ())) < 2
                _bump(res, "UNMAPPED",
                      f"{term} ({c.inst} {role}) is on no netlist node (expected "
                      f"{want}); "
                      + ("that pin is DANGLING — nothing else sits on its net"
                         if dangling else f"its net is {show(root)}"))
            elif got != want:
                _bump(res, "WRONG TERMINAL",
                      f"{term} ({c.inst} {role}) is on {got} but the netlist puts "
                      f"it on {want}")

    # -- 5. honest coverage -------------------------------------------------
    _scope(res, G, comps, tube_terms, part_terms, modelled_terms, mem, M,
           net_map, undrawn, unplaced)
    for p in res.polarity:
        if p["verdict"] == "confirmed":
            res.scope.append(f"polarity {p['ref']}: confirmed by the DC model "
                             f"[{p['desc']}]")
        elif p["verdict"] == "unchecked":
            res.scope.append(f"polarity {p['ref']}: NOT CHECKED, {p['why']} "
                             f"[{p['desc']}]")
    for p in res.polarity:
        f = p.get("feed")
        if f:
            res.scope.append(f"feed {p['ref']}: {f['verdict']}, {f['why']}")
    res.ok = not res.errors
    return res


def _check_feeds(res: Result, G: "SchGraph", M: dict, modelled_refs: set,
                 mem: dict, winding_labels: dict):
    """UNFED RECTIFIER. Each cx:DIODE_SS the DC model gives a role is walked
    from its AC side (the end rectifier_role does not put on the supply) to a
    transformer winding; one that reaches none is a finding. A diode with no
    role is recorded as walked through a stack- or bridge-mate, or not checked.
    Verdicts land on each res.polarity entry under 'feed'. A global label is a
    winding terminal only where sch_map `winding_labels` declares it, and only
    for a terminal the sheet's transformer symbol, if it draws one, has no pin
    for; any other declaration is a STALE DECLARATION and is not applied."""
    names = _pin_numbers(G)
    pt_pin = {num: nm for nm, num in names.get("cx:PT", {}).items()}
    pt_leads = (set(names.get("cx:PT", {}))
                if any(lib == "cx:PT" for lib in G.lib.values()) else set())
    declared: dict = {}
    for label, term in (winding_labels or {}).items():
        label, term = str(label), str(term)
        where = f"sch_map.winding_labels[{label}] = {term}"
        if term not in WINDING_TERMINALS:
            _bump(res, "STALE DECLARATION",
                  f"{where} is not a winding terminal (one of "
                  f"{', '.join(sorted(WINDING_TERMINALS))}); not applied")
        elif label not in G.nets.labels:
            _bump(res, "STALE DECLARATION",
                  f"{where} names no global label on this sheet; not applied. "
                  f"Correct the name, or delete it.")
        elif WINDING_TERMINALS[term] in pt_leads:
            _bump(res, "STALE DECLARATION",
                  f"{where}: this sheet draws a transformer with a "
                  f"{WINDING_TERMINALS[term]} pin, so a label for that terminal "
                  f"must reach the pin; not applied. Delete the declaration.")
        else:
            declared[label] = term
            res.info.append(f"<{label}> stands for the transformer's {term} "
                            f"terminal (sch_map.winding_labels)")

    def is_stop(net):
        return M.get(net) is not None

    near: set = set()      # labels a walk reached that no declaration covers

    def feeds(net):
        for m in mem.get(net, ()):
            if m.startswith("<"):
                if m[1:-1] in declared:
                    return (f"the declared winding label {m} "
                            f"({declared[m[1:-1]]})")
                near.add(m)
                continue
            sref, _, num = m.rpartition(".")
            if G.lib.get(sref) == "cx:PT" and pt_pin.get(num, "HT_CT") != "HT_CT":
                return f"{m} ({pt_pin[num]})"
        return None

    diodes = {p["ref"]: p for p in res.polarity}
    nets_of = {r: [G.term(f"{r}.{DIODE_PINS['anode']}"),
                   G.term(f"{r}.{DIODE_PINS['cathode']}")] for r in diodes}
    groups = diode_groups(nets_of, is_stop)

    def neighbours_for(judged_ref):
        mates = groups[judged_ref] - {judged_ref}

        def nb(net):
            for m in mem.get(net, ()):
                if m.startswith("<"):
                    continue
                sref, _, num = m.rpartition(".")
                if sref == judged_ref or sref in modelled_refs:
                    continue
                if G.lib.get(sref) in POLARITY_WALK_LIBS or sref in mates:
                    for other in G.nets.pins.get(sref, {}):
                        if other != num:
                            yield sref, G.term(f"{sref}.{other}")
        return nb

    judged: set = set()
    for ref, p in diodes.items():
        role = rectifier_role(p["va"], p["vk"])
        if role is None:
            continue
        ac = f"{ref}.{DIODE_PINS['anode' if role[1] == 'cathode' else 'cathode']}"
        near.clear()
        f = judge_feed(ref, role, ac, G.term(ac), is_stop, feeds,
                       neighbours_for(ref), M.get)
        p["feed"] = f
        judged.add(ref)
        if f["verdict"] == "UNFED":
            mates = sorted(groups[ref] - {ref})
            _bump(res, "UNFED RECTIFIER",
                  f"{ref} ({role[0]} rectifier: its {role[1]} is on the supply) is "
                  f"fed by nothing: {f['why']}"
                  + ((f" (it reaches {', '.join(sorted(near))}, but never a "
                      f"transformer pin)" if pt_leads else
                      f" (it reaches {', '.join(sorted(near))}, which "
                      f"sch_map.winding_labels does not declare as a winding "
                      f"terminal)") if near else "")
                  + (f"; its stack or bridge is {', '.join(mates)}" if mates else "")
                  + ". Join its AC side to the winding the source draws.")
    for ref, p in diodes.items():
        if "feed" in p:
            continue
        mates = sorted(groups[ref] & judged)
        p["feed"] = ({"verdict": "covered", "ref": ref,
                      "why": f"no role of its own; walked as part of "
                             f"{', '.join(mates)}'s stack or bridge"} if mates else
                     {"verdict": "unchecked", "ref": ref,
                      "why": "no role (the model names no supply at either end) "
                             "and no stack- or bridge-mate with one"})


def _pin_numbers(G: "SchGraph") -> dict:
    """lib_id -> {pin name: pin number}, read from the sheet's own lib_symbols."""
    out: dict = {}
    for ls in G.nets.sch.libSymbols:
        names: dict = {}
        for unit in ls.units:
            for pin in unit.pins:
                names.setdefault(pin.name, pin.number)
        out[ls.libId] = names
    return out


def _closer_path(G: "SchGraph", mem: dict, start, goal) -> "list | None":
    """The WINDING_CLOSERS parts (fuses, switches) whose chain joins net `start`
    to net `goal`, nearest first; None when no such chain exists."""
    seen, frontier = {start}, [(start, [])]
    while frontier:
        net, path = frontier.pop(0)
        for m in mem.get(net, ()):
            if m.startswith("<"):
                continue
            ref, _, num = m.rpartition(".")
            if G.lib.get(ref) not in WINDING_CLOSERS:
                continue
            for other in G.nets.pins.get(ref, {}):
                nxt = G.term(f"{ref}.{other}")
                if other == num or nxt in seen:
                    continue
                if nxt == goal:
                    return path + [ref]
                seen.add(nxt)
                frontier.append((nxt, path + [ref]))
    return None


def _wire_only(G: "SchGraph"):
    """find(point) -> root over the sheet's connectivity from wires, T-taps and
    junction dots ALONE, without the joins global labels make by name
    (sch_nets.Nets builds this same graph and then ties same-named labels
    together). Lets SHORTED WINDING say whether a wire or a label did it."""
    sch = G.nets.sch
    segs = [(_key(w.points[0].X, w.points[0].Y), _key(w.points[1].X, w.points[1].Y))
            for w in sch.graphicalItems if getattr(w, "type", None) == "wire"]
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    points: set = set()
    for a, b in segs:
        union(a, b)
        points.update((a, b))
    points.update(_key(j.position.X, j.position.Y) for j in sch.junctions)
    for pinmap in G.nets.pins.values():
        points.update(pinmap.values())
    for anchors in G.nets.labels.values():
        points.update(anchors)
    for p in points:
        for a, b in segs:
            if _on_segment(p, a, b):
                union(p, a)
    return find


def _check_windings(res: Result, G: "SchGraph", bound: set):
    """SHORTED WINDING: a winding whose two ends the drawing puts on one net, by
    a wire, by two global labels of one name, or through a fuse or a switch in
    its drawn position. Must run on the nets AS DRAWN, before any sch_map
    contraction. `bound` holds the symbols a netlist element is drawn as: a
    modelled choke's short is SHORTED's to report, not this class's."""
    names = _pin_numbers(G)
    mem = G.members()
    wires = None                      # built only when a winding is shorted
    for ref in sorted(G.lib):
        lib = G.lib[ref]
        if lib == "cx:CHOKE" and ref in bound:
            continue
        shorted: set = set()
        for winding, ea, eb, half_of in WINDINGS.get(lib, ()):
            if half_of in shorted:
                continue              # the whole winding is already named
            na, nb = names.get(lib, {}).get(ea), names.get(lib, {}).get(eb)
            if na is None or nb is None:
                res.scope.append(f"winding check: {ref} ({lib}) carries no pin "
                                 f"named {ea if na is None else eb}, so its "
                                 f"{winding} is not checked")
                continue
            ta, tb = f"{ref}.{na}", f"{ref}.{nb}"
            ra, rb = G.term(ta), G.term(tb)
            if ra is None or rb is None:
                continue
            if ra == rb:
                wires = wires or _wire_only(G)
                ca = wires(G.nets.pins[ref][na])
                cb = wires(G.nets.pins[ref][nb])
                if ca == cb:
                    how = "one net: a wire joins them"
                else:
                    # a label is to blame only if one name letters both sides
                    both = sorted(n for n, anchors in G.nets.labels.items()
                                  if any(wires(x) == ca for x in anchors)
                                  and any(wires(x) == cb for x in anchors))
                    via = both or sorted({m[1:-1] for m in mem.get(ra, ())
                                          if m.startswith("<")})
                    how = (f"one net, joined by the global label"
                           f"{'s' if len(via) > 1 else ''} "
                           f"{' and '.join(repr(n) for n in via)}, one name "
                           f"lettered on both sides: give each lead its own name")
            else:
                path = _closer_path(G, mem, ra, rb)
                if path is None:
                    continue
                how = (f"one net through {', '.join(path)}: the loop runs from one "
                       f"end, through {'that part' if len(path) == 1 else 'those parts'}"
                       f", back to the other")
            shorted.add(winding)
            show = mem.get(ra, [])
            _bump(res, "SHORTED WINDING",
                  f"{ref}'s {winding} is shorted: its ends {ta} ({ea}) and {tb} "
                  f"({eb}) are {how}. Net {{{', '.join(show[:6])}"
                  f"{'' if len(show) <= 6 else f', +{len(show) - 6} more'}}}")


def _missing(res: Result, ref: str, comp, undrawn: dict, unplaced: dict, kind: str):
    """A netlist element with no symbol: declared (report) or a finding."""
    ends = f"{comp.nodes[0]}<->{comp.nodes[1]}" if comp.kind != "X" else \
           ", ".join(f"{r}={n}" for r, n in sorted(comp.roles.items()))
    if ref in undrawn:
        res.info.append(f"{ref} not drawn — {undrawn[ref]} "
                        f"(sch_map.netlist_undrawn)")
    elif ref in unplaced:
        res.info.append(f"{ref} not drawn — {unplaced[ref]} "
                        f"(reused from layout net_map.netlist_unplaced)")
    else:
        _bump(res, "MISSING SYMBOL",
              f"netlist {kind} {ref} ({ends}) has no symbol on the sheet and is "
              f"declared in neither sch_map.netlist_undrawn nor layout "
              f"net_map.netlist_unplaced")


def _node_expectation(node: str, comps, tube_terms: dict, part_terms: dict):
    """What the netlist says must sit on `node`, as (fixed, pairs).

    `fixed`  terminals pinned exactly — a tube pin IS its role, so `V1A.3` is
             the cathode and nothing else.
    `pairs`  (ref, term_a, term_b) for a two-terminal part of which EXACTLY ONE
             end must land on the node. Which end is NOT determined: a
             resistor's two terminals are interchangeable, and `cx:C` carries no
             polarity marks, so netlist node ORDER says nothing about pin
             numbers. Treating a pair as ordered would flag every part a drawing
             happens to letter the other way up. (If polarity is ever drawn on
             electrolytics, this is the assumption to revisit.)"""
    fixed: set = set()
    pairs: list = []
    for c in comps:
        if c.kind == "X" and id(c) in tube_terms:
            for role, term in tube_terms[id(c)].items():
                if c.roles.get(role) == node:
                    fixed.add(term)
        elif c.kind in ("R", "C", "L") and c.ref in part_terms:
            ta, tb = part_terms[c.ref]
            if c.nodes[0] == node and c.nodes[1] == node:
                fixed.update((ta, tb))       # a netlist short: both ends on it
            elif node in c.nodes:
                pairs.append((c.ref, ta, tb))
    return fixed, pairs


def _node_terminals(node: str, comps, tube_terms: dict, part_terms: dict) -> set:
    """Every modelled terminal the netlist puts on `node`, orientation ignored —
    for narrative only ("the netlist puts these on it"), never for a diff."""
    fixed, pairs = _node_expectation(node, comps, tube_terms, part_terms)
    out = set(fixed)
    for ref, ta, tb in pairs:
        out.add(f"{ref}(either end)")
    return out


def _scope(res, G, comps, tube_terms, part_terms, modelled_terms, mem, M,
           net_map, undrawn, unplaced):
    """State what is NOT proven, out loud."""
    n_sym = len(G.nets.pins)
    n_mod = len({t.rpartition('.')[0] for t in modelled_terms})
    res.scope.append(f"symbols on the sheet: {n_sym}; carrying a netlist element: "
                     f"{n_mod}; DC-checked terminals: {len(modelled_terms)}")
    res.scope.append(f"netlist elements: "
                     f"{sum(1 for c in comps if c.kind in ('R', 'C', 'L'))} passive, "
                     f"{sum(1 for c in comps if c.kind == 'X')} tube sections, "
                     f"{sum(1 for c in comps if c.kind in ('V', 'I'))} ideal source(s) "
                     f"(the PS front end — PT + rectifier + reservoir — is not drawn "
                     f"as a netlist element)")
    excl = net_map.get("excluded_tubes") or {}
    for sid, why in sorted(excl.items()):
        res.scope.append(f"tube {sid} DECLARED EXCLUDED from the netlist "
                         f"(layout net_map.excluded_tubes): {why} — its drawn "
                         f"wiring is NOT DC-checked")
    # every symbol the netlist does not model, tagged, grouped by symbol class
    buckets: dict = {}
    for ref in sorted(G.nets.pins):
        pins = G.nets.pins[ref]
        if all(f"{ref}.{n}" in modelled_terms for n in pins):
            continue
        unchecked = [f"{ref}.{n}" for n in sorted(pins)
                     if f"{ref}.{n}" not in modelled_terms]
        lib = G.lib.get(ref, "?").replace("cx:", "")
        buckets.setdefault(lib, []).append((ref, unchecked))
    for lib in sorted(buckets):
        items = buckets[lib]
        n_t = sum(len(u) for _r, u in items)
        res.scope.append(f"{lib}: {len(items)} symbol(s), {n_t} terminal(s) not "
                         f"DC-checked (the netlist models no element there) — "
                         f"{', '.join(r for r, _u in items)}")


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def print_result(res: Result, report: bool = False):
    verdict = "PASS" if res.ok else "FAIL"
    claim = "CLAIMED" if res.claim else "report-only"
    head = f"{verdict}  {res.amp_id}  ({claim})"
    if res.classes:
        head += "  " + " ".join(f"{k}={v}" for k, v in sorted(res.classes.items()))
    print(head)
    for e in res.errors:
        print(f"    - {e}")
    if report:
        for i in res.info:
            print(f"    . declared: {i}")
        for s in res.scope:
            print(f"    ~ scope: {s}")


def _print_polarity_summary(polarity: list):
    """Every run says how many sheet diodes the DC model decided, and names the
    ones it did not: a polarity nobody checked is never silent."""
    by: dict = {"confirmed": [], "REVERSED": [], "unchecked": []}
    for amp, p in polarity:
        by[p["verdict"]].append((amp, p))
    print(f"rectifier polarity: {len(polarity)} sheet diode(s); "
          f"{len(by['confirmed'])} confirmed by the DC model, "
          f"{len(by['REVERSED'])} REVERSED, {len(by['unchecked'])} not checked")
    reasons: dict = {}
    for amp, p in by["unchecked"]:
        reasons.setdefault(p["why"], []).append(f"{amp} {p['ref']}")
    for why, items in sorted(reasons.items()):
        print(f"  polarity not checked ({why}): {len(items)} — {', '.join(items)}")


def _print_feed_summary(polarity: list):
    """How many sheet rectifiers a winding was proven to feed, and which were
    not checked: never silent."""
    fs = [(amp, p["feed"]) for amp, p in polarity if p.get("feed")]
    unfed = [(a, f) for a, f in fs if f["verdict"] == "UNFED"]
    n_fed = sum(1 for _a, f in fs if f["verdict"] == "fed")
    cov = [f"{a} {f['ref']}" for a, f in fs if f["verdict"] == "covered"]
    unc = [f"{a} {f['ref']}" for a, f in fs if f["verdict"] == "unchecked"]
    print(f"rectifier feed: {n_fed + len(unfed)} sheet rectifier(s) the model gives "
          f"a role; {n_fed} fed, {len(unfed)} UNFED; {len(cov)} more walked as part "
          f"of a stack or bridge, {len(unc)} not checked")
    if unc:
        print(f"  feed not checked (no role, no stack- or bridge-mate with one): "
              f"{len(unc)} — {', '.join(unc)}")


def analyze(amp_id: str) -> int:
    """Dump the solved node <-> net mapping for one sheet, node by node — the
    view a fixer works from: what the netlist puts on a node, what the drawing
    actually puts there, and the difference."""
    res = check_amp(amp_id)
    print(f"=== {amp_id} ===")
    print_result(res, report=True)
    print("    per-node membership (netlist node: drawn | missing | unexpected)")
    for node in sorted(res.node_diff):
        drawn, missing, absent, extra = res.node_diff[node]
        flag = "  ok" if not (missing or absent or extra) else "  **"
        line = f"{flag} {node:<8} {', '.join(drawn) or '(nothing drawn)'}"
        if missing:
            line += f"   MISSING {', '.join(missing)}"
        if absent:
            line += f"   NEITHER-END {', '.join(absent)}"
        if extra:
            line += f"   UNEXPECTED {', '.join(extra)}"
        print("    " + line)
    return 0 if res.ok else 1


# ---------------------------------------------------------------------------
# planted-fault self-test
# ---------------------------------------------------------------------------
_WIRE_RE = re.compile(
    r"\(wire \(pts \(xy (-?[\d.]+) (-?[\d.]+)\) \(xy (-?[\d.]+) (-?[\d.]+)\)\)")


def _wires(text: str) -> list:
    """[(match, x1, y1, x2, y2)] for every wire in a .kicad_sch's text."""
    return [(m, float(m.group(1)), float(m.group(2)),
             float(m.group(3)), float(m.group(4))) for m in _WIRE_RE.finditer(text)]


def _near(a: float, b: float) -> bool:
    return abs(a - b) < 1e-3


def _move_wire_end(text: str, at: tuple, to: tuple) -> str:
    """Move the first wire endpoint sitting at `at` to `to`. Plants the
    'a wire lands on the wrong pin' fault."""
    for m, x1, y1, x2, y2 in _wires(text):
        if _near(x1, at[0]) and _near(y1, at[1]):
            new = f"(wire (pts (xy {to[0]:g} {to[1]:g}) (xy {x2:g} {y2:g}))"
            return text[:m.start()] + new + text[m.end():]
        if _near(x2, at[0]) and _near(y2, at[1]):
            new = f"(wire (pts (xy {x1:g} {y1:g}) (xy {to[0]:g} {to[1]:g}))"
            return text[:m.start()] + new + text[m.end():]
    raise AssertionError(f"self-test: no wire endpoint at {at}")


def _delete_wire(text: str, at: tuple) -> str:
    """Delete the first wire touching `at`. Plants the 'a join is missing' fault.
    A wire is two lines: the (wire (pts ...) line and its stroke/uuid line."""
    for m, x1, y1, x2, y2 in _wires(text):
        if (_near(x1, at[0]) and _near(y1, at[1])) or (_near(x2, at[0]) and _near(y2, at[1])):
            start = text.rfind("\n", 0, m.start()) + 1
            end = text.find("\n", text.find("(uuid", m.end()))
            return text[:start] + text[end + 1:]
    raise AssertionError(f"self-test: no wire at {at}")


def _pin_xy(amp_id: str, ref: str, num: str) -> tuple:
    n = Nets(AMPS / amp_id / "schematic.kicad_sch")
    return n.pins[ref][num]


_AT_RE = re.compile(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)")


def _flip_symbol(text: str, ref: str) -> str:
    """Turn the placed symbol lettered `ref` through 180 degrees about its own
    origin, every wire left where it was. A cx:DIODE_SS carries its pins at
    -5.08 and +5.08 on one axis, so this swaps the points the anode and the
    cathode land on: exactly the part drawn the other way round, the fault
    class the polarity check exists for. An edit to the regenerated file."""
    i = text.find(f'(property "Reference" "{ref}"')
    if i < 0:
        raise AssertionError(f"self-test: no symbol lettered {ref}")
    s = text.rfind("(symbol (lib_id", 0, i)
    m = _AT_RE.search(text, s, i)
    ang = (float(m.group(3) or 0) + 180) % 360
    return text[:m.start()] + f"(at {m.group(1)} {m.group(2)} {ang:g})" + text[m.end():]


def _plant_diode(text: str, ref: str, anode_label: str, cathode_label: str,
                 at: tuple = (900.0, 900.0)) -> str:
    """Add a cx:DIODE_SS lettered `ref` far off the drawing, its anode pin on a
    global label `anode_label` and its cathode pin on `cathode_label`: a diode
    joined to two existing nets by name alone, the way a sheet ties a part to a
    rail. The sheet must already carry the symbol in lib_symbols."""
    x, y = at

    def uid(n):
        return f"00000000-0000-4000-8000-{n:012d}"
    block = (f'  (symbol (lib_id "{DIODE_LIB}") (at {x:g} {y:g} 0) (unit 1)\n'
             f'    (in_bom yes) (on_board yes) (uuid "{uid(1)}")\n'
             f'    (property "Reference" "{ref}" (at {x:g} {y - 3:g} 0) '
             f'(effects (font (size 1.27 1.27))))\n'
             f'    (property "Value" "planted" (at {x:g} {y + 3:g} 0) '
             f'(effects (font (size 1.27 1.27)))))\n')
    for n, (name, px) in enumerate(((anode_label, x - 5.08),
                                    (cathode_label, x + 5.08)), 2):
        block += (f'  (global_label "{name}" (shape input) (at {px:g} {y:g} 0)\n'
                  f'    (effects (font (size 1.27 1.27)) (justify left)) '
                  f'(uuid "{uid(n)}"))\n')
    i = text.index("  (symbol (lib_id")
    return text[:i] + block + text[i:]


def selftest() -> int:
    """A gate that cannot catch a planted fault is decoration.

    Every sheet in the corpus currently has real findings (that is why this gate
    exists), so a mutation cannot be scored as "clean before, failing after".
    It is scored on the DELTA instead, which is the stronger assertion anyway:
    the fault must add a NEW finding of the expected class naming the mutated
    designator, and must not silently remove an existing one. When a sheet does
    go green, the same assertions still hold and the baseline line prints PASS.
    """
    cases = [
        # (amp, label, expected classes, mutation)
        ("5f1", "V1B cathode wire moved onto the V1B PLATE pin "
                "(the phase-inverter fault class, §1.3)",
         {"MERGED", "SPLIT", "WRONG TERMINAL", "UNMAPPED", "NODE MISMATCH"},
         lambda t: _move_wire_end(t, _pin_xy("5f1", "V1B", "3"),
                                  _pin_xy("5f1", "V1B", "1")),
         "V1B"),
        ("5f1", "the wire joining the 6V6 grid leak R9 to the grid deleted "
                "(the dangling-pin fault class, §1.4)",
         {"SPLIT", "UNMAPPED", "NODE MISMATCH", "UNREALISED"},
         lambda t: _delete_wire(t, _pin_xy("5f1", "R9", "1")),
         "R9"),
        ("5e1", "V1A plate wire moved onto the V1A GRID pin",
         {"MERGED", "SPLIT", "WRONG TERMINAL", "UNMAPPED", "NODE MISMATCH"},
         lambda t: _move_wire_end(t, _pin_xy("5e1", "V1A", "1"),
                                  _pin_xy("5e1", "V1A", "2")),
         "V1A"),
        ("jtm45", "the cathode-resistor wire at V1A deleted",
         {"SPLIT", "UNMAPPED", "NODE MISMATCH", "UNREALISED"},
         lambda t: _delete_wire(t, _pin_xy("jtm45", "V1A", "3")),
         "V1A"),
    ]
    fails: list[str] = []
    n_cases = 0
    print("=== baselines (the corpus is not green yet — deltas are what count) ===")
    base: dict = {}
    for amp in sorted({c[0] for c in cases}):
        r = check_amp(amp)
        base[amp] = set(r.errors)
        print(f"  {amp}: {'PASS' if r.ok else f'{len(r.errors)} existing finding(s)'}")

    print("=== planted faults ===")
    tmp = Path(tempfile.mkdtemp(prefix="cx-schnets-"))
    try:
        for amp, label, want_classes, mutate, needle in cases:
            src = AMPS / amp / "schematic.kicad_sch"
            text = mutate(src.read_text())
            dst = tmp / f"{amp}.kicad_sch"
            dst.write_text(text)
            r = check_amp(amp, sch_path=dst)
            n_cases += 1
            new = set(r.errors) - base[amp]
            # A planted fault must never make the gate say LESS overall. Judged
            # on the TOTAL, not per class and not on exact text: a fault can
            # legitimately restate an existing finding under another class (a
            # short can break the propagation that had exposed a split) and it
            # rewrites the member lists printed inside unrelated findings.
            lost = ([f"total fell {len(base[amp])} -> {len(r.errors)}"]
                    if len(r.errors) < len(base[amp]) else [])
            hit = sorted(e for e in new
                         if e.split(":")[0] in want_classes and needle in e)
            caught = bool(hit)
            print(f"  [{amp}] {'CAUGHT' if caught else 'MISSED'}: {label}")
            if caught:
                print(f"          -> {hit[0][:160]}")
            else:
                fails.append(f"{amp}: {label}")
                for e in sorted(new)[:3]:
                    print(f"          (new, not matched) {e[:140]}")
            if lost:
                fails.append(f"{amp}: mutation REMOVED findings of class "
                             f"{', '.join(sorted(lost))}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== declaration hygiene ===")
    # EVERY kind of sch_map declaration must name its own staleness. Before this
    # was uniform, a stale `symbols` target degraded into the redirected
    # element's MISSING SYMBOL, which points at the wrong thing: it says the
    # element is undrawn when the element is on the sheet under its own name and
    # the obsolete redirect is what hid it (a fixer renaming ab763's V1 to V1A
    # lost a debug cycle to exactly this).
    hygiene = [
        ("anchors", {"anchors": {"NOPE.9": "BP1"}}, "sch_map.anchors[NOPE.9]"),
        ("series_bridge", {"series_bridge": {"NOSUCH": "not a real part"}},
         "sch_map.series_bridge[NOSUCH]"),
        ("element_pins", {"element_pins": {"R9": ["NOPE.1", "NOPE.2"]}},
         "sch_map.element_pins[R9]"),
        ("symbols -> nothing", {"symbols": {"R9": "NOSUCH"}},
         "sch_map.symbols[R9] -> NOSUCH"),
        ("winding_labels", {"winding_labels": {"NOSUCH": "ht_a"}},
         "sch_map.winding_labels[NOSUCH]"),
        # The reported bug, exactly: the target was renamed away, and the netlist
        # element IS on the sheet under its own designator.
        ("symbols -> renamed away", {"symbols": {"V1A": "V1"}},
         "sch_map.symbols[V1A] -> V1"),
    ]
    for label, sm, needle in hygiene:
        r = check_amp("5f1", sch_map=sm)
        n_cases += 1
        hit = [e for e in r.errors
               if e.startswith("STALE DECLARATION") and needle in e]
        print(f"  stale {label:22s} {'REPORTED' if hit else 'MISSED'}")
        if hit:
            print(f"      -> {hit[0][:150]}")
        else:
            fails.append(f"a stale sch_map {label} declaration was not reported")
    # The renamed-away case must ALSO say the element is on the sheet under its
    # own name, and must NOT mis-report it as an undrawn tube.
    r = check_amp("5f1", sch_map={"symbols": {"V1A": "V1"}})
    guided = any("does letter a symbol 'V1A'" in e for e in r.errors)
    misled = any(e.startswith("MISSING SYMBOL") and "V1A" in e for e in r.errors)
    n_cases += 2
    print(f"  renamed-away hint given: {'YES' if guided else 'NO'}; "
          f"mis-reported as MISSING SYMBOL: {'YES' if misled else 'NO'}")
    if not guided:
        fails.append("the stale symbols finding does not point at the real symbol")
    if misled:
        fails.append("a stale symbols target still degrades to MISSING SYMBOL")
    # A layout-sourced declaration that does not apply to a sheet is scope, not
    # a finding: it was written about a board and may have no counterpart here.
    r = check_amp("5f1")
    n_cases += 1
    if any(e.startswith("STALE DECLARATION") for e in r.errors):
        fails.append("a reused layout declaration was reported as stale sch_map data")

    n_pol = _selftest_polarity(fails)
    n_win = _selftest_windings(fails)
    n_feed = _selftest_feeds(fails)
    n_cases += n_pol + n_win + n_feed
    for f in fails:
        print(f"  !! {f}")
    print(f"self-test: {'PASS' if not fails else 'FAIL'} ({n_cases} cases: "
          f"{n_pol} rectifier polarity, {n_win} shorted winding, "
          f"{n_feed} rectifier feed)")
    return 1 if fails else 0


_GLABEL_AT = (r'\(global_label "{name}" \(shape [^)]*\) '
              r'\(at (-?[\d.]+) (-?[\d.]+)( -?[\d.]+)?\)')


def _move_label(text: str, name: str, near: tuple, dy: float = -300.0) -> str:
    """Move the anchor of the global label `name` that sits nearest `near` off
    its wire (by `dy` mm, clear of the drawing), so the name no longer reaches
    what that wire joins. The 6G5 at e4e59fa had exactly this: HT_A/HT_B labels
    that stopped 6 mm short of the rectifier's wires."""
    pat = re.compile(_GLABEL_AT.format(name=re.escape(name)))
    found = [(abs(float(m.group(1)) - near[0]) + abs(float(m.group(2)) - near[1]), m)
             for m in pat.finditer(text)]
    if not found:
        raise AssertionError(f"self-test: no global label {name!r}")
    m = min(found, key=lambda dm: dm[0])[1]
    head = m.group(0)[:m.group(0).rfind("(at ")]
    at = f"(at {m.group(1)} {float(m.group(2)) + dy:g}{m.group(3) or ''})"
    return text[:m.start()] + head + at + text[m.end():]


def _selftest_feeds(fails: list) -> int:
    """UNFED RECTIFIER must bite on a rectifier cut off from its winding, and
    read fed, with the walk shown, on rectifiers fed as drawn. Returns the
    case count."""
    n = 0
    print("=== rectifier feed: planted faults (edits to temp copies of the "
          "regenerated .kicad_sch) ===")
    planted = [
        ("6g5", "6G5: the HT_A label at the rectifier leg moved off its wire (the "
                "base sheet's fault: labels stopped short of the diodes' wires)",
         lambda t: _move_label(t, "HT_A", _pin_xy("6g5", "D1", DIODE_PINS["anode"])),
         "D3 (HT rectifier"),
        ("6g5", "6G5: the HT_A label at the transformer moved off its wire, so the "
                "leg's HT_A names a pin it never reaches",
         lambda t: _move_label(t, "HT_A", _pin_xy("6g5", "TR1", "3")),
         "D3 (HT rectifier"),
        ("5f4", "5F4: the bias rectifier cut off from its tap (the HT_TAP label at "
                "RB1 moved off its wire)",
         lambda t: _move_label(t, "HT_TAP", _pin_xy("5f4", "RB1", "1")),
         "D1 (bias rectifier"),
    ]
    tmp = Path(tempfile.mkdtemp(prefix="cx-schfeed-"))
    try:
        for amp, label, mutate, needle in planted:
            base = check_amp(amp)
            dst = tmp / f"{amp}.kicad_sch"
            dst.write_text(mutate((AMPS / amp / "schematic.kicad_sch").read_text()))
            r = check_amp(amp, sch_path=dst)
            n += 1
            new = set(r.errors) - set(base.errors)
            hit = [e for e in new if e.startswith("UNFED RECTIFIER") and needle in e]
            print(f"  {'CAUGHT' if hit else 'MISSED'}: {label}")
            if hit:
                print(f"          -> {hit[0][:170]}")
            else:
                fails.append(f"rectifier feed: {label} was not reported")
                for e in sorted(new)[:3]:
                    print(f"          (new, not matched) {e[:140]}")
            if len(r.errors) < len(base.errors):
                fails.append(f"rectifier feed: {label} REMOVED findings")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== rectifier feed: fed as drawn ===")
    for amp, ref, want, label in (
            ("6g5", "D3", "fed", "6G5 HT leg A, through D2 and D1 to TR1's HT_A pin"),
            ("6g5", "D1", "covered", "6G5 D1, no role of its own, walked as part "
                                     "of D3's leg"),
            ("6g5", "DBIAS", "fed", "6G5 bias rectifier, from TR1's tap pin"),
            ("5f4", "D1", "fed", "5F4 bias rectifier, through RB1 to T1's tap pin"),
            ("jtm45", "D1", "fed", "JTM45 bias rectifier, from the declared HT_B "
                                   "label (the sheet draws no transformer)"),
            ("ab763-twin", "DBIAS", "fed", "AB763-Twin bias rectifier, from the "
                                           "declared BIAS TAP label, a tap its "
                                           "transformer symbol lacks")):
        r = check_amp(amp)
        n += 1
        p = next((q for q in r.polarity if q["ref"] == ref), {})
        f = p.get("feed") or {}
        got = f.get("verdict", "absent")
        print(f"  {'OK    ' if got == want else 'WRONG '} {label}: {got}")
        if f.get("why"):
            print(f"          -> {f['why'][:170]}")
        if got != want:
            fails.append(f"rectifier feed: {amp} {ref} should be {want}, got {got}")

    print("=== rectifier feed: winding labels are declared, never inferred ===")
    decl_cases = [
        ("jtm45", "JTM45 with its winding_labels declaration removed: the HT_B "
                  "label no longer counts", "winding_labels", None,
         ("UNFED RECTIFIER", "D1 (bias rectifier")),
        ("6g5", "6G5 declaring HT_A: ht_a, a terminal its transformer draws as a "
                "pin", "winding_labels", {"HT_A": "ht_a"},
         ("STALE DECLARATION", "winding_labels[HT_A]")),
    ]
    for amp, label, key, value, (cls, needle) in decl_cases:
        sm = {k: v for k, v in load_sch_map(amp).items() if k != key}
        if value is not None:
            sm[key] = value
        base = check_amp(amp)
        r = check_amp(amp, sch_map=sm)
        n += 1
        new = set(r.errors) - set(base.errors)
        hit = [e for e in new if e.startswith(cls) and needle in e]
        print(f"  {'CAUGHT' if hit else 'MISSED'}: {label}")
        if hit:
            print(f"          -> {hit[0][:170]}")
        else:
            fails.append(f"rectifier feed: {label} was not reported")
    return n


def _add_wire(text: str, a: tuple, b: tuple) -> str:
    """Add one wire from point `a` to point `b`: the 'a wire joins a winding's
    two ends' fault (the 5F1's OT primary, 2026-09-10)."""
    w = (f'  (wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g}))\n'
         f'    (stroke (width 0) (type default)) '
         f'(uuid "00000000-0000-4000-8000-0000000000aa"))\n')
    i = text.index("  (symbol (lib_id")
    return text[:i] + w + text[i:]


def _rename_label(text: str, old: str, new: str) -> str:
    """Letter every global label `old` as `new`: two leads given one name are
    one net, the fault 16 power transformers carried on 2026-09-10."""
    if f'(global_label "{old}"' not in text:
        raise AssertionError(f"self-test: no global label {old!r}")
    return text.replace(f'(global_label "{old}"', f'(global_label "{new}"')


def _winding_pin(amp: str, lib: str, name: str) -> tuple:
    """(ref, point) of the pin called `name` on the first `lib` symbol."""
    G = SchGraph(AMPS / amp / "schematic.kicad_sch")
    ref = sorted(r for r, lid in G.lib.items() if lid == lib)[0]
    return ref, G.nets.pins[ref][_pin_numbers(G)[lib][name]]


def _selftest_windings(fails: list) -> int:
    """SHORTED WINDING must bite on a wire across a winding, a wire from a
    centre tap to one end, and two leads lettered alike (directly, and through
    a switch and fuse), and must stay quiet on the same sheets as committed.
    Returns the case count."""
    n = 0
    print("=== shorted windings: planted faults (edits to temp copies of the "
          "regenerated .kicad_sch) ===")
    ot, pa = _winding_pin("5e3", "cx:OT_PP", "PRI_A")
    _r, pb = _winding_pin("5e3", "cx:OT_PP", "PRI_B")
    _r, ct = _winding_pin("5e3", "cx:OT_PP", "CT")
    planted = [
        ("5e3", f"5E3 OT {ot}: a wire from one primary end to the other "
                f"(the 5F1's fault)", lambda t: _add_wire(t, pa, pb),
         f"{ot}'s primary is shorted"),
        ("5e3", f"5E3 OT {ot}: a wire from the centre tap to one plate end",
         lambda t: _add_wire(t, ct, pa), f"{ot}'s primary's A half is shorted"),
        ("ac15", "AC15: the neutral's label lettered MAINS L like the line's (the "
                 "loop closes through the power switch and fuse)",
         lambda t: _rename_label(t, "MAINS N", "MAINS L"), "T1's primary is shorted"),
        ("5f4", "5F4: both primary leads lettered MAINS (the fault of 2026-09-10)",
         lambda t: _rename_label(t, "MAINS N", "MAINS"), "T1's primary is shorted"),
    ]
    tmp = Path(tempfile.mkdtemp(prefix="cx-schwind-"))
    try:
        for amp, label, mutate, needle in planted:
            base = check_amp(amp)
            dst = tmp / f"{amp}.kicad_sch"
            dst.write_text(mutate((AMPS / amp / "schematic.kicad_sch").read_text()))
            r = check_amp(amp, sch_path=dst)
            n += 1
            new = set(r.errors) - set(base.errors)
            hit = [e for e in new if e.startswith("SHORTED WINDING") and needle in e]
            print(f"  {'CAUGHT' if hit else 'MISSED'}: {label}")
            if hit:
                print(f"          -> {hit[0][:170]}")
            else:
                fails.append(f"shorted winding: {label} was not reported")
                for e in sorted(new)[:3]:
                    print(f"          (new, not matched) {e[:140]}")
            if len(r.errors) < len(base.errors):
                fails.append(f"shorted winding: {label} REMOVED findings")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== shorted windings: drawn right ===")
    for amp, label in (
            ("5e3", "5E3 as committed: OT centre tap on B+ between two plate ends"),
            ("ac15", "AC15 as committed: MAINS L and MAINS N, through switch and fuse"),
            ("5f4", "5F4 as committed: MAINS and MAINS N, HT centre tap on ground")):
        r = check_amp(amp)
        n += 1
        bad = [e for e in r.errors if e.startswith("SHORTED WINDING")]
        print(f"  {'OK    ' if not bad else 'WRONG '} {label}"
              + (f": {bad[0][:120]}" if bad else ""))
        if bad:
            fails.append(f"shorted winding: {amp} as committed was flagged")
    return n


def _selftest_polarity(fails: list) -> int:
    """REVERSED DIODE must bite on the three ways a diode goes wrong, and must
    confirm, not merely tolerate, diodes drawn right. Returns the case count."""
    n = 0
    print("=== rectifier polarity: the rule, one row per clause, both ways ===")
    rows = [
        # (anode V, cathode V, expected verdict, label)
        (None, -40.0, "REVERSED", "cathode on a negative supply"),
        (-40.0, None, "confirmed", "anode on a negative supply"),
        (415.0, None, "REVERSED", "anode on B+"),
        (None, 415.0, "confirmed", "cathode on B+"),
        (1.5, 0.0, "REVERSED", "forward-biased between two modelled nodes, "
                               "neither threshold crossed (the third clause alone)"),
        (0.0, 1.5, "confirmed", "the same pair, reverse-biased"),
        (0.0, None, "unchecked", "anode on ground, cathode off the model"),
        (None, None, "unchecked", "no terminal on a modelled node"),
    ]
    for va, vk, want, label in rows:
        vs: dict = {}
        a, k = ("X.1", None), ("X.2", None)
        if va is not None:
            vs["NA"], a = (va, "synthetic"), ("X.1", "NA")
        if vk is not None:
            vs["NK"], k = (vk, "synthetic"), ("X.2", "NK")
        got = judge_diode("X", a, k, vs)["verdict"]
        n += 1
        print(f"  {'OK    ' if got == want else 'WRONG '} {label}: {got}")
        if got != want:
            fails.append(f"polarity rule: {label} gave {got}, want {want}")

    print("=== rectifier polarity: planted faults (edits to temp copies of the "
          "regenerated .kicad_sch) ===")
    planted = [
        ("5f4", "5F4 bias rectifier D1 turned through 180 degrees, cathode onto "
                "the -40 V supply", lambda t: _flip_symbol(t, "D1"), "D1",
         ("cathode on",)),
        ("ab763-twin", "AB763-Twin HT rectifier DHTA turned through 180 degrees, "
                       "anode onto B+", lambda t: _flip_symbol(t, "DHTA"), "DHTA",
         ("anode on",)),
        ("5f4", "a diode planted forward from <B+1> to <GND>",
         lambda t: _plant_diode(t, "DPLANT", "B+1", GND_LABEL), "DPLANT",
         ("anode on", "forward-biased")),
    ]
    tmp = Path(tempfile.mkdtemp(prefix="cx-schpol-"))
    try:
        for amp, label, mutate, ref, needles in planted:
            base = check_amp(amp)
            dst = tmp / f"{amp}.kicad_sch"
            dst.write_text(mutate((AMPS / amp / "schematic.kicad_sch").read_text()))
            r = check_amp(amp, sch_path=dst)
            n += 1
            new = set(r.errors) - set(base.errors)
            hit = [e for e in new if e.startswith("REVERSED DIODE")
                   and f"{ref} is drawn" in e and all(x in e for x in needles)]
            print(f"  {'CAUGHT' if hit else 'MISSED'}: {label}")
            if hit:
                print(f"          -> {hit[0][:170]}")
            else:
                fails.append(f"polarity: {label} was not reported REVERSED")
            if len(r.errors) < len(base.errors):
                fails.append(f"polarity: {label} REMOVED findings")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== rectifier polarity: drawn right, and decided by the model ===")
    for amp, ref, label in (
            ("aa1164", "DB1", "AA1164 bias rectifier, anode on the -34 V supply"),
            ("ab165", "D1", "AB165 HT rectifier, cathode on B+ through the "
                            "standby switch and choke"),
            ("5f4", "D1", "5F4 bias rectifier as committed (the flip above "
                          "starts from a confirmed part)"),
            ("ab763-twin", "DHTA", "AB763-Twin HT rectifier as committed")):
        r = check_amp(amp)
        n += 1
        p = next((q for q in r.polarity if q["ref"] == ref), None)
        got = p["verdict"] if p else "absent"
        print(f"  {'OK    ' if got == 'confirmed' else 'WRONG '} {label}: {got}")
        if p:
            print(f"          -> {p['desc'][:170]}")
        if got != "confirmed":
            fails.append(f"polarity: {amp} {ref} should be confirmed, got {got}")
    return n


# ---------------------------------------------------------------------------
# cli
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    report = "--report" in argv
    strict = "--strict" in argv
    if "--analyze" in argv:
        i = argv.index("--analyze")
        return analyze(argv[i + 1])
    ids = [a for a in argv if not a.startswith("-")] or amp_ids()

    print("schematic <-> netlist equivalence")
    print("  the netlist is a DC model: it omits the PS front end, transformer")
    print("  winding DCR and the pot/tone/mixer control networks, so the sheet is")
    print("  proven isomorphic to it ONLY over what it models. Everything else is")
    print("  enumerated below as not DC-checked, never assumed correct.")
    print()
    failed_claimed, failed_any, totals = [], [], {}
    polarity: list = []
    for amp in ids:
        res = check_amp(amp)
        polarity.extend((amp, p) for p in res.polarity)
        print_result(res, report=report)
        for k, v in res.classes.items():
            totals[k] = totals.get(k, 0) + v
        if not res.ok:
            failed_any.append(amp)
            if res.claim:
                failed_claimed.append(amp)
    print()
    print(f"{len(ids)} sheet(s); {len(ids) - len(failed_any)} clean, "
          f"{len(failed_any)} with findings")
    if totals:
        print("findings by class: " +
              ", ".join(f"{k}={v}" for k, v in sorted(totals.items())))
    _print_polarity_summary(polarity)
    _print_feed_summary(polarity)
    if failed_claimed:
        print(f"GATE FAIL — claimed sheets with findings: {', '.join(failed_claimed)}")
        return 1
    if strict and failed_any:
        print(f"GATE FAIL (--strict) — sheets with findings: {', '.join(failed_any)}")
        return 1
    if failed_any:
        print("report-only: the findings above are all on sheets that do not yet carry "
              "sch_map `schematic_claim: verified`, so nothing fails CI. A sheet earns "
              "the claim by going clean first.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
