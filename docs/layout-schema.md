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
| `leads` | list | — | Optional visual wire runs |

## `parts[]` — board-mounted components

Each entry places one part by its two eyelet endpoints. `ref` is the shared key
into `bom.yaml`; the renderer looks up the value and part type (electrolytic,
film/coupling, resistor, mica) and picks the body shape and label from there.

```yaml
- { ref: C11, a: [0, 3], b: [0, 5] }   # same row  → axial part spanning cols 3–5
- { ref: RK1, a: [0, 27], b: [1, 27] } # shared col → vertical leg between the rows
```

`a` / `b` are `[row, col]` eyelet coordinates. Endpoints in the same row draw an
axial (horizontal) body; endpoints sharing a column draw a vertical leg (a
cathode resistor to ground, a bypass can). A referenced designator that is
absent from `bom.yaml` fails the render — and CI.

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

## `leads[]` — optional wire runs

```yaml
- { from: [0, 3], to: V1 }      # eyelet [row,col] → off-board stub id
- { from: [0, 7], to: [1, 7] }  # eyelet → eyelet
```

Endpoints are either an eyelet `[row, col]` or an `offboard` `id`. Leads are a
legibility aid, not a wiring reference — the redrawn schematic is the wiring
authority. Keep them sparse.
