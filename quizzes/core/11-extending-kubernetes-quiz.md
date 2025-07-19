# Kubernetes 확장 퀴즈

이 퀴즈는 Kubernetes 확장 메커니즘에 관한 개념과 실무 지식을 테스트합니다. 커스텀 리소스 정의(CRD), 커스텀 컨트롤러, API 확장, 웹훅, 오퍼레이터 패턴 등의 주제를 다룹니다.
## 객관식 문제

1. Kubernetes에서 커스텀 리소스를 정의하는 가장 일반적인 방법은 무엇인가요?
   - A) ConfigMap을 사용하여 리소스 스키마 정의
   - B) CustomResourceDefinition(CRD) 생성
   - C) API 서버 코드 직접 수정
   - D) 애그리게이션 레이어(Aggregation Layer) 사용
   
<details>
<summary>정답 보기</summary>

**정답: B) CustomResourceDefinition(CRD) 생성**

**설명:**
Kubernetes에서 커스텀 리소스를 정의하는 가장 일반적인 방법은 CustomResourceDefinition(CRD)을 생성하는 것입니다. CRD는 Kubernetes API를 확장하여 새로운 리소스 유형을 정의할 수 있게 해주는 메커니즘입니다.

CRD를 사용하면 다음과 같은 이점이 있습니다:
- 기존 Kubernetes API 서버를 수정하지 않고도 새로운 리소스 유형을 추가할 수 있습니다.
- `kubectl`과 같은 표준 Kubernetes 도구를 사용하여 커스텀 리소스를 관리할 수 있습니다.
- 리소스 검증, 버전 관리, 상태 하위 리소스 등의 기능을 활용할 수 있습니다.

CRD 예시:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
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
              properties:
                cronSpec:
                  type: string
                image:
                  type: string
                replicas:
                  type: integer
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

다른 옵션들의 문제점:
- ConfigMap은 구성 데이터를 저장하는 데 사용되며, API 확장에는 적합하지 않습니다.
- API 서버 코드를 직접 수정하는 것은 복잡하고 유지 관리가 어려우며, 업그레이드 시 문제가 발생할 수 있습니다.
- 애그리게이션 레이어는 커스텀 리소스를 정의하는 또 다른 방법이지만, 별도의 API 서버를 구현해야 하므로 CRD보다 복잡합니다.
</details>

2. Kubernetes 오퍼레이터(Operator)의 주요 목적은 무엇인가요?
   - A) 클러스터 노드의 리소스 사용량 최적화
   - B) 복잡한 애플리케이션의 운영 지식을 자동화된 소프트웨어로 인코딩
   - C) Kubernetes API 서버의 성능 향상
   - D) 클러스터 네트워킹 기능 확장
   
<details>
<summary>정답 보기</summary>

**정답: B) 복잡한 애플리케이션의 운영 지식을 자동화된 소프트웨어로 인코딩**

**설명:**
Kubernetes 오퍼레이터(Operator)의 주요 목적은 복잡한 애플리케이션의 운영 지식을 자동화된 소프트웨어로 인코딩하는 것입니다. 오퍼레이터 패턴은 사람 운영자(human operator)가 복잡한 애플리케이션을 관리하는 방식을 소프트웨어로 구현한 것입니다.

오퍼레이터의 주요 특징:
- 커스텀 리소스와 커스텀 컨트롤러를 결합하여 애플리케이션별 로직을 구현합니다.
- 애플리케이션의 배포, 업그레이드, 백업, 복구, 스케일링 등과 같은 운영 작업을 자동화합니다.
- 애플리케이션의 상태를 지속적으로 모니터링하고 원하는 상태로 조정합니다.
- 도메인 지식을 코드화하여 복잡한 애플리케이션을 선언적으로 관리할 수 있게 합니다.

오퍼레이터의 일반적인 사용 사례:
- 데이터베이스(예: PostgreSQL, MySQL, MongoDB)의 자동화된 관리
- 메시징 시스템(예: Kafka, RabbitMQ)의 배포 및 구성
- 모니터링 시스템(예: Prometheus)의 설정 및 유지 관리
- 서비스 메시(예: Istio)의 관리

오퍼레이터 예시 - Prometheus Operator:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  replicas: 2
  version: v2.35.0
  serviceMonitorSelector:
    matchLabels:
      team: frontend
  resources:
    requests:
      memory: 400Mi
```

이 간단한 선언적 구성으로 Prometheus Operator는 다음과 같은 복잡한 작업을 자동으로 처리합니다:
- Prometheus 서버 배포
- 구성 파일 생성 및 관리
- 서비스 모니터링 대상 자동 발견
- 고가용성 설정
- 스토리지 관리
- 업그레이드 조정

다른 옵션들은 오퍼레이터의 주요 목적이 아닙니다:
- 리소스 사용량 최적화는 HPA(Horizontal Pod Autoscaler), VPA(Vertical Pod Autoscaler) 등의 역할입니다.
- API 서버 성능 향상은 오퍼레이터의 주요 목적이 아닙니다.
- 네트워킹 기능 확장은 CNI 플러그인이나 서비스 메시의 역할입니다.
</details>

3. Kubernetes에서 어드미션 웹훅(Admission Webhook)의 주요 기능은 무엇인가요?
   - A) API 서버에 대한 인증 처리
   - B) 리소스 생성 또는 수정 요청을 가로채서 검증하거나 변경
   - C) 클러스터 이벤트 모니터링 및 알림 전송
   - D) 외부 시스템과의 통합을 위한 API 제공
   
<details>
<summary>정답 보기</summary>

**정답: B) 리소스 생성 또는 수정 요청을 가로채서 검증하거나 변경**

**설명:**
Kubernetes에서 어드미션 웹훅(Admission Webhook)의 주요 기능은 리소스 생성 또는 수정 요청을 가로채서 검증하거나 변경하는 것입니다. 어드미션 웹훅은 Kubernetes API 서버가 요청을 영구 저장소(etcd)에 저장하기 전에 요청을 가로채는 메커니즘을 제공합니다.

어드미션 웹훅의 두 가지 유형:

1. **검증 웹훅(Validating Webhook)**:
   - 리소스 생성, 업데이트, 삭제 요청을 검증합니다.
   - 요청을 허용하거나 거부할 수 있지만, 변경할 수는 없습니다.
   - 정책 적용, 보안 검사, 구성 검증 등에 사용됩니다.

2. **변경 웹훅(Mutating Webhook)**:
   - 리소스 생성, 업데이트 요청을 검증하고 변경할 수 있습니다.
   - 기본값 설정, 사이드카 컨테이너 주입, 레이블 추가 등에 사용됩니다.
   - 검증 웹훅보다 먼저 실행됩니다.

어드미션 웹훅 구성 예시:
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-namespace
      name: webhook-service
      path: "/validate-pods"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

어드미션 웹훅의 일반적인 사용 사례:
- 보안 정책 적용(예: 특권 컨테이너 금지)
- 리소스 요청 및 제한 강제
- 사이드카 컨테이너 자동 주입(예: Istio)
- 레이블 및 어노테이션 자동 추가
- 이미지 레지스트리 제한
- 네임스페이스 기반 정책 적용

다른 옵션들의 문제점:
- API 서버에 대한 인증 처리는 인증 플러그인(Authentication Plugin)의 역할입니다.
- 클러스터 이벤트 모니터링 및 알림 전송은 이벤트 리스너나 모니터링 도구의 역할입니다.
- 외부 시스템과의 통합을 위한 API 제공은 API 확장의 일반적인 목적이지만, 어드미션 웹훅의 주요 기능은 아닙니다.
</details>

4. Kubernetes API 서버의 애그리게이션 레이어(Aggregation Layer)의 주요 목적은 무엇인가요?
   - A) API 서버의 성능 최적화
   - B) 여러 API 서버를 하나의 API 서버로 통합
   - C) 커스텀 API 서버를 기본 API 서버에 통합하여 API 확장
   - D) 클러스터 내 서비스 디스커버리 제공
   
<details>
<summary>정답 보기</summary>

**정답: C) 커스텀 API 서버를 기본 API 서버에 통합하여 API 확장**

**설명:**
Kubernetes API 서버의 애그리게이션 레이어(Aggregation Layer)의 주요 목적은 커스텀 API 서버를 기본 API 서버에 통합하여 API를 확장하는 것입니다. 이를 통해 Kubernetes API를 확장하는 또 다른 방법을 제공하며, CRD보다 더 복잡하지만 더 강력한 기능을 제공합니다.

애그리게이션 레이어의 주요 특징:
- 커스텀 API 서버를 Kubernetes API 서버의 URL 공간에 통합합니다.
- 커스텀 API 서버는 자체 스토리지, 비즈니스 로직, API 버전 등을 가질 수 있습니다.
- 기본 API 서버는 요청을 적절한 커스텀 API 서버로 프록시합니다.
- 인증 및 권한 부여는 기본 API 서버에서 처리됩니다.

애그리게이션 레이어를 사용하는 경우:
- 복잡한 검증 로직이 필요한 경우
- 커스텀 스토리지 백엔드가 필요한 경우
- 기존 API와 다른 동작이 필요한 경우
- 리소스 변환 또는 특별한 상태 계산이 필요한 경우

APIService 리소스 예시:
```yaml
apiVersion: apiregistration.k8s.io/v1
kind: APIService
metadata:
  name: v1alpha1.metrics.k8s.io
