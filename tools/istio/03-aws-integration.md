# AWS 통합

이 문서에서는 Amazon EKS 환경에서 Istio를 AWS 서비스와 통합하는 방법을 다룹니다.

## 목차

1. [AWS Load Balancer 통합](#aws-load-balancer-통합)
2. [Istio vs 다른 솔루션 비교](#istio-vs-다른-솔루션-비교)
3. [EKS 특화 최적화](#eks-특화-최적화)
4. [모범 사례](#모범-사례)

## AWS Load Balancer 통합

Istio Ingress Gateway를 AWS Load Balancer와 통합하여 외부 트래픽을 처리할 수 있습니다.

### Network Load Balancer (NLB) 통합

NLB는 Layer 4 (TCP/UDP) 로드 밸런서로, 높은 성능과 낮은 지연시간이 필요한 경우 적합합니다.

#### NLB 아키텍처

```mermaid
flowchart TB
    Client[클라이언트]

    subgraph AWS["AWS 클라우드"]
        NLB[Network Load Balancer<br/>Layer 4]

        subgraph EKS["EKS 클러스터"]
            subgraph IstioGW["Istio Ingress Gateway"]
                IGW1[Gateway Pod 1<br/>Envoy Proxy]
                IGW2[Gateway Pod 2<br/>Envoy Proxy]
            end

            subgraph Apps["애플리케이션"]
                App1[Service A<br/>Pod]
                App2[Service B<br/>Pod]
            end
        end
    end

    Client -->|HTTPS 요청| NLB
    NLB -->|TCP 443| IGW1
    NLB -->|TCP 443| IGW2
    IGW1 -->|HTTP/HTTPS| App1
    IGW1 -->|HTTP/HTTPS| App2
    IGW2 -->|HTTP/HTTPS| App1
    IGW2 -->|HTTP/HTTPS| App2

    %% 스타일 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class Client default;
    class NLB awsService;
    class IGW1,IGW2 k8sComponent;
    class App1,App2 userApp;
```

#### NLB 설정

**1. AWS Load Balancer Controller 설치**

```bash
# IAM 정책 생성
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# IRSA 설정
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Helm으로 컨트롤러 설치
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**2. NLB를 사용하는 Istio Ingress Gateway 설정**

```yaml
# istio-ingress-nlb.yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # NLB 설정
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

    # TLS 설정
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/cert-id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"

    # 헬스 체크 설정
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: "http"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "15021"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/healthz/ready"

    # 추가 설정
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
spec:
  type: LoadBalancer
  selector:
    app: istio-ingressgateway
    istio: ingressgateway
  ports:
  - name: status-port
    port: 15021
    protocol: TCP
    targetPort: 15021
  - name: http2
    port: 80
    protocol: TCP
    targetPort: 8080
  - name: https
    port: 443
    protocol: TCP
    targetPort: 8443
```

**3. Gateway 리소스 설정**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
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
      credentialName: my-tls-secret
    hosts:
    - "myapp.example.com"
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true
```

#### NLB 장점

- **높은 성능**: 초당 수백만 요청 처리
- **낮은 지연시간**: Layer 4에서 동작하여 빠른 응답
- **고정 IP**: Elastic IP 할당 가능
- **프로토콜 지원**: TCP, UDP, TLS
- **비용 효율적**: ALB보다 저렴

#### NLB 사용 시나리오

- WebSocket, gRPC 등 장시간 연결이 필요한 경우
- 초당 수백만 요청을 처리해야 하는 경우
- 고정 IP가 필요한 경우
- TLS 종료를 Istio에서 수행하려는 경우

### Application Load Balancer (ALB) 통합

ALB는 Layer 7 (HTTP/HTTPS) 로드 밸런서로, 고급 라우팅 기능이 필요한 경우 적합합니다.

#### ALB 아키텍처

```mermaid
flowchart TB
    Client[클라이언트]

    subgraph AWS["AWS 클라우드"]
        ALB[Application Load Balancer<br/>Layer 7]

        subgraph EKS["EKS 클러스터"]
            subgraph IstioGW["Istio Ingress Gateway"]
                IGW1[Gateway Pod 1]
                IGW2[Gateway Pod 2]
            end

            subgraph Apps["애플리케이션"]
                App1[Service A]
                App2[Service B]
            end
        end
    end

    Client -->|HTTPS| ALB
    ALB -->|HTTP/2| IGW1
    ALB -->|HTTP/2| IGW2
    IGW1 -->|내부 라우팅| App1
    IGW1 -->|내부 라우팅| App2
    IGW2 -->|내부 라우팅| App1
    IGW2 -->|내부 라우팅| App2

    %% 스타일 정의
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% 클래스 적용
    class Client default;
    class ALB awsService;
    class IGW1,IGW2 k8sComponent;
    class App1,App2 userApp;
```

#### ALB 설정

**1. Ingress 리소스로 ALB 생성**

```yaml
# istio-ingress-alb.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: istio-ingress
  namespace: istio-system
  annotations:
    # ALB 설정
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'

    # ACM 인증서
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/cert-id

    # 헬스 체크
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-port: '15021'
    alb.ingress.kubernetes.io/healthcheck-path: /healthz/ready
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'

    # 추가 설정
    alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=60
    alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30
spec:
  ingressClassName: alb
  rules:
  - host: "myapp.example.com"
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
```

**2. 경로 기반 라우팅**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: istio-ingress-path-based
  namespace: istio-system
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: "api.example.com"
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
  - host: "admin.example.com"
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
```

#### ALB 장점

- **고급 라우팅**: Path, Header, Query String 기반 라우팅
- **WAF 통합**: AWS WAF로 보안 강화
- **인증 통합**: Cognito, OIDC 통합
- **ACM 통합**: 인증서 자동 관리
- **컨테이너 최적화**: ECS, EKS에 최적화

#### ALB 사용 시나리오

- HTTP/HTTPS 전용 트래픽
- 경로 기반 라우팅이 필요한 경우
- WAF 보안이 필요한 경우
- 여러 도메인을 단일 로드 밸런서에서 처리하는 경우

### NLB vs ALB 비교

| 특성 | NLB | ALB |
|------|-----|-----|
| **OSI Layer** | Layer 4 (TCP/UDP) | Layer 7 (HTTP/HTTPS) |
| **성능** | 초당 수백만 요청 | 초당 수만 요청 |
| **지연시간** | 매우 낮음 | 낮음 |
| **고정 IP** | 지원 (Elastic IP) | 미지원 |
| **TLS 종료** | TCP로 전달 (Istio에서 처리) | ALB에서 처리 가능 |
| **라우팅** | IP/Port 기반 | Path, Host, Header 기반 |
| **WAF 통합** | 불가 | 가능 |
| **비용** | 저렴 | 상대적으로 비쌈 |
| **WebSocket** | 네이티브 지원 | 지원 |
| **gRPC** | 네이티브 지원 | HTTP/2 필요 |
| **권장 사용** | 높은 성능, WebSocket, gRPC | HTTP 라우팅, WAF, 인증 |

## Istio vs 다른 솔루션 비교

### Istio vs VPC Lattice

VPC Lattice는 AWS의 관리형 애플리케이션 네트워킹 서비스입니다.

#### 아키텍처 비교

```mermaid
flowchart TB
    subgraph Istio["Istio 아키텍처"]
        direction TB
        ICP[istiod<br/>Control Plane]

        subgraph IPods["파드들"]
            IA1[App<br/>+ Envoy]
            IA2[App<br/>+ Envoy]
        end

        ICP -.->|구성| IA1
        ICP -.->|구성| IA2
        IA1 <-->|mTLS| IA2
    end

    subgraph VPCLattice["VPC Lattice 아키텍처"]
        direction TB
        LSN[Service Network<br/>관리형 서비스]

        subgraph LPods["파드들"]
            LA1[App<br/>사이드카 없음]
            LA2[App<br/>사이드카 없음]
        end

        LA1 -->|HTTP| LSN
        LA2 -->|HTTP| LSN
        LSN -->|라우팅| LA1
        LSN -->|라우팅| LA2
    end

    %% 스타일 정의
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class ICP controlPlane;
    class IA1,IA2 k8sComponent;
    class LSN controlPlane;
    class LA1,LA2 userApp;
```

#### 기능 비교

| 특성 | Istio | VPC Lattice |
|------|-------|-------------|
| **관리 주체** | 자체 관리 (Self-managed) | AWS 관리형 (Fully-managed) |
| **사이드카** | 필요 (Sidecar 또는 Ambient) | 불필요 |
| **리소스 오버헤드** | 높음 (각 파드에 Envoy) | 낮음 (사이드카 없음) |
| **복잡도** | 높음 | 낮음 |
| **학습 곡선** | 가파름 | 완만함 |
| **트래픽 관리** | 매우 고급 (세밀한 제어) | 기본적 (충분한 기능) |
| **mTLS** | 자동, 세밀한 제어 | 지원 |
| **Observability** | 풍부한 메트릭, 트레이스 | 기본 메트릭 |
| **Fault Injection** | 지원 | 미지원 |
| **Circuit Breaker** | 세밀한 제어 | 기본 기능 |
| **Rate Limiting** | Local + Global | 기본 기능 |
| **Multi-cluster** | 강력한 지원 | VPC 간 연결 |
| **크로스 계정** | 복잡 | 간단 (네이티브 지원) |
| **비용** | 컴퓨팅 비용 (EC2) | 서비스 사용 비용 |
| **벤더 종속** | 없음 (오픈소스) | AWS 종속 |
| **Kubernetes 전용** | 예 | 아니오 (EC2, Lambda 등) |

#### 언제 Istio를 선택할까?

**Istio가 적합한 경우:**

1. **세밀한 트래픽 제어 필요**
   - Canary 배포, A/B 테스트, Traffic Mirroring
   - 복잡한 라우팅 규칙 (Header, Cookie 기반 등)
   - Fault Injection으로 Chaos Engineering

2. **강력한 보안 요구사항**
   - 서비스 간 자동 mTLS 암호화
   - 세밀한 권한 부여 정책
   - JWT 검증, RBAC

3. **고급 관찰성 필요**
   - 상세한 메트릭 (Latency P50/P95/P99)
   - 분산 추적 (Jaeger, Zipkin)
   - 서비스 토폴로지 시각화 (Kiali)

4. **멀티 클러스터 메시**
   - 여러 EKS 클러스터 간 통신
   - 클러스터 간 페일오버
   - 글로벌 로드 밸런싱

5. **벤더 독립성**
   - 다른 클라우드 또는 온프레미스로 이동 가능성
   - Kubernetes 표준 사용

**예제: Istio의 고급 트래픽 관리**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  # Header 기반 라우팅
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # Canary 배포 (10%)
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
      weight: 10
    - destination:
        host: reviews
        subset: v2
      weight: 90
  # Traffic Mirroring
  - route:
    - destination:
        host: reviews
        subset: v2
    mirror:
      host: reviews
      subset: v3
    mirrorPercentage:
      value: 100
```

#### 언제 VPC Lattice를 선택할까?

**VPC Lattice가 적합한 경우:**

1. **간단한 서비스 연결**
   - 기본적인 로드 밸런싱과 라우팅만 필요
   - 빠른 구현이 중요

2. **낮은 운영 오버헤드**
   - AWS 관리형 서비스 선호
   - 사이드카 관리 부담 없음

3. **크로스 VPC/계정 통신**
   - 여러 AWS 계정 간 서비스 연결
   - VPC 피어링 없이 통신

4. **혼합 환경**
   - EKS + EC2 + Lambda 혼합 환경
   - Kubernetes만이 아닌 다양한 컴퓨팅 사용

5. **비용 최적화**
   - 사이드카 리소스 비용 절감
   - 작은 규모의 서비스

#### Istio + VPC Lattice 함께 사용하기

두 솔루션은 상호 배타적이지 않으며, 함께 사용할 수 있습니다:

```mermaid
flowchart TB
    subgraph Account1["AWS 계정 1"]
        subgraph EKS1["EKS 클러스터 1 (Istio)"]
            Istiod1[istiod]
            App1[Service A<br/>+ Envoy]
            App2[Service B<br/>+ Envoy]

            Istiod1 -.->|구성| App1
            Istiod1 -.->|구성| App2
        end
    end

    subgraph Account2["AWS 계정 2"]
        subgraph EKS2["EKS 클러스터 2"]
            App3[Service C<br/>사이드카 없음]
        end

        Lambda[Lambda<br/>함수]
    end

    VPCLattice[VPC Lattice<br/>Service Network]

    App1 <-->|내부 mTLS| App2
    App1 -->|VPC Lattice| VPCLattice
    VPCLattice -->|라우팅| App3
    VPCLattice -->|라우팅| Lambda

    %% 스타일 정의
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% 클래스 적용
    class Istiod1,VPCLattice controlPlane;
    class App1,App2 k8sComponent;
    class App3,Lambda userApp;
```

**사용 사례:**

- **클러스터 내부**: Istio로 세밀한 트래픽 관리와 보안
- **클러스터 간/크로스 계정**: VPC Lattice로 간단한 연결
- **혼합 환경**: Istio 클러스터와 Lambda/EC2 연결에 VPC Lattice 사용

### Istio vs Cilium (eBPF 기반)

Cilium은 eBPF를 사용하는 Kubernetes 네트워킹 및 보안 솔루션입니다.

#### 아키텍처 비교

| 특성 | Istio | Cilium |
|------|-------|--------|
| **기술 스택** | Envoy Proxy (사이드카) | eBPF (커널 레벨) |
| **주요 목적** | Service Mesh | CNI + Service Mesh |
| **네트워킹** | Kubernetes CNI 위에 동작 | CNI 자체를 제공 |
| **성능** | 좋음 | 매우 우수 (커널 레벨) |
| **리소스 사용** | 높음 (사이드카) | 낮음 (커널 레벨) |
| **L7 기능** | 매우 강력 | 기본적 |
| **관찰성** | 풍부함 | Hubble (기본적) |
| **학습 곡선** | 가파름 | 가파름 |
| **성숙도** | 높음 | 중간 (Service Mesh 기능) |

#### 기능 비교

| 기능 | Istio | Cilium |
|------|-------|--------|
| **Network Policy** | Kubernetes + Istio | Kubernetes + Cilium (더 강력) |
| **L7 Load Balancing** | 매우 세밀함 | 기본적 |
| **mTLS** | 자동, 세밀한 제어 | 지원 |
| **Traffic Management** | 매우 고급 | 기본적 |
| **Observability** | Prometheus, Jaeger, Kiali | Hubble |
| **성능** | 좋음 | 우수 |
| **Multi-cluster** | 강력함 | Cluster Mesh |

#### 언제 무엇을 선택할까?

**Istio 선택:**
- L7 트래픽 관리가 핵심 요구사항
- 강력한 서비스 메시 기능 필요
- 풍부한 관찰성과 디버깅 도구 필요

**Cilium 선택:**
- CNI 교체를 고려 중
- 네트워크 보안이 주 관심사
- 성능 최적화가 중요
- eBPF 기술 활용 원함

**함께 사용:**
- Cilium을 CNI로, Istio를 Service Mesh로 사용 가능
- 단, 기능 중복과 복잡도 증가 고려 필요

## EKS 특화 최적화

### IAM Roles for Service Accounts (IRSA) 통합

Istio 워크로드가 AWS 서비스에 안전하게 접근할 수 있도록 IRSA를 설정합니다.

#### IRSA 설정

```bash
# 1. OIDC 프로바이더 생성
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. IAM 정책 생성
cat <<EOF > app-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-bucket",
                "arn:aws:s3:::my-bucket/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name MyAppS3Policy \
    --policy-document file://app-policy.json

# 3. Service Account에 IAM Role 연결
eksctl create iamserviceaccount \
    --cluster my-cluster \
    --namespace default \
    --name my-app-sa \
    --attach-policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/MyAppS3Policy \
    --approve
```

#### Istio와 IRSA 사용

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/my-app-role
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-sa  # IRSA 사용
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: AWS_REGION
          value: us-west-2
```

### AWS Certificate Manager (ACM) 통합

ACM 인증서를 Istio Gateway에서 사용하는 방법입니다.

#### NLB에서 TLS 종료

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/cert-id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
  ports:
  - name: https
    port: 443
    targetPort: 8443
```

#### Istio에서 TLS 종료 (ACM Private CA)

```bash
# 1. ACM Private CA에서 인증서 발급
aws acm-pca issue-certificate \
    --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/ca-id \
    --csr file://csr.pem \
    --signing-algorithm "SHA256WITHRSA" \
    --validity Value=365,Type="DAYS"

# 2. Kubernetes Secret 생성
kubectl create secret tls my-tls-secret \
    --cert=certificate.pem \
    --key=private-key.pem \
    -n istio-system

# 3. Gateway에서 사용
```

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
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
      credentialName: my-tls-secret  # ACM 인증서
    hosts:
    - "myapp.example.com"
```

### CloudWatch Container Insights 통합

Istio 메트릭을 CloudWatch로 전송하여 통합 모니터링을 구현합니다.

#### CloudWatch Agent 설정

```bash
# 1. IAM 정책 연결
eksctl create iamserviceaccount \
    --cluster my-cluster \
    --namespace amazon-cloudwatch \
    --name cloudwatch-agent \
    --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy \
    --approve

# 2. CloudWatch Agent 설치
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-serviceaccount.yaml
```

#### Prometheus 메트릭 스크래핑

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: amazon-cloudwatch
data:
  prometheus.yaml: |
    global:
      scrape_interval: 1m
      scrape_timeout: 10s

    scrape_configs:
    # Istio Control Plane 메트릭
    - job_name: 'istiod'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: istiod;http-monitoring

    # Envoy 사이드카 메트릭
    - job_name: 'envoy-stats'
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_container_port_name]
        action: keep
        regex: '.*-envoy-prom'
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:15090
        target_label: __address__
```

#### CloudWatch Logs Insights 쿼리

```sql
-- Istio 에러 로그 분석
fields @timestamp, @message
| filter @logStream like /istio-proxy/
| filter @message like /error/
| sort @timestamp desc
| limit 100

-- 요청 지연시간 분석
fields @timestamp, request_duration_ms
| filter @logStream like /istio-proxy/
| stats avg(request_duration_ms), max(request_duration_ms), pct(request_duration_ms, 95) by bin(5m)
```

### EKS 최적화 설정

#### 1. Pod Resources 최적화

```yaml
# Envoy 사이드카 리소스 최적화
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        # EKS 최적화
        ISTIO_META_DNS_CAPTURE: "true"
        ISTIO_META_DNS_AUTO_ALLOCATE: "true"
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 2000m
            memory: 1024Mi
        # Connection pool 설정
        concurrency: 2
```

#### 2. Cluster Autoscaler 고려

```yaml
# Istio Gateway Autoscaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: istio-ingressgateway
  namespace: istio-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: istio-ingressgateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 3. Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: istio-ingressgateway
  namespace: istio-system
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: istio-ingressgateway
```

## 모범 사례

### 1. 로드 밸런서 선택 가이드

**NLB 사용:**
- gRPC, WebSocket 등 장시간 연결
- 초당 수백만 요청 처리
- 고정 IP 필요
- TLS 종료를 Istio에서 수행

**ALB 사용:**
- HTTP/HTTPS 전용
- 경로 기반 라우팅
- WAF 보안 필요
- Cognito 인증 통합

### 2. TLS 종료 위치

**로드 밸런서에서 종료 (권장):**
- ACM 인증서 자동 갱신
- 관리 용이
- Istio 부하 감소

**Istio에서 종료:**
- 엔드 투 엔드 암호화 필요
- 세밀한 TLS 정책 제어
- mTLS 사용

### 3. 비용 최적화

- **Spot 인스턴스**: Istio Gateway 워크로드에 활용
- **Graviton 인스턴스**: ARM 기반으로 비용 절감
- **리소스 제한**: 사이드카 리소스 적절히 설정
- **Ambient Mode**: 사이드카 오버헤드 제거 고려

### 4. 보안

- **IRSA**: IAM 역할로 AWS 서비스 접근
- **Security Group**: 최소 권한 원칙
- **mTLS**: 서비스 간 암호화 활성화
- **Network Policy**: Cilium 또는 Calico와 함께 사용

### 5. 모니터링

- **CloudWatch**: 통합 로그 및 메트릭
- **X-Ray**: 분산 추적
- **Prometheus + Grafana**: 상세 메트릭
- **Kiali**: 서비스 메시 시각화

## 다음 단계

AWS 통합을 완료했다면 다음 문서를 참고하세요:

1. **[Traffic Management](traffic-management/README.md)**: 고급 트래픽 관리 기능
2. **[Security](security/README.md)**: mTLS 및 인증/권한 부여
3. **[Observability](observability/README.md)**: 메트릭, 로그, 트레이스 수집

## 참고 자료

- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS Best Practices - Networking](https://aws.github.io/aws-eks-best-practices/networking/)
- [VPC Lattice Documentation](https://docs.aws.amazon.com/vpc-lattice/)
- [Cilium Documentation](https://docs.cilium.io/)
- [AWS Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
