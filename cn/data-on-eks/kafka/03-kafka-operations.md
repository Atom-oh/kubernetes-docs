# 第 3 部分：Kafka 运维

> **最后更新**：2026 年 9 月 12 日，Strimzi 1.2.0 / Kafka 4.3.1。
> **验证**：当前发布版本的文档/源代码、本地 CRD/合并补丁检查、提案生成/JSON 提取、Decimal 计算和 CLI 选项。未执行 Kafka 重新分配、升级或 AWS 卷更改。

本章假定已部署[第 2 部分](./02-strimzi-operator.md)中启用身份验证的 Kafka 和仅含代理的池。运维命令可能移动真实分区并更改资源：执行前请检查当前设置、放置和提案。不要将代理扩缩容流程原样应用于控制器角色池。

## 1. 存储性能和持久性

消费者积压并不意味着每次读取都是随机读取。即使顺序读取历史数据，当消费者交错读取不同范围或超出页缓存时，也可能增加物理 I/O 和尾延迟。请测量 IOPS、吞吐量、队列延迟、缓存命中率和实例 EBS 限制。

| 特性 | gp3 | io2 Block Express |
| --- | --- | --- |
| 包含的基准性能 | 3,000 IOPS / 125 MiB/s | 性能随预置 IOPS 而定 |
| 卷最大 IOPS | 80,000 | Nitro 上为 256,000 |
| 卷最大吞吐量 | 2,000 MiB/s | 4,000 MiB/s |
| 最大容量 | 64 TiB | 64 TiB |
| 公布的设计持久性 | 99.8–99.9% | 99.999% |
| 公布的 AFR 上限 | 0.2% | 0.001% |

这些是卷的设计指标，并非 Kafka 服务 SLA，也不保证能抵御任意故障。最大性能对卷大小、IOPS 比率和实例有要求。Outposts gp3 和非 Nitro io2 的限制不同。

存储容量也是账单的一部分。还要评估超出所含基准的 gp3 性能和预置 io2 IOPS。根据延迟/持久性要求、测量结果和当前区域价格选择。io2 并非仅按 IOPS 计费，严重的消费者积压也不意味着必然需要 io2。

## 2. 保留策略和可用空间

根据**保留的压缩日志字节数**和实际保留策略进行估算。将短暂峰值当作持续七天的速率会高估存储。分别计算不同主题的保留/复制要求，并考虑压缩整理、索引、内部主题和重新分配期间的临时副本。

合成场景中，以 **50 MB/s（10⁶ 字节/秒）** 持续七天，RF=3 时会产生 90.72 TB 的复制日志。

| 解释 | 容量 | 实际空闲比例 |
| --- | --- | --- |
| 在数据大小上增加 30% | 117.936 TB | 约 23.08% |
| 保持总磁盘容量的 30% 空闲 | 129.6 TB，约 117.87 TiB | 30% |

之前约 118 TB 的计算适用于第一种解释。第二种使用 `data / (1 - 0.30)`。将 129.6 TB 平均分到三个代理，每个为 43.2 TB，但实际分区倾斜仍然重要。这些是计算示例，并非第 2 部分实验 PVC 的容量建议。

**`storage-sizing.py`**

```python
"""Illustrative storage calculation, not measured traffic or a volume recommendation."""
from decimal import Decimal
import json

retained_log_bytes_per_second = Decimal("50000000")  # 50 decimal MB/s, sustained
retention_seconds = Decimal(7 * 24 * 60 * 60)
replication_factor = Decimal(3)
broker_count = Decimal(3)
margin = Decimal("0.30")
replicated_bytes = retained_log_bytes_per_second * retention_seconds * replication_factor
additive_capacity = replicated_bytes * (1 + margin)
free_space_capacity = replicated_bytes / (1 - margin)

print(json.dumps({
    "replicated_log_TB": str(replicated_bytes / Decimal(10**12)),
    "capacity_with_30_percent_added_TB": str(additive_capacity / Decimal(10**12)),
    "free_percent_with_added_margin": str((1 - replicated_bytes / additive_capacity) * 100),
    "capacity_with_30_percent_free_TB": str(free_space_capacity / Decimal(10**12)),
    "capacity_with_30_percent_free_TiB": str(free_space_capacity / Decimal(2**40)),
    "average_per_broker_TB": str(free_space_capacity / broker_count / Decimal(10**12)),
    "assumptions": [
        "Sustained retained-log bytes after compression; not a short traffic peak.",
        "No separate allowance here for indexes, internal topics, compaction or temporary reassignment copies.",
        "Per-broker division assumes equal data placement; measure actual skew."
    ]
}, indent=2))
```

