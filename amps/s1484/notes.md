# s1484 — Silvertone Twin Twelve-style

This is a department-store amplifier, and it is one of the largest circuits in
the corpus. Sears sold it; Danelectro built it; the drawing calls it neither, and
identifies it the way a service department would — **SCHEMATIC DIAGRAM OF
SILVERTONE CHASSIS 185.11040**, with the model number boxed on the parts page as
"USED IN MODEL 1484". Eight bottles: four 12AX7s, two 6CG7s, two 6L6GCs, and no
rectifier tube at all. Two channels, each with its own Bass, Treble and Volume.
Reverb on a spring pan and tremolo through a light bulb. A piggyback head over a
2×12 cabinet.

Three things make it worth documenting, and none of them is the tube count.
The **power supply** is not a rectifier feeding a dropper chain — it is a stacked
capacitor multiplier that builds a 480 V rail out of four 150-volt capacitors.
The **phase inverter** is a cathodyne, drawn in a way that makes the printed
chart look self-contradictory until you notice a wire crossing. And the maker
published a **parts list**, which almost none of the makers in this corpus did —
so the tolerances and working voltages in the parts list below are the factory's
own, not this project's era conventions.

## The supply, and why this entry cannot verify from the rail down

Nearly every circuit in this corpus is verified the same way: drive the top of
the supply, derive every node beneath it through the droppers the drawing letters,
and compare what comes out against the printed chart. That method needs a supply
that is a chain. This one is a stack.

There is no rectifier tube and no conventional reservoir. Two HT windings feed
four 1N3194 silicon diodes into four 100 µF · 150 V electrolytics (C26–C29) wired
in series, so the rail is built by stacking capacitor voltages rather than by
rectifying a higher winding — which is how a 480 V rail comes out of parts rated
for 150. Below that sit a choke (CH1) and a three-section can (C25, 20 + 10 +
5 µF · 450 V) tapped by two 68 kΩ droppers, R58 and R59.

The drawing prints exactly two figures on that whole arrangement: **480 V** at the
top of the stack and **340 V** at the 6L6GC screens. It labels no junction inside
the stack, gives no DC resistance for the choke, and — the decisive gap — prints
**nothing at all** on the node that feeds R7, R8, R33 and R34, the plate loads of
every preamp stage. Deriving the preamp from the rail would mean choosing that
rail's voltage, and this corpus does not invent supply voltages.

So the simulation does something narrower and says so: it drives each preamp plate
at **its own printed voltage** and derives the **cathodes**. Every driven node is a
number lettered on the drawing; every checked node is a different number lettered on
the drawing that the simulation has to reproduce. What that tests is each stage's bias — the drawn cathode
resistor and the tube model together — at the plate voltage the factory measured.
What it does not test is the supply. That gap is the entry's main open question
and the first reason it is a draft.

## The cathodyne, and the wire that isn't a junction

V3 is a 6CG7. Its first half is a plain gain stage after the channel mixer. Its
second half is the phase inverter, and it is a **cathodyne** — a split load, one
output off the plate through R33 and the other off the cathode side through R30.
The two are **68 kΩ each**, which is the whole trick: equal loads, equal and
opposite swings, one triode.

Three details are worth pointing at. R32, 2.2 kΩ, sits *above* the cathode tap and
is the only resistor actually setting the bias — the 68 kΩ below it is a signal
load, not a bias resistor. R31, the 1 MΩ grid leak, returns to the **tap** rather
than to ground, which is what puts the grid near the cathode potential and is
standard cathodyne practice; it is also, exactly, the 1 MΩ maximum grid-circuit
resistance the 6CG7 data sheet allows for fixed-bias operation, so the design sits
on the rating rather than inside it. And the two outputs are unequal in one
respect the drawing makes plain: C15 takes the plate signal to V7's grid while C14
takes the cathode-side signal from the tap, not from the cathode itself.

