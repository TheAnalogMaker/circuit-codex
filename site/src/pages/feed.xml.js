// /feed.xml — the archive's own feed: one entry per documented circuit and per
// reference study, newest first. Dates come from the repository (a circuit's
// verification date, otherwise its explicit `added` date; git only as a local
// backstop); an entry whose date cannot be established ships without one rather
// than with the build date, so the feed never claims a publication day it cannot
// prove. See feedEntries().
//
// Served as a static asset by Cloudflare Workers, which types .xml files as
// application/xml — acceptable for feed readers (application/rss+xml is the
// nominal type, but application/xml is universally parsed).
import rss from '@astrojs/rss';
import { feedEntries } from '../lib/corpus.js';

export function GET(context) {
  const site = context.site;
  const entries = feedEntries();
  // lastBuildDate is the newest item date, NOT the build time: a rebuild that
  // changes nothing must produce byte-identical output, and the feed must not
  // claim freshness the corpus cannot prove.
  const newest = entries.map((e) => e.date).filter(Boolean)
    .reduce((a, b) => (a > b ? a : b), null);
  return rss({
    title: 'Circuit Codex — new circuits & studies',
    description:
      'Vintage guitar tube-amp circuits as they are documented: redrawn KiCad schematics, ' +
      'ngspice-checked netlists and operating points verified against the published voltage ' +
      'charts, plus the reference studies behind the corpus.',
    site,
    trailingSlash: true,
    xmlns: { atom: 'http://www.w3.org/2005/Atom' },
    customData: [
      '<language>en-us</language>',
      '<copyright>Circuit data CC-BY-SA-4.0 — attribution required</copyright>',
      `<atom:link href="${new URL('feed.xml', site).href}" rel="self" type="application/rss+xml"/>`,
      ...(newest ? [`<lastBuildDate>${newest.toUTCString()}</lastBuildDate>`] : []),
    ].join(''),
    items: entries.map((e) => ({
      title: e.title,
      link: e.link,
      description: e.description,
      categories: e.categories,
      ...(e.date ? { pubDate: e.date } : {}),
    })),
  });
}
