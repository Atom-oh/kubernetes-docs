# Part 8: Best Practices

> **Review baseline**: Kafka 4.3.1, Strimzi 1.2.0\
> **Last reviewed**: September 12, 2026

This chapter turns the preceding examples into operational decisions to validate.
The [benchmark chapter](./09-kafka-benchmark.md) follows it; a checklist is not a
substitute for measured workload and failure tests.

## Partition design and measurement

For a conventional consumer group, one partition is assigned to at most one group
member at a time. Twenty independently consuming members therefore need at least
twenty partitions to keep all members busy. Also measure per-partition throughput,
key skew, record size, replication overhead, recovery time and broker/controller
capacity. Share groups and application-internal parallel processing have different
semantics; do not treat this rule as a universal description of every consumer API.

More partitions increase metadata, replica, buffer and recovery work. The cost
does not follow one universal per-partition memory/file-descriptor formula.
Historical 4,000/200,000 rules of thumb are not current universal limits. Choose
counts from measured steady-state and failure behavior, including replica
assignments per broker, not just logical topic partitions.

### Count partitions rather than topic headers

`grep -c "PartitionCount"` counts **topic summary lines**, not partitions.
Save the following as `partition_summary.py`. It reads the current CLI's partition
rows, including `Leader: none`, and reports logical partitions separately from
replica placements and leadership.

```python
import collections
import json
from pathlib import Path
import re
import sys

def summarize(text):
    pattern = re.compile(
        r"^\s*Topic:\s+(\S+)\s+Partition:\s+(\d+)\s+Leader:\s+(none|-?\d+)"
        r"\s+Replicas:[ \t]*([\d,]*)[ \t]+Isr:[ \t]*([\d,]*)"
    )
    partitions = {}
    topics = collections.Counter()
    leaders = collections.Counter()
    replicas = collections.Counter()
    offline = []
    for line in text.splitlines():
        if not re.search(r"\bPartition:", line):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError("Unrecognized partition row; check Kafka CLI version/output.")
        topic, partition, leader, replica_text, _ = match.groups()
        key = (topic, int(partition))
        if key in partitions:
            raise ValueError("Duplicate topic/partition row.")
        replica_ids = [int(x) for x in replica_text.split(",") if x]
        if not replica_ids or len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Missing or duplicate replica IDs.")
        partitions[key] = True
        topics[topic] += 1
        replicas.update(replica_ids)
        if leader == "none" or int(leader) < 0:
            offline.append({"topic": topic, "partition": int(partition)})
        else:
            leaders[int(leader)] += 1
    if not partitions:
        raise ValueError("No partition rows; empty visibility is not proof of a healthy cluster.")
    return {
        "visible_topics": len(topics),
        "logical_partitions": len(partitions),
        "replica_assignments": sum(replicas.values()),
        "partitions_by_topic": dict(sorted(topics.items())),
        "leaders_by_broker": dict(sorted(leaders.items())),
        "replicas_by_broker": dict(sorted(replicas.items())),
        "offline_partitions": offline,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 partition_summary.py topics.txt")
    print(json.dumps(summarize(Path(sys.argv[1]).read_text()), indent=2))
```

```bash
set -euo pipefail
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
# Run from a Kafka 4.3.1 client installation. admin.properties is local to this client.
bin/kafka-topics.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe > topics.txt
python3 partition_summary.py topics.txt
```

The result covers only the topics visible to the calling identity and the command's
filters, including internal topics when they are returned. A failed/empty query is
not evidence that a cluster has zero partitions or is healthy. Use credentials
appropriate for this administrative read; do not assume broker pod IDs or a
plaintext `localhost:9092` listener.

### Preserve the key's meaning

The Java producer's default keyed mapping uses the **serialized key bytes** and
`toPositive(murmur2(keyBytes)) % partitionCount`, unless an explicit partition,
custom partitioner or key-ignoring configuration changes the behavior. Other
clients must use a compatible partitioner/serializer if the same mapping matters.

