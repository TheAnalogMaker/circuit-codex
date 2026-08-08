#!/usr/bin/env python3
"""Validate every amps/<id>/meta.yaml against schema v1 (docs/schema.md).

Phase-0 stub: structural checks only. Grows alongside the schema — kicad_sch
round-trip (kiutils) and ngspice operating-point checks land with the pilot amps.
"""
import datetime
import re
import sys
from pathlib import Path

import yaml

# A scalar that a YAML-1.1 loader (js-yaml, which the site build uses) coerces to a
# number even though PyYAML keeps it a string — e.g. circuit_ref: 5e1 becomes 50.
# Circuit ids that look like this MUST be quoted or the two loaders disagree.
_JS_NUMERIC = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")

# Circuit id grammar (docs/schema.md, "Ids and colliding designations"):
#   <designation>                lowercase circuit designation — 5e3, ab763, jtm45
#   <designation>-<model>        the same designation qualified by the amp model it
#                                belongs to, for designations a maker reused across
#                                models (ab763-twin). One hyphen, never more: the
#                                first hyphen is the split, so the model slug is a
#                                single lowercase token.
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)?$")
ID_LINE = re.compile(r"^id:\s*([^\s#].*?)\s*$")

REQUIRED = ["id", "name_style", "family", "era", "wattage", "tubes",
            "topology", "sources", "verification"]
FAMILIES = {"tweed", "blackface", "british", "vox", "boutique", "other"}
STATUSES = {"draft", "verified"}


def check_id(meta: dict, raw: str, where: str) -> list[str]:
    """Id grammar, cross-loader quoting, and — for a model-qualified id — that the
    qualifier names the same model the circuit's own name_style names.

    That last check is what keeps `ab763-twin` from being pinned on a Deluxe
    Reverb: the site renders the qualifier by taking the tail of name_style from
    the word the slug matches, so if no word matches, the id and the page would
    disagree about which amplifier this is."""
    errors: list[str] = []
    ident = meta.get("id")
    if ident is None:
        return errors  # the missing-required-field check already reported it
    # Cross-loader guard, same trap as circuit_ref and the load-line presets: an
    # unquoted id whose text looks numeric parses as a number in the site's YAML
    # loader (5e1 -> 50) while PyYAML keeps the string, so the two disagree
    # silently. Checked in the raw text, since PyYAML has already read it as text.
    for ln, line in enumerate(raw.splitlines(), 1):
        m = ID_LINE.match(line)
        if not m:
            continue
        if _JS_NUMERIC.match(m.group(1)):
            errors.append(
                f"{where}:{ln}: id '{m.group(1)}' must be quoted — it parses as a "
                f"number in the site's YAML loader (e.g. 5e1 -> 50)")
        break
    if not isinstance(ident, str) or not ID_RE.match(ident):
        errors.append(
            f"{where}: id '{ident}' must be a lowercase circuit designation, "
            f"optionally qualified by one model slug ('<designation>-<model>', "
            f"e.g. 'ab763-twin') — see docs/schema.md")
        return errors
    if "-" in ident:
        slug = ident.split("-", 1)[1]
        style = str(meta.get("name_style") or "")
        words = re.findall(r"[A-Za-z0-9]+", style)
        if not any(w.lower() == slug for w in words):
            errors.append(
                f"{where}: id qualifier '{slug}' does not name any word of "
                f"name_style {style!r} — a model-qualified id must agree with the "
                f"model the circuit says it is")
    return errors


