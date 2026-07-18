#!/usr/bin/env python3
"""Generate amps/5f1/schematic.kicad_sch — the redrawn 5F1 schematic.

Spike goals (docs/2026-07-18-kicad-spike.md): prove programmatic KiCad
authoring with a self-contained symbol set (lib "cx", CC-BY-SA, no external
library dependencies), kiutils round-trip, and KiCanvas browser rendering.

Coordinates: schematic space, mm, +Y down. Symbol space is +Y up; a symbol
pin at (sx, sy) lands at (x + sx, y - sy) for rotation 0.
"""
from __future__ import annotations

import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f1" / "schematic.kicad_sch"


def u() -> str:
    return str(uuid.uuid4())


FONT = "(effects (font (size 1.27 1.27)))"
FONT_L = "(effects (font (size 1.27 1.27)) (justify left))"

# ---------------------------------------------------------------- symbols
LIB = """  (lib_symbols
    (symbol "cx:R" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "R" (at 2.54 1.27 0) %(F)s)
      (property "Value" "R" (at 2.54 -1.27 0) %(F)s)
      (symbol "R_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54)
          (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27) (name "~" %(F)s) (number "1" %(F)s))
        (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" %(F)s) (number "2" %(F)s))))
    (symbol "cx:C" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "C" (at 2.54 1.27 0) %(F)s)
      (property "Value" "C" (at 2.54 -1.27 0) %(F)s)
      (symbol "C_0_1"
        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "C_1_1"
        (pin passive line (at 0 3.81 270) (length 3.048) (name "~" %(F)s) (number "1" %(F)s))
        (pin passive line (at 0 -3.81 90) (length 3.048) (name "~" %(F)s) (number "2" %(F)s))))
    (symbol "cx:TRIODE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 5.08 0) %(F)s)
      (property "Value" "triode" (at 6.35 2.54 0) %(F)s)
      (symbol "TRIODE_0_1"
        (circle (center 0 0) (radius 5.08) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 1.905) (xy 2.54 1.905)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 1.905) (xy 0 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.286 0) (xy -1.27 0)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -0.508 0) (xy 0.508 0)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 0) (xy 2.286 0)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -1.905 -1.905) (xy 1.905 -1.905)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 -1.905) (xy 0 -5.08)) (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "TRIODE_1_1"
        (pin passive line (at 0 7.62 270) (length 2.54) (name "P" %(F)s) (number "1" %(F)s))
        (pin input line (at -7.62 0 0) (length 5.334) (name "G" %(F)s) (number "2" %(F)s))
        (pin passive line (at 0 -7.62 90) (length 2.54) (name "K" %(F)s) (number "3" %(F)s))))
    (symbol "cx:PENTODE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 6.35 0) %(F)s)
      (property "Value" "pentode" (at 6.35 3.81 0) %(F)s)
      (symbol "PENTODE_0_1"
        (circle (center 0 0) (radius 5.08) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 2.54) (xy 2.54 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 2.54) (xy 0 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.286 0.635) (xy -1.27 0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -0.508 0.635) (xy 0.508 0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 0.635) (xy 2.286 0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.286 -0.635) (xy -1.27 -0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -0.508 -0.635) (xy 0.508 -0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 1.27 -0.635) (xy 2.286 -0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -1.905 -2.54) (xy 1.905 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 -2.54) (xy 0 -5.08)) (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "PENTODE_1_1"
        (pin passive line (at 0 7.62 270) (length 2.54) (name "P" %(F)s) (number "1" %(F)s))
        (pin input line (at -7.62 -0.635 0) (length 5.334) (name "G1" %(F)s) (number "2" %(F)s))
        (pin passive line (at 7.62 0.635 180) (length 5.334) (name "G2" %(F)s) (number "3" %(F)s))
        (pin passive line (at 0 -7.62 90) (length 2.54) (name "K" %(F)s) (number "4" %(F)s))))
    (symbol "cx:DIODE_TUBE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "V" (at 6.35 5.08 0) %(F)s)
      (property "Value" "diode" (at 6.35 2.54 0) %(F)s)
      (symbol "DIODE_TUBE_0_1"
        (circle (center 0 0) (radius 5.08) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 1.905) (xy 2.54 1.905) (xy 0 -0.635) (xy -2.54 1.905))
          (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy -2.54 -0.635) (xy 2.54 -0.635)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 1.905) (xy 0 5.08)) (stroke (width 0.254) (type default)) (fill (type none)))
        (polyline (pts (xy 0 -0.635) (xy 0 -5.08)) (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "DIODE_TUBE_1_1"
        (pin passive line (at 0 7.62 270) (length 2.54) (name "A" %(F)s) (number "1" %(F)s))
        (pin passive line (at 0 -7.62 90) (length 2.54) (name "K" %(F)s) (number "2" %(F)s))))
    (symbol "cx:OT_SE" (pin_numbers hide) (pin_names hide) (in_bom yes) (on_board yes)
      (property "Reference" "T" (at -6.35 10.16 0) %(F)s)
      (property "Value" "OT" (at 0 0 0) %(F)s)
      (symbol "OT_SE_0_1"
        (rectangle (start -6.35 -6.35) (end 6.35 6.35)
          (stroke (width 0.254) (type default)) (fill (type none))))
      (symbol "OT_SE_1_1"
        (pin passive line (at -8.89 2.54 0) (length 2.54) (name "PRI_P" %(F)s) (number "1" %(F)s))
        (pin passive line (at -8.89 -2.54 0) (length 2.54) (name "PRI_B" %(F)s) (number "2" %(F)s))
        (pin passive line (at 8.89 2.54 180) (length 2.54) (name "SEC_H" %(F)s) (number "3" %(F)s))
        (pin passive line (at 8.89 -2.54 180) (length 2.54) (name "SEC_C" %(F)s) (number "4" %(F)s)))))
""" % {"F": FONT}

