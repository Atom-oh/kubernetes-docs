# EKS 네트워킹 - 3부: 성능 최적화, 문제 해결, 고급 사용 사례

## 개요

이 문서에서는 Amazon EKS 네트워킹의 성능 최적화, 문제 해결 방법, 그리고 고급 사용 사례에 대해 알아보겠습니다. 네트워크 성능을 최적화하는 방법, 일반적인 네트워킹 문제를 해결하는 방법, 그리고 고급 네트워킹 기능을 활용하는 방법을 다룹니다.

## 네트워크 성능 최적화

EKS 클러스터의 네트워크 성능을 최적화하기 위한 여러 전략이 있습니다.

### 인스턴스 유형 선택

네트워크 성능은 인스턴스 유형에 따라 크게 달라집니다. 네트워크 집약적인 워크로드에는 향상된 네트워킹을 지원하는 인스턴스 유형을 선택하는 것이 좋습니다.

1. **향상된 네트워킹 지원 인스턴스**: 
   - C5, M5, R5 등의 인스턴스 유형은 향상된 네트워킹을 지원합니다.
   - 이러한 인스턴스는 더 높은 대역폭, 낮은 지연 시간, 낮은 지터를 제공합니다.

2. **네트워크 대역폭**:
   - 인스턴스 크기가 클수록 더 높은 네트워크 대역폭을 제공합니다.
   - 예를 들어, m5.large는 최대 10Gbps, m5.24xlarge는 최대 25Gbps의 네트워크 대역폭을 제공합니다.

3. **Elastic Network Adapter(ENA)**:
   - ENA는 최대 100Gbps의 네트워크 대역폭을 지원합니다.
   - 대부분의 최신 인스턴스 유형은 ENA를 지원합니다.

### 클러스터 네트워킹 모드

EKS는 여러 네트워킹 모드를 지원하며, 각 모드는 성능 특성이 다릅니다.

1. **AWS VPC CNI(기본값)**:
   - 포드에 VPC IP 주소를 직접 할당합니다.
   - 네이티브 VPC 네트워킹을 사용하므로 성능이 우수합니다.
   - 각 노드는 할당할 수 있는 IP 주소 수에 제한이 있습니다.

2. **사용자 정의 네트워킹**:
   - 포드에 특정 서브넷의 IP 주소를 할당할 수 있습니다.
   - 보조 CIDR 블록을 사용하여 IP 주소 공간을 확장할 수 있습니다.
   - 네트워크 토폴로지를 더 세밀하게 제어할 수 있습니다.

3. **대체 CNI 플러그인**:
   - Calico, Cilium 등의 대체 CNI 플러그인을 사용할 수 있습니다.
   - 이러한 플러그인은 추가 기능(예: 네트워크 정책, 암호화)을 제공하지만, 성능 오버헤드가 있을 수 있습니다.

### MTU 최적화

MTU(Maximum Transmission Unit)는 네트워크 성능에 영향을 미치는 중요한 요소입니다.

1. **기본 MTU 설정**:
   - AWS VPC CNI의 기본 MTU는 9001입니다.
   - 일부 네트워크 경로는 더 작은 MTU를 요구할 수 있습니다.

2. **MTU 조정**:
   - AWS VPC CNI의 MTU 설정을 조정할 수 있습니다:

```bash
kubectl set env daemonset aws-node -n kube-system ENI_MTU=9001
```

3. **점보 프레임**:
   - 점보 프레임(MTU > 1500)을 사용하면 네트워크 성능이 향상될 수 있습니다.
   - VPC, 서브넷, 보안 그룹, 로드 밸런서 등 모든 네트워크 구성 요소가 점보 프레임을 지원해야 합니다.

### TCP 최적화

TCP 설정을 최적화하여 네트워크 성능을 향상시킬 수 있습니다.

1. **TCP 조기 역다중화**:
   - TCP 조기 역다중화는 성능을 향상시킬 수 있지만, 일부 네트워킹 모드에서는 문제를 일으킬 수 있습니다.
   - 필요한 경우 비활성화할 수 있습니다:

```bash
kubectl set env daemonset aws-node -n kube-system DISABLE_TCP_EARLY_DEMUX=true
```

2. **TCP keepalive 설정**:
   - TCP keepalive 설정을 조정하여 연결 유지 및 재사용을 최적화할 수 있습니다.
   - 이는 특히 많은 수의 짧은 연결을 처리하는 워크로드에 유용합니다.

```bash
# 시스템 수준 TCP keepalive 설정
sysctl -w net.ipv4.tcp_keepalive_time=60
sysctl -w net.ipv4.tcp_keepalive_intvl=15
sysctl -w net.ipv4.tcp_keepalive_probes=6
```

3. **TCP 버퍼 크기**:
   - TCP 버퍼 크기를 조정하여 처리량을 최적화할 수 있습니다.
   - 대역폭 지연 곱(BDP)에 따라 버퍼 크기를 설정하는 것이 좋습니다.

```bash
# 시스템 수준 TCP 버퍼 설정
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
```

### 노드 배치 및 지역성

노드 배치 및 지역성을 최적화하여 네트워크 성능을 향상시킬 수 있습니다.

1. **가용 영역 지역성**:
   - 통신이 빈번한 포드를 같은 가용 영역에 배치하여 지연 시간을 줄입니다.
   - 포드 어피니티 및 안티-어피니티를 사용하여 포드 배치를 제어합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - cache
              topologyKey: topology.kubernetes.io/zone
```

2. **노드 지역성**:
   - 통신이 빈번한 포드를 같은 노드에 배치하여 네트워크 홉을 줄입니다.
   - 이는 지연 시간에 민감한 애플리케이션에 특히 유용합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - cache
              topologyKey: kubernetes.io/hostname
```

3. **토폴로지 인식 힌트**:
   - 토폴로지 인식 힌트를 사용하여 서비스 트래픽을 같은 영역 내에서 유지합니다.
   - 이는 가용 영역 간 데이터 전송 비용을 줄이고 지연 시간을 개선합니다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.kubernetes.io/topology-aware-hints: "auto"
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### 네트워크 정책 최적화

네트워크 정책은 보안을 강화하지만, 성능에 영향을 미칠 수 있습니다.

1. **정책 수 최소화**:
   - 필요한 최소한의 네트워크 정책만 적용합니다.
   - 너무 많은 정책은 성능 저하를 일으킬 수 있습니다.

2. **정책 범위 최적화**:
   - 광범위한 정책보다 구체적인 정책을 사용합니다.
   - 레이블 선택기를 사용하여 정책 범위를 제한합니다.

3. **정책 평가 순서 고려**:
   - 네트워크 정책은 누적적으로 평가됩니다.
   - 가장 자주 사용되는 규칙을 먼저 정의하여 평가 성능을 최적화합니다.

## 네트워킹 문제 해결

EKS 클러스터에서 발생할 수 있는 일반적인 네트워킹 문제와 해결 방법을 알아보겠습니다.

### 포드 네트워킹 문제

1. **포드 IP 할당 실패**:
   - 증상: 포드가 `ContainerCreating` 상태에 멈춰 있음
   - 원인: 노드에 사용 가능한 IP 주소가 부족함
   - 해결 방법:
     - 노드 상태 확인: `kubectl describe node <node-name>`
     - AWS VPC CNI 로그 확인: `kubectl logs -n kube-system -l k8s-app=aws-node`
     - WARM_IP_TARGET 증가: `kubectl set env daemonset aws-node -n kube-system WARM_IP_TARGET=10`
     - 노드 인스턴스 유형 업그레이드: 더 많은 ENI와 IP 주소를 지원하는 인스턴스 유형으로 변경

