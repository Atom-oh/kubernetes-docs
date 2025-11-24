# Kubernetes Resource Operator (KRO)를 활용한 Helm 차트 마이그레이션

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33  
> **마지막 업데이트**: 2025년 11월 24일

## 개요

Kubernetes Resource Operator(KRO)는 Kubernetes 리소스를 선언적으로 관리하는 새로운 접근 방식입니다. 이 문서에서는 기존 Helm 차트를 KRO로 마이그레이션하는 방법을 설명하고, 이를 통해 얻을 수 있는 이점을 살펴봅니다.

## KRO 핵심 개념

### Kubernetes Resource Operator란?

Kubernetes Resource Operator(KRO)는 Kubernetes 리소스 간의 관계를 선언적으로 정의하고 관리하기 위한 프레임워크입니다. KRO는 다음과 같은 핵심 개념을 기반으로 합니다:

1. **선언적 리소스 관계**: 리소스 간의 관계를 명시적으로 정의하여 복잡한 애플리케이션 구조를 표현합니다.
2. **상태 기반 조정**: 원하는 상태와 실제 상태 간의 차이를 지속적으로 조정합니다.
3. **리소스 그래프**: 리소스 간의 의존성과 관계를 그래프 형태로 모델링합니다.
4. **자동화된 수명 주기 관리**: 리소스의 생성, 업데이트, 삭제를 자동으로 처리합니다.

### ResourceGraphDefinition(RGD)

ResourceGraphDefinition(RGD)은 KRO의 핵심 구성 요소로, 커스텀 리소스와 그에 종속된 Kubernetes 네이티브 리소스 간의 관계를 정의합니다. RGD는 다음과 같은 기능을 제공합니다:

1. **부모-자식 관계 정의**: 상위 리소스(부모)와 하위 리소스(자식) 간의 계층 구조를 정의합니다.
2. **템플릿 기반 리소스 생성**: 부모 리소스의 속성을 기반으로 자식 리소스를 동적으로 생성합니다.
3. **상태 전파**: 자식 리소스의 상태를 부모 리소스에 전파하여 전체 애플리케이션 상태를 파악할 수 있게 합니다.
4. **의존성 관리**: 자식 리소스 간의 의존성을 정의하여 올바른 순서로 생성 및 업데이트되도록 합니다.

### KRO vs 기존 접근 방식

KRO는 기존의 Kubernetes 리소스 관리 접근 방식과 비교하여 다음과 같은 차별점을 가집니다:

| 특징 | KRO | Helm | Operator SDK | Kustomize |
|------|-----|------|--------------|-----------|
| **리소스 관계 모델링** | 명시적 그래프 | 암시적 | 코드 기반 | 없음 |
| **상태 전파** | 자동 | 수동 | 코드 기반 | 없음 |
| **의존성 관리** | 선언적 | 암시적 | 코드 기반 | 없음 |
| **확장성** | 높음 | 중간 | 높음 | 낮음 |
| **학습 곡선** | 중간 | 낮음 | 높음 | 낮음 |
| **GitOps 친화성** | 높음 | 중간 | 중간 | 높음 |

### KRO 아키텍처

KRO는 다음과 같은 구성 요소로 이루어져 있습니다:

1. **KRO 컨트롤러**: ResourceGraphDefinition을 감시하고 리소스 그래프를 관리합니다.
2. **리소스 그래프 엔진**: 리소스 간의 관계와 의존성을 처리합니다.
3. **상태 관리자**: 리소스의 상태를 추적하고 전파합니다.
4. **조정 루프**: 원하는 상태와 실제 상태 간의 차이를 조정합니다.

