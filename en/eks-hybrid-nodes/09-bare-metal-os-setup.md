# Bare Metal Server OS Installation and Migration Guide

< [Previous: Operations and Maintenance](./08-operations.md) | [Table of Contents](./README.md) | [Next: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+
> **Last Updated**: February 23, 2026

This document covers OS installation methods for deploying EKS Hybrid Nodes on bare metal servers and migration strategies from VMware/OpenShift.

## Overview

### Why Choose Bare Metal

Running EKS Hybrid Nodes on bare metal servers provides the following benefits:

1. **VMware License Cost Savings**: After Broadcom's acquisition of VMware, the transition to a subscription model significantly increased licensing costs.
2. **OpenShift Subscription Cost Reduction**: Eliminate per-node Red Hat OpenShift subscription fees.
3. **Hypervisor Overhead Elimination**: Run workloads directly without a virtualization layer for optimized performance.
4. **License Management Simplification**: Reduce the burden of complex license agreements and audit compliance.

### OS Infrastructure Support Matrix

| OS | Bare Metal | VMware | Credentials | Config Tool |
|----|-----------|--------|-------------|-------------|
| Ubuntu 22.04/24.04 LTS | O | O | SSM / IAM RA | nodeadm (YAML) |
| RHEL 8/9 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Amazon Linux 2023 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Bottlerocket v1.37.0+ | X | O (VMware only) | SSM / IAM RA | govc (TOML) |

> **Note**: Bottlerocket is only supported in VMware environments. For bare metal servers, use Ubuntu, RHEL, or Amazon Linux 2023.

## Cost Comparison Analysis

### License/Subscription Cost Comparison

#### VMware vSphere
After the Broadcom acquisition, VMware transitioned from perpetual licenses to a subscription model:
- Enterprise Plus license: Approximately $4,500-8,500 per CPU socket per year
- Additional components like vSAN and NSX-T incur separate costs

#### OpenShift
Red Hat subscription-based:
- Approximately $2,500-5,000 per node per year (core-based subscription)
- Includes premium support

#### EKS Hybrid Nodes
- $0.01 per vCPU per hour (varies by region)
- No additional licensing required

### Annual Cost Comparison by Scale (32 vCPU Servers)

| Scale | VMware vSphere (Annual) | OpenShift (Annual) | EKS Hybrid Nodes (Annual) |
|-------|------------------------|-------------------|--------------------------|
| 10 nodes | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 nodes | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 nodes | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

> **Calculation**: EKS Hybrid Nodes = 32 vCPU × $0.01/hour × 8,760 hours = $2,803.20/node/year
>
> **Note**: The costs above are estimates. Actual costs may vary based on contract terms, region, and discounts.

### TCO (Total Cost of Ownership) Considerations

In addition to license/subscription costs, consider the following factors:
- Operations staff training costs
- License management and audit compliance overhead
- Technical support and consulting costs
- Migration costs (one-time)

## OS-Specific Bare Metal Installation

### Prerequisites

#### BIOS/UEFI Settings
- Configure PXE boot priority
- Disable Secure Boot or use signed bootloaders
- Enable virtualization extensions (VT-x/AMD-V) for containerd

#### Network Infrastructure
- DHCP Server: Provides IP addresses and PXE boot information
- TFTP Server: Serves bootloader and kernel images
- HTTP Server: Hosts OS installation images and configuration files

#### AWS Packer Templates
When creating images for bare metal, set the `CREDENTIAL_PROVIDER` environment variable:

```bash
# Create Qcow2 or Raw format images
export CREDENTIAL_PROVIDER=ssm  # or iam-ra

packer build \
  -var "credential_provider=${CREDENTIAL_PROVIDER}" \
  -var "output_format=raw" \
  bare-metal-template.pkr.hcl
```

### Ubuntu LTS (22.04/24.04)

Ubuntu uses Autoinstall (cloud-init based) for PXE automated installation.

#### Autoinstall Configuration Example

```yaml
#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  network:
    ethernets:
      ens0:
        dhcp4: true
    version: 2
  storage:
    layout:
      name: lvm
  identity:
    hostname: hybrid-node
    username: ubuntu
    password: "$6$rounds=4096$..."  # Encrypted password
  ssh:
    install-server: true
    authorized-keys:
      - ssh-rsa AAAA...  # SSH public key
  packages:
    - curl
    - jq
    - open-iscsi
    - nfs-common
  late-commands:
    - curtin in-target -- bash -c 'curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm && chmod +x nodeadm && mv nodeadm /usr/local/bin/'
```

#### Ubuntu 24.04 Specific Notes

Ubuntu 24.04 requires containerd v1.7.19 or later, or AppArmor profile changes are needed (Ubuntu bug #2065423):

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

> **Important**: A reboot is required after AppArmor changes. Without rebooting, Pods may not terminate properly.

### RHEL 9

RHEL uses Kickstart for PXE automated installation.

#### Kickstart Configuration Example

```bash
# ks.cfg
lang en_US.UTF-8
keyboard us
timezone America/New_York --utc
rootpw --iscrypted $6$rounds=4096$...
network --bootproto=dhcp --device=ens0 --activate
autopart --type=lvm
clearpart --all --initlabel

%packages
@core
curl
jq
container-tools
%end

%post
# Install nodeadm
curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
chmod +x nodeadm && mv nodeadm /usr/local/bin/

# SELinux configuration (if needed)
semanage permissive -a container_t
%end
```

#### RHEL containerd Installation Notes

On RHEL, you must use the `--containerd-source docker` option. The distribution default source is not supported:

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# Incorrect installation method (will fail)
# sudo nodeadm install 1.31 --credential-provider ssm
```

#### Large-Scale Environments: Satellite/Foreman Integration

For large-scale RHEL deployments, use Red Hat Satellite or Foreman for:
- Centralized Kickstart template management
- Package repository mirroring
- Provisioning workflow automation

### Amazon Linux 2023

Amazon Linux 2023 uses cloud-init based configuration.

```yaml
#cloud-config
hostname: hybrid-node
users:
  - name: ec2-user
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAA...

packages:
  - curl
  - jq

runcmd:
  - curl -OL https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
  - chmod +x nodeadm && mv nodeadm /usr/local/bin/
```

> **AWS Support Note**: When running Amazon Linux 2023 outside EC2 (on bare metal), AWS Support Plans do not apply. Only community support is available.

### Bottlerocket on VMware (Reference)

Bottlerocket is only supported in VMware environments (v1.37.0+, x86_64 only).

- Uses `settings.toml` instead of nodeadm for configuration
- govc deployment workflow: clone template → inject user-data → power on

For detailed Bottlerocket TOML configuration, refer to [04-node-bootstrap.md](./04-node-bootstrap.md).

## Credential Provider Configuration Comparison

### nodeadm-Based Configuration (Ubuntu/RHEL/AL2023)

```yaml
# nodeconfig.yaml - SSM method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
```

```yaml
# nodeconfig.yaml - IAM Roles Anywhere method
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: us-west-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:111122223333:trust-anchor/...
      profileArn: arn:aws:rolesanywhere:us-west-2:111122223333:profile/...
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

### Bottlerocket-Based Configuration (VMware)

```toml
# settings.toml - SSM method
[settings.hybrid.ssm]
activation-code = "<activation-code>"
activation-id = "<activation-id>"

[settings.kubernetes]
cluster-name = "my-cluster"
```

```toml
# settings.toml - IAM Roles Anywhere method
[settings.hybrid.iam-roles-anywhere]
trust-anchor-arn = "arn:aws:rolesanywhere:..."
profile-arn = "arn:aws:rolesanywhere:..."
role-arn = "arn:aws:iam::..."
certificate-path = "/etc/eks/pki/node.crt"
private-key-path = "/etc/eks/pki/node.key"
```

### Credential Provider Selection Guide

| Condition | Recommended Provider |
|-----------|---------------------|
| No PKI infrastructure | SSM |
| Existing PKI infrastructure | IAM Roles Anywhere |
| Custom node names needed | IAM Roles Anywhere |
| Air-gapped environment | IAM Roles Anywhere |
| Simple setup, internet available | SSM |

## Large-Scale Provisioning Automation

### PXE Boot Infrastructure Setup

```
┌─────────────────────────────────────────────────────────┐
│                    PXE Boot Server                       │
├─────────────────────────────────────────────────────────┤
│  DHCP Server                                            │
│  ├── IP address allocation                              │
│  ├── next-server: TFTP server address                   │
│  └── filename: pxelinux.0                              │
├─────────────────────────────────────────────────────────┤
│  TFTP Server                                            │
│  ├── pxelinux.0 (bootloader)                           │
│  ├── vmlinuz (kernel)                                   │
│  └── initrd.img (initial RAM disk)                     │
├─────────────────────────────────────────────────────────┤
│  HTTP Server                                            │
│  ├── OS installation images                             │
│  ├── Autoinstall/Kickstart config files                │
│  └── nodeadm binary                                     │
└─────────────────────────────────────────────────────────┘
```

### Ansible Automation Playbook

```yaml
# provision-hybrid-nodes.yaml
---
- hosts: hybrid_nodes
  become: true
  vars:
    k8s_version: "1.31"
    cred_provider: "ssm"
    cluster_name: "my-cluster"
    region: "us-west-2"

  tasks:
    - name: Download nodeadm
      get_url:
        url: https://hybrid-assets.eks.amazonaws.com/releases/latest/bin/linux/amd64/nodeadm
        dest: /usr/local/bin/nodeadm
        mode: '0755'

    - name: Install EKS components
      command: >
        nodeadm install {{ k8s_version }}
        --credential-provider {{ cred_provider }}
        {% if ansible_distribution == 'RedHat' %}--containerd-source docker{% endif %}
      args:
        creates: /usr/bin/kubelet

    - name: Deploy node configuration
      template:
        src: nodeconfig.yaml.j2
        dest: /etc/eks/nodeconfig.yaml
        mode: '0600'

    - name: Initialize node
      command: nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
      register: init_result
      changed_when: init_result.rc == 0
```

For detailed fleet management information, refer to [07-node-lifecycle.md](./07-node-lifecycle.md).

## Migration Strategies

### VMware → Bare Metal + EKS Hybrid Nodes

#### Phase 1: Build Parallel Infrastructure
- Deploy EKS cluster and hybrid node infrastructure alongside VMware
- Configure network connectivity (Direct Connect/VPN)
- Bottlerocket on VMware can coexist during the transition period

#### Phase 2: Containerize Workloads
- Migrate VM-based workloads to containers
- Configure CSI drivers before migrating stateful workloads
- Consider migrating databases to AWS managed services

#### Phase 3: Network Transition
- Transition from NSX-T to Cilium BGP
- Migrate load balancer and ingress configurations
- Update DNS records

#### Phase 4: Decommission VMware
- Verify all workloads have been migrated
- Terminate VMware licenses
- Recycle or decommission hardware

### OpenShift → EKS Hybrid Nodes

#### Concept Mapping

| OpenShift | EKS Hybrid Nodes |
|-----------|-----------------|
| Route | Ingress / Gateway API |
| SCC (Security Context Constraints) | PSS (Pod Security Standards) |
| OLM (Operator Lifecycle Manager) | Helm / EKS Add-ons |
| MachineSet | nodeadm + Ansible |
| ImageStream | ECR |
| BuildConfig | External CI/CD (CodeBuild, GitHub Actions) |
| DeploymentConfig | Deployment (standard Kubernetes) |

#### Workload Migration Checklist

- [ ] Convert Routes to Ingress or Gateway API
- [ ] Map SCCs to PSS for Pod security configuration
- [ ] Replace OLM-managed Operators with Helm Charts or EKS Add-ons
- [ ] Change ImageStream references to ECR image URLs
- [ ] Reconfigure BuildConfigs as GitHub Actions/CodeBuild pipelines
- [ ] Convert DeploymentConfigs to standard Deployments
- [ ] Review service accounts and RBAC settings

#### Phased Migration

1. **Assessment Phase**: Create inventory of current OpenShift workloads
2. **Pilot Phase**: Migrate non-critical workloads to EKS Hybrid Nodes
3. **Transition Phase**: Sequentially migrate critical workloads
4. **Completion Phase**: Decommission OpenShift cluster

## Post-Installation Verification

```bash
#!/bin/bash
# verify-bare-metal.sh

echo "=== OS Level Verification ==="
# Check OS version
cat /etc/os-release

# Check kernel version
uname -r

# Check containerd status
systemctl status containerd

# Check nodeadm version
nodeadm version

echo "=== EKS Integration Verification ==="
# Install and initialize
sudo nodeadm install 1.31 --credential-provider ssm
sudo nodeadm init --config-source file://nodeconfig.yaml

# Verify node from cluster
kubectl get nodes -l eks.amazonaws.com/compute-type=hybrid

# Check node details
kubectl describe node <node-name> | grep -A 5 "Labels:"
```

For detailed bootstrap process information, refer to [04-node-bootstrap.md](./04-node-bootstrap.md).

## Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| PXE boot failure | Node doesn't boot from network | Check DHCP/TFTP config, BIOS boot order, network cable |
| Autoinstall timeout | Ubuntu install hangs | Verify cloud-init YAML syntax, check HTTP server accessibility |
| Kickstart error | RHEL install fails | Validate ks.cfg syntax, check media accessibility |
| Ubuntu 24.04 containerd | Pods won't terminate | Update containerd to v1.7.19+, reboot for AppArmor |
| RHEL containerd | Installation fails | Use `--containerd-source docker` flag |
| nodeadm init fails | Connection timeout | Verify VPN/DX connectivity, check firewall ports |

---

< [Previous: Operations and Maintenance](./08-operations.md) | [Table of Contents](./README.md) | [Next: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
