# メトリクス概要クイズ

基本的なメトリクスの概念と監視ソリューションに関する理解度を確認しましょう。

---

1. Prometheus メトリクスの4つの基本タイプのうち、値が増加するのみで、再起動時に 0 にリセットされるタイプはどれですか？
   - A) Gauge
   - B) Counter
   - C) Histogram
   - D) Summary

<details>
<summary>回答を表示</summary>

**回答: B) Counter**

**解説:**
Counter は累積値を追跡するメトリクスタイプで、値は増加するのみで、再起動時に 0 にリセットされます。HTTP リクエスト数、エラー数、完了したタスク数などの追跡に使用されます。Gauge は増加と減少の両方が可能ですが、Histogram と Summary は分布を測定します。

</details>

---

2. Cardinality を正しく説明しているものはどれですか？
   - A) メトリクスの収集間隔を指す
   - B) 一意な時系列の組み合わせの数を指す
   - C) メトリクスデータの圧縮率を指す
   - D) メトリクスの保持期間を指す

<details>
<summary>回答を表示</summary>

**回答: B) 一意な時系列の組み合わせの数を指す**

**解説:**
Cardinality は、メトリクス内の一意なラベルの組み合わせの数を指します。Cardinality が高いと、ストレージ使用量とクエリパフォーマンスに直接影響します。user_id や request_id のように無限に増加する可能性がある値をラベルとして使用すると、Cardinality が急増します。

</details>

---

3. Pull モデルと Push モデルについて、正しくない記述はどれですか？
   - A) Prometheus は Pull ベースのシステムである
   - B) Pull モデルでは、収集ターゲットと間隔を一元的に制御する
   - C) Push モデルは短時間で終了するジョブからメトリクスを収集するのに適している
   - D) Pull モデルは NAT/ファイアウォールの背後にあるターゲットに容易にアクセスできる

<details>
<summary>回答を表示</summary>

**回答: D) Pull モデルは NAT/ファイアウォールの背後にあるターゲットに容易にアクセスできる**

**解説:**
Pull モデルでは、監視サーバーがターゲットに HTTP リクエストを直接送信してメトリクスを収集するため、NAT/ファイアウォールの背後にあるターゲットへのアクセスが困難になります。一方、Push モデルではターゲットがメトリクスを直接送信できるため、NAT/ファイアウォール環境で有利です。Pushgateway を使用すると、Pull モデルでも短時間で終了するジョブからメトリクスを収集できます。

</details>

---

4. Histogram と Summary の違いを正しく説明しているものはどれですか？
   - A) Histogram はクライアントで quantile を計算する
   - B) Summary では複数のインスタンス間で集約できる
   - C) Histogram はサーバー（クエリ時）で quantile を計算する
   - D) Summary は Histogram よりストレージ効率が高い

<details>
<summary>回答を表示</summary>

**回答: C) Histogram はサーバー（クエリ時）で quantile を計算する**

**解説:**
Histogram はデータを bucket に格納し、クエリ時にサーバーで quantile を計算します。Summary はクライアントで quantile を計算して格納します。Histogram では複数のインスタンス間で集約できますが、Summary ではできません。Histogram は SLO/SLI の測定と分散システムに推奨されます。

</details>

---

5. 推奨されないメトリクス命名規則はどれですか？
   - A) snake_case を使用する
   - B) 単位を接尾辞として含める (_seconds, _bytes)
   - C) camelCase を使用する
   - D) アプリケーション/ドメインのプレフィックスを使用する

<details>
<summary>回答を表示</summary>

**回答: C) camelCase を使用する**

**解説:**
Prometheus スタイルのメトリクス命名規則では、camelCase ではなく snake_case を使用します。`http_requests_total`、`http_request_duration_seconds` のような適切なメトリクス名では、小文字とアンダースコアを使用し、単位を接尾辞として含め、アプリケーション/ドメインのプレフィックスを使用します。

</details>

---

