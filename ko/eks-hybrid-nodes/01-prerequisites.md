# 사전 요구 사항 및 시스템 요구 사항

< [목차](./README.md) | [다음: 네트워크 구성](./02-network-configuration.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 EKS Hybrid Nodes를 구성하기 위한 온프레미스 노드, GPU 서버, 네트워크 요구 사항을 다룹니다.

## 네트워크 사전 요구 사항 개요

아래 다이어그램은 VPC 구성, Transit Gateway/Virtual Private Gateway, CIDR 요구 사항을 포함한 온프레미스 노드와 EKS 클러스터 연결을 위한 네트워크 사전 요구 사항을 보여줍니다.

![EKS Hybrid Nodes 네트워크 사전 요구 사항](../../assets/aws-official-diagrams/hybrid-prereq-diagram.png)

## 온프레미스 노드 요구 사항

### 지원 운영 체제

| 운영 체제 | 버전 | 아키텍처 |
|-----------|------|----------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |
| Bottlerocket | v1.37.0 이상 (VMware 변형만 지원) | x86_64만 |

> **Bottlerocket 참고 사항**: Bottlerocket은 VMware 변형만 EKS Hybrid Nodes에서 지원되며, Kubernetes v1.28 이상이 필요합니다. Bottlerocket은 필요한 의존성을 자체적으로 포함하고 있어 `nodeadm` CLI가 필요하지 않습니다. ARM 아키텍처는 Bottlerocket에서 지원되지 않습니다.

> **ARM 아키텍처 주의사항**:
> - ARM 노드는 **ARMv8.2 이상 + Crypto 확장** 필수 (kube-proxy v1.31+)
> - **Raspberry Pi (Pi 5 이전)는 호환되지 않음** — ARMv8.0만 지원하므로 Crypto 확장 누락
> - Pi 5 (ARMv8.2)부터 호환 가능

### 컨테이너 런타임

```bash
# containerd 버전 확인
containerd --version
# 필요 버전: 1.6.x 이상

# Docker Engine 버전 확인 (containerd 포함)
docker --version
# 필요 버전: 20.10.10 이상
```

> **OS별 containerd 주의사항**:
> - **Ubuntu 24.04**: containerd v1.7.19 이상이 필요하거나, AppArmor 프로필 구성 변경 필요
> - **RHEL**: `--containerd-source distro` 옵션은 **유효하지 않음**. 반드시 `--containerd-source docker` 사용
> - **Ubuntu 20.04 / RHEL 8**: Cilium v1.18.x 사용 시 커널 5.10 이상 필요 (기본 커널이 미달하므로 주의)

### 최소 하드웨어 사양

| 리소스 | 최소 사양 (AWS 공식) | 권장 사양 |
|--------|---------------------|----------|
| CPU | 1 vCPU | 4 코어 이상 |
| RAM | 1 GiB | 8 GB 이상 |
| 디스크 | 50 GB SSD | 100 GB NVMe SSD |
| 네트워크 | 100 Mbps | 10 Gbps 이상 |

> **참고**: AWS 공식 최소 사양은 1 vCPU / 1 GiB이지만, 실제 워크로드를 실행하려면 2코어 / 4GB 이상을 권장합니다.

### 시스템 설정 확인

```bash
# 스왑 비활성화 확인
free -h
# Swap이 0이어야 함

# 스왑 비활성화
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 필요한 커널 모듈 로드
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# 커널 파라미터 설정
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

## GPU 서버 요구 사항 (선택사항)

### NVIDIA 드라이버

```bash
# NVIDIA 드라이버 버전 확인
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# 필요 버전: 550.x 이상

# CUDA 버전 확인
nvcc --version
# 권장 버전: CUDA 12.x
```

### 지원 GPU 모델

| GPU 모델 | VRAM | 주요 용도 |
|----------|------|----------|
| NVIDIA H100 | 80 GB | 대규모 LLM 학습/추론 |
| NVIDIA H200 | 141 GB | 초대규모 모델 |
| NVIDIA A100 | 40/80 GB | AI/ML 범용 |
| NVIDIA L40S | 48 GB | 추론 최적화 |

### GPU 드라이버 설치 (Amazon Linux 2023 예시)

```bash
# NVIDIA 드라이버 설치 (Amazon Linux 2023)
# 커널 개발 패키지 설치
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)

# NVIDIA 드라이버 저장소 추가
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/amzn2023/x86_64/cuda-amzn2023.repo

