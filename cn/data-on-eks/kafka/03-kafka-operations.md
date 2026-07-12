# 第 3 部分：Kafka 运维

> **Supported Versions**: Strimzi 0.45+, Kafka 3.9\
> **最后更新**: July 9, 2026

一旦 Kafka cluster 通过 Strimzi Operator 部署完成，运维工作就会转向存储容量规划、broker 扩缩容、partition 重新分配以及零停机升级。本文档涵盖你在 EKS 上运行由 Strimzi 管理的 Kafka cluster 时会遇到的核心运维任务。

## 存储设计

### 选择 EBS Volume 类型：gp3 vs io2

Kafka log segment 大多是顺序写入和顺序读取，但不断增长的 consumer lag 可能会触发对较旧 segment 的随机读取。选择 EBS volume 类型时，需要考虑这种访问模式。

| 方面 | gp3 | io2 |
|--------|-----|-----|
| **计费** | 按容量计费；IOPS/throughput 单独预置 | 按 IOPS 计费（单位成本更高） |
| **吞吐量** | 125MB/s 基准，可通过独立预置提升到 1,000MB/s | 随 volume 大小和 IOPS 扩展 |
| **最大 IOPS** | 16,000 | 256,000 |
| **最适合** | 大多数 Kafka workload — throughput 受限的模式 | 突发性 consumer lag、具有大量小型随机 I/O 的延迟敏感 workload |
| **持久性（年故障率）** | 99.8–99.9% | 99.999% |

对于典型的事件流 workload，从 **gp3** 开始，并根据需要独立预置 throughput/IOPS — 它是更具成本效益的默认选择。只有当随机 I/O 占主导（许多 consumer group 同时从分散的 offset 读取）或你有严格的 p99 延迟 SLA 时，才迁移到 **io2**。

### 使用 JBOD 的多 Volume 存储

Strimzi 支持 JBOD (Just a Bunch Of Disks) 配置，其中每个 broker 使用多个独立 volume，而不是一个大型 volume。以这种方式拆分存储，可以让你跨 volume 并行化 throughput，并在不影响其余部分的情况下添加或替换单个 volume。

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

每个 `volumes` 条目上的 `id` 标识 broker 内的一个 log directory，partition 会以 round-robin 方式分布到各个 volume。`deleteClaim: false` 可以防止 broker 缩容或重新创建时 PVC 被删除。

> **注意**: 在 Strimzi 中，当 broker pod 启动时，Operator 会自动运行等同于 `kafka-storage.sh format` 的操作，因此你不需要自己运行该脚本来格式化 volume。

### 存储容量估算指南

使用以下公式估算磁盘大小：

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

例如，峰值 throughput 为 50MB/s，retention period 为 7 天（`604,800 seconds`），replication factor 为 3，并预留 30% headroom：

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

分布到 3 个 broker 上，大约每个 broker 39TB。Headroom 很重要，因为一旦磁盘利用率超过 high-water mark，Kafka broker 的性能会急剧下降（它会影响 log cleaner 和 segment rolling 行为）；如果由 `log.retention.bytes`/`log.retention.hours` 驱动的删除操作滞后，磁盘满载可能会让 broker 完全离线。始终保持至少 20–30% 的可用空间。

## Broker 和 Controller 扩缩容

### 扩容 Broker

增加 `KafkaNodePool` 上的 `replicas` 会指示 Strimzi 自动创建新的 broker pod 并将它们加入 cluster。

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

新的 broker 不会自动被选为现有 partition 的 leader 或 follower。要真正将现有 topic partition 分散到新的 broker 上，你需要单独执行 partition reassignment 步骤。

### Partition Reassignment (`kafka-reassign-partitions.sh`)

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

### 为什么缩容很危险

**Strimzi 在你缩容时不会自动将 partition 从 broker 上 drain 掉。** 在减少 `KafkaNodePool` 上的 `replicas` 之前，你必须先把位于将被移除 broker 上的每个 partition（leader 和 follower replica 都包括在内）重新分配到剩余 broker 上。跳过此步骤后，只存在于该 broker 上的 replica 会直接消失 — 最好的情况是出现 under-replicated partition，最坏的情况是数据丢失。

安全的缩容顺序是：

1. 针对不包含你要移除 broker 的 broker list，运行 `kafka-reassign-partitions.sh --generate`。
2. 使用 `--execute` 应用计划，并使用 `--verify` 确认完成（检查 under-replicated partition 为零）。
3. 只有在 reassignment 完全完成后，才减少 `KafkaNodePool.spec.replicas` 来移除 broker pod。

## 使用 Cruise Control 自动 Rebalance

