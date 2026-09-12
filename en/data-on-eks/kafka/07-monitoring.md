# Part 7: Monitoring

> **Review baseline**: Strimzi 1.2.0 / Kafka 4.3.1, bundled JMX Exporter 1.6.0 and Kafka Exporter 1.9.0, Prometheus Operator 0.93.1, KEDA 2.20.2\
> **Last reviewed**: September 12, 2026

## What each component observes

| Component | Role |
| --- | --- |
| JMX Prometheus Exporter | Maps in-process JVM MBeans to Prometheus metrics as a Java agent |
| Strimzi Metrics Reporter | Another supported `metricsConfig.type`; directly exposes Kafka metrics with its own configuration/naming |
| Kafka Exporter | Uses Kafka APIs to expose consumer-group offsets/lag and topic information |
| Prometheus / Prometheus Operator | Discovers and scrapes targets, evaluates rules and passes alerts to Alertmanager |
| KEDA Kafka scaler | Queries Kafka APIs for scaling; it does not require the lag exporter's Prometheus endpoint |

This chapter chooses **`jmxPrometheusExporter`**. Its mapping rules are not the same
thing as Prometheus target relabeling. `strimziMetricsReporter` is also supported,
so the old claim that JMX is the only option is incorrect. Changing exporter type
requires reviewing metric names and dashboards.

The examples build on [Part 2](./02-strimzi-operator.md): namespace `kafka`,
`my-cluster`, three broker pods, three controller pods, and a 12-partition `orders`
topic. Its node pools label pods with `docs.example.com/kafka-role: broker` or
`controller`. Prometheus Operator and KEDA must already be installed.

## Enable JMX metrics without replacing the cluster spec

Save the following as `metrics-config.yaml`. These focused rules expose replication
gauges, a broker request-handler idle ratio and throughput/ISR counters. Counter
names end in `_total`; use `rate()` on counters, not on an already computed rate.

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

Save this as **`metrics.patch.yaml`**. It is a merge patch for the existing Kafka
resource, not a complete resource to create/apply. Existing listeners, authentication,
storage and other settings are preserved.

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

The first section enables the in-process JMX agent. The second deploys Strimzi's
**Kafka Exporter**, which has a different implementation and metric names from
`seglo/kafka-lag-exporter`. That older project is archived; this chapter does not
recommend it as the current default.

Strimzi manages the exporter's connection and certificate material for its internal
Kafka listener; do not replace that with an unauthenticated 9092 address. The
release's exporter uses port **9404**, named **`tcp-prometheus`**, as do the Kafka
node metrics endpoints. Kafka Exporter is a separate workload.

`KafkaConnect` and `KafkaMirrorMaker2` have their own metrics configuration.
Cruise Control is configured under `Kafka.spec.cruiseControl`; it is not a
standalone `CruiseControl` CRD. Do not blindly reuse Kafka MBean rules for every component.

## Discover the intended targets

Save as `podmonitors.yaml`. Node and lag-exporter targets are selected separately.
The relabeling creates a stable `namespace`, `kafka_cluster`, `kafka_component`,
and, for Kafka nodes, `kafka_role` context for queries.

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

The `release` label must match your Prometheus resource's PodMonitor/PrometheusRule
selectors. Its namespace selectors and RBAC must also discover resources in `kafka`.
Check network policies and port access from Prometheus to these pods.

A correctly configured **ServiceMonitor also works** with a matching Service.
PodSet versus StatefulSet does not determine whether ServiceMonitor can work.
Here PodMonitor is a direct pod-discovery choice, not inherently a more reliable
protocol. Scrape each endpoint once; remove duplicate discovery paths and deduplicate
HA Prometheus replicas before aggregating a federated view.

## Read the metrics in context

