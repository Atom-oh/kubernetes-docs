# 裸机服务器 OS 安装和迁移指南

< [上一页：运维和维护](./08-operations.md) | [目录](./README.md) | [下一页：Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **支持的版本**: EKS 1.31+, nodeadm 0.1+
> **最后更新**: February 23, 2026

本文档介绍在裸机服务器上部署 EKS Hybrid Nodes 的 OS 安装方法，以及从 VMware/OpenShift 迁移的策略。

## 概述

### 为什么选择裸机

在裸机服务器上运行 EKS Hybrid Nodes 可提供以下优势：

1. **节省 VMware 许可证成本**：Broadcom 收购 VMware 后，转向订阅模式显著增加了许可证成本。
2. **降低 OpenShift 订阅成本**：消除按节点收取的 Red Hat OpenShift 订阅费用。
3. **消除 Hypervisor 开销**：无需虚拟化层即可直接运行工作负载，从而优化性能。
4. **简化许可证管理**：降低复杂许可证协议和审计合规的负担。

### OS 基础设施支持矩阵

| OS | 裸机 | VMware | 凭证 | 配置工具 |
|----|-----------|--------|-------------|-------------|
| Ubuntu 22.04/24.04 LTS | O | O | SSM / IAM RA | nodeadm (YAML) |
| RHEL 8/9 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Amazon Linux 2023 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Bottlerocket v1.37.0+ | X | O（仅 VMware） | SSM / IAM RA | govc (TOML) |

> **注意**：Bottlerocket 仅在 VMware 环境中受支持。对于裸机服务器，请使用 Ubuntu、RHEL 或 Amazon Linux 2023。

## 成本比较分析

### 许可证/订阅成本比较

#### VMware vSphere
Broadcom 收购后，VMware 从永久许可证转向订阅模式：
- Enterprise Plus 许可证：每个 CPU socket 每年约 $4,500-8,500
- vSAN 和 NSX-T 等附加组件会产生额外成本

#### OpenShift
基于 Red Hat 订阅：
- 每个节点每年约 $2,500-5,000（基于 core 的订阅）
- 包含高级支持

#### EKS Hybrid Nodes
- 每 vCPU 每小时 $0.01（因区域而异）
- 无需额外许可证

### 按规模进行年度成本比较（32 vCPU 服务器）

| 规模 | VMware vSphere（年度） | OpenShift（年度） | EKS Hybrid Nodes（年度） |
|-------|------------------------|-------------------|--------------------------|
| 10 nodes | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 nodes | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 nodes | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

> **计算**：EKS Hybrid Nodes = 32 vCPU × $0.01/hour × 8,760 hours = $2,803.20/node/year
>
> **注意**：以上成本为估算值。实际成本可能因合同条款、区域和折扣而异。

### TCO（总拥有成本）考虑因素

除许可证/订阅成本外，还应考虑以下因素：
- 运维人员培训成本
- 许可证管理和审计合规开销
- 技术支持和咨询成本
- 迁移成本（一次性）

## 按 OS 划分的裸机安装

### 前提条件

#### BIOS/UEFI 设置
- 配置 PXE 启动优先级
- 禁用 Secure Boot 或使用已签名的 bootloader
- 为 containerd 启用虚拟化扩展（VT-x/AMD-V）

#### 网络基础设施
- DHCP Server：提供 IP 地址和 PXE 启动信息
- TFTP Server：提供 bootloader 和 kernel 镜像
- HTTP Server：托管 OS 安装镜像和配置文件

#### AWS Packer 模板
为裸机创建镜像时，设置 `CREDENTIAL_PROVIDER` 环境变量：

```bash
# Create Qcow2 or Raw format images
export CREDENTIAL_PROVIDER=ssm  # or iam-ra

packer build \
  -var "credential_provider=${CREDENTIAL_PROVIDER}" \
  -var "output_format=raw" \
  bare-metal-template.pkr.hcl
```

### Ubuntu LTS (22.04/24.04)

Ubuntu 使用 Autoinstall（基于 cloud-init）进行 PXE 自动化安装。

#### Autoinstall 配置示例

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  network:
    ethernets:
      ens0:
        dhcp4: true
    version: 2
  storage:
    layout:
      name: lvm
  identity:
    hostname: hybrid-node
    username: ubuntu
    password: "$6$rounds=4096$..."  # Encrypted password
  ssh:
    install-server: true
    authorized-keys:
      - ssh-rsa AAAA...  # SSH public key
  packages:
    - curl
    - jq
    - open-iscsi
    - nfs-common
  late-commands:
    - curtin in-target -- bash -c 'curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm && chmod +x nodeadm && mv nodeadm /usr/local/bin/'
```

#### Ubuntu 24.04 特定说明

Ubuntu 24.04 需要 containerd v1.7.19 或更高版本，否则需要更改 AppArmor profile（Ubuntu bug #2065423）：

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

> **重要**：更改 AppArmor 后需要重启。如果不重启，Pods 可能无法正常终止。

### RHEL 9

RHEL 使用 Kickstart 进行 PXE 自动化安装。

#### Kickstart 配置示例

```bash
# ks.cfg
lang en_US.UTF-8
keyboard us
timezone America/New_York --utc
rootpw --iscrypted $6$rounds=4096$...
network --bootproto=dhcp --device=ens0 --activate
autopart --type=lvm
clearpart --all --initlabel

%packages
@core
curl
jq
container-tools
%end

%post
# Install nodeadm
curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm && mv nodeadm /usr/local/bin/

# SELinux configuration (if needed)
semanage permissive -a container_t
%end
```

#### RHEL containerd 安装说明

在 RHEL 上，必须使用 `--containerd-source docker` 选项。不支持发行版默认源：

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# Incorrect installation method (will fail)
# sudo nodeadm install 1.31 --credential-provider ssm
```

#### 大规模环境：Satellite/Foreman 集成

对于大规模 RHEL 部署，请使用 Red Hat Satellite 或 Foreman 实现：
- 集中化 Kickstart 模板管理
- Package repository 镜像
- Provisioning 工作流自动化

### Amazon Linux 2023

Amazon Linux 2023 使用基于 cloud-init 的配置。

```yaml
#cloud-config
hostname: hybrid-node
users:
  - name: ec2-user
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAA...

packages:
  - curl
  - jq

runcmd:
  - curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
  - chmod +x nodeadm && mv nodeadm /usr/local/bin/
```

> **AWS Support 注意事项**：在 EC2 之外（裸机上）运行 Amazon Linux 2023 时，AWS Support Plans 不适用。仅提供社区支持。

### VMware 上的 Bottlerocket（参考）

Bottlerocket 仅在 VMware 环境中受支持（v1.37.0+，仅 x86_64）。

- 使用 `settings.toml` 而不是 nodeadm 进行配置
- govc 部署工作流：克隆模板 → 注入 user-data → 启动

有关详细的 Bottlerocket TOML 配置，请参阅 [04-node-bootstrap.md](./04-node-bootstrap.md)。

## Credential Provider 配置比较

### 基于 nodeadm 的配置（Ubuntu/RHEL/AL2023）

```yaml
# nodeconfig.yaml - SSM method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
```

```yaml
# nodeconfig.yaml - IAM Roles Anywhere method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:111122223333:trust-anchor/...
      profileArn: arn:aws:rolesanywhere:us-west-2:111122223333:profile/...
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

### 基于 Bottlerocket 的配置（VMware）

```toml
# settings.toml - SSM method
[settings.hybrid.ssm]
activation-code = "<activation-code>"
activation-id = "<activation-id>"

[settings.kubernetes]
cluster-name = "my-cluster"
```

```toml
# settings.toml - IAM Roles Anywhere method
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "arn:aws:rolesanywhere:..."
profile-arn = "arn:aws:rolesanywhere:..."
role-arn = "arn:aws:iam::..."
certificate-path = "/etc/eks/pki/node.crt"
private-key-path = "/etc/eks/pki/node.key"
```

### Credential Provider 选择指南

| 条件 | 推荐 Provider |
|-----------|---------------------|
| 没有 PKI 基础设施 | SSM |
| 现有 PKI 基础设施 | IAM Roles Anywhere |
| 需要自定义节点名称 | IAM Roles Anywhere |
| Air-gapped 环境 | IAM Roles Anywhere |
| 设置简单，可访问互联网 | SSM |

## 大规模 Provisioning 自动化

### PXE Boot 基础设施设置

```
┌─────────────────────────────────────────────────────────┐
│                    PXE Boot Server                       │
├─────────────────────────────────────────────────────────┤
│  DHCP Server                                            │
│  ├── IP address allocation                              │
│  ├── next-server: TFTP server address                   │
│  └── filename: pxelinux.0                              │
├─────────────────────────────────────────────────────────┤
│  TFTP Server                                            │
│  ├── pxelinux.0 (bootloader)                           │
│  ├── vmlinuz (kernel)                                   │
│  └── initrd.img (initial RAM disk)                     │
├─────────────────────────────────────────────────────────┤
│  HTTP Server                                            │
│  ├── OS installation images                             │
│  ├── Autoinstall/Kickstart config files                │
│  └── nodeadm binary                                     │
└─────────────────────────────────────────────────────────┘
```

### Ansible 自动化 Playbook

```yaml
# provision-hybrid-nodes.yaml
---
- hosts: hybrid_nodes
  become: true
  vars:
    k8s_version: "1.31"
    cred_provider: "ssm"
    cluster_name: "my-cluster"
    region: "us-west-2"

  tasks:
    - name: Download nodeadm
      get_url:
        url: https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
        dest: /usr/local/bin/nodeadm
        mode: '0755'

    - name: Install EKS components
      command: >
        nodeadm install {{ k8s_version }}
        --credential-provider {{ cred_provider }}
        {% if ansible_distribution == 'RedHat' %}--containerd-source docker{% endif %}
      args:
        creates: /usr/bin/kubelet

    - name: Deploy node configuration
      template:
        src: nodeconfig.yaml.j2
        dest: /etc/eks/nodeconfig.yaml
        mode: '0600'

    - name: Initialize node
      command: nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
      register: init_result
      changed_when: init_result.rc == 0
```

有关详细的 fleet 管理信息，请参阅 [07-node-lifecycle.md](./07-node-lifecycle.md)。

## 迁移策略

### VMware → 裸机 + EKS Hybrid Nodes

#### 阶段 1：构建并行基础设施
- 在 VMware 旁部署 EKS cluster 和 hybrid node 基础设施
- 配置网络连接（Direct Connect/VPN）
- 迁移期间，VMware 上的 Bottlerocket 可以共存

#### 阶段 2：将工作负载容器化
- 将基于 VM 的工作负载迁移到 containers
- 在迁移 stateful workloads 之前配置 CSI drivers
- 考虑将数据库迁移到 AWS managed services

#### 阶段 3：网络转换
- 从 NSX-T 转换到 Cilium BGP
- 迁移 load balancer 和 ingress 配置
- 更新 DNS records

#### 阶段 4：停用 VMware
- 验证所有工作负载都已迁移
- 终止 VMware 许可证
- 回收或停用硬件

### OpenShift → EKS Hybrid Nodes

#### 概念映射

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC (Security Context Constraints) | PSS (Pod Security Standards) |
| OLM (Operator Lifecycle Manager) | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD (CodeBuild, GitHub Actions) |
| DeploymentConfig | Deployment (standard Kubernetes) |

#### 工作负载迁移检查清单

- [ ] 将 Routes 转换为 Ingress 或 Gateway API
- [ ] 将 SCCs 映射到用于 Pod security 配置的 PSS
- [ ] 用 Helm Charts 或 EKS Add-ons 替换由 OLM 管理的 Operators
- [ ] 将 ImageStream 引用更改为 ECR image URLs
- [ ] 将 BuildConfigs 重新配置为 GitHub Actions/CodeBuild pipelines
- [ ] 将 DeploymentConfigs 转换为标准 Deployments
- [ ] 审查 service accounts 和 RBAC 设置

#### 分阶段迁移

1. **评估阶段**：创建当前 OpenShift 工作负载清单
2. **试点阶段**：将非关键工作负载迁移到 EKS Hybrid Nodes
3. **转换阶段**：按顺序迁移关键工作负载
4. **完成阶段**：停用 OpenShift cluster

## 安装后验证

```bash
#!/bin/bash
# verify-bare-metal.sh

echo "=== OS Level Verification ==="
# Check OS version
cat /etc/os-release

# Check kernel version
uname -r

# Check containerd status
systemctl status containerd

# Check nodeadm version
nodeadm version

echo "=== EKS Integration Verification ==="
# Install and initialize
sudo nodeadm install 1.31 --credential-provider ssm
sudo nodeadm init --config-source file://nodeconfig.yaml

# Verify node from cluster
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node <node-name> | grep -A 5 "Labels:"
```

有关详细的 bootstrap 过程信息，请参阅 [04-node-bootstrap.md](./04-node-bootstrap.md)。

## 故障排除

| 问题 | 症状 | 解决方案 |
|-------|---------|----------|
| PXE boot 失败 | Node 未从网络启动 | 检查 DHCP/TFTP config、BIOS boot order、network cable |
| Autoinstall timeout | Ubuntu 安装挂起 | 验证 cloud-init YAML 语法，检查 HTTP server 可访问性 |
| Kickstart error | RHEL 安装失败 | 验证 ks.cfg 语法，检查 media 可访问性 |
| Ubuntu 24.04 containerd | Pods 无法终止 | 将 containerd 更新到 v1.7.19+，为 AppArmor 重启 |
| RHEL containerd | 安装失败 | 使用 `--containerd-source docker` flag |
| nodeadm init 失败 | Connection timeout | 验证 VPN/DX connectivity，检查 firewall ports |

---

< [上一页：运维和维护](./08-operations.md) | [目录](./README.md) | [下一页：Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
