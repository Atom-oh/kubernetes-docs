# Calico 深度解析：Kubernetes 网络与策略

> **示例基线**：Calico Open Source 3.32.2
>
> **最后审查**：October 12, 2026
>
> **最新版本**：Calico 3.33.0 于 October 1 发布，是最新的 Open Source 版本，并已针对 Kubernetes 1.35–1.37 进行测试。
>
> 本系列中的命令仍固定使用 3.32.2，其已测试范围为 1.34–1.36。这些示例尚未针对 3.33.0 进行验证。在选择版本前，请查阅 [3.33.0 发布说明](https://github.com/projectcalico/calico/releases/tag/v3.33.0)和[当前要求](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)。这并非开放式的 `3.29+ / Kubernetes 1.28+` 兼容性保证。

## 概述

Calico 为 Kubernetes 提供网络和网络策略；其他主机与 VM 功能则取决于部署方式和产品版本。本系列涵盖架构、封装与路由、BGP、策略、eBPF、EKS 集成以及运维。请依据[当前要求](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)选择配置，而不是依据没有日期的成熟度或资源使用量排名。

### 2026 年 7 月：用于 Kubernetes 上 VM 的 Calico

Tigera 的[官方公告](https://www.tigera.io/news/tigera-launches-ebpf-powered-calico-for-vms-on-kubernetes-vm-migration-that-doesnt-require-rebuilding-the-network/)日期为 **July 23, 2026**。其中介绍了 VMware 迁移所需的 VM/container 网络、IP 连续性、L2 网桥扩展、策略和可观测性。这是一则产品公告，并不承诺每项宣传的能力都包含在 Calico Open Source 中。请检查准确的版本、拓扑和功能状态：[Enterprise 3.23 发布说明](https://docs.tigera.io/calico-enterprise/latest/release-notes/)仍将 KubeVirt 实时迁移标记为技术预览。营销可用性并不会消除该功能特有的限制。

## 兼容性与功能边界

- Calico 3.32.2 于 August 30, 2026 发布，并已在 Kubernetes 1.34–1.36 上测试。更新的 3.33.0 版本已在 Kubernetes 1.35–1.37 上测试；仅 Kubernetes 1.37 可用并不能证明固定的 3.32.2 示例具有兼容性。
- 通用 Linux 要求为内核 5.10 或更高版本，并具备所需模块。请查阅 eBPF 指南，了解支持的架构、供应商回移补丁及各个功能更高的要求。
- Linux 数据平面包括 iptables、nftables 和 eBPF。默认值取决于安装程序/平台；当前自管 kubeadm operator 安装可默认使用 eBPF。并不存在全面的功能对等保证。
- [适用于 Windows 的 Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)支持指定的 IPv4 VXLAN 和 BGP 配置，但不支持 Linux eBPF、IPIP、IPv6/双栈、WireGuard 或所有 Linux 策略功能。
- Open Source 包含分层策略、Goldmane 流聚合和 Whisker UI。DNS/FQDN 策略、应用层策略及其他高级能力在[产品比较](https://docs.tigera.io/calico/latest/about/calico-product-editions)中存在版本边界。

## Calico 与 Cilium

| 要求 | Calico | Cilium |
|---|---|---|
| Linux 数据平面 | iptables / nftables / eBPF，取决于配置 | eBPF，并针对适用的 L7 功能使用 Envoy |
| Kubernetes NetworkPolicy | 支持，另加 Calico 策略和层级 | 支持，另加 Cilium 策略 |
| L7 / DNS 策略 | 检查 Enterprise/Cloud 许可和功能状态 | HTTP 和 DNS 策略可用；存在协议特定限制 |
| BGP | 在适用网络模式中基于 BIRD 的路由 | BGP 控制平面通告；评估所需路由和拓扑 |
| 可观测性 | Open Source Goldmane/Whisker 和指标；付费功能增加能力 | Hubble 和指标 |
| Windows | 支持的配置存在显著限制 | Cilium 1.20 agents 需要 Linux；不是 Windows beta 数据平面 |
| kube-proxy 替代 | 使用 eBPF 数据平面时可用 | 配置后可用 |
| 多集群 / mesh | 独立功能和集成；取决于版本 | Cluster Mesh 和可选 service-mesh 功能；并非全部在安装时启用 |

两者都可以是生产选择。资源使用量和运维复杂度取决于规则、流量、平台和调优。请在目标环境上验证所需功能。不要仅仅因为它们可在不同环境中工作，就在同一个集群上安装两个主要 CNI。Cilium 的[版本化要求](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)以及本站的 [Cilium service-mesh 指南](../../service-mesh/cilium-service-mesh/README.md)说明了其平台和 mesh 边界。

## 架构

![采用 Kubernetes datastore、可选 Typha、Felix、confd 和 BIRD 的 Calico BGP 部署示意图。](../../.gitbook/assets/en-networking-calico-readme-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-readme-0.html)

该图是示意性的 BGP 部署，而非强制的组件布局。下面的仅策略 EKS 示例使用 Kubernetes datastore，并省略 BIRD/confd。“Control plane”描述的是逻辑角色，而不是在 EKS 托管 control-plane 机器上的位置。Typha 是独立的 Deployment，而不是每节点进程。

| 组件 | 角色和范围 |
|---|---|
| Felix | 在工作负载节点上配置策略和适用的路由 |
| BIRD / confd | 启用该后端时的 BGP 及其配置；在仅策略模式下不存在 |
| Typha | 可选的 datastore 更新缓存/扇出；operator 会随安装扩展副本数，不一定是三个 |
| kube-controllers | Kubernetes 资源协调、同步和清理 |
| Calico CNI / IPAM | 当 Calico 管理网络时负责接口和 Pod 地址管理；在 EKS 示例中，Amazon VPC CNI/IPAM 保留这些职责 |
| Calico API server | 在默认模型中，经由内部 CRD 聚合的 `projectcalico.org/v3` API；原生 v3 CRD 是独立的技术预览 |

使用[架构参考](https://docs.tigera.io/calico/latest/reference/architecture/overview)和实际渲染的工作负载来识别已启用组件。本指南使用 Kubernetes API datastore；基于 etcd 的设计有独立的安装和功能限制。

## 网络模式与 MTU

| 模式 | 封装与路由 | 在 1500-byte IPv4 underlay 上的示例 Pod MTU |
|---|---|---|
| IPIP | IPv4-in-IPv4，通常使用 BGP 路由分发 | 1480 |
| VXLAN | 默认使用 UDP 4789；VXLAN Pod 路由不需要 BGP | 1450 |
| 未封装 | underlay 必须路由 Pod 地址；BGP 是分发路由的一种方式 | 1500 |
| CrossSubnet | 一种 IPIP 或 VXLAN 设置，仅跨节点子网封装 | 仍须为需要它的路径预留所需的隧道开销 |

这些 MTU 只是示例，并非通用常量。IPv6 VXLAN 开销、jumbo underlay、WireGuard 和云路径限制会改变计算结果。IPIP 仅支持 IPv4，而 IPv4 VXLAN 也可用于 IPIP 不适用的场景。请检查 [MTU 配置](https://docs.tigera.io/calico/latest/networking/configuring/mtu)和[overlay 要求](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip)。仅 BGP 可用并不能证明每个 underlay 跳点都能路由 Pod CIDR；同一 L2 邻接不是未封装路由 fabric 的通用先决条件。在选择模式之前，请规划 underlay、端口、地址族和平台。

## EKS：保留 Amazon VPC CNI 并添加 Calico 策略

本示例适用于具有现有且受支持 Amazon VPC CNI 安装的 Linux EC2 节点。它不会替换 Pod 网络。这不是 Auto Mode 或 Fargate 的安装方案。[官方 EKS 指南](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)要求：

1. 在选择 Calico 作为策略引擎之前，禁用 Amazon VPC CNI 的原生网络策略实施；同时运行两者会产生冲突。对于已有保护的集群，请规划并验证策略移交流程，而不是制造无保护的过渡期。
2. 设置 VPC CNI `ANNOTATE_POD_IP=true`，并向其 `aws-node` ServiceAccount 授予对 Pods 的 `patch` 访问权限。请通过已安装的 add-on/配置所有者管理这些设置，以便协调不会将其还原。在应用下面的增量 RBAC 示例前，检查实际的 ServiceAccount 名称。
3. 不要声称对 `ENABLE_V4_EGRESS=true` 的 IPv6 Pods 提供覆盖：Calico EKS 指南明确排除此组合的实施。
4. 仅选择**一种**下方安装方法。这些是全新安装示例，并非用于接管现有 operator 或迁移活跃 CNI 的命令。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-ip-patch
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-ip-patch
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-ip-patch
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

### 方法 A：固定版本的 operator manifests

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
```

### 方法 B：固定版本的 Helm 安装

完成相同的 VPC CNI 前提条件。Calico 3.32 将 CRD 安装与 operator chart 分离；仅安装小型 operator chart 不足以用于全新集群。将以下值保存为 `calico-eks-values.yaml`：

```yaml
installation:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
apiServer:
  enabled: true
```

```bash
set -euo pipefail
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico-crds projectcalico/crd.projectcalico.org.v1 --version v3.32.2   | kubectl apply --server-side -f -
helm install calico projectcalico/tigera-operator --version v3.32.2   --namespace tigera-operator --create-namespace -f calico-eks-values.yaml
```

固定版本的 chart 默认也会启用 Goldmane 和 Whisker。请在渲染后的 manifests 中审查这些组件及访问控制。原生 `projectcalico.org/v3` CRD 是独立的技术预览；这里的示例使用常规内部 CRD 加上聚合 API server。

### 验证，然后测试策略行为

```bash
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl get felixconfigurations.projectcalico.org
```

在依赖实施之前，请检查降级/进行中状态，并使用一次性工作负载测试允许和拒绝的流量。Ready DaemonSet 并不能证明策略有效。在 AmazonVPC 仅策略模式中，空的 Calico IPPools 或缺少 BIRD 会话不一定是故障：AWS 仍提供 Pod IPAM 和网络。

### 完整 Calico 网络及其他安装方法

EKS 上的完整 Calico 网络是独立的新集群设计。官方流程从没有工作负载节点开始，并在添加它们之前更改 CNI；不要在运行中的 VPC CNI 集群上应用 `cni.type: Calico` 片段。请参阅 [EKS 集成](08-eks-integration.md)和官方 EKS 流程。对于没有现有 CNI 的自管集群，请使用[本地部署指南](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises)。直接 manifests 仍是替代方案，但其 namespace、Typha 配置和生命周期与 operator 安装不同。请选择一个所有者，而不要叠加 Helm、operator 和 `calico.yaml` 安装。

## 具有明确范围的策略示例

使用专用的 `calico-demo` namespace。以下 ingress 和 egress 示例仅选择该 namespace；它们并不是全集群 zero-trust 推出。现有 Calico 层级和更早的策略仍可能改变结果。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: calico-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

对等方 `podSelector` 表示位于**同一 namespace**中的 frontend Pods。它不会验证用户身份、允许所有同 namespace 流量或设置 egress 策略。下一个独立示例将 demo namespace 的 egress 限制为指向 UDP/TCP 53 上选定的 CoreDNS Pods，并拒绝其他 egress：

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-dns-only
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: all()
  order: 100
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Deny
```

请先确认实际 DNS endpoints 和 labels。此基于 selector 的示例针对常规 CoreDNS Pods；它不是 NodeLocal DNSCache 或 Auto Mode system-resolver 策略。仅端口 53 无法识别经授权的 DNS server。如果还需要应用 egress，请在启用最终拒绝前设计并测试这些显式允许项。独立的后续允许无法覆盖匹配的较早 Calico Deny。

### FQDN 策略取决于版本

Calico Enterprise/Cloud DNS 策略中使用的 `destination.domains` 字段**不在 Open Source 3.32.2 NetworkPolicy schema 中**。不要将其应用于此 Open Source 安装。对于有授权的部署，请使用[基于域名的策略指南](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)，配置受信任 DNS servers 并允许 DNS 路径。请谨慎限制域名：`*.amazonaws.com` 将是宽泛的允许，而非对某个 AWS account 或 service 的授权。DNS 到 IP 的授权并不等同于验证 HTTP Host 或 TLS 身份。

## 监控与健康状况

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
```

Felix 默认禁用指标。启用此 listener 不会创建 Prometheus scrape job，也不会使其可安全公开；请使用[指标指南](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)配置私有发现和访问控制。`flowLogsFileEnabled` 不是 Open Source FelixConfiguration 字段。请使用受支持的 [Goldmane/Whisker flow-log 路径](https://docs.tigera.io/calico/latest/observability/view-flow-logs)，而不是复制 Enterprise file-log 设置。

| 指标 | 含义 |
|---|---|
| `felix_active_local_endpoints` | 活跃的本地工作负载和主机 endpoints |
| `felix_active_local_policies` | 此节点上 endpoints 的活跃策略 |
| `felix_iptables_rules` | 活跃的 iptables 规则；特定于数据平面 |
| `felix_int_dataplane_failures` | 将被重试的失败数据平面更新 |
| `felix_cluster_num_hosts` | Felix 的全集群主机计数；不要跨每个 Felix 实例求和 |
| `typha_connections_accepted` | 累计接受的连接，而非当前连接数 |
| `typha_connections_active` | 当前打开的客户端连接 |

请参阅 [Felix](https://docs.tigera.io/calico/latest/reference/felix/prometheus)和 [Typha](https://docs.tigera.io/calico/latest/reference/typha/prometheus)指标参考。它们是组件健康/配置指标，并不是通用的拒绝数据包计数器。Felix 健康检查默认使用 localhost:9099；启用时 Typha 健康检查通常使用 9098。检查前请读取已部署的 probes：在笔记本上执行 `curl localhost` 并不会检查节点的 health server。

## 故障排除

```bash
kubectl -n calico-system get pods -o wide
kubectl -n calico-system logs -l k8s-app=calico-node -c calico-node --tail=100
kubectl get installations.operator.tigera.io default -o yaml
kubectl get networkpolicies.networking.k8s.io -A
kubectl get networkpolicies.projectcalico.org -A
kubectl get globalnetworkpolicies.projectcalico.org
kubectl get ippools.projectcalico.org -o wide
```

operator 安装通常使用 `calico-system`；直接 manifests 可使用 `kube-system`。使用完全限定的 API resource 名称来区分 Kubernetes 和 Calico NetworkPolicies。`kubectl get nodes ...status.conditions` 不是 Calico 路由状态命令。BIRD 状态命令仅在启用 BGP 时适用，而 `calicoctl node status` 需要适当的 Calico 节点环境，而不是任意管理员笔记本。

| 症状 | 更改配置前应调查 |
|---|---|
| Pod 没有 IP | 首先确定 IPAM 所有者：仅策略 EKS 中的 VPC CNI 日志/容量，否则为 Calico IPAM |
| 跨节点故障 | 路由、underlay/firewall 权限、MTU 和所选封装；盲目启用隧道可能加剧故障 |
| 策略不匹配 | Endpoint labels、namespaces、方向、层级/顺序、现有策略和实际数据平面 |
| 高 CPU | 流量/规则规模以及指标/profile 证据；迁移至 eBPF 是计划性变更，而非即时的通用修复 |

仅在需要时使用版本匹配的 [calicoctl](https://docs.tigera.io/calico/latest/reference/calicoctl/)，选择实际操作系统/CPU 架构并验证发布 artifact。绝不可仅因缺少 BGP 或 Calico IPAM 状态就推断仅策略故障。

## 深度解析目录

| 部分 | 主题 |
|---|---|
| [1](01-introduction.md) | 简介、项目历史和实验环境设置 |
| [2](02-architecture.md) | 组件、datastore 和数据包流 |
| [3](03-networking-modes.md) | 封装、直接路由和 MTU |
| [4](04-bgp-deep-dive.md) | BGP、路由反射器和外部集成 |
| [5](05-network-policy.md) | NetworkPolicy、层级和策略设计 |
| [6](06-ebpf-dataplane.md) | eBPF 设置、限制和故障排除 |
| [7](07-advanced-topics.md) | 高级网络/安全主题 |
| [8](08-eks-integration.md) | EKS 和 VPC CNI 集成 |
| [9](09-operations.md) | 运维和诊断 |
| [术语表](glossary.md) | 术语 |

[Calico 简介测验](../../quizzes/networking/calico/01-introduction-quiz.md) · [官方文档](https://docs.tigera.io/calico/latest/about/) · [最新版本 3.33.0](https://github.com/projectcalico/calico/releases/tag/v3.33.0) · [示例基线 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2)