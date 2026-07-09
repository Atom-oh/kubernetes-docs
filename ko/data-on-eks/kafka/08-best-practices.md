# Part 8: 모범 사례

> **지원 버전**: Apache Kafka 3.9, Strimzi 0.45+\
> **마지막 업데이트**: 2026년 7월 9일

지금까지 Kafka의 핵심 개념부터 Strimzi 운영, 스키마 레지스트리, Kafka Connect/MirrorMaker, MSK 통합, 모니터링까지 다뤘습니다. 이 마지막 문서는 프로덕션 환경에서 EKS 위의 Kafka 클러스터를 안정적으로 운영하기 위한 모범 사례를 카테고리별로 정리하고, 앞선 7개 문서의 핵심 항목을 하나의 체크리스트로 통합합니다.

## 1. 파티션 설계

### 파티션 수 산정

파티션 수는 **컨슈머 그룹의 최대 병렬 처리 수**를 기준으로 시작합니다. 하나의 파티션은 동시에 하나의 컨슈머 인스턴스만 소비할 수 있으므로, 컨슈머 그룹을 최대한 어느 규모까지 스케일아웃할지 먼저 결정하고 그 수 이상으로 파티션을 만들어야 합니다. 예를 들어 피크 시점에 컨슈머 20개까지 스케일아웃할 계획이라면 파티션은 최소 20개 이상이어야 합니다.

파티션을 필요 이상으로 늘리는 것은 다음과 같은 비용을 수반하므로 지양해야 합니다.

- **파일 핸들 증가**: 파티션마다 여러 개의 로그 세그먼트 파일(`.log`, `.index`, `.timeindex`)이 열려 있어야 하므로, 브로커당 열린 파일 디스크립터 수가 선형적으로 증가합니다.
- **메모리 사용량 증가**: 프로듀서/컨슈머의 배치 버퍼, 브로커의 복제 스레드별 버퍼가 파티션 수에 비례해 늘어납니다.
- **리밸런스/장애 복구 시간 증가**: 브로커 장애 시 컨트롤러가 처리해야 할 리더 선출 작업량이 파티션 수에 비례하며, 컨슈머 그룹 리밸런스에 걸리는 시간도 늘어납니다.

Confluent가 제시했던 전통적인 경험치는 **브로커당 파티션 4,000개, 클러스터당 200,000개** 정도를 소프트 상한선으로 권장하는 것이었습니다. 이는 ZooKeeper 기반 컨트롤러가 메타데이터 전파에 병목이 있던 시절의 가이드라인입니다. KRaft(Kafka 3.x+ 컨트롤러 쿼럼) 기반 클러스터는 컨트롤러 메타데이터 처리 성능이 크게 개선되어 이보다 훨씬 많은 파티션을 처리할 수 있지만, 여전히 파티션 수를 필요 이상으로 늘리지 않는 것이 원칙이며, 브로커당 파티션 수는 실제 워크로드로 부하 테스트를 거쳐 확정해야 합니다.

