# KEDA-based Autoscaling with Istio Metrics

> **Verification baseline**: KEDA/chart 2.20.2, Istio 1.31.0, Kubernetes 1.32–1.36
> **Last reviewed**: September 11, 2026

This guide explains scaling signals and their limits. It assumes existing workloads, verified metrics and sufficient cluster capacity. Examples targeting the same Deployment are **alternatives**: select one ScaledObject/HPA owner per target, not all the objects on this page.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prometheus Metrics-based Scaling](#prometheus-metrics-based-scaling)
4. [CloudWatch Metrics-based Scaling](#cloudwatch-metrics-based-scaling)
5. [Practical Scaling Strategies](#practical-scaling-strategies)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Reference: KEDA Installation](#reference-keda-installation)

## Overview

Kubernetes HPA supports resource, custom and external metrics through the corresponding APIs, including multiple metrics. CloudWatch can be integrated through an adapter; it is not inherently impossible with HPA. KEDA provides scalers, an external metrics API and activation management while still using HPA for ordinary replica scaling.

| Signal | Meaning | Use and limitation |
|---|---|---|
| `istio_requests_total` | HTTP/gRPC request counter | Rate can measure admitted load; choose one reporter and the actual target workload |
| `istio_request_duration_milliseconds_bucket` | Classic latency histogram buckets | Quantiles are quality observations, not guaranteed inverse-capacity signals |
| `istio_tcp_connections_opened_total` | Cumulative opened connections | Its rate is connection creation rate, not currently active connections |
| `istio_request_bytes_sum` | Cumulative observed HTTP request bytes | A rate measures throughput; scope reporters and workloads |
| `envoy_cluster_upstream_rq_pending_overflow` | Client-side cluster overflow counter | Diagnose pool limits/dependencies before deciding which workload, if any, should scale |

A calibrated demand/backlog metric is a starting point. Latency, errors and circuit-breaker events can result from downstream failures that more replicas will not fix. Stateful membership, storage and application semantics also constrain scaling; “stateful” or “latency-sensitive” alone does not select a safe autoscaling policy.

## Architecture

KEDA creates/configures an HPA for the scale target and exposes external metrics. The HPA controller requests metrics through that API and updates the target's `/scale` subresource; the target controller and scheduler then create/place Pods.

| Setting or component | Responsibility |
|---|---|
| KEDA `pollingInterval` | Trigger polling and activation, including 0→1 |
| HPA controller sync | Additional metric requests and 1→N decisions; default sync period 15 seconds, cluster configurable |
| `useCachedMetrics` | Optional KEDA metric caching between polls; not enabled in these examples |
| `activationThreshold` | Activation threshold for 0↔1, not a second HPA scale-down threshold |
| `cooldownPeriod` | Wait after inactivity before KEDA scales to 0, not a pause after every scale-down |
| HPA `behavior` | 1→N stabilization and rate-of-change limits |

With `minReplicaCount` above 0, do not use activation/cooldown as ordinary replica hysteresis. Capture→scrape→query→HPA→Pod startup/readiness all contribute delay; neither a 15-second poll nor zero stabilization guarantees immediate ready capacity.

### Metric Types and Ideal Arithmetic

Ignoring HPA tolerance, missing/unready Pods, limits and behavior policies:

- **AverageValue + total demand**: desired replicas ≈ `ceil(total metric / target per Pod)`.
- **Value + a workload-wide value**: desired replicas ≈ `ceil(current replicas × observed value / target value)`.

For 600 RPS at 100 RPS/Pod, AverageValue asks for 6 replicas. Dividing the query by 3 Pods first would feed 200 and incorrectly ask for 2. `count(up)` counts scrape targets and is not a safe replica divisor either.

With 4 replicas, a global 300ms latency and a Value target 200ms suggest 6 replicas. If adding replicas does not reduce that latency, repeated decisions can drive the workload to its cap. Treat latency/error ratio controllers as experiments requiring evidence of negative feedback, not production defaults.

## Prometheus Metrics-based Scaling

The examples assume an actual Deployment named `reviews` in `default`. A Service name is not a scale target. Released Bookinfo commonly uses Deployment names such as `reviews-v1`; adapt both `scaleTargetRef` and metric selectors to the real workload rather than assuming they match a Service.

Verify one scrape of each relevant proxy and the actual labels. The primary examples use `reporter="destination"` to avoid counting both request reports. This measures requests admitted at the target; edge rejections/queues may require an independently measured demand signal.

### 1. RPS-based Scaling

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

The query includes failed requests as load and returns total RPS. `threshold: "100"` is the target per replica for AverageValue, not a global “above 100 means add a Pod” switch. Do not divide by Pod count again.

`ignoreNullValues: "false"` makes missing, NaN or infinite Prometheus results errors in KEDA 2.20.2. A real zero counter rate remains 0. Configure and test fallback for source failures; do not silently convert arbitrary missing metrics to 0. Bootstrap the scrape/metric data contract before enabling the scaler.

Fallback here uses the higher of the configured floor and current replicas after the configured error threshold, still subject to HPA limits/behavior. It is not protection against a down KEDA metrics API or absent node capacity.

### 2. Latency-based Control: Conditional Experiment

This alternative explicitly uses Value for the workload-wide p95:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-latency-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

The query returns 0 only when the actual histogram count has zero rate. With absent telemetry it stays absent; invalid quantiles remain errors rather than healthy 0. A p95 of 0 in an idle window is an intentional control value, not an observed zero-duration request.

Multiple quantiles are also Value metrics:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-quantile-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p50
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.5, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '50'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p99
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.99, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '500'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

HPA chooses the largest desired replica count, not an average or a weighted blend. Quantiles are correlated; more triggers do not inherently improve stability or establish a latency guarantee.

### 3. Error-rate Control: Conditional Experiment

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-error-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: error-percent
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (100 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
          and on() (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '5'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

This is a workload-wide 5xx/zero-status percentage with a Value target. Known idle traffic returns 0; no telemetry is not fabricated as0. Only use an error-based controller after establishing that replica shortage causes those errors. Dependency outages, authorization failures or client-side pool limits can make scaling ineffective or harmful.

### 4. Composite Metrics

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-composite-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

The RPS input is total demand with AverageValue; the latency input is Value. HPA takes the largest recommendation. The scale-up `selectPolicy: Max` chooses the larger permitted change: a five-Pod policy is not an absolute cap when the percentage policy permits more. These alternatives still need capacity and workload tests.

## CloudWatch Metrics-based Scaling

CloudWatch source cadence, publication latency, aggregation period, lookback and offset determine freshness. High-resolution custom metrics exist; a fixed “CloudWatch always has 1–3 minutes delay” is inaccurate. Prometheus also has collection and control-loop delays.

### Identity and Published Metric Contract

These examples use a KEDA operator role configured through IRSA and this workload-namespace TriggerAuthentication:

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
```

`podIdentity.provider: aws` is the current IRSA provider. Its `identityOwner: keda` differs from the deprecated scaler metadata `identityOwner: operator/pod`, which remains supported in 2.20 but is scheduled for removal in 3. Do not confuse the old `aws-eks` provider name with a new EKS Pod Identity association. Use the documented provider/SDK credential setup for the chosen identity mechanism.

The publishing example later in this guide emits:

| Metric | Namespace and exact dimensions | Interpretation |
|---|---|---|
| `IstioRequestsPerSecond` | `IstioScaling`; ClusterName=`eks-demo`, destination_workload=`reviews`, destination_workload_namespace=`default` | Precomputed RPS gauge |
| `IstioP95LatencyMilliseconds` | Same dimension set | Precomputed per-window p95 gauge in milliseconds |

All dimensions must match. A query containing only destination_workload does not identify the same custom metric.

### RPS Gauge

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Average over the gauge's60-second period retains RPS units. Summing cumulative `istio_requests_total` samples is not a request count per minute. For a genuinely published delta-count metric, derive a separately calibrated per-period target instead.

`minMetricValue` is explicitly present for the released scaler parser, but `ignoreNullValues: "false"` takes precedence on empty results. `metricEndTimeOffset` skips recent potentially incomplete points; it adds delay and does not prove data freshness. Monitor timestamps and publisher health, including stale-but-nonempty results.

### Precomputed Latency Gauge

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-p95-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-p95
    metricType: Value
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioP95LatencyMilliseconds
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '200'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Maximum
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

This asks for the largest published p95 gauge in the period. It is **not** the p95 of all requests in that CloudWatch period. Do not request `metricStat: p95` on a Prometheus histogram conversion or a p95-of-p95 gauge and claim the original distribution is preserved. Native CloudWatch percentile use requires appropriately published samples/statistics.

### Multiple Sources Are Not Ordered Failover

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-dual-source-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: prom-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Both metrics participate in the HPA's maximum recommendation. “Prometheus primary, CloudWatch secondary” is not a priority/failover policy, and stale values can retain an elevated replica recommendation. Prefer a deliberate single source or a tested multi-source/fallback design.

## Practical Scaling Strategies

### 1. Scheduled Replica Floor

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-scheduled-floor
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

During the weekday Asia/Seoul window, the Cron trigger supplies a 20-replica floor while demand can request more, up to the configured maximum. This is scheduled scaling, not a traffic-prediction model. Schedule ahead of demand when startup/readiness takes time.

### 2. Explicit Off-hours Scale to Zero

For a workload that may be unavailable outside office hours, use a positive desired count inside the window and `minReplicaCount: 0`:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: analytics-office-hours
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-service
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
```

Cron `desiredReplicas: "0"` is invalid. Outside the active window, KEDA can return to 0 under its inactivity/cooldown rules. A client request does not wake this Cron-only workload. Destination-side Istio metrics disappear with the application, so they cannot by themselves provide a reliable 0→1 demand signal. Use an independently observable queue/interceptor or keep a positive minimum when on-demand availability is required.

PromQL `hour()` uses UTC; it does not inherit a Cron scaler's Asia/Seoul timezone. Avoid mixing them as if their business-hour windows were identical.

### 3. Circuit-breaker Signals Are Diagnostics First

Client-side overflow and current connections can be inspected separately:

```promql
sum(increase(envoy_cluster_upstream_rq_pending_overflow{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
}[1m]))

sum(envoy_cluster_upstream_cx_active{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})

max(envoy_cluster_circuit_breakers_default_cx_open{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})
```

Verify the real cluster name/port, exported stats and source scrape scope. `cx_open` is a 0/1 circuit-breaker flag, not connection capacity; dividing active connections by it cannot produce saturation percentage. Increasing backend replicas does not raise a client's fixed connection-pool limits. Diagnose the limit/dependency before assigning a scaling target.

### 4. Scaling Policies Are Not Load Tiers

HPA policy lists with Percent/Pods and `selectPolicy: Max` or `Min` limit allowed changes over rolling periods. They do not automatically select “low”, “medium” and “high” load tiers from comments. Use the main behavior example to bound changes and validate it against the measured workload response.

### 5. Gateway-observed Backend Demand

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: backend-gateway-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: gateway-backend-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="source",source_workload="istio-ingressgateway",source_workload_namespace="istio-system",destination_service_name="backend",destination_service_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Verify the real gateway workload name and destination Service labels. This measures traffic for the specific backend from that gateway. `envoy_http_downstream_rq_active` is active HTTP requests, not pending connections, and a gateway-wide aggregate includes unrelated services. Do not use that aggregate to scale an arbitrary backend.

This example keeps a positive minimum. If considering 0 replicas, first prove the independent gateway/interceptor still emits the necessary metric with no backend endpoints and provides the desired request-buffering/error behavior.

## Best Practices

### 1. One Target, One Autoscaler Owner

Do not install several example ScaledObjects or an extra “backup HPA” on the same target. Coordinate existing HPA ownership and GitOps replicas fields before a change. Multiple metrics can live in one ScaledObject; native HPA can skip downscaling when a metric errors while still allowing a valid scale-up recommendation.

KEDA 2.20 fallback supports AverageValue and Value triggers except CPU/memory; it applies to ScaledObjects, not ScaledJobs. A CPU/memory trigger needs its own metrics-server/request prerequisites and is not an independent failover controller.

### 2. Capacity Planning Example, Not a Benchmark

The following preserves the original numbers as **hypothetical inputs**:

| Assumption/calculation | Result |
|---|---|
| Assumed measured per-Pod capacity 200 RPS × chosen utilization factor 70% | 140 RPS/Pod target |
| Normal load 500 /140, rounded up | 4 replicas |
| Peak load 2000 /140, rounded up | 15 replicas |
| Chosen maximum with extra room | 20, subject to actual schedulable capacity |

These were not measured by this audit. Run a bounded, approved load test against a known replica/target and record latency, errors, resources and readiness. A Service load-balancing over several replicas does not directly measure one Pod's capacity.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-capacity-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 4
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '140'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 4
    behavior: currentReplicasIfHigher
```

There is no universal “maxReplicaCount ≤70% of cluster capacity” rule: Pod count is not a CPU/memory/IP/quota percentage. HPA/KEDA scale workloads; node capacity requires separate provisioning/autoscaler configuration.

### 3. Resources and Health

Merge this fragment into the **existing** Deployment/container after confirming its container name and actual health endpoint. Retain its real image, selectors and labels:

```yaml
spec:
  template:
    spec:
      containers:
      - name: reviews
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /health
            port: 9080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
```

Requests/limits and probes are tuning inputs, not a measured throughput guarantee. Readiness and startup/draining affect when capacity is usable. Liveness should not restart an otherwise healthy process merely because a downstream dependency is unavailable.

### 4. Multiple Clusters and Regions

Use a scaler in each target cluster with a verified cluster-local datasource, or explicit cluster labels that truly exist in a federated store. With cluster-local destination-reporter data, this example counts all local backend demand:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-local-demand
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 3
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: local-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Apply each configuration in its intended cluster context. Metadata labels such as `region` do not make a ScaledObject control a remote cluster. `source_cluster` describes origin, not the destination capacity to scale; multiplying already-filtered traffic by 0.6/0.4 does not implement a global traffic split.

Service naming patterns such as `*-us-*` do not establish client geography, and `destination_region` is not a guaranteed default Istio label. Regional SLOs need verified telemetry and workload capacity, not assumed country names in service labels.

### 5. Payment and Queue Workloads

A payment workload can begin with calibrated demand and conservative bounds while latency/errors remain quality indicators:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: payment-capacity-example
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 5
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="payment-service",destination_workload_namespace="production"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 5
    behavior: currentReplicasIfHigher
```

The 100 RPS target and limits are illustrative. Confirm bottleneck causality, idempotency, downstream limits and representative failure behavior before adding ratio-based triggers.

For a queue worker, the queue remains visible when worker replicas are 0:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: data-processor-queue
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-sqs-queue
    name: backlog
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/data-processing-queue
      queueLength: '10'
      activationQueueLength: '0'
      scaleOnInFlight: 'true'
      scaleOnDelayed: 'false'
      awsRegion: us-west-2
```

Replace the example account/queue URL and configure the referenced identity. `queueLength: "10"` means target backlog per replica, not an activation threshold of ten. Activation defaults to positive backlog with the explicitly zero activation threshold. The example counts visible plus in-flight messages and excludes delayed messages; align this with processing concurrency, visibility timeout and shutdown behavior.

Istio HTTP latency is not automatically SQS job-processing duration. Instrument business processing separately instead of adding an unavailable Pod-latency trigger to the 0-replica worker.

### 6. Monitoring

Expose and scrape **operator** metrics for scaler health. The metrics adapter's metrics alone do not contain every operator counter. KEDA's `namespace` metric label identifies the scaled resource namespace; do not overwrite it with the exporter Pod namespace.

This is a scrape-config fragment to merge into the existing Prometheus configuration, with namespace-scoped discovery RBAC for EndpointSlices, Services and Pods:

```yaml
scrape_configs:
- job_name: keda-components
  kubernetes_sd_configs:
  - role: endpointslice
    namespaces:
      names:
      - keda
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_service_name
    regex: keda-operator|keda-operator-metrics-apiserver
    action: keep
  - source_labels:
    - __meta_kubernetes_endpointslice_port_name
    regex: metrics
    action: keep
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: exporter_namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: exporter_pod
```

It discovers each endpoint rather than alternating between HA operator Pods through one load-balanced Service. Confirm actual Service/port names, target labels, TLS/mesh access and scrape results. With Prometheus Operator, use equivalent selected ServiceMonitors rather than overwriting its generated ConfigMap.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: keda-scaling-alerts
  namespace: keda
spec:
  groups:
  - name: keda-scaling
    rules:
    - alert: KEDAMaxReplicasReached
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        ) >= on(namespace, horizontalpodautoscaler)
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_spec_max_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        )
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: KEDA-managed HPA is at its configured maximum
    - alert: KEDAScalerErrors
      expr: sum by (namespace, scaledObject) (increase(keda_scaler_detail_errors_total[5m])) > 0
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Scaler retrieval errors observed; inspect source/identity and fallback
    - alert: KEDAReplicaCountChurn
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         changes(kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}[10m])
        ) > 6
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Frequent observed replica-count changes; inspect demand, rollout and stabilization
```

PrometheusRule requires a matching Operator rule selector/namespace. The HPA filters use KEDA's default name prefix; adjust for custom HPA names. `keda_scaler_detail_errors_total` is the released error counter; `keda_scaler_active` is a gauge and must not be passed to `rate()` as a replica-flapping measure.

Replica-count changes can reflect demand or rollouts, not necessarily harmful oscillation. These alerts are investigation signals, not proof of failed scaling or sufficient ready capacity.

## Troubleshooting

```bash
kubectl get scaledobject reviews-rps-scaler -n default -o yaml
kubectl describe hpa keda-hpa-reviews-rps-scaler -n default
kubectl logs -n keda deployment/keda-operator
kubectl get apiservice v1beta1.external.metrics.k8s.io
kubectl get pods -n default -o wide

# Local query inspection; use a second terminal while port-forward is active.
kubectl port-forward -n istio-system svc/prometheus 9090:9090
```

```bash
promtool query instant http://127.0.0.1:9090 'sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))'
```

A local port-forward proves neither KEDA Pod connectivity nor its credentials. Check provider errors, DNS, TLS/mesh policy, metric existence/labels and aggregated-API availability from the actual component path.

For slow scaling, inspect source age, lookback, HPA sync/behavior, scheduling, image pulls and readiness before reducing pollingInterval. Activation thresholds do not accelerate ordinary 1→N scaling when a positive minimum is used. For unstable counts, examine the measured capacity response and HPA stabilization/rate limits; cooldownPeriod is not its general downscale control.

For CloudWatch, inspect returned timestamps, all dimensions, statistic/unit, collection window, offset and IAM. A higher threshold on a second metric does not make it a passive backup.

## Reference: KEDA Installation

### Pinned Chart and Actual Compatibility

The published KEDA 2.20 deployment requirement is Kubernetes 1.30+, while the chart metadata has a looser 1.23 floor. Helm accepting a version is not proof of runtime support. Use the intersection with Istio 1.31's 1.32–1.36 support and the managed platform's supported versions.

For a new installation, or a reviewed upgrade preserving existing values, use these values. Before upgrading, also review the release changes and CRD ownership/migration procedure:

```yaml
operator:
  replicaCount: 2
prometheus:
  operator:
    enabled: true
  metricServer:
    enabled: true
    port: 9022
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm upgrade --install keda kedacore/keda --version 2.20.2   --namespace keda --create-namespace --values keda-values.yaml
kubectl get deployments,services,pods -n keda
```

`operator.replicaCount: 2` and the metrics-adapter port 9022 override are valid chart values;9022 is an explicit override of the chart's8080 default. This enables operator metrics on 8080 as well. Two operator replicas alone do not make the metrics adapter/webhook or entire scaling path highly available.

If the components are injected into Istio, KEDA documents this optional port-exclusion workaround for its own TLS-protected internal protocols:

```yaml
podAnnotations:
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: '9666'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9443,6443
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: '6443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,9443
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: '9443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,6443
```

Verify actual ports and injection settings before merging. KEDA keeps its native TLS; Istio authorization does not cover the excluded traffic. This is not permission to disable transport security globally. Test API-server aggregation, admission, operator↔adapter and Prometheus connectivity.

### AWS Reader Identity

Create/review the IAM role and its EKS OIDC trust outside this example, scoped to the actual operator ServiceAccount. Apply the corresponding Helm values without blindly overwriting an existing ServiceAccount:

```yaml
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaMetricsReader
```

For the shown CloudWatch scaler, the released implementation calls GetMetricData:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-west-2"
        }
      }
    }
  ]
}
```

This is regional metric-read permission, not a per-metric namespace boundary. `cloudwatch:namespace` in the AWS example policy constrains **PutMetricData publishing**, not this query. The separate CloudWatch PromQL API has different IAM requirements; do not infer them from this scaler.

If using the SQS example, the operator additionally needs the specific queue's attribute-read permission:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-west-2:123456789012:data-processing-queue"
    }
  ]
}
```