High cardinality alone does not guarantee balanced traffic: one very busy customer
can still dominate. Random or timestamp salting changes per-key ordering, joins
and compaction identity. Use it only when the data contract permits those changes,
with an explicit recombination/ordering strategy if needed.

Increasing partition count can remap some keys; it does not redistribute old
records. It can break cross-partition key ordering and assumptions of
co-partitioned joins. The requirements depend on the join/topology; not every
Streams join uses identical co-partitioning. For order-sensitive or stateful
workloads, plan and test repartitioning/migration, often with a new topic.

## Producer tuning

Treat this as a measured starting profile, added to the existing authenticated
client configuration, not a universal optimum.

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

- `acks=all` waits for the current ISR. With RF=3 and topic/broker
  `min.insync.replicas=2`, an ISR below two rejects writes rather than waiting
  indefinitely for a second replica. A single failure is tolerable only while
  the remaining replicas/quorum and other dependencies satisfy the requirements.
- `enable.idempotence=true` suppresses supported producer retry duplicates. It
  requires compatible acks, retries and `max.in.flight.requests.per.connection`
  settings. Explicitly setting a compatible property does not disable it.
- Kafka 4.3's default linger is 5 ms; 10 ms and 32 KiB here are example tuning
  choices. `batch.size` is a per-partition batching/allocation setting, not a hard
  maximum record or request size. Queueing and delivery deadlines also affect latency.
- Compare lz4, zstd, gzip or no compression with representative data, CPU and
  latency. Do not assume one codec always has the best total cost.

`min.insync.replicas` belongs to the topic/broker, not the producer properties.
`delivery.timeout.ms` bounds delivery attempts; a high retry count does not mean
infinite delivery time. Always observe send failures.

Idempotence does not deduplicate arbitrary application resubmissions or an external
database side effect. Kafka consume-transform-produce exactly-once processing also
requires the appropriate transaction lifecycle, atomic output/input-offset commit,
fencing and read-committed consumers. A `transactional.id` string alone is not enough.

## Consumer processing and membership

This profile explicitly uses **`group.protocol=classic`** so the client heartbeat/
session settings apply. With `group.protocol=consumer`, those intervals are
controlled by the broker's consumer-group configuration instead.

