# Part 7: 모니터링

> **검토 기준**: Strimzi 1.2.0 / Kafka 4.3.1, 포함된 JMX Exporter 1.6.0·Kafka Exporter 1.9.0, Prometheus Operator 0.93.1, KEDA 2.20.2\
> **최종 검토**: 2026년 9월 12일

## 각 구성요소의 관찰 대상

| 구성요소 | 역할 |
| --- | --- |
| JMX Prometheus Exporter | 같은 JVM의 MBean을 Java agent로 읽어 Prometheus 메트릭으로 변환 |
| Strimzi Metrics Reporter | 별도로 지원되는 metricsConfig.type; 자체 설정·이름으로 Kafka 메트릭 직접 노출 |
| Kafka Exporter | Kafka API로 컨슈머 그룹 오프셋·랙과 토픽 정보 조회 |
| Prometheus / Prometheus Operator | 대상 탐색·수집, 규칙 평가와 Alertmanager 전달 |
| KEDA Kafka scaler | Kafka API를 직접 조회해 스케일링; lag exporter의 Prometheus endpoint 불필요 |

이 장은 **`jmxPrometheusExporter`**를 선택합니다. MBean 변환 규칙과 Prometheus의
대상 relabeling은 다른 단계입니다. `strimziMetricsReporter`도 지원되므로 JMX가
유일한 방법이라는 설명은 틀립니다. exporter 종류를 바꾸면 이름과 대시보드도 검토합니다.

[Part 2](./02-strimzi-operator.md)의 `kafka` 네임스페이스, `my-cluster`,
브로커 3개·컨트롤러 3개 Pod와 12개 파티션인 `orders` 토픽을 전제로 합니다.
노드 풀은 Pod에 `docs.example.com/kafka-role: broker` 또는 `controller`
라벨을 붙입니다. Prometheus Operator와 KEDA는 이미 설치되어 있어야 합니다.

## 기존 클러스터 설정을 보존하며 JMX 활성화

다음을 `metrics-config.yaml`로 저장합니다. 필요한 복제 gauge, 브로커 request
handler 유휴율과 처리량·ISR counter만 매핑합니다. `_total`은 counter이므로
처리량에는 `rate()`를 사용하며 이미 계산된 rate에 다시 적용하지 않습니다.

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

다음은 **`metrics.patch.yaml`**입니다. 기존 Kafka에 적용하는 merge patch이며
완전한 생성·apply용 리소스가 아닙니다. 기존 listener·인증·스토리지 등의 설정을
유지합니다.

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

첫 부분은 JVM 내부 JMX agent를 켜고 둘째는 Strimzi의 **Kafka Exporter**를
배포합니다. `seglo/kafka-lag-exporter`와 구현·메트릭 이름이 다릅니다. 그 프로젝트는
보관 처리되어 있으므로 현재의 기본 선택지로 권장하지 않습니다.

Strimzi가 내부 Kafka listener용 exporter 연결·인증서를 관리하므로 인증 없는
9092 주소로 바꾸지 않습니다. 이 릴리스의 exporter는 Kafka 노드 메트릭과 같은
**9404**, **`tcp-prometheus`** 포트 이름을 사용하며 별도 워크로드로 실행됩니다.

`KafkaConnect`와 `KafkaMirrorMaker2`에는 각자의 메트릭 설정이 있습니다.
Cruise Control은 `Kafka.spec.cruiseControl`에서 구성하며 독립적인 `CruiseControl`
CRD가 아닙니다. Kafka MBean 규칙을 모든 구성요소에 그대로 적용하지 않습니다.

## 의도한 대상만 탐색

`podmonitors.yaml`로 저장합니다. Kafka 노드와 lag exporter를 따로 선택하고
relabeling으로 `namespace`, `kafka_cluster`, `kafka_component`, 노드의 경우
`kafka_role`을 붙여 쿼리의 범위를 구분합니다.

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

`release` 라벨은 실제 Prometheus의 PodMonitor·PrometheusRule selector와
맞춰야 합니다. namespace selector와 RBAC도 `kafka` 리소스를 발견할 수 있어야
하며 Prometheus에서 Pod 포트로의 접근과 NetworkPolicy를 확인합니다.

알맞은 Service를 선택하는 **ServiceMonitor도 동작합니다**. PodSet·StatefulSet
여부가 그 가능성을 결정하지 않습니다. 여기서 PodMonitor는 직접 Pod를 찾는
선택이며 본질적으로 더 안정적인 프로토콜은 아닙니다. 같은 endpoint를 중복 수집하지
말고 통합 조회 시 HA Prometheus replica도 중복 제거한 뒤 합산합니다.

## 메트릭의 의미와 범위

