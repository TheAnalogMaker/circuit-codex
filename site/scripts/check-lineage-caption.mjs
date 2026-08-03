// Regression gate for the lineage figure's prose.
//
// The /lineage/ chart draws a derivation arrow for every documented cross-family
// derivation in the corpus, and the caption under it enumerates those arrows by
// name. The two must not drift: when the corpus grew a second arrow, a caption that
// named only the first ("here, the tweed 5F6-A Bassman to the Marshall JTM45") read
// as a complete list to anyone counting arrows on the chart. This gate reads the
// built page and proves the prose still names every arrow the SVG draws, and only
// those — for the figcaption and for the page's own meta description.
//
// Run from site/ after `npm run build`:  node scripts/check-lineage-caption.mjs

import fs from 'node:fs';
import path from 'node:path';

const PAGE = path.join(process.cwd(), 'dist', 'lineage', 'index.html');
if (!fs.existsSync(PAGE)) {
  console.error(`lineage caption gate: ${PAGE} not found — run \`npm run build\` first`);
  process.exit(2);
}
const html = fs.readFileSync(PAGE, 'utf8');
const strip = (s) => s.replace(/<[^>]+>/g, '').replace(/&#8202;|&nbsp;/g, ' ')
  .replace(/&amp;/g, '&').replace(/&#[0-9]+;/g, ' ').replace(/\s+/g, ' ').trim();

// --- what the chart draws
const edges = [...html.matchAll(/data-edge="([^"]+)"/g)].map((m) => m[1]);
// chip label for each documented circuit, read off the chips themselves
const labels = new Map();
for (const m of html.matchAll(/<a class="node doc[^"]*" href="\/amps\/([^/]+)\/"[^>]*>([\s\S]*?)<\/a>/g)) {
  const cid = /<text class="cid"[^>]*>([\s\S]*?)<\/text>/.exec(m[2]);
  if (cid) labels.set(m[1], strip(cid[1]).replace(/\s*✓$/, '').trim());
}

// --- what the prose says
const figcaption = strip(/<figcaption[^>]*>([\s\S]*?)<\/figcaption>/.exec(html)[1]);
const metaDesc = /<meta name="description" content="([^"]*)"/.exec(html)[1];
const NUM = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];

let failures = 0;
const fail = (msg) => { console.error(`  FAIL  ${msg}`); failures++; };

const stated = /The chart draws (\w+) arrows?:/.exec(figcaption);
if (!stated) fail('figcaption does not state how many arrows the chart draws');
else if (NUM.indexOf(stated[1]) !== edges.length)
  fail(`figcaption says "${stated[1]}" arrow(s); the SVG draws ${edges.length}`);

if (!edges.length) fail('the chart draws no derivation arrow at all');

for (const e of edges) {
  const [parent, child] = e.split('->');
  for (const id of [parent, child]) {
    const label = labels.get(id);
    if (!label) { fail(`arrow ${e}: no chip found for ${id}`); continue; }
    if (!figcaption.includes(label)) fail(`arrow ${e}: figcaption does not name ${label}`);
    if (!metaDesc.includes(label)) fail(`arrow ${e}: meta description does not name ${label}`);
  }
}
// nothing may be named as an arrow endpoint that is not one
const drawn = new Set(edges.flatMap((e) => e.split('->').map((id) => labels.get(id))));
const named = /The chart draws \w+ arrows?: (.*?)\. Each arrow/.exec(figcaption);
if (named) {
  for (const [, label] of labels) {
    if (drawn.has(label)) continue;
    if (new RegExp(`(^|[^A-Z0-9-])${label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^A-Z0-9-]|$)`).test(named[1]))
      fail(`figcaption names ${label} among the arrows, but no arrow touches it`);
  }
}

if (failures) {
  console.error(`lineage caption gate: ${failures} problem(s)`);
  process.exit(1);
}
console.log(`lineage caption gate ok — ${edges.length} arrow(s) drawn and named: ${edges.join(', ')}`);
