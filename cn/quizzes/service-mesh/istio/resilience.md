# 韧性测验

> **最后更新**：2026 年 9 月 11 日 · Istio1.31 · Kubernetes1.32–1.36；EKS 兼容性参阅安装章节。

本测验检验您对 Istio 韧性功能的理解。

各示例独立，假定所命名的 Service、标签、命名空间和使用 Sidecar 的 HTTP8080 工作负载存在。数值为示意；离线模式/查询检查不是生产/负载测试。局部性示例使用 `localityLbSetting`，不是独立的 `zoneAwareLbSetting` API。

## 选择题（1-5）

### 问题 1：异常检测基本概念

以下哪项**不是**异常检测的主要目的？

A. 自动检测行为异常的实例\
B. 配置的故障阈值和剔除上限允许时，临时剔除实例\
C. 永久删除被移除的实例\
D. 剔除期结束后，使临时剔除的主机重新具备资格

<details>

<summary>显示答案</summary>

**答案：C**

异常检测**不删除实例**，只是将其临时移出流量池。

**解释：**

**异常检测如何工作：**


**关键功能：**

1. **自动检测**：统计所配置的连续合格 HTTP/传输失败
2. **自动剔除**：超过阈值时临时移出流量池
3. **重新加入**：剔除到期；这不会发送主动探测或证明恢复
4. **临时措施**：只阻止流量，不删除实例

**选项 C 为什么不正确：**

* 异常检测是一种断路器模式
* 它**临时剔除**实例，不删除实例
* 后续成功流量确认恢复；重复失败可能触发更长剔除

**参考资料：**

