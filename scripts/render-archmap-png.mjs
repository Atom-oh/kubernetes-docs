#!/usr/bin/env node
// Render the static PNG fallback for delivered archify viewers
// (public/archmaps/<lang>-<stem>.html -> <lang>/.gitbook/assets/<lang>-<stem>.png).
//
// Why not `headless_shell --screenshot`: it captures before the viewer's
// `document.fonts.ready` re-layout runs, so legend count badges are placed
// from pre-font-swap text widths and overlap the last glyph of every label
// (the delivered HTML itself is fine in a browser). This drives the same
// Chromium through playwright-core, waits for fonts + one settled frame,
// then screenshots at the reader's 1600x1080 desktop size.
//
// Usage:
//   node scripts/render-archmap-png.mjs <stem> [<stem> ...]      # ko + en
//   node scripts/render-archmap-png.mjs --all                    # every spec in assets/diagrams/archify
//   node scripts/render-archmap-png.mjs --html <in.html> --out <out.png>
// Env:
//   ARCHMAP_CHROME        Chromium/headless_shell binary (default: playwright's chromium_headless_shell)
//   PLAYWRIGHT_CORE_DIR   a directory whose node_modules holds playwright-core
//   FONTCONFIG_FILE       forwarded to Chromium (deterministic CJK font selection)
import { createRequire } from 'node:module';
import { existsSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const VIEWPORT = { width: 1600, height: 1080 };

function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_CORE_DIR,
    ROOT,
    join(homedir(), '.npm', '_npx'),
  ].filter(Boolean);
  for (const dir of candidates) {
    const roots = dir.endsWith('_npx') && existsSync(dir)
      ? readdirSync(dir).map((d) => join(dir, d))
      : [dir];
    for (const r of roots) {
      const pkg = join(r, 'node_modules', 'playwright-core', 'package.json');
      if (existsSync(pkg)) return createRequire(pkg)('playwright-core');
    }
  }
  throw new Error('playwright-core not found: set PLAYWRIGHT_CORE_DIR to a project that has it installed');
}

function chromePath() {
  if (process.env.ARCHMAP_CHROME) return process.env.ARCHMAP_CHROME;
  const base = join(homedir(), '.cache', 'ms-playwright');
  if (!existsSync(base)) throw new Error('no ~/.cache/ms-playwright; set ARCHMAP_CHROME');
  const shells = readdirSync(base).filter((d) => d.startsWith('chromium_headless_shell-')).sort();
  if (!shells.length) throw new Error('no chromium_headless_shell under ~/.cache/ms-playwright; set ARCHMAP_CHROME');
  return join(base, shells[shells.length - 1], 'chrome-linux', 'headless_shell');
}

function parseArgs(argv) {
  const jobs = [];
  const stems = [];
  let all = false;
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--all') all = true;
    else if (a === '--html') {
      const html = argv[++i];
      if (argv[i + 1] !== '--out') throw new Error('--html needs --out <png>');
      jobs.push({ html: resolve(html), out: resolve(argv[i += 2]) });
    } else stems.push(a);
  }
  if (all) {
    const seen = new Set();
    for (const f of readdirSync(join(ROOT, 'assets', 'diagrams', 'archify'))) {
      const m = /^(ko|en)-(.+)\.[a-z]+\.json$/.exec(f);
      if (m) seen.add(m[2]);
    }
    stems.push(...[...seen].sort());
  }
  for (const stem of stems) {
    for (const lang of ['ko', 'en']) {
      const html = join(ROOT, 'public', 'archmaps', `${lang}-${stem}.html`);
      if (!existsSync(html)) { console.error(`skip ${lang}-${stem}: no ${html}`); continue; }
      jobs.push({ html, out: join(ROOT, lang, '.gitbook', 'assets', `${lang}-${stem}.png`) });
    }
  }
  if (!jobs.length) throw new Error('nothing to render (usage in file header)');
  return jobs;
}

async function settle(page) {
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    // two frames: fonts.ready -> viewer re-layout (legend badges, stage fit) -> paint
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    // The viewer's fonts.ready legend re-layout measures label widths before the
    // stage reaches its final scale (worst on a cold font cache, i.e. the first
    // page of every run), so count badges can land 2-3px inside the last glyph.
    // The viewer re-runs the same layout on window resize, so ask for it once
    // more now that fonts and scale are final.
    window.dispatchEvent(new Event('resize'));
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  });
  await page.waitForTimeout(250);
}

const jobs = parseArgs(process.argv.slice(2));
const { chromium } = loadPlaywright();
const browser = await chromium.launch({
  executablePath: chromePath(),
  args: ['--no-sandbox', '--disable-gpu', '--force-prefers-reduced-motion', '--hide-scrollbars'],
  env: { ...process.env },
});
let failed = 0;
try {
  const context = await browser.newContext({ viewport: VIEWPORT, reducedMotion: 'reduce', deviceScaleFactor: 1 });
  for (const job of jobs) {
    const page = await context.newPage();
    try {
      await page.goto('file://' + job.html, { waitUntil: 'load' });
      await settle(page);
      await page.screenshot({ path: job.out, clip: { x: 0, y: 0, ...VIEWPORT } });
      console.log(`rendered ${job.out}`);
    } catch (err) {
      failed += 1;
      console.error(`FAILED ${job.html}: ${err.message}`);
    } finally {
      await page.close();
    }
  }
} finally {
  await browser.close();
}
if (failed) {
  console.error(`${failed} render(s) failed`);
  process.exit(1);
}
