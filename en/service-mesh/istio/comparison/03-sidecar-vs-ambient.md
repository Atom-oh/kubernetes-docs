# Sidecar vs Ambient Mode Selection Guide (EKS 1.36 Test Results)

> **Supported Versions**: Istio 1.30 / EKS 1.36
> **Last Updated**: August 21, 2026

This document is a test-result-driven guide for deciding whether to adopt Istio in **sidecar mode or ambient mode** for mission-critical workloads on EKS (e.g., the order/matching path of a crypto exchange). The architecture itself is already covered in [Ambient Mode](../advanced/01-ambient-mode.md), so this document does not repeat it — instead it presents test results and a recommendation against 4 concrete requirements.

1. mTLS required (cluster-internal pod-to-pod communication)
2. NetworkPolicy required
3. Latency-sensitive workloads
4. Zero-downtime rollout — verifying the ambient waypoint 503 concern

> 💡 Every number in this document comes from a **dedicated, single-tenant EKS cluster** (`mesh-isolated-test`) built solely for this test cycle and deleted afterward. See the [test isolation note](#a-note-on-test-isolation) at the end of §4 for why a dedicated cluster was necessary.

## Decision Summary

| Requirement | Sidecar | Ambient (L4, no waypoint) | Ambient (L7, waypoint) | Cilium |
|---|---|---|---|---|
| mTLS | ✅ STRICT supported, verified | ✅ STRICT supported, verified | ✅ STRICT supported, verified | ⚠️ Not measured in this cycle — documented as identity mutual authentication plus separately-enabled WireGuard/IPsec, not a single STRICT-equivalent switch (see [below](#separate-raw-failures-from-failures-hidden-by-retry)) |
| NetworkPolicy | ✅ Existing rules work as-is, verified | ⚠️ Must allow HBONE port (15008), verified | ⚠️ Must allow HBONE port (15008), verified | ⚠️ Not measured in this cycle — CiliumNetworkPolicy is the native mechanism, not a K8s NetworkPolicy add-on |
| Latency (P50 over no-mesh baseline) | +1.29ms, measured | +0.04ms (negligible), measured | +1.86ms, measured | Not measured in this cycle |
| Zero-downtime rollout | 503s occur (0.5%, measured) | **Zero actual 503s**, replaced by 0.3% TCP resets | 503s occur **2.6%, ~5x sidecar** (measured) | Not measured in this cycle |

> ✅ **One-line conclusion**: ambient without a waypoint (L4-only) was the most stable under rollout churn and had negligible latency overhead. Attaching a waypoint (L7) pushes the 503 rate above sidecar's and latency to roughly the same level as sidecar. The evidence is in §3–§4 below. Cilium is included for a like-for-like security comparison (see [below](#separate-raw-failures-from-failures-hidden-by-retry)); it was not deployed on the test cluster, so its row states documented properties only — never a substitute for a measurement.

## 1. mTLS — Test Results (EKS 1.36.2, Istio 1.30.2)

**Test environment**
- Dedicated single-tenant cluster `mesh-isolated-test` (own VPC, no other workloads), EKS control plane and worker nodes both v1.36.2, Amazon Linux 2023 (arm64, m7g.xlarge)
- Namespace-scoped `PeerAuthentication` STRICT applied to 3 test namespaces (sidecar / ambient-L4 / ambient-L7) — not mesh-wide

### Check 1 — plaintext direct pod-IP access (must be blocked)

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### Check 2 — in-mesh access via Service (must succeed)

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### Check 3 — SPIFFE certificates

Verified via `istioctl ztunnel-config certificates` / `istioctl proxy-config secret`:

| Workload | Certificate issuer | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | shared |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | shared |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | shared |

> ✅ **Verdict**: all three modes immediately block plaintext access, only in-mesh traffic returns 200, and each workload carries its own SPIFFE ID issued from the same root CA. Both sidecar and ambient satisfy the "cluster-internal pod-to-pod traffic must be mTLS" requirement.

**How they differ**: ambient applies mTLS transparently — `istio-cni` sets up traffic redirection inside the pod's network namespace, and ztunnel carries it over an HBONE (mTLS) tunnel on port 15008 — with no application code or sidecar injection required. Sidecar achieves the same via the istio-proxy container inside the application pod. See [mTLS](../security/01-mtls.md) for certificate rotation and migration strategy details for both modes.

## 2. NetworkPolicy — Test Results

Ambient forwards a pod's real traffic to ztunnel over an HBONE tunnel (TCP 15008), which ztunnel then decrypts and delivers to the destination. This means **a NetworkPolicy that allows only the application port (e.g., 8080) will block inbound traffic to an ambient-enrolled pod**, because packets actually arrive on 15008. To use ambient together with NetworkPolicy, you must **add an inbound allow rule for TCP 15008** on the target pods.

**Test setup**: enabled VPC CNI NetworkPolicy enforcement (`enableNetworkPolicy=true`, `aws-network-policy-agent v1.3.5-eksbuild.3`, eBPF) on the dedicated `mesh-isolated-test` cluster — something we couldn't safely do on the shared cluster used in an earlier round, since it would have simultaneously activated 13 pre-existing dormant NetworkPolicies belonging to other teams. A dedicated, single-tenant cluster removed that blast-radius concern entirely.

> ⚠️ **Operational gotcha found during testing**: pods created *before* `enableNetworkPolicy` was turned on are not retroactively enforced — the eBPF hooks are only attached at pod-network-setup (CNI ADD) time. A sanity check confirmed this directly: applying a policy that allowed *only* port 9999 to already-running pods still let port-8080 traffic through unblocked. A `kubectl rollout restart` (recreating the pods) after enabling the addon was required before any NetworkPolicy took effect. This is a real gotcha worth knowing before enabling NetworkPolicy on a live cluster.

**Test 1 — ingress restricted to TCP 8080 only** (fresh pods, enforcement confirmed active)

| Mode | Result |
|---|---|
| sidecar | ✅ 200 OK — unaffected |
| ambient-L4 | ❌ blocked (`i/o timeout`) |
| ambient-L7 | ❌ blocked (`i/o timeout`) |

**Test 2 — ingress allows TCP 8080 + TCP 15008 (HBONE)**

| Mode | Result |
|---|---|
| ambient-L4 | ✅ 200 OK — restored |
| ambient-L7 | ✅ 200 OK — restored |

> ✅ **Verdict**: confirms the hypothesis above with real traffic. Ambient's real inbound packet at the workload pod's network namespace arrives on the ztunnel HBONE port (15008), not the application's port (8080); an app-port-only NetworkPolicy silently breaks ambient-enrolled pods. Sidecar is unaffected because sidecar's traffic capture happens entirely inside the pod's own network namespace after the packet already arrived on the application port.

We recommend defense-in-depth: apply both network-level (NetworkPolicy) and identity-level (AuthorizationPolicy) controls together. The sidecar-mode conflict between mTLS and NetworkPolicy is covered in [mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict).

## 3. Latency — Test Results (T5)

**Test setup**: fortio load, 200 qps, 60s, 16 connections, 12,000 requests per case, steady state (no rollout restarts running) — no-mesh baseline (unmeshed namespace) vs. sidecar vs. ambient-L4 vs. ambient-L7, all on the same `mesh-isolated-test` Graviton (m7g.xlarge) nodes. All cases returned 100% Code 200.

| Case | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (baseline) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (no waypoint) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**P50 overhead vs. no-mesh baseline**: sidecar +1.29ms · ambient-L4 +0.04ms (negligible) · ambient-L7 +1.86ms

> ✅ **Verdict**: consistent with the previously-cited published ambient-mode benchmark (L4-only lower than sidecar, waypoint roughly on par with or slightly above sidecar) — these are now first-party measurements, not a citation. For a latency-sensitive workload like a crypto trading path, this lines up with §4 below: **avoiding the waypoint helps both latency and rollout stability**.

## 4. Zero-Downtime Rollout — 503 Test Results (core finding)

### Background

The concern with ambient is that **the L7 waypoint (Envoy) reuses connections from its pool, keyed by destination IP:Port**, while **ztunnel does not notify the waypoint when a pod terminates**. If the terminated pod's IP is reassigned to a new pod, the waypoint may reuse a now-invalid connection and return a 503. Sidecar can suffer from a similar pod-termination race (see [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination) for the mechanism). We measured both failure modes head-to-head on EKS 1.36.

**Test environment**
- Dedicated single-tenant cluster `mesh-isolated-test`, EKS control plane and worker nodes both v1.36.2, arm64 (Graviton m7g.xlarge), Istio 1.30.2
- 3 namespaces (sidecar / ambient-L4 / ambient-L7) running **byte-identical workloads** (an echo server Deployment with 6 replicas + a fortio client) — only the namespace label differs
- The fortio client held keepalive connections at 100 req/s while the target namespace's `echo` Deployment was repeatedly `rollout restart`ed
- 60,000 requests collected per mode (= 100 qps × 600s)

### Results

| Mode | Rollout cycles | Requests | 503 count | 503 rate | Other errors (-1, TCP reset/EOF) | Sockets used |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4 (no waypoint) | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7 (waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |

> Perfect keepalive would mean 16 sockets used. Ambient-L7 also left 87 of 60,000 calls incomplete when the run ended, and its average latency (50.4ms) was far above the other two modes (~2-3ms).

<details>
<summary>Raw fortio run output</summary>

```
[sidecar]      42 rollouts, Sockets used: 350 (16 would be perfect keepalive)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- connection dropped with no HTTP response, not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 of 60,000 calls completed; avg latency 50.4ms vs. ~2-3ms for the other two modes)
```

</details>

**Verdict**

1. **Ambient-L7 (waypoint)'s 503 rate (2.6%) is roughly 5x sidecar's (0.5%)** on this dedicated cluster — an even larger gap than an earlier same-day measurement on a shared, contended cluster had suggested (see the isolation note below), reinforcing rather than softening the original concern that "the waypoint's connection pool reuses stale connections and produces 503s" under rollout churn.
2. **Ambient-L4 (no waypoint) again produced zero actual HTTP 503s.** Instead, it saw connection-level TCP errors ("-1", no response) at 0.3%. At L4 a failure surfaces as a *dropped connection*, not a *503 response* — leaving reconnection handling to the client/application rather than to a proxy that synthesizes an error response.
3. Ambient-L7 also showed a large average-latency spike and 87 requests that never completed within the run — consistent with the waypoint struggling under combined rollout churn and sustained load, distinct from the other two modes.
4. Rollout cycles completed in the same 600-second window (42 / 64 / 65 for sidecar / ambient-L4 / ambient-L7) were far higher than an earlier measurement on a busy shared cluster, because this dedicated cluster had no other tenants competing for CPU/network — the *relative* ordering (sidecar slowest, ambient-L4 fastest) held up, but absolute rollout speed is highly dependent on cluster contention and shouldn't be over-interpreted as an intrinsic property of any mode.

### Follow-up: after graceful-shutdown hardening

The baseline numbers above reflect **no shutdown tuning at all**. We reran the same T1 test (100 qps × 600s, 60,000 requests/mode) after adding two changes:

- **All three modes**: `lifecycle.preStop.sleep.seconds: 10` on the `echo` container (the K8s 1.29+ native sleep action — no exec/shell required) plus `terminationGracePeriodSeconds: 40`, giving Endpoint removal time to propagate across the cluster before the pod actually stops accepting connections
- **Sidecar only**: `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s` injected into istio-proxy via the `proxy.istio.io/config` pod annotation (confirmed present in the istio-proxy init container's actual env) — exits as soon as active connections hit zero instead of always waiting the full 30s

| Mode | Rollout cycles | Code 200 | Code 503 | Code -1 | Sockets used | Avg latency |
|---|---|---|---|---|---|---|
| sidecar (hardened) | 42 | 60,000 (100%) | **0** | **0** | 16 (perfect keepalive) | 2.630ms |
| ambient-L4 (hardened) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (hardened) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |

**Baseline → hardened comparison**

| Mode | Baseline error rate | Hardened error rate | Change |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503s fully eliminated** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **TCP errors also fully eliminated** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 rate cut by more than half |

> ✅ **Verdict**: this confirms, with measurements, the hypothesis that these 503s stem from a pod not shutting down gracefully before its Endpoint removal propagates — `preStop sleep 10` alone eliminated errors entirely for sidecar and ambient-L4. Ambient-L7 (waypoint) also improved substantially but didn't reach zero — meaning the waypoint's own stale-connection-reuse mechanism (the core §4 finding above) isn't fully solved by workload-side graceful-shutdown tuning alone. If you route through a waypoint, apply this hardening as a baseline and still budget for the residual 503 risk it doesn't eliminate.

### The risk of retry as a mitigation — Test Results (T2)

**Test setup**: a harness of `order` (6 replicas, non-idempotent `POST /order` with a 0.1s in-handler delay, reports its request ID to a `collector`), `collector` (counts distinct request IDs and flags any seen more than once), and `order-client` (continuous POST load at 20 req/s with a unique UUID per request). A retry policy (`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`) was applied via the same Istio VirtualService config to both sidecar (istio-proxy) and ambient-L7 (waypoint). Each mode ran for 300s with concurrent `rollout restart` of the `order` Deployment.

| Mode | Rollout cycles | Requests sent | Client-visible failures (all 3 retries exhausted) | Duplicate executions |
|---|---|---|---|---|
| sidecar (VirtualService retry) | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7 (waypoint retry) | 12 | 7,229 | 21 (0.29%) | **0** |

> ✅ **Verdict**: no duplicate non-idempotent executions were observed for either mode. The low client-visible failure rates confirm retries were actively firing and mostly masking transient rollout-churn errors — yet none of the successful retries resulted in the same logical request being processed twice.

> ⚠️ **This does not mean the race is impossible.** It means it didn't manifest under these specific conditions (perTryTimeout=2s, 20 req/s, 6 replicas, default graceful shutdown, no `preStop` hook). The theoretical mechanism — a retry re-sent after the original request already reached the app but before its response made it back to the caller — requires the connection to drop in a narrow window *after* the app started processing but *before* the response returned. 300s of continuous rollout churn didn't catch an instance of it for either mode, but a production non-idempotent path should still treat mesh-level retry as unsafe by default absent server-side idempotency keys: this test lowers confidence that the race is *common*, it does not establish that it is *safe*.

### Separate raw failures from failures hidden by retry

mTLS data-plane selection and HTTP retry policy are independent decisions. Sidecar Envoy and waypoint Envoy can retry HTTP requests at L7, while ambient ztunnel is an [L4 proxy](https://istio.io/latest/docs/ambient/architecture/data-plane/) that cannot interpret an HTTP 503 or replay an HTTP request. Comparing only final client-visible 503 counts therefore cannot show whether sidecar/waypoint had fewer raw failures or merely hid them through retries.

For a fair rollout comparison, set `attempts: 0` on POST/PATCH write routes and record these dimensions separately:

- HTTP 503, TCP reset/EOF, and connection-refused events before retry
- Envoy `upstream_rq_retry` and `upstream_rq_retry_success` counters
- actual upstream delivery count, including the original request
- final client-visible success/failure after retry processing
- whether the server processed the same idempotency key or command ID more than once

| Data plane | mTLS/encryption meaning | L7 retry location | Recommended use |
|---|---|---|---|
| Istio sidecar | Workload SPIFFE-certificate mTLS | Per-pod Envoy | Conservative baseline for critical non-idempotent paths |
| Istio ambient L4 | HBONE workload mTLS between ztunnels | None | First candidate when only Istio mTLS and L4 policy are required |
| Istio ambient L7 | HBONE plus waypoint Envoy | Shared waypoint | Add only to services requiring HTTP routing or L7 policy |
| Cilium | Identity mutual authentication and transport encryption such as WireGuard/IPsec are selected separately | None in the L3/L4 encryption layer | Existing Cilium data planes needing identity policy and network encryption |

> **Operational rule:** if mTLS is the only requirement, validate ambient L4 first and add waypoints only to services needing L7 policy or east-west HTTP routing. Keep sidecar as the baseline for critical non-idempotent paths when ambient rollout errors, measured with write retries disabled, exceed the workload error budget.

### A note on test isolation

<details>
<summary>Why a dedicated cluster was necessary, and what still went wrong (click to expand)</summary>

An earlier same-day round of T1/T3 testing ran on a shared cluster (`fsi-demo-cluster`) across 4 dedicated namespaces. That cluster's `benchmark` namespace was concurrently running a large Kafka benchmark job sweep across 100+ EC2 instance types, and immediately after the ambient-L7 T1 load completed, every resource that round had created (all 4 namespaces, `istio-system`, and all Istio/Gateway API CRDs) disappeared simultaneously with no confirmed root cause (no matching ArgoCD Application, no Kyverno/Gatekeeper policy found) — leaving T2, T4, and T5 unrun and casting some doubt on the validity of the T1 numbers gathered under that resource contention.

This round used a brand-new, single-tenant cluster (`mesh-isolated-test`, its own VPC, no other workloads) specifically to remove that class of interference, and completed T1–T5 end to end with no resource anomalies. A *different* isolation gap surfaced instead: partway through the first T1 attempt on the new cluster, the local workstation's shared `~/.kube/config` current-context silently switched away from `mesh-isolated-test` to an unrelated cluster — invalidating that attempt (the rollout-restart loop started failing with `namespace not found` once the context flipped, though the in-flight fortio load connection, already established, was unaffected). Namespaces and resources on `mesh-isolated-test` were confirmed to still be fully intact throughout via an explicit kubeconfig check — this was a workstation-level context mix-up, not a cluster-side deletion. The fix: a kubeconfig file scoped only to `mesh-isolated-test`, referenced explicitly by every test script, with a guard that aborts if the context ever drifts again. All final numbers in this document come from the corrected, context-locked reruns.

</details>

## 5. Recommendation: A Tiered Approach

Rather than a binary "sidecar or ambient" choice, we recommend **applying different mesh modes by workload tier**. This matches the use-case guidance in [Ambient Mode](../advanced/01-ambient-mode.md#use-cases), and this round of testing supports it with evidence.

| Tier | Example | Recommendation | Rationale |
|---|---|---|---|
| Core (order creation/matching/settlement, non-idempotent) | Trading API | **Ambient L4-only (no waypoint) or keep sidecar** | §4: 503 rate is ~5x sidecar when routed through a waypoint; L4-only had zero 503s. If L7 features are truly required, sidecar is the more mature option. T2 found no duplicate-execution instances under retry for either mode, but that doesn't establish it's safe — keep retry off by default on this tier regardless of mesh mode. |
| Semi-core (idempotent read APIs) | Price/balance queries | Ambient (L4, L7 if needed) | Idempotent requests are safe to retry, so the waypoint risk matters less |
| Periphery (queries, notifications, batch) | Dashboards, alerting | Adopt ambient aggressively | Maximizes resource/operational benefit; mTLS and rollout behavior verified safe by test |

**Namespace-level mixed deployment** was actually validated in this round of testing — sidecar, ambient-L4, and ambient-L7 namespaces ran concurrently on the same cluster, each independently enforcing STRICT mTLS.

### L4-only's limitations — can I still do canary deployments?

Ambient L4-only has no waypoint, so ztunnel never looks inside the HTTP request. That means **L7 features — HTTP header/path-based routing, retries, circuit breaking, traffic mirroring — cannot be applied to an L4-only service.** Whether this actually blocks canary deployments depends on where the traffic enters from.

> ✅ **Ingress canary is unaffected.** An Istio Ingress Gateway or a Gateway API `Gateway` is always a separate, full Envoy proxy (its own Deployment), regardless of whether the backend workload runs in ambient or sidecar mode. The weighted split between v1/v2 subsets via `VirtualService`/`HTTPRoute` is decided entirely at the gateway; ztunnel (L4) only tunnels the connection to the already-selected destination pod afterward. Canary deployments for externally-exposed APIs work fine with L4-only backends.

> ⚠️ **Mesh-internal (east-west) canary needs L7 on that specific service.** If service A calls service B inside the mesh and you want to split traffic between B-v1 and B-v2 by percentage, something has to make that routing decision at L7 — ztunnel can't. You'd need to either **deploy a waypoint in front of B (switch B to ambient-L7) or run B with a sidecar** for that canary to work.

**Bottom line**: canary deployments for externally-exposed APIs work fine on L4-only. Only reach for a waypoint or sidecar on the specific service that needs mesh-internal canary — which is exactly how the tiered recommendation above is meant to be applied in practice.

**Checklist before adoption**

- [ ] Does the order/matching/settlement path genuinely require L7 features (HTTP routing, retries, traffic split)? If not, ambient L4-only is the leading candidate
- [ ] Have NetworkPolicies been updated to allow the HBONE port (15008)? (§2, verified — and if you're enabling `enableNetworkPolicy` on a live cluster for the first time, recreate existing pods, since enforcement isn't retroactive)
- [ ] Is a retry policy applied to a non-idempotent API path? (§4 — T2 found no duplicate executions in testing, but keep retry disabled by default on non-idempotent paths absent server-side idempotency keys)
- [ ] Has latency been re-measured against your own workload? (§3, verified on this cluster's Graviton nodes — re-measure again if your instance type or workload profile differs materially)

## Appendix: Reproducing These Tests

Below are the actual config files and procedures that produced every number in this document. Copy them directly to reproduce the results on your own cluster.

### A. Cluster provisioning (eksctl)

The dedicated single-tenant cluster was created with eksctl, using fully public subnets with no NAT gateway (a test-only shortcut to avoid needing new Elastic IPs — enable NAT for production clusters).

<details>
<summary>eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: "1.36"
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: "true"

availabilityZones:
  - ap-northeast-2a
  - ap-northeast-2c

vpc:
  nat:
    gateway: Disable

managedNodeGroups:
  - name: mesh-test-ng-arm64
    instanceType: m7g.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 3
    volumeSize: 40
    privateNetworking: false
    labels:
      role: istio-mesh-test
    tags:
      ephemeral: "true"

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: eks-pod-identity-agent
```

</details>

```bash
eksctl create cluster -f eksctl-cluster.yaml
```

### B. Istio install (Gateway API CRDs + ambient profile)

Ambient mode's waypoint is a Gateway API `Gateway` resource, so the Gateway API CRDs must exist before installing Istio.

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml (schedules CNI/ztunnel/istiod onto arm64 nodes)</summary>

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: ambient
  values:
    cni:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
  components:
    pilot:
      k8s:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: kubernetes.io/arch
                  operator: In
                  values: ["arm64"]
```

</details>

### C. Namespace and workload manifests

4 namespaces — `mesh-test-base` (unmeshed, for the latency baseline), `mesh-test-sidecar`, `mesh-test-ambient-l4`, `mesh-test-ambient-l7`. Only the labels differ; everything else is byte-identical.

<details>
<summary>namespaces.yaml</summary>

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-base
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-sidecar
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l4
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l7
  labels:
    istio.io/dataplane-mode: ambient
```

</details>

<details>
<summary>Workload manifest (echo server, 6 replicas + fortio client) — identical across all 4 namespaces, only the namespace field changes</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar   # swap for base / ambient-l4 / ambient-l7
  labels:
    app: echo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: echo
        image: fortio/fortio:1.69.4
        args: ["server", "-http-port", "8080"]
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /fortio/
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  selector:
    app: echo
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: mesh-test-sidecar
  labels:
    app: fortio-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4
        command: ["/usr/bin/fortio"]
        args: ["server", "-http-port", "8081", "-redirect-port", "disabled"]
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

### D. mTLS — PeerAuthentication (§1)

<details>
<summary>peerauth-strict.yaml</summary>

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-sidecar
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l4
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l7
spec:
  mtls:
    mode: STRICT
```

</details>

The ambient-L7 namespace additionally needs a waypoint deployed:

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy (§2)

Enable VPC CNI's eBPF-based NetworkPolicy enforcement via the addon config. As covered in §2, this **only applies to pods created or recreated after this point**.

```bash
aws eks update-addon --cluster-name mesh-isolated-test --addon-name vpc-cni --region ap-northeast-2 \
  --configuration-values '{"enableNetworkPolicy":"true"}' --resolve-conflicts OVERWRITE

# recreate existing pods so the eBPF hooks attach
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-sidecar
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l4
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l7
```

<details>
<summary>NetworkPolicy manifests (Test 1: 8080 only → Test 2: 8080 + 15008)</summary>

```yaml
# Test 1 — this blocks ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4   # apply the same to ambient-l7 and sidecar
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
```

```yaml
# Test 2 — adding the HBONE port restores ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 15008
```

</details>

### F. Running the zero-downtime rollout test (T1, §4)

Run the fortio load generator (foreground, blocks for the test duration) and a `rollout restart` loop (background) concurrently, then stop the loop once the load finishes.

```bash
NS=mesh-test-sidecar   # repeat for ambient-l4, ambient-l7
DUR=600
CLIENT=$(kubectl get pods -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')

# ① rollout-restart loop (background) for DUR seconds
(
  START=$(date +%s)
  while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
    kubectl rollout restart deployment/echo -n "$NS"
    kubectl rollout status deployment/echo -n "$NS" --timeout=60s
  done
) &
ROLLOUT_PID=$!

# ② fortio load generator (foreground, 100qps x 600s = 60,000 requests)
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors http://echo:8080/

kill "$ROLLOUT_PID" 2>/dev/null
```

> 💡 Without `-allow-initial-errors`, fortio aborts the entire run if its warmup request happens to land during a rollout and gets a 503. This flag is required for any load test that overlaps with rollout churn.

**Graceful-shutdown hardening patch** (used for the "after hardening" rerun in §4, applied to the existing Deployments via `kubectl patch --type strategic`):

```yaml
# common to all 3 modes — ambient-l4/l7 get only this patch
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```yaml
# sidecar namespace only, additionally (EXIT_ON_ZERO_ACTIVE_CONNECTIONS)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          proxyMetadata:
            EXIT_ON_ZERO_ACTIVE_CONNECTIONS: "true"
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```bash
kubectl patch deployment/echo -n mesh-test-sidecar --type strategic --patch-file patch-prestop-sidecar.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l4 --type strategic --patch-file patch-prestop-ambient.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l7 --type strategic --patch-file patch-prestop-ambient.yaml
```

### G. Running the latency test (T5, §3)

Same fortio command, run at steady state with no rollout loop.

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Retry / duplicate-execution test harness (T2, §4)

A 3-pod harness — `order` (handles the non-idempotent POST), `collector` (detects duplicate request IDs), `order-client` (continuous load) — deployed identically into the sidecar and ambient-L7 namespaces.

<details>
<summary>ConfigMap — order_server.py / collector.py / client.py</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
data:
  order_server.py: |
    import http.server, urllib.request, time, os

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404); self.end_headers(); return
            rid = self.headers.get("X-Request-Id", "unknown")
            time.sleep(0.1)  # widen the SIGTERM-mid-request race window
            try:
                req = urllib.request.Request(COLLECTOR_URL, data=rid.encode(), method="POST")
                urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"collector report failed for {rid}: {e}", flush=True)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 8080), Handler).serve_forever()
  collector.py: |
    import http.server, json, threading

    lock = threading.Lock()
    counts = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes)}).encode()
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 9090), Handler).serve_forever()
  client.py: |
    import urllib.request, uuid, time, os

    TARGET = os.environ.get("TARGET_URL", "http://order.mesh-test-sidecar.svc.cluster.local:8080/order")
    RPS = float(os.environ.get("RPS", "20"))
    interval = 1.0 / RPS
    sent = 0
    failed = 0
    while True:
        rid = str(uuid.uuid4())
        t0 = time.time()
        try:
            req = urllib.request.Request(TARGET, data=b"{}", method="POST", headers={"X-Request-Id": rid})
            urllib.request.urlopen(req, timeout=3)
            sent += 1
        except Exception:
            failed += 1
        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)
