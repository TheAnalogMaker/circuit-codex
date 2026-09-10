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
        grounded_leg: return          # feed | return | none | humdinger | winding-ct
        pilot: { PL1: { return: chassis, source: "..." } }   # only where the
                                      #   sheet draws one lamp terminal (see W4)
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
      circuit declared `grounded_leg: none` keeps both legs off it; and a
      circuit declared `grounded_leg: humdinger` floats BOTH legs and returns
      through an artificial centre tap, which it must NAME (`humdinger: VR9`,
      or a list for the two-resistor arrangement). The named part is checked
      like any other claim: drawn on this board, reaching the ground bus, and
      spanning both supply legs — a grounded part touching one leg is not a
      centre tap, and "neither leg is grounded" on its own is indistinguishable
      from a return nobody drew. A circuit declared `grounded_leg: winding-ct`
      floats both legs too, and grounds the WINDING'S OWN centre tap - the
      blackface arrangement, where the transformer's green-yellow lead is tied
      to the red-yellow HT centre tap and taken to chassis. It must NAME that
      lead (`winding_ct: TR1.green-yellow`), and the named lead is checked: a
      transformer lead of this board, drawn, and reaching the ground bus.
  W4  the pilot lamp sits ACROSS the supply: both of its terminals are reached
      by a drawn conductor and they sit on the two different legs (on a
      single-ended supply the grounded leg IS the chassis, so a terminal on
      the ground bus is on that leg). Both terminals on one leg is a dark lamp
      that W1-W3 cannot see; a terminal on a net carrying neither leg is a
      lamp drawn in series with the chain. Where a sheet draws the lamp with
      ONE terminal - the feed arriving and the chain leaving on it, the
      holder's shell being the chassis return - the circuit says so:
      `pilot: { PL1: { return: chassis, source: "..." } }`, allowed only on a
      circuit that grounds a leg, and then the one drawn terminal must sit on
      the fed leg and the other must be drawn to nothing. A lamp that touches
      no leg of a circuit is not that circuit's lamp and is not checked by it.

A same-socket link joining two heater terminals is a finding whatever STYLE the
run carries. It used to be tested only on heater-styled runs, which left the
worst case invisible: the 6G2 drew a plain conductor across its rectifier's own
5 V filament pins and neither gate objected — not this one, because the run was
not green; not the DC gate, which excludes the rectifier socket by rule.

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
    load_tube_heater_pins,
    load_tube_heater_supplies,
    resolve_tube_slug,
    primary_value,
)
from verify_layout_nets import GND, LayoutGraph

ROOT = Path(__file__).resolve().parent.parent

