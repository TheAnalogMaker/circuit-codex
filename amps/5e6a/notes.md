# 5E6-A — Tweed Bassman-style

The mature narrow-panel revision of the 4x10 tweed Bassman's dual-rectifier
era — the last stop before the 5F6 brought in the three-knob tone stack and
the long-tailed-pair phase inverter that made the line famous. Where the 5F6
and 5F6-A each carry a single mercury-vapour or GZ34 rectifier feeding the
amp through a choke, the 5E6-A still runs the older scheme its 5D6 ancestor
established: two 5U4GA rectifier tubes in parallel and no choke at all,
plates and screens landing straight on the first filter node.

## Circuit walkthrough (short form)

Two channels (each: 1 MΩ grid leak, no stopper) → **V1** 12AY7 (100 kΩ
plates, shared 820 Ω cathode with 250 µF bypass) → 0.02 µF couplers → 1 MΩ
volume pots → 270 kΩ mixers → **V2** 12AY7, a single-section extra gain
stage (100 kΩ plate, 1.5 kΩ/25 µF cathode) → Presence(5k)/Bass/Treble network
→ **V3** 12AX7, a single-section self-biased split-load (cathodyne) phase
inverter: 56 kΩ plate, cathode split 1.5 kΩ (between the cathode pin and the
grid-leak's return junction) + 56 kΩ (junction to ground) — the same shape as
the 5F4's V3B — → 0.1 µF couplers + 1.5 kΩ stoppers →
**6L6G pair**, fixed-biased through 220 kΩ leaks, screens tied straight to
the supply with no series resistor → output transformer into four 10-inch
speakers.

Power: two **5U4GA** rectifiers in parallel (no choke) → **+420 V** (plates,
screens, OT centre tap — the drawing also reads +410/+405 V at nearby points
on this same undropped node) → 10 kΩ → **+335 V** (V3 supply) → 10 kΩ →
**+275 V** (V1/V2 supply). A selenium-rectifier bias supply (3,300 Ω, 100 µF,
56 kΩ bleeder) delivers roughly −42 V to the 6L6G grid leaks.

## What makes this circuit distinct from its neighbors

- **No choke.** Every other verified amp in this family (5F6, 5F6-A, 5F4)
  filters through the 14684 choke between the first reservoir cap and the
  screens. The 5E6-A drawing shows none: the plates, screens and OT centre
  tap all read within a few volts of each other at the same node, consistent
  with three separate 16 µF/450 V cans sitting at slightly different physical
  points on one low-impedance rail rather than three RC-filtered stages.
- **Two rectifier tubes, not one.** The 5E6-A keeps the "dual rectifier"
  scheme the family history (`history/families/bassman.yaml`) describes for
  the 5D6 lineage: two 5U4GA tubes wired in parallel off separate secondary
  taps, both cathodes landing on the same first-filter node — extra current
  capacity for the 4x10 cab's fixed-bias 6L6G pair. `history/families/bassman.yaml`
  previously carried this circuit's tube list without a rectifier at all and
  with the wrong preamp-tube count (`12AY7, 12AX7, 12AX7`); both are corrected
  here from the drawing (see that file's own history).
- **Cathodyne, not long-tailed-pair.** The corpus's own existing citation
  chain already had this right (`history/families/bassman.yaml`'s 5F6 entry:
  "swapped the cathodyne splitter for a long-tailed-pair phase inverter") —
  the 5E6-A's V3 is a single 12AX7 section, self-biased with a split cathode
  resistor exactly the way the 5F4's V3B is (1.5 kΩ junction + 56 kΩ tail),
  just without the extra driver stage the 5F4 puts in front of it.
- **No cathode follower.** That innovation is the 5F6's, not this circuit's:
  the signal runs V1 → V2 → tone network → V3 directly, with V2 doing the
  gain-recovery work a cathode follower would later take over.

## The 5E6 → 5E6-A revision

The 5E6 and 5E6-A drawings share the same drawing code (A-EE) and are
otherwise identical circuits. The one substantive difference is a handwritten
note on the 5E6 sheet beside the bias-supply series resistor: "THIS CHANGE TO
INCREASE BIAS ON PLATES SO WON'T GET HOT", with the original resistor value
struck through and "3300" written in. The 5E6-A drawing prints 3,300 Ω
cleanly with no annotation — the fix formalized. A smaller series resistor in
this bias-supply topology (selenium rectifier → series R → filter cap →
bleeder) delivers a larger-magnitude (more negative) bias voltage, which
lowers 6L6G quiescent plate current and dissipation — exactly the fix the
note describes. This is the one circuit-level change the "-A" suffix marks.

## What this pass verified, and what it didn't

The title block, tube complement (confirming the dual-5U4GA rectifier and the
2×12AY7/1×12AX7 preamp split), the rail chain, and V1's front end all read
consistently off the drawing, cross-check against the higher-resolution
Schematic Heaven scan of the same A-EE drawing, and gate against the printed
chart within the usual tolerance (worst node 29.8%, against the chart's own
±20% convention and the extra slack a choke-less, dual-rectifier supply
earns — see `voltages.yaml`). Three things are explicitly **not** resolved
this pass and are flagged rather than guessed at:

- **V2's own pin voltages** — the printed figures around V2 sit in a dense
  cluster on the scan that this pass could not confidently separate from the
  neighboring tone-network figures. `voltages.yaml` reports them as
  simulated-only (`chart: null`).
- **V3's plate/cathode/junction pin voltages** — a printed figure cluster
  near +210/+72/+1.7 V exists close to the 12AX7 on the sheet, and a first
  attempt at this netlist assigned +72 V to the cathode pin and +1.7 V to the
  grid-leak junction (mirroring how those two numbers read on the page).
  Simulating that assignment drove the tube to near cutoff — a 12AX7 cannot
  hold ~1.25 mA against the roughly −70 V grid-to-cathode bias that pairing
  implies, so at least one of those two figures was assigned to the wrong
  node (or belongs to a different pin altogether, e.g. V2's). The netlist now
  uses the 5F4's V3B values verbatim (56k plate, 1.5k/56k cathode split, same
  shape), which is known to simulate sensibly, and `voltages.yaml` leaves
  PPI/KPI/JPI informational rather than re-guess which number goes where.
  This is exactly the kind of error `verify_amps.py` exists to catch, and
  it's why the two-pass structure (a value re-read against a working DC
  model) matters more here than the raw OCR confidence would suggest.
- **The Presence/Bass/Treble ladder's exact wiring** — mostly resolved
  2026-08-08 (see below), with one residual lug-level uncertainty flagged
  in `schematic.kicad_sch`'s own annotation. Because the network is entirely
  DC-open, none of this has any bearing on the netlist's operating point —
  it only means the tone-stack lab does not yet have a topology to plot for
  this amp (it isn't one of `site/src/lib/corpus.js`'s plottable shapes).

All three are draft-status gaps, not disputes: nothing here contradicts the
drawing. The bias-supply figure's printed **sign** is also
not clearly legible on the archived scan (magnitude ~42 V is clear); it is
read as negative for consistency with every other fixed-bias amp in this
corpus and because the circuit only functions as drawn (a fixed-bias output
pair) with a negative supply.

## Drawings pass, 2026-08-08 — schematic, and two corrections

`schematic.kicad_sch` landed this session, drawn from a fresh lug-level read
of the high-resolution Schematic Heaven A-EE scan (cross-checked against the
El34World copy — see `meta.yaml` sources). That read resolved the
Presence/Bass/Treble ladder
well enough to draw (bleeder + bass shelf + a shared presence/NFB bus fed by
a 20 kΩ resistor off the speaker node, the family's usual feedback take-off;
treble wired as a rheostat, the same trick the family's 3-knob ladders use
for the bass pot) and **corrected two mis-readings** from the original data-
core pass:

- The **"10 MΩ channel-linking resistor... in series with a small mica
  cap"** bom.yaml entry was actually two unrelated parts, now `RFB` (a light
  V2 plate-to-grid feedback/self-bias resistor, drawn as a loop above V2 on
  the sheet — its left end lands on the post-mixer V2 grid node, not on the
  input jacks) and `CJ1` (a channel-jumper cap bridging the two channels'
  post-coupler nodes directly). Two 100 kΩ padding resistors (`RP1`/`RP2`,
  each channel's coupler → volume-pot hot lug) had not been catalogued at
  all.
- The bass-shelf mica cap bom.yaml read as **"500 pF (printed .0005)"**;
  this pass reads the same printed figure as **".005"**, i.e. 0.005 µF
  (`CBS`) — a 10× correction. The sheet is dense at that exact spot and a
  third read would be worth having before this entry leaves draft.

**Residual uncertainty, honestly flagged rather than guessed past:** which
of the bass pot's two end lugs is the "hot" one riding the shared
presence/NFB bus vs. the "cold" one feeding the fixed shelf network is drawn
as read but the two lugs sit close together on the scan — see the comment
in `schematic.kicad_sch` right above that block. A dedicated lug-by-lug
re-check, the kind `amps/5f6`/`amps/5f6a` got on 2026-08-03, would firm this
up before this entry leaves draft.

## No board drawing yet, and why

This circuit ships without the board diagram its siblings carry. A drawing
was built from the same A-EE layout page, and its *electrical* content
checks out: the layout-to-netlist equivalence gate proved the drawn
point-to-point wiring equivalent to the simulated netlist within the
documented DC scope, with every tube anchored and the two 5U4GA rectifiers
left outside the DC model by the same convention every other rectifier in
this archive follows.

What it does not pass is the collision lint — the gate that rejects
wiring-layer ambiguity, where two runs sit close enough to read as one wire
or an endpoint close enough to another run to read as a joint that isn't
there. Substantial rework took this board from 140 findings to 64 across
both drawing styles, concentrated in a handful of long B+ rail returns and
the points where several pot lugs converge. 64 is not close.

Wiring that is electrically right is not the same as a drawing that is
legible, and a diagram a reader can misread is worse than no diagram. This
archive does not publish a drawing a blocking gate rejects, and it does not
waive the gate to make one publishable. The board drawing lands when the
lint does.

## Lineage

The family history (`history/families/bassman.yaml`) already stated the
5F6/5F6-A's phase inverter change is a revision of "the cathodyne splitter"
that came before it — this circuit is that predecessor, landing with
`lineage.influenced: ["5f6"]`. The reciprocal edge (`5f6`'s
`lineage.derived_from: ["5e6a"]`) is added in the same change. The 5E6-A's
own ancestor, the plain 5E6 (and behind it the 5D6), is not yet a documented
circuit in this corpus, so `derived_from` is left empty here.
