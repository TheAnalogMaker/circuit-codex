#!/usr/bin/env python3
"""Generate amps/ab165/schematic.kicad_sch from the stage-template library.

Values per the published "Fender Model 'Bassman-Amp AB165'" drawing (D-FE) — see
amps/ab165/meta.yaml. Two preamp channel rows (Bass Instrument on top, Normal
below), the mixer/driver stage between them, the long-tailed-pair phase inverter
and the 6L6GC output on the right, and the power / bias supply along the bottom.
Drawn on A3 so every block stays clear of its neighbours.

Redrawn from circuit facts — never a trace of a factory drawing.

Rails as the sheet prints them: B+1 = +425 V (6L6 plates through the output
transformer primary, screens through their 470 Ω stoppers, and the local-feedback
220 kΩ pair), B+2 = +415 V (phase-inverter plate loads), B+3 = +390 V
(second-stage and mixer/driver plate loads), B+4 = +320 V (both channel input
stages and — as the sheet draws it — the bass channel's second stage). The bias
line is drawn as two trimmed legs, "-45V A" and "-45V B", because the hum-balance
control gives each output tube its own 10 kΩ leg; netlist.cir collapses both onto
one ideal −45 V source and says so.

Heaters, the pilot lamp and the PT primary/mains chain beyond the drawn switch,
fuse and ground-switch cap are an annotation layer — see netlist.cir, meta.yaml
and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ab165" / "schematic.kicad_sch"
s = Sch()


def input_stage(y, j1, j2, r1, r2, rleak, vref, rload, rk, ck, rail,
                shunt_ref=None, shunt_val=None):
    """Two-jack channel input: 68 kΩ stoppers → grid (1 MΩ leak) → 12AX7 with a
    100 kΩ plate load to `rail` and a 1.5 kΩ ‖ 25 µF cathode. `shunt_ref` adds
    the bass channel's capacitor straight across the plate load. Returns the
    triode pin dict."""
    gb = 40  # grid-bus x
    # Each jack lead starts ON its label's anchor: a global label connects at
    # that point only, so a wire begun a few mm away leaves the jack floating.
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(12, y - 4, l, y - 4)
    s.wire(r, y - 4, gb, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(12, y + 4, l, y + 4)
    s.wire(r, y + 4, gb, y + 4)
    s.wire(gb, y - 4, gb, y + 4)
    s.junction(gb, y)
    s.sym("R", rleak, "1M", gb, y + 3.81 + 4)
    s.gnd(gb, y + 7.62 + 4)
    t = s.triode(vref, "12AX7 (7025)", 52, y)
    s.wire(gb, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], rail)
    if shunt_ref:
        # the sheet's treble cut: a capacitor straight across the 100 kΩ load
        px, py = t["p"]
        top, bot = py - 3.48 - 7.62, py - 3.48
        s.sym("C", shunt_ref, shunt_val, px + 8, (top + bot) / 2)
        s.wire(px, top, px + 8, top)
        s.wire(px, bot, px + 8, bot)
        s.junction(px, bot)
    s.wire(52, y + 7.62, 52, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", 52, y + 9)
    return t


def tone_stack(tee, ct_ref, ct_val, rs_ref, cb_ref, cb_val, cb2_ref, cb2_val,
               rsl_ref, rsl_val, vrt_ref, vrb_ref, vrv_ref):
    """The blackface two-knob ladder, wired as the AB165 sheet draws it (the
    same network the AB763 and AA964 sheets print):

      IN  plate tee            slope resistor · treble cap
      N2  slope foot           slope resistor · bass cap · middle-leg cap
      N3  treble-cap output    treble cap · treble-pot end lug
      OUT treble-pot WIPER, alone → volume top
      N4  bass-cap output      bass cap · treble-pot other end lug ·
                               bass rheostat (wiper strapped to its hot lug)
      N5  bass-rheostat foot   the fixed bleed leg to ground

    Returns (N2 x, N2 y) so a channel can hang its own extra leg off the slope
    foot, and the volume pot's wiper coordinates."""
    s.wire(52, tee, 78, tee)                       # node A (stack input)
    s.junction(52, tee)
    # treble: A -> treble cap -> treble pot; the wiper alone is the output
    tl, tr = s.series_h("C", ct_ref, ct_val, 84, tee - 6)
    s.wire(78, tee, 78, tee - 6)
    s.wire(78, tee - 6, tl, tee - 6)
    s.wire(tr, tee - 6, 96, tee - 6)
    s.sym("POT", vrt_ref, "250k treb", 96, tee - 6 + 3.81)
    # slope: A -> 100k -> node N2
    sl, sr = s.series_h("R", rs_ref, "100k", 83, tee + 6)
    s.wire(78, tee, 78, tee + 6)
    s.junction(78, tee)
    s.wire(78, tee + 6, sl, tee + 6)
    s.wire(sr, tee + 6, 87, tee + 6)
    s.junction(87, tee + 6)                        # node N2 (slope foot)
    # N2 -> bass cap -> N4 (treble-pot cold lug / bass-rheostat hot lug)
    bl, br = s.series_h("C", cb_ref, cb_val, 92, tee + 6)
    s.wire(87, tee + 6, bl, tee + 6)
    s.wire(br, tee + 6, 96, tee + 6)
    s.wire(96, tee + 1.62, 96, tee + 6)
    s.sym("POT", vrb_ref, "250k bass", 96, tee + 6 + 3.81)
    s.wire(101.08, tee + 9.81, 108, tee + 9.81)    # rheostat strap
    s.wire(108, tee + 9.81, 108, tee + 6)
    s.wire(108, tee + 6, 96, tee + 6)
    s.junction(96, tee + 6)
    # N2 -> middle-leg cap -> N5 -> fixed bleed leg -> ground
    s.wire(87, tee + 6, 87, tee + 13.62)
    ml, mr = s.series_h("C", cb2_ref, cb2_val, 92, tee + 13.62)
    s.wire(87, tee + 13.62, ml, tee + 13.62)
    s.wire(mr, tee + 13.62, 96, tee + 13.62)
    s.junction(96, tee + 13.62)
    s.sym("R", rsl_ref, rsl_val, 96, tee + 17.43)
    s.gnd(96, tee + 21.24)
    # treble wiper -> volume top
    s.wire(101.08, tee - 2.19, 114, tee - 2.19)
    s.wire(114, tee - 2.19, 114, tee)
    s.sym("POT", vrv_ref, "1M vol", 114, tee + 3.81)
    s.gnd(114, tee + 7.62)
    return (87, tee + 13.62), (119.08, tee + 3.81)


