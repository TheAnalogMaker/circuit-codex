# B-15N — Ampeg B-15N Portaflex-style

The Portaflex is the amplifier that solved a carrying problem. Its chassis hangs
upside-down from the lid of the cabinet, so the whole amplifier folds away
inside the box it plays through. Ampeg introduced the idea in 1960 as the 25-watt
B-15; the **B-15N** replaced it in 1961 and gave the line its name. The circuit
documented here is the one Ampeg's own drawing carries: two identical channels
of two **6SL7** stages each, a third 6SL7 that both drives and inverts, and a
push-pull pair of **6L6GC** beam power tubes under fixed bias, with global
negative feedback taken from the speaker winding.

Three things make it worth documenting. It is an all-octal front end at a date
when nearly everyone else had gone noval. Its phase inverter is a
**self-balancing paraphase** built from two resistors strung across the driver's
own plates. And its published voltage annotations contain a contradiction that
this entry records rather than resolves.

## What the title block actually says

The sheet reads **B-15-N / U.S. PATENT 3183305 / TUBES / 6SL7 - 6SL7 - 6SL7 -
6L6GC - 6L6GC - 5AR4 / -472-**, drawn *BY S.C.*, sheet 1268, PART NO. 591722,
revision **C** — the revision block dating that issue **1/22/74**, part
591722-2, over a **B** issue, part 591722-1.

That matters twice over. First, it settles the valve complement from the
factory's own hand: no Portaflex drawing in Ampeg's published schematic library
specifies **7591** output tubes. The B-15N, B-15NC and B-15NF sheets all print
6L6GC and the B-15S prints 7027A; the 7591 belongs to Ampeg's guitar amplifiers
of the same years, not to the Portaflex. Second, it dates what is drawn. The
model left the catalogue in 1964 and this issue is from **1974** — it documents
the B-15N circuit as Ampeg last issued it, not necessarily as the first 1961
chassis left the bench. The era bracket on this entry is the model's production
window; the component values are revision C's.

## Reading the sheet: the hop-overs

Three connections on this sheet cannot be read until one drafting convention
is recognised — a convention, not a circuit question. A
long horizontal ground bus runs across the middle of the drawing, and several
vertical lines cross it. At working magnification each crossing looks like a
junction. At 400 dpi, zoomed to the pixel, each is a **hop-over** — the small
S-jog this draughtsman used for *crosses, does not connect*. The same jog turns
up again where the channel mixing resistors cross their own tone-board input
lines, where the driver rail crosses four horizontals on its way down to the
power supply, and where the output-transformer centre tap crosses the bias line.

Read as junctions, the supply is unsolvable and half the tone stack is shorted.
Read as hop-overs, the sheet resolves cleanly and the arithmetic closes: eight
preamp nodes and the screen node all land inside the era's ±20 %, and the
screen dropper's own current comes out where the drawing's two printed figures
say it should (below).

## Circuit walkthrough

**The two channels are identical, part for part.** Each has a BRIGHT jack
through 100 kΩ (bridged by 0.005 µF) and a NORMAL jack through 47 kΩ, both
landing on one grid behind a **5.6 MΩ** leak — an unusually high value, and one
the very light loading of that pair of series resistors asks for. The first
6SL7 section runs a 470 kΩ plate load over an **unbypassed** 5.6 kΩ cathode; the
second runs 220 kΩ over an unbypassed 2.2 kΩ. There is no cathode bypass can
anywhere in either channel. That is a quiet, low-gain, heavily degenerated front
end, which is what a bass amplifier with a 5.6 MΩ input wants.

**ULTRA HI and ULTRA LO** are not tone controls; they are two switches per
channel that reshape the stage between them. Off the first plate, a 0.1 µF
coupler reaches a node carrying a 0.02 µF capacitor in series with 39 kΩ down to
a 1 MΩ resistor to ground. **ULTRA LO** shorts that 1 MΩ out, dropping the shunt
leg to the bare 39 kΩ and pulling the top end down. From the same node a 0.01 µF
coupler carries on to a 1 MΩ **linear** volume control, and **ULTRA HI**
switches a 500 pF capacitor from the top of that pot to its wiper — a bright cap
on a switch rather than soldered in. The service sheet's own AC measurement note
tells you these are level-shifting: it asks for the readings with "ultra hi and
ultra lo switches off", and footnotes pin 1 of V1 and V2 with three different
figures for three combinations of the two switches.

**The tone board** is a printed assembly — the drawing rings each one in a
dashed outline and letters it *P.E.C. NO*; the channel-2 board reads 250762-1
and the channel-1 number is smudged on the published scan. Its input is the
second stage's 0.1 µF coupler. From there 220 kΩ feeds the top of a 1 MΩ bass
pot whose foot sits on 22 kΩ to ground, with **0.001 µF from the pot's top lug
to its wiper and 0.01 µF from its bottom lug to the same wiper** — the wiper
therefore sees a frequency-dependent blend of the two ends rather than a plain
tap. In parallel, 470 pF from the board input feeds the top of a 1 MΩ treble pot
whose foot goes to ground through 0.0047 µF. The two wipers are tied together
through 120 kΩ, and that link *is* the board's output. It is a compact,
interactive bass-and-treble network with no middle control and no slope
resistor, and each channel carries its own.

