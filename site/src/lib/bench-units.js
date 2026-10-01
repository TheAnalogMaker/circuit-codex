// Shared readers for the bench tools (calculators, resistor color code).
// One parser so "4k7" and "0.02mfd" mean the same thing on every page.
// House unit style is documented on /reference/guides/units-conventions/.

// Resistor shorthand. The unit letter replaces the decimal point (4k7 = 4.7 kΩ),
// and a trailing M is megohms — the notation guitar resistors are lettered in.
// A sign is not part of that shorthand: "−100k" is unreadable, not −100 kΩ.
export function ohms(v) {
  if (v == null) return null;
  // Strip the unit before lowercasing. The pages print U+03A9 (and a typed
  // ohm sign U+2126 folds to U+03C9), so a replace that runs after toLowerCase
  // never sees the glyph it was written to remove and "100Ω" fails to parse.
  const s = String(v).trim()
    .replace(/[\u03A9\u03C9\u2126]/g, '')
    .toLowerCase()
    .replace(/ohms?/g, '')
    .replace(/\s+/g, '');
  if (s === '') return null;
  const mult = { r: 1, k: 1e3, m: 1e6 };
  let m = s.match(/^(\d*)([rkm])(\d+)$/);
  if (m) return parseFloat((m[1] || '0') + '.' + m[3]) * mult[m[2]];
  m = s.match(/^(\d*\.?\d+)([rkm]?)$/);
  if (m) return parseFloat(m[1]) * (m[2] ? mult[m[2]] : 1);
  return null;
}

// Capacitance. No suffix means microfarads, which is what the calculator's
// own field is labelled in and what a bare "0.02" means on these drawings.
// p/n/u/µ are the SI prefixes; a bare m is millifarads.
//
// Tube-era drawings do not use the µ symbol. They letter a microfarad "MFD"
// (see the units guide). "0.02mfd" and "25 MFD" are that word, not a milli
// prefix with stray letters — bare "22m" stays 22 mF so the two cannot collapse.
export function farads(v) {
  if (v == null) return null;
  let s = String(v).trim().toLowerCase().replace(/farads?/g, '').replace(/\s+/g, '');
  if (s === '') return null;
  const mfd = s.match(/^(\d*\.?\d+)(µ|u|m)fd\.?$/);
  if (mfd) return parseFloat(mfd[1]) * 1e-6;
  s = s.replace(/f$/, '');
  if (s === '') return null;
  const suf = { p: 1e-12, n: 1e-9, u: 1e-6, 'µ': 1e-6, m: 1e-3 };
  const m = s.match(/^(\d*\.?\d+)([pnuµm]?)$/);
  if (!m) return null;
  return parseFloat(m[1]) * (m[2] ? suf[m[2]] : 1e-6);
}
