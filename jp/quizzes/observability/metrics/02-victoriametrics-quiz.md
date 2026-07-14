# VictoriaMetrics クイズ

VictoriaMetrics についての理解度を確認しましょう。

---

1. Prometheus と比較した VictoriaMetrics の主な利点では**ない**ものはどれですか？
   - A) 最大 7 倍効率的なデータ圧縮
   - B) 複雑なクエリで最大 20 倍高速なパフォーマンス
   - C) 別のクエリ言語を学ぶ必要がある
   - D) 水平スケーリング機能

<details>
<summary>回答を表示</summary>

**答え: C) 別のクエリ言語を学ぶ必要がある**

**解説:**
VictoriaMetrics は PromQL のスーパーセットである MetricsQL クエリ言語を使用します。既存の PromQL クエリはすべて動作し、追加の便利な機能のみを提供します。したがって、別のクエリ言語を学ぶ必要はありません。

</details>

---

2. VictoriaMetrics の cluster mode のコンポーネントでは**ない**ものはどれですか？
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmoperator

<details>
<summary>回答を表示</summary>

**答え: D) vmoperator**

**解説:**
VictoriaMetrics の cluster mode は、vminsert（書き込みリクエストのルーティング）、vmstorage（データストレージ）、vmselect（クエリ処理）の 3 つのコアコンポーネントで構成されます。vmoperator は cluster mode のコアコンポーネントではなく、別の Kubernetes Operator です。

</details>

---

3. vmagent の主な役割は何ですか？
   - A) 長期データストレージ
   - B) ダッシュボードのレンダリング
   - C) Metric の収集と Remote Write による送信
   - D) Alert のルーティング

<details>
<summary>回答を表示</summary>

**答え: C) Metric の収集と Remote Write による送信**

**解説:**
vmagent は Metric を収集し、VictoriaMetrics または他のリモートストレージに送信する軽量なエージェントです。Prometheus の scrape 設定と互換性があり、データバッファリング、再送信、label relabeling などの機能を提供します。

</details>

---

4. MetricsQL の `keep_last_value()` 関数の目的は何ですか？
   - A) 最大値を保持する
   - B) 最後の値を保持する（ギャップの補完）
   - C) 最初の値を保持する
   - D) 平均値を保持する

<details>
<summary>回答を表示</summary>

**答え: B) 最後の値を保持する（ギャップの補完）**

**解説:**
`keep_last_value()` は、時系列データ内の欠損値（ギャップ）を最後に判明している値で補完する MetricsQL 拡張関数です。scrape の失敗または一時的なデータ損失が発生した場合に、ダッシュボードや Alert のギャップを防ぐために役立ちます。

</details>

---

5. VictoriaMetrics における `--dedup.minScrapeInterval` フラグの役割は何ですか？
   - A) 最小 scrape 間隔を設定する
   - B) 指定した間隔内の重複サンプルを削除する
   - C) データ圧縮間隔を設定する
   - D) Alert 評価間隔を設定する

<details>
<summary>回答を表示</summary>

**答え: B) 指定した間隔内の重複サンプルを削除する**

**解説:**
`--dedup.minScrapeInterval` は、指定した時間間隔内にある同一時系列の重複サンプルを削除します。たとえば、`--dedup.minScrapeInterval=30s` は 30 秒以内の重複データポイントを 1 つに統合します。同じ target を複数の Prometheus インスタンスが scrape する HA 構成で役立ちます。

</details>

---

6. vmsingle と vmcluster を選択する際の正しい基準は何ですか？
   - A) 常に vmcluster を使用する
   - B) 高可用性の要件がなく、1 日あたりのサンプル数が 100M 未満の場合は vmsingle を推奨する
   - C) vmsingle はクエリ機能をサポートしていない
   - D) vmcluster は単一ノードでのみ動作する

<details>
<summary>回答を表示</summary>

**答え: B) 高可用性の要件がなく、1 日あたりのサンプル数が 100M 未満の場合は vmsingle を推奨する**

**解説:**
vmsingle（single-node mode）は設定が簡単で、小規模から中規模の環境に適しています。1 日あたりのサンプル数が 100M 未満で、高可用性が必須でない場合は vmsingle を推奨します。大規模な環境、または高可用性が必要な場合は vmcluster を使用してください。

</details>

---

7. VictoriaMetrics cluster での `replicationFactor=2` 設定は何を意味しますか？
   - A) 2 つの storage node のみを使用する
   - B) 各データポイントを 2 つの storage node にレプリケートする
   - C) 2 つの node でのみクエリを実行する
   - D) 2 倍の圧縮を適用する

<details>
<summary>回答を表示</summary>

**答え: B) 各データポイントを 2 つの storage node にレプリケートする**

**解説:**
`replicationFactor=2` は、各データポイントを 2 つの vmstorage node にレプリケートするよう vminsert を設定します。これにより、1 つの storage node に障害が発生しても、データを失わずにサービスを継続できます。これは高可用性のための推奨設定です。

</details>

---

8. MetricsQL の `default` 演算子の目的は何ですか？
   - A) デフォルトの label を設定する
   - B) 結果がない場合にデフォルト値を返す
   - C) デフォルトの集約関数を設定する
   - D) デフォルトの時間範囲を設定する

<details>
<summary>回答を表示</summary>

**答え: B) 結果がない場合にデフォルト値を返す**

**解説:**
MetricsQL の `default` 演算子は、クエリ結果が空または NaN の場合にデフォルト値を返します。たとえば、`rate(http_requests_total[5m]) / rate(http_requests_total[5m]) default 0` は、ゼロ除算エラーの代わりに 0 を返します。PromQL では、この処理に複雑な条件分岐が必要です。

</details>

---

9. vmalert の正しい役割は何ですか？
   - A) Metric の収集
   - B) データストレージ
   - C) Alert rule の評価と Alert の生成
   - D) ダッシュボードの作成

<details>
<summary>回答を表示</summary>

**答え: C) Alert rule の評価と Alert の生成**

**解説:**
vmalert は Alert rule を評価し、条件が満たされた場合に Alertmanager に Alert を送信します。これは Prometheus の alerting 機能に似ています。VictoriaMetrics または Prometheus をデータソースとして使用でき、recording rule もサポートしています。

</details>

---

10. VictoriaMetrics における vmbackup の主な目的は何ですか？
    - A) リアルタイムのデータレプリケーション
    - B) オブジェクトストレージにバックアップを作成する
    - C) ログのバックアップ
    - D) 設定ファイルのバックアップ

<details>
<summary>回答を表示</summary>

**答え: B) オブジェクトストレージにバックアップを作成する**

**解説:**
vmbackup は、VictoriaMetrics のデータを S3、GCS、Azure Blob などのオブジェクトストレージにバックアップするツールです。snapshot 機能を使用して一貫性のあるバックアップを作成し、vmrestore を使用して復元できます。これは災害復旧とデータ保護に不可欠なツールです。

</details>

---
