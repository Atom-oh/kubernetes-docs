# Observability ラボ パート 6: Distributed Tracing 分析クイズ

> **最終更新**: February 22, 2026

Observability End-to-End ラボ パート 6 で扱った Distributed Tracing 分析の概念についての理解を確認しましょう。

---

1. Span フィルタリングにおける TraceQL の基本的な構文構造は何ですか？
   - A) JOIN 句を含む SQL のような SELECT 文
   - B) ドット記法を使用した Span 属性フィルターを含む波括弧。例: `{ span.attribute = "value" }`
   - C) XML ベースのクエリ形式
   - D) 正規表現のみ

<details>
<summary>回答を表示</summary>

**回答: B) ドット記法を使用した Span 属性フィルターを含む波括弧。例: `{ span.attribute = "value" }`**

**解説:**
TraceQL は、Span セレクターに波括弧を使用するパイプラインベースの構文を採用しています。基本構造は `{ spanset_filter }` であり、フィルターでは属性にドット記法を使用します。組み込み属性には `span.` プレフィックス（例: `span.duration`、`span.status`）、リソース属性には `resource.` プレフィックス（例: `resource.service.name`）を使用し、Span 属性は直接指定します（例: `http.status_code`）。フィルターは `=`、`!=`、`>`、`<`、`=~`（正規表現）などの演算子をサポートし、`&&` と `||` で組み合わせることができます。

</details>

---

2. TraceQL クエリ `{ span.http.status_code >= 500 }` は何を返しますか？
   - A) システム内のすべての Trace
   - B) HTTP レスポンスのステータスコードが 500 以上であり、サーバーエラーを示す Span
   - C) 500 ミリ秒より長くかかった Span
   - D) 最新の 500 件の Span

<details>
<summary>回答を表示</summary>

**回答: B) HTTP レスポンスのステータスコードが 500 以上であり、サーバーエラーを示す Span**

**解説:**
このクエリは `http.status_code` 属性に基づいて Span をフィルタリングし、サーバーエラーのステータスコード（500、502、503 など）を持つものだけを返します。これは分散システムにおけるエラー状態の調査に役立ちます。クエリは一致する Span を含む Trace 全体を返し、エラー Span を強調表示します。特定の Service に焦点を当てるには、`{ span.http.status_code >= 500 && resource.service.name = "payment-service" }` のような追加フィルターで結果をさらに絞り込めます。

</details>

---

3. Tempo の Service Graph で高いエラー率またはレイテンシを持つエッジを特定するにはどうしますか？
   - A) エッジはメトリクスに関係なく常に同じように表示される
   - B) Service Graph は、エラー率とレイテンシに基づく色分けまたは太さでエッジを可視化し、問題のある Service 間通信を強調表示する
   - C) 生の Span からエッジメトリクスを手動で計算する必要がある
   - D) Service Graph はメトリクスなしで Service 名のみを表示する

<details>
<summary>回答を表示</summary>

**回答: B) Service Graph は、エラー率とレイテンシに基づく色分けまたは太さでエッジを可視化し、問題のある Service 間通信を強調表示する**

**解説:**
Tempo の Service Graph（metrics-generator により Span データから生成）は、Service をノード、その通信をエッジとして表示します。エッジにはメトリクスが付加されます。エラー率は色（高エラーは赤）、レイテンシは色のグラデーションまたはツールチップ、リクエスト率はエッジの太さで示されます。この可視化により、問題のある依存関係をすばやく特定できます。Service A から Service B へのエッジが赤い場合は、その特定の通信パスを調査してください。エッジをクリックすると、多くの場合、詳細なメトリクスと関連する Trace へのリンクが表示されます。

</details>

---

4. Span タイムライン（Waterfall View）を使用してボトルネックを特定するにはどうしますか？
   - A) ボトルネックは Span 名だけで特定される
   - B) 親 Span と比べて不釣り合いに長い期間を持つ Span、子 Span 間の大きなギャップ、または並列化できる逐次操作を探す
   - C) Waterfall View にはタイミング情報が表示されない
   - D) ボトルネックは Service Graph でのみ確認できる

<details>
<summary>回答を表示</summary>

**回答: B) 親 Span と比べて不釣り合いに長い期間を持つ Span、子 Span 間の大きなギャップ、または並列化できる逐次操作を探す**

