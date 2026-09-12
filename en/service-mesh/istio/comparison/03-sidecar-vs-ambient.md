# Sidecar vs Ambient Mode Selection Guide (EKS 1.36 Test Results)

> **Reported test versions**: Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **Original report date**: August 21, 2026 · **Content review**: September 11, 2026

This document preserves the reported mTLS, NetworkPolicy, latency and rollout measurements. Complete raw archives and exact run scripts were not attached, and this review did not recreate the AWS clusters. Configuration and arithmetic checks are not independent replication of these results.

The appendix is now a **revised lab illustration** correcting concrete script/configuration defects. It must not be described as the exact source of the historical numbers. Keep actual software, image digests, policies and artifacts with any new measurements; do not relabel these results as Istio 1.31 or another version.

## Decision Summary

| Requirement | Sidecar | Ambient (L4, no waypoint) | Ambient (L7, waypoint) | Cilium |
|---|---|---|---|---|
| mTLS | Reported STRICT checks passed | Reported STRICT checks passed | Reported STRICT checks passed | Not measured; identity mutual authentication and separately enabled WireGuard/IPsec are not one STRICT-equivalent switch |
| NetworkPolicy | The tested app-port rule worked | The tested flow also needed TCP 15008 | The tested flow also needed TCP 15008 | Not measured; Cilium enforces standard Kubernetes NetworkPolicy and CiliumNetworkPolicy/cluster-wide extensions |
| Reported P50 over baseline |+1.29 ms|+0.04 ms|+1.86 ms|Not measured|
| Untuned rollout |324 HTTP 503 +2 non-HTTP errors /60,000|0 HTTP 503 +195 non-HTTP errors /60,000|1,528 HTTP 503 +84 non-HTTP errors /59,913|Not measured|
| Hardened rollout |0 observed errors /60,000|0 observed errors /60,000|648 HTTP 503 /60,000|Not measured|

Ambient L4 had a small observed P50 difference and fewer non-success responses than the untuned sidecar in this report. Both sidecar and ambient L4 recorded zero errors in the hardened samples. A zero HTTP 503 count alone is not zero downtime, and the waypoint's observed error fraction does not establish an intrinsic failure rate or prove IP reuse as its cause.

Choose required features first, then validate total errors, latency, identity and operations against the workload's budget. The Cilium column describes documented capability only; Cilium was not deployed in this test cycle.

## 1. mTLS — Test Results (EKS 1.36.2, Istio 1.30.2)

The original report names a dedicated `mesh-isolated-test` cluster, its own VPC, Amazon Linux 2023 arm 64 m 7g.xlarge nodes, and namespace-scoped STRICT PeerAuthentication in the three mesh namespaces. Control-plane and worker Kubernetes versions were reported as 1.36.2.

Recorded plaintext Pod-IP attempts failed:

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

Recorded in-mesh Service calls returned HTTP 200 in all three modes. Envoy-related response headers differed, but header presence or absence is not proof of encryption or the full proxy path.

The certificate commands inspected proxies holding/requesting certificates. A proxy is not the certificate issuer:

| Workload | Proxy inspected | SPIFFE ID | Root CA |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | shared |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | shared |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | shared |


The IDs shown are **namespace/ServiceAccount identities**. Echo and client Pods using the same default ServiceAccount share that identity; these are not unique per-Pod SPIFFE IDs. Istiod or the configured CA supplies workload certificates.

The reported negative/positive cases are consistent with STRICT enforcement for those flows. They do not establish coverage of every cluster path, protocol, source or bypass. Ambient uses the Istio CNI network-namespace capture path and HBONE on TCP 15008; sidecar mode uses the workload proxy. See the [mTLS guide](../security/01-mtls.md) for enforcement boundaries.

## 2. NetworkPolicy — Test Results

The report used VPC CNI network-policy enforcement and identified the agent as `v1.3.5-eksbuild.3`. It does not archive the full add-on configuration/version, policy endpoints or node-state evidence. Preserve the reported version in historical results.

**Recorded ingress-port test, after the author reported confirming enforcement:**

| Mode | Result |
|---|---|
| sidecar | ✅ 200 OK — unaffected |
| ambient-L4 | ❌ blocked (`i/o timeout`) |
| ambient-L7 | ❌ blocked (`i/o timeout`) |


