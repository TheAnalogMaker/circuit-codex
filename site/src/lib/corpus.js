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
