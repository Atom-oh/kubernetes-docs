# 네트워크 구성

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2026년 2월 23일

이 문서에서는 EKS Hybrid Nodes 환경에서 필요한 CIDR 요구 사항, 방화벽 포트, AWS 엔드포인트 접근, 보안 그룹 구성, DNS 구성을 다룹니다.

## 네트워크 아키텍처 개요

다음 다이어그램은 VPC 구성, Transit Gateway 라우팅, 원격 CIDR, 방화벽 규칙을 포함한 EKS Hybrid Nodes의 전체 네트워크 토폴로지를 보여줍니다.

![EKS Hybrid Nodes 네트워크 사전 요구 사항](../../assets/aws-official-diagrams/hybrid-prereq-diagram.png)

### VPC 네트워크 허브 개념

EKS Hybrid Nodes 환경에서 VPC는 하이브리드 노드와 컨트롤 플레인 간의 **네트워크 허브** 역할을 합니다.

- **ENI 배치**: EKS 컨트롤 플레인은 VPC 서브넷에 ENI(Elastic Network Interface)를 배치합니다. 이 ENI들이 컨트롤 플레인과 하이브리드 노드 간의 통신 엔드포인트입니다.
- **트래픽 경로**: 컨트롤 플레인과 하이브리드 노드 간의 모든 트래픽은 이 ENI를 통해 흐릅니다. API 서버 요청, kubelet 통신, 웹훅 호출 등 모든 제어 평면 트래픽이 VPC ENI를 경유합니다.
- **ENI IP 변경 가능성**: 클러스터 업데이트(버전 업그레이드 등) 시 ENI가 삭제되고 재생성될 수 있으며, 이때 ENI IP 주소가 변경될 수 있습니다. 방화벽 규칙에서 개별 IP 대신 서브넷 CIDR 범위를 사용하면 이러한 변경에 유연하게 대응할 수 있습니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│  ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │  EKS Control     │    │              VPC                  │   │
│  │     Plane        │◄──►│  ┌────────┐  ┌────────┐          │   │
│  │                  │    │  │  ENI   │  │  ENI   │          │   │
│  └──────────────────┘    │  │10.0.1.x│  │10.0.2.x│          │   │
│                          │  └────┬───┘  └────┬───┘          │   │
│                          └───────┼───────────┼──────────────┘   │
└──────────────────────────────────┼───────────┼──────────────────┘
                                   │           │
                           VPN / Direct Connect
                                   │           │
┌──────────────────────────────────┼───────────┼──────────────────┐
│                          On-Premises                             │
│                    ┌─────────────┴───────────┴─────────────┐    │
│                    │         Hybrid Nodes                   │    │
│                    │   ┌─────────┐    ┌─────────┐          │    │
│                    │   │  Node   │    │  Node   │          │    │
│                    │   │ kubelet │    │ kubelet │          │    │
│                    │   └─────────┘    └─────────┘          │    │
│                    └───────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## CIDR 범위 요구 사항

온프레미스 노드 및 파드 CIDR은 다음 조건을 충족해야 합니다:

- **RFC-1918 범위** 내에 있어야 합니다: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- 다음과 **겹치지 않아야** 합니다:
  - 서로 다른 CIDR 간 (노드 CIDR ↔ 파드 CIDR)
  - EKS 클러스터의 VPC CIDR
  - Kubernetes 서비스 IPv4 CIDR

EKS 클러스터 생성 시 `RemoteNodeNetwork`와 `RemotePodNetwork` 필드에 온프레미스 CIDR을 지정합니다.

### 라우팅 가능 vs 라우팅 불가능 파드 네트워크

| 구성 | 라우팅 가능 (권장) | 라우팅 불가능 |
|------|-------------------|-------------|
| 설정 | BGP(권장), 정적 라우트 또는 커스텀 라우팅 | CNI egress masquerade/NAT 사용 |
| 웹훅 | Hybrid 노드에서 실행 가능 | 클라우드 노드에서만 실행 가능 |
| Pod↔Pod 통신 | 클라우드↔온프레미스 직접 통신 가능 | 직접 통신 불가 |
| AWS 서비스 연동 | ALB, Prometheus 등이 Hybrid 워크로드와 통신 가능 | 통신 불가 |

> **권장 사항**: Cilium BGP Control Plane을 사용하여 파드 CIDR을 라우팅 가능하게 구성하세요.

---

## 필수 방화벽 포트

### 클러스터 통신 포트

온프레미스와 AWS 간 통신을 위해 다음 포트를 열어야 합니다:

| 포트 | 프로토콜 | 방향 | 용도 |
|------|----------|------|------|
| 443 | TCP | On-Prem → AWS | Kubelet에서 Kubernetes API 서버로 통신 |
| 443 | TCP | On-Prem → AWS | 파드에서 Kubernetes API 서버로 통신 |
| 10250 | TCP | AWS → On-Prem | API 서버에서 Kubelet으로 통신 |
| 웹훅 포트 | TCP | AWS → On-Prem | API 서버에서 웹훅으로 통신 (라우팅 가능 파드 네트워크만) |
| 53 | TCP/UDP | 양방향 | CoreDNS (파드 CIDR ↔ 파드 CIDR, 클라우드 CoreDNS 시 VPC CIDR 포함) |
| 앱 포트 | 사용자 정의 | 양방향 | Pod-to-Pod 애플리케이션 통신 |

### VPN 포트 (Site-to-Site VPN 사용 시)

| 포트 | 프로토콜 | 방향 | 용도 |
|------|----------|------|------|
| 500 | UDP | 양방향 | IKE (Internet Key Exchange) |
| 4500 | UDP | 양방향 | IPSec NAT-T |

### Cilium CNI 포트

Cilium을 CNI로 사용할 때 추가로 필요한 포트:

| 포트 | 프로토콜 | 방향 | 용도 |
|------|----------|------|------|
| 8472 | UDP | 양방향 | VXLAN 오버레이 (기본 터널 모드) |
| 4240 | TCP | 양방향 | 헬스 체크 |

> **참고**: Cilium 및 Calico의 상세 방화벽 요구 사항은 각 프로젝트의 공식 문서를 참조하세요.

### iptables 규칙 예시

