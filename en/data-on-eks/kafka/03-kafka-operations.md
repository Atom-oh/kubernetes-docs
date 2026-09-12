# Part 3: Kafka Operations

> **Reviewed**: 2026-09-12, Strimzi 1.2.0 / Kafka 4.3.1.
> **Validation**: Current release documentation/source, local CRD/merge-patch checks, proposal generation/JSON extraction, Decimal calculations and CLI options. No Kafka reassignment, upgrade or AWS volume changes were executed.

This chapter assumes the authenticated Kafka deployment and broker-only pool from [Part 2](./02-strimzi-operator.md). Operational commands can move real partitions and change resources: inspect current settings, placement and proposals before executing. Do not apply broker-scaling procedures unchanged to controller-role pools.

## 1. Storage Performance and Durability

Consumer lag does not make every read random. Even sequential historical reads can increase physical I/O and tail latency when consumers interleave ranges or exceed page cache. Measure IOPS, throughput, queue latency, cache hits and instance EBS limits.

| Characteristic | gp3 | io2 Block Express |
| --- | --- | --- |
| Included baseline | 3,000 IOPS / 125 MiB/s | Performance follows provisioned IOPS |
| Maximum volume IOPS | 80,000 | 256,000 on Nitro |
| Maximum volume throughput | 2,000 MiB/s | 4,000 MiB/s |
| Maximum size | 64 TiB | 64 TiB |
| Published design durability | 99.8–99.9% | 99.999% |
| Published AFR upper bound | 0.2% | 0.001% |

These are volume design figures, not a Kafka service SLA or a guarantee against arbitrary failures. Maximum performance has volume-size, IOPS-ratio and instance requirements. Outposts gp3 and non-Nitro io2 have different limits.

Storage capacity is part of the bill. Evaluate gp3 performance above the included baseline and provisioned io2 IOPS as well. Choose based on latency/durability requirements, measurements and current regional pricing. io2 is not billed only on IOPS, and large consumer lag does not automatically require io2.

## 2. Retention and Free Space

Base estimates on **retained compressed log bytes** and actual retention. Treating a short peak as a seven-day sustained rate can overestimate storage. Calculate different topic retention/replication separately and account for compaction, indexes, internal topics and temporary reassignment copies.

A synthetic sustained **50 MB/s (10⁶ bytes/s)** for seven days at RF=3 produces 90.72 TB of replicated logs.

| Interpretation | Capacity | Actual free fraction |
| --- | --- | --- |
| Add 30% to data size | 117.936 TB | About 23.08% |
| Keep 30% of total disk capacity free | 129.6 TB, about 117.87 TiB | 30% |

The earlier approximately 118 TB calculation is correct for the first interpretation. The second uses `data / (1 - 0.30)`. Evenly dividing 129.6 TB across three brokers gives 43.2 TB each, but actual partition skew still matters. These are calculation examples, not sizing recommendations for the Part 2 lab PVCs.

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

## 3. JBOD Expansion and Changes

Kafka 4.3.1 normally prefers directories with fewer partition logs when placing new logs. This is not simple round-robin or byte-balanced placement. Adding a disk does not automatically redistribute existing data.

This merge patch expands Part 2's volume 0 from 100Gi to 500Gi and adds volume 1. It **replaces the entire volumes array**: preserve any other existing volumes rather than applying it unchanged. Existing topology/resource settings remain intact.

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

Expansion depends on the StorageClass/CSI and filesystem. PVC shrink, class changes and volume-ID changes are not this operation. Do not assign kraftMetadata: shared to two volumes.

Before disk removal, inspect replica and metadata placement and move data away. Strimzi 1.2 supports broker-local JBOD movement through remove-disks rebalance mode, with its own fields and prerequisites. deleteClaim: false/Retain is not a backup or recovery proof. Do not manually run kafka-storage.sh format on Operator-managed data.

## 4. Broker Scaling: Manual and Automatic Paths

These procedures target **broker-only pools**. Strimzi 1.2 configures a static controller quorum; do not scale controller-role pools the same way. Upstream Kafka dynamic-quorum capability is distinct from Operator support.

| Configuration | Replica-count change on an existing pool |
| --- | --- |
| No matching autoRebalance mode | Broker addition and existing replica movement are separate |
| `add-brokers` autoRebalance | Automatically redistribute after scale-out |
| `remove-brokers` autoRebalance | Automatically coordinate replica evacuation during scale-in |

Automation reacts to **replicas changes on existing pools**. Pool creation/deletion is not the same trigger. With Kafka 4.3+, automatic scale-down also cordons brokers to prevent new replica assignments while evacuation proceeds.

### Manual scale-out

```bash
kubectl -n kafka get kafka my-cluster -o jsonpath='{.spec.cruiseControl.autoRebalance}'
# Continue with the manual path only when the relevant automatic mode is not enabled.
kubectl -n kafka get kafkanodepool broker -o json > broker-before.json
kubectl -n kafka patch kafkanodepool broker --type=merge -p '{"spec":{"replicas":6}}'
kubectl -n kafka get pods -l strimzi.io/pool-name=broker
kubectl -n kafka get kafkanodepool broker -o json > broker-pool.json
```

Running Pods are insufficient: verify the Operator's current generation, broker registration, ISR and capacity. Node IDs span the cluster; do not assume IDs 0–5 or a my-cluster-broker-0 Pod.

### Manual scale-down

Identify actual removal IDs and evacuate **every replica, including internal topics**. Moving only orders/payments does not prove a broker is empty. Verify completion, remaining RF/ISR, rack distribution and capacity before reducing replicas.

