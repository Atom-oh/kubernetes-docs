# Part 7: 모니터링

> **지원 버전**: Strimzi 0.45+, Prometheus Operator, KEDA 2.x\
> **마지막 업데이트**: 2026년 7월 9일

Kafka 클러스터는 브로커 힙, 디스크, 네트워크뿐 아니라 파티션 복제 상태와 컨슈머 처리 속도까지 함께 살펴봐야 장애를 조기에 발견할 수 있습니다. 이 문서에서는 Strimzi가 노출하는 브로커 메트릭을 Prometheus로 수집하고, 컨슈머 랙을 별도로 측정하며, KEDA로 컨슈머를 오토스케일링하는 방법을 다룹니다.

## 1. Strimzi의 메트릭 노출 방식

Strimzi는 브로커/컨트롤러/Connect 등 각 컴포넌트 컨테이너 내부에서 Prometheus JMX Exporter를 별도 컨테이너(사이드카)가 아니라 **JVM Java 에이전트**로 함께 실행합니다. JMX Exporter는 JVM 내부의 JMX MBean(예: `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions`)을 읽어 이를 Prometheus 텍스트 포맷의 `/metrics` HTTP 엔드포인트로 변환합니다. 어떤 MBean을 어떤 이름/레이블로 변환할지는 relabeling 규칙이 담긴 `ConfigMap`으로 정의하며, `Kafka` CR의 `metricsConfig` 필드가 이 `ConfigMap`을 참조합니다.

Strimzi 공식 리포지토리의 [`examples/metrics`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics) 디렉터리에 브로커/Connect/Cruise Control 등에 대한 예제 JMX Exporter 설정이 포함되어 있으므로, 직접 relabeling 규칙을 처음부터 작성하기보다는 이를 기반으로 필요한 항목만 조정하는 것이 일반적입니다.

```yaml
# kafka-metrics-config.yaml (일부, Strimzi 예제 기반)
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
      # 파티션 언더 리플리케이트 카운트
      - pattern: "kafka.server<type=ReplicaManager, name=UnderReplicatedPartitions><>Value"
        name: "kafka_server_replicamanager_underreplicatedpartitions"
      # 액티브 컨트롤러 카운트 (KRaft)
      - pattern: "kafka.controller<type=KafkaController, name=ActiveControllerCount><>Value"
        name: "kafka_controller_kafkacontroller_activecontrollercount"
      # 리퀘스트 핸들러 유휴율
      - pattern: "kafka.server<type=KafkaRequestHandlerPool, name=RequestHandlerAvgIdlePercent><>OneMinuteRate"
        name: "kafka_server_kafkarequesthandlerpool_requesthandleravgidlepercent_oneminuterate"
      # 토픽별 바이트 인/아웃
      - pattern: "kafka.server<type=BrokerTopicMetrics, name=(BytesInPerSec|BytesOutPerSec), topic=(.+)><>OneMinuteRate"
        name: "kafka_server_brokertopicmetrics_$1_oneminuterate"
        labels:
          topic: "$2"
```

```yaml
# Kafka CR에서 metricsConfig로 위 ConfigMap 참조
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

`metricsConfig`를 적용하면 Strimzi가 각 브로커 컨테이너에 JMX Exporter Java 에이전트를 자동으로 활성화하고, 지정한 `ConfigMap`의 규칙 파일을 해당 컨테이너에 마운트합니다. 이후 브로커 Pod의 `9404` 포트(기본값)에서 Prometheus 텍스트 포맷 메트릭을 `/metrics` 경로로 스크레이핑할 수 있습니다. `KafkaConnect`, `KafkaMirrorMaker2`, `CruiseControl` 등 다른 CR에도 동일한 방식으로 `metricsConfig`를 지정할 수 있습니다.

## 2. 핵심 브로커 메트릭

메트릭이 많아지기 쉬운 만큼, 운영 중 가장 먼저 확인해야 할 지표를 좁혀서 이해하는 것이 중요합니다.

| 메트릭 | 의미 | 정상 값 / 확인 포인트 |
| --- | --- | --- |
| `kafka_server_replicamanager_underreplicatedpartitions` | 리더가 보유한 파티션 중 ISR(In-Sync Replica) 수가 replication factor보다 적은 파티션 수 | **0이어야 함.** 0보다 크면 팔로워가 리더를 따라가지 못하고 있다는 뜻으로, 네트워크 지연, 브로커 과부하, 디스크 I/O 병목 등을 의심해야 합니다. |
| `kafka_controller_kafkacontroller_activecontrollercount` | 해당 브로커/컨트롤러가 현재 액티브 컨트롤러인지 여부(0 또는 1) | 클러스터 전체 합계가 **정확히 1**이어야 합니다. 0이면 컨트롤러 부재(리더 선출 중 또는 장애), 2 이상이면 스플릿 브레인 가능성이 있어 즉시 조사해야 합니다. |
| Request Handler Idle Ratio (`...requesthandleravgidlepercent...`) | 브로커의 리퀘스트 처리 스레드 풀이 유휴 상태인 시간 비율 | 값이 낮아질수록(예: 20% 미만) 브로커가 CPU/스레드 부족으로 포화 상태에 가까워지고 있다는 신호입니다. 지속적으로 낮으면 브로커 스케일 아웃이나 파티션 재분배를 검토합니다. |
| `kafka_server_brokertopicmetrics_bytesinpersec_oneminuterate` / `bytesoutpersec` | 토픽별 초당 프로듀스/컨슘 바이트 처리량 | 브로커/네트워크 용량 계획, 특정 토픽의 트래픽 급증(hot partition) 탐지에 사용합니다. |
| ISR Shrink/Expand Rate (`kafka_server_replicamanager_isrshrinkspersec`, `isrexpandspersec`) | 초당 ISR에서 리플리카가 빠지거나(shrink) 다시 들어오는(expand) 빈도 | shrink가 자주 발생하면 팔로워가 반복적으로 ISR을 이탈하고 있다는 뜻이며, 언더 리플리케이트 파티션의 선행 지표로 볼 수 있습니다. |

이 중 **언더 리플리케이트 파티션 수**와 **액티브 컨트롤러 카운트**는 클러스터의 데이터 안전성과 가용성을 가장 직접적으로 보여주는 지표이므로, 대시보드 상단과 알림 규칙에 항상 포함해야 합니다.

```promql
# 클러스터 전체 액티브 컨트롤러 합계 (정상: 1)
sum(kafka_controller_kafkacontroller_activecontrollercount)

