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
parts:            [ { ref, a:[row,col], b:[row,col], nudge?:[dx,dy],
                      value_nudge?:[dx,dy] } ]
                    Board-mounted parts. `ref` keys into bom.yaml (value + type).
                    Same row -> axial body; shared column -> vertical leg.
                    Optional `nudge` shifts the ref/value label pair (px);
                    `value_nudge` shifts the VALUE alone, to slide a value out
                    from under a supply lead while its ref stays put. Both keep
                    the drawing clear of wiring.
offboard:         [ { id, ref?, kind, edge, at, label, glyph?,
                      label_nudge?:[dx,dy], value_nudge?:[dx,dy] } ]
                    kind: tube | pot | jack | xfmr | choke | switch | part
                    On a pot, `label_nudge` shifts the name+value pair and
                    `value_nudge` the value alone (px), keeping the halo — the
                    escape hatch for a value still sitting under a lug-lead run.
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

--- wire_legend: colour-swatch overrides ---------------------------------------
wire_legend:  { <colour name>: "<legend entry>" }

  Replaces a colour's bare swatch label in the drawing's wiring legend. Use it
  where a colour carries a documented FUNCTION in that drawing which the
  automatic legend cannot infer — e.g. the AA764's 6.3 V heater supply is
  single-ended (one green PT lead grounded, the other feeding pilot lamp and
  both heaters) and so renders as plain green runs, earning no "6.3 V heaters —
  twisted pair" entry. The SVG is served standalone, so it must say what green
  means on its own.

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
import re
import shutil
import subprocess
import sys
from decimal import Decimal, InvalidOperation
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
DIODE_BODY, DIODE_EDGE = "#3f4a52", "#1d2429"  # bias rectifier / silicon diode
DIODE_BAND = "#e7dcc2"                         # cathode band
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
# Board margin above the top eyelet row. A tall filter can (42 px) hangs above
# its row and prints its ref above that again, so the board needs enough tan
# above row 0 for the ref to sit ON the board rather than overhanging into the
# dark well, where dark board ink has nothing to read against.
BOARD_TOP_PAD = 56
# Headroom the canvas reserves above the highest wiring lane routed above the
# board, and the extra gap it reserves where that lane passes under the drawing
# title — see Renderer._top_lane_y().
TOP_LANE_CLEAR = 16
TITLE_LANE_CLEAR = 14
MARGIN_L, MARGIN_R = 128, 128
MARGIN_TOP, MARGIN_BOT = 150, 236
# Page-chrome type scale. A board's px geometry is fixed (CW/ROWGAP), so sheet
# width tracks column count — 1000 px for the 5F1, 2440 px for the 5F10 — at a
# near-constant height. Every one of these is read scaled to a common page
# width, so chrome type set at a fixed px size renders at wildly different ink
# heights across the corpus. Chrome sizes are therefore multiplied by
# width/CHROME_REF_W (clamped), which holds their rendered height constant.
CHROME_REF_W = 1450.0
FOOTER_BASE = 20.0       # baseline of the bottom footer row, above the edge
FOOTER_PITCH = 18.0      # footer row pitch (both scaled by self.cs)
BODY_TOP_INSET = 0
TUBE_R = 26        # tube socket radius (px)

FONT_DISP = "'Avenir Next Condensed','Arial Narrow','Helvetica Neue',Arial,sans-serif"
FONT_MONO = "'SF Mono',Menlo,Consolas,monospace"


def fmt(n: float) -> str:
    return f"{n:.1f}".rstrip("0").rstrip(".")


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


_RE_CAT_RES = re.compile(r"\bresistors?\b")


def category(part: str) -> str:
    p = (part or "").lower()
    if "electrolytic" in p:
        return "electro"
    if "mica" in p:
        return "mica"
    if "capacitor" in p or "cap" in p:
        return "film"
    # A bias-supply rectifier is a POLARISED two-lead part, not a resistor. It
    # had been falling through to the generic body, which drew it as a dogbone
    # — a builder could not tell it from the resistor beside it, and nothing on
    # the drawing said which way round it goes. "Rectifier tube" is a valve and
    # is excluded here (it matches the tube branch below).
    if "diode" in p or ("rectifier" in p and "tube" not in p):
        return "diode"
    # WORD boundary, not substring: "Lamp + photoresistor pair" is the 6G5's
    # tremolo optocoupler, and matching "resistor" inside "photoresistor" filed
    # it as a carbon-comp resistor. The consistency gate then demanded an ohms
    # value from a part whose value is the words "tremolo optocoupler", and the
    # drawing gave it a resistor dogbone — a builder cannot buy that part.
    if _RE_CAT_RES.search(p):
        return "res"
    if "transformer" in p:
        return "xfmr"
    if "choke" in p:
        return "choke"
    if "tube" in p:
        return "tube"
    return "other"


def annotation_value(item: dict) -> str | None:
    """Value for an off-board item that carries NO bom.yaml ref.

    Values normally live only in bom.yaml, keyed by ref, so a layout and the
    parts list can never disagree — and that stays true for every part the BOM
    knows. But the annotation layer draws parts the electrical model does not
    carry (a negative-feedback resistor whose schematic states it only as a
    text note, so it has no schematic symbol and therefore no BOM ref). Those
    had no way to state a value at all and rendered as an unnamed blank body.
    An `value:` on a REF-LESS offboard item is the only place such a figure can
    live; a ref'd item ignores it, so the two can never diverge."""
    v = item.get("value")
    return str(v).strip() if v not in (None, "") else None


def primary_value(value: str) -> str:
    """First '·'-separated token of a BOM value string ('16 µF · 450 V' -> '16 µF')."""
    return str(value).split("·")[0].strip()


_IRON_CACHE: dict[str, dict] = {}


def load_iron(amp_id: str) -> dict:
    """meta.yaml `iron:` — {designator: electrical rating}, for the iron whose
    parts-list value is a bare factory part number.

    "Fender 45216" identifies a transformer to a collector and tells a builder
    nothing: it does not say what impedance to wind, buy or substitute. Where
    this corpus has READ the rating from a published source it belongs on the
    drawing beside the number, and this is where it lives — one place, keyed by
    designator, so the drawing and the parts list cannot drift apart. An amp
    with no `iron:` block letters the part number alone: the corpus states what
    it has read and no more."""
    if amp_id in _IRON_CACHE:
        return _IRON_CACHE[amp_id]
    path = ROOT / "amps" / amp_id / "meta.yaml"
    out: dict = {}
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception:  # noqa: BLE001 — a malformed meta.yaml is validate.py's finding
            data = {}
        for k, v in (data.get("iron") or {}).items():
            if str(v).strip():
                out[str(k)] = str(v).strip()
    _IRON_CACHE[amp_id] = out
    return out


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
         spacing=None, upper=False, halo=None, halo_width=3.0):
    """A single <text> element. `halo` (an opaque colour) draws a thin stroked
    outline BEHIND the glyph fill (paint-order="stroke") so the label stays
    legible where a wire lead crosses behind it — a dense-board label sitting
    over converging leads (pot lug fans, tube-socket ID text under a crossing
    heater pair) reads clearly instead of merging with the wire. Deterministic:
    a fixed stroke, no shadow/blur."""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    halo_attr = (f' stroke="{halo}" stroke-width="{fmt(halo_width)}" '
                 f'stroke-linejoin="round" paint-order="stroke"') if halo else ""
    return (f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{fill}" font-size="{size}" '
            f'font-family="{font}" font-weight="{weight}" text-anchor="{anchor}"{ls}'
            f'{halo_attr}>'
            f'{esc(s)}</text>')


# ---- text metrics (label boxes feed the label-collision lint) --------------
# Average advance width per em for the two house faces: the display face is a
# CONDENSED sans (Avenir Next Condensed / Arial Narrow), the value face a
# monospace. These are estimates — deliberately a shade generous, so a box is
# never narrower than the glyphs it stands for.
ADV_DISP, ADV_MONO = 0.53, 0.61
CAP_RISE, DESCEND = 0.74, 0.22      # cap height / descender, as a fraction of em


def text_width(s, size, font=FONT_DISP, spacing=None):
    """Estimated advance width of a text() run, letter-spacing included."""
    extra = 0.0
    if spacing:
        try:
            extra = float(str(spacing).replace("em", "")) * size
        except ValueError:
            extra = 0.0
    adv = ADV_MONO if font == FONT_MONO else ADV_DISP
    return len(str(s)) * (size * adv + extra)


def text_box(x, y, s, size, *, anchor="middle", font=FONT_DISP, spacing=None):
    """Axis-aligned bounding box (x0, y0, x1, y1) of a text() element, from its
    anchor point and estimated metrics. Used by the label-collision lint."""
    w = text_width(s, size, font, spacing)
    if anchor == "start":
        x0 = x
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x - w / 2
    return (x0, y - CAP_RISE * size, x0 + w, y + DESCEND * size)


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


