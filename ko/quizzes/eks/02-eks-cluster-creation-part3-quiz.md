# EKS 클러스터 생성 퀴즈 - Part 3

> **마지막 업데이트**: 2026년 9월 11일

이 퀴즈는 EKS 네트워킹, 노드 용량, 멀티테넌시, 오토스케일링과 노드 보안을 다룹니다. 명령과 매니페스트는 학습용 예제이며, 이번 검토에서 클라우드 배포와 종단 간 동작을 실행하지 않았습니다. 사용 전에 대상 계정·리전·kubeconfig, 호환 애드온 버전과 리소스 소유권을 확인하세요.

## 기본 개념 문제

1. 일반적인 IPv4 보조 IP 계산에서 ENI 수와 ENI당 주소 한도를 결정하는 것은 무엇인가요?
   * A) 네임스페이스 이름
   * B) EC2 인스턴스 유형
   * C) Service 이름
   * D) Deployment 이름

<details>
<summary>정답 보기</summary>

**정답: B) EC2 인스턴스 유형**

Linux IPv4 **보조 IP 모드**에서 서브넷 주소가 충분하고 커스텀 네트워킹·Pod 보안 그룹을 사용하지 않는 경우, 인스턴스 유형이 ENI 수와 ENI당 주소 한도를 결정합니다. 이는 일반적인 노드당 Pod 한도 계산이며, “Pod당 IP 주소 수”를 계산하는 식이 아닙니다.

일반적인 계산식은 **각 ENI**의 기본 주소를 제외합니다:

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
마지막 2는 `aws-node`와 `kube-proxy`의 호스트 네트워크 사용을 반영한 전통적인 여유분입니다. 아래 표는 보조 IP 방식의 계산 결과이며, 모든 AMI·CNI 모드·관리형 노드 그룹의 실제 `maxPods`를 뜻하지 않습니다.

| Instance Type | Max ENIs | IPs per ENI | Max Pods |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**실제 용량과 EC2 한도 확인:**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
서브넷 IP가 부족하면 노드 한도에 도달하기 전에도 Pod 생성이 실패할 수 있습니다. CPU·메모리 요청, 다른 호스트 네트워크 Pod, 커스텀 네트워킹, Pod 보안 그룹과 kubelet 설정도 고려해야 합니다. 관리형 노드 그룹은 계산식 결과가 더 크더라도 30 vCPU 미만 인스턴스의 `maxPods`를 110, 그 외에는 250으로 제한합니다.

IPv4 prefix delegation은 ENI의 보조 주소 **슬롯** 하나에 `/28`을 할당하며, ENI 하나에 여러 prefix가 들어갈 수 있습니다. 서브넷의 주소 공간 자체가 늘어나지는 않습니다. 선행조건과 전환 절차는 5번 문제를 참고하세요.

커스텀 AL2023 AMI는 적절한 값을 계산·검증한 후 NodeConfig의 `spec.kubelet.config.maxPods`를 설정합니다. 커스텀 AMI ID가 없는 관리형 노드 그룹은 EKS가 권장값을 계산합니다. kubelet 한도만 높여도 IP나 컴퓨팅 용량이 생기지는 않습니다. eksctl에 존재하지 않는 `--kubelet-extra-args` 옵션을 전달하면 안 됩니다.

</details>

2. Pod를 선택하는 NetworkPolicy가 없을 때 NetworkPolicy 기준 격리 상태는 무엇인가요?
   * A) 다른 네트워크 제어를 따르되 격리되지 않음
   * B) 동일 네임스페이스 통신만 허용
   * C) 명시적 허용 규칙 필수
   * D) 모든 트래픽 차단

<details>
<summary>정답 보기</summary>

**정답: A) 다른 네트워크 제어를 따르되 격리되지 않음**

특정 방향에 대해 Pod를 선택하는 정책이 없으면 Kubernetes NetworkPolicy는 그 방향을 격리하지 않습니다. 그렇다고 보안 그룹·라우팅 테이블·NACL·다른 정책 API나 애플리케이션 리스너를 우회하는 것은 아닙니다.

Amazon VPC CNI는 지원되는 Linux EC2 노드에서 활성화하면 NetworkPolicy를 기본 기능으로 집행할 수 있습니다. 현재 표준·관리자 정책 안내는 VPC CNI 1.21 이상과 커널 5.10 이상을 요구하므로 선택한 애드온의 호환성을 확인하세요. Windows와 Fargate는 이 집행 경로의 대상이 아닙니다. Deployment처럼 컨트롤러가 관리하는 Pod를 사용하고 AWS의 인터페이스·Service 포트 제한을 확인하세요.

AWS VPC 네트워크 위의 Calico 정책과 Cilium AWS-CNI chaining도 대안이며 각각 별도 설치 조건이 있습니다. 구성 없이 두 번째 CNI를 설치하거나 정책 에이전트를 의도치 않게 중복 실행하면 안 됩니다. AWS Network Firewall은 라우팅되는 VPC 트래픽을 필터링하며 Kubernetes NetworkPolicy의 셀렉터를 구현하지 않습니다.

아래는 **새 전용** `network-policy-lab` 네임스페이스의 예제입니다. 첫 정책은 ingress만 격리합니다. 이어지는 두 정책은 특정 트래픽을 허용하며, `prod` 피어는 기본 네임스페이스 레이블과 backend Pod 레이블을 모두 만족해야 합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: network-policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: backend}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: frontend}
    ports:
    - {protocol: TCP, port: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prod-to-database
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: database}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: prod
      podSelector:
        matchLabels: {app: backend}
    ports:
    - {protocol: TCP, port: 5432}
```
egress도 격리하려면 실제 DNS 경로와 애플리케이션 의존성을 별도로 허용해야 합니다. 차단 결과는 기본 연결·DNS·준비 상태와 허용된 대조군이 정상임을 먼저 확인해야 의미가 있습니다. 간단한 테스트를 위해 `kube-system`이나 공유 `default` 네임스페이스 전체에 deny 정책을 적용하지 마세요.

</details>

3. 프라이빗 IPv4 서브넷의 일반적인 인터넷 egress 경로는 무엇인가요?
   * A) 서브넷에 IGW 연결
   * B) 퍼블릭 NAT Gateway를 거쳐 VPC의 IGW로 라우팅
   * C) 각 Pod에 Elastic IP 할당
   * D) 프라이빗 NAT Gateway에서 IGW로 직접 라우팅

<details>
<summary>정답 보기</summary>

**정답: B) 퍼블릭 NAT Gateway를 거쳐 VPC의 IGW로 라우팅**

프라이빗 IPv4 노드와 Pod에서 퍼블릭 IPv4 인터넷으로 나가야 한다면, 프라이빗 서브넷의 기본 경로를 **퍼블릭 서브넷의 퍼블릭 NAT Gateway**로 연결하는 구성이 일반적입니다. 그 퍼블릭 서브넷은 **VPC**에 연결된 Internet Gateway로 라우팅하며 NAT Gateway에는 Elastic IP가 있어야 합니다. NAT 인스턴스도 가능하지만 라우팅·source/destination check와 운영 구성이 추가로 필요합니다.

IPv4 VPC CNI의 기본 SNAT 동작에서는 VPC 외부로 향하는 Pod 트래픽이 먼저 노드의 기본 IPv4 주소를 사용합니다. 퍼블릭 IPv4와 IGW 경로가 있는 퍼블릭 노드는 다른 경로를 사용할 수 있습니다. 네이티브 IPv6 egress는 egress-only Internet Gateway를 사용할 수 있고, VPC Endpoint를 통한 AWS 서비스 접근에는 인터넷 NAT가 필요하지 않을 수 있습니다. NAT를 모든 Pod의 보편적인 필수조건으로 설명하면 안 됩니다.

**단일 AZ CloudFormation 라우팅 예제:** 퍼블릭·프라이빗 라우팅 테이블 연결을 설명하며 완전한 EKS VPC가 아닙니다. EKS 클러스터 서브넷은 최소 두 AZ가 필요합니다. AZ 단위 NAT 설계는 다른 AZ 의존성을 피하도록 AZ별 NAT Gateway와 프라이빗 경로를 고려하세요. NAT Gateway와 퍼블릭 IPv4에는 요금이 발생합니다. 클러스터 배포에는 개념 문서의 완전한 EKS VPC 템플릿을 검토하세요.

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: One-AZ IPv4 NAT routing demonstration; not a complete EKS VPC
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable
```
`SubnetRouteTableAssociation` 리소스가 반드시 필요합니다. 연결되지 않은 테이블에 경로를 만들어도 해당 서브넷의 라우팅은 바뀌지 않습니다.

