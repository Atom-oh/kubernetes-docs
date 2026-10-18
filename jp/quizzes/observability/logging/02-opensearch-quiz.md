# Amazon OpenSearch Service クイズ

> **最終更新日**: 2026年9月13日

[ガイド](../../../observability/logging/02-opensearch.md)にあるマネージドドメインとデータ収集の例に基づいています。

---

1. OpenSearch と Amazon OpenSearch Service の違いを正しく説明しているのはどれですか？

   - A) すべての Elasticsearch クライアントやプラグインとの互換性が保たれる
   - B) AWS は上流のすべてのリリースを即座にサポートする
   - C) OpenSearch は Apache-2.0 ライセンスのプロジェクトであり、マネージドサービスは選定されたエンジンバージョンをサポートする
   - D) このサービスは Kibana をホスティングするだけの製品である

<details>
<summary>回答を表示</summary>

**回答: C**

Elasticsearch 7.10 から派生したというだけで、あらゆるクライアントとの互換性が保証されるわけではありません。AWS がサポートするバージョンと、実際に使うクライアントやプラグインを確認してください。旧基準の 2.11 は、2027年11月7日まで標準サポートの対象です。

</details>

---

2. 専用の cluster-manager ノードを構成した場合、クラスター状態とシャード割り当てを管理するのはどのロールですか？

   - A) 専用の cluster-manager ノード
   - B) UltraWarm ストレージ
   - C) コールドストレージ
   - D) ログ収集エージェント

<details>
<summary>回答を表示</summary>

**回答: A**

AWS の設定フィールドでは、現在も `dedicated_master` という名前が使われています。マネージャーノードの数とデータレプリカ数は別の設定です。また、ゾーン認識を有効にするだけでは Multi-AZ with Standby にはなりません。

</details>

---

3. 従来の UltraWarm とコールドストレージについて、正しい記述はどれですか？

   - A) UltraWarm はすべてのデータを EBS だけに保存する
   - B) どちらも S3 を利用しており、コールドインデックスは検索前に UltraWarm へ接続する必要がある
   - C) どのワークロードでも必ず 75% のコストを削減できる
   - D) すべてのインスタンスとエンジンの組み合わせが両方の階層に対応する

<details>
<summary>回答を表示</summary>

**回答: B**

hot→UltraWarm→cold のライフサイクルを設定するには、サービス側の前提条件を満たし、移行に必要な容量を確保する必要があります。コストと検索遅延はワークロードによって異なり、階層の名称だけで一定の削減率が保証されるわけではありません。

</details>

---

4. OpenSearch Service のマネージドコールドストレージからインデックスを削除する ISM アクションはどれですか？

   - A) すべてのストレージ階層で使う `delete`
   - B) `force_merge`
   - C) `warm_migration`
   - D) `cold_delete`

<details>
<summary>回答を表示</summary>

**回答: D**

マネージドコールドストレージから削除するには `cold_delete` が必要です。ポリシーの各アクションオブジェクトには1つのアクションを指定し、処理は非同期で実行されます。例の7/30/90日はインデックスの経過日数であり、イベント発生時刻から正確にその期間だけデータを保持する保証ではありません。

</details>

---

5. Fluent Bit による直接配信と Amazon Data Firehose は、どのように比較すべきですか？

   - A) Firehose が常に最も安価である
   - B) Fluent Bit による直接配信では AWS 認証を利用できない
   - C) 運用要件、データ形式、バッファリング/再試行/バックアップ、アクセス制御、実測コストを比較する
   - D) どちらも同じ Kubernetes メタデータを自動的に付与する

<details>
<summary>回答を表示</summary>

**回答: C**

Firehose はマネージドな配信経路を提供しますが、適切なロール、接続性、対応する形式のレコードが必要です。バックアップ方式は `FailedDocumentsOnly` で選択します。`failed/` という名前のプレフィックスを使うだけでは、その方式は有効になりません。

</details>

---

6. DLS と FLS を正しく説明しているものはどれですか？

   - A) DLS は返すドキュメントを絞り込み、FLS は返すフィールドを制御する。適用されるロールと信頼できるメタデータも重要である
   - B) FLS が Kubernetes の namespace を自動的に認証する
   - C) URI ベースの IAM だけで、bulk body 内に指定されたすべてのインデックスを制限できる
   - D) セキュリティグループのルールでドキュメント単位の読み取り権限を付与できる

<details>
<summary>回答を表示</summary>

**回答: A**

ガイドでは信頼できる `kubernetes.namespace_name` メタデータを使っています。制限付きロールを追加しても、すでに付与されている広範な権限は取り消されません。また、FLS は許可されたメッセージ内の機微なテキストを伏せたり、保存済みデータやバックアップを削除したりする機能ではありません。

</details>

---

7. 完全一致検索と一般的なフィールド集計に対応する、マッピング上の文字列型はどれですか？

   - A) サブフィールドのない `text`
   - B) `keyword`
   - C) OpenSearch の型である LowCardinality
   - D) マッピングされていないフィールドのみ

<details>
<summary>回答を表示</summary>

**回答: B**

`keyword` は、解析処理を行う `text` とも、ClickHouse の LowCardinality とも異なります。keyword 型や数値型の集計の多くは列指向の doc values を使うため、毎回すべての `_source` ドキュメントを読み取るわけではありません。

</details>

---

8. `Logstash_Format On` と `logs-production` プレフィックスを設定した場合、例の Fluent Bit 出力先はどこですか？

   - A) 常にロールオーバー用エイリアスへ書き込む
   - B) 自動的に Serverless コレクションへ書き込む
   - C) 切り離されたコールドインデックスへ直接書き込む
   - D) 日付を含む `logs-production-YYYY.MM.DD` インデックスへ書き込む

<details>
<summary>回答を表示</summary>

**回答: D**

エイリアスが存在するだけでは、そのエイリアスは選択されません。ガイドでは日次インデックスへの出力と、ロールオーバー用エイリアスの設定、番号付きインデックス、書き込みエイリアスを必要とする `rollover-logs-*` への出力を区別しています。

</details>

---

9. マッピング済みのエラーログ行を直近1時間に絞り込む Query DSL はどれですか？

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>回答を表示</summary>

**回答: C**

例のマッピングでは、アプリケーションのフィールドを `app` の下に配置し、`@timestamp` を使います。filter コンテキストでは、関連度スコアを計算せずに `keyword` の完全一致と時間範囲を組み合わせられます。

</details>

---

10. ログ処理に OpenSearch、Loki、ClickHouse のどれを選ぶか、妥当に判断する基準は何ですか？

   - A) 1日100 GB という、どこにでも当てはまる切り替え基準
   - B) どの組織でもクエリの種類や割合は同じだという前提
   - C) コストは3〜5倍、削減率は60〜80%という固定ルール
   - D) 代表的なクエリを使い、保持期間、耐久性、権限、運用体制、実測コストも含めて比較する

<details>
<summary>回答を表示</summary>

**回答: D**

3つの製品はそれぞれ、インデックス化や検索の方式、運用上のトレードオフが異なります。同等の要件を基に比較し、移行、データの突き合わせ、ロールバックを検証してください。どの製品を選んでも、コンプライアンスへの適合や最低コストが自動的に保証されるわけではありません。

</details>
