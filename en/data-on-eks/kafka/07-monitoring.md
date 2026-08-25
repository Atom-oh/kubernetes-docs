# Part 7: Monitoring

> **Supported Versions**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **Last Updated**: July 9, 2026

A Kafka cluster needs more than broker heap, disk, and network graphs — you also need visibility into partition replication health and consumer processing speed to catch problems early. This document covers scraping the broker metrics Strimzi exposes with Prometheus, measuring consumer lag separately, and autoscaling consumers with KEDA.

## 1. How Strimzi Exposes Metrics

Strimzi runs a Prometheus JMX Exporter inside each broker/controller/Connect component container — not as a separate sidecar container, but as a **JVM Java agent** loaded into the same JVM process. The JMX Exporter reads JVM-internal JMX MBeans (for example `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`) and converts them into a Prometheus text-format `/metrics` HTTP endpoint. Which MBeans map to which metric names and labels is defined by a relabeling configuration stored in a `ConfigMap`, and the `Kafka` CR's `metricsConfig` field points at that `ConfigMap`.

The Strimzi upstream repository ships example JMX Exporter configurations for brokers, Connect, and Cruise Control under [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics). In practice, teams start from these examples and adjust only the rules they need rather than writing relabeling rules from scratch.

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

Once `metricsConfig` is applied, Strimzi automatically enables the JMX Exporter Java agent inside every broker container and mounts the referenced `ConfigMap`'s rules file into that same container. Prometheus-format metrics then become scrapeable at the `/metrics` path on port `9404` (the default) of each broker pod. The same `metricsConfig` field is available on `KafkaConnect`, `KafkaMirrorMaker2`, and `CruiseControl` custom resources.

## 2. Core Broker Metrics

Kafka exposes a large number of JMX metrics, so it helps to narrow down which ones actually matter day to day.

| Metric | Meaning | Healthy value / what to watch for |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | Number of partitions this broker leads whose in-sync replica (ISR) set is smaller than the configured replication factor | **Should be 0.** Any value above 0 means one or more followers are falling behind the leader — investigate network latency, broker overload, or disk I/O bottlenecks. |
| `kafka_controller_kafkacontroller_activecontrollercount` | Whether this broker/controller is currently the active controller (0 or 1) | The cluster-wide **sum must be exactly 1**. A sum of 0 means no active controller (leader election in progress or a failure); a sum of 2 or more suggests a split-brain condition and needs immediate investigation. |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | Fraction of time the broker's request-handler thread pool sits idle | A declining value (for example, below 20%) signals the broker is approaching CPU/thread saturation. Persistently low values are a signal to scale out brokers or rebalance partitions. |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | Per-topic produce/consume throughput in bytes per second | Used for broker/network capacity planning and detecting traffic spikes on individual topics (hot partitions). |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | Rate at which replicas leave (shrink) or rejoin (expand) the ISR set per second | Frequent shrinks mean followers are repeatedly falling out of sync, and typically precede an increase in under-replicated partitions. |

Of these, **under-replicated partition count** and **active controller count** most directly reflect the cluster's data safety and availability, so they belong at the top of every dashboard and alert rule set.

```promql
# Cluster-wide active controller sum (should be 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# Brokers currently reporting under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. Consumer Lag Monitoring

**Consumer lag** is, per partition, the difference between the latest produced offset (the log end offset) and the last offset a consumer group has committed. Steadily growing lag means a consumer group can't keep up with the produce rate — a sign of slow processing, a stalled consumer, or repeated rebalancing.

The JMX Exporter metrics Strimzi exposes via this in-process Java agent describe the **broker's own state** (section 2 above) and do not, by default, include consumer group offsets or lag. Computing lag requires correlating a consumer group's committed offsets (tracked in the internal `__consumer_offsets` topic) with each topic's latest offset, which is outside the scope of the broker-side exporter. Because of this, teams typically run a separate exporter dedicated to consumer lag.

The most widely used option is the community project [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter) (or a similar Burrow-style exporter), run as its own `Deployment` in the cluster. It polls the Kafka Admin API on an interval to read each consumer group's committed offsets and each topic's latest offsets, then exposes metrics such as `kafka_consumergroup_group_lag` (lag broken down by group, topic, and partition) in Prometheus format.

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

Once this exporter is deployed and Prometheus is scraping its `/metrics` endpoint, lag can be queried like this:

```promql
# Total lag per consumer group and topic (summed across partitions)
sum by (group, topic) (kafka_consumergroup_group_lag)

