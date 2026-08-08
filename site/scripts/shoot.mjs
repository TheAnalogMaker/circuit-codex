#!/usr/bin/env node
/**
 * shoot.mjs — visual-review capture rig for circuitcodex.com.
 *
 * "Figures need eyes" (AGENTS.md): fetch-based review cannot tell whether a
 * drawing rendered. This drives a real Chromium over the published site and
 * writes PNGs a reviewer (human or agent) actually looks at.
 *
 * The hard part is the schematic viewer. KiCanvas paints into a WebGL canvas
 * inside a shadow root, so a screenshot taken too early is a blank void panel
 * that *looks* like a page bug. Two independent signals gate every schematic
 * shot:
 *
 *   1. DOM/GL readiness, polled in-page: the <kicanvas-embed> has a shadow
 *      root, that root contains a sized <canvas>, and the element is no longer
 *      showing a loading state.
 *   2. Actual paint, measured from the outside: the element screenshot's PNG
 *      byte length. A blank panel is one flat colour and compresses to almost
 *      nothing; a drawn schematic is thousands of thin strokes and does not.
 *      Signal 2 is authoritative because a WebGL canvas cannot be read back
 *      with getImageData and toDataURL() returns blank without
 *      preserveDrawingBuffer — which we do not control.
 *
 * Paint is declared when the byte length clears PAINT_MIN_BYTES and stops
 * growing, never before FLOOR_MS, and never after CEILING_MS (the shot is
 * still taken at the ceiling, and the manifest records that it timed out so a
 * reviewer knows not to trust it).
 *
 * Playwright is NOT a declared dependency of the site package. The deploy path
 * (Workers Builds) runs `npm ci` on every push, and a review tool has no
 * business adding a browser driver to a production install. Install it locally,
 * once, and it stays out of everyone else's build:
 *
 *   npm i --no-save playwright && npx playwright install chromium
 *
 *   node scripts/shoot.mjs --out <dir>              # everything
 *   node scripts/shoot.mjs --out <dir> --amps 5f1,5e3,jtm45   # rig check
 *   node scripts/shoot.mjs --out <dir> --skip-amps  # pages only
 */
import { mkdir, writeFile, readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '../..');

const BASE = process.env.SHOOT_BASE || 'https://circuitcodex.com';
const VIEWPORT = { width: 1680, height: 1200 };

const FLOOR_MS = 8000;      // never believe a schematic shot taken sooner
const CEILING_MS = 25000;   // give up waiting, shoot anyway, flag it
const POLL_MS = 1000;
const PAINT_MIN_BYTES = 20000;  // a blank 1600x580 panel lands near 3-6 KB
const SETTLE_MS = 1200;         // after a toggle click

// Family pages to sample (the corpus has 14; two is enough for a look).
const FAMILIES = ['champ', 'bassman'];

// ---------------------------------------------------------------- args ----
function args(argv) {
  const out = { out: null, amps: null, skipAmps: false, skipPages: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--out') out.out = argv[++i];
    else if (a === '--amps') out.amps = argv[++i].split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--skip-amps') out.skipAmps = true;
    else if (a === '--skip-pages') out.skipPages = true;
    else if (a === '--base') process.env.SHOOT_BASE = argv[++i];
  }
  if (!out.out) { console.error('shoot.mjs: --out <dir> is required'); process.exit(2); }
  return out;
}

async function ampIds() {
  const entries = await readdir(resolve(REPO, 'amps'), { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory() && !e.name.startsWith('_'))
    .map((e) => e.name)
    .sort();
}

// ------------------------------------------------------------- helpers ----
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** In-page readiness probe for the KiCanvas embed (signal 1). */
function probeKicanvas() {
  const el = document.querySelector('kicanvas-embed');
  if (!el) return { found: false };
  const walk = (root, depth = 0) => {
    if (!root || depth > 6) return null;
    const c = root.querySelector && root.querySelector('canvas');
    if (c) return c;
    const kids = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const k of kids) {
      if (k.shadowRoot) { const hit = walk(k.shadowRoot, depth + 1); if (hit) return hit; }
    }
    return null;
  };
  const canvas = el.shadowRoot ? walk(el.shadowRoot) : null;
  const box = el.getBoundingClientRect();
  return {
    found: true,
    shadow: !!el.shadowRoot,
    canvas: !!canvas,
    cw: canvas ? canvas.width : 0,
    ch: canvas ? canvas.height : 0,
    ew: Math.round(box.width),
    eh: Math.round(box.height),
    loading: !!(el.shadowRoot && el.shadowRoot.textContent || '').match(/loading/i),
  };
}

