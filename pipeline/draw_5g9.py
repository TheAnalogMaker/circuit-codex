#!/usr/bin/env python3
"""Generate amps/5g9/schematic.kicad_sch from the stage-template library.

Values per the published 5G9 'Tremolux' drawing (B-EI) — see amps/5g9/meta.yaml.
The sheet reads: the two channel preamps (Inst., Mic.) at the top left on one
12AY7, their volume controls and the shared tone control in the middle, the
long-tailed-pair phase inverter and the 6V6GT output at the right, the tremolo
along the bottom left, and the power and bias supplies at the bottom right.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
B+1 = +370 (reservoir, output-transformer centre tap), B+2 = +368 (post-choke:
the 6V6 screens through their own 470 Ohm resistors, and both halves of the
tremolo bottle), B+3 = +310 (12AY7 plate loads and the phase-inverter plate-load
junction); -28 V is the fixed-bias line and -69 V the bias rectifier's output.
Heaters, the pilot lamp, the mains switch/fuse/cap and the tremolo footswitch
jack are omitted here (annotation layer) — see netlist.cir, meta.yaml, and the
board layout (layout.yaml).

TWO drawing facts worth stating, because both look like mistakes and are not:

  * The volume controls are driven at their WIPERS. Each 12AY7 plate goes
    through its own 0.1 uF straight to a 1 M pot's wiper; one end of each pot is
    grounded and the other end joins the shared mixing node that feeds the
    inverter, with the tone control's wiper on that node too. Turned toward the
    grounded end a pot shorts its own channel to ground against the plate's
    source impedance, which is what makes it a volume control. Both the
    schematic page and the layout page say this: on the layout the centre lug
    carries the coupling cap and the .0005, the left lug goes to the pot case,
    and the right lugs of both volume pots and the tone pot's centre lug are one
    node.

  * The tremolo bottle is a phase-shift oscillator DIRECT-COUPLED to a cathode
    follower: V3A's plate is V3B's grid, V3B's plate sits on the same +368 V
    node as the 6V6 screens, and its 220 k cathode resistor is the load the
    0.1 uF output coupler is taken from. Neither half has a static operating
    point, so both are excluded from netlist.cir — the schematic still documents
    the whole circuit. See amps/5g9/notes.md.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5g9" / "schematic.kicad_sch"
s = Sch()

GB = 40          # input grid-bus x
VX = 52          # 12AY7 x
XV = 92          # volume-pot column (and the mixing node)
XT = 78          # tone-pot column


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
    cathode is left on a KAY label: both halves share ONE cathode RC (drawing)."""
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(12, y - 4, l, y - 4)
    s.wire(r, y - 4, GB, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(12, y + 4, l, y + 4)
    s.wire(r, y + 4, GB, y + 4)
    s.wire(GB, y - 4, GB, y + 4)
    s.junction(GB, y)
    s.sym("R", rleak, "1M", GB, y + 3.81 + 4)
    s.gnd(GB, y + 7.62 + 4)
    t = s.triode(vref, vval, VX, y)
    s.wire(GB, y, t["g"][0], y)
    s.wire(VX, y + 7.62, VX, y + 11)
    s.glabel("KAY", VX, y + 11, 270)
    return t


# ============================ TITLE ==================================
s.note('Rails: B+1 +370 (reservoir · OT centre tap) · B+2 +368 (post-choke: 6V6 screens through their own 470 Ω · 1 W, and both halves of the tremolo bottle) · B+3 +310 (12AY7 plate loads · phase-inverter plate-load junction) · bias line -28 V off a -69 V rectifier')
s.note('Each volume control is driven at its WIPER, one end grounded and the other on the shared mixing node — the drawing\'s own arrangement, on both its pages. The tone control\'s wiper sits on that same node.')
s.note('Heaters, PT primary/mains, fuse, pilot lamp, the mains capacitor and the tremolo footswitch jack are omitted here — see the netlist, the sources list and the board drawing. The tremolo bottle IS drawn; only its DC operating point is excluded from the netlist (see the circuit story).')

# ============================ INST. CHANNEL ==========================
YI = 62
teeI = YI - 11.10
s.text("Inst. channel", 12, 44, 1.6)
t1a = input_stage(YI, "INST 1", "INST 2", "R1n", "R2n", "RG1", "V1A", "12AY7")
s.plate_load("RL1", "100k", t1a["p"], "B+3")

# ============================ MIC. CHANNEL ===========================
YM = 104
teeM = YM - 11.10
s.caption("Mic. channel — the same stage; the two differ only at the panel", 12, 122, 1.5)
t1b = input_stage(YM, "MIC 1", "MIC 2", "R3n", "R4n", "RG2", "V1B", "12AY7")
s.plate_load("RL2", "100k", t1b["p"], "B+3")

# --- one 820 Ω / 25 µF pair serves BOTH 12AY7 halves -------------------
s.glabel("KAY", 64, 128, 90)
s.wire(64, 128, 64, 132)
cathode_rc("RK1", "820", "CK1", "25u", 64, 132)
s.text("Both 12AY7 halves share this cathode RC", 80, 133, 1.3)

# ============================ VOLUME + TONE ==========================
# Inst.: plate tee -> .1u -> VR1's WIPER. VR1's top lug is grounded and its
# bottom lug is the mixing node; VR2 is the same pot upside down, so the two
# grounded ends sit at the outside and the mixing node between them.
s.junction(VX, teeI)
s.wire(VX, teeI, 60, teeI)
cl, cr = s.series_h("C", "C1", ".1u", 66, teeI)
s.wire(60, teeI, cl, teeI)
s.wire(cr, teeI, XV - 5.08, teeI)
s.sym("POT", "VR1", "1M-A", XV, teeI, rot=180, lx=3.4, ly=-3.4)
s.wire(XV, teeI - 3.81, XV, teeI - 7.5)
s.gnd(XV, teeI - 7.5, 90)
s.wire(XV, teeI + 3.81, XV, 71.90)

s.junction(VX, teeM)
s.wire(VX, teeM, 60, teeM)
cl, cr = s.series_h("C", "C2", ".1u", 66, teeM)
s.wire(60, teeM, cl, teeM)
s.wire(cr, teeM, XV - 5.08, teeM)
s.sym("POT", "VR2", "1M-A", XV, teeM, rot=180, lx=3.4, ly=-3.4)
s.wire(XV, teeM - 3.81, XV, 71.90)
s.wire(XV, teeM + 3.81, XV, teeM + 7.5)
s.gnd(XV, teeM + 7.5)
s.junction(XV, 71.90)
s.text("mixing node", XV + 2.5, 70.4, 1.3)

# Tone: 500 pF in from the Inst. coupler node, .005 out to ground, wiper on the
# mixing node.
s.sym("POT", "VR3", "1M-A", XT, 71.90, lx=-10.6, ly=-3.4)
s.wire(XT + 5.08, 71.90, XV, 71.90)
s.wire(XT, 71.90 - 3.81, XT, 64.71)
s.sym("C", "C3", "500p", XT, 60.90, lx=2.8, ly=-3.2)
s.wire(XT, 57.09, XT, teeI)
s.junction(XT, teeI)
s.wire(XT, 71.90 + 3.81, XT, 79.09)
s.sym("C", "C4", ".005u", XT, 82.90, lx=2.8, ly=-3.2)
s.gnd(XT, 86.71)
s.text("Tone", XT - 12.5, 78.0, 1.3)

# mixing node -> .02 -> the inverter's hot grid
s.wire(XV, 71.90, 100, 71.90)
s.wire(100, 71.90, 100, YI)
cl, cr = s.series_h("C", "C5", ".02u", 110, YI)
s.wire(100, YI, cl, YI)
s.wire(cr, YI, 130, YI)

# ============================ PHASE INVERTER (LTP) ===================
XPI = 150
YPH = 62           # hot half
YPB = 98           # cold half
JY = 78            # tail junction
s.text("Long-tailed-pair phase inverter — no feedback loop", 100, 33, 1.5)
t2a = s.triode("V2A", "12AX7", XPI, YPH)
t2b = s.triode("V2B", "12AX7", XPI, YPB)
s.plate_load("RLA", "82k 5%", t2a["p"], "B+3")
s.plate_load("RLB", "100k 5%", t2b["p"], "B+3")
# cathodes join on a right-hand stub; 470 Ω from there to the tail junction.
# The cold half's cathode comes out UNDER its own bottle and up into the bus:
# the pin at YPB - 7.62 is the PLATE.
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, 142, YPH + 10)
s.wire(XPI, YPB + 7.62, 136, YPB + 7.62)
s.wire(136, YPB + 7.62, 136, YPB - 10)
s.wire(136, YPB - 10, 142, YPB - 10)
s.wire(142, YPH + 10, 142, YPB - 10)
s.junction(142, JY)
tl, tr = s.series_h("R", "RTAIL", "470", 136.5, JY)
s.wire(142, JY, tr, JY)
s.wire(130, JY, tl, JY)
s.junction(130, JY)
# tail junction -> 10k -> ground
tl, tr = s.series_h("R", "RT2", "10k", 120, JY)
s.wire(tr, JY, 130, JY)
s.wire(tl, JY, 112, JY)
s.gnd(112, JY, 180)
# hot grid leak: the tail junction -> 1M -> hot grid
s.sym("R", "RGA", "1M", 130, JY - 8, lx=-9.4)
s.wire(130, JY - 4.19, 130, JY)
s.wire(130, JY - 11.81, 130, YPH)
s.junction(130, YPH)
s.wire(130, YPH, t2a["g"][0], YPH)
# cold grid leak: the tail junction -> 1M -> cold grid
s.sym("R", "RGB", "1M", 126, JY + 8, lx=2.8)
s.wire(126, JY + 4.19, 126, JY)
s.junction(126, JY)
s.wire(126, JY + 11.81, 126, YPB)
s.wire(126, YPB, 142.38, YPB)
s.junction(126, YPB)
# the cold grid's signal reference: .1 uF / 200 V to ground
cl, cr = s.series_h("C", "C6", ".1u", 112, YPB)
s.wire(cr, YPB, 126, YPB)
s.wire(cl, YPB, 104, YPB)
s.gnd(104, YPB, 180)

