# Istio Advanced Topics Quiz

> **Verification baseline**: Istio 1.31.0, Kubernetes 1.32–1.36, Argo Rollouts 1.10.0
> **Last reviewed**: September 11, 2026

The questions distinguish configuration, runtime behavior and evidence. Examples are independent; select the relevant topology and retain the prerequisites in the linked guide. Historical arithmetic inputs below are not current pricing or new benchmark results.

## Multiple Choice Questions (1–5)

### Question 1: Ambient and Sidecar Modes

Which architectural change can reduce per-workload proxy overhead in ambient mode?

- A. Ambient always provides more features than sidecars.
- B. A per-node ztunnel handles L4 traffic, with separately deployed waypoints for required L7 processing.
- C. Installation is guaranteed to be ten times faster.
- D. Every policy becomes stronger without configuration changes.

<details>
<summary>Show Answer</summary>

**Answer: B**

Ambient removes the requirement for one sidecar proxy in every enrolled workload Pod. ztunnel supplies the L4 secure overlay; destination waypoint enrollment and the supported L7 policies determine the additional processing path. A waypoint is not simply a universal shared hop that either ztunnel may choose arbitrarily.

| Aspect | Correct comparison |
|---|---|
| CPU/memory | Measure equivalent traffic, policy, telemetry, node count and waypoint replicas. No universal 98% saving. |
| Enrollment | Ambient can enroll existing sidecar-free Pods without an application restart; removing an existing sidecar requires workload replacement. |
| Features | Support differs. Waypoint EnvoyFilter is unsupported; ambient multicluster has its own Beta topology limits. |
| Maturity | Ambient core became GA in Istio 1.24; that does not make every later capability GA. |
| Security | mTLS and policy depend on the actual traffic path and supported policy attachment; require waypoint traversal where L7 enforcement is mandatory. |

For example, **assumed** 1,000 sidecars at 50 MB/0.1 vCPU total 50,000 MB/100 vCPU. Ten assumed ztunnels at 50 MB/0.1 vCPU plus one 200 MB/0.5 vCPU waypoint total 700 MB/1.5 vCPU. The arithmetic reductions are 98.6%/98.5%; these arbitrary inputs are neither benchmarks nor capacity guarantees.

Enrollment after installing the supported ambient components and reviewing any existing revision/injection labels:

```bash
kubectl label namespace ambient-demo istio.io/dataplane-mode=ambient --overwrite
kubectl get daemonset ztunnel -n istio-system
istioctl ztunnel-config workloads --workload-namespace ambient-demo
```

The namespace must already exist, be intended for ambient, and have compatible workloads. These commands do not install the CNI/ztunnel, configure waypoints or safely migrate injected Pods by themselves.

