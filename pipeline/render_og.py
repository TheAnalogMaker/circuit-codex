#!/usr/bin/env python3
"""Render the per-amp social cards: site/public/og/<id>.png, 1200x630.

A link to an amp page posted on a forum or in a chat is unrolled into a preview
card, and until now every one of them showed the same generic brand image. This
generates one card per circuit instead: the house brand card (dark ground, amber
wordmark) carrying the circuit designation, the descriptive style name, the era,
the power and tube complement, the verification chip — and, across the bottom
third, a full-bleed crop of that amp's own era layout-sheet drawing.

The visual is not decoration: it is a real region of amps/<id>/layout-sheet.svg,
inlined (same SVG namespace, no rasterised intermediate) and clipped to the band,
so a card can never show a board the corpus does not draw. That also means a card
goes stale the moment its layout does, which is what --check gates.

    python3 pipeline/render_og.py            # write every card
    python3 pipeline/render_og.py 5f1 5e3    # write named cards
    python3 pipeline/render_og.py --check    # CI gate: no card is stale

Rendering needs rsvg-convert (`brew install librsvg`; apt in CI). --check needs
neither rsvg nor fonts: it recomputes each card's SVG and compares digests
against pipeline/og_manifest.json, written whenever the PNGs are.


================================ THE CROP ==================================
Deterministic, and the same rule for all eighteen boards.

  height    The window is framed to the drawing's under-chassis view: from just
            below the row of pots and jacks along the board's top edge, down
            past the tube sockets to the bottom of their captions. Framing to
            the content rather than to a fixed zoom is what makes an 18-column
            Champ board and a 50-column Super Lead board read at the same
            weight on their cards (they land within 0.68–0.71 card px per
            viewBox unit; the four boards narrower than the frame are simply
            shown whole, larger).

  legibility  The zoom never falls below LAYOUT_MIN_SCALE = 0.62 card px per
            viewBox unit — the floor site/src/lib/corpus.js uses for a board
            drawing, under which the 11.5-unit part labels fall below 7 px and
            the drawing reads as a grey smear. No card shows type the site
            itself would call illegible. The frame also stays inside the
            drawing: never the sheet title above the board, never the
            attribution and legend below it.

  position  Horizontally the window lands on the busiest stretch of board — the
            placement enclosing the most part bodies, ties broken toward the
            board's centre. That is what makes a Bassman card look like a
            Bassman: the crop finds the filter and tone-stack cluster rather
            than an arbitrary run of bare eyelets.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from render_layouts import SheetRenderer, esc, fmt, load_bom

ROOT = Path(__file__).resolve().parent.parent
AMPS = ROOT / "amps"
OUT_DIR = ROOT / "site" / "public" / "og"
MANIFEST = Path(__file__).resolve().parent / "og_manifest.json"

# ---- card geometry ---------------------------------------------------------
CARD_W, CARD_H = 1200, 630
BAND_Y = 356                       # top of the layout-sheet band
BAND_H = CARD_H - BAND_Y           # 274 — the bottom ~43% of the card
PAD_L, PAD_R = 78, 1122            # type margins

# The site's own legibility floor for a board drawing, in card px per viewBox
# unit. Keep in step with LAYOUT_MIN_SCALE in site/src/lib/corpus.js.
MIN_SCALE = 0.62
CROP_INSET = 52.0                  # a part this close to the edge is not "inside"

# ---- house palette (site/src/layouts/Base.astro :root) ---------------------
GROUND = "#171310"
INK, MUTED, FAINT = "#eee2c8", "#a3927b", "#7a6a54"
AMBER, AMBER_DIM, LINE = "#e89b3f", "#b97c33", "#3a3025"
OK = "#8fae7e"
DISP = "'Avenir Next Condensed','Arial Narrow','Helvetica Neue',Arial,sans-serif"
ADV_DISP = 0.53                    # mean advance per em of the condensed face


def adv(s: str, size: float, spacing: float = 0.0) -> float:
    """Estimated advance width of a condensed-face run, letter-spacing included."""
    return len(s) * (size * ADV_DISP + spacing)


def txt(x, y, s, fill, size, *, weight=600, spacing=0.0, anchor="start",
        opacity=None) -> str:
    ls = f' letter-spacing="{fmt(spacing)}"' if spacing else ""
    op = f' opacity="{fmt(opacity)}"' if opacity is not None else ""
    return (f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{fill}" font-size="{fmt(size)}" '
            f'font-family="{DISP}" font-weight="{weight}" text-anchor="{anchor}"'
            f'{ls}{op}>{esc(s)}</text>')


# ---- corpus reading --------------------------------------------------------
def amp_ids() -> list[str]:
    return sorted(d.name for d in AMPS.iterdir()
                  if d.is_dir() and not d.name.startswith("_")
                  and (d / "layout.yaml").exists() and (d / "meta.yaml").exists())


def display_id(amp_id: str) -> str:
    """The circuit designation as the drawings print it — Fender hyphenates the
    revision suffix (5F6-A, 5F2-A, 6G6-B). Mirrors displayId() in
    site/src/lib/corpus.js."""
    return re.sub(r"^(\d[A-Z]\d+)([AB])$", r"\1-\2", amp_id.upper())


# Display names for the topology values, verbatim from TOPOLOGY_DIMENSIONS in
# site/src/lib/corpus.js — a card and the amp page's own metadata panel must call
# a circuit's parts by the same names.
BIAS = {"fixed": "Fixed bias", "cathode": "Cathode bias"}
RECT = {"tube": "Tube rectifier", "solid-state": "Solid-state rectifier"}
TONE = {"cathode-follower-fmv": "Cathode-follower FMV stack",
        "cathode-follower-tb": "Cathode-follower treble/bass",
        "tb": "Treble/bass stack",
        "single-knob": "Single tone control",
        "none": "No tone stack"}


def spec_bits(m: dict) -> list[str]:
    """The spec strip, most load-bearing first — the tail is what gets dropped
    when a long circuit's strip will not fit the card."""
    topo = m.get("topology") or {}
    ts = topo.get("tone_stack")
    bits = [f"{m['wattage']} W"]
    if topo.get("bias"):
        bits.append(BIAS.get(topo["bias"], f"{topo['bias']} bias"))
    if (topo.get("rectifier") or {}).get("kind"):
        kind = topo["rectifier"]["kind"]
        bits.append(RECT.get(kind, f"{kind} rectifier"))
    if ts:
        # An unmapped control (the AC15's top cut is not an FMV-style stack) is
        # named for what it is, never promoted to "tone stack".
        bits.append(TONE.get(ts, f"{ts} tone control"))
    return [b.upper() for b in bits]


