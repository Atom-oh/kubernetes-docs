# Argo Rollouts 통합

Argo Rollouts와 Istio를 통합하여 고급 배포 전략을 구현합니다.

## 개요

이 문서는 Argo Rollouts의 기본 개념과 Istio 통합 방법을 다룹니다.

**참고**: Canary 배포의 상세한 내용은 [트래픽 분할 가이드](../traffic-management/03-traffic-splitting.md)를 참조하세요.

## 주요 기능

- 메트릭 기반 자동 Canary 배포
- Analysis 및 자동 롤백
- Blue/Green 배포
- Progressive Delivery

## 기본 Rollout 리소스

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary
      steps:
      - setWeight: 10
      - pause: {duration: 2m}
      - setWeight: 50
      - pause: {duration: 2m}
```

## VirtualService 설정

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp-vsvc
spec:
  hosts:
  - myapp
  http:
  - name: primary
    route:
    - destination:
        host: myapp
        subset: stable
      weight: 100
    - destination:
        host: myapp
        subset: canary
      weight: 0
```

## DestinationRule 설정

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp-destrule
spec:
  host: myapp
  subsets:
  - name: stable
    labels: {}
  - name: canary
    labels: {}
```

## Analysis Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: result >= 0.95
    provider:
      prometheus:
        address: http://prometheus.istio-system:9090
        query: |
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}",
              response_code!~"5.*"
            }[2m]
          ))
          /
          sum(rate(
            istio_requests_total{
              destination_service_name="{{args.service-name}}"
            }[2m]
          ))
```

## 배포 명령어

```bash
# 새 버전 배포
kubectl argo rollouts set image myapp myapp=myapp:v2

# 상태 확인
kubectl argo rollouts get rollout myapp --watch

# 수동 승인
kubectl argo rollouts promote myapp

# 롤백
kubectl argo rollouts abort myapp
```

## 상세 가이드

Argo Rollouts와 Istio를 사용한 Canary 배포의 전체 설정과 고급 기능은 다음 문서를 참조하세요:

- **[트래픽 분할 - Canary 배포](../traffic-management/03-traffic-splitting.md#canary-배포)**
  - Argo Rollouts + Istio 아키텍처
  - 단계별 설치 가이드
  - VirtualService/DestinationRule 설정
  - AnalysisTemplate 정의
  - 메트릭 기반 자동 진행
  - 문제 해결

- **[트래픽 분할 - Blue/Green 배포](../traffic-management/03-traffic-splitting.md#bluegreen-배포)**
  - Blue/Green 전략
  - 사전/사후 분석
  - 수동 승인 및 롤백

## 참고 자료

- [Argo Rollouts 공식 문서](https://argo-rollouts.readthedocs.io/)
- [Istio 통합 가이드](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [트래픽 분할 가이드](../traffic-management/03-traffic-splitting.md)
