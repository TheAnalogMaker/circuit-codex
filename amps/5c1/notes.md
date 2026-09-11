# 5C1 — Wide-panel Champ-style

The earliest circuit-numbered Champ, and the corpus's first octal-preamp
circuit: a single 6SJ7 sharp-cutoff pentode giving one stage of voltage gain,
one 1 MΩ volume control, a cathode-biased 6V6 single-ended output, and a
5Y3GT rectifier — no tone control and no phase inverter. Wide-panel tweed
cabinet, produced circa 1953–1955. It carries the Champion 600's circuit
forward under Fender's new "Champ" model name (see the Champ family page)
and is the direct topological ancestor of the 12AX7-based 5E1 that replaces
it: the wide-panel-to-narrow-panel revision (5D1) that sits between the two
is a short-lived component revision of this same circuit, not a documented
redesign of its own (no landed circuit page).

## Circuit walkthrough (short form)

Two input jacks, each shunted to ground by its own 75 kΩ resistor, sum into
a single 0.02 µF coupling cap → **V1** (6SJ7 pentode, grid-leak/contact
biased: a 5 MΩ leak returns the grid to ground and the cathode grounds
directly, with no cathode resistor at all — the plate carries a 250 kΩ load,
the screen a 2 MΩ dropper bypassed by 0.05 µF) → 0.02 µF coupling → 1 MΩ
volume pot → **V2** 6V6GT (cathode-biased, 500 Ω with 25 µF bypass, grid
returned to ground through the volume pot) → single-ended output transformer
(≈5 kΩ : 8 Ω, typical for a single-ended 6V6; the drawing doesn't mark it)
→ speaker. No negative feedback loop on this circuit (the 5E1 does not add
one either; NFB into the Champ line waits for the 5F1).

Power: a center-tapped HT winding feeds the 5Y3GT full-wave rectifier into a
reservoir at **+340 V**. There is no choke here (the 5E1 that follows adds
one; the 5F1 and AA764 drop it again) — a plain **500 Ω** resistor drops the
rail to **+320 V**, which supplies only the 6V6 plate (through the
output-transformer primary); a
**25 kΩ** resistor then drops that node further to **+280 V**, and it is
*this* third rail — not the plate's own +320 V node — that the drawing routes
to the 6V6 screen, alongside the whole 6SJ7 plate/screen circuit. So the
single output tube's screen shares a dropper-filtered rail with the preamp
rather than riding its own plate's node, which is the opposite of where a
reader would guess it sits at a glance. Three 8 µF / 450 V cans do the
filtering — the same three-can arrangement the 5E1 keeps, just filtered
through resistors instead of the choke the 5E1 introduces.

## The 6SJ7, and why it has no cathode resistor

The 5C1's preamp tube is an octal metal pentode, not the 9-pin 12AX7 twin
triode the line switches to at the 5E1 and keeps from then on (the 5D1 in
between stays on the 6SJ7) — grid No.1 comes out on a base pin rather than a
top cap, which is what let Fender mount it flat on a
chassis-board like everything else (see the 6SJ7 tube page). Fender bias
this stage the cheapest way available: **grid-leak (contact) bias**. The
cathode ties straight to ground, and a single 5 MΩ resistor returns the grid
to ground too — with no cathode resistor anywhere in the stage. A real 6SJ7
run this way self-biases to a small negative grid voltage from grid contact
potential and rectified grid current, not from a cathode voltage drop. It is
a real, period-correct circuit — the printed chart puts its grid at −0.5 V
with the cathode at ground — and it
disappears from the Champ line entirely once the 5E1's 12AX7 arrives with
conventional cathode-biased stages.

### A documented model limitation, not a circuit claim

The project's tube models are fitted from datasheet anchor points in the
Koren model form and explicitly carry no grid-current path — a stated
limitation of the corpus's tube models, and confirmed in the 6SJ7 model's own
subcircuit, which ties the grid node only to the plate/cathode through AC-only
Miller capacitances. Contact bias is exactly
the mechanism that gap can't reach: with nothing but a capacitor and a
to-ground resistor at the grid, this DC deck has no current path that would
pull the grid negative, so it settles the grid at 0 V where the sheet prints
−0.5 V. The screen follows it: the sheet prints +21 V there, and the deck
settles near +12 V. Those two figures are carried in the voltage table as
reported, not gated. The 6SJ7 plate is gated like every other pin, and it lands
inside the chart's ±20 % — +149.3 V against the printed +130 V — but with the
stage's grid and screen off, that agreement says the plate voltage matches, not
that the 6SJ7's operating point does. The B+ rails and the 6V6 stage do not
depend on this mechanism and are chart-gated as usual.

## Verification

The layout sheet prints a voltage chart (Fender's usual "read to ground with
an electronic voltmeter, ±20%"): +340 V at the rectifier, +320 V where the
500 Ω meets the 25 kΩ, +280 V on the far side of the 25 kΩ (lettered at the
6V6's screen), the 6V6's plate and cathode at +300 V and +16 V, and the
6SJ7's plate, screen and grid at +130 V, +21 V and −0.5 V. The simulation is
gated on four of them and lands inside Fender's own ±20% on all four: the
+320 V junction 1.4% off (+324.4 V), the shared screen/preamp rail 10.8% off
(+249.8 V), the 6SJ7 plate 14.8% off (+149.3 V) and the 6V6 cathode 4.0% off
(+15.4 V). The shared rail runs low because the 25 kΩ carries 3.0 mA in the
simulation against the 1.6 mA the printed 320 → 280 V drop implies, most of
it the 6V6's screen current. The 6SJ7's screen and grid are reported, not
gated (see above). The 6V6 plate pin is not a node of its own here: the model
omits the output transformer's primary resistance, which drops the 20 V
between the junction and the pin.

The screen node is where this circuit punishes a careless reading. Tie the 6V6
screen to the +320 V junction instead of the +280 V node the drawing actually
feeds it from and the tube draws hard enough to lift the simulated cathode to
+20.4 V — 27.5% over the printed +16 V — while the shared rail, relieved of
the screen current, climbs to +303 V and takes the 6SJ7's plate to +180 V
against its printed +130 V, a 38.6% miss. The chart catches it on two nodes at
once, which is the point of gating against it.

## The board, as the factory drew it

A genuine factory layout page exists for this circuit — page 2 of the same F-DH
sheet — so the board order and the point-to-point wiring here are read from it
rather than derived. It runs 6SJ7 preamp stage, 6V6GT output, resistor-dropped
B+ chain, 5Y3GT rectifier, left to right: the reverse of the rectifier-first
reading order the four later Champs in this corpus (5E1, 5F1, AA764 and the
Vibro Champ AA764) all use.

The drawn wiring is proved electrically equivalent to the simulated netlist,
so this board carries a verified wiring claim, and both drawing styles render
with zero collision-lint findings and no waiver. One detail is worth naming
because it is easy to get wrong on a circuit this small: the coupler out of the
6SJ7's plate feeds the **volume pot**, not the 6V6 grid directly, so a model
that bridges plate to grid short-circuits past the control the drawing routes
it through. It makes no difference to any simulated voltage — SPICE treats a
coupling cap as open at DC either way — and every difference to whether the
equivalence proof means anything.

## The heater layer: a link removed, and what the sheet shows

The board drawing here used to close its heater chain with a link across the
last socket's two heater pins. Nothing on the F-DH sheet joins them, and the
6SJ7 has two heater pins and no centre tap, so those two pins *are* the supply's
two legs and a link between them is a short across it. The link is gone.

What the sheet shows, read at its full published resolution, is now stated on
this page as checked data. The schematic page draws the 6.3 V secondary with one lead grounded and
the other marked *to all 6.3 volt filaments* — the single-ended supply the
other two tweed Champs here, the 5E1 and 5F1, declare as well. On the layout
page each socket returns to chassis at the socket: at the 6V6GT a straight
lead crosses from heater pin 7 to the base
sleeve at pin 1, which the sheet grounds, leaving pin 2 the fed side; at the
6SJ7 a short bow ties heater pin 2 to the suppressor grid at pin 3, which this
circuit grounds, leaving pin 7 the fed side. The two bottles therefore ground
*opposite* heater pins, which is exactly the kind of fact no pin label can
supply and only the amplifier's own drawing carries. Both bottles are octal with
two heater pins and no centre tap, so the grouping itself was never in doubt
here — only which of the two each socket returns on, and that is now declared
and machine-checked against the leads drawn.
