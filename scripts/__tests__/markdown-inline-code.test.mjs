import assert from 'node:assert/strict'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
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
