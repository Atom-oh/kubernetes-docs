# Istio 퀴즈

이 퀴즈는 Istio 서비스 메시에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Istio의 주요 목적은 무엇인가요?

A. 컨테이너 오케스트레이션  
B. 마이크로서비스 간의 통신, 보안, 관찰성 관리  
C. 클라우드 리소스 프로비저닝 자동화  
D. 컨테이너 이미지 빌드 및 배포  

<details>
<summary>정답 및 설명</summary>

**정답: B. 마이크로서비스 간의 통신, 보안, 관찰성 관리**

**설명:**
Istio는 서비스 메시(Service Mesh) 구현체로, 마이크로서비스 간의 통신, 보안, 관찰성을 관리하는 것이 주요 목적입니다. Istio는 애플리케이션 코드를 변경하지 않고도 마이크로서비스 네트워크를 관리할 수 있게 해주는 인프라 레이어를 제공합니다.

**Istio의 주요 기능:**

1. **트래픽 관리**:
   - 서비스 간 트래픽 라우팅 및 제어
   - 로드 밸런싱
   - 서킷 브레이킹
   - 타임아웃 및 재시도
   - A/B 테스팅, 카나리 배포

2. **보안**:
   - 서비스 간 통신 암호화(mTLS)
   - 인증 및 권한 부여
   - 서비스 ID 관리
   - 접근 제어 정책

3. **관찰성**:
   - 분산 추적(Distributed Tracing)
   - 메트릭 수집 및 모니터링
   - 로깅
   - 서비스 의존성 시각화

4. **정책 적용**:
   - 속도 제한(Rate Limiting)
   - 할당량 관리
   - 접근 제어 정책 적용

**Istio 아키텍처:**

Istio는 데이터 플레인과 컨트롤 플레인으로 구성됩니다:

1. **데이터 플레인**:
   - Envoy 프록시를 사이드카로 배포
   - 모든 서비스 간 통신을 가로채고 제어
   - 정책 적용, 메트릭 수집, 보안 기능 제공

2. **컨트롤 플레인**:
   - istiod: 구성 관리, 인증서 관리, 서비스 검색
   - 데이터 플레인 프록시 구성 및 관리
   - 정책 및 라우팅 규칙 배포

**Istio가 해결하는 문제:**

1. **마이크로서비스 복잡성**: 서비스 간 통신이 복잡해지는 문제 해결
2. **일관된 보안**: 모든 서비스 간 통신에 일관된 보안 정책 적용
3. **관찰성 부족**: 분산 시스템에서의 문제 진단 및 모니터링 어려움 해결
4. **네트워크 복원력**: 장애 처리, 로드 밸런싱, 서킷 브레이킹 등을 통한 복원력 향상

**다른 옵션들의 문제점:**
- A. 컨테이너 오케스트레이션: 이는 Kubernetes의 주요 목적이며, Istio는 이미 오케스트레이션된 서비스 간의 통신을 관리합니다.
- C. 클라우드 리소스 프로비저닝 자동화: 이는 Terraform, CloudFormation 등의 IaC 도구의 목적입니다.
- D. 컨테이너 이미지 빌드 및 배포: 이는 Docker, Buildah, CI/CD 파이프라인 등의 목적입니다.
</details>

### 2. Istio에서 'Sidecar' 패턴이 의미하는 것은 무엇인가요?

A. 두 개의 컨테이너가 항상 함께 배포되는 패턴  
B. 메인 애플리케이션 컨테이너와 함께 Envoy 프록시 컨테이너가 각 파드에 자동으로 주입되는 패턴  
C. 백업 컨테이너가 메인 컨테이너의 장애를 대비하는 패턴  
D. 두 개의 클러스터가 서로 백업하는 패턴  

<details>
<summary>정답 및 설명</summary>

**정답: B. 메인 애플리케이션 컨테이너와 함께 Envoy 프록시 컨테이너가 각 파드에 자동으로 주입되는 패턴**

**설명:**
Istio에서 'Sidecar' 패턴은 메인 애플리케이션 컨테이너와 함께 Envoy 프록시 컨테이너가 각 파드에 자동으로 주입되는 패턴을 의미합니다. 이 패턴을 통해 Istio는 애플리케이션 코드를 변경하지 않고도 서비스 메시의 모든 기능을 제공할 수 있습니다.

**Sidecar 패턴의 작동 방식:**

1. **자동 주입**: Istio는 네임스페이스나 파드에 특정 레이블이 있을 때 자동으로 Envoy 프록시를 사이드카로 주입합니다.
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: my-namespace
     labels:
       istio-injection: enabled
   ```

2. **트래픽 가로채기**: 사이드카 프록시는 iptables 규칙을 사용하여 파드로 들어오고 나가는 모든 네트워크 트래픽을 가로챕니다.

3. **투명한 프록시**: 애플리케이션은 프록시의 존재를 인식하지 못하며, 프록시는 투명하게 작동합니다.

4. **메시 기능 제공**: 사이드카 프록시는 트래픽 관리, 보안, 관찰성 등 Istio의 모든 기능을 제공합니다.

**Sidecar 주입 과정:**

1. **웹훅 작동**: Istio의 sidecar-injector 웹훅이 파드 생성 요청을 가로챕니다.
2. **파드 수정**: 웹훅은 파드 스펙을 수정하여 Envoy 프록시 컨테이너와 초기화 컨테이너를 추가합니다.
3. **볼륨 마운트**: 인증서, 구성 파일 등을 위한 볼륨이 추가됩니다.
4. **환경 변수**: 프록시 구성을 위한 환경 변수가 설정됩니다.
5. **파드 생성**: 수정된 파드 스펙으로 파드가 생성됩니다.

**Sidecar 프록시의 역할:**

1. **트래픽 관리**: 서비스 간 트래픽 라우팅, 로드 밸런싱, 재시도, 타임아웃 등을 처리합니다.
2. **보안**: mTLS를 통한 암호화, 인증, 권한 부여를 제공합니다.
3. **관찰성**: 메트릭 수집, 분산 추적, 로깅을 수행합니다.
4. **정책 적용**: 속도 제한, 할당량 등의 정책을 적용합니다.

**Sidecar 구성 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: default
  namespace: my-namespace
spec:
  egress:
  - hosts:
    - "./*"
    - "istio-system/*"
  ingress:
  - port:
      number: 8080
      protocol: HTTP
      name: http
    defaultEndpoint: 127.0.0.1:8080
  workloadSelector:
    labels:
      app: my-app
```

