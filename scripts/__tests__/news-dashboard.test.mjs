import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { buildNewsData, parseNewsLog } from '../lib/news-data.mjs'
import {
  filterNews, heatmapCount, isoWeek, newsDocumentUrl,
  newsStats, newsWeeks, recentWeeks, weekStart
} from '../lib/news-dashboard.mjs'
import { generateNewsData, NEWS_DATA_PATH } from '../generate-news-data.mjs'

const ko = lines => `# 소식\n> **마지막 업데이트**: 2026년 10월 16일\n\n<!-- news-dashboard -->\n<details class="news-log">\n<summary>로그</summary>\n\n## 갱신 로그\n\n${lines}\n\n</details>\n`
const en = lines => `# News\n> **Last Updated**: October 16, 2026\n\n<!-- news-dashboard -->\n<details class="news-log">\n<summary>Log</summary>\n\n## Update Log\n\n${lines}\n\n</details>\n`
const matched = (summary, language = 'en', period = '2026-W42', source = 'https://example.org/release') =>
  `- ${period}: [core/guide.md](../core/guide.md) — ${summary}${source ? ` ([${language === 'ko' ? '원문' : 'source'}](${source}))` : ''}`

test('ISO weeks use UTC and cross calendar years without skipping empty weeks', () => {
  assert.equal(isoWeek('2021-01-01'), '2020-W53')
  assert.equal(isoWeek('2026-07-11'), '2026-W28')
  assert.deepEqual(recentWeeks('2021-W02', 4), ['2020-W52', '2020-W53', '2021-W01', '2021-W02'])
  assert.deepEqual(recentWeeks('2026-W36').slice(-3), ['2026-W34', '2026-W35', '2026-W36'])
  for (const bad of ['2026-02-30', '2026-13-01', 'invalid']) assert.throws(() => isoWeek(bad))
  for (const bad of ['2025-W53', '2026-W00', '2026-W54']) assert.throws(() => weekStart(bad))
})

test('a bilingual announcement links several documents but contributes one heatmap record', () => {
  const links = '[core/guide.md](../core/guide.md) · [eks/guide.md](../eks/guide.md)'
  const data = buildNewsData(
    ko(`- 2026-W42: ${links} — 보안 패치 (CVE-2026-1234 수정) ([원문](https://example.org/security))`),
    en(`- 2026-W42: ${links} — Security patch (CVE-2026-1234 fixed) ([source](https://example.org/security))`),
    { requireSourcesWeek: '2026-W42' }
  )
  const records = data.locales.ko.entries
  assert.deepEqual(newsStats(records), { records: 1, security: 1, documents: 2, unmatched: 0 })
  assert.equal(heatmapCount(records, 'kubernetes', '2026-W42'), 1)
  assert.equal(heatmapCount(records, 'kubernetes', '2026-W41'), 0)
  assert.equal(records[0].id, data.locales.en.entries[0].id)
  assert.equal(records[0].category, 'security')
  assert.equal(records[0].summary.includes('원문'), false)
  assert.equal(records[0].title, '보안 패치')
})

test('source-only items and original date labels remain distinct from logging weeks', () => {
  const record = parseNewsLog(en('- 2026-07-11: no matching doc — Kubeflow graduation ([source](https://example.org/kubeflow))'), 'en')[0]
  assert.equal(record.period, '2026-07-11')
  assert.equal(record.week, '2026-W28')
  assert.deepEqual(record.documents, [])
  assert.deepEqual(record.sources, ['https://example.org/kubeflow'])
  assert.equal(record.summary, 'Kubeflow graduation')
})

test('bilingual parity checks week labels, document paths, source URLs and record multiplicity', () => {
  const korean = ko(matched('업데이트', 'ko'))
  const english = en(matched('Update'))
  for (const replacement of [
    english.replace('2026-W42', '2026-W41'),
    english.replaceAll('core/guide.md', 'eks/guide.md'),
    english.replace('example.org/release', 'example.org/other'),
    english.replace('</details>', `${matched('Another update')}\n</details>`)
  ]) assert.throws(() => buildNewsData(korean, replacement), /counterpart|missing from Korean/)
  assert.equal(buildNewsData(korean, english).locales.en.entries.length, 1)
})