```
+-------------------+     +-------------------+     +-------------------+
|  커스텀 리소스    |     | ResourceGraph     |     | Kubernetes        |
|  (CR)            |<--->| Definition        |<--->| 네이티브 리소스    |
+-------------------+     +-------------------+     +-------------------+
         ^                        ^                         ^
         |                        |                         |
         v                        v                         v
+-----------------------------------------------------------------------+
|                          KRO 컨트롤러                                  |
|                                                                       |
|  +----------------+  +----------------+  +----------------+           |
|  | 리소스 그래프  |  |   상태 관리자  |  |   조정 루프    |           |
|  |     엔진       |  |                |  |                |           |
|  +----------------+  +----------------+  +----------------+           |
+-----------------------------------------------------------------------+
```

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구
- kubectl v1.31 이상
- Helm v3.10 이상
- kro CLI v0.5.0 이상
- 작동하는 Kubernetes 클러스터 (EKS, minikube, kind 등)

### KRO 설치

```bash
# KRO 컨트롤러 설치
kubectl apply -f https://github.com/kro-project/kro/releases/download/v0.5.0/kro-controller.yaml

# KRO CLI 설치
curl -L https://github.com/kro-project/kro/releases/download/v0.5.0/kro-cli-$(uname -s)-$(uname -m) -o kro
chmod +x kro
sudo mv kro /usr/local/bin/

# 설치 확인
kubectl get pods -n kro-system
```

## Helm과 KRO 비교

### Helm

Helm은 Kubernetes 애플리케이션을 패키징하고 배포하는 데 널리 사용되는 도구입니다. Helm은 다음과 같은 특징을 가지고 있습니다:

- **템플릿 기반**: Go 템플릿 언어를 사용하여 Kubernetes 매니페스트를 생성
- **차트 개념**: 애플리케이션을 패키징하는 단위
- **릴리스 관리**: 배포된 애플리케이션의 버전 관리
- **중앙 저장소**: 차트를 공유하고 재사용하기 위한 저장소

### Kubernetes Resource Operator (KRO)

KRO는 Kubernetes 커스텀 리소스를 사용하여 애플리케이션을 관리하는 접근 방식입니다:

- **선언적 API**: Kubernetes 네이티브 방식으로 리소스 정의
- **상태 기반**: 원하는 상태를 선언하고 컨트롤러가 실제 상태를 조정
- **GitOps 친화적**: 버전 제어 시스템과 통합이 용이
- **확장성**: 커스텀 리소스 정의(CRD)를 통한 확장

### 비교 표

| 기능 | Helm | KRO |
|------|------|-----|
| **패키징 방식** | 차트 (tgz 아카이브) | 커스텀 리소스 |
| **템플릿 엔진** | Go 템플릿 | 없음 (순수 YAML) |
| **버전 관리** | 릴리스 기록 | Git 기반 |
| **롤백 메커니즘** | helm rollback | GitOps 기반 롤백 |
| **의존성 관리** | requirements.yaml | ResourceGraphDefinition |
| **사용자 정의** | values.yaml | CR 스펙 |
| **설치 방법** | helm install | kubectl apply |
| **업그레이드 방법** | helm upgrade | kubectl apply |
| **삭제 방법** | helm uninstall | kubectl delete |
| **후크** | 설치/업그레이드/삭제 후크 | Kubernetes 이벤트 기반 |

## Helm에서 KRO로 마이그레이션하는 이유

1. **Kubernetes 네이티브 접근 방식**: KRO는 Kubernetes의 선언적 API 모델을 따르므로 더 일관된 경험 제공
2. **버전 관리 개선**: 각 리소스의 변경 사항을 개별적으로 추적 가능
3. **세분화된 제어**: 개별 리소스 수준에서 더 세밀한 제어 가능
4. **의존성 관리 간소화**: 명시적인 의존성 선언으로 복잡한 관계 관리 용이
5. **보안 강화**: 최소 권한 원칙에 따라 필요한 권한만 부여 가능
6. **상태 관리 개선**: 리소스 상태를 자동으로 전파하고 집계
7. **GitOps 워크플로우 통합**: 선언적 접근 방식으로 GitOps 도구와의 통합 용이

