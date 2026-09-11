# 6G4 — Brown Super-style

Fender's brown-Tolex remake of the Super, the two-10-inch step above the
Deluxe. Production ran 1960–1963 on the 6G4 chassis documented here, a
40-watt combo running a fixed-biased **6L6GC** pair off a **GZ34** rectifier,
before the 6G4-A revision swapped in a 5881 output pair and before the name
passed to the blackface Super Reverb. Where the tweed [5F4](/amps/5f4/) it
replaces cathode-biased its 6L6G pair through a selenium-assisted bias
network and a cathode-follower-fed tone stack, the 6G4 moves to a proper
fixed-bias supply, a long-tailed-pair inverter, and a **harmonic vibrato** —
a circuit that sweeps the bass and treble halves of the signal against each
other rather than simply turning the volume up and down. All five small
bottles are marked **7025** on the drawing, the low-noise selected version of
the 12AX7.

The A-FJ Super is the brown Pro ([6G5](/amps/6g5/)) part for part in the
preamp, the vibrato and the phase inverter; the two differ in the Super's
GZ34 rectifier where the Pro uses silicon diodes, and in the feedback
resistor, 10 kΩ here against the Pro's 22 kΩ.

**Correction, September 2026.** This page previously described the vibrato as
a bias-vary tremolo feeding the output tubes' bias line, and gave each
channel stage a bottle of its own. Both were misreadings: the drawing's
Intensity control feeds the vibrato circuit below, not the bias line, and
its five small bottles are shared by stage, not by channel. The circuit
below is read again from the drawing at its full resolution.

## Two channels, one bottle per stage

The drawing prints no channel names; channel 1 is the one drawn on top, whose
controls sit beside Speed and Intensity on the panel. Each channel has two
inputs on 68 kΩ stoppers, with a 1 MΩ leak to ground at input 1, into a first
stage with a 100 kΩ plate load. The two first stages are the two halves of
one bottle, V1, and share a single 820 Ω cathode resistor and a single 25 µF
bypass — the drawing letters the joined cathodes with a boxed **C** and prints
**+170 V** at both plates and **+1.4 V** at the cathodes. Each channel then
runs through a 0.05 µF coupler into its own **Bass/Treble** network and a
500 kΩ-L Volume control, into a second stage — and again both second stages
share one bottle, V2, and one 820 Ω / 25 µF cathode pair (the boxed **D**,
**+1.1 V**).

The tone network is not the blackface ladder, though it shares the ladder's
front half. From the coupler, a 250 pF treble capacitor feeds the hot lug of
a 250 kΩ-L Treble pot and a 100 kΩ slope resistor drops to the slope foot,
where the Treble pot's cold lug also sits — so far as the AB763 draws it. The
Bass control is different: a 250 kΩ-A pot wired as a **divider** from the
slope foot to ground, with the 0.01 µF bass capacitor across its upper
section (hot lug to wiper) and a 10 kΩ foot resistor across its lower (wiper
to ground). Turned up, the wiper shorts the capacitor out and the slope foot
sees the 10 kΩ; turned down, the capacitor goes straight to ground and the
lows go with it. The Treble wiper alone is the network's output.

**The two second stages are loaded differently**, which is what the chart's
**+160 V** and **+120 V** record. Channel 1's plate returns to its supply
through 100 kΩ and then a 6.8 kΩ decoupling resistor, and its output is taken
from the junction of the two, not from the plate. Channel 2's plate load is a
single 220 kΩ. Channel 1 alone has a 47 pF bright capacitor from its Volume
control's hot lug to the wiper; neither page of the drawing shows one on
channel 2.

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
tone tilts from bass to treble and back at the Speed setting. The splitter
prints **+180 V** at its plate and **+1.5 V** at its cathode (1.5 kΩ / 25 µF).

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

A 7025 **long-tailed pair** — 82 kΩ (hot) and 100 kΩ (cold) 5 % plate loads,
printed **+315 V / +310 V**, with 47 pF across the two plates and an 820 Ω
shared cathode (**+23 V**) into a 6.8 kΩ tail — drives the **6L6GC pair**
through 0.05 µF couplers, fixed-biased at **−55 V** through 220 kΩ · 5 %
leaks, with 470 Ω · 1 W screen resistors. The tail lands on a foot node
carrying a **1.5 kΩ** resistor to ground, the **10 kΩ** negative-feedback
resistor from the output transformer's secondary, the 0.1 µF that grounds the
cold grid for signal, and the **5 kΩ-L Presence** control in series with a
**0.1 µF** capacitor, which makes that branch AC-only. The 6G3 Deluxe shares
that foot, a bare 1.5 kΩ to ground with the feedback return landing on it,
but carries no Presence control at all and takes its feedback through 56 kΩ.

## Power

The GZ34 feeds two 20 µF reservoir cans, then the standby switch. The output
transformer's centre tap takes **+460 V** there, ahead of the choke; after the
choke, **+458 V** feeds the 6L6GC screens and every dropper, and the plates,
through the output transformer, print **+456 V**. From there
each rail has its own dropper and its own 20 µF can:

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
oscillator supply excepted, for the reason above. A separate bias-tap
rectifier, 8 µF, 10 kΩ, then 8 µF with a 56 kΩ bleeder deliver the fixed
**−55 V**.

## Why this entry is draft

The chain from the plate rail down to every stage is derived through
resistors the drawing letters, and every printed stage voltage is compared
with the model. Two things stand between that and `verified`: the excluded
oscillator leaves its own supply reading high, and four of the compared
figures appear on the layout page only. `verified` is granted by the
maintainer's review in any case, never by the checks alone.

**No sharper copy of the 6G4 sheet is publicly archived.** Every mirror of
the two-page schematic-and-layout scan that could be found — el34world,
Schematic Heaven, Prowess Amplifiers — serves the same single 2002 scan:
byte-identical files, or re-saves of the identical embedded page images with
no new information in them. Several archives carry only the *following*
production revision, the 6G4-A (a 2× 5881 output pair and a different preamp
complement — a different drawing, and the one this entry's own sources
distinguish it from). That one scan is enough: at its full resolution it
letters every dropper and every rail this circuit uses.

## Nine sections, five bottles

The published layout page draws exactly five noval sockets alongside the GZ34
and the two 6L6GCs, and the voltages it letters at each socket say which
stage each half carries. From the input end: V1 holds both channels' first
stages, V2 both second stages, V3 the vibrato oscillator and its splitter, V4
the vibrato pair, and V5 the phase inverter — ten triode sections, all used.
