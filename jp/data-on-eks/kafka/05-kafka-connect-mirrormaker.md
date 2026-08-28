# Part 5: Kafka Connect and MirrorMaker

> **対応バージョン**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **最終更新**: July 9, 2026

## Kafka Connect の概要

Kafka Connect は、カスタム統合コードを書くことなく、Kafka と外部システム（データベース、オブジェクトストレージ、検索エンジンなど）の間でデータを移動するためのフレームワークです。コネクタ設定を通じてデータパイプラインを宣言的に記述すれば、Connect が残りを処理します。

コネクタには、データフローの方向に応じて 2 種類があります。

* **Source connectors** は、外部システムから Kafka へデータを取り込みます。代表例は Debezium で、データベースの write-ahead log（または binlog）を読み取り、行レベルの変更イベントを CDC（Change Data Capture）パイプラインとして Kafka にストリーミングします。JDBC Source Connector はより単純なクエリベースの方式を採用し、テーブルを定期的にポーリングして結果を Kafka に書き込みます。
* **Sink connectors** は、Kafka から外部システムへデータを送出します。S3 Sink Connector はトピックデータを JSON や Parquet などの形式で S3 に書き込み、Elasticsearch Sink Connector は検索および分析のためにトピックレコードをインデックス化します。

Kafka Connect は 2 つの実行モードをサポートしています。

* **Distributed mode**: 複数の worker プロセス（Pod）がグループを形成し、単一の Connect クラスターとして動作します。1 つの worker が group coordinator として機能し、コネクタとそのタスクをグループ内に分散します。worker が停止すると、そのタスクは存続している worker に自動的に再分散されます。コネクタのライフサイクル（作成、削除、再構成）は REST API（デフォルトではポート 8083）を通じて操作します。これは Kubernetes で使用される唯一のモードです。
* **Standalone mode**: ローカル開発向けの、ファイルベースの offset store を備えた単一プロセスです。高可用性や水平スケーリングがないため、Kubernetes では使用されません。

Distributed worker は、offset、コネクタ／タスク設定、およびタスクステータスを 3 つの内部トピック（`offset.storage.topic`、`config.storage.topic`、`status.storage.topic`）に永続化します。これらのトピックが失われると、クラスター上のすべてのコネクタが状態を失うため、本番デプロイでは常に replication factor を少なくとも 3 に設定する必要があります。

## Strimzi での Kafka Connect のデプロイ

Strimzi は、distributed Connect クラスター自体を `KafkaConnect` CRD で管理し、その上で実行される個々のコネクタインスタンスを `KafkaConnector` CRD で管理します。`KafkaConnector` リソースを使用すると、REST API を手作業で呼び出す代わりに、GitOps を通じてコネクタをデプロイおよびバージョン管理できます。Strimzi が `KafkaConnector` リソースをリコンサイルできるようにするには、`KafkaConnect` リソースに `strimzi.io/use-connector-resources: "true"` アノテーションが必要です。

コネクタプラグインはベースの Strimzi Kafka Connect イメージにはバンドルされていないため、カスタムイメージが必要です。Strimzi の推奨パターンでは Dockerfile を手作業で記述する必要がありません。`KafkaConnect.spec.build` でプラグインアーティファクト（tgz/zip/jar、または Maven 座標）を宣言すると、Strimzi Operator がイメージをビルドし、Amazon ECR など指定したレジストリにプッシュします。

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

`spec.build` が変更されるたびに（プラグインの追加、バージョンの更新など）、Operator はイメージを再ビルドし、Deployment を自動的にロールアウトします。`pushSecret` が参照する Secret には、ECR へのプッシュを成功させるためのレジストリ認証情報（`docker-registry` タイプの Secret）が必要です。必要に応じて IRSA を通じてそのアクセスを付与できます。

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

`kubectl get kafkaconnector -n kafka` は各コネクタのステータスを表示します。`Ready: True` 条件は、そのタスクが worker に割り当てられ、実行中であることを意味します。

## MirrorMaker 2 アーキテクチャ

MirrorMaker 2（MM2）は、Kafka Connect フレームワーク上に構築された、トピックレベルのクラスター間レプリケーションツールです。メッセージをコピーするだけでなく、ソースクラスターのパーティショニングを保持し、consumer group offset を変換します。これにより、ディザスターリカバリー時にクリーンな consumer failover が可能になります。MM2 は内部的に 3 つのコネクタで構成されています。

* **MirrorSourceConnector**: 実際のメッセージレプリケーションを実行し、トピック設定と ACL も同期します。
* **MirrorCheckpointConnector**: ソースクラスターの consumer group offset をターゲットクラスター上の同等の offset に定期的に変換し、checkpoint トピックに記録します。この offset 変換により、DR クラスターに failover した consumer は「すでにどこまで処理したか」を把握できます。
* **MirrorHeartbeatConnector**: ソースクラスターが稼働中であり、レプリケーションパイプラインが機能していることを示す定期的な heartbeat メッセージを送信します。これはレプリケーションラグや完全な切断の検出に使用されます。

