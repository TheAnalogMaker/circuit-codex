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
const HISTORY_DIR = path.join(REPO_ROOT, 'history', 'families');

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
  // --- history tier (added with the family grouping) — every model placed in a
  // family file, documented circuit or not, so the headline counts show the
  // corpus's reach as well as its depth.
  const families = loadHistory();
  return {
    circuits: amps.length,
    verified: amps.filter((a) => a.meta.verification?.status === 'verified').length,
    models: models.length,
    families: families.length,
    historyModels: families.reduce((n, f) => n + f.models.length, 0),
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

// ----------------------------------------------------------------- load lines
// The load-line explorer runs the Koren plate-current equations in the browser. Its
// parameters are not typed into the page — they are parsed out of the corpus's own
// CC0 model files at build time, so the curves a visitor drags a load line across
// are drawn from the same numbers ngspice simulates the circuits with.
//
// A model .inc carries everything needed on two lines:
//   .subckt 6V6GT P G2 G1 K            -> node order tells triode from pentode
//   * fitted: MU=9.6 EX=1.5 KG1=... KG2=... KP=... KVB=30
// plus an "* Anchor (source): ..." header line naming the datasheet point it was
// fitted to. Rectifier diodes (.subckt … A K, PERV=…) have no grid and are skipped:
// there is no load line to draw.

const FITTED = /^\*\s*fitted:\s*(.+)$/m;
const SUBCKT = /^\.subckt\s+(\S+)\s+(.+)$/m;
const ANCHOR = /^\*\s*Anchor\s*\(([^)]*)\):\s*(.+)$/m;

function parseModelFile(text, file) {
  const sub = text.match(SUBCKT);
  const fit = text.match(FITTED);
  if (!sub || !fit) return null;
  const nodes = sub[2].trim().split(/\s+/);
  const kind = nodes.length === 4 ? 'pentode' : nodes.length === 3 ? 'triode' : 'diode';
  if (kind === 'diode') return null;
  const params = {};
  for (const [, k, v] of fit[1].matchAll(/([A-Z0-9]+)=([-\d.eE+]+)/g)) {
    params[k.toLowerCase()] = Number(v);
  }
  if (!isFinite(params.kg1) || !isFinite(params.mu)) return null;
  if (kind === 'pentode' && !isFinite(params.kg2)) return null;
  const anchor = text.match(ANCHOR);
  return {
    name: sub[1],
    kind,
    nodes,
    params,
    file,
    anchor: anchor ? anchor[2].trim() : null,
    anchorSource: anchor ? anchor[1].trim() : null,
  };
}

// Every amplifying tube model in models/, keyed for the explorer. Each is joined to
// its reference/tubes/<id>.yaml entry so the page can show the tube's role, its
// datasheet-sourced maximum ratings, and a link to its own page.
export function loadTubeModels() {
  const tubes = loadTubes();
  const byName = new Map(tubes.map((t) => [String(t.name).toUpperCase(), t]));
  return fs.readdirSync(MODELS_DIR)
    .filter((f) => f.endsWith('.inc'))
    .map((f) => parseModelFile(fs.readFileSync(path.join(MODELS_DIR, f), 'utf8'), `models/${f}`))
    .filter(Boolean)
    .map((m) => {
      const ref = byName.get(m.name.toUpperCase()) || null;
      // reference/tubes/5881.yaml carries `tube: 5881`, which js-yaml reads as a
      // number — force the slug back to text so the /reference/tubes/ link works.
      const slug = ref?.tube != null ? String(ref.tube) : m.name.toLowerCase();
      // Model headers append the datasheet URL to the anchor source; the page links
      // the sheet separately, so keep the citation prose on its own.
      const anchorSource = m.anchorSource ? m.anchorSource.split(/;\s*https?:/)[0].trim() : null;
      return {
        ...m,
        slug,
        anchorSource,
        // The tube's own reference entry writes the anchor in house notation
        // (→, µmho); the .inc header is plain ASCII for SPICE. Prefer the former.
        anchor: ref?.model?.anchor ?? m.anchor,
        role: ref?.role ?? null,
        limits: ref?.max_ratings?.limits ?? null,
        // Which rating system the sheet uses is recorded as a field on the tube
        // rather than inferred from the wording of its citation: GEC's KT66 sheet
        // heads its design-maximum column "design", and no phrase-match survives
        // that kind of variation.
        ratingSystem: ref?.max_ratings?.rating_system ?? null,
        ratingsSource: ref?.max_ratings?.source ?? null,
        ratingsSourceUrl: ref?.max_ratings?.source_url ?? null,
        usedIn: ref?.used_in ?? [],
      };
    })
    .sort((a, b) => (a.kind === b.kind
      ? a.name.localeCompare(b.name, 'en', { numeric: true })
      : a.kind.localeCompare(b.kind)));
}