| Metric in this mapping | Interpretation |
| --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | Normally zero; can rise during failures, lag or planned maintenance. Check duration and affected partitions |
| `kafka_server_replicamanager_underminisrpartitioncount` | Partitions below configured minimum ISR; important for write availability with `acks=all` |
| `kafka_controller_kafkacontroller_activecontrollercount` | Sum over one cluster's controller pods should settle at one; verify sample coverage and duplicate/stale scrapes |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | Partitions without an available leader; investigate availability |
| `kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent` | Gauge ratio, typically 0–1. Low values require correlation with CPU, GC, I/O and request latency, not automatic diagnosis |
| `kafka_server_brokertopicmetrics_bytesin_total` / `bytesout_total` | Per-topic byte counters; use `rate` for throughput |
| `kafka_server_replicamanager_isrshrinks_total` / `isrexpands_total` | ISR-change counters; correlate churn with replication status |

A controller sum above one is an abnormal **observation**, not proof of split brain:
cross-cluster aggregation, duplicate targets, scrape timing and stale samples must
be checked first. Missing samples are not zero. Under-replication alone also does
not mean data loss has occurred.

Per-topic ingest throughput:

```promql
sum by (namespace, kafka_cluster, topic) (
  rate(kafka_server_brokertopicmetrics_bytesin_total{
    namespace="kafka",kafka_cluster="my-cluster"
  }[5m])
)
```

Topic aggregate traffic does not identify which partition is hot. Add appropriately
scoped per-partition/client observations when investigating skew. The focused
mapping here is not the full upstream dashboard metric set.

## Consumer lag is committed-offset distance

For each partition, lag is normally the **log-end next offset minus the group's
committed next offset**. It is an offset distance, not always a count of business
records: compaction, offset gaps and transactions matter. A commit before durable
processing can make lag look healthy while work is unfinished.

JMX mapping of broker MBeans does not itself perform the group/partition offset
queries needed for this measurement. Strimzi's Kafka Exporter supplies
`kafka_consumergroup_lag`, labeled **`consumergroup`**, `topic` and `partition`.
Do not query the archived exporter's `kafka_consumergroup_group_lag` name or assume
its `group` label applies here.

```promql
sum by (namespace, kafka_cluster, consumergroup, topic) (
  kafka_consumergroup_lag{
    namespace="kafka",kafka_cluster="my-cluster",
    topic="orders",consumergroup="order-processor"
  } >= 0
)
```

The filter excludes negative/unknown lag values from a backlog total; it must not
hide unavailable data. Watch exporter health, missing expected groups and
`kafka_consumergroup_current_offset < 0` separately. Groups with no commits,
authentication failures and filtered-out topics can produce missing results.
Zero committed-offset lag is not an end-to-end processing SLO.

## Alerts must also detect missing data

Save as `alerts.yaml`. The expected counts, six Kafka nodes and three controllers,
match this chapter's topology. Update them when changing the node pools. The
expected group/topic alert assumes `order-processor` should be committing on
`orders`; adjust its scope and startup grace period for your application.

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

These thresholds and durations are starting points. `for` requires a continuously
present true condition before firing; it is not a scrape interval or a rolling
average. `sum(metric) != 1` alone does **not** detect an entirely missing metric
family because the result can be an empty vector. The separate coverage and
`absent()` rules handle those cases.

```bash
kubectl apply -f metrics-config.yaml
kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl apply -f podmonitors.yaml -f alerts.yaml
```

Inspect the Kafka resource's observed generation/conditions, actual pod ports and
Prometheus Targets and Rules pages. A configuration change can roll workloads.
Validate Alertmanager routing/delivery separately; creating a PrometheusRule does
not prove that a notification reached an operator.

## Scale consumers with authenticated KEDA queries

The target `Deployment/order-consumer` must already exist **in namespace `kafka`**,
connect using the Part 2 TLS/SCRAM listener, and consume as `order-processor`.
Its application credentials are separate from the scaler's read-only metadata
identity below. The ScaledObject and TriggerAuthentication also live in `kafka`.

Save as `keda-auth.yaml`. The username Secret contains no password; the User Operator
generates the password Secret. KEDA reads the username, password and CA through
the TriggerAuthentication references.

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

Save as `scaledobject.yaml`. TLS hostname verification stays enabled. KEDA's
operator must reach the broker endpoints and have access to the referenced Secrets.

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

