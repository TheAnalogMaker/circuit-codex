#!/usr/bin/env python3
"""Validate every amps/<id>/meta.yaml against schema v1 (docs/schema.md).

Phase-0 stub: structural checks only. Grows alongside the schema — kicad_sch
round-trip (kiutils) and ngspice operating-point checks land with the pilot amps.
"""
import re
import sys
from pathlib import Path

import yaml

# A scalar that a YAML-1.1 loader (js-yaml, which the site build uses) coerces to a
# number even though PyYAML keeps it a string — e.g. circuit_ref: 5e1 becomes 50.
# Circuit ids that look like this MUST be quoted or the two loaders disagree.
_JS_NUMERIC = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")

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
        for artifact in ("voltages.yaml", "netlist.cir", "notes.md",
                         "schematic.kicad_sch", "bom.yaml"):
            if not (meta_path.parent / artifact).exists():
                errors.append(f"{meta_path}: verified circuits require {artifact}")
    errors += check_bom_refs(meta_path.parent)
    for i, src in enumerate(meta.get("sources") or []):
        if not isinstance(src, dict) or not src.get("desc"):
            errors.append(f"{meta_path}: sources[{i}] must be a mapping with 'desc' (and ideally 'url')")
        elif "url" in src and not str(src["url"]).startswith("http"):
            errors.append(f"{meta_path}: sources[{i}].url must be an http(s) link")
    for ancestor in (meta.get("lineage") or {}).get("derived_from", []) or []:
        if not (meta_path.parent.parent / ancestor).is_dir():
            errors.append(f"{meta_path}: lineage.derived_from '{ancestor}' has no amps/ directory")
    return errors


def _strip_unit(ref: str) -> str:
    """V1A/V5B-style multi-unit refs collapse to their bottle ref (V1, V5)."""
    if len(ref) > 1 and ref[-1] in "AB" and ref[0] in "VTLD":
        return ref[:-1]
    return ref


def check_bom_refs(amp_dir: Path) -> list[str]:
    """Every BOM designator must exist in the schematic and vice versa."""
    bom_path = amp_dir / "bom.yaml"
    sch_path = amp_dir / "schematic.kicad_sch"
    if not (bom_path.exists() and sch_path.exists()):
        return []
    try:
        from kiutils.schematic import Schematic
    except ImportError:
        print(f"note {amp_dir.name}: kiutils unavailable — BOM/schematic cross-check skipped")
        return []
    bom = yaml.safe_load(bom_path.read_text())
    bom_refs = {i["ref"] for i in bom.get("items", []) if i.get("ref") and i["ref"] != "—"}
    sch = Schematic.from_file(str(sch_path))
    sch_refs = set()
    for sym in sch.schematicSymbols:
        for prop in sym.properties:
            if prop.key == "Reference":
                sch_refs.add(_strip_unit(prop.value))
    errors = []
    for ref in sorted(bom_refs):
        if ref not in sch_refs and _strip_unit(ref) not in sch_refs:
            errors.append(f"{bom_path}: BOM ref '{ref}' not found in schematic")
    for ref in sorted(sch_refs):
        if ref not in bom_refs and not any(_strip_unit(b) == ref for b in bom_refs):
            errors.append(f"{bom_path}: schematic ref '{ref}' missing from BOM")
    return errors