def tube_line(m: dict) -> str:
    """The tube complement as a count, in order of first appearance: a Super Lead
    reads 'ECC83 ×3 · EL34 ×4', not the same bottle printed seven times."""
    counts: dict[str, int] = {}
    for t in (m.get("tubes") or []):
        t = str(t)
        counts[t] = counts.get(t, 0) + 1
    return " · ".join(t if n == 1 else f"{t} ×{n}" for t, n in counts.items())


# ---- the crop --------------------------------------------------------------
def crop_window(rend: SheetRenderer) -> tuple[float, float, float, float]:
    """(x0, y0, w, h) in layout-sheet viewBox units — see THE CROP above.

    `rend` must have rendered: the frame is measured from the boxes the renderer
    registered for every glyph and every placed label, so the crop knows where
    the drawing's ink actually ends rather than assuming a fixed offset (socket
    captions are placed, and stagger to clear each other)."""
    W, H = float(rend.width), float(rend.height)
    bx, by, bw, bh = (float(rend.board_x), float(rend.board_y),
                      float(rend.board_w), float(rend.board_h))

    # Vertical content band: below the sheet title, above the footer stack.
    attrib_row = max(r for r in rend._footer_rows() if r is not None)
    top_limit = max(14.0, by - 96.0)
    bot_limit = min(H - 14.0, rend._footer_y(attrib_row) - 24.0 * rend.cs)
    avail_h = max(60.0, bot_limit - top_limit)

    # The band the card wants to show: from just under the row of pots and jacks
    # along the board's top edge down through the tube sockets below it and their
    # captions. That is the whole of the under-chassis view, and framing to it —
    # rather than to a fixed zoom — is what makes an 18-column Champ board and a
    # 50-column Super Lead board read at the same weight on their cards.
    tops = [rend.off_pos(it)[1] for it in rend.offboard if it.get("edge") == "top"]
    socks = [rend.off_pos(it)[1] for it in rend.offboard
             if it.get("edge", "bottom") == "bottom"]
    # Top edge: just clear of the pot and jack glyphs, so the frame opens on
    # their leads running down into the board rather than on half a pot body.
    ctop = (min(tops) + 38.0) if tops else (by - 24.0)
    if socks:
        # Bottom edge: under the socket captions, which the label placer staggers
        # to clear each other — so the depth is measured, not assumed. Bounded,
        # so one long harness label cannot drag the whole frame down.
        sy = max(socks)
        low = [d["box"][3] for d in rend.labels
               if sy - 40.0 < (d["box"][1] + d["box"][3]) / 2 < sy + 96.0]
        cbot = min((max(low) if low else sy + 54.0) + 10.0, sy + 84.0)
    else:
        cbot = by + bh + 24.0
    ctop, cbot = max(ctop, top_limit), min(cbot, bot_limit)

    aspect = CARD_W / BAND_H
    crop_w = min((cbot - ctop) * aspect, W - 24.0, CARD_W / MIN_SCALE)
    crop_h = crop_w / aspect
    crop_h = min(crop_h, avail_h)
    crop_w = crop_h * aspect

    # Horizontal: the placement enclosing the most part bodies; ties to centre.
    xs: list[float] = []
    for p in rend.parts:
        a, b = p.get("a"), p.get("b")
        if not (a and b):
            continue
        xs.append((rend.ex(a[1]) + rend.ex(b[1])) / 2.0)
    board_cx = bx + bw / 2.0
    lo, hi = 0.0, max(0.0, W - crop_w)
    best = (-1, 0.0, lo)
    x = lo
    while x <= hi + 1e-9:
        inner0, inner1 = x + CROP_INSET, x + crop_w - CROP_INSET
        n = sum(1 for v in xs if inner0 <= v <= inner1)
        off = abs((x + crop_w / 2.0) - board_cx)
        if n > best[0] or (n == best[0] and off < best[1]):
            best = (n, off, x)
        x += 2.0
    x0 = best[2]

    # Vertical: the whole content band when the window is tall enough for it
    # (any surplus split evenly, so the drawing sits centred on the paper);
    # otherwise a board this wide cannot be framed whole at a legible zoom, so
    # the board itself is centred and the crop reads as a detail.
    if crop_h >= cbot - ctop:
        y0 = ctop - (crop_h - (cbot - ctop)) / 2.0
    else:
        y0 = by + bh / 2.0 - crop_h / 2.0
    y0 = min(max(y0, top_limit), max(top_limit, bot_limit - crop_h))
    return (round(x0, 2), round(y0, 2), round(crop_w, 2), round(crop_h, 2))


