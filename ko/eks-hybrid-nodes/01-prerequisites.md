# 사전 요구 사항

< [목차](./README.md) | [다음: 네트워크 구성](02-network-configuration.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+ **마지막 업데이트**: 2026년 2월 23일

이 문서에서는 EKS Hybrid Nodes를 구성하기 위한 온프레미스 노드, GPU 서버, 네트워크 요구 사항을 다룹니다.

## 네트워크 사전 요구 사항 개요

아래 다이어그램은 VPC 구성, Transit Gateway/Virtual Private Gateway, CIDR 요구 사항을 포함한 온프레미스 노드와 EKS 클러스터 연결을 위한 네트워크 사전 요구 사항을 보여줍니다.

![EKS Hybrid Nodes 네트워크 사전 요구 사항](../.gitbook/assets/hybrid-prereq-diagram.png)

## 온프레미스 노드 요구 사항

### 지원 운영 체제

| 운영 체제        | 버전                         | 아키텍처           |
| ------------ | -------------------------- | -------------- |
| Ubuntu LTS   | 20.04, 22.04, 24.04        | x86\_64, arm64 |
| RHEL         | 8, 9                       | x86\_64, arm64 |
| Amazon Linux | 2023                       | x86\_64, arm64 |
| Bottlerocket | v1.37.0 이상 (VMware 변형만 지원) | x86\_64만       |

> **Bottlerocket 참고 사항**: Bottlerocket은 VMware 변형만 EKS Hybrid Nodes에서 지원되며, Kubernetes v1.28 이상이 필요합니다. Bottlerocket은 필요한 의존성을 자체적으로 포함하고 있어 `nodeadm` CLI가 필요하지 않습니다. ARM 아키텍처는 Bottlerocket에서 지원되지 않습니다.

> **ARM 아키텍처 주의사항**:
>
> * ARM 노드는 **ARMv8.2 이상 + Crypto 확장** 필수 (kube-proxy v1.31+)
> * **Raspberry Pi (Pi 5 이전)는 호환되지 않음** — ARMv8.0만 지원하므로 Crypto 확장 누락
> * Pi 5 (ARMv8.2)부터 호환 가능

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
>
> * **Ubuntu 24.04**: containerd v1.7.19 이상이 필요하거나, AppArmor 프로필 구성 변경 필요
> * **RHEL**: `--containerd-source distro` 옵션은 **유효하지 않음**. 반드시 `--containerd-source docker` 사용
> * **Ubuntu 20.04 / RHEL 8**: Cilium v1.18.x 사용 시 커널 5.10 이상 필요 (기본 커널이 미달하므로 주의)

### 최소 하드웨어 사양

| 리소스  | 최소 사양 (AWS 공식) | 권장 사양           |
| ---- | -------------- | --------------- |
| CPU  | 1 vCPU         | 4 코어 이상         |
| RAM  | 1 GiB          | 8 GB 이상         |
| 디스크  | 50 GB SSD      | 100 GB NVMe SSD |
| 네트워크 | 100 Mbps       | 10 Gbps 이상      |

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

## AWS Packer 템플릿을 사용한 노드 이미지 빌드

AWS는 EKS Hybrid Nodes용 노드 이미지를 빌드하기 위한 예제 Packer 템플릿을 제공합니다. 이 템플릿은 OVA (vSphere), Qcow2, Raw 출력 형식을 지원합니다.

### Packer 사전 요구 사항

| 도구                  | 최소 버전    |
| ------------------- | -------- |
| Packer              | v1.11.0+ |
| VMware vSphere 플러그인 | v1.4.0+  |
| QEMU 플러그인           | 최신 버전    |

### 환경 변수

| 변수                    | 설명                           | 기본값     |
| --------------------- | ---------------------------- | ------- |
| `PKR_SSH_PASSWORD`    | SSH 비밀번호                     | -       |
| `ISO_URL`             | OS ISO 이미지 URL               | -       |
| `ISO_CHECKSUM`        | ISO 체크섬                      | -       |
| `CREDENTIAL_PROVIDER` | 자격 증명 프로바이더 (`ssm` 또는 `iam`) | `ssm`   |
| `K8S_VERSION`         | Kubernetes 버전                | -       |
| `NODEADM_ARCH`        | 아키텍처 (`amd64` 또는 `arm64`)    | `amd64` |

**RHEL 전용 변수:**

| 변수            | 설명              |
| ------------- | --------------- |
| `RH_USERNAME` | Red Hat 구독 사용자명 |
| `RH_PASSWORD` | Red Hat 구독 비밀번호 |

**vSphere 전용 변수:**

| 변수                   | 설명            |
| -------------------- | ------------- |
| `VSPHERE_SERVER`     | vCenter 서버 주소 |
| `VSPHERE_USER`       | vCenter 사용자명  |
| `VSPHERE_PASSWORD`   | vCenter 비밀번호  |
| `VSPHERE_DATACENTER` | 데이터센터 이름      |
| `VSPHERE_CLUSTER`    | 클러스터 이름       |
| `VSPHERE_DATASTORE`  | 데이터스토어 이름     |
| `VSPHERE_NETWORK`    | 네트워크 이름       |

### 빌드 명령어

```bash
# vSphere OVA 빌드 (Ubuntu 22.04)
packer build -only=general-build.vsphere-iso.ubuntu22 template.pkr.hcl

# QEMU 이미지 빌드 (RHEL 9)
packer build -only=general-build.qemu.rhel9 template.pkr.hcl

# Amazon Linux 2023 빌드
packer build -only=general-build.qemu.al2023 template.pkr.hcl
```

> **참고**: `CREDENTIAL_PROVIDER` 환경 변수를 `iam`으로 설정하면 IAM Roles Anywhere용 이미지가 빌드됩니다. 기본값은 `ssm`입니다.

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

| GPU 모델      | VRAM     | 주요 용도         |
| ----------- | -------- | ------------- |
| NVIDIA H100 | 80 GB    | 대규모 LLM 학습/추론 |
| NVIDIA H200 | 141 GB   | 초대규모 모델       |
| NVIDIA A100 | 40/80 GB | AI/ML 범용      |
| NVIDIA L40S | 48 GB    | 추론 최적화        |

### GPU 드라이버 설치

**Ubuntu 22.04 LTS (권장):**

```bash
# 커널 헤더 설치
sudo apt-get install -y linux-headers-$(uname -r)

# NVIDIA 드라이버 저장소 추가
distribution=$(. /etc/os-release;echo $ID$VERSION_ID | sed -e 's/\.//g')
wget https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# 드라이버 설치
sudo apt-get install -y cuda-drivers-550

# NVIDIA Container Toolkit 설치
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# containerd 설정 업데이트
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

**RHEL 9:**

```bash
# 커널 개발 패키지 설치
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)