```

</details>

<details>
<summary>order / collector / order-client Deployments + Services</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  selector:
    app: collector
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: collector
        image: python:3.12-alpine
        command: ["python3", "/scripts/collector.py"]
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  selector:
    app: order
  ports:
  - port: 8080
    targetPort: 8080
    name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  replicas: 6
  selector:
    matchLabels:
      app: order
  template:
    metadata:
      labels:
        app: order
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order
        image: python:3.12-alpine
        command: ["python3", "/scripts/order_server.py"]
        env:
        - name: COLLECTOR_URL
          value: "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record"
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-client
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-client
  template:
    metadata:
      labels:
        app: order-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine
        command: ["python3", "/scripts/client.py"]
        env:
        - name: TARGET_URL
          value: "http://order.mesh-test-sidecar.svc.cluster.local:8080/order"
        - name: RPS
          value: "20"
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

Apply the retry policy to the `order` Service (sidecar's istio-proxy and ambient-L7's already-deployed waypoint both pick up this VirtualService):

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
spec:
  hosts:
  - order
  http:
  - route:
    - destination:
        host: order
        port:
          number: 8080
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

The run procedure mirrors the rollout loop in (F), but targets the `order` Deployment, resets the `collector`'s counter before measuring, and queries the duplicate count afterward:

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## References

- [Ambient Mode](../advanced/01-ambient-mode.md) — ztunnel/waypoint architecture, resource comparison vs. sidecar
- [mTLS](../security/01-mtls.md) — STRICT/PERMISSIVE modes, certificate management, NetworkPolicy conflicts
- [Istio VirtualService Retry](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry) — `attempts: 0` and retry conditions
- [Envoy Retry Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter) — retry behavior and observability
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
