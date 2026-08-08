#!/usr/bin/env python3
"""CI gate: every amps/<id>/schematic.kicad_sch must parse, round-trip through
kiutils (KiCad 6+ grammar check), tokenize the way KiCanvas does — and be a
drawing a reader can actually read.

The grammar checks catch a file KiCanvas refuses to open. They said nothing
about the far more common failure: a file that opens and is unusable. Three
classes of that shipped to the live site simultaneously —

  * lettering printed through live circuitry (a B+ flag over the sheet title,
    three tremolo sentences over a phase-shift ladder, a bias note over the
    power supply's own symbols);
  * drawings laid onto a fixed A4/A3 sheet regardless of their size, so
    KiCanvas's fit-to-page default framed mostly blank paper;
  * content laid into the bottom-right corner, where KiCad's worksheet prints
    the title block over the top of it.

None of the three is visible to a parser, and all three are pure geometry. So
this gate reconstructs the drawing's geometry from the file itself — symbol
bodies and pins from the sheet's own `lib_symbols`, property and free text from
the stroke-font metrics — and fails on overlap, on intrusion into the title
block, and on a sheet the drawing does not fill.

    python3 check_schematics.py            # gate
    python3 check_schematics.py --report   # list every box that overlaps
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from kiutils.schematic import Schematic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schematic_lib import (            # noqa: E402
    FRAME, TB_H, TB_W, label_box, text_box, _rot_local,
)

ROOT = Path(__file__).resolve().parent.parent

# A box pair must share this much in BOTH axes before it counts as a clash.
# Stroke-font advance here is an estimate (schematic_lib.CHAR_W): re-ruling
# this gate with the renderer's true advance table was tried 2026-08-08 and
# red-flagged 28 of 34 sheets over abutments already judged sub-visual, so
# the gate keeps the coarse ruler while PLACEMENT aims with the true one
# (schematic_lib's two-rulers note). Asking for a real overlap rather than a
# touch keeps the estimate from inventing findings.
OVERLAP_MM = 0.8

# Which side of its anchor a global label's name letters on. KiCanvas (and
# KiCad) draw the text horizontally at 0/180 and vertically at 90/270, then
# take the side from the justification, NOT from the rotation: the flag body
# lies right/below of the anchor at 0/90 and left/above at 180/270. Only
# these pairings put the name inside the flag outline; any other justification
# letters the net name over the very wire the flag terminates — which is how
# 219 rotated labels shipped with their names struck through, because nothing
# in this gate modelled global-label text at all.
GLABEL_JUSTIFY = {0: "left", 90: "left", 180: "right", 270: "right"}
# Fraction of the sheet's DRAWABLE area the drawing must occupy — drawable
# meaning inside the 10 mm frame and above the title-block strip, the region a
# drawing is actually allowed to use. Measuring against the raw page instead
# would charge every sheet for furniture it cannot avoid, and would make the
# gate unsatisfiable for a small circuit. Every sheet this pipeline emits is
# cut to its own drawing and lands near 90%; the way to fall under the floor is
# to pin a paper size by hand and leave the drawing rattling around inside it.
UTILISATION_FLOOR = 0.62


def strict_tokenize_errors(text: str) -> list[str]:
    """Tokenize the way KiCanvas does — stricter than kiutils.

    kiutils forgives a raw double quote inside a string; KiCanvas's tokenizer
    throws and the schematic renders as a blank panel (the AC15 'Vibravox'
    incident). A string ends at the first unescaped quote, and the next
    non-space character must close or open an s-expression.
    """
    errors: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            # A quote may only OPEN a string after whitespace or a paren —
            # a quote mid-atom is exactly where KiCanvas throws. (Two strings
            # back to back, '"Reference" "R"', are separated by a space and
            # are legal.)
            if i > 0 and text[i - 1] not in " \t\r\n(":
                errors.append(
                    f"quote opens mid-atom at index {i}: "
                    f"{text[max(0, i - 30):i + 12]!r}")
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            if j >= n:
                errors.append(f"unterminated string opened at index {i}")
            i = j + 1
        else:
            i += 1
    return errors


# ---------------------------------------------------------------------------
# Geometry, reconstructed from the file
# ---------------------------------------------------------------------------
def _lib_geometry(sch: Schematic) -> dict[str, tuple]:
    """For each library symbol: (body box, [pin segment boxes]) in symbol space.

    Body and pins are kept apart on purpose. A tube is a circle in a square
    box; its bounding rectangle's corners are empty paper, and lettering placed
    there is correct, not a clash. Pins are thin — a 0.5 mm-wide segment each —
    so a designator sitting beside a pin stub does not read as an overlap
    either."""
    out: dict[str, tuple] = {}
    for lib in sch.libSymbols:
        bx: list[float] = []
        by: list[float] = []
        pins: list[tuple[float, float, float, float]] = []
        for unit in [lib, *lib.units]:
            for g in unit.graphicItems:
                for x, y in _shape_points(g):
                    bx.append(x)
                    by.append(y)
            for p in unit.pins:
                x, y, ang = p.position.X, p.position.Y, (p.position.angle or 0)
                dx, dy = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}[int(ang) % 360]
                ex, ey = x + dx * p.length, y + dy * p.length
                pins.append((min(x, ex) - 0.25, min(y, ey) - 0.25,
                             max(x, ex) + 0.25, max(y, ey) + 0.25))
        body = (min(bx), min(by), max(bx), max(by)) if bx else None
        out[lib.libId if ":" in lib.libId else f"cx:{lib.entryName}"] = (body, pins)
    return out


def _shape_points(g) -> list[tuple[float, float]]:
    name = type(g).__name__
    if name == "SyRect":
        return [(g.start.X, g.start.Y), (g.end.X, g.end.Y)]
    if name == "SyCircle":
        c, r = g.center, g.radius
        return [(c.X - r, c.Y - r), (c.X + r, c.Y + r)]
    if name == "SyArc":
        return [(g.start.X, g.start.Y), (g.mid.X, g.mid.Y), (g.end.X, g.end.Y)]
    if name == "SyPolyLine":
        return [(p.X, p.Y) for p in g.points]
    return []


def _place(box, x, y, rot, mirror) -> tuple[float, float, float, float]:
    pts = [_rot_local(a, b, rot, mirror)
           for a in (box[0], box[2]) for b in (box[1], box[3])]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts),
            x + max(p[0] for p in pts), y + max(p[1] for p in pts))


def sheet_boxes(sch: Schematic) -> list[tuple[str, str, float, float, float, float]]:
    """Every inked element as (class, label, x0, y0, x1, y1)."""
    geo = _lib_geometry(sch)
    out: list[tuple] = []
    for s in sch.schematicSymbols:
        x, y = s.position.X, s.position.Y
        rot = int(s.position.angle or 0)
        mirror = s.mirror or ""
        body, pins = geo.get(s.libId, (None, []))
        ref = next((p.value for p in s.properties if p.key == "Reference"), s.libId)
        if body:
            out.append(("symbol", ref, *_place(body, x, y, rot, mirror)))
        for pin in pins:
            out.append(("pin", ref, *_place(pin, x, y, rot, mirror)))
        for p in s.properties:
            if p.effects and p.effects.hide:
                continue
            size = p.effects.font.height if p.effects else 1.27
            out.append(("property", f"{ref}.{p.key}={p.value}",
                        *text_box(p.value, p.position.X, p.position.Y, size)))
    for t in sch.texts:
        size = t.effects.font.height if t.effects else 1.6
        out.append(("text", t.text, *text_box(t.text, t.position.X, t.position.Y, size)))
    for lab in [*sch.globalLabels, *sch.labels, *sch.hierarchicalLabels]:
        out.append(("label", lab.text,
                    *label_box(lab.text, lab.position.X, lab.position.Y,
                               int(lab.position.angle or 0))))
    for g in sch.graphicalItems:
        pts = getattr(g, "points", None)
        if not pts:
            continue
        out.append(("wire", "", min(p.X for p in pts), min(p.Y for p in pts),
                    max(p.X for p in pts), max(p.Y for p in pts)))
    for j in sch.junctions:
        out.append(("wire", "", j.position.X - 0.4, j.position.Y - 0.4,
                    j.position.X + 0.4, j.position.Y + 0.4))
    return out


def _overlap(a, b) -> tuple[float, float]:
    """Shared extent of two (class, label, x0, y0, x1, y1) boxes, per axis."""
    return (min(a[4], b[4]) - max(a[2], b[2]),
            min(a[5], b[5]) - max(a[3], b[3]))


# Which class pairs are a defect. Wires cross symbols and each other by design;
# a pin ends inside its own body; lettering, however, must never be printed
# over another glyph or over live circuitry.
CLASH_PAIRS = {
    ("text", "symbol"), ("text", "text"), ("text", "property"), ("text", "label"),
    ("property", "symbol"), ("property", "property"), ("property", "label"),
    ("label", "symbol"), ("label", "label"),
    # schematic_lib.Sch.boxes() names its classes the same way, so the same
    # table drives the in-script debug view (see the module docstring).
    ("value", "symbol"), ("ref", "symbol"), ("spec", "symbol"),
}


def lint_sheet(sch: Schematic, boxes) -> list[str]:
    errs: list[str] = []

    # Global-label text geometry: the name must letter INSIDE the flag body,
    # which happens only when justification compensates rotation (see
    # GLABEL_JUSTIFY). The flag box itself is already in the collision set;
    # this clause pins the text to it.
    for lab in sch.globalLabels:
        rot = int(lab.position.angle or 0) % 360
        want = GLABEL_JUSTIFY.get(rot)
        have = (lab.effects and lab.effects.justify
                and lab.effects.justify.horizontally) or "left"
        if want and have != want:
            errs.append(f"global label {lab.text!r} at {rot} deg carries "
                        f"(justify {have}) — its name letters outside the flag, "
                        f"struck through by its own wire; needs (justify {want})")

    lettering = [b for b in boxes if b[0] in ("text", "property", "label", "symbol")]
    for i, a in enumerate(lettering):
        for b in lettering[i + 1:]:
            pair = (a[0], b[0]) if (a[0], b[0]) in CLASH_PAIRS else (b[0], a[0])
            if pair not in CLASH_PAIRS:
                continue
            ox, oy = _overlap(a, b)
            if ox >= OVERLAP_MM and oy >= OVERLAP_MM:
                errs.append(f"overlap {a[0]} {a[1]!r} x {b[0]} {b[1]!r} "
                            f"({ox:.1f} x {oy:.1f} mm)")

    paper = sch.paper
    std = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
           "A3": (420, 297), "A4": (297, 210), "A5": (210, 148)}
    if paper.paperSize == "User":
        pw, ph = paper.width, paper.height
    else:
        pw, ph = std.get(paper.paperSize, (297, 210))
        if paper.portrait:
            pw, ph = ph, pw

    # KiCad's worksheet hangs a 110 x 34 mm title block off the bottom-right
    # corner and prints it over anything laid there.
    tb = (pw - TB_W, ph - TB_H, pw, ph)
    for b in boxes:
        ox = min(b[4], tb[2]) - max(b[2], tb[0])
        oy = min(b[5], tb[3]) - max(b[3], tb[1])
        if ox > 0 and oy > 0:
            errs.append(f"title-block region holds {b[0]} {b[1]!r}")
    for b in boxes:
        if b[2] < FRAME - 0.5 or b[3] < FRAME - 0.5 or b[4] > pw - FRAME + 0.5 or b[5] > ph - FRAME + 0.5:
            errs.append(f"outside the {FRAME:g} mm frame: {b[0]} {b[1]!r}")

    if boxes:
        x0 = min(b[2] for b in boxes)
        y0 = min(b[3] for b in boxes)
        x1 = max(b[4] for b in boxes)
        y1 = max(b[5] for b in boxes)
        draw_w = max(pw - 2 * FRAME, 1.0)
        draw_h = max(ph - FRAME - TB_H, 1.0)
        util = ((x1 - x0) * (y1 - y0)) / (draw_w * draw_h)
        if util < UTILISATION_FLOOR:
            errs.append(f"sheet utilisation {util:.0%} < {UTILISATION_FLOOR:.0%} "
                        f"— drawing {x1 - x0:.0f}x{y1 - y0:.0f} in a "
                        f"{draw_w:.0f}x{draw_h:.0f} drawable area "
                        f"({pw:.0f}x{ph:.0f} paper)")
    return errs


def main() -> int:
    report = "--report" in sys.argv
    files = sorted((ROOT / "amps").glob("*/schematic.kicad_sch"))
    failures = 0
    for f in files:
        try:
            sch = Schematic.from_file(str(f))
            with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=True) as tmp:
                sch.to_file(tmp.name)
            strict = strict_tokenize_errors(f.read_text())
            if strict:
                raise ValueError(
                    "KiCanvas-strict tokenization failed: " + "; ".join(strict[:3]))
            tb = sch.titleBlock
            if not tb or not tb.title or not tb.date:
                raise ValueError("empty title block (title/date) — the sheet "
                                 "must name itself from meta.yaml")
            errs = lint_sheet(sch, sheet_boxes(sch))
            if errs:
                raise ValueError(f"{len(errs)} layout problem(s): "
                                 + ("; ".join(errs) if report else "; ".join(errs[:4])))
            print(f"ok   {f.relative_to(ROOT)}: {len(sch.schematicSymbols)} symbols")
        except Exception as exc:  # noqa: BLE001 — any parse failure is a CI failure
            print(f"FAIL {f.relative_to(ROOT)}: {exc}")
            failures += 1
    print(f"checked {len(files)} schematic(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
