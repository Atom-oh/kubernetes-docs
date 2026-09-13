import assert from 'node:assert/strict'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { createMarkdownRenderer, resolveConfig } from 'vitepress'

test('Korean manual TOC links point at VitePress heading IDs despite Unicode normalization', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const config = await resolveConfig(root)
  const md = await createMarkdownRenderer(root, config.markdown, '/kubernetes-docs/')
  const tokens = md.parse('# 예제\n\n[목차 이동](#네트워킹-모델)\n\n## 네트워킹 모델\n', { relativePath: 'ko/example.md' })
  const heading = tokens.find(token => token.type === 'heading_open' && token.tag === 'h2')
  const paragraph = tokens.find(token => token.type === 'inline' && token.content.startsWith('[목차 이동]'))
  const href = paragraph.children.find(token => token.type === 'link_open').attrGet('href')
  assert.equal(decodeURIComponent(href.slice(1)), heading.attrGet('id'))
})

test('explicit HTML IDs and unknown or cross-page fragments are preserved', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const config = await resolveConfig(root)
  const md = await createMarkdownRenderer(root, config.markdown, '/kubernetes-docs/')
  const tokens = md.parse(
    '# 제목\n\n<span id="네트워킹-모델"></span>\n\n## 네트워킹 모델\n\n[custom](#네트워킹-모델) [missing](#missing) [other](other.md#네트워킹-모델)\n',
    { relativePath: 'ko/example.md' }
  )
  const paragraph = tokens.find(token => token.type === 'inline' && token.content.startsWith('[custom]'))
  const links = paragraph.children.filter(token => token.type === 'link_open').map(token => decodeURIComponent(token.attrGet('href')))
  assert.deepEqual(links, ['#네트워킹-모델', '#missing', 'other.md#네트워킹-모델'])
})
