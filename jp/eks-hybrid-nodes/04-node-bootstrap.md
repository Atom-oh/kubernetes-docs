# Node Bootstrap (ノードブートストラップ)

< [前へ: Air-Gap Setup](./03-airgap-setup.md) | [目次](./README.md) | [次へ: GPU Integration](./05-gpu-integration.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+
> **最終更新**: February 23, 2026

このドキュメントでは、nodeadm を使用してオンプレミスサーバーを EKS Hybrid Nodes としてブートストラップするプロセスについて説明します。

## Bootstrap ワークフロー概要

以下の手順は、IAM 認証情報のセットアップから完全に Ready 状態の hybrid node になるまでの、Node bootstrap プロセス全体を示しています。

### Bootstrap 手順

1. **IAM 認証情報を準備する** — SSM Hybrid Activation を作成するか、IAM Roles Anywhere を設定します
2. **nodeadm をダウンロードする** — 使用するアーキテクチャ向けの CLI バイナリをダウンロードします
3. **`nodeadm install` を実行する** — Kubernetes コンポーネントと依存関係をインストールします
4. **NodeConfig YAML を作成する** — cluster details、認証情報、kubelet、containerd を設定します
5. **CA 証明書をインストールする** — private registry を使用する場合は、private registry の CA certs をシステムの trust store に追加します
6. **`nodeadm init` を実行する** — Node を初期化し、EKS cluster に登録します
7. **CNI をインストールする** — Pod networking のために Helm 経由で Cilium をデプロイします
8. **登録を確認する** — `kubectl get nodes` で Node が `Ready` と表示されることを確認します

## nodeadm CLI のダウンロードとインストール

nodeadm は、EKS Hybrid Nodes の初期化と管理に使用する CLI tool です。

### Step 1: nodeadm をダウンロードする

```bash
# Download nodeadm (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# For ARM64 architecture:
# curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/arm64/nodeadm

# Check version
nodeadm version
```

### Step 2: `nodeadm install` を実行する

`nodeadm install` コマンドは、Kubernetes コンポーネント（kubelet、kubectl など）とシステム依存関係をインストールします。これは `nodeadm init` の前に実行する必要があります。

```bash
# Install with SSM credential provider
sudo nodeadm install 1.31 --credential-provider ssm

# Install with IAM Roles Anywhere credential provider
sudo nodeadm install 1.31 --credential-provider iam-ra

# Custom timeout for slow networks
sudo nodeadm install 1.31 --credential-provider ssm --timeout 20m0s
```

> **注記**: `1.31` を対象の Kubernetes version に置き換えてください。この version は EKS cluster version と一致している必要があります。

### インストールされるファイルパス

| コンポーネント | Ubuntu/AL2023 パス | RHEL パス |
|-----------|-------------------|-----------|
| kubelet | /usr/bin/kubelet | /usr/bin/kubelet |
| kubectl | /usr/bin/kubectl | /usr/bin/kubectl |
| SSM Agent | /snap/amazon-ssm-agent (Ubuntu) / systemd (AL2023) | /usr/bin/amazon-ssm-agent |
| containerd | /usr/bin/containerd | /usr/bin/containerd |
| nodeadm | /usr/local/bin/nodeadm | /usr/local/bin/nodeadm |

## NodeConfig YAML の作成

```yaml
# nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16  # Service CIDR

  # Credential method selection (SSM or IAM Roles Anywhere)
  hybrid:
    # Method 1: SSM Hybrid Activations
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

    # Method 2: IAM Roles Anywhere (uncomment to use)
    # iamRolesAnywhere:
    #   nodeName: hybrid-node-001  # Must match certificate CN
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/iam/pki/server.pem
    #   privateKeyPath: /etc/iam/pki/server.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      # Private registry TLS configuration (uncomment and adjust for your registry)
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".tls]
      #   ca_file = "/etc/ssl/certs/registry-ca.crt"
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".auth]
      #   username = "pull-robot"
      #   password = "<token>"
```

## SSM Hybrid Activation の作成

```bash
# Create SSM Hybrid Activation
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --region ap-northeast-2 \
  --tags "Key=Environment,Value=Production" "Key=NodeType,Value=Hybrid"

# Enter the output ActivationCode and ActivationId in nodeconfig.yaml
```

## IAM Roles Anywhere のセットアップ (代替)

SSM の代わりに IAM Roles Anywhere を使用する場合は、trust anchor、profile、証明書を設定します。

```bash
# Create Trust Anchor
TRUST_ANCHOR_ARN=$(aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled \
  --query 'trustAnchor.trustAnchorArn' --output text)

# Create Profile
PROFILE_ARN=$(aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled \
  --query 'profile.profileArn' --output text)

echo "Trust Anchor ARN: $TRUST_ANCHOR_ARN"
echo "Profile ARN: $PROFILE_ARN"
# Enter these values in nodeconfig.yaml under spec.hybrid.iamRolesAnywhere
```

IAM Roles Anywhere 用の NodeConfig YAML:

```yaml
spec:
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001  # Must match certificate CN
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

> **注記**: IAM Roles Anywhere を使用する場合は、IAM RA profile で `acceptRoleSessionName` を有効にし、頻繁な credential refresh を避けるために IAM role の `MaxSessionDuration` を少なくとも 1 時間（推奨: 12 時間）に設定してください。

## システムへの CA Certificate のインストール (Private Registry)

自己署名証明書または内部 CA 証明書を使用する private container registry を使う場合は、各 Node に CA cert をインストールします。

```bash
# Install CA certificate on system (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/registry-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/registry-ca.crt
sudo update-ca-trust extract

# Configure directory for containerd to find certificate
sudo mkdir -p /etc/containerd/certs.d/<REGISTRY_HOST>
cat <<EOF | sudo tee /etc/containerd/certs.d/<REGISTRY_HOST>/hosts.toml
server = "https://<REGISTRY_HOST>"

[host."https://<REGISTRY_HOST>"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
EOF
```

## Node の初期化

### Configuration の検証

Node を初期化する前に、configuration file を検証することを推奨します。

```bash
# Validate configuration (recommended before node initialization)
nodeadm config check --config-source file://nodeconfig.yaml
```

### 初期化の実行

```bash
# Initialize node using nodeadm
sudo nodeadm init -c file://nodeconfig.yaml

# Check initialization logs
sudo journalctl -u kubelet -f

# Check node status (from EKS cluster)
kubectl get nodes -o wide
```

## Node 登録の確認

```bash
# Check node list
kubectl get nodes --show-labels

# Expected output:
# NAME                STATUS   ROLES    AGE   VERSION   LABELS
# ip-10-0-1-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2a
# ip-10-0-2-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2b
# hybrid-node-001     Ready    <none>   5m    v1.31.0   eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node hybrid-node-001

# Filter Hybrid Nodes
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid
```

---

## systemd による自動 Bootstrap

大規模デプロイでは、Node の起動時に `nodeadm install` と `nodeadm init` を自動実行する systemd service を設定できます。marker file により、install は初回起動時のみ実行され、以降の起動ではスキップされます。

### 前提条件

automatic bootstrap の前に、以下のファイルを Node 上に事前配置しておく必要があります。

- `/etc/eks/nodeconfig.yaml` — NodeConfig configuration file
- `/etc/eks/bootstrap.env` — Bootstrap environment variables
- `/usr/local/bin/nodeadm` — nodeadm binary

> **注記**: これらのファイルは、VM image build（Packer など）、cloud-init、または configuration management tools（Ansible など）を使用して事前配置できます。

### 環境設定ファイル

```bash
# /etc/eks/bootstrap.env
K8S_VERSION="1.31"
CREDENTIAL_PROVIDER="ssm"          # ssm or iam-ra
NODECONFIG_PATH="/etc/eks/nodeconfig.yaml"
```

### Bootstrap Script

```bash
#!/bin/bash
# /usr/local/bin/eks-hybrid-bootstrap.sh
set -euo pipefail

LOG_TAG="eks-hybrid-bootstrap"
MARKER_DIR="/var/lib/eks"
INSTALL_MARKER="${MARKER_DIR}/.nodeadm-installed"
INIT_MARKER="${MARKER_DIR}/.nodeadm-initialized"

# Load environment variables
source /etc/eks/bootstrap.env

log() { logger -t "$LOG_TAG" "$1"; echo "[$(date '+%H:%M:%S')] $1"; }

mkdir -p "$MARKER_DIR"

# --- install phase (first boot only) ---
if [ -f "$INSTALL_MARKER" ]; then
  log "nodeadm install already completed — skipping"
else
  log "Starting nodeadm install ${K8S_VERSION} (credential-provider: ${CREDENTIAL_PROVIDER})"
  nodeadm install "${K8S_VERSION}" --credential-provider "${CREDENTIAL_PROVIDER}"
  touch "$INSTALL_MARKER"
  log "nodeadm install completed"
fi

# --- init phase (first boot only) ---
if [ -f "$INIT_MARKER" ]; then
  log "nodeadm init already completed — skipping"
else
  log "Starting nodeadm init"
  nodeadm init -c "file://${NODECONFIG_PATH}"
  touch "$INIT_MARKER"
  log "nodeadm init completed — node registered with EKS cluster"
fi
```

```bash
sudo chmod +x /usr/local/bin/eks-hybrid-bootstrap.sh
```

### systemd Service Unit

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=EKS Hybrid Node Bootstrap (install + init)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/eks/.nodeadm-initialized

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **ConditionPathExists**: `!` prefix は、この service がファイルが **存在しない** 場合にのみ実行されることを意味します。init が完了して marker file が作成されると、以降の起動時には service は自動的にスキップされます。

### Service の有効化

```bash
sudo systemctl daemon-reload
sudo systemctl enable eks-hybrid-bootstrap.service
```

### 動作確認

```bash
# Check service status
sudo systemctl status eks-hybrid-bootstrap.service

# View bootstrap logs
sudo journalctl -u eks-hybrid-bootstrap.service

# Check marker files
ls -la /var/lib/eks/.nodeadm-*
```

### 再インストール

最初からやり直すには、marker file を削除して再起動します。

```bash
# Clean up existing state
sudo nodeadm uninstall
sudo rm -f /var/lib/eks/.nodeadm-installed /var/lib/eks/.nodeadm-initialized

# Reboot triggers automatic install + init
sudo reboot
```

### よくある質問

**Q: systemd unit file の各設定は何を意味しますか?**

| 設定 | 意味 |
|---------|---------|
| `Type=oneshot` | 起動時に 1 回だけ実行して終了します |
| `After=network-online.target` | ネットワークが完全に Ready になった後にのみ実行します |
| `ConditionPathExists=!/var/lib/eks/.nodeadm-initialized` | `!` prefix — marker file が **存在しない** 場合にのみ実行します |
| `RemainAfterExit=true` | プロセス終了後も service は active state のままになります（status check が可能） |
| `WantedBy=multi-user.target` | 通常起動時に自動的に開始します |

**Q: Node が再起動されるたびに新しい SSM activation code が必要ですか?**

いいえ。SSM Hybrid Activation の `activationCode`/`activationId` は、`nodeadm init` 中に SSM agent を AWS に登録するために 1 回だけ使用されます。登録後、SSM agent は自身の認証情報を自動的に更新するため、**通常の再起動では activation code は不要です**。

ただし、`nodeadm uninstall` を実行した場合は、SSM artifacts が削除され、再登録が必要になります。`registration-limit` に達していない場合は、同じ activation code を再利用できます。

**Q: `nodeadm init` は Node を cluster に参加させますか?**

はい。`nodeadm init` は以下の手順を順番に実行します。
1. kubelet configuration files（`/etc/kubernetes/`）を生成します
2. SSM または IAM Roles Anywhere credentials を登録します
3. kubelet systemd service を開始します
4. kubelet が EKS API server に Node を登録（join）します

言い換えると、`nodeadm init` が実際の **cluster join command** です。

**Q: SSM activation registration は `install` と `init` のどちらで行われますか?**

| Phase | SSM-Related Action |
|-------|-------------------|
| `nodeadm install --credential-provider ssm` | SSM Agent **binary only** をインストールします |
| `nodeadm init` | nodeconfig.yaml の `activationCode`/`activationId` を使用して SSM Agent を AWS に **登録** します |

SSM activation（registration）は **init phase** で行われます。

**Q: SSM activation を維持したまま Node を削除して再登録するにはどうすればよいですか?**

`kubectl delete node <NODE_NAME>` は SSM registration には影響しません（SSM は OS level で動作し、Node registration は Kubernetes level です）。kubelet がまだ実行中であれば、Node は自動的に再登録されます。

```bash
# Remove node from cluster
kubectl delete node hybrid-node-001

# If kubelet is running, it auto-registers
# If stopped, restart manually
sudo systemctl restart kubelet
```

**Q: `drain → delete → shutdown` の後、Node は systemd 経由で再起動時に自動登録されますか?**

Node は再登録されますが、それは systemd bootstrap service ではなく、**kubelet service 自体** によって処理されます。

1. `nodeadm init` は kubelet を systemd service としてインストールします
2. 再起動時に kubelet が自動的に開始し、API server に再登録します
3. marker file が存在するため bootstrap service はスキップされます（これは期待される動作です）

```bash
# No need to delete marker files in this workflow
kubectl drain hybrid-node-001 --ignore-daemonsets --delete-emptydir-data
kubectl delete node hybrid-node-001
# Shutdown and reboot → kubelet auto-registers
```

> **注記**: `nodeadm uninstall` が実行された場合にのみ、marker file を削除し、再インストールのために bootstrap service に依存してください。

---

## Cilium CNI のインストール

Cilium は、EKS Hybrid Nodes 向けに AWS がサポートする CNI です。hybrid nodes は、CNI がインストールされるまで `Not Ready` status で表示されます。Amazon VPC CNI は hybrid nodes と **互換性がありません**。

> **サポート対象バージョン**: Amazon EKS でサポートされるすべての Kubernetes versions 向け Cilium v1.17.x および v1.18.x
> **Helm repository**: `oci://public.ecr.aws/eks/cilium/cilium`

> **前提条件**:
> - **Kernel version**: Cilium には Linux kernel **5.10 以上** が必要です。Ubuntu 20.04 および RHEL 8 の default kernels は 5.10 未満です — Cilium v1.18.x をインストールする前に kernel をアップグレードする必要があります。
> - **Hybrid nodes only**: Cilium affinity は hybrid nodes（`eks.amazonaws.com/compute-type: hybrid`）でのみ実行されるように設定する必要があります。VPC CNI を使用する cloud nodes では Cilium を実行しないでください。
> - **IPAM settings are immutable**: `clusterPoolIPv4PodCIDRList` および `clusterPoolIPv4MaskSize` の値は、初回デプロイ後に **変更できません**。インストール前に Pod CIDR allocation を慎重に計画してください。

### Cilium Values YAML の作成

```yaml
# cilium-values.yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: In
          values:
          - hybrid

ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList:
    - <POD_CIDR>  # Same as your EKS cluster's remote pod networks

loadBalancer:
  serviceTopology: true

operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: In
            values:
            - hybrid
  unmanagedPodWatcher:
    restart: false

envoy:
  enabled: false

kubeProxyReplacement: "false"
```

### Cilium のインストール

```bash
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version 1.18.3-0 \
  --namespace kube-system \
  --values cilium-values.yaml
```

### インストールの確認

```bash
# Check Cilium pods are running
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# Nodes should now show Ready
kubectl get nodes -o wide
```

### Cilium のアップグレード

Cilium を新しい version にアップグレードする手順:

```bash
# 1. Preflight check (validate compatibility before upgrade)
helm install cilium-preflight oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --set preflight.enabled=true \
  --set agent=false --set operator.enabled=false

# 2. Upgrade while preserving existing values
helm upgrade cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version NEW_VERSION \
  --namespace kube-system \
  --reuse-values

# 3. Verify status
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# 4. Rollback (if issues occur)
helm rollback cilium --namespace kube-system
```

### Cilium のアンインストール

Cilium を完全に削除する手順:

```bash
# 1. Helm uninstall
helm uninstall cilium --namespace kube-system

# 2. Delete CRDs
kubectl get crds -o name | grep cilium | xargs kubectl delete

# 3. On-disk cleanup (run on each node)
sudo rm -rf /var/run/cilium /var/lib/cilium /etc/cni/net.d/05-cilium.conflist
sudo rm -f /opt/cni/bin/cilium-cni
```

### Calico 非推奨のお知らせ

> **注記**: Calico は EKS Hybrid Nodes 向けに公式サポートされなくなり、`eks-hybrid-examples` repository に移動されました。新規デプロイでは Cilium を推奨します。既存の Calico deployments は引き続き動作しますが、AWS からの公式サポートは限定的です。

---

## Bottlerocket Configuration

Bottlerocket は VMware vSphere environments（v1.37.0+）でのみサポートされ、x86_64 architecture のみ対応しています。Bottlerocket は **nodeadm を使用せず**、TOML-based configuration と user data によってブートストラップされます。

### SSM Hybrid Activation Configuration (settings.toml)

```toml
[settings.kubernetes]
cluster-name = "CLUSTER_NAME"
api-server = "API_SERVER_ENDPOINT"
cluster-certificate = "BASE64_CA_CERT"
service-cidr = "SERVICE_CIDR"

[settings.hybrid]
enable-credentials-file = true  # Required for Pod Identity

[settings.hybrid.ssm]
activation-id = "ACTIVATION_ID"
activation-code = "ACTIVATION_CODE"
```

### IAM Roles Anywhere Configuration (settings.toml)

```toml
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "TRUST_ANCHOR_ARN"
profile-arn = "PROFILE_ARN"
role-arn = "ROLE_ARN"
node-name = "NODE_NAME"  # Must match certificate CN
certificate-path = "/PATH/TO/CERT"
private-key-path = "/PATH/TO/KEY"
```

### govc による VMware デプロイ

```bash
# Clone from VM template
govc vm.clone -vm "/PATH/TO/TEMPLATE" -ds="DATASTORE" \
  -on=false -template=false -folder=/FOLDER "VM_NAME"

# Configure user data
govc vm.change -dc="DC" -vm "VM_NAME" \
  -e guestinfo.userdata="${USER_DATA}" \
  -e guestinfo.userdata.encoding=gzip+base64

# Start VM
govc vm.power -on "VM_NAME"
```

> **注記**: `USER_DATA` は、settings.toml content を gzip 圧縮し、base64 エンコードしたものです。

---

## Webhook と Add-on 配置のガイダンス

一部の EKS add-ons は、API server が pods に直接到達できる必要がある webhooks を使用します。オンプレミスの Pod CIDR が **routable でない** 場合、これらの add-ons は cloud nodes でのみ実行する必要があります。

### Cloud-Only Add-ons (Unroutable Pod CIDR)

webhook-based add-ons を cloud nodes に制限するには、`nodeAffinity` を使用します。

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

この扱いが必要な add-ons: AWS Load Balancer Controller、CloudWatch Observability Agent、ADOT、cert-manager。

### CoreDNS Mixed Mode

DNS resiliency のため、CoreDNS は cloud nodes と hybrid nodes の **両方** で実行する必要があります。少なくとも 4 replicas（各側 2 つ）で `topologySpreadConstraints` を使用します。[Network Configuration - CoreDNS Dual-Location Deployment](./02-network-configuration.md#coredns-dual-location-deployment-on-premises--cloud) を参照してください。

### EKS Pod Identity Agent

EKS Pod Identity Agent は、private/air-gap environments で `eks-auth` VPC endpoint を必要とします。EKS managed add-on としてインストールします。

```bash
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.3.3-eksbuild.1
```

---

## Node のアップグレード

Hybrid nodes は upstream Kubernetes と同じ Kubernetes version skew policy に従います。つまり、control plane より新しい version にはできず、最大 3 minor versions 古い version まで許容されます。

### Cutover Migration (推奨)

spare capacity が利用できる場合は、target version の新しい Nodes を作成し、workloads を安全に移行します。

```bash
# 1. Install nodeadm on new hosts with target version
nodeadm install K8S_VERSION --credential-provider CREDS_PROVIDER

# 2. Cordon old nodes
kubectl cordon NODE_NAME

# 3. Scale CoreDNS for resiliency
kubectl scale deployments/coredns --replicas=2 -n kube-system

# 4. Drain old nodes
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 5. Uninstall old nodes
sudo nodeadm uninstall

# 6. Delete old node resource
kubectl delete node NODE_NAME
```

### In-Place Upgrade

spare capacity が利用できない場合は、Nodes を in-place でアップグレードします（downtime が発生します）。

```bash
# 1. Cordon the node
kubectl cordon NODE_NAME

# 2. Drain workloads
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 3. Run nodeadm upgrade
sudo nodeadm upgrade K8S_VERSION -c file://nodeConfig.yaml

# 4. Uncordon after upgrade completes
kubectl uncordon NODE_NAME

# 5. Monitor
kubectl get nodes -o wide -w
```

---

## Troubleshooting

### nodeadm debug

`nodeadm debug` コマンドは、network access、credentials、cluster connectivity を検証します。

```bash
sudo nodeadm debug -c file://nodeConfig.yaml
```

これは以下を検証します。
- AWS APIs への network access
- Hybrid Nodes IAM role の AWS credentials retrieval
- EKS Kubernetes API endpoint への network access
- EKS cluster での Node authentication

### よくある問題と修正

#### インストールの問題

| 問題 | 症状 | 修正 |
|-------|---------|-----|
| root として実行する必要があります | `"msg":"Command failed","error":"must run as root"` | `sudo` で `nodeadm` を実行します |
| 依存関係に接続できません | `max retries achieved for http request` | dependency repositories への network access を確認します |
| package manager failure | `failed to run update using package manager` | 先に `apt update` または `dnf update` を実行します |
| Timeout | `context deadline exceeded` | `--timeout 20m0s` flag を使用します |

#### 接続の問題

| 問題 | 症状 | 修正 |
|-------|---------|-----|
| Node IP が CIDR 内にありません | `node IP is not in any of the remote network CIDR blocks` | `RemoteNodeNetworks` に Node IP range が含まれていることを確認します |
| API server unreachable | `Unable to connect to the server` / `dial tcp: i/o timeout` | VPN/DX tunnel、firewall port 443、TGW/VGW への VPC routes を確認します |
| Unauthorized | `Failed to ensure lease exists: Unauthorized` | IAM role、`HYBRID_LINUX` type の EKS access entry を確認します |
| Node stays NotReady | Node registered but NotReady | CNI（Cilium）をインストールし、VXLAN port 8472 を確認します |
| DNS resolution failure | EKS API endpoint の `no such host` | Route 53 Resolver Inbound Endpoint を設定し、on-prem DNS を更新します |
| Image pull failure | system pods で `ErrImagePull` | ECR VPC endpoints、containerd registry config、CA certs を確認します |
| Certificate error | `x509: certificate signed by unknown authority` | system trust store に CA cert をインストールし、`update-ca-certificates` を実行します |
| Hybrid profile exists | `hybrid profile already exists` | `nodeadm uninstall`、`nodeadm install`、`nodeadm init` の順に実行します |

#### SSM Credential の問題

| 問題 | 症状 | 修正 |
|-------|---------|-----|
| Invalid activation | `InvalidActivation` | nodeConfig.yaml の region、activationCode、activationId を確認します |
| Expired activation | `ActivationExpired` | 新しい SSM hybrid activation を作成し、nodeConfig.yaml を更新します |
| Expired token | `ExpiredTokenException` | SSM agent を再起動します: `systemctl restart amazon-ssm-agent` |

#### IAM Roles Anywhere の問題

| 問題 | 症状 | 修正 |
|-------|---------|-----|
| Certificate not found | `open /etc/iam/pki/server.pem: no such file or directory` | `/etc/iam/pki/` directory を作成し、certificate と key をコピーします |
| Not authorized | `not authorized to perform: sts:AssumeRole` | trust policy、trust anchor ARN、IAM RA profile を確認します |

### 診断コマンド

```bash
# Check kubelet status and logs
sudo systemctl status kubelet
sudo journalctl -u kubelet -f

# Check containerd
sudo systemctl status containerd

# Validate credentials
sudo aws sts get-caller-identity

# Check SSM agent (AL2023/RHEL)
sudo systemctl status amazon-ssm-agent

# Check SSM agent (Ubuntu)
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent

# Run nodeadm diagnostics
sudo nodeadm debug -c file://nodeConfig.yaml
```

### Node のリセット

bootstrap が失敗し、最初からやり直す必要がある場合:

```bash
# Basic uninstall
sudo nodeadm uninstall

# Force uninstall (cleans all state, skips confirmation prompt)
sudo nodeadm uninstall --force

# Re-run initialization
sudo nodeadm init -c file://nodeconfig.yaml
```

**nodeadm uninstall によって削除される paths:**
- `/etc/kubernetes` - Kubernetes configuration files
- `/etc/eks` - EKS-related configuration
- SSM/IAM Roles Anywhere artifacts

**v1.0.9+ の変更:**
- `/var/lib/kubelet` は **default で保持されます**（data protection improvement）
- `--force` option は、通常保持されるものを含め、すべての artifacts を削除します

---

< [前へ: Air-Gap Setup](./03-airgap-setup.md) | [目次](./README.md) | [次へ: GPU Integration](./05-gpu-integration.md) >
