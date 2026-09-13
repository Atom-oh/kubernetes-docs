# Argo Rollouts Experiment 퀴즈

이 퀴즈는 Argo Rollouts Experiment CRD의 리소스 계층, 트래픽 격리, 분석 판정, 결과 전파에 대한 이해도를 테스트합니다.

1. Experiment CRD의 핵심 용도는 무엇인가요?
   - A) 프로덕션 트래픽 전체를 새 버전으로 전환
   - B) 일회성 ReplicaSet과 분석으로 새 버전 검증
   - C) Rollout의 revision 히스토리 보관
   - D) 클러스터 노드의 부하 테스트

<details>
<summary>정답 보기</summary>

**정답: B) 일회성 ReplicaSet과 분석으로 새 버전 검증**

**설명:**
Experiment는 일회성(ephemeral) ReplicaSet을 잠깐 띄웠다가 종료 시 0으로 스케일 다운하는 리소스입니다. 트래픽 격리는 Service selector/라우터 설정으로 확보해야 합니다. 별도 ReplicaSet이라는 이유만으로 실제 사용자 영향이 없다고 보장되지 않습니다.

</details>

2. Rollout의 canary 전략에서 experiment step이 Failed 또는 Error로 끝나면 어떻게 되나요?
   - A) 해당 step만 건너뛰고 다음 step으로 진행한다
   - B) 실패한 experiment를 자동으로 재시도한다
   - C) Rollout이 abort되고 stable 버전이 유지된다
   - D) Rollout이 일시정지(pause) 상태로 대기한다

<details>
<summary>정답 보기</summary>

**정답: C) Rollout이 abort되고 stable 버전이 유지된다**

**설명:**
experiment step은 blocking step입니다. Experiment가 Successful로 끝나야만 다음 step으로 진행하고, Failed/Error면 Rollout이 abort되어 Degraded가 됩니다. Inconclusive는 별도로 InconclusiveExperiment pause를 설정하며, 원인 확인과 운영자 판단이 필요합니다. abort는 데이터베이스나 외부 부작용을 되돌리지 않습니다.

</details>

3. Rollout `demo-app`의 revision 2 업데이트에서 첫 번째 step(인덱스 0)의 experiment가 생성됐을 때, 이름 충돌이 없을 때 Experiment 기본 이름 형식으로 올바른 것은? (새 버전 PodTemplateHash는 `74d8d8b4fb`)
   - A) `demo-app-experiment-1`
   - B) `demo-app-74d8d8b4fb-2-0`
   - C) `experiment-demo-app-0-2`
   - D) `demo-app-2-0-74d8d8b4fb`

<details>
<summary>정답 보기</summary>

**정답: B) `demo-app-74d8d8b4fb-2-0`**

**설명:**
Experiment 이름은 `<Rollout명>-<새 버전 PodTemplateHash>-<revision>-<step 인덱스>` 규칙을 따릅니다. 이어서 만들어지는 ReplicaSet은 `<Experiment명>-<template명>`(예: `demo-app-74d8d8b4fb-2-0-baseline`), AnalysisRun은 `<Experiment명>-<analysis명>` 형식입니다.

</details>

4. 예제의 Service가 traffic-class=production을 선택하고 실험 Pod는 traffic-class=experiment일 때, 실험 Pod가 해당 Service에서 제외되는 이유는 무엇인가요?
   - A) 실험 Pod는 별도 네임스페이스에 생성되기 때문
   - B) 실험 Pod는 NetworkPolicy로 차단되기 때문
   - C) Service selector의 traffic-class 값이 실험 Pod label과 다르기 때문
   - D) 실험 Pod는 readinessProbe가 항상 실패하도록 설정되기 때문

<details>
<summary>정답 보기</summary>

**정답: C) Service selector의 traffic-class 값이 실험 Pod label과 다르기 때문**

**설명:**
예제는 명시적인 label/selector로 선택 집합을 분리합니다. app label만 선택하는 다른 Service가 있으면 실험 Pod도 선택할 수 있습니다. 트래픽을 의도적으로 보내려면 템플릿에 `service` 속성을 지정해 실험 전용 Service를 만들거나, trafficRouting이 구성된 Rollout에서 `weight`로 실제 트래픽 일부를 라우팅해야 합니다.

