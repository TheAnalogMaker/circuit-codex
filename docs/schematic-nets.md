# Schematic ↔ netlist equivalence — `verify_schematic_nets.py` and `sch_map.yaml`

The schematic is the artifact a visitor reads first. Until this gate existed it
was the only drawing in the repo with no connectivity proof: `check_schematics.py`
checks grammar and geometry, `validate.py` compares designator *sets*, and
`check_tonestack_wiring.py` proves one sub-network on 16 of 38 amps. Nothing
compared the drawn net structure to `netlist.cir` — so a mis-placed wire produced
a perfectly valid file that draws a different circuit, and a copy-pasted
phase-inverter mis-wire shipped on eight sheets, three of them under a verified
badge.

`pipeline/verify_schematic_nets.py` is the schematic-side twin of
`pipeline/verify_layout_nets.py` and deliberately mirrors it: build both graphs,
**solve** the mapping rather than assume it, and declare every abstraction as
reviewable data instead of burying it in code.

```
python3 pipeline/verify_schematic_nets.py            # every sheet
python3 pipeline/verify_schematic_nets.py 5e3 ab763  # named sheets
python3 pipeline/verify_schematic_nets.py --report   # + declarations + coverage
python3 pipeline/verify_schematic_nets.py --analyze 5e3   # per-node membership
python3 pipeline/verify_schematic_nets.py --selftest      # planted-fault test
python3 pipeline/verify_schematic_nets.py --strict        # fail on any finding
```

---

## What "electrically equivalent" means here

`netlist.cir` is a **DC operating-point model**. It omits the power-supply front
end (PT + rectifier + reservoir, replaced by an ideal source at the first rail),
transformer winding DCR (plate node == B+), the pot / tone / mixer control
networks, and every cap with a lead inside one of those networks. The schematic
draws the whole amp.

So a naive net-for-net match is impossible. The gate proves the schematic,
**restricted to what the netlist models**, is isomorphic to the netlist: every
modelled element's terminals on the same node, no accidental shorts, no missing
joins — and it enumerates everything outside that restriction as *not
DC-checked*, out loud, rather than trusting it in silence.

## The two graphs

**Schematic net graph** — `pipeline/sch_nets.py` `Nets`, the KiCad-6
connectivity extractor the tone-stack gate already trusts: union-find over wire
ends, on-segment T-taps (a tap connects with no dot), junction dots, global
labels tied by name, and symbol pins put through the placed symbol's
mirror-then-rotate transform. Two wires that merely cross are **not** connected.

**Netlist graph** — `verify_layout_nets.parse_netlist`, imported unchanged, so
the two gates can never disagree about what the netlist says. An `X` element's
nodes are in the subckt's declared pin order, read from `models/<tube>.inc`
(`.subckt 6V6GT P G2 G1 K`), which `_subckt_roles` turns into role → node.

## Mapping rules

| netlist | schematic | how |
|---|---|---|
| `X` tube section (`XV1A`) | symbol lettered `V1A` | by designator; role → pin number is fixed by the symbol |
| `R` / `C` / `L` | symbol of the same designator | by designator; pins `1`/`2`, **orientation unknown** |
| node `0` | the `GND` global-label net | corpus convention; a sheet with no `GND` label is a hard finding |
| everything else | — | declared in `sch_map.yaml` / reused from `layout.yaml` `net_map` |

**Tube pins are roles by construction.** Unlike the layout — where a socket pin
must be resolved through `reference/tubes/<slug>.yaml` basing and the
section ↔ triode-half assignment has to be *solved* — a schematic tube symbol is
drawn per section and its pin numbers are positional roles, fixed in
`schematic_lib.LIB` and re-emitted into every `.kicad_sch`:

| symbol | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `cx:TRIODE` | plate | grid | cathode | — |
| `cx:PENTODE` | plate | grid (G1) | screen (G2) | cathode |
| `cx:DIODE_TUBE` | plate (A) | cathode | — | — |

So `XV1A P1A G1A K1A 12AX7` binds directly: `V1A.1`→`P1A`, `V1A.2`→`G1A`,
`V1A.3`→`K1A`. No search, no half enumeration. If the drawing letters the
section differently (`XPIA` drawn as `V4A`, `XV1A` drawn as `V1`), say so in
`sch_map.symbols` — it is one line of reviewable data, not a heuristic.

