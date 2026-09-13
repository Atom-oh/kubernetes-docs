# Kafka 基础测验

> **最后更新**：2026 年 9 月 12 日，Kafka 4.3.1。

本测验检验您对 Kafka 代理/主题/分区模型、顺序保证、消费者组再平衡、KRaft 以及复制/持久性设置的理解。

## 选择题

1. Kafka 在什么范围内保证消息顺序？
   - A) 整个集群
   - B) 整个主题（跨所有分区）
   - C) 仅同一分区内
   - D) 仅同一消费者组内

<details>

<summary>显示答案</summary>

**答案：C) 仅同一分区内**

**解释：**
保证的是分区日志顺序。同键路由要求序列化、分区器和分区数保持一致；扩缩分区或客户端更改可能改变映射。业务事件时间和应用并行处理需要独立顺序约定。
</details>

2. ISR（同步副本）指什么？
   - A) 集群中注册的所有代理集合
   - B) 已充分追上领导者的副本集合
   - C) 不具备成为领导者资格的副本集合
   - D) 属于某消费者组的消费者集合

<details>

<summary>显示答案</summary>

**答案：B) 已充分追上领导者的副本集合**

**解释：**
ISR 包含充分同步的副本，包括领导者。acks=all 等待当前完整 ISR，而 min.insync.replicas 约束其最小大小。确认不等同于每条记录都执行 fsync。
</details>

3. Kafka 4.3 Java KafkaConsumer 的 enable.auto.commit 默认值是什么？
   - A) `false`
   - B) `true`
   - C) 取决于代理配置
   - D) 此设置从 Kafka 3.x 起已移除

<details>

<summary>显示答案</summary>

**答案：B) `true`**

**解释：**
Kafka 4.3 Java KafkaConsumer 默认为 true，间隔为 5000 ms。客户端位置不代表外部业务完成。异步/并行处理时，应避免提交超过未完成工作的位置。手动提交也需要正确记录已完成位置。
</details>

4. 以下哪项不会触发消费者组再平衡？
   - A) 新消费者加入组
   - B) Classic 协议消费者未在 `session.timeout.ms` 内发送心跳
   - C) 主题分区数更改
   - D) 生产者使用 `acks=all` 发送消息

<details>

<summary>显示答案</summary>

**答案：D) 生产者使用 `acks=all` 发送消息**

**解释：**
成员关系、订阅分区和心跳/轮询超时影响分配。Classic 使用客户端 session.timeout.ms；consumer 协议使用代理 group.consumer.session.timeout.ms。acks 控制生产者确认。
</details>

5. KRaft（Kafka Raft 元数据模式）从哪个 Kafka 版本开始达到生产就绪（GA）？
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>显示答案</summary>

**答案：B) Kafka 3.3**

**解释：**
KRaft 首次在 Kafka 2.8 中以早期访问预览引入，直到 Kafka 3.3 才达到生产就绪（正式可用）。后续次版本持续提升稳定性，Kafka 4.0 完全移除 ZooKeeper 模式，使 KRaft 成为唯一受支持的元数据管理机制。
</details>

6. 哪个 Kafka 版本完全移除了 ZooKeeper 模式，仅保留 KRaft 作为元数据管理机制？
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>显示答案</summary>

**答案：D) Kafka 4.0**

**解释：**
Kafka 4.0（2025 年 3 月发布）完全移除了基于 ZooKeeper 的元数据管理模式。从此版本起，新集群只能以 KRaft 模式引导，现有 ZooKeeper 集群必须在 Kafka 3.x 上完成 KRaft 迁移后，才能升级到 4.0。
</details>

7. 在三个 ISR 副本健康且控制器法定人数等其他要求维持的条件下，RF=3/min ISR=2/acks=all 可容忍多少个代理故障并保持写入可用？
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>显示答案</summary>

**答案：B) 1**

**解释：**
这里假定三个副本最初均属于健康 ISR，且控制器法定人数、网络和存储仍可用。一个代理故障后，两个剩余 ISR 成员满足最小要求，但转换期间可能出现错误/重试。两个副本故障不能保持写入可用。仅 RF=3 不保证任意两个代理故障时数据仍然保全。
</details>

8. 哪种 acks 设置不等待代理确认？
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>显示答案</summary>

**答案：A) `acks=0`**

**解释：**
acks=0 不等待代理响应，无法确认存储，返回偏移量 -1。它不保证所有负载下延迟/吞吐量最佳，并与显式启用幂等性冲突。acks=all 和 -1 等效。
</details>

9. KRaft 架构中，实际处理集群元数据更改（分区领导者选举、主题创建等）的单个节点称为什么？
   - A) 控制器投票成员
   - B) 活动控制器
   - C) 分区领导者
   - D) 元数据代理

<details>

<summary>显示答案</summary>

**答案：B) 活动控制器**

