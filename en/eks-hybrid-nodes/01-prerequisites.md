# Prerequisites and System Requirements

< [Table of Contents](./README.md) | [Next: Network Configuration](./02-network-configuration.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **Last Updated**: February 2025

This document covers the system requirements for on-premises nodes, GPU servers, and network infrastructure needed to deploy EKS Hybrid Nodes.

## On-Premises Node Requirements

### Supported Operating Systems

| Operating System | Version | Architecture |
|-----------------|---------|--------------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |

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

### GPU Driver Installation (Ubuntu Example)

```bash
# Add NVIDIA driver repository
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# Install driver (version 550)
sudo apt install -y nvidia-driver-550

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

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

# Permanent configuration (Ubuntu - Netplan)
cat <<EOF | sudo tee /etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    eth0:
      mtu: 9000
      dhcp4: true
EOF

sudo netplan apply
```

---

< [Table of Contents](./README.md) | [Next: Network Configuration](./02-network-configuration.md) >
