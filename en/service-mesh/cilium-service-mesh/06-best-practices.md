# Cilium Service Mesh Best Practices

> **Review baseline**: Cilium 1.20.1 and Cilium CLI 0.20.0.
> **Last reviewed**: September 11, 2026. Use the [installation guide](./README.md) for the separate Kubernetes, EKS and optional component compatibility checks.

## Overview

An operating plan must connect CNI ownership, proxy features, policy enforcement, capacity and recovery. The following values are examples to review against a particular cluster. They are not production-tested sizing guarantees, a CNI migration procedure or a complete EKS installation.

## Production Deployment Checklist

- [ ] Select a supported Kubernetes/Cilium/platform combination, CPU architecture and node OS. The general kernel minimum is 5.10 or a documented equivalent such as RHEL 8.10's 4.18; advanced features can require newer kernels.
- [ ] Record the current CNI, IPAM, Pod/Service/VPC CIDRs, routes, MTU and kube-proxy owner. Verify the reachable API-server address before enabling kube-proxy replacement.
- [ ] Select the L7 owner for each workload. Cilium Ingress/Gateway requires its documented kube-proxy replacement and L7 prerequisites; Istio coexistence has different settings.
- [ ] Choose authentication, encryption and authorization separately. Validate permitted and denied flows, DNS and essential infrastructure access before enforcing default deny.
- [ ] Establish metric targets, actual labels, logs, alert routing and certificate renewal. Test missing-data behavior.
- [ ] Provide enough eligible nodes for replica placement and maintenance. Check Operator/Relay readiness, disruption budgets and DaemonSet update strategy.
- [ ] Record a tested rollback point, retained chart/values/CRDs and workload/policy inventory. Rehearse in a representative environment.

### Helm Values to Review

Merge this **resource and availability overlay** with the platform configuration from the installation guide. It intentionally does not select a universal IPAM range, disable kube-proxy or enable every optional security feature.

```yaml
agent: true
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    maxUnavailable: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
l7Proxy: true
envoy:
  enabled: true
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
    podDisruptionBudget:
      enabled: true
      maxUnavailable: 1
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              k8s-app: hubble-relay
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1000m
        memory: 1Gi
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
```

`agent` is a boolean. Agent resource requests/limits belong at top-level `resources`, not `agent.resources`. The original two conflicting resource definitions have been consolidated. These CPU/memory quantities are starting examples; measure them under your policy count, churn, traffic and failure scenarios.

The Operator's chart affinity separates replicas by hostname. Relay anti-affinity here also requires two eligible nodes. This does not enforce availability-zone separation; add topology requirements appropriate to the cluster. Two replicas without schedulable placement and working dependencies do not provide HA. PDBs govern qualifying voluntary evictions, not every outage or a DaemonSet controller's rollout; direct Pod deletion also bypasses eviction protection.

External etcd is an architectural choice with its own operational requirements, not a mandatory addition once a node-count threshold is reached. Keep the chosen identity-allocation mode consistent and follow its documented migration procedure if changing it.

### Authentication and Encryption

The following is an **optional** out-of-band authentication plus WireGuard profile:

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
```

Enable it only with the [security guide's](./03-security.md) kernel, ports, SPIRE storage/identity and policy prerequisites. `authentication.enabled` is required in addition to the SPIRE settings. A rule must require authentication to enforce it. WireGuard protects eligible node-to-node traffic; SPIRE-based out-of-band authentication does not turn each application connection into an Istio-style mTLS session. `nodeEncryption` is separately gated and remains false in this example.

Cilium 1.20.1 also has **Beta ztunnel workload mTLS**, documented separately in the security guide. Its default internal CA, namespace enrollment and TCP/HBONE/policy limitations differ from the SPIRE out-of-band path. Choose an explicit design; neither checkbox wording nor a Helm feature flag proves equivalent security coverage.

## Sizing Guidelines

### Measure by Component

| Component | Capacity drivers to measure | Checks before increasing limits |
|---|---|---|
| Agent | Endpoints, identities, policy selectors/rules, connection churn, BPF maps and event volume | Working set, CPU/throttling, map pressure, policy regeneration and drop reasons |
| Envoy | Concurrent connections/streams, TLS work, request/response size, buffering and filter cost | Heap/RSS, CPU, queueing, upstream saturation and p99 at a fixed workload |
| Operator | IPAM/identity/node churn and API latency/rate limits | Reconciliation backlog, EC2/Kubernetes throttling, allocation failures |
| Hubble Relay/UI | Observed flow volume, concurrent observers, flow buffer and query scope | Lost events, relay resources, query latency and replica placement |

The former node-count table and formulas `512Mi + Pods × 1Mi` and `256Mi + connections/second × 0.1Mi` had no benchmark evidence. They are not valid universal memory models. Peak concurrent connections, buffer lifetimes, traffic mix and policy cardinality matter; a requests/second number alone does not determine retained memory. Set requests from measured scheduling needs, allow tested headroom, and verify limits under bursts and one-node loss.

### eBPF Map Sizing

This is one explicit static sizing example, not multiple alternatives in one YAML mapping:

```yaml
bpf:
  ctTcpMax: 2097152
  ctAnyMax: 1048576
  natMax: 2097152
  policyMapMax: 65536
