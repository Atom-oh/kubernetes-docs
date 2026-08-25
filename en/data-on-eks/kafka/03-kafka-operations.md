# Part 3: Kafka Operations

> **Supported Versions**: Strimzi 0.45+, Kafka 3.9\
> **Last Updated**: July 9, 2026

Once a Kafka cluster is deployed with the Strimzi Operator, the operational work shifts to storage capacity planning, broker scaling, partition reassignment, and zero-downtime upgrades. This document covers the core operational tasks you'll face running a Strimzi-managed Kafka cluster on EKS.

## Storage Design

### Choosing an EBS Volume Type: gp3 vs io2

Kafka log segments are mostly written and read sequentially, but growing consumer lag can trigger random reads against older segments. Pick your EBS volume type with that access pattern in mind.

| Aspect | gp3 | io2 |
|--------|-----|-----|
| **Billing** | Capacity-based; IOPS/throughput provisioned separately | IOPS-based (higher per-unit cost) |
| **Throughput** | 125MB/s baseline, up to 1,000MB/s with independent provisioning | Scales with volume size and IOPS |
| **Max IOPS** | 16,000 | 256,000 |
| **Best fit** | Most Kafka workloads — throughput-bound patterns | Spiky consumer lag, latency-sensitive workloads with heavy small random I/O |
| **Durability (annual failure rate)** | 99.8–99.9% | 99.999% |

For typical event-streaming workloads, start with **gp3** and provision throughput/IOPS independently as needed — it's the more cost-effective default. Only move to **io2** when random I/O dominates (many consumer groups reading from scattered offsets simultaneously) or when you have a strict p99 latency SLA.

### Multi-Volume Storage with JBOD

Strimzi supports JBOD (Just a Bunch Of Disks) configurations, where each broker uses multiple independent volumes instead of one large volume. Splitting storage this way lets you parallelize throughput across volumes and add or replace individual volumes without touching the rest.

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

The `id` on each `volumes` entry identifies a log directory within the broker, and partitions are distributed across volumes in round-robin fashion. `deleteClaim: false` protects the PVCs from being deleted when a broker is scaled down or recreated.

> **Note**: With Strimzi, the Operator automatically runs the equivalent of `kafka-storage.sh format` when a broker pod starts, so you don't need to run that script yourself to format volumes.

### Storage Sizing Guidance

Size your disks using this formula:

```
Required disk capacity = retention period × peak throughput (bytes/sec) × replication factor × (1 + headroom ratio)
```

For example, with a peak throughput of 50MB/s, a 7-day retention period (`604,800 seconds`), a replication factor of 3, and 30% headroom:

```
50MB/s × 604,800s × 3 × 1.3 ≈ 118TB (cluster total)
```

Spread across 3 brokers, that's roughly 39TB per broker. Headroom matters because Kafka brokers degrade sharply once disk utilization crosses a high-water mark (it affects log cleaner and segment-rolling behavior), and if deletion driven by `log.retention.bytes`/`log.retention.hours` falls behind, a full disk can take a broker offline entirely. Keep at least 20–30% free space at all times.

## Broker and Controller Scaling

### Scaling Out Brokers

Increasing `replicas` on a `KafkaNodePool` tells Strimzi to create new broker pods and join them to the cluster automatically.

```bash
kubectl patch kafkanodepool broker -n kafka --type=merge \
  -p '{"spec":{"replicas":6}}'

# Confirm the new brokers joined the cluster
kubectl get pods -n kafka -l strimzi.io/pool-name=broker
```

New brokers are not automatically elected as leaders or followers for existing partitions. To actually spread existing topic partitions onto the new brokers, you need a separate partition reassignment step.

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

**Strimzi does not automatically drain partitions off a broker when you scale down.** Before reducing `replicas` on a `KafkaNodePool`, you must first reassign every partition (leader and follower replicas alike) that lives on the broker being removed onto the remaining brokers. Skip this step and the replicas that only existed on that broker simply disappear — leaving you with under-replicated partitions at best, and data loss at worst.

The safe scale-down sequence is:

1. Run `kafka-reassign-partitions.sh --generate` against a broker list that excludes the broker(s) you're removing.
2. Apply the plan with `--execute` and confirm completion with `--verify` (check that under-replicated partitions is zero).
3. Only after reassignment is fully complete, reduce `KafkaNodePool.spec.replicas` to remove the broker pod(s).

## Automated Rebalancing with Cruise Control

Cruise Control continuously collects broker-level load metrics — disk usage, CPU, network throughput — and uses them to generate and execute partition reassignment plans automatically. Instead of running `kafka-reassign-partitions.sh` by hand every time you add or remove a broker, you can delegate rebalancing to goal-based automation.

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

Right after a scale-out or scale-in, scoping the rebalance to `add-brokers` or `remove-brokers` avoids the network overhead and time cost of `full` mode moving unrelated partitions that don't need to move.

## Rolling Upgrades

### Automatic Rolling Restarts on Spec Changes

When you change the spec of a `Kafka` or `KafkaNodePool` CR — resource requests/limits, config values, volumes, etc. — the Strimzi Operator detects the change and restarts broker pods **one at a time**. The Operator coordinates each restart so that it only proceeds while every partition still satisfies its `min.insync.replicas`, ensuring a restart never drops a partition's available replica count below the required threshold.

### Kafka Version Upgrades — The Two-Phase Pattern

In KRaft mode there is no `inter.broker.protocol.version`/`log.message.format.version` (those are ZooKeeper-era settings). Instead, the `Kafka` CR's `spec.kafka.version` (the software version) and `spec.kafka.metadataVersion` (the KRaft metadata log format version) must **not** be bumped together — this still needs **two separate phases**. `metadataVersion` controls the format the controller quorum uses to persist metadata, so it must stay on the old format while old and new nodes are mixed mid-rollout.

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

Applying this triggers a rolling replacement of the broker/controller binaries to 3.9.0, while the metadata format stays on 3.8-IV0. This keeps old and new nodes compatible with each other in the controller quorum during the window where both are running.

**Phase 2 — Bump metadataVersion after every node is replaced**

```yaml
    version: 3.9.0
    metadataVersion: 3.9-IV0
```

Only bump `metadataVersion` after confirming every broker/controller is running 3.9.0. This change triggers another reconciliation to adopt the new metadata format. If you reverse the order — bumping the software version and `metadataVersion` at the same time — nodes still running the old binary won't understand the new metadata format, and you'll get controller quorum communication errors.

### Strimzi Operator Version Upgrades

**Upgrade the Strimzi Operator itself before bumping the Kafka version.** Each Strimzi release supports a specific range of Kafka versions, and changing the CR to a Kafka version the running Operator doesn't recognize will fail validation. The typical order is: upgrade the Operator → give it time to complete reconciliation → upgrade the Kafka software version (Phase 1) → upgrade `metadataVersion` (Phase 2).

## Failure Handling Basics

### PodDisruptionBudget and Broker Pod Eviction

Strimzi automatically creates a `PodDisruptionBudget` (PDB) for every `KafkaNodePool`. By default, it allows only one broker pod at a time to undergo voluntary eviction — node drains, Cluster Autoscaler node replacement, and similar — which prevents multiple brokers from going down simultaneously and breaking quorum or availability.

```bash
kubectl get pdb -n kafka -l strimzi.io/cluster=my-cluster
```

### `acks=all` Producers During Rolling Restarts

With `acks=all`, producers are protected from data loss even during a broker rolling restart. If the broker being restarted was the leader for a partition, the controller elects a new leader from the in-sync replica (ISR) set just before the restart proceeds. Producers detect the leader change, refresh their metadata, and retry against the new leader — there may be a brief latency spike, but as long as `min.insync.replicas` is satisfied, no committed data is lost. Producers using `acks=1` or lower are at risk of losing messages that hadn't yet replicated to a follower at restart time.

From the consumer side, a rolling restart can trigger a consumer group rebalance and a temporary dip in throughput, but as long as offsets were being committed normally, consumers pick up right where they left off once the restart completes.

---

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md).

Next up: Part 4 covers Schema Registry — managing message schemas and compatibility strategy for Kafka topics.
