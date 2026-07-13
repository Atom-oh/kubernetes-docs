# パート 7: モニタリングクイズ

このクイズでは、Strimzi がメトリクスを公開する方法、主要な broker メトリクスの意味、consumer lag の測定方法、そして KEDA Kafka scaler の設定方法についての理解を確認します。

## 選択問題

1. 各 broker container 内で Strimzi は何を実行し、JMX メトリクスを Prometheus が scrape できる形式に変換しますか？
   - A) Fluent Bit sidecar
   - B) Prometheus JMX Exporter (JVM Java agent)
   - C) OpenTelemetry Collector DaemonSet
   - D) cAdvisor

<details>

<summary>答えを表示</summary>

**答え: B) Prometheus JMX Exporter (JVM Java agent)**

**解説:**
`Kafka` CR で `metricsConfig` が設定されている場合、Strimzi は各 broker（および Connect など）container 内で Prometheus JMX Exporter を自動的に有効化します。これは別個の sidecar container としてではなく、同じ JVM process にロードされる Java agent として動作します。この exporter は JVM 内部の JMX MBean 値を読み取り、relabeling rules に従って名前を変更し、`/metrics` HTTP endpoint で Prometheus text format として公開します。Fluent Bit は log collector であり、cAdvisor は container resource metrics を収集します。どちらもこの目的には使用されません。
</details>

2. `Kafka.spec.kafka.metricsConfig` は、JMX Exporter の relabeling rules を取得するために、どの種類の resource を参照しますか？
   - A) Secret
   - B) PersistentVolumeClaim
   - C) ConfigMap
   - D) CustomResourceDefinition

<details>

<summary>答えを表示</summary>

**答え: C) ConfigMap**

**解説:**
`metricsConfig.valueFrom.configMapKeyRef` は、relabeling rules（YAML）を含む `ConfigMap` の名前と key を指します。Strimzi はこの rules file を JMX Exporter Java agent が動作する container に mount し、どの JMX MBeans をどの Prometheus metric names と labels に対応させるかを認識できるようにします。`Secret` は certificates や credentials などの機密値のためのものであり、この目的には使用されません。
</details>

3. `kafka_server_replicamanager_underreplicatedpartitions` metric の健全な値は何ですか？
   - A) brokers の数と等しい必要がある
   - B) partitions の数と等しい必要がある
   - C) 常に 0 である必要がある
   - D) 常に 1 である必要がある

<details>

<summary>答えを表示</summary>

**答え: C) 常に 0 である必要がある**

**解説:**
この metric は、特定の broker が leader である partitions のうち、in-sync replica (ISR) set が設定された replication factor より小さいものを数えます。通常運用では、すべての follower が leader に追従している必要があるため、この値は 0 であるべきです。0 を超える値は、一部の replicas が遅れていることを示します。多くの場合、network latency、broker overload、または disk I/O bottlenecks が原因です。また、leader がその後 insufficient ISR の状態で失敗した場合、data durability に対する直接的なリスクになります。
</details>

4. 健全な運用状態では、cluster 全体で合計した `kafka_controller_kafkacontroller_activecontrollercount` はいくつであるべきですか？
   - A) 0
   - B) brokers の数と等しい
   - C) 正確に 1
   - D) controller candidates の数と等しい

<details>
<summary>答えを表示</summary>

**答え: C) 正確に 1**

**解説:**
各 broker/controller は、自身が現在 active controller であるかどうかを 0 または 1 として公開します。これを cluster 全体で合計すると、健全な運用状態では正確に 1 になるはずです。合計が 0 の場合は active controller が存在しない（leader election が進行中、または障害）ことを意味し、合計が 2 以上の場合は split-brain condition のような深刻な異常を示唆するため、直ちに調査が必要です。
</details>

5. Request Handler Idle Ratio が継続的に低い（たとえば 10% 未満）場合、最初に何を疑うべきですか？
   - A) Disk capacity が不足しつつある
   - B) broker が CPU/thread resources の飽和に近づいている
   - C) ZooKeeper connection が切断された
   - D) consumer group が rebalancing している

<details>
<summary>答えを表示</summary>

**答え: B) broker が CPU/thread resources の飽和に近づいている**

**解説:**
Request Handler Idle Ratio は、broker の request-handling thread pool が idle である時間の割合です。値が低い場合、thread pool が常に request processing で忙しいことを意味し、broker が CPU または thread capacity limits に近づいていることを示します。継続的に低い値は、brokers の scale out、partitions の rebalancing、または thread pool size の tuning を検討する合図です。
</details>

