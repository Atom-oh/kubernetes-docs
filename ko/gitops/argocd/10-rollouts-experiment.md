# Argo Rollouts Experiment 심층 분석

> **지원 버전**: Argo Rollouts 1.10.0 (과거 1.8.3/Kubernetes 1.33 기록은 별도 표기)
> **마지막 업데이트**: 2026년 9월 11일

## 목차

- [Experiment란?](#experiment란)
- [리소스 계층과 생성 체인](#리소스-계층과-생성-체인)
- [이름 생성 규칙](#이름-생성-규칙)
- [트래픽 라우팅 동작](#트래픽-라우팅-동작)
- [측정과 판정: AnalysisRun](#측정과-판정-analysisrun)
- [결과 전파와 Rollout 상태 전이](#결과-전파와-rollout-상태-전이)
- [실사용 예시](#실사용-예시)
- [kubectl 플러그인으로 관찰하기](#kubectl-플러그인으로-관찰하기)
- [실측 검증 결과](#실측-검증-결과)
- [다음 단계](#다음-단계)
- [참고 자료](#참고-자료)
- [퀴즈](#퀴즈)

## Experiment란?

Experiment는 일회성 ReplicaSet들을 만들고 분석을 실행하는 Argo Rollouts CRD입니다. baseline/canary 비교, 사전 검증, 실제 트래픽을 사용하는 실험 등에 사용할 수 있습니다. **새 ReplicaSet을 만든다는 것만으로 프로덕션 트래픽에서 격리되지는 않습니다.** Service 셀렉터와 라우터·테스트 트래픽을 명시적으로 설계해야 합니다.

| 구분 | Canary step | Experiment step |
|---|---|---|
| Pod | Rollout의 canary ReplicaSet | Experiment의 임시 ReplicaSet |
| 트래픽 | basic canary는 Pod 비율 근사, 라우터가 있으면 가중치 제어 | Service/라우터 설정에 따라 격리 또는 실트래픽 수신 |
| 종료 | 새 stable로 승격 가능 | 종료 후 지연 정책에 따라 replicas 0으로 축소 |
| 분석 | 버전별 품질 지표 | 별도 baseline/canary 지표·테스트 트래픽 필요 |

단독 `Experiment`와 Rollout의 `experiment` step을 모두 지원합니다. `specRef`와 `weight`는 **Rollout step 템플릿**의 필드입니다. 단독 Experiment는 selector/Pod template을 직접 정의합니다.

## 리소스 계층과 생성 체인

Rollout이 experiment step에 도달하면 아래 체인으로 리소스가 생성됩니다.

![Rollout이 생성하는 Experiment가 baseline·canary ReplicaSet과 AnalysisRun을 만들고, AnalysisTemplate이 templateName으로 AnalysisRun에 참조되는 구조를 보여준다.](../../.gitbook/assets/ko-gitops-argocd-10-rollouts-experiment-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-gitops-argocd-10-rollouts-experiment-0.html)

1. Rollout 업데이트가 experiment step에 도달하면 Experiment를 생성합니다. 첫 배포는 stable을 확립하며 일반 canary step을 건너뛰므로 **다음 Pod template 변경**에서 실험을 관찰합니다.
2. template별 ReplicaSet을 만들고 지정된 replica 수가 available이 되기를 기다립니다. readiness/minReadySeconds가 중요하며 progress deadline을 넘기면 실패합니다.
3. 모두 available이 되면 `status.availableAt`을 기록하고 분석을 시작합니다. `duration`을 설정했다면 이 시점부터 계산합니다.
4. 종료 조건에 따라 결과를 전파합니다. Successful은 진행, Failed/Error는 abort, **Inconclusive는 pause**입니다. 실험 ReplicaSet과 Service는 별도 정리 과정을 거칩니다.

## 이름 생성 규칙

Experiment 계열 리소스는 이름만 봐도 어느 Rollout의 몇 번째 revision, 몇 번째 step에서 나왔는지 추적할 수 있도록 규칙적으로 명명됩니다.

| 리소스 | 규칙 | 실측 예시 |
|--------|------|-----------|
| Experiment | `<Rollout명>-<새 버전 PodTemplateHash>-<revision>-<step 인덱스>` | `demo-app-74d8d8b4fb-2-0` |
| ReplicaSet | `<Experiment명>-<template명>` | `demo-app-74d8d8b4fb-2-0-baseline`, `demo-app-74d8d8b4fb-2-0-canary` |
| AnalysisRun | `<Experiment명>-<analysis명>` | `demo-app-74d8d8b4fb-2-0-success-rate` |

위 예시는 `demo-app` Rollout의 revision 2 업데이트에서 step 인덱스 0(첫 번째 step)의 experiment가 만든 리소스들입니다. [실측 검증 결과](#실측-검증-결과)의 트리 출력에서 실제 계층을 확인할 수 있습니다.

위 규칙은 기본 이름입니다. Experiment/AnalysisRun 이름 충돌 시 숫자 suffix가 붙을 수 있으므로 ownerReferences와 status에서 실제 리소스를 확인합니다.

## 트래픽 라우팅 동작

Production Service가 `app: demo-app`만 선택하면 실험 Pod도 선택할 수 있습니다. hash가 포함된 selector의 실제 값도 확인해야 하며, 별도 해시가 항상 충분한 격리를 보장한다고 가정하지 않습니다. 아래 예제는 production Service에 `traffic-class: production`을 요구하고 실험 템플릿에서 `traffic-class: experiment`로 덮어써 선택 집합을 분리합니다. 다른 Service나 mesh 경로도 함께 확인합니다.

다음은 Rollout `spec.strategy.canary.steps`에 넣는 **대안 두 가지**입니다. Service 생성만으로 외부 트래픽이 자동 연결되지는 않습니다.

```yaml
- experiment:
    duration: 1m
    templates:
    - name: baseline
      specRef: stable
      service: {}
    - name: canary
      specRef: canary
      service: {}
```

```yaml
- experiment:
    duration: 1m
    templates:
    - name: baseline
      specRef: stable
      weight: 5
    - name: canary
      specRef: canary
      weight: 5
```

- `service: {}`는 해당 템플릿 전용 Service를 생성합니다. 기본 이름은 ReplicaSet 이름이며 `service.name`으로 바꿀 수 있습니다. 컨테이너의 실제 listen port와 선언된 `containerPort`가 일치해야 합니다.
- `weight`는 template별 필드이며 기본 총 가중치 100에서 각각 5%를 뜻합니다. 사용자 지정 `maxTrafficWeight`를 쓰면 단위를 함께 확인합니다. 가중치가 있으면 Service도 생성됩니다.
- weighted Experiment는 해당 기능을 지원하는 router가 필요합니다. 1.10 문서는 ALB/Istio/SMI를 명시합니다. 일반 canary 가중치를 지원한다는 이유만으로 NGINX나 모든 플러그인이 Experiment 분배까지 지원하는 것은 아닙니다.

## 측정과 판정: AnalysisRun

AnalysisRun은 provider 결과를 조건식으로 평가합니다. 아래는 **AnalysisTemplate spec 조각**이며 전체 provider 설정은 뒤의 예제에 있습니다. 성공률이 없거나 범위를 벗어나면 양쪽 조건이 false여서 Inconclusive가 됩니다. 잘못된 타입·HTTP/수집·조건 평가 오류는 Error 경로입니다.

```yaml
metrics:
- name: success-rate
  interval: 15s
  count: 3
  successCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil &&
    asFloat(payload.success_rate) >= 0.95 && asFloat(payload.success_rate) <= 1
  failureCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil &&
    asFloat(payload.success_rate) >= 0 && asFloat(payload.success_rate) < 0.95
  failureLimit: 1
  inconclusiveLimit: 1
  consecutiveErrorLimit: 2
```

| 조건 | 측정 판정 |
|---|---|
| failureCondition=true | Failed (성공 조건보다 우선) |
| successCondition=true, failureCondition=false | Successful |
| 두 조건 모두 false | Inconclusive |
| provider 또는 조건식 오류 | Error |

성공 조건만 쓰면 그 조건이 false인 측정은 Failed입니다. 실패 조건만 쓰면 그 조건이 false인 측정은 Successful입니다. 두 조건 모두 생략하면 수집 오류가 없는 측정은 Successful입니다.

| 필드 | 의미 | 한도 초과 시 |
|---|---|---|
| failureLimit | 허용 Failed 측정 수 | Failed |
| inconclusiveLimit | 허용 Inconclusive 측정 수 | Inconclusive |
| consecutiveErrorLimit | 허용 연속 Error 수 (기본 4) | Error |

`failureLimit: 1`은 두 번째 실패 측정에서 한도를 초과합니다. `count`는 HTTP 요청 수가 아니라 분석 측정 수입니다. interval만 지정하고 count를 생략하면 무기한, 둘 다 생략하면 1회입니다. 기간이 겹치는 메트릭 조회 3회는 독립 표본 3개를 뜻하지 않습니다.

## 결과 전파와 Rollout 상태 전이

![Experiment 결과별로 Successful은 다음 step, Failed/Error는 abort, Inconclusive는 pause로 분기하며 정리는 지연 정책을 따른다.](../../.gitbook/assets/ko-gitops-argocd-10-rollouts-experiment-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-gitops-argocd-10-rollouts-experiment-1.html)

| Experiment 결과 | Rollout 동작 |
|---|---|
| Successful | 다음 step 진행 |
| Failed / Error | abort, Degraded; 구성된 라우팅/replica 정책으로 stable 복구 |
| Inconclusive | `InconclusiveExperiment` pause; 원인 확인과 운영자 판단 필요 |

1.10 구현에서는 `duration`과 분석을 무조건 AND 조건으로 기다리지 않습니다. 필수 분석(`requiredForCompletion: true`)이 모두 성공하면 duration보다 일찍 끝날 수 있습니다. 필수 분석이 남으면 기간 이후에도 기다릴 수 있으며, 필수가 아닌 분석은 duration 종료 시 중단될 수 있습니다. duration도 필수 분석도 없으면 명시적으로 종료할 때까지 계속 실행됩니다. 아래 예제는 duration을 생략하고 유한 count의 필수 분석으로 완료를 결정합니다.

`scaleDownDelaySeconds` 기본값은 30초입니다. 종료 판정과 Pod 0개/Service 삭제가 같은 순간이라고 보장하지 않습니다. 컨트롤러는 지연 이후 ReplicaSet을 축소하고 available replica가 0이 된 후 생성한 Service를 정리합니다. ReplicaSet/AnalysisRun 객체는 기록 보존·GC 정책에 따라 남을 수 있습니다. abort가 DB 변경이나 외부 부작용을 되돌리지는 않습니다.

## 실사용 예시

다음은 **교육용 상태 전이 예제**입니다. Rollouts 1.10.0/CRD와 플러그인이 설치되어 있어야 하며, `demo` namespace에 아래 JSON을 반환하는 `metrics-mock` HTTP Service를 별도로 준비해야 합니다. 그 서버 구현은 포함하지 않았으므로 manifest만 적용해도 성공한다는 의미가 아닙니다. 고정 mock 값은 baseline/canary의 실제 품질이나 트래픽 비율을 검증하지 않습니다.

```json
{"status":"ok","success_rate":0.99}
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo
---
apiVersion: v1
kind: Service
metadata:
  name: demo-production
  namespace: demo
spec:
  selector:
    app: demo-app
    traffic-class: production
  ports:
  - name: http
    port: 9898
    targetPort: http
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-check
  namespace: demo
spec:
  metrics:
  - name: success-rate
    interval: 15s
    count: 3
    successCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil
      && asFloat(payload.success_rate) >= 0.95 && asFloat(payload.success_rate) <= 1
    failureCondition: let payload = default(result, {}); payload?.status == 'ok' && payload?.success_rate != nil
      && asFloat(payload.success_rate) >= 0 && asFloat(payload.success_rate) < 0.95
    failureLimit: 1
    inconclusiveLimit: 1
    consecutiveErrorLimit: 2
    provider:
      web:
        url: http://metrics-mock.demo.svc.cluster.local/metrics.json
        jsonPath: '{$}'
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-app
  namespace: demo
spec:
  replicas: 3
  revisionHistoryLimit: 3
  progressDeadlineSeconds: 180
  selector:
    matchLabels:
      app: demo-app
  strategy:
    canary:
      steps:
      - experiment:
          scaleDownDelaySeconds: 30
          templates:
          - name: baseline
            specRef: stable
            replicas: 1
            metadata:
              labels:
                traffic-class: experiment
                experiment-role: baseline
            service: {}
          - name: canary
            specRef: canary
            replicas: 1
            metadata:
              labels:
                traffic-class: experiment
                experiment-role: canary
            service: {}
          analyses:
          - name: success-rate
            templateName: success-rate-check
            requiredForCompletion: true
      - setWeight: 20
      - pause:
          duration: 10s
  template:
    metadata:
      labels:
        app: demo-app
        traffic-class: production
      annotations:
        demo-revision: v1
    spec:
      containers:
      - name: app
        image: ghcr.io/stefanprodan/podinfo:6.15.0
        ports:
        - name: http
          containerPort: 9898
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
```

파일을 적용하고 첫 stable이 준비된 뒤, 별도 실습 클러스터에서 아래와 같이 Pod template annotation을 바꾸면 experiment step을 관찰할 수 있습니다. 이 변경은 새 이미지 품질 검증이 아니라 컨트롤러 흐름 확인용입니다. Argo CD 관리 대상은 직접 patch 대신 Git 변경으로 진행합니다. mock이 0.99면 성공, 0.50이면 failureLimit을 넘겨 abort, 필드가 없으면 Inconclusive pause 경로를 관찰합니다. 테스트 종료 후 실습 리소스 정리 범위를 확인합니다.

```bash
kubectl argo rollouts status demo-app -n demo --timeout=180s
# A second Pod-template revision exercises the steps; the image stays unchanged in this demo.
kubectl patch rollout demo-app -n demo --type merge \
  -p '{"spec":{"template":{"metadata":{"annotations":{"demo-revision":"v2"}}}}}'
kubectl argo rollouts get rollout demo-app -n demo --watch
```

`setWeight: 20`은 trafficRouting이 없는 이 예제에서 Pod 비율 근사입니다. replicas 3개로 정확한 사용자 요청 20%를 보장하지 않습니다. 실제 비교 분석은 테스트 트래픽·계측·scrape·충분한 표본과 다음 **Experiment ReplicaSet** 해시 인자를 연결해야 합니다. `podTemplateHashValue: Baseline/Canary`를 쓰는 필드가 아닙니다.

```yaml
args:
- name: baseline-hash
  value: '{{templates.baseline.podTemplateHash}}'
- name: canary-hash
  value: '{{templates.canary.podTemplateHash}}'
```

[실제 지표 비교 예제](05-traffic-management.md#experiment)를 함께 확인하세요.

## kubectl 플러그인으로 관찰하기

`kubectl argo rollouts get rollout <이름> --watch`로 Experiment의 전체 계층(Experiment → ReplicaSet → Pod, AnalysisRun)을 실시간으로 볼 수 있습니다. 아래는 원문에 남아 있던 1.8.3 실행 기록입니다. 현재 예제의 신규 실행 결과가 아니며 이름·시간·정리 시점을 1.10.0 결과로 해석하지 않습니다.

```
$ kubectl argo rollouts get rollout demo-app -n demo
Name:            demo-app
Namespace:       demo
Status:          ◌ Progressing
Strategy:        Canary
  Step:          0/3
  SetWeight:     0
  ActualWeight:  0

NAME                                                  KIND         STATUS         AGE  INFO
⟳ demo-app                                            Rollout      ◌ Progressing  51s
├──# revision:2
│  ├──⧉ demo-app-74d8d8b4fb                           ReplicaSet   • ScaledDown   29s  canary
│  └──Σ demo-app-74d8d8b4fb-2-0                       Experiment   ◌ Running      29s
│     ├──⧉ demo-app-74d8d8b4fb-2-0-baseline           ReplicaSet   ✔ Healthy      29s
│     │  └──□ demo-app-74d8d8b4fb-2-0-baseline-gvgnq  Pod          ✔ Running      29s  ready:1/1
│     ├──⧉ demo-app-74d8d8b4fb-2-0-canary             ReplicaSet   ✔ Healthy      29s
│     │  └──□ demo-app-74d8d8b4fb-2-0-canary-jq6lb    Pod          ✔ Running      29s  ready:1/1
│     └──α demo-app-74d8d8b4fb-2-0-success-rate       AnalysisRun  ◌ Running      29s  ✔ 2
└──# revision:1
   └──⧉ demo-app-779c8779bf                           ReplicaSet   ✔ Healthy      51s  stable
```

이 과거 기록에서는 revision 2의 본 ReplicaSet이 ScaledDown이었습니다. 다른 step 배치나 Service/라우터 설정에서도 새 버전의 프로덕션 노출이 없다고 일반화할 수는 없습니다. AnalysisRun의 측정 내역은 status에 그대로 남아 사후 분석에 쓸 수 있습니다.

```
$ kubectl get analysisrun demo-app-74d8d8b4fb-2-0-success-rate -n demo \
    -o jsonpath='{.status.metricResults[0]}' | python3 -m json.tool
{
    "consecutiveSuccess": 2,
    "count": 2,
    "measurements": [
        {
            "finishedAt": "2026-07-17T01:24:09Z",
            "phase": "Successful",
            "value": "{\"error_rate\":0.004,\"status\":\"ok\",\"success_rate\":0.99}"
        },
        ...
    ],
    "name": "success-rate",
    "phase": "Running",
    "successful": 2
}
```

## 실측 검증 결과

원문은 1.8.3 소스 빌드와 Kubernetes 1.33/kwok(API 컨트롤 플레인은 실제 바이너리, 노드·Pod 수명주기는 시뮬레이션)에서 아래 결과를 얻었다고 기록했습니다. 실행 manifest 전체·원시 API dump·로그가 첨부되어 있지 않아 이번 검토에서는 재현하지 못했습니다. 아래는 과거 보고이며, 1.10.0 신규 검증이나 실제 트래픽/Pod readiness·애플리케이션 품질 증거가 아닙니다.

| 과거 보고 항목 | 원문 기록 |
|-----------|------|
| experiment step 도달 시 Experiment 자동 생성, 이름 = `<Rollout명>-<PodHash>-<revision>-<step>` | 보고: `demo-app-74d8d8b4fb-2-0` (revision 2, step 0) |
| templates 기반 ReplicaSet 생성, 이름 = `<Experiment명>-<template명>` | 보고: `...-2-0-baseline`, `...-2-0-canary` 각 1 replica |
| `service: {}` 지정 템플릿의 실험 전용 Service 생성/정리 | 보고: `...-2-0-canary` Service 생성, 실험 종료 후 삭제 확인 |
| 모든 템플릿 healthy 후 AnalysisRun 생성, `interval: 15s`/`count: 3` 반복 측정 | 보고: 15초 간격 measurements 3회 기록, `successCondition` 평가 Successful |
| 성공 경로: duration 60s 경과 → Experiment Successful → 실험 RS 0으로 스케일 다운 → 다음 step(setWeight 20) 진행 → Rollout Healthy | 보고: 정상 |
| 실패 경로: 메트릭 악화 시 `failed (2) > failureLimit (1)`로 AnalysisRun Failed → Experiment Failed → Rollout abort (Degraded), stable 유지 | 보고: 정상 — abort 메시지가 원인 메트릭을 그대로 표기 |

## 다음 단계

1. **[트래픽 관리](05-traffic-management.md)**: 카나리/블루그린 전략과 인그레스 통합 속에서 experiment step을 조합하세요.

2. **[모범 사례](09-best-practices.md)**: 프로그레시브 딜리버리 운영 모범 사례를 학습하세요.

## 참고 자료

- [Experiment 공식 문서](https://argoproj.github.io/argo-rollouts/features/experiment/)
- [Analysis 공식 문서](https://argoproj.github.io/argo-rollouts/features/analysis/)
- [Experiment CRD 스펙](https://argoproj.github.io/argo-rollouts/features/specification/)


- [1.10.0 Experiment state machine](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/experiment.go)
- [1.10.0 Rollout pause/abort handling](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/rollout/experiment.go)
- [1.10.0 ReplicaSet cleanup](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/experiments/replicaset.go)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [Rollouts Experiment 퀴즈](../../quizzes/gitops/argocd/10-rollouts-experiment-quiz.md)를 풀어보세요.
