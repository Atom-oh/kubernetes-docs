# Part 8: Best Practices Quiz

このクイズでは、Kafka ディープダイブシリーズ全体にわたるベストプラクティス（partition 設計、producer/consumer のチューニング、セキュリティ（mTLS/SASL）、コスト最適化）についての理解を確認します。

## Multiple Choice Questions

1. topic の partition 数をサイジングするとき、最初に考慮すべきことは何ですか？
   - A) cluster 内の broker の総数
   - B) consumer group の最大想定並列度
   - C) producer instance の数
   - D) 利用可能な EBS volume サイズ

<details>

<summary>解答を表示</summary>

**解答: B) consumer group の最大想定並列度**

**説明:**
単一の partition は、同じ group 内では一度に 1 つの consumer instance からしか consume できません。そのため、consumer group をどこまでスケールさせる想定かを決め、少なくともその数だけ partition を用意する必要があります。ピーク時に 20 個の consumer instance までスケールする予定なら、少なくとも 20 個の partition が必要です。broker 数や EBS volume サイズは、cluster が指定された partition 数をどれだけ適切にホストできるかに関するキャパシティ上の関心事であり、その数自体を決める主な要因ではありません。
</details>

2. Confluent の古典的な経験則によると、broker あたりの partition 数のおおよそのソフト上限はいくつでしたか？
   - A) 400
   - B) 4,000
   - C) 40,000
   - D) 400,000

<details>

<summary>解答を表示</summary>

**解答: B) 4,000**

**説明:**
Confluent の古典的なガイダンスでは、broker あたり約 4,000 partition、cluster あたり 200,000 partition がソフト上限として示されていました。これは ZooKeeper ベースの controller が metadata のボトルネックだった時代のものです。KRaft ベースの cluster は、はるかに高速な controller metadata path により、より多くの partition を扱えます。しかし「できるからといって過剰に partition を増やさない」という根本原則は今も当てはまり、特定の workload における実際の上限は load testing で確認する必要があります。
</details>

3. 次のうち、topic の過剰な partition 分割による実際のコストではないものはどれですか？
   - A) broker あたりの open file handle が増える
   - B) producer/broker buffer における memory 使用量が増える
   - C) broker 障害時の leader election と rebalance 時間が長くなる
   - D) consumer group の throughput が常に低下する

<details>

<summary>解答を表示</summary>

**解答: D) consumer group の throughput が常に低下する**

**説明:**
過剰な partition 分割は、file handle、memory、障害復旧時間の overhead を増やしますが、throughput を常に低下させるわけではありません。consumer の並列度が追従できるなら、throughput は必ずしも悪化しません。実際、partition 数が少なすぎると、並列に作業できる consumer 数が制限されるため throughput の上限になります。partition 数は並列度と overhead のトレードオフであり、「多いほど常に悪い／良い」という単純な問題ではありません。
</details>

4. keyed topic の partition 数を増やしたとき、最も直接的に壊れる保証は何ですか？
   - A) replication factor
   - B) 特定の key に対する message ordering
   - C) consumer group の offset commit
   - D) broker 間の ISR list

<details>

<summary>解答を表示</summary>

**解答: B) 特定の key に対する message ordering**

**説明:**
default partitioner は `hash(key) % partition_count` を計算するため、partition 数を変更すると、同じ key が対応付けられる partition が変わります。Kafka は単一 partition 内でのみ順序を保証するため、同じ key の message が古い partition と新しい partition に分かれてしまい、consumer は key レベルの順序に依存できなくなります。その結果、Kafka Streams における co-partitioning ベースの join も壊れる可能性があります。
</details>

5. `enable.idempotence` は、明示的に設定しなくても `true` が default になったのは Kafka のどの version からですか？
   - A) Kafka 1.0
   - B) Kafka 2.0
   - C) Kafka 3.0
   - D) Kafka 4.0

<details>

<summary>解答を表示</summary>

**解答: C) Kafka 3.0**

**説明:**
`acks` または `retries` が互換性のない形で明示的に上書きされていない限り、Kafka 3.0 以降では `enable.idempotence=true` が producer の default です。これにより producer に一意の producer ID と partition ごとの sequence number が割り当てられ、broker が retry を自動的に重複排除できるようになります。
</details>

6. producer idempotence は何を防ぎますか？
   - A) consumer group rebalance
   - B) network retry によって broker 上で発生する重複 write
   - C) partition leader 障害
   - D) schema registry compatibility error

<details>

<summary>解答を表示</summary>

**解答: B) network retry によって broker 上で発生する重複 write**

