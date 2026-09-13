# Kafkaの基礎クイズ

> **最終更新**: September 12, 2026、Kafka 4.3.1。

このクイズはKafkaのブローカー/トピック/パーティションモデル、順序保証、コンシューマーグループのリバランス、KRaft、レプリケーション/耐久性設定の理解を確認します。

## 選択問題

1. Kafkaはどの範囲でメッセージ順序を保証しますか？
   - A) クラスター全体
   - B) トピック全体（全パーティションにまたがる）
   - C) 同じパーティション内のみ
   - D) 同じコンシューマーグループ内のみ

<details>

<summary>解答を表示</summary>

**正解: C) 同じパーティション内のみ**

**解説:**
保証するのはパーティションログの順序です。同一キーのルーティングには一貫したシリアライズ、パーティショナー、パーティション数が必要で、サイズやクライアントの変更で対応が変わる場合があります。業務イベント時刻やアプリケーションの並列処理には別の順序契約が必要です。
</details>

2. ISR（In-Sync Replicas）は何を指しますか？
   - A) クラスターに登録された全ブローカーの集合
   - B) リーダーに十分追いついているレプリカの集合
   - C) リーダーになる資格がないレプリカの集合
   - D) コンシューマーグループに属するコンシューマーの集合

<details>

<summary>解答を表示</summary>

**正解: B) リーダーに十分追いついているレプリカの集合**

**解説:**
ISRはリーダーを含む十分に同期したレプリカです。acks=allは現在の全ISRを待ち、min.insync.replicasはその最小数を制約します。確認応答は各レコードのfsyncと同義ではありません。
</details>

3. Kafka 4.3 Java KafkaConsumerのenable.auto.commitのデフォルト値は何ですか？
   - A) `false`
   - B) `true`
   - C) ブローカー設定に依存する
   - D) Kafka 3.xから設定が削除された

<details>

<summary>解答を表示</summary>

**正解: B) `true`**

**解説:**
Kafka 4.3 Java KafkaConsumerのデフォルトはtrue、間隔は5000 msです。クライアント位置は外部業務の完了ではありません。非同期/並列処理では未完了処理を越えてコミットしないようにします。手動コミットにも正しい完了位置の管理が必要です。
</details>

4. 次のうちコンシューマーグループのリバランスを引き起こさないものはどれですか？
   - A) 新しいコンシューマーがグループへ参加
   - B) Classicプロトコルのコンシューマーが`session.timeout.ms`内にハートビートを送れない
   - C) トピックのパーティション数が変更
   - D) プロデューサーが`acks=all`でメッセージを送信

<details>

<summary>解答を表示</summary>

**正解: D) プロデューサーが`acks=all`でメッセージを送信**

**解説:**
メンバー構成、購読パーティション、ハートビート/pollタイムアウトは割り当てに影響します。Classicはクライアントのsession.timeout.ms、consumerプロトコルはブローカーのgroup.consumer.session.timeout.msを使います。acksはプロデューサーの確認応答を制御します。
</details>

5. KRaft（Kafka Raftメタデータモード）が本番利用可能（GA）になったKafkaバージョンはどれですか？
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>解答を表示</summary>

**正解: B) Kafka 3.3**

**解説:**
KRaftはKafka 2.8で早期アクセスプレビューとして初登場しましたが、本番利用可能（一般提供）になったのはKafka 3.3です。その後のマイナーリリースで安定化が進み、Kafka 4.0はZooKeeperモードを完全削除して、KRaftを唯一の対応メタデータ管理方式にしました。
</details>

6. ZooKeeperモードを完全削除し、KRaftを唯一のメタデータ管理方式としたKafkaバージョンはどれですか？
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>解答を表示</summary>

**正解: D) Kafka 4.0**

**解説:**
Kafka 4.0（2025年3月リリース）はZooKeeperベースのメタデータ管理モードを完全に削除しました。この版以降、新クラスターはKRaftでのみ初期構築でき、既存ZooKeeperクラスターは4.0更新前にKafka 3.xでKRaft移行を完了する必要があります。
</details>

7. 正常なISRレプリカ3つがあり、コントローラークォーラムなどの他要件を維持した場合、RF=3/min ISR=2/acks=allは書き込み可用性を保ちながら何台のブローカー障害に耐えられますか？
   - A) 0
   - B) 1
   - C) 2
   - D) 3

<details>

<summary>解答を表示</summary>

**正解: B) 1**

**解説:**
最初に全3レプリカが正常ISRに属し、コントローラークォーラム、ネットワーク、ストレージが利用可能な前提です。1ブローカー障害後も残るISR 2つが最小数を満たしますが、移行中エラー/再試行は起こり得ます。2レプリカ障害では書き込み可用性を保てません。RF=3だけで任意の2ブローカー障害時のデータ存続は保証されません。
</details>

8. ブローカーの確認応答を待たないacks設定はどれですか？
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>解答を表示</summary>

**正解: A) `acks=0`**

**解説:**
acks=0はブローカー応答を待たず、保存を確認できず、offset -1を返します。全負荷で最良のレイテンシー/スループットを保証しません。明示的に有効にした冪等性とは競合します。acks=allと-1は同等です。
</details>

9. KRaftで、クラスターのメタデータ変更（パーティションリーダー選出、トピック作成など）を実際に処理する単一ノードを何と呼びますか？
   - A) コントローラー投票者
   - B) アクティブコントローラー
   - C) パーティションリーダー
   - D) メタデータブローカー