`lagThreshold: "50"` is the desired **total effective lag per replica**, not a
separate threshold that creates several consumers for each partition. For the
default AverageValue target, the rough demand is `ceil(effective total lag / 50)`,
subject to scaler adjustments, HPA tolerance, min/max replicas and stabilization.
Adding consumers cannot make one partition be consumed simultaneously by several
members of the same conventional consumer group.

`allowIdleConsumers=false` makes the scaler consider the partition count; use an
explicit `maxReplicaCount` no greater than available partitions when a strict cap
matters. This example caps at 10 with the Part 2 topic's 12 partitions. A topic or
workload with a different partition count needs a corresponding review.

Because `minReplicaCount=1`, this example does **not scale to zero**.
`activationLagThreshold` and KEDA's zero-scaling `cooldownPeriod` are not the
controls for its 1↔N behavior. HPA scale-down stabilization is configured explicitly.
If enabling zero scaling later, test new groups/missing commits, offset-reset policy,
startup and activation; do not treat unknown offsets as an empty queue.

```bash
kubectl apply -f keda-auth.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/keda-lag-reader
kubectl apply -f scaledobject.yaml
kubectl -n kafka get scaledobject order-consumer-scaler -o yaml
kubectl -n kafka get hpa
```

Compare scaler errors, the HPA's current/desired metrics and actual consumer
throughput before changing limits. The existing [KEDA guide](../../autoscaling/01-keda.md)
covers general autoscaling behavior.

## Dashboards and validation

Use the versioned upstream **Kafka, KRaft, Kafka Exporter, Connect and Cruise Control**
dashboards as references, matching the selected exporter type and label mapping.
The Strimzi 1.2 set is not a ZooKeeper deployment guide. Importing a dashboard does
not guarantee that its queries exist in this focused mapping.

Include JVM/GC, node/PVC capacity and I/O, replication availability, scrape coverage,
traffic distribution, group progress and application latency/error SLOs. The
in-process exporter also exposes JVM metrics, but host/PVC and application signals
come from their corresponding collectors.

The example's final JMX rules and Kafka Exporter were exercised against an isolated
local Kafka 4.3.1 broker: 15 records and committed offsets produced partition lags
**3, 5 and 5**. Nine alert rules were tested across normal, missing-data, failure and
cross-cluster-isolation scenarios. These tests do not prove production TLS access,
multi-node quorum behavior, Strimzi reconciliation, notification delivery or KEDA
operation against your actual workload.

- [Strimzi 1.2.0 metrics example](https://github.com/strimzi/strimzi-kafka-operator/blob/1.2.0/examples/metrics/kafka-metrics.yaml)
- [Strimzi 1.2.0 Kafka Exporter implementation](https://github.com/strimzi/strimzi-kafka-operator/blob/1.2.0/cluster-operator/src/main/java/io/strimzi/operator/cluster/model/KafkaExporter.java)
- [Strimzi 1.2.0 bundled exporter versions](https://github.com/strimzi/strimzi-kafka-operator/blob/1.2.0/docker-images/kafka-based/kafka/Dockerfile)
- [Kafka Exporter 1.9.0](https://github.com/danielqsj/kafka_exporter/tree/v1.9.0)
- [Archived kafka-lag-exporter project](https://github.com/seglo/kafka-lag-exporter)
- [KEDA 2.20 Kafka scaler](https://keda.sh/docs/2.20/scalers/apache-kafka/)
- [KEDA 2.20.2 implementation](https://github.com/kedacore/keda/blob/v2.20.2/pkg/scalers/kafka_scaler.go)
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Versioned JMX-based Grafana dashboards](https://github.com/strimzi/strimzi-kafka-operator/tree/1.2.0/examples/metrics/grafana-dashboards)
- [Versioned Strimzi Metrics Reporter dashboards](https://github.com/strimzi/strimzi-kafka-operator/tree/1.2.0/examples/metrics/strimzi-metrics-reporter/grafana-dashboards)

## Next steps

[Part 8: Best practices](./08-best-practices.md)

[Return to main page](./README.md)

## Quiz

[Topic quiz](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