# ============================ OUTPUT COUPLERS + 6V6 ==================
teeA = YPH - 11.10
teeC = YPB - 11.10
s.junction(XPI, teeA)
s.wire(XPI, teeA, 164, teeA)
s.junction(XPI, teeC)
s.wire(XPI, teeC, 164, teeC)
cl, cr = s.series_h("C", "C7", ".02u", 172, teeA)
s.wire(164, teeA, cl, teeA)
s.wire(cr, teeA, 184, teeA)
s.wire(184, teeA, 184, 44)
cl, cr = s.series_h("C", "C8", ".02u", 172, teeC)
s.wire(164, teeC, cl, teeC)
s.wire(cr, teeC, 184, teeC)
s.wire(184, teeC, 184, 110)

XO = 210
s.text("Output pair — grounded cathodes, fixed bias, its own screen resistors", 190, 30, 1.5)
for gy, vref, glref, rsref in [(44, "V4", "RG4", "RS1"), (110, "V5", "RG5", "RS2")]:
    s.wire(184, gy, XO - 7.62, gy)
    p = s.pentode(vref, "6V6GT", XO, gy)
    s.junction(190, gy)
    s.sym("R", glref, "220k", 190, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(190, gy + 7.62, 190, gy + 10.16)
    s.glabel("DEPTHW", 190, gy + 10.16, 270)
    gx, gy2 = p["g2"]
    s.wire(gx, gy2, gx + 4, gy2)
    l, r = s.series_h("R", rsref, "470 1W", gx + 10, gy2)
    s.wire(gx + 4, gy2, l, gy2)
    s.wire(r, gy2, gx + 18, gy2)
    s.glabel("B+2", gx + 18, gy2, 0)
    s.gnd(XO, p["k"][1])
s.text("Depth wiper", 193, 57.5, 1.3)

# ---- output transformer ---------------------------------------------
ot = s.ot_pp("T2", "108", 256, 77, lx=-6.35, ly=-14.5)
s.wire(XO, 35.745, XO, 32)
s.wire(XO, 32, ot["pri_a"][0], 32)
s.wire(ot["pri_a"][0], 32, ot["pri_a"][0], ot["pri_a"][1])
s.wire(XO, 101.745, XO, 106)
s.wire(XO, 106, 241, 106)
s.wire(241, 106, 241, ot["pri_b"][1])
s.wire(241, ot["pri_b"][1], ot["pri_b"][0], ot["pri_b"][1])
s.wire(ot["ct"][0], ot["ct"][1], 238, ot["ct"][1])
s.glabel("B+1", 238, ot["ct"][1], 180)
s.wire(ot["sec_h"][0], ot["sec_h"][1], 270, ot["sec_h"][1])
s.glabel("SPKR", 270, ot["sec_h"][1], 0)
s.wire(ot["sec_c"][0], ot["sec_c"][1], 270, ot["sec_c"][1])
s.glabel("GND", 270, ot["sec_c"][1], 0)

# ============================ TREMOLO ================================
YT = 215
PT_ = YT - 11.1                                    # oscillator plate tee
GRAIL = PT_ - 16                                   # the ladder's ground rail
s.text("Bias-vary tremolo — V3A phase-shift oscillator, DIRECT-COUPLED to the V3B cathode follower; the Depth control sits in the -28 V bias line itself",
       26, 176, 1.5)
s.text("Neither half has a static operating point, so both are excluded from the netlist — a DC pass says nothing about oscillation, rate or depth (see the circuit story)",
       26, 181, 1.3)
t3a = s.triode("V3A", "12AX7", 100, YT)
s.wire(100, YT - 7.62, 100, PT_)
s.sym("R", "RL3", "100k", 100, PT_ - 3.81)
s.wire(100, PT_ - 7.62, 100, PT_ - 10.16)
s.glabel("B+2", 100, PT_ - 10.16, 90)
s.junction(100, PT_)
# phase-shift ladder: plate -> .03 -> .01 -> .01 -> grid (drawn right to left)
cl, cr = s.series_h("C", "C9", ".03u", 90, PT_)
s.wire(cr, PT_, 100, PT_)
s.wire(80, PT_, cl, PT_)                           # node N3 (Speed)
s.junction(80, PT_)
cl, cr = s.series_h("C", "C10", ".01u", 70, PT_)
s.wire(cr, PT_, 80, PT_)
s.wire(60, PT_, cl, PT_)                           # node N1 (1M to the cathode)
s.junction(60, PT_)
cl, cr = s.series_h("C", "C11", ".01u", 50, PT_)
s.wire(cr, PT_, 60, PT_)
s.wire(40, PT_, cl, PT_)                           # node N2 -> grid
s.junction(40, PT_)
# N3: the Speed control from the ladder up to ground, its 100k across the
# wiper-to-ground section
s.sym("POT", "VR4", "2M", 80, PT_ - 3.81, lx=-9.6, ly=-3.4)
s.wire(80, PT_ - 7.62, 80, GRAIL)
s.junction(80, GRAIL)
l, r = s.series_h("R", "R9", "100k", 88, GRAIL)
s.wire(80, GRAIL, l, GRAIL)
s.wire(r, GRAIL, 95, GRAIL)
s.wire(95, GRAIL, 95, PT_ - 3.81)
s.wire(95, PT_ - 3.81, 85.08, PT_ - 3.81)
s.wire(80, GRAIL, 74, GRAIL)
s.gnd(74, GRAIL, 180)
s.text("Speed", 66, PT_ - 6.0, 1.3)
# N1: 1M returned to the cathode
s.sym("R", "R8", "1M", 60, PT_ - 3.81)
s.wire(60, PT_ - 7.62, 60, PT_ - 12)
s.wire(60, PT_ - 12, 30, PT_ - 12)
s.wire(30, PT_ - 12, 30, YT + 11)
s.wire(30, YT + 11, 100, YT + 11)
# N2: 1M grid leak to ground, then on to the grid
s.sym("R", "R7", "1M", 40, PT_ - 3.81)
s.wire(40, PT_ - 7.62, 40, PT_ - 12)
s.gnd(40, PT_ - 12, 90)
s.wire(40, PT_, 36, PT_)
s.wire(36, PT_, 36, YT)
s.wire(36, YT, t3a["g"][0], YT)
# oscillator cathode 1.8k || 25 uF
s.wire(100, YT + 7.62, 100, YT + 11)
s.junction(100, YT + 11)
cathode_rc("RK3", "1.5k", "CK3", "25u", 100, YT + 11)
# V3A plate -> V3B grid, direct
s.wire(100, PT_, 118, PT_)
s.wire(118, PT_, 118, YT)
t3b = s.triode("V3B", "12AX7", 140, YT)
s.wire(118, YT, t3b["g"][0], YT)
s.wire(140, YT - 7.62, 140, 196)
s.glabel("B+2", 140, 196, 90)
s.wire(140, YT + 7.62, 140, YT + 11)
s.junction(140, YT + 11)
s.sym("R", "RK4", "220k", 140, YT + 14.81, lx=-9.4, ly=0.0)
s.gnd(140, YT + 18.62)
s.text("cathode follower", 150, YT - 12.5, 1.3)
# follower output -> .1 uF -> 1M -> Depth. The Depth control's COLD end is the
# -28 V line and its WIPER feeds the output grid leaks, so cx:POT pin 1 has to
# be the -28 V end for sch_map's series_bridge to join the right section.
s.wire(140, YT + 11, 148, YT + 11)
s.wire(148, YT + 11, 148, YT + 22)
cl, cr = s.series_h("C", "C12", ".1u", 158, YT + 22)
s.wire(148, YT + 22, cl, YT + 22)
s.wire(cr, YT + 22, 168, YT + 22)
l, r = s.series_h("R", "R10", "1M", 174, YT + 22)
s.wire(168, YT + 22, l, YT + 22)
s.wire(r, YT + 22, 184, YT + 22)
s.sym("POT", "VR5", "250k-L", 184, YT + 18.19, lx=-11.6, ly=3.2)
s.wire(184, YT + 14.38, 184, YT + 11.5)
s.glabel("-28V", 184, YT + 11.5, 90)
s.wire(189.08, YT + 18.19, 196, YT + 18.19)
s.glabel("DEPTHW", 196, YT + 18.19, 0)
s.text("Depth", 172, YT + 16.0, 1.3)

# ============================ POWER SUPPLY ===========================
YPW = 200
BY = YPW + 6
s.text("Power supply — 8160 power transformer, 300-0-300 V, 5U4GB full-wave; 14684 choke; 108 output transformer",
       219, 176, 1.5)
pt = s.pt("T1", "8160", 232, YPW, lx=-6.35, ly=-12.5)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1], 0)
s.glabel("HT_A", 258, YPW - 14, 90)
s.wire(258, YPW - 14, 258, YPW - 11.5)
s.diode_tube("V6A", "5U4GB", 258, YPW - 3.88, lx=-13.4)
s.glabel("HT_B", 270, YPW - 14, 90)
s.wire(270, YPW - 14, 270, YPW - 11.5)
s.diode_tube("V6B", "5U4GB", 270, YPW - 3.88, lx=6.2)
s.wire(258, YPW + 3.74, 258, BY)
s.wire(270, YPW + 3.74, 270, BY)
s.wire(258, BY, 292, BY)
s.junction(270, BY)
# reservoir: TWO 20 uF cans on B+1, one on B+2, one on B+3 (the drawing's box)
s.junction(276, BY)
s.sym("C", "C15", "20u", 276, BY + 3.81)
s.gnd(276, BY + 7.62)
s.junction(284, BY)
s.sym("C", "C16", "20u", 284, BY + 3.81)
s.gnd(284, BY + 7.62)
s.junction(292, BY)
s.wire(292, BY - 3.5, 292, BY)
s.glabel("B+1", 292, BY - 3.5, 90)
lch, rch = s.choke("L1", "14684", 304, BY)
s.wire(292, BY, lch, BY)
s.wire(rch, BY, 324, BY)
s.junction(318, BY)
s.sym("C", "C17", "20u", 318, BY + 3.81)
s.gnd(318, BY + 7.62)
s.junction(324, BY)
s.wire(324, BY - 3.5, 324, BY)
s.glabel("B+2", 324, BY - 3.5, 90)
l, r = s.series_h("R", "RD1", "10k 1W", 332, BY)
s.wire(324, BY, l, BY)
s.wire(r, BY, 348, BY)
s.junction(342, BY)
s.sym("C", "C18", "20u", 342, BY + 3.81)
s.gnd(342, BY + 7.62)
s.wire(348, BY - 3.5, 348, BY)
s.glabel("B+3", 348, BY - 3.5, 90)

