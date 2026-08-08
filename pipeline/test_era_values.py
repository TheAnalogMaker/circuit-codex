#!/usr/bin/env python3
"""Unit tests for the sheet style's era value lettering (CI gate).

The sheet render letters a part's value ON its body, in the shorthand the era
factory drawings used and this archive documents on
/reference/guides/units-conventions/. render_layouts.era_pair() implements it.
Two properties matter enough to gate:

  1. it letters the documented cases exactly — including the ones that give the
     shorthand its point (4,700 Ω -> "4.7K" never "4700", 0.02 µF · 400 V ->
     ".02-400", 25 µF -> "25MFD", 250 pF -> "250PF");
  2. it REFUSES anything it does not understand, returning the house tokens
     untouched — a value it cannot parse must never be mangled into a wrong
     number, and every descriptive value in the corpus ("selenium", a factory
     transformer part number, "presence/NFB network") is one of those.

Property 2 is checked twice: against a fixed list of awkward strings, and
against every value in every amps/*/bom.yaml — the sweep at the end asserts
that each real corpus value either letters to a form that round-trips back to
the same physical quantity, or comes back byte-identical to the house string.

    python3 pipeline/test_era_values.py
"""
from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_value_consistency import load_sch_values      # noqa: E402

from render_layouts import (          # noqa: E402
    _era_number, _parse_farads, _parse_ohms, body_value, category, era_count,
    era_pair, iron_value, part_count, primary_value,
)

ROOT = Path(__file__).resolve().parent.parent

