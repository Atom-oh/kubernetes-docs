# EKS 네트워킹 퀴즈 - Part 3

> **마지막 업데이트**: 2026년 9월 11일

퀴즈는 [Part 3 문제 해결 개념](../../eks/03-eks-networking-part3.md), 프라이빗 연결, 멀티클러스터 설계와 메시 운영을 다룹니다. 현재 예제는 EKS Kubernetes 1.36, VPC CNI 1.23.0을 기준으로 하며 과거 App Mesh 구성은 별도로 표시합니다. 리소스 생성 예제에는 검토한 IAM·네트워크·소유권 전제가 필요합니다. 이 감사는 로컬 검증이며 EKS 배포 검증이 아닙니다.

### 1. 사이드카 기반 서비스 메시에 애플리케이션을 등록하면 무엇이 바뀌나요?

- A. All Pod traffic leaves the VPC
- B. A proxy handles enrolled service traffic
- C. Service discovery is removed
- D. All traffic requires Transit Gateway

<details>
<summary>정답 보기</summary>

**정답: B. 주입된 프록시가 등록된 서비스 트래픽을 처리합니다.**

사이드카 모드에서는 애플리케이션과 프록시가 하나의 Pod 네트워크 네임스페이스와 IP를 공유합니다. 프록시는 데이터 플레인이며 컨트롤 플레인은 라우팅·보안·신원 구성을 배포합니다. NetworkPolicy, VPC 라우팅과 Service 디스커버리는 계속 중요합니다. 논리적 경로는 다음과 같습니다:
```text
Application → client proxy → Pod network → destination proxy → application
```
가로채는 범위는 등록 여부·제외 포트·프로토콜·모드에 따라 달라지며 모든 패킷이 Service VIP를 통과해야 하는 것은 아닙니다. Ambient 메시는 노드 프록시·waypoint 방식이므로 이 문제는 사이드카 모드를 명시합니다. 메시는 주 서비스 구현을 크게 바꾸지 않고 재시도·라우팅·mTLS·텔레메트리를 제공할 수 있지만 애플리케이션의 추적 컨텍스트 전달·프로토콜 호환성·타임아웃 처리는 여전히 필요할 수 있습니다.

이전 Envoy 이미지를 임의 추가하거나 injector를 중복 사용하지 말고 선택한 메시가 지원하는 injector/revision을 사용합니다. AWS App Mesh는 과거 사례이며 2026년 9월 30일 지원·접근이 종료됩니다. 기존 배포는 이전 계획이 필요하고 새 설치의 기본 예제가 아닙니다. 유지 관리되는 구현 절차는 [Istio 설치](../../service-mesh/istio/01-installation.md)를 참고하세요.

</details>

### 2. VPC 엔드포인트는 프라이빗 EKS 워크로드에 무엇을 제공하나요?

- A. Unlimited bandwidth
- B. Private connectivity to supported services
- C. An automatic 50% discount
- D. Automatic AWS authentication

<details>
<summary>정답 보기</summary>

**정답: B. 해당 요청에 인터넷/NAT 없이 지원 AWS 서비스로 연결하는 프라이빗 경로.**

인터페이스 엔드포인트는 선택한 서브넷/AZ에 ENI를 만들며 일반적으로 시간·데이터 처리 요금이 발생합니다. S3/DynamoDB 게이트웨이 엔드포인트는 라우팅 테이블 항목을 추가하고 엔드포인트 자체 요금은 없지만 서비스·저장·요청 요금은 별개입니다. 엔드포인트는 IAM 권한이나 비용·지연 개선·규정 준수를 자동 보장하지 않습니다.

프라이빗 ECR 이미지 pull에는 `ecr.api`, `ecr.dkr`, S3 레이어 다운로드 경로와 엔드포인트 SG HTTPS 규칙, DNS 지원·private DNS, 라우팅·엔드포인트/IAM 정책을 계획합니다. 다른 서비스는 실제 부하에 따라 IRSA용 regional STS, Pod Identity용 `eks-auth`, CNI의 EC2 API, Logs·모니터링 등이 필요합니다. EKS 서비스 엔드포인트가 프라이빗 Kubernetes API 엔드포인트를 대체하지는 않습니다. ECR Public, 최초 pull-through-cache 요청이나 Windows foreign layer는 추가 외부 연결 또는 준비한 이미지 미러가 필요할 수 있습니다.

