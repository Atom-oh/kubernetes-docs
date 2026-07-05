# EKS 네트워킹 퀴즈 - Part 3

이 퀴즈는 Amazon EKS의 고급 네트워킹 개념, 서비스 메시, VPC 엔드포인트, 멀티 클러스터 네트워킹 및 네트워크 보안에 대한 이해를 테스트합니다.

## 객관식 문제

### 1. Amazon EKS에서 서비스 메시(예: AWS App Mesh, Istio)를 구현할 때 발생하는 네트워킹 아키텍처의 주요 변화는 무엇인가요?

A. 모든 파드 간 통신이 VPC 외부로 라우팅됩니다\
B. 각 파드에 사이드카 프록시가 추가되어 서비스 간 통신을 중재합니다\
C. Kubernetes Service 객체가 더 이상 사용되지 않습니다\
D. 모든 네트워크 트래픽이 AWS Transit Gateway를 통해 라우팅됩니다

<details>

<summary>정답 및 설명</summary>

**정답: B. 각 파드에 사이드카 프록시가 추가되어 서비스 간 통신을 중재합니다**

**설명:** 서비스 메시를 구현할 때 가장 중요한 아키텍처 변화는 각 파드에 사이드카 프록시(일반적으로 Envoy)가 추가된다는 것입니다. 이 사이드카 프록시는 파드의 모든 인바운드 및 아웃바운드 트래픽을 가로채고 처리하여 서비스 간 통신을 중재합니다.

**주요 특징:**

1. **사이드카 패턴**: 각 애플리케이션 컨테이너 옆에 프록시 컨테이너가 배포됩니다. 이 프록시는 모든 네트워크 통신을 처리합니다.
2. **트래픽 흐름 변화**:
   * 기존: 클라이언트 → 서비스 → 대상 파드
   * 서비스 메시: 클라이언트 → 클라이언트 사이드카 → 서비스 → 대상 사이드카 → 대상 파드
3. **데이터 플레인과 컨트롤 플레인**:
   * 데이터 플레인: 사이드카 프록시의 집합
   * 컨트롤 플레인: 프록시 구성을 관리하고 정책을 적용하는 중앙 구성 요소
4. **애플리케이션 코드 변경 없음**: 서비스 메시의 주요 이점 중 하나는 애플리케이션 코드를 변경하지 않고도 고급 네트워킹 기능을 추가할 수 있다는 것입니다.

**서비스 메시 구현 예시 (AWS App Mesh):**