## 3. JBOD 扩容和更改

Kafka 4.3.1 在放置新日志时通常优先选择分区日志较少的目录。这不是简单的轮询或按字节均衡放置。添加磁盘不会自动重新分布现有数据。

此合并补丁将第 2 部分的卷 0 从 100Gi 扩为 500Gi，并添加卷 1。它会**替换整个 volumes 数组**：请保留其他现有卷，不要原样应用。现有拓扑/资源设置保持不变。

**`storage-expand.patch.yaml`**

```yaml
# For the Part 2 broker pool with one 100Gi volume (id 0).
# Merge patch replaces the entire volumes array; preserve every existing volume.
spec:
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
        kraftMetadata: shared
      - id: 1
        type: persistent-claim
        size: 500Gi
        class: gp3-kafka
        deleteClaim: false
```

```bash
kubectl -n kafka get kafkanodepool broker -o yaml > broker-before.yaml
kubectl -n kafka patch kafkanodepool broker --type=merge \
  --patch-file storage-expand.patch.yaml
kubectl -n kafka get pvc -l strimzi.io/cluster=my-cluster
```

扩容取决于 StorageClass/CSI 和文件系统。PVC 缩容、更改存储类和卷 ID 不属于此操作。不要为两个卷都指定 kraftMetadata: shared。

移除磁盘前，请检查副本和元数据放置并迁出数据。Strimzi 1.2 通过 remove-disks 再平衡模式支持代理内的 JBOD 数据移动，该模式有自己的字段和前提条件。deleteClaim: false/Retain 不是备份，也不能证明可以恢复。不要对 Operator 管理的数据手动运行 kafka-storage.sh format。

## 4. 代理扩缩容：手动和自动方式

这些流程针对**仅含代理的池**。Strimzi 1.2 配置静态控制器法定人数；不要以同样方式扩缩控制器角色池。上游 Kafka 的动态法定人数能力与 Operator 对该能力的支持是不同的事。

| 配置 | 现有池中的副本数量更改 |
| --- | --- |
| 无匹配的 autoRebalance 模式 | 添加代理和移动现有副本是独立操作 |
| `add-brokers` autoRebalance | 扩容后自动重新分布 |
| `remove-brokers` autoRebalance | 缩容期间自动协调副本迁出 |

自动化响应的是**现有池的 replicas 更改**。池的创建/删除不是相同的触发条件。使用 Kafka 4.3+ 时，自动缩容还会封锁代理，防止迁出期间分配新副本。

### 手动扩容

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

仅有 Running 状态的 Pod 还不够：请验证 Operator 的当前 generation、代理注册、ISR 和容量。节点 ID 跨整个集群分配；不要假定 ID 为 0–5 或存在 my-cluster-broker-0 Pod。

### 手动缩容

确定实际要移除的 ID，并迁出**所有副本，包括内部主题**。仅移动 orders/payments 不能证明代理已清空。在减少 replicas 之前，验证完成情况、剩余 RF/ISR、机架分布和容量。

strimzi.io/remove-node-ids 可以选择 ID，但无效范围可能回退到默认选择：请与当前 nodeIds 比较。保持启用 Strimzi 的非空代理缩容检查。绕过检查来移除仍含数据的代理不是基准运维流程。

## 5. Cruise Control 提案和审批

本示例默认采用手动审批。在保留现有 Kafka 配置的同时添加 Cruise Control。不要通过随意指定 goals 列表而遗漏默认硬性目标，也不要将 skipHardGoalCheck 作为通用默认设置启用。

