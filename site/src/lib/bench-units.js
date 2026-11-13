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
    .replace(/\s+/g, '')
    // Tube-era drawings letter a megohm "MEG." (1 MEG., 2.2 Meg) — the same
    // megohm as a bare M, and read as one.
    .replace(/meg\.?$/, 'm');
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
// or "MF" (see the units guide), and a picofarad "MMF" or "µµF" — a
// micro-microfarad. "0.02mfd", ".02 MF" and "25 MFD" are microfarads, not a
// milli prefix with stray letters: no amplifier part is sized in millifarads,
// and reading ".02 MF" as 20 mF once put a coupling-cap corner at 0.008 Hz.
// A bare "22m" (no F at all) stays 22 mF, the SI reading of the prefix alone.
export function farads(v) {
  if (v == null) return null;
  let s = String(v).trim().toLowerCase().replace(/farads?/g, '').replace(/\s+/g, '');
  if (s === '') return null;
  const pico = s.match(/^(\d*\.?\d+)(µµ|uu|mm)fd?\.?$/);
  if (pico) return parseFloat(pico[1]) * 1e-12;
  const mfd = s.match(/^(\d*\.?\d+)(µ|u|m)fd?\.?$/);
  if (mfd) return parseFloat(mfd[1]) * 1e-6;
  s = s.replace(/f$/, '');
  if (s === '') return null;
  const suf = { p: 1e-12, n: 1e-9, u: 1e-6, 'µ': 1e-6, m: 1e-3 };
  const m = s.match(/^(\d*\.?\d+)([pnuµm]?)$/);
  if (!m) return null;
  return parseFloat(m[1]) * (m[2] ? suf[m[2]] : 1e-6);
}

// A plain number, read strictly. parseFloat() takes the longest numeric prefix,
// so "1,000" came back as 1 and "12abc" as 12 — a wrong answer printed as if it
// were right. A field either holds a whole number or it is unreadable; the
// minus sign the pages print (U+2212) reads as a minus.
export function number(v) {
  if (v == null) return null;
  const s = String(v).trim().replace(/\u2212/g, '-');
  if (s === '') return null;
  if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
