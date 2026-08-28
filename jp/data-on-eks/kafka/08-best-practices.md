# パート8：ベストプラクティス

> **対応バージョン**: Apache Kafka 3.9, Strimzi 0.45+\
> **最終更新**: July 9, 2026

この詳細解説では、Kafkaの基礎、Strimziの運用、schema registry、Kafka Connect/MirrorMaker、MSK統合、モニタリングを取り上げました。この最終ドキュメントでは、本番稼働準備に関するベストプラクティスをカテゴリ別に集約し、これまでの7つのパートにおける重要項目を、単一の本番稼働チェックリストにまとめます。

## 1. Partition設計

### Partition数のサイジング

Topicでは、**想定される最大Consumer並列性**から始めます。特定のConsumer group内では、1つのPartitionを同時に消費できるConsumer instanceは1つだけです。そのため、Consumer groupをどこまでスケールさせる見込みかを決め、少なくともその数のPartitionを用意してください。ピーク時に20のConsumer instanceまでスケールアウトする予定なら、少なくとも20のPartitionが必要です。

Partitionの過剰な分割には実際のコストがあるため、避けるべきです。

- **開いたファイルハンドルの増加**: 各Partitionは複数のログセグメントファイル（`.log`、`.index`、`.timeindex`）を開いた状態に保つため、Brokerごとのオープンファイルディスクリプタ数はPartition数に比例して増加します。
- **メモリ負荷の増加**: Producer/Consumerのbatch bufferと、Broker上のreplication threadごとのbufferはPartition数に応じて増加します。
- **rebalancingとfailoverの低速化**: Broker障害時にcontrollerが行うleader electionの作業量はPartition数に応じて増加し、Consumer groupのrebalancingにも時間がかかります。

Confluentの従来の経験則では、**Brokerあたり4,000 Partition、clusterあたり200,000 Partition**程度がソフト上限とされていました。これは、ZooKeeperベースのcontrollerがmetadataのボトルネックだった時代の指針です。KRaftベースのcluster（Kafka 3.x+ controller quorum）は、controllerのmetadataパスがはるかに高速になったため、より多くのPartition数を処理できます。しかし、原則は変わりません。可能だからという理由だけでPartitionを過剰に分割せず、実際のload testingでワークロードの実際の上限を検証してください。

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### Partition keyの選択

hot partitionを避けるため、**高いcardinalityと均一な分布**を持つkeyを選択します。デフォルトのpartitionerはkeyをmurmur2でhash化し、Partition数で剰余を取ります。そのため、低いcardinalityのkey（例: 異なる値が少数しかない`country`や`status`）では、主要なトラフィック値に該当する少数のPartitionに負荷が集中し、他のPartitionはアイドル状態になります。十分に高いcardinalityを持つフィールド（例: `user_id`）を優先するか、低いcardinalityのkeyをsalt化（ランダムまたはtimestamp由来のsuffixを追加）して、より均一に分散させてください。

### Partition数の変更は慎重に扱う

**key付き**TopicのPartition数を増やすと、keyからPartitionへのmappingが壊れます。`partition_count`が変わるとすぐに`hash(key) % partition_count`も変わるため、同じkeyが変更前とは異なるPartitionに配置される可能性があります。これにより、次の2つの具体的な問題が発生します。

- **orderingの破綻**: Kafkaが順序を保証するのはPartition内だけです。そのため、同じkeyのmessageが複数のPartitionに分割されると、Consumerはkeyレベルの順序に依存できなくなります。
- **co-partitioningの破綻**: Kafka Streams（および同様のもの）のjoinでは、joinされるTopicが同じPartition数とpartitioning schemeを共有している必要があります。joinの片側だけでPartitionを変更すると、これが壊れます。

capacity planningの段階で余裕を持ったPartition数を決め、本番Topicがすでにkeyベースのorderingまたはjoinに依存している場合は、既存のTopicのPartitionを増やすのではなく、新しいTopicへ移行することを優先してください。

## 2. Producerのチューニング

| 設定 | 推奨値 | 目的 |
|---------|--------------------|---------|
| `acks` | `all`（durabilityが重要なTopic向け） | すべてのin-sync replica（ISR）からのacknowledgmentを待機し、Broker障害でデータが失われないようにする |
| `min.insync.replicas`（Topic/Broker設定） | `2`（replication.factor=3の場合） | `acks=all`と組み合わせることで、成功前に少なくとも2つのreplicaへwriteが到達することを要求します。Producer client propertyとしてではなく、Topic（`kafka-configs.sh --entity-type topics`）またはBrokerのdefaultに設定します |
| `linger.ms` | `5`–`20` | 少量のlatencyと引き換えに、より大きなbatchと高いthroughputを得る |
| `batch.size` | `32768`–`65536`（32–64KB） | batchあたりの最大byte数を増やし、requestあたりのthroughputを向上させる |
| `enable.idempotence` | `true` | Producerのretryによる重複writeを防止する |
| `compression.type` | `lz4` または `zstd` | networkとstorageのコストを削減する |

