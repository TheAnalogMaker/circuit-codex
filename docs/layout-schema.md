# layout.yaml schema — board-layout diagrams

One optional `layout.yaml` per circuit directory. `pipeline/render_layouts.py`
turns it into `amps/<id>/layout.svg` — an original, redrawn board-layout diagram
in the house drawing style; `pipeline/check_layouts.py` gates it in CI.

A layout is a **redrawn diagram from published layout facts** — the order in
which parts sit on the board — never a trace or a dimensioned reproduction of a
factory drawing. Values and part types are **not** restated here: the renderer
reads them from `bom.yaml`, keyed by the reference designator (`ref`), so a
layout and the parts list can never disagree.

## Top level

| Field | Type | Req | Notes |
|---|---|---|---|
| `board.rows` | int | ✓ | Eyelet rows (2 for the Fender-style boards drawn so far) |
| `board.cols` | int | ✓ | Eyelet columns — the horizontal grid the parts land on |
| `board.title` | string | — | Heading drawn on the diagram (`"5E3 · eyelet board layout"`) |
| `caption` | string | ✓ | Provenance line, in public-documentation voice — shown under the diagram on the site and used as the drawing's own credit |
| `source.desc` / `source.url` | string | ✓ | The published layout drawing this order was read from; also cite it in `meta.yaml` sources |
| `parts` | list | ✓ | Board-mounted parts (below) |
| `offboard` | list | — | Tubes, pots, jacks, transformers, switches drawn as labelled stubs |
| `runs` | list | — | **v2 wiring layer** — routed hookup leads (below) |
| `bus` | list | — | **v2 wiring layer** — ground-bus segments (below) |
| `leads` | list | — | Legacy soft visual leads (superseded by `runs`; kept for back-compat) |

## `parts[]` — board-mounted components

Each entry places one part by its two eyelet endpoints. `ref` is the shared key
into `bom.yaml`; the renderer looks up the value and part type (electrolytic,
film/coupling, resistor, mica) and picks the body shape and label from there.

```yaml
- { ref: C11, a: [0, 3], b: [0, 5] }   # same row  → axial part spanning cols 3–5
- { ref: RK1, a: [0, 27], b: [1, 27] } # shared col → vertical leg between the rows
- { ref: RKA, a: [0, 12], b: [1, 12], nudge: [2, -26] } # shift label clear of wiring
```

`a` / `b` are `[row, col]` eyelet coordinates. Endpoints in the same row draw an
axial (horizontal) body; endpoints sharing a column draw a vertical leg (a
cathode resistor to ground, a bypass can). Optional `nudge: [dx, dy]` shifts the
part's ref/value label pair (in px) to keep it clear of the wiring layer. A
referenced designator that is absent from `bom.yaml` fails the render — and CI.

## `offboard[]` — labelled stubs around the board

```yaml
- { id: V1,  ref: V1,  kind: tube,  edge: bottom, at: 25,  label: "V1 · 12AY7" }
- { id: VR1, ref: VR1, kind: pot,   edge: top,    at: 14,  label: "Volume" }
- { id: T2,  ref: T2,  kind: xfmr,  edge: right,  at: 0.5, label: "Output trans" }
```

| Field | Notes |
|---|---|
| `id` | Stub identifier (a `leads[]` endpoint may reference it) |
| `ref` | Optional BOM ref; when present its value is shown under the label |
| `kind` | `tube` · `pot` · `jack` · `xfmr` · `choke` · `switch` |
| `edge` | `top` · `bottom` · `left` · `right` — which side of the board it sits on |
| `at` | Position along that edge: a column coordinate for top/bottom, a row coordinate for left/right (fractions allowed) |
| `label` | Text drawn under the stub |

Tubes draw their real pin ring with pin numbers; the pin count is read from the
tube's `reference/tubes/<tube>.yaml` basing data (via the `ref`'s BOM value), so
`runs` can address a socket pin and have it validated.

## Wiring layer (schema v2)

The wiring layer turns a placement diagram into a routed board-wiring diagram: a
builder can trace every lead. It is read lead-by-lead from the published layout
drawing. The redrawn schematic remains the electrical authority; the wiring
layer is the physical routing on the board.

### Endpoint grammar

Every `runs`/`bus` endpoint is one of:

| Form | Means |
|---|---|
| `[row, col]` | a bare board eyelet (or a routing point on the ground bus) |
| `"REF.a"` / `"REF.b"` | a board part's eyelet (`REF` is a `parts[]` ref) |
| `"V1.pin3"` | a tube socket pin — **validated** against `reference/tubes/<tube>.yaml` basing; an out-of-range/unknown pin fails the render (and CI) |
| `"VR1.lug2"` | a potentiometer lug (`1` \| `2` \| `3`; `2` is the wiper) |
| `"JI"` / `"JI.tip"` / `"JI.sleeve"` | a jack (bare id = body) |
| `"T2.green"` | a transformer / choke lead by colour name — each distinct colour gets its own stacked, colour-matched pigtail on the board-facing edge |

### `runs[]` — routed hookup leads

```yaml
runs:
  - { from: PT.red1, to: V5.pin4 }                       # colour taken from the lead
  - { from: V5.pin8, to: C11.a, color: red, via: [[3, 1.55]] }
  - { from: C11.a,  to: T2.red, via: [[3, 2.6], [30.4, 2.6]] }
```

| Field | Notes |
|---|---|
| `from` / `to` | endpoints (grammar above) |
| `color` | optional era wire-colour **name** (`red`, `green`, `yellow`, `blue`, `brown`, `black`, `red-yellow`, …). Mapped to a house-tuned palette that stays legible on the dark board and shown in the drawing's colour legend. A run onto a transformer lead inherits that lead's colour automatically. Uncoloured runs render in the neutral hookup-lead tone. |
| `via` | optional routing waypoints in **grid** units `[x, y]` where `x` = column axis, `y` = row axis (note this is horizontal-first — the opposite order from a part's `[row, col]`). `y < 0` routes above the board, `y > rows-1` below it (fractions allowed). Runs bend through these with rounded elbows; a couple of waypoints keep a lead in a clean lane clear of its neighbours. |

### `bus[]` — ground-bus segments

```yaml
bus:
  - { from: [1.45, -0.4], to: [1.45, 29.4] }   # bare ground rod along the board
```

Same endpoint grammar and `via` waypoints as `runs`, drawn as a single heavier
bare-wire line (no colour) so it reads as the ground rod it is. Cathode, filter,
and pot grounds tie to it by ending a `run` on a point along the rod.

### Self-review (mandatory)

A wiring diagram must be **looked at**, not just generated — see `docs/REVIEW.md`.
Render a PNG and read it:

```
python pipeline/render_layouts.py --png 5e3   # → /tmp/5e3.png (installs librsvg if absent)
```

Iterate until labels are legible, nothing overlaps, every run is traceable, and
the off-board parts are clearly placed.

## `leads[]` — legacy soft leads (deprecated)

Superseded by `runs`. Endpoints are an eyelet `[row, col]` or an `offboard` `id`;
drawn as faint suggestion curves. Kept only for back-compat.
