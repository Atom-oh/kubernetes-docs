# Istio 퀴즈

> **지원 버전**: Istio 1.28.0
> **EKS 버전**: 1.34 (Kubernetes 1.28+)
> **마지막 업데이트**: 2026년 2월 19일

이 퀴즈는 Istio 서비스 메시에 대한 이해도를 테스트합니다.

## 문제 1: 서비스 메시 기본 개념

<details>
<summary>서비스 메시란 무엇이며 주요 기능은?</summary>

**답변:**
서비스 메시는 서비스 간 통신을 처리하는 인프라 계층으로, 애플리케이션 코드를 변경하지 않고도 서비스 간 통신을 제어하고 관찰할 수 있게 해줍니다.

**주요 기능:**
1. **트래픽 관리**: 서비스 간 트래픽 흐름 제어
   - 라우팅, 로드 밸런싱, 카나리 배포
   - Timeout, Retry, Circuit Breaker
   - 트래픽 미러링 및 섀도우 테스트

2. **보안**: 서비스 간 통신 암호화 및 인증
   - 자동 mTLS (상호 TLS)
   - Authorization Policy (액세스 제어)
   - Request Authentication (JWT)

3. **관찰성**: 서비스 간 통신에 대한 가시성 제공
   - 메트릭 수집 (Prometheus)
   - 분산 추적 (Jaeger/Zipkin)
   - 로깅 및 시각화 (Kiali, Grafana)

**Istio의 특징:**
- 기존 분산 애플리케이션에 투명하게 계층화
- 사이드카 프록시 패턴 사용 (Envoy)
- Ambient Mode 지원 (사이드카 없는 아키텍처)
- 선언적 구성을 통한 정책 관리
</details>

## 문제 2: Istio 아키텍처

<details>
<summary>Istio 1.28.0의 주요 구성 요소와 역할은?</summary>

**답변:**
**컨트롤 플레인 (Control Plane):**
- **Istiod**: 단일 바이너리로 통합된 컨트롤 플레인
  - **서비스 검색**: 메시의 서비스 레지스트리 유지
  - **구성 관리**: Istio 구성 저장 및 배포
  - **인증서 관리**: mTLS를 위한 인증서 생성 및 순환

**데이터 플레인 (Data Plane):**
- **Envoy 프록시**: 사이드카로 배포되어 모든 네트워크 통신을 중재
  - 트래픽 라우팅 및 로드 밸런싱
  - mTLS 암호화 및 인증
  - 메트릭, 로그, 트레이스 수집

**Ambient Mode (선택사항):**
- **ztunnel**: 노드 레벨 프록시 (L4)
- **waypoint proxy**: 선택적 L7 프록시

**주요 특징:**
- 단일 바이너리 (Istiod)로 통합된 컨트롤 플레인
- 확장 가능하고 고가용성 아키텍처
- Kubernetes 네이티브 CRD 기반 구성
- Ambient Mode로 리소스 사용량 85% 이상 절감 가능
</details>

## 문제 3: 트래픽 관리 및 Argo Rollouts 통합

<details>
<summary>Istio와 Argo Rollouts를 사용하여 자동화된 카나리 배포를 구현하는 방법은?</summary>

**답변:**
Argo Rollouts는 Istio와 통합하여 메트릭 기반 자동 카나리 배포를 제공합니다.

**1. Rollout 리소스 정의:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
spec:
  replicas: 5
  strategy:
    canary:
      # Istio 트래픽 제어
      trafficRouting:
        istio:
          virtualService:
            name: reviews-vsvc
            routes:
            - primary
          destinationRule:
            name: reviews-destrule
            canarySubsetName: canary
            stableSubsetName: stable

      # 단계별 배포
      steps:
      - setWeight: 10    # 10% Canary
      - pause: {duration: 2m}
      - setWeight: 25    # 25% Canary
      - pause: {duration: 2m}
      - setWeight: 50    # 50% Canary
      - pause: {duration: 2m}

      # 자동 메트릭 분석
      analysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        startingStep: 1
```

**2. AnalysisTemplate - 자동 롤백:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    successCondition: result >= 0.95  # 95% 이상
    failureLimit: 2  # 2번 실패하면 자동 롤백
    provider:
      prometheus:
        query: |
          sum(rate(istio_requests_total{
            response_code!~"5.*"
          }[2m])) / sum(rate(istio_requests_total[2m]))
```

**주요 기능:**
- 메트릭 기반 자동 진행/롤백
- 점진적 트래픽 증가 (10% → 25% → 50% → 100%)
- Prometheus 메트릭 실시간 분석
- 실패 시 즉시 자동 롤백
</details>

## 문제 4: 보안 기능

<details>
<summary>Istio 1.28.0의 mTLS(mutual TLS) 기능과 Authorization Policy는?</summary>

