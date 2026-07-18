#!/usr/bin/env python3
"""Generate amps/5f4/schematic.kicad_sch from the stage-template library.

Values per the published 5F4 (C-EG) drawing (see amps/5f4/meta.yaml). The
circuit is redrawn from the extracted component list, not traced.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f4" / "schematic.kicad_sch"
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
t2a = s.triode("V2A", "12AX7", 101.6, 109)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 118)
s.shunt_rc("RK2", "1.5k", "C4", "25u", 101.6, 118)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# 4.7M feedback from the tone-stack output back to the V2A grid (≈0 V DC)
s.junction(91.44, 109)
s.wire(91.44, 109, 91.44, 84)
fl, fr = s.series_h("R", "RF1", "4.7M", 100, 84)
s.wire(91.44, 84, fl, 84)
s.wire(fr, 84, 156.21, 84)              # to the tone-stack output rail
# direct-coupled CF: grid from the plate stub tee
tee = 109 - 7.62 - 3.48
s.wire(101.6, tee, 108.9, tee)
s.junction(101.6, tee)
tcf = s.triode("V2B", "12AX7 CF", 116.84, 109)
s.wire(108.9, tee, 108.9, 109)
s.wire(108.9, 109, tcf["g"][0], 109)
s.wire(116.84, 101.38, 116.84, 98.5)
s.glabel("B+4", 116.84, 98.5, 90)      # CF plate straight to the rail
s.wire(116.84, 116.62, 116.84, 119.5)
s.junction(116.84, 119.5)
s.sym("R", "RKCF", "100k", 116.84, 123.31)
s.gnd(116.84, 127.12)

# ---- treble/bass tone stack (2-knob) ------------------------------------
s.wire(116.84, 119.5, 124.46, 119.5)
sl, sr = s.series_h("R", "RSL", "100k", 128.27, 119.5)
s.wire(sr, 119.5, 135.89, 119.5)
s.wire(135.89, 119.5, 135.89, 96)
# treble branch (250 pF cap + .01 across the treble pot)
s.junction(135.89, 108)
tl, tr = s.series_h("C", "C5", "250p", 139.7, 96)
s.wire(tr, 96, 147.32, 96)
s.sym("POT", "VR3", "1M treb", 147.32, 99.81)
s.sym("C", "C6", ".01u", 143.0, 91, lx=-4.0)
s.wire(143.0, 94.81, 143.0, 96)
s.junction(143.0, 96)
s.wire(143.0, 87.19, 147.32, 87.19)
s.wire(147.32, 87.19, 147.32, 96)
# bass branch (.005 cap + 1M bass pot)
bl, br = s.series_h("C", "C7", ".005u", 139.7, 108)
s.wire(br, 108, 147.32, 108)
s.wire(147.32, 103.62, 147.32, 108)     # treble pot bottom joins bass top
s.sym("POT", "VR4", "1M bass", 147.32, 111.81)
s.gnd(147.32, 115.62)
# treble wiper = stack output rail (x=156.21)
s.wire(152.4, 99.81, 156.21, 99.81)
s.wire(156.21, 99.81, 156.21, 84)
s.junction(156.21, 92)

# ---- long-tailed-pair phase inverter ------------------------------------
ol, orr = s.series_h("C", "C8", ".02u", 160.02, 92)
s.wire(orr, 92, 168.91, 92)
tp = s.triode("V3A", "12AX7", 176.53, 92)
s.wire(168.91, 92, tp["g"][0], 92)
bt = s.triode("V3B", "12AX7", 176.53, 126)
s.plate_load("RLA", "56k", tp["p"], "B+3")
s.plate_load("RLB", "100k", bt["p"], "B+3")
# shared tail: cathodes -> 1.5k -> J -> 56k -> gnd (elevated +55 V / +53 V)
s.wire(176.53, 99.62, 176.53, 102)
s.wire(176.53, 102, 182.88, 102)
s.wire(176.53, 133.62, 176.53, 136)
s.wire(176.53, 136, 182.88, 136)
s.wire(182.88, 102, 182.88, 136)
s.junction(182.88, 109)
s.sym("R", "RTAIL", "1.5k", 187.96, 109 + 3.81, lx=2.0)
s.wire(182.88, 109, 187.96, 109)
s.junction(187.96, 116.62)
s.sym("R", "RT2", "56k", 187.96, 120.43)
s.gnd(187.96, 124.24)
# both grid leaks to the junction
s.wire(168.91, 92, 168.91, 99)
s.junction(168.91, 92)
s.sym("R", "RGA", "1M", 168.91, 102.81, lx=-9.4)
s.wire(168.91, 106.62, 168.91, 116.62)
s.wire(168.91, 116.62, 187.96, 116.62)
s.wire(168.91, 126, 168.91, 122)        # bottom grid
s.wire(168.91, 126, bt["g"][0], 126)
s.junction(168.91, 126)
s.sym("R", "RGB", "1M", 168.91, 118.19, lx=-9.4)
s.text("56k NFB + 5k presence join the tail at ~0 V DC (annotation)", 150, 145, 1.1)

# ---- 6L6G pair, fixed bias ----------------------------------------------
for y, pref, cref, glref in [(84, "V4", "C9", "RGL1"), (136, "V5", "C10", "RGL2")]:
    if y == 84:
        s.wire(176.53, 80.9, 194.31, 80.9)
        s.junction(176.53, 80.9)
        cl, crr = s.series_h("C", cref, ".1u", 198.12, 80.9)
        s.wire(crr, 80.9, 205.74, 80.9)
        s.wire(205.74, 80.9, 205.74, 84)
        gy = 84
        gstop = "R5s"
    else:
        s.wire(176.53, 114.9, 191.77, 114.9)   # lower PI plate tee
        s.junction(176.53, 114.9)
        cl, crr = s.series_h("C", cref, ".1u", 195.58, 114.9)
        s.wire(crr, 114.9, 205.74, 114.9)
        s.wire(205.74, 114.9, 205.74, 136)
        gy = 136
        gstop = "R6s"
    # grid stopper 1.5k in series, then 220k grid leak to -40V
    s.wire(205.74, gy, 208.28, gy)
    gl2, gr2 = s.series_h("R", gstop, "1.5k", 212.09, gy)
    p = s.pentode(pref, "6L6G", 221.6, gy)
    s.wire(gr2, gy, p["g1"][0], gy)
    s.junction(208.28, gy)
    s.sym("R", glref, "220k", 208.28, gy + 3.81)
    s.wire(208.28, gy + 7.62, 208.28, gy + 10.16)
    s.glabel("-40V", 208.28, gy + 10.16, 270)
    # screen straight to B+2 (no screen resistor on the C-EG drawing)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(221.6, p["k"][1] + 0)

# ---- output transformer -------------------------------------------------
s.sym("OT_PP", "T3", "45216", 249.5, 110)
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
s.text("Power — PT 8087, 5U4G, choke 14684 · bias: 6.8k/56k + selenium rect -> -40V", 25, 158, 1.4)
for x, ref, ht in [(41.91, "V6A", "HT_A"), (54.61, "V6B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5U4G", x, 167.78, lx=(-11.4 if ref == "V6A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(41.91, 177.8, 82.55, 177.8)
s.junction(54.61, 177.8)
s.junction(66.04, 177.8)
s.sym("C", "C11", "16u", 66.04, 181.61)
s.gnd(66.04, 185.42)
s.glabel("B+1", 82.55, 177.8, 0)
s.wire(82.55, 177.8, 85.09, 177.8)
s.sym("CHOKE", "L1", "14684", 92.71, 177.8, lx=-4.0, ly=-6.4)
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
s.glabel("HT_B", 150.1, 172.72, 180)
s.wire(150.1, 172.72, 153.91, 172.72)
s.sym("DIODE_SS", "D1", "SEL", 158.99, 172.72, lx=-2.0, ly=-5.4)
s.wire(164.07, 172.72, 167.88, 172.72)
l, r = s.series_h("R", "RB1", "6.8k", 171.69, 172.72)
s.wire(167.88, 172.72, l, 172.72)
s.wire(r, 172.72, 183.12, 172.72)
s.junction(178.04, 172.72)
s.sym("R", "RB2", "56k", 178.04, 176.53)
s.gnd(178.04, 180.34)
s.junction(180.58, 172.72)
s.sym("C", "C15", "8u", 180.58, 176.53, lx=2.2)
s.gnd(180.58, 180.34)
s.glabel("-40V", 183.12, 172.72, 0)

s.write(OUT, [
    ("5F4 — Tweed Super-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 25, 66, 2.0),
    ("Heaters, PT primary and standby omitted — see netlist.cir and meta.yaml", 25, 70.5, 1.3),
])
print(f"wrote {OUT}")
