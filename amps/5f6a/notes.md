# 5F6-A — Tweed Bassman-style

The most influential guitar amplifier circuit ever drawn: four inputs, a
12AY7 front end, a direct-coupled cathode follower driving the
treble-mid-bass tone stack, a long-tailed-pair phase inverter, and a
fixed-bias 5881 pair — the template Marshall copied for the JTM45 and half
the industry copied after that. Produced 1958–1960, revising the 5F6 —
mainly by swapping its 83 mercury-vapour rectifier for a GZ34 and moving the
presence control out of the tone stack's ground leg to the phase-inverter
tail foot.

## Circuit walkthrough (short form)

Bright + normal channels (1M leaks, 68k stoppers) → **V1** 12AY7 (100k
plates, shared 820 Ω cathode with 250 µF bypass) → 0.02 µF couplers → 1M
volume pots (100 pF bright cap) → 270k mixers → **V2A** 12AX7 (100k plate,
820 Ω cathode) → **V2B cathode follower, DC-coupled** (100k cathode load) →
TMB tone stack (56k slope, 250 pF treble, 0.02 µF caps; 250k/1M/25k pots) →
0.02 µF → **long-tailed-pair PI**: 82k (5%) and 100k (5%) plates, 470 Ω + 10k
tail, both 1M grid leaks returned to the tail junction, 47 pF across the
plates →
0.1 µF couplers → **5881 pair**, fixed-biased at −48 V through 220k leaks,
**470 Ω 1W screen resistors** → 2Ω output (four 8Ω speakers), 27k NFB into
the tail foot with the 5k presence control.

Power: 325-0-325 (PT 8087) → GZ34 → standby → **+432 V** plates (20 µF) →
choke (14684) → **+430 V** screens → 4.7 kΩ → **+385 V** PI (20 µF) → 10k →
**+325 V** preamp (8 µF). Bias supply: selenium rectifier, 15k/56k, two
8 µF/150 V → **−48 V**.

## The tone network, as the drawings wire it

The published 5F6-A schematic and its factory layout sheet draw the same
ladder the 5F6 prints — not the textbook redrawing of these parts — and the
schematic and layout here follow the sheets (re-read at lug level 2026-08-03):

- The 250 pF treble capacitor and the 56 kΩ slope resistor both leave the
  cathode-follower output.
- One 0.02 µF capacitor runs from the slope resistor's foot to the node shared
  by the treble pot's **lower lug** and the bass pot — the treble pot's cold
  end sits on the far side of that capacitor, not on the slope foot.
- The bass pot is a **rheostat** in series down the ladder: the factory layout
  straps its wiper into the treble-lug node.
- The other 0.02 µF runs from the slope foot to the middle pot's **wiper**, so
  the Middle control slides the capacitor's injection point along a 25 kΩ leg
  that never leaves the circuit.
- The stack's output is the treble pot's **wiper alone**. Unlike the 5F6, the
  middle pot's foot runs straight to ground — the presence control moved to
  the phase-inverter tail.
- On the factory board the two 0.02 µF capacitors share their node-B eyelet
  with the slope resistor's lead, and the 250 pF mica sits beside them; the
  board-layout drawing here places all three as the sheet does.

The textbook form ties the treble pot's cold end to the slope foot, joins the
treble and bass wipers at one output node, and hangs the mid capacitor on a
rheostat-wired middle pot. The two networks share every part value and differ
audibly at the stops: as drawn, the fixed 25 kΩ leg keeps the stack from ever
going fully silent with Bass and Middle at zero, where the textbook network's
output falls to ground. The tone-stack lab plots this circuit with the wiring
its sheets draw.

## Verification — against the printed factory chart

The I-EG drawing prints a full voltage chart, and simulation matches all 13
compared nodes (S51 carries no chart value and is informational only): rails
within 0.8 %, every tube pin within 9.6 % (the chart's own convention is
±20 %). Working from the drawing also settles two details
that often circulate incorrectly:

- The phase-inverter tail is **10k** (with a 470 Ω bias resistor) — not the
  6.8k sometimes quoted. The chart's own +32.5 V junction figure confirms it:
  32.5 V across 10k matches the ~3.2 mA the plate drops imply.
- At DC the tail's 10k returns effectively straight to ground; the 27k
  feedback resistor and presence pot sit at the foot at roughly 0 V.
