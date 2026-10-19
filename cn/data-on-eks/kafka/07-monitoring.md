# 第 7 部分：监控

> **审查基线**：Strimzi 1.3.0 / Kafka 4.3.1，捆绑的 JMX Exporter 1.6.0 和 Kafka Exporter 1.10.0，Prometheus Operator 0.94.1，KEDA 2.21.0\
> **最后审查日期**：2026 年 10 月 16 日

## 各组件监控的内容

| 组件 | 作用 |
| --- | --- |
| JMX Prometheus Exporter | 作为 Java agent，将进程内 JVM MBean 映射为 Prometheus 指标 |
| Strimzi Metrics Reporter | 另一种受支持的 `metricsConfig.type`；通过其自身的配置和命名方式直接暴露 Kafka 指标 |
| Kafka Exporter | 使用 Kafka API 暴露消费者组偏移量/滞后和主题信息 |
| Prometheus / Prometheus Operator | 发现并抓取目标、评估规则，并将告警传递给 Alertmanager |
| KEDA Kafka scaler | 查询 Kafka API 以进行扩缩；它不需要滞后 Exporter 的 Prometheus 端点 |

本章选择 **`jmxPrometheusExporter`**。它的映射规则与 Prometheus 目标重新标记并不是一回事。`strimziMetricsReporter` 也受支持，因此过去声称 JMX 是唯一选项的说法并不正确。更改 Exporter 类型时，需要重新检查指标名称和仪表板。

这些示例基于[第 2 部分](./02-strimzi-operator.md)：命名空间 `kafka`、`my-cluster`、三个 broker Pod、三个 controller Pod，以及一个包含 12 个分区的 `orders` 主题。其 node pool 会为 Pod 添加标签 `docs.example.com/kafka-role: broker` 或 `controller`。必须已安装 Prometheus Operator 和 KEDA。

## 启用 JMX 指标，而不替换集群规格

将以下内容保存为 `metrics-config.yaml`。这些针对性规则会暴露复制 gauge、broker 请求处理器空闲比率，以及吞吐量/ISR 计数器。计数器名称以 `_total` 结尾；对计数器使用 `rate()`，不要对已经计算出的速率使用它。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
    - pattern: kafka.server<type=ReplicaManager, name=(UnderReplicatedPartitions|UnderMinIsrPartitionCount)><>Value
      name: kafka_server_replicamanager_$1
      type: GAUGE
    - pattern: kafka.controller<type=KafkaController, name=(ActiveControllerCount|OfflinePartitionsCount)><>Value
      name: kafka_controller_kafkacontroller_$1
      type: GAUGE
    - pattern: kafka.server<type=KafkaRequestHandlerPool, name=BrokerRequestHandlerAvgIdlePercent><>MeanRate
      name: kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent
      type: GAUGE
    - pattern: kafka.server<type=BrokerTopicMetrics, name=(BytesIn|BytesOut)PerSec, topic=(.+)><>Count
      name: kafka_server_brokertopicmetrics_$1_total
      type: COUNTER
      labels:
        topic: $2
    - pattern: kafka.server<type=ReplicaManager, name=(IsrShrinks|IsrExpands)PerSec><>Count
      name: kafka_server_replicamanager_$1_total
      type: COUNTER
```

将以下内容保存为 **`metrics.patch.yaml`**。这是针对现有 Kafka 资源的合并补丁，不是可用于创建/应用的完整资源。现有监听器、身份验证、存储和其他设置都会保留。

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

第一部分启用进程内 JMX agent。第二部分部署 Strimzi 的 **Kafka Exporter**，它与 `seglo/kafka-lag-exporter` 的实现和指标名称不同。该旧项目已归档；本章不建议将其作为当前默认选项。

Strimzi 会管理 Exporter 连接到内部 Kafka 监听器所需的连接配置和证书材料；不要将其替换为未经身份验证的 9092 地址。该版本的 Exporter 使用端口 **9404**，名称为 **`tcp-prometheus`**，Kafka 节点指标端点也使用此端口。Kafka Exporter 是一个独立的工作负载。

`KafkaConnect` 和 `KafkaMirrorMaker2` 有各自的指标配置。Cruise Control 在 `Kafka.spec.cruiseControl` 下配置；它不是独立的 `CruiseControl` CRD。不要对所有组件都盲目复用 Kafka MBean 规则。

## 发现预期目标

保存为 `podmonitors.yaml`。节点和滞后 Exporter 目标会分别选择。重新标记会创建稳定的 `namespace`、`kafka_cluster`、`kafka_component` 上下文，并为 Kafka 节点创建 `kafka_role` 上下文，供查询使用。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-node-metrics
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  namespaceSelector:
    matchNames:
    - kafka
  selector:
    matchLabels:
      strimzi.io/cluster: my-cluster
    matchExpressions:
    - key: docs.example.com/kafka-role
      operator: In
      values:
      - broker
      - controller
  podMetricsEndpoints:
  - port: tcp-prometheus
    path: /metrics
    interval: 30s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_namespace
      targetLabel: namespace
    - sourceLabels:
      - __meta_kubernetes_pod_label_strimzi_io_cluster
      targetLabel: kafka_cluster
    - targetLabel: kafka_component
      replacement: nodes
    - sourceLabels:
      - __meta_kubernetes_pod_label_docs_example_com_kafka_role
      targetLabel: kafka_role
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kafka-group-lag
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  namespaceSelector:
    matchNames:
    - kafka
  selector:
    matchLabels:
      strimzi.io/cluster: my-cluster
      docs.example.com/kafka-monitor: lag
  podMetricsEndpoints:
  - port: tcp-prometheus
    path: /metrics
    interval: 30s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_namespace
      targetLabel: namespace
    - sourceLabels:
      - __meta_kubernetes_pod_label_strimzi_io_cluster
      targetLabel: kafka_cluster
    - targetLabel: kafka_component
      replacement: lag
```

