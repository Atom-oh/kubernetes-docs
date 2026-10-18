# 裸金属服务器操作系统安装与迁移指南

< [上一章：运维](./08-operations.md) | [目录](./README.md) | [下一章：混合节点网关](./10-hybrid-nodes-gateway.md) >

> **验证基线**：已于 2026 年 9 月 13 日核查 AWS Hybrid OS/nodeadm 文档和公开价格；nodeadm 1.0.20 是本次审查的 CLI 参考版本。请选择当前受支持的 EKS/OS/CNI 组合。
> **最后更新**：September 13, 2026

本指南将具有破坏性的操作系统安装、映像准备、加入集群和只读验收检查分别说明。示例包含占位符，必须根据具体主机制定安装计划。本次审查未执行任何操作系统安装、Packer 构建、VM 创建或 AWS/集群操作。

## 概述

### 为什么选择裸金属

移除虚拟机管理程序可以避免其许可费用和执行层，但不能保证总成本更低或应用性能更好。在选择替代方案前，应盘点虚拟化功能、可用性、备份、存储、网络、支持合同和迁移工作量。VM 应用不会自动转换成容器，试点集群启动后，现有许可义务也不会消失。

### 操作系统基础设施支持矩阵

| 操作系统 | 裸金属 | 本地虚拟化 | 配置和支持边界 |
| --- | --- | --- | --- |
| Ubuntu 20.04/22.04/24.04 | 列出的 Hybrid OS 系列 | 符合 OS/kernel/CNI 要求的受支持主机基础设施 | nodeadm/YAML；需单独核实 Ubuntu 生命周期和支持情况 |
| RHEL 8/9 | 列出的 Hybrid OS 系列 | 符合 OS/kernel/CNI 要求的受支持主机基础设施 | nodeadm/YAML；Red Hat 订阅/OS 支持仍需单独处理 |
| AL2023 | **不是受支持的部署路径** | 本地虚拟化的来宾系统 | nodeadm/YAML；AWS Support Plans 不涵盖 EC2 之外的 AL2023 |
| Bottlerocket VMware 变体 >=1.37.0 | **不支持用于 Hybrid 裸金属** | VMware vSphere，**x86_64** | Bottlerocket 设置/引导；govc 用于管理 VMware VM |

AWS 支持与所列 Ubuntu/RHEL 系列的 Hybrid 集成，但不承担 OS 供应商的支持义务。请核实具体版本、架构以及 CNI/kernel 要求。EC2 之外的 AL2023 是 VM 来宾系统选项，并非通用的原始映像裸金属建议。Bottlerocket 的 VMware Kubernetes 变体从 1.28 版开始；这是变体的版本历史，并非建议运行如此旧的 EKS 版本。SSM 安装/升级需要 nodeadm >=1.0.19，因为较旧版本使用过时的 SSM 签名密钥。

## 成本比较分析

### 许可/订阅成本比较

#### VMware vSphere

请根据实际产品捆绑、许可核心数、最低要求、期限和支持获取当前报价。此处没有经过核实的旧版每插槽每年 $4,500–8,500 价格依据，不能将其视为当前 vSphere 报价。

#### OpenShift

请统一核算实际的 Red Hat 授权、物理/虚拟核心数或插槽计费标准以及支持层级。旧版每节点每年 $2,500–5,000 的估算和“包含高级支持”的说法均未核实；不要将其作为当前价格或授权保证。

#### EKS Hybrid Nodes