# (house value, category) -> (body lettering, second line)
CASES = [
    # --- resistors: bare number, K, MEG -------------------------------------
    ("4,700 Ω", "res", ("4.7K", None)),          # comma-grouped ohms normalise up
    ("470 kΩ · ½ W", "res", ("470K", None)),
    ("1 MΩ", "res", ("1MEG", None)),
    ("1 MΩ · ½ W", "res", ("1MEG", None)),
    ("15 kΩ · ½ W", "res", ("15K", None)),
    ("820 Ω · ½ W", "res", ("820", None)),
    ("47 Ω · ½ W", "res", ("47", None)),
    ("100 kΩ · ½ W", "res", ("100K", None)),
    ("1.5 kΩ · ½ W", "res", ("1.5K", None)),
    ("2.2 MΩ · ½ W", "res", ("2.2MEG", None)),
    ("10 MΩ · ½ W", "res", ("10MEG", None)),
    ("1 kΩ", "res", ("1K", None)),
    # tolerance fields are ignored, wherever they sit in the value
    ("100 kΩ · 5 % · ½ W", "res", ("100K", None)),
    ("220 kΩ · ½ W · 5%", "res", ("220K", None)),
    # --- resistors: the era's ohms-watts dash, ONLY above the implied ½ W ----
    ("250 Ω · 5 W", "res", ("250-5", None)),     # the 5E3's cathode resistor
    ("470 Ω · 1 W", "res", ("470-1", None)),
    ("22 kΩ · 3 W", "res", ("22K-3", None)),
    ("10 kΩ · 1 W", "res", ("10K-1", None)),
    ("100 Ω · ½ W", "res", ("100", None)),       # implied wattage: no suffix
    # --- film / mica caps: value-voltage, no leading zero -------------------
    ("0.02 µF · 400 V", "film", (".02-400", None)),
    ("0.05 µF · 600 V", "film", (".05-600", None)),
    ("0.1 µF · 200 V", "film", (".1-200", None)),
    ("0.0022 µF · 400 V", "film", (".0022-400", None)),
    ("0.02 µF", "film", (".02", None)),
    ("0.005 µF", "film", (".005", None)),
    ("0.68 µF", "film", (".68", None)),
    ("0.047 µF · 600 V", "film", (".047-600", None)),
    # sub-nanofarad parts are lettered in picofarads, as the era wrote them
    ("250 pF", "mica", ("250PF", None)),
    ("500 pF", "mica", ("500PF", None)),
    ("10 pF", "mica", ("10PF", None)),
    ("0.0005 µF (500 pF)", "mica", ("500PF", None)),   # same part, two ways
    ("0.001 µF", "film", (".001", None)),              # 1000 pF: µF side of it
    # --- electrolytics: MFD on the can, working voltage on its own line -----
    ("25 µF", "electro", ("25MFD", None)),
    ("25 µF · 25 V", "electro", ("25MFD", "25V")),
    ("16 µF · 450 V", "electro", ("16MFD", "450V")),
    ("8 µF · 150 V", "electro", ("8MFD", "150V")),
    ("250 µF · 6 V", "electro", ("250MFD", "6V")),
    # a REPEAT COUNT is not a rating: it comes off the working-voltage line and
    # is lettered separately (era_count), so no can claims two voltages
    ("16 µF · 450 V (×2)", "electro", ("16MFD", "450V")),
    ("8 µF · 150 V (×2)", "electro", ("8MFD", "150V")),
    # --- multi-section cans: one part, two capacitances ---------------------
    ("25 µF + 25 µF", "electro", ("25/25MFD", None)),
    ("25 µF + 25 µF · 25 V", "electro", ("25/25MFD", "25V")),
    ("50 µF + 50 µF · 450 V", "electro", ("50/50MFD", "450V")),
    ("25 µF + 50 µF · 450 V", "electro", ("25/50MFD", "450V")),
    # --- refusals: house tokens come back untouched -------------------------
    ("selenium · silicon diode in modern builds",
     "other", ("selenium", "silicon diode in modern builds")),
    # a parenthetical GLOSS is not part of the value and is never lettered on a
    # body — it is a sentence, and on a 30 px part it ran off the page
    ("selenium (silicon diode in modern builds)", "diode", ("selenium", None)),
    # an "(est.)" marker on a RATING is not a gloss to discard — it is the
    # archive saying the figure is inferred, and rule 5 publishes that
    ("25 µF · 25 V (est.)", "electro", ("25MFD", "25V (est.)")),
    ("presence/NFB network", "res", ("presence/NFB network", None)),
    ("Fender 125P1B · 320-0-320 V · 6.3 V · 5 V",
     "xfmr", ("Fender 125P1B", "320-0-320 V")),
    ("6.3 V", "other", ("6.3 V", None)),               # pilot lamp
    ("≈350 Ω DCR", "choke", ("≈350 Ω DCR", None)),
    ("20 H", "choke", ("20 H", None)),
    ("1 MΩ-A", "other", ("1 MΩ-A", None)),             # pot taper suffix
    ("250 kΩ-A", "other", ("250 kΩ-A", None)),
    ("8 kΩ : 8 Ω", "xfmr", ("8 kΩ : 8 Ω", None)),
    ("1/4 in", "other", ("1/4 in", None)),
    ("12AX7", "tube", ("12AX7", None)),
    ("", "res", ("", None)),
]


# --------------------------------------------------------------------------
# Value grammar + per-class plausibility.
#
# era_pair() only has to letter what it is given; it cannot tell a plausible
# quantity from an implausible one. Two escapes got through on that boundary and
# reached the site: a 20-600 pF HT reservoir (the factory's "20-600" shorthand for
# 20 µF at 600 V, with the shorthand kept and the unit reattached as picofarads),
# and a 30-450 µF · 450 V filter (the same shorthand, plus the voltage restated,
# so the part claimed two of them). Both round-tripped or were refused, so the
# lettering sweep passed while the DATA was wrong.
#
# So the corpus values themselves get a grammar and a physics band. Categories
# that carry a quantity — resistors and the three capacitor classes — must state
# it in house units, in this shape:
#
#     <number> <unit> [· <voltage>] [· <wattage>] [· <tolerance>] [(annotation)]
#
# and it must land inside what that class of part physically is. Everything else
# (transformers, chokes, jacks, valves, "selenium") is descriptive by design and
# is checked only for the tokens that are never a value at all.
QUANTITY_CATS = {"res", "film", "mica", "electro"}

