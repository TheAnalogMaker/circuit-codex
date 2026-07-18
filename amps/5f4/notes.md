# 5F4 — Tweed Super-style

The tweed Super is the Bassman's guitar-voiced sibling: the same big-bottle
preamp architecture — a 12AY7 two-channel front end, a 12AX7 gain stage feeding
a direct-coupled cathode follower, a treble/bass tone stack, a long-tailed-pair
phase inverter, and a fixed-bias pair of 6L6-family output tubes — but built
around two 10-inch speakers instead of the Bassman's four tens. Produced across
the late-tweed years (1957–1960), it shares the 5F6-A's power section almost
part-for-part (PT 8087, choke 14684, a 5881/6L6G pair biased near −40 V) while
running a slightly lower rail set. Its direct ancestor is the 5E-series Super
not yet published in this archive.

## Circuit walkthrough (short form)

Two channels (each: 1M grid leak, 68k stopper) → **V1** 12AY7 (100k plates,
shared 820 Ω cathode with 25 µF bypass) → 0.02 µF couplers → 1M volume pots →
270k mixers → **V2A** 12AX7 (100k plate, 1.5k/25 µF cathode) → **V2B cathode
follower, DC-coupled** (100k cathode load) → treble/bass tone stack (100k slope,
250 pF treble cap, 1M treble and bass pots) → 0.02 µF → **long-tailed-pair PI**:
56k and 100k plates, 1.5k + 56k tail, both 1M grid leaks returned to the tail
junction → 0.1 µF couplers → **6L6G pair**, fixed-biased at −40 V through 220k
leaks, screens tied straight to the +410 V node → Fender 45216 output
transformer into the two 10-inch speakers, with a 56k negative-feedback loop and
a 5k presence control.

Power: 5U4G rectifier → **+415 V** reservoir (output plates) → choke (14684) →
**+410 V** screens → 10k → **+332 V** phase-inverter supply → 10k → **+280 V**
preamp. A selenium rectifier with a 6.8k/56k network supplies the **−40 V**
bias.

The output tubes are lettered **6L6G** on the C-EG sheet; Fender equipped the
tweed Super with 5881s, the ruggedized 6L6 the Bassman and Twin also used, and
the two are interchangeable. Simulation here uses the 6L6-family 5881 model.

## The elevated phase-inverter tail

The long-tailed pair biases itself well up off ground. The two cathodes sit near
**+55 V**, joined through a 1.5k resistor to a junction at **+53.3 V**, which
then reaches ground through 56k. Both grid-leak resistors (1M each) return to
that +53.3 V junction rather than to ground, so each grid rides up close to its
own cathode and the tubes see only a volt or two of bias — the classic Fender
trick that lets a single 12AX7 swing both output tubes symmetrically. The 56k
feedback resistor and the 5k presence pot join the tail circuit but sit at
roughly 0 V DC through the speaker winding, so they do not move the operating
point.

## Verification — and what the chart gets wrong

The rails, the 12AY7 front end, the phase inverter's 56 kΩ-side plate, and the
6L6 fixed-bias supply all verify against the printed chart (worst node 11.4 %,
against the chart's own ±20 % convention). Six printed values are excluded as
disputed, with the arithmetic shown in the voltage table: the chart's V2A pair
(140 V plate with a 2.2 V cathode) is physically impossible for a 12AX7 — that
cathode voltage implies a current the tube can only pass near 280 V — and its
phase-inverter figures contradict each other. Measured period data and
simulation agree the real operating point sits near 190 V. The full analysis
is in the archive's 12AX7 calibration study.
