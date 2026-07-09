# Part 7: 모니터링 퀴즈

이 퀴즈는 Strimzi의 메트릭 노출 방식, 핵심 브로커 메트릭의 의미, 컨슈머 랙 측정 방법, KEDA Kafka 스케일러 설정에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Strimzi가 브로커의 JMX 메트릭을 Prometheus가 스크레이핑할 수 있는 형태로 변환하기 위해 브로커 컨테이너 내부에서 함께 실행하는 것은 무엇인가요?
   - A) Fluent Bit 사이드카
   - B) Prometheus JMX Exporter (JVM Java 에이전트)
   - C) OpenTelemetry Collector 데몬셋
   - D) cAdvisor

<details>

<summary>정답 보기</summary>

**정답: B) Prometheus JMX Exporter (JVM Java 에이전트)**

**설명:**
Strimzi는 `Kafka` CR의 `metricsConfig`가 설정되면 각 브로커(및 Connect 등) 컨테이너에서 Prometheus JMX Exporter를 **별도 사이드카 컨테이너가 아니라 동일 JVM 프로세스에 로드되는 Java 에이전트**로 자동 활성화합니다. 이 Exporter는 JVM 내부의 JMX MBean 값을 읽어 relabeling 규칙에 따라 이름을 변환한 뒤, `/metrics` HTTP 엔드포인트에서 Prometheus 텍스트 포맷으로 노출합니다. Fluent Bit는 로그 수집기, cAdvisor는 컨테이너 리소스 메트릭 수집기로 이 용도와 다릅니다.
</details>

2. `Kafka.spec.kafka.metricsConfig`는 어떤 리소스를 참조하여 JMX Exporter의 relabeling 규칙을 가져오나요?
   - A) Secret
   - B) PersistentVolumeClaim
   - C) ConfigMap
   - D) CustomResourceDefinition

<details>

<summary>정답 보기</summary>

**정답: C) ConfigMap**

**설명:**
`metricsConfig.valueFrom.configMapKeyRef`는 relabeling 규칙(YAML)이 담긴 `ConfigMap`의 이름과 키를 지정합니다. Strimzi는 이 규칙 파일을 JMX Exporter Java 에이전트가 실행되는 컨테이너에 마운트하여 어떤 JMX MBean을 어떤 Prometheus 메트릭 이름/레이블로 변환할지 결정합니다. Secret은 인증서나 자격 증명처럼 민감한 값을 다루는 용도이므로 이 목적에는 사용되지 않습니다.
</details>

3. `kafka_server_replicamanager_underreplicatedpartitions` 메트릭의 정상적인 값은 무엇인가요?
   - A) 브로커 수와 동일해야 함
   - B) 파티션 수와 동일해야 함
   - C) 항상 0이어야 함
   - D) 항상 1이어야 함

<details>

<summary>정답 보기</summary>

**정답: C) 항상 0이어야 함**

**설명:**
이 메트릭은 해당 브로커가 리더를 맡고 있는 파티션 중 ISR(In-Sync Replica) 개수가 replication factor보다 적은 파티션의 수를 나타냅니다. 정상 운영 중에는 모든 팔로워가 리더를 따라가고 있어야 하므로 이 값은 0이어야 합니다. 0보다 크면 네트워크 지연, 브로커 과부하, 디스크 I/O 병목 등으로 일부 리플리카가 뒤처지고 있다는 신호이며, 데이터 손실 위험(리더 장애 시 ISR이 부족하면 unclean leader election 위험)과 직결됩니다.
</details>

4. `kafka_controller_kafkacontroller_activecontrollercount` 메트릭을 클러스터 전체에서 합산했을 때 정상 값은 얼마여야 하나요?
   - A) 0
   - B) 브로커 수만큼
   - C) 정확히 1
   - D) 컨트롤러 후보 수만큼

<details>
<summary>정답 보기</summary>

**정답: C) 정확히 1**

**설명:**
각 브로커/컨트롤러는 자신이 액티브 컨트롤러인지 여부를 0 또는 1로 노출하므로, 클러스터 전체에서 이 값을 합산(`sum()`)하면 정상 상태에서는 정확히 1이어야 합니다. 합계가 0이면 액티브 컨트롤러가 없는 상태(리더 선출 중 또는 장애)이고, 2 이상이면 스플릿 브레인 같은 심각한 이상 상태를 의심해야 합니다.
</details>

