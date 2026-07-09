# Part 7: Monitoring Quiz

This quiz tests your understanding of how Strimzi exposes metrics, what the core broker metrics mean, how consumer lag is measured, and how the KEDA Kafka scaler is configured.

## Multiple Choice Questions

1. What does Strimzi run inside each broker container to convert JMX metrics into a form Prometheus can scrape?
   - A) A Fluent Bit sidecar
   - B) A Prometheus JMX Exporter (JVM Java agent)
   - C) An OpenTelemetry Collector DaemonSet
   - D) cAdvisor

<details>

<summary>Show Answer</summary>

**Answer: B) A Prometheus JMX Exporter (JVM Java agent)**

**Explanation:**
When `metricsConfig` is configured on the `Kafka` CR, Strimzi automatically enables a Prometheus JMX Exporter inside each broker (and Connect, etc.) container — not as a separate sidecar container, but as a Java agent loaded into the same JVM process. This exporter reads JVM-internal JMX MBean values, renames them according to relabeling rules, and exposes them in Prometheus text format at a `/metrics` HTTP endpoint. Fluent Bit is a log collector and cAdvisor collects container resource metrics — neither serves this purpose.
</details>

2. What kind of resource does `Kafka.spec.kafka.metricsConfig` reference to obtain the JMX Exporter's relabeling rules?
   - A) Secret
   - B) PersistentVolumeClaim
   - C) ConfigMap
   - D) CustomResourceDefinition

<details>

<summary>Show Answer</summary>

**Answer: C) ConfigMap**

**Explanation:**
`metricsConfig.valueFrom.configMapKeyRef` points to the name and key of a `ConfigMap` containing the relabeling rules (in YAML). Strimzi mounts this rules file into the container running the JMX Exporter Java agent so it knows which JMX MBeans map to which Prometheus metric names and labels. A `Secret` is for sensitive values like certificates or credentials and is not used for this purpose.
</details>

3. What is the healthy value for the `kafka_server_replicamanager_underreplicatedpartitions` metric?
   - A) It should equal the number of brokers
   - B) It should equal the number of partitions
   - C) It should always be 0
   - D) It should always be 1

<details>

<summary>Show Answer</summary>

**Answer: C) It should always be 0**

**Explanation:**
This metric counts the partitions led by a given broker whose in-sync replica (ISR) set is smaller than the configured replication factor. Under normal operation every follower should be keeping up with the leader, so this value should be 0. A value above 0 signals that some replicas are falling behind — often due to network latency, broker overload, or disk I/O bottlenecks — and is a direct risk to data durability if the leader then fails with an insufficient ISR.
</details>

4. What should the cluster-wide sum of `kafka_controller_kafkacontroller_activecontrollercount` be under healthy operation?
   - A) 0
   - B) Equal to the number of brokers
   - C) Exactly 1
   - D) Equal to the number of controller candidates

<details>
<summary>Show Answer</summary>

**Answer: C) Exactly 1**

**Explanation:**
Each broker/controller exposes whether it is currently the active controller as 0 or 1. Summing this across the cluster should yield exactly 1 under healthy operation. A sum of 0 means there is no active controller (leader election in progress, or a failure); a sum of 2 or more suggests a serious anomaly such as a split-brain condition and warrants immediate investigation.
</details>

5. If the Request Handler Idle Ratio stays persistently low (for example, below 10%), what should you suspect first?
   - A) Disk capacity is running low
   - B) The broker is approaching saturation on CPU/thread resources
   - C) The ZooKeeper connection has dropped
   - D) A consumer group is rebalancing

<details>
<summary>Show Answer</summary>

**Answer: B) The broker is approaching saturation on CPU/thread resources**

**Explanation:**
The Request Handler Idle Ratio is the fraction of time a broker's request-handling thread pool sits idle. A low value means the thread pool is constantly busy processing requests, signaling the broker is nearing its CPU or thread capacity limits. Persistently low values are a cue to consider scaling out brokers, rebalancing partitions, or tuning thread pool size.
</details>

