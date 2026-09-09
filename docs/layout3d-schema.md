# 5F1 3D layout data contract

`pipeline/export_layout3d.py` exports the existing 5F1 layout and BOM into
`site/public/layouts/5f1-3d.json`. Only `5f1` is supported by this pilot. An
unsupported id fails rather than implying the rest of the corpus has been
reviewed for 3D. Existing circuit YAML, SVGs and schematic generators are inputs,
not modified outputs.

```
python3 pipeline/export_layout3d.py 5f1
python3 pipeline/export_layout3d.py --check
python3 pipeline/export_layout3d.py --selftest
```

`--check` compares a fresh deterministic export byte for byte with the committed
file and fails on missing/stale data. It does not write. `--selftest` plants
wrong pins, reintroduced omitted heater strands, dropped components, changed
BOM values, invented routes and altered scope/provenance claims; every fault
must fail.

## Coordinates and ownership

All `[x, y]` coordinates are original `render_layouts.Renderer` pixel coordinates.
They describe a legible diagram, not measured physical dimensions. The frontend
may translate and divide them by 40 to fit its scene; heights and body volumes
are illustrative frontend geometry. It must keep each connection attached to
its declared terminals while changing viewing angle or exploding the diagram.

`Renderer` owns board/eyelet placement, part endpoints, socket-pin positions,
pot lugs, jack aliases, transformer lead positions, bus routes and heater
forks. Numeric output is rounded to six decimal places. The exporter rejects
unresolved endpoints instead of falling back to a nearby component.

## Schema version 1

| Field | Meaning |
| --- | --- |
| `schemaVersion` | Integer `1` |
| `id`, `title` | Circuit id and existing board title |
| `source` | Exact layout `{desc, url}` provenance |
| `scopeNotes` | Displayable limitations of the view |
| `connectivity` | `scope: "layout-endpoints-only"` and explanatory note; not a new verification badge |
| `board` | Existing board rectangle `{x, y, width, height}` |
| `bounds` | Extent of original board, hardware glyphs and routed connection points; excludes labels and page chrome |
| `eyelets` | All original board-grid eyelets, each `{id, point}` |
| `components` | Every placed board part and off-board item; no invented placement for unplaced BOM items |
| `terminals` | Complete endpoint alias registry: `{id, label, point, owner}` |
| `connections` | One routed connection per retained ordinary run/bus segment; the known-wrong 6.3 V heater strands are absent |
| `omittedConnections` | Four dated source-run records explaining why seven 6.3 V heater strands are withheld; includes authored endpoints, strand count, reason and primary evidence URLs, never the omitted geometry |
| `unplacedBOMRefs` | Named BOM refs absent from the source layout; currently `C2`, `C4` |

A component contains `id`, optional `ref` for a named BOM item, `kind`, `mount`,
`category`, `label`, `value`, `role`, `center`, and `terminals`. Its terminal
records have the same shape as the global registry. Two-terminal parts also
provide `a` and `b` coordinate pairs.

- `mount` is `board` or `offboard`.
- Board components have `kind: part`. Off-board kinds retain the layout's
  `tube`, `pot`, `jack`, `xfmr`, or `part`.
- `category` retains the renderer's `res`, `electro`, `film`, `mica`, `diode`,
  `xfmr`, `choke`, `tube`, or `other`; the existing pilot-lamp glyph uses `lamp`.
- Named values and roles are read from the BOM without retyping. Unnamed
  hardware keeps its existing layout label and an empty value/role.

Connections contain `id`, `from`, `to`, `fromOwner`, `toOwner`, `points`, `kind`,
`color`, `sourceRun`, `sourceFrom`, and `sourceTo`.

- Published `kind` values are `wire` or `bus`. The internal geometry also
  recognizes `heater`, but no heater connection is published by this pilot.
  `color` comes from the existing renderer palette and authored colour
  resolution, never a guessed signal function.
- `from`/`to` preserve the actual resolved terminal aliases, e.g. `R8.a`,
  `V2.pin8`, `VR1.lug2`, `PT.red1`, or the source's simplified `J1` jack alias.
  A raw coordinate endpoint becomes `point:<row>:<col>`. These coordinate
  anchors have null owners and must remain fixed when components move.