# Group/topic combinations with lag above 1000
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. Wiring Up Scraping with ServiceMonitor / PodMonitor

In environments running the Prometheus Operator (such as kube-prometheus-stack), the usual approach is not to hand-edit `scrape_configs` but to declare a `PodMonitor` CRD that discovers targets by label. Because brokers run as pods managed by Strimzi rather than behind a fixed `Service`, selecting pods directly with a `PodMonitor` is more reliable than relying on a `Service`-based `ServiceMonitor`.

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

Once metrics are flowing, alerting on under-replicated partitions is the most basic safety net to put in place. The `PrometheusRule` below fires when under-replicated partitions stay above 0 for at least 5 minutes.

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

## 5. Autoscaling Consumers with KEDA

CPU/memory-based HPA often fails to reflect a consumer workload's actual load — the number of messages waiting to be processed. KEDA's Kafka scaler (`triggers.type: kafka`) lets you scale a consumer `Deployment` based on **consumer group lag** instead. KEDA queries the lag for the configured topic/consumer group directly through the Kafka Admin API, so scaling decisions don't strictly require the separate lag exporter from section 3 (though that exporter is still useful for dashboards and alerting).

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

Key trigger parameters:

* **`bootstrapServers`**: The Kafka cluster's bootstrap address KEDA uses to query lag
* **`consumerGroup`**, **`topic`**: The consumer group and topic whose lag is measured
* **`lagThreshold`**: The per-partition lag value above which KEDA adds another replica (for example, one additional replica per 50 units of per-partition lag)
* **`activationLagThreshold`**: The minimum lag required to trigger the initial scale-up from 0 to 1 replica. If unset, even a small amount of lag immediately scales to 1.
* **`allowIdleConsumers`**: When `false` (the default), KEDA caps replicas so it never creates more consumers than there are partitions to consume.

Once this `ScaledObject` is applied, the KEDA Operator creates and manages a standard Kubernetes HPA behind the scenes, and scales back down after `cooldownPeriod` once lag subsides. For the broader KEDA concepts — scaler types, architecture, zero scaling — see the dedicated [Autoscaling: KEDA](../../autoscaling/01-keda.md) document.

## 6. Grafana Dashboards

Strimzi ships example Grafana dashboard JSON for brokers, ZooKeeper (legacy mode), Kafka Connect, and Cruise Control under [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) in its GitHub repository. Importing these and adjusting the cluster name/namespace variables is generally faster than building panels from scratch.

A solid Kafka dashboard should cover at least these panel groups:

* **Broker health**: per-broker uptime, JVM heap usage, GC pause time, request-handler/network idle ratio
* **ISR/replication status**: under-replicated partition count, ISR shrink/expand rate, active controller count (cluster-wide sum)
* **Throughput**: per-topic and per-broker bytes in/out per second, messages per second, per-partition throughput imbalance (hot-partition detection)
* **Consumer lag**: lag trend per consumer group, correlated with rebalance events to spot the cause of sudden spikes

## Next Steps

With metrics collection, alerting, and autoscaling in place, the next step is applying all of this to real operational standards — SLOs, capacity planning, and incident response procedures. That's covered in [Part 8: Best Practices](./08-best-practices.md).

[Return to Main Page](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Topic Quiz](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md).
