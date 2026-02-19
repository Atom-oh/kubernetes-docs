# Kubernetes 확장 메커니즘 퀴즈

> **관련 문서**: [Kubernetes 확장 메커니즘](../../platform/02-kubernetes-extensions.md)

## 객관식 문제

### 1. CRD(Custom Resource Definition)의 주요 목적은 무엇입니까?

- A) 기존 Kubernetes 리소스를 수정
- B) Kubernetes API를 확장하여 사용자 정의 리소스를 정의
- C) 파드의 네트워크를 구성
- D) 스토리지 볼륨을 프로비저닝

<details>
<summary>정답 보기</summary>

**정답: B) Kubernetes API를 확장하여 사용자 정의 리소스를 정의**

**설명:**
CRD는 Kubernetes API를 확장하여 네이티브 Kubernetes 리소스처럼 동작하는 사용자 정의 리소스 유형을 정의할 수 있게 해줍니다.

</details>

### 2. 커스텀 컨트롤러의 조정 루프(Reconciliation Loop)에서 수행하는 주요 작업은?

- A) 리소스를 즉시 삭제
- B) 현재 상태와 원하는 상태의 차이를 조정
- C) API 서버에 새로운 API를 등록
- D) 네트워크 정책을 적용

<details>
<summary>정답 보기</summary>

**정답: B) 현재 상태와 원하는 상태의 차이를 조정**

**설명:**
커스텀 컨트롤러의 조정 루프는 리소스의 현재 상태를 관찰하고, 원하는 상태(spec)와 비교하여 차이가 있으면 원하는 상태를 달성하기 위한 조치를 취합니다.

</details>

### 3. Operator 패턴의 핵심 구성 요소는?

- A) Deployment와 Service
- B) CRD와 커스텀 컨트롤러
- C) ConfigMap과 Secret
- D) Ingress와 NetworkPolicy

<details>
<summary>정답 보기</summary>

**정답: B) CRD와 커스텀 컨트롤러**

**설명:**
Operator 패턴은 CRD로 애플리케이션의 구성을 정의하고, 커스텀 컨트롤러로 애플리케이션의 배포, 업그레이드, 복구 등 운영 지식을 자동화합니다.

</details>

### 4. MutatingAdmissionWebhook의 주요 용도는?

- A) API 요청을 거부
- B) API 요청을 수정
- C) API 응답을 로깅
- D) API 버전을 업그레이드

<details>
<summary>정답 보기</summary>

**정답: B) API 요청을 수정**

**설명:**
MutatingAdmissionWebhook은 API 요청이 저장되기 전에 요청을 수정할 수 있습니다. 일반적인 용도: 사이드카 컨테이너 주입, 기본값 설정 등입니다.

</details>

### 5. 스케줄러 프레임워크의 Filter 플러그인의 역할은?

- A) 노드에 점수를 부여
- B) 파드를 실행할 수 없는 노드를 제외
- C) 파드를 노드에 바인딩
- D) 노드의 리소스를 예약

<details>
<summary>정답 보기</summary>

**정답: B) 파드를 실행할 수 없는 노드를 제외**

**설명:**
Filter 플러그인은 파드의 요구사항을 충족하지 못하는 노드를 필터링하여 제외합니다.

</details>

### 6. Aggregated API Server와 CRD의 차이점은?

- A) 차이 없음, 동일함
- B) Aggregated API는 더 많은 제어를 제공하지만 별도 서버 실행 필요
- C) CRD가 Aggregated API보다 더 많은 기능 제공
- D) Aggregated API는 더 이상 사용되지 않음

<details>
<summary>정답 보기</summary>

**정답: B) Aggregated API는 더 많은 제어를 제공하지만 별도 서버 실행 필요**

**설명:**
Aggregated API Server는 API 동작, 커스텀 스토리지 백엔드, 고급 기능에 대한 완전한 제어를 제공하지만 별도의 API 서버를 배포하고 유지 관리해야 합니다. CRD는 더 간단하지만 제한이 있습니다.

</details>

### 7. Kubernetes에서 Finalizer의 목적은?

