import assert from 'node:assert/strict'
import test from 'node:test'
import MarkdownIt from 'markdown-it'

import { translationFallbackHref, translationFallbackLinks } from '../../.vitepress/translation-fallback.mjs'
import { extractLastUpdated, localeAlternates } from '../../.vitepress/seo.mjs'

const files = new Set([
  'cn/basics/01-linux-basics.md',
  'cn/basics/02-linux-advanced.md',
  'en/basics/01-linux-basics.md',
  'en/kernel/01-basics.md',
  'en/networking/beginner/README.md',
  'en/networking/README.md',
  'cn/networking/README.md'
])
const fileExists = (file) => files.has(file)

test('a link to a page the translation lacks points at the English page', () => {
  const page = 'cn/basics/01-linux-basics.md'
  assert.equal(translationFallbackHref(page, '../kernel/01-basics.md', { fileExists }), '/kubernetes-docs/en/kernel/01-basics')
  assert.equal(translationFallbackHref(page, '../kernel/01-basics.md#内核', { fileExists }), '/kubernetes-docs/en/kernel/01-basics')
  assert.equal(translationFallbackHref(page, '../networking/beginner/README.md', { fileExists }), '/kubernetes-docs/en/networking/beginner/')
  assert.equal(translationFallbackHref(page, '../networking/beginner/', { fileExists }), '/kubernetes-docs/en/networking/beginner/')
  assert.equal(translationFallbackHref(page, '/cn/kernel/01-basics.md', { fileExists }), '/kubernetes-docs/en/kernel/01-basics')
})

test('links that resolve, leave the locale, or are missing in English too are left alone', () => {
  const page = 'cn/basics/01-linux-basics.md'
  for (const href of [
    './01-linux-basics.md', // exists in cn
    '../networking/README.md', // exists in cn
    '../missing/everywhere.md', // dead in en too: VitePress must still report it
    'https://example.com/x.md',
    '#section',
    'mailto:a@example.com',
    '../../assets/diagram.png',
    '../../en/kernel/01-basics.md' // leaves cn/
  ]) {
    assert.equal(translationFallbackHref(page, href, { fileExists }), undefined, href)
  }
  // ko/en pages are never rewritten.
  assert.equal(translationFallbackHref('ko/basics/01.md', '../kernel/01-basics.md', { fileExists }), undefined)
  assert.equal(translationFallbackHref('en/basics/01.md', '../kernel/missing.md', { fileExists }), undefined)
})

test('the markdown rule rewrites fallback links and opts them out of SPA navigation', () => {
  const md = new MarkdownIt()
  translationFallbackLinks(md, { fileExists })
  // An isolated fixture stays valid as real translated coverage grows.
  const html = md.render('[k](../kernel/01-basics.md#section) [b](./02-linux-advanced.md)', {
    relativePath: 'cn/basics/01-linux-basics.md'
  })
  assert.match(html, /<a href="\/kubernetes-docs\/en\/kernel\/01-basics" target="_self">k<\/a>/)
  assert.match(html, /<a href="\.\/02-linux-advanced\.md">b<\/a>/)
})

test('translated pages get alternates for every locale that has the page', () => {
  const exists = (file) => ['ko', 'en', 'cn', 'jp'].some((l) => file === `${l}/eks/01-intro.md`)
  assert.deepEqual(localeAlternates('cn/eks/01-intro.md', { fileExists: exists }), [
    { hreflang: 'ko', href: 'https://docs.atomai.click/kubernetes-docs/ko/eks/01-intro' },
    { hreflang: 'en', href: 'https://docs.atomai.click/kubernetes-docs/en/eks/01-intro' },
    { hreflang: 'zh-CN', href: 'https://docs.atomai.click/kubernetes-docs/cn/eks/01-intro' },
    { hreflang: 'ja', href: 'https://docs.atomai.click/kubernetes-docs/jp/eks/01-intro' },
    { hreflang: 'x-default', href: 'https://docs.atomai.click/kubernetes-docs/ko/eks/01-intro' }
  ])
})

test('translated date headers parse, including the full-width colon', () => {
  assert.equal(extractLastUpdated('> **最后更新**：September 15, 2026'), '2026-09-15')
  assert.equal(extractLastUpdated('> **対応バージョン**: x **最終更新**: September 15, 2026'), '2026-09-15')
  assert.equal(extractLastUpdated('> **Última actualización**: February 3, 2026'), '2026-02-03')
})
