# Observability 最適化クイズ

> **検証済みのサンプルバージョン**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **最終更新**: September 13, 2026

このクイズでは、EKS Observability 最適化ガイドの理解度を確認します。Observability の3つの柱である logging、metrics、tracing に加え、eBPF ベースの monitoring とコスト最適化戦略を扱います。

---

## 選択式問題

1. Observability の3つの柱のうち、「なぜ遅いのか？」という質問に答えるのに最も適したデータタイプはどれですか？
   - A) Logging
   - B) Metrics
   - C) Tracing
   - D) Events

<details>
<summary>回答を表示</summary>

**回答: C) Tracing**

**解説:**
Observability の3つの柱は、それぞれ異なる種類の質問に答えます。Logging は「何が起きたか？」、Metrics は「システムは健全か？」、Tracing は「なぜ遅いのか？」に答えます。Tracing は、因果関係を理解してボトルネックを分析するため、リクエストフローを追跡する用途に最適化されています。分散システムでは、複数の Service をまたぐリクエストのレイテンシーを分析する際に Tracing が不可欠です。

</details>

2. ラベルベースの高速フィルタリングに優れ、object storage（S3）を利用して高いコスト効率を実現する log storage solution はどれですか？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>回答を表示</summary>

**回答: C) Loki**

**解説:**
Loki は label indexing と object storage を使用しますが、総コストには compute、cache、object request、query、operation が含まれます。S3 の storage price を総コストと見なすのではなく、同じ Region、volume、retention、availability で比較してください。

</details>

3. EKS で logs を収集できる C ベースの agent はどれですか？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>回答を表示</summary>

**回答: B) Fluent Bit**

**解説:**
Fluent Bit は AWS deployment で使用できる C ベースの collector です。Memory と throughput は version、parser、record size、buffering、hardware に依存します。固定の 15 MB や 200K msg/s という主張は保証ではありません。

</details>

4. Prometheus における cardinality explosion の主な原因は何ですか？
   - A) scrape interval が長すぎる場合
   - B) Pod UID または timestamp を label として使用する場合
   - C) Recording Rules を多用する場合
   - D) Remote Write を有効にする場合

<details>
<summary>回答を表示</summary>

**回答: B) Pod UID または timestamp を label として使用する場合**

**解説:**
変化する request-ID/timestamp label は series count を増加させます。source で label を制限し、一意性を検証してください。labeldrop は sample を集約せず、collision を引き起こす可能性があります。target relabeling と metric relabeling は異なる段階で実行されます。

</details>

5. OpenTelemetry Collector の Tail Sampling 戦略で、ERROR span を含む受信 trace を選択する policy type はどれですか？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>回答を表示</summary>

**回答: C) status_code**

**解説:**
ERROR status_code policy は、その sampler が受信した error span を使用して trace を選択します。Trace affinity、decision timing、buffer limit、late span、upstream head sampling により、失敗したすべての request が保持されることは保証されません。

</details>

6. eBPF ベースの monitoring の最大の利点は何ですか？
   - A) より多くの種類の metrics を収集できる
   - B) コードを変更せずに application を instrument できる
   - C) metric storage cost を削減できる
   - D) query performance を改善できる

<details>
<summary>回答を表示</summary>

**回答: B) コードを変更せずに application を instrument できる**

**解説:**
対応する kernel、runtime、protocol では source change を削減できますが、すべての language、TLS library、business span を同等にカバーするわけではありません。permission、overhead、sensitive payload を検証してください。SDK auto-instrumentation でも source change を回避できる場合があります。

</details>

7. Cilium Hubble の主な用途は何ですか？
   - A) Container resource usage monitoring
   - B) Network flow の観測と分析
   - C) Log の収集と storage
   - D) Distributed tracing backend

<details>
<summary>回答を表示</summary>

**回答: B) Network flow の観測と分析**

**解説:**
Hubble は、互換性のある Cilium deployment で network flow を観測します。L7 visibility は protocol と proxy/policy configuration に依存します。すべての flow や完全な application tracing を約束するのではなく、実際の coverage を検証してください。

</details>

