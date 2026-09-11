#!/usr/bin/env python3
"""CI gate: the schematic and the board layout draw the SAME circuit, part for
part — proven against each other, with no netlist in the loop.

------------------------------------------------------------------------------
WHY A THIRD EQUIVALENCE GATE
------------------------------------------------------------------------------
`verify_layout_nets.py` proves the board against `netlist.cir`;
`verify_schematic_nets.py` proves the sheet against the same netlist. Both are
bounded by what the netlist MODELS, and the netlist is a DC operating-point
model: 1,280 of the corpus's ~2,300 BOM passives — every coupling, tone, filter
and bypass cap with a lead inside an abstracted network, every pot end, the bias
front end, the reverb and tremolo networks — have no netlist element, so both
gates skip them BY CONSTRUCTION and say so in their scope lines. A drawing
fault among those parts is invisible to CI.

The schematic (`pipeline/draw_<id>.py`) and the board (`amps/<id>/layout.yaml`)
are authored independently, so their net partitions are each other's witness:
two drawings of one circuit that disagree are wrong at least once, and the
disagreement names the part. This gate builds the sheet's nets (`sch_nets`) and
the board's nets (`verify_layout_nets.LayoutGraph`), solves the mapping between
them from terminals both surfaces name, and reports every part on which the two
partitions differ. Nothing here says WHICH surface is right — that is a source
read — but it says exactly where to read.

------------------------------------------------------------------------------
HOW THE TWO PARTITIONS ARE COMPARED
------------------------------------------------------------------------------
Anchors — terminals that carry the SAME identity on both surfaces:
  ground         the sheet's <GND> label  <->  the board's ground bus
  tube pins      a sheet section's electrode  ->  a socket pin, through
                 reference/tubes basing (`schematic_lib.tube_pin_numbers`) and
                 the datasheet unit the sheet states for that section: the
                 symbol's `Basing_unit` property where the sheet carries one,
                 else the `unit=` the draw script states, else the default
                 letter->unit map (A -> unit 1). Heater and filament pins are
                 EXCLUDED — check_heaters.py owns them (a directly heated
                 rectifier's cathode IS its filament pair and is anchored
                 softly to either pin).
  pot wipers     VRn.2 <-> VRn.lug2 (the wiper is the one lug that is a lug on
                 both surfaces; the ends are compared unordered, below)
  jacks          cx:JACK pin 1 (T) <-> J.tip, pin 2 (S) <-> J.sleeve, for a
                 sheet jack whose reference is a board jack id. A board that
                 wires only the jack BODY (`J`) anchors the sheet's tip softly
                 to it and says so; the sleeve then anchors to nothing.
  declared       `net_map.leads` — a per-amp declaration mapping a sheet
                 terminal (`T2.1`, or a label such as `<TANK RET>`) to a board
                 terminal (`T2.blue`, `JTKO.tip`). Transformer leads carry
                 colours on the board and pin numbers on the sheet, and the
                 sheet's label vocabulary names NODES (B+1, HT_B, MIXG) while the
                 board's names HARDWARE, so neither can be matched by name: the
                 map is data the author writes, never a guess in code.

Two-terminal parts (R, C, diode, fuse, choke) and pot ends are UNORDERED pairs:
a resistor has no polarity on either drawing. Their nets are resolved from the
anchors by MAJORITY VOTING to a fixed point — every part with one net mapped
casts a vote for the other net's realisation, and a sheet net takes the strict
majority, so a lone dissenter is the misplaced part and not the poisoner of
everything on its net. A vote that would land a sheet net on a board net that
already realises a DIFFERENT sheet net is a merge the board draws that the
sheet does not: inferred MERGED when the majority says so, MISPLACED on the
single part when only it does.

A part declared DC-transparent (`series_bridge`, in the layout's net_map or the
sheet's sch_map.yaml) that the board does NOT place — a grid stopper soldered at
the socket lug — is a part the board's conductor runs THROUGH, so its two sheet
nets are compared as one; a bridged part the board does place is compared as a
part like any other.

Section <-> unit swaps are searched for, not assumed: for every dual-section
socket the sheet letters, the gate re-runs the comparison with that socket's
two units exchanged, and if the exchange removes at least two findings the
socket is reported ONCE as SECTION-SWAP instead of as its collateral (a swapped
phase inverter shows only as misplaced parts, never as a split among anchors).

Excluded, by explicit rule: heater/filament wiring and the pilot lamp
(check_heaters.py), everything on the sheet the board has no vocabulary for
(transformer symbols, switches, the mains inlet, the reverb tank) — each is
listed in the scope lines, never silently dropped.

------------------------------------------------------------------------------
WHAT IT REPORTS (one line per item, each a thing a fixer can act on)
------------------------------------------------------------------------------
  SECTION-SWAP    a socket whose sections the sheet letters on the opposite
                  datasheet unit to the board (one line per socket)
  SPLIT           anchored terminals on ONE sheet net drawn as >1 board net
  MERGED          anchored terminals on ONE board net drawn as >1 sheet net
  MISPLACED       a two-terminal part (or a pot's end pair) whose pair of nets
                  on the sheet is not its pair of nets on the board — both
                  surfaces' nets printed in canonical names, a dangling board
                  lead named as such
  UNRESOLVED      a two-terminal part neither of whose nets reaches an anchor
                  on either surface — NOT checked (add an anchor to check it)
  SHEET-ONLY      a part on the sheet the board neither places nor wires:
                  declared (net_map.netlist_unplaced / series_bridge /
                  not_on_board, or a scope.not_drawn rule) or UNDECLARED
  BOARD-ONLY      a part the board places that has no symbol on the sheet
  POT-AS-RESISTOR a control the sheet draws with the resistor symbol (cx:R on
                  a VR/RV designator, or on a reference the board places as a
                  pot) — the sheet has no wiper to anchor, so the control is
                  not compared until it is drawn as the pot it is
  STALE DECL.     a not_on_board entry, not_drawn rule or leads entry that
                  covers nothing
  POT-ORIENTATION information only: a pot whose CW end (lug 3) the sheet draws
                  at the bottom of its symbol — legal, recorded so a reader of
                  the sheet is not surprised by the board

Style and gate follow verify_layout_nets.py: per-amp PASS/FAIL with scope
lines, a committed worklist (`reference/sheet-board.yaml`, `--export`) that a
normal run is gated against for DRIFT like check_heaters.py's, and `--strict`
(exit 1 on any finding on an amp whose sch_map.yaml `schematic_claim` AND
layout.yaml `wiring_claim` are both `verified`). Findings do not fail the build
yet: the corpus was surveyed, not cleaned, when this gate landed, and `--strict`
enters CI once the worklist is clean for those amps.

    python3 pipeline/verify_sheet_vs_board.py            # every amp, + worklist drift gate
    python3 pipeline/verify_sheet_vs_board.py 5f6a       # one amp, with reasons
    python3 pipeline/verify_sheet_vs_board.py --report   # + scope lines for every amp
    python3 pipeline/verify_sheet_vs_board.py --strict   # exit 1 on findings on claimed amps
    python3 pipeline/verify_sheet_vs_board.py --export   # rewrite reference/sheet-board.yaml
    python3 pipeline/verify_sheet_vs_board.py --selftest # planted-fault mutation test
"""
from __future__ import annotations

import collections
import copy
import fnmatch
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_layouts import Renderer, load_bom, resolve_tube_slug          # noqa: E402
from schematic_lib import (UNIT_PROPERTY, _basing, _ref_section,          # noqa: E402
                           _section_letters, tube_pin_numbers)
from verify_layout_nets import GND, ROOT, LayoutGraph                     # noqa: E402
from verify_schematic_nets import SchGraph                                # noqa: E402