다음 매개변수화 CloudFormation 예제는 **기존** VPC에 엔드포인트 세 개만 추가합니다. 생성 전 기존 엔드포인트·private DNS 소유권을 검토합니다. 서비스별 엔드포인트 정책은 보안 소유자가 정의해야 하며 기본 접근 설정이 IAM을 우회하지 않습니다. 완성된 격리 클러스터 배포로 가정하지 말고 변경 세트를 준비하세요:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECR API/DKR and S3 endpoints in an existing VPC; not a complete private EKS stack
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Existing subnets in distinct Availability Zones
  PrivateRouteTableIds:
    Type: CommaDelimitedList
    Description: Route tables used by the image-pulling workloads
  EndpointSecurityGroupId:
    Type: AWS::EC2::SecurityGroup::Id
    Description: Existing same-VPC SG permitting HTTPS from the intended nodes/Pods
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VpcId
      RouteTableIds: !Ref PrivateRouteTableIds
      VpcEndpointType: Gateway
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```
새 노드 그룹이 필요할 때 `eksctl create nodegroup`은 **`--subnet-ids`**를 사용하며 이전 `--vpc-private-subnets`는 이 명령의 올바른 플래그가 아닙니다. 아래는 프라이빗 API·서비스 경로가 준비된 후 과금되는 관리형 노드를 생성합니다. eksctl이 의도한 소유자이고 기존 `private-ng`가 없을 때만 사용합니다. 인스턴스 크기는 용량 권장값이 아닌 예시입니다.
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${PRIVATE_SUBNET_A:?Set an existing private subnet}"
: "${PRIVATE_SUBNET_B:?Set another private subnet}"
eksctl create nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name private-ng --managed --version auto --node-type m5.large \
  --nodes 2 --nodes-min 2 --nodes-max 3 --node-private-networking \
  --subnet-ids "$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B"
```

</details>

### 3. 겹치지 않는 여러 VPC 사이에 허브 라우팅을 제공하는 선택지는 무엇인가요?

- A. A public load balancer is mandatory
- B. Transit Gateway with complete routing
- C. Every cluster must share a VPC
- D. A NAT gateway provides Kubernetes discovery

<details>
<summary>정답 보기</summary>

**정답: B. AWS Transit Gateway**

Transit Gateway는 여러 VPC를 연결하는 설계 중 하나이며 모든 멀티클러스터의 최적 구조는 아닙니다. 신뢰 경계·규모·DNS·주소 중복·비용에 따라 VPC peering, 공유 VPC, PrivateLink 서비스 노출, VPC Lattice와 메시 게이트웨이를 비교합니다. NAT도 프라이빗 연결 용도가 있지만 서비스 디스커버리를 제공하지는 않습니다.

TGW 설계에는 라우팅할 Pod/VPC CIDR의 비중복, 참여 AZ별 연결, TGW 라우팅 테이블 연결·전파, 워크로드 서브넷 및 반환 경로가 필요합니다. TGW 경로 하나만으로 충분하지 않습니다. Kubernetes ClusterIP는 가상 서비스 주소이며 원격에서 자동 라우팅되지 않습니다. 명시적인 디스커버리 설계로 접근 가능한 Pod 또는 게이트웨이·로드 밸런서 주소를 게시하세요. 변경 전에 실제 경로 상태를 읽습니다:
```bash
set -euo pipefail
: "${AWS_REGION:?Set the transit gateway Region}"
: "${TGW_ROUTE_TABLE_ID:?Set the intended TGW route table}"
: "${VPC_ROUTE_TABLE_ID:?Set a workload-subnet route table}"
aws ec2 search-transit-gateway-routes --region "$AWS_REGION" \
  --transit-gateway-route-table-id "$TGW_ROUTE_TABLE_ID" \
  --filters Name=state,Values=active
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$VPC_ROUTE_TABLE_ID"
```
TGW 자체에 방화벽 SG를 붙이는 구조는 아닙니다. 필요에 따라 엔드포인트·노드·Pod SG, NACL, NetworkPolicy와 검사 경로를 사용합니다. VPC 간 SG 참조는 문서화된 연결·리전 조건에서 지원되는 TGW 기능이지만 TGW에 SG를 붙이거나 라우팅을 대신하는 것은 아닙니다.

