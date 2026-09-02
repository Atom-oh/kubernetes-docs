import assert from 'node:assert/strict'
import test from 'node:test'

import {
  applyBaseline,
  diffFileSets,
  expectedQuizPath,
  extractSummaryLinks
} from '../validate-language-parity.mjs'

test('diffFileSets reports files present in only one locale, sorted', () => {
  const ko = ['basics/01-linux.md', 'core/02-pods.md', 'ko-only/extra.md']
  const en = ['basics/01-linux.md', 'core/02-pods.md', 'en-only/other.md']

  assert.deepEqual(diffFileSets(ko, en), {
    onlyKo: ['ko-only/extra.md'],
    onlyEn: ['en-only/other.md']
  })
})

test('diffFileSets returns empty arrays for mirrored trees', () => {
  const files = ['a.md', 'b/c.md']
  assert.deepEqual(diffFileSets(files, [...files].reverse()), {
    onlyKo: [],
    onlyEn: []
  })
})

test('extractSummaryLinks normalizes ./ prefixes and ignores external links', () => {
  const summary = [
    '# Summary',
    '* [Intro](README.md)',
    '* [Linux](./basics/01-linux-basics.md)',
    '  * [Part 2](basics/01-linux-basics-part2.md)',
    '* [External](https://example.com/page.md)',
    '* [Anchor](#section)'
  ].join('\n')

  assert.deepEqual(extractSummaryLinks(summary), [
    'README.md',
    'basics/01-linux-basics.md',
    'basics/01-linux-basics-part2.md'
  ])
})

test('expectedQuizPath maps content files to quizzes/<path>-quiz.md', () => {
  assert.equal(
    expectedQuizPath('basics/01-linux-basics.md'),
    'quizzes/basics/01-linux-basics-quiz.md'
  )
  assert.equal(
    expectedQuizPath('networking/cilium/02-installation.md'),
    'quizzes/networking/cilium/02-installation-quiz.md'
  )
})

test('expectedQuizPath exempts READMEs, SUMMARY, quizzes, labs, and news', () => {
  assert.equal(expectedQuizPath('README.md'), null)
  assert.equal(expectedQuizPath('networking/README.md'), null)
  assert.equal(expectedQuizPath('SUMMARY.md'), null)
  assert.equal(expectedQuizPath('quizzes/basics/01-linux-basics-quiz.md'), null)
  assert.equal(expectedQuizPath('labs/basics/01-linux-basics-lab.md'), null)
  assert.equal(expectedQuizPath('news/README.md'), null)
})

test('expectedQuizPath exempts topic-quiz service-mesh subtrees but not service-mesh root', () => {
  assert.equal(expectedQuizPath('service-mesh/istio/traffic-management/02-routing.md'), null)
  assert.equal(expectedQuizPath('service-mesh/linkerd/01-installation.md'), null)
  assert.equal(expectedQuizPath('service-mesh/cilium-service-mesh/01-architecture.md'), null)
  assert.equal(
    expectedQuizPath('service-mesh/01-service-mesh-introduction.md'),
    'quizzes/service-mesh/01-service-mesh-introduction-quiz.md'
  )
})

test('applyBaseline suppresses baselined failures and reports stale entries', () => {
  const failures = [
    { rule: 'quiz-missing', path: 'ai-ml/01-ai-ml-workloads.md' },
    { rule: 'quiz-missing', path: 'core/99-new-page.md' }
  ]
  const baseline = {
    'quiz-missing': ['ai-ml/01-ai-ml-workloads.md', 'eks/gone-page.md'],
    'summary-missing': ['training/eks-auto-mode-2h-curriculum.md']
  }

  const { unexpected, stale } = applyBaseline(failures, baseline)

  assert.deepEqual(unexpected, [
    { rule: 'quiz-missing', path: 'core/99-new-page.md' }
  ])
  assert.deepEqual(stale, [
    { rule: 'quiz-missing', path: 'eks/gone-page.md' },
    { rule: 'summary-missing', path: 'training/eks-auto-mode-2h-curriculum.md' }
  ])
})
