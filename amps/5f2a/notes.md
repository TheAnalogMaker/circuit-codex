# 5F2-A — Tweed Princeton-style

The tweed Princeton is the 5F1 Champ grown up: the same one-12AX7, single-ended
6V6 signal path, but with a tone control added and negative feedback wrapped
around the driver stage. Five watts of the same sweet breakup, now with a treble
knob and a firmer, more focused voice than the Champ's. Produced 1957–1961; its
direct ancestor is the 5F2 not yet documented in this archive, and it is
the tone-control-bearing sibling of the tweed Champ already in this archive.

## Circuit walkthrough (short form)

Two input jacks (high/low, each a 68 kΩ stopper sharing a 1 MΩ leak) → **V1A**
(12AX7, 100 kΩ plate load, 1.5 kΩ bypassed cathode) → 0.02 µF coupling →
**tone/volume network** → **V1B** (12AX7, 100 kΩ plate, 1.5 kΩ *unbypassed*
cathode) → 0.02 µF coupling → **V2** 6V6GT (cathode-biased, 470 Ω 1 W, 220 kΩ
grid leak) → single-ended output transformer → speaker.

The tone/volume network is a single interactive treble-cut: two 1 MΩ linear
pots with a 0.005 µF shunt cap and a 500 pF series cap. It is entirely
capacitor-coupled, so at DC V1B's grid simply returns to ground through the
volume pot.

Negative feedback: 22 kΩ from the 8 Ω speaker output into V1B's cathode. Because
that cathode is left unbypassed, the feedback has something to push against.

Power: the 66079 transformer → 5Y3GT full-wave → first node **32 µF** (two 16 µF
caps in parallel) at B+1 (6V6 plate) → 10 kΩ 1 W dropper → **8 µF** B+2 (6V6
screen) → 22 kΩ dropper → **8 µF** B+3 (both preamp plates).

## The Champ with a backbone

Two small changes separate this circuit from the 5F1 and give the Princeton its
character. First, V1B's cathode bypass capacitor is gone: the 5F1 bypasses that
1.5 kΩ for maximum gain, while the 5F2-A leaves it open so a global feedback loop
can work against it. Second, that loop — 22 kΩ from the speaker back to the bare
cathode — trades a little raw gain for a tighter, less compressed response and a
touch more headroom. Add the treble-cut tone control and the result is an amp
that cleans up and articulates where the Champ simply flatters.

At DC none of this changes the operating points: bypass caps and the whole tone
network are invisible to a DC meter, so the 5F2-A idles exactly like a Champ.
The one visible fingerprint of the feedback loop is that V1B's cathode sits a
hair lower than V1A's — the 22 kΩ quietly parallels its 1.5 kΩ to ground.

## Verification

The published K-EG drawing supplies every component value but prints no voltage
chart — only Fender's standard ±20 % measurement notice. Because the 5F2-A's DC
signal path is identical to the tweed 6V6 single-ended Champ (the tone control is
capacitor-coupled and idles at nothing), simulation is checked against Rob
Robinette's published DC measurements for that circuit: B+ 360 / 325 / 250 V,
a ~19 V drop across the 6V6's 470 Ω cathode resistor, and 12AX7 plates near
170 V. Driving B+1 at 360 V, every compared node lands within about 8 %: the
6V6 cathode within about 2 % (19.4 V vs ~19 V, 2.1 %), the screen and preamp rails within
5–8 %, and both 12AX7 plates within 7 %.

The match is well inside Fender's ±20 % convention, but the reference is a sibling
model rather than the 5F2-A itself — a different power transformer could shift the
absolute B+ — so this circuit is published as a draft pending a voltage chart
measured on a 5F2-A.
