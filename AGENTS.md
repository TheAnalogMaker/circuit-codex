# AGENTS.md — orientation for AI agents working on Circuit Codex

This repository is built and maintained largely by AI agents under human direction.
That is stated publicly (circuitcodex.com/about/). The conventions below are binding
on every contributor, human or machine. They exist because the project's brand is
*verifiability* — a wrong claim shipped confidently is worse than no claim.

## The project in one paragraph

An open corpus of vintage guitar tube-amp circuits. Each `amps/<id>/` holds structured
data (`meta.yaml`, `netlist.cir`, `voltages.yaml`, `bom.yaml`, `layout.yaml`,
`schematic.kicad_sch`, `notes.md`) that the Astro site in `site/` renders at deploy
time (Cloudflare Workers Builds on push to main → circuitcodex.com). Tube models in
`models/` are CC0 clean-room fits. `pipeline/` holds the generators and gates.

## Hard rules (violations are closed regardless of quality)

1. **Redraw from facts — never reproduce.** Viewing published scans to *read* facts
   (values, topology, chart voltages) is fine and how this corpus is built. Copying,
   tracing, or rehosting factory drawings is not. Sources are cited as `{desc, url}`.
2. **Circuit-number-first naming.** Ids and titles use circuit designations (`5e3`,
   `jtm45`). Maker/model names appear only descriptively (`name_style:
   "Tweed Deluxe-style"`).
3. **Clean-room tube models only.** Never copy parameters from Duncan/Koren or any
   existing collection. Fit from published datasheet tabulated anchors; document the
   method in the file header. See `models/METHODOLOGY.md`.
4. **Verified is earned, never granted by an agent.** CI gates block; only the human
   maintainer's sign-off grants. Never set `verification.status: verified` or
   `wiring_claim: verified` unless the corresponding gates actually pass locally.
5. **Honesty over completeness.** A chart that contradicts itself becomes a
   `disputed: true` node with `dispute_note` arithmetic — never force-fitted. A layout
   without a factory source says "derived". Draft badges are published, not hidden.

## Gates (all must pass before any push)

```
python3 pipeline/validate.py            # schema, lineage, sources, BOM↔schematic refs
python3 pipeline/fit_models.py && git diff --exit-code models/   # zero model drift
python3 pipeline/test_models.py         # ngspice datasheet-anchor checks
python3 pipeline/verify_amps.py         # DC op-point vs chart (draft=warn, verified=FAIL)
cd pipeline && python3 check_schematics.py   # kiutils round-trip
cd pipeline && python3 check_layouts.py      # layout render + collision lint (+waivers)
python3 pipeline/verify_layout_nets.py       # layout↔netlist equivalence (+--selftest)
cd site && npm ci && npm run build      # site must build
```

Use `python3` (no `python` on PATH in the usual environments). ngspice is required
(`brew install ngspice` locally; apt in CI).

## Editorial voice (public pages)

Site pages are **visitor documentation**, never working notes: no process narration,
no internal version names (v0/v1), no repo paths in prose, no "our secondary sources
disagree" — instead state the fact and cite. House units style: `470 Ω`, `4.7 kΩ`,
`0.02 µF · 400 V`. Tolerances: tube pins ±20% (the era's printed convention), rails
tighter internal targets — label them as such.

## Figures need eyes

Fetch-based review cannot see whether SVG renders. Any `set:html`-injected SVG needs
`is:global` styles; any new/changed figure or layout requires a rendered-image check
(`python3 pipeline/render_layouts.py --png <id>` then actually look at the PNG;
KiCanvas schematics need a browser screenshot after ~12 s render time). See
`docs/REVIEW.md` for the standing rules and `docs/layout-schema.md` for the wiring
layer, lint, and equivalence-gate semantics.

## Working style that has served this repo

- Parallel authors work in scratch clones (`git clone --depth 1 file://<repo>`); one
  serial integrator hand-merges into the real repo and pushes once.
- Adversarial review is normal here: audits plant faults and attack claims. Welcome
  it; when an audit breaks your work, the fix is to harden, then re-audit — and if a
  live page overclaims meanwhile, withdraw the claim first and re-earn it.
- Every mistake found gets fixed in public with a commit message that says what was
  wrong. The history is the audit trail.
