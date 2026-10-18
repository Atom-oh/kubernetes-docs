# EKS Hybrid Nodes 前提条件测验

> **相关文档**：[前提条件](../../eks-hybrid-nodes/01-prerequisites.md)
> **最后更新**：2026年9月12日

## 选择题

### 1. 哪种情况不属于将机器注册为 EKS Hybrid Node 的受支持理由？

- A) 使用兼容的本地 GPU 服务器
- B) 让应用处理过程靠近本地数据集
- C) 将普通 EC2/云端机器注册为 Hybrid Node 基础设施
- D) 连接可靠、且已测试恢复流程的边缘工作负载

<details>
<summary>显示答案</summary>

**答案：C) 将普通 EC2/云端机器注册为 Hybrid Node 基础设施**

**解释：**
AWS 支持在客户自行运维的本地或边缘物理主机和虚拟主机上部署 Hybrid Node，而不是在云基础设施上部署。即使把 EC2 注册为 Hybrid Node，仍会产生 Hybrid Node 费用。云端节点应使用常规 AWS 计算类型。Hybrid Node 需要可靠的网络连接；仅设置 placement label 并不能证明满足法规合规要求，也不能证明节点可离线运行。

</details>

### 2. 以下哪项操作系统说明符合当前 AWS Hybrid 集成兼容性矩阵？

- A) 仅支持 Windows Server
- B) Ubuntu 20.04/22.04/24.04、RHEL 8/9、虚拟化环境中的 AL2023，以及受支持的 Bottlerocket VMware 变体
- C) 支持任意 macOS 版本
- D) 任意 Linux 镜像都会自动获得 AWS 操作系统支持

<details>
<summary>显示答案</summary>

**答案：B) Ubuntu 20.04/22.04/24.04、RHEL 8/9、虚拟化环境中的 AL2023，以及受支持的 Bottlerocket VMware 变体**

**解释：**
请同时核对供应商的安全维护状态、CPU 架构以及所选 CNI 和内核。Bottlerocket VMware v1.37.0 及更高版本仅支持 x86_64，并使用其专用的引导流程。AL2023 适用于本地虚拟化环境；AWS 对其在 EC2 以外环境中的使用不提供操作系统支持。ARM 上的 EKS kube-proxy 1.31 及更高版本要求 ARMv8.2+crypto；笼统的内核 5.4 规则或 CPU 型号名称都不足以完成兼容性验证。

</details>

### 3. 评估 GPU 工作负载兼容性时，以下哪项说法不正确？

- A) 驱动程序与 CUDA/框架镜像的兼容性很重要
- B) 内存需求取决于工作负载
- C) 必须考虑受支持的操作系统/内核和容器运行时
- D) 安装 GPU 后就可以忽略 CPU 架构

<details>
<summary>显示答案</summary>

**答案：D) 安装 GPU 后就可以忽略 CPU 架构**

**解释：**
CPU 架构、GPU 型号、驱动程序、操作系统/内核、容器工具包/运行时以及应用镜像都必须彼此兼容。Hybrid Node 没有通用的 4GB GPU 最低要求，也没有固定的 525/550 驱动程序要求。仅为运行已正确打包的容器，并不要求主机安装 nvcc 编译器；nvidia-smi 和 nvcc 报告的是不同组件的信息。

</details>

### 4. 应如何理解主机基础资源建议？

- A) 1 个 CPU 核心和 512MB 内存可保证足够
- B) AWS 建议至少配置 1 vCPU 和 1 GiB RAM，但不存在适用于所有情况的严格最低规格
- C) 每种工作负载都必须恰好使用 4 个 CPU 核心和 8GB 内存
- D) 50GB 磁盘即可保证节点满足要求

<details>
<summary>显示答案</summary>

**答案：B) AWS 建议至少配置 1 vCPU 和 1 GiB RAM，但不存在适用于所有情况的严格最低规格**

**解释：**
应分别评估操作系统、kubelet/运行时、CNI/代理、镜像与日志，以及实际工作负载的资源需求。此前提到的 2 核/2GB 答案和 20/50/100GB 磁盘规格只是彼此不一致的规划示例，并非经过验证的工作负载最低要求。同样，AWS 提供的 100Mbps/200ms 网络建议属于一般指导，并非普遍适用的验收门槛。

</details>

### 5. 主机成为 EKS Hybrid Node 后，以下哪项组件并非因此就必须安装？

- A) 兼容的 CRI 运行时，例如 containerd
- B) kubelet
- C) Docker Engine
- D) 所选的 AWS 凭证/身份验证辅助工具

<details>
<summary>显示答案</summary>

**答案：C) Docker Engine**

**解释：**
Docker 提供的 containerd 软件包来源并不是运行 Docker Engine 的必要条件。对于非 Bottlerocket 主机，nodeadm 的 install 阶段会安装依赖项，config check 会验证输入，而 init 会配置并加入节点。签名密钥变更后，通过 SSM 安装或升级需要 nodeadm 1.0.19 或更高版本；本次核对的版本为 1.0.20。RHEL 使用 `docker`，或使用预先安装的运行时并将选项设为 `none`，而不是 `distro`。

</details>

### 6. 如何正确规划 H100 Hybrid Node 部署？

- A) 在所有主机上安装 450.x
- B) 将旧版 525.x 示例视为永久适用的充分条件
- C) 不论所用框架为何，都必须恰好使用 535.x
- D) 选择受支持的 GPU/操作系统/驱动程序/CUDA/运行时组合，并验证应用程序

<details>
<summary>显示答案</summary>

**答案：D) 选择受支持的 GPU/操作系统/驱动程序/CUDA/运行时组合，并验证应用程序**

**解释：**
旧表格混淆了最低版本和建议版本，且与原答案相矛盾。450/525/535/545/550 这些版本号并不构成当前通用的部署要求。请核对具体 H100 型号、受支持的驱动程序分支、框架镜像和功能要求，并先在已隔离的测试主机上验证变更。本次审查没有执行 GPU 运算或模型基准测试。

</details>

## 参考资料

- [Hybrid Node 前提条件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [Hybrid Node 操作系统兼容性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm 参考文档](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
