# AC15 — Vox AC15-style

The AC15 was Jennings Musical Industries' first guitar amplifier, a British
15-watt combo from the end of the 1950s, and the circuit documented here is its
third revision: JMI drawing OA/031, *"VOX AC.15" amplifier circuit No. 3*, drawn
on 29 April 1960 and signed off by Dick Denney. It is the version that put the
phase-shifting vibrato back inside the amplifier rather than in a box on the
back, and it stayed in production, unchanged as a circuit, into 1963.

Almost nothing about it is done the way an American amplifier of the same year
does it. There is no tone stack. There is no bias supply. The two channels do not
mix before the phase inverter — they mix *inside* it. The first valve is a
pentode, not a triode. Every one of those choices is audible.

## Circuit walkthrough (short form)

**Normal channel.** Input (33 kΩ stopper, 1 MΩ leak) → **EF86 pentode**, running
a 220 kΩ anode load, a 1 MΩ screen feed bypassed by 0.1 µF, and a 2.2 kΩ cathode
resistor with a 25 µF bypass. This is not a Vox invention: it is Philips' own
published application circuit for the valve, reproduced part for part — the
datasheet tabulates a voltage gain near 200 for exactly this network, several
times what a triode stage delivers in the same place. The anode couples out
through 0.01 µF into the **Brilliance** switch, and from there to a 500 kΩ volume
control. The switch works on a 250 pF capacitor sitting in series with that
signal path: leave the switch open and everything has to cross the small cap, so
only the top end gets through; close it and the cap is shorted out, restoring the
full-range coupling.

**Vibrato/Tremolo channel.** Its own input valve (ECC83) and a two-position tone
network feed a phase-shift ladder of five 0.0047 µF capacitors and four 1 MΩ
returns. An ECC82 modulator swings that ladder under the control of an ECC83
phase-shift oscillator with **Speed** and **Depth** controls and a
footswitch — the circuit Vox called Vibravox. Because the ladder shifts phase
rather than simply gating level, this is closer to true vibrato than the
amplitude tremolo of its American contemporaries.

**Phase inverter.** Both channels arrive here, at a **long-tailed pair** (ECC83,
100 kΩ anode loads, a 1.2 kΩ shared cathode resistor over a 47 kΩ tail, both
1 MΩ grid leaks returned to the tail junction) — but not at the same grid. The
Normal volume drives one side, the Vibrato/Tremolo volume drives the other, so
the two channels are summed by the inverter itself. Playing into both inputs at
once is therefore not quite the parallel blend it would be in a Fender: the
channels enter in opposite phase.

**Top Cut.** The amp's only tone control, and it sits after the inverter, not
before it: a 250 kΩ pot in series with a 0.005 µF cap, bridged across the two
inverter outputs. Turning it up shunts treble differentially between the two
phases, so it darkens both channels at once, downstream of everything.

**Output.** Two **EL84** pentodes, 1.5 kΩ grid stoppers, 220 kΩ grid leaks, and
100 Ω screen stoppers off the same rail as the anodes. Bias is a single shared
130 Ω cathode resistor with a 50 µF bypass — one resistor for the pair, no bias
supply and no adjustment — feeding an output transformer with 8 Ω and 15 Ω taps.
There is no negative-feedback loop anywhere around the output stage.

**Power.** An **EZ81** rectifier off a 300-0-300 V secondary feeds a 16 µF
reservoir, a 10–20 H choke and a second 16 µF can; the standby switch breaks the
rail after the choke. Three 22 kΩ / 3 W droppers hang off that +315 V rail, one
for each channel and one for the phase inverter. Mains taps run 115 through
245 V; transformers came from Haddon, the choke from Radiospares.

## Why it sounds the way it does

Three things carry most of the character. The EF86 front end supplies gain a
triode cannot, so the amp is already working hard at modest volume. The output
pair is cathode-biased and carries no feedback loop, which lets the stage
compress and bloom instead of stiffening up. And the Top Cut sits at the
inverter rather than in the preamp, so the top end is trimmed *after* the amp
has done its distorting — the reason a rolled-off AC15 still sounds bright-edged
rather than muffled.

The EF86 is also the amp's fragile part. It is a high-gain small-signal pentode
in a combo cabinet with a 12-inch speaker, and it is famously microphonic in that
job. It survived the scale-up: the first AC30/6, drawn on the same day as this
amp's own sheet, kept the EF86 on its Normal channel. It was the revision of
May 1961 that dropped it, replacing it with an ECC83 for exactly that reason —
in a louder cabinet the valve's sensitivity to vibration had become the
amplifier's weak point.

## A note on verification

The factory drawing annotates five working voltages — +325 V at the reservoir,
+315 V at the rail, +90 V at the EF86 anode, +220 V at the phase-inverter anode
and +310 V at the EL84 anodes — but prints no tabulated valve-voltage chart, so
there is no per-pin reference and no stated measurement convention behind them.
Simulated from the redrawn netlist, the phase inverter lands within 2% of its
printed figure and the output stage settles at an entirely believable 11 V of
cathode bias. The EF86 anode does not: it simulates about a quarter low. That
gap is in the tube model, not the circuit — Philips' own tabulated figures for
this exact resistor network predict an anode within a few volts of the printed
+90 V, while the archive's single-anchor EF86 model draws roughly 10% more
cathode current at this far-from-datasheet operating point, and a 220 kΩ anode
load turns 10% of current into a quarter of the voltage.

The circuit is therefore published as a **draft**. Its topology and part values
are read from the factory drawing and cross-checked against two independent
published readings of the same circuit; its operating point is not yet confirmed
end to end.

The DC netlist covers the Normal channel, the phase inverter and the output
stage. The Vibrato/Tremolo channel is documented in the parts list but left out
of the simulation: its oscillator has no static operating point to solve for, and
reporting a partial answer for that side of the amp would be worse than reporting
none.

## A note on the drawings

The redrawn schematic asserts every connection the published drawing resolves:
the Normal channel, the phase inverter, the Top Cut, the output stage and the
power supply. The Vibrato/Tremolo channel's tone, phase-shift, modulator and
oscillator networks are inventoried part by part in the parts list, but the
available scan does not resolve how those parts interconnect, so the schematic
names the interfaces each valve works into and asserts nothing further.

The board layout is **derived**. JMI published no board-layout sheet for the
AC15, and none has been located, so the diagram lays this circuit's own parts
out in signal order along the chassis on the house eyelet grid — a builder's
reference for the circuit rather than a record of the factory's tag-strip
construction, which is what the amplifier actually used. Its point-to-point
wiring is nonetheless machine-checked: every part the operating-point netlist
models is verified in CI, terminal for terminal, to sit on the same nets the
simulation solves.
