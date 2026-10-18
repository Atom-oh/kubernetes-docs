# Node 生命周期管理

< [上一页：工作负载放置策略](./06-workload-placement.md) | [目录](./README.md) | [下一页：运维与维护](./08-operations.md) >

> **支持版本**：EKS Hybrid Nodes 使用 AWS 支持的 Kubernetes 版本；参考 nodeadm 1.0.20（通过 SSM 安装或升级需要 1.0.19+）
> **最后更新**：2026 年 9 月 13 日

本文介绍 EKS Hybrid Nodes 的高级 nodeadm 配置、集群安装自动化、升级策略、凭证生命周期管理和健康监控。

## 1. 高级 NodeConfig

### kubelet 调优

生产环境中，需要仔细调整 kubelet 资源预留、驱逐阈值、镜像垃圾回收和关机行为。

#### 资源预留（system-reserved / kube-reserved）

这些设置会在计算 Node Allocatable 时扣除预留资源；它们并非对每个主机进程都普遍适用的硬限制。默认的 enforceNodeAllocatable 设置覆盖 Pods；若还要强制执行 system/kube 预留，则需要有效的专用 cgroups 和经过审查的 cgroup 层级。选择数值前，应测量操作系统、kubelet、容器运行时以及 CNI/驱动的开销。

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| 参数 | 说明 | 初步规划示例；使用前需测量 |
|-----------|-------------|-------------------|
| `systemReserved.cpu` | 操作系统和系统守护进程使用的 CPU | 500m – 1000m |
| `systemReserved.memory` | 操作系统和系统守护进程使用的内存 | 1Gi – 2Gi |
| `kubeReserved.cpu` | kubelet 和 containerd 使用的 CPU | 500m – 1000m |
| `kubeReserved.memory` | kubelet 和 containerd 使用的内存 | 1Gi – 2Gi |

#### 驱逐阈值

kubelet 会尝试在节点级回收资源，并在资源压力下于必要时驱逐 Pod。这不构成稳定性保证；与 API 驱逐请求不同，节点压力驱逐不会遵守 PodDisruptionBudget。

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: 200Mi
      nodefs.available: 10%
      imagefs.available: 15%
      nodefs.inodesFree: 5%
      imagefs.inodesFree: 5%
    evictionSoft:
      memory.available: 500Mi
      nodefs.available: 15%
    evictionSoftGracePeriod:
      memory.available: 1m30s
      nodefs.available: 2m
    evictionMaxPodGracePeriod: 60
```

> **注意**：硬阈值没有配置软阈值观察期，达到后会立即终止。软阈值必须持续达到 evictionSoftGracePeriod 所规定的时间；evictionMaxPodGracePeriod 则单独限制 Pod 终止宽限期。软阈值不能阻止之后触发硬驱逐或 OOM。自定义 evictionHard 时，应指定完整的目标阈值映射，包括 inode 阈值：除非明确启用了受支持的默认值合并行为，否则省略项会变为零。

#### maxPods 计算

应根据 CPU、内存、守护进程开销以及 Cilium 每节点地址池来确定 maxPods。Cilium cluster-pool 会为每个 CIDR 预留两个 IPv4 地址，因此 /25、/24 和 /26 分别有 126、254 和 62 个可用地址。下方数值仅供规划，不是经验证的集群建议值，也不是从 ENI 推导的上限。不能通过简单修改现有的 clusterPoolIPv4MaskSize 来扩大已分配的地址块。

```yaml
kubelet:
  config:
    maxPods: 110  # /25 has 126 usable IPv4 addresses; leave capacity for overhead
