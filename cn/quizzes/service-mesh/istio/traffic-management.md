# 流量管理测验

> **审核版本**：Istio 1.31.0 **EKS 版本**：1.34–1.36 **最后更新**：2026年9月11日

本测验用于检验你对 Istio 流量管理功能的理解。

## 选择题（1–5）

### 问题 1：VirtualService 的作用

以下关于 VirtualService 的说法，哪一项**正确**？

A. 它会取代 Kubernetes Service 资源\
B. 它只能定义负载均衡算法\
C. 它定义路由规则并控制流量\
D. 它会让每个应用请求都经过 istiod

<details>

<summary>显示答案</summary>

**答案：C**

VirtualService 是 Istio 的核心 CRD，通过定义**路由规则**来控制流量。

**说明：**

* A (错误)：VirtualService 不会取代 Kubernetes Service；它会在 Service 之上添加路由规则
* B (错误)：负载均衡由 DestinationRule 处理；VirtualService 定义路由规则
* C (正确)：VirtualService 可定义以下内容：
  * HTTP/TCP 路由规则
  * 基于 URL 路径的路由
  * 基于 Header 的路由
  * 基于权重的流量拆分
  * Timeout 和 Retry 设置
* D (错误)：istiod 会编译 VirtualService API 对象；Envoy 在数据平面执行生成的路由配置

**示例：**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
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
```

**参考：**

* [路由](../../../service-mesh/istio/traffic-management/02-routing.md)
* [VirtualService 概念](../../../service-mesh/istio/02-basic-concepts.md#1-virtualservice)

</details>

***

### 问题 2：DestinationRule 的功能

以下哪项**不是** DestinationRule 执行的功能？

A. 定义子集\
B. 配置负载均衡算法\
C. 基于 HTTP 路径的路由\
D. 配置连接池

<details>

<summary>显示答案</summary>

**答案：C**

基于 HTTP 路径的路由属于 **VirtualService** 的职责。

**说明：**

**DestinationRule 的主要功能：**

1. **定义子集（A - 正确）**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
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

2. **负载均衡配置（B - 正确）**

```yaml
spec:
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN  # RANDOM, LEAST_REQUEST, etc.
```

3. **连接池配置（D - 正确）**

```yaml
spec:
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
```

4. **基于 HTTP 路径的路由（C - 错误）**

* 这是 VirtualService 的职责：

```yaml
# Handled by VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing-example
spec:
  hosts:
  - api-service
  http:
  - match:
    - uri:
        prefix: /api  # Path-based routing
    route:
    - destination:
        host: api-service
```

**对比表：**

| 功能 | VirtualService | DestinationRule |
| --- | --- | --- |
| 路由规则 | 是 | 否 |
| 路径匹配 | 是 | 否 |
| 子集定义 | 否 | 是 |
| 负载均衡 | 否 | 是 |
| 连接池 | 否 | 是 |

**参考：**

* [负载均衡](../../../service-mesh/istio/traffic-management/06-load-balancing.md)
* [连接池](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)

</details>

***

### 问题 3：Canary 部署中的流量拆分

以下 VirtualService 配置中，v1 和 v2 之间的流量比例是多少？

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 80
    - destination:
        host: reviews
        subset: v2
      weight: 20
```

A. v1：50%，v2：50%\
B. v1：80%，v2：20%\
C. v1：20%，v2：80%\
D. v1：100%，v2：0%

<details>

<summary>显示答案</summary>

**答案：B**

由于权重值为 **v1：80，v2：20**，流量将按 **80% 到 v1** 和 **20% 到 v2** 的比例分配。

**说明：**

**基于权重的流量拆分：**

* `weight` 字段表示相对比例
* 总权重：80 + 20 = 100
* v1 的比例：80/100 = 80%
* v2 的比例：20/100 = 20%

**Canary 部署阶段：**

```yaml
# Stage 1: 10% Canary
- weight: 90  # v1
- weight: 10  # v2

# Stage 2: 25% Canary
- weight: 75  # v1
- weight: 25  # v2

# Stage 3: 50% Canary
- weight: 50  # v1
- weight: 50  # v2

# Stage 4: 100% v2
- weight: 0   # v1
- weight: 100 # v2
```

**使用 Argo Rollouts 自动执行 Canary：**