별도로 검토한 배포 후 실제 ID와 경로를 확인하세요. CLI로 NAT Gateway를 생성한다면 반환된 ID를 저장하고 `nat-gateway-available`을 기다린 다음 경로를 생성해야 합니다. NAT 생성이 실패하면 이후 작업을 중단해야 합니다.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region}"
: "${VPC_ID:?Set the deployed VPC ID}"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
aws ec2 describe-nat-gateways --region "$AWS_REGION" \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{Id:NatGatewayId,Subnet:SubnetId,State:State}'
```
eksctl의 관리 VPC 생성에서 `vpc.nat.gateway: Single`은 유효하지만 단일 AZ 의존성을 만듭니다. `HighlyAvailable`은 AZ별 NAT를 생성합니다. 이 옵션들이 임의의 기존 서브넷 라우팅을 자동으로 복구하지는 않습니다. 실습 스택은 종속 워크로드·ENI를 제거한 뒤 직접 생성한 리소스만 삭제하고 NAT와 EIP 해제를 확인하세요.

</details>

4. Pod branch ENI 대신 노드 네트워크를 공유하게 하는 Pod 설정은 무엇인가요?
   * A) 일치하는 Pod 레이블
   * B) 일치하는 ServiceAccount 레이블
   * C) hostNetwork: true
   * D) 선택된 SecurityGroupPolicy

<details>
<summary>정답 보기</summary>

**정답: C) hostNetwork: true**

호스트 네트워크 Pod는 노드의 네트워크 네임스페이스와 보안 그룹을 공유합니다. Pod 보안 그룹은 자체 네트워크 네임스페이스를 사용하는 선택된 Pod에 branch ENI를 제공합니다.

이 Linux EC2 예제에는 trunking을 지원하는 인스턴스 유형, 호환 VPC CNI, 클러스터 역할의 `AmazonEKSVPCResourceController` 권한과 `ENABLE_POD_ENI=true`가 필요합니다. EC2 `t` 계열과 EKS Auto Mode는 이 기능을 지원하지 않습니다. DNS·제어 플레인·애플리케이션 규칙, branch ENI 용량과 `POD_SECURITY_GROUP_ENFORCING_MODE`를 확인하세요. 모드에 따라 SNAT와 정책 동작이 다릅니다. 오래된 CNI 매니페스트를 적용하지 말고 애드온 소유자의 설정 경로를 사용하세요.

SecurityGroupPolicy는 `podSelector` **또는** `serviceAccountSelector`로 Pod를 선택하므로 전용 ServiceAccount 생성은 필수가 아닙니다. `ENIConfig`는 커스텀 네트워킹 리소스이며 Pod 보안 그룹만 사용하는 데 필요하지 않습니다.

아래 ServiceAccount 셀렉터 방식은 먼저 전용 `pod-sg-lab` 네임스페이스를 만들고 SG 자리표시자를 올바른 VPC의 검토된 기존 보안 그룹으로 바꾼 뒤 선행조건을 충족해야 합니다. 대기하는 클라이언트는 선택 관계를 보여 주며 DB 연결 성공을 입증하지 않습니다. 일치하는 ServiceAccount 레이블과 Pod의 `serviceAccountName`을 모두 지정했습니다.

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: pod-sg-lab
spec:
  serviceAccountSelector:
    matchLabels:
      role: db-client
  securityGroups:
    groupIds:
    - sg-REPLACE_WITH_REVIEWED_GROUP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: db-client
  namespace: pod-sg-lab
  labels:
    role: db-client
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: pod-sg-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: db-client}
  template:
    metadata:
      labels: {app: db-client}
    spec:
      serviceAccountName: db-client
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
대신 `serviceAccountSelector`를 `podSelector: {matchLabels: {app: db-client}}`로 바꿀 수 있습니다. 정책과 선택되는 Pod는 같은 네임스페이스에 둡니다. **새로 생성된** Pod의 branch ENI와 실제 허용·차단 연결을 확인하세요. 정책을 생성해도 기존 실행 Pod에 소급 적용되지는 않습니다. 테스트 후 이 실습 네임스페이스와 정책만 정리하고 다른 리소스가 쓰는 SG를 삭제하지 마세요.

</details>



5. IPv4 prefix delegation이 제공하는 주요 용량 이점은 무엇인가요?
   * A) Pod 간 통신 속도 향상 보장
   * B) 노드당 Pod IP 용량 증가
   * C) 모든 Pod에 퍼블릭 IPv4 할당
   * D) 자동 네트워크 격리

<details>
<summary>정답 보기</summary>

**정답: B) 노드당 Pod IP 용량 증가**

Linux IPv4 prefix 모드에서는 `/28` 하나(주소 16개)가 ENI 보조 주소 슬롯 하나를 사용합니다. ENI 하나에 여러 prefix를 연결할 수 있지만 ENI 수 한도 자체는 늘어나지 않습니다. kubelet과 리소스 한도 내에서 IP 기준 Pod 밀도를 높이고 주소 할당 API 작업을 줄일 수 있습니다.

`m5.large`의 일반적인 보조 IP 계산 결과는 29 Pod입니다. 호환되는 prefix 모드 관리형 노드 그룹은 권장 `maxPods` 110을 사용할 수 있으며, 제한 없이 “110개 이상”을 실행한다는 뜻이 아닙니다. 이론적인 주소 슬롯 수는 애플리케이션 용량 보장이 아닙니다.

**선행조건과 고려사항:**

* 지원되는 Nitro 인스턴스와 호환 CNI를 사용합니다. Linux IPv4의 역사적 최소 버전은 1.9.0이며 실제 배포에는 현재 지원되는 빌드를 선택합니다.
* 서브넷에는 연속된 `/28` 블록이 필요합니다. 개별 가용 IP가 많아도 단편화되면 `InsufficientCidrBlocks` 오류가 발생할 수 있습니다. Subnet CIDR reservation으로 prefix 공간을 확보할 수 있습니다.
* prefix는 실제 서브넷 주소를 블록 단위로 소비합니다. CIDR 확장이나 IP 사용 감소·활용률 향상·비용 절감을 보장하지 않습니다.
* `WARM_PREFIX_TARGET`은 여유 prefix 수, `WARM_IP_TARGET`은 여유 IP 수, `MINIMUM_IP_TARGET`은 최소 총 할당량입니다. 뒤의 두 설정을 사용하면 `WARM_PREFIX_TARGET`보다 우선합니다. 시작 지연과 미사용 주소 소비를 함께 고려하세요.
* 교체 노드 그룹과 제어된 cordon/drain 마이그레이션을 계획합니다. 환경변수만 바꾸고 모든 Pod를 재시작하는 것으로 끝내면 안 됩니다. PDB·볼륨·여유 용량·롤백을 확인하고 새 노드를 검증한 후 기존 그룹을 제거하세요.

아래는 **새 클러스터 구성 예제**이며 기존 클러스터의 업데이트 명령이 아닙니다. API는 프라이빗 접근만 허용하므로 관리자의 라우팅 경로가 필요합니다. 버전을 생략하면 EKS 호환 기본 CNI 빌드를 선택하므로, 배포 전 실제 선택 버전을 기록·검토하세요. `withOIDC`는 eksctl의 CNI IAM 통합에 사용되며 생성되는 역할을 확인해야 합니다. 크기 상한·하한은 오토스케일러를 설치하지 않습니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prefix-demo
  region: us-west-2
  version: "1.36"
vpc:
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
iam:
  withOIDC: true
addons:
- name: vpc-cni
  configurationValues: |
    {"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
managedNodeGroups:
- name: prefix-linux
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  privateNetworking: true
  disableIMDSv1: true
```

</details>

6. CoreDNS가 읽는 Corefile을 담고 있는 Kubernetes 객체는 무엇인가요?
   * A) 노드 보안 그룹
   * B) coredns ConfigMap
   * C) StorageClass
   * D) PodDisruptionBudget