- `sourceFrom`/`sourceTo` retain the authored YAML endpoints (string or
  `[row, col]`). `sourceRun` is the stable source index `run:N` or `bus:N`.
- Ordinary connections have `id: run:N`. The source's omitted heater geometry
  would expand to `run:N:strand:K`, with a single last same-socket link; these
  strand IDs and their geometry do not appear in the published connections.

## Heater omission and scope

On 2026-09-09 independent review found that the existing renderer's 12AX7
heater expansion puts opposite legs on pins 4 and 5, then joins them with its
closing link, while never reaching pin 9. The [RCA 12AX7-A datasheet](https://frank.pocnet.net/sheets/049/1/12AX7A.pdf)
requires 6.3 V parallel operation between joined 4/5 and pin 9; the
[5F1 factory layout](https://schematicheaven.net/fenderamps/champ_5f1_schem.pdf)
shows that connection with a grounded pin-9 return. The input layout's heater
annotations therefore must not become an apparently complete 3D wiring path.

The exporter withholds source runs 43–46, seven rendered strands, from the
published `connections`. `omittedConnections` preserves each source run's
authored endpoints and omitted-strand count with a dated reason and the two
primary-source URLs. It contains no known-wrong path geometry. The displayable
scope note states the omission, and the scene must not offer a control that
reveals these absent routes. Tube sockets/pins and the pilot lamp remain
hardware, without a claim of complete heater hookup. The separate ordinary
5 V rectifier-filament routes `run:3` and `run:4` remain included.

Internally, source geometry is resolved through `Renderer.build_geometry()`;
the current heater expansion is counted using the renderer's fork paths and
`twisted_points()`. The explicit exclusion validates exactly four source-run
identities and seven strands. A changed source configuration fails for review,
as does removing the coverage note/evidence or reinserting a heater strand.
Correcting the original renderer/layout and the electrical heater checks is a
separate change. Restoring heater coverage must review and remove the exclusion
instead of silently changing only the exported endpoints.
The source correction is tracked in [issue #30](https://github.com/TheAnalogMaker/circuit-codex/issues/30).

This is an **endpoint and drawing-geometry contract**, not a serialized circuit
netlist. Crossings do not create junctions. Board terminal aliases on the same
eyelet share coordinates; the two ends of a resistor/capacitor are not joined.
No named DC nets, simulated current, polarity, insulation rating or dimensioned
manufacturing data is asserted here. The original layout/netlist equivalence
gate remains separate, including its declared heater, pilot-lamp, PT/rectifier
and control-network limits.

The source layout places 27 items: 16 board parts and 11 off-board items. It has
43 ordinary routed wires, one bus segment and four authored heater runs, which
expand into seven omitted strands. The JSON therefore contains 44 connections. Its
40 grid eyelets and 88 terminal aliases are separate concepts. C2 and C4 remain
unplaced; the exporter requires a scope review if that set changes.

## Viewer and review

The 5F1 page includes a collapsed `Layout3D.astro` panel. Opening it, or following
`#layout-3d`, loads the JSON and the separately bundled Three.js renderer. Other
amp pages do not include the viewer. The JSON URL includes a content digest so
a changed export cannot silently reuse a previous browser-cached response.

The scene renders on demand, caps device pixel ratio at two, and disposes its
graphics resources on teardown. Board parts and off-board hardware separate by
illustrative heights; each retained wire stays attached to its source endpoints.
Computed overpasses distinguish wire crossings, while explicit ground-bus
landings remain joined. Selecting a component highlights only its directly
attached leads, with the same endpoints listed as text below the scene.
`node site/scripts/check-layout3d-geometry.mjs` independently checks source-path
crossings, actual mesh knots, terminal positions and bus junctions in assembled,
half-separated and fully separated states, including synthetic overlap cases.

For a visual review, build and preview the site, then open
`/amps/5f1/#layout-3d`. Inspect the assembled and fully separated views; select
R8, V1 and PT; hide and restore their layers; use the keyboard controls and
parts-list links; and check a narrow viewport. Inspect the actual WebGL image,
including wire crossings at a readable zoom. A successful build alone does not
establish that the figure renders correctly. The static reference drawing and
parts list remain the fallback when JavaScript or WebGL is unavailable.