```bash
# 클러스터의 전체 파티션 수와 브로커당 분포 확인
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# 특정 토픽의 파티션/리더 분포 확인
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### 파티션 키 설계

파티션 키는 **높은 카디널리티와 균등한 분포**를 갖도록 선택해야 핫 파티션(hot partition)을 피할 수 있습니다. 기본 파티셔너는 키를 murmur2로 해싱한 뒤 파티션 수로 나눈 나머지를 사용하므로, 카디널리티가 낮은 키(예: `country`, `status` 등 소수의 값만 갖는 필드)를 그대로 키로 사용하면 트래픽이 특정 국가나 상태 값에 몰릴 때 일부 파티션만 과부하되고 나머지는 유휴 상태가 됩니다. `user_id`처럼 카디널리티가 충분히 높은 필드를 키로 사용하거나, 저카디널리티 키에 salt(예: 키 뒤에 랜덤/타임스탬프 접미사 부여)를 추가해 분산을 강제하는 방법을 고려합니다.

### 파티션 수 변경 시 주의

키가 있는(keyed) 토픽의 파티션 수를 함부로 늘리면 **키-파티션 매핑이 깨집니다**. 파티션 수가 바뀌면 동일한 키라도 `hash(key) % partition_count` 계산 결과가 달라지므로, 변경 이전에 기록된 메시지와 이후에 기록되는 같은 키의 메시지가 서로 다른 파티션에 위치하게 됩니다. 이는 다음 두 가지 문제를 일으킵니다.

- **순서 보장 붕괴**: Kafka는 파티션 내에서만 순서를 보장하므로, 같은 키의 메시지가 여러 파티션으로 흩어지면 컨슈머가 더 이상 키 단위의 처리 순서를 신뢰할 수 없습니다.
- **조인/co-partitioning 붕괴**: Kafka Streams 등에서 두 토픽을 키 기준으로 조인하려면 두 토픽의 파티션 수와 파티셔닝 방식이 동일해야 합니다(co-partitioning). 한쪽 토픽만 파티션을 늘리면 조인이 깨집니다.

파티션 수는 반드시 **용량 계획 단계에서 여유를 두고 결정**하고, 이미 프로덕션에 키 기반 순서 보장이나 조인에 의존하는 토픽이라면 파티션 증설 대신 새 토픽을 만들어 마이그레이션하는 방식을 고려해야 합니다.

## 2. 프로듀서 튜닝

| 설정 | 권장 값 | 목적 |
|------|---------|------|
| `acks` | `all` (내구성이 중요한 토픽) | 모든 인-싱크 레플리카(ISR)의 ack를 받을 때까지 대기하여 브로커 장애 시에도 데이터 손실 방지 |
| `min.insync.replicas` (토픽/브로커 설정) | `2` (replication.factor=3 기준) | `acks=all`과 함께 사용해 최소 2개 레플리카에 기록될 때까지 쓰기 성공을 보류 — 프로듀서 클라이언트 속성이 아니라 토픽(`kafka-configs.sh --entity-type topics`) 또는 브로커 기본값으로 설정 |
| `linger.ms` | `5`~`20` | 짧은 지연을 감내하고 더 많은 레코드를 하나의 배치로 묶어 처리량 향상 |
| `batch.size` | `32768`~`65536` (32~64KB) | 배치당 담을 수 있는 최대 바이트 수를 늘려 요청당 처리량 증가 |
| `enable.idempotence` | `true` | 재시도로 인한 중복 쓰기 방지 |
| `compression.type` | `lz4` 또는 `zstd` | 네트워크/스토리지 비용 절감 |

```properties
# 내구성이 중요한 토픽(주문, 결제 등)을 위한 프로듀서 설정
# (min.insync.replicas는 프로듀서가 아니라 토픽/브로커에서 설정하는 값이며, 참고용으로 함께 표기)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

`enable.idempotence=true`는 **Kafka 3.0부터 `acks`나 `retries`를 명시적으로 재정의하지 않는 한 기본값으로 활성화**됩니다. 프로듀서에 고유한 PID(Producer ID)와 시퀀스 번호를 부여해, 네트워크 오류로 인한 재전송이 브로커 측에서 자동으로 중복 제거(dedup)되도록 합니다. 이는 "정확히 한 번(exactly-once) 쓰기"와는 다른 개념으로, 프로듀서→브로커 구간의 중복만 제거하며 end-to-end exactly-once를 보장하려면 트랜잭션 API(`transactional.id`)가 추가로 필요합니다.

압축은 `lz4`가 CPU 오버헤드와 압축률의 균형이 좋아 대부분의 워크로드에 적합하며, JSON/텍스트 페이로드처럼 압축률이 중요한 경우 `zstd`가 더 높은 압축률을 제공하는 대신 CPU 사용량이 다소 늘어납니다. `gzip`은 압축률은 높지만 CPU 비용이 커서 고처리량 환경에는 권장하지 않습니다.

