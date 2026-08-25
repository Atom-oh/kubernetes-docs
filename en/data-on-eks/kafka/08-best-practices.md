# Part 8: Best Practices

> **Supported Versions**: Apache Kafka 3.9, Strimzi 0.45+\
> **Last Updated**: July 9, 2026

Across this deep dive we covered Kafka fundamentals, Strimzi operations, schema registry, Kafka Connect/MirrorMaker, MSK integration, and monitoring. This final document consolidates production-readiness best practices by category and rolls up the key items from all seven preceding parts into a single go-live checklist.

## 1. Partition Design

### Sizing partition count

Start from the **maximum expected consumer parallelism** for a topic. A single partition can only be consumed by one consumer instance within a given consumer group at a time, so decide how far you expect to scale a consumer group and provision at least that many partitions. If you plan to scale out to 20 consumer instances at peak, you need at least 20 partitions.

Over-partitioning has real costs and should be avoided:

- **More open file handles**: each partition keeps several log segment files (`.log`, `.index`, `.timeindex`) open, so the number of open file descriptors per broker grows linearly with partition count.
- **More memory pressure**: producer/consumer batch buffers and per-replication-thread buffers on the broker scale with partition count.
- **Slower rebalances and failover**: the amount of leader-election work the controller must do on a broker failure scales with partition count, and consumer group rebalances take longer as well.

Confluent's classic rule of thumb was a soft ceiling around **4,000 partitions per broker and 200,000 per cluster** — guidance from the era when the ZooKeeper-based controller was the metadata bottleneck. KRaft-based clusters (Kafka 3.x+ controller quorum) handle far higher partition counts thanks to a much faster controller metadata path, but the principle still holds: don't over-partition just because you can, and validate the actual ceiling for your workload with real load testing.

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### Choosing a partition key

Pick a key with **high cardinality and even distribution** to avoid hot partitions. The default partitioner hashes the key with murmur2 and takes it modulo the partition count, so a low-cardinality key (e.g. `country` or `status` with only a handful of distinct values) will overload the few partitions that match your dominant traffic values while others sit idle. Prefer a field with sufficiently high cardinality (e.g. `user_id`), or salt a low-cardinality key (append a random or timestamp-derived suffix) to force a more even spread.

### Handling partition count changes carefully

Increasing the partition count on a **keyed** topic breaks the key-to-partition mapping. Because `hash(key) % partition_count` changes as soon as `partition_count` changes, the same key can land on a different partition after the change than it did before. This causes two concrete problems:

- **Broken ordering**: Kafka only guarantees ordering within a partition, so once messages for the same key are split across partitions, consumers can no longer rely on key-level ordering.
- **Broken co-partitioning**: joins in Kafka Streams (and similar) require the joined topics to share the same partition count and partitioning scheme. Changing partitions on only one side of a join breaks it.

Decide partition counts with headroom during capacity planning, and if a production topic already depends on key-based ordering or joins, prefer migrating to a new topic over increasing partitions on the existing one.

## 2. Producer Tuning

| Setting | Recommended value | Purpose |
|---------|--------------------|---------|
| `acks` | `all` (for durability-critical topics) | Wait for acknowledgment from all in-sync replicas (ISR) so a broker failure doesn't lose data |
| `min.insync.replicas` (topic/broker setting) | `2` (with replication.factor=3) | Combined with `acks=all`, requires the write to reach at least 2 replicas before succeeding — set on the topic (`kafka-configs.sh --entity-type topics`) or broker default, not as a producer client property |
| `linger.ms` | `5`–`20` | Trade a small amount of latency for larger batches and higher throughput |
| `batch.size` | `32768`–`65536` (32–64KB) | Raise the max bytes per batch to increase throughput per request |
| `enable.idempotence` | `true` | Prevent duplicate writes caused by producer retries |
| `compression.type` | `lz4` or `zstd` | Reduce network and storage costs |