<details>
<summary>정답 보기</summary>

**정답: B) coredns ConfigMap**

`coredns` ConfigMap의 `data.Corefile`에 DNS 설정이 저장됩니다. 올바른 **설정 소유자**는 EKS 관리형 애드온인지 자체 관리 CoreDNS인지에 따라 다릅니다.

관리형 애드온은 AWS 콘솔과 `aws eks update-addon --configuration-values` 모두 지원 필드를 변경할 수 있습니다. ConfigMap 직접 수정은 애드온 업데이트에서 덮어써질 수 있으므로 전체 커스텀 Corefile을 애드온의 `corefile` 설정 키에 저장하세요. 기존 다른 설정 키를 보존하고 정확한 애드온 버전의 스키마를 검토합니다.

새 로컬 작업 디렉터리에서 수정 전 현재 설정을 저장합니다:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?Set the cluster}"
: "${EXAMPLE_REGION:?Set the Region}"
: "${EXAMPLE_KUBECONFIG:?Set a private kubeconfig path}"
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --addon-name coredns > coredns-addon-before.json
COREDNS_VERSION=$(jq -er '.addon.addonVersion' coredns-addon-before.json)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --query configurationSchema --output text > coredns-schema.json
jq -e '(.addon.configurationValues // "{}") | fromjson | select(type == "object")' \
  coredns-addon-before.json > coredns-values-before.json
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  get configmap coredns -o json | jq -er '.data.Corefile' > Corefile.reviewed
```
`Corefile.reviewed`를 수정할 때 설치 환경이 요구하는 Kubernetes 영역, 전달 설정, `ready`, 상태 확인·모니터링 플러그인을 보존하세요. 아래는 개별 수정 예제이며 전체 Corefile을 대체하지 않습니다:

* 기존 서버 블록에 정적 레코드를 추가합니다. 실제 내부 주소로 바꾸세요:

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* 조건부 전달은 별도 서버 블록으로 구성합니다. 업스트림에 도달할 수 있어야 하며 이 CoreDNS 서비스로 되돌아오는 루프가 없어야 합니다:

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* 기존 cache 구문을 대체하며 중복 추가하지 않습니다. `prefetch` 기간에는 단위가 필요합니다:

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* 선택적인 오류 클래스 쿼리 로깅입니다. 로그량과 민감한 이름 노출을 검토하세요:

```text
log {
    class error
}
```
`autopath`는 서버 측 검색 경로 완성을 위한 별도 플러그인이며 `kubernetes` 하위 지시문이 아닙니다. Kubernetes 블록 내부의 `autopath off`는 잘못된 문법입니다. 기존 `autopath @kubernetes`를 비활성화하려면 해당 지시문을 제거하며, 사용하지 않던 설치에 새로 추가할 필요는 없습니다.

스키마와 문법을 검토한 뒤 **같은** 애드온 버전의 설정을 업데이트합니다:

```bash
# After reviewing the complete Corefile and existing configuration:
jq --rawfile corefile Corefile.reviewed '.corefile = $corefile' \
  coredns-values-before.json > coredns-values-reviewed.json
COREDNS_UPDATE_ID=$(aws eks update-addon \
  --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --resolve-conflicts PRESERVE \
  --configuration-values file://coredns-values-reviewed.json \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --update-id "$COREDNS_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
응답이 아직 `InProgress`일 수 있습니다. 해당 업데이트 ID가 `Successful`이 될 때까지 확인하고, 실패하면 오류를 검토하기 전 다른 변경을 진행하지 마세요. 이후 Deployment 준비 상태·로그·내부 Service 조회와 커스텀 DNS 사례를 검증합니다. 복구가 필요하면 같은 설정 소유자를 통해 저장한 구성을 복원합니다.

자체 관리 CoreDNS는 GitOps·매니페스트 소유자를 통해 검토한 ConfigMap을 수정합니다. `reload`를 사용하면 ConfigMap 반영과 reload 주기 후 Corefile 변경을 감지하므로 재시작이 항상 필요한 것은 아닙니다. reload 오류와 DNS 동작을 확인하세요. Deployment 설정 변경에는 롤아웃이 필요할 수 있습니다.

**스케일링과 리소스:** AWS 선행조건을 만족하는 EKS 관리형 CoreDNS 버전은 `autoScaling` 설정 객체를 지원합니다. 복제본 수를 제어하는 컨트롤러는 하나로 유지하세요. 아래 CPU HPA는 **자체 관리 CoreDNS의 대안**이며 Metrics Server와 CPU requests가 필요합니다. EKS CoreDNS 오토스케일링과 함께 실행하면 안 됩니다:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-autoscaler
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
복제본 2–10개와 목표 60%는 실측에 따른 사이징이 아닌 예시입니다. 메모리·CPU throttling·캐시 증가·토폴로지·DNS 지연을 검토하고, 컨테이너 배열 인덱스로 resources 객체 전체를 덮어쓰지 말고 애드온 스키마 또는 자체 관리 워크로드 소유자를 통해 변경하세요.

</details>

7. 하나의 EKS 클러스터를 공유하는 신뢰 가능한 팀의 논리적 격리에 도움이 되는 조합은 무엇인가요?
   * A) 네임스페이스만 사용
   * B) 네임스페이스·RBAC·집행되는 정책·쿼터
   * C) 노드 선택기만 사용
   * D) 공유 cluster-admin 역할

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스·RBAC·집행되는 정책·쿼터**

서로 신뢰하는 팀이 클러스터를 공유할 때 네임스페이스·RBAC·실제로 집행되는 네트워크 정책·쿼터를 조합하면 논리적인 분리에 도움이 됩니다. 악의적인 테넌트까지 보편적으로 격리하는 해법은 아닙니다.

플랫폼 관리자는 새 `tenant-a`·`tenant-b` 네임스페이스를 만들고 적절한 Pod Security Admission 정책을 적용합니다. 이 Linux EKS 1.36 예제는 Restricted와 버전 `v1.36`을 사용합니다. 아래는 `tenant-a` 정책이며, `tenant-b`에도 대응하는 정책을 검토해 적용하세요. `tenant-a-users`에 대한 인증된 그룹 매핑도 필요합니다.

애플리케이션 권한을 명시적으로 나열했습니다. 이 Role로 테넌트가 ResourceQuota·LimitRange·NetworkPolicy·Role·RoleBinding을 직접 바꿀 수는 없습니다. 클러스터 범위 리소스는 플랫폼이 관리합니다.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
**한계와 검증:**

* 워크로드 생성 권한으로 네임스페이스의 사용 가능한 ServiceAccount나 Secret 마운트를 이용할 수 있습니다. 이 Role은 테넌트 내부 Secret 기밀성 경계가 아닙니다. 허용된 신원·마운트·보안 설정을 admission 정책으로 제한하고 플랫폼 자격 증명은 테넌트 네임스페이스 밖에 둡니다.
* DNS 규칙은 `kube-system`의 `k8s-app=kube-dns` 레이블을 가진 일반 CoreDNS Pod를 가정합니다. NodeLocal DNSCache 등 다른 DNS 경로는 수정·검증해야 합니다. 시스템 Pod로의 모든 egress가 아닌 DNS 쿼리만 허용하며, 다른 네임스페이스의 DNS 이름을 숨기지는 않습니다.
* 쿼터는 승인되는 리소스 요청·개수를 제한하지만 물리 노드 예약·대역폭 보장·noisy neighbor 제거를 보장하지 않습니다. LimitRange 값은 예시 기본값입니다.
* 온보딩 전에 테넌트 신원으로 실제 권한, 허용 연결, 테넌트 간 차단과 쿼터 거부 사례를 검증합니다.
* 전용 노드 그룹은 일부 공유를 줄이지만 노드 선택기·테인트만으로 보안 경계를 만들지는 않습니다. 강한 격리가 필요하면 샌드박스 런타임·가상 제어 플레인·별도 클러스터·계정·네트워크를 공통 의존성과 운영 비용까지 포함해 평가하세요.

네임스페이스 공유는 제어 플레인 부담을 줄이고 중앙 운영을 단순화할 수 있습니다. 보편적으로 “최적”이라는 주장 대신 필요한 격리 수준에 따라 설계를 선택해야 합니다.

