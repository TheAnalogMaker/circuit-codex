#!/usr/bin/env python3
"""CI gate: the tone stack each schematic *draws* is the tone stack the site
*plots*.

The tone-stack lab (/reference/guides/tone-stack-lab/) solves a fixed network —
the one documented in site/src/lib/tonestack.js — and fills its component values
from each amp's bom.yaml by reference designator. Nothing checked that the
drawing in amps/<id>/schematic.kicad_sch wires those same designators into that
same network, so a mis-placed wire could publish a curve for a circuit the
corpus does not draw. This gate closes that gap.

The reference designators are read out of the site's own TONE_STACK_SPECS table
rather than restated here, so the two cannot drift apart: rename a part in
corpus.js and this gate follows it. The companion TONE_STACK_GATE_EXTRAS table
(same file) lists the multi-knob networks the lab has read at lug level but
does not plot as their own preset — second channels, mainly — so every
drawing the corpus claims to have read that closely is walked here.

Each preset declares which of the two stack wirings its schematic draws
(`wiring` in TONE_STACK_SPECS), and the gate asserts the matching network.

'joined' — the textbook wiring (node names as tonestack.js writes them):

    IN   stack input        slope resistor · treble cap
    N2   slope foot         slope resistor · treble-pot end lug · bass cap
                            · mid cap
    N3   treble-cap output  treble cap · treble-pot other end lug
    OUT  stack output       treble-pot wiper · bass-pot wiper
    N4   bass-cap output    bass cap · bass-pot end lug
    N5   mid-leg top        bass-pot other end lug · mid cap · mid leg

'ladder' — the wiring the published 5F6, 5F6-A, JTM45, 1987, 1959, AA964,
AB763 (both channels), AA1164 and AA764 sheets draw:

    IN   stack input        slope resistor · treble cap
    N2   slope foot         slope resistor · bass cap · mid cap
    N3   treble-cap output  treble cap · treble-pot end lug
    OUT  stack output       treble-pot WIPER, alone
    N4   bass-cap output    bass cap · treble-pot other end lug ·
                            bass-rheostat hot lug (wiper strapped to an end)
    N5   bass-rheostat foot mid-leg top (mid pot's end lug, or the fixed leg)
    M    mid pot's wiper    the mid cap lands here (three-knob only)

The mid leg below N5 is a pot (three-knob) or a fixed resistor (blackface
two-knob). Which end lug of a pot is the "10" end is a taper fact a drawing
cannot carry, so the gate accepts either orientation and only checks what the
wires say.

'split' — the tweed 5F4's tone circuit (kind 'split'): not a wiring of the
stack above but a different network. Treble and bass ride two branches off the
cathode follower and recombine at the output:

    IN   stack input       treble cap · bass-branch coupler
    N3   treble-cap output treble-pot end lug
    N5   treble cold end   treble-pot other end lug · shunt cap to ground
    OUT  stack output      treble-pot WIPER · 220k from the bass branch
    N2   bass branch       coupler · 220k leak to ground · 100k series
                           (the 4.7M feedback resistor also returns here)
    W    bass injection    100k series · the bass pot's WIPER · 220k to OUT
    N6   bass leg          bass-pot end lug · 0.005 µF to ground; the pot's
                           other end lug is grounded outright

'treble-cut' — the single-knob tweed control (kind 'single-knob'), the network
tonestack.js models as trebleCutElements: a series capacitor and a rheostat
bleeding treble from the signal node to ground.

    IN   signal node       cut capacitor's hot end (a plate, a coupler node or
                           the volume pot's top lug — whatever the amp feeds it
                           from; the gate asserts only that it is not ground)
    M    branch middle     cut capacitor · the pot's live lug(s)
    GND  the pot's other live lug

    Whether the capacitor or the pot sits nearer the signal node is arbitrary in
    a two-element series branch, and both orders are drawn in this corpus. A
    third pot lug may be strapped to one of the two nets (the 5F2-A idiom) or
    left unwired (the 6161/GA-40 idiom, waived in sch_open_pins.yaml). What the
    gate does insist on is that the WIPER sits on one of those two nets: a wiper
    on a third live net is a three-terminal blend, not a cut, and that is a
    different network — it is exactly what separates the 5F2-A from the 5D3,
    5E3 and 5G9, whose tone pots divide between a treble path and a cut path.

Coverage accounting
-------------------
A gate that walks only what it is handed reports zero problems for every
network nobody declared, which reads as verified and is not. So this file also
carries UNCHECKED_NETWORKS: one dated entry per drawn tone network this gate
cannot walk, with the reason. It is not documentation — it is enforced. Every
circuit whose meta.yaml declares a tone network must either be walked here or
be named there, and an entry naming a network that IS now walked fails as a
stale waiver. A new amp cannot land with an unwalked tone network and no entry.

Run from pipeline/:  python3 check_tonestack_wiring.py
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import yaml

from sch_nets import Nets

ROOT = Path(__file__).resolve().parent.parent
CORPUS_JS = ROOT / "site" / "src" / "lib" / "corpus.js"

# Pot pin numbers in the cx:POT library symbol: 1 and 3 are the track ends,
# 2 is the wiper.
POT_ENDS = ("1", "3")
POT_WIPER = "2"

# Every tone network this gate does not walk, keyed `<amp id>` or
# `<amp id>:<channel>`, with the reason it is out of reach. Enforced, not
# decorative: `audit_coverage()` fails on a circuit that declares a tone network
# and appears in neither the spec tables nor this one, and on an entry naming a
# network the spec tables now walk. Where an entry records a disagreement with
# the amp's own cited sheet it is a defect note, not a licence — the network
# stays out of the walked set until the drawing is repaired and declared.
UNCHECKED_NETWORKS = {
    # --- single-knob blends: the pot divides between a treble path and a cut
    # path, so its wiper sits on a third live net. tonestack.js models the cut
    # (trebleCutElements) but not the blend, and the two are different networks.
    "5d3": "Single-knob blend: the 1 M tone pot divides between a 500 pF treble path "
           "and a 0.005 uF cut path, with its wiper feeding the next grid. No lab model.",
    "5e3": "Single-knob blend as the 5D3 draws it, and the control additionally sits "
           "inside this amp's interactive volume network rather than being fed from one "
           "stage, so even the drive model the solver assumes does not describe it.",
    "5g9": "Single-knob blend as the 5D3 draws it (500 pF treble path, 0.005 uF cut), "
           "wiper on the mixing node. No lab model.",
    "6g3:normal": "Single-knob blend, one per channel — the 6G3 draws the 5D3 network "
                  "twice with different cut capacitors. No lab model.",
    "6g3:bright": "The second of the 6G3's two single-knob blends (0.02 uF cut).",

    # --- networks the lab has no `kind` for at all.
    "5e5a": "Two cascaded pots: 0.01 uF into the Treble control, whose wiper feeds the "
            "Bass control's top lug, with a 500 pF shunt off the Treble cold lug and the "
            "Bass wiper driving the phase inverter. meta.yaml calls it `james`; it is not "
            "the B-15N's James board and the lab models neither.",
    "5e6a": "Bass shelf and treble branch never meet in a stack: the Bass control rides "
            "the shared presence/feedback bus through 220 kOhm with a 220 kOhm/0.005 uF "
            "shelf under its wiper, while the treble path runs two series capacitors "
            "(0.1 uF then 250 pF) through a Treble rheostat and into the driver grid "
            "through 47 pF. No lab model.",
    "6g6b:bass": "Cathode-follower-fed network with a 1 MOhm bass leg bridged by two "
                 "0.25 uF capacitors and a 10 kOhm dropper paralleled by a 25 kOhm Bass "
                 "control, and the channel's Treble control sitting in the shared driver "
                 "bottle's own signal path. No lab model.",
    "ac15": "Top Cut is a differential control — 250 kOhm and 0.005 uF across the two "
            "phase-inverter outputs — not a stack fed from one stage. The Vibrato "
            "channel's switched TONE I / TONE II voicing network is annotation only. "
            "A model for either would have to be written first.",
    "ac30": "The Cut control is the AC15's differential top cut (250 kOhm, 0.0047 uF "
            "across the phase-inverter outputs). No lab model.",
    "b15n:channel 1": "A James tone board: 220 kOhm into the Bass pot with 0.001 uF top-"
                      "to-wiper and 0.01 uF bottom-to-wiper and a 22 kOhm foot, 470 pF "
                      "into the Treble pot with a 0.0047 uF foot, and a 120 kOhm link "
                      "joining the two wipers as the board output. No lab model.",
    "b15n:channel 2": "The B-15N draws its James board twice; this is the second copy "
                      "(P.E.C. 250762-1), part for part the first.",
    "s1484": "No schematic.kicad_sch in the corpus, so there is no drawing for this gate "
             "to read. Its two channels' bass network plus treble-cut rheostat are "
             "recorded in bom.yaml and netlist.cir only.",

    # --- drawn networks that disagree with the amp's own cited factory sheet.
    # Read off the sheets on 2026-09-09; the crops are named in the finding.
    # These cannot be declared until the drawing (and the parts list behind it)
    # is repaired: declaring them would gate the wrong network.
    "6g4:channel 1": "DEFECT (2026-09-09): the cited 6G4 sheet feeds the tone network "
                     "from the input-stage plate through a 0.05 uF coupling capacitor "
                     "and hangs a 0.01 uF capacitor from the slope foot to the Bass "
                     "wiper, whose 10 kOhm runs to ground with the pot's own foot "
                     "grounded. The drawing here has neither capacitor, takes the "
                     "100 kOhm slope straight off the plate (a DC path to ground through "
                     "the stack) and straps the Bass pot as a rheostat above the 10 kOhm.",
    "6g4:channel 2": "The 6G4's second channel is drawn as the mirror of channel 1 and "
                     "carries the same defect; the sheet draws the two identically.",
    "6g5:channel 1": "DEFECT (2026-09-09): the cited 6G5 sheet draws the 6G4 network "
                     "exactly — 0.05 uF coupler, 100 kOhm slope, 0.01 uF to the Bass "
                     "wiper, 10 kOhm to ground. This drawing has no slope resistor and "
                     "no coupler at all, and puts the 10 kOhm in series with the 0.01 uF "
                     "between the plate and the stack, where bom.yaml's own role for it "
                     "says `tone network foot`.",
    "6g5:channel 2": "The 6G5's second channel mirrors channel 1 and carries the same "
                     "defect.",
    "6g6b:normal": "DEFECT (2026-09-09): the cited 6G6-B sheet draws the blackface "
                   "ladder — 100 kOhm slope off the plate, 0.1 uF to the tapped Treble "
                   "pot's 70 kOhm tap, 0.05 uF from the slope foot to the Bass foot, "
                   "6.8 kOhm to ground, and the Treble pot's own bottom lug bled to "
                   "ground through 0.005 uF. This drawing has no slope resistor and no "
                   "0.1 uF, runs the 0.05 uF from the plate instead, and collapses the "
                   "slope foot, the tap and the Bass foot into one node.",
}


def _parse_table(src: str, name: str) -> list:
    m = re.search(r"const " + name + r" = \[(.*?)\n\];", src, re.S)
    if not m:
        raise SystemExit(f"check_tonestack_wiring: {name} not found in corpus.js")
    # Whole-line `//` comments first: an entry that opens with one used to fall
    # out of the block pattern silently, and a spec this gate never parses is a
    # drawing this gate never walks while the summary still says zero failures.
    # That is how the 5F2-A — a *plotted* preset — went unwalked from the day it
    # landed. The count assertion below is what makes the silence impossible.
    body_src = "\n".join(ln for ln in m.group(1).split("\n") if not ln.lstrip().startswith("//"))
    specs = []
    for block in re.findall(r"\{\s*\n?\s*id: '([^']+)', kind: '([^']+)',(.*?)\n  \},", body_src, re.S):
        amp, kind, body = block
        refs = {}
        rm = re.search(r"refs: \{([^}]*)\}", body)
        if rm:
            for k, v in re.findall(r"(\w+): '([^']+)'", rm.group(1)):
                refs[k] = v
        mid = None
        mm = re.search(r"midLeg: \{ kind: '([^']+)'(?:, ref: '([^']+)')? \}", body)
        if mm:
            mid = (mm.group(1), mm.group(2))
        wm = re.search(r"wiring: '([^']+)'", body)
        wiring = wm.group(1) if wm else "joined"
        cm = re.search(r"channel: '([^']+)'", body)
        specs.append({"id": amp, "kind": kind, "refs": refs, "midLeg": mid,
                      "wiring": wiring, "channel": cm.group(1) if cm else None})
    written = len(re.findall(r"^\s*id: '", body_src, re.M))
    if written != len(specs):
        raise SystemExit(f"check_tonestack_wiring: {name} declares {written} entr(ies) but "
                         f"{len(specs)} parsed — an entry this gate cannot read is a "
                         "network it silently does not walk. Fix the table's shape.")
    return specs


def load_specs() -> list:
    """Every tone-stack network the site's tables declare: the published
    presets (TONE_STACK_SPECS) plus the read-but-not-plotted networks
    (TONE_STACK_GATE_EXTRAS), straight out of corpus.js."""
    src = CORPUS_JS.read_text(encoding="utf-8")
    specs = _parse_table(src, "TONE_STACK_SPECS")
    if not specs:
        raise SystemExit("check_tonestack_wiring: parsed no presets out of TONE_STACK_SPECS")
    extras = _parse_table(src, "TONE_STACK_GATE_EXTRAS")
    if not extras:
        raise SystemExit("check_tonestack_wiring: parsed no entries out of TONE_STACK_GATE_EXTRAS")
    return specs + extras


class Fail(Exception):
    pass


def _pairing(nets, ref_a, ref_b, label):
    """Two two-pin parts sharing exactly one net: returns (shared, other_a, other_b)."""
    a = [nets.pin(ref_a, "1"), nets.pin(ref_a, "2")]
    b = [nets.pin(ref_b, "1"), nets.pin(ref_b, "2")]
    shared = [x for x in a if x in b]
    if len(shared) != 1:
        raise Fail(f"{label}: {ref_a} and {ref_b} share {len(shared)} nets, expected exactly 1")
    s = shared[0]
    return s, next(x for x in a if x != s), next(x for x in b if x != s)


def _pot(nets, ref, want_ends, wiper_net, label):
    """A pot whose two end lugs sit on `want_ends` (either way round) and whose
    wiper sits on `wiper_net`."""
    ends = {nets.pin(ref, p) for p in POT_ENDS}
    if ends != set(want_ends):
        raise Fail(f"{label}: {ref} end lugs are not on the two expected nets")
    if nets.pin(ref, POT_WIPER) != wiper_net:
        raise Fail(f"{label}: {ref} wiper is not on the stack output net")


def check_ladder(amp: str, spec: dict) -> list:
    """The published-sheet wiring: treble-wiper-only output, bass rheostat,
    mid cap into the mid pot's wiper (or onto the fixed leg's top)."""
    path = ROOT / "amps" / amp / "schematic.kicad_sch"
    if not path.exists():
        return [f"{amp}: no schematic.kicad_sch"]
    nets = Nets(path)
    r = spec["refs"]
    problems = []
    try:
        gnd = nets.at(*nets.labels["GND"][0])

        # IN / N2 / N3 from the slope resistor and the treble cap.
        node_in, n2, n3 = _pairing(nets, r["slope"], r["trebleCap"], amp)
        # Some sheets pad the treble control with a resistor between the treble
        # capacitor and the pot's hot lug (the AA864's Bass Instrument channel
        # puts 250 kOhm above a 50 kOhm pot). Where a preset declares one, the
        # stack's N3 is the far side of it.
        if "trebleSeries" in r:
            ts = [nets.pin(r["trebleSeries"], "1"), nets.pin(r["trebleSeries"], "2")]
            if n3 not in ts:
                raise Fail(f"{amp}: treble series resistor {r['trebleSeries']} is not fed "
                           f"from the treble cap {r['trebleCap']}")
            n3 = next(x for x in ts if x != n3)
        # N4 hangs off the bass cap, which must be fed from N2.
        bc = [nets.pin(r["bassCap"], "1"), nets.pin(r["bassCap"], "2")]
        if n2 not in bc:
            raise Fail(f"{amp}: bass cap {r['bassCap']} is not fed from the slope foot")
        n4 = next(x for x in bc if x != n2)

        # Treble pot: end lugs on N3 and N4, wiper = the output, alone.
        out = nets.pin(r["treblePot"], POT_WIPER)
        _pot(nets, r["treblePot"], (n3, n4), out, amp)

        # Bass pot: a rheostat from N4 down to N5, wiper strapped to an end lug.
        bends = {nets.pin(r["bassPot"], p) for p in POT_ENDS}
        if n4 not in bends:
            raise Fail(f"{amp}: bass pot {r['bassPot']} does not sit on the bass-cap node")
        n5 = next(x for x in bends if x != n4)
        bwiper = nets.pin(r["bassPot"], POT_WIPER)
        if bwiper not in (n4, n5):
            raise Fail(f"{amp}: bass pot {r['bassPot']} wiper is not strapped — the "
                       "sheet draws a rheostat, so the wiper ties to one end of its track")
        if bwiper == out:
            raise Fail(f"{amp}: bass pot {r['bassPot']} wiper reaches the output — "
                       "that is the joined wiring, not the ladder the preset claims")

        if "midPot" in r:
            pins = {p: nets.pin(r["midPot"], p) for p in ("1", "2", "3")}
            ends = {pins["1"], pins["3"]}
            if n5 not in ends:
                raise Fail(f"{amp}: mid pot {r['midPot']} end lug is not on the bass-rheostat foot")
            cold_end = next(x for x in ends if x != n5)
            if "midCap" in r:
                mc = [nets.pin(r["midCap"], "1"), nets.pin(r["midCap"], "2")]
                if n2 not in mc:
                    raise Fail(f"{amp}: mid cap {r['midCap']} is not fed from the slope foot")
                mnode = next(x for x in mc if x != n2)
                if pins[POT_WIPER] != mnode:
                    raise Fail(f"{amp}: mid cap {r['midCap']} does not land on the mid pot's "
                               "wiper — the sheet feeds the wiper, not an end lug")
            # The cold end returns to ground, directly or (5F6) through the
            # presence pot in the stack's ground leg.
            if (spec["midLeg"] or ("", ""))[0] == "series":
                ref = spec["midLeg"][1]
                if cold_end not in {nets.pin(ref, p) for p in ("1", "2", "3")}:
                    raise Fail(f"{amp}: mid pot {r['midPot']} does not reach {ref}")
                if gnd not in {nets.pin(ref, p) for p in ("1", "2", "3")}:
                    raise Fail(f"{amp}: {ref} does not reach ground")
            elif cold_end != gnd:
                raise Fail(f"{amp}: mid pot {r['midPot']} cold end is not grounded")
        elif spec["midLeg"]:
            kind, ref = spec["midLeg"]
            if "midCap" in r:
                mc = [nets.pin(r["midCap"], "1"), nets.pin(r["midCap"], "2")]
                if {n2, n5} != set(mc):
                    raise Fail(f"{amp}: mid cap {r['midCap']} does not run from the slope "
                               "foot to the bass-rheostat foot")
            if kind == "fixed":
                legs = {nets.pin(ref, "1"), nets.pin(ref, "2")}
                if legs != {n5, gnd}:
                    raise Fail(f"{amp}: mid-leg resistor {ref} does not run from the "
                               "bass-rheostat foot to ground")
            elif kind == "ground" and n5 != gnd:
                raise Fail(f"{amp}: the bass-rheostat foot is not grounded")

        distinct = [node_in, n2, n3, out, n4, n5]
        if len(set(distinct)) != len(distinct):
            raise Fail(f"{amp}: two tone-stack nodes are shorted together")
    except Fail as exc:
        problems.append(str(exc))
    except KeyError as exc:
        problems.append(f"{amp}: reference {exc} is not in the drawing")
    return problems


def check_split(amp: str, spec: dict) -> list:
    """The 5F4's split network: two branches off the follower, recombined."""
    path = ROOT / "amps" / amp / "schematic.kicad_sch"
    if not path.exists():
        return [f"{amp}: no schematic.kicad_sch"]
    nets = Nets(path)
    r = spec["refs"]
    problems = []
    try:
        gnd = nets.at(*nets.labels["GND"][0])

        # IN from the treble cap and the bass-branch coupler, which share it.
        node_in, n3, n2 = _pairing(nets, r["trebleCap"], r["bassCoupler"], amp)

        # Treble branch: pot from N3 down to the shunt-cap node, wiper = OUT.
        sc = [nets.pin(r["trebleShuntCap"], "1"), nets.pin(r["trebleShuntCap"], "2")]
        if gnd not in sc:
            raise Fail(f"{amp}: treble shunt cap {r['trebleShuntCap']} does not reach ground")
        n5 = next(x for x in sc if x != gnd)
        out = nets.pin(r["treblePot"], POT_WIPER)
        _pot(nets, r["treblePot"], (n3, n5), out, amp)

        # Bass branch: N2 carries the leak to ground and the series resistor.
        sh = [nets.pin(r["bassShunt"], "1"), nets.pin(r["bassShunt"], "2")]
        if set(sh) != {n2, gnd}:
            raise Fail(f"{amp}: bass-branch leak {r['bassShunt']} does not run from the "
                       "coupler node to ground")
        se = [nets.pin(r["bassSeries"], "1"), nets.pin(r["bassSeries"], "2")]
        if n2 not in se:
            raise Fail(f"{amp}: bass-branch series resistor {r['bassSeries']} is not fed "
                       "from the coupler node")
        w = next(x for x in se if x != n2)

        # The branch injects at the bass pot's WIPER; one end lug is grounded,
        # the other carries the 0.005 µF leg.
        if nets.pin(r["bassPot"], POT_WIPER) != w:
            raise Fail(f"{amp}: the bass branch does not land on {r['bassPot']}'s wiper — "
                       "the sheet injects at the wiper, not an end lug")
        bends = {nets.pin(r["bassPot"], p) for p in POT_ENDS}
        if gnd not in bends:
            raise Fail(f"{amp}: neither end lug of {r['bassPot']} is grounded")
        n6 = next(x for x in bends if x != gnd)
        lc = [nets.pin(r["bassLegCap"], "1"), nets.pin(r["bassLegCap"], "2")]
        if set(lc) != {n6, gnd}:
            raise Fail(f"{amp}: bass leg cap {r['bassLegCap']} does not run from "
                       f"{r['bassPot']}'s far end lug to ground")

        # Recombination: 220k from the injection node to the treble wiper.
        os_ = [nets.pin(r["outSeries"], "1"), nets.pin(r["outSeries"], "2")]
        if set(os_) != {w, out}:
            raise Fail(f"{amp}: series resistor {r['outSeries']} does not run from the "
                       "bass injection node to the stack output")

        distinct = [node_in, n2, n3, out, w, n5, n6]
        if len(set(distinct)) != len(distinct):
            raise Fail(f"{amp}: two tone-network nodes are shorted together")
    except Fail as exc:
        problems.append(str(exc))
    except KeyError as exc:
        problems.append(f"{amp}: reference {exc} is not in the drawing")
    return problems


