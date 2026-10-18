# 基于 Istio 指标的 KEDA 自动扩缩容

> **验证基线**：KEDA/chart 2.20.2、Istio 1.31.0、Kubernetes 1.32–1.37
> **最后审阅日期**：October 16, 2026

本指南介绍扩缩容信号及其局限。它假设工作负载已存在、指标已验证且集群容量充足。针对同一 Deployment 的示例是**互斥方案**：为每个目标选择一个 ScaledObject/HPA 所有者，而不是使用本页中的所有对象。

## 目录

1. [概述](#overview)
2. [架构](#architecture)
3. [基于 Prometheus 指标的扩缩容](#prometheus-metrics-based-scaling)
4. [基于 CloudWatch 指标的扩缩容](#cloudwatch-metrics-based-scaling)
5. [实用扩缩容策略](#practical-scaling-strategies)
6. [最佳实践](#best-practices)
7. [故障排除](#troubleshooting)
8. [参考：安装 KEDA](#reference-keda-installation)

## 概述

Kubernetes HPA 可通过相应的 API 支持资源、自定义和外部指标，包括多个指标。CloudWatch 可以通过适配器集成；并非 HPA 本身无法使用 CloudWatch。KEDA 提供 scaler、外部指标 API 和激活管理，同时仍使用 HPA 进行常规副本扩缩容。

| 信号 | 含义 | 用途和局限 |
|---|---|---|
| `istio_requests_total` | HTTP/gRPC 请求计数器 | 速率可用于衡量已接纳的负载；选择一个 reporter 和实际目标工作负载 |
| `istio_request_duration_milliseconds_bucket` | 经典延迟直方图桶 | 分位数是质量观测值，并不保证是容量的反向信号 |
| `istio_tcp_connections_opened_total` | 累积打开连接数 | 其速率表示连接创建速率，而非当前活动连接数 |
| `istio_request_bytes_sum` | 累积观测到的 HTTP 请求字节数 | 速率表示吞吐量；应限定 reporter 和工作负载范围 |
| `envoy_cluster_upstream_rq_pending_overflow` | 客户端侧集群溢出计数器 | 在决定是否以及对哪个工作负载进行扩缩容之前，先诊断连接池限制和依赖项 |

经过校准的需求/积压指标是一个起点。延迟、错误和断路器事件可能由下游故障造成，而增加副本无法解决这些问题。有状态成员关系、存储和应用语义也会限制扩缩容；仅凭“有状态”或“对延迟敏感”并不能确定安全的自动扩缩容策略。

## 架构

KEDA 会为扩缩容目标创建/配置 HPA，并公开外部指标。HPA 控制器通过该 API 请求指标，并更新目标的 `/scale` 子资源；随后目标控制器和调度器会创建/放置 Pod。

| 设置或组件 | 职责 |
|---|---|
| KEDA `pollingInterval` | 触发器轮询和激活，包括 0→1 |
| HPA 控制器同步 | 额外的指标请求和 1→N 决策；默认同步周期为 15 秒，可由集群配置 |
| `useCachedMetrics` | 可选的 KEDA 指标缓存，在轮询间隔期间使用；这些示例未启用 |
| `activationThreshold` | 用于 0↔1 的激活阈值，不是第二个 HPA 缩容阈值 |
| `cooldownPeriod` | 在无活动后等待一段时间，再由 KEDA 缩容到 0；并非每次缩容后暂停 |
| HPA `behavior` | 1→N 稳定窗口和变化速率限制 |

当 `minReplicaCount` 大于 0 时，不要将 activation/cooldown 用作常规副本迟滞机制。采集→抓取→查询→HPA→Pod 启动/就绪都会造成延迟；15 秒轮询或零稳定窗口都不能保证立即具备可用容量。

### 指标类型与理想计算方式

忽略 HPA 容差、缺失/未就绪的 Pod、限制和行为策略时：

- **AverageValue + 总需求量**：期望副本数 ≈ `ceil(总指标值 / 每个 Pod 的目标值)`。
- **Value + 工作负载范围的值**：期望副本数 ≈ `ceil(当前副本数 × 观测值 / 目标值)`。

对于每 Pod 100 RPS、总计 600 RPS 的情况，AverageValue 会要求 6 个副本。若先将查询结果除以 3 个 Pod，就会得到 200，并错误地只要求 2 个副本。`count(up)` 统计的是抓取目标数，也不是安全的副本除数。

如果有 4 个副本，全局延迟为 300ms，Value 目标为 200ms，则会建议扩至 6 个副本。如果增加副本并未降低该延迟，反复决策可能会让工作负载一直扩到上限。应将延迟/错误率控制器视为需要负反馈证据的实验，而非生产环境默认设置。

## 基于 Prometheus 指标的扩缩容

这些示例假设 `default` 中有一个实际名为 `reviews` 的 Deployment。Service 名称不是扩缩容目标。已发布的 Bookinfo 通常使用 `reviews-v1` 等 Deployment 名称；应根据实际工作负载调整 `scaleTargetRef` 和指标选择器，而不要假设它们与 Service 名称一致。

验证每个相关代理的抓取数据，并确认实际标签。主要示例使用 `reporter="destination"`，以避免重复统计请求报告。这衡量的是目标端接纳的请求；边缘拒绝/排队情况可能需要独立测量的需求信号。

### 1. 基于 RPS 的扩缩容

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

查询会将失败请求也计入负载，并返回总 RPS。对于 AverageValue，`threshold: "100"` 是每个副本的目标值，并非“超过 100 就增加一个 Pod”的全局开关。不要再次除以 Pod 数量。

在 KEDA 2.20.2 中，`ignoreNullValues: "false"` 会使缺失、NaN 或无限大的 Prometheus 结果在 KEDA 中成为错误。真实的零计数器速率仍然是 0。应为数据源故障配置并测试 fallback；不要将任意缺失指标静默转换为 0。启用 scaler 前，先建立抓取/指标数据契约。

这里的 fallback 会在达到配置的错误阈值后，采用配置的下限和当前副本数中的较大值，但仍受 HPA 限制/行为约束。它无法防护 KEDA 指标 API 不可用或节点容量不足。

### 2. 基于延迟的控制：有条件的实验

此备选方案明确对工作负载范围的 p95 使用 Value：

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

只有在实际直方图计数的速率为零时，查询才会返回 0。遥测数据缺失时结果仍然缺失；无效的分位数仍会产生错误，而不会变成健康的 0。空闲时间窗口中的 p95 为 0 是有意设置的控制值，并不表示观测到了持续时间为零的请求。

多个分位数也都是 Value 指标：

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

HPA 会选择期望副本数最大的指标，而不是取平均值或加权组合。分位数彼此相关；增加触发器并不能天然提高稳定性，也无法形成延迟保证。

### 3. 基于错误率的控制：有条件的实验

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

这是一个工作负载范围的 5xx/零状态百分比，目标类型为 Value。已知空闲流量会返回 0；没有遥测数据时不会伪造出 0。只有在确认副本不足会导致这些错误之后，才使用基于错误率的控制器。依赖项中断、授权失败或客户端连接池限制都可能使扩缩容无效，甚至带来危害。

### 4. 组合指标

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

RPS 输入是使用 AverageValue 的总需求量；延迟输入是 Value。HPA 采用最大建议值。扩容 `selectPolicy: Max` 会选择允许的较大变化量：如果百分比策略允许增加更多副本，五个 Pod 的策略就不是绝对上限。这些备选方案仍需进行容量和工作负载测试。

## 基于 CloudWatch 指标的扩缩容

CloudWatch 数据源的采集节奏、发布延迟、聚合周期、回看时间和偏移量共同决定数据的新鲜度。高分辨率自定义指标确实存在；“CloudWatch 总是延迟 1–3 分钟”这种说法并不准确。Prometheus 也有采集和控制循环延迟。

### 身份与已发布指标契约

这些示例使用通过 IRSA 配置的 KEDA operator 角色，以及以下位于工作负载命名空间的 TriggerAuthentication：

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

`podIdentity.provider: aws` 是当前的 IRSA provider。其 `identityOwner: keda` 与已弃用的 scaler 元数据 `identityOwner: operator/pod` 不同；后者在 2.20 中仍受支持，但计划在 3 中移除。不要将旧的 `aws-eks` provider 名称与新的 EKS Pod Identity 关联混淆。针对所选身份机制，使用文档中说明的 provider/SDK 凭证配置。

本指南后面的发布示例会输出以下指标：

| 指标 | 命名空间和确切维度 | 说明 |
|---|---|---|
| `IstioRequestsPerSecond` | `IstioScaling`；ClusterName=`eks-demo`、destination_workload=`reviews`、destination_workload_namespace=`default` | 预先计算的 RPS gauge |
| `IstioP95LatencyMilliseconds` | 相同的维度集合 | 以毫秒为单位、按窗口预先计算的 p95 gauge |

所有维度都必须匹配。仅包含 destination_workload 的查询无法标识同一个自定义指标。

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

对该 gauge 的 60 秒周期求平均值会保留 RPS 单位。累加 `istio_requests_total` 的累计样本并不等同于每分钟的请求数。如果发布的是真正的增量计数指标，则应单独推导并校准每周期目标值。

已明确设置 `minMetricValue`，以适配已发布 scaler 的解析器，但当结果为空时，`ignoreNullValues: "false"` 优先生效。`metricEndTimeOffset` 会跳过最近可能尚未完整的数据点；它会增加延迟，但不能证明数据是新鲜的。应监控时间戳和发布器运行状况，包括非空但已过期的结果。

### 预先计算的延迟 Gauge

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

此配置会采用该周期内已发布 p95 gauge 的最大值。它**不是**该 CloudWatch 周期内所有请求的 p95。不要对 Prometheus 直方图转换结果或 p95-of-p95 gauge 设置 `metricStat: p95`，并声称原始分布得到了保留。只有在以适当方式发布样本/统计数据时，才能使用 CloudWatch 原生百分位数。

### 多个数据源并非按顺序故障转移

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

两个指标都会参与 HPA 的最大建议值计算。“Prometheus 主用，CloudWatch 备用”不是优先级/故障转移策略，过期值仍可能维持较高的副本建议。应优先选择明确的单一数据源，或经过测试的多源/fallback 设计。

## 实用扩缩容策略

### 1. 定时设置副本下限

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

在首尔时间的工作日时段内，Cron 触发器会提供 20 个副本的下限；需求仍可要求更多副本，但不超过配置的最大值。这是定时扩缩容，不是流量预测模型。如果启动/就绪需要时间，应提前安排扩容。

### 2. 明确在非工作时段缩容到零

对于允许在办公时间以外不可用的工作负载，可在时间窗口内设置大于零的期望副本数，并将 `minReplicaCount` 设为 0：

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

Cron 的 `desiredReplicas: "0"` 无效。在激活窗口之外，KEDA 可根据其无活动/cooldown 规则回到 0。客户端请求不会唤醒这个仅由 Cron 触发的工作负载。应用停止后，目标端 Istio 指标也会消失，因此它们本身无法提供可靠的 0→1 需求信号。使用可独立观测的队列/拦截器，或在需要按需可用时保持正数的最小副本数。

PromQL `hour()` 使用 UTC；它不会继承 Cron scaler 的 Asia/Seoul 时区。不要混用它们并假设其业务时段完全一致。

### 3. 首先将断路器信号用于诊断

可以分别检查客户端侧溢出和当前连接：

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

核实实际集群名称/端口、导出的统计数据和源抓取范围。`cx_open` 是 0/1 断路器标志，不是连接容量；用活动连接数除以它无法得到饱和百分比。增加 backend 副本不会提高客户端固定的连接池限制。指定扩缩容目标前，应先诊断限制/依赖项。

### 4. 扩缩容策略不是负载等级

带有 Percent/Pods 和 `selectPolicy: Max` 或 `Min` 的 HPA 策略列表，会限制滚动周期内允许的变化量。它们不会根据注释自动选择“低”“中”“高”负载等级。使用主要行为示例限制变化，并根据测得的工作负载响应进行验证。

### 5. 网关观测到的后端需求

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

核实实际网关工作负载名称和目标 Service 标签。此配置衡量来自该网关、发往特定后端的流量。`envoy_http_downstream_rq_active` 表示活动 HTTP 请求，而非待处理连接；网关范围的聚合数据还包括无关 Service。不要用这个聚合指标来扩缩容任意后端。

此示例保持正数的最小副本数。如果考虑缩容到 0，应先证明在没有后端端点时，独立的网关/拦截器仍会输出所需指标，并能提供期望的请求缓冲/错误处理行为。

## 最佳实践

### 1. 一个目标，一个自动扩缩容所有者

不要在同一目标上安装多个示例 ScaledObject，也不要再额外配置一个“备用 HPA”。变更前应协调现有 HPA 所有权和 GitOps 中的副本数字段。多个指标可以放在一个 ScaledObject 中；如果某个指标出错，原生 HPA 可以跳过缩容，同时仍允许依据有效指标扩容。

KEDA 2.20 的 fallback 支持 AverageValue 和 Value 触发器，但不包括 CPU/内存；它适用于 ScaledObject，不适用于 ScaledJobs。CPU/内存触发器需要各自的 metrics-server/请求前提条件，并不是独立的故障转移控制器。

### 2. 容量规划示例，不是基准测试

以下内容将原始数字保留为**假设输入**：

| 假设/计算 | 结果 |
|---|---|
| 假设测得的每 Pod 容量为 200 RPS × 所选利用率系数 70% | 目标值为 140 RPS/Pod |
| 正常负载 500 /140，向上取整 | 4 个副本 |
| 峰值负载 2000 /140，向上取整 | 15 个副本 |
| 所选最大值并留有额外空间 | 20，受实际可调度容量限制 |

这些数据并非本次审查测得。应针对已知副本数/目标进行范围受限且经过批准的负载测试，并记录延迟、错误、资源和就绪情况。由多个副本提供负载均衡的 Service 无法直接测出单个 Pod 的容量。

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

不存在通用的“maxReplicaCount ≤ 集群容量的 70%”规则：Pod 数量不是 CPU/内存/IP/配额的百分比。HPA/KEDA 负责扩缩工作负载；节点容量需要单独配置节点供应/自动扩缩容。

### 3. 资源与健康状况

确认容器名称和实际健康检查端点后，将此片段合并到**现有** Deployment/容器中。保留实际镜像、选择器和标签：

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

requests/limits 和探针是调优输入，不是吞吐量保证。就绪状态、启动和排空都会影响容量何时可用。仅仅因为下游依赖不可用，不应通过 liveness 重启原本健康的进程。

### 4. 多集群和多区域

在每个目标集群中使用一个 scaler，并配置经过验证的集群本地数据源；或者使用联邦存储中确实存在的显式集群标签。对于集群本地的 destination-reporter 数据，以下示例会统计所有本地 backend 需求：

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

在预期的集群上下文中应用每个配置。诸如 `region` 的元数据标签不会让 ScaledObject 控制远程集群。`source_cluster` 描述来源，而不是要扩展的目标容量；对已筛选的流量乘以 0.6/0.4 并不能实现全局流量拆分。

类似 `*-us-*` 的 Service 命名模式无法确定客户端的地理位置，`destination_region` 也不是 Istio 保证提供的默认标签。区域性 SLO 需要经过验证的遥测数据和工作负载容量，而非 Service 标签中臆测的国家/地区名称。

### 5. 支付和队列工作负载

支付工作负载可以从经过校准的需求和保守的边界开始，同时将延迟/错误视为质量指标：

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

100 RPS 目标值和限制仅为示例。在添加基于比例的触发器之前，应先确认瓶颈因果关系、幂等性、下游限制和具有代表性的故障行为。

对于队列 worker，即使副本数为 0，队列仍然可见：

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

替换示例账户/队列 URL，并配置所引用的身份。`queueLength: "10"` 表示每个副本的目标积压量，而非值为十的激活阈值。激活阈值明确设为零时，默认会在积压量大于零时激活。此示例统计可见和正在处理的消息，并排除延迟消息；应使其与处理并发数、可见性超时和关闭行为保持一致。

Istio HTTP 延迟不会自动等同于 SQS 作业处理时长。应单独监测业务处理情况，而不要给副本数为 0 的 worker 添加无法获取的 Pod 延迟触发器。

### 6. 监控

公开并抓取 **operator** 指标，以监控 scaler 健康状况。指标适配器的指标本身并不包含所有 operator 计数器。KEDA 的 `namespace` 指标标签标识扩缩容资源的命名空间；不要将其替换成 exporter Pod 的命名空间。

以下是要合并到现有 Prometheus 配置中的抓取配置片段，并需要针对 EndpointSlice、Service 和 Pod 配置命名空间范围内的发现 RBAC：

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

此配置会发现每个端点，而不是通过一个负载均衡 Service 在 HA operator Pod 之间交替抓取。确认实际的 Service/端口名称、目标标签、TLS/网格访问和抓取结果。如果使用 Prometheus Operator，应使用等效的、经过选择的 ServiceMonitor，而不要覆盖它生成的 ConfigMap。

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

PrometheusRule 需要匹配的 Operator 规则选择器/命名空间。HPA 筛选器使用 KEDA 的默认名称前缀；如有自定义 HPA 名称，请相应调整。`keda_scaler_detail_errors_total` 是已发布的错误计数器；`keda_scaler_active` 是 gauge，不应将其传给 `rate()` 作为副本抖动指标。

副本数变化可能来自需求或滚动更新，不一定意味着有害振荡。这些告警用于提示调查，不能证明扩缩容失败或就绪容量充足。

## 故障排除

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

本地端口转发既不能证明 KEDA Pod 可以连接，也不能证明其凭证有效。应从实际组件路径检查 provider 错误、DNS、TLS/网格策略、指标是否存在及其标签，以及聚合 API 的可用性。

如果扩缩容较慢，应先检查数据源时间、回看时间、HPA 同步/行为、调度、镜像拉取和就绪情况，然后再缩短 pollingInterval。使用正数最小副本时，激活阈值不会加快常规 1→N 扩缩容。如果副本数不稳定，应检查测得的容量响应和 HPA 稳定窗口/速率限制；cooldownPeriod 并不是通用的缩容控制机制。

对于 CloudWatch，应检查返回的时间戳、所有维度、统计数据/单位、采集窗口、偏移量和 IAM。第二个指标设置更高的阈值，并不会使其成为被动备用指标。

## 参考：安装 KEDA

### 固定 Chart 版本与实际兼容性

已发布的 KEDA 2.20 部署要求为 Kubernetes 1.30+，而 chart 元数据允许的最低版本更低，为 1.23。Helm 接受某个版本，并不代表它在运行时受支持。应使用与 Istio 1.31 支持的 1.32–1.37 版本以及托管平台支持版本的交集。

对于新安装，或在保留现有值的前提下经过审查的升级，请使用以下值。升级前还应审查发行版变更以及 CRD 所有权/迁移流程：

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

`operator.replicaCount: 2` 和 metrics-adapter 端口 9022 覆盖值都是有效的 chart 值；9022 是对 chart 默认端口 8080 的显式覆盖。这也会在 8080 上启用 operator 指标。仅有两个 operator 副本并不能让 metrics adapter/webhook 或整个扩缩容路径实现高可用。

如果这些组件注入了 Istio sidecar，KEDA 为其自身受 TLS 保护的内部协议记录了以下可选端口排除方案：

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

合并前应核实实际端口和注入设置。KEDA 会保留原生 TLS；Istio 授权不覆盖被排除的流量。这并不意味着可以全局关闭传输安全。应测试 API server 聚合、准入、operator↔adapter 以及 Prometheus 连通性。

### AWS 读取者身份

在此示例之外创建/审查 IAM 角色及其 EKS OIDC 信任关系，并将权限范围限定到实际的 operator ServiceAccount。应用相应的 Helm 值时，不要盲目覆盖现有 ServiceAccount：

```yaml
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaMetricsReader
```

对于此处展示的 CloudWatch scaler，已发布实现会调用 GetMetricData：

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

这是区域级指标读取权限，不是按指标命名空间划定的边界。AWS 示例策略中的 `cloudwatch:namespace` 限制的是 **PutMetricData 发布操作**，而非此处的查询。单独的 CloudWatch PromQL API 有不同的 IAM 要求；不要从此 scaler 推断其要求。

如果使用 SQS 示例，operator 还需要读取特定队列属性的权限：

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

队列 worker 还需要适当的接收/删除/可见性权限；scaler 的读取角色不会授予这些权限。应使用 operator 身份限制可创建/更改 ScaledObject 和 TriggerAuthentication 的人员。

### 可选的 CloudWatch EMF 发布

此示例使用 **上游 Collector Contrib 0.158.0 和 Operator 0.158.0**，符合 operator 对次版本的建议。Operator 0.158 支持 Kubernetes 1.25–1.36。operator 不会自动升级自定义镜像。只有在核实其组件/配置后，才可将 ADOT 发行版作为替代方案；此处的命令并未声称已针对未指定的 ADOT 镜像进行测试。

首先将此 recording-rule 文件加载到现有 Prometheus 中（或使用带有适当选择标签的等效 PrometheusRule）：

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

这里只会导出展示的工作负载。这些指标已经是计算完成的 RPS 和滚动窗口 p95 gauge，并非原始累计请求计数器，也无法据此重建请求延迟分布。

然后，在兼容的 Operator/CRD 和已审查的现有发布器角色/日志组基础上，应用以下配置：

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

`v1beta1` 配置是一个对象。此 operator 版本仍提供旧版 `v1alpha1` API，因此不应称其已移除；此示例使用当前形式，并指定了包含所需组件的 Contrib 镜像。

Collector 仅联邦抓取两个指定的 recording metric，保留工作负载维度，添加配置的 ClusterName，并将 EMF 写入固定日志流。应使命名空间、指标名称、单位和全部三个维度与 CloudWatch scaler 保持一致。EMF exporter 会丢弃 NaN/Inf；recording 表达式会区分已知空闲时的 0 与遥测数据不可用。

此示例使用一个发布器副本，以避免重复轮询；这并非高可用设计。应配置实际的 Prometheus 身份验证/网格访问、发布器身份、日志保留期和资源限制。本次审查未在 AWS 上部署或测试该 operator/controller 和 EMF 交付流程。

发布器日志组必须事先存在，并由平台管理其保留期。示例角色需要在该日志组内创建日志流并写入日志的权限：

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

EMF 通过 CloudWatch Logs 发送；仅授予 `cloudwatch:PutMetricData` 并不能授权此 exporter。此配置中的指标命名空间不会通过这些 Logs 调用上的 PutMetricData 命名空间条件进行强制限制。日志摄取/存储和生成的自定义指标会产生不同费用；应控制基数和保留期，而不要假设减少副本就一定能省钱。

## 参考资料

- [KEDA ScaledObject 规范](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [激活与扩缩容](https://keda.sh/docs/2.20/concepts/scaling-deployments/)
- [Prometheus scaler](https://keda.sh/docs/2.20/scalers/prometheus/)
- [CloudWatch scaler](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [SQS scaler](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Cron scaler](https://keda.sh/docs/2.20/scalers/cron/)
- [AWS IRSA provider](https://keda.sh/docs/2.20/authentication-providers/aws/)
- [KEDA 指标](https://keda.sh/docs/2.20/integrations/prometheus/)
- [KEDA 与 Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)
- [KEDA 部署要求](https://keda.sh/docs/2.20/deploy/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Istio 标准指标](https://istio.io/latest/docs/reference/config/metrics/)
- [Operator0.158 兼容性](https://raw.githubusercontent.com/open-telemetry/opentelemetry-operator/v0.158.0/docs/getting-started/compatibility.md)
- [Collector0.158 EMF exporter](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.158.0/exporter/awsemfexporter/README.md)
- [CloudWatch EMF](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [CloudWatch 命名空间条件](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [可观测性](../observability/README.md)
- [弹性](../resilience/README.md)
- [流量管理](../traffic-management/README.md)

用于生产环境之前，应验证信号语义、实际指标标签/新鲜度、空闲/缺失数据行为、单一扩缩容所有者、容量、有代表性的故障响应和恢复能力。示例中的阈值、副本下限和时间值都是测试的起始输入。