```properties
group.id=order-processor
group.protocol=classic
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

Bound actual processing time, not merely record count. A slow record can still
exceed `max.poll.interval.ms`. Dynamic and static members do not have identical
reassignment timing: a static member can stop heartbeats after the poll timeout,
with reassignment deferred until its session expires.

### Commit after durable processing

Auto-commit does not know when an asynchronous external effect finishes.
A correctly ordered synchronous loop can use auto-commit, but do not assume it
tracks a worker pool's progress. The following helper demonstrates explicit
synchronous process-before-commit with auto-commit disabled.

```java
import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public final class ConsumerExamples {
    public static void setStaticIdentity(Properties props, String instanceId) {
        if (instanceId == null || instanceId.isBlank() || instanceId.contains("${")) {
            throw new IllegalArgumentException("Supply a resolved, stable, unique consumer instance ID.");
        }
        props.setProperty(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
    }

    public static int processOneBatch(
            Consumer<String, String> consumer,
            java.util.function.Consumer<ConsumerRecord<String, String>> processDurably) {
        var records = consumer.poll(Duration.ofMillis(500));
        for (var record : records) {
            processDurably.accept(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();
        }
        return records.count();
    }
}
```

```java
// props already includes bootstrap, TLS/SCRAM, deserializers and the profile below.
try (var consumer = new KafkaConsumer<String, String>(props)) {
    consumer.subscribe(List.of("orders"));
    while (!Thread.currentThread().isInterrupted()) {
        ConsumerExamples.processOneBatch(consumer, application::processDurably);
    }
}
```

`application.processDurably` is application code that must return only after the
required effect succeeds. On processing/commit failure, stop and recover or
explicitly seek to the correct positions; **do not catch an error and keep polling**
past failed records. A restart can replay already processed records, so external
effects need a suitable idempotency/transaction strategy. Configure shutdown with
KafkaConsumer's supported wakeup/close pattern.

KafkaConsumer is not generally thread-safe. Offloading work requires bounded queues,
partition ordering, pause/resume on the consumer thread, contiguous completed
offset tracking and rebalance handling. Moving work to a thread pool alone is not
a reliability fix.

### Resolve a stable static-member ID

Java `Properties` does **not** expand `group.instance.id=${POD_NAME}`.
Resolve the environment value in application/configuration code before creating
the consumer:

```java
// One consumer instance per stable logical member in this example.
ConsumerExamples.setStaticIdentity(props, System.getenv("KAFKA_GROUP_INSTANCE_ID"));
```

For one consumer per StatefulSet pod, a Downward API value from `metadata.name`
can supply a stable logical identity. Deployment pod names change across many
rollouts; multiple consumers in one pod need different IDs. Every active consumer
instance needs a unique ID, with deliberate reuse only by its replacement.
Duplicate active IDs can fence a member.

Static membership can avoid unnecessary rebalances for compatible short restarts;
it does not guarantee unchanged assignment whenever a pod returns before a timer.
Topology, membership and subscriptions also matter, and a longer session timeout
delays recovery of a genuinely failed member.

## Authentication, authorization and networking

### Separate the two CAs and listener properties

With default Strimzi-managed CAs:

- The **cluster CA** signs broker/internal component certificates; clients trust
  the appropriate server certificate chain.
- The **clients CA** signs `KafkaUser` client certificates for mTLS.
- `user.crt`/`user.key` are client credentials. A user Secret's clients-CA certificate
  is not a substitute for the broker trust chain.

A listener's network exposure uses `type: internal`, `loadbalancer`, etc.
Encryption is `tls: true`, and client authentication is
`authentication.type: tls`. There is no listener exposure type named `tls`.

The following is **one additional listener entry** for the existing
`spec.kafka.listeners` array, not a replacement for the Part 2 TLS/SCRAM listener.
Review the entire desired Kafka resource before adding it:

```yaml
name: mtls
port: 9094
type: internal
tls: true
authentication:
  type: tls
networkPolicyPeers:
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: kafka-clients
  podSelector:
    matchLabels:
      app: order-service
```

Both selectors are in **one peer**, so the pod must have `app=order-service`
**and** be in namespace `kafka-clients`. Two separate peer entries would be OR:
matching pods in the policy namespace, or every pod in the selected namespace.
Network policies are additive, require CNI enforcement and do not override a
second policy that also allows traffic. Consider egress and the actual external/
node traffic path too.

This separate mTLS user preserves the existing SCRAM user's identity:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

The User Operator must reconcile it, and the broker's simple authorizer must be
enabled. Distribute the user credentials and broker trust to the application's
namespace through a controlled rotation workflow; Kubernetes cannot directly mount
a Secret from another namespace. Confirm current generation, successful TLS/auth
and permitted/denied actions. Committing YAML alone does not grant working access.

The existing SCRAM path still needs TLS for encryption and password rotation.
Neither a Kafka ACL nor a NetworkPolicy replaces the other layer.

### Encrypt newly provisioned persistent storage explicitly

For the standard EBS CSI driver, use an encrypted StorageClass and/or account/Region
EBS encryption-by-default settings. This example also retains volumes and waits
for scheduling before selecting an AZ:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: 'true'
```

For Auto Mode use its separate `ebs.csi.eks.amazonaws.com` provisioner and topology
constraints from Part 2, also specifying `encrypted: "true"`. Do not infer dynamic
PVC encryption from Auto Mode's node/ephemeral-disk encryption statement; its
StorageClass parameter reference lists `encrypted` defaulting to false. Confirm
the actual created EBS volume's encryption and KMS key.

A customer-managed key requires its actual ARN and the appropriate role/key grants,
not `key/xxxxxxxx`. Changing a StorageClass or enabling account defaults does not
retroactively encrypt existing volumes. Plan a supported data/snapshot migration
and verify restore access before replacing persistent storage.

## Capacity, tiering and retention

Kafka benefits from page cache, but CPU (including TLS/compression), network,
storage throughput/IOPS and cgroup memory limits can each dominate. Include heap,
off-heap, page cache and other workloads in measurements. There is no universal
“4–8 GB heap is enough” or memory-optimized-instance cost winner.

Kafka tiered storage has been production-ready since 3.9 and is supported by
Strimzi 1.2. It still needs a compatible **RemoteStorageManager plugin**, its
dependencies in the image, remote access credentials/permissions, retention,
cleanup and recovery configuration. Strimzi's custom integration uses
`spec.kafka.tieredStorage` with its plugin class/path/config. Turning on
`remote.log.storage.system.enable` alone does not connect Kafka to S3.
Read the version's feature limitations and test unavailable remote storage and restore.

### Retention is a data decision

The following example changes an existing topic to three days or **50 GiB per
partition**, whichever limit is reached first. Deletion works at segment granularity
and asynchronously; it is not an instantaneous exact byte cap.

```bash
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe \
  --entity-type topics --entity-name application-logs
# After reviewing retention/recovery requirements: shortening retention can delete data.
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --alter \
  --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

Lowering retention can irreversibly remove records needed for replay or recovery.
With `cleanup.policy=compact`, cleaning is asynchronous and keeps the latest value
per key subject to tombstones/cleaner behavior; high key cardinality and active/
uncleaned segments can still grow. Compaction is not a hard storage bound.
`compact,delete` also applies deletion retention, which can remove the last value
of an old key. Design state-rebuild and tombstone retention requirements explicitly.

### Spot and disruption

Keep the controller quorum on suitable reliable capacity in this production
baseline. Broker Spot capacity can be considered for workloads that tolerate its
risks, but spreading pods alone does not prevent correlated reclamations.
Combine broker rack-aware replica placement, node/AZ distribution, replacement
capacity in the EBS volume's AZ and tested recovery/headroom.

Strimzi 1.2's PDB covers the Kafka cluster's pods and constrains voluntary eviction.
It does not guarantee quorum during forced deletion, node failure, Spot reclamation
or every Operator rolling operation. RF=3/minISR=2, a PDB and On-Demand controllers
are design inputs, not a proof of zero loss or downtime.

## Evidence to retain before production use

- Version/API compatibility, upgrade/rollback and certificate-rotation rehearsal.
- Measured partition, replica, CPU/memory/network/storage limits under failure.
- Tested authorization boundaries, client identity and secret/trust rotation.
- Schema/history compatibility, processing/commit behavior and duplicate handling.
- Restore/failover evidence with measured RPO/RTO and required schemas/keys.
- Scrape/alert/notification coverage, consumer capacity and application SLOs.
- Retention, storage encryption, cost assumptions and a named operational owner.

Apply the controls relevant to the workload and record remaining limitations.
Completing a generic checklist cannot certify production readiness.

## References and validation

The examples were checked using Kafka 4.3.1 configuration classes, its actual
keyed partitioner and MockConsumer process/commit tests, plus released resource
schemas and topic-output fixtures. They do not replace real TLS/CNI enforcement,
encrypted-volume inspection, failure recovery or application correctness tests.

- [Kafka 4.3 producer configuration](https://kafka.apache.org/43/configuration/producer-configs/)
- [Kafka 4.3 consumer configuration](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Kafka 4.3 tiered storage](https://kafka.apache.org/43/operations/tiered-storage/)
- [Kafka 4.3.1 keyed partitioner](https://github.com/apache/kafka/blob/4.3.1/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java)
- [Kafka 4.3.1 topic-description output](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- [Strimzi 1.2.0 deployment, TLS and tiered-storage guide](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Kubernetes NetworkPolicy selector semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EBS encryption by default](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)
- [EKS Auto Mode StorageClass parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

## Next steps

[Part 9: Kafka benchmark](./09-kafka-benchmark.md)

[Return to main page](./README.md)

## Quiz

[Topic quiz](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
