# 可観測性の最適化クイズ

> **検証済みの例示バージョン**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **最終更新日**: 2026年9月13日

このクイズでは、EKS 可観測性最適化ガイドの理解度を確認します。可観測性の三本柱であるログ、メトリクス、トレースに加え、eBPF ベースの監視とコスト最適化の方針を扱います。

---

## 選択式問題

1. 可観測性の三本柱のうち、「なぜ遅いのか」という問いに答えるのに最も適したデータはどれですか？
   - A) ログ
   - B) メトリクス
   - C) トレース
   - D) イベント

<details>
<summary>回答を表示</summary>

**回答: C) トレース**

**解説:**
可観測性の三本柱は、それぞれ異なる問いに答えます。ログは「何が起きたか」、メトリクスは「システムは健全か」、トレースは「なぜ遅いのか」を示します。トレースは、因果関係を理解してボトルネックを分析できるよう、リクエストの経路を追跡する用途に適しています。分散システムで複数のサービスを通るリクエストの遅延を調べる際に役立ちます。

</details>

2. ラベルによる高速な絞り込みに優れ、S3 などのオブジェクトストレージを利用するログ保存先はどれですか？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>回答を表示</summary>

**回答: C) Loki**

**解説:**
Loki はラベル索引とオブジェクトストレージを使いますが、総コストにはコンピューティング、キャッシュ、オブジェクト要求、クエリ、運用も含まれます。S3 の保存料金を総コストと見なさず、同じリージョン、データ量、保持期間、可用性の条件で比較してください。

</details>

3. EKS でログを収集できる、C 言語で実装されたエージェントはどれですか？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>回答を表示</summary>

**回答: B) Fluent Bit**

**解説:**
Fluent Bit は AWS 環境で使用できる C 言語ベースのコレクターです。メモリ使用量やスループットは、バージョン、パーサー、レコードサイズ、バッファリング、ハードウェアによって変わります。15 MB や毎秒 20 万メッセージといった固定値は保証ではありません。

</details>

4. Prometheus で cardinality が急増する主な原因は何ですか？
   - A) scrape interval が長すぎる
   - B) Pod UID や timestamp を label に使う
   - C) Recording Rule を多用する
   - D) Remote Write を有効にする

<details>
<summary>回答を表示</summary>

**回答: B) Pod UID や timestamp を label に使う**

**解説:**
変化する request ID や timestamp を label にすると、時系列数が増加します。データの発生元で label の種類を制限し、一意性も確認してください。`labeldrop` はサンプルを集約せず、衝突を起こすことがあります。target relabeling と metric relabeling は異なる段階で実行されます。

</details>

5. OpenTelemetry Collector の Tail Sampling で、ERROR span を含む受信済み trace を選ぶ policy type はどれですか？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>回答を表示</summary>

**回答: C) status_code**

**解説:**
`ERROR` の `status_code` policy は、その sampler が受信した error span を使って trace を選択します。trace affinity、判定タイミング、バッファ上限、遅れて届く span、上流の head sampling が影響するため、失敗したすべてのリクエストが保持されるとは限りません。

</details>

6. eBPF ベースの監視の最大の利点は何ですか？
   - A) より多くの種類のメトリクスを収集できる
   - B) コードを変更せずにアプリケーションを計測できる
   - C) メトリクスの保存コストを削減できる
   - D) クエリ性能を改善できる

<details>
<summary>回答を表示</summary>

**回答: B) コードを変更せずにアプリケーションを計測できる**

**解説:**
対応するカーネル、ランタイム、プロトコルでは、ソースコードの変更を減らせます。ただし、あらゆる言語、TLS ライブラリ、業務上の span を同等にカバーするわけではありません。権限、オーバーヘッド、機微なペイロードを検証してください。SDK による自動計測でも、コード変更を避けられる場合があります。

</details>

7. Cilium Hubble の主な用途は何ですか？
   - A) コンテナのリソース使用量の監視
   - B) ネットワークフローの観測と分析
   - C) ログの収集と保存
   - D) 分散トレースのバックエンド

<details>
<summary>回答を表示</summary>

**回答: B) ネットワークフローの観測と分析**

