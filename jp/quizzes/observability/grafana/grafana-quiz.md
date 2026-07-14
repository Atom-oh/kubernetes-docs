# Grafana ダッシュボードクイズ

Grafana に関する理解度を確認しましょう。

---

1. Grafana でデータソースをプロビジョニングする方法として**使用されない**ものはどれですか？
   - A) sidecar を使用した ConfigMap
   - B) Grafana API
   - C) 環境変数
   - D) provisioning directory

<details>
<summary>回答を表示</summary>

**回答: C) 環境変数**

**解説:**
Grafana のデータソースは、provisioning directory 内の YAML ファイル、ConfigMap を使用する sidecar アプローチ、または Grafana API を通じてプロビジョニングできます。環境変数は Grafana の設定（grafana.ini）には使用されますが、データソースを直接定義するためには使用されません。

</details>

---

2. RED Method における「R」「E」「D」はそれぞれ何を表しますか？
   - A) Resource、Error、Duration
   - B) Rate、Error、Duration
   - C) Request、Exception、Delay
   - D) Response、Event、Data

<details>
<summary>回答を表示</summary>

**回答: B) Rate、Error、Duration**

**解説:**
RED Method は、サービスレベルのメトリクスを分析するための手法です。Rate（リクエスト処理率）、Error（エラー率）、Duration（応答時間）の 3 つの主要なメトリクスを監視します。これは、マイクロサービスの健全性を把握するための効果的なフレームワークです。

</details>

---

3. Grafana で Tempo と Loki を接続してトレースとログの相関関係を実装するには、どの設定が必要ですか？
   - A) 同じデータベースを使用する
   - B) Tempo データソースで tracesToLogs を設定する
   - C) 別途プラグインをインストールする
   - D) Grafana Enterprise ライセンス

<details>
<summary>回答を表示</summary>

**回答: B) Tempo データソースで tracesToLogs を設定する**

**解説:**
Tempo データソース設定の tracesToLogs セクションを構成すると、トレースから関連するログへ直接移動できます。datasourceUid で Loki を指定し、tags を使用して接続用のラベルを設定します。これは追加のプラグインを必要としない Grafana の組み込み機能です。

</details>

---

4. USE Method における「U」「S」「E」はそれぞれ何を表しますか？
   - A) User、Service、Event
   - B) Utilization、Saturation、Errors
   - C) Uptime、Status、Exceptions
   - D) Usage、Speed、Efficiency

<details>
<summary>回答を表示</summary>

**回答: B) Utilization、Saturation、Errors**

**解説:**
USE Method は、システムリソースを分析するための手法です。Utilization、Saturation、Errors を監視します。各リソース（CPU、メモリ、ディスク、ネットワーク）についてこれら 3 つのメトリクスを分析することで、ボトルネックを特定できます。

</details>

---

5. Grafana Alerting における evaluation interval の役割は何ですか？
   - A) アラートメッセージの配信間隔
   - B) アラートルールの評価頻度
   - C) データ保持期間
   - D) ダッシュボードの更新間隔

<details>
<summary>回答を表示</summary>

**回答: B) アラートルールの評価頻度**

**解説:**
evaluation interval は、アラートルールを評価する頻度を決定します。たとえば、1m に設定すると、条件を毎分確認します。これはアラートの感度とリソース使用量に影響します。短すぎるとリソース使用量が増加し、長すぎると問題の検出が遅れます。

</details>

---

6. Google SRE の 4 Golden Signals に含まれ**ない**ものはどれですか？
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>回答を表示</summary>

**回答: C) Availability**

**解説:**
4 Golden Signals は、Latency、Traffic、Errors、Saturation です。Availability は重要なメトリクスですが、4 Golden Signals には含まれません。Availability は Errors と関連していますが、別の概念です。

</details>

---

7. Grafana でダッシュボード変数を使用する主な利点は何ですか？
   - A) ダッシュボードの読み込み速度の向上
   - B) 動的フィルタリングによるダッシュボードの再利用性の向上
   - C) データストレージ容量の削減
   - D) セキュリティの強化

<details>
<summary>回答を表示</summary>

**回答: B) 動的フィルタリングによるダッシュボードの再利用性の向上**

**解説:**
ダッシュボード変数を使用すると、単一のダッシュボードで複数のクラスター、namespace、Service を監視できます。ドロップダウンから値を選択すると、すべてのパネルクエリが動的に更新されます。これによりダッシュボードの数が減り、メンテナンスが簡素化されます。

</details>

---

8. Grafana と Prometheus の統合において、Exemplar 機能の役割は何ですか？
   - A) メトリクスデータの圧縮
   - B) メトリクスとトレースデータのリンク
   - C) クエリのキャッシュ
   - D) データのバックアップ

<details>
<summary>回答を表示</summary>

**回答: B) メトリクスとトレースデータのリンク**

**解説:**
Exemplar は、TraceID を Prometheus メトリクスにリンクする機能です。histogram または counter メトリクスにサンプルの TraceID を保存することで、Grafana のメトリクスグラフ上の特定のポイントをクリックすると、その時点のトレースデータをすぐにクエリできます。

</details>

---

9. Grafana Cloud と Self-hosted Grafana の正しい違いはどれですか？
   - A) Grafana Cloud は無料である
   - B) Self-hosted ではプラグインをインストールできない
   - C) Grafana Cloud は自動スケーリングと SLA を提供する
   - D) Self-hosted にはデータソースの制限がある

<details>
<summary>回答を表示</summary>

**回答: C) Grafana Cloud は自動スケーリングと SLA を提供する**

**解説:**
Grafana Cloud は、自動スケーリング、99.9% SLA、自動アップデートなどを提供するマネージドサービスです。Self-hosted は完全な制御を提供し、すべてのプラグインをインストールできますが、インフラストラクチャの管理が必要です。どちらの選択肢もさまざまなデータソースをサポートします。

</details>

---

10. Grafana のダッシュボードプロビジョニングに sidecar を使用する場合、ConfigMap に必要なラベルはどれですか？
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>回答を表示</summary>

**回答: B) grafana_dashboard: "true"**

**解説:**
Grafana Helm chart の sidecar 機能を使用する場合、ダッシュボード JSON を含む ConfigMap に `grafana_dashboard: "true"` ラベルを追加する必要があります。sidecar コンテナはこのラベルを持つ ConfigMap を監視し、ダッシュボードを自動的にプロビジョニングします。

</details>

---
