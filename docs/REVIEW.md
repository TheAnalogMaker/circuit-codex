# Quality gates — how an amp gets to the site

Two layers: deterministic checks in CI, and an editorial/accuracy judge pass
on the rendered output.

## Layer 1 — CI (every push, blocking)

| Gate | Tool | What it catches |
|---|---|---|
| Metadata schema | `pipeline/validate.py` | Missing/invalid fields, bad lineage refs, unlinked sources |
| Artifact completeness | `pipeline/validate.py` | A `verified` amp missing netlist, voltages, notes, schematic, or BOM |
| BOM ↔ schematic cross-check | `pipeline/validate.py` | Any designator in one but not the other (both directions; V1A/V1B collapse to bottle V1) |
| History ↔ amp cross-check | `pipeline/validate.py` | A family row and the circuit it links stating different years or wattage — the two tiers describing the same amplifier on the family page, the lineage chip and the amp's own page. Where a row deliberately covers more (or less) than its circuit, it carries an `era_note` saying why; the note is printed loudly like a lint waiver, renders on the family page beside both numbers, and is an error once the disagreement it waives is gone |
| Tube-model anchors | `pipeline/fit_models.py` + `test_models.py` | Model drift; models not matching datasheet anchors in ngspice |
| Operating-point verification | `pipeline/verify_amps.py` | Simulated DC vs published chart outside tolerance (blocking for `verified`) |
| Worst-deviation claim | `pipeline/verify_amps.py` | `verification.max_deviation_pct` disagreeing with the worst gated node the same run just computed. The field is a hand-written mirror of a number the site prints on the amp page, so it needs a gate that executes it: the 5E4-A shipped `9.2` (its driver plate) while its worst node was the 12AY7 cathode at 10.0%. Blocking for draft and verified alike — an internal contradiction, not a chart disagreement |
| Schematic grammar | `pipeline/check_schematics.py` | kiutils round-trip failures, plus KiCanvas-strict tokenization (a raw quote inside a string that kiutils forgives and KiCanvas renders as a blank panel) |
| Schematic sheet furniture | `pipeline/check_schematics.py` | An empty title block — the corpus shipped 34 sheets whose Title and Date were blank, advertising an unfinished drawing under the `verified` badge. Every sheet now states its own designation, style, revision date and status, read from its `meta.yaml` |
| Schematic legibility | `pipeline/check_schematics.py` | Lettering printed through live circuitry (a B+ flag over the sheet title, tremolo prose over a phase-shift ladder), drawing content laid into the bottom-right corner where the worksheet prints the title block over it, and a drawing that fills less than 62% of its sheet's drawable area. All three are pure geometry, invisible to a parser and fatal to a reader; the gate reconstructs symbol bodies, pins, property text and labels from the file itself and fails on overlap, intrusion and dilution |
| Layout render + determinism | `pipeline/check_layouts.py` | A `layout.yaml` that fails to render, or a stale committed drawing out of sync with a fresh render — checked for **both** published styles (`layout.svg` and the era `layout-sheet.svg`) |
| Era value lettering | `pipeline/test_era_values.py` | The sheet style's on-body value shorthand (`4.7K`, `.02-400`, `25MFD`, `250PF`) drifting from the documented convention, or mangling a value it cannot parse — swept over every value in every `bom.yaml` |
| Social-card staleness | `pipeline/render_og.py --check` | A committed `site/public/og/<id>.png` no longer matching the layout, metadata or renderer it was built from — or hand-edited. Digest-based, so it needs no rasteriser in CI |
| Wiring collision lint | `pipeline/check_layouts.py` | Wiring-layer ambiguity — near-parallel overlap (two runs reading as one wire) or terminal ambiguity (an endpoint reading as landing on another run). The three **label** checks additionally run against the sheet style, which sets its type at its own sizes and letters values on the bodies (findings tagged `[sheet]`). Blocking unless the amp carries a waiver in `pipeline/lint_waivers.yaml`; active waivers are printed loudly |
| Layout ↔ netlist equivalence | `pipeline/verify_layout_nets.py` | The drawn point-to-point wiring not being electrically equivalent to the verified netlist — an extra connection (short), a missing connection (split node), a lead on the wrong node, an **unanchored tube**, or a signal run relabelled `twisted`. Builds both net graphs and proves isomorphism within the DC scope (heaters/pilot/PT-AC excluded, declared in `net_map`). Hardened 2026-07-19 (see `docs/layout-schema.md`): EU/US valve aliases resolve, every netlist tube must anchor to a socket (by id or type) or fail, PI→output coupling caps + grid leaks are modelled so push-pull phase and inter-stage routing are checked natively, twisted runs are validated onto heater pins, `net_map` anchors are labelled CONSTRAINING/REDUNDANT, and the unverified control-network island is declared terminal-by-terminal. A round-2 re-audit (same day) closed three more escapes: the **phantom-pin bug** (pin anchors now thread bottle→socket, so a function-named tube checks its *real* socket terminals), a complete **unchecked-terminal enumeration** (every non-modelled part lead and pot lug is listed with its net, tagged *placement not DC-checked*, so a mis-lugged pot ground or a bias resistor on a live rail can't hide by landing on a netlist-carrying net), and **shrinking the unchecked set** (every DC-open cap with both leads on named DC nodes added to the netlist across all 8 amps, `verify_amps` still 8/0/0). **Hard-blocking** for any amp whose `layout.yaml` sets `wiring_claim: verified`; report-only otherwise. Hardened again 2026-08-02 (**H9**): the section↔triode-half assignment is now enumerated for *every* multi-section bottle, including one whose netlist models only one of its two halves (a 12AX7 sharing a socket with an excluded tremolo oscillator, or a single-triode channel input) — those sockets previously anchored no pin at all and their whole signal wiring went unchecked; a candidate half must carry every role the netlist instance uses, so a numbered detector-diode plate (6AT6) is never mistaken for a triode half. A `--selftest` step first proves the gate catches a planted fault for every hole class (now incl. phantom-pin full-path, the two enumeration cases, and the H9 wrong-pin + 6AT6 false-positive pair, and HB, the same half-bottle wired ACROSS both triode halves) |

## Layer 2 — judge pass (every new/changed amp page, post-deploy)

A reviewing agent (a Claude session — Flywheel-compatible) reads the **live
rendered pages** and judges what CI can't:

1. **Editorial voice** — pages must read as public documentation, never as
   the project's internal working notes (no process narration, no
   "secondary sources", no changelog-style headings).
