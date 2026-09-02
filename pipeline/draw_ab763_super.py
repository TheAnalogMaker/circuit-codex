#!/usr/bin/env python3
"""Generate amps/ab763-super/schematic.kicad_sch from the stage-template library.

Values per the published "SUPER-REVERB-AMP AB763" drawing (C-FD), cited in
amps/ab763-super/meta.yaml. Two preamp channel rows at the top (Normal — the
plain two-knob stack; Vibrato — the genuine three-knob FMV stack, its Middle a
real pot in place of the Normal channel's fixed bleed resistor), the reverb
driver/recovery/mixer block below them, the tremolo oscillator (single triode,
excluded from netlist.cir — no static DC point) under that, the long-tailed-
pair phase inverter and the 6L6GC pair on the right, and the rectifier/filter
and bias supplies along the bottom.

Redrawn from circuit facts — never a trace of a factory drawing. Rails, in the
netlist's own names:
  BP1 = +460 V   6L6GC plates (OT centre tap merges here, primary DCR omitted),
                 screens (470 Ohm-1W stoppers), reverb driver (via T4 primary
                 DCR), tremolo oscillator plate load — all driven directly.
  BC  = +450 V   drawing node [C]: phase-inverter plate supply. Derived from
                 BP1 through the printed 1k-1W dropper (RD1) — a check on the
                 chart, not an input to it.
  BD  = +410 V   drawing node [D]: every 100k-loaded preamp triode (both
                 channel inputs, the vibrato 2nd stage, the mix driver, the
                 reverb recovery amp). Derived from BC through the printed
                 4.7k-1W dropper (RD2).
  -52 V          the fixed-bias grid line, off the dedicated PT tap's own
                 silicon-rectified, adjustable-pot supply (no hum-balance leg
                 on this platform, unlike ab763-twin's).

Heaters, PT primary/mains and the pilot lamp are omitted here (annotation
layer) — see netlist.cir, meta.yaml, and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ab763-super" / "schematic.kicad_sch"
s = Sch()


def input_stage(y, j1, j2, r1, r2, rleak, vref, vval, rload, rk, ck, rail, x=52):
    """Two-jack input: 68k stoppers -> grid (1M leak) -> triode -> plate load +
    RC cathode. Returns the triode pin dict."""
    gb = 40  # grid-bus x
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(12, y - 4, l, y - 4)          # the lead must REACH the jack label
    s.wire(r, y - 4, gb, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(12, y + 4, l, y + 4)
    s.wire(r, y + 4, gb, y + 4)
    s.wire(gb, y - 4, gb, y + 4)
    s.junction(gb, y)
    s.sym("R", rleak, "1M", gb, y + 3.81 + 4)
    s.gnd(gb, y + 7.62 + 4)
    t = s.triode(vref, vval, x, y)
    s.wire(gb, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], rail)
    s.wire(x, y + 7.62, x, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", x, y + 9)
    return t


def tone_stack(tee, ct, rs, cb, cm, vrt, vrb, vrv, cbr, sw, mid_ref, mid_val,
                mid_is_pot, xT=96, xv=114):
    """The blackface tone stack, wired as the C-FD sheet draws it: the plate
    feeds the network directly (nothing blocks DC ahead of it), so the slope
    resistor's foot sits at plate potential and the caps do the blocking.
    Node A is the plate node; node B the slope foot. The treble pot's LOWER
    lug shares a node with the bass pot's top; the bass pot is a rheostat
    above the middle leg. `mid_is_pot` False draws that leg as the Normal
    channel's fixed bleed resistor (mid_ref/mid_val = RSLN/"6.8k"); True
    draws it as the Vibrato channel's genuine Middle pot, wired as a rheostat
    in the bleed's exact place — same node, same footprint, the one part
    that differs between the two channels' otherwise-identical stacks. The
    stack's output (treble wiper, through the switched bright cap) drops to
    the row 11.1 mm below `tee` and stops there — the caller wires on from
    the returned x, since the two channels' downstream differs (Normal goes
    to RMD1/PIG; Vibrato goes straight into V2B's grid). Returns that x."""
    s.wire(52, tee, 78, tee)                      # node A (stack input)
    s.junction(52, tee)
    # treble: A -> 250 pF -> treble pot top; wiper is the stack output
    tl, tr = s.series_h("C", ct, "250p", 84, tee - 6)
    s.wire(78, tee, 78, tee - 6)
    s.wire(78, tee - 6, tl, tee - 6)
    s.wire(tr, tee - 6, xT, tee - 6)
    s.sym("POT", vrt, "250k-A treb", xT, tee - 6 + 3.81)
    # slope: A -> 100k -> node B
    sl, sr = s.series_h("R", rs, "100k", 83, tee + 6)
    s.wire(78, tee, 78, tee + 6)
    s.junction(78, tee)
    s.wire(78, tee + 6, sl, tee + 6)
    s.wire(sr, tee + 6, 87, tee + 6)
    s.junction(87, tee + 6)                       # node B
    # node B -> 0.1u -> the treble-bottom / bass-top node
    bl, br = s.series_h("C", cb, ".1u", 92, tee + 6)
    s.wire(87, tee + 6, bl, tee + 6)
    s.wire(br, tee + 6, xT, tee + 6)
    s.wire(xT, tee + 1.62, xT, tee + 6)           # treble bottom lug -> bass node
    s.sym("POT", vrb, "250k-A bass", xT, tee + 6 + 3.81)
    s.wire(xT + 5.08, tee + 9.81, xT + 12, tee + 9.81)   # bass wired as a rheostat
    s.wire(xT + 12, tee + 9.81, xT + 12, tee + 6)
    s.wire(xT + 12, tee + 6, xT, tee + 6)
    s.junction(xT, tee + 6)
    # node B -> 0.022u -> the middle leg (bleed resistor, or the Vibrato Middle pot)
    ml, mr = s.series_h("C", cm, ".022u", 92, tee + 13.62)
    s.wire(87, tee + 6, 87, tee + 13.62)
    s.wire(87, tee + 13.62, ml, tee + 13.62)
    s.wire(mr, tee + 13.62, xT, tee + 13.62)
    s.junction(xT, tee + 13.62)
    if mid_is_pot:
        s.sym("POT", mid_ref, mid_val, xT, tee + 13.62 + 3.81)
        s.wire(xT + 5.08, tee + 17.43, xT + 12, tee + 17.43)   # rheostat: wiper -> hot lug
        s.wire(xT + 12, tee + 17.43, xT + 12, tee + 13.62)
        s.wire(xT + 12, tee + 13.62, xT, tee + 13.62)
        s.gnd(xT, tee + 21.24)
    else:
        s.sym("R", mid_ref, mid_val, xT, tee + 17.43)
        s.gnd(xT, tee + 21.24)
    # treble wiper -> volume top
    s.wire(xT + 5.08, tee - 2.19, xv, tee - 2.19)
    s.wire(xv, tee - 2.19, xv, tee)
    s.sym("POT", vrv, "1M-A vol", xv, tee + 3.81)
    s.gnd(xv, tee + 7.62)
    # bright cap, in series with its panel switch, top lug -> wiper
    s.junction(xv, tee)
    s.wire(xv, tee, xv, tee - 9)
    cl, cr = s.series_h("C", cbr, "120p", xv + 10, tee - 9)
    s.wire(xv, tee - 9, cl, tee - 9)
    swl, swr = s.switch(sw, "Bright", xv + 19, tee - 9)
    s.wire(cr, tee - 9, swl, tee - 9)
    s.wire(swr, tee - 9, xv + 26, tee - 9)
    s.wire(xv + 26, tee - 9, xv + 26, tee + 3.81)
    s.wire(xv + 5.08, tee + 3.81, xv + 26, tee + 3.81)
    s.junction(xv + 26, tee + 3.81)
    # output drops to the row the caller's downstream wiring starts from
    s.wire(xv + 26, tee + 3.81, xv + 26, tee + 11.1)
    return xv + 26