```

| 掩码大小 | IPv4 地址总数 | maxPods 示例 |
|-----------|----------|-------------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### 镜像垃圾回收

自动清理未使用的镜像，以管理磁盘空间。

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### 关机宽限期

在受支持的 Linux 主机上，优雅关机依赖 systemd inhibitor locks 和 kubelet 配置。断电或强制关机时，无法保证 Pod 优雅终止。

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **注意**：此双组配置的总计 60 秒预算包含关键 Pod 的 20 秒，因此其他 Pod 可用的时间窗口为 40 秒。这不表示每个 Pod 都一定能获得 40 秒；其 terminationGracePeriodSeconds 设置和实际关机条件同样适用。

### 高级 containerd 配置

#### 私有 Registry 镜像设置

以下片段使用 containerd 1.x（配置版本 2）。containerd 2.x 应使用配置版本 3 以及 registry 插件路径 io.containerd.cri.v1.images.registry。重启运行时前，先检查安装版本和最终合并后的有效配置。必须验证 registry 信任和镜像路径支持；不要关闭 TLS 验证。

使用可信任的私有 registry 作为镜像源。下方 server 配置保留上游端点作为回退；它不构成隔离网络配置。依赖镜像源之前，应验证身份验证、代理项目路径和 CA 信任。

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

使用 `hosts.toml` 文件为每个 registry 配置镜像源：

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### GPU 节点的 NVIDIA Runtime Class

此 containerd 1.x 片段假设专用 GPU 节点上已经安装 NVIDIA runtime 二进制文件或工具包以及兼容驱动。它只注册一个处理程序，不会安装 GPU 软件栈。需要时，应通过实际的 RuntimeClass/工作负载配置选择该处理程序。containerd 2.x 应使用配置版本 3 和 io.containerd.cri.v1.runtime 插件路径；不要混用两种格式。设备插件/DRA 和工具包的前置条件请参见 GPU 章节。

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### Label 和 Taint 策略

#### nodeadm 自动添加的 Label

初始化 hybrid nodes 时，nodeadm 会自动分配以下 label：

```
eks.amazonaws.com/compute-type=hybrid
```

无需将此 label 手动添加到 `--node-labels`。

#### 自定义 Label 策略

按用途或环境添加 label，以便对工作负载放置进行精细控制。

```yaml
kubelet:
  flags:
    # Purpose-based labels
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # Environment-based labels (production)
    # - --node-labels=environment=production,tier=compute

    # Datacenter location labels
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### Taint 策略

| 策略 | 说明 | 使用场景 |
|----------|-------------|----------|
| 自动 Taint（NodeConfig） | 首次注册 Node 时应用；需明确协调现有 Node 的 Taint | 所有 hybrid nodes 共用的 Taint |
| 手动 Taint（kubectl） | 运维期间动态应用 | GPU 节点隔离、维护模式 |

```yaml
# Automatic taints in NodeConfig
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# Manual taint addition during operations
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoSchedule
```

<a id="full-production-nodeconfig-example"></a>

### 完整 NodeConfig 审查模板

这是尚未执行的配置模板，不代表已达到生产就绪状态。前面的 kubelet/containerd 片段应放在 spec 下。集群名称和 Region 必须对应预期集群；nodeadm 通过其获准的发现路径获取集群元数据。真实 activation 值只能通过获准的私有 NodeConfig 文件交付。containerd 语法和所有资源数值都应根据实际主机选择。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 10Gi
      kubeReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 5Gi
      evictionHard:
        memory.available: 200Mi
        nodefs.available: 10%
        imagefs.available: 15%
        nodefs.inodesFree: 5%
        imagefs.inodesFree: 5%
      evictionSoft:
        memory.available: 500Mi
        nodefs.available: 15%
      evictionSoftGracePeriod:
        memory.available: 1m30s
        nodefs.available: 2m
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
      evictionMaxPodGracePeriod: 60
    flags:
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
  containerd:
    config: "version = 2\n[plugins.\"io.containerd.grpc.v1.cri\".registry]\n  config_path\
      \ = \"/etc/containerd/certs.d\"\n"