def sheet_inner(svg_path: Path) -> str:
    """The drawing content of a committed layout-sheet.svg, root element removed.
    These sheets carry no <defs> and no ids, so inlining one cannot collide with
    the card's own clip path."""
    text = svg_path.read_text()
    m = re.match(r"<svg\b[^>]*>", text)
    if not m:
        raise SystemExit(f"{svg_path}: no <svg> root")
    return text[m.end():].rsplit("</svg>", 1)[0].strip()


# ---- the card --------------------------------------------------------------
def card_svg(amp_id: str) -> str:
    amp_dir = AMPS / amp_id
    meta = yaml.safe_load((amp_dir / "meta.yaml").read_text())
    layout = yaml.safe_load((amp_dir / "layout.yaml").read_text())
    rend = SheetRenderer(layout, load_bom(amp_dir), amp_id)
    rend.render()          # populates the glyph/label boxes the crop measures
    cx0, cy0, cw, ch = crop_window(rend)
    s = CARD_W / cw

    did = display_id(amp_id)
    era = meta.get("era") or {}
    v = meta.get("verification") or {}
    verified = v.get("status") == "verified"
    tubes = tube_line(meta)

    e: list[str] = []
    e.append(f'<rect width="{CARD_W}" height="{CARD_H}" fill="{GROUND}"/>')

    # --- brand row ---------------------------------------------------------
    e.append(f'<g transform="translate({PAD_L},40)">'
             f'<circle cx="20" cy="26" r="18" fill="none" stroke="{AMBER}" stroke-width="4.6"/>'
             f'<rect x="15" y="0" width="9" height="18" rx="3" fill="{AMBER}"/></g>')
    e.append(txt(PAD_L + 54, 76, "CIRCUIT", INK, 26, weight=700, spacing=5.2))
    e.append(txt(PAD_L + 54 + adv("CIRCUIT ", 26, 5.2), 76, "CODEX", AMBER,
                 26, weight=700, spacing=5.2))
    e.append(txt(PAD_R, 76, f"circuitcodex.com/amps/{amp_id}/", FAINT, 22,
                 weight=600, spacing=1.4, anchor="end"))

    # --- circuit designation, and the verification chip on its baseline ----
    id_size = 146 if len(did) <= 3 else (128 if len(did) <= 5 else 112)
    id_w = adv(did, id_size, 2)
    e.append(txt(PAD_L - 4, 212, did, AMBER, id_size, weight=700, spacing=2))
    e.append(f'<rect x="{PAD_L}" y="236" width="104" height="5" rx="2.5" fill="{AMBER_DIM}"/>')

    chip = f"✓  VERIFIED  {v.get('date')}" if verified and v.get("date") else \
           ("✓  VERIFIED" if verified else "DRAFT")
    chip_col, chip_edge = (OK, OK) if verified else (MUTED, LINE)
    cwid = adv(chip, 21, 2.6) + 44
    chip_x = PAD_R - cwid
    e.append(f'<rect x="{fmt(chip_x)}" y="171" width="{fmt(cwid)}" height="40" '
             f'rx="20" fill="none" stroke="{chip_edge}" stroke-width="1.5"/>')
    e.append(txt(PAD_R - 22, 198, chip, chip_col, 21, spacing=2.6, anchor="end"))

    # A signal rail runs from the designation to the chip — the brand card's
    # motif, and it keeps the space between them from reading as a hole. Drawn
    # only where there is room for the whole run.
    rail0, rail1 = PAD_L - 4 + id_w + 44, chip_x - 30
    if rail1 - rail0 >= 230:
        mid = (rail0 + rail1) / 2
        e.append(f'<g stroke="{LINE}" stroke-width="2.4" fill="none" '
                 f'stroke-linejoin="round">'
                 f'<path d="M{fmt(rail0)} 191 H{fmt(mid - 62)} l14 -13 14 26 14 -26 '
                 f'14 26 14 -13 H{fmt(rail1)}"/>'
                 f'<circle cx="{fmt(rail0)}" cy="191" r="4.5" fill="{LINE}" stroke="none"/>'
                 f'<circle cx="{fmt(rail1)}" cy="191" r="4.5" fill="{LINE}" stroke="none"/>'
                 f'</g>')

    # --- style name + era ---------------------------------------------------
    name = str(meta.get("name_style", ""))
    yrs = f"{era['start']}–{era.get('end', era['start'])}" if era.get("start") else ""
    era_w = adv(yrs, 32, 3) + 40 if yrs else 0
    name_size = 46
    while name_size > 34 and adv(name, name_size, 1.2) > (PAD_R - PAD_L - era_w):
        name_size -= 2
    e.append(txt(PAD_L, 292, name, INK, name_size, weight=600, spacing=1.2))
    if yrs:
        e.append(txt(PAD_R, 292, yrs, MUTED, 32, weight=600, spacing=3, anchor="end"))

    # --- spec strip: topology left, tube complement right -------------------
    e.append(f'<rect x="{PAD_L}" y="312" width="{PAD_R - PAD_L}" height="1" fill="{LINE}"/>')
    # Two runs share this line, so it is set to fit: type comes down a short
    # ladder first, and only a strip that still will not fit gives up its tail
    # facet. The tube complement is never dropped.
    LADDER = ((19.0, 1.5), (18.0, 1.4), (17.0, 1.2), (16.0, 1.0))
    bits, gap, avail = spec_bits(meta), 30.0, float(PAD_R - PAD_L)
    while True:
        spec = " · ".join(bits)
        for size, sp in LADDER:
            if adv(spec, size, sp) + gap + adv(tubes, size, sp) <= avail:
                break
        else:
            if len(bits) > 2:
                bits = bits[:-1]
                continue
        break
    e.append(txt(PAD_L, 337, spec, MUTED, size, weight=600, spacing=sp))
    if tubes:
        e.append(txt(PAD_R, 337, tubes, FAINT, size, weight=600, spacing=sp,
                     anchor="end"))

    # --- the board band -----------------------------------------------------
    e.append(f'<g clip-path="url(#band)">'
             f'<rect x="0" y="{BAND_Y}" width="{CARD_W}" height="{BAND_H}" fill="#e9dcba"/>'
             f'<g transform="translate(0,{BAND_Y}) scale({fmt(s)}) '
             f'translate({fmt(-cx0)},{fmt(-cy0)})" '
             f'font-family="{DISP}">{sheet_inner(amp_dir / "layout-sheet.svg")}</g></g>')
    # seam: an amber rule where the dark card meets the drafting paper
    e.append(f'<rect x="0" y="{BAND_Y - 4}" width="{CARD_W}" height="4" fill="{AMBER}"/>')

    board = "turret" if "turret" in str((layout.get("board") or {}).get("title", "")).lower() \
        else "eyelet"
    alt = (f"{did} — {name}. Circuit Codex card: {spec_bits(meta)[0].lower()}, "
           f"with a detail of the redrawn {board}-board layout drawing.")
    body = "\n".join(e)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
            f'viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-label="{esc(alt)}">\n'
            f'<defs><clipPath id="band"><rect x="0" y="{BAND_Y}" width="{CARD_W}" '
            f'height="{BAND_H}"/></clipPath></defs>\n{body}\n</svg>\n')


