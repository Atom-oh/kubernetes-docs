# Kafka Connect and MirrorMaker Quiz

This quiz tests your understanding of Kafka Connect's source/sink connector model, distributed mode, Strimzi's `KafkaConnect`/`KafkaConnector` CRDs, and MirrorMaker 2's architecture and disaster recovery patterns.

## Multiple Choice Questions

1. A connector like Debezium, which reads a database's WAL/binlog and streams change events into Kafka, is what kind of connector?
   - A) Sink connector
   - B) Source connector
   - C) Filter connector
   - D) Transform connector

<details>

<summary>Show Answer</summary>

**Answer: B) Source connector**

**Explanation:**
Source connectors pull data INTO Kafka from an external system. Debezium is the canonical example of a CDC (Change Data Capture) source connector: it reads a database's write-ahead log (or binlog) and streams row-level change events into Kafka. Sink connectors do the opposite — they push data OUT of Kafka into external systems like S3 or Elasticsearch.
</details>

2. What do the S3 Sink Connector and Elasticsearch Sink Connector have in common?
   - A) They pull data from an external system into Kafka
   - B) They push data from a Kafka topic out to an external system
   - C) They replicate data between topics
   - D) They manage consumer group offsets

<details>

<summary>Show Answer</summary>

**Answer: B) They push data from a Kafka topic out to an external system**

**Explanation:**
Both the S3 Sink Connector and the Elasticsearch Sink Connector are sink connectors, meaning they push data accumulated in a Kafka topic out to an external system. S3 Sink Connector writes topic data to an S3 bucket in formats like JSON or Parquet, while Elasticsearch Sink Connector indexes topic data for search and analytics.
</details>

3. In Kafka Connect's distributed mode, what happens when one worker dies?
   - A) The entire Connect cluster stops
   - B) The dead worker's tasks are automatically rebalanced onto other surviving workers
   - C) The connector automatically switches to standalone mode
   - D) All offset information is reset

<details>

<summary>Show Answer</summary>

**Answer: B) The dead worker's tasks are automatically rebalanced onto other surviving workers**

**Explanation:**
In distributed mode, multiple worker processes form a group that acts as a single Connect cluster, with a group coordinator distributing connectors and tasks across the workers. If a worker dies, the coordinator detects it and automatically rebalances that worker's tasks onto the remaining workers to maintain availability. This is the key difference from standalone mode, which runs as a single process with no high availability.
</details>

4. Why is Kafka Connect's standalone mode never used in Kubernetes/Strimzi environments?
   - A) It doesn't support a REST API
   - B) It has no high availability or horizontal scalability
   - C) It only supports source connectors
   - D) It doesn't support TLS

<details>

<summary>Show Answer</summary>

**Answer: B) It has no high availability or horizontal scalability**

**Explanation:**
Standalone mode runs as a single process with a file-based offset store, designed for local development and testing. Since there is only one worker, there's no other worker to take over if it fails, and the workload can't be spread across multiple nodes. Because of these limitations, Kubernetes/Strimzi environments always run distributed mode, backed by multiple worker Pods.
</details>

5. What is the main advantage of using the `KafkaConnector` CRD in Strimzi?
   - A) It lets you manage connectors declaratively through GitOps instead of calling the REST API directly
   - B) It automatically writes connector plugin code for you
   - C) It converts distributed mode into standalone mode
   - D) It eliminates the need for an offset storage topic

<details>

<summary>Show Answer</summary>

**Answer: A) It lets you manage connectors declaratively through GitOps instead of calling the REST API directly**

**Explanation:**
With the `KafkaConnector` CRD, you don't need to call the Connect REST API directly to create, delete, or reconfigure connectors — you declare the desired state in a YAML manifest, and the Strimzi Operator reconciles it against the actual connector state. This enables a GitOps workflow where connector configuration is version-controlled in a Git repository and deployed through code review/CI pipelines.
</details>

6. What annotation is required on a `KafkaConnect` resource to enable the `KafkaConnector` CRD for it?
   - A) `strimzi.io/kraft: enabled`
   - B) `strimzi.io/node-pools: enabled`
   - C) `strimzi.io/use-connector-resources: "true"`
   - D) `strimzi.io/connect-mode: distributed`

<details>

<summary>Show Answer</summary>

**Answer: C) `strimzi.io/use-connector-resources: "true"`**

**Explanation:**
Adding the `strimzi.io/use-connector-resources: "true"` annotation to a `KafkaConnect` resource's metadata tells the Strimzi Operator to watch for `KafkaConnector` resources targeting that Connect cluster and reconcile them into real connectors. Without this annotation, creating `KafkaConnector` resources has no effect.
</details>

