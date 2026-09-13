import assert from 'node:assert/strict'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  absolutizeLinks,
  buildLlmsFull,
  buildLlmsTxt,
  generateLlmsFiles,
  groupSlug,
  pageUrl,
  parseSummary,
  RAW_BASE,
  sectionBundles,
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
  const pages = {
    'README.md': '# Intro\n\nNavigation only.',
    'core/01-cluster-architecture.md':
      '# Cluster Architecture\n\nExplains the Kubernetes control plane and worker nodes.',
    'storage/README.md':
      '# Storage Overview\n\nIntroduces persistent storage options for Kubernetes.'
  }
  const index = buildLlmsTxt(
    { en: parseSummary(SAMPLE) },
    { en: (mdPath) => pages[mdPath] ?? null }
  )

  assert.ok(
    index.includes(
      `- [Kubernetes · Cluster Architecture](${SITE_BASE}/llms/en/core/01-cluster-architecture.md): Explains the Kubernetes control plane and worker nodes.`
    )
  )
  assert.ok(index.includes(`${SITE_BASE}/llms/en/storage/README.md`))
  assert.ok(!index.includes(`${SITE_BASE}/llms/en/README.md`))
  assert.ok(!index.includes('05-keda-quiz'))
  // quiz index stays reachable via the Optional section
  assert.ok(index.includes(`- [Quizzes (English)](${SITE_BASE}/en/quizzes/)`))
})

test('llms-full excludes root navigation, quiz groups, and missing pages', () => {
  const groups = parseSummary(SAMPLE)
  const pages = {
    'README.md': '# Intro\nnavigation only',
    'core/01-cluster-architecture.md': '# Cluster\nbody'
  }
  const { text, missing } = buildLlmsFull('en', groups, (p) => pages[p] ?? null)
  assert.ok(text.includes(`Source: ${SITE_BASE}/en/core/01-cluster-architecture`))
  assert.ok(!text.includes('navigation only'))
  assert.ok(!text.includes('quizzes/'))
  assert.ok(missing.includes('storage/README.md'))
})

test('absolutizeLinks rewrites relative references to fetchable URLs', () => {
  const src = [
    'See [architecture](../core/01-cluster-architecture.md#nodes) and',
    '[the quiz](../quizzes/networking/01-quiz.md), [home](../README.md).',
    '![diagram](../../assets/diagrams/flow.svg)',
    '![png](../.gitbook/assets/ko-net-0.png)',
    '[external](https://kubernetes.io/docs/) [anchor](#top) [root](/kubernetes-docs/ko/)'
  ].join('\n')
  const out = absolutizeLinks(src, 'ko', 'networking/01-introduction.md')

  assert.ok(out.includes(`(${SITE_BASE}/llms/ko/core/01-cluster-architecture.md#nodes)`))
  assert.ok(out.includes(`(${SITE_BASE}/ko/quizzes/networking/01-quiz)`))
  assert.ok(out.includes(`[home](${SITE_BASE}/ko/)`))
  assert.ok(out.includes(`(${RAW_BASE}/assets/diagrams/flow.svg)`))
  assert.ok(out.includes(`(${RAW_BASE}/ko/.gitbook/assets/ko-net-0.png)`))
  assert.ok(out.includes('(https://kubernetes.io/docs/)'))
  assert.ok(out.includes('(#top)'))
  assert.ok(out.includes('(/kubernetes-docs/ko/)'))
})

test('absolutizeLinks leaves paths that escape the repository alone', () => {
  const src = '[up](../../../outside.md)'
  assert.equal(absolutizeLinks(src, 'ko', 'basics/01.md'), src)
})

test('groupSlug picks the dominant top-level directory, or intro for root pages', () => {
  const groups = parseSummary(SAMPLE)
  // 2 scheduling pages vs 1 core and 1 autoscaling → scheduling dominates
  assert.equal(groupSlug(groups.find((g) => g.group === 'Kubernetes')), 'scheduling')
  assert.equal(groupSlug(groups.find((g) => g.group === 'Storage')), 'storage')
  assert.equal(groupSlug({ items: [{ path: 'roadmap.md' }, { path: 'llm-guide.md' }] }), 'intro')
})

