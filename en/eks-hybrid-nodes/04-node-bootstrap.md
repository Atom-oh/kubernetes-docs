# Node Bootstrap

< [Previous: Air-Gap Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+
> **Last Updated**: February 2025

This document covers the process of bootstrapping on-premises servers as EKS Hybrid Nodes using nodeadm.

## nodeadm CLI Installation

nodeadm is the CLI tool for initializing and managing EKS Hybrid Nodes.

```bash
# Download nodeadm (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Check version
nodeadm version
```

## Writing NodeConfig YAML

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

## Create SSM Hybrid Activation

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

## Install CA Certificate on System

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

## Node Initialization

```bash
# Initialize node using nodeadm
sudo nodeadm init -c file://nodeconfig.yaml

# Check initialization logs
sudo journalctl -u kubelet -f

# Check node status (from EKS cluster)
kubectl get nodes -o wide
```

## Verify Node Registration

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

---

< [Previous: Air-Gap Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >
