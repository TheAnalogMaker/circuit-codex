#!/usr/bin/env python3
"""MAINTAINER ONLY. Record that the maintainer has reviewed a verified
circuit's facts as they stand today.

Agents and contributors never run this on a real amp - the same rule as for
setting `verification.status`, `wiring_claim` or `schematic_claim`. A stamp is
the maintainer's sign-off, and a stamp nobody reviewed is a forged one.

    python3 pipeline/stamp_verification.py 5f6a

Writes two keys into amps/<id>/meta.yaml's `verification:` block:

    facts_sha256: "<the amp's current facts fingerprint>"   (quoted: never a number)
    reviewed: <today, YYYY-MM-DD>

and then re-exports reference/verification-freshness.yaml, so the stamp and the
worklist land in one commit. The fingerprint and what it covers are defined in
pipeline/verification_freshness.py.

The edit is a minimal text edit, never a YAML round-trip: every other line of
meta.yaml - comments, alignment, key order - is left byte for byte, and a
re-stamp replaces its own two lines in place. The result is re-parsed and must
equal the original plus exactly those two keys, or the file is restored and the
stamp fails.

Refuses unless `verification.status` is `verified`: the stamp records a review
of a granted badge, never a grant.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verification_freshness as vf                                        # noqa: E402

KEYS = ("facts_sha256", "reviewed")


class StampRefused(Exception):
    pass


def _block(lines: list) -> tuple:
    """(start, end, indent) of the top-level `verification:` block: `start` is
    the `verification:` line, `end` one past its last indented line."""
    start = next((i for i, ln in enumerate(lines)
                  if re.match(r"verification:\s*(#.*)?$", ln)), None)
    if start is None:
        raise StampRefused("meta.yaml has no block-style `verification:` mapping")
    end, indent = start + 1, None
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if not ln.strip():
            continue
        if not ln[0].isspace():
            break
        if indent is None and not ln.lstrip().startswith("#"):
            indent = ln[:len(ln) - len(ln.lstrip())]
        end = i + 1
    if indent is None:
        raise StampRefused("meta.yaml's `verification:` block has no keys")
    return start, end, indent


def stamped_text(text: str, sha: str, today: str) -> str:
    lines = text.split("\n")
    start, end, indent = _block(lines)
    new = {"facts_sha256": f"{indent}facts_sha256: \"{sha}\"",
           "reviewed": f"{indent}reviewed: {today}"}
    for i in range(start + 1, end):
        for k in KEYS:
            if re.match(rf"{re.escape(indent)}{k}:", lines[i]) and k in new:
                lines[i] = new.pop(k)
    return "\n".join(lines[:end] + [new[k] for k in KEYS if k in new] + lines[end:])


def stamp(amp_id: str, amps_dir: Path = vf.AMPS, today: "str | None" = None,
          export: bool = True) -> str:
    d = amps_dir / amp_id
    meta_path = d / "meta.yaml"
    if not meta_path.exists():
        raise StampRefused(f"{amp_id}: no {meta_path}")
    text = meta_path.read_text()
    meta = yaml.safe_load(text) or {}
    status = (meta.get("verification") or {}).get("status")
    if status != "verified":
        raise StampRefused(f"{amp_id}: verification.status is {status!r}, not 'verified' - "
                           f"a stamp records a review of a granted badge, never a grant")
    today = today or datetime.date.today().isoformat()
    sha = vf.fingerprint(amp_id, d)
    new_text = stamped_text(text, sha, today)
    want = dict(meta)
    want["verification"] = dict(meta["verification"], facts_sha256=sha,
                                reviewed=datetime.date.fromisoformat(today))
    meta_path.write_text(new_text)
    if yaml.safe_load(new_text) != want:
        meta_path.write_text(text)
        raise StampRefused(f"{amp_id}: the edited meta.yaml did not parse to the original "
                           f"plus the two stamp keys - restored, nothing stamped")
    if export:
        vf.export_worklist(amps_dir)
    return sha


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(
        description="MAINTAINER ONLY - agents and contributors never run this. Stamps "
                    "amps/<id>/meta.yaml with the circuit's current facts fingerprint "
                    "(verification.facts_sha256) and today's date (verification.reviewed), "
                    "recording that the maintainer has reviewed the verified circuit as it "
                    "stands, then re-exports reference/verification-freshness.yaml. "
                    "Refuses unless verification.status is verified.")
    ap.add_argument("amp", nargs="+", help="amp id(s), e.g. 5f6a")
    a = ap.parse_args(argv)
    rc = 0
    for amp_id in a.amp:
        try:
            sha = stamp(amp_id, export=False)
        except StampRefused as e:
            print(f"REFUSED {e}")
            rc = 1
            continue
        print(f"stamped {amp_id}: facts_sha256 {sha}")
    vf.export_worklist()
    print(f"re-exported {vf.WORKLIST.relative_to(vf.ROOT)}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
