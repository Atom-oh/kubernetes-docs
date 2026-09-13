# Shared VPC와 Connectivity 퀴즈

> 이 퀴즈는 [Shared VPC와 Connectivity](../../governance/04-shared-vpc-and-connectivity.md) 문서의 학습 내용을 테스트합니다.

---

1. TGW route propagation과 VPC route table의 관계는?
   - A) TGW prefix100개가 Shared VPC 전체 고정 한도
   - B) TGW route는 VPC table에 자동 전파되지 않으며 owner가 TGW 방향 static route를 구성
   - C) 모든 table이 하나의 quota 공유
   - D) CIDR quota는 절대 먼저 도달하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) TGW route는 VPC table에 자동 전파되지 않으며 owner가 TGW 방향 static route를 구성**

**설명:**
TGW table 총량은 기본10,000이고 VPC non-propagated route는 기본500입니다. VGW propagated-route100을 TGW 총량으로 혼동하지 않습니다.

</details>

---

2. Shared VPC participant가 owner resource 중 describe할 수 없는 것은?
   - A) Subnet
   - B) 자기 Security Group
   - C) NAT Gateway
   - D) Route table

<details>
<summary>정답 보기</summary>

**정답: C) NAT Gateway**

**설명:**
Owner NAT Gateway는 participant가 describe할 수 없습니다. 다만 중앙 inventory·로그·위임된 읽기 경로로 감사 증거를 구성할 수 있습니다.

</details>

---

3. Shared VPC에서 LBC subnet discovery를 설계하는 적절한 방법은?
   - A) 모든 버전에서 자동 성공을 가정
   - B) 실제 controller 모드·권한·태그 가시성을 검증하고 explicit subnet ID도 검토
   - C) 반드시 owner가 Ingress 생성
   - D) NAT Gateway만으로 discovery 수행

<details>
<summary>정답 보기</summary>

**정답: B) 실제 controller 모드·권한·태그 가시성을 검증하고 explicit subnet ID도 검토**

**설명:**
Owner tag는 자동 공유되지 않습니다. 명시적 subnet은 예측 가능한 선택이며 모든 controller discovery가 실패한다는 뜻은 아닙니다.

</details>

---

4. VPC Lattice의 장기 연결 제한을 올바르게 설명한 것은?
   - A) Service와 resource는 모두10분 제한
   - B) Service lifetime10분과 resource idle350초를 구분하고 protocol/reconnect를 검증
   - C) 모든 WebSocket이 HTTP listener에서 기본 지원
   - D) 장기 연결은 어떤 경로도 불가능

<details>
<summary>정답 보기</summary>

**정답: B) Service lifetime10분과 resource idle350초를 구분하고 protocol/reconnect를 검증**

**설명:**
Resource에는 같은 lifetime 제한이 없습니다. WebSocket은 TLS listener나 resource 경로를 검토할 수 있으며 각 protocol·인증 조건을 확인해야 합니다.

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
