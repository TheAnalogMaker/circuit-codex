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


================================ SCHEMA v2 ==================================
layout.yaml grows an optional **wiring layer** on top of the placement layer.
Everything below `parts` / `offboard` is unchanged; `runs` and `bus` are new.

board:            { rows, cols, title }
caption:          provenance line (public-documentation voice)
source:           { desc, url }               the published layout drawing
parts:            [ { ref, a:[row,col], b:[row,col], nudge?:[dx,dy] } ]
                    Board-mounted parts. `ref` keys into bom.yaml (value + type).
                    Same row -> axial body; shared column -> vertical leg.
                    Optional `nudge` shifts the ref/value label pair (px) to
                    keep it clear of wiring.
offboard:         [ { id, ref?, kind, edge, at, label, glyph? } ]
                    kind: tube | pot | jack | xfmr | choke | switch | part
                    Tubes draw their real pin ring + numbers (pin count read
                    from reference/tubes/<tube>.yaml basing data).
                    kind: part is a generic 2-lead off-board component with two
                    addressable terminals (REF.a / REF.b) — the pilot lamp and
                    chassis-mounted resistors (e.g. a grid-leak at the input
                    jacks) that don't sit on the eyelet board. glyph: lamp draws
                    the pilot-lamp glyph (bulb + bayonet base hint); otherwise a
                    small axial body is drawn (typed from bom.yaml when a ref is
                    given, else neutral). Its .a/.b terminals face the board so
                    runs land on them like any other endpoint.

