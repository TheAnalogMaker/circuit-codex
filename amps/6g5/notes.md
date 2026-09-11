# 6G5 — Brown Pro-style

Fender's biggest brown-Tolex combo: a 40-watt, two-channel amplifier built
around a pair of **6L6GC** output tubes and a single 15-inch speaker, produced
1960–1963 on the A-FJ drawing. Where the brown Deluxe ([6G3](/amps/6g3/)) is a
small amp learning fixed bias and a long-tailed-pair inverter, the Pro is the
same redesign applied to Fender's high-power circuit: **silicon
rectification** in place of a tube rectifier, **fixed, non-adjustable bias**,
and a **harmonic vibrato** — a circuit that sweeps the bass and treble halves
of the signal against each other rather than simply turning the volume up and
down. All five small bottles are marked **7025** on the drawing, the low-noise
selected version of the 12AX7.

**Correction, September 2026.** This page previously described the vibrato as
a photocell tremolo and gave each channel a bottle of its own. Both were
misreadings: the drawing has no lamp or photocell anywhere, and its five
small bottles are shared by stage, not by channel. The circuit below is read
again from the drawing at its full resolution.

## Signal path

**Two channels, one bottle per stage.** The drawing prints no channel names;
channel 1 is the one drawn on top, whose controls sit beside Speed and
Intensity on the panel. Each channel has two inputs on 68 kΩ stoppers, with a
1 MΩ leak to ground at input 1, into a first stage with a 100 kΩ plate load.
The two first stages are the two halves of one bottle, V1, and share a single
820 Ω cathode resistor and a single 25 µF bypass — the drawing letters the
joined cathodes with a boxed **C** and prints **+170 V** at both plates and
**+1.4 V** at the cathodes. Each channel then runs through a 0.05 µF coupler
into its own **Bass/Treble** network and a 500 kΩ-L Volume control, into a
second stage — and again both second stages share one bottle, V2, and one
820 Ω / 25 µF cathode pair (the boxed **D**, **+1.1 V**).

**The two second stages are loaded differently**, which is what the chart's
**+160 V** and **+120 V** record. Channel 1's plate returns to its supply
through 100 kΩ and then a 6.8 kΩ decoupling resistor, and its output is taken
from the junction of the two, not from the plate. Channel 2's plate load is a
single 220 kΩ. Channel 1 alone has a 47 pF bright capacitor from its Volume
control's hot lug to the wiper; neither page of the drawing shows one on
channel 2.

**The tone network** is the one the brown Super ([6G4](/amps/6g4/)) draws,
part for part. From the coupler, a 250 pF treble capacitor feeds the hot lug
of a 250 kΩ-L Treble pot and a 100 kΩ slope resistor drops to the slope foot,
where the Treble pot's cold lug also sits. The Bass control is a 250 kΩ-A pot
wired as a divider from the slope foot to ground, with the 0.01 µF bass
capacitor across its upper section (hot lug to wiper) and a 10 kΩ foot
resistor across its lower (wiper to ground); the Treble wiper alone is the
output. The pot values are what both pages of the drawing letter — Treble
250K-L, Bass 250K-A, Volume 500K-L.

**Only channel 1 goes through the vibrato.** Its output feeds the vibrato
circuit below; channel 2's output joins the vibrato's output afterwards,
through 0.05 µF and 1 MΩ, and the sum drives the phase inverter through a
0.001 µF coupler.

## The harmonic vibrato

Channel 1's signal is split into two bands. A **low-pass** branch — 470 kΩ
into 0.005 µF to ground — reaches one grid of V4 through 0.01 µF; a
**high-pass** branch — a 220 kΩ / 220 kΩ divider — reaches the other grid
through 250 pF. The two halves of V4 amplify one band each: 100 kΩ plate
loads, one shared 4.7 kΩ cathode resistor bypassed by 2 µF, printed **+320 V**
at both plates and **+3.3 V** at the cathodes. Their plates recombine through
470 kΩ apiece.

A slow oscillator makes the two bands take turns. V3A is a phase-shift
oscillator — a ladder of 0.02, 0.01 and 0.01 µF from its plate back to its
grid, with the 4 MΩ reverse-audio **Speed** control and a 100 kΩ to ground on
the first node, a 1 MΩ to the cathode on the second, and a 1 MΩ grid leak.
Its 470 kΩ plate load and 4.7 kΩ / 25 µF cathode print **+130 V** and
**+1.3 V**. The vibrato pedal's jack sits on the ladder's second node: the
footswitch grounds it and the oscillation stops. The oscillator's output
leaves through 4.7 MΩ and 0.005 µF onto the 10 MΩ-L **Intensity** control,
and the wiper feeds the low-band grid of V4 through 1 MΩ.

