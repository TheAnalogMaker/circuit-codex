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

## Verification

The C-EG drawing prints a full factory voltage chart, and the simulation matches
the backbone of it: the four B+ rails land within about 4 %, the 12AY7 front end
within about 5 %, and the 6L6 fixed-bias line exactly. Two things keep the rest
of the chart from closing, and together they hold this page at **draft** rather
than verified.

The first is the second gain stage and its cathode follower. Both run their
plates near +140 V — well under the +250 V point where the corpus's v0 12AX7
model is fitted — and below that anchor the model under-reads plate current, so
those two nodes settle high in simulation (the follower simply tracks its
direct-coupled driver). The sibling 5F6-A runs the same stage nearer +180 V and
reproduces cleanly, which is exactly the pattern you would expect from a model
that is sharp around its anchor and soft away from it.

The second is the phase inverter, whose printed figures do not fully reconcile
with each other. The chart shows +270 V and +213 V on the two plates but only
+53 V at the tail junction above the 56k tail resistor; the plate voltages imply
a couple of milliamps of total current, while the +53 V junction implies about
one. No single operating point satisfies all of those readings at once, so the
self-consistent simulation lands above the printed plate values. This kind of
tension is common in hand-measured factory charts.

Neither gap points at a wrong component value — the rails, the 12AY7 stage, and
the whole power section all reproduce from the same extracted parts list. The
low-voltage 12AX7 nodes are what a curve-traced 12AX7 model (the roadmap's v1)
should finally settle.