Cloud Map에는 네임스페이스 준비, Service 생성, 등록과 상태·등록 해제 관리가 필요합니다. TGW가 프라이빗 호스팅 존 DNS를 자동 공유하지는 않습니다. 승인된 프라이빗 존 연결 또는 Route 53 Resolver 엔드포인트·규칙을 사용합니다. 다른 VPC의 `base+2` 리졸버를 해당 클러스터 CoreDNS처럼 지정하지 마세요. 아래 **Corefile 조각**은 내보낸 `cluster2.example.internal` 레코드를 해석하는 실제 접근 가능 인바운드 리졸버 두 개를 전제로 합니다. DNS 소유 관리 도구로 병합하고 클러스터 로컬 존은 보존합니다:
```text
cluster2.example.internal:53 {
    errors
    cache 30
    forward . 10.1.20.10 10.1.21.10
}
```
아래 ingress 정책은 NAT·프록시 이후 실제 보이는 소스 주소 기준으로 원격 CIDR의 API 포트 하나를 허용합니다. 다른 일치 정책이 허용을 넓힐 수 있습니다. Egress·DNS 요구는 별도 설계하며 클러스터 간 네임스페이스·Pod 레이블이 자동 공유되지는 않습니다.
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remote-api-ingress
  namespace: multicluster-demo
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.1.0.0/16
    ports:
    - protocol: TCP
      port: 8080
```
Istio multi-primary와 primary-remote는 다른 컨트롤 플레인 배치입니다. 지원 모델을 선택하고 east-west 게이트웨이, 신원 신뢰와 대상 상태를 검증합니다. 기존 App Mesh 멀티클러스터 사용은 2026년 9월 종료를 반영해야 합니다. 실제 경로의 시간·처리·AZ 간 요금을 비교하세요. 같은 VPC나 퍼블릭 로드 밸런서 설계도 본질적으로 틀린 것은 아니며 별도 보안·비용 분석이 필요합니다.

</details>

### 4. IPv4 주소를 /28 블록으로 할당하여 주소 슬롯 밀도를 높이는 VPC CNI 기능은 무엇인가요?

- A. hostNetwork for all Pods
- B. Prefix delegation
- C. NodePort for every Service
- D. Global Accelerator for Pod-to-Pod traffic

<details>
<summary>정답 보기</summary>

**정답: B. Prefix delegation**

위임된 IPv4 /28은 ENI 주소 슬롯 하나로 Pod 주소 16개를 제공합니다. 할당 API 작업과 Pod 시작·밀도에 도움이 될 수 있지만 보편적인 패킷 처리량 개선이나 전체 서브넷 고갈 해결책은 아닙니다. IPv6는 prefix 크기가 다릅니다. 지원 Nitro 하드웨어, 연속된 여유 prefix, kubelet maxPods와 자원 용량이 밀도를 제한합니다.

스키마·소유권 검토 후 아래 JSON 조각을 해당 EKS add-on 구성에 병합하거나 대응하는 Helm `env` 값을 사용합니다. 이전 `amazon-vpc-cni` ConfigMap의 소문자 키는 Linux CNI를 구성하지 않습니다:
```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
`WARM_PREFIX_TARGET=1`은 prefix 크기가 아니라 여유 prefix 하나를 뜻합니다. 양수 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`이 warm-prefix 목표보다 우선하며 큰 warm pool은 서브넷 공간을 더 예약합니다. 노드 그룹 전환과 maxPods를 함께 계획하세요. DaemonSet 토글만으로 기존 노드가 임의의 밀도를 지원하지 않습니다.

| 인스턴스 | 일반 보조 IPv4 maxPods 계산식 | 해당 소형 인스턴스의 prefix 모드 예시 상한 |
|---|---:|---:|
| t3.medium | 17 | 110 |
| m5.large | 29 | 110 |
| c5.xlarge | 58 | 110 |
| r5.2xlarge | 58 | 110 |

이는 벤치마크나 모든 Pod 수용 보장이 아닌 구성 제한입니다. 이전 c5.xlarge/r5.2xlarge의 250은 틀렸으며 EKS 권장 상한은 vCPU 30개 미만 110, 30개 이상 250입니다. Pod SG의 branch 인터페이스 제한은 별도입니다. Prefix 할당에는 연속된 /28이 필요하며 보편적인 최소 /24 서브넷 조건이나 SG 정책 자동 단순화는 아닙니다.
```bash
set -euo pipefail
: "${AWS_REGION:?Set the node Region}"
kubectl get nodes -o 'custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,PODS:.status.allocatable.pods'
kubectl -n kube-system get daemonset aws-node -o yaml
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
aws ec2 describe-instance-types --region "$AWS_REGION" \
  --instance-types t3.medium m5.large c5.xlarge r5.2xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,vCPUs:VCpuInfo.DefaultVCpus,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4Slots:NetworkInfo.Ipv4AddressesPerInterface}'
