# Part 7: Monitoring

> **対応バージョン**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **最終更新**: July 9, 2026

Kafka cluster には、broker の heap、disk、network のグラフだけでは不十分です。問題を早期に検出するには、partition replication の健全性と consumer の処理速度も可視化する必要があります。このドキュメントでは、Strimzi が Prometheus 向けに公開する broker metrics のスクレイピング、consumer lag の個別測定、そして KEDA による consumer の autoscaling について説明します。

## 1. Strimzi が Metrics を公開する仕組み

Strimzi は各 broker/controller/Connect component container の内部で Prometheus JMX Exporter を実行します。これは独立した sidecar container ではなく、同じ JVM process に読み込まれる **JVM Java agent** です。JMX Exporter は JVM 内部の JMX MBeans（例: `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`）を読み取り、Prometheus text-format の `/metrics` HTTP endpoint に変換します。どの MBeans をどの metric name と label に map するかは、`ConfigMap` に保存された relabeling configuration で定義され、`Kafka` CR の `metricsConfig` field がその `ConfigMap` を参照します。

Strimzi upstream repository には、broker、Connect、Cruise Control 向けの JMX Exporter configuration の例が [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics) 配下に含まれています。実運用では、team はこれらの例を出発点にし、relabeling rule をゼロから書くのではなく、必要な rule だけを調整するのが一般的です。

```yaml
# kafka-metrics-config.yaml (excerpt, based on Strimzi's example)
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
      # Under-replicated partition count
      - pattern: "kafka.server<type=ReplicaManager, name=UnderReplicatedPartitions><>Value"
        name: "kafka_server_replicamanager_underreplicatedpartitions"
      # Active controller count (KRaft)
      - pattern: "kafka.controller<type=KafkaController, name=ActiveControllerCount><>Value"
        name: "kafka_controller_kafkacontroller_activecontrollercount"
      # Request handler idle ratio
      - pattern: "kafka.server<type=KafkaRequestHandlerPool, name=RequestHandlerAvgIdlePercent><>OneMinuteRate"
        name: "kafka_server_kafkarequesthandlerpool_requesthandleravgidlepercent_oneminuterate"
      # Per-topic bytes in/out
      - pattern: "kafka.server<type=BrokerTopicMetrics, name=(BytesInPerSec|BytesOutPerSec), topic=(.+)><>OneMinuteRate"
        name: "kafka_server_brokertopicmetrics_$1_oneminuterate"
        labels:
          topic: "$2"
```

```yaml
# Kafka CR referencing the ConfigMap above via metricsConfig
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    # ...
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

`metricsConfig` が適用されると、Strimzi は各 broker container 内で JMX Exporter Java agent を自動的に有効化し、参照された `ConfigMap` の rules file を同じ container に mount します。その後、Prometheus-format metrics は各 broker Pod の port `9404`（default）の `/metrics` path で scrape 可能になります。同じ `metricsConfig` field は、`KafkaConnect`、`KafkaMirrorMaker2`、`CruiseControl` custom resources でも利用できます。

## 2. 主要な Broker Metrics

Kafka は多数の JMX metrics を公開するため、日常的に本当に重要なものに絞り込むと役立ちます。

| Metric | 意味 | 健全な値 / 監視すべき点 |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | この broker が leader であり、in-sync replica (ISR) set が設定された replication factor より小さい partition の数 | **0 であるべきです。** 0 を超える値は、1 つ以上の follower が leader に遅れていることを意味します。network latency、broker overload、または disk I/O bottleneck を調査してください。 |
| `kafka_controller_kafkacontroller_activecontrollercount` | この broker/controller が現在 active controller かどうか（0 または 1） | cluster-wide の **sum は必ず 1** でなければなりません。sum が 0 の場合は active controller が存在しない（leader election 進行中または failure）ことを意味します。sum が 2 以上の場合は split-brain condition の可能性があり、直ちに調査が必要です。 |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | broker の request-handler thread pool が idle 状態にある時間の割合 | 値の低下（例: 20% 未満）は、broker が CPU/thread saturation に近づいていることを示します。低い値が継続する場合は、broker の scale out または partition rebalance の合図です。 |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | topic ごとの produce/consume throughput（bytes per second） | broker/network capacity planning と、個別 topic の traffic spike（hot partition）検出に使用します。 |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | replica が ISR set から離脱（shrink）または再参加（expand）する per-second rate | shrink が頻発する場合、follower が繰り返し sync から外れていることを意味し、通常 under-replicated partitions の増加に先行します。 |

これらのうち、**under-replicated partition count** と **active controller count** は cluster の data safety と availability を最も直接的に反映するため、すべての dashboard と alert rule set の最上位に置くべきです。

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Consumer Lag Monitoring

**Consumer lag** とは、partition ごとに、最後に produce された offset（log end offset）と consumer group が最後に commit した offset の差です。lag が継続的に増加する場合、consumer group が produce rate に追いついていないことを意味します。これは処理の遅さ、停止した consumer、または繰り返される rebalancing の兆候です。

Strimzi がこの in-process Java agent を通じて公開する JMX Exporter metrics は、**broker 自身の状態**（上記 section 2）を表すものであり、default では consumer group offset や lag は含まれません。lag の計算には、consumer group の committed offset（internal `__consumer_offsets` topic で tracking される）と各 topic の latest offset を相関させる必要があり、これは broker-side exporter の範囲外です。そのため、team は通常、consumer lag 専用の exporter を別途実行します。

最も広く使われている選択肢は community project の [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter)（または類似の Burrow-style exporter）で、cluster 内で独自の `Deployment` として実行します。これは一定 interval で Kafka Admin API を poll し、各 consumer group の committed offset と各 topic の latest offset を読み取り、その後 Prometheus format で `kafka_consumergroup_group_lag`（group、topic、partition ごとに分解された lag）などの metrics を公開します。

```yaml
# Minimal ConfigMap for kafka-lag-exporter
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-lag-exporter-config
  namespace: kafka
