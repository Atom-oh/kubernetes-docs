# Istio 퀴즈

이 퀴즈는 Istio 서비스 메시에 대한 이해도를 테스트합니다.

## 문제 1: 서비스 메시 기본 개념

<details>
<summary>서비스 메시란 무엇이며 주요 기능은?</summary>

**답변:**
서비스 메시는 서비스 간 통신을 처리하는 인프라 계층으로, 애플리케이션 코드를 변경하지 않고도 서비스 간 통신을 제어하고 관찰할 수 있게 해줍니다.

**주요 기능:**
1. **트래픽 관리**: 서비스 간 트래픽 흐름 제어
2. **보안**: 서비스 간 통신 암호화 및 인증
3. **관찰성**: 서비스 간 통신에 대한 가시성 제공

**Istio의 특징:**
- 기존 분산 애플리케이션에 투명하게 계층화
- 사이드카 프록시 패턴 사용 (Envoy)
- 선언적 구성을 통한 정책 관리
</details>

## 문제 2: Istio 아키텍처

<details>
<summary>Istio의 주요 구성 요소와 역할은?</summary>

**답변:**
**데이터 플레인:**
- **Envoy 프록시**: 사이드카로 배포되어 모든 네트워크 통신을 중재

**컨트롤 플레인 (Istiod):**
- **Pilot**: 서비스 디스커버리 및 트래픽 관리 정책 배포
- **Citadel**: 인증서 관리 및 보안 정책 적용
- **Galley**: 구성 검증 및 배포 (1.5 이후 Istiod에 통합)

**주요 특징:**
- 단일 바이너리 (Istiod)로 통합된 컨트롤 플레인
- 확장 가능하고 고가용성 아키텍처
- Kubernetes 네이티브 CRD 기반 구성
</details>

## 문제 3: 트래픽 관리

<details>
<summary>Istio에서 카나리 배포를 구현하는 방법은?</summary>

**답변:**
```yaml
# DestinationRule - 서비스 버전 정의
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2

---
# VirtualService - 트래픽 분할
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-vs
spec:
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
```

**주요 기능:**
- 가중치 기반 트래픽 분할
- 헤더/쿠키 기반 라우팅
- 점진적 트래픽 증가
</details>

## 문제 4: 보안 기능

<details>
<summary>Istio의 mTLS(mutual TLS) 기능과 구성 방법은?</summary>

**답변:**
**mTLS 장점:**
- 서비스 간 통신 자동 암호화
- 상호 인증으로 보안 강화
- 애플리케이션 코드 변경 없이 적용
- 자동 인증서 발급 및 갱신

**구성 방법:**
```yaml
# PeerAuthentication - mTLS 정책
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT

---
# DestinationRule - 클라이언트 mTLS 설정
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: default
spec:
  host: "*.production.svc.cluster.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL

---
# AuthorizationPolicy - 접근 제어
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
  - to:
    - operation:
        methods: ["GET", "POST"]
```
</details>

## 문제 5: Gateway 및 Ingress

<details>
<summary>Istio Gateway의 역할과 구성 방법은?</summary>

**답변:**
**Gateway 역할:**
- 클러스터 외부에서 내부 서비스로의 트래픽 진입점
- 로드 밸런서에서 실행되는 Envoy 프록시 구성
- TLS 종료 및 인증서 관리

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
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com
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
```
</details>

## 문제 6: 관찰성 도구

<details>
<summary>Istio에서 제공하는 관찰성 도구들과 각각의 역할은?</summary>

**답변:**
**내장 관찰성 기능:**
- **메트릭**: Prometheus 형식의 자동 메트릭 생성
- **로깅**: 액세스 로그 및 애플리케이션 로그
- **추적**: 분산 추적 데이터 생성

**통합 도구들:**
1. **Kiali**: 서비스 메시 토폴로지 시각화
   ```yaml
   # Kiali 구성
   spec:
     external_services:
       prometheus:
         url: "http://prometheus:9090"
       grafana:
         url: "http://grafana:3000"
       jaeger:
         url: "http://jaeger-query:16686"
   ```

2. **Jaeger**: 분산 추적
   ```yaml
   # 추적 활성화
   apiVersion: install.istio.io/v1alpha1
   kind: IstioOperator
   spec:
     values:
       pilot:
         traceSampling: 100.0
   ```

3. **Prometheus**: 메트릭 수집
4. **Grafana**: 메트릭 시각화 대시보드

**커스텀 메트릭:**
```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: custom-metrics
spec:
  metrics:
  - providers:
    - name: prometheus
  - overrides:
    - match:
        metric: ALL_METRICS
      tagOverrides:
        request_id:
          value: "%{REQUEST_ID}"