- A) 리소스 삭제 속도 향상
- B) 정리가 완료될 때까지 리소스 삭제 방지
- C) 실패한 파드 자동 재시작
- D) 리소스 생성 검증

<details>
<summary>정답 보기</summary>

**정답: B) 정리가 완료될 때까지 리소스 삭제 방지**

**설명:**
Finalizer는 컨트롤러가 필요한 정리 작업(외부 리소스 삭제 등)을 수행하고 finalizer를 제거할 때까지 리소스 삭제를 차단합니다.

</details>

### 8. 파드가 노드에 바인딩된 후 실행되는 스케줄러 확장 지점은?

- A) PreFilter
- B) PostBind
- C) Reserve
- D) Score

<details>
<summary>정답 보기</summary>

**정답: B) PostBind**

**설명:**
PostBind 플러그인은 파드가 노드에 성공적으로 바인딩된 후 호출됩니다. 정보 제공용이며 정리나 알림에 사용됩니다.

</details>

### 9. Istio에서 어드미션 웹훅을 통해 사이드카를 주입하는 데 사용되는 어노테이션은?

- A) istio.io/inject
- B) sidecar.istio.io/inject
- C) istio-injection
- D) auto-inject.istio.io

<details>
<summary>정답 보기</summary>

**정답: B) sidecar.istio.io/inject**

**설명:**
`sidecar.istio.io/inject` 어노테이션은 Istio의 mutating 웹훅이 파드에 Envoy 사이드카를 주입할지 제어합니다. 네임스페이스 수준 제어는 `istio-injection` 레이블을 사용합니다.

</details>

### 10. 스케줄러 프레임워크에서 Score 플러그인의 목적은?

- A) 부적합한 노드 필터링
- B) 노드 순위 지정 및 최적 노드 선택
- C) 선택된 노드에 파드 바인딩
- D) 파드 사양 검증

<details>
<summary>정답 보기</summary>

**정답: B) 노드 순위 지정 및 최적 노드 선택**

**설명:**
Score 플러그인은 필터링을 통과한 노드에 점수를 할당합니다. 스케줄러는 모든 Score 플러그인에서 가장 높은 합산 점수를 가진 노드를 선택합니다.

</details>

## 단답형 문제

### 1. CRD에서 스키마 검증에 사용되는 표준은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: OpenAPI v3 Schema (openAPIV3Schema)**

**설명:**
CRD의 `spec.versions[].schema.openAPIV3Schema`에서 OpenAPI v3 스키마를 사용하여 커스텀 리소스의 구조와 유효성 검사 규칙을 정의합니다.

</details>

### 2. Kubernetes 컨트롤러에서 Owner Reference의 역할은?

<details>
<summary>정답 보기</summary>

**정답: 리소스 간 소유 관계를 정의하여 가비지 컬렉션과 이벤트 전파를 관리**

**설명:**
Owner Reference는 부모-자식 관계를 정의하고, 부모 삭제 시 Kubernetes 가비지 컬렉션을 통해 자식을 자동 삭제합니다.

</details>

### 3. ValidatingAdmissionPolicy와 ValidatingAdmissionWebhook의 차이점은?

<details>
<summary>정답 보기</summary>

**정답: ValidatingAdmissionPolicy는 CEL 표현식을 사용하고 프로세스 내에서 실행되며, ValidatingAdmissionWebhook은 외부 HTTP 엔드포인트를 호출합니다.**

**설명:**
ValidatingAdmissionPolicy(1.26에서 도입)는 더 나은 성능을 제공하고 외부 웹훅 인프라가 필요 없지만, 웹훅보다 유연성이 떨어집니다.

</details>

### 4. controller-runtime 라이브러리란 무엇이며 왜 일반적으로 사용됩니까?

<details>
<summary>정답 보기</summary>

**정답: controller-runtime은 클라이언트 캐싱, 리더 선출, 조정 루프 관리를 포함하여 Kubernetes 컨트롤러 구축을 위한 공통 패턴을 제공하는 라이브러리입니다.**

**설명:**
Kubebuilder 프로젝트의 일부인 controller-runtime은 보일러플레이트 코드와 모범 사례를 추상화하여 신뢰할 수 있는 operator를 더 쉽게 구축할 수 있게 합니다.

