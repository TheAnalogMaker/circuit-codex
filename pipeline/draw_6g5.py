#!/usr/bin/env python3
"""Generate amps/6g5/schematic.kicad_sch from the stage-template library.

Values per the published Fender "Pro-Amp" Model 6G5 drawing (A-FJ) — see
amps/6g5/meta.yaml and notes.md. Two full mirrored channels (Normal top,
Bright bottom), each two 7025 stages into a Bass/Treble tone stack and a
Volume pot; both channels sum at a shared mixing node that the tremolo
photocell also shunts; a driver stage feeds the long-tailed-pair phase
inverter and the two 6L6GC output tubes; a silicon bridge (no tube
rectifier) and a dropper chain make up the power supply. Drawn on A3 so
every block clears its neighbours and the title block.

Redrawn from circuit facts — never a trace of a factory drawing. Rails:
BP1 = +456 (6L6GC plates, post-choke), BP2 = +430 (screens, after the read
4700 Ohm-1W dropper), BP3 = +410 / BDRV = +480 / BD = +300 (phase-inverter,
driver and shared-preamp rails — netlist.cir DRIVES these three directly as
anchors rather than deriving them through the 56k/10k dropper chain; see its
header and notes.md for why). -55 V is the fixed-bias line, likewise an ideal
source in the DC model. Heaters, PT primary/mains, the pilot lamp and the
chassis switches are omitted here (annotation layer) — see netlist.cir,
meta.yaml, and the board layout (layout.yaml).

The tremolo oscillator (V3) IS drawn: the schematic documents the whole
circuit. Its DC operating point alone is excluded from netlist.cir — a
running phase-shift oscillator has no static bias point (see notes.md). Its
phase-shift ladder values are a schematic-only, typical-of-the-family
reading (bom.yaml flags them); nothing about that affects any gated claim.
"""
from pathlib import Path

from schematic_lib import Sch

OUT = Path(__file__).resolve().parent.parent / "amps" / "6g5" / "schematic.kicad_sch"
s = Sch()

GB = 40   # input grid-bus x
VX = 52   # channel first-stage triode x


def cathode_split_rc(rref, rval, cref, cval, x, ytop, dx=7.62):
    """Cathode R with a split-can C to ground; label pushed clear of the join wire."""
    s.sym("R", rref, rval, x, ytop + 3.81, lx=-9.2, ly=0.0)
    s.sym("C", cref, cval, x + dx, ytop + 3.81)
    s.wire(x, ytop, x + dx, ytop)
    s.wire(x, ytop + 7.62, x + dx, ytop + 7.62)
    s.gnd(x, ytop + 7.62)