<details>

<summary>解答を表示</summary>

**正解: B) アクティブコントローラー**

**解説:**
コントローラー投票者1つがアクティブコントローラーに選ばれます。後任の選出には必要な過半数と接続性が必要です。専用コントローラーはブローカーのデータロールを担う必要はありません。
</details>

10. ClassicグループプロトコルでのCooperativeStickyAssignorの目的は何ですか？
    - A) プロデューサーのパーティションキーハッシュ方式を変更
    - B) リバランス中のパーティション移動を最小化し、コストを減らす
    - C) コントローラークォーラムの投票者数を動的調整
    - D) ISR内のレプリカ数を増やす

<details>

<summary>解答を表示</summary>

**正解: B) リバランス中のパーティション移動を最小化し、コストを減らす**

**解説:**
CooperativeStickyAssignorはClassicグループプロトコルのクライアント割り当て器です。段階的再割り当てで不要な中断を減らします。新しいconsumerプロトコルはサーバー側割り当て器を使うため、同じクライアントクラス設定は適用しません。
</details>

## 短答問題

11. KRaftの内部メタデータRaftログの名前は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `__cluster_metadata`**

**解説:**
__cluster_metadataはKRaftの内部メタデータRaftログで、通常__cluster_metadata-0ディレクトリとして見えます。KafkaProducer/KafkaConsumerで管理する通常アプリケーショントピックではなく、コントローラーとブローカーはメタデータの複製/取得経路を使います。
</details>

12. ネットワーク再試行によるメッセージの重複書き込みを防ぐため、有効にするプロデューサー設定は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `enable.idempotence`（冪等プロデューサー、`enable.idempotence=true`）**

**解説:**
プロデューサーID、エポック、シーケンスが、同じ送信の再試行による重複を抑えます。アプリが業務イベントを新しい送信として提出する場合の一般的な重複排除ではありません。トランザクションには論理書き込み主体のID/フェンシング、出力/入力オフセットのアトミックなコミット、read_committedでの消費が必要です。
</details>

13. パーティションキーのカーディナリティが低い（異なる値が少ない）ため、少数パーティションに通信が集中する状況を何と呼びますか？

<details>

<summary>解答を表示</summary>

**正解: ホットパーティション**

**解説:**
キーに選んだ値のカーディナリティが不足するか、特定値が不釣り合いに頻出するとホットパーティションが生じます。例えば大半の通信が少数の大口顧客IDに集中すると、キーのハッシュ先だけが過負荷となり、残りはアイドルになります。並列コンシューマー処理の利点が失われるため、キー設計で通信分布を慎重に確認すべきです。
</details>

14. KafkaConsumerの連続したpoll()呼び出し間隔を制限する設定は何ですか？

<details>

<summary>解答を表示</summary>

**正解: `max.poll.interval.ms`**

**解説:**
デフォルトは300000 msです。静的メンバーシップ（group.instance.id）では超過しても即パーティション再割り当てにはならず、ハートビート停止後のセッションタイムアウトも関係します。Classic/consumerのタイムアウト規則を確認し、処理、pollサイズ、実行モデルを一緒に調整します。
</details>

## 実践問題

15. 8パーティション、レプリケーション係数3、`min.insync.replicas=2`で`events`トピックを作成する`kafka-topics.sh`コマンドを書いてください。

<details>

<summary>解答を表示</summary>

**解答:**
```bash
kafka-topics.sh --create \
  --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**解説:**
3台以上のブローカーと適切な認証を備えた到達可能なクラスターを前提とします。8パーティションなら、自動割り当てされるパーティションベースグループで最大8つのアクティブ所有者を持てます。1コンシューマーが複数を所有することもあります。耐障害性は実際の同期、クォーラム、他条件に依存します。
</details>

16. 専用コントローラーnode.id=90と3つの検出エンドポイントを持つKafka 4.3.1動的クォーラム設定の抜粋を書き、シードが投票者メンバー構成ではない理由を説明してください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
# Configuration excerpt for node 90; these DNS names must resolve in the deployment.
process.roles=controller
node.id=90
controller.quorum.bootstrap.servers=controller-0.example.internal:9093,controller-1.example.internal:9093,controller-2.example.internal:9093
listeners=CONTROLLER://controller-0.example.internal:9093
advertised.listeners=CONTROLLER://controller-0.example.internal:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=./controller-90-data
```

**解説:**
controller.quorum.bootstrap.serversは検出シード一覧で、投票者構成ではありません。初期format/bootstrapではクラスターID、ディレクトリID、初期投票者を調整する必要があります。動的クォーラムでcontroller.quorum.votersを設定しないでください。DNS、リスナー、TLS/認証をデプロイに合わせます。設定抜粋であり、完全なデプロイ可能クラスターではありません。
</details>

17. 冪等性とトランザクションIDのプロデューサー設定を示し、Kafka間のexactly-once処理に必要な追加手順を説明してください。

<details>

<summary>解答を表示</summary>

**解答:**
```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**解説:**
設定はトランザクション用プロデューサーを準備するだけです。initTransactions、beginTransaction、出力送信、次入力オフセットによるsendOffsetsToTransaction、commitTransaction、中止/復旧処理を実装します。コンシューマーは自動コミットを無効にしread_committedを使います。同時書き込み主体には異なるトランザクションIDが必要で、delivery.timeout.msなどの期限も適用されます。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [次のクイズ: Strimzi Operator](./02-strimzi-operator-quiz.md)
