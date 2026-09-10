import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { buildDocuments, generateLlmsFiles } from '../generate-llms-txt.mjs'
import { createDocsSearch, loadDocuments } from '../lib/docs-search.mjs'

const groups = [
  { group: 'Storage', items: [
    { title: 'EBS comparison', path: 'storage/benchmark.md' },
    { title: 'Duplicate', path: 'storage/benchmark.md' },
    { title: 'Missing', path: 'storage/missing.md' },
    { title: 'Quiz misplaced in navigation', path: 'quizzes/answer.md' },
    { title: 'Lab misplaced in navigation', path: 'labs/exercise.md' }
  ] },
  { group: 'Networking', items: [{ title: 'Cilium', path: 'networking/cilium.md' }] },
  { group: 'Quiz Collection', items: [{ title: 'Answer', path: 'quizzes/answer.md' }] },
  { group: 'Lab Guides', items: [{ title: 'Lab', path: 'labs/exercise.md' }] }
]
const pages = {
  'storage/benchmark.md': '# EBS gp2 gp3\n\n> **Last Updated**: September 10, 2026\n\nStorage throughput.\n\n## Measured result\n\n스토리지를 비교한 gp3 결과: 125 MiB/s.\n\n```sh\n# Not a heading\n```\n',
  'networking/cilium.md': '# Cilium networking\n\nCilium 네트워크 정책을 설명합니다.\n',
  'quizzes/answer.md': '# Answer key\n\nsecretquiztoken',
  'labs/exercise.md': '# Lab\n\nlabonlytoken'
}
const docs = ['ko', 'en'].flatMap(locale =>
  buildDocuments(locale, groups, name => pages[name] ?? null)
)

test('retrieval corpus excludes answers, labs, missing pages, and duplicate navigation', () => {
  assert.deepEqual(docs.map(doc => doc.id), [
    'ko/storage/benchmark.md', 'ko/networking/cilium.md',
    'en/storage/benchmark.md', 'en/networking/cilium.md'
  ])
  const doc = docs[0]
  assert.equal(doc.url, 'https://www.atomai.click/kubernetes-docs/ko/storage/benchmark')
  assert.equal(doc.markdownUrl, 'https://www.atomai.click/kubernetes-docs/llms/ko/storage/benchmark.md')
  assert.equal(doc.lastUpdated, '2026-09-10')
  assert.deepEqual(doc.headings, ['EBS gp2 gp3', 'Measured result'])
  assert.equal(doc.sha256, createHash('sha256').update(doc.content).digest('hex'))
  assert.equal(doc.bytes, Buffer.byteLength(doc.content))
})

test('keyword search finds body evidence with Korean prefixes and filters language and section', () => {
  const search = createDocsSearch(docs)
  const result = search.search({ query: '스토리지 gp3', locale: 'ko', section: 'storage' })
  assert.equal(result.results.length, 1)
  assert.equal(result.results[0].id, 'ko/storage/benchmark.md')
  assert.ok(result.results[0].snippet.includes('125 MiB/s'))
  assert.equal(result.results[0].content, undefined)
  assert.equal(search.search({ query: 'Cilium', locale: 'en' }).results[0].id, 'en/networking/cilium.md')
  assert.equal(search.search({ query: 'Cilium', locale: 'ko', section: 'storage' }).results.length, 0)
  assert.equal(search.search({ query: 'secretquiztoken' }).results.length, 0)
  assert.equal(search.search({ query: 'labonlytoken' }).results.length, 0)
  assert.equal(search.search({ query: 'missingterm' }).results.length, 0)
  assert.equal(search.search({ query: 'Cilium', locale: 'all', limit: 1 }).results.length, 1)
})