```

</details>

### 5. Istio 사이드카 모드의 프록시는 무엇이며 어떻게 진단하나요?

<details>
<summary>정답 보기</summary>

**정답: Envoy**

Istio 사이드카 모드는 Envoy를 사용하고 istiod가 디스커버리·라우팅·인증서 구성을 제공합니다. 이전 Pilot/Citadel 기능은 istiod로 통합되었으며 Mixer는 현재 필수 구성 요소가 아닙니다. 다른 메시는 다른 프록시를 사용할 수 있고 Envoy가 Kubernetes나 모든 메시의 필수 요건은 아닙니다.

Envoy는 구성에 따라 연결 풀, HTTP/TCP 라우팅, 재시도, outlier detection, TLS와 텔레메트리를 제공합니다. 컨테이너 추가만으로 투명한 트래픽 가로채기, 워크로드 신원, xDS나 mTLS가 설정되지는 않습니다. 실제 메시는 지원 injector와 proxy 빌드를 사용합니다. 이전 Envoy1.20 이미지와 불완전한 Deployment는 현재 설치 예제로 적합하지 않았습니다.

아래 **독립 reverse-proxy bootstrap**은 기존 listener/route/cluster 개념을 설명하며 upstream Envoy1.39.1로 로컬 검증했습니다. 같은 네트워크 네임스페이스의 `127.0.0.1:8080`에 별도 HTTP 애플리케이션이 있어야 합니다. 프록시와 관리 리스너는 loopback에만 바인딩하며 프로덕션이나 Kubernetes 메시 배포가 아닙니다:
```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
static_resources:
  listeners:
  - name: local-proxy
    address:
      socket_address:
        address: 127.0.0.1
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: demo_http
          route_config:
            name: local-route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: /
                route:
                  cluster: local-app
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: local-app
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local-app
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
```
`envoy-config.yaml`로 저장하고 일치하는 upstream 바이너리로 검증합니다. 구문 검증이 백엔드 연결이나 워크로드 신원 동작을 증명하지는 않습니다.
```bash
envoy --mode validate --concurrency 1 --config-path envoy-config.yaml
```
기존 Kubernetes 메시 프록시는 19000을 가정하지 말고 실제 관리 포트·컨테이너 이름을 확인합니다. App Mesh 기본 관리 포트는9901, Istio는 보통15000이며 배포 설정은 다를 수 있습니다. 한 터미널에서 다음 port-forward를 실행합니다:
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the existing mesh workload namespace}"
: "${MESH_POD:?Set the existing proxy Pod}"
: "${ENVOY_ADMIN_PORT:?Use the admin port actually configured by that mesh}"
kubectl -n "$MESH_NAMESPACE" port-forward --address 127.0.0.1 \
  "pod/$MESH_POD" "19000:$ENVOY_ADMIN_PORT"
```
다른 터미널에서 시간 제한이 있는 읽기 전용 쿼리를 실행합니다. Config dump는 내부 토폴로지나 민감한 구성을 포함할 수 있으므로 게시하거나 관리 리스너를 외부에 노출하지 않습니다.
```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/config_dump
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/stats
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/clusters
```
업스트림 상태, 연결 풀 제한, 재시도, 필터 비용, 메모리와 요청 지연을 함께 봅니다. 측정한 부하에 맞춰 조정하며 오버헤드를 줄이려고 보안 필터만 제거하면 보안 모델이 바뀝니다.

</details>

### 6. 일반 EKS 노드의 DNS는 무엇이 제공하며 어떻게 구성하나요?

<details>
<summary>정답 보기</summary>

**정답: CoreDNS (실제 DNS/add-on 소유자부터 확인).**

CoreDNS는 일반적인 EKS 컴퓨팅의 DNS add-on입니다. 생성 방식·소유권은 다를 수 있으며 EKS Auto Mode에는 관리형 클러스터 DNS가 포함되어 기존 CoreDNS Deployment가 반드시 필요하지 않습니다. 아래 일반 add-on 점검 전에 컴퓨팅·DNS 소유자를 확인합니다. ResourceNotFound가 나오면 소유권을 조사하며 자동 재설치하지 않습니다:
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns
kubectl -n kube-system get deployment coredns -o yaml
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```
Service DNS는 보통 `<service>.<namespace>.svc.<cluster-domain>`이며 `cluster.local`은 흔한 값이지 불변값은 아닙니다. Headless/ExternalName은 일반 ClusterIP 레코드와 다릅니다. 임의 Pod IP마다 유용한 역방향 DNS 레코드가 있다고 가정하지 않습니다.

아래는 설명용 **Corefile**이며 ConfigMap을 무조건 덮어쓰는 예제가 아닙니다. 관리형 구성, 실제 클러스터 도메인·프로브·DNS Service를 보존합니다. `pods insecure`는 Pod 존재를 검증하지 않는 구문 기반 Pod-IP DNS 응답을 허용하므로 의도한 Kubernetes 플러그인 모드를 선택합니다.
```text
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
`errors`는 오류, `health`와 `ready`는 서로 다른 프로브, `kubernetes`는 클러스터 레코드, `forward`는 외부 도메인, `prometheus`는 메트릭을 담당합니다. `cache`·`reload`·`loadbalance`는 캐시·설정 재로드·레코드 순서에 영향을 줍니다. `loop`는 시작 시 일부 단순 전달 루프를 탐지하며 모든 동적 루프를 영구 차단하는 기능은 아닙니다. `loadbalance`는 DNS 응답 순서를 바꾸며 Service 패킷을 전달하지 않습니다.