// Output-stage presets, straight from reference/loadlines.yaml — the file
// pipeline/export_loadlines.py generates by reading each amp's netlist.cir and
// simulating it. Amp title and verification status are joined in from the corpus so
// a preset never claims more than the circuit itself does.
export function loadLoadlineStages() {
  const p = path.join(REFERENCE_DIR, 'loadlines.yaml');
  if (!fs.existsSync(p)) return [];
  const stages = yaml.load(fs.readFileSync(p, 'utf8')).stages || [];
  const amps = new Map(loadCorpus().map((a) => [a.id, a]));
  return stages.map((s) => {
    const amp = amps.get(s.amp) || null;
    return {
      ...s,
      display: displayId(s.amp),
      verified: amp?.meta?.verification?.status === 'verified',
      wattage: amp?.meta?.wattage ?? null,
    };
  });
}

export function loadGlossary() {
  const raw = fs.readFileSync(path.join(REFERENCE_DIR, 'glossary.yaml'), 'utf8');
  const terms = yaml.load(raw).terms || [];
  return [...terms].sort((a, b) => a.sort_key.localeCompare(b.sort_key, 'en'));
}

// ------------------------------------------------------------------ history lib
// The history tier (history/families/*.yaml) documents each amp *line* as a
// chronological chain of models — most of them not yet fully documented circuits.
// It renders the /history/ pages and feeds the lineage graph's ghost nodes. A model
// carries a documented circuit only where its circuit_ref names a real amps/ entry;
// everything else is a history-tier entry (an outline chip / "not yet documented"
// badge). Nothing is invented: eras, tubes, and prose come straight from the YAML.

// Compact designation for a chip label: the first token of a multi-designation
// string ("6G6 / 6G6-A" → "6G6", "5E6 / 5E6-A" → "5E6") so timeline chips stay tight.
//
// The separator is a SPACED slash, and only a spaced slash. Fender's files list two
// designations for one model that way; Vox's do not — "AC30/4", "AC30/6" and "AC1/15"
// are single model names that happen to contain a slash, and "AC30 (AC/30)" carries
// one inside a parenthesis. Splitting on any slash turned all three AC30 variants
// into an identical "AC30" chip and cut the fourth off mid-word as "AC30 (AC".
export function shortDesignation(desig) {
  return String(desig).split(/\s+\/\s+/)[0].trim();
}

// Load every family file, tag each model documented/ghost against the live corpus,
// and attach a slug + era span. Sorted by the first model's start year (oldest lines
// first) so the /history/ index and lineage lanes read chronologically.
export function loadHistory() {
  if (!fs.existsSync(HISTORY_DIR)) return [];
  const corpusIds = new Set(loadCorpus().map((a) => a.id));
  const fams = fs.readdirSync(HISTORY_DIR)
    .filter((f) => f.endsWith('.yaml'))
    .map((f) => {
      const fam = yaml.load(fs.readFileSync(path.join(HISTORY_DIR, f), 'utf8'));
      const slug = f.replace(/\.ya?ml$/, '');
      const models = (fam.models || []).map((m) => {
        const ref = m.circuit_ref ?? null;
        const documented = !!(ref && corpusIds.has(ref));
        return {
          ...m,
          circuit_ref: ref,
          documented,
          ampId: documented ? ref : null,
          shortDesig: shortDesignation(m.designation),
        };
      });
      const starts = models.map((m) => m.years?.start).filter((y) => y != null);
      const ends = models.map((m) => m.years?.end).filter((y) => y != null);
      return {
        slug,
        family: fam.family,
        title: fam.title,
        maker_style: fam.maker_style,
        summary: (fam.summary || '').trim(),
        notes: (fam.notes || '').trim(),
        models,
        documentedCount: models.filter((m) => m.documented).length,
        eraStart: starts.length ? Math.min(...starts) : null,
        eraEnd: ends.length ? Math.max(...ends) : null,
      };
    });
  return fams.sort((a, b) =>
    (a.eraStart ?? 9999) - (b.eraStart ?? 9999) || a.slug.localeCompare(b.slug));
}

