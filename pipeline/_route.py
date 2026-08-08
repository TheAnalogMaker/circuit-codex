#!/usr/bin/env python3
"""Scratch routing aid: fan convergent hookup runs apart until the collision
lint's wiring half reports zero.

It only ever edits `via:` waypoints — never a run's `from`/`to`, never a part
position, never the bus. The wiring layer's electrical claim is carried by the
endpoints, so the net graph pipeline/verify_layout_nets.py proves is untouched
by anything this does (re-run it anyway; that is the discipline).

Scoring mirrors the gate exactly for the hard verdict, and adds a soft term for
near-misses so the search has a gradient rather than a cliff. Costs are held as
a per-pair matrix so a single run's re-route only re-scores that run's row.

Not part of the gate set.
"""
from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

import yaml

from render_layouts import (LINT_ANGLE, LINT_OVERLAP, LINT_SEP, LINT_TERM,
                            LINT_VERTEX_CLEAR, Renderer, _parallel_overlap,
                            _point_seg_dist, _seg_angle_deg, load_bom)

ROOT = Path(__file__).resolve().parent.parent

SOFT_TERM = 11.0       # an endpoint this close to another run already scores
SOFT_ANGLE = 15.0      # …as does a shallower-than-comfortable convergence
SOFT_SEP = 4.0
SOFT_W = 55.0          # margins matter: clearing the gate by 0.3 px is not clear
HARD_W = 4000000.0
# The drawing is the deliverable, not the number: a re-route that clears the
# gate by sending a lead on a detour is worse than the finding it fixed. Churn
# is priced in — added waypoints and added wire length both cost — so the
# search settles on the smallest change that reads as deliberate routing.
CHURN_VIA = 4000.0     # per waypoint added to a run
CHURN_LEN = 7.0        # per px of polyline length added
CHURN_TURN = 30000.0   # per elbow that doubles the lead back on itself
TURN_LIMIT = 108.0     # degrees of course change that reads as a hairpin
# phase 2 only works pairs that are genuinely tight — a 7 px clearance is not a
# defect, and re-routing a lead that reads fine only churns the drawing.
TIGHT_SOFT = 16.0      # (SOFT_TERM - d)**2 at d = 7 px
# The authored routing is a reading of the published drawing, so it is the thing
# being preserved: a fix fans a lane apart, it does not re-plan the lead. Shape
# drift from the authored polyline is priced, and bounded outright.
CHURN_SHAPE = 320.0    # per px of mean drift from the authored polyline
SHAPE_LIMIT = 84.0     # px of max drift a re-route may not exceed


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


