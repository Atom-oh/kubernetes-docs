# 前提条件

< [目次](./) | [次へ: ネットワーク設定](02-network-configuration.md) >

> **対応バージョン**: EKS 1.31+, nodeadm 0.1+ **最終更新**: February 23, 2026

このドキュメントでは、EKS Hybrid Nodes をデプロイするために必要なオンプレミス Node、GPU server、およびネットワークインフラストラクチャのシステム要件について説明します。

## ネットワーク前提条件の概要

次の図は、オンプレミス Node を EKS cluster に接続するためのネットワーク前提条件を示しています。これには、VPC 設定、Transit Gateway/Virtual Private Gateway、および CIDR 要件が含まれます。

![EKS Hybrid Nodes ネットワーク前提条件](../.gitbook/assets/hybrid-prereq-diagram.png)

## オンプレミス Node 要件

### 対応 Operating Systems

| Operating System | Version                                  | Architecture   |
| ---------------- | ---------------------------------------- | -------------- |
| Ubuntu LTS       | 20.04, 22.04, 24.04                      | x86\_64, arm64 |
| RHEL             | 8, 9                                     | x86\_64, arm64 |
| Amazon Linux     | 2023                                     | x86\_64, arm64 |
| Bottlerocket     | v1.37.0 以上 (VMware variants のみ)      | x86\_64 のみ   |

> **Bottlerocket の注記**: EKS Hybrid Nodes でサポートされる Bottlerocket は VMware variants のみであり、Kubernetes v1.28 以降が必要です。Bottlerocket には必要な依存関係がすべて自動的に含まれるため、`nodeadm` CLI は不要です。Bottlerocket では ARM architecture はサポートされていません。

> **ARM Architecture の注記**:
>
> * ARM nodes には **Crypto extension を備えた ARMv8.2 以降** が必要です (kube-proxy v1.31+ の場合)
> * **Raspberry Pi (pre-Pi 5) は互換性がありません** — Crypto extension を備えていない ARMv8.0 のみをサポートしています
> * Pi 5 (ARMv8.2) 以降は互換性があります

### Container Runtime

```bash
# Check containerd version
containerd --version
# Required version: 1.6.x or higher

# Check Docker Engine version (includes containerd)
docker --version
# Required version: 20.10.10 or higher
```

> **OS 固有の containerd 注記**:
>
> * **Ubuntu 24.04**: containerd v1.7.19 以降、または AppArmor profile 設定の変更が必要です
> * **RHEL**: `--containerd-source distro` は **有効ではありません**。`--containerd-source docker` を使用する必要があります
> * **Ubuntu 20.04 / RHEL 8**: デフォルト kernel は 5.10 未満であり、Cilium v1.18.x に必要です

### 最小 Hardware 仕様

| Resource | Minimum (AWS Official) | Recommended       |
| -------- | ---------------------- | ----------------- |
| CPU      | 1 vCPU                 | 4 cores 以上      |
| RAM      | 1 GiB                  | 8 GB 以上         |
| Disk     | 50 GB SSD              | 100 GB NVMe SSD   |
| Network  | 100 Mbps               | 10 Gbps 以上      |

> **注記**: AWS 公式の最小要件は 1 vCPU / 1 GiB ですが、実際の workload を実行するには 2 cores / 4 GB 以上を推奨します。

### System Configuration Check