def _shrink(box, inset):
    """Box shrunk by `inset` on every side (never inverted)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (min(x0 + inset, cx), min(y0 + inset, cy),
            max(x1 - inset, cx), max(y1 - inset, cy))


def _box_overlap(a, b):
    """(width, height) of the intersection of two boxes; (0, 0) when disjoint."""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return (max(0.0, w), max(0.0, h))


def _seg_hits_box(p, q, box):
    """True when segment p-q intersects the axis-aligned `box` (interior or
    edge). Liang–Barsky clip — exact, no sampling."""
    x0, y0, x1, y1 = box
    px, py = p
    dx, dy = q[0] - px, q[1] - py
    t0, t1 = 0.0, 1.0
    for pv, qv in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
        if abs(pv) < 1e-12:
            if qv < 0:
                return False
            continue
        r = qv / pv
        if pv < 0:
            if r > t1:
                return False
            t0 = max(t0, r)
        else:
            if r < t0:
                return False
            t1 = min(t1, r)
    return t0 <= t1


def _seg_box_span(p, q, box):
    """Length of the part of segment p-q that lies inside `box` (0 when it
    misses). The lint uses this so a wire merely clipping a box corner is not
    treated the same as one driven straight through the type."""
    x0, y0, x1, y1 = box
    px, py = p
    dx, dy = q[0] - px, q[1] - py
    t0, t1 = 0.0, 1.0
    for pv, qv in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
        if abs(pv) < 1e-12:
            if qv < 0:
                return 0.0
            continue
        r = qv / pv
        if pv < 0:
            if r > t1:
                return 0.0
            t0 = max(t0, r)
        else:
            if r < t0:
                return 0.0
            t1 = min(t1, r)
    if t1 <= t0:
        return 0.0
    return (t1 - t0) * math.hypot(dx, dy)


def _clean_polyline(pts, eps=1.5):
    """Drop coincident points and collapse degenerate out-and-back spurs.

    A run whose waypoint list doubles back on itself renders as a hairpin with
    no terminus — the reviewer's word for it was 'a drafting artefact', and it
    is: a line that goes somewhere, comes to a point and returns says nothing
    about the circuit. Collapsing them here means no drawing can carry one."""
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    changed = True
    while changed and len(out) >= 3:
        changed = False
        for i in range(1, len(out) - 1):
            a, b, c = out[i - 1], out[i], out[i + 1]
            if math.hypot(c[0] - a[0], c[1] - a[1]) <= max(eps, 3.0):
                # a -> b -> (back to a): the excursion carries no information
                del out[i]
                changed = True
                break
    return out if len(out) >= 2 else pts


def _deflect_around(p, q, sockets):
    """Waypoints that take segment p->q around any socket keep-out it violates,
    tangentially. Returns [] when the segment is already clear.

    Two cases. If neither end sits on the socket the segment is simply pushed
    out to the keep-out radius at its closest approach. If one end IS a pin on
    that socket — which every heater landing is — the wire instead leaves
    radially to the keep-out ring and then turns along it, so it departs the
    lug the way a real harness does rather than cutting back over the pins."""
    best = None
    for (cx, cy, r) in sockets:
        d = _point_seg_dist((cx, cy), p, q)
        if d >= r - 0.5:
            continue
        if best is None or d < best[0]:
            best = (d, cx, cy, r)
    if best is None:
        return []
    _d, cx, cy, r = best
    C = (cx, cy)
    dp = math.hypot(p[0] - cx, p[1] - cy)
    dq = math.hypot(q[0] - cx, q[1] - cy)
    anchored = None
    if dp < r - 0.5:
        anchored = (p, q)
    elif dq < r - 0.5:
        anchored = (q, p)
    if anchored is None:
        # a pass-by: push the closest approach out to the keep-out ring
        f = _closest_point_on_seg(C, p, q)
        vx, vy = f[0] - cx, f[1] - cy
        L = math.hypot(vx, vy)
        if L < 1e-6:
            ux, uy = _seg_unit(p, q)
            vx, vy, L = -uy, ux, 1.0
        return [(cx + vx / L * r, cy + vy / L * r)]
    inner, outer = anchored
    ux, uy = inner[0] - cx, inner[1] - cy
    L = math.hypot(ux, uy) or 1e-9
    ux, uy = ux / L, uy / L
    escape = (cx + ux * r, cy + uy * r)
    # which way round the ring is the far end?
    cross = ux * (outer[1] - cy) - uy * (outer[0] - cx)
    s = 1.0 if cross >= 0 else -1.0
    th = math.radians(62.0) * s
    tx = ux * math.cos(th) - uy * math.sin(th)
    ty = ux * math.sin(th) + uy * math.cos(th)
    tangent = (cx + tx * r, cy + ty * r)
    if _point_seg_dist(C, escape, outer) >= r - 0.5:
        return [escape] if inner is p else [escape]
    return ([escape, tangent] if inner is p else [tangent, escape])


def _closest_point_on_seg(pt, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return a
    t = max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L2))
    return (ax + t * dx, ay + t * dy)


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
        # Optional per-layout wiring-legend overrides, {colour_name: "entry"}.
        # A colour that carries a documented FUNCTION in a given drawing (the
        # AA764's single-ended 6.3 V heater feed, which is a plain green run and
        # so earns no twisted-pair legend line) says so in the swatch row, so
        # the SVG is self-describing when read on its own.
        self.wire_legend = {str(k).lower(): str(v)
                            for k, v in (layout.get("wire_legend") or {}).items()}
        self.bus = layout.get("bus", []) or []               # v2 ground bus
        self.errors: list[str] = []
        # label / obstacle registries — every piece of drawing-content type goes
        # through self.lab(), every glyph body through obst_*(). The
        # label-collision lint (lint_layout, checks c/d/e) reads them back after
        # a render, so the gate measures the same geometry the SVG ships.
        self.labels: list[dict] = []
        self.obstacles: list[dict] = []
        self._pending: list[dict] = []
        # PAGE CHROME — title, attribution, footnotes, legend rows. Not board
        # content (it is never placed, and the placer must not route around it),
        # but it IS ink on the page, and until 2026-08-08 nothing measured it:
        # the 5E4-A's attribution line ran 1515 px past the right edge of its own
        # viewBox and simply was not in the picture — no viewport could recover
        # it, because it was never drawn inside the page. Every chrome string now
        # goes through chrome_text(), which records its box, and lint check (h)
        # reads them back with the same "ink must be inside the viewBox" rule it
        # already applies to glyphs and labels.
        self.chrome: list[dict] = []
        # Footnotes raised by the drawing itself (an iron rating the glyph could
        # not carry — see iron_value()); each is one footer line.
        self.footnotes: list[str] = []
        self.iron = load_iron(amp_id)
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
        # Does this board carry a polarised rectifier/diode body? (drives the
        # extra Bodies-legend entry — the legend must name every form drawn.)
        self._has_diode = any(
            category(self.bom.get(p.get("ref"), {}).get("part", "")) == "diode"
            for p in self.parts if p.get("ref")) or any(
            category(self.bom.get(it.get("ref"), {}).get("part", "")) == "diode"
            for it in self.offboard if it.get("ref"))
        # transformer lead colour slots (assigned from run/bus endpoints)
        self._assign_xfmr_leads()
        self._colours_used: list[str] = []
        self._has_twisted = False
        # known ahead of the geometry pass (needed for the footer-height math
        # below): does this layout's raw wiring carry a twisted heater run at
        # all? If so the legend earns an extra note line (see _legend), which
        # needs its own reserved row in the footer band.
        self._layout_has_twisted = any(
            str(r.get("style", "")).lower() == "twisted" for r in self.runs)
        # The wiring legend's swatch row and the drawing's footnotes are page
        # chrome whose LENGTH is data-dependent, so both are resolved here,
        # before the page is sized — see _footer_stack().
        self._prescan_wiring()
        self._collect_footnotes()
        # board pixel box
        self.board_x = MARGIN_L
        # Top-edge off-board items label AWAY from the board (upward) so the
        # label band never lands in the item's own terminal row and lead fan —
        # see _label_side(). That needs headroom above them: the canvas top
        # margin grows so the highest label's cap-top clears the drawing title
        # (baseline 34, descender ~40).
        rise = max([self._top_label_rise(it) for it in self.offboard
                    if it.get("edge") == "top"] or [0.0])
        self.board_w = PAD_X * 2 + (self.cols - 1) * CW
        self.board_h = BOARD_TOP_PAD + ROWGAP + 40
        self.width = self.board_x + self.board_w + MARGIN_R
        # The bottom margin below already grows so the deepest routing lane
        # clears the footer legend; the head of the canvas needs the mirror of
        # that rule. A run routed ABOVE the board (a negative `via` row) lays a
        # lane across the top of the sheet — high enough and it leaves the sheet
        # entirely, and the drawing title sits in that same band, where a wire
        # drawn through the words reads as part of the circuit. Boards whose
        # wiring already clears both keep their geometry exactly as it was.
        self.board_y = max(MARGIN_TOP, int(math.ceil(52 + rise + 84)),
                           self._top_lane_y())
        # ---- page-chrome type scale -------------------------------------
        # Board geometry is a fixed px grid (CW/ROWGAP), so a 50-column board
        # renders 2.4x wider than a 20-column one at a near-constant height.
        # Rendered to a common page width — which is how every one of these is
        # actually read — fixed-size chrome type shrinks in proportion: the
        # title and the legend on the widest sheet came out roughly half the
        # ink height of the narrowest. So the *chrome* (title, attribution,
        # legend) is set relative to the sheet's own viewBox width, which keeps
        # its rendered ink height constant across the corpus. Board CONTENT
        # type (refs, values, socket captions) is deliberately NOT scaled: it
        # is measured against a fixed-px grid by the placer and the lint, and
        # it must stay legible relative to the parts it names.
        self.cs = min(1.62, max(0.92, self.width / CHROME_REF_W))
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
            # and the rest leaves room for the stacked footer lines. That
            # reserve used to be the constant 92 (110 with a twisted-pair note),
            # which held only while the footer was exactly four or five lines.
            # It is now MEASURED from the stack the page will actually draw
            # (_footer_stack), so a wrapped attribution, a wrapped swatch row or
            # a footnote grows the band instead of being drawn under the page
            # edge or off the side of it. Floored at 356 (374 with the note) so
            # ordinary under-chassis layouts keep their footer clear.
            nrows = len(self._footer_stack())
            base_reserve = FOOTER_BASE + nrows * FOOTER_PITCH
            footer_reserve = base_reserve * self.cs
            default_rows = 5 if self._layout_has_twisted else 4
            footer_floor = (374 if self._layout_has_twisted else 356) \
                + (footer_reserve - (FOOTER_BASE + default_rows * FOOTER_PITCH))
            needed = self.ey(deep_row) + 14 + footer_reserve - (self.board_y + self.board_h)
            self.margin_bot = max(int(math.ceil(footer_floor)), int(math.ceil(needed)))
        else:
            extra = (len(self._footer_stack()) - 1) * FOOTER_PITCH * self.cs
            self.margin_bot = int(math.ceil(
                MARGIN_BOT + (MARGIN_BOT * (self.cs - 1)) * 0.4 + max(0.0, extra)))
        self.height = self.board_y + self.board_h + self.margin_bot

    # ---- coordinates --------------------------------------------------------
    def ex(self, col):
        return self.board_x + PAD_X + col * CW

    def ey(self, row):
        top = self.board_y + BOARD_TOP_PAD
        return top + row * ROWGAP

    # ---- page chrome (title / attribution / legend) -------------------------
    def cz(self, size):
        """A chrome type size, scaled to this sheet's own width (see self.cs)."""
        return round(size * self.cs, 2)

    def _footer_y(self, row):
        """Baseline of footer row `row`, counted up from the bottom edge:
        0 = bodies legend, 1 = joints, then the wiring rows, the twisted-pair
        note, any footnotes and the attribution — see _footer_stack()."""
        return self.height - (FOOTER_BASE + row * FOOTER_PITCH) * self.cs

    # ---- page chrome: measured, and inside the page ------------------------
    # Chrome ink stays this far inside the right page edge. The legend and the
    # attribution used to run left-to-right with no terminator at all: the
    # 5E4-A's provenance line was 3559 px wide on a 2044 px page, so two thirds
    # of the sentence that says WHERE THE DRAWING CAME FROM was never in the
    # picture. Nothing downstream could recover it — a viewport can only crop
    # what is inside the viewBox, and this was outside it. Every chrome row is
    # now wrapped to this width and every chrome string is measured by lint
    # check (h), so the failure cannot come back silently.
    CHROME_RIGHT_PAD = 24.0
    FOOT_INDENT = 58.0        # x of the first entry after a row's caption word
    FOOT_GUTTER = 16.0        # clear space after an entry, before the next
    TWISTED_NOTE = ("Note: the 6.3 V heater twisted pair always routes on the "
                    "top layer and never joins another run — its crossings are "
                    "not hop-overs.")

    def chrome_width(self):
        return self.width - self.board_x - self.CHROME_RIGHT_PAD

    def chrome_text(self, els, x, y, s, fill, size, *, anchor="start",
                    font=FONT_MONO, weight=500, spacing=None, tag="chrome"):
        """Draw a page-chrome string AND record its box, so the bounds check
        sees it. Chrome is not board content — it is never placed and the label
        placer must not route around it — but it is ink on the page."""
        if not str(s).strip():
            return
        els.append(text(x, y, s, fill, size, anchor=anchor, font=font,
                        weight=weight, spacing=spacing))
        self.chrome.append({"tag": tag, "text": str(s),
                            "box": text_box(x, y, str(s), size, anchor=anchor,
                                            font=font, spacing=spacing)})

    def chrome_mark(self, x0, y0, x1, y1, tag):
        """Record a non-text chrome mark (a legend swatch or glyph) for (h)."""
        self.chrome.append({"tag": tag, "box": (min(x0, x1), min(y0, y1),
                                                max(x0, x1), max(y0, y1))})

    @staticmethod
    def _wrap(s, size, avail, font=FONT_MONO, spacing=None):
        """Word-wrap a chrome string to `avail` px using the same metrics the
        lint measures with. Words are never broken: a single over-long token
        stays whole and check (h) reports it, rather than the page hiding it."""
        out, cur = [], ""
        for w in str(s).split():
            cand = f"{cur} {w}".strip()
            if cur and text_width(cand, size, font, spacing) > avail:
                out.append(cur)
                cur = w
            else:
                cur = cand
        if cur:
            out.append(cur)
        return out or [""]

    def attribution(self):
        src = self.layout.get("source", {}) or {}
        if src.get("desc"):
            return f"Redrawn from {src['desc']} — not a trace"
        return self.layout.get("caption") or ""

    def _chunk_entries(self, entries, avail):
        """Split legend entries into rows that fit. The caption word ('Wiring:')
        indents the first row; continuation rows start at the same indent so the
        column reads straight."""
        rows, cur, w = [], [], self.FOOT_INDENT * self.cs
        for e in entries:
            if cur and w + e["w"] > avail:
                rows.append(cur)
                cur, w = [], self.FOOT_INDENT * self.cs
            cur.append(e)
            w += e["w"]
        if cur:
            rows.append(cur)
        return rows or [[]]

    def _footer_stack(self):
        """Every footer row, BOTTOM row first — the order _footer_y() counts in.

        Built once, from the same data the drawing pass uses, so the height
        reserved in the geometry pass and the rows actually drawn are the same
        number by construction. The old fixed indices (bodies=0, joints=1,
        wiring=2, attrib=3) could not grow, which is how a long provenance line
        came to be drawn off the page instead of wrapped onto it."""
        if getattr(self, "_stack_cache", None) is not None:
            return self._stack_cache
        avail = self.chrome_width()
        fs = self.cz(10.5)
        ns = self.cz(9.5)
        rows: list[tuple] = []
        for chunk in reversed(self._chunk_entries(self._bodies_entries(fs), avail)):
            rows.append(("entries", "Bodies:", chunk, fs))
        if self.runs or self.bus:
            for chunk in reversed(self._chunk_entries(self._joints_entries(fs), avail)):
                rows.append(("entries", "Joints:", chunk, fs))
            for chunk in reversed(self._chunk_entries(self._wiring_entries(fs), avail)):
                rows.append(("entries", "Wiring:", chunk, fs))
        if self._has_twisted:
            for line in reversed(self._wrap(self.TWISTED_NOTE, ns, avail)):
                rows.append(("line", line, ns, "faint"))
        for note in reversed(self.footnotes):
            for line in reversed(self._wrap(note, ns, avail)):
                rows.append(("line", line, ns, "faint"))
        for line in reversed(self._wrap(self.attribution(), fs, avail)):
            if line:
                rows.append(("line", line, fs, "faint"))
        self._stack_cache = rows
        return rows

    def _draw_footer(self, els):
        """Draw the planned footer stack. Only the caption word of a row group's
        FIRST (topmost) chunk is printed; continuation rows are indented under
        it, so 'Wiring:' names the block rather than repeating down it."""
        s = self.cs
        stack = self._footer_stack()
        seen_caption: set[str] = set()
        for i in range(len(stack) - 1, -1, -1):
            row = stack[i]
            y = self._footer_y(i)
            if row[0] == "line":
                _kind, txt, size, tone = row
                self.chrome_text(els, self.board_x, y, txt,
                                 self.FOOT_FAINT if tone == "faint" else self.FOOT_MUTED,
                                 size, tag="chrome caption")
                continue
            _kind, caption, chunk, fs = row
            if caption not in seen_caption:
                self.chrome_text(els, self.board_x, y, caption, self.FOOT_FAINT, fs,
                                 tag=f"chrome {caption.rstrip(':').lower()}")
                seen_caption.add(caption)
            cx = self.board_x + self.FOOT_INDENT * s
            for e in chunk:
                els.append(e["glyph"](cx, y, s))
                self.chrome_mark(cx, y - 11 * s, cx + e["lead"] * s, y + 3 * s,
                                 "legend swatch")
                self.chrome_text(els, cx + e["lead"] * s, y, e["label"],
                                 self.FOOT_MUTED, fs, tag="chrome legend")
                cx += e["w"]

    def _entry(self, label, lead, glyph, fs):
        return {"label": label, "lead": lead, "glyph": glyph,
                "w": lead * self.cs + text_width(label, fs, FONT_MONO)
                     + self.FOOT_GUTTER * self.cs}

    # ---- legend entries (house paint; SheetRenderer overrides the drawing) --
    FOOT_FAINT = FAINT
    FOOT_MUTED = MUTED

    @staticmethod
    def _rule(cx, y, s, colour, width, length=18.0):
        return (f'<line x1="{fmt(cx)}" y1="{fmt(y - 3*s)}" x2="{fmt(cx + length*s)}" '
                f'y2="{fmt(y - 3*s)}" stroke="{colour}" stroke-width="{fmt(width*s)}" '
                f'stroke-linecap="round"/>')

    def _wiring_entries(self, fs):
        out = [self._entry("lead (uncoloured)", 24.0,
                           lambda cx, y, s: self._rule(cx, y, s, WIRE_NEUTRAL, 2.4), fs)]
        for key in self._colours_used:
            col = WIRE.get(key, WIRE_NEUTRAL)
            out.append(self._entry(
                self.wire_legend.get(key, key), 24.0,
                lambda cx, y, s, c=col: self._rule(cx, y, s, c, 2.4), fs))
        if self.bus:
            out.append(self._entry("ground bus", 24.0,
                                   lambda cx, y, s: self._rule(cx, y, s, BUS_CORE, 3.4), fs))
        if self._has_twisted:
            out.append(self._entry("6.3 V heaters — twisted pair", 26.0,
                                   self._twist_swatch, fs))
        return out

    def _twist_swatch(self, cx, y, s, colour=None):
        colour = colour or HEATER
        d1, d2 = twisted_strands([(cx, y - 3 * s), (cx + 20 * s, y - 3 * s)],
                                 amp=2.6 * s, wavelen=8.0 * s)
        return (f'<path d="{d1}" fill="none" stroke="{colour}" '
                f'stroke-width="{fmt(1.5*s)}" stroke-linecap="round"/>'
                f'<path d="{d2}" fill="none" stroke="{colour}" '
                f'stroke-width="{fmt(1.5*s)}" stroke-linecap="round"/>')

    def _hop_swatch(self, cx, y, s, colour):
        hd = hopped_path([(cx, y - 3 * s), (cx + 34 * s, y - 3 * s)],
                         {0: [(17.0 * s, HOP_R * s)]}, r=11 * s)
        return (f'<path d="{hd}" fill="none" stroke="{colour}" '
                f'stroke-width="{fmt(2.3*s)}" stroke-linecap="round" '
                f'stroke-linejoin="round"/>')

    def _joints_entries(self, fs):
        return [
            self._entry("wire end (solder joint)", 13.0,
                        lambda cx, y, s: solder_blob(cx + 4 * s, y - 3 * s), fs),
            self._entry("cross-over (no connect)", 40.0,
                        lambda cx, y, s: self._hop_swatch(cx, y, s, WIRE_NEUTRAL), fs),
        ]

    def _bodies_entries(self, fs):
        items = [(RES_BODY, "resistor"), (FILM_BODY, "film / coupling cap"),
                 (ELEC_BODY, "electrolytic"), (MICA_BODY, "mica")]
        if self._has_diode:
            items.append((DIODE_BODY, "diode / rectifier"))
        return [self._entry(
            lab, 19.0,
            lambda cx, y, s, f=fill: (
                f'<rect x="{fmt(cx)}" y="{fmt(y-8*s)}" width="{fmt(14*s)}" '
                f'height="{fmt(9*s)}" rx="{fmt(2.5*s)}" fill="{f}" '
                f'stroke="{BOARD_EDGE}" stroke-width="0.6"/>'), fs)
            for fill, lab in items]

    # ---- pre-render scans (data the page size depends on) -------------------
    def _prescan_wiring(self):
        """Resolve which colour swatches and which twisted-pair note the legend
        will carry, in the order the drawing pass will emit them. Run in the
        constructor, because the footer's height depends on it and the page is
        sized before anything is drawn."""
        for spec in self.runs:
            if str(spec.get("style", "")).lower() == "twisted":
                self._has_twisted = True
                continue
            colour = spec.get("color") or self._endpoint_colour(spec.get("from")) \
                or self._endpoint_colour(spec.get("to"))
            if colour:
                key = str(colour).lower()
                if key not in self._colours_used:
                    self._colours_used.append(key)

    def _collect_footnotes(self):
        """Footnote lines the iron glyphs raise — see iron_value(). One line per
        off-board transformer/choke whose parts-list value says more than the
        drawing can letter beside it."""
        for it in self.offboard:
            if it.get("kind") not in ("xfmr", "choke") or not it.get("ref"):
                continue
            ref = it["ref"]
            _drawn, note = iron_value(self.bom_for(ref)["value"], self.iron.get(ref))
            if note:
                self.footnotes.append(f"{ref} — {note}")

    # ---- labels + obstacles (drawing content the lint measures) ------------
    def lab(self, x, y, s, fill, size, *, anchor="middle", font=FONT_DISP,
            weight=600, spacing=None, halo=None, halo_width=3.0, tag="",
            group=None, keep_in=None, owner=None):
        """QUEUE a content label. Nothing is emitted here: labels are resolved
        and drawn in one final pass (_emit_labels) once every wire, body and
        terminal is known, so placement can be collision-aware instead of a
        fixed offset plus hand-authored nudges. `group` ties labels that must
        move together (a ref and its value); `keep_in` is a box the label may
        not leave (the board rect for a board part, the canvas for the rest).
        Title, attribution and the footer legends are chrome, not board
        content — they call text() directly and are neither placed nor
        measured."""
        if not str(s).strip():
            return ""
        self._pending.append({
            "x": x, "y": y, "text": str(s), "fill": fill, "size": size,
            "anchor": anchor, "font": font, "weight": weight, "spacing": spacing,
            "halo": halo, "halo_width": halo_width, "tag": tag,
            "group": group if group is not None else f"_{len(self._pending)}",
            "keep_in": keep_in, "owner": owner,
        })
        return ""

    # Candidate placements, tried in order: the authored position first, then a
    # short deterministic ladder of small moves. Kept short and local on
    # purpose — a label that has to travel far to find air is a drawing problem
    # for a human to solve, and the lint will say so.
    LABEL_LADDER = [(0, 0), (0, -12), (0, 12), (0, -22), (0, 22),
                    (-18, 0), (18, 0), (-18, -12), (18, -12), (-18, 12), (18, 12),
                    (0, -32), (0, 32), (-30, -12), (30, -12), (-30, 12), (30, 12),
                    (0, -42), (0, 42),
                    # Second tier, added with the (hard, soft) scoring: the
                    # placer no longer stops at the first merely-legal rung, so
                    # a few more reaches give it somewhere clean to land on a
                    # dense board instead of settling on a conductor.
                    (-26, -22), (26, -22), (-26, 22), (26, 22),
                    (-12, -32), (12, -32), (-12, 32), (12, 32),
                    (-40, 0), (40, 0), (-40, -22), (40, -22), (-40, 22), (40, 22)]
    # Second phase: a label still struck after its whole group has been placed
    # may slide on its own — the measured form of the old hand-authored
    # `value_nudge`. Deliberately short so a value never travels far enough from
    # its ref to be mis-attributed (that was its own review finding).
    LABEL_SOLO_LADDER = [(0, -9), (0, 9), (-14, 0), (14, 0), (0, -14), (0, 14),
                         (-20, -9), (20, -9), (-20, 9), (20, 9),
                         (0, -21), (0, 21), (-24, -21), (24, -21), (-24, 21), (24, 21)]

    def _label_cost(self, boxes, placed, wires):
        """How many legibility violations a candidate placement of one label
        group costs — same tests, same thresholds as the lint's checks c/d/e,
        so a placement the placer accepts is a placement the gate accepts."""
        return self._label_cost2(boxes, placed, wires)[0]

    # A conductor merely CROSSING a label transversally is not a lint failure —
    # the halo handles it, and demanding otherwise on a dense board would be
    # unsatisfiable. But it is still the second-best placement, and until
    # 2026-08-04 the placer could not tell it apart from clear air: it broke on
    # the first zero-HARD-cost rung, so a designator landed on a lead whenever
    # that rung came first, even with untouched board a rung further along.
    # Every "label struck by a lead" finding in the 2026-08-03 review was this.
    # So placements are now scored on a (hard, soft) pair: `hard` is exactly the
    # gate's verdict and still dominates; `soft` counts near misses — any
    # conductor in the box at all, any glyph contact, any crowding of an
    # already-placed label — and breaks ties among placements the gate would
    # accept equally. The gate is unchanged; the drawing simply stops settling.
    SOFT_WIRE_SPAN = 2.0      # any conductor this far into a label box at all
    SOFT_GLYPH = 0.8          # any body/socket/solder-dot contact
    SOFT_GAP = 5.5            # clear space a label PREFERS around itself

    def _label_cost2(self, boxes, placed, wires):
        hard = soft = 0
        for box in boxes:
            width = box[2] - box[0]
            tbox = _shrink(box, LINT_LABEL_INSET)
            hard_wire = soft_wire = False
            for _name, pts in wires:
                span = 0.0
                for k in range(len(pts) - 1):
                    span = max(span, _seg_box_span(pts[k], pts[k + 1], tbox))
                if span > max(LINT_WIRE_SPAN, LINT_WIRE_FRAC * width):
                    hard_wire = True
                    break
                if span > self.SOFT_WIRE_SPAN:
                    soft_wire = True
            hard += hard_wire
            soft += soft_wire
            hard_ob = soft_ob = False
            for ob in self.obstacles:
                w, h = _box_overlap(tbox, ob["box"])
                if w > LINT_GLYPH_W and h > LINT_GLYPH_H:
                    hard_ob = True
                    break
                if w > self.SOFT_GLYPH and h > self.SOFT_GLYPH:
                    soft_ob = True
            hard += hard_ob
            soft += soft_ob
            grown = _shrink(box, -LINT_LABEL_GAP)
            roomy = _shrink(box, -self.SOFT_GAP)
            hard_lb = soft_lb = False
            for pb in placed:
                w, h = _box_overlap(grown, pb)
                if w > LINT_LABEL_W and h > LINT_LABEL_H:
                    hard_lb = True
                    break
                w2, h2 = _box_overlap(roomy, pb)
                if w2 > LINT_LABEL_W and h2 > LINT_LABEL_H:
                    soft_lb = True
            hard += hard_lb
            soft += soft_lb
        return hard, soft

    def _emit_labels(self, wires):
        """Resolve every queued label against the finished geometry, then draw.
        Groups are placed in queue order — off-board identifications first, then
        the board's ref/value pairs — each one treating the already-placed
        labels as fixed. Deterministic: a fixed ladder, first-best wins,
        ties broken by ladder order."""
        groups: dict = {}
        for spec in self._pending:
            groups.setdefault(spec["group"], []).append(spec)
        placed: list[tuple] = []
        out: list[str] = []
        for gid, specs in groups.items():
            best, best_cost = (0, 0), None
            for (dx, dy) in self.LABEL_LADDER:
                boxes = [text_box(sp["x"] + dx, sp["y"] + dy, sp["text"], sp["size"],
                                  anchor=sp["anchor"], font=sp["font"],
                                  spacing=sp["spacing"]) for sp in specs]
                keep = specs[0].get("keep_in")
                if keep and any(b[0] < keep[0] or b[1] < keep[1] or b[2] > keep[2]
                                or b[3] > keep[3] for b in boxes):
                    continue
                cost = self._label_cost2(boxes, placed, wires)
                if best_cost is None or cost < best_cost:
                    best, best_cost = (dx, dy), cost
                if cost == (0, 0):
                    break
            dx, dy = best
            for sp in specs:
                sx, sy = sp["x"] + dx, sp["y"] + dy
                box = text_box(sx, sy, sp["text"], sp["size"], anchor=sp["anchor"],
                               font=sp["font"], spacing=sp["spacing"])
                cur = self._label_cost2([box], placed, wires)
                if len(specs) > 1 and cur != (0, 0):
                    keep = sp.get("keep_in")
                    for (ex, ey_) in self.LABEL_SOLO_LADDER:
                        cand = text_box(sx + ex, sy + ey_, sp["text"], sp["size"],
                                        anchor=sp["anchor"], font=sp["font"],
                                        spacing=sp["spacing"])
                        if keep and (cand[0] < keep[0] or cand[1] < keep[1]
                                     or cand[2] > keep[2] or cand[3] > keep[3]):
                            continue
                        cand_cost = self._label_cost2([cand], placed, wires)
                        if cand_cost < cur:
                            sx, sy, box, cur = sx + ex, sy + ey_, cand, cand_cost
                            if cur == (0, 0):
                                break
                placed.append(box)
                self.labels.append({"text": sp["text"], "tag": sp["tag"], "box": box})
                lead = self._leader(sp.get("owner"), box)
                if lead:
                    out.append(lead)   # before the text: the halo cuts it clean
                out.append(text(sx, sy, sp["text"], sp["fill"], sp["size"],
                                anchor=sp["anchor"], font=sp["font"],
                                weight=sp["weight"], spacing=sp["spacing"],
                                halo=sp["halo"], halo_width=sp["halo_width"]))
        return "".join(out)

    # A label the placer had to move this far from the body it names gets a
    # LEADER: a hairline from the type back to the part. Without one, a
    # designator that has been pushed clear of a crowded row reads as belonging
    # to whatever it landed nearest (the 5F2-A sheet's R9 sat beside C6 and was
    # read as C6's; the 5D3's RPT was pushed onto a wire two eyelets away).
    # Below the threshold nothing is drawn — a label sitting on its own part
    # needs no pointer, and a leader on every label would be noise.
    LEADER_INK = BOARD_EDGE
    LEADER_GAP = 15.0
    LEADER_MAX = 140.0        # beyond this the placement is a drawing fault,
                              # and lint check (i) is the right place to say so

    def _leader(self, owner_tag, box):
        if not owner_tag:
            return ""
        boxes = [ob["box"] for ob in self.obstacles if ob["tag"] == owner_tag]
        if not boxes:
            return ""
        target = min(boxes, key=lambda b: _box_gap(box, b))
        gap = _box_gap(box, target)
        if not (self.LEADER_GAP < gap < self.LEADER_MAX):
            return ""
        (x1, y1), (x2, y2) = _box_link(box, target)
        return (f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
                f'stroke="{self.LEADER_INK}" stroke-width="0.9" opacity="0.75" '
                f'stroke-linecap="round"/>'
                f'<circle cx="{fmt(x2)}" cy="{fmt(y2)}" r="1.4" '
                f'fill="{self.LEADER_INK}" opacity="0.75"/>')

    def canvas_box(self, pad=8.0):
        """The box a label may not leave — the drawing canvas, minus a margin."""
        return (pad, pad, self.width - pad, self.height - pad)

    def board_box(self, pad=3.0):
        """The box a BOARD PART's ref and value may not leave — the board rect.

        A board part's labels used to be bounded only by the canvas, so when the
        placer could not find air beside a bottom-row part it slid the value down
        off the board: onto the drawn board edge, onto the ground bus rod, or out
        onto the bare chassis strip below, where dark board ink has nothing to
        read against (the 5E1's R9, the 5E3's RL1 and RL4, the 5F6-A's RD1 and
        RM2, the 5E4-A's RSL). A value printed off its own board is worse than a
        value printed close to its neighbour: the reader cannot tell which part
        it belongs to, and on the sheet style cannot see it at all. The ladder is
        now bounded by the board, and where the board genuinely has no air the
        placer falls back to the authored position — still on the board, beside
        the part, which is the drawing telling the truth about how tight it is."""
        return (self.board_x + pad, self.board_y + pad,
                self.board_x + self.board_w - pad,
                self.board_y + self.board_h - pad)

    def obst_rect(self, x0, y0, x1, y1, tag):
        self.obstacles.append({"tag": tag, "box": (min(x0, x1), min(y0, y1),
                                                   max(x0, x1), max(y0, y1))})

    def obst_circle(self, cx, cy, r, tag):
        self.obstacles.append({"tag": tag, "box": (cx - r, cy - r, cx + r, cy + r)})

    # ---- off-board label placement -----------------------------------------
    def _label_side(self, item):
        """Which way an off-board item's label band faces: -1 (above the glyph)
        for a TOP-edge item, +1 (below) otherwise. The rule is 'away from the
        board': a top-edge pot, jack or transformer has its lugs, tip/sleeve or
        pigtails on its board-facing (lower) side, and every lead it carries
        fans down through that band — so a label placed there is guaranteed to
        be struck by its own wiring. Bottom/left/right items already label away
        from the board with the house 'below the glyph' band."""
        return -1 if item.get("edge") == "top" else 1

    def _top_lane_y(self):
        """The least `board_y` that (a) keeps every wiring lane routed above the
        board inside the canvas, and (b) keeps the lanes that pass under the
        drawing title clear of it. 0 when nothing routes above the board.

        A run's `via` list is enough to find those lanes: each consecutive pair
        of vias is routed orthogonally, so the pair covers columns
        min..max somewhere at or above the shallower of its two rows. That is a
        conservative read — it can reserve headroom for a lane that turns before
        it reaches the title — and conservative is the right side to err on for
        a rule whose failure modes are a wire that leaves the sheet and a wire
        drawn through a word.

        Both styles are measured and the taller title wins, so the two drawings
        of one board keep a common geometry.
        """
        segs = []                      # (row, col_lo, col_hi), row < 0 only
        for spec in (list(self.runs) + list(self.bus)):
            pts = []
            for v in (spec.get("via") or []):
                if not (isinstance(v, (list, tuple)) and len(v) == 2):
                    continue
                try:
                    pts.append((float(v[0]), float(v[1])))
                except (TypeError, ValueError):
                    continue
            for (c0, r0), (c1, r1) in zip(pts, pts[1:]):
                if min(r0, r1) < 0:
                    segs.append((min(r0, r1), min(c0, c1), max(c0, c1)))
            for c, r in pts:
                if r < 0:
                    segs.append((r, c, c))
        if not segs:
            return 0
        title = ((self.layout.get("board", {}) or {}).get("title")
                 or f"{self.amp_id.upper()} board layout")
        # self.cs is a function of self.width alone and is assigned further down
        # this constructor; recompute it here rather than reorder the geometry.
        cs = min(1.62, max(0.92, self.width / CHROME_REF_W))
        house_ts, sheet_ts = round(17 * cs, 2), round(18 * cs, 2)
        # house: baseline 20+ts plus a descender; sheet: same baseline, plus the
        # rule drawn under it at +7.5 and its own stroke.
        bottom = 20 + max(house_ts * 1.22, sheet_ts + 7.5 + 0.6 * cs)
        right = self.board_x + max(
            text_width(title, house_ts, spacing="0.08em"),
            text_width(title.upper(), sheet_ts, spacing="0.14em"))
        need = 0
        for row, c_lo, c_hi in segs:
            # (a) the lane has to be on the sheet at all
            need = max(need, TOP_LANE_CLEAR - BOARD_TOP_PAD - row * ROWGAP)
            # (b) and clear of the title where it passes beneath it
            if self.board_x + PAD_X + c_lo * CW <= right:
                need = max(need, bottom + TITLE_LANE_CLEAR - BOARD_TOP_PAD
                           - row * ROWGAP)
        return int(math.ceil(need))

    def _top_label_rise(self, item):
        """How far above a TOP-edge item's centre its label band's cap-top
        reaches — the headroom the canvas must reserve above it."""
        kind = item.get("kind", "tube")
        if kind == "pot":
            return 18 + 21 + CAP_RISE * 11.5
        if kind == "tube":
            return TUBE_R + 8 + CAP_RISE * 12
        if kind in ("xfmr", "choke"):
            h = 56 if kind == "xfmr" else 34
            return h / 2 + 27 + CAP_RISE * 11.5
        if kind == "jack":
            return 9 + 8 + CAP_RISE * 10.5
        if kind == "part":
            # lamp glyph labels sit above the bulb; a generic axial body labels
            # just above its own (board-facing) terminals.
            return 30 + CAP_RISE * 11.5 if item.get("glyph") == "lamp" else 10 + CAP_RISE * 11.5
        return 9 + 8 + CAP_RISE * 10.5      # switch / fuse / misc

    def cathode_side(self, part):
        """Which end of a drawn body carries the cathode band: -1 = the left
        (horizontal) or top (vertical) end, +1 = the right/bottom end, 0 = not
        declared. Read from the part's optional `cathode: a|b` field, which
        names the eyelet the SCHEMATIC puts the cathode on — the drawing never
        infers a polarity, and an undeclared diode is drawn unbanded rather
        than guessed at."""
        end = str(part.get("cathode", "")).strip().lower()
        if end not in ("a", "b"):
            return 0
        (r1, c1), (r2, c2) = part["a"], part["b"]
        if c1 == c2 and r1 != r2:            # vertical: -1 = upper eyelet
            first_is_low = r1 < r2
        else:
            first_is_low = c1 <= c2
        a_low = first_is_low
        return (-1 if a_low else 1) if end == "a" else (1 if a_low else -1)

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

    def _lead_callout(self, item, colour, ex_, ey_, base, ink, halo):
        """Name a transformer pigtail the drawing cannot name by colour.

        A lead whose suffix IS an era wire colour needs no callout — the ink and
        the legend say it. But where the source drawing shows uncoloured wire
        the layout addresses the terminals by FUNCTION (`T2.pri_p`,
        `T2.sec_h`), and those four identical black leads into four identical
        terminals told a builder nothing about which was which. The callout
        letters the terminal name the data already carries, so nothing is
        invented and nothing is left to guess."""
        if lead_base(colour) is not None:
            return
        txt = str(colour).replace("_", " ").replace("-", " ").upper()
        edge = item.get("edge", "left")
        dx, dy = base[0] - ex_, base[1] - ey_       # points back at the body
        if abs(dx) >= abs(dy):
            lx, anchor = ex_ - math.copysign(7.5, dx), ("end" if dx > 0 else "start")
            ly = ey_ + 3.0
        else:
            lx, anchor, ly = ex_, "middle", ey_ - math.copysign(8.0, dy)
        self.lab(lx, ly, txt, ink, 7.5, anchor=anchor, weight=600, spacing="0.03em",
                 halo=halo, halo_width=2.4,
                 tag=f"lead {item.get('id', '')}.{colour}",
                 group=f"lead:{item.get('id', '')}.{colour}",
                 keep_in=self.canvas_box())

    def xfmr_lead_pos(self, item, colour):
        cx, cy = self.off_pos(item)
        edge = item.get("edge", "left")
        w, h = (46, 56) if item.get("kind") == "xfmr" else (40, 34)
        slots = self.xfmr_leads.get(item["id"], [colour])
        if colour not in slots:
            slots = slots + [colour]
        idx = slots.index(colour)
        n = len(slots)
        # Stack the pigtails along the board-facing edge, centred.
        #
        # NOT CHANGED, and the reason is worth recording. A power transformer
        # carries up to six leads out of a 56 px face; at this pitch they all
        # end on one line and leave it as a single knot in which no individual
        # lead can be followed back to its terminal (the 5F1 and 5E3 power
        # ends). Widening `spread` or fanning `stub` fixes that in isolation —
        # and moves every lead endpoint, which every authored `via` list in
        # layout.yaml is tuned against to within a few pixels. Three variants
        # were measured on 2026-08-08 (spread +6, a 3 px fan, a 9 px alternating
        # fan); each cleared the knot and each broke between 6 and 57 wiring
        # lint findings across the corpus, all of them re-routing work in
        # layout.yaml rather than engine faults. The fan-out is therefore a
        # per-layout routing change, not an engine parameter, and belongs with
        # the `via` lists it moves.
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
        # The gloss comes off (see body_value) and the repeat count goes ON: a
        # "(×2)" buried in the working-voltage field said two cans while the
        # drawing showed one and the value label said nothing at all (5F6-A C15,
        # 5F1 C4). The count is a fact about the part, so it is lettered.
        val = body_value(primary_value(rec["value"]))
        n = part_count(rec["value"])
        if n:
            val = f"{val} ×{n}"
        a, b = part["a"], part["b"]
        (r1, c1), (r2, c2) = a, b
        x1, y1 = self.ex(c1), self.ey(r1)
        x2, y2 = self.ex(c2), self.ey(r2)
        vertical = c1 == c2 and r1 != r2
        ndx, ndy = (part.get("nudge") or [0, 0])[:2]
        vndx, vndy = (part.get("value_nudge") or [0, 0])[:2]
        els = []
        # leads (short wires) drawn under the body
        els.append(f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
                   f'stroke="{LEAD}" stroke-width="2"/>')
        band = self.cathode_side(part) if cat == "diode" else 0
        if vertical:
            cx = x1
            cy = (y1 + y2) / 2
            geom, labs = self._body_vertical(cat, cx, cy, val, ref, ndx, ndy, vndx, vndy,
                                             band=band)
        else:
            cx = (x1 + x2) / 2
            cy = y1
            span = abs(c2 - c1)
            geom, labs = self._body_horizontal(cat, cx, cy, span, val, ref,
                                               ndx, ndy, vndx, vndy, band=band)
        els += geom
        # eyelets on top of leads
        els.append(eyelet(x1, y1))
        els.append(eyelet(x2, y2))
        self.obst_circle(x1, y1, 4.0, f"eyelet {ref}.a")
        self.obst_circle(x2, y2, 4.0, f"eyelet {ref}.b")
        return "".join(els), "".join(labs)

    def _label_pair(self, cx, top_y, bot_y, ref, val, ndx=0, ndy=0, vndx=0, vndy=0):
        # `nudge` (ndx/ndy) shifts the ref+value pair; `value_nudge` (vndx/vndy)
        # shifts the VALUE alone — so a value sitting under a supply lead can be
        # moved to clear space while its ref stays put.
        # Board labels carry a BOARD-coloured halo. On the board it is invisible
        # (it is the board's own tone) and simply cuts a clean gap where a
        # hookup lead passes behind the type; where a label overhangs the board
        # edge — a tall filter can's ref has nowhere else to go — the same halo
        # keeps dark ink legible against the dark well instead of vanishing.
        return (self.lab(cx + ndx, top_y + ndy, ref, BOARD_REF, 11.5, weight=700,
                         spacing="0.02em", tag=f"{ref} ref", group=f"part:{ref}",
                         keep_in=self.board_box(), halo=BOARD, halo_width=3.0,
                         owner=f"{ref} body")
                + self.lab(cx + ndx + vndx, bot_y + ndy + vndy, val, BOARD_VAL, 11,
                           font=FONT_MONO, weight=600, tag=f"{ref} value",
                           group=f"part:{ref}", keep_in=self.board_box(),
                           halo=BOARD, halo_width=2.8, owner=f"{ref} body"))

    def _body_horizontal(self, cat, cx, cy, span, val, ref, ndx=0, ndy=0, vndx=0, vndy=0,
                         band=0):
        w = max(26.0, span * CW - 16)
        els: list[str] = []
        labs: list[str] = []
        if cat == "diode":
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="2.5" fill="{DIODE_BODY}" stroke="{DIODE_EDGE}" stroke-width="1"/>')
            if band:
                bxx = (x + 4.5) if band < 0 else (x + w - 8.5)
                els.append(f'<rect x="{fmt(bxx)}" y="{fmt(y + 1.5)}" width="4" '
                           f'height="{fmt(h - 3)}" fill="{DIODE_BAND}"/>')
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            labs.append(self._label_pair(cx, y - 6, cy + 21, ref, val, ndx, ndy, vndx, vndy))
            return els, labs
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
            self.obst_rect(x, y - 4.5, x + w, y + h, f"{ref} body")
            labs.append(self._label_pair(cx, y - 6, cy + 24, ref, val, ndx, ndy, vndx, vndy))
        elif cat == "mica":
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="4" fill="{MICA_BODY}" stroke="{MICA_EDGE}" stroke-width="1.2"/>')
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            labs.append(self._label_pair(cx, y - 6, cy + 20, ref, val, ndx, ndy, vndx, vndy))
        elif cat == "film":
            h = 22
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="10" fill="{FILM_BODY}" stroke="{FILM_EDGE}" stroke-width="1.2"/>')
            els.append(f'<line x1="{fmt(cx)}" y1="{fmt(y+2)}" x2="{fmt(cx)}" y2="{fmt(y+h-2)}" '
                       f'stroke="{FILM_EDGE}" stroke-width="0.8" opacity="0.7"/>')
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            labs.append(self._label_pair(cx, y - 6, cy + 22, ref, val, ndx, ndy, vndx, vndy))
        else:  # resistor / other
            h = 16
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="7" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            for ex_ in (x + 5, x + w - 5):
                els.append(f'<line x1="{fmt(ex_)}" y1="{fmt(y+1)}" x2="{fmt(ex_)}" y2="{fmt(y+h-1)}" '
                           f'stroke="{RES_END}" stroke-width="2"/>')
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            labs.append(self._label_pair(cx, y - 6, cy + 21, ref, val, ndx, ndy, vndx, vndy))
        return els, labs

    def _body_vertical(self, cat, cx, cy, val, ref, ndx=0, ndy=0, vndx=0, vndy=0, band=0):
        # A standing part bridging the two eyelet rows. Every family keeps the
        # body vocabulary it uses horizontally — a vertical film cap is a
        # square-cornered rectangle, a vertical resistor an end-banded rounded
        # body — so a builder can still tell R from C by shape when the part is
        # turned through 90 degrees.
        h = 40
        w = 15
        x, y = cx - w / 2, cy - h / 2
        els = []
        fill, edge, rx = RES_BODY, RES_END, 6.0
        if cat == "electro":
            fill, edge = ELEC_BODY, ELEC_EDGE
        elif cat == "film":
            fill, edge, rx = FILM_BODY, FILM_EDGE, 1.5
            w = 17
            x = cx - w / 2
        elif cat == "mica":
            fill, edge, rx = MICA_BODY, MICA_EDGE, 1.5
            w = 17
            x = cx - w / 2
        elif cat == "diode":
            fill, edge, rx = DIODE_BODY, DIODE_EDGE, 2.5
        els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                   f'rx="{fmt(rx)}" fill="{fill}" stroke="{edge}" stroke-width="1"/>')
        if cat == "electro":
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(y + 7)}" x2="{fmt(x + w)}" '
                       f'y2="{fmt(y + 7)}" stroke="{ELEC_EDGE}" stroke-width="1"/>')
        elif cat == "film":
            els.append(f'<line x1="{fmt(x + 2)}" y1="{fmt(cy)}" x2="{fmt(x + w - 2)}" '
                       f'y2="{fmt(cy)}" stroke="{FILM_EDGE}" stroke-width="0.8" '
                       f'opacity="0.7"/>')
        elif cat == "diode":
            if band:
                byy = (y + 2.5) if band < 0 else (y + h - 6.5)
                els.append(f'<rect x="{fmt(x + 1.5)}" y="{fmt(byy)}" '
                           f'width="{fmt(w - 3)}" height="4" fill="{DIODE_BAND}"/>')
        elif cat != "mica":
            for ey_ in (y + 5, y + h - 5):
                els.append(f'<line x1="{fmt(x+1)}" y1="{fmt(ey_)}" x2="{fmt(x+w-1)}" y2="{fmt(ey_)}" '
                           f'stroke="{RES_END}" stroke-width="2"/>')
        # label sits to the right, except near the right board edge where it
        # would overflow — then flip it to the left.
        if cx > self.board_x + self.board_w - 64:
            lx, anchor = cx - w / 2 - 6, "end"
        else:
            lx, anchor = cx + w / 2 + 6, "start"
        self.obst_rect(x, y, x + w, y + h, f"{ref} body")
        labs = [self.lab(lx + ndx, cy - 3 + ndy, ref, BOARD_REF, 11.5, weight=700,
                         anchor=anchor, spacing="0.02em", tag=f"{ref} ref",
                         group=f"part:{ref}", keep_in=self.board_box(),
                         halo=BOARD, halo_width=3.0, owner=f"{ref} body"),
                self.lab(lx + ndx + vndx, cy + 11 + ndy + vndy, val, BOARD_VAL, 11,
                         anchor=anchor, font=FONT_MONO, weight=600, tag=f"{ref} value",
                         group=f"part:{ref}", keep_in=self.board_box(),
                         halo=BOARD, halo_width=2.8, owner=f"{ref} body")]
        return els, labs

    # ---- off-board stubs ----------------------------------------------------
    def off_pos(self, item):
        edge = item.get("edge", "bottom")
        at = float(item.get("at", 0))
        if edge in ("top", "bottom"):
            x = self.ex(at)
            # Both off-board rows are anchored to their nearest EYELET ROW, not
            # to the board rect: the board's top padding is a legibility
            # parameter (BOARD_TOP_PAD) and must not move a pot or jack
            # relative to the eyelets its leads land on.
            y = (self.ey(0) - 128) if edge == "top" else (self.ey(self.rows - 1) + 116)
        elif edge == "left":
            x = self.board_x - 78
            y = self.ey(0) + at * ROWGAP
        else:  # right
            x = self.board_x + self.board_w + 78
            y = self.ey(0) + at * ROWGAP
        return x, y

    def _edge_safe(self, cx, s, size, mono, pad=12):
        """Placement for a label centred at cx that must stay inside the canvas.
        Keeps it centred when it fits; otherwise right- or left-aligns it to the
        near border so a long sublabel (e.g. an off-board transformer on the
        right edge) is never clipped. Returns (x, anchor)."""
        halfw = len(str(s)) * size * (0.6 if mono else 0.55) / 2
        if cx + halfw > self.width - pad:
            return self.width - pad, "end"
        if cx - halfw < pad:
            return pad, "start"
        return cx, "middle"

    def off_stub(self, item):
        """An off-board item. Returns (glyph_svg, label_svg): the glyph is drawn
        with the rest of the board geometry, the label in the FINAL text pass so
        nothing — including the top-layer heater twisted pairs — can paint over
        it. Label bands sit AWAY from the board (see _label_side), clear of the
        item's own terminal row and lead fan."""
        kind = item.get("kind", "tube")
        label = item.get("label", item.get("id", ""))
        ref = item.get("ref")
        x, y = self.off_pos(item)
        val = (body_value(primary_value(self.bom_for(ref)["value"])) if ref
               else body_value(annotation_value(item) or "") or None)
        sgn = self._label_side(item)
        els: list[str] = []
        labs: list[str] = []
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
                # pin number, just inside the ring (socket chrome, not a board
                # label — deliberately not measured by the label lint)
                nx = x + (r - 8.5) * math.sin(theta)
                ny = y - (r - 8.5) * math.cos(theta)
                els.append(text(nx, ny + 3, str(pin), FAINT, 7.5, font=FONT_MONO, weight=600))
            self.obst_circle(x, y, r, f"socket {item.get('id', '')}")
            # tube-socket ID label: opaque halo AND the final text pass, so a
            # heater twisted pair routed close under the socket reads behind
            # the text instead of cutting through it.
            lab_y = (y - r - 8) if sgn < 0 else (y + r + 15)
            labs.append(self.lab(x, lab_y, label, INK, 12, spacing="0.05em",
                                 halo=WELL, halo_width=3.2,
                                 tag=f"socket {item.get('id', '')}",
                                 group=f"tube:{item.get('id', '')}",
                                 keep_in=self.canvas_box()))
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
                self.obst_circle(lx, ly, 1.9, f"lug {item.get('id', '')}.{lug}")
            self.obst_circle(x, y, r, f"pot {item.get('id', '')}")
            # Name + value sit on the side of the pot AWAY from the board. A
            # top-edge pot's three lugs are on its lower face and every lead it
            # carries fans down from them, so the old below-the-glyph band was
            # struck by the pot's own wiring by construction; above the glyph it
            # is clear. Halo kept (an opaque well-coloured outline) for the
            # crossings that remain, and the nudges stay as the escape hatch.
            lnx, lny = (item.get("label_nudge") or [0, 0])[:2]
            vnx, vny = (item.get("value_nudge") or [0, 0])[:2]
            if sgn < 0:
                lab_y, val_y = y - r - 21, y - r - 8
            else:
                lab_y, val_y = y + r + 14, y + r + 27
            labs.append(self.lab(x + lnx, lab_y + lny, label, INK, 11.5,
                                 spacing="0.04em", halo=WELL, halo_width=3.2,
                                 tag=f"pot {item.get('id', '')} name",
                                 group=f"pot:{item.get('id', '')}",
                                 keep_in=self.canvas_box()))
            if val:
                labs.append(self.lab(x + lnx + vnx, val_y + lny + vny, val, MUTED,
                                     10.5, font=FONT_MONO, weight=500, halo=WELL,
                                     halo_width=3.0,
                                     tag=f"pot {item.get('id', '')} value",
                                     group=f"pot:{item.get('id', '')}",
                                     keep_in=self.canvas_box()))
        elif kind == "jack":
            r = 9
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{WELL}" '
                       f'stroke="{MUTED}" stroke-width="1.6"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{MUTED}"/>')
            self.obst_circle(x, y, r, f"jack {item.get('id', '')}")
            lab_y = (y - r - 8) if sgn < 0 else (y + r + 13)
            labs.append(self.lab(x, lab_y, label, MUTED, 10.5, spacing="0.03em",
                                 halo=WELL, halo_width=3.0,
                                 tag=f"jack {item.get('id', '')}",
                                 group=f"jack:{item.get('id', '')}",
                                 keep_in=self.canvas_box()))
        elif kind in ("xfmr", "choke"):
            # Iron letters its IDENTITY beside the glyph — a factory part number,
            # an impedance ratio, an inductance — and sends anything the parts
            # list adds to that (a measured DCR estimate, a provenance note) to a
            # footnote. See iron_value(): those strings are sentences, and on the
            # 5E5-A one of them was lettered clean off the left edge of the page.
            if ref:
                val = iron_value(self.bom_for(ref)["value"], self.iron.get(ref))[0]
            w, h = (46, 56) if kind == "xfmr" else (40, 34)
            els.append(f'<rect x="{fmt(x-w/2)}" y="{fmt(y-h/2)}" width="{w}" height="{h}" rx="4" '
                       f'fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>')
            for dx in (-6, 0, 6):
                els.append(f'<line x1="{fmt(x+dx)}" y1="{fmt(y-h/2+5)}" x2="{fmt(x+dx)}" '
                           f'y2="{fmt(y+h/2-5)}" stroke="{FAINT}" stroke-width="1.4"/>')
            self.obst_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                           f"{kind} {item.get('id', '')}")
            # coloured pigtails for each lead colour wired to this transformer
            for colour in self.xfmr_leads.get(item.get("id"), []):
                ex_, ey_, base = self.xfmr_lead_pos(item, colour)
                wc = colour_hex(lead_base(colour))
                els.append(f'<line x1="{fmt(base[0])}" y1="{fmt(base[1])}" x2="{fmt(ex_)}" '
                           f'y2="{fmt(ey_)}" stroke="{wc}" stroke-width="2.6" '
                           f'stroke-linecap="round"/>')
                els.append(term_dot(ex_, ey_, 2.4))
                self.obst_circle(ex_, ey_, 2.4, f"pigtail {item.get('id', '')}.{colour}")
                self._lead_callout(item, colour, ex_, ey_, base, MUTED, BOARD)
            # Edge-safe placement: an off-board transformer near a side border can
            # carry a sublabel wider than the gap to the canvas edge (the OT on the
            # right edge). Keep the pair centred under the body where it fits; when
            # the value would overflow, align the whole pair to the near border so
            # nothing is clipped.
            lab_x, lab_anchor = x, "middle"
            val_x, val_anchor = x, "middle"
            if val:
                val_x, val_anchor = self._edge_safe(x, val, 10.5, True)
                if val_anchor != "middle":
                    lab_x, lab_anchor = val_x, val_anchor
            # Same halo treatment as the pot and socket labels, and the same
            # away-from-the-board band: a top-edge transformer stacks its
            # coloured pigtails and their terminal dots on its lower face, which
            # is exactly where the label used to be printed.
            if sgn < 0:
                lab_y, val_y = y - h / 2 - 27, y - h / 2 - 14
            else:
                lab_y, val_y = y + h / 2 + 14, y + h / 2 + 27
            labs.append(self.lab(lab_x, lab_y, label, INK, 11.5, spacing="0.04em",
                                 anchor=lab_anchor, halo=WELL, halo_width=3.2,
                                 tag=f"{kind} {item.get('id', '')} name",
                                 group=f"{kind}:{item.get('id', '')}",
                                 keep_in=self.canvas_box()))
            if val:
                labs.append(self.lab(val_x, val_y, val, MUTED, 10.5, font=FONT_MONO,
                                     weight=500, anchor=val_anchor, halo=WELL,
                                     halo_width=3.0,
                                     tag=f"{kind} {item.get('id', '')} value",
                                     group=f"{kind}:{item.get('id', '')}",
                                     keep_in=self.canvas_box()))
        elif kind == "part":
            g, l = self._part_glyph(item, x, y, label, val)
            els += g
            labs += l
        else:  # switch / fuse / misc
            w, h = 34, 18
            els.append(f'<rect x="{fmt(x-w/2)}" y="{fmt(y-h/2)}" width="{w}" height="{h}" rx="4" '
                       f'fill="{PANEL}" stroke="{LINE}" stroke-width="1.4"/>')
            self.obst_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                           f"{kind} {item.get('id', '')}")
            lab_y = (y - h / 2 - 8) if sgn < 0 else (y + h / 2 + 13)
            labs.append(self.lab(x, lab_y, label, MUTED, 10.5, spacing="0.03em",
                                 halo=WELL, halo_width=3.0,
                                 tag=f"{kind} {item.get('id', '')}",
                                 group=f"{kind}:{item.get('id', '')}",
                                 keep_in=self.canvas_box()))
        return "".join(els), "".join(labs)

    def _part_glyph(self, item, x, y, label, val):
        """Generic off-board 2-lead part (kind: part): a pilot lamp (glyph:
        lamp) or a small axial body, with two board-facing terminals wired as
        REF.a / REF.b. Returns (glyph_els, label_els)."""
        edge = item.get("edge", "top")
        away = {"top": (0, -1), "bottom": (0, 1),
                "left": (-1, 0), "right": (1, 0)}.get(edge, (0, -1))
        ta = self.part_terminal_pos(item, "a")
        tb = self.part_terminal_pos(item, "b")
        els: list[str] = []
        labs: list[str] = []
        pid = item.get("id", "")
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
            self.obst_circle(bx, by, 9.5, f"lamp {pid}")
            self.obst_rect(cbx - 9.7, cby - 6, cbx + 9.7, cby + 6, f"lamp base {pid}")
            laby = by - 15 if away[1] < 0 else by + 24
            labs.append(self.lab(bx, laby, label, INK, 11.5, spacing="0.04em",
                                 halo=WELL, halo_width=3.2, tag=f"part {pid}",
                                 group=f"off:{pid}", keep_in=self.canvas_box()))
            for (tx, ty) in (ta, tb):
                els.append(term_dot(tx, ty, 2.2))
                self.obst_circle(tx, ty, 2.2, f"terminal {pid}")
            return els, labs
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
            self.obst_rect(rx, ry, rx + bw, ry + bh, f"part {pid} body")
            # ref above value in BOTH directions — a bottom-edge part used to
            # print its value above its designator, the only place in the corpus
            # where the pair read upside down.
            top = away[1] < 0
            ref_y = (ry - 18) if top else (ry + bh + 11)
            val_y = (ry - 5) if top else (ry + bh + 24)
            labs.append(self.lab(midx, ref_y, label, INK, 11.5, weight=700,
                                 spacing="0.02em", halo=WELL, halo_width=3.2,
                                 tag=f"part {pid} ref", group=f"off:{pid}",
                                 keep_in=self.canvas_box()))
            if val:
                labs.append(self.lab(midx, val_y, val, MUTED, 10.5, font=FONT_MONO,
                                     weight=500, halo=WELL, halo_width=3.0,
                                     tag=f"part {pid} value", group=f"off:{pid}",
                                     keep_in=self.canvas_box()))
        else:
            bw, bh = 15.0, max(22.0, abs(tb[1] - ta[1]) - 8)
            rx, ry = midx - bw / 2, midy - bh / 2
            els.append(f'<rect x="{fmt(rx)}" y="{fmt(ry)}" width="{fmt(bw)}" height="{fmt(bh)}" '
                       f'rx="6" fill="{RES_BODY}" stroke="{RES_END}" stroke-width="1"/>')
            self.obst_rect(rx, ry, rx + bw, ry + bh, f"part {pid} body")
            lx = midx + away[0] * 16
            anchor = "end" if away[0] < 0 else "start"
            labs.append(self.lab(lx, midy - 3, label, INK, 11.5, weight=700, anchor=anchor,
                                 spacing="0.02em", halo=WELL, halo_width=3.2,
                                 tag=f"part {pid} ref", group=f"off:{pid}",
                                 keep_in=self.canvas_box()))
            if val:
                labs.append(self.lab(lx, midy + 11, val, MUTED, 10.5, anchor=anchor,
                                     font=FONT_MONO, weight=500, halo=WELL,
                                     halo_width=3.0, tag=f"part {pid} value",
                                     group=f"off:{pid}", keep_in=self.canvas_box()))
        for (tx, ty) in (ta, tb):
            els.append(term_dot(tx, ty, 2.2))
            self.obst_circle(tx, ty, 2.2, f"terminal {pid}")
        return els, labs

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
        pts = _clean_polyline(pts)
        if str(spec.get("style", "")).lower() == "twisted":
            pts = self._socket_keepout(pts)
        return pts

    # ---- socket keep-out (heater routing) -----------------------------------
    # The 6.3 V pair is the topmost layer by design — it has to show its pin
    # landings — so anything it crosses it also knocks out. Routed straight
    # from pin to pin it therefore crossed the socket's own interior on every
    # 9-pin valve in the corpus, wiping out pin numerals and the caption under
    # the socket. A real harness never does that: it leaves the lug and turns
    # away, running around the socket's flank. This pass makes the drawing do
    # the same — the pin ring, its numerals and its caption band are a keep-out
    # the heater router deflects around, tangentially, with no change to which
    # pins the pair lands on (so the equivalence gate sees exactly the same
    # net) and none to any other run.
    SOCKET_KEEPOUT = 12.0     # clear ring outside the socket's outer circle

    def _sockets(self):
        out = []
        for it in self.offboard:
            if it.get("kind") != "tube":
                continue
            cx, cy = self.off_pos(it)
            out.append((cx, cy, TUBE_R + 5 + self.SOCKET_KEEPOUT))
        return out

    def _socket_keepout(self, pts):
        sockets = self._sockets()
        if not sockets or len(pts) < 2:
            return pts
        for _ in range(4):                     # bounded, deterministic
            new = [pts[0]]
            changed = False
            for k in range(len(pts) - 1):
                p, q = pts[k], pts[k + 1]
                det = _deflect_around(p, q, sockets)
                if det:
                    new.extend(det)
                    changed = True
                new.append(q)
            pts = _clean_polyline(new)
            if not changed:
                break
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
        # off-board stubs and board parts, GEOMETRY only: every label they own
        # is QUEUED (see lab()) and resolved in the final text pass below, once
        # every wire, body and terminal dot is known.
        for it in self.offboard:
            geom, _ = self.off_stub(it)
            els.append(geom)
        for p in self.parts:
            geom, _ = self.part_body(p)
            els.append(geom)
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
            self.obst_circle(tx, ty, 4.4, "solder joint")
        # FINAL TEXT PASS — every board and off-board label, drawn last so
        # nothing can paint over it. The twisted heater pair is the top wiring
        # layer by design (it must show its pin landings), so a label emitted
        # with the glyph it belongs to was painted over by the heaters however
        # good its halo: a halo can only protect against what is drawn BEFORE
        # the text. Labels now come after every wire, and keep their halos for
        # the crossings that remain. Placement is resolved here too, against the
        # finished geometry, so a label lands in air by measurement rather than
        # by hand-authored nudge.
        wires = [(f"run[{r['i']}]", r["pts"]) for r in runs if r["pts"]]
        wires += [(f"bus[{b['j']}]", b["pts"]) for b in bus if b["pts"]]
        els.append(self._emit_labels(wires))
        # title + attribution
        title = (self.layout.get("board", {}) or {}).get("title") or f"{self.amp_id.upper()} board layout"
        ts = self.cz(17)
        self.chrome_text(els, bx, 20 + ts, title, INK, ts, font=FONT_DISP,
                         weight=600, spacing="0.08em", tag="chrome title")
        # attribution, footnotes and the legends, as one measured stack
        self._draw_footer(els)
        body = "\n".join(els)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(self.width)} '
               f'{fmt(self.height)}" role="img" aria-label="{esc(title)} — redrawn board '
               f'layout diagram" width="100%" font-family="{FONT_DISP}">\n'
               f'<rect x="0" y="0" width="{fmt(self.width)}" height="{fmt(self.height)}" '
               f'fill="{WELL}"/>\n{body}\n</svg>\n')
        if self.errors:
            raise ValueError(f"{self.amp_id}: layout errors: {self.errors}")
        return svg


# ==================== sheet style — era drafting idiom (--style sheet) =======
# A STYLE-ONLY re-skin of the same geometry: SheetRenderer inherits every
# coordinate, endpoint resolution, run polyline, hop-over and label-placement
# code path from Renderer and overrides nothing but paint. It emits to a
# PARALLEL file (amps/<id>/layout-sheet.svg); the default house render, the
# collision lint and the layout↔netlist equivalence gate are untouched.
#
# The idiom is the era factory layout sheet's general drafting style (never any
# specific sheet's artwork — hard rule 1 applies to style exactly as to facts):
# cream aged-paper ground, near-black ink, component OUTLINES with the value
# written on the body, dogbone resistors, tube sockets as plain double circles
# with pin dots + numbers, pots rear-view with three lug tabs, and the board as
# a strong double-line rectangle dominating the sheet. Era wire colours stay
# (they are period fact), ink-weighted for the light ground.

SH_PAPER = "#e9dcba"          # aged cream ground
SH_BOARD = "#e2d2a9"          # board interior, one tone darker than the page
SH_BODY = "#f0e6c8"           # component fill — lifts the outline off the board
SH_INK = "#211c13"            # near-black drafting ink
SH_INK2 = "#4c4132"           # secondary ink (values, pin numbers)
SH_FAINT = "#8d7f63"          # faint ink (unused eyelets, attribution)
SH_BUS_CORE = "#d9c99e"       # bare bus rod interior (hollow double-line)

