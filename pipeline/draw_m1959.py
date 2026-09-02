#!/usr/bin/env python3
"""Generate amps/m1959/schematic.kicad_sch from the stage-template library.

Values per the published Marshall model 1959 factory drawing (Unicord 70-6-11
rev B, July 1970) — see amps/m1959/meta.yaml. The 1959 is the 100-watt Super
Lead: the model 1987's front end (four inputs into two deliberately unmatched
channels, a DC-coupled cathode follower ahead of the TMB stack, a long-tailed-
pair inverter) driving FOUR EL34 pentodes in parallel push-pull, two per phase,
off a silicon bridge rectifier — there is no rectifier valve at all.

Valve numbering follows the drawing: V1 input (one triode per channel), V2
second stage + cathode follower, V3 long-tailed-pair phase inverter, V4-V7 the
EL34 output quartet. Each output valve carries its own 5.6 k grid stopper and
1 k screen stopper; one 120 k grid leak serves each pair.

Heaters, the PT primary, the fuses, the standby switch and the pilot lamp are
omitted (see netlist.cir). The power section shows the silicon bridge, the
series-pair reservoir bank with its 56 k sharing resistors, the 20 k / 10 k /
10 k dropper chain and the diode / 27 k / 15 k / 47 k negative-bias supply with
its 27 k adjust trimmer.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "m1959" / "schematic.kicad_sch"
s = Sch()

# ============================ V1 input — two channels =======================
# Each channel: high + low input jacks -> 68k stoppers -> grid (1M leak); 100k
# plate load to B+4; its own cathode bias; plate -> coupler -> 1M volume with a
# bright cap across it -> 470k mixer into the shared V2A grid line.
MIXLINE_X = 100.0
V2_Y = 140.0
for (y, hi, lo, sHi, sLo, gref, pref, plref, kref, kval, cbref, cbval,
     cpref, cpval, vref, brC, brCval, mref) in [
        (60, "CH I HI", "CH I LO", "R1s", "R2s", "RG1", "V1A", "RL1",
         "RK1", "820", "C1", "250u", "C3", ".022u", "VR1", "C5", ".005u", "RM1"),
        (96, "CH II HI", "CH II LO", "R3s", "R4s", "RG2", "V1B", "RL2",
         "RK2", "2.7k", "C2", ".68u", "C4", ".0022u", "VR2", "C6", "500p", "RM2")]:
    t = s.triode(pref, "ECC83", 54, y)
    gx = t["g"][0]
    # high input -> 68k stopper -> grid
    s.glabel(hi, 20, y - 4, 180)
    s.wire(20, y - 4, 26, y - 4)
    hl, hr = s.series_h("R", sHi, "68k", 31, y - 4)
    s.wire(26, y - 4, hl, y - 4)
    s.wire(hr, y - 4, gx - 3.81, y - 4)
    s.wire(gx - 3.81, y - 4, gx - 3.81, y)
    # low input -> 68k stopper -> grid
    s.glabel(lo, 20, y + 6, 180)
    s.wire(20, y + 6, 26, y + 6)
    ll, lr = s.series_h("R", sLo, "68k", 31, y + 6)
    s.wire(26, y + 6, ll, y + 6)
    s.wire(lr, y + 6, gx - 3.81, y + 6)
    s.wire(gx - 3.81, y + 6, gx - 3.81, y)
    s.junction(gx - 3.81, y)
    s.wire(gx - 3.81, y, gx, y)
    # 1M grid leak to ground (chassis-mounted at the jacks)
    s.sym("R", gref, "1M", gx - 3.81, y + 9, lx=-9.4)
    s.gnd(gx - 3.81, y + 12.81)
    # plate load 100k to B+4
    s.plate_load(plref, "100k", t["p"], "B+4")
    # cathode bias R + bypass cap
    s.wire(54, y + 7.62, 54, y + 10)
    s.wire(54, y + 10, 60, y + 10)
    s.shunt_rc(kref, kval, cbref, cbval, 60, y + 10)
    # plate stub -> coupler -> volume pot
    ty = y - 7.62 - 3.48
    s.wire(54, ty, 66, ty)
    s.junction(54, ty)
    cl, cr = s.series_h("C", cpref, cpval, 70, ty)
    s.wire(cl, ty, 66, ty)
    s.wire(cr, ty, 80, ty)
    # Volume-pot lettering anchored below the wiper, clear of the pot body:
    # the default anchor laid "1M vol" across the wiper wire and RM's pin.
    s.sym("POT", vref, "1M vol", 80, ty + 3.81, lx=2.8, ly=2.2)
    s.wire(80, ty + 7.62, 80, ty + 9.5)
    s.gnd(80, ty + 9.5)
    # bright cap across the volume pot (top -> wiper)
    s.sym("C", brC, brCval, 80, ty - 4.5, lx=2.4)
    s.wire(80, ty, 80, ty - 0.69)
    s.wire(80, ty - 8.31, 88, ty - 8.31)
    s.wire(88, ty - 8.31, 88, ty + 3.81)
    s.junction(85.08, ty + 3.81)
    # wiper -> 470k mixer -> shared V2A grid line
    s.wire(85.08, ty + 3.81, 88, ty + 3.81)
    ml, mr = s.series_h("R", mref, "470k", 92, ty + 3.81)
    s.wire(88, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, MIXLINE_X, ty + 3.81)
    s.wire(MIXLINE_X, ty + 3.81, MIXLINE_X, V2_Y)
s.junction(MIXLINE_X, 88.71)
s.junction(MIXLINE_X, V2_Y)

# ==================== V2A second stage + V2B cathode follower ================
t2a = s.triode("V2A", "ECC83", 110, V2_Y)
s.wire(MIXLINE_X, V2_Y, t2a["g"][0], V2_Y)
# cathode 820R + 0.68u partial bypass (the drawing annotates a 1k variant)
s.wire(110, V2_Y + 7.62, 110, V2_Y + 10)
s.wire(110, V2_Y + 10, 116, V2_Y + 10)
s.shunt_rc("RK3", "820", "C7", ".68u", 116, V2_Y + 10)
s.plate_load("RL3", "100k", t2a["p"], "B+3")
# DC-coupled cathode follower: grid from the V2A plate stub tee
tee = V2_Y - 7.62 - 3.48
s.wire(110, tee, 118, tee)
s.junction(110, tee)
t2b = s.triode("V2B", "ECC83 CF", 126, V2_Y)
s.wire(118, tee, 118, V2_Y)
s.wire(118, V2_Y, t2b["g"][0], V2_Y)
s.wire(126, V2_Y - 7.62, 126, V2_Y - 10.5)
s.glabel("B+3", 126, V2_Y - 10.5, 90)      # CF plate straight to the rail
s.wire(126, V2_Y + 7.62, 126, V2_Y + 10.5)
s.junction(126, V2_Y + 10.5)
s.sym("R", "RKCF", "100k", 126, V2_Y + 14.31)
s.gnd(126, V2_Y + 18.12)

# ======================= TMB tone stack (cathode-follower fed) ===============
# 33k slope; 500p treble / 250k; 0.022 bass / 1M; 0.022 mid / 25k.
CF = V2_Y + 10.5                           # cathode-follower output node
# Wired as the published model 1959 drawing (Unicord 70-6-11) draws it — the
# same network as the model 1987, JTM45 and 5F6-A sheets before it:
#   node A = cathode-follower output: 500 pF to the treble pot AND the 33k slope;
#   node B = the slope's foot: 0.022 uF to the treble-bottom/bass node, 0.022 uF
#            to the MIDDLE POT'S WIPER;
#   the bass pot is a rheostat (the drawing's arrow-through-body variable
#   resistor) in series down the ladder, and the stack's output is the TREBLE
#   WIPER ALONE.
s.wire(126, CF, 133, CF)
sl, sr = s.series_h("R", "RSL", "33k", 137, CF)
s.wire(133, CF, sl, CF)
s.junction(133, CF)
s.wire(133, CF, 133, 126)                  # node A up to the 500 pF branch
s.wire(sr, CF, 145, CF)
s.junction(145, CF)
s.wire(145, CF, 145, 138)                  # node B riser, up to the bass cap
s.wire(145, CF, 145, 160)                  # node B riser, down to the mid cap
# treble branch: 500p -> 250k treble pot
tl, tr = s.series_h("C", "C8", "500p", 149, 126)
s.wire(133, 126, tl, 126)
s.wire(tr, 126, 156, 126)
s.sym("POT", "VR3", "250k treb", 156, 129.81)
# bass branch: node B -> 0.022 -> treble-bottom/bass node
bl, br = s.series_h("C", "C9", ".022u", 149, 138)
s.wire(145, 138, bl, 138)
s.wire(br, 138, 156, 138)
s.wire(156, 133.62, 156, 138)              # treble bottom lug -> bass node
s.junction(156, 138)
s.sym("POT", "VR4", "1M bass", 156, 141.81)
s.wire(161.08, 141.81, 165, 141.81)        # bass wiper strapped to its hot lug (rheostat)
s.wire(165, 141.81, 165, 138)
s.wire(165, 138, 156, 138)
# mid branch: node B -> 0.022 -> the middle pot's wiper
ml, mr = s.series_h("C", "C10", ".022u", 149, 160)
s.wire(145, 160, ml, 160)
s.wire(mr, 160, 163.6, 160)
s.wire(163.6, 160, 163.6, 151.81)
s.wire(163.6, 151.81, 161.08, 151.81)      # -> middle wiper
s.wire(156, 145.62, 156, 148)              # bass foot -> middle top
s.sym("POT", "VR5", "25k mid", 156, 151.81)
s.gnd(156, 155.62)
# treble wiper = stack output
s.wire(161.08, 129.81, 165, 129.81)
s.wire(165, 129.81, 165, 122)

# ===================== V3 long-tailed-pair phase inverter ===================
GL = 178.4          # grid / grid-leak column
RC = 166.0          # V3A grid-leak return column
JY = 182.0          # tail-junction lane, clear below both bottles
ol, orr = s.series_h("C", "C11", ".022u", 173, 122)
s.wire(165, 122, ol, 122)
s.wire(orr, 122, GL, 122)
t3a = s.triode("V3A", "ECC83", 186, 122)
s.wire(GL, 122, t3a["g"][0], 122)
t3b = s.triode("V3B", "ECC83", 186, 158)
s.plate_load("RLA", "82k", t3a["p"], "B+2")      # tone-stack-driven side
s.plate_load("RLB", "100k", t3b["p"], "B+2")
# 47 pF plate-to-plate compensation, drawn between the two plate rows
s.wire(186, 114.38, 199, 114.38)
s.junction(186, 114.38)
s.wire(199, 114.38, 199, 128.57)
s.sym("C", "C12", "47p", 199, 132.38)
s.wire(199, 136.19, 199, 150.38)
s.wire(199, 150.38, 186, 150.38)
s.junction(186, 150.38)
# shared tail: cathodes -> 470 -> J -> 10k -> gnd
s.wire(186, 129.62, 186, 132)
s.wire(186, 132, 192, 132)
s.wire(186, 165.62, 186, 168)
s.wire(186, 168, 192, 168)
s.wire(192, 132, 192, 175)
s.junction(192, 168)
rl, rr = s.series_h("R", "RTAIL", "470", 200, 175)
s.wire(192, 175, rl, 175)
s.wire(rr, 175, 208, 175)
s.wire(208, 175, 208, JY)
s.junction(208, JY)
s.sym("R", "RT2", "10k", 208, JY + 3.81)
s.gnd(208, JY + 7.62)
# grid leaks, both returned to the tail junction along the JY lane
s.wire(GL, 122, GL, 126)
s.junction(GL, 122)
s.sym("R", "RGA", "1M", GL, 129.81, lx=-9.4)
s.wire(GL, 133.62, GL, 135.5)
s.wire(GL, 135.5, RC, 135.5)
s.wire(RC, 135.5, RC, JY)
s.wire(GL, 158, GL, 162)
s.sym("R", "RGB", "1M", GL, 165.81, lx=-9.4)
s.wire(GL, 169.62, GL, JY)
s.junction(GL, 158)
s.wire(GL, 158, t3b["g"][0], 158)
# 0.1 uF AC coupling from the presence / feedback node up to the V3B grid
s.wire(174, 158, GL, 158)
s.wire(174, 158, 174, 166.19)
s.sym("C", "C14", ".1u", 174, 170, lx=-6.0, ly=3.0)
s.wire(174, 173.81, 174, JY)
# the tail-junction lane itself
s.wire(145, JY, RC, JY)
s.wire(RC, JY, 174, JY)
s.wire(174, JY, GL, JY)
s.wire(GL, JY, 208, JY)
s.junction(RC, JY)
s.junction(174, JY)
s.junction(GL, JY)

# ---- negative feedback + presence, at the tail junction --------------------
nl, nr = s.series_h("R", "RNFB", "47k", 141, JY)
s.wire(nr, JY, 145, JY)
s.wire(nl, JY, 134, JY)
s.glabel("SPKR", 134, JY, 180)
s.junction(160, JY)
s.wire(160, JY, 160, 188)
s.sym("POT", "VR6", "5k presence", 160, 191.81, lx=-14.0, ly=6.5)
s.wire(160, 195.62, 165.08, 195.62)        # free lug tied to the wiper
s.wire(165.08, 195.62, 165.08, 191.81)
s.wire(165.08, 191.81, 170, 191.81)
s.sym("C", "C13", ".1u", 170, 195.62, lx=2.2)
s.gnd(170, 199.43)
s.text("Presence: the 5 k pot works as a variable resistor into the 0.1 uF, "
       "shunting the", 60, 190, 1.15)
s.text("feedback node to ground at high frequency. Being DC-blocked it adds "
       "no series", 60, 194, 1.15)
s.text("resistance, so the inverter tail returns to ground through the 10 k "
       "alone.", 60, 198, 1.15)

# ======================= EL34 quartet, fixed bias ===========================
# Two valves per phase. Each PI plate drives a 0.022 uF coupler onto a grid
# line carrying one 120 k leak to the bias supply and a 5.6 k stopper per valve.
for plate_y, cref, glref, gcol, pairs in [
        (114.38, "C15", "RGL1", 228,
         [(55, "V4", "RS4", "RSC4"), (90, "V5", "RS5", "RSC5")]),
        (150.38, "C16", "RGL2", 232,
         [(165, "V6", "RS6", "RSC6"), (200, "V7", "RS7", "RSC7")])]:
    gys = [g for g, _, _, _ in pairs]
    top, bot = min(gys + [plate_y]), max(gys + [plate_y])
    s.wire(199, plate_y, 206, plate_y)
    s.junction(199, plate_y)
    cl, cr = s.series_h("C", cref, ".022u", 212, plate_y)
    s.wire(206, plate_y, cl, plate_y)
    s.wire(cr, plate_y, gcol, plate_y)
    s.wire(gcol, top, gcol, bot)
    for gy in gys + [plate_y]:
        if top < gy < bot:
            s.junction(gcol, gy)
    for gy, vref2, stref, scref in pairs:
        sl2, sr2 = s.series_h("R", stref, "5.6k", gcol + 6, gy)
        s.wire(gcol, gy, sl2, gy)
        p = s.pentode(vref2, "EL34", 252, gy, lx=-14.0, ly=4.0)
        s.wire(sr2, gy, p["g1"][0], gy)
        # 1 k screen stopper from the reservoir rail
        s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 1.9, p["g2"][1])
        sc1, sc2 = s.series_h("R", scref, "1k", p["g2"][0] + 5.71, p["g2"][1])
        s.wire(sc2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
        s.glabel("B+1", p["g2"][0] + 11.5, p["g2"][1], 0)
        s.gnd(252, p["k"][1])
    # 120 k grid leak for the pair -> adjustable bias line
    s.junction(gcol, bot)
    s.wire(gcol, bot, gcol, bot + 5.62)
    s.sym("R", glref, "120k", gcol, bot + 9.43, lx=-9.6)
    s.wire(gcol, bot + 13.24, gcol, bot + 15.78)
    s.glabel("-BIAS", gcol, bot + 15.78, 270)

# ---- output transformer ----------------------------------------------------
s.sym("OT_PP", "T1", "OT", 300, 130, lx=-6.35, ly=-14.0)
s.wire(252, 46.745, 252, 40)               # V4 plate
s.wire(252, 40, 284, 40)
s.wire(284, 40, 284, 124.92)
s.wire(252, 81.745, 252, 75)               # V5 plate joins the same primary end
s.wire(252, 75, 284, 75)
s.junction(284, 75)
s.wire(284, 124.92, 291.11, 124.92)
s.wire(252, 156.745, 252, 150)             # V6 plate
s.wire(252, 150, 288, 150)
s.wire(252, 191.745, 252, 185)             # V7 plate
s.wire(252, 185, 288, 185)
s.wire(288, 185, 288, 135.08)
s.junction(288, 150)
s.wire(288, 135.08, 291.11, 135.08)
s.wire(291.11, 130, 280, 130)              # primary centre tap -> reservoir rail
s.wire(280, 130, 280, 133)
s.glabel("B+1", 280, 133, 270)
s.wire(308.89, 127.46, 313, 127.46)
s.glabel("SPKR", 313, 127.46, 0)
s.wire(308.89, 132.54, 313, 132.54)
s.glabel("GND", 313, 132.54, 0)
s.text("16 / 8 / 4 ohm secondary taps; feedback is taken from the 16 ohm tap.",
       258, 148, 1.15)

# ======================= power supply — silicon bridge ======================
PY = 226.0
s.text("Power — universal-primary mains transformer (110/120/200/225/245 V) "
       "and HT winding; silicon bridge; series-pair 100 uF reservoir bank "
       "with 56 k sharing resistors;", 20, 214, 1.4)
s.text("a 20 k then two 10 k rail droppers, each node filtered by a pair of "
       "50 uF capacitors.", 20, 218.5, 1.4)
# bridge: two legs, each an upper and a lower arm between the rails
for x, dU, dL, lab, lx_off in [(44, "D2", "D4", "HT_A", -8), (64, "D3", "D5", "HT_B", 8)]:
    s.sym("DIODE_SS", dU, "A10D10", x, 232, rot=90, lx=2.6, ly=-1.2)
    s.wire(x, 226.92, x, PY)
    s.wire(x, 237.08, x, 244)
    s.sym("DIODE_SS", dL, "A10D10", x, 256, rot=90, lx=2.6, ly=-1.2)
    s.wire(x, 250.92, x, 244)
    s.wire(x, 261.08, x, 262)
    s.junction(x, 244)
    s.junction(x, PY)
    s.wire(x, 244, x + lx_off, 244)
    s.glabel(lab, x + lx_off, 244, 180 if lx_off < 0 else 0)
s.wire(44, PY, 64, PY)
s.wire(44, 262, 64, 262)
s.gnd(54, 262)
s.junction(54, 262)
# reservoir: two series pairs in parallel, 56 k sharing resistors across each half
s.wire(64, PY, 116, PY)
for x, lib, upper, lower, val in [(96, "C", "C19", "C20", "100u"),
                                  (104, "C", "C21", "C22", "100u"),
                                  (112, "R", "RB1", "RB2", "56k")]:
    s.sym(lib, upper, val, x, PY + 3.81)
    s.sym(lib, lower, val, x, PY + 11.43)
    s.junction(x, PY)
    s.junction(x, PY + 7.62)
s.wire(96, PY + 7.62, 112, PY + 7.62)
s.wire(96, PY + 15.24, 112, PY + 15.24)
s.gnd(104, PY + 15.24)
s.junction(96, PY + 15.24)
s.junction(112, PY + 15.24)
s.junction(116, PY)
s.wire(116, PY, 116, PY - 3)
s.glabel("B+1", 116, PY - 3, 90)
s.text("Reservoir: 100 uF cans in series pairs, the 56 k resistors sharing "
       "the rail across each half.", 124, 243, 1.15)
# dropper chain: 20k -> B+2 (phase inverter), 10k -> B+3, 10k -> B+4
s.wire(116, PY, 122.19, PY)
for x0, rref, rval, rail, cA, cB in [
        (126, "RD1", "20k", "B+2", "C23", "C24"),
        (158, "RD2", "10k", "B+3", "C25", "C26"),
        (190, "RD3", "10k", "B+4", "C27", "C28")]:
    dl, dr = s.series_h("R", rref, rval, x0, PY)
    s.wire(dr, PY, x0 + (18 if rref == "RD3" else 20), PY)   # the chain ends on its last can
    s.junction(x0 + 8, PY)
    s.wire(x0 + 8, PY - 3, x0 + 8, PY)
    s.glabel(rail, x0 + 8, PY - 3, 90)
    for cx, cref2 in [(x0 + 12, cA), (x0 + 18, cB)]:
        s.junction(cx, PY)
        s.sym("C", cref2, "50u", cx, PY + 3.81)
        s.gnd(cx, PY + 7.62)
    if rref != "RD3":
        s.wire(x0 + 20, PY, x0 + 28.19, PY)

# ======================= negative-bias supply ===============================
BY = 252.0
s.glabel("HT_B", 116, BY, 180)
s.wire(116, BY, 123.92, BY)
s.sym("DIODE_SS", "D1", "1008", 129, BY, rot=180, lx=-2.4, ly=-5.4, label_rot=0)
s.wire(134.08, BY, 146, BY)
s.junction(140, BY)
s.sym("R", "RBA", "27k", 140, BY + 3.81)
s.gnd(140, BY + 7.62)
s.junction(146, BY)
s.sym("C", "C17", "8u", 146, BY + 3.81, lx=2.2)
s.gnd(146, BY + 7.62)
bl2, br2 = s.series_h("R", "RBB", "15k", 156, BY)
s.wire(146, BY, bl2, BY)
s.wire(br2, BY, 166, BY)
s.junction(166, BY)
s.sym("C", "C18", "8u", 166, BY + 3.81, lx=2.2)
s.gnd(166, BY + 7.62)
cl2, cr2 = s.series_h("R", "RBC", "47k", 176, BY)
s.wire(166, BY, cl2, BY)
s.wire(cr2, BY, 186, BY)
s.sym("POT", "VR7", "27k bias adj", 186, BY + 3.81, lx=6.0, ly=-5.6)
s.gnd(186, BY + 7.62)
s.wire(191.08, BY + 3.81, 205, BY + 3.81)
s.glabel("-BIAS", 205, BY + 3.81, 0)
s.text("Bias supply: its own HT-tap diode, a 27 k bleeder and 15 k between "
       "the two 8 uF filters, then the 47 k / 27 k-trimmer divider that sets "
       "the grid bias.", 116, 266, 1.15)

# ---- parts the drawing annotates rather than wires -------------------------
s.sym("C", "C29", ".22u", 185, 276, lx=-2.8, ly=-5.6)
s.sym("C", "C30", ".22u", 201, 276, lx=-2.8, ly=-5.6)
s.sym("C", "C31", ".05u", 217, 276, lx=-2.8, ly=-5.6)
s.text("Annotated on the drawing and drawn here without connections: C29 / "
       "C30 0.22 uF snubbers at the HT winding", 20, 278, 1.2)
s.text("and C31 0.05 uF mains-to-chassis. The 4 A mains fuse, 1 A HT fuse, "
       "standby switch and pilot lamp", 20, 282, 1.2)
s.text("are annotations too, and the 6.3 V heater winding is omitted — see "
       "netlist.cir and meta.yaml.", 20, 286, 1.2)

s.write(OUT, [
    "Four EL34s in parallel push-pull off a silicon bridge — the 100 W head on the model 1987's front end. Heaters, PT primary and pilot lamp omitted.",
    "Channel I is the high-treble channel and channel II the normal channel; each has a high- and a low-sensitivity jack, and the two are voiced apart at the cathode.",
])
print(f"wrote {OUT}")
