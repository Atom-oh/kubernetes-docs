# Kubernetes Resource Operator (KRO)를 활용한 Helm 차트 마이그레이션

> **지원 버전**: Kubernetes 1.26, 1.27, 1.28  
> **마지막 업데이트**: 2023년 7월 20일

## 개요

Kubernetes Resource Operator(KRO)는 Kubernetes 리소스를 선언적으로 관리하는 새로운 접근 방식입니다. 이 문서에서는 기존 Helm 차트를 KRO로 마이그레이션하는 방법을 설명하고, 이를 통해 얻을 수 있는 이점을 살펴봅니다.

## 실습 환경 설정

이 문서의 예제를 따라하기 위해서는 다음과 같은 도구와 환경이 필요합니다:

### 필수 도구
- kubectl v1.26 이상
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

### 3. ResourceGraphDefinition 생성

ResourceGraphDefinition(RGD)은 KRO의 핵심 개념으로, 커스텀 리소스와 Kubernetes 네이티브 리소스 간의 관계를 정의합니다.

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
