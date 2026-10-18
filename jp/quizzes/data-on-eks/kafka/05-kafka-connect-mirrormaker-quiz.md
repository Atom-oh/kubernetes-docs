# Kafka ConnectとMirrorMakerクイズ

このクイズでは、章で使うStrimzi v1設定、実際のplugin、replication、復旧の条件を確認します。

## 1. Debezium PostgreSQLとS3 sinkは、それぞれどちら向きにデータを移動しますか？

<details>
<summary>解答を表示</summary>

Debeziumはsourceであり、snapshot/WALの変更をKafkaへ送ります。S3 sinkはKafka recordをS3へ送ります。各pluginのformatとdelivery動作を確認してください。

</details>

## 2. Debezium recordをAiven S3 sinkでarchiveすると、現在のdatabase tableを自動的に再構築できますか？

<details>
<summary>解答を表示</summary>

いいえ。この例ではoperationとbefore/after dataを含むCDC eventをarchiveします。現在のstateをmaterializeするには、key、delete/tombstone、順序、replayを扱う必要があります。

</details>

## 3. distributed Connectのgroup coordinatorとworker leaderは、どのように異なりますか？

<details>
<summary>解答を表示</summary>

groupはKafka brokerが調整し、選出されたworker leaderがassignmentを計算します。worker障害では、task障害とは別に、遅延した再割り当てやreplayが発生する場合があります。

</details>

## 4. standalone ConnectはKubernetes上で実行できませんか？

<details>
<summary>解答を表示</summary>

実行できますが、distributed worker failoverはありません。StrimziのKafkaConnectはdistributed modeを管理します。workerを増やしても、単一taskのconnectorが自動的に並列化されるわけではありません。

</details>

## 5. KafkaConnector CRで管理中のconnectorをRESTから直接編集すると、何が起きる可能性がありますか？

<details>
<summary>解答を表示</summary>

operatorがconnectorをCRのdesired stateに戻す可能性があります。変更にはCRを使い、Kubernetesの更新権限とConnect REST accessを制限してください。

</details>

## 6. KafkaConnector reconciliationを有効にするannotationと、この例で使うAPI versionは何ですか？

<details>
<summary>解答を表示</summary>

`strimzi.io/use-connector-resources: "true"`と`kafka.strimzi.io/v1`です。v1への移行では`groupId`やinternal topic名などのfieldも変わります。`apiVersion`だけを書き換えても不十分です。

</details>

## 7. `spec.build`で指定すべきものと、ECR認証の扱いを説明してください。

<details>
<summary>解答を表示</summary>

plugin version、URL、checksum、output image tagを指定します。有効なpush Secretとimage-pull permissionを維持してください。ECR tokenは12時間で失効します。runtimeのS3 identityとbuild/push認証は別の仕組みです。

</details>

## 8. MM2のoffset-sync mappingとcheckpointは何のために使いますか？

<details>
<summary>解答を表示</summary>

MirrorSourceConnectorがsource/target offset mappingを出力し、MirrorCheckpointConnectorがそれを使ってsource group commitを変換します。source offsetとtarget offsetが同じとは限りません。

</details>

## 9. DefaultReplicationPolicyはremote topicにどのような名前を付け、cycleをどのように検出しますか？

<details>
<summary>解答を表示</summary>

`<source-alias>.<topic>`を使い、origin chain内ですでにtarget aliasへ戻っているcycleを検出します。prefix付きのtopicをすべて除外するわけではなく、第三のclusterへのmulti-hop replicationが正当な場合もあります。

</details>

## 10. active-passive failoverでは、MM2以外に何を準備する必要がありますか？

<details>
<summary>解答を表示</summary>

旧writerをfenceし、replication/checkpointのfreshnessを測り、target側のpermissionとschemaを確認し、endpoint/subscriptionを変更して、再開位置を検証します。sourceを復旧できなければ未replicate dataを失う可能性があります。重複replayも測定してください。

</details>

## 11. ApacheのMirrorHeartbeatTaskがheartbeatを送信していれば、source dataのreplicationは健全だといえますか？

<details>
<summary>解答を表示</summary>

いいえ。このtaskはsource dataを読まずにheartbeatを出力できます。partitionの進捗、error、checkpointのfreshnessも確認してください。また、ApacheのclassとStrimzi 1.3のv1 CRDがサポートするfieldを区別してください。

</details>

## 12. Connect v1のinternal topic fieldと、config topicのpartition/retention要件は何ですか？

<details>
<summary>解答を表示</summary>

`spec.configStorageTopic`、`spec.offsetStorageTopic`、`spec.statusStorageTopic`です。config topicにはcompactionを使い、partition数を1にします。worker groupには`spec.groupId`を設定します。sink group offsetは別です。

</details>

## 13. `sync.topic.acls.enabled=true`にすると、sourceのsecurity policy全体がそのまま複製されますか？

<details>
<summary>解答を表示</summary>

いいえ。Kafka 4.3.1は選択されたliteral topic ACLを処理し、ALLOW WRITEを除外し、ALLOW ALLをREADにdowngradeします。すべてのuser、cluster policy、外部IAM policyを移行するわけではありません。この例ではtarget policyを別途管理します。

</details>

## 14. `replication-latency-ms`とcross-region compressionを解釈する際、何に注意しますか？

<details>
<summary>解答を表示</summary>

これはtarget acknowledgement時刻からrecord timestampを引いた値です。clock skew、timestamp mode、replayの影響を受けます。target Regionのworkerでtarget producerのcompressionを有効にしても、すでにRegion間を通過したsource fetch trafficは減りません。

</details>

## 15. KafkaMirrorMaker2 v1でtargetとsourceの接続先はどこに定義しますか？

<details>
<summary>解答を表示</summary>

`spec.target`と`spec.mirrors[].source`です。targetにはalias、`bootstrapServers`、`groupId`、3つのinternal topic名が必要です。旧形式の`connectCluster`/`clusters`/`heartbeatConnector`構造を使わないでください。

</details>

## 16. 章で使うDebezium PostgreSQL KafkaConnectorを書き、その前提条件を説明してください。

<details>
<summary>解答を表示</summary>

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

logical replication、必要なprivilege、publication、適切なreplica identityを準備します。許可されたSecret-directory providerでpasswordを読み込み、DBのTLS hostnameを検証してください。taskは1つであり、slotが停滞して保持するWALを監視してください。

</details>

## 17. 章のv1 MM2例でgroup offsetを同期する主な条件は何ですか？

<details>
<summary>解答を表示</summary>

source/checkpointのreplication policyとoffset-syncsの配置を一致させ、`sync.group.offsets.enabled=true`を有効にします。有効なmapping/checkpointとpermissionが必要です。また、target groupはinactiveまたは未作成でなければなりません。実行中のconsumerを上書きしません。章の`mm2.yaml`にあるtarget/source構造を使ってください。

</details>

## 18. IdentityReplicationPolicyとtopicsPatternを使えば、双方向の任意writeを安全にできますか？

<details>
<summary>解答を表示</summary>

いいえ。Identityはorigin-prefix情報を失わせ、default policyと同等のloop検出機能もありません。topicの方向別所有者、filter、writer policy、切り替えを設計してください。topic filterだけではdata conflictや重複は解決されません。

</details>

---

[学習教材に戻る](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [次のクイズ](./06-msk-integration-quiz.md)
