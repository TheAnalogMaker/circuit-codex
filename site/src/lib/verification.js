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
  if (!reports) reports = Object.fromEntries(['sheet-board', 'heaters', 'electrolytics', 'verification-freshness'].map((name) => {
    const file = path.join(ROOT, 'reference', `${name}.yaml`);
    return [name, fs.existsSync(file) ? parseReport(fs.readFileSync(file, 'utf8')) : null];
  }));
  return reports;
}

// reference/verification-freshness.yaml (pipeline/verification_freshness.py)
// lists every verified circuit whose facts - netlist, chart values, BOM, the
// two drawings' nets - no longer match what the maintainer stamped at review,
// or that carries no stamp. Such a circuit is still verified, on its date; the
// page adds that the changes since then await re-review. Presence by id is the
// whole contract: the file's values are never decoded here.
export function reviewPending(amp, reports = loadVerificationReports()) {
  return amp.meta?.verification?.status === 'verified'
    && Boolean(reports['verification-freshness']?.amps?.[amp.id]);
}
export const REVIEW_PENDING_NOTE = 'changes since then are awaiting maintainer re-review';
const isoDate = (value) => {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toISOString().slice(0, 10);
};

const yes = (value) => value === true || value === 'true';
const count = (value) => value !== undefined && value !== null && /^\d+$/.test(String(value))
  ? Number(value) : null;
const list = (value) => Array.isArray(value) ? value : [];
const counted = (n, singular, plural = `${singular}s`) => `${n} ${n === 1 ? singular : plural}`;
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
    `${missing.length} of ${counted(gated.length, 'reference node')} ${missing.length === 1 ? 'lacks' : 'lack'} a complete comparison.`, [], 'attention');
  else if (outside.length) dc = row('dc', 'DC operating point', 'Outside target',
    `${outside.length} of ${counted(gated.length, 'reference node')} ${outside.length === 1 ? 'falls outside its' : 'fall outside their'} stated tolerance.`, [], 'attention');
  else if (gated.length) dc = row('dc', 'DC operating point',
    amp.meta?.verification?.status === 'verified' ? 'Verified' : 'Within target',
    `${counted(gated.length, 'reference node')} ${gated.length === 1 ? 'is' : 'are'} within tolerance.`
      + (amp.meta?.verification?.status !== 'verified' ? ' The circuit remains a draft awaiting maintainer review.'
        : reviewPending(amp, reports) ? ` Maintainer verification is recorded${isoDate(amp.meta.verification.date) ? ` for ${isoDate(amp.meta.verification.date)}` : ''}; ${REVIEW_PENDING_NOTE}.`
          : ' Maintainer verification is recorded.'), [], 'checked');
  if (reviewPending(amp, reports)) dc.details.push('The circuit\'s facts (netlist, reference voltages, parts list, both drawings\' connections, capacitor polarity marks and heater declarations) have changed since the maintainer\'s review, or no review fingerprint is on record yet. The badge stands on its date until the maintainer re-reviews.');
  if (disputed) dc.details.push(`${counted(disputed, 'disputed node')} ${disputed === 1 ? 'is' : 'are'} excluded from the tolerance result; ${disputed === 1 ? 'its' : 'their'} reasoning is listed in the operating-point table.`);
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
    misplaced: ['part with different connections', 'parts with different connections'],
    merged: ['merged net', 'merged nets'], split: ['split net', 'split nets'],
    section_swap: ['valve-section swap', 'valve-section swaps'], board_only: ['board-only part', 'board-only parts'],
    sheet_only_undeclared: ['sheet-only part without an exclusion', 'sheet-only parts without an exclusion'],
    stale_declarations: ['outdated exclusion', 'outdated exclusions'], unresolved: ['unresolved part', 'unresolved parts'],
    pot_as_resistor: ['control without a comparable wiper', 'controls without a comparable wiper'],
  };
  if (!sheet || !sheet.counts || !Object.keys(names).every((k) => count(sheet.counts[k]) !== null)) {
    result.push(absent('drawings', 'Schematic against board'));
  } else {
    const findings = Object.entries(names).filter(([k]) => count(sheet.counts[k]) > 0)
      .map(([k, [singular, plural]]) => counted(count(sheet.counts[k]), singular, plural));
    const excluded = count(sheet.counts.sheet_only_declared);
    result.push(row('drawings', 'Schematic against board', findings.length ? 'Open findings' : 'No open findings',
      findings.length ? findings.join('; ') + '.' : 'No disagreement is listed in the published comparison.',
      ['A finding identifies a difference or a coverage gap. The factory source must decide which drawing, if either, needs correction.',
        `${excluded === null ? 'An unreported number of sheet-only parts' : counted(excluded, 'sheet-only part')} ${excluded === 1 ? 'is' : 'are'} explicitly excluded${list(sheet.sheet_only_declared).length ? `: ${sheet.sheet_only_declared.join(', ')}` : ''}. Heaters and the pilot lamp are checked separately.`], findings.length ? 'attention' : 'checked'));
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
  const wrongCount = completeCounts ? count(counts.wrong) : wrong.length;
  const undecidedCount = completeCounts ? count(counts.undecided) + count(counts.unmarked) : undecided.length;
  if (wrong.length || (completeCounts && count(counts.wrong))) result.push(row('polarity', 'Capacitor polarity', 'Open findings',
    `${counted(wrongCount, 'positive-lead marking')} ${wrongCount === 1 ? 'disagrees' : 'disagree'} with the model's voltage ordering.`, detail, 'attention'));
  else if (undecided.length || (completeCounts && count(counts.undecided) + count(counts.unmarked))) result.push(row('polarity', 'Capacitor polarity', 'Partial',
    `${counted(undecidedCount, 'capacitor marking')} cannot be confirmed by the DC model.`, detail, 'attention'));
  else if (completeCounts && count(counts.cans) > 0) result.push(row('polarity', 'Capacitor polarity', 'Checked',
    `${counted(count(counts.right), 'capacitor marking')} ${count(counts.right) === 1 ? 'agrees' : 'agree'} with the model's voltage ordering.`, ['This check uses DC voltage ordering; source review establishes markings the model cannot decide.'], 'checked'));
  else if (completeCounts && count(counts.cans) === 0) result.push(row('polarity', 'Capacitor polarity', 'Not applicable', 'No electrolytic capacitors were found by this check.'));
  else result.push(absent('polarity', 'Capacitor polarity'));
  return result;
}
