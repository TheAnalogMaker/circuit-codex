# 6G2 — Brown Princeton-style

The Princeton line's hard break. For fifteen years the Princeton had been, in
Fender's own framing, a Champ with a tone control — a single-ended 6V6 student
amp tracking the Champ's own revisions through the tweed 5F2-A. The brownface
6G2 (1961–63) abandons that architecture entirely: a fixed-bias **push-pull**
pair of 6V6GTs, a cathodyne phase inverter to drive them, and a tremolo — a
fundamentally different, more powerful power stage, not a revision of the
single-ended one. `amps/5f2a/notes.md` warns readers not to read its own values
onto anything from the 6G2 forward, and this page is why: no `lineage.derived_from`
edge is drawn to the 5F2-A. The line the 6G2 *does* start runs forward to the
blackface **AA964** Princeton, which keeps this circuit's fixed-bias 6V6 pair,
its cathodyne, and its bias-vary tremolo almost unchanged.

The drawing labels the first bottle **7025**, the low-noise selected version of
the 12AX7; the second small bottle is a plain 12AX7.

## Signal path

**Input.** Two jacks share a 68 kΩ stopper each into a common 1 MΩ grid leak,
into V1A — 100 kΩ plate load, 1.5 kΩ cathode with its own 25 µF bypass.

**Tone and Volume.** A single 0.02 µF coupler carries V1A's plate into the
Tone/Volume network: a 1 MΩ-A Tone control (capacitor-coupled cut, single-knob
style, the same architecture the tweed 5F2-A used) and a 1 MΩ-A Volume pot.
This network is not in the DC netlist — the wiper draws no grid current, so
its own resistance never sets an operating point, exactly as the corpus treats
every other volume/tone network. A second 0.02 µF coupler carries the wiper
into V1B, an identical second stage: 100 kΩ plate load, its own 1.5 kΩ/25 µF
cathode.

**Cathodyne phase inverter.** V1B's plate couples through 0.02 µF into the
grid of a **cathodyne** — a single 12AX7 triode with matched output impedances,
sharing its bottle with the tremolo oscillator. 56 kΩ plate load off the
preamp/PI rail; a small cathode resistor into a tail junction, 56 kΩ from that
junction to ground; the 1 MΩ grid leak returns to the **tail junction, not
ground** — so the grid floats at the tail's own quiescent voltage rather than
0 V, since no grid current flows to drop anything across the leak. This is the
identical wiring the sibling **5F10 Harvard** and the descendant **AA964**
Princeton both use for their own cathodynes (56 kΩ plate, small cathode
resistor into a 56 kΩ tail, 1 MΩ leak to the junction) — a recipe this corpus
now has three independent factory drawings for. The plate output couples
0.1 µF into one 6V6's grid; the tail-junction output couples 0.1 µF into the
other's, exactly mirroring how the 5F10's own netlist takes its second
coupler from the junction rather than the bare cathode pin.

**Output.** Two 6V6GTs, grounded cathodes, 1500 Ω grid stoppers. Both grids
wire straight into the **Intensity** pot's wiper rather than through a
dedicated grid-leak resistor — see "The tremolo modulates the bias" below.
No negative-feedback resistor appears on the published drawing, unlike the
5F10 that precedes it and the AA964 that follows: this Princeton runs
open-loop.

## The tremolo modulates the bias — without a leak resistor in the way

The other half of the cathodyne's bottle is a phase-shift oscillator: 56 kΩ
plate load taken straight off the driven reservoir (not the derived preamp
rail, so it keeps running cleanly regardless of preamp loading), a Speed
control (3 MΩ reverse-audio) setting the RC ladder's rate, and its output
leaving through 220 kΩ and 0.1 µF into a 250 kΩ-linear **Intensity** control.

Where the 6G3/AB763 generation fixes a 220 kΩ · 5 % grid-leak resistor at each
output tube and modulates the bias *supply* upstream of it, the 6G2 wires the
Intensity pot's wiper **directly** to both 6V6 grid-stopper junctions — no
separate leak resistor at all. The pot's own two ends are the -35 V fixed-bias
supply on one side and the oscillator's AC-only output (capacitor-coupled, so
DC-blocked) on the other. Because the output grids draw no DC grid current,
nothing can flow through the pot regardless of its resistance or wiper
position, so the grids sit at exactly -35 V no matter where Intensity is set —
what varies is how much of the oscillator's AC swing rides on top of that
fixed point. It is the same trick the later amps use, wired one stage earlier
and with one fewer resistor.

## Power

A 125P1A power transformer feeds a 5Y3GT full-wave rectifier, delivering
**+315 V** at the reservoir — the same node the output transformer's centre
tap and the oscillator's own plate load sit on. From there: 1000 Ω · 1 W to
**+312 V** at the 6V6 screens, then 10 kΩ · 1 W to **+280 V** at the preamp
and cathodyne rail. A separate 100 kΩ · 5 % feed, a rectifier, a 25 µF · 50 V
can and a 30 kΩ · 5 % bleeder make the **-35 V** fixed bias.

## Reading against the printed chart

The drawing prints a comprehensive per-pin voltage chart, values ±20 %, read
to ground with an electronic voltmeter — the same convention as every other
verified circuit in this corpus, and considerably more complete than the
5F2-A's undocumented single-ended predecessor or the AC15's five scattered
annotations. `pipeline/verify_amps.py` reproduces every gated node within 4 %
of the printed chart (worst nodes: the cathodyne's cathode pin and tail
junction, 3.9 %; every other node inside 2 %) — tighter than several of this
corpus's own *verified* entries.

One component value on this sheet is settled by the chart rather than by the
ink, and it is worth stating which: the cathodyne's cathode resistor, in the
faintest corner of the scan, reads plausibly as 700 Ω. Simulated against the
netlist, 700 Ω does not reproduce the printed
+56.5 V (cathode) / +55 V (tail junction) pair — it lands both nodes over
20 % high. 1.5 kΩ — a value this same sheet uses repeatedly elsewhere, as
every 6V6 grid stopper — reproduces both within 4 %, and is a far more
plausible misread of a faint "1500" than an unrelated "700" would be. The
tail-to-ground resistor (56 kΩ) is read in agreement with the identical
cathodyne recipe the 5F10 and AA964 factory drawings independently carry, and
that value is further confirmed by the same chart match. Everything else — the
rail chain, both preamp stages, the cathodyne's plate load, the output stage,
and the bias supply — carries no such ambiguity.

The entry stays a **draft** pending the maintainer's review, which is the only
thing that grants `verified` here. The DC model itself is ready for it: every
gated node reproduces inside 4%.

## The oscillator, excluded

The tremolo oscillator (the cathodyne bottle's other half) is a running
phase-shift oscillator with no static operating point — a dynamic average, not
a DC bias, the same reasoning `amps/6g3` documents for its own oscillator. Its
plate load taps the driven reservoir node directly, so excluding it from the
netlist costs nothing downstream. Its own RC ladder's exact tap count is not
fully resolved from this scan; because the stage is excluded from the gated
model regardless, that residual uncertainty has no bearing on any gated node.

## Lineage

No ancestor lands in this corpus: the 5F2-A is the Princeton this circuit
replaces, but it is explicitly not a derivation of it (see above). Forward,
the AA964 blackface Princeton keeps this circuit's fixed-bias 6V6 pair and its
cathodyne almost unchanged, refining only the rectifier (5Y3GT → GZ34) and the
exact cathode-network values — which is also why the 6G2's own faint-scan
cathode resistors could be cross-checked against a drawing one generation
newer.