_NUM = r"\d[\d,]*(?:\.\d+)?"
_UNIT = r"(?:Ω|kΩ|MΩ|pF|nF|µF)"
_RE_QTY = re.compile(rf"^{_NUM}\s*{_UNIT}$")
# A multi-section can is one physical part carrying two values, and the factory
# drawings write it as such. The house form spells both out — "25 µF + 25 µF" —
# because the alternatives in use here ("25/25 µF", "50+50 µF dual can",
# "25/50 µF (dual can)") are four spellings of one thing, and two of them read as
# a fraction. Each section is banded separately.
_RE_MULTI = re.compile(rf"^{_NUM}\s*{_UNIT}(?:\s*\+\s*{_NUM}\s*{_UNIT})+$")
# Something that was MEANT to be a number: a value opening with a digit or a bare
# decimal point. A value that opens with a word ("electrolytic, value not
# printed", "presence/NFB network") is honest descriptive data — the drawing
# prints no figure — and era_pair refuses it verbatim, so the grammar leaves it be.
_RE_LOOKS_NUMERIC = re.compile(r"^[.\d]")
_RE_VOLT_FIELD = re.compile(rf"^{_NUM}\s*V$")
_RE_WATT_FIELD = re.compile(rf"^(?:{_NUM}|½|¼)\s*W$")
_RE_TOL_FIELD = re.compile(rf"^{_NUM}\s*%$")
_RE_DASH_PAIR = re.compile(r"\d\s*-\s*\d")
_RE_PAREN = re.compile(r"\s*\(([^()]*)\)\s*$")

# (min, max) for the quantity a part of this class carries, and for its printed
# working voltage. Wide enough that no real vintage part is near an edge, tight
# enough that a misattached unit or a misplaced decimal cannot survive: an
# electrolytic reservoir is never picofarads, and a mica is never microfarads
# by the handful.
BANDS = {                    # farads or ohms
    "res":     (Decimal("1"), Decimal("1E8")),                 # 1 Ω … 100 MΩ
    "film":    (Decimal("1E-11"), Decimal("2E-6")),            # 10 pF … 2 µF
    "mica":    (Decimal("1E-12"), Decimal("1E-8")),            # 1 pF … 10 000 pF
    "electro": (Decimal("1E-7"), Decimal("1E-2")),             # 0.1 µF … 10 000 µF
}
VOLT_BANDS = {
    "film":    (Decimal("100"), Decimal("1000")),
    "mica":    (Decimal("100"), Decimal("1000")),
    "electro": (Decimal("3"), Decimal("700")),
}
# Tokens that are never a value. "n/a" was lettered verbatim onto three pieces of
# iron on one board; every other amp in the corpus describes the part instead.
NON_VALUES = {"n/a", "na", "n\\a", "-", "?", "tbd", "unknown"}


