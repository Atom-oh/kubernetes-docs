# パート 7: モニタリング

> **検証基準**: Strimzi 1.3.0 / Kafka 4.3.1、同梱の JMX Exporter 1.6.0 と Kafka Exporter 1.10.0、Prometheus Operator 0.94.1、KEDA 2.21.0\
> **最終確認日**: 2026年10月16日

## 各コンポーネントが観測するもの

| コンポーネント | 役割 |
| --- | --- |
| JMX Prometheus Exporter | Java agent として、プロセス内の JVM MBean を Prometheus メトリクスに変換 |
| Strimzi Metrics Reporter | 別のサポート対象 `metricsConfig.type`。独自の設定と命名で Kafka メトリクスを直接公開 |
| Kafka Exporter | Kafka API を使い、consumer group の offset／lag と topic 情報を公開 |
| Prometheus / Prometheus Operator | target を検出・scrape し、rule を評価して Alertmanager に alert を渡す |
| KEDA Kafka scaler | scaling のため Kafka API に問い合わせる。lag exporter の Prometheus endpoint は不要 |

この章では **`jmxPrometheusExporter`** を選びます。その mapping rule は Prometheus target の relabeling とは別のものです。`strimziMetricsReporter` もサポートされるため、JMX だけが選択肢だという従来の説明は正しくありません。exporter の種類を変える場合は、メトリクス名と dashboard を見直してください。

例は[パート 2](./02-strimzi-operator.md)の構成を前提とします。namespace は `kafka`、クラスターは `my-cluster`、broker pod が3つ、controller pod が3つ、`orders` topic は12 partition です。node pool は pod に `docs.example.com/kafka-role: broker` または `controller` の label を付けます。Prometheus Operator と KEDA は事前にインストールしてください。

## クラスター仕様を置き換えずに JMX メトリクスを有効にする

次を `metrics-config.yaml` として保存します。この絞り込んだ rule は、replication gauge、broker の request-handler idle ratio、throughput／ISR counter を公開します。counter 名は `_total` で終わります。すでに計算済みの rate ではなく、counter に `rate()` を適用してください。

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

次を **`metrics.patch.yaml`** として保存します。これは既存の Kafka resource に適用する merge patch であり、新規作成／適用する完全な resource ではありません。既存の listener、認証、storage、その他の設定は保持されます。

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

最初のセクションはプロセス内の JMX agent を有効にします。2つ目は、`seglo/kafka-lag-exporter` とは実装もメトリクス名も異なる Strimzi の **Kafka Exporter** をデプロイします。旧プロジェクトはアーカイブ済みのため、この章では現在の既定として推奨しません。

Strimzi は内部 Kafka listener への exporter 接続と証明書情報を管理します。認証のない 9092 address に置き換えないでください。このリリースの exporter は、Kafka node の metrics endpoint と同じく、port **9404** を **`tcp-prometheus`** という名前で使います。Kafka Exporter は別の workload です。

`KafkaConnect` と `KafkaMirrorMaker2` には、それぞれ独自のメトリクス設定があります。Cruise Control は `Kafka.spec.cruiseControl` の下で設定します。単独の `CruiseControl` CRD ではありません。すべてのコンポーネントに Kafka MBean rule をそのまま流用しないでください。

## 対象 target を検出する

次を `podmonitors.yaml` として保存します。node と lag exporter の target は個別に選択します。relabeling によって、query に使う安定した `namespace`、`kafka_cluster`、`kafka_component` の属性を作り、Kafka node には `kafka_role` も付与します。

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

`release` label は Prometheus resource の PodMonitor／PrometheusRule selector と一致させる必要があります。namespace selector と RBAC でも `kafka` 内の resource を検出できるようにしてください。Prometheus から pod への NetworkPolicy と port アクセスも確認します。

Service が一致するよう正しく設定すれば、**ServiceMonitor も利用できます**。PodSet か StatefulSet かによって ServiceMonitor が機能するかは決まりません。ここでは PodMonitor を pod の直接検出に使いますが、仕組みとして本質的に信頼性が高いという意味ではありません。endpoint は一度だけ scrape してください。重複する検出経路を取り除き、統合ビューでは HA Prometheus replica の重複も除去します。

## メトリクスを状況に応じて読む

