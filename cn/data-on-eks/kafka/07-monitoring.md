# 第 7 部分：监控

> **支持的版本**：Strimzi 0.45+、Prometheus Operator、KEDA 2.x\
> **最后更新**：July 9, 2026

Kafka 集群所需的不只是 broker 堆、磁盘和网络图表——还需要了解分区复制健康状况和消费者处理速度，以便及早发现问题。本文介绍如何使用 Prometheus 抓取 Strimzi 暴露的 broker 指标、如何单独测量消费者延迟，以及如何使用 KEDA 自动扩缩消费者。

## 1. Strimzi 如何暴露指标

Strimzi 会在每个 broker/controller/Connect 组件容器内运行 Prometheus JMX Exporter——它不是独立的 sidecar 容器，而是加载到同一个 JVM 进程中的 **JVM Java agent**。JMX Exporter 读取 JVM 内部的 JMX MBean（例如 `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`），并将其转换为 Prometheus 文本格式的 `/metrics` HTTP 端点。哪些 MBean 映射到哪些指标名称和标签，由存储在 `ConfigMap` 中的重标签配置定义；`Kafka` CR 的 `metricsConfig` 字段则指向该 `ConfigMap`。

Strimzi 上游仓库在 [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics) 下提供了适用于 broker、Connect 和 Cruise Control 的 JMX Exporter 配置示例。实践中，团队通常从这些示例开始，只调整所需规则，而不是从头编写重标签规则。

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

应用 `metricsConfig` 后，Strimzi 会自动在每个 broker 容器内启用 JMX Exporter Java agent，并将所引用 `ConfigMap` 的规则文件挂载到同一容器中。随后，可以在每个 broker Pod 的端口 `9404`（默认值）的 `/metrics` 路径抓取 Prometheus 格式的指标。`KafkaConnect`、`KafkaMirrorMaker2` 和 `CruiseControl` 自定义资源同样提供 `metricsConfig` 字段。

## 2. 核心 Broker 指标

Kafka 暴露大量 JMX 指标，因此应聚焦于日常实际重要的指标。

