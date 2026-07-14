# Amazon OpenSearch Service クイズ

Amazon OpenSearch Service の理解度を確認しましょう。

---

1. Amazon OpenSearch Service はどのオープンソースプロジェクトをベースにしていますか？

   - A) Apache Solr
   - B) Elasticsearch 7.10 のフォーク
   - C) Apache Lucene 単体
   - D) Splunk のオープンソース版

<details>
<summary>回答を表示</summary>

**回答: B) Elasticsearch 7.10 のフォーク**

**解説:**
OpenSearch は、AWS が Apache 2.0 ライセンスの下で Elasticsearch 7.10 をフォークして 2021 年に作成したオープンソースプロジェクトです。Elastic のライセンス変更（SSPL）への対応として開始されました。

</details>

---

2. OpenSearch Cluster で、index metadata 管理と cluster state 管理を担う Node タイプはどれですか？

   - A) Data Node
   - B) Master Node
   - C) UltraWarm Node
   - D) Coordinating Node

<details>
<summary>回答を表示</summary>

**回答: B) Master Node**

**解説:**
Master Node は、cluster state 管理、index の作成・削除、shard allocation の判断などの Cluster 管理タスクを処理します。本番環境では、専用 Master Node を 3 台使用することが推奨されます。

</details>

---

3. OpenSearch で費用対効果に優れた読み取り専用の storage tier はどれですか？

   - A) Hot Storage
   - B) Warm Storage
   - C) UltraWarm
   - D) Standard Storage

<details>
<summary>回答を表示</summary>

**回答: C) UltraWarm**

**解説:**
UltraWarm は S3 ベースの読み取り専用 storage tier であり、Hot storage（EBS）より約 75% 低コストです。頻繁に query されない過去の log data の保存に適しています。

</details>

---

4. ISM（Index State Management）policy の主な目的は何ですか？

   - A) index security settings の管理
   - B) index lifecycle（rollover、削除など）の自動化
   - C) index query の最適化
   - D) index replication の設定

<details>
<summary>回答を表示</summary>

**回答: B) index lifecycle（rollover、削除など）の自動化**

**解説:**
ISM policy は index lifecycle を自動管理します。index rollover、Hot→UltraWarm→Cold への移行、retention period 経過後の削除を自動化できます。

</details>

---

5. OpenSearch の log collection method のうち、最も費用対効果が高く管理が容易なものはどれですか？

   - A) EC2 上の Logstash
   - B) FluentBit DaemonSet + 直接送信
   - C) Kinesis Data Firehose
   - D) Lambda functions

<details>
<summary>回答を表示</summary>

**回答: C) Kinesis Data Firehose**

**解説:**
Kinesis Data Firehose は、buffering、compression、batch processing を自動的に実行するフルマネージドサービスです。組み込みの S3 backup と error handling により、運用負荷が低く、大規模な log collection において費用対効果に優れています。

</details>

---

6. OpenSearch Fine-Grained Access Control（FGAC）で、特定の Namespace の log へのアクセスのみを制限する機能はどれですか？

   - A) Field-Level Security (FLS)
   - B) Document-Level Security (DLS)
   - C) Index-Level Security
   - D) Cluster-Level Security

<details>
<summary>回答を表示</summary>

**回答: B) Document-Level Security (DLS)**

**解説:**
Document-Level Security（DLS）は、特定の条件に一致する document へのアクセスのみを制限します。たとえば、条件 `kubernetes.namespace: "team-a"` を使用して、特定の team の log のみへのアクセスを設定できます。

</details>

---

7. OpenSearch index template で、`LowCardinality` の代わりに使用される Elasticsearch/OpenSearch の string optimization type はどれですか？

   - A) text
   - B) keyword
   - C) analyzed_string
   - D) compact_string

<details>
<summary>回答を表示</summary>

**回答: B) keyword**

**解説:**
OpenSearch では、低 cardinality の string field（namespace、level など）に `keyword` type を使用します。`text` type は full-text search 用に tokenization される一方、`keyword` は exact match と aggregation 向けに最適化されています。

</details>

---

8. OpenSearch の cost optimization における正しい storage tiering の順序はどれですか？

   - A) Cold → UltraWarm → Hot
   - B) Hot → Cold → UltraWarm
   - C) Hot → UltraWarm → Cold
   - D) UltraWarm → Hot → Cold

<details>
<summary>回答を表示</summary>

**回答: C) Hot → UltraWarm → Cold**

**解説:**
data はまず高速な query のために Hot storage（EBS）に保存され、時間の経過とともに UltraWarm（読み取り専用）へ移動し、最後に古い data のために Cold Storage（S3）へ移動します。この順に cost は低下します。

</details>

---

9. OpenSearch で特定の時間範囲内の error log を検索するための正しい Query DSL はどれですか？

   - A) `{"query": {"match": {"level": "error", "time": "1h"}}}`
   - B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`
   - C) `{"filter": {"level": "error", "time": "> now-1h"}}`
   - D) `{"search": {"level": "error", "since": "1h"}}`

<details>
<summary>回答を表示</summary>

**回答: B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`**

**解説:**
OpenSearch Query DSL では、複数の条件を組み合わせるために `bool` query を使用します。`must` array には、`match`（text matching）と `range`（time range）の両方の指定が含まれます。

</details>

---

10. OpenSearch と Loki を比較した場合、OpenSearch がより適している use case はどれですか？

    - A) cost optimization が最優先の startup
    - B) full-text search と複雑な analytical query が必要なケース
    - C) 既存の Grafana stack との integration
    - D) 単純な log filtering のみが必要なケース

<details>
<summary>回答を表示</summary>

**回答: B) full-text search と複雑な analytical query が必要なケース**

**解説:**
OpenSearch は、強力な Lucene ベースの full-text search 機能と複雑な aggregation query をサポートしています。security analysis（SIEM）、compliance、複雑な log analysis に適しています。cost optimization や単純な filtering には、Loki の方が適しています。

</details>
