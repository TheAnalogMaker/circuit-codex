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
junction so the stage self-biases — simulation puts the cathode pin at 44.2 V and
the junction at 43.0 V, a clean −1.3 V grid-to-cathode. The plate (56 kΩ from the
+250 V rail) sits at 202.5 V, balancing the two drive signals to the output pair.

## Verification — against the printed factory chart

The F-EF drawing prints a full voltage chart, and simulation matches it across
the board: the +302 V and +250 V rails land within 2 %, and every compared tube
pin is within 8.4 % (the chart's own convention is ±20 %). The driver cathode is
the one node left informational — it is unbypassed and loaded at DC by the 56 kΩ
feedback resistor returning from the speaker, and the anchor-fit 12AX7 model runs
a little light there, so simulation reads about 1.2 V against the printed 1.5 V.
The 6AT6 uses a purpose-built, public-domain model fitted to its RCA datasheet
(triode section only); the two diode units play no part in the amplifier and are
left unmodeled.
