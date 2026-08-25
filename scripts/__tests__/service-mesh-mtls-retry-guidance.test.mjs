import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

async function read(locale, relativePath) {
  return readFile(path.join(root, locale, relativePath), 'utf8')
}

for (const locale of ['ko', 'en']) {
  test(`${locale}: write routes explicitly disable mesh retries`, async () => {
    const retry = await read(
      locale,
      'service-mesh/istio/traffic-management/05-retry-timeout.md',
    )

    assert.match(
      retry,
      /connect-failure,refused-stream,unavailable,cancelled/,
    )
    assert.match(retry, /regex:\s*["']\^\(POST\|PATCH\)/)
    assert.match(retry, /attempts:\s*0/)
    assert.doesNotMatch(
      retry,
      /attempts:\s*1\s*#.*(?:disable|disabled|비활성)/i,
    )
  })

  test(`${locale}: comparison separates raw failures from retries`, async () => {
    const comparison = await read(
      locale,
      'service-mesh/istio/comparison/03-sidecar-vs-ambient.md',
    )

    assert.match(comparison, /upstream_rq_retry/)
    assert.match(comparison, /(?:raw failure|원시 실패)/i)
    assert.match(comparison, /Cilium/)
  })

  test(`${locale}: Cilium authentication and encryption are distinct`, async () => {
    const security = await read(
      locale,
      'service-mesh/cilium-service-mesh/03-security.md',
    )

    assert.match(security, /out-of-band/i)
    assert.match(security, /WireGuard.*IPsec|IPsec.*WireGuard/s)
    assert.match(security, /STRICT/)
  })

  test(`${locale}: quizzes use the current retry document path`, async () => {
    const trafficQuiz = await read(
      locale,
      'quizzes/service-mesh/istio/traffic-management.md',
    )

    assert.doesNotMatch(trafficQuiz, /06-timeout-retry\.md/)
    assert.match(trafficQuiz, /05-retry-timeout\.md/)
  })

  test(`${locale}: no example retries a POST with reset`, async () => {
    const retry = await read(
      locale,
      'service-mesh/istio/traffic-management/05-retry-timeout.md',
    )

    // Every example that matches a POST route must not pair it with a
    // `retryOn` that includes `reset` — a reset can occur after the server
    // already committed the write, so replaying it is unsafe.
    const postMethodPattern =
      /(?:exact:\s*POST|regex:\s*["'][^"'\n]*POST[^"'\n]*["'])/g
    const WINDOW = 700
    let match
    let checked = 0
    while ((match = postMethodPattern.exec(retry)) !== null) {
      const window = retry.slice(match.index, match.index + WINDOW)
      const retryOnMatch = window.match(/retryOn:\s*([^\n]+)/)
      if (retryOnMatch) {
        checked += 1
        assert.doesNotMatch(
          retryOnMatch[1],
          /reset/,
          `found a POST route paired with retryOn containing "reset": ${retryOnMatch[1]}`,
        )
      }
    }
    // Sanity check: the page still contains POST examples to scan at all.
    assert.ok(
      /POST/.test(retry),
      'expected the retry/timeout page to contain POST examples',
    )
  })
}

test('comparison decision summary and Cilium guidance stay in sync across ko/en', async () => {
  const [koComparison, enComparison] = await Promise.all([
    read('ko', 'service-mesh/istio/comparison/03-sidecar-vs-ambient.md'),
    read('en', 'service-mesh/istio/comparison/03-sidecar-vs-ambient.md'),
  ])
  const [koSecurity, enSecurity] = await Promise.all([
    read('ko', 'service-mesh/cilium-service-mesh/03-security.md'),
    read('en', 'service-mesh/cilium-service-mesh/03-security.md'),
  ])

  const countOf = (text, pattern) => (text.match(pattern) || []).length

  // The Decision Summary table must mention Cilium in both locales — a
  // locale-only addition (like the earlier gap where Cilium existed only
  // in the secondary table, not the top summary) would slip past
  // per-locale-only assertions.
  assert.equal(
    countOf(koComparison, /Cilium/g),
    countOf(enComparison, /Cilium/g),
    'ko/en comparison docs mention Cilium a different number of times',
  )

  for (const pattern of [/upstream_rq_retry/g, /STRICT/g]) {
    assert.equal(
      countOf(koComparison, pattern),
      countOf(enComparison, pattern),
      `ko/en comparison docs disagree on occurrences of ${pattern}`,
    )
  }

  for (const pattern of [/out-of-band/gi, /WireGuard/gi, /STRICT/g]) {
    assert.equal(
      countOf(koSecurity, pattern),
      countOf(enSecurity, pattern),
      `ko/en Cilium security docs disagree on occurrences of ${pattern}`,
    )
  }

  // Both locales must state the Cilium-vs-Istio decision guidance, not just
  // the negative "not an automatic replacement" framing.
  assert.match(enSecurity, /[Cc]hoose (?:Cilium|Istio)/)
  assert.match(koSecurity, /고르는 경우/)
})
