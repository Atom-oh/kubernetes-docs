# Kafka Fundamentals Quiz

This quiz tests your understanding of Kafka's broker/topic/partition model, ordering guarantees, consumer group rebalancing, KRaft, and replication/durability settings.

## Multiple Choice Questions

1. Within what scope does Kafka guarantee message ordering?
   - A) Across the entire cluster
   - B) Across an entire topic (across all its partitions)
   - C) Only within the same partition
   - D) Only within the same consumer group

<details>

<summary>Show Answer</summary>

**Answer: C) Only within the same partition**

**Explanation:**
Kafka only guarantees message ordering within a single partition. If a topic has multiple partitions, there is no guaranteed relative order between messages stored in different partitions, regardless of the order the producer sent them in. To preserve ordering for a specific entity's events (for example, events for a given order ID), you must use a key that identifies that entity so all its events are routed to the same partition.
</details>

2. What does ISR (In-Sync Replicas) refer to?
   - A) The set of all brokers registered in the cluster
   - B) The set of replicas that are sufficiently caught up with the leader
   - C) The set of replicas that are ineligible to become leader
   - D) The set of consumers belonging to a consumer group

<details>

<summary>Show Answer</summary>

**Answer: B) The set of replicas that are sufficiently caught up with the leader**

**Explanation:**
ISR (In-Sync Replicas) is the set of follower replicas (plus the leader itself) whose data is sufficiently synchronized with the partition's leader replica. When a write is sent with `acks=all`, it is only considered successful once every replica in the ISR has received the message. A follower that falls too far behind the leader is removed from the ISR, which acts as a safeguard for data consistency during failures.
</details>

3. What is the default value of a Kafka consumer's `enable.auto.commit` setting?
   - A) `false`
   - B) `true`
   - C) It depends on the broker configuration
   - D) The setting was removed starting in Kafka 3.x

<details>

<summary>Show Answer</summary>

**Answer: B) `true`**

**Explanation:**
The default value of `enable.auto.commit` is `true`, in which case the consumer automatically commits offsets every `auto.commit.interval.ms` (5 seconds by default). This is convenient, but the offset can be committed before message processing actually finishes, risking message loss on failure. To commit only after processing completes, set `enable.auto.commit=false` and call `commitSync()` or `commitAsync()` explicitly.
</details>

4. Which of the following does NOT trigger a consumer group rebalance?
   - A) A new consumer joins the group
   - B) A consumer fails to send a heartbeat within `session.timeout.ms`
   - C) The number of partitions on the topic changes
   - D) A producer sends a message with `acks=all`

<details>

<summary>Show Answer</summary>

**Answer: D) A producer sends a message with `acks=all`**

**Explanation:**
Rebalances happen when consumer group membership changes or the partition layout of the subscribed topic changes: consumers joining or leaving, heartbeat timeouts, exceeding `max.poll.interval.ms`, or a change in partition count are the typical triggers. `acks`, on the other hand, is a producer-side setting that determines how the producer confirms a write completed — it has nothing to do with a consumer group's partition assignment or rebalancing.
</details>

5. Starting with which Kafka version did KRaft (Kafka Raft metadata mode) become production-ready (GA)?
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Show Answer</summary>

**Answer: B) Kafka 3.3**

**Explanation:**
KRaft was first introduced as an early-access preview in Kafka 2.8, but it did not become production-ready (General Availability) until Kafka 3.3. It continued to stabilize over subsequent minor releases, and Kafka 4.0 removed ZooKeeper mode entirely, making KRaft the only supported metadata management mechanism.
</details>

6. In which Kafka version was ZooKeeper mode removed entirely, leaving KRaft as the only metadata management mechanism?
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>Show Answer</summary>

**Answer: D) Kafka 4.0**

**Explanation:**
Kafka 4.0 (released in March 2025) completely removed the ZooKeeper-based metadata management mode. From this version on, new clusters can only be bootstrapped in KRaft mode, and existing ZooKeeper-based clusters must complete a migration to KRaft on Kafka 3.x before upgrading to 4.0.
</details>

