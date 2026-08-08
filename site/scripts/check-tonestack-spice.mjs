// Parity gate for the tone-stack lab — and for the wiring study's numbers.
//
// The lab solves each preset's network in the browser by nodal analysis
// (src/lib/tonestack.js). The study at /reference/studies/tone-stack-ladder/
// quotes decibel figures from that solver and states that ngspice reproduces
// them. This script makes both claims checkable from the repository instead of
// resting on an authoring-time run:
//
//   1. PARITY — for every network form the study cites (the joined reference
//      form, the ladder in both its mid-leg forms, the 5F4's split network),
//      the element list from networkFor() is emitted as an ngspice netlist,
//      swept 10 Hz–100 kHz at 40 points/decade, and compared against the
//      browser solver at every frequency ngspice reports.
//
//   2. STUDY FIGURES — every decibel and hertz figure the study prints is
//      re-derived from the same solver and asserted at the precision the study
//      states it, so the published table cannot drift from the code.
//
// Run from site/:  node scripts/check-tonestack-spice.mjs   (needs ngspice)

import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { toneStackPresets } from '../src/lib/corpus.js';
import { networkFor, responseDb, summarise, GND, SRC } from '../src/lib/tonestack.js';

const PARITY_TOL_DB = 1e-3; // authoring-time observed worst case ~5e-5 dB

const presets = toneStackPresets();
const byId = (id) => presets.find((p) => p.id === id);
const asJoined = (p) => ({ ...p, parts: { ...p.parts, wiring: 'joined' } });
const pos = (t, m, b) => ({ treble: t / 10, mid: m / 10, bass: b / 10 });

const p5f6a = byId('5f6a');
const j5f6a = asJoined(p5f6a);
const pab = byId('ab763');
const jab = asJoined(pab);
const p5f4 = byId('5f4');

let failures = 0;
const fail = (msg) => { failures++; console.log(`FAIL ${msg}`); };

// ---------------------------------------------------------------- 1. parity
// SRC (-2) becomes node 999 driven by the 1 V AC source; GND (-1) becomes
// node 0; unknown node i becomes i+1 — same elements, same values.
function spiceNetlist(els, out) {
  const node = (x) => (x === GND ? '0' : x === SRC ? '999' : String(x + 1));
  const lines = ['* tone-stack parity sweep', 'V1 999 0 dc 0 ac 1'];
  let nr = 0, nc = 0;
  for (const e of els) {
    if (e.k === 'R') lines.push(`R${++nr} ${node(e.a)} ${node(e.b)} ${e.v}`);
    else if (e.v > 0) lines.push(`C${++nc} ${node(e.a)} ${node(e.b)} ${e.v}`);
  }
  lines.push('.ac dec 40 10 100k');
  return { text: lines.join('\n'), outVec: `v(${node(out)})` };
}

function ngspiceSweep(els, out, dir, tag) {
  const { text, outVec } = spiceNetlist(els, out);
  const cir = join(dir, `${tag}.cir`);
  const dat = join(dir, `${tag}.txt`);
  writeFileSync(cir, `${text}\n.control\nrun\nset filetype=ascii\nwrdata ${dat} ${outVec}\nquit\n.endc\n.end\n`);
  execFileSync('ngspice', ['-b', cir], { stdio: ['ignore', 'ignore', 'pipe'] });
  return readFileSync(dat, 'utf8').trim().split('\n').map((line) => {
    const [f, re, im] = line.trim().split(/\s+/).map(Number);
    return { f, db: 20 * Math.log10(Math.hypot(re, im)) };
  });
}

const parityCases = [
  ['5f6a ladder, five all round', p5f6a, pos(5, 5, 5)],
  ['5f6a joined, five all round', j5f6a, pos(5, 5, 5)],
  ['5f6a ladder, Bass and Middle at zero', p5f6a, pos(5, 0, 0)],
  ['5f6a joined, Bass and Middle at zero', j5f6a, pos(5, 0, 0)],
  ['ab763 ladder (fixed leg), five and five', pab, pos(5, 5, 5)],
  ['ab763 joined (fixed leg), five and five', jab, pos(5, 5, 5)],
  ['5f4 split, five and five', p5f4, pos(5, 5, 5)],
];

