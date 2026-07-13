# Part 3: Kafka Operations

> **Supported Versions**: Strimzi 0.45+, Kafka 3.9\
> **最終更新**: July 9, 2026

Kafka cluster が Strimzi Operator でデプロイされると、運用作業は storage capacity planning、broker scaling、partition reassignment、zero-downtime upgrade に移ります。このドキュメントでは、EKS 上で Strimzi-managed Kafka cluster を運用する際に直面する主要な運用タスクを扱います。

## Storage Design

### Choosing an EBS Volume Type: gp3 vs io2

Kafka log segment は主に sequential に書き込み・読み取りされますが、consumer lag が増大すると、古い segment に対する random read が発生することがあります。その access pattern を念頭に置いて EBS volume type を選択してください。

| Aspect | gp3 | io2 |
|--------|-----|-----|
| **Billing** | Capacity-based; IOPS/throughput provisioned separately | IOPS-based (higher per-unit cost) |
| **Throughput** | 125MB/s baseline, up to 1,000MB/s with independent provisioning | Scales with volume size and IOPS |
| **Max IOPS** | 16,000 | 256,000 |
| **Best fit** | Most Kafka workloads — throughput-bound patterns | Spiky consumer lag, latency-sensitive workloads with heavy small random I/O |
| **Durability (annual failure rate)** | 99.8–99.9% | 99.999% |

一般的な event-streaming workload では、まず **gp3** から始め、必要に応じて throughput/IOPS を個別に provision します。これはより cost-effective な default です。random I/O が支配的な場合（多数の consumer group が scattered offset から同時に読み取る場合）や、厳格な p99 latency SLA がある場合にのみ **io2** に移行してください。

### Multi-Volume Storage with JBOD

Strimzi は JBOD (Just a Bunch Of Disks) configuration をサポートしており、各 broker は 1 つの大きな volume ではなく、複数の独立した volume を使用します。この方法で storage を分割すると、volume 間で throughput を parallelize でき、残りに影響を与えずに個別の volume を追加または置換できます。

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

各 `volumes` entry の `id` は broker 内の log directory を識別し、partition は round-robin 方式で volume 間に分散されます。`deleteClaim: false` は、broker が scale down または recreate されたときに PVC が削除されないよう保護します。

> **Note**: Strimzi では、broker pod の起動時に Operator が `kafka-storage.sh format` 相当を自動的に実行するため、volume を format するためにその script を自分で実行する必要はありません。

### Storage Sizing Guidance

disk size は次の式で見積もります。

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

たとえば、peak throughput が 50MB/s、retention period が 7 日（`604,800 seconds`）、replication factor が 3、headroom が 30% の場合:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

3 つの broker に分散すると、broker あたりおよそ 39TB になります。headroom は重要です。Kafka broker は disk utilization が high-water mark を超えると急激に劣化し（log cleaner と segment-rolling の挙動に影響します）、`log.retention.bytes`/`log.retention.hours` による削除が追いつかない場合、disk full によって broker が完全に offline になる可能性があります。常に少なくとも 20–30% の free space を確保してください。

## Broker and Controller Scaling

### Scaling Out Brokers

`KafkaNodePool` の `replicas` を増やすと、Strimzi は新しい broker pod を作成し、それらを cluster に自動的に参加させます。

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

新しい broker は、既存 partition の leader または follower として自動的に選出されるわけではありません。既存 topic partition を実際に新しい broker に分散するには、別途 partition reassignment step が必要です。

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

### Why Scaling Down Is Dangerous

**Strimzi は scale down 時に broker から partition を自動的に drain しません。** `KafkaNodePool` の `replicas` を減らす前に、削除される broker 上に存在するすべての partition（leader と follower replica の両方）を、残りの broker に再割り当てする必要があります。この step を省略すると、その broker にのみ存在していた replica は単に消失します。最良の場合でも under-replicated partition が残り、最悪の場合は data loss につながります。

安全な scale-down sequence は次のとおりです。

1. 削除する broker を除外した broker list に対して `kafka-reassign-partitions.sh --generate` を実行します。
2. `--execute` で plan を適用し、`--verify` で完了を確認します（under-replicated partition が zero であることを確認します）。
3. reassignment が完全に完了した後でのみ、`KafkaNodePool.spec.replicas` を減らして broker pod を削除します。

## Automated Rebalancing with Cruise Control

Cruise Control は broker-level load metrics（disk usage、CPU、network throughput）を継続的に収集し、それを使って partition reassignment plan を自動的に生成・実行します。broker を追加または削除するたびに `kafka-reassign-partitions.sh` を手動で実行する代わりに、goal-based automation に rebalancing を委任できます。