strimzi.io/remove-node-ids can select IDs, but an invalid range can fall back to default selection: compare it with current nodeIds. Keep Strimzi's nonempty-broker scale-down check enabled. Bypassing it to remove data-bearing brokers is not the baseline operating procedure.

## 5. Cruise Control Proposals and Approval

This example defaults to manual approval. Add Cruise Control while preserving the existing Kafka configuration. Do not omit default hard goals through an arbitrary goals list or enable skipHardGoalCheck as a generic default.

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

Insufficient metric samples or infeasible goals can prevent ProposalReady. Review movement volume, goals, racks and capacity before approval. Distinguish manually created auto-approval=false requests from requests generated by automatic scaling. Use a unique name for a new change if a prior request already exists.

| Mode | Purpose |
| --- | --- |
| `full` | Goal-based redistribution across the cluster |
| `add-brokers` | Move replicas onto specified new brokers |
| `remove-brokers` | Move replicas away from specified brokers |
| `remove-disks` | Move replicas off JBOD volumes within a broker |

Add/remove modes require broker IDs. Narrower scope does not guarantee faster execution or less impact. This helper validates IDs against a broker-pool snapshot and creates **proposal CR JSON only**. It does not assess capacity, ISR/rack safety or call an API.

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

### Optional: automatic rebalancing for existing pools

This configuration can **move data without a separate manual approval after replicas change**. Enable it only under a defined operating policy/goals. status.autoRebalance.state=Idle can also follow failure; inspect the generated KafkaRebalance result and Kafka status together.

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

## 6. Manual Kafka CLI Alternative

Keep JSON files and the admin configuration in the same environment running the CLI. A local file is not automatically available inside kubectl exec. The client needs access to all advertised endpoints and a TLS/SASL identity authorized for administration. The Part 2 orders application user is not an admin.

This example targets orders only. It is not a complete inventory for broker removal.

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

--generate prints both Current and Proposed JSON. Retain the original output as a record of prior placement, then extract only Proposed to a new file. The helper refuses to overwrite an existing output, so use a new filename for a new plan.

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

The helper validates JSON shape, not broker existence, retained RF, rack balance or complete partition inventory.

--verify checks the specified reassignment/log-directory moves. **Without --preserve-throttles, completed verification can clear broker/topic throttle settings, so it is not purely read-only.** Coordinate cleanup with other work sharing those limits. Verification is also not a complete under-replicated/offline-partition health check.

```bash
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-replicated-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --under-min-isr-partitions
kafka-topics.sh --bootstrap-server "$DOCS_BOOTSTRAP" --command-config "$DOCS_ADMIN_CONFIG" \
  --describe --unavailable-partitions
```

## 7. Version Upgrades

Choose an Operator combination supporting **both the current and target Kafka versions**. No Operator upgrade is needed merely for ordering if it already supports both. If the latest Operator drops the current Kafka version, plan intermediate supported versions and API conversion instead of installing it directly.

### Software and metadataVersion

When metadataVersion is omitted, Strimzi can automatically update it to the default after upgrading Kafka binaries. Changing both fields in one update does not inherently corrupt the quorum.

Explicitly retaining the previous metadataVersion can provide a validation/recovery decision window before increasing it. This example upgrades **an existing Kafka 4.2.1 / metadata 4.2-IV1** cluster to 4.3.1 under Strimzi 1.2. It is not an instruction to lower metadata on the already-4.3.1 Part 2 lab.

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

Check status.kafkaVersion, status.kafkaMetadataVersion, status.operatorLastSuccessfulVersion, generation and actual Pod images together. Custom Kafka, Connect or MirrorMaker images must also be prepared for compatible versions.

After validating clients and the recovery plan, raise metadata if appropriate. New metadata/features can prevent downgrade; a Git revert is not a recovery guarantee.

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

Not every spec change restarts Pods: dynamic Kafka configuration or supported volume expansion may follow other paths. When restarts are required, Operator availability checks are not absolute zero-downtime/loss guarantees. Observe data state, ISR, controller quorum, client timeouts and retries.

## 8. PDB and Failure Handling

Strimzi 1.2's default Kafka PDB is **one per Kafka cluster, covering Kafka Pods across its node pools**, not one per pool. If generation settings or custom PDBs differ, inspect actual selectors and minAvailable/maxUnavailable.

PDBs constrain voluntary eviction. They do not prevent node/AZ failures, direct Pod deletion or every Operator action. min.insync.replicas is not a single switch preventing every form of data loss.

```bash
kubectl -n kafka get pdb -l strimzi.io/cluster=my-cluster -o yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl -n kafka get pods,pvc -l strimzi.io/cluster=my-cluster
```

acks=all provides stronger durability under its synchronized-replica assumptions, but does not guarantee every application request succeeds. Plan for leader/coordinator changes, timeouts, retries and repeated processing during restarts. Broker restarts do not necessarily stop every consumer group as a whole.

Additional components such as Strimzi Drain Cleaner have their own supported modes/PDB behavior. Do not remove finalizers or scale-down checks merely because an operation failed; first inspect the cause and remaining data/metadata replicas.

## Next Steps and References

- [Schema Registry](./04-schema-registry.md)
- [Kafka overview](./README.md)
- [Quiz](../../quizzes/data-on-eks/kafka/03-kafka-operations-quiz.md)
- [Strimzi 1.2 operations](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kafka 4.3 design](https://kafka.apache.org/43/design/design/)
- [Kafka 4.3.1 log directory selection](https://github.com/apache/kafka/blob/4.3.1/core/src/main/scala/kafka/log/LogManager.scala)
- [Kafka reassignment command implementation](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/reassign/ReassignPartitionsCommand.java)
- [EBS gp3](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EBS io2 Block Express](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)
- [EBS pricing](https://aws.amazon.com/ebs/pricing/)
