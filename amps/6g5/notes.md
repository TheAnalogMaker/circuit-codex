# 6G5 — Brown Pro-style

Fender's biggest brown-Tolex combo: a 40-watt, two-channel amplifier built
around a pair of **6L6GC** output tubes and a single 15-inch speaker, produced
1960–1963 on the A-FJ drawing. Where the brown Deluxe ([6G3](/amps/6g3/)) is a
small amp learning fixed bias and a long-tailed-pair inverter, the Pro is the
same redesign applied to Fender's high-power circuit: **silicon-bridge
rectification** in place of a tube rectifier, **fixed, non-adjustable bias**,
and a genuine **tremolo** — read here directly off the drawing as a photocell
circuit, not the "harmonic vibrato" a secondary field guide labels it (see
below). The preamp bottles are marked **7025** on the drawing, the low-noise
selected version of the 12AX7.

## Signal path

**Two full channels.** Normal and Bright are drawn as mirror images, each with
two input jacks (a 68 kΩ stopper apiece, over a shared 1 MΩ leak) into a first
12AX7 stage — 100 kΩ plate load, 820 Ω cathode with a split 25 + 25 µF bypass,
printed **+170 V / +1.4 V** on both channels. From there each channel runs its
own **Bass/Treble** tone stack and Volume control into a **second** 12AX7
stage (100 kΩ plate load) before the two channels sum at a shared node — the
printed plate reads **+160 V** on channel 1 and **+120 V** on channel 2; the
drawing gives no reason for the asymmetry (different bias points on nominally
identical stages happen on hand-built amps of this era) and this archive
reports both rather than forcing them to match.

**The mixing/tremolo node.** Both channels' second stages land on one node
carrying the tremolo optocoupler (below) before a **driver** 12AX7 stage
(100 kΩ plate load, printed **+320 V**) that feeds the phase inverter. The
driver carries a sizeable local network around it (470 kΩ, two 220 kΩ resistors,
2500 pF) that this entry reads onto the BOM but does not model in the DC
netlist — see "What isn't modelled" below.

**Phase inverter and output.** A **long-tailed-pair** 12AX7 — 82 kΩ (hot) and
100 kΩ (cold) 5 % plate loads, printed **+315 V / +310 V**, an 820 Ω shared
cathode into a 6.8 kΩ tail — drives the **two 6L6GC** output tubes through
0.05 µF couplers. A 56 kΩ negative-feedback resistor from the speaker and a
5 kΩ-L Presence control land at the tail foot. The output tubes run **fixed,
non-adjustable bias**: grounded cathodes, 220 kΩ · 5 % grid leaks to the bias
line, and individual 470 Ω · 1 W screen stoppers off a shared 4.7 kΩ · 1 W
screen dropper.

## The tremolo is a photocell circuit, not harmonic vibrato

A field guide's summary for this model calls the tremolo "harmonic vibrato" —
but the drawing itself shows one 12AX7 phase-shift oscillator (Speed on a
4 MΩ-RA rheostat, 1.5 kΩ cathode with a 25 + 25 µF bypass, printed +120 V
plate / +1.5 V cathode) driving a **lamp facing a photoresistor**, the classic
Fender optocoupler, wired to shunt the channel-mixing node to ground —
Intensity sets how hard the lamp is driven. That is the same circuit family as
the tweed-era optical tremolo circuits, not the phase-mixed dual-triode network
"harmonic vibrato" names (compare the brown Deluxe's own *bias-vary* tremolo,
which is a third, different mechanism again — see [6g3](/amps/6g3/)). Per this
project's hard rule 1, the published drawing governs over a secondary
description where the two disagree; the field guide's date range and wattage
are used, its circuit-type label is not.

Electrically, an oscillator like this has no static operating point — it swings
around whatever its printed pins describe. This entry excludes it from the DC
netlist exactly as [ab763](/amps/ab763/) excludes its own tremolo oscillator,
and reports the printed pins for the record only (`voltages.yaml`, both
`chart: null`).

## Power

A single HT secondary feeds a **silicon full-wave bridge** (four diodes, no
tube rectifier) into a **+460 V** reservoir, filtered through a choke to
**+456 V** at the 6L6GC plates (output-transformer primary DCR omitted, as
throughout this corpus) and, through a shared 4.7 kΩ · 1 W dropper, **+430 V**
at the screens. A 56 kΩ + 10 kΩ divider steps that down toward the phase-
inverter and driver supply (**+320 V / +315 V / +310 V** printed at those
stages). Fixed bias reads **−55 V** off a tight, rotated hand-lettered label
beside the two output-stage 220 kΩ grid leaks — the sheet carries no separate
bias test point the way the rail voltages are individually called out, so this
figure is read with a wider margin than the horizontal prints (flagged in
`voltages.yaml`).