6. Why don't the broker metrics Strimzi exposes by default include consumer group lag?
   - A) Consumer lag is sensitive information that cannot be exposed for security reasons
   - B) Computing lag requires correlating a consumer group's committed offsets with a topic's latest offsets, but the JMX Exporter only reads the broker's own JMX MBeans
   - C) The Strimzi version used is too old to support it
   - D) Consumer lag can only be measured from the client side

<details>
<summary>Show Answer</summary>

**Answer: B) Computing lag requires correlating a consumer group's committed offsets with a topic's latest offsets, but the JMX Exporter only reads the broker's own JMX MBeans**

**Explanation:**
The JMX Exporter Java agent only reads and exposes JMX MBeans internal to the broker process (replication state, throughput, controller status, etc.). Consumer lag is the difference between a consumer group's last committed offset and a topic's latest (log end) offset, which requires querying both values separately through the Kafka Admin API. This is why consumer lag is typically measured with a dedicated tool such as `kafka-lag-exporter`.
</details>

7. Which community exporter is introduced in this document for measuring consumer lag?
   - A) node-exporter
   - B) kafka-lag-exporter
   - C) blackbox-exporter
   - D) kube-state-metrics

<details>
<summary>Show Answer</summary>

**Answer: B) kafka-lag-exporter**

**Explanation:**
`kafka-lag-exporter` is a community project that periodically queries a consumer group's committed offsets and each topic's latest offsets via the Kafka Admin API, then exposes metrics such as `kafka_consumergroup_group_lag` in Prometheus format. `node-exporter` collects host system metrics, `blackbox-exporter` probes endpoints, and `kube-state-metrics` reports Kubernetes object state — none of these serve this purpose.
</details>

8. When scraping Strimzi-managed Kafka broker pods in a Prometheus Operator environment, which CRD is more reliable than targeting a fixed `Service`?
   - A) ServiceMonitor
   - B) PodMonitor
   - C) Probe
   - D) AlertmanagerConfig

<details>
<summary>Show Answer</summary>

**Answer: B) PodMonitor**

**Explanation:**
Brokers run as individual pods managed by Strimzi. A `PodMonitor` that selects pods directly by label (such as `strimzi.io/cluster`) discovers scrape targets more reliably than a `ServiceMonitor`, which targets a fixed `Service` endpoint. `Probe` is for blackbox-style endpoint checks, and `AlertmanagerConfig` configures alert routing — neither is for pod-level metric scraping.
</details>

9. In a `PrometheusRule` alert for under-replicated partitions, what does `for: 5m` do?
   - A) It scrapes metrics every 5 minutes
   - B) The condition must hold true continuously for 5 minutes before the alert actually fires
   - C) The alert automatically resolves 5 minutes after firing
   - D) It computes a 5-minute average of the value

<details>
<summary>Show Answer</summary>

**Answer: B) The condition must hold true continuously for 5 minutes before the alert actually fires**

**Explanation:**
In a Prometheus alerting rule, the `for` field means the condition in `expr` must remain true for the specified duration before the alert transitions from `pending` to `firing`. Setting `for: 5m` reduces noisy alerts caused by momentary spikes and ensures alerts only fire for genuinely persistent problems.
</details>

10. How does KEDA's Kafka scaler determine a consumer group's lag?
    - A) By scraping the Prometheus metrics exposed by kafka-lag-exporter
    - B) By querying the Kafka Admin API directly
    - C) By parsing the broker's JMX Exporter `/metrics` endpoint
    - D) By reading offsets stored in ZooKeeper

<details>
<summary>Show Answer</summary>

**Answer: B) By querying the Kafka Admin API directly**

**Explanation:**
KEDA's Kafka scaler calls the Kafka Admin API directly, using trigger parameters like `bootstrapServers`, `consumerGroup`, and `topic`, to determine a consumer group's lag. This means a separate Prometheus exporter such as `kafka-lag-exporter` is not strictly required for scaling decisions (though it remains useful for dashboards and alerting). ZooKeeper no longer stores offsets in KRaft mode.
</details>

## Short Answer Questions

11. Define consumer lag in one sentence.