## 실제 예제: Nginx Helm 차트를 KRO로 마이그레이션

### 기존 Helm 차트 (values.yaml)

```yaml
# Nginx Helm 차트 values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO 커스텀 리소스 정의

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
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
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### ResourceGraphDefinition 생성

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: nginxapp-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: NginxApp
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: nginx
                image: {{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}
                imagePullPolicy: {{.parent.spec.image.pullPolicy}}
                ports:
                - containerPort: {{.parent.spec.service.port}}
                resources:
                  {{- if .parent.spec.resources }}
                  limits:
                    {{- if .parent.spec.resources.limits.cpu }}
                    cpu: {{.parent.spec.resources.limits.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.limits.memory }}
                    memory: {{.parent.spec.resources.limits.memory}}
                    {{- end }}
                  requests:
                    {{- if .parent.spec.resources.requests.cpu }}
                    cpu: {{.parent.spec.resources.requests.cpu}}
                    {{- end }}
                    {{- if .parent.spec.resources.requests.memory }}
                    memory: {{.parent.spec.resources.requests.memory}}
                    {{- end }}
                  {{- end }}
    
    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.service.port}}
            targetPort: {{.parent.spec.service.port}}
          type: {{.parent.spec.service.type}}
    
    - apiVersion: networking.k8s.io/v1
      kind: Ingress
      nameTemplate: "{{.parent.metadata.name}}"
      condition: "{{.parent.spec.ingress.enabled}}"
      template: |
        spec:
          rules:
          {{- range .parent.spec.ingress.hosts }}
          - host: {{.host}}
            http:
              paths:
              {{- range .paths }}
              - path: {{.path}}
                pathType: {{.pathType}}
                backend:
                  service:
                    name: {{$.parent.metadata.name}}
                    port:
                      number: {{$.parent.spec.service.port}}
              {{- end }}
          {{- end }}
  
  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
      fieldMappings:
        - child: "status.availableReplicas"
          parent: "status.availableReplicas"
        - child: "status.readyReplicas"
          parent: "status.readyReplicas"
    
    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
```

### KRO 커스텀 리소스 인스턴스

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### 배포 및 검증

```bash
# CRD 및 RGD 적용
kubectl apply -f nginxapp-crd.yaml
kubectl apply -f nginxapp-rgd.yaml

# 커스텀 리소스 인스턴스 적용
kubectl apply -f my-nginx.yaml

# 생성된 리소스 확인
kubectl get deployments,services,ingress -l app=my-nginx

# 커스텀 리소스 상태 확인
kubectl get nginxapp my-nginx -o yaml
```

## KRO 사용 사례

### 1. 마이크로서비스 애플리케이션 관리

KRO는 여러 구성 요소로 이루어진 마이크로서비스 애플리케이션을 관리하는 데 이상적입니다. 각 마이크로서비스는 다음과 같은 리소스로 구성될 수 있습니다:

- Deployment 또는 StatefulSet
- Service
- ConfigMap
- Secret
- HorizontalPodAutoscaler
- PodDisruptionBudget

KRO를 사용하면 이러한 리소스 간의 관계를 명시적으로 정의하고, 단일 커스텀 리소스를 통해 전체 마이크로서비스를 관리할 수 있습니다.

### 2. 데이터베이스 클러스터 관리

데이터베이스 클러스터(예: PostgreSQL, MySQL)는 여러 구성 요소와 복잡한 설정이 필요합니다. KRO를 사용하면 다음과 같은 리소스를 관리할 수 있습니다:

- 마스터 및 레플리카 StatefulSet
- 서비스 엔드포인트
- 영구 볼륨 클레임
- 백업 및 복원 작업
- 모니터링 구성

### 3. 멀티 클러스터 애플리케이션 배포

KRO는 여러 Kubernetes 클러스터에 걸쳐 있는 애플리케이션을 관리하는 데도 사용할 수 있습니다. 이를 통해 다음과 같은 시나리오를 지원합니다:

