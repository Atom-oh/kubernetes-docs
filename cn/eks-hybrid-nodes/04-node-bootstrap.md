# 节点引导

< [上一页：受限互联网设置](./03-airgap-setup.md) | [目录](./README.md) | [下一页：GPU 集成](./05-gpu-integration.md) >

> **支持的版本**：EKS Hybrid Nodes；已核对 nodeadm v1.0.20 源码。请为目标集群选择受支持的操作系统、Kubernetes 和 CNI 组合。
> **最后更新**：2026年9月12日

本章介绍如何将已准备好的本地主机接入 EKS，并区分软件安装、AWS 身份、初始化和经验证的工作负载就绪状态。示例要求先确定集群和主机，并由操作员批准相关变更。本地验证不能证明生产网络、操作系统镜像、PKI 或工作负载已经过测试。

## 引导工作流

1. 按照[先决条件](./01-prerequisites.md)和[网络配置](./02-network-configuration.md)，准备受支持的操作系统/运行时、唯一主机身份、时间同步、路由、DNS 和防火墙规则。
2. 准备 **Hybrid Nodes IAM 角色**、SSM 或 IAM Roles Anywhere 提供方，以及类型为 `HYBRID_LINUX` 的集群访问条目。仅有通用 SSM 管理角色并不足够。
3. 核实 Hybrid nodeadm 版本，然后在主机上或受控的操作系统镜像构建流程中安装依赖项。
4. 使用且仅使用一种凭证提供方，交付受保护的逐节点 NodeConfig。必要时配置代理和注册表信任。
5. 在已确认的主机上运行 `nodeadm config check`，然后运行 `nodeadm init`。
6. 配置受支持的 Hybrid CNI 和必需的附加组件。Node 即使已注册，也仍可能处于 `NotReady` 状态。
7. 验证准确的 Node 身份、Ready 条件、CNI/DNS、凭证刷新情况和受限范围的工作负载，再将其投入使用。

## nodeadm 与依赖项安装

Hybrid nodeadm 来自 **`aws/eks-hybrid`**，而不是 EC2 的 `amazon-eks-ami` 安装程序。新的 SSM 安装/升级需要 **nodeadm 1.0.19 或更高版本**，因为较早版本包含过时的 SSM 签名密钥。本次审查核对的是已发布的 **v1.0.20 源码**。

请通过 HTTPS 验证下载经批准的版本，并在以 root 执行前，将其摘要与独立批准的记录比对。不要盲目用可变的 `latest` 下载替换 `/usr/local/bin/nodeadm`。[受限互联网章节](./03-airgap-setup.md)介绍了镜像准备以及已检查版本的私有清单标志。本环境中的官方制品主机未通过 TLS 主机名验证，因此本次审计没有下载或执行 nodeadm 二进制文件。

```bash
# Target host/image builder: installs software. Choose exactly one provider.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${CREDENTIAL_PROVIDER:?ssm or iam-ra}" "${REGION:?}"
: "${CONTAINERD_SOURCE:?distro, docker or none for this OS}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
case "$CONTAINERD_SOURCE" in distro|docker|none) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" \
  --containerd-source "$CONTAINERD_SOURCE" --region "$REGION" --timeout 20m
```

新节点应优先使用与控制平面相同的小版本。支持的 kubelet 版本偏差只是兼容性范围，不代表应安装较旧且不受支持的 EKS 版本。kubelet 不能比 API server 更新；还应检查 EKS 和 CNI 支持情况以及上游版本偏差策略。

RHEL 不支持 `distro`；请使用文档指定的 Docker 软件包来源，或使用已预装的兼容运行时并选择 `none`。AL2023 不支持 `docker`。`none` 会跳过 containerd 安装。私有模式也会跳过操作系统软件包安装；它不会补齐缺失的运行时依赖项。

| 组件 | 文档记录的安装位置 |
|---|---|
| kubelet | `/usr/bin/kubelet` |
| kubectl | `/usr/local/bin/kubectl` |
| ECR 凭证提供方 | `/etc/eks/image-credential-provider/ecr-credential-provider` |
| AWS IAM authenticator / 签名助手 | `/usr/local/bin/aws-iam-authenticator` / `/usr/local/bin/aws_signing_helper` |
| SSM 设置 CLI | `/opt/ssm/ssm-setup-cli` |
| SSM Agent | Ubuntu snap：`/snap/amazon-ssm-agent/current/amazon-ssm-agent`；AL2023/RHEL：`/usr/bin/amazon-ssm-agent` |
| containerd | Ubuntu/AL2023：`/usr/bin/containerd`；RHEL 文档使用 `/bin/containerd` |
| nodeadm 跟踪器 | `/opt/nodeadm/tracker` |

