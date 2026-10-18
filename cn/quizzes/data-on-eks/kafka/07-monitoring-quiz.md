# 第 7 部分：监控测验

请核对实际指标名称、抓取范围和缺失数据、消费者延迟，以及经过身份验证的 KEDA 行为。

## 1. 本章的 JMX 方案如何运行？它是 Strimzi 唯一支持的指标方案吗？

<details>
<summary>显示答案</summary>

JMX Exporter 作为 Java agent 在同一个 JVM 中运行。Strimzi 也支持 strimziMetricsReporter。切换方案时，应核对指标命名、配置和仪表板。

</details>

## 2. JMX MBean 映射规则与 PodMonitor 的 relabeling 有何不同？

<details>
<summary>显示答案</summary>

ConfigMap 中的 JMX 规则将 MBean 映射为指标名称和标签。PodMonitor 的 relabeling 是独立的发现步骤，用于补充目标上下文，例如 namespace、kafka_cluster 和 role。

</details>

## 3. UnderReplicatedPartitions 大于零是否表示数据已经丢失？

<details>
<summary>显示答案</summary>

不表示。健康稳态值为零，但故障、延迟或计划内操作都可能使其升高。请检查持续时间、under-min-ISR 和离线分区情况，以及造成变化的原因。

</details>

## 4. active-controller 指标总和为 2，是否可以立即判定发生了 split brain？

<details>
<summary>显示答案</summary>

不能。应先检查集群范围、重复抓取目标、陈旧样本和抓取时序。单个集群控制器的预期稳态总和为 1。

</details>

## 5. BrokerRequestHandlerAvgIdlePercent 偏低时，应结合检查哪些指标？

<details>
<summary>显示答案</summary>

应同时检查 CPU、GC、I/O、请求延迟和队列，以及吞吐量。该指标表示处理程序繁忙，但不足以单独证明 CPU 是原因，也不自动意味着应该增加线程或 broker。

</details>

## 6. 仅靠 broker 的 JMX 映射能否计算消费者组延迟？

<details>
<summary>显示答案</summary>

不能。计算延迟需要消费者组已提交的 offset 和分区末尾 offset。本章使用 Strimzi Kafka Exporter；KEDA 则独立查询 Kafka API。

</details>

## 7. 本章选用的 Kafka Exporter 延迟指标及消费者组标签是什么？旧项目目前处于什么状态？

<details>
<summary>显示答案</summary>

本章使用 `kafka_consumergroup_lag` 和 `consumergroup`。较早的 seglo/kafka-lag-exporter 项目已归档；不要把它的 kafka_consumergroup_group_lag 指标或 group 标签约定与本章使用的 exporter 混淆。

</details>

## 8. PodMonitor 是否总比 ServiceMonitor 可靠？

<details>
<summary>显示答案</summary>

不是。只要 Service 和选择器配置正确，ServiceMonitor 就能工作。本章选择直接发现 Pod；请核对 Prometheus 的标签和命名空间选择器、RBAC、网络连通性以及是否发生重复抓取。

</details>

## 9. 解释 PrometheusRule 中 for: 5m 的作用，以及如何处理缺失数据。

<details>
<summary>显示答案</summary>

告警条件必须持续存在且为真五分钟，之后才会触发。它不是抓取间隔，也不是平均时间。某个指标族缺失时，sum 比较可能得到空结果，因此还要检查 absent 和抓取覆盖率。

</details>

## 10. KEDA Kafka scaler 是否需要 Prometheus 延迟 exporter？

<details>
<summary>显示答案</summary>

不需要。它直接查询 Kafka API，但需要自行具备 broker 网络连通性、TLS、身份验证和 Secret 访问权限。这条查询路径与仪表板使用的 exporter 不同。

</details>

## 11. 延迟为 0 是否能证明业务处理已经完成？

<details>
<summary>显示答案</summary>

不能。该值通常是日志末尾的下一个 offset 减去已提交的下一个 offset。提前提交，或数据及采集条件的差异，都可能使它与业务处理完成情况不同。压缩和事务也会使它不同于物理记录数。

</details>

## 12. 应如何查询 bytesin_total 和 idle_percent？

<details>
<summary>显示答案</summary>

对 bytesin_total 这个 counter 使用 rate(...[5m])，计算每秒速率。idle_percent 已经是比率型 gauge，应直接观察，不要再次对它使用 rate。

</details>

## 13. 如何理解 lagThreshold=50 与 minReplicaCount=1？

<details>
<summary>显示答案</summary>

目标是每个副本承担的有效总延迟为 50；可粗略按 ceil(总延迟/50) 估算副本数，但实际结果受 HPA/scaler 调整和限制影响。这不会为每个分区单独创建多个消费者。minReplicaCount 为 1 时，应检查 HPA 缩容行为，而不是缩至零的激活或冷却设置。

</details>

## 14. ISR 变化和 topic 吞吐量能说明什么？它们有哪些局限？

<details>
<summary>显示答案</summary>

ISR shrink/expand counter 的速率可以反映变化频度，便于结合复制健康状况进行分析。仅有 topic 聚合吞吐量无法识别热点分区；还需查看分区和客户端层面的数据。

</details>

## 15. 编写补丁，将本章的 metricsConfig 和 Kafka Exporter 添加到现有 Kafka 资源中。

<details>
<summary>显示答案</summary>

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

请先创建 metrics-config.yaml，再使用 `kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml`。这不是完整的 Kafka 创建清单，并且会保留已有的身份验证和 listeners 配置。

</details>

## 16. 编写一个使用 TLS/SCRAM 和同一命名空间中 TriggerAuthentication 的 ScaledObject。

<details>
<summary>显示答案</summary>

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

这要求本章的 keda-auth.yaml 和已有的 kafka/order-consumer Deployment。应用必须以 order-processor 作为消费者组运行。最大副本数 10 适用于第 2 部分所示的 12 个分区；其他拓扑应据此调整。

</details>

## 17. 对于副本不足告警，应如何分别处理集群范围、for 条件和缺失数据？

<details>
<summary>显示答案</summary>

将 gauge 限定为 namespace="kafka"、kafka_cluster="my-cluster"，按集群求和，并对大于 0 的条件应用 for:5m。另设节点抓取覆盖率和控制器指标缺失告警。对于延迟，还要监控 exporter 故障、预期消费者组缺失和负的已提交 offset。

</details>

---

[返回学习资料](../../../data-on-eks/kafka/07-monitoring.md) | [上一测验](./06-msk-integration-quiz.md) | [下一测验](./08-best-practices-quiz.md)