[官方价格页面](https://aws.amazon.com/eks/pricing/)按**上报的节点 vCPU 小时数**采用每月累进分档收费：前 576,000 小时为 $0.020；接下来的 576,000 小时为 $0.014；接下来的 4,608,000 小时为 $0.010；接下来的 5,760,000 小时为 $0.008；超过 11,520,000 小时的部分为 $0.006。这不是通用的固定 $0.01 费率。

在单个账户/区域内，或通过 AWS Organizations 合并账单在同一区域的多个账户之间，分档用量会汇总。启用超线程的裸金属核心可能各自上报两个 vCPU。节点加入时开始计费，移除时停止计费；工作负载闲置不会免除节点费用。对于超过 32 vCPU 的机器，AWS 建议客户联系其客户团队。集群、预置控制平面/功能、网络、日志记录、存储、操作系统和其他支持费用需另行计算。

### 不同规模的年度成本比较（32 vCPU 服务器）

以下是一个确定性的**模型**，不是账单或测量结果：每个节点上报 32 vCPU、每月均按 730 小时计算、使用一个区域/汇总范围、没有其他 Hybrid 用量，并按 12 个相同的模型月份计算。最后一列加上一个按标准支持收费 $0.10/小时的基础层集群。未计入其他服务、折扣/税费、硬件、电力、OS 授权、人力和迁移成本；实际月份长度/分档重置会影响账单。

| 节点数 | 每月 vCPU 小时数 | 每月节点费用 | 年化节点费用 | 年化节点费用 + 一个基础标准支持集群 |
| --- | --- | --- | --- | --- |
| 10 | 233,600 | $4,672.00 | $56,064.00 | $56,940.00 |
| 50 | 1,168,000 | $19,744.00 | $236,928.00 | $237,804.00 |
| 100 | 2,336,000 | $31,424.00 | $377,088.00 | $377,964.00 |

<details>
<summary>保留的历史估算（未经核实且并非当前价格）</summary>

为便于追溯，保留了原始表格。无法核实供应商报价来源。其 EKS 列采用了过时的假设 `32 × $0.01 × 8,760 = $2,803.20/node-year`，且未计入集群费用或累进分档。这些数字不能作为当前有效的比较性 TCO 证据。

| 规模 | VMware vSphere（先前年度估算） | OpenShift（先前年度估算） | EKS Hybrid（过时的固定费率估算） |
| --- | --- | --- | --- |
| 10 个节点 | ~$45,000–85,000 | ~$25,000–50,000 | ~$28,032 |
| 50 个节点 | ~$225,000–425,000 | ~$125,000–250,000 | ~$140,160 |
| 100 个节点 | ~$450,000–850,000 | ~$250,000–500,000 | ~$280,320 |

</details>

### TCO（总拥有成本）考量

请将备用容量、设施/电力、OS/安全补丁、PKI/SSM 运维、存储/备份/恢复、连接、监控、人员、许可义务和回滚能力纳入考虑。比较支持范围相同的方案；不要依据未经核实的旧表格声称节省了某个百分比。

## 特定操作系统的裸金属安装

### 先决条件

#### BIOS/UEFI 设置

请核实所选安装程序、固件、启动模式、NIC/存储驱动程序和已签名启动链。只要经过验证的引导加载程序/kernel/module 链支持 Secure Boot，就应保持启用；不要将禁用它当作容器的通用前提。普通 Linux containerd/runc 容器不需要 VT-x/AMD-V 硬件虚拟化。基于 VM 的沙箱、QEMU/KVM 映像构建器和其他虚拟化工作负载有各自独立的要求。

#### 网络基础设施

传统 PXE 通常使用 DHCP/ProxyDHCP 和 TFTP，而 UEFI HTTP/iPXE 设计可以使用不同的启动传输方式。`pxelinux.0` 并非通用的 UEFI 引导程序。请使用适合固件的引导程序，核实 ISO/kernel/initrd 的完整性，并将预配网络与工作负载网络分开。请保护主机专属配置；不要通过未经身份验证的共享 HTTP/TFTP 根目录提供激活码、私钥或密码。

#### AWS Packer 模板

[AWS 示例目录](https://github.com/aws/eks-hybrid/tree/main/example/packer)当前包含 `hybrid-nodes-template.pkr.hcl`，而不是原文中虚构的 `bare-metal-template.pkr.hcl`。其输入 `CREDENTIAL_PROVIDER` 接受 `ssm` 或 `iam`；其中的 HCL 会将 `iam` 映射到 nodeadm 的 `iam-ra`。QEMU 输出使用 `PACKER_OUTPUT_FORMAT`，而不是 `output_format` 变量。请在经批准的提交版本中审查模板和 provisioner 脚本，包括必需的 builder 输入以及密码/用户数据处理方式。

```bash
# From a reviewed checkout of aws/eks-hybrid/example/packer:
export NODEADM_ARCH=amd       # This template uses amd/arm, not amd64/arm64.
export CREDENTIAL_PROVIDER=ssm # The template accepts ssm/iam; maps iam to nodeadm iam-ra.
export PACKER_OUTPUT_FORMAT=raw
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
: "${ISO_URL:?Set the approved Ubuntu or RHEL installer ISO}"
: "${ISO_CHECKSUM:?Set the verified vendor ISO checksum}"
export K8S_VERSION ISO_URL ISO_CHECKSUM
# Also prepare the selected builder's required inputs using the reviewed template.
packer validate -syntax-only hybrid-nodes-template.pkr.hcl
# A separate build action, not a validation step:
# packer build -only=general-build.qemu.ubuntu24 hybrid-nodes-template.pkr.hcl
```

该模板还包含 AMI/vSphere builder：请在单独授权构建前，仅选择预期使用的 builder。仅做语法验证并不代表映像已构建/测试。不要将过时的 Kubernetes 示例、默认 builder 密码、全局可读的凭据文件或已注册的机器/SSM 身份复制到可复用映像中。

对于手动预配的主机，请准备经批准的 nodeadm 版本/架构，并附上经过审查的校验和。这是**安装步骤**，不是健康检查。请通过经批准的版本验证流程获取校验和；不要自行编造，也不要绕过校验不匹配的问题。

```bash
set -euo pipefail
: "${NODEADM_VERSION:?Set the approved release, at least 1.0.19 for SSM}"
: "${NODEADM_SHA256:?Set the approved SHA-256 for this release and architecture}"
: "${NODEADM_ARTIFACT:?Set the local file delivered through the approved artifact channel}"
case "$(uname -m)" in
  x86_64) NODEADM_ARCH=amd64 ;;
  aarch64|arm64) NODEADM_ARCH=arm64 ;;
  *) printf 'Unsupported architecture\n' >&2; exit 2 ;;
esac
[[ "$NODEADM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "$NODEADM_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || exit 2
[[ "$(printf '%s\n' 1.0.19 "$NODEADM_VERSION" | sort -V | head -n 1)" == 1.0.19 ]] || exit 2
umask 077
STAGING_DIR=$(mktemp -d)
trap 'rm -f -- "$STAGING_DIR/nodeadm"; rmdir -- "$STAGING_DIR"' EXIT
cp -- "$NODEADM_ARTIFACT" "$STAGING_DIR/nodeadm"
printf '%s  %s\n' "$NODEADM_SHA256" "$STAGING_DIR/nodeadm" | sha256sum --check -
chmod 0700 "$STAGING_DIR/nodeadm"
# Check the verified staged binary before replacing the installed executable.
ACTUAL_VERSION=$("$STAGING_DIR/nodeadm" --version)
VERSION_RE="(^|[^0-9.])v?${NODEADM_VERSION//./\\.}([^0-9A-Za-z.+-]|$)"
[[ "$ACTUAL_VERSION" =~ $VERSION_RE ]] || { printf 'Artifact version mismatch\n' >&2; exit 2; }
printf '%s\n' "$ACTUAL_VERSION"
sudo install -m 0755 "$STAGING_DIR/nodeadm" /usr/local/bin/nodeadm
/usr/local/bin/nodeadm --version
```

### Ubuntu LTS (22.04/24.04)

Ubuntu Server 的 Subiquity Autoinstall 使用 YAML；cloud-init 可以提供其配置。以下模板刻意保留交互式存储配置，并要求在使用前提供准确的已批准磁盘序列号和 SSH 密钥。选择/分区磁盘会销毁其现有数据。请先在可丢弃的目标上确认备份、磁盘清单、安装程序交付、访问/恢复方式和固件兼容性。对于装有数据盘的主机，不应使用通配符/空磁盘匹配，也不应假定选择“最大磁盘”。

#### Autoinstall 配置示例

```yaml
#cloud-config
autoinstall:
  version: 1
  interactive-sections: [storage]
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
      match:
        serial: REPLACE_WITH_APPROVED_DISK_SERIAL
  identity:
    hostname: replace-with-unique-hostname
    username: hybrid-admin
    password: "!"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
    - "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
  packages: [curl, jq]
  shutdown: poweroff
```

此模板中的 `password: "!"` 会锁定密码身份验证；请核实经批准的 SSH 访问和恢复路径。请根据主机和所选安装程序提供相应的网络/NIC/VLAN/bond 设置。本地架构检查不会测试磁盘选择、启动或登录。nodeadm 会在上文所述的单独步骤中暂存/安装；安装程序不会获取未经验证的 `latest` 二进制文件。

#### Ubuntu 24.04 特定说明

[Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)涉及容器终止期间 AppArmor 拒绝信号的问题，已有发布的程序包修复。AWS 的 OS 页面仍说明了 1.7.19+ 修复所涉及的背景。请检查实际的发行版程序包/回移补丁、已加载的配置文件、运行时和拒绝日志。这并不能普遍解释所有卡住的 Pod，也不意味着建议继续使用旧版 containerd。

```bash
# Read-only investigation on the affected host:
containerd --version
dpkg-query -W 'containerd*' 'runc*' 'apparmor*'
sudo journalctl -k --since '30 minutes ago' --no-pager -n 200
if test -f /run/reboot-required.pkgs; then cat /run/reboot-required.pkgs; fi
```

对于文档所述的受影响程序包/配置文件转换，Ubuntu 问题要求重启以加载已修正的配置文件；请通过生命周期流程安排节点排空、重启和工作负载检查。不要笼统地认为每次修改 AppArmor 都需要重启。`aa-remove-unknown` 会移除 `/etc/apparmor.d` 中不存在的所有已加载配置文件；它不是针对特定配置文件的编辑工具，也不是默认的修复命令。

### RHEL 9

RHEL 使用 Kickstart。以下内容是安装模板，**不是 Bash**。请替换为经批准的单个安装磁盘标识符、密码哈希和完整 SSH 公钥。`ignoredisk --only-use` 和 `clearpart --drives` 必须指定同一个已核实的磁盘；不要使用不受限制的 `clearpart --all`。请根据所选 RHEL 安装程序配置仓库/stage2/bootloader/网络详细信息，并在使用前通过其 ksvalidator 验证。

#### Kickstart 配置示例

```text
# Template: substitute and validate the approved target disk, key and password hash.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
rootpw --lock
user --name=hybrid-admin --groups=wheel --iscrypted --password=REPLACE_WITH_CRYPT_HASH
sshkey --username=hybrid-admin "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=REPLACE_WITH_APPROVED_INSTALL_DISK
clearpart --all --initlabel --drives=REPLACE_WITH_APPROVED_INSTALL_DISK
autopart --type=lvm
selinux --enforcing
services --enabled=sshd
%packages
@core
openssh-server
curl
jq
%end
poweroff
```

保持 SELinux 处于 enforcing 状态，并针对具体的策略/上下文要求进行诊断。nodeadm 文档说明了 containerd SELinux 配置和 Pod 安全上下文；不要笼统地将 `container_t` 标记为 permissive。OS 程序包与 nodeadm/containerd 安装属于不同阶段。

#### RHEL containerd 安装说明

`distro` 不是 RHEL 上受支持的 nodeadm containerd 来源。选择 `docker`，让 nodeadm 安装兼容的 Docker-distributed 程序包；如果单独安装/维护 containerd，则选择 `none`。“RHEL 始终需要 docker”这种说法过于宽泛。

```bash
set -euo pipefail
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
sudo nodeadm install "$K8S_VERSION" --credential-provider ssm \
  --containerd-source docker
# If containerd is separately installed and maintained, choose --containerd-source none.
```

#### 大规模环境：Satellite/Foreman 集成

Satellite/Foreman 可管理经过审查的 Kickstart 模板、仓库和预配工作流。请逐台验证磁盘、硬件标识、订阅、构件完整性和故障恢复；语法有效的共享模板并不意味着可以清除任意主机群的数据。

### Amazon Linux 2023

这是**虚拟化来宾系统参考**，不是裸金属安装选项。AWS 为 EC2 之外的 AL2023 提供 KVM、VMware 和 Hyper-V VM 映像。AWS Support Plans 不涵盖 EC2 之外的 AL2023 OS 使用；请将其与 EKS Hybrid 集成支持区分开来。请使用合适的映像和 cloud-init 传输方式。最简 VM 身份片段如下：

```yaml
#cloud-config
# VM identity fragment only; it does not install or join a Hybrid Node.
hostname: replace-with-unique-hostname
manage_etc_hosts: true
ssh_pwauth: false
```

该片段有意不创建管理员、不嵌入密钥，也不初始化节点。请准备经批准的访问方式，并使用单独审查过的引导流程。AL2023 不支持 `--containerd-source docker`；请使用其支持的发行版来源，或自行管理 containerd。

### VMware 上的 Bottlerocket（参考）

对于 EKS Hybrid Nodes，请在 x86_64 上使用受支持的 VMware 变体 >=1.37.0。Bottlerocket 设置和引导容器用于配置操作系统/身份验证；govc 是 VMware VM 管理 CLI，不是 TOML 设置解析器。有关版本化设置、私密用户数据和凭据配置，请参阅[完整引导指南](./04-node-bootstrap.md)。

## 凭据提供程序配置比较

### 基于 nodeadm 的配置（Ubuntu/RHEL/AL2023）

以下是互为替代的 SSM 和 IAM Roles Anywhere 方案。请将每个占位符替换为经批准的集群/区域/身份信息，使用 root 所有权和 0600 模式保护 NodeConfig，并妥善保护每台主机的私钥。不要将已注册的 SSM 状态或共用主机密钥放入克隆的黄金映像。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: "REPLACE_WITH_PRIVATE_ACTIVATION_CODE"
      activationId: "REPLACE_WITH_PRIVATE_ACTIVATION_ID"
```

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_WITH_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_WITH_ID
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

nodeadm 会验证配置，并通过已配置的 AWS 身份获取所需的集群元数据。加入集群前，请核实实际的 API 可达性、EKS 访问条目、信任/权限和证书路径；仅解析 YAML 并不能证明已获授权。

### 基于 Bottlerocket 的配置（VMware）

旧版 `[settings.hybrid.ssm]` 和 `[settings.hybrid.iam-roles-anywhere]` 配置块不是有效的 Bottlerocket 设置。请使用[节点引导](./04-node-bootstrap.md)中所述的受支持 Kubernetes 设置和有文档说明的 Hybrid 引导容器输入。Base64 用户数据只是编码，并非加密；请保护 VMware guestinfo 和预配日志。

### 凭据提供程序选择指南

| 情况 | 选择考量 |
| --- | --- |
| 没有托管 PKI | SSM Hybrid 激活可减少证书管理工作；仍需维护身份/激活生命周期 |
| 已有托管 PKI | IAM Roles Anywhere 可使用每台主机的 X.509 身份；需维护签发、信任、过期和吊销 |
| 没有公共互联网 | 两者都需要通过经批准的私有/代理路径访问所需的 AWS API；请核实端点支持情况 |
| 完全断连/DDIL | EKS Hybrid Nodes 不属于受支持的运行模式；IAM Roles Anywhere 仍会调用 AWS CreateSession |
| 自定义节点身份 | 请查看提供程序的命名和生命周期规则；不要假定 Node 名称是可解析的主机名 |

请参阅[私有连接](./03-airgap-setup.md)。“没有公共互联网”和“没有 AWS 连接”是不同的要求。

## 大规模预配自动化

### PXE 启动基础设施设置

```text
Approved host/firmware inventory
  → matching DHCP/HTTP/PXE boot configuration
  → verified signed loader and installer kernel/initrd
  → protected host-specific installation configuration
  → explicit approved disk / OS installation
  → unique host identity / separate Hybrid bootstrap
```

所示的 TFTP/PXELINUX 组合描述的是传统 BIOS。UEFI PXE 也可以使用 TFTP，但需要兼容 UEFI 的引导程序；请根据实际环境选择受支持的安全传输方式。ISO 校验和与签名信任是独立于 DHCP 可达性的事项。

### Ansible 自动化 Playbook

以下 playbook 是针对已准备好的主机执行的**只读预检**。如果组件/服务缺失，它会停止；它不会以 `/usr/bin/kubelet` 是否存在来证明版本符合要求。它不会安装二进制文件、部署机密模板，也不会反复运行 nodeadm init。

```yaml
# Read-only preflight; does not provision, install, or initialize hosts.
- name: Inspect approved Hybrid hosts
  hosts: hybrid_nodes
  become: true
  gather_facts: false
  serial: 1
  any_errors_fatal: true
  tasks:
  - name: Read OS release
    ansible.builtin.command:
      argv: [cat, /etc/os-release]
    changed_when: false
  - name: Read architecture
    ansible.builtin.command:
      argv: [uname, -m]
    changed_when: false
  - name: Read installed nodeadm version
    ansible.builtin.command:
      argv: [/usr/local/bin/nodeadm, --version]
    changed_when: false
  - name: Check each required service
    ansible.builtin.command:
      argv: [systemctl, is-active, --quiet, "{{ item }}"]
    loop: [containerd, kubelet]
    changed_when: false
```

进行预配时，请使用相互独立且经批准的阶段：验证主机/磁盘清单 → 暂存经过验证的 OS/构件 → 提供私密的主机专属配置 → 执行[引导状态/身份流程](./04-node-bootstrap.md) → 验证实际 Node UID、版本、新 Lease 和工作负载健康状况。对于现有主机，请使用[生命周期管理](./07-node-lifecycle.md)。一次协调一台主机，出现故障时停止并保留部分状态证据；不要用 `creates: /usr/bin/kubelet` 隐藏变更。

## 迁移策略

### VMware → 裸金属 + EKS Hybrid Nodes

#### 阶段 1：构建并行基础设施

盘点工作负载、虚拟机、许可、网络/安全功能、存储和依赖项。准备并行的受支持目标环境、私有连接和回滚能力。过渡期间可以继续使用 VMware 上的 Bottlerocket，但它不会因此变成裸金属操作系统。

#### 阶段 2：将工作负载容器化

明确地将适合的工作负载容器化；有些 VM 可能需要继续保留为 VM。在迁移写入方之前，验证状态迁移、CSI 行为、权限、备份和恢复。AWS 托管数据库是一种架构选项，而不是自动转换方案。

#### 阶段 3：网络过渡

分别盘点 NSX-T 路由、overlay、防火墙、负载均衡和策略功能。Cilium BGP 可以交换路由；它不能作为 NSX-T 所有功能的等效替代品。在切换流量前，请验证地址分配、返回路径、入口/TLS、DNS、策略和现有连接。

#### 阶段 4：停用 VMware

只有在工作负载/数据验收完成、回滚窗口达成一致、备份恢复经过验证且许可/保留决策已落实后，才能停用 VMware。请核实实际要移除的基础设施；不要将取消许可或擦除磁盘设为流水线的自动收尾操作。

### OpenShift → EKS Hybrid Nodes

#### 概念映射

| OpenShift | 候选目标 | 需要解决的迁移差异 |
| --- | --- | --- |
| Route | Ingress / Gateway API controller | TLS 终止/重新加密/直通、权重、注释和策略均取决于 controller |
| SCC | PSS/Pod Security Admission 加上所需策略/默认值 | PSS 不会复现 SCC 的 UID/SELinux/组策略或变更行为 |
| OLM | 受支持的 OLM、Helm 或 EKS add-on/operator 交付方式 | OLM 可在 Kubernetes 上运行；CRD 转换、升级和依赖项不会自动迁移 |
| MachineSet | 主机生命周期/预配自动化 | nodeadm/Ansible 并非具备替换/扩缩语义的 Machine API controller |
| ImageStream | Registry 加映像晋级/触发器自动化 | ECR 可存储映像，但不能替代 ImageStream 导入/标记/变更触发器 |
| BuildConfig | 经审查的外部 CI/CD | 需要重建源代码、映像、凭据和构建策略行为 |
| DeploymentConfig | Deployment 加上所需的发布自动化 | 保留触发器、钩子、策略和回滚行为 |

#### 工作负载迁移检查清单

- 盘点所有 Route、策略/默认值、CRD/operator、映像触发器、构建和发布钩子。
- 使用有代表性的工作负载测试目标行为以及服务账户/RBAC 范围。
- 验证数据一致性、快照/恢复、DNS/TLS、网络控制和可观测性。
- 在停用源环境前演练切换和回滚。

#### 分阶段迁移

评估依赖项 → 试点一个具有代表性的非关键工作负载 → 按可控批次过渡 → 验收数据/运维并保留恢复证据 → 在商定的回滚期结束后停用源环境。

## 安装后验证

验证不得重新安装程序包或初始化已加入集群的主机。以下读取操作仅用于观察；进程处于活动状态或旧的 Ready 条件本身并不代表工作负载已验收。

```bash
# Read-only, on the host mapped to the intended Kubernetes Node:
set -euo pipefail
cat /etc/os-release
uname -m -r
/usr/local/bin/nodeadm --version
containerd --version
for service in containerd kubelet; do
  systemctl is-active --quiet "$service"
done
```

```bash
# From the approved administrative context; these are reads, not installation:
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved context}"
: "${NODE:?Set the actual registered Node name from inventory}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o yaml
```

使用 Node 到主机的清单映射，检查最新 Lease 和版本，确认 CNI/DNS/存储，并按照[引导](./04-node-bootstrap.md)和[生命周期](./07-node-lifecycle.md)指南执行经批准的工作负载检查。读取失败/状态未知均不能视为通过。

## 故障排除

| 问题 | 检查和范围明确的后续步骤 |
| --- | --- |
| 启动失败 | 固件模式、已签名引导程序、DHCP/HTTP/TFTP 设计、NIC 驱动程序和经批准的映像校验和 |
| Autoinstall/Kickstart 失败 | 安装程序日志/架构、目标磁盘、仓库/stage2 和主机专属配置；不要盲目重试破坏性分区操作 |
| Ubuntu 终止问题 | 实际的 AppArmor 信号拒绝证据、已修复的程序包/回移补丁以及按计划执行的必要重启 |
| RHEL containerd | 选择受支持的 docker/none 来源，核实实际运行时和 SELinux 策略 |
| nodeadm/身份验证 | 核实当前 nodeadm、受保护的配置、AWS 私有连接、身份和信任；避免盲目重新注册 |

## 验证范围和参考资料

本地证据包括 50 项架构/契约/命令替身检查、12 项构件/主机/API-read 子进程案例、pykickstart 3.78 RHEL9 解析器，以及 10 项 Decimal 定价断言。规范的 Autoinstall 架构允许额外的根键，不能替代所选安装程序的验证。未执行真实的操作系统安装、磁盘擦除、启动/登录、Packer 映像构建、Ansible SSH 操作、nodeadm 执行、VM 创建或 AWS/Kubernetes 调用。临时测试目标和可执行文件均为模拟对象。

- [AWS Hybrid OS 要求](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [AWS Hybrid nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS EKS 定价](https://aws.amazon.com/eks/pricing/)
- [AWS Packer 示例](https://github.com/aws/eks-hybrid/tree/main/example/packer)
- [Canonical Autoinstall 参考](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [RHEL 9 Kickstart 参考](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer)
- [Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)
- [aa-remove-unknown 手册](https://manpages.ubuntu.com/manpages/noble/man8/aa-remove-unknown.8.html)
- [EC2 之外的 AL2023](https://docs.aws.amazon.com/linux/al2023/ug/outside-ec2.html)
- [Operator Lifecycle Manager](https://olm.operatorframework.io/docs/)
- [OpenShift SCC API](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_apis/securitycontextconstraints-security-openshift-io-v1)


---

< [上一章：运维](./08-operations.md) | [目录](./README.md) | [下一章：混合节点网关](./10-hybrid-nodes-gateway.md) >
