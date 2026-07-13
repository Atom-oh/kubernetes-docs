# Node 引导启动

< [上一页：Air-Gap 设置](./03-airgap-setup.md) | [目录](./README.md) | [下一页：GPU 集成](./05-gpu-integration.md) >

> **支持的版本**: EKS 1.31+, nodeadm 0.1+
> **最后更新**: February 23, 2026

本文档介绍使用 nodeadm 将本地服务器引导启动为 EKS Hybrid Nodes 的过程。

## Bootstrap 工作流概览

以下步骤概述了从 IAM 凭证设置到完全就绪的 hybrid node 的完整 node bootstrap 流程。

### Bootstrap 步骤

1. **准备 IAM 凭证** — 创建 SSM Hybrid Activation 或配置 IAM Roles Anywhere
2. **下载 nodeadm** — 下载适用于你的架构的 CLI 二进制文件
3. **运行 `nodeadm install`** — 安装 Kubernetes 组件和依赖项
4. **编写 NodeConfig YAML** — 配置 cluster 详细信息、凭证、kubelet 和 containerd
5. **安装 CA 证书** — 将私有 registry CA 证书添加到系统信任存储（如果使用私有 registry）
6. **运行 `nodeadm init`** — 初始化 node 并向 EKS cluster 注册
7. **安装 CNI** — 通过 Helm 部署 Cilium 以实现 pod 网络
8. **验证注册** — 确认 node 在 `kubectl get nodes` 中显示为 `Ready`

## nodeadm CLI 下载和安装

nodeadm 是用于初始化和管理 EKS Hybrid Nodes 的 CLI 工具。

### 步骤 1：下载 nodeadm

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

### 步骤 2：运行 `nodeadm install`

`nodeadm install` 命令会安装 Kubernetes 组件（kubelet、kubectl 等）和系统依赖项。必须先运行此命令，然后再运行 `nodeadm init`。

```bash
# Install with SSM credential provider
sudo nodeadm install 1.31 --credential-provider ssm

# Install with IAM Roles Anywhere credential provider
sudo nodeadm install 1.31 --credential-provider iam-ra

# Custom timeout for slow networks
sudo nodeadm install 1.31 --credential-provider ssm --timeout 20m0s
```

> **注意**: 将 `1.31` 替换为你的目标 Kubernetes 版本。该版本必须与你的 EKS cluster 版本匹配。

### 安装文件路径

| 组件 | Ubuntu/AL2023 路径 | RHEL 路径 |
|-----------|-------------------|-----------|
| kubelet | /usr/bin/kubelet | /usr/bin/kubelet |
| kubectl | /usr/bin/kubectl | /usr/bin/kubectl |
| SSM Agent | /snap/amazon-ssm-agent (Ubuntu) / systemd (AL2023) | /usr/bin/amazon-ssm-agent |
| containerd | /usr/bin/containerd | /usr/bin/containerd |
| nodeadm | /usr/local/bin/nodeadm | /usr/local/bin/nodeadm |

## 编写 NodeConfig YAML

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

## 创建 SSM Hybrid Activation

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

## IAM Roles Anywhere 设置（替代方案）

如果使用 IAM Roles Anywhere 而不是 SSM，请配置 trust anchor、profile 和证书：

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

用于 IAM Roles Anywhere 的 NodeConfig YAML：

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

> **注意**: 使用 IAM Roles Anywhere 时，请在 IAM RA profile 上启用 `acceptRoleSessionName`，并将 IAM role 的 `MaxSessionDuration` 设置为至少 1 小时（建议：12 小时），以避免频繁刷新凭证。

## 在系统上安装 CA 证书（私有 Registry）

如果你使用带有自签名或内部 CA 证书的私有 container registry，请在每个 node 上安装 CA 证书：

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

## Node 初始化

### 配置验证

建议在初始化 node 之前验证配置文件：

```bash
# Validate configuration (recommended before node initialization)
nodeadm config check --config-source file://nodeconfig.yaml
```

### 运行初始化

```bash
# Initialize node using nodeadm
sudo nodeadm init -c file://nodeconfig.yaml

# Check initialization logs
sudo journalctl -u kubelet -f

# Check node status (from EKS cluster)
kubectl get nodes -o wide
```

## 验证 Node 注册

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

## 使用 systemd 自动化 Bootstrap

对于大规模部署，你可以配置 systemd service，在 node 启动时自动运行 `nodeadm install` 和 `nodeadm init`。Marker 文件可确保 install 仅在首次启动时运行，并在后续启动时跳过。

### 先决条件

以下文件必须在自动 bootstrap 之前预先放置到 node 上：

