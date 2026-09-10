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
python3 pipeline/validate.py --selftest && \
python3 pipeline/validate.py            # schema, lineage, sources, BOM↔schematic refs
                                        #   + history rows vs the circuit each links:
                                        #   years, wattage and the tube complement,
                                        #   canonicalised through reference/tubes so
                                        #   7025 and 12AX7 are one bottle. era_note on
                                        #   the row is the documented waiver.
python3 pipeline/fit_models.py && git diff --exit-code models/   # zero model drift
python3 pipeline/test_models.py         # ngspice datasheet-anchor checks
python3 pipeline/test_era_values.py     # era lettering + house/schematic surface conventions
python3 pipeline/check_value_consistency.py --selftest && \
python3 pipeline/check_value_consistency.py --strict   # cross-surface quantities agree
python3 pipeline/check_tube_used_in.py --selftest && \
python3 pipeline/check_tube_used_in.py                 # tube used_in == circuits that letter the tube
python3 pipeline/verify_amps.py         # DC op-point vs chart (draft=warn, verified=FAIL)
                                        #   + reference/op-points.yaml staleness (the
                                        #   simulated volts the amp pages print).
                                        #   Regenerate with --export and commit.
cd pipeline && python3 check_schematics.py --connectivity=selftest && \
python3 check_schematics.py   # kiutils round-trip + sheet furniture/legibility
                              #   lint + the connectivity report: every symbol
                              #   pin must share its net with another pin or
                              #   label, because KiCad joins wires at their
                              #   ENDPOINTS and a lead stopping short of a bus
                              #   draws as connected and carries nothing.
                              #   BLOCKING since 2026-09-02 (default error;
                              #   --connectivity=warn to survey); waivers in
                              #   pipeline/sch_open_pins.yaml, dated, one
                              #   reason sentence each.
cd pipeline && for f in draw_*.py; do python3 "$f" >/dev/null; done && \
(cd ../site && node scripts/sync-assets.mjs) && \
git diff --exit-code -- ../amps ../site/public/schematics   # zero schematic drift: ids are
                                  #   content-derived, so regenerating an
                                  #   unchanged drawing reproduces its file
                                  #   byte for byte. Same gate as models/.
cd pipeline && python3 check_tonestack_wiring.py  # drawn tone stack == plotted one
cd pipeline && python3 check_layouts.py      # BOTH layout renders + collision lint (+waivers)
python3 pipeline/render_og.py --check        # per-amp social cards match their layouts
python3 pipeline/verify_layout_nets.py       # layout↔netlist equivalence (+--selftest)
                                  #   + rectifier polarity: every board diode's
                                  #   `cathode:` against the simulated sign of
                                  #   the supply it sits on. BLOCKING on every
                                  #   board, claimed or not, since 2026-09-11
                                  #   (POLARITY_BLOCKING; docs/layout-schema.md)
                                  #   + UNFED RECTIFIER: a rectifier's AC side
                                  #   reaching no power-transformer lead
                                  #   (blocking, same switch)
                                  #   + electrolytic polarity: each can's drawn
                                  #   '+' vs the DC sign; the worklist
                                  #   reference/electrolytics.yaml is drift-
                                  #   gated (regenerate with --export)
                                  #   + SHORTED PART: a two-lead part with both
                                  #   leads on one net, read as drawn
                                  #   (blocking on every board,
                                  #   SHORTED_PART_BLOCKING)
python3 pipeline/check_heaters.py --selftest && \
python3 pipeline/check_heaters.py            # heater wiring vs the amp's own declared
                                  #   supply, connection groups and returns, and
                                  #   the pilot lamp ACROSS the two legs (W4) —
                                  #   a SEPARATE claim from the DC equivalence
                                  #   above, which excludes heaters entirely.
                                  #   A layout with no `heaters:` block prints
                                  #   NOT DECLARED, is not checked, and its
                                  #   drawing carries a visitor-facing marker
                                  #   saying so. Also gates the committed
                                  #   worklist reference/heaters.yaml against a
                                  #   fresh run; regenerate with --export.
