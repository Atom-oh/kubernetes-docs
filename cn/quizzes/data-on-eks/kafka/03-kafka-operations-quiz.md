# Kafka 运维测验

> **最后更新**：October 16, 2026, Strimzi 1.3.0 / Kafka 4.3.1.

本测验旨在检验你对 EKS 上由 Strimzi 管理的 Kafka 集群的存储设计、Broker 扩缩容、Cruise Control 重新平衡、滚动升级和故障处理的理解。

## 选择题

1. AWS 为低延迟、高 IOPS 和高耐久性设计了哪种 SSD 选项？
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>显示答案</summary>

**答案：C) io2**

**说明：**
io2 Block Express 面向低延迟、高 IOPS 和高耐久性。最大 256,000 IOPS 需要满足 Nitro 等适当条件。请区分 99.999% 的设计耐久性与 0.001% 的 AFR。容量和 IOPS 都会影响成本；应依据测量结果、需求和定价进行选择。
</details>

2. `KafkaNodePool` 上哪种存储类型可配置 Broker 使用多个独立卷？
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>显示答案</summary>

**答案：B) `type: jbod`**

**说明：**
JBOD 提供独立的卷 ID。Kafka 4.3.1 通常会优先选择分区日志较少的目录来存储新日志；但这不保证采用轮询或按字节均衡的方式分配。现有数据的迁移是另一项独立操作。
</details>

3. 对于持续写入速率为 100MB/s、保留期为七天且 RF=3 的日志，哪种公式能确保总容量中有 30% 空闲？
   - A) 100MB/s × 7 天（秒数）× 3
   - B) 100MB/s × 7 天（秒数）× 3 ÷ 0.70
   - C) 100MB/s × 7 天（秒数）÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>显示答案</summary>

**答案：B) 100MB/s × 7 天（秒数）× 3 ÷ 0.70**

**说明：**
在数据大小上增加 30%，总容量中只会剩下约 23.08% 的空闲空间。将复制后的数据量除以 0.70，才能保留 30% 的空闲空间。应使用持续保留的压缩后日志字节数、实际保留期，并单独考虑运行开销。
</details>

4. 对于由 Strimzi 管理的 Kafka 集群，运维人员必须手动运行哪个脚本来格式化存储卷？
   - A) 必须在每个 Broker 上手动运行 `kafka-storage.sh format`
   - B) 必须使用 `kafka-configs.sh` 应用格式设置
   - C) 无：Broker Pod 启动时，Strimzi Operator 会自动处理此操作
   - D) 必须使用 `kafka-reassign-partitions.sh --format`

<details>

<summary>显示答案</summary>

**答案：C) 无：Broker Pod 启动时，Strimzi Operator 会自动处理此操作**

**说明：**
Strimzi/启动脚本会管理新存储元数据所需的初始化。每次启动时不会清除现有数据。不要随意手动格式化由 Operator 管理的卷。
</details>

5. 如果没有匹配的 autoRebalance 模式，增加 Broker 池的副本数会怎样？
   - A) 现有分区会立即重新分配到新 Broker 上
   - B) 新 Broker 会加入集群，但现有主题分区不会自动重新分配
   - C) 新 Broker 会自动成为所有分区的 Leader
   - D) 新 Broker 只会充当 Controller

<details>

<summary>显示答案</summary>

**答案：B) 新 Broker 会加入集群，但现有主题分区不会自动重新分配**

**说明：**
此描述适用于没有匹配的 autoRebalance 模式的情况。配置了 add-brokers 自动化后，Strimzi 1.3 可以在现有池的副本数增加后自动重新平衡。创建或删除池属于不同的事件。
</details>

6. 移除 Broker 之前，必须满足什么数据状态要求？
   - A) 无需任何操作：Strimzi 会自动清空该 Broker
   - B) 必须先将待移除 Broker 上的分区重新分配到剩余 Broker
   - C) 必须重启集群
   - D) 必须删除所有主题

<details>

<summary>显示答案</summary>

**答案：B) 必须先将待移除 Broker 上的分区重新分配到剩余 Broker**

**说明：**
移除 Broker 之前，必须安全地迁出所有副本。手动操作流程包括内部主题；配置 remove-brokers autoRebalance 后，可以自动协调迁出过程。保留非空 Broker 检查，并验证移除 ID。
</details>

7. Cruise Control 的主要作用是什么？
   - A) 自动创建和删除主题
   - B) 收集 Broker 负载指标，并自动生成/执行基于目标的分区重新分配计划
   - C) 管理消费者组偏移量提交
   - D) 自动续订 TLS 证书

<details>

<summary>显示答案</summary>

**答案：B) 收集 Broker 负载指标，并自动生成/执行基于目标的分区重新分配计划**

**说明：**
Cruise Control 会根据负载和目标计算方案，并依照审批/自动化策略执行。生成方案与迁移数据是两项独立操作；不要轻率地绕过指标不足或硬性目标失败的问题。
</details>

8. 在 `KafkaRebalance` 资源的 `mode` 字段中，哪种模式专注于将分区迁移到新添加的 Broker 上以填充其负载？
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>显示答案</summary>

**答案：B) `add-brokers`**

**说明：**
add-brokers 会针对指定的新 Broker，并且需要这些 Broker 的实际 ID。目标、数据量和机架约束会决定耗时和影响；它并不总是比 full 更快。remove-brokers 则会在移除 Broker 之前将其清空。
</details>

9. 将 Kafka 4.2.1 升级到 4.3.1，同时在验证期内保留旧元数据格式，应采用哪种方式？
   - A) 立即同时提升 version 和 metadataVersion
   - B) 将 version 提升到 4.3.1，保留 metadataVersion 4.2-IV1，然后先进行验证，再改为 4.3-IV0
   - C) 在检查二进制兼容性之前先提升 metadataVersion
   - D) 删除所有数据并重启