def check_treble_cut(amp: str, spec: dict) -> list:
    """The single-knob tweed cut: a capacitor and a rheostat in series from the
    signal node to ground. Either element may sit nearer the signal — a
    two-element series branch has no order — so the gate finds the branch rather
    than assuming one."""
    path = ROOT / "amps" / amp / "schematic.kicad_sch"
    if not path.exists():
        return [f"{amp}: no schematic.kicad_sch"]
    nets = Nets(path)
    r = spec["refs"]
    problems = []
    try:
        gnd = nets.at(*nets.labels["GND"][0])
        cap = [nets.pin(r["cutCap"], "1"), nets.pin(r["cutCap"], "2")]
        pot = {p: nets.pin(r["tonePot"], p) for p in ("1", "2", "3")}
        live = [n for n in pot.values() if n in cap]
        if not live:
            raise Fail(f"{amp}: tone pot {r['tonePot']} does not touch the cut capacitor "
                       f"{r['cutCap']}")
        mid = live[0]
        if gnd in cap:
            raise Fail(f"{amp}: cut capacitor {r['cutCap']} runs to ground on its own — "
                       f"the branch must reach ground through {r['tonePot']}")
        node_in = next(x for x in cap if x != mid)
        if node_in == gnd:
            raise Fail(f"{amp}: the cut branch's signal end is grounded")
        if gnd not in pot.values():
            raise Fail(f"{amp}: tone pot {r['tonePot']} does not reach ground")
        if pot[POT_WIPER] not in (mid, gnd):
            raise Fail(f"{amp}: tone pot {r['tonePot']} wiper is on a third live net — "
                       "that is a treble/cut blend, not the cut this preset claims")
        # A third lug may be strapped to either end of the branch or left
        # unwired (a waived open pin), but never taken anywhere else.
        stray = [p for p, n in pot.items() if n not in (mid, gnd)
                 and len(nets.nets().get(n, ())) > 1]
        if stray:
            raise Fail(f"{amp}: tone pot {r['tonePot']} lug(s) {', '.join(sorted(stray))} "
                       "are wired outside the cut branch")
    except Fail as exc:
        problems.append(str(exc))
    except KeyError as exc:
        problems.append(f"{amp}: reference {exc} is not in the drawing")
    return problems