# ============================ TITLE ==================================
s.note('Heaters, PT primary/mains and the pilot lamp omitted here — see netlist.cir, meta.yaml, layout.yaml. Rails: BP1 +460 (6L6GC plates, screens, reverb driver, tremolo osc.) · BC +450 node [C] (PI plates) · BD +410 node [D] (every 100k preamp stage) · bias -52 V')
s.note('Chart notice: voltages read to ground with an electronic voltmeter, values ±20%. Resistors ½ W 10% and capacitors at least 400 V unless marked.')

# ============================ NORMAL CHANNEL (top row) =================
YN = 64
s.text("Normal channel (two-knob stack — fixed bleed, no Middle)", 12, 44, 1.7)
t1 = input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RGN1", "V1", "12AX7",
                  "RLN1", "RKN1", "CKN1", "BD")
teeN = YN - 7.62 - 3.48
noutx = tone_stack(teeN, "CTN", "RSN", "CBN", "CBN2", "VRTN", "VRBN", "VRVN",
                    "CBRN", "SWBN", "RSLN", "6.8k", False, xT=96, xv=114)
# stack output (bright-capped treble wiper) -> RMD1 -> the PI-grid bus. The
# Normal channel has no second gain stage, so this resistor is its whole
# path onward, exactly mirroring amps/ab763's own RMD1.
s.wire(noutx, teeN + 11.1, 220, teeN + 11.1)
ml, mr = s.series_h("R", "RMD1", "220k", 230, teeN + 11.1)
s.wire(220, teeN + 11.1, ml, teeN + 11.1)
s.wire(mr, teeN + 11.1, 246, teeN + 11.1)
s.glabel("PIG", 246, teeN + 11.1, 0)

