# Grafana Loki クイズ

Grafana Loki についての理解度を確認しましょう。

---

1. Loki が Elasticsearch よりもコスト効率に優れる主な理由は何ですか？

   - A) クエリパフォーマンスが高速である
   - B) ログ内容ではなく label のみをインデックス化する
   - C) より優れた圧縮アルゴリズムを使用する
   - D) Cloud-native 設計である

<details>
<summary>回答を表示</summary>

**回答: B) ログ内容ではなく label のみをインデックス化する**

**解説:**
Loki はログ内容をインデックス化せず、メタデータ（label）のみをインデックス化します。これによりインデックスサイズが大幅に削減され、S3 のような低コストの object storage を使用できるため、Elasticsearch と比較して運用コストを 10 分の 1 に抑えられます。

</details>

---

2. Loki アーキテクチャで、ログデータをメモリにバッファリングして storage に保存するコンポーネントはどれですか？

   - A) Distributor
   - B) Querier
   - C) Ingester
   - D) Compactor

<details>
<summary>回答を表示</summary>

**回答: C) Ingester**

**解説:**
Ingester は Distributor からログデータを受信し、メモリにバッファリングして（chunk を作成）、WAL を管理し、chunk を storage にフラッシュします。また、リアルタイムクエリにも応答します。

</details>

---

3. 本番 EKS 環境で推奨される Loki のデプロイモードはどれですか？

   - A) Monolithic mode
   - B) Simple Scalable mode
   - C) Microservices mode
   - D) Standalone mode

<details>
<summary>回答を表示</summary>

**回答: B) Simple Scalable mode**

**解説:**
Simple Scalable mode はスケーラビリティのために読み取り/書き込みパスを分離しつつ、Microservices mode よりも運用が簡単です。日次ログ量が 100GB から 10TB の大半の本番 EKS クラスターに適しています。

</details>

---

4. 1 秒あたりのエラーログレートを計算する正しい LogQL クエリはどれですか？

   - A) `count({app="nginx"} |= "error")`
   - B) `rate({app="nginx"} |= "error" [5m])`
   - C) `sum({app="nginx"} |= "error")`
   - D) `avg({app="nginx"} |= "error" [5m])`

<details>
<summary>回答を表示</summary>

**回答: B) `rate({app="nginx"} |= "error" [5m])`**

**解説:**
`rate()` 関数は、指定した時間範囲における 1 秒あたりのログ行数を計算します。`[5m]` は 5 分間の範囲を意味します。`count()` はメトリクスクエリでこのようには使用せず、`sum()` と `avg()` もこのように単独では使用しません。

</details>

---

5. Loki の label 設計で避けるべき、高カーディナリティ label の例はどれですか？

   - A) namespace
   - B) app
   - C) pod_name
   - D) environment

<details>
<summary>回答を表示</summary>

**回答: C) pod_name**

**解説:**
pod_name は数千の一意な値を持つ可能性があるため、高カーディナリティ label になります。高カーディナリティ label は stream 数を大幅に増加させ、インデックスサイズの増大とメモリ使用量の増加につながります。namespace、app、environment は通常、値が数十個以下であるため、適切です。

</details>

---

6. EKS で Loki の S3 backend にアクセスする際に推奨される認証方法はどれですか？

   - A) Access Key ID/Secret Access Key
   - B) IAM Roles for Service Accounts (IRSA)
   - C) EC2 Instance Profile
   - D) AWS STS AssumeRole

<details>
<summary>回答を表示</summary>

**回答: B) IAM Roles for Service Accounts (IRSA)**

**解説:**
IRSA は IAM role を Kubernetes Service Account に関連付けるため、Access Key をコードや設定に保存する必要がなくなります。これは最も安全な推奨アプローチであり、EKS 環境でネイティブにサポートされています。

</details>

---

7. JSON ログをパースした後に特定のフィールド値でフィルタリングする正しい LogQL 構文はどれですか？

   - A) `{app="api"} | json | level="error"`
   - B) `{app="api"} | json | filter level="error"`
   - C) `{app="api"} | json | where level="error"`
   - D) `{app="api"} | json | select level="error"`

<details>
<summary>回答を表示</summary>

**回答: A) `{app="api"} | json | level="error"`**

**解説:**
LogQL では、JSON のパース後の label フィルターに `| field_name="value"` 形式を使用します。`filter`、`where`、`select` は LogQL の構文ではありません。

</details>

---

8. Loki Compactor の主な役割では**ない**ものはどれですか？

   - A) 小さな chunk をより大きな chunk にマージする
   - B) 保持ポリシーを適用する（データ削除）
   - C) クライアントからログを受信する
   - D) インデックスの最適化

<details>
<summary>回答を表示</summary>

**回答: C) クライアントからログを受信する**

**解説:**
クライアントからログを受信するのは Distributor の役割です。Compactor はバックグラウンドで保存データを最適化し、保持ポリシーに従って古いデータを削除します。

</details>

---

9. Loki で "rate limit exceeded" エラーが発生した場合、どの設定を調整すべきですか？

   - A) max_streams_per_user
   - B) ingestion_rate_mb, ingestion_burst_size_mb
   - C) max_query_parallelism
   - D) chunk_idle_period

<details>
<summary>回答を表示</summary>

**回答: B) ingestion_rate_mb, ingestion_burst_size_mb**

**解説:**
"Rate limit exceeded" エラーは、ログの取り込みレートが制限を超えた場合に発生します。`ingestion_rate_mb`（1 秒あたりの最大取り込み量）と `ingestion_burst_size_mb`（バースト許容量）を増やすことで解決できます。

</details>

---

10. Loki のパフォーマンスチューニングにおいて、Ingester の `chunk_idle_period` 設定は何を意味しますか？

    - A) chunk の作成から削除までの時間
    - B) アイドル状態の stream がフラッシュされるまでの待機時間
    - C) クエリのタイムアウト時間
    - D) ログの保持期間

<details>
<summary>回答を表示</summary>

**回答: B) アイドル状態の stream がフラッシュされるまでの待機時間**

**解説:**
`chunk_idle_period` は、その stream に新しいログが届かなくなった際に、chunk を storage にフラッシュするまでの待機時間です。この値を小さくするとメモリ使用量は減りますが、小さな chunk が多数作成される可能性があります。

</details>
