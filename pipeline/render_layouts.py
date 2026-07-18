#!/usr/bin/env python3
"""Render amps/<id>/layout.yaml -> amps/<id>/layout.svg in the Circuit Codex
house drawing style.

Original artwork: a tan eyelet board with a two-row eyelet grid, part bodies
drawn as simple shapes (electrolytic can, coupling/film cap, carbon resistor,
mica), each labelled with its reference designator and value. Values and part
types are read from bom.yaml — the reference designator is the shared key, so a
layout never restates a value the parts list already owns. Off-board items
(tubes, pots, jacks, transformers, switches) are drawn as labelled stubs around
the board in the order the published layout drawing shows.

This is a redrawn board diagram from published layout facts — component order
follows the drawing — never a trace or a dimensioned reproduction of a factory
drawing.

Output is fully deterministic (no randomness, no timestamps): re-running the
renderer on unchanged inputs reproduces the SVG byte-for-byte, which is what
pipeline/check_layouts.py verifies.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# ---- house palette (mirrors site/src/layouts/Base.astro tokens) ------------
INK, MUTED, FAINT = "#eee2c8", "#a3927b", "#7a6a54"
AMBER, OX = "#e89b3f", "#9c4a38"
PANEL, WELL, LINE, LINESOFT = "#211a14", "#120f0c", "#3a3025", "#2c241c"
# board + eyelets
BOARD, BOARD_EDGE = "#c2a165", "#6f5836"
BOARD_GRAIN = "#b7965c"
EYELET, EYELET_HOLE = "#e7cd92", "#2a2016"
LEAD = "#cbb891"
# component families
RES_BODY, RES_END = "#e2d4b0", "#8a6f4e"      # carbon-composition resistor body
FILM_BODY, FILM_EDGE = "#caa23e", "#8a6d28"   # mustard coupling / film cap
ELEC_BODY, ELEC_EDGE, ELEC_TOP = "#93a0a9", "#586066", "#aab5bd"  # electrolytic can
MICA_BODY, MICA_EDGE = "#8a5f45", "#5f4130"   # mica cap
# ink-on-board labels: dark, high-contrast against the tan board (as the
# original hand-lettered layout drawings read), amber-family for the ref
BOARD_REF, BOARD_VAL = "#5e3d15", "#26190c"

# ---- geometry --------------------------------------------------------------
CW = 36            # eyelet column pitch (px)
PAD_X = 30         # board interior x padding
ROW0 = 0.0         # row centre offsets are computed from BOARD_TOP
ROWGAP = 116       # px between the two eyelet rows
MARGIN_L, MARGIN_R = 128, 128
MARGIN_TOP, MARGIN_BOT = 150, 210
BODY_TOP_INSET = 0

FONT_DISP = "'Avenir Next Condensed','Arial Narrow','Helvetica Neue',Arial,sans-serif"
FONT_MONO = "'SF Mono',Menlo,Consolas,monospace"


def fmt(n: float) -> str:
    return f"{n:.1f}".rstrip("0").rstrip(".")


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def category(part: str) -> str:
    p = (part or "").lower()
    if "electrolytic" in p:
        return "electro"
    if "mica" in p:
        return "mica"
    if "capacitor" in p or "cap" in p:
        return "film"
    if "resistor" in p:
        return "res"
    if "transformer" in p:
        return "xfmr"
    if "choke" in p:
        return "choke"
    if "tube" in p:
        return "tube"
    return "other"


def primary_value(value: str) -> str:
    """First '·'-separated token of a BOM value string ('16 µF · 450 V' -> '16 µF')."""
    return str(value).split("·")[0].strip()


def load_bom(amp_dir: Path) -> dict:
    raw = yaml.safe_load((amp_dir / "bom.yaml").read_text())
    out = {}
    for it in raw.get("items", []):
        ref = it.get("ref")
        if ref and ref != "—":
            out[ref] = {"value": it.get("value", ""), "part": it.get("part", "")}
    return out


# ---- small SVG element builders --------------------------------------------
def text(x, y, s, fill, size, *, anchor="middle", font=FONT_DISP, weight=600,
         spacing=None, upper=False):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{fill}" font-size="{size}" '
            f'font-family="{font}" font-weight="{weight}" text-anchor="{anchor}"{ls}>'
            f'{esc(s)}</text>')


def eyelet(x, y, r=4.0):
    return (f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{EYELET}" '
            f'stroke="{BOARD_EDGE}" stroke-width="0.8"/>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r - 2.2)}" fill="{EYELET_HOLE}"/>')


class Renderer:
    def __init__(self, layout: dict, bom: dict, amp_id: str):
        self.layout = layout
        self.bom = bom
        self.amp_id = amp_id
        b = layout.get("board", {})
        self.rows = int(b.get("rows", 2))
        self.cols = int(b.get("cols", 20))
        self.parts = layout.get("parts", []) or []
        self.offboard = layout.get("offboard", []) or []
        self.leads = layout.get("leads", []) or []
        self.unknown: list[str] = []
        # board pixel box
        self.board_x = MARGIN_L
        self.board_y = MARGIN_TOP
        self.board_w = PAD_X * 2 + (self.cols - 1) * CW
        self.board_h = 40 + ROWGAP + 40
        self.width = self.board_x + self.board_w + MARGIN_R
        self.height = self.board_y + self.board_h + MARGIN_BOT

    # coordinate of an eyelet (row, col)
    def ex(self, col):
        return self.board_x + PAD_X + col * CW

    def ey(self, row):
        top = self.board_y + 44
        return top + row * ROWGAP

    def bom_for(self, ref):
        rec = self.bom.get(ref)
        if rec is None:
            self.unknown.append(ref)
            return {"value": "?", "part": ""}
        return rec

    # ---- board part body ----------------------------------------------------
    def part_body(self, part):
        ref = part["ref"]
        rec = self.bom_for(ref)
        cat = category(rec["part"])
        val = primary_value(rec["value"])
        a, b = part["a"], part["b"]
        (r1, c1), (r2, c2) = a, b
        x1, y1 = self.ex(c1), self.ey(r1)
        x2, y2 = self.ex(c2), self.ey(r2)
        vertical = c1 == c2 and r1 != r2
        els = []
        # leads (short wires) drawn under the body
        els.append(f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
                   f'stroke="{LEAD}" stroke-width="2"/>')
        if vertical:
            cx = x1
            cy = (y1 + y2) / 2
            els += self._body_vertical(cat, cx, cy, val, ref)
        else:
            cx = (x1 + x2) / 2
            cy = y1
            span = abs(c2 - c1)
            els += self._body_horizontal(cat, cx, cy, span, val, ref)
        # eyelets on top of leads
        els.append(eyelet(x1, y1))
        els.append(eyelet(x2, y2))
        return "".join(els)

    def _label_pair(self, cx, top_y, bot_y, ref, val):
        return (text(cx, top_y, ref, BOARD_REF, 11.5, weight=700, spacing="0.02em")
                + text(cx, bot_y, val, BOARD_VAL, 11, font=FONT_MONO, weight=600))

    def _body_horizontal(self, cat, cx, cy, span, val, ref):
        w = max(26.0, span * CW - 16)
        els = []
        if cat == "electro":
            h = 42
            x, y = cx - w / 2, cy - h + 8
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="6" fill="{ELEC_BODY}" stroke="{ELEC_EDGE}" stroke-width="1.2"/>')
            els.append(f'<ellipse cx="{fmt(cx)}" cy="{fmt(y)}" rx="{fmt(w/2)}" ry="4.5" '
                       f'fill="{ELEC_TOP}" stroke="{ELEC_EDGE}" stroke-width="1"/>')
            els.append(f'<line x1="{fmt(x+6)}" y1="{fmt(y+9)}" x2="{fmt(x+14)}" y2="{fmt(y+9)}" '
                       f'stroke="{WELL}" stroke-width="1.6"/>')  # + bar
            els.append(f'<line x1="{fmt(x+10)}" y1="{fmt(y+5)}" x2="{fmt(x+10)}" y2="{fmt(y+13)}" '
                       f'stroke="{WELL}" stroke-width="1.6"/>')  # + stem
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(cy+8-2)}" x2="{fmt(x+w)}" y2="{fmt(cy+8-2)}" '
                       f'stroke="{ELEC_EDGE}" stroke-width="1"/>')
            els.append(self._label_pair(cx, y - 6, cy + 24, ref, val))
        elif cat == "mica":
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="4" fill="{MICA_BODY}" stroke="{MICA_EDGE}" stroke-width="1.2"/>')
            els.append(self._label_pair(cx, y - 6, cy + 20, ref, val))
        elif cat == "film":
            h = 22
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="10" fill="{FILM_BODY}" stroke="{FILM_EDGE}" stroke-width="1.2"/>')
            els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y+2)}" x2="{fmt(cx)}" y2="{fmt(y+h-2)}" '
                       f'stroke="{FILM_EDGE}" stroke-width="0.8" opacity="0.7"/>')
            els.append(self._label_pair(cx, y - 6, cy + 22, ref, val))
        else:  # resistor / other
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="7" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            for ex_ in (x + 5, x + w - 5):
                els.append(f'<line x1="{fmt(ex_)}" y1="{fmt(y+1)}" x2="{fmt(ex_)}" y2="{fmt(y+h-1)}" '
                           f'stroke="{RES_END}" stroke-width="2"/>')
            els.append(self._label_pair(cx, y - 6, cy + 21, ref, val))
        return els

    def _body_vertical(self, cat, cx, cy, val, ref):
        # vertical carbon/wirewound resistor bridging the two rows (cathode legs)
        h = 40
        w = 15
        x, y = cx - w / 2, cy - h / 2
        els = []
        fill = RES_BODY
        if cat == "electro":
            fill = ELEC_BODY
        els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                   f'rx="6" fill="{fill}" stroke="{RES_END}" stroke-width="1"/>')
        if cat != "electro":
            for ey_ in (y + 5, y + h - 5):
                els.append(f'<line x1="{fmt(x+1)}" y1="{fmt(ey_)}" x2="{fmt(x+w-1)}" y2="{fmt(ey_)}" '
                           f'stroke="{RES_END}" stroke-width="2"/>')
        # label sits to the right, except near the right board edge where it
        # would overflow — then flip it to the left.
        if cx > self.board_x + self.board_w - 64:
            lx, anchor = cx - w / 2 - 6, "end"
        else:
            lx, anchor = cx + w / 2 + 6, "start"
        els.append(text(lx, cy - 3, ref, BOARD_REF, 11.5, weight=700,
                        anchor=anchor, spacing="0.02em"))
        els.append(text(lx, cy + 11, val, BOARD_VAL, 11, anchor=anchor,
                        font=FONT_MONO, weight=600))
        return els

    # ---- off-board stubs ----------------------------------------------------
    def off_pos(self, item):
        edge = item.get("edge", "bottom")
        at = float(item.get("at", 0))
        if edge in ("top", "bottom"):
            x = self.ex(at)
            y = (self.board_y - 78) if edge == "top" else (self.board_y + self.board_h + 74)
        elif edge == "left":
            x = self.board_x - 72
            y = self.ey(0) + at * ROWGAP
        else:  # right
            x = self.board_x + self.board_w + 72
            y = self.ey(0) + at * ROWGAP
        return x, y

    def off_stub(self, item):
        kind = item.get("kind", "tube")
        label = item.get("label", item.get("id", ""))
        ref = item.get("ref")
        x, y = self.off_pos(item)
        val = primary_value(self.bom_for(ref)["value"]) if ref else None
        els = []
        if kind == "tube":
            r = 22
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{PANEL}" '
                       f'stroke="{AMBER}" stroke-width="1.8"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="6.5" fill="none" '
                       f'stroke="{FAINT}" stroke-width="1"/>')
            import math
            for k in range(8):
                ang = -90 + k * 45
                px = x + 13 * math.cos(math.radians(ang))
                py = y + 13 * math.sin(math.radians(ang))
                els.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="1.8" fill="{MUTED}"/>')
            els.append(text(x, y + r + 15, label, INK, 12, spacing="0.05em"))
        elif kind == "pot":
            r = 18
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{PANEL}" '
                       f'stroke="{MUTED}" stroke-width="1.6"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{MUTED}"/>')
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(x)}" y2="{fmt(y-r+3)}" '
                       f'stroke="{AMBER}" stroke-width="2"/>')
            els.append(text(x, y + r + 14, label, INK, 11.5, spacing="0.04em"))
            if val:
                els.append(text(x, y + r + 27, val, MUTED, 10.5, font=FONT_MONO, weight=500))
        elif kind == "jack":
            r = 9
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{WELL}" '
                       f'stroke="{MUTED}" stroke-width="1.6"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{MUTED}"/>')
            els.append(text(x, y + r + 13, label, MUTED, 10.5, spacing="0.03em"))
        elif kind in ("xfmr", "choke"):
            w, h = (46, 56) if kind == "xfmr" else (40, 34)
            els.append(f'<rect x="{fmt(x-w/2)}" y="{fmt(y-h/2)}" width="{w}" height="{h}" rx="4" '
                       f'fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>')
            for dx in (-6, 0, 6):
                els.append(f'<line x1="{fmt(x+dx)}" y1="{fmt(y-h/2+5)}" x2="{fmt(x+dx)}" '
                           f'y2="{fmt(y+h/2-5)}" stroke="{FAINT}" stroke-width="1.4"/>')
            els.append(text(x, y + h / 2 + 14, label, INK, 11.5, spacing="0.04em"))
            if val:
                els.append(text(x, y + h / 2 + 27, val, MUTED, 10.5, font=FONT_MONO, weight=500))
        else:  # switch / fuse / misc
            w, h = 34, 18
            els.append(f'<rect x="{fmt(x-w/2)}" y="{fmt(y-h/2)}" width="{w}" height="{h}" rx="4" '
                       f'fill="{PANEL}" stroke="{LINE}" stroke-width="1.4"/>')
            els.append(text(x, y + h / 2 + 13, label, MUTED, 10.5, spacing="0.03em"))
        return "".join(els)

    def lead_run(self, lead):
        def pt(endpoint):
            if isinstance(endpoint, (list, tuple)):
                return self.ex(endpoint[1]), self.ey(endpoint[0])
            for it in self.offboard:
                if it.get("id") == endpoint:
                    return self.off_pos(it)
            return None
        a = pt(lead.get("from"))
        b = pt(lead.get("to"))
        if not a or not b:
            return ""
        mx = (a[0] + b[0]) / 2
        return (f'<path d="M {fmt(a[0])} {fmt(a[1])} Q {fmt(mx)} {fmt((a[1]+b[1])/2)} '
                f'{fmt(b[0])} {fmt(b[1])}" fill="none" stroke="{LINESOFT}" '
                f'stroke-width="1.4" opacity="0.85"/>')

    # ---- assemble -----------------------------------------------------------
    def render(self) -> str:
        els = []
        # board panel
        bx, by, bw, bh = self.board_x, self.board_y, self.board_w, self.board_h
        els.append(f'<rect x="{fmt(bx)}" y="{fmt(by)}" width="{fmt(bw)}" height="{fmt(bh)}" '
                   f'rx="10" fill="{BOARD}" stroke="{BOARD_EDGE}" stroke-width="2"/>')
        # faint grain lines
        for gy in (self.ey(0), self.ey(1)):
            els.append(f'<line x1="{fmt(bx+12)}" y1="{fmt(gy)}" x2="{fmt(bx+bw-12)}" y2="{fmt(gy)}" '
                       f'stroke="{BOARD_GRAIN}" stroke-width="12" opacity="0.35" '
                       f'stroke-linecap="round"/>')
        # faint full eyelet grid
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.ex(c), self.ey(r)
                els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="2.4" fill="{EYELET_HOLE}" '
                           f'opacity="0.5"/>')
        # optional lead runs (under parts/stubs)
        for lead in self.leads:
            els.append(self.lead_run(lead))
        # off-board stubs
        for it in self.offboard:
            els.append(self.off_stub(it))
        # board parts
        for p in self.parts:
            els.append(self.part_body(p))
        # title + attribution
        title = (self.layout.get("board", {}) or {}).get("title") or f"{self.amp_id.upper()} board layout"
        els.append(text(bx, 34, title, INK, 17, anchor="start", spacing="0.08em"))
        src = self.layout.get("source", {}) or {}
        if src.get("desc"):
            attrib = f"Redrawn from {src['desc']} — not a trace"
        else:
            attrib = self.layout.get("caption") or ""
        if attrib:
            els.append(text(bx, self.height - 42, attrib, FAINT, 10.5, anchor="start",
                            font=FONT_MONO, weight=500))
        # legend
        self._legend(els)
        body = "\n".join(els)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(self.width)} '
               f'{fmt(self.height)}" role="img" aria-label="{esc(title)} — redrawn board '
               f'layout diagram" width="100%" font-family="{FONT_DISP}">\n'
               f'<rect x="0" y="0" width="{fmt(self.width)}" height="{fmt(self.height)}" '
               f'fill="{WELL}"/>\n{body}\n</svg>\n')
        if self.unknown:
            raise ValueError(f"{self.amp_id}: layout refs absent from bom.yaml: "
                             f"{sorted(set(self.unknown))}")
        return svg

    def _legend(self, els):
        items = [(RES_BODY, "resistor"), (FILM_BODY, "film / coupling cap"),
                 (ELEC_BODY, "electrolytic"), (MICA_BODY, "mica")]
        x = self.board_x
        y = self.height - 20
        els.append(text(x, y, "Bodies:", FAINT, 10.5, anchor="start", font=FONT_MONO, weight=500))
        cx = x + 52
        for fill, lab in items:
            els.append(f'<rect x="{fmt(cx)}" y="{fmt(y-8)}" width="14" height="9" rx="2.5" '
                       f'fill="{fill}" stroke="{BOARD_EDGE}" stroke-width="0.6"/>')
            els.append(text(cx + 19, y, lab, MUTED, 10.5, anchor="start", font=FONT_MONO,
                            weight=500))
            cx += 26 + len(lab) * 6.4


def render_layout(amp_dir: Path) -> str:
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    return Renderer(layout, bom, amp_dir.name).render()


def render_all(write: bool = True) -> list[Path]:
    written = []
    for yml in sorted((ROOT / "amps").glob("*/layout.yaml")):
        svg = render_layout(yml.parent)
        out = yml.parent / "layout.svg"
        if write:
            out.write_text(svg)
        written.append(out)
        print(f"rendered {out.relative_to(ROOT)} ({len(svg)} bytes)")
    return written


if __name__ == "__main__":
    render_all(write=True)
    if not list((ROOT / "amps").glob("*/layout.yaml")):
        print("no layout.yaml files found", file=sys.stderr)
