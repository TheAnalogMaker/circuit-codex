// node --test worker/ — the Worker's redirects against a stand-in asset store.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import worker from "./index.js";

const published = new Set(["/", "/amps/5f10/", "/feed.xml", "/sitemap-index.xml", "/_astro/Page_AbC12.js"]);
let lookups = 0;
const env = {
  ASSETS: {
    async fetch(req) {
      lookups++;
      const { pathname } = new URL(req.url);
      if (published.has(pathname) && req.headers.get("if-none-match") === '"v1"') return new Response(null, { status: 304 });
      if (published.has(pathname)) return new Response("ok", { status: 200 });
      if (published.has(pathname + "/")) return Response.redirect(new URL(pathname + "/", req.url).toString(), 307);
      // What not_found_handling: "404-page" serves: dist/404.html, status 404.
      return new Response("<h1>Nothing at this address.</h1>", { status: 404 });
    },
  },
};
const get = (path, host = "circuitcodex.com", headers = {}) =>
  worker.fetch(new Request(`https://${host}${path}`, { headers }), env);

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

// The stand-in above serves a 404 page body only because production is
// configured to. With not_found_handling left at its default ("none"), the
// asset store answers a miss with an empty 404 and the site's 404 page is
// never seen — which is how production ran until this was added.
test("the asset config serves the built 404 page on a miss", () => {
  const url = new URL("../wrangler.jsonc", import.meta.url);
  const config = JSON.parse(readFileSync(url, "utf8").replace(/^\s*\/\/.*$/gm, ""));
  assert.equal(config.assets.not_found_handling, "404-page");
  assert.ok(existsSync(new URL("../site/src/pages/404.astro", import.meta.url)));
});

test("a miss passes the 404 page body through, capitalised or not", async () => {
  for (const path of ["/nope/", "/NOPE/", "/amps/NOPE/"]) {
    const r = await get(path);
    assert.equal(r.status, 404, path);
    assert.match(await r.text(), /Nothing at this address/, path);
  }
});

test("guessed names typed in capitals still reach their alias", async () => {
  for (const [from, to] of [["/AMPS/", "/#circuits"], ["/Feed", "/feed.xml"], ["/RSS.xml", "/feed.xml"], ["/Sitemap.xml", "/sitemap-index.xml"]]) {
    const r = await get(from);
    assert.equal(r.status, 301, from);
    assert.equal(r.headers.get("location"), `https://circuitcodex.com${to}`, from);
  }
});

test("a capitalised path that redirects again lands in one hop, query kept", async () => {
  const r = await get("/amps/5F10?from=chart");
  assert.equal(r.status, 301);
  assert.equal(r.headers.get("location"), "https://circuitcodex.com/amps/5f10/?from=chart");
});

test("a revalidation (304) passes straight through without a second lookup", async () => {
  lookups = 0;
  const r = await get("/_astro/Page_AbC12.js", undefined, { "If-None-Match": '"v1"' });
  assert.equal(r.status, 304);
  assert.equal(lookups, 1);
});

test("only a miss is retried in lowercase", async () => {
  const failing = { ASSETS: { async fetch() { lookups++; return new Response("down", { status: 503 }); } } };
  lookups = 0;
  const r = await worker.fetch(new Request("https://circuitcodex.com/amps/5F10/"), failing);
  assert.equal(r.status, 503);
  assert.equal(lookups, 1);
});