```properties
# Producer settings for durability-critical topics (orders, payments, etc.)
# (min.insync.replicas is a topic/broker setting, not a producer property — shown here for reference only)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

`enable.idempotence=true`は、これと互換性のない方法で`acks`または`retries`を明示的に上書きしない限り、**Kafka 3.0以降のdefault**です。Producerに一意のproducer IDとPartitionごとのsequence numberを割り当てるため、Brokerは一時的なnetwork errorによるretryを透過的にdeduplicateできます。これは完全なexactly-once semanticsとは異なります。idempotenceが除去するのはProducerからBrokerへのhopにおける重複のみであり、真のend-to-end exactly-onceにはtransactional API（`transactional.id`）も必要です。

`lz4`は、ほとんどのワークロードでCPU overheadとcompression ratioのバランスに優れています。`zstd`は、JSON/textが多いpayloadに有用な、より高い圧縮率を提供しますが、その代わりCPU使用量はやや高くなります。`gzip`の圧縮率は高いものの、CPU消費が大きいため、一般に高throughputのProducerには推奨されません。

## 3. Consumerのチューニング

### rebalance stormの回避

処理に`max.poll.interval.ms`（defaultは5分）より長い時間がかかると、Consumerはgroupから強制的にevictされ、rebalanceが発生します。複数のConsumerが同時に低速化すると、これが繰り返しgroupを中断させる「rebalance storm」へと連鎖する可能性があります。

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

`max.poll.records`を下げると、1回の`poll()`呼び出しで返されるrecord数が減り、poll間の処理時間が短縮されます。`max.poll.interval.ms`を上げると、低速な処理でevictされるまでの余裕が増えます。より堅牢な修正方法はアーキテクチャによるものです。重い処理をpoll loopから完全に切り離して別のworker thread poolに移し、pollではworkの取得と引き渡しだけを行います。

### 手動offset commit

at-least-once処理が重要なpipeline（注文処理、支払い）では、auto-commit（`enable.auto.commit=true`）によって、対応するrecordの処理が実際に完了する前にoffsetがcommitされる可能性があります。その間にConsumerがcrashすると、そのrecordは「commit済み」であっても、pipelineの観点では実質的に失われます。

```properties
enable.auto.commit=false
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);          // business logic
    }
    consumer.commitSync();        // commit only after processing succeeds
}
```

### Static group membership

Kubernetes上のConsumer Podは、rolling deploy、OOMKilled restart、node replacementなどで頻繁にrestartします。defaultでは、Consumerがgroupから離脱して再参加すると完全なrebalanceが発生します。そのため、短時間のrestartが頻繁に起きると、group全体で不要な処理停止が繰り返されます。`group.instance.id`を設定するとstatic membershipが有効になります。Consumerが`session.timeout.ms`以内に再接続した場合、rebalanceを一切行わず、以前のPartition assignmentをそのまま再開します。

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id`はPodごとに一意である必要があります。通常はStatefulSetのPod名から取得するか、downward API経由でinjectします。

## 4. セキュリティ

### mTLS（transport encryption + mutual authentication）

Kafka clusterがdeployされると、Strimziは独自のcluster CAを自動的にprovisionおよびrotateします。listenerのtypeを`tls`に設定するとclient-Broker間のtrafficがencryptされ、`KafkaUser`に`tls` authentication typeを指定すると、Strimziはそのcluster CAで署名したclient certificateを発行します。

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

### SASL/SCRAM

client certificateの配布とrotateが現実的でない環境（legacy app、third-party tool）では、username/passwordベースのSASL/SCRAM（`scram-sha-512`）が有力な代替手段です。listenerのauthentication typeを`scram-sha-512`に設定し、対応する`KafkaUser`にも同じ`authentication.type`を指定します。Strimziがcredentialを自動的にSecretへ生成します。

### 宣言的ACL管理

上記の`KafkaUser`の例で示したように、`authorization.type: simple`と`acls` listを使うと、Brokerに対して手作業で`kafka-acls.sh`を実行するのではなく、GitOpsを通じてACLをcodeとして管理できます。新しいserviceをTopicへonboardするには、新しい`KafkaUser` resourceをcommitするだけです。

### Network policy

Strimzi listenerは`networkPolicyPeers`をサポートし、特定のlistener port（例: 9092/9093/9094）に到達できるPodを制限します。

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    networkPolicyPeers:
      - podSelector:
          matchLabels:
            app: order-service
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kafka-clients
```

Strimziはこれを内部で標準のKubernetes `NetworkPolicy`に変換するため、指定したselectorに一致するPodのみがlistener portに到達できます。

### 保存時の暗号化

EBS volume encryptionは、EBS CSI driverが自動的に適用するものではありません。次のいずれかで明示的にopt inする必要があります。

- account/regionレベルの**「EBS encryption by default」**設定を有効にし、その後に作成されるすべてのvolumeを自動的にencryptする。
- `StorageClass`に`encrypted: "true"`（および必要に応じて`kmsKeyId`）を設定する。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx
```

