# Kafka Operations Quiz

This quiz tests your understanding of storage design, broker scaling, Cruise Control rebalancing, rolling upgrades, and failure handling for a Strimzi-managed Kafka cluster on EKS.

## Multiple Choice Questions

1. Which EBS volume type is better suited for a workload with heavy random I/O from many consumer groups reading at scattered offsets and a strict p99 latency SLA?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>Show Answer</summary>

**Answer: C) io2**

**Explanation:**
io2 is billed on IOPS and offers up to 256,000 IOPS with 99.999% durability, making it well suited to latency-sensitive workloads dominated by small random I/O. Most event-streaming workloads are throughput-bound, so gp3 is the more cost-effective starting point; io2 is worth the switch only when random I/O becomes the bottleneck, such as spiky consumer lag or a strict p99 SLA.
</details>

2. What storage type on a `KafkaNodePool` configures a broker to use multiple independent volumes?
   - A) `type: persistent-claim`
   - B) `type: jbod`
   - C) `type: ephemeral`
   - D) `type: multi-volume`

<details>

<summary>Show Answer</summary>

**Answer: B) `type: jbod`**

**Explanation:**
`storage.type: jbod` (Just a Bunch Of Disks) lets you define multiple independent volumes per broker in a `volumes` list. Each volume is identified by an `id`, and partitions are distributed round-robin across them. `persistent-claim` is the type used for each individual volume entry within a JBOD configuration.
</details>

3. With a 7-day retention period, 100MB/s peak throughput, a replication factor of 3, and 30% headroom, what formula gives the required disk capacity for the whole cluster?
   - A) 100MB/s × 7 days (seconds) × 3
   - B) 100MB/s × 7 days (seconds) × 3 × 1.3
   - C) 100MB/s × 7 days (seconds) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>Show Answer</summary>

**Answer: B) 100MB/s × 7 days (seconds) × 3 × 1.3**

**Explanation:**
The sizing formula is `retention period × peak throughput × replication factor × (1 + headroom ratio)`. Convert retention to seconds and multiply by peak throughput to get the raw data volume, multiply by the replication factor to account for replicas, and finally multiply by the headroom factor (30% headroom = 1.3x) to leave safety margin.
</details>

4. What script must an operator manually run to format storage volumes on a Strimzi-managed Kafka cluster?
   - A) `kafka-storage.sh format` must be run manually on every broker
   - B) `kafka-configs.sh` must be used to apply format settings
   - C) None — the Strimzi Operator handles this automatically when a broker pod starts
   - D) `kafka-reassign-partitions.sh --format` must be used

<details>

<summary>Show Answer</summary>

**Answer: C) None — the Strimzi Operator handles this automatically when a broker pod starts**

**Explanation:**
With Strimzi, the Operator automatically handles volume formatting when a broker pod starts. This is a convenience compared to running plain open-source Kafka manually, where you'd need to run `kafka-storage.sh format` yourself.
</details>

5. When you scale out brokers by increasing `replicas` on a `KafkaNodePool`, what happens automatically for the new brokers?
   - A) Existing partitions are immediately redistributed onto the new brokers
   - B) The new brokers join the cluster, but existing topic partitions are not automatically reassigned
   - C) The new brokers automatically become leaders for all partitions
   - D) The new brokers only serve as controllers

<details>

<summary>Show Answer</summary>

**Answer: B) The new brokers join the cluster, but existing topic partitions are not automatically reassigned**

**Explanation:**
Increasing `replicas` causes Strimzi to create new broker pods and join them to the cluster, but moving existing topic partitions onto them is not automatic. To actually utilize the new brokers' capacity, you need a manual reassignment via `kafka-reassign-partitions.sh` or a Cruise Control rebalance in `add-brokers` mode.
</details>

6. What must be done before scaling down a broker?
   - A) Nothing — Strimzi drains it automatically
   - B) Partitions on the broker being removed must first be reassigned to the remaining brokers
   - C) The cluster must be restarted
   - D) All topics must be deleted

<details>

<summary>Show Answer</summary>

**Answer: B) Partitions on the broker being removed must first be reassigned to the remaining brokers**

**Explanation:**
Strimzi does not automatically drain partitions when scaling down a broker. Before reducing `replicas`, all replicas on the broker being removed must be reassigned to the remaining brokers — otherwise you risk under-replicated partitions or outright data loss.
</details>

7. What is the primary role of Cruise Control?
   - A) It automates topic creation and deletion
   - B) It collects broker load metrics and automatically generates/executes goal-based partition reassignment plans
   - C) It manages consumer group offset commits
   - D) It automatically renews TLS certificates

<details>

<summary>Show Answer</summary>

**Answer: B) It collects broker load metrics and automatically generates/executes goal-based partition reassignment plans**

**Explanation:**
Cruise Control continuously collects per-broker load metrics — disk usage, CPU, network throughput — and uses configured goals to automatically generate and execute partition reassignment plans. This removes the need to manually run `kafka-reassign-partitions.sh` for routine rebalancing.
</details>

8. In the `mode` field of a `KafkaRebalance` resource, which mode is focused on moving partitions onto newly added brokers to fill their load?
   - A) `full`
   - B) `add-brokers`
   - C) `remove-brokers`
   - D) `partial`

<details>

<summary>Show Answer</summary>

**Answer: B) `add-brokers`**

**Explanation:**
`add-brokers` mode focuses on moving partitions onto newly added brokers, making it faster and narrower in scope than `full` mode, which reassigns across every broker including unrelated ones. `remove-brokers` mode, conversely, focuses on moving partitions off brokers about to be removed — a useful drain step before scaling down.
</details>

