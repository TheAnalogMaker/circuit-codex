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
220k grid leak) → single-ended output transformer (~8k:8Ω class) → speaker.
Negative feedback: 22k from the speaker jack into V1B's cathode (at DC this
parallels the 1.5k through the secondary's near-zero DCR).

Power: 325-0-325 PT → 5Y3GT full-wave → filter nodes 26 µF / 8 µF / 8 µF (450 V,
as marked on the drawing) separated by a 10k and a 22k dropper:
B+1 340 V (output plate) → B+2 295 V (screen) → B+3 250 V (preamp plates).

## Operating point: chart vs. simulation (resolved 2026-07-18)

Chart node values read from the published Fender drawing (GM): **B+1 340 V
(26 µF/450 V cap), B+2 295 V (8 µF), B+3 250 V (8 µF)**. With B+1 driven at
340 V, simulation discriminates the dropping-resistor value cleanly:

| Node | Chart | Sim, R11=10k | Sim, R11=22k |
|---|---|---|---|
| B+2 | 295 V | 291 V (1.3%) | 292 V (0.9%) |
| B+3 | 250 V | 273 V (**9.2% off**) | 255 V (2.0%) |
| V1A plate | ~170 V | 183 V | **171.6 V (0.9%)** |
| V1B plate | ~170 V | 180 V | **169.1 V (0.5%)** |
| 6V6 cathode | 19 V (5E1 x-ref) | 18.0 V | 18.1 V (4.8%) |

**Conclusion:** the second dropper is 22k, not the 10k a secondary source
claimed — with it, every published figure (rails, the walkthrough's 170 V
plates, the ampbooks cathode cross-reference) reconciles simultaneously.
The netlist now carries R11 = 22k on that basis.

## Before `verified`

- [ ] Confirm the printed value of the resistor between the two 8 µF filter
      caps on the published drawing (expected marking: 22K).
- [ ] If the drawing's tube-pin voltage chart lists per-pin values, add them
      to voltages.yaml (plate/cathode pins for V1 and V2).
- [ ] Optionally add OT primary DCR to the deck (second-order effect).