# ============================ VIBRATO CHANNEL (second row) =============
YV = 118
s.caption("Vibrato channel (reverb + tremolo) — three-knob stack, genuine Middle pot", 12, 86, 1.7)
t2 = input_stage(YV, "VIB 1", "VIB 2", "R1v", "R2v", "RGV1", "V2A", "12AX7",
                  "RLV1", "RKV1", "CKV1", "BD")
teeV = YV - 7.62 - 3.48
voutx = tone_stack(teeV, "CTV", "RSV", "CBV", "CBV2", "VRTV", "VRBV", "VRVV",
                    "CBRV", "SWBV", "VRMV", "250k-A mid", True, xT=96, xv=114)

# V2B second stage: grid fed straight off the volume wiper/bright-cap node —
# the pot's own ground pin is the DC return (netlist's RGV2 equivalent), no
# discrete grid-leak part on this drawing (none in bom.yaml).
# V2B stands to the RIGHT of the stack's output column. Drawn ON that column it
# shared it with its own 100k plate load, so the volume wiper's lead ran up
# through RLV2's body and out both its pins: the load was shorted out and the
# plate sat on the BD rail together with the grid it was supposed to drive.
XV2B = 152
t2b = s.triode("V2B", "12AX7", XV2B, YV)
s.wire(voutx, YV, t2b["g"][0], YV)
s.plate_load("RLV2", "100k", t2b["p"], "BD")
s.wire(XV2B, YV + 7.62, XV2B, YV + 9)
s.shunt_rc("RKV2", "820", "CKV2", "25u", XV2B, YV + 9)
# V2B plate tees to two independent couplers: CRS (500p) to the reverb driver
# grid, and CCV2 (0.02u) to the dry side of the mix node — matching notes.md's
# "feeds two places" description exactly.
teeb = YV - 7.62 - 3.48
s.wire(XV2B, teeb, 160, teeb)
s.junction(XV2B, teeb)
cl, cr = s.series_h("C", "CCV2", ".02u", 166, teeb)
s.wire(160, teeb, cl, teeb)
s.wire(cr, teeb, 176, teeb)
s.wire(176, teeb, 176, 150)
s.glabel("MIXG", 176, 150, 270)
# the reverb send tees off the plate ROW on its own riser, clear of the plate
# load column and of the rail flag at its head
s.junction(160, teeb)
s.wire(160, teeb, 160, teeb - 18)
rl, rr = s.series_h("C", "CRS", "500p", 128, teeb - 18)
s.wire(160, teeb - 18, rr, teeb - 18)
s.wire(rl, teeb - 18, 40, teeb - 18)
s.glabel("RVSEND", 40, teeb - 18, 180)