8. Kepler（Kubernetes Efficient Power Level Exporter）が主に測定する metric は何ですか？
   - A) CPU temperature
   - B) Network bandwidth
   - C) Energy（joules）と power（watts）
   - D) Disk I/O latency

<details>
<summary>回答を表示</summary>

**回答: C) Energy（joules）と power（watts）**

**解説:**
Kepler 0.10+ は legacy 0.7 と異なります。0.11.4 では、kepler_pod_cpu_watts は power gauge であり、rate(kepler_pod_cpu_joules_total[5m]) は J/s=W です。1000 を掛けると milliwatts になります。hardware access と attribution support を検証してください。

</details>

9. OpenCost/KubeCost で team ごとの cost を追跡する推奨方法は何ですか？
   - A) team ごとに別々の Kubernetes cluster を作成する
   - B) namespace と Pod で cost-center や team などの label を標準化する
   - C) team ごとに別々の AWS account を割り当てる
   - D) ResourceQuotas のみを設定する

<details>
<summary>回答を表示</summary>

**回答: B) namespace と Pod で cost-center や team などの label を標準化する**

**解説:**
OpenCost は Kubernetes label に基づいて cost を配分します。namespace と Pod に `cost-center`、`team`、`environment` などの label を一貫して適用することで、`aggregate=label:team` を使用して OpenCost API 経由で team ごとの cost を query できます。このアプローチにより、既存の cluster structure を維持しながら、詳細な cost analysis と chargeback が可能になります。

</details>

10. SLO（Service Level Objective）ベースの monitoring において、「Error Budget」とは何を意味しますか？
    - A) monitoring system operation に割り当てられた budget
    - B) SLO target から逸脱する際に許容される error の量
    - C) alert の送信コスト
    - D) log storage に使用できる storage capacity

<details>
<summary>回答を表示</summary>

**回答: B) SLO target から逸脱する際に許容される error の量**

**解説:**
request ベースの 99.9% SLO では、許容される bad request は定義された window における total requests×0.001 に等しくなります。これを time ベースの downtime と混同しないでください。残りの 30-day budget には、直近5分間の ratio ではなく、30-day の request-weighted error ratio が必要です。

</details>

---

## 短答式問題

1. 複雑な query を事前計算して保存することで dashboard query performance を向上させる Prometheus feature の名前は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Recording Rules

**解説:**
Recording Rules は PromQL expression を定期的に評価し、結果を新しい time series として保存します。たとえば、`record: node:cpu_utilization:ratio` を使用して node CPU utilization を事前計算すると、dashboard は複雑な query を実行する代わりにこの metric を直接 query でき、応答が高速化されます。これらは PrometheusRule CRD の `record` field で定義されます。

</details>

2. OpenTelemetry で、decision window の span を収集し、観測された outcome を使用して sample を行う sampling method は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tail Sampling

**解説:**
デフォルトの trace-complete sampling は、decision window 中に受信した span を使用して決定します。すべての span の完了や到着を証明することはできません。affinity、buffer、late span、restart、upstream sampling を考慮してください。

</details>

3. trace ID を metric data point にリンクし、metrics から traces への直接 navigation を可能にする Prometheus feature は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Exemplars

**解説:**
Exemplars は、追加の context（通常は traceID）を metric sample に付加する feature です。histogram または counter metric に exemplar を追加すると、Grafana の metric graph 上の特定の point をクリックして、その時点の trace に直接移動できます。これにより Observability data 間の correlation analysis が容易になり、trace で「なぜこの時点で latency が急増したのか」を分析できます。

</details>

4. VictoriaMetrics cluster mode で、metric data storage を担当する component の名前は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** vmstorage

**解説:**
vmstorage が data を保存します。複数の instance だけでは replication は確立されません。replication factor、vminsert/vmselect behavior、query deduplication、failure handling を設定してください。

</details>

5. 古い data を S3 Glacier のような低コスト storage に移動して log/metric storage cost を削減する戦略は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tiered Storage

**解説:**
Tiering は access frequency、restore delay、retention に依存します。active な Loki/Tempo block を Glacier に移すと query が機能しなくなる場合があります。compatibility/recovery を検証するか、別の archive を使用してください。節約額は固定の割合ではありません。

