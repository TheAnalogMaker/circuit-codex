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
**470 Ω 1W screen resistors** → 2 Ω output (four 8 Ω speakers), with 27 kΩ of
negative feedback returning to the foot of the phase-inverter tail — the far
end of its 10k, which is not grounded — alongside the 5 kΩ presence pot's
track and the second grid's 0.1 µF.

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

## What the revision changed

Both drawings print the same rails (+432/+430/+385/+325), the same −48 V bias
and the same transformer set (8087 power, 14684 choke, 45249 output into a 2 Ω
secondary), so the differences from the [5F6](/amps/5f6/) are narrow and
specific:

- **Rectifier.** The 83 mercury-vapour tube gives way to the GZ34.
- **Presence.** The 5 kΩ presence pot and the 27 kΩ feedback return leave the
  tone stack's ground leg and land at the foot of the phase-inverter tail
  instead: the tail's 10k no longer returns to ground but to the node they
  share, and the pot's track runs from there to ground with 0.1 µF on its
  wiper. The middle pot's foot, which fed the presence pot on the 5F6, now
  runs straight to ground.
- **Output stage.** The 5F6's 1.5 kΩ grid stoppers and 100 Ω screen resistors
  become no stoppers and 470 Ω 1 W screen resistors.
- **Second-stage cathode.** The 5F6 bypasses V2A's 820 Ω cathode resistor with
  25 µF; here the same resistor runs unbypassed.

The two parts lists share their resistor and pot designators, so those read
side by side. The capacitor numbers do not: the 5F6 carries two capacitors this
revision drops — the 25 µF on V2A's cathode and the 47 pF across the
phase-inverter plates — so the C run diverges from C4 onward and the same
number names a different part on each page. Compare capacitors by role.

## The heater circuit, and a supply that grounds neither leg

This is the first amplifier in the archive whose 6.3 V winding is centre-tapped
and grounded *at the tap*. The tweeds either side of it run a single-ended
supply — one green lead grounded at the transformer, the other feeding
everything, each socket returning to chassis on its own. Here the green-yellow
lead goes to the chassis and the two greens float about it, half a supply either
side of ground. Nothing is grounded at a socket at all.

The sheet does not route the heater leads. Instead it names each socket's
landings with a short stub marked X, which is a stronger statement than the
"to all 6.3 volt heaters" arrow the blackface drawings use, because it says
*which pins* even though it does not say by what path. At all three nine-pin
bottles a bow outside the socket rim ties pins 4 and 5 together and carries one
X, with the second X at the centre tap on pin 9: the 6.3 V parallel arrangement,
in which the two heater ends are one leg and the centre tap is the other. At
both 5881 sockets the two X stubs sit on pins 2 and 7, that valve's only heater
pins.

The two greens run up to the pilot light, one to each of its terminals, and
from each terminal an X-marked arrow leaves for the heaters: the lamp sits
across the pair, and the chain is arrowed from both of its terminals, which is
how the board draws it.

Because neither leg is grounded, which of the two the drawing calls feed and
which return carries no claim — it is only a name, and the declaration says so.
The GZ34 keeps its own 5 V winding, which floats at the rectified B+ with the
cathode strapped to the heater inside the envelope at pin 8.

## Verification — against the printed factory chart

The I-EG drawing prints a full voltage chart. Simulation matches 11 of its 13
compared nodes (S51 carries no chart value and is informational only): rails
within 0.7 %, every gated tube pin within 9.8 % (the chart's own convention is
±20 %). The other two, the phase-inverter cathodes and the tail junction, are
shown as disputed, because the chart's tail figures fit a circuit the drawing
does not show:

- The phase-inverter tail is **10k** (with a 470 Ω bias resistor), as the
  drawing letters it — not the 6.8k sometimes quoted.
- The 10k does **not** return to ground. Both the schematic and the layout
  land its far end on a node of its own, which the 27 kΩ feedback resistor
  (back to the speaker, DC ground through the output transformer) and the
  presence pot's 5 kΩ track hold above ground; the V3B grid's 0.1 µF lands
  there too. Simulated, that foot sits at +12.6 V and the junction at +42.3 V.
- The printed +32.5 V junction and +34 V cathodes are what the printed plate
  currents, 3.38 mA in all, give through a 10k returned straight to ground —
  33.8 V — and they are, figure for figure, the chart the [5F6](/amps/5f6/)
  prints, whose 10k does return to ground. Through the drawn foot the same
  current would put the junction near 48 V. The page prints the chart's figures
  beside the simulation and marks them disputed, rather than bending the circuit
  to fit them.
