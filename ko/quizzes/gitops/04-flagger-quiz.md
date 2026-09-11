# Flagger Progressive Delivery 퀴즈

1. Flagger의 Canary 배포에서 `stepWeight: 10`, `maxWeight: 50` 설정의 의미는?
   - A) 분석 트래픽을 10%씩 50%까지 늘린 후 승격 절차 진행
   - B) 10개의 Pod를 생성하여 최대 50개까지 확장
   - C) 10초 간격으로 50%까지 트래픽을 전환
   - D) 10%의 에러율까지 허용하고 50%에서 롤백

<details>
<summary>정답 보기</summary>

**정답: A) 분석 트래픽을 10%씩 50%까지 늘린 후 승격 절차 진행**

**설명:**
stepWeight는 분석 중 가중치 증가량이고 maxWeight는 분석 단계의 목표 최대값입니다. 검사를 통과하면 10→20→30→40→50%로 진행한 뒤 primary 갱신·전환 절차로 승격합니다. 승격 과정에서 canary가 일시적으로 전체 트래픽을 받을 수 있으므로 50%를 전체 수명의 상한으로 해석하지 않습니다.

</details>

---

2. Flagger가 Canary 배포를 자동으로 롤백하는 조건은?
   - A) CPU 사용률이 80%를 초과할 때
   - B) 한 revision 분석에서 실패 검사 수가 threshold에 도달할 때
   - C) Pod 수가 maxReplicas를 초과할 때
   - D) 배포 시간이 30분을 초과할 때

<details>
<summary>정답 보기</summary>

**정답: B) 한 revision 분석에서 실패 검사 수가 threshold에 도달할 때**

**설명:**
Flagger는 각 분석 단계에서 정의된 메트릭(request-success-rate, request-duration 등)을 평가합니다. 실패 검사는 해당 revision에서 누적되며 성공할 때마다 초기화되는 연속 실패 수가 아닙니다. threshold에 도달하면 후속 조정에서 rollback합니다. primary 갱신 중 장애처럼 건강한 canary를 유지해야 하는 예외 복구 단계도 있습니다.

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
Flagger는 Flux/Flagger 에코시스템의 일부로 GitOps 워크플로우에 자연스럽게 통합됩니다. Argo Rollouts는 ArgoCD와 함께 Argo 에코시스템을 구성합니다. 생태계 결합은 배타적인 요구 사항이 아닙니다. Flagger는 기존 workload를 Canary로 조정하고, Argo Rollouts는 Rollout CRD와 workloadRef 등을 사용합니다. 구체적인 라우팅/실험 기능은 provider에 따라 다릅니다.

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
`mirror: true`는 프로덕션 트래픽의 사본을 새 버전(Green)으로 전송하여 실제 트래픽 패턴으로 테스트합니다. 응답은 클라이언트에게 반환되지 않지만, 복제한 요청의 DB 쓰기·메시지 발송·결제·부하는 발생할 수 있습니다. 검증된 read-only 요청 또는 격리/멱등성 설계가 필요합니다.

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
Pre-rollout webhook은 트래픽 전환이 시작되기 전에 호출됩니다. 준비된 도구/권한으로 smoke 또는 적합성 테스트를 수행합니다. cmd 부하 테스트의 비동기 수락은 품질 통과와 다르며, bash처럼 완료를 기다리는 테스트는 timeout 안에 끝나야 합니다.

</details>

---

7. FluxCD와 Flagger를 함께 사용할 때 Image Automation의 동작 순서는?
   - A) 이미지 선택 → 검토·병합된 Git 변경 → Flux 적용 → Flagger 분석
   - B) Flagger Canary 분석 → 새 이미지 태그 감지 → Git 커밋
   - C) Git 커밋 → 새 이미지 태그 감지 → Flux 동기화
   - D) Flux 동기화 → Flagger Canary 분석 → 새 이미지 태그 감지

<details>
<summary>정답 보기</summary>

**정답: A) 이미지 선택 → 검토·병합된 Git 변경 → Flux 적용 → Flagger 분석**

**설명:**
image-reflector가 태그/정책을 평가하고 image-automation이 표시된 YAML 필드를 수정합니다. 별도 push 브랜치라면 PR 검토·병합 후 Flux가 source 브랜치를 적용하고 Flagger가 workload 변경을 감지합니다. Flagger가 HelmRelease 자체를 직접 동기화하는 것은 아닙니다.

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
A/B Testing에서는 `spec.analysis.match`에 정의된 HTTP 헤더나 쿠키 조건에 따라 트래픽을 분류합니다. 조건을 만족하는 요청만 새 버전으로 라우팅되므로, 선택된 cohort로 트래픽을 보낼 수 있습니다. 하지만 클라이언트가 헤더/쿠키를 바꿀 수 있으므로 이를 직원 권한이나 민감한 기능의 인증 수단으로 사용하지 않습니다.

</details>
