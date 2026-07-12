# Kafka 运维测验

本测验用于检验你对 EKS 上由 Strimzi 管理的 Kafka 集群的存储设计、broker 扩缩容、Cruise Control 再平衡、滚动升级和故障处理的理解。

## 多项选择题

1. 对于许多 consumer group 从分散 offset 读取而产生大量随机 I/O，并且有严格 p99 延迟 SLA 的工作负载，哪种 EBS volume type 更适合？
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>显示答案</summary>

**答案：C) io2**

**解释：**
io2 按 IOPS 计费，最高可提供 256,000 IOPS，并具备 99.999% 的持久性，因此非常适合以小型随机 I/O 为主的延迟敏感型工作负载。大多数事件流工作负载受吞吐量限制，因此 gp3 是更具成本效益的起点；只有当随机 I/O 成为瓶颈时（例如突发的 consumer lag 或严格的 p99 SLA），才值得切换到 io2。
</details>

2. `KafkaNodePool` 上的哪种存储类型会将 broker 配置为使用多个独立 volume？
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>显示答案</summary>

**答案：B) `type: jbod`**

**解释：**
`storage.type: jbod` (Just a Bunch Of Disks) 允许你在 `volumes` 列表中为每个 broker 定义多个独立 volume。每个 volume 由一个 `id` 标识，partition 会以轮询方式分布到这些 volume 上。`persistent-claim` 是 JBOD 配置中每个单独 volume 条目使用的类型。
</details>

3. 在保留期为 7 天、峰值吞吐量为 100MB/s、复制因子为 3，并预留 30% headroom 的情况下，哪个公式可以得到整个集群所需的磁盘容量？
   - A) 100MB/s × 7 天（秒） × 3
   - B) 100MB/s × 7 天（秒） × 3 × 1.3
   - C) 100MB/s × 7 天（秒） ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>显示答案</summary>

**答案：B) 100MB/s × 7 天（秒） × 3 × 1.3**

**解释：**
容量估算公式是 `retention period × peak throughput × replication factor × (1 + headroom ratio)`。将保留期转换为秒并乘以峰值吞吐量，得到原始数据量；再乘以复制因子以计入副本；最后乘以 headroom 系数（30% headroom = 1.3x），以留出安全余量。
</details>

4. 在由 Strimzi 管理的 Kafka 集群上，operator 必须手动运行哪个脚本来格式化存储 volume？
   - A) 必须在每个 broker 上手动运行 `kafka-storage.sh format`
   - B) 必须使用 `kafka-configs.sh` 来应用格式化设置
   - C) 无 — Strimzi Operator 会在 broker pod 启动时自动处理
   - D) 必须使用 `kafka-reassign-partitions.sh --format`

<details>

<summary>显示答案</summary>

**答案：C) 无 — Strimzi Operator 会在 broker pod 启动时自动处理**

**解释：**
使用 Strimzi 时，Operator 会在 broker pod 启动时自动处理 volume 格式化。相比手动运行普通开源 Kafka，这更方便；在后者中，你需要自行运行 `kafka-storage.sh format`。
</details>

5. 当你通过增加 `KafkaNodePool` 上的 `replicas` 来扩展 broker 时，新 broker 会自动发生什么？
   - A) 现有 partition 会立即重新分布到新 broker 上
   - B) 新 broker 会加入集群，但现有 topic partition 不会自动重新分配
   - C) 新 broker 会自动成为所有 partition 的 leader
   - D) 新 broker 只作为 controller 提供服务

<details>

<summary>显示答案</summary>

**答案：B) 新 broker 会加入集群，但现有 topic partition 不会自动重新分配**

**解释：**
增加 `replicas` 会使 Strimzi 创建新的 broker pod 并将它们加入集群，但把现有 topic partition 移动到这些 broker 上并不会自动发生。要真正利用新 broker 的容量，需要通过 `kafka-reassign-partitions.sh` 手动重新分配，或使用 Cruise Control 的 `add-brokers` 模式进行 rebalance。
</details>

6. 在缩减 broker 之前必须做什么？
   - A) 什么都不用做 — Strimzi 会自动 drain 它
   - B) 必须先将要移除的 broker 上的 partition 重新分配到剩余 broker
   - C) 必须重启集群
   - D) 必须删除所有 topic

<details>

<summary>显示答案</summary>

