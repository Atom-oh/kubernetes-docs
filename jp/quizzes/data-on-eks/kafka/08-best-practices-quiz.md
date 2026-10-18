# Part 8: ベストプラクティスクイズ

partition、client、security、capacity、復旧の設計を実際の条件に照らして確認します。

## 1. 一般的なconsumer groupのpartition数を決めるとき、何を考慮すべきですか？

<details>
<summary>解答を表示</summary>

memberの並列度、partitionあたりのthroughput、keyの偏り、recordのサイズ、replicaの配置、復旧を測定・検討します。同じgroupでは、1つのpartitionを割り当てられるのは1つのgroup memberです。share groupやapplication内部の並列化は別の仕組みです。

</details>

## 2. 過去のpartition数の経験則を、現在も共通の上限として扱えますか？

<details>
<summary>解答を表示</summary>

いいえ。上限はversion、broker/controller、replica数、workloadに依存します。論理partition数とbrokerごとのreplica配置を区別し、通常時と障害時の両方をテストしてください。

</details>

## 3. PartitionCountを含む行を数えれば、partitionの総数が分かりますか？

<details>
<summary>解答を表示</summary>

いいえ。それで数えられるのはtopicのsummary行です。partition_summary.pyのようにPartition:行を読み、論理partition数とreplica配置を分けて数えます。検索結果が空の場合、表示権限、filter条件も確認してください。

</details>

## 4. key付きtopicのpartition数を増やすと、すべてのkeyが必ず別partitionへ移動しますか？

<details>
<summary>解答を表示</summary>

すべてのkeyが移動するわけではありませんが、一部は別partitionに再割り当てされる可能性があります。既存recordは元の場所に残るため、key順序、state、co-partitioned joinの前提に影響します。serializer、partitioner、topologyを確認してください。

</details>

## 5. acksやretriesを明示すると、常にdefaultのidempotenceが無効になりますか？

<details>
<summary>解答を表示</summary>

いいえ。問題になるのは互換性のない設定です。enable.idempotence=trueを明示する場合は、acks、retries、max.in.flightも互換性のある値にします。矛盾する設定はconfiguration errorになります。

</details>

## 6. idempotenceまたはtransactional.idだけで、end-to-end exactly-onceを実現できますか？

<details>
<summary>解答を表示</summary>

いいえ。producerのretryとapplicationによる再送、外部への副作用は別の問題です。Kafka transactionでは入力offsetと出力を原子的にcommitし、fencing/read_committedと正しいlifecycleを扱う必要があります。外部systemには独自の対策も必要です。

</details>

## 7. RF=3、acks=all、min.insync.replicas=2のとき、ISRが1まで減るとどうなりますか？

<details>
<summary>解答を表示</summary>

writeは拒否されます。acks=allは現在のISRを待ち、最小ISRはtopicまたはbrokerで設定します。replicationがすでに低下した状態で障害が起きた場合に、writeの継続やデータ損失ゼロを無条件に保証するものではありません。

</details>

## 8. max.poll.interval.msとheartbeat/session設定では、何を区別して考える必要がありますか？

<details>
<summary>解答を表示</summary>

poll間の実際の処理時間を確認します。static memberの再割り当てはsession expiryまで待つ場合があります。classic clientのheartbeat/session設定と、consumer protocolでbrokerが制御する設定を区別してください。

</details>

## 9. static membershipを使えば、restart時のrebalanceを必ず防げますか？

<details>
<summary>解答を表示</summary>

いいえ。安定した一意のidentity、再接続までの時間、topology、subscription、group membershipが関係します。同一IDで複数のmemberが同時に動くとfencingが発生することがあり、sessionを長くすると実際の障害からの復旧も遅れます。

</details>

## 10. デフォルトのStrimziでKafkaUserのmTLS client certificateに署名するCAはどれですか？

<details>
<summary>解答を表示</summary>

clients CAです。cluster CAはbrokerおよび内部componentのcertificateに使われます。client credentialとbrokerを信頼するためのCA chainを区別してください。

</details>

## 11. cardinalityを高くするかrandom saltを使えば、keyの偏りはそれだけで安全に解消できますか？

<details>
<summary>解答を表示</summary>

いいえ。負荷の高いkeyが支配的なら、依然としてtrafficが偏ることがあります。saltingは順序、join、compactionで使うidentityを変えるため、要件で許容されることを先に確認し、分割したデータを再結合する方法も計画してください。

</details>

## 12. 処理中にexceptionが起きた後、commitをせずにpollを続けても安全ですか？

<details>
<summary>解答を表示</summary>

いいえ。fetch positionはすでに先へ進んでいる場合があります。適切に停止・復旧するかseekし、永続的な処理が完了してからcommitしてください。再配信による重複と、外部への副作用を冪等に処理する方法も設計します。

</details>

## 13. Kafkaのcapacityはmemory量や固定のheap sizeだけから決められますか？

<details>
<summary>解答を表示</summary>

いいえ。page cache、TLS/compressionのCPU負荷、networking、IOPS/throughput、cgroupのmemory、復旧動作を測定してください。codecやinstanceによる費用上の利点は、dataとworkloadに依存します。

</details>

## 14. 1つのnetworkPolicyPeers entry内でnamespaceSelectorとpodSelectorはどう組み合わされますか？

<details>
<summary>解答を表示</summary>

同じpeer内ではAND、別々のpeer entry間ではORです。NetworkPolicyは加算的に適用されるため、CNIでのenforcementとegressも確認してください。このentryだけでは、別のpolicyが許可するtrafficを拒否できません。

</details>

## 15. StorageClassの暗号化、Auto Mode、既存volumeについて説明してください。

<details>
<summary>解答を表示</summary>

使用するprovisionerに対してencrypted: "true"と実際のKMS権限を設定し、EBS側でも確認します。Auto Modeのnode/ephemeral diskだけを根拠に、すべての動的PVCが暗号化されると判断してはいけません。StorageClassやaccount defaultの変更で既存volumeが遡って暗号化されることもありません。

</details>

## 16. producerのtuning profileを書き、batch.sizeと最小ISRの役割を説明してください。

<details>
<summary>解答を表示</summary>

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

batch.sizeはpartitionごとのbatch化と割り当てを制御し、record/requestの厳密な上限ではありません。min.insync.replicasはtopicまたはbrokerで設定します。codecとlingerの選択を測定し、send failureとdelivery timeoutを処理してください。

</details>

## 17. 既存のSCRAM userを維持したまま、別のmTLS KafkaUserを作成してください。

<details>
<summary>解答を表示</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
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
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

さらに、tls:trueとauthentication.type:tlsを使うlistenerが必要です。tlsというexposure typeはありません。clients-CA credentialとbroker trustを配布・rotationし、実際に許可される操作と拒否される操作を確認してください。

</details>

## 18. 環境変数由来のstatic member IDをmanual commitとどう組み合わせますか？

<details>
<summary>解答を表示</summary>

Java Propertiesは${POD_NAME}を展開しません。consumerを作成する前に、一意で安定したIDを解決し、setStaticIdentityへ渡してください。enable.auto.commit=falseとprocessOneBatchを使い、failureを握りつぶしてpollを続けないでください。retention/recoveryと重複処理への備えも必要です。

</details>

---

[学習教材に戻る](../../../data-on-eks/kafka/08-best-practices.md) | [次のクイズ](./09-kafka-benchmark-quiz.md)
