# 弹性测验

> **最后更新**：2026 年 10 月 12 日
>
> **版本**: Istio 1.31，支持 Kubernetes 1.32–1.37。
> 有关 EKS 兼容性，请参阅安装章节。

本测验用于检验你对 Istio 弹性功能的理解。

每个示例均相互独立，并假定已存在所列的 Service、标签、namespace 和带 sidecar 的 HTTP8080 工作负载。数值仅作说明；离线 schema/query 检查并非生产/负载测试。本地性示例使用 `localityLbSetting`，而非独立的 `zoneAwareLbSetting` API。

## 选择题（1-5）

### 问题 1：Outlier Detection 基本概念

以下哪项**不是** Outlier Detection 的主要目的？

A. 自动检测行为异常的实例\
B. 当配置的失败阈值和驱逐上限允许时，暂时驱逐实例\
C. 永久删除已移除的实例\
D. 在驱逐期结束后，使被暂时驱逐的主机再次符合条件

<details>

<summary>显示答案</summary>

**答案：C**

Outlier Detection **不会删除实例**，而是将其暂时从流量池中移除。

**说明：**

**Outlier Detection 的工作方式：**


**主要特性：**

1. **自动检测**：统计配置的连续符合条件的 HTTP/传输失败
2. **自动驱逐**：超过阈值时，暂时从流量池中移除
3. **重新加入**：驱逐到期；这不会发送主动探测或证明实例已恢复
4. **临时措施**：仅阻止流量，不删除实例

**选项 C 为什么不正确：**

* Outlier Detection 是一种 Circuit Breaker 模式
* 它会**暂时驱逐**实例，而不会删除它们
* 后续成功的流量可确认恢复；重复失败可能触发更长时间的驱逐

**参考：**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 问题 2：Rate Limiting 类型比较

以下哪项陈述正确比较了 Local Rate Limiting 和 Global Rate Limiting？

A. Local Rate Limiting 的准确性更高\
B. Global Rate Limiting 的性能更快\
C. Local Rate Limiting 在每个 Envoy proxy 独立限制请求\
D. Global Rate Limiting 无需外部服务即可运行

<details>

<summary>显示答案</summary>

**答案：C**

Local Rate Limiting 在**每个 Envoy proxy 独立地**限制请求。

**说明：**

**Local 与 Global Rate Limiting 对比：**

| 特征  | Local Rate Limiting | Global Rate Limiting             |
| --------------- | ------------------- | -------------------------------- |
| **配额范围** | 本地配置的 bucket | 共享 domain/descriptor 和窗口 |
| **性能** | 非常快           | 略慢                  |
| **复杂度**  | 低                 | 高（需要外部服务） |
| **使用场景**    | 常规保护  | 需要精确限制时  |

**Local Rate Limiting 的特性：**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

所示 bucket 初始有100 个 token，并以10/s 的速率补充。在适当的负载分配下，三个副本合计可持续约30/s，且各自具有突发额度；这不是共享的30/s 上限。

**Global Rate Limiting 的特性：**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**Token Bucket 算法：**

