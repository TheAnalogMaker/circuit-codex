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

Usage:
    python3 pipeline/export_loadlines.py            # regenerate reference/loadlines.yaml
    python3 pipeline/export_loadlines.py --check     # fail if the checked-in file drifts
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
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


def grid_bias_node(rows: list[list[str]], grid: str, supplies: dict[str, float]) -> tuple[str | None, float | None]:
    """A fixed-bias grid returns through its grid leak to a negative supply node.
    Returns (node, volts) when the grid leak lands on a DC source, else (None, None)."""
    for t in rows:
        if not t[0].upper().startswith("R") or len(t) < 4:
            continue
        a, b = t[1], t[2]
        if grid not in (a, b):
            continue
        other = b if a == grid else a
        if other in supplies:
            return other, supplies[other]
    return None, None


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
        bias_node, bias_v = (None, None)
        if rk_total is None:
            bias_node, bias_v = grid_bias_node(rows, stage["grids"][0], supplies)

        # Nodes worth reading: plate, every distinct screen node, cathode, first grid.
        screens = list(dict.fromkeys(stage["screens"]))
        nodes = [n for n in [stage["plate"], *screens, stage["cathode"],
                             stage["grids"][0]] if n != "0"]
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
            "grid_supply_node": bias_node,
            "grid_supply_v": bias_v,
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


def main() -> int:
    data = build()
    text = HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    if "--check" in sys.argv:
        if not OUT.exists():
            print(f"FAIL {OUT.relative_to(ROOT)} missing — run pipeline/export_loadlines.py")
            return 1
        drift = numeric_drift(OUT.read_text(), text)
        if drift:
            print(f"FAIL {OUT.relative_to(ROOT)} is stale — re-run pipeline/export_loadlines.py")
            for line in drift:
                print(f"  {line}")
            return 1
        print(f"ok {OUT.relative_to(ROOT)} matches the netlists ({len(data['stages'])} stage(s))")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(data['stages'])} output stage(s)")
    for s in data["stages"]:
        print(f"  {s['amp']:6s} {s['tube']:6s} x{s['output_tubes']} {s['bias']:8s} "
              f"B+ {s['plate_v']:.1f} V  screen {s['screen_v']:.1f} V  "
              f"cathode {s['cathode_v']:.2f} V  Ip {s['sim_ip_ma']:.2f} mA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
