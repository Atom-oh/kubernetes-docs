# Kafka Fundamentals Quiz

> **Last Updated**: September 12, 2026, Kafka 4.3.1.

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
The guarantee is partition log order. Same-key routing requires consistent serialization, partitioner and partition count; resizing or client changes can change the mapping. Business-event time and parallel application processing require separate ordering contracts.
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
ISR contains sufficiently synchronized replicas, including the leader. acks=all waits for the current full ISR, while min.insync.replicas constrains its minimum size. Acknowledgement is not equivalent to fsync of every record.
</details>

3. What is the default enable.auto.commit value for Kafka 4.3 Java KafkaConsumer?
   - A) `false`
   - B) `true`
   - C) It depends on the broker configuration
   - D) The setting was removed starting in Kafka 3.x

<details>

<summary>Show Answer</summary>

**Answer: B) `true`**

**Explanation:**
Kafka 4.3 Java KafkaConsumer defaults to true with a 5000 ms interval. Client position is not external business completion. In asynchronous/parallel processing, avoid committing beyond unfinished work. Manual commit also requires correct completed-position accounting.
</details>

4. Which of the following does NOT trigger a consumer group rebalance?
   - A) A new consumer joins the group
   - B) A Classic-protocol consumer fails to send a heartbeat within `session.timeout.ms`
   - C) The number of partitions on the topic changes
   - D) A producer sends a message with `acks=all`

<details>

<summary>Show Answer</summary>

**Answer: D) A producer sends a message with `acks=all`**

**Explanation:**
Membership, subscribed partitions and heartbeat/poll timeouts affect assignment. Classic uses client session.timeout.ms; the consumer protocol uses broker group.consumer.session.timeout.ms. acks controls producer acknowledgements.
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

7. With three healthy ISR replicas and other requirements such as controller quorum maintained, how many broker failures can RF=3/min ISR=2/acks=all tolerate while retaining write availability?
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>Show Answer</summary>

**Answer: B) 1**

**Explanation:**
This assumes all three replicas initially belong to a healthy ISR and controller quorum, networking and storage remain viable. Two remaining ISR members satisfy the minimum after one broker failure, though transition errors/retries can occur. Two replica failures do not preserve write availability. RF=3 alone does not guarantee data survival under arbitrary two-broker failures.
</details>

8. Which acks setting does not wait for a broker acknowledgement?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>Show Answer</summary>

**Answer: A) `acks=0`**

**Explanation:**
acks=0 waits for no broker response, cannot confirm storage and returns offset -1. It does not guarantee the best latency/throughput under every load. It conflicts with explicitly enabled idempotence. acks=all and -1 are equivalent.
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
One controller voter is elected active controller. Electing a replacement requires the necessary majority and connectivity. Dedicated controllers need not serve the broker data role.
</details>

10. What is the purpose of CooperativeStickyAssignor in the Classic group protocol?
    - A) To change how the producer hashes partition keys
    - B) To minimize partition movement during a rebalance, reducing its cost
    - C) To dynamically adjust the number of voters in the controller quorum
    - D) To increase the number of replicas included in the ISR

<details>

<summary>Show Answer</summary>

**Answer: B) To minimize partition movement during a rebalance, reducing its cost**

**Explanation:**
CooperativeStickyAssignor is a client assignor for the Classic group protocol. Incremental reassignment reduces unnecessary disruption. The newer consumer protocol uses server-side assignors, so the same client-class configuration does not apply.
</details>

## Short Answer Questions

11. What is the name of KRaft's internal metadata Raft log?

<details>

<summary>Show Answer</summary>

**Answer: `__cluster_metadata`**

**Explanation:**
__cluster_metadata is KRaft's internal metadata Raft log, commonly visible as a __cluster_metadata-0 directory. It is not an ordinary application topic managed through KafkaProducer/KafkaConsumer; controllers and brokers use metadata replication/fetch paths.
</details>

12. What producer setting is enabled to prevent duplicate message writes caused by network retries?

<details>

<summary>Show Answer</summary>

**Answer: `enable.idempotence` (the idempotent producer, `enable.idempotence=true`)**

**Explanation:**
Producer IDs, epochs and sequences suppress duplicates of the same retried transmission. They do not generally deduplicate an application submitting a business event as a new send. Transactions require logical-writer identity/fencing, atomic output/input-offset commits and read_committed consumption.
</details>

13. What is the term for the situation where traffic concentrates on a small number of partitions because the chosen partition key has low cardinality (few distinct values)?

<details>

<summary>Show Answer</summary>

**Answer: Hot Partition**

**Explanation:**
A hot partition occurs when the values chosen as the partition key don't have enough cardinality (distinct values), or when a particular value occurs disproportionately often. For example, if most of the traffic is concentrated on a handful of large customer IDs, only the partitions those keys hash to receive excessive load while the rest sit idle. This defeats the benefit of parallel consumer processing, so traffic distribution should be reviewed carefully when designing the key.
</details>

14. Which setting bounds the interval between consecutive KafkaConsumer poll() calls?

<details>

<summary>Show Answer</summary>

**Answer: `max.poll.interval.ms`**

**Explanation:**
The default is 300000 ms. With static membership (group.instance.id), exceeding it does not immediately reassign partitions; session timeout after heartbeats stop also matters. Check Classic/consumer timeout rules and tune processing, poll size and execution model together.
</details>

## Hands-on Questions

15. Write the `kafka-topics.sh` command to create a topic named `events` with 8 partitions, a replication factor of 3, and `min.insync.replicas=2`.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
kafka-topics.sh --create \
  --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**Explanation:**
This assumes a reachable cluster with at least three brokers and appropriate authentication. Eight partitions permit up to eight active owners in an automatically assigned partition-based group; one consumer can own several. Failure tolerance depends on actual synchronization, quorum and other conditions.
</details>

16. Write a Kafka 4.3.1 dynamic-quorum configuration excerpt for dedicated controller node.id=90 with three discovery endpoints, and explain why seeds are not voter membership.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
# Configuration excerpt for node 90; these DNS names must resolve in the deployment.
process.roles=controller
node.id=90
controller.quorum.bootstrap.servers=controller-0.example.internal:9093,controller-1.example.internal:9093,controller-2.example.internal:9093
listeners=CONTROLLER://controller-0.example.internal:9093
advertised.listeners=CONTROLLER://controller-0.example.internal:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=./controller-90-data
```

**Explanation:**
controller.quorum.bootstrap.servers is a discovery seed list, not voter membership. Initial format/bootstrap must coordinate cluster ID, directory IDs and initial voters. Do not set controller.quorum.voters for a dynamic quorum. Match DNS, listeners and TLS/authentication to the deployment; this is a configuration excerpt, not a complete deployable cluster.
</details>

17. Provide producer settings for idempotence and a transactional ID, and explain the additional steps needed for Kafka-to-Kafka exactly-once processing.

<details>

<summary>Show Answer</summary>

**Answer:**
```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**Explanation:**
Configuration only prepares a producer for transactions. Implement initTransactions, beginTransaction, output sends, sendOffsetsToTransaction with next input offsets, commitTransaction, and abort/recovery handling. Consumers disable auto commit and use read_committed. Concurrent writers need distinct transactional IDs; deadlines such as delivery.timeout.ms still apply.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [Next Quiz: Strimzi Operator](./02-strimzi-operator-quiz.md)
