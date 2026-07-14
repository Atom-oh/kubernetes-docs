# Linkerd 可观测性测验

本测验用于测试您对 Linkerd 可观测性功能的理解。

## 测验题目

### 1. 以下哪项不是 Linkerd 自动收集的黄金指标？

A. 成功率
B. 请求率 (RPS)
C. 延迟
D. CPU 使用率

<details>
<summary>显示答案</summary>

**答案：D. CPU 使用率**

**说明：**
Linkerd 会自动收集三项黄金指标：成功率、请求率 (RPS) 和延迟 (p50、p95、p99)。CPU 使用率是 Kubernetes 指标，必须单独收集。

</details>

### 2. 以下哪项不包含在 `linkerd viz stat` 命令输出中？

A. SUCCESS（成功率）
B. RPS（请求率）
C. LATENCY_P99
D. ERROR_TYPE

<details>
<summary>显示答案</summary>

**答案：D. ERROR_TYPE**

**说明：**
`linkerd viz stat` 显示 MESHED、SUCCESS、RPS、LATENCY_P50/P95/P99。必须通过 `linkerd viz tap` 或日志检查错误类型。

</details>

### 3. `linkerd viz tap` 命令的用途是什么？

A. 捕获网络数据包
B. 查看实时请求流
C. 更改代理配置
D. 更新证书

<details>
<summary>显示答案</summary>

**答案：B. 查看实时请求流**

**说明：**
`linkerd viz tap` 实时流式传输请求。它会显示请求方法、路径、状态码、延迟、mTLS 状态等。

</details>

### 4. 定义 ServiceProfile 后可以获得哪些额外指标？

A. Pod 资源使用率
B. 每路由指标
C. 网络带宽
D. 磁盘 I/O

<details>
<summary>显示答案</summary>

**答案：B. 每路由指标**

**说明：**
定义 ServiceProfile 可收集每路由（例如 GET /api/users、POST /api/orders）的成功率、请求率和延迟指标。可通过 `linkerd viz routes` 命令查看。

</details>

### 5. 访问 Viz 扩展的 Prometheus 的默认方法是什么？

A. NodePort Service
B. LoadBalancer Service
C. kubectl port-forward
D. 公共 URL

<details>
<summary>显示答案</summary>

**答案：C. kubectl port-forward**

**说明：**
Viz 的 Prometheus 被部署为 ClusterIP Service。可通过 `kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090` 访问。出于安全考虑，不建议对外暴露。

</details>

### 6. 以下哪个 header 不是分布式追踪传播所必需的？

A. x-b3-traceid
B. x-request-id
C. x-linkerd-proxy
D. x-b3-spanid

<details>
<summary>显示答案</summary>

**答案：C. x-linkerd-proxy**

**说明：**
分布式追踪所需的 header 包括：x-request-id、x-b3-traceid、x-b3-spanid、x-b3-parentspanid、x-b3-sampled、b3 等。x-linkerd-proxy 不存在。

</details>

### 7. `linkerd viz top` 命令显示什么？

A. 使用最多资源的 Pod
B. 最活跃的请求路径
C. 最常见的错误消息
D. 最新日志条目

<details>
<summary>显示答案</summary>

**答案：B. 最活跃的请求路径**

**说明：**
`linkerd viz top` 实时显示最活跃的请求路径。它会显示 Source、Destination、Method、Path、Count、Latency、Success Rate 等。

</details>

### 8. 哪个 annotation 用于设置代理日志级别？

A. config.linkerd.io/log-level
B. config.linkerd.io/proxy-log-level
C. linkerd.io/proxy-log
D. proxy.linkerd.io/log-level

<details>
<summary>显示答案</summary>

**答案：B. config.linkerd.io/proxy-log-level**

**说明：**
`config.linkerd.io/proxy-log-level` annotation 用于设置代理日志级别。示例："warn,linkerd=info,linkerd_proxy=debug"

</details>

### 9. 用于计算 Linkerd 成功率的正确 Prometheus 查询是什么？

A. `sum(response_total{classification="success"}) / sum(response_total)`
B. `rate(success_total[5m]) / rate(request_total[5m])`
C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`
D. `avg(success_rate)`

<details>
<summary>显示答案</summary>

**答案：C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`**

**说明：**
成功率通过将成功响应率除以总响应率来计算。rate() 函数计算时间范围内每秒的速率，sum() 函数进行聚合。

</details>

### 10. Jaeger 扩展的主要功能是什么？

A. 指标收集
B. 日志聚合
C. 分布式追踪
D. 流量拆分

<details>
<summary>显示答案</summary>

**答案：C. 分布式追踪**

**说明：**
Jaeger 扩展提供分布式追踪。它可视化请求经过多个 Service 的完整路径，并分析每个步骤的延迟。

</details>

### 11. linkerd viz dashboard 命令不提供以下哪个视图？

A. Topology
B. Deployments
C. Pod Logs
D. Routes

<details>
<summary>显示答案</summary>

**答案：C. Pod Logs**

**说明：**
Viz dashboard 提供 Namespace、Deployments、Pods、TCP、Routes、Topology 和 Tap 视图。必须通过 kubectl logs 或单独的日志系统检查 Pod 日志。

</details>

### 12. 与外部 Grafana 集成时，使用哪个 Viz 安装选项？

A. `--set grafana.external=true`
B. `--set grafana.enabled=false`
C. `--set grafana.url=external`
D. `--set monitoring=external`

<details>
<summary>显示答案</summary>

**答案：B. `--set grafana.enabled=false`**

**说明：**
使用外部 Grafana 时，请禁用 Viz 的内置 Grafana。使用 `helm install linkerd-viz linkerd/linkerd-viz --set grafana.enabled=false`，或在 values 文件中配置。

</details>