5. Request Handler Idle Ratio 값이 지속적으로 낮게(예: 10% 미만) 유지될 때 가장 먼저 의심해야 할 상황은 무엇인가요?
   - A) 디스크 용량이 부족함
   - B) 브로커가 CPU/스레드 리소스 부족으로 포화 상태에 가까움
   - C) ZooKeeper 연결이 끊어짐
   - D) 컨슈머 그룹이 리밸런싱 중임

<details>
<summary>정답 보기</summary>

**정답: B) 브로커가 CPU/스레드 리소스 부족으로 포화 상태에 가까움**

**설명:**
Request Handler Idle Ratio는 브로커의 리퀘스트 처리 스레드 풀이 유휴 상태로 대기하는 시간의 비율입니다. 이 값이 낮다는 것은 스레드 풀이 계속 요청을 처리하느라 바쁘다는 뜻으로, 브로커가 CPU 또는 스레드 자원 한계에 가까워지고 있다는 신호입니다. 지속적으로 낮으면 브로커 스케일 아웃, 파티션 재분배, 또는 스레드 풀 크기 조정을 검토해야 합니다.
</details>

6. Strimzi가 기본으로 제공하는 브로커 메트릭에 컨슈머 그룹의 랙(lag)이 포함되지 않는 이유는 무엇인가요?
   - A) 컨슈머 랙은 보안상 노출할 수 없는 정보이기 때문
   - B) 랙 계산에는 컨슈머 그룹의 커밋 오프셋과 토픽의 최신 오프셋을 함께 조회해야 하는데, JMX Exporter는 브로커 자체 JMX MBean만 읽기 때문
   - C) Strimzi 버전이 오래되어 지원하지 않기 때문
   - D) 컨슈머 랙은 클라이언트에서만 측정 가능하기 때문

<details>
<summary>정답 보기</summary>

**정답: B) 랙 계산에는 컨슈머 그룹의 커밋 오프셋과 토픽의 최신 오프셋을 함께 조회해야 하는데, JMX Exporter는 브로커 자체 JMX MBean만 읽기 때문**

**설명:**
JMX Exporter Java 에이전트는 브로커 프로세스 내부의 JMX MBean(리플리케이션 상태, 처리량, 컨트롤러 상태 등)만 읽어 노출합니다. 컨슈머 랙은 컨슈머 그룹이 마지막으로 커밋한 오프셋과 토픽의 최신(log end) 오프셋의 차이이므로, 이를 계산하려면 Kafka Admin API를 통해 두 값을 별도로 조회해야 합니다. 이 때문에 컨슈머 랙 측정에는 보통 `kafka-lag-exporter`와 같은 별도 도구가 사용됩니다.
</details>

7. 컨슈머 랙을 측정하기 위해 이 문서에서 소개한 커뮤니티 Exporter는 무엇인가요?
   - A) node-exporter
   - B) kafka-lag-exporter
   - C) blackbox-exporter
   - D) kube-state-metrics

<details>
<summary>정답 보기</summary>

**정답: B) kafka-lag-exporter**

**설명:**
`kafka-lag-exporter`는 Kafka Admin API를 통해 주기적으로 컨슈머 그룹의 커밋 오프셋과 각 토픽의 최신 오프셋을 조회하여 `kafka_consumergroup_group_lag`와 같은 메트릭을 Prometheus 포맷으로 노출하는 커뮤니티 프로젝트입니다. node-exporter는 호스트 시스템 메트릭, blackbox-exporter는 엔드포인트 프로빙, kube-state-metrics는 Kubernetes 오브젝트 상태를 위한 Exporter로 이 목적과는 다릅니다.
</details>

8. Strimzi가 관리하는 Kafka 브로커 Pod의 메트릭을 Prometheus Operator 환경에서 스크레이핑할 때, 고정된 `Service` 대신 사용하는 것이 더 안정적인 CRD는 무엇인가요?
   - A) ServiceMonitor
   - B) PodMonitor
   - C) Probe
   - D) AlertmanagerConfig

<details>
<summary>정답 보기</summary>

**정답: B) PodMonitor**

