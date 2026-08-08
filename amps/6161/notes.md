# 6161 — Valco 6161-style

The 6161 is a Chicago amplifier that never carried its builder's name. Valco
made instruments and amplifiers under Supro, National, Airline and Oahu, and
built amplifiers under contract for Gretsch, Harmony and Kay — so the same
chassis went out of the same factory wearing whichever badge had ordered it.
This one is documented from the drawing whose title block reads **Valco Model
6161**: three 12AX7s, a pair of **6973** beam power tubes, a 5Y3-GT rectifier,
tremolo, one tone control, and two 10-inch speakers.

Two things make it worth documenting. The output tube is one almost nobody else
used. And the phase inverter is a **paraphase** — the arrangement American
makers had largely abandoned by 1960, kept here and made to work by a single
pair of resistors.

## The 6973

A 6973 is a beam power tube in a nine-pin bottle the size of an EL84's, and it
behaves like neither of its neighbours. It takes about the drive of a 6L6 while
dissipating only **12 watts** at the plate — barely more than an EL84 — and its
screen grid is rated for 2 W and 330 V, less headroom still. A pair of them is
asked to make roughly 20 W. There is very little thermal margin in the design,
which is exactly why the amplifier lets go early and hard rather than stiffening
up: it is running near its ceiling at idle.

Near it, and in fact past it. The published measurement on the sibling
amplifier reads 24 V across the shared 250 Ω cathode resistor, which is 96 mA
for the pair — about 48 mA each, at some 345 V from plate to cathode, or
roughly 16 W in a tube rated for 12. The simulation lands in the same place.
Whether that was a deliberate choice or an accepted one, it is what the drawing
specifies, and it is a large part of why these amplifiers sound the way they do
and why their output tubes did not last.

The data sheet rates two ways of feeding the screens, and this circuit uses the
plainer one. Screens come off their own supply node behind a 1 kΩ dropper, not
from taps on the output-transformer primary — the arrangement that would have
allowed the higher 410 V supply ceiling.

## Circuit walkthrough (short form)

**Channels.** Two identical halves of one 12AX7, each fed by a *pair* of jacks
panel-marked **Treble** and **Bass**: the Treble jack couples in through
0.005 µF, the Bass jack through a 100 kΩ series resistor, and both land on the
same grid behind a 470 kΩ leak. There are no channel tone controls — the jack
you choose *is* the voicing. Each half runs a 270 kΩ plate load off its own
supply node, dropped from the main rail through 100 kΩ and decoupled by
0.05 µF. Channel 1's 2.2 kΩ cathode resistor is left **unbypassed**; channel 2's
1.5 kΩ carries a 35 µF can — and, as below, the tremolo tube. The two halves
part company after the plate as well: channel 1 runs a single 0.005 µF coupler
straight into its volume control, while channel 2 has a 500 pF capacitor from
its plate to ground and reaches its own volume through **two** 0.005 µF
couplers in series with a 270 kΩ shunt between them. Channel 2 is the darker
and the quieter of the two before either control is touched.

**Volume, mixer and tone.** Each channel gets a 500 kΩ volume with a 500 pF cap
bridging it, and the two wipers are summed through 270 kΩ apiece into one node.
The amp's only tone control hangs there: a 0.005 µF capacitor into a 500 kΩ pot
to ground, trimming treble off both channels at once, with a 500 pF shunt fixed
across the same node. From there a 300 pF capacitor — small enough to be a
voicing choice, not just a coupler — carries the mix into the inverter.

**Phase inverter.** A **paraphase**, and the interesting part of the amplifier.
The first half of the second 12AX7 is an ordinary gain stage on a 270 kΩ load
with a 2.2 kΩ cathode bypassed by 0.05 µF; its plate drives one 6973 grid
through 0.01 µF. The second half has to produce the same signal upside down, and
it is fed by tapping the first output grid through a **270 kΩ / 12 kΩ divider**,
whose junction is the second half's grid. The divider throws away all but about
1/23.5 of the drive and the second half has to put it back: on a 270 kΩ load
working into the opposite grid leak, with **3.9 kΩ of cathode resistance left
unbypassed** to hold its gain down, a 12AX7 returns roughly 27×. Those two
numbers are the entire balancing act — no shared cathode, no tail, no feedback.
They land close but deliberately not exact, and the inverted side runs a little
hotter than the driver side. The 12 kΩ resistor is the one to respect: it sets
the balance of the whole output stage on its own.

