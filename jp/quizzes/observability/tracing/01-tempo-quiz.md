# Grafana Tempo クイズ

Grafana Tempo に関する理解度を確認しましょう。

---

1. Grafana Tempo の主な特徴は何ですか？
   - A) 高速検索のためにすべてのデータをIndex化する
   - B) Indexing コストを不要にする TraceID ベースのストレージ
   - C) リアルタイムのストリーミング処理
   - D) 自動異常検知

<details>
<summary>回答を表示</summary>

**回答: B) Indexing コストを不要にする TraceID ベースのストレージ**

**解説:**
Tempo は Indexing を行わず、TraceID のみを使用してトレースデータを保存・検索します。これにより、大規模なトレースデータを低コストで保存できます。ほかの tracing システムでは検索性能を向上させるためにさまざまなフィールドをIndex化しますが、その結果ストレージコストが増加します。

</details>

---

2. Tempo のアーキテクチャで、トレースデータを受信して検証するコンポーネントはどれですか？
   - A) Ingester
   - B) Querier
   - C) Distributor
   - D) Compactor

<details>
<summary>回答を表示</summary>

**回答: C) Distributor**

**解説:**
Distributor はさまざまな形式（Jaeger、Zipkin、OTLP など）のトレースデータを受信して検証します。検証済みのデータは、hashing に基づいて適切な Ingester に分散されます。Ingester はデータをバッファリングして保存し、Querier は検索を処理します。

</details>

---

3. error ステータスの span のみを取得する正しい TraceQL クエリはどれですか？
   - A) `{ error = true }`
   - B) `{ status = error }`
   - C) `{ span.error = 1 }`
   - D) `{ state = "ERROR" }`

<details>
<summary>回答を表示</summary>

**回答: B) { status = error }**

**解説:**
TraceQL では、`{ status = error }` 構文を使用して error span をフィルタリングします。status フィールドには ok、error、unset の値を指定でき、OpenTelemetry の SpanStatus に対応します。

</details>

---

4. S3 を Tempo のバックエンドストレージとして使用する場合に推奨される AWS 認証方法はどれですか？
   - A) Access Key を環境変数に保存する
   - B) 認証情報を Secret に保存する
   - C) IRSA (IAM Roles for Service Accounts)
   - D) EC2 Instance Profile

<details>
<summary>回答を表示</summary>

**回答: C) IRSA (IAM Roles for Service Accounts)**

**解説:**
IRSA は EKS 環境で推奨されます。IRSA は IAM role を Kubernetes ServiceAccount に関連付け、Pod レベルでのきめ細かな権限管理を可能にします。静的な認証情報を保存するより安全であり、認証情報のローテーションも自動で処理されます。

</details>

---

5. Tempo の Metrics Generator が生成する metric type ではないものはどれですか？
   - A) Service Graph metrics
   - B) Span metrics
   - C) Log metrics
   - D) RED metrics (Rate, Error, Duration)

<details>
<summary>回答を表示</summary>

**回答: C) Log metrics**

**解説:**
Tempo の Metrics Generator は、トレースデータから Service Graph metrics と Span metrics（RED metrics を含む）を生成します。これらの metrics は Prometheus に送信され、service map の可視化とパフォーマンス監視に使用されます。Log metrics は Loki によって生成され、Tempo の対象範囲外です。

</details>

---

6. Tempo Distributed mode で、データ耐久性のために複数の Ingester 間で replica を維持する機能の名称は何ですか？
   - A) Sharding
   - B) Replication Factor
   - C) Partitioning
   - D) Mirroring

<details>
<summary>回答を表示</summary>

**回答: B) Replication Factor**

**解説:**
Replication Factor は、各 trace を何個の Ingester に複製するかを決定します。たとえば、replication_factor=3 は各 trace が 3 つの Ingester に保存されることを意味するため、1 つの Ingester に障害が発生してもデータは失われません。これは Tempo の高可用性構成における重要な設定です。

</details>

---

7. Grafana で Tempo と Loki を統合して Trace-to-Log correlation を実装するには、どの設定が必要ですか？
   - A) 同じ namespace にデプロイする
   - B) TraceID を抽出するよう derivedFields を設定する
   - C) 同じ S3 bucket を使用する
   - D) 同一の label を使用する

<details>
<summary>回答を表示</summary>

**回答: B) TraceID を抽出するよう derivedFields を設定する**

**解説:**
Loki data source の設定で derivedFields を構成し、ログから TraceID を抽出して Tempo へのリンクを作成します。regex pattern で TraceID を照合して Tempo data source にリンクすることで、ログから関連する trace を直接クエリできます。

</details>

---

8. Tempo における Compactor の役割は何ですか？
   - A) リアルタイムのクエリ処理
   - B) トレースデータの受信と分散
   - C) 保存された block の圧縮と retention policy の適用
   - D) メモリバッファの管理

<details>
<summary>回答を表示</summary>

**回答: C) 保存された block の圧縮と retention policy の適用**

**解説:**
Compactor は Object Storage に保存された trace block を圧縮・最適化します。また、block_retention 設定に従って retention policy を適用し、古いデータを削除します。Compactor は通常 single instance として実行され、cluster ごとにアクティブなのは 1 つだけです。

</details>

---

9. Service A から Service B への呼び出しパターンを検索する正しい TraceQL クエリはどれですか？
   - A) `{ resource.service.name = "A" } AND { resource.service.name = "B" }`
   - B) `{ resource.service.name = "A" } >> { resource.service.name = "B" }`
   - C) `{ resource.service.name = "A" } -> { resource.service.name = "B" }`
   - D) `{ resource.service.name = "A" } | { resource.service.name = "B" }`

<details>
<summary>回答を表示</summary>

**回答: B) { resource.service.name = "A" } >> { resource.service.name = "B" }**

**解説:**
TraceQL では、`>>` 演算子が構造的なマッチングを行い、最初の条件に一致する span が 2 番目の条件に一致する span の ancestor であるケースを検索します。これにより、Service 間の呼び出しパターンを分析できます。`>` 演算子は直接の parent-child relationship のみを照合します。

</details>

---

10. Tempo のパフォーマンス最適化で推奨されない設定はどれですか？
    - A) max_block_duration を 30 分に設定する
    - B) cache として Memcached を使用する
    - C) すべての attribute をIndex化する
    - D) Query Frontend で query sharding を有効化する

<details>
<summary>回答を表示</summary>

**回答: C) すべての attribute をIndex化する**

**解説:**
Tempo の中核となる設計原則は、コストを削減するために Indexing を最小限に抑えることです。すべての attribute をIndex化すると Tempo の利点が損なわれ、ストレージコストが大幅に増加します。代わりに、max_block_duration のチューニング、caching、query sharding によってパフォーマンスを最適化します。

</details>

---
