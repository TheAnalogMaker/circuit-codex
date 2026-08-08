# JTM100 — British 100-watt lead-style

The head that doubled Marshall's output stage. Players wanted more volume on
stage than 45 watts gave, and the answer was arithmetic rather than invention:
take the JTM45, keep the front end almost untouched, and hang four KT66 beam
tetrodes on a much stiffer supply. Nothing about the preamp announces the
change — four jacks, two channels, a direct-coupled cathode follower feeding a
treble-middle-bass stack, a long-tailed-pair inverter. Everything after the
inverter is new: two output valves become four, the GZ34 rectifier valve
disappears in favour of silicon, and the plate rail climbs from the JTM45's
450 V to **560 V**.

That last number is the character of the amplifier and also its reputation. A
KT66 is rated for 25 W of plate dissipation; at 560 V there is very little room
between a usable idle current and the rating, which is one reason the 100-watt
heads moved to EL34s and then to lower rails within a couple of years. The
amplifier documented here is the KT66 window: 1965 into 1966, the era of
left-over JTM45 front panels on 100-watt chassis that gave these heads their
other common name, JTM45/100.

## Circuit walkthrough (short form)

Four jacks across two channels (1 MΩ leaks, 68 kΩ stoppers) → **V1** ECC83
(100 kΩ plates, one shared 820 Ω cathode with a 25 µF bypass) → 0.02 µF
couplers → 1 MΩ volume pots (100 pF bright cap across the second) → 270 kΩ
mixers → **V3A** ECC83 (100 kΩ plate, unbypassed 820 Ω cathode) → **V3B
cathode follower, DC-coupled** (100 kΩ load) → TMB stack (56 kΩ slope; 270 pF,
0.02 µF and 0.02 µF; 250 kΩ / 1 MΩ / 25 kΩ pots) → 0.02 µF → **long-tailed-pair
PI**: 82 kΩ and 100 kΩ plates, 47 pF across them, 470 Ω from the joined cathodes
to the tail junction where both 1 MΩ leaks return, then 10 kΩ down to the
presence pot → 0.1 µF couplers onto two phase nodes, each with a 220 kΩ grid
leak to the bias line → **four KT66s**, 1 kΩ · 5 W screen stoppers on all four →
output transformer, whose secondary leads the sheet letters by colour — blue for
a 100 V line tap, white 16 Ω, yellow 8 Ω, orange common — with 27 kΩ of negative
feedback from the 16 Ω tap.

Power: a universal-primary mains transformer (110/250 V), two arms of three
series silicon diodes and a standby switch into a reservoir of three series
32 µF pairs — a 2 A slow-blow fuse in the mains lead, a 1 A slow-blow in the HT
centre-tap return — **560 V**, feeding the output plates
through the transformer primary. A **20 H choke** takes that to the **559 V**
screen node; 8.2 kΩ and a 32 µF drop to the **470 V** inverter rail; 10 kΩ · 1 W
and 16 µF drop again to the **390 V** preamp rail. The negative grid bias has
its own diode, a 470 kΩ trim, 150 kΩ, a 56 kΩ / 16 kΩ divider and two 8 µF
filters, and the drawing circles **−65/−66 V** at it.

## Two things the drawing does that a tidy redrawing would not

**The presence control sits inside the tail, not beside it.** On the JTM45 the
inverter's 10 kΩ tail goes to ground and the presence pot and feedback resistor
join it there. Here the 10 kΩ lands on the *top* of the 5 kΩ presence pot, and
the pot completes the path to ground. The chart proves it rather than merely
allowing it: 52 V at the inverter cathodes with 310 V and 300 V plates off a
470 V rail means 3.65 mA in the tail, which needs about 14 kΩ to ground — the
10 kΩ alone would put the cathodes near 37 V. The drawing then circles 16 V at
the pot's top, which is what 3.65 mA through 5 kΩ gives. Three independently
printed numbers agree on one topology.

