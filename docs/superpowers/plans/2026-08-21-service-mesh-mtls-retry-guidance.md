# Service Mesh mTLS and Retry Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the Korean and English Istio/Cilium documentation so mTLS data-plane selection is independent from HTTP retry policy, especially for non-idempotent writes.

**Architecture:** Keep GitBook-compatible Markdown as the source of truth and enforce the critical guidance with a Node content-contract test. Update the existing comparison, retry, Cilium security, and quiz pages in place without changing measured benchmark values or other locales.

**Tech Stack:** Markdown, Mermaid, Kubernetes/Istio `VirtualService` YAML, Node.js built-in test runner, VitePress.

---

### Task 1: Add the bilingual content contract

**Files:**
- Create: `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

- [ ] **Step 1: Write the failing content-contract test**

```js
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
    const retry = await read(locale, 'service-mesh/istio/traffic-management/05-retry-timeout.md')
    assert.match(retry, /connect-failure,refused-stream,unavailable,cancelled/)
    assert.match(retry, /regex:\s*["']\^\(POST\|PATCH\)/)
    assert.match(retry, /attempts:\s*0/)
    assert.doesNotMatch(retry, /attempts:\s*1\s*#.*(?:disable|비활성)/i)
  })

  test(`${locale}: comparison separates raw failures from retries`, async () => {
    const comparison = await read(locale, 'service-mesh/istio/comparison/03-sidecar-vs-ambient.md')
    assert.match(comparison, /upstream_rq_retry/)
    assert.match(comparison, /(?:raw failure|원시 실패)/i)
    assert.match(comparison, /Cilium/)
  })

  test(`${locale}: Cilium authentication and encryption are distinct`, async () => {
    const security = await read(locale, 'service-mesh/cilium-service-mesh/03-security.md')
    assert.match(security, /out-of-band/i)
    assert.match(security, /WireGuard.*IPsec|IPsec.*WireGuard/s)
    assert.match(security, /STRICT/)
  })

  test(`${locale}: quizzes use the current retry document path`, async () => {
    const trafficQuiz = await read(locale, 'quizzes/service-mesh/istio/traffic-management.md')
    assert.doesNotMatch(trafficQuiz, /06-timeout-retry\.md/)
    assert.match(trafficQuiz, /05-retry-timeout\.md/)
  })
}
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

Expected: FAIL because the retry pages lack the default-policy warning and method-split `attempts: 0` example, the comparison lacks raw-versus-retried measurement guidance, and the quizzes still reference `06-timeout-retry.md`.

### Task 2: Correct Istio retry guidance

**Files:**
- Modify: `ko/service-mesh/istio/traffic-management/05-retry-timeout.md`
- Modify: `en/service-mesh/istio/traffic-management/05-retry-timeout.md`
- Test: `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

- [ ] **Step 1: Add the default retry warning in both locales**

Add the following policy facts near `## Retry 설정` / `## Retry Configuration`:

```markdown
> **Important:** Omitting `retries` does not necessarily mean no retry. Istio's
> cluster-wide default is `attempts: 2` with
> `retryOn: connect-failure,refused-stream,unavailable,cancelled`. Set
> `attempts: 0` on a route to disable proxy retries explicitly.
```

The Korean page must carry the same values and state that `attempts` counts retry attempts after the original request.

- [ ] **Step 2: Replace the unsafe POST example with method-split routes**

Use this policy shape in both locales:

```yaml
http:
  - name: writes-no-mesh-retry
    match:
      - method:
          regex: "^(POST|PATCH)$"
    timeout: 10s
    retries:
      attempts: 0
    route:
      - destination:
          host: orders
  - name: reads-limited-retry
    match:
      - method:
          regex: "^(GET|HEAD)$"
    timeout: 5s
    retries:
      attempts: 2
      perTryTimeout: 2s
      retryOn: connect-failure,refused-stream
    route:
      - destination:
          host: orders
```

Explain that POST/PATCH and domain-defined writes default to no mesh retry, while PUT/DELETE are only safe when the application contract is truly idempotent.

- [ ] **Step 3: Add ambiguity and application safeguards**

Add matching ko/en guidance that a server may commit before its response is lost, so a proxy cannot infer replay safety from a reset or 503. Document these controls:

```markdown
- `Idempotency-Key` backed by a database uniqueness constraint
- `ETag`/`If-Match` or version-based compare-and-swap
- transaction/command status lookup after an ambiguous outcome
- transactional outbox for irreversible downstream effects
```

Link the Istio VirtualService reference, Envoy retry reference, and RFC 9110.

- [ ] **Step 4: Run the focused test**

Run: `node --test scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

Expected: retry assertions pass; comparison/Cilium/quiz assertions remain red.

### Task 3: Add equivalent data-plane and security decision guidance

**Files:**
- Modify: `ko/service-mesh/istio/comparison/03-sidecar-vs-ambient.md`
- Modify: `en/service-mesh/istio/comparison/03-sidecar-vs-ambient.md`
- Modify: `ko/service-mesh/cilium-service-mesh/03-security.md`
- Modify: `en/service-mesh/cilium-service-mesh/03-security.md`
- Test: `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

