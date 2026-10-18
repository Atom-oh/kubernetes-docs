import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import test from 'node:test'
import { createMarkdownRenderer } from 'vitepress'
import { syncTranslatedAnchors } from '../sync-translated-anchors.mjs'

test('anchor CLI help and invalid options leave every locale file untouched', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translated-anchors-cli-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  for (const locale of ['en', 'cn', 'jp', 'es']) fs.mkdirSync(path.join(root, locale))
  fs.writeFileSync(path.join(root, 'en/page.md'), '# Page\n\n[Go](#page)\n')
  const translated = '# 翻訳\n\n[Go](#page)\n'
  for (const locale of ['cn', 'jp', 'es']) fs.writeFileSync(path.join(root, locale, 'page.md'), translated)
  const script = new URL('../sync-translated-anchors.mjs', import.meta.url).pathname
  for (const args of [
    ['--help'], ['-h'], ['--locale', 'cn', '--typo'],
    ['--locale'], ['--locale', 'unknown'], ['--check', '--check'], ['--help', '--locale', 'cn']
  ]) {
    const result = spawnSync(process.execPath, [script, ...args], { cwd: root, encoding: 'utf8' })
    assert.ifError(result.error)
    assert.equal(result.status, args.length === 1 && ['--help', '-h'].includes(args[0]) ? 0 : 1)
    if (result.status === 0) assert.match(result.stdout, /^Usage:/)
    for (const locale of ['cn', 'jp', 'es']) {
      assert.equal(fs.readFileSync(path.join(root, locale, 'page.md'), 'utf8'), translated, `${locale}: ${args}`)
    }
  }
})