data:
  application.conf: |
    kafka-lag-exporter {
      port = 8000
      clusters = [
        {
          name = "my-cluster"
          bootstrap-brokers = "my-cluster-kafka-bootstrap.kafka.svc:9092"
        }
      ]
      poll-interval = 30 seconds
    }
```

この exporter が deploy され、Prometheus がその `/metrics` endpoint を scrape するようになると、lag は次のように query できます。

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. ServiceMonitor / PodMonitor による Scraping の接続

Prometheus Operator（kube-prometheus-stack など）を実行している環境では、通常 `scrape_configs` を手で編集するのではなく、label によって target を discovery する `PodMonitor` CRD を宣言します。broker は固定の `Service` の背後ではなく、Strimzi が管理する Pod として実行されるため、`Service`-based の `ServiceMonitor` に依存するよりも、`PodMonitor` で Pod を直接選択する方が信頼性が高くなります。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-broker-metrics
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      strimzi.io/kind: Kafka
      strimzi.io/cluster: my-cluster
  namespaceSelector:
    matchNames:
      - kafka
  podMetricsEndpoints:
    - port: tcp-prometheus
      path: /metrics
      interval: 30s
```

metrics が流れ始めたら、under-replicated partitions に対する alerting は導入すべき最も基本的な safety net です。以下の `PrometheusRule` は、under-replicated partitions が少なくとも 5 分間 0 を超えたままの場合に発火します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-broker-alerts
  namespace: kafka
  labels:
    release: kube-prometheus-stack
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
            description: "Under-replicated partitions have been above 0 for over 5 minutes. Check follower brokers for lag or failure."
        - alert: KafkaNoActiveController
          expr: sum(kafka_controller_kafkacontroller_activecontrollercount) != 1
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "Abnormal Kafka active controller count"
            description: "The cluster-wide sum of active controllers is not 1. Check controller leader election status."
```

## 5. KEDA による Consumer の Autoscaling

CPU/memory-based HPA は、consumer workload の実際の load、つまり処理待ち message の数を反映できないことがよくあります。KEDA の Kafka scaler（`triggers.type: kafka`）を使うと、代わりに **consumer group lag** に基づいて consumer `Deployment` を scale できます。KEDA は設定された topic/consumer group の lag を Kafka Admin API 経由で直接 query するため、scaling decision には section 3 の別個の lag exporter は必須ではありません（ただし、その exporter は dashboard と alerting には引き続き有用です）。

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
  cooldownPeriod: 60
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9092
        consumerGroup: order-consumer-group
        topic: orders
        lagThreshold: "50"
        activationLagThreshold: "5"
        allowIdleConsumers: "false"
```

主要な trigger parameters:

* **`bootstrapServers`**: KEDA が lag を query するために使用する Kafka cluster の bootstrap address
* **`consumerGroup`**, **`topic`**: lag を測定する consumer group と topic
* **`lagThreshold`**: この値を超えると KEDA が replica を追加する per-partition lag value（例: per-partition lag 50 units ごとに 1 つの追加 replica）
* **`activationLagThreshold`**: 0 から 1 replica への初回 scale-up を trigger するために必要な最小 lag。未設定の場合、少量の lag でも即座に 1 に scale します。
* **`allowIdleConsumers`**: `false`（default）の場合、KEDA は consume する partition 数より多くの consumer を作成しないように replica 数を制限します。

この `ScaledObject` が適用されると、KEDA Operator は背後で標準の Kubernetes HPA を作成・管理し、lag が低下した後、`cooldownPeriod` 経過後に scale down します。より広範な KEDA の概念 — scaler types、architecture、zero scaling — については、専用の [Autoscaling: KEDA](../../autoscaling/01-keda.md) ドキュメントを参照してください。

## 6. Grafana Dashboards

Strimzi は GitHub repository 内の [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) 配下で、broker、ZooKeeper（legacy mode）、Kafka Connect、Cruise Control 向けの Grafana dashboard JSON 例を提供しています。これらを import して cluster name/namespace variables を調整する方が、panel をゼロから構築するより一般的に高速です。

堅実な Kafka dashboard には、少なくとも次の panel groups を含めるべきです。

* **Broker health**: broker ごとの uptime、JVM heap usage、GC pause time、request-handler/network idle ratio
* **ISR/replication status**: under-replicated partition count、ISR shrink/expand rate、active controller count（cluster-wide sum）
* **Throughput**: topic ごとおよび broker ごとの bytes in/out per second、messages per second、partition ごとの throughput imbalance（hot-partition detection）
* **Consumer lag**: consumer group ごとの lag trend。rebalance events と相関させて、急激な spike の原因を特定します。

## Next Steps

metrics collection、alerting、autoscaling が整ったら、次の step はこれらすべてを実際の運用標準 — SLOs、capacity planning、incident response procedures — に適用することです。これは [Part 8: Best Practices](./08-best-practices.md) で扱います。

[Main Page に戻る](./)

## Quiz

この chapter で学んだ内容を確認するには、[Topic Quiz](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md) に挑戦してください。
