#!/usr/bin/env python3
"""Export each documented circuit's output-stage DC context to reference/loadlines.yaml.

The load-line explorer at /reference/guides/load-lines/ solves the Koren plate-current
equations in the browser. Its per-amp presets must start from the *corpus's own*
numbers, not from anything typed by hand, so this script reads them out of the
material the gates already check:

  * amps/<id>/netlist.cir  — which power tube, which plate/screen/grid/cathode nodes,
                             how many bottles share the stage, the cathode resistor,
                             and (for fixed bias) the bias supply.
  * ngspice operating point — the plate-node, screen-node and cathode-node voltages,
                             plus each output tube's plate and screen current straight
                             off the model's own behavioural sources.
  * amps/<id>/bom.yaml     — the output transformer's primary impedance, where the
                             drawing prints one. Where it does not, the field stays
                             null and carries the BOM's own wording; nothing invented.

The simulated currents and voltages are written out as a parity reference: the browser
solver runs the same Koren maths on the same fitted parameters, so its answer must
match this file. The page shows both numbers side by side.

Drift gate: `python3 pipeline/export_loadlines.py --check` fails when the checked-in
file no longer says what this run simulates. The comparison is value-level
(verify_amps.numeric_drift), never byte-level: ngspice is deterministic on a fixed
netlist only within one build, and across builds (Homebrew macOS vs the CI runner's
apt ngspice) the last rounded digit of a node can flip — solver provenance, not
corpus drift.

Consistency gate: drift alone cannot see a field that is *consistently* wrong, because
a fresh export reproduces the same wrong value and the comparison passes forever. That
is exactly how eleven fixed-bias circuits shipped a null `grid_supply_node` — the old
resolver only looked one resistor out from the first output tube's grid, so it found
the rail whenever the netlist put the grid leak on the grid pin and missed it whenever
a grid stopper stood in between. So `--check` also asserts the file's internal
contract: every fixed-bias stage names a bias rail or says in words why it cannot, and
the rail it names carries the voltage the grid node actually sits at.
`--selftest` plants each fault class on the committed file and proves the assertion
fires; `--check` runs it too, so the proof travels with the gate.

Usage:
    python3 pipeline/export_loadlines.py            # regenerate reference/loadlines.yaml
    python3 pipeline/export_loadlines.py --check     # fail if the checked-in file drifts
    python3 pipeline/export_loadlines.py --selftest  # prove the consistency gate fires
"""
from __future__ import annotations

import copy
import re
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

import yaml

# One definition of "what counts as drift" for both generated reference files —
# see numeric_drift's docstring for why bytes were the wrong thing to compare.
from verify_amps import numeric_drift

ROOT = Path(__file__).resolve().parent.parent
AMPS = ROOT / "amps"
OUT = ROOT / "reference" / "loadlines.yaml"

# Output valves the explorer can draw. Not every 4-terminal pentode qualifies: the
# AC15's EF86 is a small-signal pentode sitting on a 220 kΩ anode load, and its
# milliamp of plate current is not an output stage. So this stays an explicit list of
# the valves the corpus documents in output service — but it is *gated*, not trusted:
# every circuit must yield exactly one output stage, and build() fails naming the
# pentodes it saw if one does not. That gate is what caught the EL84 missing here
# when the Vox AC15 joined the corpus; a frozen list that silently drops a circuit is
# the failure mode this file is most exposed to.
POWER_TUBES = {"6V6GT", "5881", "6L6GC", "KT66", "EL34", "EL84", "6973"}

class QStr(str):
    """A string that must survive both YAML loaders. Circuit ids like 5e1 and tube
    names like 5881 are read as numbers by js-yaml (the site's loader) unless they
    are quoted — the same trap pipeline/validate.py guards history files against."""


