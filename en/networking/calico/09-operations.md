# Part 9: Calico Operations Guide

> **Reviewed baseline**: Calico 3.32.2 / Operator 1.42.6 / Kubernetes 1.34–1.36 tested by Calico.
> **Last Updated**: September 12, 2026

## Overview

This chapter provides comprehensive operational guidance for Calico deployments, covering installation, monitoring, troubleshooting, upgrades, and best practices for production environments.

Operations form a feedback loop: validate the installation, observe its behavior, diagnose changes, and retain recoverable configuration/state before upgrades. A configuration export and a tested datastore recovery serve different purposes.

## Installation Guide

Use one installation owner and a profile that matches the platform. The following example is for a **fresh self-managed Linux cluster with full Calico CNI**, Iptables and VXLAN. Prepare a nonoverlapping Pod CIDR, compatible node OS/kernel, Kubernetes API connectivity and underlay UDP 4789 connectivity between eligible nodes. It is not the VPC CNI policy-only configuration; use [Part 8](08-eks-integration.md) for EKS. Review [networking modes](03-networking-modes.md) before choosing a different overlay/BGP design.

### Tigera Operator Manifests

Calico 3.32 requires the separate Calico CRDs as well as the operator manifest:

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl wait --for=condition=Available deployment/tigera-operator \
  -n tigera-operator --timeout=300s
```

Save the following as `installation.yaml`, replacing the example Pod CIDR to match the prepared cluster. Omit MTU to use the operator's detection; do not substitute a guessed MTU for measurement of the actual path.

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f installation.yaml
```

BGP is disabled in this VXLAN example; BGP diagnostics are relevant only if your chosen profile enables it. Calico API server and Goldmane/Whisker are OSS components. The current OSS flow-logs guide marks the observability feature as tech preview; assess that status before relying on it operationally.

Leave component resource sizing and Typha scaling with the operator until measurements justify supported overrides. Arbitrary fixed memory limits, unsupported `typhaDeployment.spec.replicas`/`minReadySeconds` overrides, or a `KubeControllers` entry in the legacy `componentResources` list are not a production configuration. Use the versioned Installation API; see [architecture](02-architecture.md) and [scaling](07-advanced-topics.md).

### Helm Alternative

The Helm chart installs the same operator. Save this as `calico-values.yaml`; use this path instead of installing a second operator with manifests.

```yaml
installation:
  enabled: true
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --namespace tigera-operator --version v3.32.2 \
  -f calico-values.yaml > calico-rendered.yaml

# Apply only after reviewing the prepared cluster and rendered resources.
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator --create-namespace --version v3.32.2 \
  -f calico-values.yaml
```

Top-level `podAnnotations` applies to the operator Pod. It does not enable Felix metrics or set up Prometheus scraping for every component. Configure metrics explicitly in the monitoring section below. `manageCRDs: true` lets the operator manage CRDs after startup; upgrade ordering for new fields is covered later.

### Direct Manifest Alternative

For an installation already managed by direct manifests, use the matching release/profile and preserve its customization. Review the downloaded file before applying it:

```bash
curl -fL https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml \
  -o calico.yaml
```

Edit the relevant configuration, including the Pod CIDR and enabled networking mode. A global `sed` replacement can change an example or commented value without configuring the actual IP pool. Do not mix direct-manifest resources in `kube-system` with an operator installation in `calico-system`.

### Validate Installation

```bash
kubectl get tigerastatus
kubectl get installation default -o yaml
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get nodes -o wide
```

For direct manifests, inspect the actual namespace and resource names. Ready components do not prove policy enforcement or application reachability. Test required Service/DNS paths and both allowed and denied application connections with controller-managed workloads. Use the actual API server HTTPS endpoint and appropriate authentication when checking API access; an HTTP request to `kubernetes.default` is not an authenticated API health test.

## calicoctl Command Reference

Install the matching **3.32.2** binary from the official release and verify its checksum as described in [the installation chapter](01-introduction.md). Release assets include Linux AMD64/ARM64, macOS AMD64/ARM64 and Windows AMD64; select the actual host architecture. Do not execute PowerShell download commands inside Bash or use an older client after an upgrade without investigating the compatibility warning.

