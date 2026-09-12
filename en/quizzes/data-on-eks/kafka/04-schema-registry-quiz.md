# Schema Registry Quiz

Review schema contracts, encoding, compatibility, recovery and the deployment example.

## 1. Why does Kafka's basic record storage not enforce a schema contract?

<details>
<summary>Show answer</summary>

Keys and values are stored as bytes. Structural and business validation depends on serializers, applications and validation paths. Adding a field does not always break a consumer.

</details>

## 2. Can JSON be versioned and validated before runtime without a registry?

<details>
<summary>Show answer</summary>

Yes. JSON Schema, CI checks and versioned specifications can provide a contract. A registry centralizes governance and distribution; binary encoding is a separate choice.

</details>

## 3. What are the first five bytes in the common Confluent schema-ID payload framing?

<details>
<summary>Show answer</summary>

One magic byte and a four-byte schema ID, followed by the value. Protobuf also includes message indexes. This is not a universal rule for every registry or encoding.

</details>

## 4. Which main schema formats does Karapace 6.2.3 support?

<details>
<summary>Show answer</summary>

Avro, JSON Schema and Protobuf. Check JSON Schema draft/keyword validation and compatibility-analysis support separately.

</details>

## 5. What matters when checking Apache-2.0 and Confluent component licenses?

<details>
<summary>Show answer</summary>

Apache-2.0 includes conditions such as preserving required notices. Confluent server and client/Avro modules can have different licenses. Check the actual component and support contract instead of inferring terms from scale.

</details>

## 6. What enables Avro evolution, and what is a field default used for?

<details>
<summary>Show answer</summary>

Writer/reader schema resolution. A reader uses a default when the writer schema lacks that field. It does not permit a writer to omit an arbitrary required field.

</details>

## 7. Can a deleted Protobuf field number be reused for a different meaning?

<details>
<summary>Show answer</summary>

Do not reuse it. Old data or clients can interpret the number with its previous meaning. Reserve removed numbers/names as appropriate and check wire types and application semantics.

</details>

## 8. What is the usual rollout order for a backward-compatible schema change?

<details>
<summary>Show answer</summary>

Consumers first: the new reader must read the previous writer's data. Test business behavior too, and remember compatibility is configured for a subject rather than inherently for a topic.

</details>

## 9. Which direction does FORWARD compatibility check?

<details>
<summary>Show answer</summary>

The previous reader must read the new writer's data, typically allowing producers to upgrade first. This alone does not validate a new reader's replay of old data.

</details>

## 10. Does removing an Avro field always break forward compatibility?

<details>
<summary>Show answer</summary>

No. If the old reader has a default, it can supply the field missing from the new writer's data. Without a default it fails. Distinguish this from the backward direction, where the new reader no longer requires the field.

</details>

## 11. What must be checked for a cold-cache consumer and a registry migration?

<details>
<summary>Show answer</summary>

The identifier in a retained record must resolve to the same writer schema. Verify ID mappings, references, subject strategy, encoding, authentication and client versions. A URL change alone is not sufficient evidence.

</details>

## 12. Which mode requires both BACKWARD and FORWARD, and what does its TRANSITIVE variant add?

<details>
<summary>Show answer</summary>

FULL. FULL_TRANSITIVE checks both schema directions against all prior versions. Ordinary FULL compares with the latest previous version. Neither guarantees business semantics or application behavior.

</details>

## 13. Does Apicurio KafkaSQL store complete snapshot files in its snapshots topic?

<details>
<summary>Show answer</summary>

No. It records file paths. File durability, sharing and recovery need their own design. The lab disables scheduled snapshots and retains the full journal for replay after restart.

</details>

## 14. Which settings satisfy the default KafkaSQL 3.3.3 journal/snapshots topic checks?

<details>
<summary>Show answer</summary>

`cleanup.policy=delete`, `retention.ms=-1` and `retention.bytes=-1`. Monitor growth with indefinite retention. Do not copy a generic `_schemas` compaction configuration or short event retention.

</details>

## 15. Which Avro properties differ between a producer and a consumer?

<details>
<summary>Show answer</summary>

The producer uses `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer`; the consumer uses `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer`. Both need a registry URL plus their broker TLS/SASL configuration and library dependencies.

</details>

## 16. Write Avro definitions for a timestamp-millis field and a defaulted discountCode field.

<details>
<summary>Show answer</summary>

```json
[
  {"name":"createdAt","type":{"type":"long","logicalType":"timestamp-millis"}},
  {"name":"discountCode","type":["null","string"],"default":null}
]
```

These are definitions for a record's `fields` array. The logical type belongs inside the type object; the added field's null default applies when a new reader reads old data.

</details>

## 17. How do you register the chapter's order.avsc under the orders-value subject?

<details>
<summary>Show answer</summary>

Follow the chapter's `register.sh` example: parse the JSON and create a request file containing the schema string and `schemaType: AVRO`. POST it to `/apis/ccompat/v7/subjects/orders-value/versions`, checking HTTP failures. Configure compatibility first and retrieve the latest version afterward. The default TopicNameStrategy assumes topic `orders`.

</details>

## 18. Describe what connects the chapter's Apicurio deployment to the preceding Strimzi environment.

<details>
<summary>Show answer</summary>

Use image 3.3.3, `APICURIO_STORAGE_KIND=kafkasql`, `my-cluster-kafka-bootstrap.kafka.svc:9093`, SASL_SSL/SCRAM-SHA-512, the CA truststore, Secret-backed JAAS configuration and explicit hostname verification. Pre-create three storage topics and user ACLs, disabling automatic topic creation. Distinguish health checks on management port 9000 from HTTP API port 8080. HTTP API authentication is separate from Kafka authentication; the lab is not a public service.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/04-schema-registry.md) | [Next quiz](./05-kafka-connect-mirrormaker-quiz.md)