spec:
  service:
    name: metrics-server
    namespace: kube-system
  group: metrics.k8s.io
  version: v1alpha1
  insecureSkipTLSVerify: true
  groupPriorityMinimum: 100
  versionPriority: 100
```

이 구성은 `metrics.k8s.io/v1alpha1` API 그룹에 대한 요청을 `kube-system` 네임스페이스의 `metrics-server` 서비스로 라우팅합니다.

애그리게이션 레이어를 사용하는 실제 예:
- metrics-server: 노드 및 포드 리소스 사용량 메트릭 제공
- service-catalog: 외부 서비스 브로커와의 통합
- custom-metrics-apiserver: HPA를 위한 커스텀 메트릭 제공

다른 옵션들의 문제점:
- 애그리게이션 레이어는 API 서버의 성능을 최적화하기 위한 것이 아닙니다.
- 여러 API 서버를 하나로 통합하는 것은 정확하지 않은 설명입니다. 애그리게이션 레이어는 여러 API 서버를 단일 URL 공간으로 통합하지만, 서버 자체는 별도로 실행됩니다.
- 애그리게이션 레이어는 서비스 디스커버리를 제공하지 않습니다. 이는 Kubernetes 서비스의 역할입니다.
</details>

5. Kubernetes에서 커스텀 컨트롤러(Custom Controller)의 주요 역할은 무엇인가요?
   - A) 클러스터 노드의 리소스 사용량 모니터링
   - B) 커스텀 리소스의 상태를 관찰하고 원하는 상태로 조정
   - C) API 서버에 대한 요청 인증 및 권한 부여
   - D) 클러스터 네트워킹 관리
   
<details>
<summary>정답 보기</summary>

**정답: B) 커스텀 리소스의 상태를 관찰하고 원하는 상태로 조정**

**설명:**
Kubernetes에서 커스텀 컨트롤러(Custom Controller)의 주요 역할은 커스텀 리소스의 상태를 관찰하고 원하는 상태로 조정하는 것입니다. 컨트롤러는 Kubernetes의 핵심 운영 패턴인 "조정 루프(reconciliation loop)"를 구현하여 시스템의 실제 상태를 원하는 상태로 지속적으로 조정합니다.

커스텀 컨트롤러의 주요 특징:
- 특정 리소스 유형(일반적으로 CRD로 정의된 커스텀 리소스)을 감시합니다.
- 리소스 변경 이벤트에 반응하여 비즈니스 로직을 실행합니다.
- 리소스의 실제 상태를 원하는 상태로 조정하는 작업을 수행합니다.
- 리소스의 상태 필드를 업데이트하여 현재 상태를 반영합니다.

커스텀 컨트롤러의 일반적인 구성 요소:
1. **인포머(Informer)**: Kubernetes API 서버를 감시하고 리소스 변경 이벤트를 수신합니다.
2. **워크큐(Work Queue)**: 처리해야 할 이벤트를 저장하고 관리합니다.
3. **조정기(Reconciler)**: 리소스의 원하는 상태와 실제 상태를 비교하고 필요한 작업을 수행합니다.
4. **클라이언트(Client)**: Kubernetes API와 상호 작용하여 리소스를 생성, 업데이트, 삭제합니다.

커스텀 컨트롤러 예시 - 간단한 조정 함수:
```go
func (c *Controller) reconcile(key string) error {
    // 네임스페이스와 이름으로 키 분리
    namespace, name, err := cache.SplitMetaNamespaceKey(key)
    if err != nil {
        return err
    }
    
    // 커스텀 리소스 가져오기
    instance, err := c.customResourceLister.CustomResources(namespace).Get(name)
    if errors.IsNotFound(err) {
        // 리소스가 삭제됨 - 정리 작업 수행
        return nil
    }
    if err != nil {
        return err
    }
    
    // 리소스 상태 확인 및 필요한 작업 수행
    // 예: 하위 리소스 생성, 외부 시스템과 통합, 상태 업데이트 등
    
    // 상태 업데이트
    instanceCopy := instance.DeepCopy()
    instanceCopy.Status.Phase = "Reconciled"
    _, err = c.customResourceClient.CustomResources(namespace).UpdateStatus(instanceCopy)
    return err
}
```

커스텀 컨트롤러의 일반적인 사용 사례:
- 복잡한 애플리케이션 배포 및 관리 자동화
- 외부 시스템과의 통합(예: 클라우드 리소스 프로비저닝)
- 백업 및 복구 프로세스 자동화
- 고급 배포 전략 구현(예: 카나리 배포, 블루-그린 배포)

다른 옵션들의 문제점:
- 클러스터 노드의 리소스 사용량 모니터링은 metrics-server나 Prometheus와 같은 모니터링 도구의 역할입니다.
- API 서버에 대한 요청 인증 및 권한 부여는 인증 및 권한 부여 플러그인의 역할입니다.
- 클러스터 네트워킹 관리는 CNI 플러그인이나 네트워크 컨트롤러의 역할입니다.
</details>
6. Kubernetes에서 CRD(CustomResourceDefinition)의 검증(validation) 스키마를 정의하는 데 사용되는 형식은 무엇인가요?
   - A) JSON Schema
   - B) XML Schema
   - C) OpenAPI v3 Schema
   - D) GraphQL Schema
   
<details>
<summary>정답 보기</summary>

**정답: C) OpenAPI v3 Schema**

**설명:**
Kubernetes에서 CRD(CustomResourceDefinition)의 검증 스키마를 정의하는 데 사용되는 형식은 OpenAPI v3 Schema입니다. 이 스키마는 커스텀 리소스의 구조와 필드 유형을 정의하고, API 서버가 리소스 생성 및 업데이트 요청을 검증하는 데 사용됩니다.

CRD의 검증 스키마 예시:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

이 예시에서 `openAPIV3Schema` 필드는 다음과 같은 검증 규칙을 정의합니다:
- `spec` 필드는 필수입니다.
- `spec` 내에서 `cronSpec`과 `image` 필드는 필수입니다.
- `cronSpec`은 문자열이며 cron 표현식 패턴을 따라야 합니다.
- `image`는 문자열입니다.
- `replicas`는 정수이며 1에서 10 사이의 값이어야 합니다.

OpenAPI v3 Schema는 다음과 같은 다양한 검증 기능을 제공합니다:
- 필수 필드 지정
- 데이터 유형 검증(문자열, 숫자, 불리언, 객체, 배열 등)
- 문자열 패턴 검증(정규 표현식)
- 숫자 범위 검증(최소값, 최대값)
- 배열 길이 검증
- 열거형 값 검증
- 중첩된 객체 구조 정의

다른 옵션들의 문제점:
- JSON Schema는 OpenAPI의 기반이지만, Kubernetes는 특별히 OpenAPI v3 Schema를 사용합니다.
- XML Schema는 Kubernetes API에서 사용되지 않습니다.
- GraphQL Schema는 GraphQL API에 사용되지만, Kubernetes API에는 사용되지 않습니다.
</details>

7. Kubernetes에서 커스텀 리소스의 상태(status) 하위 리소스를 활성화하는 주요 이점은 무엇인가요?
   - A) 리소스 생성 속도 향상
   - B) 스펙(spec)과 상태(status) 업데이트의 분리 및 RBAC 제어 가능
   - C) 자동 백업 및 복구 기능 제공
   - D) 리소스 버전 관리 간소화
   
<details>
<summary>정답 보기</summary>

**정답: B) 스펙(spec)과 상태(status) 업데이트의 분리 및 RBAC 제어 가능**

**설명:**
Kubernetes에서 커스텀 리소스의 상태(status) 하위 리소스를 활성화하는 주요 이점은 스펙(spec)과 상태(status) 업데이트의 분리 및 RBAC(Role-Based Access Control)을 통한 접근 제어가 가능하다는 것입니다.

상태 하위 리소스를 활성화하면 다음과 같은 이점이 있습니다:

1. **관심사의 분리**:
   - `spec` 필드는 사용자가 원하는 상태를 정의합니다.
   - `status` 필드는 컨트롤러가 관찰한 실제 상태를 보고합니다.
   - 이 분리를 통해 사용자와 컨트롤러의 책임이 명확해집니다.

2. **RBAC 제어**:
   - 상태 업데이트 권한을 컨트롤러에만 부여하고 일반 사용자에게는 읽기 권한만 부여할 수 있습니다.
   - 이를 통해 상태 정보가 무단으로 변경되는 것을 방지할 수 있습니다.

3. **충돌 방지**:
   - 사용자가 `spec`을 업데이트하는 동안 컨트롤러가 `status`를 업데이트해도 충돌이 발생하지 않습니다.
   - 이는 두 필드가 별도의 API 요청으로 업데이트되기 때문입니다.

4. **스케일 하위 리소스 지원**:
   - 상태 하위 리소스를 활성화하면 스케일 하위 리소스도 활성화할 수 있습니다.
   - 이를 통해 HPA(Horizontal Pod Autoscaler)와 같은 표준 Kubernetes 스케일링 도구를 사용할 수 있습니다.

CRD에서 상태 하위 리소스 활성화 예시:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      subresources:
        status: {}  # 상태 하위 리소스 활성화
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                # 스펙 필드 정의...
            status:
              type: object
              properties:
                # 상태 필드 정의...
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

컨트롤러에서 상태 업데이트 예시:
```go
// 상태만 업데이트
statusUpdate := &v1alpha1.MyResource{}
statusUpdate.Name = instance.Name
statusUpdate.Namespace = instance.Namespace
statusUpdate.Status.Phase = "Running"
statusUpdate.Status.Message = "Resource is running"