| この mapping のメトリクス | 意味 |
| --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 通常はゼロ。障害、lag、計画メンテナンス中に増える場合がある。継続時間と該当 partition を確認 |
| `kafka_server_replicamanager_underminisrpartitioncount` | 設定された最小 ISR を下回る partition。`acks=all` の書き込み可用性に関係 |
| `kafka_controller_kafkacontroller_activecontrollercount` | 1クラスターの controller pod 全体の合計は1に落ち着くはず。sample の網羅性、重複／古い scrape を確認 |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | 利用可能な leader がない partition。可用性を調査 |
| `kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent` | gauge ratio。通常は0～1。低値だけで決めつけず、CPU、GC、I/O、request latency と関連付ける |
| `kafka_server_brokertopicmetrics_bytesin_total` / `bytesout_total` | topic ごとの byte counter。throughput には `rate` を使う |
| `kafka_server_replicamanager_isrshrinks_total` / `isrexpands_total` | ISR 変更の counter。頻繁な変化を replication 状況と照合 |

controller の合計が1を超えるのは異常な**観測結果**ですが、それだけで split brain の証拠にはなりません。まずクラスターをまたぐ集計、target の重複、scrape のタイミング、古い sample を確認してください。sample がないことはゼロを意味しません。under-replication だけではデータ損失が起きたとも言えません。

topic ごとの ingest throughput:

```promql
sum by (namespace, kafka_cluster, topic) (
  rate(kafka_server_brokertopicmetrics_bytesin_total{
    namespace="kafka",kafka_cluster="my-cluster"
  }[5m])
)
```

topic 全体の通信量だけでは、どの partition が hot なのか分かりません。偏りを調査するときは、適切な範囲に絞った partition／client 別の観測を追加してください。ここで使う絞り込んだ mapping は、上流 dashboard のメトリクス一式ではありません。

## Consumer lag は commit 済み offset との差

通常、各 partition の lag は **log-end の次 offset から group の commit 済み次 offset を引いた値**です。これは offset の距離であり、常に業務レコードの件数と一致するわけではありません。compaction、offset の欠番、transaction が影響します。処理を永続化する前に commit すると、作業が終わっていなくても lag が正常に見えることがあります。

broker MBean の JMX mapping だけでは、この計測に必要な group／partition offset query は実行されません。Strimzi Kafka Exporter は `kafka_consumergroup_lag` を公開し、label に **`consumergroup`**、`topic`、`partition` を付けます。アーカイブ済み exporter の `kafka_consumergroup_group_lag` という名前を query したり、その `group` label がここでも使えると仮定したりしないでください。

```promql
sum by (namespace, kafka_cluster, consumergroup, topic) (
  kafka_consumergroup_lag{
    namespace="kafka",kafka_cluster="my-cluster",
    topic="orders",consumergroup="order-processor"
  } >= 0
)
```

この filter は backlog の合計から負値／不明な lag を除外しますが、データの欠落を隠してはいけません。exporter の稼働状態、想定 group の欠落、`kafka_consumergroup_current_offset < 0` を別々に監視してください。commit がない group、認証失敗、filter された topic では結果が欠ける場合があります。commit 済み offset に対する lag がゼロでも、end-to-end の処理 SLO を満たすとは限りません。

## alert ではデータ欠落も検出する

次を `alerts.yaml` として保存します。想定する Kafka node 6つと controller 3つは、この章の topology に対応しています。node pool を変更したら値を更新してください。group／topic の存在確認 alert は、`order-processor` が `orders` に commit する前提です。アプリケーションに合わせて対象範囲と起動時の猶予を調整してください。

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

しきい値と継続時間は開始時の目安です。`for` は alert を発火させる前に、条件が継続して true であることを要求します。scrape 間隔でも移動平均でもありません。`sum(metric) != 1` だけでは、メトリクス系列が完全に欠落した場合を**検出できません**。結果が空の vector になり得るためです。coverage と `absent()` の rule で別途扱います。

```bash
kubectl apply -f metrics-config.yaml
kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl apply -f podmonitors.yaml -f alerts.yaml
```

Kafka resource の観測済み generation／condition、実際の pod port、Prometheus の Targets／Rules ページを確認してください。設定変更によって workload の rollout が起きる場合があります。Alertmanager の routing／delivery は別に検証してください。PrometheusRule を作成しただけでは、運用担当者に通知が届いた証拠になりません。

## 認証付き KEDA query で consumer をスケールする

対象の `Deployment/order-consumer` は、すでに **namespace `kafka` 内**に存在し、パート 2 の TLS/SCRAM listener に接続し、consumer group `order-processor` としてレコードを処理している必要があります。そのアプリケーション認証情報は、以下の scaler が使う読み取り専用の metadata identity とは別です。ScaledObject と TriggerAuthentication も `kafka` に配置します。

