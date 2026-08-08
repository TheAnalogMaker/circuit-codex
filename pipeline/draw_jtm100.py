#!/usr/bin/env python3
"""Generate amps/jtm100/schematic.kicad_sch from the stage-template library.

Values per the published Marshall 100-watt factory drawing, title block "BASIC
SCHEMATIC FOR MARSHALL 100 WATT SUPER TREM AMP / TYPE 1959T" — see
amps/jtm100/meta.yaml. This is the JTM45 front end driving FOUR KT66 beam
tetrodes in parallel push-pull off a solid-state HT supply: two arms of three
series silicon diodes into a reservoir of three series 32 uF pairs, a 20 H choke
to the screen node, then 8.2 k and 10 k rail droppers.

THIS IS THE PLAIN HEAD. The sheet is the tremolo version, exactly as the JTM45
sheet is: its V2 is the tremolo oscillator valve and it drives a transistor that
shunts the V3A grid node, and neither belongs to the non-tremolo head. Both are
omitted, so the valve numbering follows the drawing and skips V2 — V1 input
pair, V3 second stage + cathode follower, V4 long-tailed-pair inverter, V5-V8
the KT66 quartet.

Two details are drawn as the sheet draws them rather than tidied up:

* the presence control sits IN the phase-inverter tail — the 10 k lands on the
  TOP of the 5 k pot and the pot completes the path to ground — and the 27 k
  feedback resistor arrives at that same node, which the drawing circles at
  16 V. The 0.1 uF (C8) couples that node to the V4B grid;
* only half the output valves get a grid stopper. Each phase node feeds one
  valve through a 15 k stopper and takes the other valve's grid straight off the
  node — V5 and V8 stoppered, V6 and V7 not.

Heaters, the mains transformer, the standby switch, the two fuses and the pilot
lamp are omitted (see netlist.cir); they are named in the notes at the foot of
the drawing.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "jtm100" / "schematic.kicad_sch"
s = Sch()

MIXLINE_X = 100.0
V3_Y = 140.0

# ====================== V1 input — two channels, shared cathode ==============
# Each channel: input jack -> 68k stopper -> grid (1M leak to ground); 100k
# plate load to B+4; 0.02 uF coupler -> 1M volume -> 270k mixer into the shared
# V3A grid line. The chassis carries four jacks — two per channel, each with its
# own 68k — and the drawing gives each channel one grid leak.
for (y, jack, sref, gref, vtube, plref, cpref, vref, mref, brC) in [
        (60, "CH I IN",  "R1s", "RG1", "V1A", "RL1", "C1", "VR1", "RM1", None),
        (96, "CH II IN", "R2s", "RG2", "V1B", "RL2", "C2", "VR2", "RM2", "C23")]:
    t = s.triode(vtube, "ECC83", 54, y)
    gx = t["g"][0]                                   # 46.38
    s.glabel(jack, 20, y, 180)
    s.wire(20, y, 26, y)
    hl, hr = s.series_h("R", sref, "68k", 33, y)
    s.wire(26, y, hl, y)
    s.wire(hr, y, gx, y)
    s.junction(42, y)
    s.sym("R", gref, "1M", 42, y + 3.81, lx=-9.6, ly=1.2)   # clear of the stopper body
    s.gnd(42, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # plate stub -> coupler -> volume pot -> mixer
    ty = y - 7.62 - 3.48
    s.wire(54, ty, 66, ty)
    s.junction(54, ty)
    cl, cr = s.series_h("C", cpref, ".02u", 70, ty)
    s.wire(cl, ty, 66, ty)
    s.wire(cr, ty, 80, ty)
    s.sym("POT", vref, "1M vol", 80, ty + 3.81)
    s.wire(80, ty + 7.62, 80, ty + 9.5)
    s.gnd(80, ty + 9.5)
    if brC:                                          # 100 pF bright cap across VR2
        s.sym("C", brC, "100p", 80, ty - 4.5, lx=2.4)
        s.wire(80, ty, 80, ty - 0.69)
        s.wire(80, ty - 8.31, 88, ty - 8.31)
        s.wire(88, ty - 8.31, 88, ty + 3.81)
    s.junction(85.08, ty + 3.81)          # the pot's wiper pin, exactly
    s.wire(85.08, ty + 3.81, 88, ty + 3.81)
    ml, mr = s.series_h("R", mref, "270k", 92, ty + 3.81)
    s.wire(88, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, MIXLINE_X, ty + 3.81)
    s.wire(MIXLINE_X, ty + 3.81, MIXLINE_X, V3_Y)
s.junction(MIXLINE_X, 88.71)
s.junction(MIXLINE_X, V3_Y)
s.text("A capacitor of illegible value parallels the channel II mixer on the "
       "sheet; it is listed in bom.yaml and not drawn.", 20, 128, 1.15)

# shared input cathode: one 820 R with a 25 uF bypass under both triodes
s.wire(54, 67.62, 54, 71)
s.wire(54, 71, 48, 71)
s.wire(48, 71, 48, 112)
s.wire(54, 103.62, 54, 107)
s.wire(54, 107, 48, 107)
s.junction(48, 107)
s.shunt_rc("RK1", "820", "C3", "25u", 48, 112)

# ==================== V3A second stage + V3B cathode follower ================
t3a = s.triode("V3A", "ECC83", 110, V3_Y)
s.wire(MIXLINE_X, V3_Y, t3a["g"][0], V3_Y)
s.wire(110, V3_Y + 7.62, 110, 150)
s.wire(110, 150, 116, 150)
s.sym("R", "RK2", "820", 116, 153.81)                # unbypassed on this sheet
s.gnd(116, 157.62)
s.plate_load("RL3", "100k", t3a["p"], "B+4")
tee = V3_Y - 7.62 - 3.48                             # 128.9
s.wire(110, tee, 118, tee)
s.junction(110, tee)
t3b = s.triode("V3B", "ECC83 CF", 126, V3_Y)
s.wire(118, tee, 118, V3_Y)
s.wire(118, V3_Y, t3b["g"][0], V3_Y)
s.wire(126, V3_Y - 7.62, 126, 129.5)
s.glabel("B+4", 126, 129.5, 90)                      # CF plate straight to the rail
s.wire(126, V3_Y + 7.62, 126, 150.5)
s.junction(126, 150.5)
s.sym("R", "RKCF", "100k", 126, 154.31)
s.gnd(126, 158.12)

# ======================= TMB tone stack (cathode-follower fed) ===============
# 56k slope; 270 pF treble / 250k; 0.02 bass / 1M; 0.02 mid / 25k — the JTM45's
# network with the middle capacitor lettered 0.02 instead of 0.01, so the bass
# and middle caps read the same value.
# Wired as the sheet draws it (the ladder the 5F6-A, JTM45, 1987 and 1959 sheets
# share): node A = the cathode-follower output, carrying the 270 pF to the
# treble pot AND the slope resistor; node B = the slope's foot, carrying 0.02 uF
# to the treble-bottom/bass node and 0.02 uF to the MIDDLE POT'S WIPER; the bass
# pot is a rheostat in series down the ladder; the output is the TREBLE WIPER
# ALONE.
CF = 150.5
s.wire(126, CF, 133, CF)
sl, sr = s.series_h("R", "RSL", "56k", 137, CF)
s.wire(133, CF, sl, CF)
s.junction(133, CF)
s.wire(133, CF, 133, 126)                            # node A riser
s.wire(sr, CF, 145, CF)
s.junction(145, CF)
s.wire(145, CF, 145, 138)                            # node B riser, bass cap
s.wire(145, CF, 145, 160)                            # node B riser, mid cap
tl, tr = s.series_h("C", "C4", "270p", 149, 126)
s.wire(133, 126, tl, 126)
s.wire(tr, 126, 156, 126)
s.sym("POT", "VR3", "250k treb", 156, 129.81)
bl, br = s.series_h("C", "C5", ".02u", 149, 138)
s.wire(145, 138, bl, 138)
s.wire(br, 138, 156, 138)
s.wire(156, 133.62, 156, 138)                        # treble bottom lug -> bass node
s.junction(156, 138)
s.sym("POT", "VR4", "1M bass", 156, 141.81)
s.wire(161.08, 141.81, 165, 141.81)                  # bass wiper strapped (rheostat)
s.wire(165, 141.81, 165, 138)
s.wire(165, 138, 156, 138)
ml, mr = s.series_h("C", "C6", ".02u", 149, 160)
s.wire(145, 160, ml, 160)
s.wire(mr, 160, 163.6, 160)
s.wire(163.6, 160, 163.6, 151.81)
s.wire(163.6, 151.81, 161.08, 151.81)                # -> middle wiper
s.wire(156, 145.62, 156, 148)                        # bass foot -> middle top
s.sym("POT", "VR5", "25k mid", 156, 151.81)
s.gnd(156, 155.62)
s.wire(161.08, 129.81, 165, 129.81)                  # treble wiper = stack output
s.wire(165, 129.81, 165, 122)

# ===================== V4 long-tailed-pair phase inverter ===================
# The bottles sit one above the other with their plate loads rising in the same
# column, so the tail runs BELOW both of them: the joined cathodes come down the
# right-hand rail into the 470, and the tail junction — where both 1 M grid leaks
# return — sits on the lane under the lower bottle. The 10 k then drops from that
# junction to the TOP of the presence pot, and the 0.1 uF (C8) taps the same
# presence node back up to the V4B grid.
GL = 188.38          # grid-leak column: V4A grid, both 1 M leaks, V4B grid
RC = 174.0           # the RGA return column
PC = 158.0           # the presence / feedback column the 27 k comes down
JY = 186.0           # tail-junction lane, clear below both bottles
ol, orr = s.series_h("C", "C7", ".02u", 176, 122)
s.wire(165, 122, ol, 122)
s.wire(orr, 122, GL, 122)
t4a = s.triode("V4A", "ECC83", 196, 122)
t4b = s.triode("V4B", "ECC83", 196, 158)
s.wire(GL, 122, t4a["g"][0], 122)
s.plate_load("RLA", "82k", t4a["p"], "B+3")          # tone-stack-driven side
s.plate_load("RLB", "100k", t4b["p"], "B+3")
# 47 pF plate-to-plate compensation, drawn between the two plate rows
s.wire(196, 114.38, 209, 114.38)
s.junction(196, 114.38)
s.wire(209, 114.38, 209, 128.57)
s.sym("C", "C12", "47p", 209, 132.38)
s.wire(209, 136.19, 209, 150.38)
s.wire(209, 150.38, 196, 150.38)
s.junction(196, 150.38)
# joined cathodes -> the right-hand rail -> 470 -> the tail junction
s.wire(196, 129.62, 196, 133)
s.wire(196, 133, 204, 133)
s.wire(196, 165.62, 196, 169)
s.wire(196, 169, 204, 169)
s.wire(204, 133, 204, 179)
s.junction(204, 169)
rl, rr = s.series_h("R", "RTAIL", "470", 212, 179)
s.wire(204, 179, rl, 179)
s.wire(rr, 179, 220, 179)
s.wire(220, 179, 220, JY)
s.junction(220, JY)
# both grid leaks return to the tail junction along the JY lane
s.wire(GL, 122, GL, 126)
s.junction(GL, 122)
s.sym("R", "RGA", "1M", GL, 129.81, lx=-9.4)
s.wire(GL, 133.62, GL, 137)
s.wire(GL, 137, RC, 137)
s.wire(RC, 137, RC, JY)
s.wire(GL, 158, GL, 162)
s.sym("R", "RGB", "1M", GL, 165.81, lx=-9.4)
s.wire(GL, 169.62, GL, JY)
s.junction(GL, 158)
s.wire(GL, 158, t4b["g"][0], 158)
s.wire(RC, JY, GL, JY)
s.wire(GL, JY, 220, JY)
s.junction(GL, JY)
s.junction(RC, JY)
# the tail continues through the 10 k into the TOP of the presence pot
tl2, tr2 = s.series_h("R", "RT2", "10k", 166, JY)
s.wire(tr2, JY, RC, JY)
s.wire(tl2, JY, PC, JY)
# the 0.1 uF from that same presence node back up to the V4B grid
# label placed BELOW this one — above it is the middle pot's ground symbol
s.sym("C", "C8", ".1u", 166, 158, rot=90, lx=-3.2, ly=4.4)
cl2, cr2 = 166 - 3.81, 166 + 3.81
s.wire(cr2, 158, GL, 158)
s.wire(cl2, 158, PC, 158)
s.wire(PC, 158, PC, 192)
s.junction(PC, JY)
# presence pot in series in the tail, with its wiper capacitor to ground
s.sym("POT", "VR7", "5k presence", PC, 195.81, lx=-16.0, ly=6.4)
s.gnd(PC, 199.62)
s.wire(PC + 5.08, 195.81, 168, 195.81)
s.sym("C", "C11", ".1u", 168, 199.62, lx=2.2)
s.gnd(168, 203.43)
# 27 k negative feedback from the 16 ohm secondary tap onto the same node
s.junction(PC, 176)
s.wire(PC, 176, 150, 176)
nl, nr = s.series_h("R", "RNFB", "27k", 144, 176)
s.wire(nr, 176, 150, 176)
s.wire(nl, 176, 136, 176)
s.glabel("SPKR", 136, 176, 180)
s.text("The presence control is IN the tail: the 10 k lands on the TOP of the "
       "5 k pot and the pot completes the path to ground, so the tail sees "
       "about 15 k.", 20, 194, 1.2)
s.text("The drawing circles 16 V at that node, which is what the chart's 52 V "
       "inverter cathodes and the drawn 470 + 10 k require. C8 couples the node "
       "to the V4B grid.", 20, 198, 1.2)

# ======================= KT66 quartet, adjustable fixed bias =================
# Two valves per phase off one 0.1 uF coupler and one 220k grid leak; ONE valve
# of each pair carries a 15k grid stopper and the other takes its grid straight
# off the phase node, which is what the sheet draws.
for plate_y, cref, glref, gcol, leak_y, pairs in [
        (114.38, "C9",  "RGL1", 238, 114.38,
         [(55, "V5", "RS1", "R5s"), (90, "V6", "RS2", None)]),
        (150.38, "C10", "RGL2", 242, 200,
         [(165, "V7", "RS3", None), (200, "V8", "RS4", "R8s")])]:
    gys = [g for g, _, _, _ in pairs]
    top, bot = min(gys + [plate_y]), max(gys + [plate_y])
    s.wire(209, plate_y, 216, plate_y)
    s.junction(209, plate_y)
    cl, cr = s.series_h("C", cref, ".1u", 222, plate_y)
    s.wire(216, plate_y, cl, plate_y)
    s.wire(cr, plate_y, gcol, plate_y)
    s.wire(gcol, top, gcol, bot)
    for gy in gys + [plate_y]:
        if top < gy < bot:
            s.junction(gcol, gy)
    for gy, vref2, scref, stref in pairs:
        p = s.pentode(vref2, "KT66", 262, gy, lx=-15.0, ly=4.6)
        if stref:                                    # 15k grid stopper
            s2l, s2r = s.series_h("R", stref, "15k", gcol + 7, gy)
            s.wire(gcol, gy, s2l, gy)
            s.wire(s2r, gy, p["g1"][0], gy)
        else:                                        # grid straight off the node
            s.wire(gcol, gy, p["g1"][0], gy)
        # 1 k 5 W screen stopper from the screen rail
        s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 1.9, p["g2"][1])
        sc1, sc2 = s.series_h("R", scref, "1k 5W", p["g2"][0] + 5.71, p["g2"][1])
        s.wire(sc2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
        s.glabel("B+2", p["g2"][0] + 11.5, p["g2"][1], 0)
        s.gnd(262, p["k"][1])
    # 220k grid leak for the pair -> the adjustable negative-bias line
    s.junction(gcol, leak_y)
    s.wire(gcol, leak_y, gcol, leak_y + 5.62)
    s.sym("R", glref, "220k", gcol, leak_y + 9.43, lx=-9.6)
    s.wire(gcol, leak_y + 13.24, gcol, leak_y + 15.78)
    s.glabel("-BIAS", gcol, leak_y + 15.78, 270)

# ---- output transformer ----------------------------------------------------
s.sym("OT_PP", "T1", "OT", 312, 128, lx=-6.35, ly=-14.0)
s.wire(262, 46.745, 262, 40)                         # V5 plate
s.wire(262, 40, 294, 40)
s.wire(294, 40, 294, 122.92)
s.wire(262, 81.745, 262, 75)                         # V6 plate, same primary end
s.wire(262, 75, 294, 75)
s.junction(294, 75)
s.wire(294, 122.92, 303.11, 122.92)
s.wire(262, 156.745, 262, 150)                       # V7 plate
s.wire(262, 150, 298, 150)
s.wire(262, 191.745, 262, 185)                       # V8 plate, same primary end
s.wire(262, 185, 298, 185)
s.wire(298, 185, 298, 133.08)
s.junction(298, 150)
s.wire(298, 133.08, 303.11, 133.08)
s.wire(303.11, 128, 300, 128)                        # primary centre tap -> B+1
s.wire(300, 128, 300, 120)
s.glabel("B+1", 300, 120, 90)
s.wire(320.89, 125.46, 325, 125.46)
s.glabel("SPKR", 325, 125.46, 0)
s.wire(320.89, 130.54, 325, 130.54)
s.glabel("GND", 325, 130.54, 0)
s.text("Secondary leads are lettered on the sheet: blue 100 V line, white "
       "16 ohm, yellow 8 ohm, orange common.", 262, 106, 1.2)
s.text("Feedback is taken from the 16 ohm tap.", 262, 110, 1.2)

# ======================= power supply — silicon HT bank ======================
PY = 237.0
s.text("Power — universal-primary mains transformer (110/250 V, 50/60 c/s) and "
       "a centre-tapped HT winding; each arm rectified by three series silicon "
       "diodes; reservoir of three series 32 uF pairs;", 20, 208, 1.4)
s.text("a 20 H choke to the KT66 screen node, then 8.2 k and 10 k rail "
       "droppers. The mains lead carries a 2 A slow-blow fuse and the HT centre "
       "tap a 1 A slow-blow; a standby switch sits between", 20, 212.5, 1.4)
s.text("the diode bank and the reservoir. Fuses, switch, mains transformer, "
       "heater winding and pilot lamp are omitted here — see netlist.cir.",
       20, 217, 1.4)
for arm_y, ht, dr in [(230, "HT_A", ("D1", "D2", "D3")),
                      (244, "HT_B", ("D4", "D5", "D6"))]:
    s.glabel(ht, 22, arm_y, 180)
    s.wire(22, arm_y, 26.92, arm_y)
    for i, dref in enumerate(dr):
        x = 32 + 14 * i
        s.sym("DIODE_SS", dref, "IS107", x, arm_y, lx=-2.4, ly=-5.4)
        if i:
            s.wire(x - 8.92, arm_y, x - 5.08, arm_y)
    s.wire(65.08, arm_y, 72, arm_y)
    s.junction(72, arm_y)
s.wire(72, 230, 72, 244)
s.wire(72, PY, 80, PY)
s.junction(72, PY)
# reservoir: three series 32 uF pairs across B+1
for x, upper, lower in [(92, "C13", "C14"), (104, "C15", "C16"), (116, "C17", "C18")]:
    s.sym("C", upper, "32u", x, PY + 3.81)
    s.sym("C", lower, "32u", x, PY + 11.43)
    s.junction(x, PY)
    s.junction(x, PY + 7.62)
s.wire(92, PY + 15.24, 116, PY + 15.24)
s.junction(92, PY + 15.24)
s.junction(116, PY + 15.24)
s.gnd(104, PY + 15.24)
s.wire(80, PY, 130, PY)
s.junction(86, PY)
s.wire(86, PY - 3, 86, PY)
s.glabel("B+1", 86, PY - 3, 90)
# 20 H choke -> the KT66 screen node; then the two droppers
s.wire(130, PY, 134.38, PY)
s.sym("CHOKE", "L1", "20H", 142, PY, lx=-4.0, ly=-6.4)
s.wire(149.62, PY, 160, PY)
s.junction(156, PY)
s.wire(156, PY - 3, 156, PY)
s.glabel("B+2", 156, PY - 3, 90)
dl, dr2 = s.series_h("R", "RD1", "8.2k", 168, PY)
s.wire(160, PY, dl, PY)
s.wire(dr2, PY, 182, PY)
s.junction(178, PY)
s.wire(178, PY - 3, 178, PY)
s.glabel("B+3", 178, PY - 3, 90)
s.junction(182, PY)
s.sym("C", "C19", "32u", 182, PY + 3.81, lx=2.2)
s.gnd(182, PY + 7.62)
el, er = s.series_h("R", "RD2", "10k 1W", 192, PY)
s.wire(182, PY, el, PY)
s.wire(er, PY, 206, PY)
s.junction(200, PY)
s.wire(200, PY - 3, 200, PY)
s.glabel("B+4", 200, PY - 3, 90)
s.sym("C", "C20", "16u", 206, PY + 3.81, lx=2.2)
s.gnd(206, PY + 7.62)

# ======================= adjustable negative-bias supply =====================
# An HT-tap diode behind a 470k trimmer paralleling a 150k, then the 56k/16k
# divider between two 8 uF filters. The drawing circles -65/-66 V at it.
BY = 254.0
s.glabel("HT_A", 232, 268, 180)
s.wire(232, 268, 244, 268)
bl2, br2 = s.series_h("R", "RB1", "150k", 252, 268)
s.wire(244, 268, bl2, 268)
s.wire(br2, 268, 262, 268)
s.sym("POT", "VR6", "470k trim", 252, 277, rot=90, lx=-6.4, ly=6.2)
s.wire(248.19, 277, 244, 277)
s.wire(244, 277, 244, 268)
s.junction(244, 268)
s.wire(255.81, 277, 262, 277)
s.wire(262, 277, 262, 268)
s.junction(262, 268)
s.wire(252, 271.92, 262, 271.92)                     # wiper strapped (rheostat)
s.junction(262, 271.92)
s.sym("DIODE_SS", "D7", "IS107", 262, 262, rot=270, lx=2.6, ly=-1.2)
s.wire(262, 267.08, 262, 268)                        # cathode toward the HT winding
s.wire(262, 256.92, 262, BY)                         # anode = the negative rail
s.wire(262, BY, 288.19, BY)
s.junction(274, BY)
s.sym("C", "C21", "8u", 274, BY + 3.81, lx=2.2)
s.gnd(274, BY + 7.62)
s.junction(282, BY)
s.sym("R", "RB2", "56k", 282, BY + 3.81)
s.gnd(282, BY + 7.62)
fl, fr = s.series_h("R", "RB3", "16k", 292, BY)
s.wire(fr, BY, 302, BY)
s.junction(302, BY)
s.sym("C", "C22", "8u", 302, BY + 3.81, lx=2.2)
s.gnd(302, BY + 7.62)
s.wire(302, BY, 310, BY)
s.glabel("-BIAS", 310, BY, 0)
s.text("Bias: the 470 k trimmer parallels the 150 k, so winding it changes "
       "the series resistance ahead of the diode.", 180, 292, 1.2)

s.write(OUT, [
    ("JTM100 — British 100-watt lead-style · Circuit Codex · CC-BY-SA 4.0 · "
     "redrawn from circuit facts", 20, 26, 2.2),
    ("Four KT66s in parallel push-pull on a 560 V solid-state rail — the JTM45 "
     "front end with its output section doubled. The tremolo valve of the "
     "source sheet is omitted, so the numbering skips V2.", 20, 31, 1.4),
    ("Channel I and channel II are identical apart from the 100 pF bright cap "
     "across channel II's volume control; the chassis carries two jacks per "
     "channel, each with its own 68 kohm stopper.", 20, 35.5, 1.3),
], paper="A3")
print(f"wrote {OUT}")
