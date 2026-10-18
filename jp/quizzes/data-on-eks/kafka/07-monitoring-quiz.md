# パート 7: モニタリングクイズ

実際のメトリクス名、スクレイプ対象とデータ欠落、lag、認証付き KEDA の動作を確認しましょう。

## 1. この章の JMX 方式はどのように動作しますか？Strimzi のメトリクス収集方式はこれだけですか？

<details>
<summary>解答を表示</summary>

JMX Exporter は同じ JVM 内で Java agent として動作します。Strimzi は `strimziMetricsReporter` もサポートしています。方式を切り替える場合は、メトリクス名、構成、ダッシュボードを見直してください。

</details>

## 2. JMX MBean のマッピングルールと PodMonitor の relabeling はどう違いますか？

<details>
<summary>解答を表示</summary>

ConfigMap の JMX ルールは MBean をメトリクス名やラベルに変換します。PodMonitor の relabeling は別の検出段階であり、namespace、`kafka_cluster`、role などの対象コンテキストを付与します。

</details>

## 3. `UnderReplicatedPartitions` が 0 より大きい場合、すでにデータが失われたことを意味しますか？

<details>
<summary>解答を表示</summary>

いいえ。正常な定常状態では 0 ですが、障害、lag、計画作業で増えることがあります。継続時間、min-ISR 未満の状態や offline partition、原因を確認してください。

</details>

## 4. active controller の合計値が 2 なら、すぐに split brain と判断できますか？

<details>
<summary>解答を表示</summary>

いいえ。最初にクラスターの対象範囲、重複ターゲット、古いサンプル、スクレイプのタイミングを確認します。1 クラスターの controller 数の定常状態の合計は 1 です。

</details>

## 5. `BrokerRequestHandlerAvgIdlePercent` が低い場合、何と関連付けて調べますか？

<details>
<summary>解答を表示</summary>

CPU、GC、I/O、リクエストのレイテンシー／キュー、スループットと合わせて確認します。この値は handler が忙しいことを示しますが、CPU だけが原因だと断定したり、スレッドや broker を自動的に増やす根拠にしたりはできません。

</details>

## 6. broker の JMX マッピングだけで consumer group の lag を計算できますか？

<details>
<summary>解答を表示</summary>

いいえ。group が commit した offset と partition の末尾 offset の両方が必要です。この章では Strimzi Kafka Exporter を使います。KEDA は別経路で Kafka API に問い合わせます。

</details>

## 7. 使用する Kafka Exporter の lag メトリクス名と group label を挙げ、以前のプロジェクトの状態も説明してください。

<details>
<summary>解答を表示</summary>

メトリクスは `kafka_consumergroup_lag`、group label は `consumergroup` です。以前の `seglo/kafka-lag-exporter` はアーカイブされています。その exporter の `kafka_consumergroup_group_lag`／`group` という名前と、この exporter のものを混同しないでください。

</details>

## 8. PodMonitor は常に ServiceMonitor より信頼性が高いですか？

<details>
<summary>解答を表示</summary>

いいえ。Service と selector が正しければ ServiceMonitor も使えます。この章では Pod を直接検出する方式を選んでいます。Prometheus の label／namespace selector、RBAC、ネットワーク、重複スクレイプを確認してください。

</details>

## 9. PrometheusRule における `for: 5m` とデータ欠落の扱いを説明してください。

<details>
<summary>解答を表示</summary>

アラートが発火するには、条件が 5 分間存在し、真であり続ける必要があります。これはスクレイプ間隔でも平均値でもありません。メトリクス群が欠落すると sum の比較結果が空になることがあるため、`absent` とスクレイプ範囲の確認も追加してください。

</details>

## 10. KEDA の Kafka scaler は Prometheus lag exporter を必要としますか？

<details>
<summary>解答を表示</summary>

いいえ。Kafka API に直接問い合わせます。そのため、ダッシュボード用 exporter とは別に、broker への接続、TLS、認証、Secret へのアクセスが必要です。

</details>

## 11. lag が 0 なら、ビジネス処理が完了したと証明できますか？

<details>
<summary>解答を表示</summary>

いいえ。通常は log-end の次 offset から commit 済みの次 offset を差し引いて測ります。早すぎる commit やデータ／収集条件によって、ビジネス処理の完了状況とは異なる場合があります。compaction やトランザクションによって、物理的なレコード数とも一致しないことがあります。

</details>

## 12. `bytesin_total` と `idle_percent` はどのようにクエリしますか？

<details>
<summary>解答を表示</summary>

秒あたりのスループットには、counter である `bytesin_total` に `rate(...[5m])` を使います。`idle_percent` はすでに比率を表す gauge なので、さらに `rate` を適用せず、その値を直接確認します。

</details>

## 13. `lagThreshold=50` と `minReplicaCount=1` の意味を説明してください。

<details>
<summary>解答を表示</summary>

目標はレプリカあたりの実効 lag 合計 50 です。おおよその台数は `ceil(合計 lag / 50)` ですが、HPA／scaler の調整や上限の影響を受けます。partition ごとに consumer が複数作られるわけではありません。最小数が 1 の場合は、ゼロへの activation／cooldown ではなく、HPA の scale-down 動作を確認してください。

</details>

## 14. ISR の変化と topic のスループットから何が分かりますか？その限界は何ですか？

<details>
<summary>解答を表示</summary>

ISR の shrink／expand counter の rate から、レプリケーションの健全性と関連付けるべき変動を把握できます。topic 全体のスループットだけでは負荷の高い partition を特定できません。partition と client の観察データも追加してください。

</details>

## 15. 既存 Kafka リソースに、この章の metricsConfig と Kafka Exporter を追加する patch を書いてください。

<details>
<summary>解答を表示</summary>

```yaml
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
  kafkaExporter:
    topicRegex: ^orders$
    groupRegex: ^order-processor$
    showAllOffsets: true
    template:
      pod:
        metadata:
          labels:
            docs.example.com/kafka-monitor: lag
```

先に `metrics-config.yaml` を作成し、次に `kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml` を実行します。これは Kafka を新規作成する完全な manifest ではなく、既存の認証設定と listener を保持します。

</details>

## 16. 同じ namespace 内の TLS／SCRAM と TriggerAuthentication を使う ScaledObject を書いてください。

<details>
<summary>解答を表示</summary>

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: kafka
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1
  maxReplicaCount: 10
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
      version: 4.3.1
      consumerGroup: order-processor
      topic: orders
      tls: enable
      sasl: scram_sha512
      lagThreshold: '50'
      allowIdleConsumers: 'false'
      offsetResetPolicy: earliest
    authenticationRef:
      name: kafka-lag-auth
```

この構成には、章の `keda-auth.yaml` と既存の `kafka/order-consumer` Deployment が必要です。アプリケーションは `order-processor` として consume しなければなりません。最大 10 replica はパート 2 の 12 partition に合わせた値です。別のトポロジーでは調整してください。

</details>

## 17. under-replication アラートで、クラスター範囲、`for`、データ欠落の扱いをどのように分けますか？

<details>
<summary>解答を表示</summary>

namespace=`kafka`、`kafka_cluster`=`my-cluster` に gauge の対象を絞り、クラスター単位で合計して、`> 0` の条件に `for: 5m` を適用します。node のスクレイプ範囲不足と controller メトリクス欠落は別ルールで検出します。lag については exporter の失敗、想定 group の欠落、負の committed offset も監視してください。

</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/07-monitoring.md) | [前のクイズ](./06-msk-integration-quiz.md) | [次のクイズ](./08-best-practices-quiz.md)