The queue worker needs its own receive/delete/visibility permissions as appropriate; the scaler's read role does not grant those. Limit who may create/change ScaledObjects and TriggerAuthentications using operator identities.

### Optional CloudWatch EMF Publication

This example uses **upstream Collector Contrib 0.158.0 with Operator 0.158.0**, matching the operator's minor-version recommendation. Operator 0.158 supports Kubernetes 1.25–1.36. A custom image is not automatically upgraded by the operator. An ADOT distribution is an alternative only after verifying its components/configuration; the commands below are not claimed tested against an unspecified ADOT image.

First load this recording-rule file into the existing Prometheus (or equivalent PrometheusRule with the appropriate selection labels):

```yaml
groups:
- name: istio-scaling-export
  interval: 30s
  rules:
  - record: istio_scaling_requests_per_second
    expr: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
  - record: istio_scaling_p95_milliseconds
    expr: |-
      (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
        and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
      or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
```

Only the shown workload is exported. These are already-calculated RPS and rolling-window p95 gauges; they are not raw cumulative request counters or a reconstructable request-latency distribution.

Then, with the compatible Operator/CRDs and an existing reviewed publisher role/log group:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-metrics-publisher
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/IstioMetricsPublisher
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: istio-scaling
  namespace: istio-system
spec:
  mode: deployment
  replicas: 1
  serviceAccount: istio-metrics-publisher
  image: otel/opentelemetry-collector-contrib:0.158.0
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
  config:
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      prometheus:
        config:
          scrape_configs:
          - job_name: istio-scaling-federate
            scrape_interval: 60s
            honor_labels: true
            metrics_path: /federate
            params:
              match[]:
              - '{__name__=~"istio_scaling_requests_per_second|istio_scaling_p95_milliseconds"}'
            static_configs:
            - targets:
              - prometheus.istio-system.svc.cluster.local:9090
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
        spike_limit_mib: 64
      metricstransform:
        transforms:
        - include: istio_scaling_requests_per_second
          action: update
          new_name: IstioRequestsPerSecond
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
        - include: istio_scaling_p95_milliseconds
          action: update
          new_name: IstioP95LatencyMilliseconds
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
      batch:
        timeout: 60s
        send_batch_size: 256
    exporters:
      awsemf:
        namespace: IstioScaling
        region: us-west-2
        log_group_name: /aws/otel/istio-scaling
        log_stream_name: eks-demo
        dimension_rollup_option: NoDimensionRollup
        metric_declarations:
        - dimensions:
          - - ClusterName
            - destination_workload
            - destination_workload_namespace
          metric_name_selectors:
          - ^IstioRequestsPerSecond$
          - ^IstioP95LatencyMilliseconds$
        metric_descriptors:
        - metric_name: IstioRequestsPerSecond
          unit: Count/Second
          overwrite: true
        - metric_name: IstioP95LatencyMilliseconds
          unit: Milliseconds
          overwrite: true
    service:
      extensions:
      - health_check
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - metricstransform
          - batch
          exporters:
          - awsemf
