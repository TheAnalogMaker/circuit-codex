# AB763 (Twin Reverb) — Blackface Twin Reverb-style

Fender's flagship of the blackface years and the reference for a loud clean
amplifier: 85 watts from four 6L6GC output tubes into a pair of 12-inch
speakers, with the same spring reverb and tube tremolo the smaller reverb amps
carry. The circuit ran from 1963 to 1967. Two channels — a plain **Normal** and
a **Vibrato** channel with the reverb and the tremolo — each get a full
three-knob tone stack and a switched bright cap, and both feed one long-tailed
pair driving the output quartet. There is no rectifier tube: the high tension is
rectified by silicon, three series diodes to a leg.

The preamp bottles are marked **7025** on the drawing, the low-noise selected
version of the 12AX7; the reverb driver and the phase inverter are **12AT7s**,
chosen for the current they can deliver, and the tremolo runs on its own 12AX7.

## Signal path

**Both channels, up to the volume control.** Two inputs (each a 68 kΩ stopper
on a 1 MΩ leak) → a 12AX7 stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF
bypass) → a **three-knob tone stack** — 250 pF treble capacitor and 100 kΩ slope
resistor both leaving the plate node, 0.1 µF to the node shared by the treble
pot's lower lug and the bass pot, 0.047 µF down to the 10 kΩ middle control, and
the treble wiper alone as the output — → a 1 MΩ volume with a 120 pF bright cap
across it on a switch.

**Normal channel.** Volume → a second 12AX7 stage (100 kΩ plate) → a 0.047 µF
coupler into a 220 kΩ mixing resistor. No reverb, no tremolo.

**Vibrato channel.** Volume → a second 12AX7 stage (100 kΩ plate) → a 0.02 µF
coupler into the reverb and tremolo section.

## Two cathodes, four triodes

The drawing marks nodes that appear in more than one place with a boxed letter,
and two of those letters carry cathodes rather than supply rails. Each ties a
pair of stages onto **one** 820 Ω resistor and **one** 25 µF bypass can:

- the Normal channel's second stage and the Vibrato channel's second stage;
- the reverb-recovery stage and the reverb/dry mix driver.

Both ends of each pair are printed at the same +2.0 V, which is what a shared
node means. The consequence is worth stating plainly: the two stages on a shared
resistor are not independent. Each one's current sets the other's bias, so the
two are half as deeply biased as a private 820 Ω would make them, and anything
that changes one — a swapped tube, a hotter section — moves the other with it.

## Reverb and tremolo

**Reverb.** A 500 pF capacitor sends the vibrato channel's signal to a **12AT7
with both triodes in parallel** (1 MΩ grid leak, 2.2 kΩ shared cathode) feeding
the 125A20B transformer and the spring tank. What comes back is recovered by a
12AX7 stage across a 220 kΩ tank leak, coupled out by 0.003 µF, and blended with
the dry signal by the 100 kΩ Reverb control through a 470 kΩ mixing resistor.

**Tremolo.** The tremolo tube is a 12AX7 doing two jobs. One triode is a
phase-shift oscillator (220 kΩ plate load, 2.7 kΩ cathode, Speed on a 3 MΩ
control); the other drives the **neon lamp** inside an optocoupler, sitting at
the top of a 100 kΩ feed from the supply with a 10 MΩ bleeder across its plate.
The lamp faces a photoresistor which, through the 50 kΩ Intensity control,
periodically shunts the mix driver's grid toward ground and swings the volume.

**Mixing and inversion.** The mix driver (100 kΩ plate, its grid fed through
3.3 MΩ with 10 pF across it) is coupled out by 0.1 µF into the vibrato channel's
own 220 kΩ mixing resistor. The two channels' mixing resistors meet, and a
single 0.001 µF capacitor carries the sum to the phase inverter's grid.

