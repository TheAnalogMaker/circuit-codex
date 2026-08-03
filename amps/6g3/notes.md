# 6G3 — Brown Deluxe-style

The bridge between the two most famous Deluxes. Built for the brown-Tolex years
of 1961–63, the 6G3 keeps the tweed Deluxe's 6V6GT pair and drops almost
everything else: cathode bias gives way to a **−26 V fixed-bias supply**, the
5Y3GT to a **GZ34**, the cathodyne inverter to a **long-tailed pair**, and the
single interactive volume pair to two properly separated channels — Normal and
Bright — each with its own volume and tone. It also gains a tremolo, and not the
usual kind: this one modulates the output tubes' bias directly. Every structural
choice here reappears two years later in the blackface Deluxe Reverb.

The drawing labels the first bottle **7025**, the low-noise selected version of
the 12AX7; the other two small bottles are 12AX7s.

## Signal path

**Two channels into one bottle.** Each channel takes two jacks, each on its own
68 kΩ stopper, over a shared 1 MΩ grid leak, and each drives one half of the
7025 — 220 kΩ plate load, and a single 1.5 kΩ cathode resistor with a 25 µF
bypass serving both halves. The one asymmetry is what names the channels: the
Normal side carries a **0.003 µF capacitor across its plate load**, bleeding
treble to the supply rail, and the Bright side does not.

**Controls.** Each channel then runs through a 0.02 µF coupler into a 1 MΩ-A
volume, with a 1 MΩ-A tone control hung across it — a 0.01 µF cap to ground on
the Normal channel, 0.02 µF on the Bright, each returning through a 500 pF mica
to the volume wiper. Both wipers meet at a pair of **220 kΩ mixing resistors**
that sum the channels into the driver grid.

**Driver.** The mixed signal meets a 12AX7 stage with a 100 kΩ plate load and a
1.5 kΩ cathode resistor bypassed by 25 µF. The plate load does not go straight to
the supply: it returns to the +270 V rail through a **15 kΩ decoupling
resistor**, and the 0.01 µF coupler to the phase inverter is taken from the
junction of the two.

**Phase inverter and output.** A 12AX7 **long-tailed pair** — 82 kΩ and 100 kΩ
5 % plate loads with a 100 pF cap between them, an 820 Ω resistor from the joined
cathodes to a tail junction, 6.8 kΩ onward to a node held near ground by a
1.5 kΩ resistor, and both 1 MΩ grid leaks returned to the tail junction. The
**56 kΩ negative-feedback resistor** comes back from the speaker terminal to that
same 1.5 kΩ foot, and a 0.1 µF · 200 V capacitor carries it into the cold grid.
From there two 0.1 µF couplers feed the **6V6GT pair**, whose cathodes are
grounded and whose grids sit on the −26 V bias line through 220 kΩ · 5 % leaks.

## The tremolo modulates the bias

The other half of the driver bottle is a **phase-shift oscillator**: 220 kΩ plate
load, 2.7 kΩ cathode with a 25 µF bypass, and a three-section
0.02 µF / 0.01 µF / 0.01 µF ladder on 1 MΩ returns, with a 3.5 MΩ-RA Speed
control setting the rate. Its output leaves the plate through 220 kΩ and 0.1 µF
into a 250 kΩ-L **Intensity** control — and that control sits *in the −26 V bias
line itself*, with a 0.05 µF · 200 V cap from its wiper to ground.

That is the whole trick. The output grids draw no grid current, so no DC flows
through the Intensity pot and the bias voltage arrives unchanged wherever the
knob is set; what varies is how much of the oscillator's swing rides on top of
it. The output tubes are pushed toward and away from cutoff in time with the
oscillator, so the amp's own gain does the wobbling. Fender would abandon the
idea in the blackface amps in favour of an optocoupler shunting a preamp grid.

## Power

A 125P2A power transformer with a 333-0-333 V secondary feeds the GZ34, which
delivers **+375 V** at the reservoir — the same node the output transformer's
centre tap sits on, and the node the tremolo oscillator draws its plate current
from. From there the rail steps down through the drawing's own droppers:
1 kΩ · 2 W to **+365 V** at the 6V6 plates and screens, 10 kΩ · 1 W to **+325 V**
at the phase-inverter plates, and 27 kΩ · 1 W to **+270 V** at the preamp, on
16 µF, 16 µF, 16 µF and 8 µF · 450 V cans. A separate 100 kΩ · 5 % feed off one
HT leg, a rectifier, a 25 µF · 50 V can and a 22 kΩ · 5 % bleeder make the −26 V
bias — fixed, with no adjustment trimmer.

## Lineage

The 5E3 is the amp this one replaces, and the differences are the point: the
brown Deluxe is where the line adopts fixed bias, a tube-rectified GZ34 supply,
a long-tailed-pair inverter and negative feedback. The blackface **AB763** Deluxe
Reverb inherits all four — its own −35 V bias supply and 12AT7 long-tailed pair
are this circuit's arrangement scaled up — which is why the 6G3, not any tweed,
is the Deluxe Reverb's direct ancestor.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to ground
with an electronic voltmeter. Only one node is driven in the simulation — the
+375 V reservoir — and every rail below it is *solved* through the printed
droppers, so the chart's supply voltages are predictions here rather than inputs:
the screen rail lands at +364 V against a printed +365 V, the phase-inverter rail
at +323 V against +325 V, and the preamp rail at +271 V against +270 V. The
stages track just as closely — the driver plate within 2 % of its printed +165 V,
both inverter plates within 2 % of +230 V and +225 V, and the +20 V / +18 V
cathode and tail junction within 6 %. The worst gated node sits about a
twentieth off, comfortably inside the drawing's own convention.

One stage is deliberately left out. The **tremolo oscillator** is a running
oscillator, and its printed pins — +205 V at the plate, +2.0 V at the cathode —
are the average a meter reads while it swings, set by grid-leak detection rather
than by a static bias point. It is reported here rather than fitted to the chart.
Because its plate load taps the driven reservoir node directly, leaving it out of
the solution costs nothing downstream: no other node on the chart is affected.
