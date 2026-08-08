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

from render_layouts import (          # noqa: E402
    _parse_farads, _parse_ohms, category, era_pair, primary_value,
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
    # a multi-section can keeps the section count the house string carries
    ("16 µF · 450 V (×2)", "electro", ("16MFD", "450V (×2)")),
    # --- refusals: house tokens come back untouched -------------------------
    ("selenium · silicon diode in modern builds",
     "other", ("selenium", "silicon diode in modern builds")),
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
            if body == primary_value(value):
                n_house += 1                      # refused: house token, verbatim
                continue
            n_letter += 1
            if not round_trips(value, cat, body):
                failures.append(f"{bom.parent.name}:{item.get('ref')} {value!r}")
                print(f"  FAIL {bom.parent.name} {item.get('ref')}: "
                      f"{value!r} -> {body!r} is not the same quantity")
    print(f"  {n_letter} value(s) lettered and round-tripped, "
          f"{n_house} left in house units")

    if failures:
        print(f"\n{len(failures)} era-lettering check(s) FAILED: "
              f"{', '.join(failures[:6])}"
              f"{' …' if len(failures) > 6 else ''}")
        return 1
    print(f"\nall {len(CASES)} era-lettering cases and the corpus sweep passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