// Reverse lookup: circuit id → the history family that documents it (title + slug),
// for the amp page's "Family line" link. Built once from loadHistory(); a documented
// circuit belongs to exactly one family (validate.py enforces uniqueness).
export function circuitFamilyMap() {
  const map = new Map();
  for (const fam of loadHistory()) {
    for (const m of fam.models) {
      if (m.documented && !map.has(m.ampId)) {
        map.set(m.ampId, { slug: fam.slug, title: fam.title, family: fam.family });
      }
    }
  }
  return map;
}

// --------------------------------------------------------- corpus by family
// The homepage grid is grouped by the amp line each circuit belongs to. The
// grouping key is the history family that documents the circuit — a reverse
// lookup through the family files' circuit_refs — so a circuit and its line
// carry the same name on both pages. A circuit no family file claims yet falls
// back to its own meta.family era string, so a newly added amp always lands
// under a heading rather than disappearing.
//
// Groups run oldest era first — the tweed lines, then blackface, then the British
// circuits — ranked by the earliest era style in the group and, on a tie, by the
// earliest year. Everything comes from the data; no list of amps or families is
// written down here.
//
// The order below IS meta.family's controlled vocabulary (docs/schema.md), in the
// order that enum declares, which already runs oldest first. It is written out
// rather than inferred so that a value the schema does not define sorts last and
// loudly instead of silently landing mid-list; ERA_STYLES must be kept in step with
// the schema enum. (It previously listed brown, brownface and silverface — none of
// which the schema defines, so they could never match — while omitting vox, which
// it does.)
const ERA_STYLES = ['tweed', 'blackface', 'british', 'vox', 'boutique', 'other'];

// "other" is the enum's catch-all for a circuit whose cosmetic era the vocabulary
// has no word for — the 6G3 brown Deluxe is the corpus's one case. It is a
// placeholder, not an era name, so it ranks but never captions a group.
const ERA_STYLE_PLACEHOLDER = 'other';

function eraRank(style) {
  const i = ERA_STYLES.indexOf(String(style || '').toLowerCase());
  return i === -1 ? ERA_STYLES.length : i;
}