6. Prometheus に長期ストレージ用の別ソリューションが必要である理由として、適切でないものはどれですか？
   - A) 圧縮率が低く、ディスク使用量が増加する
   - B) 単一ノードアーキテクチャのためスケーラビリティに制限がある
   - C) PromQL は複雑なクエリをサポートしていない
   - D) ネイティブ HA クラスタリングがサポートされていない

<details>
<summary>回答を表示</summary>

**回答: C) PromQL は複雑なクエリをサポートしていない**

**解説:**
PromQL は複雑なクエリをサポートする非常に強力なクエリ言語です。Prometheus が長期ストレージに適していない理由には、比較的低い圧縮率、単一ノードアーキテクチャによるスケーラビリティの制限、ネイティブ HA クラスタリングの欠如、長期データに対するクエリ速度の低さがあります。

</details>

---

7. 正しくないソリューション比較はどれですか？
   - A) VictoriaMetrics は Prometheus より高い圧縮率を提供する
   - B) CloudWatch はフルマネージドサービスである
   - C) Mimir はローカルディスクのみをサポートする
   - D) Datadog は SaaS モデルで提供される

<details>
<summary>回答を表示</summary>

**回答: C) Mimir はローカルディスクのみをサポートする**

**解説:**
Grafana Mimir はオブジェクトストレージ（S3、GCS、Azure Blob など）を必要とする分散メトリクスストアです。ローカルディスクの代わりにクラウドオブジェクトストレージを使用して、無制限のスケーラビリティと長期保持を実現します。VictoriaMetrics はローカルディスクとオブジェクトストレージの両方をサポートします。

</details>

---

8. 高 Cardinality の問題を防止するための適切でない方法はどれですか？
   - A) ユーザー ID をメトリクスラベルとして使用しない
   - B) リクエスト ID をメトリクスラベルとして使用しない
   - C) HTTP ステータスコードをグループ化する (200 → 2xx)
   - D) すべてのラベル値を一意に保つ

<details>
<summary>回答を表示</summary>

**回答: D) すべてのラベル値を一意に保つ**

**解説:**
高 Cardinality を防止するには、ラベル値が無限に増加しないようにする必要があります。ユーザー ID、リクエスト ID、セッション ID のように無限に増加する可能性がある値は、ラベルとして使用すべきではありません。HTTP ステータスコードをグループ化し（200 → 2xx）、URL パスを正規化する（/users/123 → /users/{id}）ほうが適切です。

</details>

---

9. Kubernetes 環境における主なメトリクスソースと役割の組み合わせとして正しいものはどれですか？
   - A) node-exporter - Kubernetes オブジェクトの状態メトリクス
   - B) kube-state-metrics - Node レベルのハードウェアメトリクス
   - C) cAdvisor - Container レベルのリソースメトリクス
   - D) metrics-server - 長期メトリクスストレージ

<details>
<summary>回答を表示</summary>

**回答: C) cAdvisor - Container レベルのリソースメトリクス**

**解説:**
cAdvisor（Container Advisor）は、Container ごとの CPU、メモリ、I/O などのリソースメトリクスを収集します。node-exporter は Node レベルのハードウェア/OS メトリクスを提供し、kube-state-metrics は Kubernetes API オブジェクト（Pod、Deployment、Node など）の状態メトリクスを提供し、metrics-server は HPA/VPA 向けのリアルタイムリソースメトリクスを提供します。

</details>

---

10. メトリクスソリューションを選択する際の適切でない考慮事項はどれですか？
    - A) チームの運用能力と規模
    - B) マルチクラウドの要件
    - C) コスト構造と予算
    - D) メトリクス名の長さ

<details>
<summary>回答を表示</summary>

**回答: D) メトリクス名の長さ**

**解説:**
メトリクスソリューションを選択する際は、チームの運用能力、マルチクラウドの要件、コスト構造、スケーラビリティの要件、既存のエコシステムとの統合を考慮する必要があります。メトリクス名の長さはソリューションの選択に影響しません。代わりに、Cardinality、データ保持期間、クエリパフォーマンスが重要な考慮事項です。

</details>

---
