#!/usr/bin/env python3
"""Generate amps/5e3/schematic.kicad_sch from the stage-template library.

Values per the published 5E3 (F-EE) drawing (see amps/5e3/meta.yaml sources).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e3" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7, two channels, shared 820R cathode ------------------------
for ch, (y, jack, gref, pref, plref) in enumerate(
        [(96, "INST", "RG1", "V1A", "RL1"), (128, "MIC", "RG2", "V1B", "RL2")]):
    s.glabel(jack, 30, y, 180)
    s.wire(30, y, 34.29, y)
    l, r = s.series_h("R", f"R{ch + 1}s", "68k", 38.1, y)
    s.wire(34.29, y, l, y)
    t = s.triode(pref, "12AY7", 53.34, y)
    s.wire(r, y, t["g"][0], y)
    # The leak hangs off the stopper's OWN right pin, which is the grid node.
    # `t["g"][0] - 4` put it 0.19 mm clear of that lead: drawn on it, wired to
    # nothing.
    s.junction(r, y)
    s.sym("R", gref, "1M", r, y + 3.81)
    s.gnd(r, y + 7.62)
    s.plate_load(plref, "100k", t["p"], "B+3")

# shared cathode bus: both K pins to x=60.96 rail, 820R + 25u to ground
s.wire(53.34, 103.62, 53.34, 106)
s.wire(53.34, 106, 60.96, 106)
s.wire(53.34, 135.62, 53.34, 138)
s.wire(53.34, 138, 60.96, 138)
s.wire(60.96, 106, 60.96, 141)
s.junction(60.96, 138)
s.shunt_rc("RK1", "820", "C10", "25u", 60.96, 141)

# ---- couplers -> volume WIPERS; the V2A grid line off the pot ends -------
# F-EE (schematic page 6118x3617, crop 1400,500,1400,1800) lands each .1-400 on
# its volume's ARROW, grounds the far end of each track, and joins the near
# ends on one vertical line into the V2A grid. The tone pot hangs between the
# top coupler/wiper node (.0005) and ground (.005), its wiper on that grid
# line. Until 2026-10-03 this sheet fed the pots on an end, took the grid off
# the wipers, and ran the tone pot from the V2A plate to the PI grid (V1 audit,
# 5e3.md). Pin 1 is the grid end on both volumes (rot=180 puts VR1's at the
# bottom, as the drawing does; mirror="y" keeps VR2's at the top).
GX = 86.36                              # the V2A grid line
for y, cref, vref, kw in [(88.38, "C1", "VR1", dict(rot=180, lx=2.6, ly=-6.2, label_rot=0)),
                          (120.38, "C2", "VR2", dict(mirror="y", lx=2.6, ly=6.0))]:
    s.wire(53.34, y, 58.42, y)          # from plate stub top junction
    s.junction(53.34, y)
    l, r = s.series_h("C", cref, ".1u", 62.23, y)
    s.wire(r, y, GX - 5.08, y)          # coupler -> wiper
    s.sym("POT", vref, "1M vol", GX, y, **kw)
grid_top, grid_bot = 88.38 + 3.81, 120.38 - 3.81
s.gnd(GX, 88.38 - 3.81, 90)             # VR1's far end (pin 3, top) to ground
s.gnd(GX, 120.38 + 3.81)                # VR2's far end (pin 3, bottom) to ground
s.wire(GX, grid_top, GX, grid_bot)      # the two grid ends, one line
s.junction(GX, 108)

# tone: .0005 off the C1/wiper node, pot, .005 to ground; wiper to the grid line
TX = 71.12
s.junction(TX, 88.38)
s.sym("C", "C5", "500p", TX, 92.19 + 1.79, lx=-6.4, ly=1.0)
s.wire(TX, 88.38, TX, 90.17)
s.sym("POT", "VR3", "1M tone", TX, 101.6, lx=-12.2, ly=1.0)
s.wire(TX + 5.08, 101.6, GX, 101.6)
s.junction(GX, 101.6)
s.sym("C", "C6", ".005u", TX, 109.22, lx=-7.4, ly=1.0)
s.gnd(TX, 113.03)

# ---- V2A 12AX7 second stage --------------------------------------------
t2a = s.triode("V2A", "12AX7", 96.52, 108)
s.wire(86.36, 108, t2a["g"][0], 108)
s.shunt_rc("RK2", "1.5k", "C4", "25u", 96.52, t2a["k"][1] + 1.5)
s.wire(96.52, t2a["k"][1], 96.52, t2a["k"][1] + 1.5)
s.plate_load("RL3", "100k", t2a["p"], "B+3")

# ---- cathodyne PI ------------------------------------------------------
tpi = s.triode("V2B", "12AX7", 138.43, 112)
s.wire(128.27, 112, tpi["g"][0], 112)
s.plate_load("RL4", "56k", tpi["p"], "B+3")
# cathodyne bias stack: K -> 1.5k -> J -> 56k -> gnd; grid leak 1M to J
s.wire(138.43, 119.62, 138.43, 121.92)
s.sym("R", "RKA", "1.5k", 138.43, 125.73)
s.junction(138.43, 129.54)
s.sym("R", "RKB", "56k", 138.43, 133.35, lx=-9.4, ly=1.0)   # clear of the C8 tap
s.gnd(138.43, 137.16)
# The leak run stops at RGPI's own head. Taken all the way to 129.54 it ran
# through the resistor, shorting it and tying the PI grid to the tail junction.
s.wire(128.27, 112, 128.27, 121.92)
s.junction(128.27, 112)
s.sym("R", "RGPI", "1M", 128.27, 125.73, lx=-9.4)
s.wire(128.27, 129.54, 138.43, 129.54)

# ---- outputs: plate + cathode couplers to the 6V6 pair ------------------
pty = tpi["p"][1]                       # the tap must start ON the plate pin
l, r = s.series_h("C", "C7", ".1u", 149.86, pty)
s.wire(tpi["p"][0], pty, l, pty)        # plate-side tap
s.junction(tpi["p"][0], pty)
s.wire(r, pty, 155, pty)
s.wire(155, pty, 155, 92)               # own column: up the grid-leak column
                                        # this lead ran through RG6A's body
# Cathode-side tap ON the cathode, the top of the 1.5k: F-EE's schematic runs
# the .1-200 from the dot above the 1500 and its layout puts the cap's eyelet on
# the 1500's cathode end. (11e9875 had moved it to the 1.5k/56k junction to
# agree with a netlist that read C8 on JPI; the netlist was the misreading.)
s.junction(138.43, 121.92)
s.wire(138.43, 121.92, 146.05, 121.92)
l, r = s.series_h("C", "C8", ".1u", 149.86, 121.92)
s.wire(r, 121.92, 155, 121.92)
s.wire(155, 121.92, 155, 132)

kpin6 = {}
for y, vref, gl, st in [(92, "V3", "RG6A", "R3s"), (132, "V4", "RG6B", "R4s")]:
    l, r = s.series_h("R", st, "1.5k", 163.83, y)
    s.wire(155, y, 158.75, y)
    s.wire(158.75, y, l, y)
    p = s.pentode(vref, "6V6GT", 175.26, y)
    kpin6[vref] = p["k"]
    s.wire(r, y, p["g1"][0], y)
    s.junction(158.75, y)
    s.sym("R", gl, "220k", 158.75, y + 3.81)
    s.gnd(158.75, y + 7.62)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)

# Shared 250R/5W cathode. The bus stands clear of the screen pins: run down
# x=182.88 it passed through V4's own screen pin, tying B+2 to the cathodes.
KBUS = 191.77
s.wire(kpin6["V3"][0], kpin6["V3"][1], 175.26, 102)
s.wire(175.26, 102, KBUS, 102)
s.wire(kpin6["V4"][0], kpin6["V4"][1], 175.26, 142)
s.wire(175.26, 142, KBUS, 142)
s.wire(KBUS, 102, KBUS, 146)
s.junction(KBUS, 142)
s.shunt_rc("RK66", "250 5W", "C9", "25u", KBUS, 146)

# ---- output transformer -------------------------------------------------
# T2 sits far enough right to leave the cathode bus its own column; every lead
# starts on the pin the helper returns.
ot = s.ot_pp("T2", "8k:8", 210.82, 112)
s.wire(175.26, 83.745, 175.26, 81.28)
s.wire(175.26, 81.28, ot["pri_a"][0], 81.28)
s.wire(ot["pri_a"][0], 81.28, ot["pri_a"][0], ot["pri_a"][1])
s.wire(175.26, 123.745, 175.26, 121.3)  # lower 6V6 plate — route right
s.wire(175.26, 121.3, 197, 121.3)
s.wire(197, 121.3, 197, ot["pri_b"][1])
s.wire(197, ot["pri_b"][1], ot["pri_b"][0], ot["pri_b"][1])
s.wire(ot["ct"][0], ot["ct"][1], 199.39, 112)
s.wire(199.39, 112, 199.39, 109)
s.glabel("B+1", 199.39, 109, 90)        # center tap
s.wire(ot["sec_h"][0], ot["sec_h"][1], 222.25, ot["sec_h"][1])
s.glabel("SPKR", 222.25, ot["sec_h"][1], 0)
s.wire(ot["sec_c"][0], ot["sec_c"][1], 222.25, ot["sec_c"][1])
s.glabel("GND", 222.25, ot["sec_c"][1], 0)

# ---- power supply -------------------------------------------------------
s.text("Power supply — 325-0-325 PT secondary, 5Y3GT full-wave", 25, 158, 1.6)
for x, ref, ht in [(45.72, "V5A", "HT_A"), (58.42, "V5B", "HT_B")]:
    s.glabel(ht, x, 157.5, 90)
    s.wire(x, 157.5, x, 160.16)
    d = s.diode_tube(ref, "5Y3GT", x, 167.78, lx=(-11.4 if ref == "V5A" else 6.0))
    s.wire(x, 175.4, x, 177.8)
s.wire(45.72, 177.8, 90.17, 177.8)
s.junction(58.42, 177.8)
s.junction(71.12, 177.8)
s.sym("C", "C11", "16u", 71.12, 181.61)
s.gnd(71.12, 185.42)
s.glabel("B+1", 90.17, 177.8, 0)
s.wire(90.17, 177.8, 92.71, 177.8)
l, r = s.series_h("R", "RD1", "5k", 96.52, 177.8)
s.wire(r, 177.8, 109.22, 177.8)
s.junction(102.87, 177.8)
s.glabel("B+2", 102.87, 175.26, 90)
s.wire(102.87, 175.26, 102.87, 177.8)
s.junction(106.68, 177.8)
s.sym("C", "C12", "16u", 106.68, 181.61)
s.gnd(106.68, 185.42)
l, r = s.series_h("R", "RD2", "22k", 113.03, 177.8)
s.wire(r, 177.8, 124.46, 177.8)
s.junction(119.38, 177.8)
s.glabel("B+3", 119.38, 175.26, 90)
s.wire(119.38, 175.26, 119.38, 177.8)
s.sym("C", "C13", "16u", 124.46, 181.61)
s.gnd(124.46, 185.42)

s.write(OUT, [
    "Heaters and PT primary omitted — see the netlist and the sources list",
])
print(f"wrote {OUT}")