# Basing elements that belong to the heater/filament circuit and nothing else.
# NOT the whole answer to "is this a heater pin", and D1/D4 must not use it as
# though it were: a pin can carry a heater AND something else, and then it is
# labelled for the other role. The GZ34's pin 8 is the heater's far end and the
# cathode, labelled `cathode`; reading these labels alone made its 5 V winding
# look like a one-pin heater and made the true circuit unstateable — D1 threw
# out the pin the sheet puts the winding on. load_tube_heater_pins() unions
# these labels with the valve's own `heater.shared_pins` — the reviewed list of
# pins carrying a heater end under another element's name, which T1 below proves
# against the basing — and that union is the single authority both checks use.
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
        # The DRAWING's own verdict, from render_layouts.heater_fully_declared:
        # every socket the heater ink lands on is covered by a declaration. Not
        # the same as "nothing is ambiguous" — a board of octal sockets has no
        # ambiguity and still has never been read against its sheet — and not
        # the same as `declared`, which is true of a layout that has stated one
        # circuit of two. This is the field that measures the job.
        self.fully_declared = False
        self.errors: list[str] = []
        self.notes: list[str] = []
        # (socket, pin, pin, kind, detail) for every same-socket heater link on
        # an undeclared circuit — the worklist's findings.
        self.straps: list[tuple] = []
        # socket id -> what the drawing lands its pair on, for the worklist
        self.doubtful: dict = {}
        # (circuit id, lamp id, how it sits across the legs) for every pilot
        # lamp W4 proved - the positive record, so a selftest can tell "the
        # lamp passed" from "nothing looked at the lamp".
        self.lamps: list[tuple] = []
        # Why an undeclared heater layer is still undeclared, where the answer
        # is not "no factory sheet" but "no copy that resolves the pins yet".
        self.pending = ""

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
    res.fully_declared = R.heater_fully_declared
    circuits = layout.get("heaters") or []
    twisted = sum(1 for s in R.runs if is_heater_run(s))

    # WHAT IS STILL UNESTABLISHED - surveyed for EVERY layout, declared or not.
    #
    # This used to run only when a layout declared nothing, which was fine while
    # a layout either declared its whole heater layer or none of it. It stopped
    # being fine the moment a drawing could declare ONE circuit and not another:
    # the 6G3, 6G4, AB763 and AB763 Super sheets draw their 5 V rectifier
    # winding lead by lead but only ARROW their 6.3 V chain ("to all 6.3 volt
    # heaters"), so those four declare the one and not the other. Surveying only
    # undeclared layouts would have dropped twelve centre-tapped sockets out of
    # reference/heaters.yaml the moment the 5 V circuits landed - the worklist
    # quietly shrinking because a DIFFERENT circuit on the same board got read.
    # A worklist that misstates the size of its own job is worse than none.
    #
    # Sockets a circuit does declare are skipped: those are proved below.
    ct = []
    for sid in sorted(R.off_by_id):
        it = R.off_by_id[sid]
        if it.get("kind") != "tube" or sid in R._heater_decl:
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

    # Same-socket links, classified against the valve's own sheet. These are
    # findings, not failures: the gate cannot fix a drawing whose source has
    # not been read, but it can refuse to let one sit here unnamed. (Straps
    # inside a declared circuit are proved below and never appear here.)
    strap_notes = []
    for sid, a, b, kind, detail in R.heater_strap_findings():
        res.straps.append((sid, a, b, kind, detail))
        if kind == "shorted":
            strap_notes.append(
                f"  FINDING - SHORTS THE SUPPLY: the drawing links {sid} "
                f"pin {a} to pin {b}, and {detail}. Needs a read of this "
                f"amplifier's own sheet before it can be corrected.")
        else:
            strap_notes.append(
                f"  FINDING - needs a source read: the drawing links {sid} "
                f"pin {a} to pin {b}; {detail}.")

    def report_unestablished(headline: str):
        res.notes.append(headline)
        for line in ct:
            res.notes.append(f"  centre-tapped socket {line}")
        if not ct:
            res.notes.append("  no centre-tapped socket on the heater chain")
        res.notes.extend(strap_notes)

    if not circuits:
        # Not a failure - an undeclared heater layer is an UNVERIFIED one, and
        # saying so is the point. The sockets that matter are the centre-tapped
        # ones, because those are exactly where the drawing cannot be read off
        # the pin labels: print what each one's own runs land on, and what that
        # grouping would mean, so the report is a worklist and not a shrug.
        unsourced = str(layout.get("heaters_unsourced", "") or "").strip()
        res.pending = str(layout.get("heaters_pending", "") or "").strip()
        report_unestablished(
            f"heaters NOT DECLARED - {twisted} heater run(s). Not checked; this "
            f"drawing claims only what its own runs name."
            + ("  NO FACTORY LAYOUT SHEET EXISTS for this amplifier, so these "
               "sockets are not waiting on a reader: " + unsourced
               if unsourced else "")
            + ("  READ PENDING: " + res.pending if res.pending else ""))
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
        if grounded not in ("feed", "return", "none", "humdinger", "winding-ct"):
            res.errors.append(
                f"{tag}: grounded_leg must be feed | return | none | humdinger "
                f"| winding-ct, got {circuit.get('grounded_leg')!r}")
            continue
        # `winding-ct` - both legs float and the WINDING'S OWN centre tap is
        # grounded: the blackface arrangement (green-yellow tied to the
        # red-yellow HT centre tap and taken to chassis). "Neither leg is
        # grounded" is again not the whole claim - it is also what a floating
        # pair with no return looks like - so the circuit NAMES the lead, and
        # the named lead is checked: a transformer lead of this board, drawn,
        # and reaching the ground bus.
        winding_ct = circuit.get("winding_ct")
        if grounded == "winding-ct" and not winding_ct:
            res.errors.append(
                f"{tag}: grounded_leg: winding-ct must name the transformer's "
                f"centre-tap lead that reaches ground, as "
                f"`winding_ct: TR1.green-yellow`")
            continue
        if grounded != "winding-ct" and winding_ct:
            res.errors.append(
                f"{tag}: names winding_ct {winding_ct!r} but grounded_leg is "
                f"{grounded!r} - only a `winding-ct` circuit has one")
            continue
        if winding_ct:
            winding_ct = str(winding_ct)
            xf, _, lead = winding_ct.partition(".")
            xf_it = R.off_by_id.get(xf)
            if not lead or xf_it is None or xf_it.get("kind") not in ("xfmr", "choke"):
                res.errors.append(
                    f"{tag}: winding_ct must name a transformer lead of this "
                    f"board (`<xfmr id>.<lead>`), got {winding_ct!r}")
                continue
        # `humdinger` - the supply floats and an ARTIFICIAL CENTRE TAP carries
        # the return: a hum-balance pot across the two legs with its wiper to
        # chassis, or a pair of fixed resistors doing the same job. Neither leg
        # is grounded (so W3 treats it as `none`), but "neither leg is grounded"
        # is not the whole claim, and a circuit that stopped there would be
        # indistinguishable from a supply whose return nobody drew. So the
        # declaration NAMES the part, and the named part is checked: it is on
        # this board, it reaches ground, and its terminals span BOTH legs.
        humdinger = circuit.get("humdinger")
        hum_refs = ([humdinger] if isinstance(humdinger, str)
                    else [str(x) for x in (humdinger or [])])
        if grounded == "humdinger" and not hum_refs:
            res.errors.append(
                f"{tag}: grounded_leg: humdinger must name the part that "
                f"reaches ground, as `humdinger: VR9` or `humdinger: [R40, R41]`")
            continue
        if grounded != "humdinger" and hum_refs:
            res.errors.append(
                f"{tag}: names humdinger {hum_refs} but grounded_leg is "
                f"{grounded!r} - only a `humdinger` circuit has one")
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

            # D1 - declared pins are heater terminals of this valve. The set is
            # the basing labels UNIONED with the valve's own declared supplies,
            # so a pin that carries the heater and something else (a rectifier
            # whose cathode is strapped to a heater pin) still counts.
            heater_pins = load_tube_heater_pins(slug) or set()
            stray = sorted(p for leg in legs for p in leg if p not in heater_pins)
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
        want_gnd = {"feed": 0, "return": 1, "none": -1, "humdinger": -1,
                    "winding-ct": -1}[grounded]
        gnd_root = LG.net(GND) if GND in LG.uf.parent else None
        if grounded == "winding-ct":
            # The named centre-tap lead is a claim like any other: drawn on
            # this board, and reaching the ground bus. (Both legs staying off
            # the bus is proved below with the other grounded_leg values.)
            if winding_ct not in LG.uf.parent:
                res.errors.append(
                    f"{tag}: the winding centre tap {winding_ct} is declared "
                    f"grounded, but no drawn conductor leaves that lead")
            elif gnd_root is None or LG.net(winding_ct) != gnd_root:
                res.errors.append(
                    f"{tag}: the winding centre tap {winding_ct} is drawn but "
                    f"does not reach the ground bus - a centre tap grounded "
                    f"nowhere leaves the supply floating")
        if grounded == "humdinger":
            # Every terminal the named part(s) put on the drawing.
            terms = [t for t in LG.uf.parent
                     if any(t.startswith(f"{r}.") for r in hum_refs)]
            if not terms:
                res.errors.append(
                    f"{tag}: the humdinger {hum_refs} is declared as this "
                    f"circuit's return, but no drawn conductor reaches it")
            elif gnd_root is None or not any(LG.net(t) == gnd_root for t in terms):
                res.errors.append(
                    f"{tag}: the humdinger {hum_refs} does not reach the ground "
                    f"bus - a floating supply with a floating hum balance has "
                    f"no return at all")
            else:
                # An artificial centre tap sits ACROSS the supply. A grounded
                # part touching one leg (or neither) is not one, and saying so
                # is the whole point of naming it.
                touched = {k for k in (0, 1)
                           if any(LG.net(t) in nets[k] for t in terms)}
                if touched != {0, 1}:
                    missed = ", ".join(("feed", "return")[k]
                                       for k in (0, 1) if k not in touched)
                    res.errors.append(
                        f"{tag}: the humdinger {hum_refs} does not reach the "
                        f"{missed} leg - an artificial centre tap has to span "
                        f"BOTH legs to be one")
        for k, name in ((0, "feed"), (1, "return")):
            on_gnd = gnd_root is not None and gnd_root in nets[k]
            if k == want_gnd and not on_gnd:
                res.errors.append(
                    f"{tag}: the {name} leg is declared grounded but no drawn "
                    f"conductor takes it to the ground bus")
            if k != want_gnd and on_gnd:
                res.errors.append(
                    f"{tag}: the {name} leg reaches the ground bus, but this "
                    f"circuit {_grounding_says(grounded, hum_refs, winding_ct)}")

        # ---- W4: the pilot lamp sits ACROSS the two legs ------------------
        _check_pilot_lamps(res, R, LG, tag, cid, circuit, grounded, want_gnd,
                           nets, gnd_root, hum_refs, winding_ct, verbose)
        if verbose:
            res.notes.append(f"  {cid}: {volts:g} V, grounded leg = {grounded}; "
                             f"feed net {sorted(nets[0])} / return net {sorted(nets[1])}")

    # A PARTIAL DECLARATION IS SAID OUT LOUD. Proving one circuit says nothing
    # about a socket no circuit names, and a report that fell silent about the
    # rest would read as coverage. Same rule as the drawing's own footer marker
    # (render_layouts.heater_provenance_note).
    if ct or res.straps:
        declared_v = sorted({c["volts"] for c in R._heater_decl.values()})
        report_unestablished(
            f"heaters PARTLY DECLARED - the "
            f"{' and '.join(f'{v:g} V' for v in declared_v)} circuit(s) above are "
            f"checked; the rest of this drawing's heater layer is NOT.")
    return res


