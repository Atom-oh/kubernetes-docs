# Part 8: 모범 사례 퀴즈

이 퀴즈는 파티션 설계, 프로듀서/컨슈머 튜닝, 보안(mTLS/SASL), 비용 최적화 등 Kafka 딥다이브 시리즈 전체를 아우르는 모범 사례 이해도를 테스트합니다.

## 객관식 문제

1. 토픽의 파티션 수를 산정할 때 가장 먼저 고려해야 할 기준은 무엇인가요?
   - A) 클러스터의 전체 브로커 수
   - B) 예상되는 컨슈머 그룹의 최대 병렬 처리 수
   - C) 프로듀서 인스턴스 수
   - D) 사용 가능한 EBS 볼륨 크기

<details>

<summary>정답 보기</summary>

**정답: B) 예상되는 컨슈머 그룹의 최대 병렬 처리 수**

**설명:**
하나의 파티션은 동시에 하나의 컨슈머 인스턴스만 소비할 수 있으므로, 컨슈머 그룹을 최대 몇 개까지 스케일아웃할지 먼저 결정하고 그 수 이상으로 파티션을 만들어야 합니다. 예를 들어 피크 시점에 컨슈머 20개까지 늘릴 계획이라면 파티션은 최소 20개 이상 필요합니다. 브로커 수나 EBS 볼륨 크기는 파티션 수 자체를 결정하는 1차 기준이 아니라 파티션을 얼마나 잘 수용할 수 있는지에 관한 용량 문제입니다.
</details>

2. Confluent가 제시했던 전통적인 경험치 기준으로, 브로커당 파티션 수의 소프트 상한선은 대략 몇 개였나요?
   - A) 400개
   - B) 4,000개
   - C) 40,000개
   - D) 400,000개

<details>

<summary>정답 보기</summary>

**정답: B) 4,000개**

**설명:**
Confluent는 브로커당 파티션 4,000개, 클러스터당 200,000개 정도를 소프트 상한선으로 권장했습니다. 이는 ZooKeeper 기반 컨트롤러가 메타데이터 전파의 병목이었던 시절의 가이드라인이며, KRaft 기반 클러스터는 컨트롤러 성능이 크게 개선되어 이보다 훨씬 많은 파티션을 처리할 수 있습니다. 다만 여전히 필요 이상으로 파티션을 늘리지 않는 것이 원칙이며, 실제 상한은 부하 테스트로 확인해야 합니다.
</details>

3. 파티션을 필요 이상으로 세분화했을 때 발생하는 문제로 적절하지 않은 것은 무엇인가요?
   - A) 브로커당 열린 파일 핸들 수 증가
   - B) 프로듀서/브로커 버퍼 메모리 사용량 증가
   - C) 브로커 장애 시 리더 선출 및 리밸런스 시간 증가
   - D) 컨슈머 그룹의 최대 처리량이 항상 감소

<details>

<summary>정답 보기</summary>

**정답: D) 컨슈머 그룹의 최대 처리량이 항상 감소**

**설명:**
과도한 파티션은 파일 핸들, 메모리, 장애 복구 시간 측면에서 오버헤드를 유발하지만, 컨슈머 병렬도가 충분히 뒷받침된다면 처리량 자체가 항상 감소하는 것은 아닙니다. 오히려 파티션이 너무 적으면 컨슈머를 늘려도 병렬 처리 한계에 부딫혀 처리량이 늘지 않습니다. 파티션 수는 병렬성과 오버헤드 사이의 트레이드오프이며, "많을수록 항상 나쁘다/좋다"는 이분법으로 판단할 문제가 아닙니다.
</details>

4. 키가 있는(keyed) 토픽의 파티션 수를 늘렸을 때 가장 직접적으로 깨지는 보장은 무엇인가요?
   - A) 리플리케이션 팩터
   - B) 동일 키에 대한 메시지 순서 보장
   - C) 컨슈머 그룹의 오프셋 커밋
   - D) 브로커 간 ISR 목록

<details>

<summary>정답 보기</summary>

**정답: B) 동일 키에 대한 메시지 순서 보장**

**설명:**
기본 파티셔너는 `hash(key) % partition_count`로 파티션을 결정하므로, 파티션 수가 바뀌면 동일한 키라도 계산 결과가 달라져 변경 전후 메시지가 다른 파티션에 위치할 수 있습니다. Kafka는 파티션 내에서만 순서를 보장하므로, 같은 키의 메시지가 여러 파티션으로 흩어지면 컨슈머가 키 단위의 처리 순서를 더 이상 신뢰할 수 없습니다. 또한 Kafka Streams의 co-partitioning 기반 조인도 함께 깨질 수 있습니다.
</details>

