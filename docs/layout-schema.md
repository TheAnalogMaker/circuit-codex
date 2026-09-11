# layout.yaml schema — board-layout diagrams

One optional `layout.yaml` per circuit directory. `pipeline/render_layouts.py`
turns it into **two** original, redrawn board-layout diagrams —
`amps/<id>/layout.svg` in the house drawing style and
`amps/<id>/layout-sheet.svg` in the era layout-sheet style (below) —
and `pipeline/check_layouts.py` gates both in CI.

A layout is a **redrawn diagram from published layout facts** — the order in
which parts sit on the board — never a trace or a dimensioned reproduction of a
factory drawing. Values and part types are **not** restated here: the renderer
reads them from `bom.yaml`, keyed by the reference designator (`ref`), so a
layout and the parts list can never disagree.

## Two drawing styles, one layout

`render_layouts.py --style sheet` renders the same `layout.yaml` in the **era
layout-sheet drafting idiom** — cream ground, ink outlines, dogbone resistors,
sockets as double circles, and each part's value hand-lettered *on its body* —
to `amps/<id>/layout-sheet.svg`. It is a paint-only re-skin: `SheetRenderer`
inherits every coordinate, endpoint resolution, run polyline, hop-over and
label-placement path from `Renderer` and overrides nothing but how things are
drawn. Nothing about the *claims* differs between the two files; the amp page
shows the sheet by default and offers the house drawing beside it.

The idiom is the era sheets' general drafting style — never any specific
drawing's artwork. Hard rule 1 (redraw from facts, never reproduce) governs
style exactly as it governs values.

**Page chrome scales with the sheet.** A board's pixel geometry is a fixed grid
(`CW` × `ROWGAP`), so sheet width tracks column count — 1000 px for the 5F1,
2440 px for the 5F10 — at a near-constant height. Every one of these is read
scaled to a common page width, so chrome type set at a fixed pixel size renders
at wildly different ink heights across the corpus: the 5F10's title and legend
came out roughly half the 5F1's. Title, attribution and legend sizes (and the
footer band that holds them) are therefore multiplied by `width / CHROME_REF_W`,
clamped. Board **content** type — refs, values, socket captions — is
deliberately *not* scaled: it is measured against the fixed pixel grid by the
placer and the lint, and it must stay legible relative to the parts it names.

**Era value lettering.** In sheet style only, a part's value is compacted into
the shorthand the period drawings used and this archive documents for readers on
`/reference/guides/units-conventions/` (`era_pair()` in `render_layouts.py`):

| House units | On the sheet | Rule |
|---|---|---|
| `820 Ω · ½ W` | `820` | bare ohms; the sheet's footnote implies ½ W |
| `15 kΩ`, `4,700 Ω` | `15K`, `4.7K` | K suffix, normalised up from ohms |
| `1 MΩ` | `1MEG` | MEG suffix |
| `250 Ω · 5 W` | `250-5` | ohms–watts dash, only above the implied ½ W |
| `0.02 µF · 400 V` | `.02-400` | value–voltage dash, no leading zero |
| `250 pF`, `0.0005 µF` | `250PF`, `500PF` | under 1000 pF the era wrote pF |
| `25 µF · 25 V` | `25MFD` + `25V` | MFD on the can, volts on the line under it |

It is **strict**: anything that is not a plain resistance or capacitance comes
back untouched, so descriptive values (`selenium`, `Fender 125P1B · 320-0-320 V`,
`presence/NFB network`) keep the house wording. It applies only to values
lettered on a component body — board parts and the off-board `kind: part`
glyphs. Free-standing hardware labels keep house units: a pot's value carries a
taper suffix (`250 kΩ-A`) and a transformer's is a part number, and neither is a
body lettering. `pipeline/test_era_values.py` gates the table above plus a sweep
of every value in every `bom.yaml`. **Everything outside the sheet render —
pages, BOMs, the house drawing — is house units style, unchanged.**

## Top level

| Field | Type | Req | Notes |
|---|---|---|---|
| `board.rows` | int | ✓ | Eyelet rows (2 for the Fender-style boards drawn so far) |
| `board.cols` | int | ✓ | Eyelet columns — the horizontal grid the parts land on |
| `board.title` | string | — | Heading drawn on the diagram (`"5E3 · eyelet board layout"`) |
| `caption` | string | ✓ | Provenance line, in public-documentation voice — shown under the diagram on the site and used as the drawing's own credit |
| `source.desc` / `source.url` | string | ✓ | The published layout drawing this order was read from; also cite it in `meta.yaml` sources. Where no factory layout sheet exists (`jtm45`, `m1959`, `ac15`), cite the **circuit** drawing the arrangement was derived from and say so in the `desc` — the drawing's own attribution line prints it, and `board.title` carries `(derived)` so the site's alt text stays honest |
| `parts` | list | ✓ | Board-mounted parts (below) |
| `offboard` | list | — | Tubes, pots, jacks, transformers, switches drawn as labelled stubs |
| `runs` | list | — | **v2 wiring layer** — routed hookup leads (below) |
| `bus` | list | — | **v2 wiring layer** — ground-bus segments (below) |
| `net_map` | map | — | **v3** — reviewable data reconciling the drawn wiring with the DC netlist for the equivalence gate (below) |
| `wiring_claim` | string | — | **v3** — set to `verified` to hard-gate the equivalence check in CI (below) |
| `scope` | map | — | **v3** — board-scope declarations for the sheet ↔ board gate: `scope.not_drawn` rules naming, by glob, the parts this board does not draw and why (below) |
| `wire_legend` | map | — | Overrides a colour's swatch label in the drawing's wiring legend (below) |
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
part's ref/value label pair (in px) to keep it clear of the wiring layer;
`value_nudge: [dx, dy]` shifts the **value alone** — to slide a value out from
under a supply lead while the ref stays put (used where a dense power-supply
corner crosses a filter-cap or bias-resistor value). Both are now the *starting
point* for the automatic placement pass (below), not the mechanism: as of
2026-08-02 no layout in the corpus needs one, and a new one should only be
authored where the placer's result is measurably clean but editorially wrong.
A referenced designator that is absent from `bom.yaml` fails the render — and CI.

**Body vocabulary.** The renderer picks a body outline from the part type in
`bom.yaml`, and the same vocabulary holds whichever way the part is turned: a
film/mica cap is a square-cornered rectangle, a resistor a dogbone (rounded
ends, waisted), an electrolytic a crimped can with a `+` mark, a diode or
rectifier a square body with a cathode band. A part standing between the two
rows gets its own outline rotated, not a generic pill — before 2026-08-04 every
vertical body was the same rounded pill, so on a board of standing parts a
builder could not tell R from C by shape at all. Each form is keyed in the
drawing's **Bodies** legend.

**`cathode: a | b`** (diodes only) names the eyelet the *schematic* puts the
cathode on, so the drawn body can carry its band the right way round. The
drawing never infers polarity: an undeclared diode is drawn unbanded rather
than guessed at, and the field's comment must cite where in
`schematic.kicad_sch` the orientation was read. A band copied from a
backwards sheet is still backwards, so `verify_layout_nets.py` also judges every
declared `cathode:` against the simulated sign of the supply the diode sits on;
see *Rectifier polarity* under the equivalence gate below.

**Polarity gutter.** An electrolytic's `+` is a placed mark with reserved clear
space inside the body, and the value reflows into what is left. Set inline (as
it was until 2026-08-04) the mark's bar struck the first digit and `+25MFD`
read as `±25MFD` on every narrow can in the corpus.

