# Kafka Fundamentals Quiz

このクイズでは、Kafka の broker/topic/partition モデル、順序保証、consumer group の rebalance、KRaft、replication/durability 設定についての理解を確認します。

## 選択問題

1. Kafka が message の順序を保証する範囲はどれですか？
   - A) cluster 全体
   - B) topic 全体（すべての partition にまたがる）
   - C) 同じ partition 内のみ
   - D) 同じ consumer group 内のみ

<details>

<summary>解答を表示</summary>

**解答: C) 同じ partition 内のみ**

**説明:**
Kafka は単一の partition 内でのみ message の順序を保証します。topic に複数の partition がある場合、producer が送信した順序に関係なく、異なる partition に保存された message 間の相対的な順序は保証されません。特定の entity の event（たとえば、ある order ID に関する event）の順序を維持するには、その entity を識別する key を使用し、すべての event が同じ partition に route されるようにする必要があります。
</details>

2. ISR (In-Sync Replicas) は何を指しますか？
   - A) cluster に登録されているすべての broker の集合
   - B) leader に十分追従している replica の集合
   - C) leader になる資格のない replica の集合
   - D) consumer group に属する consumer の集合

<details>

<summary>解答を表示</summary>

**解答: B) leader に十分追従している replica の集合**

**説明:**
ISR (In-Sync Replicas) は、partition の leader replica とデータが十分に同期されている follower replica（および leader 自身）の集合です。write が `acks=all` で送信された場合、ISR 内のすべての replica が message を受信して初めて成功とみなされます。leader から大きく遅れた follower は ISR から削除され、これは障害時のデータ整合性を守るための safeguard として機能します。
</details>

3. Kafka consumer の `enable.auto.commit` 設定の default 値は何ですか？
   - A) `false`
   - B) `true`
   - C) broker configuration に依存する
   - D) この設定は Kafka 3.x 以降で削除された

<details>

<summary>解答を表示</summary>

**解答: B) `true`**

**説明:**
`enable.auto.commit` の default 値は `true` です。この場合、consumer は `auto.commit.interval.ms` ごと（default では 5 秒ごと）に offset を自動 commit します。これは便利ですが、message processing が実際に完了する前に offset が commit される可能性があり、障害時に message loss のリスクがあります。processing の完了後にのみ commit するには、`enable.auto.commit=false` を設定し、`commitSync()` または `commitAsync()` を明示的に呼び出します。
</details>

4. 次のうち、consumer group rebalance を trigger しないものはどれですか？
   - A) 新しい consumer が group に参加する
   - B) consumer が `session.timeout.ms` 以内に heartbeat を送信できない
   - C) topic 上の partition 数が変わる
   - D) producer が `acks=all` で message を送信する

<details>

<summary>解答を表示</summary>

**解答: D) producer が `acks=all` で message を送信する**

**説明:**
rebalance は、consumer group membership が変わった場合、または subscribed topic の partition layout が変わった場合に発生します。consumer の参加または離脱、heartbeat timeout、`max.poll.interval.ms` の超過、partition 数の変更が典型的な trigger です。一方で `acks` は、producer が write の完了をどのように確認するかを決定する producer 側の設定であり、consumer group の partition assignment や rebalance とは関係ありません。
</details>

5. KRaft (Kafka Raft metadata mode) が production-ready (GA) になったのは、どの Kafka version からですか？
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>解答を表示</summary>

**解答: B) Kafka 3.3**

**説明:**
KRaft は Kafka 2.8 で early-access preview として初めて導入されましたが、production-ready (General Availability) になったのは Kafka 3.3 からです。その後の minor release で安定化が続き、Kafka 4.0 では ZooKeeper mode が完全に削除され、KRaft が唯一サポートされる metadata management mechanism になりました。
</details>

6. ZooKeeper mode が完全に削除され、KRaft が唯一の metadata management mechanism になったのは、どの Kafka version ですか？
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>解答を表示</summary>

**解答: D) Kafka 4.0**

**説明:**
Kafka 4.0（2025 年 3 月 release）では、ZooKeeper ベースの metadata management mode が完全に削除されました。この version 以降、新しい cluster は KRaft mode でのみ bootstrap でき、既存の ZooKeeper ベースの cluster は 4.0 へ upgrade する前に Kafka 3.x 上で KRaft への migration を完了する必要があります。
</details>