def channel(y, tag, jn2, rjn, rg, vref_a, rl_a, rk_a, ck_a,
            vrb, vrt, ct, cf, rf, vrv, rl_b, rk_b, ck_b, rail):
    """One full channel row: jack -> stopper -> V.A -> Bass/Treble tone stack
    + Volume -> V.B. Returns V.B's triode pin dict and its plate-tee y."""
    s.glabel(f"{tag} 1", 12, y - 4, 180)
    s.glabel(f"{tag} 2", 12, y + 4, 180)
    l, r = s.series_h("R", rjn, "68k", 22, y + 4)
    s.wire(16, y + 4, l, y + 4)
    s.wire(r, y + 4, GB, y + 4)
    s.wire(16, y - 4, GB, y - 4)              # jack 1: straight to the grid bus
    s.wire(GB, y - 4, GB, y + 4)
    s.junction(GB, y)
    s.sym("R", rg, "1M", GB, y + 3.81 + 4)
    s.gnd(GB, y + 7.62 + 4)
    ta = s.triode(vref_a, "7025", VX, y)
    s.wire(GB, y, ta["g"][0], y)
    s.plate_load(rl_a, "100k", ta["p"], rail)
    s.wire(VX, y + 7.62, VX, y + 9)
    s.shunt_rc(rk_a, "820", ck_a, "25u+25u", VX, y + 9)

    tee = y - 7.62 - 3.48                     # node A: plate of the first stage
    s.junction(VX, tee)
    s.wire(VX, tee, 62, tee)
    # treble path: node A -> CT 250p -> VRT, wiper is the stack's treble output
    tl, tr = s.series_h("C", ct, "250p", 68, tee - 6)
    s.wire(62, tee, 62, tee - 6)
    s.wire(62, tee - 6, tl, tee - 6)
    s.wire(tr, tee - 6, 80, tee - 6)
    s.sym("POT", vrt, "250k-A", 80, tee - 6 + 3.81)
    # slope: node A -> RF 10k -> node B (bass foot)
    sl, sr = s.series_h("R", rf, "10k", 67, tee + 6)
    s.wire(62, tee, 62, tee + 6)
    s.junction(62, tee)
    s.wire(62, tee + 6, sl, tee + 6)
    s.wire(sr, tee + 6, 80, tee + 6)
    s.junction(80, tee + 6)                   # node B
    # node B -> CF .01u -> bass node (shared with the treble pot's foot lug)
    bl, br = s.series_h("C", cf, ".01u", 86, tee + 6)
    s.wire(80, tee + 6, bl, tee + 6)
    s.wire(br, tee + 6, 92, tee + 6)
    s.wire(85.08, tee - 2.19, 92, tee - 2.19)  # treble pot's foot lug
    s.wire(92, tee - 2.19, 92, tee + 6)
    s.sym("POT", vrb, "250k-A", 92, tee + 6 + 3.81)
    # bass wired as a rheostat: wiper strapped to its hot lug, foot to ground
    s.wire(97.08, tee + 9.81, 104, tee + 9.81)
    s.wire(104, tee + 9.81, 104, tee + 6)
    s.wire(104, tee + 6, 92, tee + 6)
    s.junction(92, tee + 6)
    s.gnd(92, tee + 13.62)
    # treble wiper -> volume top lug
    s.wire(85.08, tee - 6, 112, tee - 6)
    s.wire(112, tee - 6, 112, tee)
    s.sym("POT", vrv, "250k-A", 112, tee + 3.81)
    s.gnd(112, tee + 7.62)
    # volume wiper -> V.B grid directly (DC-referred through the pot body —
    # netlist.cir's RG1B/RG2B model this without a separate physical leak)
    s.wire(117.08, tee + 3.81, 126, tee + 3.81)
    tb = s.triode(vref_a[:-1] + "B" if vref_a.endswith("A") else vref_a, "7025",
                  138, y, lx=6.0, ly=-6.4)
    s.wire(126, tee + 3.81, 126, y)
    s.wire(126, y, tb["g"][0], y)
    s.plate_load(rl_b, "100k", tb["p"], rail)
    s.wire(138, y + 7.62, 138, y + 9)
    s.sym("R", rk_b, "1.5k (info.)", 138, y + 9 + 3.81, lx=-11.4, ly=0.0)
    s.sym("C", ck_b, "25u (info.)", 138 + 7.62, y + 9 + 3.81)
    s.wire(138, y + 9, 138 + 7.62, y + 9)
    s.wire(138, y + 9 + 7.62, 138 + 7.62, y + 9 + 7.62)
    s.gnd(138, y + 9 + 7.62)
    return tb, y - 7.62 - 3.48


# ============================ TITLE ==================================
s.note('Rails: BP1 +456 (post-choke) · BP2 +430 screens · BP3 +410 (PI, driven anchor) · BDRV +480 (driver, driven anchor) · BD +300 (preamp, driven anchor) · bias -55 V')
s.note('Heaters, PT primary/mains, pilot lamp and chassis switches are omitted here — see netlist.cir, meta.yaml, layout.yaml. BP3/BDRV/BD are DRIVEN anchors, not derived through the dropper chain shown (notes.md).')

# ============================ NORMAL CHANNEL (top) ====================
YN = 62
s.caption('Normal channel — V1 (both stages share one 7025)', 12, 48, 1.6)
t1b, teeN2 = channel(YN, "NORM", "NORM2", "R1N", "RG1A", "V1A", "RL1A", "RK1A", "CK1A",
                      "VRB1", "VRT1", "CT1", "CF1", "RF1", "VRV1", "RL1B", "RK1B", "CK1B", "BD")

