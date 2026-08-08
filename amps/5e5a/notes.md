# 5E5-A — Tweed Pro-style

The last and best-known tweed revision of Fender's Pro amp: a two-channel
12AY7 front end feeding a shared second gain stage, a passive James tone
network (Bass, Treble, Presence), a 12AX7 driver + split-load (cathodyne)
phase inverter, and a fixed-bias 6L6GB pair into a single 15-inch speaker.
Produced 1956–1960, it is the circuit that reintroduced negative feedback
(and the Presence control) after the immediately preceding 5E5 had removed
both. It is also the tweed 5-series' hottest front end: mic and instrument
each get their own gain stage before they are ever mixed, and the mixed
signal gets a *second* shared gain stage before the tone network — where the
5F6-A Bassman goes straight from its mixed node into a cathode follower, the
Pro interposes a full extra 12AY7 triode.

## Circuit walkthrough (short form)

Mic channel (68k stopper, 1M leak) → **V1A** 12AY7 ↘
Instrument channel (68k stopper, 1M leak) → **V1B** 12AY7 ↗ shared 820 Ω
cathode, 100k plates → 0.02 µF couplers → 1M MIC VOL / INST VOL pots → 270k
mixers → **V2**, a single shared 12AY7 triode (100k plate, 1.5k cathode; the
tube's second triode is idle) → the passive **James tone network** (1M Bass,
1M Treble) → **V3A** 12AX7 driver (100k plate, 1.5k cathode) → 0.02 µF →
**V3B split-load cathodyne**: 56k plate, 1.5k + 56k under the cathode, 1M
grid leak returned to the junction → 0.1 µF couplers from the cathodyne's
**plate and cathode** into 1.5k stoppers → **6L6GB pair**, fixed-biased
through 220k leaks, screens tied straight to the screens rail → output
transformer into the 15-inch speaker (with an external-speaker jack). A
100k negative-feedback resistor returns from the speaker/OT-secondary node to
a 5k **Presence** pot's hot lug (the pot's other lug grounded), its wiper
coupling through 0.1 µF into the **driver's (V3A) grid** — not the cathode,
where the 5F4 Super puts the same tap. It is an AC-only path sitting at about
0 V DC, so the DC netlist does not carry it either way.

Power: 5U4GA rectifier → **+390 V** (power-tube plates) → choke → **+385 V**
(screens) → rail dropper → **+300 V** (driver/PI) → rail dropper → **+250 V**
(preamp). A selenium rectifier supplies the **−32 V** fixed-bias rail.

## Two printed resistors the netlist does not model

The sheet prints two resistors around the shared second gain stage that the
DC model deliberately leaves out. A **100 kΩ** (RFB1) sits across V2's own
plate and grid; a **5 MΩ** (RBLEED) runs from V2's grid across to the driver's
grid, in parallel with the whole coupling + grid-leak path between them. Both
are legible enough to carry in the parts list. Modelled as plain DC resistors,
they collapse V2's operating point — its plate falls to about 8 V against a
printed +130 V — which contradicts the chart's own self-consistent class-A
reading, so at least one leg almost certainly sits behind a coupling cap this
copy of the drawing does not resolve. A DC block on the RBLEED path is the
likelier reading: it explains why a plate-referenced 100 kΩ still lets the
stage bias normally where a direct DC bridge does not. Both are therefore
carried as parts, not guessed into the netlist. Whether either leg is
capacitor-coupled wants the physical chassis or a sharper scan, and wants
settling before any board drawing wires them as hard connections.

The **James network's internal wiring** — which lugs the Bass and Treble pots
land on, beyond their existence and 1 MΩ value, both confirmed on the layout
sheet's panel row — is not resolved on this copy either. The region between
V2's plate and the driver's grid is the densest ink on the sheet: a 1 MΩ pot
flanked by a .01-400 and a .0005 cap, with the RFB1/RBLEED pair above it. The
schematic redraws the network in the standard James shape (treble peak cap +
pot, coupling cap, bass pot to ground) and captions it as such; its lug-level
wiring is illustrative rather than a chart-verified claim — the same status as
the rest of a draft circuit.

## Why the topology reads this way

The published tube-complement summaries for this amp are terse — "half
12AY7 / 12AY7 / half 12AX7" per channel plus "phase inverter: half 12AX7
(split load)" — but read as *stage chains* rather than per-channel tube
counts, they resolve to exactly the structure above: each channel keeps its
own first triode, both channels share the second 12AY7 stage and the 12AX7
driver, and the 12AX7's other half is the cathodyne. This corpus already
documents the same driver + split-load cathodyne shape (not a long-tailed
pair) on the 5F4 Super, built from the same Fender drafting office in the
same years, which is the strongest structural cross-check available here.

