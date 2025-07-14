# EKS 네트워킹 - 1부: 기본 개념 및 VPC 구성

## 개요

Amazon EKS의 네트워킹은 Kubernetes 클러스터의 통신을 관리하는 핵심 구성 요소입니다. 이 문서에서는 EKS 네트워킹의 기본 개념, VPC 구성, 서브넷 설계, 보안 그룹 구성 등을 다룹니다.

## EKS 네트워킹 아키텍처

EKS 네트워킹 아키텍처는 다음과 같은 구성 요소로 이루어져 있습니다:

1. **VPC(Virtual Private Cloud)**: EKS 클러스터가 실행되는 격리된 네트워크 환경
2. **서브넷**: VPC 내의 IP 주소 범위를 나누는 단위
3. **라우팅 테이블**: 네트워크 트래픽의 경로를 결정하는 규칙 집합
4. **인터넷 게이트웨이**: VPC와 인터넷 간의 통신을 가능하게 하는 구성 요소
5. **NAT 게이트웨이**: 프라이빗 서브넷의 리소스가 인터넷에 액세스할 수 있게 하는 구성 요소
6. **보안 그룹**: 인스턴스 수준의 가상 방화벽
7. **네트워크 ACL**: 서브넷 수준의 가상 방화벽
8. **CNI(Container Network Interface)**: 컨테이너 네트워킹을 관리하는 플러그인

### EKS 네트워킹 흐름

EKS 클러스터에서 네트워크 트래픽은 다음과 같이 흐릅니다:

1. **포드 간 통신**: 동일한 노드 또는 다른 노드의 포드 간 통신
2. **포드와 서비스 간 통신**: 포드와 클러스터 내 서비스 간 통신
3. **클러스터 내부와 외부 간 통신**: 클러스터 내부 리소스와 외부 리소스 간 통신
4. **컨트롤 플레인과 노드 간 통신**: EKS 컨트롤 플레인과 워커 노드 간 통신

```
                                   +-------------------+
                                   |                   |
                                   |  인터넷 게이트웨이   |
                                   |                   |
                                   +--------+----------+
                                            |
                                            v
+-------------------+             +-------------------+             +-------------------+
|                   |             |                   |             |                   |
|  NAT 게이트웨이     +<-----------+  퍼블릭 서브넷      |             |  EKS 컨트롤 플레인  |
|                   |             |                   |             |                   |
+--------+----------+             +-------------------+             +-------------------+
         |                                                                   ^
         v                                                                   |
+-------------------+             +-------------------+                      |
|                   |             |                   |                      |
|  프라이빗 서브넷     +<-----------+  워커 노드         +----------------------+
|                   |             |                   |
+-------------------+             +-------------------+
```

## VPC 요구 사항

EKS 클러스터를 위한 VPC는 다음 요구 사항을 충족해야 합니다:

1. **서브넷**: 최소 2개 이상의 가용 영역에 서브넷이 있어야 함
2. **IP 주소**: 충분한 수의 IP 주소를 제공해야 함
3. **DNS 호스트 이름**: DNS 호스트 이름 및 DNS 확인이 활성화되어 있어야 함
4. **인터넷 액세스**: 노드가 인터넷에 액세스할 수 있어야 함(NAT 게이트웨이 또는 인터넷 게이트웨이를 통해)

### VPC CIDR 계획

VPC CIDR 블록을 계획할 때 고려해야 할 사항:

1. **클러스터 크기**: 예상되는 노드 및 포드 수
2. **IP 주소 요구 사항**: 각 노드 및 포드에 필요한 IP 주소 수
3. **향후 확장**: 향후 확장을 위한 여유 공간
4. **기존 네트워크와의 통합**: 기존 네트워크와의 중복 방지

일반적인 VPC CIDR 블록 크기:
- 소규모 클러스터: /24 (256개 IP 주소)
- 중간 규모 클러스터: /20 (4,096개 IP 주소)
- 대규모 클러스터: /16 (65,536개 IP 주소)

### 서브넷 설계

EKS 클러스터를 위한 서브넷 설계 모범 사례:

1. **퍼블릭 서브넷**: 인터넷 게이트웨이에 직접 연결된 서브넷
   - 용도: 퍼블릭 로드 밸런서, NAT 게이트웨이, 바스티온 호스트
   - 일반적인 크기: /24 (256개 IP 주소)

2. **프라이빗 서브넷**: 인터넷 게이트웨이에 직접 연결되지 않은 서브넷
   - 용도: EKS 워커 노드, 내부 로드 밸런서
   - 일반적인 크기: /22 (1,024개 IP 주소)

3. **가용 영역 분산**: 서브넷을 여러 가용 영역에 분산
   - 최소 2개 이상의 가용 영역 사용
   - 각 가용 영역에 퍼블릭 및 프라이빗 서브넷 배치

예시 서브넷 설계:

| 서브넷 유형 | 가용 영역 | CIDR 블록 | 용도 |
|------------|---------|----------|------|
| 퍼블릭 | us-west-2a | 10.0.0.0/24 | 로드 밸런서, NAT 게이트웨이 |
| 퍼블릭 | us-west-2b | 10.0.1.0/24 | 로드 밸런서, NAT 게이트웨이 |
| 프라이빗 | us-west-2a | 10.0.2.0/22 | EKS 워커 노드 |
| 프라이빗 | us-west-2b | 10.0.6.0/22 | EKS 워커 노드 |

### 서브넷 태그

EKS는 서브넷에 특정 태그를 사용하여 리소스를 자동으로 검색합니다:

1. **퍼블릭 서브넷 태그**:
   - `kubernetes.io/role/elb`: 값을 `1`로 설정하여 인터넷 연결 로드 밸런서에 사용
   - `kubernetes.io/cluster/<cluster-name>`: 값을 `shared` 또는 `owned`로 설정

2. **프라이빗 서브넷 태그**:
   - `kubernetes.io/role/internal-elb`: 값을 `1`로 설정하여 내부 로드 밸런서에 사용
   - `kubernetes.io/cluster/<cluster-name>`: 값을 `shared` 또는 `owned`로 설정

예시:
```bash
aws ec2 create-tags \
  --resources subnet-xxxxxxxxxxxxxxxxx \
  --tags Key=kubernetes.io/cluster/my-cluster,Value=shared Key=kubernetes.io/role/elb,Value=1
```

## VPC 생성 및 구성

### AWS Management Console을 사용한 VPC 생성

1. AWS Management Console에 로그인하고 VPC 서비스로 이동합니다.
2. "VPC 생성" 버튼을 클릭합니다.
3. "VPC 및 기타" 옵션을 선택합니다.
4. 다음 정보를 입력합니다:
   - 이름 태그 자동 생성: `EKS-VPC`
   - IPv4 CIDR 블록: `10.0.0.0/16`
   - IPv6 CIDR 블록: `없음`
   - 테넌시: `기본값`
   - 가용 영역 수: `2`
   - 퍼블릭 서브넷 수: `2`
   - 프라이빗 서브넷 수: `2`
   - NAT 게이트웨이: `가용 영역당 1개`
   - VPC 엔드포인트: `없음`
5. "VPC 생성" 버튼을 클릭합니다.

### AWS CLI를 사용한 VPC 생성

