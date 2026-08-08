# 5C1 — Wide-panel Champ-style

The earliest circuit-numbered Champ, and the corpus's first octal-preamp
circuit: a single 6SJ7 sharp-cutoff pentode giving one stage of voltage gain,
one 1 MΩ volume control, a cathode-biased 6V6 single-ended output, and a
5Y3GT rectifier — no tone control and no phase inverter. Wide-panel tweed
cabinet, produced circa 1953–1955. It carries the Champion 600's circuit
forward under Fender's new "Champ" model name (history/families/champ.yaml)
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
reservoir at **+340 V**. Unlike every later Champ in the line, there is no
choke here — a plain **500 Ω** resistor drops the rail to **+320 V**, which
supplies only the 6V6 plate (through the output-transformer primary); a
**25 kΩ** resistor then drops that node further to **+260 V**, and it is
*this* third rail — not the plate's own +320 V node — that the drawing routes
to the 6V6 screen, alongside the whole 6SJ7 plate/screen circuit. So the
single output tube's screen shares a dropper-filtered rail with the preamp
rather than riding its own plate's node, which is the opposite of where a
reader would guess it sits at a glance. Three 8 µF / 450 V cans do the
filtering — the same three-can arrangement the 5E1 keeps, just filtered
through resistors instead of the choke the 5E1 introduces.

## The 6SJ7, and why it has no cathode resistor

The 5C1's preamp tube is an octal metal pentode, not the 9-pin 12AX7 twin
triode every later Champ in the line uses — grid No.1 comes out on a base pin
rather than a top cap, which is what let Fender mount it flat on a
chassis-board like everything else (reference/tubes/6sj7.yaml). Fender bias
this stage the cheapest way available: **grid-leak (contact) bias**. The
cathode ties straight to ground, and a single 5 MΩ resistor returns the grid
to ground too — with no cathode resistor anywhere in the stage. A real 6SJ7
run this way self-biases to a small negative grid voltage from grid contact
potential and rectified grid current, not from a cathode voltage drop. It is
a real, period-correct circuit (matched by the printed chart's own +130 V
plate reading, well below what a zero-bias 6SJ7 would show), and it
disappears from the Champ line entirely once the 5E1's 12AX7 arrives with
conventional cathode-biased stages.

### A documented model limitation, not a circuit claim

The project's tube models are fitted from datasheet anchor points in the
Koren model form and explicitly carry no grid-current path
(`models/METHODOLOGY.md`, "No grid-current model (v0)" — confirmed in
`models/6sj7.inc`'s subcircuit, which ties the grid node only to the
plate/cathode through AC-only Miller capacitances). Contact bias is exactly
the mechanism that gap can't reach: with nothing but a capacitor and a
to-ground resistor at the grid, this DC deck has no current path that would
pull the grid negative, so it settles `Vg1` at 0 V — a real (if small)
departure from the tube's actual operating point. The 6SJ7 plate node is
therefore marked `chart: null` in `voltages.yaml` (reported, never gated)
rather than compared against the printed +130 V, which is honest about what
the simulation can and cannot show here rather than papering over it with a
misleading percentage. The B+ rails and the 6V6 stage — which do not depend
on this mechanism — are fully chart-gated as usual.

## Verification

The layout sheet prints a voltage chart (Fender's usual "read to ground with
an electronic voltmeter, ±20%") giving the two B+ rails downstream of the
reservoir (+320 V at the 6V6 plate, +260 V at the shared 6V6-screen/6SJ7
rail), the 6SJ7 plate (+130 V, not chart-gated — see above), and the 6V6
cathode (+14 V). `pipeline/verify_amps.py` simulates within tolerance on
every chart-gated node: the 6V6 plate rail 1.4% off (+324.4 V), the shared
screen/preamp rail 3.9% off (+249.8 V), and the 6V6 cathode 9.7% off
(+15.4 V) — all inside Fender's own ±20% convention. Getting the screen rail
right took a second pass: routing it (as first drafted) onto the plate's own
+320 V node instead of the drawing's actual +260 V node overloaded the 6V6
enough to pull the simulated cathode to +20.4 V, a 46% miss, and dragged the
shared rail down to +303 V against its +260 V chart reading, a 17% miss on a
node the tube isn't even supposed to load that hard. Both symptoms cleared
once the screen moved to its drawn node.

## Schematic and layout

`schematic.kicad_sch` is redrawn from the same F-DH sheet's schematic page
(`pipeline/draw_5c1.py`) and passes `check_schematics.py`, including its
KiCanvas-strict tokenization check. `layout.yaml` is redrawn from the F-DH
sheet's *own* layout page (page 2 of the same PDF) — a genuine factory layout
sheet exists for this circuit, so the board order and point-to-point wiring
are read from it rather than derived: 6SJ7 preamp stage, then 6V6GT output,
then the resistor-dropped B+ chain, then 5Y3GT rectifier, left to right — the
reverse of the rectifier-first reading order every later Champ in this corpus
uses. Both drawing styles render clean with zero collision-lint findings and
no waiver. `pipeline/verify_layout_nets.py` proves the drawn wiring
electrically equivalent to `netlist.cir` (`wiring_claim: verified`); getting
there surfaced one real bug in the netlist itself — `C3` (the 6SJ7-plate-to-
volume-pot coupler) had been modelled as a direct bridge from the plate node
to the 6V6 grid node, short-circuiting past the pot the drawing actually
routes it through. The fix (removing `C3` from `netlist.cir`, matching how
5E1's and 5F1's identical pot-input couplers are already left out) changes no
simulated voltage — SPICE treats a coupling cap as open at DC regardless of
whether the line is present — but it was the difference between an honest
equivalence proof and a false one.

With both drawings landed and every gate above green — `check_schematics`,
`check_layouts` (zero findings, both styles), `verify_layout_nets`
(`wiring_claim: verified`), and every chart-gated node in tolerance —
`verification.status` moves to `verified` (`docs/schema.md`, AGENTS.md rule
4). `pipeline/fit_models.py` was not re-run for this pass — the 6SJ7 model
already exists in `models/6sj7.inc` and carries zero drift here.