```

The current chart keys are `ctTcpMax`, `ctAnyMax` and `natMax`; the old `ctGlobalTcpMax`, `ctGlobalAnyMax` and `natGlobalMax` values are ignored. Agent ConfigMap flags still use names such as `bpf-ct-global-tcp-max`, so do not confuse chart keys with daemon flags. NAT capacity must not exceed two-thirds of the combined TCP/other CT capacity; these numbers meet that bound. A map entry limit is not a guaranteed number of application sessions.

Increasing map sizes consumes node/kernel memory. Resizing maps or changing their implementation can disrupt state and connections. Inspect the rendered ConfigMap and actual map usage; do not infer capacity from node count or count human-readable CLI output lines as precise occupancy.

## Performance Tuning

### eBPF Settings

```yaml
bpf:
  preallocateMaps: true
  mapDynamicSizeRatio: 0.0025
bpfClockProbe: false
```

Preallocation trades more upfront memory for avoiding some allocation work; it is not a memory-saving switch. This alternative uses the dynamic sizing ratio. Do not combine it casually with the static map example: explicit sizes override derived sizing, and distributed LRU has additional constraints. `bpfClockProbe` is a top-level key; changing its clock representation on existing CT state requires the documented migration precautions.

`socketLB` is also top-level, not nested below `bpf`. For Istio coexistence its `hostNamespaceOnly` setting is significant; enabling socket acceleration indiscriminately can bypass expected proxy interception. The old `bpf.lbBypassFIBLookup` setting is not a supported chart value.

The released tuning guide's netkit/BIG TCP profile has kernel/NIC and migration prerequisites (including kernel 6.8 for that profile). Existing veth Pods cannot simply be converted by toggling a value. Use the documented per-node/new-node migration approach and validate encryption, routing and application behavior before expanding.

### Network Stack

Start by reading the node settings:

```bash
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog \
  net.core.netdev_max_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_tw_reuse
```

Change a sysctl only after identifying the relevant queue or connection-state bottleneck and checking the target kernel's semantics. The former global `sysctl -w` list was not a workload-specific tuning result. In particular, `tcp_fin_timeout` is not a universal TIME_WAIT cleanup knob, and TIME_WAIT reuse settings are not a general latency fix. Preserve original settings and use managed node configuration for a reviewed rollout.

### Envoy

`CiliumEnvoyConfig.spec.resources` accepts specific xDS resource types; it does **not** accept a Bootstrap object. The original overload-manager Bootstrap inside a CEC would not be applied. A fixed-heap monitor alone also does not define an overload action.

Use the chart's resource limits and the complete [connection-pool example](./05-ingress-gateway.md#connection-pool-configuration) for their respective purposes. An overload manager belongs in the process bootstrap, with supported actions and thresholds. If using `envoy.bootstrapConfigMap`, retain Cilium's required bootstrap wiring and validate it against the exact released Envoy image. A whole-bootstrap replacement is an advanced integration, not a safe partial CEC patch.

### Benchmark Evidence

The previous figure claimed native/Cilium/Istio p99 values of 0.1/0.3/2.5 ms without a source, version, topology, load, encryption setting or reproduction data. It is not retained as a historical measurement. Preserve real benchmark versions/dates when evidence exists; do not relabel an old result with a new release.

A useful comparison records hardware, kernel/CNI/mesh versions, request size, concurrency, connections, TLS/policy/filter configuration, warm-up, sample count, throughput, error rate and tail latency. Compare equivalent L4 or L7/security behavior rather than assuming every Cilium path is an Envoy-free mesh.

## Migration from Sidecar Mesh

### Separate CNI Migration from Mesh Migration

Installing a second CNI next to an existing one is not sufficient. The official dual-overlay migration procedure requires distinct Pod CIDRs and encapsulation, per-node control, workload recycling and explicit policy-enforcement tradeoffs. Its limitations include untested combinations. Rehearse the actual platform case; the old diagram's generic “install alongside existing CNI” step omitted essential requirements.

When Cilium already provides networking, mesh coexistence is a different task. Cilium's Istio integration describes a kube-proxy-present path:

```yaml
kubeProxyReplacement: false
cni:
  exclusive: false
