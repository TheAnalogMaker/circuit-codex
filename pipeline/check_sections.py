#!/usr/bin/env python3
"""Every valve section a circuit's tube complement supplies is instantiated in
its netlist or declared in its meta.yaml — never silently absent.

Why this gate exists. On 2026-09-10 five circuits were found missing whole
stages: the 5E5-A's and 5E6-A's cathode followers (and the 5E6-A's driver),
the AB763 Deluxe Reverb's Normal-channel second stage, and the harmonic-
vibrato pairs of the 6G4 and 6G5. Each was absent from the netlist AND the
sheet, so the sheet-vs-netlist gate had nothing to object to, and the printed
voltages that would have exposed it had been set aside as chart nulls. What a
netlist leaves out is a layer every other gate excludes; this gate turns the
omission into a declaration a reviewer can read and a source can refute.

What counts as a section is read from the tube's own reference file, never
from the shape of its name: a bottle supplies one amplifying section per
distinct `unit` its basing gives a grid pin, or one if its grid carries no
unit; a bottle with no grid pin (a rectifier) supplies none — rectifiers sit
outside the DC model by corpus convention. The BOM's V<n> rows are the
sockets. Netlist instances are the X lines whose model is a tube the reference
files name; each resolves to a socket through sch_map.yaml `symbols:` first,
then by its own name (XV3A -> socket V3, section A; XV3 -> socket V3, one
unlettered section).

The declaration, in meta.yaml:

    sections:   # valve sections the tube complement supplies that the netlist does not instantiate
      V5:  "excluded — tremolo oscillator: a running oscillator has no static DC point"
      V3A: "not drawn — the factory schematic draws only V3B"

A key is a whole socket or one section; a value starts "excluded —",
"not drawn —" or "unused —". A declaration for a section the netlist does
instantiate is stale and fails, like an undeclared gap.

Usage:
    python3 pipeline/check_sections.py              # every circuit; exit 1 on any finding
    python3 pipeline/check_sections.py --amp 6g5    # one circuit
    python3 pipeline/check_sections.py --selftest   # planted faults
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALUE_RE = re.compile(r"^(excluded|not drawn|unused) — \S")
KEY_RE = re.compile(r"^V\d+[A-Z]?$")
REF_RE = re.compile(r"^V(\d+)([A-Z])?$")
GRID_ELEMENTS = {"grid", "control-grid"}


def designation_token(s) -> str:
    """Same rule as validate.py, check_tube_used_in.py and the site's
    designationToken — one bottle name, punctuation and parentheticals stripped."""
    text = str(s or "").split("(", 1)[0].split("·", 1)[0]
    return re.sub(r"[^A-Za-z0-9]", "", text).upper()


def tube_table(root: Path) -> dict[str, tuple[str, int | None]]:
    """token -> (canonical name, sections supplied), off reference/tubes/*.yaml."""
    table: dict[str, tuple[str, int | None]] = {}
    for path in sorted((root / "reference" / "tubes").glob("*.yaml")):
        tube = yaml.safe_load(path.read_text()) or {}
        canon = str(tube.get("name") or tube.get("tube") or path.stem)
        pins = ((tube.get("basing") or {}).get("pins") or {})
        grids = [p for p in pins.values()
                 if isinstance(p, dict) and p.get("element") in GRID_ELEMENTS]
        if not pins:
            sections = None                    # the file declares no basing
        elif not grids:
            sections = 0                       # a rectifier: no grid, no section
        else:
            units = {g.get("unit") for g in grids}
            sections = len(units - {None}) or 1
        names = {designation_token(tube.get("name")), designation_token(tube.get("tube")),
                 designation_token(path.stem)}
        names |= {designation_token(a) for a in (tube.get("also_known_as") or [])}
        for n in names - {""}:
            table.setdefault(n, (canon, sections))
    return table


def _rows(node):
    if isinstance(node, dict):
        if "ref" in node:
            yield node
        for v in node.values():
            yield from _rows(v)
    elif isinstance(node, list):
        for v in node:
            yield from _rows(v)


def load_amp(amp_dir: Path, table) -> dict:
    """Everything check() needs, read off one circuit's files."""
    problems = []
    sockets = {}
    bom = yaml.safe_load((amp_dir / "bom.yaml").read_text()) or {}
    for row in _rows(bom):
        ref = str(row.get("ref", "")).strip()
        if not re.fullmatch(r"V\d+", ref):
            continue
        tok = designation_token(row.get("value"))
        if tok not in table:
            problems.append(f"BOM {ref} is a {row.get('value')!r}, which no reference/tubes file names")
            continue
        canon, n = table[tok]
        if n is None:
            problems.append(f"BOM {ref}: reference file for {canon} declares no basing, so its sections are unknown")
            continue
        sockets[ref] = (canon, n)
    instances = []
    for line in (amp_dir / "netlist.cir").read_text().splitlines():
        m = re.match(r"^\s*X(\S+)\s+.*\s(\S+)\s*$", line)
        if m and designation_token(m.group(2)) in table and table[designation_token(m.group(2))][1]:
            instances.append((m.group(1), m.group(2)))
    sch_map = amp_dir / "sch_map.yaml"
    symbols = {}
    if sch_map.exists():
        symbols = (yaml.safe_load(sch_map.read_text()) or {}).get("symbols") or {}
    meta = yaml.safe_load((amp_dir / "meta.yaml").read_text()) or {}
    return {"sockets": sockets, "instances": instances, "symbols": symbols,
            "declared": meta.get("sections") or {}, "problems": problems}


def check(data: dict) -> list[str]:
    out = list(data.get("problems", []))
    sockets, symbols, declared = data["sockets"], data["symbols"], data["declared"]
    on: dict[str, list[tuple[str, str | None]]] = {s: [] for s in sockets}
    for name, model in data["instances"]:
        ref = str(symbols.get(name, symbols.get("X" + name, name)))
        m = REF_RE.match(ref)
        if not m:
            out.append(f"netlist X{name} ({model}) names no socket — map it in sch_map.yaml symbols:")
            continue
        sock, letter = f"V{m.group(1)}", m.group(2)
        if sock not in on:
            out.append(f"netlist X{name} sits in {sock}, which the BOM does not list as a valve")
            continue
        on[sock].append((name, letter))
    if not isinstance(declared, dict):
        return out + ["meta.yaml sections: must be a mapping of socket/section -> declaration"]
    for key, value in declared.items():
        key = str(key)
        if not KEY_RE.match(key):
            out.append(f"sections: key {key!r} is not a socket (V3) or a section (V3A)")
            continue
        sock = re.match(r"V\d+", key).group(0)
        if sock not in sockets:
            out.append(f"sections: {key} names {sock}, which the BOM does not list as a valve")
        if not VALUE_RE.match(str(value or "")):
            out.append(f"sections: {key} must start \"excluded —\", \"not drawn —\" or \"unused —\" (got {str(value)[:40]!r})")
    for sock, (canon, n) in sockets.items():
        if n == 0:
            continue
        placed = on[sock]
        letters = [l for _, l in placed if l]
        for l in sorted({l for l in letters if letters.count(l) > 1}):
            out.append(f"{sock}{l} is instantiated more than once ({', '.join('X' + nm for nm, lt in placed if lt == l)})")
        whole = sock in declared
        parts = [k for k in map(str, declared) if k.startswith(sock) and len(k) == len(sock) + 1 and k[-1].isalpha()]
        if whole and placed:
            out.append(f"{sock} is declared {str(declared[sock]).split(' —')[0]} but the netlist instantiates "
                       f"{', '.join('X' + nm for nm, _ in placed)} — stale declaration")
        live = []
        for k in parts:
            if k[-1] in letters:
                out.append(f"{k} is declared {str(declared[k]).split(' —')[0]} but the netlist instantiates it — stale declaration")
            else:
                live.append(k)
        covered = n if whole else len(placed) + len(live)
        have = ", ".join("X" + nm for nm, _ in placed) or "nothing"
        if covered < n:
            out.append(f"{sock} ({canon}, {n} section{'s' * (n > 1)}): the netlist instantiates {have}; "
                       f"{n - covered} section{'s' * (n - covered > 1)} neither modelled nor declared in meta.yaml sections:")
        elif covered > n and not whole:
            out.append(f"{sock} ({canon}) supplies {n} section{'s' * (n > 1)} but {covered} are accounted for ({have}"
                       f"{'; declared ' + ', '.join(live) if live else ''})")
    return out


def selftest() -> int:
    table = tube_table(ROOT)
    fails = 0

    def expect(label, cond):
        nonlocal fails
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        fails += not cond

    for name, want in (("12AX7", 2), ("7025", 2), ("12AT7", 2), ("12AY7", 2), ("6SQ7", 1),
                       ("6V6GT", 1), ("EL84", 1), ("5Y3GT", 0), ("GZ34", 0), ("EF86", 1)):
        got = table.get(designation_token(name), (None, "missing"))[1]
        expect(f"{name} supplies {want} section(s) per its basing (got {got})", got == want)

    def base():
        return {"sockets": {"V1": ("12AX7", 2), "V2": ("6V6GT", 1), "V3": ("5Y3GT", 0)},
                "instances": [("V1A", "12AX7"), ("V1B", "12AX7"), ("V2", "6V6GT")],
                "symbols": {}, "declared": {}, "problems": []}

    expect("a complete circuit is clean", check(base()) == [])
    d = base(); d["instances"].remove(("V1B", "12AX7"))
    expect("a dropped section is caught", len(check(d)) == 1)
    d["declared"] = {"V1B": "excluded — planted"}
    expect("...and declaring it clears it", check(d) == [])
    d = base(); d["declared"] = {"V1": "excluded — planted"}
    expect("a whole-socket declaration over instantiated sections is stale", len(check(d)) == 1)
    d = base(); d["declared"] = {"V1B": "not drawn — planted"}
    expect("a section declaration over an instantiated section is stale", len(check(d)) == 1)
    d = base(); d["instances"] = [("V2", "6V6GT")]; d["declared"] = {"V1": "excluded — two sections at once"}
    expect("a whole-socket declaration covers both sections", check(d) == [])
    d = base(); d["instances"].remove(("V1B", "12AX7")); d["declared"] = {"V1B": "skipped — planted"}
    expect("a declaration with an unknown verb is caught", len(check(d)) == 1)
    d = base(); d["instances"][1] = ("V1A", "12AX7")
    expect("a section instantiated twice is caught", any("more than once" in f for f in check(d)))
    d = base(); d["instances"][0] = ("PIA", "12AX7")
    expect("an instance that names no socket is caught", len(check(d)) == 2)
    d["symbols"] = {"PIA": "V1A"}
    expect("...and sch_map symbols resolve it", check(d) == [])
    d = base(); d["declared"] = {"V9": "excluded — planted"}
    expect("a declaration for a socket the BOM lacks is caught", len(check(d)) == 1)
    d = base(); d["instances"] = [("V1", "12AX7"), ("V2", "6V6GT")]
    expect("one unlettered instance of a dual triode leaves a section to account for", len(check(d)) == 1)

    # a real circuit: delete one tube instance from a clean netlist and the gate must see it
    for amp in sorted(p for p in (ROOT / "amps").iterdir() if (p / "netlist.cir").exists()):
        real = load_amp(amp, table)
        if check(real) == [] and real["instances"]:
            mutated = dict(real, instances=real["instances"][1:])
            expect(f"deleting X{real['instances'][0][0]} from the real {amp.name} netlist is caught",
                   len(check(mutated)) == 1)
            break
    print(f"selftest: {fails} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--amp")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    table = tube_table(ROOT)
    amps = [ROOT / "amps" / a.amp] if a.amp else sorted(
        p for p in (ROOT / "amps").iterdir() if (p / "netlist.cir").exists() and not p.name.startswith("_"))
    supplied = placed = declared = bad = 0
    for amp in amps:
        data = load_amp(amp, table)
        supplied += sum(n for _, n in data["sockets"].values())
        placed += len(data["instances"])
        declared += len(data["declared"]) if isinstance(data["declared"], dict) else 0
        for f in check(data):
            print(f"FAIL {amp.name}: {f}")
            bad += 1
    print(f"checked {len(amps)} circuit(s): {supplied} valve section(s) supplied, {placed} instantiated, "
          f"{declared} declaration(s); {bad} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