```bash
# Kubernetes API 서버 통신 허용
sudo iptables -A INPUT -p tcp --dport 443 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -d 10.0.0.0/8 -j ACCEPT

# Kubelet API 허용
sudo iptables -A INPUT -p tcp --dport 10250 -s 10.0.0.0/8 -j ACCEPT

# Cilium VXLAN 허용
sudo iptables -A INPUT -p udp --dport 8472 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 8472 -j ACCEPT

# Cilium 헬스 체크 허용
sudo iptables -A INPUT -p tcp --dport 4240 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 4240 -j ACCEPT

# DNS 허용
sudo iptables -A INPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# 규칙 저장
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

---

## 온프레미스 아웃바운드 접근 요구 사항

### 설치 및 업그레이드 시 필요한 엔드포인트

nodeadm 설치 및 업그레이드를 위해 온프레미스 노드에서 다음 AWS 엔드포인트에 HTTPS(443) 접근이 필요합니다:

| 컴포넌트 | URL | 비고 |
|----------|-----|------|
| EKS 노드 아티팩트 (S3) | `https://hybrid-assets.eks.amazonaws.com` | nodeadm 바이너리 및 의존성 |
| EKS 서비스 | `https://eks.<region>.amazonaws.com` | 클러스터 정보 조회 |
| ECR 서비스 | `https://api.ecr.<region>.amazonaws.com` | 컨테이너 이미지 풀 |
| SSM 바이너리 | `https://amazon-ssm-<region>.s3.<region>.amazonaws.com` | SSM 자격 증명 프로바이더 사용 시 |
| SSM 서비스 | `https://ssm.<region>.amazonaws.com` | SSM 자격 증명 프로바이더 사용 시 |
| IAM Roles Anywhere | `https://rolesanywhere.<region>.amazonaws.com` | IAM RA 자격 증명 프로바이더 사용 시 |
| OS 패키지 관리자 | 리전별 엔드포인트 | 시스템 패키지 설치 |

### 지속 운영 시 필요한 엔드포인트

| 용도 | 소스 | 대상 | 비고 |
|------|------|------|------|
| Kubelet → API 서버 | 노드 CIDR | EKS 클러스터 IP | 포트 443 |
| Pod → API 서버 | 파드 CIDR | EKS 클러스터 IP | 포트 443 |
| SSM 자격 증명 갱신 | 노드 CIDR | SSM 엔드포인트 | 5분 간격 하트비트 |
| IAM RA 자격 증명 갱신 | 노드 CIDR | IAM Anywhere 엔드포인트 | 주기적 갱신 |
| EKS Pod Identity | 노드 CIDR | EKS Auth 엔드포인트 | Pod Identity 사용 시 |

### EKS 클러스터 네트워크 인터페이스 IP 확인

방화벽 규칙에 EKS 클러스터 IP가 필요한 경우 다음 명령으로 확인합니다:

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=<VPC_ID>" "Name=description,Values=Amazon EKS*" \
  --query 'NetworkInterfaces[].PrivateIpAddress' \
  --output text
```

> **참고**: EKS 네트워크 인터페이스는 클러스터 업데이트(예: 버전 업그레이드) 시 삭제 및 재생성될 수 있습니다. 제한된 서브넷 크기를 사용하면 IP 범위를 예측하기 쉬워 방화벽 구성에 유리합니다.

---

## VPC 프라이빗 엔드포인트 (에어갭/프라이빗 환경)

VPN 또는 Direct Connect를 통해 AWS에 연결된 온프레미스 환경에서 인터넷 없이 AWS 서비스에 접근하려면 **VPC Interface Endpoint** (PrivateLink)를 구성해야 합니다.

### 왜 VPC 엔드포인트가 필요한가

일반적인 AWS API 호출은 퍼블릭 인터넷을 경유합니다. 하지만 에어갭 또는 프라이빗 전용 환경에서는 인터넷 경로가 없으므로 AWS 서비스에 접근할 수 없습니다. VPC Interface Endpoint는 VPC 내부에 ENI(Elastic Network Interface)를 생성하여, 온프레미스에서 VPN/Direct Connect를 통해 AWS API에 직접 접근할 수 있게 합니다.

```
온프레미스 노드
  → VPN / Direct Connect
    → VPC 내부 Interface Endpoint ENI (프라이빗 IP)
      → AWS 서비스 (EKS, ECR, STS, SSM 등)
```

> **핵심**: Gateway 엔드포인트(S3, DynamoDB용)는 VPC 라우트 테이블에 경로만 추가하므로, VPN/Direct Connect로 연결된 온프레미스에서는 접근할 수 없습니다. 온프레미스에서 S3에 접근하려면 반드시 **Interface 타입** S3 엔드포인트를 사용해야 합니다.

### 필수 Interface VPC 엔드포인트

| 서비스 | 엔드포인트 서비스 이름 | Private DNS | 용도 |
|--------|----------------------|-------------|------|
| EKS | `com.amazonaws.<region>.eks` | Yes | Kubernetes API 서버 통신 |
| EKS Auth | `com.amazonaws.<region>.eks-auth` | Yes | Pod Identity 인증 |
| ECR API | `com.amazonaws.<region>.ecr.api` | Yes | 이미지 메타데이터 조회 |
| ECR DKR | `com.amazonaws.<region>.ecr.dkr` | Yes | 이미지 Pull (Docker 레지스트리) |
| S3 | `com.amazonaws.<region>.s3` | — | 이미지 레이어, nodeadm 아티팩트 (**Interface 타입**) |
| STS | `com.amazonaws.<region>.sts` | Yes | IAM 자격 증명 교환 |
| SSM | `com.amazonaws.<region>.ssm` | Yes | SSM 자격 증명 프로바이더 사용 시 |
| SSM Messages | `com.amazonaws.<region>.ssmmessages` | Yes | SSM 세션 매니저 통신 |

> **참고**: S3 Interface 엔드포인트는 `private_dns_enabled`를 자동으로 지원하지 않습니다. S3 도메인의 프라이빗 DNS 해석이 필요한 경우 별도의 Private Hosted Zone(PHZ)을 구성해야 합니다. `hybrid-assets.eks.amazonaws.com`의 프라이빗 미러링 구성은 [에어갭 환경 구성 - hybrid-assets 프라이빗 미러링](./03-airgap-setup.md#hybrid-assets-프라이빗-미러링-s3--phz-패턴)을 참조하세요.

### Terraform으로 VPC 엔드포인트 생성

#### 보안 그룹

```hcl
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "vpc-endpoints-"
  vpc_id      = var.vpc_id
  description = "Security group for VPC Interface Endpoints"

  ingress {
    description = "HTTPS from VPC and on-premises"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [
      var.vpc_cidr,           # VPC 내부 트래픽
      var.remote_node_cidr,   # 온프레미스 노드 CIDR
      var.remote_pod_cidr     # 온프레미스 파드 CIDR
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "vpc-endpoints-sg"
  }
}
```

#### Interface VPC 엔드포인트

```hcl
# 생성할 Interface 엔드포인트 목록
locals {
  interface_endpoints = {
    eks          = "com.amazonaws.${var.region}.eks"
    eks-auth     = "com.amazonaws.${var.region}.eks-auth"
    ecr-api      = "com.amazonaws.${var.region}.ecr.api"
    ecr-dkr      = "com.amazonaws.${var.region}.ecr.dkr"
    sts          = "com.amazonaws.${var.region}.sts"
    ssm          = "com.amazonaws.${var.region}.ssm"
    ssmmessages  = "com.amazonaws.${var.region}.ssmmessages"
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = local.interface_endpoints

  vpc_id              = var.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name = "vpce-${each.key}"
  }
}

