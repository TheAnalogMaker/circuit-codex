#!/usr/bin/env python3
"""Generate amps/aa764-vibro/schematic.kicad_sch from the stage-template library.

Values per the published "VIBRO-CHAMP AA764" drawing (see amps/aa764-vibro/
meta.yaml). The audio path (input jacks, V1A, tone stack, volume, V1B and its
feedback divider, the 0.02 uF coupler and the 6V6GT output stage) duplicates
amps/aa764 component-for-component -- same designators, same values, same
topology -- so this half of the sheet mirrors pipeline/draw_aa764.py exactly.
What is added is a second, dedicated 12AX7 (V4) running a bias-vary tremolo
oscillator ahead of the same output stage: V4A is an RC phase-shift oscillator
fed from the Vibrato Pedal jack (J1) and tuned by the Speed control (R24);
V4B is direct-coupled from V4A's plate and wired as a cathode follower whose
cathode, through the Intensity control (R27), injects the oscillator's signal
directly at the 6V6 cathode/bias node (K2) -- the "bias-vary" mechanism the
family name describes. V4 has no static DC operating point (a running
oscillator) and is excluded from netlist.cir; see notes.md and
amps/ab763's V5, the same category of exclusion.

Redrawn from circuit facts -- never a trace of a factory drawing. Rails:
B+1 = +355 (reservoir, output-transformer primary feed), B+2 = +340 (6V6
screen; also V4B's plate, tied straight to this rail with no plate resistor),
B+3 = +320 (both 12AX7 plate loads; also V4A's plate load). The 6.3 V heater
winding, its grounded return leg, the pilot lamp, the AC switch and the mains
fuse are an annotation layer and are not drawn here -- see netlist.cir,
notes.md and layout.yaml.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "aa764-vibro" / "schematic.kicad_sch"
s = Sch()

# ============================ TITLE ==================================
s.note('Heaters (6.3 V, one leg grounded), pilot lamp, AC switch and fuse omitted here — see netlist.cir, notes.md, layout.yaml. Rails: B+1 +355 · B+2 +340 screen · B+3 +320 preamp. Audio path is component-for-component amps/aa764 (below); the tremolo oscillator (V4, bottom) is new and excluded from netlist.cir — no static DC operating point.')

# ============================ INPUT + V1A ============================
YH, YL, GB = 58.0, 66.0, 34.0          # high jack, low jack, grid bus
s.glabel("IN 1", 8, YH, 180)
s.glabel("IN 2", 8, YL, 180)
l, r = s.series_h("R", "R1", "68k", 18, YH)
s.wire(8, YH, l, YH)
s.wire(r, YH, GB, YH)
l, r = s.series_h("R", "R2", "68k", 18, YL)
s.wire(8, YL, l, YL)
s.wire(r, YL, GB, YL)
s.wire(GB, YH, GB, YL)
s.junction(GB, 62)
s.sym("R", "R3", "1M", GB, YL + 3.81)          # grid leak, at the jacks
s.gnd(GB, YL + 7.62)

v1a = s.triode("V1A", "12AX7", 46, 62)          # p (46,54.38) g (38.38,62) k (46,69.62)
s.wire(GB, 62, v1a["g"][0], 62)
s.plate_load("R4", "100k", v1a["p"], "B+3")     # tee left at (46, 50.9)
s.wire(46, 69.62, 46, 71)
s.shunt_rc("R5", "1.5k", "C1", "25u", 46, 71)

# ============================ TONE STACK =============================
# Plate → 250 pF → treble pot; plate → 100 kΩ slope → node X; X → 0.1 µF to the
# treble/bass junction, X → 0.047 µF to the bass pot's lower end + 15 kΩ leg.
TEE, XN = 50.9, 72.0                             # plate tee, slope-node x
s.junction(46, TEE)
s.wire(46, TEE, 58, TEE)
s.wire(58, 48.38, 58, 56)
s.junction(58, TEE)
l, r = s.series_h("C", "C2", "250pF", 70, 48.38)
s.wire(58, 48.38, l, 48.38)
s.wire(r, 48.38, 86, 48.38)                      # → treble pot top (lug 1)
l, r = s.series_h("R", "R6", "100k", 64, 56)
s.wire(58, 56, l, 56)
s.wire(r, 56, XN, 56)
s.junction(XN, 56)
l, r = s.series_h("C", "C3", ".1u", 79, 56)
s.wire(XN, 56, l, 56)
s.wire(r, 56, 86, 56)                            # → treble lug 3 / bass lug 1
s.wire(XN, 56, XN, 63.62)
l, r = s.series_h("C", "C4", ".047u", 79, 63.62)
s.wire(XN, 63.62, l, 63.62)
s.wire(r, 63.62, 86, 63.62)                      # → bass pot lug 3
s.sym("POT", "VR2", "250k treb", 86, 52.19)      # lug1 (86,48.38) lug3 (86,56)
s.sym("POT", "VR3", "250k bass", 86, 59.81)      # lug1 (86,56)    lug3 (86,63.62)
s.junction(86, 56)
# bass wiper ties to its upper end, the classic blackface bass-control wiring
s.wire(91.08, 59.81, 94, 59.81)
s.wire(94, 59.81, 94, 56)
s.wire(94, 56, 86, 56)
s.sym("R", "R7", "15k", 86, 67.43)               # bass leg to ground
s.gnd(86, 71.24)

# ============================ VOLUME + V1B ===========================
s.wire(91.08, 52.19, 105, 52.19)                 # treble wiper → volume top
s.sym("POT", "VR1", "1M vol", 105, 56)           # lug1 (105,52.19) lug3 (105,59.81)
s.wire(105, 59.81, 105, 63.62)
s.gnd(105, 63.62)
v1b = s.triode("V1B", "12AX7", 124, 70)          # p (124,62.38) g (116.38,70) k (124,77.62)
s.wire(110.08, 56, 113, 56)                      # volume wiper → V1B grid
s.wire(113, 56, 113, 70)
s.wire(113, 70, v1b["g"][0], 70)
s.plate_load("R8", "100k", v1b["p"], "B+3")      # tee at (124, 58.9)

# V1B cathode sits above the feedback divider: 1.5 kΩ (bypassed by 25 µF) down to
# node KFB, then 47 Ω to ground; the 2.7 kΩ feedback leg lands on KFB.
s.wire(124, 77.62, 124, 80)
s.sym("R", "R9", "1.5k", 124, 83.81)
s.sym("C", "C5", "25u", 132, 83.81)
s.wire(124, 80, 132, 80)
s.wire(124, 87.62, 132, 87.62)
s.junction(124, 87.62)
s.sym("R", "R10", "47", 124, 91.43)
s.gnd(124, 95.24)
s.wire(112, 87.62, 124, 87.62)
s.sym("R", "R11", "2.7k", 112, 91.43)
s.glabel("SPKR", 112, 95.24, 270)

# ============================ 6V6GT OUTPUT ===========================
s.junction(124, 58.9)
s.wire(124, 58.9, 132, 58.9)
l, r = s.series_h("C", "C6", ".02u", 138, 58.9)
s.wire(132, 58.9, l, 58.9)
s.wire(r, 58.9, 150, 58.9)
s.wire(150, 58.9, 150, 70)
s.junction(150, 70)
s.sym("R", "R12", "220k", 150, 73.81)
s.gnd(150, 77.62)
v2 = s.pentode("V2", "6V6GT", 164, 70)           # p (164,61.745) g2 (171.62,68.73) k (164,76.985)
s.wire(150, 70, v2["g1"][0], 70)
s.wire(v2["g2"][0], v2["g2"][1], 176, v2["g2"][1])
s.glabel("B+2", 176, v2["g2"][1], 0)
s.wire(164, 76.985, 164, 80)
s.shunt_rc("R13", "470 1W", "C7", "25u", 164, 80)
# K2 — the 6V6 cathode/bias node the tremolo oscillator's Intensity control
# injects into (see the tremolo block below); tapped here with a global label
# so the far-off oscillator section can reach it without a sheet-crossing wire.
s.junction(164, 80)
s.wire(164, 80, 182, 80)
s.wire(182, 80, 182, 90)
s.glabel("K2", 182, 90, 270)
s.wire(164, 61.745, 164, 56)
s.sym("OT_SE", "T2", "125A35A", 196, 58.54)      # PRI_P (187.11,56) PRI_B (187.11,61.08)
s.wire(164, 56, 187.11, 56)
s.wire(187.11, 61.08, 183, 61.08)
s.wire(183, 61.08, 183, 64)
s.glabel("B+1", 183, 64, 270)
s.wire(204.89, 56, 209, 56)
s.glabel("SPKR", 209, 56, 0)
s.wire(204.89, 61.08, 209, 61.08)
s.glabel("GND", 209, 61.08, 0)

# ============================ TREMOLO OSCILLATOR (excluded) ==========
# V4A: RC phase-shift oscillator, fed by the Vibrato Pedal jack (J1) and
# tuned by the Speed control (R24, feeding back from the plate to the grid
# through C16). V4B: direct-coupled from V4A's plate (no cap between them —
# bom.yaml lists none), wired as a cathode follower whose plate ties straight
# to B+2 with no plate load and whose cathode, through the Intensity control
# (R27), injects the oscillator's signal directly at K2 (the 6V6 cathode/bias
# node) — the bias-vary mechanism. Dynamic; no static DC point (notes.md);
# excluded from netlist.cir, the same category of exclusion as amps/ab763's V5.
YT = 220
s.caption('Tremolo oscillator (V4) — bias-vary; dynamic, DC point excluded from netlist (notes.md)', 8, YT - 24, 1.4)

# --- Vibrato Pedal jack + bleeder + line coupler ----------------------
j1 = s.jack("J1", "vibrato pedal", 8, YT - 4)
s.text("Vibrato Pedal", 2, YT - 14, 1.2)
s.wire(j1["sleeve"][0], j1["sleeve"][1], j1["sleeve"][0], j1["sleeve"][1] + 5)
s.gnd(j1["sleeve"][0], j1["sleeve"][1] + 5)
s.wire(j1["tip"][0], j1["tip"][1], 20, j1["tip"][1])
s.junction(20, j1["tip"][1])
s.sym("R", "R20", "1M", 20, j1["tip"][1] + 3.81)                 # bleeder to ground
s.gnd(20, j1["tip"][1] + 7.62)
l, r = s.series_h("C", "C15", ".01u", 30, j1["tip"][1])          # jack line coupler
s.wire(20, j1["tip"][1], l, j1["tip"][1])
s.wire(r, j1["tip"][1], 38, j1["tip"][1])
s.wire(38, j1["tip"][1], 38, YT)

# --- V4A: oscillator --------------------------------------------------
t4a = s.triode("V4A", "12AX7", 48, YT)           # p (48,YT-7.62) g (40.38,YT) k (48,YT+7.62)
s.wire(38, YT, t4a["g"][0], YT)
s.junction(38, YT)
s.sym("R", "R21", "1M", 38, YT + 3.81)           # V4A grid leak
s.gnd(38, YT + 7.62)
s.plate_load("R22", "470k", t4a["p"], "B+3")     # tee at (48, YT-7.62-3.48)
s.wire(48, YT + 7.62, 48, YT + 11)
s.shunt_r("R23", "4.7k", 48, YT + 11)             # cathode bias, no bypass

# --- feedback loop: plate tee → C16 → Speed pot → back to the grid ----
tee4 = YT - 7.62 - 3.48                           # = 208.9, the plate-load tee
s.junction(48, tee4)
cl, cr = s.series_h("C", "C16", "not legible", 60, tee4)
s.wire(48, tee4, cl, tee4)
s.wire(cr, tee4, 72, tee4)
s.wire(72, tee4, 72, 232.19)
s.sym("POT", "R24", "3M-RA speed", 72, 236)      # lug1 (72,232.19) lug3 (72,239.81)
s.sym("R", "R25", "100k", 72, 243.81)            # fixed leg, lug3 → ground
s.wire(72, 239.81, 72, 240)
s.gnd(72, 247.62)
s.wire(77.08, 236, 84, 236)                       # wiper (lug2) feeds back to the grid
s.wire(84, 236, 84, 250)
s.wire(84, 250, 38, 250)
s.wire(38, 250, 38, YT)

# --- V4B: direct-coupled cathode follower ------------------------------
t4b = s.triode("V4B", "12AX7", 96, YT)           # p (96,YT-7.62) g (88.38,YT) k (96,YT+7.62)
s.wire(48, tee4, 88.38, tee4)                     # V4A plate tee → V4B grid, direct-coupled
s.wire(88.38, tee4, 88.38, YT)
s.wire(96, YT - 7.62, 96, YT - 11)
s.glabel("B+2", 96, YT - 11, 90)                  # plate tied straight to B+2, no plate load
s.wire(96, YT + 7.62, 96, YT + 11)
s.junction(96, YT + 11)
s.shunt_r("R26", "68k", 96, YT + 11)              # cathode bias, straight to ground
s.wire(96, YT + 11, 116, YT + 11)                 # tee sideways to the Intensity control
s.sym("POT", "R27", "25k-RA int", 116, YT + 14.81)  # lug1 (116,YT+11) lug3 (116,YT+18.62)
s.wire(116, YT + 18.62, 116, YT + 22.43)
s.gnd(116, YT + 22.43)
s.wire(121.08, YT + 14.81, 130, YT + 14.81)       # wiper (lug2) → injection line
s.wire(130, YT + 14.81, 130, YT - 4)
s.glabel("K2", 130, YT - 4, 90)                   # → 6V6 cathode/bias node

# ============================ POWER SUPPLY ===========================
YPW = 150.0
s.note('Power supply — TR1 125P1B, 315-0-315 V, 5Y3GT full-wave, three 20 µF · 450 V sections')
pt = s.pt("T1", "125P1B", 40, YPW)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])

s.glabel("HT_A", 70, 138, 90)
s.wire(70, 138, 70, 140.5)
s.diode_tube("V3A", "5Y3GT", 70, 148.12, lx=-11.4)
s.glabel("HT_B", 82, 138, 90)
s.wire(82, 138, 82, 140.5)
s.diode_tube("V3B", "5Y3GT", 82, 148.12, lx=6.0)
s.wire(70, 155.74, 70, 158)
s.wire(82, 155.74, 82, 158)
s.wire(70, 158, 96, 158)
s.junction(82, 158)
s.junction(88, 158)
s.sym("C", "C8", "20u", 88, 161.81)
s.gnd(88, 165.62)
s.glabel("B+1", 96, 158, 0)
s.wire(96, 158, 100.19, 158)
s.series_h("R", "R14", "1k 1W", 104, 158)
s.wire(107.81, 158, 118, 158)
s.junction(112, 158)
s.glabel("B+2", 112, 153, 90)
s.wire(112, 153, 112, 158)
s.junction(116, 158)
s.sym("C", "C9", "20u", 116, 161.81)
s.gnd(116, 165.62)
s.wire(118, 158, 120.19, 158)
s.series_h("R", "R15", "10k 1W", 124, 158)
s.wire(127.81, 158, 138, 158)
s.junction(132, 158)
s.glabel("B+3", 132, 153, 90)
s.wire(132, 153, 132, 158)
s.sym("C", "C10", "20u", 138, 161.81)
s.gnd(138, 165.62)

# period across-the-line capacitor (not fitted in modern builds)
s.text("Period across-the-line capacitor (omitted in modern builds)", 160, 136, 1.3)
s.glabel("MAINS", 160, 145, 180)
s.wire(160, 145, 164.19, 145)
s.sym("C", "C11", ".047u 600V", 168, 145, rot=90, lx=-3.2, ly=-6.2)
s.wire(171.81, 145, 176, 145)
s.gnd(176, 145)

s.write(OUT)
print(f"wrote {OUT}")
