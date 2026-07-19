# Contributing to Circuit Codex

Contributions are welcome — new circuits, corrections to existing ones, tube models,
pipeline improvements. This project is community-driven by design and
curator-controlled in practice: anyone can propose, CI and maintainers gate what
merges, and only the pipeline assigns the `verified` badge.

## The three hard rules

Pull requests that break these are closed regardless of quality:

1. **Redraw from facts — never scan or trace.** Your schematic must be independently
   drawn from the circuit's facts: component values, topology, published voltage
   charts, your own bench measurements. Reproducing or tracing factory drawings brings
   copyright exposure the project will not carry. Your PR includes an attestation
   checkbox for this.
2. **Circuit-number-first naming.** Directory ids and titles use the circuit
   designation (`5e3`, `jtm45`, `ab763`). Maker and model names appear only
   descriptively in metadata (`name_style: "Tweed Deluxe-style"`) — never in ids,
   filenames, or as standalone product names.
3. **DCO sign-off.** Every commit is signed off (`git commit -s`), certifying you have
   the right to contribute the work under this repo's licenses (code MIT, circuit data
   CC-BY-SA 4.0, tube models CC0). See <https://developercertificate.org/>.

## Adding a circuit

1. Copy `amps/_template/` to `amps/<id>/` and fill in `meta.yaml`
   (schema: `docs/schema.md`).
2. Draw `schematic.kicad_sch` (KiCad 8+, or generate it with a
   `pipeline/draw_<id>.py` script using `pipeline/schematic_lib.py` — how every
   current schematic is made).
3. Write `netlist.cir` referencing models in `models/`; add `voltages.yaml` with the
   published chart values you verified against, and `bom.yaml` keyed to the
   schematic's reference designators.
4. Optionally add `layout.yaml` (see `docs/layout-schema.md`) — a board layout with a
   wiring layer that CI proves electrically equivalent to your netlist.
5. Open a PR. CI validates the metadata schema, cross-checks BOM↔schematic
   designators, round-trips the schematic, simulates the operating point in ngspice
   against your chart values, renders and lint-checks the layout, and runs the
   layout↔netlist equivalence gate.
6. A maintainer reviews. Circuits land as `draft`; the `verified` badge requires the
   simulated operating point within tolerance of the published chart **and**
   maintainer sign-off.

New here — human or AI agent? Start with the site's
[About page](https://circuitcodex.com/about/) and this repo's `AGENTS.md` for the
binding conventions.

Not sure what to work on? Check the [wanted circuits](https://github.com/TheAnalogMaker/circuit-codex/issues?q=is%3Aissue+is%3Aopen+label%3A%22wanted+circuits%22) issue list.

## Corrections

Small fixes (a wrong value, a missing lineage edge, prose errors) are the most
valuable PRs we get — production variants and revision quirks live in this
community's collective memory, and we want them captured as data. Cite your source
(published chart, dated schematic revision, bench measurement) in the PR.

## Tube models

`models/` accepts only freshly derived fits from published datasheet curves with the
method documented in the file header — see `models/LICENSE.md` for why. Never copy
models from existing collections.