**Recorded result after allowing 8080 and HBONE15008:**

| Mode | Result |
|---|---|
| ambient-L4 | ✅ 200 OK — restored |
| ambient-L7 | ✅ 200 OK — restored |


These results show the importance of HBONE for the tested path. They do not mean every existing policy works unchanged with sidecars, or that allowing 15008 is a complete least-privilege ambient policy. Source selectors, waypoint paths, DNS/control-plane egress and the CNI implementation matter. The network policy sees the tunnel port; use appropriate identity/port policy for traffic inside it.

The author reported that recreating Pods after enabling enforcement made a negative control effective. That is an observation for the reported setup, not proof that every current agent can attach only during CNI ADD or that policies are universally non-retroactive. Verify reconciliation and actual enforcement before measuring. Current AWS documentation distinguishes standard startup, which allows traffic until policy is configured, from strict startup, which needs explicit allowances for required dependencies.

Current AWS documentation supports controller-owned Pods, including Deployments, StatefulSets, DaemonSets and Jobs; standalone Pods have additional limitations. Cilium separately supports standard NetworkPolicy and its own policy CRDs. Neither behavior should be inferred from a result on a different implementation.

## 3. Latency — Test Results (T5)

The report describes steady-state Fortio at requested 200 QPS,60 seconds,16 connections, with 12,000 successful requests per case on the same Graviton cluster:

| Case | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (baseline) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (no waypoint) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |


The reported P50 differences are sidecar 1.29 ms, ambient L4 0.04 ms and ambient L7 1.86 ms. These subtractions are correct. Repeated-run variance, resource/placement details and actual result JSON are needed before calling a small difference negligible or applying it to a trading/SLO budget.

The appendix uses a duration-based Fortio command. Requested QPS × duration is nominal offered work, not an exact call-count guarantee; use the recorded DurationHistogram.Count/RetCodes from each run. Do not update historical version labels without rerunning and retaining the experiment.


## 4. Zero-Downtime Rollout — 503 Test Results (core finding)

### Background

Pod termination, endpoint propagation, application/proxy draining, connection pools and timeouts can all affect rollout failures. The original attribution to a destination-IP reuse race and missing ztunnel notification is a **hypothesis**, not a cause established by the displayed counts. Confirm it with proxy response flags, actual upstream hosts, endpoint/Pod UID timelines and connection evidence before attributing the result to one mechanism.

The report used six echo replicas and a Fortio client in each mesh namespace, requested 100 QPS for 600 seconds, and repeatedly restarted the target Deployment. Application manifests were intended to match; injected/shared proxy resources and actual rollout exposure still differed by mode.

### Results

