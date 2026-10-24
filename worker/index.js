// Every request passes through here (run_worker_first) before the static assets.
//
// Canonical-host enforcement: www.circuitcodex.com serves byte-identical
// content to the apex unless redirected, which splits search indexing across
// two hostnames, so the www host 301s to the apex.
//
// Guessed URLs: browsers, crawlers and readers ask for addresses the site does
// not publish under that name, so the common guesses redirect to the real page.
// Circuit codes are printed in capitals (5F10, AB763), so a path that misses
// with capitals in it is retried in lowercase before giving up.
export const ALIASES = {
  "/sitemap.xml": "/sitemap-index.xml",
  "/rss.xml": "/feed.xml",
  "/feed": "/feed.xml",
  "/amps": "/#circuits",
  "/amps/": "/#circuits",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === "www.circuitcodex.com") {
      url.hostname = "circuitcodex.com";
      return Response.redirect(url.toString(), 301);
    }
    const alias = ALIASES[url.pathname];
    if (alias) return Response.redirect(new URL(alias, url).toString(), 301);

    const response = await env.ASSETS.fetch(request);
    if (response.status < 300 || !/[A-Z]/.test(url.pathname)) return response;

    const lower = new URL(url);
    lower.pathname = url.pathname.toLowerCase();
    const retry = await env.ASSETS.fetch(new Request(lower.toString(), request));
    if (retry.status >= 400) return response;
    return Response.redirect(lower.toString(), 301);
  },
};
