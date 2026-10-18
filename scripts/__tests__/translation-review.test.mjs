import assert from 'node:assert/strict'
import test from 'node:test'
import { reviewBatches, proseSections, reviewScore } from '../review-translation-batch.mjs'

test('review input retains all prose sections across batch boundaries while excluding fenced code', () => {
  const source = '# Source\n\nIntro\n\n```yaml\nkind: Pod\n```\n\n## End\nLast source sentence.\n'
  const translated = '# Traducción\n\nInicio\n\n```yaml\nkind: Pod\n```\n\n## Fin\nÚltima frase.\n'
  const batches = reviewBatches([{ path: 'es/topic.md', source, translated }], 100)
  const records = batches.flat()
  assert.ok(batches.length > 1)
  assert.equal(records.map(record => record.source).join(''), proseSections(source).join(''))
  assert.equal(records.map(record => record.translated).join(''), proseSections(translated).join(''))
  assert.ok(records.some(record => record.translated.includes('Última frase.')))
  assert.ok(records.every(record => !record.source.includes('kind: Pod')))
  assert.throws(() => reviewBatches([{ path: 'es/topic.md', source, translated: '# Incomplete' }]), /Heading/)
})

test('quality review parsing rejects missing feedback, invalid scores and extra contradictory output', () => {
  assert.deepEqual(reviewScore('SCORE: 85\nFEEDBACK: no defects found\n'), { score: 85, feedback: 'no defects found' })
  assert.equal(reviewScore('SCORE: 0\nFEEDBACK: missing text').score, 0)
  for (const output of ['SCORE: 101\nFEEDBACK: x', 'SCORE: 90', 'SCORE: 90\nFEEDBACK: x\nSCORE: 50']) {
    assert.throws(() => reviewScore(output), /Invalid/)
  }
})