def grammar_errors(value: str, cat: str) -> list[str]:
    """House-string grammar + plausibility for one BOM value. [] when clean."""
    v = str(value).strip()
    if not v:
        return []                       # an absent value is a schema question
    if v.lower() in NON_VALUES:
        return [f"{v!r} is not a value — describe the part "
                f"(its rating, its winding, or the designator the drawing prints)"]
    if cat not in QUANTITY_CATS:
        return []                       # descriptive categories are free-form
    if _RE_DASH_PAIR.search(v):
        return [f"{v!r} carries the era's dashed value-voltage shorthand; "
                f"bom.yaml holds house units ('20 µF · 600 V') and the sheet "
                f"style letters the shorthand from them"]
    body = _RE_PAREN.sub("", v).strip()
    fields = [f.strip() for f in body.split("·")]
    head = fields[0]
    if not (_RE_QTY.match(head) or _RE_MULTI.match(head)):
        if not _RE_LOOKS_NUMERIC.match(head):
            return []                   # descriptive by design; era_pair refuses it
        return [f"{v!r}: a {cat} value must open with a quantity in house units "
                f"(number + Ω/kΩ/MΩ/pF/nF/µF, sections joined by ' + '), "
                f"not {head!r}"]
    errs = []
    for f in fields[1:]:
        if not (_RE_VOLT_FIELD.match(f) or _RE_WATT_FIELD.match(f)
                or _RE_TOL_FIELD.match(f)):
            errs.append(f"{v!r}: field {f!r} is not a voltage, wattage or "
                        f"tolerance — annotations belong in `role`")
    # --- plausibility: is this the kind of quantity this class of part carries?
    lo, hi = BANDS[cat]
    for section in [s.strip() for s in head.split("+")]:
        qty = _parse_ohms(section) if cat == "res" else _parse_farads(section)
        if qty is None:
            errs.append(f"{v!r}: quantity {section!r} did not parse")
        elif not (lo <= qty <= hi):
            errs.append(f"{v!r}: {section} is outside what a {cat} part is "
                        f"(band {lo}…{hi} in base units) — check the unit")
    vb = VOLT_BANDS.get(cat)
    if vb:
        for f in fields[1:]:
            if _RE_VOLT_FIELD.match(f):
                volts = Decimal(f.split()[0].replace(",", ""))
                if not (vb[0] <= volts <= vb[1]):
                    errs.append(f"{v!r}: {f} is outside a {cat} part's working-"
                                f"voltage range ({vb[0]}…{vb[1]} V)")
    return errs


# Worked examples for the grammar itself, including the two shapes that reached
# the site. Each is (value, category, should_pass).
GRAMMAR_CASES = [
    ("20 µF · 600 V", "electro", True),
    ("30 µF · 450 V", "electro", True),
    ("16 µF · 450 V (×2)", "electro", True),
    ("0.02 µF · 400 V", "film", True),
    ("250 pF", "mica", True),
    ("0.0005 µF (500 pF)", "mica", True),
    ("220 kΩ · ½ W · 5%", "res", True),
    ("4,700 Ω · 1 W", "res", True),
    ("Fender 125P1B · 320-0-320 V · 6.3 V · 5 V", "xfmr", True),
    ("selenium · silicon diode in modern builds", "other", True),
    # the two the audit found live
    ("20-600 pF (filter, ×N per drawing)", "electro", False),   # dashed shorthand
    ("30-450 µF · 450 V", "electro", False),                    # ditto + a 2nd voltage
    # the class of thing the physics band exists for
    ("600 pF", "electro", False),                               # picofarad reservoir
    ("20 µF · 1500 V", "electro", False),                       # no such can
    ("0.02 F", "film", False),                                  # unit slipped
    # and the token that is not a value
    ("n/a", "xfmr", False),
    ("n/a", "res", False),
    # an annotation smuggled into the value instead of the role
    ("25 µF · dual-can pair", "electro", False),
]