```yaml
# App Mesh 사이드카 주입 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh 메시 이름
        appmesh.k8s.aws/virtualNode: example-vn  # 가상 노드 이름
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**서비스 메시가 제공하는 기능:**

* 트래픽 관리 (라우팅, 로드 밸런싱, 서킷 브레이킹)
* 보안 (mTLS, 인증, 권한 부여)
* 관찰 가능성 (메트릭, 로그, 분산 추적)
* 정책 적용

다른 옵션들의 문제점:

* **A. 모든 파드 간 통신이 VPC 외부로 라우팅됩니다**: 서비스 메시는 일반적으로 클러스터 내부에서 작동하며, 트래픽을 VPC 외부로 라우팅하지 않습니다.
* **C. Kubernetes Service 객체가 더 이상 사용되지 않습니다**: 서비스 메시는 Kubernetes Service 객체를 대체하지 않고 보완합니다.
* **D. 모든 네트워크 트래픽이 AWS Transit Gateway를 통해 라우팅됩니다**: 서비스 메시는 AWS Transit Gateway와 관련이 없으며, 클러스터 내부의 서비스 간 통신을 관리합니다.

</details>

### 2. Amazon EKS에서 VPC 엔드포인트를 사용하여 AWS 서비스에 비공개로 액세스할 때의 주요 이점은 무엇인가요?

A. 모든 AWS 서비스에 대한 무제한 대역폭 제공\
B. 인터넷 게이트웨이 없이도 AWS 서비스에 비공개로 액세스 가능\
C. AWS 서비스 사용 비용 50% 절감\
D. 모든 AWS 서비스에 대한 자동 인증 제공

<details>

<summary>정답 및 설명</summary>

**정답: B. 인터넷 게이트웨이 없이도 AWS 서비스에 비공개로 액세스 가능**

**설명:** Amazon EKS에서 VPC 엔드포인트를 사용하는 주요 이점은 인터넷 게이트웨이 없이도 AWS 서비스에 비공개로 액세스할 수 있다는 것입니다. 이를 통해 보안을 강화하고 데이터 전송 비용을 절감할 수 있습니다.

**VPC 엔드포인트 유형:**

1. **인터페이스 엔드포인트 (AWS PrivateLink)**:
   * 대부분의 AWS 서비스에 대한 비공개 연결 제공
   * 각 서브넷에 엔드포인트 네트워크 인터페이스(ENI) 생성
   * 예: ECR, CloudWatch, SNS, SQS 등
2. **게이트웨이 엔드포인트**:
   * S3 및 DynamoDB에 대한 비공개 연결 제공
   * 라우팅 테이블에 경로 추가
   * 추가 비용 없음

**EKS에서 VPC 엔드포인트 구성 예시:**

```yaml
# CloudFormation 예시
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VPC
      RouteTableIds:
        - !Ref PrivateRouteTable
      VpcEndpointType: Gateway
      
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VPC
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
      SecurityGroupIds:
        - !Ref EndpointSecurityGroup
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```

**EKS에서 VPC 엔드포인트를 사용해야 하는 주요 AWS 서비스:**

* Amazon ECR (컨테이너 이미지 가져오기)
* Amazon S3 (구성 파일, 백업 등)
* AWS KMS (암호화 키)
* Amazon CloudWatch (로깅 및 모니터링)
* AWS STS (IAM 역할 수임)

**VPC 엔드포인트 사용의 이점:**

1. **보안 강화**: 트래픽이 공용 인터넷을 통과하지 않음
2. **네트워크 비용 절감**: AWS 서비스로의 데이터 전송 비용 감소
3. **지연 시간 감소**: AWS 네트워크 내에서 직접 라우팅
4. **규정 준수**: 데이터 주권 및 규정 준수 요구 사항 충족

**프라이빗 서브넷의 EKS 노드 구성:**

```bash
# eksctl로 프라이빗 서브넷에 노드 그룹 생성
eksctl create nodegroup \
  --cluster my-cluster \
  --name private-ng \
  --node-private-networking \
  --vpc-private-subnets subnet-0123456789abcdef0,subnet-0123456789abcdef1
