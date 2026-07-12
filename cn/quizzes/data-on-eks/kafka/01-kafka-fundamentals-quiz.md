# Kafka Fundamentals Quiz

本测验用于测试你对 Kafka 的 broker/topic/partition 模型、排序保证、consumer group 再平衡、KRaft 以及复制/持久性设置的理解。

## Multiple Choice Questions

1. Kafka 在什么范围内保证消息顺序？
   - A) 整个集群范围内
   - B) 整个 topic 范围内（跨其所有 partition）
   - C) 仅在同一个 partition 内
   - D) 仅在同一个 consumer group 内

<details>

<summary>显示答案</summary>

**答案：C) 仅在同一个 partition 内**

**解释：**
Kafka 只保证单个 partition 内的消息顺序。如果一个 topic 有多个 partition，则存储在不同 partition 中的消息之间没有保证的相对顺序，无论 producer 发送它们的顺序如何。要保留特定实体事件的顺序（例如，给定订单 ID 的事件），必须使用一个标识该实体的 key，以便该实体的所有事件都路由到同一个 partition。
</details>

2. ISR (In-Sync Replicas) 指的是什么？
   - A) 集群中注册的所有 broker 的集合
   - B) 与 leader 足够同步的 replica 集合
   - C) 没有资格成为 leader 的 replica 集合
   - D) 属于某个 consumer group 的 consumer 集合

<details>

<summary>显示答案</summary>

**答案：B) 与 leader 足够同步的 replica 集合**

**解释：**
ISR (In-Sync Replicas) 是指其数据与 partition 的 leader replica 足够同步的 follower replica（加上 leader 本身）的集合。当以 `acks=all` 发送写入时，只有 ISR 中的每个 replica 都收到消息后，该写入才被视为成功。如果某个 follower 落后 leader 太多，它会从 ISR 中移除，这在故障期间作为数据一致性的保护机制。
</details>

3. Kafka consumer 的 `enable.auto.commit` 设置默认值是什么？
   - A) `false`
   - B) `true`
   - C) 取决于 broker 配置
   - D) 该设置从 Kafka 3.x 开始已被移除

<details>

<summary>显示答案</summary>

**答案：B) `true`**

**解释：**
`enable.auto.commit` 的默认值是 `true`，在这种情况下 consumer 会每隔 `auto.commit.interval.ms`（默认 5 秒）自动提交 offset。这很方便，但 offset 可能会在消息处理实际完成之前就被提交，从而在故障时带来消息丢失风险。要仅在处理完成后提交，请设置 `enable.auto.commit=false` 并显式调用 `commitSync()` 或 `commitAsync()`。
</details>

4. 以下哪一项不会触发 consumer group rebalance？
   - A) 新 consumer 加入 group
   - B) consumer 未能在 `session.timeout.ms` 内发送 heartbeat
   - C) topic 上的 partition 数量发生变化
   - D) producer 使用 `acks=all` 发送消息

<details>

<summary>显示答案</summary>

**答案：D) producer 使用 `acks=all` 发送消息**

**解释：**
当 consumer group 成员关系发生变化或订阅 topic 的 partition 布局发生变化时，会发生 rebalance：consumer 加入或离开、heartbeat 超时、超过 `max.poll.interval.ms`，或 partition 数量变化，都是典型触发条件。另一方面，`acks` 是 producer 端设置，用于决定 producer 如何确认写入完成——它与 consumer group 的 partition 分配或 rebalance 无关。
</details>

5. 从哪个 Kafka 版本开始，KRaft (Kafka Raft metadata mode) 成为生产就绪 (GA)？
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>显示答案</summary>

**答案：B) Kafka 3.3**

**解释：**
KRaft 最早在 Kafka 2.8 中作为早期访问预览引入，但直到 Kafka 3.3 才成为生产就绪 (General Availability)。它在后续次要版本中持续稳定下来，而 Kafka 4.0 完全移除了 ZooKeeper mode，使 KRaft 成为唯一受支持的 metadata management 机制。
</details>

6. 哪个 Kafka 版本完全移除了 ZooKeeper mode，使 KRaft 成为唯一的 metadata management 机制？
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>显示答案</summary>

**答案：D) Kafka 4.0**