次を `keda-auth.yaml` として保存します。username Secret に password は含めません。User Operator が password Secret を生成します。KEDA は TriggerAuthentication の参照先から username、password、CA を読み込みます。

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

次を `scaledobject.yaml` として保存します。TLS の hostname verification は有効のままにします。KEDA operator から broker endpoint に到達でき、参照先の Secret にアクセスできる必要があります。

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

`lagThreshold: "50"` は replica ごとの**実効 lag 合計の目標値**です。partition ごとに複数 consumer を作る個別のしきい値ではありません。既定の AverageValue target では、概算の必要数は `ceil(effective total lag / 50)` となり、scaler の調整、HPA tolerance、最小／最大 replica 数、stabilization の影響を受けます。従来型 consumer group では、consumer を増やしても1つの partition を複数 member が同時に consume できるようにはなりません。

`allowIdleConsumers=false` の場合、scaler は partition 数を考慮します。厳密に上限を守る必要があるときは、利用可能な partition 数を超えない `maxReplicaCount` を明示してください。この例ではパート 2 の topic が12 partition なので、上限を10にしています。partition 数が異なる topic や workload では、値を見直してください。

`minReplicaCount=1` のため、この例は**ゼロにはスケールしません**。`activationLagThreshold` と KEDA のゼロスケール用 `cooldownPeriod` は、1↔N の動作を制御しません。HPA の scale-down stabilization は明示的に設定します。後からゼロスケールを有効にする場合は、新規 group／commit 欠落、offset reset policy、起動と activation をテストしてください。不明な offset を空 queue とみなさないでください。

```bash
kubectl apply -f keda-auth.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/keda-lag-reader
kubectl apply -f scaledobject.yaml
kubectl -n kafka get scaledobject order-consumer-scaler -o yaml
kubectl -n kafka get hpa
```

制限を変える前に、scaler の error、HPA の現在値／目標値、実際の consumer throughput を比較してください。一般的な autoscaling の動作は、既存の [KEDA ガイド](../../autoscaling/01-keda.md)で説明しています。

## Dashboard と検証

version 固定の上流 **Kafka、KRaft、Kafka Exporter、Connect、Cruise Control** dashboard を参照し、選んだ exporter type と label mapping に合わせてください。Strimzi 1.3 の dashboard 一式は、ZooKeeper 構成の導入手順ではありません。dashboard をインポートしても、この絞り込んだ mapping に query 対象のメトリクスが存在するとは限りません。

JVM／GC、node／PVC の容量と I/O、replication の可用性、scrape coverage、traffic 分布、group の処理状況、アプリケーション latency／error SLO を含めます。プロセス内 exporter は JVM メトリクスも公開しますが、host／PVC とアプリケーションの signal は各対応 collector から取得します。

最終版の JMX rule と Kafka Exporter (1.9.0) の例は、分離したローカル Kafka 4.3.1 broker で実行しました。15件の record と commit 済み offset に対し、partition lag は **3、5、5** となりました。9つの alert rule を、正常系、データ欠落、障害、クラスター間分離のシナリオでテストしました。これらのテストだけでは、本番の TLS 接続、複数 node の quorum 動作、Strimzi reconciliation、通知配信、実 workload に対する KEDA の動作は証明できません。

- [Strimzi 1.3.0 の metrics 例](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/examples/metrics/kafka-metrics.yaml)
- [Strimzi 1.3.0 Kafka Exporter の実装](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/cluster-operator/src/main/java/io/strimzi/operator/cluster/model/KafkaExporter.java)
- [Strimzi 1.3.0 に同梱された exporter のバージョン](https://github.com/strimzi/strimzi-kafka-operator/blob/1.3.0/docker-images/kafka-based/kafka/Dockerfile)
- [Kafka Exporter 1.10.0](https://github.com/danielqsj/kafka_exporter/tree/v1.10.0)
- [アーカイブ済み kafka-lag-exporter project](https://github.com/seglo/kafka-lag-exporter)
- [KEDA 2.21 Kafka scaler](https://keda.sh/docs/2.21/scalers/apache-kafka/)
- [KEDA 2.21.0 の実装](https://github.com/kedacore/keda/blob/v2.21.0/pkg/scalers/kafka_scaler.go)
- [Prometheus alert rule](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [version 固定の JMX ベース Grafana dashboard](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/grafana-dashboards)
- [version 固定の Strimzi Metrics Reporter dashboard](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/examples/metrics/strimzi-metrics-reporter/grafana-dashboards)

## 次のステップ

[パート 8: ベストプラクティス](./08-best-practices.md)

[メインページに戻る](./README.md)

## クイズ

[トピッククイズ](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
