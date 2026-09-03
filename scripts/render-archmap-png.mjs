#!/usr/bin/env node
// Render deterministic PNG stills of delivered archify archmaps.
//
// Replaces the retired `headless_shell --screenshot --virtual-time-budget` recipe,
// which captured before the viewer's `document.fonts.ready` re-layout ran and
// left legend count badges positioned from pre-font-swap text widths.
//
// Usage:
//   node scripts/render-archmap-png.mjs <stem> [<stem> ...]   # ko+en pair per stem suffix
//   node scripts/render-archmap-png.mjs --all                 # every public/archmaps/*.html
//   node scripts/render-archmap-png.mjs --html <in.html> --out <out.png>
//
// Environment:
//   PLAYWRIGHT_CORE_DIR  dir whose node_modules has playwright-core
//                        (default: /home/atomoh/awsops/web)
//   ARCHMAP_CHROME       Chromium binary (default: newest
//                        ~/.cache/ms-playwright/chromium_headless_shell-*)
//   FONTCONFIG_FILE      optional fontconfig override for deterministic CJK

import { createRequire } from 'node:module'
import { readdirSync, existsSync } from 'node:fs'
import path from 'node:path'
import os from 'node:os'

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')
const pwDir = process.env.PLAYWRIGHT_CORE_DIR || '/home/atomoh/awsops/web'
const require_ = createRequire(path.join(pwDir, 'noop.js'))
const { chromium } = require_('playwright-core')

function chromePath() {
  if (process.env.ARCHMAP_CHROME) return process.env.ARCHMAP_CHROME
  const base = path.join(os.homedir(), '.cache/ms-playwright')
  const shells = readdirSync(base).filter((d) => d.startsWith('chromium_headless_shell-')).sort()
  if (shells.length === 0) throw new Error(`no chromium_headless_shell under ${base}; set ARCHMAP_CHROME`)
  return path.join(base, shells[shells.length - 1], 'chrome-linux', 'headless_shell')
}

function jobs(argv) {
  const list = []
  if (argv[0] === '--html') {
    const out = argv[argv.indexOf('--out') + 1]
    if (!out) throw new Error('--html requires --out <png>')
    return [{ html: path.resolve(argv[1]), png: path.resolve(out) }]
  }
  const stems = argv[0] === '--all'
    ? readdirSync(path.join(repoRoot, 'public/archmaps'))
        .filter((f) => f.endsWith('.html')).map((f) => f.replace(/\.html$/, ''))
    : argv.flatMap((s) => (/^(ko|en)-/.test(s) ? [s] : [`ko-${s}`, `en-${s}`]))
  for (const stem of stems) {
    const lang = stem.split('-')[0]
    list.push({
      html: path.join(repoRoot, 'public/archmaps', `${stem}.html`),
      png: path.join(repoRoot, lang, '.gitbook/assets', `${stem}.png`)
    })
  }
  return list
}

const argv = process.argv.slice(2)
if (argv.length === 0) {
  console.error('usage: render-archmap-png.mjs <stem>... | --all | --html <in> --out <out>')
  process.exit(2)
}

const browser = await chromium.launch({
  executablePath: chromePath(),
  args: ['--no-sandbox', '--disable-gpu', '--force-prefers-reduced-motion', '--hide-scrollbars']
})
let failures = 0
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1080 }, deviceScaleFactor: 1 })
  for (const job of jobs(argv)) {
    if (!existsSync(job.html)) {
      console.error(`MISSING ${job.html}`)
      failures += 1
      continue
    }
    await page.goto(`file://${job.html}`, { waitUntil: 'load' })
    // The viewer re-lays-out legend badges after webfonts finish loading; a
    // screenshot before that captures pre-font-swap text widths.
    await page.evaluate(() => document.fonts.ready)
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
    await page.waitForTimeout(400)
    const tall = await page.evaluate(() =>
      Math.max(document.documentElement.scrollHeight, document.body.scrollHeight))
    await page.screenshot({ path: job.png, fullPage: tall > 1080 })
    console.log(`rendered ${path.relative(repoRoot, job.png)}${tall > 1080 ? ` (fullPage ${tall}px)` : ''}`)
  }
} finally {
  await browser.close()
}
process.exit(failures === 0 ? 0 : 1)
