# 5F4 — Tweed Super-style

The tweed Super shares the Bassman's front half — a 12AY7 two-channel front
end, a 12AX7 gain stage feeding a direct-coupled cathode follower, and a
fixed-bias pair of 6L6-family output tubes — but its back half is its own
circuit: a split treble/bass tone network unlike the Bassman ladder, and a
driver + split-load (cathodyne) phase inverter rather than a long-tailed pair.
Produced across the late-tweed years (1957–1960), it shares the 5F6-A's power
iron almost part-for-part (PT 8087, choke 14684, a 5881/6L6G pair biased near
−40 V) while running a slightly lower rail set. Its direct ancestor is the
5E-series Super not yet published in this archive.

## Circuit walkthrough (short form)

Two channels (each: 1M grid leak, 68k stopper) → **V1** 12AY7 (100k plates,
shared 820 Ω cathode with 25 µF bypass) → 0.02 µF couplers → 1M volume pots →
270k mixers → **V2A** 12AX7 (100k plate, 1.5k/25 µF cathode) → **V2B cathode
follower, DC-coupled** (100k cathode load) → the split tone network (below) →
straight into the grid of **V3A**, a cathode-biased 12AX7 driver stage (100k
plate, 1.5k cathode) → 0.02 µF → **V3B split-load cathodyne**: 56k plate, 1.5k
+ 56k under the cathode, 1M grid leak returned to the 1.5k/56k junction → 0.1
µF couplers from the cathodyne's **plate and cathode** → **6L6G pair**,
fixed-biased at −40 V through 220k leaks (1.5k grid stoppers), screens tied
straight to the +410 V node → Fender 45216 output transformer into the two
10-inch speakers. A 56k negative-feedback resistor returns from the speaker to
V3A's cathode, where the 5k presence pot bleeds it to ground through 0.1 µF.

Power: 5U4G rectifier → **+415 V** reservoir (output plates) → choke (14684) →
**+410 V** screens → 10k → **+332 V** phase-inverter supply → 10k → **+280 V**
preamp. A selenium rectifier with a 6.8k/56k network supplies the **−40 V**
bias.

The output tubes are lettered **6L6G** on the C-EG sheet; Fender equipped the
tweed Super with 5881s, the ruggedized 6L6 the Bassman and Twin also used, and
the two are interchangeable. Simulation here uses the 6L6-family 5881 model.

## The tone network the sheet draws

The 5F4's two knobs are not a two-knob cut of the Bassman stack — the C-EG
sheet draws a different network, in which treble and bass ride two separate
branches off the cathode follower and recombine at the phase inverter's grid:

- **Treble**: the follower's cathode feeds a 250 pF capacitor into one end of
  the 1M treble pot; the pot's other end reaches ground through 0.01 µF, and
  the **wiper** is the output.
- **Bass**: the cathode also feeds a 0.1 µF coupler into a node carrying a
  220k leak to ground (the amp's 4.7M feedback resistor returns here too),
  then 100k in series into the 1M bass pot's **wiper** — the branch injects at
  the wiper, not at an end lug. One end lug reaches ground through 0.005 µF,
  the other is grounded outright. From the wiper node, 220k carries the branch
  to the output.
- The recombined output node **is** the driver's grid: no coupling capacitor
  and no grid-leak resistor follow the network — its own 220k-and-track path
  to ground sets the grid's DC.

There is no slope resistor and no shared cap ladder, so the two controls
interact far less than the Bassman family's do — and the treble and bass
curves cross over with no scoop carved between them.

## The phase inverter the sheet draws

The C-EG drawing prints no long-tailed pair. **V3A** is a plain cathode-biased
gain stage — 100k plate at the printed +213 V over a 1.5k cathode at +1.7 V —
and **V3B** is a split-load cathodyne: 56k in the plate (printed +270 V), 1.5k
+ 56k under the cathode (printed +55 V and +53.3 V), with the 1M grid leak
returned to the 1.5k/56k junction so the stage biases itself. The two 0.1 µF
output couplers leave from the cathodyne's plate and cathode — one inverted
output, one not, which is the whole job. The 56k feedback resistor and the 5k
presence pot land on V3A's cathode: cathode-injected feedback, with the
presence control varying how much of it the 0.1 µF bleeds to ground.

## Verification — and what the chart gets wrong

The rails, the 12AY7 front end, all five phase-inverter values, and the 6L6
fixed-bias supply verify against the printed chart (worst gated node 16.0 %,
against the chart's own ±20 % convention). The five phase-inverter figures —
+213/+1.7 on the driver, +270/+55/+53.3 on the cathodyne — are mutually
consistent once the stage is read as the driver + cathodyne the sheet draws;
an earlier revision of this page modelled a long-tailed pair here and had to
dispute three of them as contradictory, which they never were. Three printed
values remain excluded as disputed, with the arithmetic shown in the voltage
table: the chart's V2A pair (140 V plate with a 2.2 V cathode) is physically
impossible for a 12AX7 — that cathode voltage implies a current the tube can
only pass near 280 V — and the cathode follower inherits the same printed
value through its direct coupling. Measured period data and simulation agree
the real operating point sits near 190 V. The full analysis is in the
archive's 12AX7 calibration study.