### Enabling Cruise Control

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

### Triggering a Rebalance with `KafkaRebalance`

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

### Rebalance Modes

| Mode | Use case |
|------|----------|
| `full` (default) | Generates a full rebalance plan across every broker in the cluster, based on the configured goals |
| `add-brokers` | Focuses on moving partitions onto newly added brokers to fill their load — faster and narrower in scope than a full rebalance |
| `remove-brokers` | Focuses on moving partitions off brokers you're about to remove — use this as the safe drain step before scaling down |

scale-out または scale-in の直後に、rebalance scope を `add-brokers` または `remove-brokers` に限定すると、移動する必要のない無関係な partition を `full` mode が移動することによる network overhead と time cost を避けられます。

## Rolling Upgrades

### Automatic Rolling Restarts on Spec Changes

`Kafka` または `KafkaNodePool` CR の spec（resource requests/limits、config values、volumes など）を変更すると、Strimzi Operator は変更を検出し、broker pod を **1 つずつ** restart します。Operator は各 restart を調整し、すべての partition が引き続き `min.insync.replicas` を満たしている間のみ処理を進めます。これにより、restart によって partition の available replica count が required threshold を下回ることがないよう保証されます。

### Kafka Version Upgrades — The Two-Phase Pattern

KRaft mode には `inter.broker.protocol.version`/`log.message.format.version` はありません（これらは ZooKeeper-era settings です）。代わりに、`Kafka` CR の `spec.kafka.version`（software version）と `spec.kafka.metadataVersion`（KRaft metadata log format version）を同時に bump しては**いけません**。これには依然として **2 つの separate phase** が必要です。`metadataVersion` は controller quorum が metadata を永続化するために使用する format を制御するため、rollout 途中で old node と new node が混在している間は古い format のままにしておく必要があります。

**Phase 1 — Upgrade the software version only**

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

これを適用すると、broker/controller binary が 3.9.0 へ rolling replacement されますが、metadata format は 3.8-IV0 のまま維持されます。これにより、両方が稼働している期間中、controller quorum 内で old node と new node の互換性が保たれます。

**Phase 2 — Bump metadataVersion after every node is replaced**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

すべての broker/controller が 3.9.0 で稼働していることを確認した後でのみ、`metadataVersion` を bump してください。この変更により、新しい metadata format を採用するための別の reconciliation が trigger されます。順序を逆にして software version と `metadataVersion` を同時に bump すると、古い binary を実行している node は新しい metadata format を理解できず、controller quorum communication error が発生します。

### Strimzi Operator Version Upgrades

**Kafka version を bump する前に、Strimzi Operator 自体を upgrade してください。** 各 Strimzi release は特定範囲の Kafka version をサポートしており、実行中の Operator が認識しない Kafka version に CR を変更すると validation に失敗します。一般的な順序は、Operator を upgrade → reconciliation が完了するまで待機 → Kafka software version を upgrade（Phase 1）→ `metadataVersion` を upgrade（Phase 2）です。

## Failure Handling Basics

### PodDisruptionBudget and Broker Pod Eviction

Strimzi は各 `KafkaNodePool` に対して `PodDisruptionBudget` (PDB) を自動的に作成します。default では、一度に voluntary eviction（node drain、Cluster Autoscaler node replacement など）を受けられる broker pod は 1 つだけです。これにより、複数の broker が同時に停止して quorum や availability が損なわれることを防ぎます。

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### `acks=all` Producers During Rolling Restarts

`acks=all` の場合、broker rolling restart 中であっても producer は data loss から保護されます。restart される broker が partition の leader だった場合、restart が進む直前に controller は in-sync replica (ISR) set から新しい leader を選出します。producer は leader change を検出し、metadata を refresh し、新しい leader に対して retry します。一時的な latency spike が発生することはありますが、`min.insync.replicas` が満たされている限り、committed data は失われません。`acks=1` 以下を使用している producer は、restart 時点で follower にまだ replicated されていなかった message を失うリスクがあります。

consumer 側では、rolling restart によって consumer group rebalance と throughput の一時的な低下が発生することがありますが、offset が通常どおり committed されていれば、restart 完了後に consumer は中断した場所から処理を再開します。

---

[メインページに戻る](./)

## Quiz

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md) を試してください。

次は: Part 4 で Schema Registry を扱います。Kafka topic の message schema と compatibility strategy の管理について説明します。