# Era wire colours, ink-weighted for a cream ground: darker and drier than the
# house palette (which is tuned for a dark well). "black" is literal here.
SHEET_WIRE = {
    "black":        "#262119",
    "brown":        "#5f4126",
    "red":          "#9c2f23",
    "orange":       "#a85a14",
    "yellow":       "#8a6d10",
    "green":        "#2f6b30",
    "blue":         "#2d5787",
    "violet":       "#634a85",
    "purple":       "#634a85",
    "grey":         "#6e6a5e",
    "gray":         "#6e6a5e",
    "white":        "#948b76",
    "red-yellow":   "#9c5a1e",
    "green-yellow": "#7d8a1c",
    "blue-white":   "#54779c",
    "red-blue":     "#7e3f63",
}
# An UNCOLOURED hookup lead is a different claim from a lead the drawing marks
# BLACK, so the two must not be the same ink. They were #2b261c and #262119 —
# indistinguishable, which made the legend's separate "lead" and "black" rows
# meaningless. The generic lead is now a warm graphite, clearly lighter than
# the literal black above.
SH_NEUTRAL = "#57503f"        # uncoloured hookup lead = warm graphite
SH_HEATER = "#3c672f"
SH_HEATER_CT = "#7d8a1c"      # centre-tap strand: pushed to olive, clear of green
# Clear space (px) reserved for an electrolytic's '+' mark inside its body, so
# the polarity mark and the value never share a line. See plus_mark().
PLUS_GUTTER = 17.0