_, err = c.clientset.MyGroup().MyResources(namespace).UpdateStatus(statusUpdate)
```

다른 옵션들의 문제점:
- 상태 하위 리소스는 리소스 생성 속도를 향상시키지 않습니다.
- 자동 백업 및 복구 기능은 제공하지 않습니다.
- 리소스 버전 관리는 CRD의 `versions` 필드를 통해 처리되며, 상태 하위 리소스와는 직접적인 관련이 없습니다.
</details>

8. Kubernetes에서 웹훅 변환(Webhook Conversion)의 주요 목적은 무엇인가요?
   - A) API 요청을 외부 서비스로 라우팅
   - B) 커스텀 리소스의 다양한 버전 간 변환 처리
   - C) 인증 토큰을 다른 형식으로 변환
   - D) 로그 데이터를 구조화된 형식으로 변환
   
<details>
<summary>정답 보기</summary>

**정답: B) 커스텀 리소스의 다양한 버전 간 변환 처리**

**설명:**
Kubernetes에서 웹훅 변환(Webhook Conversion)의 주요 목적은 커스텀 리소스의 다양한 버전 간 변환을 처리하는 것입니다. 이 기능은 CRD의 여러 버전을 지원하고 버전 간 원활한 마이그레이션을 가능하게 합니다.

웹훅 변환의 주요 특징:

1. **다중 버전 지원**:
   - CRD는 여러 API 버전(예: v1alpha1, v1beta1, v1)을 동시에 지원할 수 있습니다.
   - 각 버전은 다른 스키마와 필드를 가질 수 있습니다.

2. **자동 변환**:
   - API 서버는 클라이언트가 요청한 버전과 스토리지 버전 간의 변환을 자동으로 처리합니다.
   - 변환 웹훅은 이 과정에서 커스텀 변환 로직을 제공합니다.

3. **스토리지 버전 독립성**:
   - 스토리지 버전이 변경되어도 이전 버전의 클라이언트는 계속 작동할 수 있습니다.
   - 웹훅은 이전 버전과 새 버전 간의 양방향 변환을 처리합니다.

CRD에서 변환 웹훅 구성 예시:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          # v1 스키마 정의...
    - name: v1beta1
      served: true
      storage: false
      schema:
        openAPIV3Schema:
          # v1beta1 스키마 정의...
  conversion:
    strategy: Webhook
    webhook:
      clientConfig:
        service:
          namespace: webhook-system
          name: crd-conversion-webhook
          path: /convert
        caBundle: <base64-encoded-ca-cert>
      conversionReviewVersions: ["v1", "v1beta1"]
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
```

변환 웹훅 서버 구현 예시:
```go
func (s *WebhookServer) ServeConvert(w http.ResponseWriter, r *http.Request) {
    var body []byte
    if r.Body != nil {
        if data, err := ioutil.ReadAll(r.Body); err == nil {
            body = data
        }
    }

    // ConversionReview 요청 디코딩
    convertReview := v1.ConversionReview{}
    if err := json.Unmarshal(body, &convertReview); err != nil {
        // 오류 처리
        return
    }

    // 변환 로직 수행
    if convertReview.Request.DesiredAPIVersion == "stable.example.com/v1" {
        // v1beta1 -> v1 변환
        for i, obj := range convertReview.Request.Objects {
            v1beta1Obj := &v1beta1.CronTab{}
            if err := json.Unmarshal(obj.Raw, v1beta1Obj); err != nil {
                // 오류 처리
                return
            }
            
            // 변환 로직
            v1Obj := &v1.CronTab{
                Spec: v1.CronTabSpec{
                    CronSpec: v1beta1Obj.Spec.Cron,  // 필드 이름 변경
                    Image: v1beta1Obj.Spec.Image,
                    Replicas: v1beta1Obj.Spec.Replicas,
                },
            }
            
            // 변환된 객체 인코딩
            raw, err := json.Marshal(v1Obj)
            if err != nil {
                // 오류 처리
                return
            }
            
            convertReview.Response.ConvertedObjects = append(
                convertReview.Response.ConvertedObjects,
                runtime.RawExtension{Raw: raw},
            )
        }
    } else {
        // v1 -> v1beta1 변환
        // 유사한 로직...
    }

    // 응답 설정
    convertReview.Response.UID = convertReview.Request.UID
    convertReview.Response.Result.Status = "Success"
    
    // 응답 전송
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(convertReview)
}
```

