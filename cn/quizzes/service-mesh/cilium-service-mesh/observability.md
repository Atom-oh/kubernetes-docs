# Cilium Service Mesh 可观测性测验

已根据 Cilium 1.20.3/Hubble CLI 1.20.2 进行核对。有关经过测试的命令、指标定义和限制，请参阅[可观测性指南](../../../service-mesh/cilium-service-mesh/04-observability.md)。

### 1. 以下哪一项不是 Hubble 的主要组件？

- **A.** Hubble Observer
- **B.** Hubble Relay
- **C.** Hubble Router
- **D.** Hubble UI

<details>
<summary>显示答案</summary>

**答案：C. Hubble Router**

Observer、Relay、UI 和 CLI 是相关的 Hubble 组件。Observer 和指标处理内嵌于 Cilium 中；Relay 则聚合已连接的服务器。Hubble Router 并非此架构中的命名组件。

</details>

### 2. 在 Hubble CLI 中，哪个命令可以筛选并仅观察 HTTP 流量？

- **A.** hubble observe --type http
- **B.** hubble observe --protocol http
- **C.** hubble observe --filter http
- **D.** hubble observe --layer http

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --protocol http**

此命令会筛选已有的 HTTP 观测数据。它不会启用 L7 检查，也不会解密任意 TLS。必须已有受支持的 L7 策略/代理路径和能够提供观测数据的流量。

</details>

### 3. 要在 Prometheus 中收集 Hubble 指标，需要在 values.yaml 中启用哪个设置？

- **A.** hubble.prometheus.enabled: true
- **B.** hubble.metrics.enabled
- **C.** hubble.export.prometheus: true
- **D.** prometheus.hubble: true

<details>
<summary>显示答案</summary>

**答案：B. hubble.metrics.enabled**

hubble.metrics.enabled 用于选择 dns 和 httpV2 等处理器。Prometheus 收集还需要可正常工作的发现/抓取机制；使用 ServiceMonitor 时，需要 Operator CRD/控制器以及匹配的选择器。创建了 ServiceMonitor 并不能证明目标已被抓取。

</details>

### 4. 以下哪一项不属于监控的四个黄金信号？

- **A.** 延迟
- **B.** 流量
- **C.** 可用性
- **D.** 饱和度

<details>
<summary>显示答案</summary>

**答案：C. 可用性**

四个信号分别是延迟、流量、错误和饱和度。可用性仍然需要明确的 SLI，且无法仅根据不完整的 HTTP5xx 观测流全面推断。

</details>

### 5. 哪个命令可以先筛选出丢弃的流，以便进一步分析原因？

- **A.** hubble observe --denied
- **B.** hubble observe --verdict DROPPED
- **C.** hubble observe --blocked
- **D.** hubble observe --policy-denied

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

DROPPED 包含多种原因。添加 --drop-reason-desc POLICY_DENIED 可筛选报告为策略拒绝的丢弃流；L7/应用层故障则需单独检查。FORWARDED 是数据路径观测结果，并不能证明业务成功。

</details>

### 6. 在 PromQL 查询中，使用哪个函数来衡量 HTTP P99 延迟？

- **A.** avg()
- **B.** histogram_quantile()
- **C.** rate()
- **D.** sum()

<details>
<summary>显示答案</summary>

**答案：B. histogram_quantile()**

histogram_quantile 根据直方图计算估算值。要聚合工作负载，请在保留 le 和选定的集群/命名空间/工作负载标签的同时，对兼容的桶速率求和，然后计算分位数。对各实例的百分位数求平均并不等同于此操作。

</details>

### 7. 以下哪一项不是 Hubble UI 提供的主要功能？

- **A.** 服务映射
- **B.** 流时间线
- **C.** 自动扩缩容
- **D.** 命名空间筛选器

<details>
<summary>显示答案</summary>

**答案：C. 自动扩缩容**

UI 会显示观测到的关系和流量详情，并提供筛选器；它不会自动扩缩工作负载。静默或不受支持的路径以及缺失的元数据，都可能导致映射不完整。

</details>

### 8. 使用 httpV2 时，应如何计算观测到的 HTTP5xx 百分比？

- **A.** 将生命周期内的错误计数器除以请求计数器，不使用速率
- **B.** 将匹配的 5xx 响应速率除以观测到的总速率，并对缺失值/零值进行范围限定的处理
- **C.** 统计指标序列的数量
- **D.** 读取自动提供的 hubble_http_error_rate gauge

<details>
<summary>显示答案</summary>

**答案：B. 将匹配的 5xx 响应速率除以观测到的总速率，并对缺失值/零值进行范围限定的处理**

使用 httpV2 时，hubble_http_requests_total 包含状态码，并根据响应事件更新。分子和分母应使用相同的分组/观测范围。仅当总数存在时，才将缺失的 5xx 分子补为零；对于缺少观测数据的情况，保留无数据状态；计算百分比时排除总数为零的情况。

</details>

### 9. 在 Hubble 中，使用哪个选项可以仅观察目标为特定 Service 的流量？

- **A.** --destination-service
- **B.** --to-service
- **C.** --target-service
- **D.** --svc

<details>
<summary>显示答案</summary>

**答案：B. --to-service**

Service 筛选器使用带命名空间的名称前缀以及基于 Service/ClusterIP 的元数据。--from-service 通常不会筛选出由该 Service 后方的 Pod 发起的调用；筛选调用方时，请使用工作负载/Pod/标签筛选器。未指定命名空间时，默认使用 default。

</details>

### 10. 哪个已记录的指标会报告已插桩 BPF 映射的压力？

- **A.** cilium_ct_usage
- **B.** cilium_bpf_map_pressure
- **C.** cilium_connections_total
- **D.** cilium_datapath_conntrack_active / cilium_datapath_conntrack_max

<details>
<summary>显示答案</summary>

**答案：B. cilium_bpf_map_pressure**

cilium_bpf_map_pressure 会报告已插桩 BPF 映射的压力；部分映射还设有报告阈值。但这并不能证明所有 CT 映射都包含在内。已记录的 CT GC 条目指标是垃圾回收时的快照，并非先前臆造的 active/max 指标对。

</details>

### 11. 要以 JSON 格式接收 Hubble 输出，应使用哪个选项？

- **A.** --format json
- **B.** -o json
- **C.** --json
- **D.** --output-type json

<details>
<summary>显示答案</summary>

**答案：B. -o json**

json 是 jsonpb 的别名。Protobuf JSON 会将 latency_ns 等 64 位值编码为字符串；在 jq 中进行数值比较之前，请先将其转换为数字。dict、compact 和 table 也是受支持的显示格式。

</details>

### 12. 使用 OpenTelemetry Collector 收集 Hubble 流日志的受支持路径是什么？

- **A.** 在 chart 中启用 hubble.export.opentelemetry
- **B.** 使用 Hubble 文件导出和 filelog receiver，然后使用受支持的日志导出器
- **C.** 自动将每条流转换为分布式追踪
- **D.** 使用已移除的 jaeger exporter 导入流日志

<details>
<summary>显示答案</summary>

**答案：B. 使用 Hubble 文件导出和 filelog receiver，然后使用受支持的日志导出器**

Cilium 1.20.3 记录了用于流日志的文件导出方式。filelog receiver 可以收集这些文件，并通过受支持的导出器（例如 OTLP/HTTP）将日志发送到 Loki。指标和应用追踪使用各自的收集路径；旧版 Hubble opentelemetry 配置项以及已移除的 Collector jaeger/loki 导出器并不能作为替代方案。

</details>
