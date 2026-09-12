import assert from 'node:assert/strict'
import { createReadStream } from 'node:fs'
import {
  mkdtemp,
  mkdir,
  readFile,
  rm,
  writeFile
} from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { parseSitemap } from 'sitemap'

import {
  LEGACY_LOCALES,
  markArchmapsNoindex,
  mergeLocaleOutputs,
  writeLegacyLocaleRedirects
} from '../build-vitepress-locales.mjs'

const sitemap = (url) => `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${url}</loc></url>
</urlset>
`

test('locale build outputs are merged with a combined sitemap', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'vitepress-locales-'))
  const koOutput = path.join(root, 'ko-build')
  const enOutput = path.join(root, 'en-build')
  const dist = path.join(root, 'dist')

  try {
    await mkdir(path.join(koOutput, 'ko'), { recursive: true })
    await mkdir(path.join(koOutput, 'assets'), { recursive: true })
    await mkdir(path.join(enOutput, 'en'), { recursive: true })
    await mkdir(path.join(enOutput, 'assets'), { recursive: true })

    await writeFile(path.join(koOutput, 'ko', 'index.html'), 'Korean')
    await writeFile(path.join(enOutput, 'en', 'index.html'), 'English')
    await writeFile(path.join(koOutput, 'assets', 'ko.js'), 'ko')
    await writeFile(path.join(enOutput, 'assets', 'en.js'), 'en')
    await writeFile(
      path.join(koOutput, 'sitemap.xml'),
      sitemap('https://www.atomai.click/kubernetes-docs/ko/')
    )
    await writeFile(
      path.join(enOutput, 'sitemap.xml'),
      sitemap('https://www.atomai.click/kubernetes-docs/en/')
    )

    await mergeLocaleOutputs([koOutput, enOutput], dist)

    assert.equal(
      await readFile(path.join(dist, 'ko', 'index.html'), 'utf8'),
      'Korean'
    )
    assert.equal(
      await readFile(path.join(dist, 'en', 'index.html'), 'utf8'),
      'English'
    )
    assert.equal(await readFile(path.join(dist, 'assets', 'ko.js'), 'utf8'), 'ko')
    assert.equal(await readFile(path.join(dist, 'assets', 'en.js'), 'utf8'), 'en')

    const items = await parseSitemap(createReadStream(path.join(dist, 'sitemap.xml')))
    assert.deepEqual(
      items.map(({ url }) => url).sort(),
      [
        'https://www.atomai.click/kubernetes-docs/en/',
        'https://www.atomai.click/kubernetes-docs/ko/'
      ]
    )
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('indexed ko/en README URLs redirect to their live section without changing canonical pages', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'readme-redirects-'))
  const source = path.join(root, 'source')
  const dist = path.join(root, 'dist')
  const cases = [
    ['ko/index.html', 'ko/README.html', 'https://www.atomai.click/kubernetes-docs/ko/'],
    ['en/index.html', 'en/README.html', 'https://www.atomai.click/kubernetes-docs/en/'],
    ['ko/networking/cilium/index.html', 'ko/networking/cilium/README.html', 'https://www.atomai.click/kubernetes-docs/ko/networking/cilium/'],
    ['en/networking/cilium/index.html', 'en/networking/cilium/README.html', 'https://www.atomai.click/kubernetes-docs/en/networking/cilium/'],
    ['en/service-mesh/istio/advanced/index.html', 'en/service-mesh/istio/advanced/README.html', 'https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/advanced/']
  ]

  try {
    for (const [page] of cases) {
      await mkdir(path.dirname(path.join(source, page)), { recursive: true })
      await writeFile(path.join(source, page), `Content of ${page}`)
    }
    await writeFile(path.join(source, 'en/networking/cilium/01-introduction.html'), 'Article')
    await writeFile(path.join(source, 'sitemap.xml'), sitemap('https://www.atomai.click/kubernetes-docs/en/'))

    await mergeLocaleOutputs([source], dist)

    for (const [page, alias, target] of cases) {
      const html = await readFile(path.join(dist, alias), 'utf8')
      assert.equal(html.match(/http-equiv="refresh" content="0; url=([^"]+)"/)?.[1], target)
      assert.equal(html.match(/rel="canonical" href="([^"]+)"/)?.[1], target)
      assert.ok(html.includes(`<a href="${target}">`))
      assert.equal(await readFile(path.join(dist, page), 'utf8'), `Content of ${page}`)
    }
    assert.equal(await readFile(path.join(dist, 'en/networking/cilium/01-introduction.html'), 'utf8'), 'Article')

    // Retired-language redirects still point directly to the live English
    // directory, rather than chaining through a newly generated README alias.
    const retired = await readFile(path.join(dist, 'cn/networking/cilium/README.html'), 'utf8')
    assert.equal(retired.match(/http-equiv="refresh" content="0; url=([^"]+)"/)?.[1],
      'https://www.atomai.click/kubernetes-docs/en/networking/cilium/')

    const items = await parseSitemap(createReadStream(path.join(dist, 'sitemap.xml')))
    assert.deepEqual(items.map(({ url }) => url), ['https://www.atomai.click/kubernetes-docs/en/'])
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('README compatibility redirects preserve an existing page and tolerate a missing locale', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'readme-redirects-existing-'))
  const source = path.join(root, 'source')
  const dist = path.join(root, 'dist')

  try {
    await mkdir(path.join(source, 'ko/networking'), { recursive: true })
    await writeFile(path.join(source, 'ko/index.html'), 'Korean home')
    await writeFile(path.join(source, 'ko/README.html'), 'Existing page')
    await writeFile(path.join(source, 'ko/networking/index.html'), 'Networking')
    await writeFile(path.join(source, 'sitemap.xml'), sitemap('https://www.atomai.click/kubernetes-docs/ko/'))

    await mergeLocaleOutputs([source], dist)

    assert.equal(await readFile(path.join(dist, 'ko/README.html'), 'utf8'), 'Existing page')
    const nested = await readFile(path.join(dist, 'ko/networking/README.html'), 'utf8')
    assert.equal(nested.match(/http-equiv="refresh" content="0; url=([^"]+)"/)?.[1],
      'https://www.atomai.click/kubernetes-docs/ko/networking/')
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('archmap viewer pages are marked noindex after the merge', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'archmap-noindex-'))
  const dist = path.join(root, 'dist')
  const archmaps = path.join(dist, 'archmaps')

  try {
    await mkdir(archmaps, { recursive: true })
    await writeFile(
      path.join(archmaps, 'ko-example-0.html'),
      '<!doctype html><html><head><title>Diagram</title></head><body></body></html>'
    )
    await writeFile(
      path.join(archmaps, 'already.html'),
      '<!doctype html><html><head><meta name="robots" content="noindex"><title>D</title></head><body></body></html>'
    )
    await writeFile(path.join(archmaps, 'notes.txt'), 'not html')

    const marked = await markArchmapsNoindex(dist)
    assert.equal(marked, 1)

    const patched = await readFile(path.join(archmaps, 'ko-example-0.html'), 'utf8')
    assert.match(patched, /<head>\s*<meta name="robots" content="noindex, follow">/)
    assert.match(patched, /<title>Diagram<\/title>/)

    // Already-marked pages are left byte-identical rather than double-tagged.
    const untouched = await readFile(path.join(archmaps, 'already.html'), 'utf8')
    assert.equal((untouched.match(/name="robots"/g) || []).length, 1)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('merged diagram viewers normalize CJK fonts and mobile toolbars without changing ordinary pages', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'archmap-fonts-'))
  const source = path.join(root, 'source')
  const dist = path.join(root, 'dist')
  const stack = "'JetBrains Mono', ui-monospace, monospace"
  const viewer = `<html><head><style>body { font-family: ${stack}; }</style></head>
<body><script id="archify-i18n-data" type="application/json">{}</script>
<script>const exportFont = "600 12px ${stack}";</script>
<p>Generator가 만든 파라미터 조합마다 Application 하나가 생성된다</p></body></html>`
  try {
    await mkdir(path.join(source, 'archmaps'), { recursive: true })
    await writeFile(path.join(source, 'sitemap.xml'), sitemap('https://example.com/'))
    await writeFile(path.join(source, 'archmaps', 'ko-example.html'), viewer)
    await writeFile(path.join(source, 'archmaps', 'jp-example.html'), viewer)
    await writeFile(path.join(source, 'ordinary.html'), viewer)

    await mergeLocaleOutputs([source], dist)
    const korean = await readFile(path.join(dist, 'archmaps', 'ko-example.html'), 'utf8')
    const japanese = await readFile(path.join(dist, 'archmaps', 'jp-example.html'), 'utf8')
    assert.equal((korean.match(/'JetBrains Mono', 'Noto Sans CJK KR'/g) || []).length, 2)
    assert.equal((japanese.match(/'JetBrains Mono', 'Noto Sans CJK JP'/g) || []).length, 2)
    assert.ok(korean.includes('Generator가 만든 파라미터 조합마다'))
    assert.equal((korean.match(/id="docs-archmap-responsive"/g) || []).length, 1)
    assert.equal((japanese.match(/id="docs-archmap-responsive"/g) || []).length, 1)
    assert.equal(await readFile(path.join(dist, 'ordinary.html'), 'utf8'), viewer)

    const second = path.join(root, 'second')
    await mergeLocaleOutputs([dist], second)
    assert.equal(await readFile(path.join(second, 'archmaps', 'ko-example.html'), 'utf8'), korean)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('legacy cn/jp/es URLs get redirect stubs to the English page', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'legacy-redirects-'))
  const dist = path.join(root, 'dist')

  try {
    await mkdir(path.join(dist, 'en', 'networking', 'calico'), { recursive: true })
    await writeFile(path.join(dist, 'en', 'index.html'), 'en root')
    await writeFile(path.join(dist, 'en', 'networking', 'calico', 'index.html'), 'section')
    await writeFile(path.join(dist, 'en', 'networking', 'calico', '02-architecture.html'), 'page')

    const written = await writeLegacyLocaleRedirects(dist)
    // 3 locales × (root index + README, section index + README, one page)
    assert.equal(written, LEGACY_LOCALES.length * 5)

    const page = await readFile(
      path.join(dist, 'cn', 'networking', 'calico', '02-architecture.html'),
      'utf8'
    )
    const target = 'https://www.atomai.click/kubernetes-docs/en/networking/calico/02-architecture'
    assert.match(page, new RegExp(`http-equiv="refresh" content="0; url=${target}"`))
    assert.match(page, new RegExp(`rel="canonical" href="${target}"`))

    // The five-locale build published section indexes as README.html.
    const legacyReadme = await readFile(
      path.join(dist, 'es', 'networking', 'calico', 'README.html'),
      'utf8'
    )
    assert.match(legacyReadme, /url=https:\/\/www\.atomai\.click\/kubernetes-docs\/en\/networking\/calico\//)

    const root404 = await readFile(path.join(dist, 'jp', 'index.html'), 'utf8')
    assert.match(root404, /url=https:\/\/www\.atomai\.click\/kubernetes-docs\/en\//)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('writeLegacyLocaleRedirects is a no-op without an English build', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'legacy-redirects-missing-'))
  try {
    assert.equal(await writeLegacyLocaleRedirects(root), 0)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('markArchmapsNoindex is a no-op when the archmaps directory is absent', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'archmap-noindex-missing-'))
  try {
    assert.equal(await markArchmapsNoindex(root), 0)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})