```bash
# VPC 생성
vpc_id=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=EKS-VPC}]' \
  --query Vpc.VpcId \
  --output text)

# DNS 호스트 이름 활성화
aws ec2 modify-vpc-attribute \
  --vpc-id $vpc_id \
  --enable-dns-hostnames

# 인터넷 게이트웨이 생성
igw_id=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=EKS-IGW}]' \
  --query InternetGateway.InternetGatewayId \
  --output text)

# 인터넷 게이트웨이를 VPC에 연결
aws ec2 attach-internet-gateway \
  --internet-gateway-id $igw_id \
  --vpc-id $vpc_id

# 퍼블릭 서브넷 생성
pub_subnet_1_id=$(aws ec2 create-subnet \
  --vpc-id $vpc_id \
  --cidr-block 10.0.0.0/24 \
  --availability-zone us-west-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Public-1},{Key=kubernetes.io/role/elb,Value=1},{Key=kubernetes.io/cluster/my-cluster,Value=shared}]' \
  --query Subnet.SubnetId \
  --output text)

pub_subnet_2_id=$(aws ec2 create-subnet \
  --vpc-id $vpc_id \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-west-2b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Public-2},{Key=kubernetes.io/role/elb,Value=1},{Key=kubernetes.io/cluster/my-cluster,Value=shared}]' \
  --query Subnet.SubnetId \
  --output text)

# 프라이빗 서브넷 생성
priv_subnet_1_id=$(aws ec2 create-subnet \
  --vpc-id $vpc_id \
  --cidr-block 10.0.2.0/22 \
  --availability-zone us-west-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Private-1},{Key=kubernetes.io/role/internal-elb,Value=1},{Key=kubernetes.io/cluster/my-cluster,Value=shared}]' \
  --query Subnet.SubnetId \
  --output text)

priv_subnet_2_id=$(aws ec2 create-subnet \
  --vpc-id $vpc_id \
  --cidr-block 10.0.6.0/22 \
  --availability-zone us-west-2b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Private-2},{Key=kubernetes.io/role/internal-elb,Value=1},{Key=kubernetes.io/cluster/my-cluster,Value=shared}]' \
  --query Subnet.SubnetId \
  --output text)

# 퍼블릭 라우팅 테이블 생성
pub_rtb_id=$(aws ec2 create-route-table \
  --vpc-id $vpc_id \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=EKS-Public-RTB}]' \
  --query RouteTable.RouteTableId \
  --output text)

# 인터넷 게이트웨이로 가는 경로 추가
aws ec2 create-route \
  --route-table-id $pub_rtb_id \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $igw_id

# 퍼블릭 서브넷을 퍼블릭 라우팅 테이블에 연결
aws ec2 associate-route-table \
  --route-table-id $pub_rtb_id \
  --subnet-id $pub_subnet_1_id

aws ec2 associate-route-table \
  --route-table-id $pub_rtb_id \
  --subnet-id $pub_subnet_2_id

# NAT 게이트웨이용 탄력적 IP 할당
eip_1_id=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=EKS-NAT-1-EIP}]' \
  --query AllocationId \
  --output text)

eip_2_id=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=EKS-NAT-2-EIP}]' \
  --query AllocationId \
  --output text)

# NAT 게이트웨이 생성
nat_1_id=$(aws ec2 create-nat-gateway \
  --subnet-id $pub_subnet_1_id \
  --allocation-id $eip_1_id \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=EKS-NAT-1}]' \
  --query NatGateway.NatGatewayId \
  --output text)

nat_2_id=$(aws ec2 create-nat-gateway \
  --subnet-id $pub_subnet_2_id \
  --allocation-id $eip_2_id \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=EKS-NAT-2}]' \
  --query NatGateway.NatGatewayId \
  --output text)

# NAT 게이트웨이가 활성화될 때까지 대기
echo "Waiting for NAT gateways to become available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $nat_1_id $nat_2_id

# 프라이빗 라우팅 테이블 생성
priv_rtb_1_id=$(aws ec2 create-route-table \
  --vpc-id $vpc_id \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=EKS-Private-RTB-1}]' \
  --query RouteTable.RouteTableId \
  --output text)

priv_rtb_2_id=$(aws ec2 create-route-table \
  --vpc-id $vpc_id \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=EKS-Private-RTB-2}]' \
  --query RouteTable.RouteTableId \
  --output text)

# NAT 게이트웨이로 가는 경로 추가
aws ec2 create-route \
  --route-table-id $priv_rtb_1_id \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $nat_1_id

aws ec2 create-route \
  --route-table-id $priv_rtb_2_id \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $nat_2_id

# 프라이빗 서브넷을 프라이빗 라우팅 테이블에 연결
aws ec2 associate-route-table \
  --route-table-id $priv_rtb_1_id \
  --subnet-id $priv_subnet_1_id

aws ec2 associate-route-table \
  --route-table-id $priv_rtb_2_id \
  --subnet-id $priv_subnet_2_id
```