다른 옵션들의 문제점:
- API 요청을 외부 서비스로 라우팅하는 것은 API 애그리게이션의 역할입니다.
- 인증 토큰 변환은 인증 플러그인의 역할입니다.
- 로그 데이터 변환은 로깅 시스템의 역할입니다.
</details>

9. Kubernetes 오퍼레이터를 개발하는 데 도움이 되는 프레임워크가 아닌 것은 무엇인가요?
   - A) Operator Framework
   - B) Kubebuilder
   - C) Metacontroller
   - D) Kubespray
   
<details>
<summary>정답 보기</summary>

**정답: D) Kubespray**

**설명:**
Kubespray는 Kubernetes 오퍼레이터를 개발하는 데 도움이 되는 프레임워크가 아닙니다. Kubespray는 Ansible 플레이북을 사용하여 Kubernetes 클러스터를 배포하고 관리하기 위한 도구입니다. 이는 클러스터 설치 및 구성에 중점을 두며, 오퍼레이터 개발과는 관련이 없습니다.

Kubernetes 오퍼레이터 개발을 위한 실제 프레임워크는 다음과 같습니다:

1. **Operator Framework**:
   - Red Hat에서 개발한 오퍼레이터 개발 도구 모음
   - 주요 구성 요소:
     - Operator SDK: 오퍼레이터 스캐폴딩 및 개발 도구
     - Operator Lifecycle Manager(OLM): 오퍼레이터 설치 및 업그레이드 관리
     - Operator Metering: 오퍼레이터 사용량 보고
   - Go, Ansible, Helm 기반 오퍼레이터 개발 지원

2. **Kubebuilder**:
   - Kubernetes SIG(Special Interest Group)에서 개발한 프레임워크
   - Go 언어로 컨트롤러를 개발하기 위한 SDK
   - 코드 생성, CRD 관리, 테스트 도구 제공
   - controller-runtime 라이브러리 기반

3. **Metacontroller**:
   - 웹훅 기반의 경량 오퍼레이터 프레임워크
   - 다양한 언어로 컨트롤러 로직 구현 가능
   - 선언적 컨트롤러 정의
   - 간단한 컨트롤러를 빠르게 개발하는 데 적합

각 프레임워크의 특징 비교:

| 프레임워크 | 주요 언어 | 복잡성 | 특징 |
|------------|-----------|--------|------|
| Operator Framework | Go, Ansible, Helm | 중간-높음 | 포괄적인 도구 세트, 다양한 개발 옵션 |
| Kubebuilder | Go | 중간 | 표준화된 패턴, 코드 생성 도구 |
| Metacontroller | 언어 독립적 | 낮음 | 웹훅 기반, 간단한 구현 |

오퍼레이터 개발 예시 (Kubebuilder 사용):
```bash
# 프로젝트 초기화
kubebuilder init --domain example.com --repo github.com/example/my-operator

# API 생성
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# 컨트롤러 구현 (controller.go 파일 편집)

# CRD 생성 및 컨트롤러 배포
make install
make deploy
```

다른 옵션들의 설명:
- Operator Framework는 Red Hat의 포괄적인 오퍼레이터 개발 도구 모음입니다.
- Kubebuilder는 Kubernetes SIG에서 개발한 Go 기반 컨트롤러 개발 프레임워크입니다.
- Metacontroller는 웹훅 기반의 경량 오퍼레이터 프레임워크입니다.
</details>

10. Kubernetes에서 커스텀 리소스 정의(CRD)와 애그리게이션 API(Aggregated API)의 주요 차이점은 무엇인가요?
    - A) CRD는 버전 관리를 지원하지 않지만, 애그리게이션 API는 지원함
    - B) CRD는 검증 스키마를 지원하지 않지만, 애그리게이션 API는 지원함
    - C) CRD는 구현이 간단하지만 유연성이 제한적이고, 애그리게이션 API는 구현이 복잡하지만 더 많은 유연성을 제공함
    - D) CRD는 클러스터 범위 리소스만 지원하고, 애그리게이션 API는 네임스페이스 범위 리소스만 지원함
    
<details>
<summary>정답 보기</summary>

**정답: C) CRD는 구현이 간단하지만 유연성이 제한적이고, 애그리게이션 API는 구현이 복잡하지만 더 많은 유연성을 제공함**

**설명:**
Kubernetes에서 커스텀 리소스 정의(CRD)와 애그리게이션 API(Aggregated API)의 주요 차이점은 구현 복잡성과 유연성의 균형에 있습니다. CRD는 구현이 간단하지만 유연성이 제한적인 반면, 애그리게이션 API는 구현이 복잡하지만 더 많은 유연성을 제공합니다.

**CRD(CustomResourceDefinition)의 특징:**
- **간단한 구현**: YAML 파일 하나로 새로운 API 리소스를 정의할 수 있습니다.
- **기존 API 서버 사용**: 별도의 API 서버를 구현할 필요가 없습니다.
- **제한된 유연성**: 
  - 스토리지는 etcd로 제한됩니다.
  - 기본 API 서버의 동작을 상속합니다.
  - 복잡한 검증 로직이나 변환 로직을 구현하기 어렵습니다.
- **웹훅을 통한 확장**: 검증 웹훅, 변환 웹훅 등을 통해 일부 기능을 확장할 수 있습니다.

**애그리게이션 API의 특징:**
- **복잡한 구현**: 별도의 API 서버를 개발하고 배포해야 합니다.
- **높은 유연성**:
  - 커스텀 스토리지 백엔드 사용 가능
  - 복잡한 비즈니스 로직 구현 가능
  - 커스텀 인증 및 권한 부여 로직 구현 가능
  - 특별한 상태 계산 및 변환 로직 구현 가능
- **완전한 API 서버 기능**: 표준 Kubernetes API 서버의 모든 기능을 활용할 수 있습니다.

**선택 기준:**

| 기준 | CRD 선택 | 애그리게이션 API 선택 |
|------|----------|----------------------|
| 구현 복잡성 | 낮음 - 간단한 YAML 정의 | 높음 - 별도의 API 서버 개발 필요 |
| 개발 시간 | 짧음 - 몇 분 내에 구현 가능 | 길음 - 완전한 API 서버 개발 필요 |
| 유지 관리 | 쉬움 - 기존 API 서버가 관리 | 어려움 - 별도의 서비스 유지 관리 필요 |
| 스토리지 옵션 | etcd만 가능 | 커스텀 스토리지 백엔드 가능 |
| 비즈니스 로직 | 제한적 - 컨트롤러로 구현 | 유연함 - API 서버에 직접 구현 가능 |
| 성능 | 일반적으로 좋음 | 커스텀 최적화 가능 |
| 사용 사례 | 간단한 CRUD 작업, 표준 패턴 | 복잡한 API 동작, 특별한 검증/변환 |

**예시 시나리오:**

CRD 적합 사례:
- 간단한 애플리케이션 구성 관리
- 기본적인 CRUD 작업이 주요 요구 사항
- 빠른 프로토타이핑 및 개발

애그리게이션 API 적합 사례:
- 외부 데이터베이스와의 통합
- 복잡한 데이터 변환 및 검증
- 특별한 인증 메커니즘 필요
- 고성능 또는 특수 목적 API

다른 옵션들의 문제점:
- CRD도 버전 관리를 지원합니다(A는 틀림).
- CRD도 OpenAPI v3 Schema를 통한 검증 스키마를 지원합니다(B는 틀림).
- CRD와 애그리게이션 API 모두 클러스터 범위 및 네임스페이스 범위 리소스를 지원합니다(D는 틀림).
</details>
## 주관식 문제

1. CustomResourceDefinition(CRD)을 사용하여 커스텀 리소스를 정의하는 방법과 해당 리소스의 검증 규칙을 설정하는 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**CustomResourceDefinition(CRD) 정의 방법:**