2. **포드 간 통신 문제**:
   - 증상: 포드가 다른 포드와 통신할 수 없음
   - 원인: 네트워크 정책, 보안 그룹, 라우팅 문제 등
   - 해결 방법:
     - 네트워크 정책 확인: `kubectl get networkpolicy`
     - 보안 그룹 규칙 확인: AWS 콘솔 또는 AWS CLI 사용
     - 포드 내에서 네트워크 연결 테스트:
     
```bash
kubectl exec -it <pod-name> -- ping <target-pod-ip>
kubectl exec -it <pod-name> -- curl <target-service-name>
kubectl exec -it <pod-name> -- traceroute <target-pod-ip>
```

3. **DNS 해결 문제**:
   - 증상: 포드가 서비스 이름을 해결할 수 없음
   - 원인: CoreDNS 문제, 네트워크 정책, 보안 그룹 등
   - 해결 방법:
     - CoreDNS 포드 상태 확인: `kubectl get pods -n kube-system -l k8s-app=kube-dns`
     - CoreDNS 로그 확인: `kubectl logs -n kube-system -l k8s-app=kube-dns`
     - DNS 구성 확인: `kubectl exec -it <pod-name> -- cat /etc/resolv.conf`
     - DNS 쿼리 테스트:
     
```bash
kubectl exec -it <pod-name> -- nslookup kubernetes.default.svc.cluster.local
kubectl exec -it <pod-name> -- dig kubernetes.default.svc.cluster.local
```

### 서비스 및 로드 밸런싱 문제

1. **서비스 연결 문제**:
   - 증상: 서비스를 통해 포드에 연결할 수 없음
   - 원인: 서비스 선택기, 포드 상태, 엔드포인트 등
   - 해결 방법:
     - 서비스 상태 확인: `kubectl describe service <service-name>`
     - 엔드포인트 확인: `kubectl get endpoints <service-name>`
     - 포드 상태 확인: `kubectl get pods -l <selector-label>`
     - 서비스 DNS 확인: `kubectl exec -it <pod-name> -- nslookup <service-name>`

2. **로드 밸런서 문제**:
   - 증상: 외부에서 로드 밸런서에 연결할 수 없음
   - 원인: 보안 그룹, 서브넷 태그, 상태 확인 등
   - 해결 방법:
     - 로드 밸런서 상태 확인: AWS 콘솔 또는 AWS CLI 사용
     - 보안 그룹 규칙 확인: 인바운드 트래픽 허용 여부
     - 서브넷 태그 확인: 적절한 태그가 있는지 확인
     - 상태 확인 구성 확인: 상태 확인 경로, 포트 등

3. **Ingress 문제**:
   - 증상: Ingress를 통해 서비스에 연결할 수 없음
   - 원인: Ingress 컨트롤러, 주석, 인증서 등
   - 해결 방법:
     - Ingress 상태 확인: `kubectl describe ingress <ingress-name>`
     - Ingress 컨트롤러 로그 확인: `kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller`
     - ALB 상태 확인: AWS 콘솔 또는 AWS CLI 사용
     - 대상 그룹 상태 확인: 대상이 정상인지 확인

### VPC 및 서브넷 문제

1. **IP 주소 부족**:
   - 증상: 포드 또는 노드를 생성할 수 없음
   - 원인: VPC 또는 서브넷의 IP 주소 공간 부족
   - 해결 방법:
     - VPC CIDR 블록 확인: `aws ec2 describe-vpcs --vpc-id <vpc-id>`
     - 서브넷 CIDR 블록 확인: `aws ec2 describe-subnets --subnet-id <subnet-id>`
     - 보조 CIDR 블록 추가: `aws ec2 associate-vpc-cidr-block --vpc-id <vpc-id> --cidr-block <cidr-block>`
     - 새 서브넷 생성: 더 큰 CIDR 블록으로 새 서브넷 생성

