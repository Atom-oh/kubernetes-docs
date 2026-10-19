# パート 4: Schema Registry

> **検証基準**: Karapace 6.2.4、Apicurio Registry 3.3.3、Strimzi 1.3.0 / Kafka 4.3.1\
> **最終確認日**: 2026年10月16日

## Schema Registry を使う理由

Kafka はレコードのキーと値をバイト列として保存します。そのため、プロデューサーとコンシューマー の間で値の構造や意味が食い違うことがあります。フィールドを追加しても、必ず コンシューマーが壊れるわけではありません。影響はエンコーディング、reader、互換性ルールによって異なります。

Registry はスキーマをバージョン管理し、登録時に設定済みの互換性ルールを確認します。アプリケーションでは、対応する シリアライザー と検証経路を使う必要があります。Registry が Kafka の全レコードを自動検査したり、通貨やタイムスタンプの意味といった業務ルールを強制したりするわけではありません。

JSON にも契約を設けられます。JSON Schema、CI チェック、バージョン管理された仕様は、Registry の有無にかかわらず利用できます。一元化された Registry は、その契約の配布と管理に役立ちますが、バイナリエンコーディングは別の選択です。ペイロードサイズやストレージコストの削減を主張する前に、圧縮後のレコードを実測して比較してください。

### レコードに含まれるもの

一般的な Confluent の **schema-ID ペイロード形式**では、値の先頭に1バイトのマジックバイトと4バイトのスキーマIDがあり、合計5バイトの後にエンコードされた値が続きます。Protobuf 形式ではメッセージインデックスも含まれます。JSON Schema の シリアライザー は、引き続き値を JSON としてエンコードします。別の シリアライザー モード、ヘッダーを使う識別子、Apicurio 固有のエンコーディングには、それぞれ個別の設定が必要です。

シリアライザー はスキーマを登録または検索し、デシリアライザー は識別子を使って writer schema を取得します。通常、クライアントはスキーマをキャッシュするため、すべてのレコードで HTTP リクエストが発生するとは限りません。ただし、キャッシュが空の場合や新しいスキーマを使う場合は、Registry へのアクセスが必要になることがあります。対応する Kafka データ、アーカイブ、災害復旧用コピーを読み取れる期間中は、ID とスキーマの対応関係を保持してください。

## 実装の比較

| 実装 | 主なスキーマ形式 | API とストレージ |
| --- | --- | --- |
| Karapace 6.2.4 | Avro、JSON Schema、**Protobuf** | Confluent 互換 REST API、Kafka ベースのスキーマストレージ、REST プロキシ も提供 |
| Apicurio Registry 3.3.3 | Avro、Protobuf、JSON Schema、その他の artifact 種別 | ネイティブ API に加え `/apis/ccompat/v7` と `/apis/ccompat/v8`、KafkaSQL と SQL のストレージ選択肢 |
| Confluent Schema Registry | Avro、Protobuf、JSON Schema | Confluent API、セルフマネージド環境では Kafka ベースのストレージ |

Karapace と Apicurio は Apache-2.0 ライセンスで公開されています。このライセンスにも、必要な表示の保持などの条件があり、「制約がない」という意味ではありません。Confluent のリポジトリでは、Community ライセンスのサーバーモジュールと Apache-2.0 ライセンスのクライアント／Avro モジュールを区別しています。クラスター規模から商用利用の条件を推測せず、実際のコンポーネントのライセンスとサポート契約を確認してください。

API 互換性は役立ちますが、**URL だけを変えても移行計画にはなりません**。保持済みレコードを使って、スキーマID、参照、subject の命名、認証、クライアントのバージョン、wire encoding を検証してください。たとえば Apicurio の互換 API は、Confluent の exporter や暗号化機能をすべて実装しているわけではありません。リクエストの任意フィールドを受け付けても、そのルールを強制するとは限りません。Apicurio が保存できる artifact 種別 が、すべての Kafka シリアライザー で使えるとも限りません。Karapace にも ブローカー、認証、スキーマ トピック の設定が必要です。Kafka ベースのストレージだから設定不要、ということではありません。

## シリアライズ形式

### Avro

次の標準的な例を `order.avsc` として保存します。Avro は名前、default、alias、定義済みの型変換を使って writer schema と reader schema を照合します。タイムスタンプの `logicalType` はフィールドの `name` の隣ではなく、**type オブジェクトの内側**に置きます。フィールド属性の位置を誤ると、構文解析はできても論理タイムスタンプとして宣言されないことがあります。

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

ここでの `amount` は説明用の double にすぎません。実際の契約では単位、精度、丸め方法を定義してください。正確な小数金額が必要なら、適切な整数または decimal 表現を使います。

### Protobuf と JSON Schema

Protobuf は番号付きフィールドと、言語固有の生成コード／runtime API を使います。時間の単位を明示してください。`int64` だけでは論理タイムスタンプは宣言されません。削除したフィールド番号を再利用せず、必要に応じて削除済みの番号と名前を予約します。

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

JSON Schema は JSON を検証します。draft のバージョンや互換性分析の対応範囲は Registry ごとに異なります。検証に対応しているからといって、すべての keyword について完全な進化分析ができるわけではありません。これらは相互に置き換えられるエンコーディングではなく、それぞれ別の契約です。

| 形式 | wire 表現 | 進化時の考慮点 |
| --- | --- | --- |
| Avro | writer schema に基づくバイナリ | reader/writer の解決、default、名前、型変換 |
| Protobuf | 番号付きフィールドを使うバイナリ | フィールド番号と wire type を維持し、アプリケーション上の意味も確認 |
| JSON Schema | JSON | 受け入れる instance の集合、必須フィールド、追加プロパティ、draft 対応 |

## 互換性とデプロイ順序

Confluent 互換 API では、互換性を **subject** 単位で設定するか、グローバルの既定値を継承します。既定の `TopicNameStrategy` では、`orders` トピック の値に `orders-value` subject を使います。別の strategy では、複数の トピック で subject を共有したり、1つの トピック 内の record type ごとに subject を分けたりできます。

| モード | 必要な関係 | 一般的なスキーマ展開順序 |
| --- | --- | --- |
| BACKWARD | 新しい reader が直前の writer のデータを読める | 先に consumer |
| FORWARD | 直前の reader が新しい writer のデータを読める | 先に producer |
| FULL | 双方向 | 検査対象のスキーマ関係に対してはいずれの順序も可能 |
| NONE | 互換性を検査しない | 明示的に調整してテスト |

非推移モードは直前のバージョンと比較します。`_TRANSITIVE` を付けたモードは、過去のすべてのバージョンと比較します。古い保持レコードを再生する場合、最新バージョンだけの確認では不十分なことがあります。`FULL` は業務上の意味、アプリケーションの動作、過去のすべてのバージョンとの互換性を保証しません。`FULL_TRANSITIVE` はスキーマ比較の範囲を広げるもので、その保証を加えるものではありません。

Avro では、次のフィールドを追加すると、新しい reader は古いレコードに対して `null` を補えます。

```json
{"name":"discountCode","type":["null","string"],"default":null}
```

default は **reader による解決**のルールです。writer が任意の必須フィールドを省略してよいという意味ではありません。

| Avro の変更 | 重要な条件 |
| --- | --- |
| reader default なしでフィールドを追加 | 新しい reader は、そのフィールドがない古いレコードを読めない |
| フィールドを削除 | 後方互換。前方互換性は古い reader に default があるかによる |
| `double` を `string` に変更 | 互換性がない。Avro の数値型変換ではない |
| `int` を `long` に変更 | 新しい reader は古い整数値を受け入れられる。逆方向は異なる |
| フィールド名を変更 | reader alias や適用可能な default によって結果が変わる。両方向をテスト |

代表的な履歴データを使った reader/writer テストを、Registry の互換性 endpoint と併せて実行してください。両者は異なる種類の問題を検出します。

## Strimzi の基準構成で Apicurio をデプロイする

これは**認証を備えた公開 Registry ではなく、非公開のラボ環境**です。[パート 2](./02-strimzi-operator.md) に記載の `my-cluster`（namespace `kafka`）、3 ブローカー、Topic Operator と User Operator、port 9093 の TLS/SCRAM listener を前提とします。以下の HTTP API にはアプリケーション認証がありません。NetworkPolicy は、CNI が NetworkPolicy を適用する場合、同じ namespace のラベル付き pod から port 8080 への通信だけを許可します。該当する pod を作成したりラベル付けしたりできる利用者を制限してください。共有の本番環境では、Kafka SASL とは別に API TLS、認証、認可を設定します。内部 Service を使うだけでは、これらの制御は提供されません。

### ストレージ トピック と Kafka identity

`registry-storage.yaml` として保存します。アプリケーション identity が読み書きできるのは、指定した3つの トピック と consumer group prefix だけです。トピック は Topic Operator が事前作成するため、アプリケーションに トピック 作成権限は不要です。

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

KafkaSQL 3.3.3 は journal、snapshot、event トピック を初期化します。journal と snapshot トピック の検査では、既定で `cleanup.policy=delete`、`retention.ms=-1`、`retention.bytes=-1` が必要です。一般的な `_schemas` の compaction 設定や、event を通常の7日間だけ保持する設定を適用しないでください。レコードが無期限に保持されるため、ディスク使用量を監視し、テスト済みのバックアップとクリーンアップを計画してください。