```

---

## 2. 集群安装自动化

### Ansible Playbook

使用受控 inventory 和小批次来编排[引导流程](./04-node-bootstrap.md)。针对每种主机架构固定并验证 Hybrid Nodes 的 nodeadm 工件；不要把 amd64 二进制发给所有主机，也不要在批次执行期间重新下载未经审查的 `latest` 二进制。对于 SSM 安装或升级，AWS 要求 nodeadm **1.0.19 或更高版本**，因为较早版本包含过时的安装器签名密钥。本章参考 1.0.20；执行前应检查获准的 OS、Kubernetes、CNI、CSI 和运行时组合。

#### Inventory 配置

下列地址是文档占位值。实际主机连接目标应与其 Kubernetes Node 名称和 UID 分开记录。特别是，由 SSM 支持的 Node 名称不一定是可解析的 SSH 主机名。

```ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
gpu-host-a ansible_host=192.0.2.10 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[cpu_nodes]
cpu-host-a ansible_host=192.0.2.20 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[hybrid_nodes:vars]
ansible_user=REPLACE_WITH_APPROVED_OPERATOR
```

#### 自动化 Playbook

此 playbook 是针对**已预装主机的预检流程**，不是完整安装程序。首先通过获准的密钥文件流程交付由 root 拥有的私有 NodeConfig；activation code/private key 不得放在普通 inventory/group 变量中，也不得出现在模板日志中。将两个摘要占位符替换为所选版本的独立验证工件。它不会运行 install/init，也不会一边声称检查健康状态、一边启动已停止的服务。

```yaml
- name: Review preinstalled Hybrid Nodes before an approved bootstrap
  hosts: hybrid_nodes
  gather_facts: true
  become: true
  serial: 1
  any_errors_fatal: true
  vars:
    architecture_map:
      x86_64: amd64
      aarch64: arm64
    approved_nodeadm_sha256:
      amd64: REPLACE_WITH_REVIEWED_AMD64_SHA256
      arm64: REPLACE_WITH_REVIEWED_ARM64_SHA256
    nodeconfig_path: /etc/eks/nodeconfig.yaml
  tasks:
  - name: Require a reviewed architecture and binary digest
    ansible.builtin.assert:
      that:
      - ansible_facts.architecture in architecture_map
      - approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]] is match('^[a-f0-9]{64}$')
  - name: Inspect the existing nodeadm artifact
    ansible.builtin.stat:
      path: /usr/local/bin/nodeadm
      checksum_algorithm: sha256
      get_checksum: true
    register: nodeadm_artifact
  - name: Match the approved artifact
    ansible.builtin.assert:
      that:
      - nodeadm_artifact.stat.exists
      - nodeadm_artifact.stat.executable
      - nodeadm_artifact.stat.checksum == approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]]
  - name: Validate the privately delivered NodeConfig
    ansible.builtin.command:
      argv:
      - /usr/local/bin/nodeadm
      - config
      - check
      - -c
      - file://{{ nodeconfig_path }}
    changed_when: false
    no_log: true
```

仅有 kubelet 文件不足以证明安装已完成。预检后，应使用逐主机操作记录和身份检查，调用引导章节中的完整 install/init 流程。发生失败时应停止该批次；保留未知或部分完成的状态以便恢复，不要盲目重复运行 init。`changed_when: false` 只控制 Ansible 报告，不会改变实际执行命令的行为。

#### 基于角色的变量（GPU 节点与 CPU 节点）

| 主机组 | 需审查的逐主机配置 |
| --- | --- |
| CPU | 所选 OS/架构、运行时格式、实测资源预留、工作负载 label 和 taint |
| GPU | CPU 前置项，以及实际驱动/工具包、所选设备插件或 DRA 路径、运行时处理程序/RuntimeClass 和 GPU 验证 |

应为每台主机显式选择模板；`group_names[0]` 不是可靠的角色选择器。声明 `nvidia.com/gpu.present=true` 不会安装驱动，也不能证明存在可分配的 GPU。请参见 [GPU 集成](./05-gpu-integration.md)。

### 集群验证脚本

单独保存经过批准的 `expected-nodes.json`，其中列出集群中**所有预期的 Hybrid Nodes**。不要从正在测试的同一个 API 响应推导此预期集合，否则会掩盖缺失节点。替换节点会改变身份记录，需要有意识地协调处理。

```json
[
  {"name": "REPLACE_WITH_REGISTERED_NODE_NAME", "uid": "REPLACE_WITH_APPROVED_NODE_UID"}
]
```

将以下内容保存为 `check-fleet.sh`。它需要 Bash、kubectl 和 jq。在运维人员的工作站上设置 `KUBE_CONTEXT`；下方集群内观察器使用其 ServiceAccount。API 调用被拒绝或失败、节点集合为空、UID 不匹配，或 condition 缺失/为 Unknown，都会返回非零状态。

```bash
#!/usr/bin/env bash
# Read-only Node inventory/condition snapshot; no workload or host mutations.
set -euo pipefail
EXPECTED_FILE="${1:?Usage: check-fleet.sh expected-nodes.json}"
umask 077
WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
KUBECTL=(kubectl --cache-dir "$WORK_DIR/kube-cache")
if [ -n "${KUBE_CONTEXT:-}" ]; then KUBECTL+=(--context "$KUBE_CONTEXT"); fi
"${KUBECTL[@]}" get nodes -l eks.amazonaws.com/compute-type=hybrid -o json > "$WORK_DIR/nodes.json"
jq -e --slurpfile expected "$EXPECTED_FILE" '
  def required($kind; $status):
    [.status.conditions[]? | select(.type == $kind)] as $c |
    ($c | length) == 1 and $c[0].status == $status;
  $expected[0] as $want |
  ($expected | length) == 1 and ($want | type) == "array" and
  ($want | length) > 0 and
  ($want | length) == ($want | map(.name) | unique | length) and
  all($want[]; (.name | type) == "string" and (.name | length) > 0 and
               (.uid | type) == "string" and (.uid | length) > 0) and
  (.items | type) == "array" and
  (.items | map(.metadata.name) | sort) == ($want | map(.name) | sort) and
  all(.items[];
    . as $node |
    any($want[]; .name == $node.metadata.name and .uid == $node.metadata.uid) and
    .metadata.deletionTimestamp == null and
    .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
    required("Ready"; "True") and
    required("MemoryPressure"; "False") and
    required("DiskPressure"; "False") and
    required("PIDPressure"; "False"))
