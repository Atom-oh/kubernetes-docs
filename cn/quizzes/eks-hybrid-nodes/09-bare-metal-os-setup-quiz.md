# 裸金属服务器操作系统安装与迁移测验

> **最后更新**：2026 年 9 月 13 日

> **相关文档**：[指南](../../eks-hybrid-nodes/09-bare-metal-os-setup.md)

## 选择题

<span id="_1-what-is-a-key-benefit-of-running-eks-hybrid-nodes-on-bare-metal-servers"></span>

### 1. 评估在裸金属上运行 Hybrid Nodes 的理由可能是什么？

- A) 自动将每台虚拟机转换为容器
- B) 有可能移除 hypervisor 层，但须结合总成本和工作负载需求进行评估
- C) 无需连接 AWS 即可运行
- D) 自动取消所有软件许可证

<details>
<summary>显示答案</summary>

**答案：B）有可能移除 hypervisor 层，但须结合总成本和工作负载需求进行评估**

**说明：**

移除 hypervisor 可能改变许可成本和执行开销，但不能保证总成本更低或性能更好。容器化、数据迁移、高可用性、支持和合同义务都需要单独处理。不要把指南中保留的、未经核实的历史价格估算当成节省金额。

</details>

<span id="_2-what-are-the-essential-components-required-for-pxe-boot-infrastructure"></span>

### 2. 传统 PXE 启动设计通常会用到哪些组件？

- A) 只有 DNS 和 NFS
- B) DHCP/ProxyDHCP 启动信息和 TFTP 启动服务器
- C) FTP 和 SMTP
- D) 只有 LDAP 和 Kerberos

<details>
<summary>显示答案</summary>

**答案：B）DHCP/ProxyDHCP 启动信息和 TFTP 启动服务器**

**说明：**

传统 PXE 通常使用 DHCP 启动信息和 TFTP。HTTP 可用于传送安装程序内容；UEFI HTTP/iPXE 设计可能采用不同路径。pxelinux.0 并不是通用的 UEFI 引导加载程序。应验证固件/加载程序链并隔离置备流程；不得在共享的未认证服务器上暴露私有激活码和密钥。

</details>

<span id="_3-which-correctly-pairs-ubuntu-s-automated-installation-method-with-rhel-s-automated-installation-method"></span>

### 3. 哪组配对正确描述了自动化操作系统安装方式？

- A) Ubuntu：Kickstart；RHEL：Autoinstall
- B) Ubuntu Server：Subiquity Autoinstall YAML；RHEL：Kickstart
- C) Ubuntu：govc；RHEL：TOML
- D) 两者都必须在安装程序中下载未经验证的最新 nodeadm

<details>
<summary>显示答案</summary>

**答案：B）Ubuntu Server：Subiquity Autoinstall YAML；RHEL：Kickstart**

**说明：**

Cloud-init 可以传递 Ubuntu 的 Autoinstall 配置；RHEL 使用 Kickstart。应验证所选安装程序版本以及主机专属的存储和网络设置。YAML 解析器或 ksvalidator 并不能证明待清除的磁盘选对了，也不能证明安装后的主机能够完成身份验证。

</details>

<span id="_4-according-to-the-os-infrastructure-support-matrix-what-is-bottlerocket-s-supported-environment"></span>

### 4. 根据审阅过的 AWS 指南，EKS Hybrid Nodes 支持在哪种环境中部署 Bottlerocket？

- A) 任何裸金属变体
- B) 所有 hypervisor 和架构
- C) x86_64 上受支持的 VMware 变体，版本不低于 1.37.0
- D) 仅限 EC2

<details>
<summary>显示答案</summary>

**答案：C）x86_64 上受支持的 VMware 变体，版本不低于 1.37.0**

**说明：**

这是 EKS Hybrid 的支持边界，并不代表所有 Bottlerocket 产品变体都受支持。Hybrid 裸金属应评估受支持的 Ubuntu/RHEL 主机。AL2023 也可作为本地虚拟化来宾系统选项，但不是受支持的通用裸金属路径。还应单独检查 Kubernetes 变体的可用性和当前生命周期要求。