```

For a planned full kube-proxy replacement path:

```yaml
kubeProxyReplacement: true
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

Retain the required API-server, CNI/IPAM and platform settings. `cni.exclusive: false` preserves other CNI configuration such as Istio CNI; `socketLB.hostNamespaceOnly: true` avoids interfering with Pod-level proxy capture. The obsolete `tunnel: vxlan` key is not a current migration recipe. If selecting an overlay independently, current keys are `routingMode` and `tunnelProtocol`, with appropriate routing/MTU requirements.

### Transfer Workloads Deliberately

Record `istio-injection`, revision labels, Pod injection annotations, ambient enrollment and existing sidecars before changing anything. A namespace label affects future admission; it does not remove an already running sidecar. Revision labels and per-Pod settings can override a simplistic namespace plan. Recreate only the selected workloads after reviewing availability and validating the replacement policy.

Use one L7 policy owner per workload during the transition. Cilium cannot enforce HTTP rules inside Istio-encrypted traffic. Disabling Istio mTLS merely to gain HTTP visibility changes security and is not an automatic conversion step. Ambient HBONE also changes what Cilium can observe at L4; keep Istio responsible for workload identity and inner-traffic policy where that path remains.

### Routing Conversion Example

Prerequisite: ready `app: reviews` Pods with `version: v1` or `v2`, serving HTTP on Pod port 9080. The separate Services make version selection explicit:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: default
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: default
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
```

An Istio routing configuration needs both the VirtualService and subset definitions:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

For workloads whose L7 ownership has been transferred, a complete Cilium CEC can implement this header-selection behavior:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: reviews-route
  namespace: default
spec:
  services:
  - name: reviews
    namespace: default
    ports:
    - 9080
    listener: reviews-listener
  backendServices:
  - name: reviews-v1
    namespace: default
  - name: reviews-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: reviews-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: reviews-migration
          route_config:
            name: reviews-routes
            virtual_hosts:
            - name: reviews
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: end-user
                    string_match:
                      exact: jason
                route:
                  cluster: default/reviews-v2
              - match:
                  prefix: /
                route:
                  cluster: default/reviews-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v1
    type: EDS
    connect_timeout: 5s
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v2
    type: EDS
    connect_timeout: 5s
```