def _grounding_says(grounded: str, hum_refs, winding_ct) -> str:
    """How a circuit's declaration describes its return, for a message that
    contrasts what the drawing does with what the declaration says."""
    if grounded == "humdinger":
        return f"floats both legs and returns through the humdinger {hum_refs}"
    if grounded == "winding-ct":
        return (f"floats both legs and grounds the winding's own centre tap "
                f"({winding_ct})")
    if grounded == "none":
        return "grounds neither leg"
    return f"grounds the {grounded} leg"


def _check_pilot_lamps(res, R, LG, tag, cid, circuit, grounded, want_gnd,
                       nets, gnd_root, hum_refs, winding_ct, verbose) -> None:
    """W4 - a pilot lamp on this circuit has both terminals reached, one on
    each leg. Every other check passes a lamp whose two terminals sit on ONE
    leg: W1 sees every declared socket pin reached, W2 sees the legs apart, W3
    sees the right leg grounded - and the lamp is dark. So the lamp is proved
    on its own terms: it is a two-terminal part, and a two-terminal part is
    lit by the voltage BETWEEN its terminals.

    "On a leg" is membership of that leg's net; on a single-ended supply the
    grounded leg's net is the ground bus, so a lamp terminal drawn to chassis
    is on that leg. A terminal on a net that carries neither leg is a lamp
    drawn in series with the chain (the fault the 5E3 shipped) or a return
    drawn to nowhere.

    The escape, `pilot: { PL1: { return: chassis } }`, exists because several
    factory sheets draw the lamp with ONE terminal - the feed arriving and the
    chain leaving on it - the holder's shell being the return, which those
    sheets do not draw and this board therefore does not draw either. It is a
    declaration and is checked as one: only on a circuit that grounds a leg
    (a lamp from one leg to chassis on a floating pair sits across half a
    winding), the one drawn terminal on the FED leg, the other terminal drawn
    to nothing - a declared-undrawn return that the board then draws anyway is
    a stale declaration and fails too.

    A lamp that touches no leg of this circuit is not this circuit's lamp (a
    mains-side neon, a lamp on another winding) and is left to whichever
    circuit it does touch."""
    legname = ("feed", "return")
    pilot = circuit.get("pilot") or {}
    if not isinstance(pilot, dict):
        res.errors.append(f"{tag}: pilot must map a lamp id to "
                          f"{{return: chassis, source: ...}}")
        pilot = {}
    lamps = [it for it in R.offboard
             if it.get("kind") == "part" and it.get("glyph") == "lamp"]
    lamp_ids = {str(it.get("id")) for it in lamps}
    for lid in sorted(pilot):
        if str(lid) not in lamp_ids:
            res.errors.append(
                f"{tag}: pilot names {lid}, which is not a pilot-lamp glyph "
                f"on this board")

    def leg_of(term):
        """0/1 = on that leg's net; 'off' = reached, on neither leg;
        None = no drawn conductor reaches it."""
        if term not in LG.uf.parent:
            return None
        root = LG.net(term)
        on = [k for k in (0, 1) if root in nets[k]]
        if len(on) == 2:
            return "both"          # W2 has already reported the bridge
        return on[0] if on else "off"

    for it in lamps:
        lid = str(it.get("id"))
        terms = [f"{lid}.a", f"{lid}.b"]
        where = {t: leg_of(t) for t in terms}
        esc = pilot.get(lid)
        touches = any(w in (0, 1, "both") for w in where.values())
        if esc is None and not touches:
            continue
        if any(w == "both" for w in where.values()):
            continue                # the bridge is the finding, not the lamp
        if esc is not None:
            ret = str((esc or {}).get("return", "")).lower() \
                if isinstance(esc, dict) else ""
            if ret != "chassis":
                res.errors.append(
                    f"{tag}: pilot.{lid}.return must be `chassis` (the only "
                    f"undrawn return a sheet shows), got {ret!r}")
                continue
            if grounded not in ("feed", "return"):
                res.errors.append(
                    f"{tag}: W4 pilot {lid} declares its return at the chassis, "
                    f"but this circuit {_grounding_says(grounded, hum_refs, winding_ct)} "
                    f"- a lamp from one leg to chassis on a floating supply sits "
                    f"across half the winding, not across it")
                continue
            hot = 1 - want_gnd
            reached = [t for t in terms if where[t] is not None]
            if len(reached) == 2:
                res.errors.append(
                    f"{tag}: W4 pilot {lid} declares its return at the chassis "
                    f"as UNDRAWN, but the drawing wires both {terms[0]} and "
                    f"{terms[1]} - a stale declaration; drop it or the run")
            elif not reached:
                res.errors.append(
                    f"{tag}: W4 DARK LAMP - no drawn conductor reaches {lid} at "
                    f"all; a chassis return still needs the feed drawn")
            elif where[reached[0]] != hot:
                res.errors.append(
                    f"{tag}: W4 DARK LAMP - {reached[0]} is the lamp's one drawn "
                    f"terminal and it is not on the {legname[hot]} leg (the fed "
                    f"one); with its return at the chassis the lamp must take "
                    f"its feed from the ungrounded leg")
            else:
                how = (f"{reached[0]} on the {legname[hot]} leg, return at the "
                       f"chassis (declared, undrawn: {str(esc.get('source', '')).strip() or 'no source given'})")
                res.lamps.append((cid, lid, how))
                if verbose:
                    res.notes.append(f"  {cid}: pilot {lid} - {how}")
            continue
        # No escape: both terminals drawn, one on each leg.
        unreached = [t for t in terms if where[t] is None]
        if unreached:
            res.errors.append(
                f"{tag}: W4 DARK LAMP - {unreached[0]} is reached by no drawn "
                f"conductor; a pilot lamp sits across the supply's two legs. "
                f"(Where the sheet draws the lamp with one terminal and its "
                f"return is the holder's shell, declare `pilot: {{{lid}: "
                f"{{return: chassis, source: ...}}}}`.)")
            continue
        off = [t for t in terms if where[t] == "off"]
        if off:
            t = off[0]
            if gnd_root is not None and LG.net(t) == gnd_root:
                res.errors.append(
                    f"{tag}: W4 DARK LAMP - {t} returns to the chassis, but this "
                    f"circuit {_grounding_says(grounded, hum_refs, winding_ct)}; "
                    f"a lamp from one leg to chassis on a floating supply sits "
                    f"across half the winding, not across it")
            else:
                res.errors.append(
                    f"{tag}: W4 DARK LAMP - {t} is on a net that carries neither "
                    f"supply leg: the lamp is drawn IN SERIES with the chain "
                    f"(its other terminal feeds the heaters) or its return "
                    f"goes nowhere")
            continue
        if where[terms[0]] == where[terms[1]]:
            res.errors.append(
                f"{tag}: W4 DARK LAMP - both terminals of {lid} are on the "
                f"{legname[where[terms[0]]]} leg; a lamp across one leg sees "
                f"no voltage")
            continue
        how = (f"{terms[0]} on the {legname[where[terms[0]]]} leg, {terms[1]} "
               f"on the {legname[where[terms[1]]]} leg")
        res.lamps.append((cid, lid, how))
        if verbose:
            res.notes.append(f"  {cid}: pilot {lid} - {how}")


