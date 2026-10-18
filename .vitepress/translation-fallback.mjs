import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { translatedLocales } from './site-scope.mjs'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const BASE = '/kubernetes-docs/'

// cn/jp/es translate only part of en, so their pages link to pages that do
// not exist in that locale yet. Such a link would fail the dead-link check and
// 404 for readers. Point it at the English page instead.
//
// Returns the English URL for a link on a translated page whose target is
// missing in that locale but exists in en, or undefined to leave the link
// alone. A link missing in en too stays as it is, so VitePress still reports
// it as dead. The hash is dropped: translated headings have other anchors.
export function translationFallbackHref(pagePath, href, { fileExists = defaultFileExists } = {}) {
  const locale = pagePath.split('/')[0]
  if (!translatedLocales.includes(locale) || !href) return undefined
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('//') || href.startsWith('#')) return undefined

  const target = href.replace(/[?#].*$/, '')
  if (!target.endsWith('.md') && !target.endsWith('/')) return undefined
  const sourceFile = target.endsWith('/') ? `${target}README.md` : target
  const resolved = sourceFile.startsWith('/')
    ? path.posix.normalize(sourceFile.slice(1))
    : path.posix.normalize(path.posix.join(path.posix.dirname(pagePath), sourceFile))
  if (!resolved.startsWith(`${locale}/`) || fileExists(resolved)) return undefined

  const english = `en/${resolved.slice(locale.length + 1)}`
  if (!fileExists(english)) return undefined
  return BASE + english.replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')
}

function defaultFileExists(relativeSourcePath) {
  return fs.existsSync(path.join(projectRoot, relativeSourcePath))
}

// markdown-it core rule. Runs before the README→index href rewrite, so links
// still carry their source file names. target="_self" makes VitePress skip the
// link in its dead-link check and router: the English page belongs to another
// locale build, so it needs a full page load, not client-side navigation.
export function translationFallbackLinks(md) {
  md.core.ruler.push('translation_fallback_links', (state) => {
    const pagePath = state.env?.relativePath
    if (!pagePath) return
    for (const blockToken of state.tokens) {
      if (blockToken.type !== 'inline' || !blockToken.children) continue
      for (const token of blockToken.children) {
        if (token.type !== 'link_open') continue
        const fallback = translationFallbackHref(pagePath, token.attrGet('href'))
        if (!fallback) continue
        token.attrSet('href', fallback)
        token.attrSet('target', '_self')
      }
    }
  })
}