- `/etc/eks/nodeconfig.yaml` — NodeConfig 配置文件
- `/etc/eks/bootstrap.env` — Bootstrap 环境变量
- `/usr/local/bin/nodeadm` — nodeadm 二进制文件

> **注意**: 这些文件可以通过 VM image 构建（Packer 等）、cloud-init 或配置管理工具（Ansible 等）预先放置。

### 环境配置文件

```bash
# /etc/eks/bootstrap.env
K8S_VERSION="1.31"
CREDENTIAL_PROVIDER="ssm"          # ssm or iam-ra
NODECONFIG_PATH="/etc/eks/nodeconfig.yaml"
```

### Bootstrap 脚本

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

> **ConditionPathExists**: `!` 前缀表示该 service 仅在文件**不存在**时运行。init 完成并创建 marker 文件后，该 service 会在后续启动时自动跳过。

### 启用 Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable eks-hybrid-bootstrap.service
```

### 验证运行情况

```bash
# Check service status
sudo systemctl status eks-hybrid-bootstrap.service

# View bootstrap logs
sudo journalctl -u eks-hybrid-bootstrap.service

# Check marker files
ls -la /var/lib/eks/.nodeadm-*
```

### 重新安装

要从头开始，请移除 marker 文件并重启：

```bash
# Clean up existing state
sudo nodeadm uninstall
sudo rm -f /var/lib/eks/.nodeadm-installed /var/lib/eks/.nodeadm-initialized

# Reboot triggers automatic install + init
sudo reboot
```

### 常见问题

**问：systemd unit 文件中的每个设置是什么意思？**

| 设置 | 含义 |
|---------|---------|
| `Type=oneshot` | 在启动时运行一次然后退出 |
| `After=network-online.target` | 仅在网络完全就绪后运行 |
| `ConditionPathExists=!/var/lib/eks/.nodeadm-initialized` | `!` 前缀 — 仅在 marker 文件**不存在**时运行 |
| `RemainAfterExit=true` | 进程退出后 service 保持 active 状态（便于状态检查） |
| `WantedBy=multi-user.target` | 在正常启动期间自动启动 |

**问：每次 node 重启时都需要新的 SSM activation code 吗？**

不需要。SSM Hybrid Activation `activationCode`/`activationId` 仅在 `nodeadm init` 期间使用一次，用于将 SSM agent 注册到 AWS。注册后，SSM agent 会自动续订自己的凭证，因此**正常重启时不需要 activation code**。

但是，如果你运行 `nodeadm uninstall`，SSM artifacts 会被删除，并且需要重新注册。如果 `registration-limit` 尚未达到，你可以重复使用同一个 activation code。

**问：`nodeadm init` 会将 node 加入 cluster 吗？**

会。`nodeadm init` 会按顺序执行以下步骤：
1. 生成 kubelet 配置文件（`/etc/kubernetes/`）
2. 注册 SSM 或 IAM Roles Anywhere 凭证
3. 启动 kubelet systemd service
4. kubelet 向 EKS API server 注册（加入）node

换句话说，`nodeadm init` 是实际的 **cluster join command**。

**问：SSM activation 注册是在 `install` 期间还是 `init` 期间发生？**

| 阶段 | SSM 相关操作 |
|-------|-------------------|
| `nodeadm install --credential-provider ssm` | 仅安装 SSM Agent **二进制文件** |
| `nodeadm init` | 使用 nodeconfig.yaml 中的 `activationCode`/`activationId` 将 SSM Agent **注册**到 AWS |

SSM activation（注册）发生在 **init 阶段**。

**问：如何在保留 SSM activation 的同时移除并重新注册 node？**

`kubectl delete node <NODE_NAME>` 不会影响 SSM 注册（SSM 在 OS 级别运行；node 注册在 Kubernetes 级别）。如果 kubelet 仍在运行，node 会自动重新注册：

```bash
# Remove node from cluster
kubectl delete node hybrid-node-001

# If kubelet is running, it auto-registers
# If stopped, restart manually
sudo systemctl restart kubelet
```

**问：在 `drain → delete → shutdown` 之后，node 会通过 systemd 在重启时自动注册吗？**

node 会重新注册，但这是由 **kubelet service 本身**处理的，而不是由 systemd bootstrap service 处理：

1. `nodeadm init` 将 kubelet 安装为 systemd service
2. 重启时，kubelet 会自动启动并向 API server 重新注册
3. bootstrap service 会被跳过，因为 marker 文件存在（这是预期行为）

```bash
# No need to delete marker files in this workflow
kubectl drain hybrid-node-001 --ignore-daemonsets --delete-emptydir-data
kubectl delete node hybrid-node-001
# Shutdown and reboot → kubelet auto-registers
```

> **注意**: 仅当已经运行 `nodeadm uninstall` 时，才应删除 marker 文件并依赖 bootstrap service 重新安装。

---

## Cilium CNI 安装

Cilium 是 AWS 支持用于 EKS Hybrid Nodes 的 CNI。Hybrid nodes 在安装 CNI 之前会显示为 `Not Ready` 状态。Amazon VPC CNI 与 hybrid nodes **不兼容**。

> **支持的版本**: Cilium v1.17.x 和 v1.18.x，适用于 Amazon EKS 支持的所有 Kubernetes 版本
> **Helm repository**: `oci://public.ecr.aws/eks/cilium/cilium`

