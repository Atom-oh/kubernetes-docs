# ゾーンクラスター運用クイズ

> **関連ドキュメント**: [ゾーンクラスター運用](../../ops/15-zonal-operations-guide.md)

## 選択式問題

### 1. EKS の7日間のネイティブロールバック期間は何を意味しますか？

- A) ロールバックの実行にかけられる時間
- B) アップグレード完了後にロールバックを開始できる期限
- C) ノードの最大稼働期間
- D) アドオンが自動的に復元される期間

<details>
<summary>回答を表示</summary>

**回答: B) アップグレード完了後にロールバックを開始できる期限**

直前のマイナーバージョンへのロールバックを開始できる期間です。クラスターの作成時のバージョン、サポート状況、その後のアップグレード、互換性も影響します。Auto Mode では最初にノードがロールバックされますが、アドオン、アプリケーション、データの変更は自動的には復元されません。

</details>

### 2. NLB ターゲットグループの重みを0にした後、何を確認する必要がありますか？

- A) 既存の接続がすべて直ちに終了すること
- B) TargetGroupBinding が別のクラスターへ移動すること
- C) 新規フローの減少と既存フローのドレインを別々に確認すること
- D) ARC が他のすべてのクラスターの重みを自動的に書き換えること

<details>
<summary>回答を表示</summary>

**回答: C) 新規フローの減少と既存フローのドレインを別々に確認すること**

通常、重みの変更が影響するのは新しいフローですが、現在の NLB ガイドによると、重みを0にすると短時間後に既存の接続も閉じられます。自然なドレインだけを前提にせず、再接続とリトライの動作をテストしてください。ノードを変更する前に NewFlowCount、ActiveFlowCount、エラーを確認します。TGB に重みのフィールドはなく、EKS の Zonal Shift がクラスター間の重みを自動的に変更することもありません。

</details>

### 3. Kafka KIP-392 を正しく構成する組み合わせはどれですか？

- A) `broker.rack` だけで、すべての consumer が自動的に構成される
- B) RackAwareReplicaSelector、`broker.rack`、一致する consumer の `client.rack`
- C) `unclean.leader.election.enable=true` だけ
- D) AZ 名と AZ ID の文字列は相互に置き換えられる

<details>
<summary>回答を表示</summary>

**回答: B) RackAwareReplicaSelector、`broker.rack`、一致する consumer の `client.rack`**

`replica.selector.class` の完全な値は `org.apache.kafka.common.replica.RackAwareReplicaSelector` です。Strimzi の Kafka CR は broker を構成しますが、通常のアプリケーション consumer は別途構成する必要があります。適切なローカル replica がない場合、選択先は leader にフォールバックします。

</details>

### 4. GLIDE の `AZ_AFFINITY_REPLICAS_AND_PRIMARY` の優先順位はどれですか？

- A) Primary のみ
- B) ローカル replica → ローカル primary → 他の AZ の replica または primary
- C) リモート replica のみ
- D) ローカルノードがなければ常にエラー

<details>
<summary>回答を表示</summary>

**回答: B) ローカル replica → ローカル primary → 他の AZ の replica または primary**

サーバー側の AZ メタデータを `client_az` と一致させる必要があります。古い replica からの読み取りを許容できるか評価してください。読み取り割合だけでは判断できません。HotelTrader が報告した改善には、AZ を考慮したルーティングに加えてリクエストのバッチ処理も含まれています。

</details>

### 5. Aurora のデフォルト reader endpoint について正しい説明はどれですか？

- A) 各 SQL クエリを別々の replica に分散する
- B) 同じ AZ の reader を保証する
- C) 接続を分散し、replica がなければ writer を使用する場合がある
- D) 接続には JDBC Wrapper が必須である

<details>
<summary>回答を表示</summary>

**回答: C) 接続を分散し、replica がなければ writer を使用する場合がある**

AZ が優先される保証はありません。AZ ごとの READER カスタムエンドポイントでは、メンバーシップとフォールバックの管理が必要です。JDBC の `fastestResponse` は応答時間を使う方式で、厳密な AZ 制約ではありません。機能リクエスト #1139 は2025年にクローズされました。

</details>

### 6. Pod の AZ を特定する方法について、誤っている説明はどれですか？

- A) 通常の Pod 作成時の admission 処理では、scheduler が選んだ node が常に分かる
- B) AWS MSK の Kyverno 例は Pod と binding のリクエストを処理する
- C) Downward API を使って `spec.nodeName` を初期化コンポーネントに渡せる
- D) IMDS へのアクセス可否は環境とセキュリティ設定によって異なる

<details>
<summary>回答を表示</summary>

**回答: A) 通常の Pod 作成時の admission 処理では、scheduler が選んだ node が常に分かる**

通常、Pod 作成時点では node はまだ選択されていません。binding 時の値注入、またはスケジューリング後の参照を使ってください。Downward API は node label を直接参照するものではなく、Strimzi が無関係なアプリケーション consumer を自動構成するわけでもありません。

</details>
