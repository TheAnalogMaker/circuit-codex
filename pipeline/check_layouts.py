#!/usr/bin/env python3
"""CI gate: every amps/<id>/layout.yaml renders cleanly to a valid SVG, and its
wiring layer passes the collision lint.

For each layout it checks that:
  * pipeline/render_layouts.py renders it without error (which also verifies
    every part / off-board reference resolves against bom.yaml — the shared key);
  * a committed amps/<id>/layout.svg exists;
  * that SVG is well-formed XML with an <svg> root;
  * the committed SVG matches a fresh render (the renderer is deterministic, so
    a stale checked-in SVG is a failure — regenerate with render_layouts.py); and
  * the wiring layer passes the collision lint (render_layouts.lint_layout) —
    near-parallel overlaps and terminal ambiguity. See lint_layout's docstring.

Collision-lint failures are BLOCKING unless the amp carries a waiver in
pipeline/lint_waivers.yaml, in which case they are downgraded to WAIVED and the
active waivers are printed loudly (a waiver is never silent). This is a
permanent, documented mechanism — like the disputed nodes on a chart.

Run this from the pipeline/ directory (it imports render_layouts):
    python3 pipeline/render_layouts.py     # (re)generate the SVGs, then…
    cd pipeline && python3 check_layouts.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.dom import minidom

import yaml

from render_layouts import lint_layout, render_layout

ROOT = Path(__file__).resolve().parent.parent
WAIVERS_PATH = Path(__file__).resolve().parent / "lint_waivers.yaml"


def load_waivers() -> dict[str, str]:
    if not WAIVERS_PATH.exists():
        return {}
    data = yaml.safe_load(WAIVERS_PATH.read_text()) or {}
    return {str(k): str(v) for k, v in (data.get("waivers") or {}).items()}


def check_one(yml: Path) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, waived_lint_notes) for one layout."""
    amp_dir = yml.parent
    rel = amp_dir.name
    errs: list[str] = []
    if not (amp_dir / "bom.yaml").exists():
        return ([f"{rel}: layout.yaml present but bom.yaml missing (refs cannot resolve)"], [])
    try:
        rendered = render_layout(amp_dir)          # resolves refs; raises on unknown
    except Exception as exc:                         # noqa: BLE001 — any render error fails CI
        return ([f"{rel}: render failed — {exc}"], [])
    svg_path = amp_dir / "layout.svg"
    if not svg_path.exists():
        return ([f"{rel}: layout.svg missing — run pipeline/render_layouts.py"], [])
    committed = svg_path.read_text()
    try:
        dom = minidom.parseString(committed)
        if dom.documentElement.tagName != "svg":
            errs.append(f"{rel}: layout.svg root element is <{dom.documentElement.tagName}>, not <svg>")
    except Exception as exc:                         # noqa: BLE001
        errs.append(f"{rel}: layout.svg is not well-formed XML — {exc}")
    if committed != rendered:
        errs.append(f"{rel}: layout.svg is stale — regenerate with pipeline/render_layouts.py")
    return (errs, [])


def main() -> int:
    waivers = load_waivers()
    ymls = sorted((ROOT / "amps").glob("*/layout.yaml"))
    all_errors: list[str] = []
    waived_summary: list[tuple[str, int, str]] = []
    for yml in ymls:
        rel = yml.parent.name
        errs, _ = check_one(yml)
        lint_fails = lint_layout(yml.parent)
        if lint_fails and rel in waivers:
            waived_summary.append((rel, len(lint_fails), waivers[rel]))
        else:
            errs += lint_fails
        all_errors += errs
        if not errs:
            n = len(yml.parent.joinpath("layout.svg").read_text())
            waived = "  [lint WAIVED]" if (rel in waivers and lint_layout(yml.parent)) else ""
            print(f"ok   amps/{rel}/layout.svg ({n} bytes){waived}")

    if waived_summary:
        print("\n" + "=" * 68)
        print("ACTIVE COLLISION-LINT WAIVERS (failures downgraded, not blocking):")
        for rel, count, reason in waived_summary:
            print(f"  !! {rel}: {count} lint failure(s) WAIVED — {reason}")
        print("These layouts carry legibility debt. Remove the waiver once fixed.")
        print("=" * 68)

    for err in all_errors:
        print(f"FAIL {err}")
    print(f"\nchecked {len(ymls)} layout(s), {len(all_errors)} failure(s), "
          f"{len(waived_summary)} waived")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
