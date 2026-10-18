import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { extractSummaryLinks } from './validate-language-parity.mjs'

function markdownFiles(directory, base = directory) {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(directory, entry.name)
    return entry.isDirectory() ? markdownFiles(file, base) :
      entry.isFile() && entry.name.endsWith('.md') ? [path.relative(base, file).split(path.sep).join('/')] : []
  })
}

export function validateGitBookCoverage(root) {
  const sources = new Set(markdownFiles(path.join(root, 'en')))
  if (!sources.size) throw new Error('No English source pages found')
  const summary = fs.readFileSync(path.join(root, 'en/SUMMARY.md'), 'utf8')
  const sourceNavigation = new Set(extractSummaryLinks(summary))
  const results = []
  for (const locale of ['cn', 'jp', 'es']) {
    const files = new Set(markdownFiles(path.join(root, locale)))
    const summaryPath = path.join(root, locale, 'SUMMARY.md')
    const navigation = new Set(fs.existsSync(summaryPath) ?
      extractSummaryLinks(fs.readFileSync(summaryPath, 'utf8')) : [])
    results.push({
      locale, sourceCount: sources.size, pageCount: files.size,
      missing: [...sources].filter(file => !files.has(file)).sort(),
      extra: [...files].filter(file => !sources.has(file)).sort(),
      missingNavigation: [...sourceNavigation].filter(file => !navigation.has(file)).sort(),
      brokenNavigation: [...navigation].filter(file => !files.has(file)).sort()
    })
  }
  return results
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const results = validateGitBookCoverage(process.cwd())
  for (const result of results) {
    console.log(`${result.locale}: ${result.pageCount}/${result.sourceCount} pages; ` +
      `${result.missing.length} missing, ${result.extra.length} extra, ` +
      `${result.missingNavigation.length} missing navigation, ${result.brokenNavigation.length} broken navigation`)
    for (const key of ['missing', 'extra', 'missingNavigation', 'brokenNavigation']) {
      for (const file of result[key]) console.error(`${result.locale} ${key}: ${file}`)
    }
  }
  if (results.some(result => ['missing', 'extra', 'missingNavigation', 'brokenNavigation']
    .some(key => result[key].length))) process.exitCode = 1
}
