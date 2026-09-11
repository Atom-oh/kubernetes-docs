import assert from 'node:assert/strict'
import test from 'node:test'
import { buildReportRequest, buildSnapshot, refreshStatistics } from '../lib/public-statistics.mjs'
import { createStatisticsLoader, parseStatisticsSnapshot } from '../../.vitepress/theme/statistics-data.mjs'
import { buildDocuments, buildLlmsFull, absolutizeLinks } from '../generate-llms-txt.mjs'

const clock = new Date('2026-09-11T03:00:00.000Z')
const metadata = { timeZone: 'Asia/Seoul' }
const metricHeaders = [{ name: 'totalUsers' }, { name: 'eventCount' }]
const value = (visitors, views) => [{ value: String(visitors) }, { value: String(views) }]
const response = () => ({
  reports: [
    { metricHeaders, metadata, rowCount: 1, rows: [{ metricValues: value(7, 20) }] },
    {
      dimensionHeaders: [{ name: 'date' }], metricHeaders, metadata, rowCount: 2,
      rows: [
        { dimensionValues: [{ value: '20260909' }], metricValues: value(5, 8) },
        { dimensionValues: [{ value: '20260910' }], metricValues: value(6, 12) }
      ]
    }
  ]
})

test('requests only document events on the production host, without personal or query dimensions', () => {
  const request = buildReportRequest()
  for (const report of request.requests) {
    assert.deepEqual(report.dateRanges, [{ startDate: '30daysAgo', endDate: 'yesterday' }])
    assert.deepEqual(report.metrics, [{ name: 'totalUsers' }, { name: 'eventCount' }])
    assert.deepEqual(report.dimensionFilter.andGroup.expressions.map(x => x.filter), [
      { fieldName: 'hostName', stringFilter: { matchType: 'EXACT', value: 'www.atomai.click', caseSensitive: false } },
      { fieldName: 'pagePath', stringFilter: { matchType: 'BEGINS_WITH', value: '/kubernetes-docs/', caseSensitive: true } },
      { fieldName: 'eventName', stringFilter: { matchType: 'EXACT', value: 'docs_page_view', caseSensitive: true } }
    ])
  }
  assert.deepEqual(request.requests[0].dimensions, [])
  assert.deepEqual(request.requests[1].dimensions, [{ name: 'date' }])
})

test('period users come from the aggregate report, not the sum of daily unique users', () => {
  const snapshot = buildSnapshot(response(), clock, clock)
  assert.deepEqual(snapshot.totals, { visitors: 7, views: 20 })
  assert.equal(snapshot.daily.reduce((sum, row) => sum + row.visitors, 0), 11)
  assert.equal(snapshot.period.start, '2026-08-12')
  assert.equal(snapshot.period.end, '2026-09-10')
  assert.equal(snapshot.daily.length, 30)
  assert.deepEqual(snapshot.daily[0], { date: '2026-08-12', visitors: 0, views: 0 })
})

test('date boundaries use the GA4 property time zone rather than the UTC build date', () => {
  const data = response()
  for (const report of data.reports) report.metadata = { timeZone: 'America/Los_Angeles' }
  data.reports[1].rows[0].dimensionValues[0].value = '20260908'
  data.reports[1].rows[1].dimensionValues[0].value = '20260909'
  const snapshot = buildSnapshot(data, clock, clock)
  assert.equal(snapshot.period.end, '2026-09-09')
  assert.equal(snapshot.period.start, '2026-08-11')
})

test('thresholded or sampled missing rows stay unknown instead of fabricated zeros', () => {
  const data = response()
  data.reports[1].metadata = { ...metadata, subjectToThresholding: true }
  const snapshot = buildSnapshot(data, clock, clock)
  assert.equal(snapshot.quality.thresholded, true)
  assert.deepEqual(snapshot.daily[0], { date: '2026-08-12', visitors: null, views: null })
  assert.equal(snapshot.daily.at(-1).views, 12)
})

test('an empty successful report is different from an unavailable report', () => {
  const data = response()
  for (const report of data.reports) {
    report.rows = []
    report.rowCount = 0
  }
  const snapshot = buildSnapshot(data, clock, clock)
  assert.deepEqual(snapshot.totals, { visitors: 0, views: 0 })
  data.reports[0].metadata = { ...metadata, emptyReason: 'Restricted data' }
  assert.throws(() => buildSnapshot(data, clock, clock), /unavailable/i)
  assert.deepEqual(parseStatisticsSnapshot({ schemaVersion: 1, status: 'unavailable', token: 'secret' }), {
    schemaVersion: 1, status: 'unavailable'
  })
})

test('rejects malformed counts, unexpected dates, incomplete responses and midnight-crossing requests', () => {
  for (const bad of ['NaN', '-1', '1.1', '9007199254740992']) {
    const data = response()
    data.reports[0].rows[0].metricValues[0].value = bad
    assert.throws(() => buildSnapshot(data, clock, clock))
  }
  const data = response()
  data.reports[1].rows[0].dimensionValues[0].value = '20260931'
  assert.throws(() => buildSnapshot(data, clock, clock))
  assert.throws(() => buildSnapshot({ reports: [] }, clock, clock))
  assert.throws(() => buildSnapshot(response(), new Date('2026-09-10T14:59:59Z'), new Date('2026-09-10T15:00:01Z')), /midnight/i)
})