```bash
# Verify swap is disabled
free -h
# Swap should be 0

# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load required kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Set kernel parameters
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

## AWS Packer Templates を使用した Node Images の構築

AWS は、EKS Hybrid Nodes 用の node images を構築するための Packer templates の例を提供しています。これらの templates は、OVA (vSphere)、Qcow2、および Raw の出力形式をサポートしています。

### Packer 前提条件

| Tool                  | Minimum Version |
| --------------------- | --------------- |
| Packer                | v1.11.0+        |
| VMware vSphere Plugin | v1.4.0+         |
| QEMU Plugin           | 最新            |

### Environment Variables

| Variable              | Description                              | Default |
| --------------------- | ---------------------------------------- | ------- |
| `PKR_SSH_PASSWORD`    | SSH password                             | -       |
| `ISO_URL`             | OS ISO image URL                         | -       |
| `ISO_CHECKSUM`        | ISO checksum                             | -       |
| `CREDENTIAL_PROVIDER` | Credential provider (`ssm` または `iam`) | `ssm`   |
| `K8S_VERSION`         | Kubernetes version                       | -       |
| `NODEADM_ARCH`        | Architecture (`amd64` または `arm64`)    | `amd64` |

**RHEL 固有の Variables:**

| Variable      | Description                    |
| ------------- | ------------------------------ |
| `RH_USERNAME` | Red Hat subscription username  |
| `RH_PASSWORD` | Red Hat subscription password  |

**vSphere 固有の Variables:**

| Variable             | Description             |
| -------------------- | ----------------------- |
| `VSPHERE_SERVER`     | vCenter server address  |
| `VSPHERE_USER`       | vCenter username        |
| `VSPHERE_PASSWORD`   | vCenter password        |
| `VSPHERE_DATACENTER` | Datacenter name         |
| `VSPHERE_CLUSTER`    | Cluster name            |
| `VSPHERE_DATASTORE`  | Datastore name          |
| `VSPHERE_NETWORK`    | Network name            |

### Build Commands

```bash
# Build vSphere OVA (Ubuntu 22.04)
packer build -only=general-build.vsphere-iso.ubuntu22 template.pkr.hcl

# Build QEMU image (RHEL 9)
packer build -only=general-build.qemu.rhel9 template.pkr.hcl

# Build Amazon Linux 2023
packer build -only=general-build.qemu.al2023 template.pkr.hcl
```

> **注記**: `CREDENTIAL_PROVIDER` environment variable を `iam` に設定すると、IAM Roles Anywhere 用の image が構築されます。デフォルトは `ssm` です。

## GPU Server 要件 (任意)

### NVIDIA Driver

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Required version: 550.x or higher

# Check CUDA version
nvcc --version
# Recommended version: CUDA 12.x
```

### 対応 GPU Models

| GPU Model   | VRAM     | Primary Use                     |
| ----------- | -------- | ------------------------------- |
| NVIDIA H100 | 80 GB    | 大規模 LLM training/inference   |
| NVIDIA H200 | 141 GB   | 非常に大規模な models           |
| NVIDIA A100 | 40/80 GB | AI/ML 汎用                      |
| NVIDIA L40S | 48 GB    | Inference に最適化              |

### GPU Driver Installation

**Ubuntu 22.04 LTS (推奨):**

```bash
# Install kernel headers
sudo apt-get install -y linux-headers-$(uname -r)

# Add NVIDIA driver repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID | sed -e 's/\.//g')
wget https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# Install driver
sudo apt-get install -y cuda-drivers-550

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Update containerd configuration
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

**RHEL 9:**

```bash
# Install kernel development packages
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)

# Add NVIDIA driver repository
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo

# Install driver
sudo dnf module install -y nvidia-driver:550-dkms

# Install NVIDIA Container Toolkit
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit

# Update containerd configuration
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## Network 要件

### Bandwidth と Latency

| Item        | Minimum            | Recommended          |
| ----------- | ------------------ | -------------------- |
| Bandwidth   | 100 Mbps           | 10 Gbps 以上         |
| Latency     | 200 ms RTT 以下    | 5 ms 以下            |
| Packet Loss | 0.1% 以下          | 0.01% 以下           |
| MTU         | 1500               | 9000 (Jumbo Frame)   |

### Jumbo Frame Configuration

