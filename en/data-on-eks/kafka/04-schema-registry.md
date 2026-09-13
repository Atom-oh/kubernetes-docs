# Part 4: Schema Registry

> **Review baseline**: Karapace 6.2.3, Apicurio Registry 3.3.3, Strimzi 1.2.0 / Kafka 4.3.1\
> **Last reviewed**: September 12, 2026

## Why use a schema registry?

Kafka stores record keys and values as bytes. A producer and consumer can therefore
disagree about the structure or meaning of a value. Not every field addition breaks
a consumer: the result depends on the encoding, reader and compatibility rules.

A registry versions schemas and checks configured compatibility rules when schemas
are registered. Applications must use the corresponding serializers and validation
paths. A registry does not automatically inspect every Kafka record or enforce
business rules such as the meaning of a currency or a timestamp.

JSON can also have a contract: JSON Schema, CI checks and versioned specifications
are possible with or without a registry. A central registry helps distribute and
govern that contract; binary encoding is a separate choice. Compare measured,
compressed records before claiming a payload-size or storage-cost saving.

### What travels in a record?

With the common Confluent **schema-ID payload framing**, a value begins with one
magic byte and a four-byte schema ID: five bytes in total, followed by the encoded
value. The Protobuf variant also includes message indexes. JSON Schema serializers
still encode the value as JSON. Other serializer modes, header-based identifiers
and native Apicurio encodings need their own configuration.

The serializer registers or looks up a schema, and the deserializer retrieves the
writer schema by its identifier. Clients normally cache schemas, so this is not
necessarily an HTTP request for every record. A cold cache or a new schema can
still require the registry. Retain the ID-to-schema mapping for as long as the
corresponding Kafka data, archives and disaster-recovery copies must be readable.

## Comparing implementations

| Implementation | Relevant schema formats | API and storage |
| --- | --- | --- |
| Karapace 6.2.3 | Avro, JSON Schema, **Protobuf** | Confluent-compatible REST API; Kafka-backed schema storage; also provides a REST proxy |
| Apicurio Registry 3.3.3 | Avro, Protobuf, JSON Schema; additional artifact types | Native API plus `/apis/ccompat/v7` and `/apis/ccompat/v8`; KafkaSQL and SQL storage options |
| Confluent Schema Registry | Avro, Protobuf, JSON Schema | Confluent API; Kafka-backed storage in the self-managed deployment |

Karapace and Apicurio publish Apache-2.0 licenses. That license has conditions,
including preservation of required notices; it does not mean “no restrictions.”
Confluent's repository distinguishes Community-licensed server modules from
Apache-2.0 client/Avro modules. Check the actual component license and any support
contract instead of inferring commercial terms from cluster size.

API compatibility is useful, but **changing only the URL is not a migration plan**.
Test schema IDs, references, subject naming, authentication, client versions and
wire encoding against retained records. For example, Apicurio's compatibility API
does not implement every Confluent exporter/encryption feature; accepting an
optional request field does not necessarily mean enforcing its rules.
An artifact type that Apicurio can store is not automatically supported by every
Kafka serializer. Karapace also needs broker, authentication and schema-topic
configuration; Kafka-backed does not mean configuration-free.

## Serialization formats

### Avro