9. What is the correct procedure for upgrading a KRaft-mode cluster's Kafka version from 3.8 to 3.9?
   - A) Change `version` and `metadataVersion` to 3.9 all at once
   - B) First change only `version` to 3.9 to roll out the new broker/controller software, and only after every node has been replaced, bump `metadataVersion` to 3.9-IV0
   - C) First bump `metadataVersion`, then change `version`
   - D) Stop the entire cluster and change all values at once

<details>

<summary>Show Answer</summary>

**Answer: B) First change only `version` to 3.9 to roll out the new broker/controller software, and only after every node has been replaced, bump `metadataVersion` to 3.9-IV0**

**Explanation:**
In KRaft mode there's no `inter.broker.protocol.version`/`log.message.format.version` (those are ZooKeeper-era settings). Instead, `spec.kafka.version` (the software version) and `spec.kafka.metadataVersion` (the format the controller quorum uses to persist metadata) must be bumped in two phases. Phase 1 bumps only the software version while keeping `metadataVersion` pinned to the old format, so old and new nodes stay compatible with each other in the controller quorum while both are running during the rollout. Phase 2 bumps `metadataVersion` only after confirming every node has been replaced. Reversing this order means nodes still on the old binary won't understand the new metadata format, causing controller quorum communication errors.
</details>

10. What Kubernetes resource does Strimzi automatically create per `KafkaNodePool` to limit voluntary evictions?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>Show Answer</summary>

**Answer: C) PodDisruptionBudget**

**Explanation:**
Strimzi automatically creates a `PodDisruptionBudget` (PDB) for every `KafkaNodePool`. By default it allows only one broker pod at a time to undergo voluntary eviction (node drains, autoscaler node replacement, etc.), preventing multiple brokers from going down simultaneously and breaking availability.
</details>

## Short Answer Questions

11. What Kafka config value does Strimzi respect during a rolling restart to ensure a partition's available replica count never drops below the required minimum?

<details>

<summary>Show Answer</summary>

**Answer: `min.insync.replicas`**

**Explanation:**
During rolling restarts triggered by CR spec changes, the Strimzi Operator restarts brokers one at a time while ensuring each partition's `min.insync.replicas` requirement is still satisfied. This prevents a restart from dropping a partition's available in-sync replica count below the required threshold, which would otherwise cause write failures or availability loss.
</details>

12. What component should be upgraded before upgrading the Kafka cluster's version itself?

<details>

<summary>Show Answer</summary>

**Answer: The Strimzi Operator**

**Explanation:**
Each Strimzi release supports a specific range of Kafka versions, and changing the CR to a Kafka version the running Operator doesn't recognize will fail validation. So the Strimzi Operator itself must be upgraded to the latest version before bumping the Kafka software version.
</details>

13. Before actually executing a partition reassignment plan, what option of `kafka-reassign-partitions.sh` is used to generate a plan against a specified broker list?

<details>

<summary>Show Answer</summary>

**Answer: `--generate`**

**Explanation:**
The `--generate` option produces a reassignment plan (JSON) based on `--topics-to-move-json-file` and `--broker-list`, without actually executing it. After reviewing the plan, you apply it with `--execute` and check progress and completion with `--verify`.
</details>

14. In one sentence, explain why a producer configured with `acks=all` can survive a broker rolling restart without losing data.

<details>

<summary>Show Answer</summary>

**Answer: If the broker being restarted was a partition leader, the controller elects a new leader from the in-sync replica (ISR) set before the restart proceeds, and as long as `min.insync.replicas` is satisfied, committed data is preserved.**

**Explanation:**
An `acks=all` producer waits for its message to be written by enough replicas to satisfy `min.insync.replicas` before treating it as committed. If the leader changes ahead of a broker restart, the producer detects the change, refreshes its metadata, and retries against the new leader — there may be a brief latency spike, but already-committed data is not lost. Producers using `acks=1` or lower have no such guarantee and risk losing in-flight messages.
</details>

## Hands-on Questions

15. Write a `KafkaNodePool` YAML named `broker` using JBOD storage with 3 volumes, each 300Gi on gp3.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Setting `storage.type: jbod` and defining three `persistent-claim` volumes in the `volumes` list, each with a unique `id` (0, 1, 2), gives the broker three independent volumes. `deleteClaim: false` protects the PVCs from deletion when the broker is recreated or scaled down, safeguarding the data on them.
</details>

16. Create a `KafkaRebalance` resource in `full` mode for a cluster named `my-cluster`, and write the command to approve the generated rebalance proposal.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Creating the `KafkaRebalance` CR causes Cruise Control to automatically generate a rebalance proposal and wait in `ProposalReady` state. The `strimzi.io/rebalance=approve` annotation is required to actually execute the partition moves. `mode: full` generates a goal-based plan covering every broker in the cluster.
</details>

17. After scaling brokers from 3 (IDs 0,1,2) to 6 (IDs 0-5), write the three-step commands (generate → execute → verify) to reassign the `orders` topic's partitions across the full broker list including the new brokers.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`--generate` produces a partition move plan targeting the given `--broker-list` (here, 0-5, including the new brokers). `--execute` kicks off the actual reassignment, and `--verify` confirms the reassignment completed with no under-replicated partitions remaining. Only after this process do the newly added brokers actually hold partition leader/follower roles.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/03-kafka-operations.md) | [Next Quiz: Schema Registry](./04-schema-registry-quiz.md)