def second_stage(y, vref, rload, rk, ck, rail, wiper, mix_ref):
    """Channel second stage: volume wiper → 12AX7 grid, 100 kΩ plate load to
    `rail`, 1.5 kΩ ‖ 25 µF cathode, plate out through the 220 kΩ mixing
    resistor to the shared MIX node."""
    wx, wy = wiper
    s.wire(wx, wy, 124, wy)
    s.junction(wx, wy)
    s.wire(124, wy, 124, y)
    t = s.triode(vref, "12AX7 (7025)", 136, y)
    s.wire(124, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], rail)
    s.wire(136, y + 7.62, 136, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", 136, y + 9)
    tee = y - 7.62 - 3.48
    s.wire(136, tee, 146, tee)
    s.junction(136, tee)
    l, r = s.series_h("R", mix_ref, "220k", 152, tee)
    s.wire(146, tee, l, tee)
    s.wire(r, tee, 166, tee)
    s.glabel("MIX", 166, tee, 0)
    return t


# ============================ TITLE ==================================
s.note('Heaters, pilot lamp and the PT primary beyond the drawn switch/fuse are omitted here — see netlist.cir, meta.yaml, layout.yaml. Rails: B+1 +425 · B+2 +415 · B+3 +390 · B+4 +320 · bias -45 V')

# ============================ BASS INSTRUMENT CHANNEL (top row) =======
YB = 62
s.text("Bass Instrument channel", 12, 44, 1.6)
t1a = input_stage(YB, "BASS 1", "BASS 2", "R1b", "R2b", "RGB1", "V1A",
                  "RLB1", "RKB1", "CKB1", "B+4",
                  shunt_ref="CLB1", shunt_val=".01u")
teeB = YB - 7.62 - 3.48
n2b, wipB = tone_stack(teeB, "CTB", "390p", "RSB", "CBB", ".1u", "CBB2", ".1u",
                       "RSLB", "8.2k", "VRTB", "VRBB", "VRVB")
# DEEP: a further 0.1 µF from the slope foot to ground through its own switch
s.wire(n2b[0], n2b[1], n2b[0], n2b[1] + 3)
s.wire(n2b[0], n2b[1] + 3, 70, n2b[1] + 3)
s.sym("C", "CDEEP", ".1u", 70, n2b[1] + 6.81)
s.wire(70, n2b[1] + 10.62, 70, n2b[1] + 13)
l, r = s.switch("SWDEEP", "DEEP", 76, n2b[1] + 13)
s.wire(70, n2b[1] + 13, l, n2b[1] + 13)
s.wire(r, n2b[1] + 13, 86, n2b[1] + 13)
s.gnd(86, n2b[1] + 13)
t1b = second_stage(YB, "V1B", "RLB2", "RKB2", "CKB2", "B+4", wipB, "RMXB")

# ============================ NORMAL CHANNEL (second row) ============
YN = 116
s.text("Normal channel", 12, 98, 1.6)
t2a = input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RGN1", "V2A",
                  "RLN1", "RKN1", "CKN1", "B+4")
