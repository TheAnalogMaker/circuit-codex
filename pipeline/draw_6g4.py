#!/usr/bin/env python3
"""Generate amps/6g4/schematic.kicad_sch from the stage-template library.

Values per the published 6G4 'Super-Amp' drawing (A-FJ) — see amps/6g4/meta.yaml
and amps/6g4/notes.md (which also documents this pass's tube-bottle reading:
five physical 7025 sockets, not six — the oscillator shares channel 1's
recovery-stage bottle, V2A/V2B, and the phase inverter is V5).

The sheet reads: channel 1 (its own input stage, Bass/Treble tone stack and
volume, recovery stage) at the top left, channel 2 mirrored at the bottom
left, the bias-vary tremolo oscillator (V2B) alongside channel 1's recovery
stage, the long-tailed-pair phase inverter and 6L6GC output at the right, and
the power and bias supplies along the bottom. Drawn on A3.

Redrawn from circuit facts — never a trace of a factory drawing. Rails: BP1
= +456 (6L6GC plates/screens, OT centre tap), BD = +261 (calibrated — both
channels' input-stage plates), BE1 = +284 (calibrated — channel 1 recovery
plate), BE2 = +215 (calibrated — channel 2 recovery plate), BC = BP1 through
the drawing's own 4700 1W dropper (RD1) feeding the PI plates; NBIAS = -55 V
fixed bias. BD/BE1/BE2 are drawn as labelled rails with no dropping-resistor
network shown: the drawing's own resistor chain from the 6L6GC-plate rail
into these three preamp rails was not legible at this scan's resolution (see
notes.md) and no bom.yaml part exists for it, so nothing is invented here —
netlist.cir drives each as an independently-calibrated ideal source. Heaters,
PT primary/mains, the pilot lamp and the vibrato-pedal jack's own switching
are omitted here (annotation layer) — see netlist.cir, meta.yaml, layout.yaml.

The tremolo oscillator IS drawn (the schematic documents the whole circuit,
same convention as 6g3/ab763); its DC operating point alone is excluded from
netlist.cir — a running phase-shift oscillator has no static bias point, and
this drawing's own chart prints no dynamic-average voltage for it either (see
notes.md).
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g4" / "schematic.kicad_sch"
s = Sch()

GB = 40   # input grid-bus x (both channels)
VX = 52   # channel-input triode x


def input_stage(y, j1, j2, r1, r2, rleak, vref, rload, rk, ck, rail):
    """Two-jack channel input: 68k stoppers -> grid (1M leak, no coupling cap —
    the jack-merge node is the grid directly) -> triode -> 100k plate load off
    `rail` -> 1.5k/25uF cathode. Returns the triode pin dict."""
    s.glabel(j1, 12, y - 4, 180)
    s.glabel(j2, 12, y + 4, 180)
    l, r = s.series_h("R", r1, "68k", 22, y - 4)
    s.wire(12, y - 4, l, y - 4)
    s.wire(r, y - 4, GB, y - 4)
    l, r = s.series_h("R", r2, "68k", 22, y + 4)
    s.wire(12, y + 4, l, y + 4)
    s.wire(r, y + 4, GB, y + 4)
    s.wire(GB, y - 4, GB, y + 4)
    s.junction(GB, y)
    s.sym("R", rleak, "1M", GB, y + 3.81 + 4)
    s.gnd(GB, y + 7.62 + 4)
    t = s.triode(vref, "7025", VX, y)
    s.wire(GB, y, t["g"][0], y)
    s.plate_load(rload, "100k", t["p"], rail)
    s.wire(VX, y + 7.62, VX, y + 9)
    s.shunt_rc(rk, "1.5k", ck, "25u", VX, y + 9)
    return t


def tone_stack(tee, cc, ct, vrt, rs, vrb, cb, rsl, vrv, cbr):
    """Bass/Treble two-knob network as the A-FJ sheet draws it. The plate tee
    feeds the stack through CC (.05) to the stack input T. From T: CT (250MM)
    to the Treble pot's hot lug (pin 1) and RS (100k) down to node A, the
    slope foot, which also carries the Treble pot's cold lug (pin 3) and the
    Bass pot's hot lug. The Bass control is a DIVIDER from A to ground: CB
    (.01) bridges its upper section (A to the wiper, node B) and RSL (10k)
    bridges its lower (B to ground); the pot's foot lug is grounded. The
    Treble wiper is the stack's output, into the Volume pot, with CBR (47MM)
    from the Volume pot's hot lug to its wiper. Returns the Volume wiper (x, y)
    for the recovery stage's grid.

    Until 2026-09-10 this function drew neither capacitor, took the slope
    straight off the plate (a DC path to ground through the stack) and
    strapped the Bass pot as a rheostat above the 10k.

    POT pin geometry (cx:POT, rot 0): pin 1 (top) = center_y - 3.81,
    pin 3 (bottom) = center_y + 3.81, pin 2 (wiper) = (center_x + 5.08,
    center_y); mirror="y" puts the wiper at center_x - 5.08."""
    s.junction(VX, tee)
    s.wire(VX, tee, 56.19, tee)
    s.series_h("C", cc, ".05u", 60, tee)             # coupler: plate tee -> T
    s.wire(63.81, tee, 70, tee)                      # node T (stack input)

    ty = tee - 12                                    # treble pot centre y
    tl, tr = s.series_h("C", ct, "250p", 76, ty - 3.81)
    s.wire(70, tee, 70, ty - 3.81)
    s.wire(70, ty - 3.81, tl, ty - 3.81)
    s.wire(tr, ty - 3.81, 88, ty - 3.81)             # -> treble pot hot lug (pin 1)
    s.sym("POT", vrt, "250k-L treb", 88, ty, lx=2.4, ly=-9.2)

    ay = tee + 8                                     # node A (slope foot) y
    sl, sr = s.series_h("R", rs, "100k", 75, ay)
    s.wire(70, tee, 70, ay)
    s.junction(70, tee)
    s.wire(70, ay, sl, ay)
    s.wire(sr, ay, 79, ay)
    s.junction(79, ay)                               # node A
    s.wire(79, ay, 88, ay)
    s.wire(88, ty + 3.81, 88, ay)                    # treble cold lug (pin 3) -> node A
    s.junction(88, ay)
    # Bass pot, mirrored so its wiper faces the capacitor and the foot: pin 1
    # (hot) on node A, pin 3 (foot) grounded, wiper = node B.
    bay = ay + 7.62                                  # bass pot centre y
    s.sym("POT", vrb, "250k-A bass", 88, bay, mirror="y", lx=2.4, ly=-1.5)
    s.wire(88, ay, 88, bay - 3.81)                   # node A -> bass hot lug (pin 1)
    s.gnd(88, bay + 3.81)                            # bass foot lug (pin 3) -> ground
    s.sym("C", cb, ".01u", 79, ay + 3.81, lx=-8.6, ly=0.0)   # CB: node A -> node B
    s.wire(79, ay + 7.62, 82.92, ay + 7.62)          # node B -> bass WIPER (mirrored, left)
    s.junction(79, ay + 7.62)
    s.sym("R", rsl, "10k", 79, ay + 7.62 + 3.81, lx=-9.4)   # RSL: node B -> ground
    s.gnd(79, ay + 15.24)

    # treble wiper (pin 2) = stack output -> Volume pot hot lug (pin 1)
    s.wire(93.08, ty, 100.5, ty)
    s.sym("POT", vrv, "500k-L vol", 100.5, ty + 3.81, lx=-11.6, ly=-10.4)
    s.gnd(100.5, ty + 7.62)
    # bright cap: Volume hot lug -> wiper, drawn over the pot
    s.junction(100.5, ty)
    s.wire(100.5, ty, 100.5, ty - 6)
    bl, br = s.series_h("C", cbr, "47p", 106, ty - 6)
    s.wire(100.5, ty - 6, bl, ty - 6)
    s.wire(br, ty - 6, 112, ty - 6)
    s.wire(112, ty - 6, 112, ty + 3.81)
    s.wire(105.58, ty + 3.81, 112, ty + 3.81)
    s.junction(105.58, ty + 3.81)
    return (105.58, ty + 3.81)


def channel(y, ch, j1, j2, r1, r2, rleak, v_in, v_rec, rload_in, rload_rec,
            rk_in, ck_in, rk_rec, ck_rec, cc_t, ct, vrt, rs, vrb, cb_t, rsl, vrv, cbr,
            cc, mixer, mixer_val, rail_in, rail_rec, y_rec):
    """One full channel: input stage -> tone stack -> recovery stage ->
    coupler -> mixing resistor -> the shared GPIA bus."""
    s.text(f"Channel {ch}", 12, y - 14, 1.6)
    t_in = input_stage(y, j1, j2, r1, r2, rleak, v_in, rload_in, rk_in, ck_in, rail_in)
    tee = y - 7.62 - 3.48
    wiper = tone_stack(tee, cc_t, ct, vrt, rs, vrb, cb_t, rsl, vrv, cbr)
    t_rec = s.triode(v_rec, "7025", 116, y_rec)
    s.wire(wiper[0], wiper[1], wiper[0], y_rec)
    s.wire(wiper[0], y_rec, t_rec["g"][0], y_rec)
    s.plate_load(rload_rec, "100k", t_rec["p"], rail_rec)
    s.wire(116, y_rec + 7.62, 116, y_rec + 9)
    s.shunt_rc(rk_rec, "820", ck_rec, "25u", 116, y_rec + 9)
    teer = y_rec - 7.62 - 3.48
    s.junction(116, teer)
    s.wire(116, teer, 124, teer)
    cl, cr = s.series_h("C", cc, ".05u", 128, teer)
    s.wire(124, teer, cl, teer)
    ml, mr = s.series_h("R", mixer, mixer_val, 138, teer)
    s.wire(cr, teer, ml, teer)
    s.wire(mr, teer, 148, teer)
    s.wire(148, teer, 148, 178)
    return t_rec


# ============================ TITLE ==================================
s.note('Rails: BP1 +456 (6L6GC plates/screens, OT CT) · BD +261 (calibrated, both input stages) · BE1 +284 (ch.1 recovery, calibrated) · BE2 +215 (ch.2 recovery, calibrated) · BC = BP1 via 4700 1W (PI plates) · bias -55 V')
s.note("Heaters, PT primary/mains, pilot lamp and the vibrato-pedal jack's switching are omitted here — see the netlist, the sources list and the board drawing. Bottles are 7025, a low-noise 12AX7 (an alias of the same valve).")

# ============================ CHANNEL 1 ================================
YN = 62
YN_REC = 66
channel(YN, 1, "CH1 IN 1", "CH1 IN 2", "R1a", "R2a", "RG1I", "V1", "V2A",
        "RL1I", "RL1D", "RK1I", "CK1I", "RK1D", "CK1D",
        "CC1T", "CT1", "VRT1", "RS1T", "VRB1", "CB1T", "RSL1", "VRV1", "CBR1",
        "CC1D", "RM1", "6.8k", "BD", "BE1", YN_REC)

# ============================ CHANNEL 2 ================================
YB = 128
YB_REC = 132
channel(YB, 2, "CH2 IN 1", "CH2 IN 2", "R1b", "R2b", "RG2I", "V3", "V4",
        "RL2I", "RL2D", "RK2I", "CK2I", "RK2D", "CK2D",
        "CC2T", "CT2", "VRT2", "RS2T", "VRB2", "CB2T", "RSL2", "VRV2", "CBR2",
        "CC2D", "RM2", "220k", "BD", "BE2", YB_REC)


# the two mixers meet on one bus line; the flag names it once
s.junction(148, 178)
s.glabel("GPIA", 148, 178, 0)

# ============================ TREMOLO OSCILLATOR (V2B) =================
# Shares channel 1's recovery-stage bottle (V2A above); its DC point is
# excluded from netlist.cir (see notes.md) — a running phase-shift
# oscillator has no static operating point, and this drawing's own chart
# prints no dynamic-average voltage for it either.
#
# RTO1 (100k) is both the plate load AND the first element of the phase-
# shift ladder (the same double duty 6G3's own RL4 plate-load resistor
# serves) — bom.yaml carries no separate plate-load part. Three series caps
# (CTO1, CTO2, CTOFB — .01/.01/.005 uF) form the ladder proper; the Speed
# pot (VRSPD, 4M-RA) shunts the first junction to ground (varying that
# stage's time constant, hence oscillation rate) and the feedback resistor
# (RTOFB, 4.7M) shunts the last junction — the grid — to ground as the
# stage's own grid leak (self-bias; no cathode resistor in bom.yaml, so the
# cathode grounds directly). Cathode -> ground; grid self-biases through
# RTOFB on grid current at oscillation amplitude, the classic phase-shift-
# oscillator limiting mechanism.
YT = 100
s.caption("Tremolo oscillator (V2B, shares V2's bottle with channel 1's recovery stage) — three-stage RC phase-shift ladder", 160, 82, 1.4)
s.note('Excluded from the netlist — a running oscillator has no static operating point (see the circuit story)')
t2b = s.triode("V2B", "7025", 176, YT, lx=6.0, ly=8.0)
s.plate_load("RTO1", "100k", t2b["p"], "BP1")
s.gnd(176, YT + 7.62)
teeo = YT - 7.62 - 3.48
s.junction(176, teeo)
s.wire(176, teeo, 184, teeo)
cl, cr = s.series_h("C", "CTO1", ".01u", 188, teeo)
s.wire(184, teeo, cl, teeo)
s.wire(cr, teeo, 196, teeo)
s.junction(196, teeo)                              # N1
# Anchor the Speed pot's lettering beside its own ground stub, under the
# wiper: the default anchor sat the value line on the ladder wire and CTO2's
# left pin, and the placer's alternative dropped it onto the ground stub.
s.sym("POT", "VRSPD", "4M-RA speed", 196, teeo + 3.81, lx=7.0, ly=2.8)
# Rheostat: foot lug to ground, wiper strapped to it (the idiom 6G3's own VR5
# uses). Drawn with neither lead, the "Speed" control was a fixed 4M to nowhere.
# The ground goes out to the LEFT: straight down it would have run through
# V2B's grid line, which crosses under this whole ladder at y = YT.
s.wire(196, teeo + 7.62, 190, teeo + 7.62)
s.gnd(190, teeo + 7.62, 180)
s.wire(201.08, teeo + 3.81, 201.08, teeo + 7.62)
s.wire(201.08, teeo + 7.62, 196, teeo + 7.62)
s.junction(196, teeo + 7.62)
s.text("Speed", 184, teeo - 6, 1.2)
cl, cr = s.series_h("C", "CTO2", ".01u", 204, teeo)
s.wire(196, teeo, cl, teeo)
s.wire(cr, teeo, 212, teeo)
s.junction(212, teeo)                              # N2
cl, cr = s.series_h("C", "CTOFB", ".005u", 220, teeo)
s.wire(212, teeo, cl, teeo)
s.wire(cr, teeo, 228, teeo)                         # N3 = grid node
s.wire(228, teeo, 234, teeo)      # node line extended so the leak has its own foot
s.junction(228, teeo)
s.wire(228, teeo, 228, YT)
s.wire(228, YT, t2b["g"][0], YT)
s.sym("R", "RTOFB", "4.7M", 234, teeo + 3.81, lx=3.2)
s.gnd(234, teeo + 7.62)

# --- Intensity: plate tee -> 220k series -> Intensity pot -> the -55V bias line
s.wire(176, teeo, 164, teeo)
s.wire(164, teeo, 164, teeo - 10)
s.sym("R", "RINT", "220k", 164, teeo - 13.81)
s.wire(164, teeo - 17.62, 164, teeo - 21)
s.sym("POT", "VRINT", "10M-RA intensity", 164, teeo - 24.81)
s.gnd(164, teeo - 32.43)
s.wire(164, teeo - 28.62, 164, teeo - 32.43)   # pot lug -> its own ground flag
s.wire(169.08, teeo - 24.81, 190, teeo - 24.81)
s.glabel("NBIAS", 190, teeo - 24.81, 0)
s.text("Intensity", 132, teeo - 26, 1.2)

# ============================ PHASE INVERTER (V5, LTP) =================
XPI = 260
YPH = 100          # hot half (V5A)
YPB = 150          # cold half (V5B)
JY = 125           # tail junction
s.caption("Long-tailed-pair phase inverter (V5)", 244, 82, 1.4)
s.note("The phase inverter runs off the BC rail — BP1 through the drawing's own 4700 1W dropper, RD1.")
# RD1: the PI's own supply dropper, BP1 -> BC (carries only the PI's own
# current in the model — see netlist.cir's DC-conventions note). Lettered
# "4700 1W" on the sheet, between the +456 V node at the choke and the
# +430 V node where the 82k and 100k plate loads meet. It read 10k here
# until 2026-09-09: the 10K lettered across the top of the sheet is RNFB,
# the feedback resistor, whose far end lands on the OT secondary hot and
# never touches this rail. netlist.cir's header carries the full trace.
s.glabel("BP1", 300, 60, 180)
s.wire(300, 60, 300, 63.5)
s.sym("R", "RD1", "4.7k 1W", 300, 67.31)
s.wire(300, 71.12, 300, 74.5)
s.glabel("BC", 300, 74.5, 0)
s.glabel("GPIA", 228.19, YPH, 180)                # bus from both channels' mixers (RM1/RM2)
s.wire(228.19, YPH, XPI - 7.62, YPH)
# The A-FJ layout wires the 82k-plate (.001-fed) triode on pins 1/2/3 (+315 V ->
# 1) and the 100k triode on 6/7/8 (+310 V -> 6) (crop triage 6g4-V5-layout-trace
# .png, 2250x1269, the only copy): V5A is datasheet unit 2, V5B unit 1.
t5a = s.triode("V5A", "7025", XPI, YPH, unit=2)
t5b = s.triode("V5B", "7025", XPI, YPB, unit=1)
s.plate_load("RLPA", "82k 5%", t5a["p"], "BC")
s.plate_load("RLPB", "100k 5%", t5b["p"], "BC")
# cathodes join on a right stub; 820 from there to the tail junction
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, 250, YPH + 10)
# ...and the cold half's cathode comes out UNDER its own bottle, left, and up
# into the same bus (YPB - 7.62 is the PLATE pin on an upright triode, so the
# tail resistor sat on the cold plate node and V5B's cathode floated).
s.wire(XPI, YPB + 7.62, 246, YPB + 7.62)
s.wire(246, YPB + 7.62, 246, YPB - 10)
s.wire(246, YPB - 10, 250, YPB - 10)
s.wire(250, YPH + 10, 250, YPB - 10)
s.junction(250, JY)
tl, tr = s.series_h("R", "RTAIL", "820 5%", 244.5, JY)
s.wire(250, JY, tr, JY)
s.wire(238, JY, tl, JY)                            # JPI, the tail junction
s.junction(238, JY)
# hot grid leak: JPI -> 1M -> hot grid
s.sym("R", "RGPA", "1M", 238, JY - 8, lx=-9.4)
s.wire(238, JY - 4.19, 238, JY)
s.wire(238, JY - 11.81, 238, YPH)
s.junction(238, YPH)
s.wire(238, YPH, 228.19, YPH)
s.junction(228.19, YPH)
# cold grid leak: JPI -> 1M -> cold grid
s.sym("R", "RGPB", "1M", 234, JY + 8, lx=2.8)
s.wire(234, JY + 4.19, 234, JY)
s.junction(234, JY)
s.wire(234, JY + 11.81, 234, YPB)
s.wire(234, YPB, XPI - 7.62, YPB)
s.junction(XPI - 7.62, YPB)

# --- tail junction -> 6.8k -> NFB/presence node ------------------------
tl, tr = s.series_h("R", "RT2", "6.8k", 226, JY)
s.wire(tr, JY, 238, JY)
s.wire(tl, JY, 216, JY)                            # NFB node
s.junction(216, JY)
nl, nr = s.series_h("R", "RNFB", "10k", 202, JY)
s.wire(nr, JY, 216, JY)
s.wire(186, JY, nl, JY)
s.glabel("SPKR", 186, JY, 180)
# Presence, drawn as the factory sheet draws it: RPF (the 1500 foot resistor)
# runs from the tail foot straight down to ground, and the 5k-L Presence pot
# in series with CPRES (.1) PARALLELS it. CPRES was missing from the corpus
# until 2026-09-09 — it is what makes the pot branch AC-only, which is exactly
# what netlist.cir claims about this node.
#
# What this shares with the 6G3 Deluxe is the tail foot itself: a 1500 foot
# resistor straight to ground with the negative-feedback return from the OT
# secondary landing on the same node, under an 820/6.8k long-tailed pair whose
# two 1M grid leaks both return to the tail junction. The 6G3 has no Presence
# control at all — no pot, no cap, a bare 1500 to ground — and its feedback
# resistor is 56k where this one is 10k. The earlier "identical to 6G3's"
# comment here claimed a Presence recipe the 6G3 sheet does not draw.
TAP = JY + 5.08                      # the pot branch leaves the foot lead here
FGY = JY + 22.86                     # ground node shared by both legs
PX = 224                             # pot/cap lane
s.wire(216, JY, 216, TAP)
s.sym("R", "RPF", "1.5k", 216, JY + 8.89, lx=3.2, ly=2.0)
s.wire(216, JY + 12.7, 216, FGY)
s.gnd(216, FGY)
s.junction(216, TAP)
# The tap lead runs on past the pot to PX + 5.08, where the wiper strap climbs
# to meet it; the pot's own top lug T-taps it at PX (dotted below).
s.wire(PX + 5.08, TAP, 216, TAP)
s.sym("POT", "VRPRES", "5k-L pres", PX, JY + 8.89, lx=3.2, ly=2.2)
s.junction(PX, TAP)
s.wire(PX, JY + 12.7, PX, JY + 15.24)
s.sym("C", "CPRES", ".1u 200V", PX, JY + 19.05, lx=3.2, ly=2.2)
s.wire(PX, FGY, 216, FGY)
s.junction(216, FGY)
# Rheostat: the wiper is strapped to the lug the tail foot feeds, so the control
# reads as the two-terminal variable resistance the sheet's glyph (an arrow
# drawn across the element, with neither end lettered) means. Left floating it
# would be a fixed 5k.
s.wire(PX + 5.08, JY + 8.89, PX + 5.08, TAP)

# ============================ OUTPUT COUPLERS + 6L6GC ==================
teea = YPH - 7.62 - 3.48
teec = YPB - 7.62 - 3.48
s.junction(XPI, teea)
s.wire(XPI, teea, 280, teea)
s.junction(XPI, teec)
s.wire(XPI, teec, 280, teec)
cl, cr = s.series_h("C", "C1", ".05u", 288, teea)
s.wire(280, teea, cl, teea)
s.wire(cr, teea, 296, teea)
# up the 296 lane, not 300: climbing x=300 the run passed through RGL1's
# lower pin and shorted V7's grid leak end to end.
s.wire(296, teea, 296, 80)
s.wire(296, 80, 300, 80)
cl, cr = s.series_h("C", "C2", ".05u", 288, teec)
s.wire(280, teec, cl, teec)
s.wire(cr, teec, 300, teec)
s.wire(300, teec, 300, 172)

XO = 324
s.text("Output pair — 6L6GC, fixed bias, screens off BP1 through 470R-1W stoppers each", 300, 62, 1.4)
plates = {}
for gy, vref, glref, sref, gnode in [(80, "V7", "RGL1", "RS1", 300), (172, "V8", "RGL2", "RS2", 300)]:
    s.wire(gnode, gy, XO - 7.62, gy)
    p = s.pentode(vref, "6L6GC", XO, gy)
    plates[vref] = p["p"]
    s.junction(gnode, gy)
    s.sym("R", glref, "220k 5%", gnode, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(gnode, gy + 7.62, gnode, gy + 10.16)
    s.glabel("NBIAS", gnode, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 2, p["g2"][1])
    sl, sr = s.series_h("R", sref, "470 1W", p["g2"][0] + 5.81, p["g2"][1])
    s.wire(sr, p["g2"][1], p["g2"][0] + 11.5, p["g2"][1])
    s.glabel("BP1", p["g2"][0] + 11.5, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# ---- output transformer ---------------------------------------------
s.sym("OT_PP", "T2", "45216", 356, 126, lx=-6.35, ly=-14.5)
s.wire(*plates["V7"], XO, 68)
s.wire(XO, 68, 347.11, 68)
s.wire(347.11, 68, 347.11, 120.92)
# V8's primary lead was drawn from a point 0.76 mm under its GROUNDED cathode,
# so the plate reached nothing and the OT's lower primary hung off the ground
# stub. Taken off the plate pin itself, up and over the bottle's own lettering.
s.wire(*plates["V8"], XO, 158)
s.wire(XO, 158, 342, 158)
s.wire(342, 158, 342, 131.08)
s.wire(342, 131.08, 347.11, 131.08)
s.wire(347.11, 126, 334, 126)
s.glabel("BP1", 334, 126, 180)
s.wire(364.89, 123.46, 368, 123.46)
s.glabel("SPKR", 368, 123.46, 0)
s.wire(364.89, 128.54, 368, 128.54)
s.glabel("GND", 368, 128.54, 0)

# ============================ POWER SUPPLY ==============================
YPW = 210
BY = YPW + 6
s.note('Power supply — TR1 8087, GZ34 full-wave, CH-125C1A choke; TR2 45216 output transformer')
pt = s.pt("T1", "8087", 212, YPW, lx=-6.35, ly=-12.5, tap=True)
s.wire(pt["tap"][0], pt["tap"][1], pt["tap"][0] + 2, pt["tap"][1])
s.glabel("HT_TAP", pt["tap"][0] + 2, pt["tap"][1], 0)
s.wire(pt["pri1"][0], pt["pri1"][1], pt["pri1"][0] - 4, pt["pri1"][1])
s.glabel("MAINS", pt["pri1"][0] - 4, pt["pri1"][1], 180)
s.wire(pt["pri2"][0], pt["pri2"][1], pt["pri2"][0] - 4, pt["pri2"][1])
s.glabel("MAINS N", pt["pri2"][0] - 4, pt["pri2"][1], 180)
s.wire(pt["ht_a"][0], pt["ht_a"][1], pt["ht_a"][0] + 4, pt["ht_a"][1])
s.glabel("HT_A", pt["ht_a"][0] + 4, pt["ht_a"][1], 0)
s.wire(pt["ht_b"][0], pt["ht_b"][1], pt["ht_b"][0] + 4, pt["ht_b"][1])
s.glabel("HT_B", pt["ht_b"][0] + 4, pt["ht_b"][1], 0)
s.wire(pt["ht_ct"][0], pt["ht_ct"][1], pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.gnd(pt["ht_ct"][0] + 4, pt["ht_ct"][1])
s.glabel("HT_A", 244, YPW - 14, 90)
s.wire(244, YPW - 14, 244, YPW - 11.5)
s.diode_tube("V9A", "GZ34", 244, YPW - 3.88, lx=-11.8)
s.glabel("HT_B", 256, YPW - 14, 90)
s.wire(256, YPW - 14, 256, YPW - 11.5)
s.diode_tube("V9B", "GZ34", 256, YPW - 3.88, lx=6.2)
s.wire(244, YPW + 3.74, 244, BY)
s.wire(256, YPW + 3.74, 256, BY)
s.wire(244, BY, 268, BY)
s.junction(256, BY)
s.junction(262, BY)
s.sym("C", "C10", "20u", 262, BY + 3.81)
s.gnd(262, BY + 7.62)
s.wire(268, BY - 3.5, 268, BY)
s.glabel("BP1", 268, BY - 3.5, 90)
s.junction(268, BY)
s.note("C10 stands for the drawing's several HT filter cans; per-node values were not fully resolved at this scan's resolution (see the parts list)")

# BD/BE1/BE2: labelled rails only — the drawing's own dropping-resistor
# chain from BP1 into these three preamp rails was not legible at this
# scan's resolution (notes.md). CH1 (bom.yaml: "reservoir -> screen/preamp
# rail") is the one part the BOM does name for this leg, so it is drawn
# feeding BD; BE1/BE2 have no discrete bom.yaml part and are left as plain
# labels — nothing else is invented here. netlist.cir drives each rail
# independently.
s.note("BD/BE1/BE2 (preamp rails) are calibrated ideal sources in the netlist — the drawing's own dropper chain into them was not legible (see the circuit story); only CH1 is a named part in the parts list.")
s.wire(268, BY, 280, BY)
s.sym("CHOKE", "CH1", "125C1A", 287.62, BY, lx=-4.0, ly=-6.4)
s.wire(295.24, BY, 300, BY)
s.glabel("BD", 300, BY, 0)
s.glabel("BE1", 300, BY + 6, 0)
s.glabel("BE2", 300, BY + 12, 0)

# ============================ BIAS SUPPLY ===============================
YBI = 240
s.text("Bias supply — the transformer's bias tap, a rectifier, 8 uF, 10k, then 8 uF with a 56k bleeder: a fixed -55 V (no trimmer)",
       196, 232, 1.3)
# A-FJ (the only copy, read natively): the transformer's bias tap feeds the
# rectifier's + (bar) end; its - end is node N with an 8-150 to ground; a 10K
# runs from N to the output node, which carries a second 8-150 to ground and
# the 56K to ground (a bleeder, not a series element) and is the -55 V line.
# Until 2026-09-10 this row fed the rectifier from an HT end, drew the 56K in
# series and carried one capacitor.
s.glabel("HT_TAP", 196, YBI, 180)
s.wire(196, YBI, 205.08, YBI)
s.sym("DIODE_SS", "DBIAS", "Si", 210, YBI, lx=-2.0, ly=-5.4, rot=180, label_rot=0)
s.wire(215.08, YBI, 222, YBI)
s.junction(222, YBI)
s.sym("C", "CBIAS", "8u", 222, YBI + 3.81)
s.gnd(222, YBI + 7.62)
l, r = s.series_h("R", "RBIAS2", "10k", 230, YBI)
s.wire(222, YBI, l, YBI)
s.wire(r, YBI, 254, YBI)
s.junction(240, YBI)
s.sym("C", "CBIAS2", "8u", 240, YBI + 3.81)
s.gnd(240, YBI + 7.62)
s.junction(247, YBI)
s.sym("R", "RBIAS1", "56k", 247, YBI + 3.81)
s.gnd(247, YBI + 7.62)
s.glabel("NBIAS", 254, YBI, 0)

s.write(OUT)
print(f"wrote {OUT}")
