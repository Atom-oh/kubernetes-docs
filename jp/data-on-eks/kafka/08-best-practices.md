# Part 8: ベストプラクティス

> **サポート対象バージョン**: Apache Kafka 3.9, Strimzi 0.45+\
> **最終更新**: July 9, 2026

このディープダイブ全体で、Kafka の基礎、Strimzi の運用、schema registry、Kafka Connect/MirrorMaker、MSK 統合、監視について取り上げました。この最後のドキュメントでは、本番対応のベストプラクティスをカテゴリ別に整理し、前の 7 つの Part から重要項目を 1 つの go-live checklist にまとめます。

## 1. Partition 設計

### partition 数のサイジング

topic の **想定される最大 consumer 並列度** から始めます。単一の partition は、特定の consumer group 内では同時に 1 つの consumer instance からしか消費できないため、consumer group をどこまでスケールさせる想定かを決め、少なくともその数の partition を用意します。ピーク時に 20 個の consumer instance までスケールアウトする予定なら、少なくとも 20 個の partition が必要です。

過剰な partition 分割には実際のコストがあり、避けるべきです。

- **より多くの open file handle**: 各 partition は複数の log segment file（`.log`, `.index`, `.timeindex`）を開いたまま保持するため、broker あたりの open file descriptor 数は partition 数に比例して増えます。
- **より大きな memory pressure**: producer/consumer の batch buffer と broker 上の replication thread ごとの buffer は、partition 数に応じて増加します。
- **より遅い rebalance と failover**: broker 障害時に controller が行う必要のある leader election 作業量は partition 数に応じて増え、consumer group の rebalance も長くなります。

Confluent の古典的な経験則では、**broker あたり約 4,000 partition、cluster あたり 200,000 partition** が緩やかな上限でした。これは ZooKeeper ベースの controller が metadata のボトルネックだった時代のガイダンスです。KRaft ベースの cluster（Kafka 3.x+ controller quorum）は、はるかに高速な controller metadata path により、より多くの partition 数を扱えますが、原則は変わりません。可能だからという理由だけで過剰に partition を増やさず、実際の workload に対する上限を実負荷テストで検証してください。

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### partition key の選択

hot partition を避けるため、**cardinality が高く、均等に分布する** key を選びます。default partitioner は key を murmur2 で hash し、それを partition 数で modulo するため、cardinality の低い key（例: 少数の異なる値しかない `country` や `status`）では、支配的な traffic 値に対応する少数の partition が過負荷になり、他の partition は idle のままになります。十分に cardinality の高い field（例: `user_id`）を優先するか、cardinality の低い key に salt（random または timestamp 由来の suffix を追加）して、より均等に分散させます。

### partition 数の変更を慎重に扱う

**keyed** topic の partition 数を増やすと、key から partition への mapping が壊れます。`partition_count` が変わるとすぐに `hash(key) % partition_count` が変わるため、同じ key が変更前とは別の partition に配置される可能性があります。これにより、次の 2 つの具体的な問題が発生します。

- **ordering の破綻**: Kafka は partition 内でのみ ordering を保証するため、同じ key の message が複数の partition に分割されると、consumer は key-level の ordering に依存できなくなります。
- **co-partitioning の破綻**: Kafka Streams（および類似の仕組み）での join では、join される topic が同じ partition 数と partitioning scheme を共有している必要があります。join の片側だけで partition を変更すると、その join が壊れます。

capacity planning の段階で headroom を含めて partition 数を決めてください。本番 topic がすでに key-based ordering や join に依存している場合は、既存 topic の partition を増やすよりも、新しい topic へ移行することを優先してください。

## 2. Producer チューニング

| Setting | Recommended value | Purpose |
|---------|--------------------|---------|
| `acks` | `all`（durability-critical topic 向け） | すべての in-sync replica（ISR）からの acknowledgment を待つことで、broker 障害による data loss を防ぐ |
| `min.insync.replicas`（topic/broker setting） | `2`（replication.factor=3 の場合） | `acks=all` と組み合わせることで、write が成功する前に少なくとも 2 つの replica に到達することを要求する — producer client property ではなく、topic（`kafka-configs.sh --entity-type topics`）または broker default に設定する |
| `linger.ms` | `5`–`20` | わずかな latency と引き換えに batch を大きくし、throughput を高める |
| `batch.size` | `32768`–`65536`（32–64KB） | request あたりの throughput を増やすため、batch あたりの max bytes を引き上げる |
| `enable.idempotence` | `true` | producer retry によって発生する duplicate write を防ぐ |
| `compression.type` | `lz4` または `zstd` | network と storage のコストを削減する |

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