| 이 매핑의 메트릭 | 해석 |
| --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 정상 상태는 0; 장애·지연·계획된 작업 중 증가 가능하므로 지속 시간과 대상 확인 |
| `kafka_server_replicamanager_underminisrpartitioncount` | min ISR 미만인 파티션; acks=all 쓰기 가용성에 중요 |
| `kafka_controller_kafkacontroller_activecontrollercount` | 한 클러스터의 컨트롤러 Pod 합계가 안정 상태에서 1; 누락·중복·오래된 수집 확인 |
| `kafka_controller_kafkacontroller_offlinepartitionscount` | 사용 가능한 리더가 없는 파티션; 가용성 조사 |
| `kafka_server_kafkarequesthandlerpool_brokerrequesthandleravgidle_percent` | 보통 0~1의 gauge 비율; CPU·GC·I/O·요청 지연과 함께 해석 |
| `kafka_server_brokertopicmetrics_bytesin_total` / `bytesout_total` | 토픽별 바이트 counter; rate로 처리량 계산 |
| `kafka_server_replicamanager_isrshrinks_total` / `isrexpands_total` | ISR 변화 counter; 복제 상태와 함께 이탈·복귀 반복 관찰 |

컨트롤러 합계가 1보다 크면 **관찰값이 비정상**인 것이지 곧바로 split brain의
증거는 아닙니다. 여러 클러스터 합산, 중복 대상, 수집 시점과 오래된 표본부터
확인합니다. 데이터 없음은 0이 아니며 under-replication 자체가 이미 데이터 손실이
발생했다는 뜻도 아닙니다.

토픽별 입력 처리량:

```promql
sum by (namespace, kafka_cluster, topic) (
  rate(kafka_server_brokertopicmetrics_bytesin_total{
    namespace="kafka",kafka_cluster="my-cluster"
  }[5m])
)
```

토픽 합계만으로 어떤 파티션이 hot한지 알 수는 없습니다. 편중을 조사할 때는
필요한 파티션·클라이언트 관찰을 추가합니다. 이 매핑은 upstream 대시보드의
모든 메트릭을 포함한 구성이 아닙니다.

## 컨슈머 랙은 커밋 오프셋의 거리

파티션별 랙은 보통 **log end의 다음 오프셋 − 그룹이 커밋한 다음 오프셋**입니다.
이는 오프셋 거리이며 항상 업무 레코드 개수와 같지는 않습니다. compaction,
오프셋 공백과 트랜잭션의 영향을 받습니다. 처리가 끝나기 전에 커밋하면 미완료 작업이
있어도 랙은 정상처럼 보일 수 있습니다.

브로커 MBean을 변환하는 JMX 설정만으로 그룹·파티션 오프셋 조회가 수행되지는
않습니다. Strimzi Kafka Exporter의 이름은 `kafka_consumergroup_lag`, 라벨은
**`consumergroup`**, `topic`, `partition`입니다. 기존 exporter의
`kafka_consumergroup_group_lag`나 `group` 라벨을 그대로 사용하지 않습니다.

```promql
sum by (namespace, kafka_cluster, consumergroup, topic) (
  kafka_consumergroup_lag{
    namespace="kafka",kafka_cluster="my-cluster",
    topic="orders",consumergroup="order-processor"
  } >= 0
)
```

필터는 음수·알 수 없는 랙을 합계에서 제외하지만 수집 불능을 숨겨서는 안 됩니다.
exporter 상태, 예상 그룹 누락과 `kafka_consumergroup_current_offset < 0`을
별도로 감시합니다. 커밋 없는 그룹, 인증 실패나 필터에 제외된 토픽은 결과 누락을
만들 수 있습니다. 커밋 랙 0이 전체 처리 경로의 SLO를 보장하지는 않습니다.

## 결측도 감지하는 알람

`alerts.yaml`로 저장합니다. 예상 노드 6개·컨트롤러 3개는 본문의 구성에 맞춘
값이므로 노드 풀을 바꾸면 함께 갱신합니다. 그룹 알람은 `order-processor`가
`orders`를 소비·커밋해야 한다는 전제이며 실제 범위와 시작 유예 시간을 조정합니다.

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

임계값과 기간은 시작 예제입니다. `for`는 조건이 지속적으로 존재하고 참이어야
firing으로 바뀌게 하며 수집 주기나 이동 평균이 아닙니다. `sum(metric) != 1`만으로
메트릭 전체 누락을 감지하지 못합니다. 빈 벡터가 될 수 있으므로 별도의 수집 범위와
`absent()` 규칙으로 처리합니다.

```bash
kubectl apply -f metrics-config.yaml
kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml
kubectl -n kafka get kafka my-cluster -o yaml
kubectl apply -f podmonitors.yaml -f alerts.yaml
```

