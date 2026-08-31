# GA-40 — Gibson GA-40 Les Paul-style, 5879 revision

Gibson's answer to the tweed combo, and almost nothing about it is a Fender idea.
Where Fullerton put a twin triode at the front of an amplifier, Gibson put a
pentode: one 5879 per channel, a nine-pin bottle whose data sheet is titled *for
audio-amplifier applications critical as to microphonics, leakage noise, and hum*
— a valve chosen for living six inches from a twelve-inch speaker. Where Fender's
tone stack sits between two gain stages, the GA-40 has no stack at all: a single
capacitor and a single control hang off the phase inverter's own anode, and that
one knob is the whole tone circuit. And where a blackface amplifier splits phase
with a long-tailed pair, this one uses a paraphase — a second triode fed a
divided copy of the first one's output — which was already old-fashioned when
this sheet was drawn and stayed in Gibson amplifiers long after.

The model number is not a wattage. A GA-40 makes about 15 W from a cathode-biased
pair of 6V6GTs.

## Which revision this is

The GA-40 ran from 1952 to late 1962, and the model number covers at least three
different amplifiers. The 1954 drawing is a genuinely different machine: three
octal 6SJ7s, a 6SN7 phase inverter, **three** 6V6GTs — two on the output and one
doing the tremolo — and a 5V4G rectifier. This entry documents the later, 5879
circuit: two 5879 pentodes, a 6SQ7 tremolo oscillator, a 12AX7 paraphase
inverter, two 6V6GTs and a 5Y3GT. Published accounts put that front end from 1956
and count no fewer than five Les Paul GA-40 variants across the model's life, so
the 5879 circuit itself covers more than one drawing.

This sheet is undated and carries no revision box, so this entry cannot say which
of those it is. The era bracket runs from the earliest year the cited sources put
the 5879 front end to the last year the model was catalogued: an outer bound over
the 5879 revisions, and labelled as one.

## The paraphase, and the arithmetic in it

The inverter is the part of this amplifier worth reading twice. Both 12AX7 halves
have 220 kΩ anode loads and share **one** 1 kΩ cathode resistor with a 20 µF
bypass. The driver half takes the mixed channel signal, and its anode drives the
first 6V6GT's grid through 0.02 µF. The 470 kΩ that leaks that grid does not go
to ground: it goes to the *other* triode's grid, where 7.5 kΩ carries on to
ground. That divider is the whole trick.

7.5 / (470 + 7.5) is 1 / 63.7. A 12AX7 working into a 220 kΩ load has very nearly
that gain, so the inverted half receives 1/64 of the first grid's swing and
returns it full size and upside down. The second 6V6GT's 470 kΩ leak *does* go to
ground, because its grid is not a divider tap. Two 470 kΩ resistors, doing two
different jobs, is what a paraphase looks like on a drawing.

The factory chart confirms the reading three ways over. Both anodes print +135 V
off a +280 V rail, which puts 0.66 mA through each 220 kΩ load; the two currents
together over one 1 kΩ resistor give 1.32 V against a printed +1.25 V. The
simulation lands +139 V and +1.28 V — inside 4 %.

## The output stage

Two 6V6GTs, cathode-biased on **one** shared 200 Ω resistor with a 20 µF bypass
and no bias supply anywhere in the amplifier. The screens are not dropped at all:
they sit straight on the post-choke supply node, the same node as the
output-transformer centre tap, which is why the chart prints +310 V for both. The
anodes read +305 V — the 5 V is the half-primary's own resistance, which this
corpus's netlists do not carry.

18.5 V over 200 Ω is 92.5 mA of cathode current for the pair, 46 mA each — and a
few of those milliamps are screen current, so the anodes take roughly 42 mA at
305 V. That is about 13 W of plate dissipation against a 12 W design-centre
rating: over the sheet, and exactly where every cathode-biased pair of the period
sat. The simulation reads 18.3 V at the cathode and 42.0 mA at the anode.

## Channel 1, and what the chart proves about the reading

Channel 1's 5879 has a 100 kΩ anode load and a 750 kΩ screen dropper, both off
the +265 V preamp rail, with the screen bypassed to ground by 0.05 µF and the
cathode on 3.3 kΩ with 20 µF across it. Every one of those values can be checked
against the chart that was measured through them:

| lettered resistor | with the printed voltage | gives |
|---|---|---|
| 100 kΩ anode load | anode +175 V from a +265 V rail | 0.90 mA of anode current |
| 750 kΩ screen dropper | screen +95 V from the same rail | 0.227 mA of screen current |
| 3.3 kΩ cathode resistor | both currents through it | **+3.72 V**, against a printed **+4.0 V** |

Two of the printed voltages and three resistors read off a low-resolution scan
predict the third printed voltage to 7 %. The values are right.

One detail of that channel is worth drawing carefully, because it is easy to
redraw wrong: the volume control is wired the unusual way round. The 0.01 µF
coupler does not land on the top of the 1 MΩ track — it lands on the **wiper**,
and the 470 kΩ mixing resistor leaves the top of the track, with the bottom end
grounded. Channel 2's own 1 MΩ volume is wired identically ahead of its 100 kΩ
mixing resistor, so it is the arrangement rather than a slip of the pen. It
still works as a volume control — the track below the wiper shunts the signal
and the track above it passes what is left — and at DC it makes no difference
at all, which is why the operating point is unmoved either way. The schematic
and the board layout draw it as the sheet draws it.

