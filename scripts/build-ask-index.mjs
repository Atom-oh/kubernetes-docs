// Builds the chunk index used by the docs Q&A API (infra/ask-docs).
// Output: build/ask-index/chunks.json.gz. Upload with `aws s3 cp` to s3://<bucket>/index/chunks.json.gz.
import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SITE = 'https://docs.atomai.click/kubernetes-docs'
const LOCALES = ['ko', 'en']
// Machine translations of en. Not indexed: their questions search the English chunks, and the index
// only records which English pages have a translation so answers can link to it.
const TRANSLATED_LOCALES = ['cn', 'jp', 'es']
const EXCLUDE = [/^quizzes\//, /\/quizzes\//, /^news\//, /^SUMMARY\.md$/, /^README\.md$/]
const MAX_CHUNK_CHARS = 2400

// VitePress serves README.md as the directory index (see the rewrites in .vitepress/site-scope.mjs).
function pageUrl(locale, relPath) {
  return `${SITE}/${locale}/${relPath.replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')}`
}

function pageTitle(relPath, raw) {
  return (raw.match(/^#\s+(.+)$/m)?.[1] ?? relPath).trim()
}

async function walk(dir, rel = '') {
  const out = []
  for (const entry of await readdir(path.join(dir, rel), { withFileTypes: true })) {
    const r = path.posix.join(rel, entry.name)
    if (entry.isDirectory()) out.push(...(await walk(dir, r)))
    else if (entry.name.endsWith('.md')) out.push(r)
  }
  return out
}

function stripMarkdown(text) {
  return text
    .replace(/<details>[\s\S]*?<\/details>/g, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function chunkFile(locale, relPath, raw) {
  const title = pageTitle(relPath, raw)
  const url = pageUrl(locale, relPath)
  const sections = []
  let current = { heading: title, lines: [] }
  for (const line of raw.split('\n')) {
    if (/^#{2,3}\s+/.test(line)) {
      sections.push(current)
      current = { heading: line.replace(/^#{2,3}\s+/, '').trim(), lines: [] }
    } else {
      current.lines.push(line)
    }
  }
  sections.push(current)

  const chunks = []
  sections.forEach((sec, i) => {
    const body = stripMarkdown(sec.lines.join('\n'))
    if (!body) return
    for (let start = 0, part = 0; start < body.length; start += MAX_CHUNK_CHARS, part++) {
      chunks.push({
        id: `${locale}/${relPath}#${i}-${part}`,
        locale,
        title,
        heading: sec.heading,
        url: sec.heading === title ? url : `${url}#${slug(sec.heading)}`,
        text: body.slice(start, start + MAX_CHUNK_CHARS),
      })
    }
  })
  return chunks
}

function slug(heading) {
  return heading.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').trim().replace(/\s+/g, '-')
}

const all = []
const pages = {}
for (const locale of LOCALES) {
  const dir = path.join(root, locale)
  pages[locale] = new Set()
  for (const rel of await walk(dir)) {
    if (EXCLUDE.some((re) => re.test(rel))) continue
    pages[locale].add(rel)
    all.push(...chunkFile(locale, rel, await readFile(path.join(dir, rel), 'utf8')))
  }
}

// English page URL -> { cn: { url, title }, ... } for the pages each translation has.
const translations = {}
for (const locale of TRANSLATED_LOCALES) {
  const dir = path.join(root, locale)
  for (const rel of await walk(dir)) {
    if (EXCLUDE.some((re) => re.test(rel)) || !pages.en.has(rel)) continue
    const raw = await readFile(path.join(dir, rel), 'utf8')
    ;(translations[pageUrl('en', rel)] ??= {})[locale] = { url: pageUrl(locale, rel), title: pageTitle(rel, raw) }
  }
}

const outDir = path.join(root, 'build', 'ask-index')
await mkdir(outDir, { recursive: true })
const payload = { generatedAt: new Date().toISOString(), count: all.length, chunks: all, translations }
const gz = gzipSync(Buffer.from(JSON.stringify(payload)))
await writeFile(path.join(outDir, 'chunks.json.gz'), gz)
const translated = TRANSLATED_LOCALES.map((l) => `${l}=${Object.values(translations).filter((t) => t[l]).length}`)
console.log(`chunks: ${all.length} (${LOCALES.map((l) => `${l}=${all.filter((c) => c.locale === l).length}`).join(', ')}), translated pages: ${translated.join(', ')}, gz ${gz.length} bytes`)