| Mode | Rollout cycles | Requests | 503 count | 503 rate | Non-HTTP results (-1) | Sockets used |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4 (no waypoint) | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7 (waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |


The original article also provided this annotated summary, not the full machine-readable artifacts:

<details>
<summary>Recorded counts (interpretive annotations corrected)</summary>

```text
[sidecar]      42 rollouts, Sockets used: 350 (client concurrency: 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- no HTTP response recorded; not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 counted calls; nominal offered calls: 60,000; avg latency 50.4ms vs. ~2-3ms for the other two modes)

```

</details>

Interpret the values with these limits:

1. The HTTP 503 fractions calculated from the counted calls are 324/60,000 =0.54% and 1,528/59,913 ≈2.55%; their ratio is about 4.72. The original rounded display 0.5%/2.6% and “about 5x” describe this sample, not an intrinsic product multiplier.
2. Ambient L4 had 195 non-HTTP failures, so zero HTTP 503 is not zero failure. Fortio -1 covers non-HTTP outcomes; the specific reset/EOF/timeout cause needs the underlying errors.
3. The 87-call difference from the nominal 60,000 does not establish that 87 started requests never completed. A time-mode run can count fewer calls. Preserve the reported 59,913 and average 50.4 ms without inventing missing-request state.
4. Fortio's SocketCount describes client sockets. It is not a direct measurement of the waypoint's upstream pool. Sixteen sockets would match the configured client concurrency under sustained reuse, but does not prove every upstream connection was healthy.
5. Baseline completed rollout counts were 42/64/65; ambient L7, not L4, had the largest count. Unequal rollout exposure and missing resource/timeline artifacts limit a causal comparison.

### Follow-up: after graceful-shutdown hardening

The original report applied preStop sleep 10 seconds and a 40-second Pod termination grace period to all modes. Sidecar also received EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true and terminationDrainDuration 30s:

| Mode | Rollout cycles | Code 200 | Code 503 | Code -1 | Sockets used | Avg latency |
|---|---|---|---|---|---|---|
| sidecar (hardened) | 42 | 60,000 (100%) | **0** | **0** | 16 | 2.630ms |
| ambient-L4 (hardened) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (hardened) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |


| Mode | Baseline error rate | Hardened error rate | Change |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **0 observed 503s in this sample** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **0 observed non-HTTP errors in this sample** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | 503 rate cut by more than half |


These are observations from the stated samples. Sidecar changed **two factors**, so the result cannot be attributed to preStop alone. The hardened rollout counts 42/38/45 also differ. Workload shutdown tuning improved the reported outcomes but does not prove the remaining waypoint errors share one cause, or that either other mode will always have zero errors.

The grace period includes preStop and container termination. A ten-second sleep provides time, not confirmation that every endpoint update has propagated. In released 1.30.2 code, EXIT_ON_ZERO_ACTIVE_CONNECTIONS first waits the configured minimum drain period and then polls downstream-listener connection statistics every second. That branch does not use the ordinary terminationDrainDuration timer; Kubernetes termination limits and observation errors still matter. Do not describe it as immediate exit or an unconditional 30-second maximum.

### The risk of retry as a mitigation — Test Results (T2)

The original report described a six-replica order service, collector and client, with a 20-request/s setting,300-second runs and a VirtualService policy with three retries and a two-second per-try timeout. The following values are preserved as **reported, not independently reproduced**:

| Mode | Rollout cycles | Requests sent | Reported client-visible failures | Duplicate reports (as reported) |
|---|---|---|---|---|
| sidecar (VirtualService retry) | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7 (waypoint retry) | 12 | 7,229 | 21 (0.29%) | **0** |


The original appendix cannot substantiate these interpretations:

- Its single sequential client ran indefinitely, never printed statistics and incremented sent only on success. At a 20-iteration/s cap, a 300-second run cannot account for 9,135 or 7,229 iterations; the 0.1-second server delay further constrains achieved rate.
- A three-second client timeout can expire before the nominal original-plus-three two-second attempts finish. A final failure does not show that all retries were exhausted.
- Collector report errors were swallowed while the order server returned 201. The counter reset overlapped an already running client, and copied ambient manifests still pointed at the sidecar namespace's services.
- X-Request-Id is a proxy/tracing identifier, not necessarily an immutable business command ID. A zero duplicate-report count with incomplete observation does not prove zero repeated business execution.
- Low final failure rates do not establish that retries fired. Effective routes, retry counters and actual deliveries were not included in the report.

The revised appendix makes the driver bounded and observable, uses a separate business identifier, and treats observer failure as an unknown/error outcome. It does not repair the provenance of the old numbers. Its in-memory collector is not a durable transaction ledger or an idempotency implementation.

### Separate raw failures from failures hidden by retry

mTLS data-plane selection and HTTP retry policy are independent decisions. Sidecar Envoy and waypoint Envoy can retry HTTP requests at L7; ztunnel is an [L4 proxy](https://istio.io/latest/docs/ambient/architecture/data-plane/) and cannot interpret HTTP 503 or replay an HTTP request.

For a fair baseline, explicitly set attempts:0 on write routes such as POST/PUT/PATCH/DELETE and measure these separately:

- HTTP errors and non-HTTP failures before retry.
- Envoy upstream_rq_retry and upstream_rq_retry_success counters from the actual relevant proxy/cluster.
- Upstream delivery/observer record counts, including original requests.
- Final client success/failure and complete client accounting.
- Repeated stable business command IDs, observer failures and observer restarts.

| Data plane | mTLS/encryption meaning | L7 retry location | Recommended use |
|---|---|---|---|
| Istio sidecar | Workload SPIFFE-certificate mTLS | Per-pod Envoy | Conservative baseline for critical non-idempotent paths |
| Istio ambient L4 | HBONE workload mTLS between ztunnels | None | First candidate when only Istio mTLS and L4 policy are required |
| Istio ambient L7 | HBONE plus waypoint Envoy | Shared waypoint | Add only to services requiring HTTP routing or L7 policy |
| Cilium out-of-band + WireGuard/IPsec | Identity mutual authentication and transport encryption such as WireGuard/IPsec are selected separately | None in the L3/L4 encryption layer | Existing Cilium data planes needing identity policy and network encryption |


The Cilium entry concerns its L3/L4 authentication/encryption layer; it does not mean Cilium has no optional L7 proxy features. None of its performance or rollout behavior was measured here.

Cilium 1.20.1 also provides a separate [ztunnel transparent-encryption beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), selected with `encryption.type: ztunnel`. It provides TCP workload mTLS with namespace enrollment; both endpoints must be enrolled. It excludes ClusterMesh and host-networked Pods, and the released guide warns that ordinary L4 policies do not work on this path except when targeting HBONE port 15008. This is a distinct deployment choice with its own CA/bootstrap requirements.

The ztunnel beta was not part of the measurements reported in this chapter.

> **Operational rule:** if mTLS is the only requirement, validate ambient L4 first and add waypoints only to services needing L7 policy or east-west HTTP routing. Keep sidecar as a baseline for critical non-idempotent paths when ambient total errors, measured with write retries disabled, exceed the workload error budget. Application retries and idempotency still need independent control.

### A note on test isolation

The original author reported interference/resource disappearance on a shared cluster and a separate workstation current-context change during an initial dedicated-cluster attempt. No forensic archive is attached, so these reports do not identify a deletion cause or establish an Istio defect.

The useful requirement is explicit isolation: a controlled test cluster, dedicated kubeconfig/context/server checks, complete resource inventory, and retained artifacts. The former appendix omitted the context guards described in its narrative. The revised procedure makes them explicit. Namespaces alone are not a guarantee of independent CPU/network or control-plane conditions.

## 5. Recommendation: A Tiered Approach

Workload tiers are planning labels, not safety guarantees:

| Workload requirement | Candidate | Validation needed |
|---|---|---|
| mTLS and L4 policy only | Ambient L4 first; retain a proven sidecar baseline where appropriate | Actual identity, NetworkPolicy/inner-port enforcement, total failures and latency |
| HTTP routing or L7 authorization | The appropriate waypoint, caller-side sidecar or gateway | Correct policy attachment, effective configuration and workload error budget |
| Critical non-idempotent commands | Any selected data plane with explicit write-retry policy and server-side correctness controls | Stable business IDs, durable idempotency/transactions, response-loss and recovery tests |
| Read APIs, notifications and batch | Choose by actual semantics and required features | Notifications/batch can have side effects; even retry-safe reads can amplify load |

The reported coexistence of three mesh namespaces is useful, but does not prove every mixed deployment, workload or policy combination safe.

### L4-only's limitations — can I still do canary deployments?

ztunnel does not provide per-HTTP-request header/path routing, mirroring or HTTP retry. An **Istio-managed** ingress gateway can make L7 routing decisions before forwarding to ambient backends. Gateway API itself is an API, not necessarily an Envoy Deployment: behavior depends on the GatewayClass/controller.

Istio VirtualService can select DestinationRule subsets; standard HTTPRoute backendRefs normally select Services. Do not describe those as the same subset API.

For east-west HTTP request routing, the L7 decision must occur on the actual caller/gateway/waypoint path. Adding only a sidecar to destination B does not make an ambient-L4 caller choose B-v 1/B-v 2 by an outbound HTTP policy. Use B's waypoint, a suitable caller-side proxy or another explicitly designed L7 hop. L4 connection-level distribution and replica-based rollout strategies are different from per-request HTTP splitting.

Review actual feature requirements, CNI/policy behavior, write retries and the workload's own measurements. The following lab illustration collects new evidence; it cannot retroactively establish the original report's missing facts.


## Appendix: Reproducing These Tests

This is a revised procedure for a controlled follow-up, not a copy-paste guarantee of the original results. Local checks cover syntax, configuration generation and the Python observer/client behavior. Cluster scheduling, mesh policy attachment, CNI enforcement and measurement completeness still require validation in the actual lab.

### A. Cluster provisioning (eksctl)

The following is the **archived input** described by the original report. It explains the node/network choices; this audit did not execute it:

<details>
<summary>Recorded eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: '1.36'
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: 'true'
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
    ephemeral: 'true'
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
- name: eks-pod-identity-agent
```

</details>

Minor Kubernetes version, unpinned add-ons and current AMI selection do not recreate the exact original control-plane patch, node image or agent versions. A public-subnet/no-NAT test layout is not a production prescription; private endpoints, IPv 6 or NAT-based egress depend on the actual network requirements.

Use an approved, isolated test cluster for new work and record its ARN/API endpoint, node/AMI/kernel versions, CNI/agent configuration and resource inventory. Do not activate previously dormant policies or replace shared CRDs on an unrelated cluster.

### B. Istio install (Gateway API CRDs + ambient profile)

Set these inputs from the intended cluster record. The helpers explicitly select the kubeconfig/context and recheck its API-server mapping:

```bash
set -euo pipefail
: "${TEST_KUBECONFIG:?Set the dedicated kubeconfig file}"
: "${TEST_CONTEXT:?Set its explicit test context}"
: "${ISTIOCTL_BIN:?Set the path to the intended Istio 1.30.2 CLI}"
: "${EXPECTED_API_SERVER:?Set the approved API-server URL}"
: "${NS:?Select the test namespace}"
: "${RUN_DIR:?Set a new artifact directory for this run}"
case "$NS" in
  mesh-test-base|mesh-test-sidecar|mesh-test-ambient-l4|mesh-test-ambient-l7) ;;
  *) echo "Unexpected test namespace" >&2; exit 1 ;;
