# ゾーンクラスター運用クイズ

> **関連ドキュメント**: [ゾーンクラスター運用](../../ops/15-zonal-operations-guide.md)

## 選択式問題

### 1. Amazon EKS のネイティブ Kubernetes バージョンロールバック（2026年7月に GA）の対象期間はどれですか？

- A) 24時間
- B) 7日間
- C) 30日間
- D) 無制限

<details>
<summary>回答を表示</summary>

**回答: B) 7日間**

**解説:**
EKS のネイティブロールバックでは、アップグレードから7日以内であれば、一度に1つのマイナーバージョンを戻せます。対象バージョンで作成されたクラスター、7日を超過したクラスター、またはすでに再アップグレードされたクラスターは対象外です。

</details>

### 2. Zonal In-Place アップグレード中にゾーンからトラフィックを退避させるには、どの仕組みを使用しますか？

- A) `kubectl drain`
- B) Target Group の重みを調整する
- C) DNS TTL の期限切れを待つ
- D) クラスターを再作成する

<details>
<summary>回答を表示</summary>

**回答: B) Target Group の重みを調整する**

**解説:**
クラスター内の何かに手を加える代わりに、TargetGroupBinding を通じて関連付けられた Target Group の重みを調整し、特定のゾーンへのトラフィックを削減または停止します。AZ 障害のような計画外の状況では、ARC Zonal Shift がこの役割を自動的に実行します。

</details>

### 3. KIP-392（Follower Fetching）を有効化するために、Kafka broker に設定する必要があるものはどれですか？

- A) `auto.leader.rebalance.enable=true`
- B) `replica.selector.class=RackAwareReplicaSelector`
- C) `unclean.leader.election.enable=true`
- D) `min.insync.replicas=2`

<details>
<summary>回答を表示</summary>

**回答: B) `replica.selector.class=RackAwareReplicaSelector`**

**解説:**
Broker では `replica.selector.class` を `RackAwareReplicaSelector` に設定し、`broker.rack`（AZ ID）を割り当てる必要があります。consumer 側では、同じ rack の follower に fetch がリダイレクトされるよう、`client.rack` プロパティを consumer 自身の AZ ID に設定する必要があります。

</details>

### 4. 読み取りが99%を超えるワークロードに推奨される Valkey GLIDE の `ReadFrom` 戦略はどれですか？

- A) `PRIMARY`
- B) `PREFER_REPLICA`
- C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`
- D) ランダム分散

<details>
<summary>回答を表示</summary>

**回答: C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`**

**解説:**
まず同じ AZ の replica を優先し、次に同じ AZ の primary へフォールバックし、他の AZ へアクセスするのは最後の手段です。読み取り主体のワークロードでは、コスト削減と可用性の推奨されるバランスを実現します。HotelTrader はこれを採用後、AZ 間転送コストを95%削減しました。

</details>

### 5. Amazon Aurora のデフォルトの reader endpoint について正しい記述はどれですか？

- A) 同じ AZ の replica を自動的に優先する
- B) AZ を認識しないラウンドロビン DNS である
- C) 常に primary にルーティングする
- D) AWS Advanced JDBC Wrapper なしでは使用できない

<details>
<summary>回答を表示</summary>

**回答: B) AZ を認識しないラウンドロビン DNS である**

**解説:**
Aurora のデフォルトの reader endpoint には AZ affinity がありません。AZ ごとの custom endpoint または AWS Advanced JDBC Wrapper の `fastestResponse` 戦略で回避できますが、真の AZ affinity 自体は `aws-advanced-jdbc-wrapper` リポジトリで未解決の機能リクエストのままです。

</details>

### 6. Pod が自身の AZ を判定する方法について、誤っている記述はどれですか？

- A) EC2 IMDS を介して直接調べられる
- B) Kyverno の mutating policy により、node label を Pod annotation にコピーできる
- C) Kubernetes Downward API は、デフォルトで node の zone label を Pod に注入する
- D) Strimzi のような operator は、組み込み機能として rack-awareness を提供できる

<details>
<summary>回答を表示</summary>

**回答: C) Kubernetes Downward API は、デフォルトで node の zone label を Pod に注入する**

**解説:**
Downward API は、node の `topology.kubernetes.io/zone` label を Pod に自動的には注入しません。そのため、他の方法、すなわち IMDS の直接参照、Kyverno ベースの admission 時の label コピー、または Strimzi のような operator の組み込みサポートが必要です。

</details>
