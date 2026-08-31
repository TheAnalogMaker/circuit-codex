#!/usr/bin/env python3
"""Fit Koren-form tube models to tabulated datasheet anchor points and emit
CC0-licensed ngspice .subckt files into models/.

Methodology: models/METHODOLOGY.md. Anchors are the published "average
characteristics" operating points from the RCA Receiving Tube Manual (RC-19,
1959). Equations follow the Koren model form (N. Koren, "Improved vacuum-tube
models for SPICE simulations", Glass Audio 8(5), 1996) — used as published
methodology; every parameter below is fitted here, none copied from existing
model collections.

Deterministic: re-running regenerates byte-identical .inc files.
Pure stdlib — no scipy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# Project defaults, documented in METHODOLOGY.md:
EX = 1.5          # Child-Langmuir 3/2-power law exponent
KVB_TRIODE = 300  # knee parameter (V^2); negligible effect at anchor region
KVB_PENTODE = 30  # pentode knee voltage parameter (V)


def _sig(z: float) -> float:
    if z > 30:
        return 1.0
    if z < -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def _softplus(z: float) -> float:
    if z > 30:
        return z
    return math.log1p(math.exp(z))


def _bisect(f, lo: float, hi: float, tol: float = 1e-12, iters: int = 200) -> float:
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError(f"bisection bracket failed: f({lo})={flo}, f({hi})={fhi}")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if abs(fmid) < tol or (hi - lo) < tol * max(1.0, mid):
            return mid
        if flo * fmid <= 0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)


@dataclass
class TriodeFit:
    name: str
    mu: float
    kp: float
    kg1: float
    ex: float = EX
    kvb: float = KVB_TRIODE


def fit_triode(name: str, mu: float, vp: float, vg: float, ia: float, gm: float) -> TriodeFit:
    """Solve KP, KG1 so the model reproduces (ia, gm) exactly at the anchor."""
    s = math.sqrt(KVB_TRIODE + vp * vp)
    a = 1.0 / mu + vg / s
    r_target = gm / ia

    def ratio_err(kp: float) -> float:
        z = kp * a
        return EX * kp * _sig(z) / (s * _softplus(z)) - r_target

    kp = _bisect(ratio_err, 1e-3, 5000.0)
    e1 = (vp / kp) * _softplus(kp * a)
    kg1 = e1 ** EX / ia
    return TriodeFit(name=name, mu=mu, kp=kp, kg1=kg1)


def _triode_ia(vp: float, vg: float, mu: float, kp: float, kg1: float,
               ex: float, kvb: float) -> float:
    """Koren triode plate current — the same expression emitted into the .inc."""
    s = math.sqrt(kvb + vp * vp)
    e1 = (vp / kp) * _softplus(kp * (1.0 / mu + vg / s))
    return (e1 ** ex) / kg1 if e1 > 0.0 else 0.0


def _triode_gm(vp: float, vg: float, p: dict, d: float = 2e-3) -> float:
    return (_triode_ia(vp, vg + d, **p) - _triode_ia(vp, vg - d, **p)) / (2 * d)


def _nelder_mead(f, x0: list[float], step: float = 0.4,
                 iters: int = 8000, tol: float = 1e-16) -> list[float]:
    """Deterministic simplex minimiser (pure stdlib). Fixed start + iteration
    count -> re-running regenerates byte-identical parameters."""
    n = len(x0)
    simplex = [list(x0)]
    for i in range(n):
        pt = list(x0)
        pt[i] += step
        simplex.append(pt)
    fv = [f(pt) for pt in simplex]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda k: fv[k])
        simplex = [simplex[k] for k in order]
        fv = [fv[k] for k in order]
        if abs(fv[-1] - fv[0]) < tol:
            break
        cen = [sum(simplex[k][j] for k in range(n)) / n for j in range(n)]
        xr = [cen[j] + (cen[j] - simplex[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < fv[0]:
            xe = [cen[j] + 2 * (cen[j] - simplex[-1][j]) for j in range(n)]
            fe = f(xe)
            simplex[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fv[-2]:
            simplex[-1], fv[-1] = xr, fr
        else:
            xc = [cen[j] + 0.5 * (simplex[-1][j] - cen[j]) for j in range(n)]
            fc = f(xc)
            if fc < fv[-1]:
                simplex[-1], fv[-1] = xc, fc
            else:
                for k in range(1, n + 1):
                    simplex[k] = [simplex[0][j] + 0.5 * (simplex[k][j] - simplex[0][j])
                                  for j in range(n)]
                    fv[k] = f(simplex[k])
    order = sorted(range(n + 1), key=lambda k: fv[k])
    return simplex[order[0]]


def fit_triode_multipoint(name: str, mu: float,
                          ia_points: list[tuple[float, float, float]],
                          gm_anchor: tuple[float, float, float]) -> TriodeFit:
    """v1 multi-point fit (12AX7 calibration study, reference/studies/
    12ax7-calibration.md). Fixes EX=1.5 (Child-Langmuir) and MU to the
    datasheet amplification factor, then frees KP, KG1, KVB to fit the plate
    current at every point in `ia_points` [(vp, vg, ia)] plus transconductance
    at `gm_anchor` (vp, vg, gm) in least squares on relative error. Unlike the
    single-anchor `fit_triode`, this constrains the plate-current curve at two
    plate voltages so it does not fall away below the 250 V anchor."""
    def objective(x: list[float]) -> float:
        kp, kg1, kvb = math.exp(x[0]), math.exp(x[1]), math.exp(x[2])
        p = dict(mu=mu, kp=kp, kg1=kg1, ex=EX, kvb=kvb)
        s = 0.0
        for vp, vg, ia_t in ia_points:
            s += ((_triode_ia(vp, vg, **p) - ia_t) / ia_t) ** 2
        vp, vg, gm_t = gm_anchor
        s += ((_triode_gm(vp, vg, p) - gm_t) / gm_t) ** 2
        return s

    x = _nelder_mead(objective, [math.log(400.0), math.log(550.0), math.log(300.0)])
    return TriodeFit(name=name, mu=mu, kp=math.exp(x[0]),
                     kg1=math.exp(x[1]), kvb=math.exp(x[2]))


@dataclass
class PentodeFit:
    name: str
    mu: float
    kp: float
    kg1: float
    kg2: float
    ex: float = EX
    kvb: float = KVB_PENTODE


def fit_pentode(name: str, mu: float, vp: float, vg2: float, vg1: float,
                ia: float, ig2: float, gm: float,
                vg2_s: float | None = None, vg1_s: float | None = None,
                kvb: float = KVB_PENTODE) -> PentodeFit:
    """Solve KP, KG1 so the model reproduces (ia, gm) at the plate anchor
    (vp, vg2, vg1). KG2 is fit to Ig2 at a screen anchor which may differ from
    the plate anchor: pass vg2_s/vg1_s when the datasheet tabulates screen
    current at a different operating point than gm/Ia (both default to the
    plate anchor's vg2/vg1, preserving the single-point behaviour).

    `kvb` defaults to the project pentode default (30 V); pass a fitted value
    only when the datasheet itself measures the plate-voltage dependence — see
    fit_pentode_kvb_from_plate_pair()."""
    a = 1.0 / mu + vg1 / vg2
    r_target = gm / ia

    def ratio_err(kp: float) -> float:
        z = kp * a
        e1 = (vg2 / kp) * _softplus(z)
        return EX * _sig(z) / e1 - r_target

    kp = _bisect(ratio_err, 1e-3, 5000.0)
    e1 = (vg2 / kp) * _softplus(kp * a)
    kg1 = (e1 ** EX) * math.atan(vp / kvb) / ia
    vg2s = vg2 if vg2_s is None else vg2_s
    vg1s = vg1 if vg1_s is None else vg1_s
    e2 = vg2s / mu + vg1s
    kg2 = (e2 ** EX) / ig2
    return PentodeFit(name=name, mu=mu, kp=kp, kg1=kg1, kg2=kg2, kvb=kvb)


def _pentode_ia(vp: float, vg2: float, vg1: float, mu: float, kp: float,
                kg1: float, kvb: float) -> float:
    """Koren pentode plate current — the same expression emitted into the .inc."""
    e1 = (vg2 / kp) * _softplus(kp * (1.0 / mu + vg1 / vg2))
    return (e1 ** EX) / kg1 * math.atan(vp / kvb) if e1 > 0.0 else 0.0


def _pentode_ig2(vg2: float, vg1: float, mu: float, kg2: float) -> float:
    """Koren pentode screen current — the same expression emitted into the .inc
    (uramp: no screen current once the grid drives the equivalent voltage negative)."""
    e2 = vg2 / mu + vg1
    return (e2 ** EX) / kg2 if e2 > 0.0 else 0.0


def fit_pentode_kvb_from_plate_pair(vp_a: float, ia_a: float,
                                    vp_b: float, ia_b: float) -> float:
    """Fit KVB to a datasheet that tabulates plate current at TWO plate voltages
    at the same grid and screen voltages.

    In this model form the only plate-voltage dependence is the atan(Va/KVB)
    factor, so such a pair measures KVB directly: solve
    atan(vp_b/KVB)/atan(vp_a/KVB) = ia_b/ia_a. This is the pentode analogue of
    the 12AX7's two-point treatment — the project default (30 V) is used
    everywhere the sheet publishes only one plate voltage, because then nothing
    in the data constrains it."""
    target = ia_b / ia_a
    return _bisect(lambda k: math.atan(vp_b / k) / math.atan(vp_a / k) - target,
                   1e-2, 1.0e4)


def solve_pentode_mu(vp: float, vg2: float, vg1: float, ia: float, ig2: float,
                     gm: float,
                     ia_rows: list[tuple[float, float, float, float]],
                     ig2_rows: list[tuple[float, float, float]],
                     kvb: float = KVB_PENTODE, grid_n: int = 400) -> float:
    """Solve MU from a sheet's own extra tabulated operating rows, for tubes
    whose publisher prints no amplification factor at all.

    MU is the one Koren parameter that cannot be solved from a single operating
    point: it only ever appears as Vg2/MU + Vg1, so at fixed Vg2 it is a pure
    offset. Where a sheet tabulates further rows at *different* screen voltages,
    those rows measure it. For each candidate MU the anchor fit is run exactly as
    usual (KP, KG1, KG2 solved so Ia, gm and Ig2 are reproduced at the anchor),
    and the candidate is scored by the relative error it leaves on the extra
    rows — `ia_rows` as (Va, Vg2, Vg1, Ia), `ig2_rows` as (Vg2, Vg1, Ig2).

    The search bracket is analytic, not guessed. Below
        MU_floor = Vg2 / (EX/(gm/Ia) + |Vg1|)
    the anchor is unreachable: gm/Ia can never exceed EX/(Vg2/MU + Vg1) in this
    form, so fit_pentode's bisection has no bracket. Above
        MU_cutoff = Vg2 / |Vg1|
    the anchor sits past cutoff and the tube draws nothing. A fixed-count grid
    scan then a golden-section refinement inside the winning cell keeps the
    result deterministic (byte-identical .inc files on re-run)."""
    mu_floor = vg2 / (EX / (gm / ia) + abs(vg1))
    mu_cutoff = vg2 / abs(vg1)

    def score(mu: float) -> float:
        try:
            f = fit_pentode("_", mu=mu, vp=vp, vg2=vg2, vg1=vg1,
                            ia=ia, ig2=ig2, gm=gm, kvb=kvb)
        except ValueError:
            return float("inf")
        s = 0.0
        for rvp, rvg2, rvg1, ria in ia_rows:
            s += ((_pentode_ia(rvp, rvg2, rvg1, mu, f.kp, f.kg1, kvb) - ria) / ria) ** 2
        for rvg2, rvg1, rig in ig2_rows:
            got = _pentode_ig2(rvg2, rvg1, mu, f.kg2)
            # A candidate MU that puts a tabulated screen current at zero is not
            # "slightly wrong", it is disqualified; score it far off rather than 0.
            s += ((got - rig) / rig) ** 2 if got > 0.0 else 1.0e6
        return s

    grid = [mu_floor + (mu_cutoff - mu_floor) * (i + 0.5) / grid_n
            for i in range(grid_n)]
    vals = [score(m) for m in grid]
    k = min(range(grid_n), key=lambda i: vals[i])
    lo = grid[max(0, k - 1)]
    hi = grid[min(grid_n - 1, k + 1)]
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = hi - inv_phi * (hi - lo), lo + inv_phi * (hi - lo)
    for _ in range(200):
        if score(c) < score(d):
            hi = d
        else:
            lo = c
        c, d = hi - inv_phi * (hi - lo), lo + inv_phi * (hi - lo)
    return 0.5 * (lo + hi)


def fit_rectifier_perveance(v_drop: float, i_at_drop: float) -> float:
    """Child's-law diode: I = P * V^1.5, P from the published drop anchor."""
    return i_at_drop / (v_drop ** 1.5)


def arc_rectifier(v_arc: float, i_ref: float, v_soft: float) -> tuple[float, float, float]:
    """Mercury-vapour rectifier: a gas discharge, NOT a space-charge-limited
    vacuum diode, so Child's law does not describe it. Once the arc strikes, the
    drop is set by the mercury ionisation potential and barely moves with current
    — the datasheets tabulate it as a single number ("Tube Voltage Drop (Approx.)")
    rather than a V/I pair.

    Model form: I = i_ref * exp((V - v_arc) / v_soft), i.e. an exponential arc
    conductance pinned to the datasheet drop at the tube's rated d-c output
    current. Nothing is solved: `v_arc` and `i_ref` are read straight off the
    sheet. `v_soft` is a project shaping choice, not a fit — it is the only free
    number, and it is set so the drop stays inside +/-1 V of the datasheet figure
    across the tube's whole rated conduction range, which is all the datasheet
    itself claims. Returned unchanged so the emitted header can state all three.
    """
    return v_arc, i_ref, v_soft


def _header(lines: list[str]) -> str:
    out = ["* " + ln if ln else "*" for ln in lines]
    return "\n".join(out)


def emit_triode(fit: TriodeFit, caps: dict[str, float], anchor_desc: str) -> str:
    f = fit
    body = f""".subckt {f.name} P G K
* fitted: MU={f.mu:g} EX={f.ex:g} KG1={f.kg1:.6g} KP={f.kp:.6g} KVB={f.kvb:g}
Bp P K I=pow(uramp((V(P,K)/{f.kp:.6g})*ln(1+exp({f.kp:.6g}*(1/{f.mu:g}+V(G,K)/sqrt({f.kvb:g}+V(P,K)*V(P,K)))))),{f.ex:g})/{f.kg1:.6g}
Cgk G K {caps['cgk']:g}p
Cgp G P {caps['cgp']:g}p
Cpk P K {caps['cpk']:g}p
.ends {f.name}"""
    return body


def emit_pentode(fit: PentodeFit, caps: dict[str, float]) -> str:
    f = fit
    body = f""".subckt {f.name} P G2 G1 K
* fitted: MU={f.mu:g} EX={f.ex:g} KG1={f.kg1:.6g} KG2={f.kg2:.6g} KP={f.kp:.6g} KVB={f.kvb:g}
Bp P K I=pow(uramp((V(G2,K)/{f.kp:.6g})*ln(1+exp({f.kp:.6g}*(1/{f.mu:g}+V(G1,K)/V(G2,K))))),{f.ex:g})/{f.kg1:.6g}*atan(V(P,K)/{f.kvb:g})
Bg2 G2 K I=pow(uramp(V(G2,K)/{f.mu:g}+V(G1,K)),{f.ex:g})/{f.kg2:.6g}
Cg1k G1 K {caps['cin']:g}p
Cg1p G1 P {caps['cgp']:g}p
Cpk P K {caps['cout']:g}p
.ends {f.name}"""
    return body


KOREN_EQUATIONS = [
    "Equations: Koren model form — N. Koren, 'Improved vacuum-tube models for",
    "  SPICE simulations', Glass Audio 8(5), 1996 (published methodology; all",
    "  parameters fitted by Circuit Codex, none copied from other collections).",
]


def common_header(tube: str, anchor: str, extra: list[str] | None = None,
                  source: str = "RCA Receiving Tube Manual RC-19, 1959, average characteristics",
                  equations: list[str] | None = None) -> str:
    lines = [
        f"{tube} — Circuit Codex tube model",
        "License: CC0 1.0 Universal (public domain dedication)",
        "  https://creativecommons.org/publicdomain/zero/1.0/",
        *(KOREN_EQUATIONS if equations is None else equations),
        f"Anchor ({source}): {anchor}",
        "Method + limitations: models/METHODOLOGY.md",
        "Generated by pipeline/fit_models.py — edit anchors there, not here.",
        "Heater not modeled (rated heater assumed). No grid-current model (v0).",
    ]
    if extra:
        lines += extra
    return _header(lines)


def main() -> None:
    MODELS_DIR.mkdir(exist_ok=True)

    # ---- 12AX7: v1 multi-point fit to the two tabulated operating points that
    #      RCA, GE, Sylvania and Philips/Mullard all print identically
    #      (reference/studies/12ax7-calibration.md):
    #        Va=250 V, Vg=-2 V -> Ia=1.2 mA, gm=1600 umho
    #        Va=100 V, Vg=-1 V -> Ia=0.5 mA (gm=1250 umho)
    #      MU=100, EX=1.5 fixed; KP, KG1, KVB fitted so the plate-current curve
    #      holds at both plate voltages (single-anchor v0 fell to ~0.15 mA at the
    #      100 V point). The disputed RCA 92CM-6879 plate family (~0.5-0.85 mA at
    #      250 V/-2 V) is deliberately NOT used — see the study.
    ax7 = fit_triode_multipoint(
        "12AX7", mu=100.0,
        ia_points=[(250.0, -2.0, 1.2e-3), (100.0, -1.0, 0.5e-3)],
        gm_anchor=(250.0, -2.0, 1600e-6))
    txt = common_header("12AX7 dual triode (one section)",
                        "Va=250 V/-2 V -> 1.2 mA, 1600 umho AND Va=100 V/-1 V -> 0.5 mA (mu=100); "
                        "v1 two-point fit, see reference/studies/12ax7-calibration.md") + "\n" + \
        emit_triode(ax7, {"cgk": 1.6, "cgp": 1.7, "cpk": 0.46}, "") + "\n"
    (MODELS_DIR / "12ax7.inc").write_text(txt)

    # ---- 12AY7: Va=250 V, Vg=-4 V -> Ia=3.0 mA, gm=1750 umho, mu=44
    ay7 = fit_triode("12AY7", mu=44.0, vp=250.0, vg=-4.0, ia=3.0e-3, gm=1750e-6)
    txt = common_header("12AY7 dual triode (one section)",
                        "Va=250 V, Vg=-4 V -> Ia=3.0 mA, gm=1750 umho, mu=44") + "\n" + \
        emit_triode(ay7, {"cgk": 1.3, "cgp": 1.3, "cpk": 0.6}, "") + "\n"
    (MODELS_DIR / "12ay7.inc").write_text(txt)

    # ---- 12AU7 (ECC82): medium-mu twin triode (mu=17), the Vox AC15's vibrato
    #      modulator valve. RCA 12AU7-A tabulated Class-A1 average characteristics,
    #      Va=250 V point: Vg=-8.5 V -> Ia=10.5 mA, gm=2200 umho, rp=7700 ohm,
    #      mu=17. Single-anchor fit at that point (KP, KG1 solved to Ia+gm),
    #      matching the 12AY7/12AT7 treatment; MU=17, EX=1.5 fixed.
    au7 = fit_triode("12AU7", mu=17.0, vp=250.0, vg=-8.5, ia=10.5e-3, gm=2200e-6)
    txt = common_header("12AU7 medium-mu twin triode (one section)",
                        "Va=250 V, Vg=-8.5 V -> Ia=10.5 mA, gm=2200 umho, mu=17",
                        ["European designation ECC82. Used in this corpus only as the",
                         "AC15 vibrato modulator, which the DC netlist does not solve",
                         "(a running phase-shift network has no static operating point),",
                         "so this model is anchor-verified but not yet exercised by an",
                         "amp simulation. Single-anchor v0 fit — see METHODOLOGY.md.",
                         "Node order: P G K"]) + "\n" + \
        emit_triode(au7, {"cgk": 1.6, "cgp": 1.5, "cpk": 0.5}, "") + "\n"
    (MODELS_DIR / "12au7.inc").write_text(txt)

    # ---- 6AT6 (triode unit): Va=250 V, Vg=-3 V -> Ia=1.0 mA, gm=1200 umho, mu=70
    at6 = fit_triode("6AT6", mu=70.0, vp=250.0, vg=-3.0, ia=1.0e-3, gm=1200e-6)
    txt = common_header("6AT6 twin-diode / high-mu triode (triode unit only)",
                        "Va=250 V, Vg=-3 V -> Ia=1.0 mA, gm=1200 umho, mu=70",
                        ["Diode units (plate No.1, plate No.2) are unused in this corpus",
                         "and are not modeled; only the triode amplifier section is fitted.",
                         "Node order: P G K (triode plate=pin7, grid=pin1, cathode=pin2)"]) + "\n" + \
        emit_triode(at6, {"cgk": 2.2, "cgp": 2.0, "cpk": 0.8}, "") + "\n"
    (MODELS_DIR / "6at6.inc").write_text(txt)

    # ---- 12AT7: high-mu twin triode (mu=60). RCA 12AT7 data sheet (March 1954)
    #      tabulated Class-A1 characteristics, Va=250 V point: cathode-bias 200 ohm,
    #      Ia=10 mA -> Vg=-2.0 V, gm=5500 umho, rp=10900 ohm, mu=60. (The sheet's
    #      second point Va=100 V/270 ohm -> 3.7 mA, 4000 umho corroborates mu=60.)
    #      Single-anchor fit at the 250 V point (KP, KG1 solved to Ia+gm), matching
    #      the 12AY7/6AT6 treatment; MU=60, EX=1.5 fixed.
    at7 = fit_triode("12AT7", mu=60.0, vp=250.0, vg=-2.0, ia=10.0e-3, gm=5500e-6)
    txt = common_header("12AT7 high-mu twin triode (one section)",
                        "Va=250 V, Vg=-2.0 V (200 ohm cathode bias) -> Ia=10 mA, gm=5500 umho, mu=60",
                        ["Second tabulated point Va=100 V/270 ohm -> 3.7 mA, 4000 umho (mu=60).",
                         "Node order: P G K. Basing 9A (reference/tubes/12at7.yaml)."],
                        source="RCA 12AT7 data sheet, March 1, 1954, tabulated characteristics") + "\n" + \
        emit_triode(at7, {"cgk": 2.2, "cgp": 1.5, "cpk": 0.5}, "") + "\n"
    (MODELS_DIR / "12at7.inc").write_text(txt)

    # ---- 6SL7GT: high-mu octal twin triode (mu=70), the octal counterpart of the
    #      12AX7 and the preamp/phase-inverter bottle of the Ampeg circuits. RCA
    #      6SL7-GT data sheet (November 5, 1954) prints ONE characteristics block,
    #      Amplifier Class A1, values for each unit: Va=250 V, Vg=-2 V -> Ia=2.3 mA,
    #      gm=1600 umho, rp=44000 ohm (approx.), mu=70. Tung-Sol (March 1, 1959,
    #      plate #5453) prints the identical row. gm*rp = 70.4 confirms the printed
    #      mu. Single-anchor fit at that point (KP, KG1 solved to Ia+gm), matching
    #      the 12AY7/6AT6/12AT7 treatment; MU=70, EX=1.5 fixed.
    #
    #      KVB stays the project triode default (300 V^2): the measured-KVB rule in
    #      METHODOLOGY.md needs a sheet that tabulates plate current at two plate
    #      voltages at the same grid voltage, and neither publisher does — RCA's
    #      block is a single 250 V column. The sheet's plate-characteristic family
    #      (92CM-6298) is deliberately not fitted to, per the 12AX7 calibration
    #      study's finding on RCA plate graphs.
    sl7 = fit_triode("6SL7GT", mu=70.0, vp=250.0, vg=-2.0, ia=2.3e-3, gm=1600e-6)
    txt = common_header("6SL7GT high-mu twin triode (one section)",
                        "Va=250 V, Vg=-2 V -> Ia=2.3 mA, gm=1600 umho, mu=70",
                        ["Capacitances are RCA's Unit No.1 figures, measured with a",
                         "close-fitting shield (JETEC No.308) tied to the cathode;",
                         "Unit No.2 reads 2.8 / 3.4 / 3.2 pF.",
                         "Known residual: plate resistance reads ~37.7 kohm here against",
                         "the sheet's printed 44 kohm (14% low), so effective mu at the",
                         "anchor is 60.3 rather than 70. This is a limit of the",
                         "single-exponent form, not a defaulted knob: holding Ia and gm",
                         "at the anchor, rp moves only 37.6->37.9 kohm across KVB 1..1000,",
                         "and would need KVB ~25000 V^2 to reach 44 kohm. Same residual",
                         "class the 7591 model documents.",
                         "Node order: P G K. Basing 8BD (reference/tubes/6sl7gt.yaml)."],
                        source="RCA 6SL7-GT data sheet, November 5, 1954, tabulated characteristics") + "\n" + \
        emit_triode(sl7, {"cgk": 3.0, "cgp": 2.8, "cpk": 3.8}, "") + "\n"
    (MODELS_DIR / "6sl7gt.inc").write_text(txt)

    # ---- 6V6GT: Va=250, Vg2=250, Vg1=-12.5 -> Ia=45 mA, Ig2=4.5 mA, gm=4100 umho
    v6 = fit_pentode("6V6GT", mu=9.6, vp=250.0, vg2=250.0, vg1=-12.5,
                     ia=45e-3, ig2=4.5e-3, gm=4100e-6)
    txt = common_header("6V6GT beam power tube",
                        "Va=250 V, Vg2=250 V, Vg1=-12.5 V -> Ia=45 mA, Ig2=4.5 mA, gm=4100 umho",
                        ["mu is grid-No.1-to-grid-No.2 amplification factor (9.6, RC-19).",
                         "Node order: P G2 G1 K"]) + "\n" + \
        emit_pentode(v6, {"cin": 9.0, "cgp": 0.7, "cout": 7.5}) + "\n"
    (MODELS_DIR / "6v6gt.inc").write_text(txt)

    # ---- 5Y3GT: tube drop ~60 V at 125 mA per plate (RC-19)
    perv = fit_rectifier_perveance(v_drop=60.0, i_at_drop=125e-3)
    txt = common_header("5Y3GT full-wave rectifier (ONE plate unit — instantiate twice)",
                        "tube voltage drop ~60 V at Ia=125 mA per plate",
                        ["Child's-law diode: I = PERV * V^1.5; PERV fitted to the drop anchor.",
                         "Node order: A K (anode, cathode/filament)"]) + f"""
.subckt 5Y3GT A K
* fitted: PERV={perv:.6g} EX=1.5
Bd A K I=pow(uramp(V(A,K)),1.5)*{perv:.6g}
Cak A K 4p
.ends 5Y3GT
"""
    (MODELS_DIR / "5y3gt.inc").write_text(txt)

    # ---- 5881 (6L6GC-family beam power): Va=250, Vg2=250, Vg1=-14 ->
    #      Ia=72 mA, Ig2=5 mA, gm=6000 umho, mu(g1-g2)=8
    p5881 = fit_pentode("5881", mu=8.0, vp=250.0, vg2=250.0, vg1=-14.0,
                        ia=72e-3, ig2=5e-3, gm=6000e-6)
    txt = common_header("5881 beam power tube (6L6GC-family anchor data)",
                        "Va=250 V, Vg2=250 V, Vg1=-14 V -> Ia=72 mA, Ig2=5 mA, gm=6000 umho",
                        ["Anchored on RC-19 6L6-GC average characteristics; 5881/6L6WGB",
                         "is treated as 6L6GC-class at these ratings (see METHODOLOGY).",
                         "mu is grid-No.1-to-grid-No.2 amplification factor (8, RC-19).",
                         "Node order: P G2 G1 K"]) + "\n" + \
        emit_pentode(p5881, {"cin": 10.0, "cgp": 0.6, "cout": 12.0}) + "\n"
    (MODELS_DIR / "5881.inc").write_text(txt)

    # ---- 6L6GC (RCA beam power, the blackface Twin's output valve): the RCA
    #      6L6-GC data sheet's Class A1 characteristics, Va=250, Vg2=250,
    #      Vg1=-14 -> Ia=72 mA, Ig2=5 mA, gm=6000 umho. RCA's sheet prints no
    #      amplification factor, so MU is the grid-No.1-to-grid-No.2 factor
    #      RC-19 prints for this tube (8) — METHODOLOGY's first preference, a
    #      published amplification factor, taken from the publisher's own manual.
    #
    #      The anchor row is the same one the 5881 model carries, because the
    #      5881 IS the ruggedized 6L6GC and RCA prints one set of Class A1
    #      characteristics for both; the two fits are therefore numerically
    #      identical by construction, not by copying. They are separate models
    #      because their MAXIMUM RATINGS are not the same tube's — 30 W / 500 V
    #      here against the 5881's 23 W / 400 V — and every rating the load-line
    #      explorer overlays is read from the model's own reference entry. A
    #      6L6GC circuit plotted on 5881 ratings reads as exceeding a plate
    #      voltage it is rated for.
    #      Capacitances are this sheet's own (Cg1-p 0.6, Cg1-k 10, Cp-k 6.5 pF).
    g6l6gc = fit_pentode("6L6GC", mu=8.0, vp=250.0, vg2=250.0, vg1=-14.0,
                         ia=72e-3, ig2=5e-3, gm=6000e-6)
    txt = common_header("6L6GC beam power tube",
                        "Va=250 V, Vg2=250 V, Vg1=-14 V -> Ia=72 mA, Ig2=5 mA, gm=6000 umho",
                        ["mu is the grid-No.1-to-grid-No.2 amplification factor (8) from",
                         "RCA RC-19; the 6L6-GC data sheet prints none (see METHODOLOGY,",
                         "'Where MU comes from'). Same anchor row as models/5881.inc — the",
                         "5881 is the ruggedized 6L6GC and RCA prints one Class A1 set for",
                         "both — so the fits coincide; the ratings attached to each do not.",
                         "Node order: P G2 G1 K"],
                        source=("RCA 6L6-GC data sheet, DATA 1, 8-60, Class A1 "
                                "characteristics; https://frank.pocnet.net/sheets/049/6/6L6GC.pdf")) \
        + "\n" + emit_pentode(g6l6gc, {"cin": 10.0, "cgp": 0.6, "cout": 6.5}) + "\n"
    (MODELS_DIR / "6l6gc.inc").write_text(txt)

    # ---- KT66 (GEC beam power tube, JTM45 output): plate/gm anchor at the
    #      GEC datasheet's gm test point Va=250, Vg2=250, Vg1=-15 -> Ia=85 mA,
    #      gm=7 mA/V (datasheet pp.1 & 3). mu(g1-g2)=9.5 from the triode-
    #      connection gm.ra (7.3 mA/V x 1.3 kOhm). The datasheet tabulates no
    #      screen current at the gm point, so KG2 is anchored on the datasheet's
    #      Class AB1 push-pull tetrode quiescent point: Vg2=300, Vg1=-27 ->
    #      Ig2=2.5 mA (p.2). Source URL in the header below.
    kt66 = fit_pentode("KT66", mu=9.5, vp=250.0, vg2=250.0, vg1=-15.0,
                       ia=85e-3, ig2=2.5e-3, gm=7000e-6,
                       vg2_s=300.0, vg1_s=-27.0)
    kt66_src = ("GEC / M-O Valve Co. KT66 data sheet, Issue 4, April 1963; "
                "https://frank.pocnet.net/sheets/084/k/KT66_GEC.pdf")
    txt = common_header("KT66 beam power tetrode",
                        "Va=250 V, Vg2=250 V, Vg1=-15 V -> Ia=85 mA, gm=7000 umho (gm test point)",
                        ["mu is grid-No.1-to-grid-No.2 amplification factor (9.5), taken from",
                         "the triode-connection gm.ra (7.3 mA/V x 1.3 kOhm) on the same sheet.",
                         "KG2 anchored on the Class AB1 push-pull tetrode quiescent point",
                         "Vg2=300 V, Vg1=-27 V -> Ig2=2.5 mA (no Ig2 tabulated at the gm point).",
                         "Capacitances from the sheet: Cg1(in)=14.5 pF, Ca-g1=1.1 pF, Ca(out)=10 pF.",
                         "Node order: P G2 G1 K"],
                        source=kt66_src) + "\n" + \
        emit_pentode(kt66, {"cin": 14.5, "cgp": 1.1, "cout": 10.0}) + "\n"
    (MODELS_DIR / "kt66.inc").write_text(txt)

    # ---- EL34 (Mullard/Philips A.F. output pentode, Marshall 1987 output): the
    #      datasheet's Class-A quick-reference point tabulates Ia, Ig2 AND gm at the
    #      SAME operating point (Va=250, Vg2=250, Vg1=-13.5 -> Ia=100 mA, Ig2=14.9 mA,
    #      gm=12.5 mA/V), so KG2 anchors at the plate/gm point directly (no separate
    #      screen point needed, unlike the KT66). mu(g1-g2)=11 is the tabulated
    #      amplification factor. Source URL in the header below.
    el34 = fit_pentode("EL34", mu=11.0, vp=250.0, vg2=250.0, vg1=-13.5,
                       ia=100e-3, ig2=14.9e-3, gm=12500e-6)
    el34_src = ("Mullard/Philips EL34 data sheet, January 1969; "
                "https://frank.pocnet.net/sheets/010/e/EL34.pdf")
    txt = common_header("EL34 A.F. output pentode",
                        "Va=250 V, Vg2=250 V, Vg1=-13.5 V -> Ia=100 mA, Ig2=14.9 mA, gm=12500 umho",
                        ["mu is grid-No.1-to-grid-No.2 amplification factor (11), the",
                         "tabulated amplification factor on the same Class-A data row.",
                         "Ig2 is tabulated at the plate/gm point, so KG2 anchors there.",
                         "Capacitances from the sheet: Cg1(in)=15.2 pF, Ca-g1=1.1 pF, Ca(out)=8.4 pF.",
                         "True pentode (suppressor g3 to pin 1, tied to cathode in use).",
                         "Node order: P G2 G1 K"],
                        source=el34_src) + "\n" + \
        emit_pentode(el34, {"cin": 15.2, "cgp": 1.1, "cout": 8.4}) + "\n"
    (MODELS_DIR / "el34.inc").write_text(txt)

    # ---- EL84 (Philips/Mullard A.F. output pentode, Vox AC15 output): the
    #      sheet's Class-A operating-characteristics block tabulates Ia, Ig2 AND S
    #      at the SAME point (Va=250, Vg2=250, Vg1=-7.3, Rk=135 -> Ia=48 mA,
    #      Ig2=5.5 mA, S=11.3 mA/V), so KG2 anchors at the plate/gm point directly
    #      (as on the EL34, unlike the KT66). mu(g1-g2)=19 is the tabulated
    #      amplification factor on the same row. Source URL in the header below.
    el84 = fit_pentode("EL84", mu=19.0, vp=250.0, vg2=250.0, vg1=-7.3,
                       ia=48e-3, ig2=5.5e-3, gm=11300e-6)
    el84_src = ("Philips/Mullard EL84 data sheet, January 1969 (A.F. Output Pentode); "
                "https://frank.pocnet.net/sheets/010/e/EL84.pdf")
    txt = common_header("EL84 A.F. output pentode",
                        "Va=250 V, Vg2=250 V, Vg1=-7.3 V -> Ia=48 mA, Ig2=5.5 mA, gm=11300 umho",
                        ["mu is grid-No.1-to-grid-No.2 amplification factor (19), the",
                         "tabulated amplification factor on the same Class-A data row.",
                         "Ig2 is tabulated at the plate/gm point, so KG2 anchors there.",
                         "Capacitances from the sheet: Cg1(a)=10.8 pF, Ca-g1=max 0.5 pF,",
                         "Ca(g1)=6.5 pF. Noval base; g3 is joined to the cathode inside",
                         "the envelope (pin 3), so there is no separate suppressor node.",
                         "Node order: P G2 G1 K"],
                        source=el84_src) + "\n" + \
        emit_pentode(el84, {"cin": 10.8, "cgp": 0.5, "cout": 6.5}) + "\n"
    (MODELS_DIR / "el84.inc").write_text(txt)

    # ---- 6973 (RCA beam power tube, the Supro/Valco 9-pin output valve): the
    #      sheet's Class-A1 characteristics block tabulates Ia, Ig2 AND gm at one
    #      point (Va=250, Vg2=250, Vg1=-15 -> Ia=46 mA, Ig2=3.5 mA, gm=4800 umho),
    #      so KP/KG1/KG2 all anchor there. RCA prints NO amplification factor for
    #      this tube — not on the data sheet and not in RC-30 — so MU is solved from
    #      the sheet's own further tabulated push-pull fixed-bias rows, which run the
    #      screen at 250/280/290 V and therefore measure it (see solve_pentode_mu).
    p6973_anchor = dict(vp=250.0, vg2=250.0, vg1=-15.0,
                        ia=46e-3, ig2=3.5e-3, gm=4800e-6)
    # (Va, Vg2, Vg1, Ia) and (Vg2, Vg1, Ig2) — the fixed-bias table's three columns,
    # halved from its "values are for 2 tubes" convention.
    p6973_ia_rows = [(250.0, 250.0, -15.0, 46e-3),
                     (350.0, 280.0, -22.0, 29e-3),
                     (400.0, 290.0, -25.0, 25e-3)]
    p6973_ig2_rows = [(250.0, -15.0, 3.5e-3),
                      (280.0, -22.0, 1.75e-3),
                      (290.0, -25.0, 1.25e-3)]
    mu6973 = solve_pentode_mu(**p6973_anchor,
                              ia_rows=p6973_ia_rows, ig2_rows=p6973_ig2_rows)
    p6973 = fit_pentode("6973", mu=mu6973, **p6973_anchor)
    src_6973 = ("RCA 6973 data sheet, 10-60 (Beam Power Tube, 9-pin miniature); "
                "https://frank.pocnet.net/sheets/049/6/6973.pdf")
    txt = common_header("6973 beam power tube",
                        "Va=250 V, Vg2=250 V, Vg1=-15 V -> Ia=46 mA, Ig2=3.5 mA, gm=4800 umho",
                        [f"mu={mu6973:.4g} is SOLVED, not read: neither the data sheet nor the",
                         "RCA Receiving Tube Manual RC-30 entry prints an amplification factor",
                         "for this tube. It is fitted to the sheet's own push-pull fixed-bias",
                         "rows (250/250/-15, 350/280/-22, 400/290/-25 V -> 46/29/25 mA per tube",
                         "and 3.5/1.75/1.25 mA screen), which vary the screen voltage and so",
                         "measure it; the anchor above is still reproduced exactly. Residuals on",
                         "those rows: plate +12.0%/+6.4%, screen +7.9%/-3.4%.",
                         "Independent check: the anchor's own gm/Ia ratio requires mu > 8.51 in",
                         "this model form, and the solved value sits above that floor.",
                         "Capacitances from the sheet: Cg1-p=0.4 pF max, Cin=9 pF, Cout=6 pF.",
                         "Node order: P G2 G1 K"],
                        source=src_6973) + "\n" + \
        emit_pentode(p6973, {"cin": 9.0, "cgp": 0.4, "cout": 6.0}) + "\n"
    (MODELS_DIR / "6973.inc").write_text(txt)

    # ---- 7591 (beam power tube, the Ampeg output valve): the Tung-Sol sheet's
    #      Class-A1 typical-operation block tabulates Ia, Ig2 AND gm at one point
    #      (Va=300, Vg2=300, Vg1=-10 -> Ia=60 mA, Ig2=8 mA, gm=10200 umho), so
    #      KP/KG1/KG2 all anchor there; Sylvania's sheet prints the identical block.
    #      MU=16.8 is the amplification factor printed on the Tung-Sol sheet.
    p7591 = fit_pentode("7591", mu=16.8, vp=300.0, vg2=300.0, vg1=-10.0,
                        ia=60e-3, ig2=8e-3, gm=10200e-6)
    src_7591 = ("Tung-Sol 7591 data sheet, March 1, 1961 (plate #6125); "
                "https://frank.pocnet.net/sheets/127/7/7591.pdf")
    txt = common_header("7591 beam power tube",
                        "Va=300 V, Vg2=300 V, Vg1=-10 V -> Ia=60 mA, Ig2=8 mA, gm=10200 umho",
                        ["mu=16.8 is the amplification factor printed beside this operating",
                         "point (measured in triode connection, as on the KT66). Three sheets",
                         "agree on the whole block — Tung-Sol 3-1961, Sylvania 10-1961 and",
                         "Westinghouse 7591A 4-1963 all print 10200 umho, 29000 Ohm, mu 16.8.",
                         "It is also the only published figure the anchor admits: the tabulated",
                         "gm/Ia ratio cannot be reached in this model form below mu=15.94, and",
                         "it agrees with the sheets' average plate characteristics",
                         "(Vg2=350, Vg1=0 -> ~260 mA; model 259 mA).",
                         "Known limitation: the sheets' push-pull Class-AB1 DESIGN tables sit",
                         "well off this fit — plate -13% to -21%, screen -29% to -64% — because",
                         "the published screen current falls far more slowly with bias than a",
                         "3/2-power law allows. Those rows are recorded in",
                         "reference/tubes/7591.yaml, not fitted to. Published plate resistance",
                         "29 kOhm at the anchor; this model, on the project default KVB, reads",
                         "about 74 kOhm.",
                         "Capacitances from the sheet: Cg1-p=0.25 pF, Cin=10 pF, Cout=5 pF.",
                         "Node order: P G2 G1 K"],
                        source=src_7591) + "\n" + \
        emit_pentode(p7591, {"cin": 10.0, "cgp": 0.25, "cout": 5.0}) + "\n"
    (MODELS_DIR / "7591.inc").write_text(txt)

    # ---- EF86 (Philips/Mullard A.F. pentode, Vox AC15 Normal-channel preamp):
    #      the sheet's "typical characteristics" block tabulates Ia, Ig2 and S at
    #      one point (Va=250, Vg2=140, Vg3=0, Vg1=-2.2 -> Ia=3.0 mA, Ig2=0.6 mA,
    #      S=2.2 mA/V), so KG1 and KG2 both anchor there. mu(g1-g2)=38 is the
    #      tabulated amplification factor. Source URL in the header below.
    ef86 = fit_pentode("EF86", mu=38.0, vp=250.0, vg2=140.0, vg1=-2.2,
                       ia=3.0e-3, ig2=0.6e-3, gm=2200e-6)
    ef86_src = ("Philips/Mullard EF86 data sheet, January 1970 (A.F. Pentode); "
                "https://frank.pocnet.net/sheets/010/e/EF86.pdf")
    txt = common_header("EF86 A.F. small-signal pentode",
                        "Va=250 V, Vg2=140 V, Vg1=-2.2 V -> Ia=3.0 mA, Ig2=0.6 mA, gm=2200 umho",
                        ["mu is grid-No.1-to-grid-No.2 amplification factor (38), the",
                         "tabulated amplification factor on the same typical-characteristics",
                         "row; the sheet also prints Ri=2.5 MOhm there.",
                         "Capacitances from the sheet: Cg1(a)=3.8 pF, Ca-g1=max 0.05 pF,",
                         "Ca(g1)=5.1 pF. The suppressor g3 has its own pin (8) and is",
                         "strapped to the cathode in every corpus circuit, so it is not a",
                         "separate model node (Vg3=0 at the anchor, as tabulated).",
                         "Node order: P G2 G1 K"],
                        source=ef86_src) + "\n" + \
        emit_pentode(ef86, {"cin": 3.8, "cgp": 0.05, "cout": 5.1}) + "\n"
    (MODELS_DIR / "ef86.inc").write_text(txt)

    # ---- 6SJ7 (metal sharp-cutoff pentode, the wide-panel tweed input valve):
    #      RCA (6-15-1948) and GE (ET-T1400, 11-56) print an identical Class-A1
    #      block, and it tabulates plate current at TWO plate voltages at the same
    #      screen and grid (Vg2=100, Vg1=-3: Va=250 -> 3.0 mA, Va=100 -> 2.9 mA).
    #      That pair measures the plate-voltage dependence directly, so KVB is
    #      fitted to it instead of taking the project default — which would put the
    #      100 V point 8.8% low. KP/KG1/KG2 then anchor at the 250 V column as usual.
    sj7_kvb = fit_pentode_kvb_from_plate_pair(vp_a=250.0, ia_a=3.0e-3,
                                              vp_b=100.0, ia_b=2.9e-3)
    sj7 = fit_pentode("6SJ7", mu=19.0, vp=250.0, vg2=100.0, vg1=-3.0,
                      ia=3.0e-3, ig2=0.8e-3, gm=1650e-6, kvb=sj7_kvb)
    sj7_src = ("RCA 6SJ7 / 6SJ7-GT data sheet, June 15, 1948; "
               "https://frank.pocnet.net/sheets/049/6/6SJ7.pdf")
    txt = common_header("6SJ7 sharp-cutoff pentode",
                        "Va=250 V, Vg2=100 V, Vg3=0 V, Vg1=-3 V -> Ia=3.0 mA, Ig2=0.8 mA, "
                        "gm=1650 umho; second tabulated plate voltage Va=100 V -> Ia=2.9 mA, "
                        "gm=1575 umho",
                        ["mu=19 is the tabulated TRIODE-connection amplification factor (grids",
                         "No.2 and No.3 tied to the plate), used in place of the grid-No.1-to-",
                         "grid-No.2 factor, which neither publisher prints — the same substitution",
                         "the KT66 model makes. RCA's gm.rp at that point (2500 umho x 7600 Ohm)",
                         "confirms the 19. Known risk: on the 7591, where both figures can be",
                         "obtained, the triode figure runs above the value the operating rows imply.",
                         f"KVB={sj7_kvb:.4g} is fitted, not defaulted: the sheet's two tabulated",
                         "plate voltages measure it (see fit_pentode_kvb_from_plate_pair). It is",
                         "corroborated independently — the model then reads 0.60 MOhm of plate",
                         "resistance at Va=100 V against the sheet's printed 0.7 MOhm, and 3.7",
                         "MOhm at Va=250 V against its 'greater than 1 megohm'.",
                         "The sheet's screen current differs between the two plate voltages",
                         "(0.8 mA at 250 V, 0.9 mA at 100 V); this model form has no plate-voltage",
                         "dependence in Ig2, so KG2 anchors on the 250 V column.",
                         "Capacitances are the metal 6SJ7's, shell tied to cathode: Cg1-p=0.005 pF",
                         "max, Cin=6 pF, Cout=7 pF. The glass 6SJ7-GT differs (0.005/7/7 pF with an",
                         "external shield) and shares the electrical data.",
                         "Suppressor g3 has its own pin (3) and is strapped to the cathode in this",
                         "corpus's circuits, as at the tabulated point (Vg3=0), so it is not a",
                         "separate model node.",
                         "Node order: P G2 G1 K"],
                        source=sj7_src) + "\n" + \
        emit_pentode(sj7, {"cin": 6.0, "cgp": 0.005, "cout": 7.0}) + "\n"
    (MODELS_DIR / "6sj7.inc").write_text(txt)

    # ---- EZ81: the Philips sheet tabulates NO per-anode tube drop — only whole-
    #      rectifier system rows (transformer volts in, DC volts out). The only
    #      per-anode datum published is the Ia-Va anode characteristic, fig.
    #      7Z00030-5.26.ha; the anchor below is READ from the measured (solid)
    #      portion of that curve, not from a table, and is recorded as such in
    #      reference/tubes/ez81.yaml. Residual: a single 3/2-power law fitted here
    #      runs ~13% high against the same curve's extrapolated (dashed) 30 V end.
    perv_ez = fit_rectifier_perveance(v_drop=10.0, i_at_drop=60e-3)
    ez81_src = ("Philips EZ81 data sheet, January 1970 (Double Anode Rectifying Tube), "
                "anode characteristic fig. 7Z00030-5.26.ha; "
                "https://frank.pocnet.net/sheets/010/e/EZ81.pdf")
    txt = common_header("EZ81 full-wave rectifier (ONE anode unit — instantiate twice)",
                        "Va=10 V -> Ia=60 mA per anode (read from the Ia-Va anode characteristic)",
                        ["Child's-law diode: I = PERV * V^1.5; PERV fitted to the curve anchor.",
                         "GRAPH-READ anchor, not a tabulated point: the sheet publishes no",
                         "per-anode drop figure, only whole-rectifier system rows. Read from",
                         "the solid (measured) part of the curve, below the dashed extension.",
                         "Indirectly heated noval double diode; both anodes share one cathode.",
                         "Node order: A K (anode, cathode)"],
                        source=ez81_src) + f"""
.subckt EZ81 A K
* fitted: PERV={perv_ez:.6g} EX=1.5
Bd A K I=pow(uramp(V(A,K)),1.5)*{perv_ez:.6g}
Cak A K 4p
.ends EZ81
"""
    (MODELS_DIR / "ez81.inc").write_text(txt)

    # ---- GZ34: tube drop ~17 V at 250 mA per plate (Mullard datasheet average)
    perv_gz = fit_rectifier_perveance(v_drop=17.0, i_at_drop=250e-3)
    txt = common_header("GZ34 full-wave rectifier (ONE plate unit — instantiate twice)",
                        "tube voltage drop ~17 V at Ia=250 mA per plate (Mullard average)",
                        ["Child's-law diode: I = PERV * V^1.5; PERV fitted to the drop anchor.",
                         "Node order: A K (anode, cathode)"]) + f"""
.subckt GZ34 A K
* fitted: PERV={perv_gz:.6g} EX=1.5
Bd A K I=pow(uramp(V(A,K)),1.5)*{perv_gz:.6g}
Cak A K 4p
.ends GZ34
"""
    (MODELS_DIR / "gz34.inc").write_text(txt)

    # ---- 5U4G: tube drop ~50 V at 200 mA per plate (RC-19 average characteristic)
    perv_5u4 = fit_rectifier_perveance(v_drop=50.0, i_at_drop=200e-3)
    txt = common_header("5U4G full-wave rectifier (ONE plate unit — instantiate twice)",
                        "tube voltage drop ~50 V at Ia=200 mA per plate",
                        ["Child's-law diode: I = PERV * V^1.5; PERV fitted to the drop anchor.",
                         "Directly-heated high-current twin-plate rectifier (5U4G/5U4GB class).",
                         "Node order: A K (anode, cathode/filament)"]) + f"""
.subckt 5U4G A K
* fitted: PERV={perv_5u4:.6g} EX=1.5
Bd A K I=pow(uramp(V(A,K)),1.5)*{perv_5u4:.6g}
Cak A K 4p
.ends 5U4G
"""
    (MODELS_DIR / "5u4g.inc").write_text(txt)

    # ---- 83: full-wave MERCURY-VAPOUR rectifier (tweed 5F6 Bassman). A gas
    #      discharge rather than a vacuum diode: the datasheets give no V/I pair to
    #      fit a perveance to, only the single characteristic "Tube Voltage Drop
    #      (Approx.) 15 volts" plus the explicit statement that the tube "is
    #      designed to supply d-c current at essentially constant voltage in spite
    #      of rather wide variations in output current" (GE). So it is modelled as
    #      an exponential arc pinned to 15 V at the rated 225 mA d-c output, with a
    #      0.35 V softness chosen (not fitted) to hold the drop inside +/-1 V of the
    #      datasheet figure from a tenth of rated current up to the 1 A per-plate
    #      peak rating. Source URLs in the header below.
    v_arc, i_arc, v_soft = arc_rectifier(v_arc=15.0, i_ref=225e-3, v_soft=0.35)
    src_83 = ("RCA type 83 data sheet, 7-63 (https://frank.pocnet.net/sheets/049/8/83.pdf), "
              "corroborated by General Electric ET-T464, 2-47 "
              "(https://frank.pocnet.net/sheets/093/8/83.pdf)")
    arc_eq = [
        "Equations: mercury-vapour arc, NOT the Koren/Child-Langmuir form used by",
        "  this project's vacuum tubes — a struck arc is not space-charge limited.",
        "  I = IREF * exp((Vak - VARC)/VSOFT); every number below is read from the",
        "  datasheets or chosen here, none copied from any model collection.",
    ]
    txt = common_header("83 full-wave mercury-vapour rectifier (ONE plate unit — instantiate twice)",
                        "Tube Voltage Drop (Approx.) = 15 V, tabulated as a single characteristic "
                        "because the arc drop hardly moves with current; rated d-c output 225 mA, "
                        "peak plate current 1 A per plate, filament 5.0 V / 3.0 A",
                        ["VARC=15 V is the datasheet drop and IREF=225 mA the rated d-c output, so",
                         "the model sits exactly on the datasheet drop at rated current. VSOFT is a",
                         "project shaping choice, not a fit — 0.35 V holds the drop within +/-1 V of",
                         "15 V over the entire rated range (22.5 mA -> 15.5 V at the 1 A peak),",
                         "which is the whole of the datasheet's claim. A Child's-law fit would",
                         "instead swing the drop more than tenfold across that range.",
                         "Mercury-temperature dependence (20-60 C condensed), ionisation and",
                         "deionisation time and switching transients are not modelled; this is a",
                         "d-c operating-point model. Peak inverse rating 1550 V.",
                         "Node order: A K (anode, cathode/filament)"],
                        source=src_83, equations=arc_eq) + f"""
.subckt 83 A K
* fitted: VARC={v_arc:g} IREF={i_arc:g} VSOFT={v_soft:g}
Bd A K I={i_arc:g}*exp((min(V(A,K),{v_arc + 5:g})-{v_arc:g})/{v_soft:g})
Cak A K 4p
.ends 83
"""
    (MODELS_DIR / "83.inc").write_text(txt)

    print("fitted parameters:")
    print(f"  12AX7: MU={ax7.mu:g} KP={ax7.kp:.6g} KG1={ax7.kg1:.6g} EX={ax7.ex:g} KVB={ax7.kvb:.6g} (v1 multi-point)")
    print(f"  12AY7: MU={ay7.mu:g} KP={ay7.kp:.6g} KG1={ay7.kg1:.6g} EX={ay7.ex:g} KVB={ay7.kvb:g}")
    print(f"  12AU7: MU={au7.mu:g} KP={au7.kp:.6g} KG1={au7.kg1:.6g} EX={au7.ex:g} KVB={au7.kvb:g}")
    print(f"  12AT7: MU={at7.mu:g} KP={at7.kp:.6g} KG1={at7.kg1:.6g} EX={at7.ex:g} KVB={at7.kvb:g}")
    print(f"  6AT6:  MU={at6.mu:g} KP={at6.kp:.6g} KG1={at6.kg1:.6g} EX={at6.ex:g} KVB={at6.kvb:g}")
    print(f"  6SL7GT: MU={sl7.mu:g} KP={sl7.kp:.6g} KG1={sl7.kg1:.6g} EX={sl7.ex:g} KVB={sl7.kvb:g}")
    print(f"  6V6GT: MU={v6.mu:g} KP={v6.kp:.6g} KG1={v6.kg1:.6g} KG2={v6.kg2:.6g} KVB={v6.kvb:g}")
    print(f"  5Y3GT: PERV={perv:.6g}")
    print(f"  5881:  MU={p5881.mu:g} KP={p5881.kp:.6g} KG1={p5881.kg1:.6g} KG2={p5881.kg2:.6g}")
    print(f"  6L6GC: MU={g6l6gc.mu:g} KP={g6l6gc.kp:.6g} KG1={g6l6gc.kg1:.6g} KG2={g6l6gc.kg2:.6g}")
    print(f"  KT66:  MU={kt66.mu:g} KP={kt66.kp:.6g} KG1={kt66.kg1:.6g} KG2={kt66.kg2:.6g}")
    print(f"  EL34:  MU={el34.mu:g} KP={el34.kp:.6g} KG1={el34.kg1:.6g} KG2={el34.kg2:.6g}")
    print(f"  EL84:  MU={el84.mu:g} KP={el84.kp:.6g} KG1={el84.kg1:.6g} KG2={el84.kg2:.6g}")
    print(f"  EF86:  MU={ef86.mu:g} KP={ef86.kp:.6g} KG1={ef86.kg1:.6g} KG2={ef86.kg2:.6g}")
    print(f"  6973:  MU={p6973.mu:.6g} KP={p6973.kp:.6g} KG1={p6973.kg1:.6g} KG2={p6973.kg2:.6g} (MU solved from the sheet's rows)")
    print(f"  7591:  MU={p7591.mu:g} KP={p7591.kp:.6g} KG1={p7591.kg1:.6g} KG2={p7591.kg2:.6g}")
    print(f"  6SJ7:  MU={sj7.mu:g} KP={sj7.kp:.6g} KG1={sj7.kg1:.6g} KG2={sj7.kg2:.6g} KVB={sj7.kvb:.6g} (KVB fitted)")
    print(f"  EZ81:  PERV={perv_ez:.6g}")
    print(f"  GZ34:  PERV={perv_gz:.6g}")
    print(f"  5U4G:  PERV={perv_5u4:.6g}")
    print(f"  83:    VARC={v_arc:g} IREF={i_arc:g} VSOFT={v_soft:g} (mercury-vapour arc)")
    # Counted, not hard-coded: the literal here read "19" while the directory held
    # 20 .inc files, so it rotted silently every time a tube was added.
    print(f"wrote {len(list(MODELS_DIR.glob('*.inc')))} models to {MODELS_DIR}")


if __name__ == "__main__":
    main()