# ============================ BRIGHT CHANNEL (bottom) ==================
YB = 160
s.caption('Bright channel — V2 (both stages share one 7025)', 12, 146, 1.6)
t2b, teeB2 = channel(YB, "BRT", "BRT2", "R2N", "RG2A", "V2A", "RL2A", "RK2A", "CK2A",
                      "VRB2", "VRT2", "CT2", "CF2", "RF2", "VRV2", "RL2B", "RK2B", "CK2B", "BD")

# ============================ CHANNEL-MIXING NODE ======================
# Each channel's 2nd-stage plate feeds the shared mixing node through a DC-open
# coupler (netlist.cir does not model these — see its header); the node's own
# 1M leak (RG5) and the tremolo photocell (below) both land here too.
MX, MY = 168, (YN + YB) / 2
s.wire(138, teeN2, 150, teeN2)
cl, cr = s.series_h("C", "CMIX1", ".05u", 156, teeN2)
s.wire(150, teeN2, cl, teeN2)
s.wire(cr, teeN2, MX, teeN2)
s.wire(MX, teeN2, MX, MY)
s.wire(138, teeB2, 150, teeB2)
cl, cr = s.series_h("C", "CMIX2", ".05u", 156, teeB2)
s.wire(150, teeB2, cl, teeB2)
s.wire(cr, teeB2, MX, teeB2)
s.wire(MX, teeB2, MX, MY)
s.junction(MX, teeN2)
s.junction(MX, teeB2)
s.junction(MX, MY)
s.sym("R", "RG5", "1M", MX, MY + 3.81, lx=3.2, ly=1.0)
s.gnd(MX, MY + 7.62)
s.note('Channel-mixing node — both channels sum here; the tremolo photocell (below) also shunts it')

# ============================ DRIVER (V5) ==============================
XD = 200
s.wire(MX, MY, XD - 7.62, MY)
td = s.triode("V5", "7025", XD, MY)
s.plate_load("RL5", "100k", td["p"], "BDRV")
s.wire(XD, MY + 7.62, XD, MY + 9)
s.shunt_rc("RK5", "820", "CK5", "25u", XD, MY + 9)
teeD = MY - 7.62 - 3.48
s.junction(XD, teeD)
s.note('Driver — local feedback network read from the drawing but not confidently resolved (schematic-only; see notes.md, bom.yaml)')
# local feedback network: plate -> RFB1 470k -> node -> RFB2/RFB3 220k each,
# one to ground, one back toward the mixing node; CFB1 2500p bridges the plate
# tee to ground. Drawn for the record; not part of the DC model.
s.wire(XD, teeD, 216, teeD)
rl, rr = s.series_h("R", "RFB1", "470k", 222, teeD)
s.wire(216, teeD, rl, teeD)
s.wire(rr, teeD, 228, teeD)
s.junction(228, teeD)
s.sym("R", "RFB2", "220k", 228, teeD + 3.81, lx=3.0, ly=1.0)
s.gnd(228, teeD + 7.62)
s.wire(228, teeD, 228, teeD - 8)
s.sym("R", "RFB3", "220k", 228, teeD - 11.81, lx=3.0, ly=-2.0)
s.wire(228, teeD - 15.62, 228, teeD - 18)
s.wire(228, teeD - 18, MX, teeD - 18)
s.wire(MX, teeD - 18, MX, teeD)
s.wire(MX, teeD, MX, MY - 0.01)
s.sym("C", "CFB1", "2500p", 210, teeD - 8, rot=90, lx=-3.2, ly=5.0)
s.wire(210, teeD - 3.81, 210, teeD)
s.wire(210, teeD, 216, teeD)
s.junction(216, teeD)
s.wire(210, teeD - 11.81, 210, teeD - 16)
s.gnd(210, teeD - 16)

