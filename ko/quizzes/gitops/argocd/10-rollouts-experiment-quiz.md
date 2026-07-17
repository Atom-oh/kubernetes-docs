# Argo Rollouts Experiment 퀴즈

이 퀴즈는 Argo Rollouts Experiment CRD의 리소스 계층, 트래픽 격리, 분석 판정, 결과 전파에 대한 이해도를 테스트합니다.

1. Experiment CRD의 핵심 용도는 무엇인가요?
   - A) 프로덕션 트래픽 전체를 새 버전으로 전환
   - B) 프로덕션 트래픽과 분리된 일회성 ReplicaSet으로 새 버전 검증
   - C) Rollout의 revision 히스토리 보관
   - D) 클러스터 노드의 부하 테스트

<details>
<summary>정답 보기</summary>

**정답: B) 프로덕션 트래픽과 분리된 일회성 ReplicaSet으로 새 버전 검증**

**설명:**
Experiment는 일회성(ephemeral) ReplicaSet을 잠깐 띄웠다가 종료 시 0으로 스케일 다운하는 리소스입니다. 기본적으로 실험 Pod는 프로덕션 Service 트래픽을 받지 않으므로, 실제 사용자 영향 없이 baseline과 canary를 비교 검증할 수 있습니다.

</details>

2. Rollout의 canary 전략에서 experiment step이 실패하면 어떻게 되나요?
   - A) 해당 step만 건너뛰고 다음 step으로 진행한다
   - B) 실패한 experiment를 자동으로 재시도한다
   - C) Rollout이 abort되고 stable 버전이 유지된다
   - D) Rollout이 일시정지(pause) 상태로 대기한다

<details>
<summary>정답 보기</summary>

**정답: C) Rollout이 abort되고 stable 버전이 유지된다**

**설명:**
experiment step은 blocking step입니다. Experiment가 Successful로 끝나야만 다음 step으로 진행하고, Failed/Inconclusive로 끝나면 Rollout이 abort되어 Degraded 상태가 되며 stable 버전이 그대로 유지됩니다.

</details>

3. Rollout `demo-app`의 revision 2 업데이트에서 첫 번째 step(인덱스 0)의 experiment가 생성됐을 때, Experiment 이름 형식으로 올바른 것은? (새 버전 PodTemplateHash는 `74d8d8b4fb`)
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

4. 아무 추가 설정 없이 experiment를 실행할 때, 실험 Pod가 프로덕션 트래픽을 받지 않는 이유는 무엇인가요?
   - A) 실험 Pod는 별도 네임스페이스에 생성되기 때문
   - B) 실험 Pod는 NetworkPolicy로 차단되기 때문
   - C) 실험 Pod의 `rollouts-pod-template-hash` label 값이 stable Pod와 달라 Service 셀렉터에 걸리지 않기 때문
   - D) 실험 Pod는 readinessProbe가 항상 실패하도록 설정되기 때문

<details>
<summary>정답 보기</summary>

**정답: C) 실험 Pod의 `rollouts-pod-template-hash` label 값이 stable Pod와 달라 Service 셀렉터에 걸리지 않기 때문**

**설명:**
기본 격리는 label 기반입니다. 트래픽을 의도적으로 보내려면 템플릿에 `service` 속성을 지정해 실험 전용 Service를 만들거나, trafficRouting이 구성된 Rollout에서 `weight`로 실제 트래픽 일부를 라우팅해야 합니다.

</details>

5. experiment 템플릿의 `weight` 필드로 실험 Pod에 실제 트래픽을 보내기 위한 전제 조건은 무엇인가요?
   - A) Rollout에 trafficRouting이 구성되어 있어야 한다
   - B) 템플릿의 replicas가 stable과 같아야 한다
   - C) AnalysisTemplate에 web provider가 있어야 한다
   - D) Experiment를 Rollout 없이 단독으로 생성해야 한다

<details>
<summary>정답 보기</summary>

**정답: A) Rollout에 trafficRouting이 구성되어 있어야 한다**

**설명:**
weight 기반 트래픽 분배는 Istio, ALB, NGINX 같은 트래픽 제공자가 비율을 실제로 나눠줄 수 있어야 하므로, trafficRouting이 구성된 Rollout에서만 동작합니다. trafficRouting 없이 트래픽을 보내려면 `service` 속성으로 실험 전용 Service를 만들어 직접 라우팅을 구성해야 합니다.

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
`failureLimit`은 허용되는 실패 횟수입니다. 실패 횟수가 이 값을 초과하는 순간 AnalysisRun이 Failed로 판정됩니다. 실측에서도 `Metric "success-rate" assessed Failed due to failed (2) > failureLimit (1)` 메시지와 함께 2번째 실패에서 Failed 처리되었습니다. 같은 방식으로 `inconclusiveLimit` 초과는 Inconclusive, `consecutiveErrorLimit`(연속 수집 오류, 기본 4) 초과는 Error가 됩니다.

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
Experiment는 일회성 리소스입니다. duration 경과 또는 분석 종료 시 baseline/canary ReplicaSet은 모두 0으로 스케일 다운되고 실험 전용 Service도 함께 삭제됩니다. 결과(Successful/Failed)만 Rollout에 전파되어 다음 step 진행 또는 abort를 결정합니다.

</details>