```bash
# Check MTU setting
ip link show eth0 | grep mtu

# Set MTU to 9000 (temporary)
sudo ip link set dev eth0 mtu 9000

# Permanent configuration (Amazon Linux 2023 - NetworkManager)
sudo nmcli connection modify "System eth0" 802-3-ethernet.mtu 9000
sudo nmcli connection up "System eth0"

# Verify configuration
nmcli connection show "System eth0" | grep mtu
```

## IAM Credential Provider Setup

EKS Hybrid Nodes では、オンプレミス Node を AWS に対して認証するために、2 つの credential providers のいずれかが必要です。

### Option A: SSM Hybrid Activations

SSM Hybrid Activations は、PKI infrastructure を必要としない、より簡単な option です。

```bash
# Create IAM role for hybrid nodes
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

# Attach required policies
aws iam attach-role-policy \
  --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodeMinimalPolicy

aws iam attach-role-policy \
  --role-name EKSHybridNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create SSM Hybrid Activation
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role EKSHybridNodeRole \
  --registration-limit 100 \
  --region ap-northeast-2
```

### Option B: IAM Roles Anywhere

IAM Roles Anywhere は、既存の PKI からの X.509 certificates を使用し、air-gap environments に適しています。

```bash
# 1. Create Trust Anchor with your CA certificate
aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled

# 2. Create Profile that maps to an IAM Role
aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled

# 3. Issue X.509 certificate for each node (using your CA)
openssl req -new -key node.key -out node.csr -subj "/CN=hybrid-node-001"
openssl x509 -req -in node.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out node.crt -days 365

# 4. Distribute cert and key to node
sudo mkdir -p /etc/iam/pki
sudo cp node.crt /etc/iam/pki/server.pem
sudo cp node.key /etc/iam/pki/server.key
```

### CloudFormation-Based IAM Setup

CLI の代わりに CloudFormation を使用して、IAM roles と関連 resources をセットアップできます。

**SSM 用 CloudFormation Template:**

```bash
# Download template
curl -OL 'https://raw.githubusercontent.com/aws/eks-hybrid/refs/heads/main/example/hybrid-ssm-cfn.yaml'

# Create parameter file
cat > cfn-ssm-parameters.json << 'EOF'
[
  {"ParameterKey": "RoleName", "ParameterValue": "EKSHybridNodeRole"},
  {"ParameterKey": "SSMDeregisterConditionTagKey", "ParameterValue": "EKSClusterARN"},
  {"ParameterKey": "SSMDeregisterConditionTagValue", "ParameterValue": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"}
]
EOF

# Deploy stack
aws cloudformation create-stack \
  --stack-name eks-hybrid-ssm-role \
  --template-body file://hybrid-ssm-cfn.yaml \
  --parameters file://cfn-ssm-parameters.json \
  --capabilities CAPABILITY_NAMED_IAM
```

**IAM Roles Anywhere 用 CloudFormation Template:**

