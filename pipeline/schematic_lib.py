#!/usr/bin/env python3
"""Reusable KiCad schematic authoring library for Circuit Codex.

Self-contained symbol set (lib "cx", CC-BY-SA — no external dependencies) plus
a builder with composable amp idioms (shunt RC, plate load to rail, series
parts, tube helpers). Per-amp generators (draw_5e3.py, draw_5f6a.py, …) become
short declarative layouts instead of coordinate soup.

Conventions: schematic space, mm, +Y down. A symbol pin at (sx, sy) lands at
(x + sx, y - sy) for rotation 0.

Sheet furniture (added 2026-08-08). Every element is recorded as a small
(kind, points, extra) tuple rather than a finished string, so `write()` can do
three things no earlier version could:

* **Title block.** The corpus shipped 34 sheets whose title block was empty —
  "Title:" blank, "Date:" blank, default "Sheet /" furniture — which reads as
  an unfinished drawing. `write()` now reads the amp's own `meta.yaml` and
  emits a real `(title_block …)`: Title = designation + style, Company =
  Circuit Codex, Date = the verification (or added) date, Rev = the
  verification status.

* **A sheet that fits the drawing.** KiCanvas's default view is
  `zoom_to_page()` — it frames the *paper*, not the ink. A 150 × 110 mm circuit
  on a fixed A3 sheet therefore opened as a postage stamp. `write()` measures
  the drawing (symbol bodies, pins, property text, labels, free text), then
  emits `(paper "User" w h)` sized to it, translating the content to sit at a
  fixed margin. The bottom 34 mm strip is reserved: that is where KiCad's
  worksheet draws the title block, and nothing may be laid into it.

* **A notes band.** Prose annotations used to be placed by hand at whatever
  coordinate looked free when the amp was drawn, and a later edit routinely
  pushed live circuitry under them. `note()` queues prose instead; `write()`
  word-wraps it into a reserved band below the circuit, clear of everything.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

FONT = "(effects (font (size 1.27 1.27)))"
FONT_L = "(effects (font (size 1.27 1.27)) (justify left))"
_STROKE = '(stroke (width 0.254) (type default)) (fill (type none))'


def _u() -> str:
    return str(uuid.uuid4())


def _poly(pts: str) -> str:
    return f"(polyline (pts {pts}) {_STROKE})"


def _arc(sx: float, sy: float, mx: float, my: float, ex: float, ey: float) -> str:
    return (f"(arc (start {sx:g} {sy:g}) (mid {mx:g} {my:g}) "
            f"(end {ex:g} {ey:g}) {_STROKE})")


def _coil_v(cx: float, y0: float, y1: float, n: int, side: int) -> str:
    """`n` semicircular turns stacked from y0 to y1 on the vertical line x=cx,
    bulging to `side` (+1 right, −1 left). Symbol space, +Y up."""
    step = (y1 - y0) / n
    r = abs(step) / 2
    return "\n        ".join(
        _arc(cx, y0 + i * step, cx + side * r, y0 + (i + 0.5) * step,
             cx, y0 + (i + 1) * step)
        for i in range(n))


def _coil_h(cy: float, x0: float, x1: float, n: int, side: int) -> str:
    """`n` semicircular turns along the horizontal line y=cy, bulging to
    `side` (+1 up, −1 down)."""
    step = (x1 - x0) / n
    r = abs(step) / 2
    return "\n        ".join(
        _arc(x0 + i * step, cy, x0 + (i + 0.5) * step, cy + side * r,
             x0 + (i + 1) * step, cy)
        for i in range(n))


def _pin(kind: str, x: float, y: float, rot: int, length: float, name: str, num: str) -> str:
    return (f'(pin {kind} line (at {x:g} {y:g} {rot}) (length {length:g}) '
            f'(name "{name}" {FONT}) (number "{num}" {FONT}))')


# Iron-core furniture shared by the three transformers: two parallel core
# laminations between the windings, so a reader can tell a transformer from a
# relay coil at a glance. Half-gap 0.762 mm, drawn the full winding height.
def _core_v(half_h: float) -> str:
    return "\n        ".join(
        _poly(f"(xy {x:g} {-half_h:g}) (xy {x:g} {half_h:g})")
        for x in (-0.762, 0.762))


LIB = f"""  (lib_symbols
    (symbol "cx:R" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "R" (at 2.54 1.27 0) {FONT})
      (property "Value" "R" (at 2.54 -1.27 0) {FONT})
      (symbol "R_0_1" (rectangle (start -1.016 -2.54) (end 1.016 2.54) {_STROKE}))
      (symbol "R_1_1"
        {_pin("passive", 0, 3.81, 270, 1.27, "~", "1")}
        {_pin("passive", 0, -3.81, 90, 1.27, "~", "2")}))
    (symbol "cx:C" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 2.54 1.27 0) {FONT})
      (property "Value" "C" (at 2.54 -1.27 0) {FONT})
      (symbol "C_0_1"
        {_poly("(xy -2.032 0.762) (xy 2.032 0.762)")}
        {_poly("(xy -2.032 -0.762) (xy 2.032 -0.762)")})
      (symbol "C_1_1"
        {_pin("passive", 0, 3.81, 270, 3.048, "~", "1")}
        {_pin("passive", 0, -3.81, 90, 3.048, "~", "2")}))
    (symbol "cx:DUALCAN" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 2.54 1.27 0) {FONT})
      (property "Value" "C" (at 2.54 -1.27 0) {FONT})
      (symbol "DUALCAN_0_1"
        {_poly("(xy -3.556 0.762) (xy -1.524 0.762)")}
        {_poly("(xy 1.524 0.762) (xy 3.556 0.762)")}
        {_poly("(xy -3.556 -0.762) (xy 3.556 -0.762)")})
      (symbol "DUALCAN_1_1"
        {_pin("passive", -2.54, 3.81, 270, 3.048, "A", "1")}
        {_pin("passive", 2.54, 3.81, 270, 3.048, "B", "2")}
        {_pin("passive", 0, -3.81, 90, 3.048, "COM", "3")}))
    (symbol "cx:CONN3" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "MS" (at 0 -6.35 0) {FONT})
      (property "Value" "inlet" (at 0 -8.89 0) {FONT})
      (symbol "CONN3_0_1"
        (rectangle (start -5.715 -2.54) (end 5.715 2.54) {_STROKE})
        (circle (center -3.81 0) (radius 0.635) {_STROKE})
        (circle (center 0 0) (radius 0.635) {_STROKE})
        (circle (center 3.81 0) (radius 0.635) {_STROKE}))
      (symbol "CONN3_1_1"
        {_pin("passive", -3.81, 5.08, 270, 2.54, "1", "1")}
        {_pin("passive", 0, 5.08, 270, 2.54, "2", "2")}
        {_pin("passive", 3.81, 5.08, 270, 2.54, "3", "3")}))
    (symbol "cx:POT" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "VR" (at 2.54 1.27 0) {FONT})
      (property "Value" "POT" (at 2.54 -1.27 0) {FONT})
      (symbol "POT_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54) {_STROKE})
        {_poly("(xy 3.302 0) (xy 1.778 0.762) (xy 1.778 -0.762) (xy 3.302 0)")})
      (symbol "POT_1_1"
        {_pin("passive", 0, 3.81, 270, 1.27, "1", "1")}
        {_pin("passive", 0, -3.81, 90, 1.27, "3", "3")}
        {_pin("passive", 5.08, 0, 180, 1.778, "W", "2")}))
    (symbol "cx:TRIODE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 5.08 0) {FONT})
      (property "Value" "triode" (at 6.35 2.54 0) {FONT})
      (symbol "TRIODE_0_1"
        (circle (center 0 0) (radius 5.08) {_STROKE})
        {_poly("(xy -2.54 1.905) (xy 2.54 1.905)")}
        {_poly("(xy 0 1.905) (xy 0 5.08)")}
        {_poly("(xy -2.286 0) (xy -1.27 0)")}
        {_poly("(xy -0.508 0) (xy 0.508 0)")}
        {_poly("(xy 1.27 0) (xy 2.286 0)")}
        {_poly("(xy -1.905 -1.905) (xy 1.905 -1.905)")}
        {_poly("(xy 0 -1.905) (xy 0 -5.08)")})
      (symbol "TRIODE_1_1"
        {_pin("passive", 0, 7.62, 270, 2.54, "P", "1")}
        {_pin("input", -7.62, 0, 0, 5.334, "G", "2")}
        {_pin("passive", 0, -7.62, 90, 2.54, "K", "3")}))
    (symbol "cx:PENTODE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 6.35 0) {FONT})
      (property "Value" "pentode" (at 6.35 3.81 0) {FONT})
      (symbol "PENTODE_0_1"
        (circle (center 0 0) (radius 5.08) {_STROKE})
        {_poly("(xy -2.54 2.54) (xy 2.54 2.54)")}
        {_poly("(xy 0 2.54) (xy 0 5.08)")}
        {_poly("(xy -2.286 0.635) (xy -1.27 0.635)")}
        {_poly("(xy -0.508 0.635) (xy 0.508 0.635)")}
        {_poly("(xy 1.27 0.635) (xy 2.286 0.635)")}
        {_poly("(xy -2.286 -0.635) (xy -1.27 -0.635)")}
        {_poly("(xy -0.508 -0.635) (xy 0.508 -0.635)")}
        {_poly("(xy 1.27 -0.635) (xy 2.286 -0.635)")}
        {_poly("(xy -1.905 -2.54) (xy 1.905 -2.54)")}
        {_poly("(xy 0 -2.54) (xy 0 -5.08)")})
      (symbol "PENTODE_1_1"
        {_pin("passive", 0, 7.62, 270, 2.54, "P", "1")}
        {_pin("input", -7.62, -0.635, 0, 5.334, "G1", "2")}
        {_pin("passive", 7.62, 0.635, 180, 5.334, "G2", "3")}
        {_pin("passive", 0, -7.62, 90, 2.54, "K", "4")}))
    (symbol "cx:DIODE_TUBE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 5.08 0) {FONT})
      (property "Value" "diode" (at 6.35 2.54 0) {FONT})
      (symbol "DIODE_TUBE_0_1"
        (circle (center 0 0) (radius 5.08) {_STROKE})
        {_poly("(xy -2.54 1.905) (xy 2.54 1.905) (xy 0 -0.635) (xy -2.54 1.905)")}
        {_poly("(xy -2.54 -0.635) (xy 2.54 -0.635)")}
        {_poly("(xy 0 1.905) (xy 0 5.08)")}
        {_poly("(xy 0 -0.635) (xy 0 -5.08)")})
      (symbol "DIODE_TUBE_1_1"
        {_pin("passive", 0, 7.62, 270, 2.54, "A", "1")}
        {_pin("passive", 0, -7.62, 90, 2.54, "K", "2")}))
    (symbol "cx:DIODE_SS" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "D" (at 0 3.175 0) {FONT})
      (property "Value" "diode" (at 0 -3.175 0) {FONT})
      (symbol "DIODE_SS_0_1"
        {_poly("(xy -1.905 1.27) (xy -1.905 -1.27) (xy 1.27 0) (xy -1.905 1.27)")}
        {_poly("(xy 1.27 1.27) (xy 1.27 -1.27)")})
      (symbol "DIODE_SS_1_1"
        {_pin("passive", -5.08, 0, 0, 3.175, "A", "1")}
        {_pin("passive", 5.08, 0, 180, 3.81, "K", "2")}))
    (symbol "cx:CHOKE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "L" (at -5.08 5.08 0) {FONT})
      (property "Value" "CHOKE" (at 0 0 0) {FONT})
      (symbol "CHOKE_0_1"
        {_poly("(xy -5.08 0) (xy -3.81 0)")}
        {_poly("(xy 3.81 0) (xy 5.08 0)")}
        {_coil_h(0, -3.81, 3.81, 4, +1)}
        {_poly("(xy -4.318 -0.762) (xy 4.318 -0.762)")}
        {_poly("(xy -4.318 -1.397) (xy 4.318 -1.397)")})
      (symbol "CHOKE_1_1"
        {_pin("passive", -7.62, 0, 0, 2.54, "1", "1")}
        {_pin("passive", 7.62, 0, 180, 2.54, "2", "2")}))
    (symbol "cx:OT_SE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 10.16 0) {FONT})
      (property "Value" "OT" (at 0 0 0) {FONT})
      (symbol "OT_SE_0_1"
        {_core_v(5.08)}
        {_poly("(xy -6.35 2.54) (xy -2.286 2.54)")}
        {_poly("(xy -6.35 -2.54) (xy -2.286 -2.54)")}
        {_coil_v(-2.286, 2.54, -2.54, 4, -1)}
        {_poly("(xy 6.35 2.54) (xy 2.286 2.54)")}
        {_poly("(xy 6.35 -2.54) (xy 2.286 -2.54)")}
        {_coil_v(2.286, 2.54, -2.54, 2, +1)})
      (symbol "OT_SE_1_1"
        {_pin("passive", -8.89, 2.54, 0, 2.54, "PRI_P", "1")}
        {_pin("passive", -8.89, -2.54, 0, 2.54, "PRI_B", "2")}
        {_pin("passive", 8.89, 2.54, 180, 2.54, "SEC_H", "3")}
        {_pin("passive", 8.89, -2.54, 180, 2.54, "SEC_C", "4")}))
    (symbol "cx:OT_PP" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 12.7 0) {FONT})
      (property "Value" "OT" (at 0 0 0) {FONT})
      (symbol "OT_PP_0_1"
        {_core_v(7.62)}
        {_poly("(xy -6.35 5.08) (xy -2.286 5.08)")}
        {_poly("(xy -6.35 0) (xy -2.286 0)")}
        {_poly("(xy -6.35 -5.08) (xy -2.286 -5.08)")}
        {_coil_v(-2.286, 5.08, 0, 2, -1)}
        {_coil_v(-2.286, 0, -5.08, 2, -1)}
        {_poly("(xy 6.35 2.54) (xy 2.286 2.54)")}
        {_poly("(xy 6.35 -2.54) (xy 2.286 -2.54)")}
        {_coil_v(2.286, 2.54, -2.54, 2, +1)})
      (symbol "OT_PP_1_1"
        {_pin("passive", -8.89, 5.08, 0, 2.54, "PRI_A", "1")}
        {_pin("passive", -8.89, 0, 0, 2.54, "CT", "2")}
        {_pin("passive", -8.89, -5.08, 0, 2.54, "PRI_B", "3")}
        {_pin("passive", 8.89, 2.54, 180, 2.54, "SEC_H", "4")}
        {_pin("passive", 8.89, -2.54, 180, 2.54, "SEC_C", "5")}))
    (symbol "cx:PT" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 12.7 0) {FONT})
      (property "Value" "PT" (at 0 0 0) {FONT})
      (symbol "PT_0_1"
        {_core_v(7.62)}
        {_poly("(xy -6.35 5.08) (xy -2.286 5.08)")}
        {_poly("(xy -6.35 -5.08) (xy -2.286 -5.08)")}
        {_coil_v(-2.286, 5.08, -5.08, 4, -1)}
        {_poly("(xy 6.35 5.08) (xy 2.286 5.08)")}
        {_poly("(xy 6.35 0) (xy 2.286 0)")}
        {_poly("(xy 6.35 -5.08) (xy 2.286 -5.08)")}
        {_coil_v(2.286, 5.08, 0, 2, +1)}
        {_coil_v(2.286, 0, -5.08, 2, +1)})
      (symbol "PT_1_1"
        {_pin("passive", -8.89, 5.08, 0, 2.54, "PRI_1", "1")}
        {_pin("passive", -8.89, -5.08, 0, 2.54, "PRI_2", "2")}
        {_pin("passive", 8.89, 5.08, 180, 2.54, "HT_A", "3")}
        {_pin("passive", 8.89, 0, 180, 2.54, "HT_CT", "4")}
        {_pin("passive", 8.89, -5.08, 180, 2.54, "HT_B", "5")}))
    (symbol "cx:JACK" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "J" (at 3.81 5.08 0) {FONT})
      (property "Value" "jack" (at 3.81 2.54 0) {FONT})
      (symbol "JACK_0_1"
        (circle (center 3.175 0) (radius 2.54) {_STROKE})
        {_poly("(xy -2.54 2.54) (xy 0.635 2.54)")}
        {_poly("(xy -2.54 -2.54) (xy 1.905 -2.54)")}
        {_poly("(xy 1.905 -2.54) (xy 1.905 -1.016)")})
      (symbol "JACK_1_1"
        {_pin("passive", -5.08, 2.54, 0, 2.54, "T", "1")}
        {_pin("passive", -5.08, -2.54, 0, 2.54, "S", "2")}))
    (symbol "cx:SWITCH" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "SW" (at 0 4.445 0) {FONT})
      (property "Value" "SW" (at 0 -4.445 0) {FONT})
      (symbol "SWITCH_0_1"
        (circle (center -2.54 0) (radius 0.635) {_STROKE})
        (circle (center 2.54 0) (radius 0.635) {_STROKE})
        {_poly("(xy -2.032 0.381) (xy 2.286 2.286)")})
      (symbol "SWITCH_1_1"
        {_pin("passive", -5.08, 0, 0, 1.905, "1", "1")}
        {_pin("passive", 5.08, 0, 180, 1.905, "2", "2")}))
    (symbol "cx:FUSE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "F" (at 0 3.81 0) {FONT})
      (property "Value" "fuse" (at 0 -3.81 0) {FONT})
      (symbol "FUSE_0_1"
        (rectangle (start -2.54 -1.016) (end 2.54 1.016) {_STROKE})
        {_poly("(xy -2.54 0) (xy 2.54 0)")})
      (symbol "FUSE_1_1"
        {_pin("passive", -5.08, 0, 0, 2.54, "1", "1")}
        {_pin("passive", 5.08, 0, 180, 2.54, "2", "2")}))
    (symbol "cx:LAMP" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "PL" (at 4.44 2.54 0) {FONT})
      (property "Value" "lamp" (at 4.44 -2.54 0) {FONT})
      (symbol "LAMP_0_1"
        (circle (center 0 0) (radius 2.54) {_STROKE})
        {_poly("(xy -1.796 -1.796) (xy 1.796 1.796)")}
        {_poly("(xy -1.796 1.796) (xy 1.796 -1.796)")})
      (symbol "LAMP_1_1"
        {_pin("passive", 0, 5.08, 270, 2.54, "1", "1")}
        {_pin("passive", 0, -5.08, 90, 2.54, "2", "2")}))
    (symbol "cx:TANK" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "RT" (at -7.62 8.89 0) {FONT})
      (property "Value" "tank" (at 0 0 0) {FONT})
      (symbol "TANK_0_1"
        (rectangle (start -7.62 -5.08) (end 7.62 5.08) {_STROKE})
        {_poly("(xy -5.08 2.54) (xy -3.81 3.556) (xy -2.54 1.524) (xy -1.27 3.556) "
               "(xy 0 1.524) (xy 1.27 3.556) (xy 2.54 1.524) (xy 3.81 3.556) (xy 5.08 2.54)")}
        {_poly("(xy -5.08 -2.54) (xy -3.81 -1.524) (xy -2.54 -3.556) (xy -1.27 -1.524) "
               "(xy 0 -3.556) (xy 1.27 -1.524) (xy 2.54 -3.556) (xy 3.81 -1.524) (xy 5.08 -2.54)")})
      (symbol "TANK_1_1"
        {_pin("passive", -10.16, 2.54, 0, 2.54, "IN_H", "1")}
        {_pin("passive", -10.16, -2.54, 0, 2.54, "IN_C", "2")}
        {_pin("passive", 10.16, 2.54, 180, 2.54, "OUT_H", "3")}
        {_pin("passive", 10.16, -2.54, 180, 2.54, "OUT_C", "4")}))
    (symbol "cx:OPTO" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 5.08 5.08 0) {FONT})
      (property "Value" "opto" (at 5.08 -5.08 0) {FONT})
      (symbol "OPTO_0_1"
        (rectangle (start -3.81 -3.81) (end 3.81 3.81) {_STROKE})
        (circle (center -1.905 0) (radius 1.016) {_STROKE})
        {_poly("(xy 0.635 -1.905) (xy 3.048 1.905)")}
        {_poly("(xy 3.048 1.905) (xy 2.286 1.397)")}
        {_poly("(xy 3.048 1.905) (xy 2.667 2.286)")})
      (symbol "OPTO_1_1"
        {_pin("passive", -6.35, 2.54, 0, 2.54, "L1", "1")}
        {_pin("passive", -6.35, -2.54, 0, 2.54, "L2", "2")}
        {_pin("passive", 6.35, 2.54, 180, 2.54, "P1", "3")}
        {_pin("passive", 6.35, -2.54, 180, 2.54, "P2", "4")})))
