# 状态、检查点与流处理模式测验

区分本章中 Flink/Kafka 和 Flink/Iceberg 的版本组合。

1. 选择 RocksDB 就能免去对堆、GC 和内存规划的考虑吗？

<details>
<summary>显示答案</summary>

**答案**：不能。原生缓存、受管理内存、用户对象、算子状态和缓冲区仍然会消耗资源。

**说明**：按键算子的后端可以共享任务槽（slot）的内存预算。应测量实际工作负载/状态以及检查点/恢复情况，而不要采用固定的 MB 阈值。

</details>

2. 在 Flink 2.2 中，增量快照是否仅适用于 RocksDB？

<details>
<summary>显示答案</summary>

**答案**：不是。实验性的 ForSt 也使用异步增量快照。

**说明**：应检查其远程 SST/本地缓存模型以及 API/快照限制。本章的配置示例使用 RocksDB。

</details>

3. 增量检查点的上传量是否只取决于逻辑键的变更？

<details>
<summary>显示答案</summary>

**答案**：不是。它会持久化新的 SST/元数据，而数据压实（compaction）可能会重写大型文件。

**说明**：可复用的共享 SST 会被引用。如果过期清理了仍被引用的文件，就可能导致恢复失败。

</details>

4. 增量恢复是否会按顺序重放所有较早的检查点？

<details>
<summary>显示答案</summary>

**答案**：不会。恢复时会加载所选检查点引用的文件。

**说明**：完整检查点不一定是单个文件。恢复情况取决于网络、文件数量、I/O 和规范状态重建成本。

</details>

5. 保存点是否一定会永久保留，直到有人手动删除？

<details>
<summary>显示答案</summary>

**答案**：不是。Operator 的保留/处置策略以及 CLAIM/NO_CLAIM 所有权都会影响其生命周期。

**说明**：检查点也可以配置显式触发和外部化保留。应检查存储、引用关系和删除责任。

</details>

6. Operator 的 last-state 是否总是使用单个最后检查点文件？

<details>
<summary>显示答案</summary>

**答案**：恢复依赖于可访问的 HA 元数据，或最后的检查点/保存点及适用路径。

**说明**：还需要有效的元数据、状态兼容性、UID 和序列化器；仅凭标签不能保证恢复成功或迁移安全。

</details>

7. Kafka EXACTLY_ONCE 需要检查点和消费者满足哪些条件？

<details>
<summary>显示答案</summary>

**答案**：事务提交要与检查点完成协调，下游消费者必须使用 read_committed。

**说明**：还需要可重放的数据源和可恢复的状态。不同的数据接收端（sink）/所有子任务并不会自动构成一个全局事务。

</details>

8. transactionalIdPrefix 何时应当唯一，何时应保持稳定？

<details>
<summary>显示答案</summary>

**答案**：不同的并发数据接收端（sink）/作业之间要唯一；同一逻辑执行重启时则要保持稳定。

**说明**：前缀冲突可能导致生产者被隔离（fencing）；变更前缀则可能延迟清理遗留事务并影响消费者进度。

</details>

9. 60 秒的检查点间隔能否将新增 Kafka 延迟限制在 60 秒以内？

<details>
<summary>显示答案</summary>

**答案**：不能。检查点耗时、事务提交、故障/恢复和消费者延迟也会造成影响。

**说明**：事务超时应与代理（broker）限制和最坏情况下的恢复时间相匹配。5.0.0 构建器（builder）的默认值为一小时。

</details>

10. 每种 Kafka 连接器的事务命名策略都会在每次调用时创建新 ID 吗？

<details>
<summary>显示答案</summary>

**答案**：不会。可选的 POOLING 会重用名称，与默认的 INCREMENTING 不同。

**说明**：POOLING 要求 Kafka 3+、额外的主题读取权限和迁移检查。应单独测量频繁提交的负载。

</details>

11. 实际检查的 DynamicIcebergSink API 和运行时组合是什么？

<details>
<summary>显示答案</summary>

**答案**：forInput → generator → catalogLoader → append；Iceberg 1.11.0 与 Flink 2.1.3。

**说明**：生成器（generator）会向收集器（Collector）输出 DynamicRecords。不能将 Flink 2.1 的运行时 JAR 宣称为已通过 Flink 2.2.1 验证。

</details>

12. 仅插入的 Dynamic Iceberg 辅助程序能否原样用作 Debezium CDC 处理器？

<details>
<summary>显示答案</summary>

**答案**：不能。应验证 RowKind、用于相等匹配的字段、upsert、表格式和数据模式演进限制。

**说明**：受管 Firehose/MSK Connect 替代方案也需要检查数据源、权限、数据键、格式、缓冲和故障处理。

</details>

13. 为 SQL 窗口查询声明 event_time TIMESTAMP 列就够了吗？

<details>
<summary>显示答案</summary>

**答案**：流式事件时间窗口需要时间属性；示例中声明了 WATERMARK。

**说明**：审查过的规划器（planner）会拒绝没有 WATERMARK 的普通时间戳变体。还需要连接器/格式 JAR。

</details>

14. S3 插件和随附演示程序有哪些特定版本的限制？

<details>
<summary>显示答案</summary>

**答案**：插件包含已结束支持的 AWS SDK v1.12.779；StateMachineExample 在代码中设置了两秒的检查点间隔。

**说明**：不要不加判断地混用 v2 提供程序类。应检查 min-pause 和应用程序覆盖项，而不是只根据配置推断执行频率。

</details>

15. 水位线之后到达的记录是否总会被丢弃或自动发送到侧输出（side output）？

<details>
<summary>显示答案</summary>

**答案**：不会。水位线用于估计进度；在允许迟到时间内，窗口可能再次触发。

**说明**：清理后发送到侧输出需要显式配置。应检查时间戳提取、空闲检测以及 SQL/DataStream 差异。

</details>

---

[返回学习资料](../../../data-on-eks/flink/03-state-checkpointing-streaming.md)