**Sidecar 패턴의 장점:**

1. **투명성**: 애플리케이션 코드를 변경하지 않고도 서비스 메시 기능을 제공합니다.
2. **일관성**: 모든 서비스에 동일한 네트워킹, 보안, 관찰성 기능을 제공합니다.
3. **분리**: 비즈니스 로직과 인프라 기능이 분리됩니다.
4. **업그레이드 용이성**: 애플리케이션과 독립적으로 사이드카를 업그레이드할 수 있습니다.

**Sidecar 패턴의 단점:**

1. **리소스 오버헤드**: 각 파드에 추가 컨테이너가 필요하므로 리소스 사용량이 증가합니다.
2. **지연 시간**: 프록시를 통한 추가 홉으로 인해 약간의 지연 시간이 발생할 수 있습니다.
3. **복잡성**: 시스템의 전반적인 복잡성이 증가합니다.

**다른 옵션들의 문제점:**
- A. 두 개의 컨테이너가 항상 함께 배포되는 패턴: 이는 일반적인 사이드카 패턴의 설명이지만, Istio의 맥락에서는 특별히 Envoy 프록시가 자동으로 주입되는 것을 의미합니다.
- C. 백업 컨테이너가 메인 컨테이너의 장애를 대비하는 패턴: 이는 사이드카 패턴이 아니라 고가용성을 위한 다른 패턴입니다.
- D. 두 개의 클러스터가 서로 백업하는 패턴: 이는 멀티 클러스터 배포 전략이며, 사이드카 패턴과는 관련이 없습니다.
</details>
### 3. Istio의 'Virtual Service'의 주요 목적은 무엇인가요?

A. 가상 머신 생성 및 관리  
B. 트래픽 라우팅 규칙 정의  
C. 서비스 메시 외부 서비스와의 통합  
D. 서비스 간 인증 관리  

<details>
<summary>정답 및 설명</summary>

**정답: B. 트래픽 라우팅 규칙 정의**

**설명:**
Istio의 'Virtual Service'의 주요 목적은 트래픽 라우팅 규칙을 정의하는 것입니다. Virtual Service는 Kubernetes 서비스로 들어오는 트래픽을 어떻게 라우팅할지 정의하는 Istio의 커스텀 리소스입니다. 이를 통해 A/B 테스팅, 카나리 배포, 블루-그린 배포 등 다양한 고급 트래픽 라우팅 시나리오를 구현할 수 있습니다.

**Virtual Service의 주요 기능:**

1. **트래픽 분할**: 여러 서비스 버전 간에 트래픽을 백분율로 분할할 수 있습니다.
2. **HTTP 경로 기반 라우팅**: URL 경로에 따라 다른 서비스로 트래픽을 라우팅할 수 있습니다.
3. **헤더 기반 라우팅**: HTTP 헤더 값에 따라 트래픽을 라우팅할 수 있습니다.
4. **재시도 및 타임아웃**: 서비스 호출에 대한 재시도 횟수와 타임아웃을 설정할 수 있습니다.
5. **장애 주입**: 테스트 목적으로 지연이나 오류를 주입할 수 있습니다.

**Virtual Service 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
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
```

이 예시에서:
- `end-user` 헤더가 `jason`인 요청은 `reviews` 서비스의 `v2` 버전으로 라우팅됩니다.
- 다른 모든 요청은 `reviews` 서비스의 `v1` 버전으로 라우팅됩니다.

**트래픽 분할 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 80
    - destination:
        host: reviews
        subset: v2
      weight: 20
```

이 예시에서:
- 트래픽의 80%는 `reviews` 서비스의 `v1` 버전으로 라우팅됩니다.
- 트래픽의 20%는 `reviews` 서비스의 `v2` 버전으로 라우팅됩니다.

**경로 기반 라우팅 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo
spec:
  hosts:
  - bookinfo.com
  http:
  - match:
    - uri:
        prefix: /reviews
    route:
    - destination:
        host: reviews
  - match:
    - uri:
        prefix: /ratings
    route:
    - destination:
        host: ratings
  - route:
    - destination:
        host: details
```

이 예시에서:
- `/reviews` 경로로 시작하는 요청은 `reviews` 서비스로 라우팅됩니다.
- `/ratings` 경로로 시작하는 요청은 `ratings` 서비스로 라우팅됩니다.
- 다른 모든 요청은 `details` 서비스로 라우팅됩니다.

**Virtual Service와 함께 사용되는 다른 리소스:**

1. **DestinationRule**: 서비스의 서브셋(버전)을 정의하고 로드 밸런싱 정책을 설정합니다.
   ```yaml
   apiVersion: networking.istio.io/v1beta1
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
     - name: v3
       labels:
         version: v3
   ```

2. **Gateway**: 메시 외부에서 들어오는 트래픽을 처리하는 로드 밸런서를 구성합니다.
   ```yaml
   apiVersion: networking.istio.io/v1beta1
   kind: Gateway
   metadata:
     name: bookinfo-gateway
   spec:
     selector:
       istio: ingressgateway
     servers:
     - port:
         number: 80
         name: http
         protocol: HTTP
       hosts:
       - bookinfo.com
   ```

**Virtual Service의 장점:**

1. **세분화된 트래픽 제어**: 다양한 조건에 따라 트래픽을 정밀하게 제어할 수 있습니다.
2. **점진적 배포**: 카나리 배포나 블루-그린 배포를 쉽게 구현할 수 있습니다.
3. **A/B 테스팅**: 다양한 서비스 버전을 테스트하고 비교할 수 있습니다.
4. **장애 복원력**: 재시도, 타임아웃, 서킷 브레이킹 등을 통해 장애 복원력을 향상시킬 수 있습니다.

**다른 옵션들의 문제점:**
- A. 가상 머신 생성 및 관리: Virtual Service는 가상 머신과 관련이 없으며, 트래픽 라우팅을 위한 것입니다.
- C. 서비스 메시 외부 서비스와의 통합: 이는 ServiceEntry의 주요 목적입니다.
- D. 서비스 간 인증 관리: 이는 주로 AuthorizationPolicy와 PeerAuthentication의 역할입니다.
</details>

### 4. Istio에서 'Locality Load Balancing'의 주요 목적은 무엇인가요?

A. 여러 클라우드 제공자 간에 트래픽을 분산  
B. 지리적으로 가까운 서비스 인스턴스로 트래픽을 우선 라우팅하여 지연 시간 최소화  
C. 클러스터 내의 모든 노드에 균등하게 트래픽 분산  
D. 서비스 메시 외부 서비스로의 트래픽 관리  

<details>
<summary>정답 및 설명</summary>

**정답: B. 지리적으로 가까운 서비스 인스턴스로 트래픽을 우선 라우팅하여 지연 시간 최소화**

**설명:**
Istio에서 'Locality Load Balancing'의 주요 목적은 지리적으로 가까운 서비스 인스턴스로 트래픽을 우선 라우팅하여 지연 시간을 최소화하는 것입니다. 이 기능은 여러 지역이나 영역에 걸쳐 배포된 서비스에서 네트워크 지연 시간을 줄이고 비용을 절감하는 데 도움이 됩니다.

**Locality Load Balancing의 작동 방식:**

1. **로컬리티 정의**: 각 서비스 인스턴스는 리전(region), 영역(zone), 서브영역(sub-zone)으로 구성된 로컬리티 정보를 가집니다.
2. **우선순위 결정**: 클라이언트와 같은 로컬리티에 있는 서비스 인스턴스가 우선적으로 선택됩니다.
3. **장애 대응**: 로컬 인스턴스에 장애가 발생하면 다른 로컬리티의 인스턴스로 트래픽이 전환됩니다.
4. **분배 비율 설정**: 로컬리티 간 트래픽 분배 비율을 구성할 수 있습니다.

**Locality Load Balancing 구성 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: my-service
spec:
  host: my-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/zone1/*
          to:
            "us-west/zone1/*": 80
            "us-west/zone2/*": 20
        - from: us-east/zone1/*
          to:
            "us-east/zone1/*": 80
            "us-east/zone2/*": 20
        failover:
        - from: us-west
          to: us-east
        - from: us-east
          to: us-west
```