# NVIDIA 드라이버 저장소 추가
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo

# 드라이버 설치
sudo dnf module install -y nvidia-driver:550-dkms

# NVIDIA Container Toolkit 설치
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit

# containerd 설정 업데이트
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## 네트워크 요구 사항

### 대역폭 및 지연 시간

| 항목    | 최소 요구         | 권장 사양              |
| ----- | ------------- | ------------------ |
| 대역폭   | 100 Mbps      | 10 Gbps 이상         |
| 지연 시간 | 200 ms RTT 이하 | 5 ms 이하            |
| 패킷 손실 | 0.1% 이하       | 0.01% 이하           |
| MTU   | 1500          | 9000 (Jumbo Frame) |

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

### CloudFormation 기반 IAM 설정

CLI 대신 CloudFormation을 사용하여 IAM 역할 및 관련 리소스를 설정할 수 있습니다.

**SSM용 CloudFormation 템플릿:**

```bash
# 템플릿 다운로드
curl -OL 'https://raw.githubusercontent.com/aws/eks-hybrid/refs/heads/main/example/hybrid-ssm-cfn.yaml'

# 파라미터 파일 생성
cat > cfn-ssm-parameters.json << 'EOF'
[
  {"ParameterKey": "RoleName", "ParameterValue": "EKSHybridNodeRole"},
  {"ParameterKey": "SSMDeregisterConditionTagKey", "ParameterValue": "EKSClusterARN"},
  {"ParameterKey": "SSMDeregisterConditionTagValue", "ParameterValue": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"}
]
EOF

# 스택 배포
aws cloudformation create-stack \
  --stack-name eks-hybrid-ssm-role \
  --template-body file://hybrid-ssm-cfn.yaml \
  --parameters file://cfn-ssm-parameters.json \
  --capabilities CAPABILITY_NAMED_IAM
```

**IAM Roles Anywhere용 CloudFormation 템플릿:**