# ===========================================================================
# ONE CONVENTION PER SURFACE
# ===========================================================================
# The same part states its value on four surfaces, and until 2026-08-08 each
# surface had drifted into several conventions at once. One capacitor rendered
# "5n" on the schematic, "0.005 µF · 600 V" in the parts list and "0.005 µF" on
# the board (5E3 C6, 5D3 C6). One dropper printed "4,700 Ω" beside neighbours
# printing "15 kΩ" (5F6-A RD1). Three surfaces, three notations, one part — and
# a reader with no way to tell whether the difference means anything.
#
# check_value_consistency.py already proves the surfaces name the same
# QUANTITY. This proves they name it in the same WAY, which is the half a
# quantity check cannot see: "4,700 Ω" and "4.7 kΩ" agree perfectly and still
# make a parts list read as if two people wrote it.
#
#   bom.yaml / prose / the house drawing
#       House units, engineering prefix chosen so the mantissa reads 1…999:
#       470 Ω, 4.7 kΩ, 1 MΩ. Capacitance in pF below 1000 pF and in µF at and
#       above it: 250 pF, 0.001 µF, 0.02 µF. Never comma-grouped thousands
#       ("4,700 Ω"), never a unit that forces a leading run of zeros
#       ("0.0005 µF"). Secondary ratings follow in '·' fields.
#
#   schematic.kicad_sch symbol Value
#       Drafting shorthand, in the idiom of the tradition the drawing belongs
#       to (meta.yaml `conventions.notation`, default "us"):
#         us — the unit letter is the SI prefix of the house unit, so the
#              schematic and the parts list name the same decade: 0.005 µF is
#              ".005u", never "5n"; 500 pF is "500p", never ".0005u"; 1.5 kΩ is
#              "1.5k", never "1500".
#         uk — British drafting practice, which this corpus's Marshall, Hiwatt
#              and Vox entries are drawn in: RKM/IEC 60062 infix for resistors
#              ("2k2", "1M8", "470R") and nanofarads for film caps ("47n",
#              "1n0"). It is a real convention with its own consistency, not a
#              drift, so it is DECLARED per amp rather than normalised away.
#       Secondary ratings are separate space-separated fields carrying their
#       own unit letter — "470 5W", "20u 600V" — never the era's dashed
#       shorthand ("100u-25") and never the house middot ("20u·600V"). The dash
#       form belongs to the sheet lettering and nowhere else; left on a
#       schematic it reads as one number and means two.
#
#   the era layout-sheet render
#       era_pair(), documented at the top of this file and on
#       /reference/guides/units-conventions/.
#
# Everything below gates those rules against the real corpus.
_SI = {"Ω": "", "kΩ": "k", "MΩ": "M", "pF": "p", "nF": "n", "µF": "u", "μF": "u"}
_RE_HOUSE_QTY = re.compile(r"^([\d.,]+)\s*(Ω|kΩ|MΩ|pF|nF|µF|μF)$")
# Drafting shorthand for a single quantity: a number, an optional unit letter.
_RE_SCH_HEAD = re.compile(r"^[.\d][\d.,]*([a-zA-ZΩµ]*)$")
_RE_RKM = re.compile(r"^\d+[kMRunp]\d+$")
# Forms that state more than one part or more than one section, and are read
# elsewhere (check_value_consistency) rather than here.
_RE_SCH_MULTI = re.compile(r"[+/]|^\d+\s*[x×]", re.I)
_RES_SUFFIX = {"": "", "R": "", "k": "k", "K": "k", "M": "M", "MEG": "M", "meg": "M"}
NOTATIONS = ("us", "uk")


def house_form(cat: str, value: str) -> str | None:
    """The canonical house string for a value, or None when it already is one
    (or is not a quantity at all)."""
    if cat not in QUANTITY_CATS:
        return None
    head = _RE_PAREN.sub("", str(value)).strip().split("·")[0].strip()
    if "+" in head:                     # a twin can: each section is banded
        parts = [h.strip() for h in head.split("+")]
        want = [house_form(cat, h) or h for h in parts]
        return " + ".join(want) if want != parts else None
    m = _RE_HOUSE_QTY.match(head)
    if not m:
        return None
    if cat == "res":
        q = _parse_ohms(head)
        if q is None:
            return None
        if q >= 1000000:
            want = f"{_era_number(q / Decimal(1000000))} MΩ"
        elif q >= 1000:
            want = f"{_era_number(q / Decimal(1000))} kΩ"
        else:
            want = f"{_era_number(q)} Ω"
    else:
        q = _parse_farads(head)
        if q is None:
            return None
        want = (f"{_era_number(q / Decimal('1E-12'))} pF" if q < Decimal("1E-9")
                else f"{_era_number(q / Decimal('1E-6'))} µF")
    return None if want == head else want