이 예시에서:
- `us-west/zone1`의 트래픽은 80%는 같은 영역에, 20%는 `us-west/zone2`로 분배됩니다.
- `us-east/zone1`의 트래픽은 80%는 같은 영역에, 20%는 `us-east/zone2`로 분배됩니다.
- `us-west` 리전에 장애가 발생하면 트래픽은 `us-east`로 페일오버됩니다.
- `us-east` 리전에 장애가 발생하면 트래픽은 `us-west`로 페일오버됩니다.

**Locality Load Balancing의 이점:**

1. **지연 시간 감소**: 지리적으로 가까운 서비스 인스턴스로 트래픽을 라우팅하여 지연 시간을 최소화합니다.
2. **네트워크 비용 절감**: 리전 간 트래픽을 줄여 네트워크 비용을 절감합니다.
3. **장애 복원력 향상**: 한 로컬리티에 장애가 발생해도 다른 로컬리티로 자동 페일오버됩니다.
4. **리소스 활용도 최적화**: 로컬리티 간 트래픽 분배를 통해 리소스 활용도를 최적화할 수 있습니다.

**Locality Load Balancing 구성 옵션:**

1. **enabled**: Locality Load Balancing을 활성화 또는 비활성화합니다.
2. **distribute**: 특정 로컬리티에서 다른 로컬리티로의 트래픽 분배 비율을 정의합니다.
3. **failover**: 한 로컬리티에 장애가 발생했을 때 트래픽을 전환할 로컬리티를 정의합니다.
4. **failoverPriority**: 페일오버 우선순위를 설정합니다(리전 > 영역 > 서브영역).

**Locality Load Balancing과 관련된 개념:**

1. **Outlier Detection**: 비정상적인 서비스 인스턴스를 감지하고 로드 밸런싱에서 제외합니다.
   ```yaml
   outlierDetection:
     consecutive5xxErrors: 5
     interval: 30s
     baseEjectionTime: 30s
   ```

2. **Circuit Breaking**: 서비스 과부하를 방지하기 위해 연결 수, 요청 수 등을 제한합니다.
   ```yaml
   connectionPool:
     tcp:
       maxConnections: 100
     http:
       http1MaxPendingRequests: 1024
       maxRequestsPerConnection: 10
   ```

3. **Connection Pooling**: 서비스 인스턴스에 대한 연결을 재사용하여 성능을 향상시킵니다.

**Locality Load Balancing 사용 시나리오:**

1. **글로벌 서비스 배포**: 여러 지역에 배포된 서비스에서 사용자에게 가장 가까운 인스턴스로 트래픽을 라우팅합니다.
2. **재해 복구**: 한 리전에 장애가 발생했을 때 다른 리전으로 자동 페일오버합니다.
3. **비용 최적화**: 리전 간 트래픽을 최소화하여 네트워크 비용을 절감합니다.
4. **하이브리드 클라우드**: 온프레미스와 클라우드 환경 간의 트래픽을 최적화합니다.

**다른 옵션들의 문제점:**
- A. 여러 클라우드 제공자 간에 트래픽을 분산: Locality Load Balancing은 클라우드 제공자보다는 지리적 위치에 중점을 둡니다.
- C. 클러스터 내의 모든 노드에 균등하게 트래픽 분산: 이는 일반적인 로드 밸런싱의 목적이며, Locality Load Balancing은 지리적 근접성에 따라 우선순위를 부여합니다.
- D. 서비스 메시 외부 서비스로의 트래픽 관리: 이는 ServiceEntry의 주요 목적입니다.
</details>
### 5. Istio에서 'Global Rate Limit'의 주요 목적은 무엇인가요?

A. 클러스터의 전체 리소스 사용량 제한  
B. 서비스 메시 전체에 걸쳐 API 호출 빈도 제한  
C. 글로벌 네트워크 대역폭 제한  
D. 전체 사용자 세션 수 제한  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 메시 전체에 걸쳐 API 호출 빈도 제한**

**설명:**
Istio에서 'Global Rate Limit'의 주요 목적은 서비스 메시 전체에 걸쳐 API 호출 빈도를 제한하는 것입니다. 이는 서비스를 과부하로부터 보호하고, 공정한 리소스 사용을 보장하며, DDoS 공격을 방어하는 데 도움이 됩니다. 로컬 속도 제한과 달리, 글로벌 속도 제한은 중앙 집중식 속도 제한 서비스를 사용하여 모든 프록시 인스턴스에 걸쳐 속도 제한을 조정합니다.