# ============================ BIAS SUPPLY ============================
YBI = 250
s.text("Bias supply — one HT leg into a rectifier and an 8 µF can, then an 82k / 56k divider: a fixed -28 V, no trimmer and no series feed resistor",
       219, 242, 1.4)
s.glabel("HT_B", 240, YBI, 180)
s.wire(240, YBI, 248.92, YBI)
s.sym("DIODE_SS", "D1", "selenium", 254, YBI, lx=-3.4, ly=-5.6)
s.wire(259.08, YBI, 268, YBI)
s.junction(268, YBI)
s.sym("C", "C13", "8u 150V", 268, YBI + 3.81)
s.gnd(268, YBI + 7.62)
l, r = s.series_h("R", "R11", "82k", 282, YBI)
s.wire(268, YBI, l, YBI)
s.wire(r, YBI, 294, YBI)
s.junction(294, YBI)
s.sym("C", "C14", "8u 150V", 294, YBI + 3.81)
s.gnd(294, YBI + 7.62)
s.wire(294, YBI, 304, YBI)
s.junction(304, YBI)
s.sym("R", "R12", "56k", 304, YBI + 3.81, lx=3.0, ly=0.0)
s.gnd(304, YBI + 7.62)
s.wire(304, YBI, 314, YBI)
s.glabel("-28V", 314, YBI, 0)

s.write(OUT)
print(f"wrote {OUT}")
