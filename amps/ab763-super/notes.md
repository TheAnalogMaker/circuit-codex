# AB763 — Blackface Super Reverb-style

The 4×10, 6L6GC step up from the Deluxe Reverb: a 40-watt combo running the
same reverb-and-tremolo Vibrato channel as its blackface siblings, but on a
bigger power section and — as printed on its own schematic — a genuinely
asymmetric pair of tone stacks. The blackface Super Reverb ships under the
AA763 drawing from 1963 and moves to the AB763 revision below for the rest of
its run, 1964 to 1967. Two channels feed the shared output stage: a plain
**Normal** channel and a **Vibrato** channel carrying the reverb and the
tremolo, into a fixed-biased 6L6GC pair through a 12AT7 phase inverter,
rectified by a GZ34. The preamp bottles are marked **7025** on the drawing,
the low-noise selected version of the 12AX7; the tremolo oscillator is
labelled plain 12AX7; the reverb driver and phase inverter are **12AT7s**.

## Signal path

**Normal channel.** Two inputs (each a 68 kΩ stopper on a 1 MΩ leak) → a
12AX7 stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF bypass) → a
**two-knob** tone stack — Treble and Bass only, the middle leg tied to a fixed
6.8 kΩ bleed resistor rather than a control — and a 1 MΩ volume with its own
120 pF bright switch. No reverb, no tremolo.

**Vibrato channel.** Input stage as above → a **three-knob** tone stack —
Treble, Bass, **and Middle**, where the Normal channel's fixed bleed resistor
is replaced by a genuine 250 kΩ-A potentiometer — and its own 120 pF bright
switch → a second 12AX7 stage (100 kΩ plate, 820 Ω cathode). This stage's
output feeds two places: a 500 pF cap to the reverb driver, and (through a
0.02 µF cap) the dry side of the reverb/tremolo mix network.

The two tone stacks are not the same circuit with a knob added — the Normal
channel's middle leg is hard-wired to ground through 6.8 kΩ, full stop, while
the Vibrato channel's is a control a player turns. This is read directly off
the schematic, not inferred from the panel layout.

**Reverb.** The dry Vibrato signal drives a **12AT7 with both triodes in
parallel** (2.2 kΩ shared cathode) into the 125A20B transformer and the
spring tank — the same reverb-transformer part number the Deluxe Reverb and
Twin Reverb entries in this corpus cite. The returned signal comes back
through a 12AX7 recovery stage (100 kΩ plate, 820 Ω cathode, grid on a 220 kΩ
leak from the tank) and is blended with the dry signal by the 100 kΩ Reverb
control before reaching the mix driver.

**Tremolo.** A 12AX7 phase-shift oscillator (Speed on a 3 MΩ reverse-audio
pot) drives an **optocoupler** — a neon lamp facing a photoresistor — that
periodically shunts the mix-driver's grid to ground. The Intensity control
sets how hard the lamp is driven.

**Mix driver and phase inverter.** A third 12AX7 stage (100 kΩ plate, 820 Ω
cathode, 3.3 MΩ grid leak, 10 pF bright cap) sums the dry Vibrato signal and
the recovered reverb, is shunted by the tremolo optocoupler, and drives a
12AT7 **long-tailed pair** (82 kΩ and 100 kΩ 5% plate loads, a 470 Ω cathode
resistor to a tail junction, 22 kΩ tail to ground, both 1 MΩ grid leaks
returned to that junction) — exactly the tail values amps/ab763's own phase
inverter uses. The pair splits the signal for the **6L6GC pair**, each output
tube fixed-biased at **−52 V** through a 220 kΩ leak *and its own 1.5 kΩ grid
stopper* — a resistor the Deluxe Reverb's 6V6GT stage does not carry — with
470 Ω · 1 W screen resistors, and an 820 Ω negative-feedback loop returning
from the speaker to the inverter.

## Power

360-0-360 V (power transformer 125P5D) → **GZ34** → a pair of 70 µF · 350 V
reservoir caps (with 220 kΩ balancing bleeders off the standby switch) →
filter choke (125C1A) → **+460 V** at the 6L6GC plates (the output
transformer 125A9A's centre tap reads +465 V on the chart, 5 V above the
plate reading — merged to one modelled rail, the primary DCR omitted, exactly
as amps/ab763 merges its own +415 V/+420 V pair) → **+460 V** screens (via
470 Ω · 1 W stoppers) → a printed **1 kΩ** dropper → **+450 V** at the
phase-inverter plates and the reverb-driver plate → a printed **4.7 kΩ**
dropper → **+410 V** at every 100 kΩ-loaded preamp stage. A separate PT tap
feeds a silicon-rectified, 25 µF-filtered supply through an **adjustable
10 kΩ-L pot** for the **−52 V** fixed bias — unlike the Deluxe Reverb's fixed
bias-balance arrangement, this platform lets the player (or the tech) trim
the output-tube bias directly, the same feature amps/ab763-twin's own bias
supply carries.

