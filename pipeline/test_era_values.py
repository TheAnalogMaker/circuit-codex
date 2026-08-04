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

    # --- corpus sweep: every real BOM value, lettered or left alone ----------
    print("\ncorpus sweep — every amps/*/bom.yaml value:")
    n_letter = n_house = 0
    for bom in sorted((ROOT / "amps").glob("*/bom.yaml")):
        for item in (yaml.safe_load(bom.read_text()) or {}).get("items", []):
            value, cat = str(item.get("value", "")), category(item.get("part", ""))
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
