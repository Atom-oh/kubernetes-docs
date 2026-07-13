# Bare Metal Server OS インストールと Migration ガイド

< [前へ: Operations and Maintenance](./08-operations.md) | [目次](./README.md) | [次へ: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+
> **最終更新**: February 23, 2026

このドキュメントでは、bare metal servers に EKS Hybrid Nodes をデプロイするための OS インストール方法と、VMware/OpenShift からの migration 戦略について説明します。

## 概要

### Bare Metal を選択する理由

EKS Hybrid Nodes を bare metal servers 上で実行すると、次のメリットがあります。

1. **VMware ライセンスコストの削減**: Broadcom による VMware 買収後、subscription model への移行によりライセンスコストが大幅に増加しました。
2. **OpenShift subscription コストの削減**: Node ごとの Red Hat OpenShift subscription 料金を排除します。
3. **Hypervisor オーバーヘッドの排除**: 仮想化レイヤーなしで workloads を直接実行し、performance を最適化します。
4. **ライセンス管理の簡素化**: 複雑なライセンス契約と audit compliance の負担を軽減します。

### OS Infrastructure Support Matrix

| OS | Bare Metal | VMware | 認証情報 | 設定ツール |
|----|-----------|--------|-------------|-------------|
| Ubuntu 22.04/24.04 LTS | O | O | SSM / IAM RA | nodeadm (YAML) |
| RHEL 8/9 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Amazon Linux 2023 | O | O | SSM / IAM RA | nodeadm (YAML) |
| Bottlerocket v1.37.0+ | X | O (VMware のみ) | SSM / IAM RA | govc (TOML) |

> **注記**: Bottlerocket は VMware environments でのみサポートされます。bare metal servers では、Ubuntu、RHEL、または Amazon Linux 2023 を使用してください。

## コスト比較分析

### ライセンス/Subscription コスト比較

#### VMware vSphere
Broadcom による買収後、VMware は永続ライセンスから subscription model に移行しました。
- Enterprise Plus license: CPU socket あたり年間約 $4,500-8,500
- vSAN や NSX-T などの追加コンポーネントには個別のコストが発生します

#### OpenShift
Red Hat subscription ベース:
- Node あたり年間約 $2,500-5,000（core ベースの subscription）
- Premium support を含みます

#### EKS Hybrid Nodes
- 1 vCPU あたり 1 時間 $0.01（region により異なります）
- 追加ライセンスは不要です

### 規模別の年間コスト比較（32 vCPU Servers）

| 規模 | VMware vSphere (年間) | OpenShift (年間) | EKS Hybrid Nodes (年間) |
|-------|------------------------|-------------------|--------------------------|
| 10 nodes | ~$45,000-85,000 | ~$25,000-50,000 | ~$28,032 |
| 50 nodes | ~$225,000-425,000 | ~$125,000-250,000 | ~$140,160 |
| 100 nodes | ~$450,000-850,000 | ~$250,000-500,000 | ~$280,320 |

> **計算**: EKS Hybrid Nodes = 32 vCPU × $0.01/hour × 8,760 hours = $2,803.20/node/year
>
> **注記**: 上記のコストは見積もりです。実際のコストは、契約条件、region、discounts によって異なる場合があります。

### TCO（Total Cost of Ownership）の考慮事項

ライセンス/subscription コストに加えて、次の要素を考慮してください。
- Operations staff の training コスト
- ライセンス管理と audit compliance のオーバーヘッド
- Technical support と consulting コスト
- Migration コスト（一回限り）

## OS 別 Bare Metal インストール

### 前提条件

#### BIOS/UEFI Settings
- PXE boot priority を設定する
- Secure Boot を無効化するか、signed bootloaders を使用する
- containerd のために virtualization extensions（VT-x/AMD-V）を有効化する

#### Network Infrastructure
- DHCP Server: IP addresses と PXE boot 情報を提供します
- TFTP Server: bootloader と kernel images を提供します
- HTTP Server: OS installation images と configuration files をホストします

#### AWS Packer Templates
bare metal 用の images を作成する場合は、`CREDENTIAL_PROVIDER` environment variable を設定します。

```bash
# Create Qcow2 or Raw format images
export CREDENTIAL_PROVIDER=ssm  # or iam-ra

packer build \
  -var "credential_provider=${CREDENTIAL_PROVIDER}" \
  -var "output_format=raw" \
  bare-metal-template.pkr.hcl
```

### Ubuntu LTS (22.04/24.04)

Ubuntu は、PXE automated installation に Autoinstall（cloud-init ベース）を使用します。

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

#### Ubuntu 24.04 固有の注記

Ubuntu 24.04 では containerd v1.7.19 以降が必要です。そうでない場合は AppArmor profile の変更が必要です（Ubuntu bug #2065423）。

```bash
# Check containerd version
containerd --version

# If version is below 1.7.19, modify AppArmor profile
sudo aa-remove-unknown

# Reboot required to apply changes
sudo reboot
```

> **重要**: AppArmor の変更後は reboot が必要です。reboot しない場合、Pods が適切に終了しない可能性があります。

### RHEL 9

RHEL は、PXE automated installation に Kickstart を使用します。

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

#### RHEL containerd インストールに関する注記

RHEL では、`--containerd-source docker` option を使用する必要があります。distribution default source はサポートされていません。

```bash
# Correct installation method
sudo nodeadm install 1.31 --credential-provider ssm --containerd-source docker

# Incorrect installation method (will fail)
# sudo nodeadm install 1.31 --credential-provider ssm
```

#### 大規模 Environments: Satellite/Foreman 統合

大規模な RHEL deployments では、Red Hat Satellite または Foreman を次の目的で使用します。
- 集中管理された Kickstart template 管理
- Package repository mirroring
- Provisioning workflow automation

### Amazon Linux 2023

Amazon Linux 2023 は cloud-init ベースの configuration を使用します。

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

> **AWS Support に関する注記**: Amazon Linux 2023 を EC2 外部（bare metal 上）で実行する場合、AWS Support Plans は適用されません。Community support のみ利用できます。

### VMware 上の Bottlerocket（Reference）

Bottlerocket は VMware environments（v1.37.0+、x86_64 のみ）でのみサポートされます。

- configuration には nodeadm ではなく `settings.toml` を使用します
- govc deployment workflow: template の clone → user-data の注入 → power on

詳細な Bottlerocket TOML configuration については、[04-node-bootstrap.md](./04-node-bootstrap.md) を参照してください。

## Credential Provider Configuration 比較

### nodeadm ベースの Configuration（Ubuntu/RHEL/AL2023）

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

### Bottlerocket ベースの Configuration（VMware）

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

### Credential Provider 選択ガイド

| 条件 | 推奨 Provider |
|-----------|---------------------|
| PKI infrastructure なし | SSM |
| 既存の PKI infrastructure | IAM Roles Anywhere |
| Custom node names が必要 | IAM Roles Anywhere |
| Air-gapped environment | IAM Roles Anywhere |
| Simple setup、internet 利用可能 | SSM |

## 大規模 Provisioning Automation

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

詳細な fleet management 情報については、[07-node-lifecycle.md](./07-node-lifecycle.md) を参照してください。

## Migration 戦略

### VMware → Bare Metal + EKS Hybrid Nodes

#### Phase 1: 並行 Infrastructure を構築する
- VMware と並行して EKS cluster と hybrid node infrastructure をデプロイする
- Network connectivity（Direct Connect/VPN）を設定する
- VMware 上の Bottlerocket は transition period 中に共存できます

#### Phase 2: Workloads を Containerize する
- VM ベースの workloads を containers に migrate する
- Stateful workloads を migrate する前に CSI drivers を設定する
- Databases を AWS managed services に migrate することを検討する

#### Phase 3: Network Transition
- NSX-T から Cilium BGP に transition する
- Load balancer と ingress configurations を migrate する
- DNS records を更新する

#### Phase 4: VMware を Decommission する
- すべての workloads が migrate されたことを確認する
- VMware licenses を終了する
- Hardware を再利用または decommission する

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

- [ ] Routes を Ingress または Gateway API に変換する
- [ ] Pod security configuration のために SCCs を PSS に map する
- [ ] OLM-managed Operators を Helm Charts または EKS Add-ons に置き換える
- [ ] ImageStream references を ECR image URLs に変更する
- [ ] BuildConfigs を GitHub Actions/CodeBuild pipelines として再設定する
- [ ] DeploymentConfigs を標準 Deployments に変換する
- [ ] Service accounts と RBAC settings を確認する

#### Phased Migration

1. **Assessment Phase**: 現在の OpenShift workloads の inventory を作成する
2. **Pilot Phase**: Non-critical workloads を EKS Hybrid Nodes に migrate する
3. **Transition Phase**: Critical workloads を順次 migrate する
4. **Completion Phase**: OpenShift cluster を decommission する

## インストール後の Verification

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

詳細な bootstrap process 情報については、[04-node-bootstrap.md](./04-node-bootstrap.md) を参照してください。

## Troubleshooting

| 問題 | 症状 | 解決策 |
|-------|---------|----------|
| PXE boot failure | Node が network から boot しない | DHCP/TFTP config、BIOS boot order、network cable を確認する |
| Autoinstall timeout | Ubuntu install がハングする | cloud-init YAML syntax を検証し、HTTP server accessibility を確認する |
| Kickstart error | RHEL install が失敗する | ks.cfg syntax を検証し、media accessibility を確認する |
| Ubuntu 24.04 containerd | Pods が終了しない | containerd を v1.7.19+ に更新し、AppArmor のために reboot する |
| RHEL containerd | Installation が失敗する | `--containerd-source docker` flag を使用する |
| nodeadm init fails | Connection timeout | VPN/DX connectivity を検証し、firewall ports を確認する |

---

< [前へ: Operations and Maintenance](./08-operations.md) | [目次](./README.md) | [次へ: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
