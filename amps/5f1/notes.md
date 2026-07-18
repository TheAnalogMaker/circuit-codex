# 5F1 — Tweed Champ-style

The smallest amp in the tweed canon and the clearest illustration of a complete
guitar amplifier: one 12AX7 providing two gain stages, a cathode-biased 6V6GT
single-ended output, a 5Y3GT rectifier, and nothing else — no tone control, no
phase inverter, five watts of pure signal path. Produced 1958–1964; direct
ancestor: the 5E1 (lineage edge lands when `amps/5e1` exists).

## Circuit walkthrough (short form)

Input jack → 68k grid stopper → **V1A** (12AX7, 100k plate load, 1.5k bypassed
cathode) → 0.022 µF coupling → 1M audio volume pot → **V1B** (12AX7, 100k plate,
1.5k cathode) → 0.022 µF coupling → **V2** 6V6GT (cathode-biased, 470 Ω 5 W,
220k grid leak) → single-ended output transformer (≈5 kΩ : 8 Ω, typical for a single-ended 6V6;
the drawing doesn't mark it) → speaker.
Negative feedback: 22k from the speaker jack into V1B's cathode (at DC this
parallels the 1.5k through the secondary's near-zero DCR).

Power: 325-0-325 PT → 5Y3GT full-wave → filter nodes 16 µF / 8 µF / 8 µF (450 V)
separated by a 10k and a 22k dropper (all confirmed in print on the K-EE sheet):
B+1 340 V (output plate) → B+2 295 V (screen) → B+3 250 V (preamp plates).

## How simulation pinned down the rail dropper

The published chart marks **B+1 340 V, B+2 295 V, B+3 250 V**. Driving B+1
at 340 V, simulation discriminates the second dropping-resistor value
cleanly — a nice example of what simulation-verified archiving can do:

| Node | Chart | Sim with 10k | Sim with 22k |
|---|---|---|---|
| B+2 | 295 V | 291 V (1.3%) | 292 V (0.9%) |
| B+3 | 250 V | 273 V (**9.2% off**) | 255 V (2.0%) |

With 22k, the downstream stage voltages fall into line as well.
**Conclusion:** the second dropper is 22k — a value some descriptions of
this circuit get wrong — and the schematic's printed 22K marking confirms
it.

## Verification

Simulation is checked against the drawing's full printed voltage chart: the
6V6 cathode within 0.6 % (18.1 V vs +18 V), rails within 2 %, and the 12AX7
pins (+150 V plate, +1.5 V cathode) within the chart's own printed ±20 %
convention — Fender measured on 1958 production tubes, while these models are
datasheet-typical, so the preamp simulating slightly leaner than the era
measurement is expected behavior. Planned refinements: output-transformer
primary resistance in the DC deck, and full curve-traced tube models.
