# パート 4: Schema Registry

> **サポート対象バージョン**: Karapace 4.x, Apicurio Registry 3.x, Confluent Schema Registry (互換 API)\
> **最終更新**: July 9, 2026

## Schema Registry が必要な理由

Kafka 自体はすべてのメッセージを不透明なバイト配列として扱います。producer がその配列にどの形式で書き込むかは関知しません。問題は、producer と consumer は通常別々のアプリケーションであり、異なるチームが所有し、異なるスケジュールでデプロイされることです。producer がフィールドを追加したり型を変更した瞬間に、その変更を認識していない consumer はメッセージのデシリアライズに失敗するか、壊れた値を読み取ることになります。

### Schema のない JSON の問題

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

このような生の JSON payload は人間にとって読みやすい一方で、実際のコストを伴います。

* **強制される契約がない**: producer が `amount` を文字列に黙って変更することを防ぐものはありません。
* **検証は runtime のみ**: 欠落したフィールドや型の不一致は、consumer が payload をパースしようとしたときに初めて表面化します。
* **Payload サイズ**: フィールド名はすべてのメッセージで繰り返され、バイナリ形式より大きくなります。高スループットでは、実際のネットワーク・ストレージコストになります。
* **バージョン履歴がない**: 「この topic の schema のバージョン 3 はどのようなものだったか」に答える方法がありません。

### Schema Registry が解決すること

Schema Registry は、Avro、Protobuf、JSON Schema などの構造化形式の schema を一元的に保存・バージョン管理し、バージョン間の互換性ルールを強制する独立したサービスです。フローはおおよそ次のようになります。

1. メッセージを送信する前に、producer は自身の schema を registry に登録（または検索）します。
2. registry は schema ID を返し、producer は完全な schema の代わりに、その ID だけを先頭に付加して payload をシリアライズします（通常は 5 バイトの magic-byte + ID header）。
3. consumer はメッセージに埋め込まれた schema ID を読み取り、registry から一致する schema を取得して、それに従ってデシリアライズします。
4. 新しい schema バージョンが登録されると、registry は互換性ルールに照らしてチェックし、違反していれば登録を完全に拒否します。

これにより、producer と consumer は**互いのデプロイスケジュールを知ることなく**独立して進化できます。また、wire payload には schema ID だけが含まれるため、Avro/Protobuf のバイナリエンコーディングは JSON より大幅に小さくなります。

## 主要な実装の比較

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **ベンダー** | Aiven | Red Hat | Confluent |
| **ライセンス** | Apache License 2.0 | Apache License 2.0 | Confluent Community License (2018 年以降は完全なオープンソースではない) |
| **サポート形式** | Avro, JSON Schema | Avro, Protobuf, JSON Schema, OpenAPI, AsyncAPI, GraphQL, Kafka Connect schemas, など | Avro, Protobuf, JSON Schema |
| **API 互換性** | Confluent REST API と互換 | Confluent 互換モード (`ccompat`) | オリジナル API (事実上の標準) |
| **バンドルされた REST Proxy** | あり (Karapace REST Proxy) | なし (registry のみ) | 商用の REST Proxy が別途必要 |
| **商用サポート条件** | Aiven のマネージドサービスまたはコミュニティ経由 | Red Hat サブスクリプション経由 | 大規模利用では Confluent Platform のライセンスが必要 |
| **EKS/Strimzi への適合性** | 強い — 純粋なオープンソースで軽量 | 強い — 複数形式・複数 backend | ライセンスレビューが必要 |

**セルフマネージドの EKS + Strimzi スタックには、Karapace または Apicurio Registry を推奨します。**どちらも Apache-2.0 ライセンスで提供され、再配布や変更に制限はありません。一方、Confluent Schema Registry の Confluent Community License は、競合するマネージドサービスとして提供することを明示的に禁止しています。これは 2018 年以降、完全なオープンソースではありません。`kafka-avro-serializer` などの client-side library は引き続き Confluent から公開されていますが、REST API には互換性があるため、通常は `schema.registry.url` を Karapace または Apicurio に向ければコード変更なしで動作します。

## シリアライゼーション形式

### Avro

Avro は schema を JSON として定義し、データをコンパクトなバイナリ形式にシリアライズします。Kafka ecosystem で最も広く使われている形式であり、際立った特徴は **schema resolution** です。**writer schema**（データの書き込み時に使用）と **reader schema**（データを読み戻す際に使用）は、完全に一致している必要はありません。Avro は明確に定義されたルールに従って差分を解決します。

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

Protobuf schema は `.proto` ファイルで定義され、`protoc` でコンパイルして各ターゲット言語のコードを生成します。Avro と同様にコンパクトなバイナリエンコーディングを生成しますが、明示的なフィールド番号を割り当て、より厳格な型システムを備えているため、言語をまたいでより高品質な生成コードになる傾向があります。Kafka ecosystem では Protobuf の採用が着実に増えています。

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

