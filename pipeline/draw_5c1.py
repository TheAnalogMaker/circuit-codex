#!/usr/bin/env python3
"""Generate amps/5c1/schematic.kicad_sch from the stage-template library.

Values per the published Champ 5C1 (F-DH) drawing (see amps/5c1/meta.yaml).
The 5C1 is the earliest circuit-numbered Champ: a single 6SJ7 pentode preamp
stage (grid-leak/contact bias — no cathode resistor at all), a cathode-biased
6V6GT single-ended output, a 5Y3GT rectifier, and no choke — two resistor
droppers feed the B+ chain instead, with the 6V6 screen sharing the *second*
dropper's output with the whole 6SJ7 plate/screen circuit rather than sharing
a node with its own plate. It is the direct topological ancestor of the
12AX7-based 5E1 (draw_5e1.py), whose layout conventions this script follows.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5c1" / "schematic.kicad_sch"
s = Sch()

Y = 100.0     # signal row
GAP = 3.48    # plate_load's default plate-to-resistor riser — reused so the
              # coupling and screen taps below land exactly on the tube's own node

# ---- inputs: two jacks, each its own 75k shunt to ground, summed ----------
s.glabel("IN 1", 26, Y, 180)
s.wire(26, Y, 37.1, Y)
s.junction(37.1, Y)
s.shunt_r("R1", "75k", 37.1, Y)
s.wire(37.1, Y, 45, Y)

s.glabel("IN 2", 26, Y - 14, 180)
s.wire(26, Y - 14, 37.1, Y - 14)
s.junction(37.1, Y - 14)
s.shunt_r("R2", "75k", 37.1, Y - 14)
s.wire(37.1, Y - 14, 45, Y - 14)
s.wire(45, Y - 14, 45, Y)
s.junction(45, Y)

# summed node -> C1 coupling cap -> V1 grid node (5 Meg leak, contact bias)
cl, cr = s.series_h("C", "C1", ".02u", 53.34, Y)
s.wire(45, Y, cl, Y)
s.wire(cr, Y, 60.96, Y)
s.junction(60.96, Y)
s.sym("R", "R3", "5M", 60.96, Y + 3.81)   # grid leak, shunt to ground
s.gnd(60.96, Y + 7.62)
s.wire(60.96, Y, 68.58, Y)                 # to V1 grid

# ---- V1 6SJ7 pentode preamp — grid-leak (contact) bias, no cathode resistor
v1 = s.pentode("V1", "6SJ7", 76.2, Y)
# cathode grounds directly — the defining feature of contact bias
s.wire(v1["k"][0], v1["k"][1], v1["k"][0], v1["k"][1] + 3)
s.gnd(v1["k"][0], v1["k"][1] + 3)

# plate load R5 250k -> B+3, with a coupling tap at the plate node
s.plate_load("R5", "250k", v1["p"], "B+3", gap=GAP)
tapx, tapy = v1["p"][0], v1["p"][1] - GAP   # plate node (before R5's own body)
s.junction(tapx, tapy)
s.wire(tapx, tapy, tapx + 8, tapy)
cl, cr = s.series_h("C", "C3", ".02u", tapx + 11.81, tapy)

# screen: R4 2M dropper -> B+3, bypassed by C2 0.05uF to ground
sx, sy = v1["g2"]
nx = sx + 3.0
s.wire(sx, sy, nx, sy)
s.junction(nx, sy)
s.shunt_r("C2", ".05u", nx, sy, lib="C")
s.wire(nx, sy, nx, sy - GAP)
s.sym("R", "R4", "2M", nx, sy - GAP - 3.81)
s.wire(nx, sy - GAP - 7.62, nx, sy - GAP - 10.16)
s.glabel("B+3", nx, sy - GAP - 10.16, 90)

# ---- volume pot: 1M, wiper -> V2 grid directly (no separate 6V6 grid leak —
# the pot's own body provides the DC return, modelled as RVOL in netlist.cir)
vr_x = cr + 4.81
s.wire(cr, tapy, vr_x, tapy)               # coupler -> pot top lug (pin 3)
s.sym("POT", "VR1", "1M vol", vr_x, tapy + 3.81)
s.wire(vr_x, tapy + 7.62, vr_x, tapy + 11.43)   # pot bottom lug (pin 1) -> ground
s.gnd(vr_x, tapy + 11.43)
wx = vr_x + 5.08                            # wiper (pin 2)
s.wire(wx, tapy + 3.81, wx, Y)
s.wire(wx, Y, wx + 16, Y)                   # -> V2 grid

# ---- V2 6V6GT single-ended output ------------------------------------------
x2 = wx + 16 + 7.62
v2 = s.pentode("V2", "6V6GT", x2, Y)
# screen -> B+3 (shares the whole 6SJ7 preamp rail — NOT the plate's own node)
s.wire(v2["g2"][0], v2["g2"][1], v2["g2"][0] + 12.7, v2["g2"][1])
s.glabel("B+3", v2["g2"][0] + 12.7, v2["g2"][1], 0)
# cathode: 500 ohm bypassed by 25uF
s.wire(x2, v2["k"][1], x2, v2["k"][1] + 2)
s.shunt_rc("R6", "500", "C4", "25u", x2, v2["k"][1] + 2)
# plate -> OT primary
tx = x2 + 22.84
ty = 90.0
s.sym("OT_SE", "T1", "SE 5k:8", tx, ty)
s.wire(x2, v2["p"][1], x2, 87.46)
s.wire(x2, 87.46, tx - 8.89, 87.46)         # -> PRI_P
s.wire(tx - 8.89, 92.54, tx - 11.43, 92.54) # PRI_B -> B+2
s.wire(tx - 11.43, 92.54, tx - 11.43, 95.08)
s.glabel("B+2", tx - 11.43, 95.08, 270)
s.wire(tx + 8.89, 87.46, tx + 11.43, 87.46) # SEC_H -> speaker
s.glabel("SPKR", tx + 11.43, 87.46, 0)
s.wire(tx + 8.89, 92.54, tx + 11.43, 92.54) # SEC_C -> ground
s.glabel("GND", tx + 11.43, 92.54, 0)

# ---- power supply: 5Y3GT, reservoir, two resistor droppers (no choke) -----
s.note('Power supply — center-tapped HT · 5Y3GT full-wave · resistor-dropped, no choke on this pre-5E1 circuit · heaters and PT primary omitted')
for x, ref, ht in [(50.8, "V3A", "HT_A"), (63.5, "V3B", "HT_B")]:
    s.glabel(ht, x, 152.5, 90)
    s.wire(x, 152.5, x, 155.16)
    s.diode_tube(ref, "5Y3GT", x, 162.78, lx=(-11.4 if ref == "V3A" else 6.0))
    s.wire(x, 170.4, x, 172.8)
s.wire(50.8, 172.8, 76.2, 172.8)            # cathode bus -> reservoir
s.junction(63.5, 172.8)
s.junction(76.2, 172.8)
s.sym("C", "C5", "8u", 76.2, 176.61)        # reservoir B+1
s.gnd(76.2, 180.42)
s.glabel("B+1", 76.2, 169.24, 90)
# R7 500 ohm dropper B+1 -> B+2 (no choke on this circuit)
s.wire(76.2, 172.8, 80, 172.8)
l, r = s.series_h("R", "R7", "500", 83.81, 172.8)
s.wire(r, 172.8, 92, 172.8)
s.junction(92, 172.8)
s.sym("C", "C6", "8u", 92, 176.61)          # filter B+2
s.gnd(92, 180.42)
s.glabel("B+2", 92, 169.24, 90)
# R8 25k dropper B+2 -> B+3 (feeds the whole 6SJ7 preamp rail AND the 6V6 screen)
s.wire(92, 172.8, 96, 172.8)
l, r = s.series_h("R", "R8", "25k", 99.81, 172.8)
s.wire(r, 172.8, 108, 172.8)
s.junction(108, 172.8)
s.sym("C", "C7", "8u", 108, 176.61)         # filter B+3
s.gnd(108, 180.42)
s.glabel("B+3", 108, 169.24, 90)

s.write(OUT, [
    "Heaters and PT primary omitted — see netlist.cir and meta.yaml",
])
print(f"wrote {OUT}")
