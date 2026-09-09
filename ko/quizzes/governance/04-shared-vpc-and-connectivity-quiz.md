# Shared VPC와 Connectivity 퀴즈

> 이 퀴즈는 [Shared VPC와 Connectivity](../../governance/04-shared-vpc-and-connectivity.md) 문서의 학습 내용을 테스트합니다.

---

1. 대규모 hub-and-spoke 구성의 Shared VPC에서 실제로 가장 먼저 도달하는 quota는?
   - A) VPC당 IPv4 CIDR 수 (5개, 50개까지 조정 가능)
   - B) VPC 라우팅 테이블당 전파(propagated) route 수 (100개, 조정 불가)
   - C) VPC당 subnet 수 (200개)
   - D) VPC당 NAU (64,000, 256,000까지 조정 가능)

<details>
<summary>정답 보기</summary>

**정답: B) VPC 라우팅 테이블당 전파(propagated) route 수 (100개, 조정 불가)**

**설명:**
중앙 TGW hub에서 route propagation을 켜면 VPC + on-prem prefix 합계가 100을 넘는 순간 정지됩니다. 이는 유일한 조정 불가 항목이자 실제 첫 병목이며, IPv4 CIDR 수 한도는 오히려 가장 늦게 도달합니다.

</details>

---

2. Shared VPC에서 participant Account가 전혀 describe할 수 없는 리소스는?
   - A) Subnet
   - B) Security Group (자기 것)
   - C) NAT Gateway
   - D) Route table

<details>
<summary>정답 보기</summary>

**정답: C) NAT Gateway**

**설명:**
participant는 NAT Gateway를 describe조차 할 수 없습니다. 이 때문에 개인정보 계층이 participant Account이고 VPC가 중앙 소유라면, 데이터 소유팀이 자기 데이터의 egress 경로를 스스로 검증할 수 없다는 감사 가능성 문제가 생깁니다.

</details>

---

3. Shared VPC + EKS 조합에서 AWS Load Balancer Controller의 subnet 자동 탐색과 관련해 권장되는 것은?
   - A) 자동 탐색에 항상 의존해도 안전하다
   - B) VPC·subnet 태그는 participant에게 공유되지 않으므로, Ingress/Service에 subnet ID를 명시적으로 annotation하는 것을 표준으로 둔다
   - C) owner Account에서 Ingress를 직접 생성해야 한다
   - D) NAT Gateway를 통해서만 subnet을 탐색할 수 있다

<details>
<summary>정답 보기</summary>

**정답: B) VPC·subnet 태그는 participant에게 공유되지 않으므로, Ingress/Service에 subnet ID를 명시적으로 annotation하는 것을 표준으로 둔다**

**설명:**
`kubernetes.io/role/elb` 등의 태그는 owner 소유이므로 participant Account에서 보인다고 보장할 수 없습니다. 자동 탐색에 의존하지 말고 명시적 annotation을 표준으로 삼는 것이 안전합니다.

</details>

---

4. VPC Lattice의 제약 중 장기 연결(gRPC streaming, WebSocket 등)에 특히 문제가 되는 것은?
   - A) VPC당 service network association이 1개로 제한된다
   - B) Lattice service의 최대 연결 수명이 10분이다
   - C) MTU가 8,500바이트로 제한된다
   - D) Region당 service network가 50개로 제한된다

<details>
<summary>정답 보기</summary>

**정답: B) Lattice service의 최대 연결 수명이 10분이다**

**설명:**
Lattice service는 최대 연결 수명이 10분이라, 장기 연결이 10분마다 강제로 끊기고 애플리케이션이 재연결을 처리해야 합니다. 이 때문에 장기 연결을 쓰는 구간은 Lattice 대상에서 제외하는 것이 권장되며, 반대로 CIDR이 겹치는 레거시 환경 연결에는 Lattice가 적합할 수 있습니다.

</details>

---

5. Route 53 Profiles의 DNS 우선순위 규칙을 올바르게 설명한 것은?
   - A) 항상 local VPC의 rule이 Profile보다 우선한다
   - B) 항상 Profile의 rule이 local VPC보다 우선한다
   - C) 이름이 같으면 local VPC가 우선하지만, Profile에 더 구체적인 이름이 등록되어 있으면 Profile이 우선한다
   - D) 우선순위는 무작위로 결정된다

<details>
<summary>정답 보기</summary>

**정답: C) 이름이 같으면 local VPC가 우선하지만, Profile에 더 구체적인 이름이 등록되어 있으면 Profile이 우선한다**

**설명:**
예를 들어 local VPC에 `example.com` rule이 있고 Profile에 더 구체적인 `test.example.com` rule이 있다면 Profile이 적용됩니다. 이 때문에 "중앙 Profile은 워크로드가 위임받은 namespace보다 구체적인 이름을 갖지 않는다"를 명문 규칙으로 두는 것이 권장됩니다.

</details>
