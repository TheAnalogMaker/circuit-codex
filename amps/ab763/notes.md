# AB763 — Blackface Deluxe Reverb-style

The circuit most players picture when they think "Fender clean": a 22-watt,
6V6 combo with tube reverb and a genuine tremolo. The blackface Deluxe Reverb
arrives in 1963 on the AA763 drawing; the AB763 revision below is the one that
carried it from 1964 to 1967 and the one the model is remembered by. Two
channels share the output stage — a plain **Normal**
channel and a **Vibrato** channel carrying the reverb and the tremolo — feeding a
fixed-biased 6V6GT pair through a 12AT7 phase inverter, rectified by a GZ34. The
preamp bottles are marked **7025** on the drawing, the low-noise selected version
of the 12AX7; the reverb driver and phase inverter are **12AT7s**, chosen for the
current they can deliver.

## Signal path

**Normal channel.** Two inputs (each a 68 kΩ stopper on a 1 MΩ leak) → first
12AX7 stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF bypass) → a
treble-bass tone stack (100 kΩ slope, 250 kΩ treble and bass, 6.8 kΩ bleed, and
250 pF · 0.1 µF · 0.047 µF caps) and a 1 MΩ volume → a second 12AX7 stage
(100 kΩ plate load) → a 0.047 µF coupler and a 220 kΩ mixing resistor into the
phase inverter. No reverb, no tremolo.

**Vibrato channel.** Input stage as above → the identical tone stack, part for
part (with a 47 pF bright cap across the volume pot, top lug to wiper) and a
1 MΩ volume → a second 12AX7 stage (100 kΩ plate, 820 Ω cathode) → the reverb
and tremolo section.

**One cathode for two stages.** The two channels' second stages share a single
cathode network. The drawing marks both cathodes with a boxed **A** and draws the
820 Ω resistor and its 25 µF bypass once, at the Vibrato stage; the Normal stage
has no cathode resistor of its own, and the factory layout runs its cathode pin
to the Vibrato bottle's before the one lead goes on to the 820 Ω. That resistor
carries both triodes' current, and the +1.3 V the chart prints at each end of
the box is a single point.

## The tone stacks, as the sheet wires them

Both channels draw the same two-knob ladder the blackface AA964 prints — not
the textbook redrawing of these parts — and the schematic here follows the
sheet (re-read at lug level 2026-08-03):

- The 250 pF treble capacitor and the 100 kΩ slope resistor both leave the
  plate node; the three capacitors do all the DC blocking.
- The 0.1 µF runs from the slope foot to the node shared by the treble pot's
  **lower lug** and the bass pot — the treble pot's cold end sits on the far
  side of that capacitor, not on the slope foot.
- The bass pot is a **rheostat** above the fixed leg, and the 0.047 µF runs
  from the slope foot to the bass pot's foot, where the 6.8 kΩ bleed takes the
  network to ground.
- The stack's output is the treble pot's **wiper alone**, into the volume
  control. The tone-stack lab plots the normal channel with this wiring.

**Reverb.** The dry vibrato signal drives a **12AT7 with both triodes in
parallel** (2.2 kΩ shared cathode) into the 125A20B transformer and the spring
tank. The returned signal comes back through a **12AX7 recovery stage** (100 kΩ
plate, 820 Ω cathode) and meets the dry signal at the mix driver's grid: the
reverb through 470 kΩ from the 100 kΩ Reverb control's wiper, the dry signal
through 3.3 MΩ with 10 pF across it, and a 220 kΩ to ground holding the grid.
The mix driver has no cathode resistor of its own either: it shares the recovery
stage's 820 Ω and 25 µF, a connection the drawing marks with a boxed **E**.

**Tremolo.** One half of a 12AX7 is a phase-shift oscillator: its plate feeds a
0.02 µF / 0.01 µF / 0.01 µF ladder back to its own grid, and the 3 MΩ Speed
control, in series with 100 kΩ, tunes the ladder's middle to ground. The other
half, coupled directly to the ladder, drives a neon lamp in its plate circuit.
The lamp faces a photoresistor inside an **optocoupler**; the photoresistor
hangs from the Intensity control's wiper, and Intensity's other end takes the
vibrato channel's output just after the mix driver, so each flash shunts that
signal toward ground and the volume swings. The vibrato footswitch grounds the
oscillator's feed and stops it.

**Phase inverter and output.** The two channels meet at one node, each through
its own 220 kΩ mixing resistor — the Vibrato side after the mix driver's 0.1 µF
coupler — and a 0.001 µF capacitor carries that node into a 12AT7
**long-tailed pair** (82 kΩ and 100 kΩ
5% plate loads, a 470 Ω cathode resistor to a tail junction, 22 kΩ tail to
ground, both 1 MΩ grid leaks returned to that junction) splits the signal for the
**6V6GT pair**. The output tubes are fixed-biased at **−35 V** through 220 kΩ
leaks, with 470 Ω · 1 W screen resistors, and an 820 Ω negative-feedback loop
returns from the speaker to the inverter.

## Power

330-0-330 V (power transformer 125P33A) → **GZ34** → **+415 V** at the 6V6
plates (the output transformer centre tap sits at +420 V) → filter choke →
**+415 V** screens → a 10 kΩ dropper → **+325 V** at the phase-inverter plates
→ a second 10 kΩ dropper → the preamp rail every 100 kΩ-loaded 12AX7 stage
hangs from — both channels' input and second stages, the reverb recovery and the
mix driver — which the chart gives no voltage of its own. A separate negative supply — a 470 Ω · 1 W feed, a rectifier, 25 µF and
50 µF cans and a 10 kΩ divider — provides the **−35 V** fixed bias.

## Bias and lineage

Where the tweed Deluxe cathode-biased its 6V6s, the blackface Deluxe Reverb runs
a proper **negative-bias supply** — the recipe it inherited from the brownface
Deluxe (the [6G3](/amps/6g3/)) rather than from any tweed, along with that amp's
long-tailed-pair inverter, GZ34 rectifier and negative-feedback loop.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to ground
with an electronic voltmeter. The simulated DC operating point tracks it across
the modelled stages: the reverb-driver plate lands at +414 V against a printed
+410 V, the phase-inverter plates and the +77 V / +75.5 V tail fall within a tenth
of the chart, and the 6V6 screens sit at +415 V with their grids on the −35 V bias
line. The preamp rail is not held at a figure of its own: the chart prints none,
so it is solved through its 10 kΩ dropper from the +325 V node, and the six
preamp plates are a genuine check on the chart rather than an echo of it: they
land between +176 V and +180 V against printed figures of +170 V and +180 V. The
widest miss is at the two shared cathodes, boxes A and E, each +1.48 V against a
printed +1.3 V — about a seventh high.

One stage is reported rather than compared:

- **The tremolo oscillator.** Its printed pins (+270 V plate, +2.1 V cathode) are
  the running average a meter reads while it swings, set by grid-leak detection;
  a running oscillator has no static operating point, so it is left out of the DC
  solution. Its plate loads return to the +415 V node after the choke, which the
  solution holds at its printed value, so leaving it out moves no other reading.

Every gated node verifies against the printed chart within the drawing's own
±20 % convention, with the tremolo oscillator set aside above as a documented
exclusion rather than force-fitted to the chart.