def sch_form_errors(house: str, sch: str, cat: str, notation: str) -> list[str]:
    """Does a schematic Value follow this amp's drafting idiom? [] when it does.

    Only values whose parts-list form is a plain quantity are checked — a
    transformer's ratio, a pot's taper and a diode's material are designations
    and are compared by check_value_consistency, not here."""
    hm = _RE_HOUSE_QTY.match(_RE_PAREN.sub("", str(house)).strip().split("·")[0].strip())
    if not hm:
        return []
    want = _SI[hm.group(2)]
    raw = str(sch).strip()
    if not raw or _RE_SCH_MULTI.search(raw.split()[0]):
        return []                       # multi-section / repeat count: read elsewhere
    if "·" in raw:
        return [f"{raw!r}: a schematic states secondary ratings as separate "
                f"space-separated fields ('470 5W', '20u 600V'); '·' is the "
                f"house-units separator and belongs in bom.yaml"]
    head = raw.split()[0]
    if _RE_RKM.match(head):
        if notation == "uk":
            return []
        return [f"{raw!r}: RKM infix notation ('2k2') is the British drafting "
                f"idiom; this amp is drawn in the 'us' idiom, so write '2.2k' "
                f"— or declare conventions.notation: uk in meta.yaml"]
    if re.match(r"^[.\d][\d.,]*[a-zA-Zµ]*-\d", head):
        return [f"{raw!r}: the dashed value-voltage shorthand belongs to the era "
                f"SHEET lettering, which render_layouts.era_pair() generates; on "
                f"a schematic it reads as one number and means two"]
    m = _RE_SCH_HEAD.match(head)
    if not m:
        return []                       # not a bare quantity; nothing to compare
    got = m.group(1)
    if cat == "res":
        got = _RES_SUFFIX.get(got, got)
    else:
        got = got.rstrip("Ff")
        if notation == "uk" and got in ("n", "p", "u"):
            return []                   # nF is idiomatic British for film caps
    if got != want:
        return [f"{raw!r}: the parts list states {house!r}, so the schematic "
                f"names the same decade as {want or 'a bare number'!r} — "
                f"got {got!r}"]
    return []


def notation_of(amp_dir: Path) -> str:
    meta = yaml.safe_load((amp_dir / "meta.yaml").read_text()) or {}
    n = str(((meta.get("conventions") or {}).get("notation") or "us")).lower()
    return n if n in NOTATIONS else "us"


# Worked examples for the two surface conventions, as (house, schematic,
# category, notation, should_pass).
SURFACE_CASES = [
    ("0.005 µF", ".005u", "film", "us", True),
    ("0.005 µF", "5n", "film", "us", False),        # 5E3 C6 / 5D3 C6, as shipped
    ("0.005 µF", "5n", "film", "uk", True),         # …and idiomatic on a Hiwatt
    ("500 pF", "500p", "mica", "us", True),
    ("500 pF", ".0005u", "mica", "us", False),      # 5F10 C3, as shipped
    ("1.5 kΩ", "1.5k", "res", "us", True),
    ("1.5 kΩ", "1500", "res", "us", False),         # 5F6 RGS1/RGS2, as shipped
    ("2.2 kΩ", "2k2", "res", "uk", True),           # DR103 / 2204 house idiom
    ("2.2 kΩ", "2k2", "res", "us", False),
    ("20 µF", "20u 600V", "electro", "us", True),
    ("20 µF", "20u·600V", "electro", "us", False),  # 6G6-B C10/C11, as shipped
    ("100 µF", "100u-25", "electro", "us", False),  # 5E6-A C14, as shipped
    ("50 µF", "2x50u", "electro", "us", True),      # a repeat count, read elsewhere
    ("25 µF + 25 µF", "25u+25u", "electro", "us", True),
]

