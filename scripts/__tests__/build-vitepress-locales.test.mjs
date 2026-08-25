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

import { mergeLocaleOutputs } from '../build-vitepress-locales.mjs'

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
