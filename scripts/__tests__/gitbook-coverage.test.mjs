import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { validateGitBookCoverage } from '../validate-gitbook-coverage.mjs'

test('coverage checks all locales and source navigation, including missing files and dangling entries', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gitbook-coverage-'))
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))
  for (const locale of ['en', 'cn', 'jp', 'es']) {
    fs.mkdirSync(path.join(root, locale, 'new-section'), { recursive: true })
    fs.writeFileSync(path.join(root, locale, 'README.md'), '# Home\n')
    fs.writeFileSync(path.join(root, locale, 'SUMMARY.md'), '* [New](new-section/page.md)\n')
    fs.writeFileSync(path.join(root, locale, 'new-section/page.md'), '# Content\n')
  }
  assert.ok(validateGitBookCoverage(root).every(result => !result.missing.length && !result.missingNavigation.length))
  fs.rmSync(path.join(root, 'cn/new-section/page.md'))
  fs.writeFileSync(path.join(root, 'jp/SUMMARY.md'), '* [Home](README.md)\n')
  fs.writeFileSync(path.join(root, 'es/extra.md'), '# Obsolete\n')
  const [cn, jp, es] = validateGitBookCoverage(root)
  assert.deepEqual(cn.missing, ['new-section/page.md'])
  assert.deepEqual(cn.brokenNavigation, ['new-section/page.md'])
  assert.deepEqual(jp.missing, [])
  assert.deepEqual(jp.missingNavigation, ['new-section/page.md'])
  assert.deepEqual(es.extra, ['extra.md'])
})
