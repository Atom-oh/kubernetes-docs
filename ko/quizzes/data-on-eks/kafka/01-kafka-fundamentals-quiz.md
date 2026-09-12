# Kafka 핵심 개념 퀴즈

> **검토 기준**: 2026-09-12, Kafka 4.3.1.

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
파티션 로그의 기록 순서만 보장합니다. 같은 키를 같은 파티션으로 보내려면 serialization·partitioner·파티션 수가 일관되어야 하며, 파티션 증설이나 클라이언트 변경 시 매핑이 달라질 수 있습니다. 업무 발생 시각이나 소비자의 병렬 처리 순서는 별도 계약입니다.
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
ISR은 리더와 충분히 동기화된 복제본이며 리더 자신도 포함합니다. acks=all은 현재 ISR 전체의 승인을 기다리고 min.insync.replicas는 필요한 최소 ISR을 제한합니다. 승인과 매 레코드의 디스크 fsync는 같은 의미가 아닙니다.
</details>

3. Kafka 4.3 Java KafkaConsumer의 enable.auto.commit 기본값은?
   - A) `false`
   - B) `true`
   - C) 브로커 설정에 따라 다름
   - D) Kafka 3.x부터 제거된 설정

<details>

<summary>정답 보기</summary>

**정답: B) `true`**

**설명:**
Kafka 4.3 Java KafkaConsumer의 기본값은 true, 간격 기본값은 5000 ms입니다. 클라이언트 위치는 외부 업무 처리 완료와 다릅니다. 특히 비동기·병렬 처리에서는 완료되지 않은 레코드 뒤의 offset이 커밋되지 않도록 관리합니다. 수동 commit도 완료한 위치를 올바르게 계산해야 합니다.
</details>

4. 다음 중 컨슈머 그룹 리밸런싱을 유발하는 상황이 아닌 것은 무엇인가요?
   - A) 새 컨슈머가 그룹에 참여
   - B) Classic 프로토콜의 컨슈머가 `session.timeout.ms` 내에 하트비트를 보내지 못함
   - C) 토픽의 파티션 수가 변경됨
   - D) 프로듀서가 `acks=all`로 메시지를 전송함

<details>

<summary>정답 보기</summary>

**정답: D) 프로듀서가 `acks=all`로 메시지를 전송함**

**설명:**
멤버십·구독 파티션 변화·heartbeat/poll timeout은 그룹 할당에 영향을 줍니다. Classic은 클라이언트 session.timeout.ms, consumer 프로토콜은 broker의 group.consumer.session.timeout.ms를 사용합니다. acks는 생산자의 승인 설정입니다.
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

7. 세 복제본이 모두 정상 ISR이고 controller quorum 등 다른 조건이 유지될 때, RF=3/min ISR=2/acks=all에서 쓰기 가용성을 유지할 수 있는 broker 장애 수는?
   - A) 0대
   - B) 1대
   - C) 2대
   - D) 3대

<details>

<summary>정답 보기</summary>

**정답: B) 1대**

**설명:**
처음 세 복제본이 모두 정상 ISR이고 controller quorum·네트워크·저장소 조건이 유지되는 경우의 답입니다. 한 broker 손실 후 두 ISR이 남으면 최소값을 만족하지만 leader 전환 중 오류와 재시도는 가능하며, 두 복제본 손실 시 쓰기 가용성은 유지되지 않습니다. RF=3만으로 임의의 두 장애에서 데이터 보존까지 보장하는 것은 아닙니다.
</details>

8. broker 응답을 전혀 기다리지 않는 acks 설정은?
   - A) `acks=0`
   - B) `acks=1`
   - C) `acks=all`
   - D) `acks=-1`

<details>

<summary>정답 보기</summary>

**정답: A) `acks=0`**

**설명:**
acks=0은 broker 응답을 기다리지 않아 저장 여부를 확인할 수 없고 반환 offset은 -1입니다. 모든 부하에서 지연·처리량이 가장 좋다고 보장하지 않습니다. 명시적 enable.idempotence=true와는 충돌합니다. acks=all과 -1은 같은 의미입니다.
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
controller voter 중 하나가 active controller로 선출됩니다. 새 리더 선출에는 필요한 과반수와 통신이 유지되어야 합니다. 전용 controller 프로세스는 데이터 broker 역할을 수행하지 않을 수 있습니다.
</details>

10. Classic 그룹 프로토콜의 CooperativeStickyAssignor를 사용하는 주된 목적은?
    - A) 프로듀서의 파티션 키 해싱 방식을 변경하기 위해
    - B) 리밸런싱 시 파티션 재배치를 최소화하여 리밸런싱 비용을 줄이기 위해
    - C) 컨트롤러 쿼럼의 보터 수를 동적으로 조정하기 위해
    - D) ISR에 포함되는 레플리카 수를 늘리기 위해

<details>

<summary>정답 보기</summary>

**정답: B) 리밸런싱 시 파티션 재배치를 최소화하여 리밸런싱 비용을 줄이기 위해**

**설명:**
CooperativeStickyAssignor는 Classic 그룹 프로토콜의 클라이언트 assignor입니다. 이동할 파티션을 점진적으로 재할당해 불필요한 중단을 줄입니다. 새 consumer 프로토콜은 서버 측 assignor를 사용하므로 이 클래스를 같은 설정 방법으로 적용하지 않습니다.
</details>

## 단답형 문제

11. KRaft의 내부 메타데이터 Raft 로그 이름은?

<details>

<summary>정답 보기</summary>

**정답: `__cluster_metadata`**

