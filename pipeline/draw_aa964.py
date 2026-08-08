#!/usr/bin/env python3
"""Generate amps/aa964/schematic.kicad_sch from the stage-template library.

Values per the published "Princeton-Amp AA964" drawing (see amps/aa964/meta.yaml).
Drawn on A3: the signal path runs left to right along the top — two input jacks,
the 7025's first stage, the treble/bass tone stack and volume, the 7025's second
stage, the cathodyne inverter and the fixed-bias 6V6 pair into the output
transformer. The tremolo oscillator (the other half of the 12AX7) sits in the
middle band, the power supply, bias supply and mains along the bottom.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
B+1 = +420 V (reservoir, OT centre tap, 6V6 plates), B+2 = +415 V (6V6 screens),
B+3 = +370 V (the filtered node between the two 18 k droppers), B+4 = +290 V
(both 7025 plates and the inverter); -34 V is the fixed-bias line. Heaters and
the pilot lamp are omitted here (annotation layer) — see netlist.cir, meta.yaml
and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "aa964" / "schematic.kicad_sch"
s = Sch()

# ============================ TITLE ==================================
s.note('Heaters and pilot lamp omitted here — see netlist.cir, meta.yaml, layout.yaml.  Rails: B+1 +420 · B+2 +415 screens · B+3 +370 · B+4 +290 · bias -34 V')

# ============================ INPUT + FIRST STAGE (V1A) ===============
YN = 62
s.text("First stage (7025) · treble/bass tone stack · volume", 12, 30, 1.6)
s.glabel("INPUT 1", 12, YN + 4, 180)
s.glabel("INPUT 2", 12, YN - 4, 180)
GB = 40                                        # grid bus x
l, r = s.series_h("R", "R2n", "68k", 24, YN - 4)
s.wire(16, YN - 4, l, YN - 4)
s.wire(r, YN - 4, GB, YN - 4)
l, r = s.series_h("R", "R1n", "68k", 24, YN + 4)
s.wire(16, YN + 4, l, YN + 4)
s.wire(r, YN + 4, GB, YN + 4)
s.wire(GB, YN - 4, GB, YN + 4)
s.junction(GB, YN)
s.sym("R", "RG1A", "1M", GB, YN + 7.81)        # 1M grid leak at the jacks
s.gnd(GB, YN + 11.62)
t1a = s.triode("V1A", "7025", 52, YN)
s.wire(GB, YN, t1a["g"][0], YN)
s.plate_load("RL1A", "100k", t1a["p"], "B+4")
s.wire(52, YN + 7.62, 52, YN + 9)
s.shunt_rc("RK1A", "1.5k", "CK1A", "25u", 52, YN + 9)

# ---- treble / bass tone stack (no coupling cap: the caps do the blocking) ----
TEE = YN - 7.62 - 3.48                         # V1A plate stub tee = 50.9
s.wire(52, TEE, 64, TEE)
s.junction(52, TEE)
# treble branch: plate -> CT 250 pF -> treble pot top
s.wire(64, TEE, 64, TEE - 8)
cl, cr = s.series_h("C", "CT", "250p", 80, TEE - 8)
s.wire(64, TEE - 8, cl, TEE - 8)
s.wire(cr, TEE - 8, 96, TEE - 8)
s.sym("POT", "VRT", "250k treb", 96, TEE - 8 + 3.81)     # pins TEE-8 / TEE-0.38
# slope branch: plate -> RS 100k -> node B
s.wire(64, TEE, 64, TEE + 6)
s.junction(64, TEE)
sl, sr = s.series_h("R", "RS", "100k", 74, TEE + 6)
s.wire(64, TEE + 6, sl, TEE + 6)
s.wire(sr, TEE + 6, 84, TEE + 6)                          # node B
# node B -> CB1 0.1 -> the treble-bottom/bass node (as the published AA964
# schematic draws it: the treble pot's lower lug sits on the far side of the
# bass capacitor, not on the slope foot)
cl, cr = s.series_h("C", "CB1", ".1u", 90, TEE + 6)
s.wire(84, TEE + 6, cl, TEE + 6)
s.wire(cr, TEE + 6, 96, TEE + 6)
s.wire(96, TEE - 0.38, 96, TEE + 6)                       # treble bottom lug -> bass node
s.sym("POT", "VRB", "250k bass", 96, TEE + 6 + 3.81)      # pins TEE+6 / TEE+13.62
# bass pot wired as a rheostat: wiper strapped to its hot lug (the drawing's
# arrow-through-body variable resistor); the stack's output is the treble
# wiper alone
s.wire(101.08, TEE + 9.81, 108, TEE + 9.81)
s.wire(108, TEE + 9.81, 108, TEE + 6)
s.wire(108, TEE + 6, 96, TEE + 6)
s.junction(96, TEE + 6)
# node B -> CB2 0.047 -> node D -> RBL 6.8k -> ground
s.wire(84, TEE + 6, 84, TEE + 13.62)
s.junction(84, TEE + 6)
cl, cr = s.series_h("C", "CB2", ".047u", 90, TEE + 13.62)
s.wire(84, TEE + 13.62, cl, TEE + 13.62)
s.wire(cr, TEE + 13.62, 96, TEE + 13.62)
s.sym("R", "RBL", "6.8k", 96, TEE + 17.43)
s.gnd(96, TEE + 21.24)
# treble wiper -> volume pot -> V1B grid
s.wire(101.08, TEE - 4.19, 114, TEE - 4.19)
s.sym("POT", "VRV", "1M vol", 114, TEE - 0.38)            # pins TEE-4.19 / TEE+3.43
s.gnd(114, TEE + 3.43)
s.wire(119.08, TEE - 0.38, 126, TEE - 0.38)
s.wire(126, TEE - 0.38, 126, YN)

# ============================ SECOND STAGE (V1B) ======================
s.text("Second stage (7025) · 47 Ω feedback tail", 130, 30, 1.6)
t1b = s.triode("V1B", "7025", 140, YN)
s.wire(126, YN, t1b["g"][0], YN)
s.plate_load("RL1B", "100k", t1b["p"], "B+4")
# cathode: 1.5k || 25u down to the tail junction J1B, then 47R to ground
s.wire(140, YN + 7.62, 140, YN + 10)
s.sym("R", "RK1B", "1.5k", 140, YN + 13.81)               # pins YN+10 / YN+17.62
s.sym("C", "CK1B", "25u", 149, YN + 13.81)
s.wire(140, YN + 10, 149, YN + 10)
s.wire(140, YN + 17.62, 149, YN + 17.62)
s.junction(140, YN + 17.62)                               # J1B
s.sym("R", "R47", "47", 140, YN + 21.43)
s.gnd(140, YN + 25.24)
# global feedback: 2.7k from the speaker back to the 47R tail
s.glabel("SPKR", 116, YN + 17.62, 180)
nl, nr = s.series_h("R", "RNFB", "2.7k", 126, YN + 17.62)
s.wire(120, YN + 17.62, nl, YN + 17.62)
s.wire(nr, YN + 17.62, 140, YN + 17.62)

# ============================ CATHODYNE PHASE INVERTER (V2B) ==========
s.text("Cathodyne phase inverter (½ 12AX7)", 176, 30, 1.6)
TEEB = YN - 7.62 - 3.48
s.wire(140, TEEB, 150, TEEB)
s.junction(140, TEEB)
cl, cr = s.series_h("C", "CC1", ".022u", 158, TEEB)
s.wire(150, TEEB, cl, TEEB)
s.wire(cr, TEEB, 170, TEEB)
s.wire(170, TEEB, 170, YN)
XPI = 196
t2b = s.triode("V2B", "12AX7", XPI, YN)
s.wire(170, YN, t2b["g"][0], YN)
s.junction(186, YN)
s.plate_load("RLPI", "56k", t2b["p"], "B+4")
# cathode -> 1k -> junction JPI -> 56k tail -> ground; 1M grid leak back to JPI
s.wire(XPI, YN + 7.62, XPI, YN + 10)
s.sym("R", "RKPI", "1k", XPI, YN + 13.81)                 # pins YN+10 / YN+17.62
s.junction(XPI, YN + 17.62)                               # JPI (+63.8 V)
s.sym("R", "RTAIL", "56k", XPI, YN + 21.43)
s.gnd(XPI, YN + 25.24)
s.sym("R", "RGPI", "1M", 186, YN + 8, lx=-9.4)            # pins YN+4.19 / YN+11.81
s.wire(186, YN, 186, YN + 4.19)
s.wire(186, YN + 11.81, 186, YN + 17.62)
s.wire(186, YN + 17.62, XPI, YN + 17.62)

# ============================ OUTPUT COUPLERS + 6V6 PAIR ==============
# inverter plate (in phase-inverted) -> C1 -> V3 grid; cathode -> C2 -> V4 grid
TEEP = YN - 7.62 - 3.48
s.wire(XPI, TEEP, XPI + 8, TEEP)
s.junction(XPI, TEEP)
cl, cr = s.series_h("C", "C1", ".1u", XPI + 16, TEEP)
s.wire(XPI + 8, TEEP, cl, TEEP)
s.wire(cr, TEEP, XPI + 26, TEEP)
s.wire(XPI + 26, TEEP, XPI + 26, 40)
s.wire(XPI + 26, 40, 234, 40)
KTEE = YN + 10
s.wire(XPI, KTEE, XPI + 8, KTEE)
s.junction(XPI, KTEE)
cl, cr = s.series_h("C", "C2", ".1u", XPI + 16, KTEE)
s.wire(XPI + 8, KTEE, cl, KTEE)
s.wire(cr, KTEE, XPI + 26, KTEE)
s.wire(XPI + 26, KTEE, XPI + 26, 96)
s.wire(XPI + 26, 96, 234, 96)

XO = 258
s.text("Fixed-bias 6V6GT pair — screens tied straight to B+2, no stopper resistors", 232, 124, 1.4)
for gy, vref, glref in [(40, "V3", "RGL1"), (96, "V4", "RGL2")]:
    s.junction(234, gy)
    s.sym("R", glref, "220k 5%", 234, gy + 3.81)
    s.wire(234, gy + 7.62, 234, gy + 10.16)
    s.glabel("-34V", 234, gy + 10.16, 270)
    p = s.pentode(vref, "6V6GT", XO, gy)
    s.wire(234, gy, p["g1"][0], gy)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 6, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# ---- output transformer TR2 (125A10B) + speaker jack --------------------
s.sym("OT_PP", "TR2", "125A10B", 300, 68)
s.wire(XO, 31.745, XO, 24)
s.wire(XO, 24, 285, 24)
s.wire(285, 24, 285, 62.92)
s.wire(285, 62.92, 291.11, 62.92)                          # V3 plate -> PRI_A
s.wire(XO, 87.745, XO, 80)
s.wire(XO, 80, 278, 80)
s.wire(278, 80, 278, 73.08)
s.wire(278, 73.08, 291.11, 73.08)                          # V4 plate -> PRI_B
s.wire(291.11, 68, 272, 68)
s.wire(272, 68, 272, 58)
s.glabel("B+1", 272, 58, 90)                               # primary centre tap
jspk = s.jack("JSPK", "spkr", 324, 68, lx=3.4, ly=-9.6)    # tip 65.46, sleeve 70.54
s.wire(308.89, 65.46, jspk["tip"][0], 65.46)               # secondary -> speaker tip
s.junction(314, 65.46)
s.glabel("SPKR", 314, 60, 90)
s.wire(314, 60, 314, 65.46)
s.wire(308.89, 70.54, jspk["sleeve"][0], 70.54)            # secondary cold -> sleeve
s.junction(314, 70.54)
s.wire(314, 70.54, 314, 78)
s.gnd(314, 78)

# ============================ TREMOLO OSCILLATOR (V2A) ================
YT = 180
RAILY = 208                                    # phase-shift ladder rail
s.caption('Tremolo oscillator (½ 12AX7) — a running phase-shift oscillator; its DC point is excluded from netlist.cir (see notes.md)', 20, 148, 1.4)
t2a = s.triode("V2A", "12AX7", 60, YT)
s.plate_load("RTO", "220k", t2a["p"], "B+2")
s.wire(60, YT + 7.62, 60, YT + 10)
s.shunt_rc("RKTO", "3.3k", "CKTO", "25u", 52.38, YT + 10)
s.junction(60, YT + 10)
# phase-shift ladder: plate -> .02 -> N2 (speed) -> .01 -> N1 -> .01 -> grid
PTEE = YT - 7.62 - 3.48                                    # 168.9
s.wire(60, PTEE, 70, PTEE)
s.junction(60, PTEE)
cl, cr = s.series_h("C", "CTO1", ".02u", 78, PTEE)
s.wire(70, PTEE, cl, PTEE)
s.wire(cr, PTEE, 90, PTEE)                                 # N2
# speed control: N2 -> 3M rheostat -> 100k -> ground
s.wire(90, PTEE, 94.19, PTEE)
s.sym("POT", "VRSPD", "3M speed", 98, PTEE, rot=90, lx=-3.2, ly=6.4)
s.wire(101.81, PTEE, 106, PTEE)
s.wire(98, PTEE - 5.08, 94.19, PTEE - 5.08)               # rheostat: wiper to lug 1
s.wire(94.19, PTEE - 5.08, 94.19, PTEE)
s.junction(94.19, PTEE)
sl, sr = s.series_h("R", "RSPD", "100k", 112, PTEE)
s.wire(106, PTEE, sl, PTEE)
s.wire(sr, PTEE, 120, PTEE)
s.gnd(120, PTEE)
# N2 down to the lower ladder rail
s.wire(90, PTEE, 90, RAILY)
s.junction(90, PTEE)
cl, cr = s.series_h("C", "CTO2", ".01u", 82, RAILY)
s.wire(90, RAILY, cr, RAILY)
s.wire(cl, RAILY, 72, RAILY)                               # N1
s.junction(72, RAILY)
cl, cr = s.series_h("C", "CTO3", ".01u", 62, RAILY)
s.wire(72, RAILY, cr, RAILY)
s.wire(cl, RAILY, 48, RAILY)                               # oscillator grid
s.junction(48, RAILY)
s.wire(48, RAILY, 48, YT)
s.wire(48, YT, t2a["g"][0], YT)
s.sym("R", "RTO2", "1M", 48, RAILY + 3.81, lx=-8.4)        # grid -> ground
s.gnd(48, RAILY + 7.62)
s.sym("R", "RTO1", "1M", 72, 197)                          # N1 -> cathode
s.wire(72, 200.81, 72, RAILY)
s.wire(72, 193.19, 72, YT + 10)
s.wire(72, YT + 10, 60, YT + 10)
# vibrato-pedal jack: shorts the ladder to ground and silences the oscillator
s.wire(72, RAILY, 72, RAILY + 10)
jvib = s.jack("JVIB", "ftsw", 80, RAILY + 12.54, lx=3.4, ly=-9.6)
s.wire(72, RAILY + 10, jvib["tip"][0], RAILY + 10)         # ladder foot -> tip
s.wire(*jvib["sleeve"], 68, jvib["sleeve"][1])             # sleeve -> chassis
s.wire(68, RAILY + 18, 68, jvib["sleeve"][1])
s.gnd(68, RAILY + 18)
# oscillator output: plate -> 1M -> node (.02 to ground) -> .1 -> intensity
s.wire(60, PTEE, 36, PTEE)
s.wire(36, PTEE, 36, YT)
ol, orr = s.series_h("R", "RTOUT", "1M", 28, YT)
s.wire(36, YT, orr, YT)
s.wire(ol, YT, 18, YT)
s.junction(18, YT)
s.sym("C", "CTOUT1", ".02u", 18, YT + 3.81)
s.gnd(18, YT + 7.62)
s.wire(18, YT, 18, YT - 6)
s.sym("C", "CTOUT2", ".1u", 18, YT - 9.81)                 # pins YT-6 / YT-13.62
s.wire(18, YT - 13.62, 18, YT - 18)
s.wire(18, YT - 18, 22.19, YT - 18)
s.sym("POT", "VRINT", "250k int", 26, YT - 18, rot=90, lx=-13.0, ly=-6.0)
s.wire(29.81, YT - 18, 34, YT - 18)
s.glabel("BIAS", 34, YT - 18, 0)                           # to the bias supply
s.wire(26, YT - 23.08, 26, YT - 27)
s.glabel("-34V", 26, YT - 27, 90)                          # wiper IS the bias line
s.text("At DC the 0.1 µF blocks the oscillator, so no current flows in the Intensity "
       "control and its wiper sits at the supply's -34 V.", 130, 232, 1.1)

# ============================ POWER SUPPLY ============================
YPW = 252
s.note('Power supply — TR1 125P1B 340-0-340 · GZ34 · 20 µF·450 V cans, 1 k-1 W then 18 k-1 W + 18 k-1 W droppers')
pt = s.pt("TR1", "125P1B", 44, YPW)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
# GZ34 full-wave rectifier
s.glabel("HT_A", 74, YPW - 12, 90)
s.wire(74, YPW - 12, 74, YPW - 9.5)
s.diode_tube("V5A", "GZ34", 74, YPW - 1.88, lx=-11.4)
s.glabel("HT_B", 86, YPW - 12, 90)
s.wire(86, YPW - 12, 86, YPW - 9.5)
s.diode_tube("V5B", "GZ34", 86, YPW - 1.88, lx=6.0)
s.wire(74, YPW + 5.74, 74, YPW + 8)
s.wire(86, YPW + 5.74, 86, YPW + 8)
s.wire(74, YPW + 8, 100, YPW + 8)
s.junction(86, YPW + 8)
s.junction(92, YPW + 8)
s.sym("C", "CA", "20u", 92, YPW + 11.81, lx=2.6, ly=-0.4)
s.gnd(92, YPW + 15.62)
s.glabel("B+1", 100, YPW + 8, 0)
s.wire(100, YPW + 8, 103, YPW + 8)
RAIL = YPW + 8
for rref, rval, xr, nxt, cref, xlab in [("RD1", "1k 1W", 109, 124, "CB", "B+2"),
                                        ("RD2", "18k 1W", 130, 146, "CC", "B+3"),
                                        ("RD3", "18k 1W", 152, 168, "CD", "B+4")]:
    l, r = s.series_h("R", rref, rval, xr, RAIL)
    s.wire(xr - 6, RAIL, l, RAIL)
    s.wire(r, RAIL, nxt, RAIL)
    s.junction(nxt - 6, RAIL)
    s.glabel(xlab, nxt - 6, RAIL - 2.54, 90)
    s.wire(nxt - 6, RAIL - 2.54, nxt - 6, RAIL)
    s.junction(nxt - 2, RAIL)
    s.sym("C", cref, "20u", nxt - 2, RAIL + 3.81, lx=2.6, ly=-0.4)
    s.gnd(nxt - 2, RAIL + 7.62)

# ============================ BIAS SUPPLY =============================
YB = 168
s.text("Bias supply — off the HT winding → -34 V", 200, 158, 1.3)
s.glabel("HT_B", 200, YB, 180)
s.wire(204, YB, 206.19, YB)
l, r = s.series_h("R", "RBF", "100k 5%", 210, YB)
s.wire(r, YB, 218, YB)
s.sym("DIODE_SS", "DBIAS", "Si", 223.08, YB, lx=-2.0, ly=-5.4)
s.wire(228.16, YB, 246, YB)
s.junction(231, YB)
s.sym("R", "RB", "27k", 231, YB + 3.81, lx=-8.0)
s.gnd(231, YB + 7.62)
s.junction(241, YB)
s.sym("C", "CBIAS", "25u 50V", 241, YB + 3.81, lx=2.6)
s.gnd(241, YB + 7.62)
s.glabel("BIAS", 246, YB, 0)

# ============================ MAINS · FUSE · SWITCHES =================
s.text("Mains, fuse and switches — the period ground-switch cap is not fitted in modern builds",
       200, 196, 1.3)
s.glabel("AC 117 V", 200, 206, 180)
s.wire(204, 206, 204.92, 206)
s.sym("FUSE", "FUSE", "1A SB", 210, 206, lx=-3.2, ly=-6.0)
s.wire(215.08, 206, 220.92, 206)
s.sym("SWITCH", "SW1", "AC sw", 226, 206, lx=-3.2, ly=-6.0)
s.wire(231.08, 206, 240, 206)
s.glabel("MAINS", 240, 206, 0)
s.glabel("AC 117 V", 200, 214, 180)
s.wire(204, 214, 240, 214)
s.glabel("MAINS", 240, 214, 0)
s.junction(210, 214)
s.wire(210, 214, 210, 224)
s.wire(210, 224, 216.92, 224)
s.sym("SWITCH", "SW2", "gnd sw", 222, 224, lx=-3.2, ly=-6.0)
s.wire(227.08, 224, 234.19, 224)
s.sym("C", "CDEATH", ".047u 600V", 238, 224, rot=90, lx=-3.2, ly=-6.2)
s.wire(241.81, 224, 246, 224)
s.gnd(246, 224)

s.write(OUT)
print(f"wrote {OUT}")
