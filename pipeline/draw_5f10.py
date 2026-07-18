#!/usr/bin/env python3
"""Generate amps/5f10/schematic.kicad_sch from the stage-template library.

Values per the published Harvard 5F10 (F-EF) drawing (see amps/5f10/meta.yaml).
Signal flows left->right on the upper rows; power supply + bias sit below.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f10" / "schematic.kicad_sch"
s = Sch()

# ---- input: three jacks, each a 68k stopper, merged to the 6AT6 grid ------
# The chassis has three jacks (1/2/3); the grid returns to ground through the
# switched jacks — drawn here as jack 1 normalled to ground via its 68k (R1s).
GB = 44          # grid-bus x
for jack, ref, y in [("IN3", "R3s", 86), ("IN2", "R2s", 96), ("IN1", "R1s", 112)]:
    s.glabel(jack, 16, y, 180)
    s.wire(16, y, 20, y)
    l, r = s.series_h("R", ref, "68k", 26, y)
    s.wire(20, y, l, y)
    s.wire(r, y, GB, y)
    s.junction(GB, y)
s.gnd(20, 116)                 # jack-1 normalling ground (grid DC reference)
s.wire(20, 112, 20, 116)
s.wire(GB, 86, GB, 112)        # grid bus
s.text("Inputs 1-3, each via a 68k stopper; grid grounded through the switched jacks", 14, 80, 1.1)

# ---- V1 6AT6 first stage ------------------------------------------------
t1 = s.triode("V1", "6AT6", 54, 100)
s.wire(GB, 100, t1["g"][0], 100)
s.junction(GB, 100)
s.plate_load("RL1", "100k", t1["p"], "B+3")
s.wire(54, 107.62, 54, 109)
s.shunt_rc("RK1", "1.5k", "C1", "25u", 54, 109)

# ---- volume + tone ------------------------------------------------------
# 6AT6 plate -> .02u -> volume(1M); bright .0005u across it; tone(1M)+.005u
tee = 100 - 7.62 - 3.48        # plate-stub tee y
s.wire(54, tee, 63, tee)
s.junction(54, tee)
cl, cr = s.series_h("C", "C2", ".02u", 67, tee)
s.wire(63, tee, cl, tee)
s.wire(cr, tee, 74, tee)       # node A (volume top)
s.sym("POT", "VR1", "1M vol", 74, tee + 3.81)
s.gnd(74, tee + 11.43)
# bright cap across the volume: node A -> wiper
s.wire(74, tee, 74, tee - 4)
s.wire(74, tee - 4, 82, tee - 4)
bl, br = s.series_h("C", "C3", ".0005u", 86, tee - 4)
s.wire(82, tee - 4, bl, tee - 4)
s.wire(br, tee - 4, 92, tee - 4)
s.wire(92, tee - 4, 92, tee + 3.81)
s.wire(79.08, tee + 3.81, 92, tee + 3.81)   # wiper to bright-cap return = node W
s.junction(79.08, tee + 3.81)
# tone: node A -> .005u -> tone pot(1M) -> gnd  (treble bleed)
s.wire(74, tee, 74, tee - 8)
s.junction(74, tee)
tl, tr = s.series_h("C", "C4", ".005u", 100, tee - 8)
s.wire(74, tee - 8, tl, tee - 8)
s.wire(tr, tee - 8, 106, tee - 8)
s.sym("POT", "VR2", "1M tone", 106, tee - 8 + 3.81)
s.gnd(106, tee - 8 + 11.43)
s.wire(111.08, tee - 8 + 3.81, 111.08, tee - 8)   # wiper tied to top (rheostat)
s.wire(111.08, tee - 8, 106, tee - 8)
# node W -> 12AX7 driver grid
s.wire(92, tee + 3.81, 92, 110)
s.wire(92, 110, 106.38, 110)

# ---- V2A 12AX7 driver ---------------------------------------------------
t2a = s.triode("V2A", "12AX7", 114, 110)
s.wire(106.38, 110, t2a["g"][0], 110)
s.plate_load("RL2", "100k", t2a["p"], "B+3")
# unbypassed 1.5k cathode; 56k NFB from the speaker returns here
s.wire(114, 117.62, 114, 120)
s.junction(114, 120)
s.sym("R", "RK2", "1.5k", 114, 123.81)
s.gnd(114, 127.62)
nl, nr = s.series_h("R", "RNFB", "56k", 124, 120)
s.wire(114, 120, nl, 120)
s.wire(nr, 120, 131, 120)
s.glabel("SPKR", 131, 120, 0)

# ---- V2B 12AX7 cathodyne phase inverter --------------------------------
# driver plate -> .02u -> PI grid; 1M leak to the 1.5k/56k cathode junction
ptee = 110 - 7.62 - 3.48
s.wire(114, ptee, 124, ptee)
s.junction(114, ptee)
dl, dr = s.series_h("C", "C5", ".02u", 128, ptee)
s.wire(124, ptee, dl, ptee)
s.wire(dr, ptee, 132.38, ptee)
s.wire(132.38, ptee, 132.38, 110)
t2b = s.triode("V2B", "12AX7", 140, 110)
s.wire(132.38, 110, t2b["g"][0], 110)
s.plate_load("RL3", "56k", t2b["p"], "B+3")
# cathode stack: K -> 1.5k -> J -> 56k -> gnd; grid leak 1M to J
s.wire(140, 117.62, 140, 120)
s.sym("R", "RKA", "1.5k", 140, 123.81)
s.junction(140, 127.62)
s.sym("R", "RKB", "56k", 140, 131.42)
s.gnd(140, 135.23)
# grid leak from PI grid down to the junction J (140,127.62)
s.wire(132.38, 110, 132.38, 127.62)
s.junction(132.38, 110)
s.sym("R", "RGPI", "1M", 132.38, 123.81, lx=-9.4)
s.wire(132.38, 127.62, 140, 127.62)

# ---- couplers from the PI to the 6V6 grids ------------------------------
# plate (top) -> C6 .1u/400 -> upper 6V6 grid (approached horizontally at y=92,
# clear of the grid-leak RG1 that drops from that node); cathode -> C7 -> lower
s.wire(140, ptee, 146.19, ptee)       # plate-side tap
s.junction(140, ptee)
al, ar = s.series_h("C", "C6", ".1u", 150, ptee)
s.wire(ar, ptee, 155, ptee)
s.wire(155, ptee, 155, 92)
s.wire(155, 92, 158.75, 92)
s.wire(140, 120, 146.19, 120)         # cathode-side tap (top of RKA)
s.junction(140, 120)
kl, kr = s.series_h("C", "C7", ".1u", 150, 120)
s.wire(kr, 120, 158.75, 120)
s.wire(158.75, 120, 158.75, 132)

# ---- 6V6GT pair, fixed bias --------------------------------------------
for y, vref, gl, st in [(92, "V3", "RG1", "Rs1"), (132, "V4", "RG2", "Rs2")]:
    l, r = s.series_h("R", st, "1.5k", 163.83, y)
    s.wire(158.75, y, l, y)
    p = s.pentode(vref, "6V6GT", 175.26, y)
    s.wire(r, y, p["g1"][0], y)
    s.junction(158.75, y)
    s.sym("R", gl, "220k", 158.75, y + 3.81)
    s.wire(158.75, y + 7.62, 158.75, y + 10.16)
    s.glabel("-21V", 158.75, y + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(175.26, p["k"][1])           # cathode to ground (fixed bias)

# ---- output transformer -------------------------------------------------
s.sym("OT_PP", "T1", "PP OT", 203.2, 112)
s.wire(175.26, 83.745, 175.26, 81.28)
s.wire(175.26, 81.28, 194.31, 81.28)
s.wire(194.31, 81.28, 194.31, 106.92)   # upper plate -> PRI_A
s.wire(175.26, 123.745, 175.26, 121.3)
s.wire(175.26, 121.3, 190, 121.3)
s.wire(190, 121.3, 190, 117.08)
s.wire(190, 117.08, 194.31, 117.08)     # lower plate -> PRI_B
s.wire(194.31, 112, 191.77, 112)
s.wire(191.77, 112, 191.77, 109)
s.glabel("B+1", 191.77, 109, 90)        # center tap
s.wire(212.09, 109.46, 214.63, 109.46)
s.glabel("SPKR", 214.63, 109.46, 0)     # NFB taps this node
s.wire(212.09, 114.54, 214.63, 114.54)
s.glabel("GND", 214.63, 114.54, 0)

# ---- power supply -------------------------------------------------------
s.text("Power supply — HT winding, 5Y3GT full-wave (heaters, PT primary, AC switch/fuse omitted)", 22, 158, 1.5)
for x, ref, ht in [(45.72, "V5A", "HT_A"), (58.42, "V5B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5Y3GT", x, 167.78, lx=(-11.4 if ref == "V5A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(45.72, 177.8, 90.17, 177.8)
s.junction(58.42, 177.8)
s.junction(71.12, 177.8)
s.sym("C", "C8", "16u", 71.12, 181.61)
s.gnd(71.12, 185.42)
s.glabel("B+1", 90.17, 177.8, 0)
s.wire(90.17, 177.8, 92.71, 177.8)
l, r = s.series_h("R", "RD1", "470", 96.52, 177.8)
s.wire(r, 177.8, 109.22, 177.8)
s.junction(102.87, 177.8)
s.glabel("B+2", 102.87, 175.26, 90)
s.wire(102.87, 175.26, 102.87, 177.8)
s.junction(106.68, 177.8)
s.sym("C", "C9", "16u", 106.68, 181.61)
s.gnd(106.68, 185.42)
l, r = s.series_h("R", "RD2", "22k", 113.03, 177.8)
s.wire(r, 177.8, 124.46, 177.8)
s.junction(119.38, 177.8)
s.glabel("B+3", 119.38, 175.26, 90)
s.wire(119.38, 175.26, 119.38, 177.8)
s.sym("C", "C10", "16u", 124.46, 181.61)
s.gnd(124.46, 185.42)

# ---- bias supply --------------------------------------------------------
s.text("Bias supply — selenium rectifier off an HT tap -> -21 V (25u x2)", 138, 160, 1.3)
s.glabel("HT_B", 138, 168, 180)
s.wire(138, 168, 141.91, 168)
s.sym("DIODE_SS", "D1", "SEL", 146.99, 168, lx=-2.0, ly=-5.4)
s.wire(152.07, 168, 155.88, 168)
l, r = s.series_h("R", "RB1", "6.8k", 159.69, 168)
s.wire(155.88, 168, l, 168)
s.wire(r, 168, 171.12, 168)
s.junction(166.04, 168)
s.sym("R", "RB2", "56k", 166.04, 171.81)
s.gnd(166.04, 175.62)
s.junction(168.58, 168)
s.sym("C", "C11", "25u", 168.58, 171.81, lx=2.2)
s.gnd(168.58, 175.62)
s.glabel("-21V", 171.12, 168, 0)

s.write(OUT, [
    ("5F10 — Tweed Harvard-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 22, 70, 2.0),
    ("Heaters, PT primary, AC switch/fuse/pilot omitted — see netlist.cir and meta.yaml", 22, 74.5, 1.3),
])
print(f"wrote {OUT}")
