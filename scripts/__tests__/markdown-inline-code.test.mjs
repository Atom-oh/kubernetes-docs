import assert from 'node:assert/strict'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { readFile } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import { compile } from '@vue/compiler-dom'
import { createMarkdownRenderer, resolveConfig } from 'vitepress'

async function render(source) {
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const config = await resolveConfig(root)
  const md = await createMarkdownRenderer(root, config.markdown, '/kubernetes-docs/')
  const html = md.render(source, { relativePath: 'en/fixture.md' })
  const errors = []
  const result = compile(html, {
    mode: 'module',
    prefixIdentifiers: true,
    onError: error => errors.push(error.message)
  })
  return { html, errors, code: result.code }
}

test('CJK emphasis repairs render as bold without changing prose, links or code', async () => {
  const script = fileURLToPath(new URL('../repair-markdown-emphasis.py', import.meta.url))
  const code = '> ```text\n> **leave code unchanged**\n> ```\n'
  const source = [
    'SSM에는 **nodeadm 1.0.19+**가 필요합니다.',
    '**Alpha gate（既定で無効）**が必要です。',
    '**本章并未证明部署成功。**本地检查见[说明](https://example.org/reference)。',
    '확인한 경로는 **`/health`**이며, 예시는 `**literal**`입니다.',
    code
  ].join('\n\n')
  const fixed = execFileSync('python3', [
    '-c', 'import runpy, sys; module = runpy.run_path(sys.argv[1]); sys.stdout.write(module["repair"](sys.stdin.read()))',
    script
  ], { input: source, encoding: 'utf8' })
  assert.equal(fixed.replaceAll('**', ''), source.replaceAll('**', ''))
  assert.ok(fixed.includes(code))
  assert.ok(fixed.includes('`**literal**`'))
  const { html, errors } = await render(fixed)
  assert.deepEqual(errors, [])
  assert.match(html, /<strong>nodeadm 1\.0\.19<\/strong>\+/)
  assert.match(html, /<strong>Alpha gate<\/strong>/)
  assert.match(html, /<strong>本章并未证明部署成功<\/strong>。/)
  assert.match(html, /href="https:\/\/example\.org\/reference"/)
  assert.match(html, /<strong><code[^>]*>\/health<\/code>이며<\/strong>/)
})

test('inline Docker and Helm templates remain literal and compile as Vue', async () => {
  const { html, errors, code } = await render(
    "Run `docker inspect --format='{{index .RepoDigests 0}}'` and keep `{{ .Values.name }}` literal."
  )
  assert.deepEqual(errors, [])
  assert.match(html, /<code v-pre=""/)
  assert.match(html, /\{\{index \.RepoDigests 0\}\}/)
  assert.doesNotMatch(code, /_ctx\.(index|Values)/)
})

test('inline HTML stays escaped while prose Vue bindings still work', async () => {
  const { html, errors, code } = await render(
    '`<img src=x onerror=alert(1)> {{ literal }}`\n\n<span>{{ count }}</span>'
  )
  assert.deepEqual(errors, [])
  assert.match(html, /&lt;img/)
  assert.doesNotMatch(html, /<img/)
  assert.doesNotMatch(code, /_ctx\.literal/)
  assert.match(code, /_ctx\.count/)
})

for (const locale of ['ko', 'en']) {
  test(`${locale}: Argo CD RBAC action placeholders do not become Vue elements`, async () => {
    const source = await readFile(new URL(`../../${locale}/gitops/argocd/06-projects-rbac.md`, import.meta.url), 'utf8')
    const { html, errors } = await render(source)
    assert.deepEqual(errors, [])
    assert.match(html, /update\/&lt;group&gt;\/&lt;kind&gt;\/&lt;namespace&gt;\/&lt;name&gt;/)
  })

  test(`${locale}: EKS diagnostic paths with placeholders compile as literal text`, async () => {
    const source = await readFile(new URL(`../../${locale}/eks/11-eks-advanced-debugging.md`, import.meta.url), 'utf8')
    const { html, errors } = await render(source)
    assert.deepEqual(errors, [])
    assert.match(html, /\/etc\/alertmanager\/secrets\/&lt;secret-name&gt;\//)
  })

  test(`${locale}: EKS diagnostic quiz commands compile with literal placeholders`, async () => {
    const source = await readFile(new URL(`../../${locale}/quizzes/eks/11-eks-advanced-debugging-quiz.md`, import.meta.url), 'utf8')
    const { html, errors } = await render(source)
    assert.deepEqual(errors, [])
    assert.match(html, /\/aws\/eks\/&lt;cluster-name&gt;\/cluster/)
    assert.match(html, /kubectl debug node\/&lt;node-name&gt; --image=&lt;reviewed-image&gt;/)
  })
}