For Kubernetes datastore access, a typical Unix shell configuration is:

```bash
export DATASTORE_TYPE=kubernetes
export KUBECONFIG="$HOME/.kube/config"
calicoctl version
calicoctl get nodes -o wide
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy
calicoctl get tier
calicoctl get networkset -A
calicoctl get globalnetworkset
calicoctl get workloadendpoint -A
calicoctl get hostendpoint
calicoctl get ippool -o yaml
calicoctl get bgpconfiguration default -o yaml
calicoctl get bgppeer -o wide
calicoctl get felixconfiguration default -o yaml
```

The kubeconfig must select the intended cluster and have appropriate RBAC. You can supply a Calico API configuration file explicitly with `--config`; do not assume an arbitrary path under `~/.config` is auto-discovered. For direct etcdv3 datastore access, use its supported configuration and certificate validation. This is a different deployment profile, not permission to access an EKS-managed etcd service.

### Local Node Diagnostics

`calicoctl node status` reports the **local node's BGP status**. It is not a remote, cluster-wide readiness check merely because a kubeconfig is set. Run it on the intended node with the documented access, or inspect that node's BIRD socket as shown below.

`calicoctl node diags` collects a diagnostic archive on the selected node. Its supported `--log-dir` flag selects the **input log directory**; there is no `--output-dir` flag in 3.32.2. The implementation requires root and can invoke a privileged diagnostic container and signal Felix to dump state. Treat it as deliberate evidence collection, not a passive health probe. Protect the resulting archive and use the output path printed by the command.

### Calico IPAM

Run these only when **Calico IPAM** allocates the addresses. With VPC CNI, host-local or another IPAM, troubleshoot the actual allocator.

```bash
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
calicoctl ipam show --show-configuration
calicoctl ipam show --ip=10.244.0.15
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

`--show-blocks` reports block utilization. Use BlockAffinity records for the block-to-node association; it is not the same as the Kubernetes Node PodCIDR. `--ip` is a read-only allocation lookup. A report can identify candidates for investigation; a missing Pod alone is not proof that an allocation is safe to release.

There is no `ipam release --block` or `--handle` flag in the reviewed CLI. Report-based release has allocation sequence checks and still requires the cleanup procedure in [advanced IPAM](07-advanced-topics.md). `ipam split NUMBER --cidr=...` is a real command, but splits an **IP pool**, not an allocation block; it requires a locked datastore and a power-of-two split count. It is a planned migration operation, not a routine fix for a stuck Pod.

### Resource Changes and Exports

`get`, `create`, `apply`, `replace`, `patch` and `delete` operate on supported resource types. Prefer an explicit type/namespace, review the complete policy set and preserve unrelated fields when patching. For example, a change to logging belongs in the existing FelixConfiguration or its GitOps owner, not a replacement object containing only the new field.

`calicoctl get all` is not an all-resource backup. Enumerate the required resource types and include Kubernetes policies and operator resources separately. `calicoctl get ... --export` exists, but the reviewed CLI ignores it when no resource name is supplied. It does not turn a list export into a complete portable disaster-recovery backup. See the backup section below.

## Prometheus Metrics

Confirm names, types and labels from the **installed version's `/metrics` output**. Dataplane-specific series are not guaranteed to exist in every profile, and a missing series is not a zero. The names below were checked against Calico 3.32.2 source and the official metric references.

### Enable Component Metrics

Felix metrics are disabled by default; its default port is **9091**. Typha metrics are also disabled by default; the Typha binary's default metrics port is **9091**, while this operator example explicitly selects **9093**. kube-controllers metrics are enabled by default on **9094**.

For an existing operator installation, merge these settings through its configuration owner:

```bash
kubectl patch felixconfiguration default --type=merge \
  -p '{"spec":{"prometheusMetricsEnabled":true,"prometheusMetricsPort":9091}}'
