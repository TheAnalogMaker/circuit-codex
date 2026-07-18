# Tube SPICE models (CC0)

Goal: the first explicitly open-licensed tube SPICE model set — every model freshly
fit from published datasheet curves, methodology documented per file, dedicated to the
public domain (CC0, see LICENSE.md).

Phase-0 targets (covers the pilot circuits 5f1 / 5e3 / 5f6a):

- [ ] 12AX7 (triode)
- [ ] 12AY7 (triode)
- [ ] 6V6GT (beam power, pentode-mode fit)
- [ ] 5881 / 6L6GC (beam power)
- [ ] 5Y3GT (rectifier)
- [ ] GZ34 (rectifier)

File convention: `<tube>.inc`, ngspice `.subckt`, header comment stating datasheet
source (manufacturer, year, figure numbers) and the fit method/parameters.