const dir = mkdtempSync(join(tmpdir(), 'tonestack-spice-'));
let worst = { d: 0, label: '' };
try {
  for (const [label, preset, position] of parityCases) {
    const { els, n, out } = networkFor(preset, position);
    void n;
    const sweep = ngspiceSweep(els, out, dir, label.replace(/[^a-z0-9]+/gi, '-'));
    let w = 0;
    for (const { f, db } of sweep) {
      const d = Math.abs(db - responseDb(preset, position, f));
      if (d > w) w = d;
    }
    if (w > worst.d) worst = { d: w, label };
    const ok = w <= PARITY_TOL_DB;
    if (!ok) failures++;
    console.log(`${ok ? 'ok  ' : 'FAIL'} parity ${label}: worst |Δ| ${w.toExponential(2)} dB over ${sweep.length} points`);
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}
console.log(`     worst parity residual overall: ${worst.d.toExponential(2)} dB (${worst.label})`);

// -------------------------------------------------------- 2. study figures
const at1k = (p, q) => responseDb(p, q, 1000);
function expect(label, got, want, tol) {
  const ok = Math.abs(got - want) <= tol;
  if (!ok) failures++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} study ${label}: computed ${got.toFixed(3)}, study prints ${want}`);
}

// The comparison table, on the 5F6-A's parts (one-decimal figures, gaps from
// the unrounded values).
const rows = [
  ['Treble 5 · Middle 5 · Bass 5', pos(5, 5, 5), -12.8, -13.8, 0.9],
  ['Treble 10 · Middle 1 · Bass 9', pos(10, 1, 9), -13.5, -23.2, 9.7],
  ['Treble 5 · Middle 0 · Bass 0', pos(5, 0, 0), -17.2, -100.7, 83.5],
  ['Treble 10 · Middle 0 · Bass 0', pos(10, 0, 0), -12.3, -100.9, 88.6],
];
for (const [label, q, lWant, jWant, gapWant] of rows) {
  const l = at1k(p5f6a, q), j = at1k(j5f6a, q);
  expect(`${label} · ladder`, l, lWant, 0.06);
  expect(`${label} · joined`, j, jWant, 0.06);
  expect(`${label} · gap`, l - j, gapWant, 0.06);
}

// Worst 1 kHz disagreement across the whole-number dial settings with neither
// Bass nor Middle at zero.
let detentMax = { g: -Infinity, t: 0, m: 0, b: 0 };
for (let t = 0; t <= 10; t++) for (let m = 1; m <= 10; m++) for (let b = 1; b <= 10; b++) {
  const g = Math.abs(at1k(p5f6a, pos(t, m, b)) - at1k(j5f6a, pos(t, m, b)));
  if (g > detentMax.g) detentMax = { g, t, m, b };
}
expect('worst detent gap (Bass, Middle ≥ 1)', detentMax.g, 9.7, 0.06);
if (!(detentMax.t === 10 && detentMax.m === 1 && detentMax.b === 9)) {
  fail(`study worst detent gap sits at T${detentMax.t}·M${detentMax.m}·B${detentMax.b}, study prints T10·M1·B9`);
}

// The floors: Bass and Middle at zero, Treble at five.
const sL = summarise(p5f6a, pos(5, 0, 0));
const sJ = summarise(j5f6a, pos(5, 0, 0));
expect('ladder floor (min, B0·M0·T5)', sL.minDb, -30.8, 0.06);
expect('ladder at 1 kHz (B0·M0·T5)', sL.at1k, -17.2, 0.06);
expect('joined floor (min, B0·M0·T5)', sJ.minDb, -104.7, 0.06);

// The notch positions: Bass 10, the others at five.
const nL = summarise(p5f6a, pos(5, 5, 10));
const nJ = summarise(j5f6a, pos(5, 5, 10));
expect('ladder deepest point (B10), Hz', nL.minHz, 710, 5);
expect('joined deepest point (B10), Hz', nJ.minHz, 2100, 60);

// The blackface two-knob case: floors a decibel apart, 1 kHz still 9 dB apart.
const bL = summarise(pab, pos(5, 5, 0));
const bJ = summarise(jab, pos(5, 5, 0));
expect('ab763 ladder floor (Bass 0)', bL.minDb, -29.3, 0.06);
expect('ab763 joined floor (Bass 0)', bJ.minDb, -30.5, 0.06);
expect('ab763 gap at 1 kHz (Bass 0)', Math.abs(bL.at1k - bJ.at1k), 9, 0.5);

console.log(`\ntone-stack solver vs. ngspice + study figures: ${failures} failure(s)`);
process.exit(failures ? 1 : 0);