CRD는 Kubernetes API를 확장하여 새로운 리소스 유형을 정의하는 메커니즘입니다. CRD를 생성하면 새로운 RESTful API 엔드포인트가 생성되고, `kubectl`과 같은 표준 도구를 사용하여 해당 리소스를 관리할 수 있습니다.

**1. 기본 CRD 구조:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: <plural>.<group>  # 예: crontabs.stable.example.com
spec:
  group: <api-group>      # 예: stable.example.com
  names:
    kind: <kind-name>     # 예: CronTab
    plural: <plural-name> # 예: crontabs
    singular: <singular-name>  # 예: crontab
    shortNames:           # 선택 사항
    - <short-name>        # 예: ct
  scope: Namespaced       # 또는 Cluster
  versions:
    - name: <version>     # 예: v1
      served: true        # API 서버에서 제공 여부
      storage: true       # 스토리지 버전 여부
      schema:
        openAPIV3Schema:
          # 스키마 정의
```

**2. 검증 규칙 설정:**

CRD의 검증 규칙은 `openAPIV3Schema` 필드를 통해 설정합니다. 이 스키마는 OpenAPI v3 형식을 따르며, 리소스의 구조와 필드 유형을 정의합니다.

**기본 검증 규칙 예시:**

```yaml
schema:
  openAPIV3Schema:
    type: object
    required: ["spec"]
    properties:
      spec:
        type: object
        required: ["cronSpec", "image"]
        properties:
          cronSpec:
            type: string
            pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
          image:
            type: string
          replicas:
            type: integer
            minimum: 1
            maximum: 10
            default: 1
```

**3. 고급 검증 기능:**

OpenAPI v3 Schema는 다양한 검증 기능을 제공합니다:

- **필수 필드**: `required` 배열에 필드 이름을 추가하여 필수 필드 지정
  ```yaml
  required: ["fieldName1", "fieldName2"]
  ```

- **데이터 유형**: `type` 필드를 사용하여 데이터 유형 지정
  ```yaml
  type: string | number | integer | boolean | array | object
  ```

- **문자열 제약 조건**: 문자열 길이 및 패턴 검증
  ```yaml
  minLength: 3
  maxLength: 64
  pattern: '^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
  ```

- **숫자 제약 조건**: 숫자 범위 검증
  ```yaml
  minimum: 0
  maximum: 100
  multipleOf: 5
  ```

- **배열 제약 조건**: 배열 길이 및 항목 검증
  ```yaml
  minItems: 1
  maxItems: 10
  uniqueItems: true
  items:
    type: string
  ```

- **열거형 값**: 허용된 값 목록 지정
  ```yaml
  enum: ["value1", "value2", "value3"]
  ```

- **기본값**: 필드의 기본값 지정
  ```yaml
  default: "default-value"
  ```

- **추가 속성**: 추가 속성 허용 여부 제어
  ```yaml
  additionalProperties: false
  ```

**4. 전체 CRD 예시:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["cronSpec", "image"]
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                  default: 1
            status:
              type: object
              properties:
                active:
                  type: boolean
                lastScheduleTime:
                  type: string
                  format: date-time
      subresources:
        status: {}  # 상태 하위 리소스 활성화
      additionalPrinterColumns:
        - name: Schedule
          type: string
          description: The cron schedule
          jsonPath: .spec.cronSpec
        - name: Image
          type: string
          description: The image to use
          jsonPath: .spec.image
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

**5. CRD 적용 및 사용:**

```bash
# CRD 적용
kubectl apply -f crontab-crd.yaml

# 커스텀 리소스 생성
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: my-crontab
spec:
  cronSpec: "* * * * */5"
  image: my-cron-image
  replicas: 3
EOF

# 커스텀 리소스 조회
kubectl get crontabs
kubectl get ct  # 짧은 이름 사용
```

**6. 검증 규칙 테스트:**

잘못된 값으로 리소스를 생성하면 검증 오류가 발생합니다:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: stable.example.com/v1
kind: CronTab
metadata:
  name: invalid-crontab
spec:
  cronSpec: "invalid-cron-spec"  # 패턴 불일치
  image: my-cron-image
  replicas: 20  # 최대값 초과
EOF
```

이 명령은 다음과 같은 오류를 반환합니다:
```
Error from server (Invalid): error when creating "STDIN": admission webhook "validate-crontab.example.com" denied the request: 
- spec.cronSpec: Invalid value: "invalid-cron-spec": does not match pattern '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
- spec.replicas: Invalid value: 20: must be less than or equal to 10
```

**7. 모범 사례:**

- 명확하고 상세한 스키마 정의
- 필수 필드 명시적 지정
- 적절한 기본값 제공
- 문자열 패턴 및 숫자 범위 제한
- 상태 하위 리소스 활성화
- 추가 프린터 열 구성
- 버전 관리 전략 수립
</details>

2. Kubernetes 오퍼레이터 패턴(Operator Pattern)의 핵심 개념과 오퍼레이터를 구현하는 일반적인 방법을 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 오퍼레이터 패턴의 핵심 개념:**

오퍼레이터 패턴은 애플리케이션별 운영 지식을 소프트웨어로 인코딩하여 복잡한 애플리케이션을 자동으로 관리하는 Kubernetes 확장 메커니즘입니다. 이 패턴은 사람 운영자(human operator)가 복잡한 시스템을 관리하는 방식을 모방합니다.

**1. 핵심 개념:**

- **선언적 관리**: 사용자는 원하는 상태를 선언하고, 오퍼레이터는 현재 상태를 원하는 상태로 조정합니다.
- **도메인 지식 인코딩**: 특정 애플리케이션의 운영 지식과 모범 사례를 코드화합니다.
- **조정 루프(Reconciliation Loop)**: 지속적으로 실제 상태를 관찰하고 원하는 상태로 조정합니다.
- **커스텀 리소스**: 애플리케이션별 구성 및 상태를 저장하는 데 사용됩니다.
- **컨트롤러**: 커스텀 리소스의 변경을 감시하고 필요한 작업을 수행합니다.

**2. 오퍼레이터의 일반적인 기능:**

- **설치 및 업그레이드**: 애플리케이션 구성 요소 배포 및 버전 업그레이드
- **자동 복구**: 장애 감지 및 복구 작업 수행
- **백업 및 복원**: 데이터 백업 및 복원 프로세스 자동화
- **스케일링**: 워크로드 요구에 따른 자동 확장 및 축소
- **구성 관리**: 애플리케이션별 구성 변경 처리
- **운영 자동화**: 일상적인 운영 작업 자동화(예: 데이터베이스 압축, 인덱스 재구축)

**오퍼레이터 구현 방법:**

**1. 오퍼레이터 SDK 사용:**

