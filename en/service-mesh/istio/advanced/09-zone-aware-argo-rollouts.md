# Zone-Aware Argo Rollouts

> **Verification baseline**: Istio 1.31.0, Argo Rollouts 1.10.0, Kubernetes 1.32–1.36
> **Last reviewed**: September 11, 2026
> **Difficulty**: Advanced

This guide separates independent zonal canaries from cross-AZ failover. The main example is a **zonal routing/isolation blueprint**: a client cohort selects one zone's stable/canary Services. It does not implement automatic failover to another zone when those endpoints disappear.

## Table of Contents

1. [Problem Definition](#problem-definition)
2. [Architecture Overview](#architecture-overview)
3. [Key Design Decisions](#key-design-decisions)
4. [Implementation Guide](#implementation-guide)
5. [Traffic Flow](#traffic-flow)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## Problem Definition

### Spot Interruptions and PDBs

Spot capacity can be reclaimed and correlated capacity loss must be planned for. Interruption notices are best effort; stop/terminate notices normally give two minutes, while hibernation starts immediately. EKS managed node groups attempt replacement/rebalancing, but do not guarantee a replacement is Ready before draining an interrupted node.

A PodDisruptionBudget constrains voluntary Eviction API operations. It does not prevent EC2 interruption, node failure, direct Pod deletion or every controller-driven update. Rollouts does not create/manage the PDBs below; the application team defines them and Kubernetes computes their status.

For nine healthy matching Pods with **integer `minAvailable: 6`**, the illustrative voluntary-disruption allowance is three. If only six remain healthy, that allowance is zero. This is not a “33% minimum requiring six Pods”: with nine expected Pods, `minAvailable: "33%"` rounds up to three. Percentage `maxUnavailable` has different semantics and controller-scale requirements.

Splitting that global budget into `minAvailable: 1` per zone changes protection. With one zone gone, the remaining two budgets may allow voluntary evictions down to one healthy Pod each, rather than preserving six globally. This can be useful for independent operations, but it is a different availability/capacity policy. A budget selecting both stable and canary Pods also does not guarantee capacity in each weighted destination separately.

### Goals and Constraints

| Design | Independent zonal versions | Cross-AZ failover | Main constraint |
|---|---|---|---|
| One shared revision/subset with endpoints across AZs | No independent per-zone revision control | Possible within the selected endpoint pool | Healthy capacity and compatible release/data state in the other AZ |
| Per-zone Rollouts and zone-filtered Services, shown here | Yes | Not supplied by locality settings | A selected zone's empty pool remains empty |
| Separate health-aware entry routing before zonal gateways/pipelines | Can be designed | Requires its own policy/controller and tests | Extra routing, capacity, identity and recovery coordination |

Do not claim all three properties—strict zonal filtering, independent per-zone hashes and transparent failover—by adding a DestinationRule alone. A separate entry-routing design is outside this deployment blueprint and has not been production-tested here.

## Architecture Overview

A common `test` Service supplies the DNS name. For injected clients, a VirtualService selects a zonal route using an **explicit client Pod label**. Each route points to that zone's stable/canary Services. A separate Rollout controls that pair's Service hashes and its own named route's weights.

Istiod compiles the configuration into Envoy. VirtualService/DestinationRule objects are not network hops. A non-meshed client can use the common Service's ordinary Kubernetes endpoint selection, bypassing these route rules; routing labels are not a security boundary.

Each zone's Pods are scheduled only in its configured AZ. Consequently, zone A's Services contain no zone B/C fallback endpoints. Independent deployment state also does not eliminate shared control-plane, API-server, network or database dependencies.

## Key Design Decisions

### 1. Route Ownership

Rollouts 1.10 reconciles configured route weights and supported managed destinations; it does not blindly replace every destination array. Different route names avoid competing desired weights. However, three controllers updating one VirtualService can still encounter Kubernetes `resourceVersion` conflicts and reconciliation delays. Separate objects/entry routing are an option when stronger control-plane isolation is required.

This blueprint uses distinct routes (`zone-a-route`, `zone-b-route`, `zone-c-route`) and **host-level splitting**. It does not mix Service-hash and DestinationRule-subset ownership. The [integration guide](08-argo-rollouts.md) explains both alternatives.

### 2. Client Labels and Actual AZs

`sourceLabels` selects source workloads when Istiod builds their mesh configuration; it is not a runtime request-header match. Node labels such as `topology.kubernetes.io/zone` are not automatically copied to Pods. A custom `routing.example.com/zone: a` Pod label must be paired with verified placement in the intended AZ.

These selectors apply to mesh clients, not generic external requests arriving at an ingress gateway. Preserve the `mesh` gateway scope. Unknown client cohorts get an explicit 503 response in this example instead of silently selecting another zone.

### 3. Locality Cannot Escape the Selected Pool

A subset selected by `zone: a` and a Rollout A hash cannot fail over to a sibling zone B subset. The same applies to a zone-filtered Service. Outlier detection only changes endpoint eligibility inside the selected upstream pool; it does not jump to a different VirtualService route.

Also, `localityLbSetting.distribute`, `failover` and `failoverPriority` are alternatives, not fields to combine freely. The `failover.from/to` values are **regions**, not `region/zone` strings. An A→B→C→A AZ cycle is not established by those entries.

## Implementation Guide

### Prerequisites

Use the controller, CLI, injection, Prometheus and workload prerequisites from [Argo Rollouts Integration](08-argo-rollouts.md). This is an isolated sidecar HTTP demo with default/legacy injection; use the installed revision/tag instead on a revisioned mesh. The lab requires compatible EC2-backed Linux worker nodes, quotas, networking, image access and observability. Fargate is outside this blueprint; choose a currently supported EKS version within the Istio compatibility range.

The example AZ names `us-east-1a/b/c` must be replaced with actual node labels. AZ name mappings can differ across accounts; verify AZ IDs when coordinating physical zones across accounts. The pinned demo image is Linux amd64 only, so each selected AZ needs compatible nodes or a separately verified replacement image.

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone,kubernetes.io/arch
```

### 1. Namespace and Common/Zone Services

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: zone-rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: zone-rollouts-demo
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
  name: test-stable-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
```

The common Service is a DNS entry for meshed callers, not an authorization mechanism. The six zonal Services have an actual Pod `zone` selector; Rollouts adds each stable/canary hash.

### 2. Client Template Contract

Merge this into an **existing Deployment named `zone-client-a`**, retaining its selector, containers, verified image, resources and other placement constraints. Add the `a` route label to the actual Pod template, not only the Deployment metadata:

```yaml
metadata:
  name: zone-client-a
  namespace: zone-rollouts-demo
spec:
  template:
    metadata:
      labels:
        routing.example.com/zone: a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
```

Prepare equivalent B/C clients with matching labels and actual AZ constraints when testing them. When combining affinity with existing rules, preserve the intended AND/OR restrictions; do not broaden node eligibility accidentally. Verify `.spec.nodeName` against the selected Node's zone. The fragment does not deploy a client or copy node metadata automatically.

### 3. Shared VirtualService with Independent Routes

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  hosts:
  - test
  - test.zone-rollouts-demo.svc.cluster.local
  gateways:
  - mesh
  http:
  - name: zone-a-route
    match:
    - sourceLabels:
        routing.example.com/zone: a
    route:
    - destination:
        host: test-stable-a
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-a
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-b-route
    match:
    - sourceLabels:
        routing.example.com/zone: b
    route:
    - destination:
        host: test-stable-b
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-b
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-c-route
    match:
    - sourceLabels:
        routing.example.com/zone: c
    route:
    - destination:
        host: test-stable-c
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-c
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: unclassified-client
    directResponse:
      status: 503
      body:
        string: No reviewed client-zone route
```

Before test traffic, verify that each controller has selected the intended hashes and healthy endpoints. Initial weights are 100/0, not an unexplained live 90/10 split. Each named route explicitly disables mesh retries; application retry behavior is separate.

### 4. Per-zone Rollouts

The workload, replica count, requests/limits and pauses are demo inputs. Three replicas do not automatically spread across three nodes. Review node-level spread/anti-affinity, capacity, PDBs and stable/canary headroom for a real deployment.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-a
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: a
  template:
    metadata:
      labels:
        app: test
        zone: a
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
  strategy:
    canary:
      stableService: test-stable-a
      canaryService: test-canary-a
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-a-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-b
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: b
  template:
    metadata:
      labels:
        app: test
        zone: b
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b
  strategy:
    canary:
      stableService: test-stable-b
      canaryService: test-canary-b
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-b-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-c
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: c
  template:
    metadata:
      labels:
        app: test
        zone: c
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1c
  strategy:
    canary:
      stableService: test-stable-c
      canaryService: test-canary-c
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-c-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
```

Each Rollout has its own selector, image/revision state, Services and analysis arguments. After the first 5% gate, an indefinite pause requires an intentional promotion. A hard zone affinity leaves the affected Pods Pending if that AZ has no capacity; it does not relocate them to healthy AZs.

### 5. Explicit PDBs

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-a-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: a
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-b-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: b
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-c-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: c
```

These preserve the original illustrative minimum of one Pod per zone. They are not equivalent to the earlier global minimum of six and do not protect each traffic-weighted revision independently. Inspect `currentHealthy`, `desiredHealthy` and `disruptionsAllowed` before voluntary maintenance.

### 6. Per-zone Analysis

Create this template before the Rollouts. It uses the actual zonal canary Service name and standard source-reporter metrics rather than invented Pod-zone labels:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-check
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-2xx-rate
    interval: 1m
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
```

The numerator is specifically **HTTP 2xx**, preserving this guide's success definition. An all 5xx window produces 0, not an empty numerator; no traffic or missing data cannot pass the finite-value/volume gates. Source proxies and the provider must reach the configured Prometheus, and its actual labels must match these selectors.

Sustain representative meshed traffic through `http://test.zone-rollouts-demo.svc.cluster.local:8080/color`. The caller label chooses its zone, and the controller chooses that zone's stable/canary weight. Five-minute warm-up exceeds the two-minute metric lookback; the twenty-request estimate and measurement counts are illustrative, not statistical confidence.

## Traffic Flow

### Normal Zonal Path

A correctly labelled client A, placed in the reviewed AZ, gets `zone-a-route`, which targets A's stable/canary Services. The observed ratio depends on sample size, sessions and readiness, not an exact per-ten-request guarantee.

### Zone Loss

If every eligible A endpoint disappears, A's route has no healthy upstream. Lowering an outlier threshold or changing the PDB cannot manufacture B endpoints in A's Service. The example returns failures until capacity or an explicitly designed higher-level routing policy changes.

For continuity across AZs, choose an architecture with healthy remote endpoints in the same selected release pool, or implement and test a separate entry-layer failover policy. Account for remote capacity, data consistency, authentication, in-flight requests and failback. No transparent/cyclic failover is claimed by the zonal code above.

### Separate Shared-endpoint Locality Alternative

The following belongs to a **different setup**: an existing `shared-app` Service or selected subset whose eligible endpoints span AZs and have compatible release state. It does not enable failover on the zonal Services above. If a DestinationRule already owns that shared host/subsets, merge this trafficPolicy into it instead of creating a competing rule:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: shared-endpoint-locality
  namespace: zone-rollouts-demo
spec:
  host: shared-app.zone-rollouts-demo.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

Locality priorities prefer matching region/zone and can move subsequent traffic to eligible healthy endpoints. They do not specify a fixed cyclic AZ order. `consecutive5xxErrors` is the current field; consecutive detection is traffic-driven, while `interval` applies to periodic detection work. Ejecting all endpoints can cause errors, and an already failed request is not automatically replayed. See [Zone-Aware Routing](../resilience/03-zone-aware-routing.md).

## Troubleshooting

```bash
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo
kubectl get virtualservice test -n zone-rollouts-demo -o yaml
kubectl get services test-stable-a test-canary-a -n zone-rollouts-demo -o yaml
kubectl get pods -n zone-rollouts-demo -l app=test -o wide --show-labels
kubectl get endpointslices -n zone-rollouts-demo -l kubernetes.io/service-name=test-canary-a
kubectl get pdb -n zone-rollouts-demo -o wide

istioctl proxy-config routes <client-a-pod> -n zone-rollouts-demo
istioctl proxy-config endpoints <client-a-pod> -n zone-rollouts-demo --cluster 'outbound|8080||test-canary-a.zone-rollouts-demo.svc.cluster.local'
kubectl get analysisruns -n zone-rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

- **Update conflicts**: Distinguish ownership of the same route from temporary object-version conflicts on a shared VirtualService. Different subset names alone do not solve either cause.
- **Wrong zone selected**: Compare actual caller Pod labels, Node placement and compiled routes. Do not assume node zone labels were copied to Pods.
- **No fallback**: Inspect the selected Service/subset's eligible endpoints first. If none exist outside A, faster outlier detection cannot provide cross-AZ failover.
- **No canary traffic**: Confirm mesh traversal, ready EndpointSlices, hash selectors, actual weights and sufficient samples.
- **Stuck/failed analysis**: Inspect its raw result and provider error, not only the aggregate rollout phase. Missing custom zone labels are not built-in telemetry.

## Best Practices

### 1. Coordinate Version Changes Explicitly

Promote resumes an existing pause; it does not deploy a new image or prove another AZ is healthy. Update one zone's desired image in Git (or directly in the isolated lab), observe its analysis and workload state, then decide whether to advance another zone. A fixed five-minute wait is not sufficient evidence by itself.

```bash
# Isolated lab alternative to changing Git; affects zone A only.
kubectl argo rollouts set image test-a app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n zone-rollouts-demo
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo --watch
# After the intended manual pause and review:
kubectl argo rollouts promote test-a -n zone-rollouts-demo
```

Abort does not revert the desired image in Git. Coordinate GitOps so it does not overwrite each zone's managed weights or Service hash selectors; see the preceding integration guide.

### 2. Continuous Analysis Alternative

Replace the inline-step schedule deliberately if continuous monitoring is needed. `count` is omitted in the background template, and `startingStep: 2` means the third step:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-continuous
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: zone-canary-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary-a
        - name: namespace
          value: zone-rollouts-demo
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

Keep the correct zone's route, Services and arguments when adapting this A fragment to B/C. Independent analysis can still depend on shared Prometheus/network/control-plane availability.

### 3. Monitoring Rules

This PrometheusRule requires Prometheus Operator and matching rule namespace/label selectors. A standalone Istio addon Prometheus does not load this CRD automatically.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: zone-rollout-alerts
  namespace: zone-rollouts-demo
spec:
  groups:
  - name: zone-rollout
    rules:
    - alert: HighErrorRateZoneACanary
      expr: |-
        ((sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) > 0.05
        and
        (sum(increase(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) >= 20
      for: 2m
      annotations:
        summary: Zone A canary has elevated 5xx/zero-status rate with observed traffic
    - alert: UnexpectedDemoZoneRoute
      expr: |-
        sum(rate(istio_requests_total{
          reporter="source",source_workload="zone-client-a",source_workload_namespace="zone-rollouts-demo",
          destination_service_namespace="zone-rollouts-demo",destination_service_name=~"test-(stable|canary)-(b|c)"
        }[5m])) > 0
      for: 5m
      annotations:
        summary: Demo client A is using a B/C destination Service; inspect route/placement assumptions
```

The first rule checks 5xx/zero-status failures; 4xx also lowers the Analysis 2xx rate but does not trigger this particular error rule. Low/missing traffic requires a separately designed expected-traffic/telemetry-health signal; absence is not proof of a healthy canary.

The second is a **demo routing-invariant alert**, not a universal physical cross-AZ detector. It assumes the real source Deployment is `zone-client-a`, its placement is A, and B/C Services retain their zonal selectors. For physical-zone measurements, use verified node/endpoint locality or explicitly enriched telemetry as described in the routing/observability guides.

### 4. Recovery and Capacity

Diversify Spot capacity and retain adequate fault-tolerant capacity according to the actual EKS/node provisioning model. Zonal affinity, interruption handling and PDB policy cannot guarantee replacement capacity. Check the node group's lifecycle behavior and the application's termination/restore process.

There are no measured resource or latency results for this blueprint. Size Istiod, proxies and the Rollouts controller from measured reconciliation pressure, endpoint counts, resource use and normal/failure-path latency for the actual workload.

## References and Next Steps

- [Argo Rollouts Integration](08-argo-rollouts.md)
- [Zone-Aware Routing](../resilience/03-zone-aware-routing.md)
- [Outlier Detection](../resilience/01-outlier-detection.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
- [Istio VirtualService source selectors](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio locality failover](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [Istio DestinationRule API](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Argo Rollouts Istio integration](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [Kubernetes disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PDB configuration and rounding](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Node affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [EC2 interruption notices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [EKS managed-node Spot behavior](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [AWS AZ IDs and account mapping](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
- [AWS Regions and Availability Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

Use the maintained integration/routing guides above as the starting point for lab validation. [Multi-cluster](02-multi-cluster.md) introduces additional trust, connectivity and failure-domain design; it is not a single-setting extension of this blueprint.