The other band is driven the opposite way by V3B, the oscillator's second
half, working as a phase splitter. Both V4 grids return through 1 MΩ each to
V3B's grid, so the swing arriving at the low-band grid reaches the splitter
too; V3B inverts it and feeds it to the high-band grid through 0.05 µF and
1 MΩ. As the oscillator pushes one band up, it pulls the other down — the
tone tilts from bass to treble and back at the Speed setting. Capacitors on
the oscillator's plate, the Intensity control, the splitter's grid and its
plate (0.03, 0.1, 0.05, 0.05 and 0.25 µF to ground) round off the sweep. The
splitter prints **+180 V** at its plate and **+1.5 V** at its cathode (1.5 kΩ
/ 25 µF).

**In the model.** The vibrato pair and the splitter each have a static
operating point, and both are simulated and compared with the chart. The
oscillator does not: a running phase-shift oscillator swings around whatever
its printed pins describe, so it is excluded from the model, exactly as the
[AB763](/amps/ab763/) excludes its own, and its printed pins are reported for
the record only. Leaving it out has one visible cost. The oscillator draws
about 0.3 mA from the supply it shares with the splitter, and without it that
supply simulates about 300 V against the printed +275 V; with a stand-in for
that current it lands on 275 V, and the splitter on its printed +180 V.

## Phase inverter and output

A **long-tailed-pair** inverter — 82 kΩ (hot) and 100 kΩ (cold) 5 % plate
loads, printed **+315 V / +310 V**, with 47 pF across the two plates and an
820 Ω shared cathode (**+23 V**) into a 6.8 kΩ tail — drives the **two
6L6GC** output tubes through 0.05 µF couplers. The tail lands on a foot node
carrying a **1.5 kΩ** resistor to ground, the **22 kΩ** negative-feedback
resistor from the output transformer's secondary, the 0.1 µF that grounds the
cold grid for signal, and the **5 kΩ-L Presence** control in series with a
**0.1 µF** capacitor, which makes that branch AC-only. The output tubes run
**fixed, non-adjustable bias**: grounded cathodes, 220 kΩ · 5 % grid leaks to
the bias line and individual 470 Ω · 1 W screen stoppers.

## Power

The centre-tapped HT secondary feeds **two legs of three silicon diodes** (no
tube rectifier) into two 20 µF reservoir cans, then the standby switch. The output
transformer's centre tap takes **+460 V** there, ahead of the choke; after the
choke, **+458 V** feeds the 6L6GC screens and every dropper, and the plates,
through the output transformer, print **+456 V**. From there each rail has its own dropper and its own 20 µF can:

| Rail | Printed | Fed through | Feeds |
|---|---|---|---|
| Phase-inverter supply | +430 V | 4.7 kΩ · 1 W from +458 V | the inverter's two plate loads |
| Rail A | +260 V | 56 kΩ · 1 W from +430 V | all four channel plate loads |
| Vibrato-pair supply | +350 V | 56 kΩ · 1 W from +458 V | V4's plate loads |
| Oscillator supply | +275 V | 56 kΩ · 1 W from +350 V | the oscillator's and splitter's plate loads |

The last three figures are lettered on the layout page only. The model drives
the +460 V and +458 V nodes either side of the choke, whose resistance is
not printed, and the bias line, and solves every other rail through these
resistors, each landing within a few percent of its printed value — the
oscillator supply excepted, for the reason above. Fixed bias reads **−55 V**
off a small rotated label beside the two output grid leaks, from a
bias-tap rectifier, 8 µF, 10 kΩ, then 8 µF with a 56 kΩ bleeder; that one
figure is read with a wider margin than the horizontal prints.

## Why this entry is draft

The chain from the plate rail down to every stage is derived through
resistors the drawing letters, and every printed stage voltage is compared
with the model. Three things stand between that and `verified`: the excluded
oscillator leaves its own supply reading high; four of the compared figures
appear on the layout page only; and the −55 V bias label is read with less
confidence than the rest. `verified` is granted by the maintainer's review in
any case, never by the checks alone.

## Seven bottles, five noval sockets

The chassis carries **five 7025s**, not seven — the layout page's socket row
draws five noval sockets alongside the two 6L6GC octals, and the voltages it
letters at each socket say which stage each half carries. From the input end:
V1 holds both channels' first stages, V2 both second stages, V3 the vibrato
oscillator and its splitter, V4 the vibrato pair, and V5 the phase inverter.

The board diagram draws the vibrato network on the eyelet board, where the
layout page mounts it, and the parts the page mounts at the controls there:
the tone parts at each channel's pots, the Speed control's 100 kΩ, the
Intensity wiper's 0.05 µF, and the Presence control's 1.5 kΩ and 0.1 µF.

## Lineage

The 6G5's predecessor is the narrow-panel tweed Pro, the **5E5-A**, which this
corpus documents — and the metadata carries the derivation edge. The brown
circuit keeps the tweed Pro's 40 W-class output pair and its Presence control,
and replaces the tube rectifier with silicon diodes, the split-load cathodyne
with a long-tailed pair, and the single channel with two plus a harmonic
vibrato. It is the same shape of redesign the 6G3 applies to the tweed
Deluxe. Behind the 5E5-A stand the earlier tweed Pros, the 5C5 and 5D5, which
are history-tier entries rather than documented circuits.
