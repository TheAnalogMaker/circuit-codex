# 6G6-B — Blonde Bassman-style

The middle circuit of the piggyback Bassman's three-revision run: a
50-watt head-and-cabinet rig that replaced the tweed 4x10 combo entirely.
Fender moved the Bassman name onto a genuinely different amplifier here —
two full input channels (Bass, Normal), each running its own two-stage
preamp and its own Bass/Treble/Volume network, mixing into a shared driver
stage before a long-tailed-pair phase inverter and a fixed-bias 5881 pair.
The 6G6 (late 1960) used a GZ34 tube rectifier; the 6G6-A (early 1961)
moved to solid-state rectification; the 6G6-B carried that forward with
further circuit changes through 1963, running in blonde Tolex until the
blackface AA864 piggyback head replaced it in 1964.

## Circuit walkthrough (short form)

**Bass channel**: two inputs (68k stoppers, 1M leak) → **V1A** (2,700 Ω
cathode, 220 kΩ plate off the shared +230 V rail, printed +135 V/+1.1 V) →
**V1B** recovery (100 kΩ cathode, *unbypassed* — no cap drawn, the deepest
local feedback in the preamp, printed +13.6 V) → a Bass/Volume network (25
kΩ-L Bass pot, 820 Ω foot, 250 kΩ-L Volume pot) whose wiper feeds the
shared driver stage directly.

**Normal channel**: two inputs → **V2A** (1,500 Ω cathode, 100 kΩ plate off
the same +230 V rail, printed +1.9 V) → a Treble/Bass network (350 kΩ/70 kΩ
tap Treble, 250 kΩ-A Bass) → **V2B** recovery (2,700 Ω cathode, 220 kΩ
plate off a dedicated +355 V rail, printed +190 V/+1.8 V) → a 1 MΩ-A
Volume pot → a 470 kΩ resistor into the shared driver stage's grid.

**Shared driver**: both channels' Volume outputs land on **V3A**'s grid
(100 kΩ plate off +230 V, printed +150 V) → the Bass channel's own 250
kΩ-A Treble control (the front panel's BASS/TREBLE/VOLUME group ahead of
the Bass jacks reads 25k-L/250k-A/250k-L, so this pot sits in the driver
bottle's signal path rather than beside the channel's other two knobs) →
**V3B** recovery (1,500 Ω cathode, 100 kΩ plate off +230 V, printed
+150 V/+1.3 V) → 470 kΩ + a 500 pF coupler into the phase inverter.

**Phase inverter**: long-tailed pair, 82 kΩ (hot) / 100 kΩ (cold) 5%
plates off a +410 V rail (printed +300 V/+280 V), both 1 MΩ grid leaks
returned to the tail junction. The shared cathodes sit 820 Ω above the tail
junction — printed +30.0 V at the cathodes, +28.0 V at the junction, a
2.0 V split that implies roughly 2.4 mA of combined tail current,
corroborating the 82k/100k plate currents within the chart's own tolerance.

**Output**: two 5881s, fixed-biased through 220 kΩ leaks from a −54 V
supply (grounded cathodes, no cathode resistor), 470 Ω 1 W screen
resistors off a +430 V tap, plates direct on +428 V.

**Power**: a centre-tapped HT winding feeds two three-diode series legs — a
solid-state full-wave rectifier; there is no rectifier tube in this circuit.
Filtered B+ is distributed as several separately-dropped taps rather than
one single reservoir chain: +430 V (screens), +428 V (plates), +410 V
(phase inverter), +355 V (Normal channel recovery stage), +230 V (shared
preamp rail, read independently beside both channels' input stages). A
small silicon diode off an AC tap, 1 kΩ/4,700 Ω dropping, a choke (TR2,
125C1A) and a 25/50 µF dual can produce −54 V for the output bias.

## Reading this drawing — what's solid, what's estimated

The E-FB drawing (both the board-layout and schematic pages) prints its own
title block reading "FENDER 'BASSMAN' LAYOUT / SCHEMATIC — MODEL 6G6-B" —
confirmed against the target amp before any value was read. Every rail,
every cathode value cited above, and both phase-inverter plate voltages are
read directly off the printed chart at a clean junction dot.

Two internal nodes are engineering estimates rather than printed figures,
flagged inline in `netlist.cir`/`voltages.yaml` and left `chart: null`:

- **V1B's own plate-load resistor.** Its cathode (100 kΩ, +13.6 V) is
  printed clearly; the resistor carrying its plate to a rail is not legible
  on the rendered drawing at the resolution available here. Modelled as
  220 kΩ off the shared +230 V rail, mirroring V1A.
- **V3A's cathode.** V3B's is chart-read (1,500 Ω, +1.3 V); V3A prints the
  identical +150 V plate off the identical 100 kΩ/+230 V leg but its own
  cathode figure is not itself printed. Mirrored from V3B rather than
  asserted as read.
- **The phase-inverter tail's return to ground.** The chart prints both
  ends of the 820 Ω shared-cathode resistor (+30.0 V / +28.0 V), but not
  the resistor that carries the tail junction the rest of the way to
  ground — the front panel's PRESENCE (25 kΩ-L) control likely sits in
  that leg, as it does on the corpus's other long-tailed-pair designs, but
  its exact position in this drawing was not traced. Modelled as a plain
  10 kΩ, sized so the ~2.4 mA the 820 Ω implies lands near the printed
  +28.0 V — an estimate, not a read value.

Two chart figures the simulated deck does not reach are worth naming here
rather than leaving to whoever reads the table. V1B's cathode is printed at
+13.6 V; the deck settles far below it, because the plate-load resistor
above that cathode is the estimate described just above and the estimate
sets the current. V2A's cathode is printed at +1.9 V with every part in that
stage read from the sheet, and the deck settles about a third under it. That
second disagreement is recorded, not explained — no arithmetic here resolves
it, and it is one of the reasons this entry is a draft.

**What this entry ships.** The circuit data, the redrawn schematic, and the
board drawing built from the E-FB layout page — each channel's Bass, Treble
and Volume network drawn in full, because on this sheet those parts mount on
the board rather than at the panel. The drawn wiring is proved electrically
equivalent to the simulated circuit.

The entry stays a draft while those two chart figures stand unresolved.
Neither is smoothed over above, and a verified badge is a maintainer's to
grant, not this entry's to claim.

## The Bass/Normal split, and why the driver bottle carries a Treble pot

This is a genuinely two-channel amplifier, not a single voice with a bright
switch: each channel gets its own complete two-stage preamp and its own
tone network, and they mix only after both have already been shaped. The
Bass channel's Treble control physically living inside the shared driver
bottle's own signal path (between its two triode sections) rather than
beside the channel's Bass and Volume pots is a printed fact of this
drawing, not a simplification — the front-panel silkscreen order
(Presence, Bass, Treble, Volume, then the Normal jacks; Bass, Treble,
Volume, then the Bass jacks) is what fixes which knob belongs to which
channel, and the schematic's own component placement is what shows the
Bass channel's Treble pot living downstream of the mixing point.

The Normal channel, by contrast, carries its Treble control in its own
first-stage network (350 kΩ/70 kΩ tap) before mixing — the two channels'
tone-shaping paths are not identical twins of each other, only broadly
parallel.
