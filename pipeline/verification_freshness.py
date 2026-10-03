#!/usr/bin/env python3
"""The facts fingerprint: is a verified circuit still the circuit the
maintainer reviewed?

------------------------------------------------------------------------------
WHY
------------------------------------------------------------------------------
`verification.status: verified` is granted once, by the maintainer, on a given
day. The fact files go on changing after that — a V1 audit redraws a tone
network, a BOM value is corrected, a disputed chart figure is settled — and
until this gate nothing on the badge said so: a verified badge read the same
the day it was granted and after a dozen fact fixes nobody re-reviewed.

Git history cannot answer "what changed since the review": CI and Workers
Builds clone shallowly. So the review is pinned to CONTENT instead. When the
maintainer grants or re-confirms the badge, `pipeline/stamp_verification.py`
writes this fingerprint into meta.yaml as `verification.facts_sha256`, with
`verification.reviewed: <date>`. Any later change to the facts changes the
fingerprint, and the amp goes on the worklist below until it is re-stamped.

------------------------------------------------------------------------------
WHAT IS HASHED (the facts) AND WHAT IS NOT (the cosmetics)
------------------------------------------------------------------------------
A SHA-256 over a canonical JSON form of, per amp:

  netlist      netlist.cir element and directive lines: `*` comment lines and
               `;` / `$` inline comments dropped, `+` continuations joined,
               whitespace collapsed, lower-cased (SPICE is case-blind), sorted.
  voltages     voltages.yaml, per node: chart value, tolerance and `disputed`
               flag. `note`, `dispute_note` and `source` are prose and dropped.
               Numbers are compared as numbers (430 and 430.0 are one value).
  bom          bom.yaml, per item: ref, part and value (the value carries the
               rating: "0.02 µF · 400 V"). `role` and `notes` are prose and
               dropped.
  sheet nets   the schematic's NET PARTITION: for every net, the set of symbol
               pins on it (`V1A.1`), built by verify_sheet_vs_board's own
               extraction (its `Sheet`, i.e. sch_nets). Net labels are names,
               not connections, and are dropped — except ground, kept as `GND`.
               Each valve section's stated datasheet unit (`Basing_unit`) is
               included, since a section moved to the other unit changes which
               socket pins it is wired to without changing a pin's net.
  board nets   the board's NET PARTITION: for every net, the set of part
               terminals on it (`RL1.a`, `V2.pin6`, `VR1.lug2`, `GND`), built by
               verify_sheet_vs_board's own extraction (its `Board`, i.e.
               verify_layout_nets.LayoutGraph). Bare eyelet nodes (`@r,c`)
               are coordinates and are dropped.
  polarity     every electrolytic the board draws (parts[] rows and off-board
               `kind: part` stubs whose BOM part is an electrolytic, as
               verify_layout_nets.board_electrolytics picks them): [ref, the
               layout's declared `plus:` lead]. A can with no `plus:` is
               recorded as None — never render_layouts' position default — so
               declaring, moving or removing a '+' is a change.
  heaters      the layout's `heaters:` block, as check_heaters.check_layout
               reads it: per circuit its id, supply volts, grounded_leg,
               winding_ct and humdinger part(s); per socket its feed and return
               pins (each sorted); per pilot lamp its return. `winding`,
               `source` and pilot `source` text are prose and dropped. Whether
               the layer is declared `heaters_pending` / `heaters_unsourced` is
               kept as a flag, its prose is not. Circuits are sorted.

Every collection is sorted, so ordering never matters. Coordinates, `via`
waypoints, run colours, fonts, symbol and label positions and every comment
are outside the hash by construction: a re-route, a re-lettering or a reworded
note does not ask for a re-review, a changed value, net or dispute does.

The sheet partition is read RAW: no `series_bridge` declaration from the
layout is folded in (verify_sheet_vs_board does that for its comparison).
Declarations are about how two drawings are compared, not what either draws.

FINGERPRINT_VERSION is folded into the hash. Changing the canonical form
above means bumping it, which re-pends every stamped amp — by design: a stamp
records what the maintainer reviewed under one definition of "the facts".

------------------------------------------------------------------------------
THE WORKLIST, AND WHAT CI DOES WITH IT
------------------------------------------------------------------------------
`reference/verification-freshness.yaml` lists every verified amp whose current
fingerprint differs from its stamp, or that carries no stamp: its current
fingerprint, the stamped one (or null) and the review date (or null). A normal
run fails ONLY if that committed file is not what a fresh run produces — the
same drift gate as reference/sheet-board.yaml and reference/heaters.yaml. An
amp being pending never fails CI: fact fixes must keep landing, and the site
says "re-review pending" for exactly the amps this file lists.

Only the maintainer stamps (pipeline/stamp_verification.py). Agents and
contributors never run it — the same rule as for `verification.status`.

    python3 pipeline/verification_freshness.py            # worklist drift gate (alias --check)
    python3 pipeline/verification_freshness.py 5f6a       # one amp's fingerprint and state
    python3 pipeline/verification_freshness.py --export   # rewrite the worklist
    python3 pipeline/verification_freshness.py --selftest # what flips the hash, what doesn't
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_layout_nets import GND, ROOT                                  # noqa: E402
from render_layouts import category                                       # noqa: E402
from verify_sheet_vs_board import Board, Sheet, _swap_refs               # noqa: E402

AMPS = ROOT / "amps"
WORKLIST = ROOT / "reference" / "verification-freshness.yaml"
FINGERPRINT_VERSION = 1


# ===========================================================================
# canonical facts
# ===========================================================================
def _num(x):
    """A YAML scalar as a comparable fact: numbers as floats, so 430 == 430.0."""
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, (int, float)):
        return repr(float(x))
    return " ".join(str(x).split())


def _text(x):
    return None if x is None else " ".join(str(x).split())


def netlist_facts(text: str) -> list:
    lines: list = []
    for raw in text.replace("\r", "").split("\n"):
        s = raw.strip()
        if not s or s.startswith("*"):
            continue
        s = re.split(r"\s;|^;|\s\$\s|\s\$$", s, maxsplit=1)[0].strip()
        if not s:
            continue
        if s.startswith("+") and lines:
            lines[-1] += " " + s[1:].strip()
            continue
        lines.append(s)
    return sorted(" ".join(s.lower().split()) for s in lines)


def voltages_facts(data: dict) -> list:
    out = []
    for node, e in ((data or {}).get("nodes") or {}).items():
        e = e if isinstance(e, dict) else {"chart": e}
        out.append([str(node), _num(e.get("chart")), _num(e.get("tol_pct")),
                    bool(e.get("disputed", False))])
    return sorted(out)


def bom_facts(data: dict) -> list:
    out = []
    for it in (data or {}).get("items") or []:
        if not isinstance(it, dict):
            continue
        out.append([_text(it.get("ref")), _text(it.get("part")), _text(it.get("value"))])
    return sorted(out, key=lambda r: [("" if v is None else v) for v in r])


def _partition(groups) -> list:
    return sorted(sorted(g) for g in groups if g)


def sheet_facts(amp_id: str, amp_dir: Path) -> dict:
    sh = Sheet(amp_id, amp_dir / "schematic.kicad_sch", None)
    groups = []
    for members in sh.G.members().values():
        g = set()
        for m in members:
            m = str(m)
            if m == "<GND>":
                g.add(GND)
            elif not m.startswith("<"):
                g.add(m)
        groups.append(g)
    return {"nets": _partition(groups),
            "units": sorted([ref, str(u)] for ref, u in sh.units.items())}


def board_facts(amp_id: str, amp_dir: Path) -> dict:
    """The board's net partition, its electrolytics' declared '+' leads and its
    heater declarations, all read off one verify_sheet_vs_board `Board`."""
    bd = Board(amp_id, amp_dir)
    return {"nets": _partition({str(m) for m in members if not str(m).startswith("@")}
                               for members in bd.LG.nets().values()),
            "polarity": polarity_facts(bd.R),
            "heaters": heater_facts(bd.layout)}


def polarity_facts(R) -> list:
    """[ref, declared '+' lead] for every electrolytic the board draws — the
    parts[] rows and off-board `kind: part` stubs verify_layout_nets'
    board_electrolytics() judges, picked by the same BOM category. The lead is
    the layout's own `plus:`, never render_layouts' position default: a can
    with no declaration is recorded as None, so declaring one is a change."""
    def electro(ref):
        return category(str((R.bom.get(ref) or {}).get("part", ""))) == "electro"
    out = [[str(p["ref"]), p.get("plus")] for p in R.parts
           if p.get("ref") and electro(p["ref"])]
    out += [[str(it["ref"]), it.get("plus")] for it in R.offboard
            if it.get("kind") == "part" and it.get("ref") and it.get("id")
            and electro(it["ref"])]
    return sorted(out, key=lambda r: (r[0], str(r[1])))


def _pins(x) -> list:
    try:
        return sorted(int(p) for p in (x or []))
    except (TypeError, ValueError):
        return [str(x)]


def heater_facts(layout: dict) -> dict:
    """The `heaters:` declarations, as check_heaters.check_layout() reads them:
    per circuit its id, supply volts, grounded_leg, winding_ct and humdinger
    part(s); per socket its feed and return pins; per pilot lamp its return.
    `winding`, `source` and every pilot `source` are prose and dropped. Whether
    the layer is declared pending or unsourced is kept as a flag; its prose is
    not."""
    circuits = []
    for c in layout.get("heaters") or []:
        if not isinstance(c, dict):
            circuits.append(_num(c))
            continue
        hum = c.get("humdinger")
        hum = [hum] if isinstance(hum, str) else [str(x) for x in (hum or [])]
        circuits.append({
            "id": _text(c.get("id")),
            "volts": _num(c.get("volts")),
            "grounded_leg": _text(c.get("grounded_leg")),
            "winding_ct": _text(c.get("winding_ct")),
            "humdinger": sorted(hum),
            "sockets": {str(sid): ([_pins(g.get("feed")), _pins(g.get("return"))]
                                   if isinstance(g, dict) else _num(g))
                        for sid, g in (c.get("sockets") or {}).items()},
            "pilot": {str(lid): (_text(e.get("return")) if isinstance(e, dict) else _num(e))
                      for lid, e in (c.get("pilot") or {}).items()},
        })
    return {"circuits": sorted(circuits, key=lambda c: json.dumps(c, sort_keys=True)),
            "pending": bool(str(layout.get("heaters_pending", "") or "").strip()),
            "unsourced": bool(str(layout.get("heaters_unsourced", "") or "").strip())}


def facts(amp_id: str, amp_dir: "Path | None" = None) -> dict:
    """Every hashed fact of one amp, canonical. A missing file is recorded as
    None (a verified amp carries all of them; validate.py enforces that)."""
    d = amp_dir or AMPS / amp_id

    def load(name):
        p = d / name
        return yaml.safe_load(p.read_text()) if p.exists() else None

    has_sheet = (d / "schematic.kicad_sch").exists()
    has_board = (d / "layout.yaml").exists()
    return {
        "version": FINGERPRINT_VERSION,
        "netlist": netlist_facts((d / "netlist.cir").read_text())
        if (d / "netlist.cir").exists() else None,
        "voltages": voltages_facts(load("voltages.yaml")) if (d / "voltages.yaml").exists() else None,
        "bom": bom_facts(load("bom.yaml")) if (d / "bom.yaml").exists() else None,
        "sheet": sheet_facts(amp_id, d) if has_sheet else None,
        "board": board_facts(amp_id, d) if has_board else None,
    }


def fingerprint(amp_id: str, amp_dir: "Path | None" = None) -> str:
    blob = json.dumps(facts(amp_id, amp_dir), sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


# ===========================================================================
# per-amp state and the worklist
# ===========================================================================
def _date(x):
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()[:10]
    return None if x is None else str(x)


def verification_of(amp_dir: Path) -> dict:
    meta = yaml.safe_load((amp_dir / "meta.yaml").read_text()) or {}
    return meta.get("verification") or {}


def state(amp_id: str, amp_dir: "Path | None" = None) -> dict:
    d = amp_dir or AMPS / amp_id
    v = verification_of(d)
    current = fingerprint(amp_id, d)
    stamped = v.get("facts_sha256")
    stamped = None if stamped is None else str(stamped)
    return {"current": current, "stamped": stamped, "reviewed": _date(v.get("reviewed")),
            "verified": _date(v.get("date")), "pending": stamped != current}


def verified_ids(amps_dir: Path = AMPS) -> list:
    return sorted(d.name for d in amps_dir.iterdir()
                  if d.is_dir() and (d / "meta.yaml").exists()
                  and verification_of(d).get("status") == "verified")


def worklist(amps_dir: Path = AMPS) -> dict:
    amps: dict = {}
    ids = verified_ids(amps_dir)
    for amp_id in ids:
        s = state(amp_id, amps_dir / amp_id)
        if not s["pending"]:
            continue
        amps[amp_id] = {
            "current": s["current"],
            "stamped": s["stamped"],
            "reviewed": s["reviewed"],
            "verified": s["verified"],
            "reason": "never stamped" if s["stamped"] is None else "facts changed since review",
        }
    summary = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "verified": len(ids),
        "pending": len(amps),
        "never_stamped": sum(1 for a in amps.values() if a["stamped"] is None),
        "changed_since_review": sum(1 for a in amps.values() if a["stamped"] is not None),
    }
    return {"summary": summary, "amps": amps}


WORKLIST_HEADER = """\
# GENERATED - pipeline/verification_freshness.py --export. Do not hand-edit; a
# run that disagrees with this file fails the gate, the same way
# reference/sheet-board.yaml and reference/heaters.yaml are held to what a
# fresh run produces.
#
# WHAT THIS IS. Every verified circuit whose facts have changed since the
# maintainer last reviewed them, or that has never been stamped. The facts are
# netlist.cir, the voltages.yaml chart values, tolerances and disputed flags,
# the bom.yaml refs, parts and values, the schematic's and the board's net
# partitions, the board's declared electrolytic '+' leads and its heater
# declarations - no comments, coordinates, routes or fonts (see the gate's
# docstring). `verification.facts_sha256` in meta.yaml records the fingerprint
# the maintainer reviewed; `current` is what the files hash to now.
#
# HOW TO READ IT. An amp listed here is still verified, and its page says so,
# with the date - followed by "changes since then are awaiting maintainer
# re-review". `reason` is `never stamped` (no review on record) or `facts
# changed since review` (`stamped` differs from `current`). Being listed never
# fails CI: fact fixes keep landing, and this file is how they stay visible.
#
# CLEARING AN ENTRY. The maintainer re-reviews the amp and runs
# `pipeline/stamp_verification.py <id>`, which stamps meta.yaml and re-exports
# this file. Only the maintainer stamps; agents and contributors never do. A
# contributor whose change moves a fingerprint re-exports this file with
# `pipeline/verification_freshness.py --export`, which never stamps anything.
"""


def export_worklist(amps_dir: Path = AMPS, path: Path = WORKLIST) -> dict:
    data = worklist(amps_dir)
    path.write_text(WORKLIST_HEADER
                    + yaml.safe_dump(data, sort_keys=True, width=100, allow_unicode=True))
    return data


def check_worklist(amps_dir: Path = AMPS, path: Path = WORKLIST) -> list:
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    if not path.exists():
        return [f"{rel} is missing - regenerate with pipeline/verification_freshness.py --export"]
    committed = yaml.safe_load(path.read_text()) or {}
    fresh = worklist(amps_dir)
    if committed == fresh:
        return []
    out = [f"DRIFT: {rel} is not what a fresh run produces - "
           f"regenerate with pipeline/verification_freshness.py --export"]
    if committed.get("summary") != fresh.get("summary"):
        out.append(f"    committed summary: {committed.get('summary')}")
        out.append(f"    fresh     summary: {fresh.get('summary')}")
    ca, fa = committed.get("amps") or {}, fresh.get("amps") or {}
    changed = sorted(k for k in set(ca) | set(fa) if ca.get(k) != fa.get(k))
    if changed:
        out.append(f"    amps that differ: {', '.join(changed)}")
    return out


# ===========================================================================
# self-test — on temp copies; the committed tree is never touched
# ===========================================================================
SELFTEST_AMP = "5f6a"
HEATER_AMP = SELFTEST_AMP     # declares its heater layer (winding-ct, five sockets)


def _sub(path: Path, old: str, new: str, count: int = 1):
    t = path.read_text()
    assert old in t, f"selftest: {old!r} not in {path.name}"
    path.write_text(t.replace(old, new, count))


def _re_sub(path: Path, pattern: str, repl, flags=re.M):
    t = path.read_text()
    t2, n = re.subn(pattern, repl, t, count=1, flags=flags)
    assert n == 1, f"selftest: /{pattern}/ not in {path.name}"
    path.write_text(t2)


def _layout_runs(amp_dir: Path, fn):
    p = amp_dir / "layout.yaml"
    d = yaml.safe_load(p.read_text())
    fn(d["runs"])
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))


def _first_run(runs, pred):
    for r in runs:
        if pred(r):
            return r
    raise AssertionError("selftest: no run matches")


def _is_term(x):
    return isinstance(x, str) and "." in x


def _move_lead(runs):
    """Land a run's far end on a different net: a real wiring change."""
    r = _first_run(runs, lambda r: _is_term(r.get("from")) and _is_term(r.get("to")))
    other = _first_run(runs, lambda o: _is_term(o.get("to")) and o.get("to") not in
                       (r.get("from"), r.get("to")) and o.get("from") not in
                       (r.get("from"), r.get("to")))
    r["to"] = other["to"]