* [异常检测](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 问题 2：限速类型比较

哪项陈述正确比较了本地限速和全局限速？

A. 本地限速准确度更高\
B. 全局限速性能更快\
C. 本地限速在每个 Envoy 代理独立限制请求\
D. 全局限速无需外部服务

<details>

<summary>显示答案</summary>

**答案：C**

本地限速**在每个 Envoy 代理独立**限制请求。

**解释：**

**本地与全局限速比较：**

| 特性 | 本地限速 | 全局限速 |
| --------------- | ------------------- | -------------------------------- |
| **配额范围** | 本地配置的桶 | 共享域/描述符及时间窗口 |
| **性能** | 很快 | 稍慢 |
| **复杂度** | 低 | 高（需要外部服务） |
| **使用场景** | 一般保护 | 需要精确限制时 |

**本地限速特性：**

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

所示桶初始有 100 个令牌，每秒补充 10 个。在适当负载分布下，三个副本总计可持续约 30/s，且各有突发额度；这不是共享的 30/s 上限。

**全局限速特性：**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**令牌桶算法：**

![令牌桶限速器流程：桶最多容纳 100 个令牌，每秒补充 10 个；每个到达请求消耗一个令牌获准，无剩余令牌时以 HTTP 429 拒绝。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**参考资料：**

* [限速](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 问题 3：可用区感知路由的收益

哪项**不是**使用可用区感知路由的收益？

A. 通过同可用区通信降低延迟\
B. 节省跨可用区数据传输成本\
C. 将每个服务副本放在一个可用区内，保证提高可用性\
D. 在适当策略和容量存在时，故障转移到可达健康端点

<details>

<summary>显示答案</summary>

**答案：C**

C 不是保证。局部性相对于每个调用方，可将调用方流量集中在本地可用区。将所有副本移到一个可用区会创建共享故障域，并可能使该可用区过载。

**解释：**

**可用区感知路由的正确行为：**


**可用区感知路由的实际收益：**

同可用区路由可降低延迟中的网络部分和计费跨可用区字节数，但确切延迟/价格/节省取决于部署。80/10/10 权重表示正常流量发送到全部三个健康可用区；10% 部分不是备用故障转移。其他可用区需要真实可达端点和备用容量。

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

**参考资料：**

* [可用区感知路由](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 问题 4：异常检测参数

以下异常检测配置在什么条件下剔除实例？

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. 错误持续 5 秒时\
B. 5 次连续合格 5xx 失败达到阈值，且受剔除上限约束时\
C. 30 秒内错误率超过 50% 时\
D. 每 30 秒无条件剔除

<details>

<summary>显示答案</summary>

**答案：B**

B 说明触发条件。五次连续合格失败可即时触发剔除；`interval` 是周期扫描间隔，`maxEjectionPercent` 可阻止实际执行。仅缓慢的成功响应不是延迟异常值。

**解释：**

**异常检测关键参数：**

| 参数 | 描述 | 默认值 | 示例范围 |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors** | 连续错误阈值 | 5 | 3-10 |
| **interval** | 分析间隔 | 10s | 10s-60s |
| **baseEjectionTime** | 最小剔除时间 | 30s | 30s-300s |
| **maxEjectionPercent** | 最大剔除比例 | 10% | 10%-50% |

**参数详细解释：**

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

成功响应重置相关连续序列。主机达到阈值时，若上限允许则可剔除；实际剔除时长结束后重新具备资格。重复剔除通过 Envoy 倍数/上限增加时长。`minHealthPercent` 是恐慌/故障放行阈值，不保证健康 Pod 比例；0 禁用该阈值。

**参考资料：**

* [异常检测](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 问题 5：令牌桶算法

每请求一个令牌且需求持续时，初始突发后受补充速率限制的长期准入速率是多少？

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

设置 `tokens_per_fill: 10` 和 `fill_interval: 1s` 时，**每秒添加 10 个令牌**，所以平均为 **10 req/s**。

**解释：**

**令牌桶算法参数：**

* **max\_tokens**：桶可存储的最大令牌数（突发额度）
* **tokens\_per\_fill**：每个 fill\_interval 添加的令牌数（**平均吞吐量**）
* **fill\_interval**：令牌添加间隔

**计算方法：**

```
Average request rate = tokens_per_fill / fill_interval
                     = 10 / 1s
                     = 10 req/s

Burst throughput = max_tokens
                 = 100 req (for a brief moment)
```

**随时间变化的行为：**

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

**实际配置示例：**

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

**参考资料：**

* [限速](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 简答题（6-10）

### 问题 6：实现异常检测

生产中的 `product-service` 间歇性变慢并超时。您希望通过异常检测自动剔除问题实例。编写满足以下要求的 DestinationRule：

**要求：**

* 连续 3 次错误后剔除
* 每 20 秒周期扫描；连续失败可即时检测
* 初始基础剔除时长设为 60 秒
* 最多允许剔除 30%
* 同时检测 502、503、504 网关错误

<details>

<summary>显示答案</summary>

仅慢响应不是异常检测条件。示例区分 HTTP 错误和本地观察的传输失败；必须有真实路由/客户端超时，才能观察超时。

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

网关错误子集 502/503/504 已包含于 5xx。相同阈值 3 虽冗余但有效；更低网关阈值会更早按该子集剔除。`interval: 20s` 不延迟连续错误检测。`baseEjectionTime: 60s` 是初始最小时长，不是主动健康探测。30% 上限限制剔除，但不能让剩余端点保持健康。`minHealthPercent: 70` 会在低于阈值时启用恐慌行为，不是保留 70% 健康容量。不受支持的 `enforcing*` 字段是 Envoy 内部字段，不属于此 DestinationRule API。

十主机示例在三次剔除后可达到上限，但已发现池大小、取整和当前健康状况都重要；检查实际执行/检测/溢出计数器。重新加入的主机必须收到成功流量才能证明恢复。

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

按[异常检测章节](../../../service-mesh/istio/resilience/01-outlier-detection.md)启用可选统计/抓取。根据实测错误和备用容量调整阈值；不暗示通用“生产”值。

</details>

***

### 问题 7：应用本地限速

名为 `api-gateway`、已注入 Sidecar 的应用收到过量 HTTP 流量。您希望应用本地限速，将每个 Envoy 代理限制为每秒 50 请求，最大突发 200。编写 EnvoyFilter。

额外要求：

* 应用限速时添加 `X-RateLimit-Limit` 标头
* 在 429 响应中包含 `Retry-After: 1` 标头

<details>

<summary>显示答案</summary>

假定 `api-gateway` 是 `production` 中运行 HTTP8080、注入 Sidecar 的应用。它在选定 HTTP 请求到达 Envoy 后提供保护；不是完整 DDoS 或连接/TLS 防护。对于真正的 Istio 入口网关，按限速章节使用其命名空间/选择器及 `GATEWAY` 上下文。

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

满桶可立即允许最多 200 请求，再每秒补充 50 个令牌。耗尽后若需求持续 100 请求/秒，在每请求一个令牌、无其他限制的假设下，约可允许 50/s。平滑 40/s 需求可以容纳，但仅 40/s 平均值不保证每次突发都接受。准入不保证后端处理成功。

过滤器默认返回 HTTP429，仅为实际限速响应添加这些标头。此配置不会为正常 200 响应添加这些标头。`Retry-After: 1` 是建议延迟，不是预留，也不保证一秒后成功。此示例不创建 `tokens_remaining` 动态元数据，因此省略虚构 Remaining 标头。

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

不同路径前缀桶使用这个**替代方案**，不要添加第二个重叠过滤器。显式描述符生成器由 Istio1.31 固定的 Envoy API 支持。缺失/不匹配路径使用有界默认桶；前缀匹配包含以所给文本开头的更长路径。

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

可选统计采集、全局服务/Redis 前提条件和可信身份处理参阅[限速](../../../service-mesh/istio/resilience/02-rate-limiting.md)。

</details>

***

### 问题 8：可用区感知路由配置

您的 AWS EKS 集群分布在 3 个可用区（us-east-1a、us-east-1b、us-east-1c）。希望为 `order-service` 配置可用区感知路由，减少跨可用区数据传输成本。

**要求：**

* 将 70% 流量发送到同可用区 Pod
* 向其他可用区各分配 15%
* 解释独立优先级故障转移方案及整个可用区故障的限制
* 解释为什么 minHealthPercent50 不是 50% 健康保证或局部性激活开关

<details>

<summary>显示答案</summary>

这些要求混合了加权分配、优先级故障转移和健康容量保证。不能在一个局部性策略中组合字段来全部表达。正常 70/15/15 流量使用以下分配策略；`minHealthPercent` 不是仅当一半 Pod 健康时才激活局部性的开关。

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

若改用本地可用区优先和溢出，应用此**替代方案**，不要同时应用两种策略。`localityLbSetting.failover` 接受区域名，不是 `region/zone` 路径。此 API 中 `distribute` 和优先级模式互斥。

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

整个可用区故障也影响其中客户端：需要其他位置的存活/重建客户端或入口。剩余健康端点容量、检测、连接复用和网络可达性决定故障转移；策略不承诺 100% 发到 zoneB 或即时恢复。`minHealthPercent: 0` 禁用恐慌模式使用不健康主机，100% 上限允许所有端点失败时全部剔除。两者都不会凭空产生健康容量。

Node→Pod 拓扑检查、匹配 topologySpreadConstraints、EKS 节点组和 EDS 诊断参阅[可用区感知章节](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)。不要仅为匹配示例而手动分配云拓扑标签。标准 Istio 指标不含 `source_cluster_zone`/`destination_cluster_zone`；可用区查询需要经验证的数据补充，与路由独立。

**成本算术示例**：假定十进制 1TB=1000GB，每计费 GB 有效费用 $0.01，基线跨可用区比例 2/3，之后为 0.30。这是简化假设，不是 AWS 报价、实测节省或完整网络账单。

| 月流量 | 之前 | 之后 | 月节省 | 年节省 |
|---|---:|---:|---:|---:|
| 1TB | $6.67 | $3.00 | $3.67 | $44.00 |
| 100TB | $666.67 | $300.00 | $366.67 | $4,400.00 |

模型减少比例为 55%。使用精确分数计算，只对展示金额取整；年节省不能乘以过早取整的月节省 $367。实际计费方向、字节量、区域和服务处理费用需要计费/流量证据。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### 问题 9：组合韧性策略

`payment-service` 是调用外部支付 API 的关键服务。实现以下组合韧性策略：

1. **异常检测**：连续 3 次错误后剔除实例
2. **重试**：对已验证幂等读取，允许在 502/503/504 时最多重试 3 次；显式禁用写入重试
3. **超时**：每请求 5 秒超时
4. **断路器**：解释为什么“错误超过 50% 时阻断整个服务”不是此 API 的连接池断路器，并展示受支持并发限制

编写 DestinationRule 和 VirtualService。

<details>

<summary>显示答案</summary>

DestinationRule 不能通过所列成功率字段实现“错误超过 50% 时全局阻断此服务”。此处不支持这些字段，统计偏差也不是固定错误百分比阈值。连接池断路器约束每调用方代理上游集群的并发连接/请求；异常检测改变主机资格。协调一致的服务范围错误比例断路器需要单独设计的应用/控制器机制。

此答案适用于**调用方→payment-service HTTP8080**。服务出站支付 API 调用需要自己的目的地策略和 TLS 可见性，如[异常检测章节](../../../service-mesh/istio/resilience/01-outlier-detection.md)所述。网格重试不能提供支付幂等性。

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

显式写入/回退规则禁用继承的网格重试。仅重试匹配且应用语义可安全重复的读取。`gateway-error` 覆盖 502/503/504；不为支付写入添加宽泛 reset/5xx/4xx 条件。传输错误不能确定支付是否已提交。

`attempts: 3` 表示初始尝试**之后**最多三次重试。四次完整 2s 尝试加退避无法容纳在 5s 内，因此总路由预算会更早停止；应用期限还必须覆盖上传/流式传输和下游工作。这不是精确故障时间线，也不承诺特定最终 HTTP 状态。

`maxRetries: 3` 限制该代理/集群中并发未完成重试，不是每请求重试数。`http2MaxRequests` 也适用于 HTTP/1.1。`maxRequestsPerConnection: 0` 允许不受该请求数上限限制的复用。待处理/活动请求溢出可能拒绝 HTTP 请求，而一次连接限制命中可能先引起排队。这些设置都不是全局 50% 错误断路器。

| 观察 | 正确解释 |
|---|---|
| 安全读取收到 502，再重试成功 | 重试可有帮助；可能再次访问同一主机，且不保证成功 |
| 主机达到失败阈值 | 若上限允许，该调用方可能剔除它；其他调用方维护各自状态 |
| 所有端点失败 | 可能不剩健康目的地；剔除定时器不修复服务，也不实现协调的半开测试 |

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

`_open` 序列是 0/1 gauge，不是可传给 `rate` 的计数器。限定 Envoy 集群标签并启用相关统计。安全运维权衡参阅[重试/超时](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)和[断路器](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)。

</details>

***

### 问题 10：性能优化和成本降低

在大型微服务环境中，月网络成本为 $5,000。制定利用 Istio 韧性功能优化性能和降低成本的全面策略。

**当前情况：**

* 100 个服务均匀分布于 3 个可用区
* 月流量：500TB
* 平均响应时间：150ms
* 错误率：3%

**目标：**

* 跨可用区成本降低 50%
* 平均响应时间低于 100ms
* 错误率低于 1%

<details>

<summary>显示答案</summary>

将给出的 100 个服务、500TB/月、$5,000 账单、150ms 延迟和 3% 错误视为**假设基线**，不是本审计实测结果。先确定计费流量组成和面向用户的 SLI 边界。代理跳点延迟不自动等于端到端请求延迟。

**1. 为每个已审核服务整合一个目的地策略**

代表性 `api-service` 示例在一个 DestinationRule 中结合连接池限制、局部性权重和受支持异常检测。不要应用多个竞争通配规则，也不要将所有服务路由到一个通用后端。根据各调用方和目的地调整数值；样本不是生产默认值。

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

**2. 将限速作为实测准入控制**

这些是 `production` 中 HTTP8080 上相互独立的每代理桶。验证层级标签和容量；仅“critical”标签不足以证明特定速率合理。它们不施加共享服务/账户配额，也不替代边缘防护。

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

**3. 区分示意模型与实际账单**

假定十进制 500TB=500,000GB，基线跨可用区比例 2/3，之后为 0.20，且每计费 GB **假设有效费用**为 $0.015。模型可变部分为：

| 模型 | 计算 | 月金额 |
|---|---|---:|
| 之前 | 500,000 × 2/3 × 0.015 | $5,000 |
| 之后 | 500,000 × 0.20 × 0.015 | $1,500 |
| 差额 | 5,000 − 1,500 | $3,500（70%） |

只有整张账单都是此可变部分时，才匹配完整 $5,000 基线。实际网络账单可能包括其他方向、负载均衡器/NAT 处理、互联网/区域传输和固定成本。请求/响应大小不同时，请求权重不一定等于字节比例。根据计费流量/CUR 数据和当前价格验证模型节省；不要承诺总账单节省 70%。

若用示意单跳网络延迟：同可用区 0.3ms、跨可用区 1.5ms，均匀三可用区基线为 0.3×1/3+1.5×2/3=1.10ms；80/20 为 0.54ms。此 0.56ms 组成变化不能证明端到端从 150ms 改善为 100ms。追踪实际关键路径、数据库/连接池等待、应用工作和重试放大。

**4. 验证分阶段更改**

| 示意阶段 | 扩大范围前所需证据 |
|---|---|
| 第 1–2 周：拓扑/局部性 | 实际 Node/Pod/EDS 映射、可用区容量、请求和计费字节分布、故障行为 |
| 第 3–4 周：异常检测/连接池限制 | 实际剔除、剩余端点、溢出、延迟和应用错误原因 |
| 第 5–6 周：限速 | 拒绝真实过载且不造成不可接受的合法请求拒绝；观察客户端重试行为 |

时间表仅为示意。定义回滚/停止标准，每次更改后测量。异常检测可能减少容量或暴露底层故障；不保证错误低于 1%。改变超时可能产生更多失败，而非使工作更快。

**5. 使用类型正确、范围明确的指标**

以下每服务查询诊断代表性服务。单独测量面向用户的 SLI。平均延迟使用直方图 sum/count，不是 P50；活动剔除是 gauge，实际剔除事件是 counter。

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

启用可选统计并处理无流量/抓取失败。跨可用区查询需要真实可用区数据补充；`source_cluster_zone!=destination_cluster_zone` 不是有效 PromQL。明确限定范围的条件查询参阅[可用区章节](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)。

**目标仍需测量**：跨可用区成本 −50%、面向用户平均延迟 ≤100ms、错误 <1% 是验收标准，不是预测结果。缓存放置可减少距离，但本身不提高命中率。比较开销前评估 Ambient 功能/容量要求；通用 30–50% 节省未被证实。多可用区 Deployment 上的一个 HPA 不会独立扩缩每个可用区；独立分区扩缩需要明确工作负载/控制器设计。

参考资料：[异常检测](../../../service-mesh/istio/resilience/01-outlier-detection.md)、[限速](../../../service-mesh/istio/resilience/02-rate-limiting.md)、[EKS 网络成本优化](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)。

</details>

***

## 分数计算

* 选择题 1-5：每题 10 分（共 50 分）
* 简答题 6-10：每题 10 分（共 50 分）
* **总分：100 分**

**评估标准：**

* 90-100 分：优秀（Istio 韧性专家）
* 80-89 分：理解良好；部署验证需单独进行
* 70-79 分：一般（建议进一步学习）
* 60-69 分：低于平均（需复习基本概念）
* 0-59 分：需要重新学习

## 学习资源

* [异常检测](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [限速](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [可用区感知路由](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