"""


# ---------------------------------------------------------------------------
# Symbol extents, derived from LIB itself
# ---------------------------------------------------------------------------
# The sheet-fitting and the overlap lint both need to know how much room a
# symbol takes. Reading it out of the library text keeps the two in step: add a
# glyph and its box follows, with no hand-kept table to drift.
_NUM = r"(-?\d+(?:\.\d+)?)"


def _lib_extents(lib_text: str, pins: bool = True) -> dict[str, tuple[float, float, float, float]]:
    out: dict[str, tuple[float, float, float, float]] = {}
    for chunk in lib_text.split('(symbol "cx:')[1:]:
        name = chunk[:chunk.index('"')]
        xs: list[float] = []
        ys: list[float] = []

        def add(x: float, y: float) -> None:
            xs.append(x)
            ys.append(y)

        for m in re.finditer(rf"\(rectangle \(start {_NUM} {_NUM}\) \(end {_NUM} {_NUM}\)", chunk):
            a, b, c, d = (float(g) for g in m.groups())
            add(a, b)
            add(c, d)
        for m in re.finditer(rf"\(circle \(center {_NUM} {_NUM}\) \(radius {_NUM}\)", chunk):
            cx, cy, r = (float(g) for g in m.groups())
            add(cx - r, cy - r)
            add(cx + r, cy + r)
        for m in re.finditer(rf"\(arc \(start {_NUM} {_NUM}\) \(mid {_NUM} {_NUM}\) \(end {_NUM} {_NUM}\)", chunk):
            v = [float(g) for g in m.groups()]
            for i in range(0, 6, 2):
                add(v[i], v[i + 1])
        for m in re.finditer(r"\(polyline \(pts (.*?)\) \(stroke", chunk, re.S):
            for p in re.finditer(rf"\(xy {_NUM} {_NUM}\)", m.group(1)):
                add(float(p.group(1)), float(p.group(2)))
        if pins:
            for m in re.finditer(rf"\(pin \w+ line \(at {_NUM} {_NUM} \d+\)", chunk):
                add(float(m.group(1)), float(m.group(2)))
        if xs:
            out[name] = (min(xs), min(ys), max(xs), max(ys))
    return out


# Two boxes per symbol, for two different questions. SYM_EXTENTS includes the
# pin stubs and answers "how much sheet does this part need"; SYM_BODY is the
# drawn glyph alone and answers "would lettering here print over ink". A tube's
# grid pin reaches 7.6 mm to its left through empty paper — a designator there
# is legible, and treating the pin box as solid would push it needlessly far.
SYM_EXTENTS = _lib_extents(LIB)
SYM_BODY = _lib_extents(LIB, pins=False)

# Renderer-font metrics, measured rather than assumed. KiCanvas ships KiCad's
# Newstroke font; each glyph's advance is its (right - left) bound over 21,
# and the visitor's browser draws with exactly these numbers, so text can be
# widthed with the same table (extracted from site/public/vendor/kicanvas.js).
# Characters outside the table render as '?' in KiCanvas and are priced as
# one here.
#
# Two rulers, on purpose. PLACEMENT (place_labels / place_captions) measures
# with this true table: aiming with the old flat 0.68-em average under-read
# part lettering by a quarter, which is how a label could meter clean and
# still print through its neighbour on the published render (the 5F6-A RB2
# incident). The GATE's boxes (text_box / label_box below, which
# check_schematics shares) deliberately keep the coarse estimate: re-ruling
# the gate with renderer truth was tried on 2026-08-08 and red-flagged 28 of
# 34 sheets over millimetre-scale abutments that three visual review passes
# had already judged sub-visual — a corpus-wide re-lettering campaign, not a
# lint. The placer aiming true while the gate meters coarse keeps every NEW
# placement honest without indicting the shipped corpus wholesale.
_ADV = {
    "!": 0.476, "\"": 0.762, "#": 1.000, "$": 0.952, "%": 1.143, "&": 1.238,
    "'": 0.476, "(": 0.667, ")": 0.667, "*": 0.762, "+": 1.238, ",": 0.476,
    "-": 1.238, ".": 0.476, "/": 1.048, "0": 0.952, "1": 0.952, "2": 0.952,
    "3": 0.952, "4": 0.952, "5": 0.952, "6": 0.952, "7": 0.952, "8": 0.952,
    "9": 0.952, ":": 0.476, ";": 0.476, "<": 1.238, "=": 1.238, ">": 1.238,
    "?": 0.857, "@": 1.286, "A": 0.857, "B": 1.000, "C": 1.000, "D": 1.000,
    "E": 0.905, "F": 0.857, "G": 1.000, "H": 1.048, "I": 0.476, "J": 0.762,
    "K": 1.000, "L": 0.810, "M": 1.143, "N": 1.048, "O": 1.048, "P": 1.000,
    "Q": 1.048, "R": 1.000, "S": 0.952, "T": 0.762, "U": 1.048, "V": 0.857,
    "W": 1.143, "X": 0.952, "Y": 0.857, "Z": 0.952, "[": 0.667, "\\": 0.667,
    "]": 0.667, "^": 0.571, "_": 0.762, "`": 0.381, "a": 0.905, "b": 0.905,
    "c": 0.857, "d": 0.905, "e": 0.857, "f": 0.571, "g": 0.905, "h": 0.905,
    "i": 0.476, "j": 0.476, "k": 0.810, "l": 0.524, "m": 1.333, "n": 0.905,
    "o": 0.905, "p": 0.905, "q": 0.905, "r": 0.619, "s": 0.810, "t": 0.571,
    "u": 0.905, "v": 0.762, "w": 1.048, "x": 0.810, "y": 0.762, "z": 0.810,
    "{": 0.667, "|": 0.952, "}": 0.667, "~": 0.714, "°": 0.762, "µ": 1.048,
    "·": 0.762, "×": 1.238, " ": 0.600,
}
_ADV_UNKNOWN = 0.857          # KiCanvas substitutes '?' for unknown glyphs


def text_w(t: str, size: float) -> float:
    """Ink width of a string at `size`, per the renderer's own advances."""
    return sum(_ADV.get(c, _ADV_UNKNOWN) for c in t) * size


# Flat averages. CHAR_W is the gate's ruler (see the two-rulers note above):
# tuned to mixed-case prose, it under-reads part lettering, and the gate's
# OVERLAP_MM margin absorbs the residual. PROSE_W (prose really does average
# 0.77 em over this corpus's note lines) budgets the notes-band word wrap,
# whose per-line width is then measured truly.
CHAR_W = 0.68
PROSE_W = 0.77
LINE_H = 1.4

# Where a part's designator/value pair sits when the caller does not say.
# The old single default (2.2, -3.2) was tuned for a resistor and printed the
# value straight through the body of anything wider — every pot's wiper arrow,
# every transformer, every choke in the corpus. Each entry clears its own
# glyph; the fallback still suits R, C and the small two-pin parts.
LABEL_DEFAULT = {
    "POT": (4.4, -3.2),
    "PT": (-6.35, -11.9),
    "OT_PP": (-6.35, -11.9),
    "OT_SE": (-6.35, -9.4),
    "CHOKE": (-4.0, -6.4),
    "TANK": (-7.0, -9.4),
    "OPTO": (4.4, -8.0),
    "CONN3": (-5.0, 4.0),
    "JACK": (3.0, -6.6),
    "LAMP": (4.4, -5.4),
    "DUALCAN": (4.6, -1.0),
    "TRIODE": (6.0, -6.4),
    "DIODE_TUBE": (6.0, -6.4),
    "PENTODE": (6.2, -7.6),
    "SWITCH": (-3.4, -6.0),
    "FUSE": (-3.4, -6.0),
}
LABEL_FALLBACK = (2.2, -3.2)


