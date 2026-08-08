// Build-time corpus loader — reads ../amps/*/ (meta.yaml, voltages.yaml,
// notes.md) so every page on the site is generated from the repo data.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
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
      // Intrinsic width of the redrawn board diagram, in its own viewBox units.
      // The board drawings span 1000 (5F1) to 4400 (Model 1959) units at one
      // fixed type size, so the viewer cannot scale them all to one column
      // width — the biggest would render its 11.5-unit part labels at under
      // 3 CSS px. The page uses this to give each drawing a floor width and
      // scroll the overflow. See layoutMinWidth().
      const layoutSvg = readIfExists(path.join(dir, 'layout.svg'));
      const vb = layoutSvg ? /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(layoutSvg) : null;
      // The era layout-sheet drawing of the same board: same layout.yaml, same
      // geometry and the same viewBox, only the drafting style differs. The amp
      // page shows it by default and offers the house drawing beside it.
      const hasLayoutSheet = fs.existsSync(path.join(dir, 'layout-sheet.svg'));
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
        hasLayout: !!layoutSvg,
        hasLayoutSheet,
        layoutWidth: vb ? Number(vb[1]) : null,
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

// Minimum on-screen width (CSS px) for a board drawing of `units` viewBox units.
// Type in these drawings is set in viewBox units (7.5 for a socket pin number,
// 11–12 for a part label), so legibility is a question of scale, not of column
// width: below about 0.62 the 11.5-unit labels fall under 7 CSS px and the
// drawing reads as a grey smear. Small boards keep fitting the column (the
// floor is under the column width, so `max()` leaves them alone); big ones
// overflow their scroll container instead of shrinking.
export const LAYOUT_MIN_SCALE = 0.62;

