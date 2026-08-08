#!/usr/bin/env python3
"""Generate amps/aa1164/schematic.kicad_sch from the stage-template library.

Values per the published AA1164 Princeton Reverb-Amp drawing (see
amps/aa1164/meta.yaml). One channel, but a busy sheet: the preamp and its
treble/bass stack run along the top left with the power supply on the top right;
the reverb send / 12AT7 driver / tank / recovery block sits in the middle band
with the bias supply and the mains parts to its right; the mixer, driver stage,
split-load phase inverter and 6V6 output fill the third band; the tremolo
oscillator — a running phase-shift oscillator whose DC point is a documented
netlist exclusion — occupies the bottom band. Drawn on A3.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
B+1 = +420 (rectifier reservoir, output-transformer centre tap), B+2 = +400
(6V6 screens, reverb-driver plates through TR3, tremolo plate load), B+3 = +320
(filter node only), B+4 = +240 (every preamp plate load and the phase inverter);
-34 V is the fixed-bias line. The 6.3 V heater chain and the pilot lamp are an
annotation layer shown on the board layout (layout.yaml), not here — only the
hum-balance pair appears, next to the power supply.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "aa1164" / "schematic.kicad_sch"
s = Sch()

# ============================ TITLE ==================================
s.note('Rails: B+1 +420 (reservoir / OT centre tap) · B+2 +400 (screens, reverb driver, tremolo) · B+3 +320 · B+4 +240 · bias -34 V. Heater chain and pilot lamp are shown on the board layout (layout.yaml).')

# ============================ PREAMP (band 1, left) ==================
YN = 56
s.caption('Preamp — two inputs, 7025 (12AX7) gain stage, treble/bass stack, Volume, second stage', 12, 32, 1.5)# --- inputs: two 68k stoppers onto a shared 1M grid leak
s.glabel("INPUT 1", 12, YN - 4, 180)
l, r = s.series_h("R", "R1a", "68k", 24, YN - 4)
s.wire(16, YN - 4, l, YN - 4)
s.wire(r, YN - 4, 38, YN - 4)
s.glabel("INPUT 2", 12, YN + 4, 180)
l, r = s.series_h("R", "R1b", "68k", 24, YN + 4)
s.wire(16, YN + 4, l, YN + 4)
s.wire(r, YN + 4, 38, YN + 4)
s.wire(38, YN - 4, 38, YN + 4)
s.junction(38, YN)
s.sym("R", "RGN1", "1M", 38, YN + 4 + 3.81)
s.gnd(38, YN + 4 + 7.62)

# --- V1A input stage
t1 = s.triode("V1A", "12AX7 (7025)", 52, YN)
s.wire(38, YN, t1["g"][0], YN)
s.plate_load("RLN1", "100k", t1["p"], "B+4")
s.wire(52, YN + 7.62, 52, YN + 9)
s.shunt_rc("RKN1", "1.5k", "CKN1", "25u", 52, YN + 9)

# --- treble / bass tone stack + Volume
tee = YN - 7.62 - 3.48                     # 44.9 — plate stub tee
TRB = tee - 6                              # 38.9 — treble leg
SLP = tee + 6.1                            # 51.0 — slope / bass leg
MID = tee + 17.1                           # 62.0 — the stack's "mid" node rail
# Wired as the published AA1164 sheet draws it — the same two-knob ladder as
# the AA964: the plate feeds the network directly (the three capacitors do all
# the blocking); the treble pot's LOWER lug sits on the far side of CB1,
# sharing a node with the bass pot; the bass pot is a rheostat (wiper strapped
# to its hot lug) above the fixed 6.8k leg; the stack's output is the TREBLE
# WIPER ALONE, into the Volume control.
s.junction(52, tee)
s.wire(52, tee, 76, tee)                   # node A (stack input)
# treble leg: A -> CT 250p -> VRT 250k
s.junction(76, tee)
s.wire(76, tee, 76, TRB)
tl, tr = s.series_h("C", "CT", "250p", 84, TRB)
s.wire(76, TRB, tl, TRB)
s.wire(tr, TRB, 116, TRB)
s.sym("POT", "VRT", "250k treb", 116, TRB + 3.81)
# slope leg: A -> RS 100k -> node B
s.wire(76, tee, 76, SLP)
sl, sr = s.series_h("R", "RS", "100k", 84, SLP)
s.wire(76, SLP, sl, SLP)
s.wire(sr, SLP, 92, SLP)
s.junction(92, SLP)
# node B -> CB1 0.1u -> the treble-bottom/bass node
bl, br = s.series_h("C", "CB1", ".1u", 98, SLP)
s.wire(92, SLP, bl, SLP)
s.wire(br, SLP, 104, SLP)
s.sym("POT", "VRB", "250k bass", 104, SLP + 3.81)
# the treble pot's lower lug -> the bass node (the far side of CB1)
s.wire(116, TRB + 7.62, 116, TRB + 9.9)
s.wire(116, TRB + 9.9, 104, TRB + 9.9)
s.wire(104, TRB + 9.9, 104, SLP)
s.junction(104, SLP)
# bass wired as a rheostat: wiper strapped to its hot lug
s.wire(109.08, SLP + 3.81, 112, SLP + 3.81)
s.wire(112, SLP + 3.81, 112, SLP)
s.wire(112, SLP, 104, SLP)
# node B -> CB2 0.047u -> the mid node: bass cold lug -> RSL 6.8k -> ground
s.wire(92, SLP, 92, MID)
ml, mr = s.series_h("C", "CB2", ".047u", 98, MID)
s.wire(92, MID, ml, MID)
s.wire(mr, MID, 104, MID)
s.wire(104, SLP + 7.62, 104, MID)
s.junction(104, MID)
s.wire(104, MID, 116, MID)
s.junction(116, MID)
s.sym("R", "RSL", "6.8k", 116, MID + 3.81)
s.gnd(116, MID + 7.62)
# treble wiper = the stack's output, into the Volume control
s.wire(121.08, TRB + 3.81, 132, TRB + 3.81)
s.sym("POT", "VRVOL", "1M vol", 132, TRB + 7.62)
s.gnd(132, TRB + 11.43)

# --- V1B second stage
s.wire(137.08, TRB + 7.62, 144, TRB + 7.62)
s.wire(144, TRB + 7.62, 144, YN)
t1b = s.triode("V1B", "12AX7 (7025)", 156, YN)
s.wire(144, YN, t1b["g"][0], YN)
s.plate_load("RLN2", "100k", t1b["p"], "B+4")
s.wire(156, YN + 7.62, 156, YN + 9)
s.shunt_rc("RKN2", "1.5k", "CKN2", "25u", 156, YN + 9)
# V1B plate -> CC1 0.02u -> the dry node feeding BOTH the mixer and the reverb send
s.junction(156, tee)
s.wire(156, tee, 164, tee)
cl, cr = s.series_h("C", "CC1", ".02u", 170, tee)
s.wire(164, tee, cl, tee)
s.wire(cr, tee, 182, tee)
s.glabel("DRY", 182, tee, 0)

# ============================ POWER SUPPLY (band 1, right) ===========
YPW = 60
s.text("Power supply — PT 125P1B 340-0-340 V, 5U4GB full-wave rectifier, 1 k + 18 k + 18 k droppers",
       200, 32, 1.4)
pt = s.pt("TR1", "125P1B", 216, YPW)
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

# --- 5U4GB, two plate units (directly heated: the filament is the cathode)
s.glabel("HT_A", 246, YPW - 12, 90)
s.wire(246, YPW - 12, 246, YPW - 9.5)
s.diode_tube("V7A", "5U4GB", 246, YPW - 1.88, lx=-11.6)
s.glabel("HT_B", 258, YPW - 12, 90)
s.wire(258, YPW - 12, 258, YPW - 9.5)
s.diode_tube("V7B", "5U4GB", 258, YPW - 1.88, lx=6.0)
s.wire(246, YPW + 5.74, 246, YPW + 8)
s.wire(258, YPW + 5.74, 258, YPW + 8)
s.wire(246, YPW + 8, 272, YPW + 8)
s.junction(258, YPW + 8)
# reservoir CF1 -> B+1
s.junction(264, YPW + 8)
s.sym("C", "CF1", "20u", 264, YPW + 11.81)
s.gnd(264, YPW + 15.62)
s.junction(272, YPW + 8)
s.wire(272, YPW + 5.46, 272, YPW + 8)
s.glabel("B+1", 272, YPW + 5.46, 90)
# 1k -> B+2 (screens / reverb driver / tremolo)
l, r = s.series_h("R", "R1K", "1k 1W", 280, YPW + 8)
s.wire(272, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 292, YPW + 8)
s.junction(288, YPW + 8)
s.wire(288, YPW + 5.46, 288, YPW + 8)
s.glabel("B+2", 288, YPW + 5.46, 90)
s.junction(292, YPW + 8)
s.sym("C", "CF2", "20u", 292, YPW + 11.81)
s.gnd(292, YPW + 15.62)
# 18k -> B+3 (nothing else taps this node)
l, r = s.series_h("R", "RD1", "18k 1W", 302, YPW + 8)
s.wire(292, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 314, YPW + 8)
s.junction(310, YPW + 8)
s.wire(310, YPW + 5.46, 310, YPW + 8)
s.glabel("B+3", 310, YPW + 5.46, 90)
s.junction(314, YPW + 8)
s.sym("C", "CF3", "20u", 314, YPW + 11.81)
s.gnd(314, YPW + 15.62)
# 18k -> B+4 (preamp + phase-inverter rail)
l, r = s.series_h("R", "RD2", "18k 1W", 324, YPW + 8)
s.wire(314, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 336, YPW + 8)
s.junction(332, YPW + 8)
s.wire(332, YPW + 5.46, 332, YPW + 8)
s.glabel("B+4", 332, YPW + 5.46, 90)
s.sym("C", "CF4", "20u", 336, YPW + 11.81)
s.gnd(336, YPW + 15.62)

# --- heater hum-balance pair (the 6.3 V chain itself is on the board layout)
s.text("6.3 V heater winding — hum-balance pair only; the heater chain is drawn on the board layout",
       200, 88, 1.2)
s.glabel("HTR_A", 212, 96, 180)
l, r = s.series_h("R", "RH1", "100", 226, 96)
s.wire(216, 96, l, 96)
l2, r2 = s.series_h("R", "RH2", "100", 240, 96)
s.wire(r, 96, l2, 96)
s.junction(233, 96)
s.wire(233, 96, 233, 99)
s.gnd(233, 99)
s.wire(r2, 96, 248, 96)
s.glabel("HTR_B", 248, 96, 0)

# ============================ REVERB (band 2, left) ==================
YR = 116
s.text("Reverb — 500 pF send, 12AT7 driver (both sections paralleled), 125A20B transformer, tank, recovery stage",
       12, 100, 1.5)
s.glabel("DRY", 12, YR, 180)
cl, cr = s.series_h("C", "CRS", "500p", 26, YR)
s.wire(16, YR, cl, YR)
s.wire(cr, YR, 34, YR)
s.junction(34, YR)
s.wire(34, YR, 34, YR + 22)
# paralleled 12AT7 halves
t2a = s.triode("V2A", "12AT7", 46, YR)
t2b = s.triode("V2B", "12AT7", 46, YR + 22)
s.wire(34, YR, t2a["g"][0], YR)
s.wire(34, YR + 22, t2b["g"][0], YR + 22)
s.junction(34, YR + 22)
s.sym("R", "RGRD", "1M", 34, YR + 22 + 3.81, lx=-8.6)
s.gnd(34, YR + 22 + 7.62)
# plates tied
s.wire(46, YR - 7.62, 46, YR - 11)
s.wire(46, YR + 22 - 7.62, 46, YR + 11)
s.wire(46, YR - 11, 56, YR - 11)
s.wire(46, YR + 11, 56, YR + 11)
s.wire(56, YR - 11, 56, YR + 11)
s.junction(56, YR - 11)
# shared cathode: RKRD 2.2k || CKRD 25u, tied below V2B
cy = YR + 33
s.wire(46, YR + 7.62, 38, YR + 7.62)
s.wire(38, YR + 7.62, 38, cy)
s.wire(38, cy, 46, cy)
s.wire(46, YR + 22 + 7.62, 46, cy)
s.junction(46, cy)
s.shunt_rc("RKRD", "2.2k", "CKRD", "25u", 46, cy)
# reverb transformer TR3 -> tank
s.sym("OT_SE", "TR3", "125A20B", 70, YR - 5)
s.wire(56, YR - 11, 61.11, YR - 11)
s.wire(61.11, YR - 11, 61.11, YR - 7.54)
s.wire(61.11, YR - 2.46, 61.11, YR + 1)
s.glabel("B+2", 61.11, YR + 1, 90)
tk = s.tank("TANK", "spring reverb", 100, YR - 5)
s.wire(78.89, YR - 7.54, tk["in_h"][0], YR - 7.54)
s.wire(78.89, YR - 2.46, tk["in_c"][0], YR - 2.46)
s.junction(84, YR - 2.46)
s.wire(84, YR - 2.46, 84, YR + 1)
s.gnd(84, YR + 1)
s.wire(tk["out_c"][0], tk["out_c"][1], 114, tk["out_c"][1])
s.gnd(114, tk["out_c"][1])
# recovery stage V3A: tank hot -> grid, 220k leak to ground
s.wire(tk["out_h"][0], tk["out_h"][1], 124, tk["out_h"][1])
s.wire(124, tk["out_h"][1], 124, YR)
t3a = s.triode("V3A", "12AX7", 136, YR)
s.wire(124, YR, t3a["g"][0], YR)
s.junction(124, YR)
s.sym("R", "RGR1", "220k", 124, YR + 3.81, ly=0.8)
s.gnd(124, YR + 7.62)
s.plate_load("RLR1", "100k", t3a["p"], "B+4")
s.wire(136, YR + 7.62, 136, YR + 9)
s.shunt_rc("RKR1", "1.5k", "CKR1", "25u", 136, YR + 9)
# recovery plate -> CCR1 -> Reverb control -> 470k mixer -> MIXG
teer = YR - 7.62 - 3.48
s.junction(136, teer)
s.wire(136, teer, 144, teer)
cl, cr = s.series_h("C", "CCR1", ".003u", 150, teer)
s.wire(144, teer, cl, teer)
s.wire(cr, teer, 160, teer)
s.sym("POT", "VRREV", "100k rev", 160, teer + 3.81)
s.gnd(160, teer + 7.62)
s.wire(165.08, teer + 3.81, 172, teer + 3.81)
s.junction(172, teer + 3.81)
l, r = s.series_h("R", "RMR", "470k", 178, teer + 3.81)
s.wire(172, teer + 3.81, l, teer + 3.81)
s.wire(r, teer + 3.81, 190, teer + 3.81)
s.glabel("MIXG", 190, teer + 3.81, 0)
# reverb footswitch shorts the recovered signal to ground
jrev = s.jack("JREV", "reverb fsw", 200, YR + 8)
s.wire(172, teer + 3.81, 172, jrev["tip"][1])
s.wire(172, jrev["tip"][1], jrev["tip"][0], jrev["tip"][1])
s.wire(jrev["sleeve"][0], jrev["sleeve"][1], 190, jrev["sleeve"][1])
s.gnd(190, jrev["sleeve"][1])

# ============================ BIAS SUPPLY (band 2, right) ============
YB = 120
s.text("Bias supply — 100 k feed off the HT winding, silicon rectifier, 25 µF can, 22 k bleeder → -34 V",
       250, 110, 1.3)
s.glabel("-34V", 252, YB, 180)
s.wire(256, YB, 275.92, YB)
s.junction(260, YB)
s.sym("C", "CB3", "25u", 260, YB + 3.81, ly=0.8)
s.gnd(260, YB + 7.62)
s.junction(268, YB)
s.sym("R", "RB2", "22k", 268, YB + 3.81, ly=0.8)
s.gnd(268, YB + 7.62)
s.sym("DIODE_SS", "DB1", "Si", 281, YB, lx=-2.0, ly=-5.4)
s.wire(286.08, YB, 292, YB)
l, r = s.series_h("R", "RB1", "100k 5%", 298, YB)
s.wire(292, YB, l, YB)
s.wire(r, YB, 306, YB)
s.glabel("HT_B", 306, YB, 0)

# ============================ MAINS (band 2, right) ==================
YMN = 152
s.text("Mains — fuse, AC switch, and the period ground switch (not in modern builds)", 250, 142, 1.3)
s.glabel("AC LINE", 252, YMN, 180)
s.sym("FUSE", "F1", "1A SB", 266, YMN)
s.wire(256, YMN, 260.92, YMN)
s.sym("SWITCH", "SW1", "SPST", 282, YMN)
s.wire(271.08, YMN, 276.92, YMN)
s.wire(287.08, YMN, 292, YMN)
s.glabel("MAINS", 292, YMN, 0)
s.glabel("AC LINE", 252, YMN + 12, 180)
s.sym("C", "CDEATH", ".047u", 266, YMN + 12, rot=90, lx=-3.2, ly=-6.2)
s.wire(256, YMN + 12, 262.19, YMN + 12)
s.sym("SWITCH", "SW2", "SPDT", 280, YMN + 12)
s.wire(269.81, YMN + 12, 274.92, YMN + 12)
s.wire(285.08, YMN + 12, 290, YMN + 12)
s.gnd(290, YMN + 12)

# ============================ MIXER / DRIVER / PI / OUTPUT (band 3) ==
YM = 194
s.text("Dry + reverb mixer, driver stage with the feedback loop, split-load phase inverter, 6V6 output",
       12, 164, 1.5)
# dry path: 3.3M mixer with a 10 pF bright cap across it
s.glabel("DRY", 12, YM - 10, 180)
s.wire(16, YM - 10, 20, YM - 10)
s.junction(20, YM - 10)
l, r = s.series_h("R", "RMIX", "3.3M", 26, YM - 10)
s.wire(20, YM - 10, l, YM - 10)
s.wire(r, YM - 10, 36, YM - 10)
s.wire(20, YM - 10, 20, YM - 20)
cl, cr = s.series_h("C", "CMIX", "10p", 26, YM - 20)
s.wire(20, YM - 20, cl, YM - 20)
s.wire(cr, YM - 20, 36, YM - 20)
s.wire(36, YM - 20, 36, YM - 10)
s.junction(36, YM - 10)
# the reverb mixer arrives on MIXG; both meet at the driver grid
s.glabel("MIXG", 12, YM, 180)
s.wire(16, YM, 36, YM)
s.wire(36, YM - 10, 36, YM)
s.junction(36, YM)
t3b = s.triode("V3B", "12AX7", 52, YM)
s.wire(36, YM, t3b["g"][0], YM)
s.plate_load("RLD1", "100k", t3b["p"], "B+4")
# cathode: 1.5k bypassed by 25u, sitting on the unbypassed 47 ohm the loop closes on
s.wire(52, YM + 7.62, 52, YM + 9)
s.sym("R", "RKD1", "1.5k", 52, YM + 12.81, ly=-0.4)
s.sym("C", "CKD1", "25u", 59.62, YM + 12.81, ly=-0.4)
s.wire(52, YM + 9, 59.62, YM + 9)
s.wire(52, YM + 16.62, 59.62, YM + 16.62)
s.junction(52, YM + 16.62)
s.junction(59.62, YM + 16.62)
s.sym("R", "RKD2", "47", 52, YM + 20.43, ly=0.8)
s.gnd(52, YM + 24.24)
# negative feedback from the speaker onto that 47 ohm
s.glabel("SPKR", 28, YM + 16.62, 180)
l, r = s.series_h("R", "RNFB", "2.7k", 38, YM + 16.62)
s.wire(32, YM + 16.62, l, YM + 16.62)
s.wire(r, YM + 16.62, 52, YM + 16.62)
# driver plate -> CC2 -> phase-inverter grid
teem = YM - 7.62 - 3.48
s.junction(52, teem)
s.wire(52, teem, 60, teem)
cl, cr = s.series_h("C", "CC2", ".02u", 66, teem)
s.wire(60, teem, cl, teem)
s.wire(cr, teem, 78, teem)
s.wire(78, teem, 78, YM)
# split-load (cathodyne) inverter V4B
t4b = s.triode("V4B", "12AX7", 92, YM)
s.junction(78, YM)
s.wire(78, YM, t4b["g"][0], YM)
s.plate_load("RLPI", "56k", t4b["p"], "B+4")
s.sym("R", "RGPI", "1M", 78, YM + 3.81, lx=-8.6)
s.wire(78, YM + 7.62, 78, YM + 17.62)
s.wire(78, YM + 17.62, 92, YM + 17.62)
s.wire(92, YM + 7.62, 92, YM + 10)
s.sym("R", "RKPI", "1k", 92, YM + 13.81, lx=-8.6)
s.junction(92, YM + 17.62)
s.sym("R", "RTAIL", "56k", 92, YM + 21.43, lx=-8.6, ly=0.8)
s.gnd(92, YM + 25.24)
# inverter plate / cathode -> 0.1u couplers -> the two 6V6 grids
s.junction(92, teem)
s.wire(92, teem, 102, teem)
cl, cr = s.series_h("C", "C1", ".1u", 108, teem)
s.wire(102, teem, cl, teem)
s.wire(cr, teem, 120, teem)
s.wire(120, teem, 120, YM - 16)
s.junction(92, YM + 10)
s.wire(92, YM + 10, 102, YM + 10)
cl, cr = s.series_h("C", "C2", ".1u", 108, YM + 10)
s.wire(102, YM + 10, cl, YM + 10)
s.wire(cr, YM + 10, 120, YM + 10)
s.wire(120, YM + 10, 120, YM + 22)

# --- 6V6GT pair, fixed-biased through 220k 5% leaks, screens straight to B+2
for gy, vref, glref in ((YM - 16, "V5", "RGL1"), (YM + 22, "V6", "RGL2")):
    s.wire(120, gy, 132, gy)
    s.junction(132, gy)
    s.sym("R", glref, "220k 5%", 132, gy + 3.81, ly=0.8)
    s.wire(132, gy + 7.62, 132, gy + 10.16)
    s.glabel("-34V", 132, gy + 10.16, 270)
    p = s.pentode(vref, "6V6GT", 160, gy)
    s.wire(132, gy, p["g1"][0], gy)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6.4, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 6.4, p["g2"][1], 0)
    s.gnd(160, p["k"][1])

# --- output transformer TR2 + speaker
s.sym("OT_PP", "TR2", "125A10B", 200, 199)
s.wire(160, YM - 24.255, 160, 166)          # V5 plate up and across
s.wire(160, 166, 191.11, 166)
s.wire(191.11, 166, 191.11, 193.92)
s.wire(160, YM + 13.745, 182, YM + 13.745)  # V6 plate across and up
s.wire(182, YM + 13.745, 182, 204.08)
s.wire(182, 204.08, 191.11, 204.08)
s.wire(191.11, 199, 187, 199)
s.wire(187, 199, 187, 195)
s.glabel("B+1", 187, 195, 90)
s.wire(208.89, 196.46, 214, 196.46)
s.glabel("SPKR", 214, 196.46, 0)
s.wire(208.89, 201.54, 214, 201.54)
s.gnd(214, 201.54)
jext = s.jack("JEXT", "ext spkr", 236, 212)
s.glabel("SPKR", 218, jext["tip"][1], 180)
s.wire(222, jext["tip"][1], jext["tip"][0], jext["tip"][1])
s.wire(jext["sleeve"][0], jext["sleeve"][1], 226, jext["sleeve"][1])
s.gnd(226, jext["sleeve"][1])
s.note("125A10B secondary drives the speaker and the parallel external-speaker jack; the 2.7 kΩ feedback leaves this node")

# ============================ TREMOLO OSCILLATOR (band 4) ============
YT = 246
s.text("Tremolo oscillator (V4A) — a running phase-shift oscillator:", 12, 230, 1.4)
s.text("its printed pins are dynamic averages, not a static DC point,", 12, 234, 1.4)
s.text("so it is a documented netlist exclusion (see notes.md).", 12, 238, 1.4)
t4a = s.triode("V4A", "12AX7", 76, YT)
s.plate_load("RTOP", "220k", t4a["p"], "B+2")
# cathode: 3.3k || 25u, with the phase-shift ladder's last resistor returning here
s.wire(76, YT + 7.62, 76, YT + 9)
s.sym("R", "RKTO", "3.3k", 76, YT + 12.81, lx=-8.6, ly=0.8)
s.sym("C", "CKTO", "25u", 83.62, YT + 12.81)
s.wire(76, YT + 9, 83.62, YT + 9)
s.wire(76, YT + 16.62, 83.62, YT + 16.62)
s.gnd(76, YT + 16.62)
s.junction(76, YT + 9)
# phase-shift ladder: plate -> CTO1 - RTO1 - CTO2 - RTO2 - CTO3 -> grid
teet = YT - 7.62 - 3.48
s.junction(76, teet)
s.wire(76, teet, 88, teet)
s.wire(88, teet, 88, YT + 26)
cl, cr = s.series_h("C", "CTO1", ".02u", 82, YT + 26)
s.wire(88, YT + 26, cr, YT + 26)
s.wire(cl, YT + 26, 74, YT + 26)
s.junction(74, YT + 26)
s.sym("R", "RTO1", "1M", 74, YT + 29.81, ly=0.8)
s.gnd(74, YT + 33.62)
cl, cr = s.series_h("C", "CTO2", ".05u", 66, YT + 26)
s.wire(74, YT + 26, cr, YT + 26)
s.wire(cl, YT + 26, 58, YT + 26)
s.junction(58, YT + 26)
s.sym("R", "RTO2", "1M", 58, YT + 14)
s.wire(58, YT + 17.81, 58, YT + 26)
s.wire(58, YT + 10.19, 58, YT + 9)
s.wire(58, YT + 9, 76, YT + 9)
cl, cr = s.series_h("C", "CTO3", ".01u", 50, YT + 26)
s.wire(58, YT + 26, cr, YT + 26)
s.wire(cl, YT + 26, 42, YT + 26)
s.junction(42, YT + 26)
s.sym("R", "RSPD", "100k", 42, YT + 29.81, lx=-8.6, ly=0.8)
s.sym("POT", "VRSPD", "3M speed", 42, YT + 37.43)
s.gnd(42, YT + 41.24)
# Speed pot is wired as a rheostat — wiper tied back to its top lug
s.wire(47.08, YT + 37.43, 51, YT + 37.43)
s.wire(51, YT + 37.43, 51, YT + 33.62)
s.wire(51, YT + 33.62, 42, YT + 33.62)
s.junction(42, YT + 33.62)
s.wire(42, YT + 26, 42, YT)
s.wire(42, YT, t4a["g"][0], YT)
# oscillator output -> 1M series, 0.02u shunt, 0.1u coupler, Intensity -> bias line
s.junction(88, teet)
s.wire(88, teet, 100, teet)
s.junction(100, teet)
l, r = s.series_h("R", "RTOUT", "1M", 106, teet)
s.wire(100, teet, l, teet)
s.wire(r, teet, 116, teet)
s.junction(116, teet)
s.sym("C", "CTO4", ".02u", 116, teet + 3.81, ly=0.8)
s.gnd(116, teet + 7.62)
cl, cr = s.series_h("C", "CINT", ".1u", 124, teet)
s.wire(116, teet, cl, teet)
s.wire(cr, teet, 134, teet)
s.sym("POT", "VRINT", "250k-L int", 134, teet + 3.81)
s.gnd(134, teet + 7.62)
s.wire(139.08, teet + 3.81, 148, teet + 3.81)
s.glabel("-34V", 148, teet + 3.81, 0)
# vibrato footswitch grounds the oscillator output
jvib = s.jack("JVIB", "vibrato fsw", 166, YT + 4)
s.wire(100, teet, 100, jvib["tip"][1])
s.wire(100, jvib["tip"][1], jvib["tip"][0], jvib["tip"][1])
s.wire(jvib["sleeve"][0], jvib["sleeve"][1], 156, jvib["sleeve"][1])
s.gnd(156, jvib["sleeve"][1])

s.write(OUT)
print(f"wrote {OUT}")