## 3. 컨슈머 튜닝

### 리밸런스 스톰 방지

처리 로직이 느려 `max.poll.interval.ms`(기본 5분)를 초과하면 컨슈머가 그룹에서 강제 제외되고 리밸런스가 발생합니다. 다수의 컨슈머가 동시에 느려지면 리밸런스가 연쇄적으로 반복되는 "리밸런스 스톰"이 발생할 수 있습니다.

```properties
# 배치당 처리 시간을 고려해 poll 관련 설정 조정
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

`max.poll.records`를 낮추면 한 번의 `poll()` 호출에서 반환되는 레코드 수가 줄어 처리 시간이 짧아지고, `max.poll.interval.ms`를 늘리면 느린 처리를 더 오래 허용합니다. 근본적으로는 무거운 처리 로직을 poll 스레드에서 분리해 별도 워커 스레드/스레드 풀로 넘기는 구조가 더 견고합니다.

### 수동 오프셋 커밋

주문 처리, 결제 등 최소 한 번(at-least-once) 처리가 중요한 파이프라인에서는 자동 커밋(`enable.auto.commit=true`)을 사용하면 실제 처리가 끝나기 전에 오프셋이 커밋되어, 처리 중 컨슈머가 죽으면 해당 레코드가 재처리되지 않고 유실된 것처럼 보일 위험이 있습니다.

```properties
enable.auto.commit=false
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);          // 비즈니스 로직 처리
    }
    consumer.commitSync();        // 처리 완료 후에만 오프셋 커밋
}
```

### 정적 그룹 멤버십

Kubernetes에서는 롤링 배포, OOMKilled, 노드 교체 등으로 컨슈머 Pod가 자주 재시작됩니다. 기본적으로 컨슈머가 그룹을 떠났다가 재참여하면 리밸런스가 발생하는데, 짧은 재시작마다 매번 전체 리밸런스가 일어나면 불필요한 처리 중단이 반복됩니다. `group.instance.id`로 정적 멤버십을 설정하면 컨슈머가 `session.timeout.ms` 안에 재접속할 경우 기존 파티션 할당을 그대로 유지한 채 리밸런스 없이 복귀합니다.

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id`는 Pod마다 고유해야 하므로, StatefulSet의 Pod 이름이나 다운워드 API로 주입한 값을 사용하는 것이 일반적입니다.

## 4. 보안

### mTLS (전송 계층 암호화 + 상호 인증)

Strimzi는 클러스터 배포 시 자체 CA(Cluster CA)를 자동으로 생성하고 인증서를 주기적으로 갱신합니다. 리스너 타입을 `tls`로 설정하면 클라이언트-브로커 간 트래픽이 암호화되며, `KafkaUser`에 `tls` 인증 타입을 지정하면 클러스터 CA가 서명한 클라이언트 인증서가 자동 발급됩니다.

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

### SASL/SCRAM

인증서 배포·회전을 클라이언트 측에서 관리하기 부담스러운 환경(예: 레거시 애플리케이션, 서드파티 도구)에서는 사용자명/비밀번호 기반의 SASL/SCRAM(`scram-sha-512`)이 대안이 됩니다. Strimzi는 리스너 인증 타입을 `scram-sha-512`로 설정하고, `KafkaUser`의 `authentication.type`을 동일하게 지정하면 Secret에 자격 증명을 자동 생성합니다.

### 선언적 ACL 관리

위 `KafkaUser` 예시처럼 `authorization.type: simple`과 `acls` 목록을 사용하면 브로커에 직접 `kafka-acls.sh`를 실행하는 대신 GitOps 방식으로 ACL을 코드로 관리할 수 있습니다. 신규 서비스가 특정 토픽에 접근해야 할 때는 새 `KafkaUser` 리소스를 커밋하는 것만으로 권한 부여가 끝납니다.

### 네트워크 정책