' "$WORK_DIR/nodes.json" > /dev/null
printf 'Expected Node identities and conditions match this snapshot.\n'
# CNI readiness, DNS, network paths, storage, applications and freshness need
# separate checks; Node Ready is not an end-to-end health guarantee.
```

这是 Node 库存与 condition 快照。`Ready=True` 不能证明当前 CNI、DNS、存储或应用运行正常。应分别检查所选 CNI 的实际 DaemonSet/Pods、相关站点间的连通性、DNS 解析、存储操作和工作负载端点；不要通过子字符串匹配把 `NotReady` 计为 Ready。

## 3. Node 升级策略

### 版本偏差策略

下方 1.31 表格用于说明版本偏差的计算方式，不是建议今天部署这些历史 Node 版本。应依据 AWS 当前文档选择受 EKS 支持的目标版本，以及兼容的 OS、CNI、CSI 和运行时。

Kubernetes 对 kubelet 与 API server 之间的版本兼容性有严格规定。

| kubelet 版本 | API Server 版本 | 兼容 |
|----------------|-------------------|------------|
| 1.31 | 1.31 | 是（相同版本） |
| 1.30 | 1.31 | 是（n-1） |
| 1.29 | 1.31 | 是（n-2） |
| 1.28 | 1.31 | 是（n-3） |
| 1.27 | 1.31 | 否（n-4，不受支持） |
| 1.32 | 1.31 | 否（kubelet 高于 API server，不受支持） |

> **升级顺序**：先将落后节点升级到当前控制平面次版本。将节点升级到下一个次版本之前，先升级控制平面。kubelet 版本不得高于 API server；支持的偏差范围不代表可以无限期保留旧节点。

### 升级前检查清单

每个批次开始前，批准目标主版本.次版本和完整工件版本/校验和，检查控制平面版本偏差以及 OS/CNI/CSI/运行时兼容性，并确认被驱逐工作负载有足够的备用容量。检查 Pod 请求/放置、PDB 允许的中断数、本地 PV/emptyDir 的所有权、备份/恢复和可观测性。`kubectl top` 是可选的实测用量，并不能证明每个 Pod 都能重新调度。

清点 Node 名称/UID、实际主机连接方式、凭证提供方和原始 `.spec.unschedulable` 状态。`nodeadm upgrade` 会保留 Node 名称，且不能更改凭证提供方。它通常会为请求的次版本选择最新工件；只固定次版本并不能构成不可变的工件计划。如需可重复执行，应使用获准的清单/私有工件流程。

### 滚动升级

每次只处理**一个明确选定的节点**，首次失败时即停止。下方示例是尚未执行的运维流程，并非经过可用性保证测试的集群控制器。应在获准的集群管理员工作站上、同一 shell 中运行首尾代码块，或恢复已记录的目录和输入后再运行。操作人员需要具备 Node、Lease、Pod/PDB 观察以及 cordon/drain 权限。

保存私有记录路径；这些命令会 cordon 并 drain 所选 Node。PDB 阻塞或存在本地 emptyDir 时，需要明确决定如何处理工作负载/数据。不要只为让失败的 drain 成功，就添加 force、disable-eviction 或 delete-emptydir-data。

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the actual Kubernetes Node name}"
: "${EXPECTED_UID:?Set the approved Node UID}"
UPGRADE_RECORD_DIR=$(mktemp -d "$PWD/hybrid-upgrade.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/node-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null
' "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/lease-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | type) == "string"
' "$UPGRADE_RECORD_DIR/lease-before.private.json" > /dev/null
printf 'Private upgrade record: %s\n' "$UPGRADE_RECORD_DIR"
kubectl --context "$KUBE_CONTEXT" cordon "$NODE"
kubectl --context "$KUBE_CONTEXT" drain "$NODE" --ignore-daemonsets --timeout=10m
```