**Global Rate Limit의 작동 방식:**

1. **중앙 집중식 서비스**: Istio는 외부 속도 제한 서비스(예: Envoy의 Rate Limit Service)와 통합됩니다.
2. **속도 제한 구성**: EnvoyFilter를 사용하여 속도 제한 규칙을 정의합니다.
3. **토큰 버킷 알고리즘**: 일반적으로 토큰 버킷 알고리즘을 사용하여 요청 속도를 제한합니다.
4. **분산 카운터**: 중앙 서비스는 분산된 프록시 인스턴스에서 오는 요청을 집계합니다.

**Global Rate Limit 구성 예시:**

1. **속도 제한 서비스 배포**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8081
    name: grpc
  selector:
    app: ratelimit
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
    spec:
      containers:
      - name: ratelimit
        image: envoyproxy/ratelimit:1.4.0
        env:
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: "true"
        - name: RUNTIME_IGNOREDOTFILES
          value: "true"
        - name: USE_STATSD
          value: "false"
        - name: LOG_LEVEL
          value: debug
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis:6379
        volumeMounts:
        - name: config-volume
          mountPath: /data/config
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
```

2. **속도 제한 구성**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: productpage-ratelimit
    descriptors:
      - key: path
        value: "/productpage"
        rate_limit:
          unit: minute
          requests_per_unit: 100
      - key: user
        rate_limit:
          unit: minute
          requests_per_unit: 10
```

3. **EnvoyFilter 구성**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: productpage-ratelimit
          failure_mode_deny: false
          timeout: 10s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
              timeout: 10s
```

**Global Rate Limit vs Local Rate Limit:**

1. **Global Rate Limit**:
   - 중앙 집중식 서비스를 사용하여 모든 프록시 인스턴스에 걸쳐 속도 제한을 조정
   - 분산 환경에서 정확한 속도 제한 적용 가능
   - Redis와 같은 외부 저장소를 사용하여 카운터 유지
   - 구성 및 유지 관리가 더 복잡함

2. **Local Rate Limit**:
   - 각 프록시 인스턴스가 독립적으로 속도 제한 적용
   - 프록시 간 조정 없음
   - 메모리 내 카운터 사용
   - 구성이 더 간단함
   - 분산 환경에서는 정확한 속도 제한이 어려움

**Local Rate Limit 예시**:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-local-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      app: productpage
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
            stat_prefix: http_local_rate_limiter
            token_bucket:
              max_tokens: 100
              tokens_per_fill: 100
              fill_interval: 60s
            filter_enabled:
              runtime_key: local_rate_limit_enabled
              default_value:
                numerator: 100
                denominator: HUNDRED
```

**Global Rate Limit의 사용 사례:**

1. **API 보호**: 과도한 API 호출로부터 백엔드 서비스 보호
2. **공정한 사용**: 사용자 간 공정한 리소스 사용 보장
3. **DDoS 방어**: 분산 서비스 거부 공격 방어
4. **비용 제어**: API 호출 비용 제어
5. **서비스 계층**: 다양한 서비스 계층(무료, 프리미엄 등)에 따른 차별화된 속도 제한 적용

**속도 제한 기준:**

1. **IP 주소**: 클라이언트 IP 주소별 제한
2. **사용자 ID**: 인증된 사용자별 제한
3. **API 경로**: 특정 API 엔드포인트별 제한
4. **HTTP 메서드**: GET, POST 등 HTTP 메서드별 제한
5. **사용자 정의 헤더**: 특정 헤더 값에 따른 제한

**다른 옵션들의 문제점:**
- A. 클러스터의 전체 리소스 사용량 제한: 이는 Kubernetes의 ResourceQuota와 같은 기능의 역할입니다.
- C. 글로벌 네트워크 대역폭 제한: Istio의 Global Rate Limit은 네트워크 대역폭보다는 요청 수에 중점을 둡니다.
- D. 전체 사용자 세션 수 제한: 이는 인증 시스템이나 세션 관리 시스템의 역할입니다.
</details>

### 6. Istio에서 'DestinationRule'의 주요 목적은 무엇인가요?

A. 외부 서비스와의 통신 설정  
B. 서비스 버전(subset) 정의 및 로드 밸런싱 정책 구성  
C. 인그레스 트래픽 라우팅 규칙 정의  
D. 서비스 간 인증 정책 설정  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 버전(subset) 정의 및 로드 밸런싱 정책 구성**

**설명:**
Istio에서 'DestinationRule'의 주요 목적은 서비스 버전(subset)을 정의하고 로드 밸런싱 정책을 구성하는 것입니다. DestinationRule은 VirtualService가 트래픽을 어디로 라우팅할지 결정한 후, 해당 트래픽이 어떻게 처리될지를 정의합니다. 이는 서비스의 다양한 버전을 정의하고, 각 버전에 대한 로드 밸런싱, 연결 풀, 이상치 탐지 등의 정책을 설정하는 데 사용됩니다.

**DestinationRule의 주요 기능:**

1. **서비스 서브셋 정의**: 서비스의 다양한 버전(v1, v2 등)을 레이블을 기반으로 정의합니다.
2. **로드 밸런싱 정책 설정**: 라운드 로빈, 최소 연결, 랜덤 등의 로드 밸런싱 알고리즘을 지정합니다.
3. **연결 풀 구성**: 서비스에 대한 최대 연결 수, HTTP/2 최대 요청 수 등을 설정합니다.
4. **이상치 탐지 설정**: 비정상적인 서비스 인스턴스를 감지하고 로드 밸런싱에서 제외하는 규칙을 정의합니다.
5. **TLS 설정**: 서비스 간 통신을 위한 TLS 설정을 구성합니다.

**DestinationRule 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1024
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      loadBalancer:
        simple: LEAST_CONN
  - name: v3
    labels:
      version: v3
