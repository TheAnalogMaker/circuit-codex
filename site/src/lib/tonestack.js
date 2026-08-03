// Tone-stack frequency response — the analytic model behind
// /reference/guides/tone-stack-lab/.
//
// The same module runs at build time (to render the page's default curve into
// static SVG) and in the browser (to redraw it as the sliders move), so the
// printed curve and the live curve can never disagree.
//
// METHOD. Each network is written as a list of two-terminal elements between
// numbered nodes, and solved by nodal analysis: one Kirchhoff current-law
// equation per unknown node, assembled into a complex nodal-admittance matrix
// Y·v = i and solved by Gauss–Jordan elimination with partial pivoting at every
// frequency of the sweep. A resistor of R Ω contributes admittance 1/R; a
// capacitor of C F contributes jωC. The driving stage is an ideal 1 V source
// behind its own output resistance, so |v(out)| is the level at the stack's
// output referred to that source — the driving stage's open-circuit signal, not
// the voltage that survives at the stack's own input node. The divider formed by
// the source resistance and the network is therefore inside every curve, which is
// what makes a plate-fed stack read about a decibel lower than a follower-fed one
// on otherwise identical parts.
//
// The solver was cross-checked against independent ngspice AC sweeps of the
// same element lists (10 Hz–100 kHz, 40 points/decade): the joined reference
// form, the ladder networks in both mid-leg forms (5F6/5F6-A three-knob,
// AA964/AB763 fixed-leg), and the 5F4's split network, each agree to within
// 5 × 10⁻⁵ dB worst-case.

export const GND = -1; // reference node
export const SRC = -2; // the ideal 1 V source behind the driving stage

// A pot never quite reaches 0 Ω of track, and a 0 Ω branch is a short the nodal
// matrix cannot represent. Half an ohm is far below any value in these networks
// and keeps an end-stopped control finite.
const R_FLOOR = 0.5;

const R = (a, b, v) => ({ k: 'R', a, b, v: Math.max(v, R_FLOOR) });
const C = (a, b, v) => ({ k: 'C', a, b, v });

// ---------------------------------------------------------------------------
// Complex helpers. Values are [re, im] pairs — small enough to keep allocation
// cheap across a 400-point sweep redrawn on every slider move.
const cAdd = (x, y) => [x[0] + y[0], x[1] + y[1]];
const cSub = (x, y) => [x[0] - y[0], x[1] - y[1]];
const cMul = (x, y) => [x[0] * y[0] - x[1] * y[1], x[0] * y[1] + x[1] * y[0]];
function cDiv(x, y) {
  const d = y[0] * y[0] + y[1] * y[1];
  return [(x[0] * y[0] + x[1] * y[1]) / d, (x[1] * y[0] - x[0] * y[1]) / d];
}
const cAbs = (x) => Math.hypot(x[0], x[1]);

// ---------------------------------------------------------------------------
// Solve one element list at one frequency and return the complex voltage at
// `out`, with the source held at 1 V. `n` is the number of unknown nodes
// (0 … n-1); GND and SRC are known and never get an equation of their own.
export function solveAt(elements, n, out, f) {
  const w = 2 * Math.PI * f;
  // Y (n×n) augmented with the injected-current column i (n×1).
  const Y = [];
  for (let r = 0; r < n; r++) {
    Y.push(new Array(2 * (n + 1)).fill(0));
  }
  const at = (r, c) => 2 * c; // column c starts at index 2c (re, im)

  const stamp = (a, b, y) => {
    // Standard two-terminal stamp: +y on both diagonals, −y on both off-diagonals.
    if (a >= 0) { Y[a][at(a, a)] += y[0]; Y[a][at(a, a) + 1] += y[1]; }
    if (b >= 0) { Y[b][at(b, b)] += y[0]; Y[b][at(b, b) + 1] += y[1]; }
    if (a >= 0 && b >= 0) {
      Y[a][at(a, b)] -= y[0]; Y[a][at(a, b) + 1] -= y[1];
      Y[b][at(b, a)] -= y[0]; Y[b][at(b, a) + 1] -= y[1];
    }
    // A branch to SRC injects y · 1 V into the node it lands on.
    if (a === SRC && b >= 0) { Y[b][at(b, n)] += y[0]; Y[b][at(b, n) + 1] += y[1]; }
    if (b === SRC && a >= 0) { Y[a][at(a, n)] += y[0]; Y[a][at(a, n) + 1] += y[1]; }
  };

  for (const e of elements) {
    if (e.k === 'R') stamp(e.a, e.b, [1 / e.v, 0]);
    else if (e.v > 0) stamp(e.a, e.b, [0, w * e.v]);
  }

  // Gauss–Jordan with partial pivoting.
  for (let col = 0; col < n; col++) {
    let piv = col, best = -1;
    for (let r = col; r < n; r++) {
      const mag = Math.hypot(Y[r][2 * col], Y[r][2 * col + 1]);
      if (mag > best) { best = mag; piv = r; }
    }
    if (best === 0) return [0, 0];
    if (piv !== col) { const t = Y[piv]; Y[piv] = Y[col]; Y[col] = t; }
    const d = [Y[col][2 * col], Y[col][2 * col + 1]];
    for (let c = col; c <= n; c++) {
      const q = cDiv([Y[col][2 * c], Y[col][2 * c + 1]], d);
      Y[col][2 * c] = q[0]; Y[col][2 * c + 1] = q[1];
    }
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const fct = [Y[r][2 * col], Y[r][2 * col + 1]];
      if (fct[0] === 0 && fct[1] === 0) continue;
      for (let c = col; c <= n; c++) {
        const v = cSub([Y[r][2 * c], Y[r][2 * c + 1]],
          cMul(fct, [Y[col][2 * c], Y[col][2 * c + 1]]));
        Y[r][2 * c] = v[0]; Y[r][2 * c + 1] = v[1];
      }
    }
  }
  return [Y[out][2 * n], Y[out][2 * n + 1]];
}