```

다른 옵션들의 문제점:

* **A. 모든 AWS 서비스에 대한 무제한 대역폭 제공**: VPC 엔드포인트는 무제한 대역폭을 제공하지 않으며, 서비스 및 리전에 따라 대역폭 제한이 있을 수 있습니다.
* **C. AWS 서비스 사용 비용 50% 절감**: VPC 엔드포인트는 데이터 전송 비용을 절감할 수 있지만, AWS 서비스 사용 비용 자체를 50% 절감하지는 않습니다.
* **D. 모든 AWS 서비스에 대한 자동 인증 제공**: VPC 엔드포인트는 인증을 자동화하지 않으며, 여전히 적절한 IAM 권한이 필요합니다.

</details>

### 3. Amazon EKS에서 멀티 클러스터 네트워킹을 구현하기 위한 가장 효과적인 방법은 무엇인가요?

A. 각 클러스터에 퍼블릭 로드 밸런서를 사용하여 클러스터 간 통신 구현\
B. AWS Transit Gateway를 사용하여 여러 VPC를 연결하고 클러스터 간 라우팅 구성\
C. 모든 클러스터를 단일 VPC에 배포하여 네트워크 복잡성 감소\
D. 각 클러스터에 NAT 게이트웨이를 사용하여 클러스터 간 통신 구현

<details>

<summary>정답 및 설명</summary>

**정답: B. AWS Transit Gateway를 사용하여 여러 VPC를 연결하고 클러스터 간 라우팅 구성**

**설명:** Amazon EKS에서 멀티 클러스터 네트워킹을 구현하기 위한 가장 효과적인 방법은 AWS Transit Gateway를 사용하여 여러 VPC를 연결하고 클러스터 간 라우팅을 구성하는 것입니다. 이 접근 방식은 확장성, 보안 및 관리 용이성을 제공합니다.

**AWS Transit Gateway를 사용한 멀티 클러스터 네트워킹:**

1. **아키텍처 개요**:
   * 각 EKS 클러스터는 별도의 VPC에 배포
   * Transit Gateway가 모든 VPC를 연결
   * 클러스터 간 통신은 Transit Gateway를 통해 라우팅
2.  **구성 단계**:

    ```bash
    # 1. Transit Gateway 생성
    aws ec2 create-transit-gateway --description "EKS Multi-Cluster TGW"

    # 2. VPC를 Transit Gateway에 연결
    aws ec2 create-transit-gateway-vpc-attachment \
      --transit-gateway-id tgw-0123456789abcdef0 \
      --vpc-id vpc-0123456789abcdef0 \
      --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1

    # 3. 라우팅 테이블 업데이트
    aws ec2 create-route \
      --route-table-id rtb-0123456789abcdef0 \
      --destination-cidr-block 10.1.0.0/16 \
      --transit-gateway-id tgw-0123456789abcdef0
    ```
3. **CIDR 계획**:
   * 각 클러스터/VPC에 겹치지 않는 CIDR 블록 할당
   * 예: Cluster1: 10.0.0.0/16, Cluster2: 10.1.0.0/16, Cluster3: 10.2.0.0/16

**멀티 클러스터 서비스 디스커버리 옵션:**

1.  **AWS Cloud Map**:

    ```bash
    # 네임스페이스 생성
    aws servicediscovery create-private-dns-namespace \
      --name multi-cluster.local \
      --vpc vpc-0123456789abcdef0

    # 서비스 등록
    aws servicediscovery register-instance \
      --service-id srv-0123456789abcdef0 \
      --instance-id api-service-cluster1 \
      --attributes AWS_INSTANCE_IPV4=10.0.1.123
    ```
2.  **CoreDNS 사용자 지정 구성**:

    ```yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: coredns
      namespace: kube-system
    data:
      Corefile: |
        .:53 {
            errors
            health
            kubernetes cluster.local in-addr.arpa ip6.arpa {
               pods insecure
               upstream
               fallthrough in-addr.arpa ip6.arpa
            }
            forward . /etc/resolv.conf
            cache 30
            loop
            reload
            loadbalance
        }
        cluster2.svc.local:53 {
            errors
            cache 30
            forward . 10.1.0.2
        }
    ```

**멀티 클러스터 네트워킹 보안 고려 사항:**

1. **VPC 간 트래픽 제어**:
   * Transit Gateway 보안 그룹 및 라우팅 테이블을 사용하여 트래픽 제한
   * 필요한 포트 및 프로토콜만 허용
2.  **네트워크 정책**:

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-cross-cluster
    spec:
      podSelector:
        matchLabels:
          app: api-service
      ingress:
      - from:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2의 CIDR
      egress:
      - to:
        - ipBlock:
            cidr: 10.1.0.0/16  # Cluster2의 CIDR
    ```

**멀티 클러스터 서비스 메시 옵션:**

1. **Istio 멀티 클러스터**:
   * 단일 컨트롤 플레인으로 여러 클러스터 관리
   * 클러스터 간 서비스 디스커버리 및 로드 밸런싱
2. **AWS App Mesh**:
   * 여러 클러스터에 걸쳐 있는 메시 생성
   * AWS Cloud Map을 통한 서비스 디스커버리

**비용 최적화 고려 사항:**

* Transit Gateway 시간당 요금 및 데이터 처리 요금 고려
* 클러스터 간 데이터 전송 최소화
* 가능한 경우 동일한 가용 영역 내에서 통신

다른 옵션들의 문제점:

* **A. 각 클러스터에 퍼블릭 로드 밸런서를 사용하여 클러스터 간 통신 구현**: 이 방법은 보안 위험을 증가시키고, 인터넷 데이터 전송 비용이 발생하며, 지연 시간이 증가합니다.
* **C. 모든 클러스터를 단일 VPC에 배포하여 네트워크 복잡성 감소**: 단일 VPC에 여러 클러스터를 배포하면 IP 주소 공간 제한, 보안 경계 부족, 확장성 문제가 발생할 수 있습니다.
* **D. 각 클러스터에 NAT 게이트웨이를 사용하여 클러스터 간 통신 구현**: NAT 게이트웨이는 아웃바운드 인터넷 트래픽을 위한 것이며, 클러스터 간 통신에는 적합하지 않습니다.

</details>

### 5. Amazon EKS에서 파드 네트워킹 성능을 최적화하기 위한 가장 효과적인 방법은 무엇인가요?

A. 모든 파드에 호스트 네트워크 모드 사용\
B. Amazon VPC CNI의 프리픽스 위임 기능 활성화\
C. 모든 파드에 대해 NodePort 서비스 사용\
D. 클러스터 내 모든 통신에 AWS Global Accelerator 사용