```

이 예시에서:
- `reviews` 서비스에 대한 기본 트래픽 정책은 라운드 로빈 로드 밸런싱을 사용합니다.
- 연결 풀은 TCP 연결을 100개로 제한하고, HTTP/1.1 연결당 최대 10개의 요청을 허용합니다.
- 이상치 탐지는 30초 간격으로 연속 5번의 5xx 오류가 발생하면 해당 인스턴스를 30초 동안 로드 밸런싱에서 제외합니다.
- 서비스는 v1, v2, v3 세 가지 서브셋으로 정의됩니다.
- v2 서브셋은 최소 연결 로드 밸런싱을 사용하도록 오버라이드됩니다.

**로드 밸런싱 알고리즘:**

1. **ROUND_ROBIN**: 요청을 순차적으로 각 서비스 인스턴스에 분배합니다.
2. **LEAST_CONN**: 현재 연결 수가 가장 적은 서비스 인스턴스로 요청을 라우팅합니다.
3. **RANDOM**: 무작위로 서비스 인스턴스를 선택합니다.
4. **PASSTHROUGH**: 원래 연결 정보를 유지하여 클라이언트가 선택한 인스턴스로 요청을 전달합니다.
5. **LOCALITY_WEIGHTED_LEAST_REQUEST**: 로컬리티와 현재 요청 수를 고려하여 인스턴스를 선택합니다.

**연결 풀 설정:**
```yaml
connectionPool:
  tcp:
    maxConnections: 100           # 최대 TCP 연결 수
    connectTimeout: 30ms          # 연결 타임아웃
  http:
    http1MaxPendingRequests: 1024 # HTTP/1.1 최대 대기 요청 수
    http2MaxRequests: 1024        # HTTP/2 최대 요청 수
    maxRequestsPerConnection: 10  # 연결당 최대 요청 수
    maxRetries: 3                 # 최대 재시도 횟수
```

**이상치 탐지 설정:**
```yaml
outlierDetection:
  consecutive5xxErrors: 5         # 연속 5xx 오류 횟수
  interval: 30s                   # 검사 간격
  baseEjectionTime: 30s           # 기본 제외 시간
  maxEjectionPercent: 100         # 최대 제외 비율
  minHealthPercent: 0             # 최소 정상 비율
```

**TLS 설정:**
```yaml
tls:
  mode: ISTIO_MUTUAL              # Istio mTLS 사용
  clientCertificate: /etc/certs/cert-chain.pem
  privateKey: /etc/certs/key.pem
  caCertificates: /etc/certs/root-cert.pem
  subjectAltNames:
  - spiffe://cluster.local/ns/default/sa/default
```

**VirtualService와 DestinationRule의 관계:**

- **VirtualService**: 트래픽을 어디로 라우팅할지 결정합니다.
- **DestinationRule**: 트래픽이 목적지에 도달한 후 어떻게 처리될지 정의합니다.

예를 들어:
```yaml
# VirtualService: 트래픽을 reviews 서비스의 v1 또는 v2 서브셋으로 라우팅
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 80
    - destination:
        host: reviews
        subset: v2
      weight: 20

# DestinationRule: reviews 서비스의 서브셋 정의 및 로드 밸런싱 정책 설정
apiVersion: networking.istio.io/v1beta1
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

**다른 옵션들의 문제점:**
- A. 외부 서비스와의 통신 설정: 이는 ServiceEntry의 주요 목적입니다.
- C. 인그레스 트래픽 라우팅 규칙 정의: 이는 Gateway와 VirtualService의 조합으로 처리됩니다.
- D. 서비스 간 인증 정책 설정: 이는 PeerAuthentication과 AuthorizationPolicy의 역할입니다.
</details>
### 7. Istio에서 'ServiceEntry'의 주요 목적은 무엇인가요?

A. 서비스 메시 내부에 새로운 서비스 생성  
B. 서비스 메시 외부 서비스를 서비스 메시 레지스트리에 추가하여 접근 관리  
C. 서비스 간 인증 정책 설정  
D. 서비스 버전 간 트래픽 분할  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 메시 외부 서비스를 서비스 메시 레지스트리에 추가하여 접근 관리**

**설명:**
Istio에서 'ServiceEntry'의 주요 목적은 서비스 메시 외부 서비스를 서비스 메시 레지스트리에 추가하여 접근을 관리하는 것입니다. ServiceEntry를 사용하면 Istio 서비스 메시 외부에 있는 서비스(예: 외부 API, 레거시 시스템, 다른 클러스터의 서비스 등)를 Istio의 서비스 레지스트리에 추가하여 마치 메시 내부 서비스처럼 관리할 수 있습니다.

**ServiceEntry의 주요 기능:**

1. **외부 서비스 등록**: 메시 외부 서비스를 Istio 서비스 레지스트리에 추가합니다.
2. **트래픽 관리**: 외부 서비스에 대한 트래픽을 VirtualService와 DestinationRule을 사용하여 관리할 수 있습니다.
3. **보안 정책 적용**: 외부 서비스에 대한 인증, 권한 부여, mTLS 등의 보안 정책을 적용할 수 있습니다.
4. **관찰성 확장**: 외부 서비스와의 통신에 대한 메트릭, 로그, 추적을 수집할 수 있습니다.

**ServiceEntry 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

이 예시에서:
- `api.example.com`이라는 외부 서비스를 Istio 서비스 레지스트리에 추가합니다.
- 포트 443을 통해 HTTPS 프로토콜로 접근합니다.
- `location: MESH_EXTERNAL`은 서비스가 메시 외부에 있음을 나타냅니다.
- `resolution: DNS`는 서비스 이름을 DNS를 통해 해석함을 나타냅니다.

**ServiceEntry 위치 유형:**

1. **MESH_EXTERNAL**: 서비스가 메시 외부에 있음을 나타냅니다. 이 경우 사이드카 프록시는 외부 서비스로 직접 요청을 전달합니다.
2. **MESH_INTERNAL**: 서비스가 메시 내부에 있지만 서비스 레지스트리에 등록되지 않았음을 나타냅니다. 이는 주로 멀티 클러스터 시나리오에서 사용됩니다.

**ServiceEntry 해석 유형:**

1. **DNS**: 서비스 이름을 DNS를 통해 해석합니다.
2. **STATIC**: 서비스 엔드포인트를 정적으로 지정합니다.
3. **NONE**: 서비스 이름 해석을 수행하지 않습니다.

**정적 엔드포인트 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-service
spec:
  hosts:
  - service.example.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 192.168.1.1
  - address: 192.168.1.2
