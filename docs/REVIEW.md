# Quality gates — how an amp gets to the site

Two layers: deterministic checks in CI, and an editorial/accuracy judge pass
on the rendered output.

## Layer 1 — CI (every push, blocking)

| Gate | Tool | What it catches |
|---|---|---|
| Metadata schema | `pipeline/validate.py` | Missing/invalid fields, bad lineage refs, unlinked sources |
| Artifact completeness | `pipeline/validate.py` | A `verified` amp missing netlist, voltages, notes, schematic, or BOM |
| BOM ↔ schematic cross-check | `pipeline/validate.py` | Any designator in one but not the other (both directions; V1A/V1B collapse to bottle V1) |
| Tube-model anchors | `pipeline/fit_models.py` + `test_models.py` | Model drift; models not matching datasheet anchors in ngspice |
| Operating-point verification | `pipeline/verify_amps.py` | Simulated DC vs published chart outside tolerance (blocking for `verified`) |
| Schematic grammar | `pipeline/check_schematics.py` | kiutils round-trip failures |

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

The same "figures need eyes" rule governs `amps/<id>/layout.svg`. CI
(`check_layouts.py`) proves a layout renders to valid, deterministic SVG and
that every reference resolves — but it cannot see whether the drawing *reads*.
Before a new or changed layout (especially one with a `runs`/`bus` wiring layer)
counts as reviewed, its author converts it to PNG and reads it:

```
python pipeline/render_layouts.py --png <id>   # → /tmp/<id>.png (installs librsvg if absent)
```

Check, at minimum: labels legible and clear of wires; no body/wire overlaps that
hide a value; every wiring run traceable end to end; wire colours match the
published drawing; off-board components clearly placed. Iterate until it reads
like a reference diagram a builder could follow.
