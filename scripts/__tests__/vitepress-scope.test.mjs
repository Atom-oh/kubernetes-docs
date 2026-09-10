import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { resolvePages } from 'vitepress'

import {
  createVitepressBuildScope,
  supportedLocales,
  vitepressRewrites,
  vitepressSrcExclude
} from '../../.vitepress/site-scope.mjs'

test('VitePress publishes only Korean and English content', () => {
  assert.deepEqual(supportedLocales, ['ko', 'en'])
})

test('VitePress excludes GitBook-only sources and translated mirrors', () => {
  assert.deepEqual(vitepressSrcExclude, [
    'README.md',
    'slide/**',
    'CLAUDE.md',
    '**/SUMMARY.md',
    'docs/**',
    'assets/**',
    'examples/**',
    'public/llms/**',
    'cn/**',
    'jp/**',
    'es/**'
  ])
})

test('VitePress rewrites every README to an index page URL', () => {
  assert.deepEqual(vitepressRewrites, {
    'ko/README.md': 'ko/index.md',
    'ko/:dir(.*)/README.md': 'ko/:dir/index.md',
    'en/README.md': 'en/index.md',
    'en/:dir(.*)/README.md': 'en/:dir/index.md'
  })
})

test('a locale build excludes the other published locale', () => {
  assert.deepEqual(createVitepressBuildScope('ko'), {
    locales: ['ko'],
    srcExclude: [
      'README.md',
      'slide/**',
      'CLAUDE.md',
      '**/SUMMARY.md',
      'docs/**',
      'assets/**',
      'examples/**',
      'public/llms/**',
      'cn/**',
      'jp/**',
      'es/**',
      'en/**'
    ],
    rewrites: {
      'ko/README.md': 'ko/index.md',
      'ko/:dir(.*)/README.md': 'ko/:dir/index.md'
    }
  })
})

test('an unsupported VitePress build locale is rejected', () => {
  assert.throws(
    () => createVitepressBuildScope('cn'),
    /Unsupported VitePress locale: cn/
  )
})

test('VitePress keeps internal asset documentation out of the published page graph', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'vitepress-page-scope-'))
  try {
    for (const file of ['index.md', 'ko/topic.md', 'en/topic.md', 'assets/diagrams/_parked/README.md']) {
      const target = path.join(root, file)
      fs.mkdirSync(path.dirname(target), { recursive: true })
      fs.writeFileSync(target, '# Page')
    }
    const { pages } = await resolvePages(root, createVitepressBuildScope(), console)
    assert.deepEqual(pages.sort(), ['en/topic.md', 'index.md', 'ko/topic.md'])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
