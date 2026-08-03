# AA764 — Blackface Champ-style

The student amp that outlived every fashion: five watts, one 12AX7, one
single-ended 6V6GT, a 5Y3GT rectifier, and an 8-inch speaker in a small black
cabinet. The AA764 is what the tweed 5F1 became when Fender restyled the line in
1964 — the same two-stage preamp into the same cathode-biased single-ended output
stage, now with a **treble and bass tone stack**, a stiffer power supply, and a
gentler negative-feedback loop. It ran through the blackface years and carried on
under silverface cosmetics after 1968 with the output stage untouched.

## Signal path

Two input jacks (high and low) each sit behind a **68 kΩ** grid stopper and share
a **1 MΩ** leak to ground. From there:

**V1A** — 12AX7, **100 kΩ** plate load, **1.5 kΩ** cathode with a **25 µF**
bypass. Its plate feeds the tone stack directly; both stack legs start with a
capacitor, so no DC reaches the controls.

**Tone stack** — the blackface treble-bass network. A **250 pF** cap carries the
top end onto the **250 kΩ Treble** control; a **100 kΩ** slope resistor feeds a
**0.1 µF** cap into the junction below the treble pot and a **0.047 µF** cap into
the **250 kΩ Bass** control's lower leg, which returns to ground through
**15 kΩ**. The treble wiper hands the recovered signal to a **1 MΩ** Volume
control.

**V1B** — 12AX7, **100 kΩ** plate load. Its cathode resistor is **1.5 kΩ** with a
**25 µF** bypass, but it does not land on ground: it sits on a **47 Ω** leg, and
the **2.7 kΩ** negative-feedback resistor from the speaker jack lands on that same
junction. The feedback voltage develops across the 47 Ω and appears at the
cathode, which is why the bypass can spans only the 1.5 kΩ.

**Output** — a **0.02 µF** coupling cap into the **6V6GT** grid, held down by a
**220 kΩ** leak. The 6V6 is cathode-biased on **470 Ω · 1 W** with a **25 µF**
bypass, its screen wired straight to the second filter node with no stopper, and
its plate working into the **125A35A** single-ended output transformer.

## Power

320-0-320 V from the **125P1B** power transformer → **5Y3GT** full-wave rectifier
→ three **20 µF · 450 V** filter cans. The chain reads **+360 V** at the reservoir
(which also feeds the output transformer primary), **+350 V** after a **1 kΩ · 1 W**
dropper at the 6V6 screen, and **+330 V** after a **10 kΩ · 1 W** dropper at both
12AX7 plate loads. A 1 A slow-blow fuse and an AC switch sit ahead of the primary.

The 6.3 V heater winding is **single-ended**: one of its two green leads is
grounded at the chassis and the other feeds the pilot lamp and both heaters. Each
socket therefore takes one green feed and returns through chassis ground — pin 2
fed and pin 7 grounded on the 6V6GT, pins 4 and 5 strapped together and fed with
the centre tap at pin 9 grounded on the 12AX7. The 5Y3GT is directly heated from
the separate 5 V winding and sits outside that chain.

## On the board

The eyelet board runs the length of the chassis, power end at the left. The two
rail droppers sit in a three-node stack over the filter sections they split; then
the 6V6's **470 Ω · 1 W** cathode resistor with its **25 µF** can, the **2.7 kΩ**
feedback resistor, the **1.5 kΩ**/**25 µF** driver cathode pair and the **47 Ω**
divider leg, the **220 kΩ** grid leak sharing an eyelet with the **0.02 µF**
coupler, and the two **100 kΩ** plate loads meeting at a single **+330 V** tie
point. The tone capacitors follow — **250 pF**, **0.047 µF**, **0.1 µF** — beside
the **100 kΩ** slope resistor, and the board finishes with the two **68 kΩ** input
stoppers and the first stage's **1.5 kΩ**/**25 µF** cathode pair. Two parts are
chassis-mounted rather than on the board: the **1 MΩ** grid leak at input jack 1
and the **15 kΩ** bass leg at the Bass control.

## What changed from the 5F1

Three things, all visible on the chart:

| | 5F1 (tweed) | AA764 (blackface) |
|---|---|---|
| Tone controls | none | Treble and Bass, 250 kΩ each |
| Rails | +340 / +295 / +250 V | +360 / +350 / +330 V |
| Negative feedback | 22 kΩ onto the bare cathode | 2.7 kΩ onto a 47 Ω divider leg |

The stiffer supply matters most. In the tweed circuit the 6V6 screen sat 45 V
below its plate; here it sits at the same **+350 V** the plate does, and the
preamp plates run at **+330 V** rather than +250 V. The result is a louder,
firmer, later-breaking amp than the tweed Champ, with the tone stack giving back
some of the top end the extra headroom exposes.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to ground
with an electronic voltmeter. Driving the reservoir at its printed **+360 V** and
solving everything below it:

| Node | Chart | Simulated |
|---|---|---|
| Screen rail | +350 V | +354 V (1.1 %) |
| Preamp rail | +330 V | +332 V (0.5 %) |
| V1A plate / cathode | +200 V / +1.9 V | +218 V / +1.7 V |
| V1B plate / cathode | +205 V / +1.7 V | +220 V / +1.7 V |
| 6V6 cathode | +19 V | +22.6 V (19 %) |

Every node lands inside the drawing's own ±20 % convention, but the 6V6 cathode
lands close to the edge of it, and the reason is worth stating plainly: the tube
models here are fitted to the datasheet's 250 V operating point, and this amp runs
its 6V6 with both plate and screen near 350 V — far enough outside the anchor
region that the model draws richer current than a real bottle does. The preamp
plates read high for the mirror-image reason the tweed Champ's read high: the
models are datasheet-typical while Fender measured 1964 production tubes.

One value on the chart is deliberately not simulated. The drawing prints **+360 V**
at the reservoir and **+350 V** at the 6V6 plate; the 10 V between them is the
output transformer primary's winding resistance, which the drawing does not
publish. Rather than invent a figure to close the gap, the primary resistance is
left out and the plate is treated as the reservoir node.

The board-layout diagram's point-to-point wiring is machine-checked against this
same simulated netlist: every modelled part and every socket pin is proved to sit
on the node the circuit puts it on. The heater chain, the pilot lamp and the
transformer/rectifier AC side sit outside that check and are drawn as an
annotation layer.