**답변:**
**mTLS 장점:**
- 서비스 간 통신 자동 암호화
- 상호 인증으로 보안 강화
- 애플리케이션 코드 변경 없이 적용
- 자동 인증서 발급 및 갱신

**1. PeerAuthentication - mTLS 정책:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # 프로덕션은 STRICT 권장
```

**2. AuthorizationPolicy - 세밀한 접근 제어:**
```yaml
# Deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec: {}  # 모든 요청 거부

---
# Allow specific
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

**3. RequestAuthentication - JWT 검증:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
```

**모범 사례:**
- Deny-by-default 정책 사용
- 최소 권한 원칙 적용
- Service Account 기반 인증
- Namespace 격리
</details>

## 문제 5: Gateway 및 Ingress

<details>
<summary>Istio Gateway의 역할과 TLS 구성 방법은?</summary>

**답변:**
**Gateway 역할:**
- 클러스터 외부에서 내부 서비스로의 트래픽 진입점
- Ingress/Egress 트래픽 제어
- TLS 종료 및 인증서 관리
- 로드 밸런서와 연동

**구성 예시:**
```yaml
# Gateway 정의
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTPS (443)
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com

  # HTTP (80) - HTTPS로 리다이렉트
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
    tls:
      httpsRedirect: true

---
# VirtualService - Gateway와 연결
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo-vs
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - bookinfo-gateway
  http:
  - match:
    - uri:
        prefix: /productpage
    route:
    - destination:
        host: productpage
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

**TLS 인증서 생성:**
```bash
# Kubernetes Secret으로 TLS 인증서 생성
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## 문제 6: 관찰성 도구

<details>
<summary>Istio 1.28.0에서 제공하는 관찰성 도구들과 각각의 역할은?</summary>

**답변:**
**1. Prometheus - 메트릭 수집:**
```promql
# Golden Signals 모니터링
# 1. Latency (P95)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (요청 수)
sum(rate(istio_requests_total[5m]))

# 3. Errors (에러율)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/ sum(rate(istio_requests_total[5m]))

# 4. Saturation (CPU 사용률)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

**2. Jaeger - 분산 추적:**
```yaml
# Tracing 활성화
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% 샘플링
```

**3. Kiali - 서비스 메시 시각화:**
- 실시간 토폴로지 시각화
- 트래픽 흐름 분석
- 구성 검증
- 성능 메트릭 표시

**4. Grafana - 대시보드:**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- 커스텀 대시보드 생성

**접속 방법:**
```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```
</details>

## 문제 7: Ambient Mode

<details>
<summary>Istio 1.28.0의 Ambient Mode란 무엇이며 Sidecar Mode와의 차이점은?</summary>

**답변:**
**Ambient Mode 개념:**
- 사이드카 없는 서비스 메시 아키�ecture
- ztunnel (노드 레벨 L4 프록시) + waypoint (선택적 L7 프록시)
- 리소스 사용량 85% 이상 절감

**아키텍처 비교:**

| 특성 | Sidecar Mode | Ambient Mode |
|------|-------------|--------------|
| 배포 방식 | 각 파드에 Envoy 주입 | 노드당 ztunnel 1개 |
| 리소스 사용 | 높음 (파드당 50-100MB) | 낮음 (노드당 50MB) |
| 배포 복잡도 | 높음 (재배포 필요) | 낮음 (투명하게 적용) |
| L4 기능 | 지원 | ztunnel로 지원 |
| L7 기능 | 전체 지원 | waypoint 필요 |
| 성능 | 약간 느림 | 빠름 (L4만 사용 시) |

**Ambient Mode 활성화:**
```bash
# Ambient Mode 설치
istioctl install --set profile=ambient -y

# Namespace에 Ambient Mode 활성화
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**사용 시나리오:**
- 리소스 제약이 있는 환경
- 대규모 클러스터 (1000+ pods)
- L4 기능만 필요한 경우
- 점진적 Istio 도입
</details>

## 문제 8: 복원력 패턴

<details>
<summary>Istio의 Outlier Detection, Circuit Breaker, Rate Limiting의 차이점은?</summary>

**답변:**
**1. Outlier Detection - 비정상 인스턴스 제외:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5       # 5회 연속 실패
      interval: 30s              # 30초마다 평가
      baseEjectionTime: 30s      # 30초 제외
      maxEjectionPercent: 50     # 최대 50%만 제외
```

**2. Circuit Breaker - 과부하 방지:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
```

**3. Rate Limiting - 요청 속도 제한:**
```yaml
# 로컬 Rate Limiting
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
```

**차이점:**
- **Outlier Detection**: 사후 대응 (실패 후 제외)
- **Circuit Breaker**: 사전 방지 (연결 수 제한)
- **Rate Limiting**: 요청 속도 제어 (토큰 버킷)

**조합 사용:**
```yaml
trafficPolicy:
  connectionPool:     # Circuit Breaker
    tcp:
      maxConnections: 100
  outlierDetection:   # Outlier Detection
    consecutiveErrors: 5