- 지역별 배포
- 개발, 스테이징, 프로덕션 환경 간의 일관된 배포
- 하이브리드 클라우드 환경에서의 애플리케이션 관리

## KRO의 모범 사례

### 1. 리소스 그래프 설계

- **단일 책임 원칙**: 각 커스텀 리소스는 명확한 단일 책임을 가져야 합니다.
- **적절한 추상화 수준**: 너무 세부적이거나 너무 추상적이지 않은 적절한 수준의 추상화를 선택합니다.
- **명확한 경계**: 리소스 간의 경계와 책임을 명확히 정의합니다.
- **재사용성**: 공통 패턴을 식별하고 재사용 가능한 구성 요소로 추출합니다.

### 2. 상태 관리

- **의미 있는 상태**: 사용자에게 의미 있는 상태 정보를 제공합니다.
- **상태 집계**: 여러 자식 리소스의 상태를 적절히 집계합니다.
- **조건 정의**: 명확한 조건 유형과 상태를 정의합니다.
- **진단 정보**: 문제 해결에 도움이 되는 진단 정보를 포함합니다.

### 3. 버전 관리

- **API 버전 관리**: 커스텀 리소스 API의 버전을 적절히 관리합니다.
- **변환 웹훅**: 버전 간 변환을 위한 웹훅을 구현합니다.
- **하위 호환성**: 가능한 한 하위 호환성을 유지합니다.
- **점진적 마이그레이션**: 대규모 변경은 점진적으로 도입합니다.

### 4. 보안

- **최소 권한**: 컨트롤러에 필요한 최소한의 권한만 부여합니다.
- **RBAC 정책**: 적절한 RBAC 정책을 정의하여 액세스를 제어합니다.
- **비밀 관리**: 민감한 정보는 Secret으로 관리합니다.
- **검증 웹훅**: 입력 유효성 검사를 위한 웹훅을 구현합니다.

## 결론

Helm에서 KRO로의 마이그레이션은 Kubernetes 네이티브 접근 방식으로 전환하는 중요한 단계입니다. 이를 통해 더 선언적이고, 확장 가능하며, GitOps 친화적인 애플리케이션 관리가 가능해집니다. 특히 복잡한 애플리케이션의 경우, KRO는 더 세분화된 제어와 개선된 버전 관리를 제공합니다.

ResourceGraphDefinition(RGD)은 KRO의 핵심 개념으로, 리소스 간의 관계를 명시적으로 정의하고 상태를 전파하는 메커니즘을 제공합니다. 이를 통해 복잡한 애플리케이션 구조를 더 쉽게 모델링하고 관리할 수 있습니다.

마이그레이션 과정은 초기에 추가 작업이 필요하지만, 장기적으로는 유지 관리 및 운영 측면에서 상당한 이점을 제공합니다. 점진적인 마이그레이션 접근 방식을 통해 위험을 최소화하면서 KRO의 이점을 활용할 수 있습니다.

KRO는 아직 발전 중인 기술이지만, Kubernetes 생태계의 미래 방향성을 보여주는 중요한 접근 방식입니다. 선언적 API, 리소스 관계 모델링, 상태 전파와 같은 개념은 클라우드 네이티브 애플리케이션 관리의 핵심 원칙이 되고 있습니다.

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [KRO Helm 마이그레이션 퀴즈](../quizzes/advanced/07-kro-rgd-quiz.md)를 풀어보세요.

## Helm과 KRO 비교

### Helm

Helm은 Kubernetes 애플리케이션을 패키징하고 배포하는 데 널리 사용되는 도구입니다. Helm은 다음과 같은 특징을 가지고 있습니다:

- **템플릿 기반**: Go 템플릿 언어를 사용하여 Kubernetes 매니페스트를 생성
- **차트 개념**: 애플리케이션을 패키징하는 단위
- **릴리스 관리**: 배포된 애플리케이션의 버전 관리
- **중앙 저장소**: 차트를 공유하고 재사용하기 위한 저장소

