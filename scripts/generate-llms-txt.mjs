// Generates the llms.txt endpoints (https://llmstxt.org) into public/ so every
// deploy ships an LLM-consumable index (llms.txt) and full-content dumps
// (llms-full-<locale>.txt) of the published ko/en pages.
//
// SUMMARY.md (GitBook nav) is the canonical page list, same as the sidebar.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { supportedLocales } from '../.vitepress/site-scope.mjs'
import { extractDescription } from '../.vitepress/seo.mjs'

const scriptPath = fileURLToPath(import.meta.url)
const projectRoot = path.resolve(path.dirname(scriptPath), '..')

export const SITE_BASE = 'https://www.atomai.click/kubernetes-docs'
// Images and other non-page assets are referenced relatively from the source
// tree and get content-hashed by VitePress, so the raw repo is the only stable
// absolute address for them.
export const RAW_BASE = 'https://raw.githubusercontent.com/Atom-oh/kubernetes-docs/main'

const LOCALE_LABELS = { ko: '한국어', en: 'English' }
const QUIZ_GROUP = /quiz/i
const LAB_GROUP = /lab guides/i
const ROOT_INDEX = 'README.md'

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

export function markdownPageUrl(locale, mdPath) {
  return `${SITE_BASE}/llms/${locale}/${mdPath}`
}

export function sectionBundleUrl(locale, slug) {
  return `${SITE_BASE}/llms-full-${locale}-${slug}.txt`
}

const NOT_MIRRORED = /^(quizzes|labs)\//

// Relative links only resolve inside the repo checkout. An LLM reading a page
// out of context needs every reference to be fetchable, so rewrite them:
//   - links to a ko/en content page → that page's raw Markdown twin
//   - links to quizzes/labs/locale roots (not mirrored) → the rendered page
//   - anything else (images, root README, code) → the raw file on GitHub
// Absolute URLs, anchors, and paths escaping the repo are left untouched.
export function absolutizeLinks(content, locale, mdPath, locales = supportedLocales) {
  const fromDir = path.posix.dirname(path.posix.join(locale, mdPath))

  return content.replace(
    /(!?\[[^\]]*\]\()([^)\s]+)(\))/g,
    (whole, open, target, close) => {
      if (
        /^[a-z][a-z0-9+.-]*:/i.test(target) ||
        target.startsWith('#') ||
        target.startsWith('//') ||
        target.startsWith('/')
      ) {
        return whole
      }

      const hashIndex = target.indexOf('#')
      const hash = hashIndex === -1 ? '' : target.slice(hashIndex)
      const bare = hashIndex === -1 ? target : target.slice(0, hashIndex)
      if (!bare) return whole

      const resolved = path.posix.normalize(path.posix.join(fromDir, bare))
      if (resolved.startsWith('../')) return whole

      const [head, ...rest] = resolved.split('/')
      const inLocale = locales.includes(head) && rest.length > 0
      const inner = rest.join('/')

      let url
      if (inLocale && inner.endsWith('.md')) {
        url =
          inner === ROOT_INDEX || NOT_MIRRORED.test(inner)
            ? pageUrl(head, inner)
            : markdownPageUrl(head, inner)
      } else {
        url = `${RAW_BASE}/${resolved}`
      }
      return `${open}${url}${hash}${close}`
    }
  )
}

// A SUMMARY group's bundle slug is the top-level directory most of its pages
// live in (e.g. "Kubernetes 핵심 개념" → core); language-independent, so the
// ko and en bundles for the same section share a name. Groups made of
// root-level pages (roadmap, llm-guide) collapse to "intro".
export function groupSlug({ items }) {
  const counts = new Map()
  for (const { path: mdPath } of items) {
    const segment = mdPath.includes('/') ? mdPath.split('/')[0] : 'intro'
    counts.set(segment, (counts.get(segment) ?? 0) + 1)
  }
  let best
  for (const [segment, count] of counts) {
    if (!best || count > best.count) best = { segment, count }
  }
  return best ? best.segment.toLowerCase() : 'intro'
}

// [{ group, slug, count }] for every content group of a locale, slugs made
// unique in SUMMARY order.
export function sectionBundles(groups, readPage) {
  const bundles = []
  const used = new Set()
  for (const group of groups) {
    if (QUIZ_GROUP.test(group.group) || LAB_GROUP.test(group.group)) continue
    const pages = group.items.filter(
      ({ path: mdPath }) => mdPath !== ROOT_INDEX && readPage(mdPath) !== null
    )
    if (pages.length === 0) continue

    let slug = groupSlug(group)
    for (let n = 2; used.has(slug); n += 1) slug = `${groupSlug(group)}-${n}`
    used.add(slug)
    bundles.push({ group: group.group, slug, count: pages.length, items: pages })
  }
  return bundles
}