조건부 전달에는 승인한 접근 가능 DNS 서버와 UDP/TCP53 경로가 필요합니다. VPC 서브넷의10.0.0.1 같은 첫 주소를 기업 DNS 예제로 사용하지 마세요. `file` 플러그인은 유효한 SOA·레코드를 가진 권한 있는 존 파일을 생성·마운트·관리해야 하며 stub-domain forward의 대체가 아닙니다. 퍼블릭 리졸버는 의도한 외부 경로·정보 전달 정책이 필요하고 프라이빗 존을 자동 해석하지 않습니다.

아래 캐시 조각은 `prefetch AMOUNT DURATION PERCENTAGE` 순서로 수정했습니다. cache 지시문을 중복 추가하지 말고 기존 것을 교체합니다:
```text
cache 30 {
    success 10000
    denial 1024
    prefetch 10 2m 10%
}
```
Upstream CoreDNS1.14.7은 `denial1000`을 허용하되1024로 보정하고 `success10000`은9984로 보정합니다. 명시적인1024는 기존 유효 denial 용량을 유지합니다. 이 값은 구현 동작이며 실측 DNS 용량 권장값이 아닙니다.

**스케일링 소유자 하나**를 선택합니다. 정확한 add-on 버전·스키마가 지원하면 EKS 관리형 CoreDNS 자동 확장을 사용하거나 별도 HPA/cluster-proportional autoscaler를 사용합니다. 아래 HPA는 metrics-server·CPU requests가 있는 의도적으로 자체 관리하는 Deployment용이며 다른 복제본 관리자와 함께 적용하지 않습니다.
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
기존 자원 예시(CPU 요청100m, 메모리 요청70Mi·제한170Mi)는 부하 검증값이 아닙니다. 쿼리율·오류·캐시 hit/miss·메모리/OOM·응답 지연을 보고 산정합니다. DNS 도구가 있는 기존 승인 진단 워크로드에서 dnsPolicy/dnsConfig/resolv.conf, kube-dns EndpointSlice와 정책·SG·업스트림 경로를 확인하세요. 클러스터 Service와 승인된 외부·프라이빗 이름을 나눠 테스트합니다. 이전 dnsutils 이미지나 소유자 없는 bare Pod 생성은 DNS 진단의 필수 조건이 아닙니다.

</details>

### 7. 기존 App Mesh 배포를 어떻게 보호·관찰하고 이전해야 하나요?

<details>
<summary>정답 보기</summary>

**정답: 기존 관계·신원·텔레메트리를 검토하고 지원되는 대체 구성을 검증합니다.**