</details>

### 5. CRD에서 conversion 웹훅의 목적은?

<details>
<summary>정답 보기</summary>

**정답: Conversion 웹훅은 동일한 CRD의 다른 API 버전 간에 리소스를 변환합니다.**

**설명:**
CRD에 여러 버전(예: v1alpha1, v1beta1, v1)이 있는 경우, conversion 웹훅은 API 진화를 지원하기 위해 버전 간 변환을 처리합니다.

</details>

## 실습 문제

### 1. 다음 요구사항을 충족하는 CRD를 작성하세요.

- 이름: WebApp
- 그룹: apps.example.com
- 필드: replicas (정수, 최소 1), image (문자열, 필수)

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames:
      - wa
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["image"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  default: 1
                image:
                  type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Available
          type: integer
          jsonPath: .status.availableReplicas
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

</details>

### 2. "production" 네임스페이스의 모든 Deployment를 검증하는 ValidatingAdmissionWebhook 구성을 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: deployment-validator
webhooks:
  - name: validate-deployment.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: webhook-system
        path: /validate-deployment
      caBundle: <base64-encoded-ca-cert>
    rules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
        scope: Namespaced
    namespaceSelector:
      matchLabels:
        environment: production
    failurePolicy: Fail
    sideEffects: None
    admissionReviewVersions: ["v1"]
    timeoutSeconds: 10
```

**설명:**
- `namespaceSelector`는 `environment: production` 레이블이 있는 네임스페이스로 웹훅을 제한
- `failurePolicy: Fail`은 웹훅을 사용할 수 없을 때 요청을 거부
- `sideEffects: None`은 웹훅에 부작용이 없음을 나타냄

</details>

### 3. 커스텀 컨트롤러의 간단한 조정 루프 의사 코드를 작성하세요.

<details>
<summary>정답 보기</summary>

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. WebApp 리소스 가져오기
    var webapp appsv1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        if errors.IsNotFound(err) {
            // 리소스 삭제됨, 할 일 없음
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. 삭제 중인지 확인 (finalizer 처리)
    if !webapp.DeletionTimestamp.IsZero() {
        if containsFinalizer(webapp, finalizerName) {
            // 정리 수행
            if err := r.cleanupExternalResources(&webapp); err != nil {
                return ctrl.Result{}, err
            }
            // finalizer 제거
            removeFinalizer(&webapp, finalizerName)
            if err := r.Update(ctx, &webapp); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // 3. finalizer가 없으면 추가
    if !containsFinalizer(webapp, finalizerName) {
        addFinalizer(&webapp, finalizerName)
        if err := r.Update(ctx, &webapp); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Deployment 생성 또는 업데이트
    deployment := r.constructDeployment(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, deployment); err != nil {
        return ctrl.Result{}, err
    }

    // 5. Service 생성 또는 업데이트
    service := r.constructService(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, service, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, service); err != nil {
        return ctrl.Result{}, err
    }

    // 6. 상태 업데이트
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
    if err := r.Status().Update(ctx, &webapp); err != nil {
        return ctrl.Result{}, err
    }

    // 7. 주기적 조정을 위해 재큐
    return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}
```

**핵심 포인트:**
- 항상 리소스를 찾을 수 없는 경우 처리 (삭제되었을 수 있음)
- 외부 리소스 정리를 위해 finalizer 사용
- 가비지 컬렉션을 위해 소유자 참조 설정
- 상태 하위 리소스를 별도로 업데이트
- 주기적 검사를 위한 재큐 간격 고려

</details>

## 심화 문제

### 1. 복잡한 분산 시스템을 위한 Kubernetes Operator를 설계하세요.

<details>
<summary>정답 보기</summary>

**CRD 설계:**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.database.example.com
spec:
  group: database.example.com
  names:
    kind: PostgresCluster
    plural: postgresclusters
    shortNames:
      - pg
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["replicas", "version"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                version:
                  type: string
                  enum: ["14", "15", "16"]
                storage:
                  type: object
                  properties:
                    size:
                      type: string
                      default: "10Gi"
                    storageClass:
                      type: string
                backup:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      default: true
                    schedule:
                      type: string
                      default: "0 2 * * *"
                    retention:
                      type: integer
                      default: 7
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: ["Creating", "Running", "Upgrading", "Failed", "Deleting"]
                primaryEndpoint:
                  type: string
                replicaEndpoints:
                  type: array
                  items:
                    type: string
                currentVersion:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      reason:
                        type: string
                      message:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
```

**컨트롤러 핵심 로직:**
- **Phase별 상태 관리** (Creating, Running, Upgrading, Failed)
- **자동 장애 복구** (Primary 장애 시 Failover)
- **Rolling upgrade 전략** (Replica 먼저 업그레이드, 그 다음 Primary)
- **백업 관리** (예약된 백업을 위한 CronJob)

**아키텍처:**
```
PostgresCluster CR
       |
       v
   Controller
       |
       +---> StatefulSet (PostgreSQL 파드)
       +---> Service (Primary 엔드포인트)
       +---> Service (Replica 엔드포인트)
       +---> Secret (자격 증명)
       +---> ConfigMap (PostgreSQL 구성)
       +---> CronJob (백업)
       +---> PodDisruptionBudget
```

</details>

### 2. 스케줄러 프레임워크를 사용하여 커스텀 스케줄러를 구현하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**스케줄러 플러그인 구현:**

```go
// 여러 확장 지점을 구현하는 플러그인
type CustomSchedulerPlugin struct {
    handle framework.Handle
}

// PreFilter 구현 - 파드 요구사항 확인
func (p *CustomSchedulerPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    // 파드에 필수 어노테이션이 있는지 검증
    if _, ok := pod.Annotations["custom-scheduler/zone"]; !ok {
        return nil, framework.NewStatus(framework.Unschedulable, "zone 어노테이션 누락")
    }
    return nil, framework.NewStatus(framework.Success, "")
}

// Filter 구현 - 부적합한 노드 제외
func (p *CustomSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    requiredZone := pod.Annotations["custom-scheduler/zone"]
    nodeZone := nodeInfo.Node().Labels["topology.kubernetes.io/zone"]
    
    if requiredZone != nodeZone {
        return framework.NewStatus(framework.Unschedulable, "zone 불일치")
    }
    return framework.NewStatus(framework.Success, "")
}

// Score 구현 - 적합한 노드 순위 지정
func (p *CustomSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    
    // 사용 가능한 리소스 기반으로 점수 계산
    allocatable := nodeInfo.Node().Status.Allocatable
    requested := nodeInfo.Requested
    
    cpuScore := calculateResourceScore(allocatable.Cpu(), requested.Cpu)
    memScore := calculateResourceScore(allocatable.Memory(), requested.Memory)
    
    return (cpuScore + memScore) / 2, framework.NewStatus(framework.Success, "")
}

// 플러그인 등록
func New(_ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &CustomSchedulerPlugin{handle: h}, nil
}
```

**스케줄러 구성:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: custom-scheduler
    plugins:
      preFilter:
        enabled:
          - name: CustomSchedulerPlugin
      filter:
        enabled:
          - name: CustomSchedulerPlugin
      score:
        enabled:
          - name: CustomSchedulerPlugin
        disabled:
          - name: NodeResourcesBalancedAllocation
```

**확장 지점 요약:**

| 확장 지점 | 목적 | 실행 시점 |
|-----------|------|----------|
| PreFilter | 파드 수준 검사 | 필터링 전 |
| Filter | 노드 제거 | 각 노드에 대해 |
| PostFilter | 스케줄 불가 처리 | 적합한 노드 없을 때 |
| PreScore | 점수 계산 준비 | 점수 계산 전 |
| Score | 노드 순위 지정 | 필터링된 노드에 대해 |
| NormalizeScore | 점수 정규화 | 모든 점수 계산 후 |
| Reserve | 리소스 예약 | 노드 선택 후 |
| Permit | 최종 승인 | 바인딩 전 |
| PreBind | 바인딩 전 작업 | API 바인딩 전 |
| Bind | 실제 바인딩 | API 서버 업데이트 |
| PostBind | 바인딩 후 정리 | 바인딩 후 |

</details>