<details>

<summary>显示答案</summary>

**答案：B) 将 version 提升到 4.3.1，保留 metadataVersion 4.2-IV1，然后先进行验证，再改为 4.3-IV0**

**说明：**
这是显式保留先前 metadataVersion 以进行验证的运维方式。如果未设置，Strimzi 可能会在二进制升级后更新元数据。Operator 必须支持当前和目标 Kafka 版本；之后更改格式可能会导致无法降级。
</details>

10. 哪种 Kubernetes 资源会限制 Strimzi Kafka 集群的自愿驱逐？
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>显示答案</summary>

**答案：C) PodDisruptionBudget**

**说明：**
Strimzi 1.3 通常会为每个集群创建一个 Kafka PDB，涵盖该集群各池中的 Kafka Pod。它会限制自愿驱逐，但不会限制节点/AZ 故障或强制删除。
</details>

## 简答题

11. Kafka 滚动可用性检查会考虑哪项最小 ISR 配置？

<details>

<summary>显示答案</summary>

**答案：`min.insync.replicas`**

**说明：**
min.insync.replicas 是可用性评估的重要输入，但并不能无条件保证每次滚动期间的可用性。请检查实际 ISR、Controller quorum、存储/网络状况，以及客户端超时/重试设置。
</details>

12. 升级之前，哪个组件的支持矩阵必须涵盖当前和目标 Kafka 版本？

<details>

<summary>显示答案</summary>

**答案：Strimzi Operator**

**说明：**
请确认 Strimzi 版本同时支持当前和目标 Kafka 版本。如果现有版本已支持，就不必强制升级 Operator。如果最新的 Operator 不再支持当前 Kafka 版本，则应规划中间版本以及 API/CRD 迁移。
</details>

13. 实际执行分区重新分配计划之前，使用 `kafka-reassign-partitions.sh` 的哪个选项可针对指定的 Broker 列表生成计划？

<details>

<summary>显示答案</summary>

**答案：`--generate`**

**说明：**
--generate 会打印当前分配和提议的分配，但不会执行迁移。请单独提取 Proposed，并检查 RF、ID、机架和容量。完成 --verify 后，如果没有使用 preserve-throttles，可能会清除限流配置。
</details>

14. 区分 acks=all 的耐久性假设与滚动期间请求成功的保证。

<details>

<summary>显示答案</summary>

**答案：只要同步副本和可用的 quorum/Leader 仍然存在，耐久性就更有保障，但请求仍可能超时或需要重试。**

**说明：**
acks=all 会等待当前完整 ISR，同时满足最小 ISR 要求。必须保持同步副本以及可用的 Leader/quorum/存储条件。应分别处理超时、重试和重复处理问题。
</details>

## 实操题

15. 定义一个新环境的 Broker 池示例，包含三个 300Gi gp3 卷。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: broker
  namespace: kafka
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
      class: gp3-kafka
      deleteClaim: false
      kraftMetadata: shared
    - id: 1
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
    - id: 2
      type: persistent-claim
      size: 300Gi
      class: gp3-kafka
      deleteClaim: false
  resources:
    requests:
      cpu: '2'
      memory: 4Gi
    limits:
      memory: 4Gi
  template:
    pod:
      metadata:
        labels:
          docs.example.com/kafka-role: broker
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 3
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            strimzi.io/cluster: my-cluster
            docs.example.com/kafka-role: broker
```

**说明：**
这是新环境的定义，不是将已扩容到 500Gi 的卷缩小的指令。它使用 Part 2 gp3-kafka，并选择一个元数据卷。保留/删除 claim 的设置不能替代备份。
</details>

16. 为名为 `my-cluster` 的集群创建一个 `KafkaRebalance` 资源，使用 `full` 模式，并写出批准生成的重新平衡方案的命令。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaRebalance
metadata:
  name: reviewed-full-rebalance
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
  annotations:
    strimzi.io/rebalance-auto-approval: "false"
spec:
  mode: full
```

```bash
kubectl create -f rebalance-full.yaml
kubectl -n kafka wait kafkarebalance/reviewed-full-rebalance \
  --for=condition=ProposalReady --timeout=30m
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -o yaml
# Review the proposal before executing:
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

**说明：**
必须启用 Cruise Control，并配置有效的指标/目标。自动审批为 false：请在批准前检查 ProposalReady。应区分手动请求与自动扩缩容请求。
</details>

17. 扩容 Broker 后，使用实际 ID 和 TLS 管理配置，生成、提取、执行并检查 orders 的重新分配。

<details>

<summary>显示答案</summary>

**答案：**
```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set reachable TLS bootstrap}"
: "${DOCS_ADMIN_CONFIG:?Set local admin properties file}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated broker IDs}"
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose reviewed throttle bytes/second}"
cat > topics-to-move.json <<'JSON'
{"version":1,"topics":[{"topic":"orders"}]}
JSON
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json --broker-list "$DOCS_BROKER_IDS" \
  --generate > generate-output.txt
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review the exact proposal before movement:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute --throttle "$DOCS_MOVE_BYTES_PER_SEC"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

**说明：**
请将文件保存在运行 CLI 的环境中。使用真实的 Broker ID 和 TLS 管理配置，并提取 Proposed 而不是 Current。使用 --verify --preserve-throttles 检查迁移状态，然后单独检查 URP/min-ISR/离线状态。只迁移一个主题并不能证明已将 Broker 完全清空。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/03-kafka-operations.md) | [下一个测验：Schema Registry](./04-schema-registry-quiz.md)
