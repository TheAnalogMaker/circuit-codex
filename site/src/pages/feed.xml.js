// /feed.xml — the archive's own feed: one entry per documented circuit and per
// reference study, newest first. Dates come from the repository (a circuit's
// verification date, otherwise the day the files entered git); an entry whose date
// cannot be established ships without one rather than with the build date, so the
// feed never claims a publication day it cannot prove. See feedEntries().
import rss from '@astrojs/rss';
import { feedEntries } from '../lib/corpus.js';

export function GET(context) {
  const site = context.site;
  return rss({
    title: 'Circuit Codex — new circuits & studies',
    description:
      'Vintage guitar tube-amp circuits as they are documented: redrawn KiCad schematics, ' +
      'ngspice-checked netlists and operating points verified against the published voltage ' +
      'charts, plus the reference studies behind the corpus.',
    site,
    trailingSlash: true,
    customData: [
      '<language>en-us</language>',
      '<copyright>Circuit data CC-BY-SA-4.0 — attribution required</copyright>',
    ].join(''),
    items: feedEntries().map((e) => ({
      title: e.title,
      link: e.link,
      description: e.description,
      categories: e.categories,
      ...(e.date ? { pubDate: e.date } : {}),
    })),
  });
}
