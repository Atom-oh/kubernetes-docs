# Part 5: Kafka Connect and MirrorMaker

> **Supported Versions**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **Last Updated**: July 9, 2026

## Kafka Connect Overview

Kafka Connect is a framework for moving data between Kafka and external systems — databases, object storage, search engines, and more — without writing custom integration code. You describe a data pipeline declaratively through connector configuration, and Connect handles the rest.

Connectors come in two flavors, depending on the direction data flows:

* **Source connectors** pull data INTO Kafka from an external system. Debezium is the canonical example: it reads a database's write-ahead log (or binlog) and streams row-level change events into Kafka as a CDC (Change Data Capture) pipeline. JDBC Source Connector takes a simpler query-based approach, periodically polling tables and writing the results to Kafka.
* **Sink connectors** push data OUT of Kafka into an external system. S3 Sink Connector writes topic data to S3 in formats like JSON or Parquet, while Elasticsearch Sink Connector indexes topic records for search and analytics.

Kafka Connect supports two runtime modes:

* **Distributed mode**: multiple worker processes (Pods) form a group and act as a single Connect cluster. One worker acts as group coordinator, distributing connectors and their tasks across the group; if a worker dies, its tasks are automatically rebalanced onto surviving workers. Connector lifecycle — create, delete, reconfigure — is driven through a REST API (port 8083 by default). This is the only mode used in Kubernetes.
* **Standalone mode**: a single process with a file-based offset store, intended for local development. It has no high availability or horizontal scaling, so it is never used on Kubernetes.

Distributed workers persist offsets, connector/task configuration, and task status in three internal topics (`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`). If these topics are lost, every connector on the cluster loses its state, so production deployments should always set their replication factor to at least 3.

## Deploying Kafka Connect on Strimzi

Strimzi manages the distributed Connect cluster itself through the `KafkaConnect` CRD, and manages individual connector instances running on top of it through the `KafkaConnector` CRD. Using `KafkaConnector` resources means connectors can be deployed and version-controlled through GitOps instead of calling the REST API by hand. To let Strimzi reconcile `KafkaConnector` resources, the `KafkaConnect` resource needs the `strimzi.io/use-connector-resources: "true"` annotation.

Connector plugins aren't bundled with the base Strimzi Kafka Connect image, so you need a custom image. Strimzi's recommended pattern avoids hand-writing a Dockerfile: you declare plugin artifacts (tgz/zip/jar, or Maven coordinates) under `KafkaConnect.spec.build`, and the Strimzi Operator builds the image and pushes it to a registry you specify — such as Amazon ECR.

### KafkaConnect build spec

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 3.9.0
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-cluster-offsets
    config.storage.topic: connect-cluster-configs
    status.storage.topic: connect-cluster-status
    offset.storage.replication.factor: 3
    config.storage.replication.factor: 3
    status.storage.replication.factor: 3
    key.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter: org.apache.kafka.connect.json.JsonConverter
  build:
    output:
      type: docker
      image: <account-id>.dkr.ecr.<region>.amazonaws.com/connect-cluster:latest
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.7.3.Final/debezium-connector-postgres-2.7.3.Final-plugin.tar.gz
      - name: aiven-s3-sink
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.0/s3-sink-connector-for-apache-kafka-3.4.0.zip
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

The Operator rebuilds the image and rolls out the Deployment automatically whenever `spec.build` changes — adding a plugin, bumping a version, and so on. The Secret referenced by `pushSecret` needs registry credentials (a `docker-registry` type Secret) for the ECR push to succeed; you can grant that access through IRSA if desired.

### KafkaConnector — Debezium PostgreSQL source example

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

### KafkaConnector — S3 sink example

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.S3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: orders-data-lake
    aws.s3.region: us-east-1
    format.output.type: jsonl
    file.compression.type: gzip
    flush.size: 10000
    rotate.schedule.interval.ms: 300000