The CEC has a Listener, HCM/router, both EDS Clusters and actual backend Service references. Cilium supplies dynamic endpoint configuration. `end-user: jason` is untrusted routing input, not authentication. This example does not copy every Istio timeout/retry/mTLS/telemetry behavior; compare those separately and use the [retry guidance](./02-traffic-management.md#retry-configuration) when protecting writes. Do not attach both implementations to the same active traffic path and assume equivalent ownership.

### Authorization Is Not a Mechanical Translation

For an Istio-managed `app: httpbin` workload on Pod port 8080, require incoming mTLS and allow the specific authenticated service-account principal:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: httpbin-strict
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/sleep
    to:
    - operation:
        methods:
        - GET
        paths:
        - /info*
        ports:
        - '8080'
```

A Cilium policy candidate for the same namespace/service-account label selection and GET/path intent is:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: httpbin
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:io.cilium.k8s.policy.serviceaccount: sleep
    authentication:
      mode: required
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/info.*$
```

This requires the separately installed Cilium authentication system; it does not consume the Istio certificate principal. Its security identities, trust domain, authentication exchange and encryption coverage differ. The port is the **Pod destination port**, not an assumed Service port. Additional allow policies can broaden access in either system, and Cilium egress is not denied by this ingress rule. Test allowed GET, denied methods/paths, wrong service account, missing authentication and encrypted/unencrypted paths before calling the migration equivalent.

### Rollback Plan

Keep the original workload templates, labels, policies, Secrets/certificate ownership and Helm values in the deployment system. Record exactly which resources the migration owns. First restore the chosen old traffic/policy path and verify its identity/enforcement; then remove only the replaced migration resources in the tested order.

The old script deleted **every CiliumNetworkPolicy in a namespace**, which could remove unrelated default-deny protections. It has been removed. Re-enabling one injection label and restarting all Deployments is also insufficient for revision-managed injection, ambient enrollment, StatefulSets or Jobs. CNI/IPAM rollback can require node and Pod recreation and is a separate recovery procedure.

## Gradual Adoption

If Cilium should provide only L3/L4 networking and policy, disable the relevant Cilium L7 features deliberately:

```yaml
l7Proxy: false
envoy:
  enabled: false
ingressController:
  enabled: false
gatewayAPI:
  enabled: false
```

`envoy.enabled: false` alone selects the embedded Envoy mode when L7 is otherwise enabled; it does not disable all Cilium L7 behavior. Inventory existing L7 policies, Ingress/Gateway resources and CECs before removing their functionality. With Istio ambient, Cilium sees the HBONE transport rather than the original inner workload flow in the same way as ordinary plaintext traffic.

| Phase | L7 ownership and exit criteria |
|---|---|
| Establish networking | Verify Cilium CNI/L3/L4 behavior while the current mesh retains its intended traffic ownership |
| Transfer selected workloads | Separate ownership by workload; compare routing, identity, encryption, retries and telemetry with negative tests |
| Retire old components | Remove them only after all dependent workloads and recovery procedures have been verified |

The former transition figure repeated the blanket policy-deletion rollback and oversimplified coexistence; this table replaces those steps.

## Monitoring and Alerting

### Explicit Scrape Labels

Install Prometheus Operator CRDs and configure its ServiceMonitor/PrometheusRule selectors first. This overlay fixes the example job names and a cluster label; replace `example-cluster` consistently with the actual cluster identity and adapt the `release` selector:

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_node_name
      targetLabel: node
    - targetLabel: cluster
      replacement: example-cluster
    - targetLabel: job
      replacement: cilium-agent
envoy:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      labels:
        release: prometheus
      relabelings:
      - sourceLabels:
        - __meta_kubernetes_pod_node_name
        targetLabel: node
      - targetLabel: cluster
        replacement: example-cluster
      - targetLabel: job
        replacement: cilium-envoy
```

Hubble HTTPv2 context and recording rules are configured separately in the [observability guide](./04-observability.md). L7 observations only exist for traffic with the required visibility. Use a trusted internal metrics path; these values do not configure remote Prometheus reachability.

### Operational Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-operational-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: cilium.operational
    rules:
    - alert: CiliumMetricsScrapeFailed
      expr: up{job=~"cilium-agent|cilium-envoy"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Known Cilium metrics target cannot be scraped
    - alert: HighObservedPacketDrops
      expr: sum by (cluster, node, direction, reason) (rate(cilium_drop_count_total[5m]))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High observed packet drop count
    - alert: HighBPFMapPressure
      expr: cilium_bpf_map_pressure > 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High pressure in an instrumented BPF map
```

A failed `up` scrape indicates target access failure, not necessarily a stopped Agent/Envoy process. If discovery removes a target, its `up` series can disappear entirely; compare expected node/DaemonSet inventory separately. `cilium_proxy_redirects` counts installed redirects and can legitimately be zero—it is not Envoy liveness.

The old `cilium_datapath_conntrack_active/max` ratio used nonexistent metrics. CT GC observations are not an instantaneous full-capacity gauge. Map-pressure metrics cover instrumented maps and their emission rules; verify which maps are present. Drop and pressure thresholds above are illustrative and must be calibrated by traffic, reason, duration and expected policy denies.

### Dashboard Import

This is a standalone classic dashboard JSON for Grafana UI import, not an HTTP API wrapper. Select the Prometheus data source and first install the observability guide's `cilium_hubble:*` recording rules:

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "cilium-operational",
  "title": "Cilium operational signals",
  "tags": [
    "cilium",
    "hubble"
  ],
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "panels": [
    {
      "id": 10,
      "title": "Successfully scraped agent targets",
      "type": "stat",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (cluster) (up{job=\"cilium-agent\"})",
          "legendFormat": "{{cluster}}"
        }
      ]
    },
    {
      "id": 1,
      "title": "Observed HTTP responses/s",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_responses:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "title": "Observed HTTP5xx (%)",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_5xx_percent:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "title": "Observed HTTP P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, cilium_hubble:http_latency_bucket:rate5m)",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      }
    }
  ]
}
```

The health panel counts successfully scraped agent targets, not “healthy Pods.” The HTTP panels inherit the recording rules' server-side boundary, namespace/workload/cluster scope and missing-numerator behavior. No-data is not zero failures; the dashboard requires the stated sources and labels.

## Upgrade Strategy

### Review Before Rolling Out

Cilium tests upgrades and rollbacks **between consecutive minor releases only**. First update the current minor to its latest patch and read every intervening release's required changes. The target below is 1.20.1; it is not a supported direct jump from the old 1.16/1.17 examples.

Record the **initially installed minor** for `upgradeCompatibility`, not an arbitrarily selected target/current version. Export existing user values, review renamed/removed keys and save the revised configuration as `reviewed-values.yaml`. Keep this file and exported values private if they contain sensitive material:

```bash
set -eu
umask 077
CILIUM_TARGET_VERSION=1.20.1
: "${INITIAL_CILIUM_MINOR:?Set the initial installed Cilium minor, for example 1.19}"
helm get values cilium -n kube-system -o yaml > old-values.yaml
helm history cilium -n kube-system
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
test -s reviewed-values.yaml
helm template cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" > candidate.yaml
```

Review the generated resources and the official preflight procedure before the next step. `helm diff` is an optional separately installed plugin, not built-in Helm. Avoid `--reuse-values` for a version change; it can hide newly introduced chart defaults.

Only after confirming a supported path and a maintenance/recovery plan, the same shell/session can perform the reviewed change:

```bash
set -eu
: "${CILIUM_TARGET_VERSION:?Use the previously reviewed target version}"
: "${INITIAL_CILIUM_MINOR:?Use the previously reviewed initial installed minor}"
helm upgrade cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" --wait --timeout 10m
cilium status --wait
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator hubble-relay
```

`cilium connectivity test` is a useful **active** validation that creates test workloads and network traffic; run it in the planned test environment, not as an assumed read-only status command. Check application-specific negative policy tests and long-lived connections as well as component readiness.

### Canary Strategy

A node label alone does not select a different Cilium version. Do not deploy a second overlapping Cilium DaemonSet to create a canary: agents share node-level networking resources and cluster configuration. Validate the release in a representative test cluster first. Any controlled per-node rollout must use a supported single-owner mechanism, account for Operator/shared-ConfigMap changes and bound temporary version skew. During steady state all Cilium components should run the same release.

### Rollback

Choose a **reviewed compatible** Helm revision after checking whether new CRDs/features/state prevent a safe downgrade:

```bash
set -eu
helm history cilium -n kube-system
: "${CILIUM_ROLLBACK_REVISION:?Set the reviewed, compatible Helm revision}"
helm rollback cilium "$CILIUM_ROLLBACK_REVISION" \
  -n kube-system --wait --timeout 10m