只有 drain 成功后，才连接到**映射的物理/虚拟主机**，验证其记录的身份和经过审查的 nodeadm 二进制，然后在该主机上执行有中断影响的升级。NodeConfig 必须保留现有凭证提供方。不要把跳过 Node/Pod/init 验证当作常规操作。

```bash
set -euo pipefail
: "${TARGET_MINOR:?Set the approved EKS-supported major.minor target}"
sudo /usr/local/bin/nodeadm upgrade "$TARGET_MINOR" \
  -c file:///etc/eks/nodeconfig.yaml --timeout 20m
```

即使 Kubernetes 仍显示旧的 Ready condition，升级命令报错或会话丢失也表示操作状态未知/失败。保持 Node 处于 cordon 状态并调查。确认主机操作成功后，再从工作站观察；使用工件计划中的完整预期 kubelet 版本，包括任何 build 后缀。

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the recorded Node name}"
: "${EXPECTED_UID:?Set the recorded Node UID}"
: "${EXPECTED_KUBELET_VERSION:?Set the full version from the approved artifact plan}"
: "${UPGRADE_RECORD_DIR:?Use the private record directory from the pre-upgrade step}"
jq -e --arg uid "$EXPECTED_UID" --arg node "$NODE" \
  '.metadata.uid == $uid and .metadata.name == $node' \
  "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
POSTCHECK_DIR=$(mktemp -d "$UPGRADE_RECORD_DIR/check.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$POSTCHECK_DIR/node-after.private.json"
jq -e --arg uid "$EXPECTED_UID" --arg version "$EXPECTED_KUBELET_VERSION" '
  [.status.conditions[]? | select(.type == "Ready")] as $ready |
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null and
  .status.nodeInfo.kubeletVersion == $version and
  ($ready | length) == 1 and $ready[0].status == "True"
' "$POSTCHECK_DIR/node-after.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$POSTCHECK_DIR/lease-after.private.json"
jq -e --arg uid "$EXPECTED_UID" \
  --slurpfile before "$UPGRADE_RECORD_DIR/lease-before.private.json" '
  def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | epoch) > ($before[0].spec.renewTime | epoch)
