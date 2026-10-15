# Amazon VPC CNI

> **审查基线**：VPC CNI / Helm chart 1.23.0；network policy agent 1.4.1。
> **最后更新**：October 12, 2026。
>
> **当前 EKS add-on 列表**：AWS 为 Kubernetes 1.31–1.37 列出 `v1.23.1-eksbuild.1`。
>
> **示例版本固定**：以下配置示例使用 upstream/Helm 1.23.0。Upstream、Helm 和 EKS `eksbuild` 版本是不同的标识符。请检查实际集群版本和 Region 的可用性。

## 目录

- [VPC CNI 概述](#vpc-cni-overview)
- [网络模型](#networking-model)
- [安装和配置](#installation-and-configuration)
- [IP 地址管理](#ip-address-management)
- [Network Policy 支持](#network-policy-support)
- [高级功能](#advanced-features)
- [故障排除](#troubleshooting)
- [最佳实践](#best-practices)

## VPC CNI 概述

Amazon VPC CNI 为标准 EKS EC2 节点提供 VPC 原生 Pod 网络。本指南中的 `aws-node` DaemonSet 命令面向该安装方式。Auto Mode 以节点服务形式运行托管网络组件；Fargate 和 Windows 使用不同的管理路径。在将 EC2/Linux 指令应用于其他计算模式之前，请参阅[概述](README.md)。

Pod 使用可由 VPC 路由的地址，无需 overlay 封装。路由、安全组、Network Policy、ENI/IP 限制和应用行为仍会决定连通性和性能。EKS 支持 **IPv4 或 IPv6 Pod/Service 寻址**，在创建集群时选择；它不支持双栈 Pod 或 Service。双栈 VPC 或 IPv6 Pod 的 IPv4 出站辅助接口是不同的概念。

### 架构

| 组件 | 职责 |
|---|---|
| Container runtime / CNI binary | Runtime 为 Pod sandbox 调用 CNI；AWS plugin 请求地址并配置其 network namespace。 |
| IPAMD | 在 Linux EC2 节点上维护地址池并管理所需的普通 ENI/IP。 |
| EKS network policy controller / node agent | 托管 controller 解析 policy endpoint；启用后，`aws-eks-nodeagent` 使用 eBPF 执行受支持的 policy。 |
| VPC resource controller | 在各自的前提条件下管理 branch/trunk interface 和 Windows 地址分配等功能。 |

原先的图表将 CNI binary 标记为由 kubelet 直接调用。当前 Kubernetes 将 CNI 管理委托给 container runtime。

### IP 分配模式

| 属性 | Secondary IPv4 addresses | Prefix delegation |
|---|---|---|
| 分配 | ENI 上的单独 secondary address | 带有 16 个地址的 IPv4 `/28` prefix；IPv6 使用 `/80` prefix |
| 容量 | 受 interface/address slot 和 kubelet 设置限制 | 每个 slot 有更多地址，受支持硬件、可用 prefix 及 kubelet/resource 限制影响 |
| 分配权衡 | 精细的地址分配 | 一次分配一个块；warm target 可以保留未使用的地址 |
| 选择 | 根据兼容性和测得的需求使用 | 验证 Nitro 支持、subnet 碎片化、workload churn 和功能组合 |

Prefix delegation 并非大型集群的通用要求，也无法在耗尽的 subnet 中制造地址空间。

## 网络模型

### ENI 架构

对于普通 secondary-IPv4 模式，每个 ENI 都有一个 primary address 和可供 CNI 使用的额外地址。Primary ENI 还承载节点的 primary address。额外的 ENI 可以提供更多 secondary Pod address。Custom networking 会改变哪些 interface/subnet 提供 Pod address；prefix 和 branch-ENI 模式有不同的分配规则。

```text
Linux EC2 node — ordinary secondary-IPv4 illustration
├── Primary ENI: node primary IP + secondary IPs for Pods
├── Additional ENI: its primary IP + secondary IPs for Pods
└── Additional ENI: its primary IP + secondary IPs for Pods
```

### Instance type ENI/IP 限制

| Instance type | Max ENIs | 每个 ENI 的 IPv4 slot | Legacy secondary-IP bootstrap maxPods |
|---|---|---|---|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |
| m5.8xlarge | 8 | 30 | 234 |

历史计算公式为 **`ENIs × (IPv4 slots per ENI − 1) + 2`**。其中 `+2` 代表该 bootstrap 计算中的两个 host-network system Pod；对于 m5.large，`3 × 9 + 2 = 29`。这并不意味着所有当前部署始终恰好有两个 host-network Pod。

这些是 legacy bootstrap 值，并非当前通用的 Pod 密度建议。Prefix delegation、custom networking、branch interface、multiple network card、CPU/memory 和 kubelet `maxPods` 都会产生影响。对于少于 30 vCPU 的 instance，EKS managed node group 将 `maxPods` 限制为 110，否则为 250。请检查实际节点的 allocatable capacity。

### Prefix delegation

适用于 Linux IPv4 prefix 模式的 EKS managed add-on 配置片段如下：

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

请使用下面的管理流程，将其与预期的 add-on 配置合并。对于 Helm 管理的安装，等效的 `env` mapping 应位于 Helm values 中。直接编辑 `kubectl set env` 可能会被所选 manager 调和。

IPv4 分配需要合适的连续 `/28` block，而不仅是正数的 `AvailableIpAddressCount`。请验证 subnet reservation/fragmentation 及受支持的 Nitro instance。启用 prefix 不会自动提高每个现有 kubelet 的 Pod limit，也不会提高 branch-ENI Pod limit。

## 安装和配置

### 确立所有权和兼容性

请使用面向目标集群的已配置 AWS CLI 凭证和 Kubernetes context。先执行读取操作：

```bash
EKS_REGION=ap-northeast-2
CLUSTER_NAME=my-cluster
KUBERNETES_MINOR="$(aws eks describe-cluster --region "$EKS_REGION" \
  --name "$CLUSTER_NAME" --query cluster.version --output text)"
aws eks describe-addon-versions --region "$EKS_REGION" \
  --addon-name vpc-cni --kubernetes-version "$KUBERNETES_MINOR"
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system get daemonset aws-node -o yaml
```

`describe-addon` 返回的 EKS `ResourceNotFoundException` 并不能证明未安装 CNI：它可能是 self-managed。选择**一个** manager 前，请检查现有 DaemonSet、ServiceAccount、Helm release、配置和 IAM 模型。Auto Mode networking 不通过此流程安装。

### 现有 EKS Managed Add-on

导出现有设置，并检查所选兼容 build 的 schema：

```bash
umask 077
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni > vpc-cni-before.json
jq -r '.addon.configurationValues // "{}"' vpc-cni-before.json > vpc-cni-config.json
: "${VPC_CNI_ADDON_VERSION:?Select a compatible EKS add-on build from the metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" \
  --addon-name vpc-cni --addon-version "$VPC_CNI_ADDON_VERSION"
```

检查所需的中间升级版本和 release 变更。编辑 `vpc-cni-config.json` 以保留预期的现有配置，并且仅纳入选定的变更。不要假定部分 payload 或 conflict flag 会自动保留每项设置。确认 CNI 的 IAM permission 及其配置的 IRSA/Pod Identity role；IPv6 需要相应的 permission。

对于已管理的 add-on，经审查的更新可以使用：

```bash
set -eu
VPC_CNI_UPDATE_ID="$(aws eks update-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json --resolve-conflicts PRESERVE \
  --query update.id --output text)"
aws eks describe-update --region "$EKS_REGION" --name "$CLUSTER_NAME" \
  --addon-name vpc-cni --update-id "$VPC_CNI_UPDATE_ID"
```

`PRESERVE` 是一个明确的 conflict-handling 选择；请验证生成的 environment、image 和行为。重新检查已捕获的 update ID，直至其状态为 `Successful`；若为 `Failed` 或 `Cancelled`，请在继续之前检查错误。之后再检查生成的 add-on 和 DaemonSet：

```bash
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system rollout status daemonset/aws-node --timeout=10m
```

已接受的 API request 或较早 DaemonSet 的 ready state，并不能证明此次更新和网络验证已完成。

对于安装/所有权准备后缺失的 managed add-on，create operation 是独立的：

```bash
aws eks create-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json
```

不要反复调用 `create-addon` 来开启单项功能，也不要在没有迁移计划的情况下，对现有的定制安装强制使用 `OVERWRITE`。

### Helm 管理的安装

固定整个 chart 的版本，它也会选择匹配的 init 和 policy-agent component。仅覆盖两个 image tag 不会更新 chart 的其余部分：

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm show values eks/aws-vpc-cni --version 1.23.0 > chart-defaults.yaml
helm template aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml > rendered-cni.yaml
```

为实际 IP family、CNI ServiceAccount/IAM 和选定功能准备 `helm-values.yaml`。本指南的基本 Linux 示例使用 IPv4。应用前请审查渲染后的 resource：

```bash
helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml --wait --timeout 10m
```

这些命令假设是全新安装或 Helm 管理的安装。现有的 EKS-managed 或 bootstrap-owned resource 需要经规划的 ownership migration。EKS partition/registry access 和 image-pull 前提条件也必须与环境匹配。

### 重要配置值

| 设置 | 含义 | 基线/默认值区别 |
|---|---|---|
| `WARM_IP_TARGET` | 新普通 Pod assignment 所需的空闲地址数 | 默认未设置；并非硬性最大值 |
| `MINIMUM_IP_TARGET` | 已分配地址总数的下限 | 默认未设置；使用时与正数 warm-IP target 配对 |
| `WARM_ENI_TARGET` | 所需的 warm ENI capacity | 发布默认值：1；IP target 会覆盖它 |
| `WARM_PREFIX_TARGET` | 所需的空闲 IPv4 prefix | 已发布 chart/manifest 设置为 1；bare daemon 文档表示未设置 |
| `ENABLE_PREFIX_DELEGATION` | 选择 prefix allocation | Linux chart 默认值：`"false"` |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | 选择 custom-networking 行为 | 默认值：`"false"` |
| `ENI_CONFIG_LABEL_DEF` | 选择 ENIConfig 的 node label key | Daemon 默认值：`k8s.amazonaws.com/eniConfig`；基于 zone 的示例会覆盖它 |
| `ENABLE_POD_ENI` | 启用 EC2 Pod-ENI integration | 默认值：`"false"`；仍需满足其他 SGPP 前提条件 |
| `POD_SECURITY_GROUP_ENFORCING_MODE` | SGPP routing/SNAT/security-group 行为 | 默认值：`strict` |
| `NETWORK_POLICY_ENFORCING_MODE` | 配置新 Pod rule 期间的 Network Policy 行为 | 默认值：`standard` |

两个 enforcing-mode 设置控制不同的系统。EKS 配置 payload 中的 environment value 是 string。

### Custom Networking (ENIConfig)

在预期 VPC/AZ 中创建实际的 Pod subnet 和 security group，然后引用其 ID：

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
  - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  subnet: subnet-0abcdef0123456789
  securityGroups:
  - sg-0123456789abcdef0
```

启用 custom networking 并使用节点的实际 zone label：

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

明确的 ENIConfig node annotation 优先于 label。仅有 ENIConfig object 并不会启用 custom networking。请规划 routing、DNS/security rule、地址容量以及 workload/node transition；当前 Pod 不会仅因存在新的 CIDR 或 ENIConfig 就迁移到新的 subnet。

## IP 地址管理

### Warm-pool 调优

使用测得的 Pod demand 和 churn、可用地址空间及 EC2 API limit。这些是备选示例 target，不是仅基于集群规模的建议：

```json
{
  "env": {
    "WARM_IP_TARGET": "2",
    "MINIMUM_IP_TARGET": "4"
  }
}
```

```json
{
  "env": {
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

`MINIMUM_IP_TARGET` 是总分配下限；`WARM_IP_TARGET` 以空闲地址为目标。它们优先于 ENI/prefix warm-target 策略。使用 prefix delegation 时，分配仍以 prefix 大小的单位进行。更多 warm capacity 可以减少 allocation wait，但会消耗地址，激进的变更可能增加 API call。

### 添加 Secondary CIDR

先检查现有关联、connected-network overlap、VPC CIDR restriction 和 subnet/routing requirement：

```bash
VPC_ID=vpc-0123456789abcdef0
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

以下内容使用示例 ID 和地址空间；仅将其作为经审查 VPC plan 的一部分执行：

```bash
aws ec2 associate-vpc-cidr-block --region "$EKS_REGION" \
  --vpc-id "$VPC_ID" --cidr-block 100.64.0.0/16
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

在其中创建 subnet 前，确认新的 CIDR association 已为 **associated**，而非仍在 associating：

```bash
aws ec2 create-subnet --region "$EKS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 100.64.0.0/19 --availability-zone ap-northeast-2a
```

该 subnet 还需要其预期的 route table、security rule 和 CNI selection。在规划的 transition 前，现有 Pod 会保留当前网络。RFC 6598 `100.64.0.0/10` 是 shared address space，而不是全局唯一的 private capacity；请检查与每个 connected environment 的 overlap。

### IPv6 集群配置

IP family 在创建集群时选择，之后无法更改。官方 `eksctl` interface 使用**配置文件**，而不是 `--ip-family` flag。Schema 示例为：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-example
  region: ap-northeast-2
  version: '1.35'
kubernetesNetworkConfig:
  ipFamily: IPv6
iam:
  withOIDC: true
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
managedNodeGroups:
- name: linux-nitro
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  privateNetworking: true
```

替换示例 version/Region，选择受支持的 node image，并在创建前审查 VPC endpoint/access 和 IAM setting。此处省略的 add-on version 会通过受支持的 EKS/eksctl 路径解析；对于受控部署，请检查并固定所需的兼容 build。`iam.withOIDC` 以及 managed add-on/node group 反映了记录在案的 eksctl IPv6 前提条件。

```bash
eksctl create cluster --config-file ipv6-cluster.yaml
```

本次审查未创建集群。本地 CLI help/schema 检查使用 eksctl 0.229.0；它们不是对 networking、IAM 或 Region 中可用 build 的实时验证。

IPv6 需要受支持的 Linux Nitro/Fargate 路径和 prefix allocation；不支持 Windows。IPv6 Pod 可能有一个仅出站的 IPv4 helper interface。Policy agent 文档说明，primary interface 上的 IPv6 policy 不会保护该 helper 的 IPv4 traffic。如果设计要求移除此路径，请审查 `ENABLE_V4_EGRESS`、dependency 和 Pod rollout，而不要假设仅 IPv6 policy 就会阻止它。

## Network Policy 支持

### 原生执行

标准原生 eBPF policy support 于 VPC CNI 1.14 中引入。当前 EKS 文档将 VPC CNI 1.21.0 或更高版本列为同时支持标准 `NetworkPolicy` 和 Admin `ClusterNetworkPolicy`（[EKS network policy requirements](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)）；已审查的 1.23 baseline 仍必须与集群和平台匹配。

```json
{
  "enableNetworkPolicy": "true"
}
```

`"enableNetworkPolicy": "true"` 是文档化的 string-valued configuration。受支持的 EC2 Linux node 可以使用此实现；Fargate 和 Windows 不使用其 enforcement。Auto Mode 有自己的托管实现。EKS `ClusterNetworkPolicy` Admin/Baseline control 和 Auto Mode DNS `ApplicationNetworkPolicy` 是 extension，而不是标准 `NetworkPolicy` 的别名。

在 standard mode 中，新 Pod 在解析 policy rule 时初始允许流量。可以有意选择更严格的启动行为：

```json
{
  "enableNetworkPolicy": "true",
  "env": {
    "NETWORK_POLICY_ENFORCING_MODE": "strict"
  }
}
```

Strict mode 要求在 workload 启动前，为 DNS 和其他所需流量提供正确的 policy coverage。它不会配置 SGPP 独立的 `POD_SECURITY_GROUP_ENFORCING_MODE`。

### NetworkPolicy 示例

前提条件：`app` namespace 包含 controller-managed frontend/backend workload；backend Pod 监听 TCP 8080。AWS 当前文档将 `metadata.ownerReferences` 列为可靠 enforcement 的重要条件，并要求 Service/container port number 匹配（对于 named port，还需名称匹配）。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

源 Pod selector 仅限于同一 namespace。该 rule 隔离选中的 backend ingress，并允许匹配的 frontend traffic 访问 8080；它不会拒绝 backend egress，也不会验证 application user。请考虑其他匹配 policy 和 Admin-tier 行为。使用 Deployment/Job-managed Pod 验证允许和拒绝的 flow，而不要依赖独立的 diagnostic Pod。

### 验证和诊断

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-eks-nodeagent --tail=200
kubectl get networkpolicy -A
kubectl get policyendpoints.networking.k8s.aws -A
```

这些是 **node-agent** log；policy controller 在 EKS-managed control plane 中运行。PolicyEndpoint object 是生成的 state，不应随意编辑/删除。

在已获授权且安装了 policy CLI 的 Linux node 上：

```bash
sudo /opt/cni/bin/aws-eks-na-cli ebpf progs
sudo /opt/cni/bin/aws-eks-na-cli ebpf maps
```

该工具是 `aws-eks-na-cli`，而不是 `ebpf-sdk list-maps`。检查受影响节点，并区分 process log、已配置的 policy-event log 和 CloudWatch delivery。启用外部 log delivery 还需要相应的 IAM/configuration。

## 高级功能

### Pod 的 Security Group

所选 security group 必须已经存在，并具有适当的 DNS、API、application 和 return-path rule：

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0
    - sg-0abcdef0123456789
```

选择 standard SGPP 行为的一个 **EC2** 配置示例为：

```json
{
  "env": {
    "ENABLE_POD_ENI": "true",
    "POD_SECURITY_GROUP_ENFORCING_MODE": "standard"
  }
}
```

这不是完整的 SGPP 安装。请验证受支持的 trunking instance type、集群 role 的 VPC resource-controller permission、CNI permission、subnet capacity 以及相关 EKS 前提条件。T-family instance 并不会仅因基于 Nitro 就支持 trunking。新建/重建的选中 Pod 会获得预期配置。

托管 resource controller 会附加一个**额外的 trunk ENI**，并将 branch ENI 与之关联。Trunk 不是节点的 primary `eth0` ENI。选中的 Pod 使用带有其 security group 的 branch interface；prefix delegation 不会增加 branch-Pod limit。Fargate security group 使用独立的托管路径。

| 模式 / 功能 | 需要验证的结果 |
|---|---|
| SGPP `strict` | Branch security-group 行为且不进行 Pod source NAT；NodeLocal DNSCache 和带有 `externalTrafficPolicy: Local` 的 instance-target LoadBalancer/NodePort 存在记录在案的限制 |
| SGPP `standard` | 支持记录在案的组合 policy/DNS 路径；使用默认 external-SNAT 行为时，VPC 外流量使用节点 primary address/security group |
| Custom networking 加 SGPP | Pod security group 优先于 ENIConfig security group |
| IPv6 | EKS service guide 在其 version/platform 条件下支持，包括 EC2 CNI 1.16+；较旧 README feature-table 中的 “No” 单元格不得覆盖该详细指南 |
| Windows / Auto Mode | 不支持此 SGPP 机制；Auto Mode 有单独的 node-class networking control |

模式变更会影响新启动的 Pod；请规划重建并验证 traffic path。不要假定 SNAT 后相同的 security group 管理每个 packet。

### Multiple Interface 和 Multus

VPC CNI 1.20+ 为具有 multiple network card 的合适 instance 提供原生 multi-NIC support。其 `ENABLE_MULTI_NIC` 和 Pod NIC configuration 与 Multus 不同，应用必须使用额外 interface 才能获得其好处。

Multus 是 meta-plugin。AWS 受支持的 Multus arrangement 将 VPC CNI 用作**primary delegate**；将 VPC CNI 用于 higher-order interface 不受支持。额外 interface 需要各自兼容的 plugin、地址 assignment 和 lifecycle management。

| Additional-interface requirement | 原因 |
|---|---|
| 专用且可识别的 interface | 硬编码的 `eth1` 可能指向由 IPAMD 管理的 interface |
| 额外 ENI 上的 `node.k8s.amazonaws.com/no_manage=true` | 阻止 VPC CNI 管理 Multus interface |
| AWS 分配的/可路由地址以及正确的 subnet/SG/route | 任意的 `192.168.1.0/24` 分配并不会自动在 EC2 ENI 上有效 |
| 协调的 IPAM | 共享的 `host-local` range 可能在不同 node 上分配重复地址 |
| Interface-specific policy test | 额外 interface 和 IPv4 helper path 不会自动被所有 primary-interface policy 覆盖 |

NetworkAttachmentDefinition 的 `spec.config` 包含所选 CNI JSON，包括其受支持版本、plugin、实际 parent interface 和 IPAM configuration。先前通用的 `ipvlan`/`eth1`/`host-local` manifest 遗漏了上述前提条件，已由这些实现要求替代。本指南并不声称部署了 Multus/IPAM solution。

### Windows

Windows 使用 VPC resource-controller IPAM path。请准备集群 role permission、Windows node-role authentication/access entry（适用时为 `EC2_WINDOWS`），以及为 CoreDNS 提供的 Linux/Fargate capacity。Windows Fargate、Auto Mode、Hybrid Nodes、IPv6、custom networking、SGPP 和原生 VPC-CNI Network Policy 均有记录在案的限制。

Controller 生成的 ConfigMap 必须包含以下 Windows IPAM 条目。这展示了所需 data，而不是覆盖 manager-owned ConfigMap 的指令：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-windows-ipam: 'true'
```

对于 **Helm-managed** 安装，Windows prefix target 使用与 Linux 不同的 key：

```yaml
enableWindowsIpam: 'true'
enableWindowsPrefixDelegation: 'true'
warmWindowsPrefixTarget: 1
warmWindowsIPTarget: 0
minimumWindowsIPTarget: 0
```

检查匹配 build 的 schema、field ownership 和生成的 ConfigMap。不要假定 Helm value 会被原样接受为 EKS add-on configuration property。Windows chart flag 映射到 `enable-windows-ipam` 和 `enable-windows-prefix-delegation`；此处 warm-target field 也专用于 Windows。

在满足这些前提条件并完成 AMI/version 检查后，node-group command 可使用：

```bash
eksctl create nodegroup --region "$EKS_REGION" --cluster "$CLUSTER_NAME" \
  --name windows-example --managed --node-type m5.large --nodes 2 \
  --node-ami-family WindowsServer2022FullContainer
```

Windows secondary-IP mode 通常使用一个 ENI 及其 address-slot limit，而非 Linux multi-ENI formula。Prefix delegation 和实际 kubelet limit 需要单独进行 sizing。

## 故障排除

### IP 分配和调度

检查 Pod event，以区分 scheduling failure 与 sandbox/CNI allocation failure：

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=300
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatablePods: .status.allocatable.pods}'
SUBNET_ID=subnet-0123456789abcdef0
aws ec2 describe-subnets --region "$EKS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount}'
```

`allocatablePods` 是 kubelet scheduling capacity，而不是当前 IP utilization。Subnet available-address count 并不显示是否有可用的连续 `/28`。选择补救措施前，请检查 IPAMD log、allocation mode、warm target、ENI limit、API error 和受影响节点。

### ENI Count

```bash
INSTANCE_ID=i-0123456789abcdef0
aws ec2 describe-instances --region "$EKS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AttachedENIs:length(NetworkInterfaces)}'
aws ec2 describe-instance-types --region "$EKS_REGION" --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.{MaxENI:MaximumNetworkInterfaces,IPv4PerENI:Ipv4AddressesPerInterface}'
```

原始 projection 统计的是嵌套 interface list，而不是 interface 本身。更正后的 query 会报告每个 instance 的 count。Multiple card、unmanaged/trunk interface 和 instance-specific limit 仍需要解读。

### Introspection 和 Metrics

选择受影响节点的实际 `aws-node` Pod，并保持此 forwarding session 打开：

```bash
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
AWS_NODE_POD=aws-node-example
kubectl -n kube-system port-forward "pod/$AWS_NODE_POD" 61678:61678 61679:61679
```

在另一个本地 terminal 中：

```bash
curl --fail http://127.0.0.1:61679/v1/enis
curl --fail http://127.0.0.1:61678/metrics
```

IPAMD introspection 默认使用 loopback **61679**；Prometheus metrics 使用 **61678**。`/v1/enis` 不是 metrics endpoint。这些命令通过 Kubernetes forwarding path 使用本地 curl；它们不需要 CNI image 内有 curl binary。

### 更改集群前先分类错误

| 观察结果 | 操作前需调查 |
|---|---|
| `InsufficientFreeAddressesInSubnet` | 实际空闲地址、warm allocation、选定 subnet 和计划的 capacity expansion |
| `InsufficientCidrBlocks` | 连续 prefix 可用性/fragmentation 和 subnet reservation |
| ENI/SG limit error | 特定 quota、instance/interface type 和正在使用的 object；避免移除无关 security group |
| ENI creation failure | 详细 AWS error、CNI credential role、permission/condition、quota 和 API connectivity |
| Waiting for a Pod IP | IPAMD state、controller/API delay、throttling、sandbox event 和 address readiness |

重启 IPAMD、扩大 instance 或授予更多 node-role permission 并不是通用补救措施。先收集证据，并对实际拥有失败 operation 的 component 应用经审查的变更。

## 最佳实践

根据预期 Pod、warm pool、增长和故障/替换重叠来规划 subnet capacity。`/19` 或 RFC 6598 range 是示例 design choice，而非通用要求。关联新 CIDR，创建必要的 subnet/route，并共同规划 CNI/workload adoption。

选择一种 warm-pool 策略。使用 free-IP 和 total-IP target 的 IPv4 prefix 示例为：

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

设置这些 IP target 时，不要将额外的 `WARM_PREFIX_TARGET` 解释为独立的有效 target。监控 allocation failure 和实际 resource constraint，而不是仅从集群规模推断安全性。

### Metrics 和 Alerts

已发布的 IPAMD code 导出 `awscni_total_ip_addresses`、`awscni_assigned_ip_addresses` 和 counter `awscni_no_available_ip_addresses`。Total/assigned gauge 描述的是 **IPAMD allocated pool**，而不是整个 VPC subnet space。较小的 warm target 合理情况下可能产生较高的 assigned/total ratio；cooldown、branch interface、IP family 和 kubelet capacity 需要额外上下文。

Prometheus Operator CRD 和 selector 必须已经配置。对于 Helm-managed CNI，chart 可以使用此 **IPv4-cluster 示例**创建 PodMonitor：

```yaml
podMonitor:
  create: true
  labels:
    release: prometheus
  interval: 30s
  relabelings:
  - sourceLabels:
    - __meta_kubernetes_pod_node_name
    targetLabel: node
  - targetLabel: cluster
    replacement: example-cluster
  - targetLabel: ip_family
    replacement: ipv4
  - targetLabel: job
    replacement: aws-vpc-cni
```

替换示例 cluster label，调整 `release` selector，并如实设置 IP-family label；label 不会检测集群的 family。Chart 会抓取 Agent 的命名 `metrics` port 和已启用 policy agent 的 `agentmetrics` port。EKS-managed add-on 需要独立配置的 scraper/PodMonitor，而不是安装第二个 CNI Helm release。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vpc-cni-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: vpc-cni
    rules:
    - record: vpc_cni:allocated_ipv4_pool_utilization:ratio
      expr: (awscni_assigned_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} / awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"})
        and (awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} > 0)
    - alert: CniHighAllocatedIPv4PoolUtilization
      expr: vpc_cni:allocated_ipv4_pool_utilization:ratio > 0.9
      for: 5m
      labels:
        severity: info
      annotations:
        summary: Most currently allocated IPAMD IPv4 addresses are assigned
        description: This is allocated-pool utilization, not subnet exhaustion. Check
          warm targets, assignment failures and available subnet space.
    - alert: CniIPAssignmentFailures
      expr: increase(awscni_no_available_ip_addresses{job="aws-vpc-cni"}[5m]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: IPAMD could not assign an available IP address
    - alert: CniMetricsScrapeFailed
      expr: up{job="aws-vpc-cni"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A known CNI metrics endpoint cannot be scraped
```

Pool ratio 仅限 IPv4 和正数的观测 denominator。它是信息性调优信号，而不是 subnet exhaustion 的证明。Assignment-failure counter 表示实际失败的 allocation。抓取失败不同于 target 消失；请分别比较预期的 node/component inventory。无数据并不等同于健康的零值。请在实际 monitoring environment 中调优 threshold、label 和 notification routing。

## 参考资料

- [VPC CNI 1.23.0 文档](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [VPC CNI Helm values](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/values.yaml)
- [Chart version 元数据](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/Chart.yaml)
- [已发布 CNI manifest](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/config/master/aws-k8s-cni.yaml)
- [IPAMD 实现](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/ipamd.go)
- [IPAMD introspection server](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/introspect.go)
- [IPAM datastore](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/datastore/data_store.go)
- [IPAMD metric 定义](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/utils/prometheusmetrics/prometheusmetrics.go)
- [Network policy agent 1.4.1](https://github.com/aws/aws-network-policy-agent/blob/v1.4.1/README.md)
- [AWS Helm chart index](https://aws.github.io/eks-charts/index.yaml)
- [EKS Pod 的 security group](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [SGPP 操作注意事项](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [EKS Multus 支持边界](https://docs.aws.amazon.com/eks/latest/userguide/pod-multus.html)
- [EKS Windows networking](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)
- [EKS IPv6 支持](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)
- [eksctl IPv6 配置](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-ip-family.html)
- [CNI IAM 配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [EKS VPC CNI 管理](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS network policy 条件](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [启用 EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Prefix allocation 和 Pod-capacity limit](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)

## 测验

通过 [VPC CNI 测验](../quizzes/networking/01-vpc-cni-quiz.md) 检查您的理解。