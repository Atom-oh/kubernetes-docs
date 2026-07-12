# Part 8: Best Practices Quiz

本测验用于检验你对贯穿整个 Kafka 深入系列的最佳实践的理解：partition 设计、producer/consumer 调优、安全性（mTLS/SASL）以及成本优化。

## Multiple Choice Questions

1. 在确定 topic 的 partition 数量时，首先应该考虑什么？
   - A) 集群中的 broker 总数
   - B) consumer group 的最大预期并行度
   - C) producer 实例的数量
   - D) 可用的 EBS 卷大小

<details>

<summary>显示答案</summary>

**答案：B) consumer group 的最大预期并行度**

**解释：**
在一个 group 内，单个 partition 同一时间只能由一个 consumer 实例消费，因此你需要决定期望 consumer group 扩展到多大规模，并至少预置相同数量的 partition。如果你计划在峰值时扩展到 20 个 consumer 实例，就至少需要 20 个 partition。broker 数量和 EBS 卷大小是关于集群能多好地承载给定 partition 数量的容量问题，而不是该数量本身的主要驱动因素。
</details>

2. 根据 Confluent 的经典经验法则，每个 broker 的 partition 数量大约的软上限是多少？
   - A) 400
   - B) 4,000
   - C) 40,000
   - D) 400,000

<details>

<summary>显示答案</summary>

**答案：B) 4,000**

**解释：**
Confluent 的经典指南建议每个 broker 的软上限约为 4,000 个 partition，每个集群约为 200,000 个 partition。这可以追溯到基于 ZooKeeper 的 controller 是 metadata 瓶颈的时期。得益于速度更快的 controller metadata 路径，基于 KRaft 的集群可以处理更多 partition，但底层原则——不要仅仅因为可以就过度分区——仍然适用，并且给定 workload 的真实上限应通过负载测试来确认。
</details>

3. 以下哪一项不是 topic 过度分区的真实成本？
   - A) 每个 broker 有更多打开的文件句柄
   - B) producer/broker buffer 中更高的内存使用量
   - C) broker 故障时更长的 leader election 和 rebalance 时间
   - D) consumer group 吞吐量总是下降

<details>

<summary>显示答案</summary>

**答案：D) consumer group 吞吐量总是下降**

**解释：**
过度分区确实会在文件句柄、内存和故障恢复时间方面增加开销，但它并不总是降低吞吐量——如果 consumer 并行度能够跟上，吞吐量不一定会变差。实际上，partition 太少会通过限制可并行工作的 consumer 数量来限制吞吐量。partition 数量是在并行度和开销之间的权衡，而不是一个简单的“越多总是越差/越好”的问题。
</details>

4. 当你增加带 key 的 topic 的 partition 数量时，最直接被破坏的是哪项保证？
   - A) replication factor
   - B) 给定 key 的 message ordering
   - C) consumer group offset commits
   - D) broker 之间的 ISR list

<details>

<summary>显示答案</summary>

**答案：B) 给定 key 的 message ordering**

**解释：**
默认 partitioner 会计算 `hash(key) % partition_count`，因此更改 partition 数量会改变同一个 key 映射到的 partition。由于 Kafka 只保证单个 partition 内的顺序，同一个 key 的消息可能最终被拆分到旧 partition 和新 partition 中，consumer 将不再能够依赖 key 级别的顺序。因此，Kafka Streams 中基于 co-partitioning 的 join 也可能被破坏。
</details>

5. 从哪个 Kafka 版本开始，`enable.idempotence` 默认就是 `true`，无需显式设置？
   - A) Kafka 1.0
   - B) Kafka 2.0
   - C) Kafka 3.0
   - D) Kafka 4.0

<details>

<summary>显示答案</summary>

**答案：C) Kafka 3.0**

**解释：**
自 Kafka 3.0 起，`enable.idempotence=true` 一直是 producer 的默认值，除非 `acks` 或 `retries` 被以不兼容的方式显式覆盖。它会为 producer 分配唯一的 producer ID 和每个 partition 的 sequence number，使 broker 能够自动对重试进行去重。
</details>

6. producer idempotence 会防止什么？
   - A) consumer group rebalances
   - B) 由网络重试导致的 broker 上的重复写入
   - C) partition leader failures
   - D) schema registry compatibility errors

<details>

<summary>显示答案</summary>

**答案：B) 由网络重试导致的 broker 上的重复写入**

**解释：**
当 producer 没有收到 ack 并重试同一条 record 时，如果没有 idempotence，broker 最终可能会将该 record 存储两次。idempotent producer 的 PID 和 sequence number 让 broker 能够检测并丢弃重复项。请注意，这只会对 producer 到 broker 这一跳进行去重——完整的端到端 exactly-once 仍然需要在 idempotence 之上使用 transactional API。
</details>