def text_box(t: str, x: float, y: float, size: float,
             justify: str = "left") -> tuple[float, float, float, float]:
    """Gate-ruler text box (flat CHAR_W estimate — see the two-rulers note)."""
    w = len(t) * CHAR_W * size
    h = LINE_H * size
    x0 = x if justify == "left" else (x - w if justify == "right" else x - w / 2)
    return (x0, y - h / 2, x0 + w, y + h / 2)


def _true_text_box(t: str, x: float, y: float,
                   size: float) -> tuple[float, float, float, float]:
    """Placement-ruler text box: the renderer's own ink width."""
    w = text_w(t, size)
    h = LINE_H * size
    return (x, y - h / 2, x + w, y + h / 2)


def _flag_box(w: float, x: float, y: float,
              rot: int) -> tuple[float, float, float, float]:
    """A `w`-long global-label flag body: it grows away from the connection
    point, opposite the direction the label points."""
    h = LINE_H * 1.27 + 0.8
    rot %= 360
    if rot == 0:
        return (x, y - h / 2, x + w, y + h / 2)
    if rot == 180:
        return (x - w, y - h / 2, x, y + h / 2)
    if rot == 90:                      # reads bottom-to-top: body is above
        return (x - h / 2, y - w, x + h / 2, y)
    return (x - h / 2, y, x + h / 2, y + w)