7. topic が `replication.factor=3` と `min.insync.replicas=2` で設定され、producer が `acks=all` を使用している場合、write を受け付け続けながら許容できる同時 broker 障害の最大数はいくつですか？
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>解答を表示</summary>

**解答: B) 1**

**説明:**
replication factor が 3 の場合、各 partition は 3 つの replica に保存されます。`min.insync.replicas=2` は、`acks=all` write が成功するには少なくとも 2 つの replica が ISR に残っている必要があることを意味します。1 台の broker が障害になっても、残り 2 つの replica は ISR に残るため、write は引き続き成功します。しかし 2 台の broker が同時に障害になると、ISR は 1 つだけに縮小し、`min.insync.replicas` を満たせなくなるため、producer は `NotEnoughReplicasException` を受け取ります。
</details>

8. durability が最も低い一方で latency も最も低い producer の `acks` 設定はどれですか？
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>解答を表示</summary>

**解答: A) `acks=0`**

**説明:**
`acks=0` は、producer が broker からの応答を一切待たないことを意味します。message が送信された瞬間に write が成功したとみなします。これは latency と throughput の観点では最速の option ですが、network issue や broker failure が発生した場合、message が実際に保存されたかどうかを知る方法がないため、data loss のリスクが最も高い option です。なお、`acks=all` と `acks=-1` は同じ意味であり、write が成功とみなされる前にすべての ISR replica が acknowledge する必要がある、最も安全な設定です。
</details>

9. KRaft architecture において、cluster metadata の変更（partition leader election、topic creation など）を実際に処理する単一の node は何と呼ばれますか？
   - A) Controller Voter
   - B) Active Controller
   - C) Partition Leader
   - D) Metadata Broker

<details>

<summary>解答を表示</summary>

**解答: B) Active Controller**

**説明:**
KRaft では、複数の controller voter（通常は 3 または 5、Raft quorum のため奇数）が metadata log の replication に参加し、そのうち 1 つが Raft consensus によって Active Controller に elected されます。実際に cluster metadata の変更を処理するのは Active Controller だけです。Active Controller が障害になると、残りの voter から新しい Active Controller が elected されます。
</details>

10. `CooperativeStickyAssignor` を使用する主な目的は何ですか？
    - A) producer が partition key を hash する方法を変更するため
    - B) rebalance 中の partition movement を最小化し、その cost を削減するため
    - C) controller quorum 内の voter 数を動的に調整するため
    - D) ISR に含まれる replica 数を増やすため

<details>

<summary>解答を表示</summary>

**解答: B) rebalance 中の partition movement を最小化し、その cost を削減するため**

**説明:**
従来の eager rebalancing protocol では、rebalance が開始されるたびに、すべての consumer が所有しているすべての partition を手放し、最初から再 assignment される必要があります。`CooperativeStickyAssignor` は、実際に移動が必要な partition だけを再 assignment する cooperative rebalancing protocol を使用し、既存の consumer がすでに所有している partition を保持できるようにします。これにより、rebalance 中に consumption が中断される partition の数が減り、全体的な throughput への影響が緩和されます。
</details>

## 記述問題

11. KRaft mode で cluster metadata が保存される内部 Kafka topic の名前は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `__cluster_metadata`**

**説明:**
KRaft mode では、別個の ZooKeeper ensemble に依存する代わりに、Kafka は cluster metadata（topic/partition 情報、ACL、controller state change history など）を `__cluster_metadata` という名前の internal topic 内の event log として保存します。Controller quorum voter は Raft protocol を介してこの topic を replicate し、broker は最新の metadata に追従するためにこれを subscribe します。この設計により、Kafka は metadata management にも、自身の core storage model である partition log を再利用できます。
</details>

12. network retry によって発生する duplicate message write を防ぐために有効化する producer 設定は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `enable.idempotence`（idempotent producer、`enable.idempotence=true`）**

**説明:**
`enable.idempotence=true` を設定すると、producer は各 message に sequence number と producer ID を付与します。broker はこれを使用して、retry によって発生した duplicate write を検出し破棄します。この設定は、Kafka 内（topic level）で exactly-once write を実現するための基盤であり、`transactional.id` と組み合わせることで、複数の partition または topic にまたがる atomic write へその保証を拡張できます。
</details>

