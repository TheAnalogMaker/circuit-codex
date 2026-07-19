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
TMB tone stack (56 kΩ slope; 270 pF, 0.02 µF and 0.01 µF caps; 250 kΩ / 1 MΩ /
25 kΩ pots) → 0.02 µF → **long-tailed-pair PI**: 82 kΩ and 100 kΩ plates,
470 Ω + 10 kΩ tail, both 1 MΩ grid leaks returned to the tail junction →
0.1 µF couplers → **KT66 pair**, fixed-biased through 220 kΩ leaks, with
33 kΩ grid stoppers and **1 kΩ · 2 W screen stoppers** → output transformer,
27 kΩ negative feedback into the tail foot with the 5 kΩ presence control.

Power: 360-0-360 HT → GZ34 → standby → **+450 V** reservoir feeding the output
plates (chart 430 V) → **20 H choke** → **+440 V** screens → 8.2 kΩ → **+380 V**
PI → 10 kΩ → **+310 V** preamp. Fixed bias: an HT-tap diode, 150 kΩ, and a
0.05 µF / 25 µF filter give the **−50 V** grid line.

The one part of the drawing not carried over here is the tremolo: on the
factory sheet an extra ECC83 (its "V2") and a transistor form a bias-wobble
oscillator that modulates the output valves. The plain head omits it, which is
why the valve numbering skips from V1 to V3.

## Lineage

The JTM45 is drawn from the 5F6-A, and the two schematics line up stage for
stage. The differences are exactly the ones that give the JTM45 its voice: an
ECC83 rather than a 12AY7 at the input (more front-end gain), KT66 output
valves, 1 kΩ screen stoppers in place of Fender's 470 Ω, and a stiffer, higher
HT rail.

## Verification — against the printed factory chart

Simulation matches 11 of the chart's quantitative nodes — rails within 5.1 %,
triode pins within 9.5 % worst case (the shared input cathode; the chart's own
convention is ±20 %) — worst deviation 9.5 %. A twelfth value, the
phase-inverter cathode (KPI), is excluded as disputed: the printed 40 V
contradicts the chart's own 250 V plate figures (40 V across the 10 kΩ tail
implies a current that would pull those plates far lower), and simulation —
which reproduces the printed plates exactly — settles the cathode near 31 V,
the same value the identical stage measures in the 5F6-A this circuit copies.
The tail junction (JPI) carries no printed chart value at all — the drawing
marks the PI grids only "+" — so it is reported informationally, not compared.