test('translated headings resolve source self/cross-page fragments including duplicate and explicit IDs', async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translated-anchors-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  for (const locale of ['en', 'cn', 'jp', 'es']) fs.mkdirSync(path.join(root, locale, 'topic'), { recursive: true })
  const source = '# Introduction\n\n[Next](topic/page.md#repeat-1) [Home](#introduction)\n'
  const page = '# Topic\n\n## Repeat\n\nFirst.\n\n## Repeat\n\nSecond.\n\n## Fixed {#stable-id}\n'
  fs.writeFileSync(path.join(root, 'en/README.md'), source)
  fs.writeFileSync(path.join(root, 'en/topic/page.md'), page)
  for (const locale of ['cn', 'jp', 'es']) {
    fs.writeFileSync(path.join(root, locale, 'README.md'), source.replace('Introduction', '译文'))
    fs.writeFileSync(path.join(root, locale, 'topic/page.md'), page.replaceAll('Repeat', '标题').replace('Fixed', '固定'))
  }
  const renderer = await createMarkdownRenderer(root, { html: true }, '/kubernetes-docs/')
  const result = await syncTranslatedAnchors(root, { renderer })
  assert.deepEqual(result.failures, [])
  assert.deepEqual(result.unresolvedSource, [])
  assert.equal(result.changed.length, 6)
  for (const locale of ['cn', 'jp', 'es']) {
    assert.match(fs.readFileSync(path.join(root, locale, 'README.md'), 'utf8'), /# 译文 \{#introduction\}/)
    const text = fs.readFileSync(path.join(root, locale, 'topic/page.md'), 'utf8')
    assert.match(text, /## 标题 \{#repeat-1\}/)
    assert.match(text, /## 固定 \{#stable-id\}/)
  }
  assert.deepEqual((await syncTranslatedAnchors(root, { renderer })).changed, [])
})

test('anchor repair preserves code, links and unreferenced headings and refuses mismatched structure or explicit IDs', async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translated-anchors-protection-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  fs.mkdirSync(path.join(root, 'en'))
  fs.mkdirSync(path.join(root, 'jp'))
  const source = '# Page\n\n[Go](#network)\n\n## Network\n\n```md\n## Example\n[Go](#unrelated)\n```\n\n## Unreferenced\n'
  const translated = source.replace('# Page', '# ページ').replace('## Network', '## ネットワーク').replace('## Unreferenced', '## その他')
  fs.writeFileSync(path.join(root, 'en/page.md'), source)
  const target = path.join(root, 'jp/page.md')
  fs.writeFileSync(target, translated)
  const renderer = await createMarkdownRenderer(root, { html: true }, '/kubernetes-docs/')
  const check = await syncTranslatedAnchors(root, { renderer, locales: ['jp'], apply: false })
  assert.equal(check.changed.length, 1)
  assert.equal(fs.readFileSync(target, 'utf8'), translated)
  const result = await syncTranslatedAnchors(root, { renderer, locales: ['jp'] })
  assert.deepEqual(result.failures, [])
  assert.equal(fs.readFileSync(target, 'utf8'), translated.replace('## ネットワーク', '## ネットワーク {#network}'))
  fs.writeFileSync(target, translated.replace('## ネットワーク', '## ネットワーク {#manual-id}'))
  assert.match((await syncTranslatedAnchors(root, { renderer, locales: ['jp'] })).failures[0].reason, /Existing explicit ID/)
  fs.writeFileSync(target, '# Only a summary\n')
  assert.match((await syncTranslatedAnchors(root, { renderer, locales: ['jp'] })).failures[0].reason, /Heading structure differs/)
})

test('HTML anchors and fragments in fenced code do not cause changes, and broken source fragments remain visible', async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translated-html-anchors-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  fs.mkdirSync(path.join(root, 'en'))
  fs.mkdirSync(path.join(root, 'es'))
  const source = '# Page\n\n<span id="custom"></span>\n\n[Custom](#custom) [Broken](#missing)\n\n```md\n[Not a link](#page)\n```\n'
  fs.writeFileSync(path.join(root, 'en/page.md'), source)
  fs.writeFileSync(path.join(root, 'es/page.md'), source.replace('# Page', '# Página'))
  const renderer = await createMarkdownRenderer(root, { html: true }, '/kubernetes-docs/')
  const result = await syncTranslatedAnchors(root, { renderer, locales: ['es'] })
  assert.deepEqual(result.changed, [])
  assert.deepEqual(result.failures, [])
  assert.equal(result.unresolvedSource.length, 1)
  assert.equal(result.unresolvedSource[0].href, '#missing')
  fs.writeFileSync(path.join(root, 'es/page.md'), source.replace('# Page', '# Página').replace('id="custom"', 'id="changed"'))
  assert.match((await syncTranslatedAnchors(root, { renderer, locales: ['es'] })).failures[0].reason,
    /Unresolved canonical IDs: custom/)
})

test('unreferenced pages preserve heading hierarchy without adding unnecessary IDs', async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'translated-unreferenced-headings-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  for (const locale of ['en', 'cn']) fs.mkdirSync(path.join(root, locale))
  fs.writeFileSync(path.join(root, 'en/page.md'), '# Page\n\n## Section\n\n```md\n### Example\n```\n')
  const target = path.join(root, 'cn/page.md')
  const incorrect = '# 页面\n\n### 章节\n\n```md\n### Example\n```\n'
  fs.writeFileSync(target, incorrect)
  const renderer = await createMarkdownRenderer(root, { html: true }, '/kubernetes-docs/')
  const failed = await syncTranslatedAnchors(root, { renderer, locales: ['cn'] })
  assert.deepEqual(failed.changed, [])
  assert.equal(failed.failures.length, 1)
  assert.match(failed.failures[0].reason, /Heading structure differs/)
  assert.equal(fs.readFileSync(target, 'utf8'), incorrect)
  const correct = incorrect.replace('### 章节', '## 章节')
  fs.writeFileSync(target, correct)
  const passed = await syncTranslatedAnchors(root, { renderer, locales: ['cn'] })
  assert.deepEqual(passed.failures, [])
  assert.deepEqual(passed.changed, [])
  assert.equal(fs.readFileSync(target, 'utf8'), correct)
})
