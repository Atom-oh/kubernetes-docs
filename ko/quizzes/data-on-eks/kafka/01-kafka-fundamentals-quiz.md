# Kafka 핵심 개념 퀴즈

이 퀴즈는 Kafka의 브로커/토픽/파티션 구조, 순서 보장, 컨슈머 그룹 리밸런싱, KRaft, 복제 및 내구성 설정에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Kafka에서 메시지 순서가 보장되는 범위는 어디까지인가요?
   - A) 클러스터 전체
   - B) 토픽 전체 (모든 파티션에 걸쳐)
   - C) 동일한 파티션 내에서만
   - D) 동일한 컨슈머 그룹 내에서만

<details>

<summary>정답 보기</summary>

**정답: C) 동일한 파티션 내에서만**

**설명:**
Kafka는 파티션 내부에서만 메시지 순서를 보장합니다. 하나의 토픽에 여러 파티션이 있으면, 프로듀서가 보낸 순서와 관계없이 서로 다른 파티션에 저장된 메시지 간의 상대적 순서는 보장되지 않습니다. 특정 엔티티(예: 주문 ID)의 이벤트 순서를 보장하려면 해당 엔티티를 식별하는 값을 메시지 키로 사용해 항상 같은 파티션으로 라우팅되도록 해야 합니다.
</details>

2. ISR(In-Sync Replicas)이란 무엇을 의미하나요?
   - A) 클러스터에 등록된 모든 브로커의 집합
   - B) 리더와 충분히 동기화된 레플리카의 집합
   - C) 리더 선출에 참여할 수 없는 레플리카의 집합
   - D) 컨슈머 그룹에 속한 컨슈머의 집합

<details>

<summary>정답 보기</summary>

**정답: B) 리더와 충분히 동기화된 레플리카의 집합**

**설명:**
ISR(In-Sync Replicas)은 파티션의 리더 레플리카와 데이터가 충분히 동기화된 팔로워 레플리카(및 리더 자신)의 집합입니다. `acks=all`로 쓰기를 요청하면 ISR에 포함된 모든 레플리카가 메시지를 수신해야 쓰기가 성공한 것으로 간주됩니다. 팔로워가 리더를 따라가지 못하고 지연되면 ISR에서 제외되어, 장애 시 데이터 일관성을 지키기 위한 안전장치 역할을 합니다.
</details>

3. Kafka 컨슈머의 `enable.auto.commit` 기본값은 무엇인가요?
   - A) `false`
   - B) `true`
   - C) 브로커 설정에 따라 다름
   - D) Kafka 3.x부터 제거된 설정

<details>

<summary>정답 보기</summary>

**정답: B) `true`**

**설명:**
`enable.auto.commit`의 기본값은 `true`이며, 이 경우 컨슈머는 `auto.commit.interval.ms`(기본 5초)마다 자동으로 오프셋을 커밋합니다. 편리하지만 메시지 처리가 완료되기 전에 오프셋이 커밋될 수 있어 장애 시 메시지 손실 위험이 있습니다. 처리 완료 후에만 커밋하려면 `enable.auto.commit=false`로 설정하고 `commitSync()` 또는 `commitAsync()`를 명시적으로 호출해야 합니다.
</details>

4. 다음 중 컨슈머 그룹 리밸런싱을 유발하는 상황이 아닌 것은 무엇인가요?
   - A) 새 컨슈머가 그룹에 참여
   - B) 컨슈머가 `session.timeout.ms` 내에 하트비트를 보내지 못함
   - C) 토픽의 파티션 수가 변경됨
   - D) 프로듀서가 `acks=all`로 메시지를 전송함

<details>

<summary>정답 보기</summary>

**정답: D) 프로듀서가 `acks=all`로 메시지를 전송함**

**설명:**
리밸런싱은 컨슈머 그룹의 멤버십이나 구독 대상 토픽의 파티션 구성이 바뀔 때 발생합니다: 컨슈머의 참여/이탈, 하트비트 타임아웃, `max.poll.interval.ms` 초과, 파티션 수 변경 등이 대표적인 트리거입니다. 반면 `acks`는 프로듀서가 쓰기 완료를 확인하는 방식을 결정하는 설정으로, 컨슈머 그룹의 파티션 할당이나 리밸런싱과는 무관합니다.
</details>

