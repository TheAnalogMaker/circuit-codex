#!/usr/bin/env python3
"""Generate amps/ab763-super/schematic.kicad_sch from the stage-template library.

Values per the published "SUPER-REVERB-AMP AB763" drawing (C-FD), cited in
amps/ab763-super/meta.yaml. Two preamp channel rows at the top, each a gain
stage into its tone stack into a second gain stage (Normal — the plain two-knob
stack; Vibrato — the genuine three-knob FMV stack, its Middle a real 10 kΩ pot
in place of the Normal channel's fixed 6.8 kΩ bleed resistor), the reverb
driver/recovery/mixer block below them, the long-tailed-pair phase inverter and
the 6L6GC pair on the right, the tremolo (both halves of V5 — the phase-shift
oscillator and the neon-lamp driver, excluded from netlist.cir, neither having a
static DC point) under the output pair, and the rectifier/filter and bias
supplies along the bottom.

Two cathode networks are SHARED, and the sheet draws each of them once, under
the boxed letter its source drawing gives it. Node KA (boxed [A]) is one 820 Ω
/ 25 µF carrying both second stages, Normal and Vibrato; node KE (boxed [E]) is
one 820 Ω / 25 µF carrying both the mix driver and the reverb recovery. The
stage that does not carry the parts reaches its network by that global label —
the drawing's own boxed connection, redrawn as a label rather than invented as
a second resistor.

Redrawn from circuit facts — never a trace of a factory drawing. Rails, in the
netlist's own names:
  BP1 = +460 V   6L6GC plates (OT centre tap merges here, primary DCR omitted),
                 screens (470 Ohm-1W stoppers), reverb driver (via T4 primary
                 DCR), tremolo oscillator plate load — all driven directly.
  BC  = +450 V   drawing node [C]: phase-inverter plate supply. Derived from
                 BP1 through the printed 1k-1W dropper (RD1) — a check on the
                 chart, not an input to it.
  BD  = +410 V   drawing node [D]: every 100k-loaded preamp triode (both
                 channel inputs, both channels' second stages, the mix driver,
                 the reverb recovery amp). Derived from BC through the printed
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


def input_stage(y, j1, j2, r1, r2, rleak, vref, vval, rload, rk, ck, rail, x=52,
                unit=None):
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
    t = s.triode(vref, vval, x, y, unit=unit)
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
s.note('Heaters, PT primary/mains and the pilot lamp omitted here — see the netlist, the sources list and the board drawing. Rails: BP1 +460 (6L6GC plates, screens, reverb driver, tremolo osc.) · BC +450 node [C] (PI plates) · BD +410 node [D] (every 100k preamp stage) · bias -52 V')
s.note('Chart notice: voltages read to ground with an electronic voltmeter, values ±20%. Resistors ½ W 10% and capacitors at least 400 V unless marked.')

# ============================ NORMAL CHANNEL (top row) =================
YN = 64
s.text("Normal channel (two-knob stack — fixed bleed, no Middle)", 12, 44, 1.7)
# Socket basing from the factory layout (3299×2551): on each channel's 7025 the
# input stage's +270 V plate (100k slope) lands on pin 1 and the second stage's
# (.047 coupler) on pin 6 — V1A/V2A unit 2, V1B/V2B unit 1.
t1 = input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RGN1", "V1A", "12AX7",
                  "RLN1", "RKN1", "CKN1", "BD", unit=2)
teeN = YN - 7.62 - 3.48
noutx = tone_stack(teeN, "CTN", "RSN", "CBN", "CBN2", "VRTN", "VRBN", "VRVN",
                    "CBRN", "SWBN", "RSLN", "6.8k", False, xT=96, xv=114)

# V1B second stage: grid fed straight off the volume wiper/bright-cap node, the
# same idiom the Vibrato channel's own V2B uses below (the pot's ground pin is
# the DC return — netlist RGN2; no discrete grid-leak part on this drawing).
# Its cathode carries NO resistor: the drawing boxes that pin [A] and returns it
# to the 820 Ohm / 25 uF drawn once at V2B, so the label is the connection.
XV1B = 152
t1b = s.triode("V1B", "12AX7", XV1B, YN, unit=1)
s.wire(noutx, YN, t1b["g"][0], YN)
s.plate_load("RLN2", "100k", t1b["p"], "BD")
s.wire(XV1B, YN + 7.62, XV1B, YN + 11)
s.glabel("KA", XV1B, YN + 11, 270)
# V1B plate -> CCN2 0.047u -> RMD1 220k -> the PI-grid bus, mirroring
# amps/ab763's own RMD1.
s.wire(XV1B, teeN, 196, teeN)
s.junction(XV1B, teeN)
cl, cr = s.series_h("C", "CCN2", ".047u", 202, teeN)
s.wire(196, teeN, cl, teeN)
s.wire(cr, teeN, 214, teeN)
s.wire(214, teeN, 214, YN)
s.wire(214, YN, 220, YN)
ml, mr = s.series_h("R", "RMD1", "220k", 230, YN)
s.wire(220, YN, ml, YN)
s.wire(mr, YN, 246, YN)
s.glabel("PIG", 246, YN, 0)

# ============================ VIBRATO CHANNEL (second row) =============
YV = 118
s.caption("Vibrato channel (reverb + tremolo) — three-knob stack, genuine Middle pot", 12, 86, 1.7)
t2 = input_stage(YV, "VIB 1", "VIB 2", "R1v", "R2v", "RGV1", "V2A", "12AX7",
                  "RLV1", "RKV1", "CKV1", "BD", unit=2)
teeV = YV - 7.62 - 3.48
voutx = tone_stack(teeV, "CTV", "RSV", "CBV", "CBV2", "VRTV", "VRBV", "VRVV",
                    "CBRV", "SWBV", "VRMV", "10k-A mid", True, xT=96, xv=114)

# V2B second stage: grid fed straight off the volume wiper/bright-cap node —
# the pot's own ground pin is the DC return (netlist's RGV2 equivalent), no
# discrete grid-leak part on this drawing (none in bom.yaml).
# V2B stands to the RIGHT of the stack's output column. Drawn ON that column it
# shared it with its own 100k plate load, so the volume wiper's lead ran up
# through RLV2's body and out both its pins: the load was shorted out and the
# plate sat on the BD rail together with the grid it was supposed to drive.
XV2B = 152
t2b = s.triode("V2B", "12AX7", XV2B, YV, unit=1)
s.wire(voutx, YV, t2b["g"][0], YV)
s.plate_load("RLV2", "100k", t2b["p"], "BD")
s.wire(XV2B, YV + 7.62, XV2B, YV + 9)
# Cathode network [A] — drawn HERE, once, and carrying V1B's current too: the
# label stub is the drawing's boxed [A], not a second network.
s.shunt_rc("RKA", "820", "CKA", "25u", XV2B, YV + 9)
s.junction(XV2B, YV + 9)
s.wire(XV2B, YV + 9, XV2B + 16, YV + 9)
s.glabel("KA", XV2B + 16, YV + 9, 0)
# V2B plate -> CCV2 (0.02u) -> the dry node, which feeds BOTH the reverb send
# (CRS, 500p) and, through 3.3M || 10 pF, the mix driver's grid. Until
# 2026-09-10 the send was drawn off the plate itself, ahead of CCV2.
teeb = YV - 7.62 - 3.48
s.wire(XV2B, teeb, 160, teeb)
s.junction(XV2B, teeb)
cl, cr = s.series_h("C", "CCV2", ".02u", 166, teeb)
s.wire(160, teeb, cl, teeb)
s.wire(cr, teeb, 176, teeb)
s.junction(176, teeb)
s.wire(176, teeb, 176, 150)
s.glabel("DRY", 176, 150, 270)
# the reverb send rises from the dry node on its own riser, clear of the plate
# load column and of the rail flag at its head
s.wire(176, teeb, 176, teeb - 18)
rl, rr = s.series_h("C", "CRS", "500p", 128, teeb - 18)
s.wire(176, teeb - 18, rr, teeb - 18)
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
# The tank return lands straight on the grid, and RGR1 220k is that grid's
# leak to ground, as the C-FD sheet draws it (until 2026-09-10 the 220k was
# drawn in series from the tank return).
s.glabel("TANK RET", 118, YR - 6, 180)
s.wire(118, YR - 6, 138, YR - 6)
s.junction(126, YR - 6)
s.sym("R", "RGR1", "220k", 126, YR - 6 + 3.81)
s.gnd(126, YR - 6 + 7.62)
s.wire(138, YR - 6, 138, YR)
t3b = s.triode("V3B", "12AX7", 148, YR)
s.wire(138, YR, t3b["g"][0], YR)
s.plate_load("RLR1", "100k", t3b["p"], "BD")
s.wire(148, YR + 7.62, 148, YR + 9)
# Cathode network [E] — drawn HERE, once, and carrying V3A's current too.
s.shunt_rc("RKE", "820", "CKE", "25u", 148, YR + 9)
s.junction(148, YR + 9)
s.wire(148, YR + 9, 134, YR + 9)
s.glabel("KE", 134, YR + 9, 180)
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
s.glabel("MIXG", 196, 150, 90)   # the mix driver's grid (below), joined by name

# mix driver V3a, as the C-FD sheet draws it: the dry node reaches the grid
# through RGD1 3.3M with CBD1 10p across it, IN SERIES; the grid (MIXG) takes
# the reverb return (RMR 470k, above) and its DC return RMR2 220k to ground.
# RLD1 100k -> BD; cathode to the shared [E] network by label, no resistor
# here. Until 2026-09-10 this sheet drew RGD1 as a grid leak to ground and
# CBD1 from the grid to the PLATE.
YM = YR + 22
s.glabel("DRY", 198, YM - 14, 90)
s.wire(198, YM - 14, 198, YM)
s.junction(198, YM - 6)
gl, gr = s.series_h("R", "RGD1", "3.3M", 204, YM)
s.wire(198, YM, gl, YM)
s.wire(gr, YM, 212, YM)
cbl, cbr = s.series_h("C", "CBD1", "10p", 204, YM - 6)
s.wire(198, YM - 6, cbl, YM - 6)
s.wire(cbr, YM - 6, 212, YM - 6)
s.wire(212, YM - 6, 212, YM)
s.junction(212, YM)
t3a = s.triode("V3A", "12AX7", 234, YM)
s.wire(212, YM, t3a["g"][0], YM)
s.junction(218, YM)
s.sym("R", "RMR2", "220k", 218, YM + 3.81, lx=-9.4)   # the grid leak
s.gnd(218, YM + 7.62)
s.junction(222, YM)
s.wire(222, YM, 222, YM - 12)
s.glabel("MIXG", 222, YM - 12, 90)
s.plate_load("RLD1", "100k", t3a["p"], "BD")
# Cathode: the drawing boxes this pin [E] and returns it to the 820 Ohm / 25 uF
# drawn at the reverb recovery. No resistor of its own.
s.wire(234, YM + 7.62, 234, YM + 11)
s.glabel("KE", 234, YM + 11, 270)
# mix-driver plate -> CCD1 0.1u -> node X -> RMIXV 220k -> the phase-inverter
# input junction (PIG), where the Normal channel's RMD1 lands too, joined by
# name. The Intensity control hangs from X and the photocell shunts its wiper
# to ground: the tremolo works on this stage's OUTPUT. Until 2026-09-10 this
# sheet drew CCD1 as .001 straight to PIG, with no 220k and no Intensity here.
teem = YM - 7.62 - 3.48
s.wire(234, teem, 240, teem)
s.junction(234, teem)
cl, cr = s.series_h("C", "CCD1", ".1u", 244, teem)
s.wire(240, teem, cl, teem)
ml, mr = s.series_h("R", "RMIXV", "220k", 258, teem)
s.wire(cr, teem, ml, teem)
s.wire(mr, teem, 266, teem)
s.glabel("PIG", 266, teem, 0)
s.junction(252, teem)                                   # X
s.wire(252, teem, 252, teem + 6)
s.sym("POT", "VRINT", "50k-RA int", 252, teem + 9.81, lx=6.0, ly=6.0)
s.gnd(252, teem + 13.62)
s.wire(257.08, teem + 9.81, 262, teem + 9.81)
s.glabel("PHOTOCELL", 262, teem + 9.81, 0)

# ============================ PHASE INVERTER (LTP) =====================
XPI = 300
YPH = 100  # hot
YPB = 132  # cold
s.text("Long-tailed-pair phase inverter (12AT7)", 270, 70, 1.7)
s.glabel("PIG", 264, YPH, 180)
cl, cr = s.series_h("C", "CPIA", ".001u", 272, YPH)
s.wire(264, YPH, cl, YPH)
s.wire(cr, YPH, XPI - 7.62, YPH)
# The C-FD layout page (3299 x 2551) runs the 82K plate load to pin 1 and the
# 100K to pin 6, both lettered +230 V: the hot, .001-fed half is on 1/2/3.
t6a = s.triode("V6A", "12AT7", XPI, YPH, unit=2)
t6b = s.triode("V6B", "12AT7", XPI, YPB, unit=1)
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
# The 22k tail lands on the feedback node F, where the 820 from the speaker,
# the .1-200 from the cold grid and a 100 to ground meet, as the C-FD sheet
# draws the four on one vertical. Until 2026-09-10 this sheet grounded the tail
# and had no 100.
s.sym("R", "RT2", "22k", XPI - 26, JY + 3.81)
s.wire(XPI - 26, JY + 7.62, XPI - 26, YPB)
s.junction(XPI - 26, YPB)
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
# ... and the feedback node's 100 to ground
s.junction(XPI - 46, YPB + 12)
s.wire(XPI - 46, YPB + 12, XPI - 46, YPB + 14)
s.sym("R", "RFB1", "100", XPI - 46, YPB + 17.81)
s.gnd(XPI - 46, YPB + 21.62)

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

# ============================ TREMOLO (excluded) =======================
# V5 is a 12AX7 with BOTH halves in use, as the C-FD sheet draws it (read at
# 3299 x 2551): V5A the phase-shift oscillator (+280 V plate, +2.5 V cathode)
# and V5B the neon-lamp driver (+390 V plate, +17.0 V cathode). The ladder:
#   plate -.02- S [Speed 3M-RA + 100k to ground] -.01- N1 -.01- grid,
#   with 1M from N1 and 1M from the grid meeting at J (the footswitch
#   junction), and J -2.2M- the bias supply's filter node. V5B's grid is N1.
# Until 2026-09-10 this sheet drew one triode, a two-cap ladder to a grounded
# 1M, and an Intensity rheostat plus a 27k in series with the lamp off the
# oscillator's plate, with the photocell on the mix driver's grid.
YT = 256
XA, XB = 340, 406
s.caption('Tremolo — oscillator V5A and neon-lamp driver V5B; neither half has a static DC operating point, so both are excluded from the netlist (see the circuit story)', 296, 203, 1.4)
s.note('Neither tremolo half has a static DC operating point, so V5 is excluded from the netlist (see the circuit story); both halves tap BP1 directly, a driven node, so excluding them moves no gated node.')
# The C-FD layout page (3299 x 2551) puts the oscillator on pins 1/2/3 (+280 V
# at pin 1, +2.5 V at pin 3) and the lamp driver on 6/7/8 (+390 V at pin 6,
# +17.0 V at pin 8): V5A is datasheet unit 2, V5B unit 1.
t5a = s.triode("V5A", "12AX7", XA, YT, unit=2)
t5b = s.triode("V5B", "12AX7", XB, YT, unit=1)
s.plate_load("RTO2", "220k", t5a["p"], "BP1")
s.sym("R", "RKTO1", "2.7k", XA, YT + 11.43)
s.gnd(XA, YT + 15.24)
s.sym("C", "CKTO1", "25u", XA + 8, YT + 11.43)
s.wire(XA, YT + 7.62, XA + 8, YT + 7.62)
s.wire(XA, YT + 15.24, XA + 8, YT + 15.24)
tee5 = YT - 7.62 - 3.48
YN1 = YT - 32                                   # the N1 row
s.junction(XA, tee5)
cl, cr = s.series_h("C", "CTO1", ".02u", XA + 10, tee5)
s.wire(XA, tee5, cl, tee5)
s.wire(cr, tee5, XA + 18, tee5)                 # S
s.junction(XA + 18, tee5)
# Speed control: a 3 MOhm-RA pot used as a RHEOSTAT, wiper strapped back to
# its hot lug (the idiom the AA1164's own speed control is drawn with).
s.sym("POT", "VRSPD", "3M-RA speed", XA + 26, tee5, rot=90, lx=-4.6, ly=6.4)
s.wire(XA + 18, tee5, XA + 22.19, tee5)
s.wire(XA + 26, tee5 - 5.08, XA + 22.19, tee5 - 5.08)
s.wire(XA + 22.19, tee5 - 5.08, XA + 22.19, tee5)
s.junction(XA + 22.19, tee5)
sl, sr = s.series_h("R", "RTO1", "100k", XA + 36, tee5)
s.wire(XA + 29.81, tee5, sl, tee5)
s.wire(sr, tee5, XA + 42, tee5)
s.gnd(XA + 42, tee5, rot=0)
# S -.01- N1, along the row above the plate load's rail flag
s.wire(XA + 18, tee5, XA + 18, YN1)
cl, cr = s.series_h("C", "CTO2", ".01u", XA - 10, YN1)
s.wire(XA + 18, YN1, cr, YN1)
s.wire(cl, YN1, XA - 20, YN1)                   # N1
s.junction(XA - 20, YN1)
# N1 -1M- J
sl, sr = s.series_h("R", "RTOG1", "1M", XA - 32, YN1)
s.wire(XA - 20, YN1, sr, YN1)
s.wire(sl, YN1, XA - 44, YN1)
# N1 -.01- the grid node; the grid node -1M- J
s.sym("C", "CTO3", ".01u", XA - 20, YT - 16)
s.wire(XA - 20, YN1, XA - 20, YT - 19.81)
s.wire(XA - 20, YT - 12.19, XA - 20, YT)
s.junction(XA - 20, YT)
s.wire(XA - 20, YT, t5a["g"][0], YT)
sl, sr = s.series_h("R", "RTOG2", "1M", XA - 32, YT)
s.wire(XA - 20, YT, sr, YT)
s.wire(sl, YT, XA - 44, YT)
# J, and its 2.2M to the bias supply's filter node
s.wire(XA - 44, YN1, XA - 44, YT)
s.junction(XA - 44, YT)
s.sym("R", "RTOG3", "2.2M", XA - 44, YT + 3.81, lx=-9.4)
s.wire(XA - 44, YT + 7.62, XA - 44, YT + 11)
s.glabel("BIAS FILTER", XA - 44, YT + 11, 270)
s.note('The vibrato footswitch grounds the junction of the two 1 MΩ ladder resistors and the 2.2 MΩ, and stops the oscillator (the pedal jack is not drawn here)')
# N1 -> the lamp driver's grid, over the top of the ladder
s.wire(XA - 20, YN1, XA - 20, YN1 - 12)
s.wire(XA - 20, YN1 - 12, XB - 14, YN1 - 12)
s.wire(XB - 14, YN1 - 12, XB - 14, YT)
s.wire(XB - 14, YT, t5b["g"][0], YT)
# lamp driver: 100k cathode, 10M plate bleeder, the neon lamp in series with
# 100k to the +460 V rail
s.sym("R", "RKTO2", "100k", XB, YT + 11.43)
s.gnd(XB, YT + 15.24)
s.sym("C", "CKTO2", "25u", XB + 8, YT + 11.43)
s.wire(XB, YT + 7.62, XB + 8, YT + 7.62)
s.wire(XB, YT + 15.24, XB + 8, YT + 15.24)
s.plate_load("RTO10", "10M", t5b["p"], "BP1")
op = s.opto("OPTO", "neon + photocell", XB + 24, tee5 + 2.54, ly=-10.0)
s.junction(XB, tee5)
s.wire(XB, tee5, op["l1"][0], op["l1"][1])
s.wire(op["l2"][0], op["l2"][1], op["l2"][0], YT)
s.wire(op["l2"][0], YT, XB + 24, YT)
s.sym("R", "RLAMP", "100k", XB + 24, YT + 3.81)
s.wire(XB + 24, YT + 7.62, XB + 24, YT + 10)
s.glabel("BP1", XB + 24, YT + 10, 270)
# the photocell shunts the Intensity control's wiper (at the mix driver's
# output) to ground
s.wire(op["p1"][0], op["p1"][1], op["p1"][0] + 6, op["p1"][1])
s.glabel("PHOTOCELL", op["p1"][0] + 6, op["p1"][1], 0)
s.wire(op["p2"][0], op["p2"][1], op["p2"][0] + 4, op["p2"][1])
s.gnd(op["p2"][0] + 4, op["p2"][1])

# ============================ POWER SUPPLY (bottom) =====================
YPW = 262
s.text("Power supply — T1 125P5D 360-0-360 V, GZ34 full-wave, T2 125C1A choke · standby/mains AC switch omitted", 40, 238, 1.5)
pt = s.pt("T1", "125P5D · 360-0-360V", 40, YPW)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 6, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 6, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 6, pt["pri2"][1])
s.glabel("MAINS N", pt["pri2"][0] - 6, pt["pri2"][1], 180)
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
# post-standby reservoir: two 70 uF / 350 V cans IN SERIES (C10 over C13),
# each with its own 220k-1W balancing resistor across it (RBL1, RBL2), as the
# C-FD sheet draws it. Until 2026-09-10 this was one lumped 70 uF with both
# 220k from the top node to ground.
s.junction(100, YPW + 8)
s.sym("C", "C10", "70u 350V", 100, YPW + 11.81)
s.junction(112, YPW + 8)
s.sym("R", "RBL1", "220k 1W", 112, YPW + 11.81)
s.wire(100, YPW + 15.62, 112, YPW + 15.62)
s.junction(100, YPW + 15.62)
s.junction(112, YPW + 15.62)
s.sym("C", "C13", "70u 350V", 100, YPW + 19.43)
s.sym("R", "RBL2", "220k 1W", 112, YPW + 19.43)
s.wire(100, YPW + 23.24, 112, YPW + 23.24)
s.gnd(100, YPW + 23.24)
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
s.text("Bias supply — PT tap, silicon rectifier, 25 µF filter; 10 kΩ-L pot over a 27 kΩ leg, wiper to -52 V", 218, 236, 1.4)
s.glabel("BIAS TAP", 218, YB, 180)
s.wire(218, YB, 221.92, YB)
s.sym("DIODE_SS", "DBIAS", "Si", 227, YB, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(232, YB, 236, YB)
l, r = s.series_h("R", "RBIAS", "470", 240, YB)
s.wire(236, YB, l, YB)
s.wire(r, YB, 250, YB)
s.junction(246, YB)
s.sym("C", "CBIAS", "25u 50V", 246, YB + 3.81)
s.gnd(246, YB + 7.62)
# The filter node also takes the tremolo ladder's 2.2M (RTOG3).
s.wire(250, YB, 258.19, YB)
s.junction(254, YB)
s.wire(254, YB, 254, YB - 6)
s.glabel("BIAS FILTER", 254, YB - 6, 90)
# The 10k-L pot's track runs from the filter node to a 27k leg to ground, and
# its WIPER is the -52 V grid line: the C-FD sheet's -52V line runs to the
# wiper arrow. Until 2026-09-10 the pot was drawn as a rheostat in series with
# the line, and the 27k was drawn in the tremolo as an Intensity series
# resistor. (No hum-balance leg on this platform - see the header.)
s.sym("POT", "VRBIAS", "10k-L bias", 262, YB, rot=90, lx=-3.8, ly=6.4)
s.wire(265.81, YB, 270, YB)
s.sym("R", "RBIAS2", "27k", 270, YB + 3.81)
s.gnd(270, YB + 7.62)
s.wire(262, YB - 5.08, 262, YB - 10)
s.wire(262, YB - 10, 276, YB - 10)
s.glabel("-52V", 276, YB - 10, 0)

s.write(OUT)
print(f"wrote {OUT}")
