# EKS Hybrid Nodes 前提条件测验

> **相关文档**: [前提条件](../../eks-hybrid-nodes/01-prerequisites.md)

## 多项选择题

### 1. 以下哪项不是 EKS Hybrid Nodes 的适用用例？

A. 使用本地数据中心中的 GPU 服务器
B. 出于法规合规的数据本地性要求
C. 运行纯云原生工作负载
D. 延迟敏感的边缘工作负载

<details>
<summary>显示答案</summary>

**答案：C. 运行纯云原生工作负载**

**解释：**
纯云原生工作负载在常规 EKS node groups 或 Fargate 上运行效率更高。Hybrid Nodes 用于存在特殊要求（本地、边缘、法规等）的场景。

**EKS Hybrid Nodes 的适用用例：**
- 使用本地 GPU/专用硬件
- 数据主权/法规合规要求
- 延迟敏感的边缘计算
- 云迁移过渡期
- 保护现有基础设施投资

</details>

### 2. EKS Hybrid Nodes 支持哪种操作系统？

A. 仅 Windows Server 2019
B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9
C. macOS Ventura 或更高版本
D. FreeBSD 13 或更高版本

<details>
<summary>显示答案</summary>

**答案：B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9**

**解释：**
EKS Hybrid Nodes 仅支持基于 Linux 的操作系统。支持的 OS 版本包括：
- Ubuntu 20.04 LTS, 22.04 LTS
- Amazon Linux 2023
- Red Hat Enterprise Linux (RHEL) 8, 9
- Bottlerocket（容器优化的 OS）

```bash
# Check OS version
cat /etc/os-release

# Check kernel version (5.4 or later recommended)
uname -r
```

</details>

### 3. 以下哪项不是在 Hybrid Nodes 上运行 GPU 工作负载的最低要求？

A. NVIDIA Driver 525 或更高版本
B. CUDA Toolkit 11.8 或更高版本
C. 最低 4GB GPU 内存
D. x86_64 或 arm64 架构是强制要求

<details>
<summary>显示答案</summary>

**答案：D. x86_64 或 arm64 架构是强制要求**

**解释：**
x86_64 或 arm64 架构是 CPU 架构要求，并不是 GPU 工作负载的直接要求。GPU 工作负载的关键要求是：

- **NVIDIA Driver**: 525 或更高版本（支持 CUDA 12）
- **CUDA Toolkit**: 11.8 或更高版本
- **GPU Memory**: 建议最低 4GB（因工作负载而异）
- **containerd**: 1.6 或更高版本（支持 GPU 容器）

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Check CUDA version
nvcc --version
```

</details>

### 4. EKS Hybrid Nodes 的最低硬件要求是什么？

A. CPU 1 核，内存 512MB
B. CPU 2 核，内存 2GB
C. CPU 4 核，内存 8GB
D. CPU 8 核，内存 16GB

<details>
<summary>显示答案</summary>

**答案：B. CPU 2 核，内存 2GB**

**解释：**
EKS Hybrid Nodes 的最低硬件要求是：

| 资源 | 最低要求 | 推荐配置 |
|----------|---------|-------------|
| CPU | 2 核 | 4 核或更多 |
| 内存 | 2GB | 4GB 或更多 |
| 磁盘 | 20GB | 50GB 或更多（推荐 SSD） |
| 网络 | 100Mbps | 1Gbps 或更多 |

生产环境可能需要更高规格，具体取决于工作负载要求。

</details>

### 5. 以下哪项不是 EKS Hybrid Nodes 配置所需的软件组件？

A. containerd runtime
B. kubelet
C. Docker Engine
D. aws-iam-authenticator

<details>
<summary>显示答案</summary>

**答案：C. Docker Engine**

**解释：**
EKS Hybrid Nodes 使用 containerd 作为容器运行时，不需要 Docker Engine。所需组件包括：

- **containerd**: 容器运行时（1.6 或更高版本）
- **kubelet**: Kubernetes 节点代理
- **aws-iam-authenticator**: AWS IAM 认证
- **CNI plugins**: 容器网络

```bash
# nodeadm automatically installs components
sudo nodeadm init --config-source file://nodeadm-config.yaml

# Check installed components
systemctl status containerd
systemctl status kubelet
```

</details>

### 6. 使用 H100 GPU 与 Hybrid Nodes 时所需的最低 NVIDIA driver 版本是多少？

A. 450.x
B. 470.x
C. 525.x
D. 535.x

<details>
<summary>显示答案</summary>

**答案：D. 535.x**

**解释：**
NVIDIA H100 GPU 使用 Hopper 架构，需要最新的驱动程序：

| GPU 型号 | 最低驱动版本 | 推荐驱动版本 |
|-----------|----------------------|---------------------------|
| A100 | 450.x | 525.x 或更高版本 |
| H100 | 525.x | 535.x 或更高版本 |
| H200 | 535.x | 545.x 或更高版本 |

```bash
# Verify H100 driver installation
nvidia-smi

# Update driver
sudo apt-get update
sudo apt-get install nvidia-driver-535
```

建议使用 535.x 或更高版本的驱动程序，以充分利用 H100 的关键功能（MIG 扩展、Transformer Engine 等）。

</details>