# ------------------------------------------------------------ emit helpers
body: list[str] = []


def sym(lib: str, ref: str, val: str, x: float, y: float, rot: int = 0) -> None:
    body.append(f"""  (symbol (lib_id "cx:{lib}") (at {x:g} {y:g} {rot}) (unit 1)
    (in_bom yes) (on_board yes) (uuid "{u()}")
    (property "Reference" "{ref}" (at {x + 2.2:g} {y - 3.2:g} 0) {FONT_L})
    (property "Value" "{val}" (at {x + 2.2:g} {y - 0.8:g} 0) {FONT_L}))""")


def wire(x1: float, y1: float, x2: float, y2: float) -> None:
    body.append(f"""  (wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))
    (stroke (width 0) (type default)) (uuid "{u()}"))""")


def glabel(name: str, x: float, y: float, rot: int = 0) -> None:
    body.append(f"""  (global_label "{name}" (shape input) (at {x:g} {y:g} {rot})
    (effects (font (size 1.27 1.27)) (justify left)) (uuid "{u()}"))""")


def junction(x: float, y: float) -> None:
    body.append(f"""  (junction (at {x:g} {y:g}) (diameter 0) (color 0 0 0 0) (uuid "{u()}"))""")


def text(t: str, x: float, y: float, size: float = 1.6) -> None:
    body.append(f"""  (text "{t}" (at {x:g} {y:g} 0)
    (effects (font (size {size:g} {size:g})) (justify left)) (uuid "{u()}"))""")


def gnd(x: float, y: float) -> None:
    glabel("GND", x, y, 270)


