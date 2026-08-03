# 5F6 — Tweed Bassman-style

The circuit that made the tweed Bassman famous, and the one revision short of
the amp everybody copied. Introduced in July 1957, the 5F6 brought in the
three-knob treble/middle/bass tone stack, the direct-coupled cathode follower
that drives it, the long-tailed-pair phase inverter and the fixed-bias 5881
pair — the whole architecture of the 5F6-A, arriving a year early behind a
mercury-vapour rectifier. Produced 1957–1958.

## Circuit walkthrough (short form)

Bright + normal channels (1M leaks, 68k stoppers) → **V1** 12AY7 (100k plates,
shared 820 Ω cathode with 250 µF bypass) → 0.02 µF couplers → 1M volume pots
(100 pF bright cap) → 270k mixers → **V2A** 12AX7 (100k plate, 820 Ω cathode
with 25 µF bypass) → **V2B cathode follower, DC-coupled** (100k cathode load) →
TMB tone stack (56k slope, 250 pF treble, two 0.02 µF caps; 250k/1M/25k pots)
→ 0.02 µF → **long-tailed-pair PI**: 82k (5%) and 100k (5%) plates, 470 Ω + 10k
tail, both 1M grid leaks returned to the tail junction, 47 pF across the plates
→ 0.1 µF couplers → **5881 pair**, fixed-biased at −48 V through 220k leaks and
1.5 kΩ grid stoppers, **100 Ω screen resistors** → output transformer into four
speakers, with 27k of negative feedback returning into the tone stack's ground
leg.

Power: 325-0-325 (PT 8087) → **83** → standby → **+432 V** plates (two 20 µF)
→ choke (14684) → **+430 V** screens → 4.7 kΩ → **+385 V** PI (20 µF) → 10k →
**+325 V** preamp (8 µF). Bias supply: selenium rectifier, 15k/56k, two
8 µF/150 V → **−48 V**.

## The 83, and what a mercury-vapour rectifier does to a supply

The 83 is the only mercury-vapour tube in the corpus, and it behaves nothing
like the vacuum rectifiers around it. A 5Y3 or a 5U4 is a space-charge device:
its forward drop climbs steeply with current, so the B+ falls away on loud
notes — the sag that tweed amps are loved for. The 83 instead strikes an arc in
mercury vapour, and once struck the drop is pinned near 15 V and stays there
from idle to the tube's full 225 mA. Its datasheet says as much in one line: the
tube supplies d-c current at essentially constant voltage in spite of rather
wide variations in output current.

The practical result is a stiff supply. It is also a demanding one, and the
datasheets say so in their ratings rather than in prose. The tube is specified
for vertical, base-down mounting. Its condensed mercury has to sit between
20 °C and 60 °C. And the supply must present at least 50 Ω per plate — more
if the first filter capacitor exceeds 40 µF — to keep the peak charging current
inside the 1 A per-plate limit. The chassis carries a standby switch ahead of
the first filter capacitor, which lets the filament come up before the high
voltage does. Every one of those conditions goes away with the 5F6-A's
indirectly-heated GZ34.

## What changed on the way to the 5F6-A

Both drawings print the same rails (+432/+430/+385/+325), the same −48 V bias,
the same transformer set (8087 power, 14684 choke, 45249 output) and the same
preamp values, so the differences are narrow and specific:

- **Rectifier.** The 83 gives way to the GZ34.
- **Presence.** On the 5F6 the 5 kΩ presence control sits in the tone stack's
  ground leg, below the middle pot, with the 27k feedback resistor landing on
  that same junction and a 0.1 µF cap from the presence wiper to ground; the
  phase-inverter tail's 10k returns straight to ground. The 5F6-A moves the
  presence pot and the feedback return down to the tail foot instead.
- **Output stage.** The 5F6's 1.5 kΩ grid stoppers and 100 Ω screen resistors
  become no stoppers and 470 Ω 1 W screen resistors.

## Verification — against the printed factory chart

The F-EG drawing prints a full voltage chart, and simulation matches all
fourteen gated nodes: rails within 0.8 %, every tube pin within 9.6 % against
the chart's own ±20 % convention. Two printed values are excluded, and the
reason is arithmetic rather than judgement. The chart gives both phase-inverter
grids (+22 V and +23 V) alongside the tail junction they return to (+32.5 V) —
but each grid reaches that junction through a 1 MΩ leak and nothing else, so
with no grid current both must sit at the junction's own potential. The printed
figures are 68 % and 71 % of it, the fraction a 1 MΩ source reads into a meter
of roughly 2 MΩ input resistance. They are the signature of a moving-coil
voltmeter loading the node, not of a circuit that behaves that way.

The one place the drawing invites a second look is the phase-inverter tail. It
is 10k with a 470 Ω bias resistor, and the chart's own +32.5 V junction figure
confirms it: 32.5 V across 10k is 3.25 mA, and the printed plate drops
(385→235 V through 82k, 385→230 V through 100k) imply about 3.4 mA through the
pair — the same current, inside the chart's own precision.