<details>

<summary>정답 및 설명</summary>

**정답: B. Amazon VPC CNI의 프리픽스 위임 기능 활성화**

**설명:** Amazon EKS에서 파드 네트워킹 성능을 최적화하기 위한 가장 효과적인 방법은 Amazon VPC CNI의 프리픽스 위임 기능을 활성화하는 것입니다. 이 기능은 각 노드에 할당되는 보조 IP 주소의 수를 크게 늘리고, ENI(Elastic Network Interface) 생성 빈도를 줄여 네트워킹 성능과 확장성을 향상시킵니다.

**프리픽스 위임 작동 방식:**

1. **기본 VPC CNI vs 프리픽스 위임**:
   * 기본 VPC CNI: 각 ENI에 개별 보조 IP 주소 할당
   * 프리픽스 위임: 각 ENI에 /28 CIDR 블록(16개 IP) 할당
2.  **활성화 방법**:

    ```bash
    # 프리픽스 위임 활성화
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

    # 프리픽스 위임 확인
    kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
    ```
3.  **추가 구성 옵션**:

    ```bash
    # 프리픽스 할당 크기 설정 (기본값: /28)
    kubectl set env daemonset aws-node -n kube-system WARM_PREFIX_TARGET=1

    # 사용 가능한 IP 주소가 부족할 때 새 프리픽스를 요청하는 임계값
    kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=5
    ```

**프리픽스 위임의 이점:**

1. **향상된 확장성**:
   * 노드당 최대 파드 수 증가 (일반적으로 110개에서 250개 이상으로)
   * ENI 생성 빈도 감소로 인한 API 제한 감소
2. **빠른 파드 시작 시간**:
   * 새 파드에 IP 주소를 할당하는 데 필요한 API 호출 감소
   * 대규모 파드 배포 시 성능 향상
3. **IP 주소 효율성**:
   * 더 많은 파드를 동일한 수의 ENI로 지원
   * IP 주소 고갈 문제 완화

**인스턴스 유형별 최대 파드 수 비교:**

| 인스턴스 유형    | 기본 VPC CNI | 프리픽스 위임 활성화 |
| ---------- | ---------- | ----------- |
| t3.medium  | 17         | 110         |
| m5.large   | 29         | 110         |
| c5.xlarge  | 58         | 250         |
| r5.2xlarge | 58         | 250         |

**구성 예시 (ConfigMap):**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-prefix-delegation: "true"
  warm-prefix-target: "1"
  warm-ip-target: "5"
```

**고려 사항 및 제한 사항:**

1. **서브넷 크기**:
   * 프리픽스 위임을 사용하려면 충분히 큰 서브넷이 필요합니다
   * 최소 /24 CIDR 블록 권장
2. **보안 그룹 규칙**:
   * 프리픽스 위임을 사용하면 보안 그룹 규칙이 더 간단해질 수 있음
   * 개별 IP 대신 CIDR 블록을 참조할 수 있음
3. **호환성**:
   * 일부 레거시 EC2 인스턴스 유형은 프리픽스 위임을 지원하지 않음
   * Nitro 기반 인스턴스 권장
4. **IP 주소 관리**:
   * 프리픽스 위임은 IP 주소를 더 효율적으로 사용하지만, 여전히 적절한 CIDR 계획 필요

**모니터링 및 문제 해결:**

```bash
# 노드별 IP 주소 할당 확인
kubectl exec -n kube-system aws-node-xxxxx -- curl -s http://localhost:61679/v1/enis | jq

