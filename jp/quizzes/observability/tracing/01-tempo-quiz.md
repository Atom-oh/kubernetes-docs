# Grafana Tempo クイズ

> **最終更新**: September 13, 2026

ベースライン: Tempo 3.0.3 および chart 3.6.0。

---

1. Tempo のストレージと検索を最も適切に説明しているものはどれですか？

   - A) すべての attribute を Elasticsearch でインデックス化する必要がある
   - B) Object-store の Parquet block は TraceID/TraceQL をサポートするが、ストレージとクエリには依然としてコストがかかる
   - C) ID がわかれば、drop されたすべての span を復元できる
   - D) Tempo は trace を永久に保持する

<details>
<summary>回答を表示</summary>

**回答: B) Object-store の Parquet block は TraceID/TraceQL をサポートするが、ストレージとクエリには依然としてコストがかかる**

専用 column、metadata、cache があっても、インデックス化やクエリのコストがゼロになるわけではありません。正常に ingest され、保持されたデータのみが利用可能です。

</details>

---

2. Tempo 3 の分散 write path が Kafka に commit する前に、trace data を受信して検証する component はどれですか？

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>回答を表示</summary>

**回答: C) Distributor**

Distributor は Kafka に書き込みます。Live-store、block-builder、任意の metrics-generator はそれぞれ個別に consume します。これは Tempo 2 の ingester path ではありません。

</details>

---

3. error status を持つ span を選択する TraceQL query はどれですか？

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>回答を表示</summary>

**回答: B) `{ status = error }`**

Span status の error は、latency threshold や任意の HTTP response condition とは異なります。

</details>

---

4. この EKS/S3 の例では、どの identity configuration を使用していますか？

   - A) Helm values 内の static access key
   - B) すべての workload で共有される node role
   - C) 正確な OIDC sub/aud とスコープを限定した S3 permission で monitoring:tempo に bind された IRSA
   - D) Pod との関連付けがない無関係な ServiceAccount

<details>
<summary>回答を表示</summary>

**回答: C) 正確な OIDC sub/aud とスコープを限定した S3 permission で monitoring:tempo に bind された IRSA**

role annotation とすべての Tempo Pod ServiceAccount は一致している必要があります。他の workload-identity approach には、それぞれ独自の pinned-image compatibility check が必要です。

</details>

---

5. 図示された metrics-generator processor によって trace から生成されないものはどれですか？

   - A) Service graph metrics
   - B) Span metrics
   - C) 任意の application log metrics
   - D) span から導出された rate/error/duration metrics

<details>
<summary>回答を表示</summary>

**回答: C) 任意の application log metrics**

Span-metrics と service-graphs には、明示的な processor activation と remote write が必要です。これらは任意の log を metrics に変換するものではありません。

</details>

---

6. Tempo 3 の durability について正しい記述はどれですか？

   - A) Tempo replica が 3 つあれば、常に loss がゼロであることが保証される
   - B) Microservices は Kafka を使用する。その replication、ISR、retention、recovery は個別に設計する必要がある
   - C) Monolithic mode は常に Kafka を必要とする
   - D) すべての StatefulSet には自動的に永続的な PVC がある

<details>
<summary>回答を表示</summary>

**回答: B) Microservices は Kafka を使用する。その replication、ISR、retention、recovery は個別に設計する必要がある**

chart は live-store/block-builder data に emptyDir を使用します。Kafka durability は Tempo replica 数によって確立されるものではありません。monolithic mode は Kafka を必要としません。

</details>

---

7. 正しい Grafana correlation direction はどれですか？

   - A) 同じ namespace であるだけで correlation が作成される
   - B) Tempo tracesToLogsV2 は Trace→Logs を提供し、Loki derivedFields は Logs→Trace を提供する
   - C) 両方の system が S3 bucket を共有する必要がある
   - D) derivedFields によって application が TraceID を生成する

<details>
<summary>回答を表示</summary>

**回答: B) Tempo tracesToLogsV2 は Trace→Logs を提供し、Loki derivedFields は Logs→Trace を提供する**

identifier、data-source UID、label、クエリ対象の time range は実際の data と一致している必要があります。link では欠落した telemetry を復元できません。

</details>

---

8. Tempo 3 のバックグラウンド compaction および retention 作業を処理する component はどれですか？

   - A) Grafana browser tab
   - B) OTLP client
   - C) Backend scheduler と backend worker
   - D) 変更せずにコピーされた古い compactor configuration

<details>
<summary>回答を表示</summary>

**回答: C) Backend scheduler と backend worker**

これらは古い compactor architecture を置き換えます。retention は非同期であり、独立した包括的な S3 expiration rule は backend operation と競合する可能性があります。

</details>

---

9. `{ resource.service.name = "A" } >> { resource.service.name = "B" }` は何を選択しますか？

   - A) 異なる trace 内の任意の 2 つの span
   - B) 一致する A span の descendant である一致する B
   - C) A parent のみで、B は含まれない
   - D) 直接の B child のみ

<details>
<summary>回答を表示</summary>

**回答: B) 一致する A span の descendant である一致する B**

結果は右辺にあります。直接の child には > を使用します。sibling matching も同一 trace membership test も、同じ意味ではありません。

</details>

---

10. query が遅く、最近の検索結果が空に見える場合に最も安全な最初の対応はどれですか？

   - A) Tempo 2 の `ingester.max_block_duration: 30m` をコピーする
   - B) すべての lag および recent-query protection を無効にする
   - C) tuning の前に time range、実際に受信した data、lag、scan volume、limit を確認する
   - D) 欠落した telemetry と traffic ゼロを、確実に健全な値にする

<details>
<summary>回答を表示</summary>

**回答: C) tuning の前に time range、実際に受信した data、lag、scan volume、limit を確認する**

Tempo 3 では component/default が異なります。空の結果、traffic ゼロ、failure はそれぞれ異なります。configuration の rendering だけでは、production system が動作している証明にはなりません。

</details>

---

[Tempo ガイドを確認する](../../../observability/tracing/01-tempo.md).