teeN = YN - 7.62 - 3.48
n2n, wipN = tone_stack(teeN, "CTN", "250p", "RSN", "CBN", ".1u", "CBN2", ".047u",
                       "RSLN", "6.8k", "VRTN", "VRBN", "VRVN")
# BRIGHT: 120 pF from the volume pot's top lug to its wiper, through a switch
s.junction(114, teeN - 2.19)
s.wire(114, teeN - 2.19, 114, teeN - 17)
cl, cr = s.series_h("C", "CBRN", "120p", 121, teeN - 17)
s.wire(114, teeN - 17, cl, teeN - 17)
l, r = s.switch("SWBRT", "BRIGHT", 133, teeN - 17)
s.wire(cr, teeN - 17, l, teeN - 17)
s.wire(r, teeN - 17, 142, teeN - 17)
s.wire(142, teeN - 17, 142, teeN + 3.81)
s.wire(142, teeN + 3.81, 124, teeN + 3.81)
t2b = second_stage(YN, "V2B", "RLN2", "RKN2", "CKN2", "B+3", wipN, "RMXN")

# ============================ MIXER / DRIVER (V3B) ===================
YM = 89
s.text("Channel mixer / driver", 172, 71, 1.6)
s.glabel("MIX", 172, YM, 180)
s.wire(172, YM, 180, YM)
s.junction(180, YM)
cl, cr = s.series_h("C", "CMIX", ".01u", 186, YM)
s.wire(180, YM, cl, YM)
s.wire(cr, YM, 194, YM)
s.junction(194, YM)
s.sym("R", "RGM", "470k", 194, YM + 3.81)
s.gnd(194, YM + 7.62)
t3 = s.triode("V3B", "12AX7 (7025)", 202, YM)
s.wire(194, YM, t3["g"][0], YM)
s.plate_load("RLM", "100k", t3["p"], "B+3")
s.wire(202, YM + 7.62, 202, YM + 9)
s.shunt_rc("RKM", "1.5k", "CKM", "25u", 202, YM + 9)
teeM = YM - 7.62 - 3.48
# the AB165 blend resistor: the driver's own plate returned to the mixing node
s.junction(202, teeM)
s.wire(202, teeM, 196, teeM)          # step clear of the RLM column before rising:
s.wire(196, teeM, 196, teeM - 10)     # up it, this lead would lie on RLM's own pins
fl, fr = s.series_h("R", "RFBM", "470k", 191, teeM - 10)
s.wire(196, teeM - 10, fr, teeM - 10)
s.wire(fl, teeM - 10, 180, teeM - 10)
s.wire(180, teeM - 10, 180, YM)
# driver plate -> 0.1 µF -> phase-inverter hot grid
s.wire(202, teeM, 212, teeM)
cl, cr = s.series_h("C", "CPIA", ".1u", 218, teeM)
s.wire(212, teeM, cl, teeM)
s.wire(cr, teeM, 228, teeM)
s.junction(228, teeM)
s.wire(228, teeM, 228, 62)
s.glabel("PIG", 228, 62, 0)

