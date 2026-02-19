# Prerequisites and System Requirements

< [Table of Contents](./README.md) | [Next: Network Configuration](./02-network-configuration.md) >

> **Supported Versions**: EKS 1.28+, nodeadm 0.1+
> **Last Updated**: February 2026

This document covers the system requirements for on-premises nodes, GPU servers, and network infrastructure needed to deploy EKS Hybrid Nodes.

## On-Premises Node Requirements

### Supported Operating Systems

| Operating System | Version | Architecture |
|-----------------|---------|--------------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |
| Bottlerocket | v1.37.0 and above (VMware variants only) | x86_64 only |

> **Bottlerocket Note**: Only VMware variants of Bottlerocket are supported for EKS Hybrid Nodes, and Kubernetes v1.28 or higher is required. Bottlerocket includes all necessary dependencies automatically, so the `nodeadm` CLI is not required. ARM architecture is not supported for Bottlerocket.

### Container Runtime

```bash
# Check containerd version
containerd --version
# Required version: 1.6.x or higher

# Check Docker Engine version (includes containerd)
docker --version
# Required version: 20.10.10 or higher
```

### Minimum Hardware Specifications

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores or more |
| RAM | 4 GB | 8 GB or more |
| Disk | 50 GB SSD | 100 GB NVMe SSD |
| Network | 1 Gbps | 10 Gbps or more |

### System Configuration Check

```bash
# Verify swap is disabled
free -h
# Swap should be 0

# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load required kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Set kernel parameters
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

## GPU Server Requirements (Optional)

### NVIDIA Driver

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Required version: 550.x or higher

# Check CUDA version
nvcc --version
# Recommended version: CUDA 12.x
```

### Supported GPU Models

| GPU Model | VRAM | Primary Use |
|-----------|------|-------------|
| NVIDIA H100 | 80 GB | Large-scale LLM training/inference |
| NVIDIA H200 | 141 GB | Very large models |
| NVIDIA A100 | 40/80 GB | AI/ML general purpose |
| NVIDIA L40S | 48 GB | Inference optimized |

### GPU Driver Installation (Amazon Linux 2023 Example)

```bash
# NVIDIA driver installation (Amazon Linux 2023)
# Install kernel development packages
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)

# Add NVIDIA driver repository
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/amzn2023/x86_64/cuda-amzn2023.repo

# Install driver
sudo dnf module install -y nvidia-driver:550-dkms

# Install NVIDIA Container Toolkit
sudo dnf config-manager --add-repo https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit

# Update containerd configuration
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

## Network Requirements

### Bandwidth and Latency

| Item | Minimum | Recommended |
|------|---------|-------------|
| Bandwidth | 1 Gbps | 10 Gbps or more |
| Latency | 50 ms or less | 5 ms or less |
| Packet Loss | 0.1% or less | 0.01% or less |
| MTU | 1500 | 9000 (Jumbo Frame) |

### Jumbo Frame Configuration

```bash
# Check MTU setting
ip link show eth0 | grep mtu

# Set MTU to 9000 (temporary)
sudo ip link set dev eth0 mtu 9000

# Permanent configuration (Amazon Linux 2023 - NetworkManager)
sudo nmcli connection modify "System eth0" 802-3-ethernet.mtu 9000
sudo nmcli connection up "System eth0"

# Verify configuration
nmcli connection show "System eth0" | grep mtu
```

---

< [Table of Contents](./README.md) | [Next: Network Configuration](./02-network-configuration.md) >