export function layoutMinWidth(amp) {
  const units = amp?.layoutWidth;
  return units ? Math.round(units * LAYOUT_MIN_SCALE) : null;
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
// `style` names which of the two drawings of that same board is being described
// — 'current' (the house style) or 'sheet' (the era layout-sheet drafting
// style, which letters each part's value on its body in period shorthand). The
// provenance sentence is identical in both: the styles differ in how the board
// is drawn, never in what is claimed about it.
export function layoutAlt(amp, style = 'current') {
  const name = displayId(amp.id);
  const { kind, derived } = amp.layoutBoard || boardType(amp.layout);
  const board = kind === 'circuit' ? 'board' : `${kind} board`;
  const drawn = style === 'sheet'
    ? ', drawn in the period layout-sheet style with each value lettered on the part'
    : '';
  return derived
    ? `${name} ${board} layout — an original diagram reconstructed from the redrawn schematic (no factory layout sheet exists), showing the principal parts in board order${drawn}.`
    : `${name} ${board} layout — an original diagram redrawn from the published layout drawing, showing the principal parts in the order that drawing places them on the board${drawn}.`;
}

// A per-amp meta description built from the circuit's own metadata (era, output,
// tube lineup, topology) so every amp page reads distinctly — 5E1 vs 5F1, etc.
// The closing artifact sentence is keyed to verification.status: only a circuit
// whose operating point actually passed the chart gate advertises published-chart
// operating points; a draft's operating point is simulated (its page badge says
// so), and its description must say the same rather than borrow the claim.
export function ampMetaDescription(m) {
  const tubes = (m.tubes || []).join(', ');
  const rect = m.topology?.rectifier?.type || m.topology?.rectifier?.kind || 'tube';
  const bias = m.topology?.bias ? `${m.topology.bias}-bias` : null;
  const pi = m.topology?.phase_inverter && m.topology.phase_inverter !== 'none'
    ? `${m.topology.phase_inverter} phase inverter` : null;
  const topo = [bias, pi].filter(Boolean).join(', ');
  const era = m.era ? `${m.era.start}–${m.era.end}` : '';
  const artifacts = m.verification?.status === 'verified'
    ? 'Redrawn KiCad schematic, ngspice-verified netlist, published-chart operating points, and structured metadata.'
    : 'Redrawn KiCad schematic, ngspice netlist, simulated draft operating points, and structured metadata.';
  return `${m.name_style} (${era}), ${m.wattage} W on ${tubes}` +
    (topo ? `, ${topo}` : '') + `, ${rect} rectifier. ` + artifacts;
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
  let md = fs.readFileSync(filePath, 'utf8');
  // Optional YAML frontmatter. `added` records the day the study was published
  // (its feed date) — explicit, because the production build is a shallow clone
  // whose git history cannot date anything (see gitCreationDate).
  let front = {};
  const fm = md.match(/^---\n([\s\S]*?)\n---\n/);
  if (fm) {
    front = yaml.load(fm[1]) || {};
    md = md.slice(fm[0].length);
  }
  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;
  // Subtitle: a leading italic line just under the H1 (e.g. *A metrology study…*).
  const subMatch = md.match(/^#\s+.+\n+\*(.+?)\*\s*$/m);
  const subtitle = subMatch ? subMatch[1].trim() : null;
  // Strip H1 and the subtitle line from the rendered body — they become the header.
  let body = md.replace(/^#\s+.+\n/, '');
  if (subtitle) body = body.replace(/^\s*\*.+?\*\s*\n/, '');
  return { slug, title, subtitle, added: front.added ?? null, html: marked.parse(body) };
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
// `wiring` names which of the two stack wirings the amp's own schematic draws —
// 'ladder' (the published-sheet form: treble-wiper-only output, bass rheostat,
// mid cap into the mid wiper) or 'joined' (the textbook form: wipers joined at
// one output node). Both are documented in site/src/lib/tonestack.js, and
// pipeline/check_tonestack_wiring.py asserts each drawing against the wiring
// its preset claims.
//
// This table is deliberately not generated. Every entry is a claim about how one
// circuit is wired — which part is the slope resistor, whether the middle leg is a
// pot or a fixed bleed, what drives the network — and those claims are read off the
// amp's own parts list and its recorded topology.tone_stack, not inferred. A circuit
// is listed only where its stack is one of the networks tonestack.js actually
// solves. Six of the sixteen documented circuits that carry a tone control are
// therefore absent, and the guide page names all six — it counts them out of the
// corpus rather than repeating a number, so the two cannot drift apart:
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
//   aa764  a two-knob stack drawn as the same ladder the AA964 preset now solves
//          (treble-wiper output, bass rheostat), with its own part roles
//          (0.047 µF, 15 kΩ leg). Its wiring is read and gate-checked (see
//          TONE_STACK_GATE_EXTRAS below); it is absent here only because it has
//          not yet been built into a preset entry, not because the solver lacks
//          its network.
//
// Adding one is cheap once the wiring is known; publishing a curve for a network
// that is not the circuit's own is not recoverable.
const TONE_STACK_SPECS = [
  {
    id: '5f6', kind: 'fmv', wiring: 'ladder',
    blurb: 'The first Fender three-knob stack, plotted as the 5F6 sheet draws it: the output is the treble wiper alone, the bass pot is a rheostat in the ladder, and the middle capacitor feeds the middle pot\'s wiper.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C5', treblePot: 'VR3', bassCap: 'C6', bassPot: 'VR4', midCap: 'C7', midPot: 'VR5' },
    midLeg: { kind: 'series', ref: 'VR6' },
    note: 'The 5F6 returns the middle control\'s foot to ground through the 5 kΩ presence pot instead of straight to ground — the arrangement the 5F6-A moved to the phase-inverter tail. The curve is plotted with Presence at the end of its travel that leaves no resistance in the leg; winding it up adds up to 5 kΩ under the middle control and lifts the notch a little.',
  },
  {
    id: '5f6a', kind: 'fmv', wiring: 'ladder',
    blurb: 'The tweed Bassman network — the three-knob stack every later lead amp is measured against, plotted as the 5F6-A sheet draws it: treble-wiper output, bass rheostat in the ladder, middle capacitor into the middle pot\'s wiper.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C4', treblePot: 'VR3', bassCap: 'C5', bassPot: 'VR4', midCap: 'C5b', midPot: 'VR5' },
    note: 'The parts list records one 0.02 µF value covering both the bass and the mid position; both are plotted at it. Unlike the 5F6, the middle pot\'s foot runs straight to ground — the presence control moved to the phase-inverter tail.',
  },
  {
    id: 'jtm45', kind: 'fmv', wiring: 'ladder',
    blurb: 'The Bassman ladder with a slightly smaller treble cap and a 0.01 µF mid cap, plotted as the Marshall drawing wires it: treble-wiper output, bass rheostat, mid cap into the middle pot\'s wiper.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C4', treblePot: 'VR3', bassCap: 'C5', bassPot: 'VR4', midCap: 'C6', midPot: 'VR5' },
  },
  {
    id: 'm1987', kind: 'fmv', wiring: 'ladder',
    blurb: 'The British lead variant: a 33 kΩ slope resistor and a 500 pF treble cap move the whole curve. Plotted as the Unicord drawing wires it — the same ladder as the JTM45.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C8', treblePot: 'VR3', bassCap: 'C9', bassPot: 'VR4', midCap: 'C10', midPot: 'VR5' },
  },
  {
    id: 'm1959', kind: 'fmv', wiring: 'ladder',
    blurb: 'The 100 W Super Lead carries the same stack as the 50 W head, component for component and wire for wire — the difference between the two amplifiers is downstream of this network, not in it.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    load: 'RGA',
    refs: { slope: 'RSL', trebleCap: 'C8', treblePot: 'VR3', bassCap: 'C9', bassPot: 'VR4', midCap: 'C10', midPot: 'VR5' },
  },
  {
    id: '5f4', kind: 'split', wiring: 'split',
    blurb: 'The tweed Super\'s tone circuit as the 5F4 sheet draws it — not a two-knob cut of the Bassman ladder but a different network: treble on a 250 pF divider with its cold end bled to ground through 0.01 µF, bass on a 0.1 µF-coupled chain injected into the bass pot\'s wiper, the two recombined through 220 kΩ at the phase inverter\'s grid.',
    drive: { kind: 'cathode-follower', tube: '12ax7' },
    refs: { trebleCap: 'C5', treblePot: 'VR3', trebleShuntCap: 'C6', bassCoupler: 'C16', bassShunt: 'RSH', bassSeries: 'RSL', bassPot: 'VR4', bassLegCap: 'C7', outSeries: 'RSR' },
    note: 'The stack output runs straight into the phase inverter\'s grid — no coupling capacitor and no grid-leak resistor load it, so no load resistor is entered here. The 4.7 MΩ feedback resistor returning to the bass branch is not modelled; it is large beside every impedance in the network.',
  },
  {
    id: 'ab763', kind: 'tb', wiring: 'ladder',
    blurb: 'The blackface two-knob stack, fed from a plate rather than a follower — the normal channel, plotted as the AB763 sheet wires it: treble-wiper output and a bass rheostat above the fixed 6.8 kΩ leg. The vibrato channel draws the identical network.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RLN1' },
    load: 'VRVN',
    refs: { slope: 'RSN', trebleCap: 'CTN', treblePot: 'VRTN', bassCap: 'CBN', bassPot: 'VRBN', midCap: 'CBN2' },
    midLeg: { kind: 'fixed', ref: 'RSLN' },
  },
  {
    id: 'aa964', kind: 'tb', wiring: 'ladder',
    blurb: 'The blackface Princeton\'s two-knob stack — 100 kΩ slope, 250 pF treble, 6.8 kΩ bleed — plotted as the AA964 sheet wires it: the output is the treble wiper alone and the bass pot is a rheostat above the fixed leg.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RL1A' },
    load: 'VRV',
    refs: { slope: 'RS', trebleCap: 'CT', treblePot: 'VRT', bassCap: 'CB1', bassPot: 'VRB', midCap: 'CB2' },
    midLeg: { kind: 'fixed', ref: 'RBL' },
  },
  {
    id: 'aa1164', kind: 'tb', wiring: 'ladder',
    blurb: 'The Princeton Reverb keeps the same two-knob network its non-reverb sibling uses, wire for wire — the AA1164 sheet draws the same ladder as the AA964: treble-wiper output, bass rheostat, 6.8 kΩ fixed leg. Adding the tank changed what feeds the stack, not the stack.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'RLN1' },
    load: 'VRVOL',
    refs: { slope: 'RS', trebleCap: 'CT', treblePot: 'VRT', bassCap: 'CB1', bassPot: 'VRB', midCap: 'CB2' },
    midLeg: { kind: 'fixed', ref: 'RSL' },
  },
  {
    // 'treble-cut' is a name, not a stack wiring: the network is a rheostat and
    // a capacitor bleeding treble to ground (trebleCutElements), so neither
    // 'ladder' nor 'joined' describes it. Declared explicitly so no preset falls
    // back to the 'joined' default silently.
    id: '5f2a', kind: 'single-knob', wiring: 'treble-cut',
    blurb: 'One knob: a rheostat and a small capacitor bleeding treble to ground.',
    drive: { kind: 'plate', tube: '12ax7', plateLoad: 'R4' },
    load: 'VR1',
    refs: { tonePot: 'VR2', cutCap: 'C3' },
  },
];

