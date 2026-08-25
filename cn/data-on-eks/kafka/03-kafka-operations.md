# 第 3 部分：Kafka 运维

> **支持的版本**：Strimzi 0.45+、Kafka 3.9\
> **最后更新**：July 9, 2026

使用 Strimzi Operator 部署 Kafka 集群后，运维工作将转向存储容量规划、broker 扩缩容、分区重新分配以及零停机升级。本文档介绍了在 EKS 上运行由 Strimzi 管理的 Kafka 集群时将会遇到的核心运维任务。

## 存储设计

### 选择 EBS 卷类型：gp3 与 io2

Kafka 日志段大多按顺序写入和读取，但不断增长的 consumer lag 可能会触发针对较旧日志段的随机读取。选择 EBS 卷类型时应考虑这一访问模式。

| 方面 | gp3 | io2 |
|--------|-----|-----|
| **计费** | 按容量计费；IOPS/吞吐量单独预置 | 按 IOPS 计费（单位成本更高） |
| **吞吐量** | 基准为 125MB/s，通过独立预置最高可达 1,000MB/s | 随卷大小和 IOPS 扩展 |
| **最大 IOPS** | 16,000 | 256,000 |
| **最适用场景** | 大多数 Kafka 工作负载 — 受吞吐量限制的模式 | 突发的 consumer lag、对延迟敏感且具有大量小型随机 I/O 的工作负载 |
| **耐久性（年故障率）** | 99.8–99.9% | 99.999% |

对于典型的事件流工作负载，请从 **gp3** 开始，并按需独立预置吞吐量/IOPS — 它是更具成本效益的默认选择。仅当随机 I/O 占主导地位（许多 consumer group 同时从分散的 offset 读取）或存在严格的 p99 延迟 SLA 时，才改用 **io2**。

### 使用 JBOD 的多卷存储

Strimzi 支持 JBOD（Just a Bunch Of Disks）配置，其中每个 broker 使用多个独立卷，而不是一个大卷。以这种方式拆分存储，可在卷之间并行处理吞吐量，并可添加或替换单个卷而不影响其余卷。

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
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-encrypted
        deleteClaim: false
  resources:
    requests:
      memory: 8Gi
      cpu: "2"
    limits:
      memory: 8Gi
      cpu: "4"
```

每个 `volumes` 条目中的 `id` 标识 broker 内的一个日志目录，分区会以轮询方式分布在各卷之间。`deleteClaim: false` 可防止在 broker 缩容或重新创建时删除 PVC。

> **注意**：使用 Strimzi 时，broker pod 启动时 Operator 会自动运行等效于 `kafka-storage.sh format` 的操作，因此无需自行运行该脚本来格式化卷。

### 存储容量规划指南

使用以下公式确定磁盘大小：

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

例如，峰值吞吐量为 50MB/s、保留期为 7 天（`604,800 seconds`）、副本因子为 3，且余量为 30% 时：

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

将其分布到 3 个 broker 后，每个 broker 大约为 39TB。余量非常重要，因为 Kafka broker 一旦磁盘利用率超过高水位线，性能会急剧下降（这会影响日志清理器和日志段滚动行为）；如果由 `log.retention.bytes`/`log.retention.hours` 驱动的删除滞后，磁盘写满可能会使 broker 完全离线。始终至少保留 20–30% 的可用空间。

## Broker 和 Controller 扩缩容

### 扩容 Broker

增加 `KafkaNodePool` 上的 `replicas` 会指示 Strimzi 创建新的 broker pod，并自动将它们加入集群。

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

不会自动将新 broker 选举为现有分区的 leader 或 follower。要将现有 topic 分区实际分散到新 broker 上，仍需要单独执行分区重新分配步骤。

### 分区重新分配（`kafka-reassign-partitions.sh`）

```bash
# 1) Write the topics-to-move JSON file inside the broker pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c 'cat <<EOF > /tmp/topics-to-move.json
{
  "topics": [{"topic": "orders"}, {"topic": "payments"}],
  "version": 1
}
EOF'

# 2) Generate a reassignment plan across the full broker list, saved to a file inside the pod
kubectl exec -it my-cluster-broker-0 -n kafka -- bash -c '
  bin/kafka-reassign-partitions.sh \
    --bootstrap-server localhost:9092 \
    --topics-to-move-json-file /tmp/topics-to-move.json \
    --broker-list "0,1,2,3,4,5" \
    --generate > /tmp/generate-output.txt
  # The --generate output contains both the Current and Proposed assignment JSON,
  # so extract just the JSON under "Proposed partition reassignment configuration"
  awk "/^Proposed partition reassignment configuration/{flag=1; next} flag" /tmp/generate-output.txt > /tmp/reassignment.json
'

# 3) Apply the generated plan (reassignment.json)
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --execute

# 4) Check progress
kubectl exec -it my-cluster-broker-0 -n kafka -- \
  bin/kafka-reassign-partitions.sh \
  --bootstrap-server localhost:9092 \
  --reassignment-json-file /tmp/reassignment.json \
  --verify