# ============================ REVERB + TREMOLO BLOCK (third row) =======
YR = 168
s.text("Reverb driver / recovery / mixer", 60, 150, 1.7)
s.glabel("RVSEND", 40, YR, 180)
s.wire(40, YR, 60, YR)
s.junction(60, YR)
# V4A + V4B paralleled reverb driver (both sections of one 12AT7)
t4a = s.triode("V4A", "12AT7", 72, YR)
t4b = s.triode("V4B", "12AT7", 72, YR + 22)
s.wire(60, YR, t4a["g"][0], YR)
s.wire(60, YR, 60, YR + 22)                   # the paralleled grid bus
s.wire(60, YR + 22, t4b["g"][0], YR + 22)
# The 1 MOhm leak hangs off the FOOT of the grid bus. Drawn on the bus itself
# the bus ran through the resistor body and out its far pin, shorting the leak
# and tying both driver grids to ground.
s.junction(60, YR + 22)
s.wire(60, YR + 22, 52, YR + 22)
s.sym("R", "RGRD", "1M", 52, YR + 25.81, lx=-9.4)
s.gnd(52, YR + 29.62)
# plates tied
s.wire(72, YR - 7.62, 72, YR - 10)
s.wire(72, YR + 22 - 7.62, 72, YR + 22 - 10)
s.wire(72, YR - 10, 82, YR - 10)
s.wire(72, YR + 12, 82, YR + 12)
s.wire(82, YR - 10, 82, YR + 12)
s.junction(82, YR - 10)
# shared cathode RKRD 2.2k || CKRD 25u — tied below V4B, clear of both tubes
cy = YR + 33
s.wire(72, YR + 7.62, 64, YR + 7.62)
s.wire(64, YR + 7.62, 64, cy)
s.wire(64, cy, 72, cy)
s.wire(72, YR + 22 + 7.62, 72, cy)
s.junction(72, cy)
s.shunt_rc("RKRD", "2.2k", "CKRD", "25u", 72, cy)
# reverb transformer T4 (driver -> tank), fed from BP1 through its own primary DCR
s.sym("OT_SE", "T4", "125A20B", 96, YR - 4)
s.wire(82, YR - 10, 87.11, YR - 10)
s.wire(87.11, YR - 10, 87.11, YR - 6.54)
s.wire(87.11, YR - 1.46, 87.11, YR + 2)
s.glabel("BP1", 87.11, YR + 2, 90)
s.wire(104.89, YR - 6.54, 110, YR - 6.54)
s.wire(110, YR - 6.54, 110, YR - 16)
s.glabel("REVERB TANK", 110, YR - 16, 90)
s.wire(104.89, YR - 1.46, 110, YR - 1.46)
s.gnd(110, YR - 1.46)

# reverb recovery V3B: tank return -> RGR1 220k -> grid; RLR1 100k -> BD; cathode
s.glabel("TANK RET", 118, YR - 6, 180)
gl2, gr2 = s.series_h("R", "RGR1", "220k", 128, YR - 6)
s.wire(118, YR - 6, gl2, YR - 6)
s.wire(gr2, YR - 6, 138, YR - 6)
s.wire(138, YR - 6, 138, YR)
t3b = s.triode("V3B", "12AX7", 148, YR)
s.wire(138, YR, t3b["g"][0], YR)
s.plate_load("RLR1", "100k", t3b["p"], "BD")
s.wire(148, YR + 7.62, 148, YR + 9)
s.shunt_rc("RKR1", "820", "CKR1", "25u", 148, YR + 9)
# recovery plate -> CCR1 0.003u -> VRREV 100k-L reverb level -> RMR 470k mixer
teer = YR - 7.62 - 3.48
s.wire(148, teer, 156, teer)
s.junction(148, teer)
cl, cr = s.series_h("C", "CCR1", ".003u", 162, teer)
s.wire(156, teer, cl, teer)
s.wire(cr, teer, 170, teer)
s.sym("POT", "VRREV", "100k-L rev", 170, teer + 3.81)
s.gnd(170, teer + 7.62)
s.wire(175.08, teer + 3.81, 182, teer + 3.81)
ml2, mr2 = s.series_h("R", "RMR", "470k", 188, teer + 3.81)
s.wire(182, teer + 3.81, ml2, teer + 3.81)
s.wire(mr2, teer + 3.81, 196, teer + 3.81)
s.wire(196, teer + 3.81, 196, 150)
s.glabel("MIXG", 196, 150, 90)   # same net as CCV2's dry-side MIXG stub above, by name

# mix driver V3a: grid = MIXG (dry Vibrato + recovered reverb); RMR2 220k mix-
# node reference to ground; RGD1 3.3M grid leak; CBD1 10p bright cap; RLD1
# 100k -> BD; RKD1 820 || CKD1
YM = YR + 22
s.glabel("MIXG", 202, YM, 180)
s.wire(206, YM, 210, YM)
s.junction(210, YM)
s.sym("R", "RMR2", "220k", 210, YM + 3.81)
s.gnd(210, YM + 7.62)
s.wire(210, YM, 216, YM)
s.sym("R", "RGD1", "3.3M", 216, YM + 3.81)
s.gnd(216, YM + 7.62)
s.wire(216, YM, 222, YM)
s.wire(222, YM, 222, YM - 6)
s.junction(222, YM)
cbl, cbr = s.series_h("C", "CBD1", "10p", 228, YM - 6)
s.wire(222, YM - 6, cbl, YM - 6)
s.wire(cbr, YM - 6, 234, YM - 6)
s.wire(234, YM - 6, 234, YM - 7.62 - 3.48)
t3a = s.triode("V3A", "12AX7", 234, YM)
s.wire(222, YM, t3a["g"][0], YM)
s.plate_load("RLD1", "100k", t3a["p"], "BD")
s.wire(234, YM + 7.62, 234, YM + 9)
s.shunt_rc("RKD1", "820", "CKD1", "25u", 234, YM + 9)
# mix-driver plate -> CCD1 0.001u -> PI hot grid line (PIG) — same net as the
# Normal channel's own PIG stub above (RMD1's output), joined by name alone;
# no physical wire run between the two, so neither stub is a pass-through.
teem = YM - 7.62 - 3.48
s.wire(234, teem, 240, teem)
s.junction(234, teem)
cl, cr = s.series_h("C", "CCD1", ".001u", 244, teem)
s.wire(240, teem, cl, teem)
s.wire(cr, teem, 250, teem)
s.glabel("PIG", 250, teem, 0)