`enable.idempotence=true` は、明示的に `acks` や `retries` を互換性のない方法で override しない限り、**Kafka 3.0 以降の default** です。producer に一意の producer ID と partition ごとの sequence number を割り当てることで、broker は一時的な network error による retry を透過的に deduplicate できます。これは完全な exactly-once semantics とは別物です。idempotence は producer-to-broker hop 上の duplicate のみを取り除き、真の end-to-end exactly-once には transactional API（`transactional.id`）も必要です。

`lz4` は、ほとんどの workload において CPU overhead と compression ratio のバランスが良好です。`zstd` はより高い圧縮率を提供し、JSON/text-heavy payload に有用ですが、CPU 使用量はやや高くなります。`gzip` はよく圧縮できますが CPU 負荷が高いため、一般的に high-throughput producer には推奨されません。

## 3. Consumer チューニング

### rebalance storm の回避

処理に `max.poll.interval.ms`（default 5 分）より長くかかると、consumer は group から強制的に evict され、rebalance が trigger されます。複数の consumer が同時に遅くなると、これが繰り返し group disruption を引き起こす「rebalance storm」に連鎖する可能性があります。

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

`max.poll.records` を下げると、1 回の `poll()` call から返される record 数が減り、poll 間の processing window が短くなります。`max.poll.interval.ms` を上げると、遅い処理に対して evict されるまでの headroom が増えます。より堅牢な修正は architecture 上の対応です。heavy processing を poll loop から完全に切り離して別の worker thread pool に移し、poll は fetch と work の hand off のみに使います。

### 手動 offset commit

at-least-once processing が重要な pipeline（order processing、payments）では、auto-commit（`enable.auto.commit=true`）により、対応する record の処理が実際には完了する前に offset が commit される可能性があります。その間に consumer が crash すると、その record は「committed」ではあっても、pipeline の観点では実質的に失われます。

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

### static group membership