# S3 Interface 엔드포인트 (Gateway가 아닌 Interface 타입)
resource "aws_vpc_endpoint" "s3_interface" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = false  # S3는 Interface 타입에서 자동 Private DNS 미지원

  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name = "vpce-s3-interface"
  }
}
```

### AWS CLI로 VPC 엔드포인트 생성

```bash
# 1. VPC 엔드포인트용 보안 그룹 생성
SG_ID=$(aws ec2 create-security-group \
  --group-name vpc-endpoints-sg \
  --description "Security group for VPC Interface Endpoints" \
  --vpc-id <VPC_ID> \
  --query 'GroupId' --output text)

# 보안 그룹에 443 포트 허용
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --ip-permissions '[
    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
     "IpRanges": [
       {"CidrIp": "<VPC_CIDR>", "Description": "VPC internal"},
       {"CidrIp": "<REMOTE_NODE_CIDR>", "Description": "On-prem nodes"},
       {"CidrIp": "<REMOTE_POD_CIDR>", "Description": "On-prem pods"}
     ]}
  ]'

# 2. Interface VPC 엔드포인트 생성 (EKS 예시)
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.<REGION>.eks \
  --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-group-ids $SG_ID \
  --private-dns-enabled

# 3. 나머지 서비스도 동일하게 생성
for SERVICE in eks-auth ecr.api ecr.dkr sts ssm ssmmessages; do
  echo "Creating endpoint for: $SERVICE"
  aws ec2 create-vpc-endpoint \
    --vpc-id <VPC_ID> \
    --vpc-endpoint-type Interface \
    --service-name com.amazonaws.<REGION>.$SERVICE \
    --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
    --security-group-ids $SG_ID \
    --private-dns-enabled
done

# 4. S3 Interface 엔드포인트 (private-dns-enabled 없이)
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.<REGION>.s3 \
  --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-group-ids $SG_ID

# 5. 생성된 엔드포인트 확인
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query 'VpcEndpoints[].{ID:VpcEndpointId, Service:ServiceName, State:State}' \
  --output table
```

### 온프레미스 DNS 확인 흐름

VPC 엔드포인트의 `private_dns_enabled` 옵션은 VPC 내부에서만 작동합니다. 온프레미스에서 AWS 서비스 도메인(예: `eks.ap-northeast-2.amazonaws.com`)을 VPC 엔드포인트의 프라이빗 IP로 해석하려면, Route 53 Resolver Inbound Endpoint를 통해 VPC의 DNS를 쿼리해야 합니다.

```
온프레미스 노드
  → 온프레미스 DNS 서버 (조건부 포워딩 설정)
    → Route 53 Resolver Inbound Endpoint (VPC 내)
      → Route 53이 Private Hosted Zone / VPC DNS 검색
        → VPC Endpoint ENI의 프라이빗 IP 반환
          → 온프레미스 노드가 VPN/DX를 통해 ENI에 직접 접근
```

#### 온프레미스 DNS 서버 조건부 포워딩 설정

온프레미스 DNS 서버(예: BIND, Windows DNS, dnsmasq)에서 AWS 도메인을 Route 53 Inbound Endpoint로 전달하도록 구성합니다.

```
# BIND 예시 (/etc/named.conf)
zone "amazonaws.com" {
    type forward;
    forward only;
    forwarders {
        10.0.1.10;    # Route 53 Inbound Endpoint IP #1
        10.0.2.10;    # Route 53 Inbound Endpoint IP #2
    };
};

zone "eks.amazonaws.com" {
    type forward;
    forward only;
    forwarders {
        10.0.1.10;
        10.0.2.10;
    };
};
```

> **참고**: Route 53 Resolver Inbound Endpoint 생성 방법은 이 문서의 [DNS 구성](#dns-구성) 섹션을 참조하세요. VPC 엔드포인트 구성 후 반드시 `nslookup eks.<region>.amazonaws.com`으로 프라이빗 IP가 반환되는지 확인하세요.

---

## AWS 보안 그룹 구성

EKS는 클러스터 생성 시 보안 그룹을 자동으로 구성하지만, 아웃바운드 규칙은 자동 생성되지 않습니다 (보안 그룹은 기본적으로 모든 아웃바운드를 허용).

### 자동 생성되는 인바운드 규칙

| 프로토콜 | 포트 | 소스 | 용도 |
|----------|------|------|------|
| TCP | 443 | 원격 노드 CIDR | Kubelet에서 Kubernetes API로 |
| TCP | 443 | 원격 파드 CIDR | 파드에서 Kubernetes API로 (NAT 미사용 CNI) |

### 수동 추가 필요한 아웃바운드 규칙

| 프로토콜 | 포트 | 대상 | 용도 |
|----------|------|------|------|
| TCP | 10250 | 원격 노드 CIDR | API 서버에서 Kubelet으로 |
| TCP | 웹훅 포트 | 원격 파드 CIDR | API 서버에서 웹훅으로 |

```bash
# 커스텀 보안 그룹 생성 예시
aws ec2 create-security-group \
  --group-name hybrid-nodes-sg \
  --description "Security group for EKS Hybrid Nodes" \
  --vpc-id <VPC_ID>

