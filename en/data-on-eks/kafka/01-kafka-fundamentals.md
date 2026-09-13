# Part 1: Kafka Fundamentals

> **Last Updated**: September 12, 2026. Apache Kafka 4.3.1, supported by Strimzi 1.2.0.
> **Validation**: Nineteen checks used Kafka 4.3.1's actual configuration classes for validity, defaults and conflicts. No broker or EKS cluster was started.

## 1. Brokers, Topics and Partitions

Kafka stores events in partition logs, allowing producers and consumers to progress independently. A broker can store partition replicas from several topics; it need not hold an entire topic.

| Term | Meaning |
| --- | --- |
| Broker | Server role storing data replicas and handling requests |
| Topic | Logical event category |
| Partition | An ordered append log; retention and compaction can remove records |
| Offset | A position within one partition, not a global ID; deletion and transactions can leave visible gaps |
| Replication factor | Number of partition replicas, managed through creation/reassignment metadata |
| Leader / follower | Leaders handle writes and followers replicate; configured follower fetching can serve consumer reads |
| ISR | Replicas sufficiently synchronized with the leader, including the leader itself |

![Example KafkaConsumer group with three consumers assigned three partitions; generally one consumer may own several partitions](../../.gitbook/assets/en-data-on-eks-kafka-01-kafka-fundamentals-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-kafka-01-kafka-fundamentals-0.html)

The 3:3 diagram is one example. With KafkaConsumer `subscribe()` automatic group assignment, one partition is assigned to one group member at a time; one member can own multiple partitions. Manual `assign()` usage is managed separately. Multiple groups can independently consume the same topic. Kafka 4.x Share Groups/KafkaShareConsumer use a different sharing and acknowledgement model.

## 2. Ordering and Partition Keys

Kafka defines log order **within a partition**. It does not automatically establish global topic order or business-event timestamp order.

Consistent same-key routing requires consistent serialization, partitioning and partition count. Increasing partition count can change hash-based mapping. Custom partitioners and explicitly chosen partitions also affect routing. Multiple producers, retries and parallel application processing require their own ordering contract.

Null-key routing depends on the client/partitioner. High key cardinality alone does not guarantee balanced load; a few disproportionately frequent keys can still create hot partitions.

This command creates a topic in an **already reachable cluster with at least three brokers**. Add `--command-config client.properties` for authenticated listeners. Do not apply it unchanged to the single-node learning configuration below.

```bash
: "${DOCS_BOOTSTRAP:?Set the existing Kafka bootstrap host:port}"
kafka-topics.sh --create --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic orders --partitions 6 --replication-factor 3 \
  --config min.insync.replicas=2
```

## 3. Consumer Groups and Offsets

Partition-based groups can have idle members when consumers outnumber partitions. Producer throughput, disks, networking and application processing also affect concurrency; partition count alone does not predict throughput.

### Distinguish group protocols

The Kafka 4.3 Java consumer defaults `group.protocol` to `classic`.

| Choice | Assignment and timeouts |
| --- | --- |
| `classic` | Client assignors and `session.timeout.ms` / `heartbeat.interval.ms` |
| `consumer` | Server assignors and broker `group.consumer.session.timeout.ms` / `group.consumer.heartbeat.interval.ms` |

Classic eager rebalance revokes a broad set of assignments. CooperativeStickyAssignor incrementally moves partitions that need reassignment. The newer consumer protocol also performs server-side incremental reconciliation. Not every rebalance necessarily pauses the whole group. Do not carry classic client assignor/timeout assumptions into the new protocol.

`max.poll.interval.ms` defaults to 300000 ms. With static membership (`group.instance.id`), exceeding it does not immediately reassign partitions: the consumer stops heartbeats, and the applicable session timeout also affects reassignment.

### Offsets and business completion

A committed offset generally identifies the next position to read. Client fetch position and completed external work are different facts. With asynchronous/parallel processing, do not commit past records whose work is still unfinished.

| Method | Meaning and consideration |
| --- | --- |
| Auto commit | `enable.auto.commit=true`, default interval 5000 ms; does not determine business completion |
| `commitSync()` | Waits for the call; latency impact depends on batching and frequency |
| `commitAsync()` | Track failures/progress through callbacks; do not blindly retry stale offsets and move committed progress backwards |

Commit-before-processing can lose work after failure; commit-after-processing can repeat effects during recovery. Test failures, restarts and rebalances together with the application output.

## 4. The Scope of Exactly-Once

`enable.idempotence` prevents duplicate log writes of the same producer transmission during retry. It is not a general deduplication key for an application submitting the same business event as a new send.

For Kafka-to-Kafka processing, commit output records and the **next input offsets** in the same transaction, and have consumers read with `read_committed`. Setting a `transactional.id` string does not implement that processing logic. External databases/APIs require separate sink transaction, idempotency and recovery contracts.

**`producer.properties`**

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

**`consumer.properties`**