// Read but not plotted: multi-knob tone networks the wiring gate asserts that
// the lab does not (yet) carry as a preset. pipeline/check_tonestack_wiring.py
// reads this table alongside TONE_STACK_SPECS, so every drawing the corpus
// claims to have read at lug level is walked by the same gate — and the refs
// live here, beside the preset table, so the two cannot drift apart.
//
//   ab763 vibrato — the AB763 draws its two-knob ladder twice, once per
//     channel; the preset above solves the normal channel's designators, and
//     this entry makes the vibrato channel's drawing gated too.
//   aa764 — read at lug level (treble-wiper output, bass rheostat, 15 kΩ leg)
//     but not yet built into a preset; see the absence note above.
// eslint-disable-next-line no-unused-vars -- read by pipeline/check_tonestack_wiring.py
const TONE_STACK_GATE_EXTRAS = [
  {
    id: 'ab763', kind: 'tb', wiring: 'ladder', channel: 'vibrato',
    refs: { slope: 'RSV', trebleCap: 'CTV', treblePot: 'VRTV', bassCap: 'CBV', bassPot: 'VRBV', midCap: 'CBV2' },
    midLeg: { kind: 'fixed', ref: 'RSLV' },
  },
  {
    id: 'aa764', kind: 'tb', wiring: 'ladder',
    refs: { slope: 'R6', trebleCap: 'C2', treblePot: 'VR2', bassCap: 'C3', bassPot: 'VR3', midCap: 'C4' },
    midLeg: { kind: 'fixed', ref: 'R7' },
  },
];

