#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createMarkdownRenderer, resolveConfig } from 'vitepress'
import { resolveLocalTarget } from './validate-local-links.mjs'

function markdownFiles(directory) {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(directory, entry.name)
    return entry.isDirectory() ? markdownFiles(file) :
      entry.isFile() && entry.name.endsWith('.md') ? [file] : []
  }).sort()
}

function walkTokens(tokens, visit) {
  for (const token of tokens) {
    visit(token)
    if (token.children) walkTokens(token.children, visit)
  }
}

export function documentAnchors(markdown, renderer, relativePath) {
  const tokens = renderer.parse(markdown, { relativePath })
  const headings = [], htmlIds = new Set(), links = []
  walkTokens(tokens, token => {
    if (token.type === 'heading_open') {
      headings.push({ id: token.attrGet('id'), level: token.tag, line: token.map[0] })
    }
    // The renderer adds a permalink for every heading. Only authored links
    // require canonical IDs; counting generated permalinks would touch all titles.
    if (token.type === 'link_open' && !token.attrGet('class')?.split(/\s+/).includes('header-anchor')) {
      links.push(token.attrGet('href'))
    }
    if (token.type === 'html_block' || token.type === 'html_inline') {
      for (const match of token.content.replace(/<!--[\s\S]*?-->/g, '')
        .matchAll(/<[a-z][^>]*\bid\s*=\s*(?:"([^"]+)"|'([^']+)')/gi)) {
        htmlIds.add(match[1] ?? match[2])
      }
      for (const match of token.content.replace(/<!--[\s\S]*?-->/g, '')
        .matchAll(/<a\b[^>]*\bhref\s*=\s*(?:"([^"]+)"|'([^']+)')/gi)) {
        links.push(match[1] ?? match[2])
      }
    }
  })
  return { headings, htmlIds, links }
}

function decoded(value) {
  try { return decodeURIComponent(value) } catch { return value }
}

function fragmentTarget(root, source, href, sources) {
  if (!href?.includes('#')) return null
  const fragment = decoded(href.slice(href.indexOf('#') + 1))
  if (!fragment) return null
  const target = href.slice(0, href.indexOf('#'))
  if (!target || target.startsWith('?')) return { file: source, fragment }
  const repositoryMain = /^https:\/\/(?:github\.com\/Atom-oh\/kubernetes-docs\/blob\/main\/|raw\.githubusercontent\.com\/Atom-oh\/kubernetes-docs\/main\/)/i
  if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(target) && !repositoryMain.test(target)) return null
  const candidates = resolveLocalTarget(source, target.replace(/\.html(?=\?|$)/, '.md'), root)
  // VitePress rewrites README.md links to index.md before exposing tokens.
  const file = candidates.flatMap(candidate => [candidate, candidate.replace(/[/\\]index\.md$/, '/README.md')])
    .find(candidate => sources.has(candidate))
  return file ? { file, fragment } : null
}