cilium status --wait
```

Do not blindly downgrade to 1.15 or assume Helm revision rollback reverses node networking, CRD schemas and every newly used feature. Keep the release-specific rollback prerequisites and recovery tests with the change.

## Troubleshooting

### Node and Policy State

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ct list global
```

The host `cilium` CLI manages the installation; `cilium-dbg` inside an Agent inspects local datapath state. `exec ds/cilium` chooses one Pod, so target the actual affected node's Pod during an incident. Listing CT entries can produce substantial output; it is not a reliable occupancy measurement by `wc -l`.

### Envoy and Latency

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config listeners
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config routes
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config clusters
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics
```

Use the supported admin command/socket path rather than assuming an unauthenticated TCP listener at port 9901 or a `curl` binary inside the container. Distinguish no L7 redirect, unavailable upstream, policy deny, connection saturation and slow application responses. Use the observed histogram's correct unit and labels from the Ingress/Gateway and observability guides.

### Temporary Debugging and Logs

```yaml
debug:
  enabled: true
  verbose: flow envoy policy
```

`debug.verbose` is a space-separated string, not a mapping of booleans. Enable only required groups during a bounded investigation and restore the original logging level afterward.

```bash
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --since=30m --tail=1000
kubectl -n kube-system logs -l k8s-app=cilium-envoy -c cilium-envoy --since=30m --tail=1000
cilium sysdump --output-filename cilium-audit
```

The separate Envoy DaemonSet uses the `k8s-app=cilium-envoy` selector. A sysdump is a collection operation with cluster access and may include sensitive configuration/logs; inspect the archive before sharing it. It is not a bare host `cilium-bugtool` invocation.

## EKS-Specific Guidance

### ENI Mode and AWS VPC CNI Chaining

These are different designs. Cilium ENI IPAM manages ENIs/addresses through its Operator; AWS VPC CNI chaining leaves address allocation with AWS VPC CNI and has its own L7/encryption limitations. Use the matching installation procedure.

An IPv4 ENI overlay is:

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
ipv4:
  enabled: true
ipv6:
  enabled: false
cluster:
  name: example-cluster
```

