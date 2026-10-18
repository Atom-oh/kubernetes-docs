# Grafana Mimir 测验

基线：Mimir 3.2.1 / chart 6.2.0。请复核当前架构、身份验证、存储和验证限制。

## 1. 生产环境中的 Mimir 块存储应使用什么后端？

- A. 仅本地 SSD
- B. 对象存储，例如 S3、GCS、Azure Blob 或 Swift
- C. 仅 NFS
- D. 仅内存缓存

<details>
<summary>显示答案</summary>

**答案：B. 对象存储，例如 S3、GCS、Azure Blob 或 Swift**

生产部署应使用适当的外部对象存储。Filesystem 后端可用于本地开发，但这不意味着它是共享的生产对象存储。Ingester 的本地 TSDB/WAL 和 Kafka 存储有各自独立的持久化与恢复要求。

</details>

## 2. 在 ingest-storage 架构中，Distributor 的作用是什么？

- A. 自行存储所有长期块
- B. 验证写入并将记录追加到 Kafka
- C. 从结果缓存返回所有查询
- D. 压缩 TSDB 块

<details>
<summary>显示答案</summary>

**答案：B. 验证写入并将记录追加到 Kafka**

Distributor 会验证并限制写入，然后将其分片到 Kafka 分区。写入确认取决于配置的持久性条件下 Kafka 是否成功写入；它不会等待块上传到 S3。直接写入 Ingester 仲裁描述的是经典架构。

</details>

## 3. 对不可信调用方，应如何安全地选择租户？

- A. 允许客户端自行选择任意 X-Scope-OrgID 值
- B. 由可信网关进行身份验证和授权，并由网关设置租户标头
- C. 只使用对象键前缀
- D. 将命名空间名称视为自动生效的 HTTP 身份验证

<details>
<summary>显示答案</summary>

**答案：B. 由可信网关进行身份验证和授权，并由网关设置租户标头**

X-Scope-OrgID 用于标识租户，本身不是凭证。可信网关必须替换不可信标头，并强制执行调用方与租户之间的映射。只有在代理实现了相应策略时，Basic Auth 用户名才会映射到租户。还必须限制对后端的绕过访问。

</details>

## 4. Ingester 为什么要将 TSDB 块上传到对象存储？

- A. 为了避免所有本地持久化
- B. 为了提供长期块存储和块查询访问
- C. 为了备份 Grafana 仪表板
- D. 为了保证每个已确认样本都能在任何故障下存活

<details>
<summary>显示答案</summary>

**答案：B. 为了提供长期块存储和块查询访问**

Ingester 会维护本地 TSDB/WAL，并定期上传块。本地保留时间与数据移交给 Store-gateway 的阶段会有重叠。Kafka 确认、Ingester 消费和对象上传是不同阶段；恢复能力仍取决于持久化、保留策略和故障条件。

</details>

## 5. Compactor 负责哪些工作？

- A. 抓取每个应用端点
- B. 合并块、去重副本样本并执行保留清理
- C. 验证所有租户的身份
- D. 自动对所有原始序列降采样，使用 downsampling_enabled

<details>
<summary>显示答案</summary>

**答案：B. 合并块、去重副本样本并执行保留清理**

Compactor 会合并块，并移除副本产生的重复样本。保留清理是异步进行的。虚构的 compactor.downsampling_enabled 选项无效；记录规则可以生成派生序列，但不会自动删除原始数据。

</details>

## 6. 哪项不属于 Query-frontend 的职责？

- A. 拆分并分片其支持的查询
- B. 使用查询结果缓存
- C. 持久化权威的长期 TSDB 块
- D. 合并查询响应

<details>
<summary>显示答案</summary>

**答案：C. 持久化权威的长期 TSDB 块**

Frontend 会规划和缓存工作，并返回合并后的响应。Scheduler 会对工作排队，Querier 会获取所需数据。命中元数据或 chunk 缓存并不代表完整查询答案已经得到。步长对齐可能改变请求的时间戳，并影响 PromQL 一致性。

</details>

## 7. 与 VictoriaMetrics 的比较中，哪项说法准确？

- A. Mimir 从不提供 filesystem 后端
- B. 使用 Grafana 就意味着 Mimir 在任何情况下都更快
- C. 应比较存储架构、查询语义、租户强制策略、恢复能力和实测成本
- D. VictoriaMetrics 无法支持租户

<details>
<summary>显示答案</summary>

**答案：C. 应比较存储架构、查询语义、租户强制策略、恢复能力和实测成本**

两种产品都需要身份验证/授权边界。Mimir 的生产块存储与经审查的 VictoriaMetrics 本地存储架构具有不同的运维要求。未经支持的压缩排名和对生态系统的偏好，都不能证明哪种方案在性能或成本上胜出。

</details>

## 8. Store-gateway 提供什么能力？

- A. 收集应用指标
- B. 借助对象存储、索引头和已配置缓存来访问块查询
- C. 自动验证租户身份
- D. 复制 Kafka broker

<details>
<summary>显示答案</summary>

**答案：B. 借助对象存储、索引头和已配置缓存来访问块查询**

Querier 会从 Store-gateway 请求块数据，并从 Ingester 获取近期数据；块交接期间，两个数据范围可能重叠。复用缓存或索引元数据可以避免部分工作，但这不表示每个查询都无需读取 chunk 即可完成。

</details>

## 9. compactor_blocks_retention_period 控制什么？

- A. 仅控制内存缓存过期时间
- B. Compactor 使用的长期块保留策略
- C. Kafka topic 的保留时间
- D. 精确的物理删除/合规截止时间

<details>
<summary>显示答案</summary>

**答案：B. Compactor 使用的长期块保留策略**

块的时间范围、扫描、删除标记和 deletion_delay 都会影响实际删除时间。本地 TSDB 保留和 Kafka 保留彼此独立。S3 版本控制、Object Lock 和备份也会影响数据能否彻底删除；单独设置 365d 并不能保证满足监管要求。

</details>

## 10. 哪项不是可靠的可用性假设？

- A. 单独验证 Kafka 的持久性和恢复能力
- B. 确保 zone 选择器与实际可调度节点相匹配
- C. 将所有组件放在一个 AZ 并声称能够容忍可用区故障
- D. 检查 Ingester 分区覆盖、Store-gateway 副本数和发布依赖

<details>
<summary>显示答案</summary>

**答案：C. 将所有组件放在一个 AZ 并声称能够容忍可用区故障**

逻辑 zone 不等同于物理部署位置。示例会在三个选定的 zone 中渲染三个 Ingester/Store-gateway；但 broker 拓扑、PVC、容量、队列、发布和其他组件仍需验证。缓存冗余和单个 Compactor 都不能证明端到端高可用。

</details>

[返回章节](../../../observability/metrics/03-mimir.md)