7. 在 `replication.factor=3` 的 topic 上设置 `acks=all` 和 `min.insync.replicas=2` 的组合效果是什么？
   - A) 写入总是等待全部 3 个 replica
   - B) 直到至少 2 个 replica（包括 leader）拥有该写入，写入才被视为完成
   - C) compression 会自动启用
   - D) partition leader election 会被禁用

<details>

<summary>显示答案</summary>

**答案：B) 直到至少 2 个 replica（包括 leader）拥有该写入，写入才被视为完成**

**解释：**
`acks=all` 让 producer 等待当前 in-sync replica (ISR) set 的确认，而 `min.insync.replicas=2` 会强制在 ISR 缩小到 2 以下（包括 leader）时直接拒绝写入。二者结合起来，是标准的 durability 配置，即使单个 broker 发生故障，也能让写入安全地继续。
</details>

8. 当 consumer 未能在 `max.poll.interval.ms` 内完成处理时会发生什么？
   - A) partition leader 会立即被替换
   - B) consumer 会被强制从 group 中驱逐，从而触发 rebalance
   - C) broker 会自动为该 topic 禁用 compression
   - D) 什么也不会发生——consumer 只是等待下一次 poll

<details>

<summary>显示答案</summary>

**答案：B) consumer 会被强制从 group 中驱逐，从而触发 rebalance**

**解释：**
`max.poll.interval.ms` 限制 consumer 在连续两次 `poll()` 调用之间可以花费的最长时间。超过它会让 broker 将该 consumer 视为死亡，将其从 group 中驱逐并触发 rebalance。如果多个 consumer 同时变慢，这可能级联成一场“rebalance storm”。
</details>

9. 设置 `group.instance.id` 以启用 static group membership 的主要目的是什么？
   - A) 自动提高 consumer 吞吐量
   - B) 避免短暂 pod 重启期间不必要的 rebalance
   - C) 提高 producer compression ratio
   - D) 加快 partition leader election

<details>

<summary>显示答案</summary>

**答案：B) 避免短暂 pod 重启期间不必要的 rebalance**

**解释：**
在 Kubernetes 上，consumer pod 会因为 rolling deploy、OOMKilled 事件等原因频繁重启。设置 `group.instance.id` 会启用 static membership：只要 consumer 在 `session.timeout.ms` 内重新连接，它就会恢复之前的 partition assignment，且完全不会发生 rebalance。这可以防止频繁的短时重启每次都触发完整的 group rebalance。
</details>

10. 当 Strimzi 中的 `KafkaUser` 指定 `authentication.type: tls` 时，生成的 client certificate 由谁签名？
    - A) AWS Certificate Manager
    - B) client 自己生成的 self-signed certificate
    - C) Strimzi 管理的 cluster CA
    - D) 单独部署的 cert-manager Issuer

<details>

<summary>显示答案</summary>

**答案：C) Strimzi 管理的 cluster CA**

**解释：**
Strimzi 在部署 Kafka 集群时会自动预置自己的 cluster CA，并按计划轮换证书。将 `KafkaUser` 的 `authentication.type` 设置为 `tls` 会使 Strimzi 签发一个由该 cluster CA 签名的 client certificate，并将其放入 Secret 中，可直接用于 mTLS 连接。
</details>

## Short Answer Questions

11. 哪个单一术语描述了直接使用低基数字段（例如 `country`）作为 partition key 所产生的问题？

<details>

<summary>显示答案</summary>

**答案：Hot partition**

**解释：**
默认 partitioner 会计算 `hash(key) % partition_count`，因此只有少数不同值的低基数 key 会在大多数流量共享主导值时，将流量集中到一小部分 partition 上，使其他 partition 闲置。可以通过选择更高基数的 key，或对低基数 key 加盐以强制更均匀的分布来缓解这个问题。
</details>

12. 对于 at-least-once 处理很重要的 pipeline，应该用哪种 offset commit 方法（以及设置）替代 auto-commit？

<details>

<summary>显示答案</summary>

**答案：使用 `enable.auto.commit=false` 的 manual commits，并且只在处理完成后调用 `consumer.commitSync()`（或 `commitAsync()`）**

**解释：**
auto-commit 可能会在对应 record 实际完成处理之前提交 offset，因此处理中途崩溃可能会从 pipeline 的角度有效地丢失该 record，尽管 Kafka 认为它已经“committed”。设置 `enable.auto.commit=false` 并仅在业务逻辑完成后提交，可确保崩溃会导致 record 被重新投递并重新处理，从而保留 at-least-once semantics。
</details>