def _reroute(runs):
    """Change every waypoint: the same wire drawn down a different lane."""
    for r in runs:
        if r.get("via"):
            r["via"] = [[float(x) + 0.37, float(y) - 0.21] for x, y in r["via"]]
        else:
            r["via"] = [[0.5, -0.5]]


def _sheet_cosmetics(amp_dir: Path):
    """Fonts and a property's lettering position only — no symbol, wire or
    label moves, so no connection can change."""
    p = amp_dir / "schematic.kicad_sch"
    t = p.read_text()
    assert "(font (size 1.27 1.27))" in t
    t = t.replace("(font (size 1.27 1.27))", "(font (size 1.5 1.5))")
    i = t.rindex('(property "Value"')
    j = t.index("\n", i)
    line = re.sub(r"\(at ([-\d.]+) ([-\d.]+)",
                  lambda m: f"(at {float(m.group(1)) + 2.54:g} {float(m.group(2)) - 1.27:g}",
                  t[i:j], count=1)
    assert line != t[i:j]
    p.write_text(t[:i] + line + t[j:])


def _comments(amp_dir: Path):
    _sub(amp_dir / "netlist.cir", "* ", "* (reworded) ", 1)
    _re_sub(amp_dir / "netlist.cir", r"^(R\S+[^\n;]*)$", r"\1   ; an inline remark")
    _re_sub(amp_dir / "voltages.yaml", r'note: "', 'note: "Reworded. ')
    _re_sub(amp_dir / "voltages.yaml", r'^source: ', '# a new comment line\nsource: ')
    _re_sub(amp_dir / "bom.yaml", r'role: "', 'role: "Reworded ')
    _re_sub(amp_dir / "layout.yaml", r'^runs:', '# a new comment line\nruns:')
    _re_sub(amp_dir / "meta.yaml", r'^verification:', '# a new comment line\nverification:')