```
</details>

## 문제 9: Locality Load Balancing (Zone Aware Routing)

<details>
<summary>Istio의 Locality Load Balancing 기능과 AWS EKS에서의 활용 방법은?</summary>

**답변:**
**Locality Load Balancing 개념:**
- 같은 가용 영역(AZ) 내 서비스 우선 라우팅
- 네트워크 지연시간 감소
- 크로스 AZ 데이터 전송 비용 절감 (~85%)

**구성 방법:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # 같은 AZ 우선, 다른 AZ는 장애조치용
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # 같은 AZ 80%
            "us-east-1/us-east-1b/*": 20  # 다른 AZ 20%

        # 장애 조치 정책
        failover:
        - from: us-east-1
          to: us-west-2
```

**AWS EKS에서의 활용:**
1. **비용 절감:**
   - 크로스 AZ 트래픽: $0.01/GB
   - 같은 AZ 트래픽: 무료
   - 80% 같은 AZ 라우팅 시 상당한 비용 절감

2. **성능 향상:**
   - AZ 내 지연시간: ~1ms
   - 크로스 AZ 지연시간: ~2-3ms

3. **자동 장애 조치:**
   - AZ 장애 시 자동으로 다른 AZ로 전환
   - Outlier Detection과 결합

**Pod Topology 설정:**
```yaml
# EKS 노드는 자동으로 topology 레이블 설정
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## 문제 10: Amazon EKS 통합 및 모범 사례

<details>
<summary>Istio 1.28.0을 Amazon EKS 1.34와 통합할 때 고려사항과 모범 사례는?</summary>

**답변:**
**1. 설치 및 구성:**
```bash
# Istioctl 설치
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# 프로덕션 프로필로 설치
istioctl install --set profile=production -y
```

**2. AWS Load Balancer 통합:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # Network Load Balancer
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

    # TLS 종료 (ACM 인증서)
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
```

**3. 리소스 최적화:**
```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1024Mi
```

**4. 보안 구성:**
```yaml
# VPC 보안 그룹 설정
# - Istiod: 15010, 15012, 8080
# - Envoy: 15001, 15006, 15021, 15090
# - Gateway: 80, 443

# IAM 역할 (IRSA)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::account:role/istio-gateway
```

**5. 모니터링 통합:**
```yaml
# CloudWatch Container Insights
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/cluster/istio
```

**6. 모범 사례:**
- ✅ 프로덕션 프로필 사용
- ✅ Control Plane HA (replica ≥ 3)
- ✅ mTLS STRICT 모드
- ✅ PodDisruptionBudget 설정
- ✅ Locality Load Balancing 활성화
- ✅ Prometheus + Grafana 모니터링
- ✅ 정기적인 버전 업그레이드 (Canary 방식)

**7. 비용 최적화:**
- Ambient Mode 고려 (85% 리소스 절감)
- Locality Load Balancing (크로스 AZ 비용 절감)
- Sidecar Scope 제한 (메모리 30-50% 감소)
</details>

## 보너스 문제: Progressive Delivery

<details>
<summary>Istio + Argo Rollouts로 완전 자동화된 Progressive Delivery를 구현하는 방법은?</summary>

**답변:**
Progressive Delivery는 메트릭 기반으로 자동으로 배포를 진행하거나 롤백하는 방식입니다.

**완전한 자동화 예제:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary

      steps:
      # 1단계: 10% Canary
      - setWeight: 10
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # 2단계: 25% Canary (자동 진행)
      - setWeight: 25
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # 3단계: 50% Canary (자동 진행)
      - setWeight: 50
      - pause: {duration: 2m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # 4단계: 100% Canary (자동 완료)
```

**자동 롤백 조건:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: result >= 0.95
    failureLimit: 2  # 2번 실패하면 즉시 롤백
    provider:
      prometheus:
        query: |
          # 성공률 < 95% 또는
          # 지연시간 > 500ms 또는
          # 에러율 > 5%
          # → 자동 롤백
```

**주요 이점:**
- 💚 완전 자동화 (사람 개입 불필요)
- 💚 즉시 롤백 (장애 감지 후 수초 내)
- 💚 안전한 배포 (메트릭 기반 검증)
- 💚 일관된 프로세스 (표준화)
</details>

---

**점수 계산:**
- 10-11개 정답: 우수 (Istio 전문가 수준)
- 8-9개 정답: 양호 (프로덕션 운영 가능)
- 6-7개 정답: 보통 (추가 학습 권장)
- 4-5개 정답: 미흡 (기본 개념 복습 필요)
- 0-3개 정답: 재학습 필요

**학습 자료:**
- [Istio 공식 문서](https://istio.io/latest/docs/)
- [Argo Rollouts 문서](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [본 가이드의 상세 문서](../../service-mesh/istio/)