# 프리픽스 위임 상태 확인
kubectl logs -n kube-system aws-node-xxxxx | grep -i prefix
```

다른 옵션들의 문제점:

* **A. 모든 파드에 호스트 네트워크 모드 사용**: 호스트 네트워크 모드는 파드가 노드의 네트워크 네임스페이스를 공유하게 하여 포트 충돌 문제를 일으키고 네트워크 격리를 제거합니다.
* **C. 모든 파드에 대해 NodePort 서비스 사용**: NodePort는 서비스 노출 메커니즘이며, 파드 네트워킹 성능 최적화와는 관련이 없습니다.
* **D. 클러스터 내 모든 통신에 AWS Global Accelerator 사용**: AWS Global Accelerator는 글로벌 트래픽 관리를 위한 것이며, 클러스터 내부 통신 최적화에는 적합하지 않습니다.

</details>

## 단답형 문제

### 7. Amazon EKS에서 서비스 메시를 구현할 때 사이드카 프록시로 가장 일반적으로 사용되는 오픈 소스 프록시는 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** Envoy

**상세 설명:**

Amazon EKS에서 서비스 메시를 구현할 때 가장 일반적으로 사용되는 사이드카 프록시는 Envoy입니다. Envoy는 고성능 C++ 기반 프록시로, 대부분의 주요 서비스 메시 구현(Istio, AWS App Mesh, Consul Connect 등)에서 데이터 플레인 프록시로 사용됩니다.

**Envoy의 주요 특징:**

1. **고성능 아키텍처**:
   * C++로 작성되어 낮은 지연 시간과 높은 처리량 제공
   * 이벤트 기반, 비동기 네트워킹 모델
2. **풍부한 트래픽 관리 기능**:
   * 로드 밸런싱 (라운드 로빈, 가중치 기반, 최소 요청 등)
   * 서킷 브레이킹 및 이상치 감지
   * 재시도 및 타임아웃 정책
   * 트래픽 분할 및 미러링
3. **관찰 가능성**:
   * 상세한 메트릭 및 통계
   * 분산 추적 통합 (Zipkin, Jaeger 등)
   * 액세스 로깅
4. **보안 기능**:
   * TLS/mTLS 종료
   * 인증 및 권한 부여
   * 속도 제한

**서비스 메시에서의 Envoy 배포:**

1.  **사이드카 패턴**:

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: example-app
    spec:
      template:
        spec:
          containers:
          - name: app
            image: app:latest
          - name: envoy-proxy
            image: envoyproxy/envoy:v1.20.0
            ports:
            - containerPort: 15001
            volumeMounts:
            - name: envoy-config
              mountPath: /etc/envoy
          volumes:
          - name: envoy-config
            configMap:
              name: envoy-config
    ```
2. **자동 주입**:
   * Istio: `sidecar.istio.io/inject: "true"` 어노테이션
   * AWS App Mesh: `appmesh.k8s.aws/sidecarInjectorWebhook: enabled` 레이블

**Envoy 구성 예시:**

```yaml
static_resources:
  listeners:
  - address:
      socket_address:
        address: 0.0.0.0
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: service_backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: service_backend
    connect_timeout: 0.25s
    type: STRICT_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: service_backend
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: backend-service
                port_value: 80
```

**서비스 메시별 Envoy 통합:**

1. **Istio**:
   * Envoy를 사이드카 프록시로 사용
   * istiod가 Envoy 구성을 동적으로 관리
   * Pilot, Mixer, Citadel 등의 컴포넌트가 Envoy와 통합
2. **AWS App Mesh**:
   * AWS App Mesh 컨트롤러가 Envoy 사이드카 주입
   * AWS Cloud Map과 통합하여 서비스 디스커버리 제공
   * Envoy 관리 서비스(EMS)가 Envoy 구성 관리
3. **Consul Connect**:
   * Envoy를 데이터 플레인 프록시로 사용
   * Consul이 서비스 디스커버리 및 구성 관리 제공

**Envoy 모니터링 및 디버깅:**

```bash
# Envoy 관리 인터페이스 포트 포워딩
kubectl port-forward <pod-name> 19000:19000

# 구성 및 통계 확인
curl localhost:19000/config_dump
curl localhost:19000/stats

# 클러스터 상태 확인
curl localhost:19000/clusters
```

**성능 최적화 고려 사항:**

* 리소스 할당: Envoy에 충분한 CPU 및 메모리 할당
* 연결 풀링: 업스트림 연결 풀링 구성으로 성능 향상
* 버퍼 크기: 적절한 버퍼 크기 설정으로 메모리 사용량 최적화
* 필터 체인: 필요한 필터만 활성화하여 오버헤드 최소화

Envoy는 현대적인 서비스 메시 아키텍처의 핵심 구성 요소로, 마이크로서비스 간의 통신을 안전하고 신뢰할 수 있으며 관찰 가능하게 만드는 데 중요한 역할을 합니다.

</details>

### 8. Amazon EKS에서 클러스터 내부 DNS 확인을 담당하는 Kubernetes 애드온의 이름은 무엇인가요?

<details>

<summary>정답 및 설명</summary>

**정답:** CoreDNS

**상세 설명:**

