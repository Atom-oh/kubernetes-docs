# Schema Registry Quiz

This quiz tests your understanding of why schema registries exist, Avro/Protobuf serialization trade-offs, the four compatibility modes, and the licensing differences between the major implementations (Karapace, Apicurio, Confluent).

## Multiple Choice Questions

1. What is the most fundamental problem caused by the fact that Kafka brokers never validate message content?
   - A) Broker throughput drops
   - B) Producers and consumers can evolve their schemas without knowing about each other's changes, leading to deserialization failures
   - C) You can't create more than one topic
   - D) Partition rebalancing becomes impossible

<details>

<summary>Show Answer</summary>

**Answer: B) Producers and consumers can evolve their schemas without knowing about each other's changes, leading to deserialization failures**

**Explanation:**
Kafka treats every message as an opaque byte array and enforces no data format. Because producers and consumers are typically separate applications deployed on independent schedules, a schema change on one side can silently break the other — causing deserialization failures or corrupted values. A schema registry solves this by centrally managing the contract and enforcing compatibility.
</details>

2. Compared to schema-less JSON, what is the biggest advantage of combining a binary format like Avro/Protobuf with a schema registry?
   - A) It becomes easier for humans to read
   - B) Payloads get smaller and schema changes are centrally validated
   - C) It automatically adjusts the number of partitions
   - D) Consumer groups become unnecessary

<details>

<summary>Show Answer</summary>

**Answer: B) Payloads get smaller and schema changes are centrally validated**

**Explanation:**
Avro/Protobuf use compact binary encoding that doesn't repeat field names, making payloads smaller than JSON. In addition, messages carry only a schema ID rather than the full schema — the actual schema is managed by the registry, which validates compatibility whenever a new version is registered. JSON, by contrast, remains easier for a human to read directly.
</details>

3. What does an actual message on the wire contain when using a schema registry?
   - A) The full schema definition
   - B) A short header containing the schema ID, followed by binary-encoded data
   - C) The schema registry's URL
   - D) The consumer group ID

<details>

<summary>Show Answer</summary>

**Answer: B) A short header containing the schema ID, followed by binary-encoded data**

**Explanation:**
The producer registers (or looks up) the schema with the registry and prepends the returned schema ID, typically alongside a magic byte, to the front of the serialized message. The full schema definition itself is never included in the message — only the registry stores it — which is what keeps the payload small. The consumer reads this ID and fetches the matching schema from the registry to deserialize the rest.
</details>

4. Which of the following schema registry implementations is distributed under the Apache License 2.0?
   - A) Confluent Schema Registry
   - B) Both Karapace and Apicurio Registry
   - C) Karapace only
   - D) Apicurio Registry only

<details>

<summary>Show Answer</summary>

**Answer: B) Both Karapace and Apicurio Registry**

**Explanation:**
Karapace (Aiven) and Apicurio Registry (Red Hat) are both pure open-source projects distributed under the Apache License 2.0. Confluent Schema Registry has been governed by the Confluent Community License since 2018, which places restrictions on certain commercial uses and is not a fully open-source license.
</details>

5. Which combination is recommended for a self-managed EKS + Strimzi stack to avoid licensing friction?
   - A) Confluent Schema Registry alone
   - B) Karapace or Apicurio Registry
   - C) No schema registry — just use JSON
   - D) Only AWS Glue Schema Registry is viable

<details>

<summary>Show Answer</summary>

**Answer: B) Karapace or Apicurio Registry**

**Explanation:**
Karapace and Apicurio Registry are both Apache-2.0 licensed and can be self-hosted without restriction. Confluent Schema Registry's Confluent Community License introduces terms that warrant a license review before self-managed use. Both open-source alternatives are API-compatible with Confluent's, so clients can switch without code changes.
</details>

6. What core mechanism enables schema evolution in Avro serialization?
   - A) Field-number-based mapping
   - B) Resolution rules between the writer schema and the reader schema
   - C) JSON Schema `$ref` references
   - D) Compile-time code generation

<details>

<summary>Show Answer</summary>

**Answer: B) Resolution rules between the writer schema and the reader schema**

**Explanation:**
Even when the writer schema (used when the data was written) and the reader schema (used when reading it back) differ, Avro can still correctly decode the data by applying defined resolution rules — matching fields by name, applying defaults, and so on. Field-number-based mapping is a characteristic of Protobuf, not Avro.
</details>

7. Where does Protobuf hold a relative advantage over Avro?
   - A) Its payloads are always smaller
   - B) Explicit field numbers and a stricter type system produce higher-quality cross-language generated code
   - C) It doesn't require a schema registry
   - D) It's more human-readable than JSON

<details>

<summary>Show Answer</summary>

**Answer: B) Explicit field numbers and a stricter type system produce higher-quality cross-language generated code**

**Explanation:**
Protobuf assigns an explicit number to every field in its `.proto` IDL and enforces a strict type system, which tends to produce cleaner generated client code across languages via `protoc`. Payload size is generally comparable to Avro, and Protobuf is commonly paired with a schema registry just like Avro is.
</details>

8. On a topic configured with BACKWARD compatibility, which side is safe to upgrade first?
   - A) The producer
   - B) The consumer
   - C) The broker
   - D) The ZooKeeper or KRaft controller

<details>

<summary>Show Answer</summary>

**Answer: B) The consumer**

**Explanation:**
BACKWARD compatibility means "a reader using the new schema must be able to read data written with the old schema." That means the consumer can be upgraded to the new schema first, even while producers are still writing with the old schema — the upgraded consumer will read old data correctly. FORWARD, by contrast, is the mode that's safe to deploy producer-first.
</details>