kubectl patch installation default --type=merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl get service calico-typha-metrics -n calico-system
kubectl get service calico-kube-controllers-metrics -n calico-system
```

The operator creates the Typha metrics Service when `typhaMetricsPort` is configured. Do not replace it with a conflicting Service. A direct-manifest installation needs its own Typha environment configuration and Service. Restrict metrics access appropriately; host-network endpoints can require host/network security controls beyond workload NetworkPolicy.

### Metric Names and Meaning

| Metric | Type / meaning |
| --- | --- |
| `felix_active_local_endpoints` | Gauge; local workload **and host** endpoints. Zero can be legitimate and is not a readiness test |
| `felix_active_local_policies` | Gauge; policies active on this node. Summing it counts local policy instances, not unique cluster policies |
| `felix_cluster_num_hosts`, `felix_cluster_num_policies` | Cluster-wide gauges observed by each Felix; do not sum identical copies across nodes |
| `felix_int_dataplane_failures` | Counter; failed dataplane updates that will be retried; no `_total` suffix in the reviewed metric name |
| `felix_int_dataplane_apply_time_seconds` | **Summary** of incremental dataplane update time; exports quantiles, `_sum` and `_count`, not histogram buckets |
| `felix_iptables_restore_calls`, `felix_iptables_restore_errors` | Counters for iptables-restore calls/errors in the iptables dataplane |
| `felix_log_errors`, `felix_logs_dropped` | Errors writing process logs / logs dropped by blocked output; not ERROR-level entry counts or denied packets |
| `typha_connections_active` | Gauge; open connections, including handshakes |
| `typha_connections_streaming{syncer="..."}` | Gauge; clients that completed the handshake and are streaming |
| `typha_connections_accepted` | Counter; accepted connections |
| `typha_connections_dropped` | Counter; connections dropped **for rebalancing**, not a general network-failure count |
| `typha_cache_size{syncer="..."}` | Gauge; key/value entries in the cache |
| `typha_updates_total{syncer="..."}` | Counter; updates **received from** the datastore syncer |
| `ipam_allocations_in_use{ippool="...",node="..."}` | kube-controllers gauge; Calico IPAM addresses allocated to workloads/interfaces |
| `ipam_ippool_size{ippool="..."}` | kube-controllers gauge; total addresses in the pool CIDR |
| `ipam_allocations_gc_candidates` | Potential leaks under investigation, not permission to release addresses |

BIRD's control socket is not a Prometheus exporter. Names such as `bird_protocol_up` or `calico_bgp_peer_status` require a separately selected exporter/collector with verified labels and semantics; this installation does not produce those series. Use the BGP diagnostics below or the [CalicoNodeStatus approach](04-bgp-deep-dive.md) and only add exporter alerts after checking actual output.

### ServiceMonitor Wiring

This example assumes Prometheus Operator CRDs and the `monitoring` namespace already exist. Match the ServiceMonitor labels to your Prometheus resource's `serviceMonitorSelector`, and ensure its `serviceMonitorNamespaceSelector` includes this namespace. Match PrometheusRule labels to its `ruleSelector` as well. A valid custom resource that is not selected produces no scrape/rule.

The following **separate Services** avoid changing operator-owned Services and give all three a named `http-metrics` port. If your installation already scrapes these endpoints, reuse that setup instead of adding duplicate scrapes. The ServiceMonitor's `jobLabel` produces the `calico-felix`, `calico-typha` and `calico-kube-controllers` jobs used below.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-felix-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-felix
spec:
  clusterIP: None
  selector:
    k8s-app: calico-node
  ports:
  - name: http-metrics
    port: 9091
    targetPort: 9091
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-typha-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-typha
spec:
  clusterIP: None
  selector:
    k8s-app: calico-typha
  ports:
  - name: http-metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-kube-controllers-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-kube-controllers
spec:
  clusterIP: None
  selector:
    k8s-app: calico-kube-controllers
  ports:
  - name: http-metrics
    port: 9094
    targetPort: 9094
    protocol: TCP
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-components
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  jobLabel: audit.calico/component
  selector:
    matchExpressions:
    - key: audit.calico/component
      operator: Exists
  namespaceSelector:
    matchNames:
    - calico-system
  endpoints:
  - port: http-metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

Check endpoint discovery/RBAC, network access and the Prometheus Targets page. A ServiceMonitor `endpoints.port` selects the **Service port name**; it does not mean container port number. Confirm each discovered target, rather than scraping a load-balanced Service address and assuming every node is represented.

## Grafana Dashboard

Use the configured Prometheus datasource and current time-series/stat panels. The following are panel queries, not a complete importable dashboard. Select one cluster's metrics; a central multi-cluster datasource needs the cluster label preserved in selectors and aggregations.

| Panel | PromQL |
| --- | --- |
| Endpoints per node | `felix_active_local_endpoints{job="calico-felix"}` |
| Active policies per node | `felix_active_local_policies{job="calico-felix"}` |
| Observed cluster policy count | `max(felix_cluster_num_policies{job="calico-felix"})` |
| Dataplane retries per second | `rate(felix_int_dataplane_failures{job="calico-felix"}[5m])` |
| Typha streaming connections | `typha_connections_streaming{job="calico-typha"}` |
| Local summary p99 | `felix_int_dataplane_apply_time_seconds{job="calico-felix",quantile="0.99"}` |

A per-process summary quantile is not a cluster-wide p99 and cannot be combined by `histogram_quantile`. For mean incremental apply duration while updates are occurring:

```promql
rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
/ rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])
```

With no observations, the mean is undefined (`0/0`), not proof of zero latency. Do not invent `_bucket` series for this Summary or retain unverified `felix_iptables_restore_time_seconds` queries. Use the available operation counters and dataplane timing metric.

Calico IPAM address utilization can be inspected with:

```promql
sum by (ippool) (
  max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
)
/ max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})
```

The `max` per pool/node avoids double-counting identical controller observations, then the sum totals allocations across nodes. This is **address utilization**, not blocks consumed or a guarantee of allocatable capacity for a particular node. Pool selectors, strict affinity, block caps, reserved/tunnel addresses and other constraints still matter. It does not describe VPC CNI allocation; empty/missing/zero-capacity metrics need separate investigation.

## Alert Rules

These example rules assume the jobs above, a single selected cluster and kube-state-metrics for the DaemonSet metric. Enable missing-target rules only for components you expect to run. Adapt selectors if reusing existing monitoring, and tune thresholds/durations to your workload.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  groups:
  - name: calico.rules
    rules:
    - alert: CalicoDaemonSetUnavailable
      expr: kube_daemonset_status_number_unavailable{namespace="calico-system",daemonset="calico-node"}
        > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Calico DaemonSet has unavailable Pods
        description: Inspect the affected node, rollout and kube-state-metrics data.
    - alert: CalicoMetricsScrapeFailed
      expr: up{job=~"calico-(felix|typha|kube-controllers)"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Calico scrape failed for {{ $labels.job }} on {{ $labels.instance
          }}
    - alert: CalicoMetricsTargetsMissing
      expr: |-
        absent(up{job="calico-felix"})
        or absent(up{job="calico-typha"})
        or absent(up{job="calico-kube-controllers"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: No discovered metrics targets for {{ $labels.job }}
    - alert: CalicoDataplaneRetries
      expr: rate(felix_int_dataplane_failures{job="calico-felix"}[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Dataplane updates are being retried on {{ $labels.instance }}
    - alert: CalicoDataplaneMeanSlow
      expr: |-
        (rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
        / rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])) > 0.5
        and (rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m]) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Mean dataplane update time exceeds 0.5s on {{ $labels.instance }}
    - alert: CalicoIPAMHighAddressUsage
      expr: |-
        (sum by (ippool) (
          max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
        )
        / max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})) > 0.8
        and on (ippool)
        (max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"}) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High address utilization in Calico IP pool {{ $labels.ippool }}
        description: Address utilization is {{ $value | humanizePercentage }}; inspect
          per-node eligibility and block constraints.
```