### Kubernetes Resource Operator (KRO)

KRO는 Kubernetes 커스텀 리소스를 사용하여 애플리케이션을 관리하는 접근 방식입니다:

- **선언적 API**: Kubernetes 네이티브 방식으로 리소스 정의
- **상태 기반**: 원하는 상태를 선언하고 컨트롤러가 실제 상태를 조정
- **GitOps 친화적**: 버전 제어 시스템과 통합이 용이
- **확장성**: 커스텀 리소스 정의(CRD)를 통한 확장

### 비교 표

| 기능 | Helm | KRO |
|------|------|-----|
| **패키징 방식** | 차트 (tgz 아카이브) | 커스텀 리소스 |
| **템플릿 엔진** | Go 템플릿 | 없음 (순수 YAML) |
| **버전 관리** | 릴리스 기록 | Git 기반 |
| **롤백 메커니즘** | helm rollback | GitOps 기반 롤백 |
| **의존성 관리** | requirements.yaml | ResourceGraphDefinition |
| **사용자 정의** | values.yaml | CR 스펙 |
| **설치 방법** | helm install | kubectl apply |
| **업그레이드 방법** | helm upgrade | kubectl apply |
| **삭제 방법** | helm uninstall | kubectl delete |
| **후크** | 설치/업그레이드/삭제 후크 | Kubernetes 이벤트 기반 |

## Helm에서 KRO로 마이그레이션하는 이유

1. **Kubernetes 네이티브 접근 방식**: KRO는 Kubernetes의 선언적 API 모델을 따르므로 더 일관된 경험 제공
2. **버전 관리 개선**: 각 리소스의 변경 사항을 개별적으로 추적 가능
3. **세분화된 제어**: 개별 리소스 수준에서 더 세밀한 제어 가능
4. **의존성 관리 간소화**: 명시적인 의존성 선언으로 복잡한 관계 관리 용이
5. **보안 강화**: 최소 권한 원칙에 따라 필요한 권한만 부여 가능

## 마이그레이션 단계

### 1. Helm 차트 분석

```bash
# Helm 차트 구조 확인
helm template my-chart

# 생성되는 리소스 확인
helm template my-chart | kubectl api-resources --verbs=create -o name | xargs -n 1 grep -l "kind:" | sort -u
```

### 2. 커스텀 리소스 정의(CRD) 생성

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: applications.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: Application
    plural: applications
    singular: application
    shortNames:
      - app
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
              properties:
                # 애플리케이션 구성 스키마 정의
                replicas:
                  type: integer
                  minimum: 1
                image:
                  type: string
                port:
                  type: integer
              required: ["replicas", "image"]