# ============================ TREMOLO OSCILLATOR (V3, excluded) ========
YT = 230
PT_ = YT - 11.1
s.caption('Tremolo — V3 phase-shift oscillator driving a lamp/photoresistor pair (OPTO) that shunts the mixing node. DC point excluded from netlist.cir (notes.md).', 26, 196, 1.4)
s.note('Phase-shift ladder values (RTOG1/RTOG2/CTO1-3) are a schematic-only reading, typical of this circuit family — not confidently resolved from the scan (bom.yaml).')
t3 = s.triode("V3", "7025", 100, YT)
s.wire(100, YT - 7.62, 100, PT_)
s.sym("R", "RTOP", "100k", 100, PT_ - 3.81)
s.wire(100, PT_ - 7.62, 100, PT_ - 10.16)
s.glabel("BP1", 100, PT_ - 10.16, 90)
s.junction(100, PT_)
# phase-shift ladder: plate -> .02 -> .01 -> .01 -> grid
cl, cr = s.series_h("C", "CTO3", ".02u", 90, PT_)
s.wire(cr, PT_, 100, PT_)
s.wire(80, PT_, cl, PT_)
s.junction(80, PT_)
cl, cr = s.series_h("C", "CTO1", ".01u", 70, PT_)
s.wire(cr, PT_, 80, PT_)
s.wire(60, PT_, cl, PT_)
s.junction(60, PT_)
cl, cr = s.series_h("C", "CTO2", ".01u", 50, PT_)
s.wire(cr, PT_, 60, PT_)
s.wire(40, PT_, cl, PT_)
s.junction(40, PT_)
# speed pot (rheostat) across the first ladder node
s.sym("POT", "VRSPD", "4M-RA speed", 80, PT_ - 3.81, lx=8.0, ly=-8.6)
s.wire(85.08, PT_ - 3.81, 85.08, PT_ - 7.62)
s.wire(85.08, PT_ - 7.62, 80, PT_ - 7.62)
s.junction(80, PT_ - 7.62)
s.wire(80, PT_ - 7.62, 80, PT_ - 11)
s.gnd(80, PT_ - 11)
s.text("Speed", 68, PT_ - 17.5, 1.3)
# ladder resistors to cathode / ground (RTOG1/RTOG2)
s.sym("R", "RTOG1", "1M", 60, PT_ - 3.81)
s.wire(60, PT_ - 7.62, 60, PT_ - 16)
s.wire(60, PT_ - 16, 30, PT_ - 16)
s.wire(30, PT_ - 16, 30, YT + 11)
s.wire(30, YT + 11, 100, YT + 11)
s.sym("R", "RTOG2", "1M", 40, PT_ - 3.81)
s.gnd(40, PT_ - 7.62, 90)
s.wire(40, PT_, 36, PT_)
s.wire(36, PT_, 36, YT)
s.wire(36, YT, t3["g"][0], YT)
# cathode 1.5k || 25+25u
s.wire(100, YT + 7.62, 100, YT + 11)
s.junction(100, YT + 11)
cathode_split_rc("RTOK", "1.5k", "CTOK", "25u+25u", 100, YT + 11)
# oscillator output: plate -> Intensity -> OPTO lamp -> shunts the mixing node
s.wire(100, PT_, 120, PT_)
s.sym("POT", "VRINT", "250k-L intens.", 120, PT_ + 3.81)
s.gnd(120, PT_ + 7.62)
op = s.opto("OPTO", "optocoupler", 148, PT_)
s.wire(125.08, PT_, 148 - 6.35, PT_)
s.wire(op["l2"][0], op["l2"][1], op["l2"][0] - 4, op["l2"][1])
s.gnd(op["l2"][0] - 4, op["l2"][1])
s.wire(op["p1"][0], op["p1"][1], op["p1"][0] + 4, op["p1"][1])
s.glabel("MIXG2", op["p1"][0] + 4, op["p1"][1], 0)
s.wire(op["p2"][0], op["p2"][1], op["p2"][0] + 4, op["p2"][1])
s.gnd(op["p2"][0] + 4, op["p2"][1])
s.glabel("MIXG2", MX + 6, MY, 0)
s.wire(MX + 6, MY, MX, MY)
# vibrato footswitch jack shorts the speed/ladder network when engaged (drawn
# as a simple stub to ground per the drawing's dashed VIBRATO PEDAL box)
s.jack("JVIB", "vibrato pedal", 16, YT + 30, mirror=False)
s.text("Vibrato pedal", 8, YT + 24, 1.2)