2. **라우팅 문제**:
   - 증상: 특정 대상으로 트래픽을 라우팅할 수 없음
   - 원인: 라우팅 테이블, NAT 게이트웨이, 인터넷 게이트웨이 등
   - 해결 방법:
     - 라우팅 테이블 확인: `aws ec2 describe-route-tables --route-table-id <route-table-id>`
     - NAT 게이트웨이 상태 확인: `aws ec2 describe-nat-gateways --nat-gateway-id <nat-gateway-id>`
     - 인터넷 게이트웨이 상태 확인: `aws ec2 describe-internet-gateways --internet-gateway-id <internet-gateway-id>`
     - 라우팅 추가 또는 수정: `aws ec2 create-route` 또는 `aws ec2 replace-route`

3. **VPC 엔드포인트 문제**:
   - 증상: AWS 서비스에 연결할 수 없음
   - 원인: VPC 엔드포인트 구성, 보안 그룹, 라우팅 등
   - 해결 방법:
     - VPC 엔드포인트 상태 확인: `aws ec2 describe-vpc-endpoints --vpc-endpoint-id <vpc-endpoint-id>`
     - 엔드포인트 보안 그룹 확인: 인바운드 및 아웃바운드 규칙
     - 프라이빗 DNS 설정 확인: 프라이빗 DNS가 활성화되어 있는지 확인
     - 엔드포인트 정책 확인: 적절한 권한이 있는지 확인

### 진단 도구 및 기법

1. **네트워크 진단 포드**:
   - 네트워크 문제를 진단하기 위한 도구가 포함된 포드를 배포합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: network-diagnostic
spec:
  containers:
  - name: network-diagnostic
    image: nicolaka/netshoot
    command:
    - sleep
    - "3600"
```

```bash
kubectl exec -it network-diagnostic -- bash
```

2. **tcpdump를 사용한 패킷 캡처**:
   - 포드 내에서 네트워크 트래픽을 캡처하여 분석합니다.

```bash
kubectl exec -it <pod-name> -- tcpdump -i any -n port 80
```

3. **AWS VPC Flow Logs**:
   - VPC 수준에서 네트워크 트래픽을 모니터링합니다.
   - VPC Flow Logs를 활성화하고 CloudWatch Logs에서 분석합니다.

```bash
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxxxxxxxxxxxxxx \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-destination arn:aws:logs:us-west-2:123456789012:log-group:/aws/vpc/flowlogs
```

4. **AWS X-Ray**:
   - 분산 애플리케이션의 요청 추적 및 분석을 수행합니다.
   - X-Ray SDK를 애플리케이션에 통합하고 X-Ray 콘솔에서 추적을 분석합니다.
## 고급 네트워킹 사용 사례

EKS에서 지원하는 고급 네트워킹 사용 사례를 살펴보겠습니다.

### 멀티 클러스터 네트워킹

여러 EKS 클러스터 간의 네트워킹을 구성하는 방법입니다.

1. **VPC 피어링**:
   - 서로 다른 VPC에 있는 EKS 클러스터 간에 VPC 피어링을 설정합니다.
   - 이를 통해 클러스터 간에 프라이빗 IP 주소를 사용하여 통신할 수 있습니다.

```bash
# VPC 피어링 연결 생성
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --peer-vpc-id vpc-yyyyyyyyyyyyyyyyy

# 피어링 연결 수락
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id pcx-zzzzzzzzzzzzzzzzz

# 라우팅 테이블 업데이트
aws ec2 create-route \
  --route-table-id rtb-xxxxxxxxxxxxxxxxx \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id pcx-zzzzzzzzzzzzzzzzz

aws ec2 create-route \
  --route-table-id rtb-yyyyyyyyyyyyyyyyy \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id pcx-zzzzzzzzzzzzzzzzz
```

2. **AWS Transit Gateway**:
   - 여러 VPC 및 온프레미스 네트워크를 연결하는 중앙 허브를 생성합니다.
   - 이는 더 복잡한 네트워크 토폴로지에 적합합니다.

```bash
# Transit Gateway 생성
aws ec2 create-transit-gateway \
  --description "EKS Transit Gateway" \
  --options AmazonSideAsn=64512