```

`kubectl get kafkaconnector -n kafka` shows the status of each connector; a `Ready: True` condition means its tasks have been assigned to workers and are running.

## MirrorMaker 2 Architecture

MirrorMaker 2 (MM2) is a topic-level, cluster-to-cluster replication tool built on top of the Kafka Connect framework. It does more than copy messages: it preserves the source cluster's partitioning and translates consumer group offsets, which is what makes a clean consumer failover possible during disaster recovery. Internally, MM2 is composed of three connectors:

* **MirrorSourceConnector**: does the actual message replication, and also syncs topic configuration and ACLs.
* **MirrorCheckpointConnector**: periodically translates the source cluster's consumer group offsets into the equivalent offsets on the target cluster, recording them in a checkpoint topic. This offset translation is what lets a consumer failing over to the DR cluster know "how far it had already processed."
* **MirrorHeartbeatConnector**: sends periodic heartbeat messages proving the source cluster is alive and the replication pipeline is functioning, which is used to detect replication lag or outright disconnection.

MM2 does not reuse the source topic's name verbatim on the target cluster. The default `DefaultReplicationPolicy` names remote topics `<source-cluster-alias>.<topic>`. For example, replicating the `orders` topic from a cluster aliased `us-east-1` produces a remote topic named `us-east-1.orders` on the target. This naming convention lets consumers tell locally-produced messages apart from mirrored ones by topic name alone, and it doubles as the mechanism that prevents infinite replication loops in bidirectional setups.

## Disaster Recovery Patterns

### Active-Passive

This is the most common pattern: replication runs one-way, from a primary-region cluster to a DR-region cluster. Under normal operation, applications only talk to the primary cluster, and the DR cluster sits idle, accumulating replicated data. When a regional failure occurs, you use the offset translations recorded by MirrorCheckpointConnector to move consumer groups to the DR cluster and resume consumption from the most recent available checkpoint. This isn't a perfect exactly-once cutover — depending on exactly when the checkpoint was taken relative to the failure, a small number of messages may be reprocessed, and because MM2 replication is asynchronous, any message not yet replicated to the DR cluster at the moment of failure is lost (RPO is bounded by replication lag, not zero) — but the key benefit is a fast recovery with data loss minimized to that lag window.

### Active-Active

Both regions serve traffic, and each cluster replicates bidirectionally to the other. This introduces a real risk: a topic mirrored A → B (as `A.orders`) could get mirrored right back B → A, looping forever, unless it's explicitly prevented. Strimzi/MM2 guards against this through the naming policy set in `replication.policy.class` (the default `DefaultReplicationPolicy`, or `IdentityReplicationPolicy` if you want remote topics to keep their original names) — topics that already carry a remote-cluster prefix (like `A.orders`) are excluded from further mirroring. Narrowing `topicsPattern` to only the topics that actually need cross-region replication adds a second layer of protection against accidental replication loops.

### KafkaMirrorMaker2 CR example

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
      tls:
        trustedCertificates:
          - secretName: primary-cluster-ca-cert
            certificate: ca.crt
      authentication:
        type: tls
        certificateAndKey:
          secretName: mm2-user
          certificate: user.crt
          key: user.key
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

`connectCluster: dr-region` tells the MM2 worker Pods which cluster (here, the DR region) they should use to store Connect's own internal topics. Turning on `sync.group.offsets.enabled: "true"` makes MirrorCheckpointConnector periodically write its translated offsets into the DR cluster's `__consumer_offsets`, so a failed-over consumer can resume consuming without committing offsets manually first.

## Cross-Region Replication Considerations

* **Network cost and latency**: replication across regions (or even across AZs) carries data transfer cost and round-trip latency. It's common to run the MM2 workers in the target region, pulling data from the source cluster. Tuning batch size (`producer.override.batch.size`) and compression (`producer.override.compression.type: zstd`) reduces the volume actually transferred, which translates directly into lower cross-region data transfer cost.
* **`sync.topic.acls.enabled`**: controls whether the source cluster's topic ACLs are also synced to the target. Enabling it means you don't have to maintain access control policy twice, but if the two clusters have different security postures — say, the DR cluster requires stricter access than the primary — it may be safer to disable it and manage ACLs independently on each side.
* **Monitoring replication lag**: MM2 exposes its own metrics for replication health. `replication-latency-ms` reports the time from when a message was produced on the source to when it was fully replicated to the target, and the checkpoint connector's lag-related metrics show how current the offset translation is. Scraping these into Prometheus and alerting on an SLA (e.g., "replication lag under 5 minutes") lets you continuously verify that the DR cluster is actually in a state you could fail over to.

## Next Steps

With Kafka Connect and MirrorMaker 2 in place for data movement and disaster recovery, the next step is looking at how this workload integrates with — or compares to — the fully managed Amazon MSK service. That's covered in [Part 6: MSK Integration](./06-msk-integration.md).

[Return to Main Page](./)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md).