</details>

<span id="_5-what-configuration-tool-and-format-does-bottlerocket-use-differently-from-other-operating-systems"></span>

### 5. 如何区分 Bottlerocket 设置与 govc 的用途？

- A) govc 是 Bottlerocket 的 TOML 解析器
- B) Bottlerocket 与 Ubuntu 使用相同的 nodeadm YAML
- C) Bottlerocket 使用设置/引导输入；govc 管理 VMware 虚拟机生命周期并传递 user-data
- D) settings.hybrid.ssm 是受支持的标准设置命名空间

<details>
<summary>显示答案</summary>

**答案：C）Bottlerocket 使用设置/引导输入；govc 管理 VMware 虚拟机生命周期并传递 user-data**

**说明：**

应遵循指南中与版本对应的 Bottlerocket 设置/引导流程。旧的 settings.hybrid.* 示例无效。govc 可以克隆和配置虚拟机、控制其开关机，但不是操作系统设置解析器。应保护 guestinfo 和 user-data；Base64 编码并不等于加密凭据。

</details>

<span id="_6-when-selecting-a-credential-provider-for-an-environment-without-pki-infrastructure-and-with-internet-connectivity-which-option-is-recommended"></span>

### 6. 关于 Hybrid 凭据提供程序和连接方式，哪项说法正确？

- A) IAM Roles Anywhere 无需 AWS 连接即可无限期运行
- B) 两种提供程序都需要访问各自所需的 AWS API；使用私有连接可以避免访问公共互联网
- C) SSM 始终要求直接连接公共互联网
- D) Kubernetes ServiceAccount 可以替代主机的 Hybrid 凭据提供程序

<details>
<summary>显示答案</summary>

**答案：B）两种提供程序都需要访问各自所需的 AWS API；使用私有连接可以避免访问公共互联网**

**说明：**

在没有托管 PKI 的情况下，SSM 可以减少证书管理工作。IAM Roles Anywhere 使用 X.509 身份，但仍会调用 AWS CreateSession 以获取临时凭据。两种设计都需要各自受支持的 API/私有端点路径、身份生命周期管理和 EKS 授权。完全断网/DDIL 环境并非受支持的 EKS Hybrid 运行模式。

</details>

<span id="_7-what-option-must-be-used-when-installing-containerd-with-nodeadm-on-rhel"></span>

### 7. nodeadm 在 RHEL 上安装 containerd 时，文档列出了哪些来源选项？

- A) 只支持 distro
- B) 使用 docker；如果 containerd 已另行安装并维护，也可以不指定来源
- C) 无论操作系统为何都使用 eks
- D) 使用 latest，无需检查兼容性

<details>
<summary>显示答案</summary>

**答案：B）使用 docker；如果 containerd 已另行安装并维护，也可以不指定来源**

**说明：**

RHEL 不支持 nodeadm 的 distro 来源。docker 会选择由 Docker 分发且兼容的 containerd 软件包；none 会跳过安装，因此必须在 init 之前另行管理好运行时。说所有 RHEL 安装都必须使用 docker 会遗漏这一受支持的替代方案。AL2023 的来源限制不同。

</details>

<span id="_8-what-is-the-correct-order-of-phases-when-migrating-from-vmware-to-bare-metal-eks-hybrid-nodes"></span>

### 8. 哪种迁移顺序能够保留恢复路径？

- A) 先停用源环境
- B) 试点之前先取消许可证
- C) 准备并行目标环境，迁移并测试工作负载和网络，验收数据/运维，再于回滚窗口结束后停用源环境
- D) 将虚拟机磁盘复制到容器后立即擦除源环境

<details>
<summary>显示答案</summary>

**答案：C）准备并行目标环境，迁移并测试工作负载和网络，验收数据/运维，再于回滚窗口结束后停用源环境**

**说明：**

盘点依赖关系，规划备份和恢复，并保留回滚容量。切换流量前，应测试数据一致性、TLS/DNS、访问策略和实际工作负载行为。仅将虚拟机容器化或安装 CSI 驱动都不会迁移状态。停用环境和变更许可证都需要遵循商定的验收/保留决策。