**설명:**
__cluster_metadata는 KRaft의 내부 메타데이터 Raft 로그이며 보통 __cluster_metadata-0 디렉터리로 관찰됩니다. 일반 애플리케이션 토픽처럼 KafkaProducer/KafkaConsumer로 관리하는 대상이 아닙니다. controller와 broker는 메타데이터 복제·조회 경로로 상태를 반영합니다.
</details>

12. 프로듀서 설정 중 네트워크 재시도로 인한 메시지 중복 쓰기를 방지하기 위해 활성화하는 옵션의 이름은 무엇인가요?

<details>

<summary>정답 보기</summary>

**정답: `enable.idempotence` (아이돔포턴트 프로듀서, `enable.idempotence=true`)**

**설명:**
프로듀서 ID·epoch·sequence로 같은 전송의 재시도 중복을 방지합니다. 애플리케이션이 같은 업무 이벤트를 새 전송으로 다시 보내는 것까지 일반적으로 중복 제거하지 않습니다. 트랜잭션에는 안정적인 logical writer ID, fencing, 출력·입력 offset의 원자적 커밋과 read_committed 소비가 필요합니다.
</details>

13. 특정 파티션 키의 카디널리티(고유값 개수)가 낮아 트래픽이 소수의 파티션에 몰리는 현상을 무엇이라고 부르나요?

<details>

<summary>정답 보기</summary>

**정답: 핫 파티션(Hot Partition)**

**설명:**
핫 파티션은 파티션 키로 선택한 값의 고유값 개수(카디널리티)가 충분히 크지 않거나 특정 값의 빈도가 지나치게 높을 때 발생합니다. 예를 들어 전체 트래픽의 대부분이 소수의 대형 고객 ID로 몰리면, 해당 키로 라우팅되는 파티션만 과도한 부하를 받고 나머지 파티션은 유휴 상태가 됩니다. 이 문제는 컨슈머 병렬 처리의 이점을 무력화하므로, 키 설계 시 트래픽 분포를 사전에 검토해야 합니다.
</details>

14. KafkaConsumer의 연속 poll() 호출 사이 허용 간격을 제한하는 설정은?

<details>

<summary>정답 보기</summary>

**정답: `max.poll.interval.ms`**

**설명:**
기본값은 300000 ms입니다. 정적 멤버십(group.instance.id)에서는 초과 즉시 파티션을 재할당하지 않고 heartbeat 중단 후 session timeout도 관여합니다. 사용하는 Classic/consumer 프로토콜에 맞는 timeout을 확인하고 처리량·poll 크기·처리 모델을 함께 조정합니다.
</details>

## 실습 문제

15. `kafka-topics.sh`를 사용해 파티션 8개, 복제 팩터 3, `min.insync.replicas=2`로 설정된 `events`라는 토픽을 생성하는 명령어를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```bash
kafka-topics.sh --create \
  --bootstrap-server "$DOCS_BOOTSTRAP" \
  --topic events \
  --partitions 8 \
  --replication-factor 3 \
  --config min.insync.replicas=2
```

**설명:**
이미 접근 가능한 3개 이상 broker와 필요한 인증을 전제로 합니다. 8개 파티션은 자동 파티션 할당 그룹에서 최대 8명의 활성 담당자를 허용하며, 한 소비자가 여러 파티션을 맡을 수도 있습니다. RF와 min ISR의 장애 허용은 실제 동기화 상태·quorum 등 조건을 만족할 때만 성립합니다.
</details>

16. Kafka 4.3.1의 전용 controller(node.id=90)에 세 controller endpoint를 discovery seed로 설정하는 동적 quorum 구성 발췌를 작성하고, seed와 voter 멤버십의 차이를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
# Configuration excerpt for node 90; these DNS names must resolve in the deployment.
process.roles=controller
node.id=90
controller.quorum.bootstrap.servers=controller-0.example.internal:9093,controller-1.example.internal:9093,controller-2.example.internal:9093
listeners=CONTROLLER://controller-0.example.internal:9093
advertised.listeners=CONTROLLER://controller-0.example.internal:9093
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=./controller-90-data
```

**설명:**
controller.quorum.bootstrap.servers는 quorum을 찾기 위한 seed 목록이지 voter 멤버십 선언이 아닙니다. 초기 format/bootstrap에서 cluster ID·directory ID·초기 voter를 맞춰야 합니다. 동적 quorum에서는 controller.quorum.voters를 설정하지 않습니다. DNS·listener·TLS/인증은 실제 환경에 맞춰야 하며 이 코드는 시작 가능한 전체 배포 명세가 아닌 설명용 발췌입니다.
</details>

17. Idempotence와 transactional ID를 사용하는 producer 설정 예시와, Kafka-to-Kafka exactly-once 처리에 추가로 필요한 절차를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```properties
bootstrap.servers=127.0.0.1:19092
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.StringSerializer
acks=all
enable.idempotence=true
transactional.id=orders-writer-1
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
```

**설명:**
이 설정은 트랜잭션을 사용할 준비일 뿐 처리 코드를 대신하지 않습니다. initTransactions→beginTransaction→출력 send→sendOffsetsToTransaction(다음 입력 offset)→commitTransaction과 실패 시 abort/복구가 필요합니다. consumer는 auto commit을 끄고 read_committed를 사용합니다. 동시 writer는 고유한 transactional ID를 사용하며 delivery.timeout.ms 등 기한도 적용됩니다.
</details>

---

[학습 자료로 돌아가기](../../../data-on-eks/kafka/01-kafka-fundamentals.md) | [다음 퀴즈: Strimzi Operator](./02-strimzi-operator-quiz.md)