**解释：**
Kafka 4.0（于 2025 年 3 月发布）完全移除了基于 ZooKeeper 的 metadata management mode。从该版本起，新集群只能以 KRaft mode 启动，而现有基于 ZooKeeper 的集群必须先在 Kafka 3.x 上完成迁移到 KRaft，然后才能升级到 4.0。
</details>

7. 如果某个 topic 配置为 `replication.factor=3` 和 `min.insync.replicas=2`，并且 producer 使用 `acks=all`，该 topic 在仍可接受写入的情况下最多能容忍多少个 broker 同时故障？
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>显示答案</summary>

**答案：B) 1**

**解释：**
当 replication factor 为 3 时，每个 partition 存储在 3 个 replica 上。`min.insync.replicas=2` 表示要使 `acks=all` 写入成功，至少必须有 2 个 replica 保持在 ISR 中。如果一个 broker 故障，剩余 2 个 replica 仍留在 ISR 中，因此写入会继续成功。但如果两个 broker 同时故障，ISR 会缩小到只有 1 个，不再满足 `min.insync.replicas`，producer 会收到 `NotEnoughReplicasException`。
</details>

8. 哪个 producer `acks` 设置具有最低的持久性但最低的延迟？
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>显示答案</summary>

**答案：A) `acks=0`**

**解释：**
`acks=0` 表示 producer 完全不等待 broker 的任何响应——消息一发送出去，它就认为写入成功。这在延迟和吞吐量方面是最快的选项，但如果发生网络问题或 broker 故障，就无法知道消息是否实际被存储，因此它是数据丢失风险最高的选项。请注意，`acks=all` 和 `acks=-1` 含义相同——都是最安全的设置，要求每个 ISR replica 在写入被视为成功之前确认该写入。
</details>

9. 在 KRaft 架构中，实际处理集群 metadata 变更（partition leader 选举、topic 创建等）的单个节点称为什么？
   - A) Controller Voter
   - B) Active Controller
   - C) Partition Leader
   - D) Metadata Broker

<details>

<summary>显示答案</summary>

**答案：B) Active Controller**

**解释：**
在 KRaft 中，多个 controller voter（通常为 3 或 5 个，使用奇数以形成 Raft quorum）参与复制 metadata log，其中一个会通过 Raft consensus 被选为 Active Controller。只有 Active Controller 实际处理集群 metadata 变更；如果它故障，将从剩余 voter 中选出新的 Active Controller。
</details>

10. 使用 `CooperativeStickyAssignor` 的主要目的是什么？
    - A) 改变 producer 对 partition key 进行哈希的方式
    - B) 在 rebalance 期间尽量减少 partition 移动，从而降低成本
    - C) 动态调整 controller quorum 中 voter 的数量
    - D) 增加 ISR 中包含的 replica 数量

<details>

<summary>显示答案</summary>

**答案：B) 在 rebalance 期间尽量减少 partition 移动，从而降低成本**

**解释：**
传统的 eager rebalancing 协议要求每个 consumer 在 rebalance 开始时放弃其拥有的所有 partition，并从头重新分配。`CooperativeStickyAssignor` 使用 cooperative rebalancing 协议，只重新分配实际需要移动的 partition，让现有 consumer 保留它们已经拥有的 partition。这减少了 rebalance 期间消费被中断的 partition 数量，从而缓解整体吞吐量下降。
</details>

## Short Answer Questions

11. 在 KRaft mode 中，存储集群 metadata 的内部 Kafka topic 名称是什么？

<details>

<summary>显示答案</summary>

**答案：`__cluster_metadata`**

**解释：**
在 KRaft mode 中，Kafka 不依赖单独的 ZooKeeper ensemble，而是将集群 metadata（topic/partition 信息、ACL、controller 状态变更历史等）作为 event log 存储在名为 `__cluster_metadata` 的内部 topic 中。Controller quorum voter 通过 Raft protocol 复制该 topic，broker 订阅它以保持最新 metadata。这个设计让 Kafka 也可以复用其自身的核心存储模型——partition log——进行 metadata management。
</details>

12. 启用哪个 producer 设置可以防止网络重试导致的重复消息写入？

<details>

<summary>显示答案</summary>

**答案：`enable.idempotence`（idempotent producer，`enable.idempotence=true`）**

**解释：**
设置 `enable.idempotence=true` 会使 producer 为每条消息附加 sequence number 和 producer ID，broker 使用它们检测并丢弃由重试导致的重复写入。该设置是在 Kafka 内实现 exactly-once 写入（topic 级别）的基础，将它与 `transactional.id` 结合，可以将该保证扩展到跨多个 partition 或 topic 的原子写入。
</details>

