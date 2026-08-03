# AA964 — Blackface Princeton-style

For fifteen years the Princeton was a Champ with a tone control: one small bottle
driving a single 6V6. The AA964 is what the name meant after that idea was
retired — a fixed-bias push-pull pair of **6V6GTs** at around 12 watts, a
treble-and-bass tone stack, and a tremolo that works by wobbling the output
tubes' own bias. Anyone reading the tweed 5F2-A's single-ended voltages onto a
blackface Princeton is reading the wrong amp; the two share a name and almost
nothing else.

Only two small bottles do the small-signal work. A **7025** — the low-noise
12AX7 the drawing calls for — carries both gain stages. A single **12AX7** is
split down the middle: one triode runs the tremolo oscillator, the other is the
whole phase inverter.

## Signal path

Two input jacks, each a 68 kΩ stopper on a shared 1 MΩ leak → **V1A**
(100 kΩ plate load, 1.5 kΩ cathode with a 25 µF bypass) → a **treble/bass tone
stack** (250 kΩ treble and bass controls, a 100 kΩ slope resistor, 6.8 kΩ bleed,
and 250 pF · 0.1 µF · 0.047 µF caps) and a 1 MΩ volume → **V1B**, an identical
100 kΩ / 1.5 kΩ stage → 0.022 µF into the inverter.

**Phase inverter.** One triode does it: a **cathodyne**, 56 kΩ above the plate
and 1 kΩ below the cathode into a 56 kΩ tail to ground, with the 1 MΩ grid leak
returned to that junction so the grid sits about a volt under the cathode. The
plate and the cathode each hand a 0.1 µF coupling cap to one output tube. It
provides no voltage gain — which is why V1B, the stage in front of it, has to be
a full gain stage rather than a mixer.

**Output.** The **6V6GT pair** is fixed-biased at **−34 V** through 220 kΩ · 5 %
grid leaks. The screens tie straight to the +415 V rail with no stopper
resistors, and the plates work into the 125A10B transformer. One global feedback
loop closes the amp: **2.7 kΩ** from the speaker back to a **47 Ω** tail sitting
underneath V1B's cathode resistor. That 47 Ω is the whole trick — V1B's 1.5 kΩ is
bypassed, so the returning signal has an unbypassed 47 Ω to develop across and
nothing else.

## Tremolo on the bias line

Half the 12AX7 runs a three-section **phase-shift oscillator** — 0.02 µF, 0.01 µF
and 0.01 µF against a 3 MΩ Speed control and two 1 MΩ resistors, with a 220 kΩ
plate load and a 3.3 kΩ bypassed cathode. What it does with its output is the
part worth knowing.

Bigger blackface amps spend a whole optocoupler on tremolo: a neon lamp and a
photoresistor that shunt a preamp grid to ground. The Princeton has no triode to
spare and no lamp. Instead the oscillator's output runs through 1 MΩ and a
0.1 µF cap into a 250 kΩ **Intensity** control whose wiper *is* the −34 V bias
line. The oscillator therefore pushes the output pair's grid bias up and down
directly, swinging the idle current of the whole output stage rather than
modulating a small-signal grid. A footswitch jack lands on the phase-shift ladder
and shorts it to ground to silence the oscillator.

At DC none of this matters: the oscillator reaches the Intensity control through
a blocking capacitor and the grid leaks draw essentially nothing, so no current
flows in the control and the bias line sits at the supply's −34 V wherever the
knob is set.

## Power

TR1 (125P1B), 340-0-340 V → **GZ34** → **+420 V** reservoir, feeding the output
transformer's centre tap and both 6V6 plates → 1 kΩ · 1 W → **+415 V** screens →
18 kΩ · 1 W → a filtered intermediate node → 18 kΩ · 1 W → **+290 V** for both
7025 plates and the inverter. Four 20 µF · 450 V cans do the filtering. The
negative supply is as plain as it gets: 100 kΩ from the high-voltage winding, a
silicon diode, a 25 µF · 50 V can with a 27 kΩ bleeder, and out through the
Intensity control at **−34 V**.

## Reading against the printed chart

The drawing prints a full voltage chart, every value at ±20 %, read to ground
with an electronic voltmeter. Only the +420 V reservoir is supplied to the
simulation; the screen rail and the preamp rail are solved through the drawing's
own droppers, so the printed +415 V and +290 V are results rather than inputs.
Both land close — the screen rail lands at +412 V against the printed +415 V, the
preamp rail about 2 % high — and every tube pin follows: both 7025 plates near
+195 V against a printed +190 V, their cathodes at +1.54 V and +1.56 V against a
printed +1.5 V, and the cathodyne at +232 V plate, +66 V cathode, +65 V junction
against a printed +220 / +65 / +63.8 V. The worst gated node is the inverter
plate, about 5 % off.

One node is reported rather than compared, because neither sheet prints a value
for it: the 47 Ω feedback tail under V1B. The filter node between the two 18 kΩ
droppers carries no value on the schematic, but the **layout** sheet labels that
can section **+370 V**, so it is compared like the other rails — and lands at
+354 V, about 4 % low.

**The tremolo oscillator is excluded from the DC solution.** Its printed pins —
+260 V at the plate, +2.4 V at the cathode — are the running averages a meter
reads while the circuit swings, set by grid-leak detection rather than by a
static operating point. Solving it as a quiescent stage would answer a question
the chart is not asking. Leaving it out costs the rest of the solve almost
nothing: its plate load returns to the screen rail, so the ~0.7 mA it would draw
would move that rail by well under a volt.

## What sits off the eyelet board

Four 20 µF · 450 V sections in one chassis-mounted can carry the whole supply, and
the last 18 kΩ dropper — the one between +370 V and +290 V — is mounted at the can
rather than on the board. Only the 1 kΩ and the first 18 kΩ sit on the board. The
negative supply has its own small terminal strip: 100 kΩ from the high-voltage
winding, a silicon diode, a 25 µF · 50 V can and a 27 kΩ bleeder, out through the
Intensity control. The 68 kΩ input stoppers and the 1 MΩ grid leak mount at the
input jacks, and the tone, volume, Speed and Intensity networks mount at their
pots. The board layout draws each of these where it actually lives.

This circuit is published as **verified**. The data core — values, netlist, chart
comparison, parts list — is complete and reads clean against the factory chart
(worst gated node 5.5 %, rails inside 2.4 %), and both drawings are here: a
redrawn schematic, and a board layout whose point-to-point wiring is
machine-checked electrically equivalent to the netlist. What that badge does
*not* claim is spelled out on the About page: it means simulation agrees with
the published chart, not that anyone measured this amplifier.