def check(amp: str, spec: dict) -> list:
    if spec["kind"] == "single-knob":
        return check_treble_cut(amp, spec)
    if spec["kind"] == "split":
        return check_split(amp, spec)
    if spec.get("wiring") == "ladder":
        return check_ladder(amp, spec)
    path = ROOT / "amps" / amp / "schematic.kicad_sch"
    if not path.exists():
        return [f"{amp}: no schematic.kicad_sch"]
    nets = Nets(path)
    r = spec["refs"]
    problems = []
    try:
        gnd = nets.at(*nets.labels["GND"][0])

        # IN / N2 / N3 from the slope resistor and the treble cap.
        node_in, n2, n3 = _pairing(nets, r["slope"], r["trebleCap"], amp)
        # N4 hangs off the bass cap, which must be fed from N2.
        bc = [nets.pin(r["bassCap"], "1"), nets.pin(r["bassCap"], "2")]
        if n2 not in bc:
            raise Fail(f"{amp}: bass cap {r['bassCap']} is not fed from the slope foot")
        n4 = next(x for x in bc if x != n2)

        out = nets.pin(r["treblePot"], POT_WIPER)
        _pot(nets, r["treblePot"], (n3, n2), out, amp)

        # N5: the bass pot's far end lug.
        bends = {nets.pin(r["bassPot"], p) for p in POT_ENDS}
        if n4 not in bends:
            raise Fail(f"{amp}: bass pot {r['bassPot']} does not sit on the bass-cap node")
        n5 = next(x for x in bends if x != n4)
        _pot(nets, r["bassPot"], (n4, n5), out, amp)

        if "midCap" in r:
            mc = [nets.pin(r["midCap"], "1"), nets.pin(r["midCap"], "2")]
            if {n2, n5} != set(mc):
                raise Fail(f"{amp}: mid cap {r['midCap']} does not run from the slope foot "
                           "to the bass-pot foot")
        if "midPot" in r:
            pins = {p: nets.pin(r["midPot"], p) for p in ("1", "2", "3")}
            if n5 not in pins.values():
                raise Fail(f"{amp}: mid pot {r['midPot']} is not on the bass-pot foot")
            # Normally the mid pot's cold end is ground. One circuit returns it
            # through another control (the 5F6's presence pot); the preset says so.
            cold = gnd
            if (spec["midLeg"] or ("", ""))[0] == "series":
                ref = spec["midLeg"][1]
                between = set(pins.values()) & {nets.pin(ref, p) for p in ("1", "2", "3")}
                if not between:
                    raise Fail(f"{amp}: mid pot {r['midPot']} does not reach {ref}")
                if gnd not in {nets.pin(ref, p) for p in ("1", "2", "3")}:
                    raise Fail(f"{amp}: {ref} does not reach ground")
                cold = next(iter(between))
            if cold not in pins.values():
                raise Fail(f"{amp}: mid pot {r['midPot']} is not grounded")
            if pins[POT_WIPER] not in (n5, cold):
                raise Fail(f"{amp}: mid pot {r['midPot']} wiper is floating — the mid leg is "
                           "drawn as a rheostat, so the wiper ties to one end of its track")
        elif spec["midLeg"]:
            kind, ref = spec["midLeg"]
            if kind == "fixed":
                legs = {nets.pin(ref, "1"), nets.pin(ref, "2")}
                if legs != {n5, gnd}:
                    raise Fail(f"{amp}: mid-leg resistor {ref} does not run from the "
                               "bass-pot foot to ground")
            elif kind == "ground" and n5 != gnd:
                raise Fail(f"{amp}: the bass-pot foot is not grounded")

        distinct = [node_in, n2, n3, out, n4]
        if spec["kind"] == "fmv" or (spec["midLeg"] or ("", ""))[0] == "fixed":
            distinct.append(n5)
        if len(set(distinct)) != len(distinct):
            raise Fail(f"{amp}: two tone-stack nodes are shorted together")
    except Fail as exc:
        problems.append(str(exc))
    except KeyError as exc:
        problems.append(f"{amp}: reference {exc} is not in the drawing")
    return problems