JSON Schema は JSON payload 自体の検証ルールを定義します。人間にとって読みやすくデバッグも容易ですが、フィールド名が各メッセージで繰り返されるため、payload は Avro や Protobuf よりかなり大きくなります。schema 検証が必要である一方、スループットやストレージコストへの感度が低い workload に適しています。

### 3 つの形式の比較

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema 定義 | JSON | `.proto` IDL | JSON Schema |
| Payload サイズ | 小 | 小 | 大 |
| 人間が読めるか | Schema のみ | Schema のみ | Payload も |
| クロス言語 codegen | 良好 | 優秀 | 良好 |
| Kafka ecosystem での採用状況 | 非常に高い | 高い（増加中） | 中程度 |
| Schema evolution ルール | Writer/reader resolution | フィールド番号ベース | JSON Schema 検証ルール |

## 互換性戦略

新しい schema バージョンが登録されると、registry は設定された互換性モードに従って前のバージョンと比較します。この 4 つのモードを正しく理解することは重要です。これは schema 管理において最も誤解されやすい概念です。

| モード | 意味 | デプロイ順序 |
| --- | --- | --- |
| **BACKWARD** | **新しい** schema を使用する reader が、**古い** schema で書き込まれたデータを読み取れる必要がある | 先に **consumer** をアップグレード |
| **FORWARD** | **古い** schema を使用する reader が、**新しい** schema で書き込まれたデータを読み取れる必要がある | 先に **producer** をアップグレード |
| **FULL** | BACKWARD と FORWARD の両方を満たす | どちらの順序でも安全 |
| **NONE** | 互換性チェックなし | 手動での調整が必要 |

人々が最もよく逆に理解する部分:

* **BACKWARD** は「新しい schema（reader として）が古いデータを読み取れる」ことを意味します。実際には、**新しい schema の consumer を先にデプロイ**しても安全です。producer がまだ古い schema で書き込んでいる間でも、アップグレード済みの consumer は問題なく読み取れます。
* **FORWARD** は「古い schema（reader として）が新しいデータを読み取れる」ことを意味します。つまり、**producer を先に新しい schema へアップグレード**しても安全です。古い schema で稼働している consumer は引き続き動作します。

### Backward-Compatible な変更の例

`Order` schema に default 値を持つ optional field を追加することは、BACKWARD 互換です。

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

新しい schema を使用する consumer が、この field を持たない古いデータを読み取る場合、単に `default` 値（`null`）を取得するため、失敗しません。

### 破壊的変更の例

以下は典型的な BACKWARD 互換性違反です。

* **default なしで必須 field を追加する**: default のない新しい `discount_code` field を追加すると、新しい schema の reader は、その field が存在したことのない古いデータに field を期待するため失敗します。（逆に、field を*削除する*ことは BACKWARD 互換ですが、代わりに FORWARD を破壊します。古い schema の reader は、新しいデータで削除された field が依然として必須であると期待するためです。）
* **field の型を変更する**: `amount` を `double` から `string` に変更すると、既存のバイナリエンコード済みデータを新しい型としてデコードできなくなります。
* **field を名前変更する**（alias なし）: reader は新しい名前で field を探しますが、古いデータには古い名前でしか存在しません。

## Strimzi/EKS へのデプロイ

### Apicurio Registry のデプロイ（Kafka-Topic Storage）

Strimzi 管理の Kafka cluster がすでに稼働していると仮定すると、Kafka-topic storage engine を backing として、同じ namespace に Apicurio Registry を Deployment としてデプロイできます。

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

Apicurio は `kafkasql` の代わりに SQL backend（`APICURIO_STORAGE_KIND=sql`）もサポートしているため、すでに PostgreSQL/RDS instance を実行している場合は、registry をそちらに向けることもできます。一方 Karapace は、常に Kafka topic（`_schemas`）に schema を保存し、別途 backend 設定を必要としません。

### Schema の登録

registry の実行後、schema は REST API を通じて登録されます（Confluent 互換 endpoint を使用）。

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### Client 設定

Kafka producer/consumer アプリケーションは、serializer を registry URL に向けます。

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

同じ `KafkaAvroSerializer` class は Karapace に対しても動作します。`schema.registry.url` を Karapace の REST endpoint（デフォルトでは port 8081）に向けるだけです。registry 実装を入れ替えてもアプリケーションコードを変更する必要はありません。これこそが Confluent 互換 API が提供する価値です。

## 次へ

このパートでは、producer と consumer がそれぞれ独立して進化する中で、Schema Registry が両者間のデータ契約を安全に保つ仕組みを説明しました。パート 5 では Kafka Connect と MirrorMaker に進みます。外部システムとの統合、および cluster 間でのデータレプリケーションを扱います。

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[Topic Quiz](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)に挑戦してください。
