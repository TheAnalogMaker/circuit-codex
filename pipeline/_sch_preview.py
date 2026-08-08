#!/usr/bin/env python3
"""Scratch review aid: render amps/<id>/schematic.kicad_sch to a PNG so a
schematic change can be LOOKED AT without a browser.

KiCanvas is the only real renderer this project ships against, and it needs a
browser and about twelve seconds (docs/REVIEW.md). That is right for the final
proof and far too slow for the twentieth iteration of a placement fix. This
draws the same geometry the layout gate reasons about — page outline, title
block, symbol graphics, wires, junctions, labels, lettering — straight from the
file, at a fidelity good enough to answer "does this read".

It is a review aid, not a renderer: no arcs are flattened exactly, no font is
KiCad's. Never treat it as evidence about what KiCanvas shows.

    python3 _sch_preview.py 5f4              -> /tmp/sch-5f4.png
    python3 _sch_preview.py 5f4 out.png 3.0  -> scaled 3 px/mm
"""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from kiutils.schematic import Schematic

ROOT = Path(__file__).resolve().parent.parent
STD = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
       "A3": (420, 297), "A4": (297, 210), "A5": (210, 148)}


def _xf(x, y, px, py, rot, mirror):
    if mirror == "y":
        x = -x
    elif mirror == "x":
        y = -y
    rot %= 360
    if rot == 0:
        dx, dy = x, -y
    elif rot == 90:
        dx, dy = -y, -x
    elif rot == 180:
        dx, dy = -x, y
    else:
        dx, dy = y, x
    return px + dx, py + dy


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _shape(g, place):
    n = type(g).__name__
    if n == "SyRect":
        p = [place(g.start.X, g.start.Y), place(g.end.X, g.end.Y),
             place(g.start.X, g.end.Y), place(g.end.X, g.start.Y)]
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        return (f'<rect x="{min(xs):.3f}" y="{min(ys):.3f}" '
                f'width="{max(xs) - min(xs):.3f}" height="{max(ys) - min(ys):.3f}" '
                f'fill="none" stroke="#8b1a10" stroke-width="0.22"/>')
    if n == "SyCircle":
        cx, cy = place(g.center.X, g.center.Y)
        return (f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{g.radius:.3f}" '
                f'fill="none" stroke="#8b1a10" stroke-width="0.22"/>')
    if n == "SyPolyLine":
        pts = " ".join(f"{a:.3f},{b:.3f}" for a, b in (place(p.X, p.Y) for p in g.points))
        return (f'<polyline points="{pts}" fill="none" stroke="#8b1a10" '
                f'stroke-width="0.22"/>')
    if n == "SyArc":
        # three points -> a circular arc; solve the circumcentre
        (x1, y1), (x2, y2), (x3, y3) = (place(g.start.X, g.start.Y),
                                        place(g.mid.X, g.mid.Y),
                                        place(g.end.X, g.end.Y))
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(d) < 1e-9:
            return (f'<polyline points="{x1:.3f},{y1:.3f} {x2:.3f},{y2:.3f} '
                    f'{x3:.3f},{y3:.3f}" fill="none" stroke="#8b1a10" '
                    f'stroke-width="0.22"/>')
        ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1)
              + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
        uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3)
              + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
        r = math.hypot(x1 - ux, y1 - uy)
        cross = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
        sweep = 1 if cross > 0 else 0
        return (f'<path d="M {x1:.3f} {y1:.3f} A {r:.3f} {r:.3f} 0 0 {sweep} '
                f'{x3:.3f} {y3:.3f}" fill="none" stroke="#8b1a10" stroke-width="0.22"/>')
    return ""


