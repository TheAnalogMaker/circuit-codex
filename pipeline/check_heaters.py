#!/usr/bin/env python3
"""CI gate: the heater/filament wiring a layout DECLARES is a wiring a builder
could solder, and the drawing wires exactly it.

This is a separate claim from layout<->netlist equivalence, and it is stated
separately on purpose. `verify_layout_nets.py` proves the drawn signal wiring is
electrically equivalent to the simulated netlist; heaters are not in that
netlist and are excluded from that comparison by explicit rule, so nothing in
the DC gate ever looked at a heater lead. A green PASS there says nothing at all
about the heater layer, and this file must never be read as if it did.

    DC equivalence  : the drawn signal wiring == netlist.cir      (verify_layout_nets.py)
    HEATER wiring   : the drawn heater wiring == the amp's own    (this file)
                      declared supply, connection groups and returns

What a layout declares (see docs/layout-schema.md):

    heaters:
      - id: h63
        volts: 6.3
        winding: "6.3 V secondary - green pair"
        grounded_leg: return          # feed | return | none
        sockets:
          V2: { feed: [7], return: [2] }        # octal: one pin per leg
          V1: { feed: [4, 5], return: [9] }     # noval at 6.3 V: ends strapped,
                                                #   the centre tap is the other leg

Two pin labels can never say this by themselves. The same 12AX7 runs 6.3 V
parallel (pins 4 and 5 strapped as ONE leg, the centre tap 9 the other) or
12.6 V series (4 and 5 on OPPOSITE legs, 9 carrying no supply leg). A renderer
that reads only `heater` and `heater-ct` off the basing must pick one, and
picking the series arrangement on a 6.3 V amplifier draws a short across the
supply and leaves the centre tap unwired. So the amplifier states its own
configuration and this gate proves the statement, against two things:

  the valve's datasheet   reference/tubes/<slug>.yaml `heater.supplies` - the
                          voltages the sheet permits and the pin grouping each
                          one uses. A declared configuration that is not one of
                          them is a CONFIGURATION MISMATCH.
  the drawing itself      the `runs` and `bus` the SVG is generated from, read
                          into nets exactly as render_layouts resolves them.

Checks, each with a planted fault in --selftest:

  D1  declared pins are heater-class pins of that socket's valve
  D2  the two legs are non-empty and disjoint
  D3  the declared grouping matches a datasheet supply at the declared voltage
      (this is the 6.3 V / 12.6 V configuration check)
  D4  the legs plus the supply's declared unused pins cover every heater-class
      pin of the valve - a forgotten centre tap is a hole, not a silence
  W1  every declared terminal is actually reached by a drawn conductor, and each
      socket's feed pins and return pins land on their own leg's net
      (a MISSING RETURN fails here)
  W2  the two legs are separate nets - a conductor joining them is a BRIDGE
      ACROSS THE SUPPLY, the fault a renderer that strapped 4 to 5 while calling
      them opposite legs would draw
  W3  the grounded leg reaches the ground bus and the other leg does not; a
      circuit declared `grounded_leg: none` keeps both legs off it

An amp with no `heaters:` block is reported as NOT DECLARED and is not checked -
silence is printed, never counted as coverage. Its twisted runs are drawn as the
single conductors their data names (render_layouts.heater_run_is_pair), so an
undeclared drawing asserts only what it was authored with.

    python3 pipeline/check_heaters.py             # every layout
    python3 pipeline/check_heaters.py 5f1         # one amp, with its nets
    python3 pipeline/check_heaters.py --selftest  # planted-fault mutation test
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

from render_layouts import (
    Renderer,
    is_heater_run,
    load_tube_heater_supplies,
    resolve_tube_slug,
    primary_value,
)
from verify_layout_nets import GND, LayoutGraph

ROOT = Path(__file__).resolve().parent.parent

# Basing elements that belong to the heater/filament circuit and nothing else.
HEATER_ELEMENTS = {"heater", "heater-ct", "filament"}


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


def socket_basing(R: Renderer, sid: str) -> tuple[str, dict]:
    """(tube slug, {pin: element}) for an off-board tube socket."""
    it = R.off_by_id.get(sid)
    if it is None or it.get("kind") != "tube":
        return "", {}
    slug = it.get("_tube_slug") or ""
    if not slug and it.get("ref"):
        slug = resolve_tube_slug(primary_value(R.bom_for(it["ref"])["value"]))
    path = ROOT / "reference" / "tubes" / f"{slug}.yaml"
    if not slug or not path.exists():
        return slug, {}
    data = yaml.safe_load(path.read_text()) or {}
    pins = ((data.get("basing") or {}).get("pins") or {})
    out = {}
    for k, meta in pins.items():
        try:
            out[int(k)] = str((meta or {}).get("element", "")).lower()
        except (TypeError, ValueError):
            continue
    return slug, out


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------
class HeaterResult:
    def __init__(self, amp_id: str):
        self.amp_id = amp_id
        self.declared = False
        self.errors: list[str] = []
        self.notes: list[str] = []
        # (socket, pin, pin, kind, detail) for every same-socket heater link on
        # an undeclared circuit — the worklist's findings.
        self.straps: list[tuple] = []
        # socket id -> what the drawing lands its pair on, for the worklist
        self.doubtful: dict = {}

    @property
    def ok(self) -> bool:
        return not self.errors


def _pinset(pins) -> frozenset:
    return frozenset(int(p) for p in pins)


def _supply_matches(supply: dict, legs: list[list[int]]) -> bool:
    """Does a datasheet supply's leg grouping equal this declaration's? Legs are
    unordered (feed/return is the amp's choice of which one it grounds)."""
    want = {_pinset(leg) for leg in supply["legs"]}
    got = {_pinset(leg) for leg in legs}
    return want == got and len(want) == len(got) == 2


def check_layout(amp_id: str, layout: dict, bom: dict,
                 verbose: bool = False) -> HeaterResult:
    res = HeaterResult(amp_id)
    R = Renderer(layout, bom, amp_id)
    circuits = layout.get("heaters") or []
    twisted = sum(1 for s in R.runs if is_heater_run(s))
    if not circuits:
        # Not a failure - an undeclared heater layer is an UNVERIFIED one, and
        # saying so is the point. The sockets that matter are the centre-tapped
        # ones, because those are exactly where the drawing cannot be read off
        # the pin labels: print what each one's own runs land on, and what that
        # grouping would mean, so the report is a worklist and not a shrug.
        ct = []
        for sid in sorted(R.off_by_id):
            it = R.off_by_id[sid]
            if it.get("kind") != "tube":
                continue
            slug, basing = socket_basing(R, sid)
            if not any(e == "heater-ct" for e in basing.values()):
                continue
            named = sorted(R._heater_pins_named(sid))
            supplies = load_tube_heater_supplies(slug) or []
            reading = "not read as a pair (the drawing names %d pin(s))" % len(named)
            if len(named) == 2 and not supplies:
                reading = (f"pins {named} drawn on opposite legs; "
                           f"reference/tubes/{slug}.yaml declares no heater "
                           f"supplies, so what that grouping means is unrecorded")
            elif len(named) == 2:
                same_leg = [f"{s['volts']:g} V" for s in supplies
                            if any(_pinset(leg) == frozenset(named)
                                   for leg in s["legs"])]
                split = [f"{s['volts']:g} V" for s in supplies
                         if {frozenset(leg) for leg in s["legs"]}
                         == {frozenset([named[0]]), frozenset([named[1]])}]
                if split and same_leg:
                    reading = (f"pins {named} drawn on opposite legs — the "
                               f"{', '.join(split)} grouping; at "
                               f"{', '.join(same_leg)} they are ONE leg instead")
                elif split:
                    reading = (f"pins {named} drawn on opposite legs — the "
                               f"{', '.join(split)} grouping")
                elif same_leg:
                    reading = (f"pins {named} drawn on opposite legs, but the "
                               f"{slug} sheet puts them on ONE leg at "
                               f"{', '.join(same_leg)}")
                else:
                    reading = (f"pins {named} drawn on opposite legs — no "
                               f"{slug} supply groups them either way")
            ct.append(f"{sid} [{slug}] names {named or '[]'}: {reading}")
            res.doubtful[sid] = {"tube": slug, "names": named, "reading": reading,
                                 "opposite": sid in R.heater_doubtful_sockets()}
        res.notes.append(
            f"heaters NOT DECLARED - {twisted} heater run(s). Not checked; this "
            f"drawing claims only what its own runs name.")
        for line in ct:
            res.notes.append(f"  centre-tapped socket {line}")
        if not ct:
            res.notes.append("  no centre-tapped socket on the heater chain")
        # Same-socket links, classified against the valve's own sheet. These are
        # findings, not failures: the gate cannot fix a drawing whose source has
        # not been read, but it can refuse to let one sit here unnamed.
        for sid, a, b, kind, detail in R.heater_strap_findings():
            res.straps.append((sid, a, b, kind, detail))
            if kind == "shorted":
                res.notes.append(
                    f"  FINDING - SHORTS THE SUPPLY: the drawing links {sid} "
                    f"pin {a} to pin {b}, and {detail}. Needs a read of this "
                    f"amplifier's own sheet before it can be corrected.")
            else:
                res.notes.append(
                    f"  FINDING - needs a source read: the drawing links {sid} "
                    f"pin {a} to pin {b}; {detail}.")
        return res

    res.declared = True
    LG = LayoutGraph(R)
    res.errors += [f"{amp_id}: {e}" for e in LG.errors]

    for ci, circuit in enumerate(circuits):
        cid = str(circuit.get("id", f"heaters[{ci}]"))
        tag = f"{amp_id} heaters/{cid}"
        try:
            volts = float(circuit.get("volts"))
        except (TypeError, ValueError):
            res.errors.append(f"{tag}: no numeric `volts:` - a heater circuit "
                              f"must state the supply voltage it wires")
            continue
        grounded = str(circuit.get("grounded_leg", "")).lower()
        if grounded not in ("feed", "return", "none"):
            res.errors.append(
                f"{tag}: grounded_leg must be feed | return | none, got "
                f"{circuit.get('grounded_leg')!r}")
            continue
        sockets = circuit.get("sockets") or {}
        if not sockets:
            res.errors.append(f"{tag}: declares no sockets")
            continue

        leg_terms: list[list[str]] = [[], []]     # [feed terminals, return terminals]
        for sid in sorted(sockets):
            groups = sockets[sid] or {}
            ctx = f"{tag} {sid}"
            it = R.off_by_id.get(sid)
            if it is None or it.get("kind") != "tube":
                res.errors.append(f"{ctx}: no such tube socket in this layout")
                continue
            slug, basing = socket_basing(R, sid)
            if not basing:
                res.errors.append(f"{ctx}: no basing for tube '{slug or '?'}' - "
                                  f"a heater claim cannot rest on an unknown valve")
                continue
            try:
                legs = [[int(p) for p in (groups.get("feed") or [])],
                        [int(p) for p in (groups.get("return") or [])]]
            except (TypeError, ValueError):
                res.errors.append(f"{ctx}: feed/return must be pin-number lists")
                continue

            # D2 - legs non-empty and disjoint
            if not legs[0] or not legs[1]:
                res.errors.append(
                    f"{ctx}: MISSING SUPPLY LEG - feed={legs[0] or '[]'} "
                    f"return={legs[1] or '[]'}; a heater needs both legs")
                continue
            both = _pinset(legs[0]) & _pinset(legs[1])
            if both:
                res.errors.append(
                    f"{ctx}: pin(s) {sorted(both)} declared on BOTH supply legs "
                    f"- that is a short across the supply, not a connection group")
                continue

            # D1 - declared pins are heater-class pins of this valve
            stray = sorted(p for leg in legs for p in leg
                           if basing.get(p) not in HEATER_ELEMENTS)
            if stray:
                what = ", ".join(f"pin {p} is {basing.get(p, 'not on this basing')}"
                                 for p in stray)
                res.errors.append(
                    f"{ctx}: declared on pin(s) {stray}, which are not heater "
                    f"pins of the {slug} ({what})")
                continue

            # D3 - the grouping matches a datasheet supply at this voltage
            supplies = load_tube_heater_supplies(slug)
            if not supplies:
                res.errors.append(
                    f"{ctx}: reference/tubes/{slug}.yaml declares no "
                    f"`heater.supplies` - the datasheet fact the declared "
                    f"{volts:g} V configuration would be proved against is missing")
                continue
            at_volts = [s for s in supplies if abs(s["volts"] - volts) < 1e-6]
            if not at_volts:
                listed = ", ".join(f"{s['volts']:g} V" for s in supplies)
                res.errors.append(
                    f"{ctx}: CONFIGURATION MISMATCH - {volts:g} V is not a supply "
                    f"the {slug} sheet lists ({listed})")
                continue
            shown = "; ".join(
                " | ".join(str(sorted(leg)) for leg in s["legs"])
                + (f" (pin(s) {sorted(s['unused'])} carry no supply leg)"
                   if s["unused"] else "")
                for s in at_volts)

            # D4 - every heater-class pin accounted for. This is the check the
            # 5F1 fault needed: wiring a centre-tapped valve as though it were
            # in series leaves the centre tap on no leg at all, and an unwired
            # heater terminal is a hole in the drawing, not a silence.
            heater_pins = {p for p, e in basing.items() if e in HEATER_ELEMENTS}
            allowed_unused = set()
            for s in at_volts:
                allowed_unused |= _pinset(s["unused"])
            missing = sorted(heater_pins - _pinset(legs[0]) - _pinset(legs[1])
                             - allowed_unused)
            if missing:
                res.errors.append(
                    f"{ctx}: CONFIGURATION MISMATCH - declared "
                    f"{sorted(legs[0])} | {sorted(legs[1])} at {volts:g} V leaves "
                    f"heater pin(s) {missing} on no supply leg; the {slug} sheet "
                    f"wires {volts:g} V as {shown}")
                continue

            # D3 - the grouping itself matches a datasheet supply
            match = next((s for s in at_volts if _supply_matches(s, legs)), None)
            if match is None:
                res.errors.append(
                    f"{ctx}: CONFIGURATION MISMATCH - declared "
                    f"{sorted(legs[0])} | {sorted(legs[1])} at {volts:g} V, but the "
                    f"{slug} sheet wires {volts:g} V as {shown}")
                continue

            for k in (0, 1):
                leg_terms[k] += [f"{sid}.pin{p}" for p in legs[k]]
            if verbose:
                res.notes.append(
                    f"  {sid}: {volts:g} V  feed {sorted(legs[0])}  "
                    f"return {sorted(legs[1])}  [{slug}]")

        if not leg_terms[0] or not leg_terms[1]:
            continue                        # already reported above

        # ---- W1/W2/W3: what the DRAWING does with those terminals ---------
        nets = [set(), set()]
        unreached = False
        for k in (0, 1):
            for t in leg_terms[k]:
                if t not in LG.uf.parent:
                    unreached = True
                    res.errors.append(
                        f"{tag}: {t} is declared on the "
                        f"{'feed' if k == 0 else 'return'} leg but NO drawn "
                        f"conductor lands on it - "
                        f"{'MISSING RETURN' if k == 1 else 'MISSING FEED'}")
                    continue
                nets[k].add(LG.net(t))
        if unreached:
            continue          # the drawn-net checks below would only echo it
        for k, name in ((0, "feed"), (1, "return")):
            if len(nets[k]) > 1:
                res.errors.append(
                    f"{tag}: the {name} leg is drawn as {len(nets[k])} separate "
                    f"nets - {sorted(leg_terms[k])} do not all connect")
        if nets[0] & nets[1]:
            res.errors.append(
                f"{tag}: SUPPLY LEGS BRIDGED - the feed leg {sorted(leg_terms[0])} "
                f"and the return leg {sorted(leg_terms[1])} are drawn on ONE net; "
                f"a conductor joins them and shorts the {volts:g} V supply")
        want_gnd = {"feed": 0, "return": 1, "none": -1}[grounded]
        gnd_root = LG.net(GND) if GND in LG.uf.parent else None
        for k, name in ((0, "feed"), (1, "return")):
            on_gnd = gnd_root is not None and gnd_root in nets[k]
            if k == want_gnd and not on_gnd:
                res.errors.append(
                    f"{tag}: the {name} leg is declared grounded but no drawn "
                    f"conductor takes it to the ground bus")
            if k != want_gnd and on_gnd:
                res.errors.append(
                    f"{tag}: the {name} leg reaches the ground bus, but this "
                    f"circuit grounds "
                    f"{'the ' + grounded + ' leg' if grounded != 'none' else 'neither leg'}")
        if verbose:
            res.notes.append(f"  {cid}: {volts:g} V, grounded leg = {grounded}; "
                             f"feed net {sorted(nets[0])} / return net {sorted(nets[1])}")
    return res


# ---------------------------------------------------------------------------
# the committed worklist
# ---------------------------------------------------------------------------
WORKLIST = ROOT / "reference" / "heaters.yaml"

WORKLIST_HEADER = """\
# GENERATED - pipeline/check_heaters.py --export. Do not hand-edit; a run that
# disagrees with this file fails the gate, the same way reference/op-points.yaml
# and reference/loadlines.yaml are held to what a fresh run produces.
#
# WHAT THIS IS. The heater layer of a board drawing is a separate claim from the
# DC equivalence `wiring_claim: verified` makes, and until 2026-09-09 nothing
# checked it at all (see docs/layout-schema.md, "Heater wiring is its own
# claim"). One circuit - the 5F1 - has since been read against its own factory
# sheet and declares its supply, connection groups and grounded return, which
# the gate proves. Every other layout draws a heater layer that has NOT been
# established, and this file is the standing worklist of exactly what is
# unestablished on each, so the work is tractable rather than a vague backlog.
#
# HOW TO READ IT. `doubtful_sockets` are centre-tapped valves whose drawing puts
# the two heater pins on OPPOSITE supply legs - the 12.6 V series arrangement.
# On a 6.3 V amplifier those two pins are ONE leg and the centre tap is the
# other, so each entry is a socket whose grouping turns on a fact only that
# amplifier's own drawing carries. `findings` are same-socket links: `shorted`
# joins two pins the valve's own sheet puts on opposite legs at every supply it
# lists (wrong whatever the amplifier runs), `unclassified` joins two pins that
# are one leg at one supply and opposite legs at another.
#
# CLEARING AN ENTRY. Read that amplifier's own drawing, add a `heaters:` block
# to its layout.yaml stating what it shows, correct the runs to match, and
# re-export. The count in `summary` is the size of the job.
"""


def worklist(results: list | None = None) -> dict:
    """The corpus-wide heater state, as data - what each layout declares, what
    it leaves unestablished, and every same-socket link needing a source read.
    Pass the results of a full run to avoid checking every layout twice."""
    by_id = {r.amp_id: r for r in (results or [])}
    amps: dict = {}
    ids = sorted(p.parent.name for p in (ROOT / "amps").glob("*/layout.yaml"))
    for amp_id in ids:
        layout, bom = load_amp(amp_id)
        res = by_id.get(amp_id) or check_layout(amp_id, layout, bom)
        entry: dict = {"declared": bool(res.declared)}
        if res.declared:
            entry["circuits"] = [
                {"id": str(c.get("id", "")), "volts": float(c.get("volts", 0)),
                 "grounded_leg": str(c.get("grounded_leg", "")),
                 "sockets": {str(k): {"feed": [int(p) for p in (v or {}).get("feed", [])],
                                      "return": [int(p) for p in (v or {}).get("return", [])]}
                             for k, v in (c.get("sockets") or {}).items()}}
                for c in (layout.get("heaters") or [])]
        else:
            entry["centre_tapped_sockets"] = {
                sid: {"tube": d["tube"], "drawn_on_pins": list(d["names"]),
                      "grouping": ("opposite-legs" if d["opposite"] else "not-drawn-as-a-pair"),
                      "reading": d["reading"]}
                for sid, d in sorted(res.doubtful.items())}
            entry["findings"] = [
                {"socket": sid, "pins": [a, b], "kind": kind, "detail": detail}
                for sid, a, b, kind, detail in res.straps]
        amps[amp_id] = entry
    n_doubt = sum(1 for a in amps.values()
                  for sock in (a.get("centre_tapped_sockets") or {}).values()
                  if sock["grouping"] == "opposite-legs")
    findings = [f for a in amps.values() for f in (a.get("findings") or [])]
    return {
        "summary": {
            "layouts": len(amps),
            "declared_and_checked": sum(1 for a in amps.values() if a["declared"]),
            "not_established": sum(1 for a in amps.values() if not a["declared"]),
            "doubtful_sockets": n_doubt,
            "links_that_short_the_supply": sum(1 for f in findings
                                               if f["kind"] == "shorted"),
            "links_needing_a_source_read": sum(1 for f in findings
                                               if f["kind"] == "unclassified"),
        },
        "amps": amps,
    }


def export_worklist() -> int:
    data = worklist()
    WORKLIST.write_text(WORKLIST_HEADER
                        + yaml.safe_dump(data, sort_keys=True, width=100,
                                         allow_unicode=True))
    print(f"exported {WORKLIST.relative_to(ROOT)} - "
          + ", ".join(f"{k} {v}" for k, v in data["summary"].items()))
    return 0


def check_worklist(results: list | None = None) -> list[str]:
    """The committed worklist must be what a fresh run produces. A stale one
    would understate (or overstate) a job the corpus is measuring itself by."""
    if not WORKLIST.exists():
        return [f"{WORKLIST.relative_to(ROOT)} is missing - "
                f"regenerate with pipeline/check_heaters.py --export"]
    committed = yaml.safe_load(WORKLIST.read_text()) or {}
    fresh = worklist(results)
    if committed == fresh:
        return []
    out = [f"{WORKLIST.relative_to(ROOT)} is stale - regenerate with "
           f"pipeline/check_heaters.py --export"]
    for key in ("summary",):
        if committed.get(key) != fresh.get(key):
            out.append(f"    committed {key}: {committed.get(key)}")
            out.append(f"    fresh     {key}: {fresh.get(key)}")
    ca, fa = committed.get("amps") or {}, fresh.get("amps") or {}
    changed = sorted(k for k in set(ca) | set(fa) if ca.get(k) != fa.get(k))
    if changed:
        out.append(f"    amps that differ: {', '.join(changed)}")
    return out


# ---------------------------------------------------------------------------
# self-test - a gate that cannot catch planted faults is decoration
# ---------------------------------------------------------------------------
def _mutate(layout: dict, fn) -> dict:
    m = copy.deepcopy(layout)
    fn(m)
    return m


def selftest() -> int:
    """Plant one fault per hole class on a clean, declared layout and require
    each to be CAUGHT; require the unmutated layout to PASS."""
    amp = "5f1"
    layout, bom = load_amp(amp)
    if not (layout.get("heaters") or []):
        print(f"SELFTEST CANNOT RUN: amps/{amp}/layout.yaml declares no heaters")
        return 1

    fails = 0

    base = check_layout(amp, layout, bom)
    if base.ok and base.declared:
        print(f"  ok   BASELINE       {amp} declared heater wiring PASSES")
    else:
        fails += 1
        print(f"  FAIL BASELINE       {amp} should pass but did not:")
        for e in base.errors:
            print(f"         {e}")

    def sockets(m):
        return m["heaters"][0]["sockets"]

    def drop_run(m, term):
        """Delete every run that touches a terminal — the drawing simply never
        wires it."""
        m["runs"] = [r for r in m["runs"]
                     if term not in (r.get("from"), r.get("to"))]

    cases = [
        ("W1 missing return",
         "the 12AX7 centre-tap return lead is deleted from the drawing",
         lambda m: drop_run(m, "V1.pin9")),
        ("W2 legs bridged",
         "a conductor is drawn from the 12AX7's strapped ends to its own "
         "grounded centre tap",
         lambda m: m["runs"].append({"from": "V1.pin5", "to": "V1.pin9",
                                     "color": "green"})),
        ("D4 6.3/12.6 mismatch",
         "the 6.3 V parallel declaration is rewritten as the 12.6 V series "
         "grouping — pins 4 and 5 on opposite legs, centre tap on neither",
         lambda m: sockets(m).__setitem__("V1", {"feed": [4], "return": [5]})),
        ("D3 wrong grouping",
         "all three heater pins are declared, but a heater end is grouped with "
         "the centre tap instead of with the other end",
         lambda m: sockets(m).__setitem__("V1", {"feed": [4, 9], "return": [5]})),
        ("D1 not a heater pin",
         "the return leg is declared on the 6V6's cathode",
         lambda m: sockets(m).__setitem__("V2", {"feed": [7], "return": [8]})),
        ("W3 grounded leg not grounded",
         "the circuit claims a floating supply while the drawing grounds a leg",
         lambda m: m["heaters"][0].__setitem__("grounded_leg", "none")),
        ("D2 pin on both legs",
         "one pin is declared on both supply legs",
         lambda m: sockets(m).__setitem__("V1", {"feed": [4, 5], "return": [5, 9]})),
    ]
    for hole, label, fn in cases:
        res = check_layout(amp, _mutate(layout, fn), bom)
        if res.errors:
            print(f"  ok   {hole:<22} CAUGHT  ({label})")
            print(f"         -> {res.errors[0]}")
        else:
            fails += 1
            print(f"  FAIL {hole:<22} ESCAPED ({label})")

    print(f"\nselftest: {len(cases) + 1} case(s), {fails} failure(s)")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--export" in argv:
        return export_worklist()
    only = [a for a in argv if not a.startswith("-")]
    ids = only or sorted(p.parent.name for p in (ROOT / "amps").glob("*/layout.yaml"))
    errors: list[str] = []
    declared = 0
    results: list[HeaterResult] = []
    for amp_id in ids:
        layout, bom = load_amp(amp_id)
        res = check_layout(amp_id, layout, bom, verbose=bool(only))
        results.append(res)
        if res.declared:
            declared += 1
        errors += res.errors
        state = "DECLARED" if res.declared else "not declared"
        mark = "ok  " if res.ok else "FAIL"
        print(f"{mark} {amp_id:<14} heaters {state}")
        for n in res.notes:
            print(f"       {n}")
        for e in res.errors:
            print(f"       FAIL {e}")
    shorted = [f"{r.amp_id} {sid} pins {a}-{b}"
               for r in results for sid, a, b, kind, _d in r.straps
               if kind == "shorted"]
    unclassified = sum(1 for r in results for _s, _a, _b, k, _d in r.straps
                       if k == "unclassified")
    doubtful = sum(1 for r in results for d in r.doubtful.values() if d["opposite"])
    print(f"\nchecked {len(ids)} layout(s): {declared} declare a heater circuit "
          f"and were verified, {len(ids) - declared} do not and were NOT checked")
    print(f"  {doubtful} centre-tapped socket(s) drawn on a leg grouping that is "
          f"not established; {unclassified} link(s) need a source read")
    if shorted:
        print(f"  {len(shorted)} link(s) SHORT THE SUPPLY as drawn and need a "
              f"source read: {'; '.join(shorted)}")
    if not only:
        # The worklist is committed, so a run that disagrees with it fails —
        # a stale worklist misstates the size of the job it exists to measure.
        stale = check_worklist(results)
        for line in stale:
            print(f"FAIL {line}" if not line.startswith("    ") else line)
        errors += [line for line in stale if not line.startswith("    ")]
    print(f"  {len(errors)} failure(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
