# Reference architectures

`reference/architectures/*.yaml` describes the handful of **chassis architectures**
the corpus's circuits fall into. Not a circuit, not a layout: the arrangement that
determines how a chassis is organised, and how a reader should decompose any
amplifier belonging to it.

There are seven, and four of them cover 37 of the 41 documented circuits.

## Why this exists as data rather than prose

The archive already cross-cuts its circuits by topology dimension, and already
draws each one's board. What it did not have was the layer between: an account of
how a *class* of amplifier is organised, so a reader meeting an unfamiliar circuit
knows which shape it is and where each section sits.

Written as prose that would have been the weakest thing on the site — the one
artifact checked against nothing, on an archive whose entire claim is that its
claims are checked. So it is written as data with a predicate, and gated.

## Schema

```yaml
slug: ltp-fixed                     # == filename stem
title: "Long-tailed pair, fixed bias"
order: 1                            # display order only
summary: >-
  Prose. What the architecture is, and what having it commits a chassis to.

predicate:                          # membership, over meta.topology
  phase_inverter: long-tailed-pair
  bias: fixed

sections:                           # editorial decomposition, in signal order
  - id: input
    label: "Input and first stage"
    holds: "What sits in this section, and what varies across the class."

requires:                           # claims, checked against independent data
  output_stage: push-pull           # vs reference/loadlines.yaml `config`
  negative_bias_supply: true        # vs a negative DC source in netlist.cir

exceptions:                         # optional; amp id -> dated reason
  some-amp: "2026-09-09 — why this circuit matches the predicate but is not
             a member. A reason a reviewer can check."
```

**Membership is a predicate, never a list of ids.** A new circuit files itself
into the right architecture the moment its `meta.topology` is written, and cannot
be quietly left out of one. That is the same reason `used_in` on a tube page is
derived rather than authored.

## What the gate proves

`pipeline/check_architectures.py`, with `--selftest` planting one fault per rule:

* every circuit matches **exactly one** architecture, or carries a dated,
  reasoned exception — matching none is a gap in the taxonomy, matching two means
  two predicates overlap;
* no architecture is empty, and none has an empty section list;
* `requires.output_stage` agrees with the stage `config` in
  `reference/loadlines.yaml`, which `export_loadlines.py` derives from the netlist;
* `requires.negative_bias_supply` agrees with whether the circuit's `netlist.cir`
  actually contains a negative DC source;
* no declaration is vestigial: an exception for a circuit that no longer needs
  one, or that does not exist, fails.

**The independence is the design.** The predicate selects on `meta.topology`; the
requirements are checked against the netlist and against netlist-derived data. A
disagreement therefore means either the architecture is wrong or that circuit's
metadata is — and both are worth being told about. Checking a declaration against
the same field that produced it would prove nothing.

## What is NOT claimed

`sections` is an editorial decomposition. The gate checks it is present, non-empty
and uniquely identified; it cannot check that a boundary is drawn in the right
place, and does not pretend to.

Nothing here asserts the physical layout, dimensions or clearances of any
amplifier. Those are properties of a chassis, and this archive's board drawings
are explicit that they are not dimensioned reproductions. An architecture
describes organisation, not construction.

## Adding one

Only when a circuit matches no existing predicate — which the gate will tell you,
by name, the moment its metadata lands. Prefer extending the taxonomy over writing
an exception: an exception says "this circuit is a member but should not be
counted", which is rarely what is meant, and needs a reason a reviewer can check.
