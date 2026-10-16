import { createHash } from 'node:crypto'
import { isoWeek, weekStart } from './news-dashboard.mjs'

const LINK = /\[([^\]]*)\]\(([^)\s]+)\)/g
const TOPIC_BY_DIRECTORY = {
  core: 'kubernetes', basics: 'kubernetes', kernel: 'kubernetes',
  eks: 'eks', 'eks-auto-mode': 'eks', 'eks-hybrid-nodes': 'eks',
  networking: 'networking', 'service-mesh': 'mesh', gitops: 'gitops',
  autoscaling: 'autoscaling', scheduling: 'autoscaling',
  observability: 'observability', security: 'security',
  'ai-ml': 'ai', 'data-on-eks': 'ai'
}

function plainText(value) {
  return value.replace(LINK, '$1').replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1').trim()
}

function topicFor(entry) {
  const directory = entry.documents[0]?.split('/')[0]
  if (TOPIC_BY_DIRECTORY[directory]) return TOPIC_BY_DIRECTORY[directory]
  const text = entry.summary.toLowerCase()
  if (/amazon eks|eks auto|emr on eks/.test(text)) return 'eks'
  if (/cve-\d|security|vulnerab|path traversal/.test(text)) return 'security'
  if (/\bgpu\b|\bai\b|\bllm\b|\bvllm\b|kubeflow|inference|opencost|hami/.test(text)) return 'ai'
  if (/gateway api|cilium|calico|\bdns\b|k8gb/.test(text)) return 'networking'
  if (/istio|linkerd|service mesh/.test(text)) return 'mesh'
  if (/argo\s?cd|gitops/.test(text)) return 'gitops'
  if (/karpenter|autoscal|\bkeda\b/.test(text)) return 'autoscaling'
  if (/opentelemetry|prometheus|grafana|cloudwatch/.test(text)) return 'observability'
  if (/kubernetes|etcd/.test(text)) return 'kubernetes'
  return 'ecosystem'
}

function categoryFor(entry) {
  const text = entry.summary.toLowerCase()
  if (/cve-\d|security patch|security release|istio-security|vulnerab|path traversal/.test(text)) return 'security'
  if (/breaking|retirement|retired|end of (?:life|support)|deprecat|eliminated/.test(text)) return 'breaking'
  if (/-rc\.\d|-beta\.\d|-alpha\.\d|edge-\d|release candidate|beta phase|rc phase|code freeze|sneak peek/.test(text)) return 'preview'
  if (/release|patch|\bga\b/.test(text)) return 'release'
  if (/graduat|incubat|kubecon|argocon|schedule announced/.test(text)) return 'community'
  if (/blog|guide|white paper|whitepaper/.test(text)) return 'guide'
  return 'feature'
}

export function parseNewsLog(markdown, locale) {
  const entries = []
  let inLog = false
  for (const line of markdown.split('\n')) {
    if (/^## (?:갱신 로그|Update Log)\s*$/.test(line)) {
      inLog = true
      continue
    }
    if (inLog && /^## /.test(line)) break
    if (!inLog || !/^\s*-\s+\d{4}/.test(line)) continue
    const match = /^- (\d{4}-(?:W\d{2}|\d{2}-\d{2})): (.+?) — (.+)$/.exec(line)
    if (!match) throw new Error(`${locale}: malformed news log entry: ${line}`)
    const [, period, target, body] = match
    const week = period.includes('-W') ? (weekStart(period), period) : isoWeek(period)
    const documents = []
    const sources = []
    for (const [, , url] of `${target} ${body}`.matchAll(LINK)) {
      if (url.startsWith('../')) {
        const document = url.slice(3)
        if (!/^[a-zA-Z0-9][a-zA-Z0-9/_-]*\.md$/.test(document)) {
          throw new Error(`${locale}: invalid news document path: ${url}`)
        }
        documents.push(document)
      } else {
        let parsed
        try { parsed = new URL(url) } catch { /* handled below */ }
        if (!parsed || !['https:', 'http:'].includes(parsed.protocol) || parsed.username || parsed.password) {
          throw new Error(`${locale}: invalid news source URL: ${url}`)
        }
        sources.push(url)
      }
    }
    if (!documents.length && !sources.length) {
      throw new Error(`${locale}: news entry needs a document or source link: ${line}`)
    }
    const summary = plainText(body
      .replace(/\s*[（(]\[(?:원문|source)\]\([^)]+\)[)）]/gi, '')
      .replace(/\s*[·|]\s*\[(?:원문|source)\]\([^)]+\)/gi, ''))
    if (!summary) throw new Error(`${locale}: empty news summary: ${line}`)
    const title = summary.split(/\s*[（(]/)[0]
      .replace(/^applied (?:the )?/i, '').replace(/\s+반영$/, '').trim()
    entries.push({
      period, week, documents: [...new Set(documents)].sort(),
      sources: [...new Set(sources)].sort(), title, summary
    })
  }
  if (!entries.length) throw new Error(`${locale}: news log is empty or missing`)
  return entries
}

function entryKey(entry) {
  return JSON.stringify([entry.period, entry.documents, entry.sources])
}

export function buildNewsData(korean, english, { requireSourcesWeek } = {}) {
  if (requireSourcesWeek) weekStart(requireSourcesWeek)
  const ko = parseNewsLog(korean, 'ko')
  const en = parseNewsLog(english, 'en')
  const englishByKey = new Map()
  for (const entry of en) {
    const key = entryKey(entry)
    const items = englishByKey.get(key) ?? []
    items.push(entry)
    englishByKey.set(key, items)
  }
  const occurrences = new Map()
  const currentWeekSources = new Set()
  const pairs = ko.map(entry => {
    const key = entryKey(entry)
    const translated = englishByKey.get(key)?.shift()
    if (!translated) throw new Error(`Missing English news counterpart: ${entry.period} ${entry.documents.join(', ')}`)
    const occurrence = occurrences.get(key) ?? 0
    occurrences.set(key, occurrence + 1)
    const id = createHash('sha256').update(`${key}:${occurrence}`).digest('hex').slice(0, 16)
    const topic = topicFor(translated)
    const category = categoryFor(translated)
    if (entry.week === requireSourcesWeek && !entry.sources.length) {
      throw new Error(`News for ${requireSourcesWeek} needs an official source URL: ${entry.title}`)
    }
    if (entry.week === requireSourcesWeek) {
      for (const source of entry.sources) {
        if (currentWeekSources.has(source)) {
          throw new Error(`Duplicate source in ${requireSourcesWeek}; group related documents on one record: ${source}`)
        }
        currentWeekSources.add(source)
      }
    }
    return {
      ko: { id, ...entry, topic, category },
      en: { id, ...translated, topic, category }
    }
  })
  if ([...englishByKey.values()].some(items => items.length)) {
    throw new Error('English news log contains entries missing from Korean')
  }
  pairs.sort((a, b) => b.ko.week.localeCompare(a.ko.week))
  return {
    version: 1,
    locales: {
      ko: { entries: pairs.map(pair => pair.ko) },
      en: { entries: pairs.map(pair => pair.en) }
    }
  }
}
