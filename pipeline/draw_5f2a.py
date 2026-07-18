#!/usr/bin/env python3
"""Generate amps/5f2a/schematic.kicad_sch from the stage-template library.

Values per the published 5F2-A (K-EG) drawing (see amps/5f2a/meta.yaml).
The 5F2-A is the tweed Champ signal path plus a single tone control and a
speaker-to-cathode feedback loop around the driver stage.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f2a" / "schematic.kicad_sch"
s = Sch()

# ---- input: two jacks (high/low), 68k stoppers, shared 1M leak ----------
s.glabel("INPUT-1", 24, 94, 180)
s.wire(24, 94, 28.48, 94)
la, ra = s.series_h("R", "R1", "68k", 32.29, 94)
s.wire(28.48, 94, la, 94)
s.wire(ra, 94, 44, 94)

s.glabel("INPUT-2", 24, 106, 180)
s.wire(24, 106, 28.48, 106)
lb, rb = s.series_h("R", "R2", "68k", 32.29, 106)
s.wire(28.48, 106, lb, 106)
s.wire(rb, 106, 44, 106)

# vertical bus x=44 collects both jacks; grid taps the middle at y=100
s.wire(44, 94, 44, 106)
s.junction(44, 94)
s.junction(44, 106)
s.junction(44, 100)
# 1M grid leak drops to ground from the grid tee at x=48
s.wire(44, 100, 48, 100)
s.junction(48, 100)
s.sym("R", "R3", "1M", 48, 103.81)
s.gnd(48, 107.62)

# ---- V1A input stage ----------------------------------------------------
t1a = s.triode("V1A", "12AX7", 62, 100)
s.wire(48, 100, t1a["g"][0], 100)     # grid tee -> V1A grid
# cathode 1.5k bypassed by 25u
s.wire(62, 107.62, 62, 110)
s.shunt_rc("R5", "1.5k", "C1", "25u", 62, 110)
# plate load 100k -> B+3
s.plate_load("R4", "100k", t1a["p"], "B+3")

# ---- coupling C2 -> tone/volume network ---------------------------------
s.wire(62, 88.9, 74, 88.9)
s.junction(62, 88.9)
cl, cr = s.series_h("C", "C2", ".02u", 77.81, 88.9)
s.wire(74, 88.9, cl, 88.9)
s.wire(cr, 88.9, 84, 88.9)
s.wire(84, 88.9, 84, 100)             # down into node X
s.junction(84, 88.9)
s.junction(84, 100)

# volume pot VR1: top = X, bottom = gnd, wiper -> node Y (V1B grid)
s.sym("POT", "VR1", "1M vol", 84, 103.81)
s.wire(84, 107.62, 84, 110)
s.gnd(84, 110)
s.wire(89.08, 103.81, 102, 103.81)
s.wire(102, 103.81, 102, 100)         # wiper -> Y

# C4 (500p) bypasses the volume pot: X -> Y (treble path into the grid)
s.wire(84, 88.9, 84, 84)
c4l, c4r = s.series_h("C", "C4", "500p", 93, 84)
s.wire(84, 84, c4l, 84)
s.wire(c4r, 84, 102, 84)
s.wire(102, 84, 102, 100)
s.junction(102, 100)

# tone: C3 (.005) in series with VR2 (1M) as a variable treble shunt X -> gnd
s.wire(84, 100, 76, 100)
s.sym("C", "C3", ".005u", 76, 103.81)   # top = X tap, bottom = tone node
s.sym("POT", "VR2", "1M tone", 76, 111.43)
s.wire(81.08, 111.43, 81.08, 107.62)    # wiper tied to top -> variable resistor
s.wire(81.08, 107.62, 76, 107.62)
s.wire(76, 115.24, 76, 117)
s.gnd(76, 117)

# ---- V1B driver stage (unbypassed cathode carries the feedback) ---------
t1b = s.triode("V1B", "12AX7", 110, 100)
s.wire(102, 100, t1b["g"][0], 100)    # Y -> V1B grid (102.38,100)
# cathode 1.5k, UNbypassed
s.wire(110, 107.62, 110, 110)
s.junction(110, 110)
s.sym("R", "R7", "1.5k", 110, 113.81)
s.gnd(110, 117.62)
# negative feedback R12 (22k) from the speaker into this cathode
s.wire(110, 110, 116, 110)
s.sym("R", "R12", "22k", 116, 106.19)   # vertical: bottom 110, top 102.38
s.wire(116, 102.38, 116, 99)
s.glabel("SPKR", 116, 99, 90)
# plate load 100k -> B+3
s.plate_load("R6", "100k", t1b["p"], "B+3")

# ---- coupling C5 -> 6V6 grid --------------------------------------------
s.wire(110, 88.9, 122, 88.9)
s.junction(110, 88.9)
c5l, c5r = s.series_h("C", "C5", ".02u", 127, 88.9)
s.wire(122, 88.9, c5l, 88.9)
s.wire(c5r, 88.9, 138, 88.9)
s.wire(138, 88.9, 138, 100)

# ---- 6V6GT output stage -------------------------------------------------
p6 = s.pentode("V2", "6V6GT", 148, 100)
s.wire(138, 100, p6["g1"][0], 100)    # -> grid1 (140.38,100)
s.junction(138, 100)
s.sym("R", "R8", "220k", 138, 103.81)  # grid leak
s.gnd(138, 107.62)
# cathode 470/1W bypassed by 25u
s.wire(148, 106.985, 148, 110)
s.shunt_rc("R9", "470 1W", "C6", "25u", 148, 110)
# screen -> B+2
s.wire(p6["g2"][0], p6["g2"][1], 158, p6["g2"][1])
s.wire(158, p6["g2"][1], 158, 104)
s.glabel("B+2", 158, 104, 270)
# plate -> OT primary
s.wire(148, 91.745, 148, 86)
s.wire(148, 86, 173.11, 86)

# ---- output transformer (single-ended) ----------------------------------
s.sym("OT_SE", "T2", "SE 5k:8", 182, 90)
s.wire(173.11, 86, 173.11, 87.46)     # 6V6 plate -> PRI_P
s.wire(173.11, 92.54, 170, 92.54)     # PRI_B -> B+1
s.wire(170, 92.54, 170, 96)
s.glabel("B+1", 170, 96, 270)
s.wire(190.89, 87.46, 195, 87.46)     # SEC_H -> speaker (+ feedback tap)
s.glabel("SPKR", 195, 87.46, 0)
s.wire(190.89, 92.54, 195, 92.54)     # SEC_C -> gnd
s.glabel("GND", 195, 92.54, 0)

# ---- power supply -------------------------------------------------------
s.text("Power supply — 66079 PT, 5Y3GT full-wave. Heaters, PT primary, fuse and switch omitted — see netlist.cir and meta.yaml", 24, 150, 1.5)
# 0.05 uF line cap (C11) to chassis after the fuse/switch
s.glabel("AC", 32, 156, 90)
s.wire(32, 156, 32, 159)
s.sym("C", "C11", ".05u", 32, 162.81)
s.gnd(32, 166.62)

for x, ref, ht in [(52, "V3A", "HT_A"), (64.7, "V3B", "HT_B")]:
    s.glabel(ht, x, 153, 90)
    s.wire(x, 153, x, 156.38)
    s.diode_tube(ref, "5Y3GT", x, 164, lx=(-11.4 if ref == "V3A" else 6.0))
    s.wire(x, 171.62, x, 174)
s.wire(52, 174, 96, 174)
s.junction(64.7, 174)
# B+1 first node: two 16u caps in parallel
s.junction(77, 174)
s.sym("C", "C7", "16u", 77, 177.81)
s.gnd(77, 181.62)
s.junction(86, 174)
s.sym("C", "C8", "16u", 86, 177.81)
s.gnd(86, 181.62)
s.glabel("B+1", 96, 174, 0)
s.wire(96, 174, 98.79, 174)
l, r = s.series_h("R", "R10", "10k 1W", 102.6, 174)
s.wire(r, 174, 115, 174)
s.junction(108.95, 174)
s.glabel("B+2", 108.95, 168, 90)
s.wire(108.95, 168, 108.95, 174)
s.junction(112.76, 174)
s.sym("C", "C9", "8u", 112.76, 177.81)
s.gnd(112.76, 181.62)
l, r = s.series_h("R", "R11", "22k", 119.11, 174)
s.wire(r, 174, 131, 174)
s.junction(125.46, 174)
s.glabel("B+3", 125.46, 168, 90)
s.wire(125.46, 168, 125.46, 174)
s.sym("C", "C10", "8u", 130.54, 177.81)
s.gnd(130.54, 181.62)

s.write(OUT, [
    ("5F2-A — Tweed Princeton-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 24, 70, 2.0),
    ("Single-ended 6V6; tone control + speaker-to-V1B-cathode feedback. Heaters and PT primary omitted — see netlist.cir and meta.yaml", 24, 74.5, 1.3),
])
print(f"wrote {OUT}")
