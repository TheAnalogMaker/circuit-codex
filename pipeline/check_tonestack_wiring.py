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

Run from pipeline/:  python3 check_tonestack_wiring.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from sch_nets import Nets

ROOT = Path(__file__).resolve().parent.parent
CORPUS_JS = ROOT / "site" / "src" / "lib" / "corpus.js"

# Pot pin numbers in the cx:POT library symbol: 1 and 3 are the track ends,
# 2 is the wiper.
POT_ENDS = ("1", "3")
POT_WIPER = "2"


def _parse_table(src: str, name: str) -> list:
    m = re.search(r"const " + name + r" = \[(.*?)\n\];", src, re.S)
    if not m:
        raise SystemExit(f"check_tonestack_wiring: {name} not found in corpus.js")
    specs = []
    for block in re.findall(r"\{\s*\n?\s*id: '([^']+)', kind: '([^']+)',(.*?)\n  \},", m.group(1), re.S):
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


def check(amp: str, spec: dict) -> list:
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


def main() -> int:
    specs = [s for s in load_specs() if s["kind"] in ("fmv", "tb", "split")]
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
    print(f"checked {len(specs)} tone stack(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
