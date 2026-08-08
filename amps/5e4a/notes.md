# 5E4-A — Tweed Super-style

The narrow-panel Super of 1955–56, and the circuit in which the tweed Super's
final shape arrives: two channels of 12AY7 into a second 12AY7 that gains and
then follows, a treble and bass network hung on that follower's cathode, a
driver into a split-load phase inverter, and a fixed-biased output pair on a
separate negative supply. Everything the 5F4 is remembered for is already here.
What the 5F4 changed was the output bottles and the rails.

## The name on the drawing

Fender's title block reads **`MODEL 5E4-A*`**, and the asterisk points at a
boxed note in the corner of the same sheet: **`*NOTE — (A) WAS 22 K OHMS`**.
The `(A)` is a circled marker on the bias-supply series resistor, drawn here at
18 kΩ. The drawing is a running revision, annotated in place — the way Fender
amended a sheet without redrawing it — and the suffix is the amendment's name.

That matters for anyone searching. Several documents circulating under a plain
"5E4" label are this drawing with the `-A` and its footnote removed from the
title block: same Fender drawing code (`G-EE`), same 6V6GT output pair, same
selenium bias cell, same printed voltages. The circuit archived here is filed
under the designation its own title block prints. What a genuine plain 5E4
looked like — the family history records it as a 6L6G amplifier with no
selenium bias cell — is a separate question, and one this archive leaves open
until a drawing for it turns up. The family file says so in as many words.

## The output stage is the surprise

A Super with **6V6GT** output tubes reads like a mistake, because the
designation's neighbours on either side — the wide-panel 5D4 before it, the
5F4 after it — are 6L6 amplifiers. The sheet is unambiguous: both output
bottles are lettered `6V6GT`, their screens tie straight to the +385 V node
with no screen resistors, their cathodes are grounded, and their grids return
through 220 kΩ leaks to a **−32 V** bias line off a selenium cell. That is a
6V6 pair run hard — the datasheet's design-centre plate rating is 315 V and
this circuit puts about 390 V on the plates — and it is the same trick the
tweed Deluxe plays one cabinet size down, with fixed bias instead of cathode
bias and a much bigger power supply behind it.

Two things follow from it. The amplifier is quieter at idle than a 6L6 Super
(a fixed-biased 6V6 pair draws far less standing current), and it runs out of
headroom sooner and more gradually, which is most of why a narrow-panel Super
is described as breaking up "earlier" than its own successor.

## Circuit walkthrough (short form)

**Front end.** Four jacks, two per channel, each through a 68 kΩ resistor onto
its channel's grid bus, with a 1 MΩ leak at the jacks. Both halves of the first
12AY7 sit on **one** 820 Ω cathode resistor with a 25 µF can, so neither channel
solves alone. 100 kΩ plate loads off the +250 V rail, then a 0.02 µF coupler
into each channel's 1 MΩ volume control — the Instrument channel with a 100 pF
cap across it for brightness — and a 270 kΩ mixing resistor from each wiper into
one grid.

**Gain stage and follower.** The second 12AY7 is where the 5F4 puts a 12AX7.
Its first half is a plain gain stage (100 kΩ plate, 1.5 kΩ cathode with a 25 µF
can); its plate runs DC-direct to the second half's grid, and that half is a
cathode follower on a 100 kΩ load, sitting at +130 V. The follower's job is to
drive the tone network from a low impedance, which is the only reason a passive
treble/bass stack of this kind works at all.

**Tone network.** From the follower's cathode, two branches. A 250 pF capacitor
feeds the 1 MΩ treble pot, whose cold end goes to ground through 0.01 µF. A
0.1 µF capacitor feeds a 220 kΩ leak and a 100 kΩ series resistor into the 1 MΩ
bass pot's **wiper**, with 0.005 µF on the pot's leg. A second 220 kΩ carries
the bass branch back to the network's output node — which is the phase-inverter
grid, with no coupling capacitor between them. A 5 MΩ resistor returns from the
bass branch to the gain stage's grid; that node is held near ground by its own
220 kΩ leak, so at DC the 5 MΩ is simply a grid leak.

**Phase inverter.** Not a long-tailed pair. The 12AX7's first half is a driver
(100 kΩ plate at +190 V, 1.5 kΩ cathode at +1.6 V) fed DC-direct from the tone
network; a 0.02 µF coupler takes its plate into the second half, a **split-load
cathodyne** with a 56 kΩ plate load and 1.5 kΩ + 56 kΩ under the cathode. Its
1 MΩ grid leak returns to the 1.5 kΩ/56 kΩ junction, which the sheet prints at
+56.5 V against +58 V at the cathode — a 1.5 V difference across 1.5 kΩ, so
about 1 mA, which is exactly what the 56 kΩ plate load's printed drop implies.
The stage is self-consistent on its own chart. Its two outputs leave through
0.1 µF capacitors, plate to one output grid and cathode to the other, each
through a 1.5 kΩ stopper.

**Feedback and presence.** A 56 kΩ resistor from the speaker winding lands on
the driver's cathode, with a 5 kΩ presence pot in series and 0.1 µF from its
wiper to ground — the tweed presence circuit exactly as the 5F6-A and 5F4 use
it. At DC the feedback path parallels the driver's 1.5 kΩ cathode resistor with
roughly 56 kΩ through the output secondary: a 2.6% shift on a 1.6 V node,
recorded here and not modelled.

**Supply.** 5U4GA into a 16 µF reservoir at +390 V, a choke to +385 V (screens
and the output-transformer centre tap), then 10 kΩ to +300 V for the 12AX7 and
another 10 kΩ to +250 V for the two 12AY7s, each node with its own can. A
standby switch sits between the reservoir and the rest. The bias supply is its
own branch: 18 kΩ — the resistor the sheet's footnote says was 22 kΩ — into a
selenium cell, then 100 µF with a 56 kΩ bleeder, giving the printed −32 V.

## A note on verification

The drawing states its own measurement convention on both pages: *voltages read
to ground with an electronic voltmeter, values shown ±20%*. The schematic sheet
prints the rails and every cathode; the layout sheet, same title block and same
notice, prints the plate voltages beside the eyelets they belong to. Between
them the chart covers every node this netlist solves, so the entry is gated
against the drawing's own figures at the drawing's own tolerance. Every rail
lands within 6%; the worst node is the shared 12AY7 input cathode at 10.0%,
with the driver plate next at 9.2%. Nothing is disputed and nothing is
force-fitted.

One approximation is stated rather than hidden. The sheet's 390 → 385 V drop
across the choke is taken by the whole plate-plus-screen current, but this
netlist omits output-transformer primary DCR — so the plate current reaches the
6V6GTs without crossing the choke, and only the screen and preamp current does.
The choke's DCR is entered as a plain 60 Ω estimate and the small residual is
recorded, because inventing a resistance that reproduces a drop the model
routes around would be arithmetic dressed up as a measurement.

## A note on the drawings

The board layout here is **not** derived: Fender published a layout sheet for
this circuit, page 1 of the same drawing, and the board order and the
lead-by-lead wiring are read from it. The chassis carries four input jacks; the
schematic draws one per channel, and the two 1 MΩ grid leaks mount at the jacks
as the layout sheet shows. The presence pot, the negative-feedback resistor,
the bright cap and the AC-line capacitors are chassis wiring drawn schematically
or off the board.
