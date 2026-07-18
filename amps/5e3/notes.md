# 5E3 — Tweed Deluxe-style

The most-built amp circuit in DIY history: two channels into a 12AY7, a 12AX7
second stage feeding the famous interactive volume/tone network, a cathodyne
phase inverter, and a cathode-biased 6V6GT push-pull pair with no negative
feedback — the recipe for tweed compression and breakup. Produced 1955–1960.
Its direct ancestor, the 5D3, is not yet documented in this archive.

## Circuit walkthrough (short form)

Two channels (each: 1M grid leak, 68k stoppers) → **V1** 12AY7 (100k plates,
shared 820 Ω bypassed cathode) → 0.1 µF couplers → interactive 1M volume pots
(+ single tone control: 500 pF/0.005 µF network) → **V2A** 12AX7 (100k plate,
1.5k bypassed cathode) → tone-cap coupling → **V2B cathodyne phase inverter**
→ 0.1 µF couplers → **V3/V4** 6V6GT pair (220k grid leaks, 1.5k stoppers,
shared 250 Ω 5W bypassed cathode) → 8 kΩ : 8 Ω output transformer.

Power: 325-0-325 PT → 5Y3GT → three 16 µF/450 V nodes separated by **5,000 Ω**
and **22k** droppers: B+1 (output plates) → B+2 (screens) → B+3 (preamp).

## How the cathodyne biases itself

The 5E3's phase inverter uses a wiring detail that's easy to miss: V2B's
cathode runs through **1.5k** to a junction, then **56k** to ground, and the
**1M grid leak returns to that junction** rather than to ground — the tone
network's capacitors AC-couple the grid. The stage therefore biases itself:
simulation puts the cathode at 42.4 V and the junction at 41.3 V — a clean
−1.1 V bias — with the plate (56k from B+3) at 195 V.

## Verification

Every component value comes from the published Fender drawing. The F-EE sheet
carries no factory voltage chart (only Fender's ±20 % measurement notice), so
this circuit is verified against the best published DC measurements instead:
all seven reference nodes simulate within 12 % — rails within 8 %, stage
plates within 12 %, and the 6V6 cathode within 8 %.