export function canonicalAnchorRequirements(root, renderer) {
  const documents = new Map(markdownFiles(path.join(root, 'en')).map(file => {
    const markdown = fs.readFileSync(file, 'utf8')
    return [file, documentAnchors(markdown, renderer, path.relative(root, file))]
  }))
  const required = new Map(), unresolvedSource = []
  for (const [source, document] of documents) {
    for (const href of document.links) {
      const target = fragmentTarget(root, source, href, documents)
      if (!target) continue
      const targetDocument = documents.get(target.file)
      const heading = targetDocument.headings.find(item => item.id === target.fragment) ??
        targetDocument.headings.find(item => item.id.normalize('NFC') === target.fragment.normalize('NFC'))
      if (heading) {
        if (!required.has(target.file)) required.set(target.file, new Set())
        required.get(target.file).add(heading.id)
      } else if (targetDocument.htmlIds.has(target.fragment)) {
        if (!required.has(target.file)) required.set(target.file, new Set())
        required.get(target.file).add(target.fragment)
      } else {
        unresolvedSource.push({ source: path.relative(root, source), href, target: path.relative(root, target.file) })
      }
    }
    // Explicit IDs are part of the source contract even without an inbound link.
    const lines = fs.readFileSync(source, 'utf8').split('\n')
    for (const heading of document.headings) {
      if (/\{#[^{}\s]+\}/.test(lines[heading.line])) {
        if (!required.has(source)) required.set(source, new Set())
        required.get(source).add(heading.id)
      }
    }
    for (const id of document.htmlIds) {
      if (!required.has(source)) required.set(source, new Set())
      required.get(source).add(id)
    }
  }
  return { documents, required, unresolvedSource }
}

export function repairTranslatedAnchors(sourceDocument, requiredIds, markdown, renderer, relativePath) {
  const targetDocument = documentAnchors(markdown, renderer, relativePath)
  if (sourceDocument.headings.length !== targetDocument.headings.length ||
      sourceDocument.headings.some((heading, index) => heading.level !== targetDocument.headings[index].level)) {
    throw new Error('Heading structure differs from English; translate the complete page first')
  }
  const lines = markdown.split('\n')
  let added = 0
  sourceDocument.headings.forEach((sourceHeading, index) => {
    if (!requiredIds.has(sourceHeading.id)) return
    const targetHeading = targetDocument.headings[index]
    if (targetHeading.id === sourceHeading.id || targetDocument.htmlIds.has(sourceHeading.id)) return
    const line = lines[targetHeading.line]
    const explicit = line.match(/\{#([^{}\s]+)\}/)
    if (explicit) throw new Error(`Existing explicit ID ${explicit[1]} differs from ${sourceHeading.id}`)
    if (line.match(/^\s*#{1,6}\s+/)) {
      // A trailing ATX closing sequence is syntax, not part of the title.
      lines[targetHeading.line] = `${line.replace(/\s+#+\s*$/, '').trimEnd()} {#${sourceHeading.id}}`
    } else {
      // Setext headings may have inline formatting or link text on their title line.
      lines[targetHeading.line] = `${line.trimEnd()} {#${sourceHeading.id}}`
    }
    added++
  })
  const repaired = lines.join('\n')
  const after = documentAnchors(repaired, renderer, relativePath)
  const missing = [...requiredIds].filter(id =>
    !after.headings.some(heading => heading.id === id) && !after.htmlIds.has(id))
  if (missing.length) throw new Error(`Unresolved canonical IDs: ${missing.join(', ')}`)
  return { markdown: repaired, added }
}

export async function syncTranslatedAnchors(root, { locales = ['cn', 'jp', 'es'], apply = true, renderer } = {}) {
  if (locales.some(locale => !['cn', 'jp', 'es'].includes(locale))) throw new Error('Invalid translation locale')
  if (!renderer) {
    const config = await resolveConfig(root)
    renderer = await createMarkdownRenderer(root, config.markdown, '/kubernetes-docs/')
  }
  const inventory = canonicalAnchorRequirements(root, renderer)
  const changed = [], failures = []
  for (const locale of locales) {
    for (const [source, required] of inventory.required) {
      const target = path.join(root, locale, path.relative(path.join(root, 'en'), source))
      if (!fs.existsSync(target)) continue // The separate coverage gate handles missing pages.
      const markdown = fs.readFileSync(target, 'utf8')
      try {
        const result = repairTranslatedAnchors(inventory.documents.get(source), required, markdown, renderer,
          path.relative(root, target))
        if (result.markdown === markdown) continue
        if (apply) {
          const temporary = `${target}.anchors-${process.pid}`
          fs.writeFileSync(temporary, result.markdown, { mode: fs.statSync(target).mode })
          fs.renameSync(temporary, target)
        }
        changed.push({ file: path.relative(root, target), added: result.added })
      } catch (error) {
        failures.push({ file: path.relative(root, target), reason: error.message })
      }
    }
  }
  return { changed, failures, unresolvedSource: inventory.unresolvedSource }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), localeIndex = args.indexOf('--locale')
  const result = await syncTranslatedAnchors(process.cwd(), {
    apply: !args.includes('--check'),
    locales: localeIndex < 0 ? undefined : [args[localeIndex + 1]]
  })
  console.log(JSON.stringify(result, null, 2))
  if (result.failures.length || result.unresolvedSource.length ||
      (args.includes('--check') && result.changed.length)) process.exitCode = 1
}