python3 pipeline/verify_sheet_vs_board.py --selftest && \
python3 pipeline/verify_sheet_vs_board.py    # sheet<->board net equivalence over EVERY
                                  #   part, no netlist: the two drawings are
                                  #   authored independently and are each
                                  #   other's witness over the ~1,280 passives
                                  #   the DC netlist does not model (which both
                                  #   equivalence gates skip by construction).
                                  #   Tube pins, pot wipers, jack contacts and
                                  #   <GND> anchor the two partitions; parts
                                  #   resolve by majority vote; section<->unit
                                  #   swaps are searched for. EXCLUDES heaters
                                  #   and the pilot lamp (check_heaters owns
                                  #   them) and lists what it could not anchor.
python3 pipeline/check_sections.py --selftest && \
python3 pipeline/check_sections.py           # every valve section the tube complement
                                  #   supplies (counted from the tube's own
                                  #   basing, never its name) is instantiated
                                  #   in netlist.cir or declared in meta.yaml
                                  #   `sections:` as "excluded —", "not drawn —"
                                  #   or "unused —". A stage missing from both
                                  #   the netlist and the sheet is invisible to
                                  #   every equivalence gate; this is where the
                                  #   omission has to be said.
                                  #   Findings are report-only: the worklist
                                  #   reference/sheet-board.yaml is gated for
                                  #   drift (regenerate with --export), and
                                  #   --strict (exit 1 on findings on amps whose
                                  #   sheet AND board claim verified) enters CI
                                  #   once that worklist is clean for them.
                                  #   Declarations: docs/layout-schema.md.
python3 pipeline/check_architectures.py --selftest && \
python3 pipeline/check_architectures.py     # reference architectures partition the
                                            #   corpus; each one's claims checked
                                            #   against netlist.cir and loadlines,
                                            #   not against the metadata its own
                                            #   predicate selects on. See
                                            #   docs/architecture-schema.md
python3 pipeline/verify_schematic_nets.py --selftest && \
python3 pipeline/verify_schematic_nets.py    # schematic↔netlist equivalence: SHORTED /
                                             #   MERGED / SPLIT / WRONG TERMINAL are
                                             #   drawing faults; abstractions are declared
                                             #   in amps/<id>/sch_map.yaml; a sheet with
                                             #   schematic_claim: verified hard-fails CI
                                             #   + REVERSED DIODE: a cx:DIODE_SS whose
                                             #   rotation contradicts the simulated sign
                                             #   of the supply it sits on (same gating;
                                             #   docs/schematic-nets.md#rectifier-polarity)
                                             #   + SHORTED WINDING: a winding's two ends
                                             #   on one drawn net (a wire, one label name
                                             #   on both leads, a fuse-and-switch loop),
                                             #   read BEFORE any sch_map contraction
                                             #   + UNFED RECTIFIER: a rectifier whose AC
                                             #   side reaches no transformer pin or
                                             #   label declared in sch_map winding_labels
python3 pipeline/export_loadlines.py --selftest && \
python3 pipeline/export_loadlines.py --check # reference/loadlines.yaml vs the netlists,
                                             #   plus grid-supply resolution: a fixed-bias
                                             #   stage resolves a rail or states why not,
                                             #   and the rail must equal the grid node's
                                             #   own simulated level
