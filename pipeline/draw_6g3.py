#!/usr/bin/env python3
"""Generate amps/6g3/schematic.kicad_sch from the stage-template library.

Values per the published 6G3 'Deluxe' drawing (I-FA) — see amps/6g3/meta.yaml.
The sheet reads: the two channel preamps (Normal, Bright) stacked at the top
left with their volume and tone controls, the driver stage in the middle, the
long-tailed-pair phase inverter and 6V6 output at the right, the bias-vary
tremolo oscillator along the bottom left, and the power and bias supplies at
the bottom right. Drawn on A3 so every block clears its neighbours.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
B+1 = +375 (reservoir, output-transformer centre tap, tremolo oscillator),
B+2 = +365 (6V6 screens), B+3 = +325 (phase-inverter plates),
B+4 = +270 (preamp); -26 V is the fixed-bias line. The drawing prints the
first bottle 7025 — the low-noise 12AX7. Heaters, PT primary/mains, the pilot
lamp and the chassis switches are omitted here (annotation layer) — see
netlist.cir, meta.yaml, and the board layout (layout.yaml).

The tremolo oscillator IS drawn: the schematic documents the whole circuit.
Its DC operating point alone is excluded from netlist.cir (a running
phase-shift oscillator has no static bias point) — see amps/6g3/notes.md.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g3" / "schematic.kicad_sch"
s = Sch()

GB = 40          # input grid-bus x
VX = 52          # channel-input triode x


def cathode_rc(rref, rval, cref, cval, x, ytop, dx=7.62):
    """Cathode R || C to ground — as Sch.shunt_rc, but with the resistor's
    label pushed clear of the join wire that runs across the top of the pair."""
    s.sym("R", rref, rval, x, ytop + 3.81, lx=-9.2, ly=0.0)
    s.sym("C", cref, cval, x + dx, ytop + 3.81)
    s.wire(x, ytop, x + dx, ytop)
    s.wire(x, ytop + 7.62, x + dx, ytop + 7.62)
    s.gnd(x, ytop + 7.62)


def input_stage(y, j1, j2, r1, r2, rleak, vref, vval):
    """Two-jack channel input: 68k stoppers -> grid (1M leak) -> triode. The
    cathode is left on a KIN label: both halves share ONE cathode RC (drawing)."""
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(16, y - 4, l, y - 4)
    s.wire(r, y - 4, GB, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(16, y + 4, l, y + 4)
    s.wire(r, y + 4, GB, y + 4)
    s.wire(GB, y - 4, GB, y + 4)
    s.junction(GB, y)
    s.sym("R", rleak, "1M", GB, y + 3.81 + 4)
    s.gnd(GB, y + 7.62 + 4)
    t = s.triode(vref, vval, VX, y)
    s.wire(GB, y, t["g"][0], y)
    s.wire(VX, y + 7.62, VX, y + 11)
    s.glabel("KIN", VX, y + 11, 270)
    return t


def plate_load_220k(ref, plate, shunt=None):
    """220k plate load from a channel-input plate up to B+4, optionally with the
    treble-shunt capacitor across it (the Normal channel's .003)."""
    x, py = plate
    top = py - 3.48
    s.wire(x, py, x, top)
    s.sym("R", ref, "220k", x, top - 3.81)
    s.wire(x, top - 7.62, x, top - 10.16)
    s.glabel("B+4", x, top - 10.16, 90)
    if shunt:
        sx = x - 8
        s.sym("C", shunt, ".003u", sx, top - 3.81, lx=-9.0, ly=-3.2)
        s.wire(sx, top, x, top)
        s.wire(sx, top - 7.62, x, top - 7.62)
        s.junction(x, top)
        s.junction(x, top - 7.62)
    return top


def tone_volume(tee, cc, cval, vrv, vrt, ccut, cutval, cbright, mixer):
    """Plate tee -> .02 coupler -> volume pot; the 1M-A tone control hangs on the
    same node with its wiper fed from it, one end through a capacitor to ground
    and the other through a 500 pF back to the volume wiper. The volume wiper
    then feeds a 220k mixing resistor into the driver grid."""
    s.junction(VX, tee)
    s.wire(VX, tee, 60, tee)
    cl, cr = s.series_h("C", cc, cval, 66, tee)
    s.wire(60, tee, cl, tee)
    s.wire(cr, tee, 76, tee)                        # node A: volume top + tone wiper
    s.sym("POT", vrv, "1M-A", 76, tee + 3.81, lx=-10.5, ly=2.6)
    s.gnd(76, tee + 7.62)
    s.junction(76, tee)
    # tone pot: rot 180 puts its wiper on the left, fed from node A
    s.wire(76, tee, 86.92, tee)
    s.sym("POT", vrt, "1M-A", 92, tee, rot=180, lx=3.2, ly=-3.2)
    # upper lug -> cut capacitor -> ground
    s.wire(92, tee - 3.81, 92, tee - 8)
    s.sym("C", ccut, cutval, 92, tee - 11.81, lx=2.8, ly=-3.2)
    s.glabel("GND", 92, tee - 15.62, 90)
    # lower lug -> 500 pF -> volume wiper
    s.sym("C", cbright, "500p", 86.5, tee + 3.81, rot=90, lx=-3.2, ly=5.0)
    cl, cr = 82.69, 90.31
    s.wire(81.08, tee + 3.81, cl, tee + 3.81)
    s.wire(cr, tee + 3.81, 92, tee + 3.81)
    s.junction(81.08, tee + 3.81)
    # volume wiper -> 220k mixing resistor -> driver grid
    s.wire(81.08, tee + 3.81, 81.08, tee + 14)
    ml, mr = s.series_h("R", mixer, "220k", 104, tee + 14)
    s.wire(81.08, tee + 14, ml, tee + 14)
    s.wire(mr, tee + 14, 126, tee + 14)
    s.glabel("MIXG", 126, tee + 14, 0)


# ============================ TITLE ==================================
s.text("6G3 — Brown Deluxe-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts",
       26, 18, 2.2)
s.text("Rails: B+1 +375 (reservoir · OT centre tap · tremolo oscillator) · B+2 +365 screens · B+3 +325 phase inverter · B+4 +270 preamp · bias -26 V",
       26, 23, 1.3)
s.text("Heaters, PT primary/mains, pilot lamp, chassis switches and the tremolo footswitch jack are omitted here — see netlist.cir, meta.yaml, layout.yaml. The drawing prints the first bottle 7025, a low-noise 12AX7.",
       26, 27, 1.3)

# ============================ NORMAL CHANNEL =========================
YN = 62
s.text("Normal channel", 12, 48, 1.6)
t1a = input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RG1", "V1A", "7025")
teeN = plate_load_220k("RL1", t1a["p"], shunt="C3")
tone_volume(teeN, "C1", ".02u", "VR1", "VR2", "C5", ".01u", "C6", "R5")

# ============================ BRIGHT CHANNEL =========================
YB = 104
s.text("Bright channel — no treble shunt across the plate load", 12, 90, 1.6)
t1b = input_stage(YB, "BRIGHT 1", "BRIGHT 2", "R3n", "R4n", "RG2", "V1B", "7025")
teeB = plate_load_220k("RL2", t1b["p"])
tone_volume(teeB, "C2", ".02u", "VR3", "VR4", "C7", ".02u", "C8", "R6")

# --- one 1.5k / 25 uF pair serves BOTH 7025 halves --------------------
s.glabel("KIN", 96, 128, 90)
s.wire(96, 128, 96, 132)
cathode_rc("RK1", "1.5k", "C10", "25u", 96, 132)
s.text("Both 7025 halves share this cathode RC", 112, 133, 1.3)

# ============================ DRIVER =================================
YD = 82
s.text("Driver — the 100k plate load returns to B+4 through a 15k; the coupler is taken from their junction",
       134, 44, 1.4)
s.glabel("MIXG", 134, YD, 180)
t2a = s.triode("V2A", "12AX7", 150, YD)
s.wire(138, YD, t2a["g"][0], YD)
s.wire(150, YD - 7.62, 150, YD - 10)
s.sym("R", "RL3", "100k", 150, YD - 13.81)
s.wire(150, YD - 17.62, 150, YD - 20)             # J2 junction
s.junction(150, YD - 20)
s.sym("R", "RD4", "15k", 150, YD - 23.81)
s.wire(150, YD - 27.62, 150, YD - 30)
s.glabel("B+4", 150, YD - 30, 90)
s.wire(150, YD + 7.62, 150, YD + 9)
cathode_rc("RK2", "1.5k", "C4", "25u", 150, YD + 9)
# J2 -> the phase inverter's hot grid, through the .01 coupler
s.wire(150, YD - 20, 186, YD - 20)
s.wire(186, YD - 20, 186, 100)

# ============================ PHASE INVERTER (LTP) ===================
XPI = 258
YPH = 100          # hot half
YPB = 136          # cold half
JY = 116           # tail junction
s.text("Long-tailed-pair phase inverter", 196, 86, 1.6)
s.sym("C", "C9", ".01u", 232, YPH, rot=90, lx=-3.2, ly=-6.2)
s.wire(186, YPH, 228.19, YPH)
s.wire(235.81, YPH, 250.38, YPH)
t3a = s.triode("V3A", "12AX7", XPI, YPH)
t3b = s.triode("V3B", "12AX7", XPI, YPB)
s.plate_load("RLA", "82k 5%", t3a["p"], "B+3")
s.plate_load("RLB", "100k 5%", t3b["p"], "B+3")
# cathodes join on a left stub; 820 from there to the tail junction
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, 250, YPH + 10)
s.wire(XPI, YPB - 7.62, XPI, YPB - 10)
s.wire(XPI, YPB - 10, 250, YPB - 10)
s.wire(250, YPH + 10, 250, YPB - 10)
s.junction(250, JY)
tl, tr = s.series_h("R", "RTAIL", "820", 244.5, JY)
s.wire(250, JY, tr, JY)
s.wire(238, JY, tl, JY)                            # JPI, the tail junction
s.junction(238, JY)
# tail junction -> 6.8k -> feedback node -> 1.5k -> ground; 56k from the speaker
tl, tr = s.series_h("R", "RT2", "6.8k", 228, JY)
s.wire(tr, JY, 238, JY)
s.wire(tl, JY, 220, JY)                            # NFB node
s.junction(220, JY)
s.sym("R", "RNF1", "1.5k", 220, JY + 3.81, lx=3.2, ly=2.0)
s.gnd(220, JY + 7.62)
nl, nr = s.series_h("R", "RNFB", "56k", 206, JY)
s.wire(nr, JY, 220, JY)
s.wire(196, JY, nl, JY)
s.glabel("SPKR", 192, JY, 180)
# hot grid leak: JPI -> 1M -> hot grid
s.sym("R", "RGA", "1M", 238, JY - 8, lx=-9.4)
s.wire(238, JY - 4.19, 238, JY)
s.wire(238, JY - 11.81, 238, YPH)
s.junction(238, YPH)
# cold grid leak: JPI -> 1M -> cold grid
s.sym("R", "RGB", "1M", 234, JY + 8, lx=2.8)
s.wire(234, JY + 4.19, 234, JY)
s.junction(234, JY)
s.wire(234, JY + 11.81, 234, YPB)
s.wire(234, YPB, 250.38, YPB)
s.junction(234, YPB)
s.junction(250.38, YPB)
# feedback coupler: NFB node -> .1 uF / 200 V -> cold grid
s.wire(220, JY, 216, JY)
s.wire(216, JY, 216, YPB)
cl, cr = s.series_h("C", "C14", ".1u", 224, YPB)
s.wire(216, YPB, cl, YPB)
s.wire(cr, YPB, 234, YPB)