| 指标 | 含义 | 健康值 / 需要关注的情况 |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 此 broker 作为 leader 的分区中，其同步副本（ISR）集合小于配置副本因子的分区数量 | **应为 0。**任何大于 0 的值都意味着一个或多个 follower 落后于 leader——请调查网络延迟、broker 过载或磁盘 I/O 瓶颈。 |
| `kafka_controller_kafkacontroller_activecontrollercount` | 此 broker/controller 当前是否为活跃 controller（0 或 1） | 集群范围内的**总和必须恰好为 1**。总和为 0 表示没有活跃 controller（正在进行 leader 选举或发生故障）；总和为 2 或更大则表明可能出现脑裂状况，需要立即调查。 |
| 请求处理程序空闲比率 (`...requesthandleravgidlepercent...`) | broker 请求处理程序线程池处于空闲状态的时间比例 | 持续下降的值（例如低于 20%）表明 broker 正接近 CPU/线程饱和。持续偏低的值表明应横向扩展 broker 或重新平衡分区。 |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | 每个 topic 每秒的生产/消费吞吐量（字节数） | 用于 broker/网络容量规划，以及检测单个 topic 上的流量峰值（热分区）。 |
| ISR 收缩/扩展速率 (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | 副本每秒离开（收缩）或重新加入（扩展）ISR 集合的速率 | 频繁收缩意味着 follower 反复失去同步，通常会先于未充分复制分区数量的增加出现。 |

在这些指标中，**未充分复制分区数量**和**活跃 controller 数量**最直接反映集群的数据安全性和可用性，因此应置于每个仪表板和告警规则集的首位。

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. 消费者延迟监控

**消费者延迟**是指，对于每个分区，最新生产 offset（日志末尾 offset）与消费者组最后提交的 offset 之间的差值。持续增长的延迟意味着消费者组无法跟上生产速率——这表明处理缓慢、消费者停滞或反复重新平衡。

Strimzi 通过此进程内 Java agent 暴露的 JMX Exporter 指标描述的是 **broker 自身状态**（如上文第 2 节），默认不包括消费者组 offset 或延迟。计算延迟需要将消费者组已提交的 offset（在内部 `__consumer_offsets` topic 中跟踪）与每个 topic 的最新 offset 关联起来，这超出了 broker 端 exporter 的范围。因此，团队通常会运行专用于消费者延迟的独立 exporter。

最广泛使用的选择是社区项目 [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter)（或类似的 Burrow 风格 exporter），它作为集群中的独立 `Deployment` 运行。它按一定间隔轮询 Kafka Admin API，以读取每个消费者组的已提交 offset 和每个 topic 的最新 offset，随后以 Prometheus 格式暴露诸如 `kafka_consumergroup_group_lag`（按组、topic 和分区细分的延迟）等指标。

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

部署此 exporter 并由 Prometheus 抓取其 `/metrics` 端点后，可按如下方式查询延迟：

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. 使用 ServiceMonitor / PodMonitor 配置抓取

在运行 Prometheus Operator 的环境（如 kube-prometheus-stack）中，通常的做法不是手动编辑 `scrape_configs`，而是声明一个按标签发现目标的 `PodMonitor` CRD。由于 broker 作为由 Strimzi 管理的 Pod 运行，而不是位于固定的 `Service` 后方，因此直接使用 `PodMonitor` 选择 Pod 比依赖基于 `Service` 的 `ServiceMonitor` 更可靠。

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

指标开始流入后，对未充分复制分区设置告警是最基本的安全保障。下方的 `PrometheusRule` 会在未充分复制分区持续高于 0 至少 5 分钟时触发。

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

## 5. 使用 KEDA 自动扩缩消费者

基于 CPU/内存的 HPA 通常无法反映消费者工作负载的实际负载——等待处理的消息数量。KEDA 的 Kafka scaler（`triggers.type: kafka`）使你能够改为基于**消费者组延迟**扩缩消费者 `Deployment`。KEDA 通过 Kafka Admin API 直接查询已配置 topic/消费者组的延迟，因此扩缩决策并不严格依赖第 3 节中的独立延迟 exporter（尽管该 exporter 对仪表板和告警仍然有用）。

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

关键触发器参数：

* **`bootstrapServers`**：KEDA 用来查询延迟的 Kafka 集群 bootstrap 地址
* **`consumerGroup`**、**`topic`**：用于测量延迟的消费者组和 topic
* **`lagThreshold`**：KEDA 添加另一个副本的每分区延迟阈值（例如，每 50 个单位的每分区延迟增加一个副本）
* **`activationLagThreshold`**：从 0 初始扩展到 1 个副本所需的最小延迟。若未设置，即使很小的延迟也会立即扩展到 1。
* **`allowIdleConsumers`**：当为 `false`（默认值）时，KEDA 会限制副本数，确保创建的消费者数量不会超过可消费的分区数量。

应用此 `ScaledObject` 后，KEDA Operator 会在幕后创建并管理标准 Kubernetes HPA，并在延迟消退后经过 `cooldownPeriod` 再缩容。有关更广泛的 KEDA 概念——scaler 类型、架构、缩放至零——请参阅专门的[自动扩缩：KEDA](../../autoscaling/01-keda.md)文档。

## 6. Grafana 仪表板

Strimzi 在其 GitHub 仓库的 [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) 下提供 broker、ZooKeeper（旧版模式）、Kafka Connect 和 Cruise Control 的 Grafana 仪表板 JSON 示例。导入这些示例并调整集群名称/namespace 变量，通常比从头构建面板更快。

一个完善的 Kafka 仪表板至少应涵盖以下面板组：

* **Broker 健康状况**：每个 broker 的运行时间、JVM 堆使用量、GC 暂停时间、请求处理程序/网络空闲比率
* **ISR/复制状态**：未充分复制分区数量、ISR 收缩/扩展速率、活跃 controller 数量（集群范围总和）
* **吞吐量**：每个 topic 和每个 broker 每秒的输入/输出字节数、每秒消息数、每分区吞吐量不平衡（热分区检测）
* **消费者延迟**：每个消费者组的延迟趋势，并与重新平衡事件关联以识别突然峰值的原因

## 后续步骤

完成指标收集、告警和自动扩缩后，下一步是将这些内容应用到实际的运维标准中——SLO、容量规划和事件响应流程。[第 8 部分：最佳实践](./08-best-practices.md)对此进行了介绍。

[返回主页](./README.md)

## 测验

要测试你在本章中学到的内容，请尝试[主题测验](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)。
