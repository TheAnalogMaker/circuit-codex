#!/usr/bin/env python3
"""Simulate every amps/<id>/netlist.cir and compare the DC operating point
against amps/<id>/voltages.yaml.

voltages.yaml format:
    source: where the chart values come from
    nodes:
      BP2:  {chart: 325, tol_pct: 10}
      BP3:  {chart: null, note: "informational — no confirmed chart value"}

Behavior:
  - chart: <number>  -> compared within tol_pct.
  - chart: null      -> simulated value reported, never fails.
  - Deviations FAIL CI only when meta.yaml verification.status == verified;
    for draft circuits they are printed as warnings (the pilot's honesty rule:
    a circuit cannot be verified while chart and simulation disagree).

Runs ngspice with cwd = repo root so netlist .include paths are repo-relative.

The simulated numbers are also the site's:
    python3 pipeline/verify_amps.py --export   # write reference/op-points.yaml

Every amp page heads a table "Operating point vs. published chart", and until
this export existed that table had no simulated column at all — it printed the
chart, the tolerance and a note, and the prose beside it asserted a match the
reader could not check. The site cannot re-run ngspice at build time, so the
per-node simulated voltage is exported here, by the same run that gates it, and
read by site/src/lib/corpus.js.

A published number must never be a stale number, so the ordinary gate run (no
arguments) re-checks the committed file against what it just simulated and
FAILS if it has drifted. Regenerate with --export and commit the result.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reference" / "op-points.yaml"


class QStr(str):
    """A string that must survive both YAML loaders. Circuit ids like 5e1 are read
    as numbers by js-yaml (the site's loader) unless they are quoted — the same trap
    reference/loadlines.yaml guards against."""


yaml.SafeDumper.add_representer(
    QStr, lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'"))


HEADER = """\
# Simulated DC operating point, per circuit and per node — GENERATED FILE.
#
# Written by pipeline/verify_amps.py --export from each amp's own netlist.cir
# and the ngspice operating point the same script gates against the published
# chart in amps/<id>/voltages.yaml. Do not edit by hand; re-run the script and
# commit the result. A plain `python3 pipeline/verify_amps.py` run fails if this
# file no longer matches what it simulates.
#
# Every value below is SIMULATED, never measured. The chart values it is
# compared against, their tolerances and their notes stay in each amp's
# voltages.yaml — the site joins the two so a reader sees both columns.
#
# Circuit ids and node names are quoted throughout: js-yaml (the site's loader)
# reads a bare 5e1 as the number 50, and YAML 1.1 reads a bare node called ON or
# NO as a boolean. A key that changes type between loaders is a wrong voltage.
"""


def simulate(netlist: Path, nodes: list[str]) -> dict[str, float]:
    ngspice = shutil.which("ngspice")
    if not ngspice:
        sys.exit("FAIL ngspice not found on PATH")
    control = ["", ".control", "op"]
    for n in nodes:
        control.append(f"echo M {n}=$&v({n})")
    control += [".endc", ".end", ""]
    deck = netlist.read_text() + "\n".join(control)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False, dir=ROOT) as f:
        f.write(deck)
        path = f.name
    try:
        proc = subprocess.run([ngspice, "-b", path], capture_output=True, text=True,
                              timeout=120, cwd=ROOT)
    finally:
        Path(path).unlink(missing_ok=True)
    out = proc.stdout + proc.stderr
    vals: dict[str, float] = {}
    for k, v in re.findall(r"^M (\w+)=(\S+)$", out, flags=re.MULTILINE):
        try:
            vals[k] = float(v)
        except ValueError:
            sys.exit(f"FAIL unparsable node value {k}={v!r} in {netlist}\n{out}")
    missing = [n for n in nodes if n not in vals]
    if missing:
        sys.exit(f"FAIL nodes missing from simulation of {netlist}: {missing}\n{out}")
    return vals


def verify_amp(amp_dir: Path) -> tuple[int, int, dict[str, float]]:
    """Returns (hard_failures, warnings, simulated_volts_by_node)."""
    meta = yaml.safe_load((amp_dir / "meta.yaml").read_text())
    spec = yaml.safe_load((amp_dir / "voltages.yaml").read_text())
    status = (meta.get("verification") or {}).get("status", "draft")
    nodes = spec.get("nodes") or {}
    sim = simulate(amp_dir / "netlist.cir", list(nodes))

    hard, warn = 0, 0
    worst: tuple[float, str] | None = None
    print(f"{meta['id']} ({status}):")
    for name, entry in nodes.items():
        got = sim[name]
        chart = entry.get("chart")
        if chart is None:
            print(f"  info {name}: simulated {got:.1f} V (no confirmed chart value)")
            continue
        if entry.get("disputed"):
            if not entry.get("dispute_note"):
                print(f"  FAIL {name}: disputed chart value requires a dispute_note")
                hard += 1
                continue
            print(f"  disp {name}: simulated {got:.1f} V; printed chart {chart:g} V is disputed "
                  f"(excluded from gating — see note)")
            continue
        tol = entry.get("tol_pct", 5) / 100
        err = abs(got - chart) / abs(chart)
        ok = err <= tol
        if worst is None or err > worst[0]:
            worst = (err, name)
        marker = "ok  " if ok else ("WARN" if status == "draft" else "FAIL")
        print(f"  {marker} {name}: simulated {got:.1f} V, chart {chart:g} V "
              f"({err * 100:.1f}% off, tol {tol * 100:.0f}%)")
        if not ok:
            if status == "verified":
                hard += 1
            else:
                warn += 1

    # meta.yaml's max_deviation_pct is a hand-written mirror of the number this
    # run just computed, and the site prints it on the amp page. A mirror needs
    # a gate that executes it: the 5E4-A shipped 9.2 (its driver plate) while
    # its worst gated node was the 12AY7 cathode at 10.0. Wrong either way, so
    # this fails for draft and verified alike — like the dispute_note check, it
    # is an internal contradiction, not a chart disagreement.
    claimed = (meta.get("verification") or {}).get("max_deviation_pct")
    if claimed is not None:
        if worst is None:
            print(f"  FAIL max_deviation_pct: {claimed} declared but no node is gated")
            hard += 1
        elif abs(float(claimed) - worst[0] * 100) > 0.05:
            print(f"  FAIL max_deviation_pct: meta.yaml says {claimed}, worst gated "
                  f"node is {worst[1]} at {worst[0] * 100:.1f}%")
            hard += 1
    return hard, warn, sim


def export_text(sims: dict[str, dict[str, float]]) -> str:
    """The reference/op-points.yaml body for a whole run's simulated values.

    Simulated volts only. The chart value each is compared against, its tolerance
    and its note live in the amp's voltages.yaml and are not copied here: two
    copies of one number is exactly the drift this corpus gates against
    everywhere else. Rounded to 3 decimals — ngspice is deterministic on a fixed
    netlist, so the file regenerates byte-identical and can be a drift gate.
    """
    amps = {QStr(amp): {QStr(node): round(float(v), 3) for node, v in sorted(nodes.items())}
            for amp, nodes in sorted(sims.items())}
    return HEADER + yaml.safe_dump({"amps": amps}, sort_keys=False, allow_unicode=True,
                                   width=100)


def main() -> int:
    export = "--export" in sys.argv
    amp_dirs = sorted(d for d in (ROOT / "amps").iterdir()
                      if d.is_dir() and d.name != "_template" and (d / "netlist.cir").exists())
    if not amp_dirs:
        print("no amp netlists to verify")
        return 0
    total_hard, total_warn = 0, 0
    sims: dict[str, dict[str, float]] = {}
    for d in amp_dirs:
        if not (d / "voltages.yaml").exists():
            print(f"{d.name}: netlist present but no voltages.yaml — skipping (draft)")
            continue
        h, w, sim = verify_amp(d)
        total_hard += h
        total_warn += w
        sims[d.name] = sim
    text = export_text(sims)
    if export:
        OUT.write_text(text)
        nodes = sum(len(v) for v in sims.values())
        print(f"\nwrote {OUT.relative_to(ROOT)} — {len(sims)} circuit(s), {nodes} node(s)")
    else:
        # The amp pages print these numbers. A stale file would print a voltage
        # this run did not produce, so staleness is a hard failure like any other.
        rel = OUT.relative_to(ROOT)
        if not OUT.exists():
            print(f"\nFAIL {rel} missing — run pipeline/verify_amps.py --export")
            total_hard += 1
        elif OUT.read_text() != text:
            print(f"\nFAIL {rel} is stale — re-run pipeline/verify_amps.py --export")
            total_hard += 1
        else:
            print(f"\nok {rel} matches this run ({sum(len(v) for v in sims.values())} node(s))")
    print(f"{len(amp_dirs)} amp(s) simulated, {total_hard} failure(s), {total_warn} warning(s)")
    return 1 if total_hard else 0


if __name__ == "__main__":
    sys.exit(main())
