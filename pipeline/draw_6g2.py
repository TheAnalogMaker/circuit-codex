#!/usr/bin/env python3
"""Generate amps/6g2/schematic.kicad_sch from the stage-template library.

Values per the published 6G2 Princeton (H-FA) drawing (see amps/6g2/meta.yaml).
Signal flows left->right: two-jack input (V1A) -> a single-knob Tone/Volume
network -> V1B second stage -> a cathodyne phase inverter (V2A) -> a
fixed-bias 6V6GT pair. The bias-vary tremolo oscillator (V2B, the OTHER half
of the cathodyne's own bottle) sits below with the Intensity control wired
directly into the -35 V bias line; the power and bias supplies sit at the
bottom right.

Rails: BP = +315 (5Y3GT reservoir / OT centre tap / oscillator plate),
BS = +312 (6V6 screens), BD = +280 (preamp/PI rail); -35V is the fixed-bias
line the Intensity control rides on. Heaters, PT primary/mains, the pilot
lamp and the chassis switches are omitted here (annotation layer) — see
netlist.cir, meta.yaml, and the board layout (layout.yaml).

The tremolo oscillator IS drawn — plate load, Speed control and output
coupling into Intensity are all resolved facts from the sheet. Its own
phase-shift RC ladder is NOT: bom.yaml records the count and rough values as
unresolved from this scan, so — like the AC15's vibrato/tremolo networks —
this drawing names the ladder's interfaces (grid, cathode, Speed tap) with
global labels and asserts nothing about their interconnection. Its DC
operating point alone is excluded from netlist.cir regardless (a running
oscillator has no static bias point) — see amps/6g2/notes.md.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g2" / "schematic.kicad_sch"
s = Sch()


def plate_rl(ref: str, val: str, plate: tuple, rail: str, gap: float = 3.48) -> tuple:
    """Draw a plate_load and return the tap point immediately below the
    resistor (the plate's own node, one 0-ohm lead down) so a coupler can tee
    off it without overlapping the resistor's own pins."""
    s.plate_load(ref, val, plate, rail, gap)
    x, py = plate
    return (x, py - gap)


# ============================ TITLE ==================================
s.text("6G2 — Brown Princeton-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts",
       20, 18, 2.2)
s.text("Rails: BP +315 (reservoir · OT centre tap · oscillator plate) · BS +312 screens · BD +280 preamp/PI · bias -35 V (Intensity rides this line)",
       20, 23, 1.3)
s.text("Heaters, PT primary/mains, pilot lamp and chassis switches are omitted here — see netlist.cir, meta.yaml, layout.yaml. The drawing prints the first bottle 7025, a low-noise 12AX7.",
       20, 27, 1.3)

# ============================ INPUT + V1A =============================
s.text("Input — two jacks share a 68k stopper each into a common 1M leak", 12, 46, 1.5)
s.glabel("INPUT-1", 24, 60, 180)
s.wire(24, 60, 28.48, 60)
la, ra = s.series_h("R", "R1", "68k", 32.29, 60)
s.wire(28.48, 60, la, 60)
s.wire(ra, 60, 44, 60)

s.glabel("INPUT-2", 24, 72, 180)
s.wire(24, 72, 28.48, 72)
lb, rb = s.series_h("R", "R2", "68k", 32.29, 72)
s.wire(28.48, 72, lb, 72)
s.wire(rb, 72, 44, 72)

s.wire(44, 60, 44, 72)
s.junction(44, 60)
s.junction(44, 72)
s.junction(44, 66)
s.wire(44, 66, 48, 66)
s.junction(48, 66)
s.sym("R", "RG1", "1M", 48, 69.81)
s.gnd(48, 73.62)

t1a = s.triode("V1A", "7025", 62, 66)
s.wire(48, 66, t1a["g"][0], 66)
s.wire(62, 73.62, 62, 76)
s.shunt_rc("RK1", "1.5k", "C1", "25u", 62, 76)
tapA = plate_rl("RL1", "100k", t1a["p"], "BD")   # (62, 54.9)

# ============================ TONE / VOLUME NETWORK ====================
s.text("Tone/Volume — single-knob cut network (capacitor-coupled Tone; Volume feeds V1B through its own coupler)",
       62, 44, 1.3)
s.wire(tapA[0], tapA[1], 74, tapA[1])
s.junction(*tapA)
cl, cr = s.series_h("C", "C2", ".02u", 77.81, tapA[1])
s.wire(74, tapA[1], cl, tapA[1])
s.wire(cr, tapA[1], 84, tapA[1])
s.wire(84, tapA[1], 84, 66)           # node X down to the row baseline
s.junction(84, tapA[1])
s.junction(84, 66)

# Volume VR2: top = X, bottom = gnd, wiper -> C4 -> V1B grid
s.sym("POT", "VR2", "1M-A", 84, 69.81, ly=-4.2)
s.wire(84, 73.62, 84, 76)
s.gnd(84, 76)
s.wire(89.08, 69.81, 96, 69.81)
cl2, cr2 = s.series_h("C", "C4", ".02u", 100, 69.81)
s.wire(96, 69.81, cl2, 69.81)
s.wire(cr2, 69.81, 108, 69.81)
s.wire(108, 69.81, 108, 66)           # node Y -> V1B grid tee

# Tone: X -> C3 (.0005u mica) -> VR1 (1M-A, wired as a rheostat) -> gnd
s.wire(84, 66, 76, 66)
s.sym("C", "C3", "500p", 76, 69.81, ly=-6.2)
s.sym("POT", "VR1", "1M-A", 76, 77.43, ly=2.2)
s.wire(81.08, 77.43, 81.08, 73.62)
s.wire(81.08, 73.62, 76, 73.62)
s.wire(76, 81.24, 76, 83)
s.gnd(76, 83)
s.text("Tone", 66, 87, 1.2)

# ============================ V1B SECOND STAGE ==========================
t1b = s.triode("V1B", "7025", 122, 66)
s.wire(108, 66, t1b["g"][0], 66)
# RG2 — no discrete part on the drawing: the grid returns to ground at the
# Volume pot's own ground lug. Drawn as a nominal resistor so the netlist's
# modelled node has a schematic home (bom.yaml ref RG2, part/value "—").
s.junction(t1b["g"][0], 66)
s.wire(t1b["g"][0], 66, t1b["g"][0], 69.81)
s.sym("R", "RG2", "1M*", t1b["g"][0], 73.62, lx=3.0)
s.gnd(t1b["g"][0], 77.43)
s.text("* RG2: nominal only — no discrete resistor on this sheet; the grid",
       t1b["g"][0] + 4, 71.5, 1.0)
s.text("  returns to ground at the Volume pot's own ground lug (notes.md)",
       t1b["g"][0] + 4, 74.2, 1.0)

s.wire(122, 73.62, 122, 76)
s.shunt_rc("RK2", "1.5k", "C5", "25u", 122, 76)
tapB = plate_rl("RL2", "100k", t1b["p"], "BD")   # (122, 54.9)

# ============================ CATHODYNE PHASE INVERTER ===================
s.text("Cathodyne phase inverter — plate + tail-junction outputs drive the two 6V6 grids",
       150, 44, 1.4)
s.wire(tapB[0], tapB[1], 140, tapB[1])
s.junction(*tapB)
cl6, cr6 = s.series_h("C", "C6", ".02u", 144.19, tapB[1])
s.wire(140, tapB[1], cl6, tapB[1])
s.wire(cr6, tapB[1], 158.38, tapB[1])
s.wire(158.38, tapB[1], 158.38, 66)

XPI = 172
t2a = s.triode("V2A", "12AX7", XPI, 66)
GX, GY = t2a["g"][0], 66             # (164.38, 66)
s.wire(158.38, 66, GX, GY)
s.junction(GX, GY)
tapPI = plate_rl("RL3", "56k", t2a["p"], "BD")   # (172, 54.9)

# Cathode stack: K -> RKA(1.5k) -> tail junction JPI -> RKB(56k) -> gnd
s.wire(XPI, 73.62, XPI, 76)
s.sym("R", "RKA", "1.5k", XPI, 79.81)
JPI_X, JPI_Y = XPI, 83.62
s.junction(JPI_X, JPI_Y)
s.sym("R", "RKB", "56k", XPI, 87.43)
s.gnd(XPI, 91.24)

# Grid leak RGPI (1M): GPI (grid) -> tail junction JPI — NOT to ground. Two
# separate wire runs meeting only at the resistor's own pins, so nothing
# bypasses it (a single wire spanning grid-to-JPI would short RGPI out).
s.wire(GX, GY, GX, 79.81)
s.sym("R", "RGPI", "1M", GX, 83.62)
s.wire(GX, 87.43, JPI_X, 87.43)
s.wire(JPI_X, 87.43, JPI_X, JPI_Y)

# ============================ OUTPUT COUPLERS + 6V6 PAIR =================
s.text("Output pair — grounded cathodes, fixed bias through 1.5k grid stoppers off the -35 V line",
       200, 44, 1.4)
GY3 = 50          # V3 grid row (plate-side output)
GY4 = JPI_Y        # V4 grid row (tail-junction output)

# plate-side coupler C7 -> V3 grid stopper RG3
s.wire(tapPI[0], tapPI[1], 186, tapPI[1])
s.junction(*tapPI)
cl7, cr7 = s.series_h("C", "C7", ".1u", 190.19, tapPI[1])
s.wire(186, tapPI[1], cl7, tapPI[1])
s.wire(cr7, tapPI[1], 208, tapPI[1])
s.wire(208, tapPI[1], 208, GY3)

# tail-junction coupler C8 -> V4 grid stopper RG4
s.wire(JPI_X, JPI_Y, 186, JPI_Y)
s.junction(JPI_X, JPI_Y)
cl8, cr8 = s.series_h("C", "C8", ".1u", 190.19, JPI_Y)
s.wire(186, JPI_Y, cl8, JPI_Y)
s.wire(cr8, JPI_Y, 208, GY4)

XO = 234
for gy, cref_x, vref, glref in [(GY3, 208, "V3", "RG3"), (GY4, 208, "V4", "RG4")]:
    s.wire(cref_x, gy, XO - 7.62, gy)
    p = s.pentode(vref, "6V6GT", XO, gy)
    s.junction(216, gy)
    s.sym("R", glref, "1.5k", 216, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(216, gy + 7.62, 216, gy + 10.16)
    s.glabel("-35V", 216, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6, p["g2"][1])
    s.glabel("BS", p["g2"][0] + 6, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])
    if vref == "V3":
        p3 = p
    else:
        p4 = p

# ---- output transformer ---------------------------------------------
s.sym("OT_PP", "T2", "125A10B", 266, 66, lx=-6.35, ly=-14.5)
s.wire(XO, p3["p"][1], XO, p3["p"][1] - 3.745)
s.wire(XO, p3["p"][1] - 3.745, 257.11, p3["p"][1] - 3.745)
s.wire(257.11, p3["p"][1] - 3.745, 257.11, 60.92)
s.wire(XO, p4["p"][1], XO, p4["p"][1] + 4.255)
s.wire(XO, p4["p"][1] + 4.255, 252, p4["p"][1] + 4.255)
s.wire(252, p4["p"][1] + 4.255, 252, 71.08)
s.wire(252, 71.08, 257.11, 71.08)
s.wire(257.11, 66, 248, 66)
s.glabel("BP", 248, 66, 180)
s.wire(274.89, 63.46, 278, 63.46)
s.glabel("SPKR", 278, 63.46, 0)
s.wire(274.89, 68.54, 278, 68.54)
s.glabel("GND", 278, 68.54, 0)
s.text("No negative-feedback resistor found on the published drawing — open loop", 244, 100, 1.2)

# ============================ TREMOLO OSCILLATOR =========================
YT = 150
s.text("Bias-vary tremolo — V2B phase-shift oscillator (the other half of the cathodyne's own 12AX7 bottle)",
       20, 130, 1.5)
s.text("Its DC point alone is excluded from netlist.cir — a running oscillator has no static operating point (notes.md)",
       20, 135, 1.3)
s.text("The phase-shift RC ladder between grid/cathode and the Speed tap is NOT resolved from this scan (bom.yaml):",
       20, 140, 1.2)
s.text("its interfaces are named below and nothing further is asserted about their interconnection — cf. amps/ac15.",
       20, 144.5, 1.2)

t2b = s.triode("V2B", "12AX7", 70, YT)
# Plate: RL4 (56k) straight to BP (the driven reservoir, not the derived BD
# rail) — a tee also feeds the resolved R4/C9 output chain into Intensity.
s.wire(70, YT - 7.62, 70, YT - 11.1)
s.sym("R", "RL4", "56k", 70, YT - 14.91)
s.wire(70, YT - 18.72, 70, YT - 21.27)
s.glabel("BP", 70, YT - 21.27, 90)
s.junction(70, YT - 11.1)
ml, mr = s.series_h("R", "R4", "220k", 90, YT - 11.1)
s.wire(70, YT - 11.1, ml, YT - 11.1)
cl9, cr9 = s.series_h("C", "C9", ".1u", 106, YT - 11.1)
s.wire(mr, YT - 11.1, cl9, YT - 11.1)
s.wire(cr9, YT - 11.1, 116, YT - 11.1)
s.glabel("OSC-OUT", 116, YT - 11.1, 0)

# Grid — the ladder's far interface, named and left unconnected (unresolved).
s.wire(t2b["g"][0], t2b["g"][1], t2b["g"][0], YT + 4)
s.wire(t2b["g"][0], YT + 4, 40, YT + 4)
s.glabel("OSC-LAD-G", 40, YT + 4, 180)
# Cathode — no component appears in bom.yaml for this leg either.
s.wire(70, YT + 7.62, 70, YT + 15)
s.glabel("OSC-LAD-K", 70, YT + 15, 90)
s.text("cathode network not resolved from this scan", 78, YT + 14, 1.0)

# Speed control (VR3, 3M-RA) wired as a rheostat with its own 100k end
# resistor to ground — the LOCAL wiring is a resolved fact; which ladder tap
# its hot lug reads from the sheet is not, so that lug is left named, not wired.
s.sym("POT", "VR3", "3M-RA", 40, YT - 25, lx=-9.5, ly=1.0)
s.glabel("OSC-LAD-SPD", 40, YT - 32.62, 90)
s.wire(40, YT - 28.81, 40, YT - 32.62)
s.wire(45.08, YT - 25, 45.08, YT - 21.19)
s.wire(45.08, YT - 21.19, 40, YT - 21.19)
s.junction(40, YT - 21.19)
s.sym("R", "R3", "100k", 40, YT - 17.38)
s.gnd(40, YT - 13.57)
s.text("Speed", 24, YT - 26, 1.2)

# ============================ POWER SUPPLY ===============================
YPW = 190
BY = YPW + 6
s.text("Power supply — T1 125P1A, 5Y3GT full-wave; T2 125A10B output transformer",
       150, 130, 1.5)
pt = s.pt("T1", "125P1A", 168, YPW, lx=-6.35, ly=-12.5)
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
s.glabel("HT_A", 200, YPW - 14, 90)
s.wire(200, YPW - 14, 200, YPW - 11.5)
s.diode_tube("V5A", "5Y3GT", 200, YPW - 3.88, lx=-11.8)
s.glabel("HT_B", 212, YPW - 14, 90)
s.wire(212, YPW - 14, 212, YPW - 11.5)
s.diode_tube("V5B", "5Y3GT", 212, YPW - 3.88, lx=6.2)
s.wire(200, YPW + 3.74, 200, BY)
s.wire(212, YPW + 3.74, 212, BY)
s.wire(200, BY, 224, BY)
s.junction(212, BY)
s.junction(218, BY)
s.sym("C", "C11", "30u 450V", 218, BY + 3.81)
s.gnd(218, BY + 7.62)
s.junction(224, BY)
s.wire(224, BY - 3.5, 224, BY)
s.glabel("BP", 224, BY - 3.5, 90)
l, r = s.series_h("R", "RD1", "1k 1W", 230, BY)
s.wire(224, BY, l, BY)
s.wire(r, BY, 244, BY)
s.junction(238, BY)
s.wire(238, BY - 3.5, 238, BY)
s.glabel("BS", 238, BY - 3.5, 90)
s.junction(242, BY)
s.sym("C", "C12", "30u 450V", 242, BY + 3.81)
s.gnd(242, BY + 7.62)
l, r = s.series_h("R", "RD2", "10k 1W", 250, BY)
s.wire(244, BY, l, BY)
s.wire(r, BY, 264, BY)
s.junction(258, BY)
s.wire(258, BY - 3.5, 258, BY)
s.glabel("BD", 258, BY - 3.5, 90)
s.sym("C", "C13", "30u 450V", 264, BY + 3.81)
s.gnd(264, BY + 7.62)

# ============================ BIAS SUPPLY =================================
YBI = 222
s.text("Bias supply — a 100k feed off one HT leg, a rectifier, 25 uF and a 30k bleeder set a fixed -35 V raw node",
       150, 214, 1.4)
s.glabel("HT_B", 150, YBI, 180)
l, r = s.series_h("R", "R5", "100k 5%", 164, YBI)
s.wire(150, YBI, l, YBI)
s.wire(r, YBI, 173.92, YBI)
s.sym("DIODE_SS", "D1", "selenium", 179, YBI, lx=-3.4, ly=-5.6)
s.wire(184.08, YBI, 190, YBI)
s.junction(190, YBI)
s.sym("C", "C14", "25u", 190, YBI + 3.81)
s.gnd(190, YBI + 7.62)
s.wire(190, YBI, 200, YBI)
s.junction(200, YBI)
s.sym("R", "R6", "30k 5%", 200, YBI + 3.81)
s.gnd(200, YBI + 7.62)
s.wire(200, YBI, 212, YBI)

# ---- Intensity (VR4, 250k-L) sits directly IN the -35 V bias line: the raw
# node above feeds lug1, the oscillator's AC-only output feeds lug3, and the
# WIPER — the node that actually reaches both 6V6 grid stoppers — carries
# both the fixed DC level and (capacitively) the oscillator's modulation.
s.text("Intensity sits IN the bias line (not a grid-leak network): raw -35 V on one lug, the oscillator's AC output on",
       150, 234, 1.15)
s.text("the other; the WIPER is the -35V line the 6V6 grid stoppers see, with C10 bypassing it to ground.",
       150, 238, 1.15)
s.wire(212, YBI, 212, 244)
s.sym("POT", "VR4", "250k-L", 212, 247.81)
s.wire(212, 251.62, 212, 254)
s.glabel("OSC-OUT", 212, 254, 270)
s.wire(217.08, 247.81, 224, 247.81)
s.junction(224, 247.81)
s.wire(224, 247.81, 224, 244)
s.glabel("-35V", 224, 244, 90)
s.sym("C", "C10", ".05u", 224, 251.62, lx=2.8, ly=-3.2)
s.gnd(224, 255.43)

s.write(OUT, [], paper="A3")
print(f"wrote {OUT}")
