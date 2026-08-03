// Koren plate-current maths for the load-line explorer.
//
// These are the same equations the corpus's CC0 model files hand to ngspice —
// transcribed, not re-derived. A 6V6GT .inc line reads
//
//   Bp P K I=pow(uramp((V(G2,K)/KP)*ln(1+exp(KP*(1/MU+V(G1,K)/V(G2,K))))),EX)/KG1*atan(V(P,K)/KVB)
//   Bg2 G2 K I=pow(uramp(V(G2,K)/MU+V(G1,K)),EX)/KG2
//
// and `plateCurrent` below evaluates exactly that, on parameters parsed out of the
// same file at build time. A circuit solved here therefore has to land on the same
// operating point ngspice reports for the corresponding amps/<id>/netlist.cir; the
// explorer prints both numbers so the agreement is visible rather than asserted.
//
// Units in this module are SI at the boundary — volts, ohms, amps — except where a
// name says otherwise. Model equations: N. Koren, "Improved vacuum-tube models for
// SPICE simulations", Glass Audio 8(5), 1996 (published methodology).

/** ln(1 + e^z), overflow-safe — ngspice evaluates ln(1+exp(z)) in doubles. */
export function softplus(z) {
  if (z > 30) return z;
  if (z < -30) return Math.exp(z);
  return Math.log1p(Math.exp(z));
}

/** SPICE uramp(): the positive part of x. */
const uramp = (x) => (x > 0 ? x : 0);

/**
 * Plate and screen current for one tube, in amps.
 * @param {object} model  parsed .inc model: { kind, params:{mu,ex,kg1,kg2,kp,kvb} }
 * @param {number} vpk    plate-to-cathode volts
 * @param {number} vg1k   control-grid-to-cathode volts (negative in normal bias)
 * @param {number} vg2k   screen-to-cathode volts (pentodes only)
 */
export function plateCurrent(model, vpk, vg1k, vg2k) {
  const { mu, ex, kg1, kg2, kp, kvb } = model.params;
  if (model.kind === 'pentode') {
    // A screen below its cathode has no emission to control and the model's
    // vg1/vg2 ratio is undefined there — the tube is simply off.
    if (!(vg2k > 0)) return { ip: 0, ig2: 0 };
    const e1 = (vg2k / kp) * softplus(kp * (1 / mu + vg1k / vg2k));
    const ip = (Math.pow(uramp(e1), ex) / kg1) * Math.atan(vpk / kvb);
    const ig2 = Math.pow(uramp(vg2k / mu + vg1k), ex) / kg2;
    return { ip: ip > 0 ? ip : 0, ig2 };
  }
  const e1 = (vpk / kp) * softplus(kp * (1 / mu + vg1k / Math.sqrt(kvb + vpk * vpk)));
  return { ip: Math.pow(uramp(e1), ex) / kg1, ig2: 0 };
}

/**
 * Plate current with a resistance in the plate circuit, solved self-consistently:
 * the plate load drops voltage in proportion to the current it is carrying, so
 * ip and vpk have to be found together.
 */
function plateCurrentIntoLoad(model, vSupply, ra, vg1k, vg2k) {
  if (!(ra > 0)) {
    const r = plateCurrent(model, vSupply, vg1k, vg2k);
    return { ...r, vpk: vSupply };
  }
  // f(ip) = Ip(vSupply - ip·ra) - ip is strictly decreasing: bisect it.
  let lo = 0;
  let hi = Math.max(vSupply, 0) / ra;
  for (let i = 0; i < 90; i++) {
    const mid = 0.5 * (lo + hi);
    const { ip } = plateCurrent(model, vSupply - mid * ra, vg1k, vg2k);
    if (ip > mid) lo = mid; else hi = mid;
  }
  const ip = 0.5 * (lo + hi);
  const vpk = vSupply - ip * ra;
  const { ig2 } = plateCurrent(model, vpk, vg1k, vg2k);
  return { ip, ig2, vpk };
}

/**
 * Solve one tube's DC operating point.
 *
 * @param {object}  o
 * @param {object}  o.model      parsed model
 * @param {number}  o.bplus      plate supply, volts to ground
 * @param {number}  o.ra         DC resistance in the plate circuit, ohms
 *                               (a resistive plate load, or an output transformer's
 *                               winding resistance — 0 for an ideal transformer)
 * @param {number}  o.rk         cathode resistor seen by THIS tube, ohms (0 = cathode
 *                               grounded). A resistor shared by n bottles is n·R per tube.
 * @param {number}  o.vgSupply   grid supply volts to ground (0 for cathode bias,
 *                               negative for a fixed-bias supply)
 * @param {number}  o.vg2Supply  screen supply volts to ground (pentodes)
 * @returns operating point in volts, amps and watts
 */
