# Istio 모범 사례

프로덕션 환경에서 Istio를 성공적으로 운영하기 위한 모범 사례와 권장 사항을 다룹니다.

## 목차

1. [성능 최적화](#성능-최적화)
2. [보안 강화](#보안-강화)
3. [운영 가이드](#운영-가이드)
4. [모니터링 및 관찰성](#모니터링-및-관찰성)
5. [프로덕션 체크리스트](#프로덕션-체크리스트)

## 성능 최적화

### 1. Control Plane 리소스 최적화

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
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 80
```

**권장 사항**:
- Istiod는 최소 2개 이상의 replicas
- CPU: 클러스터 크기에 따라 조정
- 메모리: 서비스 수 × 10KB 정도 예상

### 2. Data Plane 리소스 최적화

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    # Sidecar 리소스 최적화
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

**권장 사항**:
- 일반 워크로드: CPU 100m, Memory 128Mi
- 고트래픽 워크로드: CPU 500m, Memory 512Mi
- Sidecar 동시성: `concurrency: 2` (기본값)

### 3. Connection Pool 최적화

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: optimized-pool
spec:
  host: myapp
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
        idleTimeout: 300s
```

**권장 사항**:
- `maxConnections`: 워크로드 동시 연결 수 고려
- `maxRequestsPerConnection`: HTTP/1.1은 1-2, HTTP/2는 높게
- `idleTimeout`: 장시간 연결 필요 시 증가

### 4. Locality Load Balancing

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: locality-lb
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # 같은 AZ 우선
            "us-east-1/us-east-1b/*": 20
```

**이점**:
- 크로스 AZ 비용 절감 (~85%)
- 네트워크 지연시간 감소
- 가용 영역 장애 자동 처리

### 5. Sidecar Scope 제한

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "default/*"
    - "istio-system/*"
```

**이점**:
- Envoy 구성 크기 감소
- 메모리 사용량 감소
- 구성 푸시 속도 향상

## 보안 강화

### 1. Strict mTLS 적용

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

**체크리스트**:
- ✅ 모든 서비스에 STRICT mTLS 적용
- ✅ PERMISSIVE는 마이그레이션 기간에만 사용
- ✅ 외부 서비스는 DISABLE (ServiceEntry에서 처리)

### 2. Authorization Policy

```yaml
# Deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # 모든 요청 거부
---
# Allow specific
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

**모범 사례**:
- Deny-by-default 정책 사용
- 최소 권한 원칙 적용
- Service Account 기반 인증
- Namespace 격리

### 3. Egress 트래픽 제어

```yaml
# 외부 트래픽 차단
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # 명시적 ServiceEntry만 허용
---
# 허용된 외부 서비스
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 4. JWT 인증

```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[iss]
      values: ["https://auth.example.com"]
```

## 운영 가이드

### 1. 배포 전략

#### 점진적 Istio 도입

```mermaid
flowchart LR
    Start[시작]
    Phase1[Phase 1<br/>Observability]
    Phase2[Phase 2<br/>mTLS PERMISSIVE]
    Phase3[Phase 3<br/>mTLS STRICT]
    Phase4[Phase 4<br/>Advanced Features]
    End[완전 도입]

    Start --> Phase1
    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> End

    %% 스타일 정의
    classDef phase fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class Start,Phase1,Phase2,Phase3,Phase4,End phase;
```

**Phase 1: Observability (1-2주)**
```bash
# Sidecar 주입만 활성화
kubectl label namespace default istio-injection=enabled

# 메트릭, 로그, 트레이스 확인
# 성능 영향 평가
```

**Phase 2: mTLS PERMISSIVE (1-2주)**
```yaml
# PERMISSIVE 모드 활성화
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: PERMISSIVE
```

**Phase 3: mTLS STRICT (1주)**
```yaml
# STRICT 모드로 전환
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**Phase 4: Advanced Features (지속적)**
- Traffic Management (Canary, Circuit Breaker)
- Authorization Policy
- Rate Limiting

### 2. 업그레이드 전략

#### Canary Upgrade

```bash
# 1. 새 버전 Control Plane 설치
istioctl install --set revision=1-28-0 -y

# 2. 테스트 네임스페이스 이동
kubectl label namespace test istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n test

# 3. 검증 후 프로덕션 이동
kubectl label namespace prod istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n prod

# 4. 이전 버전 제거
istioctl uninstall --revision=1-27-0 -y
```

### 3. High Availability

```yaml
# Control Plane HA
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        replicaCount: 3
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: istiod
            topologyKey: kubernetes.io/hostname
```

**권장 사항**:
- Istiod: 최소 3개 replica
- 각 AZ에 고르게 분산
- PodDisruptionBudget 설정

### 4. 백업 및 복구

```bash
# Istio 구성 백업
kubectl get istiooperator -A -o yaml > istio-operator-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# 복구
kubectl apply -f istio-operator-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

## 모니터링 및 관찰성

### 1. Golden Signals

```promql
# 1. Latency (P50, P95, P99)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (요청 수)
sum(rate(istio_requests_total[5m]))

# 3. Errors (에러율)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total[5m]))

# 4. Saturation (리소스 사용률)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

### 2. Control Plane 모니터링

```promql
# Pilot 구성 푸시 시간
pilot_proxy_convergence_time

# xDS 연결 수
pilot_xds_pushes

# 메모리 사용량
process_resident_memory_bytes{app="istiod"}
```

### 3. Data Plane 모니터링

```promql
# Envoy 연결 수
envoy_cluster_upstream_cx_active

# Circuit Breaker 열림
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. Alerting Rules

```yaml
groups:
- name: istio
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: |
      (sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
      /
      sum(rate(istio_requests_total[5m]))) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  # High latency
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
      ) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected (P95 > 1s)"

  # Pilot not ready
  - alert: PilotNotReady
    expr: up{job="pilot"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pilot is not ready"
```

## 프로덕션 체크리스트

### 설치 전

- [ ] Kubernetes 버전 호환성 확인 (1.28+)
- [ ] Istio 버전 선택 (안정 버전 권장)
- [ ] 리소스 요구사항 계산
- [ ] 네트워크 정책 확인
- [ ] 백업 및 복구 계획 수립

### 설치

- [ ] 프로덕션 프로파일 사용
- [ ] Control Plane HA 구성 (replica ≥ 3)
- [ ] 리소스 제한 설정
- [ ] PodDisruptionBudget 설정
- [ ] 모니터링 스택 준비

### 보안

- [ ] mTLS STRICT 모드 활성화
- [ ] Authorization Policy 적용
- [ ] Egress 트래픽 제어
- [ ] JWT 인증 설정 (필요 시)
- [ ] Network Policy 통합

### 트래픽 관리

- [ ] VirtualService 구성
- [ ] DestinationRule 구성
- [ ] Circuit Breaker 설정
- [ ] Retry/Timeout 설정
- [ ] Rate Limiting 구성

### 관찰성

- [ ] Prometheus 통합
- [ ] Grafana 대시보드 설정
- [ ] Jaeger/Zipkin 트레이싱
- [ ] Kiali 설치
- [ ] Alerting 룰 설정

### 운영

- [ ] 업그레이드 계획 수립
- [ ] 백업 자동화
- [ ] 문서화
- [ ] On-call 가이드 작성
- [ ] Runbook 준비

### 성능

- [ ] Sidecar 리소스 최적화
- [ ] Connection Pool 튜닝
- [ ] Locality Load Balancing 설정
- [ ] Sidecar Scope 제한
- [ ] 성능 테스트 수행

### 테스트

- [ ] 기능 테스트
- [ ] 성능 테스트
- [ ] 장애 복구 테스트
- [ ] 카오스 엔지니어링
- [ ] 업그레이드 시나리오 테스트

## 일반적인 안티패턴

### ❌ 피해야 할 것들

1. **모든 것을 한번에 도입**
   ```
   ❌ Day 1에 모든 Istio 기능 활성화
   ✅ 점진적으로 기능 추가 (Observability → Security → Traffic Management)
   ```

2. **리소스 제한 없음**
   ```yaml
   ❌ Sidecar에 리소스 제한 없음
   ✅ 적절한 requests/limits 설정
   ```

3. **PERMISSIVE 모드 장기 사용**
   ```
   ❌ PERMISSIVE를 계속 사용
   ✅ 빠르게 STRICT로 전환
   ```

4. **Wildcard match 남용**
   ```yaml
   ❌ hosts: ["*"]  # 모든 서비스
   ✅ hosts: ["myapp.default.svc.cluster.local"]  # 명시적
   ```

5. **모니터링 없이 배포**
   ```
   ❌ 메트릭 확인 없이 프로덕션 배포
   ✅ Golden Signals 모니터링 필수
   ```

## 비용 최적화

### 1. Ambient Mode 고려

```yaml
# 리소스 사용량 비교
# Sidecar Mode: 100 pods × 50MB = 5GB
# Ambient Mode: 10 nodes × 50MB = 500MB

# 85% 이상 절감 가능
```

### 2. Locality Load Balancing

```yaml
# 크로스 AZ 비용 절감
# AWS: GB당 $0.01-0.02
# 80% 같은 AZ 라우팅 시 상당한 절감
```

### 3. Sidecar Scope 제한

```yaml
# 불필요한 구성 제거
# 메모리 사용량 30-50% 감소 가능
```

## 참고 자료

### 공식 문서
- [Istio Best Practices](https://istio.io/latest/docs/ops/best-practices/)
- [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)

### 커뮤니티
- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [GitHub Issues](https://github.com/istio/istio/issues)

### 추가 자료
- [Istio in Production](https://www.tetrate.io/blog/istio-in-production/)
- [Service Mesh Patterns](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
