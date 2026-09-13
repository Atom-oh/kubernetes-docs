# Part 7: 모니터링 퀴즈

메트릭의 실제 이름, 수집 범위·결측, 랙과 인증된 KEDA 동작을 확인합니다.

## 1. 이 장의 JMX 방식은 어떻게 실행되며 유일한 Strimzi 메트릭 방식인가요?

<details>
<summary>정답 보기</summary>

JMX Exporter를 같은 JVM의 Java agent로 실행합니다. 유일한 방식은 아니며 strimziMetricsReporter도 지원합니다. 이름·설정·대시보드가 다르므로 바꿀 때 함께 검토합니다.

</details>

## 2. JMX의 MBean 변환 규칙과 PodMonitor relabeling은 어떻게 다른가요?

<details>
<summary>정답 보기</summary>

ConfigMap의 JMX 규칙은 MBean을 메트릭 이름·라벨로 변환합니다. PodMonitor relabeling은 탐색한 수집 대상에 namespace·kafka_cluster·역할 등의 문맥을 붙이는 별도 단계입니다.

</details>

## 3. UnderReplicatedPartitions가 0보다 크면 이미 데이터가 손실된 것인가요?

<details>
<summary>정답 보기</summary>

아닙니다. 정상 상태는 0이지만 장애·지연·계획된 작업 중 증가할 수 있습니다. 지속 시간, min ISR 미만 여부, offline 파티션과 장애 원인을 함께 확인합니다.

</details>

## 4. 액티브 컨트롤러 합계가 2라면 바로 split brain으로 판단해도 되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 한 클러스터의 컨트롤러를 중복 없이 수집했는지, 여러 클러스터·오래된 표본·수집 시점 차이가 섞였는지 먼저 확인합니다. 안정 상태의 기대 합계는 1입니다.

</details>

## 5. BrokerRequestHandlerAvgIdlePercent가 낮을 때 무엇을 함께 보아야 하나요?

<details>
<summary>정답 보기</summary>

CPU, GC, I/O, 요청 지연·큐와 처리량을 함께 봅니다. 바쁜 handler의 신호이지만 CPU 부족 하나로 확정하거나 바로 스레드·브로커 수를 늘리지 않습니다.

</details>

## 6. 브로커 JMX 매핑만으로 컨슈머 그룹 랙이 계산되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 그룹의 커밋 오프셋과 파티션 끝 오프셋을 조회해야 합니다. 이 장은 Strimzi Kafka Exporter를 사용하며 KEDA도 별도로 Kafka API를 직접 조회합니다.

</details>

## 7. 본문의 Kafka Exporter 메트릭 이름·그룹 라벨과 기존 프로젝트의 상태를 설명하세요.

<details>
<summary>정답 보기</summary>

`kafka_consumergroup_lag`와 `consumergroup`입니다. 기존 seglo/kafka-lag-exporter는 보관 처리되었으며 그 도구의 kafka_consumergroup_group_lag/group과 혼동하지 않습니다.

</details>

## 8. PodMonitor가 ServiceMonitor보다 항상 안정적인가요?

<details>
<summary>정답 보기</summary>

아닙니다. 올바른 Service·selector가 있으면 ServiceMonitor도 동작합니다. 본문은 Pod 직접 탐색을 선택하며 Prometheus의 라벨·네임스페이스 selector, RBAC, 네트워크와 중복 수집을 확인합니다.

</details>

## 9. PrometheusRule의 for: 5m과 결측 처리를 설명하세요.

<details>
<summary>정답 보기</summary>

같은 조건이 계속 존재하고 참이어야 5분 후 firing으로 전환합니다. 수집 주기나 평균이 아닙니다. 메트릭 전체가 사라지면 sum 비교가 빈 벡터가 될 수 있으므로 absent와 수집 범위 검사도 필요합니다.

</details>

## 10. KEDA Kafka scaler는 Prometheus lag exporter가 꼭 필요한가요?

<details>
<summary>정답 보기</summary>

아닙니다. Kafka API를 직접 조회합니다. 따라서 KEDA 자체의 브로커 접근·TLS·인증·Secret 읽기 권한이 필요합니다. 대시보드용 exporter와 다른 경로입니다.

</details>

## 11. lag = 0이면 업무 처리가 끝났다는 뜻인가요?

<details>
<summary>정답 보기</summary>

아닙니다. 보통 log-end 다음 오프셋과 커밋한 다음 오프셋의 거리입니다. 처리 전에 커밋했거나 데이터·수집 상태가 다르면 업무 완료와 다릅니다. compaction·트랜잭션 때문에 물리적 레코드 개수와도 다를 수 있습니다.

</details>

## 12. 본문의 bytesin_total과 idle_percent에는 각각 어떤 연산을 적용하나요?

<details>
<summary>정답 보기</summary>

`bytesin_total`은 counter이므로 rate(...[5m])로 초당 처리량을 구합니다. idle_percent는 이미 비율인 gauge이므로 그대로 관찰하며 다시 rate를 적용하지 않습니다.

</details>

## 13. lagThreshold=50과 minReplicaCount=1일 때 스케일링을 설명하세요.

<details>
<summary>정답 보기</summary>

유효한 총 랙의 레플리카당 목표가 50이며 대략 ceil(총 랙/50)에 HPA·scaler 조정과 상한이 적용됩니다. 파티션마다 여러 컨슈머를 만드는 규칙이 아닙니다. min=1이므로 0 축소용 activation/cooldown이 아닌 HPA scale-down 정책을 봅니다.

</details>

## 14. ISR 변화와 토픽 처리량으로 무엇을 알 수 있으며 한계는 무엇인가요?

<details>
<summary>정답 보기</summary>

ISR shrink/expand counter의 rate로 이탈·복귀 반복을 관찰하고 복제 상태와 비교합니다. 토픽 합계 처리량만으로 hot 파티션을 특정할 수는 없어 추가적인 파티션·클라이언트 관찰이 필요합니다.

</details>

## 15. 기존 Kafka 리소스에 본문의 metricsConfig·Kafka Exporter를 추가하는 패치를 작성하세요.

<details>
<summary>정답 보기</summary>

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

metrics-config.yaml을 먼저 만들고 `kubectl -n kafka patch kafka my-cluster --type=merge --patch-file metrics.patch.yaml`로 적용합니다. 완전한 생성용 Kafka 매니페스트가 아니며 기존 인증·listener 등을 보존합니다.

</details>

## 16. TLS/SCRAM과 같은 namespace의 TriggerAuthentication을 사용하는 ScaledObject를 작성하세요.

<details>
<summary>정답 보기</summary>

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

본문의 keda-auth.yaml과 기존 kafka/order-consumer Deployment가 필요합니다. 애플리케이션도 order-processor로 소비해야 합니다. Part 2의 파티션 12개에 최대 10개를 적용하며 다른 구성은 상한을 조정합니다.

</details>

## 17. under-replication 알람을 만들 때 클러스터 범위·for·결측 처리를 어떻게 나누나요?

<details>
<summary>정답 보기</summary>

namespace="kafka", kafka_cluster="my-cluster"로 좁힌 gauge를 클러스터별 합산해 >0 조건에 for:5m을 적용합니다. 별도의 node scrape coverage와 controller metric missing 규칙을 둡니다. lag도 exporter 실패·예상 그룹 누락·음수 커밋 오프셋을 따로 감시합니다.

</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/07-monitoring.md) | [이전 퀴즈](./06-msk-integration-quiz.md) | [다음 퀴즈](./08-best-practices-quiz.md)