```bash
# 템플릿 다운로드
curl -OL 'https://raw.githubusercontent.com/aws/eks-hybrid/refs/heads/main/example/hybrid-ira-cfn.yaml'

# 파라미터 파일 생성
cat > cfn-iamra-parameters.json << 'EOF'
[
  {"ParameterKey": "RoleName", "ParameterValue": "EKSHybridNodeRole"},
  {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "CN"},
  {"ParameterKey": "CABundleCert", "ParameterValue": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"}
]
EOF

# 스택 배포
aws cloudformation create-stack \
  --stack-name eks-hybrid-iamra-role \
  --template-body file://hybrid-ira-cfn.yaml \
  --parameters file://cfn-iamra-parameters.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### IAM 정책 상세

하이브리드 노드 역할에 필요한 IAM 정책 세부 사항입니다.

**필수 관리형 정책:**

| 정책                                   | 용도                        |
| ------------------------------------ | ------------------------- |
| `AmazonEC2ContainerRegistryPullOnly` | ECR에서 컨테이너 이미지 풀          |
| `AmazonSSMManagedInstanceCore`       | SSM 에이전트 핵심 기능 (SSM 사용 시) |

**선택적 정책:**

| 정책                                  | 용도                  |
| ----------------------------------- | ------------------- |
| `eks-auth:AssumeRoleForPodIdentity` | EKS Pod Identity 지원 |

**SSM Deregister 조건부 정책:**

멀티 클러스터 환경에서 노드가 특정 클러스터에서만 등록 해제되도록 `EKSClusterARN` 조건 태그를 사용합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:DeregisterManagedInstance",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/EKSClusterARN": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
        }
      }
    }
  ]
}
```

### IAM Roles Anywhere 신뢰 정책 상세

IAM Roles Anywhere를 사용할 때 신뢰 정책 구성이 중요합니다.

**x509Subject/CN 매핑:**

인증서의 CN(Common Name)이 노드 이름과 일치해야 합니다. 이는 감사 추적 및 노드 식별에 사용됩니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ],
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/x509Subject/CN": "${aws:RequestTag/x509Subject/CN}"
        },
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/TRUST_ANCHOR_ID"
        }
      }
    }
  ]
}
```

**주요 구성 요소:**

| 요소                      | 설명                        |
| ----------------------- | ------------------------- |
| `sts:SetSourceIdentity` | 감사 추적을 위한 소스 ID 설정        |
| `sts:RoleSessionName`   | 인증서 CN에 바인딩되는 세션 이름       |
| `x509Subject/CN`        | 인증서의 CN이 nodeName과 일치해야 함 |

### 자격 증명 기간 비교

| 측면                   | SSM         | IAM Roles Anywhere                        |
| -------------------- | ----------- | ----------------------------------------- |
| 기본 기간                | 1시간 (고정)    | 1시간 (구성 가능)                               |
| 최대 기간                | 1시간         | 12시간                                      |
| 갱신 방식                | AWS에서 자동 갱신 | 자동 갱신, `durationSeconds` 설정 준수            |
| `MaxSessionDuration` | 해당 없음       | IAM 역할의 값이 프로필의 `durationSeconds`를 초과해야 함 |
| 구성 방법                | 구성 불가       | 프로필의 `durationSeconds` 파라미터로 설정           |

> **참고**: IAM Roles Anywhere 사용 시, IAM 역할의 `MaxSessionDuration`이 프로필의 `durationSeconds` 값보다 커야 합니다. 그렇지 않으면 자격 증명 획득에 실패합니다.

## 클러스터 액세스 준비

하이브리드 노드가 EKS 클러스터에 조인하려면 적절한 액세스 항목을 구성해야 합니다.

### HYBRID\_LINUX 액세스 항목 (권장)

`HYBRID_LINUX` 액세스 항목 유형은 하이브리드 노드를 위해 특별히 설계되었습니다:

```bash
aws eks create-access-entry \
  --cluster-name my-hybrid-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX
```

이 명령은 자동으로 다음을 설정합니다:

* 사용자 이름: <code v-pre>system:node:{{SessionName}}</code>
* Kubernetes 그룹: `system:bootstrappers`, `system:nodes`

### aws-auth ConfigMap 대안

`API_AND_CONFIG_MAP` 인증 모드를 사용하는 경우, `aws-auth` ConfigMap을 대안으로 사용할 수 있습니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - groups:
      - system:bootstrappers
      - system:nodes
      rolearn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      username: system:node:{{SessionName}}
```

```bash
kubectl apply -f aws-auth-cm.yaml
```

> **주의**: `aws-auth` ConfigMap 방식은 레거시 방식입니다. 새 클러스터에서는 `HYBRID_LINUX` 액세스 항목 사용을 권장합니다.

## VPC 구성 요구 사항

EKS 클러스터 VPC는 Hybrid Nodes 연결을 지원하도록 적절히 구성되어야 합니다.

### 라우트 테이블 구성