# VPC 연결
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id tgw-xxxxxxxxxxxxxxxxx \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --subnet-ids subnet-xxxxxxxxxxxxxxxxx subnet-yyyyyyyyyyyyyyyyy

# 라우팅 테이블 업데이트
aws ec2 create-route \
  --route-table-id rtb-xxxxxxxxxxxxxxxxx \
  --destination-cidr-block 10.1.0.0/16 \
  --transit-gateway-id tgw-xxxxxxxxxxxxxxxxx
```

3. **Service Mesh**:
   - AWS App Mesh 또는 Istio와 같은 서비스 메시를 사용하여 여러 클러스터에 걸쳐 있는 서비스를 연결합니다.
   - 이는 서비스 검색, 트래픽 관리, 보안 등의 기능을 제공합니다.

```bash
# AWS App Mesh 메시 생성
aws appmesh create-mesh --mesh-name my-mesh

# 가상 서비스 생성
aws appmesh create-virtual-service \
  --mesh-name my-mesh \
  --virtual-service-name service-a.my-apps.svc.cluster.local \
  --spec '{ 
    "provider": { 
      "virtualNode": { 
        "virtualNodeName": "service-a" 
      } 
    } 
  }'
```

### 하이브리드 네트워킹

EKS 클러스터와 온프레미스 네트워크 간의 연결을 구성하는 방법입니다.

1. **AWS Direct Connect**:
   - 온프레미스 네트워크와 AWS 간에 전용 네트워크 연결을 설정합니다.
   - 이는 안정적이고 지연 시간이 낮은 연결을 제공합니다.

```bash
# Direct Connect 가상 인터페이스 생성
aws directconnect create-private-virtual-interface \
  --connection-id dxcon-xxxxxxxxxxxxxxxxx \
  --new-private-virtual-interface '{ 
    "virtualInterfaceName": "EKS-VIF", 
    "vlan": 100, 
    "asn": 65000, 
    "authKey": "asdf1234", 
    "amazonAddress": "169.254.0.1/30", 
    "customerAddress": "169.254.0.2/30", 
    "virtualGatewayId": "vgw-xxxxxxxxxxxxxxxxx" 
  }'
```

2. **AWS Site-to-Site VPN**:
   - 온프레미스 네트워크와 AWS VPC 간에 암호화된 VPN 연결을 설정합니다.
   - 이는 Direct Connect보다 비용이 저렴하지만, 인터넷을 통해 연결됩니다.

```bash
# 고객 게이트웨이 생성
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.1 \
  --bgp-asn 65000

# VPN 연결 생성
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id cgw-xxxxxxxxxxxxxxxxx \
  --vpn-gateway-id vgw-xxxxxxxxxxxxxxxxx
```

3. **AWS Cloud WAN**:
   - 글로벌 네트워크를 구축하여 데이터 센터, 지사 사무실 및 AWS 클라우드를 연결합니다.
   - 이는 대규모 글로벌 네트워크에 적합합니다.

```bash
# Core Network 생성
aws networkmanager create-core-network \
  --global-network-id global-network-xxxxxxxxxxxxxxxxx \
  --policy-document file://core-network-policy.json
```

### 서비스 메시

서비스 메시는 서비스 간 통신을 관리하는 인프라 레이어입니다.

1. **AWS App Mesh**:
   - AWS의 관리형 서비스 메시 솔루션입니다.
   - 서비스 검색, 트래픽 라우팅, 회로 차단, 지연 시간 기반 라우팅 등의 기능을 제공합니다.

```bash
# App Mesh 컨트롤러 설치
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace \
  --set region=us-west-2 \
  --set serviceAccount.create=false \
  --set serviceAccount.name=appmesh-controller
```

```yaml
# App Mesh 가상 노드 정의
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: my-apps
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
  - portMapping:
      port: 8080
      protocol: http
  serviceDiscovery:
    dns:
      hostname: service-a.my-apps.svc.cluster.local