**Two-terminal parts are matched UNORDERED.** A resistor's two terminals are
interchangeable, and `cx:C` carries no polarity marks — netlist node order says
nothing about pin numbers, and an electrolytic's `+` end is modelled neither on
the sheet nor in the netlist. Treating the pair as ordered would flag every part
a drawing happens to letter the other way up. The orientation is instead
resolved by **constraint propagation** from the anchors to one globally
consistent whole, exactly as on the layout side. *If polarity is ever drawn on
electrolytics, this is the assumption to revisit.* The one polarity the sheets
*do* draw, a diode's, is checked on its own; see
[Rectifier polarity](#rectifier-polarity).

**Pots, cans and windings need an explicit terminal pick.** A netlist `R`/`C`
binds without ceremony only to a genuine two-lead passive
(`cx:R`, `cx:C`, `cx:CHOKE`, `cx:DIODE_SS`, `cx:FUSE`, `cx:SWITCH`, `cx:LAMP`).
A symbol with three or more pins — `cx:POT` (1/3 ends, 2 wiper), `cx:POT_TAP`
(the same plus 4, a fixed tap into the element — the 6G6-B's 350 kΩ/70 kΩ-tap
Treble control), `cx:DUALCAN`, `cx:OT_PP`, `cx:PT` — has no unambiguous "two
ends", and guessing one is how a gate starts lying. Name the two terminals in `sch_map.element_pins`, or declare
the element `netlist_undrawn`.

---

## Data the amp declares

### Reused from `amps/<id>/layout.yaml` `net_map`

Three keys carry facts about the *netlist*, not about a board, so the schematic
gate reuses them rather than making an amp say the same thing twice. Reused
entries are printed with their provenance so a reviewer sees the layout is doing
the explaining.

| key | meaning here |
|---|---|
| `series_bridge` | a DC-transparent part the netlist omits (a grid stopper): the netlist node runs **through** it, so its two ends are one node on any drawing |
| `netlist_unplaced` | a netlist element realised by a control rather than a discrete two-lead part (a pot modelled as a grid leak) |
| `excluded_tubes` | a socket the DC netlist legitimately omits (a tremolo oscillator has no static operating point) — its drawn wiring is reported as not DC-checked |

`anchors` is **not** reused: its terminals name board eyelets and transformer
lead colours (`T2.blue`), which mean nothing on a sheet.

### `amps/<id>/sch_map.yaml` — optional sidecar

A sidecar, not a new `meta.yaml` key: `meta.yaml` is schema-gated by
`validate.py`, and the layout precedent puts `net_map` in the drawing's own
file. A `.kicad_sch` cannot carry it, so the closest analogue is a file beside
it. Absent file == no declarations.

```yaml
# amps/5e3/sch_map.yaml — schematic ↔ netlist reconciliation (data, never a
# guess in code). Every line here is a claim a reviewer can check against the
# sheet and the netlist.

anchors:                 # terminal -> netlist node
  # The netlist omits OT primary DCR, so both plates and the CT are one node.
  # Terminals anchored to the SAME node declare that collapsed winding.
  T2.1: BP1              # OT primary, V3 plate end
  T2.2: BP1              # centre tap
  T2.3: BP1              # OT primary, V4 plate end
  T2.4: "0"              # secondary DCR folded into ground (the NFB return)

series_bridge:           # DC-transparent parts the netlist omits, drawn here
  R3s: "1.5 k output grid stopper — no DC grid current, grid == coupler node"
  R4s: "1.5 k output grid stopper — as above"

symbols:                 # netlist ref/instance -> schematic reference
  RCHOKE: L1             # winding DCR drawn as a choke symbol
  V1A: V1                # the sheet letters this section without a suffix

element_pins:            # netlist ref -> the two terminals that realise it
  RG3: [VR1.2, VR1.1]    # the volume pot's wiper -> track -> cold end

netlist_undrawn:         # netlist element with no symbol — reported, not failed
  RMIX: "the two channels' mixing resistors, drawn as one network"

schematic_claim: verified   # opt in to HARD gating (see below)
```

**Terminal syntax**: `REF.PIN` for a symbol pin, `<NAME>` for a label net.

### Declaration hygiene

A declaration never widens to bury a failure, and it never rots unnoticed
either. An **undeclared** undrawn element is a hard finding, and `--report`
echoes every reconciliation that was applied.

A declaration in the sheet's own `sch_map.yaml` that names nothing on the sheet
is a **`STALE DECLARATION`** finding, whichever key it sits under: a `symbols`
target, an `anchors` terminal, an `element_pins` pair, a `series_bridge`
designator. It is named as the stale line it is, with the key and the value that
no longer resolve, and the declaration is not applied.

This matters most for `symbols`, because that key *redirects* the lookup for a
netlist element. When its target no longer exists the lookup lands nowhere, and
reporting only "netlist `V1A` has no symbol" points at the wrong thing: the
element is usually still on the sheet under its own name, and the obsolete
redirect is what hid it. So the finding names the stale mapping first and adds
the hint when the netlist designator does letter a symbol:

```
STALE DECLARATION: sch_map.symbols[V1A] -> V1 names no symbol on this sheet, so
netlist V1A was looked up and not found. The sheet does letter a symbol 'V1A',
so the mapping is probably just obsolete — delete it.
```

The gate never repairs a stale mapping by falling back to the netlist
designator. A declaration is data a reviewer owns, and silently working around
a wrong one is how a map rots.

A declaration **reused from `layout.yaml`** that does not apply here is a scope
line rather than a finding: it was written about a board, and a board part may
legitimately have no counterpart on a sheet.

---

## What it reports

Each line names something a fixer can act on. A node lands in exactly one of
`MERGED` / `SPLIT` / `UNREALISED` / `NODE MISMATCH` / clean, so the per-node and
per-component views do not repeat each other.

| class | meaning |
|---|---|
| `MERGED` | one drawn net carries two netlist nodes — **a short**, with the cause of each binding |
| `SPLIT` | one netlist node drawn as several nets that never join — **a missing join**, with each fragment's members |
| `UNREALISED` | a netlist node no drawn net carries at all — usually the far side of a merge; named separately so it cannot vanish |
| `NODE MISMATCH` | a node neither merged nor split whose modelled membership still differs (a dangling lead) |
| `WRONG TERMINAL` | a modelled element drawn across the wrong pair of nodes |
| `SHORTED` | a modelled element whose two pins are on one drawn net |
| `UNMAPPED` | a modelled element's lead on a net carrying no netlist node; says explicitly when the pin is **dangling** |
| `MISSING SYMBOL` | a netlist element with no schematic symbol and no declaration |
| `STALE DECLARATION` | an `sch_map.yaml` entry that names nothing on this sheet, so it was not applied |
| `REVERSED DIODE` | a `cx:DIODE_SS` drawn the wrong way round, judged against the simulated sign of the supply it sits on ([Rectifier polarity](#rectifier-polarity)) |
| `SHORTED WINDING` | a winding whose two ends the drawing puts on one net, read on the nets as drawn ([Shorted windings](#shorted-windings)) |

`--report` adds the applied declarations and the coverage narrative: how many
symbols the netlist models, how many terminals are DC-checked, which tubes are
declared excluded, and — grouped by symbol class — **every** terminal that is
not DC-checked. `--analyze <amp>` prints the per-node membership table (drawn /
missing / neither-end / unexpected).

## Shorted windings

The netlist models no winding, and this gate joins what it is told to: an
`sch_map` anchor that puts both OT primary ends on `BP1` merges them on
purpose, because the DC model omits the winding's resistance. So a drawing
that shorts a winding used to pass. On 2026-09-10 the 5F1 was found drawing
its output transformer's primary as a wire from `PRI_P` to `PRI_B`, and 16 of
24 power transformers had their mains primary shorted because a global label
named `MAINS` lettered both leads. Two labels with one name are one net.

`SHORTED WINDING` reads every winding by its symbol's own pin names, resolved
to numbers through the sheet's `lib_symbols`, on the nets **as drawn**: before
any declared contraction.

| symbol | windings (end, end) |
|---|---|
| `cx:PT` | primary `PRI_1`/`PRI_2`; HT secondary `HT_A`/`HT_B` |
| `cx:OT_SE` | primary `PRI_P`/`PRI_B`; secondary `SEC_H`/`SEC_C` |
| `cx:OT_PP` | primary `PRI_A`/`PRI_B`; secondary `SEC_H`/`SEC_C` |
| `cx:TANK` | input coil `IN_H`/`IN_C`; output coil `OUT_H`/`OUT_C` |
| `cx:CHOKE` | `1`/`2`, when no netlist element is drawn as it (a modelled choke's short is `SHORTED`'s) |

A winding fails when its two ends are one net: joined by a wire, by two global
labels of one name, or through a fuse or a switch in its drawn position. The
last is how the 6G5's primary closed on itself, from one `MAINS` label through
switch, fuse and winding back to the same name. The finding says which: a
label is blamed only when one name letters both sides on the wires-only graph,
otherwise the wire is. **A centre tap is not an end.** CT to ground and CT to
B+ are how a winding is used and are never a finding. A CT on one net with an
end shorts half the winding, and is named as that half (`primary's A half`,
`HT secondary's B half`) unless the whole winding is already named.

## Rectifier polarity

A diode's direction is recorded in exactly one place on a sheet: the rotation
of its `cx:DIODE_SS` symbol (pin 1 = A, pin 2 = K, the band). The netlist models
no diode, so the equivalence proof above is blind to it, and on 2026-09-10 a
count found 25 of 68 sheet diodes drawn backwards under clean verdicts. What
the netlist *does* fix is the sign of every supply, and that is what this check
reads.

For each diode terminal the gate takes the netlist node its net carries and
that node's simulated voltage: from `reference/op-points.yaml`, or, for a rail
the export does not list, from the netlist's own ideal source to ground, whose
simulated voltage *is* the source value. Node `0` is 0 V. The part is
**`REVERSED DIODE`** when any clause holds:

| clause | why it is backwards |
|---|---|
| the cathode sits below −5 V | a negative supply is fed from a rectifier's **anode**; a cathode there would charge the node positive |
| the anode sits above +50 V | B+ is taken off a rectifier's **cathode** |
| both ends are modelled and V(anode) − V(cathode) > 1 V | forward-biased at DC between two nodes the netlist holds apart: it would conduct, and the circuit has no such path |

**The walk to the supply node.** A rectifier's own node usually sits behind
parts the netlist does not model: a bias row's series resistor and trim pot, an
HT standby switch, fuse or choke. So a terminal whose net carries no netlist
node walks outward across symbols that conduct DC and carry no netlist element
(`cx:R`, `cx:POT`, `cx:POT_TAP`, `cx:CHOKE`, `cx:FUSE`, `cx:SWITCH`; every pin of
a pot is one body), never across a capacitor, a transformer, a tube or another
diode, and stops at each net that carries a node. A rectifier is the source of
the supply it feeds, so its node lies at least as far from ground as anything
it reaches through resistors alone, and on the same side; the terminal
inherits the reached node nearest ground. Three things decide nothing: ground
reached through a resistor (a bleeder's or a divider's foot), a reached node
with no simulated volts, and nodes of both signs. The path prints with the
verdict. The M1987's bias rectifier at e4e59fa reads

```
REVERSED DIODE: D1 is drawn the wrong way round: cathode on -48.0 V, and a negative
supply is fed from a rectifier's ANODE. [anode D1.1 on no modelled node; cathode D1.2
on NBIAS = -48.0 V (ideal source VBIAS) through RBB, VR6] Turn the symbol through 180 degrees.
```

**Not checked is said out loud.** A diode the model does not decide is listed
with its reason in every run's closing summary, and per sheet under `--report`:
no terminal reaches a modelled node (the inner diodes of a series HT stack), or
the only node reached is ground (a bridge's low side). *Confirmed* means more
than "not reversed": the drawn part keeps every clause **and** the same part
turned round would break one, so the model actually decided it.

The rule lives in `verify_layout_nets.judge_diode`, beside `parse_netlist`, so
the board gate reads `cathode:` fields by exactly the same clauses (report-only
there for now; see `docs/layout-schema.md`). Here `REVERSED DIODE` is a finding
like any other: it hard-fails a sheet that claims `schematic_claim: verified`.

## The gate

An amp whose `sch_map.yaml` carries `schematic_claim: verified` is **hard-gated**:
a finding fails CI. An amp without the claim is report-only. This mirrors
`wiring_claim` on the layout side and `verification.status` on the netlist side —
verified is earned, never granted. `--strict` fails on any finding on any sheet;
switch CI to it once the corpus is green.

`--selftest` plants faults in a temp copy of a real sheet and proves the gate
fails on them: a wire end moved onto the wrong pin (the phase-inverter fault
class) and a wire deleted (the dangling-pin fault class). It then walks the
declaration-hygiene cases, one per `sch_map` key, including a `symbols` target
renamed away while the netlist designator still letters a symbol — the case that
used to degrade into a misleading `MISSING SYMBOL`. It asserts both that the
stale line is named and that the element is *not* mis-reported as undrawn, and
that a reused `layout.yaml` declaration is never called stale `sch_map` data.
Each mutation is scored on the **delta** — it must add a new finding of the
expected class naming the mutated designator, and must not lower the total,
which holds whether or not the sheet was clean to begin with. The assertions
keep holding once
a sheet does go green.

It then proves the polarity check. Each clause is run on synthetic volts both
ways round, including the forward-bias clause alone, with neither threshold
crossed. Three planted faults, each an edit to a temp copy of a regenerated
sheet, must each add a `REVERSED DIODE`: the 5F4's bias rectifier turned
through 180°, the AB763-Twin's HT rectifier `DHTA` turned through 180°, and a
diode planted forward from `<B+1>` to `<GND>`. The AA1164's bias rectifier and
the AB165's HT rectifier, together with the two unflipped parts, must come
back *confirmed*, not merely unflagged.

The shorted-winding cases plant four faults, and each must add a
`SHORTED WINDING`:
- a wire across the 5E3's OT primary;
- a wire from its centre tap to one plate end, which must be named as the half;
- the AC15's neutral label renamed to its line label's name, so the loop closes
  through the power switch and fuse;
- both of the 5F4's primary labels lettered `MAINS`.

The same three sheets as committed must add none. The run ends by printing its
case count, split by class.

## CI

```yaml
      - name: Schematic ↔ netlist equivalence
        run: |
          python3 pipeline/verify_schematic_nets.py --selftest
          python3 pipeline/verify_schematic_nets.py
```

The self-test runs first: a gate that cannot catch a planted fault is
decoration, so it must be proven before its verdict is read.
