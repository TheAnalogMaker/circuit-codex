#!/usr/bin/env python3
"""CI gate: every amps/<id>/schematic.kicad_sch must parse and round-trip
through kiutils (KiCad 6+ grammar check)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from kiutils.schematic import Schematic

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    files = sorted((ROOT / "amps").glob("*/schematic.kicad_sch"))
    failures = 0
    for f in files:
        try:
            sch = Schematic.from_file(str(f))
            with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=True) as tmp:
                sch.to_file(tmp.name)
            print(f"ok   {f.relative_to(ROOT)}: {len(sch.schematicSymbols)} symbols")
        except Exception as exc:  # noqa: BLE001 — any parse failure is a CI failure
            print(f"FAIL {f.relative_to(ROOT)}: {exc}")
            failures += 1
    print(f"checked {len(files)} schematic(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