// ---------------------------------------------------------------------------
// The networks.
//
// The three-knob and two-knob stacks exist in TWO wirings, and each preset
// declares which one its schematic draws (`wiring` in TONE_STACK_SPECS):
//
//   'ladder' — what the published Fender 5F6 and 5F6-A, Marshall JTM45/1987/
//     1959 and blackface AA964 sheets actually draw. The treble pot's lower
//     lug sits on the FAR side of the bass capacitor; the bass pot is a
//     rheostat (wiper strapped to an end lug) in series down the ladder; the
//     stack's output is the treble wiper ALONE; and on the three-knob
//     circuits the mid capacitor feeds the MIDDLE POT'S WIPER, so the mid
//     control slides the injection point along a fixed 25 kΩ leg instead of
//     shrinking the leg itself.
//
//   'joined' — the textbook idealisation of the same parts (Duncan-style
//     "FMV"): treble lower lug on the slope foot, treble and bass wipers
//     joined at one output node, mid capacitor on the top of a rheostat-wired
//     mid leg. Kept as the textbook reference form; as of the 2026-08-03
//     re-reading of the published drawings, no preset's own sheet draws it.
//
//   'split' — a different network again: the tweed 5F4's tone circuit
//     (splitStackElements below), in which treble and bass ride two separate
//     branches recombined at the output. It shares no slope resistor and no
//     cap ladder with the stacks above.
//
// (1) The 'joined' three-knob stack. Node numbering, following the signal:
//
//        IN   0   stack input (cathode-follower cathode, or a plate)
//        N2   1   slope-resistor foot · treble-pot CCW lug · bass and mid caps
//        N3   2   treble-cap output · treble-pot CW lug
//        OUT  3   treble-pot wiper AND bass-pot wiper — the stack's output
//        N4   4   bass-cap output · bass-pot CW lug
//        N5   5   bass-pot CCW lug · top of the mid leg
//
//     Kirchhoff's current law at each unknown node. The stack input is an unknown
//     of its own: the 1 V source sits behind Rsource, so V0 is what the driving
//     stage actually delivers into the network, not the source's 1 V. With
//     Ysrc = 1/Rsource, Ys = 1/Rslope, Yt1 = 1/(Rt(1−t)), Yt2 = 1/(Rt·t),
//     Yb1 = 1/(Rb(1−b)), Yb2 = 1/(Rb·b), Ym = 1/(Rm·m + Rfixed) and Y = jωC for
//     each capacitor:
//
//       IN :  Ysrc(V0−1) + Ys(V0−V2) + Yc1(V0−V3)                         = 0
//       N2 :  Ys(V2−V0) + Yt2(V2−Vo) + Yc2(V2−V4) + Yc3(V2−V5)            = 0
//       N3 :  Yc1(V3−V0) + Yt1(V3−Vo)                                     = 0
//       OUT:  Yt1(Vo−V3) + Yt2(Vo−V2) + Yb1(Vo−V4) + Yb2(Vo−V5) + Yl·Vo   = 0
//       N4 :  Yc2(V4−V2) + Yb1(V4−Vo)                                     = 0
//       N5 :  Yc3(V5−V2) + Yb2(V5−Vo) + Ym·V5                             = 0
//
//     Setting Rsource to zero collapses the first equation to V0 = 1 and recovers
//     the textbook five-node form.
//
//     A control at 10 puts its wiper at the "more of this" end: treble 10 ties
//     the output straight to the treble cap, bass 10 ties it straight to the
//     bass cap.
//
// (2) The two-knob stack is the same network with the mid pot replaced by a
//     fixed resistor to ground (6.8 kΩ on the blackface circuit) or by a direct
//     ground (the tweed two-knob stack), and with no mid capacitor.
//
// (3) The single-knob tweed tone control is a different animal entirely — see
//     trebleCutElements below.
export function stackElements(p, pos) {
  if (p.wiring === 'ladder') return ladderStackElements(p, pos);
  if (p.wiring === 'split') return splitStackElements(p, pos);
  return joinedStackElements(p, pos);
}