AMPS = ROOT / "amps"
PIPELINE = ROOT / "pipeline"
WORKLIST = ROOT / "reference" / "sheet-board.yaml"

# Symbol contracts, read off schematic_lib.LIB.
TUBE_LIBS = {"cx:TRIODE": "TRIODE", "cx:PENTODE": "PENTODE", "cx:DIODE_TUBE": "DIODE_TUBE"}
# Two-lead parts compared as unordered pairs. cx:LAMP is deliberately absent:
# the pilot lamp sits on the heater layer and check_heaters.py owns it.
TWO_TERM_LIBS = {"cx:R", "cx:C", "cx:DIODE_SS", "cx:FUSE", "cx:CHOKE"}
POT_LIB = "cx:POT"
JACK_LIB = "cx:JACK"
# cx:JACK pin 1 is named T (tip) and pin 2 S (sleeve) in schematic_lib.LIB;
# render_layouts.resolve() names a board jack's contacts `.tip` and `.sleeve`
# (`.ring` is drawn at the sleeve but is its own terminal, and no sheet symbol
# has a ring). A bare jack id on the board is the BODY — see sheet_terminals().
JACK_PIN_TERMINAL = {"1": "tip", "2": "sleeve"}
# schematic_lib.UNIT_PROPERTY ("Basing_unit") is the symbol property a generated
# sheet carries when its draw script states the datasheet unit a section draws.
# Read here so the gate reads the sheet, not the script; the script is the
# fallback for a sheet not yet regenerated to carry it.
_LABEL_RE = re.compile(r"^<.*>$")


# ===========================================================================
# the two surfaces, parsed once per amp
# ===========================================================================
class Sheet:
    """A parsed schematic plus what the comparison needs from it."""

    def __init__(self, amp_id: str, path: Path, draw_script: "Path | None"):
        self.amp_id = amp_id
        self.G = SchGraph(path)
        self.values: dict = {}          # reference -> Value
        self.units: dict = {}           # reference -> datasheet unit (stated)
        self.unit_source: dict = {}     # reference -> "sheet" | "draw script"
        self.pin_names: dict = {}       # lib_id -> {pin number: pin name}
        for lib in self.G.nets.sch.libSymbols:
            d = {}
            for u in lib.units:
                for pin in u.pins:
                    d[str(pin.number)] = str(pin.name)
            self.pin_names[lib.libId] = d
        for sym in self.G.nets.sch.schematicSymbols:
            ref = val = unit = None
            for prop in sym.properties:
                if prop.key == "Reference":
                    ref = prop.value
                elif prop.key == "Value":
                    val = prop.value
                elif prop.key == UNIT_PROPERTY:
                    unit = prop.value
            if ref is None:
                continue
            self.values.setdefault(ref, val)
            if unit is not None and ref not in self.units:
                self.units[ref] = _unit_token(unit)
                self.unit_source[ref] = "sheet"
        # Fallback: a sheet generated before Basing_unit existed does not carry
        # the unit its draw script states. Read the script, and say so.
        if draw_script is not None and draw_script.exists():
            for ref, unit in _script_units(draw_script).items():
                if ref not in self.units:
                    self.units[ref] = unit
                    self.unit_source[ref] = "draw script"
        self.bridged: dict = {}         # reference -> declaration source
        self.isolated = set(self.G.nets.isolated_pins())
        self.members = self.G.members()

    def term(self, name: str):
        return self.G.term(name)

    def apply_bridges(self, bd: "Board"):
        """A part declared DC-transparent (`series_bridge`, in the layout's
        net_map or the sheet's sch_map) that the board does NOT place is a part
        the board's conductor runs THROUGH — a grid stopper soldered at the
        socket lug is drawn on the sheet and is no board part. Its two sheet
        nets are one board net by declaration, so they are joined here before
        the comparison; a bridged part the board DOES place — as a two-lead
        part, an off-board stub, or a control whose lugs the board wires (the
        5G9's Depth pot) — is compared as a part like any other. Until
        2026-09-11 a placed pot read as "not placed" and was bridged, which
        folded its cold end into its wiper on the sheet side alone."""
        srcs = [("layout net_map.series_bridge", bd.net_map.get("series_bridge") or {}),
                ("sch_map.series_bridge", bd.sch_map.get("series_bridge") or {})]
        for src, entries in srcs:
            for ref in entries:
                ref = str(ref)
                if ref not in self.G.lib or bd.places(ref):
                    continue
                if self.G.join(f"{ref}.1", f"{ref}.2"):
                    self.bridged[ref] = src
        if self.bridged:
            self.isolated = set(self.G.nets.isolated_pins())
            self.members = self.G.members()


def _unit_token(text: str):
    """A stated unit as the basing files spell it: an int where it is one."""
    t = str(text).strip()
    return int(t) if t.isdigit() else t


def _script_units(path: Path) -> dict:
    out: dict = {}
    pat = re.compile(r'\.(triode|pentode|diode_tube)\(\s*"(V\w+)"\s*,\s*"[^"]+"'
                     r'[^)]*?unit\s*=\s*(\d+)')
    for m in pat.finditer(path.read_text()):
        out[m.group(2)] = int(m.group(3))
    return out


class Board:
    """A rendered layout's net graph plus what the comparison needs from it."""

    def __init__(self, amp_id: str, amp_dir: Path):
        self.amp_id = amp_id
        self.layout = yaml.safe_load((amp_dir / "layout.yaml").read_text()) or {}
        self.bom = load_bom(amp_dir)
        self.R = Renderer(copy.deepcopy(self.layout), self.bom, amp_id)
        self.LG = LayoutGraph(self.R)
        self.errors = list(self.R.errors) + list(self.LG.errors)
        self.terms: set = {m for ms in self.LG.nets().values() for m in ms}
        self.net_map: dict = self.layout.get("net_map") or {}
        sm = amp_dir / "sch_map.yaml"
        self.sch_map: dict = (yaml.safe_load(sm.read_text()) or {}) if sm.exists() else {}
        self.scope_rules: list = ((self.layout.get("scope") or {}).get("not_drawn") or [])
        # sheet reference -> board id, for off-board items whose id is not
        # their designator (a pot lettered VRP on the sheet is `id: VRP` on the
        # board, but an item may carry `ref:` under another id).
        self.id_of_ref: dict = {}
        self.kind_of_id: dict = {}
        for it in self.R.offboard:
            if "id" in it:
                self.kind_of_id[it["id"]] = it.get("kind")
                if it.get("ref"):
                    self.id_of_ref.setdefault(it["ref"], it["id"])
        self.part_refs: set = set(self.R.part_by_ref)
        self.offpart_ids: set = {it["id"] for it in self.R.offboard
                                 if it.get("kind") == "part" and "id" in it
                                 and it.get("glyph") != "lamp"}
        self.pot_ids: set = {it["id"] for it in self.R.offboard
                             if it.get("kind") == "pot" and "id" in it}
        self.jack_ids: set = {it["id"] for it in self.R.offboard
                              if it.get("kind") == "jack" and "id" in it}

    def bnet(self, term: str):
        """Board net root of a terminal, or None when the board never names it."""
        if term in self.terms:
            return self.LG.net(term)
        return None

    def places(self, ref: str) -> bool:
        """True when the board carries `ref` in any form: a two-lead part, an
        off-board part stub, or a control, jack, valve or transformer stub
        whose terminals the layout names."""
        if self.part_terms(ref) is not None:
            return True
        bid = self.id_of_ref.get(ref, ref)
        return any(str(m).split(".", 1)[0] in (ref, bid) for m in self.terms)

    def part_terms(self, ref: str):
        """(term_a, term_b) for a sheet two-lead designator, on this board."""
        if ref in self.part_refs:
            return f"{ref}.a", f"{ref}.b"
        bid = self.id_of_ref.get(ref, ref)
        if bid in self.offpart_ids:
            return f"{bid}.a", f"{bid}.b"
        return None

    def bname(self, root) -> list:
        """A board net's members in canonical names (eyelets dropped)."""
        ms = sorted(m for m in self.LG.nets().get(root, []) if not str(m).startswith("@"))
        if GND in self.LG.uf.parent and self.LG.uf.find(GND) == root and GND not in ms:
            ms.insert(0, GND)
        return ms


