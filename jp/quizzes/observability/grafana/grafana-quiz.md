# Grafana ダッシュボードクイズ

> **最終更新**: September 13, 2026

Grafana 13.2.1 の設定と運用に関する理解度をテストします。

---

1. Grafana のデータソースのプロビジョニングに使用される方法では**ない**ものはどれですか?
   - A) サイドカーを用いた ConfigMap
   - B) Grafana API
   - C) 環境変数
   - D) provisioning ディレクトリ

<details>
<summary>解答を表示</summary>

**解答: C) 環境変数**

**解説:**
Grafana のデータソースは、provisioning ディレクトリ内の YAML ファイル、ConfigMap を使用したサイドカー方式、または Grafana API を通じてプロビジョニングできます。環境変数は grafana.ini の設定値や、データソースのプロビジョニング YAML 内の URL や認証情報などの値を供給できます。しかし、変数だけではデータソースオブジェクトは作成されません。

</details>

---

2. RED メソッドにおける「R」「E」「D」は何を表しますか?
   - A) Resource, Error, Duration
   - B) Rate, Error, Duration
   - C) Request, Exception, Delay
   - D) Response, Event, Data

<details>
<summary>解答を表示</summary>

**解答: B) Rate, Error, Duration**

**解説:**
RED メソッドはサービスレベルのメトリクスを分析するための方法論です。Rate (リクエスト処理レート)、Error (エラー率)、Duration (応答時間) という 3 つの主要なメトリクスを監視します。これはマイクロサービスの健全性を把握するための効果的なフレームワークです。

</details>

---

3. Grafana で Tempo と Loki を連携させ、トレースからログへの相関付けを実現するにはどのような設定が必要ですか?
   - A) 同じデータベースを使用する
   - B) Tempo データソースで tracesToLogsV2 を設定する
   - C) 別途プラグインをインストールする
   - D) Grafana Enterprise ライセンス

<details>
<summary>解答を表示</summary>

**解答: B) Tempo データソースで tracesToLogsV2 を設定する**

**解説:**
Tempo データソース設定の tracesToLogsV2 セクションを構成することで、トレースから関連するログへ直接遷移できます。datasourceUid で Loki を指定し、tags を使って実際のトレース属性を Loki のラベルにマッピングします。trace_id などのログフィールドはパイプラインの規約と一致している必要があります。これは Grafana の組み込み機能であり、追加のプラグインは必要ありません。

</details>

---

4. USE メソッドにおける「U」「S」「E」は何を表しますか?
   - A) User, Service, Event
   - B) Utilization, Saturation, Errors
   - C) Uptime, Status, Exceptions
   - D) Usage, Speed, Efficiency

<details>
<summary>解答を表示</summary>

**解答: B) Utilization, Saturation, Errors**

**解説:**
USE メソッドはシステムリソースを分析するための方法論です。Utilization (使用率)、Saturation (飽和度)、Errors (エラー) を監視します。各リソース (CPU、メモリ、ディスク、ネットワーク) について、これら 3 つのメトリクスを分析することでボトルネックを特定できます。

</details>

---

5. Grafana Alerting における evaluation interval の役割は何ですか?
   - A) アラートメッセージの配信間隔
   - B) アラートルールの評価頻度
   - C) データの保持期間
   - D) ダッシュボードの更新間隔

<details>
<summary>解答を表示</summary>

**解答: B) アラートルールの評価頻度**

**解説:**
evaluation interval はアラートルールをどのくらいの頻度で評価するかを決定します。たとえば 1m に設定すると、1 分ごとに条件を確認します。これはアラートの感度とリソース使用量に影響します。短すぎるとリソース使用量が増加し、長すぎると問題の検知が遅れます。

</details>

---

6. Google SRE の 4 つのゴールデンシグナルに**含まれない**ものはどれですか?
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>解答を表示</summary>

**解答: C) Availability**

**解説:**
4 つのゴールデンシグナルは Latency (レイテンシ)、Traffic (トラフィック)、Errors (エラー)、Saturation (飽和度) です。Availability (可用性) は重要なメトリクスですが、4 つのゴールデンシグナルには含まれていません。Availability は Errors と関連していますが、別個の概念です。

</details>

---

7. Grafana でダッシュボード変数を使用する主な利点は何ですか?
   - A) ダッシュボードの読み込み速度の向上
   - B) 動的なフィルタリングによるダッシュボードの再利用性の向上
   - C) データストレージ容量の削減
   - D) セキュリティの強化

<details>
<summary>解答を表示</summary>

**解答: B) 動的なフィルタリングによるダッシュボードの再利用性の向上**

**解説:**
ダッシュボード変数を使用すると、1 つのダッシュボードで複数のクラスター、Namespace (名前空間)、Service を監視できます。ドロップダウンから値を選択すると、すべてのパネルのクエリが動的に更新されます。これによりダッシュボードの数が減り、メンテナンスが簡素化されます。

</details>

---

8. Grafana と Prometheus を連携する際の Exemplar 機能の役割は何ですか?
   - A) メトリクスデータの圧縮
   - B) メトリクスとトレースデータの紐付け
   - C) クエリのキャッシュ
   - D) データのバックアップ

<details>
<summary>解答を表示</summary>

**解答: B) メトリクスとトレースデータの紐付け**

**解説:**
Exemplar は選択されたメトリクスの観測値を TraceID に紐付けるものであり、すべてのリクエストを捕捉するわけではありません。ヒストグラムやカウンターのメトリクスにサンプルの TraceID を保存することで、Grafana のメトリクスグラフ上の特定のポイントをクリックすると、その時点のトレースデータを即座にクエリできます。

</details>

---

9. Grafana Cloud とセルフホスト型 Grafana の違いとして正しいものはどれですか?
   - A) Grafana Cloud は無料である
   - B) セルフホスト型ではプラグインをインストールできない
   - C) Grafana Cloud はマネージドであり、その SLA は契約内容によって異なる
   - D) セルフホスト型にはデータソースの制限がある

<details>
<summary>解答を表示</summary>

**解答: C) Grafana Cloud はマネージドであり、その SLA は契約内容によって異なる**

**解説:**
SLA、使用量の上限、機能については、実際の Cloud プランとサービス契約を確認してください。セルフホスト型の運用者は、データベース、バックアップ、アップグレード、プラグインの互換性および署名ポリシーを自ら管理します。すべての Cloud プランに 99.9% という固定の SLA が適用されると想定しないでください。

</details>

---

10. 本章のサイドカープロファイル (label=grafana_dashboard, labelValue="true") はどの ConfigMap ラベルを選択しますか?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>解答を表示</summary>

**解答: B) grafana_dashboard: "true"**

**解説:**
このプロファイルは `grafana_dashboard: "true"` を選択します。label と labelValue はいずれも設定可能であり、Grafana の普遍的な要件ではありません。このオプションのプロファイルは monitoring Namespace 内の ConfigMap のみを監視します。

</details>

---
