import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { supportedLocales } from './site-scope.mjs'

export const siteHostname = 'https://www.atomai.click/kubernetes-docs/'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MAX_DESCRIPTION_LENGTH = 160

// Only same-site links (relative or root-absolute) are candidates; README.md is
// the GitBook section-index convention that VitePress rewrites to index.md.
const README_HREF_RE = /(^|\/)README\.md(#.*)?$/

export function normalizeReadmeHref(href) {
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('//')) return href
  return href.replace(README_HREF_RE, (_, prefix, hash) => `${prefix}index.md${hash ?? ''}`)
}

function stripInlineMarkdown(text) {
  return text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // images
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // links → label
    .replace(/`([^`]*)`/g, '$1') // inline code
    .replace(/(\*\*|__)(.*?)\1/g, '$2') // bold
    .replace(/(\*|_)(.*?)\1/g, '$2') // italic
    .replace(/<[^>]+>/g, '') // inline HTML tags
    .replace(/\s+/g, ' ')
    .trim()
}

function truncateAtBoundary(text) {
  if (text.length <= MAX_DESCRIPTION_LENGTH) return text

  const window = text.slice(0, MAX_DESCRIPTION_LENGTH)
  // Prefer a sentence boundary (Latin or CJK full stop) inside the window.
  const sentenceEnd = Math.max(
    window.lastIndexOf('. '),
    window.lastIndexOf('! '),
    window.lastIndexOf('? '),
    window.endsWith('.') || window.endsWith('!') || window.endsWith('?')
      ? window.length - 1
      : -1,
    window.lastIndexOf('。')
  )
  if (sentenceEnd > 0) return window.slice(0, sentenceEnd + 1).trim()

  const wordEnd = window.lastIndexOf(' ', MAX_DESCRIPTION_LENGTH - 1)
  return `${window.slice(0, wordEnd > 0 ? wordEnd : MAX_DESCRIPTION_LENGTH - 1).trim()}…`
}

// First real body paragraph of a markdown document, as plain text capped at
// 160 chars — used as the page's meta description when frontmatter has none.
export function extractDescription(markdown) {
  let src = markdown.replace(/^---\n[\s\S]*?\n---\n?/, '') // frontmatter
  src = src.replace(/<!--[\s\S]*?-->/g, '') // comments

  const lines = src.split('\n')
  const paragraph = []
  let inFence = false

  for (const line of lines) {
    const trimmed = line.trim()

    if (/^(```|~~~)/.test(trimmed)) {
      inFence = !inFence
      continue
    }
    if (inFence) continue

    // A <details> block on a quiz page holds the answer. Skipping just the tag
    // line leaves the answer itself as the first "paragraph", which then ships
    // as the page's meta description and gives the answer away in search
    // results. Stop instead: pages whose only prose is inside the toggle get no
    // description and fall back to the locale default.
    if (/^<details\b/i.test(trimmed)) break

    const isContent =
      trimmed !== '' &&
      !trimmed.startsWith('#') && // headings
      !trimmed.startsWith('>') && // blockquotes (doc header metadata)
      !trimmed.startsWith('|') && // tables
      !/^([-*+]|\d+\.)\s/.test(trimmed) && // list items
      !/^!\[[^\]]*\]\([^)]*\)$/.test(trimmed) && // standalone images
      !trimmed.startsWith('<') && // HTML blocks (details/summary toggles etc.)
      !/^(-{3,}|_{3,}|\*{3,})$/.test(trimmed) // horizontal rules

    if (isContent) {
      paragraph.push(trimmed)
    } else if (paragraph.length) {
      break // paragraph ended
    }
  }

  const text = stripInlineMarkdown(paragraph.join(' '))
  return text ? truncateAtBoundary(text) : undefined
}

function cleanUrlPath(relativePath) {
  return relativePath.replace(/\.md$/, '').replace(/(^|\/)index$/, '$1')
}

// hreflang alternates for a rendered page (rewritten relativePath, e.g.
// "ko/networking/index.md"). Emitted only when the counterpart source file
// exists on disk — per-locale builds exclude the other locale from the page
// list, so existence is checked against the source tree, where a rendered
// ".../index.md" is a ".../README.md" on disk.
export function localeAlternates(relativePath, { fileExists = defaultFileExists } = {}) {
  const [locale, ...rest] = relativePath.split('/')
  if (!supportedLocales.includes(locale) || rest.length === 0) return []

  const pagePath = rest.join('/')
  const sourcePath = pagePath.replace(/(^|\/)index\.md$/, '$1README.md')

  const otherLocale = supportedLocales.find((l) => l !== locale)
  if (!fileExists(`${otherLocale}/${sourcePath}`)) return []

  const urlFor = (l) => `${siteHostname}${cleanUrlPath(`${l}/${pagePath}`)}`
  const koFirst = ['ko', 'en'].filter((l) => l === locale || l === otherLocale)

  return [
    ...koFirst.map((l) => ({ hreflang: l, href: urlFor(l) })),
    { hreflang: 'x-default', href: urlFor('ko') }
  ]
}

function defaultFileExists(relativeSourcePath) {
  return fs.existsSync(path.join(projectRoot, relativeSourcePath))
}

export const siteName = 'Cloud Native Operations'
export const ogImageUrl = `${siteHostname}og-cover.png`