' "$POSTCHECK_DIR/lease-after.private.json" > /dev/null
printf 'Node identity, target kubelet version, Ready and a newer Lease observed.\n'
# Workload/CNI/DNS/storage checks and the prior scheduling intent remain separate.
# This check never uncordons the node.
```

除目标版本和 Node 身份外，还要求 Lease 更新时间晚于所保存的快照。这仍不是应用验收测试。应验证 CNI、DNS、卷、驱动/运行时和工作负载恢复情况。仅当该 Node 在维护前可调度时，才明确取消 cordon。不要在 EXIT trap 中自动取消 cordon，也不要恢复原本已被有意 cordon 的 Node 的调度。保存证据后，再处理下一个获准的 Node。

### Canary 升级

应根据 OS/架构、运行时、凭证提供方和工作负载选择有代表性的 canary；不要选择 API 返回的第一个名称。采用同一套单节点流程，然后在服务约定的观察期内检查应用错误/延迟、存储/网络健康状况和实际版本。固定等待一段时间或仅检查 Node Ready 都不算通过。只有这些检查通过后，才扩展到后续小批次；切换完成且验收成功之前，应保留旧主机。

<a id="rollback-procedure"></a>

### 恢复与回滚边界

有备用容量时，AWS 建议使用替换主机并进行受控切换。在应用、存储、网络和目标版本检查通过之前，应保留旧主机。原地运行 `nodeadm upgrade` 会造成中断，它并非通用的事务式降级机制。

发生失败时，应让受影响的节点保持 cordon，停止剩余批次，保留诊断信息并检查已安装工件/凭证。使用与当前控制平面兼容的获准映像/版本恢复。即使旧的 `Ready=True` condition 仍可见，也不要自动取消 cordon；还要验证预期 Node 身份、实际 kubelet 版本以及工作负载就绪情况。

不要把递归删除 `/var/lib/kubelet` 或 `/etc/kubernetes` 当成通用回滚步骤。Pod 卷和 subpath 挂载可能暴露已挂载的主机或应用数据。从 nodeadm 1.0.9 起，即使强制卸载也会有意保留 `/var/lib/kubelet`；任何特殊清理都需要明确审查挂载和数据保留。卸载不会 drain 或删除 Kubernetes Node 对象，也不会彻底移除 CNI。对于 SSM，它还会注销托管实例。重建需要执行完整的安装/引导和身份协调流程，不能盲目循环执行卸载/重装。

---

## 4. 凭证生命周期

<a id="ssm-hybrid-activation-renewal"></a>

### SSM Hybrid Activation 到期

activation 的到期时间限制的是**新注册**。已经注册的节点仍是 Systems Manager 托管节点，直至显式注销。不要仅因原 activation 已过期，就卸载或重新注册健康节点。注册、agent 轮换凭证、IAM 权限和网络连接是彼此独立的生命周期。

只有在需要注册新主机，或获准的恢复流程要求重新注册时，才创建新的 activation。使用为 SSM 配置的实际 Hybrid Nodes IAM role；不要替换成通用 Run Command role。在执行该 AWS 资源创建命令前，检查 role 的信任策略/权限、账户、Region 和新节点的确切数量。activation code 类似密码，应将响应保存到私有文件，并通过获准的 NodeConfig 密钥文件流程交付。

```bash
set -euo pipefail
umask 077
: "${HYBRID_NODE_ROLE_NAME:?Set the reviewed Hybrid Nodes IAM role name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${NEW_NODE_COUNT:?Set the approved registration count}"
set -C  # Refuse to overwrite an existing private response file.
aws ssm create-activation   --iam-role "$HYBRID_NODE_ROLE_NAME"   --registration-limit "$NEW_NODE_COUNT"   --region "$AWS_REGION"   --output json > activation.private.json
```

AWS CLI 失败会留下不可信或可能部分写入的响应文件；停止操作并私下检查该文件，再决定是否重试。不要打印 activation code，也不要提交该文件。如果 API 默认注册时限不合适，应设置明确且获准的到期时间；最长为 30 天。数量是注册上限，并不是防止泄露 activation 被未授权主机使用的边界。

`nodeadm uninstall` 会注销由 SSM 管理的主机并移除已安装组件。之后只运行 `init` 不能代替 `install`。有意执行恢复前，应先审查 drain/数据保留和身份变更，再按完整[引导流程](./04-node-bootstrap.md)操作。必须将现有 Node 名称/UID 和 SSM 托管实例 ID 与库存协调起来；不要默默沿用旧的成功记录。

### IAM Roles Anywhere 证书续期

应通过节点现有的 PKI，在到期前更新其**主机身份验证证书**。这与 kubelet 客户端/服务器证书及 EKS 控制平面 CA 不同。证书 subject、配置的 nodeName、role session 条件、profile、role 和 trust anchor 必须保持兼容；更改 CN 并不是无害的文件轮换。

#### 证书到期监控

应检查配置的 certificatePath，而不是假定的路径。证书缺失、不可读、无效或将在 30 天内到期时，检查都会失败。30 天警告只是运维阈值示例。

```bash
#!/usr/bin/env bash
set -euo pipefail
CERT_PATH="${1:?Usage: check-cert-expiry.sh certificate.pem}"
test -r "$CERT_PATH" || { echo 'Certificate missing or unreadable' >&2; exit 1; }
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
# This is an expiration check only, not chain/key/CN/trust/IAM validation.
```

<a id="automatic-renewal-script"></a>

#### 证书续期流程

使用组织批准的 CA 客户端和经过身份验证的注册策略；不存在通用的未认证 `/sign` 端点。重复使用现有密钥时，应妥善保护；否则遵循获准的密钥轮换流程。提交带有预期身份的 CSR，并将签发后的候选证书与当前生效证书分开保存。

以下**仅为本地检查**，用于测试剩余有效期、相对于单独批准的根证书进行链验证，以及公钥是否匹配。需要时，通过 `INTERMEDIATE_CHAIN` 提供中间证书。它们不会检查所有 PKI/IAM 策略、吊销状态、nodeName/CN 或实时身份验证条件。

```bash
set -euo pipefail
umask 077
: "${CANDIDATE_CERT:?Path to the issued candidate leaf certificate}"
: "${PRIVATE_KEY:?Path to its existing protected private key}"
: "${APPROVED_CA_PEM:?Path to the separately approved trust roots}"
CERT_CHECK_DIR=$(mktemp -d)
trap 'rm -rf -- "$CERT_CHECK_DIR"' EXIT
openssl x509 -in "$CANDIDATE_CERT" -checkend 2592000 -noout
VERIFY=(openssl verify -CAfile "$APPROVED_CA_PEM")
if [ -n "${INTERMEDIATE_CHAIN:-}" ]; then VERIFY+=(-untrusted "$INTERMEDIATE_CHAIN"); fi
"${VERIFY[@]}" "$CANDIDATE_CERT"
openssl x509 -in "$CANDIDATE_CERT" -pubkey -noout > "$CERT_CHECK_DIR/cert.pub"
openssl pkey -in "$PRIVATE_KEY" -pubout > "$CERT_CHECK_DIR/key.pub"
cmp "$CERT_CHECK_DIR/cert.pub" "$CERT_CHECK_DIR/key.pub"
```

发布前应审查 subject/SAN、用途、CA 策略、吊销状态以及确切的 nodeName/role 条件。私下备份当前证书，然后由获准的证书管理器在同一文件系统上原子替换已验证证书，并保留所有者/模式。如果同时轮换密钥和证书，应协调这对文件，防止使用方读到不匹配的文件。

检查 nodeadm 配置的实际凭证助手模式（credential process 或 credential-file updater），并通过获准的私有诊断路径验证下一次凭证刷新。重启 kubelet 既不会续期 X.509 证书，也不能证明助手已接受它。只有针对该环境测试过签发者、候选证书拒绝、原子替换、刷新和回滚行为后，才安排自动续期；本章没有执行此类生产续期。

#### Trust Anchor 更新

在相同可信 CA 下续期叶证书通常不需要替换 trust anchor。CA 轮换会影响所有相关主机/profile/role。更改信任关系前，应与 PKI 和 IAM 负责人规划重叠期/迁移，检查来源类型及依赖节点，并保留恢复路径。

对于 **CERTIFICATE_BUNDLE** 来源，应使用 JSON 文件输入以保持 PEM 换行。此处 sourceData 联合类型只包含 x509CertificateData。AWS_ACM_PCA anchor 使用 acmPcaArn，需要单独审查。此示例会创建私有请求文件，随后执行 AWS 更新；不要把它作为常规证书到期监控的一部分运行。

```bash
set -euo pipefail
umask 077
: "${APPROVED_CA_PEM:?Path to the reviewed CA certificate bundle}"
: "${TRUST_ANCHOR_ID:?Set the reviewed existing trust anchor ID}"
: "${AWS_REGION:?Set the trust anchor Region}"
set -C
jq -n --rawfile bundle "$APPROVED_CA_PEM" \
  '{sourceType:"CERTIFICATE_BUNDLE", sourceData:{x509CertificateData:$bundle}}' \
  > trust-anchor-source.private.json