Kafka clusterにはコンプライアンス上重要なデータが含まれることが多いため、Broker PVCには明示的にencryptした`StorageClass`を、後から考慮する事項ではなくdefaultとして扱ってください。

## 5. コスト最適化

### instance typeの適正サイジング

ほとんどのKafkaワークロードは、CPUよりも**メモリ、特にOS page cache**の影響をはるかに強く受けます。Kafkaは、ほとんどのreadをpage cacheから提供するよう設計されています。そのため、Consumerが最近のデータをreadする一般的なケースでは、Broker heap（通常4～8GBで十分）の後に残るRAMがthroughputを直接左右します。このため、memory-optimized instance（たとえば`r6g`/`r7g` Graviton family）は、compute-optimized instanceよりも優れたprice/performanceを実現することがよくあります。

### Tiered storage

KIP-405で定義されるTiered storageは、古いログセグメントをlocal diskからS3などのremote storageへoffloadし、各Brokerに必要なlocal EBS capacityを削減します。Apache Kafka 3.6でearly accessとして導入され、**Kafka 3.9で本番利用可能（GA）**になりましたが、defaultでは有効化されていません。明示的に有効にする必要があるopt-in featureです（`remote.log.storage.system.enable=true`）。Strimziでこれに依存する前に、そのStrimzi releaseのTiered storageに関するsupportおよびmaturityの注記を確認し、まず非本番clusterで徹底的に検証してください。

### log retentionのチューニング

過剰に保持したデータはEBSの直接的かつ継続的なコストになるため、defaultをそのままにせず、実際のbusiness requirementに基づいてTopicごとに`retention.ms`/`retention.bytes`を設定してください。keyごとに最新のvalueだけが必要なTopic（state snapshot、cacheのようなデータ）では、storageが無制限に増加しないよう`cleanup.policy=compact`を使用してください。

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Spot instanceの使用

dev/staging環境またはcriticalityが低いStrimzi clusterでは、Broker node poolをSpot instanceで実行することで、コストを大幅に削減できます。ただし、**KRaft controller node poolはOn-Demandに維持する必要があります**。controller quorumの過半数を失うと、cluster全体のmetadata管理が停止します。これはSpotによる節約のために負うべきリスクではありません。Pod topology spread constraintを使用してBroker node poolをAZ/nodeにまたがって分散し、Spot reclamation eventで同じPartitionの複数のreplicaが同時に失われないようにしてください。

## 6. 本番稼働チェックリスト

この詳細解説のパート1から8の重要項目を、単一の本番前チェックリストにまとめます。

- [ ] **アーキテクチャ**: KRaft modeで実行され、controllerとBrokerのnode poolが分離されている（パート1、2）
- [ ] **Replication**: 本番Topicで`replication.factor=3`および`min.insync.replicas=2`を使用し、単一のBroker障害に耐えられる（パート1）
- [ ] **Partition設計**: Partition数が過剰に分割されず、想定される最大Consumer並列性に合わせてサイジングされている（パート8）
- [ ] **Strimzi version pinning**: OperatorおよびKafka versionが明示的にpinされ、auto-upgradeでdriftしないようになっている（パート2）
- [ ] **Storage**: Brokerの`StorageClass`がencryption（`encrypted: "true"`）付きのgp3（またはio2）を使用している（パート3、8）
- [ ] **PodDisruptionBudget**: rolling restartおよびnode replacement中にquorum/majorityの可用性をPDBが保証する（パート3）
- [ ] **Rolling upgrade rehearsal**: rolling upgrade手順をstagingで実際に実施済みである（パート3）
- [ ] **Schema compatibility**: schema registryのcompatibility mode（BACKWARD/FORWARD/FULL）がTopicの要件に応じて意図的に設定されている（パート4）
- [ ] **DR/replication**: Kafka Connect/MirrorMaker2ベースのdisaster recoveryまたはcross-region replicationが文書化され、failoverがテスト済みである（パート5）
- [ ] **MSK vs. self-managedの判断**: managed MSKとStrimzi self-managedの選択について、運用およびコストの根拠とともに文書化されている（パート6）
- [ ] **Monitoring/alerting**: Broker metricsおよびConsumer lag用のdashboardとalert ruleが存在する（パート7）
- [ ] **Autoscaling**: ConsumerワークロードがKEDAまたは同等のmechanismを介してlagに応じてscaleする（パート7）
- [ ] **Producer/Consumer config review**: `acks`、`enable.idempotence`、offset commit strategy、static group membershipがすべてワークロードの要件に照らしてレビューされている（パート8）
- [ ] **Security**: mTLSまたはSASL/SCRAM、`KafkaUser`ベースのACL、listenerの`NetworkPolicy`がすべて整備されている（パート8）
- [ ] **Cost review**: instance type、retention policy、Spotの使用状況が定期的に再評価されている（パート8）
- [ ] **Load testing**: BrokerおよびConsumerのscaleが、想定ピークthroughputで実際にload testされている

このチェックリストを満たすことは、clusterがEKS上で本番稼働する準備ができていると判断するための妥当な基準です。

---

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[Topicクイズ](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)に挑戦してください。
