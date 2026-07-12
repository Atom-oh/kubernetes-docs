# 第 7 部分：监控

> **支持的版本**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **最后更新**: July 9, 2026

Kafka cluster 需要的不仅仅是 broker heap、disk 和 network 图表 —— 你还需要了解 partition replication health 和 consumer processing speed，才能及早发现问题。本文档介绍如何使用 Prometheus 抓取 Strimzi 暴露的 broker metrics、单独衡量 consumer lag，以及使用 KEDA 自动扩展 consumers。

## 1. Strimzi 如何暴露 Metrics

Strimzi 会在每个 broker/controller/Connect component container 内运行 Prometheus JMX Exporter —— 不是作为单独的 sidecar container，而是作为加载到同一个 JVM process 中的 **JVM Java agent**。JMX Exporter 会读取 JVM 内部的 JMX MBeans（例如 `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`），并将它们转换为 Prometheus text-format 的 `/metrics` HTTP endpoint。哪些 MBeans 映射到哪些 metric names 和 labels，由存储在 `ConfigMap` 中的 relabeling configuration 定义，而 `Kafka` CR 的 `metricsConfig` 字段会指向该 `ConfigMap`。

Strimzi upstream repository 在 [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics) 下提供了 broker、Connect 和 Cruise Control 的示例 JMX Exporter configurations。实践中，团队通常会从这些示例开始，只调整所需规则，而不是从头编写 relabeling rules。

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

应用 `metricsConfig` 后，Strimzi 会自动在每个 broker container 内启用 JMX Exporter Java agent，并将引用的 `ConfigMap` rules file 挂载到同一个 container 中。随后，每个 broker pod 的 `9404` 端口（默认值）上的 `/metrics` path 就可以被抓取为 Prometheus-format metrics。同一个 `metricsConfig` 字段也可用于 `KafkaConnect`、`KafkaMirrorMaker2` 和 `CruiseControl` custom resources。

## 2. 核心 Broker Metrics

Kafka 暴露了大量 JMX metrics，因此有必要缩小范围，明确哪些 metrics 在日常运维中真正重要。

| Metric | 含义 | 健康值 / 需要关注的内容 |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 此 broker 作为 leader 的 partitions 中，其 in-sync replica (ISR) 集合小于配置的 replication factor 的数量 | **应为 0。** 任何大于 0 的值都表示一个或多个 followers 正落后于 leader —— 需要调查 network latency、broker overload 或 disk I/O bottlenecks。 |
| `kafka_controller_kafkacontroller_activecontrollercount` | 此 broker/controller 当前是否为 active controller（0 或 1） | Cluster 范围内的 **sum 必须正好为 1**。sum 为 0 表示没有 active controller（正在进行 leader election 或出现故障）；sum 为 2 或更多则暗示 split-brain 状态，需要立即调查。 |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | Broker 的 request-handler thread pool 处于 idle 状态的时间比例 | 下降的值（例如低于 20%）表示 broker 正接近 CPU/thread 饱和。持续偏低的值是需要横向扩展 brokers 或重新均衡 partitions 的信号。 |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | 按 topic 统计的 produce/consume throughput（bytes per second） | 用于 broker/network capacity planning，并检测单个 topics 上的 traffic spikes（hot partitions）。 |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | Replicas 离开（shrink）或重新加入（expand）ISR set 的速率（per second） | 频繁 shrink 表示 followers 反复失去同步，通常会先于 under-replicated partitions 增加出现。 |

在这些 metrics 中，**under-replicated partition count** 和 **active controller count** 最直接反映 cluster 的 data safety 和 availability，因此它们应该放在每个 dashboard 和 alert rule set 的最顶部。

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Consumer Lag 监控

**Consumer lag** 是指每个 partition 中，最新产生的 offset（log end offset）与 consumer group 最后提交的 offset 之间的差值。持续增长的 lag 表示 consumer group 无法跟上 produce rate —— 可能是处理速度慢、consumer 停滞，或反复 rebalancing 的信号。

Strimzi 通过这个 in-process Java agent 暴露的 JMX Exporter metrics 描述的是 **broker 自身的状态**（见上面的第 2 节），默认不包含 consumer group offsets 或 lag。计算 lag 需要将 consumer group 的 committed offsets（记录在内部 `__consumer_offsets` topic 中）与每个 topic 的最新 offset 进行关联，这超出了 broker-side exporter 的范围。因此，团队通常会运行一个专门用于 consumer lag 的独立 exporter。