**解説:**
Hubble は、対応する Cilium 環境でネットワークフローを観測します。L7 の可視性は、プロトコルとプロキシ／ポリシーの設定に左右されます。すべてのフローが見える、またはアプリケーション全体のトレースができると決めつけず、実際の対象範囲を確認してください。

</details>

8. Kepler（Kubernetes Efficient Power Level Exporter）が主に測定するものは何ですか？
   - A) CPU 温度
   - B) ネットワーク帯域幅
   - C) エネルギー（joule）と電力（watt）
   - D) ディスク I/O 遅延

<details>
<summary>回答を表示</summary>

**回答: C) エネルギー（joule）と電力（watt）**

**解説:**
Kepler 0.10 以降は、旧版 0.7 と動作が異なります。0.11.4 では `kepler_pod_cpu_watts` は電力の gauge であり、`rate(kepler_pod_cpu_joules_total[5m])` は J/s、つまり W です。1000 を掛けると milliwatt になります。ハードウェアへのアクセス条件と attribution の対応状況を確認してください。

</details>

9. OpenCost／KubeCost でチームごとのコストを追跡する推奨方法は何ですか？
   - A) チームごとに Kubernetes クラスターを分ける
   - B) namespace と Pod に cost-center や team などの label を統一して付ける
   - C) チームごとに AWS account を分ける
   - D) ResourceQuota だけを設定する

<details>
<summary>回答を表示</summary>

**回答: B) namespace と Pod に cost-center や team などの label を統一して付ける**

**解説:**
OpenCost は Kubernetes label に基づいてコストを配分します。namespace と Pod に `cost-center`、`team`、`environment` などの label を一貫して付けると、OpenCost API で `aggregate=label:team` を指定してチーム別のコストを照会できます。既存のクラスター構成を維持しながら、詳細なコスト分析と費用配賦を行えます。

</details>

10. SLO（Service Level Objective）ベースの監視で「Error Budget」とは何ですか？
    - A) 監視システムの運用に割り当てる予算
    - B) SLO の目標から逸脱することが許されるエラー量
    - C) alert の送信コスト
    - D) ログ保存に使える容量

<details>
<summary>回答を表示</summary>

**回答: B) SLO の目標から逸脱することが許されるエラー量**

**解説:**
リクエスト数に基づく 99.9% SLO では、定義した期間内に許容される不良リクエスト数は、総リクエスト数×0.001 です。これを時間ベースの停止時間と混同しないでください。30 日間の残り予算を求めるには、直近 5 分間の比率ではなく、30 日間のリクエスト数で重み付けしたエラー比率が必要です。

</details>

---

## 短答式問題

1. 複雑なクエリを事前計算して保存し、dashboard のクエリを高速化する Prometheus の機能は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Recording Rules

**解説:**
Recording Rule は PromQL 式を定期的に評価し、その結果を新しい時系列として保存します。たとえば `record: node:cpu_utilization:ratio` で node の CPU 使用率を事前計算すれば、dashboard は複雑なクエリを実行せずにこの metric を直接参照でき、応答が速くなります。PrometheusRule CRD の `record` field で定義します。

</details>

2. OpenTelemetry で、判定期間中に span を集め、観測した結果に基づいてサンプリングする方式は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tail Sampling

**解説:**
標準的な trace-complete sampling は、判定期間中に受信した span に基づいて判断します。すべての span が完了した、または到着したと証明するものではありません。affinity、バッファ、遅れて届く span、再起動、上流での sampling を考慮してください。

</details>

3. trace ID を metric のデータ点に結び付け、メトリクスからトレースへ直接移動できるようにする Prometheus の機能は何ですか？

<details>
<summary>回答を表示</summary>

**回答:** Exemplars

**解説:**
Exemplar は、traceID などの補足情報を metric sample に付加する機能です。histogram や counter に exemplar を付けると、Grafana のグラフ上の点をクリックして、その時点の trace に直接移動できます。可観測性データを関連付け、「この時点で遅延が急増したのはなぜか」を trace で調べられます。

</details>

4. VictoriaMetrics の cluster mode で、メトリクスデータを保存するコンポーネントは何ですか？

<details>
<summary>回答を表示</summary>

**回答:** vmstorage

**解説:**
vmstorage がデータを保存します。インスタンスを複数起動しただけでは replication は成立しません。replication factor、vminsert／vmselect の動作、クエリの重複排除、障害時の処理を設定してください。

