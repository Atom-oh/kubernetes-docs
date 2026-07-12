# 第 7 部分：监控测验

本测验考查你对 Strimzi 如何暴露指标、核心 broker 指标含义、如何衡量消费者延迟，以及如何配置 KEDA Kafka scaler 的理解。

## 选择题

1. Strimzi 在每个 broker 容器内运行什么组件，用于将 JMX 指标转换为 Prometheus 可以抓取的形式？
   - A) Fluent Bit sidecar
   - B) Prometheus JMX Exporter（JVM Java agent）
   - C) OpenTelemetry Collector DaemonSet
   - D) cAdvisor

<details>

<summary>显示答案</summary>

**答案：B) Prometheus JMX Exporter（JVM Java agent）**

**解释：**
当在 `Kafka` CR 上配置 `metricsConfig` 时，Strimzi 会自动在每个 broker（以及 Connect 等）容器内启用 Prometheus JMX Exporter——它不是单独的 sidecar 容器，而是作为加载到同一 JVM 进程中的 Java agent。该 exporter 读取 JVM 内部的 JMX MBean 值，根据重新标记规则重命名它们，并在 `/metrics` HTTP 端点以 Prometheus 文本格式暴露。Fluent Bit 是日志收集器，cAdvisor 收集容器资源指标——二者都不用于这个目的。
</details>

2. `Kafka.spec.kafka.metricsConfig` 引用哪种资源来获取 JMX Exporter 的重新标记规则？
   - A) Secret
   - B) PersistentVolumeClaim
   - C) ConfigMap
   - D) CustomResourceDefinition

<details>

<summary>显示答案</summary>

**答案：C) ConfigMap**

**解释：**
`metricsConfig.valueFrom.configMapKeyRef` 指向包含重新标记规则（YAML 格式）的 `ConfigMap` 的名称和 key。Strimzi 将这个规则文件挂载到运行 JMX Exporter Java agent 的容器中，使其知道哪些 JMX MBean 映射到哪些 Prometheus 指标名称和标签。`Secret` 用于证书或凭证等敏感值，不用于这个目的。
</details>

3. `kafka_server_replicamanager_underreplicatedpartitions` 指标的健康值是多少？
   - A) 它应该等于 broker 的数量
   - B) 它应该等于分区的数量
   - C) 它应该始终为 0
   - D) 它应该始终为 1

<details>

<summary>显示答案</summary>

**答案：C) 它应该始终为 0**

**解释：**
该指标统计由给定 broker 作为 leader 的分区中，其同步副本（ISR）集合小于已配置复制因子的分区数量。在正常运行时，每个 follower 都应该跟上 leader，因此该值应为 0。大于 0 的值表示某些副本正在落后——通常是由于网络延迟、broker 过载或磁盘 I/O 瓶颈——如果 leader 随后在 ISR 不足的情况下失败，这会直接威胁数据持久性。
</details>

4. 在健康运行状态下，`kafka_controller_kafkacontroller_activecontrollercount` 的集群范围总和应该是多少？
   - A) 0
   - B) 等于 broker 的数量
   - C) 恰好为 1
   - D) 等于 controller 候选者的数量

<details>
<summary>显示答案</summary>

**答案：C) 恰好为 1**

**解释：**
每个 broker/controller 会以 0 或 1 暴露它当前是否为 active controller。对整个集群求和后，在健康运行状态下应恰好为 1。总和为 0 表示没有 active controller（leader 选举正在进行，或出现故障）；总和为 2 或更多则提示存在严重异常，例如 split-brain 状态，需要立即调查。
</details>

5. 如果 Request Handler Idle Ratio 持续偏低（例如低于 10%），你首先应该怀疑什么？
   - A) 磁盘容量即将耗尽
   - B) broker 正接近 CPU/thread 资源饱和
   - C) ZooKeeper 连接已断开
   - D) 某个消费者组正在重新均衡

<details>
<summary>显示答案</summary>

**答案：B) broker 正接近 CPU/thread 资源饱和**

**解释：**
Request Handler Idle Ratio 是 broker 的请求处理线程池处于空闲状态的时间比例。较低的值表示线程池一直忙于处理请求，说明 broker 正接近其 CPU 或线程容量上限。持续偏低的值提示应考虑横向扩展 broker、重新均衡分区，或调优线程池大小。
</details>