MM2 はターゲットクラスターでソーストピックの名前をそのまま再利用しません。デフォルトの `DefaultReplicationPolicy` は、リモートトピックを `<source-cluster-alias>.<topic>` と命名します。たとえば、`us-east-1` という alias のクラスターから `orders` トピックをレプリケートすると、ターゲット上に `us-east-1.orders` という名前のリモートトピックが作成されます。この命名規則により、consumer はトピック名だけでローカル生成メッセージとミラーリングされたメッセージを区別できます。また、双方向セットアップでの無限レプリケーションループを防止するメカニズムも兼ねています。

## ディザスターリカバリーパターン

### Active-Passive

これは最も一般的なパターンです。レプリケーションは、primary region のクラスターから DR region のクラスターへ一方向に実行されます。通常運用では、アプリケーションは primary クラスターとのみ通信し、DR クラスターはアイドル状態のままレプリケートされたデータを蓄積します。リージョン障害が発生した場合、MirrorCheckpointConnector によって記録された offset 変換を使用して consumer group を DR クラスターに移動し、利用可能な最新の checkpoint から消費を再開します。これは完全な exactly-once cutover ではありません。checkpoint が障害に対してどのタイミングで取得されたかによっては、少数のメッセージが再処理される可能性があります。また、MM2 レプリケーションは非同期であるため、障害発生時点でまだ DR クラスターにレプリケートされていないメッセージは失われます（RPO はゼロではなく、レプリケーションラグによって制限されます）。ただし主な利点は、そのラグ期間にデータ損失を最小限に抑えながら迅速にリカバリーできることです。

### Active-Active

両方のリージョンがトラフィックを処理し、各クラスターが他方に対して双方向にレプリケートします。これには実際のリスクがあります。A → B にミラーリングされたトピック（`A.orders`）は、明示的に防止しなければ B → A にそのままミラーリングし返され、永遠にループする可能性があります。Strimzi/MM2 は、`replication.policy.class` で設定される命名ポリシー（デフォルトの `DefaultReplicationPolicy`、またはリモートトピックに元の名前を維持させる場合の `IdentityReplicationPolicy`）によりこれを防止します。すでにリモートクラスターの prefix（`A.orders` など）を持つトピックは、さらなるミラーリングから除外されます。`topicsPattern` を実際にクロスリージョンレプリケーションが必要なトピックのみに絞ることで、意図しないレプリケーションループに対する第 2 の保護層が加わります。

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

`connectCluster: dr-region` は、MM2 worker Pod に、Connect 独自の内部トピックの保存先として使用するクラスター（ここでは DR region）を指示します。`sync.group.offsets.enabled: "true"` を有効にすると、MirrorCheckpointConnector は変換した offset を定期的に DR クラスターの `__consumer_offsets` に書き込むため、failover した consumer は最初に手動で offset をコミットしなくても消費を再開できます。

## クロスリージョンレプリケーションに関する考慮事項

* **ネットワークコストとレイテンシー**: リージョン間（あるいは AZ 間）のレプリケーションには、データ転送コストと往復レイテンシーが伴います。MM2 worker はターゲットリージョンで実行し、ソースクラスターからデータを取得するのが一般的です。batch size（`producer.override.batch.size`）と compression（`producer.override.compression.type: zstd`）を調整すると、実際に転送するデータ量が削減され、クロスリージョンデータ転送コストの削減に直結します。
* **`sync.topic.acls.enabled`**: ソースクラスターのトピック ACL もターゲットに同期するかどうかを制御します。有効にするとアクセス制御ポリシーを二重に管理する必要はありませんが、2 つのクラスターのセキュリティ方針が異なる場合（たとえば DR クラスターでは primary より厳格なアクセスが必要な場合）は、無効にして各側で ACL を独立して管理する方が安全な可能性があります。
* **レプリケーションラグのモニタリング**: MM2 はレプリケーションの健全性に関する独自のメトリクスを公開します。`replication-latency-ms` は、メッセージがソースで生成されてからターゲットに完全にレプリケートされるまでの時間を報告します。また、checkpoint connector のラグ関連メトリクスは、offset 変換がどの程度最新かを示します。これらを Prometheus にスクレイピングし、SLA（例: 「レプリケーションラグは 5 分未満」）でアラートを設定することで、DR クラスターが実際に failover 可能な状態にあることを継続的に確認できます。

## 次のステップ

データ移動およびディザスターリカバリーのために Kafka Connect と MirrorMaker 2 を導入したら、次のステップは、このワークロードがフルマネージドの Amazon MSK サービスとどのように統合されるか、または比較されるかを確認することです。これについては、[Part 6: MSK Integration](./06-msk-integration.md) で説明します。

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md) に挑戦してください。
