# AA864 — Blackface Bassman-style

Two amplifiers have carried the Bassman name. The first was a tweed combo that
guitarists took over, ending in the 5F6-A: four ten-inch speakers, a
cathode-follower tone stack and the circuit Marshall's first head was built
around. The AA864 is the other one. Black Tolex, a **piggyback head** over its own
cabinet, solid-state rectification, fifty watts, and a front panel that says
**Bass Instrument** on one channel — Fender going back to building a bass amplifier
after the name had spent a decade attached to a guitar classic. The two share the
word on the panel and nothing else. The title block reads
`FENDER MODEL "BASSMAN-AMP AA864" P/B`.

What the AA864 does inherit, it inherits from the blonde piggyback it replaced —
the [6G6-B](/amps/6g6b/), also documented here: the two-channel Bass/Normal
split, the solid-state supply and the long-tailed-pair inverter all carry across
the changeover, and the preamp is redesigned around them. A year later the
[AB165](/amps/ab165/) reworks the Bass channel again on the same chassis.

Six bottles do the work: three **7025**s (the low-noise 12AX7 the sheet calls for),
a **12AT7** phase inverter, and a **6L6GC** pair. The three 7025s hold six triode
sections and the circuit uses five, because the two channels are not built the
same.

## Two channels, two different amplifiers

**Normal** is the ordinary blackface channel: two gain stages either side of the
familiar two-knob stack. **Bass Instrument** gets a third gain stage and a tone
network with an extra rung — the channel the amp is named for, and the one the
panel puts first.

**Normal.** Two jacks on 68 kΩ stoppers and a shared 1 MΩ leak → **V2a**
(100 kΩ plate load, 1.5 kΩ cathode, 25 µF bypass) → the blackface **treble/bass
ladder**: a 250 pF treble cap and a 100 kΩ slope resistor both off the plate, 0.1 µF
from the slope foot to the treble-lug/bass junction, a 250 kΩ bass rheostat down
onto a 0.047 µF / 6.8 kΩ leg, output taken at the 250 kΩ treble wiper → a 1 MΩ
volume with a switched **120 pF Bright** cap across it → **V2b**, an identical
100 kΩ / 1.5 kΩ stage → 220 kΩ into the inverter's grid node.

**Bass Instrument.** Same input arrangement into **V1a**, then the same ladder
scaled for the low end. The treble cap is still 250 pF, but it feeds a **250 kΩ
series resistor above a 50 kΩ treble pot**, so the control moves a small window of
a much larger divider. The slope resistor is still 100 kΩ, and off its foot hang
**three** 0.1 µF capacitors where the Normal channel has a 0.1 and a 0.047: one
across to the treble-lug/bass junction, one down into the grounded foot, and a
third that the **Deep** switch parallels with it — doubling the capacitance the
bass control works against. The rheostat in the ladder is a **10 kΩ** pot rather
than 250 kΩ, and there is no 6.8 kΩ leg: the foot goes straight to ground. A
250 kΩ volume follows, then **V1b** (100 kΩ / 1.5 kΩ / 25 µF).

The extra stage is where the channel earns its name. V1b's plate hands 0.1 µF to a
**220 kΩ / 220 kΩ divider** with 0.001 µF across its foot — a deliberate 2:1 pad
that rolls off above about 1.5 kHz — and that feeds **V3b**, a third 100 kΩ /
1.5 kΩ stage whose cathode resistor is the only one on the sheet with **no bypass
capacitor**, and whose plate load carries **0.005 µF straight across it**, a corner
near 800 Hz. Attenuate, amplify again with local
degeneration, then roll the top off at the plate: gain restored without the
brightness that would come with it. V3b's plate then meets the Normal channel
through its own 220 kΩ.

## Phase inverter

