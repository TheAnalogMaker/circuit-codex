#!/usr/bin/env python3
"""CI gate: each tube page's used_in list is the circuits that letter that tube.

The site derives the "Used in" sidebar from amps/*/meta.yaml `tubes:` plus each
tube file's name / slug / also_known_as. The YAML `used_in:` field is the same
claim written down so a reader of the files sees what the page shows. A hand
list went stale — reference/tubes/6sj7.yaml said no circuit used the tube while
amps/5c1/meta.yaml listed a 6SJ7 — so this gate rebuilds the list and fails
when the file disagrees.

Matching rule (keep in lockstep with site/src/lib/corpus.js designationToken):
strip parentheticals and punctuation, compare case-insensitively. 7025 and
ECC83 therefore match the 12AX7 page; 6L6GB matches 6L6G, not 5881.

    python3 pipeline/check_tube_used_in.py            # report + exit 1 on drift
    python3 pipeline/check_tube_used_in.py --selftest
    python3 pipeline/check_tube_used_in.py --write    # rewrite used_in in place
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AMPS = ROOT / "amps"
TUBES = ROOT / "reference" / "tubes"

USED_IN_LINE = re.compile(r"^used_in:\s*.*$", re.M)


def designation_token(s) -> str:
    text = str(s or "").split("(", 1)[0].split("·", 1)[0]
    return re.sub(r"[^A-Za-z0-9]", "", text).upper()


def tube_name_tokens(tube: dict) -> set[str]:
    names = {designation_token(tube.get("name")), designation_token(tube.get("tube"))}
    for aka in tube.get("also_known_as") or []:
        names.add(designation_token(aka))
    names.discard("")
    return names


def load_amp_tubes() -> dict[str, list[str]]:
    out = {}
    for meta_path in sorted(AMPS.glob("*/meta.yaml")):
        if meta_path.parent.name.startswith("_"):
            continue
        meta = yaml.safe_load(meta_path.read_text())
        out[str(meta["id"])] = [str(t) for t in (meta.get("tubes") or [])]
    return out


def derived_used_in(tube: dict, amp_tubes: dict[str, list[str]]) -> list[str]:
    names = tube_name_tokens(tube)
    return [amp_id for amp_id, bottles in amp_tubes.items()
            if any(designation_token(lab) in names for lab in bottles)]


def declared_used_in(tube: dict) -> list[str]:
    return [str(x) for x in (tube.get("used_in") or [])]


def load_tube_files() -> list[tuple[Path, dict]]:
    rows = []
    for path in sorted(TUBES.glob("*.yaml")):
        rows.append((path, yaml.safe_load(path.read_text())))
    return rows


def format_used_in(ids: list[str]) -> str:
    if not ids:
        return "used_in: []"
    return "used_in: [" + ", ".join(f'"{i}"' for i in ids) + "]"


def rewrite_used_in(path: Path, ids: list[str]) -> None:
    text = path.read_text()
    if not USED_IN_LINE.search(text):
        raise SystemExit(f"{path}: no used_in: line to rewrite")
    path.write_text(USED_IN_LINE.sub(format_used_in(ids), text, count=1))


def selftest() -> int:
    """A gate that cannot fail proves nothing. Plant the two drifts this
    gate exists to catch: a page that omits a circuit, and a page that claims
    a bottle the circuit does not letter."""
    amp_tubes = {"5c1": ["6SJ7", "6V6GT", "5Y3GT"], "5f6": ["5881", "5881"]}
    sj7 = {"name": "6SJ7", "tube": "6sj7", "also_known_as": ["6SJ7GT"], "used_in": []}
    w5881 = {"name": "5881", "tube": 5881, "also_known_as": ["6L6WGB"],
             "used_in": ["5e5a", "5f6"]}
    l6g = {"name": "6L6G", "tube": "6l6g", "also_known_as": ["6L6", "6L6GB"],
           "used_in": ["5e5a"]}
    failures = 0
    if derived_used_in(sj7, amp_tubes) != ["5c1"]:
        print("FAIL selftest: 6SJ7 should match 5c1"); failures += 1
    if derived_used_in(w5881, {"5e5a": ["6L6GB"], "5f6": ["5881"]}) != ["5f6"]:
        print("FAIL selftest: 5881 must not match a 6L6GB circuit"); failures += 1
    if derived_used_in(l6g, {"5e5a": ["6L6GB"], "5f4": ["6L6G"]}) != ["5e5a", "5f4"]:
        print("FAIL selftest: 6L6G aliases should match 6L6GB and 6L6G"); failures += 1
    ax7 = {"name": "12AX7", "tube": "12ax7", "also_known_as": ["ECC83", "7025"]}
    if derived_used_in(ax7, {"6g6b": ["7025"], "jtm45": ["ECC83"]}) != ["6g6b", "jtm45"]:
        print("FAIL selftest: 7025/ECC83 should match 12AX7"); failures += 1
    if failures == 0:
        print("check_tube_used_in selftest: 4 planted cases passed")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="rewrite used_in: to match the circuits that letter the tube")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    amp_tubes = load_amp_tubes()
    failures = 0
    for path, tube in load_tube_files():
        want = derived_used_in(tube, amp_tubes)
        have = declared_used_in(tube)
        if have == want:
            continue
        rel = path.relative_to(ROOT)
        if args.write:
            rewrite_used_in(path, want)
            print(f"rewrote {rel}: {have} -> {want}")
            continue
        missing = [i for i in want if i not in have]
        extra = [i for i in have if i not in want]
        print(f"FAIL {rel}")
        if missing:
            print(f"  missing: {missing}")
        if extra:
            print(f"  extra:   {extra}")
        failures += 1
    if args.write:
        return 0
    if failures:
        print(f"\n{failures} tube file(s) disagree with amps/*/meta.yaml tubes:.")
        print("Rewrite with: python3 pipeline/check_tube_used_in.py --write")
        return 1
    print(f"check_tube_used_in: {len(list(TUBES.glob('*.yaml')))} tube files match the corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