// The 'split' network — the tweed 5F4's tone circuit as its C-EG sheet draws
// it. Treble and bass are two separate branches off the cathode follower,
// recombined at the output node:
//
//    IN   0   stack input (the cathode follower's cathode)
//    N2   1   bass branch behind its 0.1 µF coupler: a 220 kΩ leak to ground
//             and a 100 kΩ series resistor onward (the amp's 4.7 MΩ feedback
//             resistor also returns to this node — outside this network)
//    N3   2   treble-cap output · treble-pot hot end
//    OUT  3   treble-pot wiper · the bass branch's 220 kΩ series resistor ·
//             the next stage's grid
//    W    4   the bass pot's WIPER — the branch injects here, not at an end
//    N5   5   treble-pot cold end · 0.01 µF to ground
//    N6   6   bass-pot end lug · 0.005 µF to ground (the opposite end lug is
//             grounded outright)
//
// Treble 10 puts the wiper on the capacitor end of its track; bass 10 puts
// the wiper on the 0.005 µF end, leaving the whole track in series with the
// grounded lug so the branch is loaded least.
function splitStackElements(p, pos) {
  const t = clamp01(pos.treble);
  const b = clamp01(pos.bass);
  const els = [
    R(SRC, 0, p.rSource),
    C(0, 2, p.trebleCap),
    R(2, 3, p.treblePot * (1 - t)),
    R(3, 5, p.treblePot * t),
    C(5, GND, p.trebleShuntCap),
    C(0, 1, p.bassCoupler),
    R(1, GND, p.bassShunt),
    R(1, 4, p.bassSeries),
    R(4, 6, p.bassPot * (1 - b)),
    C(6, GND, p.bassLegCap),
    R(4, GND, p.bassPot * b),
    R(4, 3, p.outSeries),
  ];
  if (p.rLoad) els.push(R(3, GND, p.rLoad));
  return els;
}

// The 'ladder' wiring — the network the published sheets draw. Nodes:
//
//    IN   0   stack input (cathode-follower cathode, or a plate)
//    N2   1   slope-resistor foot · bass cap · mid cap
//    N3   2   treble-cap output · treble-pot CW lug
//    OUT  3   treble-pot WIPER — the stack's output, alone
//    N4   4   bass-cap output · treble-pot CCW lug · bass-rheostat hot end
//    N5   5   bass-rheostat foot · top of the mid leg
//    M    6   the mid pot's wiper, where the mid cap lands (three-knob only)
//
//   IN :  Ysrc(V0−1) + Ys(V0−V2... as stamped)                      per KCL
//   N2 :  slope + bass cap + mid cap
//   N3 :  treble cap + upper treble track
//   OUT:  upper treble track + lower treble track + load
//   N4 :  lower treble track + bass cap + bass rheostat
//   N5 :  bass rheostat + upper mid track
//   M  :  upper mid track + lower mid track + mid cap
//
// The bass control is the fraction of the 1 MΩ track left in series between
// N4 and N5 (bass 10 = the whole track). The mid control slides the wiper —
// and with it the mid cap's injection point — along the fixed mid leg
// (mid 10 = wiper at the top, the full leg below the injection). On the
// two-knob blackface wiring the mid cap lands on N5 itself and the leg is the
// fixed bleed resistor. On the 5F6 the leg returns to ground through the 5 kΩ
// presence pot; the preset plots Presence at the end of its travel that leaves
// no resistance in the leg, and says so.
function ladderStackElements(p, pos) {
  const t = clamp01(pos.treble);
  const b = clamp01(pos.bass);
  const m = clamp01(pos.mid);
  const els = [
    R(SRC, 0, p.rSource),
    R(0, 1, p.slope),
    C(0, 2, p.trebleCap),
    R(2, 3, p.treblePot * (1 - t)),
    R(3, 4, p.treblePot * t),
    C(1, 4, p.bassCap),
    R(4, 5, p.bassPot * b),
  ];
  if (p.midPot) {
    els.push(R(5, 6, p.midPot * (1 - m)));
    els.push(R(6, GND, p.midPot * m));
    if (p.midCap) els.push(C(1, 6, p.midCap));
  } else {
    els.push(R(5, GND, p.midFixed || 0));
    if (p.midCap) els.push(C(1, 5, p.midCap));
  }
  if (p.rLoad) els.push(R(3, GND, p.rLoad));
  return els;
}