`release` 标签必须与 Prometheus 资源的 PodMonitor/PrometheusRule 选择器相匹配。其命名空间选择器和 RBAC 也必须能够发现 `kafka` 中的资源。检查网络策略，以及 Prometheus 到这些 Pod 的端口访问权限。

只要有匹配的 Service，配置正确的 **ServiceMonitor 也能正常工作**。PodSet 还是 StatefulSet 并不能决定 ServiceMonitor 是否可用。此处选择 PodMonitor 是为了直接发现 Pod，并不代表它本质上使用了更可靠的协议。每个端点只抓取一次；移除重复的发现路径，并在聚合联邦视图之前对 HA Prometheus 副本进行去重。

## 在上下文中解读指标

| 此映射中的指标 | 解释 |
| --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 通常为零；在故障、滞后或计划维护期间可能升高。检查持续时间和受影响的分区 |
| `kafka_server_replicamanager_underminisrpartitioncount` | 低于配置的最小 ISR 的分区；对于 `acks=all` 写入可用性至关重要 |
| `kafka_controller_kafkacontroller_activecontrollercount` | 对单个集群的 controller Pod 求和后应稳定为一；请确认样本覆盖范围，并检查重复/过期抓取 |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | 没有可用 leader 的分区；调查可用性问题 |
| `kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent` | gauge 比率，通常为 0–1。低值需要与 CPU、GC、I/O 和请求延迟进行关联分析，而不是自动据此下结论 |
| `kafka_server_brokertopicmetrics_bytesin_total` / `bytesout_total` | 每个主题的字节计数器；使用 `rate` 计算吞吐量 |
| `kafka_server_replicamanager_isrshrinks_total` / `isrexpands_total` | ISR 变更计数器；将频繁变动与复制状态进行关联分析 |

controller 总和大于一是一种异常的**观测结果**，并不能证明发生了脑裂：应先检查跨集群聚合、重复目标、抓取时间和过期样本。缺失样本不等于零。仅有副本不足也不代表已经发生数据丢失。

每个主题的写入吞吐量：

```promql
sum by (namespace, kafka_cluster, topic) (
  rate(kafka_server_brokertopicmetrics_bytesin_total{
    namespace="kafka",kafka_cluster="my-cluster"
  }[5m])
)
```

主题聚合流量无法识别哪个分区负载过高。调查倾斜时，应添加作用域适当的逐分区/客户端观测指标。此处的针对性映射并非完整的上游仪表板指标集。

## 消费者滞后是已提交偏移量之间的距离

对于每个分区，滞后通常是**日志末端下一个偏移量减去消费者组已提交的下一个偏移量**。它表示偏移量距离，并不总是业务记录数量：压缩、偏移量间隙和事务都会产生影响。如果在处理结果持久化之前就提交偏移量，那么即使工作尚未完成，滞后看起来也可能正常。

对 broker MBean 的 JMX 映射本身不会执行此项测量所需的消费者组/分区偏移量查询。Strimzi 的 Kafka Exporter 提供 `kafka_consumergroup_lag`，其标签为 **`consumergroup`**、`topic` 和 `partition`。不要查询已归档 Exporter 的 `kafka_consumergroup_group_lag` 名称，也不要假设此处适用其 `group` 标签。

```promql
sum by (namespace, kafka_cluster, consumergroup, topic) (
  kafka_consumergroup_lag{
    namespace="kafka",kafka_cluster="my-cluster",
    topic="orders",consumergroup="order-processor"
  } >= 0
)
```

