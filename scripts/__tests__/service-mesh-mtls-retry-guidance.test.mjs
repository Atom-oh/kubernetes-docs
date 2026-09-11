import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

async function read(locale, relativePath) {
  return readFile(path.join(root, locale, relativePath), 'utf8')
}

const meaningful = (line) => line.trim() && !line.trimStart().startsWith('#')
const indentation = (line) => line.match(/^ */)[0].length

// Extract the block-style YAML mappings/lists used by these documentation
// examples. Bound each policy to its own HTTP route: an attempts: 0 on a
// neighboring read route must not satisfy a write-route assertion.
function fieldBlock(lines, name, indent) {
  const start = lines.findIndex((line) =>
    new RegExp(`^ {${indent}}${name}:\\s*(?:#.*)?$`).test(line),
  )
  if (start < 0) return []
  let end = start + 1
  while (end < lines.length) {
    const line = lines[end]
    if (
      meaningful(line) &&
      (indentation(line) < indent ||
        (indentation(line) === indent && !line.trimStart().startsWith('- ')))
    ) break
    end += 1
  }
  return lines.slice(start + 1, end)
}

function sequenceItems(lines) {
  const first = lines.findIndex(meaningful)
  if (first < 0 || !lines[first].trimStart().startsWith('- ')) return []
  const indent = indentation(lines[first])
  const starts = lines.flatMap((line, index) =>
    indentation(line) === indent && line.trimStart().startsWith('- ')
      ? [index]
      : [],
  )
  return starts.map((start, index) => {
    const item = lines.slice(start, starts[index + 1] ?? lines.length)
    item[0] = item[0].replace(/^(\s*)- /, '$1  ')
    return { lines: item, indent: indent + 2 }
  })
}

