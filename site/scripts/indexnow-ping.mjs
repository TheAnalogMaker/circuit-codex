#!/usr/bin/env node
// IndexNow submission — tells Bing, Yandex, Seznam and the other IndexNow
// participants which URLs this deploy published, instead of waiting for a crawl.
//
// Runs at the very end of `npm run build`, after the sitemap exists in dist/. It is
// NOT a gate: search-engine notification is not a correctness claim about the
// corpus, so every failure path here logs and exits 0. A deploy must never fail
// because api.indexnow.org was slow.
//
// The key is public by design: IndexNow authenticates a submission by fetching
// https://circuitcodex.com/<key>.txt and checking that it contains the same key.
// Both live in this repository (site/public/<key>.txt).
//
// Local builds do not ping. Set INDEXNOW=1 to force a submission from a local
// build, or INDEXNOW=0 to suppress one in CI.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = 'https://circuitcodex.com';
const KEY = '2347ca0945d26f7da247b3381d5b3f59';
const ENDPOINT = 'https://api.indexnow.org/indexnow';
const TIMEOUT_MS = 15000;
const MAX_URLS = 10000; // IndexNow's per-submission ceiling

const DIST = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');

const log = (msg) => console.log(`[indexnow] ${msg}`);

// Deploy builds only, unless told otherwise. Workers Builds and GitHub Actions both
// set CI; WORKERS_CI and CF_PAGES identify the Cloudflare build environments.
function shouldPing() {
  if (process.env.INDEXNOW === '0') return false;
  if (process.env.INDEXNOW === '1') return true;
  return Boolean(process.env.WORKERS_CI || process.env.CF_PAGES || process.env.CI);
}

// Every <loc> in the built sitemap, following the sitemap index to its children.
// The sitemap is what @astrojs/sitemap generated from the pages that actually
// built, so the submission cannot name a URL this deploy does not serve.
function readSitemapUrls() {
  const index = path.join(DIST, 'sitemap-index.xml');
  if (!fs.existsSync(index)) return [];
  const locs = (xml) => [...xml.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/g)].map((m) => m[1]);
  const urls = new Set();
  for (const child of locs(fs.readFileSync(index, 'utf8'))) {
    const file = path.join(DIST, path.basename(new URL(child).pathname));
    if (!fs.existsSync(file)) continue;
    for (const u of locs(fs.readFileSync(file, 'utf8'))) {
      if (u.startsWith(SITE)) urls.add(u);
    }
  }
  return [...urls].sort();
}

async function main() {
  if (!shouldPing()) {
    log('local build — skipped (set INDEXNOW=1 to submit)');
    return;
  }
  const urlList = readSitemapUrls().slice(0, MAX_URLS);
  if (!urlList.length) {
    log('no sitemap URLs found — nothing submitted');
    return;
  }
  const body = {
    host: new URL(SITE).host,
    key: KEY,
    keyLocation: `${SITE}/${KEY}.txt`,
    urlList,
  };
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: JSON.stringify(body),
      signal: ac.signal,
    });
    // 200 accepted, 202 accepted but key still being validated. Anything else is
    // reported and ignored.
    log(`${res.status} ${res.statusText} — submitted ${urlList.length} URLs`);
  } catch (err) {
    log(`submission failed (ignored): ${err?.message || err}`);
  } finally {
    clearTimeout(timer);
  }
}

main().catch((err) => {
  log(`unexpected error (ignored): ${err?.message || err}`);
});