[Operator SDK](https://sdk.operatorframework.io/)는 Red Hat의 Operator Framework의 일부로, 오퍼레이터 개발을 간소화하는 도구입니다.

```bash
# Operator SDK 설치
curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.25.0/operator-sdk_linux_amd64
chmod +x operator-sdk_linux_amd64
sudo mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

# Go 기반 오퍼레이터 프로젝트 생성
operator-sdk init --domain example.com --repo github.com/example/my-operator

# API 생성
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --resource --controller

# CRD 생성
make manifests

# 오퍼레이터 빌드 및 배포
make docker-build docker-push
make deploy
```

**2. Kubebuilder 사용:**

[Kubebuilder](https://book.kubebuilder.io/)는 Kubernetes SIG에서 개발한 프레임워크로, 컨트롤러 개발을 위한 도구를 제공합니다.

```bash
# Kubebuilder 설치
curl -L https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH) | tar -xz -C /tmp/
sudo mv /tmp/kubebuilder_*/bin/kubebuilder /usr/local/bin/

# 프로젝트 초기화
kubebuilder init --domain example.com --repo github.com/example/my-operator

# API 생성
kubebuilder create api --group apps --version v1alpha1 --kind MyApp

# CRD 생성 및 컨트롤러 배포
make install
make deploy
```

**3. 컨트롤러 구현:**

오퍼레이터의 핵심은 조정 함수(reconciliation function)입니다. 이 함수는 커스텀 리소스의 현재 상태를 관찰하고 필요한 작업을 수행합니다.

```go
// 조정 함수 예시
func (r *MyAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := r.Log.WithValues("myapp", req.NamespacedName)
    
    // 커스텀 리소스 가져오기
    var myApp appsv1alpha1.MyApp
    if err := r.Get(ctx, req.NamespacedName, &myApp); err != nil {
        if errors.IsNotFound(err) {
            // 리소스가 삭제됨 - 정리 작업 수행
            return ctrl.Result{}, nil
        }
        // 오류 발생
        return ctrl.Result{}, err
    }
    
    // 1. 필요한 리소스가 있는지 확인
    deployment := &appsv1.Deployment{}
    err := r.Get(ctx, types.NamespacedName{Name: myApp.Name, Namespace: myApp.Namespace}, deployment)
    if errors.IsNotFound(err) {
        // 배포가 없으면 생성
        deployment = r.deploymentForMyApp(&myApp)
        log.Info("Creating a new Deployment", "Deployment.Namespace", deployment.Namespace, "Deployment.Name", deployment.Name)
        if err := r.Create(ctx, deployment); err != nil {
            log.Error(err, "Failed to create new Deployment")
            return ctrl.Result{}, err
        }
        // 배포 생성 성공
        return ctrl.Result{Requeue: true}, nil
    } else if err != nil {
        log.Error(err, "Failed to get Deployment")
        return ctrl.Result{}, err
    }
    
    // 2. 배포가 원하는 상태인지 확인
    size := myApp.Spec.Size
    if *deployment.Spec.Replicas != size {
        deployment.Spec.Replicas = &size
        if err := r.Update(ctx, deployment); err != nil {
            log.Error(err, "Failed to update Deployment")
            return ctrl.Result{}, err
        }
        // 배포 업데이트 성공
        return ctrl.Result{Requeue: true}, nil
    }
    
    // 3. 상태 업데이트
    if myApp.Status.AvailableReplicas != deployment.Status.AvailableReplicas {
        myApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
        if err := r.Status().Update(ctx, &myApp); err != nil {
            log.Error(err, "Failed to update MyApp status")
            return ctrl.Result{}, err
        }
    }
    
    return ctrl.Result{}, nil
}

// 배포 생성 함수
func (r *MyAppReconciler) deploymentForMyApp(m *appsv1alpha1.MyApp) *appsv1.Deployment {
    ls := labelsForMyApp(m.Name)
    replicas := m.Spec.Size

    dep := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      m.Name,
            Namespace: m.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: ls,
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: ls,
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{{
                        Image: m.Spec.Image,
                        Name:  "myapp",
                        Ports: []corev1.ContainerPort{{
                            ContainerPort: 8080,
                            Name:          "http",
                        }},
                    }},
                },
            },
        },
    }
    
    // 소유자 참조 설정
    ctrl.SetControllerReference(m, dep, r.Scheme)
    return dep
}
```

**4. 커스텀 리소스 정의:**

오퍼레이터가 관리할 커스텀 리소스의 API를 정의합니다.

```go
// MyApp API
type MyAppSpec struct {
    // 애플리케이션 이미지
    Image string `json:"image"`
    
    // 레플리카 수
    Size int32 `json:"size"`
    
    // 구성 옵션
    Config map[string]string `json:"config,omitempty"`
}

type MyAppStatus struct {
    // 사용 가능한 레플리카 수
    AvailableReplicas int32 `json:"availableReplicas"`
    
    // 마지막 업데이트 시간
    LastUpdateTime metav1.Time `json:"lastUpdateTime,omitempty"`
    
    // 상태 메시지
    Message string `json:"message,omitempty"`
}

// MyApp 리소스
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Replicas",type=integer,JSONPath=`.spec.size`
// +kubebuilder:printcolumn:name="Available",type=integer,JSONPath=`.status.availableReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`
type MyApp struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   MyAppSpec   `json:"spec,omitempty"`
    Status MyAppStatus `json:"status,omitempty"`
}
```

**5. Ansible 또는 Helm 기반 오퍼레이터:**

Operator SDK는 Go 외에도 Ansible 또는 Helm을 사용한 오퍼레이터 개발을 지원합니다.

**Ansible 기반 오퍼레이터:**
```bash
# Ansible 기반 오퍼레이터 생성
operator-sdk init --plugins=ansible --domain example.com
operator-sdk create api --group apps --version v1alpha1 --kind MyApp --generate-role

# roles/myapp/tasks/main.yml 편집
```

**Helm 기반 오퍼레이터:**
```bash
# Helm 기반 오퍼레이터 생성
operator-sdk init --plugins=helm --domain example.com --helm-chart=<chart-name>
```

**6. 오퍼레이터 배포 및 테스트:**

```bash
# 오퍼레이터 배포
make deploy

# 커스텀 리소스 생성
kubectl apply -f config/samples/

# 오퍼레이터 로그 확인
kubectl logs -f deployment/my-operator-controller-manager -n my-operator-system

# 리소스 상태 확인
kubectl get myapps
kubectl describe myapp my-app
```

**7. 오퍼레이터 성숙도 수준:**

오퍼레이터 성숙도 모델은 오퍼레이터의 기능 수준을 정의합니다:

1. **기본 설치**: 애플리케이션 설치 및 구성
2. **원활한 업그레이드**: 버전 간 자동 업그레이드
3. **전체 수명 주기**: 백업, 복원, 장애 복구 등
4. **애플리케이션별 기능**: 자동 스케일링, 튜닝 등
5. **자동 조정**: 모니터링 기반 자동 최적화

**8. 모범 사례:**

- 점진적으로 기능 구현 (단순한 것부터 시작)
- 철저한 오류 처리 및 로깅
- 멱등성 보장 (동일한 입력에 대해 항상 동일한 결과)
- 소유자 참조 설정 (리소스 계층 구조 및 가비지 컬렉션)
- 상태 업데이트를 통한 진행 상황 보고
- 단위 테스트 및 통합 테스트 작성
- 명확한 문서화
</details>
3. Kubernetes의 어드미션 웹훅(Admission Webhook)의 종류와 각각의 사용 사례를 설명하세요.

<details>
<summary>정답 보기</summary>

**정답:**

**Kubernetes 어드미션 웹훅(Admission Webhook)의 종류와 사용 사례:**

어드미션 웹훅은 Kubernetes API 서버가 요청을 영구 저장소(etcd)에 저장하기 전에 요청을 가로채고 수정하거나 검증할 수 있는 메커니즘입니다. 어드미션 웹훅은 크게 두 가지 유형으로 나뉩니다: 변경(Mutating) 웹훅과 검증(Validating) 웹훅.

**1. 변경 웹훅(Mutating Webhook):**

변경 웹훅은 API 서버에 들어오는 요청 객체를 수정할 수 있습니다. 이 웹훅은 검증 웹훅보다 먼저 실행됩니다.

**주요 특징:**
- 요청 객체를 수정할 수 있음
- 여러 변경 웹훅이 체인으로 실행됨
- 각 웹훅은 이전 웹훅이 수정한 객체를 받음

**구성 예시:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: sidecar-injector
      path: "/inject"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**일반적인 사용 사례:**

1. **사이드카 컨테이너 주입:**
   - Istio, Linkerd와 같은 서비스 메시에서 프록시 사이드카 자동 주입
   - 로깅, 모니터링 사이드카 추가
   - 예시: Istio의 사이드카 주입기는 포드 생성 시 Envoy 프록시 컨테이너를 자동으로 추가

2. **기본값 설정:**
   - 리소스 요청 및 제한 자동 설정
   - 보안 컨텍스트 기본값 적용
   - 레이블 및 어노테이션 자동 추가
   - 예시: 모든 포드에 기본 CPU 및 메모리 요청 설정

3. **이미지 정책 적용:**
   - 이미지 레지스트리 URL 수정
   - 이미지 태그를 다이제스트로 변환
   - 예시: `nginx:latest`를 `internal-registry.example.com/nginx:v1.19.0`으로 변경

4. **볼륨 수정:**
   - 기본 볼륨 마운트 추가
   - ConfigMap 또는 Secret 자동 마운트
   - 예시: 모든 포드에 서비스 계정 토큰 볼륨 자동 마운트

5. **네트워크 정책 적용:**
   - 기본 네트워크 설정 추가
   - DNS 구성 수정
   - 예시: 특정 네임스페이스의 모든 포드에 특정 DNS 설정 적용

**2. 검증 웹훅(Validating Webhook):**

검증 웹훅은 API 서버에 들어오는 요청을 검증하고 허용하거나 거부할 수 있습니다. 이 웹훅은 변경 웹훅 이후에 실행됩니다.

**주요 특징:**
- 요청 객체를 수정할 수 없음
- 요청을 허용하거나 거부만 가능
- 여러 검증 웹훅이 병렬로 실행됨
- 모든 웹훅이 요청을 허용해야 요청이 처리됨

**구성 예시:**
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-validator
webhooks:
- name: pod-policy.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: pod-policy-validator
      path: "/validate"
    caBundle: <base64-encoded-ca-cert>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE", "UPDATE"]
    resources: ["pods"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
```

**일반적인 사용 사례:**

1. **보안 정책 적용:**
   - 특권 컨테이너 금지
   - 루트 사용자 실행 금지
   - 호스트 네트워크/PID/IPC 사용 제한
   - 예시: 특권 모드로 실행되는 포드 거부

2. **리소스 제약 조건 검증:**
   - 리소스 요청 및 제한 필수화
   - 리소스 상한 적용
   - QoS 클래스 강제
   - 예시: 메모리 제한이 없는 포드 거부

3. **이미지 정책 검증:**
   - 승인된 레지스트리만 허용
   - 최신 태그 사용 금지
   - 취약점 스캔 결과 확인
   - 예시: 공식 레지스트리에서 가져온 이미지만 허용

4. **레이블 및 어노테이션 검증:**
   - 필수 레이블 확인
   - 레이블 형식 검증
   - 예시: 모든 포드에 `app` 및 `environment` 레이블 필수화

5. **네임스페이스 기반 정책:**
   - 네임스페이스별 리소스 제한
   - 네임스페이스별 기능 제한
   - 예시: 프로덕션 네임스페이스에서는 더 엄격한 정책 적용

**3. 웹훅 구현 방법:**

어드미션 웹훅은 HTTPS 엔드포인트를 제공하는 서비스로 구현됩니다. 이 서비스는 `AdmissionReview` 요청을 받아 처리하고 `AdmissionResponse`를 반환합니다.

**기본 웹훅 서버 구현 예시 (Go):**

```go
package main

import (
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
    
    admissionv1 "k8s.io/api/admission/v1"
    corev1 "k8s.io/api/core/v1"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/runtime/serializer"
)

var (
    runtimeScheme = runtime.NewScheme()
    codecs        = serializer.NewCodecFactory(runtimeScheme)
    deserializer  = codecs.UniversalDeserializer()
)

// 변경 웹훅 핸들러
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }
    
    // AdmissionReview 요청 디코딩
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }
    
    // 포드 객체 디코딩
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }
    
    // 패치 생성 (사이드카 컨테이너 추가)
    patch := []map[string]interface{}{
        {
            "op": "add",
            "path": "/spec/containers/-",
            "value": map[string]interface{}{
                "name": "sidecar",
                "image": "sidecar-image:latest",
                "resources": map[string]interface{}{
                    "limits": map[string]interface{}{
                        "cpu": "100m",
                        "memory": "100Mi",
                    },
                    "requests": map[string]interface{}{
                        "cpu": "50m",
                        "memory": "50Mi",
                    },
                },
            },
        },
    }
    
    // 패치를 JSON으로 변환
    patchBytes, err := json.Marshal(patch)
    if err != nil {
        http.Error(w, "Failed to marshal patch", http.StatusInternalServerError)
        return
    }
    
    // 응답 생성
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: true,
        Patch:   patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }
    
    // 응답 전송
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

