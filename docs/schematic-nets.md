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
electrolytics, this is the assumption to revisit.*

**Pots, cans and windings need an explicit terminal pick.** A netlist `R`/`C`
binds without ceremony only to a genuine two-lead passive
(`cx:R`, `cx:C`, `cx:CHOKE`, `cx:DIODE_SS`, `cx:FUSE`, `cx:SWITCH`, `cx:LAMP`).
A symbol with three or more pins — `cx:POT` (1/3 ends, 2 wiper), `cx:DUALCAN`,
`cx:OT_PP`, `cx:PT` — has no unambiguous "two ends", and guessing one is how a
gate starts lying. Name the two terminals in `sch_map.element_pins`, or declare
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

A declaration never widens to bury a failure. An **undeclared** undrawn element
is a hard finding; a **stale** declaration naming a terminal the sheet does not
carry is reported and not applied; and `--report` echoes every reconciliation it
did apply.

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

`--report` adds the applied declarations and the coverage narrative: how many
symbols the netlist models, how many terminals are DC-checked, which tubes are
declared excluded, and — grouped by symbol class — **every** terminal that is
not DC-checked. `--analyze <amp>` prints the per-node membership table (drawn /
missing / neither-end / unexpected).

## The gate

An amp whose `sch_map.yaml` carries `schematic_claim: verified` is **hard-gated**:
a finding fails CI. An amp without the claim is report-only. This mirrors
`wiring_claim` on the layout side and `verification.status` on the netlist side —
verified is earned, never granted. `--strict` fails on any finding on any sheet;
switch CI to it once the corpus is green.

`--selftest` plants faults in a temp copy of a real sheet and proves the gate
fails on them: a wire end moved onto the wrong pin (the phase-inverter fault
class), a wire deleted (the dangling-pin fault class), and a stale `sch_map`
declaration. Because no sheet is green yet, each mutation is scored on the
**delta** — it must add a new finding of the expected class naming the mutated
designator, and must not lower the total. The same assertions keep holding once
a sheet does go green.

## CI

```yaml
      - name: Schematic ↔ netlist equivalence
        run: |
          python3 pipeline/verify_schematic_nets.py --selftest
          python3 pipeline/verify_schematic_nets.py
```

The self-test runs first: a gate that cannot catch a planted fault is
decoration, so it must be proven before its verdict is read.
