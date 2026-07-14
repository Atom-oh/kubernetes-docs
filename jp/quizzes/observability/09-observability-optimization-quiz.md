# Observability 最適化クイズ

> **対応バージョン**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **最終更新**: February 22, 2026

このクイズでは、EKS Observability Optimization Guide の理解度を確認します。Observability の 3 本柱である Logging、Metrics、Tracing に加え、eBPF ベースのモニタリングとコスト最適化戦略を扱います。

---

## 選択問題

1. Observability の 3 本柱のうち、「なぜ遅いのか？」という質問に最も適したデータ型はどれですか？
   - A) Logging
   - B) Metrics
   - C) Tracing
   - D) Events

<details>
<summary>回答を表示</summary>

**回答: C) Tracing**

**解説:**
Observability の 3 本柱は、それぞれ異なる種類の質問に答えます。Logging は「何が起きたか？」、Metrics は「システムは健全か？」、Tracing は「なぜ遅いのか？」に答えます。Tracing は、因果関係の理解とボトルネックの分析のためにリクエストフローを追跡するよう最適化されています。分散システムでは、複数の Service をまたぐリクエストのレイテンシーを分析する際に Tracing が不可欠です。

</details>

2. ラベルベースの高速フィルタリングに優れ、オブジェクトストレージ（S3）を活用して高いコスト効率を実現するログストレージソリューションはどれですか？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>回答を表示</summary>

**回答: C) Loki**

**解説:**
Grafana Loki はラベルベースのインデックスを使用し、全文検索インデックスなしで高速フィルタリングを提供します。ログデータを S3 などのオブジェクトストレージに保存するため、ストレージコストが非常に低くなります（S3: $0.023/GB/月）。OpenSearch は全文検索に強い一方でインデックスのストレージコストが高く、CloudWatch Logs は取り込みコストが比較的高額です（$0.50/GB）。

</details>

3. 最もメモリ使用量が少なく、C で記述され、EKS でネイティブサポートされているログエージェントはどれですか？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>回答を表示</summary>

**回答: B) Fluent Bit**

**解説:**
Fluent Bit は C で記述され、使用メモリは約 15MB にすぎません。Fluentd（約 60MB、Ruby/C）や Vector（約 30MB、Rust）より軽量で、最大約 200K msg/s の高スループットを提供します。AWS は EKS のログコレクターとして Fluent Bit を公式に推奨しており、aws-for-fluent-bit イメージを提供しています。

</details>

4. Prometheus における cardinality explosion の主な原因は何ですか？
   - A) scrape interval が長すぎる場合
   - B) Pod UID またはタイムスタンプをラベルとして使用する場合
   - C) Recording Rules を多用しすぎる場合
   - D) Remote Write を有効にする場合

<details>
<summary>回答を表示</summary>

**回答: B) Pod UID またはタイムスタンプをラベルとして使用する場合**

**解説:**
Cardinality とは、一意な時系列の数を指します。Pod UID、タイムスタンプ、リクエスト ID などの一意な値をラベルとして使用すると、ラベルの組み合わせが無限に増加し、時系列の爆発を引き起こします。これにより Prometheus のメモリ使用量が急増し、クエリ性能が低下します。relabel_configs では pod_template_hash や controller_revision_hash のようなラベルを削除することが推奨されます。

</details>

5. OpenTelemetry Collector の Tail Sampling 戦略で、エラーを含むトレースを 100% 保持するポリシータイプはどれですか？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>回答を表示</summary>

**回答: C) status_code**

**解説:**
Tail Sampling は、トレースの完了後に完全なトレース情報に基づいてサンプリングの判断を行います。`status_code` ポリシーはトレースのステータスコード（OK、ERROR）に基づいてサンプリングします。`status_codes: [ERROR]` を設定すると、エラーを含むトレースを 100% 保持します。これは、全体のデータ量を削減しつつ、問題分析に重要なトレースを保存できる効果的な戦略です。

</details>

6. eBPF ベースのモニタリングの最大の利点は何ですか？
   - A) より多くの種類の Metrics を収集できる
   - B) コード変更なしでアプリケーションをインストルメントできる
   - C) Metrics のストレージコストを削減する
   - D) クエリ性能を改善する

<details>
<summary>回答を表示</summary>

**回答: B) コード変更なしでアプリケーションをインストルメントできる**

