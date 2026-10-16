#!/usr/bin/env node
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { extractLastUpdated } from '../.vitepress/seo.mjs'
import { buildNewsData } from './lib/news-data.mjs'

export const NEWS_DATA_PATH = '.vitepress/theme/news.generated.json'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

export function generateNewsData(repositoryRoot = root, { check = false, requireSourcesWeek } = {}) {
  const sources = Object.fromEntries(['ko', 'en'].map(locale => [
    locale, fs.readFileSync(path.join(repositoryRoot, locale, 'news/README.md'), 'utf8')
  ]))
  const data = buildNewsData(sources.ko, sources.en, { requireSourcesWeek })
  for (const locale of ['ko', 'en']) {
    const log = sources[locale].match(/<details\b[^>]*\bclass=["'][^"']*\bnews-log\b[^"']*["'][^>]*>[\s\S]*?<\/details>/)?.[0]
    const logHeading = locale === 'ko' ? '## 갱신 로그' : '## Update Log'
    if (!sources[locale].includes('<!-- news-dashboard -->') || !log?.includes(logHeading)) {
      throw new Error(`${locale}: preserve the news-dashboard marker and news-log details wrapper`)
    }
    const updated = extractLastUpdated(sources[locale])
    if (!updated) throw new Error(`${locale}: news page needs a valid last-updated header`)
    data.locales[locale].updated = updated
    for (const entry of data.locales[locale].entries) {
      for (const document of entry.documents) {
        if (!fs.existsSync(path.join(repositoryRoot, locale, document))) {
          throw new Error(`${locale}: news document does not exist: ${document}`)
        }
      }
    }
  }
  if (data.locales.ko.updated !== data.locales.en.updated) {
    throw new Error('Korean and English news last-updated dates differ')
  }
  const target = path.join(repositoryRoot, NEWS_DATA_PATH)
  const serialized = `${JSON.stringify(data, null, 2)}\n`
  if (check) {
    if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== serialized) {
      throw new Error('News dashboard data is stale. Run npm run docs:news and commit the generated file.')
    }
  } else {
    fs.mkdirSync(path.dirname(target), { recursive: true })
    fs.writeFileSync(target, serialized)
  }
  return data
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const allowed = process.argv.slice(2)
    if (allowed.some(arg => arg !== '--check' && !/^--require-sources-week=\d{4}-W\d{2}$/.test(arg))) {
      throw new Error('Usage: generate-news-data.mjs [--check] [--require-sources-week=YYYY-Www]')
    }
    const data = generateNewsData(root, {
      check: allowed.includes('--check'),
      requireSourcesWeek: allowed.find(arg => arg.startsWith('--require-sources-week='))?.split('=')[1]
    })
    console.log(`News dashboard: ${data.locales.ko.entries.length} bilingual records ${allowed.includes('--check') ? 'verified' : 'generated'}.`)
  } catch (error) {
    console.error(error.message)
    process.exitCode = 1
  }
}
