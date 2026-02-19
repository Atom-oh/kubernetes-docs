# EKS Hybrid Nodes Prerequisites Quiz

> **Related Document**: [Prerequisites](../../eks-hybrid-nodes/01-prerequisites.md)

## Multiple Choice Questions

### 1. Which is NOT a suitable use case for EKS Hybrid Nodes?

A. Utilizing GPU servers in on-premises data centers
B. Data locality requirements for regulatory compliance
C. Running purely cloud-native workloads
D. Latency-sensitive edge workloads

<details>
<summary>Show Answer</summary>

**Answer: C. Running purely cloud-native workloads**

**Explanation:**
Purely cloud-native workloads are more efficiently run on regular EKS node groups or Fargate. Hybrid Nodes are used when there are special requirements (on-premises, edge, regulatory, etc.).

**Suitable Use Cases for EKS Hybrid Nodes:**
- Utilizing on-premises GPU/specialized hardware
- Data sovereignty/regulatory compliance requirements
- Latency-sensitive edge computing
- Cloud migration transition period
- Protecting existing infrastructure investments

</details>

### 2. Which operating system is supported by EKS Hybrid Nodes?

A. Windows Server 2019 only
B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9
C. macOS Ventura or later
D. FreeBSD 13 or later

<details>
<summary>Show Answer</summary>

**Answer: B. Ubuntu 20.04/22.04, Amazon Linux 2023, RHEL 8/9**

**Explanation:**
EKS Hybrid Nodes only supports Linux-based operating systems. Supported OS versions include:
- Ubuntu 20.04 LTS, 22.04 LTS
- Amazon Linux 2023
- Red Hat Enterprise Linux (RHEL) 8, 9
- Bottlerocket (container-optimized OS)

```bash
# Check OS version
cat /etc/os-release

# Check kernel version (5.4 or later recommended)
uname -r
```

</details>

### 3. Which is NOT a minimum requirement for running GPU workloads on Hybrid Nodes?

A. NVIDIA Driver 525 or later
B. CUDA Toolkit 11.8 or later
C. Minimum 4GB GPU memory
D. x86_64 or arm64 architecture is mandatory

<details>
<summary>Show Answer</summary>

**Answer: D. x86_64 or arm64 architecture is mandatory**

**Explanation:**
x86_64 or arm64 architecture is a CPU architecture requirement, not a direct requirement for GPU workloads. Key GPU workload requirements are:

- **NVIDIA Driver**: 525 or later (CUDA 12 support)
- **CUDA Toolkit**: 11.8 or later
- **GPU Memory**: Minimum 4GB recommended (varies by workload)
- **containerd**: 1.6 or later (GPU container support)

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Check CUDA version
nvcc --version
```

</details>

### 4. What are the minimum hardware requirements for EKS Hybrid Nodes?

A. CPU 1 core, Memory 512MB
B. CPU 2 cores, Memory 2GB
C. CPU 4 cores, Memory 8GB
D. CPU 8 cores, Memory 16GB

<details>
<summary>Show Answer</summary>

**Answer: B. CPU 2 cores, Memory 2GB**

**Explanation:**
The minimum hardware requirements for EKS Hybrid Nodes are:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores or more |
| Memory | 2GB | 4GB or more |
| Disk | 20GB | 50GB or more (SSD recommended) |
| Network | 100Mbps | 1Gbps or more |

Production environments may require higher specifications depending on workload requirements.

</details>

### 5. Which is NOT a required software component for EKS Hybrid Nodes configuration?

A. containerd runtime
B. kubelet
C. Docker Engine
D. aws-iam-authenticator

<details>
<summary>Show Answer</summary>

**Answer: C. Docker Engine**

**Explanation:**
EKS Hybrid Nodes uses containerd as the container runtime, and Docker Engine is not required. Required components are:

- **containerd**: Container runtime (1.6 or later)
- **kubelet**: Kubernetes node agent
- **aws-iam-authenticator**: AWS IAM authentication
- **CNI plugins**: Container networking

```bash
# nodeadm automatically installs components
sudo nodeadm init --config-source file://nodeadm-config.yaml

# Check installed components
systemctl status containerd
systemctl status kubelet
```

</details>

### 6. What is the minimum NVIDIA driver version required for using H100 GPUs with Hybrid Nodes?

A. 450.x
B. 470.x
C. 525.x
D. 535.x

<details>
<summary>Show Answer</summary>

**Answer: D. 535.x**

**Explanation:**
The NVIDIA H100 GPU uses Hopper architecture and requires the latest drivers:

| GPU Model | Minimum Driver Version | Recommended Driver Version |
|-----------|----------------------|---------------------------|
| A100 | 450.x | 525.x or later |
| H100 | 525.x | 535.x or later |
| H200 | 535.x | 545.x or later |

```bash
# Verify H100 driver installation
nvidia-smi

# Update driver
sudo apt-get update
sudo apt-get install nvidia-driver-535
```

Driver version 535.x or later is recommended to fully utilize H100's key features (MIG expansion, Transformer Engine, etc.).

</details>

