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
| Published simulated volts | `pipeline/verify_amps.py` | `reference/op-points.yaml` — the per-node simulated voltages the amp pages print in their Simulated column — no longer matching what the run just simulated. The site cannot run ngspice at build time, so those numbers are exported (`--export`) and committed; a stale export would publish a voltage no run produced, which is why staleness fails like any other gate result |
| Worst-deviation claim | `pipeline/verify_amps.py` | `verification.max_deviation_pct` disagreeing with the worst gated node the same run just computed. The field is a hand-written mirror of a number the site prints on the amp page, so it needs a gate that executes it: the 5E4-A shipped `9.2` (its driver plate) while its worst node was the 12AY7 cathode at 10.0%. Blocking for draft and verified alike — an internal contradiction, not a chart disagreement |
| Output-stage export drift | `pipeline/export_loadlines.py --check` | A committed `reference/loadlines.yaml` that no longer says what the netlists simulate. Value-level, not byte-level, for the reason `numeric_drift` gives |
| Output-stage export consistency | `pipeline/export_loadlines.py --check` | The generated file contradicting its own grid-supply contract. A drift gate cannot see a field that is *consistently* wrong — a fresh export reproduces the same wrong value and the comparison passes forever, which is how eleven of the twenty-nine fixed-bias circuits shipped a null `grid_supply_node` for as long as the field existed while the other eighteen resolved. So the file must now also **say what kind of answer each null is**: `grid_supply_basis` is `cathode-bias` (the stage biases itself across `rk`, and there is no negative supply to name — the 5F1), `source` (the rail is a DC source and the volts are what that source statement carries), `network` (the rail is derived from a source through the netlist's own resistive network — the 5G9's 82k/56k divider — and `grid_supply_note` names the source it comes from), or `unresolved`, which is a defect and must carry a written reason, never a bare null. Every fixed-bias stage lands in one of the first three or fails. The rule with teeth is arithmetic: a resolved `grid_supply_v` must be the voltage `grid_v` actually sits at, since the grid returns to the rail through a leak carrying no DC current — that is what separates *a* node from *the* node, and it rejects naming the 5G9's −69 V rectifier instead of its −28 V divider output even though both are real nodes in the deck. `--selftest` plants each fault class on the committed file and proves the gate fires; `--check` runs it too, so the proof cannot be left unwired |
| Schematic grammar | `pipeline/check_schematics.py` | kiutils round-trip failures, plus KiCanvas-strict tokenization (a raw quote inside a string that kiutils forgives and KiCanvas renders as a blank panel) |
| Schematic sheet furniture | `pipeline/check_schematics.py` | An empty title block — the corpus shipped 34 sheets whose Title and Date were blank, advertising an unfinished drawing under the `verified` badge. Every sheet now states its own designation, style, revision date and status, read from its `meta.yaml` |
| Schematic legibility | `pipeline/check_schematics.py` | Lettering printed through live circuitry (a B+ flag over the sheet title, tremolo prose over a phase-shift ladder), drawing content laid into the bottom-right corner where the worksheet prints the title block over it, and a drawing that fills less than 62% of its sheet's drawable area. All three are pure geometry, invisible to a parser and fatal to a reader; the gate reconstructs symbol bodies, pins, property text and labels from the file itself and fails on overlap, intrusion and dilution |
| Schematic connectivity | `pipeline/check_schematics.py` | A pin the drawing shows connected and the file leaves open. KiCad joins wires at their **endpoints**: a lead that stops 0.64 mm short of a bus, or a pin sitting partway along one, renders as a finished connection and carries nothing. Six sheets shipped a phase inverter whose tail was drawn onto the wrong electrode this way, three of them under a `verified` badge, and no gate in the repo could see it — the netlists were right and the drawings were not. The check runs `sch_nets.Nets.isolated_pins()` over every sheet and requires each symbol pin to share its net with at least one other pin or label, printing the gap a fixer has to close and whether the pin has a lead to move at all (`--report` lists them all, worst gap first). `pipeline/sch_open_pins.yaml` waives a pin that is open on purpose, one dated entry per pin with a sentence saying why; a waiver whose pin is no longer open is itself an error. **Report-only** while the per-amp drawing repairs land (`--connectivity=error`, or `CX_CONNECTIVITY=error`, gates on it); `--connectivity=selftest` plants an open on a clean 5E3 net and proves the check names it |
| Schematic drift | `.github/workflows/ci.yml` | A committed `schematic.kicad_sch` that is no longer what `pipeline/draw_<id>.py` draws — the AA864 carried a title block reading `draft` for three weeks after `meta.yaml` said verified. CI regenerates every sheet and diffs, the same drift gate `models/` and `loadlines.yaml` have. This became possible only when element ids stopped being random: they are now `uuid5` over the amp id and emission order, so regenerating an unchanged drawing reproduces its file byte for byte instead of rewriting all 182 uuid lines. The published copies under `site/public/schematics/` are diffed after the build, whose first step syncs them |
| Layout render + determinism | `pipeline/check_layouts.py` | A `layout.yaml` that fails to render, or a stale committed drawing out of sync with a fresh render — checked for **both** published styles (`layout.svg` and the era `layout-sheet.svg`) |
| Era value lettering | `pipeline/test_era_values.py` | The sheet style's on-body value shorthand (`4.7K`, `.02-400`, `25MFD`, `250PF`) drifting from the documented convention, or mangling a value it cannot parse — swept over every value in every `bom.yaml` |
| Social-card staleness | `pipeline/render_og.py --check` | A committed `site/public/og/<id>.png` no longer matching the layout, metadata or renderer it was built from — or hand-edited. Digest-based, so it needs no rasteriser in CI |
| Wiring collision lint | `pipeline/check_layouts.py` | Wiring-layer ambiguity — near-parallel overlap (two runs reading as one wire) or terminal ambiguity (an endpoint reading as landing on another run). The three **label** checks additionally run against the sheet style, which sets its type at its own sizes and letters values on the bodies (findings tagged `[sheet]`). Blocking unless the amp carries a waiver in `pipeline/lint_waivers.yaml`; active waivers are printed loudly |
| Layout ↔ netlist equivalence | `pipeline/verify_layout_nets.py` | The drawn point-to-point wiring not being electrically equivalent to the verified netlist — an extra connection (short), a missing connection (split node), a lead on the wrong node, an **unanchored tube**, or a signal run relabelled `twisted`. Builds both net graphs and proves isomorphism within the DC scope (heaters/pilot/PT-AC excluded, declared in `net_map`). Hardened 2026-07-19 (see `docs/layout-schema.md`): EU/US valve aliases resolve, every netlist tube must anchor to a socket (by id or type) or fail, PI→output coupling caps + grid leaks are modelled so push-pull phase and inter-stage routing are checked natively, twisted runs are validated onto heater pins, `net_map` anchors are labelled CONSTRAINING/REDUNDANT, and the unverified control-network island is declared terminal-by-terminal. A round-2 re-audit (same day) closed three more escapes: the **phantom-pin bug** (pin anchors now thread bottle→socket, so a function-named tube checks its *real* socket terminals), a complete **unchecked-terminal enumeration** (every non-modelled part lead and pot lug is listed with its net, tagged *placement not DC-checked*, so a mis-lugged pot ground or a bias resistor on a live rail can't hide by landing on a netlist-carrying net), and **shrinking the unchecked set** (every DC-open cap with both leads on named DC nodes added to the netlist across all 8 amps, `verify_amps` still 8/0/0). **Hard-blocking** for any amp whose `layout.yaml` sets `wiring_claim: verified`; report-only otherwise. Hardened again 2026-08-02 (**H9**): the section↔triode-half assignment is now enumerated for *every* multi-section bottle, including one whose netlist models only one of its two halves (a 12AX7 sharing a socket with an excluded tremolo oscillator, or a single-triode channel input) — those sockets previously anchored no pin at all and their whole signal wiring went unchecked; a candidate half must carry every role the netlist instance uses, so a numbered detector-diode plate (6AT6) is never mistaken for a triode half. A `--selftest` step first proves the gate catches a planted fault for every hole class (now incl. phantom-pin full-path, the two enumeration cases, and the H9 wrong-pin + 6AT6 false-positive pair, and HB, the same half-bottle wired ACROSS both triode halves) |
| Heater wiring | `pipeline/check_heaters.py` | The drawn heater/filament wiring not being what the amp's own `heaters:` block declares — or that declaration not being what the valve's datasheet permits. **A separate claim from the row above, and it must never be read as covered by it**: heaters are excluded from the DC comparison by explicit rule, so until 2026-09-09 no gate here had ever looked at a heater lead, and the 5F1 shipped a 12AX7 whose two supply legs were joined and whose centre tap was unwired under a `wiring_claim: verified` badge that was true about the thing it claimed (issue #30). The cause was an inference: which two pins a supply's legs land on is a fact about the amplifier, not the valve, and a centre-tapped heater wires the same three pins as `[4,5]|[9]` at 6.3 V and `[4]|[5]` at 12.6 V. So the layout states its supply voltage, per-socket connection groups and grounded return as data, and this gate proves it against `reference/tubes/<tube>.yaml` `heater.supplies` (**D1** a declared pin is not a heater pin; **D2** a pin on both legs or an empty leg; **D4** the grouping strands a heater pin — the 6.3/12.6 configuration mismatch; **D3** every pin on a leg but the grouping is not one the sheet wires) and against the runs the SVG is generated from (**W1** a declared terminal no conductor reaches — a missing return; **W2** the two legs drawn on one net — a bridge across the supply; **W3** the grounded leg not grounded, or a leg grounded that was declared floating). `--selftest` plants one fault per class on the 5F1 and requires each to be caught. A layout with no `heaters:` block prints NOT DECLARED with its centre-tapped sockets listed and is **not checked** — and its drawing correspondingly renders a heater run at such a socket as the single conductor its data names, never as a pair with an invented second landing. Two things follow from *not checked*, because the gate is read by a maintainer and the drawing by a visitor. The **drawing carries its own marker**: the heater legend key gains `(leg grouping not established)` and a footer line states what is in doubt (the supply legs at the named centre-tapped valves) and what is not (which sockets sit on the chain, and the order it reaches them in) — flagged rather than suppressed, since deleting the layer would destroy correct information to hide doubtful information. And the **worklist is committed**: `--export` writes `reference/heaters.yaml` — per layout, the sockets drawn on an unestablished grouping and every same-socket link classified `shorted` (opposite legs at every supply the valve's sheet lists — wrong whatever the amplifier runs) or `unclassified` (one leg at one supply, opposite at another) — and a normal run **fails if that file is not what a fresh run produces**, the same drift gate `op-points.yaml` and `loadlines.yaml` carry. It found four shorted links no hand survey had listed |
| Sheet ↔ board equivalence | `pipeline/verify_sheet_vs_board.py` | The schematic and the board layout drawing different circuits over the parts the DC netlist does not model — 1,280 of ~2,300 BOM passives, which both equivalence gates above skip by construction. The two drawings are authored independently, so they are each other's witness: tube pins, pot wipers, jack contacts and `<GND>` anchor the two net partitions to each other, every two-terminal part is resolved from those anchors by majority vote, and a section ↔ unit swap is searched for on every dual-section socket. Reports `SECTION-SWAP`, `SPLIT`, `MERGED`, `MISPLACED` (both surfaces' nets in canonical names), `UNRESOLVED` (not checked), `SHEET-ONLY` (declared or UNDECLARED, against `net_map.not_on_board`, `scope.not_drawn` rules, `net_map.leads` and the reused `netlist_unplaced` / `series_bridge` declarations — see `docs/layout-schema.md`), `BOARD-ONLY`, `POT-AS-RESISTOR` (a control drawn with the resistor symbol) and `STALE DECLARATION`; heaters and the pilot lamp are excluded (`check_heaters.py` owns them). **Report-only** while the corpus is triaged: the committed worklist `reference/sheet-board.yaml` is gated for drift against a fresh run (regenerate with `--export`), and `--strict` — exit 1 on any finding on an amp whose sheet and board both claim verified — enters CI once that worklist is clean for them. `--selftest` plants a section swap, a moved cap lead, bridged wipers, a cut ground return and an undeclared deletion on temp copies of two clean amps and requires each caught |

**Two drawings are each other's gate.** Every gate above checks a drawing against
the netlist, and the netlist is a DC model that leaves ~1,280 passives unmodelled
on purpose; a coupling cap on the wrong pot lug, a tone-stack resistor into the
wrong net, or a whole dual-triode drawn on the opposite datasheet unit on the
sheet from the board, passed every gate in this table until 2026-09-10. The
schematic and the layout are written by different hands from the same source, so
where they disagree at least one is wrong — and `verify_sheet_vs_board.py` finds
those disagreements with no netlist in the loop. A finding there is not a verdict:
it names the part and prints both surfaces' nets, and the next step is always a
read of the amplifier's own sheet before either drawing is edited.

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

**And eyes need zoom** (learned 2026-08-08): a full-sheet capture at viewer
scale leaves value text ~3 px tall, and a reviewer who "confirms" a fix at
that resolution is accepting it on faith — every "unconfirmable at screenshot
resolution" item in the closing visual pass turned out to be perfectly
confirmable once the same pixels were crop-zoomed. Never accept a fix at
full-page resolution: verify the exact region with
`node scripts/shoot.mjs --out <dir> --crop <id>:<x>,<y>,<w>,<h>` (region in
the pixel coordinates of the prior overview `<id>-schematic.png`; it
re-renders at 3x device resolution rather than upscaling), or at minimum
PIL-crop the overview PNG and LANCZOS-upscale the region before judging it.

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

### Drawn is not connected

The most expensive thing to know about these files: **KiCad matches connection
points, not ink.** A wire connects at its two endpoints and nowhere else. A pin
whose end lands partway along a wire is drawn as a clean T-tap and is
electrically open; so is a lead that stops a fraction of a millimetre short of
the bus it points at. Neither is visible at page zoom, in the preview, or in a
browser screenshot — the picture is the same picture either way.

Eeschema hides this from a human by breaking the wire under the cursor as you
draw. Generated sheets get the same treatment now: `Sch.write()` cuts every wire
at each pin, wire end and junction dot that lands inside it, so a sheet this
pipeline emits is the file eeschema would have saved. Nothing moves on the page
and no net changes — it is a normalisation, not a repair.

What it cannot normalise is a lead that genuinely stops short, and that is what
`check_schematics.py --report` prints: every pin whose net holds nothing else,
with the distance from its own dangling net to the nearest ink that belongs to
a different one. Read the distance before reaching for a fix. Under 1.5 mm is a
lead drawn a grid step short and the repair is arithmetic in the draw script;
around 9 mm on a triode is a lead taken to the wrong electrode and the repair is
the stage block; 40 mm is a valve nobody wired at all.

Each finding also says whether the pin has a lead. `stub stops short` means the
wire exists and ends in the wrong place, so the repair is the coordinate it
stops at; `no lead drawn` means the pin was never wired and the repair is to
draw the lead. The corpus splits 106 stubs to 145 bare pins, and the two are
different edits to the draw script even where the distance is the same.

### A label's name is a wire

Two global labels with one name are one net, wherever they sit on the page. On
2026-09-10, 16 of 24 power transformers had their mains primary shorted
because a label named `MAINS` lettered both leads. The 6G5's primary closed on
itself from one `MAINS` label, through its switch, fuse and winding, back to
the same name. The same day the 5F1 was found drawing its output primary as a
wire across the winding. The equivalence gate saw none of it: the netlist
models no winding, and an `sch_map` anchor that puts both ends of an OT
primary on B+ joins them on purpose. `SHORTED WINDING` in
`verify_schematic_nets.py` now reads every winding on the nets as drawn,
before any declared contraction, and says whether a wire, a label name or a
fuse-and-switch loop did the joining. Give each lead of a winding a name of
its own (`MAINS` / `MAINS N`), and letter two points alike only when they are
one conductor.

### Which way round a diode is drawn

A diode's direction is a physical fact that a sheet records in exactly one
place: the rotation of its symbol. Nothing else in the file encodes it, the
netlist models no diode at all, and the boards' `cathode:` fields were copied
from the sheets, so until 2026-09-10 no gate here could tell a rectifier drawn
backwards from one drawn right, and a count that day found 25 of 68 sheet
diodes reversed. Eighteen were negative-bias rectifiers with the cathode on the
negative node, the arrangement that would charge that node positive. The check
that now exists reads the one fact the netlist does carry, the simulated sign
of each supply, and holds every diode to it: a cathode on a node the model
holds below −5 V, an anode on one above +50 V, or a part forward-biased by more
than 1 V between two modelled nodes is `REVERSED DIODE` in
`verify_schematic_nets.py` (blocking on a claimed sheet), and the same rule
reads each board's `cathode:` in `verify_layout_nets.py` (report-only until its
list is empty). Where a rectifier's own node sits behind parts the netlist does
not model, a bias row's resistor and trim pot or an HT standby switch, the
check walks through them to the node it does model and prints the path. A diode
nothing decides, like the inner diodes of a series HT stack, is listed as not
checked on every run, so review the drawn symbol against the source anyway: the
check knows which side of ground a supply is on, not which lead is the tap. A
second check, `UNFED RECTIFIER`, follows each rectifier's AC side to a
transformer winding. It exists because the 6G5 at e4e59fa drew a bridge whose
AC corners sat on ground, and polarity called two of its diodes confirmed.

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

   Repo paths are the other leak (the growth-wave-3 judges found 40+ of them
   live): a page that cites `notes.md`, `bom.yaml`, `verify_layout_nets.py` or
   a bare `amps/<id>` directory is working notes wearing a visitor page's
   clothes. Sweep every rendered prose surface for them — `notes.md` bodies,
   and the *rendered* YAML fields: `desc:` in meta.yaml sources, `notes:` and
   per-item `role:` in bom.yaml, `note:`/`dispute_note:` in voltages.yaml
   (YAML comments never render and are fine):

   ```
   grep -rniE "amps/[a-z0-9-]+|(notes|meta|bom|voltages|layout)\.(md|yaml)|\
   netlist\.cir|kicad_sch|[a-z0-9_-]+\.py|docs/[a-z]|models/METHODOLOGY|\
   reference/tubes/|history/families/" amps/*/notes.md
   ```

   and the same pattern over the YAML fields (a script that walks the parsed
   fields beats grepping whole files, which comments would flood). A markdown
   link to a live site page — `[Champ](/amps/aa764/)` — is the correct form
   for a same-site cross-reference and is not a hit; the bare directory
   spelling `amps/aa764` in prose is.

