# Kafka Connect と MirrorMaker クイズ

このクイズでは、Kafka Connect の source/sink connector モデル、distributed mode、Strimzi の `KafkaConnect`/`KafkaConnector` CRD、そして MirrorMaker 2 のアーキテクチャと disaster recovery パターンについての理解を確認します。

## 選択問題

1. データベースの WAL/binlog を読み取り、変更イベントを Kafka にストリーミングする Debezium のような connector は、どの種類の connector ですか？
   - A) Sink connector
   - B) Source connector
   - C) Filter connector
   - D) Transform connector

<details>

<summary>答えを表示</summary>

**回答: B) Source connector**

**解説:**
Source connectors は外部システムから Kafka へデータを取り込みます。Debezium は CDC (Change Data Capture) source connector の代表的な例です。データベースの write-ahead log（または binlog）を読み取り、行レベルの変更イベントを Kafka にストリーミングします。Sink connectors はその逆で、Kafka から S3 や Elasticsearch のような外部システムへデータを送り出します。
</details>

2. S3 Sink Connector と Elasticsearch Sink Connector に共通していることは何ですか？
   - A) 外部システムから Kafka にデータを取り込む
   - B) Kafka topic から外部システムへデータを送り出す
   - C) topic 間でデータを複製する
   - D) consumer group offset を管理する

<details>

<summary>答えを表示</summary>

**回答: B) Kafka topic から外部システムへデータを送り出す**

**解説:**
S3 Sink Connector と Elasticsearch Sink Connector はどちらも sink connectors であり、Kafka topic に蓄積されたデータを外部システムへ送り出します。S3 Sink Connector は topic データを JSON や Parquet などの形式で S3 bucket に書き込み、Elasticsearch Sink Connector は topic データを検索や分析のためにインデックス化します。
</details>

3. Kafka Connect の distributed mode で、1 つの worker が停止した場合はどうなりますか？
   - A) Connect cluster 全体が停止する
   - B) 停止した worker の tasks が、稼働している他の workers に自動的に rebalance される
   - C) connector が自動的に standalone mode に切り替わる
   - D) すべての offset 情報がリセットされる

<details>

<summary>答えを表示</summary>

**回答: B) 停止した worker の tasks が、稼働している他の workers に自動的に rebalance される**

**解説:**
distributed mode では、複数の worker processes が group を形成し、単一の Connect cluster として動作します。group coordinator が connectors と tasks を workers 全体に分散します。worker が停止すると、coordinator がそれを検知し、可用性を維持するために、その worker の tasks を残りの workers に自動的に rebalance します。これが standalone mode との重要な違いです。standalone mode は単一 process として実行され、高可用性はありません。
</details>

4. Kubernetes/Strimzi 環境で Kafka Connect の standalone mode が使用されない理由は何ですか？
   - A) REST API をサポートしていない
   - B) 高可用性や水平スケーラビリティがない
   - C) source connectors のみをサポートしている
   - D) TLS をサポートしていない

<details>

<summary>答えを表示</summary>

**回答: B) 高可用性や水平スケーラビリティがない**

**解説:**
standalone mode は、file-based offset store を持つ単一 process として実行され、ローカル開発やテスト向けに設計されています。worker が 1 つしかないため、失敗した場合に引き継ぐ別の worker がなく、workload を複数 node に分散することもできません。この制約のため、Kubernetes/Strimzi 環境では常に distributed mode を使用し、複数の worker Pods によって支えられます。
</details>

5. Strimzi で `KafkaConnector` CRD を使用する主な利点は何ですか？
   - A) REST API を直接呼び出す代わりに、GitOps を通じて connectors を宣言的に管理できる
   - B) connector plugin code を自動的に書いてくれる
   - C) distributed mode を standalone mode に変換する
   - D) offset storage topic が不要になる

<details>

<summary>答えを表示</summary>

**回答: A) REST API を直接呼び出す代わりに、GitOps を通じて connectors を宣言的に管理できる**

**解説:**
`KafkaConnector` CRD を使用すると、connectors の作成、削除、再設定のために Connect REST API を直接呼び出す必要はありません。YAML manifest に desired state を宣言すると、Strimzi Operator が実際の connector state と照合して reconcile します。これにより、connector configuration を Git repository で version control し、code review/CI pipelines を通じてデプロイする GitOps workflow が可能になります。
</details>

6. `KafkaConnect` resource で `KafkaConnector` CRD を有効にするために必要な annotation はどれですか？
   - A) `strimzi.io/kraft: enabled`
   - B) `strimzi.io/node-pools: enabled`
   - C) `strimzi.io/use-connector-resources: "true"`
   - D) `strimzi.io/connect-mode: distributed`

<details>

<summary>答えを表示</summary>

**回答: C) `strimzi.io/use-connector-resources: "true"`**

