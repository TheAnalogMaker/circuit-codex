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
| `kind` | `tube` · `pot` · `jack` · `xfmr` · `choke` · `switch` · `part` |
| `edge` | `top` · `bottom` · `left` · `right` — which side of the board it sits on |
| `at` | Position along that edge: a column coordinate for top/bottom, a row coordinate for left/right (fractions allowed) |
| `label` | Text drawn under the stub |
| `glyph` | Only for `kind: part` — `lamp` draws the pilot-lamp glyph; otherwise a small axial body |

Tubes draw their real pin ring with pin numbers; the pin count is read from the
tube's `reference/tubes/<tube>.yaml` basing data (via the `ref`'s BOM value), so
`runs` can address a socket pin and have it validated.

### Generic 2-lead off-board parts (`kind: part`)

Not every part sits on the eyelet board. `kind: part` is a generic off-board
component with **two addressable terminals** — `REF.a` and `REF.b` — for the
chassis-mounted odds and ends the board grid can't hold: the pilot lamp and
chassis-mounted resistors (e.g. an input grid-leak wired at the jacks). Its two
terminals face the board so `runs` land on them exactly like a board part's
`.a` / `.b` eyelets.

```yaml
- { id: PL1, kind: part, glyph: lamp, edge: left, at: 1.5,  label: "Pilot lamp" }
- { id: R1,  ref: R1,    kind: part, edge: top,   at: 19.3, label: "R1" }
```

`glyph: lamp` renders the pilot lamp (bulb + bayonet-base hint). Without a
glyph, a small axial body is drawn — typed and valued from `bom.yaml` when a
`ref` is given (so a chassis resistor still restates nothing), or neutral when
it isn't.

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
| `"REF.a"` / `"REF.b"` | a board part's eyelet (`REF` is a `parts[]` ref), **or** a generic 2-lead off-board part's terminal (`REF` is an `offboard` `kind: part` id) |
| `"V1.pin3"` | a tube socket pin — **validated** against `reference/tubes/<tube>.yaml` basing; an out-of-range/unknown pin fails the render (and CI). On a `style: twisted` (heater) run a tube endpoint must additionally be a **heater/filament** pin |
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
| `style` | optional. `twisted` draws the run as two interleaved sinusoidal strands sharing its endpoints — the classic **6.3 V heater** idiom. Twisted runs render in the heater green (`green-yellow` gives the centre-tap strand where a drawing marks one) and get a dedicated legend entry ("6.3 V heaters — twisted pair") rather than a colour swatch. |
| `via` | optional routing waypoints in **grid** units `[x, y]` where `x` = column axis, `y` = row axis (note this is horizontal-first — the opposite order from a part's `[row, col]`). `y < 0` routes above the board, `y > rows-1` below it (fractions allowed). Runs bend through these with rounded elbows; a couple of waypoints keep a lead in a clean lane clear of its neighbours. A deep lane (e.g. the twisted heater bus below the output harness) grows the drawing's bottom band automatically so it clears the legend. |

#### Heater chains (twisted pairs)

The 6.3 V filament wiring is drawn as a `style: twisted` chain in the drawing's
daisy order: **PT green pair → pilot lamp → socket to socket**. Heater/filament
socket pins are read from `reference/tubes/<tube>.yaml` basing (noval 4/5 with
9 the centre tap; octal power tubes 2/7; directly-heated rectifiers 2/8 —
those sit on the 5 V winding, not the 6.3 V chain). A twisted run onto a tube
is **validated to land on a heater pin** — a heater lead routed to a signal pin
fails the render (and CI). The pilot lamp is an `offboard` `kind: part` with a
`lamp` glyph; the pair enters `PL1.a` and leaves `PL1.b` to the first socket.

### `bus[]` — ground-bus segments

```yaml
bus:
  - { from: [1.45, -0.4], to: [1.45, 29.4] }   # bare ground rod along the board
```

Same endpoint grammar and `via` waypoints as `runs`, drawn as a single heavier
bare-wire line (no colour) so it reads as the ground rod it is. Cathode, filter,
and pot grounds tie to it by ending a `run` on a point along the rod.

### Crossing & termination legibility (automatic)

The renderer keeps the wiring layer unambiguous about **crossings** and
**terminations** — the two things a builder must never misread — with no extra
markup in the YAML:

- **Hop-over arcs.** At every transversal crossing between two plain
  (non-twisted) runs, the run appearing **later** in the `runs` list hops the
  earlier one with a small semicircular bridge (~3.5 px) — the classic
  wiring-diagram idiom, so a crossing never looks like a joint. The ground bus
  never hops (runs hop over it, with a slightly larger arc to clear the heavier
  rod); twisted heater pairs are exempt because they draw as the topmost,
  visually unmistakable layer. Hops are skipped within ~6 px of a segment's
  endpoints and never intrude on a rounded elbow. Output stays deterministic.
- **Solder blobs at run endpoints.** Every run/bus endpoint lands as a larger
  filled dot inside a darker ring with a small highlight — a soldered joint,
  clearly distinct from a bare via waypoint (undrawn) or a pass-through eyelet —
  so where a wire *terminates* is never in doubt, even inside a convergence
  cluster. Shared nodes are de-duplicated so coincident endpoints don't stack.

Both idioms are keyed in the drawing's **Joints** legend row.

### Collision lint (CI, `check_layouts.py`)

`pipeline/check_layouts.py` runs a **collision lint** over each layout's plain
runs — the checks that catch the two ways a wiring layer turns ambiguous
(twisted heater pairs and the ground bus are exempt):

| Check | Trips when |
|---|---|
| **near-parallel overlap** | two different runs' segments run at an acute angle < 10° with separation < 2.4 px over > 8 px of shared length (they read as one wire) |
| **terminal ambiguity** | a run endpoint sits within 5 px of *another* run's polyline interior while not landing on any of that run's own nodes (unclear whether it connects or merely passes by) |

Fix a failure by **lane/via adjustment** — nudge a shared lane to a distinct
row, fan converging feeds so each approaches its shared node at a wider bearing
(≳ 18° apart), or route a long harness lead in the deep band below the sockets —
preserving the published routing intent and the era wire colours. Failures print
with coordinates and run indices.

#### Waivers — `pipeline/lint_waivers.yaml`

A permanent, documented escape hatch (like a chart's disputed-node note). An amp
listed in `lint_waivers.yaml` (`{amp_id: reason}`) has its lint failures
**downgraded from blocking to WAIVED**, and CI prints the active waivers loudly
so a waiver is never silent:

```yaml
waivers:
  5f10:  "pending legibility remediation 2026-07-19"
```

An amp with zero lint failures needs no entry. Remove the waiver once the layout
is remediated. The pilot fixed **5f1** and **5e3** to zero lint; the remaining
six carry the same legibility debt behind a waiver until they are worked.

### Self-review (mandatory)

A wiring diagram must be **looked at**, not just generated — see `docs/REVIEW.md`.
Render a PNG and read it:

```
python pipeline/render_layouts.py --png 5e3   # → /tmp/5e3.png (installs librsvg if absent)
```

Iterate until labels are legible, nothing overlaps, every run is traceable, and
the off-board parts are clearly placed. The collision lint (above) is the
deterministic half of this — a clean `check_layouts.py` run means no two wires
read as one and no endpoint reads as ambiguous; the PNG read is still required
to confirm the crossings show as hops and the terminations read as solder points.

## `leads[]` — legacy soft leads (deprecated)

Superseded by `runs`. Endpoints are an eyelet `[row, col]` or an `offboard` `id`;
drawn as faint suggestion curves. Kept only for back-compat.
