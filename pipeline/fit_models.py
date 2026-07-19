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
                vg2_s: float | None = None, vg1_s: float | None = None) -> PentodeFit:
    """Solve KP, KG1 so the model reproduces (ia, gm) at the plate anchor
    (vp, vg2, vg1). KG2 is fit to Ig2 at a screen anchor which may differ from
    the plate anchor: pass vg2_s/vg1_s when the datasheet tabulates screen
    current at a different operating point than gm/Ia (both default to the
    plate anchor's vg2/vg1, preserving the single-point behaviour)."""
    a = 1.0 / mu + vg1 / vg2
    r_target = gm / ia

    def ratio_err(kp: float) -> float:
        z = kp * a
        e1 = (vg2 / kp) * _softplus(z)
        return EX * _sig(z) / e1 - r_target

    kp = _bisect(ratio_err, 1e-3, 5000.0)
    e1 = (vg2 / kp) * _softplus(kp * a)
    kg1 = (e1 ** EX) * math.atan(vp / KVB_PENTODE) / ia
    vg2s = vg2 if vg2_s is None else vg2_s
    vg1s = vg1 if vg1_s is None else vg1_s
    e2 = vg2s / mu + vg1s
    kg2 = (e2 ** EX) / ig2
    return PentodeFit(name=name, mu=mu, kp=kp, kg1=kg1, kg2=kg2)


def fit_rectifier_perveance(v_drop: float, i_at_drop: float) -> float:
    """Child's-law diode: I = P * V^1.5, P from the published drop anchor."""
    return i_at_drop / (v_drop ** 1.5)


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


def common_header(tube: str, anchor: str, extra: list[str] | None = None,
                  source: str = "RCA Receiving Tube Manual RC-19, 1959, average characteristics") -> str:
    lines = [
        f"{tube} — Circuit Codex tube model",
        "License: CC0 1.0 Universal (public domain dedication)",
        "  https://creativecommons.org/publicdomain/zero/1.0/",
        "Equations: Koren model form — N. Koren, 'Improved vacuum-tube models for",
        "  SPICE simulations', Glass Audio 8(5), 1996 (published methodology; all",
        "  parameters fitted by Circuit Codex, none copied from other collections).",
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

    print("fitted parameters:")
    print(f"  12AX7: MU={ax7.mu:g} KP={ax7.kp:.6g} KG1={ax7.kg1:.6g} EX={ax7.ex:g} KVB={ax7.kvb:.6g} (v1 multi-point)")
    print(f"  12AY7: MU={ay7.mu:g} KP={ay7.kp:.6g} KG1={ay7.kg1:.6g} EX={ay7.ex:g} KVB={ay7.kvb:g}")
    print(f"  12AT7: MU={at7.mu:g} KP={at7.kp:.6g} KG1={at7.kg1:.6g} EX={at7.ex:g} KVB={at7.kvb:g}")
    print(f"  6AT6:  MU={at6.mu:g} KP={at6.kp:.6g} KG1={at6.kg1:.6g} EX={at6.ex:g} KVB={at6.kvb:g}")
    print(f"  6V6GT: MU={v6.mu:g} KP={v6.kp:.6g} KG1={v6.kg1:.6g} KG2={v6.kg2:.6g} KVB={v6.kvb:g}")
    print(f"  5Y3GT: PERV={perv:.6g}")
    print(f"  5881:  MU={p5881.mu:g} KP={p5881.kp:.6g} KG1={p5881.kg1:.6g} KG2={p5881.kg2:.6g}")
    print(f"  KT66:  MU={kt66.mu:g} KP={kt66.kp:.6g} KG1={kt66.kg1:.6g} KG2={kt66.kg2:.6g}")
    print(f"  EL34:  MU={el34.mu:g} KP={el34.kp:.6g} KG1={el34.kg1:.6g} KG2={el34.kg2:.6g}")
    print(f"  GZ34:  PERV={perv_gz:.6g}")
    print(f"  5U4G:  PERV={perv_5u4:.6g}")
    print(f"wrote 11 models to {MODELS_DIR}")


if __name__ == "__main__":
    main()
