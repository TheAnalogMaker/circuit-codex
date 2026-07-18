# 5F6-A — Tweed Bassman-style

The most influential guitar amplifier circuit ever drawn: four inputs, a
12AY7 front end, a direct-coupled cathode follower driving the
treble-mid-bass tone stack, a long-tailed-pair phase inverter, and a
fixed-bias 5881 pair — the template Marshall copied for the JTM45 and half
the industry copied after that. Produced 1958–1960. Lineage edges to 5F6
(ancestor) and JTM45 (descendant) land when those circuits do.

## Circuit walkthrough (short form)

Bright + normal channels (1M leaks, 68k stoppers) → **V1** 12AY7 (100k
plates, shared 820Ω cathode with 250 µF bypass) → 0.02 µF couplers → 1M
volume pots (100 pF bright cap) → 270k mixers → **V2A** 12AX7 (100k plate,
820Ω cathode) → **V2B cathode follower, DC-coupled** (100k cathode load) →
TMB tone stack (56k slope, 250 pF treble, 0.02 µF caps; 250k/1M/25k pots) →
0.02 µF → **long-tailed-pair PI**: 82k (5%) and 100k (5%) plates, 470Ω + 10k
tail, both 1M grid leaks returned to the tail junction, 47 pF balance cap →
0.1 µF couplers → **5881 pair**, fixed-biased at −48 V through 220k leaks,
**470Ω 1W screen resistors** → 2Ω output (four 8Ω speakers), 27k NFB into
the tail foot with the 5k presence control.

Power: 325-0-325 (PT 8087) → GZ34 → standby → **+432 V** plates (20 µF) →
choke (14684) → **+430 V** screens → 4700Ω → **+385 V** PI (20 µF) → 10k →
**+325 V** preamp (8 µF). Bias supply: selenium rectifier, 15k/56k, two
8 µF/150 V → **−48 V**.

## Verified 2026-07-18 — against the printed factory chart

The I-EG drawing prints a full voltage chart, and the simulation matches all
14 compared nodes: rails within 0.8 %, every tube pin within 9.9 %
(chart convention ±20 %). Two source corrections came out of the read-off:

- A widely-cited secondary source claims a **6.8k stock PI tail** — the
  drawing prints **10k** (with 470Ω bias), and the chart's +32.5 V junction
  value confirms it (32.5 V ÷ 10k ≈ the 3.2 mA tail current the plate drops
  imply).
- The chart also settles the NFB/presence wiring at DC: the tail's 10k
  returns effectively straight to ground; the 27k feedback and presence pot
  hang at the foot at ~0 V DC.