6. Strimzi がデフォルトで公開する broker metrics に consumer group lag が含まれないのはなぜですか？
   - A) Consumer lag は機密情報であり、security 上の理由により公開できない
   - B) lag の計算には consumer group の committed offsets と topic の latest offsets の関連付けが必要だが、JMX Exporter は broker 自身の JMX MBeans のみを読み取るため
   - C) 使用されている Strimzi version が古すぎて対応していないため
   - D) Consumer lag は client side からしか測定できないため

<details>
<summary>答えを表示</summary>

**答え: B) lag の計算には consumer group の committed offsets と topic の latest offsets の関連付けが必要だが、JMX Exporter は broker 自身の JMX MBeans のみを読み取るため**

**解説:**
JMX Exporter Java agent は、broker process 内部の JMX MBeans（replication state、throughput、controller status など）のみを読み取って公開します。Consumer lag は、consumer group が最後に commit した offset と topic の latest（log end）offset の差であり、Kafka Admin API を通じて両方の値を別々に query する必要があります。そのため、consumer lag は通常 `kafka-lag-exporter` のような専用 tool で測定されます。
</details>

7. このドキュメントで consumer lag を測定するために紹介されている community exporter はどれですか？
   - A) node-exporter
   - B) kafka-lag-exporter
   - C) blackbox-exporter
   - D) kube-state-metrics

<details>
<summary>答えを表示</summary>

**答え: B) kafka-lag-exporter**

**解説:**
`kafka-lag-exporter` は community project であり、Kafka Admin API を介して consumer group の committed offsets と各 topic の latest offsets を定期的に query し、`kafka_consumergroup_group_lag` などの metrics を Prometheus format で公開します。`node-exporter` は host system metrics を収集し、`blackbox-exporter` は endpoints を probe し、`kube-state-metrics` は Kubernetes object state を報告します。これらはいずれもこの目的には使用されません。
</details>

8. Prometheus Operator 環境で Strimzi-managed Kafka broker pods を scrape する場合、固定の `Service` を対象にするより信頼性が高い CRD はどれですか？
   - A) ServiceMonitor
   - B) PodMonitor
   - C) Probe
   - D) AlertmanagerConfig

<details>
<summary>答えを表示</summary>

**答え: B) PodMonitor**

**解説:**
Brokers は Strimzi によって管理される個別の Pod（ポッド）として動作します。`strimzi.io/cluster` などの label によって Pods を直接選択する `PodMonitor` は、固定の `Service` endpoint を対象にする `ServiceMonitor` よりも scrape targets をより信頼性高く検出します。`Probe` は blackbox-style endpoint checks のためのものであり、`AlertmanagerConfig` は alert routing を設定します。どちらも Pod-level metric scraping のためのものではありません。
</details>

9. under-replicated partitions に関する `PrometheusRule` alert で、`for: 5m` は何をしますか？
   - A) 5 分ごとに metrics を scrape する
   - B) alert が実際に fire する前に、condition が 5 分間継続して true である必要がある
   - C) alert が fire してから 5 分後に自動的に解決する
   - D) 値の 5 分平均を計算する

<details>
<summary>答えを表示</summary>

**答え: B) alert が実際に fire する前に、condition が 5 分間継続して true である必要がある**

**解説:**
Prometheus alerting rule では、`for` field は `expr` の condition が指定された duration の間 true のままでなければ、alert が `pending` から `firing` に遷移しないことを意味します。`for: 5m` を設定すると、一時的な spikes による noisy alerts が減り、本当に継続している問題に対してのみ alerts が fire されるようになります。
</details>

10. KEDA の Kafka scaler は、consumer group の lag をどのように判定しますか？
    - A) kafka-lag-exporter が公開する Prometheus metrics を scrape する
    - B) Kafka Admin API を直接 query する
    - C) broker の JMX Exporter `/metrics` endpoint を parse する
    - D) ZooKeeper に保存された offsets を読み取る

<details>
<summary>答えを表示</summary>

**答え: B) Kafka Admin API を直接 query する**

**解説:**
KEDA の Kafka scaler は、`bootstrapServers`、`consumerGroup`、`topic` などの trigger parameters を使用して Kafka Admin API を直接呼び出し、consumer group の lag を判定します。つまり、`kafka-lag-exporter` のような別の Prometheus exporter は scaling decisions には必ずしも必要ありません（ただし dashboards や alerting には引き続き有用です）。KRaft mode では ZooKeeper は offsets を保存しなくなっています。
</details>

## 短答問題

11. consumer lag を一文で定義してください。

<details>
<summary>答えを表示</summary>

**答え: partition ごとに、latest produced offset（log end offset）と consumer group が最後に commit した offset との差。**

**解説:**
Consumer lag は、consumer がまだ処理していない messages の数を offsets 単位で測定します。lag が 0 であることは、consumer が latest message に追いついていることを意味します。lag が継続的に増加している場合、consumer の processing rate が produce rate に追いついていないことを示します。
</details>