`eni.enabled` selects the AWS Operator behavior and associated chart defaults. Keep a unique cluster name to avoid ambiguous ENI garbage-collection ownership. Do not add a universal `10.0.0.0/8` cluster-pool range to ENI mode, and do not hard-code a masquerade interface without checking the actual node devices and routing requirements.

`enableAWSSecurityGroups` is not a chart value. ENI security groups come from the supported `eni.nodeSpec.securityGroups`/`securityGroupTags` or the documented inheritance behavior. This is not automatic translation of Kubernetes policies into AWS SecurityGroupPolicy objects.

The **general ENI IPAM reference documents IPv6 as Beta**, including dual-stack subnet/prefix and IAM prerequisites, while the 1.20.1 EKS installation page still says IPv4-only. This example deliberately uses IPv4 and records that source discrepancy. Do not erase the Beta feature or claim a fully validated EKS IPv6 recipe from the general reference alone.

EKS Auto Mode and Fargate do not support this alternate-CNI DaemonSet installation path. EKS Hybrid Nodes use their own AWS-supported Cilium guidance and matrix; do not transfer that support claim to an arbitrary self-managed EC2 Cilium release.

### Node OS and Capacity

EKS stopped publishing EKS-optimized AL2 AMIs on **November 26, 2025**; 1.32 was their last Kubernetes series. Select an appropriate supported AL2023 or Bottlerocket AMI and verify its actual kernel/architecture and Cilium feature requirements. A general Linux compatibility entry mentioning AL2 is not current EKS AMI lifecycle support.

Choose instance families and sizes from measured CPU, memory, network/packet limits, ENI/IP capacity, availability and cost. The former fixed m6i/c6i/r6i recommendation was not a sizing benchmark. Verify every DaemonSet and workload image on both AMD64 and Arm64 if using mixed architectures.

### IAM

Use a role dedicated to the Cilium Operator through the supported installation identity mechanism; review its trust policy and credential access separately. The former policy omitted required operations such as `AttachNetworkInterface`, `DescribeInstanceTypes`, `DescribeRouteTables` and `CreateTags`, so it was not a complete ENI allocator policy.

The versioned ENI reference lists base and conditional API permissions. Account for ENI garbage collection, excess-IP release, instance filters and optional IPv6 allocation. Split read/list and mutation permissions according to AWS service authorization support; scope supported mutations to the intended region/resources/tags. Some describe operations require `Resource: "*"`, so a wildcard alone is not proof of either correctness or excessive access. A complete account-specific least-privilege policy also needs actual IAM/resource context and API validation; this guide does not claim to have provisioned one.

## Further Reading

Continue with the [security](./03-security.md), [observability](./04-observability.md) and [Ingress/Gateway](./05-ingress-gateway.md) guides for their complete prerequisites and examples.

- [Cilium 1.20.1 Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [System requirements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [Performance tuning](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/performance/tuning.rst)
- [Upgrade procedure](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/upgrade.rst)
- [Upgrade and rollback restrictions](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/upgrade-warning.rst)
- [Istio integration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst)
- [CNI migration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/k8s-install-migration.rst)
- [CEC resource parser](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [ENI allocation, security groups and permissions](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
- [EKS installation caveats](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst)
- [EKS AL2 AMI retirement](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [EKS alternate CNI support](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Cilium Envoy diagnostics](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/cmdref/cilium-dbg_envoy_admin_config.md)
- [Linux TCP sysctls](https://docs.kernel.org/networking/ip-sysctl.html)
- [Kubernetes disruption budgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [IAM resource-level permission troubleshooting](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