13. 对于大多数 Kafka broker workload，什么资源比 CPU 更重要，为什么？

<details>

<summary>显示答案</summary>

**答案：内存——具体来说，是 OS page cache**

**解释：**
Kafka 旨在从 page cache 提供大多数读取，因此对于 consumer 读取最新数据的常见情况，broker heap 之外剩余的 RAM 会直接决定读取吞吐量。这就是为什么 memory-optimized instance（例如 `r6g`/`r7g`）通常比 compute-optimized instance 为 Kafka broker 提供更好的性价比。
</details>

14. 哪个 Strimzi listener 字段会限制哪些 pods/namespaces 可以访问 broker 端口？

<details>

<summary>显示答案</summary>

**答案：`networkPolicyPeers`**

**解释：**
在 Strimzi listener 上设置 `networkPolicyPeers` 会使 Strimzi 生成标准的 Kubernetes `NetworkPolicy`，只允许来自匹配指定 `podSelector`/`namespaceSelector` 的 pods/namespaces 的流量访问该 listener 端口。这让你可以以声明式方式控制哪些 workload 甚至能够访问 Kafka listener。
</details>

15. 仅仅因为你使用了 EBS CSI driver，EBS 卷加密就会自动发生吗？请说出两种显式启用它的方法。

<details>

<summary>显示答案</summary>

**答案：不会，它不会自动发生。(1) 启用 account/region 级别的 “EBS encryption by default” 设置，或 (2) 在 `StorageClass` parameters 中设置 `encrypted: "true"`（并可选设置 `kmsKeyId`）**

**解释：**
EBS CSI driver 本身不会强制加密——未加密的 `StorageClass` 会生成未加密的 volume。你需要启用 account/region 范围的 “EBS encryption by default” 设置，使每个新 volume 自动加密，或者在用于 broker PVC 的 `StorageClass` 上显式设置 `encrypted: "true"`。由于 Kafka 集群经常承载合规敏感数据，将其视为默认要求而不是事后补充，是更安全的选择。
</details>

## Hands-on Questions

16. 为 durability-critical topic（例如订单处理）编写 producer 设置，涵盖 `acks`、`min.insync.replicas` 考量、idempotence 和 compression。

<details>

<summary>显示答案</summary>

**答案：**
```properties
# Producer settings (assuming the topic has replication.factor=3, min.insync.replicas=2)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

**解释：**
`acks=all` 会等待整个 ISR 的确认以保证 durability，并且与 topic 的 `min.insync.replicas=2`（假设 `replication.factor=3`）结合时，pipeline 可以容忍单个 broker 故障而不丢失数据。`enable.idempotence=true`（Kafka 3.0+ 的默认值）可以防止重试造成的重复写入，而 `compression.type=lz4` 对大多数 workload 来说，在 CPU 开销和 compression ratio 之间提供了良好平衡。`linger.ms`/`batch.size` 用少量延迟换取更大、更高效的 batch。
</details>

17. 为名为 `order-service` 的应用编写一个使用 TLS authentication 的 `KafkaUser` resource，该应用需要对 `orders` topic 的 read/write access，以及对 `order-service-group` consumer group 的 read access。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
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
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

**解释：**
设置 `authentication.type: tls` 会使 Strimzi 自动签发由 cluster CA 签名的 client certificate，并将其放入 Secret。带有 `acls` 列表的 `authorization.type: simple` 以声明式方式授予对 `orders` topic 的 Read/Write/Describe 权限，以及对 `order-service-group` consumer group 的 Read 权限。`strimzi.io/cluster` label 告诉 Strimzi Operator 这个 `KafkaUser` 属于哪个 `Kafka` 集群。
</details>

18. 编写 consumer 设置，使短暂 pod 重启不会触发 rebalance，并且仅在处理完成后提交 offsets。

<details>

<summary>显示答案</summary>

**答案：**
```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
heartbeat.interval.ms=15000
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
    consumer.commitSync();
}
```

**解释：**
`group.instance.id`（设置为唯一值，例如来自 pod name）启用 static group membership，因此只要 consumer 在 `session.timeout.ms` 内重新连接，就会保留其现有 partition assignment，而不会发生 rebalance。`enable.auto.commit=false` 与仅在处理完成后调用的 `commitSync()` 结合，可确保只有完全处理过的 record 的 offsets 被提交，从而保留 at-least-once semantics。`max.poll.records`/`max.poll.interval.ms` 会根据实际的每批处理时间进行调优，以进一步避免不必要的 rebalance。
</details>

---

[返回学习材料](../../../data-on-eks/kafka/08-best-practices.md) | [返回 Kafka 深入首页](../../../data-on-eks/kafka/README.md)
