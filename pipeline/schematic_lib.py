#!/usr/bin/env python3
"""Reusable KiCad schematic authoring library for Circuit Codex.

Self-contained symbol set (lib "cx", CC-BY-SA — no external dependencies) plus
a builder with composable amp idioms (shunt RC, plate load to rail, series
parts, tube helpers). Per-amp generators (draw_5e3.py, draw_5f6a.py, …) become
short declarative layouts instead of coordinate soup.

Conventions: schematic space, mm, +Y down. A symbol pin at (sx, sy) lands at
(x + sx, y - sy) for rotation 0. draw_5f1.py predates this library and keeps
its own copy of the base symbols; it gets ported in a cleanup pass.
"""
from __future__ import annotations

import uuid

FONT = "(effects (font (size 1.27 1.27)))"
FONT_L = "(effects (font (size 1.27 1.27)) (justify left))"
_STROKE = '(stroke (width 0.254) (type default)) (fill (type none))'


def _u() -> str:
    return str(uuid.uuid4())


def _poly(pts: str) -> str:
    return f"(polyline (pts {pts}) {_STROKE})"


def _pin(kind: str, x: float, y: float, rot: int, length: float, name: str, num: str) -> str:
    return (f'(pin {kind} line (at {x:g} {y:g} {rot}) (length {length:g}) '
            f'(name "{name}" {FONT}) (number "{num}" {FONT}))')


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
      (symbol "CHOKE_0_1" (rectangle (start -5.08 -2.54) (end 5.08 2.54) {_STROKE}))
      (symbol "CHOKE_1_1"
        {_pin("passive", -7.62, 0, 0, 2.54, "1", "1")}
        {_pin("passive", 7.62, 0, 180, 2.54, "2", "2")}))
    (symbol "cx:OT_SE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 10.16 0) {FONT})
      (property "Value" "OT" (at 0 0 0) {FONT})
      (symbol "OT_SE_0_1" (rectangle (start -6.35 -6.35) (end 6.35 6.35) {_STROKE}))
      (symbol "OT_SE_1_1"
        {_pin("passive", -8.89, 2.54, 0, 2.54, "PRI_P", "1")}
        {_pin("passive", -8.89, -2.54, 0, 2.54, "PRI_B", "2")}
        {_pin("passive", 8.89, 2.54, 180, 2.54, "SEC_H", "3")}
        {_pin("passive", 8.89, -2.54, 180, 2.54, "SEC_C", "4")}))
    (symbol "cx:OT_PP" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 12.7 0) {FONT})
      (property "Value" "OT" (at 0 0 0) {FONT})
      (symbol "OT_PP_0_1" (rectangle (start -6.35 -8.89) (end 6.35 8.89) {_STROKE}))
      (symbol "OT_PP_1_1"
        {_pin("passive", -8.89, 5.08, 0, 2.54, "PRI_A", "1")}
        {_pin("passive", -8.89, 0, 0, 2.54, "CT", "2")}
        {_pin("passive", -8.89, -5.08, 0, 2.54, "PRI_B", "3")}
        {_pin("passive", 8.89, 2.54, 180, 2.54, "SEC_H", "4")}
        {_pin("passive", 8.89, -2.54, 180, 2.54, "SEC_C", "5")})))
"""


class Sch:
    """Schematic builder with amp-idiom composites."""

    def __init__(self) -> None:
        self.body: list[str] = []

    # ---- primitives -----------------------------------------------------
    def sym(self, lib: str, ref: str, val: str, x: float, y: float, rot: int = 0,
            lx: float = 2.2, ly: float = -3.2) -> None:
        pa = (360 - rot) % 360
        self.body.append(f"""  (symbol (lib_id "cx:{lib}") (at {x:g} {y:g} {rot}) (unit 1)
    (in_bom yes) (on_board yes) (uuid "{_u()}")
    (property "Reference" "{ref}" (at {x + lx:g} {y + ly:g} {pa}) {FONT_L})
    (property "Value" "{val}" (at {x + lx:g} {y + ly + 2.4:g} {pa}) {FONT_L}))""")

    def wire(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.body.append(f"""  (wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))
    (stroke (width 0) (type default)) (uuid "{_u()}"))""")

    def glabel(self, name: str, x: float, y: float, rot: int = 0) -> None:
        self.body.append(f"""  (global_label "{name}" (shape input) (at {x:g} {y:g} {rot})
    (effects (font (size 1.27 1.27)) (justify left)) (uuid "{_u()}"))""")

    def junction(self, x: float, y: float) -> None:
        self.body.append(f"""  (junction (at {x:g} {y:g}) (diameter 0) (color 0 0 0 0) (uuid "{_u()}"))""")

    def text(self, t: str, x: float, y: float, size: float = 1.6) -> None:
        self.body.append(f"""  (text "{t}" (at {x:g} {y:g} 0)
    (effects (font (size {size:g} {size:g})) (justify left)) (uuid "{_u()}"))""")

    def gnd(self, x: float, y: float) -> None:
        self.glabel("GND", x, y, 270)

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

    def write(self, path, title_lines: list[tuple]) -> None:
        head = "\n".join(
            f"""  (text "{t}" (at {x:g} {y:g} 0)
    (effects (font (size {s:g} {s:g})) (justify left)) (uuid "{_u()}"))"""
            for (t, x, y, s) in title_lines)
        doc = f"""(kicad_sch (version 20231120) (generator "circuit-codex")
  (uuid "{_u()}")
  (paper "A4")
{LIB}
{head}
{chr(10).join(self.body)}
  (sheet_instances (path "/" (page "1")))
)
"""
        path.write_text(doc)
        return doc