**解説:**
`KafkaConnect` resource の metadata に `strimzi.io/use-connector-resources: "true"` annotation を追加すると、Strimzi Operator はその Connect cluster を対象とする `KafkaConnector` resources を監視し、それらを実際の connectors として reconcile します。この annotation がない場合、`KafkaConnector` resources を作成しても効果はありません。
</details>

7. `KafkaConnect.spec.build` を通じて connector plugins を含む custom image を構築する Strimzi 推奨の方法の特徴は何ですか？
   - A) Dockerfile を手動で書く必要がある
   - B) plugin artifact URLs を宣言すると、Operator が image を構築し、指定した registry に push する
   - C) Images は Docker Hub にしか push できない
   - D) standalone mode でのみ動作する

<details>

<summary>答えを表示</summary>

**回答: B) plugin artifact URLs を宣言すると、Operator が image を構築し、指定した registry に push する**

**解説:**
Strimzi の推奨パターンは、`KafkaConnect.spec.build` に `output`（target registry image と push secret）および `plugins` のリスト（それぞれ tgz/zip/jar artifact URLs または Maven coordinates を指定）を宣言的に設定することです。Dockerfile は不要です。Strimzi Operator が build を実行し、生成された image を Amazon ECR などの registry に push します。
</details>

8. MirrorMaker 2 で、source cluster の consumer group offsets を target cluster 上の対応する offsets に変換する役割を持つ connector はどれですか？
   - A) MirrorSourceConnector
   - B) MirrorHeartbeatConnector
   - C) MirrorCheckpointConnector
   - D) MirrorTopicConnector

<details>

<summary>答えを表示</summary>

**回答: C) MirrorCheckpointConnector**

**解説:**
MirrorCheckpointConnector は、source cluster の consumer group offsets を target cluster 上の対応する offsets に定期的に変換し、それらを checkpoint topic に記録します。この offset translation により、DR cluster へ failover して consumption を再開する必要があるときに、consumer group は「どこまで処理済みだったか」を把握できます。MirrorSourceConnector は messages、topics、ACLs の実際の replication を処理し、MirrorHeartbeatConnector は replication pipeline が稼働していることを示す heartbeats を送信します。
</details>

9. MirrorMaker 2 のデフォルト `DefaultReplicationPolicy` は remote topics にどの命名規則を使用しますか？
   - A) `<topic>.<source-cluster-alias>`
   - B) `<source-cluster-alias>.<topic>`
   - C) `mirror-<topic>`
   - D) 元の topic name のまま

<details>

<summary>答えを表示</summary>

**回答: B) `<source-cluster-alias>.<topic>`**

**解説:**
`DefaultReplicationPolicy` は remote topics に `<source-cluster-alias>.<topic>` という名前を付けます。たとえば、`us-east-1` という alias の cluster から `orders` topic を replication すると、target cluster 上に `us-east-1.orders` という remote topic が作成されます。元の名前を変更せずに維持するには、代わりに `IdentityReplicationPolicy` が必要ですが、active-active setup で loop prevention が難しくなります。
</details>

10. active-passive と active-active の DR パターンの中核的な違いは何ですか？
    - A) active-passive はデータを圧縮し、active-active は圧縮しない
    - B) active-passive は一方向にのみ replication し、active-active は双方向に replication して loop prevention が必要になる
    - C) active-active は MirrorMaker 2 を使用しない
    - D) KafkaConnector CRD を使用するのは active-passive のみである

<details>

<summary>答えを表示</summary>

**回答: B) active-passive は一方向にのみ replication し、active-active は双方向に replication して loop prevention が必要になる**

**解説:**
active-passive パターンは primary cluster から DR cluster へ一方向に replication し、DR cluster は通常 idle 状態です。active-active パターンは両方の clusters 間で双方向に replication するため、両方の regions が traffic を処理できます。しかし、これにより replicated topic が origin cluster にそのまま mirror back され、無限 loop を引き起こす可能性があります。これを防ぐには、`replication.policy.class` と topic filters によって明示的に防止する必要があります。
</details>

## 短答問題

11. source cluster が alive であり、replication pipeline が機能していることを示す heartbeat messages を定期的に送信する MirrorMaker 2 connector の名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: MirrorHeartbeatConnector**

**解説:**
MirrorHeartbeatConnector は、source cluster が正常に動作しており、replication pipeline が中断されていないことを示す heartbeat messages を定期的に送信します。これらの heartbeats が一定時間届かなくなった場合、その不在を replication lag や source cluster への接続断を検出する signal として使用できます。
</details>

12. Strimzi Kafka Connect の distributed workers が offsets、connector/task configuration、task status を保存するために使用する 3 つの internal topic configuration keys の名前は何ですか？（例: offset.storage.topic）

<details>

<summary>答えを表示</summary>

**回答: `offset.storage.topic`, `config.storage.topic`, `status.storage.topic`**