此筛选条件会从积压总量中排除负值/未知滞后值，但不能因此隐藏数据不可用的情况。应分别监控 Exporter 健康状态、预期消费者组缺失，以及 `kafka_consumergroup_current_offset < 0`。没有提交记录的消费者组、身份验证失败以及被筛除的主题都可能导致结果缺失。已提交偏移量的滞后为零，并不代表端到端处理 SLO 已达标。

## 告警还必须检测数据缺失

保存为 `alerts.yaml`。预期数量为六个 Kafka 节点和三个 controller，与本章的拓扑相符。更改 node pool 时，请相应更新这些数量。预期消费者组/主题告警假定 `order-processor` 应在 `orders` 上提交偏移量；请根据应用调整其作用范围和启动宽限期。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kafka-alerts
  namespace: kafka
  labels:
    release: kube-prometheus-stack
spec:
  groups:
  - name: kafka.rules
    rules:
    - alert: KafkaUnderReplicatedPartitions
      expr: sum by (namespace, kafka_cluster) (kafka_server_replicamanager_underreplicatedpartitions{namespace="kafka",kafka_cluster="my-cluster"}) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Kafka replication is degraded
    - alert: KafkaUnderMinISR
      expr: sum by (namespace, kafka_cluster) (kafka_server_replicamanager_underminisrpartitioncount{namespace="kafka",kafka_cluster="my-cluster"}) > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: Kafka partitions are below min ISR
    - alert: KafkaControllerCount
      expr: sum by (namespace, kafka_cluster) (kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
        != 1
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: Kafka active-controller observation is abnormal
    - alert: KafkaControllerMetricMissing
      expr: count by (namespace, kafka_cluster) (kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
        != 3 or absent(kafka_controller_kafkacontroller_activecontrollercount{namespace="kafka",kafka_cluster="my-cluster",kafka_role="controller"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Expected controller metrics are missing or duplicated
    - alert: KafkaNodeScrapeCoverage
      expr: sum by (namespace, kafka_cluster) (up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="nodes"}) != 6 or absent(up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="nodes"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Expected six Kafka node scrapes are not healthy
    - alert: KafkaLagExporterUnavailable
      expr: sum by (namespace, kafka_cluster) (up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="lag"}) != 1 or absent(up{namespace="kafka",kafka_cluster="my-cluster",kafka_component="lag"})
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Kafka lag exporter is unavailable
    - alert: KafkaConsumerLagHigh
      expr: sum by (namespace, kafka_cluster, consumergroup, topic) (kafka_consumergroup_lag{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"}
        >= 0) > 1000
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Kafka committed-offset lag is high
    - alert: KafkaConsumerLagMissing
      expr: absent(kafka_consumergroup_lag{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Expected consumer group lag has no samples
    - alert: KafkaConsumerOffsetUnknown
      expr: kafka_consumergroup_current_offset{namespace="kafka",kafka_cluster="my-cluster",topic="orders",consumergroup="order-processor"} < 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Consumer committed offset is unknown
```

这些阈值和持续时间是起始值。`for` 要求条件持续为真一段时间后才触发；它不是抓取间隔，也不是滚动平均值。单独使用 `sum(metric) != 1` **无法**检测整个指标族缺失，因为结果可能是空向量。独立的覆盖率和 `absent()` 规则会处理这些情况。

```bash
kubectl apply -f metrics-config.yaml
kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl apply -f podmonitors.yaml -f alerts.yaml
```

检查 Kafka 资源的观测到的 generation/conditions、实际 Pod 端口，以及 Prometheus 的 Targets 和 Rules 页面。配置更改可能导致工作负载滚动更新。请单独验证 Alertmanager 的路由/投递；创建 PrometheusRule 并不能证明通知已送达运维人员。

## 使用经过身份验证的 KEDA 查询来扩缩消费者

目标 `Deployment/order-consumer` 必须已存在于**命名空间 `kafka` 中**，使用第 2 部分的 TLS/SCRAM 监听器连接，并以 `order-processor` 身份消费。其应用凭证与下方 scaler 的只读元数据身份相互独立。ScaledObject 和 TriggerAuthentication 也位于 `kafka` 中。

保存为 `keda-auth.yaml`。用户名 Secret 不包含密码；User Operator 会生成密码 Secret。KEDA 通过 TriggerAuthentication 引用读取用户名、密码和 CA。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: keda-lag-reader
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
    - resource:
        type: topic
        name: orders
        patternType: literal
      operations:
      - Describe
    - resource:
        type: group
        name: order-processor
        patternType: literal
      operations:
      - Describe
---
apiVersion: v1
kind: Secret
metadata:
  name: keda-kafka-identity
  namespace: kafka
type: Opaque
stringData:
  username: keda-lag-reader
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-lag-auth
  namespace: kafka
spec:
  secretTargetRef:
  - parameter: username
    name: keda-kafka-identity
    key: username
  - parameter: password
    name: keda-lag-reader
    key: password
  - parameter: ca
    name: my-cluster-cluster-ca-cert
    key: ca.crt
```

保存为 `scaledobject.yaml`。TLS 主机名验证仍保持启用。KEDA operator 必须能够访问 broker 端点和所引用的 Secrets。

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

`lagThreshold: "50"` 表示每个副本期望承担的**有效总滞后量**，并不是为每个分区分别设置的阈值，也不会因此为每个分区创建多个消费者。对于默认的 AverageValue 目标，粗略估算的需求是 `ceil(effective total lag / 50)`（即有效总滞后量除以 50 后向上取整），但实际结果还受 scaler 调整、HPA 容差、最小/最大副本数和稳定窗口影响。增加消费者并不能让同一传统消费者组中的多个成员同时消费一个分区。

`allowIdleConsumers=false` 会让 scaler 将分区数纳入考虑；如果严格限制副本数很重要，请将 `maxReplicaCount` 显式设为不高于可用分区数的值。此示例基于第 2 部分中包含 12 个分区的主题，将上限设为 10。分区数不同的主题或工作负载需要相应地重新评估。

由于 `minReplicaCount=1`，此示例**不会缩容到零**。`activationLagThreshold` 和 KEDA 的零副本缩容 `cooldownPeriod` 并不控制其 1↔N 行为。此处显式配置了 HPA 缩容稳定窗口。如果之后启用零副本缩容，请测试新消费者组/缺失提交、偏移量重置策略、启动和激活行为；不要将未知偏移量视为空队列。

```bash
kubectl apply -f keda-auth.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/keda-lag-reader
kubectl apply -f scaledobject.yaml
kubectl -n kafka get scaledobject order-consumer-scaler -o yaml
kubectl -n kafka get hpa
```

在更改限制之前，请比较 scaler 错误、HPA 当前/期望指标和实际消费者吞吐量。现有的 [KEDA 指南](../../autoscaling/01-keda.md)介绍了通用的自动扩缩行为。

## 仪表板与验证

请使用带版本信息的上游 **Kafka、KRaft、Kafka Exporter、Connect 和 Cruise Control** 仪表板作为参考，并确保它们与所选的 Exporter 类型和标签映射相匹配。Strimzi 1.3 仪表板集并非 ZooKeeper 部署指南。导入仪表板并不能保证其中查询所需的指标都存在于此针对性映射中。

应纳入 JVM/GC、节点/PVC 容量和 I/O、复制可用性、抓取覆盖率、流量分布、消费者组进度，以及应用延迟/错误 SLO。进程内 Exporter 也会暴露 JVM 指标，但主机/PVC 和应用信号来自各自对应的采集器。

示例中的最终 JMX 规则和 Kafka Exporter (1.9.0) 已在隔离的本地 Kafka 4.3.1 broker 上进行测试：15 条记录及已提交偏移量产生的各分区滞后分别为 **3、5 和 5**。九条告警规则已在正常、数据缺失、故障和跨集群隔离场景下进行了测试。这些测试并不能证明生产环境中的 TLS 访问、多节点 quorum 行为、Strimzi 协调、通知投递，或 KEDA 能够在你的实际工作负载上正常运行。

- [Strimzi 1.3.0 指标示例](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/examples/metrics/kafka-metrics.yaml)
- [Strimzi 1.3.0 Kafka Exporter 实现](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/cluster-operator/src/main/java/io/strimzi/operator/cluster/model/KafkaExporter.java)
- [Strimzi 1.3.0 捆绑的 Exporter 版本](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/docker-images/kafka-based/kafka/Dockerfile)
- [Kafka Exporter 1.10.0](https://github.com/danielqsj/kafka_exporter/tree/v1.10.0)
- [已归档的 kafka-lag-exporter 项目](https://github.com/seglo/kafka-lag-exporter)
- [KEDA 2.21 Kafka scaler](https://keda.sh/docs/2.21/scalers/apache-kafka/)
- [KEDA 2.21.0 实现](https://github.com/kedacore/keda/blob/v2.21.0/pkg/scalers/kafka_scaler.go)
- [Prometheus 告警规则](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [带版本信息的基于 JMX 的 Grafana 仪表板](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/grafana-dashboards)
- [带版本信息的 Strimzi Metrics Reporter 仪表板](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/strimzi-metrics-reporter/grafana-dashboards)

## 后续步骤

[第 8 部分：最佳实践](./08-best-practices.md)

[返回主页](./README.md)

## 测验

[主题测验](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
