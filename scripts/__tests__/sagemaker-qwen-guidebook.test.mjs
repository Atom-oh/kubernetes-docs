import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const read = (relative) => readFileSync(path.join(root, relative), 'utf8')

const pagePaths = [
  'ai-ml/sagemaker-ai/README.md',
  'ai-ml/sagemaker-ai/01-platform-architecture.md',
  'ai-ml/sagemaker-ai/02-pii-data-tokenization.md',
  'ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md',
  'data-on-eks/sagemaker-unified-studio/README.md',
  'data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md',
  'ai-ml/sagemaker-ai/04-validation-results.md',
]

const quizPaths = [
  'quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md',
  'quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md',
  'quizzes/ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution-quiz.md',
  'quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md',
  'quizzes/ai-ml/sagemaker-ai/04-validation-results-quiz.md',
]

for (const locale of ['ko', 'en']) {
  test(`${locale}: five-part SageMaker Qwen guidebook is complete and truthful`, () => {
    const combined = pagePaths.map((page) => read(`${locale}/${page}`)).join('\n')
    assert.match(combined, /Qwen\/Qwen3-30B-A3B-Instruct-2507/)
    assert.match(combined, /TYPE<TAB>ORIGINAL/)
    assert.match(combined, /2,200/)
    assert.match(combined, /1,600.*200.*400/s)
    assert.match(combined, /80%.*20%/s)
    assert.match(combined, /3\.10\.1/)
    assert.match(combined, /(?:미실행|not executed)/i)
    assert.match(combined, /(?:membership|멤버십)/i)
    assert.doesNotMatch(combined, /fine-tuned micro-F1\s*[:=]\s*\d/i)
    assert.doesNotMatch(combined, /GPU cost\s*[:=]\s*\$?\d/i)

    for (const quiz of quizPaths) {
      assert.ok(existsSync(path.join(root, locale, quiz)), `${locale}/${quiz}`)
    }

    const summary = read(`${locale}/SUMMARY.md`)
    assert.match(summary, /sagemaker-ai\/README\.md/)
    assert.match(summary, /sagemaker-unified-studio\/README\.md/)
  })
}

test('Archify sources, viewers, and static images exist for both locales', () => {
  const bases = [
    'ko-ai-ml-sagemaker-ai-01-platform-architecture-0',
    'en-ai-ml-sagemaker-ai-01-platform-architecture-0',
    'ko-ai-ml-sagemaker-ai-04-validation-results-0',
    'en-ai-ml-sagemaker-ai-04-validation-results-0',
  ]
  for (const base of bases) {
    const type = base.includes('04-validation') ? 'workflow' : 'architecture'
    assert.ok(
      existsSync(path.join(root, `assets/diagrams/archify/${base}.${type}.json`)),
    )
    assert.ok(existsSync(path.join(root, `public/archmaps/${base}.html`)))
    const locale = base.slice(0, 2)
    assert.ok(existsSync(path.join(root, `${locale}/.gitbook/assets/${base}.png`)))
  }
})