</details>

8. EC2 인스턴스 유형의 기술적 용량 자체를 바꾸지 않는 항목은 무엇인가요?
   * A) vCPU와 메모리 크기
   * B) 네트워크·스토리지 한도
   * C) 표시용 이름 태그
   * D) ENI와 주소 한도

<details>
<summary>정답 보기</summary>

**정답: C) 표시용 이름 태그**

인스턴스 선택에는 CPU·메모리·가속기 요구, 아키텍처 호환 이미지·AMI·드라이버, Pod 밀도, 네트워크 대역폭, EBS·인스턴스 스토어 성능, AZ 가용성, 중단 허용 범위와 비용이 중요합니다. Kubernetes 버전도 지원 AMI·드라이버·기능을 통해 영향을 줄 수 있으므로 무관한 요소가 아닙니다.

아래 기존 계열 예시는 워크로드 특성을 설명하며 현재 가격·성능 순위가 아닙니다. `m5`는 범용, `r5`는 메모리 최적화, `c5`는 컴퓨팅 최적화입니다. Graviton 대안은 Arm 호환 이미지와 의존성이 필요합니다. GPU 워크로드에는 적절한 가속기 AMI와 디바이스 플러그인도 필요합니다. 인스턴스 스토어 데이터는 임시적이며 레이블만으로 DB 내구성이나 배치를 제공하지 않습니다.

아래는 검토된 기존 클러스터에 사용하는 **대안별 노드 그룹 구성 파일**입니다(`eksctl create nodegroup -f ...`). 미사용 그룹 이름과 필요한 egress·Endpoint가 있는 프라이빗 서브넷을 사용하고 실제 리전·AZ 제공 여부를 확인합니다. 상한·하한 설정은 Cluster Autoscaler를 설치하지 않습니다. 크기 0인 배치 그룹은 올바른 오토스케일러 또는 수동 확장이 필요합니다.

**웹 서버**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: web-servers
  instanceType: m5.large
  minSize: 2
  maxSize: 10
  labels:
    role: web
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**데이터베이스 워크로드**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: database-nodes
  instanceType: r5.xlarge
  minSize: 3
  maxSize: 5
  labels:
    role: database
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**배치 처리**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: batch-processors
  instanceType: c5.2xlarge
  minSize: 0
  maxSize: 20
  labels:
    role: batch
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**중단을 허용하는 Spot 워커**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: spot-workers
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m5ad.large
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    lifecycle: spot
  amiFamily: AmazonLinux2023
  privateNetworking: true
```
EKS는 버전별 표준 지원 14개월 후 연장 지원 12개월을 제공합니다. 업스트림 Kubernetes 릴리스와 별도로 EKS 지원 일정·업그레이드 조건·애드온 호환성을 확인하세요. 이 예제는 실측 비용 절감이나 용량을 주장하지 않습니다.

</details>

9. 드레인 중 자발적인 Pod 축출을 제한하는 Kubernetes 객체는 무엇인가요?
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>정답 보기</summary>

**정답: B) PodDisruptionBudget**

PDB는 Eviction API를 통한 자발적 축출을 제한합니다. 업데이트 전략의 일부이며 가용성을 보장하지 않습니다. 노드 장애·직접 Pod 삭제·Deployment 자체 롤링 업데이트를 PDB가 막지는 않습니다.

검토된 `update-lab` Deployment에 `app=my-app` 레이블의 복제본이 3개 있다고 가정하면, 다음 예제는 선택된 정상 Pod가 최소 2개 남을 때만 축출을 허용합니다:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
대안은 `maxUnavailable: "50%"`이며 두 예산 필드 중 하나만 지정합니다. 비율은 **올림**하므로 3개 중 2개 또는 1개 중 1개의 중단을 허용합니다. 절반 이상이 항상 남는다는 약속이 아닙니다. 쿼럼·준비 상태·워크로드 동작·스케줄 가능한 여유 용량에 맞춰 예산을 정하세요.

관리형 노드 그룹의 `DEFAULT` 업데이트는 선택한 기존 노드를 드레인하기 전에 대체 용량을 시작합니다. `MINIMAL`은 선택한 기존 노드를 먼저 종료하여 일시적인 추가 용량 필요를 줄입니다. `maxUnavailable`은 동시에 사용할 수 없는 노드 수를 제어하며 PDB는 Pod 축출을 별도로 제한합니다. 축출 보호를 무시할 수 있는 `--force`를 드레인 정체의 일상적인 해결책으로 사용하지 마세요.

노드 업데이트 정책을 먼저 설정하고 해당 업데이트가 성공한 **후에** 버전 업데이트를 시작합니다:

```bash
set -euo pipefail
NODEGROUP_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":1,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODEGROUP_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
해당 ID의 `describe-update`가 `Successful`이 될 때까지 확인하고 `Failed`·`Cancelled`를 명시적으로 처리합니다. 기존의 eksctl `update nodegroup --max-unavailable`은 지원되는 대체 명령이 아닙니다. 실제 PDB의 `disruptionsAllowed`, 준비 상태, 애플리케이션 상태와 볼륨 이동을 확인하세요. 복제본 3개는 보편적인 최소 요구가 아닌 예제입니다.

</details>

10. Pod의 CPU·메모리 요청값을 권장하거나 변경하는 컨트롤러는 무엇인가요?
   * A) Cluster Autoscaler
   * B) Karpenter
   * C) Horizontal Pod Autoscaler
   * D) Vertical Pod Autoscaler

<details>
<summary>정답 보기</summary>

**정답: D) Vertical Pod Autoscaler**

VPA는 Pod 리소스 요청을 권장하거나 갱신하며 HPA는 복제본 수를 바꿉니다. **둘 다** 노드 수요에 간접적으로 영향을 줄 수 있지만 관리형 노드 그룹의 ASG를 직접 관리하지는 않습니다.

| 구성 요소 | 제어 대상 |
| --- | --- |
| Cluster Autoscaler | 스케줄 가능성과 안전한 제거 조건에 따라 검색된 기존 노드 그룹·ASG의 원하는 용량 |
| Karpenter | NodePool·EC2NodeClass로 선택한 자체 NodeClaim·EC2 용량; 관리형 노드 그룹 ASG는 아님 |
| HPA / KEDA | 리소스·사용자 정의·외부 메트릭이나 이벤트에 따른 워크로드 복제본 |
| VPA | 업데이트 모드에 따른 Pod 리소스 권장값·요청값 |

**Cluster Autoscaler:** 클러스터와 같은 Kubernetes 마이너 버전을 사용합니다. EKS 1.36 예제에서 차트 9.59.0은 이미지 `v1.36.1`을 명시해야 합니다(차트 기본 이미지는 1.35.0). 먼저 태그로 제한한 IAM 권한과 ASG 검색 태그를 검토하고 전용 `cluster-autoscaler` ServiceAccount를 구성하세요. 설치 전에 렌더링한 RBAC·이미지·인수를 확인합니다:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
로컬 스토리지 보호를 임의로 비활성화하거나 ASG 대상 추적·예측 정책이 같은 desired capacity를 놓고 Cluster Autoscaler와 경쟁하게 하지 마세요.

**Karpenter 대안:** 호환 컨트롤러를 별도로 설치하고 권한을 구성합니다. AMI ID·노드 역할·검색 태그 값을 이 클러스터의 검토된 리소스로 바꾸세요. AMI는 AL2023·Kubernetes 버전·아키텍처와 일치해야 합니다. `al2023@latest`를 조용히 선택하는 대신 AMI ID 또는 검증한 버전 별칭을 고정합니다. 아래 상한과 통합 주기는 실측 사이징이나 프로비저닝 속도 보장이 아닌 예제입니다.

