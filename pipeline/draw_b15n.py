#!/usr/bin/env python3
"""Generate amps/b15n/schematic.kicad_sch from the stage-template library.

Values per the Ampeg factory drawing whose title block reads "B-15-N / U.S.
PATENT 3183305 / TUBES / 6SL7 - 6SL7 - 6SL7 - 6L6GC - 6L6GC - 5AR4 / -472-",
PART NO. 591722, revision C of 1/22/74 — see amps/b15n/meta.yaml. The same
circuit and the same annotations appear on the service-manual sheet headed
"MODEL B15N SCHEMATIC DIAGRAM (REV. C)".

The sheet reads: the two identical channels stacked at the left, each a pair of
6SL7 stages with an ULTRA LO / ULTRA HI pair of switches between them and its
own printed Bass/Treble board after the second stage; the two 270 kOhm mixing
resistors meeting at the driver grid in the middle; the third 6SL7 as driver and
self-balancing paraphase at the centre; the 6L6GC pair and the OT-214 at the
right; and the power supply along the bottom.

Redrawn from circuit facts — never a trace of a factory drawing.

RAILS. BP1 = the 5AR4 cathode / C17 reservoir, which is also the OT-214 primary
centre tap and therefore the 6L6GC plate node (450 V on the drawing); BP2 = the
6L6GC screen node, one 1 kOhm 10 W dropper below it (445 V); BP3 = the preamp
rail both channels share and BP4 = the driver rail, each behind its own 22 kOhm
1 W dropper off BP2 — the two never rejoin. -50V is the negative bias line.

HOW THE SHEET IS READ. This draughtsman marks "crosses, does not connect" with a
small S-jog that reads as a junction at working magnification. Read as junctions
the supply is unsolvable and half the tone stack is shorted; read as hop-overs
the sheet resolves. Every crossing in this redraw is a plain KiCad crossing (no
junction dot) and every connection carries one.

The heater chain (6.3 V green pair, VR7 100 Ohm hum balance, sockets V1..V5), the
mains side beyond the transformer primary (POWER SW6, POLAR. SW7, the 3 A and
6 A fuses, the switched AC outlet, C18/CM2) and the panel pilot lamp — which
this drawing puts straight across the mains primary, not on the heater chain —
are omitted here (annotation layer). See netlist.cir, bom.yaml and layout.yaml.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "b15n" / "schematic.kicad_sch"
s = Sch()

MIX = 292          # the channel mixing bus / driver grid column


def channel(Y, tag, R):
    """One complete channel: two 6SL7 stages, the ULTRA network and volume
    between them, and the printed Bass/Treble board after the second.

    `Y` is the first stage's grid line; every other level is measured from it.
    `R` names the channel's designators, which are the drawing's own."""
    TEE1 = Y - 14           # first-stage plate line, and the ULTRA network's
    TEE2 = Y - 24           # second-stage plate line = the tone board's input
    GY = Y - 10.19          # second-stage grid line = the volume wiper
    BR = Y - 26             # the ULTRA HI bright-cap lane, above the volume
    TL = Y - 8              # tone-board pot top lugs
    W = Y - 4.19            # tone-board pot wipers
    BL = Y - 0.38           # tone-board pot bottom lugs
    OUTL = Y + 16           # the mixing resistor's lane into the driver grid

    # ---- input jacks: BRIGHT through 100k (bridged 0.005) and NORMAL
    #      through 47k, both onto ONE grid behind a 5.6 MOhm leak ----------
    jb = s.jack(R["Jb"], "1/4 in", 8, Y - 4.46, mirror=True, lx=1.6, ly=-11.6)
    jn = s.jack(R["Jn"], "1/4 in", 8, Y + 9.54, mirror=True, lx=1.6, ly=7.2)
    s.text("BRIGHT", -6, Y - 4, 1.3)
    s.text("NORMAL", -6, Y + 10, 1.3)
    s.wire(jb["sleeve"][0], jb["sleeve"][1], 18, Y - 1.92)
    s.gnd(18, Y - 1.92, 0)
    s.wire(jn["sleeve"][0], jn["sleeve"][1], 18, Y + 12.08)
    s.gnd(18, Y + 12.08, 0)
    l, r = s.series_h("R", R["Rb"], "100k", 30, Y - 7)
    s.wire(jb["tip"][0], Y - 7, l, Y - 7)
    s.wire(r, Y - 7, 46, Y - 7)
    s.junction(22, Y - 7)
    s.junction(38, Y - 7)
    lc, rc = s.series_h("C", R["Cb"], ".005u", 30, Y - 17)
    s.wire(22, Y - 7, 22, Y - 17)
    s.wire(22, Y - 17, lc, Y - 17)
    s.wire(rc, Y - 17, 38, Y - 17)
    s.wire(38, Y - 17, 38, Y - 7)
    l, r = s.series_h("R", R["Rn"], "47k", 30, Y + 7)
    s.wire(jn["tip"][0], Y + 7, l, Y + 7)
    s.wire(r, Y + 7, 46, Y + 7)
    s.wire(46, Y - 7, 46, Y + 7)
    s.junction(46, Y - 7)
    s.junction(46, Y + 7)
    s.junction(46, Y)
    s.sym("R", R["Rg"], "5.6M", 46, Y + 10.81, lx=2.4, ly=-0.8)
    s.gnd(46, Y + 14.62)

    # ---- first stage: 470k over an UNBYPASSED 5.6k --------------------------
    ta = s.triode(R["Va"], "6SL7", 62, Y)
    s.wire(46, Y, ta["g"][0], Y)
    s.wire(62, ta["p"][1], 62, TEE1)
    s.junction(62, TEE1)
    s.sym("R", R["Rla"], "470k", 62, TEE1 - 3.81)
    s.wire(62, TEE1 - 7.62, 62, TEE1 - 10.16)
    s.glabel("BP3", 62, TEE1 - 10.16, 90)
    s.wire(62, ta["k"][1], 62, Y + 11)
    s.sym("R", R["Rka"], "5.6k", 62, Y + 14.81)
    s.gnd(62, Y + 18.62)

    # ---- ULTRA LO: 0.02 in series with 39k down to 1M, which SW shorts out --
    l, r = s.series_h("C", R["Cc1"], ".1u", 78, TEE1)
    s.wire(62, TEE1, l, TEE1)
    s.wire(r, TEE1, 94, TEE1)
    s.junction(94, TEE1)
    s.sym("C", R["Cul"], ".02u", 94, TEE1 + 3.81, lx=2.4, ly=-0.8)
    s.sym("R", R["Rul"], "39k", 94, TEE1 + 11.43)
    s.junction(94, TEE1 + 15.24)
    s.sym("R", R["Rus"], "1M", 94, TEE1 + 19.05)
    s.gnd(94, TEE1 + 22.86)
    s.wire(84, TEE1 + 15.24, 94, TEE1 + 15.24)
    s.sym("SWITCH", R["Swl"], "SPST", 84, TEE1 + 20.32, rot=90, lx=2.8, ly=-1.2)
    s.wire(84, TEE1 + 25.4, 84, TEE1 + 28)
    s.gnd(84, TEE1 + 28)

    # ---- volume, with the ULTRA HI 500 pF switched top-to-wiper -------------
    l, r = s.series_h("C", R["Cv"], ".01u", 110, TEE1)
    s.wire(94, TEE1, l, TEE1)
    s.wire(r, TEE1, 126, TEE1)
    s.junction(126, TEE1)
    s.sym("POT", R["Vol"], "1M-L", 126, TEE1 + 3.81, lx=-11.6, ly=2.6)
    s.gnd(126, TEE1 + 7.62)
    s.wire(126, TEE1, 126, BR)
    l, r = s.series_h("C", R["Cbr"], "500p", 140, BR)
    s.wire(126, BR, l, BR)
    s.sym("SWITCH", R["Swh"], "SPST", 158, BR, lx=-3.4, ly=-6.2)
    s.wire(r, BR, 152.92, BR)
    s.wire(163.08, BR, 168, BR)
    s.wire(168, BR, 168, GY)
    s.junction(168, GY)

    # ---- second stage: 220k over an UNBYPASSED 2.2k ------------------------
    tb = s.triode(R["Vb"], "6SL7", 182, GY)
    s.wire(131.08, GY, tb["g"][0], GY)
    s.wire(182, tb["p"][1], 182, TEE2)
    s.junction(182, TEE2)
    s.sym("R", R["Rlb"], "220k", 182, TEE2 - 3.81)
    s.wire(182, TEE2 - 7.62, 182, TEE2 - 10.16)
    s.glabel("BP3", 182, TEE2 - 10.16, 90)
    s.wire(182, tb["k"][1], 182, Y + 1)
    s.sym("R", R["Rkb"], "2.2k", 182, Y + 4.81)
    s.gnd(182, Y + 8.62)

    # ---- the printed tone board (P.E.C.) ------------------------------------
    l, r = s.series_h("C", R["Cc2"], ".1u", 198, TEE2)
    s.wire(182, TEE2, l, TEE2)
    s.wire(r, TEE2, 214, TEE2)
    s.junction(214, TEE2)
    s.wire(214, TEE2, 262, TEE2)          # the board's input line
    # bass leg
    s.sym("R", R["Rt1"], "220k", 214, TEE2 + 3.81, lx=2.4, ly=-0.8)
    s.wire(214, TEE2 + 7.62, 214, TL)
    s.junction(214, TL)
    s.sym("POT", R["Bas"], "1M-A", 214, W, lx=-12.0, ly=6.6)
    s.junction(214, BL)
    l, r = s.series_h("C", R["Ct1"], ".001u", 230, TL)
    s.wire(214, TL, l, TL)
    s.wire(r, TL, 242, TL)
    l, r = s.series_h("C", R["Ct2"], ".01u", 230, BL)
    s.wire(214, BL, l, BL)
    s.wire(r, BL, 242, BL)
    s.wire(242, TL, 242, BL)
    s.junction(242, W)
    s.wire(219.08, W, 242, W)
    s.wire(214, BL, 214, Y + 3)
    s.sym("R", R["Rt2"], "22k", 214, Y + 6.81)
    s.gnd(214, Y + 10.62)
    # treble leg — the pot is mirrored so its wiper faces the 120k link
    s.sym("C", R["Ct3"], "470p", 262, TEE2 + 3.81, lx=2.4, ly=-0.8)
    s.wire(262, TEE2 + 7.62, 262, TL)
    s.sym("POT", R["Tre"], "1M-A", 262, W, mirror="y", lx=4.6, ly=6.6)
    l, r = s.series_h("R", R["Rlk"], "120k", 250, W)
    s.wire(242, W, l, W)
    s.wire(r, W, 256.92, W)
    s.junction(256.92, W)
    s.wire(262, BL, 262, Y + 3)
    s.sym("C", R["Ct4"], ".0047u", 262, Y + 6.81)
    s.gnd(262, Y + 10.62)
    # the board output leaves through the 270k mixing resistor
    s.wire(256.92, W, 256.92, OUTL)
    l, r = s.series_h("R", R["Rmx"], "270k", 272, OUTL)
    s.wire(256.92, OUTL, l, OUTL)
    s.wire(r, OUTL, MIX, OUTL)


CH1 = dict(Jb="J1", Jn="J2", Rb="R1", Cb="C1", Rn="R2", Rg="R5", Va="V1A", Rla="R7", Rka="R8",
           Cc1="C3", Cul="C4", Rul="R9", Rus="R10", Swl="SW2", Cv="C19",
           Vol="VR1", Cbr="C9", Swh="SW1", Vb="V1B", Rlb="R15", Rkb="R16",
           Cc2="C10", Rt1="RTA1", Bas="VR2", Ct1="CTA1", Ct2="CTA2",
           Rt2="RTA2", Ct3="CTA3", Tre="VR3", Rlk="R17", Ct4="CTA4",
           Rmx="R18")
CH2 = dict(Jb="J3", Jn="J4", Rb="R3", Cb="C2", Rn="R4", Rg="R6", Va="V2A", Rla="R11", Rka="R12",
           Cc1="C5", Cul="C6", Rul="R13", Rus="R14", Swl="SW4", Cv="C20",
           Vol="VR4", Cbr="C7", Swh="SW3", Vb="V2B", Rlb="R19", Rkb="R20",
           Cc2="C8", Rt1="RTB1", Bas="VR5", Ct1="CTB1", Ct2="CTB2",
           Rt2="RTB2", Ct3="CTB3", Tre="VR6", Rlk="R21", Ct4="CTB4",
           Rmx="R22")

Y1, Y2 = 62, 132

# ============================ NOTES ==================================
s.note('Rails: BP1 = the 5AR4 cathode and C17 reservoir, which is also the OT-214 primary centre tap and therefore the 6L6GC plate node (450 V on the drawing) — BP2 = the screen node, one 1 kOhm 10 W dropper below it (445 V) — BP3 = the preamp rail both channels share and BP4 = the driver rail, each behind its own 22 kOhm 1 W dropper off BP2. The two never rejoin.')
s.note('The 6.3 V heater chain (green pair, VR7 100 Ohm hum balance, sockets V1..V5 on pins 7/8 and 7/2), the mains side beyond the transformer primary (POWER SW6, POLAR. SW7, the 3 A and 6 A fuses, the switched AC outlet, C18 and CM2) and the panel pilot lamp are omitted here — see bom.yaml and the board layout. The drawing puts that pilot straight across the mains primary, not on the heater chain.')
s.note('Two printed voltages on the driver cannot be true and are carried as disputed rather than fitted: 3 V across R25 220 Ohm is 13.6 mA, six times a 6SL7 unit\'s Class-A point and 3.2 W in a 1 W plate, and 2.2 V across R24 1 kOhm needs a 489 V rail behind the drawn 120 kOhm in an amplifier whose highest node is 450 V. See notes.md.')
s.note('The OT-214 secondary is tapped — GRN., YEL. and BLK. on the drawing — and the EXT. SPKR. jack J6 normals the internal 8 Ohm speaker. Only the green and black ends are drawn here, with R41 250 Ohm 10 W across them; the yellow tap, J6 and the speaker are the annotation layer.')
s.note('Every crossing drawn here is a crossing: the factory sheet marks "crosses, does not connect" with a small S-jog, and this redraw uses the plain KiCad convention instead — a junction dot means a joint and nothing else does.')

# ============================ CHANNELS ===============================
s.caption('Channel 1 — 6SL7 pins 4/5/6 then 1/2/3. No cathode bypass anywhere in either channel: 5.6 kOhm and 2.2 kOhm both left undegenerated.', 12, Y1 - 44, 1.6)
channel(Y1, "CH1", CH1)
s.caption('Channel 2 — component for component identical to channel 1.', 12, Y2 - 44, 1.6)
channel(Y2, "CH2", CH2)

s.caption('ULTRA LO shorts out the 1 MOhm shunt leg; ULTRA HI switches 500 pF across the volume control, top lug to wiper.', 84, Y1 + 26, 1.4)
s.caption('Printed tone board: both bass caps land on the wiper, and the 120 kOhm link between the two wipers IS the board output.', 196, Y1 + 26, 1.4)

# ============================ MIXING BUS =============================
s.note('Both channels sum through 270 kOhm apiece onto the driver grid, which has no grid leak of its own: its DC return runs back out through those two mixing resistors and both tone boards to their 22 kOhm feet. The EXT. AMP. jack J5 taps the same node.')
s.wire(MIX, Y1 + 16, MIX, Y2 + 16)
s.wire(MIX, Y2 + 16, MIX, 176)
s.junction(MIX, Y2 + 16)
s.junction(MIX, 115.46)
s.wire(MIX, 176, 322.38, 176)

# EXT. AMP. jack, tapping the same node
s.jack("J5", "1/4 in", 312, 118, lx=3.2, ly=-8.4)
s.wire(MIX, 115.46, 306.92, 115.46)
s.wire(306.92, 120.54, 306.92, 124)
s.gnd(306.92, 124)

# ============================ DRIVER + PARAPHASE =====================
s.caption('Self-balancing (floating) paraphase — R28 470k and R29 510k are strung ACROSS the two driver anodes and their midpoint drives the second grid through C11. Not a long-tailed pair: the two cathodes are separate and differently loaded.', 296, 44, 1.5)

# V3A — the INVERTED half (pins 4/5/6), fed from the divider midpoint
v3a = s.triode("V3A", "6SL7", 330, 96)
s.wire(296, 96, v3a["g"][0], 96)
s.junction(310, 96)
s.sym("R", "R23", "470k", 310, 99.81, lx=2.4, ly=-0.8)
s.gnd(310, 103.62)
s.wire(330, v3a["p"][1], 330, 82)
s.junction(330, 82)
s.sym("R", "R27", "120k", 330, 78.19)
s.wire(330, 74.38, 330, 71)
s.glabel("BP4", 330, 71, 90)
s.wire(330, v3a["k"][1], 330, 107)
s.sym("R", "R24", "1k", 330, 110.81, lx=-7.4, ly=-0.8)
s.sym("C", "CKD1", "25u 25V", 337.62, 110.81, lx=2.4, ly=-0.8)
s.wire(330, 107, 337.62, 107)
s.wire(330, 114.62, 337.62, 114.62)
s.gnd(330, 114.62)

# V3B — the DRIVER half (pins 1/2/3), grid on the mixing bus
v3b = s.triode("V3B", "6SL7", 330, 176)
s.wire(330, v3b["p"][1], 330, 162)
s.junction(330, 162)
s.sym("R", "R26", "120k", 330, 158.19)
s.wire(330, 154.38, 330, 151)
s.glabel("BP4", 330, 151, 90)
s.wire(330, v3b["k"][1], 330, 187)
s.junction(330, 187)
s.sym("R", "R25", "220", 330, 190.81, lx=-9.0, ly=-0.8)
s.gnd(330, 194.62)

# the divider across the two anodes, and the coupler to the second grid
s.wire(330, 82, 356, 82)
s.junction(356, 82)
s.sym("R", "R28", "470k", 356, 85.81, lx=2.4, ly=-0.8)
s.wire(356, 89.62, 356, 120)
s.junction(356, 120)
s.sym("R", "R29", "510k", 356, 123.81, lx=2.4, ly=-0.8)
s.wire(356, 127.62, 356, 162)
s.wire(356, 162, 330, 162)
s.junction(356, 162)
s.wire(356, 120, 370, 120)
s.wire(370, 120, 370, 60)
l, r = s.series_h("C", "C11", ".022u", 330, 60)
s.wire(370, 60, r, 60)
s.wire(l, 60, 296, 60)
s.wire(296, 60, 296, 96)

# ============================ OUTPUT STAGE ===========================
s.caption('Fixed bias, no cathode resistor and no screen stoppers: both 6L6GC cathodes go straight to ground, both screens hang together on BP2, and each grid returns to the -50 V line through its own 270 kOhm behind a 1 kOhm stopper.', 380, 44, 1.5)

v4 = s.pentode("V4", "6L6GC", 430, 96)
v5 = s.pentode("V5", "6L6GC", 430, 176)

# V3A anode -> C14 -> V4 grid line
s.wire(356, 82, 382, 82)
s.wire(382, 82, 382, 96)
l, r = s.series_h("C", "C14", ".022u", 394, 96)
s.wire(382, 96, l, 96)
s.wire(r, 96, 404, 96)
s.junction(404, 96)
s.sym("R", "R31", "270k", 404, 99.81, lx=2.4, ly=-0.8)
s.wire(404, 103.62, 404, 107)
s.glabel("-50V", 404, 107, 270)
l, r = s.series_h("R", "R32", "1k", 414, 96)
s.wire(404, 96, l, 96)
s.wire(r, 96, v4["g1"][0], 96)

# V3B anode -> C13 -> V5 grid line
s.wire(356, 162, 382, 162)
s.wire(382, 162, 382, 176)
l, r = s.series_h("C", "C13", ".022u", 394, 176)
s.wire(382, 176, l, 176)
s.wire(r, 176, 404, 176)
s.junction(404, 176)
s.sym("R", "R30", "270k", 404, 172.19)
s.wire(404, 168.38, 404, 165)
s.glabel("-50V", 404, 165, 90)
l, r = s.series_h("R", "R33", "1k", 414, 176)
s.wire(404, 176, l, 176)
s.wire(r, 176, v5["g1"][0], 176)

s.wire(v4["g2"][0], v4["g2"][1], 452, v4["g2"][1])
s.glabel("BP2", 452, v4["g2"][1], 0)
s.wire(v5["g2"][0], v5["g2"][1], 452, v5["g2"][1])
s.glabel("BP2", 452, v5["g2"][1], 0)
s.wire(430, v4["k"][1], 430, 107)
s.gnd(430, 107)
s.wire(430, v5["k"][1], 430, 196)
s.gnd(430, 196)

# ---- output transformer, speaker and the global feedback loop -----------
s.sym("OT_PP", "T2", "OT-214", 496, 130, lx=-6.35, ly=-13.6)
s.wire(430, v4["p"][1], 430, 72)
s.wire(430, 72, 470, 72)
s.wire(470, 72, 470, 124.92)
s.wire(470, 124.92, 487.11, 124.92)
s.wire(430, v5["p"][1], 430, 158)
s.wire(430, 158, 462, 158)
s.wire(462, 158, 462, 135.08)
s.wire(462, 135.08, 487.11, 135.08)
s.wire(487.11, 130, 478, 130)
s.glabel("BP1", 478, 130, 180)
s.wire(504.89, 127.46, 552.92, 127.46)
s.junction(546, 127.46)
s.wire(546, 127.46, 546, 118)
s.glabel("SPKR", 546, 118, 90)
s.jack("J6", "1/4 in", 558, 130, lx=3.6, ly=-10.4)
s.wire(552.92, 132.54, 552.92, 138)
s.gnd(552.92, 138)
s.junction(514, 127.46)
s.sym("R", "R41", "250 10W", 514, 131.27, lx=2.4, ly=-0.8)
s.wire(514, 135.08, 514, 139)
s.gnd(514, 139)
s.wire(504.89, 132.54, 504.89, 150)
s.wire(504.89, 150, 526, 150)
s.gnd(526, 150, 0)
s.text("GRN.", 508, 124.4, 1.3)
s.text("BLK.", 508, 154, 1.3)

# global negative feedback: the transformer's green secondary lead back to the
# driver cathode through 10k — it lands on R25, not on an inverter tail.
s.junction(534, 127.46)
s.wire(534, 127.46, 534, 210)
l, r = s.series_h("R", "R40", "10k", 440, 210)
s.wire(534, 210, r, 210)
s.wire(l, 210, 346, 210)
s.wire(346, 210, 346, 187)
s.wire(346, 187, 330, 187)
s.caption('Global negative feedback: 10 kOhm from the output transformer\'s green secondary lead onto the driver cathode over R25 220 Ohm, which is why that 220 Ohm is a feedback shunt leg rather than a bias resistor.', 346, 218, 1.4)

# ============================ POWER SUPPLY ===========================
s.caption('Power supply — PT-108 mains transformer, 5AR4, the STANDBY switch in the HT centre-tap return, one reservoir and a three-section can. No choke.', 300, 236, 1.5)
pt = s.pt("T1", "PT-108", 350, 262, lx=-7.0, ly=-13.4)
s.wire(pt["ht_a"][0], pt["ht_a"][1], 366, pt["ht_a"][1])
s.glabel("HTA", 366, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], 366, pt["ht_b"][1])
s.glabel("HTB", 366, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], 370.92, pt["ht_ct"][1])
s.sym("SWITCH", "SW5", "SPST", 376, 262, lx=-3.6, ly=6.4)
s.wire(381.08, 262, 388, 262)
s.gnd(388, 262, 0)

s.glabel("HTA", 404, 240, 90)
s.wire(404, 240, 404, 246.76)
s.diode_tube("V6A", "5AR4", 404, 254.38, lx=-13.6)
s.glabel("HTB", 420, 240, 90)
s.wire(420, 240, 420, 246.76)
s.diode_tube("V6B", "5AR4", 420, 254.38, lx=6.4)
s.wire(404, 262, 404, 272)
s.wire(420, 262, 420, 272)
s.wire(404, 272, 420, 272)
s.junction(412, 272)
s.wire(412, 272, 412, 280)
s.junction(412, 280)
s.sym("C", "C17", "30u 600V", 412, 283.81, lx=2.4, ly=-0.8)
s.gnd(412, 287.62)
s.wire(412, 280, 430, 280)
s.glabel("BP1", 430, 280, 0)

# BP1 -> 1k 10W -> the screen node -> two 22k droppers that never rejoin
l, r = s.series_h("R", "R39", "1k 10W 5%", 396, 280)
s.wire(412, 280, r, 280)
s.wire(l, 280, 380, 280)
s.junction(380, 280)
s.sym("C", "C16A", "40u 500V", 380, 283.81, lx=2.4, ly=-0.8)
s.gnd(380, 287.62)
s.wire(380, 274, 380, 280)
s.glabel("BP2", 380, 274, 90)
l, r = s.series_h("R", "R37", "22k 1W", 362, 280)
s.wire(380, 280, r, 280)
s.wire(l, 280, 348, 280)
s.junction(348, 280)
s.sym("C", "C16B", "40u 500V", 348, 283.81, lx=2.4, ly=-0.8)
s.gnd(348, 287.62)
s.wire(340, 280, 348, 280)
s.glabel("BP3", 340, 280, 180)
l, r = s.series_h("R", "R38", "22k 1W", 362, 294)
s.wire(380, 280, 380, 294)
s.wire(380, 294, r, 294)
s.junction(380, 294)
s.wire(l, 294, 348, 294)
s.junction(348, 294)
s.sym("C", "C16C", "40u 500V", 348, 297.81, lx=2.4, ly=-0.8)
s.gnd(348, 301.62)
s.wire(340, 294, 348, 294)
s.glabel("BP4", 340, 294, 180)

# ============================ BIAS SUPPLY ============================
s.caption('Negative-bias supply — R36 taps the 5AR4 plate, which swings below ground on every other half cycle, so D1 conducts toward the bias line. R34 and R35 sit either side of it and R42 separates the two 10 uF cans.', 452, 236, 1.4)
s.wire(404, 246.76, 452, 246.76)
s.junction(404, 246.76)
l, r = s.series_h("R", "R36", "100k 2W 5%", 470, 246.76)
s.wire(452, 246.76, l, 246.76)
s.wire(r, 246.76, 492, 246.76)
s.junction(492, 246.76)
s.sym("R", "R35", "56k 5%", 492, 250.57, lx=2.4, ly=-0.8)
s.gnd(492, 254.38)
s.wire(492, 246.76, 508, 246.76)
s.sym("DIODE_SS", "D1", "F-4", 516, 246.76, rot=180, label_rot=0, lx=-3.4, ly=-6.4)
s.wire(508, 246.76, 510.92, 246.76)
s.wire(521.08, 246.76, 528, 246.76)
s.wire(528, 246.76, 528, 268)
s.wire(528, 268, 500, 268)
s.junction(500, 268)
s.sym("R", "R34", "47k 5%", 500, 271.81, lx=2.4, ly=-0.8)
s.gnd(500, 275.62)
s.wire(500, 268, 482, 268)
s.junction(482, 268)
s.sym("C", "C15", "10u 100V", 482, 271.81, lx=2.4, ly=-0.8)
s.gnd(482, 275.62)
l, r = s.series_h("R", "R42", "10k", 468, 268)
s.wire(482, 268, r, 268)
s.wire(l, 268, 454, 268)
s.junction(454, 268)
s.sym("C", "CBF2", "10u 100V", 454, 271.81, lx=-11.4, ly=-0.8)
s.gnd(454, 275.62)
s.wire(446, 268, 454, 268)
s.glabel("-50V", 446, 268, 180)
s.text("Bias-line polarity: both cans have their negative side on the line.", 446, 282, 1.2)

# ============================ HEATER HUM BALANCE =====================
s.caption('6.3 V heater winding — the HUM CONT. balance only. The chain itself (green pair, V1..V5 on pins 7/8 and 7/2) is drawn on the board layout.', 440, 290, 1.3)
s.glabel("HTR A", 462, 296, 180)
s.wire(462, 296, 476.19, 296)
s.sym("POT", "VR7", "100-L", 480, 296, rot=270, label_rot=0, lx=-4.0, ly=-7.4)
s.wire(483.81, 296, 498, 296)
s.glabel("HTR B", 498, 296, 0)
s.wire(480, 301.08, 480, 304)
s.gnd(480, 304)

# ============================ MAINS SIDE =============================
s.note('The mains side is the annotation layer, drawn only as far as the sheet settles it: the POWER switch SW6 in one line leg ahead of the transformer primary, and the two 0.047 uF 600 V capacitors it letters C18 and (a third time) C19 — listed CM2 — from the line to chassis, the first through the POLAR. switch SW7. That corner of the published scan is coarse: the parts, their values and their mains-side placement are the sheet\'s; the exact switching is drawn as the line-to-chassis pair it letters. The 3 A and 6 A fuses, the switched 120 V AC outlet and the panel pilot lamp are not drawn — this circuit puts that pilot straight across the transformer primary, not on the heater chain.')
s.glabel("AC L", 282, 256.92, 180)
s.wire(282, 256.92, 320.92, 256.92)
s.junction(300, 256.92)
sw6a, sw6b = s.switch("SW6", "SPST", 326, 256.92, lx=-3.6, ly=-6.4)
s.wire(331.08, 256.92, pt["pri1"][0], 256.92)
s.sym("C", "C18", ".047u 600V", 300, 260.73, lx=2.4, ly=-0.8)
s.wire(300, 264.54, 300, 268)
s.sym("SWITCH", "SW7", "SPDT", 300, 273.08, rot=90, label_rot=0, lx=2.8, ly=-1.4)
s.wire(300, 278.16, 300, 281)
s.gnd(300, 281)
s.glabel("AC N", 282, 267.08, 180)
s.wire(282, 267.08, pt["pri2"][0], 267.08)
s.junction(288, 267.08)
s.sym("C", "CM2", ".047u 600V", 288, 270.89, lx=-14.4, ly=-0.8)
s.wire(288, 274.7, 288, 278)
s.gnd(288, 278)

s.write(OUT)
print(f"wrote {OUT}")