```yaml
# Strategy fragment; merge into a complete Rollout with selector/template
strategy:
  canary:
    trafficRouting:
      istio:
        virtualService:
          name: reviews
        destinationRule:
          name: reviews
          stableSubsetName: v1
          canarySubsetName: v2
    steps:
    - setWeight: 10
    - pause: {duration: 2m}
    - setWeight: 25
    - pause: {duration: 2m}
    - setWeight: 50
    - pause: {duration: 2m}
```

**参考：**

* [流量拆分](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)
* [Argo Rollouts 集成](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

</details>

***

### 问题 4：Gateway 的用途

以下哪项**不是** Istio ingress Gateway 配置的职责？

A. 定义监听端口、协议和允许的主机\
B. 使用证书 Secret 配置 TLS 终止\
C. 自动向每个应用 Pod 注入代理，并单独保护所有东西向流量\
D. 将入口流量绑定到 VirtualService 路由

<details>
<summary>显示答案</summary>

**答案：C**

Istio Gateway 用于配置现有的网关代理。工作负载加入网格以及服务间网格安全，需要 sidecar 或 ambient 数据平面及其策略。Gateway 代理本身也可以发起上游 mTLS，因此“Gateway 永远不会使用 mTLS”同样不正确。Gateway 不会签发证书；`credentialName` 引用的是由网关工作负载 namespace 中的其他组件管理的 Secret。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts: [bookinfo.example.com]
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
```

[Gateway 与 VirtualService](../../../service-mesh/istio/traffic-management/01-gateway-virtualservice.md)

</details>

***

### 问题 5：超时和重试策略

以下 VirtualService 配置表示什么？

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

A. 原始请求后最多额外重试 3 次，每次发送限制为 2 秒，整个请求限制为 10 秒\
B. 总计在 2 秒内最多重试 3 次，每次尝试限制为 10 秒\
C. 总计在 10 秒内无限重试，每次尝试限制为 2 秒\
D. 10 秒后失败且不重试

<details>

<summary>显示答案</summary>

**答案：A**

此配置允许在**原始请求之后最多额外重试 3 次**，将每次发送限制为 **2 秒**，并将整个请求限制为 **10 秒**。因此，最多会向上游发送四次请求。

**说明：**

**配置解读：**

```yaml
timeout: 10s           # Maximum time for entire request
retries:
  attempts: 3          # Up to 3 retries after the original request
  perTryTimeout: 2s    # Time limit for each delivery
```

这些计时示例假设故障符合 retryOn 条件，并且未计入退避/处理开销。超时并不意味着所有策略都会重试。

**执行场景：**

```
Scenario 1: First attempt succeeds
+- 1st attempt: 1.5s elapsed -> Success
+- Total time: 1.5s

Scenario 2: Success after 2 attempts
+- 1st attempt: 2s timeout -> Failure
+- 2nd attempt: 1.8s elapsed -> Success
+- Total time: 3.8s

Scenario 3: Original request plus all 3 retries fail
+- 1st attempt: 2s timeout -> Failure
+- 2nd attempt: 2s timeout -> Failure
+- 3rd attempt: 2s timeout -> Failure
+- 4th attempt: 2s timeout -> Failure
+- Total time: about 8s
```

**重试条件设置：**

```yaml
retries:
  attempts: 3
  perTryTimeout: 2s
  retryOn: 5xx,connect-failure,refused-stream  # Retry conditions
```

**最佳实践：**

```yaml
# Read requests: limited retry
- match:
  - method:
      regex: "^(GET|HEAD)$"
  retries:
    attempts: 2
    perTryTimeout: 2s
    retryOn: connect-failure,refused-stream

# Write requests: disable mesh retry
- match:
  - method:
      regex: "^(POST|PUT|PATCH|DELETE)$"
  retries:
    attempts: 0
```

**注意事项：**

* 为所有重试预留时间时，`timeout` 应大致大于 `(1 + attempts) x perTryTimeout`，并计入退避时间
* 重试过多可能导致级联故障
* `attempts: 0` 会禁用重试；`attempts: 1` 表示原始请求后最多再重放一次
* 默认应对 POST/PATCH 禁用网格重试，因为服务器可能已提交操作，只是响应丢失
* Workload mTLS 或网络加密不会让请求重放变得安全

**参考：**

* [超时和重试](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

## 简答题（6–10）

### 问题 6：Argo Rollouts + Istio Canary 部署

说明如何使用基于子集的 Canary rollout 和自动指标门控。请包括所需资源、创建顺序和中止条件。

<details>
<summary>显示答案</summary>

使用一个 Service、DestinationRule stable/canary 子集、VirtualService 路由、AnalysisTemplate 和完整的 Rollout。Argo 会更新路由权重和子集的 Pod 模板哈希；它不会创建预先引用的 Istio 资源。若与主机级集成，则使用独立的 stable/canary Service。命名路由必须与 Rollout 显式列出的路由相匹配；只有一个路由时，可以省略该列表。

使用全新的实验 namespace，并启用 sidecar 注入；还要使用兼容的 Argo Rollouts controller/CLI（本次审计的指南使用 v1.10.0）。将以下 Pod scrape relabeling 添加到 Prometheus，并确认 canary 流量带有 `rollout_hash` 和 `reporter="destination"` 标签。这些门控针对最新的 ReplicaSet 进行测量，而不是被 stable 与 canary 流量稀释的平均值。

```yaml
# Existing workload pod scrape job: relabel_configs fragment
- source_labels: [__meta_kubernetes_pod_label_rollouts_pod_template_hash]
  target_label: rollout_hash
```

先创建前置资源：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  ports:
  - port: 9080
    name: http
  selector:
    app: reviews
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destrule
  namespace: default
spec:
  host: reviews
  subsets:
  - name: stable
    labels:
      app: reviews
  - name: canary
    labels:
      app: reviews
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-vsvc
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - name: primary
    route:
    - destination:
        host: reviews
        subset: stable
      weight: 100
    - destination:
        host: reviews
        subset: canary
      weight: 0
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: default
spec:
  args:
  - name: service-name
  - name: pod-template-hash
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: len(result) == 1 && !isNaN(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: "sum(rate(\n  istio_requests_total{\n    destination_service_name=\"\
          {{args.service-name}}\",\n    reporter=\"destination\",\n    rollout_hash=\"\
          {{args.pod-template-hash}}\",\n    destination_workload_namespace=\"default\"\
          ,\n    response_code!~\"5.*\"\n  }[2m]\n))\n/\nsum(rate(\n  istio_requests_total{\n\
          \    destination_service_name=\"{{args.service-name}}\",\n    reporter=\"\
          destination\",\n    rollout_hash=\"{{args.pod-template-hash}}\",\n    destination_workload_namespace=\"\
          default\"\n  }[2m]\n))\n"
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency
  namespace: default
spec:
  args:
  - name: service-name
  - name: pod-template-hash
  metrics:
  - name: latency-p95
    interval: 30s
    count: 4
    successCondition: len(result) == 1 && !isNaN(result[0]) && result[0] <= 500
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: "histogram_quantile(0.95,\n  sum(rate(\n    istio_request_duration_milliseconds_bucket{\n\
          \      destination_service_name=\"{{args.service-name}}\",\n    reporter=\"\
          destination\",\n    rollout_hash=\"{{args.pod-template-hash}}\",\n     \
          \ destination_workload_namespace=\"default\"\n    }[2m]\n  )) by (le)\n\
          )\n"
```

然后创建 Rollout：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
  namespace: default
spec:
  replicas: 5
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: reviews
  template:
    metadata:
      labels:
        app: reviews
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: reviews
        image: docker.io/istio/examples-bookinfo-reviews-v2:1.20.3
        ports:
        - containerPort: 9080
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: reviews-vsvc
            routes:
            - primary
          destinationRule:
            name: reviews-destrule
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 25
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 50
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
      - setWeight: 75
      - pause:
          duration: 2m
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency
          args:
          - name: service-name
            value: reviews
          - name: pod-template-hash
            valueFrom:
              podTemplateHashValue: Latest
```

首次部署会建立 stable 版本；之后更新镜像以触发 canary 阶段。每个加权阶段都有有限时长的内联分析门控。failureLimit 为 0 时，一次测量失败就会中止当前 rollout；缺失/NaN 数据不能通过门控。门控成功后才会进入下一阶段。实际耗时取决于流量、抓取/分析间隔和控制器协调过程，不能保证只需几秒。

```bash
kubectl argo rollouts get rollout reviews --watch
kubectl get analysisruns
kubectl argo rollouts set image reviews reviews=istio/examples-bookinfo-reviews-v3:1.20.3
# Stop a failing active rollout; undo is a separate desired-template rollback
kubectl argo rollouts abort reviews
```

切换线上流量前，应等待配置传播并验证端点健康。不要让其他 controller 覆盖由 Argo 管理的权重/哈希。安装和执行前置条件见[完整 rollout 指南](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)。

</details>

***

### 问题 7：Blue/Green 与 Canary

比较流量迁移方式、资源需求、回滚方法和适用场景。

<details>
<summary>显示答案</summary>

| 方面 | Blue/Green | Canary |
| --- | --- | --- |
| 流量 | 先预览，然后切换活动 Service selector | 分阶段提高路由请求权重 |
| 验证 | 提升前后进行分析 | 随 rollout 推进进行内联/后台分析 |
| 容量 | 迁移期间通常需要两个完整版本；预览规模可不同 | 取决于副本数和扩缩策略；保留完整 stable 容量时可能接近两个版本 |
| 回滚 | 在旧版本/容量仍可用时切回 | 中止当前 rollout 并回到 stable；提升后按需撤销/重新部署 |
| 主要权衡 | 生产切换简单，但切换时影响面较大 | 每阶段暴露范围较小，但需要协调路由和分析 |

任何一种切换都不是网络层面的原子操作：端点/代理传播和现有连接都会产生影响。两者都不会撤销数据库迁移或外部副作用。在新旧版本共存期间，应保持 schema 和 API 合约兼容。Canary 权重不代表稳定的用户群组；A/B 测试需要显式的群组键。

Blue/Green 适合可充分预览且有足够临时容量的发布。Canary 适合在有代表性的流量和可信指标时逐步验证生产环境。不要仅凭“1 倍多一点”这样的假设选择 Canary；应检查其扩缩设置，包括可选的 dynamicStableScale。

```yaml
# Alternative strategy fragment for a complete Rollout
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: false
    scaleDownDelaySeconds: 600
    prePromotionAnalysis:
      templates:
      - templateName: smoke-tests
    postPromotionAnalysis:
      templates:
      - templateName: post-promotion-tests
```

使用前先创建 Service 以及带有所需参数的 AnalysisTemplate。保留时间应足以覆盖提升后的分析和回滚需求。混合式渐进流程需要专门设计；在 rollout 中途修改策略字段，不会自动将 Canary 转换成 Blue/Green。

[部署策略和示例](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)

</details>

***

### 问题 8：流量镜像（Shadow Testing）

说明如何使用流量镜像安全地测试新版本。请包括**使用场景**、**配置方法**和**注意事项**。

<details>

<summary>显示答案</summary>

**答案：**

**流量镜像概念：**

流量镜像会复制生产流量并将副本发送到新版本，同时**忽略新版本的响应**。这种方法也称为“影子测试”。

***

**1. 工作方式**

![Envoy proxy 会复制用户请求：主请求发送到生产版本 1，镜像请求发送到测试版本 2，测试版本的响应会被丢弃。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-traffic-management-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-traffic-management-0.html)

**主要特点：**

* 用户只会收到 v1 的响应
* v2 的响应会被 Envoy 丢弃
* v2 的响应不会返回给客户端，但共享资源竞争和写入副作用仍可能影响用户

***

**2. 配置方法**

**基础镜像（100%）：**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100  # Primary traffic
    mirror:
      host: reviews
      subset: v2  # Mirror target
    mirrorPercentage:
      value: 100  # 100% mirroring
```

**部分镜像（50%）：**

```yaml
spec:
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 100
    mirror:
      host: reviews
      subset: v2
    mirrorPercentage:
      value: 50  # Only 50% mirroring (reduce traffic load)
```

**镜像与 Canary 组合：**

```yaml
spec:
  http:
  - route:
    # Primary traffic: 90% v1, 10% v2
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10

    # Mirroring: Mirror all traffic to v3 (test)
    mirror:
      host: reviews
      subset: v3
    mirrorPercentage:
      value: 100
```

***

**3. 使用场景**

**场景 1：新版本性能测试**

```
Purpose: Verify if v2's performance is better than v1

1. Run v1 (production) + v2 (mirror) simultaneously
2. Monitor v2's latency, CPU, memory
3. If v2 is faster than v1 -> Proceed with Canary deployment
4. If v2 is slower than v1 -> Optimize and retest
```

**场景 2：数据库迁移验证**

```
Purpose: Verify new database schema

1. v1 -> Existing DB
2. v2 -> New DB (mirroring)
3. Verify v2's query performance and error rate
4. If no issues -> Switch to v2
```

**场景 3：Bug 修复验证**

```
Purpose: Verify that bug fix actually works

1. Run v1 (with bug) + v2 (fixed version, mirror)
2. Test v2 with production traffic
3. If v2's error rate decreases -> Deploy
```

**场景 4：缓存预热**

```
Purpose: Pre-populate new version's cache

1. Deploy v2, then warm its cache with mirror traffic before cutover
2. Once v2's cache is sufficiently populated
3. Warmup can reduce cache misses; it does not guarantee no cold start
```

***

**4. 监控配置**

**使用 Prometheus 查询监控镜像流量：**

```promql
# v2 (mirror) error rate
sum(rate(
  istio_requests_total{
    destination_version="v2",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{
    destination_version="v2"
  }[5m]
))

# v1 vs v2 latency comparison
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket[5m]
  )) by (destination_version, le)
)
```

**Grafana Dashboard：**

```yaml
# Panel 1: Error rate comparison (v1 vs v2)
# Panel 2: Latency comparison (P50, P95, P99)
# Panel 3: CPU/Memory usage
# Panel 4: Request count (v1: actual, v2: mirror)
```

***

**5. 注意事项**

**警告——负载增加：**

```
Mirroring increases service load.

Example:
- v1: 1000 RPS
- v2: 1000 RPS (mirror)
- Total load: 2000 RPS

Choose the percentage from shadow capacity and the test hypothesis; 50% is not a universal safe limit
```

**警告——留意副作用：**

```text
# Don't mirror write operations!

# Bad example
POST /api/orders  # Both v1 and v2 create orders -> Duplicates!

# Good example
GET /api/orders   # Mirror only read-only operations
```

**警告——成本：**

```
Mirroring increases resources and costs.

- 100% mirroring duplicates request volume on that route
- CPU, response traffic, and database cost depend on workload behavior

Solution: Mirror only for short periods (1-2 days)
```

**警告——无法验证响应：**

```
Mirror traffic responses are discarded, so
Istio does not compare response content. Application instrumentation or a dedicated shadow comparison system can validate correctness separately.

Can validate:
- Error rate
- Latency
- Resource usage

Cannot validate:
- Response/business correctness requires additional validation tooling
```

***

**6. 最佳实践**

```text
# Good examples
1. Mirror only read-only APIs
2. mirrorPercentage: 50% (reduce load)
3. Short-term testing (1-2 days)
4. Automatic validation based on metrics

# Bad examples
1. Mirroring write operations (duplicate data)
2. mirrorPercentage: 100% without capacity planning
3. Long-term mirroring (cost increase)
4. Manual validation (slow)
```

**参考：**

* [流量镜像](../../../service-mesh/istio/traffic-management/09-traffic-mirror.md)

</details>

***

### 问题 9：区域本地性与跨 AZ 成本

说明 EKS 上的本地性路由、故障转移所需条件，以及如何根据测得的流量估算节省。

<details>
<summary>显示答案</summary>

Istiod 会根据节点拓扑推导区域本地性；Pod 不会自动继承节点标签。检查 Node 以及代理端点的本地性信息：

```bash
kubectl get pods -o wide
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config endpoints <pod-name> -o json
```

加权分布示例如下：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-locality
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 20
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 80
            "us-east-1/us-east-1a/*": 20
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

远端的 20% 是实际承载流量，并非空闲的故障转移容量。显式设置 `failover` 是 `distribute` 的替代方案，其 from/to 值表示**区域**，例如从 us-east-1 切换到 us-west-2；它们不是“区域/可用区”的路径。可用区故障转移依赖端点本地性/健康状况。应在其他 AZ 中提供健康容量，并验证端点驱逐和 panic 行为。PDB 只限制自愿中断；它既不会创建副本，也无法阻止 AZ 故障。

**假设性计算，不是 AWS 报价**：假设每月有 200,000 GB 计费流量，跨 AZ 流量占比从 70% 降至 20%，测量路径的有效费率为每计费 GB 0.01 美元。

|  | 之前 | 之后 |
| --- | ---: | ---: |
| 跨 AZ 流量（GB） | 140,000 | 40,000 |
| 模型估算的月费用 | $1,400 | $400 |

模型估算每月节省 $1,000（71.4%），每年节省 $12,000。应使用实际计费路径费率、方向、负载均衡器/NAT/服务费用和测得的字节数；不要用服务数量的平方来推算流量。当前费率取决于区域以及具体服务/路径；同 AZ 流量也不一定免除所有处理费用。

`source_cluster`/`destination_cluster` 是集群 ID，不是 AZ。标准 Istio 指标不会自动提供所有源/目标 AZ 标签。应使用显式配置的拓扑遥测，或结合时点正确的端点/AZ 映射和计费数据分析 VPC Flow Logs。在受控流量下测量延迟；不能保证固定提升 30–60%。

- [AWS EC2 数据传输定价](https://aws.amazon.com/ec2/pricing/on-demand/)
- [VPC Flow Logs 字段](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)
- [区域本地性指南](../../../service-mesh/istio/traffic-management/06-load-balancing.md)

</details>

***

### 问题 10：Gateway TLS 配置

说明 Istio TLS 终止与 NLB 上的 ACM TLS 终止有何区别，并说明 HTTP 重定向和证书续期。

<details>
<summary>显示答案</summary>

应选择一种 TLS 终止设计。假定网关工作负载位于 istio-system，带有 istio=ingressgateway 标签，Service 端口匹配，并且已安装 AWS Load Balancer Controller。应通过负责该 Service 的安装工具合并变更。NLB 证书 ARN 和 Istio 的 credentialName 是不同对象。

**1. 在 Istio 终止 TLS**

在 NLB 上使用 TCP 透传。进行本地测试时，生成带 DNS SAN 的证书，并在客户端显式信任该证书。将示例主机名替换为你控制的域名：

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout bookinfo.key -out bookinfo.crt \
  -subj "/CN=bookinfo.example.com" \
  -addext "subjectAltName=DNS:bookinfo.example.com"
kubectl create secret tls bookinfo-secret -n istio-system \
  --key=bookinfo.key --cert=bookinfo.crt
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts: [bookinfo.example.com]
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts: [bookinfo.example.com]
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo-vs
  namespace: default
spec:
  hosts: [bookinfo.example.com]
  gateways: [istio-system/bookinfo-gateway]
  http:
  - route:
    - destination:
        host: productpage
        port:
          number: 9080
```

```bash
# INGRESS_HOST is the actual LB hostname; preserve the certificate hostname/SNI
curl --cacert bookinfo.crt \
  --connect-to "bookinfo.example.com:443:${INGRESS_HOST}:443" \
  https://bookinfo.example.com/productpage
curl -I --connect-to "bookinfo.example.com:80:${INGRESS_HOST}:80" \
  http://bookinfo.example.com/productpage
```

**2. 在 NLB 使用 ACM 终止 TLS**

使用 NLB 所在区域中状态为 ISSUED 且已通过 DNS 验证的 ACM 证书。仅请求证书并不能完成验证。NLB 是传输层负载均衡器，不会执行 HTTP 重定向；SSL 协商策略只选择 TLS 版本/密码套件。将解密后的 443 端口流量转发到一个与 HTTP 重定向监听器端口不同的网关目标端口，避免重定向循环：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/replace-with-issued-certificate
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
    service.beta.kubernetes.io/aws-load-balancer-ssl-negotiation-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
    app: istio-ingressgateway
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: https
    port: 443
    targetPort: 8081
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http-redirect
      protocol: HTTP
    hosts: [bookinfo.example.com]
    tls:
      httpsRedirect: true
  - port:
      number: 443
      name: http-after-nlb
      protocol: HTTP
    hosts: [bookinfo.example.com]
```

此替代方案会取代之前的 TLS Gateway，并使用相同的 VirtualService 绑定。本例中，NLB 到网关这一段为明文传输。如需加密该段，应配置单独的 TLS 后端设计，不要让 SIMPLE 与透传监听器不匹配。

**3. 在 Istio 配置客户端证书认证**

对于 Istio MUTUAL 监听器，应使用包含服务器凭证和受信任客户端 CA 的 Secret；不要同时使用 credentialName 和独立的 CA 文件路径：

```bash
kubectl create secret generic server-cert-secret -n istio-system \
  --from-file=tls.crt=server.crt --from-file=tls.key=server.key \
  --from-file=ca.crt=client-ca.crt
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: mutual-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-mutual
      protocol: HTTPS
    hosts: [secure.example.com]
    tls:
      mode: MUTUAL
      credentialName: server-cert-secret
      minProtocolVersion: TLSV1_2
```

```bash
curl --cacert server-ca.crt --cert client.crt --key client.key \
  https://secure.example.com/api
```

为该主机配置匹配的 VirtualService/DNS。诸如 *.example.com 的通配符 SAN 仅匹配一层最左侧标签（api.example.com），不匹配 example.com 或 x.api.example.com。应明确设置 SAN。cipherSuites 字段配置 TLS 1.3 之前版本的密码套件；它不会选择 TLS 1.3 密码套件。

**4. 证书续期**

cert-manager 1.21 支持 Kubernetes 1.33–1.36；安装或升级前应重新检查其发行版兼容矩阵。如果集群尚未由 cert-manager 管理，本次审计使用的版本为 v1.21.1：

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.21.1/cert-manager.yaml
```

配置状态为 Ready 且 challenge solver 符合实际 ingress/Gateway API/DNS 设置的 Issuer/ClusterIssuer。仅设置 ingress class 字符串并不能确保 ACME challenge 可访问。然后在网关工作负载 namespace 中创建 Certificate：

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: bookinfo-cert
  namespace: istio-system
spec:
  secretName: bookinfo-secret
  issuerRef:
    name: configured-issuer
    kind: ClusterIssuer
  dnsNames: [bookinfo.example.com]
```

```bash
kubectl wait --for=condition=Ready certificate/bookinfo-cert -n istio-system --timeout=120s
```

Istio 会监视生成的 Secret；续期由 cert-manager 执行。避免多个组件同时手动管理同一个 Secret。公网入口需要客户端信任的证书；上面的自签名示例用于实验室信任配置，内部 PKI 则需要谨慎规划信任分发和生命周期管理。

- [Istio 与 cert-manager 集成](https://istio.io/latest/docs/ops/integrations/certmanager/)
- [cert-manager 支持的发行版](https://cert-manager.io/docs/releases/)
- [AWS 集成示例](../../../service-mesh/istio/04-aws-integration.md)

</details>

***

## 评分计算

* 选择题 1–5：每题 10 分（共 50 分）
* 简答题 6–10：每题 10 分（共 50 分）
* **总分：100 分**

**评估标准：**

* 90–100 分：优秀（Istio 流量管理专家）
* 80–89 分：良好（具备生产运维能力）
* 70–79 分：一般（建议进一步学习）
* 60–69 分：低于平均水平（需要复习基础概念）
* 0–59 分：需要重新学习

## 学习资源

* [流量管理文档](../../../service-mesh/istio/traffic-management/README.md)
* [VirtualService](../../../service-mesh/istio/traffic-management/02-routing.md)
* [Gateway](../../../service-mesh/istio/traffic-management/01-gateway-virtualservice.md)
* [流量拆分](../../../service-mesh/istio/traffic-management/04-traffic-splitting.md)
* [Argo Rollouts](../../../service-mesh/istio/advanced/08-argo-rollouts.md)

* [主要参考资料 1](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
* [主要参考资料 2](https://istio.io/latest/docs/reference/config/networking/gateway/)
* [主要参考资料 3](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
* [主要参考资料 4](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/features/traffic-management/istio.md)
* [主要参考资料 5](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/analysis/prometheus.md)
* [主要参考资料 6](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.0/docs/features/bluegreen.md)
* [主要参考资料 7](https://aws.amazon.com/ec2/pricing/on-demand/)
* [主要参考资料 8](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)
* [主要参考资料 9](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
* [主要参考资料 10](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
* [主要参考资料 11](https://cert-manager.io/docs/releases/)
* [主要参考资料 12](https://istio.io/latest/docs/ops/integrations/certmanager/)
* [主要参考资料 13](https://cert-manager.io/docs/usage/certificate/)
* [主要参考资料 14](https://www.rfc-editor.org/rfc/rfc9525.html)
