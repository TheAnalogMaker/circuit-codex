// Shareable lab state. URLs use the slider's 0–10 resistance position, while
// the analytic solver takes 0–1. Only the selected network's controls survive.
import { midPositions, maxPositions, curvePath } from './tonestack.js';

export const CONTROLS = ['treble', 'mid', 'bass', 'tone'];

function position(value) {
  if (value == null || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(String(value).trim())) return 0.5;
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(Math.max(0, Math.min(10, n)) * 10) / 100 : 0.5;
}

function readSetting(params, presets, prefix = '') {
  const preset = presets.find((p) => p.id === params.get(prefix ? 'compare' : 'preset'));
  if (prefix && !preset) return null;
  const selected = preset || presets[0];
  const pos = midPositions();
  for (const c of selected.controls) pos[c] = position(params.get(prefix + c));
  return { preset: selected, pos };
}

export function readLabState(search, presets) {
  const params = new URLSearchParams(search);
  return { ...readSetting(params, presets), comparison: readSetting(params, presets, 'compare_') };
}

export function writeLabState(state, search = '') {
  const params = new URLSearchParams(search);
  for (const c of CONTROLS) {
    params.delete(c);
    params.delete('compare_' + c);
  }
  params.delete('preset');
  params.delete('compare');
  const write = (setting, prefix) => {
    params.set(prefix ? 'compare' : 'preset', setting.preset.id);
    for (const c of setting.preset.controls) {
      const value = position(setting.pos[c] * 10) * 10;
      params.set(prefix + c, value.toFixed(1));
    }
  };
  write(state, '');
  if (state.comparison) write(state.comparison, 'compare_');
  return params;
}

// A preset selection always starts at five; a pinned setting is independent of
// those active controls and survives both switching and resetting the sliders.
export function selectLabPreset(state, preset) {
  return { ...state, preset, pos: midPositions() };
}

export function pinLabComparison(state) {
  return { ...state, comparison: { preset: state.preset, pos: { ...state.pos } } };
}

export function referenceSetting(state) {
  return state.comparison || {
    preset: state.preset,
    pos: state.preset.kind === 'single-knob' ? { tone: 0 } : maxPositions(),
  };
}

// Both lines use the same solver and frequency grid; pinning never samples a
// raster or mutates a preset's component values.
export function labCurvePaths(state, frequencies) {
  const reference = referenceSetting(state);
  return {
    live: curvePath(state.preset, state.pos, frequencies),
    reference: curvePath(reference.preset, reference.pos, frequencies),
  };
}