# 드라이버 설치
sudo dnf module install -y nvidia-driver:550-dkms

# NVIDIA Container Toolkit 설치
sudo dnf config-manager --add-repo https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit

# containerd 설정 업데이트
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## 네트워크 요구 사항

### 대역폭 및 지연 시간

| 항목 | 최소 요구 | 권장 사양 |
|------|----------|----------|
| 대역폭 | 100 Mbps | 10 Gbps 이상 |
| 지연 시간 | 200 ms RTT 이하 | 5 ms 이하 |
| 패킷 손실 | 0.1% 이하 | 0.01% 이하 |
| MTU | 1500 | 9000 (Jumbo Frame) |

### Jumbo Frame 설정

```bash
# MTU 설정 확인
ip link show eth0 | grep mtu

# MTU 9000으로 설정 (임시)
sudo ip link set dev eth0 mtu 9000

# 영구 설정 (Amazon Linux 2023 - NetworkManager)
sudo nmcli connection modify "System eth0" 802-3-ethernet.mtu 9000
sudo nmcli connection up "System eth0"

# 설정 확인
nmcli connection show "System eth0" | grep mtu
```

## IAM 자격 증명 프로바이더 설정

EKS Hybrid Nodes는 온프레미스 노드를 AWS에 인증하기 위해 다음 두 가지 중 하나의 자격 증명 프로바이더가 필요합니다.

### 옵션 A: SSM Hybrid Activations

SSM Hybrid Activations는 PKI 인프라가 필요 없는 간편한 옵션입니다.

```bash
# Hybrid 노드용 IAM 역할 생성
aws iam create-role \
  --role-name EKSHybridNodeRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ssm.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 필수 정책 연결
aws iam attach-role-policy \
  --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodeMinimalPolicy

aws iam attach-role-policy \
  --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# SSM Hybrid Activation 생성
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role EKSHybridNodeRole \
  --registration-limit 100 \
  --region ap-northeast-2
```

### 옵션 B: IAM Roles Anywhere

IAM Roles Anywhere는 기존 PKI의 X.509 인증서를 사용하며, 에어갭 환경에 적합합니다.

```bash
# 1. CA 인증서로 Trust Anchor 생성
aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled

# 2. IAM 역할에 매핑되는 Profile 생성
aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled

# 3. 각 노드에 대한 X.509 인증서 발급 (자체 CA 사용)
openssl req -new -key node.key -out node.csr -subj "/CN=hybrid-node-001"
openssl x509 -req -in node.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out node.crt -days 365

# 4. 인증서와 키를 노드에 배포
sudo mkdir -p /etc/iam/pki
sudo cp node.crt /etc/iam/pki/server.pem
sudo cp node.key /etc/iam/pki/server.key
```

## VPC 구성 요구 사항

EKS 클러스터 VPC는 Hybrid Nodes 연결을 지원하도록 적절히 구성되어야 합니다.

### 라우트 테이블 구성

VPC 라우트 테이블에 온프레미스 CIDR 경로를 추가해야 합니다:

| 대상 | 타겟 | 용도 |
|------|------|------|
| 10.0.0.0/16 (VPC CIDR) | local | VPC 내부 트래픽 |
| 10.80.0.0/16 (원격 노드 CIDR) | TGW/VGW | 온프레미스 노드로 라우팅 |
| 10.85.0.0/16 (원격 파드 CIDR) | TGW/VGW | 온프레미스 파드로 라우팅 |

### 보안 그룹 요구 사항

EKS는 `RemoteNodeNetwork` / `RemotePodNetwork` 지정 시 인바운드 규칙을 자동 생성합니다. 추가 아웃바운드 규칙은 수동으로 구성해야 합니다:

| 방향 | 프로토콜 | 포트 | 소스/대상 | 용도 |
|------|----------|------|-----------|------|
| 인바운드 (자동) | TCP | 443 | 원격 노드 CIDR | Kubelet → API 서버 |
| 인바운드 (자동) | TCP | 443 | 원격 파드 CIDR | Pod → API 서버 |
| 인바운드 (자동) | TCP | 10250 | 원격 노드 CIDR | API 서버 → Kubelet |
| 아웃바운드 (수동) | TCP | 10250 | 원격 노드 CIDR | API 서버 → Kubelet |
| 아웃바운드 (수동) | TCP | 웹훅 포트 | 원격 파드 CIDR | API 서버 → 웹훅 |