# ============================ PHASE INVERTER (LTP, V6) =================
XPI = 258
YPH = 100
YPB = 160
JY = 130
s.text("Long-tailed-pair phase inverter", 244, 70, 1.6)
s.wire(XD + 7.62, MY, 230, MY)
s.wire(230, MY, 230, YPH)
t6a = s.triode("V6A", "7025", XPI, YPH)
t6b = s.triode("V6B", "7025", XPI, YPB)
s.plate_load("RLA", "82k 5%", t6a["p"], "BP3")
s.plate_load("RLB", "100k 5%", t6b["p"], "BP3")
s.wire(XPI, YPH + 7.62, XPI, YPH + 10)
s.wire(XPI, YPH + 10, 250, YPH + 10)
s.wire(XPI, YPB - 7.62, XPI, YPB - 10)
s.wire(XPI, YPB - 10, 250, YPB - 10)
s.wire(250, YPH + 10, 250, YPB - 10)
s.junction(250, JY)
tl, tr = s.series_h("R", "RTAIL", "820", 244.5, JY)
s.wire(250, JY, tr, JY)
s.wire(238, JY, tl, JY)
s.junction(238, JY)
tl, tr = s.series_h("R", "RT2", "6.8k", 228, JY)
s.wire(tr, JY, 238, JY)
s.wire(tl, JY, 220, JY)
s.junction(220, JY)
s.sym("R", "RPRES", "1.6k", 220, JY + 3.81, lx=3.2, ly=2.0)
s.sym("POT", "VRPRES", "5k-L pres.", 220, JY + 3.81 + 7.62 + 3.81, lx=3.2, ly=2.0)
s.wire(220, JY + 7.62, 220, JY + 7.62 + 3.81)
s.gnd(220, JY + 3.81 + 7.62 + 3.81 + 3.81)
nl, nr = s.series_h("R", "RNFB", "56k", 206, JY)
s.wire(nr, JY, 220, JY)
s.wire(196, JY, nl, JY)
s.glabel("SPKR", 192, JY, 180)
# hot grid leak: JPI -> 1M -> hot grid
s.sym("R", "RGA", "1M", 238, JY - 8, lx=-9.4)
s.wire(238, JY - 4.19, 238, JY)
s.wire(238, JY - 11.81, 238, YPH)
s.junction(238, YPH)
# cold grid leak: JPI -> 1M -> cold grid
s.sym("R", "RGB", "1M", 234, JY + 8, lx=2.8)
s.wire(234, JY + 4.19, 234, JY)
s.junction(234, JY)
s.wire(234, JY + 11.81, 234, YPB)
s.wire(234, YPB, 250.38, YPB)
s.junction(234, YPB)
s.junction(250.38, YPB)
s.wire(230, YPH, 234, YPH)
s.wire(234, YPH, 238.38, YPH)
s.junction(234, YPH)
# PI plate-adjacent damping cap (CPID) across the two plates
teeA = YPH - 7.62 - 3.48
teeC = YPB - 7.62 - 3.48
s.junction(XPI, teeA)
s.wire(XPI, teeA, 272, teeA)
s.junction(XPI, teeC)
s.wire(XPI, teeC, 272, teeC)
s.junction(268, teeA)
s.junction(268, teeC)
s.wire(268, teeA, 268, teeA + 3.09)
s.sym("C", "CPID", "1000p", 268, teeA + 6.9)
s.wire(268, teeA + 10.71, 268, teeC)

# ============================ OUTPUT COUPLERS + 6L6GC ==================
cl, cr = s.series_h("C", "C1", ".05u", 284, teeA)
s.wire(272, teeA, cl, teeA)
s.wire(cr, teeA, 296, teeA)
s.wire(296, teeA, 296, 80)
cl, cr = s.series_h("C", "C2", ".05u", 284, teeC)
s.wire(272, teeC, cl, teeC)
s.wire(cr, teeC, 296, teeC)
s.wire(296, teeC, 296, 160)

XO = 320
s.text("Output pair — grounded cathodes, fixed bias", 300, 60, 1.5)
for gy, vref, glref, scref in [(80, "V7", "RGL1", "RSC1"), (160, "V8", "RGL2", "RSC2")]:
    s.wire(296, gy, XO - 7.62, gy)
    p = s.pentode(vref, "6L6GC", XO, gy)
    s.junction(302, gy)
    s.sym("R", glref, "220k 5%", 302, gy + 3.81, lx=3.0, ly=2.4)
    s.wire(302, gy + 7.62, 302, gy + 10.16)
    s.glabel("-55V", 302, gy + 10.16, 270)
    s.wire(p["g2"][0], p["g2"][1], p["g2"][0] + 6, p["g2"][1])
    s.sym("R", scref, "470 1W", p["g2"][0] + 6 + 3.81, p["g2"][1], rot=90, lx=-3.2, ly=-6.2)
    s.wire(p["g2"][0] + 6 + 7.62, p["g2"][1], p["g2"][0] + 6 + 11, p["g2"][1])
    s.glabel("BP2", p["g2"][0] + 6 + 11, p["g2"][1], 0)
    s.gnd(XO, p["k"][1])

