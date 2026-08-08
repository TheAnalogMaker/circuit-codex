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


def verify_amp(amp_dir: Path) -> tuple[int, int]:
    """Returns (hard_failures, warnings)."""
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
    return hard, warn


def main() -> int:
    amp_dirs = sorted(d for d in (ROOT / "amps").iterdir()
                      if d.is_dir() and d.name != "_template" and (d / "netlist.cir").exists())
    if not amp_dirs:
        print("no amp netlists to verify")
        return 0
    total_hard, total_warn = 0, 0
    for d in amp_dirs:
        if not (d / "voltages.yaml").exists():
            print(f"{d.name}: netlist present but no voltages.yaml — skipping (draft)")
            continue
        h, w = verify_amp(d)
        total_hard += h
        total_warn += w
    print(f"\n{len(amp_dirs)} amp(s) simulated, {total_hard} failure(s), {total_warn} warning(s)")
    return 1 if total_hard else 0


if __name__ == "__main__":
    sys.exit(main())
