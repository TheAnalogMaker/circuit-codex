# Model 2204 — Master Volume lead 50-style

The 2204 is the 50-watt lead head after Marshall stopped treating volume as
something the player set on the guitar. Two changes do it. The second channel's
volume control is repurposed as a **master volume** between the preamp and the
output stage, so the front end can be driven hard at any listening level. And the
two input triodes that used to sit side by side as separate channels are wired
**in series** — V1a into a volume control into V1b — so the preamp has three gain
stages ahead of the tone stack instead of two.

That cascaded front end is the circuit's whole character. Later it was
repackaged, in 1981, with a new cabinet and a new panel and sold as the JCM800.

## Circuit walkthrough (short form)

One channel with two inputs. The High jack (J1) runs through a 68 kΩ stopper
(R3) with a 1 MΩ leak (R2) into **V1a** ECC83 (100 kΩ plate, 2.7 kΩ cathode
bypassed by 0.68 µF, and a 100 pF cap straight across the triode). V1a's plate
couples out through 0.022 µF (C3) into the preamp-volume network — a 470 kΩ series arm (R5) bridged
by a 470 pF bright cap (C4) into the 1 MΩ log **Preamp Volume** (VR1), which
carries its own 1 nF cap (C5) across the upper section — and the wiper drives
**V1b**, the cascaded second stage: 100 kΩ plate, and a cold, deliberately
**unbypassed 10 kΩ** cathode. The Low jack (J2) lands on that volume network's
own input node rather than on V1a's grid: the drawing wires V1a's coupler to the
Low jack's normalling contact, so with nothing plugged into Low the two are
joined and the cascaded front end runs normally, and a plug in Low feeds the
preamp volume directly — a low-sensitivity input that starts at the second
stage.

V1b's plate goes through 0.022 µF (C7) into a 470 kΩ / 470 kΩ divider (R10/R11,
with 470 pF across the series arm) — the gain has to be thrown away again before
the next stage — into **V2a** (100 kΩ plate, unbypassed 820 Ω cathode) →
**V2b cathode follower, DC-coupled** (100 kΩ load) → treble-middle-bass tone
stack (33 kΩ slope; 470 pF, 0.022 µF and 0.022 µF; 220 kΩ / 1 MΩ / 22 kΩ) →
**Master Volume** (VR2, 1 MΩ log) → 0.022 µF → **long-tailed-pair phase
inverter** (**V3**: 82 kΩ on the driven plate and 100 kΩ on the other, 470 Ω
shared cathode, both 1 MΩ grid leaks to the tail junction, 10 kΩ tail) →
0.022 µF couplers with 47 pF across the grids → **EL34 pair**, fixed-biased
through 220 kΩ grid leaks with 5.6 kΩ grid stoppers and 1.5 kΩ screen resistors
→ output transformer with 16/8/4 Ω taps. Negative feedback returns from the
secondary through 100 kΩ to the foot of the tail, where a 4.7 kΩ resistor to
ground and a 22 kΩ presence pot behind a 0.1 µF cap set how much of it comes back
at the top end.

Power: a mains transformer with 240/220/120 V primary taps, a four-diode silicon
bridge into a 50+50 µF reservoir, an HT fuse and a filter choke. The output
transformer's centre tap is taken **ahead** of the choke, so only the screens and
the preamp are fed through it; 10 kΩ / 1 W droppers then step the rail down for
the phase inverter and second stage, and again for the input stage. The negative
grid bias comes from its own diode, a 220 kΩ series resistor, a 56 kΩ / 22 kΩ
adjustable divider and 10 µF filters.

## Lineage

The 2204 is the 1987 rewired. Everything from the third gain stage onward — the
DC-coupled cathode follower, the tone stack, the long-tailed-pair inverter, the
EL34 pair, the presence and feedback network — carries straight across from the
50-watt Plexi, and through it from the JTM45 and the tweed 5F6-A Bassman before
that. What changed is in front of it: where the 1987 runs two input triodes as
two channels and mixes them through 470 kΩ resistors, the 2204 runs them in
series with a volume control between, and puts a second volume control after the
tone stack. The output stage also picks up screen resistors and grid stoppers
that the 1987 does not have.

## The tone network, as the drawing wires it

The 2204 STD sheet wires the stack as the Marshall drawings before it did: the
470 pF treble cap and the 33 kΩ slope resistor both leave the cathode-follower
output; one 0.022 µF runs from the slope foot to the node shared by the treble
pot's lower lug and the bass pot; the bass pot is a rheostat, its wiper strapped
back to its top; the other 0.022 µF feeds the middle pot's **wiper**; and the
stack's output is the treble pot's wiper alone, taken to the master volume through
the panel link the drawing labels 'R14'.

## A note on verification

Both sheets of the 2204 STD factory drawing print component values only; neither
carries a valve-voltage chart. The DC operating points shown for this circuit are
simulated from the redrawn netlist rather than compared against a published chart,
and the output-stage operating point in particular is an estimate: the corpus's
CC0 EL34 model is fitted to a single 250 V datasheet anchor, and this circuit runs
its plates near 470 V. Two artefacts of that extrapolation are visible in the
figures — a colder-than-real modelling bias is needed to land a physical idle
current, and the model's screen current falls to zero at that bias, so the drawn
1.5 kΩ screen resistors show no drop where a real amp would show a few volts. The
circuit is therefore published as a **draft**: its topology and part values are
read directly from the factory drawing, but its voltages are not confirmed against
a measured reference.

An earlier Marshall drawing of the same model number does print voltages — a
'50W MASTER MODEL / MODEL NO. 2204' sheet dated 11/11/76 — but it draws a
different circuit: the input triodes still sit in parallel as two channels, and
the output valves are a 6550 pair for the US market. That revision predates the
series-connected front end this entry documents, so its figures are cited as
history, not used as a chart.

## Which valves

Marshall's own 11/81 specification sheet for the 2204 lists the output pair as
"6550 for USA (EL34, KT77 elsewhere)". The EL34 complement documented here is the
non-US fitment, and it is the one the 2204 STD drawing itself labels at V4 and V5.
