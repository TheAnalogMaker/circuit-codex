#!/usr/bin/env python3
"""Generate amps/6161/schematic.kicad_sch from the stage-template library.

Values per the factory drawing whose title block reads "Valco Model 6161" —
see amps/6161/meta.yaml. The sheet reads: the two channel preamps stacked at
the top left, each fed by a pair of jacks marked Treble and Bass; the summing
network and the amplifier's single tone control in the middle; the paraphase
phase inverter and the 6973 output pair on the right; the tremolo oscillator,
its Intensity network and the cathode-follower that modulates channel 2 along
the bottom left; and the power supply at the bottom right. Drawn on A3 so every
block clears its neighbours.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
BP1 = the 5Y3-GT reservoir, which is also the output-transformer centre tap and
therefore the 6973 plate node; BP2 = the 6973 screen node, one 1 kΩ dropper
below it (this circuit does NOT tap its screens on the transformer primary);
B1 = the preamp and inverter rail, a 15 kΩ dropper below BP2. Each preamp
channel hangs off B1 through its own 100 kΩ dropper. The drawing prints NO
voltages of any kind, so no rail carries one here either.

Heaters, the PT primary/mains beyond the transformer (fuse, switch, the mains
capacitor, the line-reverse arrangement), the neon pilot, the input jacks, the
footswitch jack and the speakers are omitted here (annotation layer) — see
netlist.cir, bom.yaml, meta.yaml and the board layout (layout.yaml).

The tremolo oscillator IS drawn: the schematic documents the whole circuit.
Only its DC operating point is excluded from netlist.cir (a running phase-shift
oscillator has no static bias point) — see amps/6161/notes.md.

The two markers lettered A are the drawing's own, and they are NOT one node:
the sheet brings BOTH output-tube grid nodes out to a marker lettered A and
resolves them no further. They are drawn here as the sheet draws them — two
stubs, each lettered A — and are deliberately not global labels, which would
join them.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6161" / "schematic.kicad_sch"
s = Sch()

GB = 40          # input grid-bus x
MIXX = 160       # the summing node's column
MIXY = 87        # the summing node


def input_pair(y, jt, jb, cin, rmx, rleak, dy=5):
    """A channel's input: a Treble jack through 0.005 µF and a Bass jack through
    100 kΩ onto ONE grid node behind a 470 kΩ leak. The jack you pick is the
    voicing — there are no channel tone controls."""
    s.glabel(jt, 12, y - dy, 180)
    s.glabel(jb, 12, y + dy, 180)
    l, r = s.series_h("C", cin, ".005u", 26, y - dy)
    s.wire(12, y - dy, l, y - dy)
    s.wire(r, y - dy, GB, y - dy)
    l, r = s.series_h("R", rmx, "100k", 26, y + dy)
    s.wire(12, y + dy, l, y + dy)
    s.wire(r, y + dy, GB, y + dy)
    s.wire(GB, y - dy, GB, y + dy)
    s.junction(GB, y)
    s.junction(GB, y + dy)
    s.sym("R", rleak, "470k", GB, y + dy + 3.81)
    s.gnd(GB, y + dy + 7.62)


def volume(vtop, y, vref, cbref, rmref, feed_y):
    """A channel's 500 kΩ volume with its 500 pF bright cap bridging top to
    wiper, and the 270 kΩ mixing resistor from the wiper into the summing node.
    `vtop` is the x of the volume column; `y` is the top-lug level."""
    s.sym("POT", vref, "500k-A", vtop, y + 3.81, lx=-11.0, ly=2.4)
    s.junction(vtop, y)
    s.gnd(vtop, y + 7.62)
    w = (vtop + 5.08, y + 3.81)                       # wiper
    s.sym("C", cbref, "500p", vtop + 12, y + 3.81, rot=90, lx=-3.2, ly=-6.2)
    s.wire(w[0], w[1], vtop + 8.19, w[1])
    s.wire(vtop + 15.81, w[1], vtop + 19, w[1])
    s.wire(vtop + 19, w[1], vtop + 19, y)
    s.wire(vtop, y, vtop + 19, y)
    s.junction(vtop + 19, y)
    # wiper -> 270k mixing resistor -> the summing node
    s.junction(w[0], w[1])
    s.wire(w[0], w[1], w[0], feed_y)
    l, r = s.series_h("R", rmref, "270k", w[0] + 7, feed_y)
    s.wire(w[0], feed_y, l, feed_y)
    s.wire(r, feed_y, MIXX, feed_y)
    s.wire(MIXX, feed_y, MIXX, MIXY)


# ============================ TITLE ==================================
s.note('Rails: BP1 reservoir · OT centre tap · 6973 plates — BP2 6973 screens, on their OWN supply node (not tapped on the transformer primary) — B1 preamp and inverter rail. The drawing prints no voltages of any kind.')
s.note('Heaters, the mains side beyond the transformer (2 A fuse, switch, mains capacitor, line-reverse arrangement), the neon pilot, the input and footswitch jacks and the two 10-inch speakers are omitted here — see netlist.cir, bom.yaml, layout.yaml.')
s.note("The two stubs lettered A are the sheet's own markers on the two output-grid nodes; they are two separate nodes, not one, and the published redraw of the Supro-badged sibling bridges them with a silencing switch.")

# ============================ CHANNEL 1 ==============================
Y1 = 62
s.caption('Channel 1 — 2.2 kΩ cathode left UNBYPASSED, and no grid stopper', 12, 46, 1.6)
input_pair(Y1, "CH1 TREBLE", "CH1 BASS", "CIN1", "RMX1", "RG1")
t1a = s.triode("V1A", "12AX7", 54, Y1)
s.wire(GB, Y1, t1a["g"][0], Y1)
# plate -> 270k load -> channel-1 supply node -> 100k dropper -> B1
TEE1 = 50.9
s.wire(54, t1a["p"][1], 54, TEE1)
s.junction(54, TEE1)
s.sym("R", "RL1", "270k", 54, TEE1 - 3.81)
s.wire(54, TEE1 - 7.62, 54, 41)
s.junction(54, 41)
s.sym("R", "RD3", "100k", 54, 37.19)
s.wire(54, 33.38, 54, 31)
s.glabel("B1", 54, 31, 90)
s.sym("C", "CF4", ".05u", 66, 37.19)
s.wire(54, 41, 66, 41)
s.glabel("GND", 66, 33.38, 90)
# cathode, no bypass can
s.wire(54, t1a["k"][1], 54, 71)
s.sym("R", "RK1", "2.2k", 54, 74.81)
s.gnd(54, 78.62)
# plate -> 0.005 coupler -> volume
l, r = s.series_h("C", "CV1", ".005u", 118, TEE1)
s.wire(54, TEE1, l, TEE1)
s.wire(r, TEE1, 128, TEE1)
volume(128, TEE1, "VR1", "CB1", "RM1", 66)

# ============================ CHANNEL 2 ==============================
Y2 = 120
s.caption('Channel 2 — 2.2 kΩ grid stopper, 1.5 kΩ cathode bypassed by 35 µF', 12, 90, 1.6)
s.note("Channel 2 also carries a 500 pF cut on its plate, and its cathode is node C — shared with the tremolo follower.")
input_pair(Y2, "CH2 TREBLE", "CH2 BASS", "CIN2", "RMX2", "RG2")
t1b = s.triode("V1B", "12AX7", 60, Y2)
l, r = s.series_h("R", "RGS1", "2.2k", 46, Y2)
s.wire(GB, Y2, l, Y2)
s.wire(r, Y2, t1b["g"][0], Y2)
TEE2 = 108.9
s.wire(60, t1b["p"][1], 60, TEE2)
s.junction(60, TEE2)
s.sym("R", "RL2", "270k", 60, TEE2 - 3.81)
s.wire(60, TEE2 - 7.62, 60, 99)
s.junction(60, 99)
s.sym("R", "RD4", "100k", 60, 95.19)
s.wire(60, 91.38, 60, 89)
s.glabel("B1", 60, 89, 90)
s.sym("C", "CF5", ".05u", 72, 95.19)
s.wire(60, 99, 72, 99)
s.glabel("GND", 72, 91.38, 90)
# the 500 pF plate-to-ground cut this channel has and channel 1 does not
s.sym("C", "CP2", "500p", 46, TEE2 - 3.81)
s.wire(46, TEE2, 60, TEE2)
s.glabel("GND", 46, TEE2 - 7.62, 90)
# cathode: 1.5k || 35 uF, and the node the tremolo follower lands on
s.wire(60, t1b["k"][1], 60, 130)
s.shunt_rc("RK2", "1.5k", "CK2", "35u", 60, 130)
s.junction(60, 130)
s.glabel("C", 50, 130, 180)
s.wire(50, 130, 60, 130)
# plate -> 0.005 -> 270k shunt -> 0.005 -> volume (channel 2 only)
l, r = s.series_h("C", "CI1", ".005u", 80, TEE2)
s.wire(60, TEE2, l, TEE2)
s.wire(r, TEE2, 90, TEE2)
s.junction(90, TEE2)
s.sym("R", "RI1", "270k", 90, TEE2 + 3.81)
s.gnd(90, TEE2 + 7.62)
l, r = s.series_h("C", "CI2", ".005u", 100, TEE2)
s.wire(90, TEE2, l, TEE2)
s.wire(r, TEE2, 128, TEE2)
volume(128, TEE2, "VR2", "CB2", "RM2", 124)

# ============================ MIXER + TONE ===========================
s.caption("Volume · mixer · tone — the two wipers sum through 270 kΩ apiece into one node, and the amp's ONLY tone control hangs there, trimming both channels at once.", 150, 74, 1.5)
s.junction(MIXX, MIXY)
s.sym("C", "CT1", "500p", MIXX - 8, MIXY + 3.81, lx=-11.0, ly=2.4)
s.wire(MIXX - 8, MIXY, MIXX, MIXY)
s.gnd(MIXX - 8, MIXY + 7.62)
s.sym("C", "CT2", ".005u", MIXX + 8, MIXY + 3.81)
s.wire(MIXX, MIXY, MIXX + 8, MIXY)
s.junction(MIXX + 8, MIXY)
s.wire(MIXX + 8, MIXY + 7.62, MIXX + 8, MIXY + 9.19)
s.sym("POT", "VR3", "500k-A", MIXX + 8, MIXY + 13)
s.wire(MIXX + 13.08, MIXY + 13, MIXX + 20, MIXY + 13)
s.glabel("GND", MIXX + 20, MIXY + 13, 0)
s.wire(MIXX + 8, MIXY + 16.81, MIXX + 8, MIXY + 19)
s.text("Tone — a rheostat: wiper to ground, far lug left free", MIXX - 6, MIXY + 23, 1.2)
# mixer -> 300 pF -> the inverter's driver grid
l, r = s.series_h("C", "CPI", "300p", MIXX + 22, MIXY)
s.wire(MIXX + 8, MIXY, l, MIXY)
s.wire(r, MIXY, 192, MIXY)
s.junction(192, MIXY)
s.sym("R", "RG3", "1M", 192, MIXY + 3.81)
s.gnd(192, MIXY + 7.62)

# ============================ PARAPHASE INVERTER =====================
s.text("Paraphase phase inverter — no shared cathode, no tail, no feedback: the second half is fed by tapping the FIRST output grid through a 270 kΩ / 12 kΩ divider,",
       196, 48, 1.5)
s.text("and its own 3.9 kΩ cathode is left unbypassed to hold its gain down to what that divider asks for. The 12 kΩ sets the balance of the whole output stage on its own.",
       196, 52, 1.3)
t2a = s.triode("V2A", "12AX7", 210, 87)
s.wire(192, MIXY, t2a["g"][0], 87)
TEEA = 75.9
s.wire(210, t2a["p"][1], 210, TEEA)
s.junction(210, TEEA)
s.sym("R", "RL3", "270k", 210, TEEA - 3.81)
s.wire(210, TEEA - 7.62, 210, 65)
s.glabel("B1", 210, 65, 90)
s.wire(210, t2a["k"][1], 210, 96)
s.shunt_rc("RK3", "2.2k", "CK3", ".05u", 210, 96)

t2b = s.triode("V2B", "12AX7", 210, 140)
TEEB = 128.9
s.wire(210, t2b["p"][1], 210, TEEB)
s.junction(210, TEEB)
s.sym("R", "RL4", "270k", 210, TEEB - 3.81)
s.wire(210, TEEB - 7.62, 210, 118)
s.glabel("B1", 210, 118, 90)
s.wire(210, t2b["k"][1], 210, 149)
s.sym("R", "RK4", "3.9k", 210, 152.81)
s.gnd(210, 156.62)

# the divider: V5 grid -> 270k -> the V2B grid tap -> 12k -> ground
s.sym("R", "RPA", "270k", 250, 116)
s.wire(250, 70, 250, 112.19)
s.wire(250, 119.81, 250, 176)
s.junction(250, 176)
s.sym("R", "RPB", "12k", 250, 179.81)
s.gnd(250, 183.62)
s.wire(250, 176, 196, 176)
s.wire(196, 176, 196, 140)
s.wire(196, 140, t2b["g"][0], 140)

# ============================ OUTPUT COUPLERS + 6973 =================
s.text("6973 output pair — ONE shared 250 Ω cathode resistor biases both bottles; there is no bias supply and no negative-feedback loop anywhere around the stage.",
       262, 40, 1.5)
# V2A plate -> 0.01 -> V5 grid (the node the divider hangs on)
s.wire(210, TEEA, 216, TEEA)
s.wire(216, TEEA, 216, 70)
l, r = s.series_h("C", "CC1", ".01u", 228, 70)
s.wire(216, 70, l, 70)
s.wire(r, 70, 302.38, 70)
s.junction(250, 70)
s.junction(268, 70)
s.wire(268, 70, 268, 60)
s.text("A", 266, 58, 2.4)
# V2B plate -> 0.01 -> V4 grid
s.wire(210, TEEB, 216, TEEB)
s.wire(216, TEEB, 216, 186)
l, r = s.series_h("C", "CC2", ".01u", 240, 186)
s.wire(216, 186, l, 186)
s.wire(r, 186, 272, 186)
s.wire(272, 186, 272, 175)
s.wire(268, 175, 302.38, 175)
s.junction(272, 175)
s.junction(280, 175)
s.wire(268, 175, 268, 165)
s.text("A", 266, 163, 2.4)
s.sym("R", "RGL2", "470k", 280, 178.81)
s.gnd(280, 182.62)

v5 = s.pentode("V5", "6973", 310, 70)
v4 = s.pentode("V4", "6973", 310, 175)
s.wire(v5["g2"][0], v5["g2"][1], 326, v5["g2"][1])
s.glabel("BP2", 326, v5["g2"][1], 0)
s.wire(v4["g2"][0], v4["g2"][1], 326, v4["g2"][1])
s.glabel("BP2", 326, v4["g2"][1], 0)
s.wire(310, v5["k"][1], 310, 84)
s.glabel("KOUT", 310, 84, 270)
s.wire(310, v4["k"][1], 310, 190)
s.glabel("KOUT", 310, 190, 270)
# the pair's entire bias arrangement
s.glabel("KOUT", 256, 209, 180)
s.wire(260, 209, 268, 209)
s.shunt_rc("RKO", "250 7W", "CKO", "35u", 268, 209)

# ---- output transformer + speakers ----------------------------------
s.sym("OT_PP", "T2", "340-6", 370, 122, lx=-6.35, ly=-14.5)
s.wire(310, v5["p"][1], 310, 52)
s.wire(310, 52, 352, 52)
s.wire(352, 52, 352, 116.92)
s.wire(352, 116.92, 361.11, 116.92)
s.wire(310, v4["p"][1], 310, 158)
s.wire(310, 158, 340, 158)
s.wire(340, 158, 340, 127.08)
s.wire(340, 127.08, 361.11, 127.08)
s.wire(361.11, 122, 354, 122)
s.glabel("BP1", 354, 122, 180)
s.wire(378.89, 119.46, 386, 119.46)
s.glabel("SPKRS", 386, 119.46, 0)
s.wire(378.89, 124.54, 386, 124.54)
s.glabel("GND", 386, 124.54, 0)

# ============================ TREMOLO OSCILLATOR =====================
s.text("Tremolo — a phase-shift oscillator on V3A with Speed wired as a rheostat. Its DC point alone is excluded from netlist.cir: a running oscillator has no static operating point (notes.md).",
       24, 182, 1.5)
t3a = s.triode("V3A", "12AX7", 150, 205)
PT_ = 193                                    # the oscillator's plate line
s.wire(150, t3a["p"][1], 150, PT_)
s.junction(150, PT_)
l, r = s.series_h("C", "CTO1", ".03u", 120, PT_)
s.wire(r, PT_, 150, PT_)
s.wire(l, PT_, 88, PT_)
s.wire(88, PT_, 88, 205)                     # node A — the ladder's first node
s.junction(88, 205)
# plate load, and the output take-off beyond it
s.wire(150, PT_, 180, PT_)
s.junction(180, PT_)
s.sym("R", "RTO1", "270k", 180, PT_ + 3.81)
s.wire(180, PT_ + 7.62, 180, 202)
s.glabel("B1", 180, 202, 270)
# the phase-shift ladder, drawn left to right into the grid
l, r = s.series_h("C", "CTO2", ".02u", 98, 205)
s.wire(88, 205, l, 205)
s.wire(r, 205, 108, 205)
s.junction(108, 205)
s.sym("R", "RTOR1", "1M", 108, 208.81)
s.wire(108, 212.62, 108, 224)
l, r = s.series_h("C", "CTO3", ".01u", 118, 205)
s.wire(108, 205, l, 205)
s.wire(r, 205, 128, 205)
s.junction(128, 205)
s.sym("R", "RTOR2", "1.5M", 128, 208.81)
s.wire(128, 212.62, 128, 224)
l, r = s.series_h("R", "RTOG", "2.2k", 136, 205)
s.wire(128, 205, l, 205)
s.wire(r, 205, t3a["g"][0], 205)
# Speed: a 100k end resistor from the ladder's first node into a 500k rheostat
s.sym("R", "RSPD", "100k", 88, 208.81)
s.sym("POT", "VR4", "500k-A", 88, 216.43, lx=-11.4, ly=2.4)
s.wire(93.08, 216.43, 96, 216.43)
s.wire(96, 216.43, 96, 224)
s.wire(88, 220.24, 88, 223)
s.text("Speed", 74, 214, 1.3)
# cathode, and the ladder's common return
s.wire(150, t3a["k"][1], 150, 216)
s.sym("R", "RTOK", "1k", 150, 219.81)
s.wire(150, 223.62, 150, 224)
s.wire(96, 224, 158, 224)
s.junction(108, 224)
s.junction(128, 224)
s.junction(150, 224)
s.glabel("GND", 158, 224, 0)
# oscillator output -> 0.01 -> 1M -> tremolo switch -> the footswitch jack
s.wire(180, PT_, 190, PT_)
s.wire(190, PT_, 190, 232)
l, r = s.series_h("C", "CTOUT", ".01u", 200, 232)
s.wire(190, 232, l, 232)
l2, r2 = s.series_h("R", "RTOUT", "1M", 216, 232)
s.wire(r, 232, l2, 232)
a, b = s.switch("SW1", "SPST", 232, 232)
s.wire(r2, 232, a, 232)
s.wire(b, 232, 244, 232)
s.glabel("FT SW", 244, 232, 0)
s.text("Footswitch jack (normally closed) — annotation layer", 190, 240, 1.2)

# ============================ INTENSITY + FOLLOWER ===================
s.text("The tremolo is not a gate in the signal path: V3B's anode goes straight to the rail with NO load resistor and its cathode lands directly on channel 2's cathode node (C),",
       24, 244, 1.5)
s.text("so the two tubes share that one 1.5 kΩ resistor and the follower's current swings channel 2's bias at oscillator rate.",
       24, 248, 1.3)
YF = 258
s.glabel("FT SW", 20, YF, 180)
l, r = s.series_h("R", "RTI1", "1M", 30, YF)
s.wire(20, YF, l, YF)
s.wire(r, YF, 40, YF)
s.junction(40, YF)
s.sym("C", "CTI1", ".05u", 40, YF + 3.81)
s.gnd(40, YF + 7.62)
l, r = s.series_h("R", "RTI2", "1.5M", 50, YF)
s.wire(40, YF, l, YF)
s.wire(r, YF, 62, YF)
s.junction(62, YF)
s.sym("R", "RTI", "270k", 62, YF + 3.81)
s.gnd(62, YF + 7.62)
s.junction(62, YF + 7.62)
s.sym("C", "CTI2", ".05u", 72, YF + 3.81)
s.wire(62, YF, 72, YF)
s.wire(62, YF + 7.62, 72, YF + 7.62)
s.junction(72, YF)
l, r = s.series_h("R", "RGS2", "2.2k", 82, YF)
s.wire(72, YF, l, YF)
t3b = s.triode("V3B", "12AX7", 100, YF)
s.wire(r, YF, t3b["g"][0], YF)
s.wire(100, t3b["p"][1], 100, YF - 16)
s.glabel("B1", 100, YF - 16, 90)
s.wire(100, t3b["k"][1], 100, YF + 12)
s.glabel("C", 100, YF + 12, 270)

# ============================ POWER SUPPLY ===========================
s.note('Power supply — E-3693A mains transformer, 5Y3-GT full-wave rectifier, three cans and two droppers: no choke and no standby.')
pt = s.pt("T1", "E-3693A", 300, 232, lx=-6.35, ly=-12.5)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 5, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 5, pt["ht_ct"][1])
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 5, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 5, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 5, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 5, pt["ht_b"][1], 0)
s.glabel("HT_A", 340, 208, 90)
s.wire(340, 208, 340, 214.76)
s.diode_tube("V6A", "5Y3GT", 340, 222.38, lx=-13.0)
s.glabel("HT_B", 356, 208, 90)
s.wire(356, 208, 356, 214.76)
s.diode_tube("V6B", "5Y3GT", 356, 222.38, lx=6.2)
s.wire(340, 230, 340, 240)
s.wire(356, 230, 356, 240)
s.wire(340, 240, 356, 240)
s.junction(348, 240)
s.wire(348, 240, 348, 250)
# rail chain, right to left: BP1 -1k/1W-> BP2 -15k-> B1
s.junction(348, 250)
s.sym("C", "CF1", "20u", 348, 253.81)
s.gnd(348, 257.62)
s.wire(348, 250, 360, 250)
s.glabel("BP1", 360, 250, 0)
l, r = s.series_h("R", "RD1", "1k 1W", 334, 250)
s.wire(348, 250, r, 250)
s.wire(l, 250, 322, 250)
s.junction(322, 250)
s.sym("C", "CF2", "10u", 322, 253.81)
s.gnd(322, 257.62)
s.wire(322, 244, 322, 250)
s.glabel("BP2", 322, 244, 90)
l, r = s.series_h("R", "RD2", "15k", 308, 250)
s.wire(322, 250, r, 250)
s.wire(l, 250, 296, 250)
s.junction(296, 250)
s.sym("C", "CF3", "10u", 296, 253.81)
s.gnd(296, 257.62)
s.wire(288, 250, 296, 250)
s.glabel("B1", 288, 250, 180)

s.write(OUT)
print(f"wrote {OUT}")
