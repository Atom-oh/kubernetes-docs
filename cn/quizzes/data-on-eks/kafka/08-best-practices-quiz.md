# 第 8 部分：最佳实践测验

根据实际条件评估 partition、client、安全、容量和恢复。

## 1. 为常规 consumer group 规划 partition 数量时，应考虑哪些因素？

<details>
<summary>显示答案</summary>

测量成员并行度、每个 partition 的吞吐量、key 分布偏斜、record 大小、副本放置和恢复需求。一个 partition 会分配给同一 group 中的一个成员；share group 和应用内部并行处理方式则不同。

</details>

## 2. 历史上的 partition 数量规则可以视为当前通用上限吗？

<details>
<summary>显示答案</summary>

不能。限制取决于版本、broker/controller、副本数和工作负载。要区分逻辑 partition 数量与每个 broker 上的副本放置数，并测试稳态和故障情况。

</details>

## 3. 统计包含 `PartitionCount` 的行数就能得到 partition 总数吗？

<details>
<summary>显示答案</summary>

不能。这样数出的是 topic 摘要行。应像 `partition_summary.py` 一样读取 `Partition:` 行，分别统计逻辑 partition 和副本放置数。还要检查结果为空、可见性和筛选条件。

</details>

## 4. 增加 keyed topic 的 partition 数量时，每个 key 都必须迁移吗？

<details>
<summary>显示答案</summary>

不一定每个 key 都会迁移，但部分 key 可能重新映射。旧 record 仍留在原处，这会影响 key 顺序、状态和共分区 join 的假设。请检查 serializer、partitioner 和拓扑。

</details>

## 5. 显式配置 `acks` 或 `retries` 总会禁用默认的幂等性吗？

<details>
<summary>显示答案</summary>

不会；问题在于设置不兼容。显式设置 `enable.idempotence=true` 时，`acks`、`retries` 和 `max.in.flight` 必须兼容；冲突会导致配置错误。

</details>

## 6. 仅有幂等性或 `transactional.id` 就能实现端到端 exactly-once 吗？

<details>
<summary>显示答案</summary>

不能。producer 重试与应用重新提交不同。Kafka 事务需要原子提交输出和输入 offset、fencing/`read_committed` 以及正确的生命周期管理；外部系统则需要自己的处理策略。

</details>

## 7. RF=3、`acks=all`、`min.insync.replicas=2` 时，如果 ISR 降到 1 会怎样？

<details>
<summary>显示答案</summary>

写入会被拒绝。`acks=all` 等待当前 ISR 中的副本确认，而最小 ISR 是 topic/broker 设置。当复制已经降级时，这并不无条件保证写入继续，也不保证单次故障后零数据丢失。

</details>

## 8. `max.poll.interval.ms` 与 heartbeat/session 设置有哪些区别需要注意？

<details>
<summary>显示答案</summary>

检查两次 poll 之间的实际处理时长。静态成员的重新分配可能要等到 session 过期。还要区分 classic client 的 heartbeat/session 设置与 consumer protocol 下由 broker 控制的设置。

</details>

## 9. 静态成员身份能保证重启时不触发 rebalance 吗？

<details>
<summary>显示答案</summary>

不能。稳定且唯一的身份、重新连接时间、拓扑、订阅和成员关系都会影响结果。重复的活动 ID 可能导致 fencing；较长的 session 也会延迟对真实故障的恢复。

</details>

## 10. 默认 Strimzi 中，哪个 CA 为 KafkaUser 的 mTLS client 证书签名？

<details>
<summary>显示答案</summary>

clients CA。cluster CA 用于 broker/内部组件证书。请区分 client 凭证与用于信任 broker 的 CA 证书链。

</details>

## 11. 高基数 key 或随机加盐本身能安全地解决 key 分布偏斜吗？

<details>
<summary>显示答案</summary>

不能。占主导的热点 key 仍可能造成流量偏斜。加盐会改变顺序、join 和 compaction 身份；先确认数据契约允许这样做，并规划后续合并。

</details>

## 12. 处理异常后不提交 offset、继续 poll，这样安全吗？

<details>
<summary>显示答案</summary>

不安全。fetch position 可能已经前进。应正确停止/恢复或 seek，并且只在持久化处理成功后提交。还要为重复重放和外部副作用设计幂等处理。

</details>

## 13. 仅凭内存量或固定的 heap 大小就能确定 Kafka 容量吗？

<details>
<summary>显示答案</summary>

不能。要测量 page cache、TLS/压缩 CPU、网络、IOPS/吞吐量、cgroup 内存和恢复情况。codec 和实例的成本优势取决于数据与工作负载。

</details>

## 14. 在同一个 networkPolicyPeers 条目中，`namespaceSelector` 和 `podSelector` 如何组合？

<details>
<summary>显示答案</summary>

在一个 peer 中是 AND 关系；不同 peer 条目之间是 OR 关系。NetworkPolicy 是累加生效的，并且需要检查 CNI 是否实施策略以及出站规则。这个条目不会拒绝其他策略已允许的流量。

</details>

## 15. 说明 StorageClass 加密、Auto Mode 和现有卷之间的关系。

<details>
<summary>显示答案</summary>

针对所选 provisioner 设置 `encrypted: true` 和实际所需的 KMS 权限，然后验证 EBS 卷。不能根据 Auto Mode 的节点/临时磁盘推断所有动态 PVC 都已加密。修改 StorageClass 或账户默认值不会追溯加密现有卷。

</details>

## 16. 写出 producer 调优配置，并说明 `batch.size` 和最小 ISR 的作用。

<details>
<summary>显示答案</summary>

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

`batch.size` 控制每个 partition 的批处理/分配大小，并非严格的 record 或请求上限。在 topic/broker 上配置 `min.insync.replicas`。应测量 codec/linger 的效果，并处理发送失败和投递超时。

</details>

## 17. 编写独立的 mTLS KafkaUser，同时保留现有 SCRAM 用户。

<details>
<summary>显示答案</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

还需要一个 `tls: true` 且 `authentication.type: tls` 的 listener；`tls` 并不是名为 exposure type 的值。分发并轮换 clients-CA 凭证及 broker 信任配置，并验证实际允许/拒绝的操作。

</details>

## 18. 如何将基于环境变量的静态成员 ID 与手动提交结合使用？

<details>
<summary>显示答案</summary>

Java Properties 不会展开 `${POD_NAME}`。创建 consumer 前，先解析出唯一且稳定的 ID 并传给 `setStaticIdentity`。使用 `enable.auto.commit=false` 和 `processOneBatch`；不要吞掉失败后继续 poll。仍需处理保留期限、恢复和重复消息。

</details>

---

[返回学习材料](../../../data-on-eks/kafka/08-best-practices.md) | [下一个测验](./09-kafka-benchmark-quiz.md)