# ===========================================================================
# result
# ===========================================================================
class Result:
    def __init__(self, amp_id: str):
        self.amp_id = amp_id
        self.claim = False              # both drawings claim verified
        self.section_swap: list = []    # [(socket, removed)]
        self.split: list = []           # [(groups, line)]
        self.merged: list = []          # [(groups, line)]
        self.misplaced: list = []       # [(key, line)]
        self.unresolved: list = []      # [(key, line)]
        self.sheet_only_undeclared: list = []   # [(ref, line)]
        self.sheet_only_declared: list = []     # [(ref, line)]
        self.board_only: list = []      # [(ref, line)]
        self.pot_as_r: list = []        # [(ref, line)]
        self.stale: list = []           # [line]
        self.pot_flipped: list = []     # [pot]
        self.scope: list = []
        self.info: list = []
        self.anchors = 0
        self.checked = 0
        self.soft_ok = 0
        self.soft_bad: list = []        # [(label, line)]  (counted as MISPLACED)
        self.openwired: list = []       # [(groups, line)]  (scope, not a finding)

    def findings(self) -> list:
        """[(class, line)] — everything that counts as a finding."""
        out = []
        for sock, removed in self.section_swap:
            out.append(("SECTION-SWAP", f"{sock}: the sheet letters this socket's sections "
                                        f"on the opposite datasheet unit to the board "
                                        f"(exchanging them removes {removed} finding(s))"))
        out += [("SPLIT", ln) for _g, ln in self.split]
        out += [("MERGED", ln) for _g, ln in self.merged]
        out += [("MISPLACED", ln) for _k, ln in self.misplaced]
        out += [("MISPLACED", ln) for _k, ln in self.soft_bad]
        out += [("UNRESOLVED", ln) for _k, ln in self.unresolved]
        out += [("SHEET-ONLY", ln) for _r, ln in self.sheet_only_undeclared]
        out += [("BOARD-ONLY", ln) for _r, ln in self.board_only]
        out += [("POT-AS-RESISTOR", ln) for _r, ln in self.pot_as_r]
        out += [("STALE DECLARATION", ln) for ln in self.stale]
        return out

    def score(self) -> int:
        """What the section-swap search minimises: the topology findings."""
        return len(self.split) + len(self.merged) + len(self.misplaced) + len(self.soft_bad)

    @property
    def ok(self) -> bool:
        return not self.findings()

    def counts(self) -> dict:
        return {
            "section_swap": len(self.section_swap), "split": len(self.split),
            "merged": len(self.merged), "misplaced": len(self.misplaced) + len(self.soft_bad),
            "unresolved": len(self.unresolved),
            "sheet_only_undeclared": len(self.sheet_only_undeclared),
            "sheet_only_declared": len(self.sheet_only_declared),
            "board_only": len(self.board_only), "pot_as_resistor": len(self.pot_as_r),
            "stale_declarations": len(self.stale),
            "pot_orientation_flipped": len(self.pot_flipped),
            "anchors": self.anchors, "two_terminal_checked": self.checked,
        }


# ===========================================================================
# sheet terminals -> board vocabulary
# ===========================================================================
def _socket_of(ref: str) -> str:
    m = re.fullmatch(r"(V\d+)[A-Za-z]?", ref)
    return m.group(1) if m else ref


def _flip_unit(sh: Sheet, ref: str, unit):
    """The OTHER unit of a dual-section valve (the section-swap trial)."""
    pins = _basing(resolve_tube_slug(sh.values.get(ref, "") or "")) or {}
    units = sorted({m.get("unit") for m in pins.values() if m.get("unit") is not None},
                   key=lambda u: (0, float(u)) if str(u).isdigit() else (1, str(u)))
    if len(units) != 2:
        return unit
    if unit is None:
        letters = _section_letters(pins)
        want = _ref_section(ref)
        unit = next((u for u, ltr in letters.items() if ltr == want), None)
    if unit is None:
        return None
    return units[1] if unit == units[0] else units[0]