`up == 0` detects a discovered target whose scrape failed. It does not detect a target that disappeared entirely; the `absent` rules detect loss of **all** targets for an expected component. Detecting one missing node among healthy nodes needs comparison with the expected node/DaemonSet inventory. An alert missing from the UI is not proof of health if its metric or rule was never loaded.

A Typha connection decrease or rebalance counter increase can be expected during scaling. Correlate persistent streaming/client lag and component availability before calling it an incident. Likewise, zero local endpoints does not mean Felix is unready. Use actual readiness/rollout status and separate synthetic allow/deny tests.

## Log Analysis and Troubleshooting

### Start with the Affected Workload and Node

A Pending Pod may be unschedulable before any CNI is called. Inspect events and `spec.nodeName` first. For a CNI/IP allocation error, identify the allocator and inspect the affected node's kubelet/CNI logs; Felix's process log is not the source of every Pod IPAM error.

```bash
CALICO_NAMESPACE=calico-system
WORKLOAD_NAMESPACE=calico-demo
WORKLOAD_POD=replace-with-actual-pod

kubectl describe pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE"
CALICO_NODE=$(kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" \
  -o jsonpath='{.spec.nodeName}')
test -n "$CALICO_NODE" || { echo "Pod is not scheduled to a node" >&2; exit 1; }
kubectl get pods -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o wide

# Select the actual agent Pod on this node, including during a rollout.
CALICO_POD=replace-with-actual-calico-node-pod
kubectl logs -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node \
  --since=15m --tail=200 --timestamps
```