test('public payload is allowlisted and cannot expose raw API data or credentials', () => {
  const data = response()
  data.access_token = 'private-token'
  data.reports[0].metadata.privateEmail = 'private@example.com'
  const snapshot = buildSnapshot(data, clock, clock)
  snapshot.privateKey = 'private-key'
  const publicData = parseStatisticsSnapshot(snapshot)
  assert.ok(!JSON.stringify(publicData).includes('private'))
  assert.throws(() => parseStatisticsSnapshot({ ...snapshot, site: { ...snapshot.site, host: 'other.example.com' } }))
  assert.throws(() => parseStatisticsSnapshot({ ...snapshot, daily: snapshot.daily.slice(1) }))
  assert.throws(() => parseStatisticsSnapshot({ ...snapshot, generatedAt: '2026-09-01T00:00:00Z' }))
})

test('failed refresh retains a validated previous snapshot with its original timestamp', async () => {
  const previous = buildSnapshot(response(), clock, clock)
  let requests = 0
  const result = await refreshStatistics({
    propertyId: '123456789', accessToken: 'private-token', now: () => clock,
    fetchImpl: async (url, options) => {
      requests++
      if (url.includes('analyticsdata.googleapis.com')) {
        assert.equal(options.headers.Authorization, 'Bearer private-token')
        return new Response('private API error detail', { status: 403 })
      }
      assert.equal(options.headers?.Authorization, undefined)
      return Response.json(previous)
    }
  })
  assert.equal(requests, 2)
  assert.equal(result.source, 'previous')
  assert.equal(result.snapshot.generatedAt, previous.generatedAt)
  assert.ok(!JSON.stringify(result).includes('private'))
})

test('missing credentials and missing previous data produce an honest unavailable state', async () => {
  const result = await refreshStatistics({
    fetchImpl: async () => new Response('not found', { status: 404 })
  })
  assert.equal(result.source, 'unavailable')
  assert.deepEqual(result.snapshot, { schemaVersion: 1, status: 'unavailable' })
})

test('a corrupted previous snapshot cannot be republished as trustworthy counts', async () => {
  const previous = buildSnapshot(response(), clock, clock)
  previous.totals.visitors = -5
  const result = await refreshStatistics({
    now: () => clock, fetchImpl: async () => Response.json(previous)
  })
  assert.equal(result.source, 'unavailable')
})

test('successful API refresh publishes only aggregate data', async () => {
  const result = await refreshStatistics({
    propertyId: '123456789', accessToken: 'private-token', now: () => clock,
    fetchImpl: async (url, options) => {
      assert.equal(url, 'https://analyticsdata.googleapis.com/v1beta/properties/123456789:batchRunReports')
      assert.equal(options.method, 'POST')
      return Response.json(response())
    }
  })
  assert.equal(result.source, 'ga4')
  assert.equal(result.snapshot.totals.visitors, 7)
})

test('the statistics utility stays navigable but out of the learning corpus', () => {
  const groups = [{ group: 'Introduction', items: [{ title: 'Statistics', path: 'statistics.md' }] }]
  assert.deepEqual(buildDocuments('en', groups, () => '# Statistics'), [])
  assert.equal(buildLlmsFull('en', groups, () => '# Statistics').text, '')
  assert.equal(absolutizeLinks('[Stats](./statistics.md)', 'en', 'README.md'),
    '[Stats](https://www.atomai.click/kubernetes-docs/en/statistics)')
})

test('the browser loader retries synchronous failures and shares successful requests', async () => {
  let calls = 0
  const errors = [], accepted = []
  const loader = createStatisticsLoader({
    getUrl: () => '/kubernetes-docs/site-statistics.json',
    onSnapshot: value => accepted.push(value),
    onError: value => errors.push(value),
    fetchImpl: () => {
      if (++calls === 1) throw new TypeError('Synchronous fetch failure')
      return Promise.resolve(Response.json(buildSnapshot(response(), clock, clock)))
    }
  })
  await loader()
  assert.deepEqual(errors, [false, true])
  const retry = loader()
  assert.equal(loader(), retry)
  await retry
  assert.equal(calls, 2)
  assert.equal(accepted[0].totals.visitors, 7)
  assert.equal(errors.at(-1), false)
  await loader()
  assert.equal(calls, 2)
})

test('the browser loader works without AbortSignal.timeout', async () => {
  const original = AbortSignal.timeout
  try {
    AbortSignal.timeout = undefined
    let accepted
    const loader = createStatisticsLoader({
      getUrl: () => '/site-statistics.json',
      onSnapshot: value => { accepted = value },
      onError: () => {},
      fetchImpl: async (_url, options) => {
        assert.ok(options.signal instanceof AbortSignal)
        return Response.json({ schemaVersion: 1, status: 'unavailable' })
      }
    })
    await loader()
    assert.equal(accepted.status, 'unavailable')
  } finally {
    AbortSignal.timeout = original
  }
})

test('a timed-out browser request can be retried', async () => {
  const errors = []
  let calls = 0, accepted
  const loader = createStatisticsLoader({
    getUrl: () => '/site-statistics.json', timeoutMs: 10,
    onSnapshot: value => { accepted = value },
    onError: value => errors.push(value),
    fetchImpl: (_url, options) => {
      if (++calls > 1) return Promise.resolve(Response.json({ schemaVersion: 1, status: 'unavailable' }))
      return new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new Error('Timed out')), { once: true })
      })
    }
  })
  await loader()
  assert.equal(errors.at(-1), true)
  await loader()
  assert.equal(calls, 2)
  assert.equal(accepted.status, 'unavailable')
})
