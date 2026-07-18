#!/usr/bin/env python3
"""Verify every model in models/ against its datasheet anchor point in ngspice.

For each tube: build a spec-point testbench, run `ngspice -b`, parse the
operating point, and assert the model reproduces the anchor within tolerance.
Exit non-zero on any failure (CI gate).

ngspice quirk: every `op` opens a new plot and `let` vectors live in the plot
that created them — so each measurement is echoed immediately after its own
`op`, and gm is computed here in Python from the finite difference.

Tolerances: anchored currents 2% (fit hits them analytically; slack covers
solver + simulator numerics), gm 5% (finite difference).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

TOL_I = 0.02
TOL_GM = 0.05

TRIODE_BENCH = """* {name} anchor-point verification
.include {inc}
Vp P 0 {vp}
Vg G 0 {vg}
X1 P G 0 {name}
.control
op
let ia = abs(i(Vp))
echo M ia0=$&ia
alter Vg = {vg_hi}
op
let ia = abs(i(Vp))
echo M ia_hi=$&ia
alter Vg = {vg_lo}
op
let ia = abs(i(Vp))
echo M ia_lo=$&ia
.endc
.end
"""

PENTODE_BENCH = """* {name} anchor-point verification
.include {inc}
Vp P 0 {vp}
Vs S 0 {vg2}
Vg G 0 {vg1}
X1 P S G 0 {name}
.control
op
let ia = abs(i(Vp))
let ig = abs(i(Vs))
echo M ia0=$&ia
echo M ig2=$&ig
alter Vg = {vg_hi}
op
let ia = abs(i(Vp))
echo M ia_hi=$&ia
alter Vg = {vg_lo}
op
let ia = abs(i(Vp))
echo M ia_lo=$&ia
.endc
.end
"""

RECT_BENCH = """* {name} anchor-point verification
.include {inc}
Va A 0 {va}
X1 A 0 {name}
.control
op
let ia = abs(i(Va))
echo M ia0=$&ia
.endc
.end
"""


def run_bench(deck: str) -> dict[str, float]:
    ngspice = shutil.which("ngspice")
    if not ngspice:
        sys.exit("FAIL ngspice not found on PATH")
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(deck)
        path = f.name
    proc = subprocess.run([ngspice, "-b", path], capture_output=True, text=True, timeout=60)
    out = proc.stdout + proc.stderr
    vals: dict[str, float] = {}
    for k, v in re.findall(r"^M (\w+)=(\S+)$", out, flags=re.MULTILINE):
        try:
            vals[k] = float(v)
        except ValueError:
            sys.exit(f"FAIL unparsable measurement {k}={v!r}\n--- output ---\n{out}")
    if not vals:
        sys.exit(f"FAIL no measurements from ngspice.\n--- deck ---\n{deck}\n--- output ---\n{out}")
    return vals


def check(name: str, key: str, got: float, want: float, tol: float) -> list[str]:
    err = abs(got - want) / abs(want)
    status = "ok " if err <= tol else "FAIL"
    print(f"  {status} {name} {key}: got {got:.4g}, anchor {want:.4g} ({err * 100:.2f}% off, tol {tol * 100:.0f}%)")
    return [] if err <= tol else [f"{name} {key}"]


def main() -> int:
    failures: list[str] = []

    print("12AX7 @ Va=250, Vg=-2:")
    r = run_bench(TRIODE_BENCH.format(name="12AX7", inc=MODELS / "12ax7.inc",
                                      vp=250, vg=-2, vg_hi=-1.95, vg_lo=-2.05))
    failures += check("12AX7", "Ia", r["ia0"], 1.2e-3, TOL_I)
    failures += check("12AX7", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 1600e-6, TOL_GM)

    print("12AY7 @ Va=250, Vg=-4:")
    r = run_bench(TRIODE_BENCH.format(name="12AY7", inc=MODELS / "12ay7.inc",
                                      vp=250, vg=-4, vg_hi=-3.95, vg_lo=-4.05))
    failures += check("12AY7", "Ia", r["ia0"], 3.0e-3, TOL_I)
    failures += check("12AY7", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 1750e-6, TOL_GM)

    print("6AT6 @ Va=250, Vg=-3 (triode unit):")
    r = run_bench(TRIODE_BENCH.format(name="6AT6", inc=MODELS / "6at6.inc",
                                      vp=250, vg=-3, vg_hi=-2.95, vg_lo=-3.05))
    failures += check("6AT6", "Ia", r["ia0"], 1.0e-3, TOL_I)
    failures += check("6AT6", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 1200e-6, TOL_GM)

    print("6V6GT @ Va=250, Vg2=250, Vg1=-12.5:")
    r = run_bench(PENTODE_BENCH.format(name="6V6GT", inc=MODELS / "6v6gt.inc",
                                       vp=250, vg2=250, vg1=-12.5,
                                       vg_hi=-12.45, vg_lo=-12.55))
    failures += check("6V6GT", "Ia", r["ia0"], 45e-3, TOL_I)
    failures += check("6V6GT", "Ig2", r["ig2"], 4.5e-3, TOL_I)
    failures += check("6V6GT", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 4100e-6, TOL_GM)

    print("5881 @ Va=250, Vg2=250, Vg1=-14:")
    r = run_bench(PENTODE_BENCH.format(name="5881", inc=MODELS / "5881.inc",
                                       vp=250, vg2=250, vg1=-14,
                                       vg_hi=-13.95, vg_lo=-14.05))
    failures += check("5881", "Ia", r["ia0"], 72e-3, TOL_I)
    failures += check("5881", "Ig2", r["ig2"], 5e-3, TOL_I)
    failures += check("5881", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 6000e-6, TOL_GM)

    print("GZ34 @ Va=17 (per plate):")
    r = run_bench(RECT_BENCH.format(name="GZ34", inc=MODELS / "gz34.inc", va=17))
    failures += check("GZ34", "Ia", r["ia0"], 250e-3, TOL_I)

    print("5Y3GT @ Va=60 (per plate):")
    r = run_bench(RECT_BENCH.format(name="5Y3GT", inc=MODELS / "5y3gt.inc", va=60))
    failures += check("5Y3GT", "Ia", r["ia0"], 125e-3, TOL_I)

    if failures:
        print(f"\n{len(failures)} anchor check(s) FAILED: {', '.join(failures)}")
        return 1
    print("\nall model anchor checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
