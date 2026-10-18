#!/usr/bin/env node
// GitHub Pages (www.atomai.click) only forwards visitors to docs.atomai.click.
// For the given locales, every page in the built site becomes a redirect stub
// to the same docs.atomai.click URL, so www does not carry a second full copy
// of them. Pages that already are stubs (they target docs.atomai.click) stay.
//
// Usage: node scripts/www-redirect-stubs.mjs <dist> <locale>...
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { listHtmlFiles, redirectStub } from './build-vitepress-locales.mjs'

const DOCS_ROOT = 'https://docs.atomai.click/kubernetes-docs/'

export async function writeWwwRedirectStubs(dist, locales) {
  let written = 0
  for (const locale of locales) {
    let pages
    try {
      pages = await listHtmlFiles(path.join(dist, locale))
    } catch (error) {
      if (error.code === 'ENOENT') continue
      throw error
    }
    for (const page of pages) {
      const filePath = path.join(dist, locale, page)
      if ((await readFile(filePath, 'utf8')).includes('http-equiv="refresh"')) continue
      const cleanPath = page === 'index.html' || page.endsWith('/index.html')
        ? page.slice(0, -'index.html'.length)
        : page.replace(/\.html$/, '')
      await writeFile(filePath, redirectStub(`${DOCS_ROOT}${locale}/${cleanPath}`))
      written += 1
    }
  }
  return written
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [dist, ...locales] = process.argv.slice(2)
  if (!dist || locales.length === 0) {
    console.error('Usage: node scripts/www-redirect-stubs.mjs <dist> <locale>...')
    process.exit(2)
  }
  const written = await writeWwwRedirectStubs(dist, locales)
  console.log(`Replaced ${written} ${locales.join('/')} pages with docs.atomai.click redirects`)
}
