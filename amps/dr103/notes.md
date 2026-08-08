# DR103 — Hiwatt Custom 100-style

The DR103 is the amplifier the Hiwatt name is built on: a 100-watt head on four
EL34s, four inputs across two channels, and a control panel that carries a
master volume at a time when the British competition did not. Dave Reeves had
trained in the Royal Air Force and worked at Mullard; made redundant in 1966, he
founded Hylight in September of that year and built amplifiers for Ivor
Arbiter's Sound City shop. The DR103 began as one of those — a customised Sound
City L100, renamed the Custom 100 once it carried Reeves's own badge. From 1971
the wiring was standardised by Harry Joyce, a certified government wirer who
capped his own output at forty amplifiers a month, and the amplifier's
reputation for military-grade construction dates from that arrangement.

Where the Marshall lead heads of the same years aim at a lot of gain in a small
preamp, the DR103 spends its four preamp valves on control and drive. Two of
them are cathode followers. The tone stack is driven by one and the phase
inverter by the other, and the master volume sits between them — so the
amplifier can be turned down without the tone stack going limp, and the output
stage is driven from a low impedance no matter where the controls sit. That is
the "hi-fi" character people describe, and it is a circuit choice, not just the
Partridge iron.

## Circuit walkthrough (short form)

Four jacks — Brilliant high and low, Normal high and low — through 68 kΩ
stoppers and 1 MΩ leaks into **V1** ECC83, one triode per channel. Both halves
carry 220 kΩ plate loads and, unlike the Marshall heads, **share a single 1.5 kΩ
cathode resistor** bypassed by 100 µF: the two channels are voiced apart at the
coupling cap instead, 1 nF for Brilliant against 10 nF for Normal. Each plate
feeds its own 470 kΩ volume, and the two mix through 470 kΩ resistors into
**V2B** (220 kΩ plate, 2.2 kΩ unbypassed cathode) → **V2A cathode follower,
DC-coupled**, on a 120 kΩ 2 W load — the value is a warning about how much
voltage that triode stands off.

From there the tone stack: 100 pF into a 220 kΩ treble pot, a 100 kΩ slope
resistor, 47 nF into the 470 kΩ bass rheostat and a second 47 nF into the wiper
of a 22 kΩ middle pot. The treble wiper alone is the output, through 220 kΩ into
a 470 kΩ **master volume**.

**V3B** (100 kΩ plate, 2.2 kΩ cathode with a 47 nF bypass) is the driver, and
its plate reaches the next grid through an arrangement worth pausing on: a 22 nF
capacitor **in parallel with a 1.8 MΩ resistor**, working against a 1 MΩ grid
leak. That is a DC-coupled divider, not a coupling cap — the V3A grid sits at
roughly a third of the driver's plate voltage rather than at zero, and the
capacitor simply takes the signal round the resistor. **V3A** is the second
cathode follower, on 220 kΩ, wired **straight** into the phase-inverter grid
with no capacitor between them.

**V4** is an ECC81 long-tailed pair with deliberately unequal 82 kΩ and 91 kΩ
plate loads, a 22 kΩ tail down to a junction and 2.2 kΩ from there to ground.
Its second grid takes its DC reference from the first through 1 MΩ and is tied
to the tail junction for signal by 100 nF. Negative feedback returns from the
output transformer's 16 Ω tap through 10 kΩ **to that junction** — not to a
grounded point, as in the Marshall heads — so the feedback resistor is part of
the inverter's own tail network. The presence control hangs off the driver
plate: 1 nF in, a 100 kΩ pot with 100 R to ground, 47 nF back out to the same
junction.

Behind the inverter, 47 nF couplers feed two EL34s per phase through **22 kΩ**
grid stoppers — four times what the Marshall heads use — with one 100 kΩ grid
leak per pair carrying the fixed bias, and a 100 Ω stopper on every screen.

Power: a silicon bridge into a reservoir of two 220 µF · 350 V capacitors in
series with 220 kΩ balancing resistors, then a standby switch to HT1, which
feeds the output plates and the transformer centre tap directly. 100 Ω · 5 W
takes it to HT2; 470 Ω · 10 W carries HT2 on to the screen bus; 1 kΩ takes HT2
down to HT3, the preamp rail. HT3 then drops hard — 47 kΩ · 2 W to the
second-stage plate load, another 22 kΩ · 2 W to the input valve and the driver —
which is why the first stages idle around 160 V off a rail that starts near 480.
The bias supply is its own diode, a 1 kΩ series resistor, 100 µF and 47 kΩ, and
on every drawing read for this entry it is **fixed, with no trimmer**.

