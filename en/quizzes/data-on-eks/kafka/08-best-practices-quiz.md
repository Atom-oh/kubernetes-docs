# Part 8: Best Practices Quiz

This quiz tests your understanding of best practices spanning the whole Kafka deep dive series: partition design, producer/consumer tuning, security (mTLS/SASL), and cost optimization.

## Multiple Choice Questions

1. What should you consider first when sizing a topic's partition count?
   - A) The total number of brokers in the cluster
   - B) The maximum expected parallelism of the consumer group
   - C) The number of producer instances
   - D) The available EBS volume size

<details>

<summary>Show Answer</summary>

**Answer: B) The maximum expected parallelism of the consumer group**

**Explanation:**
A single partition can only be consumed by one consumer instance within a group at a time, so you need to decide how far you expect to scale a consumer group and provision at least that many partitions. If you plan to scale to 20 consumer instances at peak, you need at least 20 partitions. Broker count and EBS volume size are capacity concerns about how well the cluster can host a given partition count, not the primary driver of that count itself.
</details>

2. According to Confluent's classic rule of thumb, what was the approximate soft ceiling for partitions per broker?
   - A) 400
   - B) 4,000
   - C) 40,000
   - D) 400,000

<details>

<summary>Show Answer</summary>

**Answer: B) 4,000**

**Explanation:**
Confluent's classic guidance suggested a soft ceiling around 4,000 partitions per broker and 200,000 per cluster. This dates back to when the ZooKeeper-based controller was the metadata bottleneck. KRaft-based clusters handle far more partitions thanks to a much faster controller metadata path, but the underlying principle — don't over-partition just because you can — still applies, and the real ceiling for a given workload should be confirmed with load testing.
</details>

3. Which of the following is NOT a real cost of over-partitioning a topic?
   - A) More open file handles per broker
   - B) Higher memory usage in producer/broker buffers
   - C) Longer leader election and rebalance time on broker failure
   - D) Consumer group throughput always decreases

<details>

<summary>Show Answer</summary>

**Answer: D) Consumer group throughput always decreases**

**Explanation:**
Over-partitioning does add overhead in file handles, memory, and failure recovery time, but it doesn't always reduce throughput — if consumer parallelism can keep up, throughput isn't necessarily worse. In fact, too few partitions caps throughput by limiting how many consumers can work in parallel. Partition count is a trade-off between parallelism and overhead, not a simple "more is always worse/better" question.
</details>

4. What guarantee breaks most directly when you increase the partition count on a keyed topic?
   - A) The replication factor
   - B) Message ordering for a given key
   - C) Consumer group offset commits
   - D) The ISR list between brokers

<details>

<summary>Show Answer</summary>

**Answer: B) Message ordering for a given key**

**Explanation:**
The default partitioner computes `hash(key) % partition_count`, so changing the partition count changes which partition the same key maps to. Since Kafka only guarantees ordering within a single partition, messages for the same key can end up split across old and new partitions, and consumers can no longer rely on key-level ordering. Co-partitioning-based joins in Kafka Streams can also break as a result.
</details>

5. As of which Kafka version does `enable.idempotence` default to `true` without needing to be set explicitly?
   - A) Kafka 1.0
   - B) Kafka 2.0
   - C) Kafka 3.0
   - D) Kafka 4.0

<details>

<summary>Show Answer</summary>

**Answer: C) Kafka 3.0**

**Explanation:**
`enable.idempotence=true` has been the producer default since Kafka 3.0, unless `acks` or `retries` are explicitly overridden in an incompatible way. It assigns the producer a unique producer ID and per-partition sequence numbers so the broker can automatically deduplicate retries.
</details>

6. What does producer idempotence prevent?
   - A) Consumer group rebalances
   - B) Duplicate writes on the broker caused by network retries
   - C) Partition leader failures
   - D) Schema registry compatibility errors

<details>

<summary>Show Answer</summary>

**Answer: B) Duplicate writes on the broker caused by network retries**