# 인바운드 규칙 추가
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --ip-permissions '[
    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
     "IpRanges": [{"CidrIp": "<REMOTE_NODE_CIDR>"}, {"CidrIp": "<REMOTE_POD_CIDR>"}]}
  ]'
```

> **주의**: 보안 그룹당 기본 인바운드 규칙 제한은 60개입니다. 또한 EKS는 원격 네트워크를 제거할 때 규칙을 자동으로 삭제하지 않으므로 수동 정리가 필요합니다.

---

## Pod CIDR 방화벽 전략

Pod 간 통신을 위해 전체 Pod CIDR 범위에 대한 방화벽 규칙을 등록해야 합니다.

```bash
# Pod CIDR 범위 예시: 10.244.0.0/16
# 클러스터의 Pod CIDR 확인
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Pod CIDR에 대한 방화벽 규칙 추가
sudo iptables -A INPUT -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -d 10.244.0.0/16 -j ACCEPT

# Service CIDR도 추가 (예: 172.20.0.0/16)
sudo iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 172.20.0.0/16 -j ACCEPT
```

---

## DNS 구성

### Route 53 Resolver Inbound Endpoint

온프레미스에서 AWS 도메인을 쿼리할 수 있도록 Inbound Endpoint를 생성합니다.

```bash
# Inbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-inbound-$(date +%s)" \
  --name "hybrid-inbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction INBOUND \
  --ip-addresses SubnetId=subnet-111111111,Ip=10.0.1.10 SubnetId=subnet-222222222,Ip=10.0.2.10

# Endpoint IP 확인
aws route53resolver list-resolver-endpoint-ip-addresses \
  --resolver-endpoint-id rslvr-in-xxxxxxxxxxxxx
```

### Route 53 Resolver Outbound Endpoint

AWS에서 온프레미스 도메인을 쿼리할 수 있도록 Outbound Endpoint와 전달 규칙을 생성합니다.

```bash
# Outbound Endpoint 생성
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-outbound-$(date +%s)" \
  --name "hybrid-outbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction OUTBOUND \
  --ip-addresses SubnetId=subnet-111111111 SubnetId=subnet-222222222

# 전달 규칙 생성 (온프레미스 도메인)
aws route53resolver create-resolver-rule \
  --creator-request-id "forward-onprem-$(date +%s)" \
  --name "forward-to-onprem" \
  --rule-type FORWARD \
  --domain-name "internal.company.io" \
  --resolver-endpoint-id rslvr-out-xxxxxxxxxxxxx \
  --target-ips "Ip=192.168.1.10,Port=53" "Ip=192.168.1.11,Port=53"

# VPC에 규칙 연결
aws route53resolver associate-resolver-rule \
  --resolver-rule-id rslvr-rr-xxxxxxxxxxxxx \
  --vpc-id vpc-0123456789abcdef0
```

### CoreDNS 커스텀 도메인 구성

온프레미스 도메인에 대한 DNS 쿼리를 온프레미스 DNS 서버로 전달합니다.

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
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
    internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
```

```bash
# CoreDNS ConfigMap 적용
kubectl apply -f coredns-configmap.yaml

# CoreDNS 재시작
kubectl rollout restart deployment coredns -n kube-system

# DNS 해석 테스트
kubectl run dns-test --rm -it --image=busybox --restart=Never -- nslookup internal.company.io
```

### CoreDNS 이중 배치 구성 (온프레미스 + 클라우드)

#### 왜 이중 배치가 필요한가?

EKS Hybrid Nodes 환경에서 CoreDNS가 클라우드 노드에만 실행되면, 온프레미스 Pod의 DNS 쿼리가 VPN/Direct Connect를 거쳐 클라우드까지 왕복해야 합니다. 반대로 CoreDNS가 온프레미스 노드에만 실행되면, 클라우드 Pod의 DNS 쿼리가 역방향으로 왕복합니다.

**양쪽 모두에 CoreDNS Pod가 존재해야** DNS 지연이 최소화되고, 한쪽 네트워크 장애 시에도 DNS 서비스가 유지됩니다.

#### 레플리카 수 권장

최소 **4개** (클라우드 2개 + 온프레미스 2개)를 권장합니다. 각 위치에 2개 이상의 레플리카를 배치하여 고가용성을 확보합니다.

#### CoreDNS Deployment 패치

`topologySpreadConstraints`와 `tolerations`를 사용하여 CoreDNS Pod를 클라우드와 온프레미스 노드에 균등하게 분산합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
spec:
  replicas: 4
  template:
    spec:
      tolerations:
        - key: "eks.amazonaws.com/compute-type"
          value: "hybrid"
          effect: "NoSchedule"
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: "eks.amazonaws.com/compute-type"
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              k8s-app: kube-dns
```

#### kubectl patch 명령어

```bash
kubectl patch deployment coredns -n kube-system --type=strategic -p '{
  "spec": {
    "replicas": 4,
    "template": {
      "spec": {
        "tolerations": [
          {
            "key": "eks.amazonaws.com/compute-type",
            "value": "hybrid",
            "effect": "NoSchedule"
          }
        ],
        "topologySpreadConstraints": [
          {
            "maxSkew": 1,
            "topologyKey": "eks.amazonaws.com/compute-type",
            "whenUnsatisfiable": "ScheduleAnyway",
            "labelSelector": {
              "matchLabels": {
                "k8s-app": "kube-dns"
              }
            }
          }
        ]
      }
    }
  }
}'
```

#### 배치 확인

```bash
# CoreDNS Pod가 양쪽 노드에 분산되었는지 확인
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide

# 노드별 compute-type 레이블 확인
kubectl get nodes -L eks.amazonaws.com/compute-type
```

> **참고**:
> - EKS 관리형 CoreDNS 애드온을 사용하는 경우, 애드온의 `configurationValues`를 통해 동일한 설정을 적용할 수 있습니다.
> - `whenUnsatisfiable: ScheduleAnyway`를 사용하므로 한쪽에 노드가 없어도 스케줄링이 차단되지 않습니다. 이는 클러스터 초기 부트스트랩 시 CoreDNS가 정상적으로 시작될 수 있도록 보장합니다.

---

## 트래픽 플로우 패턴

AWS와 온프레미스 간의 트래픽 흐름 패턴을 이해하는 것은 방화벽 구성과 문제 해결에 필수적입니다. 다음 섹션에서는 AWS 공식 아키텍처 다이어그램과 함께 각 트래픽 패턴을 상세히 설명합니다.

> **출처**: [AWS EKS Hybrid Nodes Traffic Flows](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-traffic-flows.html)

### 패턴 1: Kubelet → EKS 컨트롤 플레인

Kubelet은 DNS 조회를 통해 API 서버 엔드포인트로 HTTPS 요청을 시작합니다. 퍼블릭 액세스 모드에서는 트래픽이 퍼블릭 인터넷을 통과합니다. 프라이빗 모드에서는 VPN/DX를 통해 VPC ENI로 트래픽이 흐릅니다.

![Kubelet에서 컨트롤 플레인으로](../../assets/interactive-diagrams/hybrid-nodes-kubelet-to-cp.svg)

### 패턴 2: EKS 컨트롤 플레인 → Kubelet

API 서버는 노드 상태 객체에서 노드 IP를 가져옵니다. 트래픽은 VPC를 통해 라우팅된 후 Direct Connect 또는 VPN을 통해 클라우드 경계를 넘어 포트 10250의 kubelet에 도달합니다. 이는 `kubectl logs`, `kubectl exec`, `kubectl port-forward` 등에 사용됩니다.

![컨트롤 플레인에서 Kubelet으로](../../assets/interactive-diagrams/hybrid-nodes-cp-to-kubelet.svg)

### 패턴 3: Pod → EKS 컨트롤 플레인

Pod는 `kubernetes` Service(ClusterIP)를 통해 Kubernetes API와 통신합니다. kube-proxy가 DNAT를 적용하여 서비스 IP를 컨트롤 플레인 ENI IP로 변환한 후, 패킷이 VPN/DX를 통해 VPC로 라우팅됩니다.

- **CNI NAT 미사용 시**: Pod가 kubernetes 서비스 IP(예: 172.16.0.1)로 전송하면 kube-proxy가 컨트롤 플레인 ENI IP로 DNAT를 적용합니다. 반환 트래픽은 파드 CIDR을 통한 역방향 라우팅이 필요합니다.
- **CNI NAT 사용 시**: CNI가 노드 처리 전에 SNAT를 적용하여 반환 라우팅을 단순화합니다(추가 파드 CIDR 라우팅 불필요).

![Pod에서 컨트롤 플레인으로](../../assets/interactive-diagrams/hybrid-nodes-pod-to-cp.svg)

### 패턴 4: EKS 컨트롤 플레인 → Pod (웹훅)

API 서버가 하이브리드 노드에서 실행 중인 웹훅 Pod에 직접 연결을 시작합니다. 트래픽은 원격 파드 CIDR에 대해 VPC를 통해 라우팅되고, 게이트웨이를 통해 경계를 넘습니다. 이는 **라우팅 가능한 파드 CIDR이 필요**합니다.

![컨트롤 플레인에서 Pod로](../../assets/interactive-diagrams/hybrid-nodes-cp-to-pod.svg)

> **중요**: 온프레미스 파드 CIDR이 라우팅 불가능한 경우, **모든 웹훅을 클라우드 노드에서 실행**해야 합니다. 아래 [웹훅 구성](#웹훅-구성) 섹션을 참조하세요.

### 패턴 5: 하이브리드 노드 간 Pod ↔ Pod

서로 다른 하이브리드 노드의 Pod는 [VXLAN 캡슐화](../networking/cilium/03-networking.md#vxlan-기술-심층-분석)(또는 Geneve, IP-in-IP와 같은 유사한 오버레이 프로토콜)를 사용하여 통신합니다. CNI는 소스/대상 노드 IP를 사용하여 외부 헤더로 원본 Pod-to-Pod 패킷을 캡슐화합니다. 수신 노드의 CNI가 캡슐을 해제하고 대상 Pod로 전달합니다.

![하이브리드 노드 간 Pod-to-Pod](../../assets/interactive-diagrams/hybrid-nodes-pod-to-pod.svg)

#### VXLAN 캡슐화 상세

VXLAN(Virtual Extensible LAN)은 L2 프레임을 L3 패킷으로 캡슐화하여 오버레이 네트워크를 구성합니다. 하이브리드 노드 간 Pod 통신에서 패킷 구조가 어떻게 변환되는지 살펴봅니다.

**원본 패킷 (캡슐화 전)**
```
┌────────────────────────────────────────────────┐
│  Pod-A IP (src) → Pod-B IP (dst) │   Payload   │
│    10.85.0.10       10.85.1.20   │   (data)    │
└────────────────────────────────────────────────┘
```

**VXLAN 캡슐화 후**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Outer IP Header │ UDP Header │ VXLAN Header │      Original Packet          │
│ Node-A → Node-B │ Port 8472  │    (VNI)     │ Pod-A IP → Pod-B IP │ Payload │
│ 10.80.1.10      │            │              │ 10.85.0.10  10.85.1.20        │
│   → 10.80.1.11  │            │              │                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**캡슐화 프로세스 (송신 노드)**
1. Pod-A가 Pod-B로 패킷을 전송합니다
2. 송신 노드의 CNI(Cilium)가 대상 Pod IP를 확인하고 해당 노드를 조회합니다
3. CNI가 원본 패킷을 VXLAN 헤더와 외부 IP 헤더로 래핑합니다
4. 외부 헤더의 소스/대상 IP는 노드 IP를 사용합니다
5. 캡슐화된 패킷이 UDP 포트 8472로 전송됩니다

**역캡슐화 프로세스 (수신 노드)**
1. 수신 노드가 UDP 8472 포트에서 VXLAN 패킷을 수신합니다
2. CNI가 VXLAN 헤더와 외부 IP 헤더를 제거합니다
3. 원본 패킷이 대상 Pod로 전달됩니다

**주요 구성 요소**
| 구성 요소 | 설명 |
|-----------|------|
| VNI (VXLAN Network Identifier) | 파드 네트워크 트래픽을 격리하는 24비트 식별자 (기본값: 자동 할당) |
| UDP 포트 | Cilium 기본값: 8472, 표준 VXLAN: 4789 |
| MTU | VXLAN 오버헤드(50바이트)를 고려하여 설정 필요 (예: 1500 → 1450) |

> **참고**: Cilium은 VXLAN 외에도 Geneve, IP-in-IP 등 다른 터널 프로토콜을 지원합니다. `--tunnel` 옵션으로 터널 모드를 선택할 수 있습니다.

### 패턴 6: 클라우드 Pod ↔ 하이브리드 Pod (East-West)

VPC Pod(VPC CNI 사용)가 하이브리드 Pod로 직접 전송합니다. VPC 라우팅이 트래픽을 온프레미스 게이트웨이로 보냅니다. 패킷이 경계를 넘어 하이브리드 노드에 도착합니다. 이는 **라우팅 가능한 파드 CIDR**과 적절한 VPC 라우트 테이블 항목이 필요합니다.

![East-West 트래픽](../../assets/interactive-diagrams/hybrid-nodes-east-west.svg)

### 트래픽 플로우 요약

| # | 플로우 | 방향 | 포트 | 요구 사항 |
|---|--------|------|------|-----------|
| 1 | Kubelet → API 서버 | On-Prem → AWS | TCP 443 | VPN/DX 또는 인터넷 |
| 2 | API 서버 → Kubelet | AWS → On-Prem | TCP 10250 | SG 아웃바운드 규칙 |
| 3 | Pod → API 서버 | On-Prem → AWS | TCP 443 | kube-proxy DNAT |
| 4 | API 서버 → Webhook Pod | AWS → On-Prem | TCP 8443+ | **라우팅 가능 파드 CIDR** |
| 5 | Hybrid Pod ↔ Hybrid Pod | On-Prem 내부 | UDP 8472 | Cilium VXLAN |
| 6 | Cloud Pod ↔ Hybrid Pod | AWS ↔ On-Prem | VPC 라우트 | **라우팅 가능 파드 CIDR** + VPC 라우트 |

### kube-proxy iptables 체인 구조

kube-proxy는 Kubernetes Service 트래픽을 실제 Pod로 라우팅하기 위해 iptables 규칙을 사용합니다. 하이브리드 노드에서도 동일한 3단계 체인 구조가 적용됩니다.

```
KUBE-SERVICES (진입점)
  └─→ KUBE-SVC-xxxx (서비스별 체인, 로드 밸런싱)
        └─→ KUBE-SEP-xxxx (엔드포인트별 체인, Pod IP로 DNAT)
