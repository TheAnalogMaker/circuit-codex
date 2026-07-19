#!/usr/bin/env python3
"""Generate amps/m1987/schematic.kicad_sch from the stage-template library.

Values per the published Marshall model 1987 factory drawing (Unicord 70-19-11,
July 1970) — see amps/m1987/meta.yaml. The 1987 is the EL34 evolution of the
JTM45: the same four-input two-channel front end, DC-coupled cathode follower and
long-tailed-pair inverter, but with a pair of EL34 pentodes for the JTM45's KT66
beam tetrodes and a silicon full-wave rectifier for the GZ34.

Valve numbering follows the drawing: V1 input (two channels, one triode each),
V2 second stage + cathode follower, V3 long-tailed-pair phase inverter, V4/V5
EL34 output. The two input channels are deliberately unmatched — the bright
channel runs an 820R cathode fully bypassed (320uF), the normal channel a colder
2.7k with a 0.68uF partial bypass.

Heaters, the PT primary and the pilot lamp are omitted (see netlist.cir); the
power section shows the silicon rectifier, reservoir, choke, dropper chain and the
diode/220k/15k/25k negative-bias supply.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "m1987" / "schematic.kicad_sch"
s = Sch()

# ============================ V1 input — two channels =======================
# Each channel: high + low input jacks -> 68k stoppers -> grid (1M leak); 100k
# plate load to B+5; its own cathode bias; plate -> coupler -> 1M volume (bright
# cap + 470k bright resistor) -> 470k mixer into the shared V2A grid line.
MIXLINE_X = 100.0
for (y, hi, lo, sHi, sLo, gref, pref, plref, kref, kval, cbref, cbval,
     cpref, cpval, vref, brC, brCval, brR, mref) in [
        (92, "BRIGHT HI", "BRIGHT LO", "R1s", "R2s", "RG1", "V1A", "RL1",
         "RK1", "820", "C1", "320u", "C3", ".022u", "VR1", "C5", ".005u", "RB1", "RM1"),
        (128, "NORMAL HI", "NORMAL LO", "R3s", "R4s", "RG2", "V1B", "RL2",
         "RK2", "2.7k", "C2", ".68u", "C4", ".0022u", "VR2", "C6", "500p", "RB2", "RM2")]:
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
    # 1M grid leak to ground
    s.sym("R", gref, "1M", gx - 3.81, y + 9, lx=-9.4)
    s.gnd(gx - 3.81, y + 12.81)
    # plate load 100k to B+5
    s.plate_load(plref, "100k", t["p"], "B+5")
    # cathode bias R + bypass cap
    s.wire(54, y + 7.62, 54, y + 10)
    s.wire(54, y + 10, 60, y + 10)
    s.shunt_rc(kref, kval, cbref, cbval, 60, y + 10)
    s.gnd(60, y + 10)
    # plate stub -> coupler -> volume pot
    ty = y - 7.62 - 3.48
    s.wire(54, ty, 66, ty)
    s.junction(54, ty)
    cl, cr = s.series_h("C", cpref, cpval, 70, ty)
    s.wire(cl, ty, 66, ty)
    s.wire(cr, ty, 80, ty)
    s.sym("POT", vref, "1M vol", 80, ty + 3.81)
    s.wire(80, ty + 7.62, 80, ty + 9.5)
    s.gnd(80, ty + 9.5)
    # bright network across the volume pot (top -> wiper): cap ‖ resistor
    s.sym("C", brC, brCval, 80, ty - 4.5, lx=2.4)
    s.wire(80, ty, 80, ty - 0.7)
    s.wire(80, ty - 8.3, 88, ty - 8.3)
    s.wire(88, ty - 8.3, 88, ty + 3.81)
    s.sym("R", brR, "470k", 84, ty - 8.3, rot=90, lx=-3.2, ly=-6.0)
    s.junction(85.09, ty + 3.81)
    # wiper -> 470k mixer -> shared V2A grid line
    s.wire(85.09, ty + 3.81, 88, ty + 3.81)
    ml, mr = s.series_h("R", mref, "470k", 92, ty + 3.81)
    s.wire(88, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, MIXLINE_X, ty + 3.81)
    s.wire(MIXLINE_X, ty + 3.81, MIXLINE_X, 110)
s.junction(MIXLINE_X, 110)

# ==================== V2A second stage + V2B cathode follower ================
t2a = s.triode("V2A", "ECC83", 110, 110)
s.wire(MIXLINE_X, 110, t2a["g"][0], 110)
# cathode 820R + 0.68u bypass
s.wire(110, 117.62, 110, 120)
s.wire(110, 120, 116, 120)
s.shunt_rc("RK3", "820", "C7", ".68u", 116, 120)
s.gnd(116, 120)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# DC-coupled cathode follower: grid from the V2A plate stub tee
tee = 110 - 7.62 - 3.48
s.wire(110, tee, 118, tee)
s.junction(110, tee)
t2b = s.triode("V2B", "ECC83 CF", 126, 110)
s.wire(118, tee, 118, 110)
s.wire(118, 110, t2b["g"][0], 110)
s.wire(126, 102.38, 126, 99.5)
s.glabel("B+4", 126, 99.5, 90)            # CF plate straight to the rail
s.wire(126, 117.62, 126, 120.5)
s.junction(126, 120.5)
s.sym("R", "RKCF", "100k", 126, 124.31)
s.gnd(126, 128.12)

# ======================= TMB tone stack (cathode-follower fed) ===============
# 33k slope; 500p treble / 250k; 0.022 bass / 1M; 0.022 mid / 25k.
s.wire(126, 120.5, 133, 120.5)
sl, sr = s.series_h("R", "RSL", "33k", 137, 120.5)
s.wire(133, 120.5, sl, 120.5)
s.wire(sr, 120.5, 145, 120.5)
s.wire(145, 120.5, 145, 96)
s.junction(145, 108)
# treble branch: 500p -> 250k treble pot
tl, tr = s.series_h("C", "C8", "500p", 149, 96)
s.wire(tr, 96, 156, 96)
s.wire(145, 96, tl, 96)
s.sym("POT", "VR3", "250k treb", 156, 99.81)
# bass branch: 0.022 -> 1M bass pot
bl, br = s.series_h("C", "C9", ".022u", 149, 108)
s.wire(145, 108, bl, 108)
s.wire(br, 108, 156, 108)
s.wire(156, 103.62, 156, 108)             # treble pot bottom joins bass top
s.sym("POT", "VR4", "1M bass", 156, 111.81)
s.wire(156, 115.62, 156, 118)
s.sym("POT", "VR5", "25k mid", 156, 121.81)
# mid cap in series with the mid pot to ground
s.wire(156, 125.62, 156, 128)
s.sym("C", "C10", ".022u", 156, 131.81)
s.gnd(156, 135.62)
s.wire(161.08, 121.81, 163.6, 121.81)     # mid wiper tied to its top
s.wire(163.6, 121.81, 163.6, 118)
s.wire(163.6, 118, 156, 118)
s.junction(156, 118)
# treble wiper = stack output
s.wire(161.08, 99.81, 165, 99.81)
s.wire(165, 99.81, 165, 92)

# ===================== V3 long-tailed-pair phase inverter ===================
ol, orr = s.series_h("C", "C11", ".022u", 169, 92)
s.wire(165, 92, ol, 92)
s.wire(orr, 92, 170.4, 92)
t3a = s.triode("V3A", "ECC83", 178, 92)
s.wire(170.4, 92, t3a["g"][0], 92)
t3b = s.triode("V3B", "ECC83", 178, 128)
s.plate_load("RLA", "100k", t3a["p"], "B+3")
s.plate_load("RLB", "82k", t3b["p"], "B+3")
# 47pF plate-to-plate compensation
s.wire(178, 84.38, 191, 84.38)
s.junction(178, 84.38)
s.sym("C", "C12", "47p", 191, 84.38, rot=90, lx=-3.2, ly=-6.2)
s.wire(191, 88.19, 191, 120.38)
s.wire(178, 120.38, 191, 120.38)
s.junction(178, 120.38)
# shared tail: cathodes -> 470 -> J -> 10k -> gnd
s.wire(178, 99.62, 178, 102)
s.wire(178, 102, 184, 102)
s.wire(178, 135.62, 178, 138)
s.wire(178, 138, 184, 138)
s.wire(184, 102, 184, 138)
s.junction(184, 110)
s.sym("R", "RTAIL", "470", 189, 110 + 3.81, lx=2.0)
s.wire(184, 110, 189, 110)
s.junction(189, 117.62)
s.sym("R", "RT2", "10k", 189, 121.43)
s.gnd(189, 125.24)
# grid leaks to the tail junction
s.wire(170.4, 92, 170.4, 99)
s.junction(170.4, 92)
s.sym("R", "RGA", "1M", 170.4, 102.81, lx=-9.4)
s.wire(170.4, 106.62, 170.4, 117.62)
s.wire(170.4, 117.62, 189, 117.62)
s.wire(170.4, 128, 170.4, 124)            # bottom grid AC-grounded / DC to J
s.wire(170.4, 128, t3b["g"][0], 128)
s.junction(170.4, 128)
s.sym("R", "RGB", "1M", 170.4, 119.19, lx=-9.4)
s.text("Presence + NFB (27k) join the tail foot at ~0 V DC (annotation)", 150, 148, 1.1)

# ======================= EL34 pair, fixed bias ==============================
for gy, pref, cref, glref in [(88, "V4", "C13", "RGL1"), (140, "V5", "C14", "RGL2")]:
    if gy == 88:
        s.wire(178, 80.9, 196, 80.9)          # V3A plate tee
        s.junction(178, 80.9)
        cl, cr = s.series_h("C", cref, ".022u", 200, 80.9)
        s.wire(196, 80.9, cl, 80.9)
        s.wire(cr, 80.9, 209, 80.9)
        s.wire(209, 80.9, 209, gy)
    else:
        s.wire(178, 116.9, 196, 116.9)        # V3B plate tee
        s.junction(178, 116.9)
        cl, cr = s.series_h("C", cref, ".022u", 200, 116.9)
        s.wire(196, 116.9, cl, 116.9)
        s.wire(cr, 116.9, 209, 116.9)
        s.wire(209, 116.9, 209, gy)
    p = s.pentode(pref, "EL34", 222, gy)
    s.wire(209, gy, p["g1"][0], gy)
    s.junction(209, gy)
    # 220k grid leak to the bias line
    s.sym("R", glref, "220k", 209, gy + 3.81)
    s.wire(209, gy + 7.62, 209, gy + 10.16)
    s.glabel("-BIAS", 209, gy + 10.16, 270)
    # screen straight to B+2
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 3, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 3, p["g2"][1], 0)
    s.gnd(222, p["k"][1])

# ---- output transformer ----------------------------------------------------
s.sym("OT_PP", "T1", "OT", 250, 114)
s.wire(222, 88 - 0.635 - 7.62, 222, 77.5)
s.wire(222, 77.5, 241, 77.5)
s.wire(241, 77.5, 241, 108.92)
s.wire(222, 140 - 0.635 - 7.62, 222, 130.5)
s.wire(222, 130.5, 236, 130.5)
s.wire(236, 130.5, 236, 119.08)
s.wire(236, 119.08, 241, 119.08)
s.wire(241, 114, 238.5, 114)
s.wire(238.5, 114, 238.5, 111)
s.glabel("B+1", 238.5, 111, 90)
s.wire(258.89, 111.46, 261.4, 111.46)
s.glabel("SPKR", 261.4, 111.46, 0)
s.wire(258.89, 116.54, 261.4, 116.54)
s.glabel("GND", 261.4, 116.54, 0)

# ======================= power supply — silicon rectifier ===================
s.text("Power — universal-primary PT (110/120/200/225/245 V) + HT winding; "
       "silicon full-wave rectifier; 50u+80u reservoir; choke; 10k/47k/10k "
       "droppers", 24, 160, 1.4)
# HT winding (global labels) -> two rectifier diodes -> reservoir B+1
s.glabel("HT_A", 26, 170, 180)
s.wire(26, 170, 30, 170)
s.sym("DIODE_SS", "D2", "1N4007", 35, 170, lx=-2.0, ly=-5.4)
s.glabel("HT_B", 26, 178, 180)
s.wire(26, 178, 30, 178)
s.sym("DIODE_SS", "D3", "1N4007", 35, 178, lx=-2.0, ly=5.0)
s.wire(40.08, 170, 44, 170)
s.wire(40.08, 178, 44, 178)
s.wire(44, 170, 44, 178)
s.junction(44, 174)
s.wire(44, 174, 47, 174)
# diode snubbers (across each diode, annotated)
s.sym("C", "C23", ".022u", 35, 165, lx=2.4)
s.sym("C", "C24", ".022u", 35, 183, lx=2.4)
# reservoir: 50u + 80u to ground, B+1
s.junction(50, 174)
s.sym("C", "C17", "50u", 50, 177.81)
s.gnd(50, 181.62)
s.junction(53, 174)
s.sym("C", "C18", "80u", 55, 177.81, lx=2.2)
s.gnd(55, 181.62)
s.glabel("B+1", 47, 174, 180)
s.wire(47, 174, 60, 174)
# choke -> B+2 (screens)
s.sym("CHOKE", "L1", "choke", 67.6, 174, lx=-4.0, ly=-6.4)
s.wire(75.2, 174, 86, 174)
s.junction(80, 174)
s.glabel("B+2", 80, 171.46, 90)
s.wire(80, 171.46, 80, 174)
s.junction(83, 174)
s.sym("C", "C19", "50u", 83, 177.81)
s.gnd(83, 181.62)
# RD1 10k -> B+3 (PI)
l, r = s.series_h("R", "RD1", "10k", 90, 174)
s.wire(86, 174, l, 174)
s.wire(r, 174, 101, 174)
s.junction(96, 174)
s.glabel("B+3", 96, 171.46, 90)
s.wire(96, 171.46, 96, 174)
s.junction(99, 174)
s.sym("C", "C20", "50u", 99, 177.81)
s.gnd(99, 181.62)
# RD2 47k -> B+4 (2nd stage / CF)
l, r = s.series_h("R", "RD2", "47k", 105, 174)
s.wire(101, 174, l, 174)
s.wire(r, 174, 116, 174)
s.junction(111, 174)
s.glabel("B+4", 111, 171.46, 90)
s.wire(111, 171.46, 111, 174)
s.junction(114, 174)
s.sym("C", "C21", "50u", 114, 177.81)
s.gnd(114, 181.62)
# RD3 10k -> B+5 (input)
l, r = s.series_h("R", "RD3", "10k", 120, 174)
s.wire(116, 174, l, 174)
s.wire(r, 174, 129, 174)
s.junction(126, 174)
s.glabel("B+5", 126, 171.46, 90)
s.wire(126, 171.46, 126, 174)
s.sym("C", "C22", "50u", 129, 177.81)
s.gnd(129, 181.62)

# ======================= negative-bias supply ===============================
# HT tap -> D1 -> 220k(RBA) -> node; 15k(RBB)/25k trim(VR6)/47k(RBC) divider;
# 8u+8u filters -> -BIAS.
s.glabel("HT_B", 150, 160, 180)
s.wire(150, 160, 154, 160)
s.sym("DIODE_SS", "D1", "1N4007", 159, 160, lx=-2.0, ly=-5.4)
s.wire(164.08, 160, 168, 160)
l, r = s.series_h("R", "RBA", "220k", 172, 160)
s.wire(168, 160, l, 160)
s.wire(r, 160, 178, 160)
s.junction(178, 160)
# filter 8u
s.sym("C", "C15", "8u", 178, 163.81)
s.gnd(178, 167.62)
# 15k + 25k trim + 47k divider down to ground; wiper is the bias line
s.wire(178, 160, 184, 160)
s.sym("R", "RBB", "15k", 184, 163.81)
s.wire(184, 167.62, 184, 170)
s.sym("POT", "VR6", "25k adj", 184, 173.81)
s.wire(189.08, 173.81, 192, 173.81)       # wiper -> bias line
s.glabel("-BIAS", 192, 173.81, 0)
s.junction(192, 173.81)
s.sym("C", "C16", "8u", 195, 177, lx=2.2)
s.gnd(195, 180.81)
s.wire(184, 177.62, 184, 180)
s.sym("R", "RBC", "47k", 184, 183.81)
s.gnd(184, 187.62)

s.write(OUT, [
    ("Model 1987 — Plexi lead 50-style · Circuit Codex · CC-BY-SA 4.0 · redrawn "
     "from circuit facts", 24, 66, 2.0),
    ("EL34 evolution of the JTM45 — silicon rectifier, dual EL34 output. Heaters, "
     "PT primary and pilot lamp omitted — see netlist.cir and meta.yaml", 24, 70.5, 1.3),
])
print(f"wrote {OUT}")
