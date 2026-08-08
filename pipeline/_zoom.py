#!/usr/bin/env python3
"""Scratch review aid: render a magnified crop of a layout SVG for the
mandatory PNG read (docs/REVIEW.md). Coordinates are the SVG's own user units.

    python3 _zoom.py 5e5a house 1400 250 600 450 out.png
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def crop(amp, style, x, y, w, h, out, scale=3.0):
    svg = ROOT / "amps" / amp / ("layout-sheet.svg" if style == "sheet"
                                 else "layout.svg")
    src = svg.read_text()
    vb = re.search(r'viewBox="([-\d. ]+)"', src).group(1).split()
    vx, vy, vw, vh = (float(v) for v in vb)
    sub = re.sub(r'viewBox="[-\d. ]+"', f'viewBox="{x} {y} {w} {h}"', src, count=1)
    sub = re.sub(r'\bwidth="[\d.]+"', f'width="{w}"', sub, count=1)
    sub = re.sub(r'\bheight="[\d.]+"', f'height="{h}"', sub, count=1)
    tmp = Path("/tmp/_zoom.svg")
    tmp.write_text(sub)
    subprocess.run(["rsvg-convert", "-w", str(int(w * scale)),
                    str(tmp), "-o", out], check=True)
    print(f"{out}  (full viewBox {vx} {vy} {vw} {vh})")


if __name__ == "__main__":
    a = sys.argv
    crop(a[1], a[2], float(a[3]), float(a[4]), float(a[5]), float(a[6]), a[7],
         float(a[8]) if len(a) > 8 else 3.0)