// 검증 웹훅 핸들러
func validateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }
    
    // AdmissionReview 요청 디코딩
    admissionReview := admissionv1.AdmissionReview{}
    if _, _, err := deserializer.Decode(body, nil, &admissionReview); err != nil {
        http.Error(w, "Failed to decode request", http.StatusBadRequest)
        return
    }
    
    // 포드 객체 디코딩
    pod := corev1.Pod{}
    if err := json.Unmarshal(admissionReview.Request.Object.Raw, &pod); err != nil {
        http.Error(w, "Failed to decode pod", http.StatusBadRequest)
        return
    }
    
    // 검증 로직
    allowed := true
    var message string
    
    // 특권 컨테이너 검사
    for _, container := range pod.Spec.Containers {
        if container.SecurityContext != nil && container.SecurityContext.Privileged != nil && *container.SecurityContext.Privileged {
            allowed = false
            message = "Privileged containers are not allowed"
            break
        }
    }
    
    // 응답 생성
    admissionResponse := admissionv1.AdmissionResponse{
        UID:     admissionReview.Request.UID,
        Allowed: allowed,
    }
    
    if !allowed {
        admissionResponse.Result = &metav1.Status{
            Message: message,
            Status:  "Failure",
            Reason:  metav1.StatusReasonForbidden,
            Code:    403,
        }
    }
    
    // 응답 전송
    admissionReview.Response = &admissionResponse
    resp, err := json.Marshal(admissionReview)
    if err != nil {
        http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
        return
    }
    
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}

func main() {
    http.HandleFunc("/mutate", mutateHandler)
    http.HandleFunc("/validate", validateHandler)
    
    fmt.Println("Starting webhook server on :8443")
    http.ListenAndServeTLS(":8443", "tls.crt", "tls.key", nil)
}
```

**4. 웹훅 배포 및 구성:**

웹훅 서버는 일반적으로 Kubernetes 클러스터 내에 배포되며, 서비스와 TLS 인증서가 필요합니다.

```yaml
# 웹훅 서버 배포
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-server
  template:
    metadata:
      labels:
        app: webhook-server
    spec:
      containers:
      - name: server
        image: webhook-server:latest
        ports:
        - containerPort: 8443
        volumeMounts:
        - name: tls
          mountPath: "/etc/webhook/certs"
          readOnly: true
      volumes:
      - name: tls
        secret:
          secretName: webhook-server-tls

---
# 웹훅 서버 서비스
apiVersion: v1
kind: Service
metadata:
  name: webhook-server
  namespace: webhook-system
spec:
  selector:
    app: webhook-server
  ports:
  - port: 443
    targetPort: 8443