13. 当所选 partition key 的基数较低（不同值很少），导致流量集中在少数 partition 上时，这种情况称为什么？

<details>

<summary>显示答案</summary>

**答案：Hot Partition**

**解释：**
当选作 partition key 的值没有足够的基数（不同值），或者某个特定值出现得过于频繁时，就会出现 hot partition。例如，如果大部分流量集中在少数几个大型客户 ID 上，只有这些 key 哈希到的 partition 会收到过高负载，而其他 partition 则处于空闲状态。这会削弱并行 consumer 处理的优势，因此在设计 key 时应仔细审查流量分布。
</details>

14. 哪个设置控制 consumer 在两次调用 `poll()` 之间可花费的最长消息处理时间，并在超过该时间时因 consumer 被认为已离开 group 而触发 rebalance？

<details>

<summary>显示答案</summary>

**答案：`max.poll.interval.ms`**

**解释：**
`max.poll.interval.ms` 指定连续两次 `poll()` 调用之间允许的最长时间（默认 5 分钟）。如果处理一次 `poll()` 返回的 record 所用时间超过该值，broker 会认为该 consumer 不再存活，将其从 group 中移除，并触发 rebalance。这是与 `session.timeout.ms` 分开的机制，后者由单独的 heartbeat 线程管理；如果处理逻辑较慢，应增加此值或减少 `max.poll.records` 以缩小 batch size。
</details>

## Hands-on Questions

15. 编写 `kafka-topics.sh` 命令，创建一个名为 `events` 的 topic，包含 8 个 partition、replication factor 为 3，并设置 `min.insync.replicas=2`。

<details>

<summary>显示答案</summary>

**答案：**
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**解释：**
`--partitions 8` 将该 topic 拆分为 8 个 partition，允许最多 8 个 consumer 并行消费。`--replication-factor 3` 将每个 partition 复制到 3 个 broker，在最多 2 个 broker 故障时保留数据。`--config min.insync.replicas=2` 强制至少 2 个 replica 保持在 ISR 中，`acks=all` 写入才能成功；结合 replication factor，可在单个 broker 故障时保持写入可用。
</details>

16. 编写一个用于专用 3 节点 KRaft controller quorum 的示例 `server.properties` 配置（仅 controller role，无 broker role）。使用 node ID 90、91 和 92。

<details>

<summary>显示答案</summary>

**答案：**
```properties
# server.properties for one dedicated controller node (e.g., node.id=90)
process.roles=controller
node.id=90

controller.quorum.voters=90@kraft-controller-0:9093,91@kraft-controller-1:9093,92@kraft-controller-2:9093

listeners=CONTROLLER://:9093
controller.listener.names=CONTROLLER

log.dirs=/var/lib/kafka/controller-data
```

**解释：**
设置 `process.roles=controller` 表示该节点只作为 controller quorum voter，不服务 broker 流量。在较大的集群中，以这种方式将 controller role 与 broker role 分离，可以避免 metadata 处理负载与数据处理负载竞争，从而提高稳定性。`controller.quorum.voters` 必须以 `node.id@host:port` 的格式列出参与 controller quorum 的每个节点，使用奇数数量（3 或 5）可让集群计算出明确的 Raft quorum majority。
</details>

17. 编写一个 producer 配置（Java properties 格式），结合 `acks=all`、idempotent write 和 transactional ID，以实现 exactly-once 写入。

<details>

<summary>显示答案</summary>

**答案：**
```properties
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all
enable.idempotence=true
transactional.id=order-producer-1
max.in.flight.requests.per.connection=5
retries=2147483647
```

**解释：**
`acks=all` 要求每个 ISR replica 都收到消息后，该写入才被视为成功，而 `enable.idempotence=true` 会消除由重试导致的重复写入。设置 `transactional.id` 会使 producer 成为 transactional producer，使其能够使用 `initTransactions()`、`beginTransaction()` 和 `commitTransaction()` API 跨多个 partition 原子写入。设置很高的 `retries` 是安全的，只要已设置 `enable.idempotence=true`，因为顺序和重复会自动管理；`max.in.flight.requests.per.connection` 必须保持在 5 或以下，以避免破坏排序保证。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [下一个测验：Strimzi Operator](./02-strimzi-operator-quiz.md)
