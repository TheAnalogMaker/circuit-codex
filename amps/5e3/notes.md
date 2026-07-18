# 5E3 — Tweed Deluxe-style

The most-built amp circuit in DIY history: two channels into a 12AY7, a 12AX7
second stage feeding the famous interactive volume/tone network, a cathodyne
phase inverter, and a cathode-biased 6V6GT push-pull pair with no negative
feedback — the recipe for tweed compression and breakup. Produced 1955–1960.
Direct ancestor: 5D3 (lineage edge lands when `amps/5d3` exists).

## Circuit walkthrough (short form)

Two channels (each: 1M grid leak, 68k stoppers) → **V1** 12AY7 (100k plates,
shared 820Ω bypassed cathode) → 0.1 µF couplers → interactive 1M volume pots
(+ single tone control: 500 pF/0.005 µF network) → **V2A** 12AX7 (100k plate,
1.5k bypassed cathode) → tone-cap coupling → **V2B cathodyne phase inverter**
→ 0.1 µF couplers → **V3/V4** 6V6GT pair (220k grid leaks, 1.5k stoppers,
shared 250Ω 5W bypassed cathode) → 8k:8Ω output transformer.

Power: 325-0-325 PT → 5Y3GT → three 16 µF/450 V nodes separated by **5,000 Ω**
and **22k** droppers: B+1 (output plates) → B+2 (screens) → B+3 (preamp).

## The cathodyne detail the secondary sources garble

The published F-EE drawing settles the phase-inverter wiring that conflicting
descriptions obscure: V2B's cathode runs through **1.5k** to a junction, then
**56k** to ground; the **1M grid leak returns to that junction** (not to
ground), and the tone network's capacitors AC-couple the grid. The stage
self-biases: simulation puts the cathode at 42.4 V, junction at 41.3 V —
a clean −1.1 V bias, with the plate (56k from B+3) at 195 V.

## Verified 2026-07-18

The F-EE drawing carries **no factory voltage chart** (only the ±20 % notice),
so verification uses Rob Robinette's published DC measurements as the
reference: all seven charted nodes simulate within 12 % (rails 5–8 %, stage
plates 4–12 %, 6V6 cathode 7.8 %). Component values are 100 % drawing-read.