6. 为什么 Strimzi 默认暴露的 broker 指标不包含消费者组延迟？
   - A) 消费者延迟是敏感信息，出于安全原因不能暴露
   - B) 计算延迟需要将消费者组已提交 offset 与 topic 的最新 offset 相关联，但 JMX Exporter 只读取 broker 自身的 JMX MBean
   - C) 使用的 Strimzi 版本太旧，不支持它
   - D) 消费者延迟只能从客户端侧测量

<details>
<summary>显示答案</summary>

**答案：B) 计算延迟需要将消费者组已提交 offset 与 topic 的最新 offset 相关联，但 JMX Exporter 只读取 broker 自身的 JMX MBean**

**解释：**
JMX Exporter Java agent 只读取并暴露 broker 进程内部的 JMX MBean（复制状态、吞吐量、controller 状态等）。消费者延迟是消费者组最后提交的 offset 与 topic 最新（log end）offset 之间的差值，这需要通过 Kafka Admin API 分别查询这两个值。因此，消费者延迟通常使用专用工具（例如 `kafka-lag-exporter`）来测量。
</details>

7. 本文档介绍了哪个社区 exporter 用于测量消费者延迟？
   - A) node-exporter
   - B) kafka-lag-exporter
   - C) blackbox-exporter
   - D) kube-state-metrics

<details>
<summary>显示答案</summary>

**答案：B) kafka-lag-exporter**

**解释：**
`kafka-lag-exporter` 是一个社区项目，它会通过 Kafka Admin API 定期查询消费者组已提交的 offset 以及每个 topic 的最新 offset，然后以 Prometheus 格式暴露指标，例如 `kafka_consumergroup_group_lag`。`node-exporter` 收集主机系统指标，`blackbox-exporter` 探测端点，`kube-state-metrics` 报告 Kubernetes 对象状态——这些都不用于这个目的。
</details>

8. 在 Prometheus Operator 环境中抓取由 Strimzi 管理的 Kafka broker Pod 时，哪个 CRD 比定位固定的 `Service` 更可靠？
   - A) ServiceMonitor
   - B) PodMonitor
   - C) Probe
   - D) AlertmanagerConfig

<details>
<summary>显示答案</summary>

**答案：B) PodMonitor**

**解释：**
broker 作为由 Strimzi 管理的独立 Pod 运行。直接按标签（例如 `strimzi.io/cluster`）选择 Pod 的 `PodMonitor`，比定位固定 `Service` 端点的 `ServiceMonitor` 更可靠地发现抓取目标。`Probe` 用于 blackbox 风格的端点检查，`AlertmanagerConfig` 配置告警路由——二者都不用于 Pod 级别的指标抓取。
</details>

9. 在针对 under-replicated partitions 的 `PrometheusRule` 告警中，`for: 5m` 有什么作用？
   - A) 每 5 分钟抓取一次指标
   - B) 条件必须连续为 true 达到 5 分钟，告警才会真正触发
   - C) 告警触发后会在 5 分钟后自动恢复
   - D) 它会计算该值的 5 分钟平均值

<details>
<summary>显示答案</summary>

**答案：B) 条件必须连续为 true 达到 5 分钟，告警才会真正触发**

**解释：**
在 Prometheus 告警规则中，`for` 字段表示 `expr` 中的条件必须在指定持续时间内保持为 true，告警才会从 `pending` 转换为 `firing`。设置 `for: 5m` 可以减少由瞬时尖峰造成的噪声告警，并确保告警只针对真正持续存在的问题触发。
</details>

10. KEDA 的 Kafka scaler 如何确定消费者组延迟？
    - A) 通过抓取 kafka-lag-exporter 暴露的 Prometheus 指标
    - B) 通过直接查询 Kafka Admin API
    - C) 通过解析 broker 的 JMX Exporter `/metrics` 端点
    - D) 通过读取存储在 ZooKeeper 中的 offset

<details>
<summary>显示答案</summary>

**答案：B) 通过直接查询 Kafka Admin API**

**解释：**
KEDA 的 Kafka scaler 会直接调用 Kafka Admin API，使用 `bootstrapServers`、`consumerGroup` 和 `topic` 等 trigger 参数来确定消费者组延迟。这意味着单独的 Prometheus exporter（例如 `kafka-lag-exporter`）对于扩缩容决策并非严格必需（尽管它对于仪表板和告警仍然有用）。在 KRaft 模式下，ZooKeeper 不再存储 offset。
</details>

## 简答题

11. 用一句话定义消费者延迟。

