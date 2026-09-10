#!/usr/bin/env python3
"""CI gate: the reference architectures partition the corpus, and each one's
claims hold for every circuit it claims.

`reference/architectures/*.yaml` describes the handful of chassis architectures
the corpus's circuits fall into — the long-tailed pair on fixed bias, the
cathodyne on cathode bias, the single-ended practice amp, and so on. Each file
names its members by PREDICATE over `meta.topology` rather than by listing amp
ids, so a new circuit files itself and cannot be quietly left out.

The point of this gate is that an authored description is otherwise unfalsifiable.
Every other artifact in this archive is checked against something: a netlist
against a published chart, a drawing against its netlist, a layout against the
same. A prose model of "how this class is built" has no such anchor unless one is
built for it, and an unanchored model on a site whose whole claim is that its
claims are checked would be the weakest thing on it.

So each architecture states what must be true of its members, and this gate
proves it — against `netlist.cir` and `reference/loadlines.yaml`, not against the
same `meta.topology` fields the predicate already selects on. That independence is
the whole design: a disagreement means either the architecture is wrong or the
circuit's metadata is, and both are worth knowing.

    python3 check_architectures.py            # gate
    python3 check_architectures.py --report   # membership, one line per circuit
    python3 check_architectures.py --selftest # plant faults, prove each is caught

WHAT IS CHECKED

  * every circuit matches EXACTLY ONE architecture, or is a dated, reasoned
    exception — a circuit matching none is a gap in the taxonomy, and a circuit
    matching two means two predicates overlap;
  * no architecture is empty (a class with no members is a description of nothing);
  * `requires.output_stage` matches the stage `config` in reference/loadlines.yaml,
    which is derived from the netlist by export_loadlines.py;
  * `requires.negative_bias_supply` matches whether the circuit's netlist actually
    contains a negative DC source — the visible difference between a chassis that
    carries a bias rail and one that does not;
  * declarations are not stale: an exception naming a circuit that no longer
    matches, or does not exist, is an error rather than a silent no-op.

WHAT IS NOT CHECKED, AND IS NOT CLAIMED

The `sections` list is an editorial decomposition. This gate checks that it is
present, that its ids are unique and that it is not empty; it does not and cannot
verify that a section boundary is the right place to draw one. Nothing here
asserts physical layout, dimensions or clearances of any circuit.
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ARCH_DIR = ROOT / "reference" / "architectures"
LOADLINES = ROOT / "reference" / "loadlines.yaml"

# A negative rail as the netlists write one: `VBIAS NBIAS 0 DC -52`. The name
# varies (5g9 letters its own VB69), so match the shape, not the label.
NEG_SUPPLY = re.compile(r"^V[A-Z0-9_]+\s+\S+\s+0\s+DC\s+-\s*\d", re.M | re.I)

REQUIRED_KEYS = {"slug", "title", "summary", "predicate", "sections", "requires"}


def load_architectures() -> list[dict]:
    out = []
    for path in sorted(glob.glob(str(ARCH_DIR / "*.yaml"))):
        doc = yaml.safe_load(Path(path).read_text()) or {}
        doc["_path"] = str(Path(path).relative_to(ROOT))
        out.append(doc)
    return out


def load_circuits() -> dict[str, dict]:
    """amp id -> {topology, netlist text}. Circuits only; no template dirs."""
    out = {}
    for path in sorted(glob.glob(str(ROOT / "amps" / "*" / "meta.yaml"))):
        amp = Path(path).parent.name
        if amp.startswith("_"):
            continue
        meta = yaml.safe_load(Path(path).read_text()) or {}
        if not meta.get("id"):
            continue
        netlist = Path(path).parent / "netlist.cir"
        out[amp] = {
            "topology": meta.get("topology") or {},
            "netlist": netlist.read_text() if netlist.exists() else "",
            "has_netlist": netlist.exists(),
        }
    return out


def load_stage_configs() -> dict[str, str]:
    doc = yaml.safe_load(LOADLINES.read_text()) or {}
    return {s["amp"]: s.get("config") for s in doc.get("stages", [])}


def matches(pred: dict, topology: dict) -> bool:
    return all(topology.get(k) == v for k, v in (pred or {}).items())


def check(archs: list[dict], circuits: dict, configs: dict[str, str]) -> list[str]:
    errs: list[str] = []

    # ---- shape ----------------------------------------------------------
    seen_slugs: set[str] = set()
    for a in archs:
        where = a.get("_path", "?")
        missing = REQUIRED_KEYS - set(a)
        if missing:
            errs.append(f"{where}: missing key(s) {', '.join(sorted(missing))}")
            continue
        if a["slug"] in seen_slugs:
            errs.append(f"{where}: duplicate slug {a['slug']!r}")
        seen_slugs.add(a["slug"])
        if Path(where).stem != a["slug"]:
            errs.append(f"{where}: filename does not match slug {a['slug']!r}")
        if not a["sections"]:
            errs.append(f"{where}: no sections — an architecture with no decomposition "
                        f"describes nothing")
        ids = [s.get("id") for s in a["sections"]]
        if len(ids) != len(set(ids)):
            errs.append(f"{where}: duplicate section id(s)")
        if not a.get("predicate"):
            errs.append(f"{where}: empty predicate would claim every circuit")

    # ---- partition ------------------------------------------------------
    claims: dict[str, list[str]] = defaultdict(list)
    for a in archs:
        if not a.get("predicate"):
            continue
        for amp, c in circuits.items():
            if matches(a["predicate"], c["topology"]):
                claims[amp].append(a["slug"])

    for amp in sorted(circuits):
        held = claims.get(amp, [])
        excused = [a["slug"] for a in archs
                   if amp in (a.get("exceptions") or {})]
        if len(held) > 1:
            errs.append(f"{amp}: claimed by {len(held)} architectures "
                        f"({', '.join(held)}) — their predicates overlap")
        elif not held and not excused:
            t = circuits[amp]["topology"]
            errs.append(f"{amp}: matches no architecture "
                        f"(phase_inverter={t.get('phase_inverter')!r}, "
                        f"bias={t.get('bias')!r}) — extend the taxonomy or declare "
                        f"a dated exception")

    # ---- exceptions are live, not vestigial -----------------------------
    for a in archs:
        for amp, reason in (a.get("exceptions") or {}).items():
            if amp not in circuits:
                errs.append(f"{a['_path']}: exception names {amp!r}, which is not a circuit")
            elif not str(reason).strip():
                errs.append(f"{a['_path']}: exception for {amp} has no reason")
            elif matches(a.get("predicate") or {}, circuits[amp]["topology"]):
                errs.append(f"{a['_path']}: exception for {amp} is stale — it matches "
                            f"the predicate and needs no exception")

    # ---- the claims themselves, against independent data ----------------
    for a in archs:
        if not a.get("predicate"):
            continue
        members = [amp for amp in sorted(circuits)
                   if matches(a["predicate"], circuits[amp]["topology"])]
        if not members:
            errs.append(f"{a['_path']}: no circuit matches this predicate — an "
                        f"architecture with no members is a description of nothing")
        req = a.get("requires") or {}

        want_cfg = req.get("output_stage")
        if want_cfg:
            for amp in members:
                got = configs.get(amp)
                if got is None:
                    errs.append(f"{a['slug']}/{amp}: no output stage in "
                                f"reference/loadlines.yaml to check output_stage against")
                elif got != want_cfg:
                    errs.append(f"{a['slug']}/{amp}: declares output_stage "
                                f"{want_cfg!r} but the netlist's stage is {got!r}")

        if "negative_bias_supply" in req:
            want = bool(req["negative_bias_supply"])
            for amp in members:
                c = circuits[amp]
                if not c["has_netlist"]:
                    errs.append(f"{a['slug']}/{amp}: no netlist.cir to check "
                                f"negative_bias_supply against")
                    continue
                got = bool(NEG_SUPPLY.search(c["netlist"]))
                if got != want:
                    errs.append(
                        f"{a['slug']}/{amp}: declares negative_bias_supply={want} "
                        f"but its netlist {'has' if got else 'has no'} negative DC "
                        f"source")
    return errs


def report(archs, circuits, configs) -> None:
    for a in sorted(archs, key=lambda x: x.get("order", 99)):
        members = [amp for amp in sorted(circuits)
                   if matches(a.get("predicate") or {}, circuits[amp]["topology"])]
        req = a.get("requires") or {}
        print(f"\n{a['slug']}  ({len(members)} circuit(s))  {a['title']}")
        print(f"  predicate  {a.get('predicate')}")
        print(f"  requires   output_stage={req.get('output_stage')} "
              f"negative_bias_supply={req.get('negative_bias_supply')}")
        print(f"  sections   {', '.join(s.get('id','?') for s in a.get('sections') or [])}")
        print(f"  members    {' '.join(members)}")


def selftest() -> int:
    """Plant one fault per rule and prove it is caught."""
    archs = load_architectures()
    circuits = load_circuits()
    configs = load_stage_configs()

    base = check(archs, circuits, configs)
    if base:
        print("selftest ABORTED — the corpus is not clean to begin with:")
        for e in base:
            print("   " + e)
        return 1

    import copy
    cases: list[tuple[str, callable]] = []

    def overlap(a, c, cf):
        a = copy.deepcopy(a)
        a[0]["predicate"] = dict(a[1]["predicate"])
        return a, c, cf

    def uncovered(a, c, cf):
        c = copy.deepcopy(c)
        first = sorted(c)[0]
        c[first]["topology"]["phase_inverter"] = "no-such-inverter"
        return a, c, cf

    def wrong_cfg(a, c, cf):
        a = copy.deepcopy(a)
        for x in a:
            if (x.get("requires") or {}).get("output_stage") == "push-pull":
                x["requires"]["output_stage"] = "single-ended"
                break
        return a, c, cf

    def wrong_bias(a, c, cf):
        a = copy.deepcopy(a)
        for x in a:
            if (x.get("requires") or {}).get("negative_bias_supply") is True:
                x["requires"]["negative_bias_supply"] = False
                break
        return a, c, cf

    def stale_exception(a, c, cf):
        a = copy.deepcopy(a)
        members = [amp for amp in c
                   if matches(a[0].get("predicate") or {}, c[amp]["topology"])]
        a[0]["exceptions"] = {members[0]: "planted"}
        return a, c, cf

    def empty_arch(a, c, cf):
        a = copy.deepcopy(a)
        a[0]["predicate"] = {"phase_inverter": "nothing-matches-this"}
        return a, c, cf

    def no_sections(a, c, cf):
        a = copy.deepcopy(a)
        a[0]["sections"] = []
        return a, c, cf

    cases = [
        ("two predicates overlap", overlap),
        ("a circuit matches no architecture", uncovered),
        ("declared output_stage contradicts the netlist", wrong_cfg),
        ("declared negative_bias_supply contradicts the netlist", wrong_bias),
        ("an exception is stale", stale_exception),
        ("an architecture has no members", empty_arch),
        ("an architecture has no sections", no_sections),
    ]

    failures = 0
    for name, mutate in cases:
        a, c, cf = mutate(archs, circuits, configs)
        errs = check(a, c, cf)
        if errs:
            print(f"  ok   caught: {name}")
        else:
            print(f"  FAIL not caught: {name}")
            failures += 1
    print(f"\nselftest: {len(cases) - failures}/{len(cases)} planted fault(s) caught")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="print membership")
    ap.add_argument("--selftest", action="store_true",
                    help="plant faults and prove each is caught")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    archs = load_architectures()
    if not archs:
        print("no architectures found in reference/architectures/")
        return 1
    circuits = load_circuits()
    configs = load_stage_configs()

    if args.report:
        report(archs, circuits, configs)
        print()

    errs = check(archs, circuits, configs)
    for e in errs:
        print("FAIL " + e)
    covered = sum(
        1 for amp in circuits
        if any(matches(a.get("predicate") or {}, circuits[amp]["topology"]) for a in archs)
    )
    print(f"checked {len(archs)} architecture(s) over {len(circuits)} circuit(s); "
          f"{covered} circuit(s) claimed, {len(errs)} error(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