Use explicit time and tail limits. With selectors, `kubectl logs` can default to a short tail; a requested time window is not proof that all lines in that window were returned. For a restarted container, inspect its previous log where available. Preserve retrieval errors rather than converting them into “no errors.”

Felix process logs describe programming and component activity. Turning `logSeverityScreen` to Debug does not create a per-packet policy decision log. Record the original field and its configuration owner before a temporary change, then restore the exact prior value or absence rather than assuming Info was the previous setting. File/syslog output also depends on its configured path and runtime.

### Address Allocation and Connectivity

| Symptom | Check before changing state |
| --- | --- |
| No scheduled node | Scheduler events, capacity, affinity and taints; this is not yet an IPAM diagnosis |
| CNI allocation failure | The actual allocator's logs, pool/address capacity, selector eligibility, block/affinity limits and API access |
| Pod IP reachable but Service fails | Endpoints/EndpointSlices, Service ports, kube-proxy or BPF Service handling, DNS and policy |
| Small packets work, larger ones fail | Underlay/overlay MTU, fragmentation/PMTUD and return path |
| Intended policy does not block | Actual endpoint identity/labels, direction, namespace selectors, tier/order, prior allow rules, host-network/other-interface limitations and established connections |

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip route show
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip -d link show
calicoctl get networkpolicy -n "$WORKLOAD_NAMESPACE" -o yaml
calicoctl get globalnetworkpolicy -o yaml
calicoctl get tier -o yaml
calicoctl get workloadendpoint -n "$WORKLOAD_NAMESPACE" -o yaml
kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" --show-labels
```

Do not select the first `calico-node` Pod in the cluster and assume it is on the failing workload's node. ICMP success/failure alone does not validate TCP or HTTP policy. Use an approved diagnostic workload with known tools and the application's real protocol/port.

For Calico IPAM, use the read-only commands above and the [IPAM cleanup procedure](07-advanced-topics.md). Pool CIDR and blockSize are immutable; adding a nonoverlapping eligible pool is a planned capacity change, not an in-place CIDR expansion. Do not release an address or restart an agent before proving the cause.

For operator installations, MTU and address autodetection belong to `Installation.spec.calicoNetwork`, with tunnel-specific Felix fields where documented. `FelixConfiguration.spec.mtu` and `ipAutoDetectionMethod` are not the reviewed APIs. Follow [MTU/networking guidance](03-networking-modes.md), preserve other settings and validate new/existing Pods separately.

### BGP Diagnostics

Run BGP checks only for a profile that uses BGP. On the selected `calico-node` Pod, use the actual BIRD socket:

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
calicoctl get bgpconfiguration -o yaml
calicoctl get bgppeer -o yaml
calicoctl get bgpfilter -o yaml
```

Use `bird6.ctl` for the corresponding IPv6 daemon when deployed. Verify local/peer ASNs, chosen source address, TCP 179 in both directions, authentication/TTL settings, route filters and the expected route advertisements. A successful TCP connection is not proof that the session established or the required prefixes were accepted. Check the packaged log configuration before assuming a log file exists; the released container's BIRD run/log scripts determine where it writes. See [BGP deep dive](04-bgp-deep-dive.md).