# ============================ NEGATIVE FEEDBACK ======================
s.caption('Negative feedback — speaker line → inverter hot grid (DC-blocked)', 150, 32, 1.3)
s.glabel("SPKR", 150, 38, 180)
nl, nr = s.series_h("R", "RNFB", "47k", 162, 38)
s.wire(150, 38, nl, 38)
fl2, fr2 = s.series_h("C", "CNFB", ".1u", 178, 38)
s.wire(nr, 38, fl2, 38)
s.wire(fr2, 38, 228, 38)
s.wire(228, 38, 228, teeM)

# ============================ PHASE INVERTER (12AT7 LTP) =============
XPI = 258
YPH = 62    # hot half
YPB = 100   # cold half
JY = 81     # tail junction
s.text("Long-tailed-pair phase inverter", 236, 50, 1.6)
s.glabel("PIG", 222, YPH, 180)
s.wire(222, YPH, 230, YPH)
s.junction(230, YPH)
s.wire(230, YPH, 250.38, YPH)
t4a = s.triode("V4A", "12AT7", XPI, YPH)
t4b = s.triode("V4B", "12AT7", XPI, YPB)
s.plate_load("RLPA", "100k 5%", t4a["p"], "B+2")
s.plate_load("RLPB", "100k 5%", t4b["p"], "B+2")
# grid leaks: both returned to the tail junction, drawn as one column
s.sym("R", "RGPA", "1M", 230, (YPH + JY) / 2, lx=-9.4)
s.wire(230, (YPH + JY) / 2 - 3.81, 230, YPH)
s.wire(230, (YPH + JY) / 2 + 3.81, 230, JY)
s.sym("R", "RGPB", "1M", 230, (JY + YPB) / 2, lx=-9.4)
s.wire(230, (JY + YPB) / 2 - 3.81, 230, JY)
s.wire(230, (JY + YPB) / 2 + 3.81, 230, YPB)
s.junction(230, JY)
s.wire(230, YPB, 250.38, YPB)
# cold grid held at AC ground by the 0.1 µF / 200 V capacitor
s.junction(240, YPB)
s.wire(240, YPB, 240, YPB + 6)
s.sym("C", "CPIB", ".1u", 240, YPB + 9.81)
s.gnd(240, YPB + 13.62)
# joined cathodes -> 470 Ω -> tail junction -> 22 kΩ -> ground.
# Both halves are drawn the same way up, so BOTH cathodes are the pin BELOW the
# envelope (y + 7.62) — as amps/5f6a draws its long-tailed pair. Taking the cold
# half's y - 7.62 instead lands on its PLATE, which ties the cold plate to the
# cathode bus and leaves the cold cathode dangling. The bus runs down the
# grid-side channel between the grid pins and the envelopes (XPI - 6.35, the
# same 1.27 mm clearance 5F6-A uses on its own side), so it crosses no lead.
KBUS = XPI - 6.35
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, KBUS, YPH + 10)
s.wire(XPI, YPB + 7.62, XPI, YPB + 10)
s.wire(XPI, YPB + 10, KBUS, YPB + 10)
s.wire(KBUS, YPH + 10, KBUS, YPB + 10)
s.junction(KBUS, JY)
tl, tr = s.series_h("R", "RTAIL", "470", 242.5, JY)
s.wire(KBUS, JY, tr, JY)
s.wire(tl, JY, 234, JY)
s.wire(234, JY, 230, JY)
s.sym("R", "RT2", "22k", 234, JY + 3.81)
s.junction(234, JY)
s.gnd(234, JY + 7.62)

