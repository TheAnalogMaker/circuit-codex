// node --test worker/ — the Worker's redirects against a stand-in asset store.
import { test } from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

const published = new Set(["/", "/amps/5f10/", "/feed.xml", "/sitemap-index.xml", "/_astro/Page_AbC12.js"]);
const env = {
  ASSETS: {
    async fetch(req) {
      const { pathname } = new URL(req.url);
      if (published.has(pathname)) return new Response("ok", { status: 200 });
      if (published.has(pathname + "/")) return Response.redirect(new URL(pathname + "/", req.url).toString(), 307);
      return new Response("missing", { status: 404 });
    },
  },
};
const get = (path, host = "circuitcodex.com") => worker.fetch(new Request(`https://${host}${path}`), env);

test("www redirects to the apex", async () => {
  const r = await get("/amps/5f10/?x=1", "www.circuitcodex.com");
  assert.equal(r.status, 301);
  assert.equal(r.headers.get("location"), "https://circuitcodex.com/amps/5f10/?x=1");
});

test("guessed feed and sitemap names redirect", async () => {
  for (const [from, to] of [["/sitemap.xml", "/sitemap-index.xml"], ["/rss.xml", "/feed.xml"], ["/amps/", "/#circuits"]]) {
    const r = await get(from);
    assert.equal(r.status, 301, from);
    assert.equal(r.headers.get("location"), `https://circuitcodex.com${to}`, from);
  }
});

test("a capitalised circuit code redirects to the lowercase page", async () => {
  for (const path of ["/amps/5F10/", "/AMPS/5F10/", "/amps/5F10"]) {
    const r = await get(path);
    assert.equal(r.status, 301, path);
    assert.match(r.headers.get("location"), /^https:\/\/circuitcodex\.com\/amps\/5f10\/?$/, path);
  }
});

test("published files and real misses pass through untouched", async () => {
  assert.equal((await get("/_astro/Page_AbC12.js")).status, 200);
  assert.equal((await get("/amps/5f10/")).status, 200);
  assert.equal((await get("/amps/NOPE/")).status, 404);
  assert.equal((await get("/nope/")).status, 404);
});