Amazon EKS에서 클러스터 내부 DNS 확인을 담당하는 Kubernetes 애드온은 CoreDNS입니다. CoreDNS는 Kubernetes 클러스터 내에서 서비스 디스커버리를 위한 DNS 서버 역할을 하며, 파드와 서비스의 이름 확인을 처리합니다.

**CoreDNS의 주요 기능:**

1. **서비스 디스커버리**:
   * `<service-name>.<namespace>.svc.cluster.local` 형식의 DNS 이름 확인
   * 파드 IP 주소에 대한 역방향 DNS 조회 지원
2. **플러그인 아키텍처**:
   * 다양한 플러그인을 통해 기능 확장
   * 캐싱, 메트릭, 로깅, 오류 처리 등
3. **구성 유연성**:
   * Corefile을 통한 선언적 구성
   * 동적 리로드 지원

**EKS에서의 CoreDNS 배포:**

1. **기본 배포 구성**:
   * EKS 클러스터 생성 시 자동으로 배포됨
   * kube-system 네임스페이스에서 실행
   * 일반적으로 2개 이상의 복제본으로 배포
2.  **확인 방법**:

    ```bash
    # CoreDNS 파드 확인
    kubectl get pods -n kube-system -l k8s-app=kube-dns

    # CoreDNS 버전 확인
    kubectl describe deployment coredns -n kube-system | grep Image
    ```

**CoreDNS 구성 (Corefile):**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

**주요 플러그인 설명:**

1. **errors**: 오류를 로그에 기록
2. **health**: 상태 확인 엔드포인트 제공
3. **ready**: 준비 상태 확인 엔드포인트 제공
4. **kubernetes**: Kubernetes 서비스 디스커버리 처리
5. **prometheus**: Prometheus 메트릭 노출
6. **forward**: 외부 DNS 쿼리를 상위 DNS 서버로 전달
7. **cache**: DNS 응답 캐싱
8. **loop**: DNS 루프 감지 및 방지
9. **reload**: Corefile 변경 시 자동 리로드
10. **loadbalance**: 다중 A/AAAA 레코드에 대한 로드 밸런싱

**사용자 지정 구성 예시:**

1.  **외부 도메인에 대한 특정 DNS 서버 사용**:

    ```
    example.com {
        forward . 10.0.0.1
    }
    ```
2.  **스텁 도메인 구성**:

    ```
    internal.corp {
        file /etc/coredns/internal.db
    }
    ```
3.  **조건부 전달**:

    ```
    . {
        forward . 8.8.8.8 8.8.4.4 {
            policy sequential
        }
    }
    ```

**성능 최적화 및 확장:**

1.  **자동 스케일링**:

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: coredns
      namespace: kube-system
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: coredns
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 60
    ```
2.  **리소스 할당 최적화**:

    ```yaml
    resources:
      limits:
        memory: 170Mi
      requests:
        cpu: 100m
        memory: 70Mi
    ```
3.  **캐시 튜닝**:

    ```
    cache {
        success 10000
        denial 1000
        prefetch 10 10% 2m
    }
    ```

**문제 해결:**

1.  **DNS 해결 테스트**:

    ```bash
    # 테스트 파드 생성
    kubectl run dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 -- sleep 3600

    # DNS 조회 테스트
    kubectl exec -it dnsutils -- nslookup kubernetes.default
    ```
2.  **CoreDNS 로그 확인**:

    ```bash
    kubectl logs -n kube-system -l k8s-app=kube-dns
    ```
3.  **DNS 정책 확인**:

    ```bash
    kubectl get pods <pod-name> -o jsonpath='{.spec.dnsPolicy}'
    ```

CoreDNS는 EKS 클러스터의 중요한 구성 요소로, 서비스 디스커버리를 통해 마이크로서비스 아키텍처의 핵심 기능을 제공합니다. 적절한 구성과 모니터링을 통해 안정적인 DNS 서비스를 보장하는 것이 중요합니다.

</details>

## 실습 문제

### 10. Amazon EKS 클러스터에서 서비스 메시(예: AWS App Mesh)를 구현하여 마이크로서비스 간 통신을 보호하고 모니터링하는 방법을 설명하세요. 구현 단계, 주요 구성 요소 및 모니터링 방법을 포함하세요.

<details>

<summary>정답 및 설명</summary>

**정답:**

Amazon EKS 클러스터에서 AWS App Mesh를 구현하여 마이크로서비스 간 통신을 보호하고 모니터링하는 방법은 다음과 같습니다:

### 1. AWS App Mesh 구현 단계

#### 1.1. 사전 요구 사항 설정

```bash
# 필요한 IAM 권한 설정
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=appmesh-system \
  --name=appmesh-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AWSCloudMapFullAccess,arn:aws:iam::aws:policy/AWSAppMeshFullAccess \
  --override-existing-serviceaccounts \
  --approve

