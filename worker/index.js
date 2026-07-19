// Canonical-host enforcement: www.circuitcodex.com serves byte-identical
// content to the apex unless redirected, which splits search indexing across
// two hostnames. Every request passes through here (run_worker_first) so the
// www host can 301 to the apex before the static assets are served.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === "www.circuitcodex.com") {
      url.hostname = "circuitcodex.com";
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