/**
 * Wait for the schematic to actually paint, then return its element buffer.
 * Signal 2 (PNG byte length) decides; signal 1 is recorded for the manifest.
 */
async function waitForSchematicPaint(page, notes) {
  const el = page.locator('kicanvas-embed').first();
  const t0 = Date.now();
  let last = 0, stable = 0, buf = null, probe = null;

  while (true) {
    const elapsed = Date.now() - t0;
    try { probe = await page.evaluate(probeKicanvas); } catch { probe = null; }

    if (probe && probe.found && probe.canvas) {
      try { buf = await el.screenshot({ timeout: 15000 }); } catch { buf = null; }
      const n = buf ? buf.length : 0;
      if (n >= PAINT_MIN_BYTES) {
        // growing still? give it another tick; two flat reads = done drawing.
        stable = n <= last * 1.02 ? stable + 1 : 0;
        if (elapsed >= FLOOR_MS && stable >= 2) {
          notes.push(`schematic painted at ${(elapsed / 1000).toFixed(1)}s, ` +
            `${n} B, canvas ${probe.cw}x${probe.ch}`);
          return { buf, ok: true };
        }
      }
      last = n;
    }

    if (elapsed >= CEILING_MS) {
      if (!buf) { try { buf = await el.screenshot({ timeout: 15000 }); } catch {} }
      notes.push(`TIMEOUT: schematic never cleared the paint threshold in ` +
        `${(elapsed / 1000).toFixed(1)}s (last ${last} B, probe ` +
        `${JSON.stringify(probe)}) — shot may be blank`);
      return { buf, ok: false };
    }
    await sleep(POLL_MS);
  }
}

async function shootElement(page, selector, file, notes, label) {
  const el = page.locator(selector).first();
  if (!(await el.count())) { notes.push(`absent: ${label || selector}`); return false; }
  await el.scrollIntoViewIfNeeded().catch(() => {});
  await sleep(250);
  const buf = await el.screenshot({ timeout: 20000 });
  await writeFile(file, buf);
  return true;
}

async function shootFullPage(page, file) {
  const buf = await page.screenshot({ fullPage: true, timeout: 60000 });
  await writeFile(file, buf);
}

/** Fonts + lazy images + any inline SVG figure settled. */
async function settlePage(page) {
  await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.evaluate(() => {
    for (const img of document.images) { img.loading = 'eager'; }
    window.scrollTo(0, document.body.scrollHeight);
  }).catch(() => {});
  await sleep(600);
  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await sleep(400);
}