**説明:**
producer が ack を受け取れず同じ record を retry した場合、idempotence がなければ broker がその record を 2 回保存してしまう可能性があります。idempotent producer の PID と sequence number により、broker は重複を検出して破棄できます。なお、これは producer-to-broker hop のみを重複排除するものです。完全な end-to-end exactly-once を実現するには、idempotence に加えて transactional API が必要です。
</details>

7. `replication.factor=3` の topic で `acks=all` と `min.insync.replicas=2` を設定すると、組み合わせとしてどのような効果がありますか？
   - A) write は常に 3 つすべての replica を待つ
   - B) 少なくとも 2 つの replica（leader を含む）が write を保持するまで完了とみなされない
   - C) compression が自動的に有効になる
   - D) partition leader election が無効になる

<details>

<summary>解答を表示</summary>

**解答: B) 少なくとも 2 つの replica（leader を含む）が write を保持するまで完了とみなされない**

**説明:**
`acks=all` は、現在の in-sync replica (ISR) set からの acknowledgment を producer に待たせます。また `min.insync.replicas=2` は、ISR が 2 未満（leader を含む）に縮小した場合に write を即座に拒否します。これらを組み合わせることで、単一 broker 障害が発生しても安全に write を継続できる、標準的な durability 設定になります。
</details>

8. consumer が `max.poll.interval.ms` 内に処理を完了できないと、何が起こりますか？
   - A) partition leader がただちに置き換えられる
   - B) consumer が group から強制退去され、rebalance が発生する
   - C) broker がその topic の compression を自動的に無効にする
   - D) 何も起こらない。consumer は次の poll を待つだけである

<details>

<summary>解答を表示</summary>

**解答: B) consumer が group から強制退去され、rebalance が発生する**

**説明:**
`max.poll.interval.ms` は、consumer が連続する `poll()` call の間に取れる最大時間を制限します。これを超えると broker は consumer を dead とみなし、group から退去させて rebalance を発生させます。複数の consumer が同時に遅くなると、これが「rebalance storm」に連鎖する可能性があります。
</details>

9. static group membership を有効にするために `group.instance.id` を設定する主な目的は何ですか？
   - A) consumer throughput を自動的に増やす
   - B) 短時間の pod restart 中に不要な rebalance を避ける
   - C) producer の compression ratio を改善する
   - D) partition leader election を高速化する

<details>

<summary>解答を表示</summary>

**解答: B) 短時間の pod restart 中に不要な rebalance を避ける**

**説明:**
Kubernetes では、rolling deploy、OOMKilled event などにより consumer pod が頻繁に restart します。`group.instance.id` を設定すると static membership が有効になります。consumer が `session.timeout.ms` 内に再接続する限り、以前の partition assignment を維持したまま再開し、rebalance はまったく発生しません。これにより、短時間の restart が発生するたびに full group rebalance が起きることを防げます。
</details>

10. Strimzi の `KafkaUser` で `authentication.type: tls` を指定した場合、生成される client certificate には誰が署名しますか？
    - A) AWS Certificate Manager
    - B) client 自身が生成した self-signed certificate
    - C) Strimzi が管理する cluster CA
    - D) 別途 deploy された cert-manager Issuer

<details>

<summary>解答を表示</summary>

**解答: C) Strimzi が管理する cluster CA**

**説明:**
Strimzi は Kafka cluster が deploy されると、自身の cluster CA を自動的に provisioning し、schedule に従って certificate を rotate します。`KafkaUser` の `authentication.type` を `tls` に設定すると、Strimzi はその cluster CA によって署名された client certificate を Secret に発行し、mTLS connection で利用できる状態にします。
</details>

## Short Answer Questions

11. 低 cardinality の field（例: `country`）を partition key として直接使用することで発生する問題を表す単一の用語は何ですか？

<details>

<summary>解答を表示</summary>

**解答: Hot partition**

**説明:**
default partitioner は `hash(key) % partition_count` を計算するため、少数の distinct value しか持たない低 cardinality key では、ほとんどの traffic が支配的な値を共有する場合、traffic が少数の partition に集中し、他の partition は idle のままになります。これは、より高い cardinality の key を選ぶか、低 cardinality の key に salting を行って、より均等に分散させることで緩和できます。
</details>

12. at-least-once processing が重要な pipeline では、auto-commit の代わりにどのような offset commit approach（および設定）を使うべきですか？

<details>

<summary>解答を表示</summary>

**解答: `enable.auto.commit=false` を設定し、処理完了後にのみ `consumer.commitSync()`（または `commitAsync()`）を呼び出す manual commit**