## Health Check Automation

The following **operator-installation status check** runs from a management environment with Bash, jq and a compatible kubectl. It performs read-only API/log requests, checks the observed DaemonSet generation and replica availability, and fails if a request fails. It does not inspect BGP sockets, validate packet forwarding or prove every policy is correct.

```bash
#!/usr/bin/env bash
# calico-status-check.sh: operator component status and bounded log collection.
set -euo pipefail
CALICO_NAMESPACE=${CALICO_NAMESPACE:-calico-system}

if ! calico_ds_json=$(kubectl get daemonset calico-node -n "$CALICO_NAMESPACE" \
  --request-timeout=20s -o json); then
  echo "Unable to read calico-node DaemonSet status" >&2
  exit 2
fi
if ! jq -e '
  .status.desiredNumberScheduled as $desired
  | ($desired > 0)
    and (.status.observedGeneration >= .metadata.generation)
    and (.status.updatedNumberScheduled == $desired)
    and (.status.numberReady == $desired)
    and (.status.numberAvailable == $desired)
    and ((.status.numberUnavailable // 0) == 0)
' <<<"$calico_ds_json" >/dev/null; then
  echo "Calico DaemonSet is not fully observed, updated and available" >&2
  exit 1
fi

if ! calico_status_json=$(kubectl get tigerastatus --request-timeout=20s -o json); then
  echo "Unable to read operator component status" >&2
  exit 2
fi
if ! jq -e '
  (.items | length) > 0 and all(.items[];
    any(.status.conditions[]?; .type == "Available" and .status == "True")
    and any(.status.conditions[]?; .type == "Progressing" and .status == "False")
    and any(.status.conditions[]?; .type == "Degraded" and .status == "False")
  )
' <<<"$calico_status_json" >/dev/null; then
  echo "Operator components are unavailable, progressing, degraded or missing conditions" >&2
  exit 1
fi

if ! calico_logs=$(kubectl logs -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  -c calico-node --since=15m --tail=200 --timestamps --prefix \
  --request-timeout=20s); then
  echo "Unable to retrieve selected Calico logs; do not report no errors" >&2
  exit 2
fi
printf '%s\n' "$calico_logs"
echo "Component status checks passed; review these bounded logs and test application policy separately."
```

An empty/unscheduled DaemonSet, stale status or missing component conditions is not a successful check. Logs are limited to the selected window/tail and still need interpretation. A counter or ERROR word alone is not equivalent to a live outage.

To schedule this in a CronJob, first package and validate those tools and the script in an approved image. Use a dedicated ServiceAccount with read access to the DaemonSet, Pods/Pod logs and TigeraStatus; do not reuse the privileged `calico-node` identity. Configure concurrency, deadlines and failure reporting. The `calico/ctl` image is not a general-purpose Bash/kubectl diagnostic environment, and a normal Job cannot inspect another node's BIRD socket without additional deliberate access. No working in-cluster CronJob is implied by this local script.

## Version Upgrade and Recovery

### Prepare the Transition

```bash
calicoctl version
kubectl version --output=yaml
kubectl get deployment tigera-operator -n tigera-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
kubectl get tigerastatus
kubectl get daemonset calico-node -n calico-system -o wide
helm get values calico -n tigera-operator -o yaml
```

The Helm command applies only to a Helm-managed installation. Inventory the actual installed images, CRDs, datastore, node OS/kernel, dataplane and Kubernetes compatibility. Preserve owned manifests/values, policies and a tested recovery plan. `kubectl version --short` is not a current command option.

Follow the [3.32 upgrade procedure](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade) for the actual source version and installation method. Review the OwnerReference/UID migration notes when crossing the relevant releases. Pin the target version and update calicoctl as well.

For Helm, either apply the matching Calico CRDs through their owner before the new operator, or use `manageCRDs: true` and wait until the operator has installed them before using new fields. Updating the operator is not a reason to blindly overwrite field ownership with `--force-conflicts`. After the reviewed change, monitor operator, calico-node and the other configured components, then test allow/deny paths during and after rollout.