class Model:
    """Wiring-lint cost model over one layout's plain runs."""

    def __init__(self, amp: str):
        self.amp = amp
        self.dir = ROOT / "amps" / amp
        self.layout = yaml.safe_load((self.dir / "layout.yaml").read_text())
        self.bom = load_bom(self.dir)
        self.rend = Renderer(self.layout, self.bom, amp)
        self.specs = self.rend.runs                 # same list object as layout["runs"]
        self.n = len(self.specs)
        self.pts = [None] * self.n
        self.plain = [False] * self.n
        for i in range(self.n):
            self._geom(i)
        self.pair_hard = [[0] * self.n for _ in range(self.n)]
        self.pair_soft = [[0.0] * self.n for _ in range(self.n)]
        for i in range(self.n):
            for j in range(self.n):
                if i != j:
                    h, s = self._pair(i, j)
                    self.pair_hard[i][j] = h
                    self.pair_soft[i][j] = s
        self.hard = sum(sum(r) for r in self.pair_hard)
        self.soft = sum(sum(r) for r in self.pair_soft)
        self.base_pts = [list(p) if p else None for p in self.pts]
        self.base_len = [self._plen(i) for i in range(self.n)]
        self.base_turns = [self._turns(i) for i in range(self.n)]
        self.base_via = [len(s.get("via") or []) for s in self.specs]
        self.orig_via = [[list(v) for v in (s.get("via") or [])]
                         for s in self.specs]
        self.churn = 0.0
        self.score_ceiling = float("inf")

    def to_grid(self, pt):
        """Pixel -> the [x=col, y=row] grid a `via` is written in."""
        x0, x1 = self.rend.ex(0), self.rend.ex(1)
        y0, y1 = self.rend.ey(0), self.rend.ey(1)
        return [(pt[0] - x0) / (x1 - x0), (pt[1] - y0) / (y1 - y0)]

    def midpoint_hint(self, i):
        """Where a first waypoint belongs on a run that has none: between its
        own two ends. Seeding at the grid origin instead put every candidate
        waypoint in the far corner of the board, so a via-less run — the exact
        shape that lands a straight lead across another run's eyelet — could
        never be bowed clear."""
        pts = self.pts[i]
        if not pts:
            return [0.0, 0.0]
        a, b = self.to_grid(pts[0]), self.to_grid(pts[-1])
        return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]

    def _plen(self, i):
        pts = self.pts[i]
        if not pts:
            return 0.0
        return sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))

    def _turns(self, i):
        """Elbows where the lead changes course by more than TURN_LIMIT — the
        out-and-back a reader can only read as a stub, not a route."""
        pts = self.pts[i]
        if not pts or len(pts) < 3:
            return 0
        bad = 0
        for k in range(1, len(pts) - 1):
            ax, ay = pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]
            bx, by = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
            na, nb = math.hypot(ax, ay), math.hypot(bx, by)
            if na < 1e-6 or nb < 1e-6:
                continue
            cosang = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
            if math.degrees(math.acos(cosang)) > TURN_LIMIT:
                bad += 1
        return bad

    def _drift(self, i):
        """(mean, max) distance from the current polyline to the authored one."""
        pts, base = self.pts[i], self.base_pts[i]
        if not pts or not base or len(base) < 2:
            return 0.0, 0.0
        samples = []
        total = self._plen(i)
        step = max(total / 26.0, 6.0)
        for k in range(len(pts) - 1):
            p, q = pts[k], pts[k + 1]
            seg = math.dist(p, q)
            n = max(1, int(seg / step))
            for t in range(n + 1):
                f = t / n
                samples.append((p[0] + (q[0] - p[0]) * f,
                                p[1] + (q[1] - p[1]) * f))
        ds = [min(_point_seg_dist(s, base[k], base[k + 1])
                  for k in range(len(base) - 1)) for s in samples]
        return sum(ds) / len(ds), max(ds)

    def _churn_of(self, i):
        extra_via = max(0, len(self.specs[i].get("via") or []) - self.base_via[i])
        extra_len = max(0.0, self._plen(i) - self.base_len[i])
        extra_turn = max(0, self._turns(i) - self.base_turns[i])
        mean_drift, _mx = self._drift(i)
        return (extra_via * CHURN_VIA + extra_len * CHURN_LEN
                + extra_turn * CHURN_TURN + mean_drift * CHURN_SHAPE)

    # ---- geometry -----------------------------------------------------------
    def _geom(self, i):
        spec = self.specs[i]
        twisted = str(spec.get("style", "")).lower() == "twisted"
        pts = self.rend._run_points(spec, f"run[{i}]")
        self.plain[i] = bool(pts) and not twisted
        self.pts[i] = pts if self.plain[i] else None
        self.bb = getattr(self, "bb", [None] * self.n)
        self.bb[i] = _bbox(pts) if self.pts[i] else None

    # ---- pair cost ----------------------------------------------------------
    def _pair(self, i, j):
        """Cost the ORDERED pair (i, j): parallel overlap counted once (i < j)
        plus i's endpoints measured against j's polyline."""
        hard = 0
        soft = 0.0
        pa, pb = self.pts[i], self.pts[j]
        if pa is None or pb is None:
            return 0, 0.0
        ba, bbx = self.bb[i], self.bb[j]
        if (ba[0] > bbx[2] + 12 or bbx[0] > ba[2] + 12
                or ba[1] > bbx[3] + 12 or bbx[1] > ba[3] + 12):
            return 0, 0.0
        if i < j:
            for sa in range(len(pa) - 1):
                a1, a2 = pa[sa], pa[sa + 1]
                for sb in range(len(pb) - 1):
                    b1, b2 = pb[sb], pb[sb + 1]
                    ang = _seg_angle_deg(a1, a2, b1, b2)
                    if ang >= SOFT_ANGLE:
                        continue
                    ov = _parallel_overlap(a1, a2, b1, b2, SOFT_SEP)
                    if not ov:
                        continue
                    if ang < LINT_ANGLE:
                        hv = _parallel_overlap(a1, a2, b1, b2, LINT_SEP)
                        if hv and hv[0] > LINT_OVERLAP:
                            hard += 1
                    soft += ov[0] * 0.6
        for E in (pa[0], pa[-1]):
            if any(math.hypot(E[0] - v[0], E[1] - v[1]) < LINT_VERTEX_CLEAR
                   for v in pb):
                continue
            d = min(_point_seg_dist(E, pb[sb], pb[sb + 1])
                    for sb in range(len(pb) - 1))
            if d >= SOFT_TERM:
                continue
            if d < LINT_TERM:
                hard += 1
            soft += (SOFT_TERM - d) ** 2
        return hard, soft

    # ---- incremental update -------------------------------------------------
    def reroute(self, i, via):
        """Apply a via list to run i; return an undo token."""
        spec = self.specs[i]
        old_via = spec.get("via")
        old_pts, old_plain, old_bb = self.pts[i], self.plain[i], self.bb[i]
        old_rowh = list(self.pair_hard[i])
        old_rows = list(self.pair_soft[i])
        old_colh = [self.pair_hard[j][i] for j in range(self.n)]
        old_cols = [self.pair_soft[j][i] for j in range(self.n)]
        old_hard, old_soft, old_churn = self.hard, self.soft, self.churn
        self.churn -= self._churn_of(i)
        if via:
            spec["via"] = [list(v) for v in via]
        else:
            spec.pop("via", None)
        self._geom(i)
        self.churn += self._churn_of(i)
        for j in range(self.n):
            if j == i:
                continue
            h, s = self._pair(i, j)
            self.hard += h - self.pair_hard[i][j]
            self.soft += s - self.pair_soft[i][j]
            self.pair_hard[i][j], self.pair_soft[i][j] = h, s
            h2, s2 = self._pair(j, i)
            self.hard += h2 - self.pair_hard[j][i]
            self.soft += s2 - self.pair_soft[j][i]
            self.pair_hard[j][i], self.pair_soft[j][i] = h2, s2
        return (i, old_via, old_pts, old_plain, old_bb, old_rowh, old_rows,
                old_colh, old_cols, old_hard, old_soft, old_churn)

    def undo(self, tok):
        (i, old_via, old_pts, old_plain, old_bb, rowh, rows, colh, cols,
         hard, soft, churn) = tok
        spec = self.specs[i]
        if old_via is None:
            spec.pop("via", None)
        else:
            spec["via"] = old_via
        self.pts[i], self.plain[i], self.bb[i] = old_pts, old_plain, old_bb
        self.pair_hard[i] = rowh
        self.pair_soft[i] = rows
        for j in range(self.n):
            self.pair_hard[j][i] = colh[j]
            self.pair_soft[j][i] = cols[j]
        self.hard, self.soft, self.churn = hard, soft, churn

    def legible(self, i):
        """Hard constraint on the DRAWING, independent of the gate: a fix that
        sends a lead the long way round, hairpins it, or piles on waypoints is
        not a fix. Bounds are per-run and relative to the authored routing."""
        if self.pts[i] is None:
            return True
        if len(self.specs[i].get("via") or []) > self.base_via[i] + 1:
            return False
        if self._turns(i) > self.base_turns[i]:
            return False
        if self._drift(i)[1] > SHAPE_LIMIT:
            return False
        return self._plen(i) <= self.base_len[i] * 1.22 + 34.0

    @property
    def score(self):
        return self.hard * HARD_W + self.soft * SOFT_W + self.churn

    def snapshot(self):
        return [[list(v) for v in (s.get("via") or [])] for s in self.specs]

    def restore(self, snap):
        for i, via in enumerate(snap):
            if [list(v) for v in (self.specs[i].get("via") or [])] != via:
                self.reroute(i, via)

    def blame(self, hard_only=True):
        """Runs implicated in a finding, weighted. Hard-only by default: the
        soft term is a tie-break for the runs already being worked on, never a
        licence to re-route a lead that reads fine."""
        w = {}
        for i in range(self.n):
            for j in range(self.n):
                if i == j:
                    continue
                v = self.pair_hard[i][j] * 40.0
                if not hard_only and self.pair_soft[i][j] > TIGHT_SOFT:
                    v += self.pair_soft[i][j] * 0.05
                if v:
                    w[i] = w.get(i, 0.0) + v
                    w[j] = w.get(j, 0.0) + v
        return w


