# JTM45 — British lead-style

Marshall's first amplifier, and the first time one maker's circuit crossed to
another: the JTM45 is a close copy of the tweed 5F6-A Bassman, rebuilt with
British parts. Fender's low-gain 12AY7 input valve becomes an ECC83 (the
European 12AX7), the 5881/6L6 output pair becomes a pair of KT66 beam
tetrodes, the mains-supply voltages run a little higher, and solid-state
diodes handle the bias supply. Everything downstream — the four inputs, the
direct-coupled cathode follower feeding a treble-middle-bass tone stack, the
long-tailed-pair phase inverter — is the Bassman, almost part for part. The
higher-gain input valve and the KT66 bottles are what turned a clean bass amp
into the seed of British rock tone. Produced from 1962; the drawing here is
the mid-1960s revision shared across the tremolo combos and the 1987 head.

## Circuit walkthrough (short form)

Normal (V1A) and bright (V1B) channels, two jacks each (a 68 kΩ stopper per jack,
the 1 MΩ leak at jack 1's tip) → **V1**
ECC83 (100 kΩ plates, shared 820 Ω cathode with 250 µF bypass) → 0.02 µF
couplers → 1 MΩ volume pots (the 100 pF bright cap sits on the volume V1B
feeds) → 270 kΩ mixers, the bright one bridged by a 56 pF capacitor → **V3A** ECC83 (100 kΩ plate,
820 Ω cathode) → **V3B cathode follower, DC-coupled** (100 kΩ cathode load) →
TMB tone stack (56 kΩ slope; 270 pF treble, 0.02 µF bass and 0.02 µF middle caps; 250 kΩ / 1 MΩ /
25 kΩ pots) → 0.02 µF → **long-tailed-pair PI**: 82 kΩ and 100 kΩ plates,
470 Ω + 10 kΩ tail, both 1 MΩ grid leaks returned to the tail junction →
0.1 µF couplers straight onto the grids (the drawing has no grid stoppers) →
**KT66 pair**, fixed-biased through 220 kΩ leaks, their screens fed through
**one shared 1 kΩ · 2 W** and then **a 470 Ω · 1 W per screen** → output
transformer,
27 kΩ negative feedback into the tail foot with the 5 kΩ presence control
and its 0.1 µF wiper-to-ground capacitor.

Power: 360-0-360 HT → GZ34 (0.05 µF from its cathode to the return) → standby
→ **+450 V** reservoir → **20 H choke** → **+440 V** node carrying the output
transformer's centre tap (plates, chart 430 V), the screen feed, a 32 µF filter
and the 8.2 kΩ → **+380 V** PI → 10 kΩ → **+310 V** preamp. Fixed bias, as
drawn: the HT winding end that also feeds a GZ34 anode → a series resistor →
a diode → an "8" filter → 16 kΩ → the grid-line node, which carries a shunt to
the return, an unvalued electrolytic and both 220 kΩ leaks.

The one part of the drawing not carried over here is the tremolo: on the
factory sheet an extra ECC83 (its "V2") drives a 2G374 transistor that shunts
the V3A mixer/grid signal through a 0.1 µF capacitor, 10 kΩ, the 50 kΩ depth
control and 33 kΩ. This is signal-amplitude modulation, with no connection to
the output-valve bias line. The plain head omits the entire tremolo branch,
which is why the valve numbering skips from V1 to V3.

## Lineage

The JTM45 is drawn from the 5F6-A, and the two schematics line up stage for
stage. The differences are exactly the ones that give the JTM45 its voice: an
ECC83 rather than a 12AY7 at the input (more front-end gain), KT66 output
valves, a shared 1 kΩ screen feed added ahead of the 470 Ω each screen
keeps, and a stiffer, higher HT rail.

## The tone network, as the drawing wires it

The Marshall drawing wires the stack exactly as the Fender 5F6-A sheet it
copies: the 270 pF treble capacitor and the 56 kΩ slope resistor both leave the
cathode-follower output; one 0.02 µF runs from the slope foot to the node
shared by the treble pot's lower lug and the bass pot; the bass pot is a
rheostat — the drawing loops its wiper to the foot lug — in series down to the
middle pot's top lug; the 0.02 µF mid capacitor feeds the middle pot's
**wiper**; and the stack's output is the treble pot's wiper alone, into the
0.02 µF phase-inverter coupler. The textbook redrawing of these parts joins the
treble and bass wipers at one output node and hangs the mid capacitor on a
rheostat-wired middle pot instead; the schematic, the board diagram and the
tone-stack lab all follow the drawing.

## Verification — against the printed factory chart

Simulation matches all 12 quantitative chart nodes within their tolerances.
The phase-inverter cathode is about 42 V against the printed 40 V. An earlier
redrawing grounded the 10 kΩ tail and incorrectly treated the chart value as
disputed; the factory drawing ends that resistor at the presence/feedback
junction, whose 5 kΩ track and 27 kΩ feedback resistor both return to ground.
The largest deviation is 6.5% at the V3A plate, within the chart's ±20%
tube-pin tolerance. The tail junction carries no numerical chart value:
the drawing marks the inverter grids only “+”, so it is reported informationally.

The drawing letters the input valve's sections, and that fixes which channel is
which: V1A's plate feeds the plain volume and V1B's plate feeds the volume
carrying the 100 pF, so V1B is the bright channel. V1A's printed load reads
"1■0K", its middle digit a solid blob that cannot be told from a 0 or an 8 on
this drawing. The corpus keeps 100 kΩ because the chart prints both input
plates at 220 V on one shared cathode, which a 180 kΩ / 100 kΩ pair could not
give; that rules 180 kΩ out, it does not read the digit.

The screen feed is drawn as one 1 kΩ · 2 W from the node after the choke to a
junction, then a 1 W resistor to each screen. The upper one reads "470"; the
lower one's first digit is not legible, and 470 is kept because 670 and 870 are
not standard values, which is elimination rather than a reading.

## What the drawing does not settle: the bias

The bias network's values are only partly legible. The series resistor prints
as "1■0K" with a middle digit that could be 5, 6 or 8, and the grid-line shunt as
"5■K" with its second digit overprinted by a wire. The electrolytic on the grid
line carries no value, and the "8" and "16K" are probable readings. No type is
printed at the diode; the drawing's "1N4007" note is about replacing the GZ34.
The only voltage printed on the network is a bubble reading "10 5V" on the
grid-line node, and it cannot be the quiescent bias. The cans there are drawn
minus-up, so the node is negative. Read as −105 V, it is far beyond the KT66's
cutoff of about −46 V at the chart's 440 V screens: the valves would pass no
plate current, and the plates could not read 10 V below the centre-tap node, as
the chart prints them. Read as −10.5 V, the output pair would draw several
hundred milliamps and drag the 440 V rail to about 380 V. The chart's own cell
for the KT66 grids is an illegible handwritten note.

So the DC model holds the grid line at an ideal −50 V. Nothing on the drawing
supplies that figure; it is the corpus's earlier assumption, kept so the model
has a bias at all. The gated rails depend on it through the plate current the
choke carries. The 0.05 µF that the earlier model treated as a bias filter is
on the rectifier side of the standby switch, from the GZ34 cathode to the
return, and the 25 µF it listed is not printed anywhere.