# Helm 리포지토리 추가
helm repo add eks https://aws.github.io/eks-charts
helm repo update
```

#### 1.2. App Mesh 컨트롤러 설치

```bash
# App Mesh 컨트롤러 네임스페이스 생성
kubectl create ns appmesh-system

# App Mesh 컨트롤러 설치
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --set region=${AWS_REGION} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=appmesh-controller
```

#### 1.3. 메시 생성

```yaml
# mesh.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
```

```bash
kubectl apply -f mesh.yaml
```

#### 1.4. 애플리케이션 네임스페이스 설정

```bash
# 애플리케이션 네임스페이스 생성 및 레이블 지정
kubectl create ns app-namespace
kubectl label namespace app-namespace mesh=my-mesh
kubectl label namespace app-namespace appmesh.k8s.aws/sidecarInjectorWebhook=enabled
```

#### 1.5. 가상 노드 및 서비스 정의

```yaml
# virtual-node.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      healthCheck:
        protocol: http
        path: "/health"
        port: 8080
        healthyThreshold: 2
        unhealthyThreshold: 2
        timeoutMillis: 2000
        intervalMillis: 5000
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

```yaml
# virtual-service.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: service-a
  namespace: app-namespace
spec:
  awsName: service-a.app-namespace.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: service-a-router
```

```yaml
# virtual-router.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
```

#### 1.6. 애플리케이션 배포

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-a
  namespace: app-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: service-a
  template:
    metadata:
      labels:
        app: service-a
    spec:
      containers:
      - name: service-a
        image: service-a:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
```

### 2. mTLS 구성으로 통신 보호

#### 2.1. AWS Certificate Manager Private CA 설정

```bash
# 프라이빗 CA 생성
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration file://ca-config.json \
  --certificate-authority-type "ROOT" \
  --idempotency-token 1234567890 \
  --tags Key=Name,Value=AppMeshCA

# CA ARN 저장
export CA_ARN=$(aws acm-pca list-certificate-authorities --query 'CertificateAuthorities[?Status==`ACTIVE`].Arn' --output text)
```

#### 2.2. TLS 구성 추가

```yaml
# virtual-node-with-tls.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      tls:
        mode: STRICT  # mTLS 활성화
        certificate:
          acm:
            certificateArn: arn:aws:acm:region:account-id:certificate/certificate-id
  backends:
    - virtualService:
        virtualServiceRef:
          name: service-b
        clientPolicy:
          tls:
            enforce: true
            ports:
              - 8080
            validation:
              trust:
                acm:
                  certificateAuthorityArns:
                    - ${CA_ARN}
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
```

### 3. 모니터링 및 관찰 가능성 설정

#### 3.1. AWS X-Ray 통합

```yaml
# mesh-with-xray.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

```bash
# X-Ray 데몬 배포
kubectl apply -f https://github.com/aws/aws-app-mesh-controller-for-k8s/raw/master/config/samples/xray-daemon.yaml
```

#### 3.2. Amazon CloudWatch 통합

```yaml
# envoy-config.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  namespaceSelector:
    matchLabels:
      mesh: my-mesh
  egressFilter:
    type: ALLOW_ALL
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  logging:
    accessLog:
      file:
        path: /dev/stdout
        format:
          json:
            - key: "source"
              value: "%DOWNSTREAM_REMOTE_ADDRESS%"
            - key: "destination"
              value: "%UPSTREAM_REMOTE_ADDRESS%"
            - key: "protocol"
              value: "%PROTOCOL%"
```

```bash
# CloudWatch 에이전트 배포
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-serviceaccount.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-configmap.yaml

kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-daemonset.yaml
```

#### 3.3. Prometheus 및 Grafana 설정

