# Circuit Codex

**An open, machine-readable archive of the circuits that made electric guitar.**

Every classic amplifier circuit — redrawn as a clean KiCad schematic, verified as an
ngspice netlist against published voltage charts, tagged with structured metadata, and
connected to its ancestors and descendants in a navigable lineage graph
(5F6-A → JTM45 → 1959 → 2204 …).

An [Analog Maker](https://theanalogmaker.com) project. Guitar-pedal circuits are on the
roadmap once the amp corpus is established.

**Status: Phase 0 — pipeline pilot.** First three circuits (5F1, 5E3, 5F6-A) are being
run end-to-end to prove the ingest pipeline. Nothing here is `verified` yet.

## Principles

1. **Redrawn from facts, never scanned.** Every schematic is independently drawn from
   the underlying circuit — component values, topology, published voltage charts. No
   factory drawings are reproduced or traced.
2. **Circuit-number-first naming.** Circuits are identified by their designation
   (`5e3`, `jtm45`, `ab763`); maker names appear only descriptively ("Tweed
   Deluxe-style"). This project is not affiliated with or endorsed by any amplifier
   manufacturer.
3. **Verification is earned, not assumed.** A circuit is `verified` only when its
   netlist simulates within tolerance of the published voltage chart in CI **and** a
   maintainer signs off. Everything else is `draft`.
4. **Open forever.** The archive is free. The data stays free. See Licensing.

## Repository layout

```
amps/<id>/          one directory per circuit
  schematic.kicad_sch   redrawn KiCad schematic
  netlist.cir           ngspice netlist (references models/)
  meta.yaml             era, tubes, topology tags, lineage edges  → docs/schema.md
  voltages.yaml         published chart vs simulated operating point
  notes.md              history + circuit walkthrough
models/             tube SPICE models, freshly derived from datasheet curves (CC0)
pipeline/           validation + rendering tooling (Python)
docs/               schema and process documentation
```

## Licensing

- **Code** (`pipeline/`, site, CI): [MIT](LICENSE)
- **Circuit data** (`amps/`): [CC-BY-SA 4.0](amps/LICENSE.md)
- **Tube models** (`models/`): [CC0 1.0](models/LICENSE.md) — to our knowledge the first
  explicitly open-licensed tube SPICE model set

## Contributing

Contributions are welcome from day one — see [CONTRIBUTING.md](CONTRIBUTING.md).
The short version: redraw from facts (attested in your PR), follow the naming rules,
sign off your commits (DCO). The `verified` badge is assigned by CI + maintainer
review only.

## Safety

Tube amplifiers operate at lethal voltages (350 V+), and filter capacitors hold charge
long after power-off. This archive documents circuits for study; if you build or open
an amplifier, learn high-voltage safety practice first. The authors accept no liability
for use of this information.