yaml.SafeDumper.add_representer(
    QStr, lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'"))


HEADER = """\
# Output-stage DC context for every documented circuit — GENERATED FILE.
#
# Written by pipeline/export_loadlines.py from each amp's own netlist.cir, its
# ngspice operating point, and its bom.yaml. Do not edit by hand; re-run the
# script (`python3 pipeline/export_loadlines.py`) and commit the result.
#
# Every voltage and current below is simulated, not measured. The published
# chart values live in amps/<id>/voltages.yaml and are gated separately by
# pipeline/verify_amps.py. Where a drawing prints no output-transformer primary
# impedance, ot_primary_z is null and ot_primary_note repeats the parts list's
# own wording rather than inventing a figure.
#
# grid_supply_basis says what kind of answer grid_supply_node/_v are, so a null
# never has to be guessed at:
#
#   cathode-bias  the stage biases itself across its cathode resistor; no
#                 negative supply exists to name, and node and volts are null.
#   source        the rail is a DC source in the netlist, and grid_supply_v is
#                 the value that source statement carries — nothing derived.
#   network       the rail is a node the netlist derives from a DC source
#                 through its own resistive network, and grid_supply_v is that
#                 node's simulated DC level. grid_supply_note names the source.
#   unresolved    the netlist holds a fixed-bias stage whose rail this script
#                 could not follow. grid_supply_note says what it looked for and
#                 what it found. This is a defect to fix, never a resting state.
"""


# --------------------------------------------------------------------- netlist
def parse_value(tok: str) -> float | None:
    """SPICE value token -> float. 470, 1.5k, 22k, 1meg, 250."""
    m = re.match(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)(meg|k|m|g|u|n|p|)$", tok.strip(), re.I)
    if not m:
        return None
    mult = {"": 1.0, "k": 1e3, "meg": 1e6, "m": 1e-3, "g": 1e9,
            "u": 1e-6, "n": 1e-9, "p": 1e-12}
    return float(m.group(1)) * mult[m.group(2).lower()]


def read_deck(path: Path) -> list[list[str]]:
    """Netlist lines as token lists, comments and blanks dropped."""
    rows = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("*") or s.startswith("."):
            continue
        rows.append(s.split())
    return rows


def find_output_stage(rows: list[list[str]]) -> dict | None:
    """Locate the output stage: every X-instance of a power tube, grouped by the
    (plate, cathode) pair they share. Returns None for circuits with no power tube."""
    tubes = []
    for t in rows:
        if not t[0].upper().startswith("X") or len(t) != 6:
            continue
        p, g2, g1, k, model = t[1], t[2], t[3], t[4], t[5].upper()
        if model in POWER_TUBES:
            tubes.append({"ref": t[0], "plate": p, "screen": g2, "grid": g1,
                          "cathode": k, "model": model})
    if not tubes:
        return None
    first = tubes[0]
    same = [x for x in tubes
            if x["plate"] == first["plate"] and x["cathode"] == first["cathode"]]
    return {"tubes": same, "n": len(same), "model": first["model"],
            "plate": first["plate"], "cathode": first["cathode"],
            "screens": [x["screen"] for x in same],
            "grids": [x["grid"] for x in same]}


def cathode_resistor(rows: list[list[str]], node: str) -> float | None:
    """Total resistance from the shared cathode node to ground (parallel combination)."""
    if node == "0":
        return None
    conductance = 0.0
    found = False
    for t in rows:
        if not t[0].upper().startswith("R") or len(t) < 4:
            continue
        a, b, val = t[1], t[2], parse_value(t[3])
        if val is None or val <= 0:
            continue
        if {a, b} == {node, "0"}:
            conductance += 1.0 / val
            found = True
    return (1.0 / conductance) if found else None


def dc_sources(rows: list[list[str]]) -> dict[str, float]:
    out = {}
    for t in rows:
        if t[0].upper().startswith("V") and len(t) >= 5 and t[3].upper() == "DC":
            v = parse_value(t[4])
            if v is not None:
                out[t[1]] = v
    return out


def resistor_graph(rows: list[list[str]]) -> dict[str, set[str]]:
    """Node adjacency over resistors only. Caps are DC-open and the tube models draw
    no grid current, so at DC the grid-return path is made of resistors and nothing
    else — which is what makes a resistive walk the right way to find the bias rail."""
    adj: dict[str, set[str]] = {}
    for t in rows:
        if not t[0].upper().startswith("R") or len(t) < 4:
            continue
        if parse_value(t[3]) is None:
            continue
        adj.setdefault(t[1], set()).add(t[2])
        adj.setdefault(t[2], set()).add(t[1])
    return adj


def _resistive_hops(adj: dict[str, set[str]], start: str) -> dict[str, int]:
    """Nodes reachable from `start` over resistors, with hop counts. Ground is never
    entered: every rail sits above it through something, so a walk allowed through
    ground would leave the bias network and come back somewhere unrelated."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in adj.get(node, ()):
            if nxt == "0" or nxt in dist:
                continue
            dist[nxt] = dist[node] + 1
            queue.append(nxt)
    return dist


def grid_supply_rail(rows: list[list[str]], stage: dict,
                     supplies: dict[str, float]) -> dict:
    """Find the negative bias rail a fixed-bias output stage's grids return to.

    The rail is the nearest node reachable from *every* output grid through
    resistors that is either a negative DC source or a node the netlist derives
    from one. Both halves of that sentence are load-bearing, and each of them is
    a bug this function has already had:

    * *Every* grid, not the first one. A netlist is free to put the grid leak on
      the tube's grid pin (`RGL1 NBIAS G51`) or on the far side of the grid
      stopper (`RGS1 G51 N51` + `RGL1 NBIAS N51`) — the same physical circuit,
      drawn the same way, written down in two orders. A resolver that looked one
      resistor out from the first grid found the rail in the first spelling and
      nothing at all in the second, which is why 11 of the corpus's 29 fixed-bias
      circuits shipped a null rail while 18 resolved. Requiring the node to be
      common to all the grids finds the meeting point rather than a way-station:
      a stopper node belongs to one bottle, the rail belongs to all of them.
    * *Derived from* a source, not only a source. The 5G9's grids hang on the
      junction of an 82k/56k divider off its −69 V bias rectifier. The stage sits
      at −28 V; the deck's only negative source says −69. Walking to the first
      source it can see would have named a rail the stage never sits on, so the
      nearer node wins and is reported as `network` — the raw source is named in
      the note, not in the number.

    A candidate must be a *terminus* of the bias network, which is what keeps a
    single-tube stage (where "common to every grid" is vacuous) from settling on
    its own grid stopper: either the node is the negative source itself, or it
    stands between that source and ground. A grid stopper's far end is neither.

    Returns {node, basis, volts, note}; `volts` is filled here only for a source
    rail, where the value is what the source statement says. A `network` rail's
    voltage is read out of the operating point by the caller, like every other
    voltage in this file.
    """
    negative = {n for n, v in supplies.items() if v < 0}
    if not negative:
        return {"node": None, "basis": "unresolved", "volts": None,
                "note": "the netlist declares no negative DC source, so this stage "
                        "has no bias rail to name — check whether it is fixed-bias "
                        "at all."}

    adj = resistor_graph(rows)
    # A node the stage uses as an electrode is not the rail it returns to. On the
    # JTM100 this is not hypothetical: it writes two bottles' grids straight onto
    # the nodes their neighbours reach through a stopper, so G5, G8, NGA and NGB
    # all land in the set common to every grid. None of them qualifies below and
    # the distance rule would reject them anyway, so this changes no answer in
    # today's corpus — it is here so the rule never has to rely on distance to
    # keep a grid node out. A rail that *is* a negative source stays eligible even
    # if a grid sits directly on it, so the guard can never manufacture a false
    # "unresolved" out of a netlist that omits a grid leak.
    electrodes = ({stage["plate"], stage["cathode"]}
                  | set(stage["grids"]) | set(stage["screens"])) - negative
    hops = [_resistive_hops(adj, g) for g in dict.fromkeys(stage["grids"])]
    common = set(hops[0]).intersection(*(set(h) for h in hops[1:]))

    candidates = []
    for node in sorted(common - electrodes - {"0"}):
        near = adj.get(node, set())
        if node in negative:
            kind = "source"
        elif (near & negative) and "0" in near:
            kind = "network"
        else:
            continue
        # Nearest to the grids wins: the divider's output sits between them and the
        # raw supply, and it is the one the stage actually sits on.
        candidates.append((max(h[node] for h in hops),
                           sum(h[node] for h in hops), node, kind))
    if not candidates:
        named = ", ".join(f"{n} ({supplies[n]:.1f} V)" for n in sorted(negative))
        return {"node": None, "basis": "unresolved", "volts": None,
                "note": f"no node reachable from every output grid through resistors "
                        f"is a negative DC source or a node between one and ground; "
                        f"the deck's negative source(s): {named}."}

    _, _, node, kind = min(candidates)
    if kind == "source":
        return {"node": node, "basis": "source", "volts": supplies[node], "note": None}
    src = sorted(adj.get(node, set()) & negative)[0]
    return {"node": node, "basis": "network", "volts": None,
            "note": f"{node} is not itself a source: the netlist derives it from "
                    f"{src} ({supplies[src]:.1f} V) through a resistive network to "
                    f"ground, and grid_supply_v is that node's simulated DC level."}


# ------------------------------------------------------------------- simulate
def simulate(netlist: Path, nodes: list[str], probes: list[str]) -> dict[str, float]:
    ngspice = shutil.which("ngspice")
    if not ngspice:
        sys.exit("FAIL ngspice not found on PATH")
    ctl = ["", ".control", "op"]
    for n in nodes:
        ctl.append(f"echo M {n}=$&v({n})")
    for i, p in enumerate(probes):
        ctl.append(f"print {p}")
    ctl += [".endc", ".end", ""]
    deck = netlist.read_text() + "\n".join(ctl)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False, dir=ROOT) as f:
        f.write(deck)
        path = f.name
    try:
        proc = subprocess.run([ngspice, "-b", path], capture_output=True, text=True,
                              timeout=120, cwd=ROOT)
    finally:
        Path(path).unlink(missing_ok=True)
    out = proc.stdout + proc.stderr
    vals: dict[str, float] = {}
    for k, v in re.findall(r"^M (\w+)=(\S+)$", out, flags=re.MULTILINE):
        vals[k] = float(v)
    for k, v in re.findall(r"^(@\S+\[i\])\s*=\s*(\S+)$", out, flags=re.MULTILINE):
        vals[k] = float(v)
    missing = [n for n in nodes if n not in vals] + [p for p in probes if p not in vals]
    if missing:
        sys.exit(f"FAIL missing from simulation of {netlist}: {missing}\n{out}")
    return vals


# ------------------------------------------------------------------------ bom
OT_Z = re.compile(r"(≈|~|approx\.?\s*)?\s*([\d.]+)\s*(k)?\s*Ω\s*:", re.I)


def lettered_output_tube(bom: dict | None) -> str | None:
    """The output valve's own designation, as the parts list letters it.

    `tube` above is the SPICE model the netlist instantiates, and those two are
    not always the same designation: the whole 6L6 family shares one clean-room
    fit (models/5881.inc), so a 5E5-A whose sheet letters 6L6GB and a 5F4 whose
    sheet letters 6L6G both simulate as '5881'. The model name is what the
    browser solver needs; the lettered designation is what the amp page must
    print, because that is the valve the drawing names. Returns None when the
    parts list carries no power tube, and the caller falls back to the model."""
    for item in (bom or {}).get("items", []) or []:
        if str(item.get("part", "")).strip().lower() == "power tube":
            v = str(item.get("value", "")).strip()
            if v:
                return v
    return None


def ot_primary(bom: dict | None) -> tuple[float | None, bool, str | None]:
    """(primary ohms, approximate?, note) from the parts list's output-transformer row."""
    for item in (bom or {}).get("items", []) or []:
        if "output transformer" not in str(item.get("part", "")).lower():
            continue
        value = str(item.get("value", ""))
        role = str(item.get("role", ""))
        m = OT_Z.search(value)
        if m:
            ohms = float(m.group(2)) * (1e3 if m.group(3) else 1.0)
            return ohms, bool(m.group(1)), f"{value} — {role}" if role else value
        return None, False, f"{value} — {role}" if role else value
    return None, False, None


# ----------------------------------------------------------------------- main
def pentode_models(rows: list[list[str]]) -> list[str]:
    """Every 4-terminal pentode model instantiated in a deck, for the coverage gate's
    failure message — so a circuit whose output valve is missing from POWER_TUBES says
    which valves it actually contains instead of just vanishing from the export."""
    seen = [t[5].upper() for t in rows
            if t[0].upper().startswith("X") and len(t) == 6]
    return sorted(set(seen))


def build() -> dict:
    stages = []
    missing: list[str] = []
    for amp_dir in sorted(d for d in AMPS.iterdir()
                          if d.is_dir() and d.name != "_template"):
        netlist = amp_dir / "netlist.cir"
        if not netlist.exists():
            continue
        rows = read_deck(netlist)
        stage = find_output_stage(rows)
        if not stage:
            # Every documented circuit is an amplifier and therefore has an output
            # stage. Reaching here means POWER_TUBES has fallen behind the corpus.
            missing.append(f"  amps/{amp_dir.name}: no output stage — "
                           f"pentodes in its netlist: {', '.join(pentode_models(rows)) or 'none'}")
            continue
        meta = yaml.safe_load((amp_dir / "meta.yaml").read_text())
        bom_path = amp_dir / "bom.yaml"
        bom = yaml.safe_load(bom_path.read_text()) if bom_path.exists() else None

        supplies = dc_sources(rows)
        rk_total = cathode_resistor(rows, stage["cathode"])
        if rk_total is not None:
            rail = {"node": None, "basis": "cathode-bias", "volts": None, "note": None}
        else:
            rail = grid_supply_rail(rows, stage, supplies)

        # Nodes worth reading: plate, every distinct screen node, cathode, first grid —
        # plus the bias rail itself where the netlist derives it rather than stating it.
        screens = list(dict.fromkeys(stage["screens"]))
        nodes = [n for n in [stage["plate"], *screens, stage["cathode"],
                             stage["grids"][0]] if n != "0"]
        if rail["basis"] == "network" and rail["node"] not in nodes:
            nodes.append(rail["node"])
        first_ref = stage["tubes"][0]["ref"].lower()
        probes = [f"@b.{first_ref}.bp[i]", f"@b.{first_ref}.bg2[i]"]
        sim = simulate(netlist, nodes, probes)

        def volts(node: str) -> float:
            return 0.0 if node == "0" else round(sim[node], 3)

        ot_z, ot_approx, ot_note = ot_primary(bom)
        n = stage["n"]
        config = "single-ended" if n == 1 else "push-pull"
        entry = {
            "amp": QStr(meta["id"]),
            "name_style": meta["name_style"],
            "tube": QStr(stage["model"]),
            # The designation the drawing letters, where it differs from the model
            # the netlist instantiates (the 6L6 family shares one fit) — this is
            # what the amp page prints; `tube` stays the solver's model name.
            "tube_lettered": QStr(lettered_output_tube(bom) or stage["model"]),
            "output_tubes": n,
            "config": config,
            "bias": "cathode" if rk_total is not None else "fixed",
            "plate_node": stage["plate"],
            "plate_v": volts(stage["plate"]),
            "screen_node": screens[0],
            "screen_v": volts(screens[0]),
            "cathode_node": stage["cathode"],
            "cathode_v": volts(stage["cathode"]),
            # Per-tube cathode resistor: a shared resistor carries every bottle's
            # current, so one tube "sees" n times its value.
            "rk_total": None if rk_total is None else round(rk_total, 4),
            "rk_per_tube": None if rk_total is None else round(rk_total * n, 4),
            "grid_node": stage["grids"][0],
            # The grid's own simulated voltage — what the tube actually sees. It equals
            # the bias supply while grid current is zero (the v0 models carry no grid-
            # current term), but reading the node keeps the preset honest if that changes.
            "grid_v": volts(stage["grids"][0]),
            "grid_supply_node": rail["node"],
            # A source rail reports what the source statement says; a derived one
            # reports the node's own simulated level. See grid_supply_basis.
            "grid_supply_v": (volts(rail["node"]) if rail["basis"] == "network"
                              else rail["volts"]),
            "grid_supply_basis": rail["basis"],
            "grid_supply_note": rail["note"],
            "ot_primary_z": ot_z,
            "ot_primary_approx": ot_approx,
            "ot_primary_note": ot_note,
            # ngspice parity reference — per tube, milliamps.
            "sim_ip_ma": round(sim[probes[0]] * 1e3, 4),
            "sim_ig2_ma": round(sim[probes[1]] * 1e3, 4),
        }
        stages.append(entry)
    if missing:
        sys.exit("FAIL export_loadlines: every documented circuit must yield one "
                 "output stage; these did not —\n" + "\n".join(missing) +
                 "\n  Add the output valve to POWER_TUBES in pipeline/export_loadlines.py.")
    return {"stages": stages}


# ------------------------------------------------------------------ consistency
BASES = ("cathode-bias", "source", "network", "unresolved")

# The grid sits on the rail through a leak carrying no DC current, so the two
# voltages are the same number. This is the assertion that turns "the resolver
# found *a* node" into "the resolver found *the* node": naming the 5G9's −69 V
# rectifier instead of its −28 V divider output is arithmetically loud even
# though both are real nodes in the deck. The tolerance is wide enough for
# solver provenance (numeric_drift's own atol is 5 mV) and nowhere near wide
# enough to swallow a wrong node.
RAIL_TOL_V = 0.5


def consistency_problems(data: dict) -> list[str]:
    """What this generated file must say about itself, independent of drift.

    A drift gate compares a fresh export against the committed one, so a field
    that is wrong the same way every run passes for as long as it exists. These
    rules execute the grid-supply contract instead: a fixed-bias stage names its
    rail or says why it cannot, and a null always carries a reason a reader can
    tell apart from every other null.
    """
    problems: list[str] = []
    for s in data.get("stages") or []:
        amp = s.get("amp", "?")
        basis, node = s.get("grid_supply_basis"), s.get("grid_supply_node")
        volts, note = s.get("grid_supply_v"), s.get("grid_supply_note")

        if basis not in BASES:
            problems.append(f"{amp}: grid_supply_basis {basis!r} is not one of {BASES}")
            continue
        if s.get("bias") == "cathode":
            if basis != "cathode-bias":
                problems.append(f"{amp}: cathode-biased stage claims grid_supply_basis "
                                f"{basis!r}")
            if node is not None or volts is not None:
                problems.append(f"{amp}: cathode-biased stage names a grid supply "
                                f"({node} / {volts}) — it biases itself across rk")
            continue

        if basis == "cathode-bias":
            problems.append(f"{amp}: fixed-bias stage claims grid_supply_basis "
                            f"'cathode-bias'")
        elif basis == "unresolved":
            if node is not None or volts is not None:
                problems.append(f"{amp}: unresolved rail still names {node} / {volts}")
            if not isinstance(note, str) or len(note.strip()) < 20:
                problems.append(f"{amp}: fixed-bias stage resolves no grid supply and "
                                f"gives no reason — an unresolved rail must say in "
                                f"words what was looked for and what was found")
        else:  # source | network
            if not node:
                problems.append(f"{amp}: grid_supply_basis {basis!r} names no node")
            if not isinstance(volts, (int, float)) or isinstance(volts, bool):
                problems.append(f"{amp}: grid_supply_basis {basis!r} carries no voltage")
            elif volts >= 0:
                problems.append(f"{amp}: grid supply {volts} V is not negative — a "
                                f"fixed-bias grid returns to a negative rail")
            elif isinstance(s.get("grid_v"), (int, float)):
                gap = abs(s["grid_v"] - volts)
                if gap > RAIL_TOL_V:
                    problems.append(
                        f"{amp}: grid_supply_v {volts} V is not the voltage the grid "
                        f"node sits at ({s['grid_v']} V, gap {gap:.3f} V) — the rail "
                        f"named is not the rail the stage returns to")
            if basis == "network" and not (isinstance(note, str) and note.strip()):
                problems.append(f"{amp}: a derived rail must name the source it comes "
                                f"from in grid_supply_note")
    return problems


def _plant(data: dict, amp: str, **fields) -> dict:
    """A copy of `data` with one stage's fields overwritten — for the selftest."""
    out = copy.deepcopy(data)
    for s in out["stages"]:
        if s["amp"] == amp:
            s.update(fields)
            return out
    raise SystemExit(f"selftest: no stage {amp!r} in the committed export")


def selftest() -> int:
    """Plant each fault class the consistency gate exists to catch, and prove it
    fires. Runs against the committed file rather than a fresh export, so it needs
    no ngspice and exercises exactly the shapes the gate protects."""
    if not OUT.exists():
        print(f"FAIL {OUT.relative_to(ROOT)} missing — nothing to selftest against")
        return 1
    data = yaml.safe_load(OUT.read_text())
    clean = consistency_problems(data)
    if clean:
        print("FAIL selftest baseline: the committed file is already inconsistent —")
        for line in clean:
            print(f"  {line}")
        return 1

    fixed = next(s for s in data["stages"] if s["bias"] == "fixed")
    cathode = next(s for s in data["stages"] if s["bias"] == "cathode")
    faults = [
        ("a fixed-bias rail silently nulled",
         _plant(data, fixed["amp"], grid_supply_node=None, grid_supply_v=None,
                grid_supply_basis="unresolved", grid_supply_note=None)),
        ("an unresolved rail with a reason too thin to act on",
         _plant(data, fixed["amp"], grid_supply_node=None, grid_supply_v=None,
                grid_supply_basis="unresolved", grid_supply_note="n/a")),
        ("a rail the grid node does not sit on",
         _plant(data, fixed["amp"], grid_supply_v=fixed["grid_v"] - 21.0)),
        ("a positive grid supply",
         _plant(data, fixed["amp"], grid_supply_v=48.0)),
        ("a derived rail that names no source",
         _plant(data, fixed["amp"], grid_supply_basis="network",
                grid_supply_note=None)),
        ("a cathode-biased stage handed a bias rail",
         _plant(data, cathode["amp"], grid_supply_node="NBIAS",
                grid_supply_v=-48.0, grid_supply_basis="source")),
        ("a basis outside the vocabulary",
         _plant(data, fixed["amp"], grid_supply_basis="probably")),
    ]
    ok = True
    for label, planted in faults:
        found = consistency_problems(planted)
        print(f"  {'caught' if found else 'MISSED'}  {label}"
              + (f" — {found[0]}" if found else ""))
        ok = ok and bool(found)
    if not ok:
        print("FAIL export_loadlines --selftest: the consistency gate missed a "
              "planted fault")
        return 1
    print(f"ok export_loadlines --selftest: {len(faults)} planted fault(s) caught, "
          f"committed file clean ({len(data['stages'])} stage(s))")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    data = build()
    bad = consistency_problems(data)
    if bad:
        print("FAIL export_loadlines: the export contradicts its own grid-supply "
              "contract —")
        for line in bad:
            print(f"  {line}")
        return 1
    text = HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    if "--check" in sys.argv:
        if not OUT.exists():
            print(f"FAIL {OUT.relative_to(ROOT)} missing — run pipeline/export_loadlines.py")
            return 1
        committed = yaml.safe_load(OUT.read_text())
        stale = consistency_problems(committed)
        if stale:
            print(f"FAIL {OUT.relative_to(ROOT)} contradicts its own grid-supply "
                  f"contract —")
            for line in stale:
                print(f"  {line}")
            return 1
        drift = numeric_drift(OUT.read_text(), text)
        if drift:
            print(f"FAIL {OUT.relative_to(ROOT)} is stale — re-run pipeline/export_loadlines.py")
            for line in drift:
                print(f"  {line}")
            return 1
        # The consistency rules are only worth their exit code if they can fail, and
        # a gate whose proof lives in a separate command is a gate somebody forgets
        # to wire up. It costs no simulation, so it rides along here.
        if selftest() != 0:
            return 1
        print(f"ok {OUT.relative_to(ROOT)} matches the netlists ({len(data['stages'])} stage(s))")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(data['stages'])} output stage(s)")
    for s in data["stages"]:
        if s["bias"] == "cathode":
            rail = f"rk {s['rk_total']:g} Ω"
        elif s["grid_supply_node"]:
            rail = (f"rail {s['grid_supply_node']} {s['grid_supply_v']:g} V "
                    f"[{s['grid_supply_basis']}]")
        else:
            rail = "rail UNRESOLVED"
        print(f"  {s['amp']:14s} {s['tube']:6s} x{s['output_tubes']} {s['bias']:8s} "
              f"B+ {s['plate_v']:.1f} V  screen {s['screen_v']:.1f} V  "
              f"cathode {s['cathode_v']:.2f} V  Ip {s['sim_ip_ma']:.2f} mA  {rail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
