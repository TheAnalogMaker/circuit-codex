#!/usr/bin/env python3
"""Generate amps/ac15/schematic.kicad_sch from the stage-template library.

Values per JMI drawing OA/031, "VOX AC.15 amplifier circuit No. 3" (29-4-60) —
see amps/ac15/meta.yaml for the sources. Redrawn from circuit facts; never a
trace of a factory drawing.

The sheet reads left to right. The Normal channel runs along the top: three
input jacks into an EF86 pentode on Philips' own published application network
(220 kOhm anode load, 1 MOhm screen feed with a 0.1 uF bypass, 2.2 kOhm cathode),
out through the Brilliance switch to the Normal volume. The Vibrato/Tremolo
channel runs below it. Both channels arrive at the ECC83 long-tailed pair in the
centre — at OPPOSITE grids, which is how this amp mixes them — and the Top Cut
control bridges the pair's two anodes. The cathode-biased EL84 pair and the
output transformer sit on the right; the EZ81 supply runs along the bottom.

There is no tone stack, no bias supply and no negative-feedback loop: all three
absences are visible on the sheet.

SCOPE. Every part the corpus asserts a connection for carries a designator and
is drawn. The Vibrato/Tremolo channel's tone, phase-shift, modulator and
oscillator networks are NOT asserted: the published OA/031 scan resolves their
values but not their interconnection, so they carry no designator in bom.yaml
and appear here as the named interfaces each valve runs into. That is the same
treatment the tweed entries give their presence and feedback parts. Heaters and
the 6.3 V winding are an annotation layer (see amps/ac15/layout.yaml).

Rails: B+1 = +315 V (the rail after the choke and standby switch), B+N = Normal
channel, B+P = phase inverter, B+V = Vibrato/Tremolo channel — each behind its
own 22 kOhm dropper, exactly as the drawing shows.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ac15" / "schematic.kicad_sch"
s = Sch()


def input_network(jrefs, srefs, svals, ys, leakref, gbx, gy):
    """Three input jacks (two normal, one the drawing's alternate single jack),
    each through its own grid stopper onto a shared grid bus with a 1 MOhm leak.
    Returns the grid-bus x."""
    for jref, sref, sval, y in zip(jrefs, srefs, svals, ys):
        j = s.jack(jref, "1/4 in", 20, y + 2.54, mirror=True)
        l, r = s.series_h("R", sref, sval, 42, y)
        s.wire(j["tip"][0], y, l, y)
        s.wire(r, y, gbx, y)
        # sleeve to chassis, stepped clear of the jack below it
        s.wire(j["sleeve"][0], y + 5.08, 30, y + 5.08)
        s.wire(30, y + 5.08, 30, y + 8.08)
        s.gnd(30, y + 8.08)
    s.wire(gbx, ys[0], gbx, ys[-1])
    for y in ys[1:]:
        s.junction(gbx, y)
    s.wire(gbx, ys[-1], gbx, ys[-1] + 6)
    s.sym("R", leakref, "1M", gbx, ys[-1] + 9.81, lx=-9.4)
    s.gnd(gbx, ys[-1] + 13.62)
    return gbx


# ============================== TITLE ======================================
s.note('No tone stack · no bias supply · no negative feedback. Both channels mix INSIDE the phase inverter, at opposite grids. Rails: B+1 +315 V · B+N Normal · B+P inverter · B+V vibrato')
s.note('Heaters, the 6.3 V winding and the pilot-lamp wiring are an annotation layer — see netlist.cir, bom.yaml and layout.yaml.')

# ====================== NORMAL CHANNEL — EF86 preamp =======================
s.text('Normal channel', 16, 27.5, 1.6)
input_network(["JN1", "JN2", "JN"], ["RIN1", "RIN2", "RGS1"], ["68k", "68k", "33k"],
              [36, 50, 64], "RG1", 60, 50)

v1 = s.pentode("V1", "EF86", 76, 50, lx=-16.0, ly=-9.2)
s.wire(60, 50, v1["g1"][0], 50)
s.plate_load("RL1", "220k", v1["p"], "B+N")
TEE_N = v1["p"][1] - 3.48                       # 38.265 — the EF86 anode node
# screen: 1 MOhm feed from B+N, 0.1 uF to chassis
s.wire(v1["g2"][0], v1["g2"][1], 92, v1["g2"][1])
s.sym("R", "RS1", "1M", 92, v1["g2"][1] - 3.81)
s.wire(92, v1["g2"][1] - 7.62, 92, 32)
s.glabel("B+N", 92, 32, 90)
s.junction(92, v1["g2"][1])
s.wire(92, v1["g2"][1], 100, v1["g2"][1])
s.sym("C", "CS1", ".1u", 100, v1["g2"][1] + 3.81)
s.gnd(100, v1["g2"][1] + 7.62)
# cathode: 2.2k with a 25 uF bypass
s.wire(76, v1["k"][1], 76, 60)
s.wire(76, 60, 82, 60)
s.shunt_rc("RK1", "2.2k", "CK1", "25u", 82, 60)
s.text("g3 (pin 8) strapped to the cathode", 66, 74, 1.1)

# anode -> 0.01 uF coupler -> Brilliance (250 pF bridged by the switch) -> volume
s.wire(76, TEE_N, 104, TEE_N)
s.junction(76, TEE_N)
cl, cr = s.series_h("C", "CO1", ".01u", 110, TEE_N)
s.wire(104, TEE_N, cl, TEE_N)
s.wire(cr, TEE_N, 120, TEE_N)
swl, swr = s.switch("SW-BRIL", "SPST", 131, TEE_N, lx=-3.4, ly=5.6)
s.wire(120, TEE_N, swl, TEE_N)
s.wire(swr, TEE_N, 142, TEE_N)
s.junction(120, TEE_N)
s.junction(142, TEE_N)
s.wire(120, TEE_N, 120, 30)
bl, br = s.series_h("C", "CBR", "250p", 131, 30)
s.wire(120, 30, bl, 30)
s.wire(br, 30, 142, 30)
s.wire(142, 30, 142, TEE_N)
s.text("Brilliance: the switch shorts the 250 pF cap out, so 'on' couples treble only",
       104, 57, 1.1)
s.sym("POT", "VR1", "500k vol", 142, TEE_N + 3.81)
s.wire(142, TEE_N + 7.62, 142, 48.5)
s.gnd(142, 48.5)
s.wire(147.08, TEE_N + 3.81, 156, TEE_N + 3.81)
s.glabel("NORM VOL", 156, TEE_N + 3.81, 0)

# ================== VIBRATO / TREMOLO CHANNEL (not asserted) ===============
s.text('Vibrato/Tremolo channel — \u2018Vibravox\u2019', 16, 89.5, 1.6)
input_network(["JV1", "JV2", "JV"], ["RIN3", "RIN4", "RGS2"], ["68k", "68k", "33k"],
              [98, 112, 126], "RG2", 60, 112)

v5a = s.triode("V5A", "ECC83", 76, 112)
s.wire(60, 112, v5a["g"][0], 112)
s.wire(76, 119.62, 76, 122)
s.wire(76, 122, 82, 122)
s.shunt_rc("RKV1", "2.2k", "CKV1", "25u", 82, 122)
s.wire(76, 104.38, 76, 100.9)
s.wire(76, 100.9, 86, 100.9)
s.glabel("TONE-NET IN", 86, 100.9, 0)

s.glabel("TONE-NET OUT", 104, 112, 180)
s.wire(104, 112, 110, 112)
cl, cr = s.series_h("C", "CVC", ".01u", 116, 112)
s.wire(110, 112, cl, 112)
v5b = s.triode("V5B", "ECC83", 140, 112)
s.wire(cr, 112, v5b["g"][0], 112)
s.junction(126, 112)
s.sym("R", "RGV", "1M", 126, 115.81, lx=2.6, ly=-8.6)
s.gnd(126, 119.62)
s.wire(140, 119.62, 140, 124)
s.wire(140, 124, 146, 124)
s.sym("R", "RKV2", "1.5k", 146, 127.81)
s.gnd(146, 131.62)
s.wire(140, 104.38, 140, 100.9)
s.wire(140, 100.9, 150, 100.9)
s.glabel("LADDER IN", 150, 100.9, 0)

s.glabel("LADDER OUT", 160, 112, 180)
s.wire(160, 112, 166, 112)
s.sym("POT", "VR2", "500k vol", 166, 115.81)
s.wire(166, 119.62, 166, 122)
s.gnd(166, 122)
s.wire(171.08, 115.81, 178, 115.81)
s.glabel("VIB VOL", 178, 115.81, 0)

# the modulator and the oscillator: each valve drawn against the named network
# it works into. Those networks are inventoried in bom.yaml, not asserted here.
v6 = s.triode("V6", "ECC82 mod", 70, 152)
s.wire(70, 144.38, 70, 140)
s.glabel("MOD-NET a", 70, 140, 90)
s.wire(62.38, 152, 56, 152)
s.glabel("MOD-NET g", 56, 152, 180)
s.wire(70, 159.62, 70, 164)
s.glabel("MOD-NET k", 70, 164, 270)

v7 = s.triode("V7", "ECC83 osc", 130, 152)
s.wire(130, 144.38, 130, 140)
s.glabel("OSC-NET a", 130, 140, 90)
s.wire(122.38, 152, 116, 152)
s.glabel("OSC-NET g", 116, 152, 180)
s.wire(130, 159.62, 130, 164)
s.glabel("OSC-NET k", 130, 164, 270)

s.glabel("B+V", 176, 148, 180)
s.wire(176, 148, 184, 148)
s.text("→ Vibrato/Tremolo networks", 185, 148.5, 1.1)

s.note("The two-position TONE network, the five-section phase-shift ladder, the ECC82 "
       "modulator network and the ECC83 oscillator network (with Depth, Speed, the "
       "fast/slow switch and the footswitch jack) are listed part by part in bom.yaml. "
       "The published drawing resolves their VALUES but not their interconnection, so "
       "this sheet names the interfaces and asserts nothing further. The phase-shift "
       "vibrato bends pitch rather than gating level — see notes.md.")

# ================= PHASE INVERTER — ECC83 long-tailed pair =================
s.text("Phase inverter — long-tailed pair; both channels enter, at opposite grids",
       196, 31, 1.6)
s.glabel("NORM VOL", 176, 58, 180)
s.wire(176, 58, 182, 58)
cl, cr = s.series_h("C", "CIN1", ".01u", 190, 58)
s.wire(182, 58, cl, 58)
s.wire(cr, 58, 203, 58)
s.glabel("VIB VOL", 176, 104, 180)
s.wire(176, 104, 182, 104)
cl, cr = s.series_h("C", "CIN2", ".01u", 190, 104)
s.wire(182, 104, cl, 104)
s.wire(cr, 104, 203, 104)

v2a = s.triode("V2A", "ECC83", 215, 58)
v2b = s.triode("V2B", "ECC83", 215, 104)
s.junction(203, 58)
s.wire(203, 58, v2a["g"][0], 58)
s.junction(203, 104)
s.wire(203, 104, v2b["g"][0], 104)
s.plate_load("RLA", "100k", v2a["p"], "B+P")
s.plate_load("RLB", "100k", v2b["p"], "B+P")
TEE_A, TEE_B = v2a["p"][1] - 3.48, v2b["p"][1] - 3.48       # 46.9 / 92.9

# both 1 MOhm grid leaks return to the tail junction, between the two valves
s.wire(203, 58, 203, 65)
s.sym("R", "RGA", "1M", 203, 68.81, lx=-9.4)
s.wire(203, 72.62, 203, 86.62)
s.sym("R", "RGB", "1M", 203, 90.43, lx=-9.4)
s.wire(203, 94.24, 203, 104)
s.junction(203, 76)
s.wire(203, 76, 228, 76)
# shared 1.2k cathode over a 47k tail
s.wire(215, 65.62, 215, 68.38)
s.wire(215, 68.38, 228, 68.38)
s.wire(215, 111.62, 215, 114)
s.wire(215, 114, 222, 114)
s.wire(222, 68.38, 222, 114)
s.junction(222, 68.38)
s.sym("R", "RTAIL", "1.2k", 228, 72.19)
s.junction(228, 76)
s.sym("R", "RT2", "47k", 228, 79.81)
s.gnd(228, 83.62)

# ---- Top Cut: 250k in series with 0.005 uF, bridged across the two anodes ---
s.wire(215, TEE_A, 246, TEE_A)
s.junction(215, TEE_A)
s.wire(215, TEE_B, 246, TEE_B)
s.junction(215, TEE_B)
s.wire(246, TEE_A, 246, 56)
s.junction(246, TEE_A)
s.sym("C", "CTC", ".005u", 246, 59.81)
s.wire(246, 63.62, 246, 68)
s.sym("POT", "VR3", "250k top cut", 246, 71.81, lx=2.6)
s.wire(246, 75.62, 246, TEE_B)
s.junction(246, TEE_B)
s.wire(251.08, 71.81, 251.08, 79)
s.wire(251.08, 79, 246, 79)
s.junction(246, 79)
s.text("Top Cut — the amp's only tone control, and it sits AFTER the inverter",
       232, 122, 1.15)

# ==================== OUTPUT — EL84 pair, cathode bias =====================
s.text("Output — EL84 pair, one shared 130 Ohm cathode resistor, no bias supply, "
       "no feedback loop", 268, 24, 1.6)
for tee, cref, vref, glref, stref, scref, g1y in [
        (TEE_A, "CC1", "V3", "RGL1", "RST1", "RSC1", 50),
        (TEE_B, "CC2", "V4", "RGL2", "RST2", "RSC2", 110)]:
    s.wire(246, tee, 258, tee)
    cl, cr = s.series_h("C", cref, ".01u", 264, tee)
    s.wire(258, tee, cl, tee)
    s.wire(cr, tee, 282, tee)
    s.wire(282, tee, 282, g1y)
    s.junction(282, g1y)
    s.sym("R", glref, "220k", 282, g1y + 3.81, lx=-9.6)
    s.gnd(282, g1y + 7.62)
    l, r = s.series_h("R", stref, "1.5k", 288.57, g1y)
    s.wire(282, g1y, l, g1y)
    p = s.pentode(vref, "EL84", 300, g1y, lx=-15.4, ly=-12.4)
    s.wire(r, g1y, p["g1"][0], g1y)
    # screen through its 100 Ohm stopper, off the same rail as the anodes
    s.wire(p["g2"][0], p["g2"][1], 318, p["g2"][1])
    l, r = s.series_h("R", scref, "100", 324, p["g2"][1])
    s.wire(318, p["g2"][1], l, p["g2"][1])
    s.wire(r, p["g2"][1], 331, p["g2"][1])
    s.glabel("B+1", 331, p["g2"][1], 0)

# shared cathode: ONE 130 Ohm / 5 W resistor with a 50 uF bypass — the whole bias
s.wire(300, 56.985, 300, 60)
s.wire(300, 60, 312, 60)
s.wire(300, 116.985, 300, 120)
s.wire(300, 120, 312, 120)
s.wire(312, 60, 312, 126)
s.junction(312, 120)
s.sym("R", "R22", "130 5W", 312, 129.81, lx=-13.6, ly=-0.4)
s.sym("C", "CKO", "50u", 319.62, 129.81, lx=2.6, ly=-0.4)
s.wire(312, 126, 319.62, 126)
s.wire(312, 133.62, 319.62, 133.62)
s.gnd(312, 133.62)

# ---- output transformer + speaker jacks ----------------------------------
s.sym("OT_PP", "T2", "8/15 ohm", 352, 66)
s.wire(300, 41.745, 300, 38)
s.wire(300, 38, 338, 38)
s.wire(338, 38, 338, 60.92)
s.wire(338, 60.92, 343.11, 60.92)
s.wire(300, 101.745, 300, 99)
s.wire(300, 99, 334, 99)
s.wire(334, 99, 334, 71.08)
s.wire(334, 71.08, 343.11, 71.08)
s.wire(343.11, 66, 330, 66)
s.wire(330, 66, 330, 58)
s.glabel("B+1", 330, 58, 90)
s.wire(360.89, 68.54, 370, 68.54)
s.wire(370, 68.54, 370, 76)
s.gnd(370, 76)
s.wire(360.89, 63.46, 400, 63.46)
s.wire(400, 63.46, 400, 102)
for jref, jy in [("JSPK1", 86), ("JSPK2", 102)]:
    j = s.jack(jref, "1/4 in", 386, jy + 2.54, mirror=True)
    s.wire(400, jy, j["tip"][0], jy)
    s.wire(j["sleeve"][0], jy + 5.08, 396, jy + 5.08)
    s.wire(396, jy + 5.08, 396, jy + 9)
    s.gnd(396, jy + 9)
s.junction(400, 86)

# ======================= POWER SUPPLY — EZ81 rectifier =====================
s.text("Power — Haddon mains transformer (300-0-300 V HT), EZ81 rectifier, "
       "10-20 H Radiospares choke", 16, 199, 1.6)
s.glabel("MAINS L", 16, 212.92, 180)
s.wire(16, 212.92, 20, 212.92)
l, r = s.fuse("F1", "2A", 28, 212.92)
s.wire(20, 212.92, l, 212.92)
l2, r2 = s.switch("SW1", "DPST", 46, 212.92)
s.wire(r, 212.92, l2, 212.92)
l3, r3 = s.switch("SW2", "5-pos", 64, 212.92)
s.wire(r2, 212.92, l3, 212.92)
t1 = s.pt("T1", "Haddon OF 031", 88, 218)
s.wire(r3, 212.92, t1["pri1"][0], 212.92)
s.glabel("MAINS N", 16, 223.08, 180)
s.wire(16, 223.08, t1["pri2"][0], 223.08)
s.text("SW2 selects the 115 / 160 / 205 / 225 / 245 V primary taps; SW1 breaks both "
       "mains poles", 16, 231, 1.15)
s.text("T1 also carries the 6.3 V · 4 A heater winding (heaters not drawn)", 16, 235, 1.15)
for pin, label in [("ht_a", "HT_A"), ("ht_ct", "GND"), ("ht_b", "HT_B")]:
    x, y = t1[pin]
    s.wire(x, y, x + 6, y)
    s.glabel(label, x + 6, y, 0)

for x, ref, ht in [(128, "V8A", "HT_A"), (146, "V8B", "HT_B")]:
    s.glabel(ht, x, 192, 90)
    s.wire(x, 192, x, 197.38)
    s.diode_tube(ref, "EZ81", x, 205, lx=(-11.8 if ref == "V8A" else 6.0))
    s.wire(x, 212.62, x, 218)
s.wire(128, 218, 172.38, 218)
s.junction(146, 218)
s.junction(160, 218)
s.sym("C", "CR1", "16u", 160, 221.81)
s.gnd(160, 225.62)
s.text("+325 V", 152, 212, 1.15)
s.sym("CHOKE", "CH1", "10-20H", 180, 218, lx=-5.6, ly=-7.4)
l, r = s.switch("SW7", "standby", 204, 218)
s.wire(187.62, 218, l, 218)
s.wire(r, 218, 240, 218)
s.junction(222, 218)
s.sym("C", "CR2", "16u", 222, 221.81)
s.gnd(222, 225.62)
s.text("+315 V", 228, 212, 1.15)

# three parallel 22k droppers off the +315 V rail — one per channel, one for the PI
s.junction(240, 218)
s.wire(240, 218, 246, 218)
s.wire(246, 218, 246, 250)
s.junction(246, 218)
for y, dref, dval, cref, cval, rail in [
        (218, "RD1", "22k", "CF1", "8u", "B+N"),
        (234, "RD2", "22k", "CF2", "8u", "B+P"),
        (250, "RD3", "22k", "CF3", "33u", "B+V")]:
    if y != 218:
        s.junction(246, y)
    s.wire(246, y, 250, y)
    l, r = s.series_h("R", dref, dval, 256, y)
    s.wire(250, y, l, y)
    s.wire(r, y, 276, y)
    s.junction(268, y)
    s.sym("C", cref, cval, 268, y + 3.81)
    s.gnd(268, y + 7.62)
    s.glabel(rail, 276, y, 0)

# pilot lamp off the 6.3 V winding
s.glabel("6.3V", 274, 199.92, 180)
s.wire(274, 199.92, 288, 199.92)
s.lamp("PL1", "6.3 V", 288, 205)
s.gnd(288, 210.08)

s.write(OUT)
print(f"wrote {OUT}")
