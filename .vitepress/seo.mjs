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
