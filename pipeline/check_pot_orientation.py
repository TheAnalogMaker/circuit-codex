#!/usr/bin/env python3
"""CI gate: every potentiometer is DRAWN from the side the layout says it is
drawn from.

A separate claim from layout<->netlist equivalence, and it must never be read as
covered by it. `verify_layout_nets.py` proves that the lug a run lands on sits on
the right netlist node — that `VR1.lug1` really is the grounded end. It says
nothing whatever about where lug 1 sits on the PAGE, because a drawing whose
three lugs are laid out in the mirror order is still electrically the same
drawing. So until this gate, a pot could be wired backwards on every board in the
corpus and every check would stay green:

    DC equivalence  : the drawn wiring == netlist.cir            (verify_layout_nets.py)
    POT ORIENTATION : the drawn lug ORDER == the sheet's own      (this file)
                      declared viewing side

The invariant this gate rests on
--------------------------------
A potentiometer's terminals are numbered by the part, not by the drawing: 1 is
the counter-clockwise end, 2 the wiper, 3 the clockwise end. That triad is rigid.
How it is clocked in its mounting hole is free; which way round it reads is not:

    seen from the SHAFT side (knob, component side)  1 -> 2 -> 3 runs COUNTER-CLOCKWISE
    seen from the WIRING side (rear, into the chassis)  1 -> 2 -> 3 runs CLOCKWISE

That is why the sweep — not the position — is the thing to check: it survives any
rotation of the pot and pins down exactly one fact, which side of the chassis the
reader is standing on. A board-layout diagram is drawn from ONE side, so every pot
on a sheet must sweep the same way, and which way is what `conventions.layout_view`
declares.

Read off the factory sheets (2026-09-09): Fender draws the lug fan on the panel
side of the body with the grounded lug at the counter-clockwise end of the fan —
1 -> 2 -> 3 clockwise, i.e. a wiring-side view — on the 5E3 (F-EE), 5F6-A (I-EG),
6G3 (I-FA), AB763 Twin and Deluxe Reverb (C-FD) and AA1164 sheets alike. The tube
sockets on those same sheets number their pins clockwise, which is the standard
bottom-view basing order and the same wiring-side reading. `tube_pin_pos()` has
always drawn its rings that way. Before 2026-09-09 `pot_lug_pos()` did not: it
offset lug 1..3 along the tangent with a fixed sign, so the two edges whose
board-facing normal points the other way — `top` and `right` — came out mirrored,
and 213 of the corpus's 215 pots are `edge: top`.

Checks, each with a planted fault in --selftest
-----------------------------------------------
  V1  a pot whose drawn lug sweep contradicts the layout's declared view
  V2  a drawing whose pots do not all sweep the same way — a sheet cannot be two
      views at once, so this fires even where nothing is declared
  V3  a `conventions.layout_view` or per-pot `lugs:` value that is not one of the
      permitted words
  V4  three lugs with no readable sweep at all: coincident, collinear through the
      body, or off the pot's own rim — the shape a renderer regression leaves
  V5  a pot whose fan points the opposite way from its own `lugs:` declaration

V2 is deliberately not enough on its own. The corpus's actual fault was uniform:
every top-edge pot mirrored, which is perfectly self-consistent and invisible to a
consistency check. Only a DECLARED view can catch a drawing that is coherently
wrong, which is the whole reason `conventions.layout_view` exists rather than
being inferred from the drawing it is meant to judge.

    python3 pipeline/check_pot_orientation.py             # every layout
    python3 pipeline/check_pot_orientation.py 5e3         # one amp, pot by pot
    python3 pipeline/check_pot_orientation.py --report    # every pot, with angles
    python3 pipeline/check_pot_orientation.py --selftest  # planted-fault mutation test
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml

from render_layouts import Renderer

ROOT = Path(__file__).resolve().parent.parent

VIEWS = ("wiring", "component")
FAN_SIDES = ("board", "panel")
DEFAULT_VIEW = "wiring"
DEFAULT_FAN = "board"

# Which way the board lies from an off-board item on each edge, in SVG's y-down
# frame. Same table the renderer places terminals with.
BOARD_NORMAL = {"top": (0.0, 1.0), "bottom": (0.0, -1.0),
                "left": (1.0, 0.0), "right": (-1.0, 0.0)}


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_amp(amp_id: str) -> tuple[dict, dict]:
    d = ROOT / "amps" / amp_id
    layout = yaml.safe_load((d / "layout.yaml").read_text()) or {}
    bom_raw = yaml.safe_load((d / "bom.yaml").read_text()) or {}
    items = bom_raw.get("items", bom_raw) if isinstance(bom_raw, dict) else bom_raw
    bom = {it["ref"]: it for it in (items or []) if isinstance(it, dict) and "ref" in it}
    return layout, bom


def load_declared_view(amp_id: str) -> str | None:
    """meta.yaml `conventions.layout_view`, or None where the amp is silent.

    Silence is not an error — it means the corpus default (`wiring`), which is
    what every factory sheet read so far draws. It is recorded as silence rather
    than rewritten so a reader can tell a default from a decision."""
    path = ROOT / "amps" / amp_id / "meta.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:  # noqa: BLE001 — a malformed meta.yaml is validate.py's finding
        return None
    v = ((data.get("conventions") or {}).get("layout_view"))
    return None if v is None else str(v).strip().lower()


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def lug_positions(R: Renderer, item: dict) -> list[tuple[float, float]]:
    """Where the RENDERER puts lugs 1, 2, 3 — asked of the renderer, never
    recomputed here. A gate that reimplements the geometry it is checking cannot
    see the renderer change under it."""
    return [tuple(R.pot_lug_pos(item, lug)) for lug in (1, 2, 3)]


def clock_deg(cx: float, cy: float, px: float, py: float) -> float:
    """Bearing of a point about a body centre, in degrees clockwise from
    straight up the page (0 = 12 o'clock, 90 = 3 o'clock). SVG's y grows
    downward, which is why the y term is negated."""
    return math.degrees(math.atan2(px - cx, -(py - cy))) % 360.0


def sweep(angles: list[float]) -> str:
    """'clockwise' | 'counter-clockwise' | 'none' for three bearings in lug
    order. A fan spans well under a half turn, so each step must be a short arc
    the same way round; anything else has no sweep to read."""
    def steps(seq):
        return [(seq[i + 1] - seq[i]) % 360.0 for i in range(len(seq) - 1)]
    fwd = steps(angles)
    if all(0.5 < s < 179.5 for s in fwd):
        return "clockwise"
    rev = steps(list(reversed(angles)))
    if all(0.5 < s < 179.5 for s in rev):
        return "counter-clockwise"
    return "none"


def expected_sweep(view: str) -> str:
    return "clockwise" if view == "wiring" else "counter-clockwise"


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------
class PotResult:
    def __init__(self, amp_id: str):
        self.amp_id = amp_id
        self.declared: str | None = None
        self.view = DEFAULT_VIEW
        self.pots: list[dict] = []      # one row per pot, for --report
        self.errors: list[str] = []
        self.notes: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def check_layout(amp_id: str, layout: dict, bom: dict,
                 declared: str | None = None,
                 lug_reader=lug_positions) -> PotResult:
    res = PotResult(amp_id)
    res.declared = declared
    if declared is not None and declared not in VIEWS:
        res.errors.append(
            f"V3 conventions.layout_view: {declared!r} is not one of "
            f"{'|'.join(VIEWS)} — the drawing must name the side it is drawn from")
        return res
    res.view = declared or DEFAULT_VIEW
    want = expected_sweep(res.view)

    R = Renderer(layout, bom, amp_id)
    pots = [it for it in R.offboard if it.get("kind") == "pot"]
    if not pots:
        res.notes.append("no pots on this layout")
        return res

    seen: dict[str, list[str]] = {}
    for it in pots:
        pid = str(it.get("id") or it.get("ref") or "?")
        edge = str(it.get("edge", "top"))
        fan = str(it.get("lugs", DEFAULT_FAN)).strip().lower()
        cx, cy = R.off_pos(it)
        pts = lug_reader(R, it)
        angles = [clock_deg(cx, cy, px, py) for px, py in pts]
        radii = [math.dist((cx, cy), p) for p in pts]
        got = sweep(angles)
        row = {"pot": pid, "edge": edge, "lugs": fan,
               "angles": [round(a, 1) for a in angles],
               "clock": [f"{int(a // 30) or 12}:{int((a % 30) * 2):02d}" for a in angles],
               "sweep": got}
        res.pots.append(row)

        if fan not in FAN_SIDES:
            res.errors.append(
                f"V3 {pid}: lugs: {fan!r} is not one of {'|'.join(FAN_SIDES)}")
            continue

        # V4 — a fan the renderer has stopped drawing as a fan.
        rmin, rmax = min(radii), max(radii)
        if got == "none" or rmin <= 0.0 or rmax > rmin * 1.6:
            res.errors.append(
                f"V4 {pid}: the three lugs are not a readable fan about the pot "
                f"body (bearings {row['angles']}, radii "
                f"{[round(r, 1) for r in radii]}) — two of them coincide, they "
                f"do not step the same way round, or one sits at a different "
                f"radius from the others")
            continue

        # V5 — the fan points where the pot says it points.
        nx, ny = BOARD_NORMAL.get(edge, BOARD_NORMAL["top"])
        mx = sum(p[0] for p in pts) / 3.0 - cx
        my = sum(p[1] for p in pts) / 3.0 - cy
        toward_board = (mx * nx + my * ny) > 0
        if toward_board != (fan == "board"):
            res.errors.append(
                f"V5 {pid}: declared lugs: {fan} but the fan is drawn on the "
                f"{'board' if toward_board else 'panel'} side of the body "
                f"(edge: {edge})")

        # V1 — the sweep against the declared view.
        if got != want:
            res.errors.append(
                f"V1 {pid}: lugs 1->2->3 sweep {got} about the body "
                f"({' -> '.join(row['clock'])}), but layout_view "
                f"{res.view}{'' if declared else ' (default)'} means a "
                f"{want} sweep — lug 1 is drawn on the wrong end of the fan")
        seen.setdefault(got, []).append(pid)

    # V2 — one sheet, one side. Fires with or without a declaration.
    if len(seen) > 1:
        detail = "; ".join(f"{s}: {', '.join(ids)}" for s, ids in sorted(seen.items()))
        res.errors.append(
            f"V2 mixed view — the pots on this drawing do not all sweep the same "
            f"way ({detail}); a single sheet is drawn from one side")
    return res


# ---------------------------------------------------------------------------
# self-test — a gate that cannot catch planted faults is decoration
# ---------------------------------------------------------------------------
def _mirror_reader(only: str | None = None):
    """Return a lug reader that mirrors the fan of one pot (or all of them).

    The mirror is what the pre-2026-09-09 `pot_lug_pos()` produced on a top- or
    right-edge pot: the same three points, lug 1 and lug 3 exchanged. Planting it
    is planting the historical fault, not an invented one."""
    def reader(R, item):
        pts = lug_positions(R, item)
        pid = str(item.get("id") or item.get("ref") or "?")
        if only is None or pid == only:
            pts = list(reversed(pts))
        return pts
    return reader


def _collapse_reader(R, item):
    """A renderer that has stopped fanning the lugs at all."""
    p = R.pot_lug_pos(item, 2)
    return [tuple(p), tuple(p), tuple(p)]


def _panel_reader(R, item):
    """The fan swung to the far side of the body — the pot turned 180 degrees in
    its own hole. A rotation, so the sweep is untouched and only the side moves:
    exactly the drawing a `lugs:` declaration is there to pin down."""
    cx, cy = R.off_pos(item)
    return [(2 * cx - px, 2 * cy - py) for px, py in lug_positions(R, item)]


def selftest() -> int:
    amp = "5e3"                       # three pots, all edge: top, wiring-side view
    layout, bom = load_amp(amp)
    pots = [it for it in (layout.get("offboard") or []) if it.get("kind") == "pot"]
    if len(pots) < 2:
        print(f"SELFTEST CANNOT RUN: amps/{amp}/layout.yaml needs at least two pots")
        return 1
    first = str(pots[0].get("id"))
    fails = 0

    base = check_layout(amp, layout, bom, declared=None)
    if base.ok:
        print(f"  ok   BASELINE          {amp}: {len(base.pots)} pot(s) sweep "
              f"{expected_sweep(base.view)} against layout_view {base.view}")
    else:
        fails += 1
        print(f"  FAIL BASELINE          {amp} should pass and did not:")
        for e in base.errors:
            print(f"         {e}")
        print("         (on a tree where the pot_lug_pos sign fix has NOT landed "
              "this is the finding, not a broken gate — see docs/layout-schema.md)")

    cases = [
        ("V1 whole sheet mirrored", "V1",
         "every pot drawn from the knob side while the amp declares the wiring "
         "side — the corpus's own pre-fix state, self-consistent and so invisible "
         "to V2 alone",
         dict(declared="wiring", lug_reader=_mirror_reader(None))),
        ("V2 mixed view", "V2",
         f"one pot ({first}) mirrored and the rest not, with NOTHING declared",
         dict(declared=None, lug_reader=_mirror_reader(first))),
        ("V1 single pot mirrored", "V1",
         f"one pot ({first}) mirrored on a sheet that declares the wiring side",
         dict(declared="wiring", lug_reader=_mirror_reader(first))),
        ("V3 unknown view word", "V3",
         "the amp declares layout_view: rear, which is not one of the two words",
         dict(declared="rear")),
        ("V4 fan collapsed", "V4",
         "a renderer regression puts all three lugs on one point",
         dict(declared="wiring", lug_reader=_collapse_reader)),
        ("V5 fan on the wrong side", "V5",
         "the pot is turned 180 degrees in its hole — fan toward the panel, "
         "sweep untouched — while the layout still says lugs: board",
         dict(declared="wiring", lug_reader=_panel_reader)),
    ]
    for hole, code, label, kw in cases:
        res = check_layout(amp, layout, bom, **kw)
        hit = [e for e in res.errors if e.startswith(code)]
        if hit:
            print(f"  ok   {hole:<24} CAUGHT  ({label})")
            print(f"         -> {hit[0]}")
        else:
            fails += 1
            print(f"  FAIL {hole:<24} ESCAPED ({label})")
            if res.errors:
                print(f"         (it reported {res.errors[0].split(':')[0]}, "
                      f"not {code})")

    print(f"\nselftest: {len(cases) + 1} case(s), {fails} failure(s)")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    report = "--report" in argv
    only = [a for a in argv if not a.startswith("-")]
    ids = only or sorted(p.parent.name for p in (ROOT / "amps").glob("*/layout.yaml"))
    errors: list[str] = []
    declared_n = 0
    npots = 0
    for amp_id in ids:
        layout, bom = load_amp(amp_id)
        declared = load_declared_view(amp_id)
        res = check_layout(amp_id, layout, bom, declared=declared)
        if declared:
            declared_n += 1
        npots += len(res.pots)
        errors += res.errors
        state = f"{res.view}" + ("" if declared else " (default)")
        mark = "ok  " if res.ok else "FAIL"
        print(f"{mark} {amp_id:<14} {len(res.pots):>2} pot(s), view {state}")
        for n in res.notes:
            print(f"       {n}")
        if report or only:
            for row in res.pots:
                print(f"       {row['pot']:<8} edge {row['edge']:<6} "
                      f"lugs {row['lugs']:<5} {' -> '.join(row['clock']):<20} "
                      f"{row['sweep']}")
        for e in res.errors:
            print(f"       FAIL {e}")
    print(f"\nchecked {len(ids)} layout(s), {npots} pot(s); "
          f"{declared_n} amp(s) declare a layout_view, "
          f"{len(ids) - declared_n} take the {DEFAULT_VIEW} default")
    print(f"  {len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