```

**외부 서비스에 대한 트래픽 관리:**

ServiceEntry를 정의한 후, VirtualService와 DestinationRule을 사용하여 외부 서비스에 대한 트래픽을 관리할 수 있습니다:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: external-api-vs
spec:
  hosts:
  - api.example.com
  http:
  - timeout: 3s
    retries:
      attempts: 3
      perTryTimeout: 1s
    route:
    - destination:
        host: api.example.com
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: external-api-dr
spec:
  host: api.example.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1024
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**TLS 설정 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: ServiceEntry
metadata:
  name: external-api-tls
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: external-api-tls-dr
spec:
  host: api.example.com
  trafficPolicy:
    tls:
      mode: SIMPLE  # TLS 연결 사용
      sni: api.example.com  # SNI 설정
```

**ServiceEntry 사용 사례:**

1. **외부 API 접근**: 외부 API(예: 결제 게이트웨이, 소셜 미디어 API 등)에 대한 접근을 관리합니다.
2. **레거시 시스템 통합**: 메시 외부의 레거시 시스템을 서비스 메시와 통합합니다.
3. **멀티 클러스터 통신**: 다른 클러스터의 서비스와 통신합니다.
4. **클라우드 서비스 접근**: AWS S3, Google Cloud Storage 등의 클라우드 서비스에 대한 접근을 관리합니다.
5. **데이터베이스 접근**: 외부 데이터베이스에 대한 접근을 관리합니다.

**ServiceEntry와 Egress Gateway:**

ServiceEntry는 종종 Egress Gateway와 함께 사용되어 외부 서비스에 대한 트래픽을 더 세밀하게 제어합니다:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: istio-egressgateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - api.example.com
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: direct-api-through-egress-gateway
spec:
  hosts:
  - api.example.com
  gateways:
  - istio-egressgateway
  - mesh
  http:
  - match:
    - gateways:
      - mesh
      port: 80
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 80
  - match:
    - gateways:
      - istio-egressgateway
      port: 80
    route:
    - destination:
        host: api.example.com
        port:
          number: 80
```

**다른 옵션들의 문제점:**
- A. 서비스 메시 내부에 새로운 서비스 생성: ServiceEntry는 새로운 서비스를 생성하는 것이 아니라 외부 서비스를 레지스트리에 추가합니다.
- C. 서비스 간 인증 정책 설정: 이는 PeerAuthentication과 AuthorizationPolicy의 역할입니다.
- D. 서비스 버전 간 트래픽 분할: 이는 VirtualService의 주요 기능입니다.
</details>

### 8. Istio에서 'AuthorizationPolicy'의 주요 목적은 무엇인가요?

A. 사용자 인증 관리  
B. 서비스 간 트래픽 라우팅 규칙 정의  
C. 서비스에 대한 접근 제어 정책 정의  
D. 서비스 메시 외부 서비스와의 통합  

<details>
<summary>정답 및 설명</summary>

**정답: C. 서비스에 대한 접근 제어 정책 정의**

**설명:**
Istio에서 'AuthorizationPolicy'의 주요 목적은 서비스에 대한 접근 제어 정책을 정의하는 것입니다. AuthorizationPolicy는 어떤 소스(사용자, 서비스 등)가 어떤 조건에서 어떤 작업(HTTP 메서드, gRPC 작업 등)을 수행할 수 있는지 세밀하게 제어할 수 있게 해줍니다. 이를 통해 최소 권한 원칙을 적용하고 서비스 간 통신의 보안을 강화할 수 있습니다.

**AuthorizationPolicy의 주요 구성 요소:**

1. **selector**: 정책이 적용될 워크로드를 선택합니다.
2. **action**: ALLOW, DENY, CUSTOM 중 하나를 지정합니다.
3. **rules**: 정책 규칙을 정의합니다.
   - **from**: 소스 규칙(principals, namespaces, ip blocks 등)
   - **to**: 대상 규칙(operations, ports 등)
   - **when**: 조건 규칙(headers, request attributes 등)

**AuthorizationPolicy 예시:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: httpbin-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/sleep"]
    - source:
        namespaces: ["test"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/info*"]
    when:
    - key: request.headers[X-Custom-Header]
      values: ["value1", "value2"]
```

이 예시에서:
- `httpbin` 앱에 대한 정책을 정의합니다.
- `default` 네임스페이스의 `sleep` 서비스 계정 또는 `test` 네임스페이스의 소스만 허용합니다.
- `GET` 메서드와 `/info`로 시작하는 경로에 대한 요청만 허용합니다.
- 요청 헤더 `X-Custom-Header`가 `value1` 또는 `value2` 값을 가질 때만 허용합니다.

**ALLOW vs DENY 정책:**

1. **ALLOW 정책**: 명시적으로 허용된 트래픽만 허용하고 나머지는 모두 거부합니다.
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-policy
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["default"]
    to:
    - operation:
        methods: ["GET"]
```

2. **DENY 정책**: 명시적으로 거부된 트래픽만 거부하고 나머지는 모두 허용합니다.
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-policy
spec:
  selector:
    matchLabels:
      app: httpbin
  action: DENY
  rules:
  - from:
    - source:
        namespaces: ["untrusted"]
    to:
    - operation:
        methods: ["POST"]
```

**정책 평가 순서:**

1. CUSTOM 정책이 있으면 먼저 평가됩니다.
2. DENY 정책이 있으면 다음으로 평가됩니다.
3. ALLOW 정책이 있으면 마지막으로 평가됩니다.
4. 일치하는 정책이 없으면 기본적으로 허용됩니다.

**네임스페이스 수준 및 메시 수준 정책:**

1. **네임스페이스 수준 정책**: 특정 네임스페이스의 모든 워크로드에 적용됩니다.
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: ns-level-policy
  namespace: default
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["trusted"]
```

2. **메시 수준 정책**: 루트 네임스페이스(일반적으로 istio-system)에 정의되고 selector가 없는 정책은 메시의 모든 워크로드에 적용됩니다.
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: mesh-level-policy
  namespace: istio-system
spec:
  action: DENY
  rules:
  - from:
    - source:
        namespaces: ["untrusted"]
```

**고급 접근 제어 시나리오:**

1. **JWT 클레임 기반 접근 제어**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: jwt-based-policy
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["*"]
    when:
    - key: request.auth.claims[groups]
      values: ["admin", "developer"]
```

2. **IP 기반 접근 제어**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: ip-based-policy
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        ipBlocks: ["10.0.0.0/24", "192.168.1.0/24"]
```

