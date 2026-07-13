# 裸金属服务器 OS 安装与迁移测验

> **相关文档**: [裸金属服务器 OS 安装与迁移指南](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 选择题

### 1. 在裸金属服务器上运行 EKS Hybrid Nodes 的关键优势是什么？

A. 比 AWS EC2 实例更快的网络速度
B. 节省 VMware 许可成本并消除 hypervisor 开销
C. 能够使用 Bottlerocket OS
D. AWS Support Plans 覆盖范围

<details>
<summary>显示答案</summary>

**答案: B) 节省 VMware 许可成本并消除 hypervisor 开销**

**解释:**
在裸金属服务器上运行 EKS Hybrid Nodes 可以节省 VMware 许可成本（在 Broadcom 收购后转为订阅模式）以及 OpenShift 订阅费用。此外，消除 hypervisor 层可以优化性能。

</details>

### 2. PXE boot 基础设施所需的基本组件是什么？

A. DNS server 和 NFS server
B. DHCP server 和 TFTP server
C. FTP server 和 SMTP server
D. LDAP server 和 Kerberos server

<details>
<summary>显示答案</summary>

**答案: B) DHCP server 和 TFTP server**

**解释:**
PXE boot 基础设施的核心组件包括：
- DHCP Server: 提供 IP 地址分配和 PXE boot 信息（next-server、filename）
- TFTP Server: 提供 bootloader (pxelinux.0)、kernel (vmlinuz) 和初始 RAM disk (initrd.img)
- HTTP Server（可选）: 托管 OS 安装镜像和配置文件

</details>

### 3. 哪一项正确匹配了 Ubuntu 的自动化安装方法和 RHEL 的自动化安装方法？

A. Ubuntu: Kickstart, RHEL: Autoinstall
B. Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart
C. Ubuntu: Preseed, RHEL: Anaconda
D. Ubuntu: YAML, RHEL: JSON

<details>
<summary>显示答案</summary>

**答案: B) Ubuntu: Autoinstall (cloud-init), RHEL: Kickstart**

**解释:**
- Ubuntu 使用 Autoinstall（基于 cloud-init）进行 PXE 自动化安装。它使用 YAML 格式配置文件。
- RHEL 使用 Kickstart 进行 PXE 自动化安装。配置通过 ks.cfg 文件完成。

</details>

### 4. 根据 OS 基础设施支持矩阵，Bottlerocket 支持的环境是什么？

A. 同时支持裸金属和 VMware
B. 仅裸金属
C. 仅 VMware
D. 仅 AWS EC2

<details>
<summary>显示答案</summary>

**答案: C) 仅 VMware**

**解释:**
对于 EKS Hybrid Nodes，Bottlerocket 仅在 VMware 环境中受支持（v1.37.0+，仅 x86_64）。对于裸金属服务器，必须使用 Ubuntu、RHEL 或 Amazon Linux 2023。Bottlerocket 不使用 nodeadm；它使用 settings.toml 进行配置。

</details>

### 5. Bottlerocket 使用的配置工具和格式与其他操作系统有何不同？

A. nodeadm (YAML)
B. ansible (INI)
C. govc (TOML)
D. terraform (HCL)

<details>
<summary>显示答案</summary>

**答案: C) govc (TOML)**

**解释:**
Bottlerocket 不使用 nodeadm；而是使用 settings.toml 文件进行配置。govc 部署工作流是：克隆模板 → 注入 user-data → 开机。相比之下，Ubuntu、RHEL 和 Amazon Linux 2023 使用 nodeadm (YAML)。

</details>

### 6. 在没有 PKI 基础设施但具有互联网连接的环境中选择 credential provider 时，推荐哪个选项？

A. IAM Roles Anywhere
B. SSM Hybrid Activations
C. Kubernetes Service Account
D. OIDC Provider

<details>
<summary>显示答案</summary>

**答案: B) SSM Hybrid Activations**

**解释:**
Credential provider 选择指南：
- 无 PKI 基础设施，可访问互联网：SSM
- 已有 PKI 基础设施：IAM Roles Anywhere
- Air-gapped 环境：IAM Roles Anywhere
- 需要自定义 node 名称：IAM Roles Anywhere

由于设置简单且不需要证书，SSM 推荐用于大多数环境。

</details>

### 7. 在 RHEL 上使用 nodeadm 安装 containerd 时必须使用哪个选项？

A. `--containerd-source distro`
B. `--containerd-source docker`
C. `--containerd-source eks`
D. `--containerd-version latest`

<details>
<summary>显示答案</summary>

**答案: B) `--containerd-source docker`**

**解释:**
在 RHEL 上，必须使用 `--containerd-source docker` 选项。发行版默认源（distro）在 RHEL 上不受支持：

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker
```

如果没有此选项，安装将失败。

</details>

### 8. 从 VMware 迁移到裸金属 + EKS Hybrid Nodes 时，各阶段的正确顺序是什么？

A. 停用 VMware → 容器化 workloads → 网络转换 → 构建并行基础设施
B. 容器化 workloads → 构建并行基础设施 → 停用 VMware → 网络转换
C. 构建并行基础设施 → 容器化 workloads → 网络转换 → 停用 VMware
D. 网络转换 → 构建并行基础设施 → 容器化 workloads → 停用 VMware

<details>
<summary>显示答案</summary>

**答案: C) 构建并行基础设施 → 容器化 workloads → 网络转换 → 停用 VMware**

**解释:**
VMware → 裸金属 + EKS Hybrid Nodes 迁移阶段：
1. 第 1 阶段：构建并行基础设施（在 VMware 旁边部署 EKS cluster 和 hybrid node 基础设施）
2. 第 2 阶段：容器化 Workloads（将基于 VM 的 workloads 迁移到 containers）
3. 第 3 阶段：网络转换（从 NSX-T 转换到 Cilium BGP）
4. 第 4 阶段：停用 VMware（在验证所有 workloads 已迁移后）

</details>

### 9. OpenShift 的 Route 概念在 EKS Hybrid Nodes 中映射为什么？

A. Service
B. Ingress / Gateway API
C. NetworkPolicy
D. Endpoint

<details>
<summary>显示答案</summary>

**答案: B) Ingress / Gateway API**

**解释:**
从 OpenShift 迁移到 EKS Hybrid Nodes 时的概念映射：

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC | PSS (Pod Security Standards) |
| OLM | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD |
| DeploymentConfig | Deployment |

</details>

### 10. 当 Ubuntu 24.04 上由于 containerd 问题导致 Pods 无法终止时，解决方案是什么？

A. 禁用 SELinux 并重启
B. 将 containerd 更新到 v1.7.19+，或修改 AppArmor profile 并重启
C. 将 container runtime 切换到 Docker
D. 降级到 cgroup v1

<details>
<summary>显示答案</summary>

**答案: B) 将 containerd 更新到 v1.7.19+，或修改 AppArmor profile 并重启**

**解释:**
Ubuntu 24.04 需要 containerd v1.7.19 或更高版本，或者需要更改 AppArmor profile（Ubuntu bug #2065423）：

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

如果不重启，Pods 可能无法正常终止。

</details>
