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

2. ALB weighted target group의 "fail open" 동작을 올바르게 설명한 것은?
   - A) unhealthy target에는 절대 트래픽을 보내지 않는다
   - B) healthy target이 부족하면 등록된 모든 target(unhealthy 포함)에 트래픽을 보낸다
   - C) target group 전체가 즉시 서비스 불가 상태가 된다
   - D) 자동으로 다른 리전으로 failover한다

<details>
<summary>정답 보기</summary>

**정답: B) healthy target이 부족하면 등록된 모든 target(unhealthy 포함)에 트래픽을 보낸다**

**설명:**
"unhealthy target으로 자동 failover하지 않는다"는 설명은 절반만 맞습니다. 실제로는 healthy target이 부족하면 ALB가 fail open 동작을 하며, `minimum_healthy_targets` 설정으로 완화해야 합니다. 기본값은 "healthy target 1개면 healthy"이므로 대규모 target group에서 위험할 수 있습니다.

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
판정표 dry-run은 대표 워크로드 10~15개에 두 사람이 독립적으로 판정표를 적용해 불일치율 20% 미만, 예외 처리율 15% 미만을 성공 기준으로 검증합니다. 그 결과로 나온 Account/VPC/클러스터 수 추정치가 나머지 POC의 목표값을 결정합니다.

</details>

---

4. 미사용 리전을 통제할 때 가장 강한 통제 수단은?
   - A) SCP `aws:RequestedRegion` Deny
   - B) Security Hub CSPM 활성화
   - C) Region opt-in 비활성화
   - D) GuardDuty 활성화

<details>
<summary>정답 보기</summary>

**정답: C) Region opt-in 비활성화**

**설명:**
SCP Deny는 예방 통제이고 Security Hub CSPM·GuardDuty는 탐지 통제(활성화한 리전의 finding만 처리하고 소급 수집하지 않음)이지만, Region opt-in을 비활성화하는 것이 가장 강한 통제 수단입니다.

</details>
