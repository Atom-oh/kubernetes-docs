# GWLB·GENEVE 퀴즈

> **마지막 업데이트**: 2026년 10월 15일

[본문과 공식 출처 보기](../../security/16-gwlb-geneve-inspection.md)

### 1. 모든 검사 가능한 GWLB target이 unhealthy일 때 AWS 문서의 설명은?

- A) 장비 직접 우회 대신 unhealthy target으로 전달
- B) 원래 목적지로 직접 전달
- C) 모든 packet 암호화
- D) 앱 가용성 보장

<details>
<summary>정답 보기</summary>

**정답: A) 장비 직접 우회 대신 unhealthy target으로 전달**

**설명:** 장비를 직접 우회하지 않습니다. AWS는 flow별 target 임의 선택과 그 target이 회복할 때까지 drop을 설명합니다. health만 실패했는데 전달되는 경우는 PoC 가설이며 AZ별 대상과 cross-zone 설정을 확인합니다.

</details>

### 2. 등록된 target이 하나도 없을 때 새로운 flow의 결과는?

- A) 직접 우회
- B) traffic drop
- C) 새 target 자동 생성
- D) WAF가 IP 흐름 대신 처리

<details>
<summary>정답 보기</summary>

**정답: B) traffic drop**

**설명:** 새 flow는 전달할 target이 없어 drop을 확인해야 합니다. all-unhealthy와 구분하고, 기존 flow는 failover·drain 설정에 따라 별도로 시험합니다.

</details>

### 3. no_rebalance의 기존 flow 동작은?

- A) 완전한 state와 항상 이전
- B) 성공 보장
- C) 기존 target을 유지해 unhealthy에서 blackhole 가능
- D) 검사 우회

<details>
<summary>정답 보기</summary>

**정답: C) 기존 target을 유지해 unhealthy에서 blackhole 가능**

**설명:** rebalance도 독립 장비 state를 복구하지 않습니다. 두 failover 속성은 같은 값이어야 합니다.

</details>

### 4. TGW appliance mode가 제공하는 것은?

- A) 자동 IPS
- B) 장비 간 자동 state 복제
- C) 모든 VPC local packet 검사
- D) 양방향 inspection attachment AZ 선택의 일관성

<details>
<summary>정답 보기</summary>

**정답: D) 양방향 inspection attachment AZ 선택의 일관성**

**설명:** flow별 양방향 attachment/AZ 선택은 GWLB target stickiness나 제조사 세션 공유와 다릅니다. appliance mode는 TGW의 기본 origin-AZ 선호를 대신합니다.

</details>

### 5. 2/3-tuple stickiness와 TGW appliance mode를 함께 쓸 수 있는가?

- A) 공식 제약상 안 된다
- B) 항상 가능
- C) UDP 6081이 열리면 가능
- D) 모든 target unhealthy일 때만 가능

<details>
<summary>정답 보기</summary>

**정답: A) 공식 제약상 안 된다**

**설명:** 현재 AWS 문서는 TGW appliance mode에 5-tuple을 요구합니다. reduced-tuple 모드의 부하 집중과 실제 지원 조합을 확인합니다.

</details>

### 6. security group에 대한 올바른 설명은?

- A) GWLB·GWLBE 각각 ALB식 SG가 필요
- B) 둘 다 해당 SG를 지원하지 않으며 장비·workload ENI·NACL·route를 확인
- C) 장비 SG는 무관
- D) NACL은 stateful

<details>
<summary>정답 보기</summary>

**정답: B) 둘 다 해당 SG를 지원하지 않으며 장비·workload ENI·NACL·route를 확인**

**설명:** GWLB SG 설정을 만들지 않습니다. health·외부 GENEVE에는 실제 경로 통제가 필요합니다.

</details>

### 7. NAT subnet의 return route를 검토하는 이유는?

- A) DNS만 필요
- B) 요청 route를 자동 따른다
- C) 역변환 후 응답도 일관된 검사 경로로 돌아와야 한다
- D) NAT가 firewall state 자동 복제

<details>
<summary>정답 보기</summary>

**정답: C) 역변환 후 응답도 일관된 검사 경로로 돌아와야 한다**

**설명:** 요청 검사만으로 충분하지 않습니다. 변환 전후 tuple을 기록하고 loop를 방지합니다.

</details>

### 8. GWLB가 fragmentation·PMTUD로 모든 MTU 문제를 해결하는가?

- A) 모든 jumbo packet에서 그렇다
- B) health가 green이면 그렇다
- C) license가 정상이면 그렇다
- D) 아니다; encapsulation과 모든 구간 MTU를 확인한다

<details>
<summary>정답 보기</summary>

**정답: D) 아니다; encapsulation과 모든 구간 MTU를 확인한다**

**설명:** AWS는 최대 8500 bytes·68 bytes overhead와 GWLB fragmentation/PMTUD 미제공을 설명합니다. 실제 packet·protocol 경로를 시험합니다.

</details>
