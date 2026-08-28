# Service Mesh mTLS and Retry Guidance Design

## Goal

Align the Korean and English service mesh documentation around one production
decision:

- choose mTLS data planes independently from HTTP retry behavior;
- do not use mesh retries to hide rollout failures on non-idempotent writes;
- compare Istio sidecar, ambient L4, ambient L7 with waypoint, and Cilium using
  equivalent security and failure criteria.

The update must remain compatible with both GitBook and VitePress.

## Scope

Update the Korean and English versions of:

- `service-mesh/istio/comparison/03-sidecar-vs-ambient.md`
- `service-mesh/istio/traffic-management/05-retry-timeout.md`
- `service-mesh/cilium-service-mesh/03-security.md`
- `quizzes/service-mesh/istio/comparison.md`
- `quizzes/service-mesh/istio/traffic-management.md`

No Chinese, Japanese, or Spanish translation is included. Those locales remain
GitBook sources and are handled by the existing translation workflow outside
this change.

## Content Design

### Sidecar, Ambient, and Cilium comparison

The existing EKS measurements remain the primary evidence. Add guidance that:

- sidecar and waypoint Envoy proxies can apply L7 retries;
- ztunnel is an L4 proxy and cannot inspect an HTTP 503 or replay an HTTP
  request;
- lower client-visible 503 counts can be caused by retries rather than fewer
  raw transport failures;
- comparisons must disable write retries and record raw HTTP errors, TCP
  resets, retry attempts, and final client-visible outcomes separately;
- ambient L4 is the first candidate when only Istio workload mTLS is required;
- waypoint is added only for services that require L7 policy or routing;
- sidecar remains the conservative baseline for critical non-idempotent paths
  when ambient rollout failures exceed the workload error budget.

Add a compact comparison of these four data planes:

1. Istio sidecar
2. Istio ambient L4 with ztunnel only
3. Istio ambient L7 with waypoint
4. Cilium authentication plus transport encryption

### Retry and timeout guidance

Correct the current POST example, which configures one retry and includes
`reset`. The updated guidance must state:

- Istio applies its cluster-wide default retry policy when a route does not
  specify one;
- `attempts: 0` explicitly disables retries;
- POST, PATCH, and other domain-defined write operations default to no mesh
  retry;
- GET and HEAD can use narrowly scoped retries;
- PUT and DELETE are only retried when the application's domain contract is
  actually idempotent;
- a response can be lost after the server commits, so a proxy cannot prove
  that replay is safe.

Provide one method-split `VirtualService` example with write retries disabled
and read retries limited to connection establishment or refused-stream
conditions.

Describe application-level safeguards:

- idempotency keys backed by a database uniqueness constraint;
- optimistic concurrency through ETag/If-Match or a version field;
- transaction or command status lookup for ambiguous outcomes;
- transactional outbox for irreversible downstream side effects.

### Cilium security semantics

Separate three concepts that are currently conflated:

- Cilium identity-based authorization;
- Cilium mutual authentication;
- payload encryption using WireGuard/IPsec or the native ztunnel preview.

The text must avoid presenting these as an automatic drop-in equivalent to
Istio STRICT workload mTLS. It must identify the maturity and operational
differences and explain when Cilium is appropriate:

- Cilium is suitable when the requirement is efficient L3/L4 identity policy
  and network encryption on an existing Cilium data plane;
- Istio is preferable when mature workload-certificate mTLS, PeerAuthentication
  semantics, or Istio L7 policy is required.

### Quiz updates

Update the comparison and traffic-management quizzes so that learners can
distinguish:

- raw failures from failures hidden by retries;
- `attempts: 0` from `attempts: 1`;
- transport ambiguity from a confirmed server-side failure;
- workload mTLS from network encryption.

Fix references to the nonexistent `06-timeout-retry.md` path.

## Source Policy

Use primary sources:

- current Istio VirtualService and ambient architecture documentation;
- current Envoy retry documentation;
- Kubernetes endpoint termination documentation;
- Cilium mutual authentication, encryption, and Istio integration
  documentation;
- RFC 9110 for HTTP idempotency semantics;
- the existing repository's EKS 1.36 measurements for local conclusions.

Externally sourced claims receive direct Markdown links in the content. Local
measurements remain explicitly labeled as results from the documented test
environment.

## Validation

Add a content contract test that fails before the documentation update and
verifies both locales contain:

- the Istio default retry warning;
- `attempts: 0` for write routes;
- no recommendation to retry POST with `reset`;
- the Cilium authentication-versus-encryption distinction;
- matching decision guidance in Korean and English.

Then run:

1. the new focused test;
2. the complete documentation test suite;
3. local link and image validation;
4. Markdown diff checks;
5. separate Korean and English VitePress production builds using `/tmp`
   output directories to avoid increasing root EBS usage.

## Non-Goals

- changing the measured EKS benchmark values;
- deploying or benchmarking a live cluster;
- changing Istio or Cilium installation manifests;
- translating cn/jp/es content;
- implementing application idempotency logic.
