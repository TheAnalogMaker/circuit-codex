import { loadCorpus, displayId, circuitFamilyMap, loadLoadlineStages, toneStackPresetIds, ampOpPoints, schematicNetsVerified, TOPOLOGY_DIMENSIONS } from './corpus.js';
import { loadVerificationReports, reviewPending, verificationRows } from './verification.js';

export function comparisonCircuits() {
  const topology = (key, meta) => {
    const value = meta.topology?.[key];
    return value ? TOPOLOGY_DIMENSIONS.find((d) => d.key === key)?.values[value]?.label || value.replaceAll('-', ' ') : null;
  };
  const families = circuitFamilyMap();
  const stages = new Map(loadLoadlineStages().map((s) => [s.amp, s]));
  const presets = toneStackPresetIds();
  const reports = loadVerificationReports();
  return loadCorpus().map((amp) => {
    const m = amp.meta;
    const stage = stages.get(amp.id);
    const checks = verificationRows(amp, { schematicChecked: schematicNetsVerified(amp), opRows: ampOpPoints(amp), reports });
    return {
      id: amp.id, name: displayId(amp.id), style: m.name_style,
      family: families.get(amp.id)?.title ?? null,
      tonePreset: presets.has(amp.id), loadline: !!stage,
      unknown: checks.filter((r) => ['Not checked', 'Incomplete', 'Not established', 'Partial'].includes(r.status)).map((r) => `check-${r.id}`),
      values: {
        family: families.get(amp.id)?.title ?? null,
        years: m.era?.start && m.era?.end ? `${m.era.start}–${m.era.end}` : null,
        power: Number.isFinite(m.wattage) ? `${m.wattage} W` : null,
        output: stage ? `${stage.tube_lettered || stage.tube} ×${stage.output_tubes}` : null,
        tubes: m.tubes?.join(', ') ?? null,
        rectifier: m.topology?.rectifier?.type || m.topology?.rectifier?.kind || null,
        bias: topology('bias', m),
        inverter: topology('phase_inverter', m),
        tone: topology('tone_stack', m),
        status: m.verification?.status === 'verified'
          ? (reviewPending(amp, reports) ? 'Verified, re-review pending' : 'Verified') : 'Draft',
        reference: amp.voltages?.source || null,
        ...Object.fromEntries(checks.map((r) => [`check-${r.id}`, `${r.status} — ${r.summary}`])),
      },
    };
  });
}
export const COMPARISON_FIELDS = [
  ['family', 'Family line'], ['years', 'Years'], ['power', 'Output power'], ['output', 'Output valves'],
  ['tubes', 'Tube complement'], ['rectifier', 'Rectifier'], ['bias', 'Bias'],
  ['inverter', 'Phase inverter'], ['tone', 'Tone network'], ['status', 'Circuit status'],
  ['reference', 'Voltage reference'], ['check-dc', 'DC comparison'],
  ['check-schematic', 'Schematic check'], ['check-board', 'Board check'],
  ['check-drawings', 'Drawing comparison'], ['check-heaters', 'Heaters'], ['check-polarity', 'Capacitor polarity'],
];