The structural cause is worth naming too: `notes.md` is a single channel doing
double duty, public circuit story *and* session work log, and the site
publishes the whole file under "Circuit story". Until that split exists, the
discipline is the author's: **a dated heading in `notes.md` is a defect**, and
so is any sentence whose subject is the project rather than the circuit.

## Reading a value off a scan

Every gate in this project checks the corpus against itself. Not one of them can
tell you that a figure was misread off the source in the first place — and a
misread *chart* value is worse than a misread part value, because the simulation
is then calibrated to it and the page reports agreement.

Two rules, learned the hard way on the same afternoon (2026-09-09).

**1. Check the resolution before you trust the digits.** Schematic Heaven's copy
of the 5F8-A sheet is 1506 × 841 natively. Read at that size it gives rails of
+377/+375 and a phase-inverter cathode of +22.5 V. The Internet Archive's capture
of the el34world scan of the same drawing is 6368 × 3218 (693 ppi) and plainly
reads +397/+395 and +28.5 V. Render at 400 dpi or better, crop, and magnify. If a
glyph is not unambiguous, find a better copy — the Wayback Machine holds
el34world's PDFs even while the live site is unreachable — or record the figure as
unresolved (`chart: null`). Never publish a blurred digit as read. State in the
source description which copy each figure came from, so a later reader can tell.

**2. Arithmetic can FALSIFY a reading. It cannot ESTABLISH one.** The asymmetry is
the whole point, and both halves happened here:

* *Falsification worked.* +22.5 V at a cathode sitting below a +27 V junction fed
  through 470 Ω is not merely unlikely, it is impossible. The circuit refuted the
  reading before a better scan confirmed it. This is cheap, and it works when no
  better copy exists.
* *Establishment failed.* On the 5G9 a blurred cathode resistor read as `1500` or
  `1800`. The sheet's own printed voltages give 0.98 mA and 1.7 V, so ≈1.74 kΩ,
  and 1.8 kΩ was published. The drawing letters **1500**. The arithmetic agreed
  with the wrong answer because a ±20 % chart tolerance is wide enough to swallow
  the difference.

So: use the circuit to *reject* a figure that cannot be true, and go back to the
source for the figure that is. A computed value that merely lands inside the
sheet's tolerance is not evidence of anything — that tolerance is exactly the
width in which two different components look alike.

When a misread does ship and is later caught, record it where a reader will meet
it, as `amps/5g9/notes.md` does. A correction nobody can see teaches nobody.
