import rss from '@astrojs/rss';
import { loadCorrections } from '../lib/revisions.js';
export function GET({ site }) {
  return rss({
    title: 'Circuit Codex — corrections',
    description: 'Corrections to circuit facts, drawings and verification coverage.',
    site,
    // Each link is a fragment on /corrections/. @astrojs/rss appends a slash to
    // links by default, which lands after the fragment (#id/) and matches no
    // element, so the reader opens the top of the page instead of the entry.
    trailingSlash: false,
    items: loadCorrections().map((c) => ({ title: c.title, description: c.description,
      link: `/corrections/#${c.id}`, pubDate: new Date(`${c.date}T00:00:00Z`), categories: c.amps })),
  });
}