# ---- moves ------------------------------------------------------------------
DELTAS = [0.05, 0.1, 0.17, 0.26, 0.38, 0.55, 0.8, 1.15, 1.6]


def clamp(layout, pt):
    cols = layout["board"]["cols"]
    rows = layout["board"]["rows"]
    return [round(max(-3.2, min(cols + 2.2, pt[0])), 3),
            round(max(-4.6, min(rows + 3.6, pt[1])), 3)]


def candidates(layout, spec, rng, hint=None):
    via = [list(v) for v in (spec.get("via") or [])]
    out = []
    for j in range(len(via)):
        for d in DELTAS:
            for ax in (0, 1):
                for sgn in (1, -1):
                    nv = [list(v) for v in via]
                    nv[j][ax] += sgn * d
                    nv[j] = clamp(layout, nv[j])
                    out.append(nv)
    for pos in range(len(via) + 1):
        base = via[pos - 1] if pos > 0 else None
        nxt = via[pos] if pos < len(via) else None
        if base and nxt:
            seed = [(base[0] + nxt[0]) / 2, (base[1] + nxt[1]) / 2]
        else:
            seed = list(base or nxt or hint or [0.0, 0.0])
        for _ in range(16):
            nv = [list(v) for v in via]
            nv.insert(pos, clamp(layout, [seed[0] + rng.uniform(-2.6, 2.6),
                                          seed[1] + rng.uniform(-1.8, 1.8)]))
            out.append(nv)
    for j in range(len(via)):
        nv = [list(v) for v in via]
        nv.pop(j)
        out.append(nv)
    return out