`nodeadm install` 会通过已签名的设置 CLI 安装并配置 SSM agent；**SSM 注册发生在 `init` 阶段**。这不是手动执行 `dpkg`，再运行另一个不兼容的 nodeadm 安装程序。

## NodeConfig 与凭证

### SSM

为已准备好的 Hybrid 角色提供集群名称/Region 和有效的 activation code/ID：

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_ACTIVATION_CODE
      activationId: REPLACE_WITH_ACTIVATION_ID
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=workload.example.com/location=onprem
```

受保护的配置是输入模板，不应作为秘密提交到版本库。设置 root 所有权和 `0600` 权限；交付值时不要将其写入日志或 shell 历史。集群发现会通过 Hybrid 角色的 EKS 权限获取 API endpoint 和 CA。以 base64 编码字段传递的原始 PEM 块不能替代 API 所要求的表示格式。

`maxPods` 和关机等待时间只是规划示例，不是容量保证。检查 CNI 地址分配、预留 IP、资源和工作负载终止要求。可选的 `NoSchedule` taint 需要工作负载/CNI 配置相应的 toleration；不要添加会悄悄阻止必需 agent 或应用调度的默认 taint。

创建 activation 时只能由凭证所有者操作，并使用已准备好的 Hybrid 角色、正确的 Region、明确的到期时间和有上限的注册次数。将响应保存到私有文件中，不要直接打印 activation code：

```bash
# AWS write: owner-approved activation for one new host.
set -euo pipefail
umask 077
: "${REGION:?}" "${HYBRID_ROLE_NAME:?Prepared Hybrid Nodes IAM role name}"
: "${ACTIVATION_EXPIRY:?Future UTC timestamp within SSM service limits}"
test ! -e activation.json
aws ssm create-activation --region "$REGION" \
  --iam-role "$HYBRID_ROLE_NAME" --registration-limit 1 \
  --expiration-date "$ACTIVATION_EXPIRY" \
  --default-instance-name eks-hybrid-node > activation.json
```

请求失败或状态未知，并不意味着应盲目重试创建；请与凭证所有者核对实际状态。SSM 会使用生成的 `mi-*` 托管实例 ID 作为 Node 名称。普通重启会沿用 SSM 注册，并刷新临时凭证。重新注册需要仍有效且尚有剩余注册次数的 activation；到期时间和次数上限都很重要。

### IAM Roles Anywhere

使用在[先决条件](./01-prerequisites.md)中准备的 trust anchor、已启用的 profile、Hybrid 角色以及逐节点证书/密钥。每次执行本章流程时都不要重新创建 trust anchor/profile。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_ID
      roleArn: arn:aws:iam::111122223333:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

这些路径只是示例，并不意味着应在多台机器间复用同一张证书。请将 `nodeName` 绑定到角色信任策略所使用的证书属性；常见的 CN 条件要求二者匹配。名称必须符合 Node 命名规则，且最长为 64 个字符。在 profile 上启用 **`acceptRoleSessionName: true`**。

仅将角色最大会话时长设为 12 小时，并不会自动延长会话。实际请求/profile 时长必须不超过角色的 `MaxSessionDuration`；二者相等是允许的。根据安全和可用性要求选择时长，并验证凭证续期。静态 IAM 用户访问密钥不是 nodeadm 支持的第三种 Hybrid 节点凭证提供方。

## 私有注册表信任

对于内部注册表，请通过注册表所有者核实 CA 指纹和证书主机名。在适当情况下，优先采用仅针对该注册表的信任配置。不要全局安装任意收到的证书，也不要关闭主机名验证。

经批准注册表的 `hosts.toml` 示例：

```toml
# /etc/containerd/certs.d/registry.internal.example.com/hosts.toml
server = "https://registry.internal.example.com"

