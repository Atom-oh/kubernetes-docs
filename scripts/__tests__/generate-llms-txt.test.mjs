import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildLlmsFull,
  buildLlmsTxt,
  generateLlmsFiles,
  pageUrl,
  parseSummary,
  SITE_BASE
} from '../generate-llms-txt.mjs'
import fs from 'node:fs'

const SAMPLE = `# Table of contents

## Intro

* [Intro](README.md)

## Kubernetes

* [Cluster Architecture](core/01-cluster-architecture.md)
* [Custom Scheduler](scheduling/01-custom-scheduler-part1.md)
  * [Part 1: Basics](scheduling/01-custom-scheduler-part1.md)
  * [Part 2: Implementation](scheduling/02-custom-scheduler-part2.md)
* Autoscaling
  * [KEDA](autoscaling/01-keda.md)

## Storage

* [Storage Overview](storage/README.md)

## Quiz Collection

* [Quizzes](quizzes/README.md)
  * [KEDA Quiz](quizzes/autoscaling/05-keda-quiz.md)
`

test('pageUrl maps README and regular pages to published clean URLs', () => {
  assert.equal(pageUrl('ko', 'README.md'), `${SITE_BASE}/ko/`)
  assert.equal(pageUrl('ko', 'storage/README.md'), `${SITE_BASE}/ko/storage/`)
  assert.equal(
    pageUrl('en', 'core/01-cluster-architecture.md'),
    `${SITE_BASE}/en/core/01-cluster-architecture`
  )
})

test('parseSummary dedupes a part1 repeated as parent and first child', () => {
  const groups = parseSummary(SAMPLE)
  const k8s = groups.find((g) => g.group === 'Kubernetes')
  const schedulerEntries = k8s.items.filter((i) =>
    i.path.includes('01-custom-scheduler-part1.md')
  )
  assert.equal(schedulerEntries.length, 1)
  assert.equal(schedulerEntries[0].title, 'Custom Scheduler')
  assert.ok(k8s.items.some((i) => i.path === 'autoscaling/01-keda.md'))
})

test('llms.txt index lists content pages and excludes quiz pages', () => {
  const index = buildLlmsTxt({ en: parseSummary(SAMPLE) })
  assert.ok(index.includes(`${SITE_BASE}/en/core/01-cluster-architecture`))
  assert.ok(index.includes(`${SITE_BASE}/en/storage/`))
  assert.ok(!index.includes('05-keda-quiz'))
  // quiz index stays reachable via the Optional section
  assert.ok(index.includes(`- [Quizzes (English)](${SITE_BASE}/en/quizzes/)`))
})

test('llms-full excludes quiz groups and skips missing pages without failing', () => {
  const groups = parseSummary(SAMPLE)
  const pages = {
    'README.md': '# Intro\nhello',
    'core/01-cluster-architecture.md': '# Cluster\nbody'
  }
  const { text, missing } = buildLlmsFull('en', groups, (p) => pages[p] ?? null)
  assert.ok(text.includes(`Source: ${SITE_BASE}/en/core/01-cluster-architecture`))
  assert.ok(!text.includes('quizzes/'))
  assert.ok(missing.includes('storage/README.md'))
})

test('generation from the real repo produces a non-empty index', () => {
  const [indexPath] = generateLlmsFiles()
  const index = fs.readFileSync(indexPath, 'utf8')
  assert.ok(index.startsWith('# Cloud Native Operations'))
  assert.ok(index.includes('## Docs'))
  assert.ok(index.length > 10000)
})