def validate_history(root: Path) -> list[str]:
    """History-tier check for history/families/*.yaml.

    The history tier documents each amp *line* as a chronological chain of models
    (most not yet documented circuits). It feeds the /history/ pages and the lineage
    graph's ghost nodes, so it earns its own gate: schema shape, chronological
    sanity (start<=end and models ordered by start year), every model sourced, every
    non-null circuit_ref pointing at a real amps/ directory, and — because the amp
    pages reverse-map a documented circuit to exactly one family — each circuit_ref
    claimed by at most one family file.
    """
    hist_dir = root / "history" / "families"
    if not hist_dir.exists():
        return []  # history tier is optional; absent is not an error
    errors: list[str] = []
    amp_dirs = {p.name for p in (root / "amps").iterdir()
                if p.is_dir() and p.name != "_template"}
    claimed: dict[str, str] = {}  # circuit_ref -> family file that first claimed it
    files = sorted(hist_dir.glob("*.yaml"))
    n_models = 0
    for fam_path in files:
        rel = fam_path.relative_to(root)
        raw = fam_path.read_text()
        # Cross-loader guard: an unquoted circuit_ref whose text looks numeric parses
        # differently under js-yaml (site) than PyYAML (this gate). Catch it in the raw
        # text since PyYAML has already silently coerced nothing and kept the string.
        for ln, line in enumerate(raw.splitlines(), 1):
            m = re.match(r"^\s*circuit_ref:\s*([^\s#].*?)\s*$", line)
            if m and _JS_NUMERIC.match(m.group(1)):
                errors.append(
                    f"{rel}:{ln}: circuit_ref '{m.group(1)}' must be quoted — it parses "
                    f"as a number in the site's YAML loader (e.g. 5e1 → 50)")
        fam = yaml.safe_load(raw)
        if not isinstance(fam, dict):
            errors.append(f"{rel}: not a mapping")
            continue
        for key in ("family", "title", "summary", "models"):
            if key not in fam:
                errors.append(f"{rel}: missing required field '{key}'")
        if fam.get("family") and fam["family"] != fam_path.stem:
            errors.append(
                f"{rel}: family '{fam['family']}' != filename '{fam_path.stem}'")
        models = fam.get("models")
        if not isinstance(models, list) or not models:
            errors.append(f"{rel}: 'models' must be a non-empty list")
            continue
        prev_start = None
        for i, m in enumerate(models):
            where = f"{rel}: models[{i}]"
            if not isinstance(m, dict):
                errors.append(f"{where}: not a mapping")
                continue
            n_models += 1
            for key in ("designation", "years", "key_change", "sources"):
                if key not in m:
                    errors.append(f"{where}: missing required field '{key}'")
            # chronological sanity: start<=end, and models ordered by start year
            years = m.get("years")
            start = end = None
            if isinstance(years, dict):
                start, end = years.get("start"), years.get("end")
                if start is not None and end is not None and start > end:
                    errors.append(f"{where}: years.start {start} > years.end {end}")
            else:
                errors.append(f"{where}: years must be a mapping with start/end")
            if start is not None:
                if prev_start is not None and start < prev_start:
                    errors.append(
                        f"{where}: out of chronological order "
                        f"(start {start} precedes previous {prev_start})")
                prev_start = start
            # every model entry has >=1 source (each a mapping with a desc)
            srcs = m.get("sources")
            if not isinstance(srcs, list) or not srcs:
                errors.append(f"{where}: needs at least one source")
            else:
                for j, s in enumerate(srcs):
                    if not isinstance(s, dict) or not s.get("desc"):
                        errors.append(f"{where}: sources[{j}] must be a mapping with 'desc'")
                    elif "url" in s and not str(s["url"]).startswith("http"):
                        errors.append(f"{where}: sources[{j}].url must be an http(s) link")
            # circuit_ref (when present) must name a real amps/ directory, and no two
            # families may claim the same documented circuit (reverse-lookup integrity)
            ref = m.get("circuit_ref")
            if ref is not None:
                if ref not in amp_dirs:
                    errors.append(f"{where}: circuit_ref '{ref}' has no amps/ directory")
                elif ref in claimed and claimed[ref] != fam_path.name:
                    errors.append(
                        f"{where}: circuit_ref '{ref}' already claimed by "
                        f"{claimed[ref]} — a documented circuit belongs to one family")
                else:
                    claimed[ref] = fam_path.name
    print(f"checked {len(files)} history family file(s), {n_models} model(s)")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    metas = sorted(p for p in (root / "amps").glob("*/meta.yaml")
                   if p.parent.name != "_template")
    all_errors = []
    for meta_path in metas:
        all_errors += validate(meta_path)
    all_errors += validate_history(root)
    for err in all_errors:
        print(f"FAIL {err}")
    print(f"checked {len(metas)} circuit(s), {len(all_errors)} error(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