3. **경로 및 메서드 기반 접근 제어**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: path-method-policy
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - to:
    - operation:
        methods: ["GET"]
        paths: ["/public/*"]
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/admin"]
    to:
    - operation:
        methods: ["*"]
        paths: ["*"]
```

**AuthorizationPolicy와 PeerAuthentication의 차이:**

- **PeerAuthentication**: 서비스 간 통신의 인증 방법(mTLS 등)을 정의합니다.
- **AuthorizationPolicy**: 인증된 클라이언트가 서비스에 접근할 수 있는 권한을 정의합니다.

**다른 옵션들의 문제점:**
- A. 사용자 인증 관리: 이는 RequestAuthentication의 역할입니다.
- B. 서비스 간 트래픽 라우팅 규칙 정의: 이는 VirtualService의 역할입니다.
- D. 서비스 메시 외부 서비스와의 통합: 이는 ServiceEntry의 역할입니다.
</details>
### 9. Istio에서 'Gateway'의 주요 목적은 무엇인가요?

A. 서비스 메시 내부 서비스 간 통신 관리  
B. 서비스 메시 외부에서 내부로의 트래픽 진입점 정의  
C. 서비스 메시 내부에서 외부로의 트래픽 출구점 정의  
D. 서비스 버전 간 트래픽 분할  

<details>
<summary>정답 및 설명</summary>

**정답: B. 서비스 메시 외부에서 내부로의 트래픽 진입점 정의**

**설명:**
Istio에서 'Gateway'의 주요 목적은 서비스 메시 외부에서 내부로의 트래픽 진입점을 정의하는 것입니다. Gateway는 메시 가장자리에서 작동하는 로드 밸런서로, HTTP/HTTPS, TCP, TLS 등의 트래픽을 수신하고 이를 메시 내부 서비스로 라우팅하는 역할을 합니다. Gateway는 인그레스 트래픽을 처리하기 위한 Istio의 방식으로, Kubernetes의 Ingress 리소스보다 더 강력하고 유연한 기능을 제공합니다.

**Gateway의 주요 기능:**

1. **프로토콜 지원**: HTTP, HTTPS, TCP, TLS 등 다양한 프로토콜 지원
2. **포트 구성**: 다양한 포트에서 트래픽 수신
3. **호스트 기반 라우팅**: 여러 호스트 이름에 대한 트래픽 처리
4. **TLS 설정**: SNI 기반 라우팅, TLS 종료, 인증서 구성
5. **VirtualService 연결**: Gateway와 VirtualService를 연결하여 세부적인 라우팅 규칙 정의

**Gateway 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway  # Istio 기본 인그레스 게이트웨이 사용
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "bookinfo.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - "secure.bookinfo.example.com"
    tls:
      mode: SIMPLE
      credentialName: bookinfo-cert
```

이 예시에서:
- `istio: ingressgateway` 레이블이 있는 게이트웨이 워크로드에 적용됩니다.
- HTTP 트래픽은 포트 80에서 `bookinfo.example.com` 호스트에 대해 수신합니다.
- HTTPS 트래픽은 포트 443에서 `secure.bookinfo.example.com` 호스트에 대해 수신하며, TLS 종료를 수행합니다.
- `bookinfo-cert`라는 이름의 인증서를 사용합니다.

**Gateway와 VirtualService 연결:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo
spec:
  hosts:
  - "bookinfo.example.com"
  gateways:
  - bookinfo-gateway  # Gateway 이름 참조
  http:
  - match:
    - uri:
        prefix: /productpage
    - uri:
        prefix: /login
    - uri:
        prefix: /logout
    route:
    - destination:
        host: productpage
        port:
          number: 9080
  - match:
    - uri:
        prefix: /api/v1/products
    route:
    - destination:
        host: product-api
        port:
          number: 9080
```

이 예시에서:
- `bookinfo-gateway`를 통해 들어오는 트래픽에 대한 라우팅 규칙을 정의합니다.
- `/productpage`, `/login`, `/logout` 경로로 들어오는 요청은 `productpage` 서비스로 라우팅됩니다.
- `/api/v1/products` 경로로 들어오는 요청은 `product-api` 서비스로 라우팅됩니다.

**TLS 모드:**

1. **PASSTHROUGH**: TLS 트래픽을 종료하지 않고 그대로 전달합니다.
```yaml
tls:
  mode: PASSTHROUGH
```

2. **SIMPLE**: 서버 측 TLS 종료를 수행합니다.
```yaml
tls:
  mode: SIMPLE
  credentialName: my-cert
```

3. **MUTUAL**: 상호 TLS(mTLS)를 사용하여 클라이언트 인증을 요구합니다.
```yaml
tls:
  mode: MUTUAL
  credentialName: my-cert
  caCertificates: /etc/certs/ca.crt
```

4. **AUTO_PASSTHROUGH**: SNI 값을 기반으로 트래픽을 라우팅합니다.
```yaml
tls:
  mode: AUTO_PASSTHROUGH
```

**인그레스 게이트웨이 vs 이그레스 게이트웨이:**

1. **인그레스 게이트웨이(Ingress Gateway)**:
   - 서비스 메시 외부에서 내부로의 트래픽 진입점
   - 외부 클라이언트의 요청을 메시 내부 서비스로 라우팅

2. **이그레스 게이트웨이(Egress Gateway)**:
   - 서비스 메시 내부에서 외부로의 트래픽 출구점
   - 메시 내부 서비스의 외부 요청을 제어하고 모니터링

**이그레스 게이트웨이 예시:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: istio-egressgateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "external-service.example.com"
```

**Gateway와 Kubernetes Ingress의 차이점:**

1. **프로토콜 지원**: Gateway는 HTTP, HTTPS, TCP, TLS 등 다양한 프로토콜을 지원하지만, Ingress는 주로 HTTP와 HTTPS에 중점을 둡니다.
2. **라우팅 기능**: Gateway는 VirtualService와 함께 사용하여 더 강력한 라우팅 기능을 제공합니다.
3. **TLS 구성**: Gateway는 더 유연한 TLS 구성 옵션을 제공합니다.
4. **다중 포트**: Gateway는 단일 리소스에서 여러 포트를 구성할 수 있습니다.
5. **트래픽 관리**: Gateway는 Istio의 다른 트래픽 관리 기능과 통합됩니다.

**Gateway 사용 시나리오:**

