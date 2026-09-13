# Kafka 运维测验

> **最后更新**：2026 年 9 月 12 日，Strimzi 1.2.0 / Kafka 4.3.1。

本测验检验您对 EKS 上 Strimzi 管理的 Kafka 集群的存储设计、代理扩缩容、Cruise Control 再平衡、滚动升级和故障处理的理解。

## 选择题

1. AWS 为低延迟、高 IOPS 和高持久性设计了哪种 SSD 选项？
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>显示答案</summary>

**答案：C) io2**

**解释：**
io2 Block Express 面向低延迟、高 IOPS 和持久性。最高 256,000 IOPS 需要 Nitro 等适当条件。区分 99.999% 设计持久性与 0.001% AFR。容量和 IOPS 都影响成本；应根据测量、要求和价格选择。
</details>

2. `KafkaNodePool` 上哪种存储类型将代理配置为使用多个独立卷？
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>显示答案</summary>

**答案：B) `type: jbod`**

**解释：**
JBOD 提供独立卷 ID。Kafka 4.3.1 对新日志通常优先选择分区日志较少的目录；不保证轮询或按字节均衡放置。移动现有数据是独立操作。
</details>

3. 持续保留 100MB/s 日志、保留七天且 RF=3 时，哪个公式让总容量的 30% 保持空闲？
   - A) 100MB/s × 7 天（秒数）× 3
   - B) 100MB/s × 7 天（秒数）× 3 ÷ 0.70
   - C) 100MB/s × 7 天（秒数）÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>显示答案</summary>

**答案：B) 100MB/s × 7 天（秒数）× 3 ÷ 0.70**

**解释：**
在数据大小上增加 30%，仅使总容量约 23.08% 空闲。将复制数据除以 0.70，才能保留 30% 空闲。使用持续保留/压缩日志字节数、实际保留期和独立运维开销。
</details>

4. 在 Strimzi 管理的 Kafka 集群上，操作员必须手动运行什么脚本来格式化存储卷？
   - A) 必须在每个代理手动运行 `kafka-storage.sh format`
   - B) 必须使用 `kafka-configs.sh` 应用格式化设置
   - C) 无需手动脚本——代理 Pod 启动时由 Strimzi Operator 自动处理
   - D) 必须使用 `kafka-reassign-partitions.sh --format`

<details>

<summary>显示答案</summary>

**答案：C) 无需手动脚本——代理 Pod 启动时由 Strimzi Operator 自动处理**

**解释：**
Strimzi/启动脚本管理新存储元数据所需初始化。现有数据不会在每次启动时被擦除。不要随意手动格式化 Operator 管理的卷。
</details>

5. 没有匹配的 autoRebalance 模式时，增加代理池 replicas 会发生什么？
   - A) 现有分区立即重新分布到新代理
   - B) 新代理加入集群，但现有主题分区不会自动重新分配
   - C) 新代理自动成为所有分区的领导者
   - D) 新代理仅充当控制器

<details>

<summary>显示答案</summary>

**答案：B) 新代理加入集群，但现有主题分区不会自动重新分配**

**解释：**
这描述没有匹配 autoRebalance 模式的情况。配置 add-brokers 自动化后，Strimzi 1.2 可在现有池 replicas 增加后自动再平衡。池创建/删除是不同事件。
</details>

6. 移除代理前必须满足什么数据状态要求？
   - A) 无需任何要求——Strimzi 自动排空
   - B) 必须先将待移除代理上的分区重新分配到剩余代理
   - C) 必须重启集群
   - D) 必须删除所有主题

<details>

<summary>显示答案</summary>

**答案：B) 必须先将待移除代理上的分区重新分配到剩余代理**

**解释：**
移除代理前必须安全迁出所有副本。手动流程包含内部主题；配置的 remove-brokers autoRebalance 可自动协调迁出。保留非空代理检查并验证移除 ID。
</details>

7. Cruise Control 的主要作用是什么？
   - A) 自动创建和删除主题
   - B) 收集代理负载指标并自动生成/执行基于目标的分区重新分配计划
   - C) 管理消费者组偏移提交
   - D) 自动续订 TLS 证书

<details>

<summary>显示答案</summary>

**答案：B) 收集代理负载指标并自动生成/执行基于目标的分区重新分配计划**

**解释：**
Cruise Control 根据负载/目标计算提案，并按审批/自动化策略执行。生成提案和移动数据相互独立；不要随意绕过指标不足或硬性目标失败。
</details>

