# Kafka Connect and MirrorMaker Quiz

Review the chapter's Strimzi v1 configuration, actual plugins, replication and recovery conditions.

## 1. In which directions do Debezium PostgreSQL and an S3 sink move data?

<details>
<summary>Show answer</summary>

Debezium is a source that sends snapshot/WAL changes into Kafka; an S3 sink sends Kafka records to S3. Check each plugin's formats and delivery behavior.

</details>

## 2. Does archiving Debezium records with the Aiven S3 sink automatically reconstruct the current database table?

<details>
<summary>Show answer</summary>

No. The example archives CDC events with operation and before/after data. Materializing current state requires handling keys, deletes/tombstones, ordering and replay.

</details>

## 3. How do the distributed Connect group coordinator and worker leader differ?

<details>
<summary>Show answer</summary>

A Kafka broker coordinates the group; the elected worker leader computes assignments. Worker failure can trigger delayed reassignment and replay, and differs from a task failure.

</details>

## 4. Is standalone Connect impossible to run on Kubernetes?

<details>
<summary>Show answer</summary>

It can run there, but lacks distributed worker failover. Strimzi KafkaConnect manages distributed mode. More workers do not automatically parallelize a single-task connector.

</details>

## 5. What can happen when directly editing a connector through REST while KafkaConnector CRs manage it?

<details>
<summary>Show answer</summary>

The operator can reconcile it back to the CR's desired state. Use the CR as the mutation path and restrict Kubernetes updates and Connect REST access.

</details>

## 6. Which annotation enables KafkaConnector reconciliation, and what API version is used here?

<details>
<summary>Show answer</summary>

`strimzi.io/use-connector-resources: "true"` and `kafka.strimzi.io/v1`. The v1 migration includes fields such as groupId and internal topic names; changing apiVersion alone is insufficient.

</details>

## 7. What should be pinned and checked in spec.build, and how is ECR authentication handled?

<details>
<summary>Show answer</summary>

Specify plugin versions, URLs, checksums and an output image tag. Maintain a valid push Secret and image-pull permissions; ECR tokens expire after 12 hours. Runtime S3 identity and build-push authentication are separate.

</details>

## 8. What are MM2 offset-sync mappings and checkpoints for?

<details>
<summary>Show answer</summary>

MirrorSourceConnector emits source/target offset mappings; MirrorCheckpointConnector uses them to translate source group commits. Source and target offsets are not assumed to be equal.

</details>

## 9. How does DefaultReplicationPolicy name remote topics and detect cycles?

<details>
<summary>Show answer</summary>

It uses `<source-alias>.<topic>` and detects a cycle back to a target alias already in the origin chain. It does not exclude every prefixed topic; multi-hop replication to a third cluster can be legitimate.

</details>

## 10. What must be prepared beyond MM2 for active-passive failover?

<details>
<summary>Show answer</summary>

Fence old writers, measure replication/checkpoint freshness, verify target permissions and schemas, change endpoints/subscriptions and validate resumed positions. An unrecoverable source can lose unreplicated data; measure duplicate replay too.

</details>

## 11. Does an Apache MirrorHeartbeatTask heartbeat prove that source data replication is healthy?

<details>
<summary>Show answer</summary>

No. The task can emit a heartbeat without reading source data. Also inspect partition progress, errors and checkpoint freshness. Distinguish this Apache class from fields supported by Strimzi 1.2's v1 CRD.

</details>

## 12. What are Connect v1's internal topic fields and their partition/retention requirements?

<details>
<summary>Show answer</summary>

`spec.configStorageTopic`, `spec.offsetStorageTopic` and `spec.statusStorageTopic`. Use compaction and one partition for the config topic. Set the worker group with spec.groupId; sink group offsets are separate.

</details>

## 13. Does sync.topic.acls.enabled=true copy the entire source security policy unchanged?

<details>
<summary>Show answer</summary>

No. Kafka 4.3.1 processes selected literal topic ACLs, excludes ALLOW WRITE and downgrades ALLOW ALL to READ. It does not migrate all users, cluster policies or external IAM policies. The example manages target policies separately.

</details>

## 14. What matters when interpreting replication-latency-ms and cross-region compression?

<details>
<summary>Show answer</summary>

It measures target acknowledgement time minus record timestamp, affected by clock skew, timestamp mode and replay. Compression on a target-region worker's target producer does not reduce source fetch traffic that already crossed regions.

</details>

## 15. Where are target and source connections defined in KafkaMirrorMaker2 v1?

<details>
<summary>Show answer</summary>

`spec.target` and `spec.mirrors[].source`. The target requires alias, bootstrapServers, groupId and three internal topic names. Do not use the old connectCluster/clusters/heartbeatConnector structure.

</details>

## 16. Write the chapter's Debezium PostgreSQL KafkaConnector and describe its prerequisites.

<details>
<summary>Show answer</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
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
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

Prepare logical replication, privileges, publication and suitable replica identity. Read the password through the allowed Secret-directory provider and verify the DB TLS hostname. It uses one task; monitor WAL retained by a stalled slot.

</details>

## 17. What are the key conditions for group-offset synchronization in the chapter's v1 MM2 example?

<details>
<summary>Show answer</summary>

Match source/checkpoint replication policy and offset-syncs location, enabling `sync.group.offsets.enabled=true`. Valid mappings/checkpoints and permissions are required, and the target group must be inactive or absent. Active consumers are not overwritten. Use the target/source structure in the chapter's mm2.yaml.

</details>

## 18. Do IdentityReplicationPolicy and topicsPattern make arbitrary bidirectional writes safe?

<details>
<summary>Show answer</summary>

No. Identity loses origin-prefix information and lacks the default policy's equivalent loop detection. Design directional topic ownership, filters, writer policies and cutover. Topic filters do not automatically resolve data conflicts or duplicates.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [Next quiz](./06-msk-integration-quiz.md)
