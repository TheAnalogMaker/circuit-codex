#!/usr/bin/env python3
"""Generate amps/5e5a/schematic.kicad_sch from the stage-template library.

Values per the published Fender 5E5-A (J-EE) schematic — component list read
from amps/5e5a/{bom,netlist.cir,notes.md}, extended 2026-08-08 with a
sharper re-read of the same source PDF (see meta.yaml sources, notes.md
"2026-08-08 re-read"). The circuit is redrawn from the extracted component
list, not traced.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e5a" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, two channels, shared 820R/dual-25u cathode ----------------
for ch, (y, jack, gref, pref, plref, cref, vref, mref) in enumerate([
        (92, "INST", "RG1", "V1A", "RL1", "C_c1", "VR1", "RMX1"),
        (126, "MIC", "RG2", "V1B", "RL2", "C_c2", "VR2", "RMX2")]):
    s.glabel(jack, 26, y, 180)
    s.wire(26, y, 30.48, y)
    l, r = s.series_h("R", f"R{ch + 1}s", "68k", 34.29, y)
    s.wire(30.48, y, l, y)
    t = s.triode(pref, "12AY7", 49.53, y)
    s.wire(r, y, t["g"][0], y)
    s.junction(t["g"][0] - 3.81, y)
    s.sym("R", gref, "1M", t["g"][0] - 3.81, y + 3.81)
    s.gnd(t["g"][0] - 3.81, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+4")
    # coupler -> volume pot -> 270k mixer into the shared V2 grid line
    ty = y - 7.62 - 3.48
    s.wire(49.53, ty, 60.96, ty)
    s.junction(49.53, ty)
    cl, crr = s.series_h("C", cref, ".02u", 64.77, ty)
    s.wire(crr, ty, 73.66, ty)
    s.sym("POT", vref, "1M vol", 73.66, ty + 3.81)
    s.gnd(73.66, ty + 11.43)
    s.wire(78.74, ty + 3.81, 81.28, ty + 3.81)
    ml, mr = s.series_h("R", mref, "270k", 85.09, ty + 3.81)
    s.wire(81.28, ty + 3.81, ml, ty + 3.81)
    s.wire(mr, ty + 3.81, 91.44, ty + 3.81)
    s.wire(91.44, ty + 3.81, 91.44, 109)
s.junction(91.44, 109)
s.caption('Bright/treble-peak cap across each vol pot omitted (AC only, not on the BOM)', 44, 79, 1.1)

# shared V1 cathode: both triodes' K pins bus together into one 820R/25+25u can
s.wire(49.53, 99.62, 49.53, 103)
s.wire(49.53, 103, 56.13, 103)
s.wire(49.53, 133.62, 49.53, 137)
s.wire(49.53, 137, 56.13, 137)
s.wire(56.13, 103, 56.13, 140)
s.junction(56.13, 137)
s.shunt_rc("RK1", "820", "C4", "25u+25u", 56.13, 140)

# ---- V2 12AY7 (single triode — the other half is unused) -----------------
t2 = s.triode("V2", "12AY7", 101.6, 109)
s.wire(91.44, 109, t2["g"][0], 109)
s.wire(101.6, 116.62, 101.6, 118)
s.shunt_rc("RK2", "1.5k", "C4b", "25u", 101.6, 118)
s.plate_load("RL3", "100k", t2["p"], "B+4")
s.sym("R", "RG3", "1M", t2["g"][0] - 3.81, 112.81)
s.gnd(t2["g"][0] - 3.81, 116.62)

# RFB1: 100k printed straight across V2's own plate and grid (annotation —
# excluded from netlist.cir; drawn as wired because it visually exists on
# the sheet, see notes.md "2026-08-08 re-read").
fby = 109 - 7.62 - 3.48 - 5
s.wire(t2["g"][0], fby + 5, t2["g"][0], fby)
s.wire(101.6, 101.38, 101.6, fby)
fl, fr = s.series_h("R", "RFB1", "100k", (t2["g"][0] + 101.6) / 2, fby)
s.wire(t2["g"][0], fby, fl, fby)
s.wire(fr, fby, 101.6, fby)

# ---- James tone network (Bass/Treble) + Presence, into the driver grid ---
# Illustrative wiring: the pot count (VR3 Bass, VR4 Treble, both 1M; VR5
# Presence 5k), the coupling caps flanking the treble pot (.01-400/.0005),
# and the destination (driver grid, not cathode) are confirmed on the
# 2026-08-08 re-read; which lug each wiper lands on is not independently
# re-verified — see notes.md ("James tone network..."). netlist.cir
# abstracts the whole network to RG4, a single 1M leak at the driver's grid.
ty2 = 109 - 7.62 - 3.48
s.wire(101.6, ty2, 101.6, 84)
s.wire(101.6, 84, 108, 84)
tcl, tcr = s.series_h("C", "C_tr1", ".01u 400V", 112, 84)
s.wire(tcr, 84, 122, 84)
s.sym("POT", "VR4", "1M treble", 122, 87.81)          # top pin (122, 84)
s.sym("C", "C_tr2", ".0005u", 122, 95.43)              # top pin (122, 91.62) == VR4 bottom pin
s.gnd(122, 99.24)                                      # == C_tr2 bottom pin
s.wire(127.08, 87.81, 137, 87.81)                      # VR4 wiper -> right
s.wire(137, 87.81, 137, 92.19)
s.sym("POT", "VR3", "1M bass", 137, 96)                # top pin (137, 92.19) == wire above
s.gnd(137, 99.81)                                      # == VR3 bottom pin
s.wire(142.08, 96, 150, 96)                            # VR3 wiper -> right
s.wire(150, 96, 150, 126)                              # down to the driver-grid bus
s.note('Bass/Treble lug wiring illustrative (James network; not re-verified lug by lug)')

# RBLEED: 5 MEG printed from V2's grid across to the driver's grid, in
# parallel with the tone/coupling path above (annotation — excluded from
# netlist.cir, same status as RFB1; see notes.md).
s.wire(t2["g"][0], fby, t2["g"][0], 68)
s.wire(t2["g"][0], 68, 180, 68)
bl, br = s.series_h("R", "RBLEED", "5MEG", 160, 68)
s.wire(180, 68, 180, 126)
s.note('RFB1 (100k, V2 plate<->grid) and RBLEED (5MEG, V2 grid -> driver grid) are printed')
s.note('on the sheet but excluded from netlist.cir — see notes.md "2026-08-08 re-read"')

# Presence + negative feedback: speaker/OT-secondary node -> R_NFB 100k ->
# VR5 (Presence, 5k, other lug grounded) -> wiper -> C_NFB .1-200 -> driver
# grid. Confirmed 2026-08-08 landing on the GRID, not the cathode.
s.glabel("SPKR", 205, 60, 180)
s.wire(205, 60, 198, 60)
pnl, pnr = s.series_h("R", "R_NFB", "100k", 190, 60)
s.wire(198, 60, pnr, 60)
s.wire(pnl, 60, 184, 60)
s.sym("POT", "VR5", "5k pres", 184, 63.81)
s.gnd(184, 71.43)
s.wire(189.08, 63.81, 192, 63.81)
ncl, ncr = s.series_h("C", "C_NFB", ".1u 200V", 196, 63.81)
s.wire(ncr, 63.81, 200, 63.81)
s.wire(200, 63.81, 200, 126)

# ---- driver (V3A) + split-load cathodyne (V3B), one 12AX7 ----------------
bt = s.triode("V3A", "12AX7", 200, 126, lx=8.8)
s.wire(150, 126, bt["g"][0], 126)
s.wire(180, 126, bt["g"][0], 126)
s.junction(bt["g"][0], 126)
tp = s.triode("V3B", "12AX7", 200, 92)
s.plate_load("RL4", "100k", bt["p"], "B+3")
s.plate_load("RL5", "56k", tp["p"], "B+3")
s.sym("R", "RK3", "1.5k", 200, 137.43)
s.gnd(200, 141.24)
# driver plate tee -> C1 .02 -> cathodyne grid
s.junction(200, 114.9)
c1l, c1r = s.series_h("C", "C1", ".02u", 191, 114.9)
s.wire(c1r, 114.9, 200, 114.9)
s.wire(c1l, 114.9, 184, 114.9)
s.wire(184, 114.9, 184, 92)
s.wire(184, 92, tp["g"][0], 92)
# cathodyne grid leak RGPI 1M -> the 1.5k/56k junction
s.junction(184, 105)
gbl, gbr = s.series_h("R", "RGPI", "1M", 191.5, 105)
s.wire(184, 105, gbl, 105)
s.wire(gbr, 105, 196.5, 105)
s.wire(196.5, 105, 196.5, 109.62)
s.wire(196.5, 109.62, 208.5, 109.62)
# cathodyne cathode chain: RKA 1.5k -> J -> RKB 56k -> gnd
s.wire(200, 99.62, 200, 102)
s.wire(200, 102, 208.5, 102)
s.sym("R", "RKA", "1.5k", 208.5, 105.81, lx=2.0)
s.junction(208.5, 109.62)
s.sym("R", "RKB", "56k", 208.5, 113.43, lx=2.0)
s.gnd(208.5, 117.24)
s.text("VR5 presence wiper + R_NFB land on V3A's grid (annotation) — see notes.md", 150, 149, 1.1)

# ---- 6L6GB pair, fixed bias ----------------------------------------------
for y, pref, cref, glref, gstop in [(84, "V4", "C2", "RGL1", "R5s"),
                                     (136, "V5", "C3", "RGL2", "R6s")]:
    if y == 84:
        s.wire(200, 80.9, 218, 80.9)
        s.junction(200, 80.9)
        cl, crr = s.series_h("C", cref, ".1u", 222, 80.9)
        s.wire(crr, 80.9, 229.5, 80.9)
        s.wire(229.5, 80.9, 229.5, 84)
        gy = 84
    else:
        s.junction(208.5, 102)
        cl, crr = s.series_h("C", cref, ".1u", 214.5, 102)
        s.wire(208.5, 102, cl, 102)
        s.wire(crr, 102, 219.5, 102)
        s.wire(219.5, 102, 219.5, 136)
        s.wire(219.5, 136, 229.5, 136)
        gy = 136
    s.wire(229.5, gy, 232, gy)
    gl2, gr2 = s.series_h("R", gstop, "1.5k", 235.8, gy)
    p = s.pentode(pref, "6L6GB", 245.3, gy)
    s.wire(gr2, gy, p["g1"][0], gy)
    s.junction(232, gy)
    s.sym("R", glref, "220k", 232, gy + 3.81)
    s.wire(232, gy + 7.62, 232, gy + 10.16)
    s.glabel("-32V", 232, gy + 10.16, 270)
    # screen straight to B+2 (no screen resistor legible on the sheet)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)
    s.gnd(245.3, p["k"][1])

# ---- output transformer ---------------------------------------------------
s.sym("OT_PP", "T2", "~4.3k:8", 273.2, 110)
s.wire(245.3, 84 - 0.635 - 7.62, 245.3, 73.5)
s.wire(245.3, 73.5, 264.3, 73.5)
s.wire(264.3, 73.5, 264.3, 104.92)
s.wire(245.3, 136 - 0.635 - 7.62, 245.3, 126.5)
s.wire(245.3, 126.5, 259.4, 126.5)
s.wire(259.4, 126.5, 259.4, 115.08)
s.wire(259.4, 115.08, 264.3, 115.08)
s.wire(264.3, 110, 261.77, 110)
s.wire(261.77, 110, 261.77, 107)
s.glabel("B+1", 261.77, 107, 90)
jk = s.jack("SPKR", "15in spkr", 291, 110)
s.wire(282.1, 107.46, jk["tip"][0], jk["tip"][1])
s.wire(282.1, 112.54, jk["sleeve"][0], jk["sleeve"][1])
s.text("Extra 8-ohm speaker jack (parallel) omitted — annotation only", 250, 122, 1.0)

# ---- power supply + bias ---------------------------------------------------
s.text("Power — 5U4GA rectifier; choke DCR ~110 R (est.); bias: selenium rect -> -32V", 25, 158, 1.4)
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
s.sym("C", "C_f1", "16u", 108.86, 181.61)
s.gnd(108.86, 185.42)
l, r = s.series_h("R", "RD1", "16k", 115.57, 177.8)
s.wire(r, 177.8, 127, 177.8)
s.junction(121.92, 177.8)
s.glabel("B+3", 121.92, 175.26, 90)
s.wire(121.92, 175.26, 121.92, 177.8)
s.junction(124.46, 177.8)
s.sym("C", "C_f2", "16u", 124.46, 181.61)
s.gnd(124.46, 185.42)
l, r = s.series_h("R", "RD2", "22k", 130.81, 177.8)
s.wire(r, 177.8, 142.24, 177.8)
s.junction(137.16, 177.8)
s.glabel("B+4", 137.16, 175.26, 90)
s.wire(137.16, 175.26, 137.16, 177.8)
s.sym("C", "C_f3", "8u", 142.24, 181.61)
s.gnd(142.24, 185.42)
# bias supply: HT tap -> selenium -> 100uF filter -> -32V node
s.glabel("HT_B", 150.1, 160.72, 180)
s.wire(150.1, 160.72, 153.91, 160.72)
s.sym("DIODE_SS", "D1", "SEL", 158.99, 160.72, lx=-2.0, ly=-5.4)
s.wire(164.07, 160.72, 167.88, 160.72)
s.junction(167.88, 160.72)
s.sym("C", "C_bias", "100u", 167.88, 164.53)
s.gnd(167.88, 168.34)
s.glabel("-32V", 170.42, 160.72, 0)

s.write(OUT, [
    "Heaters, PT primary and standby omitted — see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
