# 前提条件

< [目次](./README.md) | [次へ: ネットワーク設定](02-network-configuration.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+ **最終更新**: February 23, 2026

このドキュメントでは、EKS Hybrid Nodes をデプロイするために必要なオンプレミスノード、GPU サーバー、およびネットワークインフラストラクチャのシステム要件について説明します。

## ネットワーク前提条件の概要

次の図は、VPC 設定、Transit Gateway/Virtual Private Gateway、および CIDR 要件を含む、オンプレミスノードを EKS cluster に接続するためのネットワーク前提条件を示しています。

![cluster の RemoteNodeNetwork および RemotePodNetwork 設定を、VPC 側とオンプレミス側の両方の route table に関連付けた Hybrid nodes の前提条件図。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## オンプレミスノードの要件

### サポート対象 Operating System

| Operating System | バージョン                               | アーキテクチャ   |
| ---------------- | ---------------------------------------- | -------------- |
| Ubuntu LTS       | 20.04, 22.04, 24.04                      | x86\_64, arm64 |
| RHEL             | 8, 9                                     | x86\_64, arm64 |
| Amazon Linux     | 2023                                     | x86\_64, arm64 |
| Bottlerocket     | v1.37.0 以降（VMware variant のみ）      | x86\_64 のみ   |

> **Bottlerocket に関する注意**: EKS Hybrid Nodes では Bottlerocket の VMware variant のみがサポートされ、Kubernetes v1.28 以降が必要です。Bottlerocket には必要な依存関係がすべて自動的に含まれるため、`nodeadm` CLI は不要です。Bottlerocket では ARM architecture はサポートされません。

> **ARM Architecture に関する注意**:
>
> * ARM node には **Crypto extension を備えた ARMv8.2 以降**が必要です（kube-proxy v1.31+ のため）
> * **Raspberry Pi（Pi 5 より前）は互換性がありません** — Crypto extension を欠く ARMv8.0 のみをサポートします
> * Pi 5（ARMv8.2）以降は互換性があります

### Container Runtime

```bash
# Check containerd version
containerd --version
# Required version: 1.6.x or higher

# Check Docker Engine version (includes containerd)
docker --version
# Required version: 20.10.10 or higher
```

> **OS 固有の containerd に関する注意**:
>
> * **Ubuntu 24.04**: containerd v1.7.19 以降、または AppArmor profile 設定の変更が必要です
> * **RHEL**: `--containerd-source distro` は**無効**です。`--containerd-source docker` を使用する必要があります
> * **Ubuntu 20.04 / RHEL 8**: デフォルト kernel は、Cilium v1.18.x に必要な 5.10 未満です

### 最小 Hardware 仕様

| リソース | 最小（AWS 公式） | 推奨            |
| -------- | ---------------------- | --------------- |
| CPU      | 1 vCPU           | 4 cores 以上    |
| RAM      | 1 GiB            | 8 GB 以上       |
| Disk     | 50 GB SSD        | 100 GB NVMe SSD |
| Network  | 100 Mbps         | 10 Gbps 以上    |

> **注意**: AWS 公式の最小値は 1 vCPU / 1 GiB ですが、実際の workload の実行には 2 cores / 4 GB 以上を推奨します。

### システム設定の確認

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

## AWS Packer Templates を使用した Node image のビルド

AWS は EKS Hybrid Nodes 用の node image をビルドするための Packer template の例を提供しています。これらの template は OVA（vSphere）、Qcow2、および Raw の出力形式をサポートします。

### Packer の前提条件

| Tool                  | 最小バージョン |
| --------------------- | --------------- |
| Packer                | v1.11.0+        |
| VMware vSphere Plugin | v1.4.0+         |
| QEMU Plugin           | 最新            |

### 環境変数

| 変数                  | 説明                                 | デフォルト |
| --------------------- | ------------------------------------ | ------- |
| `PKR_SSH_PASSWORD`    | SSH password                         | -       |
| `ISO_URL`             | OS ISO image URL                     | -       |
| `ISO_CHECKSUM`        | ISO checksum                         | -       |
| `CREDENTIAL_PROVIDER` | Credential provider（`ssm` または `iam`） | `ssm`   |
| `K8S_VERSION`         | Kubernetes version                   | -       |
| `NODEADM_ARCH`        | Architecture（`amd64` または `arm64`）    | `amd64` |

**RHEL 固有の変数:**

| 変数          | 説明                         |
| ------------- | ----------------------------- |
| `RH_USERNAME` | Red Hat subscription username |
| `RH_PASSWORD` | Red Hat subscription password |

**vSphere 固有の変数:**

| 変数                 | 説明                |
| -------------------- | ---------------------- |
| `VSPHERE_SERVER`     | vCenter server address |
| `VSPHERE_USER`       | vCenter username    |
| `VSPHERE_PASSWORD`   | vCenter password    |
| `VSPHERE_DATACENTER` | Datacenter name     |
| `VSPHERE_CLUSTER`    | Cluster name        |
| `VSPHERE_DATASTORE`  | Datastore name      |
| `VSPHERE_NETWORK`    | Network name        |

### ビルドコマンド

```bash
# Build vSphere OVA (Ubuntu 22.04)
packer build -only=general-build.vsphere-iso.ubuntu22 template.pkr.hcl

# Build QEMU image (RHEL 9)
packer build -only=general-build.qemu.rhel9 template.pkr.hcl

# Build Amazon Linux 2023
packer build -only=general-build.qemu.al2023 template.pkr.hcl
```

> **注意**: `CREDENTIAL_PROVIDER` 環境変数を `iam` に設定すると、IAM Roles Anywhere 用の image がビルドされます。デフォルトは `ssm` です。

## GPU Server の要件（オプション）

### NVIDIA Driver

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Required version: 550.x or higher

# Check CUDA version
nvcc --version
# Recommended version: CUDA 12.x
```

### サポート対象 GPU Model

| GPU Model   | VRAM     | 主な用途                         |
| ----------- | -------- | ---------------------------------- |
| NVIDIA H100 | 80 GB    | 大規模 LLM training/inference     |
| NVIDIA H200 | 141 GB   | 非常に大きな model                |
| NVIDIA A100 | 40/80 GB | AI/ML 汎用                        |
| NVIDIA L40S | 48 GB    | inference 最適化                  |

### GPU Driver のインストール

**Ubuntu 22.04 LTS（推奨）:**

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

## ネットワーク要件

### Bandwidth と Latency

| 項目        | 最小               | 推奨                 |
| ----------- | ------------------ | ------------------ |
| Bandwidth   | 100 Mbps           | 10 Gbps 以上        |
| Latency     | 200 ms RTT 以下    | 5 ms 以下           |
| Packet Loss | 0.1% 以下          | 0.01% 以下          |
| MTU         | 1500               | 9000（Jumbo Frame） |

### Jumbo Frame の設定

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

## IAM Credential Provider のセットアップ

EKS Hybrid Nodes では、オンプレミスノードを AWS で認証するために、2 種類の Credential provider のいずれかが必要です。

### オプション A: SSM Hybrid Activations

SSM Hybrid Activations は、PKI infrastructure を必要としない、よりシンプルなオプションです。

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

### オプション B: IAM Roles Anywhere

IAM Roles Anywhere は既存の PKI の X.509 certificate を使用するため、air-gap environment に最適です。

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

### CloudFormation ベースの IAM セットアップ

CLI の代わりに、CloudFormation を使用して IAM Role および関連リソースをセットアップできます。

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

### IAM Policy の詳細

Hybrid node Role に必要な IAM Policy の詳細です。

**必要な Managed Policy:**

| Policy                               | 目的                                          |
| ------------------------------------ | --------------------------------------------- |
| `AmazonEC2ContainerRegistryPullOnly` | ECR から container image を pull する         |
| `AmazonSSMManagedInstanceCore`       | SSM agent のコア機能（SSM 使用時）            |

**オプションの Policy:**

| Policy                              | 目的                       |
| ----------------------------------- | ------------------------ |
| `eks-auth:AssumeRoleForPodIdentity` | EKS Pod Identity のサポート |

**SSM Deregister Conditional Policy:**

複数 cluster environment では、`EKSClusterARN` condition tag を使用して、node が特定の cluster からのみ deregister できるようにします。

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

### IAM Roles Anywhere Trust Policy の詳細

IAM Roles Anywhere を使用する場合、Trust policy の設定は重要です。

**x509Subject/CN Mapping:**

certificate の CN（Common Name）は node name と一致している必要があります。これは audit tracking と node identification に使用されます。

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

**主要コンポーネント:**

| コンポーネント            | 説明                                      |
| ----------------------- | --------------------------------------- |
| `sts:SetSourceIdentity` | audit tracking 用に source identity を設定 |
| `sts:RoleSessionName`   | certificate CN に紐付く session name     |
| `x509Subject/CN`        | certificate CN は nodeName と一致必須      |

### Credential Duration の比較

| 項目                 | SSM              | IAM Roles Anywhere                                     |
| -------------------- | ---------------- | ------------------------------------------------------ |
| デフォルト Duration   | 1 hour（固定）    | 1 hour（設定可能）                                      |
| 最大 Duration        | 1 hour           | 12 hours                                               |
| Rotation             | AWS により自動    | 自動、`durationSeconds` に従う                         |
| `MaxSessionDuration` | N/A              | IAM Role の値は profile の `durationSeconds` を超える必要があります |
| 設定                 | 設定不可         | profile の `durationSeconds` parameter で設定          |

> **注意**: IAM Roles Anywhere を使用する場合、IAM Role の `MaxSessionDuration` は profile の `durationSeconds` 値より大きくなければなりません。そうでない場合、credential の取得に失敗します。

## Cluster Access の準備

Hybrid node が EKS cluster に参加するには、適切な access entry が必要です。

### HYBRID\_LINUX Access Entry（推奨）

`HYBRID_LINUX` access entry type は、hybrid node 向けに特別に設計されています。

```bash
aws eks create-access-entry \
  --cluster-name my-hybrid-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX
```

このコマンドにより、以下が自動的に設定されます。

* Username: <code v-pre>system:node:{{SessionName}}</code>
* Kubernetes group: `system:bootstrappers`、`system:nodes`

### aws-auth ConfigMap の代替方法

`API_AND_CONFIG_MAP` authentication mode を使用する場合は、代替として `aws-auth` ConfigMap を使用できます。

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

> **注意**: `aws-auth` ConfigMap の方法は legacy approach です。新しい cluster では、`HYBRID_LINUX` access entry を使用することを推奨します。

## VPC 設定の要件

EKS cluster VPC は、Hybrid Nodes connectivity をサポートするよう適切に設定する必要があります。

### Route Table の設定

VPC route table には、オンプレミス CIDR の route を含める必要があります。

| 宛先                            | Target  | 目的                           |
| ------------------------------- | ------- | ------------------------------ |
| 10.0.0.0/16 (VPC CIDR)          | local   | VPC 内部 traffic               |
| 10.80.0.0/16 (Remote Node CIDR) | TGW/VGW | オンプレミス node への route  |
| 10.85.0.0/16 (Remote Pod CIDR)  | TGW/VGW | オンプレミス Pod への route   |

### Security Group の要件

`RemoteNodeNetwork` / `RemotePodNetwork` を指定すると、EKS は inbound rule を自動作成します。追加の outbound rule は手動で設定する必要があります。

| 方向              | Protocol | Port          | Source/Destination | 目的                        |
| ----------------- | -------- | ------------- | ------------------ | --------------------------- |
| Inbound（自動）   | TCP      | 443           | Remote Node CIDR   | Kubelet → API Server        |
| Inbound（自動）   | TCP      | 443           | Remote Pod CIDR    | Pod → API Server            |
| Inbound（自動）   | TCP      | 10250         | Remote Node CIDR   | API Server → Kubelet        |
| Outbound（手動）  | TCP      | 10250         | Remote Node CIDR   | API Server → Kubelet        |
| Outbound（手動）  | TCP      | Webhook ports | Remote Pod CIDR    | API Server → Webhooks       |

> **注意**: Security Group あたりの inbound rule には 60 個の上限があります。複数の CIDR を使用する場合は rule 数を確認してください。

### API Server Endpoint Access Mode

| Mode        | Kubelet Path                  | ユースケース                                    |
| ----------- | ----------------------------- | -------------------------------------------- |
| **Public**  | Internet → EKS API endpoint   | シンプルなセットアップ、オンプレミスから internet が必要 |
| **Private** | VPN/DX → VPC ENI → API Server | air-gap、最大の security **（推奨）**          |

> **警告**: **hybrid node では「Public and Private」mode を使用しないでください。** この mode では、hybrid node は EKS API endpoint を public IP のみに解決するため、private VPN/Direct Connect 接続が失敗します。その結果、**node は cluster に参加できません**。Public または Private のいずれかを選択する必要があり、両方は選択できません。

> **推奨**: 本番 hybrid environment では **Private** endpoint access を使用してください。

## Hybrid Nodes 用 EKS Cluster の作成

Hybrid nodes support を備えた EKS cluster を作成する場合、次の要件が適用されます。

* **Authentication mode**: `API` または `API_AND_CONFIG_MAP` を使用する必要があります
* **IP address family**: IPv4 を使用する必要があります
* **Endpoint connectivity**: Public または Private のみを使用する必要があります（「Public and Private」は**サポートされません** — hybrid node の join failure を引き起こします）
* **Remote network**: `RemoteNodeNetwork` および `RemotePodNetwork` CIDR を指定します

### eksctl を使用する場合

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

### AWS CLI を使用する場合

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

## Hybrid Nodes でサポートされる Add-on

すべての EKS Add-on が hybrid node と互換性を持つわけではありません。Amazon VPC CNI は互換性が**ありません**。

### AWS Add-on

| Add-on                   | 最小互換バージョン           |
| ------------------------ | -------------------------- |
| kube-proxy               | v1.25.14-eksbuild.2+       |
| CoreDNS                  | v1.9.3-eksbuild.7+         |
| ADOT (OpenTelemetry)     | v0.102.1-eksbuild.2+       |
| CloudWatch Observability | v2.2.1-eksbuild.1+         |
| EKS Pod Identity Agent   | v1.3.3-eksbuild.1+         |
| Node monitoring agent    | v1.2.0-eksbuild.1+         |
| CSI snapshot controller  | v8.1.0-eksbuild.1+         |

### Community Add-on

| Add-on                    | 最小互換バージョン          |
| ------------------------- | -------------------------- |
| Kubernetes Metrics Server | v0.7.2-eksbuild.1+         |
| cert-manager              | v1.17.2-eksbuild.1+        |
| Prometheus Node Exporter  | v1.9.1-eksbuild.2+         |
| kube-state-metrics        | v2.15.0-eksbuild.4+        |
| External DNS              | v0.19.0-eksbuild.1+        |

***

< [目次](./README.md) | [次へ: ネットワーク設定](02-network-configuration.md) >