WALKED_KINDS = ("fmv", "tb", "split", "single-knob")


def _corpus_tone_networks() -> dict:
    """{amp id: declared topology.tone_stack} for every circuit in amps/."""
    out = {}
    for d in sorted((ROOT / "amps").iterdir()):
        meta = d / "meta.yaml"
        if d.name.startswith("_") or not meta.is_file():
            continue
        doc = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        out[d.name] = ((doc.get("topology") or {}).get("tone_stack"))
    return out


def audit_coverage(specs: list) -> list:
    """Every circuit that draws a tone network is walked above or named in
    UNCHECKED_NETWORKS, and nothing is named there that is now walked.

    Without this, the gate's own summary is the misleading number: it counts the
    networks it was handed and says nothing about the ones nobody declared, so a
    tone network drawn on a sheet and compared against nothing reads as clean.
    """
    problems = []
    walked = {(s["id"], s.get("channel")) for s in specs}
    walked_ids = {i for i, _ in walked}
    declared = _corpus_tone_networks()

    for key in sorted(UNCHECKED_NETWORKS):
        amp, _, channel = key.partition(":")
        if amp not in declared:
            problems.append(f"UNCHECKED_NETWORKS names {key}, which is not a circuit here")
            continue
        if declared[amp] in (None, "none"):
            problems.append(f"UNCHECKED_NETWORKS names {key}, whose meta.yaml declares no "
                            "tone network — drop the entry")
            continue
        if (amp, channel or None) in walked:
            problems.append(f"UNCHECKED_NETWORKS still names {key}, which the spec tables "
                            "now walk — stale entry, drop it")

    named = {k.partition(":")[0] for k in UNCHECKED_NETWORKS}
    for amp, kind in sorted(declared.items()):
        if kind in (None, "none"):
            continue
        if amp not in walked_ids and amp not in named:
            problems.append(f"{amp} declares tone_stack: {kind} and is neither walked by a "
                            "spec nor named in UNCHECKED_NETWORKS — its drawn tone network "
                            "is compared against nothing")
    return problems


