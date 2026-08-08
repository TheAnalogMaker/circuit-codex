#!/usr/bin/env python3
"""Generate amps/5f1/schematic.kicad_sch — the redrawn 5F1 schematic.

Spike goals (docs/2026-07-18-kicad-spike.md): prove programmatic KiCad
authoring with a self-contained symbol set (lib "cx", CC-BY-SA, no external
library dependencies), kiutils round-trip, and KiCanvas browser rendering.

Coordinates: schematic space, mm, +Y down. Symbol space is +Y up; a symbol
pin at (sx, sy) lands at (x + sx, y - sy) for rotation 0.

Ported to schematic_lib 2026-08-08: this file kept a private copy of the base
symbols from the original spike, so it missed every later improvement to the
shared set — the transformer glyphs, the fitted sheet, the title block.
"""
from __future__ import annotations
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f1" / "schematic.kicad_sch"
s = Sch()


# --------------------------------------------------------------- the 5F1

# V1A input stage -----------------------------------------------------
s.glabel("INPUT", 33, 100, 180)
s.wire(33, 100, 41.91, 100)
s.sym("R", "R3", "68k", 45.72, 100, 90, lx=-3.2, ly=-6.0)
s.wire(49.53, 100, 53.34, 100)
s.sym("TRIODE", "V1A", "12AX7", 60.96, 100, lx=6.0, ly=-6.4)
s.junction(53.34, 100)
s.sym("R", "R1", "1M", 53.34, 110.49)
s.wire(53.34, 100, 53.34, 106.68)
s.gnd(53.34, 114.3)
# cathode
s.wire(60.96, 107.62, 60.96, 111.76)
s.junction(60.96, 111.76)
s.sym("R", "R4", "1.5k", 60.96, 115.57)
s.wire(60.96, 111.76, 68.58, 111.76)
s.sym("C", "C2", "25u", 68.58, 115.57)
s.wire(60.96, 119.38, 68.58, 119.38)
s.gnd(60.96, 119.38)
# plate + supply
s.wire(60.96, 92.38, 60.96, 88.9)
s.junction(60.96, 88.9)
s.sym("R", "R5", "100k", 60.96, 85.09)
s.wire(60.96, 81.28, 60.96, 78.74)
s.glabel("B+3", 60.96, 78.74, 90)
# coupling to volume
s.wire(60.96, 88.9, 68.58, 88.9)
s.sym("C", "C1", ".02u", 72.39, 88.9, 90, lx=-3.2, ly=-6.2)
s.wire(76.2, 88.9, 81.28, 88.9)
s.wire(81.28, 88.9, 81.28, 100)
s.junction(81.28, 100)
s.sym("R", "VR1", "1M vol", 81.28, 103.81)
s.wire(81.28, 107.62, 81.28, 110.16)
s.gnd(81.28, 110.16)

# V1B driver stage ----------------------------------------------------
s.wire(81.28, 100, 99.06, 100)
s.sym("TRIODE", "V1B", "12AX7", 106.68, 100, lx=6.0, ly=-6.4)
s.wire(106.68, 107.62, 106.68, 111.76)
s.junction(106.68, 111.76)
s.sym("R", "R6", "1.5k", 106.68, 115.57)
s.wire(106.68, 111.76, 99.06, 111.76)
s.sym("C", "C4", "25u", 99.06, 115.57)
s.wire(99.06, 119.38, 106.68, 119.38)
s.gnd(106.68, 119.38)
# NFB from speaker into V1B cathode
s.wire(106.68, 111.76, 114.3, 111.76)
s.sym("R", "R13", "22k NFB", 114.3, 115.57)
s.wire(114.3, 119.38, 114.3, 121.92)
s.glabel("SPKR", 114.3, 121.92, 270)
# plate
s.wire(106.68, 92.38, 106.68, 88.9)
s.junction(106.68, 88.9)
s.sym("R", "R7", "100k", 106.68, 85.09)
s.wire(106.68, 81.28, 106.68, 78.74)
s.glabel("B+3", 106.68, 78.74, 90)
s.wire(106.68, 88.9, 114.3, 88.9)
s.sym("C", "C3", ".02u", 118.11, 88.9, 90, lx=-3.2, ly=-6.2)
s.wire(121.92, 88.9, 127, 88.9)
s.wire(127, 88.9, 127, 100)
s.junction(127, 100)
s.sym("R", "R9", "220k", 127, 103.81)
s.wire(127, 107.62, 127, 110.16)
s.gnd(127, 110.16)