**Explanation:**
When a producer doesn't receive an ack and retries the same record, without idempotence the broker could end up storing the record twice. An idempotent producer's PID and sequence numbers let the broker detect and drop the duplicate. Note this only dedupes the producer-to-broker hop — full end-to-end exactly-once still requires the transactional API on top of idempotence.
</details>

7. What is the combined effect of setting `acks=all` and `min.insync.replicas=2` on a topic with `replication.factor=3`?
   - A) Writes always wait for all 3 replicas
   - B) A write isn't considered complete until at least 2 replicas (including the leader) have it
   - C) Compression is automatically enabled
   - D) Partition leader election is disabled

<details>

<summary>Show Answer</summary>

**Answer: B) A write isn't considered complete until at least 2 replicas (including the leader) have it**

**Explanation:**
`acks=all` makes the producer wait for acknowledgment from the current in-sync replica (ISR) set, and `min.insync.replicas=2` forces writes to be rejected outright if the ISR shrinks below 2 (leader included). Together, this is the standard durability configuration that lets writes continue safely even if a single broker fails.
</details>

8. What happens when a consumer fails to finish processing within `max.poll.interval.ms`?
   - A) The partition leader is immediately replaced
   - B) The consumer is force-evicted from the group, triggering a rebalance
   - C) The broker automatically disables compression for that topic
   - D) Nothing — the consumer just waits for the next poll

<details>

<summary>Show Answer</summary>

**Answer: B) The consumer is force-evicted from the group, triggering a rebalance**

**Explanation:**
`max.poll.interval.ms` bounds how long a consumer can take between successive `poll()` calls. Exceeding it makes the broker treat the consumer as dead, evicting it from the group and triggering a rebalance. If multiple consumers slow down at once, this can cascade into a "rebalance storm."
</details>

9. What is the main purpose of setting `group.instance.id` to enable static group membership?
   - A) Automatically increase consumer throughput
   - B) Avoid unnecessary rebalances during brief pod restarts
   - C) Improve producer compression ratio
   - D) Speed up partition leader election

<details>

<summary>Show Answer</summary>

**Answer: B) Avoid unnecessary rebalances during brief pod restarts**

**Explanation:**
Consumer pods restart frequently on Kubernetes due to rolling deploys, OOMKilled events, and similar. Setting `group.instance.id` enables static membership: as long as the consumer reconnects within `session.timeout.ms`, it resumes with its previous partition assignment intact, with no rebalance at all. This prevents frequent short-lived restarts from triggering a full group rebalance each time.
</details>

10. When a `KafkaUser` in Strimzi specifies `authentication.type: tls`, who signs the resulting client certificate?
    - A) AWS Certificate Manager
    - B) A self-signed certificate generated by the client itself
    - C) Strimzi's managed cluster CA
    - D) A separately deployed cert-manager Issuer

<details>

<summary>Show Answer</summary>

**Answer: C) Strimzi's managed cluster CA**

**Explanation:**
Strimzi automatically provisions its own cluster CA when a Kafka cluster is deployed and rotates certificates on a schedule. Setting a `KafkaUser`'s `authentication.type` to `tls` causes Strimzi to issue a client certificate signed by that cluster CA into a Secret, ready for use in mTLS connections.
</details>

## Short Answer Questions

11. What single term describes the problem that arises from using a low-cardinality field (e.g. `country`) directly as a partition key?

<details>

<summary>Show Answer</summary>

**Answer: Hot partition**

**Explanation:**
The default partitioner computes `hash(key) % partition_count`, so a low-cardinality key with only a handful of distinct values will concentrate traffic onto a small subset of partitions whenever most traffic shares the dominant value, leaving other partitions idle. This can be mitigated by choosing a higher-cardinality key or salting a low-cardinality one to force a more even spread.
</details>

12. For pipelines where at-least-once processing matters, what offset commit approach (and setting) should replace auto-commit?

<details>

<summary>Show Answer</summary>

**Answer: Manual commits with `enable.auto.commit=false`, calling `consumer.commitSync()` (or `commitAsync()`) only after processing completes**

**Explanation:**
Auto-commit can commit an offset before the corresponding record has actually finished processing, so a crash mid-processing can effectively lose that record from the pipeline's point of view even though Kafka considers it "committed." Setting `enable.auto.commit=false` and committing only after business logic finishes ensures a crash results in the record being redelivered and reprocessed, preserving at-least-once semantics.
</details>