# ---------------------------------------------------------------------------
# T1 - a tube file's declared supplies must agree with its own basing
# ---------------------------------------------------------------------------
def _check_one_tube_file(path, root) -> list[str]:
    """T1 for a single reference/tubes/<slug>.yaml."""
    errs: list[str] = []
    data = yaml.safe_load(path.read_text()) or {}
    supplies = (data.get("heater") or {}).get("supplies") or []
    if not supplies:
        return errs
    basing = ((data.get("basing") or {}).get("pins") or {})
    heater_pins, elements = set(), {}
    for k, meta in basing.items():
        elem = str((meta or {}).get("element", "")).lower()
        elements[int(k)] = elem
        if elem in HEATER_ELEMENTS:
            heater_pins.add(int(k))
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path.name
    if not heater_pins:
        return [f"{rel}: declares heater.supplies but its basing names no "
                f"heater/filament pin"]
    # A pin may carry a heater end AND something the basing letters instead,
    # because the basing element is what the DC netlist must see: the GZ34's
    # pin 8 is the heater's other end strapped to the cathode, and the rectified
    # B+ leaves on it. Such a pin is DECLARED, with the element it is lettered
    # as, so the exception is reviewed rather than guessed.
    shared = {int(k): str(v).lower() for k, v
              in ((data.get("heater") or {}).get("shared_pins") or {}).items()}
    for pin, elem in sorted(shared.items()):
        if pin not in elements:
            errs.append(f"{rel}: heater.shared_pins names pin {pin}, which is "
                        f"not on this valve's basing")
        elif elements[pin] != elem:
            errs.append(f"{rel}: heater.shared_pins says pin {pin} is '{elem}', "
                        f"but the basing letters it '{elements[pin]}'")
    used = {int(x) for sup in supplies for leg in (sup.get("legs") or [])
            for x in leg}
    for pin in sorted(set(shared) - used):
        errs.append(f"{rel}: heater.shared_pins declares pin {pin}, which no "
                    f"supply leg uses — an exception nothing needs")
    for sup in supplies:
        volts = sup.get("volts")
        legs = [[int(x) for x in leg] for leg in (sup.get("legs") or [])]
        unused = {int(x) for x in (sup.get("unused") or [])}
        if len(legs) != 2 or not all(legs):
            errs.append(f"{rel}: the {volts} V supply must have two non-empty "
                        f"legs, got {legs}")
            continue
        named = set(legs[0]) | set(legs[1])
        stray = sorted((named | unused) - heater_pins - set(shared))
        if stray:
            lettered = ", ".join(f"pin {x} is {elements.get(x, 'not on this basing')}"
                                 for x in stray)
            errs.append(f"{rel}: the {volts} V supply names pin(s) {stray}, which "
                        f"are not heater pins of this valve ({lettered})")
        both = sorted(set(legs[0]) & set(legs[1]))
        if both:
            errs.append(f"{rel}: the {volts} V supply puts pin(s) {both} on both legs")
        missing = sorted(heater_pins - named - unused)
        if missing:
            errs.append(f"{rel}: the {volts} V supply accounts for heater pin(s) "
                        f"{missing} on neither leg nor `unused`")
    return errs