1. **다중 호스트 라우팅**: 여러 도메인 이름에 대한 트래픽을 처리합니다.
2. **TLS 종료**: HTTPS 트래픽을 종료하고 내부적으로 HTTP로 라우팅합니다.
3. **경로 기반 라우팅**: URL 경로에 따라 다른 서비스로 트래픽을 라우팅합니다.
4. **카나리 배포**: 새 버전의 서비스로 일부 트래픽을 라우팅합니다.
5. **A/B 테스팅**: 사용자 그룹에 따라 다른 서비스 버전으로 트래픽을 라우팅합니다.

**다른 옵션들의 문제점:**
- A. 서비스 메시 내부 서비스 간 통신 관리: 이는 주로 VirtualService와 DestinationRule의 역할입니다.
- C. 서비스 메시 내부에서 외부로의 트래픽 출구점 정의: 이는 이그레스 게이트웨이의 역할이지만, Gateway 자체는 주로 인그레스 트래픽을 처리합니다.
- D. 서비스 버전 간 트래픽 분할: 이는 VirtualService의 주요 기능입니다.
</details>

### 10. Istio에서 'PeerAuthentication'의 주요 목적은 무엇인가요?

A. 사용자 인증 관리  
B. 서비스 간 트래픽 라우팅 규칙 정의  
C. 서비스 간 통신의 인증 방법(mTLS 등) 정의  
D. 서비스에 대한 접근 제어 정책 정의  

<details>
<summary>정답 및 설명</summary>

**정답: C. 서비스 간 통신의 인증 방법(mTLS 등) 정의**

**설명:**
Istio에서 'PeerAuthentication'의 주요 목적은 서비스 간 통신의 인증 방법(mTLS 등)을 정의하는 것입니다. PeerAuthentication은 워크로드 간 통신에 사용되는 상호 TLS(mTLS) 모드를 지정하여 서비스 간 통신의 보안을 강화합니다. 이를 통해 서비스 간 통신이 암호화되고 인증되어 중간자 공격, 도청 등으로부터 보호됩니다.

**PeerAuthentication의 주요 기능:**

1. **mTLS 모드 설정**: STRICT, PERMISSIVE, DISABLE 등의 mTLS 모드 지정
2. **워크로드 선택**: 특정 워크로드에 대한 인증 정책 적용
3. **포트별 설정**: 특정 포트에 대해 다른 mTLS 모드 적용
4. **네임스페이스 및 메시 수준 정책**: 네임스페이스 또는 전체 메시에 대한 기본 정책 설정

**PeerAuthentication 예시:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

이 예시에서:
- `istio-system` 네임스페이스에 정의된 정책이므로 메시 전체에 적용됩니다.
- `STRICT` 모드를 사용하여 모든 워크로드 간 통신에 mTLS를 요구합니다.

**mTLS 모드:**

1. **STRICT**: mTLS가 필수입니다. 암호화되지 않은 연결은 거부됩니다.
2. **PERMISSIVE**: mTLS와 일반 텍스트 트래픽을 모두 허용합니다. 주로 마이그레이션 시나리오에서 사용됩니다.
3. **DISABLE**: mTLS를 비활성화합니다. 모든 트래픽은 암호화되지 않습니다.

**네임스페이스 수준 정책:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: my-namespace
spec:
  mtls:
    mode: STRICT
```

이 예시에서:
- `my-namespace` 네임스페이스의 모든 워크로드에 대해 STRICT mTLS 모드를 적용합니다.

**워크로드 수준 정책:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: frontend
  namespace: my-namespace
spec:
  selector:
    matchLabels:
      app: frontend
  mtls:
    mode: STRICT
```

이 예시에서:
- `my-namespace` 네임스페이스에서 `app: frontend` 레이블이 있는 워크로드에만 STRICT mTLS 모드를 적용합니다.

**포트별 mTLS 설정:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: api-server
  namespace: my-namespace
spec:
  selector:
    matchLabels:
      app: api-server
  mtls:
    mode: STRICT
  portLevelMtls:
    8080:
      mode: DISABLE
```

이 예시에서:
- `app: api-server` 레이블이 있는 워크로드에 대해 기본적으로 STRICT mTLS 모드를 적용합니다.
- 포트 8080에 대해서는 mTLS를 비활성화합니다.

**정책 우선순위:**

1. 가장 구체적인 정책이 우선 적용됩니다:
   - 워크로드의 특정 포트에 대한 정책
   - 워크로드에 대한 정책
   - 네임스페이스에 대한 정책
   - 메시 전체에 대한 정책

**mTLS 마이그레이션 시나리오:**

1. **PERMISSIVE 모드로 시작**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE
```

2. **서비스별로 STRICT 모드로 전환**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: service-a
  namespace: my-namespace
spec:
  selector:
    matchLabels:
      app: service-a
  mtls:
    mode: STRICT
```

3. **네임스페이스 전체를 STRICT 모드로 전환**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: my-namespace
spec:
  mtls:
    mode: STRICT
```

4. **메시 전체를 STRICT 모드로 전환**:
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

**DestinationRule과의 관계:**

PeerAuthentication은 서버 측에서 mTLS 요구 사항을 설정하지만, 클라이언트 측에서도 mTLS를 사용하도록 DestinationRule을 구성해야 합니다:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api-server
spec:
  host: api-server.my-namespace.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

**PeerAuthentication과 AuthorizationPolicy의 차이:**

- **PeerAuthentication**: 서비스 간 통신의 인증 방법(mTLS 등)을 정의합니다.
- **AuthorizationPolicy**: 인증된 클라이언트가 서비스에 접근할 수 있는 권한을 정의합니다.

**mTLS의 이점:**

1. **암호화**: 서비스 간 통신이 암호화되어 도청을 방지합니다.
2. **인증**: 통신하는 서비스의 ID를 확인합니다.
3. **무결성**: 전송 중인 데이터가 변조되지 않았음을 보장합니다.
4. **비 부인 방지**: 통신 당사자가 통신 사실을 부인할 수 없습니다.

**다른 옵션들의 문제점:**
- A. 사용자 인증 관리: 이는 RequestAuthentication의 역할입니다.
- B. 서비스 간 트래픽 라우팅 규칙 정의: 이는 VirtualService의 역할입니다.
- D. 서비스에 대한 접근 제어 정책 정의: 이는 AuthorizationPolicy의 역할입니다.
</details>