function scalarValue(line) {
  const value = line.slice(line.indexOf(':') + 1).trim()
  const quoted = value.match(/^(["'])(.*?)\1(?:\s*#.*)?$/)
  return quoted ? quoted[2] : value.replace(/\s+#.*$/, '').trim()
}

function virtualServiceHttpRoutes(markdown) {
  const routes = []
  for (const fence of markdown.matchAll(/^```ya?ml\s*\n([\s\S]*?)^```\s*$/gm)) {
    for (const document of fence[1].split(/^---\s*$/m)) {
      if (!/^kind:\s*VirtualService\s*$/m.test(document)) continue
      const spec = fieldBlock(document.split('\n'), 'spec', 0)
      const http = fieldBlock(spec, 'http', 2)
      const documentRoutes = []
      for (const route of sequenceItems(http)) {
        const methods = sequenceItems(
          fieldBlock(route.lines, 'match', route.indent),
        ).flatMap((match) =>
          fieldBlock(match.lines, 'method', match.indent)
            .filter((line) => /^\s*(exact|prefix|regex):/.test(line))
            .map((line) => ({
              type: line.trim().split(':')[0],
              value: scalarValue(line),
            })),
        )
        const retries = fieldBlock(route.lines, 'retries', route.indent)
        const attempts = retries.find((line) => /^\s*attempts:/.test(line))
        const retryOn = retries.find((line) => /^\s*retryOn:/.test(line))
        documentRoutes.push({
          methods,
          attempts: attempts ? Number(scalarValue(attempts)) : undefined,
          retryOn: retryOn ? scalarValue(retryOn).split(/\s*,\s*/) : [],
        })
      }
      const declaredMethods = document
        .split('\n')
        .filter(meaningful)
        .map((line) => line.replace(/\s+#.*$/, ''))
        .join('\n')
        .match(/\bmethod\s*:/g) ?? []
      assert.equal(
        documentRoutes.reduce(
          (count, route) => count + route.methods.length, 0,
        ),
        declaredMethods.length,
        'a method matcher could not be read; update the extractor rather than skipping a safety check',
      )
      routes.push(...documentRoutes)
    }
  }
  return routes
}

function matchesMethod(route, method) {
  return route.methods.some(({ type, value }) => {
    if (type === 'exact') return value === method
    if (type === 'prefix') return method.startsWith(value)
    // The method expressions in this guide use the common JS/RE2 subset.
    return new RegExp(`^(?:${value})$`).test(method)
  })
}

function assertWriteRoutesDisableRetries(routes) {
  for (const method of ['POST', 'PATCH']) {
    const matches = routes.filter((route) => matchesMethod(route, method))
    assert.ok(matches.length, `expected an explicit ${method} route`)
    for (const route of matches) {
      assert.equal(route.attempts, 0, `${method} route must explicitly set attempts: 0`)
    }
  }
}

function assertPostRoutesDoNotRetryReset(routes) {
  const matches = routes.filter((route) => matchesMethod(route, 'POST'))
  assert.ok(matches.length, 'expected an explicit POST route')
  for (const route of matches) {
    assert.ok(!route.retryOn.includes('reset'), 'POST route must not retry an ambiguous reset')
  }
}

for (const locale of ['ko', 'en']) {
  test(`${locale}: EnvoyFilter examples use the API version served by Istio`, async () => {
    let checked = 0
    for (const directory of ['service-mesh/istio', 'quizzes/service-mesh/istio']) {
      const files = await readdir(path.join(root, locale, directory), { recursive: true })
      for (const file of files.filter(file => file.endsWith('.md'))) {
        const relative = path.join(directory, file)
        const markdown = await read(locale, relative)
        for (const fence of markdown.matchAll(/^```ya?ml\s*\n([\s\S]*?)^```\s*$/gm)) {
          for (const document of fence[1].split(/^---\s*$/m)) {
            if (!/^kind:\s*EnvoyFilter\s*$/m.test(document)) continue
            // Unlike VirtualService, EnvoyFilter still serves only v1alpha3
            // in the official Istio 1.31.0 CRD.
            assert.match(document, /^apiVersion:\s*networking\.istio\.io\/v1alpha3\s*$/m, relative)
            checked += 1
          }
        }
      }
    }
    assert.ok(checked > 0, 'expected EnvoyFilter examples to be checked')
  })

  test(`${locale}: write routes explicitly disable mesh retries`, async () => {
    const retry = await read(
      locale,
      'service-mesh/istio/traffic-management/05-retry-timeout.md',
    )

    assert.match(
      retry,
      /connect-failure,refused-stream,unavailable,cancelled/,
    )
    assertWriteRoutesDisableRetries(virtualServiceHttpRoutes(retry))
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
    assertPostRoutesDoNotRetryReset(virtualServiceHttpRoutes(retry))
  })
}

function retryExample(methods, writePolicy) {
  return `\`\`\`yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: example
spec:
  hosts: [example]
  http:
  - match:
${methods}
    route:
    - destination:
        host: example
${writePolicy}
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: example
    retries:
      attempts: 0
      retryOn: reset
\`\`\`
`
}

test('write safety accepts reordered, expanded and exact method matchers', () => {
  const policy = '    retries:\n      attempts: 0'
  for (const methods of [
    '    - method:\n        regex: "^(POST|PATCH)$"',
    "    - method:\n        regex: '^(DELETE|PATCH|PUT|POST)$'",
    '    - method:\n        exact: PATCH\n    - method:\n        exact: POST',
  ]) {
    assertWriteRoutesDisableRetries(
      virtualServiceHttpRoutes(retryExample(methods, policy)),
    )
  }
})

test('write safety rejects missing or nonzero retry limits on the write route', () => {
  const methods = '    - method:\n        regex: "^(POST|PATCH)$"'
  for (const policy of ['', '    retries:\n      attempts: 1']) {
    assert.throws(
      () => assertWriteRoutesDisableRetries(
        virtualServiceHttpRoutes(retryExample(methods, policy)),
      ),
      /POST route must explicitly set attempts: 0/,
    )
  }
  assert.throws(
    () => virtualServiceHttpRoutes(
      retryExample('    - method: { exact: POST }', '    retries:\n      attempts: 0'),
    ),
    /a method matcher could not be read/,
    'unsupported layouts must fail closed, not silently skip a write route',
  )
})

test('POST reset checking does not consume a following read route policy', () => {
  const methods = '    - method:\n        exact: POST'
  assertPostRoutesDoNotRetryReset(
    virtualServiceHttpRoutes(retryExample(methods, '    retries:\n      attempts: 0')),
  )
  assert.throws(
    () => assertPostRoutesDoNotRetryReset(
      virtualServiceHttpRoutes(
        retryExample(methods, '    retries:\n      attempts: 3\n      retryOn: 5xx,reset'),
      ),
    ),
    /POST route must not retry an ambiguous reset/,
  )
})

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
