# KRO Helm 마이그레이션 퀴즈

> **관련 문서**: [KRO를 활용한 Helm 차트 마이그레이션](../../package-management/02-kro-helm-migration.md)

## 객관식 문제

### 1. Kubernetes Resource Operator(KRO)의 핵심 개념이 아닌 것은?

- A) 선언적 리소스 관계
- B) 상태 기반 조정
- C) 명령형 스크립트 실행
- D) 리소스 그래프

<details>
<summary>정답 보기</summary>

**정답: C) 명령형 스크립트 실행**

**설명:**
KRO는 선언적 방식으로 리소스를 관리합니다. 선언적 리소스 관계, 상태 기반 조정, 리소스 그래프, 자동화된 수명 주기 관리가 핵심 개념이며, 명령형 스크립트 실행은 KRO의 핵심 개념이 아닙니다.

</details>

### 2. ResourceGraphDefinition(RGD)에서 `childResources`의 역할은 무엇입니까?

- A) 부모 리소스의 메타데이터를 정의
- B) 부모 리소스에서 생성될 자식 리소스 목록을 정의
- C) 클러스터 전역 설정을 정의
- D) 네임스페이스 정책을 정의

<details>
<summary>정답 보기</summary>

**정답: B) 부모 리소스에서 생성될 자식 리소스 목록을 정의**

**설명:**
`childResources`는 부모 커스텀 리소스에서 생성될 자식 Kubernetes 리소스(Deployment, Service, Ingress 등)의 목록과 템플릿을 정의합니다.

</details>

### 3. KRO와 Helm을 비교할 때, KRO의 주요 차별점은 무엇입니까?

- A) Go 템플릿 사용
- B) 차트 아카이브 패키징
- C) 명시적 리소스 관계 모델링과 자동 상태 전파
- D) 릴리스 기록 관리

<details>
<summary>정답 보기</summary>

**정답: C) 명시적 리소스 관계 모델링과 자동 상태 전파**

**설명:**
KRO는 리소스 간의 관계를 명시적 그래프로 모델링하고 자식 리소스의 상태를 부모 리소스에 자동으로 전파합니다.

</details>

### 4. RGD 템플릿에서 `.parent`는 무엇을 참조합니까?

- A) Kubernetes 클러스터
- B) 부모 커스텀 리소스
- C) 네임스페이스
- D) 컨트롤러 파드

<details>
<summary>정답 보기</summary>

**정답: B) 부모 커스텀 리소스**

**설명:**
RGD 템플릿에서 `.parent`는 ResourceGraphDefinition이 적용된 부모 커스텀 리소스를 참조합니다.

</details>

### 5. KRO에서 조건부 자식 리소스 생성에 사용되는 필드는?

- A) `when`
- B) `if`
- C) `condition`
- D) `enabled`

<details>
<summary>정답 보기</summary>

**정답: C) `condition`**

**설명:**
RGD의 childResources에서 `condition` 필드를 사용하여 조건부로 자식 리소스를 생성할 수 있습니다.

</details>

### 6. KRO에서 `statusMappings`의 목적은 무엇입니까?

- A) 오류 처리 동작 정의
- B) 자식 리소스 상태를 부모 리소스 상태에 매핑
- C) 로깅 레벨 구성
- D) 리소스 쿼터 설정

<details>
<summary>정답 보기</summary>

**정답: B) 자식 리소스 상태를 부모 리소스 상태에 매핑**

**설명:**
`statusMappings`는 자식 리소스에서 상태 정보를 추출하여 부모 커스텀 리소스의 상태 필드로 전파하는 방법을 정의합니다.

</details>

### 7. KRO가 리소스 의존성을 처리하는 방법은?

- A) YAML 파일의 수동 순서 지정
- B) 리소스 그래프로 자동 생성 순서 결정
- C) 숫자 우선순위 필드 사용
- D) 알파벳 순서 정렬

<details>
<summary>정답 보기</summary>

**정답: B) 리소스 그래프로 자동 생성 순서 결정**