HOUSE_CASES = [
    ("4.7 kΩ", "res", True),
    ("4,700 Ω", "res", False),          # 5F6-A RD1, as shipped
    ("3,300 Ω", "res", False),          # 5E6-A RB1, as shipped
    ("1000 Ω", "res", False),           # 6G2 RD1, as shipped
    ("470 Ω", "res", True),
    ("1 MΩ", "res", True),
    ("250 pF", "mica", True),
    ("0.0005 µF", "mica", False),       # 6G2 C3, as shipped
    ("2500 pF", "mica", False),         # 6G5 CFB1, as shipped
    ("0.001 µF", "film", True),
    ("0.02 µF", "film", True),
    ("25 µF + 25 µF", "electro", True),
]


def check(label: str, got, want) -> list[str]:
    if got == want:
        print(f"  ok   {label:38s} -> {got!r}")
        return []
    print(f"  FAIL {label:38s} -> {got!r}, expected {want!r}")
    return [label]


def round_trips(value: str, cat: str, lettered: str) -> bool:
    """The lettering names the same physical quantity as the house string."""
    # '0.0005 µF (500 pF)' — the parenthetical restates the same value in the
    # other unit, so it is dropped before the quantity is read off.
    prim = re.sub(r"\s*\([^()]*\)\s*$", "", primary_value(value)).strip()
    prim = re.sub(r"\(\s*[x×]\s*\d+\s*\)", "", prim).strip()
    # A twin can round-trips SECTION BY SECTION: "25 µF + 25 µF" -> "25/25MFD"
    # states two capacitances and the check has to read both, or a can lettered
    # 25/50 would pass against a parts list saying 25 + 25.
    if "+" in prim:
        want = [_parse_farads(t.strip()) for t in prim.split("+")]
        m = re.fullmatch(r"([\d./]+)MFD", lettered)
        if not m or any(w is None for w in want):
            return False
        got = [Decimal(t) * Decimal("1E-6") for t in m.group(1).split("/")]
        return got == want
    ohms, farads = _parse_ohms(prim), _parse_farads(prim)
    body = lettered.split("-")[0] if "-" in lettered else lettered
    if ohms is not None:
        if body.endswith("MEG"):
            back = Decimal(body[:-3]) * 1000000
        elif body.endswith("K"):
            back = Decimal(body[:-1]) * 1000
        else:
            back = Decimal(body)
        return back == ohms
    if farads is not None:
        if body.endswith("PF"):
            back = Decimal(body[:-2]) * Decimal("1E-12")
        elif body.endswith("MFD"):
            back = Decimal(body[:-3]) * Decimal("1E-6")
        else:
            back = Decimal("0" + body) * Decimal("1E-6")
        return back == farads
    return False


