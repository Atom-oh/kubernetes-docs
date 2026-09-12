# Part 5: Kafka Connect and MirrorMaker

> **Review baseline**: Strimzi 1.2.0, Kafka 4.3.1, Debezium PostgreSQL 3.6.2.Final, Aiven S3 sink 3.4.3\
> **Last reviewed**: September 12, 2026

## Connect workers and connectors

Kafka Connect runs plugins that move data between Kafka and external systems.
Configuration is sufficient only when an appropriate plugin already exists and
the database/storage permissions, format and network prerequisites are satisfied.

| Direction | Example | Important distinction |
| --- | --- | --- |
| Source: external system → Kafka | Debezium PostgreSQL CDC | Initial snapshot and logical WAL streaming differ from JDBC polling |
| Sink: Kafka → external system | Aiven S3 sink | Supported formats and delivery behavior depend on the particular plugin |

In distributed mode, a **Kafka broker** coordinates the worker group; an elected
worker leader computes assignments. A failed worker triggers reassignment, which
can take time and cause replay. A failed connector task is not automatically the
same event as worker failure; inspect failures and configure restart behavior.

Standalone Connect can run in a container or on Kubernetes, but it has no
distributed worker failover. Strimzi's `KafkaConnect` manages distributed mode.
Three workers do not make a single-task PostgreSQL connector run three tasks.

Distributed Connect uses compacted config, source-offset and status topics.
The config topic needs **one partition**. Give each Connect deployment its own
group ID and topic names. RF=3 is the baseline here because three brokers exist;
it is not a universal minimum that works with fewer brokers. Replication is not a
backup. Sink consumer offsets normally live in Kafka consumer groups, not in the
source-offset storage topic.

## Strimzi v1 is more than an apiVersion change

Strimzi 1.2.0 serves the `kafka.strimzi.io/v1` API. Convert older resources with the
release's migration procedure before upgrading; do not merely rename `v1beta2`.

| Resource | Current v1 field |
| --- | --- |
| KafkaConnect worker group | `spec.groupId` |
| KafkaConnect internal topic names | `spec.configStorageTopic`, `spec.offsetStorageTopic`, `spec.statusStorageTopic` |
| KafkaMirrorMaker2 destination and worker storage | `spec.target`, with its own `groupId` and three topic-name fields |
| KafkaMirrorMaker2 source connection | `spec.mirrors[].source` |

The old MM2 `connectCluster`, `clusters`, `sourceCluster`, `targetCluster` and
`heartbeatConnector` fields are not in this v1 schema. Apache MM2 includes a
heartbeat connector implementation, but that does not make it a configurable
`KafkaMirrorMaker2` v1 field.

## Prepare the Connect example

Use [Part 2](./02-strimzi-operator.md)'s three-broker `my-cluster` with TLS/SCRAM
and the Topic/User Operators. Replace the example ECR account/repository and DB/S3
names before deployment. Prepare these additional dependencies:

- `debezium-db-credentials`: a Kubernetes Secret with a `password` key.
- `rds-ca`: a Secret with `ca.crt`, containing the trusted PostgreSQL/RDS CA chain.
- An existing ECR repository, a current `kubernetes.io/dockerconfigjson` push
  Secret named `ecr-registry-credentials`, and image-pull permission for the nodes.
- A workload AWS identity for the **Connect pods**, scoped to the intended S3
  bucket/prefix. Configure Pod Identity or IRSA and validate the plugin's actual
  credential chain. Build-push identity and runtime S3 identity are separate.

ECR authorization tokens expire after 12 hours. Maintain/refresh the push Secret
before builds. Merely assigning an IRSA role does not establish that the selected
image builder can log in to ECR. Strimzi 1.2 enables its Buildah build feature by
default; check build-pod requirements on the actual nodes.

Save the following as `create-topics.py`, run it, and apply `connect-topics.json`.
The seven-day data retention is a lab choice; size retention for outage and
recovery requirements before relying on this pipeline.