export function corpusByFamily() {
  const famOf = circuitFamilyMap();
  const groups = new Map();
  for (const amp of loadCorpus()) {
    const fam = famOf.get(amp.id) || null;
    const style = amp.meta.family || 'other';
    const key = fam ? `history:${fam.slug}` : `era:${style}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        title: fam ? fam.title : style,
        href: fam ? `/history/${fam.slug}/` : null,
        inHistory: !!fam,
        amps: [],
      });
    }
    groups.get(key).amps.push(amp);
  }
  return [...groups.values()]
    .map((g) => {
      const starts = g.amps.map((a) => a.meta.era?.start).filter((y) => y != null);
      const ends = g.amps.map((a) => a.meta.era?.end).filter((y) => y != null);
      return {
        ...g,
        amps: [...g.amps].sort((a, b) =>
          (a.meta.era?.start ?? 0) - (b.meta.era?.start ?? 0) || a.id.localeCompare(b.id)),
        styles: [...new Set(g.amps.map((a) => a.meta.family)
          .filter((s) => s && s !== ERA_STYLE_PLACEHOLDER))],
        rank: Math.min(...g.amps.map((a) => eraRank(a.meta.family))),
        eraStart: starts.length ? Math.min(...starts) : null,
        eraEnd: ends.length ? Math.max(...ends) : null,
      };
    })
    .sort((a, b) => a.rank - b.rank
      || (a.eraStart ?? 9999) - (b.eraStart ?? 9999)
      || a.title.localeCompare(b.title));
}

// Split a pd_basis string ("pd-outright (published 1920)") into its leading
// controlled-vocabulary token and the human-readable remainder.
export function pdBasis(str) {
  if (!str) return { token: null, rest: '' };
  const token = str.split(/\s/)[0];
  const rest = str.slice(token.length).replace(/^[\s—–-]+/, '').trim();
  return { token, rest };
}

// -------------------------------------------------------------- tone-stack lib
// The tone-stack lab (/reference/guides/tone-stack-lab/) plots the frequency
// response of the passive control networks the corpus documents. No component
// value is written here: each preset names the reference designators, and the
// values are read out of that circuit's own bom.yaml at build time — so a curve
// on the page cannot drift away from the parts list it claims to plot.
//
// `drive` records how the network is fed, because it changes the answer. A
// cathode follower presents roughly 1/gm; a plate presents rp ∥ its plate load,
// with rp = µ/gm. Both figures come from the driving tube's published
// small-signal data in reference/tubes/*.yaml, never from a guess.

const SI_MULT = { p: 1e-12, n: 1e-9, 'µ': 1e-6, u: 1e-6, k: 1e3, M: 1e6 };

// "56 kΩ · ½ W" → 56000 · "0.02 µF · 400 V" → 2e-8 · "250 kΩ-A" → 250000.
export function componentValue(str) {
  const m = String(str).match(/([\d.]+)\s*(p|n|µ|u|k|M)?\s*(F|Ω)/u);
  if (!m) throw new Error(`tone-stack lab: cannot read a component value from "${str}"`);
  return parseFloat(m[1]) * (m[2] ? SI_MULT[m[2]] : 1);
}

// µ and gm as the tube's datasheet-anchor line records them, in SI units.
function tubeSmallSignal(tubeId) {
  const tube = loadTubes().find((t) => String(t.tube) === tubeId);
  const anchor = String(tube?.model?.anchor || '');
  const gm = /gm=([\d.]+)\s*µmho/.exec(anchor);
  const mu = /µ=([\d.]+)/.exec(anchor);
  if (!gm || !mu) throw new Error(`tone-stack lab: no small-signal anchor for ${tubeId}`);
  return { gm: parseFloat(gm[1]) * 1e-6, mu: parseFloat(mu[1]) };
}

// One entry per tone stack the corpus documents completely enough to plot.
// `refs` are reference designators in that amp's bom.yaml; `drive` and `load`
// name the stage feeding the network and the resistance hanging off its output.
// The stack's own wiring — which is common to every circuit in each group — is
// documented in site/src/lib/tonestack.js.
//
// This table is deliberately not generated. Every entry is a claim about how one
// circuit is wired — which part is the slope resistor, whether the middle leg is a
// pot or a fixed bleed, what drives the network — and those claims are read off the
// amp's own parts list and its recorded topology.tone_stack, not inferred. A circuit
// is listed only where its stack is one of the three networks tonestack.js actually
// solves. Six of the sixteen documented circuits that carry a tone control are
// therefore absent, and the guide page names all six:
//
//   ac15   topology.tone_stack: top-cut — a cap and pot across the two phase-inverter
//          outputs, a differential cut with no counterpart here. Not a variant of the
//          single-knob network; it would need its own model.
//   5d3    single-knob, but with a 500 pF treble path alongside the cut capacitor.
//   6g3    two single-knob controls, each with the same extra treble path.
//   5e3    single-knob (500 pF / 0.005 µF), but the control sits inside the amp's
//          interactive volume network rather than being fed from one stage, so the
//          single-resistance drive model this solver assumes does not describe it.
//   5f10   single-knob; not yet built as a preset.
//   aa764  a two-knob stack whose bass leg is a 15 kΩ resistor and a 0.047 µF cap,
//          and whose parts list labels the 0.1 µF as the bass cap — the opposite of
//          the ab763 convention. Resolving which capacitor sits where needs the
//          schematic read, not a guess, so it stays out until someone reads it.
//
// Adding one is cheap once the wiring is known; publishing a curve for a network
// that is not the circuit's own is not recoverable.
const TONE_STACK_SPECS = [
  {
    id: '5f6', kind: 'fmv',
    blurb: 'The 5F6 Bassman stack — the same network as the 5F6-A, but its parts list separates the bass and middle capacitors instead of printing one value for both.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C5', treblePot: 'VR3', bassCap: 'C6', bassPot: 'VR4', midCap: 'C7', midPot: 'VR5' },
  },
  {
    id: '5f6a', kind: 'fmv',
    blurb: 'The tweed Bassman network — the three-knob stack every later lead amp is measured against.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C4', treblePot: 'VR3', bassCap: 'C5', bassPot: 'VR4', midCap: 'C5', midPot: 'VR5' },
    note: 'The parts list records one 0.02 µF value covering both the bass and the mid position; both are plotted at it.',
  },
  {
    id: 'jtm45', kind: 'fmv',
    blurb: 'The same network as the Bassman with a slightly smaller treble cap and a 0.01 µF mid cap.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C4', treblePot: 'VR3', bassCap: 'C5', bassPot: 'VR4', midCap: 'C6', midPot: 'VR5' },
  },
  {
    id: 'm1987', kind: 'fmv',
    blurb: 'The British lead variant: a 33 kΩ slope resistor and a 500 pF treble cap move the whole curve.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C8', treblePot: 'VR3', bassCap: 'C9', bassPot: 'VR4', midCap: 'C10', midPot: 'VR5' },
  },
  {
    id: 'm1959', kind: 'fmv',
    blurb: 'The 100 W Super Lead carries the same stack as the 50 W head, component for component — the difference between the two amplifiers is downstream of this network, not in it.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C8', treblePot: 'VR3', bassCap: 'C9', bassPot: 'VR4', midCap: 'C10', midPot: 'VR5' },
  },
  {
    id: '5f4', kind: 'tb',
    blurb: 'The tweed two-knob stack — the three-knob network with the mid leg taken straight to ground.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C5', treblePot: 'VR3', bassCap: 'C7', bassPot: 'VR4' },
    midLeg: { kind: 'ground' },
    omits: ['C6'],
  },
  {
    id: 'ab763', kind: 'tb',
    blurb: 'The blackface two-knob stack, fed from a plate rather than a follower — the normal channel.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RLN1' },
    load: 'VRVN',
    refs: { slope: 'RSN', trebleCap: 'CTN', treblePot: 'VRTN', bassCap: 'CBN2', bassPot: 'VRBN' },
    midLeg: { kind: 'fixed', ref: 'RSLN' },
  },
  {
    id: 'aa964', kind: 'tb',
    blurb: 'The blackface Princeton runs the Deluxe Reverb\'s stack unchanged — 100 kΩ slope, 250 pF treble, 6.8 kΩ bleed — on the same 6V6 pair at roughly half the power.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RL1A' },
    load: 'VRV',
    refs: { slope: 'RS', trebleCap: 'CT', treblePot: 'VRT', bassCap: 'CB2', bassPot: 'VRB' },
    midLeg: { kind: 'fixed', ref: 'RBL' },
  },
  {
    id: 'aa1164', kind: 'tb',
    blurb: 'The Princeton Reverb keeps the same two-knob network its non-reverb sibling uses; adding the tank changed what feeds the stack, not the stack.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RLN1' },
    load: 'VRVOL',
    refs: { slope: 'RS', trebleCap: 'CT', treblePot: 'VRT', bassCap: 'CB2', bassPot: 'VRB' },
    midLeg: { kind: 'fixed', ref: 'RSL' },
  },
  {
    id: '5f2a', kind: 'single-knob',
    blurb: 'One knob: a rheostat and a small capacitor bleeding treble to ground.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'R4' },
    load: 'VR1',
    refs: { tonePot: 'VR2', cutCap: 'C3' },
  },
];

export const TONE_STACK_KINDS = {
  fmv: { label: 'Three-knob stack', controls: ['treble', 'mid', 'bass'] },
  tb: { label: 'Two-knob stack', controls: ['treble', 'bass'] },
  'single-knob': { label: 'Single tone control', controls: ['tone'] },
};

// Build every plottable preset: values resolved from the BOM, source and load
// resistances derived from published tube data and the circuit's own parts.
export function toneStackPresets() {
  const amps = new Map(loadCorpus().map((a) => [a.id, a]));
  return TONE_STACK_SPECS.map((spec) => {
    const amp = amps.get(spec.id);
    if (!amp) throw new Error(`tone-stack lab: no circuit "${spec.id}" in the corpus`);
    const byRef = new Map((amp.bom?.items || []).map((i) => [String(i.ref), i]));
    const item = (ref) => {
      const it = byRef.get(ref);
      if (!it) throw new Error(`tone-stack lab: ${spec.id} has no BOM entry ${ref}`);
      return it;
    };
    const val = (ref) => componentValue(item(ref).value);

    const { gm, mu } = tubeSmallSignal(spec.drive.tube);
    const rSource = spec.drive.kind === 'cathode-follower'
      ? 1 / gm
      : (() => { const rp = mu / gm, rl = val(spec.drive.plateLoad); return (rp * rl) / (rp + rl); })();
    const rLoad = val(spec.load);

    const parts = { rSource, rLoad };
    const bill = [];
    const push = (ref, role) => {
      const it = item(ref);
      if (!bill.some((b) => b.ref === ref)) bill.push({ ref, value: it.value, part: it.part, role });
    };

    if (spec.kind === 'single-knob') {
      parts.tonePot = val(spec.refs.tonePot);
      parts.cutCap = val(spec.refs.cutCap);
      push(spec.refs.tonePot, 'Tone pot');
      push(spec.refs.cutCap, 'Cut capacitor');
    } else {
      parts.slope = val(spec.refs.slope);
      parts.trebleCap = val(spec.refs.trebleCap);
      parts.treblePot = val(spec.refs.treblePot);
      parts.bassCap = val(spec.refs.bassCap);
      parts.bassPot = val(spec.refs.bassPot);
      parts.midCap = spec.refs.midCap ? val(spec.refs.midCap) : 0;
      parts.midPot = spec.refs.midPot ? val(spec.refs.midPot) : 0;
      parts.midFixed = spec.midLeg?.kind === 'fixed' ? val(spec.midLeg.ref) : 0;
      push(spec.refs.slope, 'Slope resistor');
      push(spec.refs.trebleCap, 'Treble capacitor');
      push(spec.refs.treblePot, 'Treble pot');
      push(spec.refs.bassCap, 'Bass capacitor');
      push(spec.refs.bassPot, 'Bass pot');
      if (spec.refs.midCap) push(spec.refs.midCap, 'Mid capacitor');
      if (spec.refs.midPot) push(spec.refs.midPot, 'Mid pot');
      if (spec.midLeg?.kind === 'fixed') push(spec.midLeg.ref, 'Fixed mid leg');
    }

    return {
      id: spec.id,
      kind: spec.kind,
      label: displayId(spec.id),
      style: amp.meta.name_style,
      era: amp.meta.era,
      blurb: spec.blurb,
      note: spec.note || null,
      controls: TONE_STACK_KINDS[spec.kind].controls,
      drive: {
        kind: spec.drive.kind,
        tube: item(spec.refs.slope ? spec.refs.slope : spec.refs.tonePot) && spec.drive.tube.toUpperCase(),
        ohms: rSource,
      },
      loadRef: spec.load,
      loadOhms: rLoad,
      midLeg: spec.midLeg?.kind || (spec.refs.midPot ? 'pot' : null),
      omits: (spec.omits || []).map((ref) => ({ ref, value: item(ref).value, role: item(ref).role })),
      bill,
      parts,
      topologyHref: topologyHref('tone_stack', amp.meta),
    };
  });
}

// Circuit ids that the lab carries a preset for — the amp pages use this to
// decide whether to offer the "plot this stack" link.
export function toneStackPresetIds() {
  return new Set(TONE_STACK_SPECS.map((s) => s.id));
}
