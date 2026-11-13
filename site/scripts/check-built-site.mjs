// Run from site/ after `npm run build`: node --test scripts/check-built-site.mjs
// Checks on the built output (dist/) that no source-level test can see.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const dist = new URL('../dist/', import.meta.url);
const read = (rel) => fs.readFileSync(new URL(rel, dist), 'utf8');

// Every corrections-feed link is a fragment on /corrections/, and must name an
// entry that page carries. @astrojs/rss appends a slash by default, which lands
// after the fragment (#id/) and matches nothing.
test('corrections feed links land on their entries', () => {
  const feed = read('corrections.xml');
  const page = read('corrections/index.html');
  const links = [...feed.matchAll(/<link>([^<]+)<\/link>/g)].map((m) => m[1]).slice(1); // [0] is the channel
  assert.ok(links.length > 0, 'the feed has items');
  for (const link of links) {
    const url = new URL(link);
    assert.equal(url.pathname, '/corrections/', link);
    const id = decodeURIComponent(url.hash.slice(1));
    assert.ok(page.includes(`id="${id}"`), `${link} names no element on /corrections/`);
  }
});

// Every JSON data block in every page parses, and carries no raw "<": the HTML
// parser ends a script element at the first "</script" in its text, so one data
// string holding it would spill the rest of the block into the page. Built with
// jsonForScript() (src/lib/json-script.js).
import { jsonForScript } from '../src/lib/json-script.js';

test('jsonForScript leaves the parser nothing to stop on', () => {
  const value = { note: 'see </script><script>alert(1)</script> & <b>', n: 5 };
  const text = jsonForScript(value);
  assert.ok(!text.includes('<'));
  assert.deepEqual(JSON.parse(text), value);
});

test('every JSON script block in dist parses and holds no raw "<"', () => {
  const pages = fs.readdirSync(dist, { recursive: true }).filter((f) => String(f).endsWith('.html'));
  let blocks = 0;
  for (const page of pages) {
    const html = read(String(page));
    for (const m of html.matchAll(/<script type="application\/(?:ld\+)?json"[^>]*>([\s\S]*?)<\/script>/g)) {
      blocks++;
      assert.doesNotThrow(() => JSON.parse(m[1]), `${page}: a JSON block does not parse`);
      assert.ok(!m[1].includes('<'), `${page}: a JSON block holds a raw "<"`);
    }
  }
  assert.ok(blocks > 100, `expected the site's JSON blocks, found ${blocks}`);
});
