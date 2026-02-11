# EKS Hybrid Nodes Guide

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **Last Updated**: February 2025

Amazon EKS Hybrid Nodes is a feature that allows you to manage on-premises servers from the AWS EKS control plane. This document covers the concepts, configuration methods, and practical usage of EKS Hybrid Nodes in production environments.

## Table of Contents

1. [EKS Hybrid Nodes Overview](#eks-hybrid-nodes-overview)
2. [System Requirements](#system-requirements)
3. [Network Configuration](#network-configuration)
4. [Harbor Registry Integration](#harbor-registry-integration)
5. [Hybrid Node Setup](#hybrid-node-setup)
6. [GPU Server Integration](#gpu-server-integration)
7. [Workload Placement Strategies](#workload-placement-strategies)
8. [Cost Optimization](#cost-optimization)
9. [Operations and Maintenance](#operations-and-maintenance)
10. [Next Steps](#next-steps)

## EKS Hybrid Nodes Overview

### What are Hybrid Nodes?

EKS Hybrid Nodes is a feature that enables you to register servers in your on-premises data center or edge environment as Kubernetes nodes managed by the AWS EKS control plane. This allows you to manage cloud and on-premises infrastructure as a single Kubernetes cluster.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    EKS Control Plane                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ API Server  │  │    etcd     │  │ Controller  │               │   │
│  │  │             │  │             │  │  Manager    │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                    VPN / Direct Connect                                  │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│         On-Premises          │        Data Center                        │
│  ┌───────────────────────────┴────────────────────────────────────────┐ │
│  │                     Hybrid Nodes                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │ │
│  │  │   Node 1    │  │   Node 2    │  │  GPU Node   │                 │ │
│  │  │  (Worker)   │  │  (Worker)   │  │   (H100)    │                 │ │
│  │  │  nodeadm    │  │  nodeadm    │  │  nodeadm    │                 │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why Use Hybrid Nodes?

#### 1. Regulatory Compliance and Data Sovereignty

Certain industries (finance, healthcare, government) have regulations requiring data to remain within specific regions or facilities. With Hybrid Nodes, you can keep sensitive data on-premises while leveraging EKS management capabilities.

```yaml
# Example of regulatory compliance workload placement
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

#### 2. Data Gravity

When large datasets exist on-premises, it's more efficient to bring compute closer to the data rather than moving data to the cloud.

#### 3. Leveraging Existing Hardware

You can continue to utilize already-invested high-performance servers (especially GPU servers) while applying modern Kubernetes-based workload management.

#### 4. Unified Management

Managing Kubernetes workloads in both cloud and on-premises environments from a single control plane reduces operational complexity.

### Architecture Components

The EKS Hybrid Nodes architecture consists of the following components:

| Component | Location | Role |
|-----------|----------|------|
| EKS Control Plane | AWS | API server, etcd, controller manager, scheduler |
| nodeadm | On-Premises | Node bootstrap and management agent |
| kubelet | On-Premises | Pod execution and node status reporting |
| containerd | On-Premises | Container runtime |
| VPN/Direct Connect | Network | Secure connection between AWS and on-premises |
| SSM Agent or IAM Roles Anywhere | On-Premises | Credential management |

### Primary Use Cases

1. **AI/ML Workloads**: Model training on on-premises GPU servers, inference services in the cloud
2. **Financial Services**: Transaction data processing on-premises, analytics in the cloud
3. **Manufacturing**: Edge computing in factories integrated with central cloud
4. **Media Processing**: Large media file processing where the data resides

## System Requirements

### On-Premises Node Requirements

#### Supported Operating Systems

| Operating System | Version | Architecture |
|-----------------|---------|--------------|
| Ubuntu LTS | 20.04, 22.04, 24.04 | x86_64, arm64 |
| RHEL | 8, 9 | x86_64, arm64 |
| Amazon Linux | 2023 | x86_64, arm64 |

#### Container Runtime

```bash
# Check containerd version
containerd --version
# Required version: 1.6.x or higher

# Check Docker Engine version (includes containerd)
docker --version
# Required version: 20.10.10 or higher
```

#### Minimum Hardware Specifications

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores or more |
| RAM | 4 GB | 8 GB or more |
| Disk | 50 GB SSD | 100 GB NVMe SSD |
| Network | 1 Gbps | 10 Gbps or more |

#### System Configuration Check

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

### GPU Server Requirements (Optional)

#### NVIDIA Driver

```bash
# Check NVIDIA driver version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Required version: 550.x or higher

# Check CUDA version
nvcc --version
# Recommended version: CUDA 12.x
```

#### Supported GPU Models

| GPU Model | VRAM | Primary Use |
|-----------|------|-------------|
| NVIDIA H100 | 80 GB | Large-scale LLM training/inference |
| NVIDIA H200 | 141 GB | Very large models |
| NVIDIA A100 | 40/80 GB | AI/ML general purpose |
| NVIDIA L40S | 48 GB | Inference optimized |

#### GPU Driver Installation (Ubuntu Example)

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

### Network Requirements

#### Bandwidth and Latency

| Item | Minimum | Recommended |
|------|---------|-------------|
| Bandwidth | 1 Gbps | 10 Gbps or more |
| Latency | 50 ms or less | 5 ms or less |
| Packet Loss | 0.1% or less | 0.01% or less |
| MTU | 1500 | 9000 (Jumbo Frame) |

#### Jumbo Frame Configuration

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

## Network Configuration

### Required Firewall Ports

The following ports must be opened for communication between on-premises and AWS:

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 443 | TCP | Bidirectional | Kubernetes API server |
| 10250 | TCP | AWS → On-Prem | Kubelet API |
| 53 | TCP/UDP | Bidirectional | DNS queries |
| 4500 | UDP | Bidirectional | IPSec NAT-T (VPN) |
| 500 | UDP | Bidirectional | IKE (VPN) |

#### iptables Rules Example

```bash
# Allow Kubernetes API server communication
sudo iptables -A INPUT -p tcp --dport 443 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -d 10.0.0.0/8 -j ACCEPT

# Allow Kubelet API
sudo iptables -A INPUT -p tcp --dport 10250 -s 10.0.0.0/8 -j ACCEPT

# Allow DNS
sudo iptables -A INPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### Pod CIDR Firewall Strategy

You need to register firewall rules for the entire Pod CIDR range for Pod-to-Pod communication.

```bash
# Pod CIDR range example: 10.244.0.0/16
# Check cluster's Pod CIDR
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Add firewall rules for Pod CIDR
sudo iptables -A INPUT -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -d 10.244.0.0/16 -j ACCEPT

# Add Service CIDR as well (e.g., 172.20.0.0/16)
sudo iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 172.20.0.0/16 -j ACCEPT
```

### DNS Configuration

#### Route 53 Resolver Inbound Endpoint

Create an Inbound Endpoint to allow on-premises to query AWS domains.

```bash
# Create Inbound Endpoint
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-inbound-$(date +%s)" \
  --name "hybrid-inbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction INBOUND \
  --ip-addresses SubnetId=subnet-111111111,Ip=10.0.1.10 SubnetId=subnet-222222222,Ip=10.0.2.10

# Check Endpoint IPs
aws route53resolver list-resolver-endpoint-ip-addresses \
  --resolver-endpoint-id rslvr-in-xxxxxxxxxxxxx
```

#### Route 53 Resolver Outbound Endpoint

Create an Outbound Endpoint and forwarding rules to allow AWS to query on-premises domains.

```bash
# Create Outbound Endpoint
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-outbound-$(date +%s)" \
  --name "hybrid-outbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction OUTBOUND \
  --ip-addresses SubnetId=subnet-111111111 SubnetId=subnet-222222222

# Create forwarding rule (on-premises domain)
aws route53resolver create-resolver-rule \
  --creator-request-id "forward-onprem-$(date +%s)" \
  --name "forward-to-onprem" \
  --rule-type FORWARD \
  --domain-name "internal.company.io" \
  --resolver-endpoint-id rslvr-out-xxxxxxxxxxxxx \
  --target-ips "Ip=192.168.1.10,Port=53" "Ip=192.168.1.11,Port=53"

# Associate rule with VPC
aws route53resolver associate-resolver-rule \
  --resolver-rule-id rslvr-rr-xxxxxxxxxxxxx \
  --vpc-id vpc-0123456789abcdef0
```

#### CoreDNS Custom Domain Configuration

Forward DNS queries for on-premises domains to on-premises DNS servers.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
    internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
    harbor.internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
```

```bash
# Apply CoreDNS ConfigMap
kubectl apply -f coredns-configmap.yaml

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system

# Test DNS resolution
kubectl run dns-test --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io
```

## Harbor Registry Integration

In Hybrid Nodes environments, operating your own container registry on-premises is efficient. Harbor is an open-source registry providing enterprise-grade features.

### Harbor 2.13 Installation (Helm)

#### Prerequisites

```bash
# Add Helm repository
helm repo add harbor https://helm.goharbor.io
helm repo update

# Create namespace
kubectl create namespace harbor
```

#### TLS Certificate Generation (Self-Signed)

```bash
# Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Company/OU=IT/CN=harbor-ca" \
  -key ca.key \
  -out ca.crt

# Generate Harbor server key
openssl genrsa -out harbor.key 4096

# Create CSR configuration file
cat > harbor-csr.conf <<EOF
[req]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = req_ext
prompt = no

[req_distinguished_name]
C = KR
ST = Seoul
L = Seoul
O = Company
OU = IT
CN = harbor.internal.company.io

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = harbor.internal.company.io
DNS.2 = harbor
DNS.3 = harbor.harbor.svc.cluster.local
IP.1 = 192.168.1.100
EOF

# Generate CSR
openssl req -new -key harbor.key -out harbor.csr -config harbor-csr.conf

# Sign certificate
openssl x509 -req -sha512 -days 3650 \
  -extfile harbor-csr.conf \
  -extensions req_ext \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -in harbor.csr \
  -out harbor.crt

# Create Kubernetes Secret
kubectl create secret tls harbor-tls \
  --cert=harbor.crt \
  --key=harbor.key \
  -n harbor
```

#### Harbor Helm Values Configuration

```yaml
# harbor-values.yaml
expose:
  type: loadBalancer
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls

externalURL: https://harbor.internal.company.io

persistence:
  enabled: true
  persistentVolumeClaim:
    registry:
      storageClass: "local-path"
      size: 500Gi
    database:
      storageClass: "local-path"
      size: 10Gi
    redis:
      storageClass: "local-path"
      size: 5Gi
    trivy:
      storageClass: "local-path"
      size: 10Gi

harborAdminPassword: "StrongP@ssw0rd!"

database:
  type: internal
  internal:
    resources:
      requests:
        memory: 256Mi
        cpu: 100m

redis:
  type: internal

trivy:
  enabled: true
  skipUpdate: false
  resources:
    requests:
      memory: 512Mi
      cpu: 200m

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
  core:
    path: /metrics
    port: 8001
  registry:
    path: /metrics
    port: 8001
  exporter:
    path: /metrics
    port: 8001

portal:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

core:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

jobservice:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m

registry:
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
```

```bash
# Install Harbor
helm install harbor harbor/harbor \
  --namespace harbor \
  --values harbor-values.yaml \
  --version 1.14.0

# Verify installation
kubectl get pods -n harbor
kubectl get svc -n harbor
```

### Robot Account Creation

Create a Robot Account for Kubernetes to use when pulling images.

```bash
# Create Robot Account via Harbor CLI or API
curl -k -X POST "https://harbor.internal.company.io/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  -u "admin:StrongP@ssw0rd!" \
  -d '{
    "name": "k8s-pull-robot",
    "description": "Robot account for Kubernetes image pulling",
    "duration": -1,
    "level": "system",
    "permissions": [
      {
        "kind": "project",
        "namespace": "*",
        "access": [
          {"resource": "repository", "action": "pull"},
          {"resource": "artifact", "action": "read"}
        ]
      }
    ]
  }'
```

### Kubernetes Integration

#### Create Docker Registry Secret

```bash
# Create Secret with Harbor credentials
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.internal.company.io \
  --docker-username='robot$k8s-pull-robot' \
  --docker-password='<robot-account-token>' \
  --docker-email=admin@company.io \
  --namespace=default

# Replicate to all namespaces (optional)
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get secret harbor-registry-secret -n default -o yaml | \
    sed "s/namespace: default/namespace: $ns/" | \
    kubectl apply -f -
done
```

#### Configure imagePullSecrets in ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: default
  namespace: default
imagePullSecrets:
- name: harbor-registry-secret
```

```bash
# Patch existing default ServiceAccount
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets": [{"name": "harbor-registry-secret"}]}'
```

#### Configure Harbor Hostname Resolution in CoreDNS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns-custom
  namespace: kube-system
data:
  harbor.server: |
    harbor.internal.company.io:53 {
        errors
        cache 30
        hosts {
            192.168.1.100 harbor.internal.company.io
            fallthrough
        }
    }
```

## Hybrid Node Setup

### nodeadm CLI Installation

nodeadm is the CLI tool for initializing and managing EKS Hybrid Nodes.

```bash
# Download nodeadm (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Check version
nodeadm version
```

### Writing NodeConfig YAML

```yaml
# nodeconfig.yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
    apiServerEndpoint: https://XXXXXXXXXXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com
    certificateAuthority: |
      -----BEGIN CERTIFICATE-----
      MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      -----END CERTIFICATE-----
    cidr: 10.100.0.0/16  # Service CIDR

  # Credential method selection (SSM or IAM Roles Anywhere)
  hybrid:
    # Method 1: SSM Hybrid Activations
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>

    # Method 2: IAM Roles Anywhere (uncomment to use)
    # iamRolesAnywhere:
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/eks/pki/node.crt
    #   privateKeyPath: /etc/eks/pki/node.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=topology.kubernetes.io/zone=on-premises,node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=location=on-premises:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".tls]
        ca_file = "/etc/ssl/certs/harbor-ca.crt"

      [plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.internal.company.io".auth]
        username = "robot$k8s-pull-robot"
        password = "<robot-account-token>"
```

### Create SSM Hybrid Activation

```bash
# Create SSM Hybrid Activation
aws ssm create-activation \
  --default-instance-name "eks-hybrid-node" \
  --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" \
  --registration-limit 100 \
  --region ap-northeast-2 \
  --tags "Key=Environment,Value=Production" "Key=NodeType,Value=Hybrid"

# Enter the output ActivationCode and ActivationId in nodeconfig.yaml
```

### Install CA Certificate on System

```bash
# Install Harbor CA certificate on system (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/harbor-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/harbor-ca.crt
sudo update-ca-trust extract

# Configure directory for containerd to find certificate
sudo mkdir -p /etc/containerd/certs.d/harbor.internal.company.io
cat <<EOF | sudo tee /etc/containerd/certs.d/harbor.internal.company.io/hosts.toml
server = "https://harbor.internal.company.io"

[host."https://harbor.internal.company.io"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/harbor-ca.crt"
EOF
```

### Node Initialization

```bash
# Initialize node using nodeadm
sudo nodeadm init -c file://nodeconfig.yaml

# Check initialization logs
sudo journalctl -u kubelet -f

# Check node status (from EKS cluster)
kubectl get nodes -o wide
```

### Verify Node Registration

```bash
# Check node list
kubectl get nodes --show-labels

# Expected output:
# NAME                STATUS   ROLES    AGE   VERSION   LABELS
# ip-10-0-1-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2a
# ip-10-0-2-100       Ready    <none>   1d    v1.31.0   topology.kubernetes.io/zone=ap-northeast-2b
# hybrid-node-001     Ready    <none>   5m    v1.31.0   topology.kubernetes.io/zone=on-premises

# Check node details
kubectl describe node hybrid-node-001

# Filter Hybrid Nodes
kubectl get nodes -l topology.kubernetes.io/zone=on-premises
```

## GPU Server Integration

### NVIDIA GPU Operator Deployment

The GPU Operator automatically deploys all components needed to manage NVIDIA GPUs in a Kubernetes cluster.

```bash
# Add NVIDIA GPU Operator Helm repository
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Install GPU Operator
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true \
  --set migManager.enabled=false \
  --set dcgmExporter.enabled=true
```

> **Note**: Since NVIDIA drivers are already installed on on-premises nodes, set `driver.enabled=false`.

### H100/H200 Server Integration

#### Verify Device Plugin Configuration

```bash
# Check Device Plugin status on GPU nodes
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset

# Check GPU resources
kubectl describe node hybrid-gpu-node-001 | grep -A 10 "Allocatable:"
# Expected output:
# Allocatable:
#   cpu:                128
#   memory:             1024Gi
#   nvidia.com/gpu:     8
```

#### GPU Resource Verification

```bash
# Verify GPU access with test Pod
kubectl run gpu-test --rm -it \
  --image=nvidia/cuda:12.3.1-base-ubuntu22.04 \
  --restart=Never \
  --overrides='
{
  "spec": {
    "nodeSelector": {"topology.kubernetes.io/zone": "on-premises"},
    "tolerations": [{"key": "location", "operator": "Equal", "value": "on-premises", "effect": "NoSchedule"}],
    "containers": [{
      "name": "gpu-test",
      "image": "nvidia/cuda:12.3.1-base-ubuntu22.04",
      "command": ["nvidia-smi"],
      "resources": {"limits": {"nvidia.com/gpu": "1"}}
    }]
  }
}' \
  -- nvidia-smi
```

### Dynamic Resource Allocation (DRA)

Kubernetes 1.31+ enables more flexible GPU resource management through DRA.

#### ResourceClass Definition

```yaml
# gpu-resource-class.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: nvidia-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.present
      operator: In
      values: ["true"]
---
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: high-memory-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.product
      operator: In
      values: ["NVIDIA-H100-80GB-HBM3", "NVIDIA-H200"]
```

#### ResourceClaim Template

```yaml
# gpu-resource-claim-template.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
  namespace: ai-workloads
spec:
  spec:
    resourceClassName: nvidia-gpu
    allocationMode: WaitForFirstConsumer
```

#### Pod Definition Using DRA

```yaml
# pod-with-dra.yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference-pod
  namespace: ai-workloads
spec:
  nodeSelector:
    topology.kubernetes.io/zone: on-premises
  tolerations:
  - key: location
    operator: Equal
    value: on-premises
    effect: NoSchedule
  containers:
  - name: llm-server
    image: harbor.internal.company.io/ai/vllm-server:v0.4.0
    resources:
      claims:
      - name: gpu-resource
    env:
    - name: CUDA_VISIBLE_DEVICES
      value: "0,1,2,3"
  resourceClaims:
  - name: gpu-resource
    source:
      resourceClaimTemplateName: gpu-claim-template
```

#### DRA Monitoring Metrics

```bash
# Check ResourceClaim status
kubectl get resourceclaims -n ai-workloads

# ResourceClaim details
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# Check DRA controller logs
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

## Workload Placement Strategies

### Node Affinity and Taints/Tolerations

#### Hybrid Node Taint Configuration

```bash
# Add Taint to on-premises nodes
kubectl taint nodes hybrid-node-001 location=on-premises:NoSchedule

# Add additional Taint to GPU nodes
kubectl taint nodes hybrid-gpu-node-001 gpu=true:NoSchedule
```

#### On-Premises Only Workload

```yaml
# on-prem-workload.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
  namespace: analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
      tolerations:
      - key: location
        operator: Equal
        value: on-premises
        effect: NoSchedule
      containers:
      - name: processor
        image: harbor.internal.company.io/analytics/data-processor:v2.1.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

### GPU Workloads On-Premises, CPU Workloads in Cloud Pattern

```yaml
# hybrid-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-training
  namespace: ai-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ml-training
  template:
    metadata:
      labels:
        app: ml-training
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
              - key: nvidia.com/gpu.present
                operator: In
                values:
                - "true"
      tolerations:
      - key: location
        operator: Equal
        value: on-premises
        effect: NoSchedule
      - key: gpu
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: trainer
        image: harbor.internal.company.io/ai/model-trainer:v1.0.0
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            cpu: "16"
            memory: "64Gi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference-api
  namespace: ai-workloads
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ml-inference-api
  template:
    metadata:
      labels:
        app: ml-inference-api
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: NotIn
                values:
                - on-premises
      containers:
      - name: api
        image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/ai/inference-api:v1.0.0
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
```

### Cloud Bursting with Karpenter

Automatically scale to AWS when on-premises capacity is exceeded.

#### Karpenter NodePool Configuration

```yaml
# karpenter-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cloud-burst-pool
spec:
  template:
    metadata:
      labels:
        node-type: cloud-burst
        topology.kubernetes.io/zone: ap-northeast-2a
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m6i.4xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2023
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-hybrid-cluster
  role: KarpenterNodeRole-my-hybrid-cluster
```

#### Topology-Aware Scheduling

```yaml
# topology-aware-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: latency-sensitive-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: latency-sensitive
  template:
    metadata:
      labels:
        app: latency-sensitive
    spec:
      topologySpreadConstraints:
      - maxSkew: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: latency-sensitive
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - on-premises
          - weight: 50
            preference:
              matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - ap-northeast-2a
                - ap-northeast-2b
      containers:
      - name: app
        image: harbor.internal.company.io/apps/latency-app:v1.0.0
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
```

## Cost Optimization

### On-Premises GPU vs Cloud GPU Cost Comparison

#### Monthly Cost Comparison (Example)

| Item | On-Premises H100 Server | AWS p5.48xlarge |
|------|------------------------|-----------------|
| GPU | 8x H100 80GB | 8x H100 80GB |
| Hourly Cost | ~$24.96 (TCO-based) | ~$98.32 |
| Monthly Cost (24/7) | ~$17,971 | ~$70,790 |
| 3-Year TCO | ~$647,000 | ~$2,548,440 |

> **Calculation Basis**: On-premises includes hardware, power, cooling, space, management personnel. Cloud is based on On-Demand pricing.

#### Cost Calculation Script

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid Environment Cost Calculator

# On-premises H100 server monthly cost (TCO-based)
ONPREM_H100_MONTHLY=17971

# AWS p5.48xlarge hourly cost
AWS_P5_HOURLY=98.32

# Enter usage hours
read -p "Monthly GPU usage hours: " HOURS

# Calculate costs
AWS_COST=$(echo "$AWS_P5_HOURLY * $HOURS" | bc)
ONPREM_COST=$ONPREM_H100_MONTHLY

echo ""
echo "=== Monthly Cost Comparison ==="
echo "On-Premises H100: \$${ONPREM_COST}"
echo "AWS p5.48xlarge: \$${AWS_COST}"
echo ""

# Calculate break-even point
BREAKEVEN=$(echo "$ONPREM_COST / $AWS_P5_HOURLY" | bc)
echo "Break-even point: ${BREAKEVEN} hours/month"
echo "If current usage exceeds ${BREAKEVEN} hours, on-premises is more cost-effective."
```

### Break-Even Analysis

```
Cost comparison by monthly usage hours:

  $80,000 |                                        ___
          |                                   ____/
  $60,000 |                              ____/
          |                         ____/
  $40,000 |                    ____/
          |               ____/
  $20,000 |----------____/------------------------ On-Premises (Fixed Cost)
          |     ____/
        0 |____/
          +----+----+----+----+----+----+----+----+
            100  200  300  400  500  600  700  730
                     Monthly GPU Usage Hours

Break-even point: ~183 hours/month (25% utilization)
- Below 183 hours: AWS is advantageous
- Above 183 hours: On-premises is advantageous
```

### AWS Cost Explorer Integration

```bash
# Hybrid environment cost tag configuration
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=TAG,Key=Environment Type=TAG,Key=NodeType \
  --filter '{
    "Tags": {
      "Key": "kubernetes.io/cluster/my-hybrid-cluster",
      "Values": ["owned"]
    }
  }'

# Cost analysis by EKS cluster
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter '{
    "Tags": {
      "Key": "eks:cluster-name",
      "Values": ["my-hybrid-cluster"]
    }
  }'
```

### Selective Workload Distribution Recommendations

| Workload Type | Recommended Location | Reason |
|--------------|---------------------|--------|
| Large-scale model training | On-Premises GPU | Long-running, cost-effective |
| Real-time inference (high load) | On-Premises GPU | Consistent latency |
| Real-time inference (variable) | AWS (Karpenter) | Elastic scaling |
| Data preprocessing | On-Premises CPU | Minimize data movement |
| API serving | AWS | Global distribution, Auto Scaling |
| Batch processing | AWS Spot | Cost optimization |

## Operations and Maintenance

### Harbor Vulnerability Scan Automation

```yaml
# harbor-scan-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: harbor-vulnerability-scan
  namespace: harbor
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scanner
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              # Trigger scan for all project images
              for project in $(curl -sk -u admin:$HARBOR_PASSWORD \
                "https://harbor.internal.company.io/api/v2.0/projects" | \
                jq -r '.[].name'); do

                for repo in $(curl -sk -u admin:$HARBOR_PASSWORD \
                  "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories" | \
                  jq -r '.[].name'); do

                  # Scan latest tag
                  curl -sk -X POST -u admin:$HARBOR_PASSWORD \
                    "https://harbor.internal.company.io/api/v2.0/projects/$project/repositories/${repo#*/}/artifacts/latest/scan"
                done
              done
            env:
            - name: HARBOR_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: harbor-admin-secret
                  key: password
          restartPolicy: OnFailure
```

### Database Backup Procedure

```bash
#!/bin/bash
# harbor-backup.sh - Harbor Database Backup Script

BACKUP_DIR="/backup/harbor/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres registry > $BACKUP_DIR/registry.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notarysigner > $BACKUP_DIR/notarysigner.sql

kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres notaryserver > $BACKUP_DIR/notaryserver.sql

# Redis backup
kubectl exec -n harbor harbor-redis-0 -- \
  redis-cli BGSAVE

kubectl cp harbor/harbor-redis-0:/data/dump.rdb $BACKUP_DIR/redis-dump.rdb

# Registry data backup (optional - large)
# kubectl exec -n harbor harbor-registry-xxx -- \
#   tar czf - /storage > $BACKUP_DIR/registry-storage.tar.gz

echo "Backup complete: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

### Prometheus Metrics Collection

```yaml
# hybrid-node-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-nodes
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: kubelet
  namespaceSelector:
    matchNames:
    - kube-system
  endpoints:
  - port: https-metrics
    scheme: https
    tlsConfig:
      insecureSkipVerify: true
    bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_topology_kubernetes_io_zone]
      regex: on-premises
      action: keep
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: gpu-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames:
    - gpu-operator
  podMetricsEndpoints:
  - port: metrics
    interval: 15s
```

#### Grafana Dashboard Query Examples

```promql
# Hybrid Node CPU Usage
100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle", node=~"hybrid-.*"}[5m])) * 100)

# Hybrid Node Memory Usage
(1 - (node_memory_MemAvailable_bytes{node=~"hybrid-.*"} / node_memory_MemTotal_bytes{node=~"hybrid-.*"})) * 100

# GPU Usage (DCGM)
DCGM_FI_DEV_GPU_UTIL{kubernetes_node=~"hybrid-gpu-.*"}

# GPU Memory Usage
DCGM_FI_DEV_FB_USED{kubernetes_node=~"hybrid-gpu-.*"} / DCGM_FI_DEV_FB_FREE{kubernetes_node=~"hybrid-gpu-.*"} * 100
```

### Direct Connect Performance Validation

```bash
#!/bin/bash
# network-validation.sh - Direct Connect Network Performance Validation

echo "=== Direct Connect Performance Validation ==="

# Target configuration
EKS_API_ENDPOINT="XXXXXXXX.gr7.ap-northeast-2.eks.amazonaws.com"
AWS_VPC_HOST="10.0.1.100"

# Latency test
echo ""
echo "1. Latency Test (Target: <5ms)"
LATENCY=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f2)
echo "   Average Latency: ${LATENCY}ms"
if (( $(echo "$LATENCY < 5" | bc -l) )); then
    echo "   [PASS] Latency target met"
else
    echo "   [WARN] Latency exceeds target (5ms)"
fi

# Jitter test
echo ""
echo "2. Jitter Test (Target: <2ms)"
JITTER=$(ping -c 100 $AWS_VPC_HOST | tail -1 | awk '{print $4}' | cut -d'/' -f4)
echo "   Jitter: ${JITTER}ms"
if (( $(echo "$JITTER < 2" | bc -l) )); then
    echo "   [PASS] Jitter target met"
else
    echo "   [WARN] Jitter exceeds target (2ms)"
fi

# Packet loss test
echo ""
echo "3. Packet Loss Test (Target: <0.01%)"
PACKET_LOSS=$(ping -c 1000 $AWS_VPC_HOST | grep "packet loss" | awk '{print $6}' | tr -d '%')
echo "   Packet Loss Rate: ${PACKET_LOSS}%"
if (( $(echo "$PACKET_LOSS < 0.01" | bc -l) )); then
    echo "   [PASS] Packet loss target met"
else
    echo "   [WARN] Packet loss exceeds target (0.01%)"
fi

# Bandwidth test (requires iperf3)
echo ""
echo "4. Bandwidth Test (Target: >1Gbps)"
if command -v iperf3 &> /dev/null; then
    BANDWIDTH=$(iperf3 -c $AWS_VPC_HOST -t 10 -f g | grep "sender" | awk '{print $7}')
    echo "   Bandwidth: ${BANDWIDTH} Gbps"
else
    echo "   [SKIP] iperf3 not installed"
fi

echo ""
echo "=== Validation Complete ==="
```

### Certificate Renewal Management

```bash
#!/bin/bash
# cert-renewal.sh - Certificate Expiration Check and Renewal Alert

# Check Harbor certificate expiration
echo "=== Certificate Expiration Check ==="

HARBOR_CERT="/etc/ssl/certs/harbor-ca.crt"
DAYS_WARNING=30

if [ -f "$HARBOR_CERT" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in $HARBOR_CERT | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo "Harbor CA Certificate"
    echo "  Expiry Date: $EXPIRY_DATE"
    echo "  Days Remaining: $DAYS_LEFT days"

    if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
        echo "  [WARN] Certificate renewal required!"
        # Send alert (Slack, Email, etc.)
    else
        echo "  [OK] Certificate valid"
    fi
fi

# Check Kubernetes certificate
echo ""
echo "Kubernetes Cluster Certificate"
kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].lastHeartbeatTime}'
```

### Common Troubleshooting

#### ImagePullBackOff Diagnosis

```bash
# Check problem pods
kubectl get pods --all-namespaces | grep ImagePullBackOff

# Check details
kubectl describe pod <pod-name> -n <namespace>

# Common causes and solutions:
# 1. Harbor authentication failure
kubectl get secret harbor-registry-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq

# 2. Certificate issue check
openssl s_client -connect harbor.internal.company.io:443 -CAfile /etc/ssl/certs/harbor-ca.crt

# 3. DNS resolution issue
kubectl run dns-debug --rm -it --image=busybox --restart=Never -- nslookup harbor.internal.company.io

# 4. Network connectivity issue
kubectl run net-debug --rm -it --image=nicolaka/netshoot --restart=Never -- curl -v https://harbor.internal.company.io/v2/
```

#### DNS Resolution Issues

```bash
# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# DNS query test
kubectl run dnsutils --rm -it --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 --restart=Never -- bash
# Inside Pod:
nslookup harbor.internal.company.io
nslookup kubernetes.default.svc.cluster.local
dig +short harbor.internal.company.io

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system
```

#### Node Connectivity Issues

```bash
# Check node status
kubectl get nodes
kubectl describe node hybrid-node-001

# Check kubelet logs (run on node)
sudo journalctl -u kubelet -f --since "10 minutes ago"

# API server connection test (run on node)
curl -k https://<EKS-API-ENDPOINT>:443/healthz

# Check SSM Agent status (run on node)
sudo systemctl status amazon-ssm-agent

# Re-register node
sudo nodeadm reset
sudo nodeadm init -c file://nodeconfig.yaml
```

## Next Steps

To deepen your understanding and practice with EKS Hybrid Nodes, refer to the following resources:

### Quiz

To test your understanding of this document, try the following quiz:
- [EKS Hybrid Nodes Quiz](../../quizzes/eks/12-eks-hybrid-nodes-quiz.md)

### Related Documents

- [EKS Resiliency Guide](./10-eks-resiliency.md) - High availability configuration in hybrid environments
- [EKS Cost Optimization](./07-eks-cost-optimization.md) - Cost management strategies
- [EKS Monitoring and Logging](./06-eks-monitoring-logging.md) - Integrated monitoring configuration

### Official Documentation

- [AWS EKS Hybrid Nodes Official Documentation](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes.html)
- [nodeadm User Guide](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Harbor Official Documentation](https://goharbor.io/docs/)
- [NVIDIA GPU Operator Documentation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