# 언더 리플리케이트 파티션이 존재하는 브로커
kafka_server_replicamanager_underreplicatedpartitions > 0
```

## 3. 컨슈머 랙 모니터링

**컨슈머 랙(Consumer Lag)** 은 파티션별로 "가장 최근에 프로듀스된 오프셋(log end offset)"과 "컨슈머 그룹이 마지막으로 커밋한 오프셋"의 차이입니다. 랙이 지속적으로 증가한다는 것은 컨슈머가 프로듀스 속도를 따라가지 못하고 있다는 뜻이며, 처리 지연, 컨슈머 장애, 파티션 리밸런싱 반복 등의 신호일 수 있습니다.

Strimzi가 JMX Exporter Java 에이전트로 노출하는 메트릭은 **브로커 자체의 상태**(위 2번 항목들)를 다루며, 기본적으로 컨슈머 그룹의 오프셋/랙은 포함하지 않습니다. 컨슈머 랙은 브로커가 아니라 `__consumer_offsets` 토픽과 각 토픽의 최신 오프셋을 함께 조회해야 계산할 수 있기 때문에, 보통 별도의 Exporter를 추가로 배포합니다.

가장 널리 쓰이는 방식은 커뮤니티 프로젝트인 [`kafka-lag-exporter`](https://github.com/seglo/kafka-lag-exporter)(또는 유사한 Burrow 계열 exporter)를 클러스터 내 별도 `Deployment`로 실행하는 것입니다. 이 Exporter는 Kafka Admin API를 통해 주기적으로 컨슈머 그룹의 커밋 오프셋과 토픽의 최신 오프셋을 조회하여 `kafka_consumergroup_group_lag`(그룹·토픽·파티션별 랙)와 같은 메트릭을 Prometheus 포맷으로 노출합니다.

```yaml
# kafka-lag-exporter를 위한 최소 ConfigMap 예시
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

이 Exporter를 배포한 뒤 Prometheus가 해당 `/metrics` 엔드포인트를 스크레이핑하도록 설정하면 다음과 같은 쿼리로 랙을 확인할 수 있습니다.

```promql
# 컨슈머 그룹별 총 랙 (파티션 합산)
sum by (group, topic) (kafka_consumergroup_group_lag)

# 랙이 1000을 초과하는 그룹·토픽 조합
sum by (group, topic) (kafka_consumergroup_group_lag) > 1000
```

## 4. ServiceMonitor / PodMonitor로 스크레이핑 연동

Prometheus Operator를 사용하는 환경(kube-prometheus-stack 등)에서는 브로커 Pod의 `/metrics` 엔드포인트를 수동으로 `scrape_configs`에 추가하는 대신, `PodMonitor` CRD로 라벨 기반 자동 디스커버리를 구성하는 것이 일반적입니다. 브로커는 `StatefulSet`이 아니라 Strimzi가 관리하는 Pod이므로, 고정된 `Service`보다는 `PodMonitor`로 Pod 라벨을 직접 셀렉트하는 방식이 더 안정적으로 동작합니다.

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

