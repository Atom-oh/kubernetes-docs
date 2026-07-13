# 第4部: Schema Registry（スキーマレジストリ）

> **サポート対象バージョン**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (compatible API)\
> **最終更新**: July 9, 2026

## Schema Registry が必要な理由

Kafka 自体は、すべてのメッセージを不透明なバイト配列として扱います。producer がその配列にどのような形式で書き込むかは気にしません。問題は、producer と consumer が通常は別々のアプリケーションであり、異なるチームが所有し、異なるスケジュールでデプロイされることです。producer がフィールドを追加したり型を変更したりした瞬間、その変更を知らない consumer はメッセージのデシリアライズに失敗するか、壊れた値を読み取ってしまいます。

### Schema-less JSON の問題

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

このような生の JSON payload は人間が読みやすい一方で、実際のコストを伴います。

* **強制される契約がない**: producer が `amount` を密かに文字列に変更しても、それを止めるものがありません。
* **検証は runtime のみ**: 欠落フィールドや型の不一致は、consumer が payload を解析しようとしたときに初めて表面化します。
* **Payload サイズ**: フィールド名がすべてのメッセージで繰り返されるため、バイナリ形式より大きくなり、高スループットでは実際のネットワーク/ストレージコストになります。
* **バージョン履歴がない**: 「この topic の schema のバージョン 3 はどのようなものだったか？」に答える方法がありません。

### Schema Registry が解決すること

Schema Registry は、Avro、Protobuf、JSON Schema のような構造化形式の schema を一元的に保存し、バージョン管理し、バージョン間の互換性ルールを強制する独立した service です。流れはおおよそ次のようになります。

1. メッセージを送信する前に、producer は自分の schema を registry に登録します（または検索します）。
2. registry は schema ID を返し、producer は完全な schema の代わりに、その ID だけを先頭に付けて（通常は 5-byte の magic-byte + ID header）payload をシリアライズします。
3. consumer はメッセージに埋め込まれた schema ID を読み取り、対応する schema を registry から取得して、それに従ってデシリアライズします。
4. 新しい schema version が登録されると、registry は互換性ルールに照らして確認し、違反している場合は登録を即座に拒否します。

これにより、producer と consumer は **互いの deployment schedule を知らなくても** 独立して進化できます。また、wire payload には schema ID だけが含まれるため、Avro/Protobuf のバイナリエンコーディングは JSON よりも大幅に小さくなります。

## 主要な実装の比較

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **ベンダー** | Aiven | Red Hat | Confluent |
| **ライセンス** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (2018 年以降、完全な open source ではない) |
| **サポート形式** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, Kafka Connect schemas, etc. | Avro, Protobuf, JSON Schema |
| **API 互換性** | Confluent REST API と互換 | Confluent-compatible mode (`ccompat`) | 元の API (de facto standard) |
| **Storage backend** | Kafka topic | Kafka topic or SQL (e.g. PostgreSQL) | Kafka topic |
| **同梱 REST Proxy** | Yes (Karapace REST Proxy) | No (registry only) | Separate commercial REST Proxy |
| **Commercial support terms** | Aiven の managed service、または community 経由 | Red Hat subscription 経由 | scale 時に Confluent Platform licensing が必要 |
| **EKS/Strimzi との適合性** | 強い — 純粋な open source、軽量 | 強い — multi-format、multi-backend | ライセンス確認が必要 |

**自己管理の EKS + Strimzi stack では、Karapace または Apicurio Registry を推奨します。** どちらも Apache-2.0 license で提供され、再配布や変更に制限はありません。対照的に、Confluent Schema Registry の Confluent Community License は、競合する managed service として提供することを明示的に禁止しており、2018 年以降は完全な open source ではありません。`kafka-avro-serializer` のような client-side library は現在も Confluent から公開されていますが、REST API には互換性があるため、`schema.registry.url` を Karapace または Apicurio に向けるだけで、通常はコード変更なしで動作します。

## Serialization Formats

### Avro

Avro は schema を JSON として定義し、data をコンパクトなバイナリ形式にシリアライズします。Kafka ecosystem で最も広く使われている形式であり、特に優れている機能は **schema resolution** です。**writer schema**（data が書き込まれたときに使用された schema）と **reader schema**（読み戻すときに使用される schema）は完全に一致している必要がなく、Avro が明確に定義されたルールに従って差分を解決します。

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

Protobuf schema は `.proto` file で定義され、`protoc` でコンパイルして各 target language のコードを生成します。Avro と同様にコンパクトなバイナリエンコーディングを生成しますが、明示的なフィールド番号を割り当て、より厳密な型システムを持つため、言語をまたいでより高品質な生成コードを作りやすくなります。Kafka ecosystem での Protobuf 採用は着実に増えています。

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