esac
check_mesh_context() {
  local actual
  actual=$(kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}') || return 1
  if [ "$actual" != "$EXPECTED_API_SERVER" ]; then
    echo "API-server mismatch; stopping" >&2
    return 1
  fi
}
kmesh() {
  check_mesh_context &&
    kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
imesh() {
  check_mesh_context &&
    "$ISTIOCTL_BIN" --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
check_mesh_context
mkdir -p "$RUN_DIR"
```

This prevents reliance on the shared current-context value; it does not protect against every concurrent cluster or credential change. Keep the dedicated file controlled and retain the verified cluster identity.

The reported version was Istio 1.30.2. The original appendix's Gateway API1.1.0 compatibility statement was not backed by an installed-bundle archive. Released 1.30.2 dependencies/conformance use 1.5.1. For the revised Gateway/HTTPRoute cases, use the matching standard bundle after checking other installed controllers; do not treat the latest catalog entry as compatibility evidence.

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

L4 ambient alone does not require a waypoint resource. This experiment includes an L7 case, so compatible Gateway API resources are needed before waypoint creation. Use the intended Istio CLI/version and supported upgrade path; do not silently upgrade a historical test to a new release.

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
                values:
                - arm64
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
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
                  values:
                  - arm64
```

This overlay's CNI, ztunnel and Istiod arm 64 affinity was checked in a native 1.30.2 offline render. A render is not a deployment test.

### C. Namespace and workload manifests

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

The following application template is for one case. Change every metadata.namespace to the selected case and apply with explicit `-n "$NS"` so a mismatch fails. Keep application settings equivalent, but record the different injected/shared proxy configuration too.

<details>
<summary>Revised echo and Fortio workload template</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
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
        kubernetes.io/os: linux
      containers:
      - name: echo
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        args:
        - server
        - -http-port
        - '8080'
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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        command:
        - /usr/bin/fortio
        args:
        - server
        - -http-port
        - '8081'
        - -redirect-port
        - disabled
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

The new illustration pins the reported Fortio version to a registry digest checked during this review and names HTTP ports explicitly. The original report did not archive its image digest or all protocol settings; these revisions are not evidence that the old run used identical bytes. The Fortio image is scratch-based: use its binary, not assumed sh/curl/cat utilities inside it.

### D. mTLS — PeerAuthentication (§1)

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

For the L7 namespace:

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

Verify actual Pod injection/enrollment, certificates and the Service traffic path before load. A direct Pod-IP plaintext rejection tests L4 enforcement; it does not prove that every possible call traverses a waypoint or an L7 policy.

### E. NetworkPolicy (§2)

Merge the network-policy opt-in into the **reviewed existing** add-on configuration through its owner:

```json
{"enableNetworkPolicy":"true"}
```

Record the actual CNI/agent version and standard/strict startup mode. Do not blindly replace other add-on settings with a one-field update and OVERWRITE. Check generated policy endpoints and negative-control traffic after reconciliation. Recreate the intended test Pods if required by the installed setup; the historical observation is not a universal non-retroactivity rule.

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

Test 1 and Test 2 are successive alternatives for the same selected workload/policy name:

```yaml
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
```

```yaml
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

Apply each in the selected case namespace. These deliberately source-unrestricted port rules are a reachability experiment, not complete tenant isolation. Other selected policies combine with them. Test the actual DNS, control-plane, source and inner-port/identity requirements rather than assuming one allowed tunnel port preserves every original policy boundary.


### F. Rollout + 503 test (T1, §4)

For each case, start with ready workloads and a new artifact directory. The bounded loop below records rollout intervals alongside Fortio's actual results. Its start is not an atomic barrier with the load generator: use the timestamps to identify the overlapping exposure, including a rollout that finishes after load stops.

```bash
# Run after loading the context helpers above. Requires GNU timeout.
DUR=600
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
kmesh -n "$NS" rollout status deployment/fortio-client --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
STOP_FILE="$RUN_DIR/stop-rollouts"
test ! -e "$STOP_FILE"
trap 'touch "$STOP_FILE"' EXIT INT TERM
(
  begin=$(date +%s)
  while [ $(( $(date +%s) - begin )) -lt "$DUR" ] && [ ! -e "$STOP_FILE" ]; do
    cycle_start=$(date +%s)
    kmesh --request-timeout=15s -n "$NS" rollout restart deployment/echo || exit 1
    kmesh --request-timeout=75s -n "$NS" rollout status deployment/echo \
      --timeout=60s || exit 1
    printf '%s,%s\n' "$cycle_start" "$(date +%s)" >> "$RUN_DIR/rollout-times.csv"
  done
) >"$RUN_DIR/rollouts.log" 2>&1 &
ROLLOUT_PID=$!

check_mesh_context
load_status=0
timeout --signal=TERM --kill-after=5s "$((DUR+30))s" \
  kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
  -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio.json" 2>"$RUN_DIR/load.log" || load_status=$?
touch "$STOP_FILE"
rollout_status=0
wait "$ROLLOUT_PID" || rollout_status=$?
trap - EXIT INT TERM
if [ "$load_status" -ne 0 ] || [ "$rollout_status" -ne 0 ]; then
  echo "Invalid run: inspect load/rollout logs" >&2
  exit 1
fi
jq -e '.DurationHistogram.Count > 0 and (.RetCodes | type == "object")' \
  "$RUN_DIR/fortio.json" >/dev/null
```

Keep the result JSON, both stderr logs, rollout intervals, Pod/endpoint timelines and proxy configuration. A timeout or failed rollout makes the run incomplete; do not silently treat partial output as a clean sample. `SocketCount` measures Fortio's client-side sockets.

For the follow-up, merge the appropriate fragment below into the existing echo Deployment. These are **strategic-merge fragments**, not standalone Deployment manifests: the first is the common application change; the second also changes sidecar proxy shutdown settings.

```yaml
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
---
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

Repeat the experiment with a new run directory and label the changed factors. The kubelet sleep lifecycle hook is usable on the reported Kubernetes version; check older clusters' feature support separately. The Pod grace period includes preStop. A sleep does not acknowledge endpoint convergence, and the proxy's exit-on-zero path does not guarantee a fixed 30-second drain maximum.

### G. Latency test (T5, §3)

Use stable workloads without the rollout loop:

```bash
# No rollout loop for this steady-state case.
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
kmesh -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio-latency.json" 2>"$RUN_DIR/latency.log"
jq '{Version, RequestedQPS, ActualQPS, ActualDuration,
     count: .DurationHistogram.Count, RetCodes, SocketCount}' \
  "$RUN_DIR/fortio-latency.json"
```

Report actual counts, achieved QPS, error codes, all required percentiles and run-to-run variance. Requested 200 QPS for 60 seconds is a load setting, not proof of exactly 12,000 successful calls.

### H. Duplicate-execution observation (T2, §4)

The following revised toy harness replaces the original unbounded client and silent observer failures. It records a stable `Idempotency-Key` for each logical client command; Envoy tracing headers are not used as the business identifier. It intentionally **does not deduplicate** commands or implement a durable business transaction.

Save the ConfigMap as t 2-configmap.yaml:

<details>
<summary>Bounded client, order server and in-memory observer</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar
data:
  order_server.py: |
    import http.server
    import os
    import time
    import urllib.error
    import urllib.request

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector:9090/record")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            command_id = self.headers.get("Idempotency-Key", "").strip()
            if not command_id:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.1)  # Processing delay before the observer record, not a post-commit delay.
            try:
                request = urllib.request.Request(
                    COLLECTOR_URL, data=command_id.encode(), method="POST"
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                # The record may have committed before an ambiguous transport failure.
                print(f"observer outcome unknown for {command_id}: {error}", flush=True)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
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
            if self.path != "/record":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                deliveries = sum(counts.values())
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes)}).encode()
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
    import json
    import math
    import os
    import time
    import urllib.error
    import urllib.request
    import uuid


    def run():
        target = os.environ.get("TARGET_URL", "http://order:8080/order")
        rps = float(os.environ.get("RPS", "20"))
        duration = float(os.environ.get("DURATION_SECONDS", "300"))
        timeout = float(os.environ.get("TIMEOUT_SECONDS", "12"))
        if not all(math.isfinite(value) and value > 0 for value in (rps, duration, timeout)):
            raise ValueError("RPS, DURATION_SECONDS and TIMEOUT_SECONDS must be finite and positive")
        interval = 1.0 / rps
        attempted = succeeded = failed = 0
        start = time.monotonic()
        deadline = start + duration
        while time.monotonic() < deadline:
            tick = time.monotonic()
            command_id = str(uuid.uuid4())
            attempted += 1
            request = urllib.request.Request(
                target, data=b"{}", method="POST", headers={"Idempotency-Key": command_id}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response.read()
                    if 200 <= response.status < 300:
                        succeeded += 1
                    else:
                        failed += 1
            except urllib.error.HTTPError as error:
                error.close()
                failed += 1
            except (urllib.error.URLError, TimeoutError, OSError):
                failed += 1
            pause = min(interval - (time.monotonic() - tick), deadline - time.monotonic())
            if pause > 0:
                time.sleep(pause)
        elapsed = time.monotonic() - start
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "requested_rps_cap": rps,
            "elapsed_seconds": elapsed,
            "achieved_rps": attempted / elapsed if elapsed else 0,
        }


    if __name__ == "__main__":
        print(json.dumps(run()), flush=True)