Both channels' 220 kΩ mix resistors land on one node, and **500 pF** carries it into
the **12AT7 long-tailed pair** — 82 kΩ on the hot plate, 100 kΩ on the cold, both
5 %, from the +410 V rail; a 470 Ω resistor under the joined cathodes and a
**22 kΩ tail**; 1 MΩ grid leaks returned to the tail junction, which the chart puts
at +93 V under +95 V cathodes.

The tail does not go to ground. It returns to a **100 Ω** resistor, and the
amplifier's global feedback — **820 Ω** from the output transformer's secondary —
lands on the same node, so the feedback voltage develops across that 100 Ω. A
0.1 µF · 200 V capacitor carries the node to the cold grid, which takes its DC from
the tail junction through its 1 MΩ leak.

## Output

0.1 µF couplers into 220 kΩ · 5 % grid leaks returned to the **−44 V** bias line,
then 1.5 kΩ grid stoppers, into the **6L6GC** pair: cathodes to ground, screens off
the +420 V rail through 470 Ω · 1 W stoppers, plates printed at +420 V into the
**125A13A** transformer, whose centre tap the sheet marks +422 V, and out to the
cabinet's two speakers, with an EXT SPKR jack in parallel.

## Power

**No rectifier tube.** TR1 (125P7D; 125P7DX on the export model) runs 305-0-305 V AC
into two strings of three series silicon diodes — stacked for reverse voltage, not
for current — giving **+422 V** across two 70 µF · 350 V cans in series, balanced by
a pair of 220 kΩ · 1 W resistors. A **standby switch** passes that to the plate
rail, which feeds the output transformer's centre tap at the same **+422 V**; the
**125C1A choke** drops it to **+420 V** for the screens, 1 kΩ · 1 W
to **+410 V** for the inverter, and 4.7 kΩ · 1 W to the preamp rail, with a 20 µF ·
525 V can on each. The bias supply taps the same 305 V winding through 470 Ω · 1 W
and one diode into a 25 µF · 50 V can, then a 10 kΩ linear **bias adjust** over a
15 kΩ leg, out at −44 V.

## Reading against the printed chart

The drawing prints a full voltage chart — every value at ±20 %, read to ground
with an electronic voltmeter. Two rails are supplied to the simulation, the
+422 V plate rail and the +420 V screen rail either side of the choke; everything
below is solved through the drawing's own droppers.

Most of it lands close. The inverter rail solves to +410 V against a printed
+410 V. The screens sit at +419 V against +420 V. Every preamp plate solves to
+251 V — right on the Normal channel's printed +250 V, and 5–7 % above the Bass
channel's printed +235 V — with cathodes at +1.93 V against printed values of
+2.0, +1.8 and +1.9 V. The inverter reads +235 V and +229 V at its plates against
printed +220 and +205 V, with +89 V cathodes and a +87 V tail junction against
+95 and +93 V. The worst node is about 12 % out, inside the sheet's own
tolerance.

**One node is printed twice, differently.** The circuit sheet marks the preamp
rail — the node below the 4.7 kΩ · 1 W dropper — **+340 V**. The layout sheet
marks the same eyelet **+380 V**. Only one of them can be right, and the drawn
resistor says which: seventy volts across 4.7 kΩ is 14.9 mA, but the node's only
load is five 100 kΩ plate loads, and the sheets' own plate voltages price their
draw at 6.9 mA — a 32 V drop, which lands at +378 V. The entry carries the layout
sheet's **+380 V** and records the circuit sheet's +340 V beside it as the figure
that does not close. The simulation solves the node at +379 V.

## Tube models

The sheet's **7025** is a 12AX7 and uses that model. The **6L6GC** pair runs the
corpus's own 6L6GC model, fitted to the RCA 6L6-GC data sheet's Class A1
characteristics — so the ratings the load-line explorer draws over this circuit
are the 6L6GC's 30 W plate dissipation on a 500 V ceiling, which is the headroom
a +422 V plate rail is asking for.

This circuit is published as a **draft**. Its component values and voltage chart
are read from the published drawings and its operating point is solved against
that chart, but it has not been through the maintainer's review.