**解释：**
一个控制器投票成员被选为活动控制器。选举替代者需要必要的多数派和连通性。专用控制器不必承担代理数据角色。
</details>

10. Classic 组协议中 CooperativeStickyAssignor 的用途是什么？
    - A) 改变生产者对分区键的哈希方式
    - B) 尽量减少再平衡期间的分区移动，降低成本
    - C) 动态调整控制器法定人数中的投票成员数
    - D) 增加 ISR 中包含的副本数

<details>

<summary>显示答案</summary>

**答案：B) 尽量减少再平衡期间的分区移动，降低成本**

**解释：**
CooperativeStickyAssignor 是 Classic 组协议的客户端分配器。增量重新分配减少不必要中断。较新的 consumer 协议使用服务器端分配器，因此相同客户端类配置不适用。
</details>

## 简答题

11. KRaft 内部元数据 Raft 日志叫什么？

<details>

<summary>显示答案</summary>

**答案：`__cluster_metadata`**

**解释：**
__cluster_metadata 是 KRaft 内部元数据 Raft 日志，通常表现为 __cluster_metadata-0 目录。它不是通过 KafkaProducer/KafkaConsumer 管理的普通应用主题；控制器和代理使用元数据复制/获取路径。
</details>

12. 启用哪个生产者设置可防止网络重试导致的重复消息写入？

<details>

<summary>显示答案</summary>

**答案：`enable.idempotence`（幂等生产者，`enable.idempotence=true`）**

**解释：**
生产者 ID、纪元和序列号抑制同一次重试传输的重复。它们通常不去重应用将同一业务事件作为新发送提交的情况。事务需要逻辑写入方身份/隔离、原子输出与输入偏移提交，以及 read_committed 消费。
</details>

13. 因所选分区键基数低（不同值较少）而使流量集中在少数分区的情况叫什么？

<details>

<summary>显示答案</summary>

**答案：热点分区**

**解释：**
分区键值的基数（不同值数量）不足，或某个值出现频率过高，就会形成热点分区。例如，大部分流量集中于少数大型客户 ID 时，仅这些键哈希到的分区承受过量负载，其他分区则空闲。这削弱并行消费者处理的收益，因此设计键时应仔细审核流量分布。
</details>

14. 哪个设置限制连续 KafkaConsumer poll() 调用之间的间隔？

<details>

<summary>显示答案</summary>

**答案：`max.poll.interval.ms`**

**解释：**
默认值为 300000 ms。使用静态成员关系（group.instance.id）时，超过此值不会立即重新分配分区；停止心跳后的会话超时也很重要。检查 Classic/consumer 超时规则，并同时调整处理、轮询大小和执行模型。
</details>

## 实践题

15. 编写 `kafka-topics.sh` 命令，创建名为 `events` 的主题，包含 8 个分区、复制因子 3，并设置 `min.insync.replicas=2`。

<details>

<summary>显示答案</summary>

**答案：**
```bash
kafka-topics.sh --create \
  --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**解释：**
此处假定集群可达、至少有三个代理并具有适当身份验证。八个分区允许自动分配的基于分区消费者组中最多八个活动所有者；一个消费者可拥有多个分区。容错取决于实际同步、法定人数和其他条件。
</details>

16. 为专用控制器 node.id=90 编写 Kafka 4.3.1 动态法定人数配置片段，包含三个发现端点，并解释为什么种子不代表投票成员关系。

<details>

<summary>显示答案</summary>

**答案：**
```properties
# Configuration excerpt for node 90; these DNS names must resolve in the deployment.
process.roles=controller
node.id=90
controller.quorum.bootstrap.servers=controller-0.example.internal:9093,controller-1.example.internal:9093,controller-2.example.internal:9093
listeners=CONTROLLER://controller-0.example.internal:9093
advertised.listeners=CONTROLLER://controller-0.example.internal:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=./controller-90-data
```

**解释：**
controller.quorum.bootstrap.servers 是发现种子列表，不是投票成员关系。初始格式化/引导必须协调集群 ID、目录 ID 和初始投票成员。动态法定人数不要设置 controller.quorum.voters。让 DNS、监听器和 TLS/身份验证匹配部署；这是配置片段，不是完整可部署集群。
</details>

17. 提供幂等性和事务 ID 的生产者设置，并解释 Kafka 到 Kafka 恰好一次处理还需哪些步骤。

<details>

<summary>显示答案</summary>

**答案：**
```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**解释：**
配置仅为生产者使用事务做准备。实现 initTransactions、beginTransaction、输出发送、携带下一输入偏移的 sendOffsetsToTransaction、commitTransaction，以及中止/恢复处理。消费者禁用自动提交并使用 read_committed。并发写入方需要不同事务 ID；delivery.timeout.ms 等期限仍适用。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [下一测验：Strimzi Operator](./02-strimzi-operator-quiz.md)