**説明:**
Auto-commit は、対応する record の処理が実際には完了する前に offset を commit する可能性があります。そのため、処理中に crash すると、Kafka から見ると「committed」済みであっても、pipeline の観点ではその record が実質的に失われる可能性があります。`enable.auto.commit=false` を設定し、business logic の完了後にのみ commit することで、crash 時には record が再配信・再処理され、at-least-once semantics が維持されます。
</details>

13. ほとんどの Kafka broker workload において CPU より重要な resource は何ですか？またその理由は何ですか？

<details>

<summary>解答を表示</summary>

**解答: Memory — 具体的には OS page cache**

**説明:**
Kafka はほとんどの read を page cache から提供するよう設計されています。そのため、consumer が recent data を読む一般的なケースでは、broker heap の後に残る RAM が read throughput を直接決定します。これが、memory-optimized instance（たとえば `r6g`/`r7g`）が Kafka broker において compute-optimized instance より優れた price/performance を提供することが多い理由です。
</details>

14. どの Strimzi listener field が、broker port に到達できる pod/namespace を制限しますか？

<details>

<summary>解答を表示</summary>

**解答: `networkPolicyPeers`**

**説明:**
Strimzi listener に `networkPolicyPeers` を設定すると、Strimzi は指定された `podSelector`/`namespaceSelector` に一致する pod/namespace から、その listener port への traffic のみを許可する標準の Kubernetes `NetworkPolicy` を生成します。これにより、どの workload が Kafka listener に到達できるかを宣言的に制御できます。
</details>

15. EBS CSI driver を使っているだけで EBS volume encryption は自動的に行われますか？明示的に有効にする 2 つの方法を挙げてください。

<details>

<summary>解答を表示</summary>

**解答: いいえ、自動的には行われません。(1) account/region レベルの「EBS encryption by default」設定を有効にする、または (2) `StorageClass` parameters に `encrypted: "true"`（必要に応じて `kmsKeyId`）を設定する**

**説明:**
EBS CSI driver は、それ自体で encryption を強制しません。暗号化されていない `StorageClass` は暗号化されていない volume を作成します。すべての新規 volume が自動的に暗号化されるよう account/region 全体の「EBS encryption by default」設定を有効にするか、broker PVC に使用する `StorageClass` で `encrypted: "true"` を明示的に設定する必要があります。Kafka cluster は compliance-sensitive data を扱うことが多いため、これを後付けではなく default として扱う方が安全です。
</details>

## Hands-on Questions

16. durability が重要な topic（例: order processing）向けに、`acks`、`min.insync.replicas` の考慮事項、idempotence、compression を含む producer settings を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
# Producer settings (assuming the topic has replication.factor=3, min.insync.replicas=2)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

**説明:**
`acks=all` は ISR 全体からの acknowledgment を待ち、durability を保証します。また topic の `min.insync.replicas=2`（`replication.factor=3` を想定）と組み合わせることで、pipeline は data loss なしで単一 broker 障害に耐えられます。`enable.idempotence=true`（Kafka 3.0+ の default）は retry による重複 write を防ぎ、`compression.type=lz4` はほとんどの workload に対して CPU overhead と compression ratio のバランスが良好です。`linger.ms`/`batch.size` は、少しの latency と引き換えに、より大きく効率的な batch を実現します。
</details>

17. `orders` topic への read/write access と `order-service-group` consumer group への read access が必要な `order-service` という application 向けに、TLS authentication を使用する `KafkaUser` resource を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
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

**説明:**
`authentication.type: tls` を設定すると、Strimzi は cluster CA によって署名された client certificate を Secret に自動的に発行します。`authorization.type: simple` と `acls` list により、`orders` topic に対する Read/Write/Describe と、`order-service-group` consumer group に対する Read が宣言的に付与されます。`strimzi.io/cluster` label は、この `KafkaUser` がどの `Kafka` cluster に属するかを Strimzi Operator に伝えます。
</details>

18. 短時間の pod restart が rebalance を引き起こさず、offset が処理完了後にのみ commit されるように consumer settings を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
heartbeat.interval.ms=15000
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
    consumer.commitSync();
}
```

**説明:**
`group.instance.id`（pod name などから一意に設定）は static group membership を有効にするため、`session.timeout.ms` 内に再接続する限り、consumer は rebalance なしで既存の partition assignment を維持します。`enable.auto.commit=false` と、処理完了後にのみ呼び出される `commitSync()` を組み合わせることで、完全に処理された record の offset だけが commit され、at-least-once semantics が維持されます。`max.poll.records`/`max.poll.interval.ms` は、実際の batch あたり処理時間に合わせて調整され、不要な rebalance をさらに回避します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/08-best-practices.md) | [Kafka ディープダイブホームに戻る](../../../data-on-eks/kafka/README.md)