Now the wire. R34, V3A's 100 kΩ plate load, is drawn running down the page and
**crossing** the horizontal wire that carries the printed 125 V — with no junction
dot. Read as a junction, the chart becomes nonsense: 100 kΩ between a 125 V node
and a 100 V plate passes 0.25 mA, which across V3A's 1.5 kΩ cathode resistor is
0.4 V, not the 4 V the drawing prints; run the arithmetic the other way and the
plate lands below ground. Read as a crossing — which is what it is, and what the
same sheet does at several other places — R34 carries on to the preamp rail, the
cathodyne tap carries its own cathode current and nothing else, and the numbers
behave. Simulating it that way puts the tap at **117.5 V against the printed
125 V**, 6% out.

## What the models say, and where they miss

Five bottles are solved. Four of the five checked nodes land comfortably; one
does not.

| node | printed | simulated | |
|---|---|---|---|
| V1 shared cathode | 1.1 V | 1.1 V | +4.0% |
| V2A cathode | 1.1 V | 1.2 V | +13.3% |
| V2B cathode | 1.1 V | 1.2 V | +13.3% |
| V3A cathode | 4 V | 3.2 V | **−20.7%** |
| cathodyne tap | 125 V | 117.5 V | −6.0% |

V3A's cathode is the miss, and it is a real one: the model idles that 6CG7 at
about 2.1 mA where the printed 4 V across 1.5 kΩ implies 2.7 mA. It sits just
outside the ±20% convention this corpus applies to a tube pin, and it is the
second reason the entry is a draft. The 6CG7 model is new here and fitted to a
single datasheet operating point, the sheet's 250 V column — and it is running at
100 V in this socket, a long way from that point. The residual runs in the
same direction the model's own published low-voltage check misses in (8.42 mA
against 10 mA printed at Va=90 V). Whether the gap is the model or the drawing is
not settled here.

The output pair is driven at all three of its printed pin voltages — 475 V plates,
340 V screens, −36 V grids — so what it reports is the **idle current**:
26.7 mA a tube, 12.7 W at the plate, about 42% of the 6L6GC's 30 W rating. Fixed
bias, no cathode resistor on either bottle, both pin 8s straight to the chassis,
and a separate negative supply (D5 with a 100 µF · 50 V reservoir) making the
−36 V. The bias arrives at each grid through 330 kΩ.

## The 55 volts that belongs to nothing

The sheet letters **55 V** beside R43, and R43 is V5's grid leak. One end of it is
V5's grid, which reaches the rest of the amplifier only through the 0.01 µF
coupler C16 and can therefore only be at 0 V DC. The other end is the chassis end
of R44, V5's shared cathode resistor, which the drawing takes to the ground bus.
Neither end can be at 55 V, and no third node touches the resistor.

The likeliest reading is that the figure belongs to **V4B's plate** — the nearest
node on the sheet whose voltage is otherwise never given, and one whose 0.8 V
cathode over 10 kΩ implies a current a plate could sit at 55 V on. But the drawing
does not put it there. It is recorded as an unplaced figure rather than
moved onto a node this entry would like it to fit, and it is the third reason the
entry is a draft.

## Two parts the factory never named

Each channel's first stage returns its grid to ground through a 1 MΩ leak. Both
resistors are drawn on both published copies of the schematic, and **neither
carries a reference designator** — on a sheet that letters 61 resistors, 31
capacitors, 5 diodes and 8 bottles. They are missing from the factory parts list
too, whose 1 MΩ group is exactly R5, R28, R31, R43 and R47.

They are real parts in the signal path and the simulation models both, so the parts
list carries them with a dash where a designator would go, rather than inventing
numbers for them. A designator is
what a drawing letters on a part; these the factory never did.

## Where the two published documents disagree

Two copies of this circuit were read: the factory scan, and a corrected
re-typeset reproduction of the whole Sears manual published by the Silvertone
archive, whose author states plainly that he fixed schematic errors in the
original. Where the two differ, the factory sheet is what this entry records. In
practice they differ almost nowhere — the redraw is faithful, and it is the reason
several values here can be read at all.

