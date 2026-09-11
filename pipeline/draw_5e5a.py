#!/usr/bin/env python3
"""Generate amps/5e5a/schematic.kicad_sch from the stage-template library.

Values and topology per the published Fender 5E5-A (J-EE) sheet set: the
schematic page for the circuit, the layout page for what the schematic page
leaves unlettered (the interstage coupler's value, the socket pins each stage
uses). Re-read 2026-09-10 at the PDF's own 1506 x 864: V2 is a gain stage
DC-coupled into a cathode follower, and the tone network hangs off the
follower's cathode (see amps/5e5a/notes.md). The circuit is redrawn from the
extracted component list, not traced.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e5a" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, two channels, shared 820R/dual-25u cathode ----------------
for ch, (y, jack, gref, pref, plref, cref, vref, mref) in enumerate([
        (92, "INST", "RG1", "V1A", "RL1", "C5", "VR1", "RMX1"),
        (126, "MIC", "RG2", "V1B", "RL2", "C6", "VR2", "RMX2")]):
    s.glabel(jack, 26, y, 180)
    s.wire(26, y, 30.48, y)
    l, r = s.series_h("R", f"R{ch + 1}s", "68k", 34.29, y)
    s.wire(30.48, y, l, y)
    t = s.triode(pref, "12AY7", 49.53, y)
    s.wire(r, y, t["g"][0], y)
    # The 1M grid leak hangs from the JACK-1 tip node, jack side of the 68k
    # stopper, as the factory sheet draws it (jack 1 tip -> 1 MEG -> ground;
    # the stoppers run from the jack tips to the grid). The stopper carries
    # no DC, so the netlist sees one node either way.
    s.junction(l, y)
    s.sym("R", gref, "1M", l, y + 3.81, lx=2.2, ly=0.0)
    s.gnd(l, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # coupler -> volume pot -> 270k mixer into the shared V2 grid line
    ty = y - 7.62 - 3.48
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", cref, ".02u", 64.77, ty)
    s.wire(crr, ty, 73.66, ty)
    s.sym("POT", vref, "1M vol", 73.66, ty + 3.81)
    s.gnd(73.66, ty + 7.62)         # cold lug: pot centre + 3.81, not + 7.62
    s.wire(78.74, ty + 3.81, 81.28, ty + 3.81)
    ml, mr = s.series_h("R", mref, "270k", 85.09, ty + 3.81)
    s.wire(81.28, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 91.44, ty + 3.81)
    s.wire(91.44, ty + 3.81, 91.44, 109)
    if ch == 0:
        # Bright cap: the sheet prints .0001 from the INST volume's hot lug to
        # its wiper, on this channel only — the MIC volume has none. It rides
        # above the pot and drops onto the wiper lead at RMX1's pin.
        s.wire(73.66, ty, 73.66, ty - 3.81)
        s.junction(73.66, ty)
        bl, br = s.series_h("C", "C16", "100p", 77.47, ty - 3.81)
        s.wire(br, ty - 3.81, br, ty + 3.81)
        s.junction(br, ty + 3.81)
s.junction(91.44, 109)

# shared V1 cathode: both triodes' K pins bus together into one 820R/25+25u can
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C4", "25u+25u", 56.13, 140)

# ---- V2A gain stage + DC-coupled cathode follower V2B, one 12AY7 ----------
# Both sections are used. The layout page puts the gain stage on socket pins
# 1-2-3 (datasheet unit 2) and the follower on 6-7-8 (unit 1): V2A's 100k
# plate load is soldered across the socket from pin 6 — the follower's plate,
# on the rail — to pin 1, with a strap from pin 1 to the follower's grid, pin 7.
t2a = s.triode("V2A", "12AY7", 101.6, 109, unit=2)
s.wire(91.44, 109, t2a["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 118)
s.shunt_rc("RK2", "1.5k", "C4b", "25u", 101.6, 118)
s.plate_load("RL3", "100k", t2a["p"], "B+4")
# direct-coupled follower: grid from the plate stub's top, where RL3 starts
tee = 109 - 7.62 - 3.48
s.junction(101.6, tee)
s.wire(101.6, tee, 112.4, tee)
t2b = s.triode("V2B", "12AY7", 124.46, 109, unit=1)
s.wire(112.4, tee, 112.4, 109)
s.wire(112.4, 109, t2b["g"][0], 109)
s.wire(124.46, 101.38, 124.46, 98.5)
s.glabel("B+4", 124.46, 98.5, 90)      # follower plate straight to the rail
s.wire(124.46, 116.62, 124.46, 119.38)
s.junction(124.46, 119.38)
s.sym("R", "RKCF", "100k", 124.46, 123.19)
s.gnd(124.46, 127.0)

# ---- tone network off the follower's cathode: the 5F4's split circuit ----
# Treble: 250 pF from the follower's cathode to the Treble pot, whose other
# end is bled to ground through 0.01 uF; its wiper is the network's output.
# Bass: a 0.1 uF coupler into the bass branch — 220k to ground, then 100k into
# the Bass pot's WIPER (one end lug grounded, the other through 0.005 uF) —
# and 220k from that wiper to the output. The 5 MEG from V2A's grid returns to
# the bass branch, on the far side of the coupler.
s.wire(124.46, 119.38, 147.32, 119.38)     # the follower's cathode bus
s.junction(147.32, 119.38)
s.sym("C", "C8", "250p", 147.32, 115.57, lx=-7.0)          # pins 111.76 / 119.38
s.sym("POT", "VR4", "1M treble", 147.32, 107.95, lx=-10.0, ly=-1.5)
s.sym("C", "C7", ".01u 400V", 147.32, 100.33, lx=-10.0)    # pins 96.52 / 104.14
s.gnd(147.32, 96.52, 90)
# bass branch
c14l, c14r = s.series_h("C", "C14", ".1u 200V", 156.21, 119.38)
s.wire(147.32, 119.38, c14l, 119.38)
s.wire(c14r, 119.38, 167.64, 119.38)
s.junction(163.83, 119.38)                 # TB: the 5 MEG lands here
s.junction(167.64, 119.38)
s.sym("R", "RSH", "220k", 167.64, 123.19, lx=-6.5, ly=-0.5)
s.gnd(167.64, 127.0)
rsl_l, rsl_r = s.series_h("R", "RSL", "100k", 173.99, 119.38)
s.wire(167.64, 119.38, rsl_l, 119.38)
rsr_l, rsr_r = s.series_h("R", "RSR", "220k", 185.42, 119.38)
s.wire(rsl_r, 119.38, rsr_l, 119.38)
s.junction(rsr_l, 119.38)                  # TW: the Bass pot's wiper node
s.wire(rsr_l, 119.38, rsr_l, 132.08)
s.sym("POT", "VR3", "1M bass", rsr_l - 5.08, 132.08, lx=4.4, ly=2.0)
s.gnd(rsr_l - 5.08, 128.27, 90)            # one end lug grounded outright
s.sym("C", "C15", ".005u 600V", rsr_l - 5.08, 139.7, lx=-11.0)   # the other through .005
s.gnd(rsr_l - 5.08, 143.51)
# output: the Treble wiper and RSR meet, then run to the driver's grid
s.wire(152.4, 107.95, 194.31, 107.95)
s.wire(194.31, 107.95, 194.31, 126)
s.wire(rsr_r, 119.38, 194.31, 119.38)
s.junction(194.31, 119.38)

# RF1, the 5 MEG: from the mixing node (V2A's grid) over the top of the stage
# and down onto the bass branch.
s.wire(91.44, 84.71, 91.44, 66)
s.junction(91.44, 84.71)
rfl, rfr = s.series_h("R", "RF1", "5M", 127.0, 66)
s.wire(91.44, 66, rfl, 66)
s.wire(rfr, 66, 163.83, 66)
s.wire(163.83, 66, 163.83, 119.38)

# ---- driver (V3A) + split-load cathodyne (V3B), one 12AX7 ----------------
# The layout page puts the driver on socket pins 1-2-3 (unit 2) and the
# cathodyne on 6-7-8 (unit 1): the driver's plate eyelet (+190 V) runs to
# pin 1 and the Treble wiper's lead to pin 2.
DX = 12.7                 # this block and everything right of it, as drawn
X3 = 200 + DX
bt = s.triode("V3A", "12AX7", X3, 126, lx=8.8, unit=2)
s.wire(194.31, 126, bt["g"][0], 126)
tp = s.triode("V3B", "12AX7", X3, 92, unit=1)
s.plate_load("RL4", "100k", bt["p"], "B+3")
s.plate_load("RL5", "56k", tp["p"], "B+3")
s.sym("R", "RK3", "1.5k", X3, 137.43)
s.gnd(X3, 141.24)
# driver plate tee -> C1 .02 -> cathodyne grid
s.junction(X3, 114.9)
c1l, c1r = s.series_h("C", "C1", ".02u", 191 + DX, 114.9)
s.wire(c1r, 114.9, X3, 114.9)
s.wire(c1l, 114.9, 184 + DX, 114.9)
s.wire(184 + DX, 114.9, 184 + DX, 92)
s.wire(184 + DX, 92, tp["g"][0], 92)
# cathodyne grid leak RGPI 1M -> the 1.5k/56k junction
s.junction(184 + DX, 105)
gbl, gbr = s.series_h("R", "RGPI", "1M", 191.5 + DX, 105)
s.wire(184 + DX, 105, gbl, 105)
s.wire(gbr, 105, 196.5 + DX, 105)
s.wire(196.5 + DX, 105, 196.5 + DX, 109.62)
s.wire(196.5 + DX, 109.62, 208.5 + DX, 109.62)
# cathodyne cathode chain: RKA 1.5k -> J -> RKB 56k -> gnd
s.wire(X3, 99.62, X3, 102)
s.wire(X3, 102, 208.5 + DX, 102)
s.sym("R", "RKA", "1.5k", 208.5 + DX, 105.81, lx=2.0)
s.junction(208.5 + DX, 109.62)
s.sym("R", "RKB", "56k", 208.5 + DX, 113.43, lx=2.0)
s.gnd(208.5 + DX, 117.24)

# ---- negative feedback + presence, both on the driver's cathode ----------
# The J-EE sheet ties the 100k from the speaker and the 5k Presence pot to
# V3A's cathode dot (+1.6 V), not to its grid; the pot's wiper bleeds to
# ground through 0.1 uF. The schematic page leaves the pot's third lug open;
# the layout page straps it to the wiper, and that is how it is drawn here.
s.junction(X3, 133.62)
s.wire(X3, 133.62, 200.66, 133.62)
s.wire(200.66, 133.62, 200.66, 149.86)
s.junction(200.66, 149.86)
nl, nr = s.series_h("R", "RNF", "100k", 192.4, 149.86)
s.wire(nr, 149.86, 200.66, 149.86)
s.wire(184.15, 149.86, nl, 149.86)
s.glabel("SPKR", 184.15, 149.86, 180)
s.sym("POT", "VR5", "5k pres", 200.66, 153.67, lx=-10.5, ly=1.2)   # top pin (200.66, 149.86)
c9l, c9r = s.series_h("C", "C9", ".1u 200V", 210.82, 153.67)
s.wire(205.74, 153.67, c9l, 153.67)        # wiper -> C9 -> ground
s.gnd(c9r, 153.67, 0)
s.wire(200.66, 157.48, 205.74, 157.48)     # free end lug strapped to the wiper
s.wire(205.74, 157.48, 205.74, 153.67)
s.junction(205.74, 153.67)

# ---- 6L6GB pair, fixed bias ----------------------------------------------
for y, pref, cref, glref, gstop in [(84, "V4", "C2", "RGL1", "R5s"),
                                     (136, "V5", "C3", "RGL2", "R6s")]:
    if y == 84:
        cl, crr = s.series_h("C", cref, ".1u", 222 + DX, 80.9)
        s.wire(X3, 80.9, cl, 80.9)     # `218` stopped 0.19 mm short of C2
        s.junction(X3, 80.9)
        s.wire(crr, 80.9, 229.5 + DX, 80.9)
        s.wire(229.5 + DX, 80.9, 229.5 + DX, 84)
        gy = 84
    else:
        s.junction(208.5 + DX, 102)
        cl, crr = s.series_h("C", cref, ".1u", 214.5 + DX, 102)
        s.wire(208.5 + DX, 102, cl, 102)
        s.wire(crr, 102, 219.5 + DX, 102)
        s.wire(219.5 + DX, 102, 219.5 + DX, 136)
        s.wire(219.5 + DX, 136, 229.5 + DX, 136)
        gy = 136
    # The 220k leak returns on the GRID side of the stopper. netlist.cir MODELS
    # the stopper (R5s NG61 G61) and puts the leak on G61; at x=232 it sat on
    # the coupler side, i.e. the wrong node.
    p = s.pentode(pref, "6L6GB", 245.3 + DX, gy)
    gl2, gr2 = s.series_h("R", gstop, "1.5k", p["g1"][0] - 3.81, gy)
    s.wire(229.5 + DX, gy, gl2, gy)
    s.junction(gr2, gy)
    s.sym("R", glref, "220k", gr2, gy + 3.81, lx=-9.4, ly=1.0)
    s.wire(gr2, gy + 7.62, gr2, gy + 10.16)
    s.glabel("-32V", gr2, gy + 10.16, 270)
    # screen straight to B+2 (no screen resistor on the sheet)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(245.3 + DX, p["k"][1])

# ---- output transformer ---------------------------------------------------
# Every OT lead starts on the pin the helper returns. The hand-typed
# 264.3 / 282.1 were 0.01 mm off their pins, which left both 6L6 plates, the
# centre tap and the speaker jack wired to nothing at all.
ot = s.ot_pp("T2", "~4.3k:8", 273.2 + DX, 110)
s.wire(245.3 + DX, 84 - 0.635 - 7.62, 245.3 + DX, 73.5)
s.wire(245.3 + DX, 73.5, ot["pri_a"][0], 73.5)
s.wire(ot["pri_a"][0], 73.5, ot["pri_a"][0], ot["pri_a"][1])
s.wire(245.3 + DX, 136 - 0.635 - 7.62, 245.3 + DX, 126.5)
s.wire(245.3 + DX, 126.5, 259.4 + DX, 126.5)
s.wire(259.4 + DX, 126.5, 259.4 + DX, ot["pri_b"][1])
s.wire(259.4 + DX, ot["pri_b"][1], ot["pri_b"][0], ot["pri_b"][1])
s.wire(ot["ct"][0], ot["ct"][1], 261.77 + DX, 110)
s.wire(261.77 + DX, 110, 261.77 + DX, 107)
s.glabel("B+1", 261.77 + DX, 107, 90)
jk = s.jack("SPKR", "15in spkr", 291 + DX, 110)
# the speaker node carries the SPKR flag the feedback resistor returns to
spk = (ot["sec_h"][0] + jk["tip"][0]) / 2
s.wire(ot["sec_h"][0], ot["sec_h"][1], spk, ot["sec_h"][1])
s.wire(spk, ot["sec_h"][1], jk["tip"][0], jk["tip"][1])
s.glabel("SPKR", spk, ot["sec_h"][1], 90)
s.wire(ot["sec_c"][0], ot["sec_c"][1], jk["sleeve"][0], jk["sleeve"][1])
s.text("Extra 8-ohm speaker jack (parallel) omitted — annotation only", 250 + DX, 122, 1.0)

# ---- power supply + bias ---------------------------------------------------
s.text("Power — 5U4GA rectifier; choke DCR ~110 R (est.); bias: 10k + selenium rect, 100uF/56k -> -32V", 25, 158, 1.4)
lp = s.lamp("PL1", "pilot", 30, 172, lx=-9.5, ly=-1)
s.glabel("6.3V", lp["hi"][0], lp["hi"][1] - 2.5, 90)
s.wire(lp["hi"][0], lp["hi"][1] - 2.5, lp["hi"][0], lp["hi"][1])
s.gnd(lp["lo"][0], lp["lo"][1] + 2.5)
s.wire(lp["lo"][0], lp["lo"][1], lp["lo"][0], lp["lo"][1] + 2.5)
for x, ref, ht in [(41.91, "V6A", "HT_A"), (54.61, "V6B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5U4GA", x, 167.78, lx=(-11.4 if ref == "V6A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(41.91, 177.8, 82.55, 177.8)
s.junction(54.61, 177.8)
# the first filter can sits on the rectifier output, ahead of the choke
s.junction(69.85, 177.8)
s.sym("C", "C17", "16u", 69.85, 181.61)
s.gnd(69.85, 185.42)
s.glabel("B+1", 82.55, 177.8, 0)
s.wire(82.55, 177.8, 85.09, 177.8)
l, r = s.series_h("R", "RCHOKE", "~110 (choke)", 92.71, 177.8)
s.wire(85.09, 177.8, l, 177.8)
s.wire(r, 177.8, 100.33, 177.8)
s.wire(100.33, 177.8, 111.76, 177.8)
s.junction(105.41, 177.8)
s.glabel("B+2", 105.41, 175.26, 90)
s.wire(105.41, 175.26, 105.41, 177.8)
s.junction(108.86, 177.8)
s.sym("C", "C10", "16u", 108.86, 181.61)
s.gnd(108.86, 185.42)
l, r = s.series_h("R", "RD1", "10k", 115.57, 177.8)
s.wire(r, 177.8, 127, 177.8)
s.junction(121.92, 177.8)
s.glabel("B+3", 121.92, 175.26, 90)
s.wire(121.92, 175.26, 121.92, 177.8)
s.junction(124.46, 177.8)
s.sym("C", "C11", "16u", 124.46, 181.61)
s.gnd(124.46, 185.42)
l, r = s.series_h("R", "RD2", "10k", 130.81, 177.8)
s.wire(r, 177.8, 142.24, 177.8)
s.junction(137.16, 177.8)
s.glabel("B+4", 137.16, 175.26, 90)
s.wire(137.16, 175.26, 137.16, 177.8)
s.sym("C", "C12", "8u", 142.24, 181.61)
s.gnd(142.24, 185.42)
# bias supply: winding bias tap -> 10k -> selenium -> 100uF ‖ 56k -> -32V node
# (the factory sheet: "10 K" from the tap into the cell, "56 K" across the
# "100-25" can; the rectifier hangs on the tap, not on an HT end / plate)
s.glabel("HT_TAP", 150.1, 160.72, 180)
l, r = s.series_h("R", "RB1", "10k", 157, 160.72)
s.wire(150.1, 160.72, l, 160.72)
s.wire(r, 160.72, 162.42, 160.72)
s.sym("DIODE_SS", "D1", "SEL", 167.5, 160.72, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(172.58, 160.72, 183.12, 160.72)
s.junction(178.04, 160.72)
s.sym("R", "RB2", "56k", 178.04, 164.53)
s.gnd(178.04, 168.34)
s.junction(180.58, 160.72)
s.sym("C", "C13", "100u", 180.58, 164.53, lx=2.2)
s.gnd(180.58, 168.34)
s.glabel("-32V", 183.12, 160.72, 0)

# ---- power transformer ------------------------------------------------
# The 8087-family transformer brings out a BIAS TAP on the HT winding between
# one end and the centre tap — the lead the layout letters RED-BLUE — and the
# factory sheet draws the bias feed from that fourth winding terminal, never
# from a rectifier plate. Mains switch, fuse and the 5 V / 6.3 V windings are
# not drawn.
pt = s.pt("T1", "PT", 205, 176, tap=True)
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

s.note("The Presence pot's free end lug is drawn strapped to its wiper, as the layout page wires it; the schematic page leaves it open")
s.write(OUT, [
    "Heaters, mains switches, ground switch, fuse and standby omitted — see the parts list and the sources list",
])
print(f"wrote {OUT}")
