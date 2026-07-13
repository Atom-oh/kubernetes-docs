# Schema Registry クイズ

このクイズでは、schema registry が存在する理由、Avro/Protobuf シリアライゼーションのトレードオフ、4 つの compatibility mode、主要な実装（Karapace、Apicurio、Confluent）間のライセンスの違いについての理解を確認します。

## 選択問題

1. Kafka broker が message content を検証しないという事実によって発生する、最も根本的な問題は何ですか？
   - A) Broker のスループットが低下する
   - B) Producer と consumer が互いの変更を知らないまま schema を進化させることができ、deserialization failure につながる
   - C) 複数の topic を作成できない
   - D) Partition rebalancing が不可能になる

<details>

<summary>回答を表示</summary>

**回答: B) Producer と consumer が互いの変更を知らないまま schema を進化させることができ、deserialization failure につながる**

**解説:**
Kafka はすべての message を不透明な byte array として扱い、data format を強制しません。Producer と consumer は通常、独立したスケジュールでデプロイされる別々のアプリケーションであるため、一方の schema change がもう一方を静かに壊し、deserialization failure や破損した value を引き起こす可能性があります。Schema registry は contract を一元管理し、compatibility を強制することでこれを解決します。
</details>

2. Schema-less JSON と比較して、Avro/Protobuf のような binary format を schema registry と組み合わせる最大の利点は何ですか？
   - A) 人間が読みやすくなる
   - B) Payload が小さくなり、schema change が一元的に検証される
   - C) Partition 数が自動的に調整される
   - D) Consumer group が不要になる

<details>

<summary>回答を表示</summary>

**回答: B) Payload が小さくなり、schema change が一元的に検証される**

**解説:**
Avro/Protobuf は field name を繰り返さない compact binary encoding を使用するため、payload は JSON より小さくなります。さらに、message は full schema ではなく schema ID のみを持ちます。実際の schema は registry によって管理され、新しい version が登録されるたびに compatibility が検証されます。一方、JSON は人間が直接読むには引き続き容易です。
</details>

3. Schema registry を使用する場合、wire 上の実際の message には何が含まれますか？
   - A) Full schema definition
   - B) Schema ID を含む短い header、その後に binary-encoded data
   - C) Schema registry の URL
   - D) Consumer group ID

<details>

<summary>回答を表示</summary>

**回答: B) Schema ID を含む短い header、その後に binary-encoded data**

**解説:**
Producer は schema を registry に登録（または検索）し、返された schema ID を、通常は magic byte とともに serialized message の先頭に付与します。Full schema definition 自体は message に含まれず、registry のみが保存します。これが payload を小さく保つ理由です。Consumer はこの ID を読み取り、registry から一致する schema を取得して残りを deserialize します。
</details>

4. 次の schema registry 実装のうち、Apache License 2.0 の下で配布されているものはどれですか？
   - A) Confluent Schema Registry
   - B) Karapace と Apicurio Registry の両方
   - C) Karapace のみ
   - D) Apicurio Registry のみ

<details>

<summary>回答を表示</summary>

**回答: B) Karapace と Apicurio Registry の両方**

**解説:**
Karapace（Aiven）と Apicurio Registry（Red Hat）は、どちらも Apache License 2.0 の下で配布されている純粋な open-source project です。Confluent Schema Registry は 2018 年以降 Confluent Community License によって管理されており、特定の商用利用に制限を設けているため、完全な open-source license ではありません。
</details>

5. Licensing friction を避けるために、self-managed EKS + Strimzi stack に推奨される組み合わせはどれですか？
   - A) Confluent Schema Registry のみ
   - B) Karapace または Apicurio Registry
   - C) Schema registry なし — JSON だけを使用する
   - D) AWS Glue Schema Registry のみが実行可能

<details>

<summary>回答を表示</summary>

**回答: B) Karapace または Apicurio Registry**

**解説:**
Karapace と Apicurio Registry はどちらも Apache-2.0 license であり、制限なく self-host できます。Confluent Schema Registry の Confluent Community License には、self-managed use の前に license review が必要となる条件が含まれます。どちらの open-source alternative も Confluent の API と互換性があるため、client は code change なしで切り替えられます。
</details>