**Phase inverter and output.** A 12AT7 **long-tailed pair** — 82 kΩ and 100 kΩ
5% plate loads, a 470 Ω cathode resistor down to a tail junction, 22 kΩ from
that junction onward, and both 1 MΩ grid leaks returned to it — splits the
signal for the **four 6L6GC**. The tail does not run straight to ground: it
lands on the negative-feedback node, where an 820 Ω resistor comes back from the
speaker and a 100 Ω leg goes to ground, so the feedback arrives in the tail. The
output tubes are fixed-biased at **−52 V** through two 220 kΩ leaks — one per
phase, each feeding two tubes — with a 1.5 kΩ stopper on every grid and a 470 Ω
· 1 W resistor on every screen.

## Power

340-0-340 V (power transformer 125P34A) → a **silicon full-wave rectifier**,
three series diodes to a leg → the standby switch → a reservoir of two 70 µF ·
350 V cans in series, balanced by a pair of 220 kΩ · 1 W resistors → **+460 V**
at the output-transformer centre tap and the 6L6GC plates → the 125C1A choke →
**+458 V** at the screens, the reverb-transformer feed and the tremolo → a
1 kΩ · 1 W dropper → **+450 V** at the phase-inverter plates → a 4.7 kΩ · 1 W
dropper → **+410 V** feeding all six preamp plate loads, on 20 µF · 525 V cans.
The grid line comes from the transformer's bias tap through a 470 Ω · 1 W
resistor, a rectifier and a 25 µF · 50 V can, to a 10 kΩ balance control over a
27 kΩ leg whose wiper sets the **−52 V**.

## The AB763 designation, twice

Fender put "AB763" on more than one drawing. The blackface
[Deluxe Reverb](/amps/ab763/) carries it too, and the two amps share the
generation's recipe — fixed bias, a long-tailed-pair inverter, tube reverb and
tremolo, the same tone-stack ladder — but they are not the same circuit and
neither is descended from the other. The Deluxe Reverb is a cathode-cool
22-watt amp on two 6V6GTs, a GZ34 rectifier and two-knob tone stacks; this is an
85-watt amp on four 6L6GCs, silicon rectification, three-knob stacks, and a
preamp with two extra gain stages to feed them. The archive keeps the bare
`ab763` for the Deluxe Reverb, which reached it first, and qualifies this one by
its model.

The circuit this amp actually descends from is the blonde 6G8-A Twin — four
bottles, fixed bias, solid-state rectification and a long-tailed pair were all
in place before the blackface redesign added the reverb and the middle controls.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to
ground with an electronic voltmeter. Two nodes are held at their printed values
in simulation — the +460 V reservoir and the +458 V node after the choke — and
everything below them is solved through the drawing's own droppers, so the two
lower rails are a test of the chart rather than an input to it. They pass: the
phase-inverter supply lands at +446 V against a printed +450 V and the preamp
supply at +408 V against +410 V, which is the arithmetic of six 100 kΩ plate
loads and a phase inverter agreeing with the resistors Fender specified.

Every node on the chart falls inside the drawing's own ±20 % across the modelled
stages: the reverb driver, the four preamp stages, the recovery and mix driver,
the phase inverter's +100 V cathodes and +98 V tail junction, and the screens
and grids of the output quartet. The widest gap is the vibrato channel's second
stage, whose plate simulates about 15 % above its printed +240 V — and that is
the shared-cathode node showing itself, because the chart prints +270 V at the
other end of the same 820 Ω and two stages on one resistor cannot in fact sit
30 V apart.

This circuit is published as **verified**: every node the chart prints for a
modelled stage is compared, none is set aside as disputed, and the worst gap is
the one described just above.

The **tremolo tube** is left out of the DC solution, both halves. The oscillator
is a running phase-shift circuit whose printed +2.0 V cathode is a
grid-leak-detected average rather than a quiescent point, and the lamp driver's
printed +380 V plate and +5.6 V cathode are what a meter reads while the neon
lamp fires and extinguishes. Neither is a static operating point, so both are
reported here rather than fitted to the chart. Unlike the Deluxe Reverb's
tremolo, this one hangs off the +458 V node rather than the preamp rail, so
leaving it out shifts nothing else on the chart.

The output quartet is simulated on a clean-room 6L6GC model fitted to RCA's own
tabulated Class A1 characteristics for that tube. It idles at about 30 mA a
bottle on the +460 V rail — a little under half the tube's 30 W plate rating,
and well inside its 500 V ceiling.
