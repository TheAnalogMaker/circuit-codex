#!/usr/bin/env python3
"""Generate amps/5f6/schematic.kicad_sch from the stage-template library.

Values per the published 5F6 (F-EG) drawing (see amps/5f6/meta.yaml). The 5F6
differs from its 5F6-A revision in four places, all drawn here: the 83
mercury-vapour rectifier, the 5 kΩ presence control sitting in the tone stack's
ground leg (with the 27 kΩ feedback resistor landing on that same junction and a
0.1 µF cap from the presence wiper to ground), the 1.5 kΩ output grid stoppers,
and 100 Ω screen resistors.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f6" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, bright + normal channels, shared 820R/250u cathode -------
for ch, (y, jack, sref, gref, pref, plref, cref, vref, mref) in enumerate([
        (92, "BRIGHT", "R1s", "RG1", "V1A", "RL1", "C1", "VR1", "RM1"),
        (126, "NORMAL", "R2s", "RG2", "V1B", "RL2", "C2", "VR2", "RM2")]):
    s.glabel(jack, 26, y, 180)
    s.wire(26, y, 30.48, y)
    l, r = s.series_h("R", sref, "68k", 34.29, y)
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
s.text("100 pF bright cap across VR1 omitted (AC only) · each channel's second jack adds another 68 kΩ stopper", 40, 76, 1.1)

# shared cathode
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C3", "250u", 56.13, 140)

# ---- V2A + DC-coupled cathode follower ---------------------------------
t2a = s.triode("V2A", "12AX7", 101.6, 109)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 119)
s.sym("R", "RK2", "820", 101.6, 122.81)
s.sym("C", "C4", "25u", 109.22, 122.81)
s.wire(101.6, 119, 109.22, 119)
s.wire(101.6, 126.62, 109.22, 126.62)
s.gnd(101.6, 126.62)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
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

# ---- TMB tone stack, presence in the ground leg -------------------------
# Wired as the published 5F6 (F-EG) schematic draws it — NOT the later
# "canonical FMV" idealisation:
#   node A = cathode-follower output: 250 pF to the treble pot AND the 56k slope;
#   node B = the slope's foot: one 0.02 uF to the treble-bottom/bass node, the
#            other 0.02 uF to the MIDDLE POT'S WIPER;
#   the bass pot is a rheostat (wiper strapped to its hot lug) in series down
#   the ladder, and the stack's output is the TREBLE WIPER ALONE.
# The factory 5F6 layout sheet wires the pots the same way (bass wiper strapped,
# middle wiper fed by the second 0.02 uF, treble wiper out).
s.wire(116.84, 119.5, 124.46, 119.5)
s.junction(124.46, 119.5)
s.wire(124.46, 119.5, 124.46, 94)      # node A up to the 250 pF branch
s.wire(124.46, 94, 140.19, 94)
sl, sr = s.series_h("R", "RSL", "56k", 128.27, 119.5)
s.wire(sr, 119.5, 137, 119.5)
tl, tr = s.series_h("C", "C5", "250p", 144, 94)
s.wire(tr, 94, 152.4, 94)
s.sym("POT", "VR3", "250k treb", 152.4, 97.81)
# node B -> 0.02 uF to the treble-bottom/bass node, 0.02 uF to the mid wiper
s.junction(137, 119.5)
s.wire(137, 119.5, 137, 106)
bl, br = s.series_h("C", "C6", ".02u", 144, 106)
s.wire(137, 106, bl, 106)
s.wire(br, 106, 152.4, 106)
s.wire(137, 119.5, 137, 143)
b2l, b2r = s.series_h("C", "C7", ".02u", 144, 143)
s.wire(137, 143, b2l, 143)
s.wire(b2r, 143, 161, 143)
s.wire(161, 143, 161, 121.81)
s.wire(161, 121.81, 157.48, 121.81)    # -> middle wiper
# the stack column: treble -> bass -> middle -> presence -> ground
s.wire(152.4, 101.62, 152.4, 106)      # treble bottom lug -> bass node
s.sym("POT", "VR4", "1M bass", 152.4, 109.81)
s.wire(157.48, 109.81, 166, 109.81)    # bass wiper strapped to its hot lug (rheostat)
s.wire(166, 109.81, 166, 106)
s.wire(166, 106, 152.4, 106)
s.junction(152.4, 106)
s.wire(152.4, 113.62, 152.4, 118)
s.sym("POT", "VR5", "25k mid", 152.4, 121.81)
s.wire(152.4, 125.62, 152.4, 130)
s.junction(152.4, 128)
s.sym("POT", "VR6", "5k pres", 152.4, 133.81)
s.gnd(152.4, 137.62)
s.wire(157.48, 133.81, 163, 133.81)    # presence wiper -> 0.1 uF -> ground
s.sym("C", "C13", ".1u", 163, 137.62)
s.gnd(163, 141.43)
# 27k negative feedback: speaker node -> the middle/presence junction
s.wire(152.4, 128, 146, 128)
s.wire(146, 128, 146, 152)
nl, nr = s.series_h("R", "RNF", "27k", 152, 152)
s.wire(146, 152, nl, 152)
s.wire(nr, 152, 160, 152)
s.glabel("SPKR", 160, 152, 0)
# treble wiper = stack output
s.wire(157.48, 97.81, 157.48, 92)

# ---- long-tailed-pair phase inverter ------------------------------------
ol, orr = s.series_h("C", "C10", ".02u", 162, 92)
s.wire(157.48, 92, ol, 92)
s.wire(orr, 92, 168.91, 92)
tp = s.triode("V3A", "12AX7", 176.53, 92)
s.wire(168.91, 92, tp["g"][0], 92)
bt = s.triode("V3B", "12AX7", 176.53, 126)
s.plate_load("RLA", "82k 5%", tp["p"], "B+3")
s.plate_load("RLB", "100k 5%", bt["p"], "B+3")
# shared tail: cathodes -> 470 -> J -> 10k -> gnd
s.wire(176.53, 99.62, 176.53, 102)
s.wire(176.53, 102, 182.88, 102)
s.wire(176.53, 133.62, 176.53, 136)
s.wire(176.53, 136, 182.88, 136)
s.wire(182.88, 102, 182.88, 136)
s.junction(182.88, 109)
s.sym("R", "RTAIL", "470", 187.96, 109 + 3.81, lx=2.0)
s.wire(182.88, 109, 187.96, 109)
s.junction(187.96, 116.62)
s.sym("R", "RT2", "10k", 187.96, 120.43)
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
bl2, br2 = s.series_h("C", "C11", ".1u", 162.56, 126)
s.wire(br2, 126, 168.91, 126)
s.wire(bl2, 126, 156.5, 126)
s.wire(156.5, 126, 156.5, 131)
s.gnd(156.5, 131)                       # V3B grid AC-grounded (0.1 uF, 200 V)
# 47 pF across the two plates
s.junction(190, 80.9)
s.wire(190, 80.9, 190, 93)
s.sym("C", "C12", "47p", 190, 96.81)
s.wire(190, 100.62, 190, 114.9)
s.junction(190, 114.9)

# ---- 5881 pair, fixed bias ----------------------------------------------
for y, pref, cref, glref, gsref, sref in [(84, "V4", "C8", "RGL1", "RGS1", "RS1"),
                                          (136, "V5", "C9", "RGL2", "RGS2", "RS2")]:
    if y == 84:
        s.wire(176.53, 80.9, 194.31, 80.9)
        s.junction(176.53, 80.9)
        cl, crr = s.series_h("C", cref, ".1u", 198.12, 80.9)
        s.wire(crr, 80.9, 205.74, 80.9)
        s.wire(205.74, 80.9, 205.74, 84)
        gy = 84
    else:
        s.wire(176.53, 114.9, 191.77, 114.9)   # lower PI plate tee (above V)
        s.junction(176.53, 114.9)
        cl, crr = s.series_h("C", cref, ".1u", 195.58, 114.9)
        s.wire(crr, 114.9, 205.74, 114.9)
        s.wire(205.74, 114.9, 205.74, 136)
        gy = 136
    p = s.pentode(pref, "5881", 224, gy)
    s.junction(205.74, gy)
    gl2, gr2 = s.series_h("R", gsref, "1.5k", 211, gy)
    s.wire(205.74, gy, gl2, gy)
    s.wire(gr2, gy, p["g1"][0], gy)
    s.sym("R", glref, "220k", 205.74, gy + 3.81)
    s.wire(205.74, gy + 7.62, 205.74, gy + 10.16)
    s.glabel("-48V", 205.74, gy + 10.16, 270)
    # screen resistor to B+2
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 1.9, p["g2"][1])
    sl2, sr2 = s.series_h("R", sref, "100", p["g2"][0] + 5.71, p["g2"][1])
    s.wire(sr2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 11.5, p["g2"][1], 0)
    s.gnd(224, p["k"][1] + 0)

# ---- output transformer -------------------------------------------------
s.sym("OT_PP", "T3", "2R sec", 252, 110)
s.wire(224, 84 - 0.635 - 7.62, 224, 73.5)
s.wire(224, 73.5, 243.11, 73.5)
s.wire(243.11, 73.5, 243.11, 104.92)
s.wire(224, 136 - 0.635 - 7.62, 224, 126.5)
s.wire(224, 126.5, 238, 126.5)
s.wire(238, 126.5, 238, 115.08)
s.wire(238, 115.08, 243.11, 115.08)
s.wire(243.11, 110, 240.57, 110)
s.wire(240.57, 110, 240.57, 107)
s.glabel("B+1", 240.57, 107, 90)
s.wire(260.89, 107.46, 263.43, 107.46)
s.glabel("SPKR", 263.43, 107.46, 0)
s.wire(260.89, 112.54, 263.43, 112.54)
s.glabel("GND", 263.43, 112.54, 0)

# ---- power supply + bias ------------------------------------------------
s.text("Power — 325-0-325 (PT 8087), 83 mercury-vapour rectifier, choke 14684 · bias: selenium rect, 15k/56k, 8 µF/150 V pair -> -48 V", 25, 158, 1.4)
for x, ref, ht in [(41.91, "V6A", "HT_A"), (54.61, "V6B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "83", x, 167.78, lx=(-11.4 if ref == "V6A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(41.91, 177.8, 85.09, 177.8)
s.junction(54.61, 177.8)
s.junction(66.04, 177.8)
s.sym("C", "C14", "20u", 66.04, 181.61)
s.gnd(66.04, 185.42)
s.junction(74.93, 177.8)
s.sym("C", "C15", "20u", 74.93, 181.61)
s.gnd(74.93, 185.42)
s.junction(82.55, 177.8)
s.glabel("B+1", 82.55, 175.26, 90)
s.wire(82.55, 175.26, 82.55, 177.8)
s.sym("CHOKE", "L1", "14684", 92.71, 177.8, lx=-4.0, ly=-6.4)
s.wire(100.33, 177.8, 111.76, 177.8)
s.junction(105.41, 177.8)
s.glabel("B+2", 105.41, 175.26, 90)
s.wire(105.41, 175.26, 105.41, 177.8)
s.junction(108.86, 177.8)
s.sym("C", "C16", "20u", 108.86, 181.61)
s.gnd(108.86, 185.42)
l, r = s.series_h("R", "RD1", "4.7k 1W", 115.57, 177.8)
s.wire(r, 177.8, 127, 177.8)
s.junction(121.92, 177.8)
s.glabel("B+3", 121.92, 175.26, 90)
s.wire(121.92, 175.26, 121.92, 177.8)
s.junction(124.46, 177.8)
s.sym("C", "C17", "20u", 124.46, 181.61)
s.gnd(124.46, 185.42)
l, r = s.series_h("R", "RD2", "10k 1W", 130.81, 177.8)
s.wire(r, 177.8, 142.24, 177.8)
s.junction(137.16, 177.8)
s.glabel("B+4", 137.16, 175.26, 90)
s.wire(137.16, 175.26, 137.16, 177.8)
s.sym("C", "C18", "8u", 142.24, 181.61)
s.gnd(142.24, 185.42)
# bias supply: HT tap -> selenium rect -> 8 uF -> 15k -> -48 V, 56k bleeder
s.glabel("HT_B", 152, 172.72, 180)
s.wire(152, 172.72, 155.81, 172.72)
s.sym("DIODE_SS", "D1", "SEL", 160.89, 172.72, lx=-2.0, ly=-5.4)
s.wire(165.97, 172.72, 169.78, 172.72)
s.junction(169.78, 172.72)
s.sym("C", "C19", "8u", 169.78, 176.53, lx=-6.2)
s.gnd(169.78, 180.34)
l, r = s.series_h("R", "RB1", "15k", 176.53, 172.72)
s.wire(169.78, 172.72, l, 172.72)
s.wire(r, 172.72, 194, 172.72)
s.junction(184.15, 172.72)
s.sym("R", "RB2", "56k", 184.15, 176.53)
s.gnd(184.15, 180.34)
s.junction(189.23, 172.72)
s.sym("C", "C20", "8u", 189.23, 176.53, lx=2.2)
s.gnd(189.23, 180.34)
s.glabel("-48V", 194, 172.72, 0)

s.write(OUT, [
    ("5F6 — Tweed Bassman-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 25, 66, 2.0),
    ("Heaters, PT primary and standby omitted — see netlist.cir and meta.yaml", 25, 70.5, 1.3),
])
print(f"wrote {OUT}")