--- runs: routed hookup leads -------------------------------------------------
runs:
  - { from: <endpoint>, to: <endpoint>, color?: <name>, style?: twisted,
      via?: [[x,y], ...] }

  <endpoint> is one of:
    [row, col]      a bare board eyelet (row 0/1, integer col)
    "REF.a"/"REF.b" a board part's eyelet (REF is a parts[] ref; .a/.b picks
                    which of its two endpoints). Also addresses a generic
                    2-lead OFF-board part (kind: part) by its .a/.b terminals.
    "V1.pin3"       a tube socket pin. The pin number is VALIDATED against the
                    tube's basing data in reference/tubes/<tube>.yaml — an
                    out-of-range or unknown pin fails the render (and CI). On a
                    style:twisted (heater) run, a tube endpoint is additionally
                    required to be a HEATER/FILAMENT pin (element heater |
                    heater-ct | filament in the basing — noval 4/5/9, octal 2/7,
                    rectifier filament 2/8); a signal pin on a heater run fails.
    "VR1.lug2"      a potentiometer lug (1 | 2 | 3; 2 is the wiper).
    "JI" / "JI.tip" / "JI.sleeve"   a jack (bare id = body; .tip/.sleeve pin).
    "T2.green"      a transformer / choke lead, addressed by colour name. Each
                    distinct colour used on a given transformer gets its own
                    stacked, colour-matched pigtail on the board-facing edge.

  color?  optional era wire colour NAME (see WIRE palette). It is mapped to a
          small house-tuned palette that stays legible on the dark board, and
          shows up in the drawing's colour legend. Uncoloured runs render in
          the neutral hookup-lead tone.
  style?  optional. "twisted" renders the run as two interleaved sinusoidal
          strands sharing the run's endpoints — the classic 6.3 V heater idiom.
          Twisted runs default to the heater green (with green-yellow available
          for a centre-tap lead where a drawing marks one) and earn their own
          legend entry ("6.3 V heaters — twisted pair") instead of a colour
          swatch. Use for the filament/heater chain: PT green pair → pilot
          lamp → socket to socket in the drawing's daisy order.
  via?    optional routing waypoints, in GRID units [x, y] where x = column
          axis and y = row axis (same axes as eyelets, but note the [x, y]
          order is the drawing's, i.e. horizontal-first — the opposite of a
          part endpoint's [row, col]). y < 0 routes above the board, y > (rows-1)
          below it. Fractions allowed. Runs bend through these with rounded
          elbows, so a couple of waypoints keep a lead off its neighbours.

--- bus: ground-bus segments --------------------------------------------------
bus:
  - { from: <endpoint>, to: <endpoint>, via?: [[x,y], ...] }

  The bare ground bus that runs the length of the board. Same endpoint grammar
  and `via` waypoints as runs, but drawn as a single heavier bare-wire line
  (no colour, no casing) so it reads as the ground rod it is.
============================================================================
"""
from __future__ import annotations

import math
import shutil
import subprocess
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

# ---- wiring palette --------------------------------------------------------
# Era wire-colour names mapped to a small, house-tuned palette. Each colour is
# nudged toward the amber/warm register of the house style and kept light/
# saturated enough to stay legible on the tan board AND the dark well. "black"
# can't be literal (it would vanish on the dark ground) — it becomes a legible
# slate; the striped factory leads ("red-yellow") become a single warm hue.
WIRE = {
    "black":        "#5f6672",   # legible slate (literal black is invisible here)
    "brown":        "#a9743f",
    "red":          "#d8564a",
    "orange":       "#e28f38",
    "yellow":       "#d8b23c",
    "green":        "#5fa64f",
    "blue":         "#4f8fcf",
    "violet":       "#a279c6",
    "purple":       "#a279c6",
    "grey":         "#9c968a",
    "gray":         "#9c968a",
    "white":        "#e7dcc2",
    "red-yellow":   "#d79a45",   # HT centre-tap striped lead -> warm amber
    "green-yellow": "#9cba50",
    "blue-white":   "#8fb4dc",
    "red-blue":     "#c56f93",   # bias-tap striped lead -> red with a violet cast
}
WIRE_NEUTRAL = "#b7a483"          # uncoloured hookup lead
WIRE_CASING = WELL                # dark halo behind a run, for crossings
# 6.3 V heater / filament twisted pair: the heater green, a touch brighter than
# the generic "green" run so the interleaved strands read as the heater idiom.
HEATER = "#6fbf59"
HEATER_CT = "#9cba50"             # green-yellow centre-tap strand, when marked
# pilot-lamp glyph
LAMP_GLASS, LAMP_GLASS_EDGE = "#e8b552", "#9c6b1f"   # warm amber jewel
LAMP_BASE, LAMP_BASE_EDGE = "#9aa2a9", "#5b636a"     # bayonet base
# bare-wire ground bus: a light tinned-wire core over a darker edge, so it
# reads as a solid rod laid across the board.
BUS_CORE, BUS_EDGE = "#e6dcc2", "#6f5836"
# terminal dot (solder joint) at a run endpoint
TERM_FILL, TERM_RING = "#e7cd92", "#3a2c18"
# solder-blob at a run ENDPOINT — a larger filled dot + darker ring, clearly
# distinct from a via waypoint (undrawn) or a pass-through eyelet, so where a
# wire LANDS is never in doubt even inside a convergence cluster.
SOLDER_FILL, SOLDER_RING, SOLDER_HL = "#dcc487", "#241a0e", "#f4ead0"

# ---- hop-over crossings ----------------------------------------------------
# At every transversal crossing between two plain (non-twisted) runs, the run
# appearing LATER in the runs list hops the earlier one with a small
# semicircular bridge — the classic wiring-diagram idiom. The ground bus never
# hops (runs hop over it); twisted heater pairs are exempt (topmost layer).
HOP_R = 3.5              # semicircle radius for a run-over-run hop (px)
HOP_R_BUS = 5.2          # a run hopping the heavier ground bus needs more lift
HOP_MIN_ANGLE = 18.0     # a crossing flatter than this is a near-parallel graze
HOP_END_CLEAR = 6.0      # skip hops within ~6 px of either segment's endpoints

# ---- geometry --------------------------------------------------------------
CW = 36            # eyelet column pitch (px)
PAD_X = 30         # board interior x padding
ROW0 = 0.0         # row centre offsets are computed from BOARD_TOP
ROWGAP = 116       # px between the two eyelet rows
MARGIN_L, MARGIN_R = 128, 128
MARGIN_TOP, MARGIN_BOT = 150, 236
BODY_TOP_INSET = 0
TUBE_R = 26        # tube socket radius (px)

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


_WIRE_KEYS_BY_LEN = sorted(WIRE, key=len, reverse=True)


def lead_base(name: str) -> str | None:
    """Base colour NAME of a transformer-lead suffix — 'red1'/'red-a' -> 'red',
    'red-yellow' -> 'red-yellow'. Longest matching palette key wins."""
    s = str(name).lower()
    for key in _WIRE_KEYS_BY_LEN:
        if s.startswith(key):
            return key
    return None


def colour_hex(name: str | None) -> str:
    return WIRE.get(str(name).lower(), WIRE_NEUTRAL) if name else WIRE_NEUTRAL


def tube_slug(value: str) -> str:
    """'12AY7' / '6V6GT' -> reference/tubes filename stem ('12ay7', '6v6gt').

    NOTE: this is the *raw* slug of a single token. For a real BOM value that may
    carry an EU/US equivalent name ('ECC83 (12AX7)'), use resolve_tube_slug(),
    which aliases to the canonical basing/model slug this corpus carries — a raw
    slug of 'ECC83 (12AX7)' is 'ecc8312ax7', which matches no basing file."""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


# ---- valve equivalents (EU/US) ---------------------------------------------
# Common cross-labellings that share a basing/model with a tube this corpus
# carries but may be printed under the other name on a drawing/BOM. This is a
# SUPPLEMENT; the primary alias source is each reference/tubes/<slug>.yaml
# `also_known_as` list (data-driven, self-maintaining — see _valve_alias_map()).
_VALVE_ALIAS_SUPPLEMENT = {
    "ecc83": "12ax7", "7025": "12ax7", "12ax7a": "12ax7", "6681": "12ax7",
    "ecc82": "12au7", "12au7a": "12au7", "5814a": "12au7", "5963": "12au7",
    "ecc81": "12at7", "12at7a": "12at7", "6201": "12at7",
    "ecc88": "6dj8", "6922": "6dj8", "e88cc": "6dj8",
    "ecc85": "6aq8",
    "6ca7": "el34", "6ca7": "el34",
    "7027a": "6l6g", "5932": "6l6g", "6l6": "6l6g", "6l6gc": "6l6g",
    "6p1": "6v6gt", "6v6": "6v6gt", "6v6g": "6v6gt",
    "cv1988": "kt66", "u77": "gz34", "cv1377": "gz34", "5ar4": "gz34",
    "5z4": "5y3gt", "5y3": "5y3gt", "5u4": "5u4g", "5u4gb": "5u4g",
}

_ALIAS_CACHE: dict | None = None


def _valve_alias_map() -> dict:
    """alias-slug -> canonical tube slug, built from every reference/tubes YAML's
    own name + `also_known_as` (self-maintaining), then the hardcoded supplement.
    A canonical tube always maps to itself. Cached."""
    global _ALIAS_CACHE
    if _ALIAS_CACHE is not None:
        return _ALIAS_CACHE
    amap: dict = {}
    tubes_dir = ROOT / "reference" / "tubes"
    if tubes_dir.exists():
        for path in sorted(tubes_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text()) or {}
            except Exception:  # noqa: BLE001 — a malformed YAML shouldn't crash aliasing
                continue
            canon = str(data.get("tube") or path.stem).strip()
            canon_slug = tube_slug(canon) or path.stem
            amap[canon_slug] = canon_slug
            amap.setdefault(tube_slug(str(data.get("name", ""))), canon_slug)
            for aka in (data.get("also_known_as") or []):
                s = tube_slug(str(aka))
                if s:
                    amap.setdefault(s, canon_slug)
    for alias, canon in _VALVE_ALIAS_SUPPLEMENT.items():
        # only trust the supplement when its target basing actually exists
        if (tubes_dir / f"{canon}.yaml").exists():
            amap.setdefault(alias, canon)
    amap.pop("", None)
    _ALIAS_CACHE = amap
    return amap


def resolve_tube_slug(value: str) -> str:
    """Resolve a BOM tube value to the reference/tubes basing slug, honouring
    EU/US equivalents. '12AX7' -> '12ax7'; 'ECC83 (12AX7)' -> '12ax7';
    'ECC83' -> '12ax7'. Resolution order:
      1. the raw slug of the whole value, if it names a basing file or alias;
      2. else each alphanumeric token of the value, first that resolves wins;
      3. else the raw whole-value slug (which will fail-hard downstream on a
         claimed amp rather than silently skipping the tube).
    This is the H1 fix: a valve printed under its EU name still anchors."""
    amap = _valve_alias_map()
    tubes_dir = ROOT / "reference" / "tubes"

    def _resolve(slug: str) -> str | None:
        if not slug:
            return None
        if slug in amap:
            return amap[slug]
        if (tubes_dir / f"{slug}.yaml").exists():
            return slug
        return None

    whole = tube_slug(value)
    hit = _resolve(whole)
    if hit:
        return hit
    for tok in str(value).replace("(", " ").replace(")", " ").split():
        hit = _resolve(tube_slug(tok))
        if hit:
            return hit
    return whole


def load_tube_pins(slug: str) -> set[int] | None:
    """Valid pin numbers for a tube from reference/tubes/<slug>.yaml, or None."""
    path = ROOT / "reference" / "tubes" / f"{slug}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    pins = ((data.get("basing") or {}).get("pins") or {})
    try:
        return {int(k) for k in pins}
    except (TypeError, ValueError):
        return None


_HEATER_ELEMENTS = {"heater", "heater-ct", "filament"}


def load_tube_heater_pins(slug: str) -> set[int] | None:
    """Heater / filament pin numbers for a tube (element in {heater, heater-ct,
    filament}) from reference/tubes/<slug>.yaml basing, or None if unknown.
    Noval dual-triodes: 4/5 heater + 9 heater-ct; octal power tubes: 2/7;
    directly-heated rectifiers: 2/8 filament. A style:twisted (heater) run is
    validated against this set so a heater lead can't land on a signal pin."""
    path = ROOT / "reference" / "tubes" / f"{slug}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    pins = ((data.get("basing") or {}).get("pins") or {})
    out: set[int] = set()
    for k, meta in pins.items():
        try:
            num = int(k)
        except (TypeError, ValueError):
            continue
        if isinstance(meta, dict) and str(meta.get("element", "")).lower() in _HEATER_ELEMENTS:
            out.add(num)
    return out or None


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


def term_dot(x, y, r=2.7):
    return (f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{TERM_FILL}" '
            f'stroke="{TERM_RING}" stroke-width="0.9"/>')


def solder_blob(x, y):
    """A run ENDPOINT solder joint: a larger filled dot inside a darker ring,
    with a small specular highlight so it reads as a soldered blob rather than a
    bare eyelet or a mid-wire via. Deterministic."""
    return (f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="4.4" fill="none" '
            f'stroke="{SOLDER_RING}" stroke-width="1.8"/>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3.2" fill="{SOLDER_FILL}" '
            f'stroke="{SOLDER_RING}" stroke-width="0.7"/>'
            f'<circle cx="{fmt(x - 1.0)}" cy="{fmt(y - 1.0)}" r="1.0" '
            f'fill="{SOLDER_HL}" opacity="0.85"/>')


# ---- wire-crossing geometry (hop-overs + lint) -----------------------------
def _seg_len(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _seg_unit(a, b):
    L = _seg_len(a, b) or 1e-9
    return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def _seg_angle_deg(a1, a2, b1, b2):
    """Acute angle (0..90 deg) between two segments' directions."""
    v1 = (a2[0] - a1[0], a2[1] - a1[1])
    v2 = (b2[0] - b1[0], b2[1] - b1[1])
    l1 = math.hypot(*v1)
    l2 = math.hypot(*v2)
    if l1 < 1e-9 or l2 < 1e-9:
        return 0.0
    cosang = abs((v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2))
    return math.degrees(math.acos(min(1.0, cosang)))


def _seg_intersection(a1, a2, b1, b2):
    """Proper interior crossing of segments a1-a2 and b1-b2. Returns
    (t, s, (px, py)) with 0<t<1, 0<s<1, or None."""
    x1, y1 = a1
    x2, y2 = a2
    x3, y3 = b1
    x4, y4 = b2
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-9:
        return None
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    s = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    if 0.0 < t < 1.0 and 0.0 < s < 1.0:
        return (t, s, (x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    return None


def _point_seg_dist(p, a, b):
    """Shortest distance from point p to segment a-b."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rounded_path(points, r=11.0):
    """SVG path string through `points` [(x,y),...] with rounded elbows of
    radius r (clamped to half the shorter adjacent segment). Deterministic."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        return ""
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return f"M {fmt(x0)} {fmt(y0)} L {fmt(x1)} {fmt(y1)}"
    d = [f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        v0 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l0 = math.hypot(*v0) or 1.0
        l2 = math.hypot(*v2) or 1.0
        rr = min(r, l0 / 2, l2 / 2)
        a = (p1[0] + v0[0] / l0 * rr, p1[1] + v0[1] / l0 * rr)   # entry of corner
        b = (p1[0] + v2[0] / l2 * rr, p1[1] + v2[1] / l2 * rr)   # exit of corner
        d.append(f"L {fmt(a[0])} {fmt(a[1])}")
        d.append(f"Q {fmt(p1[0])} {fmt(p1[1])} {fmt(b[0])} {fmt(b[1])}")
    d.append(f"L {fmt(pts[-1][0])} {fmt(pts[-1][1])}")
    return " ".join(d)


def twisted_strands(points, amp=3.4, wavelen=15.0, step=3.0):
    """Two interleaved sinusoidal strand paths through `points` [(x,y),...] that
    share the polyline's endpoints — the classic twisted-pair (heater) idiom.
    A half-sine amplitude window forces both strands to meet exactly at the two
    ends; between them they weave with opposite phase so they read as a twist.
    Deterministic. Returns (d_strand1, d_strand2)."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        return "", ""
    # cumulative arc length along the straight polyline
    seg = []
    total = 0.0
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        d = math.hypot(dx, dy) or 1e-6
        seg.append((total, d, (dx / d, dy / d)))
        total += d
    if total < 1e-6:
        return "", ""
    k = 2 * math.pi / wavelen
    n = max(2, int(total / step))
    s1, s2 = [], []
    for j in range(n + 1):
        s = total * j / n
        # locate segment
        idx = 0
        for m in range(len(seg)):
            if s >= seg[m][0] and (m == len(seg) - 1 or s < seg[m + 1][0]):
                idx = m
                break
        s0, d, (ux, uy) = seg[idx]
        t = s - s0
        px = pts[idx][0] + ux * t
        py = pts[idx][1] + uy * t
        nx, ny = -uy, ux                       # left normal
        env = amp * math.sin(math.pi * s / total)   # 0 at both ends
        off = env * math.sin(k * s)
        s1.append((px + nx * off, py + ny * off))
        s2.append((px - nx * off, py - ny * off))
    d1 = "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in s1)
    d2 = "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in s2)
    return d1, d2


def hopped_path(points, seg_hops, r=11.0):
    """SVG path through `points` with rounded elbows (radius r, as rounded_path)
    AND small semicircular hop-over bridges inserted at the crossings listed in
    `seg_hops` — a dict {segment_index: [(dist_along_segment, hop_r), ...]}.
    A hop bows to a deterministic side (up for horizontal-ish runs, right for
    vertical-ish) and is only drawn when its arc fits inside the segment's
    straight, un-rounded span, so it never fouls an elbow. Deterministic; with
    an empty `seg_hops` it reproduces rounded_path's geometry."""
    pts = [(float(x), float(y)) for x, y in points]
    n = len(pts)
    if n < 2:
        return ""
    seglen = [_seg_len(pts[i], pts[i + 1]) for i in range(n - 1)]
    segu = [_seg_unit(pts[i], pts[i + 1]) for i in range(n - 1)]
    # corner radius at each interior vertex (matches rounded_path's clamp)
    cr = [0.0] * n
    for k in range(1, n - 1):
        cr[k] = min(r, seglen[k - 1] / 2, seglen[k] / 2)
    d = [f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"]
    for i in range(n - 1):
        ux, uy = segu[i]
        L = seglen[i]
        cut_start = cr[i] if i >= 1 else 0.0
        cut_end = cr[i + 1] if (i + 1) <= (n - 2) else 0.0
        # bulge normal: prefer up (-y); for vertical runs prefer right (+x)
        p1, p2 = (-uy, ux), (uy, -ux)
        if p1[1] != p2[1]:
            nrm = p1 if p1[1] < p2[1] else p2
        else:
            nrm = p1 if p1[0] >= p2[0] else p2
        sweep = 1 if (ux * nrm[1] - uy * nrm[0]) < 0 else 0
        seg_end = (pts[-1] if i == n - 2
                   else (pts[i + 1][0] - ux * cr[i + 1], pts[i + 1][1] - uy * cr[i + 1]))
        for (dist, hop_r) in seg_hops.get(i, []):
            if dist - hop_r < cut_start + 0.5 or dist + hop_r > L - cut_end - 0.5:
                continue
            cx, cy = pts[i][0] + ux * dist, pts[i][1] + uy * dist
            d.append(f"L {fmt(cx - ux * hop_r)} {fmt(cy - uy * hop_r)}")
            d.append(f"A {fmt(hop_r)} {fmt(hop_r)} 0 0 {sweep} "
                     f"{fmt(cx + ux * hop_r)} {fmt(cy + uy * hop_r)}")
        d.append(f"L {fmt(seg_end[0])} {fmt(seg_end[1])}")
        if i < n - 2:
            bx = pts[i + 1][0] + segu[i + 1][0] * cr[i + 1]
            by = pts[i + 1][1] + segu[i + 1][1] * cr[i + 1]
            d.append(f"Q {fmt(pts[i + 1][0])} {fmt(pts[i + 1][1])} {fmt(bx)} {fmt(by)}")
    return " ".join(d)


def compute_hops(wires):
    """Given `wires` — a list of {key, order, points, is_bus} for every plain
    (non-twisted) run and every ground-bus segment-set — return a hop map
    {key: {segment_index: [(dist, hop_r), ...]}}. At each transversal crossing
    the wire with the HIGHER order (later in the runs list) hops; the ground bus
    (order -1) never hops but is hopped over. Deterministic."""
    segs = []
    for w in wires:
        p = w["points"]
        for si in range(len(p) - 1):
            segs.append((w["order"], w["key"], si, p[si], p[si + 1], w["is_bus"]))
    hops: dict = {}
    for oa, ka, sia, a1, a2, _busa in segs:
        for ob, kb, sib, b1, b2, busb in segs:
            if ka == kb or oa <= ob:      # only the later wire hops; skip self
                continue
            inter = _seg_intersection(a1, a2, b1, b2)
            if inter is None:
                continue
            if _seg_angle_deg(a1, a2, b1, b2) < HOP_MIN_ANGLE:
                continue                   # near-parallel graze — a lint case
            t, s, _p = inter
            lenA, lenB = _seg_len(a1, a2), _seg_len(b1, b2)
            distA, distB = t * lenA, s * lenB
            if min(distA, lenA - distA) < HOP_END_CLEAR:
                continue
            if min(distB, lenB - distB) < HOP_END_CLEAR:
                continue
            hop_r = HOP_R_BUS if busb else HOP_R
            hops.setdefault(ka, {}).setdefault(sia, []).append((distA, hop_r))
    # sort each segment's hops and drop ones that would overlap a neighbour
    for key in hops:
        for si in hops[key]:
            merged: list = []
            for dist, hop_r in sorted(hops[key][si]):
                if merged and dist - merged[-1][0] < merged[-1][1] + hop_r + 1.0:
                    continue
                merged.append((dist, hop_r))
            hops[key][si] = merged
    return hops


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
        self.leads = layout.get("leads", []) or []           # legacy soft leads
        self.runs = layout.get("runs", []) or []             # v2 wiring
        self.bus = layout.get("bus", []) or []               # v2 ground bus
        self.errors: list[str] = []
        # indexes
        self.part_by_ref = {p["ref"]: p for p in self.parts if "ref" in p}
        self.off_by_id = {it["id"]: it for it in self.offboard if "id" in it}
        # resolve tube basing for every off-board tube
        for it in self.offboard:
            if it.get("kind") == "tube":
                slug = resolve_tube_slug(primary_value(self.bom_for(it["ref"])["value"])) \
                    if it.get("ref") else ""
                pins = load_tube_pins(slug) if slug else None
                it["_pins"] = pins
                it["_pincount"] = (max(pins) if pins else 8)
                it["_heater_pins"] = load_tube_heater_pins(slug) if slug else None
        # transformer lead colour slots (assigned from run/bus endpoints)
        self._assign_xfmr_leads()
        self._colours_used: list[str] = []
        self._has_twisted = False
        # board pixel box
        self.board_x = MARGIN_L
        self.board_y = MARGIN_TOP
        self.board_w = PAD_X * 2 + (self.cols - 1) * CW
        self.board_h = 40 + ROWGAP + 40
        self.width = self.board_x + self.board_w + MARGIN_R
        # a wired layout needs an under-chassis band below the sockets for the
        # long left-right harness leads; a placement-only layout stays compact.
        # A deep routing lane (e.g. the twisted heater bus laid below the output
        # harness) grows the band so it clears the bottom legend/attribution.
        if self.runs or self.bus:
            deep_row = float(self.rows - 1)
            for spec in (list(self.runs) + list(self.bus)):
                for v in (spec.get("via") or []):
                    if isinstance(v, (list, tuple)) and len(v) == 2:
                        try:
                            deep_row = max(deep_row, float(v[1]))
                        except (TypeError, ValueError):
                            pass
            # ey() needs board_y (set above); +14 clears the wire + twist amp,
            # +92 leaves room for the four stacked footer lines (attribution +
            # wiring + joints + bodies). Floored at 356 so ordinary
            # under-chassis layouts keep their footer clear.
            needed = self.ey(deep_row) + 14 + 92 - (self.board_y + self.board_h)
            self.margin_bot = max(356, int(math.ceil(needed)))
        else:
            self.margin_bot = MARGIN_BOT
        self.height = self.board_y + self.board_h + self.margin_bot

    # ---- coordinates --------------------------------------------------------
    def ex(self, col):
        return self.board_x + PAD_X + col * CW

    def ey(self, row):
        top = self.board_y + 44
        return top + row * ROWGAP

    def bom_for(self, ref):
        rec = self.bom.get(ref)
        if rec is None:
            self.errors.append(f"ref '{ref}' absent from bom.yaml")
            return {"value": "?", "part": ""}
        return rec

    # ---- endpoint resolution (wiring layer) --------------------------------
    def _assign_xfmr_leads(self):
        """Scan runs+bus for '<xfmr>.<colour>' endpoints and give each colour a
        stacked slot on that transformer, in first-seen order (deterministic)."""
        self.xfmr_leads: dict[str, list[str]] = {}
        for spec in (list(self.runs) + list(self.bus)):
            for key in ("from", "to"):
                ep = spec.get(key)
                if not isinstance(ep, str) or "." not in ep:
                    continue
                name, suffix = ep.split(".", 1)
                it = self.off_by_id.get(name)
                if it and it.get("kind") in ("xfmr", "choke"):
                    slots = self.xfmr_leads.setdefault(name, [])
                    if suffix not in slots:
                        slots.append(suffix)

    def tube_pin_pos(self, item, pin):
        x, y = self.off_pos(item)
        n = int(item.get("_pincount") or 8)
        step = 360.0 / (n + 1)
        theta = math.radians(180 + step * pin)      # clockwise from top; gap at bottom
        return x + TUBE_R * math.sin(theta), y - TUBE_R * math.cos(theta)

    def pot_lug_pos(self, item, lug):
        cx, cy = self.off_pos(item)
        r = 18
        # lugs sit on the board-facing side of the pot; 1/2/3 left→right
        edge = item.get("edge", "top")
        if edge == "bottom":
            return cx + (lug - 2) * 11, cy - r - 4
        if edge == "left":
            return cx + r + 4, cy + (lug - 2) * 11
        if edge == "right":
            return cx - r - 4, cy + (lug - 2) * 11
        return cx + (lug - 2) * 11, cy + r + 4          # top (board below)

    def part_terminal_pos(self, item, term):
        """The two terminals of a generic off-board 2-lead part (kind: part),
        placed on the board-facing side of the body so runs land cleanly. term
        is 'a' or 'b'; a is the first terminal (left / top), b the second."""
        cx, cy = self.off_pos(item)
        edge = item.get("edge", "top")
        s = -1 if term == "a" else 1
        if edge == "top":       # board below -> terminals below body
            return cx + s * 14, cy + 16
        if edge == "bottom":    # board above -> terminals above body
            return cx + s * 14, cy - 16
        if edge == "left":      # board right -> terminals to the right
            return cx + 16, cy + s * 14
        return cx - 16, cy + s * 14        # right: board left -> terminals left

    def xfmr_lead_pos(self, item, colour):
        cx, cy = self.off_pos(item)
        edge = item.get("edge", "left")
        w, h = (46, 56) if item.get("kind") == "xfmr" else (40, 34)
        slots = self.xfmr_leads.get(item["id"], [colour])
        if colour not in slots:
            slots = slots + [colour]
        idx = slots.index(colour)
        n = len(slots)
        # stack the pigtails along the board-facing edge, centred
        spread = min(h - 12, max(1, n - 1) * 14)
        off = (idx - (n - 1) / 2) * (spread / max(1, n - 1)) if n > 1 else 0
        stub = 16
        if edge == "left":     # board is to the right
            return cx + w / 2 + stub, cy + off, (cx + w / 2, cy + off)
        if edge == "right":    # board is to the left
            return cx - w / 2 - stub, cy + off, (cx - w / 2, cy + off)
        if edge == "top":
            return cx + off, cy + h / 2 + stub, (cx + off, cy + h / 2)
        return cx + off, cy - h / 2 - stub, (cx + off, cy - h / 2)   # bottom

    def resolve(self, ep, ctx=""):
        """Return (x, y) for an endpoint spec, appending to self.errors on a bad
        reference. Also records any coloured transformer pigtails drawn."""
        if isinstance(ep, (list, tuple)):
            if len(ep) == 2:
                return self.ex(ep[1]), self.ey(ep[0])
            self.errors.append(f"{ctx}: bad eyelet endpoint {ep!r}")
            return None
        if not isinstance(ep, str):
            self.errors.append(f"{ctx}: bad endpoint {ep!r}")
            return None
        if "." not in ep:
            it = self.off_by_id.get(ep)
            if it is None:
                self.errors.append(f"{ctx}: unknown endpoint '{ep}'")
                return None
            if it.get("kind") == "jack":
                return self.off_pos(it)
            return self.off_pos(it)
        name, suffix = ep.split(".", 1)
        # board part endpoint
        if name in self.part_by_ref:
            p = self.part_by_ref[name]
            if suffix not in ("a", "b"):
                self.errors.append(f"{ctx}: part '{name}' endpoint must be .a or .b, got '.{suffix}'")
                return None
            r, c = p[suffix]
            return self.ex(c), self.ey(r)
        it = self.off_by_id.get(name)
        if it is None:
            self.errors.append(f"{ctx}: unknown endpoint '{ep}'")
            return None
        kind = it.get("kind")
        if kind == "tube":
            digits = "".join(ch for ch in suffix if ch.isdigit())
            if not digits:
                self.errors.append(f"{ctx}: tube '{name}' pin '{suffix}' has no pin number")
                return None
            pin = int(digits)
            valid = it.get("_pins")
            if valid is not None and pin not in valid:
                self.errors.append(
                    f"{ctx}: tube '{name}' has no pin {pin} "
                    f"(valid: {sorted(valid)} per reference/tubes basing)")
                return None
            if valid is None and not (1 <= pin <= int(it.get("_pincount") or 8)):
                self.errors.append(f"{ctx}: tube '{name}' pin {pin} out of range")
                return None
            return self.tube_pin_pos(it, pin)
        if kind == "pot":
            digits = "".join(ch for ch in suffix if ch.isdigit())
            if digits not in ("1", "2", "3"):
                self.errors.append(f"{ctx}: pot '{name}' lug must be 1|2|3, got '{suffix}'")
                return None
            return self.pot_lug_pos(it, int(digits))
        if kind == "jack":
            cx, cy = self.off_pos(it)
            if suffix.lower() in ("tip",):
                return cx - 5, cy
            if suffix.lower() in ("sleeve", "ring"):
                return cx + 5, cy
            return cx, cy
        if kind in ("xfmr", "choke"):
            x, y, _ = self.xfmr_lead_pos(it, suffix)
            return x, y
        if kind == "part":
            if suffix not in ("a", "b"):
                self.errors.append(
                    f"{ctx}: off-board part '{name}' terminal must be .a or .b, got '.{suffix}'")
                return None
            return self.part_terminal_pos(it, suffix)
        self.errors.append(f"{ctx}: endpoint '{ep}' unsupported for kind '{kind}'")
        return None

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
        ndx, ndy = (part.get("nudge") or [0, 0])[:2]
        els = []
        # leads (short wires) drawn under the body
        els.append(f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
                   f'stroke="{LEAD}" stroke-width="2"/>')
        if vertical:
            cx = x1
            cy = (y1 + y2) / 2
            els += self._body_vertical(cat, cx, cy, val, ref, ndx, ndy)
        else:
            cx = (x1 + x2) / 2
            cy = y1
            span = abs(c2 - c1)
            els += self._body_horizontal(cat, cx, cy, span, val, ref, ndx, ndy)
        # eyelets on top of leads
        els.append(eyelet(x1, y1))
        els.append(eyelet(x2, y2))
        return "".join(els)

    def _label_pair(self, cx, top_y, bot_y, ref, val, ndx=0, ndy=0):
        return (text(cx + ndx, top_y + ndy, ref, BOARD_REF, 11.5, weight=700, spacing="0.02em")
                + text(cx + ndx, bot_y + ndy, val, BOARD_VAL, 11, font=FONT_MONO, weight=600))

    def _body_horizontal(self, cat, cx, cy, span, val, ref, ndx=0, ndy=0):
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
            els.append(self._label_pair(cx, y - 6, cy + 24, ref, val, ndx, ndy))
        elif cat == "mica":
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="4" fill="{MICA_BODY}" stroke="{MICA_EDGE}" stroke-width="1.2"/>')
            els.append(self._label_pair(cx, y - 6, cy + 20, ref, val, ndx, ndy))
        elif cat == "film":
            h = 22
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="10" fill="{FILM_BODY}" stroke="{FILM_EDGE}" stroke-width="1.2"/>')
            els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y+2)}" x2="{fmt(cx)}" y2="{fmt(y+h-2)}" '
                       f'stroke="{FILM_EDGE}" stroke-width="0.8" opacity="0.7"/>')
            els.append(self._label_pair(cx, y - 6, cy + 22, ref, val, ndx, ndy))
        else:  # resistor / other
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="7" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            for ex_ in (x + 5, x + w - 5):
                els.append(f'<line x1="{fmt(ex_)}" y1="{fmt(y+1)}" x2="{fmt(ex_)}" y2="{fmt(y+h-1)}" '
                           f'stroke="{RES_END}" stroke-width="2"/>')
            els.append(self._label_pair(cx, y - 6, cy + 21, ref, val, ndx, ndy))
        return els

    def _body_vertical(self, cat, cx, cy, val, ref, ndx=0, ndy=0):
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
        els.append(text(lx + ndx, cy - 3 + ndy, ref, BOARD_REF, 11.5, weight=700,
                        anchor=anchor, spacing="0.02em"))
        els.append(text(lx + ndx, cy + 11 + ndy, val, BOARD_VAL, 11, anchor=anchor,
                        font=FONT_MONO, weight=600))
        return els

    # ---- off-board stubs ----------------------------------------------------
    def off_pos(self, item):
        edge = item.get("edge", "bottom")
        at = float(item.get("at", 0))
        if edge in ("top", "bottom"):
            x = self.ex(at)
            y = (self.board_y - 84) if edge == "top" else (self.board_y + self.board_h + 80)
        elif edge == "left":
            x = self.board_x - 78
            y = self.ey(0) + at * ROWGAP
        else:  # right
            x = self.board_x + self.board_w + 78
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
            r = TUBE_R
            n = int(item.get("_pincount") or 8)
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{PANEL}" '
                       f'stroke="{AMBER}" stroke-width="1.8"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="6.5" fill="none" '
                       f'stroke="{FAINT}" stroke-width="1"/>')
            step = 360.0 / (n + 1)
            for pin in range(1, n + 1):
                theta = math.radians(180 + step * pin)
                px = x + r * math.sin(theta)
                py = y - r * math.cos(theta)
                els.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="2.1" fill="{MUTED}"/>')
                # pin number, just inside the ring
                nx = x + (r - 8.5) * math.sin(theta)
                ny = y - (r - 8.5) * math.cos(theta)
                els.append(text(nx, ny + 3, str(pin), FAINT, 7.5, font=FONT_MONO, weight=600))
            els.append(text(x, y + r + 15, label, INK, 12, spacing="0.05em"))
        elif kind == "pot":
            r = 18
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{PANEL}" '
                       f'stroke="{MUTED}" stroke-width="1.6"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{MUTED}"/>')
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(x)}" y2="{fmt(y-r+3)}" '
                       f'stroke="{AMBER}" stroke-width="2"/>')
            # three lug pips on the board-facing side
            for lug in (1, 2, 3):
                lx, ly = self.pot_lug_pos(item, lug)
                els.append(f'<circle cx="{fmt(lx)}" cy="{fmt(ly)}" r="1.9" fill="{MUTED}"/>')
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
            # coloured pigtails for each lead colour wired to this transformer
            for colour in self.xfmr_leads.get(item.get("id"), []):
                ex_, ey_, base = self.xfmr_lead_pos(item, colour)
                wc = colour_hex(lead_base(colour))
                els.append(f'<line x1="{fmt(base[0])}" y1="{fmt(base[1])}" x2="{fmt(ex_)}" '
                           f'y2="{fmt(ey_)}" stroke="{wc}" stroke-width="2.6" '
                           f'stroke-linecap="round"/>')
                els.append(term_dot(ex_, ey_, 2.4))
            els.append(text(x, y + h / 2 + 14, label, INK, 11.5, spacing="0.04em"))
            if val:
                els.append(text(x, y + h / 2 + 27, val, MUTED, 10.5, font=FONT_MONO, weight=500))
        elif kind == "part":
            els += self._part_glyph(item, x, y, label, val)
        else:  # switch / fuse / misc
            w, h = 34, 18
            els.append(f'<rect x="{fmt(x-w/2)}" y="{fmt(y-h/2)}" width="{w}" height="{h}" rx="4" '
                       f'fill="{PANEL}" stroke="{LINE}" stroke-width="1.4"/>')
            els.append(text(x, y + h / 2 + 13, label, MUTED, 10.5, spacing="0.03em"))
        return "".join(els)

    def _part_glyph(self, item, x, y, label, val):
        """Generic off-board 2-lead part (kind: part): a pilot lamp (glyph:
        lamp) or a small axial body, with two board-facing terminals wired as
        REF.a / REF.b."""
        edge = item.get("edge", "top")
        away = {"top": (0, -1), "bottom": (0, 1),
                "left": (-1, 0), "right": (1, 0)}.get(edge, (0, -1))
        ta = self.part_terminal_pos(item, "a")
        tb = self.part_terminal_pos(item, "b")
        els = []
        if item.get("glyph") == "lamp":
            # base sits just off the terminals; bulb (jewel) sits further away
            cbx, cby = x + away[0] * 2, y + away[1] * 2       # bayonet base centre
            bx, by = x + away[0] * 15, y + away[1] * 15       # bulb centre
            for (tx, ty) in (ta, tb):
                els.append(f'<line x1="{fmt(tx)}" y1="{fmt(ty)}" x2="{fmt(cbx)}" '
                           f'y2="{fmt(cby)}" stroke="{LEAD}" stroke-width="2"/>')
            els.append(f'<rect x="{fmt(cbx-8)}" y="{fmt(cby-6)}" width="16" height="12" '
                       f'rx="2" fill="{LAMP_BASE}" stroke="{LAMP_BASE_EDGE}" stroke-width="1"/>')
            # bayonet pin hints on the base flanks
            els.append(f'<circle cx="{fmt(cbx-8)}" cy="{fmt(cby)}" r="1.7" fill="{LAMP_BASE_EDGE}"/>')
            els.append(f'<circle cx="{fmt(cbx+8)}" cy="{fmt(cby)}" r="1.7" fill="{LAMP_BASE_EDGE}"/>')
            els.append(f'<circle cx="{fmt(bx)}" cy="{fmt(by)}" r="9.5" fill="{LAMP_GLASS}" '
                       f'stroke="{LAMP_GLASS_EDGE}" stroke-width="1.4"/>')
            els.append(f'<circle cx="{fmt(bx-2.6)}" cy="{fmt(by-2.6)}" r="2.4" fill="{INK}" '
                       f'opacity="0.5"/>')
            # filament squiggle inside the jewel
            els.append(f'<path d="M {fmt(bx-3.5)} {fmt(by+1.5)} q 1.8 -5 3.5 0 q 1.8 5 3.5 0" '
                       f'fill="none" stroke="{LAMP_GLASS_EDGE}" stroke-width="0.9"/>')
            laby = by - 15 if away[1] < 0 else by + 24
            els.append(text(bx, laby, label, INK, 11.5, spacing="0.04em"))
            for (tx, ty) in (ta, tb):
                els.append(term_dot(tx, ty, 2.2))
            return els
        # generic axial 2-lead body drawn between the terminals
        horiz = edge in ("top", "bottom")
        midx, midy = (ta[0] + tb[0]) / 2, (ta[1] + tb[1]) / 2
        els.append(f'<line x1="{fmt(ta[0])}" y1="{fmt(ta[1])}" x2="{fmt(tb[0])}" '
                   f'y2="{fmt(tb[1])}" stroke="{LEAD}" stroke-width="2"/>')
        if horiz:
            bw = max(22.0, abs(tb[0] - ta[0]) - 8)
            bh = 15.0
            rx, ry = midx - bw / 2, midy - bh / 2
            els.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(bw)}" height="{fmt(bh)}" '
                       f'rx="6" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            for ex_ in (rx + 5, rx + bw - 5):
                els.append(f'<line x1="{fmt(ex_)}" y1="{fmt(ry+1)}" x2="{fmt(ex_)}" '
                           f'y2="{fmt(ry+bh-1)}" stroke="{RES_END}" stroke-width="2"/>')
            top = away[1] < 0
            ref_y = (ry - 18) if top else (ry + bh + 24)
            val_y = (ry - 5) if top else (ry + bh + 11)
            els.append(text(midx, ref_y, label, INK, 11.5, weight=700, spacing="0.02em"))
            if val:
                els.append(text(midx, val_y, val, MUTED, 10.5, font=FONT_MONO, weight=500))
        else:
            bw, bh = 15.0, max(22.0, abs(tb[1] - ta[1]) - 8)
            rx, ry = midx - bw / 2, midy - bh / 2
            els.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(bw)}" height="{fmt(bh)}" '
                       f'rx="6" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            lx = midx + away[0] * 16
            anchor = "end" if away[0] < 0 else "start"
            els.append(text(lx, midy - 3, label, INK, 11.5, weight=700, anchor=anchor,
                            spacing="0.02em"))
            if val:
                els.append(text(lx, midy + 11, val, MUTED, 10.5, anchor=anchor,
                                font=FONT_MONO, weight=500))
        for (tx, ty) in (ta, tb):
            els.append(term_dot(tx, ty, 2.2))
        return els

    # ---- legacy soft leads (kept for back-compat) --------------------------
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

    # ---- v2 wiring: routed runs + ground bus -------------------------------
    def _run_points(self, spec, ctx):
        a = self.resolve(spec.get("from"), ctx + " from")
        b = self.resolve(spec.get("to"), ctx + " to")
        if not a or not b:
            return None
        pts = [a]
        for v in (spec.get("via") or []):
            if isinstance(v, (list, tuple)) and len(v) == 2:
                pts.append((self.ex(v[0]), self.ey(v[1])))   # via is [x=col, y=row]
            else:
                self.errors.append(f"{ctx}: bad via point {v!r}")
        pts.append(b)
        return pts

    def _endpoint_colour(self, ep):
        """Base colour name if `ep` addresses a transformer lead, else None."""
        if isinstance(ep, str) and "." in ep:
            name, suffix = ep.split(".", 1)
            it = self.off_by_id.get(name)
            if it and it.get("kind") in ("xfmr", "choke"):
                return lead_base(suffix)
        return None

    def _check_heater_endpoint(self, ep, ctx):
        """A style:twisted (heater) run onto a tube socket must land on a
        heater/filament pin — validated against reference/tubes basing."""
        if not (isinstance(ep, str) and "." in ep):
            return
        name, suffix = ep.split(".", 1)
        it = self.off_by_id.get(name)
        if not (it and it.get("kind") == "tube"):
            return
        digits = "".join(ch for ch in suffix if ch.isdigit())
        if not digits:
            return
        pin = int(digits)
        heaters = it.get("_heater_pins")
        if heaters is not None and pin not in heaters:
            self.errors.append(
                f"{ctx}: heater (twisted) run onto tube '{name}' pin {pin} is not a "
                f"heater/filament pin (heater pins: {sorted(heaters)} per reference/tubes basing)")

    def run_wire(self, spec, i, pts, seg_hops=None):
        if not pts:
            return "", []
        seg_hops = seg_hops or {}
        twisted = str(spec.get("style", "")).lower() == "twisted"
        colour = spec.get("color")
        if not colour:
            colour = self._endpoint_colour(spec.get("from")) or self._endpoint_colour(spec.get("to"))
        if twisted:
            # heater pair: validate endpoints, default to the heater green, and
            # earn a dedicated legend entry instead of a colour swatch.
            self._check_heater_endpoint(spec.get("from"), f"run[{i}] from")
            self._check_heater_endpoint(spec.get("to"), f"run[{i}] to")
            self._has_twisted = True
            base = lead_base(colour) if colour else None
            stroke = HEATER_CT if base == "green-yellow" else HEATER
            d1, d2 = twisted_strands(pts)
            center = rounded_path(pts, r=11)
            casing = (f'<path d="{center}" fill="none" stroke="{WIRE_CASING}" '
                      f'stroke-width="5.0" stroke-linecap="round" stroke-linejoin="round" '
                      f'opacity="0.6"/>')
            strands = (f'<path d="{d1}" fill="none" stroke="{stroke}" stroke-width="1.7" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>'
                       f'<path d="{d2}" fill="none" stroke="{stroke}" stroke-width="1.7" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
            return casing + strands, [pts[0], pts[-1]]
        stroke = colour_hex(colour) if colour else WIRE_NEUTRAL
        if colour:
            key = str(colour).lower()
            if key not in self._colours_used:
                self._colours_used.append(key)
        d = hopped_path(pts, seg_hops, r=11)
        casing = (f'<path d="{d}" fill="none" stroke="{WIRE_CASING}" stroke-width="4.8" '
                  f'stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>')
        wire = (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="2.3" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        return casing + wire, [pts[0], pts[-1]]

    def bus_wire(self, spec, i, pts):
        if not pts:
            return "", []
        d = rounded_path(pts, r=9)
        edge = (f'<path d="{d}" fill="none" stroke="{BUS_EDGE}" stroke-width="6.4" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        core = (f'<path d="{d}" fill="none" stroke="{BUS_CORE}" stroke-width="3.4" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        return edge + core, [pts[0], pts[-1]]

    # ---- resolved wiring geometry (shared by render + lint) -----------------
    def build_geometry(self):
        """Resolve every run and bus segment-set to its pixel polyline. Returns
        (runs, bus) where each run is {i, spec, pts, twisted} and each bus entry
        is {j, spec, pts}. `pts` is None when an endpoint fails to resolve."""
        runs = []
        for i, spec in enumerate(self.runs):
            pts = self._run_points(spec, f"run[{i}]")
            runs.append({"i": i, "spec": spec, "pts": pts,
                         "twisted": str(spec.get("style", "")).lower() == "twisted"})
        bus = []
        for j, spec in enumerate(self.bus):
            bus.append({"j": j, "spec": spec, "pts": self._run_points(spec, f"bus[{j}]")})
        return runs, bus

    def _hop_map(self, runs, bus):
        """Build the hop map for the plain runs + bus (twisted runs excluded)."""
        wires = []
        for b in bus:
            if b["pts"]:
                wires.append({"key": ("bus", b["j"]), "order": -1,
                              "points": b["pts"], "is_bus": True})
        for r in runs:
            if r["pts"] and not r["twisted"]:
                wires.append({"key": ("run", r["i"]), "order": r["i"],
                              "points": r["pts"], "is_bus": False})
        return compute_hops(wires)

    # ---- assemble -----------------------------------------------------------
    def render(self) -> str:
        els = []
        term_pts: list[tuple[float, float]] = []
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
        # legacy soft leads (under everything)
        for lead in self.leads:
            els.append(self.lead_run(lead))
        # resolve wiring geometry once, then work out the hop-over bridges: at
        # every transversal crossing the later run hops the earlier one; runs
        # hop the ground bus; twisted heater pairs are exempt (topmost layer).
        runs, bus = self.build_geometry()
        hops = self._hop_map(runs, bus)
        bus_pts: list[tuple[float, float]] = []       # ground-rod ends (small dot)
        run_pts: list[tuple[float, float]] = []       # run endpoints (solder blob)
        # ground bus (under the coloured runs — it is the reference rail)
        for b in bus:
            svg, tp = self.bus_wire(b["spec"], b["j"], b["pts"])
            els.append(svg)
            bus_pts += tp
        # routed hookup runs (twisted heater pairs are deferred below the part
        # loops — they must draw ABOVE the socket discs so the pin landing on
        # the 9-pin top heater pins stays visible instead of vanishing under
        # the socket)
        twisted_runs = []
        for r in runs:
            if r["twisted"]:
                twisted_runs.append(r)
                continue
            svg, tp = self.run_wire(r["spec"], r["i"], r["pts"],
                                    hops.get(("run", r["i"]), {}))
            els.append(svg)
            run_pts += tp
        # off-board stubs
        for it in self.offboard:
            els.append(self.off_stub(it))
        # board parts
        for p in self.parts:
            els.append(self.part_body(p))
        # heater twisted pairs, above the sockets
        for r in twisted_runs:
            svg, tp = self.run_wire(r["spec"], r["i"], r["pts"])
            els.append(svg)
            run_pts += tp
        # ground-rod ends: a plain terminal dot
        for (tx, ty) in bus_pts:
            els.append(term_dot(tx, ty))
        # run endpoints: a solder blob (deduped by rounded position so shared
        # nodes don't stack) — where a wire LANDS is never in doubt
        seen: set = set()
        for (tx, ty) in run_pts:
            key = (round(tx, 1), round(ty, 1))
            if key in seen:
                continue
            seen.add(key)
            els.append(solder_blob(tx, ty))
        # title + attribution
        title = (self.layout.get("board", {}) or {}).get("title") or f"{self.amp_id.upper()} board layout"
        els.append(text(bx, 34, title, INK, 17, anchor="start", spacing="0.08em"))
        src = self.layout.get("source", {}) or {}
        if src.get("desc"):
            attrib = f"Redrawn from {src['desc']} — not a trace"
        else:
            attrib = self.layout.get("caption") or ""
        if attrib:
            els.append(text(bx, self.height - 74, attrib, FAINT, 10.5, anchor="start",
                            font=FONT_MONO, weight=500))
        # legends
        self._legend(els)
        body = "\n".join(els)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(self.width)} '
               f'{fmt(self.height)}" role="img" aria-label="{esc(title)} — redrawn board '
               f'layout diagram" width="100%" font-family="{FONT_DISP}">\n'
               f'<rect x="0" y="0" width="{fmt(self.width)}" height="{fmt(self.height)}" '
               f'fill="{WELL}"/>\n{body}\n</svg>\n')
        if self.errors:
            raise ValueError(f"{self.amp_id}: layout errors: {self.errors}")
        return svg

    def _legend(self, els):
        # wiring legend (only when the layout has a wiring layer)
        y = self.height - 56
        x = self.board_x
        if self.runs or self.bus:
            cx = x
            els.append(text(cx, y, "Wiring:", FAINT, 10.5, anchor="start", font=FONT_MONO,
                            weight=500))
            cx += 58
            # neutral lead sample
            els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y-3)}" x2="{fmt(cx+18)}" y2="{fmt(y-3)}" '
                       f'stroke="{WIRE_NEUTRAL}" stroke-width="2.4" stroke-linecap="round"/>')
            els.append(text(cx + 24, y, "lead", MUTED, 10.5, anchor="start", font=FONT_MONO,
                            weight=500))
            cx += 24 + 4 * 6.4 + 16
            for key in self._colours_used:
                col = WIRE.get(key, WIRE_NEUTRAL)
                els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y-3)}" x2="{fmt(cx+18)}" y2="{fmt(y-3)}" '
                           f'stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>')
                els.append(text(cx + 24, y, key, MUTED, 10.5, anchor="start", font=FONT_MONO,
                                weight=500))
                cx += 24 + len(key) * 6.4 + 16
            if self.bus:
                els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y-3)}" x2="{fmt(cx+18)}" y2="{fmt(y-3)}" '
                           f'stroke="{BUS_CORE}" stroke-width="3.4" stroke-linecap="round"/>')
                els.append(text(cx + 24, y, "ground bus", MUTED, 10.5, anchor="start",
                                font=FONT_MONO, weight=500))
                cx += 24 + len("ground bus") * 6.4 + 16
            if self._has_twisted:
                # a small twisted-pair swatch, then the heater label
                d1, d2 = twisted_strands([(cx, y - 3), (cx + 20, y - 3)], amp=2.6, wavelen=8.0)
                els.append(f'<path d="{d1}" fill="none" stroke="{HEATER}" stroke-width="1.5" '
                           f'stroke-linecap="round"/>')
                els.append(f'<path d="{d2}" fill="none" stroke="{HEATER}" stroke-width="1.5" '
                           f'stroke-linecap="round"/>')
                els.append(text(cx + 26, y, "6.3 V heaters — twisted pair", MUTED, 10.5,
                                anchor="start", font=FONT_MONO, weight=500))
            # joints legend: a solder blob (wire end) + a hop-over (cross-over)
            jy = self.height - 38
            els.append(text(x, jy, "Joints:", FAINT, 10.5, anchor="start", font=FONT_MONO,
                            weight=500))
            jx = x + 58
            els.append(solder_blob(jx + 4, jy - 3))
            els.append(text(jx + 13, jy, "wire end (solder joint)", MUTED, 10.5,
                            anchor="start", font=FONT_MONO, weight=500))
            jx += 13 + len("wire end (solder joint)") * 6.4 + 20
            # a short lead with a hop bump, then the label
            hd = hopped_path([(jx, jy - 3), (jx + 34, jy - 3)], {0: [(17.0, HOP_R)]}, r=11)
            els.append(f'<path d="{hd}" fill="none" stroke="{WIRE_NEUTRAL}" stroke-width="2.3" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
            els.append(text(jx + 40, jy, "cross-over (no connect)", MUTED, 10.5,
                            anchor="start", font=FONT_MONO, weight=500))
        # bodies legend
        items = [(RES_BODY, "resistor"), (FILM_BODY, "film / coupling cap"),
                 (ELEC_BODY, "electrolytic"), (MICA_BODY, "mica")]
        y = self.height - 20
        els.append(text(x, y, "Bodies:", FAINT, 10.5, anchor="start", font=FONT_MONO, weight=500))
        cx = x + 58
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


# ---- collision lint (CI gate, see pipeline/check_layouts.py) ----------------
LINT_ANGLE = 10.0      # (a) near-parallel: acute angle below this counts
LINT_SEP = 2.4         # (a) two runs closer than this read as one wire
LINT_OVERLAP = 8.0     # (a) shared near-parallel length that trips the lint
LINT_TERM = 5.0        # (b) a run end this close to another run's interior…
LINT_VERTEX_CLEAR = 4.0  # …unless it sits on one of that run's own nodes


def _parallel_overlap(a1, a2, b1, b2, sep):
    """Longest contiguous stretch of segment a1-a2 that runs within `sep` of
    segment b1-b2, sampled at 1 px. Returns (length, midpoint) or None."""
    L = _seg_len(a1, a2)
    if L < 1e-6:
        return None
    ux, uy = _seg_unit(a1, a2)
    hits = []
    k = 0
    while True:
        d = min(k * 1.0, L)
        p = (a1[0] + ux * d, a1[1] + uy * d)
        hits.append((d, _point_seg_dist(p, b1, b2) < sep))
        if d >= L:
            break
        k += 1
    best_len, best_mid = 0.0, None
    i = 0
    while i < len(hits):
        if hits[i][1]:
            j = i
            while j < len(hits) and hits[j][1]:
                j += 1
            span = hits[j - 1][0] - hits[i][0]
            if span > best_len:
                best_len = span
                md = (hits[i][0] + hits[j - 1][0]) / 2
                best_mid = (a1[0] + ux * md, a1[1] + uy * md)
            i = j
        else:
            i += 1
    return (best_len, best_mid) if best_mid is not None else None


def lint_layout(amp_dir: Path) -> list[str]:
    """Collision lint for the wiring layer — the checks CI runs so the drawing
    is never ambiguous about crossings or terminations. Both run over the plain
    (non-twisted) runs; twisted heater pairs and the ground bus are exempt:

      (a) near-parallel overlap — segments from two different runs at an acute
          angle < 10 deg with separation < 2.4 px over > 8 px of shared length
          (they read as a single wire);
      (b) terminal ambiguity — a run endpoint within 5 px of ANOTHER run's
          polyline interior while not sitting on any of that run's own nodes
          (it's unclear whether the wire lands there or merely passes by).

    Returns a sorted list of failure strings with coordinates + run indices.
    """
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    runs, _bus = Renderer(layout, bom, amp_dir.name).build_geometry()
    plain = [r for r in runs if r["pts"] and not r["twisted"]]
    fails: list[str] = []
    # (a) near-parallel overlap
    for ai in range(len(plain)):
        for bi in range(ai + 1, len(plain)):
            A, B = plain[ai], plain[bi]
            pa, pb = A["pts"], B["pts"]
            for sa in range(len(pa) - 1):
                for sb in range(len(pb) - 1):
                    a1, a2, b1, b2 = pa[sa], pa[sa + 1], pb[sb], pb[sb + 1]
                    if _seg_angle_deg(a1, a2, b1, b2) >= LINT_ANGLE:
                        continue
                    ov = _parallel_overlap(a1, a2, b1, b2, LINT_SEP)
                    if ov and ov[0] > LINT_OVERLAP:
                        length, mid = ov
                        fails.append(
                            f"{amp_dir.name}: near-parallel overlap run[{A['i']}] & "
                            f"run[{B['i']}] ~{length:.1f}px within {LINT_SEP}px near "
                            f"({mid[0]:.0f},{mid[1]:.0f})")
    # (b) terminal ambiguity
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
                        fails.append(
                            f"{amp_dir.name}: terminal ambiguity run[{A['i']}] endpoint "
                            f"({E[0]:.0f},{E[1]:.0f}) within {LINT_TERM}px of run[{B['i']}] "
                            f"interior")
                        break
    return sorted(fails)


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


# ---- --png debug mode ------------------------------------------------------
def ensure_rsvg() -> str | None:
    exe = shutil.which("rsvg-convert")
    if exe:
        return exe
    brew = shutil.which("brew")
    if not brew:
        print("rsvg-convert not found and Homebrew is unavailable; "
              "install librsvg to use --png", file=sys.stderr)
        return None
    print("rsvg-convert not found — installing librsvg via Homebrew…", file=sys.stderr)
    subprocess.run([brew, "install", "librsvg"], check=False)
    return shutil.which("rsvg-convert")


def render_png(ids: list[str], width: int = 1600) -> list[Path]:
    """Convert amps/<id>/layout.svg -> /tmp/<id>.png for a visual self-review.
    With no ids, converts every amp that has a layout."""
    exe = ensure_rsvg()
    if not exe:
        return []
    if not ids:
        ids = [p.parent.name for p in sorted((ROOT / "amps").glob("*/layout.yaml"))]
    out_paths = []
    for amp_id in ids:
        svg = ROOT / "amps" / amp_id / "layout.svg"
        if not svg.exists():
            print(f"no layout.svg for {amp_id}", file=sys.stderr)
            continue
        png = Path("/tmp") / f"{amp_id}.png"
        subprocess.run([exe, "-w", str(width), str(svg), "-o", str(png)], check=True)
        print(f"png {png}")
        out_paths.append(png)
    return out_paths


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--png" in args:
        args.remove("--png")
        # ensure SVGs are current before converting
        render_all(write=True)
        render_png(args)
    else:
        render_all(write=True)
        if not list((ROOT / "amps").glob("*/layout.yaml")):
            print("no layout.yaml files found", file=sys.stderr)
