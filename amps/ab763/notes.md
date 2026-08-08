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
250 pF · 0.1 µF · 0.047 µF caps) and a 1 MΩ volume → the mixing resistor into
the phase inverter.
No reverb, no tremolo.

**Vibrato channel.** Input stage as above → the identical tone stack, part for
part (with a 47 pF bright cap across the volume pot, top lug to wiper) and a
1 MΩ volume → a second 12AX7 stage (100 kΩ plate, 820 Ω cathode) → the reverb
and tremolo section.

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
Deluxe (the [6G3](/amps/6g3/)) rather than from any tweed, along with that amp's
long-tailed-pair inverter, GZ34 rectifier and negative-feedback loop.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to ground
with an electronic voltmeter. The simulated DC operating point tracks it across
the modelled stages: the reverb-driver plate lands at +414 V against a printed
+410 V, the phase-inverter plates and the +77 V / +75.5 V tail fall within a tenth
of the chart, and the 6V6 screens sit at +415 V with their grids on the −35 V bias
line. Two nodes are reported for information only:

- **The two channel-input plates.** Their supply rail is shared with the tremolo
  oscillator, a phase-shift oscillator that has no static operating point and so is
  left out of the DC solution. With that load absent, the rail runs above its
  loaded factory value and the two input plates read high — so the printed
  +180 V / +170 V are shown for reference rather than compared.

- **The tremolo oscillator.** Its printed pins (+270 V plate, +2.1 V cathode) are
  the running average a meter reads while it swings, set by grid-leak detection.
  Solved as a quiescent stage, the 220 kΩ / 2.7 kΩ node sits near +200 V — about a
  quarter below the printed +270 V — so it is reported rather than fitted to the
  chart.

Every gated node verifies against the printed chart within the drawing's own
±20 % convention — the worst sits about a tenth off — with the tremolo oscillator
and the two shared-rail input plates set aside above as documented exclusions
rather than force-fitted to the chart.