- [ ] **Step 1: Add a raw-failure measurement section to the Istio comparison**

Add a four-plane table covering:

| Data plane | mTLS/encryption meaning | L7 retry location | Recommended use |
|---|---|---|---|
| Istio sidecar | Workload certificate mTLS | Per-pod Envoy | Conservative baseline for critical writes |
| Ambient L4 | HBONE workload mTLS | None in ztunnel | First candidate when only Istio mTLS/L4 policy is needed |
| Ambient L7 | HBONE plus waypoint Envoy | Shared waypoint | Only where L7 routing/policy is required |
| Cilium | Identity authentication plus separately selected transport encryption | Not provided by L3/L4 encryption | Existing Cilium deployments needing identity policy and network encryption |

State that sidecar/waypoint can hide a raw failure through retry while ztunnel cannot interpret an HTTP 503. Require rollout tests to record raw HTTP/TCP failures, `upstream_rq_retry`, retry successes, and final client-visible outcomes separately, with write retries disabled.

- [ ] **Step 2: Correct the Cilium security model**

Replace the opening claim and sequence diagram with three distinct layers:

```markdown
1. identity-based authorization through Cilium identities and policy;
2. mutual authentication performed out-of-band from the application data path;
3. payload encryption supplied separately by WireGuard/IPsec, or by the native
   ztunnel mTLS preview where supported.
```

State that this is not automatically equivalent to Istio `PeerAuthentication`
`STRICT`. Recommend Cilium for efficient L3/L4 policy and network encryption on
an existing Cilium data plane, and Istio where mature workload-certificate mTLS
and Istio L7 policy semantics are required.

- [ ] **Step 3: Run the focused test**

Run: `node --test scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

Expected: retry, comparison, and Cilium assertions pass; quiz link assertions remain red.

### Task 4: Update quizzes and verify the documentation build

**Files:**
- Modify: `ko/quizzes/service-mesh/istio/comparison.md`
- Modify: `en/quizzes/service-mesh/istio/comparison.md`
- Modify: `ko/quizzes/service-mesh/istio/traffic-management.md`
- Modify: `en/quizzes/service-mesh/istio/traffic-management.md`
- Test: `scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

- [ ] **Step 1: Add one comparison question in both locales**

Ask which experiment fairly compares rollout reliability. The correct answer must disable write retries and separately record raw HTTP errors, TCP resets, retry attempts, and final client outcomes. Update the question count and score bands from four to five.

- [ ] **Step 2: Correct the traffic-management quiz**

In the retry explanation, explicitly state:

```markdown
`attempts: 0` disables retries. `attempts: 1` allows one replay after the
original attempt and is not "retry disabled."
```

Add the commit-before-response-loss ambiguity and the workload-mTLS-versus-network-encryption distinction, and change `06-timeout-retry.md` to `05-retry-timeout.md`. Preserve the existing `README.md` link corrections already present in the working tree.

- [ ] **Step 3: Verify GREEN**

Run: `node --test scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs`

Expected: all content-contract tests pass.

- [ ] **Step 4: Run repository validation**

Run: `npm run docs:validate`

Expected: all Node tests, ko/en internal-link checks, and image-asset checks pass.

- [ ] **Step 5: Build Korean and English independently in `/tmp`**

```bash
rm -rf /tmp/vitepress-mtls-retry-ko /tmp/vitepress-mtls-retry-en
VITEPRESS_BUILD_LOCALE=ko NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-mtls-retry-ko
VITEPRESS_BUILD_LOCALE=en NODE_OPTIONS=--max-old-space-size=8192 \
  node node_modules/vitepress/bin/vitepress.js build . \
  --outDir /tmp/vitepress-mtls-retry-en
```

Expected: both commands exit 0 and produce `ko/service-mesh/istio/comparison/03-sidecar-vs-ambient.html` and `en/service-mesh/istio/comparison/03-sidecar-vs-ambient.html` in their respective output directories.

- [ ] **Step 6: Review the final diff**

Run:

```bash
git diff --check
git diff --stat -- \
  scripts/__tests__/service-mesh-mtls-retry-guidance.test.mjs \
  ko/service-mesh/istio en/service-mesh/istio \
  ko/service-mesh/cilium-service-mesh/03-security.md \
  en/service-mesh/cilium-service-mesh/03-security.md \
  ko/quizzes/service-mesh/istio en/quizzes/service-mesh/istio
```

Expected: no whitespace errors and only the approved ko/en documentation scope plus its contract test is changed by this implementation.

- [ ] **Step 7: Record commit limitation**

Do not modify `.git`. The repository metadata is read-only in this environment, so leave the verified changes in the working tree and report that no commit was created.
