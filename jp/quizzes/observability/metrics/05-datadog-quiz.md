# Datadog クイズ

Datadog に関する理解度を確認するクイズです。

---

1. Datadog の主要なデプロイメントモデルは何ですか？
   - A) セルフホストのみ
   - B) SaaS (Software as a Service)
   - C) オンプレミスのみ
   - D) ハイブリッドが必須

<details>
<summary>回答を表示</summary>

**回答: B) SaaS (Software as a Service)**

**解説:**
Datadog は SaaS モデルで提供される統合オブザーバビリティプラットフォームです。ユーザーは Datadog Agent をデプロイするだけでよく、データの保存、処理、可視化は Datadog のクラウドインフラストラクチャによって処理されます。これにより、運用上の負荷をかけずに強力な監視機能を利用できます。

</details>

---

2. Datadog Cluster Agent の役割は何ですか？
   - A) コンテナログの収集
   - B) クラスターレベルのメトリクスおよびイベントの収集
   - C) APM トレースの処理
   - D) ダッシュボードのレンダリング

<details>
<summary>回答を表示</summary>

**回答: B) クラスターレベルのメトリクスおよびイベントの収集**

**解説:**
Datadog Cluster Agent は Kubernetes クラスターからクラスター レベルのメトリクスとイベントを収集します。また、HPA (Horizontal Pod Autoscaler) 用のカスタムメトリクスサーバーとしての役割や、Admission Controller による自動 APM インストルメンテーションのインジェクションも提供します。

</details>

---

3. Datadog で自動 APM インストルメンテーションを有効にするにはどうしますか？
   - A) アプリケーションコードの変更が必要
   - B) Admission Controller と Pod ラベルを使用する
   - C) 別途 APM サーバーをデプロイする
   - D) ライブラリを手動でインジェクションする

<details>
<summary>回答を表示</summary>

**回答: B) Admission Controller と Pod ラベルを使用する**

**解説:**
Datadog Admission Controller を有効にすると、`admission.datadoghq.com/enabled: "true"` ラベルを持つ Pod に APM インストルメンテーションライブラリが自動的にインジェクションされます。Java、Python、Node.js、.NET、Ruby などの主要な言語をサポートしており、コードを変更せずにトレーシングを開始できます。

</details>

---

4. DogStatsD の役割は何ですか？
   - A) ログの収集
   - B) カスタムメトリクスの収集 (StatsD 互換)
   - C) ダッシュボードの作成
   - D) アラートのルーティング

<details>
<summary>回答を表示</summary>

**回答: B) カスタムメトリクスの収集 (StatsD 互換)**

**解説:**
DogStatsD は Datadog Agent に含まれる StatsD 互換のメトリクス収集デーモンです。アプリケーションは UDP 経由でカスタムメトリクス (カウンター、ゲージ、ヒストグラム、ディストリビューション) を送信できます。タグ機能が追加された StatsD プロトコルと互換性があります。

</details>

---

5. Datadog でトレースとログを関連付けるにはどうしますか？
   - A) ログファイルを手動でアップロードする
   - B) ログに trace_id と span_id を含める
   - C) 別途接続サービスをデプロイする
   - D) ログとトレースのタイムスタンプを照合する

<details>
<summary>回答を表示</summary>

**回答: B) ログに trace_id と span_id を含める**

**解説:**
Datadog でトレースとログを関連付けるには、ログに `dd.trace_id` と `dd.span_id` を含める必要があります。Datadog APM ライブラリは、MDC (Mapped Diagnostic Context) を通じてこの情報を自動的にインジェクションできます。これにより、APM から関連するログを直接表示できます。

</details>

---

6. Datadog のコスト構造において、インフラストラクチャ監視の課金単位は何ですか？
   - A) メトリクス数
   - B) ホスト数
   - C) API 呼び出し数
   - D) データ転送量

<details>
<summary>回答を表示</summary>

**回答: B) ホスト数**

**解説:**
Datadog のインフラストラクチャ監視はホスト数に基づいて課金されます。各ノード、インスタンス、コンテナホストが課金対象です。APM、ログ管理、その他の機能にはそれぞれ別の課金体系があり、ホストベースの課金によりコスト予測が容易になります。

</details>

---

7. Datadog Watchdog の機能は何ですか？
   - A) 手動でのアラート設定
   - B) AI ベースの自動異常検出
   - C) ログ検索
   - D) ダッシュボードの作成

<details>
<summary>回答を表示</summary>

**回答: B) AI ベースの自動異常検出**

**解説:**
Watchdog は Datadog の AI/ML ベースの自動異常検出機能です。インフラストラクチャ、APM、ログデータ内の異常なパターンを自動的に検出し、アラートを生成します。しきい値を手動で設定することなく異常を特定できます。

</details>

---

8. Datadog Agent で Prometheus メトリクスを収集するにはどうしますか？
   - A) 別途 Prometheus サーバーが必要
   - B) Pod アノテーションで自動検出を設定する
   - C) 各エンドポイントを手動で登録する
   - D) Prometheus を Datadog に置き換える

<details>
<summary>回答を表示</summary>

**回答: B) Pod アノテーションで自動検出を設定する**

**解説:**
Datadog Agent は `ad.datadoghq.com/<container>.checks` アノテーションを使用して、Prometheus メトリクスエンドポイントを自動検出して収集します。設定は Prometheus のスクレイプ設定に類似しており、別途 Prometheus サーバーを用意せずにメトリクスを収集できます。

</details>

---

9. Datadog で SLO (Service Level Objective) を設定する際に使用できるメトリクスの種類は何ですか？
   - A) ログイベントのみ
   - B) メトリクスベース、モニターベース、タイムスライスベース
   - C) APM トレースのみ
   - D) インフラストラクチャメトリクスのみ

<details>
<summary>回答を表示</summary>

**回答: B) メトリクスベース、モニターベース、タイムスライスベース**

**解説:**
Datadog SLO は、メトリクスベース (成功/失敗のカウント)、モニターベース (既存モニターのステータス)、タイムスライスベース (時間間隔ごとのステータス) の 3 種類をサポートしています。APM トレース、カスタムメトリクス、ログベースのメトリクスなど、さまざまなデータソースを利用できます。

</details>

---

10. 有効ではない Datadog のコスト最適化戦略はどれですか？
    - A) APM トレースのサンプリングレートを調整する
    - B) 不要なログをフィルタリングする
    - C) すべてのメトリクスを最高解像度で収集する
    - D) カスタムメトリクスのカーディナリティを管理する

<details>
<summary>回答を表示</summary>

**回答: C) すべてのメトリクスを最高解像度で収集する**

**解説:**
Datadog のコスト最適化では、APM トレースのサンプリング、ログフィルタリング、カスタムメトリクスのカーディナリティ管理が重要です。すべてのメトリクスを最高解像度で収集すると、コストが急増します。必要なメトリクスのみを選択的に収集し、適切なサンプリングを適用してください。

</details>
