# Lettering conventions — one per surface

A single part in this corpus states its value on four surfaces, each written for
a different reader:

| surface | file | example |
|---|---|---|
| parts list, prose, house drawing | `bom.yaml`, `notes.md`, `layout.svg` | `0.005 µF · 600 V` |
| schematic | `schematic.kicad_sch` symbol `Value` | `.005u` |
| era layout sheet | `layout-sheet.svg` (generated) | `.005-600` |
| reference designator | every file, shared key | `C6` |

Until 2026-08-08 each of those surfaces carried **several** conventions at once.
One capacitor rendered `5n` on the schematic, `0.005 µF · 600 V` in the parts
list and `0.005 µF` on the board (5E3 C6, 5D3 C6). One dropper printed
`4,700 Ω` beside neighbours printing `15 kΩ` (5F6-A RD1). Three surfaces, three
notations, one part — and a reader with no way to tell whether the difference
meant anything.

`pipeline/check_value_consistency.py` proves the surfaces name the same
**quantity**. This page defines how each names it, and
`pipeline/test_era_values.py` gates that — the half a quantity check cannot see,
because `4,700 Ω` and `4.7 kΩ` agree perfectly and still read as if two people
wrote the parts list.

---

## 1. House units — `bom.yaml`, prose, the house drawing

Engineering prefix chosen so the mantissa reads **1…999**:

```
470 Ω      4.7 kΩ      1 MΩ      2.2 MΩ
```

Never comma-grouped thousands (`4,700 Ω`), never a bare ohms value at or above
1 kΩ (`1000 Ω`), never a unit that forces a leading run of zeros
(`0.0005 µF`).

Capacitance is written in **pF below 1000 pF** and in **µF at and above it**:

```
10 pF      250 pF      500 pF      0.001 µF      0.02 µF      25 µF
```

Secondary ratings follow in `·` fields, in this order — working voltage,
wattage, tolerance:

```
0.02 µF · 400 V        470 Ω · 5 W        220 kΩ · ½ W · 5%
```

A multi-section can spells both sections out, joined by ` + `:

```
25 µF + 25 µF · 25 V
```

That form means **this designator is the whole can**. Where a can's two sections
carry two different designators, each designator states its own section's value
and the packaging is stated in `role:` — otherwise the parts list claims 50 µF
of bypass where the amp has 25.

A repeat count is a parenthetical, and it is a count of parts, not a rating:

```
8 µF · 150 V (×2)
```

A parenthetical is a **gloss**: an aside for a reader with the page in front of
them. It never appears on a component body — see §4.

**Gated by:** `test_era_values.house_form()` (documented cases + a sweep of
every value in every `amps/*/bom.yaml`).

---

## 2. Schematic drafting shorthand — `schematic.kicad_sch`

The schematic uses drafting shorthand, in the idiom of the tradition the drawing
belongs to. That idiom is declared per amp:

```yaml
# amps/<id>/meta.yaml
conventions:
  notation: us      # or uk; default us
```

### `us` — American drafting practice

The unit letter is the **SI prefix of the house unit**, so the schematic and the
parts list name the same decade:

| house | schematic | not |
|---|---|---|
| `0.005 µF` | `.005u` | `5n` |
| `500 pF` | `500p` | `.0005u` |
| `1.5 kΩ` | `1.5k` | `1500` |
| `1 MΩ` | `1M` | `1000k` |

### `uk` — British drafting practice

Used by this corpus's Hiwatt and Marshall entries, whose source drawings are
lettered that way. RKM / IEC 60062 infix for resistors and nanofarads for film
capacitors:

```
2k2      1M8      470R      47n      1n0
```

This is a real convention with its own internal consistency, not a drift, so it
is **declared** rather than normalised away.

### Both idioms

Secondary ratings are **separate space-separated fields carrying their own unit
letter**:

```
470 5W        20u 600V        100k 1W 5%
```

Never the era's dashed shorthand (`100u-25`, `.1u-200`) — that belongs to the
sheet lettering and nowhere else; left on a schematic it reads as one number and
means two. Never the house middot (`20u·600V`) — that is the parts-list
separator.

A role note may follow a value (`1M vol`, `22k NFB`); it is annotation, not part
of the quantity.