**Output.** Two 6973s, grids returned through the divider on one side and a
470 kΩ leak on the other, screens on their own node, plates straight onto the
reservoir through the output transformer. Bias is a **single shared 250 Ω
resistor** for the pair with a 35 µF bypass — one resistor, no bias supply, no
adjustment, and no negative-feedback loop anywhere around the stage.

**Tremolo, and why it is wired the way it is.** The third 12AX7 splits into a
phase-shift oscillator — three capacitors and two megohm-class returns around
one triode, with **Speed** on a 500 kΩ pot — and an output follower. The
oscillator's output leaves through 0.01 µF, passes a switch and the footswitch
jack, and reaches the follower's grid through the **Intensity** network.

The follower is where the trick is. Its anode goes *straight to the rail with no
load resistor*, and its cathode lands **directly on channel 2's cathode node**.
The two tubes share that one 1.5 kΩ resistor, so their currents add in it: the
follower holds channel 2's cathode well above where a 12AX7 would sit on its
own, and swinging the follower's current at oscillator rate swings channel 2's
bias with it. That is the tremolo — not a gate in the signal path but a hand on
the preamp's bias. It also means the two stages cannot be understood separately:
a published measurement set taken on a surviving sibling amplifier reads the
same ~2.4 V at two different sockets, because those two pins are one node.

**Power.** A 5Y3-GT into a 20 µF reservoir feeds the output plates; 1 kΩ · 1 W
drops to a 10 µF screen node; 15 kΩ drops again to the 10 µF rail that runs the
inverter plates directly and each preamp channel through its own 100 kΩ. Three
cans, two droppers, no choke and no standby.

## The A markers

The drawing brings **both** output-tube grid nodes out to markers lettered A and
resolves them no further — the only two A's on the sheet. The published redraw
of the Supro-badged sibling shows an SPST switch bridging exactly those two
nodes, which shorts the grids together and silences the amplifier. Either way
the pair carries no DC, so it changes no operating point; it is listed in the
parts list as annotation and asserted nowhere.

## A note on verification

This drawing prints **no voltages at all** — not a tabulated valve-voltage chart
of the kind Fender printed, and not even the handful of annotated working
voltages the Vox sheets and Valco's own later Supro S66xx sheets carry. There is
therefore no factory reference to verify against, and that alone is enough to
publish the circuit as a **draft**.

What exists instead is a published measurement set taken on a surviving 1965
Supro **1624T** — the Supro-badged sibling of this chassis, whose own published
drawing agrees with this one part for part on the entire supply chain, on the
shared 250 Ω output cathode resistor and its 35 µF bypass, and on the paraphase
divider and both inverter cathodes. Two nodes from it are compared here, and
only two, because only two are unambiguous in somebody else's socket numbering:
the screen node simulates 359.8 V against a measured 350 V, and the shared
output cathode 25.1 V against a measured 24 V. Both sit inside the era's ±20 %
tube-pin convention. Everything else is reported, never asserted.

The rest of that measurement set is quoted in the sources for a reader who wants
it, and it lines up: 212 V and 118 V at two preamp plates against 216 V and
117 V simulated, 2.36 V and 0.98 V at their cathodes against 2.5 V and 1.2 V.
None of it is gated, because the mapping from that amplifier's socket numbers to
this drawing's bottle numbers cannot be proved.

The DC netlist covers both channels, the inverter, the output pair and the
tremolo follower. The tremolo **oscillator** is left out: a running phase-shift
oscillator's quiescent point is shifted by grid-leak detection and is not a
static operating point, which is how the corpus treats the AB763 and 6G3
oscillators too. Here the exclusion is not quite free — that oscillator's
270 kΩ plate load taps the rail this netlist *derives* rather than drives, so
the rail and everything under it reads a few volts high by construction. The
same measurement set puts about 0.25 mA through that load, which is roughly 4 V
across the dropper.

## A note on the model number

**6161 names more than one circuit.** A documented 1957 example of the same
model number is a different amplifier: 6V6 output tubes, 6SQ7 triodes in the
preamp and tremolo, and a 12AX7 inverter — already a paraphase, and already
biasing its output pair on one shared cathode resistor, at 330 Ω. The revision
documented here is the one the title-block drawing shows: three 12AX7s, two
6973s and a 5Y3-GT. The drawing carries no date and no revision box, so the era
bracket on this entry is an outer bound — the earliest year a dated example of
this complement can be cited, to the year Valco folded — rather than a record of
what was built when.
