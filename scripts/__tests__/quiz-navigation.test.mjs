import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const repositoryRoot = path.resolve(import.meta.dirname, '../..')

for (const locale of ['ko', 'en']) {
  test(`${locale} quiz navigation uses label-only groups`, () => {
    const summary = readFileSync(path.join(repositoryRoot, locale, 'SUMMARY.md'), 'utf8')

    assert.doesNotMatch(summary, /\]\(quiz\//)
    assert.equal(existsSync(path.join(repositoryRoot, locale, 'quiz')), false)
    assert.equal(existsSync(path.join(repositoryRoot, locale, 'quizzes')), true)
  })
}
