import test from 'node:test';
import assert from 'node:assert/strict';
import { parseReport, verificationRows, loadVerificationReports } from '../src/lib/verification.js';
import { loadCorpus, ampOpPoints, schematicNetsVerified } from '../src/lib/corpus.js';
import { comparisonSelection, comparisonUrl, difference, fieldDifference } from '../src/lib/comparison-state.js';
import { comparisonCircuits } from '../src/lib/comparison.js';
import { circuitDownload, bomCsv, csvCell } from '../src/lib/downloads.js';
import { loadCorrections } from '../src/lib/revisions.js';

const amps = loadCorpus();
const amp = amps.find((a) => a.id === '5e3');
const status = (rows, id) => rows.find((r) => r.id === id).status;
test('Python-exported scientific-looking circuit IDs remain exact strings', () => {
  const report = parseReport('amps:\n  5e3:\n    fully_established: false\n  5e1:\n    count: 1\n');
  assert.deepEqual(Object.keys(report.amps), ['5e3', '5e1']);
  assert.equal(report.amps['5e3'].fully_established, 'false');
  assert.ok(loadVerificationReports()['sheet-board'].amps['5e3']);
});
test('missing evidence, partial heaters, and known wrong polarity cannot become checked', () => {
  const missing = verificationRows(amp);
  for (const id of ['dc', 'drawings', 'heaters', 'polarity']) assert.equal(status(missing, id), 'Not checked');
  const reports = { heaters: { amps: { [amp.id]: { declared: 'true', fully_established: 'false', findings: [] } } },
    electrolytics: { amps: { [amp.id]: { wrong: [{ref:'C4',leads:'positive mark on lower-voltage end'}] } } } };
  const rows = verificationRows(amp, { reports });
  assert.equal(status(rows, 'heaters'), 'Partial');
  assert.equal(status(rows, 'polarity'), 'Open findings');
  assert.equal(status(rows, 'drawings'), 'Not checked');
  for (const heater of [
    {declared:true,fully_established:true},
    {declared:true,fully_established:true,circuits:[{id:'h63'}],findings:[{kind:'unclassified'}]},
    {declared:true,fully_established:true,circuits:[{id:'h63'}],findings:[],centre_tapped_sockets:{V1:{}}},
  ]) assert.equal(status(verificationRows(amp, {reports:{heaters:{amps:{[amp.id]:heater}}}}), 'heaters'), 'Partial');
  const published = verificationRows(amp, {reports:loadVerificationReports()});
  assert.equal(status(published, 'heaters'), 'Checked');
  const brown = amps.find((a) => a.id === '6g3');
  const exclusions = verificationRows(brown, {reports:loadVerificationReports()}).find((r) => r.id === 'drawings').details.join(' ');
  for (const ref of loadVerificationReports()['sheet-board'].amps['6g3'].sheet_only_declared) assert.ok(exclusions.includes(ref));
});
test('only complete per-amp capacitor counts establish clean polarity coverage', () => {
  const result = (data) => status(verificationRows(amp, { reports: { electrolytics: { amps: { [amp.id]: data } } } }), 'polarity');
  assert.equal(result({}), 'Not checked');
  assert.equal(result({ counts: {cans:3,right:3,wrong:0,undecided:0,unmarked:0} }), 'Checked');
  assert.equal(result({ counts: {cans:3,right:2,wrong:0,undecided:1,unmarked:0} }), 'Partial');
  assert.equal(result({ counts: {cans:3,right:1,wrong:0,undecided:0,unmarked:0} }), 'Not checked');
});
test('voltage mismatch and missing simulation override a recorded verified badge', () => {
  const current = { gated:true, disputed:false, chart:100, sim:110, within:false };
  assert.equal(status(verificationRows(amp, { opRows:[current] }), 'dc'), 'Outside target');
  assert.equal(status(verificationRows(amp, { opRows:[{...current,sim:null,within:null}] }), 'dc'), 'Incomplete');
  assert.equal(status(verificationRows({...amp,meta:{verification:{status:'draft'}}}, {opRows:[{...current,within:true}]}), 'dc'), 'Within target');
  for (const n of [{gated:true,sim:42}, {...current,sim:NaN}, {...current,within:undefined}, {...current,chart:undefined}]) {
    assert.equal(status(verificationRows(amp, {opRows:[n]}), 'dc'), 'Incomplete');
  }
});
test('comparison URLs round-trip, reject unknown and duplicate circuits, preserve missing data', () => {
  const ids = amps.map((a) => a.id);
  for (const a of amps) {
    const s = comparisonSelection(`?left=${a.id}&right=${a.id}&differences=1`, ids);
    assert.notEqual(s.left, s.right);
    assert.deepEqual(comparisonSelection(comparisonUrl(s).split('?')[1], ids), s);
  }
  const invalid = comparisonSelection('?left=../../wrong&right=<script>', ids);
  assert.ok(ids.includes(invalid.left)); assert.ok(ids.includes(invalid.right));
  assert.equal(difference(null, null), 'Not recorded');
  assert.equal(difference('0', '0'), 'Same');
  assert.equal(difference('12 W', '15 W'), 'Different');
  const missing = {values:{polarity:'Not checked'},unknown:['polarity']};
  assert.equal(fieldDifference(missing, missing, 'polarity'), 'Not recorded');
});
test('all corpus comparisons/downloads retain identity, check coverage, attribution and source revision', () => {
  const comparisons = comparisonCircuits();
  assert.equal(comparisons.length, amps.length);
  for (const amp of amps) {
    const comp = comparisons.find((c) => c.id === amp.id);
    assert.ok(comp); assert.ok(!JSON.stringify(comp).includes('undefined'));
    const data = circuitDownload(amp);
    assert.equal(data.id, amp.id); assert.match(data.revision, /^[a-f0-9]{40}$/);
    assert.equal(data.checks.length, 6); assert.ok(data.license.includes('by-sa'));
    const csv = bomCsv(data);
    assert.ok(csv.includes('Archive revision')); assert.ok(csv.includes(data.revision));
    assert.equal(data.parts?.items.length, amp.bom?.items.length);
    const direct = verificationRows(amp, {opRows:ampOpPoints(amp),schematicChecked:schematicNetsVerified(amp),reports:loadVerificationReports()});
    assert.deepEqual(data.checks, direct);
  }
});
test('CSV quotes fields and prevents spreadsheet formula interpretation', () => {
  assert.equal(csvCell('a,"b"\nc'), '"a,""b""\nc"');
  for (const value of ['=1+1','+cmd','-1+2','@sum(1)','\t=1','  =1']) assert.ok(csvCell(value).startsWith('"\''));
  assert.equal(csvCell('0.02 µF · 400 V'), '"0.02 µF · 400 V"');
});
test('correction entries have stable distinct identifiers and valid circuit targets', () => {
  const entries = loadCorrections();
  assert.ok(entries.length > 0);
  assert.equal(new Set(entries.map((e) => e.id)).size, entries.length);
  for (const entry of entries) {
    assert.ok(entry.amps.every((id) => amps.some((a) => a.id === id)));
    assert.match(entry.date,/^\d{4}-\d{2}-\d{2}$/);
    assert.ok(Number.isFinite(Date.parse(entry.date)));
  }
});