# ---- era value lettering (SHEET STYLE ONLY) --------------------------------
# House units style is unchanged everywhere else — pages, BOMs, the default
# render all keep "0.02 µF · 400 V" and "4.7 kΩ · ½ W". The era layout sheets
# had no parts-list column at all: a part's value was hand-lettered ON the part,
# compressed onto one short line. This archive already documents that shorthand
# for readers, on /reference/guides/units-conventions/ ("Reading the shorthand
# on the original drawings"), and era_pair() letters exactly what that page
# describes:
#
#   resistors  bare number with a K or MEG suffix — 820 Ω -> "820",
#              15 kΩ -> "15K", 4,700 Ω -> "4.7K", 1 MΩ -> "1MEG". A wattage
#              suffix only where the part is bigger than the sheet's implied
#              ½ W, in the era's ohms–watts dash form: 250 Ω · 5 W -> "250-5".
#   film /
#   mica caps  value–voltage joined by a dash, µF written as a bare decimal
#              with no leading zero: 0.02 µF · 400 V -> ".02-400", 0.005 µF
#              -> ".005". Sub-nanofarad parts are lettered in picofarads, as
#              the era wrote them: 250 pF -> "250PF", 0.0005 µF -> "500PF".
#   electros   microfarads lettered MFD (the µ symbol was awkward on a drafting
#              pen): 25 µF -> "25MFD", with the working voltage on its own
#              line under it ("450V") — the can is tall enough for two.
#
#   dual cans  one part, two capacitances: the sections are joined by a slash
#              and the unit written once — 25 µF + 25 µF -> "25/25MFD", exactly
#              as the era sheets lettered a twin can.
#
# It is deliberately STRICT: a token it cannot parse as a resistance or a
# capacitance comes back untouched, so descriptive values keep the house
# wording ("selenium", "Fender 125P1B · 320-0-320 V", "presence/NFB network").
# It is applied ONLY to values lettered on a component body — board parts and
# the off-board part glyphs, which are the same dogbones and cans drawn beside
# the board. Free-standing hardware labels keep house units: a pot's value
# carries a taper suffix ("250 kΩ-A") and a transformer's is a part number, and
# neither is a body lettering. Nothing outside SheetRenderer calls this.
#
# What the strictness must NOT become is a licence to letter a sentence. A value
# era_pair() refuses comes back as the house string, and a house string can be a
# whole clause ("selenium (silicon diode in modern builds)"), a repeat count
# ("8 µF · 150 V (×2)") or a measured estimate ("~110 Ω DCR (est.)"). Lettered
# verbatim on a 30 px body those ran off the part and, on the 5E4-A, clean off
# the page. So the callers letter body_value() — the value with its parenthetical
# gloss removed — and the parts that carry a rating rather than a quantity
# (transformers, chokes) go through iron_value(), which keeps the identity on the
# drawing and sends the gloss to a numbered footnote. Nothing is dropped: the
# full house string is on the amp page and in bom.yaml, where nothing is cramped.

_ERA_NUM = r"[0-9][0-9,]*(?:\.[0-9]+)?"
_RE_TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")
# The factory value-voltage shorthand ("20-600", ".02-400") inside a house value
# string. era_pair() refuses it; pipeline/test_era_values.py rejects it in bom.yaml.
_RE_VALUE_DASH_PAIR = re.compile(r"\d\s*-\s*\d")
_RE_OHMS = re.compile(rf"^({_ERA_NUM})\s*([kM])?\s*(?:Ω|ohms?)$")
_RE_FARADS = re.compile(rf"^({_ERA_NUM})\s*([µμunp])F$")
_RE_VOLTS = re.compile(rf"^({_ERA_NUM})\s*V\b(.*)$")
_RE_WATTS = re.compile(r"^(\S+)\s*W$")

_OHM_MULT = {None: Decimal(1), "": Decimal(1),
             "k": Decimal(1000), "M": Decimal(1000000)}
_FARAD_MULT = {"µ": Decimal("1E-6"), "μ": Decimal("1E-6"), "u": Decimal("1E-6"),
               "n": Decimal("1E-9"), "p": Decimal("1E-12")}
# Vulgar fractions as the BOMs write them ("½ W", "¾ A").
_FRACTIONS = {"½": Decimal("0.5"), "¼": Decimal("0.25"), "¾": Decimal("0.75"),
              "⅓": Decimal(1) / Decimal(3), "⅔": Decimal(2) / Decimal(3),
              "⅛": Decimal("0.125")}
# The sheets' own footnote states the standard resistor wattage once ("all
# resistors are one-half watt … unless otherwise noted"), so only a part ABOVE
# it earns a per-part wattage suffix.
_IMPLIED_WATTS = Decimal("0.5")


def _era_decimal(tok: str) -> Decimal | None:
    """'4,700' / '0.02' / '½' -> Decimal, or None if it is not a number."""
    s = str(tok).strip().replace(",", "")
    if s in _FRACTIONS:
        return _FRACTIONS[s]
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _era_number(d: Decimal) -> str:
    """Decimal -> shortest exact lettering: 4.7 -> '4.7', 820 -> '820'."""
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _parse_ohms(tok: str) -> Decimal | None:
    m = _RE_OHMS.match(str(tok).strip())
    if not m:
        return None
    n = _era_decimal(m.group(1))
    return None if n is None else n * _OHM_MULT[m.group(2)]


def _parse_farads(tok: str) -> Decimal | None:
    m = _RE_FARADS.match(str(tok).strip())
    if not m:
        return None
    n = _era_decimal(m.group(1))
    return None if n is None else n * _FARAD_MULT[m.group(2)]


def _era_ohms(ohms: Decimal) -> str:
    if ohms >= 1000000:
        return _era_number(ohms / Decimal(1000000)) + "MEG"
    if ohms >= 1000:
        return _era_number(ohms / Decimal(1000)) + "K"
    return _era_number(ohms)


def _era_farads(farads: Decimal, cat: str) -> str:
    if farads < Decimal("1E-9"):          # under 1000 pF: the era wrote pF
        return _era_number(farads / Decimal("1E-12")) + "PF"
    micro = farads / Decimal("1E-6")
    if cat == "electro" or micro >= 1:
        # MFD spelled out — and a bare "25" on a can would read as a resistor
        return _era_number(micro) + "MFD"
    return _era_number(micro).lstrip("0")  # ".02" — the era dropped the zero


# A repeat COUNT — "(×2)", "(x3)" — is not part of a value: it says how many of
# this identical part the drawing calls for. Lettered into the working-voltage
# line it produced "150V (×2)" on an 8 µF can, which reads as a second rating.
# It comes off the value here and is lettered as the era sheets lettered it, in
# its own line beside the part: "2 REQ'D". See era_count().
_RE_COUNT_PAREN = re.compile(r"\(\s*[x×]\s*(\d+)\s*\)")
# A multi-section can: one part, two (or three) capacitances, written in house
# units as "25 µF + 25 µF". Refusing it lettered the house string verbatim onto
# a 34 px can; the era sheets wrote "25/25MFD".
_RE_SECTION_SPLIT = re.compile(r"\s*\+\s*")


def part_count(value: str) -> int | None:
    """How many identical parts a house value calls for — '8 µF · 150 V (×2)'
    -> 2 — or None when it states no count (which means one)."""
    m = _RE_COUNT_PAREN.search(str(value))
    return int(m.group(1)) if m else None


def era_count(value: str) -> str | None:
    """The era's repeat-count lettering: '8 µF · 150 V (×2)' -> "2 REQ'D"."""
    n = part_count(value)
    return f"{n} REQ'D" if n else None


def _strip_count(text: str) -> str:
    return _RE_COUNT_PAREN.sub("", str(text)).strip()


def _parse_sections(tok: str) -> tuple[Decimal, ...] | None:
    """('25 µF + 25 µF') -> (25e-6, 25e-6); None when it is not a section vector.

    Every section must carry its own unit in house units — this reads bom.yaml,
    whose grammar gate (test_era_values.grammar_errors) already requires that —
    so nothing here has to guess which half an omitted unit belonged to."""
    parts = [p.strip() for p in _RE_SECTION_SPLIT.split(str(tok).strip()) if p.strip()]
    if len(parts) < 2:
        return None
    out = []
    for p in parts:
        q = _parse_farads(p)
        if q is None:
            return None
        out.append(q)
    return tuple(out)


def body_value(value: str) -> str:
    """The house-units value as it is LETTERED ON A PART, gloss removed.

    A parenthetical in a BOM value is an aside for a reader with a page in front
    of them — a modern-substitute note ('selenium (silicon diode in modern
    builds)'), a restatement in the other unit ('0.0005 µF (500 pF)'), a
    provenance note ('≈4.1 kΩ : 8 Ω (est. for 2×6L6GB into one 15-in speaker)').
    None of it fits on a component body, and lettered there it pushed the value
    off the part and, on two boards, off the page. The drawing letters the value;
    bom.yaml and the amp page keep the whole sentence."""
    s = _RE_TRAILING_PAREN.sub("", str(value).strip()).strip()
    return s or str(value).strip()


# A choke's or transformer's parts-list value is whatever the drawing printed:
# a factory part number, an impedance ratio, an inductance — or, where the corpus
# had to measure rather than read, a DC resistance marked as an estimate. The
# first three IDENTIFY or RATE the part and belong on the drawing beside it. A
# DCR estimate does neither: it is a measurement note, it is the one field a
# builder must not mistake for a winding spec, and lettered under a 40 px choke
# glyph on the 5E5-A it ran off the left edge of the page. It goes to a footnote.
_RE_DCR = re.compile(r"^[≈~]?\s*[\d.,]+\s*(?:k|M)?\s*(?:Ω|ohms?)\s*DCR\b", re.I)


def iron_value(value: str, extra: str | None = None) -> tuple[str | None, str | None]:
    """A transformer's or choke's label -> (drawn beside the glyph, footnote).

    `extra` is the amp's meta.yaml `iron:` entry for this designator — the
    electrical rating for a part whose parts-list value is a bare factory number
    ("Fender 45216"). A drawing that names only a part number tells a builder
    nothing about what to wind or buy, so where the corpus HAS read the rating it
    is lettered with the number. Where it has not, nothing is invented: the
    number stands alone and the gap is visible."""
    raw = str(value).strip()
    if not raw:
        return (None, None)
    rating = str(extra).strip() if extra and str(extra).strip() else None
    ident = body_value(raw.split("·")[0].strip())
    if _RE_DCR.match(ident):
        ident = None                    # a measurement note is not an identity
    if ident and rating:
        ident = f"{ident} · {rating}"
    elif rating:
        ident = rating
    # The footnote carries the WHOLE house claim whenever the drawing shows less
    # than all of it, so nothing the parts list states is lost by being drawn.
    note = None if (ident and raw in ident) else raw
    return (ident, note)


def era_pair(value: str, cat: str) -> tuple[str, str | None]:
    """House BOM value string -> (body lettering, second line or None).

    Falls back to the house tokens (first '·' field, second field) for anything
    that is not a plain resistance or capacitance, so this never invents or
    mangles a value it does not understand. See the block comment above."""
    toks = [t.strip() for t in str(value).split("·")]
    house = (body_value(toks[0]), body_value(toks[1]) if len(toks) > 1 else None)
    prim = _strip_count(_RE_TRAILING_PAREN.sub("", toks[0]).strip())  # '0.0005 µF (500 pF)'
    rest = toks[1:]

    # Refuse a half-parse. The era shorthand packs value and working voltage into
    # one dashed token ("20-600" = 20 µF at 600 V), and that shorthand belongs to
    # the LETTERING, never to the house value string. Left in `value`, it used to
    # come apart into nonsense: "30-450 µF · 450 V" lettered as "30-450 µF" over a
    # "450 V" second line — one part claiming two different working voltages. A
    # number this function cannot read whole is a number it must not letter at all.
    if _RE_VALUE_DASH_PAIR.search(prim):
        return house

    ohms = _parse_ohms(prim)
    if ohms is not None:
        letter = _era_ohms(ohms)
        for t in rest:
            mw = _RE_WATTS.match(t)
            w = _era_decimal(mw.group(1)) if mw else None
            if w is not None and w > _IMPLIED_WATTS:
                letter += "-" + _era_number(w)
                break
        return letter, None

    farads = _parse_farads(prim)
    sections = None if farads is not None else _parse_sections(prim)
    if farads is not None or sections is not None:
        if sections is not None:
            # A twin can is ONE part with two capacitances: the era sheets
            # lettered "25/25MFD", unit written once. Sections keep the order
            # the parts list states them in — that order is the corpus's claim
            # about which section does which job.
            letter = "/".join(_era_number(s / Decimal("1E-6")) for s in sections) + "MFD"
        else:
            letter = _era_farads(farads, cat)
        volts = tail = None
        for t in rest:
            mv = _RE_VOLTS.match(_strip_count(t))
            if mv and _era_decimal(mv.group(1)) is not None:
                volts, tail = _era_number(_era_decimal(mv.group(1))), mv.group(2)
                break
        if cat == "electro" or sections is not None:
            return letter, (f"{volts}V{tail}" if volts else None)
        if volts and not tail.strip():
            return f"{letter}-{volts}", None      # ".02-400"
        return letter, (house[1] if volts else None)

    return house


def sheet_eyelet(x, y, r=3.8):
    return (f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{SH_BODY}" '
            f'stroke="{SH_INK}" stroke-width="1.1"/>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="1.5" fill="none" '
            f'stroke="{SH_INK}" stroke-width="0.7"/>')


def sheet_term(x, y, r=2.4):
    return f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{SH_INK}"/>'


def sheet_solder(x, y):
    """Run-endpoint solder joint in ink: a solid dot inside a fine ring —
    unmistakably a termination, never a passing wire."""
    return (f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="4.5" fill="none" '
            f'stroke="{SH_INK}" stroke-width="1.0"/>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="2.9" fill="{SH_INK}"/>')


def plus_mark(cx, cy, arm, ink, width=1.5):
    """The electrolytic polarity '+', drawn as a placed MARK with its own
    clear space — never inline with the value. Set inline it collided with the
    first digit on every narrow can in the corpus and the pair read as '±'."""
    return [f'<line x1="{fmt(cx - arm)}" y1="{fmt(cy)}" x2="{fmt(cx + arm)}" '
            f'y2="{fmt(cy)}" stroke="{ink}" stroke-width="{fmt(width)}"/>',
            f'<line x1="{fmt(cx)}" y1="{fmt(cy - arm)}" x2="{fmt(cx)}" '
            f'y2="{fmt(cy + arm)}" stroke="{ink}" stroke-width="{fmt(width)}"/>']


def dogbone_path(cx, cy, w, r_end=8.6, waist=5.6):
    """Closed dogbone outline (two round ends, straight waist) centred at
    (cx, cy), overall width w — the era hand-drafted resistor body. The end
    radius is clamped so the waist never inverts: a body too short for a true
    dogbone degrades gracefully into a fat oval (also period)."""
    r_e = max(3.5, min(r_end, w / 2 - 6.6))
    waist_e = max(2.0, min(waist, r_e - 1.2))
    half = w / 2
    lcx, rcx = cx - half + r_e, cx + half - r_e
    t = math.sqrt(max(r_e * r_e - waist_e * waist_e, 0.0))
    x0, x1 = lcx + t, rcx - t
    if x0 > x1:                      # belt and braces: never emit a bowtie
        x0 = x1 = cx
    return (f"M {fmt(x0)} {fmt(cy - waist_e)} L {fmt(x1)} {fmt(cy - waist_e)} "
            f"A {fmt(r_e)} {fmt(r_e)} 0 1 1 {fmt(x1)} {fmt(cy + waist_e)} "
            f"L {fmt(x0)} {fmt(cy + waist_e)} "
            f"A {fmt(r_e)} {fmt(r_e)} 0 1 1 {fmt(x0)} {fmt(cy - waist_e)} Z")