test('sectionBundles skips quiz groups, empty groups, and dedupes slugs', () => {
  const groups = parseSummary(SAMPLE)
  const pages = new Set([
    'README.md',
    'core/01-cluster-architecture.md',
    'scheduling/01-custom-scheduler-part1.md',
    'scheduling/02-custom-scheduler-part2.md',
    'autoscaling/01-keda.md'
  ])
  const bundles = sectionBundles(groups, (p) => (pages.has(p) ? 'body' : null))

  assert.deepEqual(
    bundles.map(({ group, slug, count }) => ({ group, slug, count })),
    [{ group: 'Kubernetes', slug: 'scheduling', count: 4 }]
  )
  // Intro (root README only) and Storage (missing page) produce no bundle.
  assert.ok(!bundles.some((b) => b.group === 'Storage'))

  const twice = sectionBundles(
    [
      { group: 'A', items: [{ path: 'core/a.md' }] },
      { group: 'B', items: [{ path: 'core/b.md' }] }
    ],
    () => 'body'
  )
  assert.deepEqual(twice.map((b) => b.slug), ['core', 'core-2'])
})

test('llms.txt lists section bundles per locale', () => {
  const index = buildLlmsTxt(
    { en: parseSummary(SAMPLE) },
    {},
    { en: [{ group: 'Kubernetes', slug: 'core', count: 4 }] }
  )
  assert.ok(index.includes('## Section bundles (English)'))
  assert.ok(
    index.includes(`- [Kubernetes](${SITE_BASE}/llms-full-en-core.txt): 4 pages concatenated`)
  )
  // Section bundles come before Optional, as llms.txt readers scan top-down.
  assert.ok(index.indexOf('## Section bundles') < index.indexOf('## Optional'))
})

test('generation writes each indexed page as raw Markdown', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'llms-pages-'))

  try {
    for (const locale of ['ko', 'en']) {
      fs.mkdirSync(path.join(root, locale, 'core'), { recursive: true })
      fs.writeFileSync(
        path.join(root, locale, 'SUMMARY.md'),
        [
          '# Table of contents',
          '',
          '## Intro',
          '',
          '* [Intro](README.md)',
          '',
          '## Kubernetes',
          '',
          '* [Cluster Architecture](core/01-cluster-architecture.md)'
        ].join('\n')
      )
      fs.writeFileSync(
        path.join(root, locale, 'README.md'),
        '# Intro\n\nNavigation only.'
      )
      fs.writeFileSync(
        path.join(root, locale, 'core/01-cluster-architecture.md'),
        '# Cluster Architecture\n\nActual LLM-readable body. ![d](../../assets/d.svg)'
      )
    }
    // A stale bundle from a section that no longer exists must not survive.
    fs.mkdirSync(path.join(root, 'public'), { recursive: true })
    fs.writeFileSync(path.join(root, 'public', 'llms-full-ko-removed.txt'), 'old')

    const written = generateLlmsFiles(root)

    const rawPath = path.join(
      root,
      'public/llms/ko/core/01-cluster-architecture.md'
    )
    assert.equal(
      fs.readFileSync(rawPath, 'utf8'),
      `# Cluster Architecture\n\nActual LLM-readable body. ![d](${RAW_BASE}/assets/d.svg)`
    )

    const bundlePath = path.join(root, 'public', 'llms-full-ko-core.txt')
    assert.ok(written.includes(bundlePath))
    assert.ok(
      fs.readFileSync(bundlePath, 'utf8').includes(
        `Source: ${SITE_BASE}/ko/core/01-cluster-architecture`
      )
    )
    assert.ok(!fs.existsSync(path.join(root, 'public', 'llms-full-ko-removed.txt')))
    assert.ok(
      fs.readFileSync(path.join(root, 'public', 'llms.txt'), 'utf8').includes(
        `${SITE_BASE}/llms-full-ko-core.txt`
      )
    )
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test('generation from the real repo produces a non-empty index', () => {
  const [indexPath] = generateLlmsFiles()
  const index = fs.readFileSync(indexPath, 'utf8')
  assert.ok(index.startsWith('# Cloud Native Operations'))
  assert.ok(index.includes('## Docs'))
  assert.ok(index.length > 10000)
})