def label_box(name: str, x: float, y: float, rot: int) -> tuple[float, float, float, float]:
    """Gate-ruler bounding box of a global label."""
    return _flag_box((len(name) + 2) * CHAR_W * 1.27, x, y, rot)


def _true_label_box(name: str, x: float, y: float,
                    rot: int) -> tuple[float, float, float, float]:
    """Placement-ruler flag box: the outline KiCanvas actually draws wraps
    the name's ink plus its furniture (0.375 x size expansion each side and
    the input-shape point, ~2.1 mm together)."""
    return _flag_box(text_w(name, 1.27) + 2.1, x, y, rot)


def _rot_local(sx: float, sy: float, rot: int, mirror: str) -> tuple[float, float]:
    """Symbol-space (sx, sy) -> schematic-space offset from the symbol origin."""
    if mirror == "y":
        sx = -sx
    elif mirror == "x":
        sy = -sy
    rot %= 360
    if rot == 0:
        return (sx, -sy)
    if rot == 90:
        return (-sy, -sx)
    if rot == 180:
        return (-sx, sy)
    return (sy, sx)


def sym_box(lib: str, x: float, y: float, rot: int,
            mirror: str = "", body: bool = False) -> tuple[float, float, float, float]:
    table = SYM_BODY if body else SYM_EXTENTS
    x0, y0, x1, y1 = table.get(lib, (-5.0, -5.0, 5.0, 5.0))
    pts = [_rot_local(a, b, rot, mirror)
           for a in (x0, x1) for b in (y0, y1)]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts),
            x + max(p[0] for p in pts), y + max(p[1] for p in pts))


# Two boxes clash when they share this much in BOTH axes. Deliberately TIGHTER
# than check_schematics.OVERLAP_MM (0.8): the placer must aim clear of the
# gate's threshold, not at it, or a 0.85 mm overlap passes here and fails there.
HIT_MM = 0.5


def _hit(a, b) -> bool:
    return (min(a[2], b[2]) - max(a[0], b[0]) >= HIT_MM
            and min(a[3], b[3]) - max(a[1], b[1]) >= HIT_MM)


def _union(boxes):
    boxes = list(boxes)
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


# ---------------------------------------------------------------------------
# Sheet furniture
# ---------------------------------------------------------------------------
# KiCad's default worksheet draws a 10 mm frame and hangs the title block off
# the bottom-right corner: a 110 x 34 mm block measured inward from that
# corner. Content laid into that rectangle is printed over by the frame, so
# `write()` reserves the bottom TB_H strip of every sheet it sizes.
FRAME = 10.0
TB_W = 110.0
TB_H = 34.0
MARGIN = 12.7          # content inset from the paper edge (clears the frame)
GAP = 6.0              # circuit -> notes band
MIN_W = 148.0          # narrowest sheet that still fits the title block
NOTE_SIZE = 1.2
NOTE_LEAD = 4.4

ROOT = Path(__file__).resolve().parent.parent


def display_id(amp_id: str) -> str:
    """Mirror of site/src/lib/corpus.js displayId(): 5f6a -> 5F6-A,
    ab763-twin -> AB763 (Twin)."""
    m = re.fullmatch(r"([a-z0-9]+)-([a-z0-9]+)", amp_id)
    head = (m.group(1) if m else amp_id).upper()
    head = re.sub(r"^(\d[A-Z]\d+)([AB])$", r"\1-\2", head)
    if not m:
        return head
    return f"{head} ({m.group(2).capitalize()})"