```python
import json
from pathlib import Path

topics = [
    ("connect-cluster-configs", 1, "compact"),
    ("connect-cluster-offsets", 3, "compact"),
    ("connect-cluster-status", 3, "compact"),
    ("orders-db.public.orders", 3, "delete"),
    ("orders-db.public.order_items", 3, "delete"),
]
items = []
for name, partitions, cleanup in topics:
    config = {"cleanup.policy": cleanup, "min.insync.replicas": 2}
    if cleanup == "delete":
        config["retention.ms"] = 604800000
    items.append({
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaTopic",
        "metadata": {"name": name, "namespace": "kafka",
                     "labels": {"strimzi.io/cluster": "my-cluster"}},
        "spec": {"partitions": partitions, "replicas": 3, "config": config},
    })
Path("connect-topics.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
```

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: connect-cluster
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: connect-cluster-
          patternType: prefix
        operations: [Read, Write, Create, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: orders-db.
          patternType: prefix
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: connect-cluster
          patternType: literal
        operations: [Read]
      - resource:
          type: group
          name: connect-orders-s3-sink
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

Save the user resource as `connect-user.yaml`. Creation permission is scoped to
Connect's internal topic prefix; the five topics are pre-created by the Topic
Operator with explicit settings. Automatic source data-topic creation is disabled.
Additional tables/topics need an explicit matching update.

## Build and deploy Connect

Save as `connect.yaml`. Both downloaded plugin artifacts have SHA-512 checksums.
`spec.build` is one supported option; a prebuilt tested image or supported plugin
image volumes are other options. A successful build does not prove DB/S3 access.

The directory config provider reads a mounted Secret from an allowed path; it
does not need Kubernetes API Secret-read RBAC. This replaces the incomplete
`${secrets:...}` example that had neither its provider nor access permissions.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 4.3.1
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
  groupId: connect-cluster
  configStorageTopic: connect-cluster-configs
  offsetStorageTopic: connect-cluster-offsets
  statusStorageTopic: connect-cluster-status
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-cluster
    passwordSecret:
      secretName: connect-cluster
      password: password
  config:
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    offset.flush.interval.ms: 60000
    topic.creation.enable: false
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    config.providers: dir
    config.providers.dir.class: org.apache.kafka.common.config.provider.DirectoryConfigProvider
    config.providers.dir.param.allowed.paths: /mnt/debezium
  template:
    pod:
      volumes:
        - name: debezium-credentials
          secret:
            secretName: debezium-db-credentials
        - name: rds-ca
          secret:
            secretName: rds-ca
    connectContainer:
      volumeMounts:
        - name: debezium-credentials
          mountPath: /mnt/debezium
          readOnly: true
        - name: rds-ca
          mountPath: /mnt/rds-ca
          readOnly: true
  build:
    output:
      type: docker
      image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/connect-cluster:kafka4.3.1-deb3.6.2-s3-3.4.3
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo.maven.apache.org/maven2/io/debezium/debezium-connector-postgres/3.6.2.Final/debezium-connector-postgres-3.6.2.Final-plugin.tar.gz
            sha512sum: eabc5416446a32c3c763749262cd03115fbc2804bf48018348184f660222e9e5c8395306d9e795c9d52cbe246a5386142bdae376d418f6cf1bd5233e83e8ffe7
      - name: aiven-s3
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.3/s3-sink-connector-for-apache-kafka-3.4.3.zip
            sha512sum: d355c7d41713dab83384a51e28b6670f63775a0aa394eb0d9e99172d862f53d9e42c54534369cdcfefadfeb4f50e7ffac2029c65dd878f0def3db33058627758
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

```bash
python3 create-topics.py
kubectl apply -f connect-topics.json -f connect-user.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/connect-cluster
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/connect-cluster-configs kafkatopic/connect-cluster-offsets \
  kafkatopic/connect-cluster-status kafkatopic/orders-db.public.orders \
  kafkatopic/orders-db.public.order_items
kubectl apply -f connect.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=900s kafkaconnect/connect-cluster
```

With `strimzi.io/use-connector-resources: "true"`, manage connector mutations through
the CRs; direct REST changes can be reconciled away. Restrict the Connect REST API
and Kubernetes update permissions. All plugins in this worker deployment share
its mounted secrets and workload identity; isolate different trust domains in
different Connect deployments.

## PostgreSQL CDC source

Before applying `source.yaml`, enable PostgreSQL logical replication and arrange
the required replication slots/WAL senders, replication user and table privileges.
For RDS PostgreSQL, enabling the logical-replication parameter can require a reboot.
Use the actual engine-version procedure. Monitor retained WAL: a stalled slot can
fill storage. Do not drop a slot as a routine restart step.

An authorized table owner creates the publication in database `orders`:

```sql
CREATE PUBLICATION debezium_orders_pub
FOR TABLE public.orders, public.order_items;
```

Ensure suitable primary keys/replica identity for the update/delete events you
need. The connector takes an initial snapshot and then streams WAL. The
PostgreSQL connector uses one task; `tasksMax` is a maximum, not guaranteed parallelism.

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

The mounted password is not printed in the manifest. Test credential rotation and
restart/reconfiguration behavior rather than assuming existing DB connections
immediately adopt a changed Secret.

## Aiven S3 sink

Save as `sink.yaml`. The actual 3.4.3 connector class is
`io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector`.
The older example class `io.aiven.kafka.connect.s3.S3SinkConnector` is absent from
that artifact. `flush.size` and `rotate.schedule.interval.ms` are also not its
configuration keys; they must not be copied from a different vendor's S3 connector.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: REPLACE-WITH-YOUR-BUCKET
    aws.s3.region: ap-northeast-2
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    format.output.type: jsonl
    format.output.fields: key,value,offset,timestamp
    file.compression.type: gzip
    file.max.records: 10000
```

This stores **CDC event envelopes**, including operation and before/after data,
not an automatically materialized current-state table. The source and sink use
JSON converters with schema envelopes enabled. Keep converter settings consistent
with the actual Kafka records. `file.max.records` controls record grouping, and the
worker's `offset.flush.interval.ms` affects periodic flushing; it is not a promise
that every object arrives within a fixed deadline.

The AWS default credential chain is used when explicit credential options are
absent. Grant the plugin's required object/multipart operations only for the
intended destination and any required KMS key. Test normal events, deletes,
tombstones, retries and restart replay before treating the archive as a recovery
source. S3 objects do not automatically provide end-to-end exactly-once behavior.

```bash
kubectl apply -f source.yaml -f sink.yaml
kubectl -n kafka get kafkaconnector orders-db-source orders-s3-sink -o yaml
```

Inspect current generation, conditions, `status.connectorStatus.connector.state`
and every task's state/trace. Also check real source and destination progress.
`Ready=True` is an operator status observation, not proof that data is current.

## MirrorMaker 2 and disaster recovery

MM2 preserves record bytes and partition numbers while writing new target offsets.
It does not preserve the source offset numbers or automatically migrate schema
registry IDs, application transactions, external sink state or every security policy.

| Component | Responsibility and limit |
| --- | --- |
| MirrorSourceConnector | Copies records and emits offset-sync mappings; topic/config/ACL sync depends on settings |
| MirrorCheckpointConnector | Translates source group offsets and emits checkpoints; can update eligible inactive target groups |
| Apache MirrorHeartbeatConnector | Emits heartbeat records; its task can do so without reading source data, so heartbeat presence alone proves neither source health nor complete replication |

Active-passive uses one-way replication and an explicit cutover runbook.
If the source cannot be recovered, records not replicated before failure may be
lost. Replayed records can be duplicated; the replay window need not be small.
Measure replication and checkpoint freshness, fence the old writers, verify target
permissions/schema availability, change application endpoints/topic subscriptions
and test the resumed positions. MM2 does not perform these application steps.

In active-active, `DefaultReplicationPolicy` prefixes remote topics and detects
cycles **back to an alias already in their origin chain**. It does not exclude
every prefixed topic: multi-hop replication to a third cluster can be legitimate.
`IdentityReplicationPolicy` loses that naming information and does not provide
equivalent loop protection. Use deliberate directional filters and ownership;
it is not a generic conflict-resolution system for two writers.

## Current KafkaMirrorMaker2 v1 example

This one-way template requires working cross-cluster DNS/network access, three
target brokers, the listed source/target Secrets in namespace `kafka`, and separately
prepared Kafka ACLs. The endpoint strings are placeholders. Run workers where both
clusters are reachable; `spec.target` selects Kafka storage, not a Kubernetes region.

| Identity | Required scope to plan |
| --- | --- |
| Source | Read/describe selected topics, describe selected group offsets |
| Target | Connect internal topics and worker group; write/create intended remote topics and MM2 internal topics; read offset mappings/checkpoints; update selected inactive group offsets |

Pre-create internal topics with appropriate compaction/partitioning or grant the
specific creation rights required by the selected configuration. Source and target
credentials can differ. This example stores offset-syncs on the target and disables
ACL/config copying so that destination policies are managed explicitly.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 4.3.1
  replicas: 3
  target:
    alias: dr-region
    bootstrapServers: dr-kafka-bootstrap.REPLACE.example.com:9093
    groupId: primary-to-dr
    configStorageTopic: primary-to-dr-configs
    offsetStorageTopic: primary-to-dr-offsets
    statusStorageTopic: primary-to-dr-status
    tls:
      trustedCertificates:
        - secretName: dr-cluster-ca-cert
          certificate: ca.crt
    authentication:
      type: scram-sha-512
      username: mm2-target
      passwordSecret:
        secretName: mm2-target
        password: password
    config:
      config.storage.replication.factor: 3
      offset.storage.replication.factor: 3
      status.storage.replication.factor: 3
  mirrors:
    - source:
        alias: us-east-1
        bootstrapServers: primary-kafka-bootstrap.REPLACE.example.com:9093
        tls:
          trustedCertificates:
            - secretName: primary-cluster-ca-cert
              certificate: ca.crt
        authentication:
          type: scram-sha-512
          username: mm2-source
          passwordSecret:
            secretName: mm2-source
            password: password
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.topic.acls.enabled: false
          sync.topic.configs.enabled: false
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.group.offsets.enabled: true
          sync.group.offsets.interval.seconds: 60
          emit.checkpoints.interval.seconds: 60
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      topicsPattern: 'orders[.].*|payments[.].*'
      groupsPattern: 'orders-consumer-.*'
```

The pattern matches `orders.` and `payments.` prefixes; it does not include bare
`orders`, `payments`, or `orders-db.public.orders`. Adapt it to the actual topic
inventory. Source and checkpoint connectors must agree on replication policy,
separator and offset-syncs location.

`sync.group.offsets.enabled=true` only updates eligible **inactive/absent** target
groups with translatable offsets; it does not overwrite an actively consuming
group. Consumer membership, permissions, mapping/checkpoint availability and
already-committed target positions affect the result. Never infer a successful
failover solely from this setting or an operator Ready condition.

## Network and monitoring

For workers in the target region, source-to-worker fetch traffic crosses regions.
Compressing the worker's **target producer** does not retroactively compress that
fetch traffic; source producer/topic compression and placement matter. Measure
both network legs, CPU and latency instead of promising a saving from one knob.

`replication-latency-ms` is measured when the target acknowledges a record, relative
to the record timestamp. Timestamp mode, historical replay and clock skew affect
it. `record-age-ms` is observed on the read path. Monitor per-partition progress,
errors, data freshness and checkpoint freshness as well; a stopped or empty
stream can produce stale/absent samples. Prometheus metric names depend on the
exporter mappings, so a Kafka metric name is not automatically a PromQL name.

## References and validation

The examples were checked against the released v1 CRDs and native connector
configuration definitions. Local MM2 behavior checks do not establish actual
cross-region connectivity, database privileges, ECR builds, S3 delivery or a
successful disaster-recovery cutover.

- [Strimzi 1.2.0 CRDs: authoritative resource fields](https://github.com/strimzi/strimzi-kafka-operator/tree/1.2.0/install/cluster-operator)
- [Strimzi 1.2.0 deployment guide](https://strimzi.io/docs/operators/1.2.0/deploying.html)
- [Debezium 3.6 PostgreSQL connector](https://debezium.io/documentation/reference/3.6/connectors/postgresql.html)
- [Aiven S3 connector 3.4.3](https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/blob/v3.4.3/s3-sink-connector/README.md)
- [ECR authorization token lifetime](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetAuthorizationToken.html)
- [Kafka 4.3.1 MirrorSourceConnector](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceConnector.java)
- [Kafka 4.3.1 MirrorCheckpointTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorCheckpointTask.java)
- [Kafka 4.3.1 MirrorHeartbeatTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorHeartbeatTask.java)
- [Kafka 4.3.1 MirrorSourceTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceTask.java)

## Next steps

[Part 6: MSK integration](./06-msk-integration.md) compares managed options.

[Return to main page](./README.md)

## Quiz

[Topic quiz](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
