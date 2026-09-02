// Generates the llms.txt endpoints (https://llmstxt.org) into public/ so every
// deploy ships an LLM-consumable index (llms.txt) and full-content dumps
// (llms-full-<locale>.txt) of the published ko/en pages.
//
// SUMMARY.md (GitBook nav) is the canonical page list, same as the sidebar.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { supportedLocales } from '../.vitepress/site-scope.mjs'

const scriptPath = fileURLToPath(import.meta.url)
const projectRoot = path.resolve(path.dirname(scriptPath), '..')

export const SITE_BASE = 'https://www.atomai.click/kubernetes-docs'

const LOCALE_LABELS = { ko: '한국어', en: 'English' }
const QUIZ_GROUP = /quiz/i
const LAB_GROUP = /lab guides/i

// GitBook SUMMARY.md -> [{ group, items: [{ title, path }] }], link items only,
// deduped by path within a group list (multi-part topics repeat part1 as the
// parent entry and its first child).
export function parseSummary(source) {
  const groups = []
  let current = null
  for (const line of source.split('\n')) {
    const heading = line.match(/^## (.+)$/)
    if (heading) {
      current = { group: heading[1].trim(), items: [], seen: new Set() }
      groups.push(current)
      continue
    }
    const item = line.match(/^ *\* \[(.+?)\]\((.+?)\)/)
    if (!item || !current) continue
    const [, title, target] = item
    if (current.seen.has(target)) continue
    current.seen.add(target)
    current.items.push({ title, path: target })
  }
  for (const group of groups) delete group.seen
  return groups
}

// SUMMARY-relative markdown path -> published clean URL
// (cleanUrls strips .md; README.md becomes the directory index).
export function pageUrl(locale, mdPath) {
  const withoutReadme = mdPath.replace(/(^|\/)README\.md$/, '$1')
  const clean = withoutReadme.replace(/\.md$/, '')
  return `${SITE_BASE}/${locale}/${clean}`
}

export function buildLlmsTxt(summariesByLocale) {
  const lines = [
    '# Cloud Native Operations',
    '',
    '> Hands-on Kubernetes, Amazon EKS, and cloud-native operations guidebook —',
    '> Linux/container foundations, Kubernetes core, EKS, networking, service mesh,',
    '> storage, databases, data pipelines, AI/ML, security, GitOps, platform',
    '> engineering, observability, and operations, with measured-on-AWS benchmark',
    '> data. Korean (ko) is the primary human-edited language; English (en) mirrors',
    '> its coverage. Full-content dumps: llms-full-ko.txt and llms-full-en.txt.',
    ''
  ]
  for (const locale of Object.keys(summariesByLocale)) {
    lines.push(`## Docs (${LOCALE_LABELS[locale] ?? locale})`, '')
    for (const { group, items } of summariesByLocale[locale]) {
      if (QUIZ_GROUP.test(group) || LAB_GROUP.test(group)) continue
      for (const { title, path: mdPath } of items) {
        const label = group === title ? title : `${group} · ${title}`
        lines.push(`- [${label}](${pageUrl(locale, mdPath)})`)
      }
    }
    lines.push('')
  }
  lines.push('## Optional', '')
  for (const locale of Object.keys(summariesByLocale)) {
    const label = LOCALE_LABELS[locale] ?? locale
    lines.push(
      `- [Quizzes (${label})](${pageUrl(locale, 'quizzes/README.md')})`,
      `- [Labs (${label})](${pageUrl(locale, 'labs/README.md')})`
    )
  }
  lines.push('')
  return lines.join('\n')
}

const SEPARATOR = '-'.repeat(40)

export function buildLlmsFull(locale, groups, readPage) {
  const chunks = []
  const missing = []
  for (const { group, items } of groups) {
    if (QUIZ_GROUP.test(group)) continue
    for (const { path: mdPath } of items) {
      const content = readPage(mdPath)
      if (content === null) {
        missing.push(mdPath)
        continue
      }
      chunks.push(
        `${SEPARATOR}\nSource: ${pageUrl(locale, mdPath)}\n${SEPARATOR}\n\n${content.trimEnd()}\n`
      )
    }
  }
  return { text: chunks.join('\n'), missing }
}

export function generateLlmsFiles(root = projectRoot) {
  const outDir = path.join(root, 'public')
  fs.mkdirSync(outDir, { recursive: true })

  const summaries = {}
  for (const locale of supportedLocales) {
    summaries[locale] = parseSummary(
      fs.readFileSync(path.join(root, locale, 'SUMMARY.md'), 'utf8')
    )
  }

  const written = []
  const indexPath = path.join(outDir, 'llms.txt')
  fs.writeFileSync(indexPath, buildLlmsTxt(summaries))
  written.push(indexPath)

  for (const locale of supportedLocales) {
    const readPage = (mdPath) => {
      const filePath = path.join(root, locale, mdPath)
      return fs.existsSync(filePath) ? fs.readFileSync(filePath, 'utf8') : null
    }
    const { text, missing } = buildLlmsFull(locale, summaries[locale], readPage)
    for (const mdPath of missing) {
      console.warn(`llms-full-${locale}: skipping missing page ${locale}/${mdPath}`)
    }
    const fullPath = path.join(outDir, `llms-full-${locale}.txt`)
    fs.writeFileSync(fullPath, text)
    written.push(fullPath)
  }
  return written
}

if (process.argv[1] && path.resolve(process.argv[1]) === scriptPath) {
  for (const file of generateLlmsFiles()) {
    const size = (fs.statSync(file).size / 1024 / 1024).toFixed(2)
    console.log(`wrote ${path.relative(projectRoot, file)} (${size} MiB)`)
  }
}