## Bias and lineage

The blackface Super Reverb inherits its fixed-bias, GZ34-rectified, 2×6L6GC
output section directly from the brown-Tolex Super — the [6G4](/amps/6g4/) —
rather than from any tweed circuit, carrying over the same 40 W rating, the
same output-tube count, and the family's long-standing "power ratings vary by
source" caveat (see history/families/super.yaml). The AB763 revision adds the
reverb/tremolo Vibrato channel and the asymmetric tone-stack pair documented
above; the Normal channel's simpler two-knob stack is the closer cousin of
the Deluxe Reverb's own (both channels, in that amp).

## Reading against the printed chart

The drawing prints a full voltage chart at every preamp, phase-inverter and
reverb-driver stage, all at the sheet's own ±20 % convention (rails held to a
tighter target). One rail is driven at its charted value (BP1 = +460 V, the
6L6GC plate/screen supply); the two rails below it (+450 V, +410 V) are
**derived** through the drawing's own printed dropper resistors (1 kΩ, then
4.7 kΩ) rather than driven directly, so their simulated values are a genuine
check against the chart — the same modelling choice amps/ab763-twin makes for
its own BC/BD pair, and a step more rigorous than amps/ab763's, which drives
both of its own two upper rails independently.

## Exclusions and what is reported, not gated

- **The tremolo oscillator (V5, 12AX7).** A running phase-shift oscillator
  has no static DC operating point — its printed pins are the average a meter
  reads while it swings, set by grid-leak detection — so it is documented
  here rather than modelled in netlist.cir, the same treatment amps/ab763 and
  amps/ab763-twin give their own tremolo stages. Its supply taps BP1, a
  **driven** node, so excluding it shifts no gated node's simulated value —
  unlike amps/ab763, whose tremolo shares a *derived* input-stage rail and so
  does move one.

- **BC and BD are derived, not measured inputs.** Both carry a `chart:`
  value in voltages.yaml precisely so a passing run of `verify_amps.py`
  demonstrates the drawing's own two dropper resistors reproduce its own two
  printed rail voltages under the modelled preamp/PI load — a genuine
  cross-check the pilot amps' single-driven-rail approach does not offer.

## Three cathodes the chart and the drawing disagree about

Seventeen of the twenty gated nodes land, several of them tightly: both
derived rails reproduce their printed values to within half a percent through
the drawing's own droppers, and both input stages land within one percent at
plate and cathode alike.

Three do not, and they are the same three stages — the Vibrato channel's
second stage, the mix driver and the reverb recovery. All three are drawn the
same way: a **100 kΩ** plate load off the +410 V rail over an **820 Ω**
cathode resistor. All three miss in the same direction and by about the same
amount.

| node | printed | simulated | |
|---|---|---|---|
| Vibrato 2nd stage cathode | 2.1 V | 1.5 V | **−30.4 %** |
| mix driver cathode | 2 V | 1.5 V | **−26.9 %** |
| reverb recovery cathode | 2 V | 1.5 V | **−26.9 %** |
| their plates (all three) | 270 V | 231 V | −14.4 % |

The chart's own two figures for these stages do not close on each other. Take
them as printed: 2.1 V across 820 Ω is 2.6 mA, and 2.6 mA through a 100 kΩ
plate load drops 260 V, which off the +410 V rail would put the plate at
+150 V — not the +270 V printed two pins away. Run it from the plate instead
and the +270 V reading implies 1.4 mA, which across 820 Ω is 1.2 V, not the
2.1 V printed. The simulation sits between the two, self-consistently: 1.8 mA,
1.5 V at the cathode and 231 V at the plate.

So the deviation is not a stage that fails to solve; it is a printed pair that
cannot both be right for the parts the sheet draws. Whether the cathode
figures were read at a shared box serving more than one section, or the plate
loads on these three stages are not the 100 kΩ read here, is not settled by
this scan. It is published as the miss it is rather than tuned away, and it is
the reason this entry is a draft.

## Verification

`verification.status` stays `draft`, and nothing here sets it: that flip is
the maintainer's, never an agent's. What the entry does carry is a
`wiring_claim: verified` on the board drawing — a narrower claim, and one the
equivalence gate actually proves, that every run drawn on the board is
electrically the same net the netlist declares within the documented DC scope.

The full artifact set is present: schematic, board layout in both styles, the
social card, and the family-tier entry. The three cathode nodes above are the
open question a sign-off pass has to weigh.