[host."https://registry.internal.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry.internal.example.com/ca.crt"
```

每个节点上都必须存在与之匹配且经过审核的 CA 文件。对于 containerd 1.x，注册表 `config_path` 应位于 `plugins."io.containerd.grpc.v1.cri".registry` 下；对于 containerd 2.x/配置版本 3，则应位于 `plugins."io.containerd.cri.v1.images".registry` 下。检查 nodeadm 生成的 `/etc/containerd/config.toml`，并使用与已安装运行时对应的配置节。不要将已弃用的内联注册表 `configs/auth` 与 `config_path` 配置组合，也不要把注册表密码放进 NodeConfig。

如果组织需要系统级 CA 信任，Ubuntu 使用 `/usr/local/share/ca-certificates/` 和 `update-ca-certificates`；RHEL/AL2023 使用 `/etc/pki/ca-trust/source/anchors/` 和 `update-ca-trust extract`。不要在 RHEL 示例中引用 Ubuntu 路径。普通 ECR 证书使用公共信任；操作系统仍需可用的 CA bundle。注册表信任与注册表身份验证是两回事。

## 初始化与验证

```bash
# Identified target host; init changes local configuration and joins EKS.
set -euo pipefail
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
```

对于使用私有清单的安装，请按照[受限互联网设置](./03-airgap-setup.md)中的说明，在 `init` 时传入经批准的 `--manifest-override` 和 `--private-mode`。代理设置必须传递给实际的 nodeadm/daemon 进程。`config check` 是本地配置检查，不是端到端的节点接入测试。

在**集群管理员**工作站上，核实预期的 kubeconfig context 和准确的预期 Node 名称（SSM 为 `mi-*`，IAM Roles Anywhere 为经批准的名称）：

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${EXPECTED_NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o json > node-registration.json
jq -e '.metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid"
  and (.metadata.uid | type == "string" and length > 0)' node-registration.json
expected_uid=$(jq -er '.metadata.uid' node-registration.json)
# After CNI and required add-ons are ready:
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" wait \
  --for=condition=Ready "node/$EXPECTED_NODE_NAME" --timeout=5m
observed_uid=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o jsonpath='{.metadata.uid}')
test "$observed_uid" = "$expected_uid"
```

记录 Node UID，并将 provider/地址与已确认的物理/虚拟主机进行比对。Ready 条件是必要条件，但还需验证 DNS、镜像拉取、连通性、凭证刷新和必需工作负载。先前的 `v1.31.0` 输出仅为历史示例，并非本次新注册的测量结果。

## 为已预装软件的主机配置 systemd 自动化

在受控的构建/安装阶段使用 `nodeadm install` 准备软件。以下自动化仅执行**初始化**，并将记录绑定到机器 ID、经批准的 nodeadm 二进制文件、NodeConfig 以及可选的私有清单。若状态发生变化或初始化只完成了一部分，它会拒绝静默重试注册。不要将注册状态、机器 ID、密钥或此状态目录克隆到其他节点。

root 所有、权限为 `0600` 的 `/etc/eks/bootstrap.env` 示例：

```text
NODECONFIG_PATH=/etc/eks/nodeconfig.yaml
APPROVED_NODEADM_SHA256=REPLACE_WITH_APPROVED_64_HEX_DIGEST
# Only for the reviewed private-manifest path:
# LOCAL_MANIFEST=/etc/eks/manifest.json
```

将以下 root 所有的脚本保存为 `/usr/local/bin/eks-hybrid-bootstrap.sh`。受保护的父目录和文件必须由主机所有者管理；这不能防御拥有 root 权限的恶意操作者。

```bash
#!/usr/bin/env bash
# Initialize one preinstalled, uniquely identified host. Run as root.
set -euo pipefail
umask 077
[[ "$EUID" -eq 0 ]]
: "${NODECONFIG_PATH:?Absolute per-node config path}"
: "${APPROVED_NODEADM_SHA256:?Hash from the approved binary record}"
[[ "$NODECONFIG_PATH" = /* ]]
[[ "$APPROVED_NODEADM_SHA256" =~ ^[0-9a-f]{64}$ ]]
NODEADM=/usr/local/bin/nodeadm
STATE=/var/lib/eks-hybrid-bootstrap

private_file() {
  local path=$1 owner mode
  [[ -f "$path" && ! -L "$path" ]]
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" == 600 ]]
}

private_file "$NODECONFIG_PATH"
test -s /etc/machine-id
test -s /opt/nodeadm/tracker
test -x "$NODEADM"
actual=$(sha256sum "$NODEADM")
[[ "${actual%% *}" == "$APPROVED_NODEADM_SHA256" ]]
if [[ -e /var/lib/eks/.nodeadm-installed || -e /var/lib/eks/.nodeadm-initialized ]]; then
  echo 'Legacy markers found: review existing installation and migrate state manually.' >&2
  exit 1
fi
[[ ! -L "$STATE" ]]
mkdir -p -m 700 "$STATE"
[[ "$(stat -c '%u:%a' "$STATE")" == 0:700 ]]
exec 9>"$STATE/lock"
flock -n 9

args=(--config-source "file://$NODECONFIG_PATH")
fingerprint_inputs=(/etc/machine-id "$NODEADM" "$NODECONFIG_PATH")
if [[ -n "${LOCAL_MANIFEST:-}" ]]; then
  [[ "$LOCAL_MANIFEST" = /* ]]
  private_file "$LOCAL_MANIFEST"
  fingerprint_inputs+=("$LOCAL_MANIFEST")
  args+=(--manifest-override "file://$LOCAL_MANIFEST" --private-mode)
fi
fingerprint=$(sha256sum "${fingerprint_inputs[@]}" | sha256sum)
fingerprint=${fingerprint%% *}
if [[ -e "$STATE/state" ]]; then
  private_file "$STATE/state"
  if [[ "$(cat "$STATE/state")" == "$fingerprint init-command-completed" ]]; then
    echo 'Matching initialization record; verify current Node readiness separately.'
    exit 0
  fi
  echo 'Changed identity/config or incomplete initialization: manual recovery required.' >&2
  exit 1
fi

"$NODEADM" config check --config-source "file://$NODECONFIG_PATH"
printf '%s started\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
# Failure/interruption retains started state and prevents an automatic retry.
"$NODEADM" init "${args[@]}"
systemctl is-active --quiet containerd
systemctl is-active --quiet kubelet
printf '%s init-command-completed\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
echo 'Init command completed; cluster registration/CNI/readiness still require verification.'
```

状态记录表示 init 命令已完成，且当时两个本地服务都处于活动状态。它**不表示 Kubernetes Node 已 Ready**。失败时会保留 `started` 记录；操作员应检查实际主机/SSM/集群状态后再协调处理。服务超时或命令中断，并不能证明注册没有发生。

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=Initialize one prepared EKS Hybrid Node
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
TimeoutStartSec=10min
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

通过主机配置管理方安装并启用该服务。`network-online.target` 按网络管理器的等待服务安排启动顺序；它不能保证 DNS、VPN、EKS 或凭证服务实际可达。`RemainAfterExit` 记录的是服务状态，不是节点健康状态。systemd 会解析 `EnvironmentFile`；脚本不会通过 shell `source` 执行该文件。

仅留下标记文件的旧安装需要显式迁移。仅删除 `.nodeadm-installed` / `.nodeadm-initialized` 并重启，并不是重置流程。对于启用凭证文件等经批准的配置变更，应遵照文档中的维护/init 流程，并在之后协调更新自动化记录。

普通重启时，已配置的 kubelet/凭证服务会恢复运行。删除 Kubernetes Node 对象不会注销 SSM，也不会停止 kubelet；仍在运行且获授权的 kubelet 可以重新创建 Node。不要把 `delete node` 当作主机退役操作，也不要假定每台故障主机都会重新接入。

## Cilium CNI

AWS 当前支持其维护的 **Cilium 1.17.x 和 1.18.x** Hybrid Nodes 版本。已发布示例包括 `oci://public.ecr.aws/eks/cilium/cilium` 中的 `1.17.9-0` 和 `1.18.3-0`。这并不意味着建议选择任意更新的上游 chart。

AWS 当前 CNI 页面明确指出，由于内核要求，**Ubuntu 20.04 和 RHEL 8 不适用于 Cilium v1.18.3**。不要声称只要更换内核就能获得 AWS 支持；应选择文档矩阵中列出的操作系统/CNI 组合。

Calico 示例已迁至 `aws-samples/eks-hybrid-examples`。这不代表 Calico 项目已弃用，也不保证现有的每个 Calico 部署都会继续正常工作。AWS 专门的当前 CNI 支持页面列出了 AWS 维护的 Cilium 版本和支持能力。

### 安装配置值

此 IPv4 cluster-pool 示例假设经过审核的远端 Pod 网络为 `10.85.0.0/16`，且与 Node/VPC/Service 网络不重叠。首次安装前，请替换为集群批准的值：

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/compute-type
              operator: In
              values: [hybrid]
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList: [10.85.0.0/16]
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
                values: [hybrid]
  unmanagedPodWatcher:
    restart: false
envoy:
  enabled: false
kubeProxyReplacement: "false"
preflight:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
```

预检 selector 与 agent affinity 相互独立。`/25` 包含 128 个地址；Cilium cluster-pool 会预留其中两个，因此不能保证有 128 个可用 Pod 地址。还需协调 kubelet `maxPods`、hostNetwork Pod 和其他限制。

不要修改现有 pool 条目或 `clusterPoolIPv4MaskSize`。Cilium 文档说明通过**添加**新的 pool 条目来扩展；请先协调 EKS 远端网络、路由/BGP、地址重叠及容量审核。声称“整个列表永远不能扩展”并不准确。

```bash
# Cluster write; requires approved context, values and supported chart.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${CILIUM_VERSION:?Approved AWS chart version}"
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values cilium-values.yaml --wait --timeout 10m
```

验证每个目标 Hybrid 节点上的 Cilium agent、operator、Node 就绪状态和跨节点流量。Affinity 会将此安装限制在 Hybrid 节点；云节点网络仍由其现有控制器管理。替换 kube-proxy 的设计需要单独的 API 可达性和迁移方案；不要让同一节点上同时存在相互冲突的 kube-proxy 行为。

### 升级和移除边界

升级 Cilium 前，保存当前 values/manifests 和明确的 Helm revision，查阅相应版本的升级说明，并使用批准的 values 渲染待部署的 chart。单独创建一个作用范围限于 Hybrid 节点的预检 release，并设置 `preflight.enabled=true`、`agent=false`、`operator.enabled=false`。请等待其 DaemonSet 覆盖到目标节点，**并且**验证 Deployment 已 Ready；创建预检 release 本身不等于预检通过。

只有预检通过后才移除该预检 release。使用经过审核并保存的 values 以及适当的 `upgradeCompatibility` 设置执行升级。不要使用 `--reuse-values`，将已过时的设置盲目带入次版本升级。回滚需要明确且经过验证的 revision，并须检查 CNI 状态/CRD 兼容性；它不能保证数据平面会自动恢复。

移除 CNI 是会造成中断的退役/迁移任务。请先迁移工作负载，并确认哪些节点、策略和 CR 仍依赖 Cilium。不要在共享集群中运行 `kubectl get crds | grep cilium | xargs kubectl delete`。Helm 卸载不能保证会清除主机路由、接口或 BPF 状态。请遵循相应版本的 CNI 清理流程，在已确认并疏散的主机上操作；删除路径前先检查活动挂载和保留数据。

## Bottlerocket 使用不同的引导约定

AWS 从 **1.37.0** 起支持 VMware Bottlerocket 变体，并要求使用受支持的 x86_64 Kubernetes 变体及相应前提条件。它**不运行 nodeadm**。AWS 指南通过配置 Kubernetes/AWS 设置以及 **`eks-hybrid-setup` 引导容器**来完成设置。此前的 `[settings.hybrid.ssm]` 和 `[settings.hybrid.iam-roles-anywhere]` 示例不是文档规定的设置格式。

请从[使用 Bottlerocket 连接 Hybrid 节点](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)中选择相应 provider 的完整设置。常见字段包括：

```toml
# Common fragment only: combine with the provider-specific settings from AWS.
[settings.kubernetes]
cluster-name = "my-hybrid-cluster"
api-server = "https://REPLACE_WITH_CLUSTER_ENDPOINT"
cluster-certificate = "REPLACE_WITH_BASE64_CLUSTER_CA"
hostname-override = "hybrid-node-001"
provider-id = "eks-hybrid:///ap-northeast-2/my-hybrid-cluster/hybrid-node-001"
authentication-mode = "aws"
cloud-provider = ""
server-tls-bootstrap = true

[settings.network]
hostname = "hybrid-node-001"

[settings.aws]
region = "ap-northeast-2"

[settings.kubernetes.node-labels]
"eks.amazonaws.com/compute-type" = "hybrid"

[settings.bootstrap-containers.eks-hybrid-setup]
mode = "always"
user-data = "REPLACE_WITH_BASE64_PROVIDER_BOOTSTRAP_INPUT"
```

此片段不是可直接启动的完整配置。SSM provider 会向 `eks-hybrid-ssm-setup` 提供 activation/Region 输入；注册后，Node 名称会改为 `mi-*`。IAM Roles Anywhere 会向 `eks-hybrid-iam-ra-setup` 提供证书/密钥输入和 AWS credential-process 配置，并将 role session name 绑定到证书策略。还要包含文档规定的 ECR provider 以及 provider 专属的节点标签/设置。

Base64 是编码，不是加密。Provider 引导数据可能包含 activation 秘密或私钥：请保护 VM 配置、guestinfo、管理权限和诊断导出；切勿放入公共仓库或日志。Admin container 的 SSH 访问是可选项，且必须单独授权。不要将已注册的 VM 克隆成干净模板。

首次开机前，先配置经批准、**已关机且新建的 VM**。AWS 指南使用 base64 编码的 `settings.toml`，并设置 `guestinfo.userdata.encoding=base64`；不要把普通 base64 标成 `gzip+base64`。预配前请确认实际使用的 govc/VMware 版本、数据存储、网络、模板所有权和秘密交付方式。本次审计没有执行 VMware 部署。

## 附加组件放置与 Pod Identity

将 API server 流量路由到实际的 webhook/聚合 API 监听器。如果 Hybrid Pod CIDR 不可达，应将**webhook server/operator** 放置在可达的云节点上，或在支持的情况下验证适当的 hostNetwork 设计。这不意味着每个 CloudWatch/ADOT agent 或应用 Pod 都必须运行在云端。

将工作负载放到云节点时，使用明确审核过的节点标签/affinity，并检查容量/taint。`NotIn [hybrid]` 也会匹配没有标签的节点，因此不能证明目标节点属于获批的 EC2 节点。

在云端与 Hybrid 混合的集群中，AWS 建议两侧各至少运行一个 CoreDNS 副本。四个副本加软性拓扑分布约束，并不能保证两侧各正好两个副本。请在[网络配置](./02-network-configuration.md)中应用并验证节点放置与 Service Traffic Distribution 流程。

| 节点操作系统 | Pod Identity 准备工作 |
|---|---|
| Ubuntu/RHEL/AL2023 | 设置 `spec.hybrid.enableCredentialsFile: true`，然后按文档运行 `nodeadm init`；agent 配置启用 `daemonsets.hybrid.create` |
| Bottlerocket | 操作系统 **1.39.0+**；provider 引导命令使用 `--enable-credentials-file=true`；启用 `daemonsets.hybrid-bottlerocket.create` |

兼容性最低版本为：非 Bottlerocket agent **v1.3.3-eksbuild.1**，Bottlerocket agent **v1.3.7-eksbuild.2**；这些不是当前建议安装的目标版本。请为集群选择当前兼容的附加组件版本/配置架构。挂载的临时凭证路径不同：`/eks-hybrid/.aws/credentials` 与 Bottlerocket 的 `/var/eks-hybrid/.aws/credentials`。

私有部署需要 `eks-auth` 服务路径、节点角色的 `eks-auth:AssumeRoleForPodIdentity` 权限，以及每个工作负载各自的 Pod Identity association/信任/权限。仅安装 agent 并不足够。请通过附加组件所有者合并所需的 DaemonSet 配置；不要用盲目执行的 `create-addon` 覆盖现有附加组件。

## 升级、恢复和移除

优先新增**已完成初始化并验证的替代容量**，然后再疏散旧节点。只在新主机上安装二进制文件并不会增加集群容量。保留必需的 DNS 可用性；不要为了所谓的“弹性”盲目将现有四副本 CoreDNS 部署缩减到两个。

针对一个已确认的旧节点，核对 context、Node UID、主机映射以及工作负载/数据所有权。执行 cordon 和带超时的 drain；若出现任何 PDB/eviction 错误就停止。`--delete-emptydir-data` 明确允许丢弃本地 emptyDir 数据，不应作为默认安全选项。非托管 Pod、本地持久数据和 DaemonSet 需要分别处理。不要使用 `--force` 或禁用 eviction 来假装解除被阻止的 drain。

原地更新时，应在已疏散的主机上运行文档规定的 `nodeadm upgrade`，然后验证身份、软件版本、Ready/CNI/DNS 和工作负载行为，再取消 cordon。这会造成中断；“没有备用容量”并不能让这种做法变安全。

退役时，先停止任何自动引导/重新加入路径，完成文档规定的 nodeadm 移除和 provider 注销，再删除确切的 Node 对象，并由其所有者协调剩余 CNI 资源。必要的恢复证据应私下保存。

`nodeadm uninstall` 不等于 `kubectl drain` 或 `kubectl delete node`。如果仍有工作负载 Pod，它通常会拒绝执行。它不会删除所有 CNI/附加组件制品。**从 v1.0.9 起，即使使用文档规定的 force/skip 卸载路径，也不会删除 `/var/lib/kubelet`**，因为已挂载的路径可能暴露主机文件系统。`--force` 会额外删除默认 CNI/Kubernetes 路径；它不是一个通用的“跳过确认并删除所有内容”标志。任何手动删除前都要检查挂载和数据。

如果移除后获准重新安装，请使用有效凭证再次按 **install → config check → init** 顺序执行，并协调更新自动化记录。不要仅因身份验证错误、现有 profile 或 init 部分完成，就卸载仍在运行的节点。

## 故障排查

| 现象 | 更改状态前先调查 |
|---|---|
| 较旧 nodeadm 上的 SSM 安装程序签名失败 | 确认已批准的 nodeadm 至少为 1.0.19；不要绕过签名检查 |
| 软件包管理器/下载失败 | 实际仓库访问、代理、CA 信任、软件包锁、受支持的操作系统/运行时以及具体错误；`dnf update` 是系统升级，不是诊断命令 |
| 超时 | 确定失败阶段和可达性；单纯延长超时并不能修复问题 |
| Node IP 不在远端网络范围内 | 核对实际配置的节点 IP 与 EKS remote-node CIDR |
| API 无法访问 / Unauthorized | 检查 DNS/路由/443 端口和返回路径、预期 Hybrid 角色、信任/凭证有效性以及 `HYBRID_LINUX` access entry |
| NotReady | 检查 CNI/agent 日志、选定的数据通路端口、运行时、磁盘/资源条件；并非所有情况都是缺少 CNI |
| 镜像拉取或 x509 错误 | 检查准确的镜像/身份验证路径、ECR API/DKR/S3、私有注册表 CA 和主机名；保持 TLS 验证开启 |
| Activation / token 过期 | 对比 activation 到期时间/次数/Region 与运行中 agent 的凭证续期、时间同步和 AWS 可达性；重启不保证解决问题 |
| Hybrid profile 已存在 / init 部分完成 | 检查当前 nodeadm/provider 状态和预期集群；保留证据，不要自动卸载 |

```bash
# Private diagnostic output on the identified node; no nonexistent nodeadm status.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet --since '-15 min' --lines 200 --no-pager
sudo nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml
```

`nodeadm debug` 会读取 AWS/集群信息并检查凭证。请私下保存其输出，并在分享前进行脱敏。`sudo aws sts get-caller-identity` 可能使用不同的 root/admin 凭证链，不能证明 kubelet 实际使用了什么凭证。不要使用 `curl -k` 进行 TLS 验证。服务器 CA 信任与 kubelet 客户端证书的批准/签发是两种不同机制。

## 主要参考资料

- [Hybrid nodeadm 命令、文件位置和移除行为](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid 凭证](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [IAM Roles Anywhere CreateSession 时长](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [SSM CreateActivation](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)
- [AWS Hybrid CNI 支持与生命周期](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium cluster-pool 扩展](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/ipam/cluster-pool.rst)
- [Bottlerocket Hybrid 引导](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)
- [Hybrid 附加组件与 Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [containerd 注册表主机配置](https://github.com/containerd/containerd/blob/v2.2.0/docs/hosts.md)
- [systemd network-online 语义](https://systemd.io/NETWORK_ONLINE/)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)

< [上一页：受限互联网设置](./03-airgap-setup.md) | [目录](./README.md) | [下一页：GPU 集成](./05-gpu-integration.md) >