export function buildLlmsTxt(
  summariesByLocale,
  readPagesByLocale = {},
  bundlesByLocale = {}
) {
  const lines = [
    '# Cloud Native Operations',
    '',
    '> Hands-on Kubernetes, Amazon EKS, and cloud-native operations guidebook —',
    '> Linux/container foundations, Kubernetes core, EKS, networking, service mesh,',
    '> storage, databases, data pipelines, AI/ML, security, GitOps, platform',
    '> engineering, observability, and operations, with measured-on-AWS benchmark',
    '> data. Korean (ko) is the primary human-edited language; English (en) mirrors',
    '> its coverage. Full-content dumps: llms-full-ko.txt and llms-full-en.txt;',
    '> per-section dumps (a few hundred KiB each) are listed under "Section',
    '> bundles". Every link below returns raw Markdown with absolute URLs.',
    ''
  ]
  for (const locale of Object.keys(summariesByLocale)) {
    lines.push(`## Docs (${LOCALE_LABELS[locale] ?? locale})`, '')
    for (const { group, items } of summariesByLocale[locale]) {
      if (QUIZ_GROUP.test(group) || LAB_GROUP.test(group)) continue
      for (const { title, path: mdPath } of items) {
        if (mdPath === ROOT_INDEX) continue

        const readPage = readPagesByLocale[locale]
        const content = readPage?.(mdPath)
        if (readPage && content === null) continue

        const label = group === title ? title : `${group} · ${title}`
        const description =
          typeof content === 'string' ? extractDescription(content) : undefined
        lines.push(
          `- [${label}](${markdownPageUrl(locale, mdPath)})${
            description ? `: ${description}` : ''
          }`
        )
      }
    }
    lines.push('')
  }
  for (const locale of Object.keys(bundlesByLocale)) {
    const bundles = bundlesByLocale[locale]
    if (!bundles || bundles.length === 0) continue
    lines.push(`## Section bundles (${LOCALE_LABELS[locale] ?? locale})`, '')
    for (const { group, slug, count } of bundles) {
      lines.push(
        `- [${group}](${sectionBundleUrl(locale, slug)}): ${count} page${
          count === 1 ? '' : 's'
        } concatenated, each preceded by a "Source:" block`
      )
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
      if (mdPath === ROOT_INDEX) continue

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

function writeMarkdownPages(root, locale, groups, readPage) {
  const rawRoot = path.join(root, 'public', 'llms', locale)
  const seen = new Set()

  for (const { group, items } of groups) {
    if (QUIZ_GROUP.test(group) || LAB_GROUP.test(group)) continue

    for (const { path: mdPath } of items) {
      if (mdPath === ROOT_INDEX || seen.has(mdPath)) continue
      seen.add(mdPath)

      const content = readPage(mdPath)
      if (content === null) continue

      const outputPath = path.join(rawRoot, mdPath)
      fs.mkdirSync(path.dirname(outputPath), { recursive: true })
      fs.writeFileSync(outputPath, content)
    }
  }
}

export function generateLlmsFiles(root = projectRoot) {
  const outDir = path.join(root, 'public')
  fs.mkdirSync(outDir, { recursive: true })
  fs.rmSync(path.join(outDir, 'llms'), { recursive: true, force: true })

  for (const stale of fs.readdirSync(outDir)) {
    if (/^llms-full-.*\.txt$/.test(stale)) fs.rmSync(path.join(outDir, stale))
  }

  const summaries = {}
  const readPages = {}
  const bundles = {}
  for (const locale of supportedLocales) {
    summaries[locale] = parseSummary(
      fs.readFileSync(path.join(root, locale, 'SUMMARY.md'), 'utf8')
    )
    readPages[locale] = (mdPath) => {
      const filePath = path.join(root, locale, mdPath)
      if (!fs.existsSync(filePath)) return null
      return absolutizeLinks(fs.readFileSync(filePath, 'utf8'), locale, mdPath)
    }
    bundles[locale] = sectionBundles(summaries[locale], readPages[locale])
    writeMarkdownPages(root, locale, summaries[locale], readPages[locale])
  }

  const written = []
  const indexPath = path.join(outDir, 'llms.txt')
  fs.writeFileSync(indexPath, buildLlmsTxt(summaries, readPages, bundles))
  written.push(indexPath)

  for (const locale of supportedLocales) {
    for (const bundle of bundles[locale]) {
      const { text } = buildLlmsFull(
        locale,
        [{ group: bundle.group, items: bundle.items }],
        readPages[locale]
      )
      const bundlePath = path.join(outDir, `llms-full-${locale}-${bundle.slug}.txt`)
      fs.writeFileSync(bundlePath, text)
      written.push(bundlePath)
    }
  }

  for (const locale of supportedLocales) {
    const { text, missing } = buildLlmsFull(
      locale,
      summaries[locale],
      readPages[locale]
    )
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
