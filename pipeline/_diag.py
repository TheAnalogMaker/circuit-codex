#!/usr/bin/env python3
"""Scratch diagnostic: map collision-lint findings back to layout.yaml runs.

Not part of the gate set — a working aid for routing a layout to zero findings.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import yaml

from render_layouts import (LINT_ANGLE, LINT_OVERLAP, LINT_SEP, LINT_TERM,
                            LINT_VERTEX_CLEAR, Renderer, SheetRenderer,
                            _parallel_overlap, _point_seg_dist, _seg_angle_deg,
                            lint_layout, load_bom)

ROOT = Path(__file__).resolve().parent.parent


def geo(amp: str):
    d = ROOT / "amps" / amp
    layout = yaml.safe_load((d / "layout.yaml").read_text())
    bom = load_bom(d)
    rend = Renderer(layout, bom, amp)
    runs, bus = rend.build_geometry()
    return layout, rend, runs, bus


def spec_str(spec) -> str:
    bits = [f"from={spec.get('from')}", f"to={spec.get('to')}"]
    if spec.get("color"):
        bits.append(f"color={spec['color']}")
    if spec.get("style"):
        bits.append(f"style={spec['style']}")
    if spec.get("via"):
        bits.append(f"via={spec['via']}")
    return "  ".join(bits)


def cmd_wiring(amp: str):
    """Print every wiring finding with both runs' specs and polylines."""
    layout, rend, runs, bus = geo(amp)
    plain = [r for r in runs if r["pts"] and not r["twisted"]]
    byi = {r["i"]: r for r in runs}
    out = []
    for ai in range(len(plain)):
        for bi in range(ai + 1, len(plain)):
            A, B = plain[ai], plain[bi]
            for sa in range(len(A["pts"]) - 1):
                for sb in range(len(B["pts"]) - 1):
                    a1, a2 = A["pts"][sa], A["pts"][sa + 1]
                    b1, b2 = B["pts"][sb], B["pts"][sb + 1]
                    if _seg_angle_deg(a1, a2, b1, b2) >= LINT_ANGLE:
                        continue
                    ov = _parallel_overlap(a1, a2, b1, b2, LINT_SEP)
                    if ov and ov[0] > LINT_OVERLAP:
                        out.append(("PARA", A["i"], B["i"], ov[1], ov[0],
                                    (a1, a2), (b1, b2)))
    for A in plain:
        for E in (A["pts"][0], A["pts"][-1]):
            for B in plain:
                if B["i"] == A["i"]:
                    continue
                pb = B["pts"]
                if any(math.hypot(E[0] - v[0], E[1] - v[1]) < LINT_VERTEX_CLEAR for v in pb):
                    continue
                for sb in range(len(pb) - 1):
                    if _point_seg_dist(E, pb[sb], pb[sb + 1]) < LINT_TERM:
                        out.append(("TERM", A["i"], B["i"], E, sb,
                                    (pb[sb], pb[sb + 1]), None))
                        break
    for row in out:
        kind, ai, bi, at, extra, sega, segb = row
        print(f"--- {kind} run[{ai}] vs run[{bi}] at ({at[0]:.0f},{at[1]:.0f})")
        print(f"    A run[{ai}]: {spec_str(byi[ai]['spec'])}")
        print(f"      pts {[ (round(p[0]),round(p[1])) for p in byi[ai]['pts'] ]}")
        print(f"    B run[{bi}]: {spec_str(byi[bi]['spec'])}")
        print(f"      pts {[ (round(p[0]),round(p[1])) for p in byi[bi]['pts'] ]}")
    print(f"\n{len(out)} wiring finding(s)")


def cmd_runs(amp: str, *idx: str):
    layout, rend, runs, bus = geo(amp)
    want = {int(i) for i in idx} if idx else None
    for r in runs:
        if want is not None and r["i"] not in want:
            continue
        print(f"run[{r['i']}] {spec_str(r['spec'])}")
        if r["pts"]:
            print(f"    pts {[ (round(p[0],1),round(p[1],1)) for p in r['pts'] ]}")


def cmd_at(amp: str, x: str, y: str, rad: str = "40"):
    """Every run whose polyline comes within <rad> of (x, y)."""
    layout, rend, runs, bus = geo(amp)
    X, Y, R = float(x), float(y), float(rad)
    for r in runs:
        if not r["pts"]:
            continue
        d = min(_point_seg_dist((X, Y), r["pts"][k], r["pts"][k + 1])
                for k in range(len(r["pts"]) - 1)) if len(r["pts"]) > 1 else 1e9
        if d <= R:
            print(f"run[{r['i']}] d={d:.1f} {spec_str(r['spec'])}")
            print(f"    pts {[ (round(p[0],1),round(p[1],1)) for p in r['pts'] ]}")
    for b in bus:
        if not b["pts"] or len(b["pts"]) < 2:
            continue
        d = min(_point_seg_dist((X, Y), b["pts"][k], b["pts"][k + 1])
                for k in range(len(b["pts"]) - 1))
        if d <= R:
            print(f"bus[{b['j']}] d={d:.1f} {spec_str(b['spec'])}")


def cmd_grid(amp: str):
    """Print the grid<->pixel mapping so via waypoints can be reasoned about."""
    layout, rend, runs, bus = geo(amp)
    print(f"rows={rend.rows} cols={rend.cols}")
    print(f"ex(0)={rend.ex(0):.1f} ex(1)={rend.ex(1):.1f} ex(2)={rend.ex(2):.1f}")
    print(f"ey(0)={rend.ey(0):.1f} ey(1)={rend.ey(1):.1f}")
    print(f"col step={rend.ex(1)-rend.ex(0):.2f}  row step={rend.ey(1)-rend.ey(0):.2f}")


def cmd_lint(*amps: str):
    for a in amps:
        d = ROOT / "amps" / a
        f = lint_layout(d) + lint_layout(d, style="sheet", labels_only=True)
        print(f"=== {a}: {len(f)}")
        for x in f:
            print("   ", x)


if __name__ == "__main__":
    cmd = sys.argv[1]
    globals()[f"cmd_{cmd}"](*sys.argv[2:])
