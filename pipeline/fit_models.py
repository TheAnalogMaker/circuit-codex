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
                ia: float, ig2: float, gm: float) -> PentodeFit:
    a = 1.0 / mu + vg1 / vg2
    r_target = gm / ia

    def ratio_err(kp: float) -> float:
        z = kp * a
        e1 = (vg2 / kp) * _softplus(z)
        return EX * _sig(z) / e1 - r_target

    kp = _bisect(ratio_err, 1e-3, 5000.0)
    e1 = (vg2 / kp) * _softplus(kp * a)
    kg1 = (e1 ** EX) * math.atan(vp / KVB_PENTODE) / ia
    e2 = vg2 / mu + vg1
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


def common_header(tube: str, anchor: str, extra: list[str] | None = None) -> str:
    lines = [
        f"{tube} — Circuit Codex tube model",
        "License: CC0 1.0 Universal (public domain dedication)",
        "  https://creativecommons.org/publicdomain/zero/1.0/",
        "Equations: Koren model form — N. Koren, 'Improved vacuum-tube models for",
        "  SPICE simulations', Glass Audio 8(5), 1996 (published methodology; all",
        "  parameters fitted by Circuit Codex, none copied from other collections).",
        f"Anchor (RCA Receiving Tube Manual RC-19, 1959, average characteristics): {anchor}",
        "Method + limitations: models/METHODOLOGY.md",
        "Generated by pipeline/fit_models.py — edit anchors there, not here.",
        "Heater not modeled (rated heater assumed). No grid-current model (v0).",
    ]
    if extra:
        lines += extra
    return _header(lines)


def main() -> None:
    MODELS_DIR.mkdir(exist_ok=True)

    # ---- 12AX7: Va=250 V, Vg=-2 V -> Ia=1.2 mA, gm=1600 umho, mu=100
    ax7 = fit_triode("12AX7", mu=100.0, vp=250.0, vg=-2.0, ia=1.2e-3, gm=1600e-6)
    txt = common_header("12AX7 dual triode (one section)",
                        "Va=250 V, Vg=-2 V -> Ia=1.2 mA, gm=1600 umho, mu=100") + "\n" + \
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
    print(f"  12AX7: MU={ax7.mu:g} KP={ax7.kp:.6g} KG1={ax7.kg1:.6g} EX={ax7.ex:g} KVB={ax7.kvb:g}")
    print(f"  12AY7: MU={ay7.mu:g} KP={ay7.kp:.6g} KG1={ay7.kg1:.6g} EX={ay7.ex:g} KVB={ay7.kvb:g}")
    print(f"  6AT6:  MU={at6.mu:g} KP={at6.kp:.6g} KG1={at6.kg1:.6g} EX={at6.ex:g} KVB={at6.kvb:g}")
    print(f"  6V6GT: MU={v6.mu:g} KP={v6.kp:.6g} KG1={v6.kg1:.6g} KG2={v6.kg2:.6g} KVB={v6.kvb:g}")
    print(f"  5Y3GT: PERV={perv:.6g}")
    print(f"  5881:  MU={p5881.mu:g} KP={p5881.kp:.6g} KG1={p5881.kg1:.6g} KG2={p5881.kg2:.6g}")
    print(f"  GZ34:  PERV={perv_gz:.6g}")
    print(f"  5U4G:  PERV={perv_5u4:.6g}")
    print(f"wrote 8 models to {MODELS_DIR}")


if __name__ == "__main__":
    main()
