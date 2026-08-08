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
# Arc rectifiers: the datasheet prints one *approximate* drop for the whole rated
# range, so the off-anchor points are held to +/-1 V of it (7% of 15 V) rather than
# to the 2% an exactly-solved anchor gets.
TOL_ARC = 0.07

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

# Mercury-vapour rectifiers are anchored the way their datasheets state them: a
# tube *drop* that is near-constant over the rated current range, not a current at
# a stated voltage. So this bench drives the rated current and reads the drop back,
# then repeats at a tenth of rated current and at the peak-plate rating — which is
# what makes the check meaningful (a space-charge diode would swing the drop by
# more than 10x across that span, an arc barely moves). Rsh conditions the matrix:
# an arc has almost no conductance below its striking voltage, so the anode node is
# otherwise floating at the initial guess. At 1 G it draws 15 nA against 225 mA.
ARC_RECT_BENCH = """* {name} arc-drop verification
.include {inc}
Ia 0 A DC {i_rated}
Rsh A 0 1g
X1 A 0 {name}
.nodeset v(A)={v_guess}
.control
op
echo M v_rated=$&v(A)
alter Ia = {i_low}
op
echo M v_low=$&v(A)
alter Ia = {i_peak}
op
echo M v_peak=$&v(A)
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

    print("12AU7 @ Va=250, Vg=-8.5:")
    r = run_bench(TRIODE_BENCH.format(name="12AU7", inc=MODELS / "12au7.inc",
                                      vp=250, vg=-8.5, vg_hi=-8.45, vg_lo=-8.55))
    failures += check("12AU7", "Ia", r["ia0"], 10.5e-3, TOL_I)
    failures += check("12AU7", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 2200e-6, TOL_GM)

    print("12AT7 @ Va=250, Vg=-2:")
    r = run_bench(TRIODE_BENCH.format(name="12AT7", inc=MODELS / "12at7.inc",
                                      vp=250, vg=-2, vg_hi=-1.95, vg_lo=-2.05))
    failures += check("12AT7", "Ia", r["ia0"], 10e-3, TOL_I)
    failures += check("12AT7", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 5500e-6, TOL_GM)

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

    print("KT66 @ Va=250, Vg2=250, Vg1=-15 (plate/gm anchor):")
    r = run_bench(PENTODE_BENCH.format(name="KT66", inc=MODELS / "kt66.inc",
                                       vp=250, vg2=250, vg1=-15,
                                       vg_hi=-14.95, vg_lo=-15.05))
    failures += check("KT66", "Ia", r["ia0"], 85e-3, TOL_I)
    failures += check("KT66", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 7000e-6, TOL_GM)

    print("KT66 @ Va=415, Vg2=300, Vg1=-27 (screen anchor):")
    r = run_bench(PENTODE_BENCH.format(name="KT66", inc=MODELS / "kt66.inc",
                                       vp=415, vg2=300, vg1=-27,
                                       vg_hi=-26.95, vg_lo=-27.05))
    failures += check("KT66", "Ig2", r["ig2"], 2.5e-3, TOL_I)

    print("EL34 @ Va=250, Vg2=250, Vg1=-13.5:")
    r = run_bench(PENTODE_BENCH.format(name="EL34", inc=MODELS / "el34.inc",
                                       vp=250, vg2=250, vg1=-13.5,
                                       vg_hi=-13.45, vg_lo=-13.55))
    failures += check("EL34", "Ia", r["ia0"], 100e-3, TOL_I)
    failures += check("EL34", "Ig2", r["ig2"], 14.9e-3, TOL_I)
    failures += check("EL34", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 12500e-6, TOL_GM)

    print("EL84 @ Va=250, Vg2=250, Vg1=-7.3:")
    r = run_bench(PENTODE_BENCH.format(name="EL84", inc=MODELS / "el84.inc",
                                       vp=250, vg2=250, vg1=-7.3,
                                       vg_hi=-7.25, vg_lo=-7.35))
    failures += check("EL84", "Ia", r["ia0"], 48e-3, TOL_I)
    failures += check("EL84", "Ig2", r["ig2"], 5.5e-3, TOL_I)
    failures += check("EL84", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 11300e-6, TOL_GM)

    print("EF86 @ Va=250, Vg2=140, Vg1=-2.2:")
    r = run_bench(PENTODE_BENCH.format(name="EF86", inc=MODELS / "ef86.inc",
                                       vp=250, vg2=140, vg1=-2.2,
                                       vg_hi=-2.15, vg_lo=-2.25))
    failures += check("EF86", "Ia", r["ia0"], 3.0e-3, TOL_I)
    failures += check("EF86", "Ig2", r["ig2"], 0.6e-3, TOL_I)
    failures += check("EF86", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 2200e-6, TOL_GM)

    print("6973 @ Va=250, Vg2=250, Vg1=-15:")
    r = run_bench(PENTODE_BENCH.format(name="6973", inc=MODELS / "6973.inc",
                                       vp=250, vg2=250, vg1=-15,
                                       vg_hi=-14.95, vg_lo=-15.05))
    failures += check("6973", "Ia", r["ia0"], 46e-3, TOL_I)
    failures += check("6973", "Ig2", r["ig2"], 3.5e-3, TOL_I)
    failures += check("6973", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 4800e-6, TOL_GM)

    print("7591 @ Va=300, Vg2=300, Vg1=-10:")
    r = run_bench(PENTODE_BENCH.format(name="7591", inc=MODELS / "7591.inc",
                                       vp=300, vg2=300, vg1=-10,
                                       vg_hi=-9.95, vg_lo=-10.05))
    failures += check("7591", "Ia", r["ia0"], 60e-3, TOL_I)
    failures += check("7591", "Ig2", r["ig2"], 8e-3, TOL_I)
    failures += check("7591", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 10200e-6, TOL_GM)

    # The 6SJ7 is the one pentode whose sheet tabulates plate current at two plate
    # voltages, so its KVB is fitted rather than defaulted (fit_models.py) — and both
    # columns are therefore checked here. The 100 V column is what the fit buys: on
    # the project default KVB it would read 8.8% low, past the tolerance below.
    print("6SJ7 @ Va=250, Vg2=100, Vg1=-3:")
    r = run_bench(PENTODE_BENCH.format(name="6SJ7", inc=MODELS / "6sj7.inc",
                                       vp=250, vg2=100, vg1=-3,
                                       vg_hi=-2.95, vg_lo=-3.05))
    failures += check("6SJ7", "Ia", r["ia0"], 3.0e-3, TOL_I)
    failures += check("6SJ7", "Ig2", r["ig2"], 0.8e-3, TOL_I)
    failures += check("6SJ7", "gm", (r["ia_hi"] - r["ia_lo"]) / 0.1, 1650e-6, TOL_GM)

    print("6SJ7 @ Va=100, Vg2=100, Vg1=-3 (second tabulated plate voltage):")
    r = run_bench(PENTODE_BENCH.format(name="6SJ7", inc=MODELS / "6sj7.inc",
                                       vp=100, vg2=100, vg1=-3,
                                       vg_hi=-2.95, vg_lo=-3.05))
    failures += check("6SJ7", "Ia @ Va=100", r["ia0"], 2.9e-3, TOL_I)
    failures += check("6SJ7", "gm @ Va=100", (r["ia_hi"] - r["ia_lo"]) / 0.1, 1575e-6, TOL_GM)

    print("EZ81 @ Va=10 (per anode):")
    r = run_bench(RECT_BENCH.format(name="EZ81", inc=MODELS / "ez81.inc", va=10))
    failures += check("EZ81", "Ia", r["ia0"], 60e-3, TOL_I)

    print("GZ34 @ Va=17 (per plate):")
    r = run_bench(RECT_BENCH.format(name="GZ34", inc=MODELS / "gz34.inc", va=17))
    failures += check("GZ34", "Ia", r["ia0"], 250e-3, TOL_I)

    print("5Y3GT @ Va=60 (per plate):")
    r = run_bench(RECT_BENCH.format(name="5Y3GT", inc=MODELS / "5y3gt.inc", va=60))
    failures += check("5Y3GT", "Ia", r["ia0"], 125e-3, TOL_I)

    print("5U4G @ Va=50 (per plate):")
    r = run_bench(RECT_BENCH.format(name="5U4G", inc=MODELS / "5u4g.inc", va=50))
    failures += check("5U4G", "Ia", r["ia0"], 200e-3, TOL_I)

    print("83 mercury-vapour arc drop (datasheet: approx 15 V, essentially constant):")
    r = run_bench(ARC_RECT_BENCH.format(name="83", inc=MODELS / "83.inc",
                                        i_rated="225m", i_low="22.5m", i_peak="1",
                                        v_guess=15))
    failures += check("83", "Vdrop @ 225 mA rated", r["v_rated"], 15.0, TOL_I)
    failures += check("83", "Vdrop @ 22.5 mA", r["v_low"], 15.0, TOL_ARC)
    failures += check("83", "Vdrop @ 1 A peak", r["v_peak"], 15.0, TOL_ARC)

    if failures:
        print(f"\n{len(failures)} anchor check(s) FAILED: {', '.join(failures)}")
        return 1
    print("\nall model anchor checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