def sheet_terminals(sh: Sheet, bd: Board, swap: frozenset = frozenset()):
    """Read every symbol pin the sheet nets into the board's terminal names.

    Returns a dict with:
      anchors   {board terminal: sheet net}      hard anchors (identity on both)
      canon_of  {raw sheet terminal: board name} for printing sheet nets
      soft      [(candidate board terminals, sheet net, label)]
      twoterm   {key: (sheet net 1, sheet net 2, board term 1, board term 2)}
                key is the designator, or "VRn#ends" for a pot's end pair
      pots      {sheet ref: board id}
      absent    [(ref, reason)]  sheet parts the board neither places nor wires
      partial   [(ref, reason)]  pots / jacks the board wires only partly
      unmatched {lib: [refs]}    symbol classes with no board vocabulary
      unnumbered [(ref, key)]    tube electrodes the basing cannot number
      stale     [line]           net_map.leads entries naming nothing
      notes     [line]
    """
    G = sh.G
    anchors: dict = {}
    canon_of: dict = {}     # raw sheet terminal -> the board's name for it
    soft: list = []
    twoterm: dict = {}
    pots: dict = {}
    absent: list = []
    partial: list = []
    pot_as_r: list = []     # controls drawn with cx:R
    unmatched: dict = collections.defaultdict(list)
    unnumbered: list = []
    stale: list = []
    notes: list = []

    g = G.term("<GND>")
    if g is not None:
        anchors[GND] = g
    else:
        notes.append("the sheet carries no <GND> label — ground is not anchored")

    bysym: dict = collections.defaultdict(dict)
    for t in G.all_terminals():
        ref, num = t.rsplit(".", 1)
        bysym[ref][num] = G.term(t)

    for ref in sorted(bysym):
        pins = bysym[ref]
        lib = G.lib.get(ref)
        if lib in TUBE_LIBS:
            sock = _socket_of(ref)
            bid = bd.id_of_ref.get(sock, sock)
            unit = sh.units.get(ref)
            if sock in swap:
                unit = _flip_unit(sh, ref, unit)
            numbered = tube_pin_numbers(TUBE_LIBS[lib], ref, sh.values.get(ref, "") or "",
                                        unit=unit)
            key_of = sh.pin_names.get(lib, {})
            for num, net in sorted(pins.items()):
                key = key_of.get(num, num).lower()
                socketpins = numbered.get(key)
                if not socketpins:
                    unnumbered.append((ref, key))
                    continue
                cands = [f"{bid}.pin{p}" for p in socketpins.split(",")]
                canon_of[f"{ref}.{num}"] = "/".join(cands)
                if len(cands) == 1:
                    anchors[cands[0]] = net
                else:
                    # a directly heated rectifier's cathode is its filament pair
                    soft.append((cands, net, f"{ref}.{key}"))
        elif lib == POT_LIB:
            bid = bd.id_of_ref.get(ref, ref)
            pots[ref] = bid
            if bid not in bd.pot_ids:
                absent.append((ref, "pot on the sheet, not placed on the board"))
                continue
            wired = {n for n in ("1", "2", "3") if f"{bid}.lug{n}" in bd.terms}
            if "2" in pins:
                canon_of[f"{ref}.2"] = f"{bid}.lug2"
            if "2" in pins and "2" in wired:
                anchors[f"{bid}.lug2"] = pins["2"]
            ends_on_sheet = "1" in pins and "3" in pins
            if ends_on_sheet and {"1", "3"} <= wired:
                # the sheet's top pin (1) on the CW lug (3) is the standard
                # orientation; the flipped one is recorded as information
                twoterm[f"{ref}#ends"] = (pins["1"], pins["3"], f"{bid}.lug3", f"{bid}.lug1")
            if not wired:
                absent.append((ref, "pot placed on the board with no lug wired"))
            elif wired != {"1", "2", "3"}:
                miss = sorted({"1", "2", "3"} - wired)
                partial.append((ref, f"pot lug(s) {', '.join(miss)} unwired on the board"))
        elif lib in TWO_TERM_LIBS:
            if set(pins) != {"1", "2"}:
                unmatched[lib].append(ref)
                continue
            bid = bd.id_of_ref.get(ref, ref)
            if lib == "cx:R" and (bd.kind_of_id.get(bid) == "pot"
                                  or re.match(r"^(VR|RV)\w*$", ref)):
                pot_as_r.append((ref, bd.kind_of_id.get(bid) == "pot"))
                continue
            bt = bd.part_terms(ref)
            if ref in sh.bridged:
                absent.append((ref, "on the sheet, not placed on the board; declared "
                                    "DC-transparent, so the board's conductor runs through it"))
                continue
            if bt is None:
                absent.append((ref, "on the sheet, not placed on the board"))
                continue
            ta, tb = bt
            missing = [t for t in (ta, tb) if t not in bd.terms]
            if missing:
                absent.append((ref, f"placed on the board, lead(s) "
                                    f"{', '.join(m.split('.')[1] for m in missing)} wired to nothing"))
                continue
            twoterm[ref] = (pins["1"], pins["2"], ta, tb)
        elif lib == JACK_LIB:
            bid = bd.id_of_ref.get(ref, ref)
            if bid not in bd.jack_ids:
                notes.append(f"sheet jack {ref} has no board jack of that id — not anchored")
                continue
            contacts = {t for t in (f"{bid}.tip", f"{bid}.sleeve", f"{bid}.ring") if t in bd.terms}
            body = bid in bd.terms
            for num, contact in JACK_PIN_TERMINAL.items():
                net = pins.get(num)
                if net is None:
                    continue
                t = f"{bid}.{contact}"
                canon_of[f"{ref}.{num}"] = t
                if t in bd.terms:
                    anchors[t] = net
                elif not contacts and body and contact == "tip":
                    soft.append(([bid], net, f"{ref}.tip"))
                    notes.append(f"jack {ref}: the board wires its body only (no .tip/.sleeve) — "
                                 f"read as the tip; the sleeve anchors to nothing")
                else:
                    partial.append((ref, f"jack {contact} unwired on the board"))
        else:
            unmatched[lib or "?"].append(ref)

    # Declared sheet terminal -> board terminal (transformer leads, labels).
    for skey, bterm in sorted((bd.net_map.get("leads") or {}).items()):
        skey, bterm = str(skey), str(bterm)
        snet = G.term(skey)
        if snet is None:
            stale.append(f"net_map.leads[{skey}] -> {bterm} names no pin or label on the "
                         f"sheet — not applied. Correct the terminal, or delete it.")
            continue
        if bterm not in bd.terms:
            stale.append(f"net_map.leads[{skey}] -> {bterm} names no wired terminal on the "
                         f"board — not applied. Correct the terminal, or delete it.")
            continue
        anchors[bterm] = snet
        notes.append(f"declared lead: sheet {skey} is board {bterm} (net_map.leads)")

    return {"anchors": anchors, "canon_of": canon_of, "soft": soft, "twoterm": twoterm,
            "pots": pots, "absent": absent, "partial": partial, "pot_as_r": pot_as_r,
            "unmatched": dict(unmatched),
            "unnumbered": unnumbered, "stale": stale, "notes": notes}


# ===========================================================================
# the comparison
# ===========================================================================
def _sheet_names(sh: Sheet, S: dict, root) -> list:
    """A sheet net's members: every symbol pin and label on it, an anchored
    terminal under the board's name for it (V1A.1 prints as V1.pin6)."""
    canon = S["canon_of"]
    out = {canon.get(str(m), str(m)) for m in sh.members.get(root, [])}
    if root == S["anchors"].get(GND):
        out.add(GND)
    return sorted(out)


def _show(names: list, n: int = 10) -> str:
    return "{" + ", ".join(names[:n]) + (f", +{len(names) - n} more" if len(names) > n else "") + "}"


