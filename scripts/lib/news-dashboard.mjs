export const NEWS_TOPICS = [
  'kubernetes', 'eks', 'networking', 'mesh', 'gitops',
  'autoscaling', 'observability', 'security', 'ai', 'ecosystem'
]

export const NEWS_CATEGORIES = [
  'security', 'breaking', 'release', 'preview', 'feature', 'community', 'guide'
]

export function isoWeek(dateString) {
  const date = new Date(`${dateString}T00:00:00Z`)
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== dateString) {
    throw new Error(`Invalid news date: ${dateString}`)
  }
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7))
  const year = date.getUTCFullYear()
  const week = Math.ceil(((date - new Date(Date.UTC(year, 0, 1))) / 86400000 + 1) / 7)
  return `${year}-W${String(week).padStart(2, '0')}`
}

export function weekStart(week) {
  const match = /^(\d{4})-W(\d{2})$/.exec(week)
  if (!match || Number(match[2]) < 1 || Number(match[2]) > 53) {
    throw new Error(`Invalid news week: ${week}`)
  }
  const date = new Date(Date.UTC(Number(match[1]), 0, 4))
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() || 7) - 1) + (Number(match[2]) - 1) * 7)
  if (isoWeek(date.toISOString().slice(0, 10)) !== week) {
    throw new Error(`Invalid news week: ${week}`)
  }
  return date
}

export function recentWeeks(latestWeek, count = 8) {
  if (!latestWeek) return []
  const start = weekStart(latestWeek)
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(start)
    date.setUTCDate(date.getUTCDate() - (count - index - 1) * 7)
    return isoWeek(date.toISOString().slice(0, 10))
  })
}

export function newsWeeks(entries) {
  return [...new Set(entries.map(entry => entry.week))].sort().reverse()
}

export function filterNews(entries, { topic = '', category = '', week = '', query = '' } = {}) {
  const words = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean)
  return entries.filter(entry => {
    if (topic && entry.topic !== topic) return false
    if (category && entry.category !== category) return false
    if (week && entry.week !== week) return false
    const text = `${entry.summary} ${entry.documents.join(' ')} ${entry.sources.join(' ')} ${entry.period}`.toLocaleLowerCase()
    return words.every(word => text.includes(word))
  })
}

export function newsStats(entries) {
  return {
    records: entries.length,
    security: entries.filter(entry => entry.category === 'security').length,
    documents: new Set(entries.flatMap(entry => entry.documents)).size,
    unmatched: entries.filter(entry => entry.documents.length === 0).length
  }
}

export function heatmapCount(entries, topic, week) {
  return entries.filter(entry => entry.topic === topic && entry.week === week).length
}

export function newsDocumentUrl(base, locale, document) {
  const clean = document.replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')
  return `${base}${locale}/${clean}`
}