# ============================ OUTPUT COUPLERS + 6V6 ==================
teeA = YPH - 7.62 - 3.48
teeC = YPB - 7.62 - 3.48
s.junction(XPI, teeA)
s.wire(XPI, teeA, 272, teeA)
s.junction(XPI, teeC)
s.wire(XPI, teeC, 272, teeC)
# 100 pF damping capacitor across the inverter plates
s.junction(268, teeA)
s.junction(268, teeC)
s.wire(268, teeA, 268, 103.09)
s.sym("C", "C15", "100p", 268, 106.9)
s.wire(268, 110.71, 268, teeC)
cl, cr = s.series_h("C", "C12", ".1u", 284, teeA)
s.wire(272, teeA, cl, teeA)
s.wire(cr, teeA, 296, teeA)
s.wire(296, teeA, 296, 80)
cl, cr = s.series_h("C", "C13", ".1u", 284, teeC)
s.wire(272, teeC, cl, teeC)
s.wire(cr, teeC, 296, teeC)
s.wire(296, teeC, 296, 144)

XO = 320
s.text("Output pair — grounded cathodes, fixed bias", 300, 60, 1.5)
for gy, vref, glref in [(80, "V4", "RG4"), (144, "V5", "RG5")]:
    s.wire(296, gy, XO - 7.62, gy)
    p = s.pentode(vref, "6V6GT", XO, gy)
    s.junction(302, gy)
    s.sym("R", glref, "220k 5%", 302, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(302, gy + 7.62, 302, gy + 10.16)
    s.glabel("-26V", 302, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 6, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# ---- output transformer ---------------------------------------------
s.sym("OT_PP", "T2", "125A1A", 352, 112, lx=-6.35, ly=-14.5)
s.wire(XO, 71.745, XO, 68)
s.wire(XO, 68, 343.11, 68)
s.wire(343.11, 68, 343.11, 106.92)
s.wire(XO, 135.745, XO, 132)
s.wire(XO, 132, 338, 132)
s.wire(338, 132, 338, 117.08)
s.wire(338, 117.08, 343.11, 117.08)
s.wire(343.11, 112, 334, 112)
s.glabel("B+1", 330, 112, 180)
s.wire(360.89, 109.46, 364, 109.46)
s.glabel("SPKR", 364, 109.46, 0)
s.wire(360.89, 114.54, 364, 114.54)
s.glabel("GND", 364, 114.54, 0)

# ============================ TREMOLO OSCILLATOR =====================
YT = 215
PT_ = YT - 11.1                                    # plate tee (y = 203.9)
s.text("Bias-vary tremolo — V2B phase-shift oscillator; the Intensity control sits in the -26 V bias line itself",
       26, 174, 1.5)
s.text("Its DC point alone is excluded from netlist.cir — a running oscillator has no static operating point (notes.md)",
       26, 179, 1.3)
t2b = s.triode("V2B", "12AX7", 100, YT)
s.wire(100, YT - 7.62, 100, PT_)
s.sym("R", "RL4", "220k", 100, PT_ - 3.81)
s.wire(100, PT_ - 7.62, 100, PT_ - 10.16)
s.glabel("B+1", 100, PT_ - 10.16, 90)
s.junction(100, PT_)
# phase-shift ladder: plate -> .02 -> .01 -> .01 -> grid (drawn right to left)
cl, cr = s.series_h("C", "C16", ".02u", 90, PT_)
s.wire(cr, PT_, 100, PT_)
s.wire(80, PT_, cl, PT_)                           # node N3
s.junction(80, PT_)
cl, cr = s.series_h("C", "C17", ".01u", 70, PT_)
s.wire(cr, PT_, 80, PT_)
s.wire(60, PT_, cl, PT_)                           # node N1
s.junction(60, PT_)
cl, cr = s.series_h("C", "C18", ".01u", 50, PT_)
s.wire(cr, PT_, 60, PT_)
s.wire(40, PT_, cl, PT_)                           # node N2 -> grid
s.junction(40, PT_)
# N3: the Speed control, wired as a rheostat, and its 100k end resistor
s.sym("POT", "VR5", "3.5M-RA", 80, PT_ - 3.81, lx=8.0, ly=-8.6)
s.wire(85.08, PT_ - 3.81, 85.08, PT_ - 7.62)
s.wire(85.08, PT_ - 7.62, 80, PT_ - 7.62)
s.junction(80, PT_ - 7.62)
s.sym("R", "R9", "100k", 80, PT_ - 11.43)
s.glabel("GND", 80, PT_ - 15.24, 90)
s.text("Speed", 68, PT_ - 17.5, 1.3)
# N1: 1M returned to the cathode
s.sym("R", "R8", "1M", 60, PT_ - 3.81)
s.wire(60, PT_ - 7.62, 60, PT_ - 16)
s.wire(60, PT_ - 16, 30, PT_ - 16)
s.wire(30, PT_ - 16, 30, YT + 11)
s.wire(30, YT + 11, 100, YT + 11)
# N2: 1M grid leak to ground, then on to the grid
s.sym("R", "R7", "1M", 40, PT_ - 3.81)
s.glabel("GND", 40, PT_ - 7.62, 90)
s.wire(40, PT_, 36, PT_)
s.wire(36, PT_, 36, YT)
s.wire(36, YT, t2b["g"][0], YT)
# cathode 2.7k || 25 uF
s.wire(100, YT + 7.62, 100, YT + 11)
s.junction(100, YT + 11)
cathode_rc("RK3", "2.7k", "C11", "25u", 100, YT + 11)
# oscillator output: plate -> 220k -> .1 uF -> Intensity -> the bias line
ml, mr = s.series_h("R", "R10", "220k", 120, PT_)
s.wire(100, PT_, ml, PT_)
s.wire(mr, PT_, 130, PT_)
cl, cr = s.series_h("C", "C19", ".1u", 136, PT_)
s.wire(130, PT_, cl, PT_)
s.wire(cr, PT_, 146, PT_)
s.sym("POT", "VR6", "250k-L", 146, PT_ + 3.81)
s.wire(146, PT_ + 7.62, 146, PT_ + 10.16)
s.glabel("-26V", 146, PT_ + 10.16, 270)
s.wire(151.08, PT_ + 3.81, 157, PT_ + 3.81)
s.sym("C", "C20", ".05u", 157, PT_ + 7.62, lx=2.8, ly=-3.2)
s.gnd(157, PT_ + 11.43)
s.text("Intensity", 140, PT_ - 5, 1.3)

# ============================ POWER SUPPLY ===========================
YPW = 222
BY = YPW + 6
s.text("Power supply — TR1 125P2A, 333-0-333 V, GZ34 full-wave; TR2 125A1A output transformer",
       196, 174, 1.5)
pt = s.pt("T1", "125P2A", 212, YPW, lx=-6.35, ly=-12.5)
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
s.glabel("HT_A", 244, YPW - 14, 90)
s.wire(244, YPW - 14, 244, YPW - 11.5)
s.diode_tube("V6A", "GZ34", 244, YPW - 3.88, lx=-11.8)
s.glabel("HT_B", 256, YPW - 14, 90)
s.wire(256, YPW - 14, 256, YPW - 11.5)
s.diode_tube("V6B", "GZ34", 256, YPW - 3.88, lx=6.2)
s.wire(244, YPW + 3.74, 244, BY)
s.wire(256, YPW + 3.74, 256, BY)
s.wire(244, BY, 268, BY)
s.junction(256, BY)
# rail chain: B+1 -1k/2W-> B+2 -10k/1W-> B+3 -27k/1W-> B+4
s.junction(262, BY)
s.sym("C", "C21", "16u", 262, BY + 3.81)
s.gnd(262, BY + 7.62)
s.junction(268, BY)
s.wire(268, BY - 3.5, 268, BY)
s.glabel("B+1", 268, BY - 3.5, 90)
l, r = s.series_h("R", "RD1", "1k 2W", 274, BY)
s.wire(268, BY, l, BY)
s.wire(r, BY, 288, BY)
s.junction(282, BY)
s.wire(282, BY - 3.5, 282, BY)
s.glabel("B+2", 282, BY - 3.5, 90)
s.junction(286, BY)
s.sym("C", "C22", "16u", 286, BY + 3.81)
s.gnd(286, BY + 7.62)
l, r = s.series_h("R", "RD2", "10k 1W", 294, BY)
s.wire(288, BY, l, BY)
s.wire(r, BY, 308, BY)
s.junction(302, BY)
s.wire(302, BY - 3.5, 302, BY)
s.glabel("B+3", 302, BY - 3.5, 90)
s.junction(306, BY)
s.sym("C", "C23", "16u", 306, BY + 3.81)
s.gnd(306, BY + 7.62)
l, r = s.series_h("R", "RD3", "27k 1W", 314, BY)
s.wire(308, BY, l, BY)
s.wire(r, BY, 328, BY)
s.junction(322, BY)
s.wire(322, BY - 3.5, 322, BY)
s.glabel("B+4", 322, BY - 3.5, 90)
s.sym("C", "C24", "8u", 328, BY + 3.81)
s.gnd(328, BY + 7.62)

# ============================ BIAS SUPPLY ============================
YBI = 254
s.text("Bias supply — a 100k feed off one HT leg, a rectifier, 25 uF and a 22k bleeder: a fixed -26 V, no trimmer",
       196, 246, 1.4)
s.glabel("HT_B", 196, YBI, 180)
l, r = s.series_h("R", "R11", "100k 5%", 210, YBI)
s.wire(200, YBI, l, YBI)
s.wire(r, YBI, 219.92, YBI)
s.sym("DIODE_SS", "D1", "selenium", 225, YBI, lx=-3.4, ly=-5.6)
s.wire(230.08, YBI, 236, YBI)
s.junction(236, YBI)
s.sym("C", "C25", "25u", 236, YBI + 3.81)
s.gnd(236, YBI + 7.62)
s.wire(236, YBI, 246, YBI)
s.junction(246, YBI)
s.sym("R", "R12", "22k 5%", 246, YBI + 3.81)
s.gnd(246, YBI + 7.62)
s.wire(246, YBI, 258, YBI)
s.glabel("-26V", 258, YBI, 0)

s.write(OUT, [], paper="A3")
print(f"wrote {OUT}")