```

### 为什么缩容有风险

**当你缩容时，Strimzi 不会自动从 broker 中迁出分区。** 在减少 `KafkaNodePool` 的 `replicas` 之前，必须先将位于待移除 broker 上的每个分区（包括 leader 和 follower 副本）重新分配到其余 broker。跳过此步骤，则仅存在于该 broker 上的副本会直接消失 — 最好的结果是出现副本不足的分区，最坏的结果是数据丢失。

安全的缩容顺序如下：

1. 针对不包含待移除 broker 的 broker 列表运行 `kafka-reassign-partitions.sh --generate`。
2. 使用 `--execute` 应用计划，并通过 `--verify` 确认完成（检查副本不足的分区数量是否为零）。
3. 仅在重新分配完全完成后，才减少 `KafkaNodePool.spec.replicas` 以移除 broker pod。

## 使用 Cruise Control 自动重新平衡

Cruise Control 会持续收集 broker 级别的负载指标 — 磁盘使用情况、CPU、网络吞吐量 — 并使用这些指标自动生成和执行分区重新分配计划。无需在每次添加或移除 broker 时手动运行 `kafka-reassign-partitions.sh`，你可以将重新平衡交由基于目标的自动化来处理。

### 启用 Cruise Control

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # ... existing kafka config ...
  cruiseControl:
    config:
      # Goals: keep disk/CPU/network usage even across brokers
      goals: >-
        com.linkedin.kafka.cruisecontrol.analyzer.goals.RackAwareGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.CpuCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkInboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkOutboundCapacityGoal
```

### 使用 `KafkaRebalance` 触发重新平衡

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
# Generate a rebalance proposal (not executed yet: PendingProposal → ProposalReady)
kubectl get kafkarebalance my-rebalance -n kafka -o yaml

# Approve the proposal to actually execute the rebalance
kubectl annotate kafkarebalance my-rebalance -n kafka \
  strimzi.io/rebalance=approve

# Watch progress
kubectl get kafkarebalance my-rebalance -n kafka -w
```

### 重新平衡模式

| 模式 | 使用场景 |
|------|----------|
| `full`（默认） | 根据配置的目标，在集群中的每个 broker 上生成完整的重新平衡计划 |
| `add-brokers` | 专注于将分区迁移到新添加的 broker 以填充其负载 — 比完整重新平衡更快且范围更小 |
| `remove-brokers` | 专注于将分区从即将移除的 broker 中迁出 — 在缩容前将其作为安全的排空步骤 |

刚完成扩容或缩容后，将重新平衡范围限定为 `add-brokers` 或 `remove-brokers`，可避免 `full` 模式迁移不需要移动的无关分区所产生的网络开销和时间成本。

## 滚动升级

### Spec 更改时自动滚动重启

当更改 `Kafka` 或 `KafkaNodePool` CR 的 spec — 资源 requests/limits、配置值、卷等 — Strimzi Operator 会检测到该更改，并**一次重启一个** broker pod。Operator 会协调每次重启，确保仅在每个分区仍满足其 `min.insync.replicas` 时才继续，从而确保重启绝不会使分区的可用副本数低于所需阈值。

### Kafka 版本升级 — 两阶段模式

在 KRaft 模式中，没有 `inter.broker.protocol.version`/`log.message.format.version`（它们是 ZooKeeper 时代的设置）。相反，`Kafka` CR 的 `spec.kafka.version`（软件版本）和 `spec.kafka.metadataVersion`（KRaft 元数据日志格式版本）**不能**同时升级 — 这仍然需要**两个独立阶段**。`metadataVersion` 控制 controller quorum 用于持久化元数据的格式，因此在滚动发布中旧节点与新节点混合的期间，必须保持旧格式。

**阶段 1 — 仅升级软件版本**

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.9.0
    # Keep metadataVersion pinned to the old format
    metadataVersion: 3.8-IV0
```

应用此配置会将 broker/controller 二进制文件滚动替换为 3.9.0，同时元数据格式保持在 3.8-IV0。在两者同时运行的期间，这可使 controller quorum 中的旧节点和新节点彼此兼容。

**阶段 2 — 在每个节点都被替换后升级 metadataVersion**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

仅在确认每个 broker/controller 都运行 3.9.0 后才升级 `metadataVersion`。这一更改会触发另一次协调以采用新的元数据格式。如果颠倒顺序 — 同时升级软件版本和 `metadataVersion` — 仍在运行旧二进制文件的节点将无法理解新元数据格式，并会出现 controller quorum 通信错误。

### Strimzi Operator 版本升级

**在升级 Kafka 版本前，先升级 Strimzi Operator 本身。** 每个 Strimzi 版本支持特定范围的 Kafka 版本，而将 CR 更改为正在运行的 Operator 不识别的 Kafka 版本将导致验证失败。典型顺序为：升级 Operator → 等待其完成协调 → 升级 Kafka 软件版本（阶段 1）→ 升级 `metadataVersion`（阶段 2）。

## 故障处理基础

### PodDisruptionBudget 和 Broker Pod 驱逐

Strimzi 会为每个 `KafkaNodePool` 自动创建一个 `PodDisruptionBudget`（PDB）。默认情况下，它一次只允许一个 broker pod 进行自愿驱逐 — 节点排空、Cluster Autoscaler 节点替换等 — 从而防止多个 broker 同时下线并破坏 quorum 或可用性。

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### 滚动重启期间的 `acks=all` Producer

使用 `acks=all` 时，即使在 broker 滚动重启期间，producer 也能免受数据丢失影响。如果正在重启的 broker 是某个分区的 leader，controller 会在重启继续前从同步副本（ISR）集合中选举新的 leader。producer 会检测到 leader 更改、刷新其元数据并向新 leader 重试 — 可能会出现短暂的延迟峰值，但只要满足 `min.insync.replicas`，就不会丢失任何已提交的数据。使用 `acks=1` 或更低值的 producer 存在丢失消息的风险，因为这些消息在重启时可能尚未复制到 follower。

从 consumer 角度来看，滚动重启可能触发 consumer group 重新平衡并导致吞吐量暂时下降，但只要 offset 一直正常提交，重启完成后 consumer 就会从中断处继续处理。

---

[返回主页](./README.md)

## 测验

要测试本章所学内容，请尝试[主题测验](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)。

接下来：第 4 部分将介绍 Schema Registry — 管理 Kafka topic 的消息 schema 和兼容性策略。
