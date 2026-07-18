# Calibrating the 12AX7: which datasheet do you believe?

*A metrology study behind the Circuit Codex tube models.*

The 12AX7 is the most-used small-signal triode in guitar amplification — it is the
gain stage, the cathode follower, and the phase inverter in nearly every circuit in
this archive. So when our SPICE model of it mispredicts a stage by a third, that is
worth chasing to the bottom. This is the write-up of that chase. The short version:
the tube's published data is remarkably consistent across four manufacturers and two
continents — *except* for one chart, which turns out to be the odd one out; and the
amplifier voltage chart that started the whole investigation is itself partly to
blame.

## Background: what the model has to do

Circuit Codex ships a SPICE model for each tube, fitted to the tube's published
"average characteristics" and dedicated to the public domain. The model form is the
Koren equation (a standard, non-proprietary triode expression); the *numbers* in it
are fitted here from datasheet facts, never copied from another model collection.
The method is described in [`models/METHODOLOGY.md`](https://github.com/TheAnalogMaker/circuit-codex/blob/main/models/METHODOLOGY.md).

The original models are **single-anchor fits**: each triode's parameters are solved
so the model reproduces exactly *one* published operating point — for the 12AX7, the
classic **Va = 250 V, Vg = −2 V → Ia = 1.2 mA, gm = 1600 µmho** point. That is enough
to verify a stage whose plate sits near 250 V, but a 12AX7 gain stage in a tweed amp
often runs its plate down at 140–190 V, far below the anchor, and there the model
was under-reading plate current badly. On the [5F4](/amps/5f4/) the
affected nodes deviate from the printed factory chart by up to ~39 %.

The obvious fix — trace the datasheet's full plate-characteristic curve family and
least-squares fit the whole thing — ran into a metrology problem, which is the
subject of this study.

## The finding that stopped the curve fit

RCA's own 12AX7-A datasheet disagrees with itself. On page 1 it prints a table of
typical operation; on page 3 it prints an "average plate characteristics" graph
(drawing no. **92CM-6879**). Read the graph at the same point the table describes —
Va = 250 V, Vg = −2 V — and it gives a plate current well below **1 mA**, roughly
half the **1.2 mA** the table on page 1 states.

Half is not a rounding error. Fitting a model to the graph would move every 12AX7
stage in the corpus in the *wrong* direction relative to the factory amplifier
charts. Before fitting anything, we needed to know which of RCA's two numbers is
correct — and that meant going to other manufacturers.

Sources (all datasheets via [Frank Philipse's tube-data archive](https://frank.pocnet.net/)):

- RCA 12AX7-A — [`/sheets/049/1/12AX7A.pdf`](https://frank.pocnet.net/sheets/049/1/12AX7A.pdf) (Radio Corporation of America, Harrison NJ, "Data 1, 10-60")
- General Electric 12AX7 — [`/sheets/093/1/12AX7.pdf`](https://frank.pocnet.net/sheets/093/1/12AX7.pdf) (ET-T509B, 6-53)
- Sylvania 12AX7 — [`/sheets/137/1/12AX7.pdf`](https://frank.pocnet.net/sheets/137/1/12AX7.pdf) (Engineering Data Service, September 1955)
- Philips / Mullard ECC83 — [`/sheets/030/e/ECC83.pdf`](https://frank.pocnet.net/sheets/030/e/ECC83.pdf) (Philips, 5-5-1960)

(The RCA sheet is filed on the archive under folder 049 and the GE sheet under 093;
each PDF's own letterhead is the authority for its provenance, and that is what is
cited here.)

## What the tables say

Every manufacturer prints the *same* two-point "Class A₁ amplifier, each section"
typical operation. These are printed numeric values, exact as read:

| Source | @ Va=100 V, Vg=−1 V | @ Va=250 V, Vg=−2 V |
|---|---|---|
| RCA 12AX7-A (049) | 0.5 mA · 1250 µmho · rp 80 kΩ · µ 100 | 1.2 mA · 1600 µmho · rp 62.5 kΩ · µ 100 |
| GE 12AX7 (093) | 0.5 mA · 1250 µmho · rp 80 kΩ · µ 100 | 1.2 mA · 1600 µmho · rp 62.5 kΩ · µ 100 |
| Sylvania 12AX7 (137) | 0.5 mA · 1250 µmho · rp 80 kΩ · µ 100 | 1.2 mA · 1600 µmho · rp 62.5 kΩ · µ 100 |
| Philips/Mullard ECC83 (030) | 0.5 mA · 1.25 mA/V · rp 80 kΩ · µ 100 | 1.2 mA · 1.6 mA/V · rp 62.5 kΩ · µ 100 |

Four independent data departments, over seven years (1953–1960), agree to the last
digit — including a **second operating point at 100 V** that the RCA table also
carries. That second point is the prize: it is a published, low-plate-voltage fact
about the tube, exactly in the regime where our model was failing, and it does not
come from any amplifier chart.

The tables are also internally consistent: amplification factor µ = gm × rp holds at
both points (1250 µmho × 80 kΩ = 100; 1600 µmho × 62.5 kΩ = 100). Nothing in the
tabulated data is in tension.

## Which chart is the outlier

To decide whether the RCA **92CM-6879** plate graph or the tabulated 1.2 mA is
correct, three independent lines of evidence all point the same way.

**1. RCA's *other* graph agrees with the table.** The same RCA sheet prints, on
page 4, an "average characteristics" graph (drawing **92CM-6880**) of rp, gm and µ
against grid voltage at Eb = 100, 200 and 300 V. Read at Eb = 100 V, Vg = −1 V it
gives rp ≈ 0.080 MΩ, gm ≈ 1250 µmho, µ ≈ 100 (read precision ≈ ±0.005 MΩ / ±100 µmho)
— matching the table. Only the 92CM-6879 *plate* graph on page 3 is out of step, and
only in one direction.

**2. GE drew its own curves, and they match the table.** GE's sheet (093) contains
two independently drawn graphs in conventional orientation (Ef = 12.6 V): an average
plate-characteristics family (Ia vs Va) and an average transfer family (Ia vs Vg at
Eb = 50…300 V). Both are legible and both confirm the table (read precision ≈ ±0.1 mA):

| GE graph read | value | tabulated |
|---|---|---|
| Plate family, Vg = −2.0 V curve at Va = 250 V | ≈ 1.2–1.3 mA | 1.2 mA |
| Transfer family, Eb = 250 V curve at Vg = −2 V | ≈ 1.2–1.3 mA | 1.2 mA |
| Transfer family, Eb = 100 V curve at Vg = −1 V | ≈ 0.5 mA | 0.5 mA |

GE's plate-characteristics graph is the *same kind of chart* as RCA's 92CM-6879, drawn
by a different manufacturer, and it lands on 1.2 mA where RCA's lands near 0.6 mA. That
is as clean a cross-check as this kind of question allows.

**3. Real resistance-coupled operating points agree with the table.** Philips' ECC83
sheet prints measured resistance-coupled amplifier tables — actual DC operating points
for a stage with a plate-load resistor and cathode bias. For the 100 kΩ-load table,
each row's implied plate voltage (Vb − Ia·Ra) and grid bias (−Ia·Rk) give a low-plate
operating point, exactly the 5F4's regime:

| Vb | Rk | Ia (measured) | implied Vp | implied Vg |
|---|---|---|---|---|
| 200 V | 1800 Ω | 0.65 mA | 135 V | −1.17 V |
| 250 V | 1500 Ω | 0.86 mA | 164 V | −1.29 V |
| 300 V | 1200 Ω | 1.11 mA | 189 V | −1.33 V |
| 350 V | 1000 Ω | 1.40 mA | 210 V | −1.41 V |
| 400 V | 820 Ω | 1.72 mA | 228 V | −1.41 V |

These currents are consistent with the tabulated behaviour and far above what the
92CM-6879 plate family would predict at the same voltages.

**Verdict:** the tabulated **1.2 mA / 0.5 mA** two-point data is correct, corroborated
by four tables, three independently drawn graphs, and one set of measured
resistance-coupled points. The RCA **92CM-6879** plate-characteristics graph is the
lone outlier — a drafting artefact on one sheet, not a fact about the tube — and it is
deliberately **not** used for calibration. (Reading that graph precisely is also
hampered by its rotated axes and coarse scan; there is no need to rely on the exact
figure, only on the fact that it sits well below every other source.)

## The recalibration recipe

With a trustworthy second point in hand, the fix is a **two-point fit** rather than a
single-anchor solve. Keeping the tube's amplification factor (µ = 100) and the
space-charge exponent (EX = 1.5, the 3/2-power law) fixed as before, the fit now frees
three parameters — KP, KG1 and the knee term KVB — and solves them so the model
reproduces:

- plate current at **both** tabulated points (0.5 mA at 100 V/−1 V *and* 1.2 mA at
  250 V/−2 V), and
- transconductance at the 250 V anchor (1600 µmho), the point the model test suite
  checks.

The single freed parameter compared with the original models is KVB: in the
single-anchor fit it was a fixed default with negligible effect near 250 V, but it is
precisely the term that shapes how current falls away at low plate voltage, so it must
be free to honour the 100 V point. The fit is a small deterministic Nelder-Mead solve
in the existing pure-Python pipeline; it never touches the disputed plate graph or any
amplifier chart (calibrating to the amp charts we later verify against would be
circular).

Resulting parameters (12AX7, one section):

| | µ | EX | KP | KG1 | KVB |
|---|---|---|---|---|---|
| single-anchor | 100 | 1.5 | 373.2 | 555.5 | 300 |
| two-point | 100 | 1.5 | 679.8 | 658.0 | 25 690.8 |

How the two models compare against the datasheet and against the independent Philips
resistance-coupled points (which were *not* used in the fit):

| Test point | tabulated / measured | single-anchor | two-point |
|---|---|---|---|
| Ia @ 250 V, −2 V | 1.2 mA | 1.20 mA (0 %) | 1.20 mA (0 %) |
| gm @ 250 V, −2 V | 1600 µmho | 1600 (0 %) | 1600 (0 %) |
| Ia @ 100 V, −1 V | 0.5 mA | 0.15 mA (**−69 %**) | 0.50 mA (0 %) |
| gm @ 100 V, −1 V | 1250 µmho | 601 (−52 %) | 800 (−36 %) |
| Ia @ Vp 135 V (Philips) | 0.65 mA | 0.39 mA (−41 %) | 0.72 mA (+10 %) |
| Ia @ Vp 164 V (Philips) | 0.86 mA | 0.67 mA (−22 %) | 0.95 mA (+10 %) |
| Ia @ Vp 189 V (Philips) | 1.11 mA | 1.07 mA (−4 %) | 1.27 mA (+14 %) |

The recalibration does exactly what it was meant to: it removes the large systematic
*under-read* at low plate voltage. It does not make everything perfect — the two-point
fit slightly over-reads current in the 160–190 V band, and its transconductance at
100 V is still low (an inherent limit of a single-exponent triode expression, which
cannot match plate current *and* transconductance at two widely separated voltages at
once). But for DC operating-point work — what this archive verifies — it is a clearly
better description of the tube.

## What it does to the amplifiers

Rebuilding the model and re-simulating every circuit shows the recalibration helping
where the model was genuinely wrong — the low-plate gain stages — and drifting
slightly on stages that were already accurate. No circuit that passed before fails
after; the automated voltage checks stay green.

| Circuit · node | printed chart | single-anchor | two-point |
|---|---|---|---|
| 5F1 · V1 plate (P1A) | 150 V | 171.6 V (14.4 %) | 163.9 V (**9.2 %**) |
| 5E1 · V1 plate (P1A) | 150 V | 178.7 V (19.1 %) | 172.1 V (**14.7 %**) |
| 5F2-A · V1 plate (P1B) | 170 V | 178.4 V (5.0 %) | 171.4 V (**0.8 %**) |
| 5F6-A · V2 plate (P2A) | 180 V | 185.7 V (3.2 %) | 181.6 V (**0.9 %**) |
| 5E3 · V2 plate (P2A) | 167 V | 159.6 V (4.4 %) | 151.5 V (9.3 %) |
| 5F10 · V2 plate (P2A) | 170 V | 164.5 V (3.2 %) | 156.8 V (7.8 %) |

Averaged over every chart-valued node in the corpus, mean deviation moves from 8.2 %
to 7.9 % — a modest net improvement that understates the real story, which is a large
improvement on the worst (lowest-voltage) stages traded against small drift on stages
that were already within a few percent.

## The amplifier chart that cannot be satisfied

The investigation began with the 5F4, whose second gain stage deviates ~37 %. The
recalibration barely moves it (37.1 % → 34.0 %), and that is the most instructive
result in the study, because it shows the 5F4 deviation was never mainly a *model*
problem.

The 5F4's printed factory chart shows its V2A stage at a **plate of 140 V** with a
**cathode of 2.2 V**. A 2.2 V cathode across the stage's 1.5 kΩ cathode resistor means
1.47 mA of plate current. But a 12AX7 biased at Vg = −2.2 V is essentially at cutoff at
Vp = 140 V — at that grid voltage the tube needs roughly **280 V** on the plate to pass
1.47 mA. The chart's plate voltage and its cathode voltage cannot both be true for a
12AX7: they describe two different operating points.

The self-consistent operating point for that stage — 100 kΩ plate load from ~280 V,
1.5 kΩ cathode bias — sits near **190 V**, which is what both the old and new models
produce, and which the Philips resistance-coupled data independently supports (at
Vp ≈ 189 V the tube passes ~1.1 mA; the single-anchor model is only −4 % off there).
The 5F4's phase-inverter nodes are inconsistent in the same way, as its
[circuit notes](/amps/5f4/) already record. No physically valid 12AX7
model can reproduce those printed numbers, because the printed numbers do not describe
a physically valid operating point. Those chart values should be treated as
**disputed**, the way the JTM45's phase-inverter cathode reading already is — not
chased with model parameters.

## Status

The recalibrated 12AX7 model is **not adopted as the shipping standard on the strength
of the 5F4 alone.** The adoption bar for this change was that the 5F4's worst 12AX7
stage improve materially with no regressions; the 5F4's worst nodes are its
phase-inverter, whose printed chart is internally inconsistent, so they cannot improve
and in fact drift slightly. The bar is not met, and the honest conclusion is that the
5F4 page needs its disputed nodes marked, not a model tuned to hit impossible targets.

The recipe and data themselves are sound, and the two-point fit is the correct
calibration of the tube. Whether to adopt it corpus-wide is a separate decision, to be
judged on overall accuracy across every circuit rather than on the 5F4 — a decision
this study hands over with the evidence laid out. Until then the single-anchor models
remain the standard, with the documented caveat that they under-read plate current
below ~200 V.

---

*Sources are linked inline. Datasheet graph values are stated with their read
precision; tabulated values are exact as printed. No factory drawings are reproduced
here — only facts read from them. Models and pipeline are CC0; see
[`models/METHODOLOGY.md`](https://github.com/TheAnalogMaker/circuit-codex/blob/main/models/METHODOLOGY.md).*
