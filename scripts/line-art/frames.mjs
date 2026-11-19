// usage: node scripts/line-art/frames.mjs <svg> <outPrefix> <t1,t2,...> [dark] [reduced]
import { createRequire } from 'node:module';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
const req = createRequire('/home/atomoh/kubernetes-docs/node_modules/playwright-core/package.json');
let pw; try { pw = req('playwright-core'); } catch { pw = null; }
if (!pw) { const npx = join(homedir(), '.npm/_npx'); for (const d of readdirSync(npx)) { try { pw = createRequire(join(npx, d, 'node_modules/playwright-core/package.json'))('playwright-core'); break; } catch {} } }
const base = join(homedir(), '.cache/ms-playwright');
const shell = readdirSync(base).filter(d => d.startsWith('chromium_headless_shell')).sort().pop();
const exe = join(base, shell, 'chrome-linux', 'headless_shell');
const [svgPath, out, times, ...flags] = process.argv.slice(2);
const svg = readFileSync(svgPath, 'utf8');
const browser = await pw.chromium.launch({ executablePath: exe, args: ['--font-render-hinting=none'] });
const ctx = await browser.newContext({ viewport: { width: 960, height: 500 }, deviceScaleFactor: 1,
  colorScheme: flags.includes('dark') ? 'dark' : 'light', reducedMotion: flags.includes('reduced') ? 'reduce' : 'no-preference' });
const page = await ctx.newPage();
await page.setContent(`<html><body style="margin:0">${svg}</body></html>`);
for (const t of times.split(',').map(Number)) {
  await page.evaluate((t) => { const s = document.querySelector('svg'); s.pauseAnimations(); s.setCurrentTime(t); }, t);
  await page.waitForTimeout(50);
  await page.screenshot({ path: `${out}-t${t}.png` });
}
await browser.close();
console.log('frames ok');
