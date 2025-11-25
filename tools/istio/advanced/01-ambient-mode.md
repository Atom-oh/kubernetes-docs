# Ambient Mode

Ambient Mode는 Istio 1.28에서 도입된 혁신적인 데이터 플레인 아키텍처입니다. 기존 Sidecar 방식의 복잡성과 리소스 오버헤드를 줄이면서도 Service Mesh의 핵심 기능을 제공합니다.

## 목차

1. [개요](#개요)
2. [Sidecar Mode vs Ambient Mode](#sidecar-mode-vs-ambient-mode)
3. [아키텍처](#아키텍처)
4. [설치 및 구성](#설치-및-구성)
5. [마이그레이션](#마이그레이션)
6. [성능 비교](#성능-비교)
7. [사용 사례](#사용-사례)
8. [문제 해결](#문제-해결)

## 개요

Ambient Mode는 애플리케이션 파드에 Sidecar 프록시를 주입하지 않고도 Service Mesh 기능을 제공하는 새로운 방식입니다.

### 핵심 개념

```mermaid
flowchart TB
    subgraph SidecarMode["Sidecar Mode (기존)"]
        App1[Application<br/>Container]
        Sidecar1[Envoy<br/>Sidecar]
        App1 <--> Sidecar1
    end

    subgraph AmbientMode["Ambient Mode (신규)"]
        App2[Application<br/>Container Only]
        Node[Node-level<br/>ztunnel<br/>L4 Proxy]
        Waypoint[Waypoint<br/>Proxy<br/>L7 Features]
        
        App2 -->|투명하게| Node
        Node -->|L7 필요 시| Waypoint
    end

    %% 스타일 정의
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef sidecar fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef ambient fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class App1,App2 app;
    class Sidecar1 sidecar;
    class Node,Waypoint ambient;
```

### Ambient Mode의 장점

1. **낮은 리소스 사용**: 파드당 프록시가 아닌 노드당 프록시
2. **간단한 배포**: 파드 재시작 불필요
3. **투명한 적용**: 애플리케이션 변경 없음
4. **유연한 L7 기능**: 필요한 경우만 waypoint 사용

## Sidecar Mode vs Ambient Mode

### 아키텍처 비교

#### Sidecar Mode

```mermaid
flowchart TB
    subgraph Pod1["Pod"]
        App1[App<br/>Container]
        Envoy1[Envoy<br/>Sidecar]
    end

    subgraph Pod2["Pod"]
        App2[App<br/>Container]
        Envoy2[Envoy<br/>Sidecar]
    end

    subgraph Pod3["Pod"]
        App3[App<br/>Container]
        Envoy3[Envoy<br/>Sidecar]
    end

    App1 <--> Envoy1
    App2 <--> Envoy2
    App3 <--> Envoy3

    Envoy1 <-->|mTLS| Envoy2
    Envoy2 <-->|mTLS| Envoy3

    %% 스타일 정의
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef envoy fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class App1,App2,App3 app;
    class Envoy1,Envoy2,Envoy3 envoy;
```

**특징**:
- 각 파드에 Envoy 프록시 주입
- 모든 L4/L7 기능 지원
- 높은 리소스 사용량
- 파드 재시작 필요

#### Ambient Mode

```mermaid
flowchart TB
    subgraph Node["Kubernetes Node"]
        subgraph Pods["Application Pods"]
            App1[App<br/>Pod 1]
            App2[App<br/>Pod 2]
            App3[App<br/>Pod 3]
        end

        Ztunnel[ztunnel<br/>L4 Proxy<br/>mTLS, Telemetry]
    end

    subgraph WaypointLayer["Waypoint Proxy (Optional)"]
        Waypoint[Waypoint<br/>L7 Proxy<br/>Advanced Routing]
    end

    App1 -->|투명| Ztunnel
    App2 -->|투명| Ztunnel
    App3 -->|투명| Ztunnel

    Ztunnel -->|L4 only| Service[Service]
    Ztunnel -.->|L7 needed| Waypoint
    Waypoint --> Service

    %% 스타일 정의
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef waypoint fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class App1,App2,App3 app;
    class Ztunnel ztunnel;
    class Waypoint waypoint;
    class Service service;
```

**특징**:
- 노드당 하나의 ztunnel
- L4 기능 기본 제공
- L7 기능은 waypoint 필요
- 파드 재시작 불필요

### 상세 비교표

| 항목 | Sidecar Mode | Ambient Mode |
|------|-------------|--------------|
| **배포 방식** | 파드에 Sidecar 주입 | 노드 레벨 ztunnel + 선택적 waypoint |
| **리소스 사용** | 높음 (파드당 ~50-100MB) | 낮음 (노드당 ~50MB) |
| **파드 재시작** | 필요 | 불필요 |
| **초기 지연** | 있음 (Sidecar 초기화) | 최소 |
| **L4 기능** | ✅ 지원 | ✅ 지원 |
| **L7 기능** | ✅ 전체 지원 | ⚠️ Waypoint 필요 |
| **mTLS** | ✅ 자동 | ✅ 자동 |
| **Telemetry** | ✅ 상세 | ✅ 기본 (L4), 상세 (L7 with waypoint) |
| **Circuit Breaker** | ✅ 지원 | ⚠️ Waypoint 필요 |
| **Retry/Timeout** | ✅ 지원 | ⚠️ Waypoint 필요 |
| **Header 조작** | ✅ 지원 | ⚠️ Waypoint 필요 |
| **성능 오버헤드** | 중간 (~5-10%) | 낮음 (~1-3%) |
| **운영 복잡도** | 높음 | 낮음 |
| **프로덕션 준비** | ✅ 성숙 | ⚠️ 베타 (Istio 1.28+) |

### 리소스 사용량 비교

```yaml
# Sidecar Mode
# 100개 파드 × 50MB = 5GB 메모리
# 100개 파드 × 0.1 CPU = 10 vCPU

# Ambient Mode
# 10개 노드 × 50MB = 500MB 메모리 (ztunnel)
# + Waypoint (필요 시): 200MB 메모리
# 총: ~700MB 메모리
```

## 아키텍처

### ztunnel (Zero Trust Tunnel)

ztunnel은 Ambient Mode의 핵심 구성 요소로, 노드 레벨에서 실행되는 경량 L4 프록시입니다.

#### ztunnel 역할

```mermaid
flowchart TB
    App[Application Pod]
    Ztunnel[ztunnel<br/>DaemonSet]
    
    subgraph ZtunnelFeatures["ztunnel 기능"]
        MTLS[mTLS<br/>암호화]
        L4Telemetry[L4 Telemetry<br/>메트릭 수집]
        Identity[Identity<br/>Service Account]
        L4LB[L4 Load Balancing]
    end

    Target[Target Service]

    App -->|TCP 연결| Ztunnel
    Ztunnel -->|mTLS 적용| MTLS
    MTLS -->|메트릭 수집| L4Telemetry
    L4Telemetry -->|Identity 확인| Identity
    Identity -->|로드 밸런싱| L4LB
    L4LB -->|전송| Target

    %% 스타일 정의
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef target fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class App app;
    class Ztunnel ztunnel;
    class MTLS,L4Telemetry,Identity,L4LB feature;
    class Target target;
```

**ztunnel 특징**:
- Rust로 작성 (성능 최적화)
- DaemonSet으로 배포
- CNI 플러그인과 통합
- eBPF 기반 트래픽 리다이렉션

#### ztunnel 배포

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ztunnel
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: ztunnel
  template:
    metadata:
      labels:
        app: ztunnel
    spec:
      hostNetwork: true
      containers:
      - name: istio-proxy
        image: istio/ztunnel:1.28.0
        securityContext:
          privileged: true
          capabilities:
            add:
            - NET_ADMIN
            - SYS_ADMIN
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
          limits:
            cpu: 200m
            memory: 100Mi
```

### Waypoint Proxy

Waypoint는 L7 기능이 필요한 경우 사용하는 선택적 프록시입니다.

#### Waypoint 역할

```mermaid
flowchart TB
    Ztunnel[ztunnel]
    
    subgraph WaypointFeatures["Waypoint 기능"]
        L7Routing[L7 Routing<br/>Path, Header]
        Retry[Retry/Timeout]
        CircuitBreaker[Circuit Breaker]
        FaultInjection[Fault Injection]
        HeaderManip[Header 조작]
    end

    Target[Target Service]

    Ztunnel -->|L7 필요 시| L7Routing
    L7Routing --> Retry
    Retry --> CircuitBreaker
    CircuitBreaker --> FaultInjection
    FaultInjection --> HeaderManip
    HeaderManip --> Target

    %% 스타일 정의
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef target fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class Ztunnel ztunnel;
    class L7Routing,Retry,CircuitBreaker,FaultInjection,HeaderManip feature;
    class Target target;
```

**Waypoint 특징**:
- Service Account별 또는 Namespace별 배포
- Envoy 프록시 기반
- 모든 L7 Istio 기능 지원
- 필요한 서비스만 선택적 사용

#### Waypoint 배포

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: default
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

## 설치 및 구성

### 1. Istio 설치 (Ambient Mode)

```bash
# Istio 다운로드
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.28.0 sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Ambient profile로 설치
istioctl install --set profile=ambient -y

# 설치 확인
kubectl get pods -n istio-system
# 출력:
# NAME                                   READY   STATUS
# istio-cni-node-xxxxx                   1/1     Running
# istiod-xxxxx                           1/1     Running
# ztunnel-xxxxx                          1/1     Running
```

### 2. Namespace에 Ambient Mode 활성화

```bash
# Label로 Ambient Mode 활성화
kubectl label namespace default istio.io/dataplane-mode=ambient

# 확인
kubectl get namespace default -o yaml | grep istio.io/dataplane-mode
```

### 3. 애플리케이션 배포

```yaml
# 일반 Deployment (Sidecar 불필요)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reviews
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reviews
  template:
    metadata:
      labels:
        app: reviews
    spec:
      containers:
      - name: reviews
        image: istio/examples-bookinfo-reviews-v1:1.17.0
        ports:
        - containerPort: 9080
```

### 4. Waypoint 프록시 배포 (선택적)

```bash
# Service Account별 Waypoint 생성
istioctl x waypoint apply --service-account reviews

# 또는 Namespace별 Waypoint
istioctl x waypoint apply --namespace default

# Waypoint 확인
kubectl get gateway -n default
```

### 5. L7 기능 사용

```yaml
# VirtualService (Waypoint 사용)
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: default
spec:
  hosts:
  - reviews
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
---
# DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## 마이그레이션

### Sidecar Mode에서 Ambient Mode로

#### 단계별 마이그레이션

```mermaid
flowchart LR
    Start[Sidecar Mode<br/>운영 중]
    Install[Ambient<br/>컴포넌트 설치]
    Label[Namespace<br/>Label 추가]
    Remove[Sidecar<br/>제거]
    Waypoint[Waypoint<br/>배포]
    End[Ambient Mode<br/>완전 전환]

    Start --> Install
    Install --> Label
    Label --> Remove
    Remove --> Waypoint
    Waypoint --> End

    %% 스타일 정의
    classDef step fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class Start,Install,Label,Remove,Waypoint,End step;
```

#### 1단계: Ambient 컴포넌트 설치

```bash
# 기존 Istio가 설치되어 있다면
istioctl install --set profile=ambient --skip-confirmation

# ztunnel과 CNI 확인
kubectl get daemonset -n istio-system
```

#### 2단계: 테스트 Namespace에 적용

```bash
# 테스트 네임스페이스 생성
kubectl create namespace test-ambient

# Ambient Mode 활성화
kubectl label namespace test-ambient istio.io/dataplane-mode=ambient

# 테스트 애플리케이션 배포
kubectl apply -f samples/sleep/sleep.yaml -n test-ambient
```

#### 3단계: 검증

```bash
# mTLS 작동 확인
kubectl exec -n test-ambient deploy/sleep -- curl -s http://httpbin:8000/headers

# Telemetry 확인
kubectl logs -n istio-system -l app=ztunnel | grep test-ambient
```

#### 4단계: 프로덕션 Namespace 전환

```bash
# 기존 Namespace에 Label 추가
kubectl label namespace default istio.io/dataplane-mode=ambient

# 파드 재시작 (Sidecar 제거)
kubectl rollout restart deployment -n default

# Sidecar 제거 확인
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}' | grep -v istio-proxy
```

#### 5단계: Waypoint 배포 (L7 기능 필요 시)

```bash
# Service Account별 Waypoint
for sa in $(kubectl get sa -n default -o name); do
  istioctl x waypoint apply --service-account ${sa#serviceaccount/} -n default
done
```

### 롤백 전략

```bash
# Ambient에서 Sidecar로 되돌리기

# 1. Namespace Label 제거
kubectl label namespace default istio.io/dataplane-mode-

# 2. Sidecar Injection 활성화
kubectl label namespace default istio-injection=enabled

# 3. 파드 재시작
kubectl rollout restart deployment -n default

# 4. Waypoint 제거
kubectl delete gateway -n default --all
```

## 성능 비교

### 벤치마크 결과

| 메트릭 | Sidecar Mode | Ambient Mode (ztunnel only) | Ambient Mode (with waypoint) |
|--------|-------------|---------------------------|---------------------------|
| **Memory/Pod** | ~50-100MB | ~1-2MB | ~1-2MB (app) + shared waypoint |
| **CPU/Pod** | ~0.1 vCPU | ~0.01 vCPU | ~0.01 vCPU (app) + shared waypoint |
| **Latency (P50)** | +2-3ms | +0.5-1ms | +2-3ms |
| **Latency (P99)** | +5-10ms | +1-2ms | +5-10ms |
| **Throughput** | -5-10% | -1-3% | -5-10% |

### 리소스 절감 계산

```python
# 100개 파드 클러스터 예시

# Sidecar Mode
sidecar_memory = 100 * 50  # 5000MB = 5GB
sidecar_cpu = 100 * 0.1    # 10 vCPU

# Ambient Mode (10 nodes)
ambient_memory = 10 * 50 + 200  # 700MB (ztunnel + 1 waypoint)
ambient_cpu = 10 * 0.1 + 0.5    # 1.5 vCPU

# 절감량
memory_saved = sidecar_memory - ambient_memory  # 4300MB (~86%)
cpu_saved = sidecar_cpu - ambient_cpu          # 8.5 vCPU (~85%)
```

## 사용 사례

### 1. L4 기능만 필요한 경우

```yaml
# ztunnel만 사용 (Waypoint 불필요)
apiVersion: v1
kind: Namespace
metadata:
  name: backend
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: backend
spec:
  replicas: 3
  # ... (일반 Deployment)
```

**이점**:
- mTLS 자동 적용
- 기본 Telemetry
- 최소 리소스 사용

### 2. 선택적 L7 기능 사용

```yaml
# 특정 Service만 Waypoint 사용
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: frontend-waypoint
  namespace: frontend
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: frontend
  labels:
    istio.io/use-waypoint: frontend-waypoint
```

### 3. 점진적 마이그레이션

```bash
# 단계별 마이그레이션
# 1. Non-critical services
kubectl label namespace dev istio.io/dataplane-mode=ambient

# 2. Testing
kubectl label namespace staging istio.io/dataplane-mode=ambient

# 3. Production (one by one)
kubectl label namespace prod-backend istio.io/dataplane-mode=ambient
kubectl label namespace prod-frontend istio.io/dataplane-mode=ambient
```

## 문제 해결

### ztunnel이 작동하지 않음

```bash
# ztunnel 상태 확인
kubectl get daemonset -n istio-system ztunnel
kubectl logs -n istio-system -l app=ztunnel

# CNI 확인
kubectl get daemonset -n istio-system istio-cni-node
kubectl logs -n istio-system -l k8s-app=istio-cni-node
```

### Waypoint로 트래픽이 가지 않음

```bash
# Waypoint 상태 확인
kubectl get gateway -n <namespace>

# Service Account에 Waypoint 연결 확인
kubectl get sa <sa-name> -n <namespace> -o yaml | grep use-waypoint

# Envoy 구성 확인
istioctl proxy-config clusters <waypoint-pod> -n <namespace>
```

### 참고 자료

- [Istio Ambient Mode](https://istio.io/latest/docs/ops/ambient/)
- [Ambient Mode Architecture](https://istio.io/latest/blog/2022/introducing-ambient-mesh/)
- [ztunnel GitHub](https://github.com/istio/ztunnel)