def render(amp: str, out: Path, scale: float = 2.0) -> Path:
    sch = Schematic.from_file(str(ROOT / "amps" / amp / "schematic.kicad_sch"))
    if sch.paper.paperSize == "User":
        pw, ph = sch.paper.width, sch.paper.height
    else:
        pw, ph = STD.get(sch.paper.paperSize, (297, 210))
        if sch.paper.portrait:
            pw, ph = ph, pw

    body = [f'<rect x="0" y="0" width="{pw}" height="{ph}" fill="#fffdf7"/>',
            f'<rect x="10" y="10" width="{pw - 20}" height="{ph - 20}" '
            f'fill="none" stroke="#999" stroke-width="0.3"/>',
            f'<rect x="{pw - 110}" y="{ph - 34}" width="108" height="32" '
            f'fill="#f3ece0" stroke="#999" stroke-width="0.3"/>']
    tb = sch.titleBlock
    if tb:
        body.append(f'<text x="{pw - 108}" y="{ph - 22}" font-size="2.6" '
                    f'font-family="sans-serif" font-weight="bold">'
                    f'{_esc(tb.title)}</text>')
        body.append(f'<text x="{pw - 108}" y="{ph - 17}" font-size="2" '
                    f'font-family="sans-serif">Date: {_esc(tb.date)} · '
                    f'Rev: {_esc(tb.revision)} · {_esc(tb.company)}</text>')

    libs = {lib.libId if ":" in lib.libId else f"cx:{lib.entryName}": lib
            for lib in sch.libSymbols}
    for s in sch.schematicSymbols:
        lib = libs.get(s.libId)
        if not lib:
            continue
        px, py, rot = s.position.X, s.position.Y, int(s.position.angle or 0)
        mirror = s.mirror or ""

        def place(x, y, px=px, py=py, rot=rot, mirror=mirror):
            return _xf(x, y, px, py, rot, mirror)

        for unit in [lib, *lib.units]:
            for g in unit.graphicItems:
                body.append(_shape(g, place))
            for p in unit.pins:
                ang = int(p.position.angle or 0) % 360
                dx, dy = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}[ang]
                a = place(p.position.X, p.position.Y)
                b = place(p.position.X + dx * p.length, p.position.Y + dy * p.length)
                body.append(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" '
                            f'x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="#8b1a10" '
                            f'stroke-width="0.22"/>')
        for prop in s.properties:
            if prop.effects and prop.effects.hide:
                continue
            h = prop.effects.font.height if prop.effects else 1.27
            body.append(f'<text x="{prop.position.X:.3f}" '
                        f'y="{prop.position.Y + h * 0.36:.3f}" font-size="{h:.2f}" '
                        f'font-family="monospace" fill="#0d3b66">'
                        f'{_esc(prop.value)}</text>')

    for g in sch.graphicalItems:
        pts = getattr(g, "points", None)
        if not pts or len(pts) < 2:
            continue
        body.append(f'<line x1="{pts[0].X:.3f}" y1="{pts[0].Y:.3f}" '
                    f'x2="{pts[1].X:.3f}" y2="{pts[1].Y:.3f}" stroke="#0a6" '
                    f'stroke-width="0.22"/>')
    for j in sch.junctions:
        body.append(f'<circle cx="{j.position.X:.3f}" cy="{j.position.Y:.3f}" '
                    f'r="0.5" fill="#0a6"/>')
    for lab in [*sch.globalLabels, *sch.labels, *sch.hierarchicalLabels]:
        x, y = lab.position.X, lab.position.Y
        rot = int(lab.position.angle or 0) % 360
        anchor = {0: "start", 180: "end", 90: "start", 270: "start"}[rot]
        tr = f' transform="rotate({-90 if rot == 90 else (90 if rot == 270 else 0)} {x} {y})"'
        body.append(f'<text x="{x:.3f}" y="{y + 0.45:.3f}" font-size="1.27" '
                    f'text-anchor="{anchor}" font-family="monospace" '
                    f'fill="#7a1fa2"{tr}>{_esc(lab.text)}</text>')
    for t in sch.texts:
        h = t.effects.font.height if t.effects else 1.6
        body.append(f'<text x="{t.position.X:.3f}" y="{t.position.Y + h * 0.36:.3f}" '
                    f'font-size="{h:.2f}" font-family="sans-serif" fill="#222">'
                    f'{_esc(t.text)}</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}mm" height="{ph}mm" '
           f'viewBox="0 0 {pw} {ph}">' + "".join(body) + "</svg>")
    tmp = out.with_suffix(".svg")
    tmp.write_text(svg)
    subprocess.run(["rsvg-convert", "-z", str(scale), "-o", str(out), str(tmp)],
                   check=True)
    return out


if __name__ == "__main__":
    amp = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/sch-{amp}.png")
    render(amp, out, float(sys.argv[3]) if len(sys.argv) > 3 else 2.0)
    print(out)
