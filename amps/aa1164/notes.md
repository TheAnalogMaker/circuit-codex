# AA1164 — Blackface Princeton Reverb-style

The reverb-equipped blackface Princeton: a 12-watt, single-channel amp with tube
reverb and a genuine tremolo, running a fixed-biased pair of 6V6GTs behind a
**split-load phase inverter**. It was introduced in 1964 alongside the
reverbless AA964 and carried blackface cosmetics through 1967. Six controls —
Volume, Treble, Bass, Reverb, Speed, Intensity — and a **5U4GB** rectifier
rather than the GZ34 of its larger siblings. The preamp bottle is marked
**7025** on the drawing, the low-noise selected version of the 12AX7.

## Signal path

**Preamp.** Two inputs, each through its own 68 kΩ stopper onto a shared 1 MΩ
grid leak → first 12AX7 stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF
bypass) → a treble-bass tone
stack (250 kΩ treble and bass, a 100 kΩ slope resistor, 6.8 kΩ bleed, 250 pF,
0.1 µF and 0.047 µF caps) and a 1 MΩ Volume → a second identical 12AX7 stage.
There is only one channel; everything the amp does happens in this one chain.

**The tone stack, as the sheet wires it.** The AA1164 draws the same two-knob
ladder as the AA964 it descends from — not the textbook redrawing of the same
parts — and the schematic here follows the sheet (re-read at lug level
2026-08-03): the 250 pF and the 100 kΩ slope both leave the plate node; the
0.1 µF runs from the slope foot to the node shared by the treble pot's
**lower lug** and the bass pot; the bass pot is a **rheostat** above the
0.047 µF/6.8 kΩ foot (the factory layout mounts the 6.8 kΩ right on the bass
pot, its far lead grounded to the case); and the stack's output is the treble
pot's **wiper alone**, into the Volume control. The tone-stack lab plots this
circuit with that wiring.

**Reverb.** After the second preamp stage the signal splits. A 500 pF cap taps
the dry signal off to a **12AT7 with both triodes in parallel** (2.2 kΩ shared
cathode) that swings the 125A20B transformer and the spring tank. The return
comes back through a **12AX7 recovery stage** (220 kΩ grid resistor, 100 kΩ
plate, 1.5 kΩ cathode) and the 100 kΩ Reverb control. Dry and wet are then
summed by a pair of resistors straight onto the next grid: 3.3 MΩ for the dry
path (with a 10 pF cap across it to keep the top end) and 470 kΩ for the reverb.

**Driver.** The mixed signal drives a third 12AX7 stage with a 100 kΩ plate load
and a two-part cathode: 1.5 kΩ bypassed by 25 µF, sitting on an unbypassed
**47 Ω**. That 47 Ω is where the negative feedback lands — a 2.7 kΩ resistor
back from the speaker — so the whole loop closes on a cathode rather than on the
inverter.

**Tremolo.** A 12AX7 phase-shift oscillator (Speed on a 3 MΩ control) does not
touch the audio path at all. Its output is coupled through the **250 kΩ
Intensity** control directly onto the **−34 V bias line** feeding the output
tubes' grid leaks, so the tremolo works by rocking the output stage's bias up
and down. That is a different mechanism from the optocoupler tremolo of the
larger blackface amps, which shunts a preamp grid to ground instead.

**Phase inverter and output.** A single 12AX7 triode wired as a **split-load
(cathodyne) inverter**: 56 kΩ in the plate, 1 kΩ plus 56 kΩ in the cathode, and
a 1 MΩ grid leak returned to the junction of those two cathode resistors, which
is what sets the stage's bias. Plate and cathode feed the two **6V6GT** grids
through 0.1 µF caps. The output tubes are fixed-biased at **−34 V** through
220 kΩ 5% leaks; their screens tie straight to the supply with no screen
resistors, and the 125A10B output transformer drives the speaker and a parallel
external-speaker jack.

## Power

340-0-340 V (power transformer 125P1B) → **5U4GB** → **+420 V** at the reservoir,
which is also the output transformer's centre tap → a 1 kΩ · 1 W dropper →
**+400 V** for the 6V6 screens and the reverb driver → 18 kΩ · 1 W → **+320 V**
→ 18 kΩ · 1 W → **+240 V** for every preamp plate load and the phase inverter.
The 6V6 plates read **+410 V**, ten volts under the centre tap they hang from.
A separate negative supply — a 100 kΩ 5% feed off the HT winding, a silicon
rectifier, a 25 µF can and a 22 kΩ bleeder — provides the **−34 V** fixed bias.

Nothing taps the +320 V node except its own filter capacitor, which is why the
two 18 kΩ droppers show identical 80 V drops on the printed chart.

## What sets it apart

Compared with the reverb-and-tremolo blackface amps above it, the AA1164 makes
three different choices.

The phase inverter is a **split-load stage rather than a long-tailed pair**. A
cathodyne has no voltage gain of its own, so all the drive for the output tubes
has to come out of the preamp ahead of it, and the two 6V6 grids are fed from
one triode instead of two.

The tremolo **modulates the output stage's bias** instead of shunting a preamp
grid through an optocoupler. Its depth therefore depends on where the output
tubes are biased rather than on how much signal is at a grid.

The feedback returns to a **driver cathode over a 47 Ω resistor** rather than to
the phase inverter. With only 47 Ω of unbypassed cathode resistance to work
against, the loop is a shallow one.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to ground
with an electronic voltmeter. The simulation takes only the +420 V reservoir as
given and solves the 1 kΩ and both 18 kΩ droppers, so the +400 V screen rail, the
+320 V node and the +240 V preamp rail are results rather than assumptions — and
they land 1.9 %, 2.4 % and 3.2 % from the chart. Below them the preamp plates sit
at +161 V against a printed +160 V, the reverb-driver cathode at +8.0 V exactly
on the chart, and the split-load inverter's three nodes no more than 12 % from
their printed +200 V / +50 V / +49 V.

One node is set aside. **The tremolo oscillator** shares a bottle with the phase
inverter, and its printed pins (+260 V plate, +2.4 V cathode) are the running
average a meter reads while it swings, set by grid-leak detection rather than by
a static operating point. It is reported rather than fitted to the chart. Its
plate load draws about half a milliamp from the screen rail, so leaving it out
accounts for roughly half a volt of the margin by which the three supply nodes
read high.

Every gated node verifies against the printed chart within the drawing's own
±20 % convention — the worst 11.5 % off — with the tremolo oscillator set aside
above as a documented exclusion rather than force-fitted to the chart.