**설명:**
KRO는 리소스 그래프를 사용하여 리소스 간의 의존성을 이해하고 리소스 생성 및 삭제의 올바른 순서를 자동으로 결정합니다.

</details>

### 8. KRO에서 부모 커스텀 리소스가 삭제되면 어떻게 됩니까?

- A) 자식 리소스가 고아로 남음
- B) 자식 리소스가 자동으로 가비지 컬렉션됨
- C) 수동 정리 필요
- D) 오류 발생

<details>
<summary>정답 보기</summary>

**정답: B) 자식 리소스가 자동으로 가비지 컬렉션됨**

**설명:**
KRO는 자식 리소스에 소유자 참조를 설정하므로, 부모가 삭제되면 Kubernetes의 가비지 컬렉터가 자동으로 모든 자식 리소스를 제거합니다.

</details>

### 9. KRO에서 커스텀 리소스 변경을 감시하는 컴포넌트는?

- A) API 서버
- B) 스케줄러
- C) KRO 컨트롤러
- D) Kubelet

<details>
<summary>정답 보기</summary>

**정답: C) KRO 컨트롤러**

**설명:**
KRO 컨트롤러는 ResourceGraphDefinition으로 정의된 커스텀 리소스의 변경을 감시하고 원하는 상태를 조정합니다.

</details>

### 10. Helm의 `helm upgrade --install` 동작에 해당하는 KRO 방식은?

- A) 커스텀 리소스에 `kubectl apply`
- B) 커스텀 리소스에 `kubectl replace`
- C) 커스텀 리소스에 `kubectl patch`
- D) `kubectl create --save-config`

<details>
<summary>정답 보기</summary>

**정답: A) 커스텀 리소스에 `kubectl apply`**

**설명:**
`kubectl apply`는 `helm upgrade --install`과 유사한 멱등성 동작을 제공합니다. 리소스가 없으면 생성하고 있으면 업데이트합니다.

</details>

## 단답형 문제

### 1. KRO에서 커스텀 리소스와 Kubernetes 네이티브 리소스 간의 관계를 정의하는 핵심 리소스는 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: ResourceGraphDefinition (RGD)**

**설명:**
ResourceGraphDefinition(RGD)은 KRO의 핵심 구성 요소로, 커스텀 리소스(부모)와 Kubernetes 네이티브 리소스(자식) 간의 관계를 선언적으로 정의합니다.

</details>

### 2. Helm의 values.yaml에 해당하는 KRO의 개념은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: 커스텀 리소스(CR)의 spec**

**설명:**
Helm에서 values.yaml로 구성을 커스터마이징하는 것처럼, KRO에서는 커스텀 리소스의 spec 필드를 통해 애플리케이션 구성을 정의합니다.

</details>

### 3. RGD 템플릿에서 형제 자식 리소스의 출력을 참조하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: `.children.<resourceId>` 구문 사용**

**설명:**
RGD 템플릿에서 `.children.<resourceId>`를 사용하여 다른 자식 리소스의 metadata, spec, status 필드에 접근할 수 있습니다.

</details>

### 4. KRO가 관리되는 리소스를 추적하는 데 사용하는 어노테이션은?

<details>
<summary>정답 보기</summary>

**정답: `kro.run/owner` 어노테이션**

**설명:**
KRO는 Kubernetes 소유자 참조와 함께 `kro.run/owner` 어노테이션을 사용하여 어떤 리소스가 어떤 부모 커스텀 리소스에 의해 관리되는지 추적합니다.

</details>

### 5. KRO가 커스텀 리소스의 스키마 검증을 처리하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: RGD의 spec.schema 필드에 정의된 OpenAPI v3 스키마 사용**

**설명:**
KRO는 RGD에서 CRD를 생성하며, ResourceGraphDefinition에 정의된 OpenAPI v3 스키마를 사용하여 스키마 검증을 수행합니다.

</details>

## 실습 문제

### 1. 다음 Helm values.yaml을 KRO 커스텀 리소스 인스턴스로 변환하세요.

