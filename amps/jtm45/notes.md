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

The drawing carries a full valve-voltage chart, and simulation matches it
closely. All four supply rails land within about 5 % of their printed values,
and every preamp and phase-inverter **plate** sits within a few percent: the
input plates at 220 V, the second-stage plate at 190 V, the cathode-follower
output at 190 V, and both phase-inverter plates at 250 V all reproduce almost
exactly.

One node does not agree, and it is worth being plain about. The chart prints
the phase-inverter **cathode** at 40 V, but simulation puts it near 31 V — a
22 % gap. The chart is internally inconsistent here: a 40 V cathode would
require about 3.8 mA flowing in the tail, and that much current through the
82 kΩ and 100 kΩ plate loads would pull the phase-inverter plates down to
roughly 190-225 V, not the 250 V the same chart prints alongside. Simulation
can satisfy the plates or the cathode but not both, and it favours the plates;
the identical long-tailed pair in the 5F6-A settles at the same ~31 V. Because
that charted cathode falls outside tolerance, the circuit is published as a
draft rather than verified, with the discrepancy noted rather than smoothed
over.