**기존 운영·이전 실습:** AWS App Mesh의 지원과 리소스 접근은 **2026년9월30일** 종료됩니다. 이전 절차로 새 메시·Private CA·퍼블릭 Grafana를 생성하지 마세요. 기존 배포는 관계를 파악하고 종료 전에 이전합니다. ECS Service Connect는 EKS 설치 대상이 아니므로 실제 사용 기능에 맞는 지원 Kubernetes 메시·게이트웨이 구조를 평가합니다.
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the namespace of the existing mesh workloads}"
kubectl get meshes.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get virtualnodes.appmesh.k8s.aws,virtualservices.appmesh.k8s.aws,virtualrouters.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get deployments,services
```
**1. 기존 관계를 정리합니다.** Mesh의 namespace selector는 참여 네임스페이스를, VirtualNode의 pod selector는 워크로드·리스너·디스커버리를 선택합니다. VirtualService는 VirtualNode 또는 VirtualRouter를 가리키며 router의 경로가 가중치 대상 노드를 선택합니다. 백엔드 참조, 엔드포인트 DNS, 헬스체크, IAM/IRSA, injector와 실제 리스닝 포트를 확인합니다. 이전 `service-a:latest` 자리표시자와 누락된 service-b 워크로드는 동작하는 애플리케이션이 아니었습니다. 진단을 위해 기존 ServiceAccount를 덮어쓰거나 full-access 정책을 붙이지 마세요.

**2. TLS와 상호 인증을 구분합니다.** 서버 인증서만 가진 STRICT 리스너는 암호화 연결을 요구하지만 그 자체로 클라이언트를 인증하지는 않습니다. App Mesh mTLS에는 클라이언트 인증서와 서버 측 클라이언트 신뢰, 클라이언트 측 서버 신뢰·SAN 검사가 필요합니다. 클라이언트 인증서와 리스너 검증 신뢰는 ACM 클라이언트 인증서 참조가 아닌 파일 또는 SDS를 사용합니다. 프록시 간 mTLS가 워크로드 내부 app-to-Envoy 구간도 자동 암호화하지는 않습니다.

다음은 새 설치가 아닌 **기존 구성 검토 예제**입니다. 파일이 프록시에 안전하게 마운트되어 있고 인증서의 신원·용도가 맞으며 service-b와 의도한 Mesh에 속한 네임스페이스가 있어야 합니다. 신뢰 설계에 따라 승인된 클라이언트 SAN도 제한합니다. CA만 신뢰하면 그 CA가 발급한 적격 클라이언트 인증서를 허용합니다:
```yaml
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
      mode: STRICT
      certificate:
        file:
          certificateChain: /certs/server.crt
          privateKey: /certs/server.key
      validation:
        trust:
          file:
            certificateChain: /certs/trusted-client-ca.pem
    outlierDetection:
      baseEjectionDuration:
        unit: s
        value: 30
      interval:
        unit: s
        value: 10
      maxEjectionPercent: 50
      maxServerErrors: 5
  backends:
  - virtualService:
      virtualServiceRef:
        name: service-b
      clientPolicy:
        tls:
          enforce: true
          ports: [8080]
          certificate:
            file:
              certificateChain: /certs/client.crt
              privateKey: /certs/client.key
          validation:
            trust:
              file:
                certificateChain: /certs/trusted-server-ca.pem
            subjectAlternativeNames:
              match:
                exact: [service-b.app-namespace.svc.cluster.local]
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
  logging:
    accessLog:
      file:
        path: /dev/stdout
```
계정의 ACTIVE CA 전체를 변수 하나에 넣지 마세요. 루트 CA 생성에는 명시적인 구성과 활성화·인증서 단계가 필요하고 요금이 발생하며 즉시 사용 가능한 인증서가 생기는 것은 아닙니다. 의도한 ARN을 정확히 보존합니다. App Mesh Kubernetes CRD 필드는 대소문자를 구분하며 `certificateARN`, `certificateAuthorityARNs`를 사용합니다. 일반 YAML 파일의 `${CA_ARN}`은 셸 변수로 치환되지 않습니다. 파일 기반 예제는 누락된 CA 절차를 실행했다고 가정하지 않습니다.

기존 평문 피어는 문서화된 PERMISSIVE 전환, 클라이언트·서버 신원과 신뢰 준비, 허용·거부 피어 테스트를 거쳐 STRICT로 바꿉니다. `ssl.handshake`, `ssl.no_certificate`, `ssl.fail_verify_no_cert`, `ssl.fail_verify_san`과 실제 요청을 확인하며 서버 TLS 성공만으로 mTLS를 증명하지 않습니다.

**3. 이전 중 관찰 가능성을 보존합니다.** 이전 절차의 `Mesh.spec.tracing`, `Mesh.spec.logging`, `Mesh.spec.serviceDiscovery`는 검토한 controller1.13.1 CRD 필드가 아닙니다. 접근 로그는 위처럼 VirtualNode에 구성합니다. App Mesh Envoy 이미지의 tracing 설정은 별도이며 다음 **컨테이너 환경 조각**에는 로컬2000 포트의 X-Ray daemon/collector, 권한·엔드포인트 접근과 trace-context 전달이 필요합니다:
```yaml
env:
- name: ENABLE_ENVOY_XRAY_TRACING
  value: "1"
- name: XRAY_DAEMON_PORT
  value: "2000"
```
승인된 수집기로 실제 프록시 `/stats` 또는 Prometheus 엔드포인트를 수집합니다. CloudWatch에는 scrape·export·EMF 구성이 필요하며 `AWS/AppMesh` RequestCount/Latency가 자동 생성된다고 가정하지 않습니다. 대시보드 전에 실제 네임스페이스·메트릭 이름·차원·단위를 조사합니다. 기존 CloudWatch·Prometheus·Grafana 소유권과 자격 증명·지원 StorageClass를 유지하세요. floating 매니페스트, 고정 Grafana 관리자 암호와 검토하지 않은 public LoadBalancer는 피합니다. 선택적인 아래 Grafana provisioning 조각은 기존 Prometheus datasource만 식별하며 설치나 보안 구성이 아닙니다:
```yaml
apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://prometheus-server.prometheus.svc.cluster.local
  access: proxy
  isDefault: true