Save the following canonical example as `order.avsc`. Avro resolves a writer schema
against a reader schema using names, defaults, aliases and defined type promotions.
The timestamp's `logicalType` belongs inside its **type object**, not beside the
field's `name`. A misplaced field attribute can parse while failing to declare a
logical timestamp.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    {
      "name": "orderId",
      "type": "string"
    },
    {
      "name": "customerId",
      "type": "string"
    },
    {
      "name": "amount",
      "type": "double"
    },
    {
      "name": "currency",
      "type": "string",
      "default": "USD"
    },
    {
      "name": "createdAt",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      }
    }
  ]
}
```

Here `amount` is only an illustrative double. A real contract must define units,
precision and rounding; use a suitable integer or decimal representation where
exact decimal amounts are required.

### Protobuf and JSON Schema

Protobuf uses numbered fields and language-specific generated/runtime APIs. Define
the time unit explicitly; `int64` alone does not declare a logical timestamp.
Do not reuse deleted field numbers; reserve removed numbers and names as appropriate.

```protobuf
syntax = "proto3";
package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at_millis = 5;
}
```

JSON Schema validates JSON. Support for draft versions and compatibility analysis
varies by registry; validation support does not imply complete evolution analysis
for every keyword. These are distinct contracts, not interchangeable encodings.

| Format | Wire representation | Evolution considerations |
| --- | --- | --- |
| Avro | Binary with writer-schema interpretation | Reader/writer resolution, defaults, names and promotions |
| Protobuf | Binary with numbered fields | Preserve field numbers and wire types; check application semantics |
| JSON Schema | JSON | Accepted instance sets, required fields, additional properties and draft support |

## Compatibility and deployment order

In the Confluent-compatible API, configure compatibility at the **subject** level
(or inherit a global default). Under the default `TopicNameStrategy`, values in
topic `orders` use subject `orders-value`; other strategies can share a subject
across topics or separate record types within a topic.

| Mode | Required relationship | Typical schema rollout |
| --- | --- | --- |
| BACKWARD | New reader can read the previous writer's data | Consumers first |
| FORWARD | Previous reader can read the new writer's data | Producers first |
| FULL | Both directions | Either order for the checked schema relationship |
| NONE | No compatibility check | Coordinate and test explicitly |

The non-transitive modes compare with the latest prior version. Their
`_TRANSITIVE` variants compare with all prior versions. For replay of older retained
records, checking only the latest version can be insufficient. `FULL` does not
guarantee business semantics, application behavior or compatibility with every
historical version; `FULL_TRANSITIVE` extends the schema comparison, not that guarantee.

For Avro, adding this field allows a new reader to supply `null` for old records:

```json
{"name":"discountCode","type":["null","string"],"default":null}
```

The default is a **reader-resolution** rule, not permission for a writer to omit
an arbitrary required field.

| Avro change | Important condition |
| --- | --- |
| Add a field without a reader default | New reader cannot read old records lacking that field |
| Remove a field | Backward compatible; forward compatibility depends on whether the old reader has a default |
| Change `double` to `string` | Incompatible; this is not an Avro numeric promotion |
| Change `int` to `long` | New reader can accept old integer values; the reverse direction is different |
| Rename a field | A reader alias or an applicable default can change the result; test both directions |

Run reader/writer tests with representative historical data as well as the
registry's compatibility endpoint. They catch different classes of failure.

## Deploying Apicurio with the Strimzi baseline

This is a **private lab deployment**, not an authenticated public registry.
It assumes [Part 2](./02-strimzi-operator.md)'s `my-cluster` in namespace `kafka`,
three brokers, Topic/User Operators, and the TLS/SCRAM listener on port 9093.
The HTTP API below has no application authentication. The NetworkPolicy allows
port 8080 only from labeled pods in the same namespace when the CNI enforces
NetworkPolicy. Restrict who can create or label those pods. For shared production
use, configure API TLS, authentication and authorization separately from Kafka
SASL; an internal Service alone does not provide those controls.

### Storage topics and Kafka identity

Save as `registry-storage.yaml`. The application identity reads/writes only its
three named topics and its consumer-group prefix. Topics are pre-created by the
Topic Operator, so the application does not need topic-creation permission.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-journal
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-snapshots
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: registry-events
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: apicurio-registry
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
          name: kafkasql-journal
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: kafkasql-snapshots
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: registry-events
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: group
          name: apicurio-registry-
          patternType: prefix
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

KafkaSQL 3.3.3 initializes the journal, snapshots and events topics. Its journal and
snapshot topic checks require `cleanup.policy=delete`, `retention.ms=-1` and
`retention.bytes=-1` by default. Do not apply a generic `_schemas` compaction recipe
or ordinary seven-day event retention to them. This preserves records indefinitely,
so monitor disk growth and plan tested backups and cleanup.

KafkaSQL rebuilds local SQL state from the journal and any available snapshot.
The snapshots topic contains **snapshot file paths**, not the complete snapshot
files. The following lab disables scheduled snapshots and keeps the full journal;
losing a pod means replay and potentially a long startup. Durable/shared snapshot
storage, backup, restore and journal trimming need a separate recovery design.
The group prefix is configurable, but a fixed `group.id` is not the way to retain
KafkaSQL state: this release generates unique groups to ensure replay on startup.

### Deployment and Service

Save as `registry.yaml`. The CA and JAAS values come from Strimzi Secrets.
Hostname verification is set explicitly. Resource sizes and the ten-minute
startup allowance are initial lab settings; measure memory and replay time.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apicurio-registry
  template:
    metadata:
      labels:
        app: apicurio-registry
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: registry
          image: quay.io/apicurio/apicurio-registry:3.3.3
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9000
          env:
            - name: APICURIO_STORAGE_KIND
              value: kafkasql
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: my-cluster-kafka-bootstrap.kafka.svc:9093
            - name: APICURIO_KAFKASQL_TOPIC_AUTO_CREATE
              value: "false"
            - name: APICURIO_KAFKASQL_CONSUMER_GROUP_PREFIX
              value: apicurio-registry-
            - name: APICURIO_KAFKASQL_SNAPSHOT_SCHEDULED_ENABLED
              value: "false"
            - name: APICURIO_KAFKA_COMMON_SECURITY_PROTOCOL
              value: SASL_SSL
            - name: APICURIO_KAFKA_COMMON_SASL_MECHANISM
              value: SCRAM-SHA-512
            - name: APICURIO_KAFKA_COMMON_SASL_JAAS_CONFIG
              valueFrom:
                secretKeyRef:
                  name: apicurio-registry
                  key: sasl.jaas.config
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_TYPE
              value: PKCS12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_LOCATION
              value: /etc/kafka-ca/ca.p12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: my-cluster-cluster-ca-cert
                  key: ca.password
            - name: APICURIO_KAFKA_COMMON_SSL_ENDPOINT_IDENTIFICATION_ALGORITHM
              value: HTTPS
          volumeMounts:
            - name: kafka-ca
              mountPath: /etc/kafka-ca
              readOnly: true
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          startupProbe:
            httpGet:
              path: /health/ready
              port: management
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /health/ready
              port: management
          livenessProbe:
            httpGet:
              path: /health/live
              port: management
      volumes:
        - name: kafka-ca
          secret:
            secretName: my-cluster-cluster-ca-cert
            items:
              - key: ca.p12
                path: ca.p12
---
apiVersion: v1
kind: Service
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  selector:
    app: apicurio-registry
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apicurio-registry-ingress
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      app: apicurio-registry
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              docs.example.com/registry-client: "true"
      ports:
        - protocol: TCP
          port: 8080
```

```bash
kubectl apply -f registry-storage.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/kafkasql-journal kafkatopic/kafkasql-snapshots kafkatopic/registry-events \
  kafkauser/apicurio-registry
kubectl apply -f registry.yaml
kubectl -n kafka rollout status deployment/apicurio-registry --timeout=600s
kubectl -n kafka port-forward --address=127.0.0.1 service/apicurio-registry 8080:8080
```

Port forwarding requires Kubernetes access and stays in the foreground. Restart
the workload after changing Secret-backed environment variables. For SQL storage,
`APICURIO_STORAGE_KIND=sql` alone is not a PostgreSQL configuration: select the
SQL kind and supply a dedicated database, TLS, credentials and recovery procedures.
The default in-memory H2 database is not durable production storage.

## Register the same schema used by the application

From another terminal, register `order.avsc` under `orders-value`. This avoids the
old mismatch between a namespaced multi-field example and a different one-field
schema hidden inside a curl string. The first request explicitly configures the
subject's compatibility; HTTP failures cause a nonzero curl exit status.

```bash
# Run from a directory containing the order.avsc above.
# Keep kubectl port-forward running in a separate terminal.
REGISTRY_URL="http://127.0.0.1:8080/apis/ccompat/v7"
python3 - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path("order.avsc").read_text())
Path("register-order.json").write_text(json.dumps({
    "schemaType": "AVRO",
    "schema": json.dumps(schema)
}) + "\n")
PY
curl --fail-with-body --silent --show-error \
  -X PUT "$REGISTRY_URL/config/orders-value" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary '{"compatibility":"BACKWARD_TRANSITIVE"}'
curl --fail-with-body --silent --show-error \
  -X POST "$REGISTRY_URL/subjects/orders-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary @register-order.json
curl --fail-with-body --silent --show-error \
  "$REGISTRY_URL/subjects/orders-value/versions/latest"
```

## Producer and consumer settings

These are **additional** properties for applications already configured with the
Part 2 broker address, TLS trust and their own Kafka identities. Registry HTTP
credentials and Kafka SASL credentials are separate. Include a compatible,
version-pinned Confluent Avro serializer dependency in the application; it is not
provided merely by installing Kafka or Strimzi.

Producer:

```properties
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
auto.register.schemas=false
```

Consumer:

```properties
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
specific.avro.reader=false
```

The producer example requires the matching schema to be registered first.
With `specific.avro.reader=false`, consumers use generic Avro records; generated
SpecificRecord classes require the matching code and reader setting. The default
subject strategy assumes the application's Kafka topic is `orders`.

Before changing registries, test a cold-cache consumer against retained records,
new-version registration, compatibility rejection, schema references and restart/
recovery. Preserve the original schema-ID mapping or perform an explicit supported
data/identifier migration. A successful HTTP health check is not a serialization test.

## References and validation

This chapter's examples were checked against the pinned release configuration and
Strimzi/Kubernetes schemas, with local Avro reader/writer tests. Those checks do not
replace deploying the image, connecting to the actual TLS broker, or exercising
the application's exact serializer version.

- [Apache Avro specification](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers: updating a message type](https://protobuf.dev/programming-guides/proto3/#updating)
- [Confluent compatibility rules](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Confluent serializers and wire format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html)
- [Karapace 6.2.3](https://github.com/Aiven-Open/karapace/tree/6.2.3)
- [Apicurio Registry 3.3.3](https://github.com/Apicurio/apicurio-registry/tree/3.3.3)
- [Apicurio compatibility API support matrix](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/ccompat/rest/README.md)
- [Apicurio KafkaSQL configuration](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/kafkasql/KafkaSqlConfiguration.java)
- [Apicurio topic configuration verification](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/util/KafkaAdminUtil.java)
- [Confluent component licenses](https://github.com/confluentinc/schema-registry/blob/master/LICENSE)

## What's next

[Part 5](./05-kafka-connect-mirrormaker.md) covers external integrations and
cross-cluster replication. Schema storage and ID migration must be considered
alongside record replication.

[Return to main page](./README.md)

## Quiz

[Topic quiz](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
