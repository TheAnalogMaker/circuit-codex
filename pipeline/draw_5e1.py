#!/usr/bin/env python3
"""Generate amps/5e1/schematic.kicad_sch from the stage-template library.

Values per the published Champ 5E1 (H-EE) drawing (see amps/5e1/meta.yaml).
The 5E1 is the 5F1's direct ancestor: same tube set and preamp, but a
choke-filtered supply whose post-choke node feeds both the 6V6 plate and screen.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "5e1" / "schematic.kicad_sch"
s = Sch()

Y = 100.0   # signal row

# ---- inputs: two jacks, each 68k stopper, shared 1M grid leak ------------
s.glabel("IN 1", 26, Y, 180)
s.wire(26, Y, 33.29, Y)
l, r = s.series_h("R", "R1", "68k", 37.1, Y)
s.wire(40.91, Y, 49.53, Y)
s.glabel("IN 2", 26, Y - 8, 180)
s.wire(26, Y - 8, 33.29, Y - 8)
l, r = s.series_h("R", "R2", "68k", 37.1, Y - 8)
s.wire(40.91, Y - 8, 49.53, Y - 8)
s.wire(49.53, Y - 8, 49.53, Y)
s.junction(49.53, Y)
s.sym("R", "R3", "1M", 49.53, Y + 3.81)   # grid leak, shunt to ground
s.gnd(49.53, Y + 7.62)
s.wire(49.53, Y, 53.34, Y)                 # to V1A grid

# ---- V1A input stage ----------------------------------------------------
v1a = s.triode("V1A", "12AX7", 60.96, Y)
# cathode: 1.5k bypassed by 25u
s.wire(60.96, Y + 7.62, 60.96, Y + 10)
s.shunt_rc("R4", "1.5k", "C1", "25u", 60.96, Y + 10)
# plate load to preamp rail B+3
s.plate_load("R5", "100k", v1a["p"], "B+3")
# coupler off the plate stub -> volume pot
s.wire(60.96, 88.9, 68.58, 88.9)
s.junction(60.96, 88.9)
cl, cr = s.series_h("C", "C2", ".02u", 72.39, 88.9)
s.wire(cr, 88.9, 77.47, 88.9)
s.sym("POT", "VR1", "1M vol", 77.47, 92.71)
s.wire(77.47, 96.52, 77.47, 100.33)
s.gnd(77.47, 100.33)
# wiper -> V1B grid
s.wire(82.55, 92.71, 82.55, Y)
s.wire(82.55, Y, 99.06, Y)

# ---- V1B driver stage (unbypassed cathode, NFB into it) -----------------
v1b = s.triode("V1B", "12AX7", 106.68, Y)
s.wire(106.68, Y + 7.62, 106.68, Y + 10)
s.junction(106.68, Y + 10)
s.sym("R", "R6", "1.5k", 106.68, Y + 13.81)
s.gnd(106.68, Y + 17.62)
# negative feedback: 22k from the speaker node into this cathode
s.wire(106.68, Y + 10, 114.3, Y + 10)
s.sym("R", "R11", "22k NFB", 114.3, Y + 13.81)
s.wire(114.3, Y + 17.62, 114.3, Y + 20.16)
s.glabel("SPKR", 114.3, Y + 20.16, 270)
# plate load to preamp rail B+3
s.plate_load("R7", "100k", v1b["p"], "B+3")
# coupler off the plate stub -> 6V6 grid
s.wire(106.68, 88.9, 114.3, 88.9)
s.junction(106.68, 88.9)
cl, cr = s.series_h("C", "C3", ".02u", 118.11, 88.9)
s.wire(cr, 88.9, 127, 88.9)
s.wire(127, 88.9, 127, Y)
s.junction(127, Y)
s.sym("R", "R9", "220k", 127, Y + 3.81)    # 6V6 grid leak
s.gnd(127, Y + 7.62)
s.wire(127, Y, 129.54, Y)                  # to 6V6 grid (g1)

# ---- V2 6V6GT single-ended output ---------------------------------------
v2 = s.pentode("V2", "6V6GT", 137.16, Y)
# screen to B+2 (same node as the OT primary B+)
s.wire(v2["g2"][0], v2["g2"][1], 149.86, v2["g2"][1])
s.glabel("B+2", 149.86, v2["g2"][1], 0)
# cathode: 470 bypassed by 25u
s.wire(137.16, v2["k"][1], 137.16, v2["k"][1] + 2)
s.shunt_rc("R8", "470", "C4", "25u", 137.16, v2["k"][1] + 2)
# plate -> OT primary
s.sym("OT_SE", "T1", "SE 5k:8", 160, 90)
s.wire(137.16, v2["p"][1], 137.16, 87.46)
s.wire(137.16, 87.46, 151.11, 87.46)       # to PRI_P
s.wire(151.11, 92.54, 148.57, 92.54)       # PRI_B -> B+2
s.wire(148.57, 92.54, 148.57, 95.08)
s.glabel("B+2", 148.57, 95.08, 270)
s.wire(168.89, 87.46, 171.43, 87.46)       # SEC_H -> speaker
s.glabel("SPKR", 171.43, 87.46, 0)
s.wire(168.89, 92.54, 171.43, 92.54)       # SEC_C -> ground
s.glabel("GND", 171.43, 92.54, 0)

# ---- power supply: 5Y3GT, reservoir, choke, 22k dropper -----------------
s.text("Power supply — center-tapped HT · 5Y3GT full-wave · choke-filtered · heaters and PT primary omitted",
       25, 150, 1.5)
for x, ref, ht in [(50.8, "V3A", "HT_A"), (63.5, "V3B", "HT_B")]:
    s.glabel(ht, x, 152.5, 90)
    s.wire(x, 152.5, x, 155.16)
    s.diode_tube(ref, "5Y3GT", x, 162.78, lx=(-11.4 if ref == "V3A" else 6.0))
    s.wire(x, 170.4, x, 172.8)
s.wire(50.8, 172.8, 76.2, 172.8)           # cathode bus -> reservoir
s.junction(63.5, 172.8)
s.junction(76.2, 172.8)
s.sym("C", "C5", "8u", 76.2, 176.61)       # reservoir B+1
s.gnd(76.2, 180.42)
s.glabel("B+1", 76.2, 169.24, 90)
# choke B+1 -> B+2
s.wire(76.2, 172.8, 84, 172.8)
s.sym("CHOKE", "L1", "choke", 91.62, 172.8, lx=-4.0, ly=-6.4)
s.wire(99.24, 172.8, 107, 172.8)
s.junction(107, 172.8)
s.sym("C", "C6", "8u", 107, 176.61)        # filter B+2
s.gnd(107, 180.42)
s.glabel("B+2", 107, 169.24, 90)
# 22k dropper B+2 -> B+3
s.wire(107, 172.8, 111, 172.8)
l, r = s.series_h("R", "R10", "22k", 114.81, 172.8)
s.wire(r, 172.8, 122, 172.8)
s.junction(122, 172.8)
s.sym("C", "C7", "8u", 122, 176.61)        # filter B+3
s.gnd(122, 180.42)
s.glabel("B+3", 122, 169.24, 90)

s.write(OUT, [
    ("5E1 — Tweed Champ-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts", 25, 70, 2.0),
    ("Heaters and PT primary omitted — see netlist.cir and meta.yaml", 25, 74.5, 1.3),
])
print(f"wrote {OUT}")