export function solveOperatingPoint(o) {
  const { model, bplus, ra = 0, rk = 0, vgSupply = 0, vg2Supply = 0 } = o;
  const at = (vk) => {
    const vg1k = vgSupply - vk;
    const vg2k = (model.kind === 'pentode' ? vg2Supply : 0) - vk;
    const r = plateCurrentIntoLoad(model, bplus - vk, ra, vg1k, vg2k);
    return { ...r, vk, vg1k, vg2k, ik: r.ip + r.ig2 };
  };

  let pt;
  if (!(rk > 0)) {
    pt = at(0);
  } else {
    // g(vk) = Ik(vk)·Rk − vk falls monotonically: more cathode volts means a more
    // negative grid and a lower screen, so less current, while −vk falls too.
    let lo = 0;
    let hi = Math.max(bplus, 1);
    for (let i = 0; i < 120; i++) {
      const mid = 0.5 * (lo + hi);
      if (at(mid).ik * rk > mid) lo = mid; else hi = mid;
    }
    pt = at(0.5 * (lo + hi));
  }

  // Small-signal figures, by central difference on the same equations.
  const d = 0.05;
  const gm = (plateCurrent(model, pt.vpk, pt.vg1k + d, pt.vg2k).ip
    - plateCurrent(model, pt.vpk, pt.vg1k - d, pt.vg2k).ip) / (2 * d);
  const dv = Math.max(1, Math.abs(pt.vpk) * 0.01);
  const dip = (plateCurrent(model, pt.vpk + dv, pt.vg1k, pt.vg2k).ip
    - plateCurrent(model, pt.vpk - dv, pt.vg1k, pt.vg2k).ip) / (2 * dv);
  const rp = dip > 0 ? 1 / dip : Infinity;

  return {
    ...pt,
    pa: pt.vpk * pt.ip,
    pg2: pt.vg2k * pt.ig2,
    gm,
    rp,
    muEff: isFinite(rp) ? gm * rp : Infinity,
    // Cathode current runs a little ahead of plate current in a pentode because the
    // screen current comes home the same way; this ratio tilts the DC load line.
    kRatio: pt.ip > 0 ? pt.ik / pt.ip : 1,
  };
}

/**
 * One constant-Vg1 plate curve, as [{v, i}] points in volts and amps.
 * Sampled densely near the knee, where the curve turns hardest.
 */
export function plateCurve(model, vg1k, vg2k, vMax, n = 220) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    // Square spacing puts most samples in the first fifth of the axis.
    const t = i / n;
    const v = vMax * t * t;
    const { ip } = plateCurrent(model, v, vg1k, vg2k);
    pts.push({ v, i: ip });
  }
  return pts;
}

/** A "nice" step (1, 2, 2.5, 5 × 10^k) at or just above `raw`. */
export function niceStep(raw) {
  if (!(raw > 0)) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const mult = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
  return mult * mag;
}

/**
 * The grid-voltage steps to draw, chosen so the family spans zero bias down to
 * roughly cut-off for this tube at this supply — the range a real datasheet plots.
 */
export function gridSteps(model, { bplus, vg2k }) {
  const { mu } = model.params;
  const span = model.kind === 'pentode'
    ? Math.max(vg2k, 1) / mu * 1.35
    : Math.max(bplus, 1) / mu * 1.2;
  const step = niceStep(span / 9);
  const steps = [];
  for (let k = 0; k * step <= span + 1e-9 && steps.length < 18; k++) steps.push(-k * step);
  return { step, steps };
}

/**
 * Graphical class-A power estimate for a single-ended stage: swing the grid
 * symmetrically about the operating point along the AC load line, out to zero bias,
 * and take the textbook (Vmax − Vmin)(Imax − Imin) / 8.
 * Returns null when the swing cannot be constructed.
 */
export function seOutputEstimate(model, q, zac) {
  if (!(zac > 0) || !(q.ip > 0)) return null;
  const drive = Math.abs(q.vg1k);          // grid swing to zero bias
  if (!(drive > 0)) return null;
  // Intersections of the AC load line (through Q, slope −1/zac) with the two
  // extreme grid curves. Solve ip = Ip(vQ + (iQ − ip)·zac) by bisection.
  const along = (vg1k) => {
    let lo = 0;
    let hi = q.ip + (q.vpk / zac);
    for (let i = 0; i < 80; i++) {
      const mid = 0.5 * (lo + hi);
      const v = q.vpk + (q.ip - mid) * zac;
      const { ip } = plateCurrent(model, v, vg1k, q.vg2k);
      if (ip > mid) lo = mid; else hi = mid;
    }
    const ip = 0.5 * (lo + hi);
    return { ip, v: q.vpk + (q.ip - ip) * zac };
  };
  const top = along(q.vg1k + drive);       // toward zero bias — more current, less volts
  const bot = along(q.vg1k - drive);       // equally far the other way
  // The two intersections run in opposite directions on the two axes, so take the
  // magnitude of each excursion rather than the signed difference.
  const po = Math.abs((top.v - bot.v) * (top.ip - bot.ip)) / 8;
  if (!(po > 0)) return null;
  return { po, drive, top, bot };
}
