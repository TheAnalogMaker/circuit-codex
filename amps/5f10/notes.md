# 5F10 — Tweed Harvard-style

The tweed line's fixed-bias oddball: a roughly 10-watt student amp built around a
6AT6, a 12AX7, a fixed-biased 6V6GT pair and a 5Y3GT rectifier. Where almost
every other tweed Fender cathode-biases its output tubes, the Harvard runs a
proper negative-bias supply — the same idea as the bigger Bassman and the later
brownface amps, shrunk into a one-knob-tone practice combo. It also opens with a
**6AT6**, a twin-diode/high-mu triode borrowed from the radio-and-television
parts bin (only the triode section is used), rather than the usual 12AY7/12AX7
front end. Produced through the late tweed years.

## Circuit walkthrough (short form)

Three inputs (each a 68 kΩ stopper, grid grounded through the switched jacks) →
**6AT6** first stage (100 kΩ plate load, 1.5 kΩ cathode with a 25 µF bypass) →
0.02 µF coupler → **1 MΩ volume** (with a 500 pF bright cap) and a **1 MΩ tone**
control (0.005 µF) → **12AX7 driver** (100 kΩ plate, 1.5 kΩ *unbypassed* cathode)
→ 0.02 µF → **12AX7 cathodyne phase inverter** (56 kΩ plate load, 1.5 kΩ + 56 kΩ
cathode stack, 1 MΩ grid leak returned to the junction) → 0.1 µF couplers →
**6V6GT pair**, fixed-biased at −21 V through 220 kΩ grid leaks with 1.5 kΩ
stoppers → output transformer → speaker. A **56 kΩ negative-feedback** resistor
runs from the speaker back to the driver's cathode.

Power: HT winding → **5Y3GT** → **+305 V** plates (16 µF) → 470 Ω → **+302 V**
screens → 22 kΩ → **+250 V** preamp (16 µF). The bias supply is a selenium
rectifier off an HT tap, filtered by 6.8 kΩ / 56 kΩ and two 25 µF cans, giving
the **−21 V** grid line.

## Fixed bias in a tweed

Two details set the Harvard apart from its cathode-biased tweed siblings. First,
the 6V6 grids are held at a fixed −21 V from the selenium bias supply rather than
lifted by a shared cathode resistor, so the output tubes idle warm and give up a
little of the tweed "sag and bloom" for a firmer, louder response. Second, the
phase inverter is a **cathodyne**: the 12AX7's cathode runs through 1.5 kΩ to a
junction and then 56 kΩ to ground, with the 1 MΩ grid leak returned to that
junction so the stage self-biases — simulation puts the cathode pin at 47.4 V and
the junction at 46.1 V, a clean −1.3 V grid-to-cathode. The plate (56 kΩ from the
+250 V rail) sits at 197 V, balancing the two drive signals to the output pair.

## Verification — against the printed factory chart

The F-EF drawing prints a full voltage chart, and every node on it is gated
against simulation. The +302 V and +250 V rails land within 3 %, and every tube
pin is within the chart's own ±20 % convention. The worst of them is the driver
cathode at 15.7 %: it is unbypassed and loaded at DC by the 56 kΩ feedback
resistor returning from the speaker, and the anchor-fit 12AX7 model runs a
little light there, so simulation reads 1.3 V against the printed 1.5 V. Every
other pin lands within 7.8 %. Nothing is disputed and nothing is excluded.
The 6AT6 uses a purpose-built, public-domain model fitted to its RCA datasheet
(triode section only); the two diode units play no part in the amplifier and are
left unmodeled.

## The heater layer: what the sheet shows, and a question it answered

The board drawing here used to close its heater chain with a link across the
6AT6's two heater pins. Nothing on the F-EF sheet joins them, and the 6AT6 has
two heater pins and no centre tap, so those two pins *are* the supply's two legs
and a link between them is a short across it. The link is gone; a drawn pair
already spans both of a socket's heater pins, so the chain's last hop never
needed one.

What the layout sheet shows, read at its native 6378 × 4525 with the 12AX7's
socket circle fitted to its drawn rim and the pin bearings measured: one green
transformer lead meets the yellow-red HT centre tap at a solder point and goes
to a ground hatch, and the other green runs to the pilot light's single
terminal and on to the first 6V6GT at pin 7; each 6V6GT takes pin 2 to a
ground hatch, with the unused pin 1 bowed to it as the tie point; the 6AT6's
heater pin 4 carries a short lead to a ground symbol and pin 3 takes the feed;
and at the 12AX7 a short bow outside the socket rim ties pins 4 and 5 together
while pin 9 carries a lead up to a ground hatch — the 6.3 V parallel grouping,
ends strapped as one leg with the centre tap the other. A single-ended supply,
every socket returning to chassis on its own, and the board declares it as
such and is drawn as single green leads.

Two things about the 12AX7 were open until the socket was measured rather than
looked at. A stroke that seemed to join pins 8 and 9 at 9× is the socket rim:
with the circle fitted (coverage 1.00), the ink between those pins has the
same inner and outer edge as every other arc of the same rim, and nothing lies
outside it. And a straight line leaves the pins-4/5 tie and runs right past the
cathode at pin 3 — either landing on that terminal or grazing it on its way to
the 6AT6. The scan cannot separate a landing from a crossing there, and the
circuit's own argument (a heater leg tied to a cathode with the other leg
grounded would short the supply) can reject a reading but not establish one.
It does not need to: which pins the supply's two legs sit on is settled by the
bow and the grounded centre tap, and that is all the heater declaration
states. The collision stays recorded here as what it is.