</details>

5. 古いログやメトリクスを S3 Glacier などの低コストストレージへ移し、保存費用を下げる戦略は何と呼ばれますか？

<details>
<summary>回答を表示</summary>

**回答:** Tiered Storage

**解説:**
階層化の設計は、アクセス頻度、復元時間、保持期間によって変わります。稼働中の Loki／Tempo block を Glacier へ移すと、クエリに支障が出ることがあります。互換性と復旧手順を検証するか、別の archive を使ってください。削減率は一定ではありません。

</details>

---

## ハンズオン問題

1. DEBUG と TRACE レベルのログを抽出対象から除外する Fluent Bit の設定を記述してください。

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
任意の message text ではなく、parse 済みの level field に対して `^(DEBUG|TRACE)$` を照合します。破棄されるログ量と、障害調査への影響を測定してください。40～60% のコスト削減は保証されません。

</details>

2. service ごとの HTTP error rate が 5% を超え、その状態が 5 分続いたら warning を発生させる PrometheusRule を記述してください。

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
この alert rule は service ごとに 5XX status code の比率を計算します。`status=~"5.."` は 500～599 の status code に一致する正規表現です。`for: 5m` によって condition が 5 分続いた場合にだけ alert を発生させ、一時的な急増による誤報を抑えます。`sum by (service)` により、service ごとに独立した alert が生成されます。

</details>

3. error trace を 100%、latency が 1 秒を超える trace も 100%、残りを 10% サンプリングする OpenTelemetry Collector の tail_sampling processor 設定を記述してください。

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
これらの肯定条件の policy は、一致した受信済み error／slow trace を保持し、それ以外を確率的にサンプリングします。バッファ、affinity、遅れて届く span の上限は引き続き影響します。error／slow trace の割合によって全体の保持率は変わるため、90% 削減は保証されません。first-match の動作を drop／composite policy にまで一般化しないでください。

</details>

---

## 上級問題

1. 500 ノードを超える大規模 EKS クラスターで、可観測性スタックの高可用性を実現する構成を設計してください。収集、保存、クエリの各層にどのコンポーネントをどう配置するか説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

ノード数だけから replica 数を決めないでください。ノード上のログ agent と gateway を分け、trace ID に基づいて tail sampling を振り分け、バッファリング、backpressure、drop を測定します。Loki／Tempo の現行モードに必要な replication、quorum、AZ の要件に従ってください。VictoriaMetrics の replication と query 重複排除、AMP の quota と retention を設定します。Prometheus の replica 数×shard 数に応じた PVC とメモリを確保し、shard のクエリ結果を統合します。Grafana には共有 DB と、別途高可用性を構成した Alerting が必要です。query caching が利用できる edition か確認してください。PDB や S3 の耐久性だけでは、エンドツーエンドの可用性は保証されません。障害と復旧をテストしてください。

</details>

2. 月額 $5,000 の可観測性コストがかかる環境で、品質を維持しながら 50% 削減する方針を提案してください。ログ、メトリクス、トレースごとに具体策を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

$5,000 の基準額と 50% の目標は仮定です。最大の費目に取り組む前に、取り込み、保存、スキャン、計算、運用の各コストを把握してください。parse 済み level による filter、request 単位の確率サンプリング、安全な metric／bucket 削減、tail sampling、保持期間の変更を個別に試します。throttling は 10% sampler ではなく、recording rule は生データの保持期間を変えません。同じリージョン、可用性、クエリ、保持期間の要件で総コストを比較してください。削減効果は重なるため、割合を単純に足し合わせず、請求額、データ損失、SLO のカバー範囲、調査の成功率を評価します。目標を達成できる根拠がなければ、確認できた証拠と次の実験を報告してください。

</details>

---

**スコア計算:**
- 正解数 18～20: 優秀（可観測性の専門家レベル）
- 正解数 14～17: 良好（実務で活用可能）
- 正解数 10～13: 平均（追加学習を推奨）
- 正解数 6～9: 基礎（基本概念を復習）
- 正解数 0～5: 不十分（全体を復習）

---

**関連学習資料:**
- [EKS 可観測性最適化ガイド](../../observability/09-observability-optimization.md)