Strimzi 리스너에는 `networkPolicyPeers`를 지정해 브로커 리스너 포트(예: 9092/9093/9094)에 접근 가능한 Pod를 제한할 수 있습니다.

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    networkPolicyPeers:
      - podSelector:
          matchLabels:
            app: order-service
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kafka-clients
```

이렇게 하면 Kafka `NetworkPolicy` CRD 필드가 표준 Kubernetes `NetworkPolicy` 리소스를 자동 생성하여, 지정된 레이블/네임스페이스 외에서는 리스너 포트로 접근할 수 없게 됩니다.

### 저장 데이터 암호화

EBS 볼륨 암호화는 EBS CSI 드라이버가 자동으로 처리해주는 기능이 아니며, 다음 중 하나를 명시적으로 설정해야 합니다.

- 계정/리전 수준의 **"기본적으로 EBS 암호화" 설정**을 활성화하면 이후 생성되는 모든 볼륨이 자동으로 암호화됩니다.
- `StorageClass`에 `encrypted: "true"`(필요 시 `kmsKeyId`)를 명시합니다.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:ap-northeast-2:123456789012:key/xxxxxxxx
```

Kafka는 규정 준수 대상 데이터를 다루는 경우가 많으므로, 브로커 PVC가 사용하는 `StorageClass`는 위와 같이 암호화를 명시적으로 켜는 것을 기본값으로 삼는 것이 안전합니다.

## 5. 비용 최적화

### 인스턴스 타입 선정

대부분의 Kafka 워크로드는 CPU보다 **메모리(정확히는 OS 페이지 캐시)** 에 훨씬 민감합니다. Kafka는 디스크 읽기의 상당 부분을 페이지 캐시에서 처리하도록 설계되어 있어, 컨슈머가 최신 데이터를 따라가는 일반적인 상황에서는 브로커 힙(보통 4~8GB면 충분)을 넘어서는 나머지 메모리를 페이지 캐시로 활용하는 것이 처리량에 직접적인 영향을 줍니다. 컴퓨팅 최적화 인스턴스보다 메모리 최적화 인스턴스(`r6g`/`r7g` 등 Graviton 계열)가 동일 비용 대비 더 나은 성능을 내는 경우가 많습니다.

### 티어드 스토리지 (Tiered Storage)

KIP-405로 정의된 Kafka 티어드 스토리지는 오래된 로그 세그먼트를 로컬 디스크 대신 S3와 같은 원격 저장소로 오프로드해, 브로커의 로컬 EBS 용량 요구치를 줄이는 기능입니다. 업스트림 Apache Kafka에서는 Kafka 3.6에 얼리 액세스로 도입되었고, **Kafka 3.9부터 프로덕션 준비(GA) 상태**가 되었지만 기본값은 아니므로 여전히 명시적으로 활성화(`remote.log.storage.system.enable=true`)해야 하는 옵트인 기능입니다. Strimzi에서 티어드 스토리지를 사용하려면 해당 버전의 Strimzi 릴리스 노트에서 지원 여부와 성숙도를 먼저 확인하고, 프로덕션 적용 전 별도 클러스터에서 충분히 검증해야 합니다.

### 로그 보존 정책 튜닝

`retention.ms`/`retention.bytes`를 토픽별 실제 요구 사항에 맞게 설정해 비교적 비싼 EBS에 필요 이상으로 데이터를 오래 보관하지 않도록 합니다. 최신 값만 필요한 토픽(예: 상태 스냅샷, 캐시성 데이터)은 `cleanup.policy=compact`로 설정하면 키별 최신 레코드만 유지되어 무한정 증가하는 것을 막을 수 있습니다.