```

**체인별 역할**

| 체인 | 역할 | 예시 |
|------|------|------|
| **KUBE-SERVICES** | 모든 ClusterIP 서비스의 목적지 IP:Port를 매칭 | `172.20.0.1:443` → `KUBE-SVC-NPX...` |
| **KUBE-SVC-xxxx** | 확률 기반 로드 밸런싱으로 엔드포인트 선택 | 3개 Pod → 각각 33% 확률 |
| **KUBE-SEP-xxxx** | 특정 Pod IP:Port로 DNAT 수행 | DNAT to `10.85.0.15:8080` |

**실제 iptables 규칙 예시**

```bash
# KUBE-SERVICES 체인 (nat 테이블)
-A KUBE-SERVICES -d 172.20.0.10/32 -p tcp -m tcp --dport 80 -j KUBE-SVC-XXXXXX

# KUBE-SVC 체인 (로드 밸런싱)
-A KUBE-SVC-XXXXXX -m statistic --mode random --probability 0.33333 -j KUBE-SEP-AAAAAA
-A KUBE-SVC-XXXXXX -m statistic --mode random --probability 0.50000 -j KUBE-SEP-BBBBBB
-A KUBE-SVC-XXXXXX -j KUBE-SEP-CCCCCC

# KUBE-SEP 체인 (DNAT)
-A KUBE-SEP-AAAAAA -p tcp -j DNAT --to-destination 10.85.0.15:8080
-A KUBE-SEP-BBBBBB -p tcp -j DNAT --to-destination 10.85.0.16:8080
-A KUBE-SEP-CCCCCC -p tcp -j DNAT --to-destination 10.85.1.20:8080
```

> **하이브리드 환경에서의 의미**: 위 예시에서 `10.85.1.20`이 다른 하이브리드 노드에 있는 Pod라면, DNAT 후 패킷은 VXLAN 캡슐화를 거쳐 해당 노드로 전송됩니다. kube-proxy가 Service 트래픽을 Pod IP로 변환하고, CNI가 실제 네트워크 라우팅을 담당합니다.

### kubelet 엔드포인트

kubelet은 각 노드에서 실행되며 API 서버와의 통신을 위해 REST 엔드포인트를 노출합니다.

**kubelet API 포트 및 엔드포인트**

| 포트 | 엔드포인트 | 용도 |
|------|-----------|------|
| 10250 | `/pods` | 노드에서 실행 중인 Pod 목록 조회 |
| 10250 | `/exec/{namespace}/{pod}/{container}` | 컨테이너에서 명령 실행 (`kubectl exec`) |
| 10250 | `/logs/{namespace}/{pod}/{container}` | 컨테이너 로그 스트리밍 (`kubectl logs`) |
| 10250 | `/metrics` | kubelet 메트릭 노출 (Prometheus 수집용) |
| 10250 | `/healthz` | kubelet 헬스 체크 |

**노드 등록 및 주소 보고**

kubelet이 클러스터에 노드를 등록할 때 `Node.status.addresses`에 주소 정보를 보고합니다:

```yaml
status:
  addresses:
  - address: 10.80.1.10        # 실제 온프레미스 IP
    type: InternalIP
  - address: hybrid-node-001   # 노드 호스트명
    type: Hostname
