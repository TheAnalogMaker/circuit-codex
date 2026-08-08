# AC30/6 — Vox AC30/6-style

The AC30 is the AC15 scaled up. Jennings Musical Industries drew the first
AC30/6 sheet on 29 April 1960, the same day as the AC15's own drawing and by the
same two hands — Dick Denney designing, Derek Underdown tracing — and it carries
the same set of decisions: four EL84s instead of two, cathode-biased on one
shared resistor with no bias supply, no negative-feedback loop anywhere, a
long-tailed-pair inverter, and a single tone control sitting *after* that
inverter. Six inputs across three channels give the model its name.

The circuit documented here is not that first sheet. It is the amplifier after
the list of changes of 8 May 1961, read from JMI drawing **OS/065**, *"VOX"
A.C.30.36 AMPLIFIER CIRCUIT / NORMAL*, whose title block still carries the
original 29-4-60 date and whose modifications box runs through Issue 4 of
11 September 1964 — the date on or after which those changes were drawn into the
body of the sheet. That distinction matters more here than it usually does,
because the single most-quoted fact about the AC30 lives inside it.

## The valve that did not survive the scale-up

The 1960 AC30/6 kept the AC15's **EF86** pentode on its Normal channel. The
May 1961 changes took it out and put one **ECC83** in its place, half for the
Brilliant channel and half for the Normal — and the reason was mechanical, not
tonal. An EF86 is a high-gain small-signal pentode; in a cabinet with two
twelve-inch speakers at 30 watts it is famously microphonic, and it had become
the amplifier's weak point. Everything the AC30 is remembered for sounding like
dates from after that substitution.

It left a signature behind. The two channels do not merely share a bottle: they
share its **cathode**. R4, a single 1.5 kΩ resistor with a 25 µF bypass, biases
both halves of V1, so the two front ends are not independent, and neither can be
solved on its own — a fact this archive's netlist has to honour before it can
report a single voltage.

## Circuit walkthrough (short form)

**Brilliant and Normal channels.** Six jacks, 68 kΩ input stoppers, 1 MΩ leaks
→ **V1 (ECC83)**, one half each, both on 220 kΩ anode loads and that shared
1.5 kΩ / 25 µF cathode. The channels differ in one part: the Normal side couples
out through 0.047 µF, the Brilliant side through **500 pF**, a capacitor small
enough that only the top of the band crosses it. That single component is the
whole of the "Brilliant" voicing on this circuit — there is no extra stage and no
tone stack behind it.

**Vibrato/Tremolo channel.** Its own ECC83 first stage (V7), a switched voicing
network, a phase-shift ladder, an **ECC82** modulator (V8) and an **ECC83**
phase-shift oscillator (V9) with Speed and Depth and a footswitch — the Vibravox
arrangement the AC15 carries, at the same scale.

**Phase inverter.** A **long-tailed pair** (V2, ECC83): 100 kΩ anode loads, a
1.2 kΩ shared cathode resistor over a 47 kΩ tail, both 1 MΩ grid leaks returned
to the tail junction. The mixing is worth a second look. Brilliant and Normal
each reach *one* grid through their own 220 kΩ resistor, while the
Vibrato/Tremolo volume drives *the other*. Two channels sum before the pair; the
third enters against them. Play into a Brilliant jack and a Vib/Trem jack at once
and the two signals arrive in opposite phase — the same quirk the AC15 has with
its two channels, inherited rather than designed out.

**Cut.** The amp's only tone control, and it sits after the inverter: a 250 kΩ
log pot in series with a 0.0047 µF capacitor, bridged across the two inverter
outputs. Turning it up shunts treble differentially between the two phases, so it
darkens all three channels at once, downstream of everything that makes the
amplifier distort.

**Output.** Four **EL84s** in parallel push-pull, two per phase, each with its own
1.5 kΩ grid stopper and 100 Ω screen stopper off the same rail as the anodes.
Bias is one shared **50 Ω** cathode resistor with a 250 µF bypass — one resistor
for four valves, no bias supply and no adjustment. The drawing annotates it
directly: *quiescent 10 V*, rising to *12.5 V at 30 watts*. Ten volts across
50 Ω is 200 mA for the quad, 50 mA a valve, which is why an AC30 runs as hot as
it does and why it compresses instead of stiffening when pushed. The output
transformer is 4 kΩ anode to anode, with 8 Ω and 15 Ω taps, and there is no
feedback loop around any of it.