# --------------------------------------------------------------- the 5F1
text("5F1 — Tweed Champ-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 25, 70, 2.0)
text("Heaters and PT primary omitted — see netlist.cir and meta.yaml", 25, 74.5, 1.3)

# V1A input stage -----------------------------------------------------
glabel("INPUT", 33, 100, 180)
wire(33, 100, 41.91, 100)
sym("R", "R3", "68k", 45.72, 100, 90)
wire(49.53, 100, 53.34, 100)
sym("TRIODE", "V1A", "1/2 12AX7", 60.96, 100)
junction(53.34, 100)
sym("R", "R1", "1M", 53.34, 110.49)
wire(53.34, 100, 53.34, 106.68)
gnd(53.34, 114.3)
# cathode
wire(60.96, 107.62, 60.96, 111.76)
junction(60.96, 111.76)
sym("R", "R4", "1.5k", 60.96, 115.57)
wire(60.96, 111.76, 68.58, 111.76)
sym("C", "C2", "25u", 68.58, 115.57)
wire(60.96, 119.38, 68.58, 119.38)
gnd(60.96, 119.38)
# plate + supply
wire(60.96, 92.38, 60.96, 88.9)
junction(60.96, 88.9)
sym("R", "R5", "100k", 60.96, 85.09)
wire(60.96, 81.28, 60.96, 78.74)
glabel("B+3", 60.96, 78.74, 90)
# coupling to volume
wire(60.96, 88.9, 68.58, 88.9)
sym("C", "C1", "22n", 72.39, 88.9, 90)
wire(76.2, 88.9, 81.28, 88.9)
wire(81.28, 88.9, 81.28, 100)
junction(81.28, 100)
sym("R", "VR1", "1M vol", 81.28, 103.81)
wire(81.28, 107.62, 81.28, 110.16)
gnd(81.28, 110.16)

# V1B driver stage ----------------------------------------------------
wire(81.28, 100, 99.06, 100)
sym("TRIODE", "V1B", "1/2 12AX7", 106.68, 100)
wire(106.68, 107.62, 106.68, 111.76)
junction(106.68, 111.76)
sym("R", "R6", "1.5k", 106.68, 115.57)
wire(106.68, 111.76, 99.06, 111.76)
sym("C", "C4", "25u", 99.06, 115.57)
wire(99.06, 119.38, 106.68, 119.38)
gnd(106.68, 119.38)
# NFB from speaker into V1B cathode
wire(106.68, 111.76, 114.3, 111.76)
sym("R", "R13", "22k NFB", 114.3, 115.57)
wire(114.3, 119.38, 114.3, 121.92)
glabel("SPKR", 114.3, 121.92, 270)
# plate
wire(106.68, 92.38, 106.68, 88.9)
junction(106.68, 88.9)
sym("R", "R7", "100k", 106.68, 85.09)
wire(106.68, 81.28, 106.68, 78.74)
glabel("B+3", 106.68, 78.74, 90)
wire(106.68, 88.9, 114.3, 88.9)
sym("C", "C3", "22n", 118.11, 88.9, 90)
wire(121.92, 88.9, 127, 88.9)
wire(127, 88.9, 127, 100)
junction(127, 100)
sym("R", "R9", "220k", 127, 103.81)
wire(127, 107.62, 127, 110.16)
gnd(127, 110.16)

# 6V6 output stage ----------------------------------------------------
wire(127, 100, 129.54, 100)
sym("PENTODE", "V2", "6V6GT", 137.16, 100.635)
# grid pin lands at (129.54, 101.27); tie the run down to it
wire(129.54, 100, 129.54, 101.27)
# screen to B+2
wire(144.78, 100, 147.32, 100)
wire(147.32, 100, 147.32, 105.41)
glabel("B+2", 147.32, 105.41, 270)
# cathode
wire(137.16, 108.255, 137.16, 111.76)
junction(137.16, 111.76)
sym("R", "R8", "470", 137.16, 115.57)
wire(137.16, 111.76, 144.78, 111.76)
sym("C", "C6", "25u", 144.78, 115.57)
wire(137.16, 119.38, 144.78, 119.38)
gnd(137.16, 119.38)
# plate to OT
wire(137.16, 93.015, 137.16, 87.63)
wire(137.16, 87.63, 148.59, 87.63)
sym("OT_SE", "T2", "8k:8", 157.48, 90.17)
wire(148.59, 87.63, 148.59, 87.63)
wire(148.59, 87.63, 148.59, 87.63)
wire(148.59, 87.63, 148.59, 87.63)
wire(148.59, 87.63, 148.59, 92.71)
wire(148.59, 92.71, 148.59, 87.63)
# OT pins: pri_p at (148.59, 87.63), pri_b at (148.59, 92.71)
wire(148.59, 92.71, 146.05, 92.71)
wire(146.05, 92.71, 146.05, 95.25)
glabel("B+1", 146.05, 95.25, 270)
wire(166.37, 87.63, 168.91, 87.63)
glabel("SPKR", 168.91, 87.63, 0)
wire(166.37, 92.71, 168.91, 92.71)
glabel("GND", 168.91, 92.71, 0)

# power supply --------------------------------------------------------
text("Power supply — 325-0-325 PT secondary, 5Y3GT full-wave", 25, 140, 1.6)
glabel("HT_A", 50.8, 139.7, 90)
wire(50.8, 139.7, 50.8, 142.38)
sym("DIODE_TUBE", "V3A", "1/2 5Y3GT", 50.8, 150)
glabel("HT_B", 63.5, 139.7, 90)
wire(63.5, 139.7, 63.5, 142.38)
sym("DIODE_TUBE", "V3B", "1/2 5Y3GT", 63.5, 150)
wire(50.8, 157.62, 50.8, 160.02)
wire(63.5, 157.62, 63.5, 160.02)
wire(50.8, 160.02, 95.25, 160.02)
junction(63.5, 160.02)
junction(76.2, 160.02)
sym("C", "C5", "26u", 76.2, 163.83)
gnd(76.2, 167.64)
glabel("B+1", 95.25, 160.02, 0)
wire(95.25, 160.02, 97.79, 160.02)
sym("R", "R10", "10k", 101.6, 160.02, 90)
wire(105.41, 160.02, 114.3, 160.02)
junction(107.95, 160.02)
glabel("B+2", 107.95, 157.48, 90)
wire(107.95, 157.48, 107.95, 160.02)
junction(111.76, 160.02)
sym("C", "C7", "8u", 111.76, 163.83)
gnd(111.76, 167.64)
sym("R", "R11", "22k", 118.11, 160.02, 90)
wire(121.92, 160.02, 129.54, 160.02)
junction(124.46, 160.02)
glabel("B+3", 124.46, 157.48, 90)
wire(124.46, 157.48, 124.46, 160.02)
sym("C", "C8", "8u", 129.54, 163.83)
gnd(129.54, 167.64)

# ------------------------------------------------------------------ file
doc = f"""(kicad_sch (version 20231120) (generator "circuit-codex")
  (uuid "{u()}")
  (paper "A4")
{LIB}
{chr(10).join(body)}
  (sheet_instances (path "/" (page "1")))
)
"""
OUT.write_text(doc)
print(f"wrote {OUT} ({len(doc)} bytes, {len(body)} elements)")
