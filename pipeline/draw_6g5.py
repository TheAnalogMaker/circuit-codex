#!/usr/bin/env python3
"""Generate amps/6g5/schematic.kicad_sch from the stage-template library.

Values per the published Fender "Pro-Amp" Model 6G5 drawing (A-FJ) — see
amps/6g5/meta.yaml and notes.md. Channel 1 runs across the top and channel 2
below it, each with two inputs, a first stage on V1, a Bass/Treble network
and Volume, and a second stage on V2. The two first stages share one cathode
pair and the two second stages another — the factory sheet letters them C and
D; they are the K1 and K2 labels here. Channel 1's output feeds the harmonic
vibrato: a low-pass and a high-pass branch into the two sections of V4, whose
plates recombine at VMIX, where channel 2 joins them. The oscillator V3A and
its phase splitter V3B run along the bottom left; the phase inverter V5, the
6L6GC pair and the output transformer on the right; the power supply and its
dropper chain along the bottom right.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
BP1 +456 (6L6GC plates, and the screens and every dropper at the drawing's
+458 V post-choke node — choke and OT resistance omitted), BC +430 (phase
inverter, through 4700 1W), BA +260 (both channels, through 56k 1W from BC),
BV +350 (vibrato pair, through 56k 1W from BP1), BL +275 (oscillator and
splitter, through a further 56k 1W). -55 V is the fixed-bias line, an ideal
source in the DC model. Heaters and the standby switch are omitted here (see
the board drawing).

Every dual-triode section states the datasheet unit the layout page's socket
voltages put it on: V1A pins 6-8 and V1B 1-3; V2A 1-3 (+160 V at pin 1) and
V2B 6-8 (+120 V at pin 6); V3A 1-3 (+130 V) and V3B 6-8 (+180 V); V4A 1-3 and
V4B 6-8 (each band's grid traced to its pin); V5A 1-3 (+315 V) and V5B 6-8
(+310 V).

Until 2026-09-10 this sheet drew a different amplifier: one 7025 per channel,
a "driver" stage that was one half of the vibrato pair, and an optocoupler
the drawing does not have, with the oscillator laid across the mains corner.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g5" / "schematic.kicad_sch"
s = Sch()

GB = 40    # input grid-bus x
VX = 52    # first-stage triode x
XB = 138   # second-stage triode x


def inputs(y, tag, r_in2, r_in1, rleak):
    """Input 2 reaches the grid through its 68k; input 1 through its own 68k,
    with the channel's 1M leak to ground at the input-1 end, where A-FJ draws
    it (the board mounts it on the jack)."""
    s.glabel(f"{tag} IN 2", 8, y + 4, 180)
    l, r = s.series_h("R", r_in2, "68k", 26, y + 4)
    s.wire(8, y + 4, l, y + 4)
    s.wire(r, y + 4, GB, y + 4)
    s.glabel(f"{tag} IN 1", 8, y - 4, 180)
    s.wire(8, y - 4, 16, y - 4)
    s.junction(16, y - 4)
    s.sym("R", rleak, "1M", 16, y - 4 - 3.81, lx=-8.6, ly=0.0)
    s.gnd(16, y - 4 - 7.62, 90)
    l, r = s.series_h("R", r_in1, "68k", 26, y - 4)
    s.wire(16, y - 4, l, y - 4)
    s.wire(r, y - 4, GB, y - 4)
    s.wire(GB, y - 4, GB, y + 4)
    s.junction(GB, y)


def tone_stack(y, cc, rs, ct, vrt, vrb, cf, rf, vrv, cbr):
    """The first stage's plate tee -> coupler -> Bass/Treble network ->
    Volume. Returns the Volume wiper point.

    The network as the A-FJ sheet draws it: the plate feeds the stack through
    CC (.05) to the stack input T; from T, CT (250MM) to the Treble pot's hot
    lug and RS (100k) down to node A, the slope foot, which also carries the
    Treble pot's cold lug and the Bass pot's hot lug. The Bass control is a
    DIVIDER from A to ground: CF (.01) bridges its upper section (A to the
    wiper, node B) and RF (10k) bridges its lower (B to ground). Treble wiper
    -> Volume hot lug. Channel 1 alone carries CBR (47MM) from that lug to
    the Volume wiper; neither page draws one on channel 2."""
    tee = y - 7.62 - 3.48
    s.junction(VX, tee)
    s.wire(VX, tee, 56.19, tee)
    s.series_h("C", cc, ".05u", 60, tee)      # coupler: plate tee -> T
    s.wire(63.81, tee, 70, tee)               # node T (stack input)
    ty = tee - 12                             # treble pot centre y
    tl, tr = s.series_h("C", ct, "250p", 76, ty - 3.81)
    s.wire(70, tee, 70, ty - 3.81)
    s.wire(70, ty - 3.81, tl, ty - 3.81)
    s.wire(tr, ty - 3.81, 88, ty - 3.81)      # -> treble pot hot lug (pin 1)
    s.sym("POT", vrt, "250k-L", 88, ty, lx=2.4, ly=-9.2)
    ay = tee + 8                              # node A (slope foot) y
    sl, sr = s.series_h("R", rs, "100k", 75, ay)
    s.wire(70, tee, 70, ay)
    s.junction(70, tee)
    s.wire(70, ay, sl, ay)
    s.wire(sr, ay, 79, ay)
    s.junction(79, ay)                        # node A
    s.wire(79, ay, 88, ay)
    s.wire(88, ty + 3.81, 88, ay)             # treble cold lug (pin 3) -> node A
    s.junction(88, ay)
    # Bass pot, mirrored so its wiper faces the capacitor and the foot: pin 1
    # (hot) on node A, pin 3 (foot) grounded, wiper = node B.
    bay = ay + 7.62
    s.sym("POT", vrb, "250k-A", 88, bay, mirror="y", lx=2.4, ly=-1.5)
    s.wire(88, ay, 88, bay - 3.81)
    s.gnd(88, bay + 3.81)
    s.sym("C", cf, ".01u", 79, ay + 3.81, lx=-8.6, ly=0.0)   # CF: node A -> node B
    s.wire(79, ay + 7.62, 82.92, ay + 7.62)   # node B -> bass WIPER (mirrored, left)
    s.junction(79, ay + 7.62)
    s.sym("R", rf, "10k", 79, ay + 11.43, lx=-9.4)   # RF: node B -> ground
    s.gnd(79, ay + 15.24)
    # treble wiper (pin 2) = stack output -> Volume pot hot lug (pin 1)
    s.wire(93.08, ty, 100.5, ty)
    s.sym("POT", vrv, "500k-L", 100.5, ty + 3.81, lx=-11.6, ly=-10.4)
    s.gnd(100.5, ty + 7.62)
    if cbr:
        # bright cap: Volume hot lug -> wiper, drawn over the pot
        s.junction(100.5, ty)
        s.wire(100.5, ty, 100.5, ty - 6)
        bl, br = s.series_h("C", cbr, "47p", 106, ty - 6)
        s.wire(100.5, ty - 6, bl, ty - 6)
        s.wire(br, ty - 6, 112, ty - 6)
        s.wire(112, ty - 6, 112, ty + 3.81)
        s.wire(105.58, ty + 3.81, 112, ty + 3.81)
        s.junction(105.58, ty + 3.81)
        s.wire(112, ty + 3.81, 126, ty + 3.81)
    else:
        s.wire(105.58, ty + 3.81, 126, ty + 3.81)
    return 126, ty + 3.81


def cathode_label(x, y, name):
    """A section whose cathode joins its bottle-mate's: a short stub down to
    the shared-cathode label (the factory sheet's boxed C and D)."""
    s.wire(x, y + 7.62, x, y + 11)
    s.glabel(name, x, y + 11, 270)


def cathode_pair(x, y, rref, cref, name, bypass="25u 25V", rval="820"):
    """The shared cathode pair itself, under one of its two sections, with the
    label its bottle-mate joins by."""
    s.wire(x, y + 7.62, x, y + 9)
    s.shunt_rc(rref, rval, cref, bypass, x, y + 9)
    s.wire(x, y + 9, x - 6, y + 9)
    s.junction(x, y + 9)
    s.glabel(name, x - 6, y + 9, 180)


# ============================ TITLE ==================================
s.note('Rails: BP1 +456 (6L6GC plates; the screens and every dropper hang at the drawing\'s +458 V post-choke node, choke and transformer resistance omitted) · BC +430 (phase inverter) · BA +260 (both channels) · BV +350 (vibrato pair) · BL +275 (oscillator and splitter) · bias -55 V')
s.note('K1 and K2 are the two shared cathode pairs the factory sheet letters C and D: both first stages (V1) sit on one 820 Ω / 25 µF, both second stages (V2) on another.')
s.note('The vibrato oscillator V3A is drawn in full and excluded from the DC model — a running phase-shift oscillator has no static operating point. The splitter V3B and the vibrato pair V4 are modelled.')
s.note('Heaters, the standby switch and the second of the two 20 µF reservoir cans are omitted here — see the sources list and the board drawing.')

# ============================ CHANNEL 1 (top) =========================
Y1 = 62
s.caption('Channel 1 — V1A, tone network and Volume, V2A (into the vibrato)', 12, 20, 1.6)
inputs(Y1, "CH1", "R1N", "R1H", "RG1A")
t1a = s.triode("V1A", "7025", VX, Y1, unit=1)
s.wire(GB, Y1, t1a["g"][0], Y1)
s.plate_load("RL1A", "100k", t1a["p"], "BA")
cathode_pair(VX, Y1, "RK1", "CK1", "K1")
wx, wy = tone_stack(Y1, "CC1T", "RS1T", "CT1", "VRT1", "VRB1", "CF1", "RF1", "VRV1", "CBR1")
t2a = s.triode("V2A", "7025", XB, Y1, lx=6.0, ly=-6.4, unit=2)
s.wire(wx, wy, wx, Y1)
s.wire(wx, Y1, t2a["g"][0], Y1)
# Channel 1's plate load is 100k and then 6800 to rail A; the output is taken
# at their junction, N1D, not at the plate.
s.wire(XB, Y1 - 7.62, XB, Y1 - 11.1)
s.sym("R", "RL1B", "100k", XB, Y1 - 14.91, lx=-9.4, ly=0.0)
N1D = Y1 - 18.72
s.junction(XB, N1D)
s.sym("R", "RLD1", "6.8k", XB, N1D - 3.81, lx=-9.0, ly=0.0)
s.wire(XB, N1D - 7.62, XB, N1D - 10.16)
s.glabel("BA", XB, N1D - 10.16, 90)
cathode_pair(XB, Y1, "RK2", "CK2", "K2")
s.wire(XB, N1D, 144.19, N1D)
s.series_h("C", "CC1D", ".05u", 148, N1D)

# ============================ CHANNEL 2 ================================
Y2 = 136
s.caption('Channel 2 — V1B, tone network and Volume, V2B (to the mixing node)', 12, 96, 1.6)
inputs(Y2, "CH2", "R2N", "R2H", "RG2A")
t1b = s.triode("V1B", "7025", VX, Y2, unit=2)
s.wire(GB, Y2, t1b["g"][0], Y2)
s.plate_load("RL2A", "100k", t1b["p"], "BA")
cathode_label(VX, Y2, "K1")
wx, wy = tone_stack(Y2, "CC2T", "RS2T", "CT2", "VRT2", "VRB2", "CF2", "RF2", "VRV2", None)
t2b = s.triode("V2B", "7025", XB, Y2, lx=6.0, ly=-6.4, unit=1)
s.wire(wx, wy, wx, Y2)
s.wire(wx, Y2, t2b["g"][0], Y2)
s.plate_load("RL2B", "220k", t2b["p"], "BA")
cathode_label(XB, Y2, "K2")
tee2 = Y2 - 7.62 - 3.48
s.junction(XB, tee2)
s.wire(XB, tee2, 144.19, tee2)
s.series_h("C", "CC2D", ".05u", 148, tee2)
s.series_h("R", "RM2", "1M", 158, tee2)
s.wire(151.81, tee2, 154.19, tee2)
s.wire(161.81, tee2, 166, tee2)
s.glabel("VMIX", 166, tee2, 0)

# ============================ HARMONIC VIBRATO: FILTERS + V4 ===========
# Channel 1's output (VIN) splits into a low-pass branch (470k into .005 to
# ground, then .01 to V4A's grid) and a high-pass branch (220k/220k divider,
# then 250MM to V4B's grid). Both grids return through 1M each to GS, the
# splitter's grid; the oscillator's two antiphase outputs arrive at GV1 and
# GV2 from the block below.
XVIN = 168
XV4 = 214
YA = 55            # V4A (low band)
YB = 110           # V4B (high band)
s.caption('Harmonic vibrato — the band-splitting filters and the vibrato pair V4', 160, 20, 1.6)
s.wire(151.81, N1D, XVIN, N1D)
s.wire(XVIN, N1D, XVIN, YA)
s.junction(XVIN, YA)
l, r = s.series_h("R", "RLP", "470k", 176, YA)
s.wire(XVIN, YA, l, YA)
s.wire(r, YA, 182, YA)
s.junction(182, YA)
s.sym("C", "CLP", ".005u", 182, YA + 3.81, lx=-8.6, ly=0.0)
s.gnd(182, YA + 7.62)
l, r = s.series_h("C", "CV1", ".01u", 190, YA)
s.wire(182, YA, l, YA)
t4a = s.triode("V4A", "7025", XV4, YA, unit=2)
s.wire(r, YA, t4a["g"][0], YA)
s.junction(198, YA)
s.wire(198, YA, 198, YA - 5)
s.glabel("GV1", 198, YA - 5, 90)
s.junction(202, YA)
# high-pass branch
s.wire(XVIN, YA, XVIN, YA + 10)
s.sym("R", "RHP1", "220k", XVIN, YA + 13.81, lx=-9.4, ly=0.0)
VHP = YA + 17.62
s.junction(XVIN, VHP)
s.sym("R", "RHP2", "220k", XVIN, VHP + 3.81, lx=-9.4, ly=0.0)
s.gnd(XVIN, VHP + 7.62)
s.wire(XVIN, VHP, 176, VHP)
s.wire(176, VHP, 176, YB)
l, r = s.series_h("C", "CV2", "250p", 186, YB)
s.wire(176, YB, l, YB)
t4b = s.triode("V4B", "7025", XV4, YB, unit=1)
s.wire(r, YB, t4b["g"][0], YB)
s.junction(198, YB)
s.wire(198, YB, 198, YB + 5)
s.glabel("GV2", 198, YB + 5, 270)
s.junction(202, YB)
# the two grid returns and their midpoint GS
GSY = (YA + YB) / 2
s.wire(202, YA, 202, GSY - 11.62)
s.sym("R", "RGV1", "1M", 202, GSY - 7.81, lx=-9.4, ly=0.0)
s.wire(202, GSY - 4.0, 202, GSY)
s.junction(202, GSY)
s.wire(202, GSY, 202, GSY + 4.0)
s.sym("R", "RGV2", "1M", 202, GSY + 7.81, lx=-9.4, ly=0.0)
s.wire(202, GSY + 11.62, 202, YB)
s.wire(202, GSY, 196, GSY)
s.glabel("GS", 196, GSY, 180)
# plate loads off BV, and the recombining 470k pair into VMIX
s.plate_load("RLV1", "100k", t4a["p"], "BV")
s.plate_load("RLV2", "100k", t4b["p"], "BV")
teeA = YA - 7.62 - 3.48
teeB = YB - 7.62 - 3.48
XM = 230
s.junction(XV4, teeA)
s.wire(XV4, teeA, XM, teeA)
s.sym("R", "RMV1", "470k", XM, teeA + 3.81, lx=3.0, ly=0.0)
s.junction(XV4, teeB)
s.wire(XV4, teeB, XM, teeB)
s.sym("R", "RMV2", "470k", XM, teeB - 3.81, lx=3.0, ly=0.0)
YMIX = 74
s.wire(XM, teeA + 7.62, XM, YMIX)
s.wire(XM, teeB - 7.62, XM, YMIX)
s.junction(XM, YMIX)
s.wire(XM, YMIX, XM + 6, YMIX)
s.junction(XM + 6, YMIX)
s.wire(XM + 6, YMIX, XM + 6, YMIX + 5)
s.glabel("VMIX", XM + 6, YMIX + 5, 270)
# joined cathodes: 4.7k / 2-25 under V4B, V4A joins by the KV label
cathode_label(XV4, YA, "KV")
s.wire(XV4, YB + 7.62, XV4, YB + 11)
s.shunt_rc("RKV", "4.7k", "CKV", "2u 25V", XV4, YB + 11)
s.wire(XV4 + 7.62, YB + 11, XV4 + 12, YB + 11)
s.glabel("KV", XV4 + 12, YB + 11, 0)

# ============================ VIBRATO OSCILLATOR V3A + SPLITTER V3B =====
# V3A: three-section phase-shift ladder (.02 / .01 / .01) from the plate back
# to the grid. Node A carries the Speed rheostat and its 100k to ground, node
# B the 1M to the cathode and the vibrato-pedal jack (the footswitch grounds
# it and the ladder stops), the grid a 1M leak. The output leaves the plate
# through 4.7M and .005 onto the Intensity control's hot end (.1-200 to
# ground); the wiper (.05-200 to ground) feeds V4A's grid through 1M.
# V3B: its grid is GS, the node the two vibrato grids return to — so the
# oscillator's swing reaches it through V4A's grid network — and its plate
# (.25 to ground, .001 back to the grid) feeds V4B's grid through .05 and 1M.
YO = 225
XO = 60
s.caption('Vibrato oscillator V3A (excluded from the DC model) and its phase splitter V3B', 10, 176, 1.6)
t3a = s.triode("V3A", "7025", XO, YO, unit=2)
s.plate_load("RTOP", "470k", t3a["p"], "BL")
LAD = YO - 7.62 - 3.48
s.junction(XO, LAD)
l, r = s.series_h("C", "CTO3", ".02u", 52, LAD)
s.wire(r, LAD, XO, LAD)
s.wire(l, LAD, 44, LAD)
s.junction(44, LAD)                        # node A
l, r = s.series_h("C", "CTO1", ".01u", 36, LAD)
s.wire(r, LAD, 44, LAD)
s.wire(l, LAD, 28, LAD)
s.junction(28, LAD)                        # node B
l, r = s.series_h("C", "CTO2", ".01u", 20, LAD)
s.wire(r, LAD, 28, LAD)
s.wire(l, LAD, 12, LAD)
s.wire(12, LAD, 12, YO)
s.junction(12, YO)
s.sym("R", "RTOG2", "1M", 12, YO + 3.81, lx=2.8, ly=0.0)
s.gnd(12, YO + 7.62)
s.wire(12, YO, t3a["g"][0], YO)
# Speed: a rheostat above node A, its wiper strapped to the lug the 100k
# hangs from, so the control is the variable resistance the drawing's arrow
# across the element means.
s.wire(44, LAD, 44, LAD - 5.09)
s.sym("POT", "VRSPD", "4M-RA", 44, LAD - 8.9, lx=6.4, ly=-2.0)
s.wire(49.08, LAD - 8.9, 49.08, LAD - 12.71)
s.wire(49.08, LAD - 12.71, 44, LAD - 12.71)
s.junction(44, LAD - 12.71)
s.sym("R", "RSPD", "100k", 44, LAD - 16.52, lx=3.0, ly=0.0)
s.gnd(44, LAD - 20.33, 90)
s.text("Speed", 34.5, LAD - 9.5, 1.2)
# node B: 1M to the cathode, and the vibrato-pedal jack
s.sym("R", "RTOG1", "1M", 28, LAD + 3.81, lx=-9.0, ly=0.0)
s.wire(28, LAD + 7.62, 28, YO + 11)
jv = s.jack("JVIB", "vibrato pedal", 12, LAD - 15, mirror=True, lx=-9.0, ly=-4.0)
s.wire(jv["tip"][0], jv["tip"][1], 28, jv["tip"][1])
s.wire(28, jv["tip"][1], 28, LAD)
s.wire(jv["sleeve"][0], jv["sleeve"][1], 21, jv["sleeve"][1])
s.gnd(21, jv["sleeve"][1])
# cathode 4.7k / 25-25, with the ladder's 1M from node B landing on it
s.wire(XO, YO + 7.62, XO, YO + 11)
s.junction(XO, YO + 11)
s.shunt_rc("RTOK", "4.7k", "CTOK", "25u 25V", XO, YO + 11)
s.wire(28, YO + 11, XO, YO + 11)
# output: .03 to ground, then 4.7M + .005 onto the Intensity control
XT = 76
s.wire(XO, LAD, XT, LAD)
s.junction(XT, LAD)
s.sym("C", "CTOP", ".03u", XT, LAD + 3.81, lx=2.6, ly=0.0)
s.gnd(XT, LAD + 7.62)
l, r = s.series_h("R", "RTOF", "4.7M", XT + 8, LAD)
s.wire(XT, LAD, l, LAD)
l2, r2 = s.series_h("C", "CTOF", ".005u", XT + 18, LAD)
s.wire(r, LAD, l2, LAD)
s.wire(r2, LAD, XT + 26, LAD)
s.junction(XT + 26, LAD)                   # node X, Intensity's hot end
s.sym("C", "CTX", ".1u 200V", XT + 26, LAD + 3.81, lx=-10.4, ly=0.0)
s.gnd(XT + 26, LAD + 7.62)
s.wire(XT + 26, LAD, XT + 34, LAD)
s.sym("POT", "VRINT", "10M-L", XT + 34, LAD + 3.81, lx=2.2, ly=-7.6)
s.gnd(XT + 34, LAD + 7.62)
s.text("Intensity", XT + 28, LAD - 9.5, 1.2)
W = LAD + 3.81
s.wire(XT + 39.08, W, XT + 44, W)
s.junction(XT + 44, W)
s.sym("C", "CTW", ".05u 200V", XT + 44, W + 3.81, lx=2.6, ly=0.0)
s.gnd(XT + 44, W + 7.62)
l, r = s.series_h("R", "RWV", "1M", XT + 52, W)
s.wire(XT + 44, W, l, W)
s.wire(r, W, XT + 62, W)
s.glabel("GV1", XT + 62, W, 0)
# splitter V3B
XS = 160
YS = 245
t3b = s.triode("V3B", "7025", XS, YS, unit=1)
s.plate_load("RLS", "100k", t3b["p"], "BL")
s.wire(XS, YS + 7.62, XS, YS + 11)
s.shunt_rc("RKS", "1.5k", "CKS", "25u 25V", XS, YS + 11)
s.glabel("GS", 126, YS, 180)
s.wire(126, YS, t3b["g"][0], YS)
s.junction(132, YS)
s.sym("C", "CGS", ".05u 200V", 132, YS + 3.81, lx=-11.4, ly=0.0)
s.gnd(132, YS + 7.62)
s.junction(140, YS)
s.sym("R", "RGS", "1M", 140, YS + 3.81, lx=2.8, ly=0.0)
s.gnd(140, YS + 7.62)
teeS = YS - 7.62 - 3.48
s.junction(XS, teeS)
s.wire(XS, teeS, 148, teeS)
s.sym("C", "CFS", ".001u", 148, YS - 3.81, lx=-8.4, ly=-2.0)
s.wire(148, teeS, 148, YS - 7.62)
s.junction(148, YS)
s.wire(XS, teeS, 176, teeS)
s.junction(176, teeS)
s.sym("C", "CPS", ".25u", 176, teeS + 3.81, lx=2.6, ly=0.0)
s.gnd(176, teeS + 7.62)
l, r = s.series_h("C", "CSV", ".05u", 184, teeS)
s.wire(176, teeS, l, teeS)
l2, r2 = s.series_h("R", "RSV", "1M", 194, teeS)
s.wire(r, teeS, l2, teeS)
s.wire(r2, teeS, 204, teeS)
s.glabel("GV2", 204, teeS, 0)

# ============================ PHASE INVERTER (LTP, V5) =================
XPI = 296
YPH = 74
YPB = 124
JY = 103
XJ = XPI - 20      # JPI, the tail junction
s.caption("Long-tailed-pair phase inverter (V5)", 250, 36, 1.6)
l, r = s.series_h("C", "CPIN", ".001u", XM + 14, YPH)
s.wire(XM + 6, YPH, l, YPH)
# The A-FJ layout wires the 82k (hot, .001-fed) triode on pins 1/2/3 (+315 V
# at pin 1) and the 100k (cold) one on 6/7/8 (+310 V at pin 6).
t5a = s.triode("V5A", "7025", XPI, YPH, unit=2)
t5b = s.triode("V5B", "7025", XPI, YPB, unit=1)
s.wire(r, YPH, t5a["g"][0], YPH)
s.plate_load("RLA", "82k 5%", t5a["p"], "BC")
s.plate_load("RLB", "100k 5%", t5b["p"], "BC")
# cathodes join on a bus left of the bottles
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, XPI - 8, YPH + 10)
s.wire(XPI, YPB + 7.62, XPI, YPB + 10)
s.wire(XPI, YPB + 10, XPI - 14, YPB + 10)
s.wire(XPI - 14, YPB + 10, XPI - 14, YPB - 10)
s.wire(XPI - 14, YPB - 10, XPI - 8, YPB - 10)
s.wire(XPI - 8, YPH + 10, XPI - 8, YPB - 10)
s.junction(XPI - 8, JY)
tl, tr = s.series_h("R", "RTAIL", "820", XPI - 13.5, JY)
s.wire(tr, JY, XPI - 8, JY)
s.wire(XJ, JY, tl, JY)
s.junction(XJ, JY)
s.sym("R", "RGA", "1M", XJ, JY - 8, lx=-9.4)
s.wire(XJ, JY - 4.19, XJ, JY)
s.wire(XJ, JY - 11.81, XJ, YPH)
s.junction(XJ, YPH)
s.sym("R", "RGB", "1M", XJ - 4, JY + 8, lx=-9.4)
s.wire(XJ - 4, JY + 4.19, XJ - 4, JY)
s.wire(XJ - 4, JY, XJ, JY)
s.junction(XJ - 4, JY)
s.wire(XJ - 4, JY + 11.81, XJ - 4, YPB)
s.junction(XJ - 4, YPB)
s.wire(XJ - 4, YPB, t5b["g"][0], YPB)
# tail -> 6.8k -> the foot node: 1500 to ground, 22k from the OT
# secondary, .1-200 from the cold grid, and the Presence branch (5k-L
# rheostat in series with .1-200, AC-only) paralleling the 1500.
NFX = XJ - 26
tl, tr = s.series_h("R", "RT2", "6.8k", XJ - 14, JY)
s.wire(tr, JY, XJ - 4, JY)
s.wire(tl, JY, NFX, JY)
s.junction(NFX, JY)
l, r = s.series_h("R", "RNFB", "22k", NFX - 8, JY)
s.wire(r, JY, NFX, JY)
s.wire(l, JY, NFX - 16, JY)
s.glabel("SPKR", NFX - 16, JY, 180)
l, r = s.series_h("C", "CGB", ".1u 200V", XJ - 14, YPB)
s.wire(r, YPB, XJ - 4, YPB)
s.wire(NFX, YPB, l, YPB)
s.wire(NFX, JY, NFX, YPB)
s.junction(NFX, YPB)
TAP = YPB + 3
FGY = YPB + 21
s.wire(NFX, YPB, NFX, TAP)
s.junction(NFX, TAP)
s.wire(NFX, TAP, NFX, TAP + 3.5)
s.sym("R", "RPRES", "1.5k", NFX, TAP + 7.31, lx=2.8, ly=0.0)
s.wire(NFX, TAP + 11.12, NFX, FGY)
s.gnd(NFX, FGY)
PX = NFX - 8
s.wire(NFX, TAP, PX + 5.08, TAP)
s.wire(PX + 5.08, TAP, PX, TAP)
s.sym("POT", "VRPRES", "5k-L", PX, TAP + 3.81, lx=-9.6, ly=0.0)
s.wire(PX + 5.08, TAP + 3.81, PX + 5.08, TAP)
s.junction(PX + 5.08, TAP)
s.sym("C", "CPRES", ".1u 200V", PX, TAP + 11.43, lx=-10.8, ly=0.0)
s.wire(PX, TAP + 15.24, PX, FGY)
s.wire(PX, FGY, NFX, FGY)
s.junction(NFX, FGY)
s.text("Presence", PX - 6, FGY + 3.5, 1.2)
# 47MM across the two plates; the output couplers
teeH = YPH - 7.62 - 3.48
teeC = YPB - 7.62 - 3.48
XCP = XPI + 14
XC = XPI + 22
s.junction(XPI, teeH)
s.wire(XPI, teeH, XC - 3.81, teeH)
s.junction(XPI, teeC)
s.wire(XPI, teeC, XC - 3.81, teeC)
s.junction(XCP, teeH)
s.junction(XCP, teeC)
s.wire(XCP, teeH, XCP, teeH + 7.29)
s.sym("C", "CPP", "47p", XCP, teeH + 11.1, lx=2.6, ly=0.0)
s.wire(XCP, teeH + 14.91, XCP, teeC)
s.series_h("C", "C1", ".05u", XC, teeH)
s.series_h("C", "C2", ".05u", XC, teeC)

# ============================ OUTPUT PAIR + OT ========================
XOUT = 352
XG = XC + 8
s.caption("Output pair — 6L6GC, grounded cathodes, fixed bias", 324, 36, 1.6)
plates = {}
for gy, tee, vref, glref, scref in ((YPH, teeH, "V7", "RGL1", "RSC1"),
                                    (YPB, teeC, "V8", "RGL2", "RSC2")):
    s.wire(XC + 3.81, tee, XG, tee)
    s.wire(XG, tee, XG, gy)
    s.wire(XG, gy, XOUT - 7.62, gy)
    p = s.pentode(vref, "6L6GC", XOUT, gy)
    plates[vref] = p["p"]
    s.junction(XG + 6, gy)
    s.sym("R", glref, "220k 5%", XG + 6, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(XG + 6, gy + 7.62, XG + 6, gy + 10.16)
    s.glabel("-55V", XG + 6, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6, p["g2"][1])
    s.sym("R", scref, "470 1W", p["g2"][0] + 6 + 3.81, p["g2"][1], rot=90, lx=-3.2, ly=-6.2)
    s.wire(p["g2"][0] + 6 + 7.62, p["g2"][1], p["g2"][0] + 6 + 11, p["g2"][1])
    s.glabel("BP1", p["g2"][0] + 6 + 11, p["g2"][1], 0)
    s.gnd(XOUT, p["k"][1])
XT2 = 402
ot = s.ot_pp("TR2", "n/a", XT2, 98, lx=-6.35, ly=-14.5)
s.wire(*plates["V7"], XOUT, 60)
s.wire(XOUT, 60, XT2 - 13, 60)
s.wire(XT2 - 13, 60, XT2 - 13, ot["pri_a"][1])
s.wire(XT2 - 13, ot["pri_a"][1], *ot["pri_a"])
s.wire(*plates["V8"], XOUT, 111)
s.wire(XOUT, 111, XT2 - 13, 111)
s.wire(XT2 - 13, 111, XT2 - 13, ot["pri_b"][1])
s.wire(XT2 - 13, ot["pri_b"][1], *ot["pri_b"])
s.wire(*ot["ct"], XT2 - 17, ot["ct"][1])
s.glabel("B_RES", XT2 - 17, ot["ct"][1], 180)
s.wire(*ot["sec_h"], XT2 + 13, ot["sec_h"][1])
s.glabel("SPKR", XT2 + 13, ot["sec_h"][1], 90)
jk = s.jack("JSPK", "spkr", XT2 + 23, 98)
s.wire(XT2 + 13, ot["sec_h"][1], *jk["tip"])
s.wire(*ot["sec_c"], *jk["sleeve"])
s.wire(XT2 + 15, ot["sec_c"][1], XT2 + 15, ot["sec_c"][1] + 4)
s.junction(XT2 + 15, ot["sec_c"][1])
s.gnd(XT2 + 15, ot["sec_c"][1] + 4)

# ============================ POWER SUPPLY ==============================
s.caption("Power supply — silicon full-wave (two legs of three diodes), choke, and the dropper chain to every rail", 196, 186, 1.4)
BY = 213
# A-FJ: each HT end of TR1 runs through a leg of three silicon diodes, every
# + (bar, cathode) toward the reservoir; the centre tap is grounded.
for yy, refs, net, ly in ((BY - 16, ("D1", "D2", "D3"), "HT_A", -5.4),
                          (BY - 8, ("D4", "D5", "D6"), "HT_B", 5.0)):
    s.glabel(net, 196, yy, 180)
    s.wire(196, yy, 200.92, yy)
    for k, ref in enumerate(refs):
        s.sym("DIODE_SS", ref, "1N4007", 206 + 10.16 * k, yy, lx=-2.0, ly=ly)
    s.wire(206 + 10.16 * 2 + 5.08, yy, 240, yy)
s.wire(240, BY - 16, 240, BY)
s.junction(240, BY - 8)
s.wire(240, BY, 244, BY)
s.junction(244, BY)
s.sym("C", "CF3", "20u 600V", 244, BY + 3.81, lx=2.6, ly=1.6)
s.gnd(244, BY + 7.62)
s.wire(244, BY, 244, BY - 3.5)
s.glabel("B_RES", 244, BY - 3.5, 90)
s.wire(244, BY, 248.38, BY)
s.sym("CHOKE", "L1", "CH.", 256, BY)
s.wire(263.62, BY, 270, BY)
RAILS1 = (("BP1", 270, "CF4"), ("BC", 286, "CF5"), ("BA", 302, "CF6"))
for net, x, cref in RAILS1:
    s.junction(x, BY)
    s.wire(x, BY, x, BY - 3.5)
    s.glabel(net, x, BY - 3.5, 90)
    s.sym("C", cref, "20u 600V", x, BY + 3.81, lx=2.6, ly=1.6)
    s.gnd(x, BY + 7.62)
l, r = s.series_h("R", "RD1", "4.7k 1W", 278, BY)
s.wire(270, BY, l, BY)
s.wire(r, BY, 286, BY)
l, r = s.series_h("R", "RD2", "56k 1W", 294, BY)
s.wire(286, BY, l, BY)
s.wire(r, BY, 302, BY)
BY2 = BY + 22
s.glabel("BP1", 262, BY2, 180)
for net, x, cref in (("BV", 278, "CF7"), ("BL", 294, "CF8")):
    s.junction(x, BY2)
    s.wire(x, BY2, x, BY2 - 3.5)
    s.glabel(net, x, BY2 - 3.5, 90)
    s.sym("C", cref, "20u 600V", x, BY2 + 3.81, lx=2.6, ly=1.6)
    s.gnd(x, BY2 + 7.62)
l, r = s.series_h("R", "RD3", "56k 1W", 270, BY2)
s.wire(262, BY2, l, BY2)
s.wire(r, BY2, 278, BY2)
l, r = s.series_h("R", "RD4", "56k 1W", 286, BY2)
s.wire(278, BY2, l, BY2)
s.wire(r, BY2, 294, BY2)
s.text("+460 V", 234, BY - 20, 1.1)
s.text("+458 V", 266, BY - 9, 1.1)

# mains / AC switch / fuse / pilot lamp
PTX, PTY = 372, 222
pt = s.pt("TR1", "n/a", PTX, PTY, lx=-6.35, ly=-11.9, tap=True)
s.wire(pt["tap"][0], pt["tap"][1], pt["tap"][0] + 2, pt["tap"][1])
s.glabel("HT_TAP", pt["tap"][0] + 2, pt["tap"][1], 0)
sw_l, sw_r = s.switch("SW1", "AC", 344, PTY - 5.08)
s.wire(330, PTY - 5.08, sw_l, PTY - 5.08)
s.glabel("MAINS", 330, PTY - 5.08, 180)
fl, fr = s.fuse("F1", "3A", 356, PTY - 5.08)
s.wire(sw_r, PTY - 5.08, fl, PTY - 5.08)
s.wire(fr, PTY - 5.08, *pt["pri1"])
s.wire(*pt["pri2"], 330, PTY + 5.08)
s.glabel("MAINS N", 330, PTY + 5.08, 180)
s.wire(*pt["ht_a"], PTX + 20, PTY - 5.08)
s.glabel("HT_A", PTX + 20, PTY - 5.08, 0)
s.wire(*pt["ht_b"], PTX + 20, PTY + 5.08)
s.glabel("HT_B", PTX + 20, PTY + 5.08, 0)
s.wire(*pt["ht_ct"], PTX + 20, PTY)
s.glabel("GND", PTX + 20, PTY, 0)
lp = s.lamp("PL1", "pilot", 344, 242)
s.wire(*lp["hi"], lp["hi"][0], 236)
s.glabel("HTR_A", lp["hi"][0], 236, 90)
s.wire(*lp["lo"], lp["lo"][0], 250)
s.glabel("HTR_B", lp["lo"][0], 250, 270)
s.text("Pilot lamp — across the 6.3 V heater supply", 352, 243, 1.1)

# bias supply, read off A-FJ: TR1's bias tap -> rectifier (+ end toward the
# tap) -> 8-150 -> 10K -> the -55 V line, which carries a second 8-150 and a
# 56K bleeder to ground. The netlist drives the -55 V line as an ideal source.
YBI = 258
s.caption("Bias supply — TR1's bias tap, a rectifier, 8 µF, 10k, then 8 µF with a 56k bleeder: -55 V", 196, 248, 1.3)
s.glabel("HT_TAP", 196, YBI, 180)
s.wire(196, YBI, 204.92, YBI)
s.sym("DIODE_SS", "DBIAS", "Si", 210, YBI, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(215.08, YBI, 222, YBI)
s.junction(222, YBI)
s.sym("C", "CBIAS", "8u", 222, YBI + 3.81, lx=2.6, ly=1.6)
s.gnd(222, YBI + 7.62)
l, r = s.series_h("R", "RBIAS2", "10k", 231, YBI)
s.wire(222, YBI, l, YBI)
s.wire(r, YBI, 262, YBI)
s.junction(240, YBI)
s.sym("C", "CBIAS2", "8u", 240, YBI + 3.81, lx=2.6, ly=1.6)
s.gnd(240, YBI + 7.62)
s.junction(254, YBI)
s.sym("R", "RBIAS1", "56k", 254, YBI + 3.81, lx=2.8, ly=0.0)
s.gnd(254, YBI + 7.62)
s.glabel("-55V", 262, YBI, 0)

s.write(OUT)
print(f"wrote {OUT}")