def main() -> int:
    specs = [s for s in load_specs() if s["kind"] in WALKED_KINDS]
    unwalkable = [s for s in load_specs() if s["kind"] not in WALKED_KINDS]
    failures = []
    for spec in specs:
        label = spec["id"] + (f" ({spec['channel']} channel)" if spec.get("channel") else "")
        problems = check(spec["id"], spec)
        if problems:
            failures.extend(problems)
            for p in problems:
                print(f"FAIL {p}")
        else:
            print(f"ok   {label}: drawing matches the declared {spec['kind']} "
                  f"network ({spec['wiring']} wiring)")
    for spec in unwalkable:
        failures.append(f"{spec['id']}: kind '{spec['kind']}' has no walker in this gate")
        print(f"FAIL {failures[-1]}")

    for p in audit_coverage(specs):
        failures.append(p)
        print(f"FAIL {p}")

    declared = _corpus_tone_networks()
    no_network = sorted(a for a, k in declared.items() if k in (None, "none"))
    print(f"\nchecked {len(specs)} tone network(s), {len(failures)} failure(s)")
    print(f"{len(no_network)} circuit(s) carry no tone control at all: "
          f"{', '.join(no_network)}")
    print(f"{len(UNCHECKED_NETWORKS)} drawn tone network(s) remain UNCHECKED — drawn on "
          "the sheet, compared against nothing:")
    for key in sorted(UNCHECKED_NETWORKS):
        for i, line in enumerate(textwrap.wrap(UNCHECKED_NETWORKS[key], 84)):
            print(f"  - {key}: {line}" if i == 0 else f"    {' ' * len(key)}  {line}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