def compare(sh: Sheet, bd: Board, swap: frozenset = frozenset()) -> Result:
    res = Result(sh.amp_id)
    S = sheet_terminals(sh, bd, swap)
    anchors, soft, twoterm = S["anchors"], S["soft"], S["twoterm"]
    bnet = bd.bnet
    res.stale += S["stale"]

    def sname(root) -> str:
        return _show(_sheet_names(sh, S, root))

    def bname(root) -> str:
        return _show(bd.bname(root))

    def sheet_open(canon) -> bool:
        """Is this anchor's sheet net a singleton (the pin drawn open)? An open
        pin says nothing about its net, so it anchors nothing — the board may
        wire it (check_schematics owns open pins) without this gate objecting."""
        s = anchors.get(canon)
        mem = [m for m in sh.members.get(s, []) if not _LABEL_RE.match(str(m))]
        return len(mem) <= 1 and canon != GND

    # --- 1. anchored partition ------------------------------------------------
    common = {c: s for c, s in anchors.items() if bnet(c) is not None}
    res.anchors = len(common)
    for c in sorted(set(anchors) - set(common)):
        if c != GND:
            res.scope.append(f"{c}: on the sheet, wired to nothing on the board — not anchored "
                             f"(a tube pin's wiring is verify_layout_nets' claim)")
    by_sheet: dict = collections.defaultdict(list)
    by_board: dict = collections.defaultdict(list)
    for c, s in common.items():
        by_sheet[s].append(c)
        by_board[bnet(c)].append(c)
    for s, cs in by_sheet.items():
        groups: dict = collections.defaultdict(list)
        for c in cs:
            groups[bnet(c)].append(c)
        if len(groups) > 1:
            gs = sorted(sorted(v) for v in groups.values())
            res.split.append((gs, f"sheet net {sname(s)} is drawn as {len(gs)} board nets: "
                                  + " | ".join(bname(b) for b in groups)))
    for b, cs in by_board.items():
        groups: dict = collections.defaultdict(list)
        for c in cs:
            groups[common[c]].append(c)
        if len(groups) > 1:
            opens = [v for v in groups.values() if len(v) == 1 and sheet_open(v[0])]
            others = [v for v in groups.values() if v not in opens]
            gs = sorted(sorted(v) for v in groups.values())
            if opens and len(others) <= 1:
                res.openwired.append((gs, f"{', '.join(sorted(o[0] for o in opens))}: drawn "
                                          f"open on the sheet, wired on the board into "
                                          f"{bname(b)} (an open pin is check_schematics' claim)"))
            else:
                res.merged.append((gs, f"board net {bname(b)} carries {len(gs)} sheet nets: "
                                       + " | ".join(sname(s) for s in groups)))

    M: dict = {}        # sheet net -> board net
    Minv: dict = {}     # board net -> sheet net
    for c, s in sorted(common.items()):
        if sheet_open(c):
            continue
        b = bnet(c)
        M.setdefault(s, b)
        Minv.setdefault(b, s)

    # soft anchors: a sheet net that may realise on any of several board terminals
    for cands, s, label in soft:
        bs = {bnet(c) for c in cands} - {None}
        if not bs:
            continue
        if s in M:
            if M[s] in bs:
                res.soft_ok += 1
            else:
                res.soft_bad.append((label, f"{label}: the sheet nets it with {sname(s)}, "
                                            f"realised on the board as {bname(M[s])}, but the "
                                            f"board has it on {' / '.join(bname(b) for b in sorted(bs, key=str))}"))
        elif len(bs) == 1:
            b = next(iter(bs))
            M.setdefault(s, b)
            Minv.setdefault(b, s)
            res.soft_ok += 1

    # --- 2. two-terminal parts: majority voting to a fixed point --------------
    pending: dict = {}
    for key, (s1, s2, ta, tb) in twoterm.items():
        b1, b2 = bnet(ta), bnet(tb)
        if b1 is None or b2 is None:
            continue        # already listed as absent
        pending[key] = (s1, s2, b1, b2)
    inferred_merge: dict = {}     # (sheet net) -> (board net, voters)
    blocked: dict = {}            # key -> (sheet net, board net it would land on)
    while True:
        votes: dict = collections.defaultdict(collections.Counter)
        voters: dict = collections.defaultdict(list)
        for key, (s1, s2, b1, b2) in pending.items():
            m1, m2 = M.get(s1), M.get(s2)
            if m1 is not None and s2 not in M:
                tgt = b2 if m1 == b1 else (b1 if m1 == b2 else None)
                if tgt is not None:
                    votes[s2][tgt] += 1
                    voters[(s2, tgt)].append(key)
            if m2 is not None and s1 not in M:
                tgt = b2 if m2 == b1 else (b1 if m2 == b2 else None)
                if tgt is not None:
                    votes[s1][tgt] += 1
                    voters[(s1, tgt)].append(key)
        new: dict = {}
        for s, c in votes.items():
            top = c.most_common(2)
            if len(top) == 1 or top[0][1] > top[1][1]:
                b, n = top[0]
                if b in Minv and Minv[b] != s:
                    # the board lands this sheet net on the realisation of ANOTHER
                    # sheet net: a merge the board draws that the sheet does not
                    if n >= 2:
                        inferred_merge[s] = (b, voters[(s, b)])
                    else:
                        blocked[voters[(s, b)][0]] = (s, b)
                        continue
                new[s] = b
        if not new:
            break
        for s, b in new.items():
            M[s] = b
            Minv.setdefault(b, s)
    for s, (b, who) in sorted(inferred_merge.items(), key=lambda kv: str(kv[0])):
        res.merged.append((sorted(who), f"board net {bname(b)} carries sheet net {sname(s)} "
                                        f"and sheet net {sname(Minv[b])} — inferred through "
                                        f"{', '.join(sorted(who))}"))

    for key, (s1, s2, b1, b2) in sorted(pending.items()):
        m1, m2 = M.get(s1), M.get(s2)
        ref = key[:-5] if key.endswith("#ends") else key
        ta, tb = twoterm[key][2], twoterm[key][3]
        if m1 is None and m2 is None:
            res.unresolved.append((key, f"{ref}: neither of its sheet nets {sname(s1)} / "
                                        f"{sname(s2)} reaches an anchor on either surface — "
                                        f"not checked"))
            continue
        res.checked += 1
        why = None
        dangling = [lead for lead, b, s in ((ta, b1, s1), (tb, b2, s2))
                    if len(bd.bname(b)) <= 1 and len(sh.members.get(s, [])) > 1]
        if s1 == s2 and b1 != b2:
            why = "the sheet shorts its two ends onto one net, the board does not"
        elif b1 == b2 and s1 != s2:
            why = "the board lands both leads on one net, the sheet does not"
        elif m1 is not None and m2 is not None:
            if {m1, m2} != {b1, b2}:
                why = "its pair of nets on the sheet is not its pair on the board"
        else:
            m = m1 if m1 is not None else m2
            other_s = s2 if m1 is not None else s1
            other_b = b2 if m == b1 else (b1 if m == b2 else None)
            if other_b is None:
                why = "its pair of nets on the sheet is not its pair on the board"
            elif key in blocked:
                why = (f"the board lands its other lead on the net of {sname(Minv[other_b])}, "
                       f"the sheet draws it on {sname(other_s)}")
            elif dangling:
                why = "a lead is wired to nothing on the board"
        if why and dangling:
            why += ("; lead " + " and ".join(d.split(".")[1] for d in dangling)
                    + " is wired to nothing on the board while the sheet nets it")
        if why:
            res.misplaced.append((key, f"{ref}: {why}. sheet {sname(s1)} / {sname(s2)}; "
                                       f"board {ta} {bname(b1)} / {tb} {bname(b2)}"))
    res.unresolved.sort()

    # pot orientation (information): the sheet's top pin landing on lug 1
    for key, (s1, s2, ta, tb) in sorted(twoterm.items()):
        if not key.endswith("#ends"):
            continue
        pot = key[:-5]
        b3, b1 = bnet(ta), bnet(tb)
        if s1 in M and s2 in M and b1 != b3 and M[s1] == b1 and M[s2] == b3:
            res.pot_flipped.append(pot)

    # --- 3. sheet-only / board-only, against the declarations -----------------
    S["_sheet_refs"] = set(sh.G.lib)
    _declarations(res, bd, S)
    for ref, placed in sorted(S["pot_as_r"]):
        res.pot_as_r.append((ref, f"{ref}: the sheet draws this control with the resistor "
                                  f"symbol (cx:R); "
                                  + ("the board places it as a pot, and a resistor has no wiper "
                                     "to anchor — not compared until the sheet draws the pot"
                                     if placed else
                                     "the board does not place it either — a VR/RV designator "
                                     "names a control, so draw the pot")))

    # --- 4. scope ---------------------------------------------------------------
    res.scope += S["notes"]
    for ref, why in S["partial"]:
        res.scope.append(f"{ref}: {why} — anchored only where both surfaces wire it")
    if S["unnumbered"]:
        refs = sorted({r for r, _k in S["unnumbered"]})
        res.scope.append(f"tube pins not numbered by the basing (a dual valve lettered "
                         f"without a section, or a valve the corpus has no basing for) — "
                         f"not anchored: {', '.join(refs)}")
    for lib, refs in sorted(S["unmatched"].items()):
        res.scope.append(f"{lib.replace('cx:', '')}: {len(refs)} symbol(s) the board has no "
                         f"terminal vocabulary for — not compared: {', '.join(sorted(refs))}")
    for ref, src in sorted(sh.bridged.items()):
        res.scope.append(f"{ref}: declared DC-transparent ({src}) and not placed — its two "
                         f"sheet nets are compared as one board net")
    for ref, src in sorted(sh.unit_source.items()):
        if src == "draw script":
            res.scope.append(f"{ref}: datasheet unit {sh.units[ref]} read from "
                             f"draw_{sh.amp_id.replace('-', '_')}.py — the committed sheet does "
                             f"not carry {UNIT_PROPERTY} yet (regenerate it)")
        else:
            res.scope.append(f"{ref}: datasheet unit {sh.units[ref]} stated on the sheet "
                             f"({UNIT_PROPERTY})")
    for _g, ln in res.openwired:
        res.scope.append(ln)
    res.scope.append(f"anchors {res.anchors}; two-terminal parts checked {res.checked}, "
                     f"unresolved {len(res.unresolved)}; soft anchors {res.soft_ok} ok, "
                     f"{len(res.soft_bad)} bad; heaters, pilot lamp: excluded (check_heaters.py)")
    for e in bd.errors:
        res.scope.append(f"layout: {e}")
    return res


