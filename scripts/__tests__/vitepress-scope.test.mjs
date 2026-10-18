import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { resolvePages } from 'vitepress'

import {
  createVitepressBuildScope,
  publishedLocales,
  supportedLocales,
  translatedLocales,
  vitepressRewrites,
  vitepressSrcExclude
} from '../../.vitepress/site-scope.mjs'

const BASE_EXCLUDE = [
  'README.md',
  'slide/**',
  'CLAUDE.md',
  'aws-architecture-review-request.md',
  '**/SUMMARY.md',
  'docs/**',
  'assets/**',
  'examples/**',
  'public/llms/**'
]

test('VitePress publishes the hand-edited and the translated locales', () => {
  assert.deepEqual(supportedLocales, ['ko', 'en'])
  assert.deepEqual(translatedLocales, ['cn', 'jp', 'es'])
  assert.deepEqual(publishedLocales, ['ko', 'en', 'cn', 'jp', 'es'])
})

test('VitePress excludes GitBook-only sources but no published locale', () => {
  assert.deepEqual(vitepressSrcExclude, BASE_EXCLUDE)
})

test('VitePress rewrites every README to an index page URL', () => {
  assert.deepEqual(
    vitepressRewrites,
    Object.fromEntries(
      publishedLocales.flatMap((locale) => [
        [`${locale}/README.md`, `${locale}/index.md`],
        [`${locale}/:dir(.*)/README.md`, `${locale}/:dir/index.md`]
      ])
    )
  )
})

test('a locale build excludes the other published locales', () => {
  assert.deepEqual(createVitepressBuildScope('jp'), {
    locales: ['jp'],
    srcExclude: [...BASE_EXCLUDE, 'ko/**', 'en/**', 'cn/**', 'es/**'],
    rewrites: {
      'jp/README.md': 'jp/index.md',
      'jp/:dir(.*)/README.md': 'jp/:dir/index.md'
    }
  })
})

test('an unpublished VitePress build locale is rejected', () => {
  assert.throws(
    () => createVitepressBuildScope('fr'),
    /Unsupported VitePress locale: fr/
  )
})

test('VitePress keeps internal review and asset documentation out of the published page graph', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'vitepress-page-scope-'))
  try {
    for (const file of ['index.md', 'ko/topic.md', 'en/topic.md', 'cn/topic.md', 'assets/diagrams/_parked/README.md', 'aws-architecture-review-request.md']) {
      const target = path.join(root, file)
      fs.mkdirSync(path.dirname(target), { recursive: true })
      fs.writeFileSync(target, '# Page')
    }
    const { pages } = await resolvePages(root, createVitepressBuildScope(), console)
    assert.deepEqual(pages.sort(), ['cn/topic.md', 'en/topic.md', 'index.md', 'ko/topic.md'])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