5. `enable.idempotence`는 Kafka 몇 버전부터 별도로 지정하지 않아도 기본적으로 활성화되나요?
   - A) Kafka 1.0
   - B) Kafka 2.0
   - C) Kafka 3.0
   - D) Kafka 4.0

<details>

<summary>정답 보기</summary>

**정답: C) Kafka 3.0**

**설명:**
`enable.idempotence=true`는 Kafka 3.0부터, `acks`나 `retries`를 명시적으로 재정의하지 않는 한 프로듀서의 기본값으로 활성화됩니다. 프로듀서에 고유한 PID와 시퀀스 번호를 부여해 브로커가 재시도로 인한 중복 쓰기를 자동으로 걸러낼 수 있게 합니다.
</details>

6. 프로듀서의 idempotence(멱등성)가 방지해 주는 것은 무엇인가요?
   - A) 컨슈머 그룹의 리밸런스
   - B) 네트워크 재시도로 인한 브로커 측 중복 쓰기
   - C) 파티션 리더의 장애
   - D) 스키마 레지스트리의 호환성 오류

<details>

<summary>정답 보기</summary>

**정답: B) 네트워크 재시도로 인한 브로커 측 중복 쓰기**

**설명:**
프로듀서가 브로커의 ack를 받지 못해 동일한 레코드를 재전송할 때, 멱등성이 비활성화된 상태라면 브로커에 같은 레코드가 중복으로 기록될 수 있습니다. 멱등성 프로듀서는 PID와 시퀀스 번호로 이를 감지해 브로커가 중복을 제거하도록 합니다. 다만 이는 프로듀서→브로커 구간의 중복만 제거하며, end-to-end exactly-once를 위해서는 트랜잭션 API가 추가로 필요합니다.
</details>

7. `acks=all`과 `min.insync.replicas=2`를 `replication.factor=3`인 토픽에 함께 설정하면 어떤 효과가 있나요?
   - A) 항상 3개 레플리카 모두에 기록될 때까지 대기한다
   - B) 최소 2개 레플리카(리더 포함)에 기록될 때까지 쓰기가 완료되지 않는다
   - C) 압축(compression)이 자동으로 활성화된다
   - D) 파티션 리더 선출이 비활성화된다

<details>

<summary>정답 보기</summary>

**정답: B) 최소 2개 레플리카(리더 포함)에 기록될 때까지 쓰기가 완료되지 않는다**

**설명:**
`acks=all`은 프로듀서가 현재 ISR(in-sync replica) 전체의 ack를 기다리게 하고, `min.insync.replicas=2`는 ISR이 최소 2개(리더 포함) 미만으로 줄어들면 쓰기 자체를 거부하도록 강제합니다. 이 조합은 브로커 1대가 장애나도 데이터 손실 없이 쓰기를 계속할 수 있게 하는 표준적인 durability 설정입니다.
</details>

8. 컨슈머가 `max.poll.interval.ms`를 초과해 처리를 마치지 못하면 어떤 일이 발생하나요?
   - A) 해당 파티션의 리더가 즉시 교체된다
   - B) 컨슈머가 그룹에서 강제로 제외되고 리밸런스가 발생한다
   - C) 브로커가 해당 토픽의 압축을 자동으로 비활성화한다
   - D) 아무 일도 일어나지 않으며 다음 poll을 계속 기다린다

<details>

<summary>정답 보기</summary>

**정답: B) 컨슈머가 그룹에서 강제로 제외되고 리밸런스가 발생한다**

**설명:**
`max.poll.interval.ms`는 한 번의 `poll()` 이후 다음 `poll()`을 호출하기까지 허용되는 최대 시간입니다. 이 시간을 초과하면 브로커는 해당 컨슈머가 죽었다고 판단해 그룹에서 제외시키고 리밸런스를 트리거합니다. 다수의 컨슈머가 동시에 느려지면 리밸런스가 반복되는 "리밸런스 스톰"으로 이어질 수 있습니다.
</details>

9. `group.instance.id`를 설정해 정적 그룹 멤버십(static group membership)을 사용하는 주된 목적은 무엇인가요?
   - A) 컨슈머 처리량을 자동으로 늘린다
   - B) 짧은 Pod 재시작 시 불필요한 리밸런스를 방지한다
   - C) 프로듀서의 압축률을 개선한다
   - D) 파티션 리더 선출 속도를 높인다