5. KRaft(Kafka Raft metadata mode)가 프로덕션 사용 가능(GA)이 된 Kafka 버전은 언제부터인가요?
   - A) Kafka 2.8
   - B) Kafka 3.3
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>정답 보기</summary>

**정답: B) Kafka 3.3**

**설명:**
KRaft는 Kafka 2.8에서 초기 프리뷰(early access)로 처음 도입되었지만, 프로덕션 환경에서 사용 가능한 GA(General Availability) 상태가 된 것은 Kafka 3.3부터입니다. 이후 여러 마이너 버전을 거쳐 안정화되었고, Kafka 4.0에서는 ZooKeeper 모드가 완전히 제거되어 KRaft가 유일한 메타데이터 관리 방식이 되었습니다.
</details>

6. ZooKeeper 모드가 완전히 제거되고 KRaft가 유일한 메타데이터 관리 방식이 된 Kafka 버전은 무엇인가요?
   - A) Kafka 3.3
   - B) Kafka 3.5
   - C) Kafka 3.9
   - D) Kafka 4.0

<details>

<summary>정답 보기</summary>

**정답: D) Kafka 4.0**

**설명:**
Kafka 4.0(2025년 3월 출시)에서 ZooKeeper 기반 메타데이터 관리 모드가 완전히 제거되었습니다. 이 버전부터는 새로운 클러스터를 KRaft 모드로만 부트스트랩할 수 있으며, 기존 ZooKeeper 기반 클러스터는 Kafka 3.x에서 KRaft로 마이그레이션을 완료한 뒤에만 4.0으로 업그레이드할 수 있습니다.
</details>

7. 토픽을 `replication.factor=3`, `min.insync.replicas=2`로 설정하고 프로듀서가 `acks=all`을 사용할 때, 쓰기 가용성을 유지하면서 허용할 수 있는 최대 동시 브로커 장애 수는 몇 대인가요?
   - A) 0대
   - B) 1대
   - C) 2대
   - D) 3대

<details>

<summary>정답 보기</summary>

**정답: B) 1대**

**설명:**
복제 팩터가 3이므로 파티션은 3개의 레플리카에 저장됩니다. `min.insync.replicas=2`는 ISR에 최소 2개의 레플리카가 남아 있어야 `acks=all` 쓰기가 성공한다는 의미입니다. 브로커 1대가 장애를 겪어도 나머지 2개의 레플리카가 ISR에 남아 있어 쓰기가 계속 성공합니다. 하지만 2대가 동시에 장애를 겪으면 ISR이 1개로 줄어 `min.insync.replicas` 조건을 만족하지 못해 프로듀서는 `NotEnoughReplicasException`을 받게 됩니다.
</details>

8. 프로듀서의 `acks` 설정 중 내구성이 가장 낮고 지연시간이 가장 짧은 값은 무엇인가요?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>정답 보기</summary>

**정답: A) `acks=0`**

**설명:**
`acks=0`은 프로듀서가 브로커의 응답을 전혀 기다리지 않고 메시지를 전송한 즉시 성공으로 간주하는 설정입니다. 지연시간과 처리량 면에서는 가장 유리하지만, 네트워크 문제나 브로커 장애가 발생하면 메시지가 실제로 저장되었는지 알 수 없어 데이터 손실 위험이 가장 큽니다. 참고로 `acks=all`과 `acks=-1`은 동일한 의미이며, ISR의 모든 레플리카가 기록을 완료해야 성공으로 간주하는 가장 안전한 설정입니다.
</details>

9. KRaft 아키텍처에서 실제로 클러스터 메타데이터 변경(파티션 리더 선출, 토픽 생성 등)을 처리하는 단일 노드를 무엇이라고 부르나요?
   - A) 컨트롤러 보터(Controller Voter)
   - B) 액티브 컨트롤러(Active Controller)
   - C) 파티션 리더(Partition Leader)
   - D) 메타데이터 브로커(Metadata Broker)

<details>

<summary>정답 보기</summary>

**정답: B) 액티브 컨트롤러(Active Controller)**

