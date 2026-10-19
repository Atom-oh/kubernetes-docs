# 第5部: Kafka ConnectとMirrorMaker

> **確認済みの基準バージョン**: Strimzi 1.3.0、Kafka 4.3.1、Debezium PostgreSQL 3.6.3.Final、Aiven S3 sink 3.4.3\
> **最終確認日**: 2026年10月16日

## Connect workerとconnector

Kafka Connectは、Kafkaと外部システムの間でデータを移動するプラグインを実行します。設定だけで動作するのは、適切なプラグインがすでに存在し、データベースやストレージの権限、形式、ネットワークなどの前提条件も満たされている場合に限られます。

| 方向 | 例 | 重要な違い |
| --- | --- | --- |
| Source: 外部システム → Kafka | Debezium PostgreSQL CDC | 初期スナップショットと論理WALストリーミングは、JDBCによるポーリングとは異なる |
| Sink: Kafka → 外部システム | Aiven S3 sink | 対応形式と配信動作は個々のプラグインによって異なる |

分散モードでは、**Kafka broker**がworker groupを調整し、選出されたworker leaderが割り当てを計算します。workerが停止すると再割り当てが起きますが、時間がかかり、メッセージが再処理される場合があります。connector taskの失敗は、workerの停止と常に同じ事象とは限りません。失敗内容を調べ、再起動動作を設定してください。

Standalone Connectはコンテナ内やKubernetes上でも実行できますが、分散workerのフェイルオーバーはありません。Strimziの `KafkaConnect` は分散モードを管理します。workerを3つにしても、PostgreSQL connectorが1 taskしか使わないなら、3 taskに増えるわけではありません。

分散Connectは、compactionを有効にしたconfig、source-offset、status topicを使います。Config topicは**1 partition**にする必要があります。Connectの各deploymentには、それぞれ異なるgroup IDとtopic名を指定してください。ここではbrokerが3台あるためRF=3を基準にしています。brokerが少ない環境でも使える普遍的な最小値ではありません。レプリケーションはバックアップではありません。Sinkのconsumer offsetは通常、source-offset保存用topicではなくKafkaのconsumer groupに保存されます。

## Strimzi v1はapiVersionの変更だけではない

Strimzi 1.3.0は `kafka.strimzi.io/v1` APIを提供します。古いリソースはupgradeの前にこのリリースの移行手順で変換してください。`v1beta2` という文字列だけを置き換えてはいけません。

| リソース | 現行v1のfield |
| --- | --- |
| KafkaConnect worker group | `spec.groupId` |
| KafkaConnectの内部topic名 | `spec.configStorageTopic`、`spec.offsetStorageTopic`、`spec.statusStorageTopic` |
| KafkaMirrorMaker2の宛先とworker保存先 | `spec.target` と、その配下の独自の `groupId` および3つのtopic名field |
| KafkaMirrorMaker2のsource接続 | `spec.mirrors[].source` |

旧MM2の `connectCluster`、`clusters`、`sourceCluster`、`targetCluster`、`heartbeatConnector` fieldは、このv1 schemaにはありません。Apache MM2にheartbeat connectorの実装が含まれていても、`KafkaMirrorMaker2` v1で設定できるfieldになるわけではありません。

## Connectの例を準備する

[第2部](./02-strimzi-operator.md)の、TLS/SCRAMとTopic/User Operatorを設定した3 brokerの `my-cluster` を使用します。デプロイする前に、例のECRアカウントとrepository、DB/S3名を置き換えてください。さらに次の依存関係を準備します。

- `debezium-db-credentials`: `password` keyを持つKubernetes Secret。
- `rds-ca`: 信頼するPostgreSQL/RDS CA chainを含む `ca.crt` keyを持つSecret。
- 既存のECR repository、有効な `kubernetes.io/dockerconfigjson` 形式で `ecr-registry-credentials` と名付けたpush Secret、およびnodeによるimage pullの許可。
- **Connect Pod用**のAWS workload identity。対象のS3 bucket/prefixに権限を絞ります。Pod IdentityまたはIRSAを設定し、プラグインが実際に使うcredential chainを検証してください。Buildをpushするidentityと、実行時のS3 identityは別です。

