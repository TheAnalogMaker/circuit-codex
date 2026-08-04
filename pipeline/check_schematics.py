#!/usr/bin/env python3
"""CI gate: every amps/<id>/schematic.kicad_sch must parse and round-trip
through kiutils (KiCad 6+ grammar check)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from kiutils.schematic import Schematic

ROOT = Path(__file__).resolve().parent.parent


def strict_tokenize_errors(text: str) -> list[str]:
    """Tokenize the way KiCanvas does — stricter than kiutils.

    kiutils forgives a raw double quote inside a string; KiCanvas's tokenizer
    throws and the schematic renders as a blank panel (the AC15 'Vibravox'
    incident). A string ends at the first unescaped quote, and the next
    non-space character must close or open an s-expression.
    """
    errors: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            # A quote may only OPEN a string after whitespace or a paren —
            # a quote mid-atom is exactly where KiCanvas throws. (Two strings
            # back to back, '"Reference" "R"', are separated by a space and
            # are legal.)
            if i > 0 and text[i - 1] not in " \t\r\n(":
                errors.append(
                    f"quote opens mid-atom at index {i}: "
                    f"{text[max(0, i - 30):i + 12]!r}")
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            if j >= n:
                errors.append(f"unterminated string opened at index {i}")
            i = j + 1
        else:
            i += 1
    return errors


def main() -> int:
    files = sorted((ROOT / "amps").glob("*/schematic.kicad_sch"))
    failures = 0
    for f in files:
        try:
            sch = Schematic.from_file(str(f))
            with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=True) as tmp:
                sch.to_file(tmp.name)
            strict = strict_tokenize_errors(f.read_text())
            if strict:
                raise ValueError(
                    "KiCanvas-strict tokenization failed: " + "; ".join(strict[:3]))
            print(f"ok   {f.relative_to(ROOT)}: {len(sch.schematicSymbols)} symbols")
        except Exception as exc:  # noqa: BLE001 — any parse failure is a CI failure
            print(f"FAIL {f.relative_to(ROOT)}: {exc}")
            failures += 1
    print(f"checked {len(files)} schematic(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