# ============================ OUTPUT STAGE (6L6GC pair) ==============
XO = 320
s.text("6L6GC output pair — fixed bias, local feedback from each plate", 288, 30, 1.6)
teeA = YPH - 7.62 - 3.48
teeC = YPB - 7.62 - 3.48
# PI plates -> 0.022 µF couplers -> output grids
s.junction(XPI, teeA)
s.wire(XPI, teeA, XPI + 10, teeA)
al, ar = s.series_h("C", "C1", ".022u", XPI + 16, teeA)
s.wire(XPI + 10, teeA, al, teeA)
s.wire(ar, teeA, 286, teeA)
s.wire(286, teeA, 286, 58)
s.junction(XPI, teeC)
s.wire(XPI, teeC, XPI + 10, teeC)
kl, kr = s.series_h("C", "C2", ".022u", XPI + 16, teeC)
s.wire(XPI + 10, teeC, kl, teeC)
s.wire(kr, teeC, 286, teeC)
s.wire(286, teeC, 286, 118)
for gy, vref, glref, gsref, sref, bias in [(58, "V5", "RGL1", "RGS1", "RS1", "-45V A"),
                                           (118, "V6", "RGL2", "RGS2", "RS2", "-45V B")]:
    s.junction(286, gy)
    s.sym("R", glref, "220k 5%", 286, gy + 3.81)
    s.wire(286, gy + 7.62, 286, gy + 10.16)
    s.glabel(bias, 286, gy + 10.16, 270)
    l, r = s.series_h("R", gsref, "1.5k", 299, gy)
    s.wire(286, gy, l, gy)
    p = s.pentode(vref, "6L6GC", XO, gy)
    s.wire(r, gy, p["g1"][0], gy)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2, p["g2"][1])
    sl2, sr2 = s.series_h("R", sref, "470 1W", p["g2"][0] + 5.81, p["g2"][1])
    s.wire(sr2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
    s.glabel("B+1", p["g2"][0] + 11.5, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# local feedback: 220 kΩ from each output plate back to the inverter plate
s.wire(XO, 49.745, XO, 40)
s.junction(XO, 40)
bl2, br2 = s.series_h("R", "RBSA", "220k", 288, 40)
s.wire(XO, 40, br2, 40)
s.wire(bl2, 40, XPI + 6, 40)          # down beside the RLPA column, not through
s.wire(XPI + 6, 40, XPI + 6, teeA)    # it — x=XPI would cross the B+2 rail stub
s.junction(XPI + 6, teeA)
s.wire(XO, 109.745, XO, 105)
s.junction(XO, 105)
bl3, br3 = s.series_h("R", "RBSB", "220k", 300, 105)
s.wire(XO, 105, br3, 105)
s.wire(bl3, 105, 268, 105)
s.wire(268, 105, 268, teeC)
s.junction(268, teeC)

# output transformer TR3
s.sym("OT_PP", "TR3", "125A13A", 352, 88)
s.wire(XO, 40, 343.11, 40)
s.wire(343.11, 40, 343.11, 82.92)      # V5 plate -> primary A
s.wire(XO, 105, 343.11, 105)
s.wire(343.11, 105, 343.11, 93.08)     # V6 plate -> primary B
s.wire(343.11, 88, 340.57, 88)
s.wire(340.57, 88, 340.57, 84)
s.glabel("B+1", 340.57, 84, 90)        # primary centre tap
s.wire(360.89, 85.46, 366, 85.46)
s.glabel("SPKR", 366, 85.46, 0)
s.wire(360.89, 90.54, 366, 90.54)
s.glabel("GND", 366, 90.54, 0)

# ============================ POWER SUPPLY (bottom) ==================
YPW = 215
s.text("Power supply — TR1 125P7D 320-0-320 (125P7DX export), three series silicon diodes per leg, TR2 125C1A choke behind the standby switch",
       26, 200, 1.4)
pt = s.pt("TR1", "125P7D", 52, YPW)
s.glabel("MAINS", 4, YPW - 5.08, 180)
fl3, fr3 = s.fuse("F1", "2A slo-blo", 18, YPW - 5.08)
s.wire(4, YPW - 5.08, fl3, YPW - 5.08)
sl3, sr3 = s.switch("SWAC", "AC", 33, YPW - 5.08)
s.wire(fr3, YPW - 5.08, sl3, YPW - 5.08)
s.wire(sr3, YPW - 5.08, pt["pri1"][0], YPW - 5.08)
s.glabel("MAINS", 4, YPW + 5.08, 180)
s.wire(4, YPW + 5.08, pt["pri2"][0], YPW + 5.08)
# period ground switch + capacitor off the mains
s.junction(20, YPW + 5.08)
s.wire(20, YPW + 5.08, 20, YPW + 13)
cd1, cd2 = s.series_h("C", "CDEATH", ".047u", 26, YPW + 13)
s.wire(20, YPW + 13, cd1, YPW + 13)
gl3, gr3 = s.switch("SWGND", "GND", 37, YPW + 13)
s.wire(cd2, YPW + 13, gl3, YPW + 13)
s.wire(gr3, YPW + 13, 46, YPW + 13)
s.gnd(46, YPW + 13)
s.text("Period ground-switch capacitor (not in modern builds)", 14, YPW + 21, 1.1)
# HT winding -> the two rectifier legs
s.wire(pt["ht_a"][0], pt["ht_a"][1], 66.92, pt["ht_a"][1])
s.sym("DIODE_SS", "D1", "Si x3", 72, pt["ht_a"][1], lx=-3.0, ly=-5.4)
s.wire(77.08, pt["ht_a"][1], 90, pt["ht_a"][1])
s.wire(pt["ht_b"][0], pt["ht_b"][1], 66.92, pt["ht_b"][1])
s.sym("DIODE_SS", "D2", "Si x3", 72, pt["ht_b"][1], lx=-3.0, ly=5.6)
s.wire(77.08, pt["ht_b"][1], 90, pt["ht_b"][1])
s.wire(90, pt["ht_a"][1], 90, pt["ht_b"][1])
s.junction(90, YPW)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], 63, YPW)
s.gnd(63, YPW)
s.wire(90, YPW, 96, YPW)
# reservoir: two 70 µF cans in series with their 220 kΩ balancing resistors
s.wire(96, YPW, 116, YPW)
s.junction(100, YPW)
s.sym("C", "C10", "70u", 100, YPW + 3.81)
s.junction(100, YPW + 7.62)
s.sym("C", "C11", "70u", 100, YPW + 11.43)
s.gnd(100, YPW + 15.24)
s.sym("R", "RBAL1", "220k 1W", 110, YPW + 3.81, lx=-11.0)
s.sym("R", "RBAL2", "220k 1W", 110, YPW + 11.43, lx=-11.0)
s.wire(100, YPW + 7.62, 110, YPW + 7.62)
s.wire(100, YPW + 15.24, 110, YPW + 15.24)
s.junction(110, YPW)
s.junction(110, YPW + 7.62)
s.junction(100, YPW + 15.24)
# standby switch, then the choke, then the +425 screen node
st1, st2 = s.switch("SWSTBY", "STANDBY", 122, YPW)
s.wire(116, YPW, st1, YPW)
s.sym("CHOKE", "TR2", "125C1A", 142, YPW, lx=-5.0, ly=-6.4)
s.wire(st2, YPW, 134.38, YPW)
s.wire(149.62, YPW, 160, YPW)
for x, cx, cref, rail, cval in [(154, 160, "C12", "B+1", "20u"),
                                (174, 180, "C13", "B+2", "20u"),
                                (194, 200, "C14", "B+3", "20u"),
                                (214, 220, "C15", "B+4", "8u")]:
    s.junction(x, YPW)
    s.wire(x, YPW - 4, x, YPW)
    s.glabel(rail, x, YPW - 4, 90)
    s.wire(x, YPW, cx, YPW)     # rail node -> its own filter can; without this
    s.junction(cx, YPW)         # span the chain breaks at every dropper output
    s.sym("C", cref, cval, cx, YPW + 3.81)
    s.gnd(cx, YPW + 7.62)