**`cruise-control.patch.yaml`**

```yaml
spec:
  cruiseControl: {}
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file cruise-control.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

**`rebalance-full.yaml`**

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
# Review optimizationResult, movement volume, goals, capacity and expected impact first.
kubectl -n kafka annotate kafkarebalance reviewed-full-rebalance \
  strimzi.io/rebalance=approve --overwrite
kubectl -n kafka get kafkarebalance reviewed-full-rebalance -w
```

指标样本不足或目标不可行都可能阻止进入 ProposalReady。审批前请审核数据移动量、目标、机架和容量。区分手动创建的 auto-approval=false 请求与自动扩缩容生成的请求。如果之前的请求已存在，请为新更改使用唯一名称。

| 模式 | 用途 |
| --- | --- |
| `full` | 在集群范围内基于目标重新分布 |
| `add-brokers` | 将副本移动到指定的新代理 |
| `remove-brokers` | 从指定代理迁出副本 |
| `remove-disks` | 从代理内的 JBOD 卷迁出副本 |

添加/移除模式需要代理 ID。范围更窄并不保证执行更快或影响更小。此辅助程序根据代理池快照验证 ID，且**仅创建提案 CR JSON**。它不评估容量、ISR/机架安全性，也不调用 API。

**`rebalance_request.py`**

```python
"""Generate a manual KafkaRebalance proposal from a broker pool snapshot; no API calls."""
import argparse
import json
from pathlib import Path


def request(pool, mode, broker_ids):
    if pool.get("kind") != "KafkaNodePool" or pool.get("spec", {}).get("roles") != ["broker"]:
        raise ValueError("Use a broker-only KafkaNodePool snapshot")
    metadata = pool.get("metadata", {})
    namespace = metadata.get("namespace")
    cluster = metadata.get("labels", {}).get("strimzi.io/cluster")
    if not namespace or not cluster:
        raise ValueError("The pool must include namespace and cluster label")
    known = pool.get("status", {}).get("nodeIds", [])
    if not known or any(type(value) is not int or value < 0 for value in known):
        raise ValueError("Read a fresh pool snapshot with valid status.nodeIds")
    if mode not in ("add-brokers", "remove-brokers"):
        raise ValueError("Select add-brokers or remove-brokers")
    if not broker_ids or len(broker_ids) != len(set(broker_ids)):
        raise ValueError("Supply distinct broker IDs")
    if any(type(value) is not int or value not in known for value in broker_ids):
        raise ValueError("Every selected broker must belong to the supplied pool")
    return {
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaRebalance",
        "metadata": {
            "name": f"reviewed-{mode}", "namespace": namespace,
            "labels": {"strimzi.io/cluster": cluster},
            "annotations": {"strimzi.io/rebalance-auto-approval": "false"},
        },
        "spec": {"mode": mode, "brokers": sorted(broker_ids)},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--mode", choices=["add-brokers", "remove-brokers"], required=True)
    parser.add_argument("--brokers", nargs="+", type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(request(json.loads(args.pool.read_text()), args.mode, args.brokers), indent=2))
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"Cannot create proposal: {error}\n")
```

```bash
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
# Set actual broker IDs from the snapshot, not controller IDs.
DOCS_BROKER_ID="REPLACE_WITH_VERIFIED_BROKER_ID"
python3 rebalance_request.py --pool broker-pool.json \
  --mode remove-brokers --brokers "$DOCS_BROKER_ID" > remove-proposal.json
python3 -m json.tool remove-proposal.json
# Review the generated proposal before creating/approving it.
```

### 可选：现有池的自动再平衡

此配置可以**在 replicas 更改后，无需另行手动审批就移动数据**。仅在已定义运维策略/目标的情况下启用。失败后也可能出现 status.autoRebalance.state=Idle；请同时检查生成的 KafkaRebalance 结果和 Kafka 状态。

**`auto-rebalance.patch.yaml`**