7. If a topic is configured with `replication.factor=3` and `min.insync.replicas=2`, and the producer uses `acks=all`, what is the maximum number of simultaneous broker failures the topic can tolerate while still accepting writes?
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>Show Answer</summary>

**Answer: B) 1**

**Explanation:**
With a replication factor of 3, each partition is stored on 3 replicas. `min.insync.replicas=2` means at least 2 replicas must remain in the ISR for an `acks=all` write to succeed. If one broker fails, the remaining 2 replicas stay in the ISR, so writes continue to succeed. But if two brokers fail simultaneously, the ISR shrinks to just 1, no longer satisfying `min.insync.replicas`, and the producer receives a `NotEnoughReplicasException`.
</details>

8. Which producer `acks` setting has the lowest durability but the lowest latency?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>Show Answer</summary>

**Answer: A) `acks=0`**

**Explanation:**
`acks=0` means the producer does not wait for any response from the broker at all — it considers the write successful the instant the message is sent. This is the fastest option in terms of latency and throughput, but if a network issue or broker failure occurs, there is no way to know whether the message was actually stored, making it the riskiest option for data loss. Note that `acks=all` and `acks=-1` mean the same thing — the safest setting, requiring every ISR replica to acknowledge the write before it's considered successful.
</details>

9. In the KRaft architecture, what is the single node called that actually processes cluster metadata changes (partition leader election, topic creation, etc.)?
   - A) Controller Voter
   - B) Active Controller
   - C) Partition Leader
   - D) Metadata Broker

<details>

<summary>Show Answer</summary>

**Answer: B) Active Controller**

**Explanation:**
In KRaft, several controller voters (typically 3 or 5, an odd number for Raft quorum) participate in replicating the metadata log, and one of them is elected Active Controller through Raft consensus. Only the Active Controller actually processes cluster metadata changes; if it fails, a new Active Controller is elected from the remaining voters.
</details>

10. What is the main purpose of using the `CooperativeStickyAssignor`?
    - A) To change how the producer hashes partition keys
    - B) To minimize partition movement during a rebalance, reducing its cost
    - C) To dynamically adjust the number of voters in the controller quorum
    - D) To increase the number of replicas included in the ISR

<details>

<summary>Show Answer</summary>

**Answer: B) To minimize partition movement during a rebalance, reducing its cost**

**Explanation:**
The traditional eager rebalancing protocol requires every consumer to give up all of its owned partitions and get reassigned from scratch whenever a rebalance starts. `CooperativeStickyAssignor` uses a cooperative rebalancing protocol that only reassigns the partitions that actually need to move, letting existing consumers keep the partitions they already own. This reduces the number of partitions whose consumption is interrupted during a rebalance, mitigating the overall throughput hit.
</details>

## Short Answer Questions

11. What is the name of the internal Kafka topic where cluster metadata is stored in KRaft mode?

<details>

<summary>Show Answer</summary>

**Answer: `__cluster_metadata`**

**Explanation:**
In KRaft mode, instead of relying on a separate ZooKeeper ensemble, Kafka stores cluster metadata (topic/partition information, ACLs, controller state change history, etc.) as an event log in an internal topic named `__cluster_metadata`. Controller quorum voters replicate this topic via the Raft protocol, and brokers subscribe to it to stay current with the latest metadata. This design lets Kafka reuse its own core storage model — the partition log — for metadata management as well.
</details>

12. What producer setting is enabled to prevent duplicate message writes caused by network retries?

<details>

<summary>Show Answer</summary>

**Answer: `enable.idempotence` (the idempotent producer, `enable.idempotence=true`)**