# ============================ TREMOLO OSCILLATOR (excluded) ============
YT = 232
s.caption('Tremolo oscillator (V5, one 12AX7 half) — excluded from netlist.cir (notes.md)', 26, 199, 1.4)
s.note('The tremolo oscillator has no static DC operating point, so it is excluded from netlist.cir (notes.md); its supply taps BP1 directly, a driven node, so excluding it moves no gated node.')
t5 = s.triode("V5", "12AX7", 60, YT, lx=-16.0, ly=-12.0)
s.plate_load("RTO2", "220k", t5["p"], "BP1")
s.wire(60, YT + 7.62, 60, YT + 9)
s.shunt_rc("RKTO1", "2.7k", "CKTO1", "25u", 60, YT + 9)
# plate tees: (a) phase-shift network back to the grid, (b) the intensity feed
tee5 = YT - 7.62 - 3.48
s.junction(60, tee5)
cl, cr = s.series_h("C", "CTO1", ".01u", 74, tee5)   # plate -> node N1
s.wire(60, tee5, cl, tee5)
s.wire(cr, tee5, 90, tee5)
s.junction(90, tee5)                                  # N1: speed network
# Speed control: a 3 MOhm-RA pot used as a RHEOSTAT, wiper strapped back to
# its hot lug (the idiom the AA1164's own speed control is drawn with).
s.sym("POT", "VRSPD", "3M-RA speed", 98, tee5, rot=90, lx=-4.6, ly=-10.0)
s.wire(90, tee5, 94.19, tee5)
s.wire(98, tee5 - 5.08, 94.19, tee5 - 5.08)
s.wire(94.19, tee5 - 5.08, 94.19, tee5)
s.junction(94.19, tee5)
sl, sr = s.series_h("R", "RTO1", "100k", 108, tee5)
s.wire(101.81, tee5, sl, tee5)
s.gnd(sr, tee5, rot=0)
# N1 -> CTO2 -> node N2 -> RTOG 1M to ground -> grid. Routed well clear (in x)
# of the reverb driver's cathode network (RKRD/CKRD) directly above, so the
# two blocks' labels never crowd each other.
s.wire(90, tee5, 90, YT - 20)
cl2, cr2 = s.series_h("C", "CTO2", ".01u", 62, YT - 20)
s.wire(90, YT - 20, cr2, YT - 20)
s.wire(cl2, YT - 20, 38, YT - 20)
s.junction(38, YT - 20)
s.sym("R", "RTOG", "1M", 38, YT - 20 + 3.81)
s.gnd(38, YT - 20 + 7.62)
s.wire(38, YT - 20, 38, YT)
s.wire(38, YT, 52.38, YT)
s.note('The vibrato footswitch grounds the oscillator grid bus and stops the oscillator (period detail; not modelled here)')
# Intensity: the oscillator's PLATE PIN row (clear of the speed network above
# it) -> VRINT 50k-RA as a rheostat -> RINT 27k -> the optocoupler's neon lamp.
YI = t5["p"][1]
s.junction(60, YI)
s.wire(60, YI, 120.19, YI)
s.sym("POT", "VRINT", "50k-RA int", 124, YI, rot=90, lx=-4.6, ly=6.4)
s.wire(124, YI - 5.08, 120.19, YI - 5.08)
s.wire(120.19, YI - 5.08, 120.19, YI)
s.junction(120.19, YI)
il, ir = s.series_h("R", "RINT", "27k", 136, YI)
s.wire(127.81, YI, il, YI)
op = s.opto("OPTO", "neon + photocell", 152, YI + 2.54)
s.wire(ir, YI, op["l1"][0], op["l1"][1])
s.wire(op["l2"][0], op["l2"][1], op["l2"][0] - 6, op["l2"][1])
s.gnd(op["l2"][0] - 6, op["l2"][1])
s.wire(op["p1"][0], op["p1"][1], op["p1"][0] + 6, op["p1"][1])
s.glabel("MIXG", op["p1"][0] + 6, op["p1"][1], 0)     # photocell shunts the mix-driver grid
s.wire(op["p2"][0], op["p2"][1], op["p2"][0] + 6, op["p2"][1])
s.gnd(op["p2"][0] + 6, op["p2"][1])

