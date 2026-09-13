# Amazon OpenSearch Service クイズ

> **最終更新**: September 13, 2026

[ガイド](../../../observability/logging/02-opensearch.md)の managed domain および collector の例に基づいています。

---

1. OpenSearch と Amazon OpenSearch Service の違いを正しく説明しているのはどれですか？

   - A) すべての Elasticsearch client/plugin が互換のまま利用できる
   - B) AWS はすべての upstream リリースを即座にサポートする
   - C) OpenSearch は Apache-2.0 のプロジェクトであり、managed service は選定されたエンジンバージョンをサポートする
   - D) このサービスは Kibana のホスティング製品にすぎない

<details>
<summary>回答を表示</summary>

**回答: C**

Elasticsearch 7.10 系の系譜は、包括的な互換性の保証ではありません。AWS のバージョンサポート状況と、実際に使う client/plugin を確認してください。以前の 2.11 ベースラインは 2027 年 11 月 7 日まで標準サポートが継続されます。

</details>

---

2. 専用の cluster-manager node を構成した場合、cluster state と shard 割り当ての管理を担うロールはどれですか？

   - A) 専用の cluster-manager node
   - B) UltraWarm storage
   - C) Cold storage
   - D) log collector

<details>
<summary>回答を表示</summary>

**回答: A**

AWS の設定フィールドでは今も dedicated_master という名称が使われています。manager の数は data replica の数とは別物であり、zone awareness だけでは Multi-AZ with Standby は有効になりません。

</details>

---

3. 従来の UltraWarm と cold storage について正しい記述はどれですか？

   - A) UltraWarm はすべてを EBS 上にのみ保存する
   - B) いずれも S3 backed であり、cold index はクエリする前に UltraWarm へ attach する必要がある
   - C) すべてのワークロードでちょうど 75% 削減できる
   - D) すべての instance / エンジンの組み合わせが両方の tier をサポートする

<details>
<summary>回答を表示</summary>

**回答: B**

hot→UltraWarm→cold のポリシーには、該当するサービスの前提条件と移行のためのキャパシティが必要です。コストとクエリレイテンシはワークロードによって変わり、tier の名称が一定の削減率を保証するものではありません。

</details>

---

4. managed な OpenSearch Service の cold storage から index を削除する ISM アクションはどれですか？

   - A) すべての storage tier における delete
   - B) force_merge
   - C) warm_migration
   - D) cold_delete

<details>
<summary>回答を表示</summary>

**回答: D**

managed な cold storage では cold_delete が必要です。ポリシーは 1 つの action オブジェクトにつき 1 アクションを使用し、非同期に実行されます。例に出てくる 7/30/90 日という index の経過日数は、イベント発生時刻を基準にした厳密な保持期間の保証ではありません。

</details>

---

5. Fluent Bit からの直接配信と Amazon Data Firehose はどのように比較すべきですか？

   - A) Firehose が常に最も安価な選択肢である
   - B) Fluent Bit からの直接配信では AWS に対して認証できない
   - C) 運用要件、スキーマ、buffering/retry/backup、アクセス、そして実測コストを比較する
   - D) どちらも同一の Kubernetes メタデータを自動的に作成する

<details>
<summary>回答を表示</summary>

**回答: C**

Firehose は managed な配信経路を提供しますが、ロール、接続性、互換性のあるレコードが必要です。backup モードは FailedDocumentsOnly で選択するものであり、failed/ という名前の prefix だけでその挙動が選ばれるわけではありません。

</details>

---

6. DLS と FLS を正しく説明しているのはどれですか？

   - A) DLS はドキュメントを絞り込み、FLS は返されるフィールドを制御する。実効ロールと信頼できるメタデータは依然として重要である
   - B) FLS が Kubernetes namespace を自動的に認証する
   - C) URI ベースの IAM だけで、bulk body の内部で指定されたすべての index を制限できる
   - D) security group のルールがドキュメントレベルの読み取りアクセスを付与する

<details>
<summary>回答を表示</summary>

**回答: A**

ガイドでは信頼できる kubernetes.namespace_name メタデータを使用しています。制限されたロールを付与しても、既存のより広い権限は打ち消されません。また FLS は、許可された message の中にある機微なテキストをマスクしたり、保存済みのデータや backup を削除したりはしません。

</details>

---

7. 完全一致の検索と一般的なフィールド集計をサポートする、mapping 上の文字列型はどれですか？

   - A) subfield のない text
   - B) keyword
   - C) OpenSearch の型としての LowCardinality
   - D) mapping されていないフィールドのみ

<details>
<summary>回答を表示</summary>

**回答: B**

keyword は、analyze される text とも ClickHouse の LowCardinality とも異なります。keyword や数値の集計の多くは列指向の doc values を使うため、常に完全な _source ドキュメントをすべて scan するわけではありません。

</details>

---

8. Logstash_Format On と prefix logs-production の設定では、例に示された Fluent Bit の output はどこへ書き込みますか？

   - A) 常に rollover alias へ
   - B) 自動的に Serverless collection へ
   - C) detach された cold index へ直接
   - D) 日付ベースの logs-production-YYYY.MM.DD index へ

<details>
<summary>回答を表示</summary>

**回答: D**

alias が存在するだけで、それが選ばれるわけではありません。ガイドでは日次 index の経路と、rollover alias の設定・番号付き index・write alias を必要とする rollover-logs-* の経路を区別しています。

</details>

---

9. 直近 1 時間の、mapping された error ログ行を絞り込む Query DSL はどれですか？

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>回答を表示</summary>

**回答: C**

例の mapping ではアプリケーションのフィールドを app 配下にネストし、@timestamp を使用しています。filter context では、関連度スコアリングを必要とせずに keyword の完全一致と時間範囲を組み合わせられます。

</details>

---

10. ログのワークロードに対して OpenSearch、Loki、ClickHouse を選定する際の妥当な判断基準は何ですか？

   - A) 1 日 100GB という普遍的な切り替え基準
   - B) すべての組織でクエリの構成は同じだという主張
   - C) コストは 3〜5 倍、削減率は 60〜80% という固定のルール
   - D) 代表的なクエリに加えて、保持期間、耐久性、権限、運用能力、そして実測コスト

<details>
<summary>回答を表示</summary>

**回答: D**

3 つはいずれも indexing / クエリのモデルと運用上のトレードオフが異なります。同等の要件で比較し、移行・整合性確認・ロールバックを検証してください。コンプライアンスや最小コストを自動的に成立させる製品はありません。

</details>