def optimise(amp: str, iters: int = 3000, seed: int = 7, verbose=True,
             model: Model | None = None, budget_s: float = 900.0,
             hard_stall_limit: int = 350, cand_cap: int = 110,
             min_gain: float = 12.0):
    m = model or Model(amp)
    rng = random.Random(seed)
    print(f"{amp}: start hard={m.hard} soft={m.soft:.0f}")
    stall = 0
    margin_left = 0
    best_hard, best_score = m.hard, m.score
    hard_floor, hard_stall = m.hard, 0
    t0 = time.monotonic()
    snapshot = m.snapshot()
    for it in range(iters):
        # Phase 1 works only the runs the GATE names. Once it is green, phase 2
        # keeps going on the near-misses for a bounded while: a lead that clears
        # a lug by 5.1 px passes the lint and still reads as ambiguous.
        w = m.blame(hard_only=(m.hard > 0))
        if m.hard == 0:
            if margin_left == 0:
                margin_left = 420
                print(f"  gate green at it{it} — margin pass")
            margin_left -= 1
            if margin_left <= 0:
                break
        if not w:
            break
        ranked = sorted(w.items(), key=lambda kv: -kv[1])
        pool = [i for i, _ in ranked[:14]]
        ri = rng.choice(pool)
        if not m.plain[ri]:
            continue
        best = m.score
        hard_before = m.hard
        cands = candidates(m.layout, m.specs[ri], rng, m.midpoint_hint(ri))
        rng.shuffle(cands)
        improved = False
        # A move has to be worth making. Accepting sub-pixel gains lets the
        # search dither forever on a board this size instead of converging.
        gain = min_gain if m.hard == 0 else min_gain * 4
        for nv in cands[:cand_cap]:
            tok = m.reroute(ri, nv)
            if (m.legible(ri) and m.score < best - gain
                    and m.hard <= hard_before):
                improved = True
                break
            m.undo(tok)
        if m.hard < hard_floor:
            hard_floor, hard_stall = m.hard, 0
        else:
            hard_stall += 1
        if improved:
            stall = 0
            if verbose and m.hard <= 4:
                print(f"  it{it}: hard={m.hard} soft={m.soft:.0f} "
                      f"churn={m.churn:.0f}")
        else:
            stall += 1
            # Kick: a convergence cluster can sit in a local minimum where no
            # single lead improves alone. Take a sideways step on a culprit —
            # never one that opens a new finding — and let the descent resume.
            if stall % 55 == 0 and m.hard > 0:
                for nv in cands[:120]:
                    tok = m.reroute(ri, nv)
                    if m.legible(ri) and m.hard <= hard_before:
                        break
                    m.undo(tok)
        if m.hard < best_hard or (m.hard == best_hard and m.score < best_score):
            best_hard, best_score = m.hard, m.score
            snapshot = m.snapshot()
        if stall > 700 or hard_stall > hard_stall_limit \
                or time.monotonic() - t0 > budget_s:
            if verbose:
                print(f"  stopping at it{it}: stall={stall} "
                      f"hard_stall={hard_stall} "
                      f"elapsed={time.monotonic() - t0:.0f}s")
            break
    if snapshot is not None and (m.hard > best_hard
                                 or (m.hard == best_hard
                                     and m.score > best_score)):
        m.restore(snapshot)
    print(f"{amp}: end hard={m.hard} soft={m.soft:.0f} churn={m.churn:.0f}")
    return m