9. Which statement correctly describes FORWARD compatibility?
   - A) A reader using the old schema must be able to read data written with the new schema
   - B) A reader using the new schema must be able to read data written with the old schema
   - C) No compatibility checking is performed at all
   - D) Consumers must always be upgraded first

<details>

<summary>Show Answer</summary>

**Answer: A) A reader using the old schema must be able to read data written with the new schema**

**Explanation:**
FORWARD means "the old schema (as a reader) can read data written with the new schema." Under this mode, producers can be upgraded to the new schema first, and consumers still running the old schema will keep reading correctly. B describes BACKWARD, C describes NONE, and D is the safe order under BACKWARD, not FORWARD.
</details>

10. Which of the following schema changes violates BACKWARD compatibility?
    - A) Adding an optional field with a default value
    - B) Adding a required field without a default value
    - C) Adding a doc comment to a field
    - D) Reordering fields without changing their names or types

<details>

<summary>Show Answer</summary>

**Answer: B) Adding a required field without a default value**

**Explanation:**
Adding a required field with no default means that a reader using the new schema, when reading old data (which never had this field), expects a value but finds none — causing a read failure. Removing a field, by contrast, IS backward compatible, since the new-schema reader simply never looks for it (though this breaks FORWARD compatibility instead). Adding an optional field with a default is the classic example of a BACKWARD-compatible change, while adding doc comments or reordering fields (Avro matches by name) has no effect on the actual data structure.
</details>

## Short Answer Questions

11. What piece of information does a consumer read from a message in order to find the correct schema for deserializing it?

<details>

<summary>Show Answer</summary>

**Answer: The schema ID**

**Explanation:**
When serializing, the producer includes only the schema ID issued by the registry (typically encoded near the front of the message alongside a magic byte) rather than the full schema. The consumer reads this ID, queries the registry for the matching schema, and uses it to deserialize the rest of the binary payload.
</details>

12. What is the name of the compatibility mode that requires both BACKWARD and FORWARD compatibility to hold at the same time?

<details>

<summary>Show Answer</summary>

**Answer: FULL**

**Explanation:**
FULL compatibility requires both BACKWARD (a new-schema reader can read old data) and FORWARD (an old-schema reader can read new data) to hold simultaneously. This makes producer/consumer upgrade order irrelevant, but it's also the strictest of the four modes in terms of what schema changes it permits.
</details>

13. What are the two storage backend types supported by Apicurio Registry?

<details>

<summary>Show Answer</summary>

**Answer: A Kafka-topic-based backend (kafkasql) and a SQL-based backend (sql, e.g. PostgreSQL)**

**Explanation:**
Apicurio Registry lets you choose the backend via the `APICURIO_STORAGE_KIND` environment variable: `kafkasql` stores schema metadata in a Kafka topic, while `sql` stores it in a relational database such as PostgreSQL. Karapace, by contrast, always uses a Kafka topic (`_schemas`) as its only storage option.
</details>

14. Which license did Confluent switch key components (including Schema Registry) to around 2018, making them no longer fully open source?

<details>

<summary>Show Answer</summary>

**Answer: The Confluent Community License**

**Explanation:**
Around 2018, Confluent moved several core components, including Schema Registry, to the Confluent Community License. This license keeps the source code visible but prohibits certain uses — such as offering it as a competing managed service — that OSI-approved open-source licenses would allow.
</details>

15. What property do Kafka clients set so an Avro serializer/deserializer knows where to find the schema registry?

<details>

<summary>Show Answer</summary>

**Answer: schema.registry.url**

**Explanation:**
The `schema.registry.url` property tells `KafkaAvroSerializer`/`KafkaAvroDeserializer` (and their equivalents) which REST endpoint to use for registering and looking up schemas. Changing only this property lets you swap between Karapace, Apicurio, and Confluent without any application code changes.
</details>

## Hands-on Questions

16. Write an Avro field definition that adds an optional `discountCode` field to an existing `Order` schema in a BACKWARD-compatible way.

<details>

<summary>Show Answer</summary>

**Answer:**
```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

**Explanation:**
Combining the union type `["null", "string"]` with `default: null` means a reader using the new schema, when reading old data that lacks this field, automatically receives `null`. Adding a required field with no default would break BACKWARD compatibility, so preserving compatibility with existing data always requires specifying a default.
</details>

17. Write a curl call to the Confluent-compatible REST API to register a new Avro schema under the `orders-value` subject.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

**Explanation:**
Sending a `POST` request to `/subjects/<subject>/versions` registers the schema. `<topic>-value` is Confluent's standard subject naming convention for the value payload of a given topic. The `schema` field in the request body carries the actual Avro schema as an escaped JSON string. On registration, the registry validates the new schema against previous versions according to the configured compatibility mode.
</details>

18. Write the core container spec (image, environment variables) for an Apicurio Registry Deployment that uses a Kafka topic as its storage backend, running in the same namespace as a Strimzi Kafka cluster.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
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
```

**Explanation:**
`APICURIO_STORAGE_KIND=kafkasql` tells Apicurio to persist schema metadata in a Kafka topic instead of requiring a separate database. `APICURIO_KAFKASQL_BOOTSTRAP_SERVERS` must point at the bootstrap service Strimzi creates (`<cluster-name>-kafka-bootstrap`). To use the SQL backend instead, set `APICURIO_STORAGE_KIND=sql` along with the corresponding datasource connection settings.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/04-schema-registry.md) | [Next Quiz: Kafka Connect and MirrorMaker](./05-kafka-connect-mirrormaker-quiz.md)