```

### 3. ResourceGraphDefinition 개념 및 생성

#### ResourceGraphDefinition(RGD) 개념 이해

ResourceGraphDefinition(RGD)은 KRO의 핵심 개념으로, 커스텀 리소스와 Kubernetes 네이티브 리소스 간의 관계를 선언적으로 정의합니다. RGD는 다음과 같은 중요한 역할을 수행합니다:

1. **리소스 간 관계 정의**: 상위 리소스(부모)와 하위 리소스(자식) 간의 관계를 명시적으로 정의합니다.
2. **템플릿 기반 리소스 생성**: 부모 리소스의 속성을 기반으로 자식 리소스를 동적으로 생성합니다.
3. **상태 전파**: 자식 리소스의 상태를 부모 리소스에 전파하여 전체 애플리케이션 상태를 파악할 수 있게 합니다.
4. **수명 주기 관리**: 부모 리소스의 수명 주기에 따라 자식 리소스의 생성, 업데이트, 삭제를 자동으로 관리합니다.

#### RGD의 주요 구성 요소

1. **resourceKind**: RGD가 적용될 커스텀 리소스의 종류를 지정합니다.
   - `group`: API 그룹 (예: kro.example.com)
   - `kind`: 리소스 종류 (예: Application)
   - `version`: API 버전 (예: v1)

2. **childResources**: 부모 리소스에서 생성될 자식 리소스 목록을 정의합니다.
   - `apiVersion`: 자식 리소스의 API 버전
   - `kind`: 자식 리소스의 종류
   - `nameTemplate`: 자식 리소스의 이름을 생성하는 템플릿
   - `template`: 자식 리소스의 스펙을 정의하는 템플릿

3. **상태 매핑(statusMappings)**: 자식 리소스의 상태를 부모 리소스의 상태로 매핑하는 규칙을 정의합니다.
   - `childResource`: 상태를 가져올 자식 리소스 참조
   - `conditions`: 자식 리소스의 조건을 부모 리소스의 조건으로 매핑

4. **의존성 관리(dependencies)**: 자식 리소스 간의 의존성을 정의합니다.
   - `source`: 의존성의 소스 리소스
   - `target`: 의존성의 대상 리소스
   - `condition`: 의존성 조건 (예: Ready)

#### RGD 템플릿 문법

RGD 템플릿은 Go 템플릿 언어를 기반으로 하며, 다음과 같은 특별한 변수와 함수를 제공합니다:

1. **변수**:
   - `.parent`: 부모 리소스에 접근 (예: `.parent.metadata.name`)
   - `.children`: 다른 자식 리소스에 접근 (예: `.children.service.metadata.name`)

2. **함수**:
   - `include`: 다른 템플릿을 포함
   - `toYaml`: 객체를 YAML 형식으로 변환
   - `fromYaml`: YAML 문자열을 객체로 변환
   - `tpl`: 문자열을 템플릿으로 평가

#### ResourceGraphDefinition 예시

```yaml
apiVersion: kro.run/v1alpha1
kind: ResourceGraphDefinition
metadata:
  name: application-graph
spec:
  resourceKind:
    group: kro.example.com
    kind: Application
    version: v1
  childResources:
    - apiVersion: apps/v1
      kind: Deployment
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          replicas: {{.parent.spec.replicas}}
          selector:
            matchLabels:
              app: {{.parent.metadata.name}}
          template:
            metadata:
              labels:
                app: {{.parent.metadata.name}}
            spec:
              containers:
              - name: {{.parent.metadata.name}}
                image: {{.parent.spec.image}}
                ports:
                - containerPort: {{.parent.spec.port}}
    - apiVersion: v1
      kind: Service
      nameTemplate: "{{.parent.metadata.name}}"
      template: |
        spec:
          selector:
            app: {{.parent.metadata.name}}
          ports:
          - port: {{.parent.spec.port}}
            targetPort: {{.parent.spec.port}}
          type: ClusterIP
  statusMappings:
    - childResource:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      conditions:
        - type: Available
          mapping:
            type: Ready
    - childResource:
        kind: Service
        name: "{{.parent.metadata.name}}"
      fieldMappings:
        - child: "spec.clusterIP"
          parent: "status.serviceIP"
  dependencies:
    - source:
        kind: Service
        name: "{{.parent.metadata.name}}"
      target:
        kind: Deployment
        name: "{{.parent.metadata.name}}"
      condition: Available
```

#### 고급 RGD 기능

1. **조건부 자식 리소스 생성**:
```yaml
childResources:
  - apiVersion: networking.k8s.io/v1
    kind: Ingress
    nameTemplate: "{{.parent.metadata.name}}"
    condition: "{{.parent.spec.ingress.enabled}}"
    template: |
      spec:
        rules:
        {{- range .parent.spec.ingress.hosts }}
        - host: {{.host}}
          http:
            paths:
            {{- range .paths }}
            - path: {{.path}}
              pathType: {{.pathType}}
              backend:
                service:
                  name: {{$.parent.metadata.name}}
                  port:
                    number: {{$.parent.spec.service.port}}
            {{- end }}
        {{- end }}
