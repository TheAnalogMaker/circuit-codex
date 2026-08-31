# 6G6-B — Blonde Bassman-style

The middle circuit of the piggyback Bassman's three-revision run: a
50-watt head-and-cabinet rig that replaced the tweed 4x10 combo entirely.
Fender moved the Bassman name onto a genuinely different amplifier here —
two full input channels (Bass, Normal), each running its own two-stage
preamp and its own Bass/Treble/Volume network, mixing into a shared driver
stage before a long-tailed-pair phase inverter and a fixed-bias 5881 pair.
The 6G6 (late 1960) used a GZ34 tube rectifier; the 6G6-A (early 1961)
moved to solid-state rectification; the 6G6-B carried that forward with
further circuit changes through 1963, running in blonde Tolex until the
blackface [AA864](/amps/aa864-bassman/) piggyback head replaced it in 1964 —
carrying this circuit's two-channel split, its solid-state supply and its
long-tailed-pair inverter with it.

## Circuit walkthrough (short form)

**Bass channel**: two inputs (68 kΩ stoppers, 1 MΩ leak) → **V1A** (2.7 kΩ
cathode, 220 kΩ plate off the Bass row's +230 V lane, printed +135 V/+1.1 V)
→ **V1B**, a *cathode follower* direct-coupled to that plate: its own plate
lead goes straight to the same +230 V lane with no plate resistor in it, and
its 100 kΩ cathode load is the stage's output, printed +136 V. That cathode
drives the Bass/Volume network (1 MΩ and a 250 pF + 47 kΩ branch, two
0.25 µF bridging caps, a 10 kΩ dropper paralleled by the 25 kΩ-L Bass pot,
an 820 Ω foot and a 250 kΩ-L Volume pot) whose wiper feeds the shared driver
stage.

**Normal channel**: two inputs → **V2A** (1.5 kΩ cathode, 100 kΩ plate load
climbing to that channel's own +355 V lane, printed +230 V/+1.9 V) → a
Treble/Bass network (250 pF into a 350 kΩ/70 kΩ-tap Treble pot; 0.05 µF into
a 250 kΩ-A Bass pot over a 6.8 kΩ foot with 0.005 µF across it) → a 1 MΩ-A
Volume pot → **V2B** recovery (2.7 kΩ cathode, 220 kΩ plate off the same
+355 V lane, printed +190 V/+1.8 V) → a 470 kΩ resistor into the shared
driver stage's grid.

**Shared driver**: both channels' Volume outputs land on **V3A**'s grid
(100 kΩ plate off +230 V, 1.5 kΩ cathode, printed +150 V/+1.2 V) → the Bass
channel's own 250 kΩ-A Treble control (the front panel's BASS/TREBLE/VOLUME
group ahead of the Bass jacks reads 25k-L/250k-A/250k-L, so this pot sits in
the driver bottle's signal path rather than beside the channel's other two
knobs) → **V3B** recovery (1.5 kΩ cathode, 100 kΩ plate off +230 V with
0.002 µF across it, printed +150 V/+1.3 V) → 470 kΩ + a 500 pF coupler into
the phase inverter.

**Phase inverter**: long-tailed pair, 82 kΩ (hot) / 100 kΩ (cold) 5%
plates off a +410 V lane (printed +300 V/+280 V), both 1 MΩ grid leaks
returned to the tail junction. The shared cathodes sit 820 Ω above that
junction — printed +30 V at the cathodes, +28 V at the junction. Below the
junction the sheet letters the whole foot: 6.8 kΩ down to a
presence/feedback node, 4.7 kΩ from there to ground, the 56 kΩ speaker
feedback returning to the same node (a second path to ground through the
output transformer's secondary), and the front panel's 25 kΩ-L Presence pot
bridging the 4.7 kΩ end to end with a 0.1 µF · 200 V cap on its wiper.

**Output**: two 5881s, fixed-biased through 220 kΩ leaks from a −54 V
supply (grounded cathodes, no cathode resistor), 470 Ω 1 W screen
resistors off a +430 V tap, plates direct on +428 V.

**Power**: a centre-tapped HT winding feeds two three-diode series legs — a
solid-state full-wave rectifier; there is no rectifier tube. The chain runs
+430 V (screens, at the reservoir) → choke (TR2, 125C1A) → +428 V (plates)
→ 4.7 kΩ · 1 W → +410 V (phase inverter) → 27 kΩ · 1 W → +355 V (the Normal
channel's whole lane). The Bass row's +230 V lane hangs off the +428 V node
through its own 56 kΩ · 1 W dropper and a 20 µF · 600 V filter. A small
silicon diode off an AC tap, 1 kΩ dropping, a 27 kΩ bleeder and a 25/50 µF
dual can produce −54 V for the output bias.

## Reading this drawing

The E-FB drawing (both the board-layout and schematic pages) prints its own
title block reading "FENDER 'BASSMAN' LAYOUT / SCHEMATIC — MODEL 6G6-B" —
confirmed against the target amp before any value was read.

Two places on this sheet are easy to misread, and both reward a lug-level
look at high magnification.

- **V1B is a cathode follower.** Its plate lead runs straight down to the
  Bass row's +230 V lane with no plate-load resistor in it; its grid takes
  V1A's plate directly, with no coupling capacitor and no grid leak of its
  own; and its 100 kΩ cathode load is what feeds the tone network. The
  printed figure at that cathode is **+136 V**, not +13.6 V — the mark
  between the 3 and the 6 is the +230 V lane's own wire crossing the
  lettering, and it runs the full height of the text rather than sitting on
  the baseline like the decimal points elsewhere on the sheet. A follower
  riding about a volt above the +135 V plate that drives it is exactly what
  +136 V beside +135 V describes; read the crossing wire as a decimal point
  and the resulting 13.6 V across 100 kΩ is a current no self-biased 12AX7
  stage can pass at any rail on this drawing.
- **The sheet's third "+230 V." is a plate voltage.** It letters +230 V
  twice on the Bass row's own supply lane — a rail — and once more in the
  Normal channel, at V2A's plate. That plate's 100 kΩ load climbs to the
  +355 V lane, the same lane V2B's 220 kΩ uses. Hang it on a shared
  +230 V rail instead and the stage's current halves, leaving the cathode a
  third under the printed 1.9 V — the sheet's own figures rule that reading
  out.

Both readings are corroborated by arithmetic already on the sheet.
136 V across 100 kΩ is 1.36 mA; add V1A's 0.43 mA and the driver bottle's
two 0.8 mA sections and the +230 V lane draws about 3.4 mA, which across its
own 56 kΩ · 1 W dropper falls 190 V from the +428 V node — landing on the
printed +230 V. Read as a common-cathode stage instead, V1B passes about
30 µA, the lane draws 2 mA, and the same dropper would leave it above
+310 V. In the Normal channel, the 125 V across V2A's 100 kΩ is 1.25 mA, and
1.9 V across its 1500 Ω cathode resistor is 1.27 mA — the two printed
figures agreeing to 2%.

V3A's cathode figure (+1.2 V beside its 1.5 kΩ) and the phase-inverter
tail's whole foot (6.8 kΩ, 4.7 kΩ, the 56 kΩ feedback and the Presence pot
across the foot) are likewise printed on the sheet and read directly:
nothing in the simulated deck is an estimate.
The Presence pot itself is the one drawn DC path left out of the deck — pots
are omitted corpus-wide — and including its 25 kΩ element would move the
tail junction from 28.4 V to about 27.8 V, both inside the chart's ±20%.

With the circuit the sheet actually draws, every gated node lands: the worst
is V1A's cathode at 17.3% against the chart's own ±20% convention. The entry
stays a draft only because a verified badge is a maintainer's to grant.

The board drawing follows the E-FB layout page, and it draws each channel's
Bass, Treble and Volume network in full — on this sheet those parts mount on
the board rather than at the panel, which is why they appear here and not as
panel stubs. The drawn wiring is proved electrically equivalent to the
simulated circuit.

## The Bass/Normal split, and why the driver bottle carries a Treble pot

This is a genuinely two-channel amplifier, not a single voice with a bright
switch: each channel gets its own complete two-stage preamp and its own
tone network, and they mix only after both have already been shaped. The
Bass channel's Treble control physically living inside the shared driver
bottle's own signal path (between its two triode sections) rather than
beside the channel's Bass and Volume pots is a printed fact of this
drawing, not a simplification — the front-panel silkscreen order
(Presence, Bass, Treble, Volume, then the Normal jacks; Bass, Treble,
Volume, then the Bass jacks) is what fixes which knob belongs to which
channel, and the schematic's own component placement is what shows the
Bass channel's Treble pot living downstream of the mixing point.

The Normal channel, by contrast, carries its Treble control in its own
first-stage network (350 kΩ/70 kΩ tap) before mixing — the two channels'
tone-shaping paths are not identical twins of each other, only broadly
parallel.