> **참고**: 보안 그룹당 인바운드 규칙 제한은 60개입니다. 다수의 CIDR을 사용하는 경우 규칙 수를 확인하세요.

### API 서버 엔드포인트 접근 모드

| 모드 | Kubelet 경로 | 사용 사례 |
|------|-------------|----------|
| **Public** | 인터넷 → EKS API 엔드포인트 | 간단한 설정, 온프레미스에서 인터넷 필요 |
| **Private** | VPN/DX → VPC ENI → API 서버 | 에어갭, 최고 수준 보안 **(권장)** |

> **경고**: **"Public and Private" 동시 사용 모드는 하이브리드 노드에서 사용하지 마세요.** 이 모드에서는 하이브리드 노드가 EKS API 엔드포인트를 퍼블릭 IP로만 resolve하여 VPN/Direct Connect를 통한 프라이빗 연결이 실패하고, 결과적으로 **노드가 클러스터에 조인하지 못합니다**. 반드시 Public 또는 Private 중 하나만 선택하세요.

> **권장 사항**: 프로덕션 하이브리드 환경에서는 **Private** 엔드포인트 접근 모드를 사용하세요.

## 하이브리드 노드용 EKS 클러스터 생성

하이브리드 노드 지원 EKS 클러스터 생성 시 다음 요구 사항이 적용됩니다:

- **인증 모드**: `API` 또는 `API_AND_CONFIG_MAP` 사용 필수
- **IP 주소 패밀리**: IPv4 사용 필수
- **엔드포인트 연결**: Public 또는 Private 중 하나만 사용 ("Public and Private" 동시 사용 **불가** — 하이브리드 노드 조인 실패)
- **원격 네트워크**: `RemoteNodeNetwork` 및 `RemotePodNetwork` CIDR 지정

### eksctl 사용

```yaml
# cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-hybrid-cluster
  region: ap-northeast-2
  version: "1.31"

remoteNetworkConfig:
  iam:
    provider: ssm  # 또는 IAM Roles Anywhere의 경우 'ira'
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
    - cidrs: ["10.80.0.0/16"]
  remotePodNetworks:
    - cidrs: ["10.85.0.0/16"]
```

```bash
eksctl create cluster -f cluster-config.yaml
```

### AWS CLI 사용

```bash
aws eks create-cluster \
    --name my-hybrid-cluster \
    --region ap-northeast-2 \
    --kubernetes-version 1.31 \
    --role-arn arn:aws:iam::123456789012:role/myAmazonEKSClusterRole \
    --resources-vpc-config subnetIds=subnet-xxx,subnet-yyy,securityGroupIds=sg-zzz,endpointPrivateAccess=true,endpointPublicAccess=false \
    --access-config authenticationMode=API_AND_CONFIG_MAP \
    --remote-network-config '{"remoteNodeNetworks":[{"cidrs":["10.80.0.0/16"]}],"remotePodNetworks":[{"cidrs":["10.85.0.0/16"]}]}'
```

### kubeconfig 업데이트

```bash
aws eks update-kubeconfig --name my-hybrid-cluster --region ap-northeast-2

# 클러스터 접근 확인
kubectl get svc
```

## 하이브리드 노드 지원 애드온

모든 EKS 애드온이 하이브리드 노드와 호환되는 것은 아닙니다. Amazon VPC CNI는 호환되지 **않습니다**.

### AWS 애드온

| 애드온 | 최소 호환 버전 |
|--------|---------------|
| kube-proxy | v1.25.14-eksbuild.2+ |
| CoreDNS | v1.9.3-eksbuild.7+ |
| ADOT (OpenTelemetry) | v0.102.1-eksbuild.2+ |
| CloudWatch Observability | v2.2.1-eksbuild.1+ |
| EKS Pod Identity Agent | v1.3.3-eksbuild.1+ |
| Node monitoring agent | v1.2.0-eksbuild.1+ |
| CSI snapshot controller | v8.1.0-eksbuild.1+ |

### 커뮤니티 애드온

| 애드온 | 최소 호환 버전 |
|--------|---------------|
| Kubernetes Metrics Server | v0.7.2-eksbuild.1+ |
| cert-manager | v1.17.2-eksbuild.1+ |
| Prometheus Node Exporter | v1.9.1-eksbuild.2+ |
| kube-state-metrics | v2.15.0-eksbuild.4+ |
| External DNS | v0.19.0-eksbuild.1+ |

---

< [목차](./README.md) | [다음: 네트워크 구성](./02-network-configuration.md) >
