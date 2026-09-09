# 5F8-A — High-power Tweed Twin-style

The last tweed Twin, and the circuit that sets the shape of every Twin after
it: the 5F6-A's front end and long-tailed-pair inverter driving **four** 5881s
in two parallel pairs instead of two, on a supply stiff enough to hold them.
Two channels of two jacks feed a 12AY7; a 12AX7 stage direct-coupled to a
cathode follower drives the treble/middle/bass stack; a second 12AX7 splits the
phase; and the output quartet runs fixed-bias at −41 V with 470 Ω 1 W screen
resistors and a 1.5 kΩ stopper bridging each pair's grids. A GZ34 rectifies,
a choke follows the reservoir, and a standby switch stands ahead of both.

## Circuit walkthrough (short form)

Bright and normal channels, two jacks each (68 kΩ stoppers, 1 MΩ leaks) →
**V1** 12AY7 (100 kΩ plates, shared 820 Ω cathode with 250 µF bypass) →
0.02 µF couplers → 1 MΩ volume pots (100 pF bright cap) → 270 kΩ mixers →
**V2A** 12AX7 (100 kΩ plate, 820 Ω cathode, unbypassed) → **V2B cathode
follower, DC-coupled** (100 kΩ cathode load) → TMB tone stack (56 kΩ slope,
250 pF treble, two 0.02 µF; 250 kΩ/1 MΩ/25 kΩ pots) → 0.02 µF →
**long-tailed-pair PI**: 82 kΩ and 100 kΩ 5% plates, 470 Ω + 10 kΩ tail, both
1 MΩ grid leaks returned to the tail junction, 47 pF across the plates, 0.1 µF
holding the second grid at the tail foot → two 0.1 µF couplers → **four 5881s
in two parallel pairs**, fixed-biased at −41 V, into the 45268 output
transformer and two speakers, with 56 kΩ of negative feedback returning to the
tail foot alongside the 5 kΩ presence pot and its 0.1 µF wiper cap.

Power: 300-0-300 (PT 7993) → GZ34 → standby → **+397 V** plates (two 20 µF
cans) → choke (14684) → **+395 V** screens → 4.7 kΩ 1 W → **+355 V** phase
inverter (20 µF) → 10 kΩ 1 W → **+295 V** preamp (8 µF). Bias supply: selenium
rectifier, 15 kΩ/56 kΩ, two 8 µF/150 V cans → **−41 V**.

## The output stage, as the drawings wire it

The four bottles are **two parallel pairs**, not two push-pull pairs, and the
distinction is the whole circuit:

- Each phase of the inverter drives one pair through **one** 0.1 µF coupler
  and **one** 220 kΩ grid leak. The leak hangs on the coupler node, which is
  the first bottle's grid.
- The **1.5 kΩ stopper stands between the pair's two grids**, not in series
  with the coupler. On the factory board it is a single resistor bridging one
  socket's grid pin to the next socket's — which is exactly what the schematic
  draws, and what a builder wiring from the layout sheet will find.
- Both bottles of a pair share a plate connection to one end of the output
  transformer's primary, and both cathodes go straight to ground. Only the
  screens are individual: each has its own 470 Ω 1 W resistor to the +395 V
  node, and all four are socket-mounted rather than on the eyelet board.

## The tone network, as the drawings wire it

The published 5F8-A schematic and its factory layout sheet draw the same ladder
the 5F6 and 5F6-A print — not the textbook redrawing of these parts — and the
schematic and layout here follow the sheets:

- The 250 pF treble capacitor and the 56 kΩ slope resistor both leave the
  cathode-follower output.
- One 0.02 µF capacitor runs from the slope resistor's foot to the node shared
  by the treble pot's **lower lug** and the bass pot.
- The bass pot is a **rheostat** in series down the ladder, its wiper strapped
  into the treble-lug node.
- The other 0.02 µF runs from the slope foot to the middle pot's **wiper**, so
  the Middle control slides the capacitor's injection point along a 25 kΩ leg
  that never leaves the circuit.
- The stack's output is the treble pot's **wiper alone**, and the middle pot's
  foot runs straight to ground; the presence control sits at the phase-inverter
  tail instead.

## What this page does not claim

- **The secondary impedance.** The drawing prints the output transformer's
  part number (45268) and nothing about its windings, so no impedance is
  stated here and the amp carries no `iron` rating. Two speakers, no figure.
- **The power rating and the production years.** The sheet prints neither.
  The 80 W figure and the 1958–1960 span come from a separate published
  source, cited below, rather than from the drawing.
- **The bias supply's own voltages.** Only the −41 V line it delivers is
  printed, so the simulation drives that node as an ideal source rather than
  modelling the selenium rectifier and its 15 kΩ/56 kΩ divider.
- **The 100 pF bright cap.** It mounts on the bright volume pot's own lugs,
  inside the volume network the DC model abstracts, so it is annotated on the
  schematic rather than drawn as a two-terminal part.

## Where the model simplifies, and why

The DC deck drives +397 V at the reservoir and derives everything below it. Two
simplifications are worth stating plainly, because both are visible on the
sheet:

- **The choke** is modelled as 130 Ω of winding resistance, an estimate. The
  sheet prints 397 V on one side of it and 395 V on the other — the same 2 V
  the 5F6-A's sheet prints across the same part number, 14684.
- **The tail foot.** The drawing runs the 10 kΩ tail's foot to the presence
  pot's hot lug and grounds the pot's cold lug, with the 56 kΩ feedback
  resistor landing on the same foot. The DC model collapses that return to
  ground. The printed chart supports it: +27 V at the tail junction is 2.7 mA
  through 10 kΩ, and the two plate drops (355→230 through 82 kΩ, 355→225
  through 100 kΩ) imply 2.8 mA — so the foot is sitting at about zero, and the
  presence network is carrying no meaningful DC.

## Verification — against the printed factory chart

The I-EG drawing prints a full voltage chart, and simulation matches all
fourteen compared nodes (the 5881 screen carries no chart value and is
informational only): rails within 0.3 %, every tube pin within 7.4 %, against
the sheet's own stated convention of ±20 % read with an electronic voltmeter.

## Reading the chart off a scan

The I-EG sheet circulates in copies of very different quality, and its chart is
lettered small. Every voltage on this page was read from a 693 ppi capture
(6368 × 3218 for the schematic page); the widely mirrored copy carries the same
sheet at 1506 × 841, roughly 100 ppi, and its chart digits do not resolve.
Two figures come out wrong if you read them from the coarse copy anyway:

| node | coarse copy | 693 ppi |
|---|---|---|
| supply either side of the choke | +377 / +375 | **+397 / +395** |
| phase-inverter cathode | +22.5 V | **+28.5 V** |

The cathode is the one to check against your own copy, because the circuit
settles it without the drawing: it has to sit *above* the tail junction's
+27 V, since its current reaches that junction through the 470 Ω. A figure
below +27 V cannot be right, whatever the scan appears to say.

Component values and topology read cleanly off either copy. It is only the
chart that needs the resolution.