**解説:**
distributed-mode Connect workers は 3 つの internal topics を使用します。offsets には `offset.storage.topic`、connector/task configuration には `config.storage.topic`、task status には `status.storage.topic` です。これらの topics が失われると、cluster 上のすべての connectors が state を失うため、production deployments では replication factor を少なくとも 3 に設定する必要があります。
</details>

13. MirrorMaker 2 が source cluster の topic ACLs も target cluster に sync するかどうかを制御する configuration key は何ですか？

<details>

<summary>答えを表示</summary>

**回答: `sync.topic.acls.enabled`**

**解説:**
`sync.topic.acls.enabled` を `true` に設定すると、source cluster の topic ACLs も target cluster に sync されるため、access control policy を二重に管理する必要がありません。ただし、2 つの clusters の security posture が異なる場合、たとえば DR cluster がより厳格な access control を必要とする場合は、これを無効にして各側で ACLs を独立して管理する方が安全な場合があります。
</details>

14. message が source cluster で生成されてから target に完全に replication されるまでの時間を報告する、MirrorMaker 2 が公開する metric の名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: `replication-latency-ms`**

**解説:**
`replication-latency-ms` は MirrorMaker 2 が公開する主要 metrics の 1 つであり、message が source cluster で生成されてから target cluster に完全に replication されるまでの経過時間を報告します。これを Prometheus に scrape して alerting することで、replication lag SLA を継続的に検証できます。
</details>

15. Strimzi で、設定済み clusters のうち MM2 worker Pods が自身の internal topics（offsets、configuration など）を保存するために使用する cluster を指定する `KafkaMirrorMaker2` resource の `spec` field は何ですか？

<details>

<summary>答えを表示</summary>

**回答: `connectCluster`**

**解説:**
`KafkaMirrorMaker2.spec.connectCluster` は、`spec.clusters` で定義された cluster aliases の 1 つを指し、MM2 worker Pods が自身の Kafka Connect internal topics（offset、configuration、status storage topics）を保存する cluster を決定します。通常は DR または target cluster に設定されます。
</details>

## ハンズオン問題

16. `connect-cluster` という名前の `KafkaConnect` cluster（`strimzi.io/use-connector-resources: "true"` annotation が設定済み）上で動作する Debezium PostgreSQL source connector 用の `KafkaConnector` resource を書いてください。単一 task に制限してください。

<details>

<summary>答えを表示</summary>

**回答:**
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

**解説:**
`metadata.labels.strimzi.io/cluster: connect-cluster` label は、この `KafkaConnector` をどの `KafkaConnect` cluster 上で実行するかを Strimzi Operator に伝えます。`spec.class` は実際の connector implementation class（Debezium PostgreSQL connector）を指定し、`plugin.name: pgoutput` は PostgreSQL の logical replication output plugin を指定します。`tasksMax: 1` は、PostgreSQL source connector が単一の replication slot しか使用できないため、その work を複数 tasks に並列化できないという事実を反映しています。
</details>

17. `us-east-1` という alias の cluster から `dr-region` という alias の cluster へ、`orders.*` と `payments.*` に一致する topics を一方向に replication し、consumer group offsets も sync する `KafkaMirrorMaker2` resource を書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
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

**解説:**
`mirrors` list の各 entry は 1 つの replication direction（`sourceCluster` から `targetCluster`）を定義します。`topicsPattern` は replication を `orders.*` と `payments.*` に制限し、`checkpointConnector.config.sync.group.offsets.enabled: "true"` を設定すると、変換された consumer group offsets が target cluster の `__consumer_offsets` に書き込まれます。`connectCluster: dr-region` は、MM2 workers が internal topics を保存する cluster として DR region を指定します。
</details>

18. active-active configuration で topic が loop（A から B、B から A、さらに B...）内で無限に mirror されるのを防ぐために確認する 2 つの settings を説明してください。

<details>

<summary>答えを表示</summary>

**回答:**
1. `replication.policy.class` — デフォルトの `DefaultReplicationPolicy` では、remote-cluster prefix（`<alias>.<topic>`）をすでに持つ topics は、さらなる mirroring から自動的に除外されます。
2. `topicsPattern` — 各 mirror direction の pattern を狭め、実際に replication が必要な topics だけを明示的に含めることで、意図しない topics が replication cycle に巻き込まれるのを防ぎます。

**解説:**
`DefaultReplicationPolicy` の命名規則（`<source-cluster-alias>.<topic>`）自体が loop に対する最初の防御線です。cluster B が `A.orders` のような topic を cluster A に mirror back しようとすると、MM2 はそれをすでに prefix が付いた remote topic として認識し、再度 mirror しません。さらに、各 mirror direction の `topicsPattern` を明示的に狭めることで、configuration mistake や通常と異なる topic naming pattern が誤って replication loop を引き起こすリスクを低減できます。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [次のクイズ: MSK Integration](./06-msk-integration-quiz.md)
