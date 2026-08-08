# Proposal — wire `check_value_consistency.py` into CI

**Status:** IMPLEMENTED 2026-08-08, on the integration of the four parallel
units this page was written during. The precondition it set for itself — a
corpus with zero disagreements — held on the merged tree, so the two steps
below are now in `.github/workflows/ci.yml` and the gate list in `AGENTS.md`.
The gate blocks from this commit on. Nothing here grants any circuit
`verified`; that remains the maintainer's alone (AGENTS.md rule 4).

## What it gates

One part states its value on up to four surfaces — `schematic.kicad_sch`,
`bom.yaml`, `layout.yaml`, and the era sheet lettering generated from
`bom.yaml`. `validate.py` proves the *designators* line up. Nothing proved the
*quantities* do. `pipeline/check_value_consistency.py` normalises every surface
to a physical quantity (ohms, farads, henries, volts, watts, or a designation
token) and reports every designator whose surfaces disagree.

## Why now

The corpus is clean. On the merged tree, 2026-08-08:

```
$ python3 pipeline/check_value_consistency.py
7 findings across 34 amps: UNSTATED=2, UNLINKED=5
  0 disagreement(s) — gated (--strict)
  7 declared-gap row(s) — informational: a value the source did not print, or an
    annotation with no designator to cross-check against

$ python3 pipeline/check_value_consistency.py --strict ; echo $?
0
```

One declared gap fewer than when this page was drafted: the 5F4 and 5F6-A
schematics stopped naming their negative-feedback network in a text note and
now draw it, so `RNF`, `VR6` and their wiper caps carry designators the gate can
cross-check instead of ref-less annotations it could only report. A gap closes
by drawing the part, never by relaxing the gate.

The 28 findings this gate reported before that work were: nine spellings of a
valve name the corpus's own equivalence table already reconciles (`7025` /
`12AX7`, `5Y3-GT` / `5Y3GT`); four dual-can values that claimed 50 µF where the
amp has 25 (6G4 CK1D/CK1I/CK2D/CK2I); five schematic values carrying the era's
dashed value-voltage shorthand, which reads as one number and means two (5E5-A
C_NFB and C_tr1, 6G2 C11–C13); two from a category bug that filed the 6G5's
optocoupler as a resistor; and eight declared gaps. All but the last eight are
fixed; the eight are honest and are not gated (below).

## What `--strict` does and does not fail on

`--strict` exits 1 on **disagreements** — `MISMATCH`, `UNIT-MISMATCH`,
`VOLTS-MISMATCH`, `WATTS-MISMATCH`, `TYPE-MISMATCH`, `AMBIGUOUS`. Those are
defects: two surfaces state different things about one part and a builder cannot
tell which to trust.

It deliberately does **not** fail on `UNSTATED` or `UNLINKED`. Those are the
archive keeping its own honesty rule (AGENTS.md rule 5): a value the source
never printed (`"electrolytic (value not printed)"`), or an annotation the
electrical model carries no designator for (a negative-feedback resistor the
schematic states only as a text note). Gating them would push a contributor to
invent a number to clear the gate, which is the exact failure this project
exists to avoid. They are printed on every run so they stay visible.

## The gate proves it can still fail

`--selftest` runs 29 pairs — the ones that must agree and the ones that must
NOT — through the same normalisers, so the script cannot quietly degrade into
"no findings, ever" as more notations get absorbed:

```
$ python3 pipeline/check_value_consistency.py --selftest
selftest: 29/29 pairs behaved as specified
```

Planted faults it catches include a decade slip (`100 kΩ` vs `10k`), a unit slip
(`250 pF` vs `250n`), a wattage clash (`470 Ω · 5 W` vs `470 1W`), a working-
voltage clash, a wrong valve (`12AX7` vs `12AY7`), a wrong part number
(`1N4007` vs `1N4148`) and a wrong impedance ratio (`5k:8` vs `4k:8`).

## Proposed change

Two lines in `.github/workflows/ci.yml`, after `test_era_values.py`:

```yaml
      # A part states its value on up to four surfaces (schematic symbol, BOM,
      # layout label, era sheet lettering). validate.py proves the designators
      # line up; this proves the quantities do. The self-test runs first because
      # a gate that cannot fail proves nothing.
      - run: python pipeline/check_value_consistency.py --selftest
      - run: python pipeline/check_value_consistency.py --strict
```

and one line in the AGENTS.md gate list:

```
python3 pipeline/check_value_consistency.py --selftest && \
python3 pipeline/check_value_consistency.py --strict   # cross-surface quantities agree
```

Runtime: ~1.5 s for the whole corpus locally; it reads `bom.yaml`, `layout.yaml`
and the kiutils-parsed schematic, all of which other
steps already load.

## Cost of saying yes

Every future PR that changes a value must change it on every surface that states
it, or CI fails with the designator and both readings. That is the point, and it
is the same contract `render_og.py --check` and `export_loadlines.py --check`
already impose for other generated artifacts.

## Cost of saying no

The corpus is clean today and nothing holds it there. The four 6G4 dual-can
values had been live long enough to reach the site; so had the two era-shorthand
schematic values. Report-only found them; only a gate keeps them out.
