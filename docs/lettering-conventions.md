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

### Lettering is never rotated (2026-09-08)

**A body may stand; its lettering is always read with the page the right way
up.** No factory layout sheet turns type through 90°, and until 2026-09-08 this
one did: a standing resistor carried `1.5K` or `820` rotated up its body, and a
standing electrolytic stacked a rotated `25MFD` beside a rotated `25V` — the
AC30's C1 was the worst of them. The house drawing had always done this
correctly, so the sheet was a regression against its own sibling.

A standing part now letters **horizontally beside the body**, ref over value,
flipped to the near side at the right board edge; an electrolytic's capacitance
and working voltage take two horizontal lines rather than two rotated columns.
The same rule governs a standing off-board `kind: part` glyph. `_fixed_text()`
has no `rotate` argument any more, which is the enforcement: there is no way to
letter a rotated string.

### A value goes on the body only where the body is clear

The sheet's promise is *the value is on the part*, and the fallback when it will
not fit is a placed label beside it. Two things bound "fit": the body's own
width, and — for an off-board `kind: part`, whose two terminals stand on the
body when its minimum width exceeds their spacing — the **clear span between
those terminals** (`_val_on_body()`). The 5F6-A's C16 lettered `.1-200` straight
across its own two terminal dots and read `:1-200`; it now letters beside the
part, and every value that does clear its terminals is unchanged.

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

## 5. Tube pin numbers on the schematic

A designator says *which* valve. The number beside an electrode says **which
socket pin to put a probe on**, and it is the one piece of lettering a
technician uses more than any other. The corpus published none until 2026-09-08,
because both tube symbols hid their pin numbers — and the numbers they hid were
*positional* (a triode's plate was pin 1, a pentode's screen pin 3), true of no
valve in this corpus except by accident. A 6V6's plate is pin 3.

Those positional numbers stay in the symbol library. They are the pipeline's own
pin identity — the handle `sch_nets`, `verify_schematic_nets` and
`sch_open_pins.yaml` use to name a pin (`V6A.3` is that sheet's cathode whatever
valve sits in the socket) — and they are never shown. The **real** number is
lettered beside the electrode, at 1.1 mm, smaller than a value, from the
corpus's own basing data in `reference/tubes/<slug>.yaml`.

Three rules, and the third is the one that matters:

1. **The valve comes from the symbol's own value** — `12AX7`, `ECC83 CF`,
   `12AX7 (7025)` — resolved through the alias map the layout renderer already
   uses (`render_layouts.resolve_tube_slug`, built from each tube file's
   `also_known_as` plus a supplement). One resolution rule, corpus-wide: a valve
   printed under its European name numbers the same as under its American one.
2. **The half comes from the drawing, because a section letter is a
   designator and not a basing fact.** `V1A` and `V1B` are chosen by whoever
   drew the sheet, and this corpus's convention — followed in the prose of the
   5F4, JTM45, JTM100, 6G6-B and S1484 — is that **A is the first half in
   signal order**. That is a naming rule. Which physical half of the glass a
   stage uses is a different question, and only the factory sheet answers it.

   The two usually coincide, because a first stage usually sits on the half
   the datasheet calls unit 1, and where the drawing says nothing the letter
   of rank *n* takes the unit of rank *n* (A → unit 1, B → unit 2). Sometimes
   they do not coincide, and then **the drawing states the unit it means**:

   ```python
   # The factory schematic prints its own pin numbers on this socket: the input
   # stage's plate is pin 1 at +200 V and its cathode pin 3 at +1.8 V, so the
   # input stage is the valve's unit 2 …
   v1a = s.triode("V1A", "12AX7", 46, 62, unit=2)
   ```

   Declared data with its source beside it, not a rule guessed in code. The
   letter never moves: a Champ's input stage stays `V1A`, because that is what
   a technician writes. Four amps carry such a declaration today — the 5E4-A,
   5F6, AA764 and AA764-vibro — and stating the unit on one half of a bottle
   while leaving the other on the default is an error the library raises,
   since both halves would then claim the same pins.

   **The units themselves are the datasheet's, and they are not pin order.**
   RCA's 12AX7-A, the sheet this corpus cites, prints under *Basing
   Designation for BOTTOM VIEW … 9A*:

   > Pin 1 – Plate of Unit No.2  Pin 6 – Plate of Unit No.1
   > Pin 2 – Grid of Unit No.2   Pin 7 – Grid of Unit No.1
   > Pin 3 – Cathode of Unit No.2  Pin 8 – Cathode of Unit No.1

   So unit No.1 is pins 6/7/8. A 5Y3's unit 1 is pin 6 while a GZ34's is pin
   4 — the same two valves in opposite pin order — which is why nothing
   positional can stand in for reading the data, and why a rule like "the A
   half is whichever has the lowest pins" (KiCad's own ECC83 symbol) is wrong
   here: it was tried, and it contradicted this corpus's own layout drawings
   on the same amp page.
3. **Silence beats a guess.** A valve whose basing the corpus does not carry
   prints no number. A *sectioned* electrode on a bottle whose designator names
   no section and whose drawing states no unit — a dual triode lettered plainly
   `V1` — prints no number either, because nothing has said which half it is
   and inventing one would put a wrong pin on a verified sheet. (A `unit=`
   declaration is enough on its own: it rescues an unlettered bottle.)
   Unsectioned electrodes on the same
   bottle still print: a 6AT6's triode plate is pin 7 whatever its diode units
   do. An electrode the valve brings out on two pins prints both (`2,8` on a
   5Y3's filament, `4,8` on a 7591's screen).

Heater pins are not lettered: these sheets do not draw heater wiring, and a
number with no electrode beside it names nothing.

Passives keep their pin numbers hidden. A resistor's designator and value are
what a reader needs; its pin 1 is an artefact of the symbol.

**Glyphs.** The symbols letter what they can and draw the rest. Plate is a plain
bar; the cathode is a bracket with a filament hairpin under it, so the two ends
of a bottle are never confusable; the pentode's screen sits on its own row above
the control grid, stepped up to its right-hand lead. A rectifier is drawn as
**one** envelope over however many sections the sheet places for it, with one
filament strand running the width of the bottle — a 5Y3 is one valve with two
plates, not two valves. The envelope is a schematic graphic rather than symbol
ink (the two halves are separate placed symbols), so it states the outline
colour the viewer gives every other bottle; that is a deliberate coupling to the
renderer's theme, noted at `schematic_lib.GLASS_RGBA`. On an indirectly heated
rectifier the strand is the heater-cathode the datasheet ties together.

**Line weight follows paper size.** The corpus spans 169 mm to 682 mm of paper
and every sheet is fitted into the same viewer box, so one millimetre weight
renders four times lighter on the widest sheet than on the narrowest. Each sheet
therefore states its own line group, scaled to land at a constant rendered
weight (`schematic_lib.ink_width`, `junction_d`) — ISO 128's rule, and the
reason the AB763 Twin's outlines no longer dissolve. Text is deliberately *not*
scaled with it: lettering is placed against a collision lint tuned to 1.27 mm.

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
| tube pin numbers are the valve's real basing | `reference/tubes/*.yaml` is the only source; `pipeline/check_schematics.py` proves the lettering prints over nothing |