The simulation is the part that misses. See `voltages.yaml` — the corpus's 5879
model is a single-anchor fit at Va = 250 V, Vg2 = 100 V, and in this model form
the screen-current law has no plate-voltage term at all. Run at the screen
voltage this circuit uses it draws roughly a third of the screen current the real
valve does, so the 750 kΩ dropper leaves the screen at +130 V instead of +95 V
and the extra screen volts pull the anode down to +134 V. Anode −24 %, screen
+37 %, cathode +23 %, all outside the era's ±20 %.

Some of that gap is not the model's. The chart states its own convention —
*voltages to chassis with 20,000 O.P.V. meter* — and 20,000 ohms per volt on a
250 V range is 5 MΩ. Five megohms across a node fed through 750 kΩ draws 19 µA,
worth about 14 V of extra drop in that dropper, so the screen this chart printed
is meaningfully lower than the screen the amplifier ran. It is the most
meter-sensitive node on the sheet, and it is the node the simulation misses by
the most. The same loading is worth only about 3 V at the anode, behind 100 kΩ,
and nothing at all at the cathode.

What remains is a v0 tube-fit limitation of exactly the kind
`models/METHODOLOGY.md` warns about. It is one of the three reasons this circuit
is a draft, and it is left visible rather than hidden behind an ungated node.

## Channel 2 and the tremolo — read, not lettered

Both are on the drawing and neither is in the netlist or the parts list. This is
the honest edge of what the surviving scan supports, so here is what is legible
and what is not.

**Channel 2** takes the same input arrangement as channel 1 — two jacks, a 51 kΩ
series resistor each, one 1 MΩ leak — onto a second 5879 with a 2.2 kΩ cathode
resistor. Its anode load reads 510 kΩ, and its output runs through a ladder of
five 0.005 µF series capacitors with 1 MΩ shunts between them before reaching its
own 1 MΩ volume control and a 100 kΩ mixing resistor into the inverter grid. That
ladder is a progressive bass cut, and a published bench feature on a 1956 example
describes this channel's front end as carrying a filter network of the Vox
AC10/AC15 kind, which is what it is.

**The tremolo** is a 6SQ7 phase-shift oscillator with 510 kΩ resistors in its
anode chain, a 500 kΩ Frequency control and 0.01 µF / 0.05 µF ladder capacitors,
feeding a 100 kΩ resistor into a 500 kΩ Depth control. It does not gate the signal path.
It modulates channel 2's **screen and supply** — swinging the gain of a pentode
by moving the electrode that sets a pentode's gain. Seth Lover designed it.

What is *not* legible is the resistor that feeds channel 2's screen, and how the
Depth network loads it. The factory chart makes the consequence unmissable:
channel 2's screen prints **+32 V** where channel 1's prints +95 V, off the same
+265 V rail. Nothing about channel 2's operating point can be derived without
that resistor, and this entry will not invent it.

The chart's channel-2 row does not close on any reading of the drawing this scan
supports, and that is worth stating plainly rather than quietly. Take the row as
printed — anode +130 V, screen +32 V, cathode +1.45 V. The cathode figure over a
2.2 kΩ resistor is 0.66 mA of total current, but the anode figure off a +265 V
rail through the 510 kΩ load is only 0.27 mA, which would leave 0.4 mA flowing in
a screen sitting 30 V above ground — far more screen current than plate current,
which a sharp-cutoff pentode does not do. Note also that the row shares two of its
three figures exactly with the 6SQ7 row directly beneath it (+130 and +1.45), the
kind of coincidence a transcription slip produces. Both possibilities — an
unresolved screen network, or an error on the chart — stay open here, and neither
is resolved by guessing.

Any future re-reading of this circuit should start with a better scan of the
channel-2 and tremolo half of the sheet, or with a second published drawing of
the same revision. Until then, the parts list letters what can be built and says
so.

## Supply

5Y3GT into a 20 µF reservoir (+315 V at its cathode on the chart), a 3 H choke,
then 10 µF at the +310 V node that feeds both screens and the output-transformer
centre tap. From there 10 kΩ to the +280 V inverter rail and another 10 kΩ to the
+265 V preamp rail with its own 10 µF can. A published restoration records the can
complement as 20/10/10/10 µF; this reading places three of the four, and the
fourth most likely sits on the +280 V rail. That gap is recorded in the parts
list rather than filled in.

Because the droppers between those three rails also carry channel 2 and the
tremolo — neither of them modelled — the netlist drives all three rails at the
chart's own printed figures instead of deriving a chain that is missing half its
load. That is the same convention the 6G6-B entry uses, and the reason none of the
three appears as a gated node: a driven node proves nothing.

## Mains

A polarity switch — the era's line-reverse arrangement — chooses which side of
the 115–125 V line the 0.02 µF capacitor grounds. The on/off switch sits in one
leg and a 3 A fuse in the other. A 6.3 V pilot lamp hangs on the heater winding.
Do not build the mains side as drawn; it predates grounded three-wire practice.