// Self-referencing canonical. The same pages are also published on GitBook, so
// without this the two copies compete as duplicates for the same queries.
export function canonicalUrl(relativePath) {
  return `${siteHostname}${cleanUrlPath(relativePath)}`
}

const KO_DATE_RE = /^>\s*\*\*마지막 업데이트\*\*\s*:\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/m
const EN_DATE_RE = /^>\s*\*\*(?:Supported Versions|Last Updated)\*\*\s*:\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})/m
const EN_MONTHS = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december'
]

function isoDate(year, month, day) {
  if (month < 1 || month > 12 || day < 1 || day > 31) return undefined
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

// The document header carries the human-readable update date in one of two
// locale formats; sitemap lastmod needs it as ISO 8601.
export function extractLastUpdated(source) {
  const ko = source.match(KO_DATE_RE)
  if (ko) return isoDate(Number(ko[1]), Number(ko[2]), Number(ko[3]))

  const en = source.match(EN_DATE_RE)
  if (!en) return undefined
  const month = EN_MONTHS.indexOf(en[1].toLowerCase()) + 1
  if (month === 0) return undefined
  return isoDate(Number(en[3]), month, Number(en[2]))
}

// Open Graph + Twitter card tags. Link previews in Slack, X, and LinkedIn are a
// real share-to-click path for these pages, and neither was emitted before.
export function socialHeadTags({ title, description, url, locale }) {
  const tags = [
    ['meta', { property: 'og:type', content: 'article' }],
    ['meta', { property: 'og:site_name', content: siteName }],
    ['meta', { property: 'og:title', content: title }],
    ['meta', { property: 'og:url', content: url }],
    ['meta', { property: 'og:image', content: ogImageUrl }],
    ['meta', { property: 'og:locale', content: locale === 'en' ? 'en_US' : 'ko_KR' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: title }],
    ['meta', { name: 'twitter:image', content: ogImageUrl }]
  ]
  if (description) {
    tags.push(['meta', { property: 'og:description', content: description }])
    tags.push(['meta', { name: 'twitter:description', content: description }])
  }
  return tags
}

// Directory names are the only breadcrumb label source, and most of this tree
// is named after acronyms and products that read wrong when naively capitalized.
const SEGMENT_LABELS = {
  'ai-ml': 'AI/ML',
  'container-registry': 'Container Registry',
  'data-on-eks': 'Data on EKS',
  eks: 'EKS',
  'eks-auto-mode': 'EKS Auto Mode',
  'eks-hybrid-nodes': 'EKS Hybrid Nodes',
  gitops: 'GitOps',
  argocd: 'Argo CD',
  'service-mesh': 'Service Mesh',
  istio: 'Istio',
  linkerd: 'Linkerd',
  'cilium-service-mesh': 'Cilium Service Mesh',
  cilium: 'Cilium',
  calico: 'Calico',
  grafana: 'Grafana',
  'platform-engineering': 'Platform Engineering',
  ops: 'Ops',
  labs: 'Labs',
  quizzes: 'Quizzes'
}

function titleCase(segment) {
  const known = SEGMENT_LABELS[segment]
  if (known) return known
  return segment
    .replace(/^\d+-/, '')
    .split('-')
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(' ')
}

// Breadcrumb trail from the rendered path, e.g. "ko/eks/03-eks-networking-part1.md"
// → site root, "eks", page. Directory names are the only label source available.
export function breadcrumbTrail(relativePath, pageTitle) {
  const [locale, ...rest] = relativePath.split('/')
  if (!supportedLocales.includes(locale) || rest.length === 0) return []

  // A section index page *is* its last directory, so that directory must not
  // appear both as a crumb and as the page itself.
  const isIndex = rest[rest.length - 1] === 'index.md'
  if (isIndex && rest.length === 1) return []

  const crumbs = [{ name: siteName, url: `${siteHostname}${locale}/` }]
  const directories = isIndex ? rest.slice(0, -2) : rest.slice(0, -1)
  let walked = `${locale}`
  for (const directory of directories) {
    walked += `/${directory}`
    crumbs.push({ name: titleCase(directory), url: `${siteHostname}${walked}/` })
  }
  if (pageTitle) {
    crumbs.push({ name: pageTitle, url: `${siteHostname}${cleanUrlPath(relativePath)}` })
  }
  return crumbs
}

// TechArticle + BreadcrumbList, so search engines can read what the page is and
// where it sits instead of inferring both from the URL.
export function structuredData({ title, description, url, locale, lastUpdated, crumbs }) {
  const graph = [
    {
      '@type': 'TechArticle',
      headline: title,
      ...(description ? { description } : {}),
      inLanguage: locale === 'en' ? 'en-US' : 'ko-KR',
      mainEntityOfPage: { '@type': 'WebPage', '@id': url },
      ...(lastUpdated ? { dateModified: lastUpdated } : {}),
      isPartOf: { '@type': 'WebSite', name: siteName, url: siteHostname }
    }
  ]
  if (crumbs && crumbs.length > 1) {
    graph.push({
      '@type': 'BreadcrumbList',
      itemListElement: crumbs.map((crumb, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: crumb.name,
        item: crumb.url
      }))
    })
  }
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': graph })
}
