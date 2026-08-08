#!/usr/bin/env python3
"""Take an already-routed layout the rest of the way: walk out its hairpins,
prove the result from disk, then report the clearances left.

    python3 _finish.py 5e6a 6g6b
"""
from __future__ import annotations

import sys

from _route import Model, kinks, margins, unkink, write_back


def total_kinks(m):
    return sum(kinks(m, i) for i in range(m.n) if m.plain[i])


for amp in sys.argv[1:]:
    m = Model(amp)
    if m.hard:
        print(f"{amp}: STILL {m.hard} hard finding(s) — not finished")
        continue
    before = total_kinks(m)
    left = before
    for seed in (11, 23, 37, 53, 71, 89, 103):
        left = unkink(m, seed=seed, slack=120000.0)
        if left == 0 or m.hard:
            break
    if m.hard:
        print(f"{amp}: unkink re-opened the gate — abandoning, layout untouched")
        continue
    write_back(amp, m.layout)
    # prove it from disk, not from the object that just claimed it
    chk = Model(amp)
    wt, wp = margins(chk)
    print(f"{amp}: reloaded — hard={chk.hard} hairpins {before} -> "
          f"{total_kinks(chk)}; tightest terminal {wt[0]:.2f}px (gate 5.0), "
          f"worst near-parallel {wp[0]:.1f}px (gate 8.0)")