```

2. **자식 리소스 간 참조**:
```yaml
childResources:
  - apiVersion: v1
    kind: ConfigMap
    nameTemplate: "{{.parent.metadata.name}}-config"
    template: |
      data:
        app.properties: |
          server.port={{.parent.spec.port}}
          
  - apiVersion: apps/v1
    kind: Deployment
    nameTemplate: "{{.parent.metadata.name}}"
    template: |
      spec:
        template:
          spec:
            containers:
            - name: {{.parent.metadata.name}}
              volumeMounts:
              - name: config
                mountPath: /app/config
            volumes:
            - name: config
              configMap:
                name: {{.children.configmap.metadata.name}}
```

3. **상태 집계 및 전파**:
```yaml
statusMappings:
  - childResource:
      kind: Deployment
      name: "{{.parent.metadata.name}}"
    conditions:
      - type: Available
        mapping:
          type: Ready
    fieldMappings:
      - child: "status.readyReplicas"
        parent: "status.readyCount"
      - child: "status.replicas"
        parent: "status.totalCount"
```
kind: CustomResourceDefinition
metadata:
  name: applications.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: Application
    listKind: ApplicationList
    plural: applications
    singular: application
    shortNames:
      - app
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
              properties:
                # 애플리케이션 속성 정의
                replicas:
                  type: integer
                  minimum: 0
                image:
                  type: string
                config:
                  type: object
                  x-kubernetes-preserve-unknown-fields: true
```

### 3. 오퍼레이터 개발

```go
package main

import (
    "context"
    "fmt"
    
    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/api/errors"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/client-go/kubernetes"
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/log"
    
    krov1 "example.com/kro/api/v1"
)

// ApplicationReconciler reconciles an Application object
type ApplicationReconciler struct {
    client.Client
    Scheme *runtime.Scheme
}

func (r *ApplicationReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)
    
    // 애플리케이션 CR 가져오기
    var app krov1.Application
    if err := r.Get(ctx, req.NamespacedName, &app); err != nil {
        if errors.IsNotFound(err) {
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }
    
    // 디플로이먼트 생성 또는 업데이트
    deployment := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      app.Name,
            Namespace: app.Namespace,
        },
        Spec: appsv1.DeploymentSpec{
            Replicas: &app.Spec.Replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: map[string]string{
                    "app": app.Name,
                },
            },
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{
                    Labels: map[string]string{
                        "app": app.Name,
                    },
                },
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{
                        {
                            Name:  "app",
                            Image: app.Spec.Image,
                        },
                    },
                },
            },
        },
    }
    
    // 디플로이먼트 적용
    if err := r.Create(ctx, deployment); err != nil {
        if !errors.IsAlreadyExists(err) {
            return ctrl.Result{}, err
        }
        
        // 이미 존재하면 업데이트
        if err := r.Update(ctx, deployment); err != nil {
            return ctrl.Result{}, err
        }
    }
    
    log.Info("Reconciled Application", "name", app.Name)
    return ctrl.Result{}, nil
}
```

### 4. 커스텀 리소스 생성

```yaml
apiVersion: kro.example.com/v1
kind: Application
metadata:
  name: my-application
spec:
  replicas: 3
  image: nginx:latest
  config:
    port: 80
    path: /api
```

## 실제 예제: Nginx Helm 차트를 KRO로 마이그레이션

### 기존 Helm 차트 (values.yaml)

```yaml
# Nginx Helm 차트 values.yaml
replicaCount: 2

image:
  repository: nginx
  tag: 1.21.0
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  hosts:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
```

