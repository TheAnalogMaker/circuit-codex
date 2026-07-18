# KiCad schematic spike — findings (2026-07-18, gate G0)

**Verdict: the KiCad-native pipeline works end-to-end.** Programmatic authoring →
kiutils validation → KiCanvas in-browser rendering, verified visually in Chrome.

## What was proven

1. **Programmatic authoring** — `pipeline/draw_5f1.py` generates the complete
   5F1 schematic (26 symbol instances, signal path + power supply) as a
   KiCad 8 `.kicad_sch`, using a self-contained symbol library (`cx:` — triode,
   pentode, tube diode, R, C, single-ended OT) embedded in the file. No external
   symbol-library dependencies → no licensing questions, and KiCanvas needs no
   library resolution.
2. **kiutils round-trip** — parses and re-emits cleanly; now a CI gate
   (`pipeline/check_schematics.py`) for every schematic in the corpus.
3. **KiCanvas embed** — `site/public/vendor/kicanvas.js` (self-hosted, alpha) +
   `<kicanvas-embed>` on the amp page renders the schematic with pan/zoom and a
   download control. Verified rendering in Chrome at `/amps/5f1/`.

## Viewer decision

**KiCanvas embed, self-hosted — adopted.** Renders our generated files
faithfully, ships pan/zoom + file download for free, and keeps the raw
`.kicad_sch` as the single source of truth (`site/scripts/sync-assets.mjs`
copies corpus schematics into the build). Fallback (kicad-cli SVG pre-render)
not needed; revisit only if KiCanvas's alpha status bites.

## Known polish items (not blockers)

- Rotated (horizontal) resistors render their value text rotated; label
  placement pass needed for rotated symbols.
- Junction dots render small at default zoom.
- Layout is generator-driven (hand-tuned coordinates per amp). Effort for the
  5F1: ~2–3 h including symbol design; subsequent amps reuse the symbol set and
  helpers, est. **2–4 h per amp** at 5E3/5F6-A complexity. Acceptable for G0.

## G0 gate: CLOSED

All four pilot-pipeline capabilities now exist: metadata schema + validation,
netlist + op-point verification vs published charts (5F1 verified), tube-model
derivation with CI anchors, and schematic authoring + browser rendering.