ECR認証tokenは12時間で期限切れになります。build前にpush Secretを維持または更新してください。IRSA roleを割り当てただけで、選択したimage builderがECRにloginできるとは限りません。Strimzi 1.3はBuildahだけでConnect imageをbuildします。実際に使うnode上でbuild Podの要件を確認してください。

以下を `create-topics.py` として保存して実行し、`connect-topics.json` を適用します。7日間のデータ保持はこのラボ用の設定です。パイプラインを信頼する前に、停止時間と復旧要件に合わせて保持期間を決めてください。

```python
import json
from pathlib import Path

topics = [
    ("connect-cluster-configs", 1, "compact"),
    ("connect-cluster-offsets", 3, "compact"),
    ("connect-cluster-status", 3, "compact"),
    ("orders-db.public.orders", 3, "delete"),
    ("orders-db.public.order_items", 3, "delete"),
]
items = []
for name, partitions, cleanup in topics:
    config = {"cleanup.policy": cleanup, "min.insync.replicas": 2}
    if cleanup == "delete":
        config["retention.ms"] = 604800000
    items.append({
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaTopic",
        "metadata": {"name": name, "namespace": "kafka",
                     "labels": {"strimzi.io/cluster": "my-cluster"}},
        "spec": {"partitions": partitions, "replicas": 3, "config": config},
    })
Path("connect-topics.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
```

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: connect-cluster
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
          name: connect-cluster-
          patternType: prefix
        operations: [Read, Write, Create, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: orders-db.
          patternType: prefix
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: connect-cluster
          patternType: literal
        operations: [Read]
      - resource:
          type: group
          name: connect-orders-s3-sink
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

Userリソースを `connect-user.yaml` として保存します。作成権限はConnect内部topicのprefixに絞ります。5つのtopicは、明示した設定でTopic Operatorが事前作成します。Sourceデータtopicの自動作成は無効です。テーブルやtopicを追加するときは、対応する設定も明示的に更新してください。

## Connectをbuildしてデプロイする

`connect.yaml` として保存します。ダウンロードする2つのプラグイン成果物にはSHA-512 checksumがあります。`spec.build` はサポートされる方法の1つです。テスト済みのprebuilt imageや、サポート対象のplugin image volumeも使用できます。buildの成功だけでは、DBやS3への接続確認にはなりません。

Directory config providerは、許可されたpathにmountしたSecretを読み込みます。Kubernetes APIからSecretを読むRBAC権限は不要です。これにより、provider設定もアクセス権もなかった不完全な `${secrets:...}` の例を置き換えます。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 4.3.1
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
  groupId: connect-cluster
  configStorageTopic: connect-cluster-configs
  offsetStorageTopic: connect-cluster-offsets
  statusStorageTopic: connect-cluster-status
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-cluster
    passwordSecret:
      secretName: connect-cluster
      password: password
  config:
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    offset.flush.interval.ms: 60000
    topic.creation.enable: false
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    config.providers: dir
    config.providers.dir.class: org.apache.kafka.common.config.provider.DirectoryConfigProvider
    config.providers.dir.param.allowed.paths: /mnt/debezium
  template:
    pod:
      volumes:
        - name: debezium-credentials
          secret:
            secretName: debezium-db-credentials
        - name: rds-ca
          secret:
            secretName: rds-ca
    connectContainer:
      volumeMounts:
        - name: debezium-credentials
          mountPath: /mnt/debezium
          readOnly: true
        - name: rds-ca
          mountPath: /mnt/rds-ca
          readOnly: true
  build:
    output:
      type: docker
      image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/connect-cluster:kafka4.3.1-deb3.6.3-s3-3.4.3
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo.maven.apache.org/maven2/io/debezium/debezium-connector-postgres/3.6.3.Final/debezium-connector-postgres-3.6.3.Final-plugin.tar.gz
            sha512sum: 400495c485a1da532c5d7e2dcc3bbb1b7f7dcdbcdc74c82529309cb89a2c37298319ea45ea00414b3ce750a51ad01084e104725e810c55c1a7c1981baff201a0
      - name: aiven-s3
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.3/s3-sink-connector-for-apache-kafka-3.4.3.zip
            sha512sum: d355c7d41713dab83384a51e28b6670f63775a0aa394eb0d9e99172d862f53d9e42c54534369cdcfefadfeb4f50e7ffac2029c65dd878f0def3db33058627758
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

```bash
python3 create-topics.py
kubectl apply -f connect-topics.json -f connect-user.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/connect-cluster
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/connect-cluster-configs kafkatopic/connect-cluster-offsets \
  kafkatopic/connect-cluster-status kafkatopic/orders-db.public.orders \
  kafkatopic/orders-db.public.order_items
kubectl apply -f connect.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=900s kafkaconnect/connect-cluster
```

`strimzi.io/use-connector-resources: "true"` を設定した場合、connectorの変更はCRを通じて管理してください。REST APIへの直接変更はreconcileで元に戻される場合があります。Connect REST APIとKubernetesの更新権限を制限してください。このworker deployment内のすべてのプラグインは、mountされたSecretとworkload identityを共有します。信頼ドメインが異なる場合は、別々のConnect deploymentに分離してください。

## PostgreSQL CDC source

`source.yaml` を適用する前に、PostgreSQLの論理レプリケーションを有効にし、必要なreplication slot/WAL sender、replication user、table privilegeを用意します。RDS PostgreSQLでは、論理レプリケーションparameterを有効にするため再起動が必要な場合があります。実際のengine versionに対応する手順に従ってください。保持されるWALを監視してください。slotが停止したままだと、ストレージを使い切る可能性があります。通常の再起動手順としてslotを削除してはいけません。

権限を持つtable ownerが、`orders` database内にpublicationを作成します。

```sql
CREATE PUBLICATION debezium_orders_pub
FOR TABLE public.orders, public.order_items;
```

必要なupdate/delete eventを扱えるよう、適切なprimary keyまたはreplica identityがあることを確認してください。Connectorは最初にsnapshotを取り、その後WALをstreamingします。PostgreSQL connectorが使うtaskは1つです。`tasksMax` は最大数であり、並列実行が保証される値ではありません。

```yaml
apiVersion: kafka.strimzi.io/v1
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
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

Mountしたpasswordはmanifestに出力されません。Secretを変更すれば既存のDB接続にも即時反映されると想定せず、認証情報のrotationと再起動・再設定時の動作をテストしてください。

## Aiven S3 sink

`sink.yaml` として保存します。実際の3.4.3 connector classは `io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector` です。以前の例で使っていた `io.aiven.kafka.connect.s3.S3SinkConnector` classは、このartifactにはありません。`flush.size` と `rotate.schedule.interval.ms` もその設定keyではないため、別vendorのS3 connectorからコピーしてはいけません。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: REPLACE-WITH-YOUR-BUCKET
    aws.s3.region: ap-northeast-2
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    format.output.type: jsonl
    format.output.fields: key,value,offset,timestamp
    file.compression.type: gzip
    file.max.records: 10000
```

ここに保存されるのは、operationと変更前後のデータを含む**CDC event envelope**であり、最新状態を表すtableが自動的に作成されるわけではありません。Sourceとsinkではschema envelopeを有効にしたJSON converterを使います。Converter設定は実際のKafka recordと一致させてください。`file.max.records` はrecordのまとめ方を制御し、workerの `offset.flush.interval.ms` は定期的なflushに影響します。いずれも、すべてのobjectが一定時間内に到着する保証ではありません。

明示的なcredential optionを指定しない場合は、AWSのdefault credential chainを使います。対象の保存先と必要なKMS keyに限って、プラグインが必要とするobject/multipart操作を許可してください。通常event、delete、tombstone、retry、再起動後のreplayを試し、archiveを復旧元として扱う前に動作を確認してください。S3 objectだけでend-to-endのexactly-once動作が得られるわけではありません。

```bash
kubectl apply -f source.yaml -f sink.yaml
kubectl -n kafka get kafkaconnector orders-db-source orders-s3-sink -o yaml
```

現行generation、condition、`status.connectorStatus.connector.state`、各taskのstate/traceを確認してください。実際のsourceと宛先で進行していることも調べます。`Ready=True` はOperatorの状態観測であり、データが最新である証明ではありません。

## MirrorMaker 2とディザスターリカバリー

MM2はrecordのbyte列とpartition番号を保ったまま、宛先側で新しいoffsetを付けて書き込みます。Source側のoffset番号は保持しません。また、schema registry ID、アプリケーションtransaction、外部sinkの状態、すべてのsecurity policyを自動移行するわけではありません。

| コンポーネント | 責務と制約 |
| --- | --- |
| MirrorSourceConnector | Recordをコピーし、offset-sync mappingを出力。topic/config/ACLの同期は設定による |
| MirrorCheckpointConnector | Source group offsetを変換してcheckpointを出力。条件を満たす停止中の宛先groupを更新することもある |
| Apache MirrorHeartbeatConnector | Heartbeat recordを出力。Taskはsource dataを読まずに送信できるため、heartbeatがあるだけではsourceの正常性や複製完了を証明しない |

Active-passiveでは一方向のレプリケーションと、明示的な切り替え手順を使います。Sourceを復旧できない場合、障害前に複製されていないrecordが失われることがあります。再生されるrecordは重複する可能性があり、replay期間が短いとも限りません。複製状況とcheckpointの新しさを測定し、旧writerを停止・隔離し、宛先側の権限とschemaを確認してから、アプリケーションendpointとtopic購読先を切り替え、読み取り位置から再開できることをテストしてください。これらのアプリケーション側の手順をMM2が実行するわけではありません。

Active-activeでは、`DefaultReplicationPolicy` がremote topic名にprefixを付け、origin chainにすでに含まれるaliasへ**戻る**cycleを検出します。prefix付きtopicをすべて除外するわけではありません。3つ目のクラスターへのmulti-hop複製は正当な構成になり得ます。`IdentityReplicationPolicy` はこの命名情報を失い、同等のloop保護を提供しません。方向別のfilterとownershipを明示して設定してください。これは複数writer間の競合を一般的に解決する仕組みではありません。

## 現行KafkaMirrorMaker2 v1の例

この一方向templateでは、クラスター間のDNS/network接続、宛先側の3 broker、`kafka` namespace内に列挙するsource/target Secret、および別途用意したKafka ACLが必要です。Endpoint文字列はplaceholderです。両クラスターに到達できる場所でworkerを実行してください。`spec.target` が選ぶのはKafkaの保存先であり、Kubernetes regionではありません。

| Identity | 計画する必要がある権限範囲 |
| --- | --- |
| Source | 選択したtopicのread/describe、選択したgroup offsetのdescribe |
| Target | Connect内部topicとworker group、対象remote topicおよびMM2内部topicのwrite/create、offset mapping/checkpointのread、選択した停止中group offsetの更新 |

内部topicは適切なcompaction/partition設定で事前作成するか、選択した設定で必要になる作成権限だけを付与してください。Sourceとtargetで別々の認証情報を使えます。この例ではoffset-syncをtargetに保存し、ACL/configのコピーを無効にして、宛先のpolicyを明示的に管理します。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 4.3.1
  replicas: 3
  target:
    alias: dr-region
    bootstrapServers: dr-kafka-bootstrap.REPLACE.example.com:9093
    groupId: primary-to-dr
    configStorageTopic: primary-to-dr-configs
    offsetStorageTopic: primary-to-dr-offsets
    statusStorageTopic: primary-to-dr-status
    tls:
      trustedCertificates:
        - secretName: dr-cluster-ca-cert
          certificate: ca.crt
    authentication:
      type: scram-sha-512
      username: mm2-target
      passwordSecret:
        secretName: mm2-target
        password: password
    config:
      config.storage.replication.factor: 3
      offset.storage.replication.factor: 3
      status.storage.replication.factor: 3
  mirrors:
    - source:
        alias: us-east-1
        bootstrapServers: primary-kafka-bootstrap.REPLACE.example.com:9093
        tls:
          trustedCertificates:
            - secretName: primary-cluster-ca-cert
              certificate: ca.crt
        authentication:
          type: scram-sha-512
          username: mm2-source
          passwordSecret:
            secretName: mm2-source
            password: password
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.topic.acls.enabled: false
          sync.topic.configs.enabled: false
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.group.offsets.enabled: true
          sync.group.offsets.interval.seconds: 60
          emit.checkpoints.interval.seconds: 60
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      topicsPattern: 'orders[.].*|payments[.].*'
      groupsPattern: 'orders-consumer-.*'
```

このpatternは `orders.` と `payments.` で始まるprefixに一致します。`orders` や `payments` だけのtopic、および `orders-db.public.orders` は含みません。実際のtopic一覧に合わせて調整してください。Source connectorとcheckpoint connectorでは、replication policy、separator、offset-syncの保存先を一致させる必要があります。

`sync.group.offsets.enabled=true` が更新するのは、offsetを変換できる**停止中または存在しない**対象groupだけです。消費中のgroupを上書きするものではありません。Consumerの参加状態、権限、mapping/checkpointの有無、targetですでにcommitされた位置も結果に影響します。この設定やOperatorのReady状態だけからfailover成功を判断してはいけません。

## Networkと監視

Workerをtarget regionで実行すると、sourceからworkerへのfetch通信はregion間を通ります。Workerの**target producer**を圧縮しても、すでに行われたfetch通信を遡って圧縮することはできません。Source producer/topicの圧縮設定と配置が重要です。1つの設定値によるコスト削減を約束するのではなく、両方のnetwork経路、CPU、遅延を測定してください。

`replication-latency-ms` はrecordのtimestampを基準に、targetがrecordを確認応答した時点で測定します。Timestamp mode、過去データのreplay、clock skewが値に影響します。`record-age-ms` はread pathで観測されます。partitionごとの進捗、error、データの新しさ、checkpointの新しさも監視してください。停止または空のstreamでは、古いsampleが残るか、sampleがなくなる場合があります。Prometheusのmetric名はexporterのmappingによって異なるため、Kafkaのmetric名をそのままPromQL名として使えるとは限りません。

## 参照資料と検証範囲

この例は、リリース済みv1 CRDとconnector本体の設定定義に照らして確認しています。ローカルでのMM2動作確認は、実際のregion間接続、database権限、ECR build、S3への配信、ディザスターリカバリーの切り替え成功を証明するものではありません。

- [Strimzi 1.3.0 CRD: 正式なresource field](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/install/cluster-operator)
- [Strimzi 1.3.0デプロイガイド](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Debezium 3.6 PostgreSQL connector](https://debezium.io/documentation/reference/3.6/connectors/postgresql.html)
- [Aiven S3 connector 3.4.3](https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/blob/v3.4.3/s3-sink-connector/README.md)
- [ECR認証tokenの有効期間](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetAuthorizationToken.html)
- [Kafka 4.3.1 MirrorSourceConnector](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceConnector.java)
- [Kafka 4.3.1 MirrorCheckpointTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorCheckpointTask.java)
- [Kafka 4.3.1 MirrorHeartbeatTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorHeartbeatTask.java)
- [Kafka 4.3.1 MirrorSourceTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceTask.java)

## 次のステップ

[第6部: MSK統合](./06-msk-integration.md)では、マネージドサービスの選択肢と比較します。

[メインページに戻る](./README.md)

## クイズ

[トピッククイズ](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