That node is also where the feedback arrives and where the inverter's second
grid is driven from: the 27 kΩ comes down to it from the 16 Ω tap, and a 0.1 µF
couples it up to the V4B grid. The two 1 MΩ grid leaks return not there but to
the junction *between* themselves, one 10 kΩ further up the tail — a distinction
the sheet draws plainly and a redrawing can easily lose.

**Only half the output valves get a grid stopper.** Each phase node feeds one
valve through a 15 kΩ stopper and the other valve's grid directly off the node —
V5 and V8 stoppered, V6 and V7 not. That is what the sheet draws, at every
zoom level, and it is reproduced rather than symmetrised. It costs nothing at
DC (no grid current, so all four grids sit on the bias line either way) and it
is exactly the sort of detail a redrawing quietly "fixes" into something the
factory never built.

## Lineage

The JTM100 is the JTM45 with its output section doubled, and through the JTM45
it descends from the tweed 5F6-A Bassman. Forward, it is the circuit Marshall
catalogued as the **1959** Super Lead: the corpus's `m1959` entry documents the
July-1970 factory drawing of that model, by which point the KT66 quartet had
become four EL34s and the choke-and-dropper supply had been rearranged. The
100-watt line's 50-watt sibling took the same path from JTM50 to the
model 1987.

## The tone network, as the drawing wires it

The stack is the JTM45's, one component value apart: 56 kΩ slope resistor,
270 pF across the treble pot, 250 kΩ treble, 1 MΩ bass, 25 kΩ middle. Where the
JTM45 uses 0.01 µF for the middle cap this sheet letters **0.02 µF**, so both
the bass and middle caps read the same value. The later cataloged 1959 drawing
replaces the whole front of the stack with 500 pF and 33 kΩ; that change is not
in this sheet.

## Verification — against the printed factory chart

This drawing prints a full **VALVE VOLTAGE CHART**, measured "to chassis under
no signal conditions with an AVO Model 8 Mk II, meter sensitivity 20,000 Ω/V",
and it circles six further node voltages on the schematic itself. That is a
richer measurement basis than any other Marshall sheet in the corpus, and the
circuit reproduces it well: every rail lands within 4.3% of its circled figure,
every preamp and inverter plate within 3.5%, and all three hand-meter cathode
readings within 8%. The worst node is the presence-pot top at 13.1% — a
single-digit reading set by tube current rather than by a stiff supply.

The entry is nonetheless published as a **draft**, for two reasons that have
nothing to do with the chart.

The first is the output stage. The v0 KT66 model is an anchor-point fit taken at
250 V (models/METHODOLOGY.md); this circuit runs its screens at 559 V, and at
that operating point the model idles each valve near 72 mA — about 40 W against
the KT66's published 25 W rating. Real amplifiers of this type are set far
colder. Nothing in the gated node set depends on that current (the model draws
no screen current here at all, so the 1 kΩ stoppers show no drop and the screen
nodes read exactly the rail), but a circuit whose output valves simulate at 160%
of their rating is not one to stamp verified.

The second is the chart's own two silent cells. The inverter grids are printed
as "+" rather than a number, and the KT66 control-grid cell is a hand-lettered
range that the archived scan does not render legibly, so the modelled bias comes
from the schematic's circled −65/−66 V instead of from the chart. Both nodes are
reported informationally rather than gated.

## A naming note

The title block reads "BASIC SCHEMATIC FOR MARSHALL 100 WATT SUPER TREM AMP /
TYPE 1959T", and it is the tremolo version of the head — the same relationship
the corpus's `jtm45` entry has to its own factory sheet, which is likewise a
trem drawing read for the plain head. The sheet's V2 tremolo valve and the
transistor-driven depth network that shunts the V3A grid node are omitted here,
which is why the valve numbering skips from V1 to V3. The circuit is filed under
the era designation the schematic archives use for the 1965–67 100-watt heads,
JTM100, because the bare `1959` designation belongs to the cataloged EL34 head
already documented at `m1959` and the two are different circuits.