def check_tube_supplies(slugs: list[str] | None = None) -> list[str]:
    """Every `heater.supplies` leg must name heater-class pins of that valve's
    own basing, and between them the legs plus `unused` must account for all of
    them. A datasheet citation proves the VOLTAGE; nothing but this proves the
    pin list was typed correctly, and a wrong leg here would be believed by
    every layout that declares against it."""
    errs: list[str] = []
    for path in sorted((ROOT / "reference" / "tubes").glob("*.yaml")):
        if slugs and path.stem not in slugs:
            continue
        errs += _check_one_tube_file(path, ROOT)
    return errs


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
# A LAYOUT CAN BE PART-WAY. `declared` says a layout states at least one heater
# circuit; `fully_established` says nothing is left over. They differ, and the
# difference is the point: the 6G3, 6G4, AB763 and AB763 Super sheets draw their
# 5 V rectifier-filament winding lead by lead but only ARROW their 6.3 V chain
# ("to all 6.3 volt heaters"), so each of those declares its 5 V circuit, has it
# proved, and still carries centre-tapped preamp sockets nothing has
# established. Both halves are recorded on every entry; read `fully_established`
# for the size of the job, never `declared`.
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
# re-export. The count in `summary` is the size of the job. An entry carrying
# `read_pending_because` has a factory sheet that no located copy resolves;
# the string says which copies were tried, so the next attempt starts there.
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
        # BOTH HALVES, ALWAYS. `declared` is no longer all-or-nothing: a layout
        # can prove its 5 V rectifier winding off a sheet that only arrows its
        # 6.3 V chain, and then it has circuits AND unestablished sockets. The
        # worklist has to carry both, or reading one field would understate the
        # job — the entry would look cleared because a different circuit on the
        # same board got read.
        entry: dict = {"declared": bool(res.declared)}
        if res.declared:
            entry["circuits"] = [
                {"id": str(c.get("id", "")), "volts": float(c.get("volts", 0)),
                 "grounded_leg": str(c.get("grounded_leg", "")),
                 "sockets": {str(k): {"feed": [int(p) for p in (v or {}).get("feed", [])],
                                      "return": [int(p) for p in (v or {}).get("return", [])]}
                             for k, v in (c.get("sockets") or {}).items()}}
                for c in (layout.get("heaters") or [])]
        entry["fully_established"] = bool(res.fully_declared)
        # WHICH KIND OF GAP. Some amplifiers have no factory board-layout sheet
        # at all — the board is derived from the circuit drawing — so their
        # sockets can never be cleared by a better scan. Counting those with the
        # unread ones would overstate the job and misdirect the reading effort.
        unsourced = str(layout.get("heaters_unsourced", "") or "").strip()
        if unsourced and not entry["fully_established"]:
            entry["no_factory_layout_sheet"] = unsourced
        # A THIRD KIND OF GAP: a factory sheet exists but no copy found so far
        # resolves the socket pins. Recorded so the next reader starts from
        # what was tried, not from the vague backlog again.
        pending = str(layout.get("heaters_pending", "") or "").strip()
        if pending and not entry["fully_established"]:
            entry["read_pending_because"] = pending
        entry["centre_tapped_sockets"] = {
            sid: {"tube": d["tube"], "drawn_on_pins": list(d["names"]),
                  "grouping": ("opposite-legs" if d["opposite"] else "not-drawn-as-a-pair"),
                  "reading": d["reading"]}
            for sid, d in sorted(res.doubtful.items())}
        entry["findings"] = [
            {"socket": sid, "pins": [a, b], "kind": kind, "detail": detail}
            for sid, a, b, kind, detail in res.straps]
        amps[amp_id] = entry
    def _doubt(entry) -> int:
        return sum(1 for sock in (entry.get("centre_tapped_sockets") or {}).values()
                   if sock["grouping"] == "opposite-legs")

    n_doubt = sum(_doubt(a) for a in amps.values())
    n_doubt_nosheet = sum(_doubt(a) for a in amps.values()
                          if a.get("no_factory_layout_sheet"))
    findings = [f for a in amps.values() for f in (a.get("findings") or [])]
    return {
        "summary": {
            "layouts": len(amps),
            "declared_and_checked": sum(1 for a in amps.values() if a["declared"]),
            # The number that actually measures the job: a layout with NOTHING
            # left unestablished. `declared_and_checked` counts a layout that
            # declares one circuit of two, so on its own it would overstate.
            "fully_established": sum(1 for a in amps.values()
                                     if a["fully_established"]),
            "not_established": sum(1 for a in amps.values() if not a["declared"]),
            "doubtful_sockets": n_doubt,
            # Of those, the ones on amplifiers with no factory board-layout
            # sheet: they are not waiting on a reader, and no scan will clear
            # them. Everything else is work a source read finishes.
            "doubtful_sockets_no_factory_sheet": n_doubt_nosheet,
            "doubtful_sockets_pending_a_read": n_doubt - n_doubt_nosheet,
            "layouts_with_no_factory_layout_sheet": sum(
                1 for a in amps.values() if a.get("no_factory_layout_sheet")),
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
def _plant_humdinger(m: dict, pid: str = "RHUM", at: float = 15) -> None:
    """Put a hum-balance part on the mutated layout so the humdinger cases test
    the rule and not a missing endpoint. An off-board `kind: part` carrying a
    `value:` needs no bom entry, so the fixture stays inside the test."""
    m.setdefault("offboard", []).append(
        {"id": pid, "kind": "part", "edge": "bottom", "at": at,
         "label": "Hum balance", "value": "100 Ω"})


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
        # D1 reads the basing labels UNIONED with the valve's declared
        # supplies, so that a rectifier pin carrying both the heater and the
        # cathode counts as a heater pin. That union must not have widened into
        # "any pin will do": a diode plate is still not a heater terminal.
        ("D1 union not a blank cheque",
         "the rectifier's 5 V winding is declared on a diode plate",
         lambda m: m["heaters"][1]["sockets"].__setitem__(
             "V3", {"feed": [2], "return": [4]})),
        ("W3 grounded leg not grounded",
         "the circuit claims a floating supply while the drawing grounds a leg",
         lambda m: m["heaters"][0].__setitem__("grounded_leg", "none")),
        ("D2 pin on both legs",
         "one pin is declared on both supply legs",
         lambda m: sockets(m).__setitem__("V1", {"feed": [4, 5], "return": [5, 9]})),
        # A SHORT ACROSS A FILAMENT IS A SHORT WHATEVER COLOUR IT IS DRAWN IN.
        # The 6G2 shipped a plain conductor from its rectifier's pin 2 to pin 8
        # — straight across the 5 V winding — and neither gate objected: this
        # one looked only at heater-styled runs, and the DC gate excludes the
        # rectifier socket by rule. heater_strap_findings() is style-blind now,
        # and W2 catches it once the circuit is declared. Both halves planted.
        ("W2 plain run shorts a filament",
         "an UNCOLOURED conductor is drawn across the 5Y3GT's two filament "
         "pins — the fault the 6G2 shipped",
         lambda m: m["runs"].append({"from": "V3.pin2", "to": "V3.pin8"})),
        # `grounded_leg: humdinger` - a floating pair whose return is an
        # ARTIFICIAL centre tap (a hum-balance pot across the legs, wiper to
        # chassis; or a pair of fixed resistors). Planted on h5, the 5Y3GT's
        # 5 V winding, because that circuit genuinely floats - so each case
        # fails on the humdinger rule under test and not on W3 first.
        ("humdinger must name its part",
         "a floating supply claims an artificial centre tap without naming it",
         lambda m: m["heaters"][1].__setitem__("grounded_leg", "humdinger")),
        ("humdinger must be drawn",
         "the named hum-balance part is nowhere on the drawing",
         lambda m: (m["heaters"][1].__setitem__("grounded_leg", "humdinger"),
                    m["heaters"][1].__setitem__("humdinger", "RHUM"))),
        ("humdinger must span both legs",
         "the named part reaches ground but touches only one of the two legs",
         lambda m: (m["heaters"][1].__setitem__("grounded_leg", "humdinger"),
                    m["heaters"][1].__setitem__("humdinger", "RHUM"),
                    _plant_humdinger(m),
                    m["runs"].append({"from": "V3.pin2", "to": "RHUM.a"}),
                    m["runs"].append({"from": "RHUM.b", "to": [1.45, 3.0]}))),
        ("humdinger must reach ground",
         "the named part spans both legs but never reaches the chassis",
         lambda m: (m["heaters"][1].__setitem__("grounded_leg", "humdinger"),
                    m["heaters"][1].__setitem__("humdinger", "RHUM"),
                    _plant_humdinger(m),
                    m["runs"].append({"from": "V3.pin2", "to": "RHUM.a"}),
                    m["runs"].append({"from": "V3.pin8", "to": "RHUM.b"}))),
    ]
    # ---- `winding-ct` and W4 (2026-09-10) ----------------------------------
    # The 5F1's transformer has no centre-tap lead and its sheet draws the
    # lamp with one terminal; the fixtures below give the layout what each
    # rule needs so that every case fails on the rule under test and not on a
    # missing endpoint. A transformer lead is a run endpoint like any other,
    # so a lead the layout never names comes into being by drawing it.
    def plant_ct(m, to=None):
        m["runs"].append({"from": "PT.green-yellow", "to": to or [1.45, 3.0]})

    def h5_winding_ct(m, lead="PT.green-yellow"):
        m["heaters"][1]["grounded_leg"] = "winding-ct"
        m["heaters"][1]["winding_ct"] = lead

    def drop_escape(m):
        m["heaters"][0].pop("pilot", None)

    def repoint(m, frm, to, new_frm, new_to):
        for r in m["runs"]:
            if r.get("from") == frm and r.get("to") == to:
                r["from"], r["to"] = new_frm, new_to
                return
        raise AssertionError(f"selftest fixture: no run {frm} -> {to}")

    cases += [
        ("winding-ct names no lead",
         "a circuit claims a grounded winding centre tap without naming the lead",
         lambda m: m["heaters"][1].__setitem__("grounded_leg", "winding-ct"),
         "must name the transformer's centre-tap lead"),
        ("winding-ct lead not drawn",
         "the named centre-tap lead is nowhere on the drawing",
         lambda m: h5_winding_ct(m),
         "no drawn conductor leaves that lead"),
        ("winding-ct lead off ground",
         "the named centre-tap lead is drawn, to a bare eyelet off the bus",
         lambda m: (h5_winding_ct(m), plant_ct(m, [0.5, 3.0])),
         "does not reach the ground bus"),
        ("winding-ct not a xfmr lead",
         "the centre tap is named on a socket pin",
         lambda m: h5_winding_ct(m, "V3.pin2"),
         "must name a transformer lead"),
        ("winding-ct but leg grounded",
         "the 6.3 V circuit claims a grounded centre tap while the drawing "
         "still grounds its return leg",
         lambda m: (m["heaters"][0].__setitem__("grounded_leg", "winding-ct"),
                    m["heaters"][0].__setitem__("winding_ct", "PT.green-yellow"),
                    plant_ct(m)),
         "grounds the winding's own centre tap"),
        ("W4 lamp across one leg",
         "the lamp's second terminal is drawn to the SAME leg as its first",
         lambda m: (drop_escape(m),
                    m["runs"].append({"from": "PL1.b", "to": "V2.pin7",
                                      "style": "heater"})),
         "both terminals of PL1 are on the feed leg"),
        ("W4 lamp return undrawn",
         "one lamp terminal is drawn to nothing and no chassis return is declared",
         lambda m: drop_escape(m),
         "reached by no drawn conductor"),
        ("W4 lamp in series",
         "the feed enters one lamp terminal and the chain leaves the OTHER "
         "- the fault the 5E3 shipped",
         lambda m: (drop_escape(m),
                    repoint(m, "PL1.a", "V2.pin7", "PL1.b", "V2.pin7")),
         "IN SERIES"),
        ("W4 lamp across the return",
         "both lamp terminals are drawn to the chassis",
         lambda m: (drop_escape(m),
                    repoint(m, "PT.green2", "PL1.a", "PT.green2", "V2.pin7"),
                    repoint(m, "PL1.a", "V2.pin7", "PL1.a", [1.45, 3.0]),
                    m["runs"].append({"from": "PL1.b", "to": [1.45, 3.4]})),
         "both terminals of PL1 are on the return leg"),
        ("W4 escape on floating supply",
         "a chassis return is declared on a circuit that grounds no leg",
         lambda m: m["heaters"][1].__setitem__("pilot", m["heaters"][0].pop("pilot")),
         "grounds neither leg"),
        ("W4 escape but return drawn",
         "the return is declared undrawn and the drawing wires it anyway",
         lambda m: m["runs"].append({"from": "PL1.b", "to": [1.45, 3.0],
                                     "style": "heater"}),
         "stale declaration"),
        ("W4 escape names no lamp",
         "the declaration names a lamp the board does not have",
         lambda m: m["heaters"][0].__setitem__(
             "pilot", {"PLX": {"return": "chassis"}}),
         "not a pilot-lamp glyph"),
        ("W4 escape, feed on ground",
         "with the return declared at the chassis, the one drawn terminal is "
         "itself on the grounded leg",
         lambda m: (repoint(m, "PT.green2", "PL1.a", "PT.green2", "V2.pin7"),
                    repoint(m, "PL1.a", "V2.pin7", "PL1.a", [1.45, 3.0])),
         "not on the feed leg"),
    ]
    for case in cases:
        hole, label, fn = case[:3]
        expect = case[3] if len(case) > 3 else None
        res = check_layout(amp, _mutate(layout, fn), bom)
        hit = [e for e in res.errors if expect is None or expect in e]
        if hit:
            print(f"  ok   {hole:<26} CAUGHT  ({label})")
            print(f"         -> {hit[0]}")
        else:
            fails += 1
            print(f"  FAIL {hole:<26} ESCAPED ({label})"
                  + (f" - expected {expect!r}" if expect else ""))
            for e in res.errors[:3]:
                print(f"         got: {e}")

    # A RULE THAT ONLY REJECTS IS USELESS. The point of `humdinger` is to make
    # a floating pair with an artificial centre tap DECLARABLE, so the positive
    # path is proved too: part across both legs, wiper to chassis, PASSES.
    def good_humdinger(m):
        # The real arrangement: a resistor from EACH leg to chassis. A part is
        # not a short in the layout graph, so the legs themselves stay off
        # ground — which is exactly the physical claim, and exactly what W3
        # still demands.
        m["heaters"][1]["grounded_leg"] = "humdinger"
        m["heaters"][1]["humdinger"] = ["RH1", "RH2"]
        _plant_humdinger(m, "RH1", 14)
        _plant_humdinger(m, "RH2", 16)
        m["runs"] += [{"from": "V3.pin2", "to": "RH1.a"},
                      {"from": "RH1.b", "to": [1.45, 3.0]},
                      {"from": "V3.pin8", "to": "RH2.a"},
                      {"from": "RH2.b", "to": [1.45, 3.4]}]
    res = check_layout(amp, _mutate(layout, good_humdinger), bom)
    if res.ok and res.declared:
        print(f"  ok   {'humdinger DECLARABLE':<22} a hum-balance part across "
              f"both legs with a chassis return PASSES")
    else:
        fails += 1
        print(f"  FAIL {'humdinger DECLARABLE':<22} a correct artificial centre "
              f"tap was rejected:")
        for e in res.errors:
            print(f"         {e}")

    # A GROUNDED WINDING CENTRE TAP IS DECLARABLE: name the lead, draw it to
    # the bus, keep both legs off it - PASSES.
    def good_winding_ct(m):
        h5_winding_ct(m)
        plant_ct(m)
    res = check_layout(amp, _mutate(layout, good_winding_ct), bom)
    if res.ok and res.declared:
        print(f"  ok   {'winding-ct DECLARABLE':<26} a named centre-tap lead drawn "
              f"to the bus, both legs floating, PASSES")
    else:
        fails += 1
        print(f"  FAIL {'winding-ct DECLARABLE':<26} a correct grounded centre tap "
              f"was rejected:")
        for e in res.errors:
            print(f"         {e}")

    # W4 LOOKED AT THE LAMP. A PASS that never examined the lamp would prove
    # nothing, so the positive record is asserted: the baseline's declared
    # chassis return, and a lamp DRAWN across both legs.
    seen = [l for l in base.lamps if l[1] == "PL1" and "chassis" in l[2]]
    if seen:
        print(f"  ok   {'W4 lamp seen (declared)':<26} {seen[0][2][:70]}...")
    else:
        fails += 1
        print(f"  FAIL {'W4 lamp seen (declared)':<26} the baseline's lamp was "
              f"not examined: {base.lamps!r}")

    def drawn_return(m):
        drop_escape(m)
        m["runs"].append({"from": "PL1.b", "to": [1.45, 3.0], "style": "heater"})
    res = check_layout(amp, _mutate(layout, drawn_return), bom)
    seen = [l for l in res.lamps if l[1] == "PL1" and "PL1.b on the return leg" in l[2]]
    if res.ok and seen:
        print(f"  ok   {'W4 lamp DRAWN across':<26} feed on one terminal, chassis "
              f"on the other, PASSES: {seen[0][2]}")
    else:
        fails += 1
        print(f"  FAIL {'W4 lamp DRAWN across':<26} a lamp drawn across both legs "
              f"was rejected or not seen: {res.errors[:2]!r} {res.lamps!r}")

    # THE PARTIAL-DECLARATION MARKER. A layout that declares SOME of its heater
    # layer must keep the "not established" markers for the rest — the legend
    # key and the footer line — or a partial claim reads as a whole one. Proved
    # on the drawing itself, because that is where the claim is made: strip the
    # 5F1's 6.3 V circuit, leaving only the rectifier's 5 V one declared, and
    # its 12AX7 must still be named as unestablished.
    def half_declare(m):
        m["heaters"].pop(0)                      # drop the 6.3 V circuit
        # ...and take away the 12AX7's centre-tap return, so its heater runs
        # name only pins 4 and 5 — the drawing then shows the two heater pins
        # on opposite legs, which is precisely the state the marker exists to
        # report. (With pin 9 still drawn there is nothing doubtful about it.)
        m["runs"] = [r for r in m["runs"] if "V1.pin9" not in (r.get("from"), r.get("to"))]

    half = _mutate(layout, half_declare)
    R = Renderer(half, bom, amp)
    note = R.heater_provenance_note()
    caveat = R._heater_legend_caveat()
    if (not R.heater_fully_declared and "V1" in note
            and "5 V" in note and "not established" in caveat):
        print(f"  ok   {'PARTIAL marker kept':<22} declaring one circuit of two "
              f"leaves the other's marker on the drawing")
        print(f"         -> {note[:96]}...")
    else:
        fails += 1
        print(f"  FAIL {'PARTIAL marker kept':<22} a half-declared layout lost "
              f"its marker: note={note!r} caveat={caveat!r}")

    # T1 - the tube-file pin-agreement check, planted in a copy of a real file
    import tempfile
    tube = yaml.safe_load((ROOT / "reference" / "tubes" / "12ax7.yaml").read_text())
    tube["heater"]["supplies"][0]["legs"] = [[4, 5], [3]]      # pin 3 is a cathode
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "reference" / "tubes"
        d.mkdir(parents=True)
        (d / "12ax7.yaml").write_text(yaml.safe_dump(tube))
        errs = _check_one_tube_file(d / "12ax7.yaml", Path(tmp))
    if errs:
        print(f"  ok   {'T1 leg on a signal pin':<22} CAUGHT  (a supply leg is "
              f"declared on the 12AX7's pin 3, a cathode)")
        print(f"         -> {errs[0]}")
    else:
        fails += 1
        print(f"  FAIL {'T1 leg on a signal pin':<22} ESCAPED")
    if check_tube_supplies():
        fails += 1
        print("  FAIL T1 baseline           the corpus's own tube files do not agree "
              "with their basings")
    else:
        print(f"  ok   {'T1 BASELINE':<22} every tube file's supplies agree with its basing")

    print(f"\nselftest: {len(cases) + 8} case(s), {fails} failure(s)")
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
        tube_errs = check_tube_supplies()
        for e in tube_errs:
            print(f"FAIL {e}")
        errors += tube_errs
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