def _declarations(res: Result, bd: Board, S: dict):
    """SHEET-ONLY against the four ways a board declares what it does not draw,
    BOARD-ONLY for the reverse, and a STALE DECLARATION for a per-part entry or
    a rule that covers nothing."""
    nm = bd.net_map
    unplaced = {str(k): str(v) for k, v in (nm.get("netlist_unplaced") or {}).items()}
    bridged = {str(k): f"{v} [sch_map]" for k, v in (bd.sch_map.get("series_bridge") or {}).items()}
    bridged.update({str(k): str(v) for k, v in (nm.get("series_bridge") or {}).items()})
    not_on_board = {str(k): str(v) for k, v in (nm.get("not_on_board") or {}).items()}
    rules = []
    for i, rule in enumerate(bd.scope_rules):
        if not isinstance(rule, dict) or not rule.get("match"):
            res.stale.append(f"scope.not_drawn[{i}] has no `match:` glob — ignored")
            continue
        rules.append((str(rule["match"]), str(rule.get("why", "")), i))
    used_parts: set = set()
    used_rules: set = set()
    for ref, why in sorted(S["absent"]):
        decl = None
        if ref in not_on_board:
            decl = f"net_map.not_on_board: {not_on_board[ref]}"
            used_parts.add(ref)
        elif ref in unplaced:
            decl = f"net_map.netlist_unplaced: {unplaced[ref]}"
        elif ref in bridged:
            decl = f"series_bridge: {bridged[ref]}"
        else:
            for pat, rwhy, i in rules:
                if fnmatch.fnmatchcase(ref, pat):
                    decl = f"scope.not_drawn[{pat}]: {rwhy}"
                    used_rules.add(i)
                    break
        if decl:
            res.sheet_only_declared.append((ref, f"{ref}: {why} — declared ({decl})"))
        else:
            res.sheet_only_undeclared.append((ref, f"{ref}: {why} — UNDECLARED (declare it in "
                                                   f"net_map.not_on_board or a scope.not_drawn rule)"))
    for ref in sorted(set(not_on_board) - used_parts):
        res.stale.append(f"net_map.not_on_board[{ref}] covers nothing: the board wires {ref}, "
                         f"or the sheet has no such part. Delete it.")
    for pat, _why, i in rules:
        if i not in used_rules:
            res.stale.append(f"scope.not_drawn[{pat}] matches no sheet-only part — the rule "
                             f"is dead. Delete it.")
    # BOARD-ONLY: a placed part with no symbol on the sheet
    on_sheet = set(S.get("_sheet_refs") or [])
    for ref in sorted(bd.part_refs | bd.offpart_ids | bd.pot_ids):
        it = bd.R.off_by_id.get(ref)
        sref = (it or {}).get("ref") or ref
        if sref in on_sheet or ref in on_sheet:
            continue
        kind = "pot" if ref in bd.pot_ids else "part"
        res.board_only.append((ref, f"{ref}: {kind} on the board, no symbol on the sheet"))


# ===========================================================================
# per-amp entry: the section-swap search
# ===========================================================================
def load_amp(amp_id: str, amp_dir: "Path | None" = None):
    amp_dir = amp_dir or AMPS / amp_id
    sh = Sheet(amp_id, amp_dir / "schematic.kicad_sch",
               PIPELINE / f"draw_{amp_id.replace('-', '_')}.py")
    bd = Board(amp_id, amp_dir)
    sh.apply_bridges(bd)
    return sh, bd


def check_amp(amp_id: str, amp_dir: "Path | None" = None) -> Result:
    amp_dir = amp_dir or AMPS / amp_id
    sh, bd = load_amp(amp_id, amp_dir)
    return check_pair(sh, bd, amp_dir)


def check_pair(sh: Sheet, bd: Board, amp_dir: Path) -> Result:
    base = compare(sh, bd, frozenset())
    # every dual-section socket the sheet letters with sections is a candidate
    cands: set = set()
    for ref, lib in sh.G.lib.items():
        if lib in TUBE_LIBS and re.fullmatch(r"V\d+[A-Za-z]", ref):
            sock = _socket_of(ref)
            if bd.id_of_ref.get(sock, sock) in bd.kind_of_id:
                cands.add(sock)
    best, swap = base, set()
    improved = True
    while improved and cands - swap:
        improved = False
        for sock in sorted(cands - swap):
            r = compare(sh, bd, frozenset(swap | {sock}))
            if r.score() <= best.score() - 2:      # must remove at least two findings
                best, swap, improved = r, swap | {sock}, True
                break
    if swap:
        for sock in sorted(swap):
            without = compare(sh, bd, frozenset(swap - {sock}))
            best.section_swap.append((sock, without.score() - best.score()))
    sch_claim = str(bd.sch_map.get("schematic_claim", "")).lower()
    best.claim = (sch_claim == "verified"
                  and str(bd.layout.get("wiring_claim", "")).lower() == "verified")
    return best


# ===========================================================================
# reporting
# ===========================================================================
_SHORT = {"STALE DECLARATION": "STALE DECL."}


def print_result(res: Result, report: bool = False):
    tag = ("both drawings claim verified" if res.claim
           else "report-only (a drawing without its claim)")
    head = "PASS" if res.ok else "FAIL"
    print(f"\n=== {res.amp_id}: {head} — {tag} ===")
    if report:
        for s in res.scope:
            print(f"  {'scope':<13}| {s}")
    for cls, line in res.findings():
        print(f"  {_SHORT.get(cls, cls):<13}| {line}")
    for _r, line in res.sheet_only_declared:
        print(f"  {'declared':<13}| {line}")
    for pot in res.pot_flipped:
        print(f"  {'info':<13}| POT-ORIENTATION {pot}: the sheet draws the CW end (lug 3) at the "
              f"bottom of the symbol — legal, noted so the board reads as expected")
    if res.ok:
        print("  sheet and board draw the same circuit over every anchored and resolved "
              "part (within the documented scope)")


# ===========================================================================
# the committed worklist
# ===========================================================================
WORKLIST_HEADER = """\
# GENERATED - pipeline/verify_sheet_vs_board.py --export. Do not hand-edit; a
# run that disagrees with this file fails the gate, the same way
# reference/heaters.yaml, op-points.yaml and loadlines.yaml are held to what a
# fresh run produces.
#
# WHAT THIS IS. The schematic and the board layout of each amplifier are two
# independent drawings of one circuit, and over the ~1,280 passives the DC
# netlist does not model they were compared by nothing until this gate landed.
# This file is the standing list of every part on which the two drawings
# DISAGREE, per amplifier and per class (see the gate's docstring for the
# classes). Nothing here says which drawing is right: each entry needs a read of
# that amplifier's own source before either surface is edited.
#
# HOW TO READ IT. `section_swap` names a socket whose sections the sheet letters
# on the opposite datasheet unit to the board. `split` / `merged` are anchored
# terminals (tube pins, pot wipers, jack contacts, ground) grouped as one net on
# one surface and more than one on the other. `misplaced` are two-terminal
# parts (and pot end pairs, `VRn#ends`) whose pair of nets differs between the
# surfaces. `sheet_only_undeclared` are parts the sheet draws and the board
# neither places nor wires, with no declaration saying why (net_map.not_on_board
# or a scope.not_drawn rule in layout.yaml); `sheet_only_declared` are the ones
# that are explained. `unresolved` are parts neither surface anchors, so they
# are NOT checked. `pot_as_resistor` names a control the sheet draws with the
# resistor symbol (no wiper to anchor). `pot_orientation_flipped` is
# information only.
#
# CLEARING AN ENTRY. Read the amplifier's own sheet, correct the surface that is
# wrong (draw_<id>.py or layout.yaml), regenerate, and re-export. The `summary`
# is the size of the job; `--strict` enters CI once it is clean for every amp
# whose sheet and board both claim verified.
"""