# AWS mutation: run only after the CA rollover and dependent-node review.
aws rolesanywhere update-trust-anchor --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --region "$AWS_REGION" --source file://trust-anchor-source.private.json \
  --output json > trust-anchor-update.private.json
```

读取并验证目标 anchor，然后对 canary 测试新凭证签发，再完成轮换。API 报错代表状态未知/失败，不能证明旧信任仍有效。切勿记录签发的凭证，也不要假设替换一个 anchor 会自动保留所有旧证书的访问权限。

## 5. 健康监控自动化

### 自动化健康检查 CronJob

此观察器会运行第 2 节中的 Node 快照检查。它**不会**在主机上执行 nodeadm，也不会验证主机的 AWS 凭证。应使用经过审查、包含 Bash、kubectl 和 jq、与集群兼容且可由 UID 10001 运行的映像。部署前必须替换映像占位符；本章没有验证任何映像或集群执行情况。监控 namespace 必须已经存在。

从已保存的 check-fleet.sh 和获准的 expected-nodes.json 创建 ConfigMap manifest。然后与下方 ServiceAccount/RBAC/CronJob 一同审查并应用。ClusterRole 可以列出所有 Node；label selector 只是查询过滤条件，不是授权边界。还应审查拥有权限、可以更改 ConfigMap 或使用该 ServiceAccount 运行 Pod 的 namespace 用户。

```bash
: "${KUBE_CONTEXT:?Set the approved cluster context}"
kubectl --context "$KUBE_CONTEXT" -n monitoring create configmap hybrid-node-check \
  --from-file=check-fleet.sh --from-file=expected-nodes.json \
  --dry-run=client -o yaml > hybrid-node-check.yaml
