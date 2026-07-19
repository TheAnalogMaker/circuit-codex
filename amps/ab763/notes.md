# AB763 — Blackface Deluxe Reverb-style

The circuit most players picture when they think "Fender clean": a 22-watt,
6V6 combo with tube reverb and a genuine tremolo, built on the AB763 chassis that
ran from 1963 to 1967. Two channels share the output stage — a plain **Normal**
channel and a **Vibrato** channel carrying the reverb and the tremolo — feeding a
fixed-biased 6V6GT pair through a 12AT7 phase inverter, rectified by a GZ34. The
preamp bottles are marked **7025** on the drawing, the low-noise selected version
of the 12AX7; the reverb driver and phase inverter are **12AT7s**, chosen for the
current they can deliver.

## Signal path

**Normal channel.** Two inputs (each a 68 kΩ stopper on a 1 MΩ leak) → first
12AX7 stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF bypass) → a
treble-bass tone stack (250 kΩ treble and bass, 6.8 kΩ bleed, 250 pF and
0.047 µF caps) and a 1 MΩ volume → the mixing resistor into the phase inverter.
No reverb, no tremolo.

**Vibrato channel.** Input stage as above → tone stack (with a 47 pF bright cap
across the treble) and volume → a second 12AX7 stage (100 kΩ plate, 820 Ω
cathode) → the reverb and tremolo section.

**Reverb.** The dry vibrato signal drives a **12AT7 with both triodes in
parallel** (2.2 kΩ shared cathode) into the 125A20B transformer and the spring
tank. The returned signal comes back through a **12AX7 recovery stage** (100 kΩ
plate, 820 Ω cathode) and is blended back with the dry signal by the 100 kΩ
Reverb control, then handed to the mix driver that feeds the inverter.

**Tremolo.** A 12AX7 phase-shift oscillator (Speed on a 3 MΩ control) drives an
**optocoupler** — a neon lamp facing a photoresistor — that periodically shunts
the mix-driver's grid to ground, swinging the volume up and down. The Intensity
control sets how hard the lamp is driven.

**Phase inverter and output.** A 12AT7 **long-tailed pair** (82 kΩ and 100 kΩ
5% plate loads, a 470 Ω cathode resistor to a tail junction, 22 kΩ tail to
ground, both 1 MΩ grid leaks returned to that junction) splits the signal for the
**6V6GT pair**. The output tubes are fixed-biased at **−35 V** through 220 kΩ
leaks, with 470 Ω · 1 W screen resistors, and an 820 Ω negative-feedback loop
returns from the speaker to the inverter.

## Power

330-0-330 V (power transformer 125P33A) → **GZ34** → **+415 V** at the 6V6
plates (the output transformer centre tap sits at +420 V) → filter choke →
**+415 V** screens → a 10 kΩ dropper → **+325 V** at the phase-inverter plates
and the 820 Ω-cathode preamp stages → a second 10 kΩ dropper → the channel-input
rail. A separate negative supply — a 470 Ω · 1 W feed, a rectifier, 25 µF and
50 µF cans and a 10 kΩ divider — provides the **−35 V** fixed bias.

## Bias and lineage

Where the tweed Deluxe cathode-biased its 6V6s, the blackface Deluxe Reverb runs
a proper **negative-bias supply** — the recipe it inherited from the brownface
Deluxe (the 6G3) rather than from any tweed. That ancestry edge lands in the
lineage graph when the 6G3 does.

## Reading against the printed chart

The drawing prints a full voltage chart (its notice sets every value at ±20 %,
read to ground with an electronic voltmeter). Simulation of the DC operating
point tracks it across the modeled stages: the reverb-driver plate lands at
+414 V against a printed +410 V, the phase-inverter plates and +77 V/+75.5 V tail
fall within a tenth of the chart, the 6V6 screens sit at +415 V and their grids at
the −35 V bias line. Two nodes are left off the gated comparison and stated for
information only, for an honest reason each:

- **The two channel-input plates.** Their supply rail is shared with the tremolo
  oscillator. That oscillator is not part of the DC model (below), so the modeled
  rail runs above the loaded factory value and the two input plates read high.

- **The tremolo oscillator itself is excluded.** A phase-shift oscillator has no
  static operating point: its printed pins (+270 V plate, +2.1 V cathode) are the
  running average a meter reads while it swings, biased by grid-leak detection. A
  static solve of the printed 220 kΩ / 2.7 kΩ stage lands near +200 V — about a
  quarter off the printed +270 V — so modeling it as a quiescent stage would
  misrepresent it. It is documented here rather than force-fitted.

This page is a draft: its operating point is simulated and reads true against the
factory chart, but the circuit has not yet cleared the full verification pass.