for x, ref, val in [(167, "RD1", "1k 1W"), (187, "RD2", "4.7k 1W"),
                    (207, "RD3", "27k 1W")]:
    l, r = s.series_h("R", ref, val, x, YPW)
    s.wire(x - 7, YPW, l, YPW)
    s.wire(r, YPW, x + 7, YPW)
s.wire(220, YPW, 226, YPW)

# ============================ BIAS SUPPLY ============================
YBI = 258
s.note('Bias supply — one HT leg through 470 Ω · 1 W and a silicon diode; the 10 kΩ-L balance control gives each output tube its own 10 kΩ leg')
s.junction(65, pt["ht_b"][1])
s.wire(65, pt["ht_b"][1], 65, YBI)
bl4, br4 = s.series_h("R", "RBIAS", "470 1W", 75, YBI)
s.wire(65, YBI, bl4, YBI)
# cathode faces the winding: the filter charges negative
s.sym("DIODE_SS", "DBIAS", "Si", 90, YBI, rot=0, lx=-3.0, ly=-5.4, mirror="y")
s.wire(br4, YBI, 84.92, YBI)
s.wire(95.08, YBI, 110, YBI)
s.junction(100, YBI)
s.sym("C", "CB1", "elec", 100, YBI + 3.81)
s.gnd(100, YBI + 7.62)
s.junction(106, YBI)
s.sym("C", "CB2", "elec", 106, YBI + 3.81)
s.gnd(106, YBI + 7.62)
# Balance control. The sheet draws the 10 kΩ-L as a two-terminal element in the
# divider — its two ends feed the two 10 kΩ legs, one leg per output tube, and
# the 15 kΩ foot grounds the ladder. Drawn here with the wiper strapped to its
# own end lug, the same reading the corpus gives a pot a drawing shows with two
# terminals; netlist.cir replaces the whole supply with an ideal −45 V source.
s.wire(110, YBI, 128, YBI)
s.sym("POT", "VRBAL", "10k-L bal", 128, YBI + 3.81, lx=-6.6)
s.junction(128, YBI)
s.wire(133.08, YBI + 3.81, 137, YBI + 3.81)
s.wire(137, YBI + 3.81, 137, YBI)
s.wire(137, YBI, 128, YBI)
s.sym("R", "RBB1", "10k", 120, YBI - 3.81, lx=-8.4)
s.wire(120, YBI, 128, YBI)
s.wire(120, YBI - 7.62, 120, YBI - 10)
s.glabel("-45V A", 120, YBI - 10, 90)
s.junction(128, YBI + 7.62)
s.sym("R", "RBB3", "15k", 128, YBI + 11.43)
s.gnd(128, YBI + 15.24)
s.wire(128, YBI + 7.62, 140, YBI + 7.62)
s.wire(140, YBI + 7.62, 140, YBI + 2)
s.sym("R", "RBB2", "10k", 140, YBI - 1.81, lx=4.4)
s.wire(140, YBI - 5.62, 140, YBI - 10)
s.glabel("-45V B", 140, YBI - 10, 90)

s.write(OUT)
print(f"wrote {OUT}")
