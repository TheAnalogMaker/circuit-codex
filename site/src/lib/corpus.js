// Build-time corpus loader — reads ../amps/*/ (meta.yaml, voltages.yaml,
// notes.md) so every page on the site is generated from the repo data.
import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import { marked } from 'marked';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const AMPS_DIR = path.join(REPO_ROOT, 'amps');
const MODELS_DIR = path.join(REPO_ROOT, 'models');
const REFERENCE_DIR = path.join(REPO_ROOT, 'reference');

function readIfExists(p) {
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
}

export function loadCorpus() {
  const amps = fs.readdirSync(AMPS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && !d.name.startsWith('_'))
    .map((d) => {
      const dir = path.join(AMPS_DIR, d.name);
      const meta = yaml.load(fs.readFileSync(path.join(dir, 'meta.yaml'), 'utf8'));
      const voltagesRaw = readIfExists(path.join(dir, 'voltages.yaml'));
      const bomRaw = readIfExists(path.join(dir, 'bom.yaml'));
      const notesRaw = readIfExists(path.join(dir, 'notes.md'));
      const layoutRaw = readIfExists(path.join(dir, 'layout.yaml'));
      const layout = layoutRaw ? yaml.load(layoutRaw) : null;
      return {
        id: meta.id,
        meta,
        voltages: voltagesRaw ? yaml.load(voltagesRaw) : null,
        bom: bomRaw ? yaml.load(bomRaw) : null,
        notesHtml: notesRaw ? marked.parse(notesRaw.replace(/^# .*\n/, '')) : null,
        layout,
        layoutBoard: boardType(layout),
        hasNetlist: fs.existsSync(path.join(dir, 'netlist.cir')),
        hasSchematic: fs.existsSync(path.join(dir, 'schematic.kicad_sch')),
        hasLayout: fs.existsSync(path.join(dir, 'layout.svg')),
      };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
  return amps;
}

export function corpusStats() {
  const amps = loadCorpus();
  const models = fs.readdirSync(MODELS_DIR).filter((f) => f.endsWith('.inc'));
  return {
    circuits: amps.length,
    verified: amps.filter((a) => a.meta.verification?.status === 'verified').length,
    models: models.length,
  };
}

export function displayId(id) {
  // Fender's own drawings hyphenate A-suffix models: 5F6-A, 5F2-A
  return String(id).toUpperCase().replace(/^(\d[A-Z]\d+)A$/, '$1-A');
}

// Board construction, read from the amp's own layout.yaml (board.title) — so the
// layout image's alt text is data-driven and honest. Fender-style circuits are
// eyelet boards redrawn from a published factory layout sheet; the JTM45 is a
// turret board reconstructed from the schematic (no factory layout drawing exists).
export function boardType(layout) {
  const title = String(layout?.board?.title || '').toLowerCase();
  const kind = title.includes('turret') ? 'turret'
    : title.includes('eyelet') ? 'eyelet'
    : 'circuit';
  // "(derived)" in the title, or a "derived" note on the source, means the board
  // diagram was reconstructed from the schematic rather than a published layout sheet.
  const derived = /derived/i.test(title) || /derived/i.test(String(layout?.source?.desc || ''));
  return { kind, derived };
}

// Data-driven alt text for the redrawn board-layout image. Neutral about the
// source: "redrawn reference diagram" for boards taken from a published layout
// sheet, "reconstructed from the schematic" for boards with no factory layout.
export function layoutAlt(amp) {
  const name = displayId(amp.id);
  const { kind, derived } = amp.layoutBoard || boardType(amp.layout);
  const board = kind === 'circuit' ? 'board' : `${kind} board`;
  return derived
    ? `${name} ${board} layout — an original diagram reconstructed from the redrawn schematic (no factory layout sheet exists), showing the principal parts in board order.`
    : `${name} ${board} layout — an original diagram redrawn from the published layout drawing, showing the principal parts in the order that drawing places them on the board.`;
}

// A per-amp meta description built from the circuit's own metadata (era, output,
// tube lineup, topology) so every amp page reads distinctly — 5E1 vs 5F1, etc.
export function ampMetaDescription(m) {
  const tubes = (m.tubes || []).join(', ');
  const rect = m.topology?.rectifier?.type || m.topology?.rectifier?.kind || 'tube';
  const bias = m.topology?.bias ? `${m.topology.bias}-bias` : null;
  const pi = m.topology?.phase_inverter && m.topology.phase_inverter !== 'none'
    ? `${m.topology.phase_inverter} phase inverter` : null;
  const topo = [bias, pi].filter(Boolean).join(', ');
  const era = m.era ? `${m.era.start}–${m.era.end}` : '';
  return `${m.name_style} (${era}), ${m.wattage} W on ${tubes}` +
    (topo ? `, ${topo}` : '') + `, ${rect} rectifier. ` +
    `Redrawn KiCad schematic, ngspice-verified netlist, published-chart operating points, and structured metadata.`;
}

export const GITHUB = 'https://github.com/TheAnalogMaker/circuit-codex';

// ---------------------------------------------------------------- topology lib
// Cross-cut "every X amp in one place" pages are generated from the same
// meta.topology fields the amp panel shows. Each dimension names how to read its
// value off an amp, the display label used in the amp's own metadata panel (so a
// panel <dd> can link straight to the matching page), an index blurb, and a fixed
// display order for the values that actually occur in the corpus. Values are
// grouped by what is *present* — a dimension a circuit doesn't record is skipped,
// never invented.

export const TOPOLOGY_DIMENSIONS = [
  {
    key: 'phase_inverter',
    dt: 'Phase inv.',
    label: 'Phase inverter',
    blurb: 'How a push-pull amp splits one signal into the two opposite-phase drives its output tubes need — or why a single-ended amp needs none.',
    read: (m) => m.topology?.phase_inverter ?? null,
    order: ['long-tailed-pair', 'cathodyne', 'none'],
    values: {
      'long-tailed-pair': { slug: 'phase-inverter-ltp', label: 'Long-tailed pair' },
      'cathodyne': { slug: 'phase-inverter-cathodyne', label: 'Cathodyne' },
      'none': { slug: 'phase-inverter-none', label: 'Single-ended (no inverter)' },
    },
  },
  {
    key: 'bias',
    dt: 'Bias',
    label: 'Output-stage bias',
    blurb: 'How the output tubes are held at their idle operating point — a self-setting cathode resistor, or a separate negative supply.',
    read: (m) => m.topology?.bias ?? null,
    order: ['fixed', 'cathode'],
    values: {
      'fixed': { slug: 'bias-fixed', label: 'Fixed bias' },
      'cathode': { slug: 'bias-cathode', label: 'Cathode bias' },
    },
  },
  {
    key: 'rectifier',
    dt: 'Rectifier',
    label: 'Rectifier',
    blurb: 'What turns the power transformer\'s high-voltage AC into the DC B+ rail — a vacuum diode that sags under load, or stiff silicon.',
    read: (m) => m.topology?.rectifier?.kind ?? null,
    order: ['tube', 'solid-state'],
    values: {
      'tube': { slug: 'rectifier-tube', label: 'Tube rectifier' },
      'solid-state': { slug: 'rectifier-solid-state', label: 'Solid-state rectifier' },
    },
  },
  {
    key: 'tone_stack',
    dt: 'Tone stack',
    label: 'Tone stack',
    blurb: 'The passive control network that shapes the amp\'s response — from no tone control at all to the three-knob stack that defined lead tone.',
    read: (m) => m.topology?.tone_stack ?? null,
    order: ['cathode-follower-fmv', 'cathode-follower-tb', 'tb', 'single-knob', 'none'],
    values: {
      'cathode-follower-fmv': { slug: 'tone-stack-cf-fmv', label: 'Cathode-follower FMV stack' },
      'cathode-follower-tb': { slug: 'tone-stack-cf-tb', label: 'Cathode-follower treble/bass' },
      'tb': { slug: 'tone-stack-tb', label: 'Treble/bass stack' },
      'single-knob': { slug: 'tone-stack-single-knob', label: 'Single tone control' },
      'none': { slug: 'tone-stack-none', label: 'No tone stack' },
    },
  },
];

// The href for the cross-cut page matching an amp's value on one dimension, or
// null when the amp doesn't record that dimension (so a panel link degrades to
// plain text rather than pointing nowhere).
export function topologyHref(dimKey, m) {
  const dim = TOPOLOGY_DIMENSIONS.find((d) => d.key === dimKey);
  if (!dim) return null;
  const val = dim.read(m);
  const cfg = val != null ? dim.values[val] : null;
  return cfg ? `/topology/${cfg.slug}/` : null;
}

// One record per (dimension, value) actually present in the corpus, each with the
// matching amps attached — the source of both the /topology/ index groups and the
// per-page getStaticPaths.
export function topologyCrossCuts() {
  const amps = loadCorpus();
  const dims = TOPOLOGY_DIMENSIONS.map((dim) => {
    const byVal = new Map();
    for (const amp of amps) {
      const val = dim.read(amp.meta);
      if (val === null || val === undefined) continue;
      if (!byVal.has(val)) byVal.set(val, []);
      byVal.get(val).push(amp);
    }
    const order = dim.order.filter((v) => byVal.has(v))
      .concat([...byVal.keys()].filter((v) => !dim.order.includes(v)));
    const pages = order.map((val) => ({
      dimKey: dim.key,
      dimLabel: dim.label,
      dt: dim.dt,
      value: val,
      slug: dim.values[val]?.slug || `${dim.key}-${val}`.replace(/[^a-z0-9]+/gi, '-'),
      label: dim.values[val]?.label || val,
      amps: byVal.get(val),
    }));
    return { key: dim.key, label: dim.label, blurb: dim.blurb, dt: dim.dt, pages };
  });
  return dims;
}

// Flat list of every cross-cut page (for getStaticPaths). Each carries its sibling
// dimensions so a page can show, per amp, the neighbouring topology choices.
export function topologyPages() {
  const dims = topologyCrossCuts();
  const flat = [];
  for (const dim of dims) {
    for (const page of dim.pages) {
      flat.push({ ...page, siblings: TOPOLOGY_DIMENSIONS.filter((d) => d.key !== page.dimKey) });
    }
  }
  return flat;
}

// Human-readable value for one topology dimension of an amp (used in the
// comparison tables' neighbour columns): rectifier shows the specific tube/type,
// everything else shows the recorded token.
export function topologyValueDisplay(dimKey, m) {
  if (dimKey === 'rectifier') return m.topology?.rectifier?.type || m.topology?.rectifier?.kind || '—';
  return m.topology?.[dimKey] ?? '—';
}

// ---------------------------------------------------------------- reference lib
// The /reference/ section renders from reference/sources.yaml, reference/tubes/
// *.yaml, and reference/studies/*.md — the same build-time data pattern the amp
// pages use. Nothing here is rehosted; every entry points at a holding archive.

export function loadSources() {
  const raw = fs.readFileSync(path.join(REFERENCE_DIR, 'sources.yaml'), 'utf8');
  return (yaml.load(raw).sources || []).map((s) => ({ ...s, host: hostOf(s.url) }));
}

export function loadTubes() {
  const dir = path.join(REFERENCE_DIR, 'tubes');
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith('.yaml'))
    .map((f) => {
      const t = yaml.load(fs.readFileSync(path.join(dir, f), 'utf8'));
      return { ...t, name: String(t.name), datasheets: (t.datasheets || []).map((d) => ({ ...d, host: hostOf(d.url) })) };
    })
    .sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true }));
}