# ============================ PHASE INVERTER (LTP) =====================
XPI = 300
YPH = 100  # hot
YPB = 132  # cold
s.text("Long-tailed-pair phase inverter (12AT7)", 270, 70, 1.7)
s.glabel("PIG", 264, YPH, 180)
cl, cr = s.series_h("C", "CPIA", ".001u", 272, YPH)
s.wire(264, YPH, cl, YPH)
s.wire(cr, YPH, XPI - 7.62, YPH)
t6a = s.triode("V6A", "12AT7", XPI, YPH)
t6b = s.triode("V6B", "12AT7", XPI, YPB)
s.plate_load("RLPA", "82k 5%", t6a["p"], "BC")
s.plate_load("RLPB", "100k 5%", t6b["p"], "BC")
# Shared tail. The cold half's lead is taken from V6B's CATHODE (YPB + 7.62)
# and routed UNDER the bottle: the common lane steps to x = XPI - 12 at y = 128,
# clear of the cold grid's own horizontals, and comes back up into the cathode
# pin. Until 2026-09-02 it was drawn from YPB - 7.62, which on an upright
# cx:TRIODE is the PLATE: RTAIL sat on V6B's plate node beside V6A's cathode,
# C2 with it, and V6B's cathode floated.
JY = 116
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, XPI - 8, YPH + 10)
s.wire(XPI - 8, YPH + 10, XPI - 8, 124)
s.wire(XPI - 8, 124, XPI - 12, 124)
s.wire(XPI - 12, 124, XPI - 12, 146)
s.wire(XPI - 12, 146, XPI, 146)
s.wire(XPI, 146, XPI, YPB + 7.62)
s.junction(XPI - 8, JY)
tl, tr = s.series_h("R", "RTAIL", "470", XPI - 13.5, JY)
s.wire(XPI - 8, JY, tr, JY)
s.wire(XPI - 19, JY, tl, JY)
s.wire(XPI - 30, JY, XPI - 19, JY)
s.junction(XPI - 26, JY)
s.junction(XPI - 22, JY)
s.sym("R", "RT2", "22k", XPI - 26, JY + 3.81)
s.gnd(XPI - 26, JY + 7.62)
s.sym("R", "RGPA", "1M", XPI - 22, JY - 8, lx=-9.4)
s.wire(XPI - 22, JY - 4.19, XPI - 22, JY)
s.wire(XPI - 22, JY - 11.81, XPI - 22, YPH - 2)
s.wire(XPI - 22, YPH - 2, XPI - 7.62, YPH - 2)
s.wire(XPI - 7.62, YPH - 2, XPI - 7.62, YPH)
s.junction(XPI - 7.62, YPH)
s.sym("R", "RGPB", "1M", XPI - 30, JY + 8, lx=-9.4)
s.wire(XPI - 30, JY + 4.19, XPI - 30, JY)
s.wire(XPI - 30, JY + 11.81, XPI - 30, YPB + 2)
s.wire(XPI - 30, YPB + 2, XPI - 7.62, YPB + 2)
s.wire(XPI - 7.62, YPB + 2, XPI - 7.62, YPB)
s.junction(XPI - 7.62, YPB)
# CPIB 0.1u/200 cold grid -> NFB node (AC ground)
cbl, cbr = s.series_h("C", "CPIB", ".1u 200V", XPI - 20, YPB)
s.wire(XPI - 7.62, YPB, cbr, YPB)
s.junction(XPI - 7.62, YPB)
s.wire(cbl, YPB, XPI - 46, YPB)
# NFB from speaker: SPKR -> RNFB 820 -> cold grid node
s.glabel("SPKR", XPI - 68, YPB + 12, 180)
nl, nr = s.series_h("R", "RNFB", "820", XPI - 58, YPB + 12)
s.wire(XPI - 68, YPB + 12, nl, YPB + 12)
s.wire(nr, YPB + 12, XPI - 46, YPB + 12)
s.wire(XPI - 46, YPB + 12, XPI - 46, YPB)
s.junction(XPI - 46, YPB)

# ============================ OUTPUT: 6L6GC pair ========================
s.text("Output pair — 6L6GC, fixed bias at -52 V through 220 kΩ leaks, one 1.5 kΩ stopper per grid", 340, 46, 1.6)
teea = YPH - 7.62 - 3.48
s.wire(XPI, teea, XPI + 10, teea)
s.junction(XPI, teea)
al, ar = s.series_h("C", "C1", ".1u 400V", XPI + 16, teea)
s.wire(XPI + 10, teea, al, teea)
s.wire(ar, teea, XPI + 26, teea)
s.wire(XPI + 26, teea, XPI + 26, 62)
s.junction(XPI + 26, 62)
s.sym("R", "RGL1", "220k 5%", XPI + 26, 62 - 3.81)
s.wire(XPI + 26, 62 - 7.62, XPI + 26, 54)
s.glabel("-52V", XPI + 26, 54, 90)
teec = YPB - 7.62 - 3.48
s.wire(XPI, teec, XPI + 10, teec)
s.junction(XPI, teec)
kl, kr = s.series_h("C", "C2", ".1u 400V", XPI + 16, teec)
s.wire(XPI + 10, teec, kl, teec)
s.wire(kr, teec, XPI + 32, teec)
s.wire(XPI + 32, teec, XPI + 32, 176)
s.junction(XPI + 32, 176)
s.sym("R", "RGL2", "220k 5%", XPI + 32, 176 + 3.81)
s.wire(XPI + 32, 176 + 7.62, XPI + 32, 188)
s.glabel("-52V", XPI + 32, 188, 270)

XO = XPI + 90
VOUT = {}
for gx, y, vref, stop, screen in [(XPI + 26, 76, "V7", "RST1", "RS1"),
                                    (XPI + 32, 152, "V8", "RST2", "RS2")]:
    s.wire(gx, y, gx + 20, y)
    s.junction(gx, y)
    sl, sr = s.series_h("R", stop, "1.5k", gx + 28, y)
    s.wire(gx + 20, y, sl, y)
    p = s.pentode(vref, "6L6GC", XO, y)
    VOUT[vref] = p
    s.wire(sr, y, XO - 7.62, y)
    s2l, s2r = s.series_h("R", screen, "470 1W", p["g2"][0] + 7.81, p["g2"][1])
    s.wire(p["g2"][0], p["g2"][1], s2l, p["g2"][1])
    s.wire(s2r, p["g2"][1], p["g2"][0] + 15, p["g2"][1])
    s.glabel("BP1", p["g2"][0] + 15, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])
s.wire(XPI + 26, 62, XPI + 26, 76)
s.wire(XPI + 32, 176, XPI + 32, 152)

# output transformer T3
s.sym("OT_PP", "T3", "125A9A", XO + 44, 114)
s.wire(XO, VOUT["V7"]["p"][1], XO, 62)
s.wire(XO, 62, XO + 35.11, 62)
s.wire(XO + 35.11, 62, XO + 35.11, 108.92)     # V7 plate -> PRI_A
s.wire(XO, VOUT["V8"]["p"][1], XO, 136)
s.wire(XO, 136, XO + 30, 136)
s.wire(XO + 30, 136, XO + 30, 119.08)
s.wire(XO + 30, 119.08, XO + 35.11, 119.08)    # V8 plate -> PRI_B
s.wire(XO + 35.11, 114, XO + 32.57, 114)
s.wire(XO + 32.57, 114, XO + 32.57, 111)
s.glabel("BP1", XO + 32.57, 111, 90)           # centre tap
s.wire(XO + 52.89, 111.46, XO + 55.43, 111.46)
s.glabel("SPKR", XO + 55.43, 111.46, 0)
s.wire(XO + 52.89, 116.54, XO + 55.43, 116.54)
s.glabel("GND", XO + 55.43, 116.54, 0)

