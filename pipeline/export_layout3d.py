#!/usr/bin/env python3
"""Export the 5F1 layout's existing geometry for an illustrative 3D view.

No source-circuit values, endpoints, dimensions, or netlist claims are invented.
The renderer is the coordinate authority, including heater forks and links.
The known-wrong 6.3 V heater routes are explicitly omitted pending correction.
Run: python3 pipeline/export_layout3d.py [5f1] [--check] [--selftest]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import sys

import yaml

from render_layouts import (
    BUS_CORE, HEATER, HEATER_CT, WIRE_NEUTRAL, Renderer, category,
    colour_hex, lead_base, twisted_points,
)

ROOT = Path(__file__).resolve().parent.parent
SUPPORTED = {"5f1"}
KNOWN_UNPLACED = {"5f1": {"C2", "C4"}}
HEATER_OMISSIONS = {
    "run:43": ("PT.green", "PL1.a", 2),
    "run:44": ("PL1.b", "V2.pin7", 2),
    "run:45": ("V2.pin2", "V1.pin4", 2),
    "run:46": ("V1.pin4", "V1.pin5", 1),
}
HEATER_OMISSION_REASON = (
    "6.3 V heater wiring is omitted while the source layout's heater connections are being corrected. "
    "The 12AX7 needs joined pins 4/5 against pin 9; the current pair expansion omits pin 9."
)
HEATER_SCOPE_NOTE = (
    "6.3 V heater wiring is not shown while the source layout's heater connections are being corrected; "
    "the pilot lamp is shown as hardware only."
)


class ExportError(ValueError):
    """An input or exported claim cannot be reconciled with the source."""


def point(value):
    if value is None or len(value) != 2 or not all(math.isfinite(float(n)) for n in value):
        raise ExportError(f"Invalid coordinate: {value!r}")
    # Six decimal places preserve endpoints far below a screen pixel while
    # removing insignificant platform math noise and keeping diffs readable.
    return [round(float(n), 6) for n in value]


def endpoint_id(ep):
    if isinstance(ep, str):
        return ep
    return "point:" + ":".join(format(float(n), ".12g") for n in ep)


def source_inputs(amp_id):
    if amp_id not in SUPPORTED:
        raise ExportError(f"Unsupported circuit {amp_id!r}; the 3D pilot supports only 5f1")
    amp = ROOT / "amps" / amp_id
    layout = yaml.safe_load((amp / "layout.yaml").read_text())
    items = yaml.safe_load((amp / "bom.yaml").read_text())["items"]
    bom = {}
    for item in items:
        ref = item.get("ref")
        if ref and ref != "—":
            if ref in bom:
                raise ExportError(f"Duplicate BOM reference: {ref}")
            bom[ref] = item
    return layout, bom


def make_renderer(layout, bom, amp_id):
    if amp_id not in SUPPORTED:
        raise ExportError(f"Unsupported circuit {amp_id!r}; the 3D pilot supports only 5f1")
    if layout.get("leads"):
        raise ExportError("Legacy visual leads are outside this pilot's endpoint contract")
    ids = [p["ref"] for p in layout["parts"]] + [p["id"] for p in layout["offboard"]]
    if len(ids) != len(set(ids)):
        raise ExportError("Duplicate component id")
    for item in layout["parts"] + layout["offboard"]:
        if item.get("ref") and item["ref"] not in bom:
            raise ExportError(f"Reference {item['ref']} absent from BOM")
    for part in layout["parts"]:
        if part["a"][0] != part["b"][0] and part["a"][1] != part["b"][1]:
            raise ExportError("Diagonal part bodies are outside the 5F1 pilot")
    return Renderer(copy.deepcopy(layout), copy.deepcopy(bom), amp_id)


def canonical_terminal(renderer, ep):
    """Retain authored aliases; coordinate endpoints use stable coordinate IDs."""
    resolved = renderer.resolve(ep, "3D terminal")
    if resolved is None or renderer.errors:
        raise ExportError("; ".join(renderer.errors))
    owner = ep.split(".", 1)[0] if isinstance(ep, str) else None
    return {"id": endpoint_id(ep), "label": endpoint_id(ep),
            "point": point(resolved), "owner": owner}


def fork_endpoint(renderer, ep, fork):
    """Identify an existing heater fork's pin by exact renderer coordinates.

    This is not a nearest-pin heuristic: precisely one pin in the renderer's
    documented heater pair must match the emitted fork landing.
    """
    if fork is None:
        return ep
    item, _ = renderer._tube_endpoint(ep)
    if item is None:
        raise ExportError("Heater fork without a source tube endpoint")
    matches = [pin for pin in item.get("_heater_pair", [])
               if point(renderer.tube_pin_pos(item, pin)) == point(fork[-1])]
    if len(matches) != 1:
        raise ExportError(f"Heater fork at {ep} does not resolve to exactly one heater pin")
    return f"{item['id']}.pin{matches[0]}"


def hardware_endpoints(renderer, item):
    cid, kind = item["id"], item["kind"]
    if kind == "tube":
        if not item.get("_pins"):
            raise ExportError(f"No documented tube basing for {cid}")
        return [f"{cid}.pin{pin}" for pin in sorted(item["_pins"])]
    if kind == "pot":
        return [f"{cid}.lug{n}" for n in (1, 2, 3)]
    if kind == "part":
        return [f"{cid}.a", f"{cid}.b"]
    if kind in ("xfmr", "choke"):
        return [f"{cid}.{suffix}" for suffix in renderer.xfmr_leads.get(cid, [])]
    if kind == "jack":
        # Only source-addressed jack aliases are terminals. Do not turn the
        # simplified J1/J2 symbols into an invented switched jack.
        return list(dict.fromkeys(ep for spec in renderer.runs + renderer.bus
                                  for ep in (spec["from"], spec["to"])
                                  if isinstance(ep, str) and ep.split(".")[0] == cid))
    raise ExportError(f"Unsupported hardware kind: {kind}")


def geometry_bounds(renderer, connection_points):
    """Measure original 2D glyph bounds, including off-board hardware bodies.

    Calling the existing glyph builders populates their obstacle boxes. No
    labels are emitted/placed and no SVG artifact is written.
    """
    for part in renderer.parts:
        renderer.part_body(part)
    for item in renderer.offboard:
        renderer.off_stub(item)
    points = list(connection_points)
    for obstacle in renderer.obstacles:
        x0, y0, x1, y1 = obstacle["box"]
        points.extend(((x0, y0), (x1, y1)))
    points.extend(((renderer.board_x, renderer.board_y),
                   (renderer.board_x + renderer.board_w, renderer.board_y + renderer.board_h)))
    minx, miny = min(p[0] for p in points), min(p[1] for p in points)
    maxx, maxy = max(p[0] for p in points), max(p[1] for p in points)
    return {"x": round(minx, 6), "y": round(miny, 6),
            "width": round(maxx-minx, 6), "height": round(maxy-miny, 6)}


def rendered_connections(renderer):
    """One entry per rendered strand, preserving its authored source run."""
    runs, buses = renderer.build_geometry()
    output = []
    for run in runs:
        spec, i = run["spec"], run["i"]
        colour = spec.get("color") or renderer._endpoint_colour(spec["from"]) \
            or renderer._endpoint_colour(spec["to"])
        if not run["pts"]:
            raise ExportError(f"Unresolved run {i}: {renderer.errors}")
        if run["twisted"]:
            for end in ("from", "to"):
                renderer._check_heater_endpoint(spec[end], f"run[{i}] {end}")
            stroke = HEATER_CT if lead_base(colour or "") == "green-yellow" else HEATER
            if run["single"]:
                paths = [(spec["from"], spec["to"], run["pts"])]
            else:
                strands = twisted_points(run["pts"])
                fa, fb = run["forks"]
                paths = []
                for k, strand in enumerate(strands):
                    # Same joining order as Renderer._heater_paths(); retain
                    # numeric points instead of parsing its SVG path string.
                    if fa:
                        strand = list(reversed(fa[k]))[:-1] + strand
                    if fb:
                        strand = strand + fb[k][1:]
                    paths.append((fork_endpoint(renderer, spec["from"], fa[k] if fa else None),
                                  fork_endpoint(renderer, spec["to"], fb[k] if fb else None), strand))
        else:
            stroke = colour_hex(colour) if colour else WIRE_NEUTRAL
            paths = [(spec["from"], spec["to"], run["pts"])]
        for k, (start, end, pts) in enumerate(paths):
            output.append({"id": f"run:{i}:strand:{k}" if run["twisted"] else f"run:{i}",
                           "from": start, "to": end, "points": pts,
                           "kind": "heater" if run["twisted"] else "wire", "color": stroke,
                           "sourceRun": f"run:{i}", "sourceFrom": spec["from"], "sourceTo": spec["to"]})
    for bus in buses:
        if not bus["pts"]:
            raise ExportError(f"Unresolved bus {bus['j']}")
        spec = bus["spec"]
        output.append({"id": f"bus:{bus['j']}", "from": spec["from"], "to": spec["to"],
                       "points": bus["pts"], "kind": "bus", "color": BUS_CORE,
                       "sourceRun": f"bus:{bus['j']}", "sourceFrom": spec["from"], "sourceTo": spec["to"]})
    if renderer.errors:
        raise ExportError("; ".join(renderer.errors))
    return output


def connection_scope(renderer):
    """Withhold known-wrong heater routes; retain source identity, not geometry.

    This dated pilot exclusion is explicit and finite. A changed source heater
    configuration must be reviewed before its geometry can be published.
    Ordinary 5 V rectifier filament wiring is not in this exclusion.
    """
    connections = rendered_connections(renderer)
    heater_groups = {}
    for connection in connections:
        if connection["kind"] == "heater":
            heater_groups.setdefault(connection["sourceRun"], []).append(connection)
    if set(heater_groups) != set(HEATER_OMISSIONS):
        raise ExportError("The reviewed 6.3 V heater omission scope changed")
    omissions = []
    for run_id, (start, end, count) in HEATER_OMISSIONS.items():
        group = heater_groups[run_id]
        if len(group) != count or any(c["sourceFrom"] != start or c["sourceTo"] != end for c in group):
            raise ExportError(f"Heater source {run_id} changed; review the pilot omission before exporting")
        omissions.append({
            "sourceRun": run_id, "sourceFrom": start, "sourceTo": end,
            "omittedStrands": count, "reason": HEATER_OMISSION_REASON,
            "reviewedAt": "2026-09-09",
            "sources": [
                {"desc": "Fender Champ-Amp 5F1 K-EE factory layout, page 2: joined 12AX7 pins 4/5 and grounded pin 9",
                 "url": "https://schematicheaven.net/fenderamps/champ_5f1_schem.pdf"},
                {"desc": "RCA 12AX7-A October 1960, pages 1-2: 6.3 V parallel operation and heater basing",
                 "url": "https://frank.pocnet.net/sheets/049/1/12AX7A.pdf"},
            ],
        })
    return [c for c in connections if c["kind"] != "heater"], omissions


def export_layout(amp_id, layout=None, bom=None):
    if layout is None or bom is None:
        layout, bom = source_inputs(amp_id)
    renderer = make_renderer(layout, bom, amp_id)
    connections, omissions = connection_scope(renderer)
    terminals = {}

    def register(ep):
        terminal = canonical_terminal(renderer, ep)
        previous = terminals.setdefault(terminal["id"], terminal)
        if previous != terminal:
            raise ExportError(f"Conflicting terminal alias: {terminal['id']}")
        return terminal

    components = []
    for p in renderer.parts:
        ref = p["ref"]
        a, b = register(f"{ref}.a"), register(f"{ref}.b")
        record = bom[ref]
        components.append({"id": ref, "ref": ref, "kind": "part", "mount": "board",
                           "category": category(record["part"]), "label": ref,
                           "value": record["value"], "role": record.get("role", ""),
                           "center": point([(a["point"][0] + b["point"][0]) / 2,
                                            (a["point"][1] + b["point"][1]) / 2]),
                           "terminals": [a, b], "a": a["point"], "b": b["point"]})
    for item in renderer.offboard:
        cid, kind = item["id"], item["kind"]
        ref = item.get("ref")
        record = bom.get(ref, {})
        eps = hardware_endpoints(renderer, item)
        component = {"id": cid, "kind": kind, "mount": "offboard",
                     "category": "lamp" if item.get("glyph") == "lamp" else category(record.get("part", "")),
                     "label": item.get("label", cid), "value": record.get("value", ""),
                     "role": record.get("role", ""), "center": point(renderer.off_pos(item)),
                     "terminals": [register(ep) for ep in eps]}
        if ref:
            component["ref"] = ref
        if kind == "part":
            component["a"], component["b"] = [t["point"] for t in component["terminals"]]
        components.append(component)

    exported_connections = []
    for connection in connections:
        start, end = register(connection["from"]), register(connection["to"])
        exported_connections.append({**connection, "from": start["id"], "to": end["id"],
                                     "fromOwner": start["owner"], "toOwner": end["owner"],
                                     "points": [point(p) for p in connection["points"]]})
    eyelets = [{"id": endpoint_id([r, c]), "point": point(renderer.resolve([r, c]))}
               for r in range(renderer.rows) for c in range(renderer.cols)]
    board = {"x": renderer.board_x, "y": renderer.board_y,
             "width": renderer.board_w, "height": renderer.board_h}
    bounds = geometry_bounds(renderer, [p for c in connections for p in c["points"]])
    data = {
        "schemaVersion": 1, "id": amp_id, "title": layout["board"]["title"],
        "source": layout["source"], "scopeNotes": [
            "Illustrative geometry follows the existing layout; it is not dimensioned chassis or manufacturing data.",
            "Connections identify layout endpoints, not simulated current flow or complete DC net membership.",
            "The input jacks retain the existing linked-input simplification; C2 and C4 are in the BOM but not placed in this layout.",
            HEATER_SCOPE_NOTE,
            "The separate 5 V rectifier filament routes remain shown within the existing drawing's annotation scope."
        ],
        "connectivity": {"scope": "layout-endpoints-only",
                         "note": "Crossing paths do not imply a junction. Shared eyelets have identical coordinates; component leads are not shorted together."},
        "board": board, "bounds": bounds,
        "eyelets": eyelets, "components": components,
        "terminals": list(terminals.values()), "connections": exported_connections,
        "omittedConnections": omissions,
        "unplacedBOMRefs": sorted(set(bom) - {c["ref"] for c in components if "ref" in c}),
    }
    validate_export(data, layout, bom, amp_id)
    return data


def validate_export(data, layout, bom, amp_id="5f1"):
    """Reject dropped/changed output, phantom endpoints and BOM drift."""
    renderer = make_renderer(layout, bom, amp_id)
    expected_connections, expected_omissions = connection_scope(renderer)
    if data.get("omittedConnections") != expected_omissions:
        raise ExportError("Heater omissions differ from the reviewed scope or provenance")
    if HEATER_SCOPE_NOTE not in data.get("scopeNotes", []):
        raise ExportError("Displayable heater omission note is missing")
    if data.get("schemaVersion") != 1 or data.get("id") != amp_id:
        raise ExportError("Schema version or circuit identity mismatch")
    if data.get("source") != layout["source"] or data.get("title") != layout["board"]["title"]:
        raise ExportError("Source provenance/title mismatch")
    if data.get("connectivity", {}).get("scope") != "layout-endpoints-only":
        raise ExportError("Unsupported connectivity claim")
    expected_board = {"x": renderer.board_x, "y": renderer.board_y,
                      "width": renderer.board_w, "height": renderer.board_h}
    if data.get("board") != expected_board:
        raise ExportError("Board geometry mismatch")
    components = {c["id"]: c for c in data["components"]}
    expected_ids = [p["ref"] for p in layout["parts"]] + [p["id"] for p in layout["offboard"]]
    if len(components) != len(data["components"]) or set(components) != set(expected_ids):
        raise ExportError("Component count/identity does not match source layout")
    expected_refs = {p["ref"] for p in layout["parts"] + layout["offboard"] if p.get("ref")}
    if set(bom) - expected_refs != KNOWN_UNPLACED[amp_id]:
        raise ExportError("The pilot's documented unplaced BOM scope changed; review scope notes before exporting")
    if data["unplacedBOMRefs"] != sorted(set(bom) - expected_refs):
        raise ExportError("Unplaced BOM references do not match source layout")
    for cid, component in components.items():
        source = renderer.part_by_ref.get(cid) or renderer.off_by_id[cid]
        ref = source.get("ref")
        if component.get("ref") != ref:
            raise ExportError(f"BOM identity mismatch for {cid}")
        if ref and (component["value"] != bom[ref]["value"] or component["role"] != bom[ref].get("role", "")):
            raise ExportError(f"BOM value/role mismatch for {cid}")
        if cid in renderer.part_by_ref:
            endpoints = [f"{cid}.a", f"{cid}.b"]
            a, b = [point(renderer.resolve(ep)) for ep in endpoints]
            center = point([(a[0]+b[0])/2, (a[1]+b[1])/2])
            mount, kind = "board", "part"
        else:
            endpoints = hardware_endpoints(renderer, source)
            center = point(renderer.off_pos(source))
            mount, kind = "offboard", source["kind"]
        expected_terminals = [canonical_terminal(renderer, ep) for ep in endpoints]
        if component["terminals"] != expected_terminals:
            raise ExportError(f"Component terminal mismatch for {cid}")
        if component["center"] != center or component["mount"] != mount or component["kind"] != kind:
            raise ExportError(f"Component placement/type mismatch for {cid}")
        if kind == "part":
            if component["a"] != expected_terminals[0]["point"] or component["b"] != expected_terminals[1]["point"]:
                raise ExportError(f"Component lead mismatch for {cid}")
        expected_category = "lamp" if source.get("glyph") == "lamp" else category(bom.get(ref, {}).get("part", ""))
        if component["category"] != expected_category:
            raise ExportError(f"Component category mismatch for {cid}")
    expected_eyelets = [{"id": endpoint_id([r, c]), "point": point(renderer.resolve([r, c]))}
                        for r in range(renderer.rows) for c in range(renderer.cols)]
    if data["eyelets"] != expected_eyelets:
        raise ExportError("Eyelet count/geometry mismatch")
    by_id = {c["id"]: c for c in data["connections"]}
    if len(by_id) != len(data["connections"]) or set(by_id) != {c["id"] for c in expected_connections}:
        raise ExportError("Connection/strand count or identity mismatch")
    for expected in expected_connections:
        actual = by_id[expected["id"]]
        start = canonical_terminal(renderer, expected["from"])
        end = canonical_terminal(renderer, expected["to"])
        for key, value in (("from", start["id"]), ("to", end["id"]),
                           ("fromOwner", start["owner"]), ("toOwner", end["owner"]),
                           ("sourceRun", expected["sourceRun"]), ("sourceFrom", expected["sourceFrom"]),
                           ("sourceTo", expected["sourceTo"]), ("kind", expected["kind"]), ("color", expected["color"])):
            if actual.get(key) != value:
                raise ExportError(f"{actual['id']} {key} differs from source")
        if actual["points"] != [point(p) for p in expected["points"]]:
            raise ExportError(f"{actual['id']} route differs from Renderer")
        if actual["points"][0] != start["point"] or actual["points"][-1] != end["point"]:
            raise ExportError(f"{actual['id']} path does not land on its declared terminals")
    expected_terminal_ids = {t["id"] for c in data["components"] for t in c["terminals"]} \
        | {endpoint_id(c[end]) for c in expected_connections for end in ("from", "to")}
    terminals = {t["id"]: t for t in data["terminals"]}
    if len(terminals) != len(data["terminals"]) or set(terminals) != expected_terminal_ids:
        raise ExportError("Terminal registry count/identity mismatch")
    source_endpoints = {endpoint_id(c[end]): c[end] for c in expected_connections for end in ("from", "to")}
    for tid, terminal in terminals.items():
        if terminal != canonical_terminal(renderer, source_endpoints.get(tid, tid)):
            raise ExportError(f"Terminal registry geometry mismatch: {tid}")
    expected_bounds = geometry_bounds(renderer, [p for c in expected_connections for p in c["points"]])
    if data.get("bounds") != expected_bounds:
        raise ExportError("Geometry bounds mismatch")
    if renderer.errors:
        raise ExportError("; ".join(renderer.errors))


def serialize(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("amp_id", nargs="?", default="5f1")
    parser.add_argument("--check", action="store_true", help="Fail if committed data differs; do not write")
    parser.add_argument("--selftest", action="store_true", help="Run integrity mutation tests")
    args = parser.parse_args()
    if args.selftest:
        import unittest
        from test_layout3d_export import Layout3DTests
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Layout3DTests))
        return 0 if result.wasSuccessful() else 1
    try:
        rendered = serialize(export_layout(args.amp_id))
        output = ROOT / "site" / "public" / "layouts" / f"{args.amp_id}-3d.json"
        if args.check:
            if not output.exists() or output.read_text() != rendered:
                raise ExportError(f"{output.relative_to(ROOT)} is missing or stale; run export_layout3d.py {args.amp_id}")
            print(f"PASS {args.amp_id}: 3D layout data matches sources")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered)
            print(output.relative_to(ROOT))
        return 0
    except (ExportError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