```yaml
# Karpenter NodePool (karpenter.sh/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
# Karpenter EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_VERIFIED_AL2023_AMI
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
**HPA:** 아래 예제에는 `autoscaling-lab`의 기존 `my-app` Deployment, Metrics Server와 CPU requests가 필요합니다:

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
**VPA:** 먼저 VPA CRD·컨트롤러를 설치합니다. 권장값만 제공하는 모드로 시작하고 권장값을 검토한 후 지원되는 명시적 업데이트 모드를 선택하세요:

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: autoscaling-lab
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```
`Off`는 Pod 리소스를 변경하지 않습니다. 권장값 적용은 VPA·Kubernetes 버전과 설정에 따라 재생성 또는 지원되는 in-place resizing을 사용할 수 있으므로 모든 모드가 재시작한다고 설명하면 안 됩니다. CPU 사용률 HPA가 같은 워크로드를 제어할 때 CPU requests를 변경하면 사용률 분모를 통해 피드백이 발생합니다. 이 권장 전용 예제는 통합 설계를 검토하기 전 충돌을 피합니다.

</details>

## 실습 문제

### 실습 1: EKS 클러스터에서 네트워크 정책 구현

**시나리오:** frontend → backend와 backend → database는 허용하고 frontend → database는 차단합니다. 원래의 Calico 학습 목표를 유지하며 IP 할당은 AWS VPC CNI가 담당합니다.

**범위:** 기존의 폐기 가능한 Linux IPv4 EKS 실습 클러스터, 충돌하는 전역·tier 정책 없음, 일반 CoreDNS와 관리자가 검토한 Calico 설치를 가정합니다. 연결 실습이며 프로덕션 마이크로서비스·DB 구성법이 아닙니다. 이번 감사에서 클라우드 설치나 트래픽 테스트를 실행하지 않았습니다.


<details>
<summary>솔루션 보기</summary>

**1. 정책 엔진 준비.** 공식 Calico EKS 안내의 **Amazon VPC networking** 경로를 따릅니다. 기본 AWS VPC CNI NetworkPolicy 집행은 Calico와 충돌하므로 설정 소유자를 통해 비활성화하되 `aws-node` 네트워킹은 유지합니다. `ANNOTATE_POD_IP=true`와 해당 ServiceAccount의 Pod patch 권한을 구성합니다. 아래 전용 RBAC는 애드온의 ClusterRole YAML에 잘못된 내용을 덧붙이지 않고 권한을 추가하는 예제입니다:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-annotation
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-annotation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-annotation
subjects:
- kind: ServiceAccount
  name: aws-node
  namespace: kube-system
```
RBAC를 저장·검토한 후 의도한 `aws-node` ServiceAccount에만 적용하고, 환경변수는 관리형 애드온 또는 자체 관리 매니페스트 소유자를 통해 설정합니다. 롤아웃과 IP annotation 동작이 정상임을 확인하기 전에는 진행하지 않습니다. 이미 Calico가 설치되어 있다면 아래 신규 설치 명령을 실행하지 말고 기존 구성을 검토해 사용하세요.

```bash
# Download pinned manifests for inspection; do not overwrite an existing installation.
curl --fail --location --output calico-crds.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
curl --fail --location --output tigera-operator.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
# After review, on the intended new lab installation:
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" create -f calico-crds.yaml
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create -f tigera-operator.yaml
```
오퍼레이터 CRD가 Established 상태가 되면 아래 검토된 `Installation`과 `APIServer`를 생성합니다. 오퍼레이터 설치만으로 AWS VPC 네트워킹 구성이 끝나지는 않습니다. `projectcalico.org/v3` 정책 예제에는 API 서버가 필요합니다:

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
```

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get tigerastatus
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get apiservice v3.projectcalico.org
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n calico-system get pods
```
Calico 구성 요소와 집계 API가 사용 가능해야 하며, 실제 집행은 아래에서 검증합니다. Node의 `Ready`만으로는 충분하지 않습니다. 선택적인 Goldmane·Whisker UI는 이 실습에 필요하지 않습니다.

**2. 소유권을 기록한 네임스페이스와 임시 DB 자격 증명 생성.** 이후 코드는 같은 Bash 세션에서 실행합니다. 정리 시 다른 네임스페이스를 대상으로 삼지 않도록 이름과 UID를 기록합니다:

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed lab cluster kubeconfig}"
NETWORK_LAB_DIR=$(mktemp -d /tmp/eks-calico-lab.XXXXXX)
NETWORK_NAMESPACE="calico-quiz-$(date +%s)-$$"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$NETWORK_NAMESPACE"
NETWORK_NAMESPACE_UID=$(kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
  get namespace "$NETWORK_NAMESPACE" -o jsonpath='{.metadata.uid}')
: "${NETWORK_NAMESPACE_UID:?}"
jq -n --arg name "$NETWORK_NAMESPACE" --arg uid "$NETWORK_NAMESPACE_UID" \
  '{namespace:$name,namespaceUID:$uid}' > "$NETWORK_LAB_DIR/ownership.json"
openssl rand -hex 32 > "$NETWORK_LAB_DIR/db-password"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
  create secret generic database-auth \
  --from-file=password="$NETWORK_LAB_DIR/db-password"
```
**3. 세 계층 배포.** frontend·backend는 Python HTTP 서버로 대체하여 두 컨테이너 모두 진단용 TCP 클라이언트를 사용할 수 있게 합니다. PostgreSQL 17 이미지는 `POSTGRES_PASSWORD_FILE`과 같은 네임스페이스의 Secret을 사용하며 외부 DB를 조작하지 않습니다. DB의 `emptyDir`는 **Pod 교체 시 사라집니다**. 중요한 데이터를 넣지 마세요. DB 이미지의 초기화 동작을 유지한 학습용 구성이며 Restricted 프로파일의 프로덕션 DB 매니페스트가 아닙니다. 메이저 버전 이미지 태그는 바뀔 수 있으므로 재현 가능한 실행에는 해석된 digest를 기록하세요.

```bash
# The HTTP layers are diagnostic stand-ins, not business applications.
for tier in frontend backend; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $tier
spec:
  replicas: 1
  selector:
    matchLabels: {app: $tier}
  template:
    metadata:
      labels: {app: $tier}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: diagnostic
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: $tier
spec:
  selector: {app: $tier}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
done

kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 1
  selector:
    matchLabels: {app: database}
  template:
    metadata:
      labels: {app: database}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      containers:
      - name: database
        image: postgres:17-alpine
        env:
        - name: POSTGRES_PASSWORD_FILE
          value: /run/secrets/postgres/password
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: [pg_isready, -U, postgres]
          initialDelaySeconds: 5
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/postgresql/data}
        - {name: auth, mountPath: /run/secrets/postgres, readOnly: true}
      volumes:
      - name: data
        emptyDir: {}
      - name: auth
        secret: {secretName: database-auth}
---
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  selector: {app: database}
  ports:
  - {port: 5432, targetPort: 5432, protocol: TCP}
EOF

for tier in frontend backend database; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    rollout status "deployment/$tier" --timeout=180s
done
```
**4. 기본 연결 확인.** 정책 적용 전 세 TCP 경로와 DNS가 모두 정상이어야 합니다. 포트 5432 연결 성공은 TCP 연결만 입증하며 SQL 인증이나 애플리케이션 정확성을 검증하지 않습니다.

```bash
# Distinguish DNS failure from TCP denial. Status 42 means a TCP failure.
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    exec "deployment/$1" -c diagnostic -- python -c '
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    address = socket.gethostbyname(host)
except OSError as error:
    print("DNS failure:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, port), timeout=3)
    connection.close()
except OSError as error:
    print("TCP connection failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP connection succeeded")
' "$2" "$3"
}

# Baseline: all three must succeed BEFORE the policy is applied.
check_tcp frontend backend 8080
check_tcp backend database 5432
check_tcp frontend database 5432
```
**5. 정책 적용과 테스트.** 선택된 Pod의 양방향을 격리하며 일치하지 않는 트래픽은 차단합니다. 두 애플리케이션 경로와 UDP·TCP DNS를 명시적으로 허용합니다. 실습 밖의 CoreDNS에 도달하려면 네임스페이스 셀렉터가 필요합니다. NodeLocal DNSCache나 다른 레이블을 사용한다면 테스트 전에 DNS 규칙을 수정하세요.

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: tier-boundaries
spec:
  selector: all()
  types: [Ingress, Egress]
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
  egress:
  - action: Allow
    protocol: UDP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
EOF

# Allow policy propagation, then verify positive controls and the denied path.
POLICY_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp frontend backend 8080
  check_tcp backend database 5432
  if check_tcp frontend database 5432; then
    sleep 2
  else
    result=$?
    if [ "$result" -ne 42 ]; then
      printf '%s\n' 'DNS/exec failure is not proof of policy denial.' >&2
      exit 1
    fi
    # Database availability must still hold after the negative observation.
    check_tcp backend database 5432
    POLICY_VERIFIED=true
    break
  fi