# ---- rasterising -----------------------------------------------------------
def ensure_rsvg() -> str:
    exe = shutil.which("rsvg-convert")
    if exe:
        return exe
    raise SystemExit("rsvg-convert not found — install librsvg "
                     "(brew install librsvg / apt-get install librsvg2-bin)")


def write_png(svg: str, out: Path) -> None:
    """Rasterise at 1200x630 and quantise. The card's palette is small by
    construction (house inks, drafting paper, a handful of era wire colours), so
    an 8-bit palette is visually lossless here and keeps a card near 100 kB —
    small enough that a preview unrolls instantly."""
    exe = ensure_rsvg()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "card.svg"
        src.write_text(svg)
        raw = subprocess.run([exe, "-w", str(CARD_W), "-h", str(CARD_H), "-f", "png",
                              str(src)], stdout=subprocess.PIPE, check=True).stdout
    from io import BytesIO

    from PIL import Image
    img = Image.open(BytesIO(raw)).convert("RGB")
    pal = img.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.FLOYDSTEINBERG)
    buf, best = BytesIO(), None
    pal.save(buf, format="PNG", optimize=True)
    best = buf.getvalue()
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    if len(buf.getvalue()) < len(best):
        best = buf.getvalue()
    out.write_bytes(best)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def build(ids: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    cards = dict(manifest.get("cards") or {})
    for amp_id in ids:
        svg = card_svg(amp_id)
        out = OUT_DIR / f"{amp_id}.png"
        write_png(svg, out)
        cards[amp_id] = {"svg": sha(svg.encode()), "png": sha(out.read_bytes())}
        print(f"og {out.relative_to(ROOT)}  {out.stat().st_size // 1024} kB")
    MANIFEST.write_text(json.dumps(
        {"note": "Digests of the generated social cards. Regenerate with "
                 "pipeline/render_og.py; gated by pipeline/render_og.py --check.",
         "cards": dict(sorted(cards.items()))}, indent=2) + "\n")


def check() -> int:
    """Staleness gate. Needs no rsvg and no fonts: it rebuilds each card's SVG
    from the corpus and compares digests with the manifest written beside the
    committed PNGs, so an edited layout, meta.yaml or renderer shows up as a
    stale card, and a hand-edited PNG shows up too."""
    if not MANIFEST.exists():
        print("og cards missing — run pipeline/render_og.py", file=sys.stderr)
        return 1
    cards = (json.loads(MANIFEST.read_text()).get("cards") or {})
    ids = amp_ids()
    errs: list[str] = []
    for amp_id in ids:
        rec = cards.get(amp_id)
        png = OUT_DIR / f"{amp_id}.png"
        if rec is None:
            errs.append(f"{amp_id}: no social card")
            continue
        if not png.exists():
            errs.append(f"{amp_id}: site/public/og/{amp_id}.png missing")
            continue
        if sha(card_svg(amp_id).encode()) != rec.get("svg"):
            errs.append(f"{amp_id}: card is stale — its layout or metadata changed")
        elif sha(png.read_bytes()) != rec.get("png"):
            errs.append(f"{amp_id}: {amp_id}.png does not match the manifest")
    for extra in sorted(set(cards) - set(ids)):
        errs.append(f"{extra}: card for an amp that is no longer in the corpus")
    for msg in errs:
        print(f"FAIL {msg}", file=sys.stderr)
    if errs:
        print(f"\n{len(errs)} stale social card(s) — regenerate with "
              f"python3 pipeline/render_og.py", file=sys.stderr)
        return 1
    print(f"og cards: {len(ids)} current")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--check"]
    if "--check" in argv:
        return check()
    build(args or amp_ids())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