```
**4. 트래픽 동작을 명시적으로 대응합니다.** 아래 기존 router 예제는 두 버전의 VirtualNode와 정상 엔드포인트가 이미 있음을 전제로 하며 가중치가 정확한 요청 수를 보장하지 않습니다. Outlier detection은 엔드포인트 배제이며 연결 풀 circuit-breaking 제한과 다릅니다. 이전 HTTP 재시도 이벤트 네 문자열은 유효합니다. `client-error`는409, `stream-error`는 refused stream을 뜻합니다. 전체 타임아웃 예산 안에서 멱등 작업의 재시도를 선택하며 실패 부하 증폭을 주의합니다.
```yaml
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
      retryPolicy:
        maxRetries: 3
        perRetryTimeout:
          unit: ms
          value: 2000
        httpRetryEvents:
        - gateway-error
```
**5. 검증 후 점진적으로 전환합니다.** 트래픽 이동 전 라우팅, 허용·거부 피어, DNS, TLS 회전, 재시도, 장애 복구, 추적·메트릭 연속성을 비교합니다. 남은 제품 지원 기간 안에서 되돌릴 경로를 보존합니다. 기존 프록시 CPU100–200m·메모리128–256Mi는 **검증되지 않은 예시 추정값**이며 실측·용량 보장이 아닙니다. 실제 포화도·메모리·지연·오류율을 측정하세요. 이 감사에서는 메시·CA·수집기·클라우드 대시보드를 생성하지 않았습니다.

</details>

### 8. VPC CNI1.23.0에서 연결 ENI의 MTU를 구성하는 변수는 무엇인가요?

- A. `ENI_MTU`
- B. `AWS_VPC_ENI_MTU`
- C. `VPC_MTU_SIZE`
- D. `MAX_ENI`

<details>
<summary>정답 보기</summary>

**정답: B. `AWS_VPC_ENI_MTU`**

`POD_MTU`는 Pod 가상 인터페이스를 구성하며 미설정 시 ENI MTU에서 값을 가져옵니다. 이전 `ENI_MTU`는 잘못된 이름입니다. 실제 경로 MTU와 노드·Pod 롤아웃을 맞추며 숫자가 허용된다고 게이트웨이·터널·원격 엔드포인트가 패킷 크기를 수용한다는 보장은 없습니다. SG는 MTU 설정 장치가 아닙니다.

</details>

### 9. Strict Pod-SG의 TCP early-demux 우회 설정은 어디에 적용하나요?

- A. Application Deployment
- B. CoreDNS ConfigMap
- C. CNI init container
- D. LoadBalancer annotation

<details>
<summary>정답 보기</summary>

**정답: C. `aws-vpc-cni-init`**

공식 안내의 `DISABLE_TCP_EARLY_DEMUX=true`는 init 컨테이너에 적용하며 Helm의 `init.env`로 표현합니다. main `aws-node` 컨테이너에만 설정하면 init 단계 변경이 적용되지 않습니다. Strict 모드의 kubelet 프로브 문제를 확인해야 하며 standard Pod-SG 모드에는 이 우회가 필요하지 않습니다.

</details>

### 10. Kubernetes NetworkPolicy가 보장하는 규칙 순서 최적화는 무엇인가요?

- A. Put the hottest rule first
- B. Sort names alphabetically
- C. Create restrictive policies last
- D. No order guarantee

<details>
<summary>정답 보기</summary>

**정답: D. 없음. 일치하는 허용은 합집합입니다.**

이식 가능한 “첫 일치 우선”이나 최신 정책 우선 규칙은 없습니다. 선택자·방향과 허용 합집합이 격리를 정하며 vendor의 tier/order API는 별개입니다. 필요한 제한을 보존하고 개수만 보고 정책을 지우지 말고 반영·실행 비용을 측정합니다.

</details>

### 11. 서브넷이 고갈됐을 때 WARM_IP_TARGET 증가로 주소 용량이 늘어나나요?

- A. Yes, it expands the subnet
- B. No, it increases spare-address demand
- C. Yes, it bypasses ENI limits
- D. Yes, it repairs every ContainerCreating Pod

<details>
<summary>정답 보기</summary>

**정답: B. 아니요. 여유 주소를 더 요청할 뿐입니다.**

용량이 있을 때 큰 warm target이 할당 지연을 줄일 수 있지만 주소 예약을 늘려 고갈을 악화시킬 수도 있습니다. 서브넷 공간, ENI 슬롯, maxPods, API 제한과 prefix 단편화를 각각 확인합니다. Prefix delegation도 전체 IPv4 주소를 늘리지는 않습니다.

</details>

### 12. 현재 Service 백엔드 주소·조건은 어느 API로 확인하나요?

- A. Only Node events
- B. Ingress annotations
- C. EndpointSlice
- D. Only the Service ClusterIP

<details>
<summary>정답 보기</summary>

**정답: C. EndpointSlice**

Service 네임스페이스에서 `kubernetes.io/service-name=<service>` 레이블로 EndpointSlice를 조회합니다. 주소·포트·ready/serving/terminating 조건과 Service 선택자·targetPort를 함께 확인합니다. 기존 Endpoints 객체는 큰 대상 집합이 잘릴 수 있으며 빈 결과는 로드 밸런서보다 선택자·readiness 문제일 수 있습니다.

</details>

### 13. trafficDistribution: PreferSameZone은 무엇을 뜻하나요?

- A. Never cross an AZ boundary
- B. Prefer same zone with fallback
- C. Move existing Pods to one AZ
- D. Override all Local traffic policies

<details>
<summary>정답 보기</summary>

**정답: B. 사용 가능한 같은 영역의 엔드포인트를 선호하며 대체 경로가 있습니다.**

호환 서비스 프록시의 라우팅 선호이며 AZ 격리 정책은 아닙니다. 지역 용량을 확보하세요. 기존 topology-mode Auto 어노테이션이 우선하며 internal/external의 Local 정책은 각각 더 엄격한 노드 지역성을 적용하여 로컬 엔드포인트가 없으면 트래픽이 중단될 수 있습니다.

</details>

### 14. 가정한10Gbps 흐름과 RTT20ms의 대역폭·지연 곱을 계산하세요.

<details>
<summary>정답 보기</summary>

**정답: 25,000,000바이트, 약23.84MiB.**

```text
10,000,000,000 bits/s × 0.020 s / 8 = 25,000,000 bytes
```
산술 예제이지 EKS 벤치마크나 모든 소켓 버퍼를 이 값으로 설정하라는 권장은 아닙니다. 실제 EC2 단일 흐름·버스트 제한, TCP 자동 튜닝, window scaling, 동시 연결과 메모리 압력을 고려합니다. 이전16MiB 상한도 측정 없이 최적값이라고 할 수 없습니다. Keepalive는 활성화된 유휴 소켓에 동작하며 HTTP 풀링·버퍼 산정과 별개입니다.

</details>

### 15. DNS, Service 선택과 애플리케이션 연결 실패를 어떻게 구분하나요?

<details>
<summary>정답 보기</summary>

**정답: 증거를 수집하고 실제 프로토콜과 정상 대조 경로를 테스트합니다.**

ContainerCreating을 네트워크 문제로 분류하기 전에 영향 Pod의 이벤트를 확인합니다. 알려진 클러스터 Service와 목적지 이름을 해석하고 Service/EndpointSlice의 선택자·포트·readiness를 확인한 뒤 같은 소스에서 Pod IP와 Service URL 접근을 비교합니다. 도구 부재·DNS 실패·죽은 백엔드를 정책 거부로 오인하지 않도록 알려진 정상 경로도 테스트하세요. 본문의 범위가 지정된 진단을 사용합니다:
```bash
set -euo pipefail
: "${APP_NAMESPACE:?Set the affected namespace}"
: "${APP_POD:?Set the affected Pod}"
: "${APP_SERVICE:?Set the affected Service}"
kubectl -n "$APP_NAMESPACE" describe pod "$APP_POD"
kubectl -n "$APP_NAMESPACE" get events --field-selector "involvedObject.name=$APP_POD" --sort-by=.metadata.creationTimestamp
kubectl -n "$APP_NAMESPACE" get service "$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get networkpolicy
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
```
로드 밸런서는 컨트롤러·클래스·scheme·대상 유형과 상태 사유를 식별합니다. 실제 애플리케이션·헬스 포트, SG·경로, TLS/SNI와 Host 라우팅을 확인합니다. ICMP만으로 TCP/UDP NetworkPolicy 적용을 증명할 수 없습니다. 확인한 원인 하나를 변경하고 소유자의 되돌릴 경로를 보존하며 같은 검증을 반복하세요. 예제는 프로덕션 네트워크 테스트 결과를 주장하지 않습니다.

</details>

공식 참고: [Private EKS](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html), [VPC CNI1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md), [CoreDNS cache](https://coredns.io/plugins/cache/), [App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html), [App Mesh metrics](https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html), [Envoy1.39.1](https://github.com/envoyproxy/envoy/releases/tag/v1.39.1).
