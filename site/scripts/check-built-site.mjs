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