Kafka의 observed generation·conditions, 실제 Pod 포트와 Prometheus Targets·Rules를
확인합니다. 설정 변경으로 워크로드가 롤링될 수 있습니다. Alertmanager의 경로·전달도
별도로 검증합니다. PrometheusRule 생성만으로 알림이 운영자에게 도착했다고 볼 수 없습니다.

## 인증된 KEDA 조회로 컨슈머 확장

대상 `Deployment/order-consumer`는 **`kafka` 네임스페이스**에 이미 존재하고
Part 2의 TLS/SCRAM listener를 사용하여 `order-processor` 그룹으로 소비해야 합니다.
애플리케이션 사용자와 아래 scaler의 읽기 전용 metadata 사용자는 별개입니다.
ScaledObject·TriggerAuthentication도 `kafka`에 둡니다.

`keda-auth.yaml`로 저장합니다. username Secret에는 비밀번호가 없으며 User
Operator가 비밀번호 Secret을 만듭니다. KEDA는 TriggerAuthentication 참조로
사용자명·비밀번호·CA를 읽습니다.

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

`scaledobject.yaml`로 저장합니다. TLS 호스트 이름 검증을 유지합니다. KEDA
Operator가 브로커에 접근하고 참조한 Secret을 읽을 수 있어야 합니다.

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

`lagThreshold: "50"`은 파티션마다 컨슈머를 여러 개 만드는 기준이 아니라
**레플리카당 유효한 총 랙의 목표**입니다. 기본 AverageValue에서는 대략
`ceil(유효한 총 랙 / 50)`을 요구하며 scaler의 조정, HPA tolerance, 최소·최대 수와
안정화 정책이 반영됩니다. 컨슈머를 늘려도 일반적인 같은 컨슈머 그룹의 여러 멤버가
하나의 파티션을 동시에 나눠 소비하지는 않습니다.

`allowIdleConsumers=false`는 파티션 수를 고려하게 합니다. 엄격한 상한이 필요하면
실제 파티션 수 이하로 `maxReplicaCount`를 지정합니다. 본문은 Part 2의 파티션
12개에 대해 최대 10개이며 다른 토픽·워크로드는 실제 파티션 수에 맞게 검토합니다.

`minReplicaCount=1`이므로 이 예제는 **0으로 축소하지 않습니다**.
`activationLagThreshold`와 0 축소용 `cooldownPeriod`는 여기의 1↔N 동작을
제어하는 설정이 아닙니다. HPA scale-down 안정화 시간을 명시했습니다.
나중에 0 축소를 켜면 새 그룹·미커밋 상태, offset-reset 정책, 시작과 activation을
검증하며 알 수 없는 오프셋을 빈 큐로 간주하지 않습니다.

```bash
kubectl apply -f keda-auth.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/keda-lag-reader
kubectl apply -f scaledobject.yaml
kubectl -n kafka get scaledobject order-consumer-scaler -o yaml
kubectl -n kafka get hpa
```

제한을 바꾸기 전에 scaler 오류, HPA의 현재·목표 지표와 실제 처리량을 비교합니다.
일반 동작은 [KEDA 문서](../../autoscaling/01-keda.md)를 함께 참고합니다.

## 대시보드와 검증 범위

버전을 고정한 upstream **Kafka·KRaft·Kafka Exporter·Connect·Cruise Control**
대시보드를 선택한 exporter 종류·라벨에 맞춰 참고합니다. Strimzi 1.2 예제는
ZooKeeper 배포 안내가 아닙니다. Import했다고 이 최소 매핑에 모든 쿼리가 존재하지는 않습니다.

JVM·GC, 노드/PVC 용량·I/O, 복제 가용성, 수집 범위, 트래픽 편중, 그룹 진행과
애플리케이션 지연·오류 SLO를 포함합니다. JVM 내 exporter는 JVM 메트릭도 제공하지만
호스트/PVC와 애플리케이션 신호는 각각의 수집기에서 가져옵니다.

최종 JMX 규칙과 Kafka Exporter를 격리된 로컬 Kafka 4.3.1에서 검증했습니다.
레코드 15개와 지정한 커밋 위치에 대해 파티션 랙 **3·5·5**를 확인했습니다.
알람 9개는 정상·결측·실패와 다른 클러스터의 지표가 섞이는 상황으로 검사했습니다.
이는 운영 TLS 접속, 다중 노드 quorum, Strimzi 조정, 알림 전달과 실제 워크로드에
대한 KEDA 동작의 성공을 의미하지 않습니다.

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

## 다음 단계

[Part 8: 모범 사례](./08-best-practices.md)

[메인 페이지로 돌아가기](./README.md)

## 퀴즈

[주제 퀴즈](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)
