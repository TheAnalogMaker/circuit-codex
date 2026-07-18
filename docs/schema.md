# meta.yaml schema — v1 (Phase 0 draft)

One `meta.yaml` per circuit directory. Validated by `pipeline/validate.py` in CI.
Schema will stabilize at the end of Phase 0 (pilot: 5f1, 5e3, 5f6a).

## Fields

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | string | ✓ | Directory name; lowercase circuit designation (`5e3`, `jtm45`) |
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
| `sources` | list | ✓ | Where the circuit facts came from (published charts, dated revisions, measurements) — never "traced from factory drawing" |
| `verification.status` | enum | ✓ | `draft` · `verified` — **only CI + maintainer review set `verified`** |
| `verification.date` | date | when verified | |
| `verification.max_deviation_pct` | number | when verified | Worst node deviation, simulated vs published chart |
| `contributors` | list | — | GitHub handles, in landing order |

## Example

See `amps/_template/meta.yaml`.
