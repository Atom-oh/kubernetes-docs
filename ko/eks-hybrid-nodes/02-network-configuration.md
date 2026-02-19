# 네트워크 구성

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >

> **지원 버전**: EKS 1.28+, nodeadm 1.0+
> **마지막 업데이트**: 2026년 2월

이 문서에서는 EKS Hybrid Nodes 환경에서 필요한 CIDR 요구 사항, 방화벽 포트, AWS 엔드포인트 접근, 보안 그룹 구성, DNS 구성을 다룹니다.

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

VPN 또는 Direct Connect를 통해 AWS에 연결된 온프레미스 환경에서 인터넷 없이 AWS 서비스에 접근하려면 **VPC Interface Endpoint (PrivateLink)**를 구성해야 합니다.

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

< [이전: 사전 요구 사항](./01-prerequisites.md) | [목차](./README.md) | [다음: 에어갭 환경 구성](./03-airgap-setup.md) >