def validate(meta_path: Path) -> list[str]:
    errors = []
    raw = meta_path.read_text()
    meta = yaml.safe_load(raw)
    if not isinstance(meta, dict):
        return [f"{meta_path}: not a mapping"]
    for key in REQUIRED:
        if key not in meta:
            errors.append(f"{meta_path}: missing required field '{key}'")
    errors += check_id(meta, raw, str(meta_path))
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
        # A verified claim needs the artifacts that back it. This block used to sit,
        # by an indentation slip, inside the `added`-is-not-a-date branch below —
        # which is only ever reached when `added` is malformed, so it had never run.
        for artifact in ("voltages.yaml", "netlist.cir", "notes.md",
                         "schematic.kicad_sch", "bom.yaml"):
            if not (meta_path.parent / artifact).exists():
                errors.append(f"{meta_path}: verified circuits require {artifact}")
    # Every circuit must carry a provable date for the site feed: verification.date
    # once verified, an explicit `added` (the git landing date) while draft. The
    # production build is a shallow clone, so git history cannot supply it there.
    if status == "draft" and "added" not in meta:
        errors.append(f"{meta_path}: draft circuits require 'added' (the date the "
                      "circuit landed in the corpus — the feed's pubDate)")
    if "added" in meta and not isinstance(meta["added"], datetime.date):
        errors.append(f"{meta_path}: 'added' must be an unquoted YYYY-MM-DD date")
    errors += check_bom_refs(meta_path.parent)
    refs = bom_refs(meta_path.parent)
    errors += check_conventions(meta, meta_path, refs)
    errors += check_iron(meta, meta_path, refs)
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


# ---------------------------------------------------------------------------
# conventions: how this drawing letters itself
# ---------------------------------------------------------------------------
# TWO REFERENCE-DESIGNATOR SCHEMES SHIP IN THIS CORPUS AND BOTH STAY.
#
# The 5F1, 5E1, 5F2-A, 5C1 and AA764 number their parts straight through —
# R1…R13, C1…C10 — the way their own factory sheets do. The 5E3, 5F10, 5F4 and
# most of what came after carry a role code in the designator instead: RD1 is
# rail dropper 1, RL4 a plate load, CK1 a cathode bypass. Neither is wrong. The
# first is what a small drawing with a dozen parts wants; the second is what a
# hundred-part Bassman needs before a reader can hold it in their head.
#
# Normalising the corpus onto one of them was the alternative, and it was
# rejected: renaming R1 to RG1 across a netlist, a schematic, a layout, a
# voltage chart and prose changes nothing a builder can measure, breaks every
# link anyone has made into this archive, and — worse — erases which scheme the
# amp's own source drawing used. What a reader actually needs is to be TOLD, on
# the page, which scheme they are reading. So each amp declares it, the site
# prints it, and this gate proves the declaration matches the parts list.
#
# One rule binds both schemes: a designator is what a DRAWING letters on a part.
# It never contains an underscore. `C_tr1` and `C_NFB` are source-code
# identifiers that leaked out of a generator script onto a published board, and
# a builder looking for "C_NFB" on a factory sheet will not find it.
DESIGNATOR_SCHEMES = ("sequential", "functional")
# Class prefixes a plain sequential designator may use: the standard reference
# designator letters, plus the ones this corpus's drawings actually letter.
_SEQ_CLASS = (r"(?:R|C|L|T|V|D|Q|X|Y|F|J|S|SW|VR|RV|PL|SPK|CH|MS|SEL|JSPK|QS|"
              r"OPTO|TANK)")
RE_SEQUENTIAL = re.compile(rf"^{_SEQ_CLASS}\d+[a-z]?$")
RE_DESIGNATOR = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def detect_designator_scheme(refs) -> str:
    """'sequential' when every designator is class + running number, else
    'functional'. Deliberately not a judgement call: one designator carrying a
    role code makes the whole parts list a functional one to read."""
    return ("sequential" if all(RE_SEQUENTIAL.match(r) for r in refs)
            else "functional")