```

</details>

The order server's 0.1-second delay occurs **before** recording, so it is not a test of response loss after a committed transaction. A collector timeout/error returns 503 and leaves an unknown outcome: the observer may have recorded before its response was lost. A client success means an observer acknowledgment in this toy model, not proof of real business exactly-once execution.

Save the first four resources below as t 2-servers.yaml and the final Job as order-client-job.yaml. Use a fresh collector with no earlier clients for each case, and change every metadata.namespace consistently. Short Service names keep calls within the selected namespace.

<details>
<summary>Collector/order Deployments, Services and bounded client Job</summary>

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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: collector
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/collector.py
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 9090
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
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
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: order
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/order_server.py
        env:
        - name: COLLECTOR_URL
          value: http://collector:9090/record
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: batch/v1
kind: Job
metadata:
  generateName: order-client-
  namespace: mesh-test-sidecar
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 360
  template:
    metadata:
      labels:
        app: order-client
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/client.py
        env:
        - name: TARGET_URL
          value: http://order:8080/order
        - name: RPS
          value: '20'
        - name: DURATION_SECONDS
          value: '300'
        - name: TIMEOUT_SECONDS
          value: '12'
        volumeMounts:
        - name: scripts
          mountPath: /scripts
          readOnly: true
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

The Job has no automatic retry and uses the native-sidecar annotation so a selected sidecar injection does not prevent Job completion. That annotation does not enroll an ambient Pod or itself enable sidecar injection. Verify the actual Job Pod and namespace enrollment. The revised templates add TCP readiness checks and pin the Python image to a registry digest verified during review; the old report did not archive that digest. Local Python behavior was tested with the host Python 3.9 standard library; this review did not execute the Python 3.12 container or deploy these resources.

The client is **sequential**: RPS20 caps new attempts, not a constant open-loop 20 QPS guarantee. The 0.1-second service delay and failures lower achieved throughput. DURATION_SECONDS bounds new request starts; the last request can extend the elapsed time by its timeout. The final JSON includes attempted/succeeded/failed and achieved_rps, with attempted = succeeded + failed.

Start with explicit no-retry routes for the order command **and the observer write**, saved together as order-no-retry.yaml:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: collector-observer-no-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - collector
  http:
  - name: observer-record
    match:
    - method:
        exact: POST
      uri:
        exact: /record
    route:
    - destination:
        host: collector
        port:
          number: 9090
    timeout: 10s
    retries:
      attempts: 0
```