Each board's output leaves through a **270 kΩ mixing resistor**; the two meet at
the driver's grid, where the EXT. AMP. jack also taps in. That mixing node has
no grid leak of its own — its DC return runs back out through both channels'
270 kΩ, each board's 120 kΩ link and bass pot, to the 22 kΩ foot.

**The driver and the paraphase.** V3's two sections are asymmetric on purpose.
Unit 2 (pins 1/2/3) takes the mixed signal on a 120 kΩ plate load over a
**220 Ω** cathode resistor; unit 1 (pins 4/5/6) has the same 120 kΩ load but a
1 kΩ cathode bypassed by 25 µF. What makes it an inverter is the pair strung
*across* the two plates: **R28 470 kΩ and R29 510 kΩ in series between them**,
their midpoint coupled by 0.022 µF to unit 1's grid, which returns to ground
through 470 kΩ. The two plates swing in antiphase, so that midpoint carries only
the residual — and any imbalance in the pair's gain shifts the residual in the
direction that corrects it. This is the **self-balancing (floating) paraphase**,
the arrangement most American makers had abandoned for the long-tailed pair by
1960. The two cathodes here are separate and differently loaded, which is what
tells you at a glance it is not an LTP.

The 220 Ω on unit 2's cathode is not really a bias resistor. It is the shunt leg
of the **global feedback divider**: R40 10 kΩ returns from the output
transformer's green secondary lead into that same node. Feedback lands on the
driver, not on a phase-inverter tail.

**Output.** Two 0.022 µF couplers carry the two plates to two grid lines. Each
grid line has a **270 kΩ return to a −50 V bias line** and a **1 kΩ stopper**
into the bottle; both 6L6GC cathodes go **straight to ground**. There are no
screen stoppers at all — both screens tie together onto one supply node. That is
about as plain as a fixed-bias push-pull output stage gets.

## The supply, and the one figure that proves the reading

The 5AR4's cathode carries a 30 µF · 600 V reservoir and is also the OT-214
primary's centre tap, so it is the plate node: the drawing annotates **450 V**
there. From it a **1 kΩ · 10 W** resistor feeds the screen node, annotated
**445 V**. Off that screen node two **22 kΩ · 1 W** resistors leave and never
rejoin — the sheet's hop-overs put each on its own horizontal — one feeding the
preamp rail both channels share, the other the driver rail behind R26 and R27.
Each of those three nodes carries a 40 µF · 500 V section of the C16 can.

The 5 V the drawing puts between plates and screens is the whole check on that
reading. Five volts across 1 kΩ is 5 mA, which is what a 6L6GC pair idles at for
screen current; the simulation, built from the drawn values and driven only at
the 450 V the sheet prints, lands the screen node at 442 V and the pair at about
29 mA of plate current each — 13 W in a 30 W plate, a sane fixed-bias idle. Two
independent facts, the drawing's annotation and the tube's own data sheet, agree
about a node neither was used to derive.

## Why the preamp plates simulate high

Every preamp plate simulates roughly 10 % above its printed figure, always in
the same direction, and the sheet says why. Note 3 reads *"VOLTAGE READINGS ARE
D.C. TAKEN WITH NO SIGNAL INSERTED USING A 20,000 Ω/VOLT METER"*. On its 250 V
range that instrument is a 5 MΩ load hung on whatever node it reads. Across the
first stage's 470 kΩ plate load the meter's own 36 µA adds about 17 V of extra
drop, turning a 181 V node into a ~164 V reading — the sheet prints 165 V. The
second stage's 220 kΩ load gives about 8 V of the same effect: 187 V simulated,
~179 V read, 175 V printed. The corpus simulates the circuit and not the
instrument, so the meter is not modelled; it is simply why a +10 % deviation
here is the expected sign and size.

## What this sheet still does not settle

**The driver's four printed voltages cannot all be true.** Ampeg annotates 235 V
and 3 V at unit 2's plate and cathode, and 225 V and 2.2 V at unit 1's. Both
cathode figures fail arithmetic that needs no simulator:

* **3 V across 220 Ω is 13.6 mA.** A 6SL7 section is a 1 W, 300 V small-signal
  triode whose own data sheet gives 2.3 mA at its Class-A point. 13.6 mA at the
  printed 235 V plate is 3.2 W in a 1 W plate — and it would need 1636 V behind
  the drawn 120 kΩ load to deliver. Meter loading cannot explain it either: a
  20,000 Ω/V meter reads *low*, never high, and the resistor is not in doubt —
  the sheet letters it plainly *R25 220 Ω*.
* **2.2 V across 1 kΩ is 2.2 mA**, and 2.2 mA through 120 kΩ is a 264 V drop, so
  the 225 V printed above it needs a 489 V supply. The highest node in this
  amplifier is the 450 V reservoir, and the driver rail sits below it behind
  22 kΩ.