**解説:**
Waterfall View は、タイミングとともに階層的な Span 関係を表示します。ボトルネックの指標には、Trace 期間の大部分を占める長い Span（例: 合計時間の 80% を要するデータベースクエリ）、待機時間（ネットワークレイテンシ、キュー遅延）を示す Span 間のギャップ、並列実行できる逐次的な子 Span、自己時間（子に割り当てられない時間）が長い Span などがあります。Waterfall を視覚的に確認することで、時間が費やされている箇所と実行パターンが最適かどうかを特定できます。

</details>

---

5. Loki から Tempo への TraceID 派生フィールドを相関のために設定するにはどうしますか？
   - A) 設定は不要で、自動的に行われる
   - B) Grafana の Loki データソース設定で、正規表現を使用してログから Trace ID を抽出する派生フィールドを追加し、Tempo データソースへの内部リンクを設定する
   - C) 相関のために別のプラグインをインストールする
   - D) 派生フィールドは外部 URL でのみ機能する

<details>
<summary>回答を表示</summary>

**回答: B) Grafana の Loki データソース設定で、正規表現を使用してログから Trace ID を抽出する派生フィールドを追加し、Tempo データソースへの内部リンクを設定する**

**解説:**
設定手順: Grafana で Loki データソースを編集し、「Derived fields」を見つけます。次の内容でフィールドを追加します。Name（例: "TraceID"）、ログ形式内の Trace ID に一致する Regex（例: `traceID=(\w+)` または `"trace_id":"([^"]+)"`）、有効化した Internal link、リンク先の Tempo データソース、Regex キャプチャグループ（`${__value.raw}`）を使用する Query。ログを表示すると、抽出された Trace ID がクリック可能なリンクになり、Tempo の Explore View で対応する Trace を開きます。

</details>

---

6. Tempo の Span to Logs 機能では何が可能になりますか？
   - A) Span からログを自動生成する
   - B) Trace 内の Span から、時間範囲と Service 名または Trace ID のようなラベルに基づいて、Loki 内の相関するログへ直接移動できる
   - C) ログを完全に Span に置き換える
   - D) CloudWatch Logs でのみ機能する

<details>
<summary>回答を表示</summary>

**回答: B) Trace 内の Span から、時間範囲と Service 名または Trace ID のようなラベルに基づいて、Loki 内の相関するログへ直接移動できる**

**解説:**
Tempo の「Span to Logs」機能（Tempo データソース設定で構成）は、Span から Loki クエリへのリンクを作成します。Trace を表示すると、各 Span には、その Span の時間ウィンドウ、Service 名、および任意で Trace ID を使用して Loki クエリを構築する「Logs」リンクがあります。これにより、Span の実行中に Service が記録した内容を調査でき、エラーの理解や予期しない動作のデバッグに非常に役立ちます。設定では、Span 属性からマッピングする Loki ラベルを指定します。

</details>

---

7. exemplar メカニズムは、メトリクスから Trace へのドリルダウンをどのように可能にしますか？
   - A) exemplar がメトリクスを完全に置き換える
   - B) exemplar は記録時に Trace ID をメトリクスサンプルへ付加し、メトリクスのデータポイントから代表的な Trace へ直接移動できるようにする
   - C) exemplar はカウンターメトリクスでのみ機能する
   - D) タイムスタンプでメトリクスと Trace を手動で相関させる必要がある

<details>
<summary>回答を表示</summary>

**回答: B) exemplar は記録時に Trace ID をメトリクスサンプルへ付加し、メトリクスのデータポイントから代表的な Trace へ直接移動できるようにする**

**解説:**
exemplar はメトリクス観測値に付加されるメタデータ（Trace ID を含む）です。histogram または counter を記録するとき、アプリケーションは現在のリクエストコンテキストから Trace ID を含めます。Grafana では、メトリクスの可視化で exemplar がグラフ上の点として表示されます。exemplar をクリックすると、Tracing バックエンドへのリンクとともにその Trace ID が表示されます。これにより強力なワークフローが実現します。ダッシュボードでレイテンシの急上昇を見つけ、その急上昇の exemplar をクリックすると、そのリクエストが遅かった理由を示す代表的な Trace をすぐに確認できます。