```

**5. 모범 사례:**

- **성능 최적화**: 웹훅은 API 서버 요청 경로에 있으므로 빠르게 응답해야 합니다.
- **오류 처리**: 웹훅 서버 장애 시 동작을 고려하여 `failurePolicy`를 적절히 설정합니다.
- **범위 제한**: 필요한 리소스 및 작업에만 웹훅을 적용합니다.
- **테스트**: 다양한 시나리오에서 웹훅의 동작을 철저히 테스트합니다.
- **모니터링**: 웹훅 서버의 성능 및 오류를 모니터링합니다.
- **버전 관리**: API 버전 변경에 대비하여 여러 버전의 AdmissionReview를 지원합니다.
</details>

## 실습 문제

1. 다음 요구 사항에 맞는 CustomResourceDefinition(CRD)을 작성하세요:
   - API 그룹: webapp.example.com
   - 버전: v1
   - 종류(Kind): WebApp
   - 스코프: Namespaced
   - 필수 필드: spec.image, spec.replicas
   - 검증 규칙: replicas는 1에서 10 사이의 정수여야 함
   - 상태 하위 리소스 활성화

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.webapp.example.com
spec:
  group: webapp.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required: ["spec"]
          properties:
            spec:
              type: object
              required: ["image", "replicas"]
              properties:
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                port:
                  type: integer
                  default: 80
                env:
                  type: array
                  items:
                    type: object
                    required: ["name"]
                    properties:
                      name:
                        type: string
                      value:
                        type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                phase:
                  type: string
      subresources:
        status: {}
      additionalPrinterColumns:
      - name: Replicas
        type: integer
        jsonPath: .spec.replicas
      - name: Image
        type: string
        jsonPath: .spec.image
      - name: Age
        type: date
        jsonPath: .metadata.creationTimestamp
  scope: Namespaced
  names:
    plural: webapps
    singular: webapp
    kind: WebApp
    shortNames:
    - wa
```

이 CRD는 다음과 같은 특징을 가집니다:

1. **기본 정보**:
   - API 그룹: `webapp.example.com`
   - 버전: `v1`
   - 종류(Kind): `WebApp`
   - 스코프: `Namespaced`

2. **스키마 검증**:
   - `spec` 필드는 필수입니다.
   - `spec.image`와 `spec.replicas`는 필수 필드입니다.
   - `spec.replicas`는 1에서 10 사이의 정수여야 합니다.
   - `spec.port`는 선택적 필드이며 기본값은 80입니다.
   - `spec.env`는 선택적 필드로 환경 변수 배열을 정의합니다.

3. **상태 하위 리소스**:
   - `status` 하위 리소스가 활성화되어 있어 컨트롤러가 상태를 업데이트할 수 있습니다.
   - `status.availableReplicas`와 `status.phase` 필드가 정의되어 있습니다.

4. **추가 프린터 열**:
   - `kubectl get webapps` 명령 실행 시 Replicas, Image, Age 열이 표시됩니다.

5. **이름 구성**:
   - 복수형: `webapps`
   - 단수형: `webapp`
   - 종류: `WebApp`
   - 짧은 이름: `wa`

이 CRD를 사용하여 다음과 같은 커스텀 리소스를 생성할 수 있습니다:

```yaml
apiVersion: webapp.example.com/v1
kind: WebApp
metadata:
  name: my-webapp
  namespace: default
spec:
  image: nginx:1.19
  replicas: 3
  port: 8080
  env:
    - name: ENV_VAR1
      value: "value1"
    - name: ENV_VAR2
      value: "value2"
```

컨트롤러는 이 리소스를 감시하고 상태를 업데이트할 수 있습니다:

```yaml
status:
  availableReplicas: 3
  phase: Running
```
</details>

2. 다음 요구 사항에 맞는 변경(Mutating) 어드미션 웹훅 구성을 작성하세요:
   - 모든 포드 생성 요청에 사이드카 컨테이너 추가
   - 특정 네임스페이스(monitoring)에만 적용
   - 웹훅 서비스: webhook-service.webhook-system.svc
   - 경로: /mutate

<details>
<summary>정답 보기</summary>

**정답:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: sidecar-injector
webhooks:
- name: sidecar-injector.example.com
  clientConfig:
    service:
      namespace: webhook-system
      name: webhook-service
      path: "/mutate"
    caBundle: ${CA_BUNDLE}  # 실제 환경에서는 base64로 인코딩된 CA 인증서로 대체
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    operations: ["CREATE"]
    resources: ["pods"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      monitoring-injection: enabled
  admissionReviewVersions: ["v1", "v1beta1"]
  sideEffects: None
  timeoutSeconds: 5
  failurePolicy: Fail
---
# 네임스페이스에 레이블 추가
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    monitoring-injection: enabled
```

이 구성은 다음과 같은 특징을 가집니다:

1. **웹훅 구성**:
   - 이름: `sidecar-injector`
   - 웹훅 서비스: `webhook-service.webhook-system.svc`
   - 경로: `/mutate`

2. **적용 범위**:
   - API 그룹: `""`(코어 API 그룹)
   - API 버전: `v1`
   - 작업: `CREATE`(포드 생성 시에만 적용)
   - 리소스: `pods`
   - 스코프: `Namespaced`

3. **네임스페이스 선택기**:
   - `monitoring-injection: enabled` 레이블이 있는 네임스페이스에만 적용
   - `monitoring` 네임스페이스에 이 레이블을 추가

4. **추가 설정**:
   - `admissionReviewVersions`: 지원하는 AdmissionReview API 버전
   - `sideEffects`: 웹훅의 부작용 없음
   - `timeoutSeconds`: 웹훅 응답 대기 시간
   - `failurePolicy`: 웹훅 실패 시 요청 거부

웹훅 서버는 다음과 같은 로직을 구현해야 합니다:

```go
func mutateHandler(w http.ResponseWriter, r *http.Request) {
    // 요청 디코딩
    body, _ := ioutil.ReadAll(r.Body)
    admissionReview := admissionv1.AdmissionReview{}
    deserializer.Decode(body, nil, &admissionReview)
    
    // 포드 객체 디코딩
    pod := corev1.Pod{}
    json.Unmarshal(admissionReview.Request.Object.Raw, &pod)
    
    // 사이드카 컨테이너 정의
    sidecarContainer := corev1.Container{
        Name:  "monitoring-sidecar",
        Image: "monitoring-agent:latest",
        Resources: corev1.ResourceRequirements{
            Limits: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("100m"),
                corev1.ResourceMemory: resource.MustParse("100Mi"),
            },
            Requests: corev1.ResourceList{
                corev1.ResourceCPU:    resource.MustParse("50m"),
                corev1.ResourceMemory: resource.MustParse("50Mi"),
            },
        },
        VolumeMounts: []corev1.VolumeMount{
            {
                Name:      "shared-data",
                MountPath: "/var/monitoring",
            },
        },
    }
    
    // 패치 생성
    patch := []map[string]interface{}{
        {
            "op":    "add",
            "path":  "/spec/containers/-",
            "value": sidecarContainer,
        },
        {
            "op":   "add",
            "path": "/spec/volumes/-",
            "value": map[string]interface{}{
                "name": "shared-data",
                "emptyDir": map[string]interface{}{},
            },
        },
    }
    
    // 패치를 JSON으로 변환
    patchBytes, _ := json.Marshal(patch)
    
    // 응답 생성
    admissionResponse := admissionv1.AdmissionResponse{
        UID:       admissionReview.Request.UID,
        Allowed:   true,
        Patch:     patchBytes,
        PatchType: func() *admissionv1.PatchType {
            pt := admissionv1.PatchTypeJSONPatch
            return &pt
        }(),
    }
    
    // 응답 전송
    admissionReview.Response = &admissionResponse
    resp, _ := json.Marshal(admissionReview)
    w.Header().Set("Content-Type", "application/json")
    w.Write(resp)
}
```

이 웹훅은 `monitoring` 네임스페이스에 생성되는 모든 포드에 모니터링 사이드카 컨테이너를 자동으로 추가합니다. 사이드카 컨테이너는 모니터링 에이전트 이미지를 사용하고, 공유 볼륨을 마운트하여 메인 컨테이너와 데이터를 공유할 수 있습니다.
</details>
