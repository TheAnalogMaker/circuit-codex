// Run from site/: node --test scripts/check-bench-units.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ohms, farads } from '../src/lib/bench-units.js';

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