export const TONE_STACK_KINDS = {
  fmv: { label: 'Three-knob stack', controls: ['treble', 'mid', 'bass'] },
  tb: { label: 'Two-knob stack', controls: ['treble', 'bass'] },
  split: { label: 'Split treble/bass', controls: ['treble', 'bass'] },
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
    // A spec without a load names none because its stack output really drives
    // nothing but the next grid (the 5F4's runs straight into the phase
    // inverter with no coupling network) — solved unloaded, and said so.
    const rLoad = spec.load ? val(spec.load) : 0;

    const parts = { rSource, rLoad, wiring: spec.wiring || 'joined' };
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
    } else if (spec.kind === 'split') {
      parts.trebleCap = val(spec.refs.trebleCap);
      parts.treblePot = val(spec.refs.treblePot);
      parts.trebleShuntCap = val(spec.refs.trebleShuntCap);
      parts.bassCoupler = val(spec.refs.bassCoupler);
      parts.bassShunt = val(spec.refs.bassShunt);
      parts.bassSeries = val(spec.refs.bassSeries);
      parts.bassPot = val(spec.refs.bassPot);
      parts.bassLegCap = val(spec.refs.bassLegCap);
      parts.outSeries = val(spec.refs.outSeries);
      push(spec.refs.trebleCap, 'Treble capacitor');
      push(spec.refs.treblePot, 'Treble pot');
      push(spec.refs.trebleShuntCap, 'Treble-pot cold-end capacitor to ground');
      push(spec.refs.bassCoupler, 'Bass-branch coupling capacitor');
      push(spec.refs.bassShunt, 'Bass-branch leak to ground');
      push(spec.refs.bassSeries, 'Bass-branch series resistor');
      push(spec.refs.bassPot, 'Bass pot (branch injected at its wiper)');
      push(spec.refs.bassLegCap, 'Bass-pot leg capacitor to ground');
      push(spec.refs.outSeries, 'Series resistor into the output node');
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
      wiring: spec.wiring || 'joined',
      label: displayId(spec.id),
      style: amp.meta.name_style,
      era: amp.meta.era,
      blurb: spec.blurb,
      note: spec.note || null,
      controls: TONE_STACK_KINDS[spec.kind].controls,
      drive: {
        kind: spec.drive.kind,
        tube: spec.drive.tube.toUpperCase(),
        ohms: rSource,
      },
      loadRef: spec.load || null,
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

// ------------------------------------------------------------- dates for feeds
// A dated entry needs a date the repository can actually prove. The sources, in
// order: a verified circuit carries verification.date, every draft circuit and
// study carries an explicit `added` date in its own file (validate.py requires it
// of drafts), and — as a local-only backstop — a full git checkout knows when a
// file first appeared. The explicit dates are what production uses: Workers Builds
// clones shallow, so the git fallback correctly reports nothing there. Where every
// source is absent, the entry ships without a date rather than with today's.

let _gitUsable = null;
function gitUsable() {
  if (_gitUsable !== null) return _gitUsable;
  try {
    const shallow = execFileSync('git', ['rev-parse', '--is-shallow-repository'],
      { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    // A shallow clone (CI checkouts, `clone --depth 1`) reports every path as first
    // seen at the single grafted commit, which would date the whole corpus to the
    // day of the build. Treat that as "no date available".
    _gitUsable = shallow === 'false';
  } catch {
    _gitUsable = false; // no git binary, or not a checkout
  }
  return _gitUsable;
}

// Date a file first entered the repository, or null when that cannot be known.
// Takes a single file path — `--follow` (which carries the date across renames)
// accepts exactly one pathspec.
export function gitCreationDate(relPath) {
  if (!gitUsable()) return null;
  try {
    const out = execFileSync(
      'git', ['log', '--diff-filter=A', '--follow', '--format=%aI', '-1', '--', relPath],
      { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (!out) return null;
    const d = new Date(out);
    return isNaN(d) ? null : d;
  } catch {
    return null;
  }
}

function asDate(v) {
  if (!v) return null;
  const d = v instanceof Date ? v : new Date(v);
  return isNaN(d) ? null : d;
}

// ------------------------------------------------------------------- feed items
// One entry per documented circuit and per reference study, newest first, undated
// entries last. A circuit is dated by the day its operating point was verified
// against the published chart, otherwise by its explicit `added` date; a study by
// its frontmatter `added`. The git-creation fallback only matters in a full local
// checkout — production builds are shallow clones, where it yields nothing.
export function feedEntries() {
  const circuits = loadCorpus().map((amp) => {
    const m = amp.meta;
    const verified = m.verification?.status === 'verified';
    const date = asDate(m.verification?.date) || asDate(m.added)
      || gitCreationDate(`amps/${amp.id}/meta.yaml`);
    return {
      kind: 'circuit',
      title: `${displayId(amp.id)} — ${m.name_style}`,
      link: `/amps/${amp.id}/`,
      description: `${verified ? 'Verified circuit' : 'Draft circuit'}: ${ampMetaDescription(m)}`,
      categories: ['Circuit', verified ? 'Verified' : 'Draft'],
      date,
    };
  });
  const studies = loadStudies().map((s) => ({
    kind: 'study',
    title: s.title,
    link: `/reference/studies/${s.slug}/`,
    description: s.subtitle || `A Circuit Codex reference study: ${s.title}.`,
    categories: ['Study'],
    date: asDate(s.added) || gitCreationDate(`reference/studies/${s.slug}.md`),
  }));
  return [...circuits, ...studies].sort((a, b) => {
    if (a.date && b.date) return b.date - a.date;
    if (a.date) return -1;
    if (b.date) return 1;
    return a.title.localeCompare(b.title);
  });
}

// --------------------------------------------------------------- dataset record
// The corpus described as one machine-readable Dataset (schema.org), for Google
// Dataset Search and any other catalogue that reads structured data. Every field is
// computed from the repository or fixed by its licence files — nothing is asserted
// here that the corpus does not carry.

export const DATA_LICENSE = 'https://creativecommons.org/licenses/by-sa/4.0/';
export const REPO_ARCHIVE = `${GITHUB}/archive/refs/heads/main.zip`;

// Earliest and latest production year the archive covers, taken from the circuits'
// own era spans and the history tier's model years — so adding a 1940s model or a
// later revision moves the coverage without anyone editing prose.
export function corpusTemporalCoverage() {
  const years = [];
  for (const a of loadCorpus()) {
    if (a.meta.era?.start) years.push(a.meta.era.start);
    if (a.meta.era?.end) years.push(a.meta.era.end);
  }
  for (const fam of loadHistory()) {
    for (const m of fam.models) {
      if (m.years?.start) years.push(m.years.start);
      if (m.years?.end) years.push(m.years.end);
    }
  }
  if (!years.length) return null;
  return `${Math.min(...years)}/${Math.max(...years)}`;
}

// Most recent date the corpus can prove something changed: the newest verification
// date on any circuit. Understates rather than overstates — a draft added since then
// carries no date of its own.
function corpusDateModified() {
  const dates = loadCorpus()
    .map((a) => asDate(a.meta.verification?.date))
    .filter(Boolean);
  return dates.length ? new Date(Math.max(...dates)).toISOString().slice(0, 10) : null;
}

export function datasetJsonLd(site) {
  const base = site ? new URL('/', site).href : 'https://circuitcodex.com/';
  const stats = corpusStats();
  const coverage = corpusTemporalCoverage();
  const modified = corpusDateModified();
  const ids = loadCorpus().map((a) => displayId(a.id));
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    // One stable identity for the one dataset: the / and /about/ copies of this
    // block carry the same @id, so catalogues merge them instead of counting two.
    '@id': `${base}#dataset`,
    name: 'Circuit Codex — vintage guitar tube-amplifier circuit corpus',
    alternateName: 'Circuit Codex corpus',
    description:
      `Structured, machine-readable records for ${stats.circuits} vintage guitar tube-amplifier ` +
      `circuits (${stats.verified} with DC operating points verified against their published ` +
      `voltage charts): independently redrawn KiCad schematics, ngspice netlists, parts lists, ` +
      `board layouts, and circuit metadata (era, tube complement, rectifier, bias, phase inverter, ` +
      `tone stack). Includes ${stats.models} clean-room tube SPICE models dedicated to the public ` +
      `domain and a history tier placing ${stats.historyModels} models across ${stats.families} ` +
      `amplifier lines. Circuit data CC-BY-SA-4.0; tube models CC0.`,
    url: base,
    sameAs: GITHUB,
    license: DATA_LICENSE,
    isAccessibleForFree: true,
    inLanguage: 'en',
    creator: { '@type': 'Organization', name: 'The Analog Maker', url: base },
    publisher: { '@type': 'Organization', name: 'Circuit Codex', url: base },
    keywords: [
      'guitar amplifier', 'vacuum tube amplifier', 'tube amp circuits', 'schematic',
      'SPICE netlist', 'ngspice', 'KiCad', 'tube SPICE models', 'voltage chart',
      'eyelet board layout', 'tone stack', 'phase inverter', 'amplifier history',
      ...ids,
    ],
    ...(coverage ? { temporalCoverage: coverage } : {}),
    ...(modified ? { dateModified: modified } : {}),
    // "or cited published measurements": not every verified circuit has a factory
    // chart — the 5E3 verifies against Robinette's published measurements — and the
    // technique statement must cover what the gate actually compares against.
    measurementTechnique:
      'ngspice DC operating-point simulation of each redrawn netlist, compared node by node ' +
      'against the circuit\'s published factory voltage chart or cited published measurements',
    variableMeasured: [
      { '@type': 'PropertyValue', name: 'DC node voltage', unitText: 'V' },
      { '@type': 'PropertyValue', name: 'Component value', description: 'Resistance (Ω), capacitance (F) and voltage rating per parts-list entry' },
      { '@type': 'PropertyValue', name: 'Rated output power', unitText: 'W' },
    ],
    distribution: [
      {
        '@type': 'DataDownload',
        name: 'Corpus repository archive (ZIP)',
        description: 'Full repository snapshot: amps/, models/, history/ and reference/ data.',
        encodingFormat: 'application/zip',
        contentUrl: REPO_ARCHIVE,
      },
      {
        '@type': 'DataDownload',
        name: 'Circuit metadata and netlists (Git repository)',
        description: 'Per-circuit meta.yaml, voltages.yaml, bom.yaml, layout.yaml and netlist.cir.',
        encodingFormat: 'text/yaml',
        contentUrl: GITHUB,
      },
    ],
  };
}

// ------------------------------------------------------------------ breadcrumbs
// BreadcrumbList in schema.org terms. Callers pass the trail as {name, url} pairs
// (paths are resolved against the site origin); the leaf keeps its own URL so the
// list is self-describing.
export function breadcrumbJsonLd(trail, site) {
  const abs = (u) => (site ? new URL(u, site).href : u);
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: trail.map((c, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: c.name,
      item: abs(c.url),
    })),
  };
}