class SheetRenderer(Renderer):
    """Era layout-sheet drafting idiom. Same layout.yaml, same geometry —
    only the paint changes. See the block comment above."""

    # The sheet draws a bigger socket (a double circle out to TUBE_R + 5) and
    # letters values on the bodies, so its label bands start from a slightly
    # different standoff than the house drawing's. On a board with a bank of
    # closely spaced parallel runs under the tube row, that shift can put every
    # rung of the house ladder on a wire while a clear lane sits between two of
    # them (the Model 1987's V5 was exactly this). The extra rungs are half
    # steps and longer reaches, appended so the house preferences still win
    # whenever they are clear — the placer breaks on the first zero-cost rung.
    LABEL_LADDER = Renderer.LABEL_LADDER + [
        (0, -6), (0, 6), (0, -17), (0, 17), (0, -27), (0, 27),
        (0, -37), (0, 37), (-24, -27), (24, -27), (-24, 27), (24, 27),
        (0, -52), (0, 52),
    ]

    def __init__(self, layout: dict, bom: dict, amp_id: str):
        super().__init__(layout, bom, amp_id)
        # value-on-body texts: emitted AFTER the queued-label pass so nothing
        # paints over them; they are fixed (a value never leaves its body).
        self._fixed: list[str] = []

    # ---- value helpers ------------------------------------------------------
    def _val_tokens(self, ref):
        """Era body lettering for a part's value — ('.02-400', None) for a film
        cap, ('16MFD', '450V') for a can, ('100K', None) for a resistor. The
        house units string is what everything outside this style prints; see
        era_pair() for the shorthand and for what it refuses to touch."""
        rec = self.bom_for(ref)
        return era_pair(rec["value"], category(rec["part"]))

    def _fits(self, s, size, avail):
        return text_width(s, size) <= avail

    def _fixed_text(self, x, y, s, size, fill=SH_INK, weight=600, halo=SH_BODY,
                    rotate=None):
        t = text(x, y, s, fill, size, weight=weight, halo=halo, halo_width=2.6)
        box = text_box(x, y, s, size)
        if rotate is not None:
            t = f'<g transform="rotate({fmt(rotate)} {fmt(x)} {fmt(y)})">{t}</g>'
            # lettered along the body: the box turns with the glyphs
            box = (x + (box[1] - y), y - (box[2] - x),
                   x + (box[3] - y), y - (box[0] - x))
        self._fixed.append(t)
        # An on-body value is ink on the drawing exactly as the body under it
        # is, so it is registered as an OBSTACLE: the label placer routes queued
        # labels around it, and the lint's label-over-glyph check reports any
        # label that still lands on it. (It is not itself a placed label — it
        # never moves, and it sits on its own body by design.)
        self.obst_rect(box[0], box[1], box[2], box[3], f"value '{s}'")

    def _ref_label(self, cx, cy, ref):
        self.lab(cx, cy, ref, SH_INK2, 8, weight=700, spacing="0.03em",
                 tag=f"{ref} ref", group=f"ref:{ref}", keep_in=self.board_box(),
                 halo=SH_BOARD, halo_width=2.4, owner=f"{ref} body")

    def _below_value(self, cx, cy, ref, val):
        """Fallback for a value that will not fit inside its body: printed just
        below it, queued so the placer keeps it in air (the house behaviour)."""
        self.lab(cx, cy, val, SH_INK2, 9.5, weight=600, tag=f"{ref} value",
                 group=f"ref:{ref}", keep_in=self.board_box(),
                 halo=SH_BOARD, halo_width=2.6, owner=f"{ref} body")

    # ---- board part bodies --------------------------------------------------
    def part_body(self, part):
        ref = part["ref"]
        rec = self.bom_for(ref)
        cat = category(rec["part"])
        v1, v2 = self._val_tokens(ref)
        # A repeat count is lettered as the era sheets lettered it — "2 REQ'D",
        # under the part — instead of riding inside the working-voltage line,
        # where "150V (×2)" read as a second rating on one can.
        cnt = era_count(rec["value"])
        (r1, c1), (r2, c2) = part["a"], part["b"]
        x1, y1 = self.ex(c1), self.ey(r1)
        x2, y2 = self.ex(c2), self.ey(r2)
        vertical = c1 == c2 and r1 != r2
        els = [f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
               f'stroke="{SH_INK}" stroke-width="1.5"/>']
        band = self.cathode_side(part) if cat == "diode" else 0
        if vertical:
            els += self._sheet_body_vertical(cat, x1, (y1 + y2) / 2, v1, v2, ref, band=band)
        else:
            els += self._sheet_body_horizontal(cat, (x1 + x2) / 2, y1,
                                               abs(c2 - c1), v1, v2, ref, band=band)
        els.append(sheet_eyelet(x1, y1))
        els.append(sheet_eyelet(x2, y2))
        self.obst_circle(x1, y1, 4.0, f"eyelet {ref}.a")
        self.obst_circle(x2, y2, 4.0, f"eyelet {ref}.b")
        if cnt:
            cy_ = max(y1, y2) + (26.0 if not vertical else 30.0)
            self.lab((x1 + x2) / 2, cy_, cnt, SH_INK2, 8, weight=600,
                     spacing="0.04em", tag=f"{ref} value", group=f"ref:{ref}",
                     keep_in=self.board_box(), halo=SH_BOARD, halo_width=2.4,
                     owner=f"{ref} body")
        return "".join(els), ""

    def _val_stacked(self, cx, cy, v1, avail, unit="V"):
        """Tight-spot lettering: a two-part value split over two lines inside a
        body too narrow to letter it across — '.02' over '400V'. The era sheets
        did exactly this wherever a cap sat between two close eyelets. The
        second rating regains its unit letter here, because the dash that
        carried its meaning is what the line break replaced. True when placed."""
        if "-" in v1:
            head, tail = v1.split("-", 1)
            tail = f"{tail}{unit}"
        elif len(v1.split()) == 2:
            head, tail = v1.split()          # a house-units value passing through
        else:
            return False
        if not (self._fits(head, 8.5, avail - 5) and self._fits(tail, 8, avail - 5)):
            return False
        self._fixed_text(cx, cy - 1.5, head, 8.5, weight=700)
        self._fixed_text(cx, cy + 8, tail, 8, fill=SH_INK2)
        return True

    def _val_inside(self, cx, cy, v1, avail):
        """Write a value on a body if any size on the ladder fits its interior
        width; True when placed. The era sheets' whole idiom is the value ON
        the part, so the ladder tries hard (down to 8 px) before giving up."""
        for size, pad in ((9.5, 10.0), (8.5, 6.0), (8.0, 4.0)):
            if self._fits(v1, size, avail - pad):
                self._fixed_text(cx, cy + size * 0.36, v1, size, weight=700)
                return True
        return False

    def _sheet_body_horizontal(self, cat, cx, cy, span, v1, v2, ref, band=0):
        # Bodies may run a shade wider than their eyelet span (a real can sits
        # over its eyelets) so the value fits ON the part, as the idiom wants.
        w = max((34.0 if cat == "electro" else 30.0), span * CW - 16)
        els: list[str] = []
        if cat == "electro":
            # filter can: tall outlined body hanging above its row, crimp line,
            # polarity + mark at the positive end, value written on the can.
            # The '+' owns a RESERVED GUTTER along the can's left edge and the
            # value reflows into what is left — set inline (as it was until
            # 2026-08-04) the mark's bar struck the first digit and '+25MFD'
            # read as '±25MFD' on every narrow can in the corpus.
            h = 42
            x, y = cx - w / 2, cy - h + 8
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="5" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.8"/>')
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(y + 6.5)}" x2="{fmt(x + w)}" '
                       f'y2="{fmt(y + 6.5)}" stroke="{SH_INK}" stroke-width="0.9"/>')
            els += plus_mark(x + 7.5, y + 13.5, 3.4, SH_INK, 1.5)
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            gut = PLUS_GUTTER                 # clear space the '+' owns
            vcx, vw = x + gut + (w - gut) / 2, w - gut
            placed = False
            for size in (10.5, 9.5, 9.0):     # beside the '+', sharing its line
                if self._fits(v1, size, vw - 5):
                    self._fixed_text(vcx, y + 22.5, v1, size, weight=700)
                    vs = min(size - 1.5, 9.0)
                    if v2 and self._fits(v2, vs, w - 8):
                        self._fixed_text(cx, y + 34, v2, vs, fill=SH_INK2)
                    placed = True
                    break
            if not placed:
                # too narrow for a side-by-side gutter: the value drops BELOW
                # the '+' band and keeps the full can width — and keeps its
                # voltage line, which the old ladder silently dropped (the
                # JTM45's C16 read '25MFD' while every neighbour on its row
                # carried a working voltage).
                for size in (10.5, 9.5, 8.5, 8.0):
                    if self._fits(v1, size, w - 6):
                        self._fixed_text(cx, y + 26, v1, size, weight=700)
                        vs = min(size - 1.0, 8.5)
                        if v2 and self._fits(v2, vs, w - 6):
                            self._fixed_text(cx, y + 36.5, v2, vs, fill=SH_INK2)
                        placed = True
                        break
            if not placed:
                self._below_value(cx, cy + 22, ref, v1)
            self._ref_label(cx, y - 6, ref)
        elif cat == "diode":
            # a rectifier is polarised: square-cornered body with a cathode
            # band, never the resistor dogbone it used to borrow.
            h = 20.0
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="1.5" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
            bw = 0.0
            if band:
                bxx = (x + 2.5) if band < 0 else (x + w - 7.5)
                els.append(f'<rect x="{fmt(bxx)}" y="{fmt(y + 1.2)}" width="5" '
                           f'height="{fmt(h - 2.4)}" fill="{SH_INK}"/>')
                bw = 11.0
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            vcx = cx + (bw / 2 if band < 0 else -bw / 2)
            if not self._val_inside(vcx, cy, v1, w - bw):
                self._below_value(cx, cy + 22, ref, v1)
            self._ref_label(cx, cy - 17, ref)
        elif cat in ("film", "mica"):
            h = 26.0 if cat == "film" else 18.0
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="2" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
            self.obst_rect(x, y, x + w, y + h, f"{ref} body")
            if cat == "film" and v2 and self._fits(v1, 9.5, w - 8) \
                    and self._fits(v2, 8.5, w - 8):
                self._fixed_text(cx, cy - 2, v1, 9.5, weight=700)
                self._fixed_text(cx, cy + 8.5, v2, 8.5, fill=SH_INK2)
            elif self._val_inside(cx, cy, v1, w):
                pass
            elif cat == "film" and self._val_stacked(cx, cy, v1, w):
                # narrow cap: the value stacks inside the rectangle rather than
                # spilling off the body — see _val_stacked
                pass
            else:
                self._below_value(cx, cy + h / 2 + 12, ref, v1)
            self._ref_label(cx, y - 6, ref)
        else:  # resistor / other: the dogbone
            els.append(f'<path d="{dogbone_path(cx, cy, w)}" fill="{SH_BODY}" '
                       f'stroke="{SH_INK}" stroke-width="1.6"/>')
            self.obst_rect(cx - w / 2, cy - 8.6, cx + w / 2, cy + 8.6, f"{ref} body")
            if not self._val_inside(cx, cy, v1, w):
                self._below_value(cx, cy + 21, ref, v1)
            self._ref_label(cx, cy - 15, ref)
        return els

    def _sheet_body_vertical(self, cat, cx, cy, v1, v2, ref, band=0):
        """A standing part bridging the two eyelet rows — the era sheets drew
        these turned through 90 degrees, keeping each family's own outline.

        Until 2026-08-04 every vertical body was the same rounded pill whatever
        it was, so on a board like the 5F10 — whose mid and right sections are
        almost all standing parts — a builder could not tell a film cap from a
        resistor by shape at all. The vocabulary now matches the horizontal
        bodies: square-cornered rectangle for a film/mica cap, dogbone for a
        resistor, crimped can with a polarity mark for an electrolytic, banded
        body for a rectifier."""
        h = 40.0
        els: list[str] = []
        # (body width, lettering centre offset from cy, lettering length budget)
        if cat in ("film", "mica"):
            # SAME square-cornered rectangle the horizontal film cap gets, just
            # standing: the outline is what distinguishes C from R on the sheet.
            w = 20.0 if cat == "film" else 17.0
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="1.5" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
            voff, budget, cols = 0.0, h, 1
        elif cat == "electro":
            # a standing can: crimp ring and its own polarity gutter at the top,
            # the value lettered up the body below them.
            w = 24.0 if v2 else 19.0
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="4" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.8"/>')
            els.append(f'<line x1="{fmt(x)}" y1="{fmt(y + 8.5)}" x2="{fmt(x + w)}" '
                       f'y2="{fmt(y + 8.5)}" stroke="{SH_INK}" stroke-width="0.9"/>')
            els += plus_mark(cx, y + 4.2, 2.8, SH_INK, 1.4)
            voff, budget, cols = 5.0, h - 12.0, (2 if v2 else 1)
        elif cat == "diode":
            w = 17.0
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                       f'rx="1.5" fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
            if band:
                byy = (y + 3.0) if band < 0 else (y + h - 8.0)
                els.append(f'<rect x="{fmt(x + 1.2)}" y="{fmt(byy)}" width="{fmt(w - 2.4)}" '
                           f'height="5" fill="{SH_INK}"/>')
            voff, budget, cols = 0.0, h - 10.0, 1
        else:                                    # resistor / other: standing dogbone
            w = 18.6
            x, y = cx - w / 2, cy - h / 2
            els.append(f'<g transform="rotate(-90 {fmt(cx)} {fmt(cy)})">'
                       f'<path d="{dogbone_path(cx, cy, h)}" fill="{SH_BODY}" '
                       f'stroke="{SH_INK}" stroke-width="1.6"/></g>')
            voff, budget, cols = 0.0, h, 1
        self.obst_rect(x, y, x + w, y + h, f"{ref} body")
        # lettered ALONG the body, so the size ladder trades against its height
        # (a standing cap is the narrowest body on the sheet and the one whose
        # value most wants to end up in the wiring if it is let off the part).
        col1 = cx + (4.0 if cols > 1 else 0.5)
        for size, pad in ((9, 8.0), (8.5, 6.0), (8, 4.0)):
            if self._fits(v1, size, budget - pad):
                self._fixed_text(col1, cy + voff, v1, size, weight=700, rotate=-90)
                if cols > 1 and self._fits(v2, 8, budget - pad):
                    self._fixed_text(cx - 6.0, cy + voff, v2, 8, fill=SH_INK2, rotate=-90)
                break
        else:
            self._below_value(cx, cy + h / 2 + 12, ref, v1)
        # ref beside the body, flipped near the right board edge (as the house)
        if cx > self.board_x + self.board_w - 64:
            self._ref_label(cx - w / 2 - 14, cy - 12, ref)
        else:
            self._ref_label(cx + w / 2 + 14, cy - 12, ref)
        return els

    # ---- off-board glyphs ---------------------------------------------------
    def off_stub(self, item):
        kind = item.get("kind", "tube")
        label = str(item.get("label", item.get("id", "")))
        ref = item.get("ref")
        x, y = self.off_pos(item)
        val = (body_value(primary_value(self.bom_for(ref)["value"])) if ref
               else body_value(annotation_value(item) or "") or None)
        sgn = self._label_side(item)
        els: list[str] = []
        if kind == "tube":
            r = TUBE_R
            n = int(item.get("_pincount") or 8)
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r + 5)}" '
                       f'fill="{SH_PAPER}" stroke="{SH_INK}" stroke-width="2.0"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="1.1"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="5" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="1.0"/>')
            step = 360.0 / (n + 1)
            for pin in range(1, n + 1):
                theta = math.radians(180 + step * pin)
                px = x + r * math.sin(theta)
                py = y - r * math.cos(theta)
                els.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="2.5" fill="{SH_INK}"/>')
                nx = x + (r - 9) * math.sin(theta)
                ny = y - (r - 9) * math.cos(theta)
                els.append(text(nx, ny + 3, str(pin), SH_INK2, 7.5, weight=600,
                                halo=SH_PAPER, halo_width=2.2))
            self.obst_circle(x, y, r + 5, f"socket {item.get('id', '')}")
            lab_y = (y - r - 13) if sgn < 0 else (y + r + 20)
            self.lab(x, lab_y, label, SH_INK, 12, weight=700, spacing="0.06em",
                     halo=SH_PAPER, halo_width=3.0,
                     tag=f"socket {item.get('id', '')}",
                     group=f"tube:{item.get('id', '')}", keep_in=self.canvas_box())
        elif kind == "pot":
            r = 18
            edge = item.get("edge", "top")
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" '
                       f'fill="{SH_PAPER}" stroke="{SH_INK}" stroke-width="1.8"/>')
            # rear view: cover-plate ring + shaft bushing, no knob/wiper mark
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r - 3.5)}" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="0.7"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="4.4" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="1.1"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="1.4" fill="{SH_INK}"/>')
            for lug in (1, 2, 3):
                lx, ly = self.pot_lug_pos(item, lug)
                # lug TAB: a small rounded tab reaching from the body edge out
                # through the lug hole, oriented toward the board
                if edge in ("top", "bottom"):
                    ty0 = ly - (9.6 - 2.6) if edge == "bottom" else ly - 2.6
                    els.append(f'<rect x="{fmt(lx - 3.4)}" y="{fmt(ty0 - 2.0)}" width="6.8" '
                               f'height="9.6" rx="1.6" fill="{SH_PAPER}" '
                               f'stroke="{SH_INK}" stroke-width="1.1"/>')
                else:
                    hx = lx - (9.6 - 2.6) if edge == "right" else lx - 2.6
                    els.append(f'<rect x="{fmt(hx - 2.0)}" y="{fmt(ly - 3.4)}" width="9.6" '
                               f'height="6.8" rx="1.6" fill="{SH_PAPER}" '
                               f'stroke="{SH_INK}" stroke-width="1.1"/>')
                els.append(f'<circle cx="{fmt(lx)}" cy="{fmt(ly)}" r="1.6" fill="none" '
                           f'stroke="{SH_INK}" stroke-width="0.9"/>')
                self.obst_circle(lx, ly, 1.9, f"lug {item.get('id', '')}.{lug}")
            self.obst_circle(x, y, r, f"pot {item.get('id', '')}")
            lnx, lny = (item.get("label_nudge") or [0, 0])[:2]
            vnx, vny = (item.get("value_nudge") or [0, 0])[:2]
            if sgn < 0:
                lab_y, val_y = y - r - 22, y - r - 9
            else:
                lab_y, val_y = y + r + 15, y + r + 28
            self.lab(x + lnx, lab_y + lny, label.upper(), SH_INK, 11, weight=700,
                     spacing="0.06em", halo=SH_PAPER, halo_width=3.0,
                     tag=f"pot {item.get('id', '')} name",
                     group=f"pot:{item.get('id', '')}", keep_in=self.canvas_box())
            if val:
                self.lab(x + lnx + vnx, val_y + lny + vny, val, SH_INK2, 10,
                         weight=600, halo=SH_PAPER, halo_width=2.8,
                         tag=f"pot {item.get('id', '')} value",
                         group=f"pot:{item.get('id', '')}", keep_in=self.canvas_box())
        elif kind == "jack":
            r = 9
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" '
                       f'fill="{SH_PAPER}" stroke="{SH_INK}" stroke-width="1.6"/>')
            els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3.2" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="1.0"/>')
            self.obst_circle(x, y, r, f"jack {item.get('id', '')}")
            lab_y = (y - r - 9) if sgn < 0 else (y + r + 14)
            self.lab(x, lab_y, label.upper(), SH_INK, 10, weight=700, spacing="0.05em",
                     halo=SH_PAPER, halo_width=2.8, tag=f"jack {item.get('id', '')}",
                     group=f"jack:{item.get('id', '')}", keep_in=self.canvas_box())
        elif kind in ("xfmr", "choke"):
            if ref:                     # identity beside the glyph; see iron_value()
                val = iron_value(self.bom_for(ref)["value"], self.iron.get(ref))[0]
            w, h = (46, 56) if kind == "xfmr" else (40, 34)
            els.append(f'<rect x="{fmt(x - w / 2)}" y="{fmt(y - h / 2)}" width="{w}" '
                       f'height="{h}" rx="2" fill="{SH_PAPER}" stroke="{SH_INK}" '
                       f'stroke-width="2.0"/>')
            els.append(f'<rect x="{fmt(x - w / 2 + 4)}" y="{fmt(y - h / 2 + 4)}" '
                       f'width="{w - 8}" height="{h - 8}" rx="1" fill="none" '
                       f'stroke="{SH_INK}" stroke-width="0.8"/>')
            self.obst_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                           f"{kind} {item.get('id', '')}")
            # name lettered INSIDE the double-line body, stacked
            words = [wd.upper() for wd in label.split()]
            ty = y - (len(words) - 1) * 5.5
            for wd in words:
                self._fixed_text(x, ty + 3, wd, 8.5, weight=700, halo=SH_PAPER)
                ty += 11
            for colour in self.xfmr_leads.get(item.get("id"), []):
                ex_, ey_, base = self.xfmr_lead_pos(item, colour)
                wc = SHEET_WIRE.get(lead_base(colour) or "", SH_NEUTRAL)
                els.append(f'<line x1="{fmt(base[0])}" y1="{fmt(base[1])}" x2="{fmt(ex_)}" '
                           f'y2="{fmt(ey_)}" stroke="{wc}" stroke-width="2.2" '
                           f'stroke-linecap="round"/>')
                els.append(sheet_term(ex_, ey_, 2.2))
                self.obst_circle(ex_, ey_, 2.4, f"pigtail {item.get('id', '')}.{colour}")
                self._lead_callout(item, colour, ex_, ey_, base, SH_INK2, SH_PAPER)
            if val:
                val_x, val_anchor = self._edge_safe(x, val, 9.5, False)
                val_y = (y - h / 2 - 10) if sgn < 0 else (y + h / 2 + 13)
                self.lab(val_x, val_y, val, SH_INK2, 9.5, weight=600, anchor=val_anchor,
                         halo=SH_PAPER, halo_width=2.8,
                         tag=f"{kind} {item.get('id', '')} value",
                         group=f"{kind}:{item.get('id', '')}", keep_in=self.canvas_box())
        elif kind == "part":
            # An off-board part is the same dogbone or can as a board part, just
            # standing beside the board — so its value is lettered the same way.
            # (Pots, transformers and chokes above keep house units: a taper
            # suffix or a factory part number is not a body lettering.)
            if ref:
                val = self._val_tokens(ref)[0]
            g, _ = self._part_glyph(item, x, y, label, val)
            els += g
        else:  # switch / fuse / misc
            w, h = 34, 18
            els.append(f'<rect x="{fmt(x - w / 2)}" y="{fmt(y - h / 2)}" width="{w}" '
                       f'height="{h}" rx="2" fill="{SH_PAPER}" stroke="{SH_INK}" '
                       f'stroke-width="1.6"/>')
            self.obst_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                           f"{kind} {item.get('id', '')}")
            lab_y = (y - h / 2 - 9) if sgn < 0 else (y + h / 2 + 14)
            self.lab(x, lab_y, label.upper(), SH_INK, 10, weight=700, spacing="0.05em",
                     halo=SH_PAPER, halo_width=2.8, tag=f"{kind} {item.get('id', '')}",
                     group=f"{kind}:{item.get('id', '')}", keep_in=self.canvas_box())
        return "".join(els), ""

    def _part_glyph(self, item, x, y, label, val):
        edge = item.get("edge", "top")
        away = {"top": (0, -1), "bottom": (0, 1),
                "left": (-1, 0), "right": (1, 0)}.get(edge, (0, -1))
        ta = self.part_terminal_pos(item, "a")
        tb = self.part_terminal_pos(item, "b")
        els: list[str] = []
        pid = item.get("id", "")
        if item.get("glyph") == "lamp":
            cbx, cby = x + away[0] * 2, y + away[1] * 2
            bx, by = x + away[0] * 15, y + away[1] * 15
            for (tx, ty) in (ta, tb):
                els.append(f'<line x1="{fmt(tx)}" y1="{fmt(ty)}" x2="{fmt(cbx)}" '
                           f'y2="{fmt(cby)}" stroke="{SH_INK}" stroke-width="1.5"/>')
            els.append(f'<rect x="{fmt(cbx - 8)}" y="{fmt(cby - 6)}" width="16" height="12" '
                       f'rx="1.5" fill="{SH_PAPER}" stroke="{SH_INK}" stroke-width="1.3"/>')
            els.append(f'<circle cx="{fmt(cbx - 8)}" cy="{fmt(cby)}" r="1.5" fill="{SH_INK}"/>')
            els.append(f'<circle cx="{fmt(cbx + 8)}" cy="{fmt(cby)}" r="1.5" fill="{SH_INK}"/>')
            els.append(f'<circle cx="{fmt(bx)}" cy="{fmt(by)}" r="9.5" fill="{SH_PAPER}" '
                       f'stroke="{SH_INK}" stroke-width="1.5"/>')
            els.append(f'<path d="M {fmt(bx - 3.5)} {fmt(by + 1.5)} q 1.8 -5 3.5 0 '
                       f'q 1.8 5 3.5 0" fill="none" stroke="{SH_INK}" stroke-width="0.9"/>')
            self.obst_circle(bx, by, 9.5, f"lamp {pid}")
            self.obst_rect(cbx - 9.7, cby - 6, cbx + 9.7, cby + 6, f"lamp base {pid}")
            laby = by - 16 if away[1] < 0 else by + 25
            self.lab(bx, laby, label.upper(), SH_INK, 10, weight=700, spacing="0.05em",
                     halo=SH_PAPER, halo_width=2.8, tag=f"part {pid}",
                     group=f"off:{pid}", keep_in=self.canvas_box())
            for (tx, ty) in (ta, tb):
                els.append(sheet_term(tx, ty, 2.2))
                self.obst_circle(tx, ty, 2.2, f"terminal {pid}")
            return els, []
        horiz = edge in ("top", "bottom")
        midx, midy = (ta[0] + tb[0]) / 2, (ta[1] + tb[1]) / 2
        els.append(f'<line x1="{fmt(ta[0])}" y1="{fmt(ta[1])}" x2="{fmt(tb[0])}" '
                   f'y2="{fmt(tb[1])}" stroke="{SH_INK}" stroke-width="1.5"/>')
        # An off-board part is the SAME body a board part gets — same dogbone,
        # same size, same value lettered ON it. It was drawn smaller with the
        # value floated below as a queued label, which broke the sheet's one
        # promise ("the value is on the part") and left those values sitting in
        # the lead fan where their own two leads struck them.
        ref = item.get("ref")
        cat = category(self.bom_for(ref)["part"]) if ref else "res"
        if horiz:
            bw = max(30.0, abs(tb[0] - ta[0]) - 6)
            if cat == "electro":
                # a chassis filter can is a CAN, crimp and polarity gutter and
                # all — off the board it was borrowing the resistor dogbone.
                bw = max(48.0, bw)        # wide enough for the '+' gutter AND the value
                bh2 = 26.0
                x0, y0 = midx - bw / 2, midy - bh2 / 2
                els.append(f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(bw)}" '
                           f'height="{fmt(bh2)}" rx="4" fill="{SH_BODY}" '
                           f'stroke="{SH_INK}" stroke-width="1.8"/>')
                els.append(f'<line x1="{fmt(x0)}" y1="{fmt(y0 + 5.5)}" '
                           f'x2="{fmt(x0 + bw)}" y2="{fmt(y0 + 5.5)}" '
                           f'stroke="{SH_INK}" stroke-width="0.9"/>')
                els += plus_mark(x0 + 7.0, y0 + 13.5, 3.2, SH_INK, 1.5)
                self.obst_rect(x0, y0, x0 + bw, y0 + bh2, f"part {pid} body")
                top = away[1] < 0
                gut = PLUS_GUTTER
                on_body = bool(val) and self._val_inside(
                    x0 + gut + (bw - gut) / 2, midy + 3.5, val, bw - gut)
                ref_y = (midy - 24) if top else (midy + 26)
                val_y = (midy - 36) if top else (midy + 38)
                self.lab(midx, ref_y, label.upper(), SH_INK, 10, weight=700,
                         spacing="0.04em", halo=SH_PAPER, halo_width=2.8,
                         tag=f"part {pid} ref", group=f"off:{pid}",
                         keep_in=self.canvas_box())
                if val and not on_body:
                    self.lab(midx, val_y, val, SH_INK2, 9.5, weight=600, halo=SH_PAPER,
                             halo_width=2.8, tag=f"part {pid} value",
                             group=f"off:{pid}", keep_in=self.canvas_box())
                for (tx, ty) in (ta, tb):
                    els.append(sheet_term(tx, ty, 2.2))
                    self.obst_circle(tx, ty, 2.2, f"terminal {pid}")
                return els, []
            if cat in ("film", "mica", "diode"):
                # a chassis-mounted cap or rectifier keeps its OWN outline, not
                # a dogbone: the body form is how the sheet says what a part is.
                bh2 = {"film": 26.0, "mica": 18.0, "diode": 20.0}[cat]
                els.append(f'<rect x="{fmt(midx - bw / 2)}" y="{fmt(midy - bh2 / 2)}" '
                           f'width="{fmt(bw)}" height="{fmt(bh2)}" rx="1.5" '
                           f'fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
                self.obst_rect(midx - bw / 2, midy - bh2 / 2, midx + bw / 2,
                               midy + bh2 / 2, f"part {pid} body")
                end = str(item.get("cathode", "")).strip().lower()
                if cat == "diode" and end in ("a", "b"):
                    left = (end == "a") == (ta[0] <= tb[0])
                    bxx = (midx - bw / 2 + 2.5) if left else (midx + bw / 2 - 7.5)
                    els.append(f'<rect x="{fmt(bxx)}" y="{fmt(midy - bh2 / 2 + 1.2)}" '
                               f'width="5" height="{fmt(bh2 - 2.4)}" fill="{SH_INK}"/>')
            else:
                els.append(f'<path d="{dogbone_path(midx, midy, bw)}" '
                           f'fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.6"/>')
                self.obst_rect(midx - bw / 2, midy - 8.6, midx + bw / 2, midy + 8.6,
                               f"part {pid} body")
            top = away[1] < 0
            on_body = bool(val) and self._val_inside(midx, midy, val, bw)
            ref_y = (midy - 19) if top else (midy + 21)
            val_y = (midy - 31) if top else (midy + 33)
            self.lab(midx, ref_y, label.upper(), SH_INK, 10, weight=700,
                     spacing="0.04em", halo=SH_PAPER, halo_width=2.8,
                     tag=f"part {pid} ref", group=f"off:{pid}",
                     keep_in=self.canvas_box())
            if val and not on_body:
                self.lab(midx, val_y, val, SH_INK2, 9.5, weight=600, halo=SH_PAPER,
                         halo_width=2.8, tag=f"part {pid} value", group=f"off:{pid}",
                         keep_in=self.canvas_box())
        else:
            bw, bh = 18.6, max(30.0, abs(tb[1] - ta[1]) - 6)
            rx, ry = midx - bw / 2, midy - bh / 2
            els.append(f'<g transform="rotate(-90 {fmt(midx)} {fmt(midy)})">'
                       f'<path d="{dogbone_path(midx, midy, bh)}" fill="{SH_BODY}" '
                       f'stroke="{SH_INK}" stroke-width="1.6"/></g>')
            self.obst_rect(rx, ry, rx + bw, ry + bh, f"part {pid} body")
            on_body = False
            if val:
                for size, pad in ((9, 8.0), (8.5, 6.0), (8, 4.0)):
                    if self._fits(val, size, bh - pad):
                        self._fixed_text(midx + 0.5, midy, val, size, weight=700,
                                         rotate=-90)
                        on_body = True
                        break
            lx = midx + away[0] * 18
            anchor = "end" if away[0] < 0 else "start"
            self.lab(lx, midy - 3, label.upper(), SH_INK, 10, weight=700, anchor=anchor,
                     spacing="0.04em", halo=SH_PAPER, halo_width=2.8,
                     tag=f"part {pid} ref", group=f"off:{pid}",
                     keep_in=self.canvas_box())
            if val and not on_body:
                self.lab(lx, midy + 11, val, SH_INK2, 9.5, anchor=anchor, weight=600,
                         halo=SH_PAPER, halo_width=2.8, tag=f"part {pid} value",
                         group=f"off:{pid}", keep_in=self.canvas_box())
        for (tx, ty) in (ta, tb):
            els.append(sheet_term(tx, ty, 2.2))
            self.obst_circle(tx, ty, 2.2, f"terminal {pid}")
        return els, []

    # ---- wiring -------------------------------------------------------------
    def run_wire(self, spec, i, pts, seg_hops=None):
        if not pts:
            return "", []
        seg_hops = seg_hops or {}
        twisted = str(spec.get("style", "")).lower() == "twisted"
        colour = spec.get("color")
        if not colour:
            colour = self._endpoint_colour(spec.get("from")) or \
                self._endpoint_colour(spec.get("to"))
        if twisted:
            self._check_heater_endpoint(spec.get("from"), f"run[{i}] from")
            self._check_heater_endpoint(spec.get("to"), f"run[{i}] to")
            self._has_twisted = True
            base = lead_base(colour) if colour else None
            stroke = SH_HEATER_CT if base == "green-yellow" else SH_HEATER
            d1, d2 = twisted_strands(pts)
            center = rounded_path(pts, r=11)
            casing = (f'<path d="{center}" fill="none" stroke="{SH_PAPER}" '
                      f'stroke-width="5.4" stroke-linecap="round" '
                      f'stroke-linejoin="round"/>')
            strands = (f'<path d="{d1}" fill="none" stroke="{stroke}" stroke-width="1.5" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>'
                       f'<path d="{d2}" fill="none" stroke="{stroke}" stroke-width="1.5" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
            return casing + strands, [pts[0], pts[-1]]
        stroke = SHEET_WIRE.get(str(colour).lower(), SH_NEUTRAL) if colour else SH_NEUTRAL
        if colour:
            key = str(colour).lower()
            if key not in self._colours_used:
                self._colours_used.append(key)
        d = hopped_path(pts, seg_hops, r=11)
        return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="2.0" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'), [pts[0], pts[-1]]

    def bus_wire(self, spec, i, pts):
        if not pts:
            return "", []
        d = rounded_path(pts, r=9)
        edge = (f'<path d="{d}" fill="none" stroke="{SH_INK}" stroke-width="4.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        core = (f'<path d="{d}" fill="none" stroke="{SH_BUS_CORE}" stroke-width="2.0" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        return edge + core, [pts[0], pts[-1]]

    # ---- assemble -----------------------------------------------------------
    def render(self) -> str:
        els = []
        bx, by, bw, bh = self.board_x, self.board_y, self.board_w, self.board_h
        # drafting-sheet page frame: a double rule around the whole sheet
        els.append(f'<rect x="6" y="6" width="{fmt(self.width - 12)}" '
                   f'height="{fmt(self.height - 12)}" fill="none" stroke="{SH_INK}" '
                   f'stroke-width="1.6"/>')
        els.append(f'<rect x="11" y="11" width="{fmt(self.width - 22)}" '
                   f'height="{fmt(self.height - 22)}" fill="none" stroke="{SH_INK}" '
                   f'stroke-width="0.6"/>')
        # the board: a strong double-line rectangle dominating the sheet
        els.append(f'<rect x="{fmt(bx)}" y="{fmt(by)}" width="{fmt(bw)}" height="{fmt(bh)}" '
                   f'rx="2" fill="{SH_BOARD}" stroke="{SH_INK}" stroke-width="3.0"/>')
        els.append(f'<rect x="{fmt(bx + 5)}" y="{fmt(by + 5)}" width="{fmt(bw - 10)}" '
                   f'height="{fmt(bh - 10)}" rx="1" fill="none" stroke="{SH_INK}" '
                   f'stroke-width="1.0"/>')
        # unused eyelets: fine open circles
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.ex(c), self.ey(r)
                els.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="2.1" fill="none" '
                           f'stroke="{SH_FAINT}" stroke-width="0.8"/>')
        for lead in self.leads:
            els.append(self.lead_run(lead))
        runs, bus = self.build_geometry()
        hops = self._hop_map(runs, bus)
        bus_pts: list[tuple[float, float]] = []
        run_pts: list[tuple[float, float]] = []
        for b in bus:
            svg, tp = self.bus_wire(b["spec"], b["j"], b["pts"])
            els.append(svg)
            bus_pts += tp
        twisted_runs = []
        for r in runs:
            if r["twisted"]:
                twisted_runs.append(r)
                continue
            svg, tp = self.run_wire(r["spec"], r["i"], r["pts"],
                                    hops.get(("run", r["i"]), {}))
            els.append(svg)
            run_pts += tp
        for it in self.offboard:
            geom, _ = self.off_stub(it)
            els.append(geom)
        for p in self.parts:
            geom, _ = self.part_body(p)
            els.append(geom)
        for r in twisted_runs:
            svg, tp = self.run_wire(r["spec"], r["i"], r["pts"])
            els.append(svg)
            run_pts += tp
        for (tx, ty) in bus_pts:
            els.append(sheet_term(tx, ty))
        seen: set = set()
        for (tx, ty) in run_pts:
            key = (round(tx, 1), round(ty, 1))
            if key in seen:
                continue
            seen.add(key)
            els.append(sheet_solder(tx, ty))
            self.obst_circle(tx, ty, 4.5, "solder joint")
        wires = [(f"run[{r['i']}]", r["pts"]) for r in runs if r["pts"]]
        wires += [(f"bus[{b['j']}]", b["pts"]) for b in bus if b["pts"]]
        els.append(self._emit_labels(wires))
        els += self._fixed
        title = ((self.layout.get("board", {}) or {}).get("title")
                 or f"{self.amp_id.upper()} board layout")
        title = title.upper()
        ts = self.cz(18)
        ty = 20 + ts
        self.chrome_text(els, bx, ty, title, SH_INK, ts, font=FONT_DISP,
                         weight=700, spacing="0.14em", tag="chrome title")
        els.append(f'<line x1="{fmt(bx)}" y1="{fmt(ty + 7.5)}" '
                   f'x2="{fmt(bx + 0.88 * text_width(title, ts, spacing="0.14em"))}" '
                   f'y2="{fmt(ty + 7.5)}" stroke="{SH_INK}" stroke-width="{fmt(1.2 * self.cs)}"/>')
        self._draw_footer(els)
        body = "\n".join(els)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(self.width)} '
               f'{fmt(self.height)}" role="img" aria-label="{esc(title)} — redrawn board '
               f'layout diagram, layout-sheet drafting style" width="100%" '
               f'font-family="{FONT_DISP}">\n'
               f'<rect x="0" y="0" width="{fmt(self.width)}" height="{fmt(self.height)}" '
               f'fill="{SH_PAPER}"/>\n{body}\n</svg>\n')
        if self.errors:
            raise ValueError(f"{self.amp_id}: layout errors: {self.errors}")
        return svg

    # ---- legend entries: the sheet's own paint ------------------------------
    FOOT_FAINT = SH_FAINT
    FOOT_MUTED = SH_INK2
    LEADER_INK = SH_INK2

    def _wiring_entries(self, fs):
        out = [self._entry("lead (uncoloured)", 24.0,
                           lambda cx, y, s: self._rule(cx, y, s, SH_NEUTRAL, 2.0), fs)]
        for key in self._colours_used:
            col = SHEET_WIRE.get(key, SH_NEUTRAL)
            out.append(self._entry(
                self.wire_legend.get(key, key), 24.0,
                lambda cx, y, s, c=col: self._rule(cx, y, s, c, 2.0), fs))
        if self.bus:
            out.append(self._entry(
                "ground bus", 24.0,
                lambda cx, y, s: (self._rule(cx, y, s, SH_INK, 4.0)
                                  + self._rule(cx + 1 * s, y, s, SH_BUS_CORE, 1.8, 16.0)),
                fs))
        if self._has_twisted:
            out.append(self._entry(
                "6.3 V heaters — twisted pair", 26.0,
                lambda cx, y, s: self._twist_swatch(cx, y, s, SH_HEATER), fs))
        return out

    def _joints_entries(self, fs):
        return [
            self._entry("wire end (solder joint)", 13.0,
                        lambda cx, y, s: sheet_solder(cx + 4 * s, y - 3 * s), fs),
            self._entry("cross-over (no connect)", 40.0,
                        lambda cx, y, s: self._hop_swatch(cx, y, s, SH_NEUTRAL), fs),
        ]

    def _bodies_entries(self, fs):
        """The sheet's outline glyphs, miniature. Every body form the drawing
        can emit is keyed here — a shape a builder cannot look up says nothing."""
        def dogbone(cx, y, s):
            return (f'<path d="{dogbone_path(cx + 9*s, y - 3.5*s, 18*s, r_end=4.4*s, waist=2.9*s)}" '
                    f'fill="{SH_BODY}" stroke="{SH_INK}" stroke-width="1.0"/>')

        def box(w, h, top, rx=1.0, crimp=False, band=False):
            def draw(cx, y, s):
                out = (f'<rect x="{fmt(cx)}" y="{fmt(y - top*s)}" width="{fmt(w*s)}" '
                       f'height="{fmt(h*s)}" rx="{fmt(rx*s)}" fill="{SH_BODY}" '
                       f'stroke="{SH_INK}" stroke-width="1.0"/>')
                if crimp:
                    out += (f'<line x1="{fmt(cx)}" y1="{fmt(y - (top-2.5)*s)}" '
                            f'x2="{fmt(cx + w*s)}" y2="{fmt(y - (top-2.5)*s)}" '
                            f'stroke="{SH_INK}" stroke-width="0.7"/>')
                if band:
                    out += (f'<rect x="{fmt(cx + (w-4)*s)}" y="{fmt(y - (top-0.5)*s)}" '
                            f'width="{fmt(3*s)}" height="{fmt((h-1)*s)}" fill="{SH_INK}"/>')
                return out
            return draw

        out = [self._entry("resistor", 23.0, dogbone, fs),
               self._entry("film / coupling cap", 19.0, box(14, 10, 9), fs),
               self._entry("electrolytic (+ = positive end)", 17.0,
                           box(12, 11, 10, rx=1.5, crimp=True), fs),
               self._entry("mica", 19.0, box(14, 8, 8), fs)]
        if self._has_diode:
            out.append(self._entry("diode / rectifier (band = cathode)", 21.0,
                                   box(16, 9, 8.5, band=True), fs))
        return out