메트릭이 수집되면 언더 리플리케이트 파티션에 대해 알림을 걸어 두는 것이 가장 기본적인 안전장치입니다. 아래 `PrometheusRule`은 언더 리플리케이트 파티션이 0보다 큰 상태가 5분 이상 지속되면 알림을 발생시킵니다.

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
            summary: "Kafka 클러스터에 언더 리플리케이트 파티션 존재"
            description: "5분 이상 언더 리플리케이트 파티션이 0보다 큽니다. 팔로워 브로커의 지연/장애 여부를 확인하세요."
        - alert: KafkaNoActiveController
          expr: sum(kafka_controller_kafkacontroller_activecontrollercount) != 1
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "Kafka 액티브 컨트롤러 수 비정상"
            description: "클러스터 전체 액티브 컨트롤러 합계가 1이 아닙니다(현재 값 확인 필요). 컨트롤러 리더 선출 상태를 점검하세요."
```

## 5. KEDA를 사용한 컨슈머 기반 오토스케일링

CPU/메모리 기반 HPA는 컨슈머 워크로드의 실제 부하(처리해야 할 메시지 양)를 반영하지 못하는 경우가 많습니다. KEDA는 Kafka 스케일러(`triggers.type: kafka`)를 통해 **컨슈머 그룹 랙**을 기준으로 컨슈머 `Deployment`를 스케일링할 수 있게 해줍니다. KEDA는 내부적으로 Kafka Admin API를 사용해 지정한 토픽/컨슈머 그룹의 랙을 직접 조회하므로, 3번에서 다룬 별도의 랙 Exporter 없이도 스케일링 판단이 가능합니다(다만 대시보드/알림용 랙 시각화에는 여전히 Exporter가 유용합니다).

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

주요 트리거 파라미터:

* **`bootstrapServers`**: 랙을 조회할 Kafka 클러스터의 부트스트랩 주소
* **`consumerGroup`**, **`topic`**: 랙을 측정할 대상 컨슈머 그룹과 토픽
* **`lagThreshold`**: 파티션당 랙이 이 값을 넘으면 레플리카를 추가로 늘리는 기준값 (예: 파티션당 랙 50마다 레플리카 1개 추가하는 방식으로 동작)
* **`activationLagThreshold`**: 0에서 1로(즉 최초 스케일 업) 전환되기 위한 최소 랙 기준. 지정하지 않으면 랙이 조금만 생겨도 즉시 1개로 스케일 업합니다.
* **`allowIdleConsumers`**: `false`(기본값)이면 KEDA가 파티션 수를 넘어서는 레플리카를 만들지 않도록 제한합니다.

이 `ScaledObject`가 적용되면 KEDA Operator가 내부적으로 표준 Kubernetes HPA를 생성/관리하며, 랙이 줄어들면 `cooldownPeriod` 이후 자동으로 스케일 인합니다. KEDA의 스케일러 종류, 아키텍처, Zero Scaling 등 일반적인 개념은 [오토스케일링: KEDA](../../autoscaling/01-keda.md) 문서에서 더 자세히 다루므로 함께 참고하세요.

## 6. Grafana 대시보드

Strimzi는 공식 리포지토리의 [`examples/metrics/grafana-dashboards`](https://github.com/strimzi/strimzi-kafka-operator/tree/main/examples/metrics/grafana-dashboards) 디렉터리에 브로커, ZooKeeper(레거시), Kafka Connect, Cruise Control용 예제 Grafana 대시보드 JSON을 제공합니다. 직접 패널을 처음부터 구성하기보다 이 예제를 Import한 뒤 클러스터 이름/네임스페이스 레이블에 맞게 변수를 조정하는 방식이 가장 빠릅니다.

좋은 Kafka 대시보드가 최소한 포함해야 할 패널 그룹:

* **브로커 헬스**: 브로커별 업타임, JVM 힙 사용률, GC 정지 시간, Request Handler/Network Idle Ratio
* **ISR/복제 상태**: 언더 리플리케이트 파티션 수, ISR Shrink/Expand Rate, 액티브 컨트롤러 카운트(클러스터 전체 합계)
* **처리량**: 토픽별/브로커별 초당 Bytes In/Out, 초당 메시지 수, 파티션당 처리량 불균형(핫 파티션 탐지)
* **컨슈머 랙**: 컨슈머 그룹별 랙 추이, 랙 급증 시점과 리밸런싱 이벤트의 상관관계

## 다음 단계

메트릭 수집, 알림, 오토스케일링까지 구성했다면 이제 이를 실제 운영 기준(SLO, 용량 계획, 장애 대응 절차)에 반영해야 합니다. 이는 [Part 8: 모범 사례](./08-best-practices.md)에서 다룹니다.

[메인 페이지로 돌아가기](./)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/07-monitoring-quiz.md)를 풀어보세요.