</details>

5. experiment 템플릿의 `weight` 필드로 실험 Pod에 실제 트래픽을 보내기 위한 전제 조건은 무엇인가요?
   - A) Rollout에 weighted Experiment를 지원하는 trafficRouting이 구성되어 있어야 한다
   - B) 템플릿의 replicas가 stable과 같아야 한다
   - C) AnalysisTemplate에 web provider가 있어야 한다
   - D) Experiment를 Rollout 없이 단독으로 생성해야 한다

<details>
<summary>정답 보기</summary>

**정답: A) Rollout에 weighted Experiment를 지원하는 trafficRouting이 구성되어 있어야 한다**

**설명:**
weight는 Rollout experiment step의 template별 필드입니다. ALB/Istio 등 해당 기능을 지원하는 router가 필요하며, 일반 canary 가중치 지원만으로 Experiment 분배 지원을 가정할 수 없습니다. trafficRouting 없이 트래픽을 보내려면 `service` 속성으로 실험 전용 Service를 만들어 직접 라우팅을 구성해야 합니다.

</details>

6. AnalysisTemplate 메트릭에서 `failureLimit: 1`로 설정했을 때 AnalysisRun 전체가 Failed가 되는 시점은 언제인가요?
   - A) 측정이 1번 실패한 즉시
   - B) 측정이 2번 실패했을 때 (failed > failureLimit)
   - C) 연속으로 1번 실패했을 때만
   - D) count로 지정한 전체 측정이 끝난 후에만

<details>
<summary>정답 보기</summary>

**정답: B) 측정이 2번 실패했을 때 (failed > failureLimit)**

**설명:**
`failureLimit`은 허용되는 실패 횟수입니다. 실패 횟수가 이 값을 초과하는 순간 AnalysisRun이 Failed로 판정됩니다. 1.10.0 구현의 비교식은 `failed > failureLimit`입니다. 같은 방식으로 `inconclusiveLimit` 초과는 Inconclusive, `consecutiveErrorLimit`(연속 수집 오류, 기본 4) 초과는 Error가 됩니다.

</details>

7. Experiment의 `duration` 타이머가 시작되는 시점은 언제인가요?
   - A) Experiment 리소스가 생성된 즉시
   - B) 첫 번째 AnalysisRun 측정이 성공한 시점
   - C) spec.templates의 모든 ReplicaSet이 healthy(available) 상태가 된 시점
   - D) Rollout이 experiment step에 도달하기 직전

<details>
<summary>정답 보기</summary>

**정답: C) spec.templates의 모든 ReplicaSet이 healthy(available) 상태가 된 시점**

**설명:**
Experiment 컨트롤러는 먼저 템플릿별 ReplicaSet을 만들고 모든 Pod가 available이 될 때까지 기다립니다. duration 타이머와 AnalysisRun 생성은 그 이후에 시작되므로, Pod 기동이 느려도 실험 시간이 잠식되지 않습니다.

</details>

8. Experiment가 종료(성공/실패 무관)되었을 때 실험용 ReplicaSet에는 어떤 일이 일어나나요?
   - A) 다음 실험을 위해 유지된다
   - B) 0으로 스케일 다운되고, `service` 속성으로 만든 Service도 정리된다
   - C) stable ReplicaSet으로 승격된다
   - D) 수동으로 삭제할 때까지 남아 있는다

<details>
<summary>정답 보기</summary>

**정답: B) 0으로 스케일 다운되고, `service` 속성으로 만든 Service도 정리된다**

**설명:**
Experiment는 일회성 리소스입니다. 종료 조건을 만족하면 기본 30초 scale-down 지연 후 ReplicaSet이 0으로 축소되고, available replica가 0인 것을 확인한 뒤 생성 Service를 정리합니다. ReplicaSet/AnalysisRun 객체는 보존 정책에 따라 남을 수 있습니다. Successful은 진행, Failed/Error는 abort, Inconclusive는 pause입니다.

</details>
