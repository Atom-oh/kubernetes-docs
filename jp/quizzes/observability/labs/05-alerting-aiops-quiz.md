# Observability ラボ パート 5: アラートと AIOps クイズ

<span id="observability-lab-part-5-alerting-and-aiops-quiz"></span>

> **最終更新**: September 13, 2026

1. PrometheusRule のアラートを評価するコンポーネントはどれですか？
   - A) Alertmanager
   - B) Prometheus
   - C) SNS
   - D) Lambda の DLQ

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus**

評価を行うのは Prometheus であり、Alertmanager はグループ化、ルーティング、通知を担当します。

</details>

---

2. DatapointsToAlarm=2 と EvaluationPeriods=3 は何を意味しますか？
   - A) 連続する 2 回の閾値超過が必ず必要である。
   - B) 評価対象の 3 データポイントのうち 2 つが閾値を超過すればよく、連続している必要はない。
   - C) 3 秒ごとに 2 回通知する。
   - D) 2 つの Region を使用する。

<details>
<summary>回答を表示</summary>

**回答: B) 評価対象の 3 データポイントのうち 2 つが閾値を超過すればよく、連続している必要はない。**

Period はメトリクスの集計粒度であり、評価頻度と同義ではありません。

</details>

---

3. 旧来の Grafana OnCall OSS のインストール手順を評価する際に重要な点は何ですか？
   - A) 永続的なサポートがある。
   - B) 2026-03-24 のアーカイブ化と Cloud Connection の終了を考慮する。
   - C) SMS のサポートは常に永久に無料である。
   - D) 任意の YAML を適用すれば運用可能になる。

<details>
<summary>回答を表示</summary>

**回答: B) 2026-03-24 のアーカイブ化と Cloud Connection の終了を考慮する。**

組織にとってサポートされているインシデント/通知の経路と、実際に配信されることを検証します。

</details>

---

4. SNS の入力トピックと出力トピックを分離するのはなぜですか？
   - A) メトリクスの単位を変更するため。
   - B) レポーターが自身の結果を処理してループに陥るのを防ぐため。
   - C) SNS が 1 つのトピックしかサポートしないため。
   - D) ログを公開するため。

<details>
<summary>回答を表示</summary>

**回答: B) レポーターが自身の結果を処理してループに陥るのを防ぐため。**

サブスクリプションと IAM の publish 権限を同じ境界に制限します。

</details>

---

5. Alertmanager の `{{ . | toJson }}` 出力に関して、パーサーは何を考慮しなければなりませんか？
   - A) 常にプレーンテキストである。
   - B) JSON タグの小文字/camelCase のキーは、Go テンプレートで先頭大文字のフィールドにアクセスする場合と異なる。
   - C) JSON はパースが不要である。
   - D) すべての SNS メッセージは同一のフィールドを持つ。

<details>
<summary>回答を表示</summary>

**回答: B) JSON タグの小文字/camelCase のキーは、Go テンプレートで先頭大文字のフィールドにアクセスする場合と異なる。**

実際の 0.34.0 のテンプレートのシリアライズと、有効/無効なペイロードをテストしました。

</details>

---

6. メトリクスが存在しない場合やクエリが失敗した場合、どのように報告すべきですか？
   - A) エラーをゼロに変換する。
   - B) 測定値を捏造せず、missing/no_data/error のラベルを付ける。
   - C) クエリ文字列を測定値として提示する。
   - D) 常に正常なステータスを報告する。

<details>
<summary>回答を表示</summary>

**回答: B) 測定値を捏造せず、missing/no_data/error のラベルを付ける。**

根拠が不十分な場合は、モデル呼び出しをスキップできます。

</details>

---

7. このサンプルにおいて Powertools の冪等性は何を提供しますか？
   - A) エンドツーエンドの SNS exactly-once 配信。
   - B) 同一のメッセージ ID に対する成功済み処理の繰り返しを 24 時間以内は抑止する。
   - C) 新しいメッセージ ID はすべて同一の操作である。
   - D) 発行と DB のコミットをアトミックに結合する。

<details>
<summary>回答を表示</summary>

**回答: B) 同一のメッセージ ID に対する成功済み処理の繰り返しを 24 時間以内は抑止する。**

発行/コミットの重複ウィンドウと、SNS/Lambda のリトライ層を区別します。

</details>

---

8. Converse の診断レスポンスはどのように受け入れますか？
   - A) どのレスポンスでも成功とする。
   - B) maxTokens を設定し、空でないテキストを伴う end_turn を必須とする。
   - C) max_tokens による停止は診断完了である。
   - D) モデルが生成したコマンドを即座に実行する。

<details>
<summary>回答を表示</summary>

**回答: B) maxTokens を設定し、空でないテキストを伴う end_turn を必須とする。**

レポーターは人間によるレビュー用に仮説を作成するもので、修復のためのツールは持ちません。

</details>

---

9. CloudWatch Investigations を開始するようにアラームを設定するにはどうしますか？
   - A) list-dashboards を呼び出す。
   - B) 準備済みの investigation-group ARN をアラームアクションとして追加する。
   - C) put-insight-rule のみを呼び出す。
   - D) Application Signals の検出のみを有効にする。

<details>
<summary>回答を表示</summary>

**回答: B) 準備済みの investigation-group ARN をアラームアクションとして追加する。**

グループ、権限、保持期間、暗号化、そして実際のアラームアクションを準備します。

</details>

---

10. 複数の分析モジュールを呼び出せば A2A プロトコルを実装したことになりますか？
   - A) 2 つの関数があれば自動的に A2A を実装したことになる。
   - B) ならない。ディスカバリー、認証、タスク/メッセージの契約は個別に実装する必要がある。
   - C) SNS を使えば常に A2A を意味する。
   - D) DynamoDB だけで十分である。

<details>
<summary>回答を表示</summary>

**回答: B) ならない。ディスカバリー、認証、タスク/メッセージの契約は個別に実装する必要がある。**

スペシャリストへの分解は設計パターンであり、エージェントプロトコルへの準拠とは別のものです。

</details>

---

[ガイドに戻る](../../../labs/observability/05-alerting-aiops-lab.md)
