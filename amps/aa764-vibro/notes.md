# AA764-VIBRO — Blackface Vibro Champ-style

Fender's smallest amp gains a trem foot. The Vibro Champ is the AA764 drawing
family's tremolo-equipped sibling: the same five-watt, single-12AX7-preamp,
single-ended-6V6 recipe as the plain [Champ](/amps/aa764/), plus a second,
dedicated 12AX7 running a bias-vary tremolo oscillator ahead of the same
output stage. Fender's own drawing prints **"VIBRO-CHAMP AA764"** — the
identical designation the non-tremolo Champ sheet carries — so this circuit
is filed under the qualified id `aa764-vibro`, leaving the plain Champ's
`aa764` to the drawing that carries no tremolo. Two print runs of the
drawing exist (an earlier "Fender
Electric Instrument Company" letterhead and a later CBS-era "A Division of
Columbia Broadcasting System" one); both carry the AA764 designation and the
same component values, and the earlier printing is the one cited here.

## Signal path

Identical to the [Champ](/amps/aa764/), component-for-component. Two input jacks (high and
low) each sit behind a **68 kΩ** grid stopper and share a **1 MΩ** leak to
ground. From there:

**V1A** — 12AX7, **100 kΩ** plate load, **1.5 kΩ** cathode with a **25 µF**
bypass. Its plate feeds the tone stack directly; both stack legs start with a
capacitor, so no DC reaches the controls.

**Tone stack** — the blackface treble-bass network. A **250 pF** cap carries
the top end onto the **250 kΩ Treble** control; a **100 kΩ** slope resistor
feeds a **0.1 µF** cap into the junction below the treble pot and a
**0.047 µF** cap into the **250 kΩ Bass** control's lower leg, which returns
to ground through **15 kΩ**. The treble wiper hands the recovered signal to a
**1 MΩ** Volume control.

**V1B** — 12AX7, **100 kΩ** plate load. Its cathode resistor is **1.5 kΩ**
with a **25 µF** bypass, but it does not land on ground: it sits on a
**47 Ω** leg, and the **2.7 kΩ** negative-feedback resistor from the speaker
jack lands on that same junction.

**Output** — a **0.02 µF** coupling cap into the **6V6GT** grid, held down by
a **220 kΩ** leak. The 6V6 is cathode-biased on **470 Ω · 1 W** with a
**25 µF** bypass, its screen wired straight to the second filter node with no
stopper, and its plate working into the **125A35A** single-ended output
transformer — the same transformer aa764 uses.

## Tremolo

A dedicated second 12AX7 bottle (both sections) — unlike the shared-
tube trem in [6G3](/amps/6g3/), where the oscillator is the second half of the
driver tube, this is its own socket, the same arrangement the
[Deluxe Reverb](/amps/ab763/) uses for its trem oscillator.

**First section** — an RC phase-shift oscillator. The **Vibrato Pedal** jack
carries a normalling switch (open when the pedal is plugged in, letting the
external footswitch mute the effect; shorted otherwise, so the trem runs
whenever nothing is plugged in) ahead of a **1 MΩ** bleeder and a **1 MΩ**
grid leak. Plate load is **470 kΩ** off the B+3 preamp rail, printing
**+170 V**; cathode is **4.7 kΩ** with a **25 µF** bypass, printing **+1.6 V**.
The frequency-setting network runs through a **3 MΩ reverse-audio Speed**
control with a **100 kΩ** fixed leg to ground — the same 3 MΩ Speed value
the Deluxe Reverb uses for its own (opto-coupled) oscillator, though the two
circuits inject the signal differently.

**Second section** — wired as a cathode follower: its plate ties straight to
the B+2 rail (**+340 V**, no plate load resistor), and its **68 kΩ** cathode
prints **+175 V**, feeding a **25 kΩ reverse-audio Intensity** control that
sets how hard the oscillator's signal is injected into the amp.

This is a **bias-vary** tremolo — it works by varying a DC operating point in
sympathy with the oscillator, the family AB763's opto-coupled Deluxe Reverb
trem does not belong to — consistent with the single-ended Champ/Princeton
line's small-amp trem circuits generally. Unlike 6G3's fixed-bias output
stage, this 6V6 is cathode-biased, so there is no separate negative-bias line
for the oscillator to modulate; the Intensity control's output lands in the
same corner of the sheet as the negative-feedback network ahead of the output
stage. The exact phase-shift coupling capacitor between the first section's
grid network and the Speed control is present on the drawing but was not
individually confirmed at the available scan resolution (C16 in the parts
list); every other oscillator value above was read directly off the sheet.

## Power

315-0-315 V from the **125P1B** power transformer — the same part number
the Champ's 320-0-320 V winding prints; the two AA764-family drawings simply
print their own figures for the identical transformer, a habit of the era's
Fender sheets that the Princeton family's drawings repeat — →
**5Y3GT** full-wave rectifier → three **20 µF · 450 V** filter cans. The
chain reads **+355 V** at the reservoir (which also feeds the output
transformer primary), **+340 V** after a **1 kΩ · 1 W** dropper at the 6V6
screen, and **+320 V** after a **10 kΩ · 1 W** dropper at both 12AX7 plate
loads — the same dropper values the Champ uses, each rail printing a few volts
lower here, plausibly the tremolo oscillator's added current draw. A 1 A
slow-blow fuse and an AC switch sit ahead of the primary.

## Excluded from the DC model: the tremolo oscillator

The tremolo oscillator (V4, both sections) is a running phase-shift
oscillator — it has no static quiescent point, the same category of
exclusion as the Deluxe Reverb's V5. Its printed chart pins (+170 V / +1.6 V
first section, +340 V / +175 V second section) are read directly off the
sheet and recorded on this page, but are not modelled or gated: the
simulated deck omits V4 entirely.