> **先决条件**:
> - **Kernel version**: Cilium 需要 Linux kernel **5.10 或更高版本**。Ubuntu 20.04 和 RHEL 8 的默认 kernel 低于 5.10 — 在安装 Cilium v1.18.x 之前必须升级 kernel。
> - **仅 hybrid nodes**: Cilium affinity 必须设置为仅在 hybrid nodes 上运行（`eks.amazonaws.com/compute-type: hybrid`）。不要在使用 VPC CNI 的 cloud nodes 上运行 Cilium。
> - **IPAM settings 不可变**: `clusterPoolIPv4PodCIDRList` 和 `clusterPoolIPv4MaskSize` 值在初始部署后**不能更改**。请在安装前仔细规划 pod CIDR 分配。

### 创建 Cilium Values YAML

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

### 安装 Cilium

```bash
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version 1.18.3-0 \
  --namespace kube-system \
  --values cilium-values.yaml
```

### 验证安装

```bash
# Check Cilium pods are running
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# Nodes should now show Ready
kubectl get nodes -o wide
```

### Cilium 升级

将 Cilium 升级到新版本的过程：

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

### Cilium 卸载

完全移除 Cilium 的过程：

```bash
# 1. Helm uninstall
helm uninstall cilium --namespace kube-system

# 2. Delete CRDs
kubectl get crds -o name | grep cilium | xargs kubectl delete

# 3. On-disk cleanup (run on each node)
sudo rm -rf /var/run/cilium /var/lib/cilium /etc/cni/net.d/05-cilium.conflist
sudo rm -f /opt/cni/bin/cilium-cni
```

### Calico 弃用通知

> **注意**: Calico 不再作为 EKS Hybrid Nodes 的官方支持方案，并已移至 `eks-hybrid-examples` repository。对于新部署，建议使用 Cilium。现有 Calico 部署将继续工作，但 AWS 的官方支持有限。

---

## Bottlerocket 配置

Bottlerocket 仅在 VMware vSphere 环境（v1.37.0+）中受支持，并且仅支持 x86_64 架构。Bottlerocket **不使用 nodeadm**，而是通过基于 TOML 的配置和 user data 进行 bootstrap。

### SSM Hybrid Activation 配置（settings.toml）

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

### IAM Roles Anywhere 配置（settings.toml）

```toml
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "TRUST_ANCHOR_ARN"
profile-arn = "PROFILE_ARN"
role-arn = "ROLE_ARN"
node-name = "NODE_NAME"  # Must match certificate CN
certificate-path = "/PATH/TO/CERT"
private-key-path = "/PATH/TO/KEY"
```

### 使用 govc 部署 VMware

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

> **注意**: `USER_DATA` 是经过 gzip 压缩并 base64 编码的 settings.toml 内容。

---

## Webhook 和 Add-on 放置指南

某些 EKS add-ons 使用 webhooks，需要 API server 能够直接访问 pods。如果你的本地 pod CIDR **不可路由**，这些 add-ons 必须仅在 cloud nodes 上运行。

### 仅 Cloud 的 Add-ons（不可路由的 Pod CIDR）

使用 `nodeAffinity` 将基于 webhook 的 add-ons 限制到 cloud nodes：

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

需要这样处理的 add-ons：AWS Load Balancer Controller、CloudWatch Observability Agent、ADOT、cert-manager。

### CoreDNS 混合模式