<details>

<summary>정답 보기</summary>

**정답: B) 짧은 Pod 재시작 시 불필요한 리밸런스를 방지한다**

**설명:**
Kubernetes에서는 롤링 배포나 OOMKilled 등으로 컨슈머 Pod가 자주 재시작됩니다. `group.instance.id`로 정적 멤버십을 설정하면, 컨슈머가 `session.timeout.ms` 안에 재접속하는 한 기존 파티션 할당을 그대로 유지한 채 리밸런스 없이 복귀할 수 있습니다. 이는 잦은 재시작이 매번 전체 리밸런스를 유발하는 것을 막아줍니다.
</details>

10. Strimzi에서 `KafkaUser`에 `authentication.type: tls`를 지정했을 때 발급되는 인증서는 누가 서명하나요?
    - A) AWS Certificate Manager
    - B) 클라이언트가 직접 생성한 자체 서명(self-signed) 인증서
    - C) Strimzi가 관리하는 클러스터 CA(Cluster CA)
    - D) 별도로 배포한 cert-manager의 Issuer

<details>

<summary>정답 보기</summary>

**정답: C) Strimzi가 관리하는 클러스터 CA(Cluster CA)**

**설명:**
Strimzi는 Kafka 클러스터를 배포할 때 자체 클러스터 CA를 자동으로 생성하고 인증서를 주기적으로 갱신합니다. `KafkaUser`의 `authentication.type`을 `tls`로 지정하면, 이 클러스터 CA가 서명한 클라이언트 인증서가 Secret으로 자동 발급되어 mTLS 통신에 사용됩니다.
</details>

## 단답형 문제

11. 카디널리티가 낮은 필드(예: `country`)를 파티션 키로 그대로 사용했을 때 발생할 수 있는 문제를 한 단어(또는 짧은 구)로 표현하면 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: 핫 파티션(hot partition)**

**설명:**
기본 파티셔너는 `hash(key) % partition_count`로 파티션을 결정하므로, 값의 종류가 적은 저카디널리티 키를 그대로 사용하면 트래픽이 특정 값에 몰릴 때 일부 파티션만 과부하되고 나머지는 유휴 상태가 되는 핫 파티션 현상이 발생합니다. 카디널리티가 높은 필드를 키로 사용하거나 저카디널리티 키에 salt를 추가해 분산을 강제하는 방식으로 완화할 수 있습니다.
</details>

12. 최소 한 번(at-least-once) 처리가 중요한 파이프라인에서 자동 커밋 대신 사용해야 하는 오프셋 커밋 방식과 관련 설정 값을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답: `enable.auto.commit=false`로 설정한 수동 커밋 — 처리 완료 후 `consumer.commitSync()`(또는 `commitAsync()`) 호출**

**설명:**
자동 커밋은 실제 처리가 끝나기 전에 오프셋을 커밋할 수 있어, 처리 중 컨슈머가 죽으면 해당 레코드가 재처리되지 않고 유실된 것처럼 보일 위험이 있습니다. `enable.auto.commit=false`로 설정하고 비즈니스 로직 처리가 완전히 끝난 뒤에만 오프셋을 커밋하면, 처리 중 장애가 발생해도 다음 컨슈머가 같은 레코드를 다시 받아 재처리할 수 있어 최소 한 번 보장이 유지됩니다.
</details>

13. Kafka 브로커 워크로드에서 CPU보다 더 중요하게 고려해야 하는 리소스는 무엇이며, 그 이유를 간단히 설명하세요.

<details>

<summary>정답 보기</summary>

**정답: 메모리(구체적으로는 OS 페이지 캐시)**

**설명:**
Kafka는 디스크 읽기의 상당 부분을 OS 페이지 캐시에서 처리하도록 설계되어 있어, 컨슈머가 최신 데이터를 따라가는 일반적인 상황에서는 브로커 힙 이후 남는 메모리를 페이지 캐시로 얼마나 활용할 수 있는지가 처리량에 직접적인 영향을 줍니다. 이 때문에 컴퓨팅 최적화 인스턴스보다 메모리 최적화 인스턴스(`r6g`/`r7g` 등)가 동일 비용 대비 더 나은 성능을 내는 경우가 많습니다.
</details>

14. Strimzi 리스너에서 특정 Pod/네임스페이스만 브로커 포트에 접근할 수 있도록 제한하는 필드의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `networkPolicyPeers`**

