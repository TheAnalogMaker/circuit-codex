import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';

const ROOT = path.resolve(process.cwd(), '..');
// These reports are written by PyYAML. Its bare 5e3 key is a string, while
// js-yaml's default schema turns it into 5000. Keep all scalars as strings and
// decode only the small set of fields whose types this view actually needs.
export const parseReport = (text) => yaml.load(text, { schema: yaml.FAILSAFE_SCHEMA });
let reports;
export function loadVerificationReports() {
  if (!reports) reports = Object.fromEntries(['sheet-board', 'heaters', 'electrolytics'].map((name) => {
    const file = path.join(ROOT, 'reference', `${name}.yaml`);
    return [name, fs.existsSync(file) ? parseReport(fs.readFileSync(file, 'utf8')) : null];
  }));
  return reports;
}

const yes = (value) => value === true || value === 'true';
const count = (value) => value !== undefined && value !== null && /^\d+$/.test(String(value))
  ? Number(value) : null;
const list = (value) => Array.isArray(value) ? value : [];
const row = (id, title, status, summary, details = [], tone = 'neutral') => ({ id, title, status, summary, details, tone });
const absent = (id, title) => row(id, title, 'Not checked', 'No published check result is available.');

export function verificationRows(amp, { schematicChecked = false, opRows = [], reports = {} } = {}) {
  const result = [];
  const gated = opRows.filter((n) => n.gated);
  const disputed = opRows.filter((n) => n.disputed).length;
  const outside = gated.filter((n) => n.within === false);
  const missing = gated.filter((n) => !Number.isFinite(n.sim) || !Number.isFinite(n.chart)
    || typeof n.within !== 'boolean');
  let dc = absent('dc', 'DC operating point');
  if (opRows.length && !gated.length) dc = row('dc', 'DC operating point', 'Simulation only',
    'No undisputed reference voltages are available for a comparison.');
  else if (gated.length && missing.length) dc = row('dc', 'DC operating point', 'Incomplete',
    `${missing.length} of ${gated.length} reference nodes lack a complete comparison.`, [], 'attention');
  else if (outside.length) dc = row('dc', 'DC operating point', 'Outside target',
    `${outside.length} of ${gated.length} reference nodes fall outside their stated tolerance.`, [], 'attention');
  else if (gated.length) dc = row('dc', 'DC operating point',
    amp.meta?.verification?.status === 'verified' ? 'Verified' : 'Within target',
    `${gated.length} reference nodes are within tolerance.`
      + (amp.meta?.verification?.status === 'verified' ? ' Maintainer verification is recorded.' : ' The circuit remains a draft awaiting maintainer review.'), [], 'checked');
  if (disputed) dc.details.push(`${disputed} disputed node${disputed === 1 ? ' is' : 's are'} excluded from the tolerance result; their reasoning is listed in the operating-point table.`);
  dc.details.push('This compares simulated DC conditions with the cited reference. It does not test sound, physical construction or every part of the circuit.');
  result.push(dc);

  result.push(amp.hasSchematic && schematicChecked
    ? row('schematic', 'Schematic against DC model', 'Checked', 'Connectivity of modelled components is checked on every change.', ['Parts outside the DC model need separate checks and source review.'], 'checked')
    : absent('schematic', 'Schematic against DC model'));
  result.push(amp.hasLayout && amp.layout?.wiring_claim === 'verified'
    ? row('board', 'Board against DC model', 'Checked', 'Connectivity of modelled components is checked on every change.', ['This does not establish heater wiring or physical spacing.'], 'checked')
    : absent('board', 'Board against DC model'));

  const sheet = reports['sheet-board']?.amps?.[amp.id];
  const names = {
    misplaced: 'parts with different connections', merged: 'merged nets', split: 'split nets',
    section_swap: 'valve-section swaps', board_only: 'board-only parts',
    sheet_only_undeclared: 'sheet-only parts without an exclusion', stale_declarations: 'outdated exclusions',
    unresolved: 'unresolved parts', pot_as_resistor: 'controls without a comparable wiper',
  };
  if (!sheet || !sheet.counts || !Object.keys(names).every((k) => count(sheet.counts[k]) !== null)) {
    result.push(absent('drawings', 'Schematic against board'));
  } else {
    const findings = Object.entries(names).filter(([k]) => count(sheet.counts[k]) > 0)
      .map(([k, label]) => `${count(sheet.counts[k])} ${label}`);
    const excluded = count(sheet.counts.sheet_only_declared);
    result.push(row('drawings', 'Schematic against board', findings.length ? 'Open findings' : 'No open findings',
      findings.length ? findings.join('; ') + '.' : 'No disagreement is listed in the published comparison.',
      ['A finding identifies a difference or a coverage gap. The factory source must decide which drawing, if either, needs correction.',
        `${excluded ?? 'An unreported number of'} sheet-only parts are explicitly excluded${list(sheet.sheet_only_declared).length ? `: ${sheet.sheet_only_declared.join(', ')}` : ''}. Heaters and the pilot lamp are checked separately.`], findings.length ? 'attention' : 'checked'));
  }

  const heater = reports.heaters?.amps?.[amp.id];
  if (!heater) result.push(absent('heaters', 'Heater and filament wiring'));
  else {
    const shorted = list(heater.findings).filter((f) => f.kind === 'shorted');
    const established = yes(heater.fully_established);
    const declared = yes(heater.declared);
    const details = [heater.read_pending_because, heater.no_factory_layout_sheet,
      ...list(heater.findings).map((f) => `${f.socket}: ${f.detail}`)].filter(Boolean);
    const doubtful = Object.keys(heater.centre_tapped_sockets || {});
    if (doubtful.length) details.unshift(`Supply-leg grouping still needs confirmation at ${doubtful.join(', ')}.`);
    const complete = established && declared && list(heater.circuits).length > 0
      && Array.isArray(heater.findings) && !heater.findings.length && !doubtful.length
      && !heater.read_pending_because;
    const status = shorted.length ? 'Open findings' : complete ? 'Checked' : declared ? 'Partial' : 'Not established';
    result.push(row('heaters', 'Heater and filament wiring', status,
      complete ? 'The declared heater circuits cover the drawing and pass their separate wiring check.'
        : declared ? 'Some circuits are checked; other heater connections remain unestablished.'
          : 'The drawn supply-leg connections have not been established by this check.',
      details, complete ? 'checked' : 'attention'));
  }

  const polarity = reports.electrolytics?.amps?.[amp.id];
  const counts = polarity?.counts;
  const wrong = list(polarity?.wrong);
  const undecided = list(polarity?.not_decided);
  const detail = [...wrong.map((c) => `${c.ref}: ${c.leads}`), ...undecided.map((c) => `${c.ref}: ${c.why}`)];
  const completeCounts = counts && ['cans', 'right', 'wrong', 'undecided', 'unmarked'].every((k) => count(counts[k]) !== null)
    && count(counts.cans) === ['right', 'wrong', 'undecided', 'unmarked'].reduce((n, k) => n + count(counts[k]), 0);
  if (wrong.length || (completeCounts && count(counts.wrong))) result.push(row('polarity', 'Capacitor polarity', 'Open findings',
    `${completeCounts ? count(counts.wrong) : wrong.length} positive-lead markings disagree with the model's voltage ordering.`, detail, 'attention'));
  else if (undecided.length || (completeCounts && count(counts.undecided) + count(counts.unmarked))) result.push(row('polarity', 'Capacitor polarity', 'Partial',
    `${completeCounts ? count(counts.undecided) + count(counts.unmarked) : undecided.length} capacitor markings cannot be confirmed by the DC model.`, detail, 'attention'));
  else if (completeCounts && count(counts.cans) > 0) result.push(row('polarity', 'Capacitor polarity', 'Checked',
    `${count(counts.right)} capacitor markings agree with the model's voltage ordering.`, ['This check uses DC voltage ordering; source review establishes markings the model cannot decide.'], 'checked'));
  else if (completeCounts && count(counts.cans) === 0) result.push(row('polarity', 'Capacitor polarity', 'Not applicable', 'No electrolytic capacitors were found by this check.'));
  else result.push(absent('polarity', 'Capacitor polarity'));
  return result;
}