**Gated by:** `test_era_values.sch_form_errors()` (documented cases + a sweep of
every symbol `Value` in every `amps/*/schematic.kicad_sch`, resolved against
that amp's declared idiom).

---

## 3. Era sheet lettering — `layout-sheet.svg`

Generated, never authored: `render_layouts.era_pair()` letters it from
`bom.yaml`. Documented for readers on
`/reference/guides/units-conventions/` and in the block comment above
`era_pair()`.

```
resistors    820 Ω -> 820      15 kΩ -> 15K      1 MΩ -> 1MEG
             a wattage suffix only above the sheet's implied ½ W:
             250 Ω · 5 W -> 250-5
film / mica  0.02 µF · 400 V -> .02-400      0.005 µF -> .005
             sub-nanofarad parts in picofarads: 250 pF -> 250PF
electros     25 µF -> 25MFD, working voltage on its own line: 450V
dual cans    25 µF + 25 µF -> 25/25MFD
counts       (×2) -> a separate "2 REQ'D" line beside the part
```

`era_pair()` is strict: a token it cannot read as a resistance or a capacitance
comes back as the house string. That is correct — it must never invent a
quantity — but the house string it hands back is the value with its
parenthetical **gloss removed** (`body_value()`), because a gloss is a sentence
and a component body is 30 px wide. Before that rule existed, `selenium (silicon
diode in modern builds)` was lettered in full on a diode body and ran off the
left edge of the 5E4-A's page.

Transformers and chokes go through `iron_value()` instead: the glyph letters the
part's **identity** (a factory part number, an impedance ratio, an inductance)
and everything else — a measured DCR estimate, a provenance note — becomes a
numbered footnote in the drawing's footer. `~110 Ω DCR (est.)` is a measurement
note, not a winding spec, and is exactly the field a builder must not mistake
for one.

Where the corpus has read an electrical rating for iron whose parts-list value is
a bare factory number, it is stated once, in `meta.yaml`, and lettered with the
number:

```yaml
iron:
  T3: "≈4 kΩ a-a : 8 Ω"      # keyed by bom.yaml designator
```

Nothing is invented: an amp with no `iron:` block letters the part number alone,
and the gap stays visible.

**Gated by:** `test_era_values.py` (documented cases + a round-trip sweep: every
lettered value must name the same physical quantity as its house string).

---

## 4. Reference designators

**Two schemes ship in this corpus and both stay.**

The 5F1, 5E1, 5F2-A, 5C1 and AA764 number their parts straight through —
`R1…R13`, `C1…C10` — the way their own factory sheets do. The 5E3, 5F10, 5F4 and
most of what came after carry a role code instead: `RD1` is rail dropper 1,
`RL4` a plate load, `CK1` a cathode bypass. Neither is wrong. The first is what a
small drawing with a dozen parts wants; the second is what a hundred-part
Bassman needs before a reader can hold it in their head.

Normalising the corpus onto one of them was the alternative, and it was
rejected. Renaming `R1` to `RG1` across a netlist, a schematic, a layout, a
voltage chart and its prose changes nothing a builder can measure, breaks every
link anyone has made into this archive, and — worse — erases which scheme the
amp's own source drawing used.

What a reader needs is to be **told**, on the page, which scheme they are
reading. So each amp declares it:

```yaml
conventions:
  designators: sequential | functional
```

* `sequential` — every designator is class + running number (`R7`, `C10`, `V2`).
  Reading one tells you nothing about the part's job; the parts list does.
* `functional` — designators carry a role code (`RD1`, `RL4`, `CK1A`).

The declaration is **checked against the parts list**, not trusted:
`validate.check_conventions()` derives the scheme from the designators and fails
when the two disagree. One designator carrying a role code makes the whole
parts list a functional one to read.

One rule binds both schemes: **a designator is what a drawing letters on a
part.** Letters and digits only — no underscores, spaces or punctuation.
`C_tr1` and `C_NFB` are source-code identifiers that leaked out of a generator
script onto a published board, and a builder looking for `C_NFB` on a factory
sheet will not find it. Amps that still carry such names hold a **declared,
dated waiver** in `validate.DESIGNATOR_WAIVERS`, printed with the reason — the
same mechanism `pipeline/lint_waivers.yaml` uses for a drawing collision that
cannot yet be resolved. A waiver is never silent and never open-ended.

---

## Where each rule is enforced

| rule | gate |
|---|---|
| house units in `bom.yaml` | `pipeline/test_era_values.py` |
| value grammar + physics bands | `pipeline/test_era_values.py` |
| schematic idiom per amp | `pipeline/test_era_values.py` |
| era sheet lettering + round-trip | `pipeline/test_era_values.py` |
| designator scheme declared and true | `pipeline/validate.py` |
| designators are letterable | `pipeline/validate.py` |
| `iron:` keys name real designators | `pipeline/validate.py` |
| surfaces agree on the **quantity** | `pipeline/check_value_consistency.py` |
| drawn value inside the page | `pipeline/check_layouts.py` (lint check h) |
