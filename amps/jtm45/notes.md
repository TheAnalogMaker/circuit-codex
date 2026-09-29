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

Bright + normal channels (1 MΩ leaks, 68 kΩ stoppers) → **V1** ECC83 (100 kΩ
plates, shared 820 Ω cathode with 250 µF bypass) → 0.02 µF couplers → 1 MΩ
volume pots (100 pF bright cap) → 270 kΩ mixers → **V3A** ECC83 (100 kΩ plate,
820 Ω cathode) → **V3B cathode follower, DC-coupled** (100 kΩ cathode load) →
TMB tone stack (56 kΩ slope; 270 pF treble, 0.01 µF bass and 0.02 µF middle caps; 250 kΩ / 1 MΩ /
25 kΩ pots) → 0.02 µF → **long-tailed-pair PI**: 82 kΩ and 100 kΩ plates,
470 Ω + 10 kΩ tail, both 1 MΩ grid leaks returned to the tail junction →
0.1 µF couplers → **KT66 pair**, fixed-biased through 220 kΩ leaks, with
33 kΩ grid stoppers and **1 kΩ · 2 W screen stoppers** → output transformer,
27 kΩ negative feedback into the tail foot with the 5 kΩ presence control
and its 0.1 µF wiper-to-ground capacitor.

Power: 360-0-360 HT → GZ34 → standby → **+450 V** reservoir feeding the output
plates (chart 430 V) → **20 H choke** → **+440 V** screens → 8.2 kΩ → **+380 V**
PI → 10 kΩ → **+310 V** preamp. Fixed bias: an HT-tap diode, 150 kΩ, and a
0.05 µF / 25 µF filter give the **−50 V** grid line.

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
valves, 1 kΩ screen stoppers in place of Fender's 470 Ω, and a stiffer, higher
HT rail.

## The tone network, as the drawing wires it

The Marshall drawing wires the stack exactly as the Fender 5F6-A sheet it
copies: the 270 pF treble capacitor and the 56 kΩ slope resistor both leave the
cathode-follower output; one 0.01 µF runs from the slope foot to the node
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
The phase-inverter cathode is about 43 V against the printed 40 V. An earlier
redrawing grounded the 10 kΩ tail and incorrectly treated the chart value as
disputed; the factory drawing ends that resistor at the presence/feedback
junction, whose 5 kΩ track and 27 kΩ feedback resistor both return to ground.
The largest deviation is 9.7% at the shared input cathode, within the chart's
±20% tube-pin tolerance. The tail junction carries no numerical chart value:
the drawing marks the inverter grids only “+”, so it is reported informationally.