VPC 라우트 테이블에 온프레미스 CIDR 경로를 추가해야 합니다:

| 대상                        | 타겟      | 용도            |
| ------------------------- | ------- | ------------- |
| 10.0.0.0/16 (VPC CIDR)    | local   | VPC 내부 트래픽    |
| 10.80.0.0/16 (원격 노드 CIDR) | TGW/VGW | 온프레미스 노드로 라우팅 |
| 10.85.0.0/16 (원격 파드 CIDR) | TGW/VGW | 온프레미스 파드로 라우팅 |

### 보안 그룹 요구 사항

EKS는 `RemoteNodeNetwork` / `RemotePodNetwork` 지정 시 인바운드 규칙을 자동 생성합니다. 추가 아웃바운드 규칙은 수동으로 구성해야 합니다:

| 방향         | 프로토콜 | 포트    | 소스/대상      | 용도               |
| ---------- | ---- | ----- | ---------- | ---------------- |
| 인바운드 (자동)  | TCP  | 443   | 원격 노드 CIDR | Kubelet → API 서버 |
| 인바운드 (자동)  | TCP  | 443   | 원격 파드 CIDR | Pod → API 서버     |
| 인바운드 (자동)  | TCP  | 10250 | 원격 노드 CIDR | API 서버 → Kubelet |
| 아웃바운드 (수동) | TCP  | 10250 | 원격 노드 CIDR | API 서버 → Kubelet |
| 아웃바운드 (수동) | TCP  | 웹훅 포트 | 원격 파드 CIDR | API 서버 → 웹훅      |

> **참고**: 보안 그룹당 인바운드 규칙 제한은 60개입니다. 다수의 CIDR을 사용하는 경우 규칙 수를 확인하세요.

### API 서버 엔드포인트 접근 모드

| 모드          | Kubelet 경로                | 사용 사례                  |
| ----------- | ------------------------- | ---------------------- |
| **Public**  | 인터넷 → EKS API 엔드포인트       | 간단한 설정, 온프레미스에서 인터넷 필요 |
| **Private** | VPN/DX → VPC ENI → API 서버 | 에어갭, 최고 수준 보안 **(권장)** |

> **경고**: **"Public and Private" 동시 사용 모드는 하이브리드 노드에서 사용하지 마세요.** 이 모드에서는 하이브리드 노드가 EKS API 엔드포인트를 퍼블릭 IP로만 resolve하여 VPN/Direct Connect를 통한 프라이빗 연결이 실패하고, 결과적으로 **노드가 클러스터에 조인하지 못합니다**. 반드시 Public 또는 Private 중 하나만 선택하세요.

> **권장 사항**: 프로덕션 하이브리드 환경에서는 **Private** 엔드포인트 접근 모드를 사용하세요.

## 하이브리드 노드용 EKS 클러스터 생성

하이브리드 노드 지원 EKS 클러스터 생성 시 다음 요구 사항이 적용됩니다:

* **인증 모드**: `API` 또는 `API_AND_CONFIG_MAP` 사용 필수
* **IP 주소 패밀리**: IPv4 사용 필수
* **엔드포인트 연결**: Public 또는 Private 중 하나만 사용 ("Public and Private" 동시 사용 **불가** — 하이브리드 노드 조인 실패)
* **원격 네트워크**: `RemoteNodeNetwork` 및 `RemotePodNetwork` CIDR 지정

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

| 애드온                      | 최소 호환 버전             |
| ------------------------ | -------------------- |
| kube-proxy               | v1.25.14-eksbuild.2+ |
| CoreDNS                  | v1.9.3-eksbuild.7+   |
| ADOT (OpenTelemetry)     | v0.102.1-eksbuild.2+ |
| CloudWatch Observability | v2.2.1-eksbuild.1+   |
| EKS Pod Identity Agent   | v1.3.3-eksbuild.1+   |
| Node monitoring agent    | v1.2.0-eksbuild.1+   |
| CSI snapshot controller  | v8.1.0-eksbuild.1+   |

### 커뮤니티 애드온

| 애드온                       | 최소 호환 버전            |
| ------------------------- | ------------------- |
| Kubernetes Metrics Server | v0.7.2-eksbuild.1+  |
| cert-manager              | v1.17.2-eksbuild.1+ |
| Prometheus Node Exporter  | v1.9.1-eksbuild.2+  |
| kube-state-metrics        | v2.15.0-eksbuild.4+ |
| External DNS              | v0.19.0-eksbuild.1+ |

***

< [목차](./README.md) | [다음: 네트워크 구성](02-network-configuration.md) >