**解説:**
eBPF（extended Berkeley Packet Filter）は、Linux カーネル内でプログラムを安全に実行し、システムコールやネットワークパケットなどを観測します。従来のインストルメンテーションでは SDK の追加、コードの変更、再デプロイが必要ですが、eBPF はカーネルレベルで透過的に動作するため、アプリケーションを変更せずにモニタリングできます。また言語に依存せず、どの言語で記述されたアプリケーションも同様にインストルメントできます。

</details>

7. Cilium Hubble の主な用途は何ですか？
   - A) コンテナのリソース使用量のモニタリング
   - B) ネットワークフローの観測と分析
   - C) ログの収集と保存
   - D) 分散 Tracing のバックエンド

<details>
<summary>回答を表示</summary>

**回答: B) ネットワークフローの観測と分析**

**解説:**
Cilium Hubble は、eBPF ベースの CNI である Cilium の Observability コンポーネントです。Hubble はクラスター内のすべてのネットワークフローをリアルタイムで観測し、DNS リクエスト、TCP 接続、HTTP トラフィックなどを分析します。`hubble observe` コマンドを使用すると、特定の Service へのトラフィックをフィルタリングしたり、ドロップされたパケットを分析したりできます。Service map の可視化やネットワークポリシーの検証に役立ちます。

</details>

8. Kepler（Kubernetes Efficient Power Level Exporter）が測定する主な Metrics は何ですか？
   - A) CPU 温度
   - B) ネットワーク帯域幅
   - C) エネルギー消費量（ジュール/ワット）
   - D) ディスク I/O レイテンシー

<details>
<summary>回答を表示</summary>

**回答: C) エネルギー消費量（ジュール/ワット）**

**解説:**
Kepler は、eBPF を使用してコンテナと Pod のエネルギー消費量を測定する CNCF プロジェクトです。`kepler_container_joules_total` Metrics を通じてエネルギー消費量（ジュール）を提供し、消費電力（ワット）は `rate(kepler_container_joules_total[5m]) * 1000` で計算できます。これにより namespace または Pod ごとのエネルギー使用量を分析でき、グリーンコンピューティングの目標達成に役立ちます。

</details>

9. OpenCost/KubeCost でチームごとのコストを追跡するための推奨方法は何ですか？
   - A) チームごとに別々の Kubernetes クラスターを作成する
   - B) namespace と Pod で cost-center や team などのラベルを標準化する
   - C) チームごとに別々の AWS アカウントを割り当てる
   - D) ResourceQuotas のみを設定する

<details>
<summary>回答を表示</summary>

**回答: B) namespace と Pod で cost-center や team などのラベルを標準化する**

**解説:**
OpenCost は Kubernetes ラベルに基づいてコストを配分します。`cost-center`、`team`、`environment` などのラベルを namespace と Pod に一貫して適用することで、`aggregate=label:team` を使用して OpenCost API からチームごとのコストをクエリできます。このアプローチにより、既存のクラスター構造を維持しながら詳細なコスト分析とチャージバックを実現できます。

</details>

10. SLO（Service Level Objective）ベースのモニタリングにおいて、「Error Budget」とは何を意味しますか？
    - A) モニタリングシステムの運用に割り当てられた予算
    - B) SLO 目標から逸脱しても許容されるエラー量
    - C) アラート送信のコスト
    - D) ログストレージに利用可能なストレージ容量

<details>
<summary>回答を表示</summary>

**回答: B) SLO 目標から逸脱しても許容されるエラー量**

**解説:**
Error Budget は SLO から導かれる概念で、許容されるエラーの総量を表します。たとえば、可用性 SLO が 99.9% の場合、Error Budget は 0.1% です。30 日間を基準にすると、約 43 分のダウンタイムが許容されます。Error Budget を使い切った場合は、新機能のデプロイを停止し、安定性の改善に注力する必要があります。残りの Error Budget 比率は、式 `1 - (1 - sli:availability:ratio) / (1 - 0.999)` で計算できます。

</details>

---

## 短答問題

1. 複雑なクエリを事前計算して保存することでダッシュボードのクエリ性能を向上させる Prometheus の機能名は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Recording Rules

**解説:**
Recording Rules は PromQL 式を定期的に評価し、その結果を新しい時系列として保存します。たとえば、`record: node:cpu_utilization:ratio` を使用してノードの CPU 使用率を事前計算すると、ダッシュボードは複雑なクエリを実行する代わりにこの Metrics を直接クエリできるため、応答が高速になります。PrometheusRule CRD の `record` フィールドで定義します。

</details>

2. OpenTelemetry で、トレース完了後に完全なトレース情報に基づいてサンプリング判断を行う手法は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tail Sampling

