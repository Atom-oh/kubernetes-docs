// Builds the chunk index used by the docs Q&A API (infra/ask-docs).
// Output: build/ask-index/chunks.json.gz. Upload with `aws s3 cp` to s3://<bucket>/index/chunks.json.gz.
import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SITE = 'https://docs.atomai.click/kubernetes-docs'
const LOCALES = ['ko', 'en']
const EXCLUDE = [/^quizzes\//, /\/quizzes\//, /^news\//, /^SUMMARY\.md$/, /^README\.md$/]
const MAX_CHUNK_CHARS = 2400

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
  const pageTitle = (raw.match(/^#\s+(.+)$/m)?.[1] ?? relPath).trim()
  const url = `${SITE}/${locale}/${relPath.replace(/\.md$/, '')}`
  const sections = []
  let current = { heading: pageTitle, lines: [] }
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
        title: pageTitle,
        heading: sec.heading,
        url: sec.heading === pageTitle ? url : `${url}#${slug(sec.heading)}`,
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
for (const locale of LOCALES) {
  const dir = path.join(root, locale)
  for (const rel of await walk(dir)) {
    if (EXCLUDE.some((re) => re.test(rel))) continue
    all.push(...chunkFile(locale, rel, await readFile(path.join(dir, rel), 'utf8')))
  }
}

const outDir = path.join(root, 'build', 'ask-index')
await mkdir(outDir, { recursive: true })
const payload = { generatedAt: new Date().toISOString(), count: all.length, chunks: all }
const gz = gzipSync(Buffer.from(JSON.stringify(payload)))
await writeFile(path.join(outDir, 'chunks.json.gz'), gz)
console.log(`chunks: ${all.length} (${LOCALES.map((l) => `${l}=${all.filter((c) => c.locale === l).length}`).join(', ')}), gz ${gz.length} bytes`)