TIDY_SLACK = 500.0   # ~9 soft units — worth paying to keep the authored routing


def tidy(m: Model):
    """With the gate green, walk each edited run back toward its authored
    routing as far as it will go without re-opening a finding or measurably
    tightening a clearance. Keeps the committed diff to the leads that actually
    had to move, instead of every lead the search happened to touch."""
    ceiling = m.score_ceiling + TIDY_SLACK
    edited = [i for i in range(m.n)
              if (m.specs[i].get("via") or []) != m.orig_via[i]]
    for _pass in range(6):
        moved = False
        for i in edited:
            cur = [list(v) for v in (m.specs[i].get("via") or [])]
            orig = [list(v) for v in m.orig_via[i]]
            if cur == orig:
                continue
            tok = m.reroute(i, orig)          # all the way home?
            if m.hard == 0 and m.score <= ceiling:
                moved = True
                continue
            m.undo(tok)
            if len(cur) > len(orig):          # drop a waypoint the search added
                for j in range(len(cur)):
                    trimmed = cur[:j] + cur[j + 1:]
                    tok = m.reroute(i, trimmed)
                    if m.hard == 0 and m.score <= ceiling:
                        cur = trimmed
                        moved = True
                        break
                    m.undo(tok)
            if len(cur) != len(orig):
                continue
            for t in (0.85, 0.6, 0.35, 0.15):   # …or part of the way
                blend = [[round(c[0] + (o[0] - c[0]) * t, 3),
                          round(c[1] + (o[1] - c[1]) * t, 3)]
                         for c, o in zip(cur, orig)]
                tok = m.reroute(i, blend)
                if m.hard == 0 and m.score <= ceiling:
                    moved = True
                    break
                m.undo(tok)
        if not moved:
            break
    return m


KINK_DEG = 150.0     # a course change this sharp draws as a dead-end needle


def kinks(m: Model, i: int) -> int:
    """Near-reversals: the out-and-back that renders as a tapering stub with no
    terminus. `_turns` guards against ADDING one; this counts the ones already
    in the authored routing so they can be walked out."""
    pts = m.pts[i]
    if not pts or len(pts) < 3:
        return 0
    n = 0
    for k in range(1, len(pts) - 1):
        ax, ay = pts[k][0] - pts[k-1][0], pts[k][1] - pts[k-1][1]
        bx, by = pts[k+1][0] - pts[k][0], pts[k+1][1] - pts[k][1]
        na, nb = math.hypot(ax, ay), math.hypot(bx, by)
        if na < 1e-6 or nb < 1e-6:
            continue
        c = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
        if math.degrees(math.acos(c)) > KINK_DEG:
            n += 1
    return n


def unkink(m: Model, seed: int = 3, slack: float = 40000.0):
    """With the gate green, walk out the hairpins the authored routing carries.
    Never trades a finding for a tidier lead: any candidate that re-opens the
    gate is rejected outright."""
    rng = random.Random(seed)
    ceiling = m.score + slack
    for _pass in range(4):
        moved = False
        for i in range(m.n):
            if not m.plain[i]:
                continue
            k0 = kinks(m, i)
            if not k0:
                continue
            cands = candidates(m.layout, m.specs[i], rng, m.midpoint_hint(i))
            rng.shuffle(cands)
            for nv in cands[:220]:
                tok = m.reroute(i, nv)
                if (m.hard == 0 and kinks(m, i) < k0 and m.legible(i)
                        and m.score <= ceiling):
                    moved = True
                    break
                m.undo(tok)
        if not moved:
            break
    return sum(kinks(m, i) for i in range(m.n) if m.plain[i])