# ---- output transformer -----------------------------------------------
s.sym("OT_PP", "TR2", "n/a", 352, 120, lx=-6.35, ly=-14.5)
s.wire(XO, 71.745, XO, 68)
s.wire(XO, 68, 343.11, 68)
s.wire(343.11, 68, 343.11, 114.92)
s.wire(XO, 151.745, XO, 148)
s.wire(XO, 148, 338, 148)
s.wire(338, 148, 338, 125.08)
s.wire(338, 125.08, 343.11, 125.08)
s.wire(343.11, 120, 334, 120)
s.glabel("BP1", 330, 120, 180)
s.wire(360.89, 117.46, 364, 117.46)
s.glabel("SPKR", 364, 117.46, 0)
s.wire(360.89, 122.54, 364, 122.54)
s.jack("JSPK", "spkr", 372, 120)
s.wire(364, 122.54, 366.92, 122.54)

# ============================ POWER SUPPLY ==============================
s.text("Power supply — silicon full-wave bridge off a single HT secondary (no tube rectifier); TR1 power, TR2 output (drawing's own designators)",
       196, 180, 1.4)
BY = 200
s.text("HT", 22, BY - 10, 1.3)
s.wire(24, BY - 4, 30, BY - 4)
s.sym("DIODE_SS", "D1", "1N4007", 34, BY - 4, lx=-2.0, ly=-5.4)
s.wire(24, BY + 4, 30, BY + 4)
s.sym("DIODE_SS", "D2", "1N4007", 34, BY + 4, lx=-2.0, ly=5.0)
s.wire(24, BY - 4, 24, BY + 4)
s.junction(24, BY)
s.glabel("HT_A", 18, BY - 4, 180)
s.glabel("HT_B", 18, BY + 4, 180)
s.wire(39.08, BY - 4, 44, BY - 4)
s.sym("DIODE_SS", "D3", "1N4007", 48, BY - 4, lx=-2.0, ly=-5.4)
s.wire(39.08, BY + 4, 44, BY + 4)
s.sym("DIODE_SS", "D4", "1N4007", 48, BY + 4, lx=-2.0, ly=5.0)
s.wire(44, BY - 4, 44, BY + 4)
s.junction(44, BY)
s.gnd(44, BY + 10)
s.wire(44, BY + 4, 44, BY + 10)
s.wire(53.08, BY - 4, 58, BY - 4)
s.wire(53.08, BY + 4, 58, BY + 4)
s.wire(58, BY - 4, 58, BY + 4)
s.junction(58, BY)
s.wire(58, BY, 62, BY)
s.junction(62, BY)
s.sym("C", "CF3", "20u 600V", 62, BY + 3.81)
s.gnd(62, BY + 7.62)
s.wire(62, BY, 62, BY - 3.5)
s.glabel("B_RES", 62, BY - 3.5, 90)
s.text("+460 V reservoir", 34, BY - 6, 1.1)
# choke to BP1
s.wire(62, BY, 68, BY)
s.sym("CHOKE", "L1", "CH.", 78, BY)
s.wire(88, BY, 94, BY)
s.junction(94, BY)
s.wire(94, BY, 94, BY - 3.5)
s.glabel("BP1", 94, BY - 3.5, 90)
s.sym("C", "CF4", "20u 600V", 94, BY + 3.81)
s.gnd(94, BY + 7.62)
s.text("+456 V", 88, BY - 6, 1.1)
# screen dropper BP1 -> BP2
s.wire(94, BY, 100, BY)
l, r = s.series_h("R", "RDSCR", "4700 1W", 106, BY)
s.wire(100, BY, l, BY)
s.wire(r, BY, 112, BY)
s.junction(112, BY)
s.wire(112, BY, 112, BY - 3.5)
s.glabel("BP2", 112, BY - 3.5, 90)
s.sym("C", "CF5", "20u 600V", 112, BY + 3.81)
s.gnd(112, BY + 7.62)
s.text("+430 V", 106, BY - 6, 1.1)
# BP2 -> RD1 56k -> node -> RD2 10k -> node (illustrative; BP3/BDRV/BD are
# DRIVEN anchors in netlist.cir, not literally derived through this chain —
# see the file header and notes.md for why the fan-out could not be resolved)
s.wire(112, BY, 118, BY)
l, r = s.series_h("R", "RD1", "56k 1W", 124, BY)
s.wire(118, BY, l, BY)
s.wire(r, BY, 130, BY)
s.junction(130, BY)
s.sym("C", "CF6", "20u 600V", 130, BY + 3.81)
s.gnd(130, BY + 7.62)
l, r = s.series_h("R", "RD2", "10k", 136, BY)
s.wire(130, BY, l, BY)
s.wire(r, BY, 142, BY)
s.junction(142, BY)
s.sym("C", "CF7", "20u 600V", 142, BY + 3.81)
s.gnd(142, BY + 7.62)
s.note('56k/10k dropper — illustrative; BP3/BDRV/BD are driven anchors (see header)')
# anchors, drawn as labelled taps off this illustrative chain
s.wire(130, BY, 130, BY - 8)
s.glabel("BP3", 130, BY - 8, 90)
s.wire(142, BY, 150, BY)
s.wire(150, BY, 150, BY - 8)
s.glabel("BDRV", 150, BY - 8, 90)
s.wire(150, BY, 150, BY + 8)
s.glabel("BD", 150, BY + 8, 270)