**설명:**
브로커는 Strimzi가 관리하는 개별 Pod들로 구성되며, `ServiceMonitor`가 대상으로 삼는 고정된 `Service` 엔드포인트보다는 Pod 라벨(`strimzi.io/cluster` 등)을 직접 셀렉트하는 `PodMonitor`가 더 안정적으로 각 브로커 Pod를 스크레이핑 대상으로 발견할 수 있습니다. `Probe`는 블랙박스 방식의 엔드포인트 점검용 CRD이며, `AlertmanagerConfig`는 알림 라우팅 설정용입니다.
</details>

9. 다음 중 언더 리플리케이트 파티션에 대한 `PrometheusRule` 알림 설정에서 `for: 5m`이 하는 역할은 무엇인가요?
   - A) 5분마다 메트릭을 스크레이핑한다
   - B) 조건이 5분 이상 지속되어야 알림이 실제로 발생(firing)한다
   - C) 알림이 발생한 후 5분 뒤에 자동으로 해제된다
   - D) 5분 동안의 평균값을 계산한다

<details>
<summary>정답 보기</summary>

**정답: B) 조건이 5분 이상 지속되어야 알림이 실제로 발생(firing)한다**

**설명:**
Prometheus의 알림 규칙에서 `for` 필드는 `expr`로 정의된 조건이 지정된 기간 동안 계속 참이어야 알림 상태가 `pending`에서 `firing`으로 전환됨을 의미합니다. `for: 5m`을 지정하면 순간적인 스파이크로 인한 노이즈성 알림을 줄이고, 실제로 문제가 지속되는 경우에만 알림을 발생시킬 수 있습니다.
</details>

10. KEDA의 Kafka 스케일러가 컨슈머 그룹의 랙을 조회하는 방법은 무엇인가요?
    - A) kafka-lag-exporter가 노출한 Prometheus 메트릭을 스크레이핑
    - B) Kafka Admin API를 통해 직접 조회
    - C) 브로커의 JMX Exporter `/metrics` 엔드포인트를 파싱
    - D) ZooKeeper에 저장된 오프셋을 조회

<details>
<summary>정답 보기</summary>

**정답: B) Kafka Admin API를 통해 직접 조회**

**설명:**
KEDA의 Kafka 스케일러는 `bootstrapServers`, `consumerGroup`, `topic` 등의 트리거 파라미터를 기반으로 Kafka Admin API를 직접 호출하여 컨슈머 그룹의 랙을 조회합니다. 따라서 스케일링 판단을 위해서는 `kafka-lag-exporter`와 같은 별도의 Prometheus Exporter가 필수적이지 않습니다(다만 대시보드/알림 시각화에는 여전히 유용합니다). ZooKeeper는 KRaft 모드에서는 더 이상 오프셋 저장에 사용되지 않습니다.
</details>

## 단답형 문제

11. 컨슈머 랙(Consumer Lag)의 정의를 한 문장으로 설명하세요.

<details>
<summary>정답 보기</summary>

**정답: 파티션별로 가장 최근에 프로듀스된 오프셋(log end offset)과 컨슈머 그룹이 마지막으로 커밋한 오프셋의 차이**

**설명:**
컨슈머 랙은 컨슈머가 아직 처리하지 못한 메시지의 양을 오프셋 단위로 나타낸 지표입니다. 랙이 0이면 컨슈머가 최신 메시지까지 모두 처리했다는 뜻이고, 랙이 지속적으로 증가하면 컨슈머의 처리 속도가 프로듀스 속도를 따라가지 못하고 있다는 신호입니다.
</details>

12. Strimzi에서 Kafka 브로커의 JMX 메트릭을 `/metrics` HTTP 엔드포인트로 변환해 노출하는 컴포넌트의 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: Prometheus JMX Exporter (JVM Java 에이전트)**

**설명:**
JMX Exporter는 JVM의 JMX MBean 값을 읽어 relabeling 규칙에 따라 이름과 레이블을 변환한 뒤, Prometheus가 스크레이핑할 수 있는 텍스트 포맷으로 `/metrics` 경로에 노출하는 컴포넌트입니다. Strimzi는 `metricsConfig`가 설정된 경우 이를 별도 사이드카 컨테이너가 아니라 브로커 등 컴포넌트 컨테이너의 동일 JVM 프로세스에서 Java 에이전트로 자동 활성화합니다.
</details>

13. KEDA `ScaledObject`의 Kafka 트리거에서, 파티션당 랙이 특정 값을 넘을 때마다 레플리카를 추가로 늘리는 기준이 되는 파라미터 이름은 무엇인가요?

