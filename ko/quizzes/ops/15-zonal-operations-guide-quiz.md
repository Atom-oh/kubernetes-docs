# Zonal 클러스터 운영 전략 퀴즈

> **관련 문서**: [Zonal 클러스터 운영 전략](../../ops/15-zonal-operations-guide.md)

## 객관식 문제

### 1. EKS 네이티브 롤백의 7일은 무엇을 뜻하나요?

- A) 롤백 완료에 반드시 필요한 시간
- B) 업그레이드 완료 후 롤백을 시작할 수 있는 자격 기간
- C) 노드의 최대 수명
- D) 애드온 자동 복원 기간

<details>
<summary>정답 보기</summary>

**정답: B) 업그레이드 완료 후 롤백을 시작할 수 있는 자격 기간**

바로 이전 마이너 버전으로 롤백을 시작할 수 있는 기간입니다. 생성 버전·지원 상태·후속 업그레이드·호환성 조건도 충족해야 합니다. Auto Mode는 노드를 먼저 되돌리며 애드온·애플리케이션·데이터 변경은 자동 복원하지 않습니다.

</details>

### 2. NLB 타겟 그룹 weight를 0으로 바꾼 뒤 확인할 사항은?

- A) 기존 연결도 모두 즉시 종료된다
- B) TargetGroupBinding이 다른 클러스터로 이동한다
- C) 새 플로우 감소와 기존 플로우 종료를 별도로 확인한다
- D) ARC가 모든 다른 클러스터의 weight를 자동 수정한다

<details>
<summary>정답 보기</summary>

**정답: C) 새 플로우 감소와 기존 플로우 종료를 별도로 확인한다**

일반적인 가중치 변경은 새 플로우 분배에 영향을 주지만, 현재 NLB 가이드는 weight 0 전환 시 잠시 후 기존 연결도 종료된다고 설명합니다. 따라서 자연 종료만을 기다린다고 가정하지 않고 재연결·재시도 영향을 검증합니다. NewFlowCount·ActiveFlowCount와 오류율을 확인한 후 노드를 변경합니다. TGB에는 weight 필드가 없고, EKS zonal shift도 클러스터 간 weight를 자동 변경하지 않습니다.

</details>

### 3. Kafka KIP-392 설정의 올바른 조합은?

- A) broker.rack만 지정하면 모든 컨슈머가 자동 설정된다
- B) RackAwareReplicaSelector, broker.rack, 일치하는 consumer client.rack
- C) unclean.leader.election.enable=true만 설정
- D) consumer AZ 이름과 broker AZ ID는 달라도 된다

<details>
<summary>정답 보기</summary>

**정답: B) RackAwareReplicaSelector, broker.rack, 일치하는 consumer client.rack**

replica.selector.class의 전체 클래스 이름은 org.apache.kafka.common.replica.RackAwareReplicaSelector입니다. Strimzi Kafka CR의 rack 설정은 브로커를 구성하며 일반 애플리케이션 컨슈머는 별도 설정합니다. 로컬 replica가 없으면 리더로 폴백합니다.

</details>

### 4. GLIDE AZ_AFFINITY_REPLICAS_AND_PRIMARY의 우선순위는?

- A) 항상 primary만
- B) 같은 AZ replica → 같은 AZ primary → 다른 AZ의 replica 또는 primary
- C) 항상 다른 AZ replica
- D) 같은 AZ가 없으면 무조건 오류

<details>
<summary>정답 보기</summary>

**정답: B) 같은 AZ replica → 같은 AZ primary → 다른 AZ의 replica 또는 primary**

서버 AZ 정보와 client_az가 맞아야 합니다. replica 읽기의 지연된 데이터를 허용하는지 먼저 판단하며 read 비율만으로 선택하지 않습니다. HotelTrader의 개선 수치는 요청 배칭을 함께 적용한 사례 결과입니다.

</details>

### 5. Aurora 기본 reader endpoint에 대한 올바른 설명은?

- A) 각 SQL 쿼리를 다른 replica에 보낸다
- B) 같은 AZ reader를 반드시 선택한다
- C) 연결 단위로 분산하며 replica가 없으면 writer에 연결될 수 있다
- D) JDBC Wrapper 없이는 접속할 수 없다

<details>
<summary>정답 보기</summary>

**정답: C) 연결 단위로 분산하며 replica가 없으면 writer에 연결될 수 있다**

AZ 우선 선택을 보장하지 않습니다. AZ별 READER custom endpoint는 멤버와 폴백을 관리해야 합니다. JDBC fastestResponse는 응답 시간 기반이며 강제 AZ 제약이 아닙니다. 기능 요청 #1139는 2025년 종료됐습니다.

</details>

### 6. 파드의 AZ 발견에 대한 설명 중 옳지 않은 것은?

- A) 일반 Pod 생성 admission에서 스케줄러가 고른 노드를 항상 알 수 있다
- B) AWS MSK의 Kyverno 예제는 Pod/binding 요청을 사용한다
- C) Downward API의 spec.nodeName을 초기화 구성 요소에 전달할 수 있다
- D) IMDS 접근은 환경과 보안 설정에 따라 제한될 수 있다

<details>
<summary>정답 보기</summary>

**정답: A) 일반 Pod 생성 admission에서 스케줄러가 고른 노드를 항상 알 수 있다**

일반적인 Pod 생성 시점에는 아직 노드가 선택되지 않았습니다. binding 시점 주입이나 스케줄링 후 조회가 필요합니다. Downward API는 노드 라벨을 직접 조회하지 않고, Strimzi가 별도 애플리케이션 컨슈머까지 자동 구성하지도 않습니다.

</details>
