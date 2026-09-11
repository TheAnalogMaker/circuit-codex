# 5E5-A — Tweed Pro-style

The last and best-known tweed revision of Fender's Pro amp: a two-channel
12AY7 front end, a second 12AY7 used as a gain stage DC-coupled into a
cathode follower, a follower-fed Treble/Bass network with a Presence control,
a 12AX7 driver + split-load (cathodyne) phase inverter, and a fixed-bias
6L6GB pair into a single 15-inch speaker. Produced 1956–1960, it is the
circuit that reintroduced negative feedback (and the Presence control) after
the immediately preceding 5E5 had removed both. Mic and instrument each get
their own gain stage before they are mixed, and the mixed signal gets a
second gain stage and a cathode follower before the tone controls — the shape
the 5F4 Super, 5E4-A Super and 5F6-A Bassman in this corpus also use.

## Circuit walkthrough (short form)

Instrument channel (68 kΩ stopper, 1 MΩ leak) → **V1A** 12AY7 ↘
Mic channel (68 kΩ stopper, 1 MΩ leak) → **V1B** 12AY7 ↗ shared 820 Ω
cathode, 100 kΩ plates → 0.02 µF couplers → 1 MΩ INST VOL / MIC VOL pots
(a 100 pF bright cap across INST VOL only) → 270 kΩ mixers → **V2A**, a 12AY7
gain stage (100 kΩ plate, 1.5 kΩ cathode bypassed by 25 µF), DC-coupled into
**V2B**, the same bottle's other section, a cathode follower with a 100 kΩ
cathode load.

The follower's cathode feeds the tone network: two branches that recombine
at the driver's grid. **Treble**: 250 pF into the Treble pot, whose other end
is bled to ground through 0.01 µF; the pot's wiper is the network's output.
**Bass**: 0.1 µF into a branch with 220 kΩ to ground and 100 kΩ onward into
the Bass pot's *wiper* (one end of that pot grounded, the other returned
through 0.005 µF), then 220 kΩ from that wiper to the output. A 5 MΩ resistor
runs from V2A's grid back to the bass branch; because the branch's 220 kΩ
holds that node at 0 V, it is also V2A's DC grid reference.

→ **V3A** 12AX7 driver (100 kΩ plate, 1.5 kΩ cathode) → 0.02 µF → **V3B
split-load cathodyne**: 56 kΩ plate, 1.5 kΩ + 56 kΩ under the cathode, 1 MΩ
grid leak returned to the junction → 0.1 µF couplers from the cathodyne's
**plate and cathode** into 1.5 kΩ stoppers → **6L6GB pair**, fixed-biased
through 220 kΩ leaks, screens tied straight to the screens rail → output
transformer into the 15-inch speaker (with an external-speaker jack). A
100 kΩ negative-feedback resistor returns from the speaker to the **driver's
cathode**, and the 5 kΩ **Presence** control hangs on the same node — a
rheostat to ground through 0.1 µF, which shunts the fed-back treble away so
that turning it up leaves the top end with less feedback.

Power: 5U4GA rectifier → **+390 V** (power-tube plates, 16 µF) → choke →
**+385 V** (screens, 16 µF) → 10 kΩ → **+300 V** (driver/PI, 16 µF) → 10 kΩ →
**+250 V** (preamp, 8 µF). A selenium rectifier supplies the **−32 V**
fixed-bias rail: 10 kΩ from a dedicated tap on the transformer's high-tension
winding — between one end and the centre tap, the red-blue lead on the
layout, never a rectifier plate — into the cell, then a 100 µF can with a
56 kΩ bleeder across it.

## The second stage

