# パート 5: Kafka Connect と MirrorMaker

> **サポートバージョン**: Strimzi 0.45+, Kafka 3.9, MirrorMaker 2\
> **最終更新**: July 9, 2026

## Kafka Connect の概要

Kafka Connect は、カスタムの統合コードを書くことなく、Kafka と外部システム（database、object storage、search engine など）の間でデータを移動するための framework です。connector 設定を通じて data pipeline を宣言的に記述すると、残りは Connect が処理します。

Connectors には、データが流れる方向に応じて 2 つの種類があります。

* **Source connectors** は、外部システムから Kafka へデータを取り込みます。Debezium は代表的な例です。database の write-ahead log（または binlog）を読み取り、row-level の変更イベントを CDC (Change Data Capture) pipeline として Kafka に stream します。JDBC Source Connector は、より単純な query-based のアプローチを取り、定期的に table を polling して結果を Kafka に書き込みます。
* **Sink connectors** は、Kafka から外部システムへデータを送り出します。S3 Sink Connector は topic data を JSON や Parquet などの形式で S3 に書き込み、Elasticsearch Sink Connector は検索と分析のために topic records を index 化します。

Kafka Connect は 2 つの runtime mode をサポートします。

* **Distributed mode**: 複数の worker process（Pods）が group を形成し、単一の Connect cluster として動作します。1 つの worker が group coordinator として機能し、connectors とその tasks を group 全体に分散します。worker が停止した場合、その tasks は生存している workers に自動的に re-balance されます。connector lifecycle（create、delete、reconfigure）は REST API（default では port 8083）を通じて操作されます。これは Kubernetes で使用される唯一の mode です。
* **Standalone mode**: file-based の offset store を持つ単一 process で、local development を想定しています。高可用性や水平 scaling がないため、Kubernetes では使用されません。

Distributed workers は、offset、connector/task configuration、task status を 3 つの internal topics（`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`）に永続化します。これらの topics が失われると、cluster 上のすべての connector が state を失うため、production deployment では必ず replication factor を少なくとも 3 に設定する必要があります。

## Strimzi で Kafka Connect をデプロイする

Strimzi は、`KafkaConnect` CRD を通じて distributed Connect cluster 自体を管理し、その上で動作する個々の connector instances を `KafkaConnector` CRD を通じて管理します。`KafkaConnector` resources を使用すると、REST API を手動で呼び出す代わりに、connectors を GitOps でデプロイおよび version control できます。Strimzi に `KafkaConnector` resources を reconcile させるには、`KafkaConnect` resource に `strimzi.io/use-connector-resources: "true"` annotation が必要です。

Connector plugins は base Strimzi Kafka Connect image には bundle されていないため、custom image が必要です。Strimzi が推奨する pattern では、Dockerfile を手書きする必要がありません。plugin artifacts（tgz/zip/jar、または Maven coordinates）を `KafkaConnect.spec.build` の下で宣言すると、Strimzi Operator が image を build し、指定した registry（Amazon ECR など）へ push します。

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

`spec.build` が変更されるたびに（plugin の追加、version の引き上げなど）、Operator は image を rebuild し、Deployment を自動的に roll out します。`pushSecret` で参照される Secret には、ECR への push を成功させるための registry credentials（`docker-registry` type の Secret）が必要です。必要であれば、IRSA を通じてその access を付与できます。

### KafkaConnector — Debezium PostgreSQL source の例

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

### KafkaConnector — S3 sink の例

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

`kubectl get kafkaconnector -n kafka` は各 connector の status を表示します。`Ready: True` condition は、その tasks が workers に割り当てられ、実行中であることを意味します。

## MirrorMaker 2 Architecture

MirrorMaker 2 (MM2) は、Kafka Connect framework の上に構築された、topic-level の cluster-to-cluster replication tool です。単に messages を copy するだけではありません。source cluster の partitioning を保持し、consumer group offsets を変換します。これにより、disaster recovery 時に clean な consumer failover が可能になります。内部的に、MM2 は 3 つの connectors で構成されています。

* **MirrorSourceConnector**: 実際の message replication を行い、topic configuration と ACLs も同期します。
* **MirrorCheckpointConnector**: source cluster の consumer group offsets を target cluster 上の対応する offsets に定期的に変換し、それらを checkpoint topic に記録します。この offset translation によって、DR cluster に fail over する consumer は「どこまで処理済みだったか」を把握できます。
* **MirrorHeartbeatConnector**: source cluster が稼働しており、replication pipeline が機能していることを示す heartbeat messages を定期的に送信します。これは replication lag や完全な disconnection の検出に使用されます。