**答案：B) 必须先将要移除的 broker 上的 partition 重新分配到剩余 broker**

**解释：**
缩减 broker 时，Strimzi 不会自动 drain partition。在减少 `replicas` 之前，必须将要移除的 broker 上的所有 replica 重新分配到剩余 broker — 否则可能出现副本不足的 partition，甚至直接导致数据丢失。
</details>

7. Cruise Control 的主要作用是什么？
   - A) 它自动化 topic 的创建和删除
   - B) 它收集 broker 负载指标，并自动生成/执行基于目标的 partition 重新分配计划
   - C) 它管理 consumer group offset commit
   - D) 它自动续订 TLS 证书

<details>

<summary>显示答案</summary>

**答案：B) 它收集 broker 负载指标，并自动生成/执行基于目标的 partition 重新分配计划**

**解释：**
Cruise Control 会持续收集每个 broker 的负载指标 — 磁盘使用率、CPU、网络吞吐量 — 并使用配置的目标自动生成和执行 partition 重新分配计划。这消除了例行 rebalance 时手动运行 `kafka-reassign-partitions.sh` 的需要。
</details>

8. 在 `KafkaRebalance` 资源的 `mode` 字段中，哪种模式专注于将 partition 移动到新添加的 broker 上以填充其负载？
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>显示答案</summary>

**答案：B) `add-brokers`**

**解释：**
`add-brokers` 模式专注于将 partition 移动到新添加的 broker 上，因此比 `full` 模式更快、范围更窄；`full` 模式会在每个 broker 之间重新分配，包括不相关的 broker。相反，`remove-brokers` 模式专注于将 partition 从即将移除的 broker 上移走 — 这是缩减前很有用的 drain 步骤。
</details>

9. 将 KRaft 模式集群的 Kafka 版本从 3.8 升级到 3.9 的正确流程是什么？
   - A) 一次性将 `version` 和 `metadataVersion` 都改为 3.9
   - B) 先只将 `version` 改为 3.9，以滚动发布新的 broker/controller 软件，并且只有在每个 node 都被替换之后，才将 `metadataVersion` 提升到 3.9-IV0
   - C) 先提升 `metadataVersion`，再更改 `version`
   - D) 停止整个集群并一次性更改所有值

<details>

<summary>显示答案</summary>

**答案：B) 先只将 `version` 改为 3.9，以滚动发布新的 broker/controller 软件，并且只有在每个 node 都被替换之后，才将 `metadataVersion` 提升到 3.9-IV0**

**解释：**
在 KRaft 模式下没有 `inter.broker.protocol.version`/`log.message.format.version`（这些是 ZooKeeper 时代的设置）。取而代之的是，必须分两个阶段提升 `spec.kafka.version`（软件版本）和 `spec.kafka.metadataVersion`（controller quorum 用来持久化 metadata 的格式）。阶段 1 只提升软件版本，同时将 `metadataVersion` 固定在旧格式，这样在 rollout 期间旧 node 和新 node 同时运行时，它们在 controller quorum 中仍彼此兼容。阶段 2 只有在确认每个 node 都已被替换之后，才提升 `metadataVersion`。颠倒这个顺序意味着仍运行旧 binary 的 node 无法理解新的 metadata 格式，从而导致 controller quorum 通信错误。
</details>

10. Strimzi 会为每个 `KafkaNodePool` 自动创建哪种 Kubernetes 资源来限制自愿驱逐？
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>显示答案</summary>

**答案：C) PodDisruptionBudget**

**解释：**
Strimzi 会为每个 `KafkaNodePool` 自动创建一个 `PodDisruptionBudget` (PDB)。默认情况下，它一次只允许一个 broker pod 发生自愿驱逐（node drain、autoscaler node 替换等），从而防止多个 broker 同时下线并破坏可用性。
</details>

## 简答题

11. 在滚动重启期间，Strimzi 会遵守哪个 Kafka 配置值，以确保 partition 的可用 replica 数量永远不会低于所需的最小值？

<details>

<summary>显示答案</summary>

**答案：`min.insync.replicas`**

**解释：**
在由 CR spec 变更触发的滚动重启期间，Strimzi Operator 会一次重启一个 broker，同时确保每个 partition 的 `min.insync.replicas` 要求仍然得到满足。这可以防止重启导致 partition 的可用 in-sync replica 数量低于所需阈值，否则会造成写入失败或可用性损失。
</details>

