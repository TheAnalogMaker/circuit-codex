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

## What the drawing resolves, and what it does not

The title block, tube complement (a dual-5U4GA rectifier and a 2×12AY7/1×12AX7
preamp split), the rail chain and V1's front end all read consistently off the
drawing, agree across the two archived copies of the same A-EE sheet, and gate
against the printed chart within the usual tolerance (worst node 29.8%, against
the chart's own ±20% convention and the extra slack a choke-less,
dual-rectifier supply earns). Three things the sheet does **not** resolve are
flagged here rather than guessed at:

- **V2's own pin voltages** — the printed figures around V2 sit in a cluster
  dense enough that they cannot be confidently separated from the neighbouring
  tone-network figures. `voltages.yaml` reports them as simulated-only
  (`chart: null`).
- **V3's plate/cathode/junction pin voltages** — a printed figure cluster near
  +210/+72/+1.7 V sits close to the 12AX7 on the sheet, but the obvious
  assignment (+72 V to the cathode pin, +1.7 V to the grid-leak junction) does
  not survive simulation: a 12AX7 cannot hold ~1.25 mA against the roughly
  −70 V grid-to-cathode bias that pairing implies, so at least one figure
  belongs to another node — possibly to V2. The netlist therefore uses the
  5F4's V3B values verbatim (56k plate, 1.5k/56k cathode split, the same
  shape), and `voltages.yaml` leaves PPI/KPI/JPI informational rather than
  assign the printed numbers to pins the physics rules out.
- **One lug of the Presence/Bass/Treble ladder** — the ladder is drawn as read
  (see below), with a single residual lug-level uncertainty annotated on the
  schematic itself. Because the network is entirely DC-open, none of it bears
  on the operating point; it does mean the tone-stack lab has no topology to
  plot for this amp, whose ladder is not one of the shapes it solves.

All three are draft-status gaps, not disputes: nothing here contradicts the
drawing. The bias-supply figure's printed **sign** is also
not clearly legible on the archived scan (magnitude ~42 V is clear); it is
read as negative for consistency with every other fixed-bias amp in this
corpus and because the circuit only functions as drawn (a fixed-bias output
pair) with a negative supply.

## The tone ladder, lug by lug

The schematic redraws the Presence/Bass/Treble ladder from a lug-level read of
the A-EE sheet: a bleeder, a bass shelf, and a shared presence/NFB bus fed by a
20 kΩ resistor off the speaker node — the family's usual feedback take-off —
with the treble pot wired as a rheostat, the same trick the family's three-knob
ladders use for their bass pot.

Two details of that region are easy to misread and are worth stating plainly.
What looks at low resolution like one "10 MΩ channel-linking resistor in series
with a small mica cap" is two unrelated parts: `RFB`, a light V2 plate-to-grid
feedback resistor drawn as a loop above V2, whose left end lands on the
post-mixer V2 grid node rather than on the input jacks; and `CJ1`, a
channel-jumper cap bridging the two channels' post-coupler nodes directly. Each
channel also carries a 100 kΩ padding resistor from its coupler to its
volume-pot hot lug (`RP1`/`RP2`). And the bass-shelf mica reads **.005**, i.e.
0.005 µF (`CBS`), not the .0005 the same dense patch of ink can suggest — a
factor of ten, and worth a third read before this entry leaves draft.

**One residual uncertainty, flagged rather than guessed past:** which of the
bass pot's two end lugs is the "hot" one riding the shared presence/NFB bus and
which is the "cold" one feeding the fixed shelf network. It is drawn as read,
the two lugs sit close together on the sheet, and the schematic carries a
comment saying so right above that block. A lug-by-lug re-check would firm it
up before this entry leaves draft.

## The board

The board diagram is redrawn from the A-EE sheet's own layout page: the
principal components in the order the drawing shows them, with their hookup.
The parallel-rectifier supply is the feature of it — two 5U4GAs and no choke,
so plates, screens and the output transformer's centre tap all land on one
first-filter node carrying three 16 µF cans, where most of this corpus's
tweed amps split the screen supply behind a choke.

The drawn point-to-point wiring is proved electrically equivalent to the
simulated circuit within the documented DC scope, every valve anchored, with
the two rectifiers outside the DC model by the same convention every other
rectifier here follows. The five panel pots sit off the board as the sheet
draws them, and the primary leads land on chassis switches; the fixed
tone-network parts are on the board.

## Lineage

The Bassman family history records the 5F6/5F6-A's long-tailed-pair phase
inverter as a revision of "the cathodyne splitter" that came before it. This
circuit is that predecessor: the corpus carries the edge in both directions,
5E6-A → 5F6. Behind the 5E6-A stand the plain 5E6 and the 5D6, neither of them
a documented circuit here, so this entry claims no ancestor of its own.