**解説:**
Tail Sampling は、トレースのすべての span が到着した後にサンプリング判断を行います。これはトレース開始時に判断を行う Head Sampling（確率的サンプリング）とは対照的です。Tail Sampling の利点は、エラーまたは高レイテンシーのトレースのみを選択的に保持できることです。ただし、判断する前にすべての span をメモリに保持する必要があるため、`decision_wait` と `num_traces` の設定が重要です。

</details>

3. trace ID を Metrics データポイントにリンクし、Metrics から Tracing へ直接移動できるようにする Prometheus の機能は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Exemplars

**解説:**
Exemplars は、Metrics サンプルに追加コンテキスト（通常は traceID）を付加する機能です。histogram または counter Metrics に exemplars を追加すると、Grafana の Metrics グラフで特定のポイントをクリックして、その時点のトレースへ直接移動できます。これにより Observability データ間の相関分析が容易になり、「この時点でなぜレイテンシーが急増したのか」をトレースで分析できます。

</details>

4. VictoriaMetrics のクラスター mode で、Metrics データのストレージを担当するコンポーネント名は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** vmstorage

**解説:**
VictoriaMetrics のクラスター mode は 3 つのコンポーネントで構成されます。vminsert は Metrics の収集と分散、vmselect はクエリ処理、vmstorage は実際の Metrics データストレージを担当します。vmstorage は複数のインスタンスで水平スケールでき、レプリケーションによって高可用性を提供します。この分離されたアーキテクチャにより、取り込み、ストレージ、クエリのワークロードを独立してスケールできます。

</details>

5. 古いデータを S3 Glacier のような低コストストレージへ移動してログ/Metrics のストレージコストを削減する戦略は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tiered Storage

**解説:**
Tiered Storage 戦略では、重要度とアクセス頻度に応じて異なるストレージ階層にデータを保存します。最近のデータは高性能ストレージ（SSD、EBS）に、中期データは S3 Standard-IA に、長期アーカイブデータは S3 Glacier Deep Archive に保存します。これによりストレージコストを 70～90% 削減できます。Loki や Tempo などのオブジェクトストレージベースのソリューションは、この戦略をデフォルトでサポートしています。

</details>

---

## ハンズオン問題

1. DEBUG および TRACE レベルのログをフィルタリングして除外する Fluent Bit 設定を記述してください。

<details>
<summary>回答を表示</summary>

**回答:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$
```

または、正規表現を使用する場合:
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log (DEBUG|TRACE)
```

**解説:**
Fluent Bit の grep filter は正規表現を使用してログをフィルタリングします。`Exclude` ディレクティブはパターンに一致するログを除外します。本番環境で DEBUG/TRACE ログをフィルタリングすると、ログ量を 40～60% 削減でき、ストレージコストを大幅に削減できます。ただし、トラブルシューティングが必要な場合は、特定の Service に対して DEBUG ログを選択的に有効化できます。

</details>

2. Service ごとの HTTP エラー率が 5% を超え、その状態が 5 分間継続した場合に warning を発生させる PrometheusRule を記述してください。

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
このアラートルールは、Service ごとの 5XX ステータスコード比率を計算します。`status=~"5.."` は、ステータスコード 500～599 に一致する正規表現です。`for: 5m` は、条件が 5 分間継続した場合にのみアラートを発生させるため、一時的なスパイクによる誤検知を防止します。`sum by (service)` を使用すると、Service ごとに独立したアラートが生成されます。

</details>

3. エラートレースを 100%、レイテンシーが 1 秒を超えるトレースを 100%、残りを 10% のみサンプリングする OpenTelemetry Collector の tail_sampling processor 設定を記述してください。

<details>
<summary>回答を表示</summary>