test('fetch paginates without losing text and rejects IDs outside the published corpus', () => {
  const search = createDocsSearch(docs)
  let content = ''
  let offset = 0
  do {
    const chunk = search.fetch({ id: 'ko/storage/benchmark.md', offset, maxLength: 100 })
    content += chunk.text
    offset = chunk.nextOffset
    assert.equal(chunk.totalChars, pages['storage/benchmark.md'].length)
    assert.ok(chunk.sha256)
  } while (offset !== null)
  assert.equal(content, pages['storage/benchmark.md'])
  const end = search.fetch({ id: docs[0].id, offset: content.length })
  assert.equal(end.text, '')
  assert.equal(end.nextOffset, null)
  for (const id of ['../../package.json', 'ko/quizzes/answer.md', 'ko/labs/exercise.md',
    '/etc/passwd', 'https://example.com/secret', 'ko/storage/missing.md']) {
    assert.throws(() => search.fetch({ id }), /Unknown document/)
  }
  assert.throws(() => search.fetch({ id: docs[0].id, offset: 99999 }), /offset/)
  assert.throws(() => search.fetch({ id: docs[0].id, offset: -1 }))
  assert.throws(() => search.fetch({ id: docs[0].id, maxLength: 1000000 }))
  assert.throws(() => search.search({ query: ' ', limit: 0 }))
  assert.throws(() => search.search({ query: 'Cilium', locale: 'jp' }))
})

test('fetch chunks survive UTF-8 encoding independently, and offsets cannot bisect an emoji', () => {
  const content = 'a'.repeat(99) + '🔍' + 'b'.repeat(120)
  const search = createDocsSearch([{ ...docs[0], content }])
  const first = search.fetch({ id: docs[0].id, maxLength: 100 })
  assert.equal(first.text, 'a'.repeat(99))
  assert.equal(first.nextOffset, 99)
  let offset = 0
  const encodedChunks = []
  do {
    const chunk = search.fetch({ id: docs[0].id, offset, maxLength: 100 })
    encodedChunks.push(Buffer.from(chunk.text, 'utf8'))
    offset = chunk.nextOffset
  } while (offset !== null)
  assert.equal(Buffer.concat(encodedChunks).toString('utf8'), content)
  assert.throws(() => search.fetch({ id: docs[0].id, offset: 100 }), /offset/)
})

test('search excerpts do not emit partial emoji at their length boundary', () => {
  const content = 'hit ' + 'a'.repeat(595) + '🔍' + 'b'.repeat(120)
  const search = createDocsSearch([{ ...docs[0], content }])
  const { snippet } = search.search({ query: 'hit' }).results[0]
  assert.equal(Buffer.from(snippet, 'utf8').toString('utf8'), snippet)
})

test('published manifest describes exact Markdown bytes and changes only with content', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'docs-manifest-'))
  try {
    for (const locale of ['ko', 'en']) {
      fs.mkdirSync(path.join(root, locale, 'storage'), { recursive: true })
      fs.writeFileSync(path.join(root, locale, 'SUMMARY.md'),
        '# Contents\n\n## Storage\n\n* [EBS](storage/benchmark.md)\n')
      fs.writeFileSync(path.join(root, locale, 'storage/benchmark.md'),
        pages['storage/benchmark.md'] + '\n![diagram](../../assets/diagram.png)\n')
    }
    generateLlmsFiles(root)
    const file = path.join(root, 'public/llms/manifest.json')
    const before = fs.readFileSync(file, 'utf8')
    const manifest = JSON.parse(before)
    assert.equal(manifest.schemaVersion, 1)
    assert.equal(manifest.documents.length, 2)
    const doc = manifest.documents[0]
    assert.equal(doc.content, undefined)
    const raw = fs.readFileSync(path.join(root, 'public/llms', doc.id))
    assert.equal(doc.sha256, createHash('sha256').update(raw).digest('hex'))
    assert.equal(doc.bytes, raw.length)
    assert.ok(raw.toString().includes('https://raw.githubusercontent.com/Atom-oh/kubernetes-docs/main/assets/diagram.png'))
    assert.ok(fs.readFileSync(path.join(root, 'public/llms.txt'), 'utf8').includes('/llms/manifest.json'))
    assert.deepEqual(loadDocuments(root).map(({ content, ...metadata }) => metadata), manifest.documents)
    generateLlmsFiles(root)
    assert.equal(fs.readFileSync(file, 'utf8'), before)
    fs.appendFileSync(path.join(root, 'ko/storage/benchmark.md'), '\nNew measurement.\n')
    generateLlmsFiles(root)
    const after = JSON.parse(fs.readFileSync(file, 'utf8'))
    assert.notEqual(after.documents[0].sha256, doc.sha256)
    assert.equal(after.documents[1].sha256, manifest.documents[1].sha256)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