MM2 は source topic の名前を target cluster でそのまま再利用しません。default の `DefaultReplicationPolicy` は remote topics に `<source-cluster-alias>.<topic>` という名前を付けます。たとえば、`us-east-1` という alias の cluster から `orders` topic を replicate すると、target 上には `us-east-1.orders` という remote topic が作成されます。この naming convention により、consumers は topic name だけで locally-produced messages と mirrored messages を区別できます。また、bidirectional setup で infinite replication loops を防ぐ仕組みとしても機能します。

## Disaster Recovery Patterns

### Active-Passive

これは最も一般的な pattern です。replication は primary-region cluster から DR-region cluster への一方向で実行されます。通常運用では、applications は primary cluster にのみ接続し、DR cluster は idle のまま replicated data を蓄積します。regional failure が発生したら、MirrorCheckpointConnector によって記録された offset translations を使って consumer groups を DR cluster に移動し、利用可能な最新の checkpoint から consumption を再開します。これは完全な exactly-once cutover ではありません。failure に対して checkpoint がいつ取得されたかによって、少数の messages が再処理される可能性があります。また MM2 replication は asynchronous であるため、failure の瞬間にまだ DR cluster へ replicate されていない message は失われます（RPO は replication lag によって制限され、zero ではありません）。しかし重要な利点は、その lag window に data loss を最小化しながら高速に recovery できることです。

### Active-Active

両方の regions が traffic を処理し、各 cluster が相手側へ bidirectional に replicate します。これには実際の risk があります。topic が A → B に mirror され（`A.orders` として）、明示的に防止しない限り、B → A にそのまま mirror され返され、永久に loop する可能性があります。Strimzi/MM2 は、`replication.policy.class` で設定される naming policy（default の `DefaultReplicationPolicy`、または remote topics に元の名前を維持させたい場合の `IdentityReplicationPolicy`）を通じてこれを防ぎます。すでに remote-cluster prefix（`A.orders` など）を持つ topics は、さらなる mirroring から除外されます。`topicsPattern` を cross-region replication が実際に必要な topics のみに絞ることで、偶発的な replication loops に対する第 2 の保護層を追加できます。

### KafkaMirrorMaker2 CR の例

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

`connectCluster: dr-region` は、MM2 worker Pods に対して、Connect 自身の internal topics を格納するためにどの cluster（ここでは DR region）を使用するべきかを指示します。`sync.group.offsets.enabled: "true"` を有効にすると、MirrorCheckpointConnector は変換済み offsets を DR cluster の `__consumer_offsets` に定期的に書き込みます。これにより、fail over した consumer は最初に offsets を手動で commit しなくても consumption を再開できます。

## Cross-Region Replication Considerations

* **Network cost and latency**: regions 間（または AZs 間でさえ）の replication には data transfer cost と round-trip latency が伴います。MM2 workers を target region で実行し、source cluster から data を pull するのが一般的です。batch size（`producer.override.batch.size`）と compression（`producer.override.compression.type: zstd`）を tuning すると、実際に転送される volume が減り、cross-region data transfer cost の削減に直接つながります。
* **`sync.topic.acls.enabled`**: source cluster の topic ACLs も target に同期するかどうかを制御します。有効にすると access control policy を二重に保守する必要がありません。しかし 2 つの clusters の security posture が異なる場合（たとえば DR cluster が primary より厳格な access を要求する場合）、無効にして各側で ACLs を独立して管理する方が安全なことがあります。
* **Monitoring replication lag**: MM2 は replication health のための独自 metrics を公開します。`replication-latency-ms` は message が source で produce されてから target に完全に replicate されるまでの時間を報告し、checkpoint connector の lag-related metrics は offset translation がどれだけ最新かを示します。これらを Prometheus に scrape し、SLA（例:「replication lag を 5 分未満に保つ」）に基づいて alert することで、DR cluster が実際に fail over 可能な状態にあることを継続的に検証できます。

## 次のステップ

Kafka Connect と MirrorMaker 2 による data movement と disaster recovery が整ったら、次のステップは、この workload が fully managed の Amazon MSK service とどのように統合されるか、またはどのように比較されるかを確認することです。これは [パート 6: MSK Integration](./06-msk-integration.md) で扱います。

[メインページに戻る](./)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md) に挑戦してください。