### Terraform을 사용한 VPC 생성

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 3.0"

  name = "eks-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b"]
  private_subnets = ["10.0.2.0/22", "10.0.6.0/22"]
  public_subnets  = ["10.0.0.0/24", "10.0.1.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  one_nat_gateway_per_az = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/cluster/my-cluster" = "shared"
    "kubernetes.io/role/elb"           = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/my-cluster" = "shared"
    "kubernetes.io/role/internal-elb"  = "1"
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

## 보안 그룹 구성

EKS 클러스터에는 다음과 같은 보안 그룹이 필요합니다:

1. **클러스터 보안 그룹**: EKS 컨트롤 플레인과 워커 노드 간의 통신을 허용
2. **노드 보안 그룹**: 워커 노드 간의 통신을 허용

### 클러스터 보안 그룹 구성

```bash
# 클러스터 보안 그룹 생성
cluster_sg_id=$(aws ec2 create-security-group \
  --group-name EKS-Cluster-SG \
  --description "Security group for EKS cluster" \
  --vpc-id $vpc_id \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=EKS-Cluster-SG}]' \
  --query GroupId \
  --output text)

# 클러스터 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id $cluster_sg_id \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# 노드 보안 그룹 생성
node_sg_id=$(aws ec2 create-security-group \
  --group-name EKS-Node-SG \
  --description "Security group for EKS worker nodes" \
  --vpc-id $vpc_id \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=EKS-Node-SG}]' \
  --query GroupId \
  --output text)

# 노드 보안 그룹 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id $node_sg_id \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# 노드 간 통신 허용
aws ec2 authorize-security-group-ingress \
  --group-id $node_sg_id \
  --source-group $node_sg_id \
  --protocol -1

# 노드에서 클러스터로의 통신 허용
aws ec2 authorize-security-group-ingress \
  --group-id $cluster_sg_id \
  --source-group $node_sg_id \
  --protocol tcp \
  --port 443

# 클러스터에서 노드로의 통신 허용
aws ec2 authorize-security-group-ingress \
  --group-id $node_sg_id \
  --source-group $cluster_sg_id \
  --protocol tcp \
  --port 10250
```

## VPC 엔드포인트

프라이빗 서브넷에 있는 EKS 노드가 인터넷에 액세스하지 않고도 AWS 서비스에 액세스할 수 있도록 VPC 엔드포인트를 구성할 수 있습니다:

```bash
# S3 게이트웨이 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id $vpc_id \
  --service-name com.amazonaws.us-west-2.s3 \
  --route-table-ids $priv_rtb_1_id $priv_rtb_2_id \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=S3-Gateway-Endpoint}]'

# ECR API 인터페이스 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id $vpc_id \
  --service-name com.amazonaws.us-west-2.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids $priv_subnet_1_id $priv_subnet_2_id \
  --security-group-ids $node_sg_id \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ECR-API-Endpoint}]'

# ECR DKR 인터페이스 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id $vpc_id \
  --service-name com.amazonaws.us-west-2.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids $priv_subnet_1_id $priv_subnet_2_id \
  --security-group-ids $node_sg_id \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=ECR-DKR-Endpoint}]'

# EKS 인터페이스 엔드포인트 생성
aws ec2 create-vpc-endpoint \
  --vpc-id $vpc_id \
  --service-name com.amazonaws.us-west-2.eks \
  --vpc-endpoint-type Interface \
  --subnet-ids $priv_subnet_1_id $priv_subnet_2_id \
  --security-group-ids $node_sg_id \
  --private-dns-enabled \
  --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=EKS-Endpoint}]'
```

## 결론

이 문서에서는 EKS 네트워킹의 기본 개념과 VPC 구성에 대해 알아보았습니다. 적절한 VPC 설계는 EKS 클러스터의 성능, 보안 및 확장성에 중요한 역할을 합니다. 다음 부분에서는 EKS의 서비스 및 로드 밸런싱, 네트워크 정책에 대해 알아보겠습니다.