// ---------------------------------------------------------------- amps ----
async function shootAmp(ctx, out, id, manifest) {
  const url = `${BASE}/amps/${id}/`;
  const notes = [];
  const files = [];
  // Fresh context per amp: the layout style toggle persists in localStorage
  // (key cc-layout-style), so a leaked "current" choice would silently make
  // every later -sheet.png a house drawing.
  const page = await ctx.newPage();
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (!resp || !resp.ok()) notes.push(`HTTP ${resp ? resp.status() : 'none'}`);
    await settlePage(page);

    // (1) schematic — the shot that needs the paint gate
    const { buf, ok } = await waitForSchematicPaint(page, notes);
    if (buf) {
      await writeFile(`${out}/${id}-schematic.png`, buf);
      files.push(`${id}-schematic.png`);
      if (!ok) notes.push('schematic.png captured past the ceiling — verify by eye');
    } else {
      notes.push('no schematic embed on this page');
    }

    // (2) layout, sheet style (the published default)
    const layout = page.locator('.viewer.layout').first();
    if (await layout.count()) {
      const sheetBtn = page.locator('.viewer.layout button[data-style="sheet"]').first();
      if (await sheetBtn.count()) {
        await sheetBtn.click({ timeout: 10000 }).catch(() => notes.push('sheet toggle click failed'));
        await sleep(SETTLE_MS);
      } else {
        notes.push('no style toggle (amp has no sheet-style drawing)');
      }
      if (await shootElement(page, '.viewer.layout', `${out}/${id}-sheet.png`, notes, 'layout'))
        files.push(`${id}-sheet.png`);

      // (3) layout, current/house style
      const curBtn = page.locator('.viewer.layout button[data-style="current"]').first();
      if (await curBtn.count()) {
        await curBtn.click({ timeout: 10000 });
        await sleep(SETTLE_MS);
        const pressed = await curBtn.getAttribute('aria-pressed');
        if (pressed !== 'true') notes.push('Current toggle did not latch (aria-pressed != true)');
        if (await shootElement(page, '.viewer.layout', `${out}/${id}-house.png`, notes, 'layout/current'))
          files.push(`${id}-house.png`);
      } else {
        notes.push('no Current toggle — single-style layout, house shot skipped');
      }
    } else {
      notes.push('no layout viewer on this page');
    }

    // (4) full page — back to the published default first
    const sheetBtn2 = page.locator('.viewer.layout button[data-style="sheet"]').first();
    if (await sheetBtn2.count()) { await sheetBtn2.click().catch(() => {}); await sleep(SETTLE_MS); }
    await shootFullPage(page, `${out}/${id}-page.png`);
    files.push(`${id}-page.png`);
  } catch (e) {
    notes.push(`ERROR: ${e.message}`);
  } finally {
    await page.close().catch(() => {});
  }
  manifest.push({ page: `/amps/${id}/`, url, files, notes });
  console.log(`  ${id}: ${files.length} files${notes.length ? ' — ' + notes.join(' | ') : ''}`);
}

// --------------------------------------------------------------- pages ----
async function shootSimple(ctx, out, path, slug, manifest, extra) {
  const url = `${BASE}${path}`;
  const notes = [];
  const files = [];
  const page = await ctx.newPage();
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (!resp || !resp.ok()) notes.push(`HTTP ${resp ? resp.status() : 'none'}`);
    await settlePage(page);
    if (extra) await extra(page, out, slug, files, notes);
    await shootFullPage(page, `${out}/${slug}-page.png`);
    files.push(`${slug}-page.png`);
  } catch (e) {
    notes.push(`ERROR: ${e.message}`);
  } finally {
    await page.close().catch(() => {});
  }
  manifest.push({ page: path, url, files, notes });
  console.log(`  ${slug}: ${files.length} files${notes.length ? ' — ' + notes.join(' | ') : ''}`);
}

/** Wait for an inline-SVG figure to exist and have real geometry. */
async function waitForSvg(page, selector, notes, label) {
  try {
    await page.waitForFunction((sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const b = el.getBoundingClientRect();
      return b.width > 40 && b.height > 40 && el.querySelectorAll('path,line,rect,text').length > 5;
    }, selector, { timeout: 20000 });
    return true;
  } catch {
    notes.push(`SVG never drew: ${label || selector}`);
    return false;
  }
}

async function loadChromium() {
  try {
    return (await import('playwright')).chromium;
  } catch {
    console.error('shoot.mjs needs Playwright, which is deliberately not a site ' +
      'dependency (it must not land in the deploy\'s `npm ci`). Install it locally:\n' +
      '  npm i --no-save playwright && npx playwright install chromium');
    process.exit(2);
  }
}