![Token-bucket rate limiter 工作流：上限为 100 个 token 的 bucket 每秒补充 10 个 token；每个到达的请求消耗一个 token 后被允许；若没有剩余 token，则以 HTTP 429 拒绝。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**参考：**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 问题 3：Zone Aware Routing 的优势

以下哪项**不是**使用 Zone Aware Routing 的优势？

A. 通过同一 AZ 内通信降低延迟\
B. 节省跨 AZ 数据传输成本\
C. 将每个 Service 副本放在一个 AZ 中，保证可用性提升\
D. 在具备适当策略和容量时，故障转移到可访问的健康 endpoint

<details>

<summary>显示答案</summary>

**答案：C**

C 不是保证。本地性相对于每个调用方而言；它可能将调用方的流量集中到其本地区域。将所有副本移至一个 AZ 会创建共享故障域，并且可能使该区域过载。

**说明：**

**Zone Aware Routing 的正确行为：**


**Zone Aware Routing 的实际优势：**

同区域路由可以降低延迟中的网络部分和可计费的跨区域字节数，但确切的延迟/价格/节省取决于部署。加权80/10/10 表示正常流量会发送到全部三个健康区域；10% 部分不是备用故障转移。其他区域需要实际可访问的 endpoint 和空闲容量。

**DestinationRule 配置示例：**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

**参考：**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 问题 4：Outlier Detection 参数

使用以下 Outlier Detection 配置时，驱逐实例的条件是什么？

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. 错误持续发生 5 秒时\
B. 连续 5 次符合条件的 5xx 失败达到阈值时，受驱逐上限约束\
C. 30 秒内错误率超过 50% 时\
D. 每 30 秒无条件驱逐

<details>

<summary>显示答案</summary>

**答案：B**

B 说明了触发条件。连续五次符合条件的失败可内联触发驱逐；`interval` 是定期扫描间隔，而 `maxEjectionPercent` 可阻止执行。仅慢速成功响应不是延迟离群值。

**说明：**

**关键 Outlier Detection 参数：**

| 参数              | 说明                 | 默认值 | 示例范围 |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors**  | 连续错误阈值 | 5       | 3-10        |
| **interval**           | 分析间隔           | 10s     | 10s-60s     |
| **baseEjectionTime**   | 最短驱逐时间       | 30s     | 30s-300s    |
| **maxEjectionPercent** | 最大驱逐比例      | 10%     | 10%-50%     |

**详细参数说明：**

**consecutive5xxErrors**

```yaml
# Sensitive service (fast detection)
consecutive5xxErrors: 3

# General service
---
consecutive5xxErrors: 5

# Lenient setting (prevent false positives)
---
consecutive5xxErrors: 10
```

**interval**

```yaml
# Fast detection (high load)
interval: 10s

# Typical case
---
interval: 30s

# Stable service
---
interval: 60s
```

**baseEjectionTime**

```yaml
# Quick recovery attempt
baseEjectionTime: 30s

# Typical case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

**maxEjectionPercent**

```yaml
# Conservative (stability priority)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (performance priority)
---
maxEjectionPercent: 50
```

**完整 DestinationRule 示例：**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

**运行示例：**

一次成功会重置相关的连续序列。当主机达到阈值时，如果上限允许，就可以将其驱逐；在其实际驱逐持续时间结束后，它将再次符合条件。重复驱逐会根据 Envoy 乘数/上限增加该持续时间。`minHealthPercent` 是 panic/fail-open 阈值，而不是健康 Pod 的保证比例；0 会禁用该阈值。

**参考：**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 问题 5：Token Bucket 算法

在每个请求消耗一个 token 且需求持续的情况下，初始突发之后，长期受补充限制的准入速率是多少？

```yaml
token_bucket:
  max_tokens: 100
  tokens_per_fill: 10
  fill_interval: 1s
```

A. 10 req/s\
B. 100 req/s\
C. 110 req/s\
D. 1000 req/s

<details>

<summary>显示答案</summary>

**答案：A**

使用 `tokens_per_fill: 10` 和 `fill_interval: 1s` 时，**每秒会添加 10 个 token**，因此平均速率为 **10 req/s**。

**说明：**

**Token Bucket 算法参数：**

* **max\_tokens**：bucket 中可存储的最大 token 数（突发额度）
* **tokens\_per\_fill**：每个 fill\_interval 添加的 token 数（**平均吞吐量**）
* **fill\_interval**：token 添加间隔

**计算方法：**

```
Average request rate = tokens_per_fill / fill_interval
                     = 10 / 1s
                     = 10 req/s

Burst throughput = max_tokens
                 = 100 req (for a brief moment)
```

**随时间的行为：**

```
T=0: 100 tokens in bucket (initial state)
     Can admit up to100 immediate requests if the bucket is full; backend concurrency is separate

T=0.1s: Bucket empty (0 tokens)
        Additional requests rejected

T=1s: 10 tokens added (Refill)
      Can handle 10 requests

T=2s: 10 tokens added
      Can handle 10 requests

Average: 10 req/s (sustainable throughput)
Burst allowance:100 requests from a full bucket, not a sustained req/s rate
```

**实用配置示例：**

```yaml
# Scenario 1: General API endpoint
token_bucket:
  max_tokens: 100        # Allow burst of 100
  tokens_per_fill: 10    # Average 10 req/s
  fill_interval: 1s

# Scenario 2: High-performance API
---
token_bucket:
  max_tokens: 1000       # Allow burst of 1000
  tokens_per_fill: 100   # Average 100 req/s
  fill_interval: 1s

# Scenario 3: Limited resource
---
token_bucket:
  max_tokens: 10         # Only 10 burst
  tokens_per_fill: 1     # Average 1 req/s
  fill_interval: 1s
```

**完整 EnvoyFilter 示例：**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**参考：**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 简答题（6-10）

### 问题 6：实施 Outlier Detection

生产环境中运行的 `product-service` 会间歇性变慢并出现超时。你希望实施 Outlier Detection，以自动驱逐有问题的实例。请编写满足以下要求的 DestinationRule：

**要求：**

* 连续 3 次错误后驱逐
* 使用20秒的定期扫描；可内联检测连续失败
* 将初始基础驱逐时长设置为60秒
* 最多允许驱逐 30%
* 同时检测 502、503、504 gateway 错误

<details>

<summary>显示答案</summary>

仅慢响应不是离群值条件。此示例将 HTTP 错误与本地观察到的传输失败分开；必须存在真实的 route/client 超时，才能观察到超时。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-service-outlier
  namespace: production
spec:
  host: product-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 20s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 3
```

Gateway 子集502/503/504 已包含在5xx 中。相同的3 阈值是冗余但有效的；更低的 gateway 阈值会更早基于该子集驱逐。`interval: 20s` 不会延迟连续错误检测。`baseEjectionTime: 60s` 是初始最短持续时间，而不是主动健康探测。30% 上限会限制驱逐，但无法保持剩余 endpoint 健康。`minHealthPercent: 70` 会在低于其阈值时启用 panic 行为，而不是保留70% 的健康容量。不支持的 `enforcing*` 字段是 Envoy 内部字段，而不是此 DestinationRule API。

一个有十台主机的示例可在三次驱逐后达到上限，但发现的池大小、取整和当前健康状况都很重要；请检查实际强制执行/检测/溢出计数器。返回的主机必须接收到成功流量，才能证明恢复。

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

按照 [outlier 章节](../../../service-mesh/istio/resilience/01-outlier-detection.md)启用可选统计/抓取。根据测量到的错误和空闲容量调整阈值；这里并未暗示存在通用的“生产”值。

</details>

***

### 问题 7：应用 Local Rate Limiting

名为 `api-gateway` 的已注入 sidecar 应用程序正在接收过多 HTTP 流量。你希望应用 Local Rate Limiting，将每个 Envoy proxy 限制为每秒 50 个请求，突发最多 200 个。请编写 EnvoyFilter。

附加要求：

* 应用 rate limit 时添加 `X-RateLimit-Limit` header
* 在 429 响应中包含 `Retry-After: 1` header

<details>

<summary>显示答案</summary>

假定 `api-gateway` 是 `production` 中在 HTTP8080 上注入了 sidecar 的应用程序。这会在选定的 HTTP 请求到达 Envoy 后进行保护；它不是完整的 DDoS 或连接/TLS 保护。对于实际的 Istio ingress gateway，请使用 rate-limit 章节中所示的 namespace/selector 和 `GATEWAY` context。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: api-gateway-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          response_headers_to_add:
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-RateLimit-Limit
              value: '50'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-Local-Rate-Limit
              value: 'true'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: Retry-After
              value: '1'
```

完整 bucket 可立即接纳最多200 个请求，之后以50 token/s 的速率补充。在耗尽后持续以100 requests/s 发送时，假设每个请求消耗一个 token 且无其他限制，约可接纳50/s。平稳的40/s 需求可以满足，但仅40/s 的平均值不能保证每个突发请求都被接纳。准入不保证后端处理成功。

该 filter 默认返回 HTTP429，并且只向其强制执行的 rate-limit 响应添加这些 header。普通200 响应不会从此配置获得这些 header。`Retry-After: 1` 是建议的延迟，不是对一秒后成功的预留或保证。此示例不会创建 `tokens_remaining` dynamic metadata，因此省略了虚构的 Remaining header。

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

对于不同 path-prefix bucket，请使用以下**替代方案**，而不是第二个重叠的 filter。显式 descriptor generator 受 Istio1.31 固定的 Envoy API 支持。缺失/不匹配的 path 使用有界默认 bucket；前缀匹配包含以所给文本开头的较长 path。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: path-based-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 30
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          always_consume_default_token_bucket: false
          descriptors:
          - entries:
            - key: header_match
              value: /api/login
            token_bucket:
              max_tokens: 30
              tokens_per_fill: 10
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /api/search
            token_bucket:
              max_tokens: 300
              tokens_per_fill: 100
              fill_interval: 1s
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: /api/login
                headers:
                - name: :path
                  string_match:
                    prefix: /api/login
          - actions:
            - header_value_match:
                descriptor_value: /api/search
                headers:
                - name: :path
                  string_match:
                    prefix: /api/search
```

```promql
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

有关可选统计收集、global service/Redis 前提条件和受信任 identity 处理，请参阅 [rate limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)。

</details>

***

### 问题 8：Zone Aware Routing 配置

你的 AWS EKS 集群分布在 3 个 AZ（us-east-1a、us-east-1b、us-east-1c）中。你希望为 `order-service` 配置 Zone Aware Routing，以降低跨 AZ 数据传输成本。

**要求：**

* 将 70% 流量发送到同一 AZ 的 Pod
* 向其他 AZ 分别分配 15%
* 说明单独的 priority-failover 替代方案和完整 AZ 故障的限制
* 说明为什么 minHealthPercent50 不是50% 健康保证或本地性激活开关

<details>

<summary>显示答案</summary>

这些要求混合了加权分配、priority failover 和健康容量保证。无法通过在一个 locality policy 中组合字段来表达所有这些要求。对正常70/15/15 流量使用以下分配策略；`minHealthPercent` 不是仅在一半 Pod 健康时激活本地性的开关。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-locality
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 70
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 70
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 70
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

如需本地区域优先和溢出，请改用此**替代方案**，而不是同时使用两种策略。`localityLbSetting.failover` 接受 region 名称，而非 `region/zone` path。此 API 中 `distribute` 与 priority 模式互斥。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-failover
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

完整的区域故障也会影响该区域中的 client：需要在其他位置有存活/重新创建的 client 或 entry point。剩余健康 endpoint 容量、检测、连接复用和网络可达性决定故障转移；该策略不保证100% 流量到 zoneB，也不保证即时恢复。`minHealthPercent: 0` 禁用对不健康 host 的 panic 使用，且100% 上限允许在全部失败时驱逐所有 endpoint。两者都不会凭空产生健康容量。

使用 [zone-aware 章节](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)进行 Node→Pod topology 检查、匹配 topologySpreadConstraints、EKS node group 和 EDS 诊断。不要仅为了使示例匹配而手动分配 cloud topology label。标准 Istio metric 不包含 `source_cluster_zone`/`destination_cluster_zone`；区域查询需要经验证的 enrichment，且与路由分开。

**说明性的成本算术**：假定十进制1TB=1000GB、每个可计费 GB 的有效费用为$0.01、基准跨区域比例为2/3，之后比例为0.30。这是简化假设，并非 AWS 报价、实测节省或完整网络账单。

| 每月流量 | 之前 | 之后 | 每月节省 | 每年节省 |
|---|---:|---:|---:|---:|
|1TB|$6.67|$3.00|$3.67|$44.00|
|100TB|$666.67|$300.00|$366.67|$4,400.00|

建模的降幅为55%。应根据精确比例计算，并且仅对显示的货币进行取整；年度节省不能乘以过早取整的每月$367。实际可计费方向、字节量、region 和 service 处理费用需要 billing/flow 证据。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### 问题 9：组合弹性策略

`payment-service` 是一个调用外部支付 API 的关键 Service。实施以下组合弹性策略：

1. **Outlier Detection**：连续 3 次错误后驱逐实例
2. **Retry**：对已验证的幂等读取，最多允许对502/503/504 重试3 次；明确禁用写入重试
3. **Timeout**：每个请求 5 秒超时
4. **Circuit Breaker**：说明为什么“错误超过50% 时阻止整个服务”不是此 API 的 pool breaker；改为展示支持的并发限制

编写 DestinationRule 和 VirtualService。

<details>

<summary>显示答案</summary>

DestinationRule 无法通过列出的 success-rate 字段实施“在全局范围内阻止此服务中超过50% 错误”。这些字段在此处不受支持，统计偏差也不是固定的错误百分比阈值。Pool circuit breaker 限制每个调用方 proxy 的 upstream cluster 的并发连接/请求；outlier detection 会改变 host 资格。协调的服务范围错误率 breaker 需要单独设计的 application/controller 机制。

此答案适用于**caller→payment-service HTTP8080**。该 service 的传出支付 API 调用需要其自身的 destination policy 和 TLS 可见性，如 [outlier 章节](../../../service-mesh/istio/resilience/01-outlier-detection.md)中所述。Mesh retry 无法提供支付幂等性。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-service-resilience
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service-retry
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
```

明确的写入/回退规则禁用继承的 mesh retry。仅重试其 application 语义可以安全重复的匹配读取。`gateway-error` 覆盖502/503/504；不会向支付写入添加宽泛的 reset/5xx/4xx 条件。传输错误无法确定支付是否已提交。

`attempts: 3` 表示初始尝试**之后**最多三次重试。四次完整的2s 尝试加上 backoff 无法在5s 内完成，因此总 route 预算会更早停止；application deadline 也必须涵盖 upload/streaming 和 downstream 工作。这不是精确的失败时间线，也不保证特定的最终 HTTP 状态。

`maxRetries: 3` 限制该 proxy/cluster 的并发未完成重试，而不是每请求重试次数。`http2MaxRequests` 也适用于 HTTP/1.1。`maxRequestsPerConnection: 0` 允许复用，不受该请求计数上限限制。待处理/活动请求溢出可以拒绝 HTTP 请求，而一次连接限制命中可能先导致排队。这些设置都不是全局50% 错误 circuit。

| 观察结果 | 正确解释 |
|---|---|
|安全读取得到502，随后在重试时成功|重试可能有帮助；它可能再次访问同一 host，且不保证成功|
|host 达到其失败阈值|如果上限允许，该 caller 可将其驱逐；其他 caller 各自维护状态|
|所有 endpoint 都失败|可能没有健康 destination 留存；驱逐计时器不会修复 service，也不会实施协调的 half-open 测试|

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

`_open` series 是0/1 gauge，而不是传递给 `rate` 的 counter。请限定 Envoy cluster label 的范围并启用相关统计。有关安全的运行权衡，请参阅 [retry/timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md) 和 [circuit breaking](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)。

</details>

***

### 问题 10：性能优化和成本降低

在大规模 microservices 环境中，每月网络成本为 $5,000。请制定一项综合策略，使用 Istio 弹性功能优化性能并降低成本。

**当前情况：**

* 100 个 Service 均匀分布在 3 个 AZ 中
* 每月流量：500TB
* 平均响应时间：150ms
* 错误率：3%

**目标：**

* 跨 AZ 成本降低 50%
* 平均响应时间低于 100ms
* 错误率低于 1%

<details>

<summary>显示答案</summary>

将给定的100 个 Service、500TB/月、$5,000 账单、150ms 延迟和3% 错误视为**假设基准**，而不是此次审计的实测结果。首先识别可计费流量组件和面向用户的 SLI 边界。Proxy hop 延迟并不自动等同于端到端请求延迟。

**1. 为每个已审查 Service 整合一个 destination policy**

代表性的 `api-service` 示例在一个 DestinationRule 中组合了 pool 限制、本地性加权和受支持的 outlier detection。不要应用多个相互竞争的 wildcard rule，也不要将每个 Service 路由到一个通用 backend。根据每个 caller 和 destination 确定值；该示例不是生产默认值。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-resilience
  namespace: production
spec:
  host: api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 80
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 2
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-routing
  namespace: production
spec:
  hosts:
  - api-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
```

**2. 将 rate limit 作为经过测量的准入控制**

这些是 `production` 中 HTTP8080 上每个 proxy 独立的 bucket。验证 tier label 和容量；仅有“critical” label 并不能证明某个特定速率合理。它们不施加共享的 service/account 配额，也不能替代 edge protection。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: critical-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: critical
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 500
            tokens_per_fill: 100
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: standard-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: standard
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**3. 将说明性模型与实际账单分开**

假定十进制500TB=500,000GB、基准跨 AZ 比例为2/3，之后比例为0.20，以及每个可计费 GB 的**假定有效费用**为$0.015。建模的可变组件为：

| 模型 | 计算 | 每月金额 |
|---|---|---:|
|之前|500,000 × 2/3 × 0.015|$5,000|
|之后|500,000 × 0.20 × 0.015|$1,500|
|差额|5,000 − 1,500|$3,500 (70%)|

只有在整个账单均为此可变组件时，这才与完整的$5,000 基准匹配。实际网络账单可能包括其他方向、load-balancer/NAT 处理、internet/region 传输和固定成本。当请求/响应大小不同时，请求权重不一定等于字节比例。请根据可计费 flow/CUR 数据和当前价格验证建模节省；不要承诺总账单节省70%。

对于说明性的单跳网络延迟：同 AZ 为0.3ms，跨 AZ 为1.5ms；均等三区域基准得到0.3×1/3+1.5×2/3=1.10ms；80/20 得到0.54ms。此0.56ms 组件变化无法证明端到端改善150ms→100ms。跟踪真实关键路径、database/pool 等待、application 工作和 retry 放大。

**4. 验证分阶段变更**

| 说明性阶段 | 扩大范围前所需的证据 |
|---|---|
|第1–2周：topology/locality|实际 Node/Pod/EDS 映射、区域容量、请求和可计费字节分布、故障行为|
|第3–4周：outlier/pool 限制|强制驱逐、剩余 endpoint、溢出、延迟和 application 错误原因|
|第5–6周：rate limit|真实过载在不会造成不可接受的合法请求拒绝的情况下被拒绝；观察 client retry 行为|

该计划仅作说明。定义 rollback/stop 条件，并在每次变更后进行测量。Outlier detection 可能移除容量或暴露底层故障；它不保证错误低于1%。改变 timeout 可能产生更多失败，而不是使工作更快。

**5. 使用类型正确且范围明确的 metric**

以下每 Service 查询可诊断代表性 Service。单独测量面向用户的 SLI。平均延迟使用 histogram sum/count，而非 P50；活动驱逐是 gauge，而强制驱逐事件是 counter。

```promql
# Per-service mean request duration, milliseconds
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m])) /
sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

