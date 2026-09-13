# Part 8: Best Practices Quiz

Assess partitions, clients, security, capacity and recovery against actual conditions.

## 1. What should be considered when sizing partitions for a conventional consumer group?

<details>
<summary>Show answer</summary>

Measure member parallelism, per-partition throughput, key skew, record sizes, replica placement and recovery. One partition is assigned to one group member, while share groups and application-internal parallelism differ.

</details>

## 2. Can historical partition-count rules be treated as current universal limits?

<details>
<summary>Show answer</summary>

No. Limits depend on versions, brokers/controllers, replica count and workload. Distinguish logical partitions from per-broker replica placements and test steady-state and failures.

</details>

## 3. Does counting lines containing PartitionCount yield the total partition count?

<details>
<summary>Show answer</summary>

No. It counts topic summary lines. Read Partition: rows, as in partition_summary.py, to count logical partitions and replica placements separately. Check empty results, visibility and filters.

</details>

## 4. Must every key move when increasing a keyed topic's partition count?

<details>
<summary>Show answer</summary>

Not every key must move, but some can remap. Old records remain where they were, affecting key ordering, state and co-partitioned join assumptions. Review serializers, partitioners and topology.

</details>

## 5. Does explicitly configuring acks or retries always disable default idempotence?

<details>
<summary>Show answer</summary>

No. Incompatible settings are the issue. With explicit enable.idempotence=true, acks, retries and max.in.flight must be compatible; conflicts cause a configuration error.

</details>

## 6. Does idempotence or a transactional.id alone provide end-to-end exactly-once?

<details>
<summary>Show answer</summary>

No. Producer retries differ from application resubmissions and external effects. Kafka transactions require atomic output/input-offset commits, fencing/read_committed and the correct lifecycle; external systems need their own strategy.

</details>

## 7. What happens when ISR drops to one with RF=3, acks=all and min.insync.replicas=2?

<details>
<summary>Show answer</summary>

Writes are rejected. acks=all waits for the current ISR, and min ISR is a topic/broker setting. It does not unconditionally guarantee continued writes or zero loss after one failure when replication is already degraded.

</details>

## 8. What distinctions matter for max.poll.interval.ms and heartbeat/session settings?

<details>
<summary>Show answer</summary>

Check actual processing time between polls. Static-member reassignment can wait until session expiry. Distinguish classic client heartbeat/session settings from broker-controlled settings for the consumer protocol.

</details>

## 9. Does static membership guarantee a restart without a rebalance?

<details>
<summary>Show answer</summary>

No. Stable unique identity, reconnect timing, topology, subscriptions and membership all matter. Duplicate active IDs can cause fencing; longer sessions also delay real failure recovery.

</details>

## 10. Which CA signs KafkaUser mTLS client certificates in default Strimzi?

<details>
<summary>Show answer</summary>

The clients CA. The cluster CA is used for broker/internal component certificates. Distinguish client credentials from the CA chain used to trust the broker.

</details>

## 11. Do high cardinality or random salts safely solve key skew by themselves?

<details>
<summary>Show answer</summary>

No. A dominant hot key can still skew traffic. Salting changes ordering, joins and compaction identity; first verify the contract permits it and plan any recombination.

</details>

## 12. Is it safe to skip committing after a processing exception and simply keep polling?

<details>
<summary>Show answer</summary>

No. The fetch position may already have advanced. Stop/recover or seek correctly, and commit only after durable processing. Design for duplicate replay and idempotent external effects.

</details>

## 13. Can Kafka capacity be determined from memory or one fixed heap size alone?

<details>
<summary>Show answer</summary>

No. Measure page cache, TLS/compression CPU, networking, IOPS/throughput, cgroup memory and recovery. Codec and instance cost advantages depend on the data and workload.

</details>

## 14. How do namespaceSelector and podSelector combine within one networkPolicyPeers entry?

<details>
<summary>Show answer</summary>

AND within one peer; separate peer entries are OR. NetworkPolicies are additive and require CNI enforcement and egress review. This entry does not deny traffic another policy allows.

</details>

## 15. Explain StorageClass encryption, Auto Mode and existing volumes.

<details>
<summary>Show answer</summary>

Set encrypted:true and actual KMS permissions for the selected provisioner, then verify EBS. Do not infer all dynamic PVC encryption from Auto Mode node/ephemeral disks. StorageClass/account-default changes do not retroactively encrypt existing volumes.

</details>

## 16. Write the producer tuning profile and explain batch.size and min ISR.

<details>
<summary>Show answer</summary>

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

batch.size controls per-partition batching/allocation, not a strict record/request cap. Configure min.insync.replicas on the topic/broker. Measure codec/linger choices and handle send failures/delivery timeouts.

</details>

## 17. Write a separate mTLS KafkaUser while preserving the existing SCRAM user.

<details>
<summary>Show answer</summary>

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

A listener with tls:true and authentication.type:tls is also required; there is no exposure type named tls. Distribute/rotate clients-CA credentials and broker trust, and verify actual allowed/denied actions.

</details>

## 18. How should an environment-based static member ID be combined with manual commits?

<details>
<summary>Show answer</summary>

Java Properties does not expand ${POD_NAME}. Pass a resolved unique stable ID to setStaticIdentity before creating the consumer. Use enable.auto.commit=false and processOneBatch, and do not swallow failures and continue polling. Retention/recovery and duplicate handling remain necessary.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/08-best-practices.md) | [Next quiz](./09-kafka-benchmark-quiz.md)