13. What resource matters more than CPU for most Kafka broker workloads, and why?

<details>

<summary>Show Answer</summary>

**Answer: Memory — specifically, OS page cache**

**Explanation:**
Kafka is designed to serve most reads out of the page cache, so for the common case of consumers reading recent data, the RAM left over after the broker heap directly determines read throughput. This is why memory-optimized instances (`r6g`/`r7g`, for example) often deliver better price/performance for Kafka brokers than compute-optimized ones.
</details>

14. What Strimzi listener field restricts which pods/namespaces can reach the broker port?

<details>

<summary>Show Answer</summary>

**Answer: `networkPolicyPeers`**

**Explanation:**
Setting `networkPolicyPeers` on a Strimzi listener causes Strimzi to generate a standard Kubernetes `NetworkPolicy` that only allows traffic to that listener port from pods/namespaces matching the specified `podSelector`/`namespaceSelector`. This lets you declaratively control which workloads can even reach the Kafka listener.
</details>

15. Does EBS volume encryption happen automatically just because you're using the EBS CSI driver? Name two ways to turn it on explicitly.

<details>

<summary>Show Answer</summary>

**Answer: No, it does not happen automatically. (1) Enable the account/region-level "EBS encryption by default" setting, or (2) set `encrypted: "true"` (and optionally `kmsKeyId`) in the `StorageClass` parameters**

**Explanation:**
The EBS CSI driver does not force encryption on its own — an unencrypted `StorageClass` produces unencrypted volumes. You need to either enable the account/region-wide "EBS encryption by default" setting so every new volume is encrypted automatically, or explicitly set `encrypted: "true"` on the `StorageClass` used for broker PVCs. Since Kafka clusters frequently carry compliance-sensitive data, treating this as the default rather than an afterthought is the safer choice.
</details>

## Hands-on Questions

16. Write producer settings for a durability-critical topic (e.g. order processing), covering `acks`, the `min.insync.replicas` consideration, idempotence, and compression.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
# Producer settings (assuming the topic has replication.factor=3, min.insync.replicas=2)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

**Explanation:**
`acks=all` waits for acknowledgment from the entire ISR, guaranteeing durability, and combined with the topic's `min.insync.replicas=2` (assuming `replication.factor=3`), the pipeline tolerates a single broker failure without data loss. `enable.idempotence=true` (the Kafka 3.0+ default) prevents duplicate writes from retries, and `compression.type=lz4` gives a good balance of CPU overhead and compression ratio for most workloads. `linger.ms`/`batch.size` trade a little latency for larger, more efficient batches.
</details>

17. Write a `KafkaUser` resource using TLS authentication for an application named `order-service` that needs read/write access to the `orders` topic and read access to the `order-service-group` consumer group.

<details>

<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
Setting `authentication.type: tls` causes Strimzi to issue a client certificate signed by the cluster CA into a Secret automatically. `authorization.type: simple` with an `acls` list declaratively grants Read/Write/Describe on the `orders` topic and Read on the `order-service-group` consumer group. The `strimzi.io/cluster` label tells the Strimzi Operator which `Kafka` cluster this `KafkaUser` belongs to.
</details>

18. Write consumer settings so that brief pod restarts don't trigger a rebalance, and offsets are only committed after processing completes.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
heartbeat.interval.ms=15000
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
    consumer.commitSync();
}
```

**Explanation:**
`group.instance.id` (set uniquely, e.g. from the pod name) enables static group membership, so the consumer keeps its existing partition assignment with no rebalance as long as it reconnects within `session.timeout.ms`. `enable.auto.commit=false` combined with `commitSync()` called only after processing finishes ensures only fully-processed records get their offsets committed, preserving at-least-once semantics. `max.poll.records`/`max.poll.interval.ms` are tuned to the actual per-batch processing time to further avoid unnecessary rebalances.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/08-best-practices.md) | [Back to Kafka Deep Dive Home](../../../data-on-eks/kafka/README.md)
