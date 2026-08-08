# meta.yaml schema — v1 (Phase 0 draft)

One `meta.yaml` per circuit directory. Validated by `pipeline/validate.py` in CI.
Schema will stabilize at the end of Phase 0 (pilot: 5f1, 5e3, 5f6a).

## Fields

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | string | ✓ | Directory name; lowercase circuit designation (`5e3`, `jtm45`), optionally model-qualified (`ab763-twin`) — see [Ids and colliding designations](#ids-and-colliding-designations) |
| `name_style` | string | ✓ | Descriptive style name (`"Tweed Deluxe-style"`) — the only place maker vocabulary appears |
| `family` | enum | ✓ | `tweed` · `blackface` · `british` · `vox` · `boutique` · `other` |
| `era.start` / `era.end` | int | ✓ | Production years of the circuit revision |
| `wattage` | number | ✓ | Nominal output watts |
| `tubes` | list | ✓ | Ordered complement, e.g. `[12AY7, 12AX7, 6V6GT, 6V6GT, 5Y3GT]` |
| `topology.rectifier` | enum | ✓ | `tube` · `solid-state` (+ `type`, e.g. `5Y3GT`) |
| `topology.bias` | enum | ✓ | `cathode` · `fixed` |
| `topology.phase_inverter` | enum | ✓ | `cathodyne` · `long-tailed-pair` · `paraphase` · `none` (single-ended) |
| `topology.tone_stack` | string | ✓ | `single-knob` · `fmv` · `james` · `cathode-follower-fmv` · … |
| `lineage.derived_from` | list of ids | — | Direct circuit ancestors (solid edges in the graph) |
| `lineage.influenced` | list of ids | — | Looser influence (dashed edges) |
| `sources` | list of `{desc, url}` | ✓ | Where the circuit facts came from (published charts, dated revisions, measurements) — cite and link; `url` optional only when no canonical link exists. Never "traced from factory drawing" |
| `verification.status` | enum | ✓ | `draft` · `verified` — **only CI + maintainer review set `verified`** |
| `verification.date` | date | when verified | |
| `verification.max_deviation_pct` | number | when verified | Worst node deviation, simulated vs published chart |
| `added` | date | when draft | Day the circuit landed in the corpus (its git landing date). The feed dates a draft by it — production builds are shallow clones, so git cannot. Verified circuits are dated by `verification.date` instead |
| `contributors` | list | — | GitHub handles, in landing order |
| `conventions.designators` | enum | ✓ | `sequential` (`R1…R13`, class + running number) · `functional` (`RD1`/`RL4`/`CK1`, role coded). Both schemes ship; the page tells the reader which one it is written in. `validate.py` derives the scheme from `bom.yaml` and fails when the declaration disagrees — see [docs/lettering-conventions.md](lettering-conventions.md) |
| `conventions.notation` | enum | — | Schematic drafting idiom: `us` (default — the unit letter is the SI prefix of the house unit: `.005u`, `500p`, `1.5k`) · `uk` (British practice: RKM infix `2k2`, nanofarad film caps `47n`). Declared, not normalised away: it is the idiom the amp's own source drawing uses |
| `iron` | map | — | `{designator: rating}` for a transformer or choke whose parts-list value is a bare factory number (`"Fender 45216"`). The layout letters the rating beside the number so the drawing says what to wind or buy. Keys must name real `bom.yaml` designators. Omit the block entirely rather than guess — an amp with no `iron:` letters the part number alone and the gap stays visible |

## Ids and colliding designations

The corpus is named circuit-number-first (AGENTS.md rule 2), so an id is the
designation the factory drawing carries, lowercased: `5e3`, `aa764`, `jtm45`.

That works until a maker reuses a designation. Fender did, repeatedly: **AB763
heads the Deluxe Reverb drawing and the Twin Reverb drawing and others; AA864
likewise.** Two circuits cannot share one directory, and neither one has a better
claim to the bare number than the other.

**The rule.** An id is one of two shapes:

```
<designation>              5e3 · ab763 · jtm45 · aa1164
<designation>-<model>      ab763-twin · aa864-bassman
```

- `<designation>` is lowercase letters and digits, no separators.
- `<model>` is a single lowercase token naming the amplifier model this revision
  of the circuit belongs to. One hyphen only — the first hyphen is the split.
- The model slug **must appear as a word in the entry's own `name_style`**.
  `pipeline/validate.py` enforces this, so `ab763-twin` cannot be filed on a
  Deluxe Reverb.
- Ids that look numeric to a YAML 1.1 loader (`5e1` → `50`) must be quoted. Also
  enforced, the same guard the history tier and the load-line presets carry.

**Existing ids do not change.** URLs are permanent, and that permanence is the
whole reason this rule exists rather than a rename convention. When a colliding
circuit lands, it takes a qualified id and the circuit already in the corpus
keeps its bare one. A qualified id may also land first — qualification is a
property of the id, not of whether its sibling exists yet.

**How it renders.** `displayId()` in `site/src/lib/corpus.js` splits on the
hyphen and appends the qualifier in parentheses, taking the text from the tail of
the circuit's own `name_style` beginning at the matched word:

| id | `name_style` | renders as |
|---|---|---|
| `ab763` | Blackface Deluxe Reverb-style | `AB763` |
| `ab763-twin` | Blackface Twin Reverb-style | `AB763 (Twin Reverb-style)` |
| `5f6a` | Tweed Bassman-style | `5F6-A` |

The qualifier is therefore never typed twice and cannot drift from the entry it
labels. Pass the style explicitly — `displayId(id, meta.name_style)` — where you
already have it; call sites that hold only an id get the same answer from the
corpus index.

## Example

See `amps/_template/meta.yaml`.
