#!/usr/bin/env python3
"""Electrical connectivity for the generated `amps/<id>/schematic.kicad_sch`
drawings.

The drawings are geometry: wires, junction dots, global labels and placed
symbols. Nothing in the file names a net, so a mis-placed wire produces a
perfectly valid file that draws a different circuit. This module rebuilds the
nets the way KiCad's own connectivity engine does, so a gate can assert what
the drawing actually connects.

Rules implemented (KiCad 6+ behaviour):

* the two ends of a wire segment are the same net;
* any connection point — a wire end, a pin, a junction dot, a global-label
  anchor — that lies *on* a wire segment (end or interior) joins that wire's
  net, which is what makes a T-tap connect without a dot;
* two wires that merely cross are **not** connected unless a junction dot sits
  on the crossing;
* a global label ties its net to every other net carrying the same name.

Pin positions come from the library symbol definitions in the file itself, put
through the placed symbol's mirror-then-rotate transform.
"""
from __future__ import annotations

from pathlib import Path

from kiutils.schematic import Schematic

EPS = 1e-6


def _key(x: float, y: float) -> tuple:
    return (round(x, 3), round(y, 3))


class _DSU:
    def __init__(self) -> None:
        self.p: dict = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _transform(px: float, py: float, angle: int, mirror: str | None) -> tuple:
    """Symbol-local pin coordinates -> schematic offsets from the symbol origin."""
    if mirror == "y":
        px = -px
    elif mirror == "x":
        py = -py
    a = int(angle or 0) % 360
    if a == 90:
        px, py = -py, px
    elif a == 180:
        px, py = -px, -py
    elif a == 270:
        px, py = py, -px
    return (px, -py)  # schematic y grows downward


def _on_segment(p: tuple, a: tuple, b: tuple) -> bool:
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if a == b:  # a zero-length wire touches only its own point
        return p == a
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > 1e-3:
        return False
    dot = (x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)
    if dot < -EPS:
        return False
    length = (x2 - x1) ** 2 + (y2 - y1) ** 2
    return dot <= length + EPS


def symbol_pins(sch: Schematic) -> dict:
    """{reference: {pin number: (x, y)}} in schematic coordinates."""
    lib = {}
    for ls in sch.libSymbols:
        pins = {}
        for unit in ls.units:
            for pin in unit.pins:
                pins[pin.number] = (pin.position.X, pin.position.Y)
        lib[ls.libId] = pins
    out = {}
    for sym in sch.schematicSymbols:
        ref = None
        for prop in sym.properties:
            if prop.key == "Reference":
                ref = prop.value
        if ref is None:
            continue
        placed = {}
        for num, (px, py) in lib.get(sym.libId, {}).items():
            dx, dy = _transform(px, py, sym.position.angle, sym.mirror)
            placed[num] = _key(sym.position.X + dx, sym.position.Y + dy)
        out.setdefault(ref, {}).update(placed)
    return out


class Nets:
    """Net membership for one schematic."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        sch = Schematic.from_file(str(self.path))
        self.sch = sch
        self.pins = symbol_pins(sch)

        segs = [(_key(w.points[0].X, w.points[0].Y), _key(w.points[1].X, w.points[1].Y))
                for w in sch.graphicalItems if getattr(w, "type", None) == "wire"]
        self.labels = {}
        for gl in list(sch.globalLabels) + list(sch.labels):
            self.labels.setdefault(gl.text, []).append(_key(gl.position.X, gl.position.Y))

        dsu = _DSU()
        for a, b in segs:
            dsu.union(a, b)

        points = set()
        for a, b in segs:
            points.add(a)
            points.add(b)
        for j in sch.junctions:
            points.add(_key(j.position.X, j.position.Y))
        for pinmap in self.pins.values():
            points.update(pinmap.values())
        for anchors in self.labels.values():
            points.update(anchors)

        for p in points:
            for a, b in segs:
                if _on_segment(p, a, b):
                    dsu.union(p, a)
        # A named label ties every point carrying that name together.
        for name, anchors in self.labels.items():
            for other in anchors[1:]:
                dsu.union(anchors[0], other)

        self.dsu = dsu

    # ---- queries --------------------------------------------------------
    def at(self, x: float, y: float):
        return self.dsu.find(_key(x, y))

    def pin(self, ref: str, number: str):
        p = self.pins[ref][number]
        return self.dsu.find(p)

    def same(self, *pins) -> bool:
        nets = {self.pin(r, n) for r, n in pins}
        return len(nets) == 1

    def net_members(self, net) -> list:
        """Every (ref, pin) and label name sitting on `net`."""
        out = []
        for ref, pinmap in self.pins.items():
            for num, p in pinmap.items():
                if self.dsu.find(p) == net:
                    out.append(f"{ref}.{num}")
        for name, anchors in self.labels.items():
            if any(self.dsu.find(a) == net for a in anchors):
                out.append(f"<{name}>")
        return sorted(out)

    def isolated_pins(self) -> list:
        """Pins that share their net with nothing else — a dangling connection."""
        bad = []
        members = self.nets()
        for ref, pinmap in sorted(self.pins.items()):
            for num, p in sorted(pinmap.items()):
                if len(members.get(self.dsu.find(p), ())) < 2:
                    bad.append(f"{ref}.{num}")
        return bad

    # ---- whole-sheet views (added for verify_schematic_nets) -------------
    def nets(self) -> dict:
        """{net root: sorted member names} for every net carrying a pin or a
        label — one pass, where repeated `net_members()` calls are O(pins) each.

        Member names are exactly `net_members()`'s: `REF.PIN` for a symbol pin
        and `<NAME>` for a label anchor. Recomputed on every call, never cached,
        because `join()` can change membership under a caller."""
        out: dict = {}
        for ref, pinmap in self.pins.items():
            for num, p in pinmap.items():
                out.setdefault(self.dsu.find(p), []).append(f"{ref}.{num}")
        for name, anchors in self.labels.items():
            for a in anchors:
                out.setdefault(self.dsu.find(a), []).append(f"<{name}>")
        return {r: sorted(set(m)) for r, m in out.items()}

    def terminal(self, name: str):
        """Net root for a terminal written as `REF.PIN` or `<LABEL>`; None when
        the sheet carries no such pin or label (the caller reports that — this
        never invents a net)."""
        if name.startswith("<") and name.endswith(">"):
            anchors = self.labels.get(name[1:-1])
            return self.dsu.find(anchors[0]) if anchors else None
        ref, _, num = name.rpartition(".")
        p = self.pins.get(ref, {}).get(num)
        return None if p is None else self.dsu.find(p)

    def join(self, a: str, b: str) -> bool:
        """Union two terminals (`REF.PIN` / `<LABEL>`) — the hook a gate uses to
        apply a DECLARED contraction (a DC-transparent series part the netlist
        omits, or a winding whose DCR the netlist collapses). Returns False when
        either terminal is absent, so a stale declaration is reported, not
        silently applied."""
        for t in (a, b):
            if self.terminal(t) is None:
                return False
        self.dsu.union(self.terminal(a), self.terminal(b))
        return True