<details>
<summary>显示答案</summary>

**答案：按分区计算，最新生产 offset（log end offset）与消费者组最后提交的 offset 之间的差值。**

**解释：**
消费者延迟以 offset 为单位，衡量消费者尚未处理的消息数量。延迟为 0 表示消费者已经追上最新消息；持续增加的延迟表示消费者的处理速率跟不上生产速率。
</details>

12. Strimzi 使用哪个组件将 Kafka broker 的 JMX 指标转换为 `/metrics` HTTP 端点？

<details>
<summary>显示答案</summary>

**答案：Prometheus JMX Exporter（一个 JVM Java agent）**

**解释：**
JMX Exporter 读取 JVM JMX MBean 值，根据已配置规则对其重命名并重新标记，然后在 `/metrics` 路径以 Prometheus 可抓取的文本格式暴露。当设置了 `metricsConfig` 时，Strimzi 会在 broker 等组件容器内的同一 JVM 进程中自动将它作为 Java agent 启用——而不是作为单独的 sidecar 容器。
</details>

13. 在 KEDA `ScaledObject` 的 Kafka trigger 中，哪个参数设置每分区延迟阈值，超过该值后会增加额外副本？

<details>
<summary>显示答案</summary>

**答案：`lagThreshold`**

**解释：**
`lagThreshold` 是可接受的每分区延迟值；每当实际延迟跨过该值的一个倍数时，KEDA 管理的 HPA 就会添加另一个副本。例如，使用 `lagThreshold: "50"` 且分区延迟为 120 时，大致会计算出需要 2-3 个副本。另外，`activationLagThreshold` 决定是否会发生从 0 到 1 个副本的初始扩容。
</details>

14. 哪一对指标可以在 under-replicated partitions 增加之前作为先行指标，用来描述副本离开或重新加入 ISR 集合的频率？

<details>
<summary>显示答案</summary>

**答案：ISR Shrink Rate 和 ISR Expand Rate（`isrshrinkspersec`、`isrexpandspersec`）**

**解释：**
ISR Shrink Rate 是副本退出 ISR 集合的每秒速率，ISR Expand Rate 是它们重新加入的速率。频繁 shrink 表明 follower 反复落后于 leader，这通常先于 under-replicated partitions 上升出现——因此它是一个有用的早期预警信号。
</details>

## 实践题

15. 编写一个 `Kafka` CR 的 `metricsConfig` YAML，使其引用名为 `kafka-metrics`、key 为 `kafka-metrics-config.yml` 的 `ConfigMap`。

<details>
<summary>显示答案</summary>

**答案：**
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

**解释：**
`type: jmxPrometheusExporter` 是 Strimzi 当前支持的唯一指标暴露类型，`valueFrom.configMapKeyRef` 指定保存重新标记规则的 `ConfigMap` 以及其中的 key。应用后，Strimzi Cluster Operator 会自动在 broker 容器内启用 JMX Exporter Java agent，并挂载引用的规则文件。
</details>

16. 编写一个 KEDA `ScaledObject`，基于 topic `orders` 上消费者组 `order-consumer-group` 的延迟，将 `order-consumer` `Deployment` 在 1 到 10 个副本之间扩缩容，并使用每分区延迟阈值 50。

<details>
<summary>显示答案</summary>

**答案：**
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

**解释：**
`scaleTargetRef.name` 标识目标 `Deployment`，而 `minReplicaCount`/`maxReplicaCount` 限定扩缩容范围。`triggers` 下的 `type: kafka` 选择 Kafka scaler，其 `metadata` 提供 bootstrap servers、消费者组、topic 和延迟阈值。KEDA Operator 使用此资源创建并管理标准 Kubernetes HPA。
</details>

17. 编写一个 `PrometheusRule`，当 under-replicated partitions 持续高于 0 至少 5 分钟时，触发 `warning` 级别的告警。

<details>
<summary>显示答案</summary>

**答案：**
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

**解释：**
`expr` 对整个集群的 under-replicated partitions 求和，并检查总数是否大于 0。`for: 5m` 要求条件保持 5 分钟后，告警才会转换为 `firing`，从而减少瞬时尖峰造成的噪声。`labels.severity` 对告警严重级别进行分类，以便用于 Alertmanager 路由。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/07-monitoring.md) | [上一测验：MSK 集成](./06-msk-integration-quiz.md) | [下一测验：最佳实践](./08-best-practices-quiz.md)