[Ambient guide](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

### Question 2: Multicluster Discovery

Which component reads the authorized Kubernetes service registries and generates proxy discovery configuration in an Istio sidecar multicluster mesh?

- A. Istiod
- B. CoreDNS alone
- C. An east-west gateway alone
- D. A ServiceEntry object alone

<details>
<summary>Show Answer</summary>

**Answer: A**

Each primary Istiod reads the Kubernetes APIs it is authorized to access. In primary-remote, remote workloads use the primary control plane; the remote installation is not a second full Istiod managed by a “super-primary.” In multi-primary, primaries have their own control planes and authorized remote discovery.

Istiod generates/distributes proxy configuration; it does not copy VirtualService/DestinationRule Kubernetes objects or application data into every cluster. Distribute configuration separately. Shared trust must be deliberately configured; equal meshID values do not create a common CA.

CoreDNS can use forwarding and other configurations but is not Istio's cross-cluster registry. Gateways transport cross-network traffic. ServiceEntry adds registry entries, including external or otherwise explicitly registered services.

Generate the actual remote secret instead of inventing a `data.kubeconfig` field:

```bash
# After the remote installation; contexts must identify the intended clusters.
istioctl create-remote-secret --context="$CTX_CLUSTER2" --name=cluster2   | kubectl --context="$CTX_CLUSTER1" apply -f -
```

The secret grants the primary access to the **remote API**. Protect its credentials and review the generated RBAC. It neither joins networks nor replicates policy objects.

[Multicluster guide](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### Question 3: EnvoyFilter Purpose

What is EnvoyFilter's main purpose?

- A. Create Kubernetes Services.
- B. Automatically generate every VirtualService.
- C. Customize selected generated Envoy proxy configuration.
- D. Replace all Istiod installation settings.

<details>
<summary>Show Answer</summary>

**Answer: C**

Prefer supported routing, telemetry, security or extension APIs for the task. EnvoyFilter is appropriate when those APIs do not provide a needed supported behavior and the generated configuration is understood. For example, this sidecar-only Lua filter changes an illustrative outbound request header:

```yaml
apiVersion: networking.istio.io/v1
kind: EnvoyFilter
metadata:
  name: quiz-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                handle:headers():replace("x-quiz-example", "yes")
              end
```

The namespace and selector must match the intended proxies. No selector generally covers proxies in the resource's namespace; a root-namespace resource can have mesh-wide scope. Do not write two `workloadSelector` keys in one YAML object. A header inserted by Lua is not authenticated identity.

Other use cases require complete dependencies: a Wasm module needs a verified artifact/runtime and mounting or a supported WasmPlugin delivery path; global rate limiting needs a reachable service, matching descriptors and failure policy. Merely inserting a filter name does not provide those systems. EnvoyFilter is not supported on ambient waypoints.

Validate the exact Istio/Envoy version, effective scope, filter order, typed payload and generated proxy configuration during upgrades. Installation values for Istiod remain Helm/istioctl configuration; IstioOperator YAML is still an istioctl input, although the in-cluster operator was removed.

[EnvoyFilter guide](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>

### Question 4: Sidecar Injection

Which controls can disable automatic sidecar injection for newly created Pods?

- A. Explicitly set the namespace label `istio-injection=disabled`.
- B. Set the workload Pod-template label `sidecar.istio.io/inject: "false"`.
- C. Restart Istiod without changing configuration.
- D. Both A and B.

<details>
<summary>Show Answer</summary>

**Answer: D**

```bash
kubectl label namespace example istio-injection=disabled --overwrite
kubectl get namespace example -L istio-injection,istio.io/rev
```

This fragment belongs under the existing Deployment's spec; retain its image, selectors and other fields:

```yaml
spec:
  template:
    metadata:
      labels:
        sidecar.istio.io/inject: 'false'
```

A disabling namespace or Pod label wins. In particular, a Pod opt-in does **not** override `istio-injection=disabled`. Removing only `istio-injection=enabled` is not universal disablement: revision labels, Pod opt-in and injector defaults must also be inspected. The old inject annotation is deprecated in favor of the label; avoid conflicting old/new settings.

Changes affect new Pods, not proxies already injected. Use the workload's reviewed rollout to change existing Pods. A mixed namespace can enable injection while selected workload templates opt out; that opt-out also changes the workload's mesh/security participation.

```bash
kubectl get pod "$POD" -n "$NAMESPACE" -o json   | jq '{containers: [.spec.containers[].name],
         initContainers: [.spec.initContainers[]? | {name, restartPolicy}]}'
```

A native sidecar can appear in initContainers with `restartPolicy: Always`; checking only ordinary containers or expecting exactly `2/2` Ready is insufficient. Ambient enrollment is a separate mechanism.

[Injection guide](../../../service-mesh/istio/advanced/07-sidecar-injection.md)

</details>

### Question 5: Argo Rollouts Traffic Splitting

Which Istio **declarative resource** contains the HTTP route weights updated by Argo Rollouts?

- A. The Rollouts controller process
- B. VirtualService
- C. A Kubernetes Service alone
- D. Gateway alone

<details>
<summary>Show Answer</summary>

**Answer: B**

Rollouts updates the named route weights, Istiod translates the configuration, and **Envoy executes** routing. VirtualService is not a process handling packets. Ten percent is a probabilistic routing weight, not a guarantee that exactly ten of every hundred requests reach the canary. Retries and long-lived connections affect observations.

A subset-based alternative requires one Service selecting the application, both subsets, and Rollouts ownership of their revision labels:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
```

Merge this strategy fragment into the complete matching Rollout from the guide; do not apply it as an incomplete resource or combine it with a different host-level splitting strategy:

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

The named Service `test`, full Rollout selector/template, controller/RBAC and namespace `rollouts-demo` must exist. Rollouts updates the subset revision labels. `retries.attempts: 0` prevents mesh retries on this route; application retry behavior is separate.

Traffic analysis happens only when configured. Automatic analysis failure can abort a rollout, but does not reverse application/database side effects. Use the guide's complete host-level or subset example, one strategy at a time.

[Argo Rollouts guide](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

## Short Answer Questions (6–10)

### Question 6: Ambient Resource and Cost Analysis

Using the original assumed inputs—500 Pods, five r5.xlarge nodes, 730 hours/month and $0.252/node-hour—calculate proxy resources and explain whether bill savings follow. Each sidecar uses 50 MB/0.1 vCPU; each ztunnel uses 50 MB/0.1 vCPU; the assumed waypoint uses 200 MB/0.5 vCPU.

<details>
<summary>Sample Answer</summary>

The price and resource figures are **exercise inputs**, not current AWS quotes or measured Istio usage. MB/GB arithmetic below is decimal.

| Resource | Sidecars | Ambient on the assumed five nodes | Arithmetic reduction |
|---|---|---|---|
| Memory | 500 × 50 = 25,000 MB | 5 × 50 + 200 = 450 MB | 24,550 MB, 98.2% |
| CPU | 500 × 0.1 = 50 vCPU | 5 × 0.1 + 0.5 = 1 vCPU | 49 vCPU, 98% |

An r5.xlarge has four vCPUs and 32 GiB of memory. Five nodes provide only 20 vCPUs before system/application needs, so the assumed 50-vCPU sidecars already make this fixed five-node scenario infeasible. A proxy-only CPU lower bound is ceil(50/4) = 13 nodes; this excludes application CPU, system reservations, memory, IP limits, placement and resilience requirements.

Do not compare that 13-node lower bound with “one ambient node” while still charging ztunnel resources for five nodes. Recalculate ztunnel resource demand for the **actual retained node count**, and include waypoint HA/traffic capacity and all other workloads.

At the assumed rate:

- One node-month costs `0.252 × 730 = $183.96`.
- Five unchanged nodes cost `$919.80/month` in either mode: measured proxy headroom alone does not reduce this bill.
- Thirteen node-months would cost `$2,391.48`, correcting the earlier arithmetic; this is not a proven required production fleet.
- If validated fleets contain Nₛ and Nₐ nodes, the compute difference is `(Nₛ − Nₐ) × $183.96/month`, before other costs or commitments.

Include EKS/control-plane charges, load balancers, cross-AZ/Region transfer, storage, telemetry and actual purchase commitments in a full comparison. Sidecars do use local communication; ambient does not automatically eliminate network charges or OOMs.

For the exercise's $6,000 migration effort, payback is `6000 / S` months only if measured net monthly savings S are positive. With unchanged billed capacity, S may be zero and that payback calculation has no finite result. Do not assert the former 92% bill saving or 2.7-month ROI from proxy arithmetic alone.

[Ambient guide](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>


### Question 7: Primary-Remote EKS Mesh

Describe the primary-remote design for two existing EKS clusters in us-east-1 and us-west-2, including discovery, trust, network prerequisites and a cross-cluster verification example.

<details>
<summary>Sample Answer</summary>

This is a **sidecar** design. Ambient's current multicluster Beta supports multi-primary/multi-network, not this primary-remote model. The primary Istiod serves remote proxies; there is no full remote Istiod that must receive configuration from a superior primary.

Before installation, establish reviewed common trust, API access, DNS, security groups/firewalls and the required L4 control/data paths. Different network IDs identify separate networks; they do not create connectivity. For multiple networks, both sides need the appropriate east-west gateways for reachable remote endpoints. Cross-Region network cost and failure recovery remain separate responsibilities.

The essential primary configuration is istioctl input:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: mesh1
      externalIstiod: true
      multiCluster:
        clusterName: cluster1
      network: network1
```

For the remote, **198.51.100.10 is a documentation placeholder**, not an EKS endpoint:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: remote
  values:
    istiodRemote:
      injectionPath: /inject/cluster/cluster2/net/network2
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster2
      network: network2
      remotePilotAddress: 198.51.100.10
```

The remote namespace also identifies its managing primary:

```bash
kubectl --context="$CTX_CLUSTER2" annotate namespace istio-system   topology.istio.io/controlPlaneClusters=cluster1 --overwrite
```

Follow the maintained guide to prepare trust, generate gateways from the same Istio release, expose primary discovery/injection and install the remote profile before creating the remote-access secret shown in Question 2. In this two-network example, the remote injection path ends in `net/network2`.

An EKS NLB commonly supplies a DNS name. The release can represent DNS-valued remotePilotAddress, but a chart render alone does not prove discovery/injection connectivity or certificate names. Complete the official external-control-plane DNS/certificate/injection-URL design; do not replace a missing load-balancer IP with an arbitrary address.

For verification, use the released `helloworld` and `curl` samples from the same Istio distribution. Create the same namespace/Service identity in both clusters, with versioned workloads as documented. A Service with no local endpoints can still supply local Kubernetes DNS while Istio discovers remote endpoints:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld
  namespace: sample
spec:
  selector:
    app: helloworld
  ports:
  - name: http
    port: 5000
    targetPort: 5000
```

This Service alone deploys no application. The sample's actual backend listens on port 5000; merely declaring containerPort 8080 does not make a stock nginx process listen there. After the complete sample deployment, select the known curl Pod/container and inspect both data-plane configuration and responses:

```bash
kubectl --context="$CTX_CLUSTER1" get service,endpointslice -n sample
kubectl --context="$CTX_CLUSTER2" get service,endpointslice -n sample
istioctl --context="$CTX_CLUSTER1" proxy-status
istioctl --context="$CTX_CLUSTER1" proxy-config endpoints "$CURL_POD" -n sample   --cluster 'outbound|5000||helloworld.sample.svc.cluster.local'
kubectl --context="$CTX_CLUSTER1" exec -n sample "$CURL_POD" -c curl --   curl --fail --max-time 5 http://helloworld.sample.svc.cluster.local:5000/hello
```

For multiple networks, the client may see an east-west gateway endpoint rather than a directly reachable remote Pod IP. One response proves only that call; exercise both directions, endpoint versions, trust, policies and failure scenarios.

Two weighted destinations with the **same host/subset/port** do not mean local 80%/remote 20%. Use a deliberate supported locality or explicit destination model with eligible endpoints. Choose one telemetry reporter and real source_cluster/destination_cluster labels when observing cross-cluster traffic.

[Multicluster guide](../../../service-mesh/istio/advanced/02-multi-cluster.md)

</details>

### Question 8: Shared Per-user Rate Limiting

Implement a shared 100-request/minute user quota for `/api/premium/*`. Explain the identity, descriptor and failure contracts.

<details>
<summary>Sample Answer</summary>

The request path is: **authenticated entry → dedicated Envoy gateway → shared rate-limit service/Redis decision → backend or rejection**. A local proxy bucket is not a quota shared across gateway replicas.

This conditional example assumes:

- A dedicated gateway in `istio-system` with actual label `app: premium-gateway`, matching TLS/route configuration and existing backend Services.
- A trusted authentication layer strips caller-supplied x-user-id and supplies one nonempty canonical user identity. Only that authenticated path may reach the gateway/backend. A raw caller-controlled header is not user identity.
- The existing isolated-lab Redis endpoint shown below is reachable. Production Redis authentication/TLS, persistence, HA, failover and suitable connection settings must be designed separately; a replica count alone does not supply them.

The matching descriptor is a **two-entry sequence**: `(header_match=premium, user_id=<trusted user>)`. The server config must nest the dynamic user entry under the premium entry. A top-level user_id-only descriptor would not match it.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: premium-ratelimit
    descriptors:
    - key: header_match
      value: premium
      descriptors:
      - key: user_id
        rate_limit:
          unit: minute
          requests_per_unit: 100
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

The image is the verified upstream commit 8fe6ea42 with a digest, not a moving master tag. The gRPC port is **8081**, HTTP health is **8080**. This workload needs a matching injector and actual mesh/network access. Configure protected Redis credentials via appropriate Secret/mount mechanisms. Ensure the new configuration is loaded; the shown file-mode setup is not proof of hot reload.

Use the generated Istio gRPC cluster so the established service discovery/TLS policy applies:

```yaml
apiVersion: networking.istio.io/v1
kind: EnvoyFilter
metadata:
  name: premium-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: premium-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
---
apiVersion: networking.istio.io/v1
kind: EnvoyFilter
metadata:
  name: premium-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: premium-gateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - header_value_match:
              descriptor_value: premium
              headers:
              - name: :path
                string_match:
                  prefix: /api/premium/
          - request_headers:
              header_name: x-user-id
              descriptor_key: user_id
              skip_if_absent: false
```

The action set is deliberately scoped to the dedicated gateway; narrow actual generated vhosts for a shared gateway. Requests outside the prefix generate no premium descriptor. Keep route/path normalization and authentication policy consistent, including encoded paths and alternate backend access.

Reject missing/empty identity on the premium path before it can bypass descriptor generation:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: premium-requires-identity
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: premium-gateway
  action: DENY
  rules:
  - to:
    - operation:
        paths:
        - /api/premium/*
    when:
    - key: request.headers[x-user-id]
      notValues:
      - '*'
```

This DENY policy is only a missing-header guard. It does not authenticate a supplied value or replace the mandatory trusted-entry/bypass controls, existing ALLOW policies, TLS or application authorization.

With `failure_mode_deny: true`, a rate-limit service error normally causes HTTP 500, while an over-limit decision causes 429. The 100 ms RPC budget is an example to test against Redis and network latency. No header/stat counter alone proves the quota is enforced.

| Verification case | Expected contract to test |
|---|---|
| One authenticated identity across two gateway replicas | One shared descriptor/window budget |
| A second identity | A separate user descriptor |
| Missing or forged identity | Rejected by the guard/authentication boundary; not a free quota bypass |
| A path outside the premium prefix | No premium descriptor; other security/rate policies still apply |
| Redis/RLS unavailable | Deliberate fail-closed behavior and observed status/latency |
| Window boundary or Redis restart | Measure counter/window behavior; do not promise exactly request 101 is denied across separate test runs |

Use bounded requests against an authorized read-only endpoint and fresh test identities/windows. Fifty requests followed by another 150 do not start two independent clean budgets. Response rate-limit headers require supported service responses and filter configuration; do not fabricate remaining/reset values.

Inspect RLS health, loaded config and actual Envoy stats (`ratelimit.ok`, `ratelimit.over_limit`, `ratelimit.error` under the HTTP stat prefix). Verify emitted Prometheus names/labels rather than inventing `rejected_total`. Do not run Redis `KEYS *` in a large production keyspace or interpret implementation-specific counters as remaining quota. The pinned distroless RLS image is not a redis-cli shell.

[Rate-limiting guide](../../../service-mesh/istio/resilience/02-rate-limiting.md) · [EnvoyFilter guide](../../../service-mesh/istio/advanced/03-envoy-filter.md)

</details>


### Question 9: Blue/Green with Analysis

Configure a Blue/Green Rollout with preview and post-promotion analysis. Explain the traffic switch and failure behavior without treating missing metrics as success.

<details>
<summary>Sample Answer</summary>

This is an **alternative** to Question 5's canary strategy. It assumes the Argo Rollouts 1.10 controller/CRDs, Istio-injected demo workloads and callers, Prometheus collecting the matching source-reporter metrics, and Linux amd64 capacity for the verified demo image. It is a lab example, not a tested production deployment.

Create the Services and complete Rollout in the existing `rollouts-demo` namespace. Rollouts owns the Service revision-hash selectors; GitOps must not overwrite those dynamic fields.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: true
      prePromotionAnalysis:
        templates:
        - templateName: preview-analysis
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: active-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
```

The initial image is the verified blue demo digest; the guide supplies the corresponding green digest for an update. On a new revision, preview points at the candidate. After successful pre-analysis, `autoPromotionEnabled: true` permits automatic promotion. Set it false when deliberate manual promotion is required; that is a separate policy choice.

Here traffic comes from meshed clients to internal Services. Production edge exposure requires a real Gateway, TLS, matching host bindings and authorization. Merely creating a second VirtualService hostname does not add it to a Gateway or protect preview access.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-preview-route
  namespace: rollouts-demo
spec:
  hosts:
  - test-preview
  - test-preview.rollouts-demo.svc.cluster.local
  http:
  - name: preview
    route:
    - destination:
        host: test-preview
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
```

Both routes explicitly disable mesh retries. The preview Service does not automatically swap to the old stable version at promotion. The active Service selector changes to the new revision; old ReplicaSets are eventually **scaled down**, not necessarily deleted. Existing connections and application/database side effects are not reversed by a selector change.

Before/during preview analysis, generate representative, authorized traffic through the preview Service. Prometheus queries do not generate traffic. This example requires an estimated 20 requests per two-minute window, finite 2xx success ≥95%, p95 ≤0.5 seconds and 5xx/zero-status errors ≤1%:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: preview-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: active-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-2xx-success
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

The two templates intentionally use the same gate definitions with different Service arguments. `initialDelay: 5m` gives the two-minute window time to move beyond the transition, but source freshness and actual traffic still need verification. Avoid reading old active-version samples as candidate evidence.

Prometheus returns a vector, so conditions inspect `result[0]` only after length and finite-value checks. The numerator's `or vector(0)` handles no-2xx/all-5xx and no-5xx/healthy cases; the denominator and volume check prevent absent or idle telemetry from passing. The success metric counts only 2xx; 4xx lowers success even though it is not in the 5xx/zero-status error numerator.

`failureLimit: 0` aborts on the first failed measurement. If set to 2, the third failure exceeds the limit; five samples with tolerated failures do not require five successes. Five samples at a 30-second interval are not an exact guaranteed 2.5-minute wall-clock phase, especially with initial delays and provider errors.

Failure before promotion leaves the old active target in place. Post-promotion failure aborts and restores the prior active selection while the old ReplicaSet is available under the controller's rules. This is not an instantaneous universal rollback guarantee. Keep adequate old-version capacity and verify propagation, sessions, drains and database compatibility.

```bash
kubectl argo rollouts get rollout test -n rollouts-demo --watch
kubectl get analysisrun -n rollouts-demo
kubectl get service test-active test-preview -n rollouts-demo -o yaml
```

Inspect the actual AnalysisRun conditions and revision tree rather than copied status output or nonexistent metric names. Rollout scale-down, endpoint propagation and application recovery must be tested in the intended environment.

[Argo Rollouts guide](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

### Question 10: DNS Behavior and Measurement

Explain Istio DNS capture versus Envoy upstream DNS resolution, show valid configuration, and design a reproducible performance comparison. Assess the original unverified benchmark figures without presenting them as new measurements.

<details>
<summary>Sample Answer</summary>

Application DNS, Istio DNS capture, CoreDNS/cache behavior and Envoy upstream resolution are distinct. A new HTTP request does not necessarily perform a fresh DNS query or connection. DNS capture is not a universal cache for arbitrary upstream responses.

In sidecar mode, istio-agent handles captured DNS requests; ambient uses its own documented DNS path and enables capture by default from Istio 1.25. Known mesh names can be answered from the name table; unknown names are forwarded. Envoy independently resolves DNS-backed upstream endpoints.

Register an application-originated HTTPS external service with a valid ServiceEntry:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.github.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

This does not originate a second TLS layer, create an egress firewall, or make encrypted HTTP request paths visible to the sidecar. Appropriate network policy and application TLS validation remain necessary.

For sidecar capture, merge this istioctl input into the existing installation values and roll affected workloads using the normal change process:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: 'true'
```

There is **no** DestinationRule `trafficPolicy.dnsRefreshRate`, and `consecutiveErrors` is not the current outlier field. Istio 1.31's generated DNS clusters respect DNS TTL; mesh `dnsRefreshRate` defaults to 60 seconds for the relevant fallback behavior. A five-minute setting is not a universal fixed refresh interval overriding positive TTLs.

Do not insert the invented `envoy.filters.network.dns_cache` filter/type. Dynamic forward proxy and the current DYNAMIC_DNS ServiceEntry mode are separate supported designs with their own requirements, not a generic cache toggle. Use the DNS guide for an explicitly scoped, version-validated cluster customization if required.

For a bounded test, use a caller container known to contain curl and an **owned/authorized** HTTPS test endpoint with controllable DNS/TTL. Set BENCH_URL explicitly. This samples process-level timings, not Envoy-only DNS latency:

```bash
: "${BENCH_URL:?Set an authorized HTTPS benchmark endpoint}"
for i in $(seq 1 20); do
  curl --silent --show-error --fail --max-time 5 --output /dev/null     --write-out '%{http_code},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}
'     "$BENCH_URL" || break
  sleep 0.2
done
```

Record the client/image, Istio/Kubernetes versions, proxy mode, TTL/answer changes, DNS path, connection reuse, concurrency, payload, TLS and warm/cold procedure. Each new curl process resets its process-local state; control connection reuse separately. Do not load-test a public GitHub API or assume a curl image also contains ApacheBench. Failed samples need explicit handling before statistics are calculated.

The original Korean text claimed EKS 1.34, Istio 1.28.0, r5.xlarge/us-east-1 and api.github.com, but supplied no raw samples or reproducible benchmark artifact. Preserve that **historical context**, not a relabeled Istio 1.31 result:

| Original unverified figure | Before | After | Arithmetic only |
|---|---:|---:|---:|
| Mean response time |287 ms|152 ms|47.04% lower|
| p95 |350 ms|180 ms|48.57% lower|
| p99 |420 ms|210 ms|50% lower|
| Throughput |12.34 RPS|23.15 RPS|87.60% higher|
| Claimed cache hit rate |0%|99%|No valid hit/miss evidence supplied|
| Claimed connection reuse |0%|95%|No valid reuse measurement supplied|

The difference in total response time cannot be attributed entirely to DNS. For concurrency 10, ApacheBench's mean time per request is approximately `1000 × 10 / RPS` ms, while its “across all concurrent requests” figure is `1000 / RPS` ms; the original labels were reversed. These corrections do not authenticate the benchmark.

Useful capture metrics include `istio_agent_dns_requests_total`, `istio_agent_dns_upstream_requests_total`, `istio_agent_dns_upstream_failures_total` and the upstream-duration histogram when actually exported. Upstream success/(success+failure) is query success, not cache hit rate. `envoy_cluster_upstream_cx_active` is a gauge; applying rate() to it does not measure connection reuse.

Inspect generated cluster DNS configuration, verified exported counters and actual resolver/connection traces. Test DNS changes and failure recovery as well as mean latency; do not recommend 5–15 minute refreshes or a fixed performance improvement without workload evidence.

[DNS guide](../../../service-mesh/istio/advanced/04-dns-cache.md)

</details>

## Scoring

- Questions 1–5: 10 points each, 50 total. Keys: **B, A, C, D, B**.
- Questions 6–10: 10 points each, 50 total. Award credit for correct mechanics, complete prerequisites, valid configuration, meaningful verification and honest measurement limits.
- Total: 100 points. A quiz score indicates understanding of these questions; it does not certify operational expertise.

## Study Materials

- [Ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [Multicluster](../../../service-mesh/istio/advanced/02-multi-cluster.md)
- [EnvoyFilter](../../../service-mesh/istio/advanced/03-envoy-filter.md)
- [DNS](../../../service-mesh/istio/advanced/04-dns-cache.md)
- [gRPC](../../../service-mesh/istio/advanced/05-grpc.md)
- [WebSocket](../../../service-mesh/istio/advanced/06-websocket.md)
- [Injection](../../../service-mesh/istio/advanced/07-sidecar-injection.md)
- [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)
- [KEDA](../../../service-mesh/istio/advanced/10-keda-autoscaling.md)