**Which end the `+` is on.** Today the `+` is placed by position, not from
data. Both styles put it at the left end of a can lying along a row and at the
top of a standing can (`render_layouts.plus_side()`, the same orientation
reading as `cathode_side()`). Off the board only the era sheet marks a can,
and only on a top- or bottom-edge stub, over terminal `a`. So a negative-bias
filter can shows its `+` on the negative node, and a standing cathode bypass on
a board whose ground bus runs along the top row shows its `+` at ground.
`verify_layout_nets.py` holds each drawn `+` to the circuit's DC sign and
keeps the result in `reference/electrolytics.yaml` (see *Electrolytic
polarity* below). A `plus: a | b` field will replace the position rule,
sourced from the factory layout's own `+` where it is legible and from the DC
sign only where the layout prints none, and saying which. Until the renderer
draws from it, no layout declares one.

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
| `glyph` | Only for `kind: part` — `lamp` draws the pilot-lamp glyph; otherwise the body its BOM part type calls for (see body vocabulary above), at the same size a board part gets, with its value lettered on it |
| `value` | Only meaningful on a **ref-less** item, and only for `kind: part`. Values live in `bom.yaml`, keyed by ref, so a layout and the parts list can never disagree — and that stays true for every part the BOM knows. But the annotation layer draws parts the electrical model does not carry (a negative-feedback resistor stated only as a schematic *text note*, so it has no symbol and therefore no BOM ref), and those had no way to state a value at all: they shipped as blank bodies. A ref'd item ignores this field, so the two can never diverge. The value must be sourced in a comment; the lint fails a ref-less `kind: part` that has neither |
| `cathode` | Only for a `kind: part` whose BOM type is a diode/rectifier — `a` \| `b`, same meaning as on `parts[]` |
| `label_nudge` / `value_nudge` | For `kind: pot` — `[dx, dy]` px shifts for the name+value pair / the value alone, keeping the label's opaque halo. `kind: tube` accepts `label_nudge` too (the socket caption as one piece), for a caption whose whole natural band is occupied by a routed run. Same status as `parts[]`'s nudges: an authored starting point for the automatic placement pass, not the mechanism |
| `tap` | Only for `kind: pot` — `true` declares a **tapped** potentiometer: a fixed connection into the resistance element brought out as a fourth solder lug, addressed as `VRn.lug4`. Drawn as a fourth pip lettered `T` on the pot's flank (the left flank of a top/bottom-edge pot, the upper flank of a left/right-edge one), never as a member of the 1/2/3 fan, whose order is the part's own. The render refuses `tap: true` on a pot whose `bom.yaml` value states no tap, and refuses `.lug4` on a pot that does not declare one — a tap is a fact about the part, so both the parts list and the layout have to say it. The 6G6-B's Normal-channel Treble control (`350 kΩ, 70 kΩ tap` on the E-FB sheet) is the corpus's one tapped pot; its tap carries the 0.1 µF from the slope foot, and the schematic draws it on the matching four-pin `cx:POT_TAP` symbol |

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
| `"VR1.lug2"` | a potentiometer lug (`1` \| `2` \| `3`; `2` is the wiper). `"VR1.lug4"` is the **tap** of a pot the layout declares `tap: true` (see `offboard[]`); on any other pot it is an error |
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
| `style` | optional, and two values say "this conductor is heater wiring": `twisted` draws the run as a **pair** — two interleaved sinusoidal strands, the supply's two legs running together, the classic 6.3 V idiom; `heater` draws **one** conductor, which is what a single-ended supply has (one leg grounded at the transformer, each socket returning to chassis on its own — the 5F1 and AA764 sheets). Both render in the heater green (`green-yellow` gives the centre-tap strand where a drawing marks one), draw on the top layer dressed round each socket's flank, and get a dedicated legend entry rather than a colour swatch. |
| `via` | optional routing waypoints in **grid** units `[x, y]` where `x` = column axis, `y` = row axis (note this is horizontal-first — the opposite order from a part's `[row, col]`). `y < 0` routes above the board, `y > rows-1` below it (fractions allowed). Runs bend through these with rounded elbows; a couple of waypoints keep a lead in a clean lane clear of its neighbours. A deep lane (e.g. the twisted heater bus below the output harness) grows the drawing's bottom band automatically so it clears the legend. |

#### Heater chains

The heater/filament wiring is drawn as a heater-styled chain in the drawing's
daisy order: **transformer winding → pilot lamp → socket to socket**.
Heater/filament socket pins are read from `reference/tubes/<tube>.yaml` basing
(noval 4/5 with 9 the centre tap; octal power tubes 2/7; directly-heated
rectifiers 2/8 — those sit on the 5 V winding, not the 6.3 V chain). A heater
run onto a tube is **validated to land on a heater pin** — a heater lead routed
to a signal pin fails the render (and CI). The pilot lamp is an `offboard`
`kind: part` with a `lamp` glyph.

##### The `heaters:` block — the wiring is data, not an inference (2026-09-09)

Which two pins a supply's legs land on is a fact about the **amplifier**, not
about the valve, and for the corpus's commonest bottle the pin labels cannot
settle it. A centre-tapped heater wires the same three pins two ways:

| supply | connection groups | what the drawing shows |
|---|---|---|
| **6.3 V parallel** | `[4, 5]` and `[9]` | the two heater ends strapped together as one leg; the centre tap is the other leg |
| **12.6 V series** | `[4]` and `[5]` | the ends are the two legs; the centre tap carries no supply leg |

Until 2026-09-09 the renderer inferred a two-pin connection from the labels
`heater` and `heater-ct` alone, and always picked the second row. On an octal
6V6 (pins 2 and 7, no centre tap) that is right and there is no other answer.
On a 12AX7, 12AY7, 12AT7 or 12AU7 running 6.3 V — nearly every preamp bottle
here — it is backwards: it draws series wiring on a parallel amplifier, joins
what the sheet strapped as **one** leg across **both** legs, and leaves the
centre tap unwired. The 5F1 shipped exactly that (issue #30).

So the amplifier states its own configuration, in a `heaters:` block at the head
of `layout.yaml`, in the `net_map` idiom — reviewable data the gate reads rather
than code that guesses:

```yaml
heaters:
  - id: h63
    volts: 6.3
    winding: "6.3 V secondary — the transformer's green pair"
    grounded_leg: return          # feed | return | none | humdinger | winding-ct
    source: "…what the cited drawing shows, in a sentence…"
    pilot:                        # only where the sheet draws ONE lamp terminal
      PL1: { return: chassis, source: "…the sheet's one dot, in a sentence…" }
    sockets:
      V2: { feed: [7], return: [2] }        # octal: one pin per leg
      V1: { feed: [4, 5], return: [9] }     # noval at 6.3 V: ends strapped,
                                            #   centre tap the other leg
  - id: h5
    volts: 5.0
    winding: "5 V rectifier-filament secondary — the yellow pair"
    grounded_leg: none
    sockets:
      V3: { feed: [2], return: [8] }        # directly-heated rectifier
```

| Field | Means |
|---|---|
| `id` | short name for the circuit, used in gate output |
| `volts` | the supply voltage the **source** shows. Proved against the valve's own datasheet — see `heater.supplies` in `reference/tubes/<tube>.yaml` |
| `winding` | prose: which secondary this is |
| `grounded_leg` | `feed`, `return`, `none`, `humdinger`, or `winding-ct`. A single-ended supply grounds one leg at the transformer; a floating pair grounds neither, and a rectifier filament sitting at B+ must ground neither. `humdinger` is a floating pair whose return is an ARTIFICIAL centre tap — a hum-balance pot across the two legs with its wiper to chassis, or a pair of fixed resistors doing the same job — and it must name the part in a sibling `humdinger:` key (`humdinger: VR9`, or `humdinger: [R40, R41]`). The gate then proves the named part is drawn, reaches the ground bus, and spans BOTH legs: a grounded part touching one leg is not a centre tap, and "neither leg is grounded" on its own cannot be told apart from a return nobody drew. `winding-ct` is a floating pair whose return is the WINDING'S OWN centre tap — the blackface arrangement, and the 5F6-A's: the transformer's green-yellow lead is tied to the red-yellow HT centre tap and taken to chassis — and it must name that lead in a sibling `winding_ct:` key (`winding_ct: TR1.green-yellow`). The gate proves the named lead is a transformer lead of this board, is drawn, and reaches the ground bus, and that neither leg does |
| `winding_ct` | with `grounded_leg: winding-ct` only: the transformer lead that is the winding's centre tap, `<xfmr id>.<lead>` |
| `pilot` | optional, per pilot lamp: `PL1: { return: chassis, source: "…" }`. Declares that the sheet draws the lamp with ONE terminal — the feed arriving and the chain leaving on it — and that its return is the lamp holder's shell to the chassis, which the sheet does not draw and the board therefore does not draw either. Allowed only on a circuit that grounds a leg; see W4 below. The 5C1, 5E1, 5E3, 5F1, 5F2-A, 5F4 and 5F10 sheets all draw the lamp this way |
| `source` | what the cited drawing shows, so a reader can check the declaration against it |
| `sockets` | per socket, the **connection group** each pin sits in. `feed` and `return` are the two legs; naming which is which is the drawing's own choice and only matters for `grounded_leg` |

`pipeline/check_heaters.py` proves each declaration against the valve's
datasheet **and** against the runs actually drawn: supply voltage,
series-versus-parallel grouping, every heater pin accounted for, both legs
reached by a conductor, the two legs kept apart, and the grounded leg actually
grounded. See *Heater wiring is its own claim* below.

**A layout with no `heaters:` block is not checked, and its drawing says so.**
The renderer no longer invents the second landing for a centre-tapped socket: a
heater run there is drawn as the **single conductor its data names**, and
`check_heaters.py` prints the amp as `heaters NOT DECLARED` with its
centre-tapped sockets listed. An octal or rectifier socket keeps its two-pin
landing, because there the basing leaves no choice.

**A floating pair is drawn as two conductors.** The gate reads a run into nets
by its two named endpoints, so a `style: twisted` daisy — each hop naming one
pin at each socket — puts a socket's return pin on the next socket's feed pin and
cannot be proved. A supply whose both legs run socket to socket (`grounded_leg:
none`, `winding-ct` or `humdinger`) is therefore drawn as two `style: heater`
chains, one per leg, each hop naming the same leg's pin at both ends, with the
pilot lamp's two terminals on the two chains; the 5F6-A and the AA964 are the
pattern. A single-ended supply draws one chain and returns each socket to the
bus on its own (the 5E3, 6G2). The legend says which it is: two single
conductors on a floating supply are lettered "both legs float" with the return
the circuit declares, so the single-lead idiom cannot read as single-ended.

##### The marker an unestablished heater layer carries

Silence is printed to the gate, never counted as coverage — but a *visitor* does
not read the gate, and a drawing with nothing on it reads as settled. So every
layout whose heater circuit is not declared prints two markers, in both board
styles:

- the **legend key** for the heater ink gains `(leg grouping not established)`
  wherever a centre-tapped socket is drawn on an unestablished grouping — the
  legend is where a reader goes to learn what the green means, so it is where
  the caveat belongs;
- a **footer line** states what is actually in doubt and what is not: that the
  heater layer is the one part of the board not established against the
  amplifier's own drawing, that at the named centre-tapped valves it shows the
  two heater pins on opposite supply legs (the 12.6 V arrangement, against which
  a 6.3 V supply straps them into one leg and returns on the centre tap), and
  that **which sockets sit on the chain and the order it reaches them in are not
  affected**. Where a drawing carries a same-socket link that shorts the supply
  whatever the amplifier runs, that link is named too.

Flagged rather than suppressed, deliberately: the daisy order and the sockets on
the chain are still right, and deleting the layer would destroy correct
information to hide doubtful information. `Renderer.heater_provenance_note()`
composes the line; a declared circuit prints neither marker.

##### `heaters_unsourced` — when no factory sheet exists to read

Twelve boards in this corpus are **derived**: the amplifier's documentation is a
circuit drawing and no factory board-layout sheet was published or located, so
the placement and routing are the Codex's own (each says so in its `source` and
its caption). Their heater legs cannot be established from a factory drawing by
anybody, ever — which is a different gap from one nobody has read yet, and the
marker must not blur them. "Not established against the amplifier's own drawing"
implies a drawing is waiting to be read.

So such a layout declares the reason, and the drawing and the worklist both
change what they say:

```yaml
heaters_unsourced: >-
  JMI published no board-layout sheet for the AC15 and none was located; this
  board is the Circuit Codex's own arrangement, so no factory drawing can
  establish its heater legs.
```

- the **footer marker** opens "Heater layer: no factory board-layout drawing
  exists for this amplifier, so its heater wiring cannot be read off one", and
  closes by saying the valves on the chain are the circuit's own while the order
  is the drawing's convention — because on a derived board that order is not a
  factory fact either;
- the **worklist** carries `no_factory_layout_sheet` on the amp and splits its
  summary into `doubtful_sockets_pending_a_read` and
  `doubtful_sockets_no_factory_sheet`, so the number that measures the reading
  job counts only sockets a reader can actually clear.

A third kind of gap has its own key. Where a factory sheet exists but no located
copy resolves the socket pins, `heaters_pending:` (a reason string) records what
was tried, and the worklist carries it as `read_pending_because` — so the next
reader starts from the last attempt rather than from the backlog. The Champ
AA764 is the case: every capture of its layout PDF is the same 2171 px copy,
while the Vibro-Champ page of the same drawing family was found at 708 ppi and
declared.

A layout may hold both: `amps/ab763-super` establishes its 5 V rectifier winding
from the schematic and leaves the 6.3 V chain unestablished, and the marker then
states what was established, that the rest was not, and that there is no factory
board-layout drawing for the rest to be read off. Replace the key with a
`heaters:` block if the circuit drawing itself turns out to establish the wiring
— the AB763 Super's does for its 5 V winding, and does not for its 6.3 V chain,
which it only arrows.

##### The worklist is committed (`reference/heaters.yaml`)

`check_heaters.py --export` writes the corpus-wide state — per layout, whether it
declares a circuit, which centre-tapped sockets are drawn on an unestablished
grouping, and every same-socket link classified `shorted` (opposite legs at every
supply the valve's sheet lists) or `unclassified` (one leg at one supply and
opposite legs at another). A normal run **fails if the committed file is not what
a fresh run produces**, the same drift gate `reference/op-points.yaml` and
`reference/loadlines.yaml` carry: a worklist that misstates the size of its own
job is worse than none. Clearing an entry means reading that amplifier's own
drawing, declaring what it shows, correcting the runs, and re-exporting.

##### The heater pair is one object spanning both pins (2026-09-08)

A `style: twisted` run is **one pair**, and the renderer draws it as one. Two
conventions used to misrepresent correct authored data, and both are gone:

- both strands shared the polyline's single endpoint, so a *pair* terminated on
  one pin. An EL34 whose pins 2 and 7 each received a "twisted pair" showed
  **four** heater conductors where two belong;
- every hop dropped into a deep lane below the sockets and climbed back, so each
  socket appeared to drop two separate pairs to a rail — which reads as a short
  across its own heater pins — and the drop owned the lower band of every wide
  sheet.

The rule now:

1. **The pair spans BOTH supply legs at each socket it lands on.** The named pin
   identifies the socket and is still validated; the pin the pair's other strand
   reaches is the socket's **opposite leg** — from the `heaters:` block where the
   layout declares one, else the socket's two `heater`/`filament` pins where the
   basing leaves no choice (an octal 2/7, a rectifier filament 2/8). Where
   neither settles it, the run is drawn as the one conductor its data names, not
   as a pair with an invented landing. The twisted **axis** stops on a harness ring outside
   the socket, and from there each strand runs on to its own pin — in to the
   wrap radius, around the socket **clear of its caption band**, then radially
   to the pin, the way a dressed harness runs. The two pairs that meet at an
   intermediate socket wrap at different radii, so they read as two conductors
   rather than one doubled line.
2. **A socket-to-socket hop routes along the socket row**, ring to ring, and the
   authored `via` waypoints on such a hop — which existed to describe the old
   rail — are not used. Anything standing in the row (a speaker jack between two
   bottle positions, a transformer) is a keep-out the pair is dressed around,
   exactly as a socket is.
3. **A hop with a non-socket end** (the PT lead, the pilot lamp) keeps its
   authored waypoints, with their depth clamped to the heater lane just below
   the socket captions. The page's bottom band is reserved from that lane, not
   from the authored row, so the sheet is no longer sized for a drop it does not
   draw.
4. **A run whose two ends are the same socket** — a strap tying two pins into one
   leg, `pin 4` to `pin 5` for 6.3 V parallel — is ONE conductor. There is no
   pair to twist and nothing to fork: it draws as a single strand dressed round
   the flank. Note what such a run *claims*: it joins those two pins. On a
   centre-tapped noval at 6.3 V that is the strap the sheet shows; between an
   octal's two heater pins, or between a heater end and its own centre tap, it
   is a **short across the supply**, and `check_heaters.py` says so wherever the
   amp declares its configuration.

Nothing about which pins a run declares changes, so `_check_heater_endpoint()`
keeps its guarantee and `verify_layout_nets.py` sees exactly the same net (the
heater layer is excluded from DC equivalence in any case — see *Scope* below).

A heater strand has to cross the socket rim to reach a pin, so the **rim is
restruck over the wiring layer** and the pair's casing stops at the harness
ring: a conductor may pass behind a glyph outline, never leave a hole in one.

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

- **Socket keep-out on the heater pair.** The 6.3 V twisted pair is the topmost
  layer by design — it has to show its pin landings — so anything it crosses it
  also knocks out. Routed straight from lug to lug it therefore cut through the
  socket's own interior on every 9-pin valve in the corpus, wiping out pin
  numerals and the caption below. The router now treats each socket's pin ring
  (plus its numerals) as a keep-out and deflects the pair around the flank,
  leaving the lug radially and then turning along the ring — which is what a
  real harness does. Which pins the pair lands on is unchanged, so the
  equivalence gate sees exactly the same net, and no other run is touched.
- **Degenerate spurs are collapsed.** A waypoint list that doubles back on
  itself rendered as a hairpin with no terminus — a line that goes somewhere,
  comes to a point and returns says nothing about the circuit. Coincident
  points and out-and-back excursions are dropped before the polyline is drawn.
- **Transformer lead callouts.** A pigtail whose suffix is an era wire colour
  needs no callout — the ink and the legend say it. Where the source drawing
  shows uncoloured wire and the layout addresses the terminals by function
  (`T2.pri_p`, `T2.sec_h`), the terminal name is lettered beside the pigtail,
  so four identical black leads into four identical terminals are no longer
  four anonymous leads. Nothing is invented: the callout is the data's own key.
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
| **label struck by wire** | a run, twisted heater pair or bus segment passes through more than half a label's own width (min 12 px) inside its box — a wire running *along* the type, not across it |
| **label over glyph** | a label's box overlaps a part body, socket, pot, jack, transformer, terminal dot, lug pip or eyelet by more than 2.5 px in both axes |
| **labels collide** | two labels' boxes come within ~2.2 px of each other (abutting with no gap reads as one string — `100 kΩ` + `250 pF` printed edge to edge reads as `100 kΩ250 pF`) |
| **false punctuation** | a conductor's paint, or a glyph outline, lies inside a **value's** number-to-unit gap — the space in `25 µF`, `250 kΩ`, `16/8/4 Ω`. Ink there is not read as a crossing; it is read as a mark (`250,kΩ`). A **hard failure**, deliberately outside the transversal-crossing allowance that covers the rest of a label |
| **ambiguous label** | two off-board items of the same kind carry the same label (two `Volume` pots, two `Ch 2 in` jacks) — the drawing then has controls a reader cannot tell apart even where `bom.yaml` roles or the wiring do distinguish them |
| **no value** | an off-board `kind: part` carries neither a `bom.yaml` ref nor a `value:` — it renders as a blank body, telling a builder a component goes there and nothing else. (Board parts are already covered: an absent ref fails the render.) |

The last four are the **label lint** (added 2026-08-02). Until it existed the
gate certified the *wiring* half of the reference-drawing bar and was blind to
the labelling half — which is the half that degrades first as boards get denser,
and the only thing keeping it honest was hand-authored `nudge` / `label_nudge` /
`value_nudge`, unmeasured. Label boxes are estimated from the house text metrics
(`text_box()` in `render_layouts.py`) and inset ~1.6 px before testing, because
every label carries an opaque halo and a wire that merely grazes a box is not a
legibility defect. A transversal crossing is likewise *not* a failure — the type
is the topmost layer and the conductor runs unbroken behind it; a wire lying
**along** the type is. The one exception, and the reason the allowance is now
stated as an exception, is a **value's number-to-unit gap**: there is no glyph
there for the wire to pass behind, so what the reader sees is a mark between the
number and its unit. That is the false-punctuation check above, and it is hard.
Since 2026-08-31 the wire test
measures the conductor's **paint**, not its centreline: the box is grown
perpendicular to each segment by that conductor class's painted half-width
(2.4 px for a house run's 4.8 px casing, the bus's own half-width for bus
segments), so a run whose centreline passes a fraction of a pixel outside the
box can no longer drive its casing through the baseline of the type unreported
— while along the type the measure (and the transversal-crossing allowance) is
unchanged. The label placer scores candidates with the identical test, so a
placement the placer accepts is still one the gate accepts.

Because the lint must measure what actually ships, it renders the layout and
reads the renderer's own label and obstacle registries — the same geometry the
committed SVG carries.

**Both styles are linted.** The wiring checks run once: the sheet is a paint-only
re-skin, so its run geometry is bit-for-bit the house geometry. The three label
checks run **twice** — once against `Renderer`, once against `SheetRenderer`
(`lint_layout(dir, style="sheet", labels_only=True)`) — because the sheet sets
its type at its own sizes and standoffs and letters values on the bodies, so it
can collide where the house drawing does not. Sheet findings are tagged
`[sheet]`. The sheet registers each on-body value as an *obstacle* rather than a
label: it never moves and it sits on its own body by design, so the placer routes
queued labels around it and the label-over-glyph check reports any that still
land on it. Adopting the style corpus-wide surfaced exactly one such collision
(the Model 1987's `V5` socket label, fenced between the socket ring and a bank of
parallel runs); it was fixed by giving the sheet placer a few extra ladder rungs,
not by moving a wire.

Fix a wiring failure by **lane/via adjustment** — nudge a shared lane to a distinct
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
is remediated. The list is currently **empty**, and stays that way as the corpus grows:
every layout in `amps/` passes every check, wiring and label alike. A count
belongs in the gate's own output, not in prose that goes stale the next time a
board lands.

### Label placement (automatic)

Labels are **queued, not drawn**, while the geometry is built, and resolved in a
single final pass once every wire, body and terminal dot exists. Two properties
follow:

- **Type is the topmost layer; its HALO is not (2026-09-08).** The twisted
  heater pair draws above the sockets by design (it must show its pin landings),
  so a socket ID emitted with its glyph was painted over by the heaters however
  good its halo — a halo can only protect against what is drawn *before* the
  text. Labels are therefore resolved after every wire. But a halo painted on
  top of the drawing also knocks a hole in whatever it covers: a lead crossing
  the space inside `25 µF` was severed above and below the gap and read as a
  broken wire (five instances in one crop of the 5E3), and a socket caption
  erased the arc of the rim it sat on. Each label is now drawn as **two
  layers** — the opaque backing early, over the board and *under* every
  conductor and glyph outline, and the glyphs last. A wire runs unbroken behind
  the type, the type is still read against its own backing, and no halo can cut
  a conductor or a rim. See `text_layers()`.
- **Placement is measured.** Each label group (a ref and its value move
  together) is tried at its authored position first, then along a short
  deterministic ladder of small offsets, scored with the *same* tests and
  thresholds the lint uses; the first clear placement wins. A label still struck
  after its group is placed may slide on its own — the measured form of the old
  `value_nudge`, deliberately short so a value never travels far enough from its
  ref to be mis-attributed. The YAML nudges remain as the authored starting
  point.
- **Near misses break the ties (2026-08-04).** A conductor merely *crossing* a
  label transversally is not a lint failure — it runs behind the type, and
  demanding otherwise on a dense board would be unsatisfiable (a crossing
  inside a value's word gap is the exception, and is hard). But it is still
  the second-best placement, and the placer could not tell it apart from clear
  air: it stopped at the first rung with no *failures*, so a designator landed
  on a lead whenever that rung came first, even with untouched board a rung
  further along. Nearly every "label struck by a lead" finding in the
  2026-08-03 vision review was this. Placements are now scored as a
  **`(hard, soft)`** pair — `hard` is zero exactly when the gate is clean and
  still dominates, `soft` counts near misses (any conductor in the box at all,
  any glyph contact, any crowding of an already-placed label) and breaks ties
  among placements the gate would accept equally. The gate is unchanged; the
  drawing simply stops settling. The ladder gained a second tier of reaches to
  give it somewhere clean to go.
- **A settling pass, and a dense last resort (2026-09-08).** Groups are placed
  in queue order against whatever is already down, so a label could be squeezed
  by a neighbour that had not been placed when it chose — the 6G6-B's `RT2` and
  `RPF` values landed on each other that way. After the first pass every label
  is **re-scored against the finished arrangement**, and any that still carries
  a hard cost gets one more solo attempt. One pass, same order: bounded and
  deterministic. Both ladders also gained a systematic fine grid, ordered by
  travel and appended rather than prepended so every placement the older rungs
  already settle stays exactly where it was — clearing a word gap or a
  neighbour is usually a four-pixel problem that rungs stepping in 12s and 18s
  walk straight over.
- **A ref's debt counts double.** A ref anchors attribution; a value is the half
  that is meant to move (that is what `value_nudge` and the solo ladder are
  for). Where a group placement cannot be clean everywhere, the placer prefers
  to leave the violation on the label that can still slide out of it, and the
  solo pass then usually clears it.

Two placement rules are structural rather than searched:

- **Off-board labels sit away from the board.** A top-edge pot, jack or
  transformer carries its lugs, tip/sleeve or pigtails on its board-facing side,
  and every lead it carries fans down through that band — so a label printed
  there is struck by the item's own wiring *by construction*. Top-edge items
  label upward; every other edge already labels away from the board.
- **Board labels carry a board-toned halo.** Invisible on the board (it is the
  board's own tone), it cuts a clean gap where a hookup lead passes behind the
  type, and where a label overhangs the board edge — a tall filter can's ref has
  nowhere else to go — it keeps dark board ink legible against the dark well.

### `wire_legend` — colour-swatch overrides

```yaml
wire_legend:
  green: "green — 6.3 V heaters (single-ended; one leg grounded)"
  heater: "green — 6.3 V heaters (single-ended; one leg grounded at the transformer)"
```

Replaces a colour's bare swatch label in the drawing's wiring legend. Use it
where a colour carries a documented **function** in that drawing which the
automatic legend cannot infer. The reserved key `heater` replaces the heater
entry's own text instead of a colour swatch: the automatic entry says "6.3 V
heaters — twisted pair" or "— single lead", which names the idiom but not the
function, and a **single-ended** supply (one transformer lead grounded, the
other feeding the pilot lamp and every heater, each socket returning to chassis
on its own — the 5F1 and AA764) is worth saying out loud. A **floating** supply
needs no override: where every drawn circuit declares `grounded_leg: none`,
`winding-ct` or `humdinger`, the automatic entry adds the clause itself ("both
legs float; the winding's centre tap is grounded" on the 5F6-A and AA964),
because two single green conductors are that supply's two legs and "single
lead" alone is the single-ended idiom. The SVGs are served standalone
(`/layouts/<id>.svg`), so each must say what its colours mean without the
surrounding page.

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

## Wiring-equivalence gate (schema v3) — `net_map` + `wiring_claim`

`pipeline/verify_layout_nets.py` proves the drawn wiring is **electrically
equivalent** to the amp's verified netlist (`netlist.cir`) — the claim that
upgrades a layout from a careful drawing to *provably correct connectivity*. No
existing layout tool (DIYLC included) does this: a layout editor knows nothing of
the amp's netlist. The check builds a net graph from the drawing and a net graph
from the netlist and proves the drawing, restricted to what the netlist models,
is isomorphic to it — every modelled component's terminals on the same node, no
accidental shorts, no missing joins.

### How the layout net graph is built

Terminals: run/bus endpoints and part leads — board eyelets (`REF.a`/`REF.b`),
tube pins (`Vn.pinN`), pot lugs (`VRn.lugN`), jack terminals, transformer leads
(`T2.blue`), and 2-lead off-board parts. Joins: **each run joins its two
endpoints** (vias are the same wire); **the ground bus is one net**; **two leads
in the same board eyelet are joined** (an eyelet is one solder point — this is
load-bearing: a cathode-bypass cap can tie to its resistor purely by sharing an
eyelet); **a component's own two leads are never joined**.

### Why a netlist can't be matched 1:1 — and how the gate bridges it honestly

`netlist.cir` is a **DC-operating-point** model. It models every DC-open cap whose
**both** leads land on a named DC node — the inter-stage coupling caps (plate →
next grid), the cathodyne output couplers (tapping the balanced junction, not the
cathode pin), and the cathode-bypass caps — so their board placement is machine-
checked (they are open at DC and move no operating point, verified against
`voltages.yaml`). It still omits the parts with a lead **inside an abstracted
network** — caps into the volume / tone / mixer control networks, the negative-bias
front end (PT + rectifier + reservoir + selenium bias supply, replaced by ideal
sources), tone-stack internals, and transformer winding DCR (plate node = B+). So
the gate does not demand a naive net-for-net match; it **solves** a globally
consistent mapping —

- **tube pins anchor nodes** via `reference/tubes/<tube>.yaml` basing
  (plate / grid / cathode / screen → the subckt's pin order), with the
  section↔triode-half assignment solved;
- **two-terminal parts** have unknown `a`/`b`↔node orientation, resolved by
  constraint propagation from the anchors to one consistent whole;

— and reconciles the netlist's documented abstractions through an explicit,
reviewable `net_map` block (data, never a guess in code):

```yaml
net_map:
  anchors:            # terminal -> netlist node. Two terminals anchored to the
                      # SAME node declare a DC bridge the netlist collapses.
    T2.blue:  BP1     #   OT primary DCR omitted -> 6V6 plate node == B+1
    T2.bplus: BP1
    SPK: "0"          #   OT-secondary DCR folded into ground (the NFB return)
  series_bridge:      # DC-transparent parts the netlist omits (grid stoppers):
    R3: "68k input grid stopper — no DC grid current, grid == input node"
  netlist_unplaced:   # netlist elements with no discrete board part — reported
    RVOL: "volume pot VR1, modelled as a grid-leak (G1B -> 0)"
```

`anchors` handle the terminals the netlist gives no node to reach on their own
(transformer leads, the speaker jack); co-anchoring to one node declares the DC
bridge the netlist collapses. `series_bridge` shorts a DC-transparent part so the
netlist node runs through it. `netlist_unplaced` names netlist elements realised
off the board or by a control (input grid leaks at the jacks; pots the netlist
models as grid-leak resistors) — reported in coverage, never a failure.

`excluded_tubes` (map `socket_id: reason`) is the explicit, reviewable
declaration for a tube socket the DC netlist legitimately omits — a **tremolo /
vibrato oscillator** is a running phase-shift oscillator with no static operating
point, so it cannot be a quiescent stage the equivalence check verifies (see
`amps/ab763`, whose `netlist.cir` excludes the V5 12AX7 for exactly this reason).
A declared socket becomes an annotation-layer exclusion, printed loudly in the
tube tally like the rectifier — its 6.3 V heater is still validated onto heater
pins by the twisted-run check, and no signal pin is DC-checked. The declaration
never widens an exclusion to bury a failure: an **UNdeclared** unmodelled signal
tube still hard-fails (`_resolve_bottles` proves this in `--selftest`), so you
cannot hide a dropped tube by leaving it out of the block.

```yaml
net_map:
  excluded_tubes:
    V5: "12AX7 tremolo oscillator — no static DC operating point (excluded from netlist.cir)"
```

### Gate hardening (2026-07-19) — what the checker now proves

An adversarial audit planted 26 faults and 12 escaped. Each escape is closed at
the level that makes it structural, and the `--selftest` carries a regression
case for every one:

- **Valve aliases (H1).** A valve printed under its European name
  (`ECC83 (12AX7)`) resolves to its basing (`12ax7`) via `resolve_tube_slug`,
  built data-first from each `reference/tubes/*.yaml` `also_known_as` list.
  *Basing not found for a tube on a claimed amp is a hard failure* — never a
  silent skip.
- **Robust tube anchoring (H2/H3).** Each netlist tube **bottle** binds to a
  socket by id, else by a unique tube-**type** cross-reference, so a
  function-named instance (`XPIA`) still anchors without relying on its label.
  The run prints a full tube tally — every bottle *anchored* / *declared-excluded*
  (rectifier, or a `net_map.excluded_tubes` socket) / **UNANCHORED** — and an unanchored tube on a claimed amp fails CI.
- **Signal-path parts are modelled (H5/H6).** `netlist.cir` now carries the
  inter-stage parts it used to omit — the PI-plate→output-grid **coupling caps**,
  the **output-tube grid leaks**, and the **grid stoppers** — so the existing
  isomorphism check covers routing and push-pull phase **natively**: a coupler on
  the wrong power-tube grid, or crossed phase-inverter outputs, is now a
  `WRONG TERMINAL`. These caps are DC-open and the leaks carry no grid current, so
  the DC operating point is unmoved (verified against `voltages.yaml`).
- **Twisted-run validation (H7).** A `style: twisted` run is excluded as a heater
  run *only after* every tube endpoint is validated to be a heater/filament pin.
  Relabelling a signal run `twisted` to duck the check is a hard failure.
- **Anchor classification (H8).** Each `net_map` anchor is re-solved with it
  removed and printed **CONSTRAINING** or **REDUNDANT**, so an inert anchor can't
  read as if it holds the verdict up.
- **Unverified island, declared (H4).** The pot / mixer / tone control networks
  the netlist abstracts are printed **terminal-by-terminal** ("unverified
  island"), so what is *not* machine-checked is stated out loud rather than
  trusted in silence.

#### Round-2 re-audit closure (2026-07-19)

A second, adversarial re-audit found three more escapes; each is now closed:

- **Phantom-pin bug.** A netlist bottle carries a *function* name (`XPIA` →
  bottle `PI`) that need not equal its socket id (`V3`); the resolver
  cross-references it, but the solver was anchoring the terminal `PI.pin6` — a
  string that exists on **no** board net — instead of the physical `V3.pin6`. On a
  function-named bottle this silently checked terminals that weren't there. The
  fix threads **bottle → socket** into every pin-terminal formation, and a
  full-path self-test renames an amp's preamp bottles to prove correct wiring
  passes *and* a broken pin on the real socket is caught.
- **Unchecked-terminal enumeration.** The island declaration only listed nets
  carrying **no** netlist node, so a non-modelled lead — or a pot lug — landing on
  a net that *already* carries one (a rail, a cathode, ground) simply vanished: a
  mis-lugged pot ground or a bias resistor dropped on a live rail read as coverage
  by silence. The checker now enumerates **every** terminal of **every**
  non-modelled two-lead part and **every** pot lug, tagged *placement not
  DC-checked*, with the net each sits on **regardless of that net**, grouped under
  explicit headings (*control networks* / *DC-open parts* / *abstracted bias
  supply* / *PT-AC* / *heaters*). Silence can no longer read as coverage.
- **Shrinking the unchecked set.** Every DC-open cap the netlist can *honestly*
  absorb — both leads on nameable DC nodes — was added to `netlist.cir` across all
  eight amps (inter-stage couplers + cathode-bypass caps), moving them from the
  enumerated-but-unchecked set into the machine-checked set with zero operating-
  point drift (`verify_amps` stays 8/0/0). Genuinely-abstracted networks stay
  excluded — but are now enumerated, not silent.

#### Half-assignment hardening (2026-08-02) — H9

Bringing **AA964** to green found one more escape. The section↔triode-half solver
only enumerated the half-assignment for a bottle whose netlist models **both**
sections; a bottle modelling only **one** half was left at `unit=None`, no pin
resolved, and *none* of that socket's signal pins were anchored — so a lead moved
to a wrong pin on it passed. The AA964's V2 is exactly that shape (the cathodyne
half is modelled; its tremolo-oscillator half is the excluded one), and so is any
single-triode channel input.

The solver now enumerates the half for every multi-section bottle, one section or
two. A candidate unit must carry **every role the netlist instance uses**, so a
numbered detector-diode plate is never mistaken for a triode half — the 6AT6 in
`amps/5f10` keys its two diode plates unit 1/2 while the triode plate is the
unnumbered pin 7, and a naive unit list anchored the plate to pin 6 and split the
node. `--selftest` carries both cases: the planted wrong-pin fault on AA964's V2
must be CAUGHT, and 5f10's correct wiring must still PASS.

The **AA1164** landed on the same hole from the other side and is now the third
case, **HB**. Its cathodyne shares a 12AX7 with the (unmodelled) tremolo
oscillator too, and with no half assigned, a stage wired *across* the two halves
— plate on one, grid and cathode on the other, a real and buildable mistake —
passed silently. Because the solver now enumerates both halves and takes whichever
yields a consistent solve, all of a section's pins must land on the **same** one.
`aa1164` also joins the `--selftest` baseline set, so the mutation means
something.

### Heater wiring is its own claim (`check_heaters.py`)

Two claims, kept apart on purpose, because a green PASS on one says nothing
whatever about the other:

| claim | tool | what it proves |
|---|---|---|
| **DC equivalence** | `verify_layout_nets.py` | the drawn *signal* wiring is electrically equivalent to `netlist.cir` |
| **Heater wiring** | `check_heaters.py` | the drawn *heater* wiring is the supply, connection groups and returns the amp declares — and those are what its valve's datasheet permits |

Heaters are not in `netlist.cir` and are excluded from the DC comparison by
explicit rule, so until 2026-09-09 **no gate in this repository had ever looked
at a heater lead**. That is how the 5F1 shipped a drawing that joined its 12AX7's
two supply legs and left the centre tap unwired, under a `wiring_claim: verified`
badge that was, and remains, true about the thing it claims.

What the heater gate rejects, each with a planted fault in `--selftest`:

| Check | Trips when |
|---|---|
| **D1** | a declared pin is not a heater-class pin of that socket's valve |
| **D2** | a pin is declared on **both** legs, or a leg is empty |
| **D4** | the declared grouping leaves a heater pin on no leg — the 6.3 V/12.6 V configuration mismatch, which strands the centre tap |
| **D3** | every pin is on a leg but the **grouping** is not one the valve's sheet wires at that voltage |
| **W1** | a declared terminal that **no drawn conductor reaches** — a missing return |
| **W2** | the two legs are drawn on one net — a **bridge across the supply** |
| **W3** | the grounded leg does not reach the ground bus, or a leg reaches it that the declaration says is floating; on a `humdinger` circuit, either leg reaching ground, or the named artificial centre tap missing from the drawing, off the ground bus, or touching only one leg; on a `winding-ct` circuit, either leg reaching ground, or the named centre-tap lead not a transformer lead of this board, not drawn, or off the ground bus |
| **W4** | the pilot lamp is not ACROSS the supply: a terminal reached by no conductor, both terminals on one leg (a dark lamp — W1–W3 all pass it), or a terminal on a net carrying neither leg (the lamp drawn in series with the chain, which the 5E3 shipped). On a single-ended supply the grounded leg's net is the ground bus, so a return drawn to chassis is on that leg. A declared `pilot: {PL1: {return: chassis}}` is checked as a claim: only on a circuit that grounds a leg, the one drawn terminal on the fed leg, the other drawn to nothing — a declared-undrawn return the board draws anyway is stale and fails. A lamp touching no leg of a circuit is not that circuit's lamp |

A same-socket link joining two heater terminals is a **finding whatever style
the run carries**. Until 2026-09-09 only heater-styled runs were tested, which
left the worst case invisible: the 6G2 drew a plain conductor straight across
its rectifier's own 5 V filament pins, and neither gate objected — not the
heater gate, because the run was not green; not the DC gate, which excludes the
rectifier socket by rule. A short across a filament is a short whatever colour
it is drawn in, so the test is what a run *joins*, not how it is painted.

D1–D4 read `heater.supplies` in `reference/tubes/<tube>.yaml` — the voltages the
datasheet permits and the pin grouping each uses, cited to the sheet like every
other fact here. W1–W3 read the `runs` and `bus` the SVG is generated from, into
nets exactly as `render_layouts` resolves them.

An amp with no `heaters:` block prints `heaters NOT DECLARED`, lists its
centre-tapped sockets, and is **not checked** — and its drawing correspondingly
claims only the conductors its data names.

### The sheet and the board are each other's gate (`verify_sheet_vs_board.py`)

Both equivalence gates above are bounded by what `netlist.cir` models, and the
netlist is a DC model: **1,280 of the corpus's ~2,300 BOM passives have no netlist
element** — every cap with a lead inside an abstracted control network, every pot
end, the bias front end, the reverb and tremolo networks — so both gates skip them
by construction and say so in their scope lines. Nothing checked those parts
until 2026-09-10.

The schematic (`pipeline/draw_<id>.py`) and the board (`layout.yaml`) are
authored independently, so their net partitions are each other's witness: two
drawings of one circuit that disagree are wrong at least once, and the
disagreement names the part. `pipeline/verify_sheet_vs_board.py` builds both net
graphs, solves the mapping between them from the terminals both surfaces name,
and reports every part on which the partitions differ. It needs no netlist.
Nothing it prints says *which* surface is right — that is a source read — but it
says exactly where to read.

**Anchors** (terminals with one identity on both surfaces): the sheet's `<GND>`
label ↔ the ground bus; a section's electrode ↔ a socket pin, through
`reference/tubes` basing and the datasheet unit the sheet states for that
section; pot wipers (`VRn.2` ↔ `VRn.lug2`); jack contacts (`cx:JACK` pin 1 ↔
`J.tip`, pin 2 ↔ `J.sleeve`, for a sheet jack whose reference is a board jack id
— a board that wires only the jack *body* anchors the sheet's tip to it softly
and says so); and whatever `net_map.leads` declares (below). Two-terminal parts
and pot ends are unordered pairs resolved from the anchors by majority voting, so
a lone dissenter is the misplaced part and not the poisoner of everything on its
net. A section ↔ unit swap is searched for on every dual-section socket, and
reported once as `SECTION-SWAP` when exchanging the units removes at least two
findings. Heater and filament pins and the pilot lamp are excluded —
`check_heaters.py` owns them.

**The datasheet unit lives on the sheet.** A draw script that states which half
of the bottle a section draws (`s.triode("V1A", "12AX7", …, unit=2)`) now emits
it as a hidden symbol property, `Basing_unit`, so the gate reads the sheet and
not the script that drew it (the script is the fallback for a sheet not yet
regenerated to carry it, and the scope line says which was used). A sheet drawn
without `unit=` carries no such property and is byte-identical to before.

**What the board declares** — four ways a part on the sheet may legitimately be
absent from the board, each reviewable data, none inferred:

```yaml
net_map:
  netlist_unplaced:   # reused: a netlist element realised off the board
    RG1: "1 MΩ grid leak mounted at the input jack"
  series_bridge:      # reused (layout net_map, or the sheet's sch_map.yaml): a
                      # DC-transparent part the board does not place — its two
                      # sheet nets are ONE board net, the conductor runs through
    R1s: "68k grid stopper soldered at the socket lug"
  not_on_board:       # per part: on the sheet, neither placed nor wired here
    C4: "treble cap mounted at the pot, chassis side"
  leads:              # sheet terminal -> board terminal, for what no name can
                      # match: transformer pins are numbers on the sheet and
                      # colours on the board; a label may be a key too
    T2.1: T2.blue
    T2.2: T2.red
    "<TANK RET>": JTKO.tip
scope:
  not_drawn:          # board-scope rule, glob on the designator
    - { match: "VR*", why: "control-panel wiring is not on the eyelet board" }
```

A part on the sheet that the board neither places nor wires and that none of
these covers is `SHEET-ONLY … UNDECLARED`, a finding. A `not_on_board` entry
naming a part the board wires, a `not_drawn` rule matching nothing, or a `leads`
entry naming a terminal either surface lacks is a `STALE DECLARATION` finding —
a declaration never rots unnoticed. A declaration never widens to bury a
disagreement: a part the board *does* place is compared as a part whatever the
declarations say.

**Report classes**, one line each with the reason: `SECTION-SWAP` (per socket),
`SPLIT` (anchored terminals on one sheet net drawn as >1 board net), `MERGED`
(one board net carrying >1 sheet net — among anchors, or inferred when the
majority of parts on a sheet net land on a board net that already realises
another), `MISPLACED` (a part whose pair of nets differs, both surfaces' nets
printed in canonical names, a dangling board lead named as such), `UNRESOLVED`
(neither of a part's nets reaches an anchor — *not checked*), `SHEET-ONLY`
(declared / UNDECLARED), `BOARD-ONLY`, `POT-AS-RESISTOR` (a control the sheet
draws with the resistor symbol — no wiper to anchor, so it is not compared until
the sheet draws the pot), `STALE DECLARATION`, and `POT-ORIENTATION` as
information (a pot whose CW end the sheet draws at the bottom of its symbol).

**Worklist and gate.** `--export` writes `reference/sheet-board.yaml` — per amp,
the counts per class and the item lists — and a normal run **fails if that file
is not what a fresh run produces**, the same drift gate `heaters.yaml`,
`op-points.yaml` and `loadlines.yaml` carry. Findings themselves do not fail the
build yet: the corpus was surveyed, not cleaned, when the gate landed (see the
`summary` block of the worklist for the size of the job). `--strict` exits 1 on
any finding on an amp whose `sch_map.yaml` `schematic_claim` **and**
`layout.yaml` `wiring_claim` are both `verified`, and enters CI once the worklist
is clean for those amps. `--selftest` plants, on temp copies of the 5C1 and 5D3
(both clean at HEAD), a section swap (by swapped references and by a
`Basing_unit` property), a cap lead moved to another eyelet, bridged pot wipers,
a cut ground return, a deleted board part first undeclared, then declared per
part, then covered by a rule, a stale declaration and a dead rule, a grid leak
relettered as a control, and a `leads` map declared right, crossed and stale —
and requires each caught and each clean case passing.

```
python3 pipeline/verify_sheet_vs_board.py            # every amp + worklist drift gate
python3 pipeline/verify_sheet_vs_board.py 5f6a       # one amp, with reasons
python3 pipeline/verify_sheet_vs_board.py --report   # + scope lines
python3 pipeline/verify_sheet_vs_board.py --strict   # exit 1 on findings on claimed amps
python3 pipeline/verify_sheet_vs_board.py --export   # rewrite reference/sheet-board.yaml
python3 pipeline/verify_sheet_vs_board.py --selftest # planted-fault mutation test
```

### Scope, printed honestly every run

Heaters (heater-styled runs), the pilot lamp, and the PT / rectifier AC side are
**not** in `netlist.cir`; they are an annotation layer excluded by **explicit rules** —
never by widening an exclusion to bury a failure. The checker prints how many runs
it checked and how many it excluded and why, and which netlist elements have no
board part. It **enumerates every non-DC-checked terminal** — each non-modelled
part lead and pot lug, with the net it sits on, grouped by heading — so nothing is
trusted by silence. It also **echoes every `net_map` reconciliation it applied** —
each anchor (`T2.blue := BP1`) and each series-bridge (`R3`) — so a reviewer
reading the run sees exactly what the gate was handed, not a bare PASS.

### Verdict, gate, and self-test

Per amp: **PASS/FAIL with per-net diffs in builder language** — *extra connection*
(a short the netlist doesn't have), *missing connection* (a node the drawing
splits), *wrong terminal* (a lead on the wrong node). An amp whose `layout.yaml`
sets `wiring_claim: verified` is **hard-gated** (a failure fails CI); an amp
without the claim is **report-only**. This mirrors `meta.yaml`'s
`verification.status: verified` gate on the netlist itself.

**Rectifier polarity: report-only until its list is empty.** A board diode's
direction lives only in its `cathode: a|b` field, and the boards copied theirs
from sheets on which 25 of 68 diodes turned out to be drawn backwards
(2026-09-10). Every diode the board draws is judged through this board's own
node map by the rule the schematic gate applies (`judge_diode`; the clauses and
the walk to the supply node are in `docs/schematic-nets.md`). That covers
`parts[]` rows and off-board `kind: part` items whose BOM type is a diode or
rectifier. A diode is REVERSED when its cathode sits on a node the model holds
below −5 V, its anode on one above +50 V, or it is forward-biased by more than
1 V between two modelled nodes. On a board the walk crosses resistors, fuses
and chokes (board or off-board), every lug of a pot, and a switch with exactly
two terminals. A diode with no `cathode:` is drawn unbanded and listed as not
checked. Each run prints every REVERSED diode with its amp, ref and both nodes'
volts, per amp (`POLAR |`) and again in a closing summary. The findings sit
apart from the DIFF lines and change no verdict while a board-repair wave
corrects the copied fields. **The check becomes blocking once that list is
empty:** set `POLARITY_BLOCKING = True` in `verify_layout_nets.py`, and a
REVERSED diode then fails a board claiming `wiring_claim: verified` like any
other DIFF.

The same run reads each board rectifier's **feed** (`UNFED RECTIFIER`,
report-only under the same switch). A diode the model gives a role is walked
from its AC side to a lead of a power transformer: an `xfmr` stub whose label
or BOM part says power or mains. The walk crosses the same parts plus the
other diodes of its own stack or bridge, and never enters ground or a DC node.
The rule and its reasons are in `docs/schematic-nets.md` under *Rectifier
feed*.

**Electrolytic polarity: a drift-gated worklist, report-only.** Every
electrolytic the board draws, board-mounted or an off-board `kind: part`, is
read with the `+` the drawing puts on it (`plus_side()`). That `+` lead must
sit on the more positive DC node, judged through the same node map and walk as
the rectifier checks. Ground is 0 V, so a can with one lead on ground takes the
other node's sign. The joint of a series-stacked pair of cans lies strictly
between its two ends: a net carrying only the stack's leads and its balancing
resistors cannot sit outside them. Two leads within 0.1 V are not ordered.

Each can reads `right`, `WRONG`, `undecided`, or `unmarked` (no `+` drawn).
`--export` writes `reference/electrolytics.yaml`: the summary, then, per board,
every WRONG can with both leads' levels and every can not decided. A full run
fails when that file is stale, as it does for `reference/heaters.yaml`. The
verdicts join the DIFF lines only when `ELECTROLYTIC_BLOCKING` is set, which
happens once `plus:` is declared and drawn and the file's `wrong` list is
empty.

**Shorted parts: report-only, its own switch.** A two-lead part whose two leads
the drawing puts on one net is shorted out: a resistor that drops nothing, a
cap that couples or filters nothing, a diode that rectifies nothing. That
covers resistors, capacitors, diodes and chokes in `parts[]`, off-board
`kind: part` stubs other than the pilot lamp, and an off-board choke with two
leads. The equivalence proof sees such a short only for a part the netlist
models, and never for one a declaration joins on purpose: a `series_bridge`
grid stopper, or transformer leads anchored to one node. So this check reads
the board **as drawn**, runs, eyelets and the ground bus, before any `net_map`
union. Each finding names its cause: one eyelet, the ground bus, or a run or
shared eyelet. It found none on 6ce2a23 across 1,730 parts, so it keeps no
worklist. Its findings join the DIFF lines once `SHORTED_PART_BLOCKING` is set.

`verify_layout_nets.py --selftest` (wired into CI) plants the adversarial audit's
exact faults — one per proven hole class — and asserts each is caught: two
endpoints swapped, a run deleted, a run rerouted to a wrong pin; an aliased-valve
(ECC83) socket pin moved (H1); a PI→output coupler rerouted to the wrong grid
(H5); crossed phase-inverter outputs (H6); a signal run relabelled `twisted`
(H7); plus resolver/island/anchor unit checks for a function-named tube anchoring
by type (H2), an unanchorable tube failing hard (H3), the island being declared
(H4), and anchors classified CONSTRAINING vs REDUNDANT (H8). The round-2 closure
adds a **full-path phantom-pin** case (a function-named bottle's correct wiring
must pass *and* a broken pin on its real socket must be caught) and two
**enumeration** cases (a mis-lugged pot ground and a bias resistor dropped on a
live rail must surface in the unchecked-terminal report even though neither is a
DC short). A rectifier-polarity case sets the 5F8-A's bias rectifier to
`cathode: b` and requires REVERSED, reached through the unmodelled RB1, with an
unchanged wiring verdict while the list is report-only. It then sets
`cathode: a` and requires *confirmed*. A feed case requires that same
rectifier to read *fed* as committed, and UNFED once its run from
`PT.red-blue` is deleted. Electrolytic cases take the 5F4's bias filter C15
and the AB763's cathode bypass CKN1 as drawn (WRONG) and with the `+` turned to
the other lead (right), and the 5F4's cathode bypass C3 both ways. They also
require the JTM100's series-stacked C13 and C14 to be decided through their
joint. Shorted-part cases plant a run between one resistor's two eyelets
on the 5F1 and a run between an off-board stub's two terminals; each must be
reported, the 5F1 as committed must report none, and a `series_bridge`
stopper is never read as shorted. A gate that can't catch planted faults is
decoration.

```
python3 pipeline/render_layouts.py                 # (re)generate SVGs first
cd pipeline && python3 verify_layout_nets.py       # check all amps
python3 verify_layout_nets.py --analyze 5e3        # dump both net graphs for one amp
python3 verify_layout_nets.py --selftest           # planted-fault mutation test
```

The pilot verified **5F1** and **5E3** (`wiring_claim: verified`). Bringing 5E3 to
green caught six real drawing errors the equivalence gate existed to find: three
shared-eyelet shorts (the B+2 rail, the phase-inverter junction, and a mic-channel
grid each shorted to the ground bus where a vertical resistor's lower eyelet
collided with a horizontal part), and three B+ tap errors (the 6V6 screens drawn
to B+1 instead of B+2, and the V2A and cathodyne plate loads to B+2 instead of
B+3) — each confirmed against the schematic, then fixed in the wiring and re-drawn.

## `leads[]` — legacy soft leads (deprecated)

Superseded by `runs`. Endpoints are an eyelet `[row, col]` or an `offboard` `id`;
drawn as faint suggestion curves. Kept only for back-compat.
