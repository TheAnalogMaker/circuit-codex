// The "enter any two" logic behind the Ohm's-law and output-transformer
// calculators, kept out of the page so it can be tested without a browser.
//
// Each calculator keeps an ORDER: the fields the reader has typed in, most
// recent first. The first two readable fields in that order drive the sum and
// every other field is written with the answer.
//
// Two rules keep a written answer from landing on top of the reader's typing:
//
//   1. A field the reader empties leaves the order. It was a driver; empty, it
//      drives nothing, and it becomes a field the answer may fill.
//   2. The field being edited is never written, even when it is not a driver.
//      Backspacing "250" to nothing used to refill the box with the value the
//      other two implied (say "2"), and the "300" typed next became "2300" —
//      a silent wrong voltage and a wrong resistor-wattage figure beside it.

/** Move `key` to the front of `order`, or drop it when its field is empty. */
export function touch(order, key, empty) {
  const next = order.filter((k) => k !== key);
  if (!empty) next.unshift(key);
  return next;
}

/** Ohm's law from any two of V (volts), I (amps), R (ohms), P (watts). */
export function solveOhm(K) {
  let V = K.V ?? null, I = K.I ?? null, R = K.R ?? null, P = K.P ?? null;
  if (V != null && I != null) { R = V / I; P = V * I; }
  else if (V != null && R != null) { I = V / R; P = V * V / R; }
  else if (V != null && P != null) { I = P / V; R = V * V / P; }
  else if (I != null && R != null) { V = I * R; P = I * I * R; }
  else if (I != null && P != null) { V = P / I; R = P / (I * I); }
  else if (R != null && P != null) { V = Math.sqrt(P * R); I = Math.sqrt(P / R); }
  return { V, I, R, P };
}

/**
 * Plan one Ohm's-law update. `values` holds SI numbers (null when blank or
 * unreadable); `editing` is the key of the field with focus, if any.
 * Returns the driving pair and the fields to write — never the edited one.
 */
export function ohmPlan(order, values, editing) {
  const keys = ['V', 'I', 'R', 'P'];
  const valid = order.filter((k) => values[k] != null && Number.isFinite(values[k]));
  if (valid.length < 2) return { use: valid, writes: {} };
  const use = valid.slice(0, 2);
  const K = {};
  use.forEach((k) => { K[k] = values[k]; });
  const r = solveOhm(K);
  const writes = {};
  for (const k of keys) {
    if (use.includes(k) || k === editing) continue;
    writes[k] = r[k] != null && Number.isFinite(r[k]) ? r[k] : null;
  }
  return { use, writes };
}

/**
 * Plan one output-transformer update from any two of Zp, Zs (ohms) and the
 * turns ratio N. Returns { N, Zp, Zs, target, write } where `write` is false
 * when the field the answer belongs in is the one being edited.
 */
export function otPlan(order, values, editing) {
  const valid = order.filter((k) => values[k] != null && Number.isFinite(values[k]) && values[k] > 0);
  if (valid.length < 2) return null;
  const drv = valid.slice(0, 2);
  let Zp = drv.includes('Zp') ? values.Zp : null;
  let Zs = drv.includes('Zs') ? values.Zs : null;
  let N = drv.includes('N') ? values.N : null;
  if (Zp != null && Zs != null) N = Math.sqrt(Zp / Zs);
  else if (Zp != null && N != null) Zs = Zp / (N * N);
  else if (Zs != null && N != null) Zp = Zs * N * N;
  const target = ['Zp', 'Zs', 'N'].find((k) => !drv.includes(k));
  return { N, Zp, Zs, target, write: target !== editing };
}