def margins(m: Model):
    """Smallest clearances left in the drawing — the gate's thresholds are 5.0 px
    (terminal) and 2.4 px over 8 px (near-parallel); report how much room the
    tightest case actually has."""
    worst_term = (999.0, None)
    worst_par = (0.0, None)
    for i in range(m.n):
        if not m.plain[i]:
            continue
        for j in range(m.n):
            if i == j or not m.plain[j]:
                continue
            pa, pb = m.pts[i], m.pts[j]
            for E in (pa[0], pa[-1]):
                if any(math.hypot(E[0] - v[0], E[1] - v[1]) < LINT_VERTEX_CLEAR
                       for v in pb):
                    continue
                d = min(_point_seg_dist(E, pb[sb], pb[sb + 1])
                        for sb in range(len(pb) - 1))
                if d < worst_term[0]:
                    worst_term = (d, f"run[{i}] end vs run[{j}]")
            if i < j:
                for sa in range(len(pa) - 1):
                    for sb in range(len(pb) - 1):
                        a1, a2, b1, b2 = pa[sa], pa[sa+1], pb[sb], pb[sb+1]
                        if _seg_angle_deg(a1, a2, b1, b2) >= LINT_ANGLE:
                            continue
                        ov = _parallel_overlap(a1, a2, b1, b2, LINT_SEP)
                        if ov and ov[0] > worst_par[0]:
                            worst_par = (ov[0], f"run[{i}] & run[{j}]")
    return worst_term, worst_par


# ---- writing back -----------------------------------------------------------
def fmt_num(v):
    r = round(float(v), 3)
    return str(int(round(r))) if abs(r - round(r)) < 1e-9 else f"{r:g}"


def fmt_val(v):
    if isinstance(v, list):
        return "[" + ", ".join(fmt_val(x) for x in v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return fmt_num(v)
    s = str(v)
    risky = (not s) or s[0].isdigit() or s[0] in "-[{,&*#?|>%@`\"'" \
        or ": " in s or s.endswith(":") or "," in s or "#" in s
    return '"' + s.replace('"', '\\"') + '"' if risky else s


KEY_ORDER = ["from", "to", "color", "style", "via"]


def run_line(spec, indent="  "):
    keys = [k for k in KEY_ORDER if k in spec] + \
           [k for k in spec if k not in KEY_ORDER]
    return f"{indent}- {{ " + ", ".join(
        f"{k}: {fmt_val(spec[k])}" for k in keys) + " }"


def write_back(amp: str, layout):
    p = ROOT / "amps" / amp / "layout.yaml"
    lines = p.read_text().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("runs:"))
    end = next(i for i in range(start + 1, len(lines))
               if lines[i] and not lines[i][0].isspace()
               and not lines[i].startswith("- "))
    seg = lines[start + 1:end]
    flow = [i for i, l in enumerate(seg) if l.startswith("  - {")]
    runs = layout["runs"]
    if len(flow) == len(runs):
        for n, li in enumerate(flow):
            seg[li] = run_line(runs[n])
    else:
        assert not any(l.lstrip().startswith("#") for l in seg), \
            "block-style runs section carries comments — refusing to re-emit"
        seg = [run_line(r) for r in runs]
    p.write_text("\n".join(lines[:start + 1] + seg + lines[end:]))


if __name__ == "__main__":
    amp = sys.argv[1]
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    m = optimise(amp, iters, seed)
    if m.hard == 0:
        m.score_ceiling = m.score
        tidy(m)
        changed = sum(1 for i in range(m.n)
                      if (m.specs[i].get("via") or []) != m.orig_via[i])
        wt, wp = margins(m)
        print(f"{amp}: tidied — soft={m.soft:.0f} churn={m.churn:.0f}, "
              f"{changed} run(s) re-routed")
        print(f"{amp}: tightest terminal clearance {wt[0]:.2f}px "
              f"(gate 5.0) {wt[1]}; worst near-parallel run {wp[0]:.1f}px "
              f"(gate 8.0) {wp[1]}")
        write_back(amp, m.layout)
        print("written")
    elif "--save-progress" in sys.argv:
        # Park the partial result so a follow-up run resumes from it instead of
        # starting over. Never leaves the repo like this: the next run has to
        # reach zero, and nothing is committed until check_layouts is green.
        write_back(amp, m.layout)
        print(f"partial written — {m.hard} hard finding(s) remain")
    else:
        print(f"NOT written — {m.hard} hard finding(s) remain")
