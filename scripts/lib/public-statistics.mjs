import {
  calendarDate, offsetDate, parseStatisticsSnapshot, statisticsSite
} from '../../.vitepress/theme/statistics-data.mjs'

const SNAPSHOT_URL = 'https://www.atomai.click/kubernetes-docs/site-statistics.json'
const METRICS = ['totalUsers', 'eventCount']

export function buildReportRequest() {
  const filter = (fieldName, matchType, value, caseSensitive = true) => ({
    filter: { fieldName, stringFilter: { matchType, value, caseSensitive } }
  })
  const common = {
    dateRanges: [{ startDate: '30daysAgo', endDate: 'yesterday' }],
    metrics: METRICS.map(name => ({ name })),
    dimensionFilter: {
      andGroup: {
        expressions: [
          filter('hostName', 'EXACT', statisticsSite.host, false),
          filter('pagePath', 'BEGINS_WITH', statisticsSite.pathPrefix),
          filter('eventName', 'EXACT', statisticsSite.event)
        ]
      }
    },
    limit: '100'
  }
  return {
    requests: [
      { ...common, dimensions: [] },
      { ...common, dimensions: [{ name: 'date' }], orderBys: [{ dimension: { dimensionName: 'date' } }] }
    ]
  }
}

function integer(value) {
  if (typeof value !== 'string' || !/^\d+$/.test(value) || !Number.isSafeInteger(Number(value))) {
    throw new Error('Invalid GA4 count')
  }
  return Number(value)
}

function metrics(row) {
  if (row.metricValues?.length !== 2) throw new Error('Incomplete GA4 metrics')
  return { visitors: integer(row.metricValues[0].value), views: integer(row.metricValues[1].value) }
}

export function buildSnapshot(data, startedAt, finishedAt) {
  if (!Array.isArray(data?.reports) || data.reports.length !== 2) throw new Error('Incomplete GA4 reports')
  const [total, daily] = data.reports
  const timeZone = total.metadata?.timeZone
  if (typeof timeZone !== 'string' || daily.metadata?.timeZone !== timeZone) {
    throw new Error('Missing or inconsistent GA4 time zone')
  }
  const today = calendarDate(startedAt, timeZone)
  if (today !== calendarDate(finishedAt, timeZone)) {
    throw new Error('GA4 request crossed property midnight; retry the refresh')
  }
  for (const report of data.reports) {
    if (report.metadata?.emptyReason) throw new Error('GA4 report unavailable')
    if (JSON.stringify(report.metricHeaders?.map(h => h.name)) !== JSON.stringify(METRICS)) {
      throw new Error('Unexpected GA4 metrics')
    }
    if ((report.rowCount ?? 0) !== (report.rows?.length ?? 0)) throw new Error('Truncated GA4 report')
  }
  if ((total.rows?.length ?? 0) > 1 ||
      JSON.stringify(daily.dimensionHeaders?.map(h => h.name)) !== '["date"]') {
    throw new Error('Unexpected GA4 dimensions')
  }
  const quality = {
    thresholded: data.reports.some(r => r.metadata?.subjectToThresholding === true),
    sampled: data.reports.some(r => r.metadata?.samplingMetadatas?.length > 0),
    dataLoss: data.reports.some(r => r.metadata?.dataLossFromOtherRow === true)
  }
  const limited = Object.values(quality).some(Boolean)
  const missing = { visitors: limited ? null : 0, views: limited ? null : 0 }
  const start = offsetDate(today, -30)
  const end = offsetDate(today, -1)
  const days = new Map()
  for (const row of daily.rows ?? []) {
    const raw = row.dimensionValues?.[0]?.value
    if (row.dimensionValues?.length !== 1 || !/^\d{8}$/.test(raw)) throw new Error('Invalid GA4 date')
    const date = `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6)}`
    if (date < start || date > end || offsetDate(date, 0) !== date || days.has(date)) {
      throw new Error('Invalid or duplicate GA4 date')
    }
    days.set(date, metrics(row))
  }
  return parseStatisticsSnapshot({
    schemaVersion: 1, status: 'ready', site: statisticsSite,
    generatedAt: finishedAt.toISOString(),
    period: { start, end, days: 30, timeZone },
    totals: total.rows?.[0] ? metrics(total.rows[0]) : { ...missing },
    daily: Array.from({ length: 30 }, (_, index) => {
      const date = offsetDate(start, index)
      return { date, ...(days.get(date) ?? missing) }
    }),
    quality
  })
}

async function json(fetchImpl, url, options = {}) {
  const response = await fetchImpl(url, { ...options, signal: AbortSignal.timeout(20000), redirect: 'error' })
  // Do not log the response body: it can contain property or account details.
  if (!response.ok) throw new Error(`Statistics HTTP ${response.status}`)
  return response.json()
}

export async function refreshStatistics({
  propertyId, accessToken, fetchImpl = fetch, now = () => new Date()
} = {}) {
  if (/^\d+$/.test(propertyId ?? '') && accessToken) {
    try {
      const startedAt = now()
      const data = await json(fetchImpl,
        `https://analyticsdata.googleapis.com/v1beta/properties/${propertyId}:batchRunReports`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(buildReportRequest())
        })
      return { source: 'ga4', snapshot: buildSnapshot(data, startedAt, now()) }
    } catch {
      // A temporary reporting/authentication failure must not erase the last
      // published counts or block a documentation deployment.
    }
  }
  try {
    const snapshot = parseStatisticsSnapshot(await json(fetchImpl, SNAPSHOT_URL))
    if (snapshot.status === 'ready') {
      if (Date.parse(snapshot.generatedAt) > now().getTime() + 300000) {
        throw new Error('Future statistics timestamp')
      }
      return { source: 'previous', snapshot }
    }
  } catch {
    // First deployment, invalid data, or a network failure: show no numbers.
  }
  return { source: 'unavailable', snapshot: { schemaVersion: 1, status: 'unavailable' } }
}
