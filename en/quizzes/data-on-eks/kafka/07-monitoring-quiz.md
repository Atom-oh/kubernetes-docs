# Part 7: Monitoring Quiz

Review actual metric names, scrape scope/missing data, lag and authenticated KEDA behavior.

## 1. How does this chapter's JMX approach run, and is it Strimzi's only metrics option?

<details>
<summary>Show answer</summary>

JMX Exporter runs as a Java agent in the same JVM. Strimzi also supports strimziMetricsReporter. Review naming, configuration and dashboards when switching.

</details>

## 2. How do JMX MBean mapping rules differ from PodMonitor relabeling?

<details>
<summary>Show answer</summary>

The ConfigMap's JMX rules map MBeans to metric names/labels. PodMonitor relabeling is a separate discovery step that supplies target context such as namespace, kafka_cluster and role.

</details>

## 3. Does UnderReplicatedPartitions above zero mean data has already been lost?

<details>
<summary>Show answer</summary>

No. The healthy steady-state value is zero, but failures, lag or planned operations can increase it. Check duration, under-min-ISR/offline partitions and the cause.

</details>

## 4. Can an active-controller sum of two immediately be diagnosed as split brain?

<details>
<summary>Show answer</summary>

No. First check cluster scope, duplicate targets, stale samples and scrape timing. The expected steady-state sum for one cluster's controllers is one.

</details>

## 5. What should be correlated with a low BrokerRequestHandlerAvgIdlePercent?

<details>
<summary>Show answer</summary>

Correlate CPU, GC, I/O, request latency/queues and throughput. It indicates busy handlers, not a conclusive CPU-only diagnosis or an automatic reason to add threads/brokers.

</details>

## 6. Does broker JMX mapping alone calculate consumer-group lag?

<details>
<summary>Show answer</summary>

No. It requires group committed offsets and partition-end offsets. This chapter uses Strimzi Kafka Exporter; KEDA independently queries Kafka APIs.

</details>

## 7. Name the chosen Kafka Exporter lag metric/group label and describe the older project's status.

<details>
<summary>Show answer</summary>

`kafka_consumergroup_lag` and `consumergroup`. The older seglo/kafka-lag-exporter is archived; do not confuse its kafka_consumergroup_group_lag/group convention with this exporter.

</details>

## 8. Is PodMonitor always more reliable than ServiceMonitor?

<details>
<summary>Show answer</summary>

No. ServiceMonitor works with a correct Service and selectors. This chapter chooses direct pod discovery; verify Prometheus label/namespace selectors, RBAC, networking and duplicate scrapes.

</details>

## 9. Explain for: 5m and missing-data behavior in a PrometheusRule.

<details>
<summary>Show answer</summary>

The condition must remain present and true for five minutes before firing. It is not a scrape interval or average. A missing metric family can make a sum comparison empty, so include absent and scrape-coverage checks.

</details>

## 10. Does the KEDA Kafka scaler require a Prometheus lag exporter?

<details>
<summary>Show answer</summary>

No. It queries Kafka APIs directly and needs its own broker reachability, TLS, authentication and Secret access. This is a different path from the dashboard exporter.

</details>

## 11. Does lag = 0 prove that business processing is complete?

<details>
<summary>Show answer</summary>

No. It normally measures log-end next offset minus committed next offset. Early commits or data/collection conditions can differ from business completion. Compaction and transactions can also make it differ from a physical record count.

</details>

## 12. How should bytesin_total and idle_percent be queried?

<details>
<summary>Show answer</summary>

Use rate(...[5m]) on the bytesin_total counter for per-second throughput. idle_percent is already a ratio gauge; observe it directly rather than applying rate again.

</details>

## 13. Explain lagThreshold=50 with minReplicaCount=1.

<details>
<summary>Show answer</summary>

The target is 50 effective total lag per replica; roughly ceil(total lag/50) is subject to HPA/scaler adjustments and limits. It does not create multiple consumers for each partition. With min=1, inspect HPA scale-down behavior, not zero-scaling activation/cooldown.

</details>

## 14. What do ISR changes and topic throughput reveal, and what are their limits?

<details>
<summary>Show answer</summary>

Rates of ISR shrink/expand counters reveal churn to correlate with replication health. Topic aggregate throughput alone cannot identify a hot partition; add partition/client observations.

</details>

## 15. Write the patch that adds the chapter's metricsConfig and Kafka Exporter to the existing Kafka resource.

<details>
<summary>Show answer</summary>

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

Create metrics-config.yaml first, then use `kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml`. This is not a complete Kafka creation manifest and preserves existing authentication/listeners.

</details>

## 16. Write the ScaledObject that uses TLS/SCRAM and a TriggerAuthentication in the same namespace.

<details>
<summary>Show answer</summary>

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

This requires the chapter's keda-auth.yaml and existing kafka/order-consumer Deployment. The application must consume as order-processor. The maximum of 10 fits Part 2's 12 partitions; adjust it for other topologies.

</details>

## 17. How should cluster scope, for and missing-data handling be separated in an under-replication alert?

<details>
<summary>Show answer</summary>

Scope the gauge to namespace="kafka", kafka_cluster="my-cluster", sum per cluster, and apply for:5m to >0. Add separate node scrape-coverage and controller-metric-missing rules. For lag, also monitor exporter failure, missing expected groups and negative committed offsets.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/07-monitoring.md) | [Previous quiz](./06-msk-integration-quiz.md) | [Next quiz](./08-best-practices-quiz.md)
