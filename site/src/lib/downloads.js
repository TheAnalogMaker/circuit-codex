import { ampOpPoints, schematicNetsVerified, DATA_LICENSE } from './corpus.js';
import { loadVerificationReports, verificationRows } from './verification.js';
import { archiveRevision, ampCorrections } from './revisions.js';

export const DOWNLOAD_SCOPE = 'DC and drawing checks have separate coverage. See included check results and the circuit page; not a dimensioned build template or a physical-build certification.';
export function circuitDownload(amp) {
  const revision = archiveRevision();
  return {
    format: 'circuit-codex-reference', version: 1, id: amp.id,
    url: `https://circuitcodex.com/amps/${amp.id}/`,
    attribution: 'The Analog Maker / Circuit Codex', license: DATA_LICENSE,
    revision: revision?.sha ?? null, scope: DOWNLOAD_SCOPE,
    metadata: amp.meta, parts: amp.bom ?? null, publishedVoltages: amp.voltages ?? null,
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