Its first section's plate load taps the same **BP3** preamp rail that feeds
V1A and V1B (through its own 470 kΩ, off-model). Leaving the oscillator out
therefore means BP3 carries a little less current in this model than the
real circuit did, and the two audio-path plates it feeds read a bit above the
printed chart as a result — the same effect the Deluxe Reverb entry documents
for its own shared rail. Here, though, the deviation stays well inside the chart's own
±20 % convention (see below), so P1A/K1A/P1B/K1B are gated normally rather
than set aside as informational.

## Reading against the printed chart

The drawing prints a full voltage chart, every value set at ±20 %, read to
ground with an electronic voltmeter. Driving the reservoir at its printed
**+355 V** and solving everything below it:

| Node | Chart | Simulated | Deviation |
|---|---|---|---|
| Screen rail (BP2) | +340 V | +349.1 V | 2.7 % |
| Preamp rail (BP3) | +320 V | +326.9 V | 2.2 % |
| V1A plate / cathode | +205 V / +1.6 V | +215.0 V / +1.7 V | 4.9 % |
| V1B plate / cathode | +200 V / +1.5 V | +216.6 V / +1.7 V | 8.3 % / 13.7 % |
| 6V6 cathode (K2) | not printed | +22.2 V | informational |

Every gated node lands comfortably inside the drawing's own ±20 % convention
— the worst is V1B's cathode at 13.7 %, still well short of the tremolo-
excluded shared-rail effect crossing that line the way it does on the
Deluxe Reverb.
The 6V6 cathode has no printed figure to compare against; the drawing prints
only **+2 V** at its grid (pin 6), a small positive reading typical of a
cathode-biased stage's grid-leak return rather than a value worth gating.

One value on the chart is deliberately not simulated. The drawing prints
**+355 V** at the reservoir and **+342 V** at the 6V6 plate; the gap between
them is the output transformer primary's winding resistance, which the
drawing does not publish — the same convention the Champ entry documents for
the same 125A35A part.

## The tremolo block, as drawn

The schematic and the board layout on this page resolve the connections the
parts list's per-part roles leave implicit. V4A's plate feeds back to its
own grid through C16 and the Speed control — a single-RC phase-shift loop,
the pot's resistance setting the frequency. V4B is direct-coupled from V4A's
plate (no capacitor — the drawing shows none) and wired as a cathode
follower whose plate ties straight to the B+2 rail with no plate load
resistor; its cathode, through the Intensity control, injects the
oscillator's signal directly at K2, the 6V6 cathode/bias node — the
bias-vary mechanism. The Vibrato Pedal jack's internal normalling contact is
not drawn as a mechanical spring switch; its effective point-to-point
connection (tip into the bleeder/coupler line, sleeve to ground) is drawn
instead. The oscillator's own RC network mounts off the board — at the
Speed and Intensity pot lugs and the jack — the same convention the Deluxe
Reverb entry documents for its own dedicated trem-oscillator network; only
V4's heater pins are wired on the board, extending the single-ended daisy
chain. The board otherwise reuses the Champ's arrangement verbatim, since
the two circuits' audio paths are component-for-component identical (see
above). The drawn wiring is proved electrically equivalent to the simulated
circuit, with V4 excluded from that check just as it is excluded from the
deck.