def render_layout(amp_dir: Path, style: str = "house") -> str:
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    cls = SheetRenderer if style == "sheet" else Renderer
    return cls(layout, bom, amp_dir.name).render()


# ---- collision lint (CI gate, see pipeline/check_layouts.py) ----------------
LINT_ANGLE = 10.0      # (a) near-parallel: acute angle below this counts
LINT_SEP = 2.4         # (a) two runs closer than this read as one wire
LINT_OVERLAP = 8.0     # (a) shared near-parallel length that trips the lint
LINT_TERM = 5.0        # (b) a run end this close to another run's interior…
LINT_VERTEX_CLEAR = 4.0  # …unless it sits on one of that run's own nodes

# --- label-collision lint (checks c/d/e) ------------------------------------
# Every label's bounding box is estimated from house text metrics (text_box).
# The box is INSET before testing: a glyph does not fill its em box, and each
# label carries an opaque halo, so a wire or body that only grazes the box is
# not a legibility defect. The thresholds below are deliberately conservative —
# they are set so a drawing whose type is actually readable reports nothing,
# and every reported failure is a strike a reader would see.
LINT_LABEL_INSET = 1.6    # shrink a text box on all sides before testing (px)
# (c) A wire CROSSING a label transversally is the ordinary case on a wired
# board and is handled by the halo every label carries — it is not a defect.
# What destroys a label is a wire running ALONG it: the in-box span then
# approaches the label's own width and the wire lies in the text, not across it.
# So the strike threshold is relative to the label's width, with an absolute
# floor for very short labels.
LINT_WIRE_FRAC = 0.5      # (c) in-box span as a fraction of the label's width
LINT_WIRE_SPAN = 12.0     # (c) absolute floor for the same test (px)
LINT_GLYPH_W = 2.5        # (d) label∩body overlap that reads as a collision (px)
LINT_GLYPH_H = 2.5
# (e) Two labels do not have to overlap to read as one string — abutting with no
# gap is enough ("100 kΩ" + "250 pF" printed edge to edge on a dense board reads
# as "100 kΩ250 pF"). So the pairwise test grows each box by LINT_LABEL_GAP and
# fails on any intersection: labels must be separated, not merely disjoint.
LINT_LABEL_GAP = 2.2      # (e) clear space every label demands around itself (px)
LINT_LABEL_W = 0.5        # (e) intersection of the grown boxes that trips it (px)
LINT_LABEL_H = 0.5
# --- envelope checks (h/i) --------------------------------------------------
# These two exist because the lint above was tuned on the first twenty boards and
# measures things RELATIVE to each other — labels against wires, labels against
# bodies, labels against labels. Nothing measured the drawing against its own
# page. So a board could pass 28/28 while an input jack was drawn at cx = -7.6,
# ink outside the viewBox and invisible in every render (5C1 shipped that way),
# and nothing would stop a label being placed in the margin, far from the part it
# names, where a reader cannot attribute it at all.
LINT_BOUNDS_SLACK = 0.5   # (h) ink may sit this far outside the viewBox, no more
# (i) The furthest a label may sit from the nearest box of the thing it names.
# Measured across the corpus: the widest legitimate reach is 58 px (a lead label
# on a transformer's far terminal), so this is generous by half again — it is a
# guard against a label that has come adrift, not a placement rule.
LINT_LABEL_REACH = 90.0
_RE_LABEL_OWNER = re.compile(r"\s+(?:ref|value)$")


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


