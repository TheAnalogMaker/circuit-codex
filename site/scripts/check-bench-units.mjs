// Run from site/: node --test scripts/check-bench-units.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ohms, farads, number } from '../src/lib/bench-units.js';
import { touch, ohmPlan, otPlan, solveOhm } from '../src/lib/bench-solve.js';

function close(actual, expected) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= Math.abs(expected) * 1e-9,
    `${actual} !~ ${expected}`);
}

test('resistor shorthand matches the units guide', () => {
  assert.equal(ohms('100k'), 1e5);
  assert.equal(ohms('4k7'), 4700);
  assert.equal(ohms('4K7'), 4700);
  assert.equal(ohms('1M'), 1e6);
  assert.equal(ohms('1m5'), 1.5e6);
  assert.equal(ohms('4R7'), 4.7);
  assert.equal(ohms('470'), 470);
  assert.equal(ohms('100 ohm'), 100);
  assert.equal(ohms('100Ω'), 100);
  assert.equal(ohms('100\u2126'), 100);
  assert.equal(ohms('1 MEG'), 1e6);
  assert.equal(ohms('1MEG.'), 1e6);
  assert.equal(ohms('2.2Meg'), 2.2e6);
  assert.equal(ohms('-100k'), null);
  assert.equal(ohms(''), null);
  assert.equal(ohms('abc'), null);
});

test('capacitance reads µF by default and MFD as microfarads', () => {
  close(farads('0.02'), 0.02e-6);
  close(farads('0.022uF'), 0.022e-6);
  close(farads('22n'), 22e-9);
  close(farads('470p'), 470e-12);
  close(farads('22m'), 22e-3);
  // MF is the drawings' microfarad too, never a millifarad: ".02 MF" read as
  // 20 mF once put a coupling-cap corner at 0.008 Hz.
  close(farads('.02 MF'), 0.02e-6);
  close(farads('0.02mf'), 0.02e-6);
  close(farads('8 MF.'), 8e-6);
  // MMF / µµF is the micro-microfarad: a picofarad.
  close(farads('250 MMF'), 250e-12);
  close(farads('250uuf'), 250e-12);
  close(farads('250µµF'), 250e-12);
  close(farads('0.02mfd'), 0.02e-6);
  close(farads('25 MFD'), 25e-6);
  close(farads('25mfd.'), 25e-6);
  close(farads('16µfd'), 16e-6);
  close(farads('0.022ufd'), 0.022e-6);
  assert.equal(farads('-0.02'), null);
  assert.equal(farads('-0.02mfd'), null);
  assert.equal(farads('mfd'), null);
  assert.equal(farads('abc'), null);
});

test('0.02mfd into 1M is the same corner as 0.02 µF', () => {
  const corner = (c, r) => 1 / (2 * Math.PI * r * c);
  const fromPeriod = corner(farads('0.02mfd'), ohms('1M'));
  const fromBare = corner(farads('0.02'), ohms('1M'));
  assert.ok(Math.abs(fromPeriod - fromBare) < 1e-9);
  assert.ok(Math.abs(fromPeriod - 7.957747154594767) < 1e-6);
});

test('plain numbers are read whole or not at all', () => {
  assert.equal(number('250'), 250);
  assert.equal(number(' 1.5 '), 1.5);
  assert.equal(number('.5'), 0.5);
  assert.equal(number('\u22121.5'), -1.5);
  assert.equal(number('-55'), -55);
  assert.equal(number('1e3'), 1000);
  assert.equal(number('1,000'), null);
  assert.equal(number('12abc'), null);
  assert.equal(number('1k'), null);
  assert.equal(number(''), null);
});

// The Ohm's-law calculator, replayed keystroke by keystroke. `fields` is what
// the reader sees, in SI units; `type` mirrors the page's input handler.
function ohmBench() {
  const fields = { V: '250', I: '', R: '100000', P: '' };
  let order = ['R', 'V'];
  const read = () => Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, number(v)]));
  const type = (k, text) => {
    fields[k] = text;
    order = touch(order, k, text.trim() === '');
    const { writes } = ohmPlan(order, read(), k);
    for (const [w, v] of Object.entries(writes)) fields[w] = v == null ? '' : String(Number(v.toPrecision(4)));
  };
  return { fields, type };
}

test('backspacing a field empty does not refill it under the reader', () => {
  const b = ohmBench();
  b.type('I', '0.0025');                   // amps here (the page shows mA); order I, R, V
  assert.equal(b.fields.V, '250');
  for (const t of ['25', '2', '']) b.type('V', t);
  assert.equal(b.fields.V, '', 'the emptied field stays empty while it has focus');
  for (const t of ['3', '30', '300']) b.type('V', t);
  assert.equal(b.fields.V, '300', 'what the reader typed is what is in the box — not "2300"');
  // V and I now drive: R = 300 V / 2.5 mA, P = 0.75 W.
  assert.equal(number(b.fields.R), 120000);
  assert.equal(number(b.fields.P), 0.75);
});

test('the edited field is never written, even when it is not a driver', () => {
  const { use, writes } = ohmPlan(['I', 'R', 'V'], { V: null, I: 2e-3, R: 1e5, P: null }, 'V');
  assert.deepEqual(use, ['I', 'R']);
  assert.ok(!('V' in writes));
  close(writes.P, 0.4);
});

test('Ohm\'s law solves every pairing', () => {
  const ref = { V: 250, I: 2.5e-3, R: 1e5, P: 0.625 };
  const keys = Object.keys(ref);
  for (let i = 0; i < 4; i++) for (let j = i + 1; j < 4; j++) {
    const r = solveOhm({ [keys[i]]: ref[keys[i]], [keys[j]]: ref[keys[j]] });
    for (const k of keys) close(r[k], ref[k]);
  }
});

test('output-transformer ratio from any two, and never into the edited field', () => {
  const plan = otPlan(['Zp', 'Zs'], { Zp: 8000, Zs: 8, N: null }, null);
  close(plan.N, Math.sqrt(1000));
  assert.equal(plan.target, 'N');
  // Ratio typed, primary being retyped and momentarily empty: Zp is out of the
  // order, so N and Zs drive and the answer belongs in Zp — which has focus.
  const order = touch(['N', 'Zp', 'Zs'], 'Zp', true);
  const held = otPlan(order, { Zp: null, Zs: 8, N: 30 }, 'Zp');
  assert.equal(held.target, 'Zp');
  assert.equal(held.write, false);
  close(otPlan(['Zp', 'N', 'Zs'], { Zp: 6600, Zs: 8, N: 30 }, 'Zp').Zs, 6600 / 900);
});
