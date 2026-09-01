import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

test('SageMaker Qwen PII validation report records the real blocked outcome', async () => {
  const json = JSON.parse(
    await readFile(
      path.join(
        root,
        'examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json',
      ),
      'utf8',
    ),
  )
  const report = await readFile(
    path.join(
      root,
      'docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md',
    ),
    'utf8',
  )

  assert.equal(json.status, 'blocked_before_training')
  assert.equal(json.training.sagemakerExecuted, false)
  assert.equal(json.training.eksExecuted, false)
  assert.deepEqual(json.dataset.counts, {
    train: 1600,
    validation: 200,
    test: 400,
  })
  assert.equal(json.cleanup.remainingResourceCount, 1)
  assert.match(report, /파인튜닝 학습 Job은 실행되지\s+않았다/)
  assert.match(report, /Unified Studio 프로젝트 1개/)
  assert.doesNotMatch(report, /fine-tuned micro-F1\s*[:=]\s*\d/i)
})