The J-EE schematic draws V2 as one envelope with both sections in use, and
the layout page confirms it at the socket. V2A's 100 kΩ plate load is
soldered across the V2 socket from pin 6 — the follower's plate, straight on
the +250 V rail — to pin 1, the gain stage's plate. A strap then runs from
pin 1 to pin 7, the follower's grid. The follower's cathode (pin 8) runs to
the eyelet printed +130 V, which carries the 100 kΩ load to ground and both
tone-network feeds. The gain stage's grid (pin 2) goes to the 270 kΩ mixers'
junction, and its cathode (pin 3) to the eyelet printed +1.9 V.

The printed figures agree with that reading. A follower's cathode sits a
volt or two above its grid, so a follower at 130 V puts V2A's plate near
128 V. V2A's 100 kΩ load then drops about 122 V from the 250 V rail, which is
1.2 mA — 1.8 V across its 1.5 kΩ cathode resistor, against the printed 1.9 V.

## Why the topology reads this way

The published tube-complement summaries for this amp are terse — "half
12AY7 / 12AY7 / half 12AX7" per channel plus "phase inverter: half 12AX7
(split load)" — but read as *stage chains* they resolve to exactly the
structure above. Each channel keeps its own first triode. Both channels share
a *whole* second 12AY7, one section a gain stage and the other the
cathode follower. The 12AX7's two halves are the driver and the cathodyne.
The Treble/Bass network off the follower's cathode is the one the 5F4 Super
and 5E4-A Super sheets draw, part for part, from the same Fender drafting
office in the same years.

## What is legible on this copy of the drawing

The published PDF carries each page as a single 1506 × 864 image, so
rendering it at a higher resolution adds no detail. At that resolution every
component value on the schematic page is legible, including V2's own
resistors (100 kΩ plate load; 1.5 kΩ with 25 µF · 25 V on the cathode;
100 kΩ under the follower) and both rail droppers (10 kΩ each). The schematic
page leaves one part unlettered, the 12AX7's interstage coupler; the layout
page prints 0.02 µF · 600 V on it. The layout page also prints three plate
voltages the schematic page leaves out: +125 V on each of V1's plates, +190 V
on the driver's plate and +245 V on the cathodyne's.

Two figures are estimated because no page letters them: the choke's DC
resistance (about 110 Ω, from the printed +390 → +385 V drop) and the output
transformer's primary impedance.

## Verification

Simulation lands all 15 printed nodes within tolerance. The largest
deviations are V1's shared cathode at 9.7%, the driver's plate at 8.9% and
V1's plates at 8.8%, all against the 20% tube-pin allowance. The rails sit
within 5.2% of their printed values against a 10% house tolerance. Both of
V2's printed nodes — V2A's cathode and the follower's — land within 3.3%, as
does the cathodyne's distinctive 58 V / 56.5 V cathode pair. As a draft
circuit these are reported, not gated.

The 100 kΩ feedback resistor is left out of the DC model. At DC it only
parallels the driver's 1.5 kΩ cathode resistor through the output
transformer's secondary, which moves that node by less than 1%.

## The board

The J-EE sheet set carries its own layout page ("FENDER 'PRO-AMP' LAYOUT
MODEL 5E5-A"), and the board diagram on this page is redrawn from it, left to
right as the sheet reads. The bias supply, the three 16 µF cans and the
fixed-bias 6L6GB support sit at the power end, then the driver and cathodyne,
then the tone network, the second 12AY7 and the 12AY7 input pair. Column
positions are this entry's own placement of that sequence, not a dimensioned
transfer of the sheet's grid.

The drawn point-to-point wiring is proved electrically equivalent to the
simulated circuit, so a lead traced across the board lands on the node the
netlist gives it. One part is drawn where it reads best rather than where the
factory mounts it: V2A's 100 kΩ plate load, which the layout page strings
across the V2 socket from pin 6 to pin 1, sits on the board beside the stage.
The tone network's 0.005 µF and 0.01 µF and its second 220 kΩ hang at the
pots, as the layout page draws them. The Presence control with its 0.1 µF,
and the Instrument volume's bright cap, are panel parts off the board.