An operator reconciles its managed DaemonSet. Removing the agent from “canary” nodes with an affinity patch does not deploy a safe canary and can leave those nodes without enforcement. Test the version/configuration in a representative isolated environment and follow supported rollout controls. Do not improvise a second competing node DaemonSet.

### Recovery Limits

`helm rollback`, applying an older operator, or applying a configuration export does not automatically undo CRD/data migration or restore packet-processing state. Check the source/target release's supported downgrade path and stored data before choosing recovery. An Installation resource remaining present is not proof of no data loss.

For EKS control-plane recovery, use the current eligibility and seven-day rollback limits described in [Part 8](08-eks-integration.md). Calico/add-ons and application compatibility remain separate responsibilities.

## Backup and Disaster Recovery

### Separate Configuration Inventory from State Recovery

| Material | Purpose and limitation |
| --- | --- |
| Git-managed manifests/Helm values and version records | Desired configuration and ownership; preserve matching CRD definitions and images |
| Calico policies, tiers, sets, pools, BGP/filter and controller configuration | Configuration inventory; include namespaced, staged and global resources actually used |
| Kubernetes NetworkPolicy, namespace/ServiceAccount labels and related RBAC | Policy identity/dependencies that a Calico-only export omits |
| Host/node/endpoints and IPAM state | Runtime/topology-dependent data; do not replay old node addresses or allocations into another cluster blindly |
| Datastore backup and application data | A consistent recovery mechanism and separately protected credentials/data; YAML lists are not an atomic datastore snapshot |

There is no `kubectl export` command. `calicoctl get TYPE -o yaml` creates a resource export; the `--export` flag has the named-resource limitation described above. For self-managed Kubernetes/etcd, follow the [Kubernetes etcd backup/recovery procedure](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) with matching versions and restore testing. Managed services require their supported recovery approach; this does not provide EKS etcd access.

### Protected Configuration Inventory Example

This script exports a **declared subset** for a 3.32 operator installation using Calico IPAM. It requires Bash, calicoctl, kubectl and sha256sum. The target directory must not exist; partial exports retain `STATE=incomplete`. It does not collect Secrets, external IAM/network devices, all operator custom resources or complete IPAM allocation state. Extend the inventory deliberately for the installed features and secure the separate credential backup.

```bash
#!/usr/bin/env bash
# calico-config-inventory.sh: protected configuration inventory, not a datastore snapshot.
set -euo pipefail
umask 077
CALICO_EXPORT_DIR=${1:?Usage: calico-config-inventory.sh NEW_EXPORT_DIRECTORY}
mkdir -m 700 -- "$CALICO_EXPORT_DIR"
printf '%s\n' incomplete > "$CALICO_EXPORT_DIR/STATE"

for calico_kind in node ippool ipreservation bgpconfiguration bgppeer bgpfilter \
  globalnetworkpolicy stagedglobalnetworkpolicy globalnetworkset \
  felixconfiguration kubecontrollersconfiguration ipamconfiguration \
  tier hostendpoint profile; do
  calicoctl get "$calico_kind" -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
for calico_kind in networkpolicy stagednetworkpolicy stagedkubernetesnetworkpolicy \
  networkset workloadendpoint; do
  calicoctl get "$calico_kind" -A -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
kubectl get installation default -o yaml > "$CALICO_EXPORT_DIR/installation.yaml"
kubectl get networkpolicies.networking.k8s.io -A -o yaml \
  > "$CALICO_EXPORT_DIR/kubernetes-networkpolicies.yaml"
kubectl get namespaces -o yaml > "$CALICO_EXPORT_DIR/namespaces.yaml"
kubectl get serviceaccounts -A -o yaml > "$CALICO_EXPORT_DIR/serviceaccounts.yaml"
(
  cd -- "$CALICO_EXPORT_DIR"
  sha256sum ./*.yaml > SHA256SUMS
)
printf '%s\n' complete > "$CALICO_EXPORT_DIR/STATE"
echo "Configuration inventory completed: $CALICO_EXPORT_DIR"
```