<details>
<summary>정답 보기</summary>

**정답: `lagThreshold`**

**설명:**
`lagThreshold`는 파티션당 허용 가능한 랙의 기준값으로, 실제 랙이 이 값의 배수를 넘어설 때마다 KEDA가 관리하는 HPA가 레플리카를 추가로 늘립니다. 예를 들어 `lagThreshold: "50"`이고 특정 파티션의 랙이 120이라면 대략 2~3개의 레플리카가 필요하다고 계산됩니다. 이와 별개로 `activationLagThreshold`는 0에서 1로의 최초 스케일 업 여부를 결정하는 파라미터입니다.
</details>

14. 언더 리플리케이트 파티션 수가 증가하기 전에 선행 지표로 관찰할 수 있는, ISR에서 리플리카가 빠지거나 다시 들어오는 빈도를 나타내는 메트릭 쌍의 이름을 쓰세요.

<details>
<summary>정답 보기</summary>

**정답: ISR Shrink Rate와 ISR Expand Rate (`isrshrinkspersec`, `isrexpandspersec`)**

**설명:**
ISR Shrink Rate는 초당 리플리카가 ISR에서 빠지는 빈도, ISR Expand Rate는 초당 리플리카가 다시 ISR에 합류하는 빈도를 나타냅니다. Shrink가 자주 발생한다는 것은 팔로워가 반복적으로 리더를 따라가지 못하고 있다는 뜻으로, 이는 언더 리플리케이트 파티션 증가의 선행 신호로 볼 수 있어 조기 경보 용도로 유용합니다.
</details>

## 실습 문제

15. `Kafka` CR에서 `kafka-metrics`라는 이름의 `ConfigMap`(키: `kafka-metrics-config.yml`)을 참조하도록 `metricsConfig`를 설정하는 YAML을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
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

**설명:**
`type: jmxPrometheusExporter`는 현재 Strimzi가 지원하는 유일한 메트릭 노출 방식이며, `valueFrom.configMapKeyRef`로 relabeling 규칙이 담긴 `ConfigMap`과 그 안의 키를 지정합니다. 이 설정이 적용되면 Strimzi Cluster Operator가 브로커 컨테이너에 JMX Exporter Java 에이전트를 자동으로 활성화하고 지정한 규칙 파일을 마운트합니다.
</details>

16. `orders` 토픽을 소비하는 `order-consumer-group` 컨슈머 그룹의 랙을 기준으로, `order-consumer` `Deployment`를 최소 1개에서 최대 10개까지 스케일링하는 KEDA `ScaledObject`를 작성하세요. 파티션당 랙 기준값은 50으로 설정합니다.

<details>
<summary>정답 보기</summary>

**정답:**
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

**설명:**
`scaleTargetRef.name`은 스케일링 대상 `Deployment`를 지정하고, `minReplicaCount`/`maxReplicaCount`로 스케일링 범위를 제한합니다. `triggers`의 `type: kafka`는 Kafka 스케일러를 사용함을 의미하며, `metadata` 아래에 부트스트랩 서버, 컨슈머 그룹, 토픽, 랙 기준값을 지정합니다. KEDA Operator는 이 리소스를 기반으로 표준 Kubernetes HPA를 생성하고 관리합니다.
</details>

17. 언더 리플리케이트 파티션이 5분 이상 0보다 큰 상태로 지속될 때 `warning` 심각도로 알림을 발생시키는 `PrometheusRule`을 작성하세요.

<details>
<summary>정답 보기</summary>

**정답:**
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
            summary: "Kafka 클러스터에 언더 리플리케이트 파티션 존재"
            description: "5분 이상 언더 리플리케이트 파티션이 0보다 큽니다."
```

**설명:**
`expr`은 클러스터 전체의 언더 리플리케이트 파티션 수를 합산하여 0보다 큰지 확인합니다. `for: 5m`은 이 조건이 5분간 지속되어야 알림이 `firing` 상태가 되도록 하여 일시적인 스파이크로 인한 노이즈를 줄입니다. `labels.severity`는 알림의 심각도를 분류하여 Alertmanager 라우팅에 활용할 수 있습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/07-monitoring.md) | [이전 퀴즈: MSK 연동](./06-msk-integration-quiz.md) | [다음 퀴즈: 모범 사례](./08-best-practices-quiz.md)
