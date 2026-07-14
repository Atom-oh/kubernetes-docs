# Log Collector 比較クイズ

Log Collector（FluentBit、Promtail、Alloy、OTEL Collector）についての理解度を確認しましょう。

---

1. 次の Log Collector のうち、メモリ使用量が最も低いものはどれですか？

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) OpenTelemetry Collector

<details>
<summary>回答を表示</summary>

**回答: B) FluentBit**

**解説:**
FluentBit は C で書かれており、約 10～50MB と最も低いメモリ使用量です。その他は Go で書かれており、約 50～100MB のメモリを使用します。

</details>

---

2. ログに Kubernetes metadata（namespace、pod_name など）を追加する FluentBit FILTER はどれですか？

   - A) [FILTER] Name modify
   - B) [FILTER] Name kubernetes
   - C) [FILTER] Name parser
   - D) [FILTER] Name record_modifier

<details>
<summary>回答を表示</summary>

**回答: B) [FILTER] Name kubernetes**

**解説:**
FluentBit の `kubernetes` filter は、Kubernetes API を通じて pod、namespace、labels などの metadata をログに自動的に追加します。

</details>

---

3. Promtail の主な制限は何ですか？

   - A) JSON 解析をサポートしていない
   - B) Loki 以外の送信先に送信できない
   - C) Kubernetes 環境で使用できない
   - D) 複数行ログを処理できない

<details>
<summary>回答を表示</summary>

**回答: B) Loki 以外の送信先に送信できない**

**解説:**
Promtail は Grafana Loki 専用エージェントとして設計されており、OpenSearch や CloudWatch などの他の送信先への送信をサポートしていません。複数の送信先が必要な場合は、FluentBit または OTEL Collector を使用してください。

</details>

---

4. Grafana Alloy はどの設定言語を使用しますか？

   - A) YAML
   - B) JSON
   - C) River (HCL-like)
   - D) INI

<details>
<summary>回答を表示</summary>

**回答: C) River (HCL-like)**

**解説:**
Grafana Alloy は、HCL（HashiCorp Configuration Language）に似た設定言語である River を使用します。YAML より表現力が高く、再利用可能なコンポーネントを定義できます。

</details>

---

5. OpenTelemetry Collector の pipeline コンポーネントの順序は何ですか？

   - A) Processors → Receivers → Exporters
   - B) Receivers → Exporters → Processors
   - C) Receivers → Processors → Exporters
   - D) Exporters → Processors → Receivers

<details>
<summary>回答を表示</summary>

**回答: C) Receivers → Processors → Exporters**

**解説:**
OTEL Collector pipelines は次の順序で構成されます: Receivers（データを受信） → Processors（データを処理・変換） → Exporters（データを送信）。

</details>

---

6. FluentBit で複雑なログ処理ロジックを実装するために使用できるスクリプト言語は何ですか？

   - A) Python
   - B) JavaScript
   - C) Lua
   - D) Ruby

<details>
<summary>回答を表示</summary>

**回答: C) Lua**

**解説:**
FluentBit は Lua scripting をサポートしており、複雑なログ処理ロジック（field transformation、条件付き処理、sensitive data masking など）を実装できます。`[FILTER] Name lua` filter を使用してください。

</details>

---

7. Promtail configuration のどの pipeline_stages setting が特定のログを除外しますか？

   - A) stage.filter
   - B) stage.drop
   - C) stage.exclude
   - D) stage.ignore

<details>
<summary>回答を表示</summary>

**回答: B) stage.drop**

**解説:**
Promtail の `stage.drop` は、regex または条件に一致するログ行を除外します。例: healthcheck logs を除外するには、`expression: "healthcheck|readiness"` を使用します。

</details>

---

8. AWS 環境で CloudWatch Logs と OpenSearch の両方にログを送信する必要がある場合、最も適した collector はどれですか？

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) Logstash

<details>
<summary>回答を表示</summary>

**回答: B) FluentBit**

**解説:**
FluentBit は `cloudwatch_logs` と `opensearch` の両方の output plugins をネイティブにサポートしています。AWS が提供する `aws-for-fluent-bit` image を使用して簡単にデプロイできます。Promtail と Alloy は Loki 向けに最適化されています。

</details>

---

9. OpenTelemetry Collector のどの processor がメモリ使用量を制限しますか？

   - A) batch
   - B) memory_limiter
   - C) resource
   - D) filter

<details>
<summary>回答を表示</summary>

**回答: B) memory_limiter**

**解説:**
`memory_limiter` processor は OTEL Collector のメモリ使用量を監視し、設定された制限に達したときに OOM を防ぐため、データ収集を一時的に停止します。

</details>

---

10. 既存の Promtail 環境から metrics と traces も収集する必要がある場合、推奨される移行先は何ですか？

    - A) FluentBit
    - B) Logstash
    - C) Grafana Alloy
    - D) Filebeat

<details>
<summary>回答を表示</summary>

**回答: C) Grafana Alloy**

**解説:**
Grafana Alloy は Promtail の後継プロジェクトであり、Promtail のすべての機能を含むとともに、metrics（Prometheus）と traces（Tempo）も収集できます。Promtail configurations は River syntax に簡単に移行できます。

</details>