def check_conventions(meta: dict, meta_path: Path, refs) -> list[str]:
    errors = []
    conv = meta.get("conventions") or {}
    if not isinstance(conv, dict):
        return [f"{meta_path}: 'conventions' must be a mapping"]
    notation = str(conv.get("notation", "us")).lower()
    if notation not in ("us", "uk"):
        errors.append(f"{meta_path}: conventions.notation must be 'us' or 'uk' "
                      f"(the schematic's drafting idiom), got {notation!r}")
    declared = conv.get("designators")
    if declared is None:
        errors.append(
            f"{meta_path}: conventions.designators is required — "
            f"'sequential' (R1…R13, the small tweed sheets) or 'functional' "
            f"(RD1/RL4/CK1, role coded). Both ship in this corpus; a reader has "
            f"to be told which one this page is written in")
    elif declared not in DESIGNATOR_SCHEMES:
        errors.append(f"{meta_path}: conventions.designators must be one of "
                      f"{list(DESIGNATOR_SCHEMES)}, got {declared!r}")
    elif refs:
        actual = detect_designator_scheme(refs)
        if actual != declared:
            odd = sorted({r for r in refs if not RE_SEQUENTIAL.match(r)})[:6]
            errors.append(
                f"{meta_path}: conventions.designators says {declared!r} but the "
                f"parts list reads {actual!r}" +
                (f" ({', '.join(odd)} carry role codes)" if odd else ""))
    # The one rule both schemes share.
    bad = sorted({r for r in refs if not RE_DESIGNATOR.match(str(r))})
    if bad and str(meta.get("id")) not in DESIGNATOR_WAIVERS:
        errors.append(
            f"{meta_path}: designator(s) {', '.join(bad)} are not designators a "
            f"drawing could letter — a reference designator is letters and "
            f"digits only (no underscores, spaces or punctuation)")
    return errors


# A designator waiver is a DECLARED, dated debt, printed loudly — the same
# mechanism pipeline/lint_waivers.yaml uses for a collision the drawing cannot
# yet resolve. It is never silent and never open-ended.
DESIGNATOR_WAIVERS = {
    "5e5a": "board and schematic carry generator-script names (C_f1, C_tr1, "
            "C_NFB, R_NFB); the rename touches netlist.cir, voltages.yaml and "
            "the drawn board together and is queued as its own change",
}


def check_iron(meta: dict, meta_path: Path, refs) -> list[str]:
    """meta.yaml `iron:` — the electrical rating for a transformer or choke whose
    parts-list value is a bare factory part number. render_layouts.load_iron()
    letters it beside the glyph; a key that names no such part would be a rating
    the drawing silently drops."""
    iron = meta.get("iron")
    if iron is None:
        return []
    if not isinstance(iron, dict):
        return [f"{meta_path}: 'iron' must be a mapping of designator -> rating"]
    errors = []
    for ref, rating in iron.items():
        if refs and str(ref) not in refs:
            errors.append(f"{meta_path}: iron['{ref}'] names no bom.yaml designator")
        if not str(rating).strip():
            errors.append(f"{meta_path}: iron['{ref}'] is empty — omit the key "
                          f"rather than state a blank rating")
    return errors


