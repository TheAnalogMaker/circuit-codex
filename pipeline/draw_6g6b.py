#!/usr/bin/env python3
"""Generate amps/6g6b/schematic.kicad_sch from the stage-template library.

Values per the published Fender "Bassman" Model 6G6-B drawing (E-FB), schematic
page — see amps/6g6b/meta.yaml. Re-read from the source PDF at 800 dpi for this
pass (the meta.yaml citation covers the original chart-reading pass; the values
below match it). Two full channels (Bass, Normal), each two preamp stages with
its own Bass/Treble/Volume tone network, mix at a shared driver bottle (V3)
ahead of a long-tailed-pair phase inverter (V4) and a fixed-bias 5881 pair
(V5/V6) off a solid-state bridge rectifier — there is no rectifier tube.

Valve numbering follows the drawing: V1 = Bass channel (both stages), V2 =
Normal channel (both stages), V3 = shared driver + the Bass channel's own
Treble control (sitting in V3's own signal path), V4 = phase inverter, V5/V6 =
output pair.

Two engineering estimates are drawn and captioned inline (matching bom.yaml):
V1B's own plate load (mirrored from V1A, not itself legible on the available
scan) and the V1A -> V1B interstage coupling cap (C0, a conventional value —
some DC-blocking cap is circuit-necessary there, but its printed value was not
legible). Heaters, the PT primary, the ground switch, the 3 A fuse and the
standby switch are omitted (see netlist.cir / meta.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g6b" / "schematic.kicad_sch"
s = Sch()

MIXG_X = 245.0  # vertical bus carrying both channels' Volume outputs to V3A's grid

# ============================ BASS CHANNEL (V1A/V1B) =========================
BY = 40.0
t1a = s.triode("V1A", "7025", 54, BY)
gx = t1a["g"][0]
s.glabel("BASS2", 20, BY - 4, 180)
s.wire(20, BY - 4, 26, BY - 4)
hl, hr = s.series_h("R", "R1s", "68k", 31, BY - 4)
s.wire(26, BY - 4, hl, BY - 4)
s.wire(hr, BY - 4, gx - 3.81, BY - 4)
s.wire(gx - 3.81, BY - 4, gx - 3.81, BY)
s.glabel("BASS1", 20, BY + 6, 180)
s.wire(20, BY + 6, 26, BY + 6)
ll, lr = s.series_h("R", "R2s", "68k", 31, BY + 6)
s.wire(26, BY + 6, ll, BY + 6)
s.wire(lr, BY + 6, gx - 3.81, BY + 6)
s.wire(gx - 3.81, BY + 6, gx - 3.81, BY)
s.junction(gx - 3.81, BY)
s.wire(gx - 3.81, BY, gx, BY)
s.sym("R", "RG1A", "1M", gx - 3.81, BY + 9, lx=-9.4)
s.gnd(gx - 3.81, BY + 12.81)
# V1A cathode: 2700 || 25uF dual-can (drawn as one equivalent cap)
s.wire(54, BY + 7.62, 54, BY + 10)
s.wire(54, BY + 10, 60, BY + 10)
s.shunt_rc("RK1A", "2700", "CK1A", "25u", 60, BY + 10)
# V1A plate -> 220k -> shared +230V rail
s.plate_load("RL1A", "220k", t1a["p"], "BP230")
P1A_Y = BY - 7.62 - 3.48
s.wire(54, P1A_Y, 54, P1A_Y)

# V1A plate -> C0 (interstage coupler, estimate) -> V1B grid
t1b = s.triode("V1B", "7025", 92, BY)
gx1b = t1b["g"][0]
s.junction(54, P1A_Y)
s.wire(54, P1A_Y, 62, P1A_Y)
cl, cr = s.series_h("C", "C0", ".1u (est)", 66, P1A_Y)
s.wire(62, P1A_Y, cl, P1A_Y)
s.wire(cr, P1A_Y, gx1b - 3.81, P1A_Y)
s.wire(gx1b - 3.81, P1A_Y, gx1b - 3.81, BY)
s.wire(gx1b - 3.81, BY, gx1b, BY)
s.sym("R", "RG1B", "1M", gx1b - 3.81, BY + 9, lx=-9.4)
s.gnd(gx1b - 3.81, BY + 12.81)
# V1B cathode: 100k, UNBYPASSED
s.wire(92, BY + 7.62, 92, BY + 10)
s.sym("R", "RK1B", "100k", 92, BY + 13.81)
s.gnd(92, BY + 17.62)
# V1B plate -> 220k (estimate) -> shared +230V rail; plate stub tees into the
# Bass tone network
s.plate_load("RL1B", "220k (est)", t1b["p"], "BP230")
NA_Y = BY - 7.62 - 3.48
s.junction(92, NA_Y)

# --- Bass tone network: NA (V1B plate) -> [1M || (.00025+47k)] -> NX; NX ->
# 10k || VR1(Bass) -> NY; NY -> 820 -> gnd; NX -> VR2(Volume) -> wiper = MIXG
NW_Y = NA_Y + 20
s.wire(92, NA_Y, 100, NA_Y)
rl, rr = s.series_h("R", "RTN2", "1M", 104, NW_Y - 10)
s.wire(100, NA_Y, 100, NW_Y - 10)
s.wire(100, NW_Y - 10, rl, NW_Y - 10)
s.wire(100, NA_Y, 100, NA_Y - 15)
cl2, cr2 = s.series_h("C", "CTN1", "250p", 100, NA_Y - 15)
s.wire(cr2, NA_Y - 15, 120, NA_Y - 15)
tl, tr = s.series_h("R", "RTN1", "47k", 120, NW_Y - 10)
s.wire(120, NA_Y - 15, 120, NW_Y - 10)
s.junction(120, NW_Y - 10)
s.wire(rr, NW_Y - 10, 120, NW_Y - 10)
NX = (120, NW_Y - 10)
# bridging caps: NW (bottom of RTN2) -> CTN2 -> NX ; NW -> CTN3 -> NY
NW = (104 + 3.81, NW_Y)
s.wire(rl - 3.81, NW_Y - 10, rl - 3.81, NW_Y)
s.junction(rl - 3.81, NW_Y)
bl, br = s.series_h("C", "CTN2", ".25u", 112, NW_Y)
s.wire(rl - 3.81, NW_Y, bl, NW_Y)
s.wire(br, NW_Y, 120, NW_Y)
s.wire(120, NW_Y, 120, NW_Y - 10 + 7.62)
s.junction(120, NW_Y)
NY_Y = NW_Y + 20
s.wire(rl - 3.81, NW_Y, rl - 3.81, NY_Y)
bl2, br2 = s.series_h("C", "CTN3", ".25u", 112, NY_Y)
s.wire(rl - 3.81, NY_Y, bl2, NY_Y)
s.wire(br2, NY_Y, 120, NY_Y)
dl, dr = s.series_h("R", "RTN3", "10k", 120, NW_Y - 10 + 20)
s.wire(120, NW_Y - 10 + 7.62 + 4.19, 120, NW_Y - 10 + 20 - 3.81)
s.wire(120, NY_Y, 120, NW_Y - 10 + 20 + 3.81)
NY = (120, NY_Y)
# Bass pot (25k-L) in parallel with RTN3, wiper strapped to its own hot lug
s.sym("POT", "VR1", "25k-L", 132, NW_Y - 10 + 20, lx=2.4, ly=-1.5)
s.wire(120, NW_Y - 10 + 16.19, 132, NW_Y - 10 + 16.19)
s.wire(132, NW_Y - 10 + 16.19, 132, NW_Y - 10 + 16.19)
s.wire(120, NW_Y - 10 + 23.81, 132, NW_Y - 10 + 23.81)
s.wire(137.08, NW_Y - 10 + 20, 140, NW_Y - 10 + 20)
s.wire(140, NW_Y - 10 + 20, 140, NW_Y - 10 + 16.19)
s.wire(140, NW_Y - 10 + 16.19, 132, NW_Y - 10 + 16.19)
# foot: NY -> 820 -> ground
s.sym("R", "RBF", "820", 120, NY_Y + 12.19)
s.gnd(120, NY_Y + 16)
# Volume pot, top fed from NX, wiper -> MIXG
s.wire(120, NW_Y - 10, 148, NW_Y - 10)
s.sym("POT", "VR2", "250k-L", 148, NW_Y - 10 + 3.81)
s.gnd(148, NW_Y - 10 + 7.62 + 3.81)
s.wire(148, NW_Y - 10 + 7.62, 148, NW_Y - 10 + 11.43)
s.wire(153.08, NW_Y - 10, MIXG_X, NW_Y - 10)
s.wire(MIXG_X, NW_Y - 10, MIXG_X, 152)
s.text("Bass ch. tone network: redrawn from the E-FB schematic page. NW/NY "
       "bridging exactly as the source drawing wires it (best-effort read of a",
       20, 90, 1.15)
s.text("hand-drawn print — not a trace); the network is not modelled in "
       "netlist.cir (abstracted control island, same convention corpus-wide).",
       20, 93.5, 1.15)

# ============================ NORMAL CHANNEL (V2A/V2B) ========================
NY0 = 130.0
t2a = s.triode("V2A", "7025", 54, NY0)
gx2 = t2a["g"][0]
s.glabel("NORM2", 20, NY0 - 4, 180)
s.wire(20, NY0 - 4, 26, NY0 - 4)
hl, hr = s.series_h("R", "R3s", "68k", 31, NY0 - 4)
s.wire(26, NY0 - 4, hl, NY0 - 4)
s.wire(hr, NY0 - 4, gx2 - 3.81, NY0 - 4)
s.wire(gx2 - 3.81, NY0 - 4, gx2 - 3.81, NY0)
s.glabel("NORM1", 20, NY0 + 6, 180)
s.wire(20, NY0 + 6, 26, NY0 + 6)
ll, lr = s.series_h("R", "R4s", "68k", 31, NY0 + 6)
s.wire(26, NY0 + 6, ll, NY0 + 6)
s.wire(lr, NY0 + 6, gx2 - 3.81, NY0 + 6)
s.wire(gx2 - 3.81, NY0 + 6, gx2 - 3.81, NY0)
s.junction(gx2 - 3.81, NY0)
s.wire(gx2 - 3.81, NY0, gx2, NY0)
s.sym("R", "RG2A", "1M", gx2 - 3.81, NY0 + 9, lx=-9.4)
s.gnd(gx2 - 3.81, NY0 + 12.81)
s.wire(54, NY0 + 7.62, 54, NY0 + 10)
s.wire(54, NY0 + 10, 60, NY0 + 10)
s.shunt_rc("RK2A", "1500", "CK2A", "25u", 60, NY0 + 10)
s.plate_load("RL2A", "100k", t2a["p"], "BP230")
P2A_Y = NY0 - 7.62 - 3.48
s.junction(54, P2A_Y)

# --- Normal tone network: P2A -> CTN4(250p) -> Treble pot top (350k/70k tap);
# P2A -> CTN5(.05u) -> Bass-leg node NB -> RTN4(6.8k)+VR4(Bass) -> gnd;
# Treble bottom lug -> NB; Treble wiper -> Volume top; Volume wiper -> V2B grid
s.wire(54, P2A_Y, 100, P2A_Y)
cl3, cr3 = s.series_h("C", "CTN4", "250p", 108, P2A_Y - 12)
s.wire(100, P2A_Y, 100, P2A_Y - 12)
s.wire(100, P2A_Y - 12, cl3, P2A_Y - 12)
s.sym("POT", "VR3", "350k-70k", 128, P2A_Y - 12 + 3.81, lx=2.4, ly=-1.5)
s.wire(cr3, P2A_Y - 12, 128, P2A_Y - 12)
s.wire(54, P2A_Y, 54, P2A_Y + 15)
cl4, cr4 = s.series_h("C", "CTN5", ".05u", 100, P2A_Y + 15)
s.wire(54, P2A_Y + 15, cl4, P2A_Y + 15)
NB = (128, P2A_Y + 15)
s.wire(cr4, P2A_Y + 15, 128, P2A_Y + 15)
s.wire(128, P2A_Y + 15, 128, P2A_Y - 12 + 3.81 - 3.81)
s.sym("R", "RTN4", "6800", 128, P2A_Y + 15 + 12.19)
s.gnd(128, P2A_Y + 15 + 16)
s.sym("C", "CTN6", ".005u", 118, P2A_Y + 15 + 12.19, lx=-8.0, ly=3.0)
s.wire(122.03, P2A_Y + 15 + 12.19, 128, P2A_Y + 15 + 12.19)
s.gnd(118, P2A_Y + 15 + 15.99)
s.sym("POT", "VR4", "250k-A", 140, P2A_Y + 15, lx=2.4, ly=-1.5)
s.wire(128, P2A_Y + 15, 132.19, P2A_Y + 15)
s.wire(145.08, P2A_Y + 15, 148, P2A_Y + 15)
s.gnd(148, P2A_Y + 15)
s.wire(128, P2A_Y - 12 + 3.81 + 3.81, 148, P2A_Y - 12 + 3.81 + 3.81)
s.wire(148, P2A_Y - 12 + 3.81 + 3.81, 148, P2A_Y + 15)
s.text("Normal ch. tone network: redrawn from the E-FB schematic page — a "
       "treble-bleed + bass-leg network feeding a Volume pot ahead of V2B.",
       20, 200, 1.15)
# Treble wiper -> Volume pot top; Volume wiper -> V2B grid
t2b = s.triode("V2B", "7025", 190, NY0)
gx2b = t2b["g"][0]
s.wire(133.08, P2A_Y - 12 + 3.81, 160, P2A_Y - 12 + 3.81)
s.sym("POT", "VR5", "1M-A", 168, P2A_Y - 12 + 3.81 + 3.81, lx=2.4, ly=-1.5)
s.wire(160, P2A_Y - 12 + 3.81, 168, P2A_Y - 12 + 3.81)
s.gnd(168, P2A_Y - 12 + 3.81 + 11.43)
s.wire(168, P2A_Y - 12 + 3.81 + 7.62, 168, P2A_Y - 12 + 3.81 + 11.43)
s.wire(173.08, P2A_Y - 12 + 3.81 + 3.81, 180, P2A_Y - 12 + 3.81 + 3.81)
s.wire(180, P2A_Y - 12 + 3.81 + 3.81, 180, NY0)
s.wire(180, NY0, gx2b, NY0)
s.sym("R", "RG2B", "1M (est)", gx2b - 3.81, NY0 + 9, lx=-9.4)
s.gnd(gx2b - 3.81, NY0 + 12.81)
s.wire(gx2b - 3.81, NY0, gx2b - 3.81, NY0 - 3)
s.wire(gx2b - 3.81, NY0 - 3, 180, NY0 - 3)
s.wire(180, NY0 - 3, 180, P2A_Y - 12 + 3.81 + 3.81 - 3)
s.junction(180, NY0)
# V2B cathode + plate off dedicated +355V rail
s.wire(190, NY0 + 7.62, 190, NY0 + 10)
s.wire(190, NY0 + 10, 196, NY0 + 10)
s.shunt_rc("RK2B", "2700", "CK2B", "25u", 196, NY0 + 10)
s.plate_load("RL2B", "220k", t2b["p"], "BP355")
P2B_Y = NY0 - 7.62 - 3.48
s.junction(190, P2B_Y)
s.wire(190, P2B_Y, 196, P2B_Y)
ml, mr = s.series_h("R", "RM1", "470k", 200, P2B_Y)
s.wire(196, P2B_Y, ml, P2B_Y)
s.wire(mr, P2B_Y, MIXG_X, P2B_Y)
s.wire(MIXG_X, P2B_Y, MIXG_X, 152)

# ============================ MIXING NODE -> SHARED DRIVER ====================
s.junction(MIXG_X, 152)
s.wire(MIXG_X, 152, 232, 152)

# ============================ SHARED DRIVER (V3A/V3B) + BASS TREBLE ==========
DY = 152.0
t3a = s.triode("V3A", "7025", 240, DY)
s.wire(232, 152, t3a["g"][0], DY)
s.sym("R", "RG3A", "1M (est)", t3a["g"][0] - 3.81, DY + 9, lx=-9.4)
s.gnd(t3a["g"][0] - 3.81, DY + 12.81)
s.wire(t3a["g"][0] - 3.81, DY, t3a["g"][0] - 3.81, DY + 5.19)
s.wire(240, DY + 7.62, 240, DY + 10)
s.wire(240, DY + 10, 246, DY + 10)
s.shunt_r("RK3A", "1500 (est)", 246, DY + 10)
s.plate_load("RL3A", "100k", t3a["p"], "BP230")
P3A_Y = DY - 7.62 - 3.48
s.wire(240, P3A_Y, 250, P3A_Y)
cl5, cr5 = s.series_h("C", "CDR1", ".1u", 254, P3A_Y)
s.wire(250, P3A_Y, cl5, P3A_Y)
s.sym("POT", "VR6", "250k-A · Bass Treble", 272, P3A_Y + 3.81, lx=2.4, ly=-1.5)
s.wire(cr5, P3A_Y, 272, P3A_Y)
s.gnd(272, P3A_Y + 7.62 + 3.81)
s.wire(272, P3A_Y + 7.62, 272, P3A_Y + 7.62 + 3.81)
t3b = s.triode("V3B", "7025", 296, DY)
s.wire(277.08, P3A_Y + 3.81, 296, P3A_Y + 3.81)
s.wire(296, P3A_Y + 3.81, 296, DY)
s.wire(296, DY, t3b["g"][0], DY)
s.junction(296, P3A_Y + 3.81)
s.sym("R", "RG3B", "1M (est)", t3b["g"][0] - 3.81, DY + 9, lx=-9.4)
s.gnd(t3b["g"][0] - 3.81, DY + 12.81)
s.wire(t3b["g"][0] - 3.81, DY, t3b["g"][0] - 3.81, DY + 5.19)
s.wire(296, DY + 7.62, 296, DY + 10)
s.wire(296, DY + 10, 302, DY + 10)
s.shunt_r("RK3B", "1500", 302, DY + 10)
s.plate_load("RL3B", "100k", t3b["p"], "BP230")
P3B_Y = DY - 7.62 - 3.48
s.wire(296, P3B_Y, 306, P3B_Y)
ml2, mr2 = s.series_h("R", "RM2", "470k", 310, P3B_Y)
s.wire(306, P3B_Y, ml2, P3B_Y)

# ============================ PHASE INVERTER (V4A/V4B) ========================
GL = 340.0
RC = 328.0
JY = 200.0
PIY_A = 200.0
PIY_B = 236.0
cl6, cr6 = s.series_h("C", "C1", "500p", 322, P3B_Y)
s.wire(mr2, P3B_Y, cl6, P3B_Y)
s.wire(cr6, P3B_Y, GL, P3B_Y)
t4a = s.triode("V4A", "7025", 348, PIY_A)
s.wire(GL, P3B_Y, GL, PIY_A)
s.wire(GL, PIY_A, t4a["g"][0], PIY_A)
s.junction(GL, PIY_A)
t4b = s.triode("V4B", "7025", 348, PIY_B)
s.plate_load("RL4A", "82k · 5%", t4a["p"], "BP410")
s.plate_load("RL4B", "100k · 5%", t4b["p"], "BP410")
# shared tail: cathodes -> 820 -> J -> 10k (est) -> gnd
s.wire(348, PIY_A + 7.62, 348, PIY_A + 10)
s.wire(348, PIY_A + 10, 354, PIY_A + 10)
s.wire(348, PIY_B + 7.62, 348, PIY_B + 10)
s.wire(348, PIY_B + 10, 354, PIY_B + 10)
s.wire(354, PIY_A + 10, 354, PIY_B + 10)
s.junction(354, PIY_B + 10)
rl3, rr3 = s.series_h("R", "RTAIL", "820", 362, PIY_A + 10 + 18)
s.wire(354, PIY_A + 10, 354, PIY_A + 10 + 18)
s.wire(354, PIY_A + 10 + 18, rl3, PIY_A + 10 + 18)
s.wire(rr3, PIY_A + 10 + 18, JY + 60, PIY_A + 10 + 18)
s.wire(JY + 60, PIY_A + 10 + 18, JY + 60, PIY_A + 10 + 30)
s.sym("R", "RFOOT", "10k (est)", JY + 60, PIY_A + 10 + 30 + 3.81)
s.gnd(JY + 60, PIY_A + 10 + 30 + 7.62)
TAIL_X = JY + 60
TAIL_Y = PIY_A + 10 + 30
# grid leaks, both returned to the tail junction
s.wire(GL, PIY_A, GL, PIY_A + 4)
s.sym("R", "RG4A", "1M", GL, PIY_A + 7.81, lx=-9.4)
s.wire(GL, PIY_A + 11.62, GL, PIY_A + 14)
s.wire(GL, PIY_A + 14, RC, PIY_A + 14)
s.wire(RC, PIY_A + 14, RC, TAIL_Y)
s.wire(GL, PIY_B, GL, PIY_B + 4)
s.sym("R", "RG4B", "1M", GL, PIY_B + 7.81, lx=-9.4)
s.wire(GL, PIY_B + 11.62, GL, TAIL_Y)
s.wire(GL, PIY_B, t4b["g"][0], PIY_B)
s.wire(RC, TAIL_Y, GL, TAIL_Y)
s.wire(GL, TAIL_Y, TAIL_X, TAIL_Y)
s.junction(RC, TAIL_Y)
s.junction(GL, TAIL_Y)
s.junction(TAIL_X, TAIL_Y)
# presence pot at the tail junction
s.wire(RC - 20, TAIL_Y, RC, TAIL_Y)
s.sym("POT", "VR7", "25k-L · Presence", RC - 20, TAIL_Y + 3.81, lx=-16, ly=6.5)
s.gnd(RC - 20, TAIL_Y + 7.62 + 3.81)
s.wire(RC - 20, TAIL_Y + 7.62, RC - 20, TAIL_Y + 7.62 + 3.81)
s.text("Presence control: front-panel 25 kΩ-L pot at the phase-inverter tail "
       "junction; exact internal tap not traced from the available scan —",
       300, 292, 1.15)
s.note("drawn as a DC-neutral shunt at the tail, matching the corpus's other long-tailed-pair designs.")

# ============================ OUTPUT PAIR (5881) ==============================
OX = 420.0
s.wire(348, PIY_A - 7.62 - 3.48, 348, PIY_A - 7.62 - 3.48)
cl7, cr7 = s.series_h("C", "C2", ".1u", OX - 20, PIY_A - 7.62 - 3.48)
s.wire(348, PIY_A - 7.62 - 3.48, cl7, PIY_A - 7.62 - 3.48)
t5 = s.pentode("V5", "5881", OX, PIY_A, lx=6.2, ly=-8.5)
s.wire(cr7, PIY_A - 7.62 - 3.48, t5["g1"][0], PIY_A - 7.62 - 3.48)
s.wire(t5["g1"][0], PIY_A - 7.62 - 3.48, t5["g1"][0], PIY_A)
s.sym("R", "RGL5", "220k", t5["g1"][0] - 3.81, PIY_A + 9, lx=-9.4)
s.wire(t5["g1"][0] - 3.81, PIY_A, t5["g1"][0] - 3.81, PIY_A + 5.19)
s.wire(t5["g1"][0] - 3.81, PIY_A + 12.81, t5["g1"][0] - 3.81, PIY_A + 16)
s.glabel("NBIAS", t5["g1"][0] - 3.81, PIY_A + 16, 270)
s.wire(t5["g2"][0], t5["g2"][1], t5["g2"][0] + 3, t5["g2"][1])
sc1, sc2 = s.series_h("R", "RS5", "470 · 1W", t5["g2"][0] + 6.81, t5["g2"][1])
s.wire(sc2, t5["g2"][1], t5["g2"][0] + 12, t5["g2"][1])
s.glabel("BP430", t5["g2"][0] + 12, t5["g2"][1], 0)
s.wire(OX, PIY_A - 7.62, OX, PIY_A - 11)
s.glabel("BP428", OX, PIY_A - 11, 90)
s.gnd(OX, t5["k"][1])

cl8, cr8 = s.series_h("C", "C3", ".1u", OX - 20, PIY_B - 7.62 - 3.48)
s.wire(348, PIY_B - 7.62 - 3.48, cl8, PIY_B - 7.62 - 3.48)
s.wire(348, PIY_B, 348, PIY_B - 7.62 - 3.48)
t6 = s.pentode("V6", "5881", OX, PIY_B, lx=6.2, ly=-8.5)
s.wire(cr8, PIY_B - 7.62 - 3.48, t6["g1"][0], PIY_B - 7.62 - 3.48)
s.wire(t6["g1"][0], PIY_B - 7.62 - 3.48, t6["g1"][0], PIY_B)
s.sym("R", "RGL6", "220k", t6["g1"][0] - 3.81, PIY_B + 9, lx=-9.4)
s.wire(t6["g1"][0] - 3.81, PIY_B, t6["g1"][0] - 3.81, PIY_B + 5.19)
s.wire(t6["g1"][0] - 3.81, PIY_B + 12.81, t6["g1"][0] - 3.81, PIY_B + 16)
s.glabel("NBIAS", t6["g1"][0] - 3.81, PIY_B + 16, 270)
s.wire(t6["g2"][0], t6["g2"][1], t6["g2"][0] + 3, t6["g2"][1])
sc3, sc4 = s.series_h("R", "RS6", "470 · 1W", t6["g2"][0] + 6.81, t6["g2"][1])
s.wire(sc4, t6["g2"][1], t6["g2"][0] + 12, t6["g2"][1])
s.glabel("BP430", t6["g2"][0] + 12, t6["g2"][1], 0)
s.wire(OX, PIY_B - 7.62, OX, PIY_B - 11)
s.glabel("BP428", OX, PIY_B - 11, 90)
s.gnd(OX, t6["k"][1])

# ---- output transformer + speaker jacks -------------------------------------
s.sym("OT_PP", "T3", "125A13A", 470, 218, lx=-6.35, ly=-14.0)
s.wire(OX + 6.35, PIY_A - 7.62, OX + 6.35, 200)
s.wire(OX + 6.35, 200, 461.11, 200)
s.wire(OX + 6.35, PIY_B - 7.62, OX + 6.35, 236)
s.wire(OX + 6.35, 236, 458, 236)
s.wire(458, 236, 458, 223.08)
s.wire(461.11, 213, 476, 213)
s.glabel("SPKR", 476, 213, 0)
s.wire(461.11, 223, 476, 223)
s.glabel("GND", 476, 223, 0)
s.text("16 / 8 ohm secondary taps.", 440, 246, 1.4)

# ============================ POWER SUPPLY (solid-state bridge) ==============
PY = 320.0
pt = s.pt("T1", "125P7A", 22, PY - 20, lx=-6.35, ly=-11.9)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 3, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 3, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 3, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 3, pt["ht_b"][1], 0)
s.note('Power — universal power transformer (TR1, 125P7A), centre-tapped HT winding; two 3-diode series legs form a silicon full-wave bridge (no rectifier tube); 20 uF/600V filters either side of the choke (TR2, 125C1A); 4.7 k/1 W and 27 k/1 W droppers feed the driver and preamp taps.')
# Each leg: HT_A (or HT_B) at top -> 3 series diodes -> joins the other leg's
# output at the bottom = B+1 (first filter node). The PT's HT centre tap
# (grounded) is the rectifier's return path, not the diode string itself.
for x, dU, dM, dL, lab in [(44, "DR1", "DR2", "DR3", "HT_A"),
                            (64, "DR4", "DR5", "DR6", "HT_B")]:
    s.sym("DIODE_SS", dU, "1N4007", x, PY + 6, rot=90, lx=2.6, ly=-1.2)
    s.sym("DIODE_SS", dM, "1N4007", x, PY + 16, rot=90, lx=2.6, ly=-1.2)
    s.sym("DIODE_SS", dL, "1N4007", x, PY + 26, rot=90, lx=2.6, ly=-1.2)
    s.wire(x, PY, x, PY + 2.175)
    s.wire(x, PY + 9.825, x, PY + 12.175)
    s.wire(x, PY + 19.825, x, PY + 22.175)
    s.wire(x, PY + 29.825, x, PY + 32)
    s.glabel(lab, x, PY - 3, 90)
    s.wire(x, PY, x, PY - 3)
# HT_A / HT_B legs meet at B+1 (first filter node)
s.wire(44, PY + 32, 64, PY + 32)
s.junction(54, PY + 32)
s.wire(54, PY + 32, 54, PY + 40)
s.wire(54, PY + 40, 90, PY + 40)
s.sym("C", "C10", "20u·600V", 96, PY + 43.81)
s.gnd(96, PY + 47.62)
s.junction(96, PY + 40)
s.wire(90, PY + 40, 96, PY + 40)
dl2, dr2 = s.series_h("R", "RD1", "4700·1W", 106, PY + 40)
s.wire(96, PY + 40, dl2, PY + 40)
s.wire(dr2, PY + 40, 118, PY + 40)
s.sym("CHOKE", "L1", "125C1A", 128, PY + 40)
s.wire(118, PY + 40, 120.38, PY + 40)
s.wire(135.62, PY + 40, 144, PY + 40)
s.sym("C", "C11", "20u·600V", 150, PY + 43.81)
s.gnd(150, PY + 47.62)
s.junction(150, PY + 40)
s.wire(144, PY + 40, 150, PY + 40)
s.wire(150, PY + 40, 150, PY + 34)
s.glabel("BP428", 150, PY + 34, 90)
s.wire(150, PY + 40, 156, PY + 40)
dl3, dr3 = s.series_h("R", "RD2", "27k·1W", 164, PY + 40)
s.wire(156, PY + 40, dl3, PY + 40)
s.wire(dr3, PY + 40, 176, PY + 40)
s.sym("C", "C12", "20u·600V (dual)", 182, PY + 43.81)
s.gnd(182, PY + 47.62)
s.junction(182, PY + 40)
s.wire(176, PY + 40, 182, PY + 40)
s.wire(182, PY + 40, 182, PY + 34)
s.glabel("BP410", 182, PY + 34, 90)
s.wire(182, PY + 40, 188, PY + 40)
s.glabel("BP230", 190, PY + 40, 0)
s.text("BP430 (5881 screens) and BP355 (Normal ch. recovery) tap the same "
       "dropper chain the E-FB drawing shows but were not fully traced at "
       "this pass; both", 20, 320, 1.15)
s.text("are driven directly as ideal sources in netlist.cir, printed at "
       "their own chart values (see meta.yaml).", 20, 323.5, 1.15)
s.glabel("BP430", 30, 340, 0)
s.glabel("BP355", 30, 346, 0)

# ============================ BIAS SUPPLY =====================================
BSY = 300.0
s.glabel("HT_B", 220, BSY, 180)
s.wire(220, BSY, 227.92, BSY)
s.sym("DIODE_SS", "DB1", "1N4148", 233, BSY, rot=180, lx=-2.4, ly=-5.4, label_rot=0)
s.wire(238.08, BSY, 250, BSY)
dl4, dr4 = s.series_h("R", "RB1", "1k·1W·5%", 258, BSY)
s.wire(250, BSY, dl4, BSY)
s.wire(dr4, BSY, 270, BSY)
s.junction(270, BSY)
s.sym("C", "C13", "25/50u", 270, BSY + 3.81, lx=2.2)
s.gnd(270, BSY + 7.62)
dl5, dr5 = s.series_h("R", "RB2", "27k·1W·5%", 280, BSY)
s.wire(270, BSY, dl5, BSY)
s.wire(dr5, BSY, 292, BSY)
s.gnd(292, BSY)
s.wire(292, BSY, 292, BSY - 3.81)
s.junction(292, BSY - 3.81)
s.wire(292, BSY - 3.81, 300, BSY - 3.81)
s.glabel("NBIAS", 300, BSY - 3.81, 0)
s.text("Bias supply: silicon diode off an AC tap, 1 k/4.7 k dropping through "
       "the choke, 27 k bleeder, dual 25/50 uF can -> -54 V.", 220, 312, 1.15)

s.write(OUT, [
    "Two full channels (Bass, Normal), each two preamp stages with its own Bass/Treble/Volume tone network, mixing at a shared driver bottle ahead of a long-tailed-pair phase inverter and a fixed-bias 5881 pair off a solid-state bridge — no rectifier tube.",
    "The Bass channel's own Treble control sits inside the driver bottle's signal path (V3A -> VR6 -> V3B), not beside its Bass/Volume pots. Heaters, PT primary, ground switch, fuse and standby switch omitted.",
])
print(f"wrote {OUT}")