**Power.** A **GZ34** off a 280-0-280 V, 160 mA secondary feeds a 16 µF
reservoir, a 10–20 H choke and a second 16 µF can. Two 22 kΩ droppers hang off
the resulting +320 V rail, one to the front end (annotated +290 V) and one to the
phase inverter. Mains taps run 115 through 245 V.

## Why it sounds the way it does

Three things carry most of the character, and only one of them is the preamp.
The output stage is the loudest fact: four cathode-biased pentodes with no
feedback loop and no bias adjustment, idling at 50 mA each, which puts the whole
stage close to its limit before a note is played. The Cut control sits at the
inverter rather than in the preamp, so the top end is trimmed *after* the
amplifier has done its distorting — a rolled-off AC30 still sounds bright-edged
rather than muffled. And the front end is deliberately plain: one triode stage
per channel, no tone stack, nothing between the guitar and the inverter but a
volume control and a coupling capacitor. What the amplifier does to a signal, it
does in the power amp.

Top Boost, when it arrived in 1961, was a factory retrofit that added a whole
extra valve stage with treble and bass controls; this sheet points at it in the
corner — *"NOTE: FOR TOP BOOST AMPLIFIER SEE DRG. Nº OS/010"* — but does not
contain it. What is documented here is the AC30 without it.

## A note on verification

The factory drawing annotates its working voltages beside the circuit — +320 V at
the rail, +290 V at the front-end anode supply, +170 V at each V1 anode, +1.6 V
at V1's shared cathode, +230 V at each inverter anode, +55 V at the inverter tail
junction, and the output stage's quiescent 10 V — but it prints no tabulated
valve-voltage chart of the kind Fender printed, and states no measurement
convention. There is therefore no per-pin reference to verify against, and the
circuit is published as a **draft** for the same reason its sibling AC15 is.

The agreement is nonetheless close. Simulated from the redrawn netlist with the
+320 V rail driven at its printed value, the front-end supply lands at 295 V
against a printed 290, the V1 anodes at 172 V against 170, V1's shared cathode at
1.68 V against 1.6, the inverter anodes at 227 V against 230, and the output
stage at 10.6 V of cathode bias against a printed 10. The worst gated node is the
inverter's tail junction, 61 V against a printed 55 — about 10%, and the one
figure on the sheet with a documented history: the modifications box records
*"230V WAS 285V"* at Issue 3 of 11 October 1963, so at least one of this
drawing's voltage annotations was revised without any change to the resistors
around it. The later figures are the ones used here, because they are the ones
the sheet as amended prints.

One value on this copy does not resolve cleanly. R19, the second phase-inverter
anode load, has a multiplier glyph that reads more like an ohm sign than a K.
It is recorded as 100 kΩ, on three independent grounds: its partner R18 is
legibly 100 kΩ, a long-tailed pair with mismatched anode loads would not put the
drawing's single +230 V annotation on both anodes, and the later Vox factory
sheet for the same inverter and output section draws the pair as 100 kΩ and
100 kΩ. The arithmetic closes: 55 V across the 47 kΩ tail is 1.17 mA, which
through two 100 kΩ loads from the inverter's supply lands both anodes where the
drawing says they sit.

The DC netlist covers the Brilliant and Normal channels, the phase inverter and
the output stage. The Vibrato/Tremolo channel is documented in the parts list but
left out of the simulation: its oscillator has no static operating point to solve
for, and reporting a partial answer for that side of the amp would be worse than
reporting none.

## A note on the drawings

The redrawn schematic asserts every connection the published drawing resolves:
the two front-end channels, the phase inverter, the Cut control, the output stage
and the power supply. The Vibrato/Tremolo channel's voicing, phase-shift,
modulator and oscillator networks are inventoried in the parts list, but the
available scan does not resolve their interconnection well enough to assert it,
so the schematic names the interfaces each valve works into and asserts nothing
further.

This copy of OS/065 also carries a **later hand addition**: a blue-ink negative
feedback loop, drawn in by some previous owner from the output transformer back
towards the front end, with a 1 MΩ resistor and a 0.1 µF capacitor. It is not
part of the circuit JMI built, it is not in the parts list, and it is not
modelled. The archive that hosts the sheet flags it as an addition, and so does
this entry — an amplifier is not defined by what a later hand wished it did.
