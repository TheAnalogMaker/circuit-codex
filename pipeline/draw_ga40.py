#!/usr/bin/env python3
"""Generate amps/ga40/schematic.kicad_sch from the stage-template library.

Values per the Gibson factory drawing whose title block reads "GA-40" and whose
lower left carries the "Les Paul" signature — see amps/ga40/meta.yaml. The sheet
reads: channel 1's 5879 pentode and its volume at the top left; the paraphase
phase inverter and the amplifier's single tone control in the middle; the
cathode-biased 6V6GT pair and the output transformer on the right; and the
power supply along the bottom.

Redrawn from circuit facts — never a trace of a factory drawing.

RAILS. The drawing's own VOLTAGE TABLE prints three E(B+) figures and this sheet
letters its rails by them: BP310 is the post-choke node that is also the
output-transformer centre tap and both 6V6GT screens; BP280 the inverter rail,
one 10 kΩ dropper below it; BP265 the channel-preamp rail, another 10 kΩ below
that.

WHAT IS NOT DRAWN, and why. Channel 2's 5879 and the 6SQ7 tremolo oscillator are
lettered as bottles and left undrawn: channel 2's screen is fed through the
tremolo's Depth network, and neither that network nor the channel-2 screen
dropper resolves on the only published drawing of this revision. Guessing the
resistor is exactly what this corpus does not do — what IS legible of both is
written out in amps/ga40/notes.md. The bottles stay on the sheet so the drawing
still accounts for every valve in the amplifier.

Heaters, the 5 V and 6.3 V windings, the pilot lamp, the jacks and the mains side
beyond the transformer are the annotation layer — see bom.yaml and layout.yaml.

The drawing letters NO reference designators, on the bottles or the passives, so
the designators here are this corpus's own (functional: RL plate load, RS screen
dropper, CK cathode bypass). See bom.yaml.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "ga40" / "schematic.kicad_sch"
s = Sch()

XFMR = "Gibson (no number printed)"

# ============================ NOTES BAND =============================
s.note("Rails, lettered from the factory chart's own E(B+) column: BP310 is the "
       "post-choke node — the output-transformer centre tap and both 6V6GT "
       "screens sit on it, and this circuit has no screen resistors at all; "
       "BP280 is the inverter rail one 10 kΩ dropper below it; BP265 the "
       "channel-preamp rail one more below that. Because those droppers also "
       "carry channel 2 and the tremolo, netlist.cir drives all three rails at "
       "the printed figures rather than deriving a chain missing half its load.")
s.note("Channel 2's 5879 and the 6SQ7 tremolo oscillator are lettered as bottles "
       "and left undrawn. Channel 2's screen is fed through the tremolo's Depth "
       "network — modulating that screen is how this amplifier makes tremolo — "
       "and neither the network nor the channel-2 screen dropper resolves on the "
       "only published drawing of this revision. The chart says the same thing "
       "loudly: +32 V on that screen against +95 V on channel 1's, off the same "
       "+265 V rail. What is legible of both is written out in notes.md.")
s.note("A published restoration records the supply-can complement as "
       "20/10/10/10 µF at 450 WVDC. Three of the four are lettered here; the "
       "fourth most likely sits on the +280 V inverter rail, where this reading "
       "places no can. The gap is left visible rather than filled.")
s.note("Heaters, the transformer's 5 V and 6.3 V windings, the pilot lamp, the "
       "input and speaker jacks and the mains side beyond the transformer "
       "(3 A fuse, on/off switch, and the 0.02 µF capacitor the polarity switch "
       "grounds onto one line leg or the other) are omitted here — see bom.yaml "
       "and layout.yaml. Do not build that mains side as the factory sheet draws "
       "it; it predates grounded three-wire practice.")
s.note("The factory drawing letters no reference designators — not on the "
       "bottles, not on the passives — so the designators on this sheet are this "
       "corpus's own, functional ones: RL a plate load, RS a screen dropper, CK a "
       "cathode bypass, RD a rail dropper.")

# ============================ CHANNEL 1 ==============================
s.caption("Channel 1 — a 5879 pentode on a 100 kΩ load with its screen fed "
          "through 750 kΩ, both off the +265 V rail", 14, 20, 1.6)
s.glabel("CH1 IN 1", 16, 46, 180)
s.glabel("CH1 IN 2", 16, 58, 180)
s.wire(16, 46, 34, 46)
s.wire(16, 58, 34, 58)
s.wire(34, 46, 34, 58)
s.junction(34, 46)
s.junction(34, 58)
# Both jacks land on ONE node behind a single 1 MΩ leak, and each reaches the
# grid through its own 51 kΩ — the arrangement the drawing letters.
s.sym("R", "RG1", "1M", 34, 61.81)
s.gnd(34, 65.62)
l, r = s.series_h("R", "RIN1", "51k", 48, 46)
s.wire(34, 46, l, 46)
s.wire(r, 46, 62, 46)
l, r = s.series_h("R", "RIN2", "51k", 48, 58)
s.wire(34, 58, l, 58)
s.wire(r, 58, 62, 58)
s.wire(62, 46, 62, 58)
s.junction(62, 46)
s.junction(62, 58)
s.junction(62, 52)

v1 = s.pentode("V1", "5879", 86, 52)
s.wire(62, 52, v1["g1"][0], 52)
# plate: 100 kΩ up to the preamp rail, with the tee the coupler leaves from
TEE1 = 40.0
s.wire(86, v1["p"][1], 86, TEE1)
s.junction(86, TEE1)
s.sym("R", "RL1", "100k", 86, TEE1 - 3.81)
s.wire(86, TEE1 - 7.62, 86, 29)
s.glabel("BP265", 86, 29, 90)
# screen: 750 kΩ dropper off the same rail, bypassed to ground by 0.05 µF
SGY = v1["g2"][1]
l, r = s.series_h("R", "RS1", "750k", 112, SGY)
s.wire(v1["g2"][0], SGY, l, SGY)
s.wire(r, SGY, 124, SGY)
s.glabel("BP265", 124, SGY, 0)
s.junction(100, SGY)
s.sym("C", "CS1", ".05u", 100, SGY + 3.81)
s.gnd(100, SGY + 7.62)
# cathode: 3.3 kΩ with a 20 µF can across it
s.wire(86, v1["k"][1], 86, 66)
s.shunt_rc("RK1", "3.3k", "CK1", "20u", 86, 66)

# ---- volume and the mixing resistor into the inverter ---------------
s.caption("Volume · mixer — the coupler drives the WIPER and the signal leaves the "
          "track's top through 470 kΩ, where channel 2's own 100 kΩ leg joins", 110, 20, 1.4)
l, r = s.series_h("C", "CV1", ".01u", 112, TEE1)
s.wire(86, TEE1, l, TEE1)
s.wire(r, TEE1, 124, TEE1)
# The coupler lands on the WIPER, not on a track end — read off the drawing, and
# the same way channel 2's own volume is wired. The track's top end is the output.
s.wire(124, TEE1, 124, 56)
s.wire(124, 56, 139.08, 56)
s.sym("POT", "VR1", "1M", 134, 47.81, lx=-11.4, ly=2.4)
s.wire(139.08, 56, 139.08, 47.81)
s.gnd(134, 51.62)
s.wire(134, 44, 134, 34)
s.wire(134, 34, 158, 34)
s.wire(158, 34, 158, 80)
l, r = s.series_h("R", "RM1", "470k", 176, 80)
s.wire(158, 80, l, 80)

# ============================ PARAPHASE INVERTER =====================
s.caption("Paraphase phase inverter — both halves on ONE shared 1 kΩ cathode "
          "resistor; the 470 kΩ / 7.5 kΩ divider hanging off the FIRST output "
          "grid is what drives the second half", 176, 34, 1.5)
s.text("7.5 / (470 + 7.5) is 1/63.7 — the gain a 12AX7 gives back on a 220 kΩ load", 176, 40, 1.3)

v4a = s.triode("V4A", "12AX7", 196, 80)
s.wire(r, 80, v4a["g"][0], 80)
TEEA = 68.9
s.wire(196, v4a["p"][1], 196, TEEA)
s.junction(196, TEEA)
s.sym("R", "RL4A", "220k", 196, TEEA - 3.81)
s.wire(196, TEEA - 7.62, 196, 58)
s.glabel("BP280", 196, 58, 90)

v4b = s.triode("V4B", "12AX7", 196, 136)
TEEB = 124.9
s.wire(196, v4b["p"][1], 196, TEEB)
s.junction(196, TEEB)
s.sym("R", "RL4B", "220k", 196, TEEB - 3.81)
s.wire(196, TEEB - 7.62, 196, 114)
s.glabel("BP280", 196, 114, 90)

# the one cathode resistor the pair of halves shares
s.wire(196, v4a["k"][1], 196, 94)
s.wire(196, 94, 206, 94)
s.wire(206, 94, 206, 152)
s.wire(196, v4b["k"][1], 196, 152)
s.wire(196, 152, 206, 152)
s.junction(206, 152)
s.shunt_rc("RK4", "1k", "CK4", "20u", 206, 152)

# ---- the amplifier's only tone control, on the driver anode ---------
s.wire(196, TEEA, 268.19, TEEA)
s.junction(216, TEEA)
s.wire(216, TEEA, 216, 96)
s.sym("C", "CT1", ".005u", 216, 99.81)
s.sym("POT", "VR3", "1M", 216, 107.43)
s.wire(221.08, 107.43, 228, 107.43)
s.glabel("GND", 228, 107.43, 0)
s.text("Tone — a rheostat: wiper to ground, the far lug left free. It is the whole", 224, 118, 1.2)
s.text("tone circuit, and it sits between the inverter and the output tubes.", 224, 122, 1.2)

# ============================ OUTPUT COUPLERS + 6V6GT ================
s.caption("6V6GT pair — ONE shared 200 Ω cathode resistor is the entire bias "
          "arrangement, there is no bias supply anywhere, and the screens sit "
          "straight on the supply node with no screen resistors", 268, 22, 1.5)
l, r = s.series_h("C", "CC1", ".02u", 272, TEEA)
s.wire(r, TEEA, 298.38, TEEA)
v5 = s.pentode("V5", "6V6GT", 306, TEEA)

# the divider: V5's grid -> 470 kΩ -> the tap that drives V4B -> 7.5 kΩ -> ground
s.junction(284, TEEA)
s.wire(284, TEEA, 284, 96.19)
s.sym("R", "RPA", "470k", 284, 100)
s.wire(284, 103.81, 284, 150)
s.wire(284, 150, 260, 150)
s.wire(260, 150, 260, 176)
s.junction(260, 176)
s.sym("R", "RPB", "7.5k", 260, 179.81)
s.gnd(260, 183.62)
s.wire(260, 176, 176, 176)
s.wire(176, 176, 176, 136)
s.wire(176, 136, v4b["g"][0], 136)

# V4B's anode -> 0.02 µF -> the second output grid, which has its own leak
s.wire(196, TEEB, 228, TEEB)
s.wire(228, TEEB, 228, 232)
l, r = s.series_h("C", "CC2", ".02u", 252, 232)
s.wire(228, 232, l, 232)
s.wire(r, 232, 272, 232)
s.wire(272, 232, 272, 200)
s.wire(272, 200, 298.38, 200)
v6 = s.pentode("V6", "6V6GT", 306, 200)
s.junction(288, 200)
s.sym("R", "RGL6", "470k", 288, 203.81)
s.gnd(288, 207.62)

# screens straight on the post-choke node; cathodes onto the shared resistor
s.wire(v5["g2"][0], v5["g2"][1], 326, v5["g2"][1])
s.glabel("BP310", 326, v5["g2"][1], 0)
s.wire(v6["g2"][0], v6["g2"][1], 326, v6["g2"][1])
s.glabel("BP310", 326, v6["g2"][1], 0)
s.wire(306, v5["k"][1], 306, 84)
s.glabel("KOUT", 306, 84, 270)
s.wire(306, v6["k"][1], 306, 215)
s.glabel("KOUT", 306, 215, 270)
s.glabel("KOUT", 330, 240, 180)
s.wire(330, 240, 344, 240)
s.shunt_rc("RKO", "200", "CKO", "20u", 344, 240)

# ---- output transformer --------------------------------------------
t2 = s.ot_pp("T2", XFMR, 368, 140)
s.wire(306, v5["p"][1], 306, 50)
s.wire(306, 50, 352, 50)
s.wire(352, 50, 352, t2["pri_a"][1])
s.wire(352, t2["pri_a"][1], t2["pri_a"][0], t2["pri_a"][1])
s.wire(306, v6["p"][1], 306, 182)
s.wire(306, 182, 340, 182)
s.wire(340, 182, 340, t2["pri_b"][1])
s.wire(340, t2["pri_b"][1], t2["pri_b"][0], t2["pri_b"][1])
s.wire(t2["ct"][0], t2["ct"][1], 332, t2["ct"][1])
s.glabel("BP310", 332, t2["ct"][1], 180)
s.wire(t2["sec_h"][0], t2["sec_h"][1], 386, t2["sec_h"][1])
s.glabel("SPKR", 386, t2["sec_h"][1], 0)
s.wire(t2["sec_c"][0], t2["sec_c"][1], 386, t2["sec_c"][1])
s.glabel("GND", 386, t2["sec_c"][1], 0)

# ============================ READ, NOT DRAWN ========================
s.caption("Channel 2 and the tremolo — read on the drawing, NOT drawn", 20, 96, 1.6)
s.pentode("V2", "5879", 52, 116)
s.triode("V3", "6SQ7", 104, 116)
s.text("Channel 2 — the tremolo-modulated channel:", 24, 132, 1.3)
s.text("its screen is what the tremolo swings.", 24, 136, 1.3)
s.text("6SQ7 phase-shift oscillator, with the", 92, 132, 1.3)
s.text("Frequency and Depth controls on it.", 92, 136, 1.3)

# ============================ POWER SUPPLY ===========================
s.caption("Power supply — 5Y3GT into a 20 µF reservoir, a 3 H choke, then two "
          "10 kΩ droppers. No standby.", 30, 150, 1.5)
pt = s.pt("T1", XFMR, 48, 170)
s.wire(pt["pri1"][0], pt["pri1"][1], 34, pt["pri1"][1])
s.glabel("MAINS", 34, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], 34, pt["pri2"][1])
s.glabel("MAINS", 34, pt["pri2"][1], 180)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], 62, pt["ht_ct"][1])
s.gnd(62, pt["ht_ct"][1])
s.wire(pt["ht_a"][0], pt["ht_a"][1], 74, pt["ht_a"][1])
s.glabel("HT_A", 74, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], 74, pt["ht_b"][1])
s.glabel("HT_B", 74, pt["ht_b"][1], 0)

s.glabel("HT_A", 140, 162, 90)
s.wire(140, 162, 140, 168.76)
s.diode_tube("V7A", "5Y3GT", 140, 176.38, lx=-13.0)
s.glabel("HT_B", 156, 162, 90)
s.wire(156, 162, 156, 168.76)
s.diode_tube("V7B", "5Y3GT", 156, 176.38, lx=6.2)
s.wire(140, 184, 140, 192)
s.wire(156, 184, 156, 192)
s.wire(140, 192, 156, 192)
s.junction(148, 192)
s.wire(148, 192, 148, 200)
s.junction(148, 200)
s.sym("C", "CF1", "20u", 148, 203.81)
s.gnd(148, 207.62)
a, b = s.choke("L1", "3H", 128, 200)
s.wire(148, 200, b, 200)
s.wire(a, 200, 108, 200)
s.junction(108, 200)
s.sym("C", "CF2", "10u", 108, 203.81)
s.gnd(108, 207.62)
s.wire(108, 200, 108, 194)
s.glabel("BP310", 108, 194, 90)
l, r = s.series_h("R", "RD1", "10k", 92, 200)
s.wire(108, 200, r, 200)
s.wire(l, 200, 80, 200)
s.junction(80, 200)
s.wire(80, 200, 80, 194)
s.glabel("BP280", 80, 194, 90)
l, r = s.series_h("R", "RD2", "10k", 64, 200)
s.wire(80, 200, r, 200)
s.wire(l, 200, 52, 200)
s.junction(52, 200)
s.sym("C", "CF3", "10u", 52, 203.81)
s.gnd(52, 207.62)
s.wire(52, 200, 52, 194)
s.glabel("BP265", 52, 194, 90)

s.write(OUT)
print(f"wrote {OUT}")