For a deliberately unsafe **isolated retry experiment only**, replace the order policy with order-retry-experiment.yaml below. Keep the collector no-retry policy. The experiment is intended to reveal possible repeated delivery; it is not a recommendation to retry production writes.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

Three retries permit up to four attempts. The two-second per-try setting and ten-second route timeout interact with connection/setup time; the twelve-second client timeout provides a larger observation window but does not prove all attempts happened. Capture the actual proxy configuration and retry counters.

In the reported Istio 1.30 line, VirtualService use with ambient is Alpha, and mixing it with Gateway API traffic configuration is unsupported. Do not install a competing HTTPRoute in this experiment. Check effective routes on the actual client sidecar or destination waypoint; ambient L4 alone cannot enforce this HTTP retry policy.

```bash
# A fresh collector and no earlier client must be running for this case.
# Replace metadata.namespace in every input with NS; explicit -n catches mismatches.
kmesh -n "$NS" apply -f t2-configmap.yaml -f t2-servers.yaml -f order-no-retry.yaml
kmesh -n "$NS" rollout status deployment/collector --timeout=120s
kmesh -n "$NS" rollout status deployment/order --timeout=120s
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-before.json"

# For the deliberate retry experiment only, replace the no-retry policy with
# order-retry-experiment.yaml and verify the effective proxy configuration first.
JOB_RESOURCE=$(kmesh -n "$NS" create -f order-client-job.yaml -o name)
JOB_NAME=${JOB_RESOURCE#*/}
if ! kmesh -n "$NS" wait --for=condition=complete "$JOB_RESOURCE" --timeout=370s; then
  kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client-failed.log" || true
  echo "Invalid/incomplete client run" >&2
  exit 1
fi
kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client.json"
jq -e '.attempted > 0 and .attempted == (.succeeded + .failed)' \
  "$RUN_DIR/client.json" >/dev/null
kmesh -n "$NS" get pods -l "batch.kubernetes.io/job-name=$JOB_NAME" \
  -o json >"$RUN_DIR/client-pods.json"
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-after.json"
kmesh -n "$NS" logs -l app=order -c order --prefix --tail=-1 \
  --max-log-requests=10 >"$RUN_DIR/available-order.log"
kmesh -n "$NS" exec deployment/collector -c collector -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9090/dupes', timeout=5).read().decode())" \
  >"$RUN_DIR/observer.json"
```