</details>

<span id="_9-what-does-openshift-s-route-concept-map-to-in-eks-hybrid-nodes"></span>

### 9. 如何迁移 OpenShift Route？

- A) 直接改名为 Service，无需其他改动
- B) 设计到 Ingress/Gateway API 的映射，并验证所选控制器的 TLS 和路由行为
- C) 将每个 Route 替换为 NetworkPolicy
- D) 将字段原样复制到 Gateway

<details>
<summary>显示答案</summary>

**答案：B）设计到 Ingress/Gateway API 的映射，并验证所选控制器的 TLS 和路由行为**

**说明：**

Ingress/Gateway API 是候选路由接口，并非自动等价的替代品。应按需保留 termination/reencrypt/passthrough、权重和注解。SCC 与 PSS/PSA、OLM 交付、ImageStream 触发器和 DeploymentConfig hook 也同样需要谨慎处理：ECR/Helm/Deployment 不会自动复现 OpenShift 的所有行为。

</details>

<span id="_10-what-is-the-solution-when-pods-won-t-terminate-on-ubuntu-24-04-due-to-containerd-issues"></span>

### 10. 对于文档所述 Ubuntu 24.04 AppArmor/container 终止问题，哪种处理方式合适？

- A) 删除每台主机上所有未知的 AppArmor 配置文件
- B) 核实实际的软件包/配置文件问题，应用受支持的修复；如果该变更要求重启，则安排计划内重启
- C) 禁用所有安全机制
- D) 假定安装恰好是 containerd 1.7.19 的版本就能修复所有卡住的 Pod

<details>
<summary>显示答案</summary>

**答案：B）核实实际的软件包/配置文件问题，应用受支持的修复；如果该变更要求重启，则安排计划内重启**

**说明：**

Bug 2065423 已发布修复，并说明受影响的软件包/配置文件变更后需要重启。应检查供应商软件包及回补状态，并查看实际的信号拒绝日志。aa-remove-unknown 会移除已加载、但在 /etc/apparmor.d 中不存在的配置文件；它不是定向编辑工具。应受控地执行排空、重启和工作负载检查，不要把每次 AppArmor 变更都当成必然需要全局重启的规则。

</details>

### 11. 哪种成本模型符合审阅过的 EKS Hybrid 定价？

- A) 统一按每 vCPU 小时 0.01 美元计费，并涵盖所有服务
- B) 按已报告的 vCPU 小时采用每月边际阶梯定价，另计集群和其他费用
- C) 只对正在运行的 Pod 请求的 CPU 计费
- D) 工作负载空闲时不收取节点费用

<details>
<summary>显示答案</summary>

**答案：B）按已报告的 vCPU 小时采用每月边际阶梯定价，另计集群和其他费用**

**说明：**

每月前 576,000 个 vCPU 小时按每 vCPU 小时 0.020 美元计费，之后采用公布的边际阶梯价格。汇总范围是账户内的区域级范围，或 Organizations 合并账单范围。还应计入已报告的 vCPU 数、月份长度、集群支持层级和其他服务。旧的每节点每年 2,803.20 美元结果是保留的、未经核实的过时假设，并非当前总拥有成本（TCO）。

</details>

### 12. 选择 Cilium BGP 来替代 NSX-T 功能意味着什么？

- A) 会自动复现 NSX-T 的所有功能
- B) BGP 提供路由交换；overlay、防火墙、负载均衡和策略需求需分别映射
- C) 无需测试返回路径路由
- D) 所有现有会话都会原样保留

<details>
<summary>显示答案</summary>

**答案：B）BGP 提供路由交换；overlay、防火墙、负载均衡和策略需求需分别映射**

**说明：**

BGP 通告并不能提供完整的 NSX 平台能力。应分别盘点路由、overlay、安全和负载均衡行为，再测试目标地址、返回路径、TLS/DNS 以及现有和新建连接。选择受支持的混合 CNI 模式并保留回滚方案；这里并未声称存在通用的一对一替代方案。

</details>
