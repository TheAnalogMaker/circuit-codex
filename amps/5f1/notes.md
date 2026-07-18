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

Power: 325-0-325 PT → 5Y3GT full-wave → three 16 µF filter nodes separated by
two 10k droppers: B+1 (output plate) → B+2 (screen) → B+3 (preamp plates).

## Simulated operating point (Circuit Codex models, B+1 held at 360 V)

| Node | Simulated | Published figure | Note |
|---|---|---|---|
| B+2 (screen) | 308 V | 325 V | −5%; OT primary DCR omitted in v0 deck |
| B+3 (preamp) | 289 V | "250 V" (walkthrough) | see open question below |
| V1A/V1B plates | 193 / 190 V | ~170 V | +12–14%; real-world 5F1 measurements also trend above the old chart |
| V1 cathodes | 1.4 V | −1.4/−1.5 V bias published | matches exactly |
| 6V6 cathode | 19.3 V | 19 V (ampbooks, 5E1) | 1.4% — strong cross-check |

## Open question (why this stays `draft`)

The secondary-source figure of **B+3 = 250 V is internally inconsistent** with a
10k dropper: two 12AX7 stages drawing ~1.4 mA total can only drop ~14 V across
R11, and the simulation agrees (289 V). Either the published chart's node values
were taken under different conditions, or a source transcription is off.
**To do before `verified`:** read the node voltages directly from the published
Fender 5F1 drawing (viewing a scan to read published values is fine — we simply
never reproduce the drawing) and correct `voltages.yaml` chart entries; add OT
primary DCR to the deck at the same time.
