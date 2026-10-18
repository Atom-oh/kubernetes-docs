# 可观测性堆栈测验

> **相关文档**：[可观测性堆栈](../../ops/09-observability-stack.md)

## 1. 哪项说法应指导新的 Loki 部署？

- A. SimpleScalable 永远是所有新部署的默认选项
- B. SimpleScalable 已弃用，并计划在 4.0 中移除；应评估替代方案
- C. Monolithic 模式无法使用对象存储
- D. 三个副本会自动保证可用区隔离

<details>
<summary>显示答案</summary>

**答案：B**

Read/write/backend 拆分描述的是 SSD（Simple Scalable Deployment）架构。新设计还必须评估其生命周期，以及 Monolithic 和 Distributed 模式的容量与运维限制。

</details>

## 2. Tempo 3 的分布式模式与单体模式有什么区别？

- A. 两者都会保留旧版 ingester
- B. Monolithic 模式始终需要 Kafka
- C. Distributed 模式使用 Kafka；Monolithic 模式可以不使用 Kafka
- D. 增加 Monolithic chart 副本即可获得受支持的分布式高可用

<details>
<summary>显示答案</summary>

**答案：C**

版本 3 使用 block-builders/live-stores 和 backend-scheduler/workers，取代分布式 ingester/compactor 架构。不要混用其部署模式。

</details>

## 3. 尾部采样有哪些限制？

- A. 它总能保留每条错误 trace
- B. 它依据 decision_wait 期间收到的 span 作出决定，无法恢复头部采样已丢弃的数据
- C. 随机 Service 负载均衡总能让一条 trace 固定经过同一个 sampler
- D. num_traces 表示每秒 trace 速率

<details>
<summary>显示答案</summary>

**答案：B**

延迟到达的 span、缓冲区限制、重启和传输故障都会产生影响。使用多个 sampler 时，需要根据 trace ID 进行路由。

</details>

## 4. batch processor 的 send_batch_size 控制什么？

- A. 批次大小的上限
- B. trace 的最长持续时间
- C. 触发发送的项目数
- D. 持久存储容量

<details>
<summary>显示答案</summary>

**答案：C**

send_batch_max_size 才是批次大小上限。应将批处理放在内存限制和采样/丢弃处理之后。

</details>

## 5. 如果 Alloy DaemonSet 的每个 Pod 都收集集群中的所有日志目标，会发生什么？

- A. 自动实现完美的高可用去重
- B. 采集可能重复；应分配目标或配置 source clustering
- C. Kubernetes API 会自动确保只有一个采集器
- D. 因为总是需要 hostPath，所以它无法启动

<details>
<summary>显示答案</summary>

**答案：B**

Kubernetes logs API source 与读取日志文件的方式不同。单个 Deployment/Recreate 示例可以减少重复，但无法提供高可用或不中断的采集。

</details>

## 6. Loki 保留策略需要哪些设置？

- A. 仅设置 retention_period
- B. 24 小时 TSDB 索引、启用 Compactor 保留策略、delete_request_store 和保留时长
- C. 将存储桶中的每个对象都设为同一时间过期
- D. Grafana 仪表板的时间范围

<details>
<summary>显示答案</summary>

**答案：B**

删除会延迟并异步执行，Compactor 状态和标记必须能在重启后保留。存储桶级生命周期过期可能会误删索引等必需对象。

</details>

## 7. 哪些标签用于标识 AMP 高可用组及其副本？

- A. namespace 和 pod
- B. cluster 和 __replica__
- C. service 和 trace_id
- D. 仅 region

<details>
<summary>显示答案</summary>

**答案：B**

同一抓取数据的副本共享 cluster 值，并使用不同的 __replica__ 值。将彼此独立的抓取覆盖范围归入同一个高可用组可能导致数据丢失。

</details>

## 8. 关于 AMP 保留时长，哪项说法正确？

- A. 150 天是不可更改的上限
- B. 每个 workspace 都可以配置，最长为 1,095 天
- C. 保留时长始终无限
- D. 延长保留时长会恢复已删除的指标

<details>
<summary>显示答案</summary>

**答案：B**

应根据需求、成本和服务限制设置保留时长。过期数据不会因此恢复。

</details>

## 9. 在 Grafana 中将 Loki 日志链接到 Tempo trace，需要什么？

- A. 同时安装两者就会自动建立链接
- B. 正确提取 trace ID，显式配置数据源 UID，并确保 trace 数据可访问
- C. 将 trace ID 加为普通 Prometheus 标签
- D. 只启用 HTTP/2

<details>
<summary>显示答案</summary>

**答案：B**

请匹配 derivedFields/tracesToLogsV2 映射、时间范围、租户和权限。Exemplar 还需要相应的插桩、OpenMetrics 和存储配置。

</details>

## 10. chart 渲染成功后还必须检查什么？

- A. 不必检查；所有未知值都会应用
- B. 实际 PVC、Service、身份、后端配置以及写入/查询路径
- C. 只需检查 YAML 缩进
- D. 将每个镜像都替换为 latest

<details>
<summary>显示答案</summary>

**答案：B**

某些 chart 值可能会被静默忽略。检查 PVC 的 claim 和 accessModes、Service 端口，并区分原生解析器校验与实际环境连通性。

</details>
