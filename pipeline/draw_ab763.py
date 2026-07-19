#!/usr/bin/env python3
"""Generate amps/ab763/schematic.kicad_sch from the stage-template library.

Values per the published AB763 Deluxe Reverb-Amp drawing (see amps/ab763/meta.yaml).
The largest sheet in the corpus: two preamp channel rows (Normal, Vibrato) at the
top, the reverb + tremolo block below them, the long-tailed-pair phase inverter and
6V6 output on the right, and the power / bias supply along the bottom. Drawn on A3
to keep every block clear of its neighbours and of the title block (bottom-right).

Redrawn from circuit facts — never a trace of a factory drawing. Rails: B+1 = +415
(6V6 plates, OT centre tap, reverb driver via T4), B+2 = +415 screens (post-choke),
B+3 = +325 (PI plates + 820 Ohm-cathode stages), B+4 = +180 (channel-input rail);
-35 V is the fixed-bias line. Heaters, PT primary/mains, and pilot lamp omitted here
(annotation layer) — see netlist.cir, meta.yaml, and the board layout (layout.yaml).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ab763" / "schematic.kicad_sch"
s = Sch()


def input_stage(y, j1, j2, r1, r2, rleak, vref, vval, rload, rk, ck, ckval, rail):
    """Two-jack input: 68k stoppers -> grid (1M leak) -> triode -> plate load + RC cathode.
    Returns the triode pin dict."""
    gb = 40  # grid-bus x
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(16, y - 4, l, y - 4)
    s.wire(r, y - 4, gb, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(16, y + 4, l, y + 4)
    s.wire(r, y + 4, gb, y + 4)
    s.wire(gb, y - 4, gb, y + 4)
    s.junction(gb, y)
    s.sym("R", rleak, "1M", gb, y + 3.81 + 4)
    s.gnd(gb, y + 7.62 + 4)
    t = s.triode(vref, vval, 52, y)
    s.wire(gb, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], rail)
    s.wire(52, y + 7.62, 52, y + 9)
    s.shunt_rc(rk, "1.5k", ck, ckval, 52, y + 9)
    return t


# ============================ TITLE ==================================
s.text("AB763 — Blackface Deluxe Reverb-style · Circuit Codex · CC-BY-SA 4.0 · redrawn from circuit facts",
       26, 20, 2.2)
s.text("Heaters, PT primary/mains, pilot lamp omitted here — see netlist.cir, meta.yaml, layout.yaml. Rails: B+1 +415 · B+2 +415 screens · B+3 +325 · B+4 +180 · bias -35 V",
       26, 25, 1.3)

# ============================ NORMAL CHANNEL (top row) ================
YN = 62
s.text("Normal channel", 12, 48, 1.6)
t1 = input_stage(YN, "NORM 1", "NORM 2", "R1n", "R2n", "RGN1", "V1", "12AX7",
                 "RLN1", "RKN1", "CKN1", "25u", "B+4")

# normal FMV tone stack + volume: plate -> CBN 0.1u -> stack -> VRVN 1M -> mixer
tee = YN - 7.62 - 3.48
s.wire(52, tee, 64, tee)
s.junction(52, tee)
cl, cr = s.series_h("C", "CBN", ".1u", 68, tee)
s.wire(64, tee, cl, tee)
s.wire(cr, tee, 78, tee)                      # node A (stack input)
# treble: A -> CTN 250p -> VRTN 250k
tl, tr = s.series_h("C", "CTN", "250p", 84, tee - 6)
s.wire(78, tee, 78, tee - 6)
s.wire(78, tee - 6, tl, tee - 6)
s.wire(tr, tee - 6, 92, tee - 6)
s.sym("POT", "VRTN", "250k treb", 92, tee - 6 + 3.81)
# slope: A -> RSN 100k -> VRBN bass top
sl, sr = s.series_h("R", "RSN", "100k", 84, tee + 4)
s.wire(78, tee, 78, tee + 4)
s.junction(78, tee)
s.wire(78, tee + 4, sl, tee + 4)
s.wire(sr, tee + 4, 100, tee + 4)
# bass: node -> CBN2 0.047u -> VRBN 250k -> RSLN 6.8k bleed -> gnd
bl, br = s.series_h("C", "CBN2", ".047u", 100, tee + 4)  # placed inline visually
s.sym("POT", "VRBN", "250k bass", 100, tee + 4 + 7.62)
s.wire(100, tee + 4 + 3.81, 100, tee + 4 + 3.81)
s.sym("R", "RSLN", "6.8k", 100, tee + 4 + 15.24)
s.gnd(100, tee + 4 + 19.05)
# treble wiper + bass wiper -> volume top
s.wire(97.08, tee - 6 + 3.81, 108, tee - 6 + 3.81)   # treble wiper
s.wire(108, tee - 6 + 3.81, 108, tee)
s.sym("POT", "VRVN", "1M vol", 108, tee + 3.81)
s.gnd(108, tee + 11.43)
# volume wiper -> mixer resistor -> PI grid bus (to the right, at PI grid line)
s.wire(113.08, tee + 3.81, 118, tee + 3.81)
ml, mr = s.series_h("R", "RMD1", "220k", 122, tee + 3.81)  # PI-grid mixer resistor shared
s.wire(118, tee + 3.81, ml, tee + 3.81)
s.wire(mr, tee + 3.81, 230, tee + 3.81)       # long run to PI hot grid
s.glabel("PIG", 230, tee + 3.81, 0)

# ============================ VIBRATO CHANNEL (second row) ============
YV = 100
s.text("Vibrato channel (reverb + tremolo)", 12, 86, 1.6)
t2 = input_stage(YV, "VIB 1", "VIB 2", "R1v", "R2v", "RGV1", "V2A", "12AX7",
                 "RLV1", "RKV1", "CKV1", "25u", "B+4")

# vibrato tone stack: plate -> CTV 250p treble w/ CBRV 47p bright; VRTV/VRBV; RSLV
teev = YV - 7.62 - 3.48
s.wire(52, teev, 64, teev)
s.junction(52, teev)
tl, tr = s.series_h("C", "CTV", "250p", 70, teev - 6)
s.wire(64, teev, 64, teev - 6)
s.wire(64, teev - 6, tl, teev - 6)
s.wire(tr, teev - 6, 80, teev - 6)
s.sym("POT", "VRTV", "250k treb", 80, teev - 6 + 3.81)
# bright cap across treble pot (top->wiper)
s.wire(80, teev - 6, 80, teev - 11)
bl, br = s.series_h("C", "CBRV", "47p", 86, teev - 11)
s.wire(80, teev - 11, bl, teev - 11)
s.wire(br, teev - 11, 92, teev - 11)
s.wire(92, teev - 11, 92, teev - 6 + 3.81)
s.wire(85.08, teev - 6 + 3.81, 92, teev - 6 + 3.81)
s.junction(85.08, teev - 6 + 3.81)
# bass + bleed
sl, sr = s.series_h("R", "RSLV", "6.8k", 70, teev + 5)
s.wire(64, teev, 64, teev + 5)
s.junction(64, teev)
s.wire(64, teev + 5, sl, teev + 5)
s.wire(sr, teev + 5, 80, teev + 5)
s.sym("POT", "VRBV", "250k bass", 80, teev + 5 + 3.81)
s.gnd(80, teev + 5 + 11.43)
# vibrato volume
s.wire(85.08, teev - 6 + 3.81, 96, teev - 6 + 3.81)   # treble wiper -> vol top
s.wire(96, teev - 6 + 3.81, 96, teev)
s.sym("POT", "VRVV", "1M vol", 96, teev + 3.81)
s.gnd(96, teev + 11.43)
# vol wiper -> V2B second-stage grid
s.wire(101.08, teev + 3.81, 108, teev + 3.81)
s.wire(108, teev + 3.81, 108, YV)
t2b = s.triode("V2B", "12AX7", 118, YV)
s.wire(108, YV, t2b["g"][0], YV)
s.plate_load("RLV2", "100k", t2b["p"], "B+3")
s.wire(118, YV + 7.62, 118, YV + 9)
s.shunt_rc("RKV2", "820", "CKV2", "25u", 118, YV + 9)
# V2B plate -> CCV2 0.02u -> reverb send (to reverb driver grid, down to block C)
teeb = YV - 7.62 - 3.48
s.wire(118, teeb, 126, teeb)
s.junction(118, teeb)
cl, cr = s.series_h("C", "CCV2", ".02u", 130, teeb)
s.wire(126, teeb, cl, teeb)
s.wire(cr, teeb, 138, teeb)
s.glabel("RVSEND", 138, teeb, 0)

# ============================ REVERB + TREMOLO BLOCK (third row) ======
YR = 152
s.text("Reverb driver / recovery / mixer", 60, 138, 1.6)
# reverb send coupling CRS 500p into paralleled 12AT7 driver grid
s.glabel("RVSEND", 40, YR, 180)
rl, rr = s.series_h("C", "CRS", "500p", 50, YR)
s.wire(44, YR, rl, YR)
s.wire(rr, YR, 60, YR)
s.junction(60, YR)
s.sym("R", "RGRD", "1M", 60, YR + 3.81)       # grid leak
s.gnd(60, YR + 7.62)
# V4A + V4B paralleled reverb driver
t4a = s.triode("V4A", "12AT7", 72, YR)
t4b = s.triode("V4B", "12AT7", 72, YR + 22)
s.wire(60, YR, t4a["g"][0], YR)
s.wire(60, YR, 60, YR + 22)
s.wire(60, YR + 22, t4b["g"][0], YR + 22)
s.junction(60, YR)
# plates tied
s.wire(72, YR - 7.62, 72, YR - 10)
s.wire(72, YR + 22 - 7.62, 72, YR + 22 - 10)
s.wire(72, YR - 10, 82, YR - 10)
s.wire(72, YR + 12, 82, YR + 12)
s.wire(82, YR - 10, 82, YR + 12)
s.junction(82, YR - 10)
# shared cathode RKRD 2.2k || CKRD 25u — tied below V4B, clear of both tubes
cy = YR + 33                                   # common cathode node, below V4B
s.wire(72, YR + 7.62, 64, YR + 7.62)           # V4A K left, then down the gap (x=64)
s.wire(64, YR + 7.62, 64, cy)
s.wire(64, cy, 72, cy)
s.wire(72, YR + 22 + 7.62, 72, cy)             # V4B K straight down to node
s.junction(72, cy)
s.shunt_rc("RKRD", "2.2k", "CKRD", "25u", 72, cy)
# reverb transformer T4 (driver -> tank)
s.sym("OT_SE", "T4", "125A20B", 96, YR - 4)
s.wire(82, YR - 10, 87.11, YR - 10)
s.wire(87.11, YR - 10, 87.11, YR - 6.54)      # plates -> PRI_P
s.wire(87.11, YR - 1.46, 87.11, YR + 2)
s.glabel("B+1", 87.11, YR + 2, 90)            # PRI_B -> B+1
s.wire(104.89, YR - 6.54, 110, YR - 6.54)
s.glabel("REVERB TANK", 110, YR - 6.54, 0)
s.wire(104.89, YR - 1.46, 110, YR - 1.46)
s.gnd(110, YR - 1.46)

# reverb recovery V3B: tank -> RGR1 220k -> grid; RLR1 100k -> B+3; RKR1 820 || CKR1
s.glabel("TANK RET", 118, YR - 6, 180)
gl2, gr2 = s.series_h("R", "RGR1", "220k", 128, YR - 6)
s.wire(122, YR - 6, gl2, YR - 6)
s.wire(gr2, YR - 6, 138, YR - 6)
s.wire(138, YR - 6, 138, YR)
t3b = s.triode("V3B", "12AX7", 148, YR)
s.wire(138, YR, t3b["g"][0], YR)
s.plate_load("RLR1", "100k", t3b["p"], "B+3")
s.wire(148, YR + 7.62, 148, YR + 9)
s.shunt_rc("RKR1", "820", "CKR1", "25u", 148, YR + 9)
# recovery plate -> CCR1 0.003u -> reverb level pot VRREV 100k -> RMR 470k mixer
teer = YR - 7.62 - 3.48
s.wire(148, teer, 156, teer)
s.junction(148, teer)
cl, cr = s.series_h("C", "CCR1", ".003u", 160, teer)
s.wire(156, teer, cl, teer)
s.wire(cr, teer, 168, teer)
s.wire(168, teer, 168, teer + 3.81 - 3.81)
s.sym("POT", "VRREV", "100k rev", 168, teer + 3.81)
s.gnd(168, teer + 11.43)
s.wire(173.08, teer + 3.81, 178, teer + 3.81)  # reverb wiper -> mix
ml2, mr2 = s.series_h("R", "RMR", "470k", 182, teer + 3.81)
s.wire(178, teer + 3.81, ml2, teer + 3.81)
s.wire(mr2, teer + 3.81, 190, teer + 3.81)
s.wire(190, teer + 3.81, 190, YR + 12)
s.glabel("MIXG", 190, YR + 12, 0)             # dry+reverb mix -> mix-driver grid

# mix driver V3A: grid = MIXG; RGD1 3.3M leak; RLD1 100k -> B+3; RKD1 820 || CKD1
YM = YR + 22
s.glabel("MIXG", 196, YM, 180)
s.wire(200, YM, 204, YM)
s.junction(204, YM)
s.sym("R", "RGD1", "3.3M", 204, YM + 3.81)    # grid leak / tremolo shunt node
s.gnd(204, YM + 7.62)
# bright cap CBD1 10p across grid to plate side (drawn as small cap to grid)
s.wire(204, YM, 204, YM - 6)
cbl, cbr = s.series_h("C", "CBD1", "10p", 210, YM - 6)
s.wire(204, YM - 6, cbl, YM - 6)
s.wire(cbr, YM - 6, 216, YM - 6)
s.wire(216, YM - 6, 216, YM - 7.62 - 3.48)
t3a = s.triode("V3A", "12AX7", 216, YM)
s.wire(204, YM, t3a["g"][0], YM)
s.junction(204, YM)
s.plate_load("RLD1", "100k", t3a["p"], "B+3")
s.wire(216, YM + 7.62, 216, YM + 9)
s.shunt_rc("RKD1", "820", "CKD1", "25u", 216, YM + 9)
# mix-driver plate -> CCD1 0.001u -> PI hot grid line (PIG)
teem = YM - 7.62 - 3.48
s.wire(216, teem, 222, teem)
s.junction(216, teem)
cl, cr = s.series_h("C", "CCD1", ".001u", 226, teem)
s.wire(222, teem, cl, teem)
s.wire(cr, teem, 232, teem)
s.wire(232, teem, 232, YM - 20)
s.glabel("PIG", 232, YM - 20, 0)

# ============================ TREMOLO OSCILLATOR (excluded) ==========
YT = 210
s.text("Tremolo oscillator (V5) + optocoupler — dynamic; DC point excluded from netlist (notes.md)",
       26, 198, 1.4)
# V5A = phase-shift oscillator; V5B = intensity driver into the optocoupler.
t5a = s.triode("V5A", "12AX7", 56, YT)
t5b = s.triode("V5B", "12AX7", 96, YT)
s.plate_load("RTO2", "220k", t5a["p"], "B+4")   # oscillator plate load
s.plate_load("RTO1", "100k", t5b["p"], "B+4")   # driver plate load
# cathodes to ground
s.sym("R", "RKTO1", "2.7k", 56, YT + 11.43)
s.gnd(56, YT + 15.24)
s.sym("R", "RKTO2", "100k", 96, YT + 11.43)
s.gnd(96, YT + 15.24)
# V5A plate tee feeds (a) CTO3 -> V5B grid and (b) the phase-shift feedback net
tee5 = YT - 7.62 - 3.48                          # = 198.9
s.junction(56, tee5)
cl, cr = s.series_h("C", "CTO3", ".02u", 68, tee5)   # 64.19..71.81
s.wire(56, tee5, cl, tee5)
s.wire(cr, tee5, 88.38, tee5)
s.wire(88.38, tee5, 88.38, YT)                   # -> V5B grid
# V5B grid leak RTO10 10M
s.wire(88.38, YT, 82, YT)
s.junction(82, YT)
s.sym("R", "RTO10", "10M", 82, YT + 3.81)
s.gnd(82, YT + 7.62)
# phase-shift feedback: plate -> CTO1 - RTOG2 - CTO2 - RTOG3 -> V5A grid
s.wire(56, tee5, 48, tee5)
s.wire(48, tee5, 48, 230)
cl, cr = s.series_h("C", "CTO1", ".01u", 42, 230)     # 38.19..45.81
s.wire(48, 230, cr, 230)
s.wire(cl, 230, 36, 230)
s.junction(36, 230)
s.sym("R", "RTOG2", "1M", 36, 233.81)
s.gnd(36, 237.62)
cl, cr = s.series_h("C", "CTO2", ".01u", 30, 230)     # 26.19..33.81
s.wire(36, 230, cr, 230)
s.wire(cl, 230, 24, 230)
s.junction(24, 230)
s.sym("R", "RTOG3", "1M", 24, 233.81)
s.gnd(24, 237.62)
s.wire(24, 230, 24, YT)
s.wire(24, YT, 48.38, YT)                         # -> V5A grid
# V5A grid leak RTOG 2.2M
s.junction(44, YT)
s.sym("R", "RTOG", "2.2M", 44, YT + 3.81)
s.gnd(44, YT + 7.62)
# speed pot VRSPD 3M — tunes the feedback net (across the CTO2 / RTOG3 node)
s.sym("POT", "VRSPD", "3M speed", 16, 226)
s.gnd(16, 233.62)
s.wire(21.08, 226, 24, 226)
s.wire(24, 226, 24, 230)
s.junction(24, 230)
# intensity: V5B plate -> VRINT 50k -> RINT 10k -> opto lamp
s.junction(96, tee5)
s.wire(96, tee5, 108, tee5)
s.wire(108, tee5, 108, 202.19)
s.sym("POT", "VRINT", "50k int", 108, 206)
s.gnd(108, 213.62)
il, ir = s.series_h("R", "RINT", "10k", 120, 206)
s.wire(113.08, 206, il, 206)
s.wire(ir, 206, 130, 206)
# optocoupler: lamp driven by intensity; photocell shunts the mix-driver grid
op = s.opto("OPTO", "roach", 142, 206)
s.wire(130, 206, 130, op["l1"][1])
s.wire(130, op["l1"][1], op["l1"][0], op["l1"][1])
s.wire(op["l2"][0], op["l2"][1], op["l2"][0] - 4, op["l2"][1])
s.gnd(op["l2"][0] - 4, op["l2"][1])
s.wire(op["p1"][0], op["p1"][1], op["p1"][0] + 4, op["p1"][1])
s.glabel("MIXG", op["p1"][0] + 4, op["p1"][1], 0)   # photocell -> mix-driver grid node
s.wire(op["p2"][0], op["p2"][1], op["p2"][0] + 4, op["p2"][1])
s.gnd(op["p2"][0] + 4, op["p2"][1])

# ============================ PHASE INVERTER (LTP) ===================
XPI = 258
YPH = 100  # hot
YPB = 132  # cold
s.text("Long-tailed-pair phase inverter", 244, 86, 1.6)
# hot grid input from PIG (mixer output)
s.glabel("PIG", 232, YPH, 180)
cl, cr = s.series_h("C", "CPIA", ".001u", 240, YPH)
s.wire(236, YPH, cl, YPH)
s.wire(cr, YPH, XPI - 7.62, YPH)
t6a = s.triode("V6A", "12AT7", XPI, YPH)
t6b = s.triode("V6B", "12AT7", XPI, YPB)
s.plate_load("RLPA", "82k 5%", t6a["p"], "B+3")
s.plate_load("RLPB", "100k 5%", t6b["p"], "B+3")
# shared tail — cathodes join at a left stub, RTAIL to the tail junction (y=116),
# RT2 to ground; both grid leaks return to that junction (all clear of the tubes).
JY = 116
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, 250, YPH + 10)
s.wire(XPI, YPB - 7.62, XPI, YPB - 10)
s.wire(XPI, YPB - 10, 250, YPB - 10)
s.wire(250, YPH + 10, 250, YPB - 10)           # cathode common (x=250)
s.junction(250, JY)
tl, tr = s.series_h("R", "RTAIL", "470", 244.5, JY)   # 240.69..248.31
s.wire(250, JY, tr, JY)
s.wire(239, JY, tl, JY)
s.wire(228, JY, 239, JY)                        # tail-junction rail (y=116)
s.junction(232, JY)
s.junction(236, JY)
# RT2 22k tail -> ground (x=232)
s.sym("R", "RT2", "22k", 232, JY + 3.81)
s.gnd(232, JY + 7.62)
# hot grid leak RGPA (x=236) up to the hot grid via a y=98 detour clear of CPIA
s.sym("R", "RGPA", "1M", 236, JY - 8, lx=-9.4)  # pins 104.19 / 111.81
s.wire(236, 111.81, 236, JY)
s.wire(236, 104.19, 236, YPH - 2)
s.wire(236, YPH - 2, 250.38, YPH - 2)
s.wire(250.38, YPH - 2, 250.38, YPH)
s.junction(250.38, YPH)
# cold grid leak RGPB (x=228) down to the cold grid via a y=134 detour
s.sym("R", "RGPB", "1M", 228, JY + 8, lx=-9.4)  # pins 120.19 / 127.81
s.wire(228, 120.19, 228, JY)
s.wire(228, 127.81, 228, YPB + 2)
s.wire(228, YPB + 2, 250.38, YPB + 2)
s.wire(250.38, YPB + 2, 250.38, YPB)
s.junction(250.38, YPB)
# CPIB 0.1u/200 cold grid -> NFB node (AC ground)
cbl, cbr = s.series_h("C", "CPIB", ".1u", 238, YPB)   # 234.19..241.81
s.wire(250.38, YPB, cbr, YPB)
s.junction(250.38, YPB)
s.wire(cbl, YPB, 224, YPB)
# NFB from speaker: SPKR -> RNFB 820 -> cold grid node; RNF2 47 to gnd
s.glabel("SPKR", XPI - 60, YPB + 12, 180)
nl, nr = s.series_h("R", "RNFB", "820", XPI - 50, YPB + 12)
s.wire(XPI - 56, YPB + 12, nl, YPB + 12)
s.wire(nr, YPB + 12, XPI - 34, YPB + 12)
s.wire(XPI - 34, YPB + 12, XPI - 34, YPB)
s.junction(XPI - 34, YPB)
s.sym("R", "RNF2", "47", XPI - 34, YPB + 3.81 + 6, lx=-8.0)
s.gnd(XPI - 34, YPB + 7.62 + 6)
s.wire(XPI - 34, YPB, XPI - 34, YPB + 6)

# ============================ OUTPUT couplers + 6V6 ==================
# PI plates -> C1/C2 0.1u -> 6V6 grids
teea = YPH - 7.62 - 3.48
s.wire(XPI, teea, XPI + 10, teea)
s.junction(XPI, teea)
al, ar = s.series_h("C", "C1", ".1u", XPI + 16, teea)
s.wire(XPI + 10, teea, al, teea)
s.wire(ar, teea, XPI + 26, teea)
s.wire(XPI + 26, teea, XPI + 26, 92)
teec = YPB - 7.62 - 3.48
s.wire(XPI, teec, XPI + 10, teec)
s.junction(XPI, teec)
kl, kr = s.series_h("C", "C2", ".1u", XPI + 16, teec)
s.wire(XPI + 10, teec, kl, teec)
s.wire(kr, teec, XPI + 26, teec)
s.wire(XPI + 26, teec, XPI + 26, 140)

XO = 320
for y, vref, glref, sref, gnode in [(92, "V7", "RGL1", "RS1", XPI + 26),
                                     (140, "V8", "RGL2", "RS2", XPI + 26)]:
    s.wire(gnode, y, XO - 7.62, y)
    p = s.pentode(vref, "6V6GT", XO, y)
    s.junction(gnode, y)
    s.sym("R", glref, "220k", gnode, y + 3.81)
    s.wire(gnode, y + 7.62, gnode, y + 10.16)
    s.glabel("-35V", gnode, y + 10.16, 270)
    # screen -> RS 470 1W -> B+2
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2, p["g2"][1])
    sl2, sr2 = s.series_h("R", sref, "470 1W", p["g2"][0] + 5.81, p["g2"][1])
    s.wire(sr2, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
    s.glabel("B+2", p["g2"][0] + 11.5, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# output transformer T3
s.sym("OT_PP", "T3", "125A1A", 352, 116)
s.wire(XO, 84.38, XO, 80)
s.wire(XO, 80, 343.11, 80)
s.wire(343.11, 80, 343.11, 110.92)     # V7 plate -> PRI_A
s.wire(XO, 132.38, XO, 128)
s.wire(XO, 128, 338, 128)
s.wire(338, 128, 338, 121.08)
s.wire(338, 121.08, 343.11, 121.08)    # V8 plate -> PRI_B
s.wire(343.11, 116, 340.57, 116)
s.wire(340.57, 116, 340.57, 113)
s.glabel("B+1", 340.57, 113, 90)       # centre tap
s.wire(360.89, 113.46, 363.43, 113.46)
s.glabel("SPKR", 363.43, 113.46, 0)
s.wire(360.89, 118.54, 363.43, 118.54)
s.glabel("GND", 363.43, 118.54, 0)

# ============================ POWER SUPPLY (bottom) ==================
YPW = 250
s.text("Power supply — PT 125P33A 330-0-330, GZ34 full-wave, choke 125C3A · standby/mains AC switch omitted",
       26, 236, 1.4)
pt = s.pt("T1", "125P33A", 40, YPW)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 4, pt["pri2"][1], 180)
# HT -> GZ34 plates
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
# GZ34 rectifier
s.glabel("HT_A", 74, YPW - 12, 90)
s.wire(74, YPW - 12, 74, YPW - 9.5)
va = s.diode_tube("V9A", "GZ34", 74, YPW - 1.88, lx=-11.4)
s.glabel("HT_B", 86, YPW - 12, 90)
s.wire(86, YPW - 12, 86, YPW - 9.5)
vb = s.diode_tube("V9B", "GZ34", 86, YPW - 1.88, lx=6.0)
s.wire(74, YPW + 5.74, 74, YPW + 8)
s.wire(86, YPW + 5.74, 86, YPW + 8)
s.wire(74, YPW + 8, 100, YPW + 8)
s.junction(86, YPW + 8)
# reservoir C10 -> B+1
s.junction(90, YPW + 8)
s.sym("C", "C10", "16u", 90, YPW + 11.81)
s.gnd(90, YPW + 11.81 + 3.81)
s.glabel("B+1", 100, YPW + 8, 0)
s.wire(100, YPW + 8, 103, YPW + 8)
# choke T2 -> B+2 node (screens) with C11
s.sym("CHOKE", "T2", "125C3A", 110.62, YPW + 8, lx=-4.0, ly=-6.4)
s.wire(118.24, YPW + 8, 128, YPW + 8)
s.junction(122, YPW + 8)
s.glabel("B+2", 122, YPW + 5.46, 90)
s.wire(122, YPW + 5.46, 122, YPW + 8)
s.junction(126, YPW + 8)
s.sym("C", "C11", "16u", 126, YPW + 11.81)
s.gnd(126, YPW + 11.81 + 3.81)
# RD1 10k -> B+3 node C12
l, r = s.series_h("R", "RD1", "10k", 132, YPW + 8)
s.wire(128, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 146, YPW + 8)
s.junction(140, YPW + 8)
s.glabel("B+3", 140, YPW + 5.46, 90)
s.wire(140, YPW + 5.46, 140, YPW + 8)
s.junction(144, YPW + 8)
s.sym("C", "C12", "16u", 144, YPW + 11.81)
s.gnd(144, YPW + 11.81 + 3.81)
# RD2 10k -> B+4 node C13
l, r = s.series_h("R", "RD2", "10k", 150, YPW + 8)
s.wire(146, YPW + 8, l, YPW + 8)
s.wire(r, YPW + 8, 164, YPW + 8)
s.junction(158, YPW + 8)
s.glabel("B+4", 158, YPW + 5.46, 90)
s.wire(158, YPW + 5.46, 158, YPW + 8)
s.sym("C", "C13", "16u", 164, YPW + 11.81)
s.gnd(164, YPW + 11.81 + 3.81)

# ============================ BIAS SUPPLY ===========================
YB = YPW - 6
s.text("Bias supply — off an HT tap → -35 V (25u/50u, 10k hum-balance)", 190, 236, 1.3)
s.glabel("HT_B", 190, YB, 180)
s.wire(190, YB, 193.91, YB)
s.sym("DIODE_SS", "DBIAS", "Si", 199, YB, lx=-2.0, ly=-5.4)
s.wire(204, YB, 208, YB)
l, r = s.series_h("R", "RBIAS", "470 1W", 212, YB)
s.wire(208, YB, l, YB)
s.wire(r, YB, 224, YB)
s.junction(218, YB)
s.sym("C", "CB1", "25u", 218, YB + 3.81)
s.gnd(218, YB + 7.62)
s.junction(224, YB)
s.sym("C", "CB2", "50u", 224, YB + 3.81)
s.gnd(224, YB + 7.62)
# hum-balance divider VRBAL 10k + RBAL 10k -> -35V
s.wire(224, YB, 230, YB)
s.sym("POT", "VRBAL", "10k bal", 234, YB, rot=90, lx=-3.2, ly=-6.0)
s.wire(230, YB, 230.19, YB)
l, r = s.series_h("R", "RBAL", "10k", 244, YB)
s.wire(238, YB, l, YB)
s.wire(r, YB, 254, YB)
s.glabel("-35V", 254, YB, 0)

# ============================ DEATH CAP =============================
s.text("Period ground-switch cap (not in modern builds)", 190, 258, 1.1)
s.glabel("MAINS", 190, YB + 16, 180)
s.wire(190, YB + 16, 194, YB + 16)
s.sym("C", "CDEATH", ".047u", 198, YB + 16, rot=90, lx=-3.2, ly=-6.2)
s.wire(201.81, YB + 16, 206, YB + 16)
s.gnd(206, YB + 16)

s.write(OUT, [], paper="A3")
print(f"wrote {OUT}")
