#!/usr/bin/env python3
"""Generate amps/5d3/schematic.kicad_sch from the stage-template library.

Values per the published 5D3 drawing (see amps/5d3/meta.yaml sources): three
input jacks, 12AY7 front end, 12AX7 driver + self-balancing paraphase inverter,
cathode-biased 6V6GT pair, 5Y3GT rectifier, no feedback loop.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5d3" / "schematic.kicad_sch"
s = Sch()

# ---- V1 12AY7 input stage ------------------------------------------------
# Channel 1: one jack, a bare 1 MΩ leak straight to the grid (no stopper).
s.glabel("IN 1", 26, 96)
s.wire(26, 96, 41.72, 96)
s.junction(41.72, 96)
s.sym("R", "RG1", "1M", 41.72, 99.81)
s.gnd(41.72, 103.62)
s.wire(41.72, 96, 45.72, 96)
v1a = s.triode("V1A", "12AY7", 53.34, 96)
s.plate_load("RL1", "100k", v1a["p"], "B+3")

# Channel 2: two jacks, each through a 68 kΩ stopper onto its own 1 MΩ leak;
# the two stoppers meet at V1B's grid.
for y, jack, gref, sref in [(118, "IN 2", "RG2", "R2S"), (138, "IN 3", "RG3", "R3S")]:
    s.glabel(jack, 26, y)
    s.wire(26, y, 32, y)
    s.junction(32, y)
    s.sym("R", gref, "1M", 32, y + 3.81)
    s.gnd(32, y + 7.62)
    l, r = s.series_h("R", sref, "68k", 39.81, y)
    s.wire(32, y, l, y)
    s.wire(r, y, 45.72, y)
s.wire(45.72, 118, 45.72, 138)
s.junction(45.72, 128)
v1b = s.triode("V1B", "12AY7", 53.34, 128)
s.plate_load("RL2", "100k", v1b["p"], "B+3")

# shared 820 Ω cathode, bypassed by 25 µF
s.wire(53.34, 103.62, 53.34, 106)
s.wire(53.34, 106, 60.96, 106)
s.wire(53.34, 135.62, 53.34, 138)
s.wire(53.34, 138, 60.96, 138)
s.wire(60.96, 106, 60.96, 141)
s.junction(60.96, 138)
s.shunt_rc("RK1", "820", "C1", "25u", 60.96, 141)

# ---- couplers -> volume controls -----------------------------------------
# Each 0.05 µF coupler feeds its pot's WIPER; one end of every pot is grounded
# and the other lands on the shared grid line that drives V2A.
for y, cref, vref, gnd_top in [(88.38, "C2", "VR1", True), (120.38, "C3", "VR2", False)]:
    s.wire(53.34, y, 66.04, y)
    s.junction(53.34, y)
    l, r = s.series_h("C", cref, ".05u", 69.85, y)
    s.wire(r, y, 84.92, y)               # -> wiper (pot drawn rot 180)
    s.sym("POT", vref, "1M vol", 90, y, rot=180, lx=2.6, ly=-6.2, label_rot=0)
    if gnd_top:                          # channel 1: element top grounded
        s.gnd(90, y - 3.81, 90)
        s.wire(90, y + 3.81, 90, 104)
    else:                                # channel 2: element bottom grounded
        s.gnd(90, y + 3.81)
        s.wire(90, y - 3.81, 90, 104)
s.junction(90, 104)

# ---- tone control ---------------------------------------------------------
# 1 MΩ pot: wiper on the grid line, one end through 0.005 µF to ground, the
# other through 500 pF onto the channel-2 coupler node.
s.sym("POT", "VR3", "1M tone", 104, 130, rot=180, lx=2.6, ly=-6.2, label_rot=0)
s.wire(98.92, 130, 98.92, 104)
s.junction(98.92, 104)
s.wire(104, 126.19, 104, 124.5)
s.sym("C", "C6", ".005u", 104, 120.69)
s.gnd(104, 116.88, 90)
s.wire(104, 133.81, 104, 136)
s.sym("C", "C5", "500p", 104, 139.81)
s.wire(104, 143.62, 104, 150)
s.wire(104, 150, 73.66, 150)
s.wire(73.66, 150, 73.66, 120.38)
s.junction(73.66, 120.38)

# ---- V2A 12AX7 driver -----------------------------------------------------
t2a = s.triode("V2A", "12AX7", 120, 104)
s.wire(90, 104, t2a["g"][0], 104)
s.plate_load("RL3", "100k", t2a["p"], "B+3")
s.wire(120, 111.62, 120, 113.12)
s.shunt_rc("RK2", "1.5k", "C4", "25u", 120, 113.12, dx=-7.62)

# ---- V2B 12AX7 paraphase inverter ----------------------------------------
t2b = s.triode("V2B", "12AX7", 140, 150)
s.plate_load("RL4", "100k", t2b["p"], "B+3")
s.wire(140, 157.62, 140, 159.12)
s.sym("R", "RK3", "1.5k", 140, 162.93)   # unbypassed — the deliberate asymmetry
s.gnd(140, 166.74)

# 100 pF across the two inverter plates
s.junction(120, 92.9)
s.wire(120, 92.9, 146.05, 92.9)
s.junction(132, 92.9)
s.wire(132, 92.9, 132, 100)
s.sym("C", "C14", "100p", 132, 103.81)
s.wire(132, 107.62, 132, 138.9)
s.wire(132, 138.9, 146.05, 138.9)
s.junction(140, 138.9)

# ---- output couplers + the self-balancing paraphase network ---------------
l, r = s.series_h("C", "C7", ".05u", 149.86, 92.9)
s.wire(r, 92.9, 165, 92.9)
s.junction(165, 92.9)
s.wire(165, 92.9, 165, 88)
s.wire(165, 88, 177.4, 88)

l, r = s.series_h("C", "C8", ".05u", 149.86, 138.9)
s.wire(r, 138.9, 165, 138.9)
s.junction(165, 138.9)
s.wire(165, 138.9, 165, 150)
s.wire(165, 150, 177.4, 150)

# 220 kΩ / 270 kΩ grid leaks meeting at the junction that feeds V2B's grid,
# and returning to ground through 56 kΩ.
s.sym("R", "RPA", "220k", 165, 96.71, lx=-9.8)
s.wire(165, 100.52, 165, 119)
s.sym("R", "RPB", "270k", 165, 135.09, lx=-9.8)
s.wire(165, 131.28, 165, 119)
s.junction(165, 119)
s.wire(165, 119, 172, 119)
s.sym("R", "RPT", "56k", 172, 122.81)
s.gnd(172, 126.62)
s.wire(165, 119, 124, 119)
s.wire(124, 119, 124, 150)
s.wire(124, 150, t2b["g"][0], 150)

# ---- 6V6GT push-pull pair -------------------------------------------------
kpin = {}
for g1y, vref in [(88, "V3"), (150, "V4")]:
    p = s.pentode(vref, "6V6GT", 185, g1y)
    kpin[vref] = p["k"]
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2.54, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 2.54, p["g2"][1], 0)

# shared 250 Ω 5 W cathode, bypassed by 25 µF.
# Both drops start on the cathode pin the helper returns — V3's used to start
# at 95.985, a millimetre below its own pin, and carried nothing.
s.wire(kpin["V3"][0], kpin["V3"][1], 185, 100)
s.wire(185, 100, 196, 100)
s.wire(kpin["V4"][0], kpin["V4"][1], 185, 160)
s.wire(185, 160, 196, 160)
s.wire(196, 100, 196, 164)
s.junction(196, 160)
s.shunt_rc("RK66", "250 5W", "C9", "25u", 196, 164)

# ---- output transformer ---------------------------------------------------
s.sym("OT_PP", "T2", "PP : 8", 215, 119)
s.wire(185, 79.745, 185, 76)
s.wire(185, 76, 206.11, 76)
s.wire(206.11, 76, 206.11, 113.92)      # -> PRI_A
s.wire(185, 141.745, 185, 138)
s.wire(185, 138, 200, 138)
s.wire(200, 138, 200, 124.08)
s.wire(200, 124.08, 206.11, 124.08)     # -> PRI_B
s.wire(206.11, 119, 202, 119)
s.wire(202, 119, 202, 115)
s.glabel("B+1", 202, 115, 90)           # centre tap
s.wire(223.89, 116.46, 227, 116.46)
s.glabel("SPKR", 227, 116.46, 0)
s.wire(223.89, 121.54, 227, 121.54)
s.glabel("GND", 227, 121.54, 0)

# ---- power supply ---------------------------------------------------------
s.note('Power supply — centre-tapped HT, 5Y3GT full-wave, two 10 kΩ droppers')
for x, ref, ht in [(45.72, "V5A", "HT_A"), (58.42, "V5B", "HT_B")]:
    s.glabel(ht, x, 181.5, 90)
    s.wire(x, 181.5, x, 184.16)
    d = s.diode_tube(ref, "5Y3GT", x, 191.78, lx=(-11.4 if ref == "V5A" else 6.0))
    s.wire(x, 199.4, x, 201.8)
s.wire(45.72, 201.8, 90.17, 201.8)
s.junction(58.42, 201.8)
s.junction(71.12, 201.8)
s.sym("C", "C11", "16u", 71.12, 205.61)
s.gnd(71.12, 209.42)
s.glabel("B+1", 90.17, 201.8, 0)
s.wire(90.17, 201.8, 92.71, 201.8)
l, r = s.series_h("R", "RD1", "10k", 96.52, 201.8)
s.wire(r, 201.8, 109.22, 201.8)
s.junction(102.87, 201.8)
s.glabel("B+2", 102.87, 199.26, 90)
s.wire(102.87, 199.26, 102.87, 201.8)
s.junction(106.68, 201.8)
s.sym("C", "C12", "16u", 106.68, 205.61)
s.gnd(106.68, 209.42)
l, r = s.series_h("R", "RD2", "10k", 113.03, 201.8)
s.wire(r, 201.8, 124.46, 201.8)
s.junction(119.38, 201.8)
s.glabel("B+3", 119.38, 199.26, 90)
s.wire(119.38, 199.26, 119.38, 201.8)
s.sym("C", "C13", "16u", 124.46, 205.61)
s.gnd(124.46, 209.42)

s.write(OUT, [
    "Heaters and PT primary omitted — see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