def main() -> int:
    failures: list[str] = []
    print("era lettering — documented cases:")
    for value, cat, want in CASES:
        failures += check(f"{value} [{cat}]", era_pair(value, cat), want)

    print("\nvalue grammar — documented cases:")
    for value, cat, want_ok in GRAMMAR_CASES:
        got = grammar_errors(value, cat)
        ok = not got
        if ok == want_ok:
            print(f"  ok   {value!r:44s} [{cat}] "
                  f"{'accepted' if ok else 'rejected: ' + got[0][:70]}")
        else:
            print(f"  FAIL {value!r:44s} [{cat}] expected "
                  f"{'accept' if want_ok else 'reject'}, got {got}")
            failures.append(f"grammar {value!r}")

    # --- corpus sweep: every real BOM value, lettered or left alone ----------
    print("\ncorpus sweep — every amps/*/bom.yaml value:")
    n_letter = n_house = 0
    for bom in sorted((ROOT / "amps").glob("*/bom.yaml")):
        for item in (yaml.safe_load(bom.read_text()) or {}).get("items", []):
            value, cat = str(item.get("value", "")), category(item.get("part", ""))
            for msg in grammar_errors(value, cat):
                failures.append(f"{bom.parent.name}:{item.get('ref')} grammar")
                print(f"  FAIL {bom.parent.name} {item.get('ref')}: {msg}")
            body, _second = era_pair(value, cat)
            if body == body_value(primary_value(value)):
                n_house += 1                      # refused: house token, gloss off
                continue
            n_letter += 1
            if not round_trips(value, cat, body):
                failures.append(f"{bom.parent.name}:{item.get('ref')} {value!r}")
                print(f"  FAIL {bom.parent.name} {item.get('ref')}: "
                      f"{value!r} -> {body!r} is not the same quantity")
    print(f"  {n_letter} value(s) lettered and round-tripped, "
          f"{n_house} left in house units")

    # --- one convention per surface -----------------------------------------
    print("\nsurface conventions — documented cases:")
    for house, sch, cat, notation, want_ok in SURFACE_CASES:
        got = sch_form_errors(house, sch, cat, notation)
        if (not got) == want_ok:
            print(f"  ok   {house!r:16s} vs {sch!r:12s} [{cat}/{notation}] "
                  f"{'accepted' if not got else 'rejected'}")
        else:
            print(f"  FAIL {house!r:16s} vs {sch!r:12s} [{cat}/{notation}] "
                  f"expected {'accept' if want_ok else 'reject'}, got {got}")
            failures.append(f"surface {house!r} vs {sch!r}")
    for value, cat, want_ok in HOUSE_CASES:
        got = house_form(cat, value)
        if (got is None) == want_ok:
            print(f"  ok   house {value!r:16s} [{cat}] "
                  f"{'canonical' if want_ok else f'-> {got!r}'}")
        else:
            print(f"  FAIL house {value!r:16s} [{cat}] expected "
                  f"{'canonical' if want_ok else 'rewrite'}, got {got!r}")
            failures.append(f"house {value!r}")

    print("\nsurface conventions — corpus sweep:")
    n_house_ok = n_sch_ok = 0
    for amp in sorted(d for d in (ROOT / "amps").iterdir()
                      if d.is_dir() and not d.name.startswith("_")):
        bom_path = amp / "bom.yaml"
        if not bom_path.exists():
            continue
        notation = notation_of(amp)
        bom = {}
        for it in (yaml.safe_load(bom_path.read_text()) or {}).get("items", []):
            ref = it.get("ref")
            if ref and ref != "—":
                bom[ref] = it
            value, cat = str(it.get("value", "")), category(it.get("part", ""))
            want = house_form(cat, value)
            if want:
                failures.append(f"{amp.name}:{ref} house units")
                print(f"  FAIL {amp.name} {ref}: parts-list value {value!r} is not "
                      f"house units — write {want!r} (mantissa 1…999, no comma "
                      f"grouping, pF below 1000 pF and µF at and above it)")
            else:
                n_house_ok += 1
        sch = amp / "schematic.kicad_sch"
        if not sch.exists():
            continue
        exact, base = load_sch_values(sch)
        for ref, vals in sorted(exact.items()):
            stem = ref[:-1] if (len(ref) > 1 and ref[-1].isalpha()
                                and ref[-2].isdigit()) else ref
            rec = bom.get(ref) or bom.get(stem)
            if not rec:
                continue
            cat = category(rec.get("part", ""))
            if cat not in QUANTITY_CATS:
                continue
            house = str(rec.get("value", ""))
            for v in vals:
                for msg in sch_form_errors(house, v, cat, notation):
                    failures.append(f"{amp.name}:{ref} schematic notation")
                    print(f"  FAIL {amp.name} {ref} [{notation}]: {msg}")
                else:
                    n_sch_ok += 1
    print(f"  {n_house_ok} parts-list value(s) in house units, "
          f"{n_sch_ok} schematic value(s) in their amp's drafting idiom")

    if failures:
        print(f"\n{len(failures)} era-lettering check(s) FAILED: "
              f"{', '.join(failures[:6])}"
              f"{' …' if len(failures) > 6 else ''}")
        return 1
    print(f"\nall {len(CASES)} era-lettering cases and the corpus sweep passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
