# Model 1987 — Plexi lead 50-style

The Marshall model 1987 is the 50-watt lead head at the centre of the "Plexi"
sound. It is the JTM45 grown up: the same four-input, two-channel front end and
cathode-follower tone stack, but with a pair of EL34 pentodes in place of the
JTM45's KT66 beam tetrodes and a solid-state rectifier in place of the GZ34.
Those two changes — a higher, stiffer rail behind faster output valves — are much
of what turned the JTM45's bluesy roar into the brighter, harder-edged voice of
late-1960s British rock.

"Plexi" names the circuit and its voicing, not the panel: Marshall switched from
the gold acrylic (Perspex) front panel to a brushed-metal panel around 1969, so
the factory drawing cited here (Unicord, July 1970) is metal-panel era.

## Circuit walkthrough (short form)

Two channels, each with high and low inputs (68 kΩ stoppers, 1 MΩ leaks) →
**V1** ECC83, one triode per channel (100 kΩ plates). The two channels are
deliberately unmatched: the high-treble channel runs an 820 Ω cathode fully
bypassed by 320 µF, while the normal channel runs a colder 2.7 kΩ cathode with a
0.68 µF partial bypass. Each plate feeds its own 1 MΩ volume control (with a
bright cap) and the channels mix through 470 kΩ resistors into **V2A** (100 kΩ
plate, 820 Ω / 0.68 µF cathode) → **V2B cathode follower, DC-coupled** (100 kΩ
load) → treble-middle-bass tone stack (33 kΩ slope; 500 pF, 0.022 µF and
0.022 µF; 250 kΩ / 1 MΩ / 25 kΩ) → **long-tailed-pair phase inverter** (**V3**:
100 kΩ and 82 kΩ plates, 470 Ω + 10 kΩ tail, both 1 MΩ grid leaks to the tail
junction, 47 pF across) → 0.022 µF couplers → **EL34 pair**, fixed-biased through
220 kΩ grid leaks → output transformer with 16/8/4 Ω taps, negative feedback and
a presence control returned to the tail.

Power: a universal-primary mains transformer (110/120/200/225/245 V taps) and a
silicon full-wave rectifier feed a 50 µF + 80 µF reservoir; a filter choke and a
chain of 10 kΩ / 1 W droppers (with a 47 kΩ dropper to the phase-inverter/second-
stage supply) step the rail down for the screens, phase inverter and preamp. The
negative grid bias comes from a diode, a 220 kΩ / 15 kΩ / 25 kΩ network and 8 µF
filters.

## Lineage

The 1987 descends directly from the JTM45, and through it from the tweed 5F6-A
Bassman the JTM45 copied. The signal path is nearly the same stage for stage; the
differences are the ones that define the Plexi. The KT66 output pair becomes a
pair of EL34 pentodes — more transconductance and a sharper overdrive — and the
GZ34 valve rectifier becomes silicon diodes, which hold the rail up harder under
load. The input valve stays an ECC83, and the four-input two-channel layout, the
DC-coupled cathode follower and the long-tailed-pair inverter all carry straight
across.

## A note on verification

Marshall drawings of this period print component values only; the model 1987
factory drawing carries no valve-voltage chart. The DC operating points shown for
this circuit are simulated from the redrawn netlist rather than compared against a
published chart, and the output-stage operating point in particular is an estimate
only. The circuit is therefore published as a **draft**: its topology and part
values are read directly from the factory drawing and cross-checked against a
second published redraw, but its voltages are not yet confirmed against a measured
reference.