This driver handles setup and accounting; it does **not** launch the order rollout loop. For a churn experiment, coordinate a separately bounded version of §F targeting deployment/order over the 300-second client window, and retain both timelines. Without that coordination, the output is a steady-state observer test.

Do not reset the observer while a client is running. Compare collector Pod UIDs and restart counts before/after, retain every order/observer error, and use log retention that survives deleted Pods. The command above retrieves only logs still available from current Pods. An observer restart, missing logs or observer error invalidates a claim of complete duplicate detection. A durable per-command ledger and controlled post-commit response-loss tests are needed to investigate real transaction safety.

## References and verification boundaries

- [Istio 1.30.2 release](https://github.com/istio/istio/releases/tag/1.30.2), [released dependencies](https://github.com/istio/istio/blob/1.30.2/go.mod), and [proxy shutdown implementation](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Istio 1.30 ambient L7 feature status](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md) and [traffic management](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/manage-traffic/index.md)
- [Kubernetes container lifecycle hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/) and [native sidecar containers](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Amazon EKS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) and [configuration/startup modes](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Cilium policy support](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Fortio 1.69.4 source and usage](https://github.com/fortio/fortio/tree/v1.69.4) and [container build](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

Configuration generation, schema checks, arithmetic and local HTTP tests support the concrete corrections above. They do not reproduce the historical EKS measurements or establish production performance, compatibility with an untested add-on combination, or exactly-once business execution.
