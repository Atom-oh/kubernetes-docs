#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const BASELINE_PATH = 'scripts/parity-baseline.json'
const EXTERNAL_TARGET = /^(?:[a-z][a-z0-9+.-]*:|\/\/|#)/i

// service-mesh subtrees whose quizzes use topic-based names (see CLAUDE.md
// "Naming Conventions" exception) rather than per-file <path>-quiz.md mirrors.
const TOPIC_QUIZ_SUBTREES = [
  'service-mesh/istio/',
  'service-mesh/linkerd/',
  'service-mesh/cilium-service-mesh/'
]

const QUIZ_EXEMPT_PREFIXES = ['quizzes/', 'labs/', 'news/']

export function diffFileSets(koFiles, enFiles) {
  const koSet = new Set(koFiles)
  const enSet = new Set(enFiles)
  return {
    onlyKo: [...koSet].filter((file) => !enSet.has(file)).sort(),
    onlyEn: [...enSet].filter((file) => !koSet.has(file)).sort()
  }
}

export function extractSummaryLinks(markdown) {
  const links = []
  for (const match of markdown.matchAll(/\[[^\]]*]\(\s*(?:<([^>]+)>|([^\s)]+))\s*\)/g)) {
    const target = (match[1] || match[2] || '').trim()
    if (!target || EXTERNAL_TARGET.test(target)) continue
    const clean = target.split(/[?#]/)[0].replace(/^\.\//, '')
    if (clean.endsWith('.md')) links.push(clean)
  }
  return links
}

export function expectedQuizPath(relativePath) {
  const basename = path.posix.basename(relativePath)
  if (basename === 'README.md' || basename === 'SUMMARY.md') return null
  if (QUIZ_EXEMPT_PREFIXES.some((prefix) => relativePath.startsWith(prefix))) return null
  if (TOPIC_QUIZ_SUBTREES.some((prefix) => relativePath.startsWith(prefix))) return null
  return path.posix.join('quizzes', relativePath.replace(/\.md$/, '-quiz.md'))
}

export function applyBaseline(failures, baseline) {
  const unexpected = failures.filter(
    (failure) => !(baseline[failure.rule] ?? []).includes(failure.path)
  )

  const failureKeys = new Set(failures.map((failure) => `${failure.rule}:${failure.path}`))
  const stale = []
  for (const [rule, paths] of Object.entries(baseline)) {
    for (const baselinePath of paths) {
      if (!failureKeys.has(`${rule}:${baselinePath}`)) {
        stale.push({ rule, path: baselinePath })
      }
    }
  }

  return { unexpected, stale }
}

async function collectMarkdownFiles(directory, base = directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await collectMarkdownFiles(entryPath, base))
    else if (entry.isFile() && entry.name.endsWith('.md')) {
      files.push(path.relative(base, entryPath).split(path.sep).join('/'))
    }
  }

  return files
}

export async function validateLanguageParity(repositoryRoot, locales = ['ko', 'en']) {
  const failures = []
  const fileSets = {}

  for (const locale of locales) {
    fileSets[locale] = await collectMarkdownFiles(path.join(repositoryRoot, locale))
  }

  // 1. The locale trees must be exact mirrors of each other.
  const [first, second] = locales
  const { onlyKo, onlyEn } = diffFileSets(fileSets[first], fileSets[second])
  for (const file of onlyKo) failures.push({ rule: `only-in-${first}`, path: file })
  for (const file of onlyEn) failures.push({ rule: `only-in-${second}`, path: file })

  for (const locale of locales) {
    const summary = await readFile(path.join(repositoryRoot, locale, 'SUMMARY.md'), 'utf8')
    const summaryLinks = new Set(extractSummaryLinks(summary))

    for (const file of fileSets[locale]) {
      // 2. Every page must be reachable from its locale's SUMMARY.md.
      if (file !== 'SUMMARY.md' && !summaryLinks.has(file)) {
        failures.push({ rule: 'summary-missing', path: `${locale}/${file}` })
      }

      // 3. Every content page must have its quiz counterpart.
      const quiz = expectedQuizPath(file)
      if (quiz && !existsSync(path.join(repositoryRoot, locale, quiz))) {
        failures.push({ rule: 'quiz-missing', path: `${locale}/${file}` })
      }
    }
  }

  return failures
}

async function loadBaseline(repositoryRoot) {
  const baselineFile = path.join(repositoryRoot, BASELINE_PATH)
  if (!existsSync(baselineFile)) return {}
  return JSON.parse(await readFile(baselineFile, 'utf8'))
}

async function main() {
  const repositoryRoot = path.resolve(process.cwd())
  const failures = await validateLanguageParity(repositoryRoot)
  const { unexpected, stale } = applyBaseline(failures, await loadBaseline(repositoryRoot))

  if (unexpected.length === 0 && stale.length === 0) {
    console.log('ko/en language parity validation passed.')
    return
  }

  for (const failure of unexpected) {
    console.error(`${failure.rule}: ${failure.path}`)
  }
  if (unexpected.length > 0) {
    console.error(
      `Found ${unexpected.length} parity failure(s). New content must ship with ` +
      'SUMMARY.md entries, a matching file in the other locale, and a quiz.'
    )
  }

  for (const entry of stale) {
    console.error(`stale baseline entry (${entry.rule}): ${entry.path} — remove it from ${BASELINE_PATH}`)
  }
  process.exitCode = 1
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await main()
}