```
</details>

## 문제 7: 최신 서비스 메시 트렌드

<details>
<summary>2023년 서비스 메시 영역의 주요 트렌드는?</summary>

**답변:**
1. **Ambient Mesh**:
   - 사이드카 없는 서비스 메시 아키텍처
   - 리소스 사용량 감소 및 성능 향상
   - Istio Ambient Mesh는 기존 사이드카 모델의 대안

2. **eBPF 기반 서비스 메시**:
   - 커널 수준의 네트워킹 제어로 오버헤드 감소
   - Cilium Service Mesh와 같은 eBPF 기반 솔루션
   - 더 나은 성능과 더 낮은 리소스 사용량

3. **멀티 클러스터 및 멀티 메시**:
   - 여러 클러스터에 걸친 서비스 메시 페더레이션
   - 클러스터 간 서비스 디스커버리 및 통신
   - Istio의 멀티 클러스터 기능 강화

4. **WebAssembly (WASM) 확장**:
   - 런타임에 커스텀 로직 추가
   - 다양한 언어로 확장 개발 가능
</details>

## 문제 8: 속도 제한

<details>
<summary>Istio에서 로컬 및 글로벌 속도 제한을 구현하는 방법은?</summary>

**답변:**
**로컬 속도 제한:**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/udpa.type.v1.TypedStruct
          type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          value:
            stat_prefix: local_rate_limiter
            token_bucket:
              max_tokens: 100
              tokens_per_fill: 100
              fill_interval: 60s
```

**글로벌 속도 제한:**
```yaml
# Redis 기반 글로벌 속도 제한
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: global-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: productpage-ratelimit
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: rate-limit-cluster
```
</details>

## 문제 9: Locality 라우팅

<details>
<summary>Istio의 Locality 라우팅 기능과 구성 방법은?</summary>

**답변:**
**Locality 라우팅 개념:**
- 지리적으로 가까운 서비스 인스턴스로 트래픽 라우팅
- 네트워크 지연 시간 감소 및 비용 절약
- 가용 영역(AZ) 및 리전 기반 라우팅

**구성 방법:**
```yaml
# DestinationRule - Locality 설정
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 3
    localityLbSetting:
      enabled: true
      distribute:
      - from: "region1/zone1/*"
        to:
          "region1/zone1/*": 80
          "region1/zone2/*": 20
      failover:
      - from: region1
        to: region2

---
# Istio 설치 시 Locality 활성화
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    pilot:
      env:
        EXTERNAL_ISTIOD: false
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster1
      network: network1
      localityLbSetting:
        enabled: true
```

**AWS EKS에서의 활용:**
- 가용 영역 간 트래픽 최적화
- 크로스 AZ 데이터 전송 비용 절약
- 장애 시 자동 페일오버
</details>

## 문제 10: Amazon EKS 통합

<details>
<summary>Istio를 Amazon EKS와 통합할 때 고려사항은?</summary>

**답변:**
1. **ALB와 Istio Gateway 통합**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: istio-ingressgateway
     annotations:
       service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
       service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
   spec:
     type: LoadBalancer
   ```

2. **EKS 노드 그룹 고려사항**:
   - 충분한 CPU/메모리 리소스 할당
   - 사이드카 프록시 오버헤드 고려
   - 네트워크 대역폭 요구사항

3. **AWS Load Balancer Controller**:
   ```yaml
   # Ingress Gateway 서비스
   annotations:
     service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
     service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
   ```

4. **VPC 및 보안 그룹**:
   - 적절한 포트 개방 (15010, 15011, 15012)
   - 사이드카 간 통신 허용
   - Istiod와 Envoy 간 통신 보장

5. **IAM 권한**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeInstances",
           "ec2:DescribeRegions",
           "elasticloadbalancing:*"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

6. **모니터링 통합**:
   - CloudWatch Container Insights
   - X-Ray 분산 추적
   - Prometheus 메트릭 수집
</details>

---

**점수 계산:**
- 8-10개 정답: 우수 (Istio 전문가 수준)
- 6-7개 정답: 양호 (추가 학습 권장)
- 4-5개 정답: 보통 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