def lint_layout(amp_dir: Path, style: str = "house",
                labels_only: bool = False) -> list[str]:
    """Collision lint for the wiring layer — the checks CI runs so the drawing
    is never ambiguous about crossings or terminations. Both run over the plain
    (non-twisted) runs; twisted heater pairs and the ground bus are exempt:

      (a) near-parallel overlap — segments from two different runs at an acute
          angle < 10 deg with separation < 2.4 px over > 8 px of shared length
          (they read as a single wire);
      (b) terminal ambiguity — a run endpoint within 5 px of ANOTHER run's
          polyline interior while not sitting on any of that run's own nodes
          (it's unclear whether the wire lands there or merely passes by).

    Three more run over the LABELS — the half of the reference-drawing bar the
    wiring checks above cannot see. A dense board degrades in its labelling
    long before its routing, and until these existed the only thing keeping a
    drawing legible was hand-authored `label_nudge` / `value_nudge`, unmeasured:

      (c) label struck by a wire — a run, twisted heater pair or ground-bus
          segment passing through more than 3 px of a label's (inset) box;
      (d) label over a glyph — a label's box overlapping a part body, socket,
          pot, jack, transformer, terminal dot, lug pip or eyelet by more than
          2.5 px in both axes;
      (e) label over a label — two labels' boxes overlapping by more than 2 px
          in both axes (they read as one string, and neither can be attributed
          to a part).

    Label boxes are estimated from house text metrics and inset (see
    LINT_LABEL_INSET) — a halo'd glyph that merely grazes a wire is fine; a wire
    driven through the type is not.

    `style` picks which renderer is measured. The sheet style is a paint-only
    re-skin, so its wiring geometry is bit-for-bit the house geometry and checks
    (a), (b) and (f) would only repeat themselves — but its LABELS are its own:
    different type sizes, values lettered on the bodies, and a different set of
    obstacles for the placer to route around. `labels_only=True` runs just the
    label checks (c/d/e), which is how check_layouts.py adds the sheet pass
    without double-reporting the wiring findings.

    Returns a sorted list of failure strings with coordinates + run indices.
    """
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    bom = load_bom(amp_dir)
    cls = SheetRenderer if style == "sheet" else Renderer
    rend = cls(layout, bom, amp_dir.name)
    runs, bus = rend.build_geometry()
    plain = [r for r in runs if r["pts"] and not r["twisted"]]
    fails: list[str] = []
    if labels_only:
        return sorted(_lint_labels(rend, runs, bus, amp_dir.name, style=style))
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
    fails += _lint_labels(rend, runs, bus, amp_dir.name, style=style)
    # (f) two off-board items of the SAME kind carrying the SAME label: the
    # drawing then has two controls, jacks or transformers a reader cannot tell
    # apart, even where the data (bom.yaml roles, the wiring itself) does
    # distinguish them. Cheap, and it guards a defect that shipped once.
    # (g) a drawn component body that states no value at all. A part the reader
    # can neither read off the drawing nor look up by ref is a blank body: it
    # tells a builder a component goes there and nothing else. Board parts are
    # covered by the bom.yaml ref (an absent ref already fails the render), so
    # this guards the annotation layer — off-board `kind: part` glyphs, which
    # may legitimately have no BOM ref and until now could ship valueless in
    # silence (the model 1987's NFB resistor did).
    for it in (layout.get("offboard") or []):
        if it.get("kind") != "part" or it.get("glyph") == "lamp":
            continue
        if it.get("ref") or annotation_value(it):
            continue
        fails.append(
            f"{amp_dir.name}: no value — off-board part '{it.get('id')}' "
            f"({it.get('label', '')}) has neither a bom.yaml ref nor a `value:`; "
            f"it renders as a blank body")
    seen: dict = {}
    for it in (layout.get("offboard") or []):
        kind, label = it.get("kind"), str(it.get("label", "")).strip()
        if not label or kind not in ("pot", "jack", "xfmr", "choke", "switch", "part"):
            continue
        key = (kind, label.lower())
        if key in seen:
            fails.append(
                f"{amp_dir.name}: ambiguous label — {kind}s '{seen[key]}' and "
                f"'{it.get('id')}' both read '{label}'")
        else:
            seen[key] = it.get("id")
    return sorted(fails)


def _lint_labels(rend: "Renderer", runs, bus, amp_id: str,
                 style: str = "house") -> list[str]:
    """Checks (c) label-vs-wire, (d) label-vs-glyph, (e) label-vs-label.

    `rend` must have been rendered (that is what populates its label and
    obstacle registries), so the gate measures exactly the geometry the
    committed SVG ships. A SheetRenderer populates both registries by the same
    code paths — its bodies and sockets call obst_rect/obst_circle exactly as
    the house ones do, and it registers its on-body value lettering as an
    obstacle too — so the same three checks measure the sheet render. Findings
    are tagged with the style so a sheet-only collision is never mistaken for a
    house one."""
    amp_id = f"{amp_id} [sheet]" if style == "sheet" else amp_id
    rend.render()
    labels = rend.labels
    # (full box, inset box): the inset box is what is tested for contact, but the
    # wire-strike fraction is of the label's OWN width — the same measure the
    # placer uses, so a placement the placer accepts is one the gate accepts.
    boxes = [(lb, _shrink(lb["box"], LINT_LABEL_INSET), lb["box"][2] - lb["box"][0])
             for lb in labels]
    fails: list[str] = []
    # (c) label struck by a wire
    wires = []
    for r in runs:
        if r["pts"]:
            wires.append((f"run[{r['i']}]", r["pts"]))
    for b in bus:
        if b["pts"]:
            wires.append((f"bus[{b['j']}]", b["pts"]))
    for lb, box, width in boxes:
        for name, pts in wires:
            span = 0.0
            for k in range(len(pts) - 1):
                span = max(span, _seg_box_span(pts[k], pts[k + 1], box))
            if span > max(LINT_WIRE_SPAN, LINT_WIRE_FRAC * width):
                fails.append(
                    f"{amp_id}: label struck by wire — '{lb['text']}' ({lb['tag']}) "
                    f"crossed by {name} over ~{span:.1f}px at "
                    f"({(box[0]+box[2])/2:.0f},{(box[1]+box[3])/2:.0f})")
                break
    # (d) label over a glyph
    for lb, box, _w in boxes:
        for ob in rend.obstacles:
            w, h = _box_overlap(box, ob["box"])
            if w > LINT_GLYPH_W and h > LINT_GLYPH_H:
                fails.append(
                    f"{amp_id}: label over glyph — '{lb['text']}' ({lb['tag']}) "
                    f"overlaps {ob['tag']} by {w:.1f}x{h:.1f}px at "
                    f"({(box[0]+box[2])/2:.0f},{(box[1]+box[3])/2:.0f})")
                break
    # (e) label over a label
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (la, _ia, _wa), (lbb, _ib, _wb) = boxes[i], boxes[j]
            ba, bb = la["box"], lbb["box"]
            w, h = _box_overlap(_shrink(ba, -LINT_LABEL_GAP), bb)
            if w > LINT_LABEL_W and h > LINT_LABEL_H:
                fails.append(
                    f"{amp_id}: labels collide — '{la['text']}' ({la['tag']}) and "
                    f"'{lbb['text']}' ({lbb['tag']}) overlap {w:.1f}x{h:.1f}px at "
                    f"({(ba[0]+ba[2])/2:.0f},{(ba[1]+ba[3])/2:.0f})")
    # (h) ink outside the page. Every glyph, every label and every piece of page
    # chrome must sit inside the viewBox the drawing publishes; ink beyond it is
    # simply not in the picture, and no viewport downstream can recover it. The
    # chrome arm was added 2026-08-08: the 5E4-A's provenance line ran 1515 px
    # past its own right edge and two thirds of the sentence naming the source
    # was invisible in every render, on the site and in print.
    for kind, items in (("glyph", rend.obstacles), ("label", labels),
                        ("chrome", rend.chrome)):
        for it in items:
            bx = it["box"]
            out_x = max(-bx[0], bx[2] - rend.width)
            out_y = max(-bx[1], bx[3] - rend.height)
            if max(out_x, out_y) > LINT_BOUNDS_SLACK:
                what = f" '{it['text']}'" if it.get("text") else ""
                fails.append(
                    f"{amp_id}: outside the viewBox — {kind}{what} ({it['tag']}) "
                    f"runs {max(out_x, 0.0):.1f}px past the left/right edge and "
                    f"{max(out_y, 0.0):.1f}px past the top/bottom of the "
                    f"{rend.width:.0f}x{rend.height:.0f} page")
    # (i) a label adrift from what it names
    owners: dict[str, list] = {}
    for ob in rend.obstacles:
        owners.setdefault(ob["tag"], []).append(ob["box"])
    for lb in labels:
        own = _RE_LABEL_OWNER.sub("", lb["tag"])
        if own not in owners:
            continue                    # nothing registered a body to measure against
        reach = min(_box_gap(lb["box"], b) for b in owners[own])
        if reach > LINT_LABEL_REACH:
            fails.append(
                f"{amp_id}: label adrift — '{lb['text']}' ({lb['tag']}) sits "
                f"{reach:.0f}px from the nearest part of {own}; a reader cannot "
                f"tell what it labels")
    return fails


def _box_gap(a, b) -> float:
    """Shortest distance between two axis-aligned boxes (0 when they touch)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def _box_link(a, b):
    """The shortest segment joining two axis-aligned boxes, as ((x1,y1),(x2,y2)).
    Used to draw a leader from a displaced label back to the part it names."""
    def axis(a0, a1, b0, b1):
        if a1 < b0:
            return a1, b0
        if b1 < a0:
            return a0, b1
        mid = (max(a0, b0) + min(a1, b1)) / 2
        return mid, mid
    x1, x2 = axis(a[0], a[2], b[0], b[2])
    y1, y2 = axis(a[1], a[3], b[1], b[3])
    return (x1, y1), (x2, y2)


def render_all(write: bool = True, style: str = "house",
               ids: list[str] | None = None) -> list[Path]:
    written = []
    for yml in sorted((ROOT / "amps").glob("*/layout.yaml")):
        if ids and yml.parent.name not in ids:
            continue
        svg = render_layout(yml.parent, style)
        out = yml.parent / ("layout-sheet.svg" if style == "sheet" else "layout.svg")
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


def render_png(ids: list[str], width: int = 1600, style: str = "house") -> list[Path]:
    """Convert amps/<id>/layout[-sheet].svg -> /tmp/<id>[-sheet].png for a
    visual self-review. With no ids, converts every amp that has a layout."""
    exe = ensure_rsvg()
    if not exe:
        return []
    if not ids:
        ids = [p.parent.name for p in sorted((ROOT / "amps").glob("*/layout.yaml"))]
    suffix = "-sheet" if style == "sheet" else ""
    out_paths = []
    for amp_id in ids:
        svg = ROOT / "amps" / amp_id / f"layout{suffix}.svg"
        if not svg.exists():
            print(f"no layout{suffix}.svg for {amp_id}", file=sys.stderr)
            continue
        png = Path("/tmp") / f"{amp_id}{suffix}.png"
        subprocess.run([exe, "-w", str(width), str(svg), "-o", str(png)], check=True)
        print(f"png {png}")
        out_paths.append(png)
    return out_paths


if __name__ == "__main__":
    args = sys.argv[1:]
    style = "house"
    if "--style" in args:
        k = args.index("--style")
        style = args[k + 1]
        del args[k:k + 2]
        if style not in ("house", "sheet"):
            sys.exit(f"unknown --style '{style}' (house | sheet)")
    # Both styles are published corpus-wide, and both honour an optional id list
    # (`render_layouts.py --style sheet ab763`) so a single board can be redrawn
    # and looked at. With no ids, every amp is rendered — which is what CI's
    # staleness check expects.
    if "--png" in args:
        args.remove("--png")
        render_all(write=True, style=style, ids=args or None)
        render_png(args, style=style)
    else:
        render_all(write=True, style=style, ids=args or None)
        if not list((ROOT / "amps").glob("*/layout.yaml")):
            print("no layout.yaml files found", file=sys.stderr)