# Per-service HTTP5xx percentage (define gRPC/application failures separately)
100 * sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

envoy_cluster_outlier_detection_ejections_active{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

启用可选统计并处理无流量/抓取失败。跨 AZ 查询需要真实的区域 enrichment；`source_cluster_zone!=destination_cluster_zone` 不是有效的 PromQL。有关显式限定范围的条件查询，请参阅 [zone 章节](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)。

**目标仍需测量**：跨 AZ 成本−50%、面向用户的平均延迟≤100ms 和错误<1% 是验收标准，而不是预测结果。Cache placement 可以缩短距离，但本身不能提高命中率。比较开销前，评估 ambient 功能/容量要求；通用30–50% 节省尚未得到证实。一个跨多区域 Deployment 的 HPA 不会独立扩缩每个区域；独立的区域扩缩需要明确的 workload/controller 设计。

参考资料：[Outlier detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)、[rate limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)、[EKS network cost optimization](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)。

</details>

***

## 分数计算

* 选择题 1-5：每题 10 分（共 50 分）
* 简答题 6-10：每题 10 分（共 50 分）
* **总分：100 分**

**评估标准：**

* 90-100 分：优秀（Istio 弹性专家）
* 80-89 分：理解良好；部署验证需另行进行
* 70-79 分：一般（建议进一步学习）
* 60-69 分：低于平均（需要复习基本概念）
* 0-59 分：需要重新学习

## 学习资源

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