```

The `v1beta1` config is an object. The older `v1alpha1` API remains served by this operator release, so it should not be described as removed; this example uses the current form and an explicit Contrib image with the required components.

The Collector federates only the two named recording metrics, preserves workload dimensions, adds the configured ClusterName, and writes EMF to a fixed log stream. Keep the namespace, metric names, units and all three dimensions aligned with the CloudWatch scalers. NaN/Inf are dropped by the EMF exporter; the recording expression distinguishes known idle 0 from unavailable telemetry.

One publisher replica avoids duplicate polling in this example; this is not an HA design. Configure real Prometheus authentication/mesh access, publisher identity, log retention and resource limits. The operator/controller and EMF delivery were not deployed or tested against AWS by this audit.

The publisher log group must already exist with platform-managed retention. Its example role needs stream creation/write within that group:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/otel/istio-scaling:log-stream:eks-demo"
    }
  ]
}
```

EMF goes through CloudWatch Logs; `cloudwatch:PutMetricData` alone does not authorize this exporter. The configured metric namespace is not enforced by a PutMetricData namespace condition on these Logs calls. Log ingestion/storage and generated custom metrics have separate costs; control cardinality and retention rather than assuming replica reduction equals bill savings.

## References

- [KEDA ScaledObject specification](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [Activation and scaling](https://keda.sh/docs/2.20/concepts/scaling-deployments/)
- [Prometheus scaler](https://keda.sh/docs/2.20/scalers/prometheus/)
- [CloudWatch scaler](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [SQS scaler](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Cron scaler](https://keda.sh/docs/2.20/scalers/cron/)
- [AWS IRSA provider](https://keda.sh/docs/2.20/authentication-providers/aws/)
- [KEDA metrics](https://keda.sh/docs/2.20/integrations/prometheus/)
- [KEDA with Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)
- [KEDA deployment requirements](https://keda.sh/docs/2.20/deploy/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Istio standard metrics](https://istio.io/latest/docs/reference/config/metrics/)
- [Operator0.158 compatibility](https://raw.githubusercontent.com/open-telemetry/opentelemetry-operator/v0.158.0/docs/getting-started/compatibility.md)
- [Collector0.158 EMF exporter](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.158.0/exporter/awsemfexporter/README.md)
- [CloudWatch EMF](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [CloudWatch namespace conditions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [Observability](../observability/README.md)
- [Resilience](../resilience/README.md)
- [Traffic Management](../traffic-management/README.md)

Before production use, validate signal semantics, actual metric labels/freshness, idle/missing-data behavior, one-owner scaling, capacity, representative failure response and recovery. The example thresholds, replica floors and timing values are starting inputs to those tests.
