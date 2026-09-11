#!/usr/bin/env python3
"""Generate amps/5e6a/schematic.kicad_sch from the stage-template library.

Values and topology per the published 5E6-A (A-EE) drawing (see
amps/5e6a/meta.yaml), read at the scan's native resolution on 2026-09-10:
schematic page 6363 x 4071, layout page 6463 x 3809. Redrawn from the facts
read there, not traced.

The drawing has seven stages on five bottles, and this sheet draws all seven:

  - a two-channel 12AY7 input (no grid stoppers, shared 820R / 250 uF cathode);
  - a second 12AY7 whose halves are a gain stage (V2A) direct-coupled to a
    cathode follower (V2B);
  - the tone network, fed from the follower's CATHODE: 0.1 uF to a node held
    at ground by 220k and fed back to V2A's grid through 10 MEG, then 220k to
    the Bass control's wiper (one end lug grounded, the other through 0.005 uF
    to ground), then 220k to the Treble control's wiper; the Treble control is
    fed from the follower through 250 pF and its far end bleeds to ground
    through 0.01 uF; its wiper is the driver's grid;
  - a 12AX7 whose halves are a driver (V3A) and a split-load cathodyne (V3B),
    with the 20k feedback resistor and the Presence control on the driver's
    cathode;
  - the fixed-bias 6L6G pair, each grid fed through a 0.1 uF coupler onto the
    junction where its 220k leak lands, then a 1.5k stopper.

The supply runs two 5U4GA in parallel (each HT end to one plate of each
bottle) into a 16 uF can at +420 V, a choke to +410 V (two 16 uF cans; the OT
centre tap and both screens), and two 10k droppers to +335 V and +275 V. The
bias supply is the HT winding's tap -> 3300R -> selenium rectifier -> -42 V,
with 100 uF and 56k to ground.

Datasheet units, from the layout page's socket wiring: the second 12AY7's
+130 V plate is pin 1 (the 100k plate load is soldered across the socket from
pin 6 to pin 1, and a jumper takes pin 7 to pin 1), so the gain stage V2A is
unit 2 and the follower V2B unit 1. The 12AX7's +200 V driver plate is pin 1
and the +260 V cathodyne plate pin 6, so V3A is unit 2 and V3B unit 1. On the
input 12AY7 the bright volume control's coupler comes from pin 6, so V1A is
unit 1 and V1B unit 2.

It is not one of the lab's plotted tone networks; check_tonestack_wiring.py
walks it as the `split` kind the 5F4 draws (site/src/lib/corpus.js
TONE_STACK_GATE_EXTRAS).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e6a" / "schematic.kicad_sch"
s = Sch()


def series_hl(lib, ref, val, x, y, lx, ly):
    """series_h with authored lettering, for a body whose default slot is taken."""
    s.sym(lib, ref, val, x, y, rot=90, lx=lx, ly=ly)
    return (x - 3.81, x + 3.81)


# ---- V1 12AY7, two channels, shared 820R/250u cathode --------------------
# No grid stoppers on this drawing: each jack tip runs straight to its grid
# with a 1 MEG leak to ground.
for ch, (y, jack, gref, pref, plref, cref, vref, mref, unit) in enumerate([
        (92, "CH-A", "RG1", "V1A", "RL1", "CC1", "VR1", "RM1", 1),
        (126, "CH-B", "RG2", "V1B", "RL2", "CC2", "VR2", "RM2", 2)]):
    s.glabel(jack, 26, y, 180)
    t = s.triode(pref, "12AY7", 49.53, y, unit=unit)
    s.wire(26, y, t["g"][0], y)
    s.junction(t["g"][0] - 3.81, y)
    s.sym("R", gref, "1M", t["g"][0] - 3.81, y + 3.81)
    s.gnd(t["g"][0] - 3.81, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # coupler -> volume pot -> 270k mixer into the shared V2A grid line
    ty = y - 7.62 - 3.48                # plate stub tee
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", cref, ".02u", 64.77, ty)
    s.wire(crr, ty, 73.66, ty)
    s.sym("POT", vref, "1M vol", 73.66, ty + 3.81, lx=3.0, ly=5.5)
    s.gnd(73.66, ty + 7.62)         # cold lug: pot centre + 3.81, not + 7.62
    ml, mr = s.series_h("R", mref, "270k", 87.63, ty + 3.81)
    s.wire(78.74, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 91.44, ty + 3.81)
    s.wire(91.44, ty + 3.81, 91.44, 109)
    if ch == 0:
        # CBR: the drawing's .0001 from VR1's hot lug to its wiper — the
        # bright channel's bright cap.
        s.junction(73.66, ty)
        s.wire(73.66, ty, 73.66, ty - 4.5)
        bl, br = s.series_h("C", "CBR", "100p", 77.47, ty - 4.5)
        s.wire(br, ty - 4.5, br, ty + 3.81)
        s.junction(br, ty + 3.81)
s.junction(91.44, 109)

# shared cathode
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C1", "250u", 56.13, 140)

# ---- V2A gain + DC-coupled cathode follower ----------------------------
t2a = s.triode("V2A", "12AY7", 101.6, 109, lx=-9.2, ly=3.4, unit=2)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 118)
s.shunt_rc("RK2", "1.5k", "C2", "25u", 101.6, 118)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# RFB 10 MEG back to the V2A grid (~0 V DC) from the tone network's first
# node (the far side of C3), as the A-EE sheet draws it.
s.wire(91.44, 109, 91.44, 84)
fl, fr = s.series_h("R", "RFB", "10M", 120, 84)
s.wire(91.44, 84, fl, 84)
s.wire(fr, 84, 137, 84)
s.wire(137, 84, 137, 119.5)             # down to node N1 (crossings = no join)
# direct-coupled CF: grid from the plate stub tee
tee = 109 - 7.62 - 3.48
s.wire(101.6, tee, 108.9, tee)
s.junction(101.6, tee)
tcf = s.triode("V2B", "12AY7 CF", 116.84, 109, unit=1)
s.wire(108.9, tee, 108.9, 109)
s.wire(108.9, 109, tcf["g"][0], 109)
s.wire(116.84, 101.38, 116.84, 98.5)
s.glabel("B+4", 116.84, 98.5, 90)      # CF plate straight to the rail
s.wire(116.84, 116.62, 116.84, 119.5)
s.junction(116.84, 119.5)
s.sym("R", "RKCF", "100k", 116.84, 123.31)
s.gnd(116.84, 127.12)

# ---- tone network, fed from the follower's cathode (node A) --------------
#   treble: A -> C4 250 pF -> VR3; its far end -> C7 .01 -> ground; the wiper
#           is the driver's grid. C8 47 pF bridges the wiper and the C4 lug.
#   bass:   A -> C3 .1 -> N1 (RBL 220k to ground; RFB 10M back to V2A's grid)
#           -> RTS 220k -> VR4's WIPER (one end lug grounded outright, the
#           other through CBS .005 to ground) -> RTO 220k -> the Treble wiper.
s.wire(116.84, 119.5, 124.46, 119.5)
s.junction(124.46, 119.5)
s.wire(124.46, 119.5, 124.46, 94)       # node A up to the 250 pF branch
s.wire(124.46, 94, 126.19, 94)
tl, tr = s.series_h("C", "C4", "250p", 130, 94)
s.wire(tr, 94, 140, 94)
s.sym("POT", "VR3", "1M treb", 140, 97.81, lx=9.5, ly=-5.0)
s.sym("C", "C7", ".01u 400V", 140, 105.43)   # treble far end -> .01 -> ground
s.gnd(140, 109.24)
# treble wiper -> the driver's grid, down the right side
s.wire(145.08, 97.81, 163, 97.81)
s.wire(163, 97.81, 163, 126)
# C8: lettered 47 MMF on the layout page, across the Treble control from its
# wiper to the lug C4 feeds. The schematic page does not draw it.
s.junction(140, 94)
s.wire(140, 94, 140, 90)
c8l, c8r = s.series_h("C", "C8", "47p", 143.81, 90)
s.wire(c8r, 90, c8r, 97.81)
s.junction(c8r, 97.81)
# bass branch: A -> C3 .1 -> N1
c3l, c3r = s.series_h("C", "C3", ".1u 200V", 130, 119.5)
s.wire(124.46, 119.5, c3l, 119.5)
s.wire(c3r, 119.5, 137, 119.5)
s.junction(137, 119.5)                  # N1: 220k leak + 10M feedback
s.sym("R", "RBL", "220k", 137, 123.31, lx=-6.5, ly=-1.6)
s.gnd(137, 127.12)
sl, sr = series_hl("R", "RTS", "220k", 143, 119.5, lx=-3.5, ly=2.2)
s.wire(137, 119.5, sl, 119.5)
s.wire(sr, 119.5, 149, 119.5)
s.junction(149, 119.5)                  # N2: injected at the bass wiper
s.wire(149, 119.5, 149, 130)
s.sym("POT", "VR4", "1M bass", 143.92, 130, lx=7.6, ly=-2.5)
s.wire(143.92, 126.19, 140, 126.19)     # one end lug grounded outright
s.wire(140, 126.19, 140, 128)
s.gnd(140, 128)
s.sym("C", "CBS", ".005u", 143.92, 137.62)  # the other end lug -> .005 -> gnd
s.gnd(143.92, 141.43)
# N2 -> 220k -> the Treble wiper (the driver's grid)
rol, ror = s.series_h("R", "RTO", "220k", 156, 119.5)
s.wire(149, 119.5, rol, 119.5)
s.wire(ror, 119.5, 163, 119.5)
s.junction(163, 119.5)

# ---- phase inverter: driver (V3A) + split-load cathodyne (V3B) ----------
bt = s.triode("V3A", "12AX7", 176.53, 126, lx=8.8, unit=2)   # driver (drawn below)
s.wire(163, 126, bt["g"][0], 126)
tp = s.triode("V3B", "12AX7", 176.53, 92, unit=1)    # cathodyne (drawn above)
s.plate_load("RLD", "100k", bt["p"], "B+3")
s.plate_load("RLA", "56k", tp["p"], "B+3")
# driver cathode: 1.5k to ground; the 20k NFB and the presence land here
s.sym("R", "RK3", "1.5k", 176.53, 137.43)
s.gnd(176.53, 141.24)
# driver plate tee -> CC3 0.02 -> cathodyne grid (left side, up to y=92)
s.junction(176.53, 114.9)
c3cl, c3cr = s.series_h("C", "CC3", ".02u", 168, 114.9)
s.wire(c3cr, 114.9, 176.53, 114.9)
s.wire(c3cl, 114.9, 160, 114.9)
s.wire(160, 114.9, 160, 92)
s.wire(160, 92, tp["g"][0], 92)
# cathodyne grid leak RGPI 1M -> the 1.5k/56k junction
s.junction(160, 105)
gbl, gbr = s.series_h("R", "RGPI", "1M", 167.5, 105)
s.wire(160, 105, gbl, 105)
s.wire(gbr, 105, 172.5, 105)
s.wire(172.5, 105, 172.5, 109.62)
s.wire(172.5, 109.62, 184.5, 109.62)
# cathodyne cathode chain: 1.5k -> J -> 56k -> gnd (beside the tube)
s.wire(176.53, 99.62, 176.53, 102)
s.wire(176.53, 102, 184.5, 102)
s.sym("R", "RKA", "1.5k", 184.5, 105.81, lx=2.0)
s.junction(184.5, 109.62)
s.sym("R", "RKB", "56k", 184.5, 113.43, lx=2.0)
s.gnd(184.5, 117.24)

# ---- negative feedback + presence, both on the driver's cathode ---------
# 20k from the speaker line; the 5k Presence control's end lug on the same
# node, its wiper to ground through 0.1 uF.
s.junction(176.53, 133.62)
s.wire(176.53, 133.62, 152, 133.62)
s.wire(152, 133.62, 152, 145)
s.junction(152, 145)
nl, nr = s.series_h("R", "RNF", "20k", 136, 145)
s.wire(nr, 145, 152, 145)
s.wire(124, 145, nl, 145)
s.glabel("SPKR", 124, 145, 180)
s.sym("POT", "VR5", "5k pres", 152, 148.81, lx=4.4, ly=-5.5)
s.wire(157.08, 148.81, 166, 148.81)          # presence wiper -> 0.1 uF -> gnd
# The far lug strapped to the wiper, as the layout page wires it (the schematic
# page leaves it open; it carries no current either way).
s.wire(152, 152.62, 152, 154.2)
s.wire(152, 154.2, 160, 154.2)
s.wire(160, 154.2, 160, 148.81)
s.junction(160, 148.81)
s.sym("C", "CPR", ".1u 200V", 166, 152.62)
s.gnd(166, 156.43)

# ---- 6L6G pair, fixed bias ----------------------------------------------
# V4 is driven from the cathodyne's PLATE (C5, .1-400), V5 from its CATHODE
# (C6, .1-200). Each coupler lands on the junction where the 220k leak from
# the -42 V supply returns, and the 1.5k stopper runs from there to the grid:
# the schematic page draws the leak on the coupler side, and the layout page
# mounts the stopper on the socket from that junction (pin 6) to the grid.
for y, pref, cref, cval, glref, gstop in [
        (84, "V4", "C5", ".1u 400V", "RGL1", "R5s"),
        (136, "V5", "C6", ".1u 200V", "RGL2", "R6s")]:
    if y == 84:
        s.wire(176.53, 80.9, 194.31, 80.9)     # cathodyne plate tee
        s.junction(176.53, 80.9)
        cl, crr = s.series_h("C", cref, cval, 198.12, 80.9)
        s.wire(crr, 80.9, 205.74, 80.9)
        s.wire(205.74, 80.9, 205.74, 84)
        gy = 84
    else:
        s.junction(184.5, 102)                # cathodyne cathode node
        cl, crr = s.series_h("C", cref, cval, 191, 102)
        s.wire(184.5, 102, cl, 102)
        s.wire(crr, 102, 196, 102)
        s.wire(196, 102, 196, 136)
        s.wire(196, 136, 205.74, 136)
        gy = 136
    p = s.pentode(pref, "6L6G", 221.6, gy)
    gl2, gr2 = s.series_h("R", gstop, "1.5k", p["g1"][0] - 3.81, gy)
    s.wire(205.74, gy, gl2, gy)
    s.junction(205.74, gy)
    s.sym("R", glref, "220k", 205.74, gy + 3.81, lx=-9.4, ly=1.0)
    s.wire(205.74, gy + 7.62, 205.74, gy + 10.16)
    s.glabel("-42V", 205.74, gy + 10.16, 270)
    # screen straight to B+2, beside the OT centre tap (no screen resistor)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(221.6, p["k"][1] + 0)

# ---- output transformer -------------------------------------------------
s.sym("OT_PP", "T3", "no number printed", 249.5, 110)
s.wire(221.6, 84 - 0.635 - 7.62, 221.6, 73.5)
s.wire(221.6, 73.5, 240.61, 73.5)
s.wire(240.61, 73.5, 240.61, 104.92)
s.wire(221.6, 136 - 0.635 - 7.62, 221.6, 126.5)
s.wire(221.6, 126.5, 235.7, 126.5)
s.wire(235.7, 126.5, 235.7, 115.08)
s.wire(235.7, 115.08, 240.61, 115.08)
s.wire(240.61, 110, 238.07, 110)
s.wire(238.07, 110, 238.07, 107)
s.glabel("B+2", 238.07, 107, 90)       # centre tap AFTER the choke
s.wire(258.39, 107.46, 260.93, 107.46)
s.glabel("SPKR", 260.93, 107.46, 0)
s.wire(258.39, 112.54, 260.93, 112.54)
s.glabel("GND", 260.93, 112.54, 0)

# ---- power supply: two 5U4GA in parallel, choke, two droppers ------------
# Each HT end feeds one plate of EACH rectifier (the drawing's parallel pair);
# the four sections' cathodes are the two filaments, tied together as B+.
s.text("Two 5U4GA in parallel · choke · bias: 3300R + selenium rect -> -42V", 85, 157.5, 1.4)
for x, ref, ht in [(30.48, "V6A", "HT_A"), (46.99, "V6B", "HT_B"),
                   (63.5, "V7A", "HT_A"), (80.01, "V7B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5U4GA", x, 167.78, lx=5.5, ly=-1.0)
    s.wire(x, 175.4, x, 177.8)
s.wire(30.48, 177.8, 95.25, 177.8)
for x in (46.99, 63.5, 80.01):
    s.junction(x, 177.8)
s.junction(88.9, 177.8)
s.sym("C", "C9", "16u", 88.9, 181.61)
s.gnd(88.9, 185.42)
s.glabel("B+1", 95.25, 177.8, 0)
s.wire(95.25, 177.8, 97.79, 177.8)
s.sym("CHOKE", "L1", "no number printed", 105.41, 177.8, lx=-16.0, ly=-7.0)
s.wire(113.03, 177.8, 129.19, 177.8)
s.junction(116.84, 177.8)
s.glabel("B+2", 116.84, 175.26, 90)
s.wire(116.84, 175.26, 116.84, 177.8)
s.junction(120.65, 177.8)
s.sym("C", "C10", "16u", 120.65, 181.61)
s.gnd(120.65, 185.42)
s.junction(125.73, 177.8)
s.sym("C", "C11", "16u", 125.73, 181.61)
s.gnd(125.73, 185.42)
l, r = s.series_h("R", "RD1", "10k", 133, 177.8)
s.wire(r, 177.8, 146.19, 177.8)
s.junction(139.7, 177.8)
s.glabel("B+3", 139.7, 175.26, 90)
s.wire(139.7, 175.26, 139.7, 177.8)
s.junction(143.51, 177.8)
s.sym("C", "C12", "16u", 143.51, 181.61)
s.gnd(143.51, 185.42)
l, r = s.series_h("R", "RD2", "10k", 150, 177.8)
s.wire(r, 177.8, 161.29, 177.8)
s.junction(156.21, 177.8)
s.glabel("B+4", 156.21, 175.26, 90)
s.wire(156.21, 175.26, 156.21, 177.8)
s.sym("C", "C13", "8u", 161.29, 181.61)
s.gnd(161.29, 185.42)

# bias supply: HT tap -> 3300 -> selenium -> -42V node, 100u and 56k to
# ground. The rectifier's + end faces the 3300 and its - end the -42 V node,
# as both pages letter it.
s.glabel("HT_TAP", 150.1, 160.72, 180)
l, r = series_hl("R", "RB1", "3.3k", 155.0, 160.72, lx=-3.2, ly=2.2)
s.wire(150.1, 160.72, l, 160.72)
s.wire(r, 160.72, 165.92, 160.72)
s.sym("DIODE_SS", "D1", "SEL", 171.0, 160.72, lx=-1.0, ly=-4.2, rot=180, label_rot=0)
s.wire(176.08, 160.72, 183.12, 160.72)
s.junction(178.04, 160.72)
s.sym("R", "RB2", "56k", 178.04, 164.53, lx=-5.5, ly=-1.6)
s.gnd(178.04, 168.34)
s.junction(180.58, 160.72)
s.sym("C", "C14", "100u 25V", 180.58, 164.53, lx=2.2)
s.gnd(180.58, 168.34)
s.glabel("-42V", 183.12, 160.72, 0)

# ---- power transformer ------------------------------------------------
# The drawing takes the bias feed from a fourth HT-winding terminal between
# one end and the centre tap. The 5 V and 6.3 V windings, mains switch, fuse,
# ground switch, standby switch and the two 0.05 uF bypass caps are not drawn.
pt = s.pt("T1", "no number printed", 205, 176, tap=True)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS N", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 12, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 12, pt["ht_a"][1], 0)
s.wire(pt["tap"][0], pt["tap"][1], pt["tap"][0] + 2, pt["tap"][1])
s.glabel("HT_TAP", pt["tap"][0] + 2, pt["tap"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 12, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 12, pt["ht_ct"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)

s.note("No grid stoppers on this drawing; each jack tip runs straight to its grid")
s.note("C8 (47 pF) is lettered on the layout page across the Treble control; the schematic page does not draw it")
s.write(OUT, [
    "Heaters, mains switch, fuse, ground and standby switches and the two 0.05 uF bypass caps omitted — see the sources list",
])
print(f"wrote {OUT}")