6. Avro serialization において schema evolution を可能にする core mechanism は何ですか？
   - A) Field-number-based mapping
   - B) Writer schema と reader schema の間の resolution rules
   - C) JSON Schema `$ref` references
   - D) Compile-time code generation

<details>

<summary>回答を表示</summary>

**回答: B) Writer schema と reader schema の間の resolution rules**

**解説:**
Writer schema（data が書き込まれたときに使用されたもの）と reader schema（読み戻すときに使用されるもの）が異なる場合でも、Avro は定義済みの resolution rules を適用することで data を正しく decode できます。具体的には field を name で照合し、default を適用する、などです。Field-number-based mapping は Protobuf の特徴であり、Avro のものではありません。
</details>

7. Protobuf が Avro に対して相対的な優位性を持つのはどこですか？
   - A) Payload が常に小さい
   - B) 明示的な field number とより厳格な type system により、cross-language の generated code の品質が高くなる
   - C) Schema registry を必要としない
   - D) JSON より人間が読みやすい

<details>

<summary>回答を表示</summary>

**回答: B) 明示的な field number とより厳格な type system により、cross-language の generated code の品質が高くなる**

**解説:**
Protobuf は `.proto` IDL 内のすべての field に明示的な number を割り当て、厳格な type system を強制します。これにより、`protoc` を通じて複数の言語でより整理された generated client code が生成されやすくなります。Payload size は一般的に Avro と同程度であり、Protobuf も Avro と同様に schema registry と組み合わせて使われることが一般的です。
</details>

8. BACKWARD compatibility で設定された topic では、どちら側を先に upgrade しても安全ですか？
   - A) Producer
   - B) Consumer
   - C) Broker
   - D) ZooKeeper または KRaft controller

<details>

<summary>回答を表示</summary>

**回答: B) Consumer**

**解説:**
BACKWARD compatibility は「新しい schema を使用する reader が、古い schema で書き込まれた data を読めなければならない」ことを意味します。つまり、producer がまだ古い schema で書き込んでいる間でも、consumer を先に新しい schema へ upgrade できます。Upgrade された consumer は古い data を正しく読み取ります。一方、FORWARD は producer-first の deploy が安全な mode です。
</details>

9. FORWARD compatibility を正しく説明している文はどれですか？
   - A) 古い schema を使用する reader が、新しい schema で書き込まれた data を読めなければならない
   - B) 新しい schema を使用する reader が、古い schema で書き込まれた data を読めなければならない
   - C) Compatibility checking はまったく実行されない
   - D) Consumer は常に先に upgrade されなければならない

<details>

<summary>回答を表示</summary>

**回答: A) 古い schema を使用する reader が、新しい schema で書き込まれた data を読めなければならない**

**解説:**
FORWARD は「古い schema（reader として）が、新しい schema で書き込まれた data を読める」ことを意味します。この mode では、producer を先に新しい schema へ upgrade でき、古い schema で動作している consumer も正しく読み続けられます。B は BACKWARD、C は NONE、D は BACKWARD での安全な順序を説明しており、FORWARD ではありません。
</details>

10. 次の schema change のうち、BACKWARD compatibility に違反するものはどれですか？
    - A) Default value を持つ optional field を追加する
    - B) Default value を持たない required field を追加する
    - C) Field に doc comment を追加する
    - D) Field の name や type を変更せずに順序を入れ替える

<details>

<summary>回答を表示</summary>

**回答: B) Default value を持たない required field を追加する**

**解説:**
Default がない required field を追加すると、新しい schema を使用する reader が古い data（その field を持っていない）を読むときに value を期待しても見つからず、read failure が発生します。対照的に、field の削除は backward compatible です。新しい schema の reader は単にその field を探さないためです（ただしこれは代わりに FORWARD compatibility を壊します）。Default を持つ optional field の追加は BACKWARD-compatible change の典型例であり、doc comment の追加や field の並べ替え（Avro は name で照合する）は実際の data structure に影響しません。
</details>

## 短答問題

11. Consumer が message から正しい schema を見つけて deserialize するために読み取る情報は何ですか？

<details>

<summary>回答を表示</summary>

**回答: Schema ID**

**解説:**
Serializing 時、producer は full schema ではなく、registry によって発行された schema ID のみを含めます（通常は message の先頭付近に magic byte とともに encode されます）。Consumer はこの ID を読み取り、registry に一致する schema を問い合わせ、それを使って binary payload の残りを deserialize します。
</details>

