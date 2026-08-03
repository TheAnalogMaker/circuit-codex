# Model 1959 — Super Lead 100-style

The Marshall model 1959 is the 100-watt Super Lead: the amplifier most people
mean when they say "Plexi". It began as a special order — 100-watt heads built
for players who wanted more than the 45-watt amplifier could give them on
stage — and became Marshall's catalogue number 1959, produced from 1965 until
1981.

The signal path is the one the whole lead line shares — the 50-watt model 1987
carries the same one two years later. Four inputs feed two deliberately
unmatched channels into one ECC83; a second ECC83 provides a gain
stage and a direct-coupled cathode follower ahead of the treble-middle-bass tone
stack; a third drives a long-tailed-pair phase inverter. What changes at 100
watts is behind the inverter: **four** EL34 pentodes in parallel push-pull, two
per phase, over a solid-state bridge rectifier and a filter bank of paired
100 µF capacitors. There is no rectifier valve to sag, and there is a great deal
of power supply behind the output valves, which is much of why the 1959 stays
tight and loud where smaller amplifiers compress.

"Plexi" names the circuit and its voicing, not the panel: Marshall switched from
the gold acrylic (Perspex) front panel to a brushed-metal panel around 1969, so
the factory drawing cited here (Unicord, July 1970) is metal-panel era.

## Circuit walkthrough (short form)

Two channels, each with high and low inputs (68 kΩ stoppers, 1 MΩ leaks) →
**V1** ECC83, one triode per channel (100 kΩ plates). The channels are voiced
apart at the cathode: the high-treble channel runs 820 Ω fully bypassed by
250 µF, the normal channel a colder 2.7 kΩ with a 0.68 µF partial bypass, and
their coupling caps differ too (0.022 µF and 0.0022 µF). Each plate feeds its
own 1 MΩ volume with a bright cap (0.005 µF and 500 pF), and the two channels
mix through 470 kΩ resistors into **V2A** (100 kΩ plate, 820 Ω / 0.68 µF
cathode) → **V2B cathode follower, DC-coupled** (100 kΩ load) → tone stack
(33 kΩ slope; 500 pF treble into 250 kΩ, 0.022 µF bass into 1 MΩ, 0.022 µF
middle into 25 kΩ) → **long-tailed-pair phase inverter** (**V3**: 82 kΩ plate on
the driven side and 100 kΩ on the other, 470 Ω over a 10 kΩ tail, both 1 MΩ grid
leaks returned to the tail junction, 47 pF across the plates).

From there the two phases split: each 0.022 µF coupler feeds a pair of EL34s
through 5.6 kΩ grid stoppers, with one 120 kΩ grid leak per pair carrying the
adjustable negative bias. Every screen grid has its own 1 kΩ stopper. The
output transformer offers 16, 8 and 4 Ω taps, and negative feedback returns from
the 16 Ω tap through a 47 kΩ resistor to the cold end of the inverter's tail,
where a 5 kΩ presence control shunts the top of the feedback band to ground.

Power: a universal-primary mains transformer (110/120/200/225/245 V taps), a
silicon bridge and a reservoir of 100 µF capacitors in series pairs with 56 kΩ
sharing resistors. That rail feeds the output valves' plates and screens
directly; a 20 kΩ / 1 W dropper takes it down to the phase inverter and two
further 10 kΩ / 1 W droppers step it down again for the second stage and the
input valve, each node filtered by a pair of 50 µF capacitors. The negative grid
bias comes from its own diode, a 15 kΩ / 27 kΩ / 47 kΩ network with 8 µF filters
and a 27 kΩ trimmer.

## Lineage

The 1959 descends from the JTM45, and through it from the tweed 5F6-A Bassman
the JTM45 copied. The path runs through the 100-watt heads Marshall built in
1965 for players who wanted more clean headroom than 45 watts gave: the output
section was doubled, and the KT66 beam tetrodes gave way to EL34 pentodes as
KT66 costs rose. The valve rectifier went with them. The front end barely
moved — four inputs, two channels, a DC-coupled cathode follower and a
long-tailed-pair inverter all carry straight across from the JTM45.

The 50-watt model 1987 is this amplifier's sibling rather than its parent: the
same front end and the same voicing with half the output valves.

## A note on verification

Marshall drawings of this period print component values only, and the 1959
drawing carries no valve-voltage chart. A factory chart does exist for the
100-watt head, issued with the sheet of the same drawing number and date that
covers the 6550-fitted Mark II — a component-for-component identical front end
ahead of a different output quartet. Its ECC83 figures are used here for the
preamp and phase inverter, and the circuit reproduces them closely: every
preamp plate lands within 5% of its printed figure and the inverter's two plates
within 3%. The cathode figures — single-digit-volt readings taken with a
hand-held meter — land within 17%.

Two things keep the circuit a **draft**. The inverter's cathode simulates about
8 volts above the printed figure, because the model idles that pair harder than
the chart's amplifier did and the supply it hangs on runs high for the same
reason. And the EL34 output stage has no published figures of its own at all:
its plate and screen voltages here are derived from a rail taken as an
assumption, and the idle current is a choice within the range these amplifiers
are set to rather than a reading. Verified is earned against measurements, and
the measurements that exist do not cover this output stage.