```

- **InternalIP**: 노드의 실제 온프레미스 IP 주소입니다. API 서버는 이 주소를 사용하여 kubelet에 연결합니다.
- **Hostname**: 노드의 호스트명입니다.

> **방화벽 규칙의 핵심**: API 서버가 kubelet에 연결할 때 `InternalIP`를 사용하므로, **AWS → On-Prem 방향으로 TCP 10250 포트**가 반드시 열려 있어야 합니다. 이 연결이 차단되면 `kubectl exec`, `kubectl logs`, `kubectl port-forward` 등의 명령이 실패합니다.

---

## 라우팅 가능한 Pod CIDR 구성

온프레미스 파드 CIDR을 라우팅 가능하게 만드는 것은 웹훅, East-West 트래픽, AWS 서비스 통합(ALB, Prometheus 등)에 필수적입니다.

![원격 Pod CIDR](../../assets/aws-official-diagrams/hybrid-nodes-remote-pod-cidrs.png)

### 옵션 1: BGP (권장)

CNI가 가상 라우터 역할을 하며 노드별 파드 CIDR 라우트를 로컬 온프레미스 라우터에 전파합니다. 가장 동적이고 유지보수하기 쉬운 접근 방식입니다.

![BGP 라우팅](../../assets/aws-official-diagrams/hybrid-nodes-bgp.png)

#### Cilium BGP Control Plane 구성

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPClusterConfig
metadata:
  name: hybrid-bgp-config
spec:
  bgpInstances:
  - name: hybrid-instance
    localASN: 65001
    peers:
    - name: on-prem-router
      peerASN: 65000
      peerAddress: 10.80.0.1
      peerConfigRef:
        name: on-prem-peer
---
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPPeerConfig
metadata:
  name: on-prem-peer
spec:
  families:
  - afi: ipv4
    safi: unicast
  gracefulRestart:
    enabled: true
---
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPAdvertisement
metadata:
  name: pod-cidr-advert
spec:
  advertisements:
  - advertisementType: PodCIDR
  - advertisementType: Service
    service:
      addresses:
      - ClusterIP
```

#### ASN (Autonomous System Number) 이해하기

위 Cilium BGP 구성에서 `localASN`과 `peerASN`은 **자율 시스템 번호**(Autonomous System Number)입니다. 각 BGP 참여자(라우터, 스위치, 또는 여기서는 각 노드의 Cilium)에게 할당되는 고유 식별자로, BGP 피어링의 양쪽 모두 ASN이 필요합니다.

**Private vs Public ASN 범위**

| 범위 | 유형 | 사용 사례 |
|------|------|----------|
| **64512 – 65534** | 16비트 Private | 내부 네트워크, 데이터센터, 랩 환경. **EKS Hybrid Nodes에서는 이 범위를 사용합니다.** |
| **4200000000 – 4294967294** | 32비트 Private | 많은 고유 ASN이 필요한 대규모 내부 배포 |
| 1 – 64511 | 16비트 Public | RIR(ARIN, RIPE, APNIC)에 등록된 인터넷 대면 네트워크 |

> **EKS Hybrid Nodes의 경우**: 항상 **Private ASN 범위**(64512–65534)를 사용하세요. Public ASN은 필요하지 않습니다 — 여기서 BGP는 Cilium 노드와 온프레미스 라우터 간의 내부 네트워크에서만 사용됩니다.

**ASN 값 선택 방법**

- **`localASN`** (예: `65001`): 하이브리드 노드에서 실행되는 Cilium에 할당된 ASN. 동일 클러스터의 모든 Cilium 노드는 일반적으로 하나의 ASN을 공유합니다.
- **`peerASN`** (예: `65000`): Cilium과 피어링하는 온프레미스 라우터의 ASN. 라우터의 BGP 구성에서 이 값을 확인합니다.

환경에 BGP가 아직 구성되어 있지 않다면, Private 범위에서 서로 다른 두 숫자를 선택하면 됩니다 (예: 라우터에 `65000`, Cilium에 `65001`). 네트워크 팀이 이미 내부적으로 BGP를 사용하고 있다면, ASN 충돌을 방지하기 위해 조율이 필요합니다.

**온프레미스 라우터 BGP 구성 예시**

아래는 위 Cilium 구성과 매칭되는 **라우터 측** BGP 피어링 구성 예시입니다. 각 예시에서 라우터는 ASN `65000`을 사용하고, `10.80.1.10`(ASN `65001`)의 Cilium 노드와 피어링합니다.

##### Cisco IOS / IOS-XE

```
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001
 neighbor 10.80.1.10 description "EKS Hybrid Node - Cilium BGP"
 !
 address-family ipv4 unicast
  neighbor 10.80.1.10 activate
  neighbor 10.80.1.10 soft-reconfiguration inbound
 exit-address-family
```

##### Cisco NX-OS (Nexus)

```
router bgp 65000
  address-family ipv4 unicast
  neighbor 10.80.1.10
    remote-as 65001
    description EKS-Hybrid-Cilium
    address-family ipv4 unicast
      soft-reconfiguration inbound
```

##### Juniper Junos (MX / QFX / SRX)

```
set protocols bgp group eks-hybrid type external
set protocols bgp group eks-hybrid peer-as 65001
set protocols bgp group eks-hybrid neighbor 10.80.1.10 description "EKS Hybrid Node"
set protocols bgp group eks-hybrid family inet unicast
set routing-options autonomous-system 65000
```

##### Arista EOS

```
router bgp 65000
   neighbor 10.80.1.10 remote-as 65001
   neighbor 10.80.1.10 description EKS-Hybrid-Cilium
   !
   address-family ipv4
      neighbor 10.80.1.10 activate
```

##### MikroTik RouterOS

```
/routing bgp connection
add name=eks-hybrid remote.address=10.80.1.10 remote.as=65001 \
    local.role=ebgp as=65000 address-families=ip
```

##### FRRouting (FRR) — 소프트웨어 라우터 (Linux)

FRRouting은 Linux 서버 및 VM에서 소프트웨어 BGP 라우터로 널리 사용됩니다:

```
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001
 neighbor 10.80.1.10 description EKS-Hybrid-Cilium
 !
 address-family ipv4 unicast
  neighbor 10.80.1.10 activate
 exit-address-family
```

##### AWS Transit Gateway (TGW)

AWS Transit Gateway와 Site-to-Site VPN을 사용하는 경우, TGW 측 ASN은 TGW 생성 시 구성됩니다:

```bash
# 커스텀 ASN으로 TGW 생성
aws ec2 create-transit-gateway \
  --options AmazonSideAsn=65000

# VPN 터널은 TGW ASN으로 자동으로 BGP를 설정합니다
# 온프레미스 라우터(또는 Cilium)는 자체 ASN을 사용하여 TGW와 피어링합니다
```

> **참고**: AWS TGW의 기본 ASN은 `64512`입니다. Cilium 노드가 `65001`을 사용하는 경우, Cilium 구성의 피어 ASN은 TGW(또는 VGW)의 ASN과 일치해야 합니다.

**다수의 하이브리드 노드 구성**

여러 하이브리드 노드가 있는 경우, 각 노드는 **동일한 `localASN`** 으로 자체 Cilium BGP 스피커를 실행합니다. 온프레미스 라우터는 각 노드와 개별적으로 피어링합니다:

```
# 라우터 구성 — 각 하이브리드 노드와 피어링
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001   ! hybrid-node-001
 neighbor 10.80.1.11 remote-as 65001   ! hybrid-node-002
 neighbor 10.80.1.12 remote-as 65001   ! hybrid-node-003
```

각 노드는 자신의 파드 CIDR 조각을 광고합니다 (예: node-001은 `10.85.0.0/25`, node-002는 `10.85.0.128/25`를 광고). 이를 통해 라우터는 모든 파드 CIDR에 대한 완전한 라우팅 테이블을 구성합니다.

#### BGP 피어링 확인

```bash
cilium bgp peers
cilium bgp routes
```

하이브리드 노드에서 Session State가 `established`로 표시되어야 합니다.

### 옵션 2: 정적 라우트

파드 CIDR을 사용한 수동 라우터 구성입니다. 가장 간단하지만 오류가 발생하기 쉽고 노드가 변경될 때 수동 업데이트가 필요합니다.

![정적 라우트](../../assets/aws-official-diagrams/hybrid-nodes-static-routes.png)

### 옵션 3: ARP 프록시

노드가 호스팅된 파드 IP에 대한 ARP 요청에 응답합니다. 로컬 라우터와 레이어 2 네트워크 근접성이 필요합니다. Cilium에는 프록시 ARP 지원이 내장되어 있습니다. 라우터 BGP나 정적 라우트 구성이 필요 없지만, 파드 CIDR이 다른 네트워크와 겹치면 안 됩니다.

![ARP 프록시](../../assets/aws-official-diagrams/hybrid-nodes-arp-proxy.png)

---

## 네트워크 정책

하이브리드 노드 환경에서 Pod 간 트래픽을 제어하기 위해 네트워크 정책을 사용할 수 있습니다. Cilium CNI를 사용하면 표준 Kubernetes NetworkPolicy와 확장된 CiliumNetworkPolicy 모두 지원됩니다.

### Kubernetes NetworkPolicy

표준 Kubernetes NetworkPolicy는 L3/L4 수준의 기본적인 트래픽 필터링을 제공합니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: bookinfo
spec:
  podSelector:
    matchLabels:
      app: reviews
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: productpage
    ports:
    - protocol: TCP
      port: 9080
```

이 정책은 `bookinfo` 네임스페이스에서 `app: productpage` 레이블이 있는 Pod만 `app: reviews` Pod의 9080 포트에 접근할 수 있도록 허용합니다.

### CiliumNetworkPolicy

CiliumNetworkPolicy는 Kubernetes NetworkPolicy의 기능을 확장하여 L7 필터링, DNS 인식 정책, 아이덴티티 기반 매칭 등을 제공합니다.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: productpage
    toPorts:
    - ports:
      - port: "9080"
        protocol: TCP
```

#### CiliumNetworkPolicy 고급 기능

**L7 HTTP 필터링**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-rule
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: productpage
    toPorts:
    - ports:
      - port: "9080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/.*"
```

**DNS 기반 Egress 정책**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-external-api
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: productpage
  egress:
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

### 하이브리드 환경에서의 네트워크 정책 고려사항

| 고려사항 | 설명 |
|----------|------|
| **기본 동작** | 네트워크 정책이 없으면 모든 트래픽이 허용됩니다. NetworkPolicy가 적용되면 명시적으로 허용된 트래픽만 통과합니다. |
| **크로스 바운더리 트래픽** | 클라우드 노드의 Pod와 하이브리드 노드의 Pod 간 통신을 정책에 반영해야 합니다. |
| **CNI 요구 사항** | Cilium이 CNI로 설정되어 있어야 두 정책 유형 모두 작동합니다. |
| **정책 적용 범위** | CiliumNetworkPolicy는 해당 네임스페이스에만 적용됩니다. 클러스터 전체 정책은 CiliumClusterwideNetworkPolicy를 사용하세요. |

> **권장 사항**: 하이브리드 환경에서는 명시적인 네트워크 정책을 정의하여 의도하지 않은 크로스 바운더리 트래픽을 방지하세요. 특히 민감한 워크로드는 엄격한 Ingress/Egress 정책으로 보호해야 합니다.

---

## 웹훅 구성

웹훅은 Kubernetes 애플리케이션과 오픈소스 프로젝트(AWS Load Balancer Controller, CloudWatch Observability Agent)에서 변환(mutating) 및 검증(validation) 기능에 사용됩니다.

### 라우팅 가능한 파드 네트워크 사용 시

온프레미스 파드 CIDR이 라우팅 가능한 경우(BGP, 정적 라우트 또는 ARP 프록시를 통해), 웹훅을 하이브리드 노드에서 실행할 수 있습니다.

### 라우팅 불가능한 파드 네트워크 사용 시

온프레미스 파드 CIDR이 **라우팅 불가능**한 경우, 노드 어피니티를 사용하여 **모든 웹훅을 클라우드 노드에서 실행**하세요:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

### 웹훅을 사용하는 애드온

다음 애드온은 웹훅 배치를 고려해야 합니다:

| 애드온 | 웹훅 배치 (라우팅 불가능 파드 CIDR) |
|--------|-----------------------------------|
| AWS Load Balancer Controller | 클라우드 노드만 |
| CloudWatch Observability Agent | 클라우드 노드만 |
| ADOT (OpenTelemetry) | 클라우드 노드만 |
| cert-manager | 클라우드 노드만 |
| Kubernetes Metrics Server | 라우팅 가능 파드 CIDR 필요 |

---

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >
