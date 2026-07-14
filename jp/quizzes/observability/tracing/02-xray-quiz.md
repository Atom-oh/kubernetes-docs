# AWS X-Ray クイズ

AWS X-Ray についての理解度を確認しましょう。

---

1. AWS X-Ray の主要な機能では**ない**ものはどれですか？
   - A) Service map visualization
   - B) Distributed tracing
   - C) Log aggregation
   - D) Performance analysis

<details>
<summary>答えを表示</summary>

**回答: C) Log aggregation**

**解説:**
AWS X-Ray は Distributed tracing、Service map visualization、Performance analysis を提供します。Log aggregation は CloudWatch Logs の機能です。X-Ray は CloudWatch Logs と統合して trace と log を関連付けることができますが、log 自体を収集または保存することはありません。

</details>

---

2. EKS で X-Ray daemon をデプロイする推奨方法はどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>答えを表示</summary>

**回答: C) DaemonSet**

**解説:**
X-Ray Daemon を DaemonSet としてデプロイすることが推奨されます。DaemonSet は各 node で 1 つの Pod を実行するため、その node 上のすべての application Pod が local X-Ray Daemon に trace data を送信できます。これにより network latency が最小化され、信頼性の高い data transmission が確保されます。

</details>

---

3. X-Ray で centralized sampling rules を設定する際に使用され**ない**パラメータはどれですか？
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>答えを表示</summary>

**回答: D) RetentionDays**

**解説:**
X-Ray sampling rules には FixedRate（固定 sampling ratio）、ReservoirSize（1 秒あたりの最小 sample 数）、Priority（rule priority）が含まれます。RetentionDays は sampling rule のパラメータではなく、X-Ray の data retention settings に関連します。デフォルトの data retention period は 30 日です。

</details>

---

4. X-Ray における Annotation と Metadata の違いは何ですか？
   - A) Annotation の最大数は 100、Metadata は無制限
   - B) Annotation は indexed され filterable、Metadata は indexed されない
   - C) Annotation は string のみをサポートし、Metadata はすべての type をサポートする
   - D) Annotation は自動生成され、Metadata は手動で追加される

<details>
<summary>答えを表示</summary>

**回答: B) Annotation は indexed され filterable、Metadata は indexed されない**

**解説:**
Annotations は indexed され、X-Ray console の filter expressions を使用して検索できます（最大 50 個）。Metadata は indexed されず検索できませんが、詳細情報の保存に使用されます。重要な identifier（user_id、order_id など）には Annotations を、request/response body などの詳細情報には Metadata を使用します。

</details>

---

5. ADOT（AWS Distro for OpenTelemetry）Collector を使用する利点では**ない**ものはどれですか？
   - A) vendor-neutral standards を使用する
   - B) multi-backend support
   - C) X-Ray-specific optimization
   - D) OpenTelemetry protocol support

<details>
<summary>答えを表示</summary>

**回答: C) X-Ray-specific optimization**

**解説:**
ADOT Collector は OpenTelemetry をベースとした vendor-neutral な Collector であり、X-Ray に加えてさまざまな backend（Prometheus、Jaeger、Datadog など）に data を送信できます。X-Ray-specific optimization は X-Ray Daemon の特性です。ADOT の利点は standardized instrumentation と multi-backend support です。

</details>

---

6. X-Ray service map で node が赤色で表示されるのはどのような場合ですか？
   - A) response time が遅い場合
   - B) traffic が多い場合
   - C) error rate が高い場合
   - D) 新しく追加された service の場合

<details>
<summary>答えを表示</summary>

**回答: C) error rate が高い場合**

**解説:**
X-Ray service map の node color は service health status を示します。赤色は error rate が高い service、黄色は warning level の問題がある service、緑色は正常な service を示します。これにより問題のある service をすばやく特定できます。

</details>

---

7. X-Ray で OpenTelemetry trace data を受信するには、どの設定が必要ですか？
   - A) X-Ray SDK をインストールする
   - B) AWS X-Ray Propagator と ID Generator を設定する
   - C) CloudWatch Agent をインストールする
   - D) Lambda Layer を追加する

<details>
<summary>答えを表示</summary>

**回答: B) AWS X-Ray Propagator と ID Generator を設定する**

**解説:**
OpenTelemetry から X-Ray に trace data を送信するには、AWS X-Ray Propagator（context propagation）と AWS X-Ray ID Generator（X-Ray format の TraceIDs を生成）を設定する必要があります。これにより、OpenTelemetry standards を使用しながら X-Ray と互換性のある trace data を生成できます。

</details>

---

8. response time が 2 秒を超える request を検索する正しい X-Ray filter expression query はどれですか？
   - A) `duration > 2`
   - B) `responsetime > 2`
   - C) `latency >= 2000`
   - D) `time > 2s`

<details>
<summary>答えを表示</summary>

**回答: B) responsetime > 2**

**解説:**
X-Ray filter expressions では、response time に `responsetime` keyword を使用し、unit は秒です。`responsetime > 2` は 2 秒を超えてかかった request を filter します。ほかに便利な filter として、`fault = true`（server error）、`error = true`（client error）、`service("name")`（特定の service）があります。

</details>

---

9. X-Ray を CloudWatch ServiceLens と統合した際に提供される機能では**ない**ものはどれですか？
   - A) trace と metric の統合ビュー
   - B) service map 上に CloudWatch alarm を表示する
   - C) automatic code instrumentation
   - D) log と trace を関連付ける

<details>
<summary>答えを表示</summary>

**回答: C) automatic code instrumentation**

**解説:**
CloudWatch ServiceLens は、X-Ray trace、CloudWatch metric、log の統合ビューを提供します。service map 上に CloudWatch alarm を表示し、log と trace を関連付ける機能を提供します。ただし、automatic code instrumentation は X-Ray SDK または OpenTelemetry auto-instrumentation を通じて行う必要があります。

</details>

---

10. X-Ray Groups の主な目的は何ですか？
    - A) user permission management
    - B) filter-based trace grouping と alerting
    - C) resource cost allocation
    - D) data retention policy settings

<details>
<summary>答えを表示</summary>

**回答: B) filter-based trace grouping と alerting**

**解説:**
X-Ray Groups は filter expressions を使用して trace を group 化します。たとえば、production environment、特定の service、error request などの group を作成できます。各 group に対して CloudWatch alarm を設定し、特定の条件（error rate の上昇など）に関する alert を受け取れます。

</details>

---