**설명:**
Strimzi 리스너에 `networkPolicyPeers`를 지정하면 `podSelector`/`namespaceSelector`로 명시된 대상만 해당 리스너 포트로 접근할 수 있는 표준 Kubernetes `NetworkPolicy`가 자동으로 생성됩니다. 이를 통해 어떤 워크로드가 Kafka 리스너 포트에 도달할 수 있는지를 선언적으로 제한할 수 있습니다.
</details>

15. EBS 볼륨 암호화가 EBS CSI 드라이버를 사용한다고 해서 자동으로 적용되는지 여부를 설명하고, 암호화를 명시적으로 켜는 방법 두 가지를 제시하세요.

<details>

<summary>정답 보기</summary>

**정답: 자동으로 적용되지 않는다. (1) 계정/리전 수준의 "기본적으로 EBS 암호화" 설정 활성화, (2) `StorageClass`의 `parameters.encrypted: "true"`(필요 시 `kmsKeyId`) 지정**

**설명:**
EBS CSI 드라이버는 암호화를 자동으로 강제하지 않으므로, 암호화되지 않은 `StorageClass`를 사용하면 볼륨이 평문으로 생성될 수 있습니다. 계정/리전 수준의 "기본적으로 EBS 암호화" 설정을 켜거나, `StorageClass`에 `encrypted: "true"`를 명시적으로 지정해야 브로커 PVC가 암호화된 볼륨으로 생성됩니다. Kafka는 규정 준수 대상 데이터를 다루는 경우가 많으므로 이를 기본값으로 삼는 것이 안전합니다.
</details>

## 실습 문제

16. 내구성이 중요한 토픽(예: 주문 처리)을 위한 프로듀서 설정을 `acks`, `min.insync.replicas` 관련 고려 사항, 멱등성, 압축을 포함해 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
# 프로듀서 설정 (토픽은 replication.factor=3, min.insync.replicas=2로 가정)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

**설명:**
`acks=all`은 ISR 전체의 ack를 기다려 durability를 보장하며, 토픽 측의 `min.insync.replicas=2`(replication.factor=3 가정)와 결합해 브로커 1대 장애까지 견딥니다. `enable.idempotence=true`(Kafka 3.0+ 기본값)는 재시도로 인한 중복 쓰기를 방지하고, `compression.type=lz4`는 CPU 오버헤드와 압축률의 균형이 좋아 대부분의 워크로드에 적합합니다. `linger.ms`/`batch.size`는 약간의 지연을 감내하고 배치 효율을 높여 처리량을 개선합니다.
</details>

17. `order-service`라는 이름의 애플리케이션이 `orders` 토픽에 읽기/쓰기 권한을, `order-service-group` 컨슈머 그룹에 읽기 권한을 갖도록 mTLS 인증 기반의 `KafkaUser` 리소스를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

**설명:**
`authentication.type: tls`를 지정하면 Strimzi 클러스터 CA가 서명한 클라이언트 인증서가 Secret으로 자동 발급됩니다. `authorization.type: simple`과 `acls` 목록으로 `orders` 토픽에 대한 Read/Write/Describe 권한, `order-service-group` 컨슈머 그룹에 대한 Read 권한을 선언적으로 부여할 수 있습니다. `strimzi.io/cluster` 레이블은 이 `KafkaUser`가 어떤 `Kafka` 클러스터에 속하는지를 Strimzi Operator에게 알려줍니다.
</details>

18. Kubernetes 환경에서 Pod가 짧게 재시작되어도 리밸런스가 발생하지 않도록, 그리고 처리 완료 후에만 오프셋이 커밋되도록 하는 컨슈머 설정을 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
heartbeat.interval.ms=15000
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);
    }
    consumer.commitSync();
}
```

**설명:**
`group.instance.id`(Pod 이름 등으로 고유하게 설정)는 정적 그룹 멤버십을 활성화해, 컨슈머가 `session.timeout.ms` 안에 재접속하면 리밸런스 없이 기존 파티션 할당을 유지합니다. `enable.auto.commit=false`와 처리 완료 후 `commitSync()` 호출은 실제 처리가 끝난 레코드만 커밋되도록 보장해 최소 한 번 처리를 지원합니다. `max.poll.records`/`max.poll.interval.ms`는 배치당 처리 시간에 맞춰 조정해 불필요한 리밸런스를 추가로 방지합니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/08-best-practices.md) | [Kafka 딥다이브 홈으로](../../../data-on-eks/kafka/README.md)