# ============================ POWER SUPPLY (bottom) =====================
YPW = 262
s.text("Power supply — T1 125P5D 360-0-360 V, GZ34 full-wave, T2 125C1A choke · standby/mains AC switch omitted", 40, 238, 1.5)
pt = s.pt("T1", "125P5D · 360-0-360V", 40, YPW)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 6, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 6, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 6, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 6, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
# GZ34 rectifier
s.glabel("HT_A", 74, YPW - 12, 90)
s.wire(74, YPW - 12, 74, YPW - 9.5)
va = s.diode_tube("V9A", "GZ34", 74, YPW - 1.88, lx=-11.4)
s.glabel("HT_B", 86, YPW - 12, 90)
s.wire(86, YPW - 12, 86, YPW - 9.5)
vb = s.diode_tube("V9B", "GZ34", 86, YPW - 1.88, lx=6.0)
s.wire(74, YPW + 5.74, 74, YPW + 8)
s.wire(86, YPW + 5.74, 86, YPW + 8)
s.wire(74, YPW + 8, 100, YPW + 8)
s.junction(86, YPW + 8)
# post-standby reservoir C10 (bom: 70 uF, physically two identical cans in
# parallel per its own "(x2)" count — drawn as the one lumped value, same
# convention as a repeated-part count elsewhere in the corpus), bled by two
# resistors (RBL1, RBL2) both bridging the same node to ground
s.sym("C", "C10", "70u", 100, YPW + 11.81)
s.gnd(100, YPW + 11.81 + 3.81)
s.junction(100, YPW + 8)
s.junction(118, YPW + 8)
s.shunt_r("RBL1", "220k 1W", 118, YPW + 8)
s.junction(130, YPW + 8)
s.shunt_r("RBL2", "220k 1W", 130, YPW + 8)
s.wire(100, YPW + 8, 142, YPW + 8)
# choke T2 -> BP1 node (screens/plates/reverb driver), filtered by C11
lch, rch = s.choke("T2", "125C1A", 148.62, YPW + 8, lx=-5.0, ly=-7.4)
s.wire(142, YPW + 8, lch, YPW + 8)
s.wire(rch, YPW + 8, 162, YPW + 8)
s.junction(159, YPW + 8)
s.glabel("BP1", 159, YPW + 4, 90)
s.wire(159, YPW + 4, 159, YPW + 8)
s.junction(162, YPW + 8)
s.sym("C", "C11", "20u 525V", 162, YPW + 11.81)
s.gnd(162, YPW + 11.81 + 3.81)
# RD1 1k-1W -> BC node, filtered by C12
l, r = s.series_h("R", "RD1", "1k 1W", 168, YPW + 8)
s.wire(162, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 182, YPW + 8)
s.junction(176, YPW + 8)
s.glabel("BC", 176, YPW + 4, 90)
s.wire(176, YPW + 4, 176, YPW + 8)
s.junction(182, YPW + 8)
s.sym("C", "C12", "20u 525V", 182, YPW + 11.81)
s.gnd(182, YPW + 11.81 + 3.81)
# RD2 4.7k-1W -> BD node (chart's own dropper — no further reservoir on this rail)
l, r = s.series_h("R", "RD2", "4.7k 1W", 190, YPW + 8)
s.wire(182, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 202, YPW + 8)
s.junction(198, YPW + 8)
s.glabel("BD", 198, YPW + 4, 90)
s.wire(198, YPW + 4, 198, YPW + 8)

# ============================ BIAS SUPPLY ================================
YB = YPW - 4
s.text("Bias supply — a dedicated PT tap, silicon-rectified, 25 µF-filtered, through an adjustable 10 kΩ-L pot", 218, 236, 1.4)
s.glabel("BIAS TAP", 218, YB, 180)
s.wire(218, YB, 221.92, YB)
s.sym("DIODE_SS", "DBIAS", "Si", 227, YB, lx=-2.0, ly=-5.4)
s.wire(232, YB, 236, YB)
l, r = s.series_h("R", "RBIAS", "470", 240, YB)
s.wire(236, YB, l, YB)
s.wire(r, YB, 250, YB)
s.junction(246, YB)
s.sym("C", "CBIAS", "25u 50V", 246, YB + 3.81)
s.gnd(246, YB + 7.62)
# The bias pot is drawn as a two-terminal element in the -52 V feed, so its
# wiper is strapped to its hot lug: an adjustable pot with a floating wiper is
# a fixed 10 k. (No hum-balance leg on this platform - see the header.)
s.wire(250, YB, 258.19, YB)
s.sym("POT", "VRBIAS", "10k-L bias", 262, YB, rot=90, lx=-3.8, ly=6.4)
s.wire(262, YB - 5.08, 258.19, YB - 5.08)
s.wire(258.19, YB - 5.08, 258.19, YB)
s.junction(258.19, YB)
s.wire(265.81, YB, 274, YB)
s.glabel("-52V", 274, YB, 0)

s.write(OUT)
print(f"wrote {OUT}")