Cruise Control 会持续收集 broker 级别的负载指标 — 磁盘使用率、CPU、网络 throughput — 并使用这些指标自动生成和执行 partition reassignment 计划。与其每次添加或移除 broker 时手动运行 `kafka-reassign-partitions.sh`，你可以将 rebalancing 委托给基于 goal 的自动化。

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

### 使用 `KafkaRebalance` 触发 Rebalance

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

### Rebalance 模式

| 模式 | 使用场景 |
|------|----------|
| `full`（默认） | 基于已配置的 goal，在 cluster 中的每个 broker 之间生成完整的 rebalance 计划 |
| `add-brokers` | 专注于将 partition 移动到新添加的 broker 上以填充其负载 — 比完整 rebalance 更快且范围更窄 |
| `remove-brokers` | 专注于将 partition 从你即将移除的 broker 上移走 — 在缩容前将其作为安全的 drain 步骤 |

在 scale-out 或 scale-in 后立即将 rebalance 范围限定为 `add-brokers` 或 `remove-brokers`，可以避免 `full` 模式移动不需要移动的无关 partition 所带来的网络开销和时间成本。

## 滚动升级

### Spec 变更时的自动滚动重启

当你更改 `Kafka` 或 `KafkaNodePool` CR 的 spec — resource requests/limits、config 值、volume 等 — Strimzi Operator 会检测到变更，并且**一次一个**地重启 broker pod。Operator 会协调每次重启，确保只有在每个 partition 仍满足其 `min.insync.replicas` 时才继续，从而保证重启永远不会使 partition 的可用 replica 数量低于所需阈值。

### Kafka 版本升级 — 两阶段模式

在 KRaft 模式中，没有 `inter.broker.protocol.version`/`log.message.format.version`（这些是 ZooKeeper 时代的设置）。相反，`Kafka` CR 的 `spec.kafka.version`（软件版本）和 `spec.kafka.metadataVersion`（KRaft metadata log format 版本）**不能**一起提升 — 这仍然需要**两个独立阶段**。`metadataVersion` 控制 controller quorum 用于持久化 metadata 的格式，因此在 rollout 中途旧节点和新节点混合运行时，它必须保持旧格式。

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

应用此变更会触发 broker/controller binary 到 3.9.0 的滚动替换，同时 metadata format 保持在 3.8-IV0。在新旧节点同时运行的窗口期内，这可以让它们在 controller quorum 中保持相互兼容。

**阶段 2 — 在每个节点都替换完成后提升 metadataVersion**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

只有在确认每个 broker/controller 都运行 3.9.0 后，才提升 `metadataVersion`。此变更会触发另一次 reconciliation 以采用新的 metadata format。如果你反过来操作 — 同时提升软件版本和 `metadataVersion` — 仍在运行旧 binary 的节点将无法理解新的 metadata format，并且会出现 controller quorum 通信错误。

### Strimzi Operator 版本升级

**在提升 Kafka 版本之前，先升级 Strimzi Operator 本身。** 每个 Strimzi release 都支持特定范围的 Kafka 版本，如果将 CR 改为当前运行的 Operator 不识别的 Kafka 版本，验证会失败。典型顺序是：升级 Operator → 给它时间完成 reconciliation → 升级 Kafka 软件版本（阶段 1）→ 升级 `metadataVersion`（阶段 2）。

## 故障处理基础

### PodDisruptionBudget 和 Broker Pod 驱逐

Strimzi 会自动为每个 `KafkaNodePool` 创建 `PodDisruptionBudget` (PDB)。默认情况下，它一次只允许一个 broker pod 发生 voluntary eviction — node drain、Cluster Autoscaler node replacement 以及类似操作 — 这可以防止多个 broker 同时下线并破坏 quorum 或可用性。

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### 滚动重启期间使用 `acks=all` 的 Producer

使用 `acks=all` 时，即使在 broker 滚动重启期间，producer 也能避免数据丢失。如果正在重启的 broker 是某个 partition 的 leader，controller 会在重启继续之前，从 in-sync replica (ISR) set 中选出新的 leader。Producer 会检测到 leader 变更，刷新其 metadata，并重试连接新的 leader — 可能会有短暂的延迟峰值，但只要满足 `min.insync.replicas`，就不会丢失已提交的数据。使用 `acks=1` 或更低设置的 producer，则有可能丢失在重启时尚未复制到 follower 的消息。

从 consumer 侧来看，滚动重启可能会触发 consumer group rebalance，并导致 throughput 暂时下降；但只要 offset 一直正常提交，重启完成后 consumer 会从中断处继续处理。

---

[返回主页](./)

## 测验

要测试你在本章学到的内容，请尝试 [Topic Quiz](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)。

下一部分：第 4 部分将介绍 Schema Registry — 管理 Kafka topic 的消息 schema 和兼容性策略。