# mains / AC switch / fuse / pilot lamp
s.sym("PT", "TR1", "n/a", 40, 224, lx=-6.35, ly=-11.9)
sw_l, sw_r = s.switch("SW1", "AC", 20, 224 - 5.08)
s.wire(8, 224 - 5.08, sw_l, 224 - 5.08)
s.glabel("MAINS", 8, 224 - 5.08, 180)
fl, fr = s.fuse("F1", "3A", 30, 224 - 5.08)
s.wire(sw_r, 224 - 5.08, fl, 224 - 5.08)
s.wire(fr, 224 - 5.08, 40 - 8.89, 224 - 5.08)
s.wire(40 - 8.89, 224 + 5.08, 8, 224 + 5.08)
s.glabel("MAINS", 8, 224 + 5.08, 180)
s.text("Mains cord not drawn — annotation layer (layout.yaml)", 8, 232, 1.1)
s.wire(40 + 8.89, 224 - 5.08, 52, 224 - 5.08)
s.glabel("HT_A", 52, 224 - 5.08, 0)
s.wire(40 + 8.89, 224 + 5.08, 52, 224 + 5.08)
s.glabel("HT_B", 52, 224 + 5.08, 0)
lp = s.lamp("PL1", "pilot", 20, 236)
s.wire(lp["hi"][0], lp["hi"][1], lp["hi"][0], 231)
s.glabel("HTR_A", lp["hi"][0], 231, 90)
s.wire(lp["lo"][0], lp["lo"][1], lp["lo"][0], 241)
s.glabel("HTR_B", lp["lo"][0], 241, 270)
s.text("Pilot lamp — fed from the 6.3 V heater chain (layout.yaml twisted run)", 30, 238, 1.1)

# bias supply — not fully resolved from the scan (notes.md); shown here as an
# ideal source label only, matching netlist.cir's own treatment.
s.text("Bias supply — a filtered tap this drawing does not fully resolve; netlist.cir treats -55 V as an ideal source (notes.md)",
       196, 210, 1.3)
s.glabel("HT_B", 196, 220, 180)
s.wire(200, 220, 206, 220)
s.sym("DIODE_SS", "DBIAS", "Si", 210, 220, lx=-2.0, ly=-5.4)
s.wire(215.08, 220, 222, 220)
s.junction(222, 220)
s.sym("C", "CBIAS", "25u", 222, 223.81)
s.gnd(222, 227.62)
s.wire(222, 220, 230, 220)
s.glabel("-55V", 230, 220, 0)

s.write(OUT)
print(f"wrote {OUT}")
