import assert from 'node:assert/strict'
import test from 'node:test'

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
    'cn/**',
    'jp/**',
    'es/**'
  ])
})

test('VitePress rewrites only the supported locale entry pages', () => {
  assert.deepEqual(vitepressRewrites, {
    'ko/README.md': 'ko/index.md',
    'en/README.md': 'en/index.md'
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
      'cn/**',
      'jp/**',
      'es/**',
      'en/**'
    ],
    rewrites: {
      'ko/README.md': 'ko/index.md'
    }
  })
})

test('an unsupported VitePress build locale is rejected', () => {
  assert.throws(
    () => createVitepressBuildScope('cn'),
    /Unsupported VitePress locale: cn/
  )
})