```properties
# Producer settings for durability-critical topics (orders, payments, etc.)
# (min.insync.replicas is a topic/broker setting, not a producer property — shown here for reference only)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

`enable.idempotence=true` has been **the default since Kafka 3.0** unless you explicitly override `acks` or `retries` in a way that's incompatible with it. It assigns the producer a unique producer ID and per-partition sequence numbers so the broker can transparently deduplicate retries caused by transient network errors. This is distinct from full exactly-once semantics — idempotence only removes duplicates on the producer-to-broker hop; true end-to-end exactly-once requires the transactional API (`transactional.id`) as well.

`lz4` offers a good balance of CPU overhead and compression ratio for most workloads. `zstd` compresses better — useful for JSON/text-heavy payloads — at the cost of somewhat higher CPU usage. `gzip` compresses well but is CPU-expensive enough that it's generally not recommended for high-throughput producers.

## 3. Consumer Tuning

### Avoiding rebalance storms

If processing takes longer than `max.poll.interval.ms` (default 5 minutes), the consumer is force-evicted from its group, triggering a rebalance. When several consumers slow down at once, this can cascade into a "rebalance storm" of repeated group disruptions.

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

Lowering `max.poll.records` reduces how many records come back from a single `poll()` call, shortening the processing window between polls. Raising `max.poll.interval.ms` gives slow processing more headroom before eviction. The more robust fix is architectural: move heavy processing off the poll loop entirely and into a separate worker thread pool, polling only to fetch and hand off work.

### Manual offset commits

For pipelines where at-least-once processing matters (order processing, payments), auto-commit (`enable.auto.commit=true`) can commit an offset before the corresponding record has actually finished processing — if the consumer crashes in between, that record is effectively lost from the pipeline's perspective even though it was "committed."

```properties
enable.auto.commit=false
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);          // business logic
    }
    consumer.commitSync();        // commit only after processing succeeds
}
```

### Static group membership

Consumer pods on Kubernetes restart often — rolling deploys, OOMKilled restarts, node replacement. By default, a consumer leaving and rejoining a group triggers a full rebalance, so frequent brief restarts cause repeated, unnecessary processing pauses across the whole group. Setting `group.instance.id` enables static membership: if the consumer reconnects within `session.timeout.ms`, it resumes with its previous partition assignment intact, with no rebalance at all.

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` must be unique per pod — typically sourced from a StatefulSet pod name or injected via the downward API.

## 4. Security

### mTLS (transport encryption + mutual authentication)

Strimzi automatically provisions and rotates its own cluster CA when a Kafka cluster is deployed. Setting a listener's type to `tls` encrypts client-broker traffic, and giving a `KafkaUser` the `tls` authentication type causes Strimzi to issue a client certificate signed by that cluster CA.

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
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
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

### SASL/SCRAM

For environments where distributing and rotating client certificates is impractical (legacy apps, third-party tools), username/password-based SASL/SCRAM (`scram-sha-512`) is a solid alternative. Set the listener's authentication type to `scram-sha-512` and give the matching `KafkaUser` the same `authentication.type`; Strimzi generates the credentials into a Secret automatically.

### Declarative ACL management

As shown in the `KafkaUser` example above, `authorization.type: simple` plus an `acls` list lets you manage ACLs as code through GitOps instead of running `kafka-acls.sh` against the brokers by hand. Onboarding a new service to a topic is just committing a new `KafkaUser` resource.

### Network policies

Strimzi listeners support `networkPolicyPeers`, restricting which pods can reach a given listener port (e.g. 9092/9093/9094).

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    networkPolicyPeers:
      - podSelector:
          matchLabels:
            app: order-service
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kafka-clients
```

Strimzi turns this into a standard Kubernetes `NetworkPolicy` behind the scenes, so only pods matching the specified selectors can reach the listener port at all.

### Encryption at rest

EBS volume encryption is **not** something the EBS CSI driver applies automatically — you need to opt in explicitly through one of:

- Enabling the account/region-level **"EBS encryption by default"** setting, so every subsequently created volume is encrypted automatically.
- Setting `encrypted: "true"` (and optionally `kmsKeyId`) on the `StorageClass`.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx
```

Since Kafka clusters often carry compliance-sensitive data, treat an explicitly encrypted `StorageClass` for broker PVCs as the default, not an afterthought.

