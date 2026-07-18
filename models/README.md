# Tube SPICE models (CC0)

Goal: the first explicitly open-licensed tube SPICE model set — every model freshly
fit from published datasheet curves, methodology documented per file, dedicated to the
public domain (CC0, see LICENSE.md).

Phase-0 targets (covers the pilot circuits 5f1 / 5e3 / 5f6a):

- [x] 12AX7 (triode) — anchor-fit v0, CI-verified
- [x] 12AY7 (triode) — anchor-fit v0, CI-verified
- [x] 6V6GT (beam power) — anchor-fit v0, CI-verified
- [ ] 5881 / 6L6GC (beam power) — lands with the 5f6a pilot
- [x] 5Y3GT (rectifier) — anchor-fit v0, CI-verified
- [ ] GZ34 (rectifier) — lands with the 5f6a pilot

File convention: `<tube>.inc`, ngspice `.subckt`, header comment stating the
datasheet anchor and license. Models are **generated** by `pipeline/fit_models.py`
(edit anchors there, never the .inc files) and verified against their anchors in
ngspice by `pipeline/test_models.py` — both enforced in CI. Method + limitations:
[METHODOLOGY.md](METHODOLOGY.md).
