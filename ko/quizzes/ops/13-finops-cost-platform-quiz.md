# FinOps 비용 가시성 플랫폼 퀴즈

1. FinOps의 세 가지 운영 사이클 단계를 올바른 순서로 나열한 것은?
   - A) Optimize → Inform → Operate
   - B) Inform → Optimize → Operate
   - C) Operate → Inform → Optimize
   - D) Inform → Operate → Optimize

<details>
<summary>정답 보기</summary>

**정답: B) Inform → Optimize → Operate**

**설명:**
FinOps 사이클은 Inform(비용 가시성 확보) → Optimize(비용 최적화) → Operate(거버넌스 운영) 순서로 반복됩니다. 먼저 누가, 무엇에, 얼마를 쓰는지 파악한 후 최적화하고, 정책으로 관리합니다.

</details>

---

2. Kubecost에서 AWS CUR(Cost and Usage Report)을 통합하는 주된 이유는?
   - A) Kubecost 라이선스 비용을 줄이기 위해
   - B) Kubernetes 외부의 AWS 서비스 비용을 추적하기 위해
   - C) Pod 레벨의 비용 정확도를 높이기 위해 실제 AWS 비용 데이터와 매칭하기 위해
   - D) 멀티 클러스터 페더레이션을 활성화하기 위해

<details>
<summary>정답 보기</summary>

**정답: C) Pod 레벨의 비용 정확도를 높이기 위해 실제 AWS 비용 데이터와 매칭하기 위해**

**설명:**
Kubecost 자체는 공개 가격(list price)을 기반으로 비용을 추정합니다. CUR 통합을 통해 Savings Plans, Reserved Instances, 협상 가격 등이 반영된 실제 청구 데이터와 매칭하여 비용 정확도를 크게 향상시킬 수 있습니다.

</details>

---

3. Kyverno로 비용 추적 레이블을 강제할 때 `validationFailureAction: Enforce`의 의미는?
   - A) 레이블이 없는 워크로드를 경고만 표시
   - B) 레이블이 없는 워크로드의 배포를 차단
   - C) 자동으로 레이블을 추가
   - D) 기존 워크로드의 레이블을 수정

<details>
<summary>정답 보기</summary>

**정답: B) 레이블이 없는 워크로드의 배포를 차단**

**설명:**
`validationFailureAction: Enforce`는 정책을 위반하는 리소스의 생성/수정을 차단합니다. team, service, cost-center 레이블이 없는 Deployment는 배포가 거부됩니다. 초기에는 `Audit` 모드로 경고만 하다가 팀이 준비되면 `Enforce`로 전환하는 것이 권장됩니다.

</details>

---

4. VPA를 `updateMode: "Off"`로 설정하는 이유는?
   - A) VPA를 비활성화하기 위해
   - B) 리소스 추천만 제공하고 Pod를 자동 재시작하지 않기 위해
   - C) CPU만 조정하고 메모리는 고정하기 위해
   - D) HPA와의 충돌을 방지하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 리소스 추천만 제공하고 Pod를 자동 재시작하지 않기 위해**

**설명:**
`updateMode: "Off"`는 VPA가 리소스 사용량을 분석하고 추천값을 제공하지만, Pod를 자동으로 재시작하여 리소스를 변경하지 않습니다. 추천값을 확인한 후 PR을 통해 수동으로 적용하는 안전한 워크플로우에 적합합니다. Goldilocks 대시보드도 이 모드를 활용합니다.

</details>

---

5. Showback과 Chargeback의 차이점은?
   - A) Showback은 비용 표시, Chargeback은 비용 숨기기
   - B) Showback은 비용 가시성 제공, Chargeback은 실제 부서/팀에 비용 청구
   - C) Showback은 실시간, Chargeback은 월간
   - D) Showback은 클라우드 전용, Chargeback은 온프레미스 전용

<details>
<summary>정답 보기</summary>

**정답: B) Showback은 비용 가시성 제공, Chargeback은 실제 부서/팀에 비용 청구**

**설명:**
Showback은 각 팀/서비스가 사용하는 리소스 비용을 보여주어 인식을 높이는 것이고, Chargeback은 실제로 해당 비용을 부서 예산에서 차감하는 것입니다. 대부분의 조직은 Showback부터 시작하여 비용 문화를 정착시킨 후 Chargeback으로 전환합니다.

</details>

---

6. Goldilocks 대시보드가 네임스페이스의 리소스 추천을 표시하려면 어떤 레이블이 필요한가요?
   - A) goldilocks.fairwinds.com/vpa-enabled=true
   - B) goldilocks.fairwinds.com/enabled=true
   - C) vpa.kubernetes.io/enabled=true
   - D) monitoring.goldilocks.com/watch=true

<details>
<summary>정답 보기</summary>

**정답: B) goldilocks.fairwinds.com/enabled=true**

**설명:**
Goldilocks는 `goldilocks.fairwinds.com/enabled=true` 레이블이 붙은 네임스페이스의 모든 Deployment에 대해 자동으로 VPA를 생성하고, 추천 리소스 값을 웹 대시보드에서 시각화합니다.

</details>

---

7. Kubecost Allocation API에서 `aggregate=label:team`의 의미는?
   - A) 팀 레이블이 있는 Pod만 필터링
   - B) 비용을 team 레이블 값별로 그룹화하여 합산
   - C) 팀별로 별도의 API 호출 생성
   - D) team 레이블을 자동으로 추가

<details>
<summary>정답 보기</summary>

**정답: B) 비용을 team 레이블 값별로 그룹화하여 합산**

**설명:**
`aggregate=label:team`은 Kubecost가 모든 Pod의 비용을 `team` 레이블 값(예: team-commerce, team-platform)별로 그룹화하여 합산합니다. 이를 통해 팀별 총 비용, CPU 비용, 메모리 비용 등을 한번에 조회할 수 있습니다.

</details>

---

8. 비용 이상 탐지에서 "네임스페이스 비용이 7일 평균의 2배를 초과"하는 알림을 30분간 유지해야 발화하는 이유는?
   - A) Prometheus 스크레이프 주기가 30분이라서
   - B) 일시적 스파이크(배포, 오토스케일링)로 인한 오탐(false positive)을 방지하기 위해
   - C) Slack API 호출 제한을 피하기 위해
   - D) Kubecost 데이터 갱신 주기가 30분이라서

<details>
<summary>정답 보기</summary>

**정답: B) 일시적 스파이크(배포, 오토스케일링)로 인한 오탐(false positive)을 방지하기 위해**

**설명:**
배포, 오토스케일링, 배치 작업 등으로 비용이 일시적으로 급등할 수 있습니다. `for: 30m`은 30분 이상 지속적으로 비용이 높은 경우에만 알림을 발화하여, 정상적인 운영 활동으로 인한 불필요한 알림을 줄입니다.

</details>