## 5. Cost Optimization

### Right-sizing instance types

Most Kafka workloads are far more sensitive to **memory — specifically OS page cache — than to CPU**. Kafka is designed to serve most reads out of the page cache, so for the common case where consumers are reading recent data, the RAM left over after the broker heap (usually 4–8GB is plenty) directly determines throughput. Memory-optimized instances (`r6g`/`r7g` Graviton family, for example) frequently deliver better price/performance than compute-optimized ones for this reason.

### Tiered storage

Tiered storage, defined by KIP-405, offloads older log segments from local disk to remote storage such as S3, reducing how much local EBS capacity each broker needs. It landed as early access in Apache Kafka 3.6 and **became production-ready (GA) in Kafka 3.9**, but it is not enabled by default — it's still an opt-in feature you must explicitly turn on (`remote.log.storage.system.enable=true`). Before relying on it with Strimzi, check that Strimzi release's support and maturity notes for tiered storage, and validate it thoroughly on a non-production cluster first.

### Tuning log retention

Set `retention.ms`/`retention.bytes` per topic based on actual business requirements instead of leaving defaults in place, since over-retaining data on EBS is a direct, ongoing cost. Topics that only need the latest value per key (state snapshots, cache-like data) should use `cleanup.policy=compact` so storage doesn't grow unbounded.

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Using Spot instances

For dev/staging environments or lower-criticality Strimzi clusters, running the broker node pool on Spot instances can cut costs substantially. However, **the KRaft controller node pool should stay on On-Demand**. Losing a majority of the controller quorum halts metadata management for the whole cluster, which is not a risk worth taking for Spot savings. Spread the broker node pool across AZs/nodes with pod topology spread constraints so a Spot reclamation event doesn't take out multiple replicas of the same partition at once.

## 6. Go-Live Checklist

Rolling up the key items from Parts 1 through 8 of this deep dive into a single pre-production checklist:

- [ ] **Architecture**: running in KRaft mode, with controller and broker node pools separated (Parts 1, 2)
- [ ] **Replication**: production topics use `replication.factor=3` and `min.insync.replicas=2`, tolerating a single broker failure (Part 1)
- [ ] **Partition design**: partition counts are sized to expected max consumer parallelism, not over-split (Part 8)
- [ ] **Strimzi version pinning**: Operator and Kafka versions are pinned explicitly, not left to drift on auto-upgrade (Part 2)
- [ ] **Storage**: broker `StorageClass` uses gp3 (or io2) with encryption (`encrypted: "true"`) (Parts 3, 8)
- [ ] **PodDisruptionBudget**: a PDB guarantees quorum/majority availability during rolling restarts and node replacement (Part 3)
- [ ] **Rolling upgrade rehearsal**: the rolling upgrade procedure has actually been exercised in staging (Part 3)
- [ ] **Schema compatibility**: schema registry compatibility mode (BACKWARD/FORWARD/FULL) is set deliberately per topic's needs (Part 4)
- [ ] **DR/replication**: Kafka Connect/MirrorMaker2-based disaster recovery or cross-region replication is documented and failover has been tested (Part 5)
- [ ] **MSK vs. self-managed decision**: the choice between managed MSK and Strimzi self-managed is documented with its operational and cost rationale (Part 6)
- [ ] **Monitoring/alerting**: dashboards and alert rules exist for broker metrics and consumer lag (Part 7)
- [ ] **Autoscaling**: consumer workloads scale on lag via KEDA or an equivalent mechanism (Part 7)
- [ ] **Producer/consumer config review**: `acks`, `enable.idempotence`, offset commit strategy, and static group membership have all been reviewed against workload needs (Part 8)
- [ ] **Security**: mTLS or SASL/SCRAM, `KafkaUser`-based ACLs, and listener `NetworkPolicy` are all in place (Part 8)
- [ ] **Cost review**: instance types, retention policy, and Spot usage are periodically re-evaluated (Part 8)
- [ ] **Load testing**: broker and consumer scale have actually been load-tested at expected peak throughput

Satisfying this checklist is a reasonable bar for saying the cluster is ready to run in production on EKS.

---

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md).