## What is legible on this copy of the drawing, and what is not

The J-EE sheet prints its voltage chart directly on the schematic rather than
as a separate table, and everything below is read from a 300 dpi capture of
the published PDF. Confidently legible, and used directly: the four
rail voltages (+390/+385/+300/+250), the bias rail (−32 V), V1's shared
cathode and both plates (+1.9 V / +130 V), V2's own plate and cathode
(+130 V / +1.9 V), the driver's cathode (+1.6 V), and the cathodyne's cathode
and 1.5k/56k junction (+58 V / +56.5 V — a consistent pair, implying ~1 mA
through both legs, exactly the shape this corpus's 5F4 Super chart shows for
the same stage). The James tone network's own component values (1M Bass, 1M Treble,
5K Presence) and the front-end/output-stage resistor network (68k stoppers,
1M leaks, 100k plates, 820 Ω shared cathode, 270k mixers, 56k cathodyne
plate, 1.5k+56k cathodyne cathode legs, 220k output grid leaks, 0.1 µF
output couplers) are also legible and match the values Fender reused across
this exact tweed lineup (5e3, 5f4 already in this corpus use the identical
figures for the identical roles).

**Not confidently legible**, and therefore carried at this corpus's standard
value for the identical role rather than guessed digit-by-digit: V2's own
plate and cathode *resistor values* (100k / 1.5k, matching 5f4's V2A — the
printed *voltages* they produce, +130 V / +1.9 V, are legible and gated), and
the two rail-dropper resistors between the screens node and the preamp node
(16k / 22k — the second figure matches 5e3's own front-end dropper exactly;
the first is derived from the printed +385→+300 V drop divided by the stage
currents the rest of the netlist already fixes, ≈5.2 mA, giving ≈16 kΩ). The
driver's and cathodyne's own plate voltages remain uncharted (`chart: null`
in voltages.yaml) — informational only, never gated. A maintainer with a
sharper scan or the physical chassis should confirm or correct these
three values, plus resolve the RFB1/RBLEED coupling question above, before
this circuit is considered for `verified`.

## Verification

`pipeline/verify_amps.py` passes all twelve chart-gated nodes within
tolerance (worst: BP4 at 8.3% against its 10% rail tolerance — the preamp
rail furthest from the not-confidently-legible RD1/RD2 dropper estimates;
next-worst PAY1/PAY2 at 8.0% and P2/K2 at ~10.5%, all against the 20% tube-pin
tolerance). K3A, the driver cathode, lands within 2.4% of its printed
+1.6 V. The cathodyne cathode/junction pair (KPI/JPI) — the two most
distinctively-shaped printed figures on this chart — land within 1%, the
strongest single piece of evidence that the driver+cathodyne reading above is
the circuit the sheet actually draws. As a draft circuit these are reported,
not gated; `verification.status` stays `draft` until a maintainer confirms
the remaining not-confidently-legible values and the RFB1/RBLEED coupling
question, per CONTRIBUTING.md.

`schematic.kicad_sch` redraws the circuit above from the same J-EE sheet set.
See its own header for what the drawing carries, and the caveat above for
what stays illustrative rather than chart-verified (the James network's
internal lug wiring).

## The board

The J-EE sheet set carries its own layout page ("FENDER 'PRO-AMP' LAYOUT
MODEL 5E5-A"), so the board diagram here is redrawn from a factory drawing
rather than derived from the schematic. It reads the way the sheet reads,
left to right: the bias supply and the fixed-bias 6L6GB support at the power
end; the driver and the split-load cathodyne in the centre, with the James
tone network beside them; then the single-triode second stage and the 12AY7
input pair. Column positions are this entry's own placement of that
sequence, not a dimensioned transfer of the sheet's grid.

The drawn point-to-point wiring is proved electrically equivalent to the
simulated circuit, so a lead traced across the board lands on the node the
netlist gives it. Two things on the drawing are illustrative rather than
proved. The James network's internal lug wiring is drawn in the simplified
arrangement described above. And the presence control and its
negative-feedback pair, along with V2's own plate-to-grid resistor and its
long grid return, are chassis wiring rather than board wiring: they are real
components, drawn on the schematic, and deliberately absent from the board
diagram.
