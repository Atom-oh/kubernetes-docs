# Zonal 클러스터 운영 전략 퀴즈

> **관련 문서**: [Zonal 클러스터 운영 전략](../../ops/15-zonal-operations-guide.md)

## 객관식 문제

### 1. Amazon EKS 네이티브 Kubernetes 버전 롤백(2026년 7월 GA)의 유효 기간은?

- A) 24시간
- B) 7일
- C) 30일
- D) 무제한

<details>
<summary>정답 보기</summary>

**정답: B) 7일**

**설명:**
EKS 네이티브 롤백은 업그레이드 후 7일 이내, 한 번에 마이너 버전 1개를 되돌릴 수 있습니다. 대상 버전으로 새로 생성된 클러스터, 7일 초과, 이미 재업그레이드된 경우 등은 롤백 대상에서 제외됩니다.

</details>

### 2. Zonal In-Place 업그레이드에서 트래픽을 zone 밖으로 빼는 데 사용하는 메커니즘은?

- A) kubectl drain
- B) Target Group weight 조정
- C) DNS TTL 만료 대기
- D) 클러스터 재생성

<details>
<summary>정답 보기</summary>

**정답: B) Target Group weight 조정**

**설명:**
클러스터 내부 리소스를 건드리지 않고, TargetGroupBinding으로 연결된 로드밸런서의 Target Group weight를 조정해 특정 zone으로의 트래픽을 줄이거나 끊습니다. AZ 장애처럼 예기치 않은 상황에는 ARC Zonal Shift가 자동으로 이 역할을 대신합니다.

</details>

### 3. Kafka KIP-392(Follower Fetching)를 활성화하기 위해 브로커에 설정해야 하는 것은?

- A) `auto.leader.rebalance.enable=true`
- B) `replica.selector.class=RackAwareReplicaSelector`
- C) `unclean.leader.election.enable=true`
- D) `min.insync.replicas=2`

<details>
<summary>정답 보기</summary>

**정답: B) `replica.selector.class=RackAwareReplicaSelector`**

**설명:**
브로커에 `replica.selector.class`를 `RackAwareReplicaSelector`로 설정하고 `broker.rack`(AZ ID)을 지정해야 합니다. 컨슈머 쪽은 `client.rack` 속성에 자기 AZ ID를 설정해야 같은 rack의 팔로워로 fetch가 재전송됩니다.

</details>

### 4. Read 비율이 99% 이상인 워크로드에 Valkey GLIDE에서 권장되는 `ReadFrom` 전략은?

- A) `PRIMARY`
- B) `PREFER_REPLICA`
- C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`
- D) 랜덤 분산

<details>
<summary>정답 보기</summary>

**정답: C) `AZ_AFFINITY_REPLICAS_AND_PRIMARY`**

**설명:**
같은 AZ의 replica를 먼저 시도하고, 없으면 같은 AZ의 primary, 최후에 다른 AZ로 폴백합니다. Read가 압도적으로 많은 워크로드에서 비용 절감과 가용성의 균형점으로 권장됩니다. HotelTrader 사례에서 이 전략 도입으로 인터-AZ 전송비가 95% 절감되었습니다.

</details>

### 5. Amazon Aurora의 기본 reader endpoint에 대한 설명으로 옳은 것은?

- A) 같은 AZ의 replica에 자동으로 우선권을 준다
- B) AZ를 고려하지 않는 라운드로빈 DNS다
- C) 항상 primary로만 요청을 보낸다
- D) AWS Advanced JDBC Wrapper 없이는 사용할 수 없다

<details>
<summary>정답 보기</summary>

**정답: B) AZ를 고려하지 않는 라운드로빈 DNS다**

**설명:**
Aurora의 기본 reader endpoint는 AZ affinity가 없는 라운드로빈 DNS입니다. AZ별 커스텀 엔드포인트를 만들거나 AWS Advanced JDBC Wrapper의 `fastestResponse` 전략으로 우회할 수 있지만, 완전한 AZ affinity 자체는 `aws-advanced-jdbc-wrapper` 저장소에 아직 열려 있는 기능 요청입니다.

</details>

### 6. 파드가 자신이 속한 AZ를 알아내는 방법에 대한 설명 중 옳지 않은 것은?

- A) EC2 IMDS를 직접 조회해서 알아낼 수 있다
- B) Kyverno mutating policy로 노드 라벨을 파드 annotation에 주입할 수 있다
- C) Kubernetes Downward API가 노드의 zone 라벨을 파드에 기본으로 주입해준다
- D) Strimzi 같은 오퍼레이터는 rack-awareness를 내장 기능으로 제공한다

<details>
<summary>정답 보기</summary>

**정답: C) Kubernetes Downward API가 노드의 zone 라벨을 파드에 기본으로 주입해준다**

**설명:**
Downward API는 노드의 `topology.kubernetes.io/zone` 라벨을 파드에 자동으로 주입해주지 않습니다. 그래서 IMDS 직접 조회, Kyverno를 통한 admission 시점 라벨 복사, 또는 Strimzi처럼 오퍼레이터가 내장 지원하는 방식 중 하나가 필요합니다.

</details>

