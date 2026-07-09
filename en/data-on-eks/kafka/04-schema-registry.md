# Part 4: Schema Registry

> **Supported Versions**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (compatible API)\
> **Last Updated**: July 9, 2026

## Why You Need a Schema Registry

Kafka itself treats every message as an opaque byte array. It doesn't care what format a producer writes into that array. The problem is that producers and consumers are usually separate applications, owned by different teams, deployed on different schedules. The moment a producer adds a field or changes a type, any consumer that doesn't know about the change either fails to deserialize the message or reads a garbled value.

### The Problem with Schema-less JSON

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

Raw JSON payloads like this are human-readable, but they come with real costs:

* **No enforced contract**: nothing stops a producer from silently turning `amount` into a string.
* **Validation only at runtime**: missing fields or type mismatches only surface when a consumer tries to parse the payload.
* **Payload size**: field names are repeated on every message, which is larger than a binary format and turns into real network/storage cost at high throughput.
* **No version history**: there's no way to answer "what did version 3 of this topic's schema look like?"

### What a Schema Registry Solves

A schema registry is a separate service that centrally stores and versions schemas for structured formats like Avro, Protobuf, and JSON Schema, and enforces compatibility rules between versions. The flow looks roughly like this:

1. Before sending a message, the producer registers (or looks up) its schema with the registry.
2. The registry returns a schema ID, and the producer serializes the payload with just that ID prepended (typically a 5-byte magic-byte + ID header) instead of the full schema.
3. The consumer reads the schema ID embedded in the message, fetches the matching schema from the registry, and deserializes accordingly.
4. When a new schema version is registered, the registry checks it against compatibility rules and rejects the registration outright if it violates them.

This lets producers and consumers evolve independently **without knowing each other's deployment schedules**. It also means the wire payload only carries a schema ID, so Avro/Protobuf binary encoding is dramatically smaller than JSON.

## Comparing the Major Implementations

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **Vendor** | Aiven | Red Hat | Confluent |
| **License** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (not fully open source since 2018) |
| **Supported formats** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, Kafka Connect schemas, etc. | Avro, Protobuf, JSON Schema |
| **API compatibility** | Compatible with the Confluent REST API | Confluent-compatible mode (`ccompat`) | The original API (de facto standard) |
| **Storage backend** | Kafka topic | Kafka topic or SQL (e.g. PostgreSQL) | Kafka topic |
| **Bundled REST Proxy** | Yes (Karapace REST Proxy) | No (registry only) | Separate commercial REST Proxy |
| **Commercial support terms** | Via Aiven's managed service, or community | Via Red Hat subscription | Requires Confluent Platform licensing at scale |
| **Fit for EKS/Strimzi** | Strong — pure open source, lightweight | Strong — multi-format, multi-backend | Needs a license review |

**For a self-managed EKS + Strimzi stack, we recommend Karapace or Apicurio Registry.** Both ship under the Apache-2.0 license with no restrictions on redistribution or modification. Confluent Schema Registry's Confluent Community License, by contrast, explicitly prohibits offering it as a competing managed service — it hasn't been fully open source since 2018. Client-side libraries such as `kafka-avro-serializer` are still published by Confluent, but because the REST API is compatible, pointing `schema.registry.url` at Karapace or Apicurio instead usually works with no code changes.

## Serialization Formats

### Avro

