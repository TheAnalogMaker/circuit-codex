#!/usr/bin/env python3
"""Validate every amps/<id>/meta.yaml against schema v1 (docs/schema.md).

Phase-0 stub: structural checks only. Grows alongside the schema — kicad_sch
round-trip (kiutils) and ngspice operating-point checks land with the pilot amps.
"""
import sys
from pathlib import Path

import yaml

REQUIRED = ["id", "name_style", "family", "era", "wattage", "tubes",
            "topology", "sources", "verification"]
FAMILIES = {"tweed", "blackface", "british", "vox", "boutique", "other"}
STATUSES = {"draft", "verified"}


def validate(meta_path: Path) -> list[str]:
    errors = []
    meta = yaml.safe_load(meta_path.read_text())
    if not isinstance(meta, dict):
        return [f"{meta_path}: not a mapping"]
    for key in REQUIRED:
        if key not in meta:
            errors.append(f"{meta_path}: missing required field '{key}'")
    if meta.get("id") and meta["id"] != meta_path.parent.name:
        errors.append(f"{meta_path}: id '{meta['id']}' != directory '{meta_path.parent.name}'")
    if meta.get("family") and meta["family"] not in FAMILIES:
        errors.append(f"{meta_path}: unknown family '{meta['family']}'")
    status = (meta.get("verification") or {}).get("status")
    if status not in STATUSES:
        errors.append(f"{meta_path}: verification.status must be one of {sorted(STATUSES)}")
    if status == "verified":
        v = meta["verification"]
        for key in ("date", "max_deviation_pct"):
            if key not in v:
                errors.append(f"{meta_path}: verified circuits require verification.{key}")
        if not (meta_path.parent / "voltages.yaml").exists():
            errors.append(f"{meta_path}: verified circuits require voltages.yaml")
    for i, src in enumerate(meta.get("sources") or []):
        if not isinstance(src, dict) or not src.get("desc"):
            errors.append(f"{meta_path}: sources[{i}] must be a mapping with 'desc' (and ideally 'url')")
        elif "url" in src and not str(src["url"]).startswith("http"):
            errors.append(f"{meta_path}: sources[{i}].url must be an http(s) link")
    for ancestor in (meta.get("lineage") or {}).get("derived_from", []) or []:
        if not (meta_path.parent.parent / ancestor).is_dir():
            errors.append(f"{meta_path}: lineage.derived_from '{ancestor}' has no amps/ directory")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    metas = sorted(p for p in (root / "amps").glob("*/meta.yaml")
                   if p.parent.name != "_template")
    all_errors = []
    for meta_path in metas:
        all_errors += validate(meta_path)
    for err in all_errors:
        print(f"FAIL {err}")
    print(f"checked {len(metas)} circuit(s), {len(all_errors)} error(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
