# Flagger Progressive Delivery 퀴즈

1. Flagger의 Canary 배포에서 `stepWeight: 10`, `maxWeight: 50` 설정의 의미는?
   - A) 트래픽을 10%에서 시작하여 50%까지 단계적으로 증가시킨 후 전체 전환
   - B) 10개의 Pod를 생성하여 최대 50개까지 확장
   - C) 10초 간격으로 50%까지 트래픽을 전환
   - D) 10%의 에러율까지 허용하고 50%에서 롤백

<details>
<summary>정답 보기</summary>

**정답: A) 트래픽을 10%에서 시작하여 50%까지 단계적으로 증가시킨 후 전체 전환**

**설명:**
`stepWeight`는 각 분석 단계에서 증가시킬 트래픽 비율이고, `maxWeight`는 Canary가 받을 수 있는 최대 트래픽 비율입니다. 10% → 20% → 30% → 40% → 50% 순으로 증가한 후, 모든 메트릭이 통과하면 100%로 승격됩니다.

</details>

---

2. Flagger가 Canary 배포를 자동으로 롤백하는 조건은?
   - A) CPU 사용률이 80%를 초과할 때
   - B) 분석 단계에서 메트릭 임계값을 연속 실패 횟수만큼 초과할 때
   - C) Pod 수가 maxReplicas를 초과할 때
   - D) 배포 시간이 30분을 초과할 때

<details>
<summary>정답 보기</summary>

**정답: B) 분석 단계에서 메트릭 임계값을 연속 실패 횟수만큼 초과할 때**

**설명:**
Flagger는 각 분석 단계에서 정의된 메트릭(request-success-rate, request-duration 등)을 평가합니다. 연속 실패 횟수(`threshold`)에 도달하면 자동으로 롤백을 수행하고, Canary 트래픽을 0%로 되돌린 후 원래 버전을 유지합니다.

</details>

---

3. Flagger와 Argo Rollouts의 핵심 차이점은?
   - A) Flagger는 Canary만 지원하고, Argo Rollouts는 Blue-Green만 지원
   - B) Flagger는 Flux 에코시스템에 통합되고, Argo Rollouts는 Argo 에코시스템에 통합
   - C) Flagger는 Istio만 지원하고, Argo Rollouts는 모든 메시를 지원
   - D) Flagger는 메트릭 분석을 지원하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) Flagger는 Flux 에코시스템에 통합되고, Argo Rollouts는 Argo 에코시스템에 통합**

**설명:**
Flagger는 Flux/Flagger 에코시스템의 일부로 GitOps 워크플로우에 자연스럽게 통합됩니다. Argo Rollouts는 ArgoCD와 함께 Argo 에코시스템을 구성합니다. 둘 다 Canary, Blue-Green, A/B Testing을 지원하며 다양한 서비스 메시와 연동됩니다.

</details>

---

4. Flagger의 Blue-Green 배포에서 `spec.analysis.mirror: true`의 역할은?
   - A) Blue와 Green 환경의 로그를 미러링
   - B) 프로덕션 트래픽을 Canary(Green)에 복제하여 실제 트래픽으로 테스트
   - C) 데이터베이스를 미러링하여 동기화
   - D) 두 환경의 설정을 동일하게 유지

<details>
<summary>정답 보기</summary>

**정답: B) 프로덕션 트래픽을 Canary(Green)에 복제하여 실제 트래픽으로 테스트**

**설명:**
`mirror: true`는 프로덕션 트래픽의 사본을 새 버전(Green)으로 전송하여 실제 트래픽 패턴으로 테스트합니다. 미러링된 응답은 클라이언트에게 반환되지 않으므로 사용자에게 영향을 주지 않으면서 새 버전의 동작을 검증할 수 있습니다.

</details>

---

5. Flagger에서 Custom Metrics를 사용한 분석 시 `templateRef`의 역할은?
   - A) Helm 차트 템플릿을 참조
   - B) MetricTemplate CR을 참조하여 Prometheus/Datadog 쿼리를 실행
   - C) Deployment 템플릿을 참조하여 Pod를 생성
   - D) ConfigMap 템플릿을 참조

<details>
<summary>정답 보기</summary>

**정답: B) MetricTemplate CR을 참조하여 Prometheus/Datadog 쿼리를 실행**

**설명:**
`templateRef`는 MetricTemplate Custom Resource를 참조합니다. MetricTemplate에는 Prometheus PromQL이나 Datadog 쿼리가 정의되어 있으며, Flagger는 분석 단계에서 이 쿼리를 실행하여 결과를 임계값과 비교합니다. 이를 통해 비즈니스 메트릭 기반의 배포 판단이 가능합니다.

</details>

---

6. Flagger의 Webhook을 사용한 Pre-rollout 테스트의 목적은?
   - A) 배포 전에 데이터베이스 마이그레이션을 실행
   - B) 트래픽 전환 전에 부하 테스트나 적합성 테스트를 실행하여 새 버전을 검증
   - C) Git 리포지토리에 태그를 생성
   - D) Slack 알림을 전송

<details>
<summary>정답 보기</summary>

**정답: B) 트래픽 전환 전에 부하 테스트나 적합성 테스트를 실행하여 새 버전을 검증**

**설명:**
Pre-rollout webhook은 트래픽 전환이 시작되기 전에 호출됩니다. 일반적으로 Flagger loadtester를 통해 부하 테스트(hey, wrk)나 Helm 테스트, Bash 스크립트 등을 실행하여 새 버전이 기본적인 동작을 정상적으로 수행하는지 검증합니다.

</details>

---

7. FluxCD와 Flagger를 함께 사용할 때 Image Automation의 동작 순서는?
   - A) 새 이미지 태그 감지 → Git 커밋 → Flux 동기화 → Flagger Canary 분석
   - B) Flagger Canary 분석 → 새 이미지 태그 감지 → Git 커밋
   - C) Git 커밋 → 새 이미지 태그 감지 → Flux 동기화
   - D) Flux 동기화 → Flagger Canary 분석 → 새 이미지 태그 감지

<details>
<summary>정답 보기</summary>

**정답: A) 새 이미지 태그 감지 → Git 커밋 → Flux 동기화 → Flagger Canary 분석**

**설명:**
Flux Image Automation이 레지스트리에서 새 이미지 태그를 감지하면, Git 리포지토리의 매니페스트를 업데이트하는 커밋을 생성합니다. Flux가 이 변경을 동기화하면 Deployment가 업데이트되고, Flagger가 변경을 감지하여 자동으로 Canary 분석 프로세스를 시작합니다.

</details>

---

8. Flagger의 A/B Testing에서 Header 기반 라우팅이 일반 Canary 배포와 다른 점은?
   - A) A/B Testing은 모든 사용자에게 새 버전을 노출
   - B) 특정 HTTP 헤더/쿠키 조건을 만족하는 요청만 새 버전으로 라우팅
   - C) A/B Testing은 롤백을 지원하지 않음
   - D) Header 기반 라우팅은 TCP 트래픽에만 적용

<details>
<summary>정답 보기</summary>

**정답: B) 특정 HTTP 헤더/쿠키 조건을 만족하는 요청만 새 버전으로 라우팅**

**설명:**
A/B Testing에서는 `spec.analysis.match`에 정의된 HTTP 헤더나 쿠키 조건에 따라 트래픽을 분류합니다. 조건을 만족하는 요청만 새 버전으로 라우팅되므로, 특정 사용자 그룹(베타 테스터, 내부 직원 등)에게만 새 기능을 노출할 수 있습니다.

</details>