cd site && npm ci && npm run build      # site must build
cd site && node scripts/check-loadline-parity.mjs   # browser solver vs. ngspice
cd site && node scripts/check-tonestack-spice.mjs   # tone-stack solver vs. ngspice + the wiring study's figures
cd site && node scripts/check-lineage-caption.mjs   # lineage prose names every drawn arrow
```

Use `python3` (no `python` on PATH in the usual environments). ngspice is required
(`brew install ngspice` locally; apt in CI).

**Non-gating steps.** `npm run build` ends with `node scripts/indexnow-ping.mjs`,
which submits the built sitemap's URLs to IndexNow (Bing, Yandex, Seznam) so a
deploy is announced instead of waited for. It is deliberately outside the gate set:
every failure path logs and exits 0, because a slow search-engine API is not a claim
about the corpus and must never fail a build. It also skips on local builds — set
`INDEXNOW=1` to force a submission, `INDEXNOW=0` to suppress one in CI. The
authentication key is public by design and lives in `site/public/<key>.txt`; if that
file is ever renamed, the `KEY` constant in the script must move with it.

`pipeline/check_source_links.py` is the other one. Every claim here is anchored to a
published document, so a citation that 404s is a claim a reader cannot check — but
whether somebody else's web server answers today is not a fact about this corpus, so
this runs on a human's say-so and never in the gate set. It sorts results into DEAD
(404/410 — ours to fix) and BLOCKED/FLAKY (403, 429, 5xx, timeouts, TLS failures —
the far end's, and no evidence the document is gone). Run it every few months, or
after a source archive reorganises:

    python3 pipeline/check_source_links.py            # report, always exits 0
    python3 pipeline/check_source_links.py --strict   # exit 1 on DEAD, for a human

Replacing a dead link is not a URL swap. Open the replacement and confirm it carries
what the citation claims — publisher, edition, and the numbers the description
quotes. On 2026-09-09 both dead links had an obvious-looking neighbour in the same
archive directory that turned out to be a differential sheet ("the 6V6 is the same as
the 6V6GTA except…") carrying none of the model's anchor figures.

## Lettering conventions (values and designators)

One convention per surface, all of them gated — `docs/lettering-conventions.md`
is binding. House units in `bom.yaml` and prose (`470 Ω`, `4.7 kΩ`,
`0.02 µF · 400 V`, `250 pF`; never comma-grouped thousands); drafting shorthand
on the schematic in the amp's declared idiom (`meta.yaml`
`conventions.notation: us|uk`), with secondary ratings as separate
space-separated fields (`470 5W`, not `470·5W` and not `470-5`); era sheet
lettering generated by `render_layouts.era_pair()` and authored nowhere. Each
amp declares its reference-designator scheme (`conventions.designators:
sequential|functional`) and `validate.py` proves the declaration against the
parts list. A designator is what a drawing letters on a part: letters and digits
only.

## Editorial voice (public pages)

Site pages are **visitor documentation**, never working notes: no process narration,
no internal version names (v0/v1), no repo paths or YAML field names in prose, no
"our secondary sources disagree" — instead state the fact and cite. House units
style: `470 Ω`, `4.7 kΩ`, `0.02 µF · 400 V`. Tolerances: tube pins ±20% (the era's
printed convention), rails tighter internal targets — label them as such.

**A corpus-scope claim names its count.** When prose says "every X in this corpus",
"the only", or "identical to", it states the number the claim covers, or the query it
rests on, so a reader — and the next author — can check it. Such a sentence is a
claim about circuits its author did not have open, and it is written from memory
unless a query says otherwise: on 2026-09-09 an audit found three of them wrong in
one week's prose, all the same bug. "The same pair every fixed-bias long-tailed-pair
amp in this corpus uses (5f4/6g3/ab763)" was true of the three circuits its author
had open and false of the corpus — there are 19 such circuits, two of them use a
different pair, and the 5F4 is a cathodyne, not a long-tailed pair at all. No gate
reads a sentence, so this convention is most of what stands behind one: grep the
prose you are shipping for "the only", "every", "identical to" and "in this corpus",
and answer each hit with a query before pushing. Where a claim *can* be gated it is —
the same audit found two family rows listing fewer preamp bottles than the circuits
they link, which is why `validate.py` now cross-checks the tube complement.

## Figures need eyes

Fetch-based review cannot see whether SVG renders. Any `set:html`-injected SVG needs
`is:global` styles; any new/changed figure or layout requires a rendered-image check
(`python3 pipeline/render_layouts.py --png <id>`, or `--style sheet --png <id>` for
the era layout-sheet drawing, then actually look at the PNG; KiCanvas schematics need
a browser screenshot after ~12 s render time). Every board ships in both styles, so a
layout change means looking at both — and a layout change also regenerates that
amp's social card (`python3 pipeline/render_og.py <id>`, then look at
`site/public/og/<id>.png`; it needs rsvg, which Workers Builds does not have, so
the PNGs are committed). See `docs/REVIEW.md` for the standing rules and
`docs/layout-schema.md` for the two styles, the wiring layer, lint, and
equivalence-gate semantics.

## Working style that has served this repo

- Parallel authors work in scratch clones (`git clone --depth 1 file://<repo>`); one
  serial integrator hand-merges into the real repo and pushes once.
- Adversarial review is normal here: audits plant faults and attack claims. Welcome
  it; when an audit breaks your work, the fix is to harden, then re-audit — and if a
  live page overclaims meanwhile, withdraw the claim first and re-earn it.
- Every mistake found gets fixed in public with a commit message that says what was
  wrong. The history is the audit trail.
