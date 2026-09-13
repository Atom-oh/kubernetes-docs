# 의사결정 프레임워크와 POC 설계 퀴즈

> 이 퀴즈는 [의사결정 프레임워크와 POC 설계](../../governance/06-decision-framework-and-poc.md) 문서의 학습 내용을 테스트합니다.

---

1. 이 문서에서 "가장 큰 누락"으로 지적하는 결정 요소는?
   - A) 태그 명명 규칙
   - B) CUJ별 RTO/RPO 목표
   - C) EKS 버전 번호
   - D) VPC CIDR 크기

<details>
<summary>정답 보기</summary>

**정답: B) CUJ별 RTO/RPO 목표**

**설명:**
CUJ별 RTO/RPO가 정의되어 있지 않으면 A/B EKS Runtime 전환 속도가 충분한지, 데이터 모델 중 어느 쪽이 복구 가능한지, AZ 구성 차이가 의미 있는지를 전혀 판정할 수 없습니다. 이 목표를 다른 무엇보다 먼저 정의해야 합니다.

</details>

---

2. ALB weighted forwarding과 fail-open의 관계는?
   - A) Unhealthy group이면 항상 다른 group으로 자동 전환
   - B) Weighted group 간 자동 failover와 group 내부 unhealthy-target routing은 별개
   - C) Weight가 RTO 보장
   - D) 모든 Region으로 자동 복제

<details>
<summary>정답 보기</summary>

**정답: B) Weighted group 간 자동 failover와 group 내부 unhealthy-target routing은 별개**

**설명:**
Weighted forward는 빈/unhealthy group의 weight를 다른 group에 자동 이관하지 않습니다. 선택 group 내부의 DNS/routing health threshold는 별도로 평가합니다.

</details>

---

3. 판정표(decision matrix) 설계에서 POC-0으로 "판정표 dry-run"을 다른 POC보다 먼저 수행하는 이유는?
   - A) 비용이 가장 적게 들기 때문이다
   - B) 경계 독립 판정, Hybrid 구성 등 다른 모든 선택지가 "판정표로 재현 가능"을 성립 조건으로 두므로, 판정표 없이는 POC 결과가 표준으로 전환되지 않기 때문이다
   - C) AWS SA의 승인이 필요하기 때문이다
   - D) 다른 POC와 관련이 없기 때문이다

<details>
<summary>정답 보기</summary>

**정답: B) 경계 독립 판정, Hybrid 구성 등 다른 모든 선택지가 "판정표로 재현 가능"을 성립 조건으로 두므로, 판정표 없이는 POC 결과가 표준으로 전환되지 않기 때문이다**

**설명:**
판정표 dry-run은 대표 워크로드 10~15개에 두 사람이 독립적으로 판정표를 적용해 불일치율 20% 미만, 예외 처리율 15% 미만 같은 조직별 예시 기준을 검증합니다. 그 결과로 나온 Account/VPC/클러스터 수 추정치가 나머지 POC의 목표값을 결정합니다.

</details>

---

4. 미사용 Region 통제에 대한 맞는 설명은?
   - A) Opt-in 비활성화가 모든 기본 Region에도 가능
   - B) SCP·탐지·지원되는 opt-in 비활성화를 조합하고 기존 resource 비용도 확인
   - C) GuardDuty만으로 API 차단
   - D) Region 비활성화가 모든 resource를 삭제

<details>
<summary>정답 보기</summary>

**정답: B) SCP·탐지·지원되는 opt-in 비활성화를 조합하고 기존 resource 비용도 확인**

**설명:**
기본 활성화 Region은 비활성화할 수 없습니다. Opt-in 비활성화도 기존 resource 삭제·과금 중지를 보장하지 않으므로 cleanup과 접근 정책을 함께 설계합니다.

</details>