def _wrap(text: str, width_chars: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if len(cand) > width_chars and cur:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines or [""]


class Sch:
    """Schematic builder with amp-idiom composites."""

    def __init__(self) -> None:
        self.items: list[tuple] = []
        self.notes: list[str] = []

    # ---- primitives -----------------------------------------------------
    def sym(self, lib: str, ref: str, val: str, x: float, y: float, rot: int = 0,
            lx: float | None = None, ly: float | None = None,
            label_rot: int | None = None,
            mirror: str = "", spec: str | None = None) -> None:
        # Property text follows the symbol's rotation unless `label_rot` pins it —
        # a body placed at 180° still wants its ref/value read left-to-right.
        dlx, dly = LABEL_DEFAULT.get(lib, LABEL_FALLBACK)
        lx = dlx if lx is None else lx
        ly = dly if ly is None else ly
        pa = (360 - rot) % 360 if label_rot is None else label_rot % 360
        # `mirror` ("x" or "y") flips the body about that axis, so one library
        # symbol serves both hands of an asymmetric part: a jack whose contacts
        # face left becomes one whose contacts face right, with the pins landing
        # at (x - sx, y - sy) instead of (x + sx, y - sy). Property text is placed
        # in absolute coordinates and is NOT mirrored — callers pass lx/ly.
        #
        # `spec` is the third lettering slot: the turns ratio or impedance of a
        # transformer, the henries of a choke — a quantity that belongs beside
        # the part but is neither its designator nor its catalogue number.
        self.items.append(("sym", [(x, y), (x + lx, y + ly)],
                           (lib, ref, val, rot, pa, mirror, spec)))

    def wire(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.items.append(("wire", [(x1, y1), (x2, y2)], ()))

    def glabel(self, name: str, x: float, y: float, rot: int = 0) -> None:
        self.items.append(("glabel", [(x, y)], (name, rot)))

    def junction(self, x: float, y: float) -> None:
        self.items.append(("junction", [(x, y)], ()))

    def text(self, t: str, x: float, y: float, size: float = 1.6) -> None:
        """Lettering pinned to a coordinate. Use it when the position IS the
        meaning — a knob name beside its pot, a node marker on a stub."""
        self.items.append(("text", [(x, y)], (t, size)))

    def caption(self, t: str, x: float, y: float, size: float = 1.6) -> None:
        """A section heading over the block it names ("Bright channel — …").

        Its coordinate says which block it belongs to, not where the glyphs
        must land, so `write()` may shift it clear of anything it would print
        through — up first, then left, then down — before it gives up and lets
        the gate complain."""
        self.items.append(("caption", [(x, y)], (t, size)))

    def note(self, t: str, size: float = NOTE_SIZE) -> None:
        """Queue a prose annotation for the sheet's notes band.

        Prose placed by hand at a coordinate that looked free when the amp was
        first drawn is the single largest source of text-over-circuitry in this
        corpus. Notes carry no coordinate: `write()` wraps them into a reserved
        band under the drawing, where nothing can grow into them."""
        self.notes.append(t)

    def gnd(self, x: float, y: float, rot: int = 270) -> None:
        """Ground flag. It defaults to pointing down, which is right for the
        foot of a shunt part — and wrong for the head of one, where the flag
        then prints straight through the body it is grounding. Pass rot=90
        (up), 0 (right) or 180 (left) when the node is not a foot."""
        self.glabel("GND", x, y, rot)

    # ---- tubes ----------------------------------------------------------
    def triode(self, ref: str, val: str, x: float, y: float,
               lx: float = 6.0, ly: float = -6.4) -> dict:
        self.sym("TRIODE", ref, val, x, y, lx=lx, ly=ly)
        return {"p": (x, y - 7.62), "g": (x - 7.62, y), "k": (x, y + 7.62)}

    def pentode(self, ref: str, val: str, x: float, g1_y: float,
                lx: float = 6.2, ly: float = -7.6) -> dict:
        y = g1_y - 0.635
        self.sym("PENTODE", ref, val, x, y, lx=lx, ly=ly)
        return {"p": (x, y - 7.62), "g1": (x - 7.62, g1_y),
                "g2": (x + 7.62, y - 0.635), "k": (x, y + 7.62)}

    def diode_tube(self, ref: str, val: str, x: float, y: float,
                   lx: float = 6.0, ly: float = -6.4) -> dict:
        self.sym("DIODE_TUBE", ref, val, x, y, lx=lx, ly=ly)
        return {"a": (x, y - 7.62), "k": (x, y + 7.62)}

    # ---- composites -----------------------------------------------------
    def series_h(self, lib: str, ref: str, val: str, x: float, y: float) -> tuple:
        """Horizontal series element centered at (x, y); returns (left, right) x."""
        ly = -6.2 if lib == "C" else -6.0
        self.sym(lib, ref, val, x, y, rot=90, lx=-3.2, ly=ly)
        return (x - 3.81, x + 3.81)

    def shunt_r(self, ref: str, val: str, x: float, ytop: float, lib: str = "R") -> float:
        """Vertical R (or C) whose top pin is at (x, ytop); grounds the bottom."""
        self.sym(lib, ref, val, x, ytop + 3.81)
        self.gnd(x, ytop + 7.62)
        return ytop + 7.62

    def shunt_rc(self, rref: str, rval: str, cref: str, cval: str,
                 x: float, ytop: float, dx: float = 7.62) -> None:
        """Parallel R‖C to ground, R at x, C at x+dx, joined top and bottom."""
        self.sym("R", rref, rval, x, ytop + 3.81)
        self.sym("C", cref, cval, x + dx, ytop + 3.81)
        self.wire(x, ytop, x + dx, ytop)
        self.wire(x, ytop + 7.62, x + dx, ytop + 7.62)
        self.gnd(x, ytop + 7.62)

    def plate_load(self, ref: str, val: str, plate: tuple, rail: str,
                   gap: float = 3.48) -> None:
        """Resistor from a plate pin up to a rail label; leaves a junction at
        the wire top of the plate stub so couplers can tee off."""
        x, py = plate
        self.wire(x, py, x, py - gap)
        self.sym("R", ref, val, x, py - gap - 3.81)
        self.wire(x, py - gap - 7.62, x, py - gap - 10.16)
        self.glabel(rail, x, py - gap - 10.16, 90)

    def pt(self, ref: str, val: str, x: float, y: float,
           lx: float = -6.35, ly: float = -11.9, spec: str | None = None) -> dict:
        """Power transformer: primary (2 pins, left), HT centre-tapped (3, right)."""
        self.sym("PT", ref, val, x, y, lx=lx, ly=ly, spec=spec)
        return {"pri1": (x - 8.89, y - 5.08), "pri2": (x - 8.89, y + 5.08),
                "ht_a": (x + 8.89, y - 5.08), "ht_ct": (x + 8.89, y),
                "ht_b": (x + 8.89, y + 5.08)}

    def ot_se(self, ref: str, val: str, x: float, y: float,
              lx: float = -6.35, ly: float = -9.4, spec: str | None = None) -> dict:
        """Single-ended output transformer; `spec` letters its impedance ratio."""
        self.sym("OT_SE", ref, val, x, y, lx=lx, ly=ly, spec=spec)
        return {"pri_p": (x - 8.89, y - 2.54), "pri_b": (x - 8.89, y + 2.54),
                "sec_h": (x + 8.89, y - 2.54), "sec_c": (x + 8.89, y + 2.54)}

    def ot_pp(self, ref: str, val: str, x: float, y: float,
              lx: float = -6.35, ly: float = -11.9, spec: str | None = None) -> dict:
        """Push-pull output transformer; `spec` letters its plate-to-plate load."""
        self.sym("OT_PP", ref, val, x, y, lx=lx, ly=ly, spec=spec)
        return {"pri_a": (x - 8.89, y - 5.08), "ct": (x - 8.89, y),
                "pri_b": (x - 8.89, y + 5.08),
                "sec_h": (x + 8.89, y - 2.54), "sec_c": (x + 8.89, y + 2.54)}

    def choke(self, ref: str, val: str, x: float, y: float,
              lx: float = -4.0, ly: float = -6.4, spec: str | None = None) -> tuple:
        """Filter choke centred at (x, y); returns its (left, right) pin x."""
        self.sym("CHOKE", ref, val, x, y, lx=lx, ly=ly, spec=spec)
        return (x - 7.62, x + 7.62)

    def jack(self, ref: str, val: str, x: float, y: float,
             lx: float | None = None, ly: float = -6.6, mirror: bool = False) -> dict:
        """Quarter-inch jack. Contacts face left and the body sits to the right;
        `mirror=True` flips it so the contacts face right (a jack on the drawing's
        right-hand edge, wired from inside)."""
        if lx is None:
            lx = -4.0 if mirror else 3.0
        self.sym("JACK", ref, val, x, y, lx=lx, ly=ly, mirror="y" if mirror else "")
        sx = 5.08 if mirror else -5.08
        return {"tip": (x + sx, y - 2.54), "sleeve": (x + sx, y + 2.54)}

    def switch(self, ref: str, val: str, x: float, y: float,
               lx: float = -3.4, ly: float = -6.0) -> tuple:
        """Horizontal switch centred at (x, y); returns its (left, right) pin x."""
        self.sym("SWITCH", ref, val, x, y, lx=lx, ly=ly)
        return (x - 5.08, x + 5.08)

    def fuse(self, ref: str, val: str, x: float, y: float,
             lx: float = -3.4, ly: float = -6.0) -> tuple:
        """Horizontal fuse centred at (x, y); returns its (left, right) pin x."""
        self.sym("FUSE", ref, val, x, y, lx=lx, ly=ly)
        return (x - 5.08, x + 5.08)

    def lamp(self, ref: str, val: str, x: float, y: float,
             lx: float = 4.4, ly: float = -5.4) -> dict:
        """Pilot lamp centred at (x, y); pins top and bottom."""
        self.sym("LAMP", ref, val, x, y, lx=lx, ly=ly)
        return {"hi": (x, y - 5.08), "lo": (x, y + 5.08)}

    def dualcan(self, ref: str, val: str, x: float, y: float,
                lx: float = 4.6, ly: float = -1.0) -> dict:
        """Dual-section can (a `50+50 µF` filter): two top terminals over one
        common negative, exactly as the period drawings letter it."""
        self.sym("DUALCAN", ref, val, x, y, lx=lx, ly=ly)
        return {"a": (x - 2.54, y - 3.81), "b": (x + 2.54, y - 3.81),
                "com": (x, y + 3.81)}

    def conn3(self, ref: str, val: str, x: float, y: float,
              lx: float = -5.0, ly: float = 4.0) -> dict:
        """Three-pole connector (a mains inlet: neutral / earth / live)."""
        self.sym("CONN3", ref, val, x, y, lx=lx, ly=ly)
        return {"1": (x - 3.81, y - 5.08), "2": (x, y - 5.08),
                "3": (x + 3.81, y - 5.08)}

    def tank(self, ref: str, val: str, x: float, y: float,
             lx: float = -7.0, ly: float = -9.4) -> dict:
        """Spring reverb tank: input transducer left, output transducer right."""
        self.sym("TANK", ref, val, x, y, lx=lx, ly=ly)
        return {"in_h": (x - 10.16, y - 2.54), "in_c": (x - 10.16, y + 2.54),
                "out_h": (x + 10.16, y - 2.54), "out_c": (x + 10.16, y + 2.54)}

    def opto(self, ref: str, val: str, x: float, y: float,
             lx: float = 4.4, ly: float = -8.0) -> dict:
        """Optocoupler: neon lamp side (left, 2 pins), photocell side (right, 2)."""
        self.sym("OPTO", ref, val, x, y, lx=lx, ly=ly)
        return {"l1": (x - 6.35, y - 2.54), "l2": (x - 6.35, y + 2.54),
                "p1": (x + 6.35, y - 2.54), "p2": (x + 6.35, y + 2.54)}

    # ---- geometry -------------------------------------------------------
    def boxes(self, dx: float = 0.0, dy: float = 0.0) -> list[tuple]:
        """Every drawn element as (label, x0, y0, x1, y1), translated by
        (dx, dy). Used to size the sheet and to lint for overlaps."""
        out = []
        for kind, pts, extra in self.items:
            p = [(x + dx, y + dy) for (x, y) in pts]
            if kind == "sym":
                lib, ref, val, rot, pa, mirror, spec = extra
                out.append((f"symbol {ref}",
                            *sym_box(lib, p[0][0], p[0][1], rot, mirror, body=True)))
                out.append((f"ref {ref}", *text_box(ref, p[1][0], p[1][1], 1.27)))
                out.append((f"value {ref}={val}",
                            *text_box(val, p[1][0], p[1][1] + 2.4, 1.27)))
                if spec:
                    out.append((f"spec {ref}={spec}",
                                *text_box(spec, p[1][0], p[1][1] + 4.8, 1.1)))
            elif kind == "wire":
                out.append(("wire", min(p[0][0], p[1][0]), min(p[0][1], p[1][1]),
                            max(p[0][0], p[1][0]), max(p[0][1], p[1][1])))
            elif kind == "glabel":
                name, rot = extra
                out.append((f"label {name}", *label_box(name, p[0][0], p[0][1], rot)))
            elif kind == "junction":
                out.append(("junction", p[0][0] - 0.4, p[0][1] - 0.4,
                            p[0][0] + 0.4, p[0][1] + 0.4))
            elif kind in ("text", "caption"):
                t, size = extra
                out.append((f"text {t[:34]!r}", *text_box(t, p[0][0], p[0][1], size)))
        return out

    def bbox(self) -> tuple[float, float, float, float]:
        """Extent of the ink, pin stubs included — what the sheet must hold."""
        ext = [b[1:] for b in self.boxes()]
        for kind, pts, extra in self.items:
            if kind == "sym":
                lib, _, _, rot, _, mirror, _ = extra
                ext.append(sym_box(lib, pts[0][0], pts[0][1], rot, mirror))
        return _union(ext)

    # ---- lettering placement -------------------------------------------
    def _label_block(self, i: int) -> list[tuple[float, float, float, float]]:
        _, pts, extra = self.items[i]
        _, ref, val, _, _, _, spec = extra
        px, py = pts[1]
        out = [_true_text_box(ref, px, py, 1.27),
               _true_text_box(val, px, py + 2.4, 1.27)]
        if spec:
            out.append(_true_text_box(spec, px, py + 4.8, 1.1))
        return out

    def _candidates(self, i: int) -> list[tuple[float, float]]:
        """Where a part's designator/value block may go, nearest first.

        The authored anchor always leads: a hand-placed label that clears its
        neighbours is better than anything a rule can invent. The alternatives
        walk out from the symbol's own body — right, left, above, below — so a
        displaced label still reads as belonging to its part."""
        _, pts, extra = self.items[i]
        lib, ref, val, rot, _, mirror, spec = extra
        (x, y), (px, py) = pts
        bx0, by0, bx1, by1 = sym_box(lib, x, y, rot, mirror, body=True)
        w = max(text_w(ref, 1.27), text_w(val, 1.27),
                text_w(spec or "", 1.1))
        h = 2.4 * (2 + (1 if spec else 0))
        out = [(px, py)]
        for pad in (0.9, 4.0, 7.5, 11.0, 15.0):
            out += [(bx1 + pad, by0 + 0.9),
                    (bx0 - w - pad, by0 + 0.9),
                    (bx1 + pad, by1 - h),
                    (bx0 - w - pad, by1 - h),
                    (bx0, by0 - h - pad),
                    (bx0, by1 + pad + 0.9)]
        return out

    def place_captions(self) -> int:
        """Nudge every section heading off whatever it would print through.

        A heading is the one piece of lettering that names a *region* rather
        than a part, so it can move within that region without lying. It tries
        upward first — away from the circuit it heads — then left, then down."""
        fixed = []
        for kind, pts, extra in self.items:
            if kind == "sym":
                lib, _, _, rot, _, mirror, _ = extra
                fixed.append(sym_box(lib, pts[0][0], pts[0][1], rot, mirror, body=True))
            elif kind == "glabel":
                fixed.append(_true_label_box(extra[0], pts[0][0], pts[0][1], extra[1]))
            elif kind == "text":
                fixed.append(_true_text_box(extra[0], pts[0][0], pts[0][1], extra[1]))

        caps = [i for i, it in enumerate(self.items) if it[0] == "caption"]
        boxes = {i: _true_text_box(self.items[i][2][0], *self.items[i][1][0],
                                   self.items[i][2][1]) for i in caps}
        moved = 0
        for i in caps:
            t, size = self.items[i][2]
            x, y = self.items[i][1][0]
            others = [b for j, b in boxes.items() if j != i]
            if not any(_hit(boxes[i], o) for o in fixed + others):
                continue
            # The ladder runs further than it used to: a banner caption
            # measured with the renderer's true advance is half again wider
            # than the old estimate thought, and a ladder that stopped at
            # 14 mm up / 24 mm left stranded the two longest captions in the
            # corpus on top of the circuitry they head.
            for cand in ([(x, y - d) for d in (3.5, 7, 10.5, 14, 17.5, 21)]
                         + [(x - d, y) for d in (6, 14, 24, 34)]
                         + [(x + d, y) for d in (6, 14, 24)]
                         + [(x, y + d) for d in (3.5, 7, 10.5)]):
                b = _true_text_box(t, cand[0], cand[1], size)
                if not any(_hit(b, o) for o in fixed + others):
                    self.items[i][1][0] = cand
                    boxes[i] = b
                    moved += 1
                    break
        return moved

    def place_labels(self) -> int:
        """Move every designator/value block that would print over something.

        Part lettering is the one class of text on these sheets whose position
        carries no meaning — only its attachment does. So when an authored
        anchor collides, the library moves it rather than asking 34 draw
        scripts to each rediscover a free spot. Returns the number moved."""
        static: list[tuple] = []
        for kind, pts, extra in self.items:
            if kind == "sym":
                lib, ref, val, rot, _, mirror, _ = extra
                static.append(sym_box(lib, pts[0][0], pts[0][1], rot, mirror, body=True))
            elif kind == "glabel":
                static.append(_true_label_box(extra[0], pts[0][0], pts[0][1], extra[1]))
            elif kind in ("text", "caption"):
                static.append(_true_text_box(extra[0], pts[0][0], pts[0][1], extra[1]))

        idx = [i for i, it in enumerate(self.items) if it[0] == "sym"]
        blocks = {i: self._label_block(i) for i in idx}

        def clashes(boxes, skip) -> bool:
            for b in boxes:
                for o in static:
                    if _hit(b, o):
                        return True
                for j, ob in blocks.items():
                    if j == skip:
                        continue
                    for o in ob:
                        if _hit(b, o):
                            return True
            return False

        moved = 0
        for _ in range(3):
            changed = 0
            for i in idx:
                if not clashes(blocks[i], i):
                    continue
                keep = self.items[i][1][1]
                for cand in self._candidates(i)[1:]:
                    self.items[i][1][1] = cand
                    trial = self._label_block(i)
                    if not clashes(trial, i):
                        blocks[i] = trial
                        changed += 1
                        break
                else:
                    self.items[i][1][1] = keep
            moved += changed
            if not changed:
                break
        return moved

    # ---- emission -------------------------------------------------------
    def _render(self, dx: float, dy: float) -> str:
        out: list[str] = []
        for kind, pts, extra in self.items:
            p = [(x + dx, y + dy) for (x, y) in pts]
            if kind == "sym":
                lib, ref, val, rot, pa, mirror, spec = extra
                mir = f" (mirror {mirror})" if mirror else ""
                (x, y), (px, py) = p
                out.append(f"""  (symbol (lib_id "cx:{lib}") (at {x:g} {y:g} {rot}){mir} (unit 1)
    (in_bom yes) (on_board yes) (uuid "{_u()}")
    (property "Reference" "{_esc(ref)}" (at {px:g} {py:g} {pa}) {FONT_L})
    (property "Value" "{_esc(val)}" (at {px:g} {py + 2.4:g} {pa}) {FONT_L}))""")
                if spec:
                    out.append(_text_sexpr(spec, px, py + 4.8, 1.1))
            elif kind == "wire":
                (x1, y1), (x2, y2) = p
                out.append(f"""  (wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))
    (stroke (width 0) (type default)) (uuid "{_u()}"))""")
            elif kind == "glabel":
                name, rot = extra
                # Justification must compensate rotation, exactly as `pa` does
                # for property text above. KiCanvas (and KiCad itself) draw a
                # label's name horizontally at 0/180 and vertically at 90/270,
                # then read WHICH SIDE of the anchor it letters on from the
                # justification: the flag body lies right/below at 0/90
                # (justify left) but left/above at 180/270, where only
                # (justify right) letters the name inside the flag. A flat
                # (justify left) shipped 219 net names outside their own flag
                # outlines, struck through by the wire they name.
                just = "right" if rot % 360 in (180, 270) else "left"
                out.append(f"""  (global_label "{_esc(name)}" (shape input) (at {p[0][0]:g} {p[0][1]:g} {rot})
    (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{_u()}"))""")
            elif kind == "junction":
                out.append(f"""  (junction (at {p[0][0]:g} {p[0][1]:g}) (diameter 0) (color 0 0 0 0) (uuid "{_u()}"))""")
            elif kind in ("text", "caption"):
                t, size = extra
                out.append(_text_sexpr(t, p[0][0], p[0][1], size))
        return "\n".join(out)

    def write(self, path, notes=(), paper: str | None = None) -> str:
        """Emit the sheet: title block from meta.yaml, paper fitted to the ink,
        prose wrapped into the reserved notes band.

        `notes` accepts plain strings or the legacy (text, x, y, size) tuples —
        their coordinates are discarded, because a note's whole point is that it
        no longer competes with the circuit for a place on the sheet."""
        path = Path(path)
        queued = list(self.notes)
        for n in notes:
            queued.append(n if isinstance(n, str) else n[0])

        self.place_captions()
        self.place_labels()
        cx0, cy0, cx1, cy1 = self.bbox()
        cw, chh = cx1 - cx0, cy1 - cy0

        # Wrap the prose to the drawing's own width (never narrower than a
        # readable measure, never wider than the circuit it annotates).
        wrap_w = max(cw, MIN_W - 2 * MARGIN)
        chars = max(40, int(wrap_w / (PROSE_W * NOTE_SIZE)))
        lines: list[str] = []
        for n in queued:
            lines.extend(_wrap(n, chars))
        notes_h = (len(lines) - 1) * NOTE_LEAD + LINE_H * NOTE_SIZE if lines else 0.0
        notes_w = max((text_w(l, NOTE_SIZE) for l in lines), default=0.0)

        inner_w = max(cw, notes_w, MIN_W - 2 * MARGIN)
        width = inner_w + 2 * MARGIN
        band = (GAP + notes_h) if lines else 0.0
        height = MARGIN + chh + band + TB_H + 2.0

        if paper:                       # a caller-pinned standard sheet
            std = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
                   "A3": (420, 297), "A4": (297, 210), "A5": (210, 148)}
            width, height = std.get(paper, (width, height))
            paper_sexpr = f'(paper "{paper}")'
        else:
            paper_sexpr = f'(paper "User" {width:.2f} {height:.2f})'

        dx, dy = MARGIN - cx0, MARGIN - cy0
        body = self._render(dx, dy)
        ny = MARGIN + chh + GAP + LINE_H * NOTE_SIZE / 2
        note_sexprs = "\n".join(
            _text_sexpr(t, MARGIN, ny + i * NOTE_LEAD, NOTE_SIZE)
            for i, t in enumerate(lines))

        meta = _read_meta(path)
        tb = _title_block(path, meta)
        doc = f"""(kicad_sch (version 20231120) (generator "circuit-codex")
  (uuid "{_u()}")
  {paper_sexpr}
{tb}
{LIB}
{body}
{note_sexprs}
  (sheet_instances (path "/" (page "1")))
)
"""
        path.write_text(doc)
        return doc


def _esc(t: str) -> str:
    # KiCad s-expression strings must escape backslash and double quote —
    # kiutils round-trips a raw inner quote, but KiCanvas's tokenizer dies
    # on it (the AC15 "Vibravox" incident). Escape here so no draw script
    # can ship an unrenderable schematic.
    return t.replace("\\", "\\\\").replace('"', '\\"')


def _text_sexpr(t: str, x: float, y: float, size: float) -> str:
    return (f"""  (text "{_esc(t)}" (at {x:g} {y:g} 0)
    (effects (font (size {size:g} {size:g})) (justify left)) (uuid "{_u()}"))""")


def _read_meta(path: Path) -> dict:
    meta_path = path.parent / "meta.yaml"
    if not meta_path.exists():
        return {}
    import yaml
    return yaml.safe_load(meta_path.read_text()) or {}


def _title_block(path: Path, meta: dict) -> str:
    """The sheet's own identity, from the amp's data — never hand-typed.

    A blank title block is a claim in itself: it says the drawing is unfinished.
    Every field here is read from meta.yaml, so a sheet cannot say one thing
    while the corpus says another."""
    amp_id = meta.get("id") or path.parent.name
    style = meta.get("name_style") or ""
    title = f"{display_id(str(amp_id))} — {style}" if style else display_id(str(amp_id))
    ver = meta.get("verification") or {}
    status = str(ver.get("status") or "draft")
    date = ver.get("date") or meta.get("added") or ""
    rev = {"verified": "verified", "draft": "draft"}.get(status, status)
    rows = [f'    (title "{_esc(title)}")',
            f'    (date "{date}")',
            f'    (rev "{_esc(rev)}")',
            '    (company "Circuit Codex")',
            '    (comment 1 "Redrawn from circuit facts — not a reproduction of any factory drawing")',
            '    (comment 2 "CC-BY-SA 4.0 · circuitcodex.com")']
    src = (meta.get("sources") or [{}])[0].get("url", "")
    if src:
        rows.append(f'    (comment 3 "Values read from: {_esc(src)}")')
    return "  (title_block\n" + "\n".join(rows) + ")"
