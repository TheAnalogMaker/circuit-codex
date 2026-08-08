#!/usr/bin/env python3
"""Generate amps/5e4a/schematic.kicad_sch from the stage-template library.

Values per the published 5E4-A (G-EE) drawing (see amps/5e4a/meta.yaml), whose
title block reads "MODEL 5E4-A*" with the footnote "*NOTE - (A) WAS 22 K OHMS"
against the bias-supply series resistor. The circuit is redrawn from the
extracted component list, never traced.

The sheet is the 5F4's direct ancestor and the drawing follows the same order,
so this generator is deliberately the 5F4's with this revision's values: a
second 12AY7 where the 5F4 puts a 12AX7, a 6V6GT output pair on a -32 V bias
line, 5 MOhm instead of 4.7 MOhm on the gain stage's grid, an 18 kOhm bias
series resistor (the footnoted change) and a 100 uF bias can.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e4a" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, two channels, shared 820R/25u cathode ---------------------
for ch, (y, jack, gref, pref, plref, cref, vref, mref) in enumerate([
        (92, "CH1", "RG1", "V1A", "RL1", "C1", "VR1", "RM1"),
        (126, "CH2", "RG2", "V1B", "RL2", "C2", "VR2", "RM2")]):
    s.glabel(jack, 26, y, 180)
    s.wire(26, y, 30.48, y)
    l, r = s.series_h("R", f"R{ch + 1}s", "68k", 34.29, y)
    s.wire(30.48, y, l, y)
    t = s.triode(pref, "12AY7", 49.53, y)
    s.wire(r, y, t["g"][0], y)
    s.junction(t["g"][0] - 3.81, y)
    s.sym("R", gref, "1M", t["g"][0] - 3.81, y + 3.81)
    s.gnd(t["g"][0] - 3.81, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # coupler -> volume pot -> 270k mixer into the shared V2A grid line
    ty = y - 7.62 - 3.48                # plate stub tee
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", cref, ".02u", 64.77, ty)
    s.wire(crr, ty, 73.66, ty)
    s.sym("POT", vref, "1M vol", 73.66, ty + 3.81)
    s.gnd(73.66, ty + 11.43)
    s.wire(78.74, ty + 3.81, 81.28, ty + 3.81)
    ml, mr = s.series_h("R", mref, "270k", 85.09, ty + 3.81)
    s.wire(81.28, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 91.44, ty + 3.81)
    s.wire(91.44, ty + 3.81, 91.44, 109)
s.junction(91.44, 109)
s.text("100 pF bright cap across VR1 omitted (AC only)", 56, 76, 1.1)

# shared cathode
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C3", "25u", 56.13, 140)

# ---- V2A gain + DC-coupled cathode follower ----------------------------
t2a = s.triode("V2A", "12AY7", 101.6, 109)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 118)
s.shunt_rc("RK2", "1.5k", "C4", "25u", 101.6, 118)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# 5M reference to the V2A grid (≈0 V DC) — the G-EE sheet returns it from
# the tone network's bass-branch node (the far side of the 0.1 µF coupler),
# NOT from the stack output
s.junction(91.44, 109)
s.wire(91.44, 109, 91.44, 84)
fl, fr = s.series_h("R", "RF1", "5M", 120, 84)
s.wire(91.44, 84, fl, 84)
s.wire(fr, 84, 137, 84)
s.wire(137, 84, 137, 119.5)             # down to node B (crossing = no join)
# direct-coupled CF: grid from the plate stub tee
tee = 109 - 7.62 - 3.48
s.wire(101.6, tee, 108.9, tee)
s.junction(101.6, tee)
tcf = s.triode("V2B", "12AY7 CF", 116.84, 109)
s.wire(108.9, tee, 108.9, 109)
s.wire(108.9, 109, tcf["g"][0], 109)
s.wire(116.84, 101.38, 116.84, 98.5)
s.glabel("B+4", 116.84, 98.5, 90)      # CF plate straight to the rail
s.wire(116.84, 116.62, 116.84, 119.5)
s.junction(116.84, 119.5)
s.sym("R", "RKCF", "100k", 116.84, 123.31)
s.gnd(116.84, 127.12)

# ---- tone network (treble/bass, split) ----------------------------------
# Wired as the published 5E4-A (G-EE) schematic draws it — NOT a two-knob cut
# of the Bassman ladder. Two branches leave the cathode follower and
# recombine at the phase inverter's grid:
#   treble: A -> 250 pF -> treble pot; its far end -> .01 -> ground; the
#           wiper is the output;
#   bass:   A -> .1-200 -> node B (220k to ground, 4.7M feedback return)
#           -> 100k -> the BASS POT'S WIPER (one end lug -> .005 -> ground,
#           the other grounded outright) -> 220k -> the output node.
# No coupling capacitor follows: the output node IS the PI grid.
s.wire(116.84, 119.5, 124.46, 119.5)
s.junction(124.46, 119.5)
s.wire(124.46, 119.5, 124.46, 94)       # node A up to the 250 pF branch
s.wire(124.46, 94, 126.19, 94)
tl, tr = s.series_h("C", "C5", "250p", 130, 94)
s.wire(tr, 94, 140, 94)
s.sym("POT", "VR3", "1M treb", 140, 97.81)
s.sym("C", "C6", ".01u", 140, 105.43)   # treble pot cold end -> .01 -> ground
s.gnd(140, 109.24)
# treble wiper -> the output node (the PI grid), down the right side
s.wire(145.08, 97.81, 163, 97.81)
s.wire(163, 97.81, 163, 126)
# bass branch: A -> C16 .1 -> node B
c16l, c16r = s.series_h("C", "C16", ".1u", 130, 119.5)
s.wire(124.46, 119.5, c16l, 119.5)
s.wire(c16r, 119.5, 137, 119.5)
s.junction(137, 119.5)                  # node B: 220k leak + 4.7M feedback
s.sym("R", "RSH", "220k", 137, 123.31)
s.gnd(137, 127.12)
sl, sr = s.series_h("R", "RSL", "100k", 143, 119.5)
s.wire(137, 119.5, sl, 119.5)
s.wire(sr, 119.5, 149, 119.5)
s.junction(149, 119.5)                  # node W: injected at the bass wiper
s.wire(149, 119.5, 149, 130)
s.sym("POT", "VR4", "1M bass", 143.92, 130)
s.wire(143.92, 126.19, 140, 126.19)     # one end lug grounded outright
s.wire(140, 126.19, 140, 128)
s.gnd(140, 128)
s.sym("C", "C7", ".005u", 143.92, 137.62)  # the other end lug -> .005 -> gnd
s.gnd(143.92, 141.43)
# W -> 220k -> the output node
rsl2, rsr2 = s.series_h("R", "RSR", "220k", 156, 119.5)
s.wire(149, 119.5, rsl2, 119.5)
s.wire(rsr2, 119.5, 163, 119.5)
s.junction(163, 119.5)

# ---- phase inverter: driver (V3A) + split-load cathodyne (V3B) ----------
# The G-EE sheet draws no long-tailed pair: V3A is a plain cathode-biased
# gain stage (100k plate, 1.5k cathode at +1.6 V) fed DC-direct from the
# tone network; its plate couples through C8 0.02 µF into the cathodyne
# V3B, whose 1M grid leak returns to the 1.5k/56k cathode junction and
# whose plate and cathode each drive an output grid through 0.1 µF.
bt = s.triode("V3A", "12AX7", 176.53, 126, lx=8.8)   # driver (drawn below)
s.wire(163, 126, bt["g"][0], 126)
tp = s.triode("V3B", "12AX7", 176.53, 92)    # cathodyne (drawn above)
s.plate_load("RLA", "100k", bt["p"], "B+3")
s.plate_load("RLB", "56k", tp["p"], "B+3")
# driver cathode: 1.5k to ground; the 56k NFB + presence land here
s.sym("R", "RK3", "1.5k", 176.53, 137.43)
s.gnd(176.53, 141.24)
# driver plate tee -> C8 0.02 -> cathodyne grid (left side, up to y=92)
s.junction(176.53, 114.9)
c8l, c8r = s.series_h("C", "C8", ".02u", 168, 114.9)
s.wire(c8r, 114.9, 176.53, 114.9)
s.wire(c8l, 114.9, 160, 114.9)
s.wire(160, 114.9, 160, 92)
s.wire(160, 92, tp["g"][0], 92)
# cathodyne grid leak RGB 1M -> the 1.5k/56k junction
s.junction(160, 105)
gbl, gbr = s.series_h("R", "RGB", "1M", 167.5, 105)
s.wire(160, 105, gbl, 105)
s.wire(gbr, 105, 172.5, 105)
s.wire(172.5, 105, 172.5, 109.62)
s.wire(172.5, 109.62, 184.5, 109.62)
# cathodyne cathode chain: 1.5k -> J -> 56k -> gnd (beside the tube)
s.wire(176.53, 99.62, 176.53, 102)
s.wire(176.53, 102, 184.5, 102)
s.sym("R", "RKA", "1.5k", 184.5, 105.81, lx=2.0)
s.junction(184.5, 109.62)
s.sym("R", "RKB", "56k", 184.5, 113.43, lx=2.0)
s.gnd(184.5, 117.24)
s.note("56k NFB from the speaker + 5k presence (0.1 µF on its wiper) land on V3A's cathode (annotation)")

# ---- 6V6GT pair, fixed bias ----------------------------------------------
# V4 is driven from the cathodyne's PLATE (C9, 0.1-400), V5 from its
# CATHODE (C10, 0.1-200) — the split-load pair of outputs the sheet draws.
for y, pref, cref, glref in [(84, "V4", "C9", "RGL1"), (136, "V5", "C10", "RGL2")]:
    if y == 84:
        s.wire(176.53, 80.9, 194.31, 80.9)     # cathodyne plate tee
        s.junction(176.53, 80.9)
        cl, crr = s.series_h("C", cref, ".1u", 198.12, 80.9)
        s.wire(crr, 80.9, 205.74, 80.9)
        s.wire(205.74, 80.9, 205.74, 84)
        gy = 84
        gstop = "R5s"
    else:
        s.junction(184.5, 102)                # cathodyne cathode node
        cl, crr = s.series_h("C", cref, ".1u", 191, 102)
        s.wire(184.5, 102, cl, 102)
        s.wire(crr, 102, 196, 102)
        s.wire(196, 102, 196, 136)
        s.wire(196, 136, 205.74, 136)
        gy = 136
        gstop = "R6s"
    # grid stopper 1.5k in series, then 220k grid leak to -40V
    s.wire(205.74, gy, 208.28, gy)
    gl2, gr2 = s.series_h("R", gstop, "1.5k", 212.09, gy)
    p = s.pentode(pref, "6V6GT", 221.6, gy)
    s.wire(gr2, gy, p["g1"][0], gy)
    s.junction(208.28, gy)
    s.sym("R", glref, "220k", 208.28, gy + 3.81)
    s.wire(208.28, gy + 7.62, 208.28, gy + 10.16)
    s.glabel("-32V", 208.28, gy + 10.16, 270)
    # screen straight to B+2 (no screen resistor on the G-EE drawing)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(221.6, p["k"][1] + 0)

# ---- output transformer -------------------------------------------------
s.sym("OT_PP", "T3", "OT", 249.5, 110)
s.wire(221.6, 84 - 0.635 - 7.62, 221.6, 73.5)
s.wire(221.6, 73.5, 240.61, 73.5)
s.wire(240.61, 73.5, 240.61, 104.92)
s.wire(221.6, 136 - 0.635 - 7.62, 221.6, 126.5)
s.wire(221.6, 126.5, 235.7, 126.5)
s.wire(235.7, 126.5, 235.7, 115.08)
s.wire(235.7, 115.08, 240.61, 115.08)
s.wire(240.61, 110, 238.07, 110)
s.wire(238.07, 110, 238.07, 107)
s.glabel("B+1", 238.07, 107, 90)
s.wire(258.39, 107.46, 260.93, 107.46)
s.glabel("SPKR", 260.93, 107.46, 0)
s.wire(258.39, 112.54, 260.93, 112.54)
s.glabel("GND", 260.93, 112.54, 0)

# ---- power supply + bias ------------------------------------------------
s.text("Power — 5U4GA, choke, standby · bias: 18k/56k + selenium rect -> -32V (the sheet's footnote: the 18k was 22k)", 25, 158, 1.4)
for x, ref, ht in [(41.91, "V6A", "HT_A"), (54.61, "V6B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5U4GA", x, 167.78, lx=(-11.4 if ref == "V6A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(41.91, 177.8, 82.55, 177.8)
s.junction(54.61, 177.8)
s.junction(66.04, 177.8)
s.sym("C", "C11", "16u", 66.04, 181.61)
s.gnd(66.04, 185.42)
s.glabel("B+1", 82.55, 177.8, 0)
s.wire(82.55, 177.8, 85.09, 177.8)
s.sym("CHOKE", "L1", "choke", 92.71, 177.8, lx=-4.0, ly=-6.4)
s.wire(100.33, 177.8, 111.76, 177.8)
s.junction(105.41, 177.8)
s.glabel("B+2", 105.41, 175.26, 90)
s.wire(105.41, 175.26, 105.41, 177.8)
s.junction(108.86, 177.8)
s.sym("C", "C12", "16u", 108.86, 181.61)
s.gnd(108.86, 185.42)
l, r = s.series_h("R", "RD1", "10k", 115.57, 177.8)
s.wire(r, 177.8, 127, 177.8)
s.junction(121.92, 177.8)
s.glabel("B+3", 121.92, 175.26, 90)
s.wire(121.92, 175.26, 121.92, 177.8)
s.junction(124.46, 177.8)
s.sym("C", "C13", "16u", 124.46, 181.61)
s.gnd(124.46, 185.42)
l, r = s.series_h("R", "RD2", "10k", 130.81, 177.8)
s.wire(r, 177.8, 142.24, 177.8)
s.junction(137.16, 177.8)
s.glabel("B+4", 137.16, 175.26, 90)
s.wire(137.16, 175.26, 137.16, 177.8)
s.sym("C", "C14", "8u", 142.24, 181.61)
s.gnd(142.24, 185.42)
# bias supply: HT tap -> selenium -> 6.8k -> -40V node, 56k bleeder
# (row lifted 12 mm from y=172.72 so nothing reaches the A4 title-block corner)
s.glabel("HT_B", 150.1, 160.72, 180)
s.wire(150.1, 160.72, 153.91, 160.72)
s.sym("DIODE_SS", "D1", "SEL", 158.99, 160.72, lx=-2.0, ly=-5.4)
s.wire(164.07, 160.72, 167.88, 160.72)
l, r = s.series_h("R", "RB1", "18k", 171.69, 160.72)
s.wire(167.88, 160.72, l, 160.72)
s.wire(r, 160.72, 183.12, 160.72)
s.junction(178.04, 160.72)
s.sym("R", "RB2", "56k", 178.04, 164.53)
s.gnd(178.04, 168.34)
s.junction(180.58, 160.72)
s.sym("C", "C15", "100u", 180.58, 164.53, lx=2.2)
s.gnd(180.58, 168.34)
s.glabel("-32V", 183.12, 160.72, 0)

s.write(OUT, [
    "Heaters, PT primary and standby omitted — see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
