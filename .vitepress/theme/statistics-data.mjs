// Shared by the publisher and the browser. Only these aggregate fields may
// enter the public JSON; raw GA responses and credentials never belong here.
export const statisticsSite = Object.freeze({
  host: 'www.atomai.click',
  pathPrefix: '/kubernetes-docs/',
  event: 'docs_page_view'
})

export function calendarDate(date, timeZone) {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(date)
  const get = type => parts.find(part => part.type === type).value
  return `${get('year')}-${get('month')}-${get('day')}`
}

export function offsetDate(value, days) {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function validDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    !Number.isNaN(Date.parse(`${value}T00:00:00Z`)) && offsetDate(value, 0) === value
}

function count(value, nullable) {
  if (nullable && value === null) return null
  if (!Number.isSafeInteger(value) || value < 0) throw new Error('Invalid statistics count')
  return value
}

export function parseStatisticsSnapshot(value) {
  if (value?.schemaVersion !== 1) throw new Error('Unknown statistics format')
  if (value.status === 'unavailable') return { schemaVersion: 1, status: 'unavailable' }
  if (value.status !== 'ready') throw new Error('Unknown statistics status')
  for (const [key, expected] of Object.entries(statisticsSite)) {
    if (value.site?.[key] !== expected) throw new Error('Statistics site mismatch')
  }
  if (typeof value.generatedAt !== 'string' || !Number.isFinite(Date.parse(value.generatedAt))) {
    throw new Error('Invalid statistics timestamp')
  }
  const period = value.period
  if (!validDate(period?.start) || !validDate(period?.end) ||
      period.days !== 30 || offsetDate(period.start, 29) !== period.end ||
      typeof period.timeZone !== 'string') {
    throw new Error('Invalid statistics period')
  }
  // Validate the IANA time zone and the closed reporting window. An older
  // snapshot keeps its original period rather than claiming today's dates.
  const generatedDate = calendarDate(new Date(value.generatedAt), period.timeZone)
  if (period.end !== offsetDate(generatedDate, -1)) throw new Error('Statistics timestamp/period mismatch')
  const quality = {}
  for (const key of ['thresholded', 'sampled', 'dataLoss']) {
    if (typeof value.quality?.[key] !== 'boolean') throw new Error('Invalid statistics quality')
    quality[key] = value.quality[key]
  }
  const limited = Object.values(quality).some(Boolean)
  if (!Array.isArray(value.daily) || value.daily.length !== 30) {
    throw new Error('Incomplete statistics days')
  }
  return {
    schemaVersion: 1, status: 'ready',
    site: { ...statisticsSite },
    generatedAt: new Date(value.generatedAt).toISOString(),
    period: { start: period.start, end: period.end, days: 30, timeZone: period.timeZone },
    totals: {
      visitors: count(value.totals?.visitors, limited),
      views: count(value.totals?.views, limited)
    },
    daily: value.daily.map((row, index) => {
      if (row.date !== offsetDate(period.start, index)) throw new Error('Invalid statistics day')
      return { date: row.date, visitors: count(row.visitors, limited), views: count(row.views, limited) }
    }),
    quality
  }
}

export function createStatisticsLoader({
  getUrl, onSnapshot, onError, fetchImpl = fetch, timeoutMs = 10000
}) {
  let request
  return function load() {
    if (request) return request
    onError(false)
    // Assign the Promise before any request work runs. A synchronous exception
    // must not have its request reset overwritten by the outer assignment.
    request = Promise.resolve().then(async () => {
      let timer
      try {
        const controller = new AbortController()
        timer = setTimeout(() => controller.abort(), timeoutMs)
        const response = await fetchImpl(getUrl(), {
          cache: 'no-cache', signal: controller.signal
        })
        if (!response.ok) throw new Error('Statistics unavailable')
        onSnapshot(parseStatisticsSnapshot(await response.json()))
      } catch {
        request = undefined
        onError(true)
      } finally {
        clearTimeout(timer)
      }
    })
    return request
  }
}
