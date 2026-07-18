#!/usr/bin/env python3
"""CI gate: every amps/<id>/layout.yaml renders cleanly to a valid SVG.

For each layout it checks that:
  * pipeline/render_layouts.py renders it without error (which also verifies
    every part / off-board reference resolves against bom.yaml — the shared key);
  * a committed amps/<id>/layout.svg exists;
  * that SVG is well-formed XML with an <svg> root; and
  * the committed SVG matches a fresh render (the renderer is deterministic, so
    a stale checked-in SVG is a failure — regenerate with render_layouts.py).

Run `python pipeline/render_layouts.py` to (re)generate the SVGs, then this gate
to confirm they are in sync and valid.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.dom import minidom

from render_layouts import render_layout

ROOT = Path(__file__).resolve().parent.parent


def check_one(yml: Path) -> list[str]:
    amp_dir = yml.parent
    rel = amp_dir.name
    errs: list[str] = []
    if not (amp_dir / "bom.yaml").exists():
        return [f"{rel}: layout.yaml present but bom.yaml missing (refs cannot resolve)"]
    try:
        rendered = render_layout(amp_dir)          # resolves refs; raises on unknown
    except Exception as exc:                         # noqa: BLE001 — any render error fails CI
        return [f"{rel}: render failed — {exc}"]
    svg_path = amp_dir / "layout.svg"
    if not svg_path.exists():
        return [f"{rel}: layout.svg missing — run pipeline/render_layouts.py"]
    committed = svg_path.read_text()
    try:
        dom = minidom.parseString(committed)
        if dom.documentElement.tagName != "svg":
            errs.append(f"{rel}: layout.svg root element is <{dom.documentElement.tagName}>, not <svg>")
    except Exception as exc:                         # noqa: BLE001
        errs.append(f"{rel}: layout.svg is not well-formed XML — {exc}")
    if committed != rendered:
        errs.append(f"{rel}: layout.svg is stale — regenerate with pipeline/render_layouts.py")
    return errs


def main() -> int:
    ymls = sorted((ROOT / "amps").glob("*/layout.yaml"))
    all_errors: list[str] = []
    for yml in ymls:
        errs = check_one(yml)
        all_errors += errs
        if not errs:
            n = len(yml.parent.joinpath("layout.svg").read_text())
            print(f"ok   amps/{yml.parent.name}/layout.svg ({n} bytes)")
    for err in all_errors:
        print(f"FAIL {err}")
    print(f"checked {len(ymls)} layout(s), {len(all_errors)} failure(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
