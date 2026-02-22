# Node Bootstrap

< [Previous: Air-Gap Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+
> **Last Updated**: February 2026

This document covers the process of bootstrapping on-premises servers as EKS Hybrid Nodes using nodeadm.

## Bootstrap Workflow Overview

The following steps outline the complete node bootstrap process from IAM credential setup to a fully ready hybrid node.

### Bootstrap Steps

1. **Prepare IAM credentials** — Create SSM Hybrid Activation or configure IAM Roles Anywhere
2. **Download nodeadm** — Download the CLI binary for your architecture
3. **Run `nodeadm install`** — Install Kubernetes components and dependencies
4. **Write NodeConfig YAML** — Configure cluster details, credentials, kubelet, and containerd
5. **Install CA certificates** — Add private registry CA certs to system trust store (if using a private registry)
6. **Run `nodeadm init`** — Initialize the node and register with EKS cluster
7. **Install CNI** — Deploy Cilium via Helm for pod networking
8. **Verify registration** — Confirm node shows `Ready` in `kubectl get nodes`

## nodeadm CLI Download and Installation

nodeadm is the CLI tool for initializing and managing EKS Hybrid Nodes.

### Step 1: Download nodeadm

```bash
# Download nodeadm (Linux x86_64)
curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# For ARM64 architecture:
# curl -Lo nodeadm https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/arm64/nodeadm

# Check version
nodeadm version
```

### Step 2: Run `nodeadm install`

The `nodeadm install` command installs Kubernetes components (kubelet, kubectl, etc.) and system dependencies. This must run before `nodeadm init`.

```bash
# Install with SSM credential provider
sudo nodeadm install 1.31 --credential-provider ssm

# Install with IAM Roles Anywhere credential provider
sudo nodeadm install 1.31 --credential-provider iam-ra

# Custom timeout for slow networks
sudo nodeadm install 1.31 --credential-provider ssm --timeout 20m0s
```

> **Note**: Replace `1.31` with your target Kubernetes version. The version must match your EKS cluster version.

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
    #   nodeName: hybrid-node-001  # Must match certificate CN
    #   trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
    #   profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
    #   roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
    #   certificatePath: /etc/iam/pki/server.pem
    #   privateKeyPath: /etc/iam/pki/server.key

  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu
      - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule

  containerd:
    config: |
      version = 2

      [plugins."io.containerd.grpc.v1.cri".registry]
        config_path = "/etc/containerd/certs.d"

      # Private registry TLS configuration (uncomment and adjust for your registry)
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".tls]
      #   ca_file = "/etc/ssl/certs/registry-ca.crt"
      # [plugins."io.containerd.grpc.v1.cri".registry.configs."registry.internal.company.io".auth]
      #   username = "pull-robot"
      #   password = "<token>"
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

## IAM Roles Anywhere Setup (Alternative)

If using IAM Roles Anywhere instead of SSM, configure the trust anchor, profile, and certificates:

```bash
# Create Trust Anchor
TRUST_ANCHOR_ARN=$(aws rolesanywhere create-trust-anchor \
  --name "eks-hybrid-trust-anchor" \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$(cat ca.pem)}" \
  --enabled \
  --query 'trustAnchor.trustAnchorArn' --output text)

# Create Profile
PROFILE_ARN=$(aws rolesanywhere create-profile \
  --name "eks-hybrid-profile" \
  --role-arns arn:aws:iam::123456789012:role/EKSHybridNodeRole \
  --enabled \
  --query 'profile.profileArn' --output text)

echo "Trust Anchor ARN: $TRUST_ANCHOR_ARN"
echo "Profile ARN: $PROFILE_ARN"
# Enter these values in nodeconfig.yaml under spec.hybrid.iamRolesAnywhere
```

NodeConfig YAML for IAM Roles Anywhere:

```yaml
spec:
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001  # Must match certificate CN
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

> **Note**: When using IAM Roles Anywhere, enable `acceptRoleSessionName` on the IAM RA profile and set `MaxSessionDuration` on the IAM role to at least 1 hour (recommended: 12 hours) to avoid frequent credential refresh.

## Install CA Certificate on System (Private Registry)

If you use a private container registry with a self-signed or internal CA certificate, install the CA cert on each node:

```bash
# Install CA certificate on system (Ubuntu)
sudo cp ca.crt /usr/local/share/ca-certificates/registry-ca.crt
sudo update-ca-certificates

# RHEL/CentOS
sudo cp ca.crt /etc/pki/ca-trust/source/anchors/registry-ca.crt
sudo update-ca-trust extract

# Configure directory for containerd to find certificate
sudo mkdir -p /etc/containerd/certs.d/<REGISTRY_HOST>
cat <<EOF | sudo tee /etc/containerd/certs.d/<REGISTRY_HOST>/hosts.toml
server = "https://<REGISTRY_HOST>"

[host."https://<REGISTRY_HOST>"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
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
# hybrid-node-001     Ready    <none>   5m    v1.31.0   eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node hybrid-node-001

# Filter Hybrid Nodes
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid
```

---

## Cilium CNI Installation

Cilium is the AWS-supported CNI for EKS Hybrid Nodes. Hybrid nodes appear with status `Not Ready` until a CNI is installed. Amazon VPC CNI is **not compatible** with hybrid nodes.

> **Supported versions**: Cilium v1.17.x and v1.18.x for all Kubernetes versions supported in Amazon EKS
> **Helm repository**: `oci://public.ecr.aws/eks/cilium/cilium`

> **Prerequisites**:
> - **Kernel version**: Cilium requires Linux kernel **5.10 or higher**. Ubuntu 20.04 and RHEL 8 default kernels are below 5.10 — you must upgrade the kernel before installing Cilium v1.18.x.
> - **Hybrid nodes only**: Cilium affinity must be set to run only on hybrid nodes (`eks.amazonaws.com/compute-type: hybrid`). Do not run Cilium on cloud nodes that use VPC CNI.
> - **IPAM settings are immutable**: The `clusterPoolIPv4PodCIDRList` and `clusterPoolIPv4MaskSize` values **cannot be changed** after initial deployment. Plan your pod CIDR allocation carefully before installing.

### Create Cilium Values YAML

```yaml
# cilium-values.yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: In
          values:
          - hybrid

ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList:
    - <POD_CIDR>  # Same as your EKS cluster's remote pod networks

loadBalancer:
  serviceTopology: true

operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: In
            values:
            - hybrid
  unmanagedPodWatcher:
    restart: false

envoy:
  enabled: false

kubeProxyReplacement: "false"
```

### Install Cilium

```bash
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version 1.18.3-0 \
  --namespace kube-system \
  --values cilium-values.yaml
```

### Verify Installation

```bash
# Check Cilium pods are running
kubectl get pods -n kube-system -l app.kubernetes.io/name=cilium

# Nodes should now show Ready
kubectl get nodes -o wide
```

---

## Webhook and Add-on Placement Guidance

Some EKS add-ons use webhooks that require the API server to reach pods directly. If your on-premises pod CIDR is **not routable**, these add-ons must run on cloud nodes only.

### Cloud-Only Add-ons (Unroutable Pod CIDR)

Use `nodeAffinity` to restrict webhook-based add-ons to cloud nodes:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

Add-ons requiring this treatment: AWS Load Balancer Controller, CloudWatch Observability Agent, ADOT, cert-manager.

### CoreDNS Mixed Mode

CoreDNS should run on **both** cloud and hybrid nodes for DNS resilience. Use `topologySpreadConstraints` with at least 4 replicas (2 per side). See [Network Configuration - CoreDNS Dual-Location Deployment](./02-network-configuration.md#coredns-dual-location-deployment-on-premises--cloud).

### EKS Pod Identity Agent

EKS Pod Identity Agent requires the `eks-auth` VPC endpoint in private/air-gap environments. Install as an EKS managed add-on:

```bash
aws eks create-addon \
  --cluster-name my-hybrid-cluster \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.3.3-eksbuild.1
```

---

## Node Upgrade

Hybrid nodes follow the same Kubernetes version skew policy as upstream Kubernetes — they cannot be newer than the control plane and may be up to three minor versions older.

### Cutover Migration (Recommended)

When spare capacity is available, create new nodes on the target version and gracefully migrate workloads:

```bash
# 1. Install nodeadm on new hosts with target version
nodeadm install K8S_VERSION --credential-provider CREDS_PROVIDER

# 2. Cordon old nodes
kubectl cordon NODE_NAME

# 3. Scale CoreDNS for resiliency
kubectl scale deployments/coredns --replicas=2 -n kube-system

# 4. Drain old nodes
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 5. Uninstall old nodes
sudo nodeadm uninstall

# 6. Delete old node resource
kubectl delete node NODE_NAME
```

### In-Place Upgrade

When spare capacity is unavailable, upgrade nodes in-place (results in downtime):

```bash
# 1. Cordon the node
kubectl cordon NODE_NAME

# 2. Drain workloads
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# 3. Run nodeadm upgrade
sudo nodeadm upgrade K8S_VERSION -c file://nodeConfig.yaml

# 4. Uncordon after upgrade completes
kubectl uncordon NODE_NAME

# 5. Monitor
kubectl get nodes -o wide -w
```

---

## Troubleshooting

### nodeadm debug

The `nodeadm debug` command validates network access, credentials, and cluster connectivity:

```bash
sudo nodeadm debug -c file://nodeConfig.yaml
```

This validates:
- Network access to AWS APIs
- AWS credentials retrieval for Hybrid Nodes IAM role
- Network access to EKS Kubernetes API endpoint
- Node authentication with EKS cluster

### Common Issues and Fixes

#### Installation Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Must run as root | `"msg":"Command failed","error":"must run as root"` | Run `nodeadm` with `sudo` |
| Unable to connect to dependencies | `max retries achieved for http request` | Verify network access to dependency repositories |
| Package manager failure | `failed to run update using package manager` | Run `apt update` or `dnf update` first |
| Timeout | `context deadline exceeded` | Use `--timeout 20m0s` flag |

#### Connection Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Node IP not in CIDR | `node IP is not in any of the remote network CIDR blocks` | Verify `RemoteNodeNetworks` includes node IP range |
| API server unreachable | `Unable to connect to the server` / `dial tcp: i/o timeout` | Check VPN/DX tunnel, firewall port 443, VPC routes to TGW/VGW |
| Unauthorized | `Failed to ensure lease exists: Unauthorized` | Verify IAM role, EKS access entry with `HYBRID_LINUX` type |
| Node stays NotReady | Node registered but NotReady | Install CNI (Cilium), check VXLAN port 8472 |
| DNS resolution failure | `no such host` for EKS API endpoint | Configure Route 53 Resolver Inbound Endpoint, update on-prem DNS |
| Image pull failure | `ErrImagePull` on system pods | Verify ECR VPC endpoints, containerd registry config, CA certs |
| Certificate error | `x509: certificate signed by unknown authority` | Install CA cert in system trust store, run `update-ca-certificates` |
| Hybrid profile exists | `hybrid profile already exists` | Run `nodeadm uninstall` then `nodeadm install` then `nodeadm init` |

#### SSM Credential Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Invalid activation | `InvalidActivation` | Verify region, activationCode, activationId in nodeConfig.yaml |
| Expired activation | `ActivationExpired` | Create new SSM hybrid activation, update nodeConfig.yaml |
| Expired token | `ExpiredTokenException` | Restart SSM agent: `systemctl restart amazon-ssm-agent` |

#### IAM Roles Anywhere Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Certificate not found | `open /etc/iam/pki/server.pem: no such file or directory` | Create `/etc/iam/pki/` directory, copy certificate and key |
| Not authorized | `not authorized to perform: sts:AssumeRole` | Verify trust policy, trust anchor ARN, IAM RA profile |

### Diagnostic Commands

```bash
# Check kubelet status and logs
sudo systemctl status kubelet
sudo journalctl -u kubelet -f

# Check containerd
sudo systemctl status containerd

# Validate credentials
sudo aws sts get-caller-identity

# Check SSM agent (AL2023/RHEL)
sudo systemctl status amazon-ssm-agent

# Check SSM agent (Ubuntu)
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent

# Run nodeadm diagnostics
sudo nodeadm debug -c file://nodeConfig.yaml
```

### Node Reset

If bootstrap fails and you need to start fresh:

```bash
# Reset the node completely
sudo nodeadm uninstall

# Clean up any remaining state
sudo rm -rf /var/lib/kubelet /etc/kubernetes /var/lib/etcd

# Re-run initialization
sudo nodeadm init -c file://nodeConfig.yaml
```

---

< [Previous: Air-Gap Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >
