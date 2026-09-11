#!/usr/bin/env python3
"""Generate amps/5f8a/schematic.kicad_sch from the stage-template library.

Values per the published 5F8-A (I-EG) drawing (see amps/5f8a/meta.yaml).

Rails, in the netlist's names and the drawing's printed figures:
  B+1 = +397 V   reservoir, 5881 plates, output-transformer centre tap
  B+2 = +395 V   screens, after the 14684 choke
  B+3 = +355 V   phase-inverter plate supply, after the 4.7 kΩ
  B+4 = +295 V   every preamp plate load and the cathode-follower plate
  -41 V          the fixed-bias grid line

The output stage is four 5881s in two PARALLEL PAIRS, which is the whole point
of this circuit and the thing that must not be flattened into a plain push-pull
pair: each phase drives two bottles whose plates, and whose cathodes, are
common, and the 1500 Ω stopper sits BETWEEN the pair's two grids rather than in
series with the coupler (on the factory board it bridges socket to socket).

Heaters, the PT primary and the standby switch are omitted here (annotation
layer) — see netlist.cir, meta.yaml and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5f8a" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, bright + normal channels, shared 820R/250u cathode -------
# Each channel has two jacks, as the sheet draws them: a 68k stopper on each,
# meeting at the grid, with the 1M leak on the same node.
for y, j1, j2, r1, r2, gref, pref, plref, cref, vref, mref in [
        (92,  "BRIGHT 1", "BRIGHT 2", "R1s", "R2s", "RG1", "V1A", "RL1", "C1", "VR1", "RM1"),
        (126, "NORMAL 1", "NORMAL 2", "R3s", "R4s", "RG2", "V1B", "RL2", "C2", "VR2", "RM2")]:
    gb = 34                              # grid-bus x
    # Jack 2 above, jack 1 below, as the sheet stacks them. Each jack reaches
    # the grid through its own 68 kΩ; the 1 MΩ leak sits on JACK 1's tip — on
    # the far side of that stopper, not on the grid — which is how the drawing
    # wires it and why the leak is a chassis part at the jacks on the layout.
    for jack, rref, jy in ((j2, r2, y - 5), (j1, r1, y + 5)):
        s.glabel(jack, 14, jy, 180)
        l, r = s.series_h("R", rref, "68k", 24, jy)
        s.wire(14, jy, l, jy)            # the lead must REACH the jack label
        s.wire(r, jy, gb, jy)
    s.wire(gb, y - 5, gb, y + 5)
    s.junction(gb, y)
    s.junction(19, y + 5)
    s.sym("R", gref, "1M", 19, y + 5 + 3.81, lx=-6.6)
    s.gnd(19, y + 5 + 7.62)
    # V1B's caption goes to the LEFT: the shared-cathode column runs down the
    # right of both bottles and would print through it on the lower one.
    t = s.triode(pref, "12AY7", 49.53, y, lx=(6.0 if y == 92 else -14.2))
    s.wire(gb, y, t["g"][0], y)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # coupler -> volume pot -> 270k mixer into the shared V2A grid line
    ty = y - 7.62 - 3.48                 # plate stub tee
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", cref, ".02u", 64.77, ty)
    s.wire(crr, ty, 73.66, ty)
    s.sym("POT", vref, "1M vol", 73.66, ty + 3.81)
    s.gnd(73.66, ty + 7.62)          # cold lug: pot centre + 3.81, not + 7.62
    s.wire(78.74, ty + 3.81, 81.28, ty + 3.81)
    ml, mr = s.series_h("R", mref, "270k", 85.09, ty + 3.81)
    s.wire(81.28, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 91.44, ty + 3.81)
    s.wire(91.44, ty + 3.81, 91.44, 109)
s.junction(91.44, 109)
s.text("100 pF bright cap across VR1 omitted (AC only)", 56, 74, 1.1)

# shared cathode
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C3", "250u", 56.13, 140)

# ---- V2A + DC-coupled cathode follower ---------------------------------
t2a = s.triode("V2A", "12AX7", 101.6, 109)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 119)
s.sym("R", "RK2", "820", 101.6, 122.81)
s.gnd(101.6, 126.62)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# direct-coupled CF: grid from the plate stub tee
tee = 109 - 7.62 - 3.48
s.wire(101.6, tee, 108.9, tee)
s.junction(101.6, tee)
tcf = s.triode("V2B", "12AX7 CF", 116.84, 109)
s.wire(108.9, tee, 108.9, 109)
s.wire(108.9, 109, tcf["g"][0], 109)
s.wire(116.84, 101.38, 116.84, 98.5)
s.glabel("B+4", 116.84, 98.5, 90)      # CF plate straight to the rail
s.wire(116.84, 116.62, 116.84, 119.5)
s.junction(116.84, 119.5)
s.sym("R", "RKCF", "100k", 116.84, 123.31)
s.gnd(116.84, 127.12)

# ---- TMB tone stack -----------------------------------------------------
# Wired as the published 5F8-A (I-EG) schematic draws it — the same ladder the
# 5F6 and 5F6-A sheets print, NOT the "canonical FMV" idealisation:
#   node A = cathode-follower output: 250 pF to the treble pot AND the 56k slope;
#   node B = the slope's foot: one 0.02 uF to the treble-bottom/bass node, the
#            other 0.02 uF to the MIDDLE POT'S WIPER;
#   the bass pot is a rheostat (wiper strapped to its hot lug) in series down
#   the ladder, and the stack's output is the TREBLE WIPER ALONE.
# The middle pot's foot runs straight to ground; the presence control sits at
# the phase-inverter tail foot instead.
s.wire(116.84, 119.5, 124.46, 119.5)
s.junction(124.46, 119.5)
s.wire(124.46, 119.5, 124.46, 94)      # node A up to the 250 pF branch
s.wire(124.46, 94, 140.19, 94)
sl, sr = s.series_h("R", "RSL", "56k", 128.27, 119.5)
s.wire(sr, 119.5, 137, 119.5)
tl, tr = s.series_h("C", "C4", "250p", 144, 94)
s.wire(tr, 94, 152.4, 94)
s.sym("POT", "VR3", "250k treb", 152.4, 97.81)
# node B -> 0.02 uF to the treble-bottom/bass node, 0.02 uF to the mid wiper
s.junction(137, 119.5)
s.wire(137, 119.5, 137, 106)
bl, br = s.series_h("C", "C5", ".02u", 144, 106)
s.wire(137, 106, bl, 106)
s.wire(br, 106, 152.4, 106)
s.wire(137, 119.5, 137, 143)
b2l, b2r = s.series_h("C", "C5b", ".02u", 144, 143)
s.wire(137, 143, b2l, 143)
s.wire(b2r, 143, 161, 143)
s.wire(161, 143, 161, 121.81)
s.wire(161, 121.81, 157.48, 121.81)    # -> middle wiper
# the stack column: treble -> bass -> middle -> ground
s.wire(152.4, 101.62, 152.4, 106)      # treble bottom lug -> bass node
s.sym("POT", "VR4", "1M bass", 152.4, 109.81)
s.wire(157.48, 109.81, 166, 109.81)    # bass wiper strapped to its hot lug (rheostat)
s.wire(166, 109.81, 166, 106)
s.wire(166, 106, 152.4, 106)
s.junction(152.4, 106)
s.wire(152.4, 113.62, 152.4, 118)
s.sym("POT", "VR5", "25k mid", 152.4, 121.81)
s.gnd(152.4, 125.62)
# treble wiper = stack output
s.wire(157.48, 97.81, 157.48, 92)

# ---- long-tailed-pair phase inverter ------------------------------------
ol, orr = s.series_h("C", "C6", ".02u", 162, 92)
s.wire(157.48, 92, ol, 92)
s.wire(orr, 92, 168.91, 92)
# Socket basing from the factory layout (6368×3218): the 82k half's +230 V
# plate lands on pin 1 (+19 V grid on 2), the 100k half's +225 V on pin 6
# (+20 V on 7), +28.5 V tail on 8 — V3A is unit 2, V3B unit 1.
tp = s.triode("V3A", "12AX7", 176.53, 92, unit=2)
s.wire(168.91, 92, tp["g"][0], 92)
bt = s.triode("V3B", "12AX7", 176.53, 126, unit=1)
s.plate_load("RLA", "82k 5%", tp["p"], "B+3")
s.plate_load("RLB", "100k 5%", bt["p"], "B+3")
# shared tail: cathodes -> 470 -> J -> 10k -> the tail's foot (NOT ground)
s.wire(176.53, 99.62, 176.53, 102)
s.wire(176.53, 102, 182.88, 102)
s.wire(176.53, 133.62, 176.53, 136)
s.wire(176.53, 136, 182.88, 136)
s.wire(182.88, 102, 182.88, 136)
s.junction(182.88, 109)
s.sym("R", "RTAIL", "470", 187.96, 109 + 3.81, lx=2.0)
s.wire(182.88, 109, 187.96, 109)
s.junction(187.96, 116.62)
s.sym("R", "RT2", "10k", 187.96, 120.43)
# both grid leaks to the junction
s.wire(168.91, 92, 168.91, 99)
s.junction(168.91, 92)
s.sym("R", "RGA", "1M", 168.91, 102.81, lx=-9.4)
s.wire(168.91, 106.62, 168.91, 116.62)
s.wire(168.91, 116.62, 187.96, 116.62)
s.wire(168.91, 126, 168.91, 122)        # bottom grid
s.wire(168.91, 126, bt["g"][0], 126)
s.junction(168.91, 126)
s.sym("R", "RGB", "1M", 168.91, 118.19, lx=-9.4)
# V3B's grid is held to the tail's FOOT by 0.1 uF, not to the junction: the
# I-EG schematic lands it on the vertical the 10k, the 56k and the presence
# pot share, and the layout puts it on the 10k's top eyelet.
s.sym("C", "C7", ".1u", 168.91, 129.81, lx=-5.9)
s.wire(168.91, 133.62, 168.91, 140)
s.wire(168.91, 140, 187.96, 140)

# ---- negative feedback + presence, at the phase-inverter tail's foot ----
# The 10k's far end is a node of its own that also carries C7, and it does not
# return to ground: 56 kΩ back to the speaker (DC ground through the OT
# secondary) and the 5 kΩ presence pot's track are its DC returns, the pot's
# lower lug grounded and 0.1 µF on its wiper, as I-EG draws them.
s.wire(187.96, 124.24, 187.96, 147)     # RT2's foot, straight down the node
s.junction(187.96, 140)
s.junction(187.96, 147)
nl, nr = s.series_h("R", "RNF", "56k", 170, 147)
s.wire(nr, 147, 187.96, 147)
s.wire(158, 147, nl, 147)
s.glabel("SPKR", 158, 147, 180)
s.sym("POT", "VR6", "5k pres", 187.96, 150.81)
s.gnd(187.96, 154.62)
s.wire(193.04, 150.81, 196, 150.81)          # presence wiper -> 0.1 uF -> gnd
s.sym("C", "C16", ".1u", 196, 154.62)
s.gnd(196, 158.43)

# ---- 47 pF across the two phase-inverter plates -------------------------
TEE_A, TEE_B = 80.9, 114.9              # the two PI plate-stub tees
s.wire(176.53, TEE_A, 200, TEE_A)
s.junction(176.53, TEE_A)
s.wire(176.53, TEE_B, 200, TEE_B)
s.junction(176.53, TEE_B)
s.junction(198, TEE_A)
s.junction(198, TEE_B)
s.wire(198, TEE_A, 198, 91)
s.sym("C", "C10", "47p", 198, 94.81, lx=2.6)
s.wire(198, 98.62, 198, TEE_B)

# ---- output quartet: four 5881s in two parallel pairs -------------------
# One 0.1 uF coupler and one 220k leak per PAIR; the 1500 ohm stopper stands
# BETWEEN the pair's two grids, so the coupler node is the first grid and the
# second grid sits behind the stopper.
GX, XO = 224, 240                       # grid column, bottle column
for tee, cref, glref, gsref, gy_hi, gy_lo, v_hi, v_lo, s_hi, s_lo in [
        (TEE_A, "C8", "RGL1", "RGS1", 66, 96, "V4", "V5", "RS1", "RS2"),
        (TEE_B, "C9", "RGL2", "RGS2", 140, 170, "V6", "V7", "RS3", "RS4")]:
    cl, crr = s.series_h("C", cref, ".1u", 206, tee)
    s.wire(200, tee, cl, tee)
    s.wire(crr, tee, 216, tee)
    s.wire(216, tee, 216, gy_hi)
    s.wire(216, gy_hi, GX, gy_hi)
    s.junction(GX, gy_hi)
    # The 220k leak hangs off the COUPLER node — which is the first grid of the
    # pair, on the near side of the stopper — exactly as the sheet draws it.
    s.wire(GX, gy_hi, GX, gy_hi - 8)
    s.sym("R", glref, "220k", GX, gy_hi - 11.81)
    s.wire(GX, gy_hi - 15.62, GX, gy_hi - 19.62)
    s.glabel("-41V", GX, gy_hi - 19.62, 90)
    # the 1500 stopper between the pair's two grids
    s.wire(GX, gy_hi, GX, (gy_hi + gy_lo) / 2 - 3.81)
    s.sym("R", gsref, "1.5k", GX, (gy_hi + gy_lo) / 2)
    s.wire(GX, (gy_hi + gy_lo) / 2 + 3.81, GX, gy_lo)
    for gy, vref, sref in ((gy_hi, v_hi, s_hi), (gy_lo, v_lo, s_lo)):
        p = s.pentode(vref, "5881", XO, gy)
        s.wire(GX, gy, p["g1"][0], gy)
        sl2, sr2 = s.series_h("R", sref, "470 1W", p["g2"][0] + 5.71, p["g2"][1])
        s.wire(p["g2"][0], p["g2"][1], sl2, p["g2"][1])
        s.wire(sr2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
        s.glabel("B+2", p["g2"][0] + 11.5, p["g2"][1], 0)
        s.gnd(XO, p["k"][1])

# ---- output transformer -------------------------------------------------
# Parallel push-pull: both plates of a pair land on the same primary end.
s.sym("OT_PP", "T3", "45268", 268, 118)
s.wire(XO, 66 - 0.635 - 7.62, XO, 52)
s.wire(XO, 52, 259.11, 52)
s.wire(259.11, 52, 259.11, 112.92)              # V4/V5 plates -> primary A
s.wire(XO, 96 - 0.635 - 7.62, XO, 82)
s.wire(XO, 82, 250, 82)
s.wire(250, 82, 250, 52)
s.junction(250, 52)
s.wire(XO, 140 - 0.635 - 7.62, XO, 128)
s.wire(XO, 128, 259.11, 128)
s.wire(259.11, 128, 259.11, 123.08)             # V6/V7 plates -> primary B
s.wire(XO, 170 - 0.635 - 7.62, XO, 156)
s.wire(XO, 156, 250, 156)
s.wire(250, 156, 250, 128)
s.junction(250, 128)
s.wire(259.11, 118, 253, 118)
s.glabel("B+1", 253, 118, 180)
s.wire(276.89, 115.46, 283, 115.46)
s.glabel("SPKR", 283, 115.46, 0)
s.wire(276.89, 120.54, 283, 120.54)
s.glabel("GND", 283, 120.54, 0)

# ---- power supply + bias ------------------------------------------------
# The caption sits to the RIGHT of the two rectifier stubs: at x=25 it would
# print straight through the HT_A / HT_B flags standing over them.
s.text("Power — 300-0-300 (PT 7993), GZ34, choke 14684 · bias: selenium rect, "
       "15k/56k, 8u/150V x2 -> -41V", 74, 162, 1.4)
for x, ref, ht in [(41.91, "V8A", "HT_A"), (54.61, "V8B", "HT_B")]:
    s.glabel(ht, x, 167.5, 90)
    s.wire(x, 167.5, x, 170.16)
    s.diode_tube(ref, "GZ34", x, 177.78, lx=(-11.4 if ref == "V8A" else 6.0))
    s.wire(x, 185.4, x, 187.8)
s.wire(41.91, 187.8, 88.9, 187.8)
s.junction(54.61, 187.8)
s.junction(66.04, 187.8)
s.sym("C", "C11", "20u", 66.04, 191.61)
s.gnd(66.04, 195.42)
s.junction(76.2, 187.8)
s.sym("C", "C11b", "20u", 76.2, 191.61)
s.gnd(76.2, 195.42)
s.glabel("B+1", 88.9, 187.8, 0)
s.wire(88.9, 187.8, 91.44, 187.8)
s.sym("CHOKE", "L1", "14684", 99.06, 187.8, lx=-4.0, ly=-6.4)
s.wire(106.68, 187.8, 118.11, 187.8)
s.junction(111.76, 187.8)
s.glabel("B+2", 111.76, 185.26, 90)
s.wire(111.76, 185.26, 111.76, 187.8)
s.junction(115.21, 187.8)
s.sym("C", "C12", "20u", 115.21, 191.61)
s.gnd(115.21, 195.42)
l, r = s.series_h("R", "RD1", "4.7k 1W", 121.92, 187.8)
s.wire(r, 187.8, 133.35, 187.8)
s.junction(128.27, 187.8)
s.glabel("B+3", 128.27, 185.26, 90)
s.wire(128.27, 185.26, 128.27, 187.8)
s.junction(130.81, 187.8)
s.sym("C", "C13", "20u", 130.81, 191.61)
s.gnd(130.81, 195.42)
l, r = s.series_h("R", "RD2", "10k 1W", 137.16, 187.8)
s.wire(r, 187.8, 148.59, 187.8)
s.junction(143.51, 187.8)
s.glabel("B+4", 143.51, 185.26, 90)
s.wire(143.51, 185.26, 143.51, 187.8)
s.sym("C", "C14", "8u", 148.59, 191.61)
s.gnd(148.59, 195.42)
# bias supply (compact): HT tap -> selenium rect -> 15k -> -41V node, 56k bleeder
s.glabel("HT_B", 144.5, 206.0, 180)
s.wire(144.5, 206.0, 148.31, 206.0)
s.sym("DIODE_SS", "D1", "SEL", 153.39, 206.0, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(158.47, 206.0, 162.28, 206.0)
s.junction(160.9, 206.0)
s.sym("C", "C15b", "8u", 160.9, 209.81)
s.gnd(160.9, 213.62)
l, r = s.series_h("R", "RB1", "15k", 166.09, 206.0)
s.wire(162.28, 206.0, l, 206.0)
s.wire(r, 206.0, 177.52, 206.0)
s.junction(172.44, 206.0)
s.sym("R", "RB2", "56k", 172.44, 209.81, lx=-4.2, ly=-9.1)
s.gnd(172.44, 213.62)
s.junction(174.98, 206.0)
s.sym("C", "C15", "8u", 174.98, 209.81, lx=2.2)
s.gnd(174.98, 213.62)
s.glabel("-41V", 177.52, 206.0, 0)

s.write(OUT, [
    "Four 5881s in two parallel pairs: each phase drives two bottles on common "
    "plates and common cathodes, with the 1500 Ω stopper between the pair's grids",
    "47 pF across the phase-inverter plates is drawn; the 100 pF bright cap "
    "across VR1 is annotated, being inside the abstracted volume network",
    "Heaters, PT primary and standby omitted — see the netlist and the sources list",
])
print(f"wrote {OUT}")
