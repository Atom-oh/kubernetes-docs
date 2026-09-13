# Kafka Operations Quiz

> **Last Updated**: September 12, 2026, Strimzi 1.2.0 / Kafka 4.3.1.

This quiz tests your understanding of storage design, broker scaling, Cruise Control rebalancing, rolling upgrades, and failure handling for a Strimzi-managed Kafka cluster on EKS.

## Multiple Choice Questions

1. Which SSD option is designed by AWS for low latency, high IOPS and high durability?
   - A) gp2
   - B) gp3
   - C) io2
   - D) st1

<details>

<summary>Show Answer</summary>

**Answer: C) io2**

**Explanation:**
io2 Block Express targets low latency, high IOPS and durability. Maximum 256,000 IOPS requires appropriate conditions such as Nitro. Distinguish 99.999% design durability from 0.001% AFR. Capacity and IOPS contribute to cost; choose using measurements, requirements and pricing.
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
JBOD provides independent volume IDs. Kafka 4.3.1 normally prefers directories with fewer partition logs for new logs; this is not guaranteed round-robin or byte-balanced placement. Existing data movement is separate.
</details>

3. For sustained 100MB/s retained logs, seven-day retention and RF=3, which formula keeps 30% of total capacity free?
   - A) 100MB/s × 7 days (seconds) × 3
   - B) 100MB/s × 7 days (seconds) × 3 ÷ 0.70
   - C) 100MB/s × 7 days (seconds) ÷ 3
   - D) 100MB/s × 3 × 1.3

<details>

<summary>Show Answer</summary>

**Answer: B) 100MB/s × 7 days (seconds) × 3 ÷ 0.70**

**Explanation:**
Adding 30% to data size leaves only about 23.08% of total capacity free. Divide replicated data by 0.70 to keep 30% free. Use sustained retained/compressed log bytes, actual retention and separate operating overhead.
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
Strimzi/startup scripts manage required initialization of new storage metadata. Existing data is not wiped on every start. Do not arbitrarily format Operator-managed volumes manually.
</details>

5. Without a matching autoRebalance mode, what does increasing broker-pool replicas do?
   - A) Existing partitions are immediately redistributed onto the new brokers
   - B) The new brokers join the cluster, but existing topic partitions are not automatically reassigned
   - C) The new brokers automatically become leaders for all partitions
   - D) The new brokers only serve as controllers

<details>

<summary>Show Answer</summary>

**Answer: B) The new brokers join the cluster, but existing topic partitions are not automatically reassigned**

**Explanation:**
This describes the case without a matching autoRebalance mode. Strimzi 1.2 can automatically rebalance after replicas increases on an existing pool when add-brokers automation is configured. Pool creation/deletion is a different event.
</details>

6. What data-state requirement must be satisfied before removing a broker?
   - A) Nothing — Strimzi drains it automatically
   - B) Partitions on the broker being removed must first be reassigned to the remaining brokers
   - C) The cluster must be restarted
   - D) All topics must be deleted

<details>

<summary>Show Answer</summary>

**Answer: B) Partitions on the broker being removed must first be reassigned to the remaining brokers**

**Explanation:**
All replicas must be safely evacuated before broker removal. Manual procedures include internal topics; configured remove-brokers autoRebalance can coordinate evacuation automatically. Preserve the nonempty-broker check and verify removal IDs.
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
Cruise Control computes proposals from load/goals and executes according to approval/automation policy. Proposal generation and movement are separate; do not casually bypass insufficient metrics or hard-goal failures.
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
add-brokers targets specified new brokers and needs their actual IDs. Goals, data volume and rack constraints determine duration/impact; it is not always faster than full. remove-brokers evacuates brokers before removal.
</details>

9. Which pattern upgrades Kafka 4.2.1 to 4.3.1 while retaining the old metadata format for a validation window?
   - A) Immediately raise both version and metadataVersion
   - B) Raise version to 4.3.1, retain metadataVersion 4.2-IV1, then validate before changing to 4.3-IV0
   - C) Raise metadataVersion before checking binary compatibility
   - D) Delete all data and restart

<details>

<summary>Show Answer</summary>

**Answer: B) Raise version to 4.3.1, retain metadataVersion 4.2-IV1, then validate before changing to 4.3-IV0**

**Explanation:**
This is the operational pattern of explicitly retaining the prior metadataVersion for validation. If omitted, Strimzi can update metadata after the binary upgrade. The Operator must support current/target Kafka, and later format changes can prevent downgrade.
</details>

10. Which Kubernetes resource constrains voluntary evictions for a Strimzi Kafka cluster?
    - A) ResourceQuota
    - B) NetworkPolicy
    - C) PodDisruptionBudget
    - D) LimitRange

<details>

<summary>Show Answer</summary>

**Answer: C) PodDisruptionBudget**

**Explanation:**
Strimzi 1.2 normally creates one Kafka PDB per cluster covering Kafka Pods across its pools. It constrains voluntary eviction, not node/AZ failures or forced deletion.
</details>

## Short Answer Questions

11. Which minimum-ISR configuration is considered in Kafka rolling-availability checks?

<details>

<summary>Show Answer</summary>

**Answer: `min.insync.replicas`**

**Explanation:**
min.insync.replicas is an important availability input, not an unconditional guarantee during every roll. Check actual ISR, controller quorum, storage/networking and client timeouts/retries.
</details>

12. Which component's support matrix must include current and target Kafka before an upgrade?

<details>

<summary>Show Answer</summary>

**Answer: The Strimzi Operator**

**Explanation:**
Verify a Strimzi version supporting both current and target Kafka. An Operator upgrade is not mandatory if it already does. If the newest Operator drops the current Kafka version, plan intermediate versions and API/CRD migration.
</details>

13. Before actually executing a partition reassignment plan, what option of `kafka-reassign-partitions.sh` is used to generate a plan against a specified broker list?

<details>

<summary>Show Answer</summary>

**Answer: `--generate`**

**Explanation:**
--generate prints current and proposed assignments without executing movement. Extract Proposed separately and review RF, IDs, racks and capacity. Completed --verify can clear throttle configuration without preserve-throttles.
</details>

14. Distinguish the durability assumptions of acks=all from request-success guarantees during a roll.

<details>

<summary>Show Answer</summary>

**Answer: Durability is stronger while synchronized copies and a viable quorum/leader remain, but requests can still time out or require retries.**

**Explanation:**
acks=all waits for the current full ISR while satisfying minimum ISR. Synchronized copies and viable leader/quorum/storage conditions must remain. Handle timeouts, retries and repeated processing separately.
</details>

## Hands-on Questions

15. Define a new-environment broker pool example with three 300Gi gp3 volumes.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
This is a new-environment definition, not an instruction to shrink a volume already expanded to 500Gi. It uses Part 2 gp3-kafka and selects one metadata volume. Retain/deleteClaim settings are not backups.
</details>

16. Create a `KafkaRebalance` resource in `full` mode for a cluster named `my-cluster`, and write the command to approve the generated rebalance proposal.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Cruise Control needs to be enabled with valid metrics/goals. Auto-approval is false: inspect ProposalReady before approving. Distinguish manual requests from automatic scaling requests.
</details>

17. After broker expansion, use actual IDs and TLS admin settings to generate, extract, execute and check an orders reassignment.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Keep files in the environment running the CLI. Use real broker IDs and TLS admin configuration, extracting Proposed rather than Current. Use --verify --preserve-throttles for movement status, then check URP/min-ISR/offline state separately. Moving one topic does not prove a complete broker drain.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/03-kafka-operations.md) | [Next Quiz: Schema Registry](./04-schema-registry-quiz.md)
