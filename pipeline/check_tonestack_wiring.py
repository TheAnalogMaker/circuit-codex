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
corpus.js and this gate follows it.

Network asserted (node names as tonestack.js writes them):

    IN   stack input        slope resistor · treble cap
    N2   slope foot         slope resistor · treble-pot end lug · bass cap
                            · mid cap
    N3   treble-cap output  treble cap · treble-pot other end lug
    OUT  stack output       treble-pot wiper · bass-pot wiper
    N4   bass-cap output    bass cap · bass-pot end lug
    N5   mid-leg top        bass-pot other end lug · mid cap · mid leg

The mid leg is a pot wired as a rheostat (three-knob stacks), a fixed resistor
(blackface two-knob), or a direct ground (tweed two-knob). Which end lug of a
pot is the "10" end is a taper fact a drawing cannot carry, so the gate accepts
either orientation and only checks what the wires say.

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


def load_specs() -> list:
    """The tone-stack presets the site publishes, straight out of corpus.js."""
    src = CORPUS_JS.read_text(encoding="utf-8")
    m = re.search(r"const TONE_STACK_SPECS = \[(.*?)\n\];", src, re.S)
    if not m:
        raise SystemExit("check_tonestack_wiring: TONE_STACK_SPECS not found in corpus.js")
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
        specs.append({"id": amp, "kind": kind, "refs": refs, "midLeg": mid})
    if not specs:
        raise SystemExit("check_tonestack_wiring: parsed no presets out of TONE_STACK_SPECS")
    return specs


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


def check(amp: str, spec: dict) -> list:
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
    specs = [s for s in load_specs() if s["kind"] in ("fmv", "tb")]
    failures = []
    for spec in specs:
        problems = check(spec["id"], spec)
        if problems:
            failures.extend(problems)
            for p in problems:
                print(f"FAIL {p}")
        else:
            print(f"ok   {spec['id']}: drawing matches the plotted {spec['kind']} network")
    print(f"checked {len(specs)} tone stack(s), {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
