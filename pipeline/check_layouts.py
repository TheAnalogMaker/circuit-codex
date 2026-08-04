#!/usr/bin/env python3
"""CI gate: every amps/<id>/layout.yaml renders cleanly to a valid SVG, and its
wiring layer passes the collision lint.

Each layout ships in BOTH published styles — the house drawing (layout.svg) and
the era layout-sheet drawing (layout-sheet.svg) the amp pages show by default.
Both are generated from the same layout.yaml by the same geometry, so both are
gated the same way. For each layout and each style it checks that:

  * pipeline/render_layouts.py renders it without error (which also verifies
    every part / off-board reference resolves against bom.yaml — the shared key);
  * the committed SVG exists;
  * that SVG is well-formed XML with an <svg> root;
  * the committed SVG matches a fresh render (the renderer is deterministic, so
    a stale checked-in SVG is a failure — regenerate with render_layouts.py); and
  * the wiring layer passes the collision lint (render_layouts.lint_layout) —
    near-parallel overlaps and terminal ambiguity. See lint_layout's docstring.

The lint runs twice. The full pass measures the house render: the wiring checks
(a/b), the label checks (c/d/e) and the duplicate-label check (f). The sheet
pass re-runs the LABEL checks only against a SheetRenderer — the two styles
share their wiring geometry exactly, but the sheet letters values on the part
bodies at its own type sizes, so it can collide where the house drawing does
not. Sheet findings are tagged `[sheet]`.

Collision-lint failures are BLOCKING unless the amp carries a waiver in
pipeline/lint_waivers.yaml, in which case they are downgraded to WAIVED and the
active waivers are printed loudly (a waiver is never silent). This is a
permanent, documented mechanism — like the disputed nodes on a chart.

Run this from the pipeline/ directory (it imports render_layouts):
    python3 pipeline/render_layouts.py                  # house SVGs
    python3 pipeline/render_layouts.py --style sheet    # sheet SVGs, then…
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


STYLES = (("house", "layout.svg", ""),
          ("sheet", "layout-sheet.svg", " --style sheet"))


def check_one(yml: Path) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, waived_lint_notes) for one layout."""
    amp_dir = yml.parent
    rel = amp_dir.name
    errs: list[str] = []
    if not (amp_dir / "bom.yaml").exists():
        return ([f"{rel}: layout.yaml present but bom.yaml missing (refs cannot resolve)"], [])
    for style, filename, flag in STYLES:
        try:
            rendered = render_layout(amp_dir, style)   # resolves refs; raises on unknown
        except Exception as exc:                       # noqa: BLE001 — any render error fails CI
            errs.append(f"{rel}: {style} render failed — {exc}")
            continue
        svg_path = amp_dir / filename
        if not svg_path.exists():
            errs.append(f"{rel}: {filename} missing — run "
                        f"pipeline/render_layouts.py{flag}")
            continue
        committed = svg_path.read_text()
        try:
            dom = minidom.parseString(committed)
            if dom.documentElement.tagName != "svg":
                errs.append(f"{rel}: {filename} root element is "
                            f"<{dom.documentElement.tagName}>, not <svg>")
        except Exception as exc:                       # noqa: BLE001
            errs.append(f"{rel}: {filename} is not well-formed XML — {exc}")
        if committed != rendered:
            errs.append(f"{rel}: {filename} is stale — regenerate with "
                        f"pipeline/render_layouts.py{flag}")
    return (errs, [])


def main() -> int:
    waivers = load_waivers()
    ymls = sorted((ROOT / "amps").glob("*/layout.yaml"))
    all_errors: list[str] = []
    waived_summary: list[tuple[str, int, str]] = []
    for yml in ymls:
        rel = yml.parent.name
        errs, _ = check_one(yml)
        # house: wiring + labels + duplicate labels. sheet: the label checks
        # again, against the style's own type — see the module docstring.
        lint_fails = lint_layout(yml.parent)
        lint_fails += lint_layout(yml.parent, style="sheet", labels_only=True)
        if lint_fails and rel in waivers:
            waived_summary.append((rel, len(lint_fails), waivers[rel]))
        else:
            errs += lint_fails
        all_errors += errs
        if not errs:
            sizes = " + ".join(
                str(len(yml.parent.joinpath(f).read_text())) for _s, f, _fl in STYLES)
            waived = "  [lint WAIVED]" if (rel in waivers and lint_fails) else ""
            print(f"ok   amps/{rel}/layout.svg + layout-sheet.svg "
                  f"({sizes} bytes){waived}")

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