# Review this manifest and the observer/RBAC manifest before applying either.
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hybrid-node-observer
rules:
- apiGroups:
  - ''
  resources:
  - nodes
  verbs:
  - get
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hybrid-node-observer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: hybrid-node-observer
subjects:
- kind: ServiceAccount
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-observer
  namespace: monitoring
spec:
  schedule: '*/30 * * * *'
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      ttlSecondsAfterFinished: 1800
      template:
        spec:
          serviceAccountName: hybrid-node-observer
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: observer
            image: example.invalid/hybrid-observer:replace-with-reviewed-build
            command:
            - /bin/bash
            - /config/check-fleet.sh
            - /config/expected-nodes.json
            env:
            - name: TMPDIR
              value: /work
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            volumeMounts:
            - name: config
              mountPath: /config
              readOnly: true
            - name: work
              mountPath: /work
          volumes:
          - name: config
            configMap:
              name: hybrid-node-check
              defaultMode: 292
          - name: work
            emptyDir:
              sizeLimit: 64Mi
```

对于失败的 Job，**以及错过的执行/近期没有成功记录的情况**，都应告警。每 30 分钟轮询一次无法即时发现故障。应通过受保护的监控集成发送通知；不要把 Slack webhook bearer URL 放入 Pod 环境变量，也不要把通知失败当作健康检查成功。

### kubelet/containerd 状态监控（Node 级别）

以下 root 所有的脚本会观察本地服务状态和根文件系统，不会重启服务。单独挂载的 kubelet/containerd/镜像文件系统需要额外检查；仅检查根磁盘百分比并不足够。命令不可用或测量格式错误时，不得报告为健康。

```bash
#!/usr/bin/env bash
# Observe local services/filesystem; do not restart anything automatically.
set -euo pipefail
failed=0
for service in kubelet containerd; do
  if ! systemctl is-active --quiet "$service"; then
    printf '%s is not active\n' "$service" >&2
    failed=1
  fi
done
usage=$(df --output=pcent / | tail -n 1 | tr -d ' %')
case "$usage" in ''|*[!0-9]*) echo 'Unknown filesystem usage' >&2; exit 1;; esac
if [ "$usage" -ge 90 ]; then
  printf 'Root filesystem usage: %s%%\n' "$usage" >&2
  failed=1
fi
exit "$failed"
```

应通过经过审查的主机管理流程将脚本安装为 `/usr/local/bin/node-health-check.sh`，设置可执行权限，并确保不受不可信用户写入。timer/unit 是配置示例；需另行接入 journal 和失败单元监控。`PrivateTmp` 并不能使记录凭证变得安全。

```ini
[Unit]
Description=Periodic Hybrid Node local observation

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
[Unit]
Description=Observe Hybrid Node local services and root filesystem

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/node-health-check.sh
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
```

针对具体网络/凭证问题，操作人员可另行使用 root 权限运行 `nodeadm debug -c file:///etc/eks/nodeconfig.yaml`。该命令会联系 AWS 和集群，可能暴露诊断上下文；应私下保留输出。不要在每次 timer 触发时悄悄运行、丢弃其错误，或在没有针对具体事件作出决定前自动重启 kubelet/containerd。

## 验证与资料来源

本地验证覆盖示例解析、模拟的 Node/API 失败情形以及合成证书检查。它不能证明集群安装、主机升级、凭证轮换、Kubernetes admission、CNI/DNS/存储测试或生产 SLO 已完成。

- [AWS Hybrid Nodes nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS Hybrid Nodes 升级](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [SSM 注册与 activation 有效期](https://docs.aws.amazon.com/systems-manager/latest/userguide/hybrid-activation-managed-nodes.html)
- [IAM Roles Anywhere 凭证配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [UpdateTrustAnchor 输入](https://docs.aws.amazon.com/botocore/latest/reference/services/rolesanywhere/client/update_trust_anchor.html)
- [Kubernetes 版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [Node 压力驱逐](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [优雅节点关机](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)
- [containerd 配置](https://github.com/containerd/containerd/blob/main/docs/cri/config.md)
- [Cilium 1.20.1 cluster-pool 分配器](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst)

---

< [上一页：工作负载放置策略](./06-workload-placement.md) | [目录](./README.md) | [下一页：运维与维护](./08-operations.md) >
