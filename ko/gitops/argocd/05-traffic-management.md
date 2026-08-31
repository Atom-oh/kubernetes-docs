# ArgoCD 트래픽 관리

> **지원 버전**: ArgoCD v2.9+, Argo Rollouts v1.6+
> **마지막 업데이트**: 2026년 7월 15일

## 목차

- [Argo Rollouts 개요](#argo-rollouts-개요)
- [설치](#설치)
- [블루/그린 배포](#블루그린-배포)
- [카나리 배포](#카나리-배포)
- [Analysis와 자동 롤백](#analysis와-자동-롤백)
- [인그레스 컨트롤러 통합](#인그레스-컨트롤러-통합)
- [EKS에서의 프로그레시브 딜리버리](#eks에서의-프로그레시브-딜리버리)
- [Experiment](#experiment)

## Argo Rollouts 개요

Argo Rollouts는 Kubernetes를 위한 프로그레시브 딜리버리(Progressive Delivery) 컨트롤러입니다. 블루/그린 배포, 카나리 배포, 실험, 자동 롤백 등 고급 배포 전략을 제공합니다.

![Argo Rollouts 컨트롤러가 블루/그린, 카나리, 실험 배포 전략을 실행하고 Ingress Controller, Service Mesh, Analysis Provider와 연동하며 분석 결과를 Metrics Server로 피드백하는 아키텍처를 보여주는 다이어그램입니다.](../../../assets/diagrams/rendered/ko-gitops-argocd-05-traffic-management-0.svg)

### 주요 특징

| 특징 | 설명 |
|------|------|
| **블루/그린 배포** | 완전한 환경 전환 |
| **카나리 배포** | 점진적 트래픽 이동 |
| **Analysis** | 메트릭 기반 자동 승격/롤백 |
| **트래픽 관리** | 인그레스 및 서비스 메시 통합 |
| **실험** | A/B 테스트 지원 |

## 설치

### Argo Rollouts 설치

```bash
# 네임스페이스 생성
kubectl create namespace argo-rollouts

# Rollouts 설치
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# 설치 확인
kubectl get pods -n argo-rollouts
```

### kubectl 플러그인 설치

```bash
# macOS
brew install argoproj/tap/kubectl-argo-rollouts

# Linux
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x ./kubectl-argo-rollouts-linux-amd64
sudo mv ./kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# 확인
kubectl argo rollouts version
```

### Rollouts Dashboard

```bash
# 대시보드 시작
kubectl argo rollouts dashboard

# 브라우저에서 접속: http://localhost:3100
```

## 블루/그린 배포

블루/그린 배포는 두 개의 동일한 환경(블루=현재, 그린=새로운)을 유지하고 트래픽을 즉시 전환합니다.

![블루/그린 전환 전에는 로드 밸런서가 Blue v1.0.0으로 트래픽을 보내고 Green v2.0.0은 대기 상태이며, 전환 후에는 로드 밸런서가 Green v2.0.0으로 전환되고 이전 버전 Blue v1.0.0은 삭제 대상이 되는 과정을 보여주는 다이어그램입니다.](../../../assets/diagrams/rendered/ko-gitops-argocd-05-traffic-management-1.svg)

### 블루/그린 Rollout 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app-bluegreen
  namespace: production
spec:
  replicas: 5
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi

  strategy:
    blueGreen:
      # Active 서비스 (프로덕션 트래픽)
      activeService: my-app-active

      # Preview 서비스 (새 버전 테스트용)
      previewService: my-app-preview

      # 자동 승격 활성화 (false면 수동 승격)
      autoPromotionEnabled: true

      # 자동 승격 전 대기 시간
      autoPromotionSeconds: 60

      # 스케일다운 지연 (롤백 대비)
      scaleDownDelaySeconds: 300

      # 스케일다운 수정 제한
      scaleDownDelayRevisionLimit: 2

      # Preview 레플리카 수 (기본값: spec.replicas와 동일)
      previewReplicaCount: 2

      # Analysis 실행 (선택)
      prePromotionAnalysis:
        templates:
          - templateName: smoke-test
        args:
          - name: service-name
            value: my-app-preview
      postPromotionAnalysis:
        templates:
          - templateName: success-rate
        args:
          - name: service-name
            value: my-app-active

      # Anti-affinity (Preview와 Active를 다른 노드에 배치)
      antiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution:
          weight: 100
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-active
  namespace: production
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-preview
  namespace: production
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

### 블루/그린 관리 명령어

```bash
# 롤아웃 상태 확인
kubectl argo rollouts get rollout my-app-bluegreen -n production

# 실시간 모니터링
kubectl argo rollouts get rollout my-app-bluegreen -n production -w

# 수동 승격 (autoPromotionEnabled: false인 경우)
kubectl argo rollouts promote my-app-bluegreen -n production

# 롤백
kubectl argo rollouts undo my-app-bluegreen -n production

# 특정 리비전으로 롤백
kubectl argo rollouts undo my-app-bluegreen -n production --to-revision=2

# 중단
kubectl argo rollouts abort my-app-bluegreen -n production

# 재시작
kubectl argo rollouts retry rollout my-app-bluegreen -n production
```

## 카나리 배포

카나리 배포는 새 버전에 점진적으로 트래픽을 이동시켜 위험을 최소화합니다.

![로드 밸런서가 안정 버전 v1.0.0 파드 4개에 80%, 카나리 버전 v2.0.0 파드 1개에 20%의 트래픽을 분배하는 구조를 보여주는 다이어그램입니다.](../../../assets/diagrams/rendered/ko-gitops-argocd-05-traffic-management-2.svg)

### 카나리 Rollout 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app-canary
  namespace: production
spec:
  replicas: 10
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi

  strategy:
    canary:
      # Canary 서비스 (선택)
      canaryService: my-app-canary

      # Stable 서비스 (선택)
      stableService: my-app-stable

      # 최대 Surge (추가 Pod 수)
      maxSurge: "25%"

      # 최대 Unavailable
      maxUnavailable: 0

      # 카나리 단계
      steps:
        # 5% 트래픽으로 시작
        - setWeight: 5

        # 30초 대기
        - pause:
            duration: 30s

        # Analysis 실행
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: my-app-canary

        # 20% 트래픽
        - setWeight: 20

        # 수동 승격 대기
        - pause: {}

        # 50% 트래픽
        - setWeight: 50

        # 1분 대기
        - pause:
            duration: 1m

        # 80% 트래픽
        - setWeight: 80

        # 최종 Analysis
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: my-app-canary

        # 100% (자동 완료)

      # 트래픽 라우팅 (인그레스/서비스 메시)
      trafficRouting:
        # NGINX Ingress
        nginx:
          stableIngress: my-app-ingress
          annotationPrefix: nginx.ingress.kubernetes.io
          additionalIngressAnnotations:
            canary-by-header: X-Canary
            canary-by-header-value: "true"

      # 또는 AWS ALB
      # trafficRouting:
      #   alb:
      #     ingress: my-app-ingress
      #     servicePort: 80

      # 또는 Istio
      # trafficRouting:
      #   istio:
      #     virtualService:
      #       name: my-app-vsvc
      #       routes:
      #         - primary

      # Analysis 실패 시 롤백
      abortScaleDownDelaySeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-stable
  namespace: production
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-canary
  namespace: production
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

### 카나리 단계 상세

![트래픽 비중을 5%에서 20%, 50%, 80%까지 단계적으로 늘리며 각 단계 사이 분석 결과가 성공이면 다음 단계로, 실패면 롤백으로 이어지고 최종 분석에 성공하면 100% 완료되는 단계적 롤아웃 흐름을 보여주는 다이어그램입니다.](../../../assets/diagrams/rendered/ko-gitops-argocd-05-traffic-management-3.svg)

## Analysis와 자동 롤백

Analysis는 배포 중 메트릭을 수집하고 평가하여 자동으로 승격하거나 롤백합니다.

### AnalysisTemplate 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: production
spec:
  args:
    - name: service-name
    - name: threshold
      value: "0.95"  # 기본값 95%
  metrics:
    - name: success-rate
      # 성공 조건
      successCondition: result[0] >= {{ args.threshold }}
      # 실패 조건
      failureCondition: result[0] < 0.90
      # 불확정 결과 제한
      failureLimit: 3
      # 재시도 간격
      interval: 30s
      # 측정 횟수
      count: 10
      # Prometheus 쿼리
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            sum(rate(
              http_requests_total{
                service="{{ args.service-name }}",
                status=~"2.."
              }[5m]
            )) /
            sum(rate(
              http_requests_total{
                service="{{ args.service-name }}"
              }[5m]
            ))
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    - name: error-rate
      successCondition: result[0] < 0.05  # 에러율 5% 미만
      failureLimit: 3
      interval: 30s
      count: 5
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            sum(rate(
              http_requests_total{
                service="{{ args.service-name }}",
                status=~"5.."
              }[5m]
            )) /
            sum(rate(
              http_requests_total{
                service="{{ args.service-name }}"
              }[5m]
            ))
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-p99
  namespace: production
spec:
  args:
    - name: service-name
    - name: threshold-ms
      value: "500"
  metrics:
    - name: latency-p99
      successCondition: result[0] < {{ args.threshold-ms }}
      failureLimit: 3
      interval: 30s
      count: 5
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            histogram_quantile(0.99,
              sum(rate(
                http_request_duration_seconds_bucket{
                  service="{{ args.service-name }}"
                }[5m]
              )) by (le)
            ) * 1000
```

### Web Analysis (HTTP 체크)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: smoke-test
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    - name: smoke-test
      successCondition: result.status == "OK"
      failureLimit: 3
      interval: 10s
      count: 3
      provider:
        web:
          url: "http://{{ args.service-name }}.production/health"
          timeoutSeconds: 10
          headers:
            - key: X-Test
              value: "true"
          jsonPath: "{$.status}"
```

### Datadog Provider

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: datadog-success-rate
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      successCondition: default(result, 0) >= 0.95
      failureLimit: 3
      interval: 1m
      count: 5
      provider:
        datadog:
          apiVersion: v2
          query: |
            sum:trace.http.request.hits{
              service:{{ args.service-name }},
              http.status_code:2*
            }.as_count() /
            sum:trace.http.request.hits{
              service:{{ args.service-name }}
            }.as_count()
```

### CloudWatch Provider (AWS)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: cloudwatch-errors
  namespace: production
spec:
  args:
    - name: load-balancer-name
  metrics:
    - name: error-count
      successCondition: result < 10
      failureLimit: 3
      interval: 1m
      count: 5
      provider:
        cloudWatch:
          metricDataQueries:
            - id: errors
              expression: |
                SELECT SUM(HTTPCode_ELB_5XX_Count)
                FROM SCHEMA("AWS/ApplicationELB", LoadBalancer)
                WHERE LoadBalancer = '{{ args.load-balancer-name }}'
```

### 복합 Analysis (여러 메트릭 결합)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    # 성공률
    - name: success-rate
      successCondition: result[0] >= 0.95
      failureLimit: 3
      interval: 30s
      count: 10
      provider:
        prometheus:
          address: http://prometheus:80
          query: |
            sum(rate(http_requests_total{service="{{ args.service-name }}",status=~"2.."}[5m])) /
            sum(rate(http_requests_total{service="{{ args.service-name }}"}[5m]))

    # 에러율
    - name: error-rate
      successCondition: result[0] < 0.05
      failureLimit: 3
      interval: 30s
      count: 10
      provider:
        prometheus:
          address: http://prometheus:80
          query: |
            sum(rate(http_requests_total{service="{{ args.service-name }}",status=~"5.."}[5m])) /
            sum(rate(http_requests_total{service="{{ args.service-name }}"}[5m]))

    # 지연 시간
    - name: latency-p99
      successCondition: result[0] < 500
      failureLimit: 3
      interval: 30s
      count: 10
      provider:
        prometheus:
          address: http://prometheus:80
          query: |
            histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="{{ args.service-name }}"}[5m])) by (le)) * 1000
```

### AnalysisRun 확인

```bash
# AnalysisRun 목록
kubectl get analysisrun -n production

# AnalysisRun 상세
kubectl describe analysisrun my-app-canary-xxx -n production

# AnalysisRun 로그
kubectl argo rollouts get rollout my-app-canary -n production
```

## 인그레스 컨트롤러 통합

Argo Rollouts는 10개 이상의 트래픽 provider를 지원합니다. Kong처럼 네이티브 통합이 없는 provider는 **Gateway API 플러그인**을 경유합니다.

| Provider | 연동 방식 | 비고 |
|---|---|---|
| NGINX Ingress | 네이티브 (`trafficRouting.nginx`) | `canary-weight` 애노테이션 직접 조작 |
| AWS ALB | 네이티브 (`trafficRouting.alb`) | Ingress backend port가 `use-annotation`이어야 함 — [실측 검증 결과](#실측-검증-결과-eks) 참고 |
| Istio | 네이티브 (`trafficRouting.istio`) | VirtualService/DestinationRule 직접 조작 |
| SMI | 네이티브 (`trafficRouting.smi`) | SMI 프로젝트 자체가 유지보수 종료 상태 — 신규 도입 비권장 |
| Ambassador, Apache APISIX, Traefik, Google Cloud | 네이티브 | 이 문서에서는 다루지 않음, [공식 문서](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/) 참고 |
| **Kong**, 기타 Gateway API 호환 구현체(kgateway 등) | **Gateway API 플러그인** (`trafficRouting.plugins`) | 네이티브 `trafficRouting.kong` 필드는 존재하지 않음 |

### NGINX Ingress

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      canaryService: my-app-canary
      stableService: my-app-stable
      trafficRouting:
        nginx:
          stableIngress: my-app-ingress
          annotationPrefix: nginx.ingress.kubernetes.io
          additionalIngressAnnotations:
            canary-by-header: X-Canary
            canary-by-header-value: "true"
      steps:
        - setWeight: 10
        - pause: {duration: 1m}
        - setWeight: 30
        - pause: {duration: 2m}
        - setWeight: 60
        - pause: {duration: 2m}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: my-app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app-stable
                port:
                  number: 80
```

### AWS ALB

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      canaryService: my-app-canary
      stableService: my-app-stable
      trafficRouting:
        alb:
          ingress: my-app-ingress
          servicePort: 80
          # 가중 대상 그룹 활성화
          annotationPrefix: alb.ingress.kubernetes.io
      steps:
        - setWeight: 10
        - pause: {duration: 1m}
        - setWeight: 30
        - pause: {duration: 2m}
        - setWeight: 60
        - pause: {duration: 2m}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.weighted-routing: |
      {
        "type": "forward",
        "forwardConfig": {
          "targetGroups": [
            {
              "serviceName": "my-app-stable",
              "servicePort": 80,
              "weight": 100
            },
            {
              "serviceName": "my-app-canary",
              "servicePort": 80,
              "weight": 0
            }
          ]
        }
      }
spec:
  rules:
    - host: my-app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: weighted-routing
                port:
                  name: use-annotation
```

> ⚠️ **실측 확인**: Ingress backend의 `port`를 `name: use-annotation` 대신 실수로 `number: 80` 같은 실제 포트로 지정하면, `alb.ingress.kubernetes.io/actions.*` 애노테이션이 **에러나 경고 없이 조용히 무시**됩니다. AWS Load Balancer Controller가 가중치 forward 규칙 대신 단일 타겟그룹 규칙을 그대로 유지하므로, `kubectl get rollout`에서는 `SetWeight`가 정상적으로 올라가는 것처럼 보여도 실제 ALB 트래픽은 전혀 전환되지 않습니다. 반드시 `aws elbv2 describe-rules`로 실제 리스너 규칙의 `ForwardConfig.TargetGroups` weight를 대조해 확인하세요.

### Istio VirtualService

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      canaryService: my-app-canary
      stableService: my-app-stable
      trafficRouting:
        istio:
          virtualService:
            name: my-app-vsvc
            routes:
              - primary  # VirtualService의 route 이름
          destinationRule:
            name: my-app-destrule
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
        - setWeight: 10
        - pause: {duration: 1m}
        - analysis:
            templates:
              - templateName: success-rate
        - setWeight: 30
        - pause: {duration: 2m}
        - setWeight: 60
        - pause: {duration: 2m}
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app-vsvc
  namespace: production
spec:
  hosts:
    - my-app.example.com
  gateways:
    - my-gateway
  http:
    - name: primary
      route:
        - destination:
            host: my-app-stable
            port:
              number: 80
          weight: 100
        - destination:
            host: my-app-canary
            port:
              number: 80
          weight: 0
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: my-app-destrule
  namespace: production
spec:
  host: my-app
  subsets:
    - name: stable
      labels:
        app: my-app
    - name: canary
      labels:
        app: my-app
```

### Gateway API 플러그인 (범용)

Kong처럼 Argo Rollouts에 네이티브로 통합되지 않은 Gateway API 호환 구현체(Kong, Traefik, kgateway 등)는 argoproj-labs가 유지하는 [Gateway API 플러그인](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi)을 통해 지원됩니다. 이 플러그인은 표준 `HTTPRoute`의 `backendRefs[].weight`를 직접 조작하므로, Gateway API를 구현하는 컨트롤러라면 어디에나 동일하게 적용됩니다. TLSRoute와 헤더 기반 라우팅도 지원하며, 2026년 기준 최신 릴리스는 v0.16.0입니다.

플러그인 설치 — 컨트롤러가 기동 시 바이너리를 다운로드하도록 `argo-rollouts-config` ConfigMap에 등록합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-config
  namespace: argo-rollouts
data:
  trafficRouterPlugins: |-
    - name: "argoproj-labs/gatewayAPI"
      location: "https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/download/v0.16.0/gatewayapi-plugin-linux-amd64"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argo-rollouts-gateway-api-plugin
rules:
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get"]
  - apiGroups: ["gateway.networking.k8s.io"]
    resources: ["httproutes", "grpcroutes", "tcproutes", "tlsroutes"]
    verbs: ["get", "list", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argo-rollouts-gateway-api-plugin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: argo-rollouts-gateway-api-plugin
subjects:
  - kind: ServiceAccount
    name: argo-rollouts
    namespace: argo-rollouts
```

Rollout에서는 `trafficRouting.plugins`로 HTTPRoute를 지정합니다:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      stableService: my-app-stable
      canaryService: my-app-canary
      trafficRouting:
        plugins:
          argoproj-labs/gatewayAPI:
            httpRoute: my-app-route
            namespace: production
      steps:
        - setWeight: 20
        - pause: {duration: 1m}
        - setWeight: 50
        - pause: {duration: 1m}
        - setWeight: 100
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-app-route
  namespace: production
spec:
  parentRefs:
    - name: my-gateway
  rules:
    - backendRefs:
        - name: my-app-stable
          kind: Service
          port: 80
          weight: 100
        - name: my-app-canary
          kind: Service
          port: 80
          weight: 0
```

플러그인이 Rollout의 각 `setWeight` 단계마다 이 두 `backendRefs[].weight` 값을 직접 갱신합니다.

### Kong (Gateway API 플러그인 경유)

Kong Ingress Controller(KIC)는 Argo Rollouts에 네이티브로 통합되어 있지 않습니다 — 위 Gateway API 플러그인을 그대로 사용합니다. KIC를 Gateway API 모드로 설치한 뒤, GatewayClass를 **unmanaged gateway**로 지정해야 합니다:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: kong
  annotations:
    konghq.com/gatewayclass-unmanaged: "true"   # 필수 — 없으면 Gateway가 "Waiting for controller"에서 멈춤
spec:
  controllerName: konghq.com/kic-gateway-controller   # KIC의 IngressClass controller 문자열과 다르므로 주의
```

이후 [Gateway API 플러그인](#gateway-api-플러그인-범용) 설정을 그대로 적용하면 됩니다 (Rollout/HTTPRoute YAML 동일).

### 실측 검증 결과 (EKS)

EKS 1.36 클러스터(Argo Rollouts v1.9.0, AWS Load Balancer Controller v3.2.1, Istio 1.30, Kong Ingress Controller 3.5 + Gateway API 플러그인 v0.16.0)에서 격리된 테스트 네임스페이스로 4개 provider를 검증했습니다. 검증 후 모든 테스트 리소스(네임스페이스, Helm 릴리스, ALB, GatewayClass)는 정리했습니다.

| Provider | 검증 항목 | 결과 |
|---|---|---|
| NGINX | `canary-weight` 애노테이션 20→50→100% 전환 | ✅ 정상 — 실시간 curl 트래픽 비율이 애노테이션 값과 일치 |
| Istio | VirtualService weight 20→50→100% 전환, `abort` 시 즉시 0% 복귀 | ✅ 정상 — curl 비율이 weight와 일치, abort 후 트래픽이 즉시 이전 stable로 전환 |
| AWS ALB | 리스너 규칙 forward weight 전환, `aws elbv2 describe-rules`로 실제 AWS 상태 대조 | ✅ 정상 (단, 위 [`use-annotation` 주의](#aws-alb) 필요) |
| Kong (Gateway API 플러그인) | `HTTPRoute.backendRefs[].weight` 전환, Kong 데이터플레인 실제 트래픽 확인 | ✅ 정상 — 단, `gatewayclass-unmanaged` 애노테이션과 정확한 `controllerName` 설정이 까다로움 (위 참고) |

## EKS에서의 프로그레시브 딜리버리

### EKS 최적화 설정

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
  annotations:
    eks.amazonaws.com/fargate-profile: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app
      containers:
        - name: app
          image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-app:v2.0.0
          ports:
            - containerPort: 8080
          env:
            - name: AWS_REGION
              value: ap-northeast-2
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
      # Spot 인스턴스 고려
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: my-app

  strategy:
    canary:
      canaryService: my-app-canary
      stableService: my-app-stable
      trafficRouting:
        alb:
          ingress: my-app-ingress
          servicePort: 80
      steps:
        - setWeight: 5
        - pause: {duration: 30s}
        - analysis:
            templates:
              - templateName: cloudwatch-success-rate
            args:
              - name: alb-name
                value: "app/my-app-alb/xxx"
        - setWeight: 20
        - pause: {duration: 1m}
        - setWeight: 50
        - pause: {duration: 2m}
        - setWeight: 80
        - pause: {duration: 2m}
---
# CloudWatch Analysis Template
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: cloudwatch-success-rate
  namespace: production
spec:
  args:
    - name: alb-name
  metrics:
    - name: success-rate
      successCondition: result >= 0.99
      failureLimit: 3
      interval: 30s
      count: 10
      provider:
        cloudWatch:
          metricDataQueries:
            - id: requests
              metricStat:
                metric:
                  namespace: AWS/ApplicationELB
                  metricName: RequestCount
                  dimensions:
                    - name: LoadBalancer
                      value: "{{ args.alb-name }}"
                period: 60
                stat: Sum
            - id: errors
              metricStat:
                metric:
                  namespace: AWS/ApplicationELB
                  metricName: HTTPCode_Target_5XX_Count
                  dimensions:
                    - name: LoadBalancer
                      value: "{{ args.alb-name }}"
                period: 60
                stat: Sum
            - id: success_rate
              expression: "1 - (errors / requests)"
```

## Experiment

Experiment는 여러 버전을 동시에 실행하여 A/B 테스트를 수행합니다.

> 리소스 생성 체인, 이름 규칙, 트래픽 격리, AnalysisRun 판정의 상세 동작은 [Rollouts Experiment 심층 분석](10-rollouts-experiment.md)을 참고하세요.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Experiment
metadata:
  name: my-experiment
  namespace: production
spec:
  # 실험 지속 시간
  duration: 1h

  # 분석 진행 전 대기 시간
  progressDeadlineSeconds: 600

  # 템플릿
  templates:
    # Baseline (현재 버전)
    - name: baseline
      replicas: 2
      selector:
        matchLabels:
          app: my-app
          version: baseline
      template:
        metadata:
          labels:
            app: my-app
            version: baseline
        spec:
          containers:
            - name: app
              image: my-app:v1.0.0
              ports:
                - containerPort: 8080

    # Canary (새 버전)
    - name: canary
      replicas: 2
      selector:
        matchLabels:
          app: my-app
          version: canary
      template:
        metadata:
          labels:
            app: my-app
            version: canary
        spec:
          containers:
            - name: app
              image: my-app:v2.0.0
              ports:
                - containerPort: 8080

  # 분석
  analyses:
    - name: compare-versions
      templateName: compare-analysis
      args:
        - name: baseline-hash
          valueFrom:
            podTemplateHashValue: Baseline
        - name: canary-hash
          valueFrom:
            podTemplateHashValue: Canary
```

### 롤아웃에서 Experiment 사용

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app
          image: my-app:v2.0.0
  strategy:
    canary:
      steps:
        - setWeight: 20
        - pause: {duration: 30s}
        # 실험 실행
        - experiment:
            duration: 10m
            templates:
              - name: baseline
                specRef: stable
                replicas: 2
              - name: canary
                specRef: canary
                replicas: 2
            analyses:
              - name: compare
                templateName: compare-analysis
        - setWeight: 50
        - pause: {duration: 2m}
```

## 다음 단계

1. **[프로젝트와 RBAC](06-projects-rbac.md)**: Rollout에 대한 접근 제어를 구성하세요.

2. **[보안](07-security.md)**: 시크릿 관리와 SSO 통합을 설정하세요.

3. **[모범 사례](09-best-practices.md)**: 프로그레시브 딜리버리 모범 사례를 학습하세요.

## 참고 자료

- [Argo Rollouts 문서](https://argoproj.github.io/argo-rollouts/)
- [블루/그린 배포](https://argoproj.github.io/argo-rollouts/features/bluegreen/)
- [카나리 배포](https://argoproj.github.io/argo-rollouts/features/canary/)
- [Analysis](https://argoproj.github.io/argo-rollouts/features/analysis/)
- [트래픽 관리](https://argoproj.github.io/argo-rollouts/features/traffic-management/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [트래픽 관리 퀴즈](../../quizzes/gitops/argocd/05-traffic-management-quiz.md)를 풀어보세요.
