import { ampOpPoints, schematicNetsVerified, DATA_LICENSE } from './corpus.js';
import { loadVerificationReports, verificationRows } from './verification.js';
import { archiveRevision, ampCorrections } from './revisions.js';

// Version 2 (2026-11): dates are YYYY-MM-DD strings throughout, as the corpus
// writes them, and metadata.tubes is a list of strings. Version 1 serialised
// js-yaml's Date objects as midnight-UTC timestamps (2026-08-08T00:00:00.000Z)
// beside plain-date corrections, and lettered tubes like 5881 as numbers.
export const DOWNLOAD_VERSION = 2;

// A copy of build-time YAML data with every Date as its calendar day. The corpus
// writes dates bare (2026-08-08), which js-yaml reads as a Date at midnight UTC;
// the day is the whole fact. Copies, never mutates: the loaders share one cache.
export function plainData(value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (Array.isArray(value)) return value.map(plainData);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, plainData(v)]));
  }
  return value;
}

function downloadMetadata(meta) {
  const out = plainData(meta);
  if (Array.isArray(out.tubes)) out.tubes = out.tubes.map((t) => String(t));
  return out;
}

export const DOWNLOAD_SCOPE = 'DC and drawing checks have separate coverage. See included check results and the circuit page; not a dimensioned build template or a physical-build certification.';
export function circuitDownload(amp) {
  const revision = archiveRevision();
  return {
    format: 'circuit-codex-reference', version: DOWNLOAD_VERSION, id: amp.id,
    url: `https://circuitcodex.com/amps/${amp.id}/`,
    attribution: 'The Analog Maker / Circuit Codex', license: DATA_LICENSE,
    revision: revision?.sha ?? null, scope: DOWNLOAD_SCOPE,
    metadata: downloadMetadata(amp.meta), parts: plainData(amp.bom ?? null),
    publishedVoltages: plainData(amp.voltages ?? null),
    operatingPoint: ampOpPoints(amp),
    checks: verificationRows(amp, { schematicChecked: schematicNetsVerified(amp), opRows: ampOpPoints(amp), reports: loadVerificationReports() }),
    corrections: ampCorrections(amp.id),
    sourceDirectory: revision ? `https://github.com/TheAnalogMaker/circuit-codex/tree/${revision.sha}/amps/${amp.id}` : null,
  };
}

export function csvCell(value) {
  let text = value === undefined || value === null ? '' : String(value);
  // CSV quoting does not prevent spreadsheet formula execution. Prefix only
  // cells whose leading content can be interpreted as a formula or control.
  if (/^[\s]*[=+\-@]|^[\t\r\n]/.test(text)) text = "'" + text;
  return `"${text.replaceAll('"', '""')}"`;
}

export function bomCsv(data) {
  const coverage = data.checks.map((r) => `${r.title}: ${r.status}`).join('; ');
  const rows = [['Circuit', 'Ref', 'Part', 'Value / rating', 'Role', 'Archive revision', 'Attribution', 'License', 'Check coverage', 'Scope', 'Circuit URL']];
  for (const item of data.parts?.items ?? []) rows.push([
    data.id, item.ref, item.part, item.value, item.role, data.revision ?? 'Unavailable',
    data.attribution, data.license, coverage, data.scope, data.url,
  ]);
  return '\uFEFF' + rows.map((r) => r.map(csvCell).join(',')).join('\r\n') + '\r\n';
}