最常用的选项是 community project [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter)（或类似 Burrow-style exporter），它作为 cluster 中自己的 `Deployment` 运行。它会按固定 interval 轮询 Kafka Admin API，读取每个 consumer group 的 committed offsets 和每个 topic 的 latest offsets，然后以 Prometheus format 暴露诸如 `kafka_consumergroup_group_lag`（按 group、topic 和 partition 拆分的 lag）这样的 metrics。

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

部署该 exporter 且 Prometheus 正在抓取其 `/metrics` endpoint 后，就可以像这样查询 lag：

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. 使用 ServiceMonitor / PodMonitor 连接 Scraping

在运行 Prometheus Operator 的环境中（例如 kube-prometheus-stack），常见做法不是手动编辑 `scrape_configs`，而是声明一个通过 label 发现 targets 的 `PodMonitor` CRD。由于 brokers 是由 Strimzi 管理的 pods，而不是位于固定 `Service` 后面，因此使用 `PodMonitor` 直接选择 pods，比依赖基于 `Service` 的 `ServiceMonitor` 更可靠。

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

metrics 开始流动后，针对 under-replicated partitions 的 alerting 是最基础、也最应该先放置的安全网。下面的 `PrometheusRule` 会在 under-replicated partitions 持续高于 0 至少 5 分钟时触发。

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

## 5. 使用 KEDA 自动扩展 Consumers

基于 CPU/memory 的 HPA 往往无法反映 consumer workload 的真实负载 —— 等待处理的 messages 数量。KEDA 的 Kafka scaler (`triggers.type: kafka`) 允许你改为基于 **consumer group lag** 扩展 consumer `Deployment`。KEDA 会通过 Kafka Admin API 直接查询所配置 topic/consumer group 的 lag，因此 scaling decisions 并不严格依赖第 3 节中的独立 lag exporter（不过该 exporter 对 dashboard 和 alerting 仍然有用）。

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

关键 trigger parameters：

* **`bootstrapServers`**: KEDA 用于查询 lag 的 Kafka cluster bootstrap address
* **`consumerGroup`**, **`topic`**: 被衡量 lag 的 consumer group 和 topic
* **`lagThreshold`**: 每个 partition 的 lag value，超过该值时 KEDA 会添加另一个 replica（例如，每 50 个单位的 per-partition lag 增加一个 replica）
* **`activationLagThreshold`**: 触发从 0 到 1 个 replica 初始 scale-up 所需的最小 lag。如果未设置，即使很小的 lag 也会立即扩展到 1。
* **`allowIdleConsumers`**: 当为 `false`（默认值）时，KEDA 会限制 replicas，确保创建的 consumers 永远不会超过可消费的 partitions 数量。

应用此 `ScaledObject` 后，KEDA Operator 会在幕后创建并管理一个标准 Kubernetes HPA，并在 lag 缓解后于 `cooldownPeriod` 之后缩容。关于更广泛的 KEDA 概念 —— scaler types、architecture、zero scaling —— 请参阅专门的 [自动扩展：KEDA](../../autoscaling/01-keda.md) 文档。

## 6. Grafana Dashboards

Strimzi 在其 GitHub repository 的 [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) 下提供了 broker、ZooKeeper（legacy mode）、Kafka Connect 和 Cruise Control 的示例 Grafana dashboard JSON。导入这些 dashboard 并调整 cluster name/namespace variables，通常比从头构建 panels 更快。

一个扎实的 Kafka dashboard 至少应覆盖以下 panel groups：

* **Broker health**: 每个 broker 的 uptime、JVM heap usage、GC pause time、request-handler/network idle ratio
* **ISR/replication status**: under-replicated partition count、ISR shrink/expand rate、active controller count（cluster-wide sum）
* **Throughput**: 按 topic 和按 broker 统计的 bytes in/out per second、messages per second、per-partition throughput imbalance（hot-partition detection）
* **Consumer lag**: 每个 consumer group 的 lag trend，并与 rebalance events 关联，以找出 sudden spikes 的原因

## 后续步骤

metrics collection、alerting 和 autoscaling 就绪后，下一步是将这一切应用到真实的运维标准中 —— SLOs、capacity planning 和 incident response procedures。这些内容将在 [第 8 部分：最佳实践](./08-best-practices.md) 中介绍。

[返回主页](./)

## 测验

要测试你在本章中学到的内容，请尝试完成 [主题测验](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)。
