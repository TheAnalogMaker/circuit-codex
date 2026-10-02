// Run from site/: node --test scripts/check-tonestack-state.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { toneStackPresets } from '../src/lib/corpus.js';
import { curvePath, responseDb, sweepFrequencies } from '../src/lib/tonestack.js';
import {
  CONTROLS, readLabState, writeLabState, selectLabPreset, pinLabComparison,
  referenceSetting, labCurvePaths,
} from '../src/lib/tonestack-state.js';

const presets = toneStackPresets();
const byId = (id) => presets.find((p) => p.id === id);
const frequencies = sweepFrequencies();

test('legacy preset links restore five for every active control', () => {
  for (const preset of presets) {
    const state = readLabState('?preset=' + preset.id, presets);
    assert.equal(state.preset, preset);
    assert.equal(state.comparison, null);
    for (const c of preset.controls) assert.equal(state.pos[c], 0.5);
  }
  assert.equal(readLabState('?preset=unknown', presets).preset, presets[0]);
  assert.equal(readLabState('', presets).preset, presets[0]);
});

test('malformed, non-finite and absent positions default; finite values clamp and match slider steps', () => {
  for (const raw of ['', ' ', 'NaN', 'Infinity', '-Infinity', '1e999', '5oops', '0x8', '<script>']) {
    const state = readLabState('?preset=5f6a&treble=' + encodeURIComponent(raw), presets);
    assert.equal(state.pos.treble, 0.5, raw);
  }
  const state = readLabState('?preset=5f6a&treble=-15&mid=25&bass=8.14', presets);
  assert.deepEqual(state.pos, { treble: 0, mid: 1, bass: 0.81, tone: 0.5 });
  assert.equal(readLabState('?preset=5f6a&treble=8e0', presets).pos.treble, 0.8);
});

test('all presets round-trip extremes and interior positions without changing plotted curves', () => {
  for (const preset of presets) for (const position of [0, 0.01, 0.37, 0.5, 0.81, 1]) {
    const state = readLabState('?preset=' + preset.id, presets);
    for (const c of preset.controls) state.pos[c] = position;
    const restored = readLabState(writeLabState(state), presets);
    assert.deepEqual(restored, state);
    assert.equal(labCurvePaths(restored, frequencies).live, curvePath(preset, state.pos, frequencies));
    for (const f of [100, 1000, 5000]) {
      assert.equal(responseDb(restored.preset, restored.pos, f), responseDb(preset, state.pos, f));
    }
  }
});

test('preset and family switches reset sliders and remove irrelevant control parameters', () => {
  let state = readLabState('?preset=5f6a&treble=8&mid=2&bass=9&tone=4', presets);
  for (const id of ['aa764', '5f4', '5f2a', 'ab763-super']) {
    state = selectLabPreset(state, byId(id));
    const query = writeLabState(state, '?treble=8&mid=2&bass=9&tone=4&utm_source=forum');
    assert.equal(query.get('utm_source'), 'forum');
    for (const c of CONTROLS) {
      assert.equal(query.get(c), state.preset.controls.includes(c) ? '5.0' : null);
    }
    assert.deepEqual(readLabState(query, presets), state);
  }
});

test('pinned comparison is a snapshot retained across edits, preset switches and resets', () => {
  let state = pinLabComparison(readLabState('?preset=5f6a&treble=8&mid=2.3&bass=0', presets));
  const saved = { ...state.comparison.pos };
  const expected = curvePath(byId('5f6a'), saved, frequencies);
  state.pos.treble = 0.1;
  assert.deepEqual(state.comparison.pos, saved);
  for (const id of ['5f2a', 'aa764', '5f4', 'm2204']) {
    state = selectLabPreset(state, byId(id));
    state.pos[state.preset.controls[0]] = 0.73;
    const restored = readLabState(writeLabState(state), presets);
    const paths = labCurvePaths(restored, frequencies);
    assert.equal(paths.reference, expected);
    assert.equal(paths.live, curvePath(state.preset, state.pos, frequencies));
    assert.deepEqual(restored.comparison.pos, saved);
    state = selectLabPreset(state, state.preset);
    assert.deepEqual(state.comparison.pos, saved);
  }
});

test('comparison URLs support default positions and safely reject unknown presets', () => {
  const state = readLabState('?preset=jtm45&compare=5f6a', presets);
  assert.equal(state.comparison.preset.id, '5f6a');
  assert.equal(state.comparison.pos.treble, 0.5);
  const malformed = readLabState('?preset=5f6a&compare=5f2a&compare_tone=Infinity&compare_mid=7', presets);
  assert.equal(malformed.comparison.pos.tone, 0.5);
  assert.equal(writeLabState(malformed).has('compare_mid'), false);
  const unknown = readLabState('?preset=5f6a&compare=missing&compare_treble=8', presets);
  assert.equal(unknown.comparison, null);
  assert.equal(writeLabState(unknown).has('compare_treble'), false);
});

test('replacing or clearing a comparison drops old family values and restores the correct reference', () => {
  let state = pinLabComparison(readLabState('?preset=5f6a&treble=8', presets));
  const oldQuery = writeLabState(state);
  state = pinLabComparison(selectLabPreset(state, byId('5f2a')));
  const query = writeLabState(state, oldQuery);
  assert.equal(query.get('compare_tone'), '5.0');
  assert.equal(query.has('compare_treble'), false);
  assert.equal(query.has('compare_mid'), false);
  state.comparison = null;
  const cleared = writeLabState(state, query);
  assert.equal(cleared.has('compare'), false);
  assert.equal(cleared.has('compare_tone'), false);
  assert.deepEqual(referenceSetting(state).pos, { tone: 0 });
  assert.equal(labCurvePaths(state, frequencies).reference, curvePath(byId('5f2a'), { tone: 0 }, frequencies));
  state = selectLabPreset(state, byId('aa764'));
  assert.equal(referenceSetting(state).pos.treble, 1);
  assert.equal(referenceSetting(state).pos.bass, 1);
});
