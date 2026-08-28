# 前提条件

< [目次](./README.md) | [次へ: ネットワーク設定](02-network-configuration.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+ **最終更新**: February 23, 2026

このドキュメントでは、EKS Hybrid Nodes をデプロイするために必要なオンプレミスノード、GPU サーバー、およびネットワークインフラストラクチャのシステム要件について説明します。

## ネットワーク前提条件の概要

次の図は、VPC 設定、Transit Gateway/Virtual Private Gateway、および CIDR 要件を含む、オンプレミスノードを EKS クラスターに接続するためのネットワーク前提条件を示しています。

![EKS Hybrid Nodes のネットワーク前提条件](../.gitbook/assets/hybrid-prereq-diagram.png)

## オンプレミスノードの要件

### サポート対象のオペレーティングシステム

| オペレーティングシステム | バージョン                                  | アーキテクチャ   |
| ---------------- | ---------------------------------------- | -------------- |
| Ubuntu LTS       | 20.04, 22.04, 24.04                      | x86\_64, arm64 |
| RHEL             | 8, 9                                     | x86\_64, arm64 |
| Amazon Linux     | 2023                                     | x86\_64, arm64 |
| Bottlerocket     | v1.37.0 以降 (VMware バリアントのみ) | x86\_64 のみ   |

> **Bottlerocket に関する注意**: EKS Hybrid Nodes でサポートされるのは Bottlerocket の VMware バリアントのみで、Kubernetes v1.28 以降が必要です。Bottlerocket には必要なすべての依存関係が自動的に含まれるため、`nodeadm` CLI は不要です。Bottlerocket では ARM アーキテクチャはサポートされません。

> **ARM アーキテクチャに関する注意**:
>
> * ARM ノードには **Crypto 拡張を備えた ARMv8.2 以降** が必要です (kube-proxy v1.31+ 向け)
> * **Raspberry Pi (Pi 5 より前) は互換性がありません** — Crypto 拡張を持たない ARMv8.0 のみをサポートしています
> * Pi 5 (ARMv8.2) 以降は互換性があります

### コンテナランタイム

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
> * **Ubuntu 24.04**: containerd v1.7.19 以降、または AppArmor プロファイル設定の変更が必要です
> * **RHEL**: `--containerd-source distro` は**有効ではありません**。`--containerd-source docker` を使用する必要があります
> * **Ubuntu 20.04 / RHEL 8**: デフォルトカーネルは Cilium v1.18.x に必要な 5.10 未満です

### 最小ハードウェア仕様

| リソース | 最小 (AWS 公式) | 推奨     |
| -------- | ---------------------- | --------------- |
| CPU      | 1 vCPU                 | 4 コア以上 |
| RAM      | 1 GiB                  | 8 GB 以上    |
| ディスク | 50 GB SSD              | 100 GB NVMe SSD |
| ネットワーク  | 100 Mbps               | 10 Gbps 以上 |

> **注意**: AWS 公式の最小値は 1 vCPU / 1 GiB ですが、実際のワークロードを実行するには 2 コア / 4 GB 以上を推奨します。

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

## AWS Packer テンプレートによるノードイメージの構築

AWS は、EKS Hybrid Nodes 用のノードイメージを構築するための Packer テンプレートの例を提供しています。これらのテンプレートは、OVA (vSphere)、Qcow2、Raw の出力形式をサポートしています。

### Packer の前提条件

| ツール                  | 最小バージョン |
| --------------------- | --------------- |
| Packer                | v1.11.0+        |
| VMware vSphere Plugin | v1.4.0+         |
| QEMU Plugin           | 最新          |

### 環境変数

| 変数              | 説明                          | デフォルト |
| --------------------- | ------------------------------------ | ------- |
| `PKR_SSH_PASSWORD`    | SSH パスワード                         | -       |
| `ISO_URL`             | OS ISO イメージ URL                     | -       |
| `ISO_CHECKSUM`        | ISO チェックサム                         | -       |
| `CREDENTIAL_PROVIDER` | 認証情報プロバイダー (`ssm` または `iam`) | `ssm`   |
| `K8S_VERSION`         | Kubernetes バージョン                   | -       |
| `NODEADM_ARCH`        | アーキテクチャ (`amd64` または `arm64`)    | `amd64` |

**RHEL 固有の変数:**

| 変数      | 説明                   |
| ------------- | ----------------------------- |
| `RH_USERNAME` | Red Hat サブスクリプションのユーザー名 |
| `RH_PASSWORD` | Red Hat サブスクリプションのパスワード |

**vSphere 固有の変数:**

| 変数             | 説明            |
| -------------------- | ---------------------- |
| `VSPHERE_SERVER`     | vCenter サーバーアドレス |
| `VSPHERE_USER`       | vCenter ユーザー名       |
| `VSPHERE_PASSWORD`   | vCenter パスワード       |
| `VSPHERE_DATACENTER` | データセンター名        |
| `VSPHERE_CLUSTER`    | クラスター名           |
| `VSPHERE_DATASTORE`  | データストア名         |
| `VSPHERE_NETWORK`    | ネットワーク名           |

### 構築コマンド

```bash
# Build vSphere OVA (Ubuntu 22.04)
packer build -only=general-build.vsphere-iso.ubuntu22 template.pkr.hcl

# Build QEMU image (RHEL 9)
packer build -only=general-build.qemu.rhel9 template.pkr.hcl

# Build Amazon Linux 2023
packer build -only=general-build.qemu.al2023 template.pkr.hcl
```

> **注意**: `CREDENTIAL_PROVIDER` 環境変数を `iam` に設定すると、IAM Roles Anywhere 用のイメージが構築されます。デフォルトは `ssm` です。

## GPU サーバーの要件 (任意)

### NVIDIA ドライバー

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Required version: 550.x or higher

# Check CUDA version
nvcc --version
# Recommended version: CUDA 12.x
```

### サポート対象の GPU モデル

| GPU モデル   | VRAM     | 主な用途                        |
| ----------- | -------- | ---------------------------------- |
| NVIDIA H100 | 80 GB    | 大規模 LLM のトレーニング/推論 |
| NVIDIA H200 | 141 GB   | 非常に大規模なモデル                  |
| NVIDIA A100 | 40/80 GB | AI/ML 汎用              |
| NVIDIA L40S | 48 GB    | 推論に最適化                |

### GPU ドライバーのインストール

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

## ネットワーク要件

### 帯域幅とレイテンシー

| 項目        | 最小            | 推奨        |
| ----------- | ------------------ | ------------------ |
| 帯域幅   | 100 Mbps           | 10 Gbps 以上    |
| レイテンシー     | 200 ms RTT 以下 | 5 ms 以下       |
| パケット損失 | 0.1% 以下       | 0.01% 以下      |
| MTU         | 1500               | 9000 (Jumbo Frame) |

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

## IAM 認証情報プロバイダーの設定

EKS Hybrid Nodes では、オンプレミスノードを AWS で認証するために、2 つの認証情報プロバイダーのいずれかが必要です。

### オプション A: SSM Hybrid Activations

SSM Hybrid Activations は、PKI インフラストラクチャを必要としない、より簡単な選択肢です。

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

IAM Roles Anywhere は既存の PKI の X.509 証明書を使用するため、エアギャップ環境に最適です。

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

### CloudFormation ベースの IAM 設定

CLI の代わりに、CloudFormation を使用して IAM ロールと関連リソースを設定できます。

**SSM 用 CloudFormation テンプレート:**

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

**IAM Roles Anywhere 用 CloudFormation テンプレート:**

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

### IAM ポリシーの詳細

ハイブリッドノードロールに必要な IAM ポリシーの詳細です。

**必須の管理ポリシー:**

| ポリシー                               | 目的                                       |
| ------------------------------------ | --------------------------------------------- |
| `AmazonEC2ContainerRegistryPullOnly` | ECR からコンテナイメージをプル                |
| `AmazonSSMManagedInstanceCore`       | SSM エージェントのコア機能 (SSM 使用時) |

**任意のポリシー:**

| ポリシー                              | 目的                  |
| ----------------------------------- | ------------------------ |
| `eks-auth:AssumeRoleForPodIdentity` | EKS Pod Identity のサポート |

**SSM 登録解除の条件付きポリシー:**

マルチクラスター環境では、`EKSClusterARN` 条件タグを使用して、ノードを特定のクラスターからのみ登録解除できるようにします:

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

### IAM Roles Anywhere 信頼ポリシーの詳細

IAM Roles Anywhere を使用する場合、信頼ポリシーの設定は重要です。

**x509Subject/CN マッピング:**

証明書の CN (Common Name) はノード名と一致する必要があります。これは監査追跡およびノード識別に使用されます。

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

| コンポーネント               | 説明                             |
| ----------------------- | --------------------------------------- |
| `sts:SetSourceIdentity` | 監査追跡用のソース ID を設定 |
| `sts:RoleSessionName`   | 証明書の CN に紐付くセッション名    |
| `x509Subject/CN`        | 証明書の CN は nodeName と一致する必要があります      |

### 認証情報の有効期間比較

| 項目               | SSM              | IAM Roles Anywhere                                     |
| -------------------- | ---------------- | ------------------------------------------------------ |
| デフォルトの有効期間     | 1 時間 (固定)   | 1 時間 (設定可能)                                  |
| 最大有効期間     | 1 時間           | 12 時間                                               |
| ローテーション             | AWS により自動 | 自動、`durationSeconds` を遵守                  |
| `MaxSessionDuration` | N/A              | IAM ロール値はプロファイルの `durationSeconds` を超える必要があります |
| 設定        | 設定不可 | プロファイルの `durationSeconds` パラメータで設定          |

> **注意**: IAM Roles Anywhere を使用する場合、IAM ロールの `MaxSessionDuration` はプロファイルの `durationSeconds` 値より大きくなければなりません。そうでない場合、認証情報の取得に失敗します。

## クラスターアクセスの準備

ハイブリッドノードが EKS クラスターに参加するには、適切なアクセスエントリが必要です。

### HYBRID\_LINUX アクセスエントリ (推奨)

`HYBRID_LINUX` アクセスエントリタイプは、ハイブリッドノード向けに特別に設計されています:

```bash
aws eks create-access-entry \
  --cluster-name my-hybrid-cluster \
  --principal-arn arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --type HYBRID_LINUX
```

このコマンドは次を自動的に設定します:

* ユーザー名: <code v-pre>system:node:{{SessionName}}</code>
* Kubernetes グループ: `system:bootstrappers`, `system:nodes`

### aws-auth ConfigMap の代替方法

`API_AND_CONFIG_MAP` 認証モードを使用する場合、代替手段として `aws-auth` ConfigMap を使用できます:

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

> **注意**: `aws-auth` ConfigMap の方法はレガシーなアプローチです。新しいクラスターでは、`HYBRID_LINUX` アクセスエントリの使用を推奨します。

## VPC 設定の要件

EKS クラスター VPC は、Hybrid Nodes 接続をサポートするように適切に設定する必要があります。

### ルートテーブルの設定

VPC ルートテーブルには、オンプレミス CIDR 向けのルートを含める必要があります:

| 宛先                     | ターゲット  | 目的                    |
| ------------------------------- | ------- | -------------------------- |
| 10.0.0.0/16 (VPC CIDR)          | local   | VPC 内部トラフィック       |
| 10.80.0.0/16 (リモートノード CIDR) | TGW/VGW | オンプレミスノードへのルート |
| 10.85.0.0/16 (リモート Pod CIDR)  | TGW/VGW | オンプレミス Pod へのルート  |

### セキュリティグループの要件

`RemoteNodeNetwork` / `RemotePodNetwork` を指定すると、EKS はインバウンドルールを自動作成します。追加のアウトバウンドルールは手動で設定する必要があります:

| 方向         | プロトコル | ポート          | 送信元/送信先 | 目的               |
| ----------------- | -------- | ------------- | ------------------ | --------------------- |
| インバウンド (自動)    | TCP      | 443           | リモートノード CIDR   | Kubelet → API Server  |
| インバウンド (自動)    | TCP      | 443           | リモート Pod CIDR    | Pod → API Server      |
| インバウンド (自動)    | TCP      | 10250         | リモートノード CIDR   | API Server → Kubelet  |
| アウトバウンド (手動) | TCP      | 10250         | リモートノード CIDR   | API Server → Kubelet  |
| アウトバウンド (手動) | TCP      | Webhook ポート | リモート Pod CIDR    | API Server → Webhooks |

> **注意**: セキュリティグループあたりのインバウンドルールには 60 件の上限があります。複数の CIDR を使用する場合はルール数を確認してください。

### API Server エンドポイントアクセスモード

| モード        | Kubelet パス                  | ユースケース                                     |
| ----------- | ----------------------------- | -------------------------------------------- |
| **Public**  | Internet → EKS API エンドポイント   | 簡単なセットアップ、オンプレミスからインターネットが必要 |
| **Private** | VPN/DX → VPC ENI → API Server | エアギャップ、最大限のセキュリティ **(推奨)**  |

> **警告**: **ハイブリッドノードで「Public and Private」モードを使用しないでください。** このモードでは、ハイブリッドノードは EKS API エンドポイントをパブリック IP のみに解決するため、プライベート VPN/Direct Connect 接続が失敗します。その結果、**ノードはクラスターへの参加に失敗します**。Public または Private のいずれかを選択する必要があり、両方は選択できません。

> **推奨**: 本番のハイブリッド環境では **Private** エンドポイントアクセスを使用してください。

## Hybrid Nodes 用 EKS クラスターの作成

Hybrid Nodes をサポートする EKS クラスターを作成する場合、以下の要件が適用されます:

* **認証モード**: `API` または `API_AND_CONFIG_MAP` を使用する必要があります
* **IP アドレスファミリー**: IPv4 を使用する必要があります
* **エンドポイント接続**: Public または Private のみを使用する必要があります (「Public and Private」は**サポートされません** — ハイブリッドノードの参加失敗の原因になります)
* **リモートネットワーク**: `RemoteNodeNetwork` および `RemotePodNetwork` CIDR を指定します

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

## Hybrid Nodes でサポートされるアドオン

すべての EKS アドオンがハイブリッドノードと互換性があるわけではありません。Amazon VPC CNI は互換性が**ありません**。

### AWS アドオン

| アドオン                   | 最小互換バージョン |
| ------------------------ | -------------------------- |
| kube-proxy               | v1.25.14-eksbuild.2+       |
| CoreDNS                  | v1.9.3-eksbuild.7+         |
| ADOT (OpenTelemetry)     | v0.102.1-eksbuild.2+       |
| CloudWatch Observability | v2.2.1-eksbuild.1+         |
| EKS Pod Identity Agent   | v1.3.3-eksbuild.1+         |
| Node monitoring agent    | v1.2.0-eksbuild.1+         |
| CSI snapshot controller  | v8.1.0-eksbuild.1+         |

### コミュニティアドオン

| アドオン                    | 最小互換バージョン |
| ------------------------- | -------------------------- |
| Kubernetes Metrics Server | v0.7.2-eksbuild.1+         |
| cert-manager              | v1.17.2-eksbuild.1+        |
| Prometheus Node Exporter  | v1.9.1-eksbuild.2+         |
| kube-state-metrics        | v2.15.0-eksbuild.4+        |
| External DNS              | v0.19.0-eksbuild.1+        |

***

< [目次](./README.md) | [次へ: ネットワーク設定](02-network-configuration.md) >