## What isn't modelled, and why this entry is draft

This is a dense, hand-lettered two-channel drawing, and three things kept this
entry from earning `verified`:

- **The preamp, driver and phase-inverter supply taps.** The drawing prints a
  4.7 kΩ-1W shared screen dropper (read and modelled as a real resistor — the
  screens node solves close to its printed +430 V) and, past that, a 56 kΩ-1W
  + 10 kΩ pair descending toward the phase-inverter/driver supply — but not
  which stages' currents that pair actually carries. Chaining every
  downstream stage (PI + driver + all four preamp triodes) through it the way
  this corpus derives other amps' rails collapsed the node to a quarter of its
  printed value: real Fender dropper chains this narrow only carry one or two
  light taps, not five stages' combined current, so the drawing's tap
  structure past the screens must fan out in a way this scan didn't resolve.
  `netlist.cir` therefore DRIVES the phase-inverter supply (BP3), the driver
  supply (BDRV) and the shared preamp rail (BD) directly, each chosen to land
  its own stage near its printed plate reading — anchors, not derivations, in
  the same spirit as `ab763` driving its BC node directly rather than deriving
  it through the dropper above it. PI plates gate at a normal 20% against
  their anchor; the driver and preamp-stage nodes are informational, because
  an anchor chosen to fit isn't independent evidence for the fit.
- **The driver stage's local feedback network.** The 470 kΩ / 220 kΩ / 2500 pF
  network around V5 is read onto the BOM but not modelled — the netlist gives
  it a plain 100 kΩ-plate/820 Ω-cathode stage instead, one more reason its
  plate reading is informational rather than gated.
- **The −55 V bias figure's own confidence.** Every other rail on this sheet
  is printed horizontally, in the same lettering size as the component values
  around it. The bias figure is a small rotated label with no dedicated test
  point, which this archive reads as "−55 V" but flags rather than treats as
  equal-confidence with the rest of the chart.

None of this is a claim that the circuit is *wrong* — the well-attested part of
the chain (B+1, the screens node, the phase-inverter plates, the fixed-bias
grid leaks) simulates close to its printed figures. It is a claim that this
entry has not yet earned `verified`, per this project's hard rule 4: that
status is set by CI plus maintainer review once the remaining structure is
resolved (most likely against a second copy of this drawing or the companion
6G5-A revision), not asserted ahead of the evidence.

## Seven bottles, five noval sockets

The chassis carries **five 7025s, not seven**. The published layout sheet's own
socket row draws five noval sockets alongside the two 6L6GC octals, and the
denser schematic page — where each triode half is drawn where the signal needs
it rather than where the socket is — is easy to read as seven. Each
preamp/driver/inverter/oscillator function maps onto its own socket: V1 carries
both Normal stages, V2 both Bright stages, V3 the tremolo oscillator (excluded
from the DC model), V5 the driver and V6 the phase inverter.

The board diagram's wiring is proved electrically equivalent to the simulated
netlist within the documented DC scope, so this entry's layout carries a
verified wiring claim. Outside that scope, by declaration: the driven BP3 /
BDRV / BD anchors, both channels' tone stacks, the oscillator's own
phase-shift ladder and the driver's local feedback network. Those three
networks are drawn on the schematic but not placed on the board diagram —
schematic-only, the same convention this corpus's other two-knob entries
follow. None of that lifts the entry past **draft**: a wiring-equivalence
proof is a claim about connectivity, not about the supply topology and
component values still unresolved above.

## Lineage

The 6G5's predecessor is the narrow-panel tweed Pro, the **5E5-A**, which this
corpus documents — and the metadata carries the derivation edge. The brown
circuit keeps the tweed Pro's 40 W-class output pair and its Presence control,
and replaces the tube rectifier with a silicon bridge, the split-load cathodyne
with a long-tailed pair, and the single channel with two plus tremolo. It is
the same shape of redesign the 6G3 applies to the tweed Deluxe. Behind the
5E5-A stand the earlier tweed Pros, the 5C5 and 5D5, which are history-tier
entries rather than documented circuits.
