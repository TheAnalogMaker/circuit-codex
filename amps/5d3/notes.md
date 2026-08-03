# 5D3 — Wide-panel Tweed Deluxe-style

The last wide-panel Deluxe, and the circuit the famous 5E3 grew out of. It is
the revision that retired the octal 6SC7 preamp for the modern nine-pin pair —
a 12AY7 feeding a 12AX7 — and it drives its cathode-biased 6V6GT pair through a
**self-balancing paraphase** inverter rather than the cathodyne that would
follow. It also drops the negative-feedback loop the 5C3 had introduced, which
is why the wide-panel run ends on the open, compressing voice the narrow-panel
amps kept. Produced 1954–1955.

## Circuit walkthrough (short form)

Three input jacks — channel 1 a single jack on a bare 1 MΩ leak, channel 2 two
jacks each through a 68 kΩ stopper onto its own 1 MΩ leak → **V1** 12AY7 (100 kΩ
plate loads, shared 820 Ω cathode bypassed by 25 µF) → 0.05 µF couplers → two
1 MΩ volume pots and the 1 MΩ tone control (500 pF and 0.005 µF) → **V2A** 12AX7
(100 kΩ plate, 1.5 kΩ bypassed cathode) → **V2B paraphase inverter** (100 kΩ
plate, 1.5 kΩ *unbypassed* cathode, 100 pF across the two plates) → 0.05 µF
couplers → **V3/V4** 6V6GT pair (no grid stoppers, shared 250 Ω 5 W cathode
bypassed by 25 µF) → output transformer with a second jack for an extra 8 Ω
speaker. No feedback loop anywhere.

Power: centre-tapped HT → 5Y3GT → three 16 µF/450 V nodes separated by **two
10 kΩ droppers**: B+1 (output plates and the transformer centre tap) → B+2
(screens) → B+3 (all four preamp plate loads).

## How the paraphase balances itself

The inverter is the circuit's signature, and it works nothing like the cathodyne
that replaced it. V2A is an ordinary gain stage; its plate drives the upper
6V6's grid through a coupler. That grid is held down by a **220 kΩ** leak — but
the leak does not go to ground. It meets the lower 6V6's **270 kΩ** leak at a
junction, and only from there does **56 kΩ** run to ground. That junction is
also V2B's grid.

So V2B is fed a tap of whatever signal is standing on the two output grids. When
the two sides are unequal, the difference appears at the junction, V2B amplifies
and inverts it, and its plate pushes the lower grid until the imbalance closes —
a see-saw that trims itself. The asymmetric 220 kΩ/270 kΩ pair is the trim: the
inverting side is deliberately fed a slightly smaller share so its extra stage of
gain does not overshoot. The 100 pF bridging the two plates tames the top end of
the loop.

At idle none of this moves a meter. No grid current flows, so the junction, both
output grids, and both driver grids all sit at zero, and each 12AX7 section
self-biases on its own 1.5 kΩ. The unbypassed cathode on V2B is the one visible
asymmetry, and it is deliberate: it holds the inverter's gain down to roughly
what the driver in front of it produces.

## What changed on the way to the 5E3

The 5D3 and the 5E3 share a tube complement, a tone control, an output stage and
a rectifier, but almost every detail between them moved:

| | 5D3 | 5E3 |
|---|---|---|
| Phase inverter | Self-balancing paraphase (both 12AX7 sections) | Cathodyne (one section) |
| Input jacks | 3 | 4 |
| Couplers | 0.05 µF | 0.1 µF |
| Rail droppers | 10 kΩ, 10 kΩ | 5 kΩ, 22 kΩ |
| 6V6 grid leaks | 220 kΩ / 270 kΩ into a 56 kΩ return | 220 kΩ each, straight to ground |
| 6V6 grid stoppers | none | 1.5 kΩ each |

The cathodyne swap is the one that matters. It frees the second 12AX7 section to
become the extra gain stage that gives the 5E3 its bite, and it trades the
paraphase's self-trimming balance for a topology that is balanced by
construction. Everything else follows from that: bigger couplers to feed the new
stage, a different dropper split to hold the preamp rail up under it, and grid
stoppers to keep the hotter drive from ringing.

## Verification

The published 5D3 sheets supply every component value but print no voltage chart
— only Fender's ±20 % measurement notice. The 5C3 drawing immediately before it
does print one, and the two circuits share the power transformer class, the
5Y3GT, all three 16 µF filter nodes, both 10 kΩ droppers and the whole output
stage, so its reservoir figure of **360 V** is the value B+1 is driven at here
and its **+18 V** across the 6V6 cathode resistor is a fair target. Simulation
puts that cathode at **16.8 V — 6.9 % off**, comfortably inside the era's
convention.

The rails are reported, not compared. The 5C3 prints +308 V and +280 V for the
screen and preamp nodes, but it feeds a pair of 6SC7s through 250 kΩ plate loads
where this circuit feeds four 100 kΩ loads, so more current crosses the same two
10 kΩ droppers and the rails must land lower: simulation gives **269 V** and
**230 V**, with the 12AY7 plates at 120 V and both 12AX7 plates at 149 V. Those
are consistent, but they are this circuit's numbers checked against a different
preamp's chart, which is not a verification. The 5D3 stays a draft until a
voltage chart measured on a 5D3 is available.
