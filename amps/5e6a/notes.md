# 5E6-A — Tweed Bassman-style

The mature narrow-panel revision of the 4x10 tweed Bassman's dual-rectifier
era, and the last stop before the 5F6 brought in the three-knob tone stack and
the long-tailed-pair phase inverter that made the line famous. Its preamp is
already the one the tweed Super's 5F4 draws: an input stage, a gain stage
direct-coupled to a cathode follower, a two-knob treble/bass network fed from
that follower, and a 12AX7 driver ahead of a split-load phase inverter. What
it keeps from its 5D6 ancestor is the supply: two 5U4GA rectifier tubes in
parallel.

## Circuit walkthrough (short form)

**Input.** Two channels, each jack running straight to a 12AY7 grid with a
1 MΩ leak and no grid stopper. The two halves share an 820 Ω / 250 µF cathode
and carry 100 kΩ plate loads from the +275 V rail. Each plate feeds a 1 MΩ
Volume control through 0.02 µF, and the bright channel's control carries 100 pF
from its hot lug to its wiper. The two wipers meet at the next grid through
270 kΩ each.

**Gain stage and cathode follower.** The second 12AY7's first half is a gain
stage (100 kΩ plate load, 1.5 kΩ / 25 µF cathode). Its plate runs straight to
the other half's grid, and that half is a cathode follower: plate on the
+275 V rail, 100 kΩ from cathode to ground.

**Tone network.** Two branches leave the follower's cathode. The treble branch
is 250 pF into one end of the 1 MΩ Treble control, whose other end bleeds to
ground through 0.01 µF. The bass branch is 0.1 µF into a node that 220 kΩ holds
at ground and that also returns 10 MΩ of feedback to the gain stage's grid;
from there 220 kΩ feeds the Bass control's wiper, whose ends go to ground
directly and through 0.005 µF. A last 220 kΩ joins the Bass wiper to the Treble
wiper, and the Treble wiper drives the next grid with no coupling capacitor.

**Driver and cathodyne.** The 12AX7's first half is a driver: 100 kΩ plate load
from +335 V and 1.5 kΩ cathode. The 20 kΩ negative-feedback resistor from the
speaker line lands on that cathode, and so does the 5 kΩ Presence control,
whose wiper goes to ground through 0.1 µF. The driver's plate couples through
0.02 µF into the other half, a split-load (cathodyne) phase inverter: 56 kΩ
plate load, 1.5 kΩ then 56 kΩ under the cathode, and a 1 MΩ grid leak returned
to the junction between them.

**Output.** The cathodyne's plate and cathode each feed a 6L6G grid through
0.1 µF, onto the junction where a 220 kΩ leak from the −42 V bias supply lands,
then through a 1.5 kΩ stopper. The screens and the output transformer's centre
tap share the +410 V node, and the transformer drives four 10-inch speakers.

**Power.** Two 5U4GA rectifiers in parallel, each HT lead to one plate of each
bottle, reach the first 16 µF can at **+420 V** through the standby switch. A
choke follows, and two more 16 µF cans hold **+410 V** for the screens and the
centre tap. A 10 kΩ dropper gives **+335 V** (driver and cathodyne), and a
second gives **+275 V** (input stage, gain stage and follower). The bias comes
from a tap on the HT winding through 3,300 Ω and a selenium rectifier to
**−42 V**, with 100 µF and 56 kΩ to ground.

## What sets it apart from its neighbours

- **Two rectifier tubes.** The 5E6-A keeps the paralleled pair of 5U4GAs the
  Bassman family history describes for the 5D6 line, where the 5F4, 5F6 and
  5F6-A in this corpus each run one rectifier tube.
- **The choke sits ahead of the output transformer.** On the 5F4 the centre tap
  takes the first filter node and the choke feeds only the screens and the
  preamp. On the 5E6-A the centre tap and the screens both sit after the choke,
  so it carries the whole amplifier's current.
- **The 5F4's preamp, with different values.** The stage chain is the one the
  5F4 draws, stage for stage. The 5E6-A puts a 12AY7 where the 5F4 has a 12AX7
  in the gain stage and follower, uses no input grid stoppers where the 5F4
  has 68 kΩ, and letters 220 kΩ where the 5F4 has 100 kΩ in the bass branch,
  10 MΩ where it has 4.7 MΩ in the feedback return, and 20 kΩ where it has
  56 kΩ from the speaker.
- **Cathodyne, not long-tailed pair.** The Bassman family history's 5F6 entry
  reads "swapped the cathodyne splitter for a long-tailed-pair phase
  inverter". This circuit is that cathodyne.

## The operating point

Every figure the schematic page prints lands within the chart's tolerance when
the circuit is simulated: the four rails, the input stage, the gain stage and
its follower, the driver and the cathodyne, and the bias. The cathodyne's
resistor junction has no figure on the schematic page; the layout page letters
+70 V at that eyelet, and the table carries it. The choke's resistance is not
printed on either page, so the model sizes it to the printed 10 V drop across
it, and the +410 V node agrees with the chart by construction rather than as
an independent check.

## What the drawing leaves open

- **Three parts the two pages letter differently.** The layout page letters
  one of the two mixers 250 K where the schematic prints 270K for both, and
  letters the Treble's bleed capacitor 600 V where the schematic prints
  .01-400. The parts list enters the schematic's values and states the
  layout's lettering beside them.
- **One part only the layout page shows.** A 47 pF capacitor bridges the Treble
  control from its wiper to the lug the 250 pF feeds. The schematic page does
  not draw it; the schematic here does, marked as coming from the layout page.
- **Which jack feeds which grid.** The layout page takes both input leads under
  the board as a pair, so it does not show which of the two jacks reaches
  which grid. The board here follows the schematic's order.

## The 5E6 → 5E6-A revision

The 5E6 and 5E6-A drawings share the same drawing code (A-EE). The one
substantive difference is a handwritten note on the 5E6 sheet beside the
bias-supply series resistor: "THIS CHANGE TO INCREASE BIAS ON PLATES SO WON'T
GET HOT", with the original resistor value struck through and "3300" written
in. The 5E6-A drawing prints 3,300 Ω cleanly with no annotation — the fix
formalized. In this bias supply the resistor sits ahead of the selenium
rectifier, which charges a 100 µF filter loaded by a 56 kΩ bleeder, so a
smaller resistor lets the filter charge nearer the winding's peak and delivers
a larger-magnitude (more negative) bias. That lowers the 6L6G's idle current
and plate dissipation, which is the fix the note describes. It is the one
circuit-level change the "-A" suffix marks.

## The board

The board diagram is redrawn from the A-EE layout page: the principal
components in the order the drawing shows them, with their hookup. The bias
parts and four 16 µF cans sit at the power end, then the driver and cathodyne
parts, the +275 V can, the gain stage and follower, the tone network's board
parts and the mixers, and the input stage at the far end. The choke is a
chassis part whose two leads come up through a grommet to the +420 V and
+410 V cans. Several parts mount off the board as the drawing shows them: each
6L6G's 1.5 kΩ stopper on its socket, the gain stage's 100 kΩ plate load across
the second 12AY7's socket, the input grid leaks at the jacks, and the
tone network's pot-side parts at the controls.

The drawn point-to-point wiring is proved electrically equivalent to the
simulated circuit within the documented DC scope, every valve anchored, with
the two rectifiers outside the DC model. The 6.3 V heater layer is drawn as the
earlier board had it and is not yet established against the amplifier's own
drawing.

## Lineage

The Bassman family history records the 5F6/5F6-A's long-tailed-pair phase
inverter as a revision of "the cathodyne splitter" that came before it. This
circuit is that predecessor: the corpus carries the edge in both directions,
5E6-A → 5F6. Behind the 5E6-A stand the plain 5E6 and the 5D6, neither of them
a documented circuit here, so this entry claims no ancestor of its own.
