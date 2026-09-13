import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { resolveConfig } from 'vitepress'

test('Markdown discovery is managed by VitePress across client navigation, without an SSR-only duplicate', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const config = await resolveConfig(root)
  const pageData = {
    filePath: 'ko/llm-guide.md',
    relativePath: 'ko/llm-guide.md',
    title: 'LLM guide',
    frontmatter: { head: [['meta', { name: 'test-existing-head', content: 'keep' }]] }
  }
  await config.transformPageData(pageData, { siteConfig: config })
  // Only frontmatter.head is reconciled by VitePress's useUpdateHead on SPA
  // navigation. transformHead-only links remain stuck on the initial page.
  const markdownLinks = head => head.filter(([tag, attrs]) =>
    tag === 'link' && attrs.type === 'text/markdown')
  assert.deepEqual(markdownLinks(pageData.frontmatter.head), [[
    'link',
    {
      rel: 'alternate',
      type: 'text/markdown',
      href: 'https://www.atomai.click/kubernetes-docs/llms/ko/llm-guide.md'
    }
  ]])
  assert.ok(pageData.frontmatter.head.some(([, attrs]) => attrs.name === 'test-existing-head'))
  assert.deepEqual(markdownLinks(await config.transformHead({ pageData })), [])
})

test('canonical, language alternates and article metadata follow the current page during SPA navigation', async () => {
  const config = await resolveConfig(fileURLToPath(new URL('../../', import.meta.url)))
  for (const name of ['llm-guide', 'roadmap']) {
    const pageData = {
      filePath: `ko/${name}.md`,
      relativePath: `ko/${name}.md`,
      title: name,
      frontmatter: {}
    }
    await config.transformPageData(pageData, { siteConfig: config })
    const head = pageData.frontmatter.head
    const url = `https://www.atomai.click/kubernetes-docs/ko/${name}`
    assert.equal(head.find(([, attrs]) => attrs.rel === 'canonical')?.[1].href, url)
    assert.equal(head.find(([, attrs]) => attrs.property === 'og:url')?.[1].content, url)
    assert.equal(head.find(([, attrs]) => attrs.hreflang === 'en')?.[1].href,
      `https://www.atomai.click/kubernetes-docs/en/${name}`)
    const json = JSON.parse(head.find(([, attrs]) => attrs.type === 'application/ld+json')[2])
    assert.equal(json['@graph'][0].mainEntityOfPage['@id'], url)
    assert.deepEqual(await config.transformHead({ pageData }), [])
  }
})