</details>

---

## ハンズオン問題

1. DEBUG および TRACE level の log をフィルタリングして除外する Fluent Bit configuration を記述してください。

<details>
<summary>回答を表示</summary>

**回答:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**解説:**
arbitrary な message text ではなく、parse された level field に対して ^(DEBUG|TRACE)$ を match させます。drop と incident investigation への影響を測定してください。40～60% の節約は保証されません。

</details>

2. service ごとの HTTP error rate が 5% を超え、その状態が5分間継続した場合に warning を発生させる PrometheusRule を記述してください。

<details>
<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
spec:
  groups:
    - name: slo.alerts
      rules:
        - alert: HighHTTPErrorRate
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "HTTP error rate for service {{ $labels.service }} exceeded 5%"
            description: "Current error rate: {{ $value | humanizePercentage }}"
```

**解説:**
この alert rule は、service ごとの 5XX status code ratio を計算します。`status=~"5.."` は status code 500～599 に一致する regex です。`for: 5m` により、condition が5分間継続した場合にのみ alert が発生し、一時的な spike による false alert を防止します。`sum by (service)` を使用すると、各 service に対して独立した alert が生成されます。

</details>

3. error trace を100%、latency が1秒を超える trace を100%、残りを10%のみ sample する OpenTelemetry Collector 向け tail_sampling processor configuration を記述してください。

<details>
<summary>回答を表示</summary>

**回答:**
```yaml
processors:
  tail_sampling:
    decision_wait: 2s
    num_traces: 1000
    maximum_trace_size_bytes: 1048576
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 1000
    - name: baseline
      type: probabilistic
      probabilistic:
        sampling_percentage: 10
```

**解説:**
これらの positive policy は、一致する受信済み error/slow trace を保持し、残りを probabilistic に sample します。buffer、affinity、late-span limit は引き続き存在します。全体の retention は error/slow の割合に依存するため、90% の削減は保証されません。first-match semantics を drop/composite policy に一般化しないでください。

</details>

---

## 上級問題

1. 大規模 EKS cluster（500+ node）で Observability stack の high availability を実現するための architecture を設計してください。collection、storage、query の各 layer について、どの component をどのように deployment すべきか説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

node count のみから replica count を導き出さないでください。node log agent と gateway を分離し、trace ID によって tail sampling を route し、buffering/backpressure と drop を測定します。現在の Loki/Tempo mode の replication/quorum/AZ requirement に従ってください。VictoriaMetrics replication/query deduplication と AMP quota/retention を設定します。Prometheus replica×shard の PVC/memory を予算化し、shard query を merge します。Grafana には shared DB と独立した Alerting HA が必要です。query caching の edition support を検証してください。PDB と S3 durability は end-to-end availability を保証しません。failure と recovery をテストしてください。

</details>

2. Observability cost が月額 $5,000 の環境で、品質を維持しながら50%の cost reduction を実現する最適化戦略を提案してください。logging、metrics、tracing の各領域について、具体的な方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

$5,000 の baseline と 50% の target は仮定です。最大の category を最適化する前に、ingestion、storage、scan、compute、operation cost を attribution してください。parsed-level filtering、request-level probability sampling、安全な metric/bucket reduction、tail sampling、retention をそれぞれ試行してください。throttling は 10% sampler ではなく、recording rule は raw-data retention を変更しません。等しい Region、availability、query、retention requirement で総コストを比較してください。節約効果は重複します。percentage を加算するのではなく、bill、data loss、SLO coverage、investigation success を評価してください。target が確立されていない場合は、evidence と次の experiment を報告してください。

</details>

---

**スコア計算:**
- 正解数 18～20: 優秀（Observability expert level）
- 正解数 14～17: 良好（実務で活用可能）
- 正解数 10～13: 平均（追加学習を推奨）
- 正解数 6～9: 基礎（基本概念を復習）
- 正解数 0～5: 不十分（内容全体の復習が必要）

---

**関連学習資料:**
- [EKS Observability 最適化ガイド](../../observability/09-observability-optimization.md)