**Explanation:**
Setting `enable.idempotence=true` causes the producer to attach a sequence number and producer ID to each message, which the broker uses to detect and discard duplicate writes caused by retries. This setting is the foundation for achieving exactly-once writes within Kafka (at the topic level), and combining it with `transactional.id` extends that guarantee to atomic writes spanning multiple partitions or topics.
</details>

13. What is the term for the situation where traffic concentrates on a small number of partitions because the chosen partition key has low cardinality (few distinct values)?

<details>

<summary>Show Answer</summary>

**Answer: Hot Partition**

**Explanation:**
A hot partition occurs when the values chosen as the partition key don't have enough cardinality (distinct values), or when a particular value occurs disproportionately often. For example, if most of the traffic is concentrated on a handful of large customer IDs, only the partitions those keys hash to receive excessive load while the rest sit idle. This defeats the benefit of parallel consumer processing, so traffic distribution should be reviewed carefully when designing the key.
</details>

14. What setting controls the maximum time a consumer can spend processing messages between calls to `poll()`, and triggers a rebalance if exceeded because the consumer is considered to have left the group?

<details>

<summary>Show Answer</summary>

**Answer: `max.poll.interval.ms`**

**Explanation:**
`max.poll.interval.ms` specifies the maximum allowed time between consecutive `poll()` calls (5 minutes by default). If processing the records returned from a single `poll()` takes longer than this, the broker considers the consumer no longer alive, removes it from the group, and triggers a rebalance. This is a separate mechanism from `session.timeout.ms`, which is governed by a separate heartbeat thread; if processing logic is slow, you should either increase this value or reduce `max.poll.records` to shrink the batch size.
</details>

## Hands-on Questions

15. Write the `kafka-topics.sh` command to create a topic named `events` with 8 partitions, a replication factor of 3, and `min.insync.replicas=2`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**Explanation:**
`--partitions 8` splits the topic into 8 partitions, allowing up to 8 consumers to consume it in parallel. `--replication-factor 3` copies each partition to 3 brokers, preserving data through up to 2 broker failures. `--config min.insync.replicas=2` enforces that at least 2 replicas remain in the ISR for an `acks=all` write to succeed, which combined with the replication factor keeps writes available through a single broker failure.
</details>

16. Write a sample `server.properties` configuration for a dedicated 3-node KRaft controller quorum (controller role only, no broker role). Use node IDs 90, 91, and 92.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
# server.properties for one dedicated controller node (e.g., node.id=90)
process.roles=controller
node.id=90

controller.quorum.voters=90@kraft-controller-0:9093,91@kraft-controller-1:9093,92@kraft-controller-2:9093

listeners=CONTROLLER://:9093
controller.listener.names=CONTROLLER

log.dirs=/var/lib/kafka/controller-data
```

**Explanation:**
Setting `process.roles=controller` means this node only acts as a controller quorum voter and does not serve broker traffic. In larger clusters, separating the controller role from the broker role this way keeps metadata processing load from competing with data processing load, improving stability. `controller.quorum.voters` must list every node participating in the controller quorum as `node.id@host:port`, and using an odd count (3 or 5) lets the cluster compute a clear Raft quorum majority.
</details>

17. Write a producer configuration (Java properties format) that combines `acks=all`, idempotent writes, and a transactional ID to achieve exactly-once writes.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all
enable.idempotence=true
transactional.id=order-producer-1
max.in.flight.requests.per.connection=5
retries=2147483647
```

**Explanation:**
`acks=all` requires every ISR replica to receive the message before the write is considered successful, and `enable.idempotence=true` eliminates duplicate writes caused by retries. Setting `transactional.id` makes the producer a transactional producer, letting it use the `initTransactions()`, `beginTransaction()`, and `commitTransaction()` APIs to atomically write across multiple partitions. Setting `retries` very high is safe once `enable.idempotence=true` is set, since ordering and duplicates are managed automatically; `max.in.flight.requests.per.connection` must stay at 5 or below to avoid breaking ordering guarantees.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [Next Quiz: Strimzi Operator](./02-strimzi-operator-quiz.md)
