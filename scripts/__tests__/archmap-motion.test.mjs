import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import vm from 'node:vm'
import test from 'node:test'
import { normalizeArchmapMotion } from '../lib/archmap-motion.mjs'

const marker = '<script id="archify-i18n-data" type="application/json">{}</script>'
const render = `if (paused && lastEffectivePaused !== true && Archify.guidedViews && Archify.guidedViews.isPlaying()) {
  Archify.guidedViews.pause();
}`

test('pausing viewers tolerates absent and partial guided-view APIs', () => {
  const normalized = normalizeArchmapMotion(`${marker}<script>${render}</script>`)
  const script = normalized.match(/<script>([\s\S]*)<\/script>/)[1]
  for (const guidedViews of [
    undefined,
    { count: 0, active: () => null },
    { isPlaying: () => true },
    { isPlaying: false, pause: true }
  ]) {
    assert.doesNotThrow(() => vm.runInNewContext(script, {
      paused: true, lastEffectivePaused: false, Archify: { guidedViews }
    }))
  }
})

test('an active guided tour pauses only on the transition to still', () => {
  const script = normalizeArchmapMotion(`${marker}<script>${render}</script>`)
    .match(/<script>([\s\S]*)<\/script>/)[1]
  let calls = 0
  const guidedViews = { isPlaying: () => true, pause: () => { calls += 1 } }
  for (const [paused, lastEffectivePaused] of [[false, false], [true, false], [true, true]]) {
    vm.runInNewContext(script, { paused, lastEffectivePaused, Archify: { guidedViews } })
  }
  assert.equal(calls, 1)
})

test('normalization is idempotent and leaves ordinary HTML unchanged', () => {
  const viewer = `${marker}<script>${render}</script>`
  const normalized = normalizeArchmapMotion(viewer)
  assert.equal(normalizeArchmapMotion(normalized), normalized)
  assert.equal(normalizeArchmapMotion(`<script>${render}</script>`), `<script>${render}</script>`)
})

test('TechDocs source viewers include the safe motion transition', async () => {
  for (const locale of ['ko', 'en']) {
    const html = await readFile(new URL(
      `../../public/archmaps/${locale}-platform-engineering-06-backstage-idp-2.html`,
      import.meta.url
    ), 'utf8')
    assert.equal(normalizeArchmapMotion(html), html)
    assert.ok(html.includes("typeof Archify.guidedViews.isPlaying === 'function'"))
    assert.ok(html.includes("typeof Archify.guidedViews.pause === 'function'"))
  }
})