Kubernetes 上の consumer pods は、rolling deploy、OOMKilled restart、node replacement などで頻繁に restart します。default では、consumer が group を離脱して再参加すると full rebalance が trigger されるため、短時間の restart が頻繁に発生すると、group 全体で不要な processing pause が繰り返されます。`group.instance.id` を設定すると static membership が有効になります。consumer が `session.timeout.ms` 内に reconnect すれば、以前の partition assignment をそのまま再開し、rebalance は一切発生しません。

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` は pod ごとに一意である必要があります。通常は StatefulSet pod name から取得するか、downward API 経由で注入します。

## 4. Security

### mTLS（transport encryption + mutual authentication）

Kafka cluster が deploy されると、Strimzi は独自の cluster CA を自動的に provision して rotate します。listener の type を `tls` に設定すると client-broker traffic が暗号化され、`KafkaUser` に `tls` authentication type を指定すると、Strimzi はその cluster CA によって署名された client certificate を発行します。

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

client certificate の配布と rotate が現実的でない環境（legacy apps、third-party tools）では、username/password ベースの SASL/SCRAM（`scram-sha-512`）が堅実な代替です。listener の authentication type を `scram-sha-512` に設定し、対応する `KafkaUser` に同じ `authentication.type` を指定します。Strimzi は credentials を Secret に自動生成します。

### Declarative ACL management

上記の `KafkaUser` example で示したように、`authorization.type: simple` と `acls` list を使うと、broker に対して手動で `kafka-acls.sh` を実行する代わりに、GitOps を通じて ACL を code として管理できます。新しい service を topic に onboarding する作業は、新しい `KafkaUser` resource を commit するだけです。

### Network policy

Strimzi listener は `networkPolicyPeers` をサポートしており、特定の listener port（例: 9092/9093/9094）に到達できる pod を制限できます。

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

Strimzi はこれを背後で標準の Kubernetes `NetworkPolicy` に変換するため、指定された selector に一致する pod のみが listener port に到達できます。

### Encryption at rest

EBS volume encryption は、EBS CSI driver が自動的に適用するものではありません。次のいずれかの方法で明示的に opt in する必要があります。

- account/region-level の **"EBS encryption by default"** setting を有効にし、以後作成されるすべての volume が自動的に暗号化されるようにする。
- `StorageClass` に `encrypted: "true"`（および必要に応じて `kmsKeyId`）を設定する。

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

Kafka cluster は compliance-sensitive data を扱うことが多いため、broker PVC 用の明示的に暗号化された `StorageClass` を後付けではなく default として扱ってください。

## 5. Cost Optimization

### instance type の right-sizing

ほとんどの Kafka workload は、CPU よりも **memory、特に OS page cache** に対してはるかに敏感です。Kafka はほとんどの read を page cache から提供するように設計されているため、consumer が最近の data を読んでいる一般的なケースでは、broker heap（通常 4〜8GB で十分）を差し引いた残りの RAM が throughput を直接決定します。この理由から、memory-optimized instance（たとえば `r6g`/`r7g` Graviton family）は、compute-optimized instance よりも良い price/performance を提供することがよくあります。

### Tiered storage

KIP-405 で定義された tiered storage は、古い log segment を local disk から S3 などの remote storage に offload し、各 broker が必要とする local EBS capacity を削減します。これは Apache Kafka 3.6 で early access として導入され、**Kafka 3.9 で production-ready（GA）になりました** が、default では有効ではありません。明示的に有効化する必要がある opt-in feature のままです（`remote.log.storage.system.enable=true`）。Strimzi でこれに依存する前に、その Strimzi release の tiered storage に関する support と maturity notes を確認し、まず non-production cluster で十分に検証してください。

### log retention のチューニング

default のままにするのではなく、実際の business requirement に基づいて topic ごとに `retention.ms`/`retention.bytes` を設定してください。EBS 上で data を過剰に保持することは、直接的かつ継続的な cost になります。key ごとに最新値だけが必要な topic（state snapshot、cache-like data）は、storage が無制限に増えないよう `cleanup.policy=compact` を使用するべきです。

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Spot instance の利用

dev/staging 環境や criticality の低い Strimzi cluster では、broker node pool を Spot instance で実行すると cost を大幅に削減できます。ただし、**KRaft controller node pool は On-Demand のままにするべきです**。controller quorum の過半数を失うと、cluster 全体の metadata management が停止します。これは Spot savings のために取る価値のある risk ではありません。Spot reclamation event によって同じ partition の複数 replica が一度に失われないよう、pod topology spread constraint を使って broker node pool を AZ/node に分散してください。

## 6. Go-Live Checklist

このディープダイブの Part 1 から 8 までの重要項目を、単一の pre-production checklist にまとめます。

- [ ] **Architecture**: KRaft mode で稼働し、controller と broker node pool が分離されている（Parts 1, 2）
- [ ] **Replication**: production topic が `replication.factor=3` と `min.insync.replicas=2` を使用し、単一 broker 障害に耐えられる（Part 1）
- [ ] **Partition design**: partition 数が想定される最大 consumer 並列度に合わせて sizing されており、過剰に分割されていない（Part 8）
- [ ] **Strimzi version pinning**: Operator と Kafka version が明示的に pin され、auto-upgrade で drift しない（Part 2）
- [ ] **Storage**: broker `StorageClass` が encryption（`encrypted: "true"`）付きの gp3（または io2）を使用している（Parts 3, 8）
- [ ] **PodDisruptionBudget**: PDB により rolling restart と node replacement 中の quorum/majority availability が保証されている（Part 3）
- [ ] **Rolling upgrade rehearsal**: rolling upgrade procedure が staging で実際に演習済みである（Part 3）
- [ ] **Schema compatibility**: schema registry compatibility mode（BACKWARD/FORWARD/FULL）が topic の needs ごとに意図的に設定されている（Part 4）
- [ ] **DR/replication**: Kafka Connect/MirrorMaker2 ベースの disaster recovery または cross-region replication が documented され、failover が tested 済みである（Part 5）
- [ ] **MSK vs. self-managed decision**: managed MSK と Strimzi self-managed の選択が、運用面および cost 面の rationale とともに documented されている（Part 6）
- [ ] **Monitoring/alerting**: broker metrics と consumer lag の dashboard と alert rule が存在する（Part 7）
- [ ] **Autoscaling**: consumer workload が KEDA または同等の mechanism により lag に基づいて scale する（Part 7）
- [ ] **Producer/consumer config review**: `acks`、`enable.idempotence`、offset commit strategy、static group membership がすべて workload needs に照らして review 済みである（Part 8）
- [ ] **Security**: mTLS または SASL/SCRAM、`KafkaUser` ベースの ACL、listener `NetworkPolicy` がすべて整備されている（Part 8）
- [ ] **Cost review**: instance type、retention policy、Spot usage が定期的に再評価されている（Part 8）
- [ ] **Load testing**: broker と consumer の scale が想定 peak throughput で実際に load-tested 済みである

この checklist を満たすことは、その cluster が EKS 上の本番環境で稼働する準備ができていると言うための妥当な基準です。

---

[メインページに戻る](./)

## Quiz

この章で学んだ内容を確認するには、[Topic Quiz](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md) に挑戦してください。
