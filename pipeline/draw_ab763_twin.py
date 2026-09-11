#!/usr/bin/env python3
"""Generate amps/ab763-twin/schematic.kicad_sch from the stage-template library.

Values per the published "TWIN REVERB-AMP AB763" drawing (C-FD), whose title block
and printed chart are cited in amps/ab763-twin/meta.yaml. The largest sheet in the
corpus, and the only one drawn on A2: two full three-knob preamp channels at the
top, the reverb send / driver / recovery / mix block below them, the tremolo
oscillator and its optocoupler under that, the long-tailed-pair phase inverter and
the four 6L6GC outputs on the right, and the silicon supply and bias supply along
the bottom.

Redrawn from circuit facts — never a trace of a factory drawing. Rails, in the
netlist's names and the drawing's boxed letters:
  B+1 = +460 V  reservoir, 6L6GC plates, output-transformer centre tap
  B+2 = +458 V  drawing node [B]: screens, reverb-transformer feed, tremolo
  B+3 = +450 V  drawing node [C]: phase-inverter plate supply
  B+4 = +410 V  drawing node [D]: all six preamp plate loads
  -52 V         the fixed-bias grid line off the balance control
Two more boxed letters carry cathodes rather than rails: [A] is the 820 Ohm/25 uF
network the two channels' second stages share, [E] the one the reverb recovery and
the mix driver share. Both are drawn once, as the sheet draws them.

Heaters, the pilot lamp and the mains switching are omitted here (annotation
layer) — see netlist.cir, meta.yaml, and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ab763-twin" / "schematic.kicad_sch"
s = Sch()


def input_stage(y, j1, j2, r1, r2, rleak, vref, vval, rload, rk, ck, rail, x=52):
    """Two-jack input: 68k stoppers -> grid (1M leak) -> triode -> plate load + RC
    cathode. Returns the triode pin dict."""
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


def tone_stack(tee, ct, rs, cb, cm, vrt, vrb, vrm, vrv, cbr, x2, xv=118):
    """The blackface three-knob (FMV) stack, wired as the C-FD sheet draws it, then
    the 1M volume with its switched bright cap across it.

    The plate feeds the network directly — nothing blocks DC ahead of it — so the
    slope resistor's foot sits at plate potential and the capacitors do the
    blocking. Node A is the plate node; node B the slope foot. The treble pot's
    LOWER lug shares a node with the bass pot's top; the bass pot is a rheostat
    above the middle pot, itself a rheostat to ground. The stack's output is the
    TREBLE WIPER alone. Returns the x at which the volume wiper leaves.
    """
    xT = 96          # the three tone pots share one column
    s.wire(52, tee, 78, tee)                     # node A (stack input)
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
    s.junction(87, tee + 6)                      # node B
    # node B -> 0.1 -> the treble-bottom / bass-top node
    bl, br = s.series_h("C", cb, ".1u", 92, tee + 6)
    s.wire(87, tee + 6, bl, tee + 6)
    s.wire(br, tee + 6, xT, tee + 6)
    s.wire(xT, tee + 1.62, xT, tee + 6)          # treble bottom lug -> bass node
    s.sym("POT", vrb, "250k-A bass", xT, tee + 6 + 3.81)
    s.wire(xT + 5.08, tee + 9.81, 110, tee + 9.81)   # bass wired as a rheostat
    s.wire(110, tee + 9.81, 110, tee + 6)
    s.wire(110, tee + 6, xT, tee + 6)
    s.junction(xT, tee + 6)
    # node B -> 0.047 -> the bass-bottom / middle-top node
    ml, mr = s.series_h("C", cm, ".047u", 92, tee + 13.62)
    s.wire(87, tee + 6, 87, tee + 13.62)
    s.wire(87, tee + 13.62, ml, tee + 13.62)
    s.wire(mr, tee + 13.62, xT, tee + 13.62)
    s.junction(xT, tee + 13.62)
    s.sym("POT", vrm, "10k-A mid", xT, tee + 13.62 + 3.81)
    s.wire(xT + 5.08, tee + 17.43, 106, tee + 17.43)  # middle wired as a rheostat
    s.wire(106, tee + 17.43, 106, tee + 13.62)
    s.wire(106, tee + 13.62, xT, tee + 13.62)
    s.gnd(xT, tee + 21.24)
    # treble wiper -> volume top
    s.wire(xT + 5.08, tee - 2.19, xv, tee - 2.19)
    s.wire(xv, tee - 2.19, xv, tee)
    s.sym("POT", vrv, "1M-A vol", xv, tee + 3.81)
    s.gnd(xv, tee + 7.62)
    # bright cap across the volume pot (top lug -> wiper), on the panel switch
    s.junction(xv, tee)
    s.wire(xv, tee, xv, tee - 9)
    cl, cr = s.series_h("C", cbr, "120p", xv + 8, tee - 9)
    s.wire(xv, tee - 9, cl, tee - 9)
    s.wire(cr, tee - 9, 134, tee - 9)
    s.wire(134, tee - 9, 134, tee + 3.81)
    s.wire(xv + 5.08, tee + 3.81, 134, tee + 3.81)
    s.junction(134, tee + 3.81)
    # volume wiper -> the channel's second-stage grid
    s.wire(134, tee + 3.81, 134, tee + 11.1)
    s.wire(134, tee + 11.1, x2 - 7.62, tee + 11.1)
    return 134


# ============================ TITLE ==================================
s.note('Heaters, pilot lamp and mains switching omitted here — see the netlist, the sources list and the board drawing. Rails: B+1 +460 (plates, OT centre tap) · B+2 +458 node [B] (screens, reverb transformer, tremolo) · B+3 +450 node [C] (PI plates) · B+4 +410 node [D] (all six preamp plate loads) · bias -52 V')
s.note('Chart notice: voltages read to ground with an electronic voltmeter, values ±20%. Resistors ½ W 10% and capacitors at least 400 V unless marked.')

# ============================ NORMAL CHANNEL (top row) ================
YN = 64
s.text("Normal channel", 12, 46, 1.8)
input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RGN1", "V1A", "12AX7 (7025)",
            "RLN1", "RKN1", "CKN1", "B+4")
teeN = YN - 7.62 - 3.48
tone_stack(teeN, "CTN", "RSN", "CBN", "CBN2", "VRTN", "VRBN", "VRMN", "VRVN",
           "CBRN", 140)

# normal second stage: 100k plate load off B+4, cathode on the SHARED [A] node
t1b = s.triode("V1B", "12AX7 (7025)", 140, YN)
s.plate_load("RLN2", "100k", t1b["p"], "B+4")
# V1B plate -> 0.047 coupler -> the normal channel's 220k mixing resistor
s.wire(140, teeN, 146, teeN)
s.junction(140, teeN)
cl, cr = s.series_h("C", "CCN2", ".047u", 150, teeN)
s.wire(146, teeN, cl, teeN)
s.wire(cr, teeN, 160, teeN)
ml, mr = s.series_h("R", "RMIXN", "220k", 170, teeN)
s.wire(160, teeN, ml, teeN)
s.wire(mr, teeN, 186, teeN)
s.glabel("MIXER", 186, teeN, 0)

# ============================ VIBRATO CHANNEL (second row) ============
YV = 122
s.text("Vibrato channel (reverb + tremolo)", 12, 104, 1.8)
input_stage(YV, "VIB 1", "VIB 2", "R1v", "R2v", "RGV1", "V2A", "12AX7 (7025)",
            "RLV1", "RKV1", "CKV1", "B+4")
teeV = YV - 7.62 - 3.48
tone_stack(teeV, "CTV", "RSV", "CBV", "CBV2", "VRTV", "VRBV", "VRMV", "VRVV",
           "CBRV", 140)


t2b = s.triode("V2B", "12AX7 (7025)", 140, YV)
s.plate_load("RLV2", "100k", t2b["p"], "B+4")
# V2B plate -> 0.02 coupler -> the dry node, which feeds both the reverb send
# and (through 3.3M || 10 pF) the mix driver's grid, in the block below
s.wire(140, teeV, 146, teeV)
s.junction(140, teeV)
cl, cr = s.series_h("C", "CCV2", ".02u", 150, teeV)
s.wire(146, teeV, cl, teeV)
s.wire(cr, teeV, 158, teeV)
s.wire(158, teeV, 158, 150)
s.glabel("DRY", 158, 150, 270)

# ---- the SHARED second-stage cathode network, the drawing's boxed node [A] ----
s.text("[A] — the two channels' second stages share ONE 820 Ω / 25 µF cathode network",
       152, 142, 1.4)
s.shunt_rc("RKA", "820", "CKA", "25u", 140, 131)
s.wire(140, YV + 7.62, 140, 131)                    # V2B cathode straight down
s.wire(140, YN + 7.62, 140, 74)                     # V1B cathode, around the right
s.wire(140, 74, 166, 74)
s.wire(166, 74, 166, 131)
s.wire(166, 131, 147.62, 131)
s.junction(147.62, 131)

# ============================ REVERB SEND / DRIVER ====================
YR = 196
s.text("Reverb driver (12AT7, both sections paralleled) · recovery · reverb-and-dry mix", 12, 172, 1.8)
# dry node -> 500 pF -> the paralleled driver grids
s.glabel("DRY", 176, 162, 180)
s.wire(176, 162, 160, 162)
cl, cr = s.series_h("C", "CRS", "500p", 148, 162)
s.wire(160, 162, cr, 162)
s.wire(cl, 162, 60, 162)
s.wire(60, 162, 60, YR)
s.junction(60, YR)
t3a = s.triode("V3A", "12AT7", 72, YR)
t3b = s.triode("V3B", "12AT7", 72, YR + 22)
s.wire(60, YR, t3a["g"][0], YR)
s.wire(60, YR, 60, YR + 22)                 # the paralleled grid bus
s.wire(60, YR + 22, t3b["g"][0], YR + 22)
# The 1 MΩ leak hangs off the FOOT of the grid bus. Drawn on the bus itself the
# bus ran straight through the resistor body and out its far pin, shorting the
# leak out and tying both driver grids to ground.
s.junction(60, YR + 22)
s.wire(60, YR + 22, 52, YR + 22)
s.sym("R", "RGRD", "1M", 52, YR + 25.81, lx=-9.4)
s.gnd(52, YR + 29.62)
# plates tied and taken to the reverb transformer
s.wire(72, YR - 7.62, 72, YR - 10)
s.wire(72, YR + 22 - 7.62, 72, YR + 12)
s.wire(72, YR - 10, 82, YR - 10)
s.wire(72, YR + 12, 82, YR + 12)
s.wire(82, YR - 10, 82, YR + 12)
s.junction(82, YR - 10)
# shared cathode 2.2k || 25 µF, tied below V3B
cy = YR + 33
s.wire(72, YR + 7.62, 64, YR + 7.62)
s.wire(64, YR + 7.62, 64, cy)
s.wire(64, cy, 72, cy)
s.wire(72, YR + 22 + 7.62, 72, cy)
s.junction(72, cy)
s.shunt_rc("RKRD", "2.2k", "CKRD", "25u", 72, cy)
# reverb transformer T4 (driver -> tank)
s.sym("OT_SE", "T4", "125A20B", 96, YR - 4)
s.wire(82, YR - 10, 87.11, YR - 10)
s.wire(87.11, YR - 10, 87.11, YR - 6.54)
s.wire(87.11, YR - 1.46, 87.11, YR + 2)
s.glabel("B+2", 87.11, YR + 2, 90)
s.wire(104.89, YR - 6.54, 112, YR - 6.54)
s.glabel("REVERB TANK", 112, YR - 6.54, 0)
s.wire(104.89, YR - 1.46, 112, YR - 1.46)
s.gnd(112, YR - 1.46)

# ---- reverb recovery (V4B): the tank return lands straight on the grid, and
# RGR1 220k is that grid's leak to ground, as the C-FD sheet draws it. Until
# 2026-09-10 the 220k was drawn in series from the tank return, and an sch_map
# anchor folded the return lead into ground to match the netlist.
s.glabel("TANK RET", 150, YR - 6, 180)
s.wire(150, YR - 6, 172, YR - 6)
s.junction(158, YR - 6)
s.sym("R", "RGR1", "220k", 158, YR - 6 + 3.81)
s.gnd(158, YR - 6 + 7.62)
s.wire(172, YR - 6, 172, YR)
t4b = s.triode("V4B", "12AX7 (7025)", 182, YR)
s.wire(172, YR, t4b["g"][0], YR)
s.plate_load("RLR1", "100k", t4b["p"], "B+4")
# recovery plate -> 0.003 -> the 100k-L reverb control -> 470k mix resistor
teeR = YR - 7.62 - 3.48
s.wire(182, teeR, 190, teeR)
s.junction(182, teeR)
cl, cr = s.series_h("C", "CCR1", ".003u", 196, teeR)
s.wire(190, teeR, cl, teeR)
s.wire(cr, teeR, 206, teeR)
s.sym("POT", "VRREV", "100k-L rev", 206, teeR + 3.81)
s.gnd(206, teeR + 7.62)
s.wire(211.08, teeR + 3.81, 216, teeR + 3.81)
ml, mr = s.series_h("R", "RMR", "470k", 222, teeR + 3.81)
s.wire(216, teeR + 3.81, ml, teeR + 3.81)
s.wire(mr, teeR + 3.81, 232, teeR + 3.81)
# the reverb return lands on the mix driver's GRID, beside its 220k leak
s.wire(232, teeR + 3.81, 232, YR + 22)

# ---- the dry node, the mix driver's grid (V4A), and its output ---------------
# The 3.3M || 10 pF runs IN SERIES from the dry node to the grid, and the 470k
# reverb return and the 220k leak land on the GRID side of it. Until 2026-09-10
# this sheet hung both on the dry side and put the photocell on the grid.
s.text("Dry node → 3.3 MΩ (10 pF across it) → mix-driver grid, where the 470 kΩ reverb "
       "return and the 220 kΩ grid leak land", 196, 236, 1.4)
YM = YR + 22
s.glabel("DRY", 196, YM - 16, 90)
s.wire(196, YM - 16, 196, YM)
s.junction(196, YM - 8)
gl, gr = s.series_h("R", "RGD1", "3.3M", 204, YM)
s.wire(196, YM, gl, YM)
s.wire(gr, YM, 214, YM)
cl, cr = s.series_h("C", "CBD1", "10p", 204, YM - 8)
s.wire(196, YM - 8, cl, YM - 8)
s.wire(cr, YM - 8, 214, YM - 8)
s.wire(214, YM - 8, 214, YM)
s.junction(214, YM)
s.wire(214, YM, 232, YM)
s.junction(224, YM)
s.sym("R", "RTOG4", "220k", 224, YM + 3.81, lx=-9.4)   # the grid leak
s.gnd(224, YM + 7.62)
s.junction(232, YM)                                     # the reverb return, from above
t4a = s.triode("V4A", "12AX7 (7025)", 244, YM)
s.wire(232, YM, t4a["g"][0], YM)
s.plate_load("RLD1", "100k", t4a["p"], "B+4")
# mix-driver plate -> 0.1 -> the vibrato channel's 220k mixing resistor
teeM = YM - 7.62 - 3.48
s.wire(244, teeM, 252, teeM)
s.junction(244, teeM)
cl, cr = s.series_h("C", "CCD1", ".1u", 258, teeM)
s.wire(252, teeM, cl, teeM)
s.wire(cr, teeM, 268, teeM)
ml, mr = s.series_h("R", "RMIXV", "220k", 276, teeM)
s.wire(268, teeM, ml, teeM)
# The Intensity control hangs from THIS node, between the 0.1 coupler and the
# 220k mixing resistor, and the photocell shunts its wiper to ground: the
# tremolo works on the mix driver's output, not on its grid.
s.junction(266, teeM)
s.wire(266, teeM, 266, teeM + 6)
s.sym("POT", "VRINT", "50k-RA int", 266, teeM + 9.81, lx=6.0, ly=6.0)
s.gnd(266, teeM + 13.62)
s.wire(271.08, teeM + 9.81, 276, teeM + 9.81)
s.glabel("PHOTOCELL", 276, teeM + 9.81, 0)
s.wire(mr, teeM, 292, teeM)
s.wire(292, teeM, 292, 145)
s.glabel("MIXER", 292, 145, 90)      # clear of CPIB's value lettering below

# ---- the SHARED recovery / mix-driver cathode network, boxed node [E] -------
s.text("[E] — the reverb recovery and the mix driver share ONE 820 Ω / 25 µF cathode network",
       248, 258, 1.4)
s.shunt_rc("RKE", "820", "CKE", "25u", 244, 250)
s.wire(244, YM + 7.62, 244, 250)                  # V4A cathode straight down
s.wire(182, YR + 7.62, 182, 244)                  # V4B cathode, along the gap
s.wire(182, 244, 260, 244)
s.wire(260, 244, 260, 250)
s.wire(260, 250, 251.62, 250)
s.junction(251.62, 250)

# ============================ TREMOLO OSCILLATOR (excluded) ==========
YT = 306
s.caption('Tremolo — oscillator V5A and neon-lamp driver V5B; neither half has a static DC operating point, so both are excluded from the netlist (see the circuit story)', 12, 252, 1.5)
XA, XB = 70, 136
# The C-FD layout page (2157 x 1397) leads the oscillator's plate (+300 V) to
# pin 1 and its +2.0 V cathode to pin 3, and the lamp driver's +380 V plate to
# pin 6: V5A is datasheet unit 2, V5B unit 1.
t5a = s.triode("V5A", "12AX7", XA, YT, unit=2)
t5b = s.triode("V5B", "12AX7", XB, YT, unit=1)
s.plate_load("RTO1", "220k", t5a["p"], "B+2")
s.sym("R", "RKTO1", "2.7k", XA, YT + 11.43)
s.gnd(XA, YT + 15.24)
s.sym("C", "CKTO1", "25u", XA + 8, YT + 11.43)
s.wire(XA, YT + 7.62, XA + 8, YT + 7.62)
s.wire(XA, YT + 15.24, XA + 8, YT + 15.24)
# The phase-shift ladder, as the C-FD sheet draws it (6138x4384):
#   plate -.02- S [Speed 3M-RA + 100k to ground] -.01- N1 -.01- grid,
#   with 1M from N1 and 1M from the grid meeting at J (the footswitch
#   junction), and J -2.2M- the bias supply's filter node. The lamp driver's
#   grid is N1. Until 2026-09-10 this sheet drove the lamp driver from S,
#   landed N1's 1M on the grid, and returned the 2.2M to ground.
tee5 = YT - 7.62 - 3.48
YN1 = YT - 32                                   # the N1 row
s.junction(XA, tee5)
cl, cr = s.series_h("C", "CTO3", ".02u", XA + 10, tee5)
s.wire(XA, tee5, cl, tee5)
s.wire(cr, tee5, XA + 18, tee5)                 # S
s.junction(XA + 18, tee5)
# Speed control: a 3 MΩ-RA pot used as a RHEOSTAT, wiper strapped back to its
# hot lug (the same idiom the AA1164's speed control is drawn with). Without
# the strap the wiper is a floating third terminal and the part is a fixed 3 M.
s.sym("POT", "VRSPD", "3M-RA speed", XA + 26, tee5, rot=90, lx=-4.6, ly=6.4)
s.wire(XA + 18, tee5, XA + 22.19, tee5)
s.wire(XA + 26, tee5 - 5.08, XA + 22.19, tee5 - 5.08)
s.wire(XA + 22.19, tee5 - 5.08, XA + 22.19, tee5)
s.junction(XA + 22.19, tee5)
sl, sr = s.series_h("R", "RTOSP", "100k", XA + 36, tee5)
s.wire(XA + 29.81, tee5, sl, tee5)
s.wire(sr, tee5, XA + 42, tee5)
s.gnd(XA + 42, tee5, rot=0)
# S -.01- N1, along the row above the plate load's rail flag
s.wire(XA + 18, tee5, XA + 18, YN1)
cl, cr = s.series_h("C", "CTO1", ".01u", XA - 10, YN1)
s.wire(XA + 18, YN1, cr, YN1)
s.wire(cl, YN1, XA - 20, YN1)                   # N1
s.junction(XA - 20, YN1)
# N1 -1M- J
sl, sr = s.series_h("R", "RTOG1", "1M", XA - 32, YN1)
s.wire(XA - 20, YN1, sr, YN1)
s.wire(sl, YN1, XA - 44, YN1)
# N1 -.01- the grid node; the grid node -1M- J
s.sym("C", "CTO2", ".01u", XA - 20, YT - 16)
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
s.note('The vibrato footswitch grounds the junction of the two 1 MΩ ladder resistors and the 2.2 MΩ, and stops the oscillator')
# N1 -> the lamp driver's grid, over the top of the ladder
s.wire(XA - 20, YN1, XA - 20, YN1 - 12)
s.wire(XA - 20, YN1 - 12, XB - 14, YN1 - 12)
s.wire(XB - 14, YN1 - 12, XB - 14, YT)
s.wire(XB - 14, YT, t5b["g"][0], YT)
# lamp driver: 100k cathode, 10M plate bleeder, the neon lamp in series with 100k
s.sym("R", "RKTO2", "100k", XB, YT + 11.43)
s.gnd(XB, YT + 15.24)
s.sym("C", "CKTO2", "25u", XB + 8, YT + 11.43)
s.wire(XB, YT + 7.62, XB + 8, YT + 7.62)
s.wire(XB, YT + 15.24, XB + 8, YT + 15.24)
s.plate_load("RTO10", "10M", t5b["p"], "B+2")
op = s.opto("OPTO", "neon + photocell", XB + 24, tee5 + 2.54, ly=-10.0)
s.junction(XB, tee5)
s.wire(XB, tee5, op["l1"][0], op["l1"][1])
s.wire(op["l2"][0], op["l2"][1], op["l2"][0], YT)
s.wire(op["l2"][0], YT, XB + 24, YT)
s.sym("R", "RLAMP", "100k", XB + 24, YT + 3.81)
s.wire(XB + 24, YT + 7.62, XB + 24, YT + 10)
s.glabel("B+2", XB + 24, YT + 10, 270)
# the photocell shunts the Intensity control's wiper (at the mix driver's
# output, above) to ground
s.wire(op["p1"][0], op["p1"][1], op["p1"][0] + 6, op["p1"][1])
s.glabel("PHOTOCELL", op["p1"][0] + 6, op["p1"][1], 0)
s.wire(op["p2"][0], op["p2"][1], op["p2"][0] + 4, op["p2"][1])
s.gnd(op["p2"][0] + 4, op["p2"][1])

# ============================ PHASE INVERTER (LTP) ===================
XPI = 336
YPH = 120   # hot
YPB = 156   # cold
s.text("Long-tailed-pair phase inverter (12AT7)", 306, 100, 1.8)
s.glabel("MIXER", 300, YPH, 180)
cl, cr = s.series_h("C", "CPIA", ".001u", 312, YPH)
s.wire(300, YPH, cl, YPH)
s.wire(cr, YPH, XPI - 7.62, YPH)
t6a = s.triode("V6A", "12AT7", XPI, YPH)
t6b = s.triode("V6B", "12AT7", XPI, YPB)
s.plate_load("RLPA", "82k 5%", t6a["p"], "B+3")
s.plate_load("RLPB", "100k 5%", t6b["p"], "B+3")
# Joined cathodes -> 470 -> tail junction -> 22k -> the feedback node.
#
# The cold half's tail lead is taken from V6B's CATHODE (YPB + 7.62) and routed
# under the bottle to the KPI lane at x = 324. Until 2026-09-02 it was drawn
# from YPB - 7.62, which on an upright cx:TRIODE is the PLATE pin: RTAIL sat on
# V6B's plate node beside V6A's cathode, and V6B's cathode floated. The lane sits
# clear of RTAIL's body on one side and of V6B's bottle and grid lead on the
# other; it crosses the cold grid's two horizontals, which carry no connection.
JY = 138
XK = 324
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, XK, YPH + 10)
s.wire(XPI, YPB + 7.62, XPI, YPB + 14)
s.wire(XPI, YPB + 14, XK, YPB + 14)
s.wire(XK, YPH + 10, XK, YPB + 14)
s.junction(XK, JY)
tl, tr = s.series_h("R", "RTAIL", "470", 318, JY)
s.wire(XK, JY, tr, JY)
s.junction(306, JY)
s.junction(310, JY)
ml, mr = s.series_h("R", "RT22", "22k", 292, JY)
s.wire(mr, JY, tl, JY)                           # the tail-junction rail
s.wire(ml, JY, 280, JY)                          # the negative-feedback node
s.junction(280, JY)
s.wire(280, JY, 274, JY)
s.sym("R", "RFB1", "100", 274, JY + 3.81, lx=-8.6)
s.gnd(274, JY + 7.62)
s.glabel("SPKR", 250, JY - 10, 180)
nl, nr = s.series_h("R", "RFB2", "820", 266, JY - 10)
s.wire(250, JY - 10, nl, JY - 10)
s.wire(nr, JY - 10, 280, JY - 10)
s.wire(280, JY - 10, 280, JY)
# grid leaks returned to the tail junction
s.sym("R", "RGPA", "1M", 310, JY - 8, lx=-9.4)
s.wire(310, JY - 4.19, 310, JY)
s.wire(310, JY - 11.81, 310, YPH - 2)
s.wire(310, YPH - 2, 328.38, YPH - 2)
s.wire(328.38, YPH - 2, 328.38, YPH)
s.junction(328.38, YPH)
s.sym("R", "RGPB", "1M", 306, JY + 8, lx=-9.4)
s.wire(306, JY + 4.19, 306, JY)
s.wire(306, JY + 11.81, 306, YPB + 2)
s.wire(306, YPB + 2, 328.38, YPB + 2)
s.wire(328.38, YPB + 2, 328.38, YPB)
s.junction(328.38, YPB)
# 0.1/200 from the cold grid to the feedback node. Its riser is kept OFF the
# RFB1 column: drawn there it ran through the 100 Ohm's body and out its far
# pin, shorting the resistor and grounding the whole feedback node.
cl, cr = s.series_h("C", "CPIB", ".1u 200V", 296, YPB)
s.wire(328.38, YPB, cr, YPB)
s.wire(cl, YPB, 280, YPB)
s.wire(280, YPB, 280, JY)

# ============================ OUTPUT: four 6L6GC =====================
s.text("Output quartet — 6L6GC, fixed bias at -52 V through two 220 kΩ leaks, "
       "one per phase and one 1.5 kΩ stopper per grid", 372, 46, 1.6)
XO = 408
# hot phase: PI hot plate -> 0.1 -> the V7/V8 grid line
teeA = YPH - 7.62 - 3.48
s.wire(XPI, teeA, XPI + 10, teeA)
s.junction(XPI, teeA)
al, ar = s.series_h("C", "C1", ".1u 400V", XPI + 18, teeA)
s.wire(XPI + 10, teeA, al, teeA)
s.wire(ar, teeA, 366, teeA)
s.wire(366, teeA, 366, 62)
s.junction(366, 62)
s.sym("R", "RGL1", "220k 5%", 366, 62 - 3.81, label_rot=0, lx=2.2, ly=-3.2)
s.wire(366, 62 - 7.62, 366, 54)
s.glabel("-52V", 366, 54, 90)
# cold phase
teeB = YPB - 7.62 - 3.48
s.wire(XPI, teeB, XPI + 10, teeB)
s.junction(XPI, teeB)
kl, kr = s.series_h("C", "C2", ".1u 400V", XPI + 18, teeB)
s.wire(XPI + 10, teeB, kl, teeB)
s.wire(kr, teeB, 372, teeB)
s.wire(372, teeB, 372, 208)
s.junction(372, 208)
s.sym("R", "RGL2", "220k 5%", 372, 208 + 3.81)
s.wire(372, 208 + 7.62, 372, 220)
s.glabel("-52V", 372, 220, 270)

VOUT = {}
for gy, y, vref, stop, screen in [(62, 76, "V7", "RST1", "RSC1"),
                                  (62, 106, "V8", "RST2", "RSC2"),
                                  (208, 170, "V9", "RST3", "RSC3"),
                                  (208, 200, "V10", "RST4", "RSC4")]:
    gx = 366 if gy == 62 else 372
    s.wire(gx, gy, 380, gy)
    s.junction(gx, gy)
    s.wire(380, gy, 380, y)
    sl, sr = s.series_h("R", stop, "1.5k", 390, y)
    s.wire(380, y, sl, y)
    p = s.pentode(vref, "6L6GC", XO, y)
    VOUT[vref] = p
    s.wire(sr, y, XO - 7.62, y)
    # the screen stub must REACH the stopper's own pin, not stop 2 mm short of it
    s2l, s2r = s.series_h("R", screen, "470 1W", p["g2"][0] + 7.81, p["g2"][1])
    s.wire(p["g2"][0], p["g2"][1], s2l, p["g2"][1])
    s.wire(s2r, p["g2"][1], p["g2"][0] + 15, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 15, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# the two grid lines run down their own columns to the lower valve of each pair
s.wire(380, 76, 380, 106)
s.junction(380, 76)
s.wire(380, 170, 380, 200)
s.junction(380, 170)

# output transformer T3 (parallel push-pull primary, 4 Ω secondary + feedback tap)
s.sym("OT_PP", "T3", "125A29A", 470, 138)
s.wire(XO, VOUT["V7"]["p"][1], XO, 60)
s.wire(XO, 60, 461.11, 60)
s.wire(461.11, 60, 461.11, 132.92)              # V7/V8 plates -> PRI_A
s.wire(XO, VOUT["V8"]["p"][1], XO, 94)
s.wire(XO, 94, 452, 94)
s.wire(452, 94, 452, 60)
s.junction(452, 60)
# V9/V10 plates -> PRI_B. Each lead now rises clear of its own bottle. The old
# run dropped from y=192 to y=232 straight down the valve column, THROUGH V10's
# envelope and out its grounded cathode pin: V9's plate and the transformer's
# cold primary sat on ground, and V10's plate floated 0.64 mm from its lead.
s.wire(XO, VOUT["V9"]["p"][1], XO, 158)
s.wire(XO, 158, 461.11, 158)
s.wire(461.11, 158, 461.11, 143.08)
s.wire(XO, VOUT["V10"]["p"][1], XO, 186)
s.wire(XO, 186, 452, 186)
s.wire(452, 186, 452, 158)
s.junction(452, 158)
s.wire(461.11, 138, 456, 138)
s.wire(456, 138, 456, 128)
s.glabel("B+1", 456, 128, 90)
s.wire(478.89, 135.46, 486, 135.46)
s.glabel("SPKR", 486, 135.46, 0)
s.wire(478.89, 140.54, 486, 140.54)
s.glabel("GND", 486, 140.54, 0)
s.text("Speaker jack and extension jack: two 12-inch speakers on the 4 Ω secondary; "
       "the 820 Ω feedback resistor is tapped from the same winding", 424, 250, 1.4)

# ============================ POWER SUPPLY (bottom) ==================
YPW = 350
s.text("Power supply — TR1 125P34A 340-0-340 V, silicon full-wave rectification (three series "
       "diodes per leg), TR2 125C1A choke. The standby switch sits between the rectifier and "
       "the reservoir and is not drawn.", 246, 296, 1.5)
pt = s.pt("T1", "125P34A · 340-0-340 V", 268, YPW, lx=-6.35, ly=-13.5)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 6, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 6, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 6, pt["pri2"][1])
s.glabel("MAINS N", pt["pri2"][0] - 6, pt["pri2"][1], 180)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.text("TR1 also carries the 6.3 V heater winding (centre tap to internal ground) and the "
       "48 V bias tap that feeds the grid supply at the right.", 246, 380, 1.3)
# two three-diode strings
s.sym("DIODE_SS", "DHTA", "Si ×3", 292, YPW - 5.08, lx=-3.4, ly=-5.4)
s.wire(pt["ht_a"][0], pt["ht_a"][1], 286.92, YPW - 5.08)
s.sym("DIODE_SS", "DHTB", "Si ×3", 292, YPW + 5.08, lx=-3.4, ly=3.0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], 286.92, YPW + 5.08)
s.wire(297.08, YPW - 5.08, 306, YPW - 5.08)
s.wire(297.08, YPW + 5.08, 306, YPW + 5.08)
s.wire(306, YPW - 5.08, 306, YPW + 5.08)
s.wire(306, YPW, 314, YPW)
s.junction(306, YPW)
# series reservoir pair with its 220k-1W balancing resistors
s.junction(314, YPW)
s.sym("C", "C10", "70u 350V", 314, YPW + 3.81)
s.sym("R", "RBAL1", "220k 1W", 326, YPW + 3.81)
s.wire(314, YPW, 326, YPW)
s.wire(314, YPW + 7.62, 326, YPW + 7.62)
s.junction(314, YPW + 7.62)
s.sym("C", "C11", "70u 350V", 314, YPW + 11.43)
s.sym("R", "RBAL2", "220k 1W", 326, YPW + 11.43)
s.wire(314, YPW + 7.62, 326, YPW + 7.62)
s.wire(314, YPW + 15.24, 326, YPW + 15.24)
s.gnd(314, YPW + 15.24)
s.wire(314, YPW, 336, YPW)
s.junction(330, YPW)
s.glabel("B+1", 330, YPW - 4, 90)
s.wire(330, YPW - 4, 330, YPW)
# choke -> node [B]
s.sym("CHOKE", "T2", "125C1A", 343.62, YPW, lx=-5.0, ly=-7.4)
s.wire(351.24, YPW, 362, YPW)
s.junction(356, YPW)
s.glabel("B+2", 356, YPW - 4, 90)
s.wire(356, YPW - 4, 356, YPW)
s.junction(360, YPW)
s.sym("C", "C12", "20u 525V", 360, YPW + 3.81)
s.gnd(360, YPW + 7.62)
# 1k-1W -> node [C]
l, r = s.series_h("R", "RD1", "1k 1W", 368, YPW)
s.wire(362, YPW, l, YPW)
s.wire(r, YPW, 384, YPW)
s.junction(378, YPW)
s.glabel("B+3", 378, YPW - 4, 90)
s.wire(378, YPW - 4, 378, YPW)
s.junction(382, YPW)
s.sym("C", "C13", "20u 525V", 382, YPW + 3.81)
s.gnd(382, YPW + 7.62)
# 4.7k-1W -> node [D]
l, r = s.series_h("R", "RD2", "4.7k 1W", 390, YPW)
s.wire(384, YPW, l, YPW)
s.wire(r, YPW, 406, YPW)
s.junction(400, YPW)
s.glabel("B+4", 400, YPW - 4, 90)
s.wire(400, YPW - 4, 400, YPW)
s.sym("C", "C14", "20u 525V", 406, YPW + 3.81)
s.gnd(406, YPW + 7.62)

# ============================ BIAS SUPPLY ===========================
YB = YPW
s.note('Bias supply — the 48 V tap → 470 Ω · 1 W → rectifier → 25 µF · 50 V → the 10 kΩ balance control over a 27 kΩ leg; its wiper sets the −52 V grid line')
s.glabel("BIAS TAP", 436, YB, 180)
l, r = s.series_h("R", "RBIAS", "470 1W", 452, YB)
s.wire(436, YB, l, YB)
s.wire(r, YB, 462, YB)
s.sym("DIODE_SS", "DBIAS", "Si", 467, YB, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(462, YB, 461.92, YB)
s.wire(472.08, YB, 480, YB)
s.junction(480, YB)
s.sym("C", "CB1", "25u 50V", 480, YB + 3.81)
s.gnd(480, YB + 7.62)
s.wire(480, YB, 490.19, YB)
# the filter node also takes the tremolo ladder's 2.2M (RTOG3)
s.junction(485, YB)
s.wire(485, YB, 485, YB - 6)
s.glabel("BIAS FILTER", 485, YB - 6, 90)
s.sym("POT", "VRBAL", "10k-L bal", 494, YB, rot=90, lx=-3.6, ly=6.4)
s.wire(497.81, YB, 506, YB)
s.sym("R", "RB2", "27k", 506, YB + 3.81)
s.gnd(506, YB + 7.62)
# The balance control's WIPER is the -52 V grid line (layout.yaml net_map:
# VRBAL.lug2 -> NBIAS). It is at y - 5.08 on a pot rotated 90 deg; the lead
# used to leave from y + 5.08, a point on no pin at all.
s.wire(494, YB - 5.08, 494, YB - 12)
s.wire(494, YB - 12, 514, YB - 12)
s.glabel("-52V", 514, YB - 12, 0)

# ============================ DEATH CAP =============================
s.note('Period ground-switch cap (not in modern builds)')
s.glabel("MAINS", 246, YB + 52, 180)
s.wire(246, YB + 52, 252.19, YB + 52)
s.sym("C", "CDEATH", ".047u 600V", 256, YB + 52, rot=90, lx=-3.6, ly=-6.4)
s.wire(259.81, YB + 52, 266, YB + 52)
s.gnd(266, YB + 52)

s.write(OUT)
print(f"wrote {OUT}")