CoreDNS 应同时运行在 **cloud** 和 hybrid nodes 上，以提高 DNS 韧性。使用 `topologySpreadConstraints` 并至少配置 4 个 replicas（每侧 2 个）。请参阅 [网络配置 - CoreDNS 双位置部署](./02-network-configuration.md#coredns-dual-location-deployment-on-premises--cloud)。

### EKS Pod Identity Agent

在私有/air-gap 环境中，EKS Pod Identity Agent 需要 `eks-auth` VPC endpoint。作为 EKS managed add-on 安装：

```bash
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.3.3-eksbuild.1
```

---

## Node 升级

Hybrid nodes 遵循与上游 Kubernetes 相同的 Kubernetes 版本偏差策略 — 它们不能比 control plane 更新，并且最多可以比 control plane 旧三个 minor versions。

### 切换迁移（推荐）

当有备用容量时，在目标版本上创建新的 nodes，并平滑迁移 workloads：

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

### 原地升级

当没有备用容量时，原地升级 nodes（会导致停机）：

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

## 故障排除

### nodeadm debug

`nodeadm debug` 命令会验证网络访问、凭证和 cluster 连接：

```bash
sudo nodeadm debug -c file://nodeConfig.yaml
```

这会验证：
- 对 AWS APIs 的网络访问
- 用于 Hybrid Nodes IAM role 的 AWS 凭证获取
- 对 EKS Kubernetes API endpoint 的网络访问
- Node 向 EKS cluster 的身份验证

### 常见问题和修复

#### 安装问题

| 问题 | 症状 | 修复 |
|-------|---------|-----|
| 必须以 root 身份运行 | `"msg":"Command failed","error":"must run as root"` | 使用 `sudo` 运行 `nodeadm` |
| 无法连接到依赖项 | `max retries achieved for http request` | 验证对依赖项 repositories 的网络访问 |
| Package manager 失败 | `failed to run update using package manager` | 先运行 `apt update` 或 `dnf update` |
| 超时 | `context deadline exceeded` | 使用 `--timeout 20m0s` 标志 |

#### 连接问题

| 问题 | 症状 | 修复 |
|-------|---------|-----|
| Node IP 不在 CIDR 中 | `node IP is not in any of the remote network CIDR blocks` | 验证 `RemoteNodeNetworks` 包含 node IP range |
| API server 不可达 | `Unable to connect to the server` / `dial tcp: i/o timeout` | 检查 VPN/DX tunnel、防火墙端口 443、到 TGW/VGW 的 VPC routes |
| 未授权 | `Failed to ensure lease exists: Unauthorized` | 验证 IAM role、带有 `HYBRID_LINUX` 类型的 EKS access entry |
| Node 保持 NotReady | Node 已注册但 NotReady | 安装 CNI (Cilium)，检查 VXLAN 端口 8472 |
| DNS 解析失败 | EKS API endpoint 的 `no such host` | 配置 Route 53 Resolver Inbound Endpoint，更新本地 DNS |
| Image pull 失败 | system pods 上出现 `ErrImagePull` | 验证 ECR VPC endpoints、containerd registry 配置、CA 证书 |
| 证书错误 | `x509: certificate signed by unknown authority` | 在系统信任存储中安装 CA 证书，运行 `update-ca-certificates` |
| Hybrid profile 已存在 | `hybrid profile already exists` | 运行 `nodeadm uninstall`，然后运行 `nodeadm install`，再运行 `nodeadm init` |

#### SSM 凭证问题

| 问题 | 症状 | 修复 |
|-------|---------|-----|
| 无效 activation | `InvalidActivation` | 验证 nodeConfig.yaml 中的 region、activationCode、activationId |
| 过期 activation | `ActivationExpired` | 创建新的 SSM hybrid activation，更新 nodeConfig.yaml |
| 过期 token | `ExpiredTokenException` | 重启 SSM agent：`systemctl restart amazon-ssm-agent` |

#### IAM Roles Anywhere 问题

| 问题 | 症状 | 修复 |
|-------|---------|-----|
| 找不到证书 | `open /etc/iam/pki/server.pem: no such file or directory` | 创建 `/etc/iam/pki/` 目录，复制证书和密钥 |
| 未授权 | `not authorized to perform: sts:AssumeRole` | 验证 trust policy、trust anchor ARN、IAM RA profile |

### 诊断命令

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

### Node 重置

如果 bootstrap 失败并且你需要重新开始：

```bash
# Basic uninstall
sudo nodeadm uninstall

# Force uninstall (cleans all state, skips confirmation prompt)
sudo nodeadm uninstall --force

# Re-run initialization
sudo nodeadm init -c file://nodeconfig.yaml
```

**nodeadm uninstall 删除的路径：**
- `/etc/kubernetes` - Kubernetes 配置文件
- `/etc/eks` - EKS 相关配置
- SSM/IAM Roles Anywhere artifacts

**v1.0.9+ 变更：**
- 默认**保留** `/var/lib/kubelet`（数据保护改进）
- `--force` 选项会移除所有 artifacts，包括通常保留的 artifacts

---

< [上一页：Air-Gap 设置](./03-airgap-setup.md) | [目录](./README.md) | [下一页：GPU 集成](./05-gpu-integration.md) >