8. `KafkaRebalance` 资源的 `mode` 字段中，哪种模式专注于将分区移动到新添加代理，为其分配负载？
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>显示答案</summary>

**答案：B) `add-brokers`**

**解释：**
add-brokers 针对指定新代理，需要实际 ID。目标、数据量和机架约束决定时长/影响；它不总是比 full 更快。remove-brokers 在移除前迁出代理数据。
</details>

9. 哪种模式将 Kafka 4.2.1 升级到 4.3.1，同时保留旧元数据格式以提供验证窗口？
   - A) 立即同时提高 version 和 metadataVersion
   - B) 将 version 提高到 4.3.1，保留 metadataVersion 4.2-IV1，验证后再改为 4.3-IV0
   - C) 检查二进制兼容性前先提高 metadataVersion
   - D) 删除所有数据并重启

<details>

<summary>显示答案</summary>

**答案：B) 将 version 提高到 4.3.1，保留 metadataVersion 4.2-IV1，验证后再改为 4.3-IV0**

**解释：**
这是显式保留之前 metadataVersion 以验证的运维模式。若省略，Strimzi 可在二进制升级后更新元数据。Operator 必须支持当前/目标 Kafka，后续格式更改可能阻止降级。
</details>

10. 哪种 Kubernetes 资源约束 Strimzi Kafka 集群的自愿驱逐？
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>显示答案</summary>

**答案：C) PodDisruptionBudget**

**解释：**
Strimzi 1.2 通常每集群创建一个 Kafka PDB，覆盖其各池的 Kafka Pod。它约束自愿驱逐，不约束节点/可用区故障或强制删除。
</details>

## 简答题

11. Kafka 滚动可用性检查会考虑哪个最小 ISR 配置？

<details>

<summary>显示答案</summary>

**答案：`min.insync.replicas`**

**解释：**
min.insync.replicas 是重要可用性输入，不是每次滚动更新的无条件保证。检查实际 ISR、控制器法定人数、存储/网络和客户端超时/重试。
</details>

12. 升级前，哪个组件的支持矩阵必须同时包含当前和目标 Kafka？

<details>

<summary>显示答案</summary>

**答案：Strimzi Operator**

**解释：**
验证 Strimzi 版本同时支持当前和目标 Kafka。若已支持，无需强制升级 Operator。若最新 Operator 不再支持当前 Kafka，规划中间版本和 API/CRD 迁移。
</details>

13. 实际执行分区重新分配计划前，使用 `kafka-reassign-partitions.sh` 的哪个选项针对指定代理列表生成计划？

<details>

<summary>显示答案</summary>

**答案：`--generate`**

**解释：**
--generate 打印当前和提议的分配，不执行移动。单独提取 Proposed，并审核 RF、ID、机架和容量。完成的 --verify 若无 preserve-throttles，可清除节流配置。
</details>

14. 区分 acks=all 的持久性假设与滚动更新期间的请求成功保证。

<details>

<summary>显示答案</summary>

**答案：同步副本和可用法定人数/领导者仍存在时持久性更强，但请求仍可能超时或需要重试。**

**解释：**
acks=all 在满足最小 ISR 的同时等待当前完整 ISR。同步副本以及有效领导者/法定人数/存储条件必须维持。单独处理超时、重试和重复处理。
</details>

## 实践题

15. 为新环境定义代理池示例，使用三个 300Gi gp3 卷。

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

**解释：**
这是新环境定义，不是要求缩小已扩至 500Gi 的卷。它使用第 2 部分的 gp3-kafka，并选择一个元数据卷。Retain/deleteClaim 设置不是备份。
</details>

16. 为名为 `my-cluster` 的集群创建 `full` 模式 `KafkaRebalance` 资源，并编写批准生成的再平衡提案的命令。

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

**解释：**
需启用 Cruise Control，并具有有效指标/目标。自动审批为 false：批准前检查 ProposalReady。区分手动请求与自动扩缩请求。
</details>

17. 代理扩容后，使用实际 ID 和 TLS 管理员设置，生成、提取、执行并检查 orders 重新分配。

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

**解释：**
将文件保留在运行 CLI 的环境。使用真实代理 ID 和 TLS 管理员配置，提取 Proposed 而非 Current。用 --verify --preserve-throttles 检查移动状态，再单独检查 URP/min-ISR/离线状态。移动一个主题不能证明代理已完全排空。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/03-kafka-operations.md) | [下一测验：Schema Registry](./04-schema-registry-quiz.md)
