#!/usr/bin/env python3
"""Generate amps/5e6a/schematic.kicad_sch from the stage-template library.

Values per the published 5E6-A (A-EE) drawing (see amps/5e6a/meta.yaml). Redrawn
from a fresh lug-level read of the high-resolution Schematic Heaven scan this
pass (2026-08-08) -- the same drawing code (A-EE), cross-checked against the
El34World copy -- which resolved most of what this corpus's data core had left
as "annotation only, not re-read at lug level" (see notes.md) and corrected two
mis-readings from the prior pass:

  - the 10 MEG resistor bom.yaml called a "channel-linking resistor between the
    two input jacks" is actually a light V2 plate-to-grid feedback/self-bias
    resistor (RFB below) -- its left end lands on the post-mixer V2 grid node,
    its right end on V2's own plate, not on the input jacks at all;
  - the 100 pF mica cap bom.yaml paired with that 10 MEG is its own, unrelated
    component: a channel-jumper cap (CJ1) bridging the two channels' post-
    coupler nodes, BEFORE two 100 k padding resistors (RP1/RP2, not previously
    catalogued at all) that feed each channel's 1 M volume pot.

The presence/bass/treble network's own internal ladder (which lug of the bass
pot ties to the fixed 220 k/0.005 uF shelf vs. the shared presence/NFB bus) is
drawn as read this pass but keeps a documented residual uncertainty -- see the
text annotation on the drawing and notes.md. It is not one of
site/src/lib/corpus.js's plottable TONE_STACK_SPECS shapes (neither the 3-knob
FMV ladder nor the 2-knob AB763-style network), so it is not registered there:
nothing to gate, nothing plotted.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e6a" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, two channels, no grid stoppers, shared 820R/250u cathode --
chan_nodes = []
for ch, (y, jack, gref, pref, plref, ccref, rpref, vref) in enumerate([
        (92, "CH-A", "RG1", "V1A", "RL1", "CC1", "RP1", "VR1"),
        (126, "CH-B", "RG2", "V1B", "RL2", "CC2", "RP2", "VR2")]):
    s.glabel(jack, 26, y, 180)
    t = s.triode(pref, "12AY7", 49.53, y)
    s.wire(26, y, t["g"][0], y)
    s.junction(t["g"][0] - 3.81, y)
    s.sym("R", gref, "1M", t["g"][0] - 3.81, y + 3.81)
    s.gnd(t["g"][0] - 3.81, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+3")
    # coupler -> [jumper cap tees here] -> 100k pad -> 1M volume pot -> 270k mixer
    ty = y - 7.62 - 3.48
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", ccref, ".02u", 64.77, ty)
    s.wire(crr, ty, 69, ty)
    chan_nodes.append((69, ty))
    pl, pr = s.series_h("R", rpref, "100k", 74, ty)
    s.wire(69, ty, pl, ty)
    s.wire(pr, ty, 81.28, ty)
    s.sym("POT", vref, "1M vol", 81.28, ty + 3.81)
    s.gnd(81.28, ty + 11.43)
    s.wire(86.36, ty + 3.81, 88.9, ty + 3.81)
    ml, mr = s.series_h("R", f"RM{ch + 1}", "270k", 92.71, ty + 3.81)
    s.wire(88.9, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 99.06, ty + 3.81)
    s.wire(99.06, ty + 3.81, 99.06, 109)
s.junction(99.06, 109)
# channel-jumper cap: bridges the two channels' post-coupler nodes directly
s.wire(chan_nodes[0][0], chan_nodes[0][1], chan_nodes[0][0], (chan_nodes[0][1] + chan_nodes[1][1]) / 2 - 3.81)
s.sym("C", "CJ1", "100p", chan_nodes[0][0], (chan_nodes[0][1] + chan_nodes[1][1]) / 2)
s.wire(chan_nodes[0][0], (chan_nodes[0][1] + chan_nodes[1][1]) / 2 + 3.81, chan_nodes[1][0], chan_nodes[1][1])
s.note("No grid stoppers on this drawing (unlike the 5F6/5F6-A's 68k); CJ1 jumpers the two channels")

# shared cathode
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C1", "250u", 56.13, 140)

# ---- V2 12AY7, single-section extra gain stage ---------------------------
# Grid = the two-channel mixer node. RFB (10 MEG, drawn as a loop above the
# tube on the A-EE sheet) ties this SAME node to V2's own plate -- a very
# light plate-to-grid feedback/self-bias path; the parallel mixer path to
# ground (through the 1 M volume-pot bodies) still sets the DC operating
# point, so netlist.cir's RG3 1 MEG-to-ground approximation is undisturbed.
t2 = s.triode("V2", "12AY7", 109.22, 109)
s.wire(99.06, 109, t2["g"][0], 109)
s.wire(109.22, 116.62, 109.22, 118)
s.shunt_rc("RK2", "1.5k", "C2", "25u", 109.22, 118)
s.plate_load("RL3", "100k", t2["p"], "B+3")
platetee = 109 - 7.62 - 3.48
s.wire(109.22, platetee, 109.22, 88)
s.wire(109.22, 88, 99.06, 88)
s.wire(99.06, 88, 99.06, 109)
fl, fr = s.series_h("R", "RFB", "10M", 103.5, 88)
s.note('RFB reads as a plate-to-grid loop on the A-EE sheet (light self-bias/NFB); netlist.cir omits it -- negligible at 10 Mohm beside the 100 kohm plate load')

# ---- tone network: bass shelf, presence/NFB bus, treble rheostat ---------
# Read off the Schematic Heaven A-EE scan this pass (2026-08-08). Node M is
# V2's own plate; TS2 is the bass-pot wiper junction, fed from M through RTS.
# VR4's hot lug rides the shared presence/NFB bus (fed by RNF from the
# speaker node, this family's usual feedback take-off); its cold lug feeds
# the fixed RBS/CBS shelf to ground -- a plain 3-terminal divider, not a
# rheostat. A residual uncertainty from this pass: which of VR4's two end
# lugs is "hot" (NFB bus) vs "cold" (shelf) is drawn as read but the two
# lugs sit close together on the scan; a dedicated lug-by-lug re-check (the
# kind amps/5f6/5f6a got 2026-08-03) would firm this up before verified.
mx = 147.32
s.wire(109.22, platetee, mx, platetee)
s.junction(109.22, platetee)
s.wire(mx, platetee, mx, 84)
s.sym("R", "RBL", "220k", mx, 80.19)
s.gnd(mx, 76.38, 90)
ts2 = 158.75
tl, tr = s.series_h("R", "RTS", "220k", mx + 8, platetee)
s.wire(mx, platetee, tl, platetee)
s.wire(tr, platetee, ts2, platetee)
ts2b = ts2 + 16
s.sym("POT", "VR4", "1M bass", ts2, platetee + 12)
s.wire(ts2, platetee, ts2 + 2, platetee)
s.wire(ts2 + 2, platetee, ts2 + 2, platetee + 12)
s.wire(ts2 + 2, platetee + 12, ts2 + 5.08, platetee + 12)   # RTS -> VR4 wiper
nfby = platetee - 22
s.wire(ts2, platetee + 8.19, ts2, nfby)                      # VR4 top lug -> NFB bus
bl, br = s.series_h("R", "RBS", "220k", ts2 + 6, platetee + 20)
s.wire(ts2, platetee + 15.81, ts2, platetee + 20)             # VR4 bottom lug -> shelf
s.wire(ts2, platetee + 20, bl, platetee + 20)
s.wire(br, platetee + 20, ts2 + 12, platetee + 20)
s.sym("C", "CBS", ".005u", ts2 + 12, platetee + 24)
s.gnd(ts2 + 12, platetee + 28)
s.sym("POT", "VR5", "5k pres", ts2 + 22, nfby + 3.81)
s.wire(ts2, nfby, ts2 + 22, nfby)
s.wire(ts2 + 27.08, nfby + 3.81, ts2 + 32, nfby + 3.81)
s.sym("C", "CPR", ".1u 200V", ts2 + 32, nfby + 7.62)
s.gnd(ts2 + 32, nfby + 11.43)
nl, nr = s.series_h("R", "RNF", "20k", ts2 + 22, nfby - 8)
s.wire(ts2 + 22, nfby, ts2 + 22, nfby - 8)
s.wire(nr, nfby - 8, ts2 + 42, nfby - 8)
s.glabel("SPKR", ts2 + 42, nfby - 8, 0)
s.text("RNF: negative feedback from the speaker node, the family's usual take-off (cf. the 5F6's 27k)", 158, 63, 1.1)

# V2 plate coupling into the treble network: two caps in series, as drawn
cx = ts2b
s.wire(cx, platetee, cx, 96)
s.sym("C", "C3", ".1u 200V", cx, 96 + 3.81)
s.wire(cx, 96 + 7.62, cx, 100.62)
s.sym("C", "C4", "250p", cx, 100.62 + 3.81)
s.wire(cx, 100.62 + 7.62, cx, 108.5)
s.wire(cx, 108.5, cx + 14, 108.5)
trl, trr = s.series_h("R", "VR3", "1M treb", cx + 22, 108.5)
s.wire(cx + 14, 108.5, trl, 108.5)
s.wire(trr, 108.5, cx + 34, 108.5)
s.sym("C", "C7", ".01u 400V", cx + 34, 112.31)
s.gnd(cx + 34, 116.12)
tl2, tr2 = s.series_h("C", "C8", "47p", cx + 44, 108.5)
s.wire(cx + 34, 108.5, tl2, 108.5)
s.note("VR3 (treble) wired as a rheostat -- the same trick the family's 3-knob ladders use for the bass pot")

# ---- phase inverter: self-biased split-load (cathodyne) V3 ---------------
# Same shape as the 5F4's V3B (netlist.cir; known to converge sensibly).
tp = s.triode("V3", "12AX7", 184.15, 92)
s.wire(cx + 47.81, 108.5, tp["g"][0] - 30, 108.5)
s.wire(tp["g"][0] - 30, 108.5, tp["g"][0] - 30, 92)
s.wire(tp["g"][0] - 30, 92, tp["g"][0], 92)
s.plate_load("RLA", "56k", tp["p"], "B+2")
s.wire(184.15, 99.62, 184.15, 102)
s.wire(184.15, 102, 192.12, 102)
s.sym("R", "RKA", "1.5k", 192.12, 105.81, lx=2.0)
s.junction(192.12, 109.62)
s.sym("R", "RKB", "56k", 192.12, 113.43, lx=2.0)
s.gnd(192.12, 117.24)
s.wire(tp["g"][0] - 30, 105, tp["g"][0] - 30, 109.62)
s.junction(tp["g"][0] - 30, 105)
gbl, gbr = s.series_h("R", "RGPI", "1M", tp["g"][0] - 22, 109.62)
s.wire(tp["g"][0] - 30, 109.62, gbl, 109.62)
s.wire(gbr, 109.62, 192.12, 109.62)

# ---- 6L6G pair, fixed bias ------------------------------------------------
for y, pref, cref, cval, glref, gsref in [
        (84, "V4", "C5", ".1u 400V", "RGL1", "R5s"),
        (136, "V5", "C6", ".1u 200V", "RGL2", "R6s")]:
    if y == 84:
        s.wire(184.15, 80.9, 201.93, 80.9)
        s.junction(184.15, 80.9)
        cl, crr = s.series_h("C", cref, cval, 205.74, 80.9)
        s.wire(crr, 80.9, 213.36, 80.9)
        s.wire(213.36, 80.9, 213.36, 84)
        gy = 84
    else:
        s.junction(192.12, 102)
        cl, crr = s.series_h("C", cref, cval, 198.62, 102)
        s.wire(192.12, 102, cl, 102)
        s.wire(crr, 102, 203.62, 102)
        s.wire(203.62, 102, 203.62, 136)
        s.wire(203.62, 136, 213.36, 136)
        gy = 136
    s.wire(213.36, gy, 215.9, gy)
    gl2, gr2 = s.series_h("R", gsref, "1.5k", 219.71, gy)
    p = s.pentode(pref, "6L6G", 229.22, gy)
    s.wire(gr2, gy, p["g1"][0], gy)
    s.junction(215.9, gy)
    s.sym("R", glref, "220k", 215.9, gy + 3.81)
    s.wire(215.9, gy + 7.62, 215.9, gy + 10.16)
    s.glabel("-42V", 215.9, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+1", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(229.22, p["k"][1] + 0)

# ---- output transformer ---------------------------------------------------
s.sym("OT_PP", "T3", "part not legible", 257.12, 110)
s.wire(229.22, 84 - 0.635 - 7.62, 229.22, 73.5)
s.wire(229.22, 73.5, 248.23, 73.5)
s.wire(248.23, 73.5, 248.23, 104.92)
s.wire(229.22, 136 - 0.635 - 7.62, 229.22, 126.5)
s.wire(229.22, 126.5, 243.32, 126.5)
s.wire(243.32, 126.5, 243.32, 115.08)
s.wire(243.32, 115.08, 248.23, 115.08)
s.wire(248.23, 110, 245.69, 110)
s.wire(245.69, 110, 245.69, 107)
s.glabel("B+1", 245.69, 107, 90)
s.wire(266.01, 107.46, 268.55, 107.46)
s.glabel("SPKR", 268.55, 107.46, 0)
s.wire(266.01, 112.54, 268.55, 112.54)
s.glabel("GND", 268.55, 112.54, 0)

# ---- power supply: two 5U4GA in parallel (no choke) + bias ---------------
s.text("Power -- PT part not legible, two 5U4GA rectifiers in parallel (no choke) -- bias: selenium rect, 3300R, 100uF/25V, 56k bleeder -> -42V", 25, 158, 1.4)
for x, ref, ht in [(41.91, "V6", "HT_A"), (54.61, "V7", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    s.diode_tube(ref, "5U4GA", x, 167.78, lx=(-11.4 if ref == "V6" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(41.91, 177.8, 82.55, 177.8)
s.junction(54.61, 177.8)
s.junction(60.32, 177.8)
s.sym("C", "C9", "16u", 60.32, 181.61)
s.gnd(60.32, 185.42)
s.junction(66.04, 177.8)
s.sym("C", "C10", "16u", 66.04, 181.61)
s.gnd(66.04, 185.42)
s.junction(72, 177.8)
s.sym("C", "C11", "16u", 72, 181.61)
s.gnd(72, 185.42)
s.glabel("B+1", 82.55, 177.8, 0)
l, r = s.series_h("R", "RD1", "10k", 90, 177.8)
s.wire(82.55, 177.8, l, 177.8)
s.wire(r, 177.8, 105.41, 177.8)
s.junction(98, 177.8)
s.glabel("B+2", 98, 175.26, 90)
s.wire(98, 175.26, 98, 177.8)
s.junction(105.41, 177.8)
s.sym("C", "C12", "16u", 105.41, 181.61)
s.gnd(105.41, 185.42)
l, r = s.series_h("R", "RD2", "10k", 112, 177.8)
s.wire(105.41, 177.8, l, 177.8)
s.wire(r, 177.8, 127, 177.8)
s.junction(121.92, 177.8)
s.glabel("B+3", 121.92, 175.26, 90)
s.wire(121.92, 175.26, 121.92, 177.8)
s.sym("C", "C13", "8u", 127, 181.61)
s.gnd(127, 185.42)
s.glabel("HT_B", 150.1, 160.72, 180)
s.wire(150.1, 160.72, 153.91, 160.72)
s.sym("DIODE_SS", "D1", "SEL", 158.99, 160.72, lx=-2.0, ly=-5.4)
s.wire(164.07, 160.72, 167.88, 160.72)
l, r = s.series_h("R", "RB1", "3.3k", 171.69, 160.72)
s.wire(167.88, 160.72, l, 160.72)
s.wire(r, 160.72, 183.12, 160.72)
s.junction(178.04, 160.72)
s.sym("R", "RB2", "56k", 178.04, 164.53)
s.gnd(178.04, 168.34)
s.junction(180.58, 160.72)
s.sym("C", "C14", "100u 25V", 180.58, 164.53, lx=2.2)
s.gnd(180.58, 168.34)
s.glabel("-42V", 183.12, 160.72, 0)

s.write(OUT, [
    "Heaters, PT primary and standby omitted -- see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