function joinedStackElements(p, pos) {
  const t = clamp01(pos.treble);
  const b = clamp01(pos.bass);
  const m = clamp01(pos.mid);
  const els = [
    R(SRC, 0, p.rSource),
    R(0, 1, p.slope),
    C(0, 2, p.trebleCap),
    R(2, 3, p.treblePot * (1 - t)),
    R(3, 1, p.treblePot * t),
    C(1, 4, p.bassCap),
    R(4, 3, p.bassPot * (1 - b)),
    R(3, 5, p.bassPot * b),
    R(5, GND, (p.midPot || 0) * m + (p.midFixed || 0)),
  ];
  if (p.midCap) els.push(C(1, 5, p.midCap));
  if (p.rLoad) els.push(R(3, GND, p.rLoad));
  return els;
}

// The single-knob tweed tone control: the pot is wired as a rheostat in series
// with a small capacitor, straight from the signal node to ground — a variable
// treble bleed rather than a divider. Only two nodes exist:
//
//        S  0   signal node = the stack's output, loaded by the volume pot
//        1      junction of the tone rheostat and the cut capacitor
//
//       S :  Ysrc(Vs−Vin) + Yr(Vs−V1) + Yl·Vs = 0
//       1 :  Yr(V1−Vs) + Yc·V1              = 0
//
// Tone at 10 leaves the whole track in circuit (least bleed, brightest); tone
// at 0 shorts the capacitor straight across the signal.
export function trebleCutElements(p, pos) {
  const k = clamp01(pos.tone);
  return [
    R(SRC, 0, p.rSource),
    R(0, 1, p.tonePot * k),
    C(1, GND, p.cutCap),
    R(0, GND, p.rLoad),
  ];
}

function clamp01(x) {
  return Math.min(1, Math.max(0, Number.isFinite(x) ? x : 0));
}

// Element list + unknown-node count + output node for whichever network a
// preset describes.
export function networkFor(preset, pos) {
  if (preset.kind === 'single-knob') {
    return { els: trebleCutElements(preset.parts, pos), n: 2, out: 0 };
  }
  // The ladder wiring's mid wiper — and the split network's second treble
  // node — are a seventh node beyond the joined form's six.
  const n = preset.parts.wiring === 'split'
    || (preset.parts.wiring === 'ladder' && preset.parts.midPot) ? 7 : 6;
  return { els: stackElements(preset.parts, pos), n, out: 3 };
}

// Magnitude response in dB at one frequency.
export function responseDb(preset, pos, f) {
  const { els, n, out } = networkFor(preset, pos);
  const v = cAbs(solveAt(els, n, out, f));
  return v > 0 ? 20 * Math.log10(v) : -Infinity;
}

// ---------------------------------------------------------------------------
// Sweep helpers. The plot runs 10 Hz to 100 kHz on a log axis — four decades,
// wide enough to show both ends of the network's behaviour asymptote out.
export const F_MIN = 10;
export const F_MAX = 1e5;

export function sweepFrequencies(points = 361) {
  const out = new Array(points);
  const lo = Math.log10(F_MIN), hi = Math.log10(F_MAX);
  for (let i = 0; i < points; i++) out[i] = 10 ** (lo + (hi - lo) * (i / (points - 1)));
  return out;
}

export function sweep(preset, pos, freqs = sweepFrequencies()) {
  const { els, n, out } = networkFor(preset, pos);
  return freqs.map((f) => {
    const v = cAbs(solveAt(els, n, out, f));
    return v > 0 ? 20 * Math.log10(v) : -999;
  });
}

