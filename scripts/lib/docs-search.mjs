import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import MiniSearch from 'minisearch'
import * as z from 'zod/v4'
import { supportedLocales } from '../../.vitepress/site-scope.mjs'
import { absolutizeLinks, buildDocuments, parseSummary } from '../generate-llms-txt.mjs'

const projectRoot = fileURLToPath(new URL('../../', import.meta.url))

export const searchInput = {
  query: z.string().trim().min(1).max(300).describe('Keywords, e.g. "gp3 throughput" or "스토리지 gp3". Use focused terms, not a whole question.'),
  locale: z.enum(['ko', 'en', 'all']).default('ko'),
  section: z.string().regex(/^[a-z0-9-]+$/).max(80).optional().describe('Optional top-level directory, e.g. storage, networking, eks.'),
  limit: z.number().int().min(1).max(20).default(8)
}
export const fetchInput = {
  id: z.string().min(1).max(400).describe('Exact document ID returned by search, including locale and .md suffix.'),
  offset: z.number().int().min(0).default(0).describe('Character offset; use the previous response nextOffset to continue.'),
  maxLength: z.number().int().min(100).max(50000).default(12000)
}
const searchSchema = z.object(searchInput)
const fetchSchema = z.object(fetchInput)

export function loadDocuments(root = projectRoot) {
  return supportedLocales.flatMap(locale => {
    const groups = parseSummary(fs.readFileSync(path.join(root, locale, 'SUMMARY.md'), 'utf8'))
    return buildDocuments(locale, groups, mdPath => {
      const file = path.join(root, locale, mdPath)
      if (!fs.existsSync(file)) return null
      return absolutizeLinks(fs.readFileSync(file, 'utf8'), locale, mdPath)
    })
  })
}

function tokenize(text) {
  return text.normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? []
}

// JSON allows escaped lone surrogates, but clients cannot round-trip them
// through UTF-8. Keep both excerpts and page boundaries at whole code points.
function splitsSurrogatePair(text, offset) {
  const before = text.charCodeAt(offset - 1)
  const after = text.charCodeAt(offset)
  return before >= 0xd800 && before <= 0xdbff && after >= 0xdc00 && after <= 0xdfff
}

function snippet(content, query) {
  const lower = content.toLowerCase()
  const positions = tokenize(query).map(term => lower.indexOf(term)).filter(index => index >= 0)
  let start = Math.max(0, (positions.length ? Math.min(...positions) : 0) - 100)
  if (splitsSurrogatePair(content, start)) start -= 1
  let end = Math.min(start + 600, content.length)
  if (splitsSurrogatePair(content, end)) end -= 1
  return `${start ? '…' : ''}${content.slice(start, end).trim()}${content.length > end ? '…' : ''}`
}

export function createDocsSearch(documents) {
  const byId = new Map(documents.map(document => [document.id, document]))
  const index = new MiniSearch({
    fields: ['title', 'description', 'headings', 'content'],
    tokenize,
    searchOptions: {
      boost: { title: 5, description: 2, headings: 3 },
      prefix: true,
      combineWith: 'AND'
    }
  })
  index.addAll(documents.map(doc => ({ ...doc, headings: doc.headings.join('\n') })))

  return {
    search(input) {
      const { query, locale, section, limit } = searchSchema.parse(input)
      const matches = index.search(query, {
        filter: ({ id }) => {
          const doc = byId.get(id)
          return (locale === 'all' || doc.locale === locale) && (!section || doc.section === section)
        }
      })
      return {
        query,
        total: matches.length,
        results: matches.slice(0, limit).map(({ id }) => {
          const { content, headings, ...metadata } = byId.get(id)
          return { ...metadata, snippet: snippet(content, query) }
        })
      }
    },
    fetch(input) {
      const { id, offset, maxLength } = fetchSchema.parse(input)
      const doc = byId.get(id)
      if (!doc) throw new Error('Unknown document ID. Use an ID returned by search.')
      if (offset > doc.content.length) throw new Error('offset exceeds document length.')
      if (splitsSurrogatePair(doc.content, offset)) throw new Error('offset splits a Unicode character. Use nextOffset from the previous response.')
      let end = Math.min(offset + maxLength, doc.content.length)
      if (splitsSurrogatePair(doc.content, end)) end -= 1
      const { content, ...metadata } = doc
      return {
        ...metadata,
        text: content.slice(offset, end),
        offset,
        nextOffset: end < content.length ? end : null,
        totalChars: content.length
      }
    }
  }
}
