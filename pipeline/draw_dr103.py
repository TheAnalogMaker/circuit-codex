#!/usr/bin/env python3
"""Generate amps/dr103/schematic.kicad_sch from the stage-template library.

The four-input Hiwatt DR103 "Custom 100" — see amps/dr103/meta.yaml for the
sources and amps/dr103/netlist.cir for the DC model this drawing carries.

Preamp values are read from the published four-input preamp drawing taken off
serial number 903 (title block: "HIWATT / Late 60s Four-Input Preamp / Preamp
from DR103 S/N 903 / Drawing rev. 1.0 - Mark Huss"); the output stage, the
supply and the control complement are read from the published early-1970s
wiring diagram of the same archive ("HIWATT DR103 LAYOUT, EARLY 1970'S",
credited on the sheet to Mark Huss with updates from Jukka K. and Brian
Haberman, 2007). Nothing is traced: this is a redraw from the values those
drawings letter.

Valve numbering follows both drawings, which agree with each other and with the
S/N 903 sheet's own "Preamp Tubes, View from Top of Chassis" key: V1 input (one
triode per channel, ONE shared cathode resistor), V2 second stage plus the
cathode follower that drives the tone stack, V3 driver plus a second cathode
follower, V4 the ECC81 long-tailed pair, V5-V8 the EL34 output quartet. Two
details separate this front end from the contemporary British lead amps it is
usually compared with: a master volume after the tone stack, and a V3B->V3A
coupling capacitor PARALLELED by a 1.8 MOhm resistor, so that stage is
DC-coupled through a divider against the 1 MOhm grid leak.

Heaters, the mains transformer and its primary taps, the fuses, the standby
switch, the mains neon and the speaker impedance selector are omitted (see
netlist.cir); the bias winding, the HT winding and the speaker return enter as
global labels.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "dr103" / "schematic.kicad_sch"
s = Sch()

MIXLINE_X = 110.0          # the two volume controls mix onto this column
V2_Y = 150.0               # the second-stage / driver row

# ======================= V1 input valve — two channels ======================
# Each channel: high + low jacks -> 68 k stoppers -> grid (1 M leak at the
# jacks); a 220 k plate load off the most-dropped rail; the channel's whole
# voicing in its coupling capacitor (1 nF Brilliant, 10 nF Normal) into a
# 470 k-A volume control and a 470 k mixing resistor. Unlike the Marshall lead
# heads the two halves are NOT voiced apart at the cathode — they share one
# 1.5 k resistor and one 100 uF bypass, drawn below.
for (y, hi, lo, sHi, sLo, gref, pref, plref, cpref, cpval, vref, mref,
     tlx, tly) in [
        (62, "BRILL HI", "BRILL LO", "R1s", "R2s", "RG1", "V1A", "RL1",
         "C2", "1n", "VR1", "RM1", 6.0, -6.4),
        (104, "NORM HI", "NORM LO", "R3s", "R4s", "RG2", "V1B", "RL2",
         "C3", "10n", "VR2", "RM2", -14.0, -11.0)]:
    t = s.triode(pref, "ECC83", 54, y, lx=tlx, ly=tly)
    gx = t["g"][0]
    s.glabel(hi, 20, y - 4, 180)
    s.wire(20, y - 4, 26, y - 4)
    hl, hr = s.series_h("R", sHi, "68k", 31, y - 4)
    s.wire(26, y - 4, hl, y - 4)
    s.wire(hr, y - 4, gx - 3.81, y - 4)
    s.wire(gx - 3.81, y - 4, gx - 3.81, y)
    s.glabel(lo, 20, y + 6, 180)
    s.wire(20, y + 6, 26, y + 6)
    ll, lr = s.series_h("R", sLo, "68k", 31, y + 6)
    s.wire(26, y + 6, ll, y + 6)
    s.wire(lr, y + 6, gx - 3.81, y + 6)
    s.wire(gx - 3.81, y + 6, gx - 3.81, y)
    s.junction(gx - 3.81, y)
    s.wire(gx - 3.81, y, gx, y)
    s.sym("R", gref, "1M", gx - 3.81, y + 9, lx=-9.4)
    s.gnd(gx - 3.81, y + 12.81)
    s.plate_load(plref, "220k", t["p"], "B+5")
    # plate stub -> coupler -> volume control -> mixing resistor -> mix column
    ty = y - 7.62 - 3.48
    s.wire(54, ty, 70, ty)
    s.junction(54, ty)
    cl, cr = s.series_h("C", cpref, cpval, 74, ty)
    s.wire(cl, ty, 70, ty)
    s.wire(cr, ty, 88, ty)
    s.sym("POT", vref, "470k-A", 88, ty + 3.81)
    s.wire(88, ty + 7.62, 88, ty + 9.5)
    s.gnd(88, ty + 9.5)
    s.wire(93.08, ty + 3.81, 96.19, ty + 3.81)
    ml, mr = s.series_h("R", mref, "470k", 100, ty + 3.81)
    s.wire(mr, ty + 3.81, MIXLINE_X, ty + 3.81)
    s.wire(MIXLINE_X, ty + 3.81, MIXLINE_X, V2_Y)

# The shared cathode: both halves down to ONE 1.5 k / 100 uF network, drawn
# clear of both bottles. The tie column at x=60 crosses the V1B plate stub's
# coupler tee without a junction — two nets, one crossing.
s.wire(54, 69.62, 54, 73)
s.wire(54, 73, 60, 73)
s.wire(60, 73, 60, 122)
s.wire(54, 111.62, 54, 122)
s.wire(54, 122, 60, 122)
s.wire(60, 122, 68, 122)
s.shunt_rc("RK1", "1k5", "C1", "100u", 68, 122)
s.note('V1 shares ONE cathode resistor between the two channels — they are voiced apart by their coupling capacitors, not at the cathode.')
s.junction(MIXLINE_X, 96.71)
s.junction(MIXLINE_X, V2_Y)

# ================== V2B second stage + V2A cathode follower =================
t2b = s.triode("V2B", "ECC83", 120, V2_Y)
s.wire(MIXLINE_X, V2_Y, t2b["g"][0], V2_Y)
s.plate_load("RL3", "220k", t2b["p"], "B+4")
s.wire(120, V2_Y + 7.62, 120, V2_Y + 10)
s.wire(120, V2_Y + 10, 126, V2_Y + 10)
s.sym("R", "RK2", "2k2", 126, V2_Y + 13.81)     # unbypassed
s.gnd(126, V2_Y + 17.62)
tee = V2_Y - 7.62 - 3.48
s.wire(120, tee, 128, tee)
s.junction(120, tee)
t2a = s.triode("V2A", "ECC83 CF", 136, V2_Y)
s.wire(128, tee, 128, V2_Y)
s.wire(128, V2_Y, t2a["g"][0], V2_Y)
s.wire(136, V2_Y - 7.62, 136, V2_Y - 10.5)
s.glabel("B+3", 136, V2_Y - 10.5, 90)
s.wire(136, V2_Y + 7.62, 136, V2_Y + 10.5)
s.junction(136, V2_Y + 10.5)
s.sym("R", "RKCF", "120k 2W", 136, V2_Y + 14.31, lx=-15.0)
s.gnd(136, V2_Y + 18.12)

# ================ FMV tone stack, driven by the cathode follower ============
# Wired as the S/N 903 drawing draws it — the ladder every British lead sheet
# of the period uses: node A (the follower's cathode) carries the 100 pF and
# the 100 k slope; the slope's foot carries the two 47 nF capacitors; the bass
# control is a rheostat with its wiper strapped to its hot lug; the middle
# capacitor lands on the MIDDLE POT'S WIPER; and the stack's output is the
# TREBLE WIPER ALONE, through a 220 k series resistor into the master volume.
CF = V2_Y + 10.5
s.wire(136, CF, 143, CF)
s.sym("R", "RSL", "100k", 147, CF, rot=90, lx=2.0, ly=-6.0)
sl, sr = (143.19, 150.81)
s.wire(143, CF, sl, CF)
s.junction(143, CF)
s.wire(143, CF, 143, 136)                    # node A riser to the 100 pF branch
s.wire(sr, CF, 155, CF)
s.junction(155, CF)
s.wire(155, CF, 155, 148)                    # node B riser, up to the bass cap
s.wire(155, CF, 155, 170)                    # node B riser, down to the mid cap
tl, tr = s.series_h("C", "C4", "100p", 159, 136)
s.wire(143, 136, tl, 136)
s.wire(tr, 136, 166, 136)
s.sym("POT", "VR3", "220k treb", 166, 139.81, lx=13.0)
bl, br = s.series_h("C", "C5", "47n", 159, 148)
s.wire(155, 148, bl, 148)
s.wire(br, 148, 166, 148)
s.wire(166, 143.62, 166, 148)                # treble bottom lug -> bass node
s.junction(166, 148)
s.sym("POT", "VR4", "470k-A bass", 166, 151.81, lx=13.0)
s.wire(171.08, 151.81, 175, 151.81)          # bass wiper strapped to its hot lug
s.wire(175, 151.81, 175, 148)
s.wire(175, 148, 166, 148)
s.sym("C", "C6", "47n", 159, 170, rot=90, lx=2.0, ly=-6.2)
mcl, mcr = (155.19, 162.81)
s.wire(155, 170, mcl, 170)
s.wire(mcr, 170, 173.6, 170)
s.wire(173.6, 170, 173.6, 161.81)
s.wire(173.6, 161.81, 171.08, 161.81)        # -> the middle pot's wiper
s.wire(166, 155.62, 166, 158)                # bass foot -> middle top
s.sym("POT", "VR5", "22k mid", 166, 161.81, lx=13.0)
s.gnd(166, 165.62)
# stack output: the treble wiper alone -> 220 k -> master volume
s.wire(171.08, 139.81, 176, 139.81)
s.wire(176, 139.81, 176, 130)
tml, tmr = s.series_h("R", "RTM", "220k", 183, 130)
s.wire(176, 130, tml, 130)
s.wire(tmr, 130, 190, 130)
s.sym("POT", "VR6", "470k-A master", 190, 133.81, lx=2.4, ly=-8.0)
s.gnd(190, 137.62)

# ================= V3B driver + V3A second cathode follower =================
t3b = s.triode("V3B", "ECC83", 210, V2_Y)
s.wire(195.08, 133.81, 199, 133.81)
s.wire(199, 133.81, 199, V2_Y)
s.wire(199, V2_Y, t3b["g"][0], V2_Y)
s.plate_load("RL4", "100k", t3b["p"], "B+5")
s.wire(210, V2_Y + 7.62, 210, V2_Y + 10)
s.wire(210, V2_Y + 10, 216, V2_Y + 10)
s.shunt_rc("RK3", "2k2", "C7", "47n", 216, V2_Y + 10)
# V3B plate -> the V3A grid through 22 nF PARALLELED BY 1.8 M: a DC-coupled
# divider against the 1 M grid leak, which is what lifts the phase inverter's
# grid reference in this amplifier.
PT_Y = V2_Y - 11.1                            # V3B plate stub top
s.wire(210, PT_Y, 216, PT_Y)
s.junction(210, PT_Y)
s.wire(216, PT_Y, 216, 131)
s.junction(216, PT_Y)
c8l, c8r = s.series_h("C", "C8", "22n", 222, PT_Y)
s.wire(216, PT_Y, c8l, PT_Y)
r18l, r18r = s.series_h("R", "R18", "1M8", 222, 131)
s.wire(216, 131, r18l, 131)
s.wire(c8r, PT_Y, 229, PT_Y)
s.wire(r18r, 131, 229, 131)
s.wire(229, 131, 229, PT_Y)
s.junction(229, PT_Y)
s.wire(229, PT_Y, 229, V2_Y)
t3a = s.triode("V3A", "ECC83 CF", 240, V2_Y)
s.wire(229, V2_Y, t3a["g"][0], V2_Y)
s.junction(229, V2_Y)
s.wire(229, V2_Y, 229, V2_Y + 2)
s.sym("R", "RG3", "1M", 229, V2_Y + 5.81, lx=-9.4)
s.gnd(229, V2_Y + 9.62)
s.wire(240, V2_Y - 7.62, 240, V2_Y - 10.5)
s.glabel("B+5", 240, V2_Y - 10.5, 90)
s.wire(240, V2_Y + 7.62, 240, V2_Y + 11)
s.junction(240, V2_Y + 11)
s.sym("R", "RKCF2", "220k", 240, V2_Y + 14.81, lx=3.0, ly=1.0)
s.gnd(240, V2_Y + 18.62)

# ================= V4 ECC81 long-tailed-pair phase inverter =================
# The V3A cathode IS the V4A grid node — no coupling capacitor between them.
V4A_Y, V4B_Y = 126.0, 174.0
t4a = s.triode("V4A", "ECC81", 266, V4A_Y)
t4b = s.triode("V4B", "ECC81", 266, V4B_Y, lx=9.5)
s.wire(240, V2_Y + 11, 243, V2_Y + 11)
s.wire(243, V2_Y + 11, 243, V4A_Y)
s.wire(243, V4A_Y, t4a["g"][0], V4A_Y)
s.junction(250, V4A_Y)
s.wire(250, V4A_Y, 250, 146)                  # 1 M between the two grids
s.sym("R", "RGB", "1M", 250, 149.81, lx=3.0, ly=5.0)
s.wire(250, 153.62, 250, V4B_Y)
s.wire(250, V4B_Y, t4b["g"][0], V4B_Y)
s.plate_load("RLA", "82k", t4a["p"], "B+3")   # driven side -> Output 1
s.plate_load("RLB", "91k", t4b["p"], "B+3")   # deliberately unequal
# shared tail: cathodes -> 22 k -> the feedback junction -> 2.2 k -> ground
s.wire(266, V4A_Y + 7.62, 266, 137)
s.wire(266, 137, 272, 137)
s.wire(266, V4B_Y + 7.62, 266, 185)
s.wire(266, 185, 272, 185)
s.wire(272, 137, 272, 196)
s.junction(272, 185)
rtl, rtr = s.series_h("R", "RTAIL", "22k", 280, 196)
s.wire(272, 196, rtl, 196)
s.wire(rtr, 196, 290, 196)
s.wire(290, 196, 290, 204)
JY = 204.0
s.junction(290, JY)
s.sym("R", "RT2", "2k2", 290, JY + 3.81)
s.gnd(290, JY + 7.62)
# 100 nF from the V4B grid down to the feedback junction (signal reference)
s.junction(254, V4B_Y)
s.wire(254, V4B_Y, 254, 184.19)
s.sym("C", "C9", "100n", 254, 188, lx=-6.6, ly=3.2)
s.wire(254, 191.81, 254, JY)
s.junction(254, JY)
# ---- negative feedback + presence, at the tail junction --------------------
nl, nr = s.series_h("R", "RNFB", "10k", 240, JY)
s.wire(nr, JY, 254, JY)
s.wire(nl, JY, 230, JY)
s.glabel("SPKR", 230, JY, 180)
s.wire(254, JY, 290, JY)
s.junction(268, JY)
s.wire(268, JY, 268, 208)
s.sym("R", "RPD", "270", 268, 211.81)
s.wire(268, 215.62, 268, 219)
s.sym("C", "C10", "10n", 268, 222.81, lx=2.4)
s.gnd(268, 226.62)
# presence: 1 nF off the V3B plate, through the 100 k control, 47 nF back into
# the feedback junction; the wiper shunts to ground through 100 ohms.
s.wire(206, PT_Y, 210, PT_Y)
s.wire(206, PT_Y, 206, 224)
c11l, c11r = s.series_h("C", "C11", "1n", 212, 224)
s.wire(206, 224, c11l, 224)
s.sym("POT", "VR7", "100k presence", 222, 224, rot=270, lx=-9.0, ly=-11.0)
s.wire(c11r, 224, 218.19, 224)
s.wire(222, 229.08, 222, 231)
s.sym("R", "RPG", "100", 222, 234.81)
s.gnd(222, 238.62)
c12l, c12r = s.series_h("C", "C12", "47n", 232, 224)
s.wire(225.81, 224, c12l, 224)
s.wire(c12r, 224, 260, 224)
s.wire(260, 224, 260, JY)
s.junction(260, JY)
s.text("Presence and negative feedback both land on the phase-inverter tail "
       "junction. Every branch of the presence network is DC-blocked, so the "
       "control moves no operating point,", 20, 214, 1.2)
s.text("and the inverter's tail returns to ground through the 2.2 k alone.",
       20, 218, 1.2)

# ==================== V5-V8 EL34 quartet, fixed bias ========================
# Two valves per phase. Each phase-inverter plate drives a 47 nF coupler onto a
# grid line carrying one 100 k leak to the bias supply and a 22 k stopper per
# valve — four times the stopper the Marshall lead heads use.
for plate_y, cref, glref, gcol, pairs in [
        (V4A_Y - 11.1, "C13", "RGL1", 294,
         [(52, "V5", "RS5", "RSC5"), (87, "V6", "RS6", "RSC6")]),
        (V4B_Y - 11.1, "C14", "RGL2", 300,
         [(190, "V7", "RS7", "RSC7"), (225, "V8", "RS8", "RSC8")])]:
    gys = [g for g, _, _, _ in pairs]
    top, bot = min(gys + [plate_y]), max(gys + [plate_y])
    # The tee runs THROUGH the tail column at x=272 rather than ending on it:
    # a plain crossing, no junction — the phase-B coupler and the inverter tail
    # are different nets and the drawing must not join them.
    s.wire(266, plate_y, 274, plate_y)
    s.junction(266, plate_y)
    cl, cr = s.series_h("C", cref, "47n", 280, plate_y)
    s.wire(274, plate_y, cl, plate_y)
    s.wire(cr, plate_y, gcol, plate_y)
    s.wire(gcol, top, gcol, bot)
    for gy in gys + [plate_y]:
        if top < gy < bot:
            s.junction(gcol, gy)
    for gy, vref2, stref, scref in pairs:
        sl2, sr2 = s.series_h("R", stref, "22k", gcol + 7, gy)
        s.wire(gcol, gy, sl2, gy)
        p = s.pentode(vref2, "EL34", 330, gy, lx=-14.6, ly=4.4)
        s.wire(sr2, gy, p["g1"][0], gy)
        s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 1.9, p["g2"][1])
        sc1, sc2 = s.series_h("R", scref, "100", p["g2"][0] + 5.71, p["g2"][1])
        s.wire(sc2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
        s.glabel("B+SCR", p["g2"][0] + 11.5, p["g2"][1], 0)
        s.gnd(330, p["k"][1])
    s.junction(gcol, bot)
    s.wire(gcol, bot, gcol, bot + 5.62)
    s.sym("R", glref, "100k", gcol, bot + 9.43, lx=-9.6)
    s.wire(gcol, bot + 13.24, gcol, bot + 15.78)
    s.glabel("-BIAS", gcol, bot + 15.78, 270)

# ---- output transformer ----------------------------------------------------
s.sym("OT_PP", "T1", "OT", 378, 145, lx=-6.35, ly=-14.0)
s.wire(330, 43.745, 330, 38)                  # V5 plate
s.wire(330, 38, 356, 38)
s.wire(356, 38, 356, 139.92)
s.wire(330, 78.745, 330, 73)                  # V6 plate, same primary end
s.wire(330, 73, 356, 73)
s.junction(356, 73)
s.wire(356, 139.92, 369.11, 139.92)
s.wire(330, 181.745, 330, 176)                # V7 plate
s.wire(330, 176, 362, 176)
s.wire(330, 216.745, 330, 211)                # V8 plate
s.wire(330, 211, 362, 211)
s.wire(362, 211, 362, 150.08)
s.junction(362, 176)
s.wire(362, 150.08, 369.11, 150.08)
s.wire(369.11, 145, 366, 145)                 # primary centre tap -> reservoir
s.glabel("B+1", 366, 145, 180)
s.wire(386.89, 142.46, 392, 142.46)
s.glabel("SPKR", 392, 142.46, 0)
s.wire(386.89, 147.54, 392, 147.54)
s.glabel("GND", 392, 147.54, 0)
s.text("4 / 8 / 16 ohm taps through a rotary", 366, 166, 1.15)
s.text("selector; feedback off the 16 ohm tap.", 366, 170, 1.15)
s.text("Two EL34s per phase in parallel push-pull, each with its own 22 k grid "
       "stopper and 100 ohm screen stopper;", 300, 250, 1.15)
s.text("one 100 k grid leak serves each pair. The screens run off their own "
       "470 ohm feed, below the plate rail.", 300, 254, 1.15)

# ======================= power supply — silicon bridge ======================
PY = 246.0
s.text("Power — mains transformer with 100 / 117.5 / 225 / 250 V primary taps "
       "(omitted); silicon bridge of four UF5408s; a series-pair 220 uF "
       "reservoir bank with 220 k sharing resistors;", 20, 232, 1.35)
s.text("100 ohm / 1 k / 47 k / 22 k rail droppers, and a 470 ohm feed to the "
       "EL34 screens. C19 is a two-section 50 uF can in one housing: RB5 and "
       "RB6 balance its halves, and their junction is the can's mid-point.",
       20, 237, 1.35)
for x, dU, dL, lab, lx_off in [(44, "D1", "D3", "HT_A", -8),
                               (64, "D2", "D4", "HT_B", 8)]:
    s.sym("DIODE_SS", dU, "UF5408", x, 252, rot=90, lx=2.6, ly=-1.2)
    s.wire(x, 246.92, x, PY)
    s.wire(x, 257.08, x, 264)
    s.sym("DIODE_SS", dL, "UF5408", x, 276, rot=90, lx=2.6, ly=-1.2)
    s.wire(x, 270.92, x, 264)
    s.wire(x, 281.08, x, 282)
    s.junction(x, 264)
    s.junction(x, PY)
    s.wire(x, 264, x + lx_off, 264)
    s.glabel(lab, x + lx_off, 264, 180 if lx_off < 0 else 0)
s.wire(44, PY, 64, PY)
s.wire(44, 282, 64, 282)
s.gnd(54, 282)
s.junction(54, 282)
# reservoir: two 220 uF cans in series, 220 k resistors sharing the rail
s.wire(64, PY, 116, PY)
for x, lib, upper, lower, val in [(96, "C", "C17", "C18", "220u"),
                                  (112, "R", "RB3", "RB4", "220k")]:
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
# dropper chain: 100 R -> B+2 (and the 470 R screen feed), 1 k -> B+3,
# 47 k -> B+4, 22 k -> B+5
d1l, d1r = s.series_h("R", "RD1", "100 5W", 124, PY)
s.wire(116, PY, d1l, PY)
s.wire(d1r, PY, 132, PY)
s.junction(132, PY)
s.wire(132, PY, 132, PY - 3)
s.glabel("B+2", 132, PY - 3, 90)
s.junction(137, PY)
s.sym("C", "C19", "2x50u", 137, PY + 3.81)
s.gnd(137, PY + 7.62)
s.wire(132, PY, 149, PY)
s.junction(143, PY)
s.sym("R", "RB5", "220k", 143, PY + 3.81)
s.sym("R", "RB6", "220k", 143, PY + 11.43)
s.junction(143, PY + 7.62)
s.gnd(143, PY + 15.24)
s.junction(149, PY)
s.sym("R", "RD2", "470 10W", 149, PY + 3.81, lx=2.4)
s.wire(149, PY + 7.62, 149, PY + 10.5)
s.glabel("B+SCR", 149, PY + 10.5, 270)
d3l, d3r = s.series_h("R", "RD3", "1k 2W", 157, PY)
s.wire(149, PY, d3l, PY)
s.wire(d3r, PY, 165, PY)
s.junction(165, PY)
s.wire(165, PY, 165, PY - 3)
s.glabel("B+3", 165, PY - 3, 90)
s.junction(170, PY)
s.sym("C", "C20", "220u", 170, PY + 3.81)
s.gnd(170, PY + 7.62)
s.junction(176, PY)
s.sym("R", "RB7", "220k", 176, PY + 3.81)
s.gnd(176, PY + 7.62)
s.wire(165, PY, 180.19, PY)
d4l, d4r = s.series_h("R", "RD4", "47k 2W", 184, PY)
s.wire(d4r, PY, 192, PY)
s.junction(192, PY)
s.wire(192, PY, 192, PY - 3)
s.glabel("B+4", 192, PY - 3, 90)
s.junction(197, PY)
s.sym("C", "C21", "32u", 197, PY + 3.81)
s.gnd(197, PY + 7.62)
s.wire(192, PY, 201.19, PY)
d5l, d5r = s.series_h("R", "RD5", "22k 2W", 205, PY)
s.wire(d5r, PY, 218, PY)
s.junction(213, PY)
s.wire(213, PY, 213, PY - 3)
s.glabel("B+5", 213, PY - 3, 90)
s.junction(218, PY)
s.sym("C", "C22", "16u", 218, PY + 3.81)
s.gnd(218, PY + 7.62)

# ======================= negative-bias supply ===============================
BY = 272.0
s.glabel("BIAS_AC", 150, BY, 180)
s.wire(150, BY, 159.19, BY)
b1l, b1r = s.series_h("R", "RB1", "1k 2W", 163, BY)
s.sym("DIODE_SS", "D5", "UF5408", 175, BY, rot=180, lx=-2.4, ly=-5.4, label_rot=0)
s.wire(b1r, BY, 169.92, BY)
s.wire(180.08, BY, 186, BY)
s.junction(186, BY)
s.sym("C", "C16", "100u 63V", 186, BY + 3.81, lx=2.4)
s.gnd(186, BY + 7.62)
s.wire(186, BY, 194, BY)
s.junction(194, BY)
s.sym("R", "RB2", "47k", 194, BY + 3.81)
s.gnd(194, BY + 7.62)
s.wire(194, BY, 206, BY)
s.glabel("-BIAS", 206, BY, 0)
s.text("Bias supply: its own transformer tap through a 1 k series resistor, a "
       "UF5408, a 100 uF filter and a 47 k bleeder. There is no bias trimmer "
       "on either drawing read for this entry —", 20, 288, 1.2)
s.text("the two 100 k grid leaks return the output grids to this line as it "
       "stands. The Issue-3 factory supply sheet of 22/11/94 prints "
       "BIAS (-38 V) for the same network.", 20, 292, 1.2)

s.write(OUT, [
    "Four inputs across two channels into a shared-cathode ECC83, a cathode-follower FMV stack with a master volume, a second cathode follower, an ECC81 long-tailed pair and four EL34s.",
    "Heaters, the mains transformer, the standby switch, the fuses, the mains neon and the speaker impedance selector are omitted — see netlist.cir and meta.yaml.",
])
print(f"wrote {OUT}")