12. 在升级 Kafka 集群版本本身之前，应先升级哪个组件？

<details>

<summary>显示答案</summary>

**答案：Strimzi Operator**

**解释：**
每个 Strimzi 版本支持特定范围的 Kafka 版本，如果将 CR 改为正在运行的 Operator 无法识别的 Kafka 版本，验证会失败。因此，在提升 Kafka 软件版本之前，必须先将 Strimzi Operator 本身升级到最新版本。
</details>

13. 在实际执行 partition 重新分配计划之前，`kafka-reassign-partitions.sh` 的哪个选项用于针对指定 broker 列表生成计划？

<details>

<summary>显示答案</summary>

**答案：`--generate`**

**解释：**
`--generate` 选项会基于 `--topics-to-move-json-file` 和 `--broker-list` 生成重新分配计划（JSON），但不会实际执行。审核该计划后，可使用 `--execute` 应用它，并用 `--verify` 检查进度和完成情况。
</details>

14. 用一句话解释，为什么配置了 `acks=all` 的 producer 可以在 broker 滚动重启期间不丢失数据。

<details>

<summary>显示答案</summary>

**答案：如果正在重启的 broker 是某个 partition leader，controller 会在重启继续之前从 in-sync replica (ISR) 集合中选出新的 leader，并且只要满足 `min.insync.replicas`，已提交的数据就会被保留。**

**解释：**
`acks=all` producer 会等待其消息被足够多的 replica 写入以满足 `min.insync.replicas`，然后才将其视为已提交。如果 leader 在 broker 重启前发生变化，producer 会检测到该变化，刷新其 metadata，并针对新的 leader 重试 — 可能会有短暂的延迟峰值，但已提交的数据不会丢失。使用 `acks=1` 或更低配置的 producer 没有这种保证，并有丢失传输中消息的风险。
</details>

## 实践题

15. 编写一个名为 `broker` 的 `KafkaNodePool` YAML，使用 JBOD 存储，包含 3 个 volume，每个 volume 在 gp3 上为 300Gi。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: broker
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
      - id: 2
        type: persistent-claim
        size: 300Gi
        class: gp3
        deleteClaim: false
```

**解释：**
设置 `storage.type: jbod`，并在 `volumes` 列表中定义三个 `persistent-claim` volume，每个都有唯一的 `id`（0、1、2），会为 broker 提供三个独立 volume。`deleteClaim: false` 会保护 PVC，避免 broker 被重新创建或缩减时删除它们，从而保护其中的数据。
</details>

16. 为名为 `my-cluster` 的集群创建一个 `full` 模式的 `KafkaRebalance` 资源，并写出批准生成的 rebalance proposal 的命令。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaRebalance
metadata:
  name: my-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  mode: full
```

```bash
# Check proposal generation status (PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to execute it
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

**解释：**
创建 `KafkaRebalance` CR 会使 Cruise Control 自动生成 rebalance proposal，并在 `ProposalReady` 状态等待。需要使用 `strimzi.io/rebalance=approve` annotation 才能实际执行 partition 移动。`mode: full` 会生成覆盖集群中每个 broker 的基于目标的计划。
</details>

17. 将 broker 从 3 个（ID 0、1、2）扩展到 6 个（ID 0-5）后，写出三步命令（generate → execute → verify），用于将 `orders` topic 的 partition 重新分配到包含新 broker 的完整 broker 列表中。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1) Define the topic to move
cat <<EOF > topics-to-move.json
{
  "topics": [{"topic": "orders"}],
  "version": 1
}
EOF

# 2) Generate the plan
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "0,1,2,3,4,5" \
  --generate

# 3) Execute the plan (using the generated reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --execute

# 4) Verify completion
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json \
  --verify
```

**解释：**
`--generate` 会生成一个 partition 移动计划，目标是给定的 `--broker-list`（此处为 0-5，包含新 broker）。`--execute` 会启动实际的重新分配，`--verify` 会确认重新分配已完成，并且没有剩余的副本不足 partition。只有完成此过程后，新添加的 broker 才会真正承载 partition leader/follower 角色。
</details>

---

[返回学习材料](../../../data-on-eks/kafka/03-kafka-operations.md) | [下一测验：Schema Registry](./04-schema-registry-quiz.md)