def all_ids() -> list:
    return sorted(d.name for d in AMPS.iterdir()
                  if d.is_dir() and (d / "layout.yaml").exists()
                  and (d / "schematic.kicad_sch").exists())


def worklist(results: list) -> dict:
    amps: dict = {}
    for r in results:
        amps[r.amp_id] = {
            "claimed": bool(r.claim),
            "counts": r.counts(),
            "section_swap": [s for s, _n in r.section_swap],
            "split": [g for g, _l in r.split],
            "merged": [g for g, _l in r.merged],
            "misplaced": sorted([k for k, _l in r.misplaced] + [k for k, _l in r.soft_bad]),
            "unresolved": [k for k, _l in r.unresolved],
            "sheet_only_undeclared": [k for k, _l in r.sheet_only_undeclared],
            "sheet_only_declared": [k for k, _l in r.sheet_only_declared],
            "board_only": [k for k, _l in r.board_only],
            "pot_as_resistor": [k for k, _l in r.pot_as_r],
            "stale_declarations": list(r.stale),
            "pot_orientation_flipped": list(r.pot_flipped),
        }
    keys = ("section_swap", "split", "merged", "misplaced", "unresolved",
            "sheet_only_undeclared", "sheet_only_declared", "board_only", "pot_as_resistor",
            "stale_declarations", "pot_orientation_flipped", "anchors", "two_terminal_checked")
    summary = {k: sum(a["counts"][k] for a in amps.values()) for k in keys}
    summary["amps"] = len(amps)
    summary["amps_with_findings"] = sum(1 for r in results if not r.ok)
    summary["claimed_amps_with_findings"] = sum(1 for r in results if r.claim and not r.ok)
    return {"summary": summary, "amps": amps}


def export_worklist(results: list) -> int:
    data = worklist(results)
    WORKLIST.write_text(WORKLIST_HEADER
                        + yaml.safe_dump(data, sort_keys=True, width=100, allow_unicode=True))
    print(f"exported {WORKLIST.relative_to(ROOT)} - "
          + ", ".join(f"{k} {v}" for k, v in sorted(data["summary"].items())))
    return 0


def check_worklist(results: list) -> list:
    if not WORKLIST.exists():
        return [f"{WORKLIST.relative_to(ROOT)} is missing - regenerate with "
                f"pipeline/verify_sheet_vs_board.py --export"]
    committed = yaml.safe_load(WORKLIST.read_text()) or {}
    fresh = worklist(results)
    if committed == fresh:
        return []
    out = [f"DRIFT: {WORKLIST.relative_to(ROOT)} is not what a fresh run produces - "
           f"regenerate with pipeline/verify_sheet_vs_board.py --export"]
    if committed.get("summary") != fresh.get("summary"):
        out.append(f"    committed summary: {committed.get('summary')}")
        out.append(f"    fresh     summary: {fresh.get('summary')}")
    ca, fa = committed.get("amps") or {}, fresh.get("amps") or {}
    changed = sorted(k for k in set(ca) | set(fa) if ca.get(k) != fa.get(k))
    if changed:
        out.append(f"    amps that differ: {', '.join(changed)}")
    return out


# ===========================================================================
# self-test — a gate that cannot catch planted faults is decoration
# ===========================================================================
def _copy_amp(tmp: Path, amp_id: str) -> Path:
    dst = tmp / amp_id
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(AMPS / amp_id, dst)
    return dst


def _edit_layout(amp_dir: Path, fn):
    p = amp_dir / "layout.yaml"
    d = yaml.safe_load(p.read_text())
    fn(d)
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))


def _drop_run(d: dict, frm, to):
    before = len(d["runs"])
    d["runs"] = [r for r in d["runs"] if not (r.get("from") == frm and r.get("to") == to)]
    assert len(d["runs"]) == before - 1, f"selftest: no run {frm} -> {to}"


def _reroute(d: dict, frm, to, new_to):
    for r in d["runs"]:
        if r.get("from") == frm and r.get("to") == to:
            r["to"] = new_to
            return
    raise AssertionError(f"selftest: no run {frm} -> {to}")


def _swap_refs(amp_dir: Path, a: str, b: str):
    """Exchange two symbols' Reference properties on the sheet (the sections
    of one bottle change places: the same fault as a wrong `unit=`)."""
    p = amp_dir / "schematic.kicad_sch"
    t = p.read_text()
    ka, kb = f'(property "Reference" "{a}"', f'(property "Reference" "{b}"'
    assert ka in t and kb in t, f"selftest: {a}/{b} not on the sheet"
    t = t.replace(ka, "\0").replace(kb, ka).replace("\0", kb)
    p.write_text(t)


def _plant_unit(amp_dir: Path, ref: str, unit):
    """Give a symbol a Basing_unit property, as a regenerated sheet would carry."""
    p = amp_dir / "schematic.kicad_sch"
    t = p.read_text()
    key = f'(property "Reference" "{ref}"'
    i = t.index(key)
    j = t.index("\n", i)
    line = t[i:j]
    at = re.search(r"\(at ([-\d.]+) ([-\d.]+) (\d+)\)", line)
    x, y, a = at.groups()
    prop = (f'\n    (property "{UNIT_PROPERTY}" "{unit}" (at {x} {float(y) + 4.8:g} {a}) '
            f'(effects (font (size 1.27 1.27)) hide))')
    p.write_text(t[:j] + prop + t[j:])


def selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="cx-sheetboard-"))
    fails: list = []
    n = 0

    def case(label: str, want: str, res: Result, needle: str = "", absent: str = ""):
        """`want` is a class that must be among the findings (naming `needle`),
        or "PASS" for no findings at all; `absent` is a class that must NOT
        appear."""
        nonlocal n
        n += 1
        found = res.findings()
        if want == "PASS":
            ok = not found
        else:
            ok = any(cls == want and needle in line for cls, line in found)
        if absent and any(cls == absent for cls, _l in found):
            ok = False
        state = "ok  " if ok else "FAIL"
        print(f"  {state} {label}")
        hit = next((line for cls, line in found if cls == want and needle in line), None)
        if hit:
            print(f"         -> {hit[:150]}")
        if not ok:
            fails.append(label)
            for cls, line in found[:4]:
                print(f"         (got) {cls}: {line[:140]}")

    try:
        # ---- 5C1: the cleanest pair in the corpus (0 findings of any class) --
        d = _copy_amp(tmp, "5c1")
        case("BASELINE      5c1 sheet and board agree", "PASS", check_amp("5c1", d))

        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: _reroute(L, "C4.b", [1.45, 13.7], "C2.a"))
        case("MISPLACED     5c1 C4's ground lead rerouted onto the screen node",
             "MISPLACED", check_amp("5c1", d), "C4")

        d = _copy_amp(tmp, "5c1")

        def move_eyelet(L):
            for p in L["parts"]:
                if p["ref"] == "C4":
                    p["b"] = [0, 9]          # C2.a's eyelet: the screen node
        _edit_layout(d, move_eyelet)
        case("MERGED        5c1 C4's lead moved into C2's eyelet, its ground wire left",
             "MERGED", check_amp("5c1", d), "V1.pin6")

        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: _drop_run(L, "V1.pin5", [1.45, 1.8]))
        case("SPLIT         5c1 6SJ7 cathode ground return cut",
             "SPLIT", check_amp("5c1", d), "V1.pin5")

        d = _copy_amp(tmp, "5c1")

        def delete_c4(L):
            L["parts"] = [p for p in L["parts"] if p["ref"] != "C4"]
            L["runs"] = [r for r in L["runs"]
                         if not (str(r.get("from")).startswith("C4.") or str(r.get("to")).startswith("C4."))]
        _edit_layout(d, delete_c4)
        case("SHEET-ONLY    5c1 C4 deleted from the board, undeclared",
             "SHEET-ONLY", check_amp("5c1", d), "C4")

        def declare_c4(L):
            delete_c4(L)
            L.setdefault("net_map", {})["not_on_board"] = {
                "C4": "selftest: the cathode bypass is mounted at the socket"}
        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, declare_c4)
        case("DECLARED      5c1 C4 covered by net_map.not_on_board -> passes",
             "PASS", check_amp("5c1", d))

        def rule_c4(L):
            delete_c4(L)
            L["scope"] = {"not_drawn": [{"match": "C*", "why": "selftest: caps live at the sockets"}]}
        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, rule_c4)
        case("SCOPE RULE    5c1 C4 covered by a scope.not_drawn glob -> passes",
             "PASS", check_amp("5c1", d))

        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: L.setdefault("net_map", {}).__setitem__(
            "not_on_board", {"C4": "selftest: stale — the board wires C4"}))
        case("STALE DECL.   5c1 not_on_board names a part the board wires",
             "STALE DECLARATION", check_amp("5c1", d), "C4")

        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: L.__setitem__(
            "scope", {"not_drawn": [{"match": "VR*", "why": "selftest: dead rule"}]}))
        case("STALE RULE    5c1 scope.not_drawn rule matching nothing",
             "STALE DECLARATION", check_amp("5c1", d), "VR*")

        d = _copy_amp(tmp, "5c1")
        p = d / "schematic.kicad_sch"
        p.write_text(p.read_text().replace('(property "Reference" "R3"',
                                           '(property "Reference" "VR3"'))
        case("POT-AS-R      5c1 grid leak R3 relettered VR3 (a control drawn as a resistor)",
             "POT-AS-RESISTOR", check_amp("5c1", d), "VR3", absent="SHEET-ONLY")

        # net_map.leads: the OT primary declared right, wrong, and stale
        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: L.setdefault("net_map", {}).__setitem__(
            "leads", {"T1.1": "T1.blue", "T1.2": "T1.red"}))
        case("LEADS         5c1 OT primary leads declared (plate=blue, B+=red) -> passes",
             "PASS", check_amp("5c1", d))
        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: L.setdefault("net_map", {}).__setitem__(
            "leads", {"T1.1": "T1.red", "T1.2": "T1.blue"}))
        r = check_amp("5c1", d)
        case("LEADS         5c1 OT primary leads declared crossed -> caught",
             next((c for c, _l in r.findings() if c in ("MERGED", "SPLIT", "MISPLACED")), "MERGED"),
             r, "T1.")
        d = _copy_amp(tmp, "5c1")
        _edit_layout(d, lambda L: L.setdefault("net_map", {}).__setitem__(
            "leads", {"T1.9": "T1.blue"}))
        case("STALE LEAD    5c1 net_map.leads names a pin the sheet has not",
             "STALE DECLARATION", check_amp("5c1", d), "T1.9")

        # series_bridge: applied to a sheet-only part, never to one the board places
        for amp, ref, want, label in (
                ("5g9", "VR5", False, "BRIDGE        5g9 Depth pot VR5 is placed on the board -> not bridged"),
                ("5f10", "Rs1", True, "BRIDGE        5f10 grid stopper Rs1 is sheet-only -> bridged")):
            n += 1
            sh_b, _bd = load_amp(amp, _copy_amp(tmp, amp))
            ok = (ref in sh_b.bridged) == want
            print(f"  {'ok  ' if ok else 'FAIL'} {label}")
            if not ok:
                fails.append(label)

        # ---- 5D3: dual triodes and two channels of pots, also clean at HEAD --
        d = _copy_amp(tmp, "5d3")
        case("BASELINE      5d3 sheet and board agree", "PASS", check_amp("5d3", d))

        d = _copy_amp(tmp, "5d3")
        _swap_refs(d, "V2A", "V2B")
        r = check_amp("5d3", d)
        case("SECTION-SWAP  5d3 V2's sections exchanged on the sheet (references swapped)",
             "SECTION-SWAP", r, "V2:")
        n += 1
        if [s for s, _n in r.section_swap] == ["V2"] and r.score() == 0:
            print("  ok   SWAP FOLDED    the swap is reported once, not as its collateral")
        else:
            fails.append("swap collateral")
            print(f"  FAIL SWAP FOLDED    swaps={r.section_swap} residual score={r.score()}")

        d = _copy_amp(tmp, "5d3")
        _plant_unit(d, "V1A", 2)
        _plant_unit(d, "V1B", 1)
        case("SECTION-SWAP  5d3 input pair V1 given Basing_unit 2/1 on the sheet",
             "SECTION-SWAP", check_amp("5d3", d), "V1:")

        d = _copy_amp(tmp, "5d3")
        _plant_unit(d, "V1A", 1)
        _plant_unit(d, "V1B", 2)
        case("UNIT PROPERTY 5d3 V1 given the units it already draws -> passes",
             "PASS", check_amp("5d3", d))

        d = _copy_amp(tmp, "5d3")
        _edit_layout(d, lambda L: L["runs"].append({"from": "VR1.lug2", "to": "VR2.lug2"}))
        case("MERGED        5d3 the two volume-pot wipers bridged on the board",
             "MERGED", check_amp("5d3", d), "VR1.lug2")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for f in fails:
        print(f"  !! {f}")
    print(f"\nselftest: {n} case(s), {len(fails)} failure(s)")
    return 1 if fails else 0


# ===========================================================================
# cli
# ===========================================================================
def main(argv: list) -> int:
    if "--selftest" in argv:
        return selftest()
    report = "--report" in argv
    strict = "--strict" in argv
    export = "--export" in argv
    ids = [a for a in argv if not a.startswith("-")]
    only = bool(ids)
    ids = ids or all_ids()

    print("schematic <-> board net equivalence over EVERY part (no netlist)")
    print("  the sheet and the board are authored independently; where both name a")
    print("  terminal they anchor each other, and every two-terminal part is checked")
    print("  from those anchors. A disagreement is a source read, not a verdict on")
    print("  which drawing is wrong. Heaters and the pilot lamp are check_heaters'.")
    results: list = []
    for amp in ids:
        try:
            res = check_amp(amp)
        except Exception as e:      # noqa: BLE001 — a crash on one amp must still name it
            print(f"\n=== {amp}: ERROR {type(e).__name__}: {e} ===")
            raise
        results.append(res)
        print_result(res, report=report or only)
    totals: dict = collections.Counter()
    for r in results:
        for cls, _l in r.findings():
            totals[cls] += 1
    with_findings = [r.amp_id for r in results if not r.ok]
    claimed_bad = [r.amp_id for r in results if r.claim and not r.ok]
    print()
    print(f"{len(results)} amp(s); {len(results) - len(with_findings)} clean, "
          f"{len(with_findings)} with findings")
    if totals:
        print("findings by class: " + ", ".join(f"{k}={v}" for k, v in sorted(totals.items())))
    errors = 0
    if export and not only:
        export_worklist(results)
    elif not only:
        for line in check_worklist(results):
            print(f"FAIL {line}" if not line.startswith("    ") else line)
            errors += 0 if line.startswith("    ") else 1
    if strict and claimed_bad:
        print(f"GATE FAIL (--strict) — amps whose sheet AND board claim verified but "
              f"disagree: {', '.join(claimed_bad)}")
        errors += 1
    elif with_findings:
        print("report-only: the findings above do not fail the build; --strict does, for "
              "amps whose sheet and board both claim verified, and enters CI once the "
              "committed worklist is clean for them.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