```properties
bootstrap.servers=127.0.0.1:19092
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=org.apache.kafka.common.serialization.StringDeserializer
group.id=order-processor
group.protocol=consumer
enable.auto.commit=false
isolation.level=read_committed
max.poll.interval.ms=300000
```

Transactional processing includes `initTransactions()`, `beginTransaction()`, output sends, `sendOffsetsToTransaction(...)`, `commitTransaction()` and abort/recovery handling. Concurrent producers need distinct transactional IDs; design stable logical-writer restart and fencing behavior.

Explicit idempotence requires `acks=all`, `retries>0` and `max.in.flight.requests.per.connection<=5`. Conflicts raise ConfigException. Implicit default idempotence can be disabled by conflicting settings. A large retries value does not override deadlines such as `delivery.timeout.ms`.

## 5. KRaft Metadata

KRaft arrived as early access in Kafka 2.8, became production-ready in 3.3, and is the only mode after ZooKeeper removal in Kafka 4.0. Dedicated controller processes need not serve broker data traffic, so controllers are not necessarily a subset of data brokers.

Controller voters replicate the metadata Raft log, with one active controller. Production deployments commonly use three or five voters. Even-sized groups also have a calculable majority; odd sizes use resources efficiently for the same failure tolerance.

`__cluster_metadata` names the internal metadata log, not an ordinary application topic managed through KafkaProducer/KafkaConsumer. Removing ZooKeeper does not remove responsibility for controller quorum, storage, upgrades and monitoring.

### Dynamic and static quorums

Dynamic quorums use `controller.quorum.bootstrap.servers` as discovery seeds, not voter membership. Initial storage formatting and quorum bootstrap must agree on cluster ID, directory IDs and initial voters. Use supported controller addition/removal procedures for changes.

Static `controller.quorum.voters` is still supported in Kafka 4.3.1. Do not set it for a dynamic quorum. Merely changing seed addresses does not automatically migrate a static quorum.

This file is for **single-node local learning**, not HA. It uses loopback PLAINTEXT listeners. Before startup, a new data directory needs the appropriate storage format/bootstrap procedure. Never arbitrarily format existing Kafka data.

**`combined-lab.properties`**

```properties
# Local, single-node configuration for learning; not an HA deployment.
process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=127.0.0.1:19093
listeners=BROKER://127.0.0.1:19092,CONTROLLER://127.0.0.1:19093
advertised.listeners=BROKER://127.0.0.1:19092,CONTROLLER://127.0.0.1:19093
listener.security.protocol.map=BROKER:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=BROKER
log.dirs=./kafka-lab-data
# Single-node internal-topic settings are for this lab only.
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
share.coordinator.state.topic.replication.factor=1
share.coordinator.state.topic.min.isr=1
```

A custom `BROKER` listener needs an explicit protocol mapping. Kafka 4.3.1 can supply a PLAINTEXT mapping for the default controller-only `CONTROLLER` listener in relevant configurations; a missing mapping line does not make every controller configuration invalid.

On EKS, use the settings, certificates and storage generated by Strimzi in Part 2. Do not edit Operator-managed Pod server.properties directly. Configure required TLS, authentication and authorization for production listeners.

## 6. Replication, Write Availability and Durability

RF=3 alone does not guarantee that all data survives any two broker failures. Consider actual replication progress, the ISR at acknowledgement, eligible leader election, storage/network failures and controller quorum.

If all three replicas initially belong to a healthy ISR, a partition using `min.insync.replicas=2` and `acks=all` can continue with two ISR members after one broker failure while other conditions hold. Leader transition can still cause errors/retries. Writes fail or are rejected below the minimum ISR, with error details depending on timing.

| acks | Acknowledgement | Interpretation |
| --- | --- | --- |
| `0` | No broker response awaited | Storage is unconfirmed; returned offset is -1 |
| `1` | Leader responds after recording | Risk of leader loss before follower replication |
| `all` / `-1` | Wait for the current full ISR | Evaluate alongside minimum ISR, replication and leader-election policy |

`acks=all` does not mean every disk completed fsync on every record. Nor does acks alone guarantee throughput or p99 rankings. Measure acknowledgement cost with comparable load, batching and networking.

You can change minimum ISR as follows. Changing the replication factor itself requires replica reassignment, not adding `replication.factor` as an ordinary topic config.

```bash
kafka-configs.sh --bootstrap-server "$DOCS_BOOTSTRAP" \
  --alter --entity-type topics --entity-name orders \
  --add-config min.insync.replicas=2
```


## Next Steps and References

- [Strimzi Operator](./02-strimzi-operator.md)
- [Kafka overview](./README.md)
- [Quiz](../../quizzes/data-on-eks/kafka/01-kafka-fundamentals-quiz.md)
- [Kafka design](https://kafka.apache.org/43/design/design/)
- [Consumer configurations](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Producer configurations](https://kafka.apache.org/43/configuration/producer-configs/)
- [KRaft operations](https://kafka.apache.org/43/operations/kraft/)
- [Strimzi 1.2.0 release and migration notice](https://github.com/strimzi/strimzi-kafka-operator/releases/tag/1.2.0)