The disagreement worth naming is *inside* the factory documentation, between its
own two pages. The **schematic** letters C12 as 0.02 µF; the **parts list** files
C12 in its 0.01 µF · 600 V tubular group. C12 is the coupler from the channel
mixer into V3A's grid, so it is open at DC either way and no operating point turns
on it — but a builder has to pick one, and this entry records the schematic's
0.02 µF because the schematic is the surface the corpus reads circuits from. A
smaller one: the schematic letters R44 as 820 Ω where the parts list row reads
"800 ohm, 20%" under part number 18-82002. Inside the printed 20% those are the
same resistor.

## Circuit walkthrough (short form)

**Inputs.** Two jacks per channel, each through 68 kΩ (R1–R4) onto a shared grid
node with an unlettered 1 MΩ leak to ground.

**V1, both channels.** One 12AX7, one triode per channel, 220 kΩ plate loads
(R7, R8) — and **one cathode resistor for both**, R6 1.5 kΩ with a 25 µF can. The
two channels are not independent at DC. Channel 1 alone carries R5, a 1 MΩ
feedback resistor from its grid back to the far side of its coupling capacitor;
channel 2 gets R9, 220 kΩ in series into its tone network, instead. That
asymmetry is deliberate and the manual explains why: channel one has "Two Inputs
and three controls", while "CHANNEL TWO . . . contains both Reverberation and
Tremolo".

**Tone, per channel.** A bass control (1 MΩ) with 0.0015 µF and 0.02 µF across its
halves, fed through 100 kΩ and shunted by 68 kΩ; a 680 pF treble bypass around it;
then a 1 MΩ treble control wired as a **rheostat** — wiper strapped to one end —
shunting the signal node to ground through 0.01 µF, so it is a treble cut, not a
boost. Then a 1 MΩ volume control. No middle control and no shared stack.

**V2 and the mixer.** A second 12AX7, one half per channel, both cathodes on
4.7 kΩ and **neither bypassed**. The two plates are summed through 68 kΩ each
(R24, R25) into a 560 kΩ mixer node, and one 0.02 µF coupler takes the mix on.

**V3.** 6CG7. First half a gain stage; second half the cathodyne described above.

**Output.** Two 6L6GCs, fixed bias, cathodes to chassis, screens on their own
340 V node behind the choke, plates on a centre-tapped primary printed at 85 Ω a
half. A standby switch sits in the bias-network line.

**Reverb.** V4 (12AX7) recovers from the CS55 spring unit through a 1 MΩ REVERB
DEPTH control that carries the reverb on/off switch on its own shaft — the parts
list calls SW1 "part of control R37", so turning the reverb down far enough
switches it off, which is exactly what the manual tells the owner to do. V5 (the
second 6CG7) drives the pan, both triodes on one 820 Ω cathode resistor at a
printed 8.2 V — about 10 mA between them, which is what a pan driver has to pass
and what a 12AX7 in the same socket could not.

**Tremolo.** V6 (12AX7) runs a phase-shift oscillator whose output drives the neon
lamp inside a **306-2H light-operated tremolo unit** — a lamp facing a photocell,
the photocell shunting the signal path. TREMOLO STRENGTH (100 kΩ) sets the depth
and TREMOLO SPEED (1 MΩ) the rate. There is no gating of the bias supply and no
modulated cathode: the modulation is optical, which is why the tremolo on this
amplifier is quiet and slow to react rather than choppy. The oscillator is
excluded from the netlist, as every tremolo oscillator in this corpus is: a
running oscillator shifted by grid-leak detection has no static operating point
worth reporting.

## A note on the id

This corpus names circuit-number-first, and the designation on this title block is
a **chassis** number: 185.11040. An id may not contain a dot, so the id here is
built from the model number the same manual page boxes — "USED IN MODEL 1484" —
prefixed to keep it a designation token rather than a bare number. Match a chassis
plate against **185.11040**, not against the id.

## A note on the rating

The 60 W in the header is the period retail rating the model was catalogued and is still
traded under. The drawing prints no output-power figure of any kind; its only
power number is the mains draw, "117 VAC 60 CYCLES 100 WATT 1 AMP". A pair of
6L6GCs idling at 12.7 W a plate on a 475 V rail is a real amplifier, but 60 W is a
catalogue number and is recorded here as one.