```

2. **Istio**:
   - 오픈 소스 서비스 메시 솔루션입니다.
   - 트래픽 관리, 보안, 관찰성 등의 기능을 제공합니다.

```bash
# Istio 설치
istioctl install --set profile=default -y
```

```yaml
# Istio 가상 서비스 정의
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: service-a
  namespace: my-apps
spec:
  hosts:
  - service-a
  http:
  - route:
    - destination:
        host: service-a
        subset: v1
      weight: 90
    - destination:
        host: service-a
        subset: v2
      weight: 10
```

3. **Linkerd**:
   - 경량 오픈 소스 서비스 메시 솔루션입니다.
   - 간단한 설치 및 구성으로 빠른 성능을 제공합니다.

```bash
# Linkerd 설치
linkerd install | kubectl apply -f -
```

```yaml
# Linkerd 서비스 프로필 정의
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: service-a.my-apps.svc.cluster.local
  namespace: my-apps
spec:
  routes:
  - name: GET /api/v1/users
    condition:
      method: GET
      pathRegex: /api/v1/users
    responseClasses:
    - condition:
        status:
          min: 500
          max: 599
      isFailure: true
```

### 서비스 검색

서비스 검색은 서비스 엔드포인트를 동적으로 찾는 메커니즘입니다.

1. **AWS Cloud Map**:
   - AWS의 관리형 서비스 검색 솔루션입니다.
   - 애플리케이션 리소스를 등록하고 DNS 또는 API 호출을 통해 검색할 수 있습니다.

```bash
# 네임스페이스 생성
aws servicediscovery create-private-dns-namespace \
  --name my-apps.local \
  --vpc vpc-xxxxxxxxxxxxxxxxx

# 서비스 생성
aws servicediscovery create-service \
  --name service-a \
  --namespace-id ns-xxxxxxxxxxxxxxxxx \
  --dns-config 'NamespaceId=ns-xxxxxxxxxxxxxxxxx,RoutingPolicy=MULTIVALUE,DnsRecords=[{Type=A,TTL=60}]'

# 인스턴스 등록
aws servicediscovery register-instance \
  --service-id srv-xxxxxxxxxxxxxxxxx \
  --instance-id instance-1 \
  --attributes 'AWS_INSTANCE_IPV4=10.0.0.1,AWS_INSTANCE_PORT=8080'
```

2. **ExternalDNS**:
   - Kubernetes 리소스를 외부 DNS 서버에 동기화하는 도구입니다.
   - Route 53, CloudFlare, Google Cloud DNS 등 다양한 DNS 제공업체를 지원합니다.

```bash
# ExternalDNS 설치
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install external-dns bitnami/external-dns \
  --set provider=aws \
  --set aws.zoneType=public \
  --set txtOwnerId=my-cluster \
  --set policy=sync
```

```yaml
# ExternalDNS와 함께 사용할 서비스
apiVersion: v1
kind: Service
metadata:
  name: service-a
  annotations:
    external-dns.alpha.kubernetes.io/hostname: service-a.example.com
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: service-a
```

3. **CoreDNS**:
   - Kubernetes의 기본 DNS 서버입니다.
   - 클러스터 내 서비스 검색을 제공합니다.

```yaml
# CoreDNS 구성 맵 수정
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
    example.com:53 {
        forward . 192.168.1.1
    }
```

### 네트워크 보안

EKS 클러스터의 네트워크 보안을 강화하는 방법입니다.

1. **보안 그룹**:
   - 포드 수준 보안 그룹을 사용하여 포드 간 통신을 제어합니다.
   - 이는 AWS VPC CNI의 보안 그룹 기능을 활성화해야 합니다.

```bash
# 보안 그룹 기능 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
```

```yaml
# 포드 보안 그룹 지정
apiVersion: v1
kind: Pod
metadata:
  name: security-groups-demo
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/security-groups: sg-xxxxxxxxxxxxxxxxx
spec:
  containers:
  - name: nginx
    image: nginx