done
[ "$POLICY_VERIFIED" = true ] || {
  printf '%s\n' 'Expected denial was not observed; inspect policy enforcement.' >&2
  exit 1
}
```
정책 전파는 비동기입니다. 타임아웃·DNS 실패·진단 도구 부재·DB 장애만으로 격리 성공을 판단하면 안 됩니다. 이 절차는 정상 기본 연결과 허용 대조군을 사용합니다. 관측이 다르면 다른 정책·경로를 조사하세요.

**6. 정리.** UID를 확인한 소유 네임스페이스만 삭제합니다. 테스트 워크로드·정책·Secret·임시 데이터가 삭제되며 클러스터 전체 Calico 설치는 제거하지 않습니다. 실습 후 로컬 비밀번호 파일도 정리하세요. 공유 CNI·RBAC 설정은 별도로 관리자가 검토한 롤백 대상이 아니라면 유지합니다.

```bash
CURRENT_NETWORK_UID=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get namespace "${NETWORK_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_NETWORK_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_NETWORK_UID" = "${NETWORK_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
    delete namespace "$NETWORK_NAMESPACE" --wait=true || exit 1
else
  printf '%s\n' 'Namespace UID changed; no deletion attempted.' >&2
  exit 1
fi
```

</details>

### 실습 2: EKS 클러스터에서 IRSA 및 S3 접근 구성

**시나리오:** 노드 역할 대신 IRSA로 한 워크로드에 기존 S3 버킷의 승인된 `training/` prefix 읽기 권한만 부여합니다. 실제 assumed-role 신원을 확인하고 의도적으로 자격 증명을 제공하지 않은 Pod와 비교합니다.

**선행조건:** Bash·jq·AWS CLI·eksctl·kubectl, 승인된 기존 EKS 클러스터, 새 네임스페이스와 IAM 역할의 관리 권한, 민감하지 않은 승인된 기존 S3 객체가 필요합니다. 이 상용 파티션 예제는 별도 고객 KMS 권한이 필요하지 않은 객체를 가정합니다. 버킷·KMS 정책, SCP, DNS, STS·S3 네트워크 경로는 추가 조건을 부과할 수 있습니다. S3 객체를 생성·수정·삭제하지 않습니다.


<details>
<summary>솔루션 보기</summary>

**1. 실습 범위와 OIDC 확인.** `EXAMPLE_CLUSTER`, `EXAMPLE_REGION`, `S3_BUCKET`, `S3_TEST_KEY`(`training/` 하위)를 설정합니다. OIDC provider는 공유 클러스터 인프라이므로 정리 시 삭제하지 않습니다. 네임스페이스 생성이나 provider 검증이 실패하면 중단하세요.

```bash
set -euo pipefail
umask 077
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```
**2. 고유한 제한 역할 생성.** 신뢰 정책에는 `aud=sts.amazonaws.com`과 정확한 네임스페이스·ServiceAccount의 `sub`가 모두 필요합니다. 역할 생성 실패 시 정책 연결을 중단하고 정리를 위해 불변 RoleId를 기록합니다.

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```
**3. 배포와 검증.** 테스트 실패 시 재시도 전에 IAM 전파를 고려하세요. 세 컨테이너는 객체 내용이나 자격 증명을 기록하지 않고 신원·prefix 목록 개수·객체 길이를 확인합니다. 신원은 새로 만든 역할과 일치해야 합니다. S3 성공만으로 판단하면 더 넓은 노드 역할의 권한을 오인할 수 있습니다.

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```
**4. 통제된 실패 대조군.** 새 네임스페이스의 기본 ServiceAccount에 IRSA annotation·EKS Pod Identity association이 없어야 하며 다른 자격 증명을 주입하지 않아야 합니다. 이 테스트 클라이언트의 IMDS fallback을 비활성화하고 정확히 자격 증명 부재 오류인지 확인합니다. 임의의 네트워크·인가 오류는 유효한 대조군 결과가 아닙니다.

```bash
# Controlled comparison: no IRSA, no Pod Identity association, no IMDS fallback.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg region "${EXAMPLE_REGION:?}" '
{
  apiVersion:"v1",kind:"Pod",
  metadata:{name:"no-role-check",namespace:$ns},
  spec:{
    automountServiceAccountToken:false,
    serviceAccountName:"default",
    nodeSelector:{"kubernetes.io/os":"linux"},
    restartPolicy:"Never",
    containers:[{
      name:"identity",image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",
      command:["aws"],args:["--region",$region,"sts","get-caller-identity"],
      env:[{name:"AWS_EC2_METADATA_DISABLED",value:"true"}],
      resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
    }]
  }
}' > "${IRSA_LAB_DIR:?}/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create -f "$IRSA_LAB_DIR/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Failed pod/no-role-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get pod no-role-check -o json > "$IRSA_LAB_DIR/negative-status.json" || exit 1
jq -e '.status.containerStatuses[] | select(.name=="identity") |
  .state.terminated.exitCode == 255' "$IRSA_LAB_DIR/negative-status.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs no-role-check -c identity > "$IRSA_LAB_DIR/negative-log.txt" || exit 1
