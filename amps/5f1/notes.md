# 5F1 — Tweed Champ-style

The smallest amp in the tweed canon and the clearest illustration of a complete
guitar amplifier: one 12AX7 providing two gain stages, a cathode-biased 6V6GT
single-ended output, a 5Y3GT rectifier, and nothing else — no tone control, no
phase inverter, five watts of pure signal path. Produced 1958–1964; direct
ancestor: the mid-1950s [5E1](/amps/5e1/).

## Circuit walkthrough (short form)

Input jack → 68k grid stopper → **V1A** (12AX7, 100k plate load, 1.5k bypassed
cathode) → 0.02 µF coupling → 1M audio volume pot → **V1B** (12AX7, 100k plate,
1.5k cathode) → 0.02 µF coupling → **V2** 6V6GT (cathode-biased, 470 Ω 5 W,
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
| B+2 | 295 V | 291 V (1.3%) | 291.5 V (1.2%) |
| B+3 | 250 V | 273 V (**9.2% off**) | 252 V (0.8%) |

With 22k, the downstream stage voltages fall into line as well.
**Conclusion:** the second dropper is 22k — a value some descriptions of
this circuit get wrong — and the schematic's printed 22K marking confirms
it.

## A correction: the heater wiring this entry drew, and what the sheet shows

The board drawing on this page shipped its 6.3 V heater wiring wrong, and the
correction is recorded here rather than quietly made.

The 12AX7 has a centre-tapped heater, which lets one valve run from either
supply: at **12.6 V** the two heater ends sit on opposite legs and the centre
tap carries none, while at **6.3 V** the two ends are strapped together as one
leg and the centre tap is the other. Both arrangements use the same three pins,
so the pin names alone cannot say which an amplifier wires — and the drawing
was built by a rule that read the pin names and always chose the series form.
On this circuit that produced a lead to each heater end and then a link joining
them, which reads as a short across the supply, with the centre tap left
unwired.

The factory drawing shows the parallel arrangement, and shows the supply it
belongs to. The schematic draws the 6.3 V secondary with one lead grounded at
the transformer and the other marked *to all 6.3 volt filaments and pilot lite*
— a single-ended supply, one wire out and the chassis back. The layout wires
exactly that: one green transformer lead to the chassis-ground point beside the
high-tension centre tap, the other to the pilot lamp and on to the 6V6GT's
heater, then to the 12AX7; the 12AX7's two heater ends strapped together and its
centre tap taken to ground; the 6V6GT's other heater pin taken to ground on its
own. The 5Y3GT keeps its separate 5 V filament winding, which floats at the
rectified B+ and is grounded nowhere.

What the drawing now states, it states as data: this circuit's supply voltage,
the connection group each socket pin belongs to and which leg returns to ground
are declared in the layout and checked — against the valve's own datasheet
grouping, and against the leads the drawing draws.

## Verification

Simulation is checked against the drawing's full printed voltage chart: the
6V6 cathode within 0.2 % (18.0 V vs +18 V), rails within 1.2 %, and the 12AX7
pins (+150 V plate, +1.5 V cathode) within the chart's own printed ±20 %
convention — Fender measured on 1958 production tubes, while these models are
datasheet-typical, so the preamp simulating slightly leaner than the era
measurement is expected behavior. Planned refinements: output-transformer
primary resistance in the DC deck, and full curve-traced tube models.