Avro defines its schema as JSON and serializes data into a compact binary format. It's the most widely used format in the Kafka ecosystem, and its standout feature is **schema resolution**: the **writer schema** (used when the data was written) and the **reader schema** (used when reading it back) don't have to match exactly — Avro resolves the differences according to well-defined rules.

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    { "name": "orderId", "type": "string" },
    { "name": "customerId", "type": "string" },
    { "name": "amount", "type": "double" },
    { "name": "currency", "type": "string", "default": "USD" },
    { "name": "createdAt", "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

### Protobuf

Protobuf schemas are defined in `.proto` files and compiled with `protoc` to generate code in each target language. Like Avro, it produces compact binary encodings, but it assigns explicit field numbers and has a stricter type system, which tends to produce higher-quality generated code across languages. Protobuf adoption in the Kafka ecosystem has been growing steadily.

```protobuf
syntax = "proto3";

package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at = 5;
}
```

### JSON Schema

JSON Schema defines validation rules for JSON payloads themselves. It's human-readable and easy to debug, but because field names are repeated in every message, payloads end up much larger than Avro or Protobuf. It fits workloads that need schema validation but are less sensitive to throughput or storage cost.

### Comparing the Three Formats

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema definition | JSON | `.proto` IDL | JSON Schema |
| Payload size | Small | Small | Large |
| Human-readable | Schema only | Schema only | Payload too |
| Cross-language codegen | Good | Excellent | Good |
| Kafka ecosystem adoption | Very high | High (growing) | Moderate |
| Schema evolution rules | Writer/reader resolution | Field-number based | JSON Schema validation rules |

## Compatibility Strategies

When a new schema version is registered, the registry checks it against the previous version according to the configured compatibility mode. Getting these four modes right matters — this is the single most commonly confused concept in schema management.

| Mode | Meaning | Deployment order |
| --- | --- | --- |
| **BACKWARD** | A reader using the **new** schema must be able to read data written with the **old** schema | Upgrade **consumers** first |
| **FORWARD** | A reader using the **old** schema must be able to read data written with the **new** schema | Upgrade **producers** first |
| **FULL** | Both BACKWARD and FORWARD hold | Either order is safe |
| **NONE** | No compatibility checking | Manual coordination required |

The part people most often get backwards:

* **BACKWARD** means "the new schema (as a reader) can read old data." In practice that means you can safely **deploy the new-schema consumer first** — even while producers are still writing with the old schema, the upgraded consumer reads it fine.
* **FORWARD** means "the old schema (as a reader) can read new data." That means you can safely **upgrade producers to the new schema first** — consumers still running the old schema keep working.

### Example of a Backward-Compatible Change

Adding an optional field with a default value to the `Order` schema is BACKWARD compatible:

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

A consumer using the new schema reading old data (which lacks this field) simply gets the `default` value (`null`) — no failure.

### Examples of Breaking Changes

These are classic BACKWARD-compatibility violations:

* **Adding a required field without a default**: adding a new `discount_code` field with no default means a new-schema reader expects the field on old data that never had it, and fails. (Conversely, *removing* a field is BACKWARD compatible but breaks FORWARD instead — an old-schema reader would still expect the now-removed field to be required on the new data.)
* **Changing a field's type**: switching `amount` from `double` to `string` means existing binary-encoded data can no longer be decoded as the new type.
* **Renaming a field** (without an alias): the reader looks for the field under its new name, but old data only has it under the old name.

## Deploying on Strimzi/EKS

### Deploying Apicurio Registry (Kafka-Topic Storage)

Assuming a Strimzi-managed Kafka cluster is already running, you can deploy Apicurio Registry as a Deployment in the same namespace, backed by a Kafka-topic storage engine.

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
      containers:
        - name: apicurio-registry
          image: quay.io/apicurio/apicurio-registry:3.0.6
          ports:
            - containerPort: 8080
          env:
            - name: APICURIO_STORAGE_KIND
              value: "kafkasql"
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: "my-kafka-cluster-kafka-bootstrap.kafka.svc:9092"
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
    - port: 8080
      targetPort: 8080
```

Apicurio also supports a SQL backend (`APICURIO_STORAGE_KIND=sql`) instead of `kafkasql`, so if you already run a PostgreSQL/RDS instance, you can point the registry there instead. Karapace, by contrast, always stores schemas in a Kafka topic (`_schemas`) and needs no separate backend configuration.

### Registering a Schema

Once the registry is running, schemas are registered through its REST API (using the Confluent-compatible endpoint):

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### Client Configuration

Kafka producer/consumer applications point their serializer at the registry URL:

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

The same `KafkaAvroSerializer` class works against Karapace too — just point `schema.registry.url` at Karapace's REST endpoint (port 8081 by default). Application code doesn't need to change when you swap registry implementations, which is exactly the value the Confluent-compatible API provides.

## What's Next

This part covered how a schema registry keeps the data contract between producers and consumers safe as both evolve independently. Part 5 moves on to Kafka Connect and MirrorMaker — integrating with external systems and replicating data across clusters.

[Return to Main Page](./)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md).