// The deepest point of the response and where it sits, plus the level at three
// reading frequencies — the numbers the page's readout quotes.
export function summarise(preset, pos) {
  const freqs = sweepFrequencies(721);
  const db = sweep(preset, pos, freqs);
  let iMin = 0;
  for (let i = 1; i < db.length; i++) if (db[i] < db[iMin]) iMin = i;
  return {
    minDb: db[iMin],
    minHz: freqs[iMin],
    interior: iMin > 0 && iMin < db.length - 1,
    at100: responseDb(preset, pos, 100),
    at1k: responseDb(preset, pos, 1000),
    at5k: responseDb(preset, pos, 5000),
  };
}

// Positions a preset opens at: every control at 5 on a 0–10 dial.
export function midPositions() {
  return { treble: 0.5, mid: 0.5, bass: 0.5, tone: 0.5 };
}

// The reference curve every plot draws behind the live one: every control at 10.
export function maxPositions() {
  return { treble: 1, mid: 1, bass: 1, tone: 1 };
}

// ---------------------------------------------------------------------------
// Plot geometry, shared by the build-time render and the live redraw so the
// static curve and the interactive one are drawn by the same code.
export const PLOT = {
  w: 740, h: 380,
  pad: { l: 58, r: 24, t: 20, b: 48 },
  dbTop: 6, dbBottom: -48,
};
const PW = PLOT.w - PLOT.pad.l - PLOT.pad.r;
const PH = PLOT.h - PLOT.pad.t - PLOT.pad.b;
const LOG_MIN = Math.log10(F_MIN);
const LOG_SPAN = Math.log10(F_MAX) - LOG_MIN;

export const plotX = (f) => PLOT.pad.l + ((Math.log10(f) - LOG_MIN) / LOG_SPAN) * PW;
export const plotY = (db) => PLOT.pad.t +
  ((PLOT.dbTop - Math.min(PLOT.dbTop, Math.max(PLOT.dbBottom, db))) /
    (PLOT.dbTop - PLOT.dbBottom)) * PH;
export const plotF = (x) => 10 ** (LOG_MIN + ((x - PLOT.pad.l) / PW) * LOG_SPAN);

// One SVG path for a set of control positions. Everything below the axis floor
// is drawn flat along the floor rather than off-canvas — an FMV stack with bass
// and middle both at zero really does put its output on the ground, and the
// page says so in words rather than drawing a line into space.
export function curvePath(preset, pos, freqs = sweepFrequencies()) {
  const db = sweep(preset, pos, freqs);
  let d = '';
  for (let i = 0; i < freqs.length; i++) {
    d += `${i ? 'L' : 'M'}${plotX(freqs[i]).toFixed(1)},${plotY(db[i]).toFixed(1)}`;
  }
  return d;
}

// Decade gridlines, plus the 2×, 3× and 5× minor lines inside each decade.
export function gridFrequencies() {
  const major = [], minor = [];
  for (let d = 1; d <= 5; d++) {
    const base = 10 ** d;
    major.push(base);
    if (d < 5) for (const k of [2, 3, 5]) minor.push(base * k);
  }
  return { major, minor };
}

export function dbGridLines() {
  const out = [];
  for (let db = PLOT.dbTop; db >= PLOT.dbBottom; db -= 6) out.push(db);
  return out;
}

export function hzLabel(f) {
  return f >= 1000 ? `${f / 1000} k` : `${f}`;
}

// Direct labels instead of a legend box: each curve is named where the two are
// furthest apart, with the label placed on the outside of its own curve so it
// crosses neither. Kept inside the middle of the plot so a right-anchored label
// cannot run off the edge, and quantised to a coarse grid so it does not jitter
// while a control is being dragged.
export function labelPlacement(preset, live, ref) {
  const freqs = sweepFrequencies(97);
  const a = sweep(preset, live, freqs);
  const b = sweep(preset, ref, freqs);
  const lo = Math.round(freqs.length * 0.16), hi = Math.round(freqs.length * 0.86);
  let best = lo;
  for (let i = lo; i <= hi; i++) if (Math.abs(a[i] - b[i]) > Math.abs(a[best] - b[best])) best = i;
  const x = plotX(freqs[best]);
  const inset = PLOT.pad.l + (PLOT.w - PLOT.pad.l - PLOT.pad.r) * 0.55;
  const anchor = x > inset ? 'end' : 'start';
  const top = PLOT.pad.t + 14;
  const bottom = PLOT.h - PLOT.pad.b - 6;
  const clamp = (y) => Math.min(bottom, Math.max(top, y));
  const above = a[best] >= b[best];
  return {
    x: x + (anchor === 'end' ? -6 : 6),
    anchor,
    yLive: clamp(plotY(a[best]) + (above ? -10 : 19)),
    yRef: clamp(plotY(b[best]) + (above ? 19 : -10)),
  };
}