def bom_refs(amp_dir: Path) -> list[str]:
    path = amp_dir / "bom.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return [str(it["ref"]) for it in (data.get("items") or [])
            if it.get("ref") and it["ref"] != "—"]


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

    It also cross-checks the two tiers against each other. A documented circuit is
    described twice — on its own page from amps/<id>/meta.yaml, and on the family
    page, the lineage chip and the history badge from the family row that claims it
    — and nothing used to make the two agree. They drifted publicly: /amps/ab763/
    said 1963-1967 while its own family row said 1964-1967, and the 5E3 read 12 W on
    its page and 15 W on its lineage chip. Where both tiers state a fact, they must
    state the same one; where a row legitimately covers more than the circuit it
    links (a combined "5E6 / 5E6-A" row spans both revisions' years), the row says so
    in `era_note` and the mismatch is waived with that reason printed.
    """
    hist_dir = root / "history" / "families"
    if not hist_dir.exists():
        return []  # history tier is optional; absent is not an error
    errors: list[str] = []
    amp_dirs = {p.name for p in (root / "amps").iterdir()
                if p.is_dir() and p.name != "_template"}
    claimed: dict[str, str] = {}  # circuit_ref -> family file that first claimed it
    waived: list[str] = []        # era_note waivers, printed loudly like the lint's
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
                    errors += _cross_check_row(root, where, m, ref, waived)
    if waived:
        print("history/amp cross-check waivers (era_note) in force:")
        for line in waived:
            print(f"  {line}")
    print(f"checked {len(files)} history family file(s), {n_models} model(s)")
    return errors


# Facts both tiers state, and where each keeps them. Only these are cross-checked:
# a family row is a one-paragraph summary of a *line*, not a second copy of the
# circuit's metadata, so it is free to say nothing — but not to say something else.
_CROSS_FIELDS = (
    ("years.start", lambda m: (m.get("years") or {}).get("start"),
     lambda meta: (meta.get("era") or {}).get("start"), "era.start"),
    ("years.end", lambda m: (m.get("years") or {}).get("end"),
     lambda meta: (meta.get("era") or {}).get("end"), "era.end"),
    ("wattage", lambda m: m.get("wattage"),
     lambda meta: meta.get("wattage"), "wattage"),
)


def _cross_check_row(root: Path, where: str, model: dict, ref: str,
                     waived: list[str]) -> list[str]:
    """Every fact a family row and the circuit it links both state must match.

    `era_note` on the row is the escape hatch, and it is a documented one: a row
    that deliberately covers more than its linked circuit (a combined designation,
    a line whose production ran past the revision this corpus drew) states why, and
    the reason is printed by the gate rather than hidden. An `era_note` on a row
    with no disagreement is itself an error — a stale waiver is a lie about the data
    and would mask the next real drift.
    """
    meta_path = root / "amps" / ref / "meta.yaml"
    if not meta_path.exists():
        return []          # the missing-directory error above already fired
    try:
        meta = yaml.safe_load(meta_path.read_text()) or {}
    except yaml.YAMLError:
        return []          # validate() reports the parse failure on its own pass
    note = str(model.get("era_note") or "").strip()
    diffs = []
    for label, row_get, meta_get, meta_label in _CROSS_FIELDS:
        row_val, meta_val = row_get(model), meta_get(meta)
        if row_val is None or meta_val is None:
            continue       # a row need not state everything the circuit does
        if row_val != meta_val:
            diffs.append(f"{label} {row_val} != amps/{ref}/meta.yaml {meta_label} "
                         f"{meta_val}")
    if diffs and note:
        waived.append(f"{where} [{ref}]: {'; '.join(diffs)} — {note}")
        return []
    if diffs:
        return [f"{where}: family row and the circuit it links disagree — "
                f"{'; '.join(diffs)}. Reconcile them, or state why the row covers "
                f"more than the circuit in an 'era_note' on this model."]
    if note:
        return [f"{where}: era_note waives a disagreement that no longer exists "
                f"between this row and amps/{ref}/meta.yaml — remove it"]
    return []


def validate_loadlines(root: Path) -> list[str]:
    """Cross-loader guard for the generated reference/loadlines.yaml.

    The load-line explorer keys its presets on the circuit id and the tube name.
    Both look numeric for ids like 5e1 and tubes like 5881, so both must be quoted
    or js-yaml (the site's loader) reads 5e1 as 50 and silently drops the preset —
    the same trap the history tier is guarded against above. Every id must also
    name a real amps/ directory.
    """
    path = root / "reference" / "loadlines.yaml"
    if not path.exists():
        return []  # optional derived file; regenerate with pipeline/export_loadlines.py
    errors: list[str] = []
    rel = path.relative_to(root)
    raw = path.read_text()
    for ln, line in enumerate(raw.splitlines(), 1):
        m = re.match(r"^\s*-?\s*(amp|tube):\s*([^\s#].*?)\s*$", line)
        if m and _JS_NUMERIC.match(m.group(2)):
            errors.append(
                f"{rel}:{ln}: {m.group(1)} '{m.group(2)}' must be quoted — it parses "
                f"as a number in the site's YAML loader (e.g. 5e1 → 50)")
    amp_dirs = {p.name for p in (root / "amps").iterdir()
                if p.is_dir() and p.name != "_template"}
    stages = (yaml.safe_load(raw) or {}).get("stages") or []
    for i, s in enumerate(stages):
        if s.get("amp") not in amp_dirs:
            errors.append(f"{rel}: stages[{i}].amp '{s.get('amp')}' has no amps/ directory")
    print(f"checked {rel} — {len(stages)} output stage(s)")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    metas = sorted(p for p in (root / "amps").glob("*/meta.yaml")
                   if p.parent.name != "_template")
    all_errors = []
    for meta_path in metas:
        all_errors += validate(meta_path)
    all_errors += validate_history(root)
    all_errors += validate_loadlines(root)
    for err in all_errors:
        print(f"FAIL {err}")
    print(f"checked {len(metas)} circuit(s), {len(all_errors)} error(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