</details>

---

8. RED メトリクスダッシュボードにおいて、Rate、Errors、Duration は何を表しますか？
   - A) ノードのリソース使用率メトリクス
   - B) Rate は毎秒のリクエストスループット、Errors は失敗したリクエストの数または割合、Duration はレスポンスタイムのレイテンシ（通常はパーセンタイル）
   - C) データベース固有のメトリクスのみ
   - D) ネットワーク帯域幅の測定値

<details>
<summary>回答を表示</summary>

**回答: B) Rate は毎秒のリクエストスループット、Errors は失敗したリクエストの数または割合、Duration はレスポンスタイムのレイテンシ（通常はパーセンタイル）**

**解説:**
RED は Service 中心のモニタリング手法です。Rate はスループット（リクエスト/秒）を測定し、「Service はどれだけのトラフィックを処理しているか」に答えます。Errors は失敗率（エラー数または割合）を測定し、「Service はどのくらいの頻度で失敗しているか」に答えます。Duration はレイテンシ分布（p50、p95、p99）を測定し、「リクエストにはどのくらい時間がかかるか」に答えます。これらのメトリクスを組み合わせると、Service の健全性を包括的に可視化できます。Rate が低下した場合は何かがリクエストを妨げており、Errors が急増した場合は何かが失敗しており、Duration が増加した場合は何かが遅くなっています。

</details>

---

9. 99.9% の可用性と 500ms 未満の p99 レイテンシに対する SLI/SLO ダッシュボードゲージを設定するにはどうしますか？
   - A) これらのメトリクスを単一のダッシュボードに表示することはできない
   - B) 現在の SLI 値を計算する PromQL クエリを使用してゲージパネルを作成し、SLO ターゲットに対する緑/黄/赤のゾーンを示すしきい値を設定する
   - C) SLI/SLO ダッシュボードには商用の Grafana ライセンスが必要である
   - D) 手動で入力した値を含む静的テキストパネルを使用する

<details>
<summary>回答を表示</summary>

**回答: B) 現在の SLI 値を計算する PromQL クエリを使用してゲージパネルを作成し、SLO ターゲットに対する緑/黄/赤のゾーンを示すしきい値を設定する**

**解説:**
可用性 SLI の場合: `sum(rate(requests_total{status!~"5.."}[30d])) / sum(rate(requests_total[30d])) * 100` をクエリし、しきい値（緑 >= 99.9%、黄 >= 99.5%、赤 < 99.5%）とともに現在の可用性の割合を表示します。p99 レイテンシの場合: `histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[5m])) by (le)) * 1000`（ms 単位）をクエリし、しきい値（緑 <= 500ms、黄 <= 750ms、赤 > 750ms）を設定します。SLO ターゲットと現在のバーンレートに基づいて残りの予算を示すエラーバジェットパネルを追加します。

</details>

---

10. `db.system` や `db.statement` などのデータベースクエリ Span 属性は、Distributed Tracing でどのように役立ちますか？
    - A) これらはデータベース接続プーリングにのみ使用される
    - B) データベースの種類を識別して実際のクエリを取得するため、Trace 内の遅いクエリ、N+1 問題、データベース関連のボトルネックを特定できる
    - C) これらの属性は OpenTelemetry では非推奨である
    - D) これらは SQL データベースにのみ適用され、NoSQL には適用されない

<details>
<summary>回答を表示</summary>

**回答: B) データベースの種類を識別して実際のクエリを取得するため、Trace 内の遅いクエリ、N+1 問題、データベース関連のボトルネックを特定できる**

**解説:**
OpenTelemetry のセマンティック規約では、標準のデータベース Span 属性を定義しています。`db.system` はデータベースの種類（postgresql、mysql、redis、mongodb）を識別し、`db.statement` はクエリテキスト（セキュリティのためのサニタイズ付き）を含み、`db.operation` は操作の種類（SELECT、INSERT）を示し、`db.name` はデータベース名を示します。これらの属性により、データベースの種類による Trace のフィルタリング、Waterfall View での遅いクエリの特定、N+1 クエリパターン（類似した逐次クエリが多数ある状態）の検出、データベース Span と全体的なリクエストレイテンシの相関付けが可能になります。この可視性はパフォーマンス最適化に不可欠です。

</details>