Three of the four figures are therefore carried as **disputed** nodes with
that arithmetic written down, and none of the three is gated: both cathodes,
and unit 2's 235 V plate — the other half of the same impossible pair, since
its printed plate and printed cathode are two statements about one current
that disagree by more than a factor of ten. Unit 1's plate is the one figure
of the four the drawn parts can reach, and it is gated normally: its 225 V
lands inside the era's ±20 %. The other three stand in the table as the
sheet's own contradiction, shown for the record instead of tuned away or
flattered by an invented supply reading.

**The negative-bias supply is an AC-fed half-wave block, and the sheet does say
so.** Every part in it is legible — D1 lettered *F-4*, R34 47 kΩ, R35 56 kΩ,
R36 100 kΩ · 2 W, R42 10 kΩ, and two 10 µF · 100 V cans whose polarity marks put
the bias line negative with respect to the bottom rail. The corner where R36
leaves the rectifier block is the one place the block's feed is easy to
misread as tapping a DC node too positive for the diode ahead of it to
conduct. Read at the pixel, on both sheets, that corner resolves: the
line from R36 drops past the two yellow 5 V leads — **hopping over both**, in
the same S-jog convention the rest of the drawing uses — and joins the red HT
lead at **V6 pin 4, the 5AR4's own plate**. That is not a DC node. A rectifier
plate swings to roughly −450 V on the half cycle its own diode is not
conducting, and D1 faces it cathode-first, so on that half cycle D1 conducts
*toward* the bias line and charges the two cans negative. R35 sits on the
rectifier side of D1 and R34 on the bias side; R42 separates the two cans. It is
the ordinary Fender-style negative-bias tap, drawn off the rectifier plate
rather than off a dedicated winding.

The −50 V line is still **driven at the value the sheet prints** in the
simulated deck, exactly as the 450 V reservoir is: no deck in this corpus
simulates a supply, and an AC-fed half-wave rectifier has no place in a DC
operating-point model. The exclusion is a matter of scope, not doubt — and
the schematic draws the block whole.

## Two things about the drawing itself

**The sheet letters three different capacitors C19.** Channel 1's 0.01 µF
coupler into the volume pot, a 10 µF · 100 V electrolytic in the bias supply,
and one of the two 0.047 µF · 600 V capacitors across the mains switching all
carry that number. The parts list keeps C19 for the first of them in reading
order and lists the other two as CBF2 and CM2, each naming the collision. A
parts list cannot carry one designator three times, and silently renumbering a
factory sheet would hide something a builder holding the drawing needs to know.

**Twelve parts are drawn with a value and no designator at all** — the six
inside each printed tone board — even though the 120 kΩ link and both pots
inside the same dashed outline are lettered. The driver's 25 µF · 25 V cathode
bypass is unlettered too. Those thirteen carry role codes here, which is why
this amp's parts list reads as a functional one although most of it is the
factory's own sequential numbering. The three-section 40 µF · 500 V can the
sheet rings and letters **C16** is listed as C16A, C16B and C16C for the same
reason: its sections sit on three different nodes — the screen node, the preamp
rail and the driver rail — and one designator cannot be carried on three.

**The pilot is a mains-side lamp, not a heater-chain bulb.** The sheet draws
*P.L.* straight across the power transformer's mains primary, downstream of the
POWER switch and quite separate from the 6.3 V green winding, which serves the
five heaters and the VR7 hum balance and nothing else. It gives no lamp type or
rating, so none is claimed; the board layout draws the pilot as the panel item
it is and gives it no lead, because that side of the circuit is outside the
drawing's scope.

## The second sheet

Ampeg's service manual prints the same circuit as *MODEL B15N SCHEMATIC DIAGRAM
(REV. C)*, and the two sheets agree on every component value and every DC
annotation. The manual adds notes the engineering sheet does not — capacitors
"in microfarads, 10%, 400V", resistors "1/2 W, 10%, composition", and a fourth
note warning that the "actual circuit may vary slightly due to normal production
changes" — along with an **A.C. VOLTAGE MEASUREMENTS** table taken at
"INPUT: .3V A.C. 400/cps" for "OUTPUT: 11V A.C. across 8 ohms load", with the
bass and treble controls at mid and both ULTRA switches off. Only its first two
rows survive the page trim on the published scan: V1 and V2 read .65 V on pin 1,
19 V on pin 2, .29 V on pin 4 and 6.5 V on pin 5, with pins 7 and 8 marked
*Fil.* The rest of the table is below the trim and is not claimed here.

Where the two sheets *do* differ is the bias corner: the engineering sheet
carries R42 10 kΩ and a second 10 µF · 100 V can that the manual sheet does not
draw, and the manual's single bias can reads 100 µF · 100 V where the
engineering sheet's reads 10 µF. That is the ordinary difference between two
printings of one revision, and it is recorded rather than averaged.

## Sources

Both sheets are Ampeg's own published schematics, and neither is reproduced
here. The title-block transcriptions, the links and the full value reading are
listed under Sources on this page; the line's chronology and its other
revisions — B-15NB, B-15NC, B-15NF, B-15S and the 1997 reissue — are on the
Portaflex family page.
