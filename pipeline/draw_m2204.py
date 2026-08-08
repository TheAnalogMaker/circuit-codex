#!/usr/bin/env python3
"""Generate amps/m2204/schematic.kicad_sch from the stage-template library.

Values per the published Marshall model 2204 STD factory drawing, both sheets
(2204PRE.DGM iss 4, 19-5-88 and 2204PWR.DGM iss 2, 18-6-89) — see
amps/m2204/meta.yaml. The 2204 is the model 1987 rewired: the two input triodes
that used to sit side by side as separate channels run in SERIES — V1a into a
preamp volume into V1b — and the second channel's volume control becomes a
MASTER VOLUME between the tone stack and the phase inverter.

Valve numbering follows the drawing: V1 input stage + cascaded second stage,
V2 third gain stage + DC-coupled cathode follower, V3 long-tailed-pair phase
inverter, V4/V5 the EL34 output pair.

Rails follow netlist.cir: B+1 reservoir (the output-transformer centre tap is
taken AHEAD of the choke, so the EL34 plates sit here), B+2 the post-choke
screen node, B+3 the drawing's rail 'X' (phase-inverter plates, V2), B+4 the
input-stage rail behind R8 (V1a and V1b plate loads).

The 6.3 V heater winding, its earthed centre tap and the undesignated mains
indicator lamp are annotations here, not drawn — see netlist.cir and the note
blocks below.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "m2204" / "schematic.kicad_sch"
s = Sch()

# ============================ V1a — input stage =============================
# J1 'High' -> R2 1M leak at the jack -> R3 68k stopper -> V1a grid.
# R4 100k plate load to the input rail; R1 2.7k cathode bypassed by C1 0.68 uF;
# C2 100 pF straight across the triode, plate to cathode.
j1 = s.jack("J1", "1/4 in", 24, 72.54, mirror=True)
s.text("High", 18, 68, 1.3)
s.wire(j1["tip"][0], 70, 40, 70)
s.junction(40, 70)
s.sym("R", "R2", "1M", 40, 73.81, lx=-9.4)
s.gnd(40, 77.62)
s.wire(j1["sleeve"][0], 75.08, 33, 75.08)
s.wire(33, 75.08, 33, 79)
s.gnd(33, 79)
hl, hr = s.series_h("R", "R3", "68k", 47, 70)
s.wire(40, 70, hl, 70)

t1a = s.triode("V1A", "ECC83", 62, 70)
s.wire(hr, 70, t1a["g"][0], 70)
s.plate_load("R4", "100k", t1a["p"], "B+4", gap=3.81)
# cathode: R1 2.7k with C1 0.68 uF across it
s.wire(62, 77.62, 62, 84)
s.wire(62, 84, 68, 84)
s.junction(68, 84)
s.wire(68, 84, 74, 84)
s.shunt_rc("R1", "2.7k", "C1", ".68u", 74, 84)
# C2 100 pF across the triode: plate stub down to the cathode line
s.wire(62, 58.57, 68, 58.57)
s.junction(62, 58.57)
s.sym("C", "C2", "100p", 68, 62.38, lx=2.4)
s.wire(68, 66.19, 68, 84)

# ================= preamp-volume network -> the cascaded V1b ================
# V1a plate -> C3 0.022 uF -> the 470k/470pF peaking arm (R5 ‖ C4) -> VR1 1M log
# preamp volume, with C5 1n0 bridging the pot's upper section; the wiper drives
# V1b.  The 'Low' jack J2 lands on the network's own input node: the drawing
# wires its normalling contact to the coupler, so with nothing in the Low jack
# the two are joined and the stage runs normally, and a plug substitutes the
# guitar for the coupler.
s.wire(68, 58.57, 74.19, 58.57)
cl, cr = s.series_h("C", "C3", ".022u", 78, 58.57)
s.wire(cr, 58.57, 89, 58.57)
s.junction(89, 58.57)
s.sym("C", "C4", "470p", 89, 62.38, lx=-8.0)
s.wire(89, 58.57, 96, 58.57)
s.junction(96, 58.57)
s.sym("R", "R5", "470k", 96, 62.38, lx=2.4)
s.wire(89, 66.19, 96, 66.19)
s.junction(96, 66.19)
s.sym("POT", "VR1", "1M preamp vol", 96, 70, lx=-24.0, ly=6.2)
s.gnd(96, 73.81)
# C5 1n0 across the pot's upper section: top lug over to the wiper
s.wire(96, 66.19, 104, 66.19)
s.wire(104, 66.19, 104, 63)
c5l, c5r = s.series_h("C", "C5", "1n0", 110, 63)
s.wire(104, 63, c5l, 63)
s.wire(c5r, 63, 116, 63)
s.wire(116, 63, 116, 70)
s.junction(116, 70)
s.wire(101.08, 70, 116, 70)

# J2 'Low' feeds that same node
j2 = s.jack("J2", "1/4 in", 86, 46, mirror=True)
s.text("Low", 80, 41.5, 1.3)
s.wire(j2["tip"][0], 43.46, 96, 43.46)
s.wire(96, 43.46, 96, 58.57)
s.wire(j2["sleeve"][0], 48.54, 91.08, 52)
s.gnd(91.08, 52)

t1b = s.triode("V1B", "ECC83", 126, 70)
s.wire(116, 70, t1b["g"][0], 70)
s.plate_load("R7", "100k", t1b["p"], "B+4", gap=3.81)
# cold, deliberately UNBYPASSED 10k cathode — the gain-shaping stage the 2204
# adds over the 1987
s.wire(126, 77.62, 126, 84)
s.sym("R", "R6", "10k", 126, 87.81)
s.gnd(126, 91.62)

# ================ interstage divider -> V2a third gain stage ================
s.wire(126, 58.57, 134.19, 58.57)
s.junction(126, 58.57)
c7l, c7r = s.series_h("C", "C7", ".022u", 138, 58.57)
s.wire(c7r, 58.57, 145, 58.57)
s.junction(145, 58.57)
s.sym("C", "C8", "470p", 145, 62.38, lx=-8.0)
s.wire(145, 58.57, 152, 58.57)
s.junction(152, 58.57)
s.sym("R", "R10", "470k", 152, 62.38, lx=2.4)
s.wire(145, 66.19, 152, 66.19)
s.junction(152, 66.19)
s.sym("R", "R11", "470k", 152, 70, lx=2.4)
s.gnd(152, 73.81)
s.wire(152, 66.19, 158, 66.19)
s.wire(158, 66.19, 158, 70)

t2a = s.triode("V2A", "ECC83", 168, 70)
s.wire(158, 70, t2a["g"][0], 70)
s.plate_load("R12", "100k", t2a["p"], "B+3", gap=3.81)
s.wire(168, 77.62, 168, 84)
s.sym("R", "R9", "820", 168, 87.81)
s.gnd(168, 91.62)

# ================== V2b DC-coupled cathode follower =========================
s.wire(168, 58.57, 176, 58.57)
s.junction(168, 58.57)
s.wire(176, 58.57, 176, 70)
t2b = s.triode("V2B", "ECC83 CF", 188, 70)
s.wire(176, 70, t2b["g"][0], 70)
s.wire(188, 62.38, 188, 57)
s.glabel("B+3", 188, 57, 90)
CFY = 80.5
s.wire(188, 77.62, 188, CFY)
s.junction(188, CFY)
s.sym("R", "R13", "100k", 188, CFY + 3.81)
s.gnd(188, CFY + 7.62)

# ======================= TMB tone stack (cathode-follower fed) ==============
# Wired as the 2204 STD sheet draws it — the same ladder as the 1987, the JTM45
# and the 5F6-A before them:
#   node A = follower output: C10 470 pF to the treble pot AND the R15 33k slope
#   node B = the slope's foot: C11 0.022 uF to the treble-bottom/bass node and
#            C12 0.022 uF to the MIDDLE POT'S WIPER
#   the bass pot is a rheostat (wiper strapped to its hot lug) in the ladder and
#   the stack's output is the TREBLE WIPER ALONE, taken to the master volume
#   through the panel link the drawing labels 'R14'.
s.wire(188, CFY, 196, CFY)
sl, sr = s.series_h("R", "R15", "33k", 200, CFY)
s.wire(196, CFY, sl, CFY)
s.junction(196, CFY)
s.wire(196, CFY, 196, 62)                 # node A riser, up to the treble cap
s.wire(sr, CFY, 208, CFY)
s.junction(208, CFY)
s.wire(208, CFY, 208, 76)                 # node B riser, up to the bass cap
s.wire(208, CFY, 208, 102)                # node B riser, down to the mid cap
tl, tr = s.series_h("C", "C10", "470p", 214, 62)
s.wire(196, 62, tl, 62)
s.wire(tr, 62, 222, 62)
s.sym("POT", "VR3", "220k treble", 222, 65.81, lx=6.0, ly=-5.6)
bl, br = s.series_h("C", "C11", ".022u", 214, 76)
s.wire(208, 76, bl, 76)
s.wire(br, 76, 222, 76)
s.wire(222, 69.62, 222, 76)               # treble bottom lug -> bass node
s.junction(222, 76)
s.sym("POT", "VR5", "1M bass", 222, 79.81, lx=6.0, ly=-5.6)
s.wire(227.08, 79.81, 232, 79.81)         # bass wiper strapped to its hot lug
s.wire(232, 79.81, 232, 76)
s.wire(232, 76, 222, 76)
ml, mr = s.series_h("C", "C12", ".022u", 214, 102)
s.wire(208, 102, ml, 102)
s.wire(mr, 102, 230, 102)
s.wire(230, 102, 230, 91.43)
s.wire(230, 91.43, 227.08, 91.43)         # -> the middle pot's wiper
s.wire(222, 83.62, 222, 87.62)            # bass foot -> middle top
s.sym("POT", "VR4", "22k middle", 222, 91.43, lx=6.0, ly=-5.6)
s.gnd(222, 95.24)
# treble wiper -> the panel link 'R14' -> master volume -> the power sheet
s.wire(227.08, 65.81, 234, 65.81)
r14l, r14r = s.series_h("R", "R14", "link", 240, 65.81)
s.wire(234, 65.81, r14l, 65.81)
s.wire(r14r, 65.81, 250, 65.81)
s.sym("POT", "VR2", "1M master vol", 250, 69.62, lx=6.0, ly=-5.6)
s.gnd(250, 73.43)
s.wire(255.08, 69.62, 264, 69.62)
s.glabel("Y", 264, 69.62, 0)

s.text("J2 'Low' lands on the preamp-volume network's own input node: the "
       "drawing wires the coupler C3 to that jack's normalling contact, so with "
       "nothing plugged into Low", 18, 108, 1.25)
s.text("the two are joined and the cascaded front end runs normally, and a plug "
       "in Low substitutes the guitar for V1a's output. 'X', 'Y' and 'Z' are the "
       "sheets' own interconnections.", 18, 112, 1.25)

# ===================== V3 long-tailed-pair phase inverter ===================
GL = 52.38          # grid column (= the triode grid pin x)
JY = 210.0          # tail-junction lane, clear below both bottles
NF = 224.0          # negative-feedback node lane
s.glabel("Y", 24, 150, 180)
s.wire(24, 150, 34.19, 150)
c9l, c9r = s.series_h("C", "C9", ".022u", 38, 150)
s.wire(c9r, 150, GL, 150)
t3a = s.triode("V3A", "ECC83", 60, 150)
t3b = s.triode("V3B", "ECC83", 60, 186)
s.plate_load("R18", "82k", t3a["p"], "B+3")      # the driven side
s.plate_load("R21", "100k", t3b["p"], "B+3")
# shared cathode -> R16 470 -> tail junction
s.wire(60, 157.62, 60, 160)
s.wire(60, 160, 68, 160)
s.wire(60, 193.62, 60, 196)
s.wire(60, 196, 68, 196)
s.wire(68, 160, 68, 196)
s.junction(68, 178)
r16l, r16r = s.series_h("R", "R16", "470", 76, 178)
s.wire(68, 178, r16l, 178)
s.wire(r16r, 178, 86, 178)
s.wire(86, 178, 86, JY)
# both 1M grid leaks return to the tail junction
s.wire(GL, 150, GL, 154)
s.junction(GL, 150)
s.sym("R", "R17", "1M", GL, 157.81, lx=-9.4)
s.wire(GL, 161.62, GL, 166)
s.wire(GL, 166, 40, 166)
s.wire(40, 166, 40, JY)
s.junction(GL, 186)
s.wire(GL, 186, GL, 190)
s.sym("R", "R19", "1M", GL, 193.81, lx=-9.4)
s.wire(GL, 197.62, GL, JY)
s.wire(40, JY, GL, JY)
s.wire(GL, JY, 86, JY)
s.junction(GL, JY)
# R20 10k tail, from the junction down to the feedback node
s.sym("R", "R20", "10k", 40, JY + 3.81, lx=-9.4)
s.wire(40, JY + 7.62, 40, NF)
# C15 0.1 uF AC-grounds the inverter's cold grid to that same node
s.wire(46, 186, GL, 186)
s.wire(46, 186, 46, NF - 7.81)
s.sym("C", "C15", ".1u", 46, NF - 4.0, lx=-6.4, ly=-1.0)
s.wire(46, NF - 0.19, 46, NF)

# ---- feedback node: R23 to ground, presence leg, R22 back from the speaker ---
s.wire(20, NF, 84.19, NF)
s.junction(40, NF)
s.junction(46, NF)
s.sym("R", "R23", "4k7", 20, NF + 3.81, lx=-9.4)
s.gnd(20, NF + 7.62)
s.junction(32, NF)
s.sym("C", "C17", ".1u", 32, NF + 3.81, lx=2.4)
s.sym("POT", "VR6", "22k presence", 32, NF + 11.43, lx=6.0, ly=-5.6)
s.wire(37.08, NF + 11.43, 42, NF + 11.43)      # wiper strapped to the foot
s.wire(42, NF + 11.43, 42, NF + 15.24)
s.wire(42, NF + 15.24, 32, NF + 15.24)
s.junction(32, NF + 15.24)
s.gnd(32, NF + 15.24)
r22l, r22r = s.series_h("R", "R22", "100k", 88, NF)
s.wire(r22r, NF, 96, NF)
s.glabel("SPKR", 96, NF, 0)

# ======================= EL34 pair, fixed bias ==============================
# Each inverter plate drives a 0.022 uF coupler onto a grid node; C18 47 pF
# bridges the two grid nodes ahead of the 5.6k stoppers, and R24/R25 220k in
# series between them meet at the bias line.
s.wire(60, 138.9, 72, 138.9)
s.junction(60, 138.9)
c14l, c14r = s.series_h("C", "C14", ".022u", 78, 138.9)
s.wire(72, 138.9, c14l, 138.9)
s.wire(c14r, 138.9, 96, 138.9)
s.wire(60, 174.9, 72, 174.9)
s.junction(60, 174.9)
c16l, c16r = s.series_h("C", "C16", ".022u", 78, 174.9)
s.wire(72, 174.9, c16l, 174.9)
s.wire(c16r, 174.9, 96, 174.9)
# C18 47p across the two grid nodes
s.junction(96, 138.9)
s.junction(96, 174.9)
s.wire(96, 138.9, 96, 153.09)
s.sym("C", "C18", "47p", 96, 156.9, lx=-7.4)
s.wire(96, 160.71, 96, 174.9)
# R24 / R25 220k grid leaks off the shared bias node
s.wire(96, 138.9, 106, 138.9)
s.sym("R", "R24", "220k", 106, 142.71, lx=2.4)
s.wire(106, 146.52, 106, 152)
s.junction(106, 152)
s.sym("R", "R25", "220k", 106, 155.81, lx=2.4)
s.wire(106, 159.62, 106, 174.9)
s.wire(96, 174.9, 106, 174.9)
s.wire(106, 152, 118, 152)
s.glabel("-BIAS", 118, 152, 0)
# grid stoppers into the valves
s.junction(106, 138.9)
s.junction(106, 174.9)
for gy, stref, vref, scref in [(138.9, "R31", "V4", "R33"),
                               (174.9, "R32", "V5", "R34")]:
    stl, str_ = s.series_h("R", stref, "5.6k", 118, gy)
    s.wire(106, gy, stl, gy)
    p = s.pentode(vref, "EL34", 150, gy, lx=-15.0, ly=4.4)
    s.wire(str_, gy, p["g1"][0], gy)
    # 1.5k screen resistor from the post-choke rail
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 1.9, p["g2"][1])
    scl, scr = s.series_h("R", scref, "1.5k", p["g2"][0] + 5.71, p["g2"][1])
    s.wire(scr, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 11.5, p["g2"][1], 0)
    s.gnd(150, p["k"][1])                       # cathodes grounded — fixed bias

# ---- output transformer, impedance selector, speaker and DI jacks ----------
s.sym("OT_PP", "T2", "789-139", 210, 157, lx=-6.35, ly=-14.0)
s.wire(150, 130.645, 150, 126)
s.wire(150, 126, 194, 126)
s.wire(194, 126, 194, 151.92)
s.wire(194, 151.92, 201.11, 151.92)
s.wire(150, 166.645, 150, 162.08)
s.wire(150, 162.08, 201.11, 162.08)
s.wire(201.11, 157, 199, 157)
s.glabel("B+1", 199, 157, 180)
s.wire(218.89, 159.54, 224, 159.54)
s.wire(224, 159.54, 224, 165)
s.gnd(224, 165)
s.wire(218.89, 154.46, 230, 154.46)
s.junction(230, 154.46)
s.wire(230, 154.46, 230, 148)
s.glabel("SPKR", 230, 148, 90)
sel_l, sel_r = s.switch("SEL2", "16/8/4", 240, 154.46, lx=-4.6, ly=-6.4)
s.wire(230, 154.46, sel_l, 154.46)
s.wire(sel_r, 154.46, 252, 154.46)
s.junction(252, 154.46)
s.wire(252, 154.46, 252, 172)
for jref, jy in [("J3", 154.46), ("J4", 172.0)]:
    j = s.jack(jref, "1/4 in", 264, jy + 2.54)
    s.wire(252, jy, j["tip"][0], jy)
    s.wire(j["sleeve"][0], jy + 5.08, 256, jy + 5.08)
    s.wire(256, jy + 5.08, 256, jy + 9)
    s.gnd(256, jy + 9)
s.text("Speakers", 262, 184, 1.3)
# DI network off the secondary
s.junction(230, 154.46)
s.wire(230, 154.46, 230, 186)
s.sym("R", "R35", "2k2", 230, 189.81, lx=2.4)
s.wire(230, 193.62, 230, 198)
s.junction(230, 198)
s.sym("R", "R36", "100", 230, 201.81, lx=2.4)
s.gnd(230, 205.62)
r37l, r37r = s.series_h("R", "R37", "560", 240, 198)
s.wire(230, 198, r37l, 198)
j5 = s.jack("J5", "1/4 in", 258, 200.54, mirror=True)
s.wire(r37r, 198, j5["tip"][0], 198)
s.wire(j5["sleeve"][0], 203.08, 266, 203.08)
s.wire(266, 203.08, 266, 207)
s.gnd(266, 207)
s.text("D.I.", 254, 210, 1.3)

# ======================= power supply and mains =============================
s.note('Power — 1202-324 mains transformer with 240 / 220 / 120 V primary selection; centre-tapped HT winding through the standby switch into two series 1N4007 pairs; 50+50 uF reservoir,')
s.text("HT fuse, and the output transformer's centre tap taken AHEAD of the "
       "choke — so only the screens and the preamp are fed through it. R29 and "
       "R8 then step the rail down twice.", 18, 244, 1.4)

ms1 = s.conn3("MS1", "N/E/L", 30, 272)
s.text("N   E   L", 22.5, 279, 1.2)
s.wire(ms1["2"][0], 266.92, 30, 262)
s.gnd(30, 262)
s.wire(ms1["3"][0], 266.92, 33.81, 258)
s.wire(33.81, 258, 38, 258)
f1l, f1r = s.fuse("F1", "T2A", 44, 258)
s.wire(38, 258, f1l, 258)
s1l, s1r = s.switch("S1", "DPST", 58, 258)
s.wire(f1r, 258, s1l, 258)
sel1l, sel1r = s.switch("SEL1", "240/220/120", 76, 258, lx=-9.0, ly=-6.4)
s.wire(s1r, 258, sel1l, 258)
t1 = s.pt("T1", "1202-324", 100, 262)
s.wire(sel1r, 258, 86, 258)
s.wire(86, 258, 86, 256.92)
s.wire(86, 256.92, t1["pri1"][0], 256.92)
s.wire(ms1["1"][0], 266.92, 20, 266.92)
s.wire(20, 266.92, 20, 250)
s.wire(20, 250, 90, 250)
s.wire(90, 250, 90, 267.08)
s.wire(90, 267.08, t1["pri2"][0], 267.08)

# HT winding: centre tap earthed, both legs switched by the standby, each leg
# rectified by a series pair of 1N4007s
s.wire(t1["ht_ct"][0], 262, 112, 262)
s.gnd(112, 262)
s.wire(t1["ht_a"][0], 256.92, 114, 256.92)
s2l, s2r = s.switch("S2", "standby", 120, 256.92, lx=-4.6, ly=-6.4)
s.wire(114, 256.92, s2l, 256.92)
s.wire(s2r, 256.92, 132.92, 256.92)
s.sym("DIODE_SS", "D3", "1N4007", 138, 256.92, lx=-2.6, ly=-5.6)
s.wire(143.08, 256.92, 144.92, 256.92)
s.sym("DIODE_SS", "D2", "1N4007", 150, 256.92, lx=-2.6, ly=-5.6)
s.wire(155.08, 256.92, 164, 256.92)
s.wire(t1["ht_b"][0], 267.08, 132.92, 267.08)
s.sym("DIODE_SS", "D5", "1N4007", 138, 267.08, lx=-2.6, ly=5.2)
s.wire(143.08, 267.08, 144.92, 267.08)
s.sym("DIODE_SS", "D4", "1N4007", 150, 267.08, lx=-2.6, ly=5.2)
s.wire(155.08, 267.08, 164, 267.08)
s.wire(164, 256.92, 164, 267.08)
s.wire(164, 262, 169.46, 262)
s.junction(164, 262)
c23 = s.dualcan("C23", "50+50u", 172, 265.81, lx=-6.6, ly=6.4)
s.wire(169.46, 262, 169.46, 258)
s.wire(169.46, 258, 174.54, 258)
s.wire(174.54, 258, 174.54, 262)
s.junction(174.54, 262)
s.gnd(c23["com"][0], 269.62)
s.wire(174.54, 262, 184.92, 262)
f2l, f2r = s.fuse("F2", "T500mA", 190, 262)
s.wire(f2r, 262, 204, 262)
s.junction(204, 262)
s.wire(204, 262, 204, 256)
s.glabel("B+1", 204, 256, 90)
s.sym("CHOKE", "T3", "choke", 214, 262, lx=-4.6, ly=-6.6)
s.wire(204, 262, 206.38, 262)
s.wire(221.62, 262, 237.46, 262)
s.junction(230, 262)
s.wire(230, 262, 230, 256)
s.glabel("B+2", 230, 256, 90)
c22 = s.dualcan("C22", "50+50u", 240, 265.81, lx=-6.6, ly=6.4)
s.wire(237.46, 262, 237.46, 258)
s.wire(237.46, 258, 242.54, 258)
s.wire(242.54, 258, 242.54, 262)
s.junction(237.46, 262)
s.junction(242.54, 262)
s.gnd(c22["com"][0], 269.62)
r29l, r29r = s.series_h("R", "R29", "10k 1W", 250, 262)
s.wire(242.54, 262, r29l, 262)
s.wire(r29r, 262, 262, 262)
s.junction(262, 262)
s.wire(262, 262, 262, 256)
s.glabel("B+3", 262, 256, 90)
r8l, r8r = s.series_h("R", "R8", "10k 1W", 276, 262)
s.wire(262, 262, r8l, 262)
s.wire(r8r, 262, 292, 262)
s.junction(292, 262)
s.wire(292, 262, 300, 262)
s.glabel("B+4", 300, 262, 0)
# C21: one section each side of R8 — the drawing's dual can straddles the dropper
c21 = s.dualcan("C21", "50+50u", 276, 275.81, lx=-6.6, ly=6.4)
s.wire(262, 262, 262, 272)
s.wire(262, 272, 273.46, 272)
s.wire(292, 262, 292, 272)
s.wire(292, 272, 278.54, 272)
s.gnd(c21["com"][0], 279.62)

# ======================= negative-bias supply ===============================
BY = 284.0
s.junction(126, 267.08)
s.wire(126, 267.08, 126, BY)
# The bias rail is NEGATIVE, so the rectifier faces the other way from the HT
# bridge: its cathode looks back at the winding through R30 and its anode feeds
# the reservoir, pumping charge out of C20.
r30l, r30r = s.series_h("R", "R30", "220k", 134, BY)
s.wire(126, BY, r30l, BY)
s.sym("DIODE_SS", "D1", "1N4007", 148, BY, rot=180, lx=-2.6, ly=-5.6, label_rot=0)
s.wire(r30r, BY, 142.92, BY)
s.wire(153.08, BY, 162, BY)
s.junction(162, BY)
s.sym("C", "C20", "10u", 162, BY + 3.81, lx=2.4)
s.gnd(162, BY + 7.62)
r27l, r27r = s.series_h("R", "R27", "15k", 172, BY)
s.wire(162, BY, r27l, BY)
s.wire(r27r, BY, 186, BY)
s.junction(180, BY)
s.sym("C", "C19", "10u", 180, BY + 3.81, lx=-7.6)
s.gnd(180, BY + 7.62)
s.junction(186, BY)
s.sym("R", "R26", "56k", 186, BY + 3.81, lx=2.4)
s.sym("POT", "RV1", "22k lin bias adj", 186, BY + 11.43, lx=6.0, ly=-5.6)
s.wire(191.08, BY + 11.43, 196, BY + 11.43)     # wiper strapped to the foot
s.wire(196, BY + 11.43, 196, BY + 15.24)
s.wire(196, BY + 15.24, 186, BY + 15.24)
s.junction(186, BY + 15.24)
s.gnd(186, BY + 15.24)
s.wire(186, BY, 206, BY)
s.glabel("-BIAS", 206, BY, 0)

s.note("S2 is a two-pole standby switch: the drawing breaks both HT legs, and one "
       "pole is drawn here. T1 also carries the 6.3 V heater winding — black and "
       "orange leads with an earthed green centre tap — which is not drawn; nor is "
       "the mains indicator lamp the drawing shows across the primary, which carries "
       "no reference designator. See netlist.cir and meta.yaml.")

s.write(OUT, [
    "The 50 W lead head with the input triodes in series and a master volume after the tone stack — the circuit repackaged in 1981 as the JCM800.",
    "Values from the Marshall 2204 STD factory drawing, both sheets. Heaters, the mains indicator and the PT's heater winding are annotations — see netlist.cir and meta.yaml.",
])
print(f"wrote {OUT}")