2. **Technical accuracy vs the literature** — stated facts checked against
   the reviewer's knowledge of these heavily documented circuits and the
   cited sources.
3. **Internal consistency** — metadata panel vs prose vs tables vs BOM;
   consistent units, date formats, and terminology across pages.
4. **Presentation** — missing sections relative to sibling pages, confusing
   table entries, anything that undermines the "verified" brand promise.

Findings get fixed in the same session or filed as issues. The judge runs on
the rendered site (not the repo) deliberately — it sees what visitors see,
including rendering bugs the data can't show.

**Known blind spot — figures need eyes, not fetches** (learned 2026-07-18):
text-fetch judges cannot see whether SVG actually *renders* — the
reading-schematics figures shipped as invisible black shapes while every
fetch-based check passed, because the styles were scoped and the SVG was
injected with `set:html` (which bypasses Astro's scoping). Two standing rules:
(1) any `set:html`-injected SVG must have its styles in an `is:global` block;
(2) figure-heavy pages get a **screenshot-based** visual pass (a browser, not
a fetch) before they count as reviewed.

First judge run: 2026-07-18 (caught internal-notes voice leaking into the
5E3 circuit story, among others — see repo history).

## Board-layout diagrams — render, then LOOK

The same "figures need eyes" rule governs both drawings of every board. CI
(`check_layouts.py`) proves each layout renders to valid, deterministic SVG and
that every reference resolves — but it cannot see whether the drawing *reads*.
Before a new or changed layout (especially one with a `runs`/`bus` wiring layer)
counts as reviewed, its author converts it to PNG and reads it — **both styles**,
since each sets its own type:

```
python pipeline/render_layouts.py --png <id>                # → /tmp/<id>.png (installs librsvg if absent)
python pipeline/render_layouts.py --style sheet --png <id>  # → /tmp/<id>-sheet.png
```

A wide board rasterised whole is too small to read; crop by rewriting the SVG's
`viewBox` over the region in question and rasterising that, rather than
declaring a drawing legible from a thumbnail.

Check, at minimum: labels legible and clear of wires; no body/wire overlaps that
hide a value; every wiring run traceable end to end; wire colours match the
published drawing; off-board components clearly placed. Two wiring-specific
things the pilot added eyes for (2026-07-19), on GM's note that "some wires
overlap and/or it is sometimes a bit unclear where a wire terminates":

- **Crossings show as hops.** Where two plain runs cross, the later one bows
  over the earlier with a small semicircular bridge — confirm a crossing never
  looks like a joint. (The deterministic `check_layouts.py` collision lint
  already proves no two wires read as one; the eyes confirm the hop *renders*.)
- **Terminations read as solder points.** Every run endpoint is a filled
  solder blob distinct from a via or pass-through — confirm where each wire
  lands is unambiguous, especially in convergence clusters.
- **Labels legible over wiring.** Part values and pot values must read clearly,
  not merge into a lead crossing behind them. Pot labels carry an opaque halo;
  where that isn't enough, nudge the value into clear space — `value_nudge` on a
  board part (value alone) or `label_nudge` / `value_nudge` on a pot (see
  `docs/layout-schema.md`). The 2026-07-19 pass cleared the 5F4/5F6-A/JTM45 pot
  values and 5F4's RTAIL/C11/RB1 labels off their supply leads this way.

Iterate until it reads like a reference diagram a builder could follow. Layouts
that still carry overlap/termination debt are held behind a
`pipeline/lint_waivers.yaml` waiver, not shipped clean — remove the waiver only
once the layout passes the lint on its own.

## Schematics — the sheet is the figure

`check_schematics.py` proves a sheet parses, states its own identity, fits its
paper and prints no lettering through its own circuitry. It cannot see whether
the circuit *reads*. KiCanvas is the renderer the site ships against and the
only true proof — a browser screenshot after about twelve seconds of render
time — but it is far too slow to iterate against. For the iterations, there is
a fast approximation:

```
python3 pipeline/_sch_preview.py <id> /tmp/sch-<id>.png 3.0   # needs librsvg
```

It draws the file's own geometry — page outline, title-block reserve, symbol
graphics, wires, junctions, labels, lettering — at a fidelity good enough to
answer "does this read". It is a review aid and **not** evidence about what
KiCanvas shows: its font is not KiCad's and its labels are plain text, not
flags. A schematic change is reviewed when the gate is green, the preview
reads, and a browser screenshot confirms it.

Two things the preview is specifically good at catching, both of which shipped
live before the 2026-08-08 pass: a part standing *on* a wire rather than beside
it (which shorts it out — the 6G4's tremolo plate load and its oscillator grid
leak were both drawn that way), and a ground flag taken off the head of a shunt
part instead of its foot, so the flag prints down through the body it grounds.
Neither shows up in a netlist gate, because neither file is the netlist.

## Social cards — the same rule

Each amp page's link preview is a generated card carrying a crop of that amp's
own layout drawing, so a layout change changes a published figure:

```
python pipeline/render_og.py <id>     # → site/public/og/<id>.png (needs librsvg)
```

Read the PNG before committing it. It is seen at a fraction of its 1200×630 —
a forum or chat preview is often 500 px wide — so what matters is that the
circuit designation and style name carry at that size, and that the board band
reads as a drawing rather than a grey texture. Check the crop landed on a
dense stretch of board, that no caption is sliced by the bottom edge, and that
the spec strip and the tube complement have not run into each other.

## Prose is written against the POST-batch corpus

Learned the hard way on 2026-08-08, when fifteen circuits landed in one
session: entries written early in a batch described a corpus the same batch
outgrew. `amps/ab165/notes.md` told readers that the AA864 and the 6G6-B "are
not yet documented circuits here" — the AA864 landed in the *same commit*, the
6G6-B later the same day. `amps/6g5/notes.md` told readers the tweed Pro was
"not yet a circuit entry" and that `derived_from` "should carry its id once it
lands", on a page whose own metadata panel already showed `derived_from: 5e5a`.
Four netlist headers said the 6L6GC had no model, three hours after the 6L6GC
model was committed. None of it was a wrong *fact* when written; all of it was
a wrong fact when published.

Two standing rules follow:

1. **Write against the corpus the batch will ship, not the one in front of
   you.** If a circuit is assigned in the same batch, it exists. Say what the
   relation is, not that the relation is pending. Never publish an instruction
   to your future self ("once it lands, `derived_from` should carry its id") —
   that is a work item, and a work item in visitor documentation reads as the
   site talking to itself.
2. **The integrator runs a stale-claims sweep before pushing.** Once every
   entry in the batch is merged, grep the whole batch's published prose for
   existence claims and process narration and re-check each hit against the
   grown corpus. The phrases that have actually gone stale here:

   ```
   grep -rniE "not (yet )?(a )?(documented|in the corpus|circuit entry)|exists yet|\
   once it lands|should carry|this (pass|session)|(data-core|drawings) (pass|session)|\
   earlier pass|first pass|what this entry ships|[0-9]{4}-[0-9]{2}-[0-9]{2} re-read" \
     amps/*/notes.md amps/*/meta.yaml amps/*/layout.yaml amps/*/bom.yaml amps/*/netlist.cir
   ```

   Numeric counts are not the whole problem — a count sweep catches "33
   circuits" going stale but not "that circuit is not documented here". Both
   need checking.

The structural cause is worth naming too: `notes.md` is a single channel doing
double duty, public circuit story *and* session work log, and the site
publishes the whole file under "Circuit story". Until that split exists, the
discipline is the author's: **a dated heading in `notes.md` is a defect**, and
so is any sentence whose subject is the project rather than the circuit.