**回答:**
```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      # Keep 100% of traces with errors
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep 100% of traces with latency over 1 second
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000

      # Sample only 10% of the rest
      - name: default-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

**解説:**
Tail Sampling ポリシーは順番に評価され、いずれかのポリシーに一致した場合、そのトレースは保持されます。`decision_wait` はトレースの完了を待機する時間であり、すべての span が到着するための十分な時間が必要です。`num_traces` はメモリ内に保持するトレースの最大数です。この設定では、エラーおよびパフォーマンス分析に重要なトレースを保持しつつ、全体のデータ量を約 90% 削減できます。

</details>

---

## 上級問題

1. 大規模な EKS クラスター（500+ ノード）で Observability スタックの高可用性を実現するアーキテクチャを設計してください。収集、ストレージ、クエリの各レイヤーについて、どのコンポーネントをどのようにデプロイすべきか説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**データ収集レイヤー:**
- Fluent Bit: 各ノードに DaemonSet としてデプロイ（メモリ制限 100-200Mi）
- OTel Collector: 前段に load balancer を配置して DaemonSet としてデプロイ
- Collector の冗長化: AZ ごとに少なくとも 2+ の Collector インスタンス

**ストレージレイヤー:**
- Logs: Loki Simple Scalable mode
  - Write path: 2+ レプリカ（AZ 分散）
  - Read path: 2+ レプリカ（クエリ load balancing）
  - Backend: S3（耐久性 99.999999999%）

- Metrics: VictoriaMetrics cluster または AMP
  - vminsert: 2+ レプリカ（書き込み load balancing）
  - vmstorage: 3+ レプリカ（レプリケーション係数 2）
  - vmselect: 2+ レプリカ（読み取り load balancing）

- Traces: Grafana Tempo
  - Distributor: 2+ レプリカ
  - Ingester: 3+ レプリカ（WAL 有効）
  - Backend: S3

**クエリレイヤー:**
- Grafana: 2+ レプリカ、セッションストレージには外部 PostgreSQL/MySQL
- Caching: Redis/Memcached によるクエリ結果のキャッシュ

**主な考慮事項:**
1. すべての stateful コンポーネントを複数の AZ にまたがってデプロイする
2. 共有ストレージとして S3 を使用する（単一障害点を排除）
3. Prometheus sharding（3-5 shards）+ Remote Write で中央ストレージへオフロードする
4. PodDisruptionBudget により rolling update 中の可用性を確保する

</details>

2. Observability のコストが月額 $5,000 の環境で、品質を維持しながらコストを 50% 削減するための最適化戦略を提案してください。Logging、Metrics、Tracing の各領域について具体的な手法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Logging の最適化（想定削減額: $1,500-2,000）**

1. **ログレベルのフィルタリング**（40-60% 削減）
   - 本番環境で DEBUG/TRACE ログを除外する
   - 実装: `Exclude log (DEBUG|TRACE)` を使用する Fluent Bit grep filter

2. **サンプリングを適用**（30-50% 削減）
   - 高頻度ログ（access logs、health checks）には 10% サンプリング
   - 実装: Fluent Bit throttle filter `Rate 10, Window 60`

3. **保持期間の最適化**（20-40% 削減）
   - 本番: 14 日、Dev/Staging: 7 日
   - 長期保持は重要なログのみ（S3 Glacier へ移動）

4. **ストレージ移行**（50-70% 削減）
   - CloudWatch Logs（$0.50/GB 取り込み） -> Loki + S3（$0.023/GB ストレージ）

**Metrics の最適化（想定削減額: $500-800）**

1. **Cardinality 管理**
   - 不要なラベルを削除する（pod_template_hash、controller_revision_hash）
   - Metrics を drop: `go_.*`、`promhttp_.*` のような内部 Metrics を除外する

2. **Scrape interval の調整**
   - 重要な Metrics: 15s、一般的な Metrics: 30s-60s
   - histogram buckets を制限する（不要な le 値を削除）

3. **Recording Rules を活用**
   - 頻繁に使用する集計クエリを事前計算する
   - 元の高解像度データを早期に削除する（7 日 -> 3 日）

4. **ストレージ移行**
   - 自己管理 Prometheus -> VictoriaMetrics（7x 圧縮率）
   - または AMP を使用する（運用負荷の排除、予測可能なコスト）

**Tracing の最適化（想定削減額: $500-1,000）**

1. **Tail Sampling を適用**（80-90% 削減）
   - エラー/低速トレース: 100% 保持
   - 通常トレース: 5-10% のみサンプリング

2. **ストレージ移行**
   - X-Ray（$5/100 万トレース） -> Tempo + S3（ストレージコストのみ）

3. **保持期間の最適化**
   - 詳細トレース: 7 日
   - 集計データ: 30 日

**合計想定削減額: $2,500-3,800（50-76%）**

鍵は重要度に基づく階層化です。すべてのデータを同じように扱うのではなく、問題分析に必要なデータを保持しながら、データ量を積極的に削減します。

</details>

---

**スコア計算:**
- 正解数 18-20: 優秀（Observability エキスパートレベル）
- 正解数 14-17: 良好（実務に適用可能）
- 正解数 10-13: 平均（追加学習を推奨）
- 正解数 6-9: 基礎（基本概念の復習が必要）
- 正解数 0-5: 不十分（全コンテンツの復習が必要）

---

**関連学習教材:**
- [EKS Observability Optimization Guide](../../observability/09-observability-optimization.md)