grep -F 'Unable to locate credentials' "$IRSA_LAB_DIR/negative-log.txt" >/dev/null || {
  printf '%s\n' 'Unexpected failure: inspect the saved log; do not claim isolation.' >&2
  exit 1
}
```
이는 자격 증명 공급자 비교이며 임의의 Pod가 IMDS에 접근할 수 없거나 컨테이너가 보안 경계라는 증명이 아닙니다. 노드 자격 증명 접근은 별도로 제한하세요. IRSA는 projected web-identity token과 STS 임시 자격 증명을 사용하며 호환 SDK가 갱신합니다. 모든 `AWS_*` 환경변수나 토큰 파일을 출력하면 안 됩니다.

**5. 소유 리소스만 정리.** 기록된 네임스페이스 UID와 IAM RoleId를 보존합니다. 아래 보호 절차는 실습 네임스페이스·inline 정책·고유 역할만 제거하며 S3 버킷·객체, 공유 OIDC provider와 클러스터는 유지합니다. 설정이 부분적으로만 성공했다면 `ownership.json`을 보고 실제 기록된 리소스만 정리하세요.

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

</details>

## 고급 주제

다음은 Amazon EKS 클러스터 생성에 관한 고급 주제에 대한 질문입니다. 이 섹션은 EKS 클러스터 생성의 심화 개념과 모범 사례에 대한 이해를 테스트합니다.

1. IPv4 prefix delegation이 보장하지 않는 주장은 무엇인가요?
   * A) prefix가 ENI 주소 슬롯을 사용함
   * B) 노드당 더 많은 IP 용량을 수용할 수 있음
   * C) 모든 애플리케이션이 더 빨리 준비됨
   * D) 연속된 서브넷 블록이 필요함

<details>
<summary>정답 보기</summary>

**정답: C) 모든 애플리케이션이 더 빨리 준비됨**

Prefix delegation은 주소 할당 지연을 줄일 수 있습니다. 기존 ENI에 prefix를 추가하면 일부 ENI 생성·연결 작업을 피할 수 있으며 AWS도 이 이점을 설명합니다. 따라서 시작 시간을 줄일 수 없고 반드시 라우팅 오버헤드를 추가한다는 기존 설명은 잘못되었습니다.

종단 간 Pod 준비 시간은 스케줄링·노드 시작·이미지 pull·볼륨 연결·초기화·프로브·애플리케이션 시작에도 영향을 받습니다. 여기에는 전후 비교 벤치마크가 제공되지 않았고 이번 감사에서도 실행하지 않았습니다. 고정된 지연 개선을 추정하거나 느려진 원인을 만들어 내면 안 됩니다.

IPv4 `/28` 하나는 보조 주소 슬롯 하나와 연속된 서브넷 주소 16개를 소비합니다. `maxPods`·컴퓨팅 리소스·서브넷 공간 내에서 노드별 IP 용량을 늘리며, CIDR 확장이나 할당 주소 감소를 보장하지는 않습니다. Warm pool 설정은 여유 주소 소비와 할당 준비 사이의 균형입니다.

기본 문제 5의 선행조건과 새 노드 그룹 전환 절차를 사용하세요. 단편화를 확인하고 호환 CNI를 구성한 후 계산된 노드 용량을 검증하며, 여유 용량과 PDB를 고려한 드레인으로 이전합니다. 기존 Pod 전체 재시작만으로 전환 계획이 완성되지는 않습니다.

</details>

2. Cluster Autoscaler를 사용하는 혼합 인스턴스 관리형 노드 그룹에서 잘못된 방법은 무엇인가요?
   * A) CPU·메모리·GPU 크기가 유사한 유형 사용
   * B) 이미지와 AZ 호환성 확인
   * C) Spot과 On-Demand 그룹 분리
   * D) 오토스케일러가 모든 유형을 시뮬레이션하므로 임의 크기 혼합

<details>
<summary>정답 보기</summary>

**정답: D) 오토스케일러가 모든 유형을 시뮬레이션하므로 임의 크기 혼합**

다양한 인스턴스 후보는 특히 Spot의 용량 선택지를 늘릴 수 있지만 오토스케일러의 스케줄링 모델을 따라야 합니다. Cluster Autoscaler는 혼합 그룹의 첫 인스턴스 유형으로 시뮬레이션하므로 CPU·메모리·GPU 크기가 같은 후보를 사용해야 합니다. 작은 대안은 Pod를 Pending 상태로 남길 수 있고 큰 대안은 용량을 낭비할 수 있습니다. 이름이 비슷해도 크기가 같지는 않습니다. 예를 들어 `c5n.large`와 `c5.large`의 메모리는 다릅니다.

관리형 노드 그룹의 capacity type은 하나입니다. On-Demand 기본 용량과 Spot 확장은 **별도 그룹**으로 구성하세요. 여러 `instanceTypes`를 나열해도 한 관리형 그룹에 구매 옵션이 섞이지 않습니다. 관리형 Spot 할당 전략은 EKS가 선택하며 `spotAllocationStrategy`는 eksctl의 `managedNodeGroups` 지원 필드가 아닙니다.

다음은 유사한 `m5` 계열 크기를 유지한 예제입니다. 미사용 그룹 이름을 사용하는 검토된 기존 클러스터의 노드 그룹 구성이며 가격·성능이나 용량 보장이 아닙니다. AZ별 제공 여부와 이미지·드라이버·스토리지 호환성을 확인하세요:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: on-demand-base
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  spot: false
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
- name: spot-scaling
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large, m5n.large]
  privateNetworking: true
  spot: true
  desiredCapacity: 0
  minSize: 0
  maxSize: 20
```
서로 다른 워크로드 크기는 메모리·컴퓨팅·범용 인스턴스를 하나의 자동 확장 그룹에 섞는 대신 분리합니다:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: compute-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [c5.2xlarge, c5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: compute}
  taints:
  - {key: workload-type, value: compute, effect: NoSchedule}
- name: memory-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [r5.2xlarge, r5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: memory}
  taints:
  - {key: workload-type, value: memory, effect: NoSchedule}