### KRO 커스텀 리소스 정의

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: nginxapps.kro.example.com
spec:
  group: kro.example.com
  names:
    kind: NginxApp
    listKind: NginxAppList
    plural: nginxapps
    singular: nginxapp
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
              properties:
                replicas:
                  type: integer
                  default: 1
                image:
                  type: object
                  properties:
                    repository:
                      type: string
                    tag:
                      type: string
                    pullPolicy:
                      type: string
                      enum: [Always, IfNotPresent, Never]
                service:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [ClusterIP, NodePort, LoadBalancer]
                    port:
                      type: integer
                ingress:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                    hosts:
                      type: array
                      items:
                        type: object
                        properties:
                          host:
                            type: string
                          paths:
                            type: array
                            items:
                              type: object
                              properties:
                                path:
                                  type: string
                                pathType:
                                  type: string
                resources:
                  type: object
                  properties:
                    limits:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
                    requests:
                      type: object
                      x-kubernetes-preserve-unknown-fields: true
```

### KRO 커스텀 리소스 인스턴스

```yaml
apiVersion: kro.example.com/v1
kind: NginxApp
metadata:
  name: my-nginx
spec:
  replicas: 2
  image:
    repository: nginx
    tag: 1.21.0
    pullPolicy: IfNotPresent
  service:
    type: ClusterIP
    port: 80
  ingress:
    enabled: true
    hosts:
      - host: example.com
        paths:
          - path: /
            pathType: Prefix
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
```

### KRO 컨트롤러 구현 (핵심 로직)

```go
func (r *NginxAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)
    
    // NginxApp CR 가져오기
    var nginxApp krov1.NginxApp
    if err := r.Get(ctx, req.NamespacedName, &nginxApp); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    
    // 1. Deployment 조정
    deployment := &appsv1.Deployment{
        ObjectMeta: metav1.ObjectMeta{
            Name:      nginxApp.Name,
            Namespace: nginxApp.Namespace,
        },
    }
    
    _, err := ctrl.CreateOrUpdate(ctx, r.Client, deployment, func() error {
        // 소유자 참조 설정
        if err := ctrl.SetControllerReference(&nginxApp, deployment, r.Scheme); err != nil {
            return err
        }
        
        // Deployment 스펙 업데이트
        replicas := int32(nginxApp.Spec.Replicas)
        deployment.Spec.Replicas = &replicas
        
        // 레이블 설정
        labels := map[string]string{"app": nginxApp.Name}
        deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
        
        // 파드 템플릿 설정
        deployment.Spec.Template.ObjectMeta.Labels = labels
        deployment.Spec.Template.Spec.Containers = []corev1.Container{
            {
                Name:            "nginx",
                Image:           fmt.Sprintf("%s:%s", nginxApp.Spec.Image.Repository, nginxApp.Spec.Image.Tag),
                ImagePullPolicy: corev1.PullPolicy(nginxApp.Spec.Image.PullPolicy),
                Ports: []corev1.ContainerPort{
                    {
                        ContainerPort: nginxApp.Spec.Service.Port,
                    },
                },
                Resources: corev1.ResourceRequirements{
                    Limits:   convertResourceList(nginxApp.Spec.Resources.Limits),
                    Requests: convertResourceList(nginxApp.Spec.Resources.Requests),
                },
            },
        }
        
        return nil
    })
    
    if err != nil {
        return ctrl.Result{}, err
    }
    
    // 2. Service 조정
    // 3. Ingress 조정 (생략)
    
    return ctrl.Result{}, nil
}
```

## 결론

Helm에서 KRO로의 마이그레이션은 Kubernetes 네이티브 접근 방식으로 전환하는 중요한 단계입니다. 이를 통해 더 선언적이고, 확장 가능하며, GitOps 친화적인 애플리케이션 관리가 가능해집니다. 특히 복잡한 애플리케이션의 경우, KRO는 더 세분화된 제어와 개선된 버전 관리를 제공합니다.

마이그레이션 과정은 초기에 추가 작업이 필요하지만, 장기적으로는 유지 관리 및 운영 측면에서 상당한 이점을 제공합니다. 점진적인 마이그레이션 접근 방식을 통해 위험을 최소화하면서 KRO의 이점을 활용할 수 있습니다.