<details>
<summary>Show Answer</summary>

**Answer: The difference, per partition, between the latest produced offset (the log end offset) and the offset a consumer group has last committed.**

**Explanation:**
Consumer lag measures, in units of offsets, how many messages a consumer has not yet processed. A lag of 0 means the consumer has caught up to the latest message; steadily increasing lag signals the consumer's processing rate can't keep up with the produce rate.
</details>

12. What is the name of the component Strimzi uses to convert a Kafka broker's JMX metrics into a `/metrics` HTTP endpoint?

<details>
<summary>Show Answer</summary>

**Answer: Prometheus JMX Exporter (a JVM Java agent)**

**Explanation:**
The JMX Exporter reads JVM JMX MBean values, renames and relabels them according to configured rules, and exposes them in a Prometheus-scrapeable text format at a `/metrics` path. When `metricsConfig` is set, Strimzi automatically enables this as a Java agent inside the same JVM process on component containers such as brokers — not as a separate sidecar container.
</details>

13. In a KEDA `ScaledObject`'s Kafka trigger, what parameter sets the per-partition lag value above which additional replicas are added?

<details>
<summary>Show Answer</summary>

**Answer: `lagThreshold`**

**Explanation:**
`lagThreshold` is the acceptable per-partition lag value; every time the actual lag crosses a multiple of this value, the HPA that KEDA manages adds another replica. For example, with `lagThreshold: "50"` and a partition lag of 120, roughly 2-3 replicas would be calculated as needed. Separately, `activationLagThreshold` determines whether the initial scale-up from 0 to 1 replica happens at all.
</details>

14. What pair of metrics can serve as a leading indicator before under-replicated partitions increase, describing how often replicas leave or rejoin the ISR set?

<details>
<summary>Show Answer</summary>

**Answer: ISR Shrink Rate and ISR Expand Rate (`isrshrinkspersec`, `isrexpandspersec`)**

**Explanation:**
ISR Shrink Rate is the per-second rate at which replicas drop out of the ISR set, and ISR Expand Rate is the rate at which they rejoin. Frequent shrinks indicate followers are repeatedly falling behind the leader, which often precedes a rise in under-replicated partitions — making it a useful early-warning signal.
</details>

## Hands-on Questions

15. Write the YAML for a `Kafka` CR's `metricsConfig` that references a `ConfigMap` named `kafka-metrics` with key `kafka-metrics-config.yml`.

<details>
<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`type: jmxPrometheusExporter` is currently the only metrics exposition type Strimzi supports, and `valueFrom.configMapKeyRef` specifies the `ConfigMap` holding the relabeling rules and the key within it. Once applied, the Strimzi Cluster Operator automatically enables the JMX Exporter Java agent inside broker containers and mounts the referenced rules file.
</details>

16. Write a KEDA `ScaledObject` that scales the `order-consumer` `Deployment` between 1 and 10 replicas based on the lag of consumer group `order-consumer-group` on topic `orders`, using a per-partition lag threshold of 50.

<details>
<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
`scaleTargetRef.name` identifies the target `Deployment`, while `minReplicaCount`/`maxReplicaCount` bound the scaling range. `type: kafka` under `triggers` selects the Kafka scaler, and its `metadata` supplies the bootstrap servers, consumer group, topic, and lag threshold. The KEDA Operator uses this resource to create and manage a standard Kubernetes HPA.
</details>

17. Write a `PrometheusRule` that fires a `warning`-severity alert when under-replicated partitions stay above 0 for at least 5 minutes.

<details>
<summary>Show Answer</summary>

**Answer:**
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

**Explanation:**
The `expr` sums under-replicated partitions across the cluster and checks whether the total is above 0. `for: 5m` requires the condition to hold for 5 minutes before the alert transitions to `firing`, reducing noise from momentary spikes. `labels.severity` classifies the alert's severity for use in Alertmanager routing.
</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/07-monitoring.md) | [Previous Quiz: MSK Integration](./06-msk-integration-quiz.md) | [Next Quiz: Best Practices](./08-best-practices-quiz.md)