```bash
# Download template
curl -OL 'https://raw.githubusercontent.com/aws/eks-hybrid/refs/heads/main/example/hybrid-ira-cfn.yaml'

# Create parameter file
cat > cfn-iamra-parameters.json << 'EOF'
[
  {"ParameterKey": "RoleName", "ParameterValue": "EKSHybridNodeRole"},
  {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "CN"},
  {"ParameterKey": "CABundleCert", "ParameterValue": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"}
]
EOF

# Deploy stack
aws cloudformation create-stack \
  --stack-name eks-hybrid-iamra-role \
  --template-body file://hybrid-ira-cfn.yaml \
  --parameters file://cfn-iamra-parameters.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### IAM Policy Details

Hybrid node role に必要な IAM policies の詳細です。

**Required Managed Policies:**

| Policy                               | Purpose                                |
| ------------------------------------ | -------------------------------------- |
| `AmazonEC2ContainerRegistryPullOnly` | ECR から container images を pull      |
| `AmazonSSMManagedInstanceCore`       | SSM agent の core 機能 (SSM 使用時)    |

**Optional Policies:**

| Policy                              | Purpose                  |
| ----------------------------------- | ------------------------ |
| `eks-auth:AssumeRoleForPodIdentity` | EKS Pod Identity support |

**SSM Deregister Conditional Policy:**

複数 cluster 環境では、`EKSClusterARN` condition tag を使用して、nodes が特定の clusters からのみ登録解除できるようにします。

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

### IAM Roles Anywhere Trust Policy Details

IAM Roles Anywhere を使用する場合、trust policy configuration は非常に重要です。

**x509Subject/CN Mapping:**

Certificate の CN (Common Name) は node name と一致している必要があります。これは audit tracking と node identification に使用されます。

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

**Key Components:**

| Component               | Description                                  |
| ----------------------- | -------------------------------------------- |
| `sts:SetSourceIdentity` | audit tracking 用の source identity を設定   |
| `sts:RoleSessionName`   | certificate CN に紐づく session name         |
| `x509Subject/CN`        | Certificate CN は nodeName と一致が必要      |

### Credential Duration Comparison

| Aspect               | SSM                | IAM Roles Anywhere                                             |
| -------------------- | ------------------ | -------------------------------------------------------------- |
| Default Duration     | 1 hour (固定)      | 1 hour (設定可能)                                              |
| Maximum Duration     | 1 hour             | 12 hours                                                       |
| Rotation             | AWS により自動     | 自動、`durationSeconds` に従う                                 |
| `MaxSessionDuration` | N/A                | IAM role value は profile の `durationSeconds` を超える必要あり |
| Configuration        | 設定不可           | profile の `durationSeconds` parameter で設定                  |

> **注記**: IAM Roles Anywhere を使用する場合、IAM role の `MaxSessionDuration` は profile の `durationSeconds` 値より大きくする必要があります。そうでない場合、credential acquisition は失敗します。

## Cluster Access Preparation

Hybrid nodes が EKS cluster に参加するには、適切な access entries が必要です。

### HYBRID\_LINUX Access Entry (推奨)

`HYBRID_LINUX` access entry type は hybrid nodes 専用に設計されています。

```bash
aws eks create-access-entry \
  --cluster-name my-hybrid-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX
```

この command は次を自動的に設定します。

* Username: <code v-pre>system:node:{{SessionName}}</code>
* Kubernetes groups: `system:bootstrappers`, `system:nodes`

### aws-auth ConfigMap Alternative

`API_AND_CONFIG_MAP` authentication mode を使用する場合、代替として `aws-auth` ConfigMap を使用できます。

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

> **注記**: `aws-auth` ConfigMap method は legacy approach です。新しい clusters では、`HYBRID_LINUX` access entry の使用を推奨します。

## VPC Configuration Requirements

EKS cluster VPC は、Hybrid Nodes connectivity をサポートするように適切に設定されている必要があります。

### Route Table Configuration

VPC route tables には、オンプレミス CIDRs の routes を含める必要があります。

| Destination                     | Target  | Purpose                       |
| ------------------------------- | ------- | ----------------------------- |
| 10.0.0.0/16 (VPC CIDR)          | local   | VPC internal traffic          |
| 10.80.0.0/16 (Remote Node CIDR) | TGW/VGW | オンプレミス nodes への route |
| 10.85.0.0/16 (Remote Pod CIDR)  | TGW/VGW | オンプレミス pods への route  |

### Security Group Requirements

`RemoteNodeNetwork` / `RemotePodNetwork` が指定されると、EKS は inbound rules を自動作成します。追加の outbound rules は手動で設定する必要があります。

| Direction         | Protocol | Port          | Source/Destination | Purpose               |
| ----------------- | -------- | ------------- | ------------------ | --------------------- |
| Inbound (auto)    | TCP      | 443           | Remote Node CIDR   | Kubelet → API Server  |
| Inbound (auto)    | TCP      | 443           | Remote Pod CIDR    | Pod → API Server      |
| Inbound (auto)    | TCP      | 10250         | Remote Node CIDR   | API Server → Kubelet  |
| Outbound (manual) | TCP      | 10250         | Remote Node CIDR   | API Server → Kubelet  |
| Outbound (manual) | TCP      | Webhook ports | Remote Pod CIDR    | API Server → Webhooks |

> **注記**: Security group ごとに inbound rules は 60 個までという制限があります。複数の CIDRs を使用する場合は、rule counts を確認してください。

### API Server Endpoint Access Modes

| Mode        | Kubelet Path                  | Use Case                                                |
| ----------- | ----------------------------- | ------------------------------------------------------- |
| **Public**  | Internet → EKS API endpoint   | Simple setup、オンプレミスからの Internet が必要        |
| **Private** | VPN/DX → VPC ENI → API Server | Air-gap、最大限の security **(推奨)**                   |

> **警告**: **Hybrid nodes では "Public and Private" mode を使用しないでください。** この mode では、hybrid nodes が EKS API endpoint を public IPs のみに解決するため、private VPN/Direct Connect connections が失敗します。その結果、**nodes が cluster に参加できなくなります**。Public または Private のいずれかを選択する必要があり、両方は選択できません。

> **推奨**: Production hybrid environments では **Private** endpoint access を使用してください。

## Hybrid Nodes 向け EKS Cluster Creation

Hybrid nodes support 付きで EKS cluster を作成する場合、次の要件が適用されます。

* **Authentication mode**: `API` または `API_AND_CONFIG_MAP` を使用する必要があります
* **IP address family**: IPv4 を使用する必要があります
* **Endpoint connectivity**: Public または Private のどちらかのみを使用する必要があります ("Public and Private" は **サポートされません** — hybrid node の join failures を引き起こします)
* **Remote networks**: `RemoteNodeNetwork` および `RemotePodNetwork` CIDRs を指定します

### eksctl の使用

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
    provider: ssm  # or 'ira' for IAM Roles Anywhere
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
    - cidrs: ["10.80.0.0/16"]
  remotePodNetworks:
    - cidrs: ["10.85.0.0/16"]
```

```bash
eksctl create cluster -f cluster-config.yaml
```

### AWS CLI の使用

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

### kubeconfig の更新

```bash
aws eks update-kubeconfig --name my-hybrid-cluster --region ap-northeast-2

# Verify cluster access
kubectl get svc
```

## Hybrid Nodes 対応 Add-ons

すべての EKS add-ons が hybrid nodes と互換性があるわけではありません。Amazon VPC CNI は互換性が **ありません**。

### AWS Add-ons

| Add-on                   | Minimum Compatible Version |
| ------------------------ | -------------------------- |
| kube-proxy               | v1.25.14-eksbuild.2+       |
| CoreDNS                  | v1.9.3-eksbuild.7+         |
| ADOT (OpenTelemetry)     | v0.102.1-eksbuild.2+       |
| CloudWatch Observability | v2.2.1-eksbuild.1+         |
| EKS Pod Identity Agent   | v1.3.3-eksbuild.1+         |
| Node monitoring agent    | v1.2.0-eksbuild.1+         |
| CSI snapshot controller  | v8.1.0-eksbuild.1+         |

### Community Add-ons

| Add-on                    | Minimum Compatible Version |
| ------------------------- | -------------------------- |
| Kubernetes Metrics Server | v0.7.2-eksbuild.1+         |
| cert-manager              | v1.17.2-eksbuild.1+        |
| Prometheus Node Exporter  | v1.9.1-eksbuild.2+         |
| kube-state-metrics        | v2.15.0-eksbuild.4+        |
| External DNS              | v0.19.0-eksbuild.1+        |

***

< [目次](./) | [次へ: ネットワーク設定](02-network-configuration.md) >