12. BACKWARD compatibility と FORWARD compatibility の両方を同時に満たすことを要求する compatibility mode の名前は何ですか？

<details>

<summary>回答を表示</summary>

**回答: FULL**

**解説:**
FULL compatibility では、BACKWARD（新しい schema の reader が古い data を読める）と FORWARD（古い schema の reader が新しい data を読める）の両方を同時に満たす必要があります。これにより producer/consumer の upgrade order は関係なくなりますが、許可される schema change の観点では 4 つの mode の中で最も厳格でもあります。
</details>

13. Apicurio Registry がサポートする 2 つの storage backend type は何ですか？

<details>

<summary>回答を表示</summary>

**回答: Kafka-topic-based backend（kafkasql）と SQL-based backend（sql、例: PostgreSQL）**

**解説:**
Apicurio Registry では、`APICURIO_STORAGE_KIND` environment variable を通じて backend を選択できます。`kafkasql` は schema metadata を Kafka topic に保存し、`sql` は PostgreSQL などの relational database に保存します。一方、Karapace は常に Kafka topic（`_schemas`）を唯一の storage option として使用します。
</details>

14. Confluent が Schema Registry を含む key component を 2018 年頃に切り替え、完全な open source ではなくなった license は何ですか？

<details>

<summary>回答を表示</summary>

**回答: Confluent Community License**

**解説:**
2018 年頃、Confluent は Schema Registry を含む複数の core component を Confluent Community License へ移行しました。この license は source code を閲覧可能なままにしますが、競合する managed service として提供することなど、OSI-approved open-source license であれば許可される特定の利用を禁止しています。
</details>

15. Kafka client は、Avro serializer/deserializer が schema registry の場所を知るためにどの property を設定しますか？

<details>

<summary>回答を表示</summary>

**回答: schema.registry.url**

**解説:**
`schema.registry.url` property は、`KafkaAvroSerializer`/`KafkaAvroDeserializer`（および同等のもの）に、schema の登録と検索に使用する REST endpoint を伝えます。この property だけを変更することで、application code を変更せずに Karapace、Apicurio、Confluent を切り替えられます。
</details>

## ハンズオン問題

16. 既存の `Order` schema に optional な `discountCode` field を BACKWARD-compatible な方法で追加する Avro field definition を書いてください。

<details>

<summary>回答を表示</summary>

**回答:**
```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

**解説:**
Union type `["null", "string"]` と `default: null` を組み合わせることで、新しい schema を使用する reader がこの field を持たない古い data を読むときに、自動的に `null` を受け取ります。Default のない required field を追加すると BACKWARD compatibility が壊れるため、既存 data との compatibility を維持するには常に default を指定する必要があります。
</details>

17. `orders-value` subject の下に新しい Avro schema を登録するための、Confluent-compatible REST API への curl call を書いてください。

<details>

<summary>回答を表示</summary>

**回答:**
```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

**解説:**
`/subjects/<subject>/versions` に `POST` request を送信すると schema が登録されます。`<topic>-value` は、指定された topic の value payload に対する Confluent の標準的な subject naming convention です。Request body の `schema` field は、実際の Avro schema を escaped JSON string として持ちます。登録時、registry は設定された compatibility mode に従って、新しい schema を以前の version に対して検証します。
</details>

18. Strimzi Kafka cluster と同じ namespace で実行され、Kafka topic を storage backend として使用する Apicurio Registry Deployment の core container spec（image、environment variables）を書いてください。

<details>

<summary>回答を表示</summary>

**回答:**
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

**解説:**
`APICURIO_STORAGE_KIND=kafkasql` は、別の database を必要とせず、schema metadata を Kafka topic に永続化するよう Apicurio に指示します。`APICURIO_KAFKASQL_BOOTSTRAP_SERVERS` は、Strimzi が作成する bootstrap service（`<cluster-name>-kafka-bootstrap`）を指している必要があります。代わりに SQL backend を使用するには、対応する datasource connection settings とともに `APICURIO_STORAGE_KIND=sql` を設定します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/04-schema-registry.md) | [次のクイズ: Kafka Connect and MirrorMaker](./05-kafka-connect-mirrormaker-quiz.md)
