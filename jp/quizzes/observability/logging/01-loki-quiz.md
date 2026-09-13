# Grafana Loki クイズ

> **最終更新**: September 13, 2026

[ガイド](../../../observability/logging/01-loki.md)の Loki3.7.7/chart18.12.1 の例に基づいています。

---

1. Loki は TSDB/chunk モデルで主に何を index しますか？

   - A) すべてのログ行のすべての単語
   - B) Stream labels
   - C) request ID のみ
   - D) timestamp のみ

<details>
<summary>回答を表示</summary>

**回答: B**

Labels により、scan する Stream を絞り込めます。これは固定の 10 倍のコスト優位性を証明するものでも、parsing/chunk-read のコストをなくすものでもありません。

</details>

---

2. log Stream を buffer し、有効な場合は WAL に書き込み、chunk を flush する component はどれですか？

   - A) Distributor
   - B) Query frontend
   - C) Ingester
   - D) Index gateway

<details>
<summary>回答を表示</summary>

**回答: C**

Ingester は最近のデータも提供します。WAL には persistent storage が必要であり、それだけで lossless-delivery や HA を保証するものではありません。

</details>

---

3. この章で使用している現在の deployment guidance と一致する記述はどれですか？

   - A) SSD はすべての production EKS cluster に対する恒久的な default である
   - B) 任意の 3 つの Pod は 3-AZ resilience を保証する
   - C) SingleBinary は唯一の chart18.12.1 mode 名である
   - D) SSD は deprecated であり、production の scaling/HA guidance では明示的な operational planning を伴う Distributed が推奨される

<details>
<summary>回答を表示</summary>

**回答: D**

SSD は Loki4.0 で削除予定です。capacity と availability は固定の GB/day table ではなく、workload、storage、topology、検証済みの failure handling に依存します。

</details>

---

4. 5 分間にわたる、条件に一致する error log line の毎秒 rate を返す query はどれですか？

   - A) `rate({app="nginx"} |= "error" [5m])`
   - B) `count({app="nginx"} |= "error")`
   - C) `sum({app="nginx"} |= "error")`
   - D) `increase(count_over_time({app="nginx"}[5m]))`

<details>
<summary>回答を表示</summary>

**回答: A**

これは Stream ごとの log-line rate であり、自動的に HTTP request error ratio になるわけではありません。LogQL には count vector aggregation がありますが、B は必要な metric-vector input を提供しません。

</details>

---

5. 調査のために一意の request ID が必要です。より適切な出発点は何ですか？

   - A) query を高速化するためにすべての request ID を index する
   - B) 必要な ID を access/privacy controls の下で log content または structured metadata に保持する
   - C) すべての cluster/namespace labels を削除する
   - D) total Stream は常に label cardinalities の積に等しいと仮定する

<details>
<summary>回答を表示</summary>

**回答: B**

high-cardinality index values は多数の Stream を作成する可能性があります。structured metadata は redaction ではなく、cardinality の積は観測された組み合わせの上限にすぎません。

</details>

---

6. IRSA の例では、ServiceAccount ownership の一貫性をどのように維持しますか？

   - A) eksctl と Helm の両方で同じ ServiceAccount を作成する
   - B) S3 access keys を Helm values に格納する
   - C) eksctl --role-only を使用し、Helm が一致する annotation 付き ServiceAccount を作成する
   - D) すべての node に bucket policy を付与し、authentication を無効にする

<details>
<summary>回答を表示</summary>

**回答: C**

role trust は、正確な cluster OIDC provider、audience、namespace/service-account subject と一致している必要があります。platform/SDK prerequisites を満たす場合は、Pod Identity も選択肢です。

</details>

---

7. JSON field を filter し、parser failure を除外する query はどれですか？

   - A) `{app="api"} | json | level="error" | __error__=""`
   - B) `{app="api"} | json | where level="error"`
   - C) `{app="api"} | json | select level="error"`
   - D) `{app="api"} | json | filter level="error"`

<details>
<summary>回答を表示</summary>

**回答: A**

LogQL では parsing 後に label-filter stage を使用します。unwrapped numeric metric の場合は、conversion error も除外するために unwrap の後に error filter を配置します。

</details>

---

8. この TSDB deployment における Compactor の役割は何ですか？

   - A) gateway user を authenticate する
   - B) すべての client push request を受信する
   - C) ingestion 後ちょうど 31 日で、すべての log が expire することを保証する
   - D) index file を compact し、retention が有効な場合にマーク済み chunk を非同期で削除する

<details>
<summary>回答を表示</summary>

**回答: D**

これは一般的な small-log-chunk merger ではありません。retention には互換性のある schema/index period、有効な processing、deletion store、durable marker state が必要です。31 日は policy の例です。

</details>

---

9. ingestion429 response の後、最初に何を行うべきですか？

   - A) capacity を測定せずにすべての limit を増やす
   - B) tenant byte rate/burst、per-stream rate、active-stream limit を区別してから、capacity/client retries を確認する
   - C) query timeout のみを増やす
   - D) すべての limit を恒久的に無効にする

<details>
<summary>回答を表示</summary>

**回答: B**

ingestion-rate および burst limit は limits_config にあります。limit を増やすと backend が過負荷になる可能性があり、retry には backoff と上限を設けた loss/buffering policy が必要です。

</details>

---

10. chunk_idle_period と /flush を正しく説明している記述はどれですか？

   - A) どちらも read-only status endpoint である
   - B) chunk_idle_period は log retention period である
   - C) chunk_idle_period は idle flushing を制御し、POST /flush は flush を積極的に trigger する
   - D) chunk_idle_period を短くすると常に total cost が下がる

<details>
<summary>回答を表示</summary>

**回答: C**

idle time を短くすると、より多くの small chunk と object request が発生する可能性があります。flush operation は health check ではなく、readiness は end-to-end durability の証明ではありません。

</details>