async function main() {
  const opt = args(process.argv.slice(2));
  const out = resolve(opt.out);
  await mkdir(out, { recursive: true });
  const manifest = [];

  const chromium = await loadChromium();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    userAgent: 'circuit-codex-review-rig (visual QA; contact via github.com/TheAnalogMaker/circuit-codex)',
  });

  try {
    if (!opt.skipPages) {
      console.log('pages:');
      await shootSimple(ctx, out, '/', 'home', manifest);

      await shootSimple(ctx, out, '/lineage/', 'lineage', manifest, async (page, o, s, files, notes) => {
        await waitForSvg(page, '.lineage svg, figure svg, svg', notes, 'lineage graph');
        if (await shootElement(page, 'figure:has(svg), .lineage', `${o}/${s}-figure.png`, notes, 'lineage figure'))
          files.push(`${s}-figure.png`);
      });

      await shootSimple(ctx, out, '/history/', 'history-index', manifest);
      for (const f of FAMILIES) {
        await shootSimple(ctx, out, `/history/${f}/`, `history-${f}`, manifest);
      }

      await shootSimple(ctx, out, '/reference/guides/tone-stack-lab/', 'tone-stack-lab', manifest,
        async (page, o, s, files, notes) => {
          const preset = page.locator('a.preset[data-preset]').first();
          if (await preset.count()) {
            const which = await preset.getAttribute('data-preset');
            await preset.click({ timeout: 10000 });
            await sleep(1500);
            notes.push(`selected preset "${which}"`);
            await waitForSvg(page, '#lab svg, .plot svg, svg', notes, 'tone-stack plot');
            if (await shootElement(page, '#lab', `${o}/${s}-preset.png`, notes, 'lab panel'))
              files.push(`${s}-preset.png`);
          } else { notes.push('no preset links found'); }
        });

      await shootSimple(ctx, out, '/reference/guides/load-lines/', 'load-lines', manifest,
        async (page, o, s, files, notes) => {
          const chip = page.locator('#ll-presets a.pchip[data-preset]').first();
          if (await chip.count()) {
            const which = await chip.getAttribute('data-preset');
            await chip.click({ timeout: 10000 });
            await sleep(1500);
            notes.push(`selected preset "${which}"`);
            await waitForSvg(page, 'svg', notes, 'load-line plot');
            if (await shootElement(page, 'figure:has(svg), .plot, main', `${o}/${s}-preset.png`, notes, 'plot'))
              files.push(`${s}-preset.png`);
          } else { notes.push('no preset chips found'); }
        });

      await shootSimple(ctx, out, '/reference/studies/tone-stack-ladder/', 'study-tone-stack-ladder', manifest,
        async (page, o, s, files, notes) => {
          const figs = page.locator('.prose figure');
          const n = await figs.count();
          notes.push(`${n} figures`);
          for (let i = 0; i < n; i++) {
            const f = figs.nth(i);
            await f.scrollIntoViewIfNeeded().catch(() => {});
            await sleep(300);
            const name = `${s}-fig${String(i + 1).padStart(2, '0')}.png`;
            try { await writeFile(`${o}/${name}`, await f.screenshot({ timeout: 20000 })); files.push(name); }
            catch (e) { notes.push(`figure ${i + 1} shot failed: ${e.message}`); }
          }
        });
    }

    if (!opt.skipAmps) {
      const ids = opt.amps || (await ampIds());
      console.log(`amps (${ids.length}):`);
      for (const id of ids) {
        await shootAmp(ctx, out, id, manifest);
        await sleep(500);   // be gentle with the origin
      }
    }
  } finally {
    await ctx.close().catch(() => {});
    await browser.close().catch(() => {});
  }

  const total = manifest.reduce((n, m) => n + m.files.length, 0);
  await writeFile(`${out}/manifest.json`, JSON.stringify({
    base: BASE,
    viewport: VIEWPORT,
    captured: new Date().toISOString(),
    paint_gate: {
      floor_ms: FLOOR_MS, ceiling_ms: CEILING_MS, poll_ms: POLL_MS,
      paint_min_bytes: PAINT_MIN_BYTES,
      method: 'in-page shadow-DOM canvas probe + element-screenshot PNG byte length ' +
        '(a WebGL canvas cannot be read back with getImageData, and toDataURL is ' +
        'blank without preserveDrawingBuffer, so byte length is the paint signal)',
    },
    shots: total,
    pages: manifest,
  }, null, 2) + '\n');
  console.log(`\n${total} shots -> ${out}/manifest.json`);
}

main().catch((e) => { console.error(e); process.exit(1); });