```bash
# 토픽별 보존 정책 조정 예시
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### Spot 인스턴스 활용

개발/스테이징 환경이나 중요도가 낮은 Strimzi 클러스터의 브로커 노드 풀은 Spot 인스턴스로 운영해 비용을 크게 줄일 수 있습니다. 다만 **컨트롤러(KRaft controller) 노드 풀은 On-Demand로 유지**해야 합니다. 컨트롤러 쿼럼이 과반수 손실되면 메타데이터 관리 자체가 중단되므로, Spot 회수로 인한 갑작스러운 손실 위험을 감수할 대상이 아닙니다. 브로커 노드 풀에는 Pod Topology Spread Constraints로 여러 AZ/노드에 분산시켜 Spot 회수 시 동시에 여러 레플리카를 잃지 않도록 구성합니다.

## 6. 운영 체크리스트

이 딥다이브 시리즈(Part 1~8)에서 다룬 핵심 항목을 프로덕션 배포 전 최종 점검 목록으로 정리하면 다음과 같습니다.

- [ ] **아키텍처**: KRaft 모드로 구성했으며, 컨트롤러 노드 풀이 브로커 노드 풀과 분리되어 있다 (Part 1, 2)
- [ ] **복제**: 프로덕션 토픽의 `replication.factor=3`, `min.insync.replicas=2`로 설정되어 단일 브로커 장애를 견딘다 (Part 1)
- [ ] **파티션 설계**: 예상 최대 컨슈머 병렬도를 기준으로 파티션 수를 산정했고, 필요 이상으로 세분화하지 않았다 (Part 8)
- [ ] **Strimzi 버전 고정**: Operator와 Kafka 버전을 명시적으로 고정(pin)하고, 자동 업그레이드에 의존하지 않는다 (Part 2)
- [ ] **스토리지**: 브로커 `StorageClass`가 gp3(또는 io2) + 암호화(`encrypted: "true"`)로 설정되어 있다 (Part 3, 8)
- [ ] **PodDisruptionBudget**: 브로커 롤링 재시작/노드 교체 시 과반수 가용성이 항상 유지되도록 PDB가 설정되어 있다 (Part 3)
- [ ] **무중단 업그레이드 리허설**: 롤링 업그레이드 절차를 스테이징에서 실제로 검증했다 (Part 3)
- [ ] **스키마 호환성**: 스키마 레지스트리의 호환성 모드(BACKWARD/FORWARD/FULL)를 토픽 특성에 맞게 명시적으로 설정했다 (Part 4)
- [ ] **DR/복제**: Kafka Connect·MirrorMaker2 기반 재해 복구 또는 지역 간 복제 절차를 문서화하고 페일오버를 검증했다 (Part 5)
- [ ] **MSK vs 셀프 매니지드 결정**: 운영 부담과 비용을 비교해 관리형 MSK와 Strimzi 셀프 매니지드 중 선택한 근거가 문서화되어 있다 (Part 6)
- [ ] **모니터링/알림**: 브로커 메트릭과 컨슈머 랙(consumer lag)에 대한 대시보드와 알림 규칙이 구성되어 있다 (Part 7)
- [ ] **오토스케일링**: 컨슈머 워크로드에 KEDA 등을 연동해 랙 기반 오토스케일링이 동작한다 (Part 7)
- [ ] **프로듀서/컨슈머 설정 리뷰**: `acks`, `enable.idempotence`, 오프셋 커밋 전략, 정적 그룹 멤버십 등이 워크로드 특성에 맞게 검토되었다 (Part 8)
- [ ] **보안**: mTLS 또는 SASL/SCRAM, `KafkaUser` 기반 ACL, 리스너 `NetworkPolicy`가 모두 적용되어 있다 (Part 8)
- [ ] **비용 리뷰**: 인스턴스 타입, 보존 정책, Spot 활용 범위를 주기적으로 재검토하는 프로세스가 있다 (Part 8)
- [ ] **부하 테스트**: 예상 피크 처리량으로 브로커·컨슈머 스케일을 실제로 부하 테스트했다

이 체크리스트를 모두 충족한다면, 해당 Kafka 클러스터는 EKS 프로덕션 환경에서 안정적으로 운영될 준비가 되었다고 볼 수 있습니다.

---

[메인 페이지로 돌아가기](./)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [주제 퀴즈](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)를 풀어보세요.
