#!/usr/bin/env python3
"""Generate amps/ac30/schematic.kicad_sch from the stage-template library.

Values per JMI drawing OS/065, "VOX A.C.30.36 AMPLIFIER CIRCUIT / NORMAL"
(title-block date 29-4-60, main body as amended to Issue 4 of 11-9-64) — see
amps/ac30/meta.yaml for the sources. Redrawn from circuit facts; never a trace
of a factory drawing.

The sheet reads left to right. The Brilliant channel runs along the top and the
Normal channel below it, two jacks each, into ONE ECC83 (V1) whose two halves
share a single 1.5 kOhm cathode resistor — the valve the May-1961 list of
changes put where the 1960 sheet had an EF86. The channels differ in one part:
the Normal side couples out through 0.047 uF, the Brilliant side through 500 pF.
Both volumes mix through 220 kOhm resistors into ONE grid of the ECC83
long-tailed pair (V2); the Vibrato/Tremolo volume drives the other, so that
channel enters in the opposite phase. The Cut control bridges the pair's two
anodes — the amp's only tone control, and it sits AFTER the inverter. Four
cathode-biased EL84s on ONE shared 50 Ohm resistor and the 4 kOhm output
transformer fill the right-hand side; the GZ34 supply runs along the bottom.

There is no tone stack, no bias supply and no negative-feedback loop: all three
absences are visible on the sheet. (The blue negative-feedback loop inked across
the published copy is a later hand addition by a previous owner, is not part of
the circuit JMI built, and is not drawn here.)

SCOPE. Every part the corpus asserts a connection for carries a designator and
is drawn. The Vibrato/Tremolo channel's input, voicing, phase-shift, modulator
and oscillator networks are NOT asserted: the published OS/065 scan resolves
their shapes but not reliably their values and interconnection, so they carry no
designator in bom.yaml and appear here as the named interfaces each valve runs
into — the same treatment the AC15 entry gives its own Vibravox channel. The
parts that DO carry designators there (the R40/C19 supply dropper, the
R41/C41/R42 modulator network and the R43/R44 modulator anode loads) are drawn
against those named interfaces and nothing further. Heaters and the 6.3 V
winding are an annotation layer (see amps/ac30/layout.yaml). OS/065 draws no
pilot lamp and bom.yaml carries no designator for one, so none is drawn.

Rails: B+1 = +320 V (after the choke), B+N = +290 V front-end anode supply,
B+P = phase inverter, B+V = Vibrato/Tremolo — the last two each behind their own
22 kOhm dropper, exactly as the drawing shows. B+V's own supply side is a named
interface: the scan does not resolve which rail that dropper chain returns to.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ac30" / "schematic.kicad_sch"
s = Sch()


def input_pair(jrefs, srefs, ys, gbx, gy, leakref, leak_x, leak_y):
    """Two input jacks, each through its own 68 kOhm stopper onto a shared grid
    bus; the bus carries a 1 MOhm leak, drawn at (leak_x, leak_y)."""
    for jref, sref, y in zip(jrefs, srefs, ys):
        j = s.jack(jref, "1/4 in", 20, y + 2.54, mirror=True)
        l, r = s.series_h("R", sref, "68k", 42, y)
        s.wire(j["tip"][0], y, l, y)
        s.wire(r, y, gbx, y)
        s.wire(j["sleeve"][0], y + 5.08, 30, y + 5.08)
        s.wire(30, y + 5.08, 30, y + 8.08)
        s.gnd(30, y + 8.08)
    s.wire(gbx, ys[0], gbx, ys[-1])
    s.junction(gbx, gy)
    s.junction(gbx, ys[-1])
    s.wire(gbx, ys[-1], gbx, leak_y)
    if leak_x != gbx:
        s.wire(gbx, leak_y, leak_x, leak_y)
    s.sym("R", leakref, "1M", leak_x, leak_y + 3.81, lx=-9.4)
    s.gnd(leak_x, leak_y + 7.62)


def plate_load_side(ref, val, plate, rail, out, up=3.48, rise=3.28):
    """Plate load up to a rail label drawn to the side, so a rail tag never
    lands in the title band or on a neighbouring part. Returns the plate-node y
    (the tee couplers hang off)."""
    x, py = plate
    tee = py - up
    s.wire(x, py, x, tee)
    s.sym("R", ref, val, x, tee - 3.81)
    s.wire(x, tee - 7.62, x, tee - 7.62 - rise)
    s.wire(x, tee - 7.62 - rise, x + out, tee - 7.62 - rise)
    s.glabel(rail, x + out, tee - 7.62 - rise, 180 if out < 0 else 0)
    return tee


# ================================ TITLE ====================================
s.note('No tone stack · no bias supply · no negative feedback. Brilliant and Normal share ONE bottle and ONE cathode resistor, and mix into ONE inverter grid.')
s.note('Rails: B+1 +320 V · B+N +290 V front end · B+P inverter · B+V vibrato. Heaters and the 6.3 V winding are an annotation layer.')

# ===================== BRILLIANT + NORMAL CHANNELS — V1 ====================
s.text('Brilliant channel', 16, 32, 1.6)
input_pair(["J1", "J2"], ["R1", "R2"], [42, 54], 58, 48, "R3", 50, 58)
v1a = s.triode("V1A", "ECC83", 76, 48)
s.wire(58, 48, v1a["g"][0], 48)
TEE_BR = plate_load_side("R5", "220k", v1a["p"], "B+N", -10.0)   # 36.9

s.text('Normal channel', 16, 71, 1.6)
input_pair(["J3", "J4"], ["R12", "R13"], [78, 90], 58, 84, "R14", 58, 94)
v1b = s.triode("V1B", "ECC83", 76, 84)
s.wire(58, 84, v1b["g"][0], 84)
TEE_NO = plate_load_side("R6", "220k", v1b["p"], "B+N", -10.0)   # 72.9

# ONE shared cathode network for both halves — R4 with C1 across it. Neither
# channel can be biased, or solved, without the other.
s.wire(76, v1a["k"][1], 88, v1a["k"][1])
s.wire(76, v1b["k"][1], 88, v1b["k"][1])
s.wire(88, v1a["k"][1], 88, 104)
s.junction(88, v1b["k"][1])
s.wire(88, 104, 96, 104)
s.shunt_rc("R4", "1.5k", "C1", "25u", 96, 104)
s.text("V1 pins 3 and 8 are tied: ONE 1.5 k / 25 uF network biases both "
       "channels' first stages", 66, 122, 1.15)

# Brilliant: 500 pF out — that capacitor is the whole of the channel's voicing
s.wire(76, TEE_BR, 122.19, TEE_BR)
s.junction(76, TEE_BR)
cl, cr = s.series_h("C", "C3", "500p", 126, TEE_BR)
s.wire(cr, TEE_BR, 140, TEE_BR)
s.sym("POT", "VR2", "500k log", 140, TEE_BR + 3.81, lx=2.6)
s.wire(140, TEE_BR + 7.62, 140, 48)
s.gnd(140, 48)
s.wire(145.08, TEE_BR + 3.81, 152, TEE_BR + 3.81)
s.text("Brilliant: the 500 pF coupler is the whole voicing — no extra stage, "
       "no tone stack", 104, 58, 1.15)

# Normal: 0.047 uF out
s.wire(76, TEE_NO, 122.19, TEE_NO)
s.junction(76, TEE_NO)
cl, cr = s.series_h("C", "C2", ".047u", 126, TEE_NO)
s.wire(cr, TEE_NO, 140, TEE_NO)
s.sym("POT", "VR1", "500k log", 140, TEE_NO + 3.81, lx=2.6)
s.wire(140, TEE_NO + 7.62, 140, 84)
s.gnd(140, 84)
s.wire(145.08, TEE_NO + 3.81, 152, TEE_NO + 3.81)

# both wipers mix through 220 k into ONE inverter grid
MIX = 172.0
for ref, wy in [("R9", TEE_BR + 3.81), ("R7", TEE_NO + 3.81)]:
    l, r = s.series_h("R", ref, "220k", 160, wy)
    s.wire(152, wy, l, wy)
    s.wire(r, wy, MIX, wy)
s.wire(MIX, TEE_BR + 3.81, MIX, TEE_NO + 3.81)
s.junction(MIX, 60)
s.wire(MIX, 60, 178.19, 60)
cl, cr = s.series_h("C", "C5", ".047u", 182, 60)
s.text("Both channels sum here, ahead of ONE inverter grid", 150, 96, 1.15)

# ================= PHASE INVERTER — ECC83 long-tailed pair =================
s.text("Phase inverter — long-tailed pair; Brilliant + Normal enter one grid, "
       "Vibrato/Tremolo the other", 189, 30, 1.6)
GC = 189.0                                       # shared grid / grid-leak column
v2a = s.triode("V2A", "ECC83", 200, 60)
v2b = s.triode("V2B", "ECC83", 200, 120)
s.wire(185.81, 60, GC, 60)
s.junction(GC, 60)
s.wire(GC, 60, v2a["g"][0], 60)
s.glabel("VIB VOL", 170, 120, 180)
s.wire(170, 120, 178.19, 120)
cl, cr = s.series_h("C", "C7", ".047u", 182, 120)
s.wire(cr, 120, GC, 120)
s.junction(GC, 120)
s.wire(GC, 120, v2b["g"][0], 120)
s.plate_load("R18", "100k", v2a["p"], "B+P")
s.plate_load("R19", "100k", v2b["p"], "B+P")
TEE_A = v2a["p"][1] - 3.48                       # 48.9
TEE_B = v2b["p"][1] - 3.48                       # 108.9

# both 1 M grid leaks return to the tail junction, in the column between them
s.wire(GC, 60, GC, 68)
s.sym("R", "R8", "1M", GC, 71.81, lx=-9.4)
s.wire(GC, 75.62, GC, 101.19)
s.sym("R", "R17", "1M", GC, 105, lx=-9.4)
s.wire(GC, 108.81, GC, 120)
s.junction(GC, 79.62)
s.wire(GC, 79.62, 216, 79.62)
# shared 1.2 k cathode over a 47 k tail
s.wire(200, v2a["k"][1], 200, 72)
s.wire(200, 72, 216, 72)
s.wire(200, v2b["k"][1], 200, 132)
s.wire(200, 132, 208, 132)
s.wire(208, 72, 208, 132)
s.junction(208, 72)
s.sym("R", "R16", "1.2k", 216, 75.81)
s.junction(216, 79.62)
s.sym("R", "R15", "47k", 216, 83.43)
s.gnd(216, 87.24)

# ---- Cut: 250 k log in series with 0.0047 uF, across the two anodes --------
s.wire(200, TEE_A, 236.19, TEE_A)
s.junction(200, TEE_A)
s.junction(224, TEE_A)
s.wire(200, TEE_B, 236.19, TEE_B)
s.junction(200, TEE_B)
s.junction(224, TEE_B)
s.wire(224, TEE_A, 224, 56)
s.sym("C", "C10", ".0047u", 224, 59.81, lx=2.6)
s.wire(224, 63.62, 224, 90)
s.sym("POT", "VR3", "250k cut", 224, 93.81, lx=2.6)
s.wire(224, 97.62, 224, TEE_B)
s.wire(229.08, 93.81, 229.08, 102)
s.wire(229.08, 102, 224, 102)
s.junction(224, 102)
s.text("Cut — the amp's only tone control, and it sits AFTER the inverter, so "
       "all three", 189, 140, 1.15)
s.text("channels darken together, downstream of everything that distorts",
       189, 144, 1.15)

# ============ OUTPUT — four EL84s, parallel push-pull, cathode bias ========
s.text("Output — four EL84s, two per phase, on ONE shared 50 Ohm cathode "
       "resistor. No bias supply, no adjustment, no feedback loop.",
       236, 24, 1.6)
CATH = 322.0
TUBE_X = 282.0
for tee, cref, gcol, stx, glref, glval, pairs in [
        (TEE_A, "C6", 252.0, 262.0, "R20", "220k",
         [(46, "V3", "R22", "R25"), (82, "V5", "R27", "R29")]),
        (TEE_B, "C9", 256.0, 266.0, "R21", "280k",
         [(118, "V4", "R23", "R26"), (154, "V6", "R28", "R30")])]:
    gys = [g for g, _, _, _ in pairs]
    top, bot = min(gys + [tee]), max(gys + [tee])
    cl, cr = s.series_h("C", cref, ".15u", 240, tee)
    s.wire(cr, tee, gcol, tee)
    s.wire(gcol, top, gcol, bot + 5.62)
    for gy in gys + [tee]:
        if top < gy < bot:
            s.junction(gcol, gy)
    s.junction(gcol, bot)
    s.sym("R", glref, glval, gcol, bot + 9.43, lx=-9.6)
    s.gnd(gcol, bot + 13.24)
    for gy, vref, stref, scref in pairs:
        sl, sr = s.series_h("R", stref, "1.5k", stx, gy)
        s.wire(gcol, gy, sl, gy)
        p = s.pentode(vref, "EL84", TUBE_X, gy, lx=-15.0, ly=5.0)
        s.wire(sr, gy, p["g1"][0], gy)
        # 100 Ohm screen stopper, off the SAME rail as the anodes
        c1, c2 = s.series_h("R", scref, "100", 298, p["g2"][1])
        s.wire(p["g2"][0], p["g2"][1], c1, p["g2"][1])
        s.wire(c2, p["g2"][1], 306, p["g2"][1])
        s.glabel("B+1", 306, p["g2"][1], 0)
        # cathode -> the one shared bias resistor
        s.wire(TUBE_X, p["k"][1], CATH, p["k"][1])

# ONE 50 Ohm resistor and a 250 uF can: the entire bias arrangement for four
# valves. The drawing annotates it "QUIESCENT 10v / 12.5v AT 30 WATTS".
s.wire(CATH, 52.985, CATH, 170)
for ky in (88.985, 124.985, 160.985):
    s.junction(CATH, ky)
s.shunt_rc("R24", "50", "C11", "250u", CATH, 170)
s.text("Quiescent 10 V across 50 Ohm = 200 mA for the quad, 50 mA a valve",
       240, 196, 1.15)

# ---- output transformer + speaker jack ------------------------------------
s.sym("OT_PP", "T1", "4k a-a", 352, 105)
s.wire(TUBE_X, 37.745, TUBE_X, 32)
s.wire(TUBE_X, 32, 330, 32)
s.wire(TUBE_X, 73.745, TUBE_X, 68)
s.wire(TUBE_X, 68, 330, 68)
s.junction(330, 68)
s.wire(330, 32, 330, 99.92)
s.wire(330, 99.92, 343.11, 99.92)
s.wire(TUBE_X, 109.745, TUBE_X, 104)
s.wire(TUBE_X, 104, 336, 104)
s.wire(TUBE_X, 145.745, TUBE_X, 140)
s.wire(TUBE_X, 140, 336, 140)
s.wire(336, 104, 336, 140)          # V4 and V6 anodes share the B-phase riser
s.junction(336, 110.08)
s.wire(336, 110.08, 343.11, 110.08)
s.wire(343.11, 105, 340, 105)
s.wire(340, 105, 340, 88)
s.glabel("B+1", 340, 88, 90)
s.wire(360.89, 102.46, 374.92, 102.46)
s.wire(360.89, 107.54, 374.92, 107.54)
s.jack("JSPK1", "1/4 in", 380, 105, lx=3.0, ly=6.6)
s.junction(368, 107.54)
s.wire(368, 107.54, 368, 116)
s.gnd(368, 116)
s.text("4 kOhm anode to anode; 8 and 15 Ohm secondary taps", 340, 148, 1.15)

# ================== VIBRATO / TREMOLO CHANNEL (not asserted) ===============
s.text('Vibrato/Tremolo channel — ‘Vibravox’', 16, 132, 1.6)
for jref, jy in [("J5", 144), ("J6", 158)]:
    j = s.jack(jref, "1/4 in", 20, jy + 2.54, mirror=True)
    s.wire(j["tip"][0], jy, 44, jy)
    s.glabel("VIB-IN NET", 44, jy, 0)
    s.wire(j["sleeve"][0], jy + 5.08, 30, jy + 5.08)
    s.wire(30, jy + 5.08, 30, jy + 8.08)
    s.gnd(30, jy + 8.08)

v7 = s.triode("V7", "ECC83", 84, 151)
s.glabel("VIB-IN NET", 64, 151, 180)
s.wire(64, 151, v7["g"][0], 151)
s.wire(84, 143.38, 84, 138)
s.glabel("VIB-NET a", 84, 138, 90)
s.wire(84, 158.62, 84, 164)
s.glabel("VIB-NET k", 84, 164, 270)

v9 = s.triode("V9", "ECC83", 136, 151)
s.glabel("OSC-NET g", 118, 151, 180)
s.wire(118, 151, v9["g"][0], 151)
s.wire(136, 143.38, 136, 138)
s.glabel("OSC-NET a", 136, 138, 90)
s.wire(136, 158.62, 136, 164)
s.glabel("OSC-NET k", 136, 164, 270)

# the panel Vibrato/Tremolo switch: it sits inside the oscillator network, so it
# is drawn between two named interfaces and nothing further is asserted.
s.glabel("OSC-NET s1", 164, 151, 180)
s.wire(164, 151, 174.92, 151)
sl2, sr2 = s.switch("SW3", "SPST", 180, 151, lx=-3.4, ly=6.4)
s.wire(sr2, 151, 192, 151)
s.glabel("OSC-NET s2", 192, 151, 0)

# supply dropper: the parts list letters R40 and C19; the rail the chain
# returns to is NOT resolved by the published scan, so it is a named interface.
s.glabel("V-SUPPLY", 20, 178, 180)
s.wire(20, 178, 32.19, 178)
l, r = s.series_h("R", "R40", "15k", 36, 178)
s.wire(r, 178, 60, 178)
s.junction(50, 178)
s.sym("C", "C19", "32u", 50, 181.81, lx=2.6)
s.gnd(50, 185.62)
s.glabel("B+V", 60, 178, 0)
s.text("R40's supply side is a named interface: the published scan does not "
       "resolve", 8, 192, 1.15)
s.text("which rail the Vibrato/Tremolo dropper chain returns to.", 8, 196, 1.15)

# Vibrato/Tremolo volume -> the inverter's OTHER grid (opposite phase)
s.glabel("LADDER OUT", 16, 205, 180)
s.wire(16, 205, 24, 205)
s.sym("POT", "VR4", "500k log", 24, 208.81, lx=2.6)
s.wire(24, 212.62, 24, 216)
s.gnd(24, 216)
s.wire(29.08, 208.81, 40, 208.81)
s.glabel("VIB VOL", 40, 208.81, 0)

# the ECC82 modulator: both anode loads ARE lettered on the sheet, so both are
# drawn; the network their grids and cathodes work into is named, not asserted.
for x, vref, lref, gl, kl in [(100, "V8A", "R43", "MOD-NET g1", "MOD-NET k1"),
                              (160, "V8B", "R44", "MOD-NET g2", "MOD-NET k2")]:
    v8 = s.triode(vref, "ECC82", x, 232)
    s.wire(x, 224.38, x, 220.9)
    s.sym("R", lref, "10k", x, 217.09)
    s.wire(x, 213.28, x, 210.74)
    s.glabel("B+V", x, 210.74, 90)
    s.wire(v8["g"][0], 232, x - 22, 232)
    s.glabel(gl, x - 22, 232, 180)
    s.wire(x, 239.62, x, 244)
    s.glabel(kl, x, 244, 270)

# the modulator network OS/065 letters: 47 k with the February-1961 capacitor
# across it, then 22 k, into the named network it works with.
s.glabel("B+V", 16, 262, 180)
s.wire(16, 262, 22, 262)
l, r = s.series_h("R", "R41", "47k", 32, 262)
s.wire(22, 262, l, 262)
s.junction(22, 262)
s.wire(22, 262, 22, 270)
cl2, cr2 = s.series_h("C", "C41", ".005u", 32, 270)
s.wire(22, 270, cl2, 270)
s.wire(cr2, 270, 44, 270)
s.wire(44, 270, 44, 262)
s.wire(r, 262, 56, 262)
s.junction(44, 262)
l, r = s.series_h("R", "R42", "22k", 66, 262)
s.wire(56, 262, l, 262)
s.wire(r, 262, 80, 262)
s.glabel("MOD-NET", 80, 262, 0)

s.text("R41 / C41 / R42 are the modulator-network parts OS/065 letters. The "
       "rest of that network, the", 8, 278, 1.15)
s.text("voicing switch, the five-section phase-shift ladder and the "
       "oscillator's own RC sections are", 8, 282, 1.15)
s.text("drawn on the sheet but are not resolved as values and interconnection, "
       "so this drawing names", 8, 286, 1.15)
s.text("the interfaces each valve works into and asserts nothing further. The "
       "phase-shift vibrato", 8, 290, 1.15)
s.text("bends pitch rather than gating level — see notes.md.", 8, 294, 1.15)

# ======================= POWER SUPPLY — GZ34 rectifier =====================
s.text("Power — Haddon mains transformer (280-0-280 V, 160 mA HT), GZ34 "
       "rectifier, 10-20 H Radiospares choke", 200, 202, 1.6)
MY = 230.92
qs = s.jack("QS", "3-pin", 212, MY + 2.54, lx=-4.0, ly=-6.6, mirror=True)
l, r = s.fuse("F1", "3A", 226, MY)
s.wire(qs["tip"][0], MY, l, MY)
l2, r2 = s.switch("SW4", "DPST", 244, MY)
s.wire(r, MY, l2, MY)
t2 = s.pt("T2", "280-0-280 V", 268, 236, lx=-6.35, ly=-12.4)
s.wire(r2, MY, t2["pri1"][0], MY)
s.wire(qs["tip"][0], MY + 5.08, 219, MY + 5.08)
s.wire(219, MY + 5.08, 219, 241.08)
s.wire(219, 241.08, t2["pri2"][0], 241.08)
for pin, label in [("ht_a", "HT_A"), ("ht_ct", "GND"), ("ht_b", "HT_B")]:
    x, y = t2[pin]
    s.wire(x, y, x + 6, y)
    s.glabel(label, x + 6, y, 0)
s.text("Primary taps 115 / 160 / 205 / 225 / 245 V; SW4 breaks both mains "
       "poles", 200, 254, 1.15)
s.text("T2 also carries the 6.3 V / 6 A heater winding and the GZ34's own "
       "5 V / 2 A winding", 200, 258, 1.15)
s.text("(heaters not drawn — see layout.yaml). OS/065 shows no pilot lamp, "
       "so none is drawn.", 200, 262, 1.15)

for x, ref, ht in [(314, "V10A", "HT_A"), (332, "V10B", "HT_B")]:
    s.glabel(ht, x, 216, 90)
    s.wire(x, 216, x, 221.38)
    s.diode_tube(ref, "GZ34", x, 229, lx=(-12.4 if ref == "V10A" else 6.0))
    s.wire(x, 236.62, x, 242)
s.wire(314, 242, 350.38, 242)
s.junction(332, 242)
s.junction(342, 242)
s.sym("C", "C39", "16u", 342, 245.81, lx=2.6)
s.gnd(342, 249.62)
s.sym("CHOKE", "CH1", "10-20H", 358, 242, lx=-5.6, ly=-7.4)
s.wire(365.62, 242, 376, 242)
s.junction(376, 242)
s.sym("C", "C40", "16u", 376, 245.81, lx=2.6)
s.gnd(376, 249.62)
s.wire(376, 242, 388, 242)
s.glabel("B+1", 388, 242, 0)
s.text("+320 V", 380, 236, 1.15)

# two 22 k droppers off the +320 V rail: one to the front end, one to the
# inverter. The Vibrato/Tremolo chain hangs off a node this scan does not
# resolve (see the note in that channel), so it is not drawn from the rail.
for gx, dref, cref, rail, note in [(296, "R10", "C4", "B+N", "+290 V"),
                                   (364, "R11", "C8", "B+P", "")]:
    s.glabel("B+1", gx, 272, 180)
    s.wire(gx, 272, gx + 6, 272)
    l, r = s.series_h("R", dref, "22k", gx + 16, 272)
    s.wire(gx + 6, 272, l, 272)
    s.wire(r, 272, gx + 34, 272)
    s.junction(gx + 22, 272)
    s.sym("C", cref, "8u", gx + 22, 275.81, lx=2.6)
    s.gnd(gx + 22, 279.62)
    s.glabel(rail, gx + 34, 272, 0)
    if note:
        s.text(note, gx + 42, 268, 1.15)


s.write(OUT)
print(f"wrote {OUT}")