12. Strimzi が Kafka broker の JMX metrics を `/metrics` HTTP endpoint に変換するために使用する component の名前は何ですか？

<details>
<summary>答えを表示</summary>

**答え: Prometheus JMX Exporter (a JVM Java agent)**

**解説:**
JMX Exporter は JVM JMX MBean values を読み取り、configured rules に従って rename と relabel を行い、`/metrics` path で Prometheus が scrape 可能な text format として公開します。`metricsConfig` が設定されている場合、Strimzi は brokers などの component containers 上で、同じ JVM process 内の Java agent としてこれを自動的に有効化します。別個の sidecar container としてではありません。
</details>

13. KEDA `ScaledObject` の Kafka trigger で、追加 replicas が追加される基準となる per-partition lag value を設定する parameter は何ですか？

<details>
<summary>答えを表示</summary>

**答え: `lagThreshold`**

**解説:**
`lagThreshold` は許容される per-partition lag value です。実際の lag がこの値の倍数を超えるたびに、KEDA が管理する HPA は別の replica を追加します。たとえば、`lagThreshold: "50"` で partition lag が 120 の場合、必要な数としておよそ 2〜3 replicas が計算されます。別途、`activationLagThreshold` は 0 から 1 replica への初期 scale-up がそもそも発生するかどうかを決定します。
</details>

14. under-replicated partitions が増加する前の leading indicator として使用でき、replicas が ISR set から離脱または再参加する頻度を表す metrics の組み合わせは何ですか？

<details>
<summary>答えを表示</summary>

**答え: ISR Shrink Rate and ISR Expand Rate (`isrshrinkspersec`, `isrexpandspersec`)**

**解説:**
ISR Shrink Rate は replicas が ISR set から drop out する per-second rate であり、ISR Expand Rate は replicas が再参加する rate です。頻繁な shrink は followers が leader に対して繰り返し遅れていることを示し、多くの場合 under-replicated partitions の増加に先行します。そのため、有用な early-warning signal になります。
</details>

## ハンズオン問題

15. `kafka-metrics-config.yml` という key を持つ `kafka-metrics` という名前の `ConfigMap` を参照する、`Kafka` CR の `metricsConfig` の YAML を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

**解説:**
`type: jmxPrometheusExporter` は現在 Strimzi が support する唯一の metrics exposition type であり、`valueFrom.configMapKeyRef` は relabeling rules を保持する `ConfigMap` と、その中の key を指定します。適用されると、Strimzi Cluster Operator は broker containers 内で JMX Exporter Java agent を自動的に有効化し、参照された rules file を mount します。
</details>

16. topic `orders` 上の consumer group `order-consumer-group` の lag に基づき、per-partition lag threshold 50 を使用して、`order-consumer` `Deployment` を 1 から 10 replicas の間で scale する KEDA `ScaledObject` を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: order-consumer
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9092
        consumerGroup: order-consumer-group
        topic: orders
        lagThreshold: "50"
```

**解説:**
`scaleTargetRef.name` は対象の `Deployment` を識別し、`minReplicaCount`/`maxReplicaCount` は scaling range を制限します。`triggers` の下の `type: kafka` は Kafka scaler を選択し、その `metadata` は bootstrap servers、consumer group、topic、lag threshold を指定します。KEDA Operator はこの resource を使用して標準の Kubernetes HPA を作成および管理します。
</details>

17. under-replicated partitions が 0 を超えた状態で少なくとも 5 分間続いた場合に、`warning` severity の alert を fire する `PrometheusRule` を書いてください。

<details>
<summary>答えを表示</summary>

**答え:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-broker-alerts
  namespace: kafka
spec:
  groups:
    - name: kafka-broker.rules
      rules:
        - alert: KafkaUnderReplicatedPartitions
          expr: sum(kafka_server_replicamanager_underreplicatedpartitions) > 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Kafka cluster has under-replicated partitions"
            description: "Under-replicated partitions have been above 0 for over 5 minutes."
```

**解説:**
`expr` は cluster 全体の under-replicated partitions を合計し、その total が 0 を超えているかどうかを確認します。`for: 5m` は、alert が `firing` に遷移する前に condition が 5 分間維持されることを要求し、一時的な spikes による noise を減らします。`labels.severity` は Alertmanager routing で使用するために alert の severity を分類します。
</details>

---

[学習資料に戻る](../../../data-on-eks/kafka/07-monitoring.md) | [前のクイズ: MSK Integration](./06-msk-integration-quiz.md) | [次のクイズ: Best Practices](./08-best-practices-quiz.md)