7. What characterizes Strimzi's recommended approach to building a custom image with connector plugins via `KafkaConnect.spec.build`?
   - A) You must write a Dockerfile by hand
   - B) You declare plugin artifact URLs, and the Operator builds and pushes the image to the registry you specify
   - C) Images can only be pushed to Docker Hub
   - D) It only works in standalone mode

<details>

<summary>Show Answer</summary>

**Answer: B) You declare plugin artifact URLs, and the Operator builds and pushes the image to the registry you specify**

**Explanation:**
Strimzi's recommended pattern is to declaratively populate `KafkaConnect.spec.build` with an `output` (the target registry image and a push secret) and a list of `plugins` (each specifying tgz/zip/jar artifact URLs or Maven coordinates). No Dockerfile is required — the Strimzi Operator performs the build itself and pushes the resulting image to a registry such as Amazon ECR.
</details>

8. In MirrorMaker 2, which connector is responsible for translating a source cluster's consumer group offsets into the equivalent offsets on the target cluster?
   - A) MirrorSourceConnector
   - B) MirrorHeartbeatConnector
   - C) MirrorCheckpointConnector
   - D) MirrorTopicConnector

<details>

<summary>Show Answer</summary>

**Answer: C) MirrorCheckpointConnector**

**Explanation:**
MirrorCheckpointConnector periodically translates a source cluster's consumer group offsets into the equivalent offsets on the target cluster and records them in a checkpoint topic. This offset translation is what lets a consumer group know "how far it had already processed" when it fails over to the DR cluster and needs to resume consumption. MirrorSourceConnector handles the actual replication of messages, topics, and ACLs, while MirrorHeartbeatConnector sends heartbeats indicating the replication pipeline is alive.
</details>

9. What naming convention does MirrorMaker 2's default `DefaultReplicationPolicy` use for remote topics?
   - A) `<topic>.<source-cluster-alias>`
   - B) `<source-cluster-alias>.<topic>`
   - C) `mirror-<topic>`
   - D) The original topic name unchanged

<details>

<summary>Show Answer</summary>

**Answer: B) `<source-cluster-alias>.<topic>`**

**Explanation:**
`DefaultReplicationPolicy` names remote topics `<source-cluster-alias>.<topic>`. For example, replicating the `orders` topic from a cluster aliased `us-east-1` produces a remote topic named `us-east-1.orders` on the target cluster. Keeping the original name unchanged requires `IdentityReplicationPolicy` instead, which makes loop prevention harder in an active-active setup.
</details>

10. What is the core difference between the active-passive and active-active DR patterns?
    - A) Active-passive compresses data and active-active does not
    - B) Active-passive replicates one-way only, while active-active replicates bidirectionally and requires loop prevention
    - C) Active-active does not use MirrorMaker 2
    - D) Only active-passive uses the KafkaConnector CRD

<details>

<summary>Show Answer</summary>

**Answer: B) Active-passive replicates one-way only, while active-active replicates bidirectionally and requires loop prevention**

**Explanation:**
The active-passive pattern replicates one-way, from the primary cluster to the DR cluster, and the DR cluster normally sits idle. The active-active pattern replicates bidirectionally between both clusters so both regions can serve traffic, but this means a replicated topic could be mirrored right back to its origin cluster, causing an infinite loop, unless it's explicitly prevented through `replication.policy.class` and topic filters.
</details>

## Short Answer Questions

11. What is the name of the MirrorMaker 2 connector that periodically sends heartbeat messages to signal that the source cluster is alive and the replication pipeline is functioning?

<details>

<summary>Show Answer</summary>

**Answer: MirrorHeartbeatConnector**

**Explanation:**
MirrorHeartbeatConnector periodically sends heartbeat messages indicating that the source cluster is operating normally and the replication pipeline has not been disrupted. If these heartbeats stop arriving for a period of time, that absence can be used as a signal to detect replication lag or a broken connection to the source cluster.
</details>

12. What are the names of the three internal topic configuration keys that Strimzi Kafka Connect's distributed workers use to store offsets, connector/task configuration, and task status? (e.g., offset.storage.topic)

<details>

<summary>Show Answer</summary>

**Answer: `offset.storage.topic`, `config.storage.topic`, `status.storage.topic`**

**Explanation:**
Distributed-mode Connect workers use three internal topics: `offset.storage.topic` for offsets, `config.storage.topic` for connector/task configuration, and `status.storage.topic` for task status. If these topics are lost, every connector on the cluster loses its state, so production deployments must set their replication factor to at least 3.
</details>

13. What configuration key controls whether MirrorMaker 2 also syncs the source cluster's topic ACLs to the target cluster?

<details>

<summary>Show Answer</summary>

**Answer: `sync.topic.acls.enabled`**

**Explanation:**
Setting `sync.topic.acls.enabled` to `true` causes the source cluster's topic ACLs to be synced to the target cluster as well, so access control policy doesn't need to be maintained twice. However, if the two clusters have different security postures — for example, if the DR cluster requires stricter access control — it may be safer to disable this and manage ACLs independently on each side.
</details>

