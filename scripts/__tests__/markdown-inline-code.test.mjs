import assert from 'node:assert/strict'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { readFile } from 'node:fs/promises'
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
}
