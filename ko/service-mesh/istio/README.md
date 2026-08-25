# Istio

Amazon EKS에서 Istio Service Mesh를 활용한 실용적인 가이드입니다.

## 목차

1. [서비스 메시가 정말 필요한가?](#서비스-메시가-정말-필요한가)
2. [설치 및 초기 설정](01-installation.md)
3. [기본 개념](02-basic-concepts.md)
4. [아키텍처](03-architecture.md)
5. [AWS 통합](04-aws-integration.md)
6. [용어집](glossary.md)
7. [Traffic Management (트래픽 관리)](traffic-management/README.md)
8. [Security (보안)](security/README.md)
9. [Observability (관찰성)](observability/README.md)
10. [Resilience (복원력)](resilience/README.md)
11. [Advanced (고급 기능)](advanced/README.md)
12. [Troubleshooting (문제 해결)](troubleshooting/common-errors.md)
13. [모범 사례](best-practices.md)
14. [대안 비교](comparison/README.md)

## Istio란?

Istio는 마이크로서비스를 연결, 보호, 제어 및 관찰하기 위한 오픈 소스 서비스 메시 플랫폼입니다. 복잡한 마이크로서비스 아키텍처에서 서비스 간 통신을 관리하고, 트래픽 제어, 보안, 관찰성을 제공합니다.

### 서비스 메시 개념

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

서비스 메시는 마이크로서비스 간의 통신을 관리하는 인프라 계층입니다. Istio는 각 서비스에 Sidecar Proxy (Envoy)를 배치하여 모든 네트워크 트래픽을 가로채고 제어합니다. 이를 통해 애플리케이션 코드 수정 없이 다음과 같은 기능을 제공합니다:

* **트래픽 라우팅**: 지능형 라우팅, 로드 밸런싱, Canary 배포
* **보안**: 자동 mTLS, 인증, 권한 부여
* **관찰성**: 메트릭, 로그, 분산 추적
* **복원력**: Circuit Breaking, Retry, Timeout

### 실제 사용 예시

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Istio 없는 일반 애플리케이션</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Istio가 적용된 애플리케이션 - 각 서비스에 Envoy Proxy가 Sidecar로 배포됨</em></p>

Istio를 적용하면 각 마이크로서비스에 Envoy Proxy가 Sidecar 컨테이너로 자동 배포되어, 모든 네트워크 트래픽을 투명하게 가로채고 제어합니다.

## 서비스 메시가 정말 필요한가?

서비스 메시는 강력한 도구이지만, 모든 상황에 적합한 것은 아닙니다. 도입 전에 신중한 검토가 필요합니다.

### 의사결정 흐름

```mermaid
flowchart TD
    Start[Service Mesh<br/>도입 고려]

    Q1{마이크로서비스<br/>아키텍처?}
    Q2{10개 이상의<br/>서비스?}
    Q3{복잡한 트래픽<br/>관리 필요?}
    Q4{Zero Trust<br/>보안 필요?}
    Q5{분산 추적/<br/>관찰성 필요?}
    Q6{운영 리소스<br/>확보?}

    NoNeed[Service Mesh<br/>불필요]
    Consider[도입 고려<br/>가능]
    NeedMesh[Service Mesh<br/>권장]

    Alternatives[대안 고려<br/>- Kubernetes NetworkPolicy<br/>- Ingress Controller<br/>- CNI 플러그인<br/>- Application-level 구현]

    Start --> Q1
    Q1 -->|No| NoNeed
    Q1 -->|Yes| Q2
    Q2 -->|No| Alternatives
    Q2 -->|Yes| Q3
    Q3 -->|No| Q4
    Q3 -->|Yes| Q6
    Q4 -->|No| Q5
    Q4 -->|Yes| Q6
    Q5 -->|No| Consider
    Q5 -->|Yes| Q6
    Q6 -->|No| Consider
    Q6 -->|Yes| NeedMesh

    %% 스타일 정의
    classDef question fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef no fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef maybe fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef yes fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef alternative fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class Q1,Q2,Q3,Q4,Q5,Q6 question;
    class NoNeed no;
    class Consider maybe;
    class NeedMesh yes;
    class Alternatives alternative;
```

### Service Mesh가 필요한 경우 ✅

#### 1. 복잡한 마이크로서비스 환경

```mermaid
flowchart LR
    subgraph WithoutMesh["Service Mesh 없이"]
        A1[Service A] -.->|수동 구현| B1[Service B]
        A1 -.->|수동 구현| C1[Service C]
        B1 -.->|수동 구현| D1[Service D]
        C1 -.->|수동 구현| D1

        Note1[각 서비스마다<br/>- 수동 mTLS 구현<br/>- 재시도 로직<br/>- 로깅/메트릭<br/>- Circuit Breaker<br/>중복 코드 증가]
    end

    subgraph WithMesh["Service Mesh 사용"]
        A2[Service A] -->|자동 처리| B2[Service B]
        A2 -->|자동 처리| C2[Service C]
        B2 -->|자동 처리| D2[Service D]
        C2 -->|자동 처리| D2

        SM[Service Mesh<br/>- 자동 mTLS<br/>- 중앙 집중식 정책<br/>- 통합 관찰성<br/>- 표준화된 보안]

        SM -.->|제어| A2
        SM -.->|제어| B2
        SM -.->|제어| C2
        SM -.->|제어| D2
    end

    %% 스타일 정의
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class A1,B1,C1,D1,A2,B2,C2,D2 service;
    class SM mesh;
    class Note1 note;
```

**권장 기준**:

* ✅ 10개 이상의 마이크로서비스
* ✅ 서비스 간 통신이 빈번함 (East-West 트래픽)
* ✅ 다양한 프로그래밍 언어 사용 (Polyglot)
* ✅ 여러 팀이 독립적으로 서비스 개발

#### 2. Zero Trust 보안 요구사항

**Service Mesh 제공**:

* 서비스 간 자동 mTLS 암호화
* SPIFFE 기반 Identity 관리
* 세밀한 인증/인가 정책
* 암호화된 통신 보장

**대안 없이는 달성 어려움**:

* 각 서비스에 보안 로직 중복 구현
* 인증서 수동 관리의 복잡성
* 일관성 없는 보안 정책

#### 3. 고급 트래픽 관리

```yaml
# Canary 배포 (트래픽 분배)
apiVersion: networking.istio.io/v1
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
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # 10%만 새 버전으로
```

**필요한 경우**:

* Canary 배포, A/B 테스트
* 헤더/경로 기반 라우팅
* Traffic Mirroring (Shadow Testing)
* Fault Injection (Chaos Engineering)
* Circuit Breaking, Retry, Timeout

#### 4. 통합 관찰성

**Service Mesh 장점**:

* 애플리케이션 코드 수정 없이 자동 메트릭 수집
* 분산 추적 (Distributed Tracing) 자동 구현
* 통일된 로깅 형식
* 서비스 토폴로지 시각화 (Kiali)

### Service Mesh가 불필요한 경우 ❌

#### 1. 단순한 아키텍처

```mermaid
flowchart LR
    User[사용자] --> LB[로드 밸런서]
    LB --> App[모놀리식<br/>애플리케이션]
    App --> DB[(데이터베이스)]

    Note["Service Mesh 불필요<br/>- 단일 애플리케이션<br/>- 간단한 통신 패턴<br/>- Ingress만으로 충분"]

    %% 스타일 정의
    classDef simple fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class User,LB,App,DB simple;
    class Note note;
```

**대신 사용**:

* Kubernetes Ingress Controller (NGINX, Traefik)
* 간단한 로드 밸런서
* Application-level 구현

#### 2. 소수의 마이크로서비스 (<10개)

**오버헤드가 더 큼**:

* Service Mesh 운영 복잡도 > 얻는 이점
* 5-10개 서비스는 수동 관리 가능
* NetworkPolicy로 충분한 보안

**대안**:

```yaml
# Kubernetes NetworkPolicy로 충분
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. 운영 리소스 부족

**Service Mesh 운영 요구사항**:

* Istio/Envoy 전문 지식
* Control Plane 모니터링 및 관리
* 업그레이드 및 패치 관리
* 문제 해결 능력 (디버깅 복잡도 증가)

**팀 준비 필요**:

* 최소 1-2명의 Service Mesh 전문가
* 지속적인 학습 및 업데이트 추적
* 충분한 테스트 환경

#### 4. 성능이 극도로 중요한 경우

**Service Mesh 오버헤드**:

* 지연 시간: +1-3ms (P50), +5-10ms (P99)
* CPU: 파드당 +10-20%
* 메모리: 파드당 +50-100MB (Sidecar 모드)

**대안 고려**:

* Ambient Mode (리소스 사용량 90% 절감)
* CNI 기반 솔루션 (Cilium)
* Application-level 최적화

### 대안 솔루션 비교

| 기능            | Service Mesh                              | CNI (Cilium) | Ingress Controller | App-level |
| ------------- | ----------------------------------------- | ------------ | ------------------ | --------- |
| **L7 트래픽 관리** | ✅ 완벽 지원                                   | ⚠️ 제한적       | ⚠️ Ingress만        | ✅ 가능      |
| **mTLS 자동화**  | ✅ 완벽 지원                                   | ✅ 가능         | ❌ 미지원              | ❌ 수동 구현   |
| **분산 추적**     | ✅ 자동                                      | ❌ 미지원        | ❌ 미지원              | ⚠️ 수동 구현  |
| **L3/L4 정책**  | ✅ 지원                                      | ✅ 완벽 지원      | ❌ 미지원              | ❌ 미지원     |
| **운영 복잡도**    | 🔴 높음                                     | 🟡 중간        | 🟢 낮음              | 🟡 중간     |
| **리소스 오버헤드**  | <p>🔴 높음 (Sidecar)<br>🟢 낮음 (Ambient)</p> | 🟢 낮음        | 🟢 낮음              | 🟢 없음     |
| **적합한 규모**    | 10+ 서비스                                   | 모든 규모        | 소규모                | 소규모       |

### CNI 기반 솔루션 (Cilium)

Cilium은 eBPF 기반으로 **네트워크 레벨**에서 많은 기능을 제공합니다:

```mermaid
flowchart TB
    subgraph Comparison["기능 비교"]
        subgraph ServiceMesh["Service Mesh (Istio)"]
            SM1[L7 프록시 기반<br/>Envoy Sidecar]
            SM2[애플리케이션 레벨<br/>트래픽 제어]
            SM3[풍부한 L7 기능<br/>Retry, Timeout, etc.]
        end

        subgraph CNI["CNI (Cilium)"]
            CN1[eBPF 기반<br/>커널 레벨]
            CN2[네트워크 레벨<br/>정책 적용]
            CN3[높은 성능<br/>낮은 오버헤드]
        end

        subgraph UseCases["사용 시나리오"]
            UC1[Service Mesh:<br/>복잡한 L7 로직]
            UC2[Cilium:<br/>네트워크 정책, 성능]
            UC3[둘 다:<br/>대규모 엔터프라이즈]
        end
    end

    %% 스타일 정의
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef cni fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef usecase fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class SM1,SM2,SM3 mesh;
    class CN1,CN2,CN3 cni;
    class UC1,UC2,UC3 usecase;
```

**Cilium이 더 적합한 경우**:

* L3/L4 네트워크 정책이 주요 목적
* 높은 성능이 핵심 요구사항
* Service Mesh 운영 부담 회피
* 간단한 mTLS 및 관찰성만 필요

**참고**: [Cilium 문서](../../networking/cilium/README.md)

### 의사결정 체크리스트

도입 전 다음 질문에 답해보세요:

**아키텍처**:

* [ ] 마이크로서비스가 10개 이상인가?
* [ ] 서비스 간 통신이 복잡한가?
* [ ] 여러 프로그래밍 언어를 사용하는가?

**보안**:

* [ ] Zero Trust 보안 모델이 필요한가?
* [ ] 서비스 간 mTLS 암호화가 필수인가?
* [ ] 세밀한 접근 제어가 필요한가?

**트래픽 관리**:

* [ ] Canary 배포, A/B 테스트가 필요한가?
* [ ] 고급 라우팅 규칙이 필요한가?
* [ ] Circuit Breaking, Retry가 많은 서비스에 필요한가?

**관찰성**:

* [ ] 분산 추적이 필수인가?
* [ ] 통합된 메트릭 수집이 필요한가?
* [ ] 서비스 토폴로지 시각화가 필요한가?

**운영**:

* [ ] Service Mesh 전문가가 있는가?
* [ ] 운영 복잡도를 감당할 수 있는가?
* [ ] 리소스 오버헤드를 수용할 수 있는가?

**결과**:

* ✅ 10개 이상 체크: Service Mesh 강력 권장
* 🟡 5-9개 체크: 신중한 평가 필요, 작은 규모로 시작 (Ambient Mode 추천)
* ❌ 4개 이하 체크: 대안 솔루션 고려 (CNI, Ingress, App-level)

### 점진적 도입 전략

Service Mesh가 필요하다고 판단되면, 점진적으로 도입하세요:

```mermaid
flowchart LR
    Phase1[Phase 1<br/>관찰성<br/>메트릭 수집만]
    Phase2[Phase 2<br/>보안<br/>mTLS 적용]
    Phase3[Phase 3<br/>트래픽 관리<br/>Canary 배포]
    Phase4[Phase 4<br/>고급 기능<br/>모든 기능 활용]

    Phase1 -->|검증 후| Phase2
    Phase2 -->|검증 후| Phase3
    Phase3 -->|검증 후| Phase4

    %% 스타일 정의
    classDef phase fill:#326CE5,stroke:#333,stroke-width:2px,color:white;

    %% 클래스 적용
    class Phase1,Phase2,Phase3,Phase4 phase;
```

**권장 순서**:

1. **Pilot 프로젝트** (1-2개 네임스페이스)
2. **관찰성 먼저** (메트릭, 로그, 추적)
3. **보안 적용** (mTLS PERMISSIVE → STRICT)
4. **트래픽 관리** (VirtualService, DestinationRule)
5. **전사 확대**

### 주요 기능

1.  **트래픽 관리**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/traffic-management/request-routing.svg" alt="Traffic Routing" width="500"></div>

    * 지능형 라우팅 및 로드 밸런싱
    * A/B 테스트, Canary 배포, Blue/Green 배포
    * Circuit Breaking, Retry, Timeout 제어
    * Traffic Mirroring 및 Fault Injection
2.  **보안**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * 서비스 간 자동 mTLS 암호화
    * 강력한 인증 및 권한 부여
    * 세밀한 액세스 제어 정책
    * 네트워크 격리 및 보안 정책
3.  **관찰성**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * 자동 메트릭, 로그, 트레이스 생성
    * Prometheus, Grafana, Jaeger, Kiali 통합
    * 서비스 토폴로지 시각화
    * 실시간 트래픽 모니터링
4. **복원력**
   * Circuit Breaker 패턴
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Istio 아키텍처

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio는 Control Plane과 Data Plane으로 구성됩니다:

```mermaid
flowchart TB
    subgraph ControlPlane["Control Plane (istiod)"]
        Pilot[Pilot<br/>서비스 디스커버리 & 트래픽 관리]
        Citadel[Citadel<br/>인증서 관리 & 보안]
        Galley[Galley<br/>구성 관리]
    end

    subgraph DataPlane["Data Plane"]
        subgraph Pod1["Pod 1"]
            App1[애플리케이션]
            Envoy1[Envoy Proxy]
        end

        subgraph Pod2["Pod 2"]
            App2[애플리케이션]
            Envoy2[Envoy Proxy]
        end

        subgraph Pod3["Pod 3"]
            App3[애플리케이션]
            Envoy3[Envoy Proxy]
        end
    end

    Pilot -.->|구성 전달| Envoy1
    Pilot -.->|구성 전달| Envoy2
    Pilot -.->|구성 전달| Envoy3

    Citadel -.->|인증서 발급| Envoy1
    Citadel -.->|인증서 발급| Envoy2
    Citadel -.->|인증서 발급| Envoy3

    Envoy1 <-->|mTLS| Envoy2
    Envoy2 <-->|mTLS| Envoy3
    Envoy1 <-->|mTLS| Envoy3

    App1 -->|요청| Envoy1
    App2 -->|요청| Envoy2
    App3 -->|요청| Envoy3

    %% 스타일 정의
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef dataPlane fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class Pilot,Citadel,Galley controlPlane;
    class App1,App2,App3 app;
    class Envoy1,Envoy2,Envoy3 proxy;
```

**Control Plane (istiod)**:

* **Pilot**: 서비스 디스커버리, 트래픽 라우팅 규칙 관리
* **Citadel**: 인증서 생성 및 관리, mTLS 활성화
* **Galley**: 구성 검증 및 배포

**Data Plane**:

* **Envoy Proxy**: 각 파드에 사이드카로 배포되어 모든 네트워크 트래픽을 가로채고 제어

### Amazon EKS에서 Istio 사용의 이점

1. **간편한 마이크로서비스 관리**
   * 애플리케이션 코드 수정 없이 트래픽 관리
   * 선언적 구성으로 일관된 정책 적용
   * Kubernetes Native API 사용
2. **강화된 보안**
   * 서비스 간 자동 암호화
   * AWS IAM과 통합된 인증
   * 세밀한 권한 제어
3. **향상된 관찰성**
   * Amazon CloudWatch와 통합
   * AWS X-Ray를 통한 분산 추적
   * 상세한 메트릭 및 로그
4. **AWS 서비스와의 통합**
   * Application Load Balancer (ALB) 통합
   * AWS Certificate Manager (ACM) 통합
   * Amazon EBS CSI Driver와 호환

### 시작하기

<div align="center"><img src="https://istio.io/latest/docs/tasks/traffic-management/ingress/ingress-gateway-example/gateway-api-topology.svg" alt="Gateway API Architecture" width="600"></div>

Istio를 처음 사용하신다면 다음 순서로 문서를 읽어보세요:

1. [**설치 및 초기 설정**](01-installation.md): EKS 클러스터에 Istio 설치
2. [**기본 개념**](02-basic-concepts.md): Istio의 핵심 개념 이해
3. [**Traffic Management**](traffic-management/README.md): Gateway, VirtualService, DestinationRule 학습
4. [**Security**](security/README.md): mTLS, 인증, 권한 부여 설정
5. [**Observability**](observability/README.md): 메트릭, 로그, 트레이스 수집
6. [**모범 사례**](best-practices.md): 프로덕션 환경에서의 권장 사항

### 실습 예제

각 섹션에는 실제로 작동하는 YAML 예제가 포함되어 있습니다. 모든 예제는 다음과 같이 클릭하여 복사할 수 있도록 구성되어 있습니다:

```yaml
# 예제 VirtualService
apiVersion: networking.istio.io/v1
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
```

### 참고 자료

* [Istio 공식 문서](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [AWS EKS 워크숍 - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
* [Istio 커뮤니티](https://discuss.istio.io/)

### 퀴즈

이 장에서 배운 내용을 테스트하려면 다음 퀴즈를 풀어보세요:

* [Traffic Management 퀴즈](../../quizzes/service-mesh/istio/traffic-management.md)
* [Security 퀴즈](../../quizzes/service-mesh/istio/security.md)
* [Observability 퀴즈](../../quizzes/service-mesh/istio/observability.md)
* [Resilience 퀴즈](../../quizzes/service-mesh/istio/resilience.md)
* [Advanced 퀴즈](../../quizzes/service-mesh/istio/advanced.md)