A `complete` marker means the declared queries and checksums completed, not that the snapshot is transactionally consistent or disaster recovery was tested. Treat exports as sensitive infrastructure data. Verify checksums, retain copies outside the failure domain and rehearse recovery with the actual datastore/versions.

### Restore Planning

1. Restore a compatible control plane/datastore and the required CRDs/operator through the chosen recovery method. A new cluster and a same-cluster recovery have different identity/IPAM requirements.
2. Review namespace/ServiceAccount identity, labels and RBAC, then restore owned declarative configuration in dependency order, including tiers and sets before dependent policies.
3. Review cluster-specific metadata, generated/controller-owned objects, old node addresses and allocations. Do not replay a raw dump as a portable desired-state manifest.
4. Verify IP allocation uniqueness, routes, encryption, Service/DNS behavior and both allowed and denied traffic before resuming normal change activity.

`calicoctl datastore migrate export/import` is a real **etcd-to-Kubernetes migration** workflow with datastore locking and rollback boundaries. It is not a generic backup shortcut for an existing Kubernetes datastore. Locking affects new Pods, and the documented migration cannot be rolled back after the Kubernetes datastore is unlocked. See the [migration procedure](https://docs.tigera.io/calico/latest/operations/datastore-migration).

## Operational Best Practices

### Policy and Access

Start default-deny validation in a selected test namespace with the required DNS, API, identity, monitoring and application dependencies. A blank global `all()` policy or an invented API-server/node label selector can cut off essential traffic. Pod and host endpoints have different policy paths; use [Part 5](05-network-policy.md) for scoped examples, tier semantics and host endpoint controls. Preserve an independently usable recovery path and test negative cases before widening scope.

### Flow Observability

Current OSS operator/Helm installations can use Goldmane and Whisker. The [OSS flow logs guide](https://docs.tigera.io/calico/latest/observability/view-flow-logs) marks this feature as tech preview and describes aggregated flows rather than one record per packet/connection. The old file/DNS logger fields and invented `FlowLogsFileReporter` names are not a valid OSS configuration.

```bash
kubectl get goldmane,whisker
kubectl port-forward -n calico-system service/whisker 8081:8081
```

The port-forward binds locally by default. Whisker/Goldmane contain sensitive workload/network data; configure authentication and access controls before exposing them elsewhere. For an upgrade from before these components existed, enable the relevant custom resources intentionally. Process debug logs, policy Log actions, aggregated flow logs and Prometheus metrics answer different questions.

### Performance and Resources

Measure endpoint/policy churn, dataplane programming time, queueing, memory and actual application traffic. Resync/refresh intervals are not Kubernetes API polling intervals; increasing them is not a universal API-load optimization. Use the actual `iptablesPostWriteCheckInterval` duration field, not the removed `...Secs` spelling. Preserve the installation owner's supported resource overrides and operator scaling.

Do not enable BPF, DSR or a guessed interface pattern as a generic tuning preset. [Part 6](06-ebpf-dataplane.md) covers kernel/platform requirements, Service handling, kube-proxy conflicts and rollback. Larger conntrack maps cost memory and do not remove all bottlenecks. Re-run the relevant workload and failure tests when a dataplane or resource change is justified.

The checks accompanying this guide are offline schema, query and script-fixture validation. They do not establish production capacity, successful cluster upgrade or disaster recovery.

## References

- [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Calico Installation API](https://docs.tigera.io/calico/latest/reference/installation/api)
- [Monitor component metrics](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Felix metrics](https://docs.tigera.io/calico/latest/reference/felix/prometheus)
- [Typha metrics](https://docs.tigera.io/calico/latest/reference/typha/prometheus)
- [kube-controllers metrics](https://docs.tigera.io/calico/latest/reference/kube-controllers/prometheus)
- [Calico troubleshooting](https://docs.tigera.io/calico/latest/operations/troubleshoot/troubleshooting)
- [Calico upgrade procedure](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)

## Next Steps and Quiz

Review the [glossary](glossary.md), [advanced topics](07-advanced-topics.md), [EKS integration](08-eks-integration.md), and the [Operations Quiz](../../quizzes/networking/calico/09-operations-quiz.md).