JSON Schema は JSON payload 自体の検証ルールを定義します。人間が読みやすく debug しやすい一方で、フィールド名がすべてのメッセージで繰り返されるため、payload は Avro や Protobuf よりかなり大きくなります。schema validation が必要だが、throughput や storage cost への感度が比較的低い workload に適しています。

### 3 つの形式の比較

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema definition | JSON | `.proto` IDL | JSON Schema |
| Payload size | 小さい | 小さい | 大きい |
| Human-readable | schema のみ | schema のみ | payload も可 |
| Cross-language codegen | 良い | 非常に良い | 良い |
| Kafka ecosystem adoption | 非常に高い | 高い (成長中) | 中程度 |
| Schema evolution rules | Writer/reader resolution | Field-number based | JSON Schema validation rules |

## 互換性戦略

新しい schema version が登録されると、registry は設定された compatibility mode に従って、前の version と照らし合わせて確認します。この 4 つの mode を正しく理解することは重要です。これは schema 管理で最もよく混同される概念です。

| Mode | Meaning | Deployment order |
| --- | --- | --- |
| **BACKWARD** | **new** schema を使う reader が、**old** schema で書かれた data を読める必要がある | **consumers** を先に upgrade |
| **FORWARD** | **old** schema を使う reader が、**new** schema で書かれた data を読める必要がある | **producers** を先に upgrade |
| **FULL** | BACKWARD と FORWARD の両方が成立 | どちらの順序でも安全 |
| **NONE** | 互換性チェックなし | 手動調整が必要 |

多くの人が最もよく逆に理解してしまう点は次のとおりです。

* **BACKWARD** は「new schema（reader として）が old data を読める」ことを意味します。実際には、**new-schema consumer を先にデプロイしても安全** ということです。producer がまだ old schema で書き込んでいる間でも、upgrade 済みの consumer はそれを問題なく読み取れます。
* **FORWARD** は「old schema（reader として）が new data を読める」ことを意味します。つまり、**producer を new schema に先に upgrade しても安全** ということです。old schema のまま動作している consumer も引き続き動作します。

### Backward-Compatible Change の例

`Order` schema に default value 付きの optional field を追加することは、BACKWARD compatible です。

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

new schema を使う consumer が old data（このフィールドを持たない data）を読む場合、単に `default` value（`null`）を取得するだけで、失敗しません。

### 破壊的変更の例

これらは典型的な BACKWARD-compatibility 違反です。

* **default のない required field の追加**: default のない新しい `discount_code` field を追加すると、new-schema reader は old data に存在しなかった field を期待するため、失敗します。（逆に、field を *削除* することは BACKWARD compatible ですが、代わりに FORWARD を壊します。old-schema reader は、削除済みの field が new data 上でも required であることを依然として期待するためです。）
* **field type の変更**: `amount` を `double` から `string` に切り替えると、既存のバイナリエンコード済み data を new type として decode できなくなります。
* **field の rename**（alias なし）: reader は新しい名前で field を探しますが、old data には古い名前でしか存在しません。

## Strimzi/EKS へのデプロイ

### Apicurio Registry のデプロイ (Kafka-Topic Storage)

Strimzi-managed Kafka cluster がすでに動作している前提で、Kafka-topic storage engine を backend として、同じ namespace に Deployment として Apicurio Registry をデプロイできます。

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

Apicurio は `kafkasql` の代わりに SQL backend（`APICURIO_STORAGE_KIND=sql`）もサポートしているため、すでに PostgreSQL/RDS instance を運用している場合は、registry をそちらに向けることもできます。対照的に Karapace は常に schema を Kafka topic（`_schemas`）に保存し、別個の backend configuration は必要ありません。

### Schema の登録

registry が起動したら、schema は REST API（Confluent-compatible endpoint を使用）を通じて登録します。

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### Client Configuration

Kafka producer/consumer application は、serializer を registry URL に向けます。

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

同じ `KafkaAvroSerializer` class は Karapace に対しても動作します。`schema.registry.url` を Karapace の REST endpoint（default では port 8081）に向けるだけです。registry implementation を入れ替えても application code を変更する必要がないことこそ、Confluent-compatible API が提供する価値です。

## 次のステップ

この部では、Schema Registry が、producer と consumer の両方が独立して進化する中で、data contract を安全に保つ方法を扱いました。第5部では Kafka Connect と MirrorMaker に進み、external system との統合と cluster 間の data replication を扱います。

[メインページに戻る](./)

## クイズ

この章で学んだ内容を確認するために、[Topic Quiz](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md) を試してみてください。