def _bom_value(amp_dir: Path):
    _re_sub(amp_dir / "bom.yaml", r'value: "(\d+) kΩ', lambda m: f'value: "{int(m.group(1)) + 1} kΩ')


def _netlist_value(amp_dir: Path):
    _re_sub(amp_dir / "netlist.cir", r"^(R\S+\s+\S+\s+\S+\s+)(\d+)(k?)\b",
            lambda m: f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}")


def _chart_value(amp_dir: Path):
    _re_sub(amp_dir / "voltages.yaml", r"chart: (\d+)", lambda m: f"chart: {int(m.group(1)) + 5}")


def _toggle_disputed(amp_dir: Path):
    p = amp_dir / "voltages.yaml"
    t = p.read_text()
    if "disputed: true" in t:
        p.write_text(t.replace("disputed: true", "disputed: false", 1))
    else:
        _re_sub(p, r"tol_pct: (\d+)", r"tol_pct: \1, disputed: true")


def _yaml_numbers(amp_dir: Path):
    """430 -> 430.0: the same number written another way."""
    _re_sub(amp_dir / "voltages.yaml", r"chart: (\d+)([,\s}])", r"chart: \1.0\2")


def selftest() -> int:
    from stamp_verification import StampRefused, stamp   # the tool under test

    tmp = Path(tempfile.mkdtemp(prefix="cx-freshness-"))
    fails: list = []
    n = 0
    base = fingerprint(SELFTEST_AMP)

    def fresh_copy(name: str) -> Path:
        d = tmp / name / "amps" / SELFTEST_AMP
        shutil.copytree(AMPS / SELFTEST_AMP, d)
        return d

    def case(label: str, mutate, flips: bool):
        nonlocal n
        n += 1
        d = fresh_copy(f"case{n}")
        try:
            mutate(d)
            got = fingerprint(SELFTEST_AMP, d)
        except Exception as e:      # noqa: BLE001 — a crash is a failed case, named
            fails.append(f"{label}: {type(e).__name__}: {e}")
            print(f"  FAIL  {label}: {type(e).__name__}: {e}")
            return
        ok = (got != base) == flips
        want = "flips" if flips else "holds"
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}: fingerprint {want}"
              + ("" if ok else f" — it {'held' if got == base else 'flipped'}"))
        if not ok:
            fails.append(label)

    print(f"verification_freshness self-test on temp copies of {SELFTEST_AMP} ({tmp})")
    f0 = facts(SELFTEST_AMP)
    for part in ("netlist", "voltages", "bom"):
        if not f0[part]:
            fails.append(f"no {part} facts extracted")
    for part, key in (("sheet", "nets"), ("board", "nets"), ("board", "polarity")):
        if not (f0[part] or {}).get(key):
            fails.append(f"no {part} {key} extracted")
    hf = facts(HEATER_AMP)["board"]["heaters"]["circuits"]
    if not hf:
        fails.append(f"no heater circuits extracted from {HEATER_AMP}")
    board = f0["board"] or {}
    print(f"  extracted {len(f0['netlist'])} netlist lines, {len(f0['voltages'])} nodes, "
          f"{len(f0['bom'])} BOM items, {len((f0['sheet'] or {}).get('nets', []))} sheet nets, "
          f"{len(board.get('nets', []))} board nets, {len(board.get('polarity', []))} "
          f"electrolytics; {len(hf)} heater circuits on {HEATER_AMP}")
    try:
        case("unchanged copy", lambda d: None, False)
        case("BOM value", _bom_value, True)
        case("netlist value", _netlist_value, True)
        case("voltage chart value", _chart_value, True)
        case("disputed flag", _toggle_disputed, True)
        case("sheet net (two resistors' designators exchanged)",
             lambda d: _swap_refs(d, "RG1", "RL1"), True)
        case("board net (a lead moved to another net)",
             lambda d: _layout_runs(d, _move_lead), True)
        case("re-route (every via waypoint moved)", lambda d: _layout_runs(d, _reroute), False)
        case("layout.yaml round-tripped (formatting, comments gone)",
             lambda d: _layout_runs(d, lambda runs: None), False)
        case("schematic fonts and a property's position", _sheet_cosmetics, False)
        case("comments, notes and roles reworded", _comments, False)
        case("a chart number written as a float", _yaml_numbers, False)
        case("an electrolytic's '+' moved to its other lead",
             lambda d: _re_sub(d / "layout.yaml", r"plus: ([ab])",
                               lambda m: "plus: " + ("a" if m.group(1) == "b" else "b")), True)
        case("an electrolytic's '+' declaration removed",
             lambda d: _re_sub(d / "layout.yaml", r" *, *plus: [ab]", ""), True)
        case("a heater socket's legs redeclared (12.6 V series grouping)",
             lambda d: _sub(d / "layout.yaml", "V1: { feed: [4, 5], return: [9] }",
                            "V1: { feed: [4], return: [5] }"), True)
        case("a heater circuit's grounded leg redeclared",
             lambda d: _sub(d / "layout.yaml", "grounded_leg: winding-ct\n    winding_ct: PT.green-yellow",
                            "grounded_leg: return"), True)
        case("heater winding and source prose reworded",
             lambda d: (_re_sub(d / "layout.yaml", r'^(\s+winding: ")', r"\1Reworded: "),
                        _re_sub(d / "layout.yaml", r"^(\s+source: >-\n\s+)", r"\1Reworded. ")), False)

        # stamp -> drops off the worklist; a fact change -> back on it
        n += 1
        d = fresh_copy("stamp")
        amps_dir = d.parent
        before = (d / "meta.yaml").read_text()
        wl0 = worklist(amps_dir)
        steps = [("listed before any stamp, as never stamped",
                  wl0["amps"].get(SELFTEST_AMP, {}).get("reason") == "never stamped")]
        stamp(SELFTEST_AMP, amps_dir, today="2026-10-03", export=False)
        after = (d / "meta.yaml").read_text()
        added = [ln for ln in after.splitlines() if ln not in before.splitlines()]
        steps.append(("the stamp adds exactly two lines and rewrites none",
                      len(added) == 2 and all(ln in after.splitlines() for ln in before.splitlines())
                      and any(ln.strip().startswith("facts_sha256: ") for ln in added)
                      and "  reviewed: 2026-10-03" in added))
        steps.append(("stamp == fingerprint", state(SELFTEST_AMP, d)["stamped"] == base))
        steps.append(("off the worklist once stamped", SELFTEST_AMP not in worklist(amps_dir)["amps"]))
        stamp(SELFTEST_AMP, amps_dir, today="2026-10-04", export=False)
        again = (d / "meta.yaml").read_text()
        steps.append(("a re-stamp replaces its two lines in place",
                      len(again.splitlines()) == len(after.splitlines())
                      and "  reviewed: 2026-10-04" in again.splitlines()))
        _bom_value(d)
        e = worklist(amps_dir)["amps"].get(SELFTEST_AMP) or {}
        steps.append(("a fact change puts it back, as changed since review",
                      e.get("reason") == "facts changed since review"
                      and e.get("stamped") == base and e.get("current") != base))
        # a draft amp is refused, and its meta.yaml is left as it was
        meta = d / "meta.yaml"
        meta.write_text(re.sub(r"^(\s+status:) verified", r"\1 draft", meta.read_text(),
                               count=1, flags=re.M))
        draft = meta.read_text()
        try:
            stamp(SELFTEST_AMP, amps_dir, today="2026-10-05", export=False)
            refused = False
        except StampRefused:
            refused = True
        steps.append(("a draft amp is refused, untouched", refused and meta.read_text() == draft))
        steps.append(("a draft amp is not on the worklist", SELFTEST_AMP not in worklist(amps_dir)["amps"]))
        for label, ok in steps:
            print(f"  {'ok  ' if ok else 'FAIL'}  stamp: {label}")
            if not ok:
                fails.append(f"stamp: {label}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fails:
        print(f"SELFTEST FAIL - {len(fails)} case(s): {', '.join(fails)}")
        return 1
    print("SELFTEST PASS - values, nets, disputes, '+' leads and heater declarations flip "
          "the fingerprint; routes, fonts, positions and comments do not; a stamp clears "
          "the amp until its facts change")
    return 0


# ===========================================================================
def main(argv: list) -> int:
    if "--selftest" in argv:
        return selftest()
    ids = [a for a in argv if not a.startswith("-")]
    if ids:
        for amp_id in ids:
            d = AMPS / amp_id
            v = verification_of(d)
            s = state(amp_id, d)
            print(f"{amp_id}: status {v.get('status')}, fingerprint {s['current']}")
            print(f"  stamped  {s['stamped'] or '(none)'}"
                  + (f", reviewed {s['reviewed']}" if s["reviewed"] else ""))
            if v.get("status") != "verified":
                print("  not verified - no review is tracked")
            else:
                print("  re-review pending" if s["pending"] else "  current - matches the stamp")
        return 0
    print("verification freshness: has a verified circuit's facts changed since the "
          "maintainer's review?")
    if "--export" in argv:
        data = export_worklist()
    else:
        data = worklist()
    for amp_id, e in sorted(data["amps"].items()):
        print(f"  {amp_id:<14} re-review pending ({e['reason']})")
    sm = data["summary"]
    print(f"{sm['verified']} verified; {sm['pending']} pending re-review "
          f"({sm['never_stamped']} never stamped, {sm['changed_since_review']} changed since review)")
    if "--export" in argv:
        print(f"exported {WORKLIST.relative_to(ROOT)}")
        return 0
    errs = check_worklist()
    for line in errs:
        print(line if line.startswith("    ") else f"FAIL {line}")
    if not errs:
        print("worklist current - a pending amp never fails this gate; a stale worklist does")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