```
전용 풀을 반드시 사용해야 하는 워크로드에는 일치하는 톨러레이션과 선택기·어피니티가 모두 필요합니다. 레이블만으로 배치되지 않으며 테인트는 테넌트 보안 경계가 아닙니다. 0에서 확장할 때의 검색 설정, 데몬 부담, 중단 처리, 스토리지 영속성과 모든 후보 유형의 테스트를 고려하세요. 다양성은 모니터링·문제 해결 작업을 늘릴 수 있으며 관리 단순화나 비용 감소가 자동으로 따라오지는 않습니다.

</details>

3. 기존 그룹을 제거하기 전에 별도의 교체 노드 그룹을 만드는 전략은 무엇인가요?
   * A) 추적하지 않는 호스트 패키지 업데이트
   * B) Blue/green 마이그레이션
   * C) 모든 노드 동시 삭제
   * D) 클러스터 표시 이름만 변경

<details>
<summary>정답 보기</summary>

**정답: B) Blue/green 마이그레이션**

Blue/green은 별도의 교체 노드 그룹을 만들고 검증 후 워크로드를 이전합니다. 기존 그룹과 호환되는 애플리케이션·데이터 상태가 남아 있는 동안 롤백 선택지를 유지할 수 있습니다. 같은 클러스터의 두 그룹은 제어 플레인과 다른 의존성을 공유하므로 완전한 격리나 무중단 보장이 아닙니다.

| 전략 | 이점 | 중요한 한계 |
| --- | --- | --- |
| Blue/green | 최종 제거 전 교체 용량 검증 | 추가 비용·용량 필요; 기존 노드와 호환 상태가 있어야 롤백 가능 |
| 관리형 롤링 업데이트 | EKS가 점진적 노드 교체 조정 | `DEFAULT`는 일시적 추가 노드 사용; PDB·용량 오류로 정체 가능 |
| Canary | 별도의 작은 워크로드·그룹부터 시험 | 실제 워크로드·트래픽 범위를 제한해야 하며 검증·라우팅 작업 추가 |
| 호스트 패키지 직접 변경 | 개별 호스트 변경 | AMI와 drift 발생; 무조건적인 SSH·yum 명령 대신 검토한 교체 이미지 수명주기 사용 |

**교체 그룹 예제:** 기존 클러스터와 미사용 그룹 이름을 확인한 뒤 파일을 검토하고 `eksctl create nodegroup -f green-nodegroup.yaml`을 사용합니다. 먼저 AL2023·아키텍처 호환성, 애드온, egress, IP 공간, 쿼터와 스토리지 토폴로지를 확인하세요.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: green-nodegroup
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 3
  maxSize: 5
  labels:
    audit.example.com/pool: green
```
**실제 카나리아는 별도 Deployment를 사용합니다:** 아래는 전용 `update-lab` 네임스페이스의 최소 HTTP 확인용 워크로드이며 기존 Service에 실수로 포함되지 않도록 고유 레이블을 사용합니다. 애플리케이션 호환성을 주장하려면 실제 애플리케이션의 검토된 카나리아로 바꾸어야 합니다. 주 Deployment의 노드 선택기를 수정하면 **모든** 복제본이 롤아웃되므로 제한된 카나리아가 아닙니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
  namespace: update-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: my-app-canary}
  template:
    metadata:
      labels: {app: my-app-canary}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        audit.example.com/pool: green
      containers:
      - name: web
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet: {path: /, port: 80}
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
```
검토한 관찰 기간 동안 준비 상태, API·CNI·DNS, 애플리케이션 오류, 리소스 압박, 영속 볼륨과 대표 트래픽을 검증합니다. 노드 레이블이 트래픽을 전환하는 것은 아니므로 라우팅을 명시적으로 관리하세요. 교체 용량과 워크로드·데이터 동작을 검증한 후 확인된 기존 노드를 하나씩 드레인합니다:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
드레인이 막히면 `--force`나 emptyDir 자동 삭제 대신 원인을 조사합니다. 이전한 워크로드와 상태를 모두 확인한 후 별도의 최종 삭제를 수행합니다:

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
관리형 롤링 방식은 기본 문제 9의 `update-nodegroup-config` 작업을 완료한 후 `update-nodegroup-version`을 제출하고 반환된 업데이트 ID를 추적합니다. 관리형 그룹 리소스는 유지되면서 EC2 노드는 교체될 수 있습니다. 기존 용량을 삭제했거나 데이터가 비호환 상태로 바뀌었다면 “즉각적인 롤백”은 더 이상 가능하지 않습니다.

</details>

4. 관리형 ASG를 제어하는 Cluster Autoscaler와 충돌할 수 있는 작업은 무엇인가요?
   * A) 검색 태그 검토
   * B) 관측에 따른 스캔 주기 조정
   * C) 정확한 Pod 리소스 요청 사용
   * D) 같은 desired capacity를 독립적으로 바꾸는 다른 정책 추가

<details>
<summary>정답 보기</summary>

**정답: D) 같은 desired capacity를 독립적으로 바꾸는 다른 정책 추가**

Cluster Autoscaler는 평균 EC2 CPU만 보는 대신 스케줄링 요청에 따라 노드 그룹 용량을 제어합니다. 같은 desired capacity를 바꾸는 ASG 대상 추적·예측 정책은 제어 루프와 충돌하고 기대한 Kubernetes 드레인 절차를 우회할 수 있습니다. “최적화”를 위해 원하는 용량을 직접 2로 재설정하면 안 됩니다.

**유용한 제어:**

* 스캔 주기는 반응 시간과 API 부하를 함께 고려합니다. 공식 기본값은 10초이며 30초는 실측 최적값이 아닌 테스트 예시입니다. 프로비저닝 타임아웃도 실제 노드 시작 동작에 맞춰야 합니다.
* 검토한 ASG 검색 태그와 태그로 제한한 IAM을 사용합니다. 태그는 대상 그룹을 식별하며 권한이나 확장 알고리즘을 제공하지는 않습니다.
* requests·레이블·테인트를 실제 용량과 맞춥니다. 단일 인스턴스 유형도 적절할 수 있으며 가용성·Spot 요구가 있다면 같은 크기의 다양한 유형이 유용합니다(고급 문제 2).
* 우선순위는 의도적으로 사용합니다. 선점은 가용성 보장이 아니며 낮은 우선순위 워크로드를 중단시킬 수 있습니다. admission·워크로드 정책을 평가한 후 필요한 Pod의 `priorityClassName`으로 다음 클래스를 지정하세요:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**오버프로비저닝:** 선점 가능한 낮은 우선순위 Pod의 requests로 여유 용량을 확보합니다. 이 예제는 Cluster Autoscaler의 expendable-Pod cutoff가 `-5`보다 낮아야 하며(예: `-10`), 애플리케이션 Pod의 우선순위는 더 높아야 합니다. 그렇지 않으면 예약 Pod가 의도한 용량 보충을 유발하지 않을 수 있습니다. 전용 네임스페이스와 미사용 PriorityClass 이름을 사용하세요:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-overprovisioning
value: -5
globalDefault: false
description: Temporary spare capacity for an autoscaling lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: autoscaling-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: overprovisioning}
  template:
    metadata:
      labels: {app: overprovisioning}
    spec:
      priorityClassName: audit-overprovisioning
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: reserve
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command: [sleep, '86400']
        resources:
          requests: {cpu: 1000m, memory: 1000Mi}
          limits: {cpu: 1000m, memory: 1000Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
이는 요청 용량 1 CPU·1000Mi를 확보하며 미리 초기화된 애플리케이션 상태가 아니고 노드 비용이 발생합니다. 이미지 pull·볼륨 연결·애플리케이션 초기화를 없애지 않습니다. 관측한 수요에 맞춰 크기를 정하고 테스트 후 소유한 예약 Deployment·PriorityClass를 제거하세요.

기존의 불완전한 v1.23 Deployment 대신 기본 문제 10의 완전하게 렌더링된 Cluster Autoscaler 구성을 사용합니다. Karpenter는 별도로 관리하는 용량의 대안이며 NodePool이 유효하고 권한이 구성된 EC2NodeClass를 참조해야 합니다. KEDA·HPA는 워크로드 복제본을 조절하여 두 노드 오토스케일러에 수요를 만들 수 있습니다. 같은 리소스에 모든 확장 기능을 켜기보다 제어 루프의 상호작용을 검증하세요.

</details>

5. EKS 노드 그룹의 일반적인 보안 모범 사례가 아닌 것은 무엇인가요?
   * A) IMDSv2 요구와 메타데이터 접근 검토
   * B) 최소 권한 IAM 사용
   * C) 모든 노드에 퍼블릭 IP 할당
   * D) 보안 그룹 규칙 검토

<details>
<summary>정답 보기</summary>

**정답: C) 모든 노드에 퍼블릭 IP 할당**

모든 노드에 퍼블릭 IP를 주는 것은 일반적인 보안 모범 사례가 아닙니다. 프라이빗 서브넷은 직접적인 인터넷 노출을 줄이지만 라우팅·보안 그룹·IAM·소프트웨어 유지 관리·워크로드 제어도 중요합니다.

**노드 신원과 메타데이터:** eksctl의 지원 필드인 `disableIMDSv1`으로 IMDSv2를 요구합니다. 중첩된 `metadataOptions` 객체는 eksctl 관리형 노드 그룹 필드가 아니며, EC2 MetadataOptions의 커스텀 설정은 검토한 Launch Template에 둡니다. IMDSv2는 일부 SSRF 경로를 완화하지만 모든 Pod, 특히 hostNetwork Pod의 노드 자격 증명 접근을 막지는 않습니다. 워크로드 신원·호스트 의존성과 함께 메타데이터 접근을 별도 검토하세요.

**최소 권한과 루트 볼륨 암호화:** 아래 기존 클러스터의 노드 그룹 예제는 CNI가 이미 자체 IRSA·Pod Identity 권한을 가진다고 가정합니다. EBS CSI·로그 수집기·애플리케이션에도 별도 검토한 역할이 필요합니다. 모든 노드에 그 권한을 넓게 붙이는 것은 최소 권한과 모순됩니다.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: secure-nodes
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  disableIMDSv1: true
  volumeEncrypted: true
  iam:
    attachPolicyARNs:
    - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
    - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
```
EBS 암호화는 Kubernetes API 데이터와 다른 계층을 보호합니다. EKS 1.28 이상은 모든 Kubernetes API 데이터를 기본 envelope encryption으로 암호화합니다. 고객 관리 KMS 키는 선택 사항이며 추가 grant·권한과 키 수명주기 책임이 따릅니다. 클러스터의 키 비활성화·삭제를 일상적인 정리 작업에 포함하지 마세요.

**네트워크 설계:** 프라이빗 API 엔드포인트는 관리자·노드의 라우팅된 접근 경로가 필요합니다. 퍼블릭 API 접근 제한은 클러스터 SG ingress 규칙이 아닌 `publicAccessCidrs`로 설정합니다. TCP 443·TCP 10250·TCP/UDP 53과 워크로드별 경로에 대해 방향과 피어 그룹을 포함한 AWS의 전체 클러스터·노드 SG 요구를 검토하세요. ingress 포트 두 개만으로 노드 네트워킹 구성이 완성되지 않습니다.

프라이빗 IPv4 인터넷 egress에는 NAT가 필요할 수 있지만 VPC Endpoint·네이티브 IPv6는 경로가 다릅니다. ingress는 로드 밸런서 또는 승인된 연결 네트워크에서 올 수 있습니다. 프라이빗 서브넷만으로 완전한 격리나 규제 준수를 입증하지는 않습니다.

**컨테이너 제어:** non-root·읽기 전용 실행과 호환되는 워크로드를 사용합니다. 다음 컨트롤러 관리 진단 Pod는 **새 전용** `security-lab` 네임스페이스에서 실행되며 네트워크나 쓰기 가능한 루트가 필요하지 않습니다:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-pod
  namespace: security-lab
spec:
  replicas: 1
  selector:
    matchLabels: &id001
      app: secure-pod
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: secure-container
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sh
        - -c
        - echo read-only-lab; sleep 3600
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 32Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```
실제로 집행되는 deny 정책은 전용 네임스페이스에서 시험할 수 있습니다. 실제 워크로드에는 필요한 DNS·애플리케이션 허용 규칙을 먼저 추가하세요:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
**로깅과 탐지:** 제어 플레인 CloudWatch 로그는 다섯 유형을 설정할 수 있습니다:

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```
반환된 업데이트가 성공할 때까지 기다린 후 실제 로그 전달과 보존 설정을 확인합니다. 이 설정이 모든 컨테이너의 애플리케이션 로그를 수집하는 것은 아닙니다. GuardDuty의 EKS 감사 로그 보호와 Runtime Monitoring은 별도 설정·범위를 가진 기능이며, 제어 플레인 로그 활성화만으로 런타임 위협 탐지를 구성하는 것은 아닙니다.

</details>


## 참고 자료

* [EKS prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [EKS maxPods and prefix procedure](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [Subnet route table association](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [CoreDNS managed add-on](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [CoreDNS cache](https://coredns.io/plugins/cache/)
* [CoreDNS reload](https://coredns.io/plugins/reload/)
* [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [EKS managed node updates](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [Calico on EKS](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
