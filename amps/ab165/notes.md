# AB165 — Blackface Bassman-style

The best-known blackface Bassman: a 50-watt piggyback head on a pair of
**6L6GC** output tubes, solid-state rectified, with two channels — **Bass** and
**Normal** — that meet at a shared mixing node instead of at the phase
inverter. It shares its name with the tweed 4x10 Bassman and almost nothing
else. Where the [5F6-A](/amps/5f6a/) is a guitar amplifier that happened to be
sold for bass, the AB165 is the purpose-built bass head Fender went back and
designed, and its voicing says so: the Bass channel opens with a 0.01 µF
capacitor thrown straight across its first plate load.

The drawing letters the three preamp bottles **7025**, the low-noise selected
12AX7; the inverter is a **12AT7**.

## Signal path

**Bass channel.** Two inputs (68 kΩ stoppers on a 1 MΩ leak) → a 12AX7 stage
with a 100 kΩ plate load, a 1.5 kΩ/25 µF cathode, and the **0.01 µF treble cut
across the plate load** → a two-knob tone stack (100 kΩ slope, a 390 pF treble
cap, 250 kΩ Treble and Bass, 8.2 kΩ foot) with a **DEEP** switch that grounds a
further 0.1 µF at the foot of the ladder → a 1 MΩ Volume → a second 12AX7 stage
(100 kΩ plate, 1.5 kΩ cathode).

**Normal channel.** The same front end without the plate-load capacitor, a
250 pF treble cap, a 0.047 µF middle-leg cap and a 6.8 kΩ foot, and a
**BRIGHT** switch that bridges 120 pF from the volume pot's top lug to its
wiper. Then its own second 12AX7 stage, identical part for part to the bass
channel's.

**Mixer.** Both second-stage plates reach one node through **220 kΩ each**, and
that node is coupled by 0.01 µF into a third 12AX7 (100 kΩ plate, 1.5 kΩ
cathode, 470 kΩ grid leak) whose plate is returned to the same node through
**470 kΩ**. Mixing before the driver, rather than at the inverter's grid, is
what lets one blend control sit ahead of a single gain stage.

**Phase inverter and output.** A 12AT7 **long-tailed pair** with two 100 kΩ 5 %
plate loads, a 470 Ω cathode resistor to a tail junction, a 22 kΩ tail to
ground bypassed by 0.1 µF, and both 1 MΩ grid leaks returned to that junction.
Its cold grid is tied to ground for AC; the **47 kΩ negative-feedback resistor
comes back from the speaker line into the hot grid** through a 0.1 µF capacitor,
mixing with the signal rather than entering at the tail.

Each inverter plate also carries a **220 kΩ straight back to the output tube it
drives** — local feedback wrapped around the coupling capacitor and the output
stage. It is the AB165's signature and the part most often removed by people
converting these heads to the earlier AA864 arrangement. It is not cosmetic: it
sets the inverter's operating point as much as its plate loads do. With the two
220 kΩ resistors in place the simulated inverter cathode sits at **+101.7 V**
against a printed **+102 V**; without them the same stage cannot reach much
past +67 V. That agreement is the strongest single check on this reading of the
sheet.

The **6L6GC pair** is fixed-biased at **−45 V** through 220 kΩ 5 % leaks and
1500 Ω stoppers, with 470 Ω · 1 W screen resistors and grounded cathodes. The
bias line is trimmed by a **10 kΩ-L balance control** — the sheet's "hum
balance", the one the notice tells you to reset when you fit new bottles — with
10 kΩ to each end and 15 kΩ to ground. Simulated idle is about **37 mA per
plate at +425 V**, near 16 W, a little over half the 6L6GC's rating.

## Power

320-0-320 V (TR1 125P7D; 125P7DX on the export model) → three series silicon
diodes per leg → **+425 V** across two 70 µF · 350 V cans in series with 220 kΩ
· 1 W balancing → standby switch → the 125C1A choke → **+425 V** at the screens
→ 1 kΩ · 1 W → **+415 V** at the inverter → 4.7 kΩ · 1 W → **+390 V** at the
second stages and the driver → 27 kΩ · 1 W → **+320 V** at the two channel
inputs. The netlist drives only the first of those and solves the rest through
the drawing's own droppers, so the printed ladder is a checked claim: +415 and
+390 land within half a percent of print, +320 within five.

A separate negative supply — 470 Ω · 1 W off the HT winding, a silicon diode
and two filter cans — feeds the bias divider.

## Reading against the printed chart

The drawing prints a full voltage chart at ±20 %, read to ground with an
electronic voltmeter. Most of it verifies closely: the supply ladder, the
screens at +425 V, the bias line at −45 V, the inverter's **+102 V / +100 V**
cathode and tail, the driver at **+250 V / +2.0 V**, the normal channel's second
stage at **+260 V / +1.9 V**, and the bass channel's input stage at
**+220 V / +1.6 V**. The worst gated nodes are the two inverter plates, which
simulate about 263 V against a printed +225 V and +220 V — inside the sheet's
own ±20 %, but only just, and the two printed plate values differ by 5 V on
plate loads the drawing gives as identical 100 kΩ 5 % parts.

**Two printed plate voltages are reported rather than compared**, because each
contradicts the drawing's own numbers rather than this simulation's:

- **The normal channel's input plate, printed +280 V.** V2a is V1a's twin —
  100 kΩ plate load, 1.5 kΩ cathode, both hung on the same +320 V rail — but
  the chart prints +220 V / +1.6 V on one and +280 V / +1.9 V on the other. The
  pair moves the wrong way against itself: the higher cathode voltage is more
  current (1.9 V over 1.5 kΩ is 1.27 mA against 1.07 mA), and more current
  through the same 100 kΩ has to leave a *lower* plate, near +193 V — never
  +280 V.

- **The bass channel's second-stage plate, printed +260 V.** Here the
  contradiction is in the wiring. The sheet takes this stage's 100 kΩ load down
  to the **+320 V** rail — its corner turns back along that rail, and the
  +390 V line below it is a separate wire, the one the normal channel's
  identical second stage branches from. On +320 V the printed +1.8 V cathode
  gives 1.2 mA and a +200 V plate; the printed +260 V would need 0.6 mA, which
  over 1.5 kΩ is +0.9 V, not +1.8 V. On **+390 V** the same parts give +268 V —
  the value the chart prints, and the value it also prints for the normal
  channel's second stage. The likeliest reading is a drafting slip in the rail
  routing, but this corpus documents the drawing as drawn: the netlist keeps
  the load on +320 V, and the printed +260 V is carried as a disputed node with
  the arithmetic above rather than quietly rewired to make it fit.

Everything else in the chart is gated at the sheet's own ±20 % convention.

## Lineage

The AB165's ancestors — the blonde 6G6-B and the blackface AA864 that first
carried the Bassman name onto a piggyback chassis — are not yet documented
circuits here, so this entry records no lineage edge. Whatever it inherited, it
did not inherit from the tweed Bassman: the [5F6-A](/amps/5f6a/) shares the
name and nothing in this schematic.