export function loadStudies() {
  const dir = path.join(REFERENCE_DIR, 'studies');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => parseStudy(path.join(dir, f), f.replace(/\.md$/, '')))
    .sort((a, b) => a.title.localeCompare(b.title));
}

export function loadStudy(slug) {
  const p = path.join(REFERENCE_DIR, 'studies', `${slug}.md`);
  return fs.existsSync(p) ? parseStudy(p, slug) : null;
}

function parseStudy(filePath, slug) {
  const md = fs.readFileSync(filePath, 'utf8');
  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;
  // Subtitle: a leading italic line just under the H1 (e.g. *A metrology study…*).
  const subMatch = md.match(/^#\s+.+\n+\*(.+?)\*\s*$/m);
  const subtitle = subMatch ? subMatch[1].trim() : null;
  // Strip H1 and the subtitle line from the rendered body — they become the header.
  let body = md.replace(/^#\s+.+\n/, '');
  if (subtitle) body = body.replace(/^\s*\*.+?\*\s*\n/, '');
  return { slug, title, subtitle, html: marked.parse(body) };
}

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

export function loadGlossary() {
  const raw = fs.readFileSync(path.join(REFERENCE_DIR, 'glossary.yaml'), 'utf8');
  const terms = yaml.load(raw).terms || [];
  return [...terms].sort((a, b) => a.sort_key.localeCompare(b.sort_key, 'en'));
}

// Split a pd_basis string ("pd-outright (published 1920)") into its leading
// controlled-vocabulary token and the human-readable remainder.
export function pdBasis(str) {
  if (!str) return { token: null, rest: '' };
  const token = str.split(/\s/)[0];
  const rest = str.slice(token.length).replace(/^[\s—–-]+/, '').trim();
  return { token, rest };
}