```bash
# Prometheus 네임스페이스 생성
kubectl create namespace prometheus

# Prometheus 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus \
  --set alertmanager.persistentVolume.storageClass="gp2" \
  --set server.persistentVolume.storageClass="gp2"

# Grafana 설치
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install grafana grafana/grafana \
  --namespace prometheus \
  --set persistence.storageClassName="gp2" \
  --set persistence.enabled=true \
  --set adminPassword='EKS!sAWSome' \
  --values grafana.yaml \
  --set service.type=LoadBalancer
```

```yaml
# grafana.yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server.prometheus.svc.cluster.local
      access: proxy
      isDefault: true
```

### 4. 트래픽 관리 및 고급 기능 구성

#### 4.1. 카나리 배포 구성

```yaml
# virtual-router-canary.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
    - portMapping:
        port: 8080
        protocol: http
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a-v1
              weight: 90
            - virtualNodeRef:
                name: service-a-v2
              weight: 10
```

#### 4.2. 서킷 브레이커 구성

```yaml
# virtual-node-circuit-breaker.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  # ... 기존 구성 ...
  listeners:
    - portMapping:
        port: 8080
        protocol: http
      outlierDetection:
        baseEjectionDuration:
          unit: s
          value: 30
        interval:
          unit: s
          value: 10
        maxEjectionPercent: 50
        maxServerErrors: 5
```

#### 4.3. 재시도 정책 구성

```yaml
# virtual-router-retry.yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  # ... 기존 구성 ...
  routes:
    - name: service-a-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: service-a
              weight: 1
        retryPolicy:
          maxRetries: 3
          perRetryTimeout:
            unit: ms
            value: 2000
          httpRetryEvents:
            - server-error
            - gateway-error
            - client-error
            - stream-error
```

### 5. 모니터링 및 문제 해결

#### 5.1. Envoy 프록시 로그 확인

```bash
# 특정 파드의 Envoy 사이드카 로그 확인
kubectl logs <pod-name> -c envoy -n app-namespace

# 모든 Envoy 로그 스트리밍
kubectl logs -f -l app=service-a -c envoy -n app-namespace
```

#### 5.2. Envoy 관리 인터페이스 접근

```bash
# 포트 포워딩 설정
kubectl port-forward <pod-name> -n app-namespace 9901:9901

# 브라우저에서 접근
# http://localhost:9901/
```

#### 5.3. X-Ray 추적 확인

AWS Management Console에서 X-Ray 서비스로 이동하여 서비스 맵과 트레이스를 확인합니다.

#### 5.4. CloudWatch 대시보드 생성

```bash
# CloudWatch 대시보드 생성을 위한 JSON 파일 준비
cat > appmesh-dashboard.json << EOF
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "RequestCount", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Sum" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Request Count"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/AppMesh", "Latency", "MeshName", "my-mesh", "VirtualNodeName", "service-a", { "stat": "Average" } ]
        ],
        "period": 60,
        "region": "${AWS_REGION}",
        "title": "Latency"
      }
    }
  ]
}
EOF

# AWS CLI를 사용하여 대시보드 생성
aws cloudwatch put-dashboard --dashboard-name AppMeshDashboard --dashboard-body file://appmesh-dashboard.json
```

### 6. 모범 사례 및 고려 사항

#### 6.1. 리소스 요구 사항

* 각 파드에 Envoy 사이드카가 추가되므로 노드 리소스 계획 필요
* 일반적으로 각 Envoy 프록시에 100-200m CPU 및 128-256Mi 메모리 할당

#### 6.2. 점진적 구현 전략

1. **단계적 접근**:
   * 비즈니스에 중요하지 않은 서비스부터 시작
   * 트래픽 미러링으로 영향 평가
   * 성공적인 검증 후 점진적으로 확장
2. **mTLS 구현**:
   * PERMISSIVE 모드로 시작
   * 모든 서비스가 호환되는지 확인
   * STRICT 모드로 전환

#### 6.3. 성능 최적화

* Envoy 리소스 제한 조정
* 적절한 상태 확인 간격 설정
* 불필요한 로깅 및 추적 최소화

#### 6.4. 보안 강화

* 최소 권한 IAM 정책 사용
* 정기적인 인증서 순환
* 네트워크 정책과 함께 심층 방어 구현

AWS App Mesh는 EKS 클러스터에서 마이크로서비스 간 통신을 보호하고 모니터링하기 위한 강력한 서비스 메시 솔루션을 제공합니다. 적절한 구성과 모니터링을 통해 애플리케이션의 안정성, 보안 및 관찰 가능성을 크게 향상시킬 수 있습니다.

</details>