```yaml
# Optional: enables automatic partition movement on existing pool replica changes.
spec:
  cruiseControl:
    autoRebalance:
      - mode: add-brokers
      - mode: remove-brokers
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file auto-rebalance.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get kafkarebalances -l strimzi.io/cluster=my-cluster
```

## 6. 手动 Kafka CLI 替代方案

将 JSON 文件和管理员配置放在运行 CLI 的同一环境中。本地文件不会自动在 kubectl exec 内可用。客户端需要访问所有公布的端点，并具有获准执行管理操作的 TLS/SASL 身份。第 2 部分的 orders 应用用户不是管理员。

本示例仅针对 orders。它不是移除代理所需的完整清单。

```json
{
  "version": 1,
  "topics": [{"topic": "orders"}]
}
```

```bash
set -euo pipefail
: "${DOCS_BOOTSTRAP:?Set a reachable TLS bootstrap endpoint}"
: "${DOCS_ADMIN_CONFIG:?Set the local admin client.properties path}"
: "${DOCS_BROKER_IDS:?Set verified comma-separated target broker IDs}"
# Save the JSON above as topics-to-move.json in this environment.
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --topics-to-move-json-file topics-to-move.json \
  --broker-list "$DOCS_BROKER_IDS" --generate > generate-output.txt
```

--generate 同时打印 Current 和 Proposed JSON。保留原始输出，作为之前放置情况的记录，然后仅将 Proposed 提取到新文件。辅助程序拒绝覆盖现有输出，因此新计划应使用新文件名。

**`extract_reassignment.py`**

```python
"""Extract Kafka 4.3 --generate's proposal; never execute reassignment."""
import argparse
import json
from pathlib import Path

MARKER = "Proposed partition reassignment configuration"


def extract(text):
    if text.count(MARKER) != 1:
        raise ValueError("Expected exactly one proposal marker; inspect the command output")
    proposal, _ = json.JSONDecoder().raw_decode(text.split(MARKER, 1)[1].lstrip())
    if (not isinstance(proposal, dict) or type(proposal.get("version")) is not int
            or proposal["version"] != 1 or not isinstance(proposal.get("partitions"), list)
            or not proposal["partitions"]):
        raise ValueError("Expected a nonempty version-1 reassignment proposal")
    seen = set()
    for entry in proposal["partitions"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid partition entry")
        topic, partition, replicas = entry.get("topic"), entry.get("partition"), entry.get("replicas")
        if not isinstance(topic, str) or not topic or type(partition) is not int or partition < 0:
            raise ValueError("Invalid topic/partition")
        if (topic, partition) in seen:
            raise ValueError("Duplicate topic/partition")
        seen.add((topic, partition))
        if (not isinstance(replicas, list) or not replicas
                or any(type(broker) is not int or broker < 0 for broker in replicas)
                or len(replicas) != len(set(replicas))):
            raise ValueError("Invalid replica list")
        if "log_dirs" in entry:
            if (not isinstance(entry["log_dirs"], list) or len(entry["log_dirs"]) != len(replicas)
                    or not all(isinstance(directory, str) for directory in entry["log_dirs"])):
                raise ValueError("Log directory and replica lists must have equal lengths")
    return proposal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        proposal = extract(args.input.read_text())
        with args.output.open("x") as stream:
            json.dump(proposal, stream, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError, AttributeError) as error:
        parser.exit(1, f"Proposal extraction failed: {error}\n")
```

```bash
python3 extract_reassignment.py generate-output.txt reassignment.json
python3 -m json.tool reassignment.json
# Review topic coverage, replica order/count, broker IDs, racks and capacity.
: "${DOCS_MOVE_BYTES_PER_SEC:?Choose the reviewed movement throttle in bytes/second}"
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --execute \
  --throttle "$DOCS_MOVE_BYTES_PER_SEC"

# Status check without removing configured throttles:
kafka-reassign-partitions.sh \
  --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --reassignment-json-file reassignment.json --verify --preserve-throttles
```

辅助程序验证的是 JSON 结构，不验证代理是否存在、RF 是否保留、机架是否均衡或分区清单是否完整。