14. What is the name of the metric MirrorMaker 2 exposes that reports the time from when a message was produced on the source cluster to when it was fully replicated to the target?

<details>

<summary>Show Answer</summary>

**Answer: `replication-latency-ms`**

**Explanation:**
`replication-latency-ms` is one of MirrorMaker 2's core exposed metrics, reporting the elapsed time from when a message was produced on the source cluster to when it was fully replicated to the target cluster. Scraping this into Prometheus and alerting on it lets you continuously verify a replication lag SLA.
</details>

15. In Strimzi, what `spec` field on a `KafkaMirrorMaker2` resource specifies which of the configured clusters the MM2 worker Pods should use to store their own internal topics (offsets, configuration, etc.)?

<details>

<summary>Show Answer</summary>

**Answer: `connectCluster`**

**Explanation:**
`KafkaMirrorMaker2.spec.connectCluster` points to one of the cluster aliases defined in `spec.clusters`, determining which cluster the MM2 worker Pods use to store their own Kafka Connect internal topics (offset, configuration, and status storage topics). This is typically set to the DR or target cluster.
</details>

## Hands-on Questions

16. Write a `KafkaConnector` resource for a Debezium PostgreSQL source connector that runs on a `KafkaConnect` cluster named `connect-cluster` (which has the `strimzi.io/use-connector-resources: "true"` annotation set). Limit it to a single task.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.xxxxxxx.us-east-1.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${secrets:kafka/debezium-db-credentials:password}"
    database.dbname: orders
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    table.include.list: public.orders,public.order_items
```

**Explanation:**
The `metadata.labels.strimzi.io/cluster: connect-cluster` label tells the Strimzi Operator which `KafkaConnect` cluster this `KafkaConnector` should run on. `spec.class` specifies the actual connector implementation class (the Debezium PostgreSQL connector), and `plugin.name: pgoutput` specifies PostgreSQL's logical replication output plugin. `tasksMax: 1` reflects the fact that a PostgreSQL source connector can only use a single replication slot, so its work cannot be parallelized across multiple tasks.
</details>

17. Write a `KafkaMirrorMaker2` resource that one-way replicates topics matching `orders.*` and `payments.*` from a cluster aliased `us-east-1` to a cluster aliased `dr-region`, also syncing consumer group offsets.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 3.9.0
  replicas: 3
  connectCluster: dr-region
  clusters:
    - alias: us-east-1
      bootstrapServers: primary-kafka-bootstrap.us-east-1.example.com:9093
    - alias: dr-region
      bootstrapServers: dr-kafka-bootstrap.us-west-2.example.com:9093
      config:
        config.storage.replication.factor: 3
        offset.storage.replication.factor: 3
        status.storage.replication.factor: 3
  mirrors:
    - sourceCluster: us-east-1
      targetCluster: dr-region
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          sync.topic.acls.enabled: "true"
      heartbeatConnector:
        config:
          heartbeats.topic.replication.factor: 3
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          sync.group.offsets.enabled: "true"
      topicsPattern: "orders.*|payments.*"
      groupsPattern: "orders-consumer-.*"
```

**Explanation:**
Each entry in the `mirrors` list defines one replication direction (`sourceCluster` to `targetCluster`). `topicsPattern` restricts replication to `orders.*` and `payments.*`, and setting `checkpointConnector.config.sync.group.offsets.enabled: "true"` causes the translated consumer group offsets to be written into the target cluster's `__consumer_offsets`. `connectCluster: dr-region` designates the DR region as the cluster where the MM2 workers store their internal topics.
</details>

18. Explain two settings you'd check to prevent a topic from being mirrored infinitely in a loop (A to B to A to B...) in an active-active configuration.

<details>

<summary>Show Answer</summary>

**Answer:**
1. `replication.policy.class` — with the default `DefaultReplicationPolicy`, topics that already carry a remote-cluster prefix (`<alias>.<topic>`) are automatically excluded from further mirroring.
2. `topicsPattern` — narrowing the pattern on each mirror direction to explicitly include only the topics that actually need replication prevents unintended topics from being caught in a replication cycle.

**Explanation:**
`DefaultReplicationPolicy`'s naming convention (`<source-cluster-alias>.<topic>`) is itself the first line of defense against loops: if cluster B tries to mirror a topic like `A.orders` back to cluster A, MM2 recognizes it as an already-prefixed remote topic and does not re-mirror it. On top of that, explicitly narrowing `topicsPattern` for each mirror direction reduces the risk of a configuration mistake or an unusual topic naming pattern accidentally triggering a replication loop.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Next Quiz: MSK Integration](./06-msk-integration-quiz.md)
