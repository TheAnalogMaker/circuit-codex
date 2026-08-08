#!/usr/bin/env python3
"""Generate amps/aa864-bassman/schematic.kicad_sch from the stage-template library.

Values per the published "BASSMAN-AMP AA864" drawing (see amps/aa864-bassman/meta.yaml).
Drawn on A3: the Bass Instrument channel across the top (three gain stages, the third
sitting to the right of its own 2:1 pad), the Normal channel below it (two stages),
the long-tailed-pair inverter and the 6L6GC output on the right, and the power and
bias supplies along the bottom.

Redrawn from circuit facts — never a trace of a factory drawing. Rails, as the sheet
prints them: B+PL = +422 (reservoir past the standby switch, and the output
transformer's centre tap), B+SCR = +420 (screen rail past the 125C1A choke),
B+PI = +410 (inverter plates), B+PRE = +380 (the preamp rail, as the layout sheet
letters it; the circuit sheet's +340 does not close — see voltages.yaml); -44 V is
the fixed-bias line. Heaters, the
pilot lamp and the PT's 6.3 V winding are omitted here (annotation layer) — see
netlist.cir, meta.yaml, and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = (Path(__file__).resolve().parent.parent / "amps" / "aa864-bassman"
       / "schematic.kicad_sch")
s = Sch()

# --- shared channel geometry (both channels are drawn on the same columns) ---
XV1 = 52       # input triode
XSLP = 85      # slope resistor centre
XLAD = 92      # ladder node
XCAP = 100     # ladder cap centre
XPOT = 110     # treble / bass pot column
XVOL = 126     # volume pot column
XWIP = 135     # volume-wiper lane
XV2 = 158      # second triode


def input_stage(y, j1, j2, r1, r2, rleak, vref, rload, rk, ck):
    """Two-jack input: 68k stoppers -> grid (1M leak) -> 7025 -> 100k plate load
    off the preamp rail + 1.5k/25u cathode RC. Returns the triode pin dict."""
    gb, d = 40, 5.5                          # grid-bus x, jack-row spacing
    s.glabel(j1, 12, y - d, 180)
    s.glabel(j2, 12, y + d, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - d)
    s.wire(16, y - d, l, y - d)
    s.wire(r, y - d, gb, y - d)
    l, r = s.series_h("R", r2, "68k", 22, y + d)
    s.wire(16, y + d, l, y + d)
    s.wire(r, y + d, gb, y + d)
    s.wire(gb, y - d, gb, y + d)
    s.junction(gb, y)
    s.sym("R", rleak, "1M", gb, y + 3.81 + d)
    s.gnd(gb, y + 7.62 + d)
    t = s.triode(vref, "7025", XV1, y)
    s.wire(gb, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], "B+PRE")
    s.wire(XV1, y + 7.62, XV1, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", XV1, y + 9)
    return t


def second_stage(y, vref, rload, rk, ck):
    """Volume wiper -> second 7025 half (100k / 1.5k / 25u), grid fed at XWIP."""
    t = s.triode(vref, "7025", XV2, y)
    s.wire(XWIP, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], "B+PRE")
    s.wire(XV2, y + 7.62, XV2, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", XV2, y + 9)
    return t


def volume(y, ref, val):
    """Volume pot below the treble wiper; wiper out along XWIP to the next grid."""
    s.wire(XPOT + 5.08, y - 2.19, XVOL, y - 2.19)
    s.sym("POT", ref, val, XVOL, y + 1.62)
    s.gnd(XVOL, y + 5.43)
    s.wire(XVOL + 5.08, y + 1.62, XWIP, y + 1.62)


# ============================ TITLE ==================================
s.note("Heaters, pilot lamp and the PT's 6.3 V winding omitted here — see netlist.cir, meta.yaml, layout.yaml. Rails: B+PL +422 (OT centre tap) · B+SCR +420 screens · B+PI +410 · B+PRE +380 preamp · bias −44 V")

# ============================ BASS INSTRUMENT CHANNEL (top row) =======
YB = 62
TB = YB - 11.1                       # plate-tee / tone-stack input line
s.text("Bass Instrument channel — three gain stages", 12, 32, 1.6)
input_stage(YB, "BASS 2", "BASS 1", "R1b", "R2b", "RGB1", "V1A", "RLB1", "RKB1", "CKB1")

# --- Bass tone stack. 250 pF off the plate into a 250k series resistor above a
#     50k treble pot; ONE 100k slope resistor down to the ladder node; and three
#     0.1 uF caps off that node — one across to the treble-lug/bass-top junction,
#     one into the grounded foot, and one the Deep switch parallels with it. The
#     10k bass pot is the rheostat and the foot goes straight to ground (there is
#     no 6.8 k leg here — that belongs to the Normal channel).
s.wire(XV1, TB, 78, TB)                      # stack input
s.junction(XV1, TB)
tl, tr = s.series_h("C", "CTB", "250p", 94, TB - 13.62)
s.wire(78, TB, 78, TB - 13.62)
s.wire(78, TB - 13.62, tl, TB - 13.62)
s.wire(tr, TB - 13.62, XPOT, TB - 13.62)
s.sym("R", "RTB", "250k", XPOT, TB - 9.81, lx=-9.6)
s.sym("POT", "VRTB", "50k treb", XPOT, TB - 2.19)
sl, sr = s.series_h("R", "RSB1", "100k", XSLP, TB + 6)
s.wire(78, TB, 78, TB + 6)
s.junction(78, TB)
s.wire(78, TB + 6, sl, TB + 6)
s.wire(sr, TB + 6, XLAD, TB + 6)             # ladder node
s.junction(XLAD, TB + 6)
bl, br = s.series_h("C", "CBB1", ".1u", XCAP, TB + 6)
s.wire(XLAD, TB + 6, bl, TB + 6)
s.wire(br, TB + 6, XPOT, TB + 6)
s.wire(XPOT, TB + 1.62, XPOT, TB + 6)        # treble bottom lug -> bass top
s.sym("POT", "VRBB", "10k bass", XPOT, TB + 9.81)
s.wire(XPOT + 5.08, TB + 9.81, 120, TB + 9.81)   # bass wired as a rheostat
s.wire(120, TB + 9.81, 120, TB + 6)
s.wire(120, TB + 6, XPOT, TB + 6)
s.junction(XPOT, TB + 6)
s.wire(XPOT, TB + 13.62, XPOT, TB + 17.43)   # ladder foot -> ground
s.gnd(XPOT, TB + 17.43)
s.sym("C", "CBB2", ".1u", XCAP, TB + 13.62, rot=90, lx=-3.2, ly=-3.6)
ml, mr = (XCAP - 3.81, XCAP + 3.81)
s.wire(XLAD, TB + 6, XLAD, TB + 13.62)
s.wire(XLAD, TB + 13.62, ml, TB + 13.62)
s.wire(mr, TB + 13.62, XPOT, TB + 13.62)
s.junction(XPOT, TB + 13.62)
s.junction(XLAD, TB + 13.62)
dl, dr = s.series_h("C", "CBB3", ".1u", XCAP, TB + 24)
s.wire(XLAD, TB + 13.62, XLAD, TB + 24)
s.wire(XLAD, TB + 24, dl, TB + 24)
s.wire(dr, TB + 24, XPOT, TB + 24)
s.sym("SWITCH", "SWDEEP", "Deep", XPOT, TB + 29.08, rot=90, lx=3.6, ly=-1.0)
s.gnd(XPOT, TB + 34.16)
volume(TB, "VRVB", "250k vol")
s.wire(XWIP, TB + 1.62, XWIP, YB)
second_stage(YB, "V1B", "RLB2", "RKB2", "CKB2")

# --- V1B plate -> 0.1 uF -> 220k/220k divider (0.001 uF across the foot) -> V3B
XDIV = 184
s.wire(XV2, TB, 168, TB)
s.junction(XV2, TB)
cl, cr = s.series_h("C", "CCB2", ".1u", 174, TB)
s.wire(168, TB, cl, TB)
s.wire(cr, TB, XDIV, TB)
s.sym("R", "RDV1", "220k", XDIV, TB + 3.81)
s.sym("R", "RDV2", "220k", XDIV, TB + 11.43, lx=-8.6)
s.gnd(XDIV, TB + 15.24)
s.sym("C", "CDV", ".001u", XDIV + 8, TB + 11.43, lx=3.4)
s.wire(XDIV, TB + 7.62, XDIV + 8, TB + 7.62)
s.wire(XDIV, TB + 15.24, XDIV + 8, TB + 15.24)
s.junction(XDIV, TB + 7.62)
s.junction(XDIV, TB + 15.24)

# ============================ BASS DRIVER (same row, right of the pad) =======
XD = 212
s.text("Bass-channel driver V3B — the one preamp cathode with no bypass can, and", 60, 98, 1.4)
s.text("0.005 µF straight across its plate load", 60, 103, 1.4)
s.wire(XDIV, TB + 7.62, 200, TB + 7.62)
s.junction(XDIV + 8, TB + 7.62)
s.wire(200, TB + 7.62, 200, YB)
t3b = s.triode("V3B", "7025", XD, YB)
s.wire(200, YB, t3b["g"][0], YB)
s.plate_load("RLB3", "100k", t3b["p"], "B+PRE")
s.sym("C", "CLB3", ".005u", XD + 8, TB - 3.81, lx=2.6)
s.wire(XD, TB, XD + 8, TB)
s.wire(XD, TB - 7.62, XD + 8, TB - 7.62)
s.junction(XD, TB)
s.junction(XD, TB - 7.62)
s.wire(XD, YB + 7.62, XD, YB + 9)
s.shunt_r("RKB3", "1.5k", XD, YB + 9)
s.wire(XD, TB, 228.19, TB)
s.junction(XD + 8, TB)
xl, xr = s.series_h("R", "RMXB", "220k", 232, TB)
s.wire(xr, TB, 244, TB)
s.glabel("PIMIX", 244, TB, 0)

# ============================ NORMAL CHANNEL (third row) ==============
YN = 180
TN = YN - 11.1
s.text("Normal channel — the blackface two-knob stack", 12, 143, 1.6)
input_stage(YN, "NORM 2", "NORM 1", "R1n", "R2n", "RGN1", "V2A", "RLN1", "RKN1", "CKN1")
s.wire(XV1, TN, 78, TN)
s.junction(XV1, TN)
tl, tr = s.series_h("C", "CTN", "250p", 94, TN - 6)
s.wire(78, TN, 78, TN - 6)
s.wire(78, TN - 6, tl, TN - 6)
s.wire(tr, TN - 6, XPOT, TN - 6)
s.sym("POT", "VRTN", "250k treb", XPOT, TN - 2.19)
sl, sr = s.series_h("R", "RSN", "100k", XSLP, TN + 6)
s.wire(78, TN, 78, TN + 6)
s.junction(78, TN)
s.wire(78, TN + 6, sl, TN + 6)
s.wire(sr, TN + 6, XLAD, TN + 6)
s.junction(XLAD, TN + 6)
bl, br = s.series_h("C", "CBN", ".1u", XCAP, TN + 6)
s.wire(XLAD, TN + 6, bl, TN + 6)
s.wire(br, TN + 6, XPOT, TN + 6)
s.wire(XPOT, TN + 1.62, XPOT, TN + 6)
s.sym("POT", "VRBN", "250k bass", XPOT, TN + 9.81)
s.wire(XPOT + 5.08, TN + 9.81, 120, TN + 9.81)
s.wire(120, TN + 9.81, 120, TN + 6)
s.wire(120, TN + 6, XPOT, TN + 6)
s.junction(XPOT, TN + 6)
s.sym("C", "CBN2", ".047u", XCAP, TN + 13.62, rot=90, lx=-3.2, ly=-3.6)
ml, mr = (XCAP - 3.81, XCAP + 3.81)
s.wire(XLAD, TN + 6, XLAD, TN + 13.62)
s.wire(XLAD, TN + 13.62, ml, TN + 13.62)
s.wire(mr, TN + 13.62, XPOT, TN + 13.62)
s.junction(XPOT, TN + 13.62)
s.sym("R", "RSLN", "6.8k", XPOT, TN + 17.43)
s.gnd(XPOT, TN + 21.24)
volume(TN, "VRVN", "1M vol")
# 120 pF Bright cap + switch across the volume pot, top lug to wiper
s.junction(XVOL, TN - 2.19)
s.wire(XVOL, TN - 2.19, XVOL, TN - 18)
cbl, cbr = s.series_h("C", "CBRN", "120p", 133, TN - 18)
s.wire(XVOL, TN - 18, cbl, TN - 18)
swl, swr = s.switch("SWBRT", "Bright", 146, TN - 18)
s.wire(cbr, TN - 18, swl, TN - 18)
s.wire(swr, TN - 18, 154, TN - 18)
s.wire(154, TN - 18, 154, TN + 1.62)
s.wire(154, TN + 1.62, XWIP, TN + 1.62)
s.junction(XWIP, TN + 1.62)
s.wire(XWIP, TN + 1.62, XWIP, YN)
second_stage(YN, "V2B", "RLN2", "RKN2", "CKN2")
s.wire(XV2, TN, 172, TN)
s.junction(XV2, TN)
nl, nr = s.series_h("R", "RMXN", "220k", 178, TN)
s.wire(172, TN, nl, TN)
s.wire(nr, TN, 244, TN)
s.glabel("PIMIX", 244, TN, 0)

# ============================ PHASE INVERTER (LTP) ====================
XPI, YPH, YPB, JY, XK = 266, 80, 120, 100, 252
TPA, TPB = YPH - 11.1, YPB - 11.1
s.triode("V4A", "12AT7", XPI, YPH)
s.triode("V4B", "12AT7", XPI, YPB)
s.plate_load("RLPA", "82k 5%", (XPI, YPH - 7.62), "B+PI")
s.plate_load("RLPB", "100k 5%", (XPI, YPB - 7.62), "B+PI")
# joined cathodes, taken down the left flank to the tail rail
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, XK, YPH + 10)
s.wire(XK, YPH + 10, XK, YPB + 10)
s.wire(XK, YPB + 10, XPI, YPB + 10)
s.wire(XPI, YPB + 10, XPI, YPB + 7.62)
s.junction(XK, JY)
tl, tr = s.series_h("R", "RTAIL", "470", 246, JY)
s.wire(XK, JY, tr, JY)
s.wire(tl, JY, 230, JY)                      # tail-junction rail
s.junction(236, JY)
s.junction(230, JY)
# hot grid: PIMIX -> 500 pF -> grid; 1M leak back to the tail junction
s.sym("R", "RGPA", "1M", 236, 92, lx=-9.4)
s.wire(236, 95.81, 236, JY)
s.wire(236, 88.19, 236, 74)
s.wire(236, 74, XPI - 7.62, 74)
s.wire(XPI - 7.62, 74, XPI - 7.62, YPH)
s.junction(XPI - 7.62, YPH)
s.glabel("PIMIX", 226, YPH, 180)
cl, cr = s.series_h("C", "CPI", "500p", 248, YPH)
s.wire(230, YPH, cl, YPH)
s.wire(cr, YPH, XPI - 7.62, YPH)
# cold grid: 1M leak to the tail junction, 0.1/200 from the feedback node
s.sym("R", "RGPB", "1M", 230, 108, lx=-9.4)
s.wire(230, 104.19, 230, JY)
s.wire(230, 111.81, 230, YPB)
s.junction(230, YPB)
pl, pr = s.series_h("C", "CPIB", ".1u 200V", 218, YPB)
s.wire(pr, YPB, XPI - 7.62, YPB)
s.junction(XPI - 7.62, YPB)
# feedback node: 22k tail -> 100 Ohm to ground, with the 820 Ohm from the speaker
rl, rr = s.series_h("R", "RT2", "22k", 212, JY)
s.wire(230, JY, rr, JY)
s.wire(rl, JY, 204, JY)
s.junction(204, JY)
s.wire(204, JY, 204, YPB)
s.wire(204, YPB, pl, YPB)
s.wire(204, JY, 198, JY)
s.junction(198, JY)
s.sym("R", "RNF", "100", 198, JY + 3.81, lx=-7.6)
s.gnd(198, JY + 7.62)
s.glabel("SPKR", 174, 90, 180)
fl, fr = s.series_h("R", "RNFB", "820", 188, 90)
s.wire(178, 90, fl, 90)
s.wire(fr, 90, 204, 90)
s.wire(204, 90, 204, JY)
s.text("12AT7 long-tailed pair — the 22 kΩ tail returns into the 100 Ω the global", 60, 112, 1.4)
s.text("feedback works across, not straight to ground", 60, 117, 1.4)

# ============================ OUTPUT couplers + 6L6GC =================
s.wire(XPI, TPA, 276, TPA)
s.junction(XPI, TPA)
al, ar = s.series_h("C", "C1", ".1u", 282, TPA)
s.wire(276, TPA, al, TPA)
s.wire(ar, TPA, 296, TPA)
s.wire(296, TPA, 296, 52)
s.wire(XPI, TPB, 276, TPB)
s.junction(XPI, TPB)
kl, kr = s.series_h("C", "C2", ".1u", 282, TPB)
s.wire(276, TPB, kl, TPB)
s.wire(kr, TPB, 296, TPB)
s.wire(296, TPB, 296, 152)

XO = 324
s.text("6L6GC (2) — fixed bias, 470 Ω · 1 W screen stoppers", 300, 32, 1.4)
for y, vref, glref, gsref, sref in [(52, "V5", "RGL1", "RGS1", "RS1"),
                                    (152, "V6", "RGL2", "RGS2", "RS2")]:
    s.junction(296, y)
    s.sym("R", glref, "220k 5%", 296, y + 3.81, lx=-11.0)
    s.wire(296, y + 7.62, 296, y + 10.16)
    s.glabel("-44V", 296, y + 10.16, 270)
    gl, gr = s.series_h("R", gsref, "1.5k", 306, y)
    s.wire(296, y, gl, y)
    pp = s.pentode(vref, "6L6GC", XO, y)
    s.wire(gr, y, pp["g1"][0], y)
    s.wire(pp["g2"][0], pp["g2"][1], 335.19, pp["g2"][1])
    sl2, sr2 = s.series_h("R", sref, "470 1W", 339, pp["g2"][1])
    s.wire(sr2, pp["g2"][1], 348, pp["g2"][1])
    s.glabel("B+SCR", 348, pp["g2"][1], 0)
    s.gnd(XO, pp["k"][1])

# output transformer TR3
s.sym("OT_PP", "T3", "125A13A", 372, 102)
s.wire(XO, 43.745, XO, 38)
s.wire(XO, 38, 356, 38)
s.wire(356, 38, 356, 96.92)
s.wire(356, 96.92, 363.11, 96.92)
s.wire(XO, 143.745, XO, 168)
s.wire(XO, 168, 352, 168)
s.wire(352, 168, 352, 107.08)
s.wire(352, 107.08, 363.11, 107.08)
s.wire(363.11, 102, 359, 102)
s.glabel("B+PL", 359, 102, 180)
s.wire(380.89, 99.46, 386, 99.46)
s.glabel("SPKR", 386, 99.46, 0)
s.wire(380.89, 104.54, 386, 104.54)
s.gnd(386, 104.54)
s.text("2×12 cabinet + EXT SPKR jack", 352, 180, 1.3)

# ============================ POWER SUPPLY (bottom) ===================
YPW = 235
s.text("Power supply — TR1 125P7D 305-0-305 (125P7DX export), three series silicon diodes per phase, "
       "125C1A choke; no rectifier tube", 26, 205, 1.4)
s.pt("T1", "125P7D", 50, YPW)
s.glabel("AC LINE", 10, YPW - 5.08, 180)
s.wire(14, YPW - 5.08, 15.92, YPW - 5.08)
fl2, fr2 = s.fuse("FUSE", "2A slo-blo", 21, YPW - 5.08)
s.wire(fr2, YPW - 5.08, 29.92, YPW - 5.08)
swl2, swr2 = s.switch("SWAC", "AC", 35, YPW - 5.08)
s.wire(swr2, YPW - 5.08, 41.11, YPW - 5.08)
s.glabel("AC LINE", 10, YPW + 5.08, 180)
s.wire(14, YPW + 5.08, 41.11, YPW + 5.08)
s.wire(58.89, YPW, 63, YPW)
s.gnd(63, YPW)                                # HT centre tap
# two three-diode strings
s.wire(58.89, YPW - 5.08, 63, YPW - 5.08)
s.wire(63, YPW - 5.08, 63, 218)
s.wire(63, 218, 69.92, 218)
s.junction(63, 218)
s.wire(63, 218, 63, 212)
s.glabel("HT-A", 63, 212, 90)
for i, ref in enumerate(["D1", "D2", "D3"]):
    x = 75 + 14 * i
    s.sym("DIODE_SS", ref, "Si", x, 218, lx=-2.0, ly=-5.4)
    if i:
        s.wire(x - 8.92, 218, x - 5.08, 218)
s.wire(108.08, 218, 118, 218)
s.wire(118, 218, 118, YPW)
s.wire(58.89, YPW + 5.08, 63, YPW + 5.08)
s.wire(63, YPW + 5.08, 63, 252)
s.wire(63, 252, 69.92, 252)
for i, ref in enumerate(["D4", "D5", "D6"]):
    x = 75 + 14 * i
    s.sym("DIODE_SS", ref, "Si", x, 252, lx=-2.0, ly=-5.4)
    if i:
        s.wire(x - 8.92, 252, x - 5.08, 252)
s.wire(108.08, 252, 118, 252)
s.wire(118, 252, 118, YPW)
s.junction(118, YPW)
# reservoir: two 70/350 cans in series, balanced by a pair of 220k 1W
s.wire(118, YPW, 128, YPW)
s.sym("C", "C10", "70u 350V", 128, YPW + 3.81, lx=-12.4)
s.sym("C", "C11", "70u 350V", 128, YPW + 11.43, lx=-12.4)
s.gnd(128, YPW + 15.24)
s.sym("R", "RBL1", "220k 1W", 138, YPW + 3.81)
s.sym("R", "RBL2", "220k 1W", 138, YPW + 11.43)
s.wire(128, YPW, 138, YPW)
s.wire(128, YPW + 7.62, 138, YPW + 7.62)
s.wire(128, YPW + 15.24, 138, YPW + 15.24)
s.junction(128, YPW)
s.junction(128, YPW + 7.62)
s.junction(128, YPW + 15.24)
# standby -> plate rail -> choke -> screen rail -> 1k -> PI rail -> 4.7k -> preamp
s.wire(138, YPW, 152.92, YPW)
s.junction(138, YPW)
sbl, sbr = s.switch("SWSTBY", "Standby", 158, YPW)
s.wire(sbr, YPW, 172, YPW)
s.wire(172, YPW, 172, YPW - 7)
s.glabel("B+PL", 172, YPW - 7, 90)
s.junction(172, YPW)
s.sym("CHOKE", "T2", "125C1A", 182, YPW, lx=-4.6, ly=-6.8)
s.wire(172, YPW, 174.38, YPW)
s.wire(189.62, YPW, 204, YPW)
s.junction(198, YPW)
s.wire(198, YPW, 198, YPW - 7)
s.glabel("B+SCR", 198, YPW - 7, 90)
s.sym("C", "C12", "20u 525V", 204, YPW + 3.81)
s.gnd(204, YPW + 7.62)
s.junction(204, YPW)
dl2, dr2 = s.series_h("R", "RD1", "1k 1W", 214, YPW)
s.wire(204, YPW, dl2, YPW)
s.wire(dr2, YPW, 230, YPW)
s.junction(224, YPW)
s.wire(224, YPW, 224, YPW - 7)
s.glabel("B+PI", 224, YPW - 7, 90)
s.sym("C", "C13", "20u 525V", 230, YPW + 3.81)
s.gnd(230, YPW + 7.62)
s.junction(230, YPW)
dl3, dr3 = s.series_h("R", "RD2", "4.7k 1W", 240, YPW)
s.wire(230, YPW, dl3, YPW)
s.wire(dr3, YPW, 256, YPW)
s.junction(250, YPW)
s.wire(250, YPW, 250, YPW - 7)
s.glabel("B+PRE", 250, YPW - 7, 90)
s.sym("C", "C14", "20u 525V", 256, YPW + 3.81)
s.gnd(256, YPW + 7.62)

# ============================ BIAS SUPPLY ============================
s.text("Bias supply — off the 305 V HT lead: 470 Ω · 1 W, one diode, a 25 µF can,",
       282, 224, 1.3)
s.text("then a 10 kΩ-L adjust over a 15 kΩ leg, out at −44 V", 282, 229, 1.3)
YBS = 250
s.glabel("HT-A", 282, YBS, 180)
s.wire(286, YBS, 291.19, YBS)
brl, brr = s.series_h("R", "RBIAS", "470 1W", 295, YBS)
s.wire(brr, YBS, 302.92, YBS)
s.sym("DIODE_SS", "DBIAS", "Si", 308, YBS, rot=180, lx=-2.0, ly=-5.4, label_rot=0)
s.wire(313.08, YBS, 320, YBS)
s.sym("C", "CB1", "25u 50V", 320, YBS + 3.81, lx=-12.4)
s.gnd(320, YBS + 7.62)
s.junction(320, YBS)
s.wire(320, YBS, 336.19, YBS)
s.sym("POT", "VRBIAS", "10k-L bias", 340, YBS, rot=90, lx=-5.0, ly=4.4, label_rot=0)
s.wire(343.81, YBS, 352, YBS)
s.sym("R", "RBIAS2", "15k", 352, YBS + 3.81)
s.gnd(352, YBS + 7.62)
s.wire(340, YBS - 5.08, 340, YBS - 12)
s.glabel("-44V", 340, YBS - 12, 90)

# ============================ GROUND SWITCH (period) =================
s.text("Period ground switch + cap (not in modern builds)", 10, 262, 1.1)
s.glabel("AC LINE", 10, 272, 180)
s.wire(14, 272, 15.92, 272)
gsl, gsr = s.switch("SWGND", "Ground", 21, 272)
s.wire(gsr, 272, 30.19, 272)
cdl, cdr = s.series_h("C", "CDEATH", ".047u 600V", 34, 272)
s.wire(30.19, 272, cdl, 272)
s.wire(cdr, 272, 42, 272)
s.gnd(42, 272)

s.write(OUT)
print(f"wrote {OUT}")
