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
coupling through 0.1 µF into the **driver's (V3A) grid** — confirmed directly
on a sharper 2026-08-08 re-read of the same sheet (see "2026-08-08 re-read"
below); not modelled in the DC netlist either way (an AC-only tap at ~0 V DC).

Power: 5U4GA rectifier → **+390 V** (power-tube plates) → choke → **+385 V**
(screens) → rail dropper → **+300 V** (driver/PI) → rail dropper → **+250 V**
(preamp). A selenium rectifier supplies the **−32 V** fixed-bias rail.

## 2026-08-08 re-read (drawings session) — corrections and new finds

The drawings session fetched the same schematicheaven.net PDF directly and
read it at 300 dpi (title block re-verified: "FENDER PRO-AMP SCHEMATIC MODEL
5E5-A J-EE", matching `meta.yaml`'s citation) — sharper than the compressed
copy the data-core session had. Four findings against that first pass:

- **V2's own plate and cathode are confidently legible after all**: both read
  **+130 V** / **+1.9 V** — the identical printed figures as V1's, now gated
  in `voltages.yaml` (previously `chart: null`, informational). Coincidence of
  the design point, not a shared component: V2 runs a single triode on its
  own cathode resistor, not V1's shared 820 Ω.
- **The driver's cathode reads +1.6 V, not +1.4 V.** The netlist's simulated
  K3A was already 1.6 V and is now an exact chart match instead of 11.6% off
  — corroborating the re-read digit, not just the sharper scan alone.
- **The negative-feedback + Presence tap lands on the driver's (V3A) GRID,
  not the cathode.** The sheet draws a 100 kΩ resistor from the speaker/OT-
  secondary node to the Presence pot's hot lug, the wiper coupling through a
  0.1 µF/200 V cap into V3A's grid — in parallel with the coupling path from
  V2. The earlier draft's "by analogy with 5F4, lands on the cathode" guess
  is superseded by this direct read; not carried into the DC netlist either
  way (an AC-only tap at ~0 V DC).
- **Two more resistors are printed but not modelled.** A 100 kΩ (RFB1) sits
  across V2's own plate and grid; a 5 MΩ (RBLEED) runs from V2's grid across
  to the driver's grid, in parallel with the whole coupling + grid-leak path
  between them. Both read clearly enough to log in `bom.yaml`, but modelled
  as plain DC resistors in `netlist.cir` they collapse V2's operating point
  (P2 driven to ~8 V against the now-gated 130 V chart) — a contradiction
  with the chart's own self-consistent class-A reading, so at least one leg
  almost certainly sits behind a coupling cap this scan doesn't resolve
  (a DC block on the RBLEED path is the more likely reading — it would
  explain why a plate-referenced 100 kΩ, RFB1, still lets the stage bias
  normally while a *direct* DC bridge does not). Carried as an
  annotation-layer BOM finding, not guessed into the netlist. A maintainer
  with the physical chassis or a still-sharper scan should resolve whether
  either leg is capacitor-coupled before it is drawn as a hard connection in
  a board drawing's wiring layer.

The James tone network's own internal wiring (which lugs the Bass and Treble
pots land on, beyond their existence and 1 MΩ value, both confirmed on the
layout sheet's panel row) was **not** independently re-resolved at this
pass — the region between V2's plate and the driver's grid is dense on this
scan (a 1 MΩ pot flanked by a .01-400 and a .0005 cap, plus the RFB1/RBLEED
pair above), and disentangling which wiper feeds which lug without
over-fitting a "standard James ladder" onto ambiguous ink was judged lower
value than getting the rest of the circuit — already gated 12/12 non-informational
nodes green — right. `schematic.kicad_sch` draws the tone network in the
standard James shape (treble peak cap + pot, coupling cap, bass pot to
ground) captioned as such; treat its lug-level wiring as illustrative rather
than a chart-verified claim, same status as the rest of a `draft` circuit.

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

The J-EE sheet prints its voltage chart directly on the schematic rather
than as a separate table; the data-core session's copy was a compressed scan,
superseded at the drawings pass by a 300 dpi capture of the same PDF (see
"2026-08-08 re-read" below). Confidently legible, and used directly: the four
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

**Not confidently legible even on the 2026-08-08 sharper scan**, and
therefore still carried at this corpus's standard value for the identical
role rather than guessed digit-by-digit: V2's own plate and cathode
*resistor values* (100k / 1.5k, matching 5f4's V2A — the printed *voltages*
these produce, +130 V / +1.9 V, are now confirmed and gated, see above), and
the two rail-dropper resistors between the screens node and the preamp node
(16k / 22k — the second figure matches 5e3's own front-end dropper exactly;
the first is derived from the printed +385→+300 V drop divided by the stage
currents the rest of the netlist already fixes, ≈5.2 mA, giving ≈16 kΩ). The
driver's and cathodyne's own plate voltages remain uncharted (`chart: null`
in voltages.yaml) — informational only, never gated. A maintainer with a
still-sharper scan or the physical chassis should confirm or correct these
three values, plus resolve the RFB1/RBLEED coupling question above, before
this circuit is considered for `verified`.

## Verification

`pipeline/verify_amps.py` passes all twelve chart-gated nodes within
tolerance (worst: BP4 at 8.3% against its 10% rail tolerance — the preamp
rail furthest from the not-confidently-legible RD1/RD2 dropper estimates;
next-worst PAY1/PAY2 at 8.0% and P2/K2 at ~10.5%, all against the 20% tube-pin
tolerance). K3A, the driver cathode, now lands within 2.4% after the
2026-08-08 re-read corrected the printed digit from +1.4 V to +1.6 V — the
netlist's simulated value (1.6 V) was already there and unchanged throughout.
The cathodyne cathode/junction pair (KPI/JPI) — the two most
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