--verify 检查指定的重新分配/日志目录移动。**不使用 --preserve-throttles 时，完成验证可能会清除代理/主题节流设置，因此该操作并非纯只读。** 请与共享这些限制的其他工作协调清理。验证也不是完整的副本不足/离线分区健康检查。

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. 版本升级

选择同时支持**当前和目标 Kafka 版本**的 Operator 组合。如果它已同时支持两者，无需仅为升级顺序而升级 Operator。如果最新 Operator 不再支持当前 Kafka 版本，应规划受支持的中间版本和 API 转换，而不是直接安装。

### 软件和 metadataVersion

省略 metadataVersion 时，Strimzi 可以在升级 Kafka 二进制文件后自动将其更新为默认值。在一次更新中更改两个字段并不必然破坏法定人数。

显式保留之前的 metadataVersion 可以在提高该值之前提供验证/恢复决策窗口。本示例在 Strimzi 1.2 下将**现有 Kafka 4.2.1 / 元数据 4.2-IV1** 集群升级到 4.3.1。它不是要求降低第 2 部分中已经使用 4.3.1 的实验集群的元数据版本。

**`upgrade-binaries.patch.yaml`**

```yaml
# Only for an existing Kafka 4.2.1 cluster currently using metadata 4.2-IV1.
spec:
  kafka:
    version: 4.3.1
    metadataVersion: 4.2-IV1
```

```bash
kubectl -n kafka get kafka my-cluster -o yaml > kafka-before-upgrade.yaml
# Check current version, metadataVersion and any custom image override first.
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-binaries.patch.yaml
kubectl -n kafka get pods -l 'strimzi.io/cluster=my-cluster,strimzi.io/pool-name' \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.containers[*].image'
kubectl -n kafka get kafka my-cluster -o yaml
```

同时检查 status.kafkaVersion、status.kafkaMetadataVersion、status.operatorLastSuccessfulVersion、generation 和实际 Pod 镜像。自定义 Kafka、Connect 或 MirrorMaker 镜像也必须准备兼容版本。

验证客户端和恢复计划后，可在合适时提高元数据版本。新元数据/功能可能阻止降级；Git 回滚不能保证恢复。

**`upgrade-metadata.patch.yaml`**

```yaml
# Apply only after validating the completed binary upgrade and recovery plan.
spec:
  kafka:
    metadataVersion: 4.3-IV0
```

```bash
kubectl -n kafka patch kafka my-cluster --type=merge \
  --patch-file upgrade-metadata.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
```

并非每种 spec 更改都会重启 Pod：动态 Kafka 配置或受支持的卷扩容可能采用其他路径。需要重启时，Operator 的可用性检查也不绝对保证零停机/零损失。请观察数据状态、ISR、控制器法定人数、客户端超时和重试。

## 8. PDB 和故障处理

Strimzi 1.2 的默认 Kafka PDB 是**每个 Kafka 集群一个，覆盖其各节点池中的 Kafka Pod**，并非每个池一个。如果生成设置或自定义 PDB 不同，请检查实际选择器和 minAvailable/maxUnavailable。

PDB 约束自愿驱逐。它们不能防止节点/可用区故障、直接删除 Pod 或所有 Operator 操作。min.insync.replicas 不是能防止一切数据丢失的单一开关。

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

acks=all 在满足同步副本假设的情况下提供更强持久性，但不保证每个应用请求都成功。重启期间，应为领导者/协调器变化、超时、重试和重复处理做好计划。代理重启不一定会让每个消费者组整体停止。

Strimzi Drain Cleaner 等附加组件具有各自支持的模式/PDB 行为。不要仅因操作失败就删除终结器或缩容检查；应先检查原因及剩余的数据/元数据副本。

## 后续步骤和参考资料

- [Schema Registry](./04-schema-registry.md)
- [Kafka 概述](./README.md)
- [测验](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Strimzi 1.2 运维](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kafka 4.3 设计](https://kafka.apache.org/43/design/design/)
- [Kafka 4.3.1 日志目录选择](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Kafka 重新分配命令实现](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [EBS 定价](https://aws.amazon.com/ebs/pricing/)