13. 選択した partition key の cardinality（distinct value の数）が低いため、traffic が少数の partition に集中する状況を表す用語は何ですか？

<details>

<summary>解答を表示</summary>

**解答: Hot Partition**

**説明:**
hot partition は、partition key として選択された値に十分な cardinality（distinct value）がない場合、または特定の値が不均衡に頻繁に出現する場合に発生します。たとえば、traffic の大部分が少数の大きな customer ID に集中している場合、それらの key が hash される partition だけが過剰な load を受け、残りは idle のままになります。これは parallel consumer processing の利点を損なうため、key を設計する際には traffic distribution を慎重に確認する必要があります。
</details>

14. `poll()` 呼び出しの間に consumer が message processing に費やせる最大時間を制御し、それを超えると consumer が group を離脱したとみなされて rebalance を trigger する設定は何ですか？

<details>

<summary>解答を表示</summary>

**解答: `max.poll.interval.ms`**

**説明:**
`max.poll.interval.ms` は、連続する `poll()` 呼び出しの間に許可される最大時間（default では 5 分）を指定します。単一の `poll()` から返された record の processing がこれより長くかかると、broker は consumer がもはや alive ではないとみなし、group から削除して rebalance を trigger します。これは `session.timeout.ms` とは別の mechanism です。`session.timeout.ms` は別個の heartbeat thread によって制御されます。processing logic が遅い場合は、この値を増やすか、`max.poll.records` を減らして batch size を小さくする必要があります。
</details>

## ハンズオン問題

15. `events` という名前の topic を、8 partitions、replication factor 3、`min.insync.replicas=2` で作成する `kafka-topics.sh` command を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**説明:**
`--partitions 8` は topic を 8 個の partition に分割し、最大 8 つの consumer が並列に consume できるようにします。`--replication-factor 3` は各 partition を 3 台の broker に copy し、最大 2 台の broker failure にわたって data を保持します。`--config min.insync.replicas=2` は、`acks=all` write が成功するために少なくとも 2 つの replica が ISR に残っていることを強制します。replication factor と組み合わせることで、単一の broker failure が発生しても write を継続できます。
</details>

16. 専用の 3-node KRaft controller quorum（controller role のみ、broker role なし）用の sample `server.properties` configuration を書いてください。node ID 90、91、92 を使用してください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
# server.properties for one dedicated controller node (e.g., node.id=90)
process.roles=controller
node.id=90

controller.quorum.voters=90@kraft-controller-0:9093,91@kraft-controller-1:9093,92@kraft-controller-2:9093

listeners=CONTROLLER://:9093
controller.listener.names=CONTROLLER

log.dirs=/var/lib/kafka/controller-data
```

**説明:**
`process.roles=controller` を設定すると、この node は controller quorum voter としてのみ動作し、broker traffic を処理しません。より大きな cluster では、このように controller role を broker role から分離することで、metadata processing load が data processing load と競合しなくなり、stability が向上します。`controller.quorum.voters` には、controller quorum に参加するすべての node を `node.id@host:port` 形式で列挙する必要があります。また奇数個（3 または 5）を使用すると、cluster が明確な Raft quorum majority を計算できます。
</details>

17. exactly-once write を実現するために、`acks=all`、idempotent write、transactional ID を組み合わせた producer configuration（Java properties format）を書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all
enable.idempotence=true
transactional.id=order-producer-1
max.in.flight.requests.per.connection=5
retries=2147483647
```

**説明:**
`acks=all` は、write が成功とみなされる前にすべての ISR replica が message を受信することを要求し、`enable.idempotence=true` は retry によって発生する duplicate write を排除します。`transactional.id` を設定すると producer は transactional producer になり、`initTransactions()`、`beginTransaction()`、`commitTransaction()` API を使用して複数の partition にまたがって atomic に write できます。`enable.idempotence=true` が設定されていれば ordering と duplicate は自動的に管理されるため、`retries` を非常に高く設定しても安全です。ordering guarantee を壊さないために、`max.in.flight.requests.per.connection` は 5 以下に保つ必要があります。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [次のクイズ: Strimzi Operator](./02-strimzi-operator-quiz.md)
