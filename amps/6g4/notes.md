# 6G4 — Brown Super-style

Fender's brown-Tolex remake of the Super, the two-10-inch step above the
Deluxe. Production ran 1960–1963 on the 6G4 chassis documented here, a
40-watt combo running a fixed-biased **6L6GC** pair off a **GZ34** rectifier,
before the 6G4-A revision swapped in a 5881 output pair and before the name
passed to the blackface Super Reverb. Where the tweed [5F4](/amps/5f4/) it
replaces cathode-biased its 6L6G pair through a selenium-assisted bias
network and a cathode-follower-fed tone stack, the 6G4 moves to a proper
fixed-bias supply, a long-tailed-pair inverter, and adds vibrato — the same
recipe the brown [6G3](/amps/6g3/) Deluxe carries at smaller scale. The
preamp/PI bottles are marked **7025** on the drawing, the low-noise selected
version of the 12AX7.

## Two mirrored channels

Each channel runs the same recipe, wired independently rather than sharing a
tone stack: two inputs (68 kΩ stoppers merged into a 1 MΩ leak, no coupling
cap — the jack-merge node is the first stage's grid directly) → a 7025 input
stage (100 kΩ plate, 1.5 kΩ cathode) off the shared +170 V input-stage rail →
a Bass/Treble two-knob tone ladder (250 pF treble cap, 100 kΩ slope, a 10 kΩ
bleed) → a Volume pot → a second 7025 recovery stage (100 kΩ plate, 820 Ω
cathode) → a mixing resistor into the phase inverter. The two channels'
recovery stages sit on **different** rails, though — channel 1's plate prints
+160 V and channel 2's +120 V — so this circuit, unlike its siblings, is not
simulated as perfectly symmetric between channels; each recovery rail is
modeled at its own printed value (see netlist.cir).

The drawing does not print channel names (unlike the following 6G4-A
revision, whose otherwise near-identical drawing labels its two channels
"VIBRATO" and "NORMAL"); this entry follows the 6G4's own drawing and does
not assert a name for either channel.

## Phase inverter and output

A 7025 **long-tailed pair** (82 kΩ hot / 100 kΩ cold 5% plate loads off a
supply derived through the drawing's own 10 kΩ dropper from the 6L6GC plate
rail, an 820 Ω shared cathode resistor to a 6.8 kΩ tail, both 1 MΩ grid
leaks returned to the tail junction) drives the **6L6GC pair**, fixed-biased
at **−55 V** through 220 kΩ · 5% leaks, with 470 Ω · 1 W screen resistors.
Presence is a 5 kΩ-linear pot and 1.5 kΩ foot resistor carrying a 56 kΩ
negative-feedback return from the speaker line — the identical recipe 6G3
uses, DC-neutral at the tail.

## Tremolo

A phase-shift oscillator (Speed on a 4 MΩ reverse-audio pot feeding a
0.01 µF/0.01 µF ladder into a 7025 grid, with a 4.7 MΩ/0.005 µF feedback
path) drives an **Intensity** control (10 MΩ reverse-audio) that injects
into the **same −55 V fixed-bias line the 6L6GC grids share** — bias-vary
tremolo, the same mechanism 6G3 uses, rather than the optocoupler-shunt
tremolo AB763 carries. The Intensity feed carries no DC (the output grids
draw no grid current), so it moves no operating point.

## Power

The GZ34 delivers **+456 V** at the 6L6GC plates and screens (470 Ω · 1 W
stoppers). A 10 kΩ dropper feeds the phase-inverter supply, landing at the
printed +315 V (hot plate) / +310 V (cold plate) through the 82k/100k plate
loads. A separate rectified/filtered bias tap (56 kΩ + 10 kΩ divider, 8 µF ·
150 V filter) delivers the fixed **−55 V** bias line.

## Reading against the printed chart — and what the scan does not resolve

The drawing prints a full voltage chart directly on the schematic at every
stage (no separate tabulated table), read to ground with an electronic
voltmeter, values shown ± (the companion layout page states the drawing's
usual ±20%). Several of those printed values are gated in voltages.yaml —
the phase-inverter plates (+315 V/+310 V, both within a few percent) and the
fixed-bias/screen nodes (exact by construction, driven or one resistor
away). The **channel input and recovery rails are not gated**: at this
scan's resolution, the drawing's own dropping-resistor chain from the main
6L6GC-plate rail into those three preamp rails was not legibly readable, so
each is instead **calibrated** — driven at whatever value reproduces the
printed *plate* reading through the drawing's own (legibly-read) 100 kΩ
plate loads and the tube's own self-bias. That reproduces the plate voltages
by construction, which is not a verification of them, so voltages.yaml
reports those plate nodes as informational and gates the cathode nodes the
calibration was *not* tuned against instead. The joined phase-inverter
cathode/tail-junction nodes (KPI/JPI) are reported the same way: not legibly
read on this drawing, but landing close to 6G3's own **verified** chart at
the analogous node (which shares the identical 820 Ω/6.8 kΩ tail pair) —
+20.9 V simulated against 6G3's printed +20 V, +18.6 V against +18 V — an
independent cross-check this circuit's own chart could not supply directly.

**The tremolo oscillator** is excluded from the netlist entirely, the same
documented-exclusion pattern 6G3 and AB763 use: it is a running phase-shift
oscillator with no static DC operating point, and unlike those two circuits'
own charts, the 6G4 drawing prints no dynamic-average pin voltage for it at
all, so there is nothing to report even informationally.

**Nine functions, eight bottles.** The published layout page draws exactly five
noval sockets alongside the GZ34 and the two 6L6GCs, so the circuit's nine
preamp/driver/inverter/oscillator functions have to share. They share the way
the 6G3 shares: the tremolo oscillator is the second section of the same bottle
as a channel's recovery stage. Which of the two channels it pairs with is not
legible at this scan's resolution — channel 1 is an editorial choice here, not
a read fact, and it has no bearing on the DC model, which excludes the
oscillator entirely.

**What stands between this circuit and `verified`.** The drawings have landed:
the schematic passes its grammar gate, both board styles render with zero
collision-lint findings, and the drawn wiring is proved electrically equivalent
to the netlist. What remains is the un-gated preamp rails above — a
higher-resolution read of the three dropping resistors would turn three
calibrated rails into checked ones — and the maintainer's own review, which is
the only thing that grants `verified` here. A gated node's worst deviation
today (the phase-inverter cold plate, 3.2% against a printed value carrying a
±20% convention) is not what is holding it back.

**Hunting a sharper copy (2026-08-30).** Every mirror found traces back to the
same single 2002 scan pair. `el34world.com`'s two-page schematic+layout PDF
and `schematicheaven.net`'s copy are byte-identical (209,750 bytes, same
embedded 2179×1437/2250×1269 rasters, `Acrobat 5.0 Image Conversion Plug-in`
CreationDate `2002-01-21`); Prowess Amplifiers' schematic and layout pages
serve the identical rasters (same pixel dimensions, same CreationDate,
same embedded object ID) merely re-saved as single-page PDFs — no new scan.
Two archives turned up only the *following* production revision, 6G4-A
(2× 5881, different preamp complement — the drawing already excluded per
`meta.yaml`'s disambiguation source): `thetubestore.com` and
`schematicheaven.net/fenderamps/super_6g4a_schem.pdf`, matching `kbapps.com`'s
6G4-A page. `elektrotanya.com`'s copy 403s. Two resale sites
(`electronicservicemanuals.com`, `audioservicemanuals.com`) list the 6G4 sheet
behind a paywall with no preview resolution stated; not pursued — a purchased
copy would still need to out-resolve the same public 2002 scan to be worth
anything, and there's no indication it's a different source. `thevintagesound.com`'s
Field Guide mirror was unreachable (connection refused). The `el34world`
forum's own 6G4-build thread links back to `el34world`'s own copy; the
`ampgarage` "editable Fender schematics" thread doesn't carry a 6G4 redraw at
all. Rendering both pages of the source PDF at 300 dpi (a straight upsample of
the same 2179×1437/2250×1269 rasters — no information gain) and inspecting the
region between the main 6L6GC-plate rail and the three preamp-rail takeoffs
confirms the earlier finding rather than merely restating it: on both the
schematic and the companion layout page, no continuous, legible wire run
carrying a resistor value connects the B+ rail to the +170 V/+160 V/+120 V
takeoffs. This isn't a blurry digit on an otherwise-traceable run — the run
itself doesn't resolve at this scan's resolution on either drawing. No
sharper copy of the 6G4 (as opposed to 6G4-A) sheet surfaced anywhere
searched. BD/BE1/BE2 remain calibrated; `verified` still requires either a
sharper original scan than any archive currently mirrors, or the maintainer's
own inspection of a physical unit/better print.
