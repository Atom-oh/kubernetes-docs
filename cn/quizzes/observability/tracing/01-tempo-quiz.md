# Grafana Tempo 测验

> **最后更新**: September 13, 2026

基准版本：Tempo 3.0.3 和 chart 3.6.0。

---

1. 下列哪项最准确地描述了 Tempo 存储和搜索？

   - A) 每个属性都必须在 Elasticsearch 中建立索引
   - B) 对象存储 Parquet 块支持 TraceID/TraceQL；存储和查询仍然会产生成本
   - C) 知道一个 ID 就能恢复每个被丢弃的 span
   - D) Tempo 会永久保留 traces

<details>
<summary>显示答案</summary>

**答案：B) 对象存储 Parquet 块支持 TraceID/TraceQL；存储和查询仍然会产生成本**

专用列、元数据和缓存并不意味着索引或查询成本为零。只有成功摄取并保留的数据才可用。

</details>

---

2. 在 Tempo 3 分布式写入路径提交到 Kafka 之前，哪个组件接收并验证 trace 数据？

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>显示答案</summary>

**答案：C) Distributor**

Distributor 写入 Kafka。Live-stores、block-builders 和可选的 metrics-generators 分别进行消费；这不是 Tempo 2 的 ingester 路径。

</details>

---

3. 哪个 TraceQL 查询会选择状态为 error 的 spans？

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>显示答案</summary>

**答案：B) `{ status = error }`**

Span 状态 error 不同于延迟阈值或任意 HTTP 响应条件。

</details>

---

4. 此 EKS/S3 示例使用了哪种身份配置？

   - A) Helm values 中的静态访问密钥
   - B) 每个工作负载共享的节点角色
   - C) 绑定到 monitoring:tempo、具有精确 OIDC sub/aud 和限定 S3 权限的 IRSA
   - D) 与任何 Pod 无关联的不相关 ServiceAccount

<details>
<summary>显示答案</summary>

**答案：C) 绑定到 monitoring:tempo、具有精确 OIDC sub/aud 和限定 S3 权限的 IRSA**

角色注解和每个 Tempo Pod ServiceAccount 必须保持一致。其他工作负载身份方法需要各自进行固定镜像兼容性检查。

</details>

---

5. 下列哪项不会由所示 metrics-generator processors 从 traces 生成？

   - A) Service graph metrics
   - B) Span metrics
   - C) 任意应用程序日志 metrics
   - D) 从 spans 派生的 rate/error/duration metrics

<details>
<summary>显示答案</summary>

**答案：C) 任意应用程序日志 metrics**

Span-metrics 和 service-graphs 需要显式启用 processor 并进行 remote write。它们不会将任意 logs 转换为 metrics。

</details>

---

6. 关于 Tempo 3 持久性的哪项陈述正确？

   - A) 三个 Tempo replicas 始终保证零丢失
   - B) Microservices 使用 Kafka；其复制、ISR、保留和恢复必须单独设计
   - C) Monolithic 模式始终需要 Kafka
   - D) 每个 StatefulSet 都会自动拥有持久性 PVC

<details>
<summary>显示答案</summary>

**答案：B) Microservices 使用 Kafka；其复制、ISR、保留和恢复必须单独设计**

该 chart 对 live-store/block-builder 数据使用 emptyDir。Kafka 持久性并非由 Tempo replica 数量决定；monolithic 模式不需要 Kafka。

</details>

---

7. 哪个 Grafana 关联方向正确？

   - A) 仅相同 namespace 就会创建关联
   - B) Tempo tracesToLogsV2 提供 Trace→Logs；Loki derivedFields 提供 Logs→Trace
   - C) 两个系统必须共享一个 S3 bucket
   - D) derivedFields 会使应用程序生成 TraceIDs

<details>
<summary>显示答案</summary>

**答案：B) Tempo tracesToLogsV2 提供 Trace→Logs；Loki derivedFields 提供 Logs→Trace**

标识符、数据源 UID、labels 和所查询的时间范围必须与真实数据匹配。链接无法恢复缺失的 telemetry。

</details>

---

8. 哪些组件负责 Tempo 3 后台 compaction 和 retention 工作？

   - A) Grafana 浏览器标签页
   - B) OTLP clients
   - C) Backend scheduler 和 backend workers
   - D) 原样复制的旧 compactor 配置

<details>
<summary>显示答案</summary>

**答案：C) Backend scheduler 和 backend workers**

它们取代了旧的 compactor 架构。Retention 是异步的，独立的全局 S3 expiration rule 可能会与 backend 操作冲突。

</details>

---

9. `{ resource.service.name = "A" } >> { resource.service.name = "B" }` 选择什么？

   - A) 不同 traces 中任意两个 spans
   - B) 与匹配 A spans 对应的匹配 B 后代
   - C) 仅 A 父级，绝不包括 B
   - D) 仅直接 B 子级

<details>
<summary>显示答案</summary>

**答案：B) 与匹配 A spans 对应的匹配 B 后代**

结果位于右侧。使用 > 表示直接子级。sibling 匹配和同一 trace 成员资格测试都不表示相同的含义。

</details>

---

10. 面对缓慢查询和看似为空的近期搜索，最安全的首要应对措施是什么？

   - A) 从 Tempo 2 复制 `ingester.max_block_duration: 30m`
   - B) 禁用所有 lag 和近期查询保护机制
   - C) 调优前检查时间范围、实际接收的数据、lag、扫描量和限制
   - D) 将缺失的 telemetry 和零流量变为有保证的健康值

<details>
<summary>显示答案</summary>

**答案：C) 调优前检查时间范围、实际接收的数据、lag、扫描量和限制**

Tempo 3 具有不同的组件和默认值。空结果、零流量和故障各不相同；仅渲染配置并不能证明生产系统能够正常运行。

</details>

---

[查看 Tempo 指南](../../../observability/tracing/01-tempo.md)。