KafkaSQL は journal と利用可能な snapshot からローカル SQL 状態を再構築します。snapshot トピック に格納されるのは**snapshot ファイルのパス**であり、snapshot ファイルそのものではありません。このラボでは定期 snapshot を無効にし、journal 全体を保持します。そのため pod を失うと再生が発生し、起動に時間がかかる可能性があります。永続的／共有 snapshot storage、backup、restore、journal の切り詰めには、別途リカバリー設計が必要です。group prefix は変更できますが、固定の `group.id` で KafkaSQL の状態を保持する方法は使いません。このリリースは、起動時の再生を保証するため一意の group を生成します。

### Deployment と Service

`registry.yaml` として保存します。CA と JAAS の値は Strimzi Secret から取得します。ホスト名検証 を明示的に有効にしています。リソース量と10分間の起動猶予はラボ用の初期値です。メモリ使用量と再生時間を実測してください。

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

port forwarding には Kubernetes へのアクセスが必要で、コマンドはフォアグラウンドで動作します。Secret に格納した環境変数を変更した後は、workload を再起動してください。SQL storage では、`APICURIO_STORAGE_KIND=sql` だけで PostgreSQL が設定されるわけではありません。SQL の種類を選び、専用 database、TLS、認証情報、リカバリー手順を用意してください。既定のインメモリ H2 database は、本番向けの永続ストレージではありません。

## アプリケーションと同じスキーマを登録する

別の ターミナル から `order.avsc` を `orders-value` に登録します。これにより、複数フィールドを持つ namespace 付きの例と、curl 文字列に埋め込まれた別の単一フィールドスキーマとの不一致を避けられます。最初のリクエストでは subject の互換性を明示的に設定し、HTTP エラーが発生すると curl はゼロ以外の終了コードを返します。

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

## Producer と コンシューマーの設定

次の設定は、パート 2 の ブローカー address、TLS trust、アプリケーション固有の Kafka identity をすでに構成した場合に**追加する**プロパティです。Registry の HTTP 認証情報と Kafka SASL の認証情報は別です。アプリケーションには、バージョンを固定した互換性のある Confluent Avro シリアライザー の依存関係を含めてください。Kafka や Strimzi をインストールしただけでは提供されません。

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

プロデューサーの例では、先に対応するスキーマを登録する必要があります。`specific.avro.reader=false` の場合、コンシューマーは汎用 Avro record を使います。生成済みの SpecificRecord class を使うには、対応するコードと reader 設定が必要です。既定の subject strategy は、アプリケーションの Kafka トピック が `orders` であることを前提とします。

Registry を変更する前に、保持済みレコードを使ったキャッシュが空の状態からの コンシューマーの読み込み、新バージョンの登録、互換性違反の拒否、スキーマ参照、再起動／リカバリーをテストしてください。元のスキーマID対応を保持するか、サポートされたデータ／識別子の移行を明示的に実施します。HTTP health check の成功だけでは、シリアライズの検証になりません。

## 参考資料と検証

この章の例は、固定したリリース構成と Strimzi／Kubernetes schema に照らして確認し、ローカルで Avro reader/writer テストを実行しました。これらの確認は、実際の image をデプロイして TLS ブローカー に接続することや、アプリケーションが使用する正確な シリアライザー バージョンを試すことの代わりにはなりません。

- [Apache Avro 仕様](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers: メッセージ型の更新](https://protobuf.dev/programming-guides/proto3/#updating)
- [Confluent の互換性ルール](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Confluent シリアライザー と wire format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html)
- [Karapace 6.2.4](https://github.com/Aiven-Open/karapace/tree/6.2.4)
- [Apicurio Registry 3.3.3](https://github.com/Apicurio/apicurio-registry/tree/3.3.3)
- [Apicurio compatibility API の対応表](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/ccompat/rest/README.md)
- [Apicurio KafkaSQL の設定](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/kafkasql/KafkaSqlConfiguration.java)
- [Apicurio トピック 設定の検証](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/util/KafkaAdminUtil.java)
- [Confluent コンポーネントのライセンス](https://github.com/confluentinc/schema-registry/blob/master/LICENSE)

## 次のステップ

[パート 5](./05-kafka-connect-mirrormaker.md) では、外部連携とクラスター間レプリケーションを扱います。レコードを複製する際には、スキーマストレージとIDの移行も考慮してください。

[メインページに戻る](./README.md)

## 確認クイズ

[トピックのクイズ](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
