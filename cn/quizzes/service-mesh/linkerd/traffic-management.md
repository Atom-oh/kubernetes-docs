# Linkerd 流量管理测验

本测验用于检验你对 Linkerd 流量管理的理解。

## 测验题目

### 1. 在 ServiceProfile 中，无法按路由配置的是什么？

A. 超时
B. 可重试性
C. 负载均衡算法
D. 路径条件

<details>
<summary>显示答案</summary>

**答案：C. 负载均衡算法**

**说明：**
ServiceProfile 可以按路由配置超时、可重试性（isRetryable）和路径条件（method、pathRegex）。负载均衡算法是 Linkerd 的全局设置，使用 EWMA。

</details>

### 2. Linkerd 使用什么负载均衡算法？

A. 轮询
B. 最少连接数
C. EWMA（指数加权移动平均）
D. 随机

<details>
<summary>显示答案</summary>

**答案：C. EWMA（指数加权移动平均）**

**说明：**
Linkerd 使用 EWMA 算法，优先选择响应延迟更快的 endpoint。它会实时适应 endpoint 状态，并自动减少发往缓慢 endpoint 的流量。

</details>

### 3. TrafficSplit 遵循什么标准规范？

A. CNCF
B. SMI（Service Mesh Interface）
C. OpenAPI
D. gRPC

<details>
<summary>显示答案</summary>

**答案：B. SMI（Service Mesh Interface）**

**说明：**
TrafficSplit 是遵循 SMI（Service Mesh Interface）标准的 CRD。SMI 定义了 Service Mesh 的通用接口，以便在不同 mesh 实现之间提供兼容性。

</details>

### 4. retryBudget 的 retryRatio 为 0.2 表示什么？

A. 所有请求中只有 20% 会被重试
B. 失败请求中只有 20% 会被重试
C. 相对于原始请求，最多允许额外进行 20% 的重试
D. 重试预算每 20 秒重置一次

<details>
<summary>显示答案</summary>

**答案：C. 相对于原始请求，最多允许额外进行 20% 的重试**

**说明：**
retryRatio 为 0.2 时，相对于原始请求数量，最多允许额外进行 20% 的重试。例如：对于 100 个请求，最多允许额外重试 20 次。这可以防止重试导致过载。

</details>

### 5. 以下哪项不是自动生成 ServiceProfile 的方法？

A. 从 OpenAPI/Swagger 规范生成
B. 从实时流量 tap 生成
C. 从 Protobuf 定义生成
D. 从 Kubernetes Service 自动生成

<details>
<summary>显示答案</summary>

**答案：D. 从 Kubernetes Service 自动生成**

**说明：**
ServiceProfile 可以使用 `linkerd profile --open-api`、`linkerd viz profile --tap` 和 `linkerd profile --proto` 命令生成。它们不会从 Kubernetes Service 自动生成，必须显式定义。

</details>

### 6. 对于 canary Deployment，TrafficSplit backend 权重之和应是多少？

A. 必须恰好为 100
B. 必须恰好为 1
C. 任何值都可以（按比例计算）
D. 必须恰好为 1000

<details>
<summary>显示答案</summary>

**答案：C. 任何值都可以（按比例计算）**

**说明：**
TrafficSplit 权重按相对比例计算。weight: 90 和 weight: 10 等同于 weight: 9 和 weight: 1。总和不必为 100。

</details>

### 7. HTTPRoute（Gateway API）不支持以下哪种路由条件？

A. 基于 Header 的路由
B. 基于路径的路由
C. 基于 Cookie 的路由
D. 基于源 IP 的路由

<details>
<summary>显示答案</summary>

**答案：D. 基于源 IP 的路由**

**说明：**
HTTPRoute 支持基于 Header、路径、方法和 Cookie（通过 Header）的路由。基于源 IP 的路由不属于 L7 路由的范围，应由 NetworkPolicy 或其他机制处理。

</details>

### 8. 将 Flagger 与 Linkerd 集成时使用哪个 metrics server？

A. Metrics Server
B. Prometheus
C. InfluxDB
D. Datadog

<details>
<summary>显示答案</summary>

**答案：B. Prometheus**

**说明：**
Flagger 从 Linkerd Viz 的 Prometheus 获取指标（成功率、延迟等），用于 canary 分析。安装 Flagger 时，使用 `--set metricsServer=http://prometheus.linkerd-viz:9090` 进行连接。

</details>

### 9. 当 ServiceProfile 的 isRetryable 在某条路由上为 false 时，会发生什么？

A. 所有请求都会失败
B. 不会进行重试
C. 超时会被忽略
D. 路由被禁用

<details>
<summary>显示答案</summary>

**答案：B. 不会进行重试**

**说明：**
isRetryable: false 表示该路由上的请求即使失败也不会被重试。这适用于 POST 请求等非幂等操作。请求本身仍会正常处理。

</details>

### 10. Linkerd 如何实现 Circuit Breaker 模式？

A. Circuit Breaker CRD
B. Failure Accrual
C. Rate Limiter
D. Timeout Policy

<details>
<summary>显示答案</summary>

**答案：B. Failure Accrual**

**说明：**
Linkerd 通过 failure accrual 实现 Circuit Breaker 模式。发生连续失败时，它会暂时排除该 endpoint，使用指数退避进行重试，并在成功后恢复正常状态。

</details>

### 11. 如何在不进行流量拆分的情况下将流量发送到 mirror Service？

A. 使用 TrafficMirror CRD
B. 直接调用 mirror Service DNS
C. 所有流量都会自动镜像
D. Linkerd 不支持流量镜像

<details>
<summary>显示答案</summary>

**答案：B. 直接调用 mirror Service DNS**

**说明：**
Linkerd 本身不具备 Istio 那样的流量镜像功能。多集群 mirror Service（例如 web-west）必须通过 DNS 直接调用，或使用 TrafficSplit 权重进行配置。

</details>

### 12. 当 ServiceProfile 的某条路由未设置 timeout 时，会发生什么？

A. 应用默认的 5 秒超时
B. 无超时（无限制）
C. 请求立即失败
D. 应用全局超时

<details>
<summary>显示答案</summary>

**答案：B. 无超时（无限制）**

**说明：**
未在 ServiceProfile 中指定 timeout 的路由会无限期等待，不会超时。这适用于流式或长时间运行的操作，但通常建议显式设置超时。

</details>