## Lineage

The documented ancestor is a customised Sound City L100, which has no entry in
this corpus, so `lineage.derived_from` is empty rather than pointed at a guess.
The DR103's siblings are the rest of the Hiwatt line — the 50-watt DR504, the
200-watt DR201 and the 400-watt DR405 — and one of the factory-lineage hand
sheets makes the relationship explicit: it is headed "HIWATT PREAMP AND DRIVE"
and lists, in one line, "DR504 DR405 DR103 DR201 ALL COMBO'S". The preamp and
driver documented here is the whole line's; what changes between models is the
number of output valves and the size of the supply.

## Two drawings, two decades — and which one this is

Four documents carry a DR103 title block, and they do not describe the same
amplifier:

- **"HIWATT / Late 60s Four-Input Preamp / Preamp from DR103 S/N 903 /
  Drawing rev. 1.0 - Mark Huss"** — a published redraw taken off a specific
  early amplifier. **This is the circuit documented here.**
- **"HIWATT DR103 LAYOUT, EARLY 1970'S"**, credited to Mark Huss with updates
  from Jukka K. and Brian Haberman, 2007 — the wiring diagram this entry's
  output stage, supply and control complement are read from.
- **"HIWATT DR103 PREAMPLIFIER CIRCUIT DIAGRAM  Drawn 19/05/95  Issue 4.
  S/No. AB0309 Onwards"**, with **"...POWER SUPPLY...  Drawn 22/11/94
  Issue 3."** and **"...OUTPUT STAGE...  Drawn 25/04/94  Issue 1."** — the
  factory sheets bound into the owner's manual. These are the *later* two-input
  revision: one jack per channel, a 220 kΩ master volume and a 100 kΩ middle,
  and they letter every preamp valve ECC83.

The four-input amplifier is the one people mean by "Hiwatt DR103", and no
factory drawing of it was found for this entry. That is stated rather than
papered over: the preamp values here come from a redraw, and a redraw is not a
factory document.

Two smaller disagreements are recorded rather than resolved. The early-1970s
wiring diagram gives 500 kΩ log volumes and bass, 250 kΩ lin treble and master
and a 100 kΩ lin middle where the S/N 903 amplifier carries 470 kΩ audio-taper
volumes, bass and master with a 220 kΩ treble and a 22 kΩ middle — in-era
variation across a hand-built run. And the manual contradicts itself about V4:
its specification page lists "Preamp valve V4  1 x ECC81 (12AT7)(6201)" while
the Issue-4 drawing letters "VALVES V1,V2,V3,V4 = ECC83". The specification, the
early wiring diagram and the S/N 903 drawing all say ECC81, so ECC81 is what
this entry records.

## A note on verification

This circuit is a **draft**, and it will stay one until measurements exist for
it. Three things keep it there.

There is **no valve-voltage chart**. Nothing published for the four-input DR103
prints an operating point, so every node in `voltages.yaml` carries `chart: null`
and nothing is gated. One printed figure is worth naming: the later factory
Issue-4 sheet annotates +160 V at the input valve's plate, on a stage that is
component-for-component this one — 220 kΩ load, shared 1.5 kΩ cathode resistor,
100 µF bypass. This circuit simulates 163 V there. That is a good sign and it is
not a verification, because the rail chain feeding that plate differs between the
two revisions.

**The supply rail is an assumption.** No DR103 drawing read here prints an HT
figure, so `netlist.cir` drives HT1 at 480 V and says so; the only published
Hiwatt HT figure found is the 460 V on the 50-watt DR504's July 1979 supply
sheet, and the DR103's supply is the larger one. Every other rail is derived
through the drawn dropper chain, so exactly one number is assumed.

**The EL34 model breaks down here.** At the −38 V bias the factory Issue-3 sheet
prints, and a screen at 467 V, the corpus's EL34 model returns about 95 mA per
valve — roughly 45 W of plate dissipation against the valve's 25 W rating, and
about twice what these amplifiers are actually set to. The model is a
single-anchor fit taken at a 250 V screen; the DR103 runs its screens nearly
twice that, far outside the fit, and the cut-off knee lands in the wrong place.
Nothing was adjusted to hide it. It does not disturb the preamp figures, because
the output plates hang directly on the driven rail and no preamp node sees their
current — but it is the reason the output stage's numbers should be read as a
model artefact rather than as a description of the amplifier.
