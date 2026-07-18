# Tube model methodology

How Circuit Codex derives its CC0 tube SPICE models, and why the public-domain
dedication is legitimate.

## The licensing problem these models solve

The widely used tube SPICE model collections (Duncan Amp Pages, Norman Koren's
parameter sets, vendor libraries) are **not** blanket open-licensed — terms are
per-model, embedded in each file. So this project derives its own models from
scratch and dedicates them to the public domain (CC0). Two ingredients make that
clean:

1. **Equations** — we use the Koren model *form* (N. Koren, "Improved vacuum-tube
   models for SPICE simulations", Glass Audio 8(5), 1996). Mathematical methods
   are not copyrightable; we cite the paper as methodology. No Koren *parameter
   values* are used.
2. **Data** — parameters are fitted to tabulated "average characteristics"
   operating points published in tube datasheets (RCA Receiving Tube Manual
   RC-19, 1959). These are facts about the tubes, not creative expression.

Rule for contributors: never copy parameters from an existing model file. Fit
from published curves/tables and document your anchors in the file header.

## Fitting procedure (v0 — anchor-point fits)

Implemented in `pipeline/fit_models.py` (pure Python, deterministic). For each
tube we fix the physically-motivated parameters and solve the remaining ones
exactly against the datasheet anchor:

- `EX = 1.5` — the Child-Langmuir 3/2-power space-charge law exponent.
- `MU` — taken directly from the datasheet amplification factor (for the beam
  power tube, the published grid-1-to-grid-2 mu).
- `KVB` — knee-shaping parameter, set to project defaults (300 V² triodes,
  30 V pentodes). At the anchor region its influence is negligible (for a
  triode at Va=250 V: √(300+250²)/250 = 1.002 — a 0.2 % effect), so it is not
  load-bearing for operating-point verification.
- `KP`, `KG1` (and `KG2`) — solved by bisection so the model reproduces the
  anchor plate current **exactly** and the anchor transconductance through the
  analytic gm/Ia ratio. The rectifier uses a Child's-law diode
  (I = PERV·V^1.5) with perveance fitted to the published tube-drop point.

Every model is then verified in actual ngspice by `pipeline/test_models.py`
(CI gate): anchored currents within 2 %, gm within 5 %.

## Known limitations (v0)

- **Anchor-point fits, not full curve fits.** The models are accurate in the
  neighborhood of the datasheet operating point — which is exactly what the
  corpus's DC operating-point verification needs. Large-signal curve shape
  (deep clipping behavior, knee detail) is approximate.
- No grid-current model; no heater model (rated heater assumed).
- Rectifier model is per-plate and ignores sag interaction beyond the V^1.5 law.

## Roadmap (v1 — curve-traced fits) and the calibration-source finding

The original v1 plan — trace the datasheet plate-characteristic family and
least-squares fit all parameters — hit a real metrology problem when first
attempted (2026-07-18, 12AX7): **RCA's average plate characteristics chart
(92CM-6879) disagrees with RCA's own tabulated typical operation by roughly
2×.** Reading the chart at Va=250 V, Vg=−2 V gives ~0.5–0.85 mA; the tabulated
datasheet point (the v0 anchor) says 1.2 mA. Fender's printed amp voltage
charts side with the tabulated value — measured plate voltages imply tube
currents at or above the tabulated point, never down at the chart-family
level. Fitting v1 to that plate family would therefore make every amp verify
*worse* against the factory charts.

v1 therefore needs a calibration-source decision before any fitting:

1. **gm/rp/µ curves** (92CM-6880: gm vs Vg at Eb=100/200/300) + the tabulated
   point — constrains voltage-dependence without inheriting the plate-family
   offset. Likely the right primary source.
2. Cross-manufacturer plate families (GE/Sylvania/Mullard ECC83) to see
   whether the RCA chart is the outlier.
3. Never calibrate to the amp charts we verify against (circular).

Resolution (2026-07-18): the calibration study (reference/studies/
12ax7-calibration.md) confirmed four-manufacturer unanimity on the tabulated
points and identified the RCA plate graph as the outlier. The **two-point fit
is now the standard for the 12AX7** (both tabulated operating points held;
KP/KG1/KVB fitted, MU/EX fixed). Other tubes remain single-anchor fits until
they justify the same treatment. Known residual: gm at 100 V reads ~36 % low —
an inherent single-exponent Koren limit; plate current is exact at both
points.

## Verifying locally

```
python3 pipeline/fit_models.py   # regenerate models/*.inc (deterministic)
python3 pipeline/test_models.py  # ngspice anchor verification
```

ngspice ≥ 39 required (`brew install ngspice` / `apt-get install ngspice`).