**설명:**
KRaft에서는 여러 컨트롤러 보터(일반적으로 3개 또는 5개, Raft 쿼럼을 위한 홀수 구성)가 메타데이터 로그 복제에 참여하며, 그중 하나가 Raft 합의를 통해 액티브 컨트롤러로 선출됩니다. 액티브 컨트롤러만이 실제로 클러스터 메타데이터 변경 작업을 처리하며, 장애가 발생하면 남은 보터들 사이에서 새로운 액티브 컨트롤러가 다시 선출됩니다.
</details>

10. `CooperativeStickyAssignor`를 사용하는 주된 목적은 무엇인가요?
    - A) 프로듀서의 파티션 키 해싱 방식을 변경하기 위해
    - B) 리밸런싱 시 파티션 재배치를 최소화하여 리밸런싱 비용을 줄이기 위해
    - C) 컨트롤러 쿼럼의 보터 수를 동적으로 조정하기 위해
    - D) ISR에 포함되는 레플리카 수를 늘리기 위해

<details>

<summary>정답 보기</summary>

**정답: B) 리밸런싱 시 파티션 재배치를 최소화하여 리밸런싱 비용을 줄이기 위해**

**설명:**
전통적인 Eager 리밸런싱 프로토콜은 리밸런싱이 시작되면 모든 컨슈머가 자신이 소유한 파티션을 반납한 뒤 처음부터 다시 할당받습니다. `CooperativeStickyAssignor`는 협력적(cooperative) 리밸런싱 프로토콜을 사용해, 실제로 이동이 필요한 파티션만 재할당하고 나머지 파티션은 기존 컨슈머가 계속 소유하도록 합니다. 이를 통해 리밸런싱 중 소비가 중단되는 파티션 수를 줄여 전체적인 처리량 저하를 완화합니다.
</details>

## 단답형 문제

11. KRaft 모드에서 클러스터 메타데이터가 저장되는 Kafka 내부 토픽의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `__cluster_metadata`**

**설명:**
KRaft 모드에서는 별도의 ZooKeeper 앙상블 대신, `__cluster_metadata`라는 내부 토픽에 클러스터 메타데이터(토픽/파티션 정보, ACL, 컨트롤러 상태 변경 이력 등)를 이벤트 로그 형태로 저장합니다. 컨트롤러 쿼럼의 보터들은 Raft 프로토콜을 통해 이 토픽을 복제하며, 브로커는 이 토픽을 구독해 최신 메타데이터를 반영합니다. 이는 Kafka가 자신의 핵심 저장 모델(파티션 로그)을 메타데이터 관리에도 재사용하는 설계입니다.
</details>

12. 프로듀서 설정 중 네트워크 재시도로 인한 메시지 중복 쓰기를 방지하기 위해 활성화하는 옵션의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `enable.idempotence` (아이돔포턴트 프로듀서, `enable.idempotence=true`)**

**설명:**
`enable.idempotence=true`로 설정하면 프로듀서는 각 메시지에 순번(sequence number)과 프로듀서 ID를 부여하고, 브로커는 이를 이용해 동일한 메시지가 재시도로 인해 중복 저장되는 것을 감지하고 제거합니다. 이 옵션은 Kafka 내부(토픽 단위)에서의 정확히 한 번(exactly-once) 쓰기를 보장하는 기반이 되며, `transactional.id`와 결합하면 여러 파티션/토픽에 걸친 원자적 쓰기까지 확장할 수 있습니다.
</details>

13. 특정 파티션 키의 카디널리티(고유값 개수)가 낮아 트래픽이 소수의 파티션에 몰리는 현상을 무엇이라고 부르나요?

<details>

<summary>정답 보기</summary>

**정답: 핫 파티션(Hot Partition)**

**설명:**
핫 파티션은 파티션 키로 선택한 값의 고유값 개수(카디널리티)가 충분히 크지 않거나 특정 값의 빈도가 지나치게 높을 때 발생합니다. 예를 들어 전체 트래픽의 대부분이 소수의 대형 고객 ID로 몰리면, 해당 키로 라우팅되는 파티션만 과도한 부하를 받고 나머지 파티션은 유휴 상태가 됩니다. 이 문제는 컨슈머 병렬 처리의 이점을 무력화하므로, 키 설계 시 트래픽 분포를 사전에 검토해야 합니다.
</details>

14. 컨슈머가 `poll()` 호출 사이에 메시지 처리에 소요할 수 있는 최대 시간을 제어하며, 이를 초과하면 컨슈머가 그룹을 떠난 것으로 간주되어 리밸런싱이 트리거되는 설정의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `max.poll.interval.ms`**