# 6V6 output stage ----------------------------------------------------
s.wire(127, 100, 129.54, 100)
s.sym("PENTODE", "V2", "6V6GT", 137.16, 100.635, lx=6.2, ly=-7.6)
# grid pin lands at (129.54, 101.27); tie the run down to it
s.wire(129.54, 100, 129.54, 101.27)
# screen to B+2
s.wire(144.78, 100, 147.32, 100)
s.wire(147.32, 100, 147.32, 105.41)
s.glabel("B+2", 147.32, 105.41, 270)
# cathode
s.wire(137.16, 108.255, 137.16, 111.76)
s.junction(137.16, 111.76)
s.sym("R", "R8", "470", 137.16, 115.57)
s.wire(137.16, 111.76, 144.78, 111.76)
s.sym("C", "C6", "25u", 144.78, 115.57)
s.wire(137.16, 119.38, 144.78, 119.38)
s.gnd(137.16, 119.38)
# plate to OT
s.wire(137.16, 93.015, 137.16, 87.63)
s.wire(137.16, 87.63, 148.59, 87.63)
s.sym("OT_SE", "T2", "SE 5k:8", 157.48, 90.17)
s.wire(148.59, 87.63, 148.59, 87.63)
s.wire(148.59, 87.63, 148.59, 87.63)
s.wire(148.59, 87.63, 148.59, 87.63)
s.wire(148.59, 87.63, 148.59, 92.71)
s.wire(148.59, 92.71, 148.59, 87.63)
# OT pins: pri_p at (148.59, 87.63), pri_b at (148.59, 92.71)
s.wire(148.59, 92.71, 146.05, 92.71)
s.wire(146.05, 92.71, 146.05, 95.25)
s.glabel("B+1", 146.05, 95.25, 270)
s.wire(166.37, 87.63, 168.91, 87.63)
s.glabel("SPKR", 168.91, 87.63, 0)
s.wire(166.37, 92.71, 168.91, 92.71)
s.glabel("GND", 168.91, 92.71, 0)

# power supply --------------------------------------------------------
s.note('Power supply — 325-0-325 PT secondary, 5Y3GT full-wave')
s.glabel("HT_A", 50.8, 139.7, 90)
s.wire(50.8, 139.7, 50.8, 142.38)
s.sym("DIODE_TUBE", "V3A", "5Y3GT", 50.8, 150, lx=-11.4, ly=-6.4)
s.glabel("HT_B", 63.5, 139.7, 90)
s.wire(63.5, 139.7, 63.5, 142.38)
s.sym("DIODE_TUBE", "V3B", "5Y3GT", 63.5, 150, lx=6.0, ly=-6.4)
s.wire(50.8, 157.62, 50.8, 160.02)
s.wire(63.5, 157.62, 63.5, 160.02)
s.wire(50.8, 160.02, 95.25, 160.02)
s.junction(63.5, 160.02)
s.junction(76.2, 160.02)
s.sym("C", "C5", "16u", 76.2, 163.83)
s.gnd(76.2, 167.64)
s.glabel("B+1", 95.25, 160.02, 0)
s.wire(95.25, 160.02, 97.79, 160.02)
s.sym("R", "R10", "10k", 101.6, 160.02, 90, lx=-3.2, ly=-6.0)
s.wire(105.41, 160.02, 114.3, 160.02)
s.junction(107.95, 160.02)
s.glabel("B+2", 107.95, 154.94, 90)
s.wire(107.95, 154.94, 107.95, 160.02)
s.junction(111.76, 160.02)
s.sym("C", "C7", "8u", 111.76, 163.83)
s.gnd(111.76, 167.64)
s.sym("R", "R11", "22k", 118.11, 160.02, 90, lx=-3.2, ly=-6.0)
s.wire(121.92, 160.02, 129.54, 160.02)
s.junction(124.46, 160.02)
s.glabel("B+3", 124.46, 154.94, 90)
s.wire(124.46, 154.94, 124.46, 160.02)
s.sym("C", "C8", "8u", 129.54, 163.83)
s.gnd(129.54, 167.64)

s.write(OUT, [
    "Heaters and PT primary omitted — see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