```

2. **네트워크 정책**:
   - Calico 또는 Cilium과 같은 CNI 플러그인을 사용하여 네트워크 정책을 구현합니다.
   - 이는 포드 간 통신을 세밀하게 제어할 수 있습니다.

```yaml
# 기본 거부 정책
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: my-apps
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

3. **암호화**:
   - Istio 또는 AWS App Mesh를 사용하여 서비스 간 통신을 암호화합니다.
   - 이는 전송 중 데이터를 보호합니다.

```yaml
# Istio mTLS 활성화
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

4. **AWS Network Firewall**:
   - VPC 수준에서 네트워크 트래픽을 필터링합니다.
   - 이는 애플리케이션 계층 및 네트워크 계층 보호를 제공합니다.

```bash
# Network Firewall 생성
aws network-firewall create-firewall \
  --firewall-name my-firewall \
  --firewall-policy-arn arn:aws:network-firewall:us-west-2:123456789012:firewall-policy/my-policy \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --subnet-mappings '[{"SubnetId":"subnet-xxxxxxxxxxxxxxxxx"}]'
```

## 네트워크 모니터링 및 로깅

EKS 클러스터의 네트워크 트래픽을 모니터링하고 로깅하는 방법입니다.

### VPC Flow Logs

VPC Flow Logs는 VPC의 네트워크 인터페이스에서 송수신되는 IP 트래픽에 대한 정보를 캡처합니다.

1. **Flow Logs 활성화**:

```bash
# VPC Flow Logs 활성화
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxxxxxxxxxxxxxx \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-destination arn:aws:logs:us-west-2:123456789012:log-group:/aws/vpc/flowlogs
```

2. **Flow Logs 분석**:
   - CloudWatch Logs Insights를 사용하여 Flow Logs를 분석합니다.

```
# 거부된 트래픽 쿼리
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action
| filter action = "REJECT"
| sort @timestamp desc
| limit 100
```

### 컨테이너 인사이트

Container Insights는 컨테이너화된 애플리케이션 및 마이크로서비스의 지표 및 로그를 수집, 집계, 요약합니다.

1. **Container Insights 활성화**:

```bash
# Container Insights 활성화
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

2. **Container Insights 대시보드**:
   - CloudWatch 콘솔에서 Container Insights 대시보드를 확인합니다.
   - 네트워크 지표(예: 네트워크 RX/TX)를 모니터링합니다.

### Prometheus 및 Grafana

Prometheus는 메트릭을 수집하고 Grafana는 이를 시각화하는 도구입니다.

1. **Prometheus 설치**:

```bash
# Prometheus 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring \
  --create-namespace
```

2. **Grafana 설치**:

```bash
# Grafana 설치
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set service.type=LoadBalancer
```

3. **네트워크 대시보드**:
   - Grafana에서 네트워크 대시보드를 가져옵니다.
   - 네트워크 트래픽, 지연 시간, 오류율 등을 모니터링합니다.

### AWS X-Ray

AWS X-Ray는 애플리케이션이 처리하는 요청에 대한 데이터를 수집하고 이를 사용하여 애플리케이션 문제를 식별하고 최적화 기회를 찾는 데 도움을 줍니다.

1. **X-Ray 설정**:

```bash
# X-Ray 데몬 설치
kubectl create namespace xray
kubectl apply -f https://amazon-eks.s3.amazonaws.com/cloudformation/2020-02-22/aws-xray-daemonset.yaml
```

2. **애플리케이션 통합**:
   - X-Ray SDK를 애플리케이션에 통합합니다.
   - 서비스 간 요청을 추적합니다.

### Hubble (Cilium)

Hubble은 Cilium의 관찰성 계층으로, 네트워크 흐름을 시각화하고 문제를 해결하는 데 도움을 줍니다.

1. **Cilium 및 Hubble 설치**:

```bash
# Cilium 및 Hubble 설치
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true
```

2. **Hubble UI 액세스**:

```bash
# Hubble UI 포트 포워딩
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

3. **네트워크 흐름 시각화**:
   - Hubble UI에서 네트워크 흐름을 시각화합니다.
   - 서비스 간 통신 패턴을 분석합니다.

## EKS 네트워킹 모범 사례

EKS 클러스터의 네트워킹을 최적화하기 위한 모범 사례입니다.

### 네트워크 설계

1. **VPC 설계**:
   - 충분한 IP 주소 공간을 계획합니다.
   - 최소 2개 이상의 가용 영역에 서브넷을 배포합니다.
   - 퍼블릭 및 프라이빗 서브넷을 적절히 구성합니다.

2. **서브넷 설계**:
   - 노드와 포드를 위한 별도의 서브넷을 고려합니다.
   - 서브넷에 적절한 태그를 지정합니다.
   - 서브넷 크기를 예상 노드 및 포드 수에 맞게 계획합니다.

3. **보안 그룹 설계**:
   - 최소 권한 원칙을 적용합니다.
   - 필요한 포트만 개방합니다.
   - 보안 그룹 규칙을 정기적으로 검토합니다.

### 성능 최적화

1. **인스턴스 유형 선택**:
   - 네트워크 집약적인 워크로드에는 향상된 네트워킹을 지원하는 인스턴스 유형을 선택합니다.
   - 인스턴스 크기에 따라 네트워크 대역폭이 달라집니다.

2. **CNI 최적화**:
   - AWS VPC CNI 구성을 워크로드에 맞게 최적화합니다.
   - 필요한 경우 대체 CNI 플러그인을 고려합니다.

3. **로드 밸런싱 최적화**:
   - 워크로드에 적합한 로드 밸런서 유형을 선택합니다.
   - 교차 영역 로드 밸런싱을 활성화합니다.
   - 적절한 대상 유형을 선택합니다.

### 보안 강화

1. **네트워크 정책 구현**:
   - 기본 거부 정책을 적용합니다.
   - 필요한 통신만 명시적으로 허용합니다.
   - 네임스페이스 간 통신을 제한합니다.

2. **전송 중 암호화**:
   - 서비스 메시를 사용하여 서비스 간 통신을 암호화합니다.
   - HTTPS를 사용하여 외부 통신을 암호화합니다.

3. **액세스 제어**:
   - IAM 역할 및 정책을 적절히 구성합니다.
   - RBAC를 사용하여 Kubernetes API 액세스를 제어합니다.

### 운영 효율성

1. **자동화**:
   - 인프라를 코드로 관리합니다(예: Terraform, AWS CDK).
   - CI/CD 파이프라인을 구축합니다.

2. **모니터링 및 로깅**:
   - 네트워크 트래픽을 모니터링합니다.
   - 이상 징후를 감지하기 위한 경보를 설정합니다.
   - 로그를 중앙 집중화하고 분석합니다.

3. **문서화**:
   - 네트워크 설계 및 구성을 문서화합니다.
   - 문제 해결 절차를 문서화합니다.

## 결론

이 문서에서는 EKS 네트워킹의 성능 최적화, 문제 해결, 고급 사용 사례에 대해 알아보았습니다. 네트워크 성능을 최적화하는 방법, 일반적인 네트워킹 문제를 해결하는 방법, 그리고 고급 네트워킹 기능을 활용하는 방법을 다루었습니다.

EKS 네트워킹은 복잡하지만, 적절한 설계, 구성, 모니터링을 통해 안정적이고 성능이 우수한 네트워크 환경을 구축할 수 있습니다. 이 문서에서 다룬 모범 사례를 따르면 EKS 클러스터의 네트워킹 문제를 최소화하고 성능을 최적화할 수 있습니다.

다음 단계로는 EKS 스토리지에 대해 알아보겠습니다. EKS에서 사용할 수 있는 다양한 스토리지 옵션, 스토리지 클래스, 영구 볼륨 등에 대해 알아볼 것입니다.