**설명:**
`max.poll.interval.ms`는 컨슈머가 연속된 `poll()` 호출 사이에 허용되는 최대 시간 간격을 지정합니다(기본값 5분). 한 번의 `poll()`로 가져온 레코드를 처리하는 데 이 시간을 초과하면, 브로커는 해당 컨슈머가 더 이상 살아있지 않다고 판단하고 그룹에서 제외한 뒤 리밸런싱을 트리거합니다. 이는 하트비트 스레드가 별도로 동작하는 `session.timeout.ms`와는 별개의 메커니즘으로, 처리 로직이 느린 경우 이 값을 늘리거나 `max.poll.records`를 줄여 배치 크기를 조정해야 합니다.
</details>

## 실습 문제

15. `kafka-topics.sh`를 사용해 파티션 8개, 복제 팩터 3, `min.insync.replicas=2`로 설정된 `events`라는 토픽을 생성하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**설명:**
`--partitions 8`은 토픽을 8개의 파티션으로 분할해 최대 8개의 컨슈머가 동시에 병렬 소비할 수 있게 합니다. `--replication-factor 3`은 각 파티션을 3개의 브로커에 복제하여 최대 2대의 브로커 장애까지 데이터를 보존합니다. `--config min.insync.replicas=2`는 `acks=all`로 쓸 때 최소 2개의 레플리카가 ISR에 남아 있어야 쓰기가 성공하도록 강제하여, 복제 팩터와 결합해 1대의 브로커 장애까지 쓰기 가용성을 유지합니다.
</details>

16. 3개의 노드로 구성된 전용 KRaft 컨트롤러 쿼럼(브로커 역할 없이 컨트롤러 역할만 수행)의 `server.properties` 설정 예시를 작성하세요. (노드 ID는 90, 91, 92를 사용)

<details>

<summary>정답 보기</summary>

**정답:**
```properties
# 각 컨트롤러 전용 노드의 server.properties (예: node.id=90인 노드)
process.roles=controller
node.id=90

controller.quorum.voters=90@kraft-controller-0:9093,91@kraft-controller-1:9093,92@kraft-controller-2:9093

listeners=CONTROLLER://:9093
controller.listener.names=CONTROLLER

log.dirs=/var/lib/kafka/controller-data
```

**설명:**
`process.roles=controller`로 설정하면 이 노드는 브로커 역할 없이 오직 컨트롤러 쿼럼의 보터로만 동작합니다. 대규모 클러스터에서는 이렇게 컨트롤러 역할을 브로커와 분리하면 메타데이터 처리 부하가 데이터 처리 부하와 경쟁하지 않아 안정성이 높아집니다. `controller.quorum.voters`에는 컨트롤러 쿼럼에 참여하는 모든 노드의 `node.id@host:port`를 나열해야 하며, 3개(또는 5개)의 홀수 구성으로 Raft 쿼럼 과반수를 계산할 수 있게 합니다.
</details>

17. 프로듀서 설정에서 `acks=all`, 아이돔포턴트 쓰기, 트랜잭션 ID를 모두 사용해 정확히 한 번(exactly-once) 쓰기를 구성하는 프로듀서 설정 예시(Java 프로퍼티 형식)를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
acks=all
enable.idempotence=true
transactional.id=order-producer-1
max.in.flight.requests.per.connection=5
retries=2147483647
```

**설명:**
`acks=all`은 ISR의 모든 레플리카가 메시지를 수신해야 성공으로 간주하도록 하고, `enable.idempotence=true`는 재시도로 인한 중복 쓰기를 제거합니다. `transactional.id`를 지정하면 프로듀서는 트랜잭셔널 프로듀서로 동작하며, `initTransactions()`, `beginTransaction()`, `commitTransaction()` API를 통해 여러 파티션에 걸친 쓰기를 원자적으로 처리할 수 있습니다. `retries`를 높게 설정해도 `enable.idempotence=true`이면 순서와 중복이 안전하게 관리되며, `max.in.flight.requests.per.connection`은 5 이하로 유지해야 순서 보장이 깨지지 않습니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [다음 퀴즈: Strimzi Operator](./02-strimzi-operator-quiz.md)