```yaml
# Helm values.yaml
replicaCount: 2
image:
  repository: myapp
  tag: "1.0.0"
service:
  type: ClusterIP
  port: 8080
```

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: kro.example.com/v1
kind: MyApp
metadata:
  name: my-application
spec:
  replicas: 2
  image:
    repository: myapp
    tag: "1.0.0"
  service:
    type: ClusterIP
    port: 8080
```

</details>

### 2. 부모 spec을 기반으로 Deployment를 생성하는 RGD childResource 정의를 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
childResources:
  - id: deployment
    resource:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{.parent.metadata.name}}"
      spec:
        replicas: "{{.parent.spec.replicas}}"
        selector:
          matchLabels:
            app: "{{.parent.metadata.name}}"
        template:
          metadata:
            labels:
              app: "{{.parent.metadata.name}}"
          spec:
            containers:
              - name: app
                image: "{{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}"
                ports:
                  - containerPort: "{{.parent.spec.service.port}}"
```

</details>

### 3. Deployment의 availableReplicas를 부모 상태에 노출하는 statusMappings 구성을 작성하세요.

<details>
<summary>정답 보기</summary>

```yaml
statusMappings:
  - childResourceId: deployment
    fieldPath: status.availableReplicas
    parentFieldPath: status.availableReplicas
  - childResourceId: deployment
    fieldPath: status.conditions
    parentFieldPath: status.deploymentConditions
```

**설명:**
statusMappings는 자식 리소스 상태에서 특정 필드를 추출하여 부모 커스텀 리소스의 상태에 매핑하므로, 사용자가 부모 리소스를 통해 애플리케이션 상태를 확인할 수 있습니다.

</details>

## 심화 문제

### 1. KRO를 사용한 멀티 환경(개발/스테이징/프로덕션) 배포 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

**환경별 커스텀 리소스 인스턴스:**

```yaml
# dev/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-dev
spec:
  replicas: 1
  image:
    tag: "dev-latest"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
---
# staging/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-staging
spec:
  replicas: 2
  image:
    tag: "rc-1.0.0"
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
---
# production/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-prod
spec:
  replicas: 3
  image:
    tag: "v1.0.0"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
```

**GitOps 통합:**
ArgoCD ApplicationSet으로 환경별 배포를 단일 RGD로 모든 환경에 자동화합니다.

</details>

### 2. 데이터베이스 클러스터와 같은 상태 저장 애플리케이션 관리에서 Helm과 KRO의 운영 차이점을 비교하세요.

<details>
<summary>정답 보기</summary>

**Helm 접근 방식:**
- 템플릿 기반: 설치 시점에 정적 매니페스트 생성
- 릴리스 관리: Secrets/ConfigMaps로 버전 추적
- 업그레이드 프로세스: `helm upgrade` 명령어 필요
- 상태 추적: 초기 배포 후 내장 조정 없음
- 롤백: 저장된 릴리스 히스토리 사용

**KRO 접근 방식:**
- 조정 기반: 지속적으로 드리프트 모니터링 및 수정
- 네이티브 Kubernetes: 표준 kubectl과 CRD 사용
- 업그레이드 프로세스: CR spec 수정 시 컨트롤러가 조정
- 상태 추적: 컨트롤러가 지속적으로 감시 및 조정
- 롤백: CR spec을 이전 상태로 되돌림

**상태 저장 애플리케이션의 주요 차이점:**

| 측면 | Helm | KRO |
|------|------|-----|
| 드리프트 감지 | 수동 | 자동 |
| 자가 복구 | 없음 | 있음 |
| 상태 가시성 | 외부 (helm status) | 네이티브 (kubectl get) |
| 의존성 관리 | 차트 의존성 | 리소스 그래프 |
| 수명 주기 훅 | pre/post 훅 | 컨트롤러 로직 |

**권장 사항:**
KRO는 지속적인 조정, 자동 드리프트 수정, 복잡한 수명 주기 관리가 필요한 상태 저장 애플리케이션에 더 적합합니다. Helm은 간단한 배포의 상태 비저장 애플리케이션에 더 단순합니다.

</details>
