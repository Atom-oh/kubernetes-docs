# パート7: モニタリング

> **サポート対象バージョン**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **最終更新**: July 9, 2026

Kafka クラスターには、broker の heap、disk、network のグラフだけでなく、問題を早期に検出するために partition replication の健全性と consumer の処理速度を可視化する必要があります。このドキュメントでは、Strimzi が公開する broker metrics を Prometheus でスクレイピングする方法、consumer lag を個別に測定する方法、KEDA で consumer をオートスケーリングする方法を扱います。

## 1. Strimzi による Metrics の公開方法

Strimzi は、broker/controller/Connect の各コンポーネント container 内で Prometheus JMX Exporter を実行します。これは別個の sidecar container ではなく、同じ JVM プロセスにロードされる **JVM Java agent** です。JMX Exporter は JVM 内部の JMX MBeans（例: `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`）を読み取り、Prometheus テキスト形式の `/metrics` HTTP endpoint に変換します。どの MBeans をどの metric 名と label にマッピングするかは、`ConfigMap` に保存された relabeling configuration で定義され、`Kafka` CR の `metricsConfig` フィールドがその `ConfigMap` を参照します。

Strimzi の upstream repository には、broker、Connect、Cruise Control 用の JMX Exporter configuration の例が [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics) 配下にあります。実運用では、チームは通常これらの例を出発点として、relabeling rule を一から作成するのではなく、必要な rule だけを調整します。

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

`metricsConfig` を適用すると、Strimzi は各 broker container 内で JMX Exporter Java agent を自動的に有効化し、参照先の `ConfigMap` の rule file を同じ container にマウントします。その後、各 broker pod の port `9404`（デフォルト）の `/metrics` path で Prometheus 形式の metrics をスクレイピングできるようになります。同じ `metricsConfig` フィールドは、`KafkaConnect`、`KafkaMirrorMaker2`、`CruiseControl` custom resource でも利用できます。

## 2. 主要な Broker Metrics

Kafka は多数の JMX metrics を公開するため、日常的に実際に重要なものに絞り込むと役立ちます。

| Metric | 意味 | 健全な値 / 注意すべき点 |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | この broker が leader となっている partition のうち、in-sync replica (ISR) set が設定済み replication factor より小さいものの数 | **0 であるべきです。** 0 を超える値は、1 つ以上の follower が leader に遅れを取っていることを意味します。network latency、broker overload、disk I/O bottleneck を調査してください。 |
| `kafka_controller_kafkacontroller_activecontrollercount` | この broker/controller が現在 active controller かどうか（0 または 1） | クラスター全体の**合計は必ず 1**でなければなりません。合計が 0 の場合は active controller がいないことを意味します（leader election の進行中または障害）。合計が 2 以上の場合は split-brain 状態が示唆され、直ちに調査が必要です。 |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | broker の request-handler thread pool が idle 状態にある時間の割合 | 値の低下（例: 20% 未満）は、broker が CPU/thread saturation に近づいていることを示します。低い値が継続する場合は、broker の scale out または partition の rebalance が必要であることを示します。 |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | topic ごとの 1 秒あたりの produce/consume throughput（bytes） | broker/network の capacity planning や、個々の topic（hot partition）における traffic spike の検出に使用します。 |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | replica が 1 秒あたりに ISR set から離脱（shrink）または再参加（expand）する rate | 頻繁な shrink は follower が繰り返し同期から外れていることを意味し、通常は under-replicated partition の増加に先行します。 |

これらのうち、**under-replicated partition count** と **active controller count** は、クラスターの data safety と availability を最も直接的に反映するため、すべての dashboard と alert rule set の最上位に配置すべきです。

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Consumer Lag のモニタリング

**Consumer lag** は partition ごとに、最新の produce offset（log end offset）と consumer group が commit した最後の offset との差です。lag が継続的に増加している場合、consumer group が produce rate に追いつけないことを意味し、処理の遅延、停止した consumer、または繰り返される rebalance の兆候です。

この in-process Java agent により Strimzi が公開する JMX Exporter metrics は、**broker 自身の状態**（上記セクション 2）を表すものであり、デフォルトでは consumer group offset や lag は含まれません。lag の算出には、consumer group の commit 済み offset（内部 `__consumer_offsets` topic で追跡）と各 topic の最新 offset を関連付ける必要があり、これは broker 側 exporter の対象範囲外です。このため、チームは通常 consumer lag 専用の別の exporter を実行します。