test('historical source-less logs are retained while current batches require links and deduplicate sources', () => {
  const historicalKo = ko(matched('과거 기록', 'ko', '2026-W36', ''))
  const historicalEn = en(matched('Historical record', 'en', '2026-W36', ''))
  assert.equal(buildNewsData(historicalKo, historicalEn).locales.ko.entries.length, 1)
  assert.throws(() => buildNewsData(historicalKo, historicalEn, { requireSourcesWeek: '2026-W36' }), /official source/)
  const korean = ko(`${matched('업데이트', 'ko')}\n${matched('추가 문서', 'ko').replaceAll('core/guide.md', 'eks/guide.md')}`)
  const english = en(`${matched('Update')}\n${matched('Other guide').replaceAll('core/guide.md', 'eks/guide.md')}`)
  assert.throws(() => buildNewsData(korean, english, { requireSourcesWeek: '2026-W42' }), /Duplicate source/)
})

test('bad log formats, unsafe URLs, traversal and impossible dates fail instead of silently disappearing', () => {
  const valid = matched('Update')
  for (const line of [
    valid.replace('2026-W42', '2026-W99'),
    valid.replace('2026-W42', '2026-02-30'),
    valid.replace(' — ', ' - '),
    valid.replaceAll('../core/guide.md', '../../outside.md'),
    valid.replace('https://example.org/release', 'javascript:alert'),
    valid.replace('https://example.org/release', '//example.org/release'),
    '- 2026-W42: no matching doc — No links'
  ]) assert.throws(() => parseNewsLog(en(line), 'en'))
  assert.throws(() => parseNewsLog('# News\n', 'en'), /empty or missing/)
})

test('topic, week, type and multi-word search combine; summary stats count unique documents', () => {
  const data = buildNewsData(
    ko(`${matched('보안 CVE-2026-1234', 'ko')}\n${matched('릴리스', 'ko', '2026-W41')}`),
    en(`${matched('Security patch CVE-2026-1234')}\n${matched('Release v1.37', 'en', '2026-W41')}`)
  )
  const records = data.locales.en.entries
  assert.deepEqual(newsWeeks(records), ['2026-W42', '2026-W41'])
  assert.equal(filterNews(records, { topic: 'kubernetes', category: 'security', week: '2026-W42', query: 'SECURITY 1234' }).length, 1)
  assert.equal(filterNews(records, { week: '2026-W41', category: 'security' }).length, 0)
  assert.equal(filterNews(records, { query: 'core/guide.md' }).length, 2)
  assert.equal(newsStats(records).documents, 1)
  assert.deepEqual(newsStats([]), { records: 0, security: 0, documents: 0, unmatched: 0 })
  assert.equal(newsDocumentUrl('/kubernetes-docs/', 'en', 'service-mesh/istio/README.md'), '/kubernetes-docs/en/service-mesh/istio/')
  assert.equal(newsDocumentUrl('/kubernetes-docs/', 'ko', 'core/01-architecture.md'), '/kubernetes-docs/ko/core/01-architecture')
})

test('generated data checks detect stale summaries, missing documents and date mismatches', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'news-dashboard-'))
  try {
    for (const language of ['ko', 'en']) {
      fs.mkdirSync(path.join(root, language, 'news'), { recursive: true })
      fs.mkdirSync(path.join(root, language, 'core'), { recursive: true })
      fs.writeFileSync(path.join(root, language, 'core/guide.md'), '# Guide\n')
    }
    fs.writeFileSync(path.join(root, 'ko/news/README.md'), ko(matched('업데이트', 'ko')))
    fs.writeFileSync(path.join(root, 'en/news/README.md'), en(matched('Update')))
    generateNewsData(root)
    const original = fs.readFileSync(path.join(root, NEWS_DATA_PATH), 'utf8')
    generateNewsData(root, { check: true })
    generateNewsData(root)
    assert.equal(fs.readFileSync(path.join(root, NEWS_DATA_PATH), 'utf8'), original)
    fs.writeFileSync(path.join(root, 'en/news/README.md'), en(matched('Update')).replace('<!-- news-dashboard -->', ''))
    assert.throws(() => generateNewsData(root), /marker/)
    fs.writeFileSync(path.join(root, 'en/news/README.md'), en(matched('Changed summary')))
    assert.throws(() => generateNewsData(root, { check: true }), /stale/)
    fs.writeFileSync(path.join(root, 'en/news/README.md'), en(matched('Update')).replace('October 16', 'October 15'))
    assert.throws(() => generateNewsData(root), /dates differ/)
    fs.writeFileSync(path.join(root, 'en/news/README.md'), en(matched('Update')))
    fs.rmSync(path.join(root, 'en/core/guide.md'))
    assert.throws(() => generateNewsData(root), /does not exist/)
  } finally { fs.rmSync(root, { recursive: true, force: true }) }
})
