// Parity gate for the load-line explorer.
//
// The explorer solves each amp's output stage in the browser from the Koren
// parameters in models/*.inc. pipeline/verify_amps.py solves the same stage in
// ngspice from the same models, inside the whole amplifier. Same maths, same
// numbers — so the two answers must agree. This script proves it on every circuit
// in the corpus, using the exact module the page ships (src/lib/loadline.js), and
// exits non-zero if any circuit drifts past tolerance.
//
// Run from site/:  node scripts/check-loadline-parity.mjs
//
// Where the two can legitimately differ: the browser holds the screen node at the
// voltage ngspice settled on, rather than re-solving the screen dropper and the
// whole preamp chain behind it. Pinning a converged unknown does not move the
// remaining solution, so the residual is numerical, not physical — and the
// tolerance below is tight enough to catch it if that ever stops being true.

import { loadTubeModels, loadLoadlineStages } from '../src/lib/corpus.js';
import { solveOperatingPoint } from '../src/lib/loadline.js';

const TOL_PCT = 1.0; // percent; observed residual is ~0.02%

const models = new Map(loadTubeModels().map((m) => [m.name.toUpperCase(), m]));
const stages = loadLoadlineStages();

let failures = 0;
const rows = [];

for (const s of stages) {
  const model = models.get(String(s.tube).toUpperCase());
  if (!model) {
    console.log(`FAIL ${s.amp}: no model parsed for ${s.tube}`);
    failures++;
    continue;
  }
  const q = solveOperatingPoint({
    model,
    bplus: s.plate_v,
    ra: 0, // the netlists put the output tube's plate straight on the rail (OT DCR omitted)
    rk: s.rk_per_tube || 0,
    vgSupply: s.grid_v || 0,
    vg2Supply: s.screen_v,
  });

  const compare = [
    ['Ip', q.ip * 1e3, s.sim_ip_ma, 'mA'],
    ['Ig2', q.ig2 * 1e3, s.sim_ig2_ma, 'mA'],
  ];
  if (s.bias === 'cathode') compare.unshift(['Vk', q.vk, s.cathode_v, 'V']);

  const errs = compare.map(([, got, want]) =>
    (Math.abs(want) > 1e-9 ? Math.abs(got - want) / Math.abs(want) * 100 : 0));
  const worst = Math.max(...errs);
  const ok = worst <= TOL_PCT;
  if (!ok) failures++;

  rows.push({ amp: s.amp, tube: s.tube, bias: s.bias, compare, worst, ok });
}

const w = (x, n) => String(x).padEnd(n);
console.log('load-line solver vs. ngspice operating point (per output tube)\n');
for (const r of rows) {
  console.log(`${r.ok ? 'ok  ' : 'FAIL'} ${w(r.amp, 7)}${w(r.tube, 7)}${w(r.bias + ' bias', 14)}worst ${r.worst.toFixed(3)}%`);
  for (const [label, got, want, unit] of r.compare) {
    console.log(`       ${w(label, 5)}browser ${got.toFixed(4)} ${unit}   ngspice ${want.toFixed(4)} ${unit}`);
  }
}
console.log(`\n${rows.length} output stage(s), tolerance ${TOL_PCT}%, ${failures} failure(s)`);
process.exit(failures ? 1 : 0);