最も広く使用されている選択肢は、community project の [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter)（または類似の Burrow-style exporter）です。これはクラスター内の独自の `Deployment` として実行されます。一定間隔で Kafka Admin API を polling し、各 consumer group の commit 済み offset と各 topic の最新 offset を読み取り、`kafka_consumergroup_group_lag`（group、topic、partition 別の lag）などの metrics を Prometheus 形式で公開します。

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

この exporter を deployment し、Prometheus がその `/metrics` endpoint をスクレイピングすると、lag は次のように query できます。

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. ServiceMonitor / PodMonitor による Scraping の接続

Prometheus Operator（kube-prometheus-stack など）を実行している環境では、通常は `scrape_configs` を手動で編集せず、label により target を検出する `PodMonitor` CRD を宣言します。broker は固定された `Service` の背後ではなく Strimzi により管理される pod として実行されるため、`Service` ベースの `ServiceMonitor` に依存するよりも、`PodMonitor` で pod を直接選択するほうが信頼性が高くなります。

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

metrics の収集が開始されたら、under-replicated partition に対する alerting が最も基本的な safety net です。以下の `PrometheusRule` は、under-replicated partition が少なくとも 5 分間 0 を上回り続けたときに発火します。

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

## 5. KEDA による Consumer のオートスケーリング

CPU/memory ベースの HPA は、consumer workload の実際の負荷、つまり処理待ちの message 数を反映できないことがよくあります。KEDA の Kafka scaler（`triggers.type: kafka`）では、代わりに **consumer group lag** に基づいて consumer `Deployment` をスケーリングできます。KEDA は Kafka Admin API を通じて、設定された topic/consumer group の lag を直接 query するため、スケーリング判断にセクション 3 の別の lag exporter は厳密には必要ありません（ただし、その exporter は dashboard と alerting に引き続き有用です）。

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

主な trigger parameter:

* **`bootstrapServers`**: lag を query するために KEDA が使用する Kafka クラスターの bootstrap address
* **`consumerGroup`**、**`topic`**: lag を測定する consumer group と topic
* **`lagThreshold`**: KEDA が replica を 1 つ追加する partition ごとの lag 値（例: partition ごとの lag が 50 増加するごとに replica を 1 つ追加）
* **`activationLagThreshold`**: 0 から 1 replica への初回 scale-up を trigger するために必要な最小 lag。未設定の場合、少量の lag でも直ちに 1 に scale します。
* **`allowIdleConsumers`**: `false`（デフォルト）の場合、KEDA は consumer 数が consume 対象の partition 数を超えないように replica 数を上限設定します。

この `ScaledObject` を適用すると、KEDA Operator は内部で標準の Kubernetes HPA を作成・管理し、lag が収まった後に `cooldownPeriod` を経て scale down します。scaler type、architecture、zero scaling など、より広範な KEDA の概念については、専用の [オートスケーリング: KEDA](../../autoscaling/01-keda.md) ドキュメントを参照してください。

## 6. Grafana Dashboards

Strimzi は GitHub repository の [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) 配下に、broker、ZooKeeper（legacy mode）、Kafka Connect、Cruise Control 用の Grafana dashboard JSON の例を提供しています。これらを import して cluster name/namespace variable を調整するほうが、通常は panel を一から作成するよりも高速です。

堅実な Kafka dashboard では、少なくとも以下の panel group をカバーすべきです。

* **Broker health**: broker ごとの uptime、JVM heap usage、GC pause time、request-handler/network idle ratio
* **ISR/replication status**: under-replicated partition count、ISR shrink/expand rate、active controller count（クラスター全体の合計）
* **Throughput**: topic ごとおよび broker ごとの 1 秒あたりの bytes in/out、1 秒あたりの messages、partition 間の throughput imbalance（hot-partition の検出）
* **Consumer lag**: consumer group ごとの lag trend。突然の spike の原因を特定するため rebalance event と関連付けます。

## 次のステップ

metrics collection、alerting、autoscaling を導入したら、次のステップはこれらすべてを実際の運用標準、すなわち SLO、capacity planning、incident response procedure に適用することです。これについては[パート8: ベストプラクティス](./08-best-practices.md)で扱います。

[メインページに戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)に挑戦してください。
