# Kubernetes 网络

> **最后更新**：October 16, 2026
>
> **固定示例版本**：Cilium 1.20.3、Calico Open Source 3.32.2、Flannel 0.28.10，以及上游 AWS VPC CNI/Helm chart 1.23.2。
>
> **当前版本信息**：AWS 为 Kubernetes 1.31–1.37 列出了 EKS 管理的 VPC CNI add-on `v1.23.1-eksbuild.1`。Calico 3.33.0 是最新的 Open Source 版本，已在 Kubernetes 1.35–1.37 上测试。更改固定示例版本前，请先查看其发布说明。
>
> 这些版本并非经过联合测试的集群配置。安装前请检查每个产品的 Kubernetes/平台兼容矩阵。

## 概述

Kubernetes 网络是核心基础设施层，负责实现容器化应用之间的通信。本节涵盖从 Kubernetes 网络基础概念到高级 CNI（容器网络接口）解决方案，以及 AWS EKS 环境中的网络模式。

## 学习路径 {#learning-path}

完成初学者课程后，请使用[专家网络学习路径](expert/README.md)，将协议项目、路由策略、EVPN、Linux 性能、云设计和自动化评估串联起来。请先检查每本练习手册的环境、证据和恢复标准。

如果你刚接触 Linux 或网络，请从[初学者课程](beginner/README.md)开始。课程的八节课将 CLI、寻址、DNS、SSH、防火墙、监控和综合实践串联起来。下面的学习路径将在此基础上扩展到协议、内核和集群实现。

从协议概念入手，逐步了解观测方法，然后将它们与容器、集群和云环境中的职责联系起来。根据先修条件选择入门点，并在继续学习前用预期成果检查理解情况。

| 阶段 | 作用 | 先修条件 | 预期成果 | 阅读 / 实践 |
|---|---|---|---|---|
| 协议、寻址、HTTP | 建立术语基础 | 基本命令行使用能力 | 跟踪请求，并区分寻址、传输和应用层行为 | 网络基础[第 1 部分](../basics/06-network-fundamentals-part1.md)、[第 2 部分](../basics/06-network-fundamentals-part2.md)、[第 3 部分](../basics/06-network-fundamentals-part3.md)、[第 4 部分](../basics/06-network-fundamentals-part4.md) |
| Linux 套接字、VFS、数据包路径 | 将 API 与内核联系起来 | TCP/IP 基础 | 区分 FD、套接字缓冲区、窗口和队列 | [内核网络协议栈](../kernel/02-network-stack.md) |
| Linux 网络诊断 | 用证据检验假设 | 套接字和数据包路径概念 | 关联套接字、数据包和应用观测结果 | [诊断实践](07-linux-network-diagnostics.md) · [测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker 和容器网络 | 定位命名空间边界 | Linux 数据包路径和基本诊断 | 说明桥接网络、已发布端口和容器名称解析 | [容器技术](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | 映射集群抽象 | 容器网络 | 跟踪名称经过 Service 到达其端点的过程，并识别 Ingress 的作用 | [Service 和网络](../core/03-services-networking.md) · [实验](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、策略 | 比较不同实现的职责 | Pod 和 Service 路径 | 区分数据包转发、策略实施和可观测性 | [eBPF 基础](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS 网络边界和性能 | 将模型应用于云网络路径 | CNI 概念和测量技能 | 识别 VPC、节点和 AZ 边界，并结合上下文解读测量结果 | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) · [Pod 网络基准测试](06-pod-network-benchmark.md) |

## Kubernetes 网络模型

当前 Kubernetes 模型提供 Pod 网络，使 Pod 可以跨节点直接通信，无需地址转换或代理，**但需遵守有意设置的网络分段**。kubelet 等节点代理必须能够访问所在节点上的 Pod。网络策略、路由和应用监听器仍会决定特定连接能否成功。

普通 Pod 拥有自己的网络命名空间和集群范围地址；同一 Pod 中的容器共享该命名空间和 localhost。Host-network Pod 共享节点网络，而双栈或多网络配置需要更精确地处理地址。重新创建 Pod 时可能分配不同的 IP；在同一 Pod 内重启容器不一定会重新创建其网络沙箱。

| 组件 | 作用 |
|---|---|
| Pod 网络 | 为工作负载网络命名空间之间提供寻址和连接能力 |
| Service/服务发现 | 在端点变化时提供稳定的服务名称或虚拟地址 |
| Ingress/Gateway 实现 | 配置外部入口和应用路由 |
| 网络策略引擎 | 实施所选实现支持的策略 |

这些职责并不构成必须依次经过的串行数据包路径。Service 转换、L7 代理和工作负载策略可能会改变特定请求经过网络的方式。

### Pod 网络

Pod 网络为 Pod 通信提供寻址和路由。下图展示普通 IPv4 Pod；图中连接以适用策略和网络控制允许这些连接为前提。

![两个节点之间普通 IPv4 Pod 的示意性直连路径；连接能力取决于已配置的策略和路由。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

图中地址是普通 Pod 地址的示意值。有意隔离以及 host-network 或多网络配置需要结合各自情况进行解读。

#### Pod 网络实现方式

| 方式 | 说明 | CNI 示例 |
|--------|-------------|-------------|
| **覆盖网络** | 在现有网络上封装流量 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **原生路由** | 使用底层网络中的路由，不进行上述覆盖封装 | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **条件式封装** | 根据已配置的拓扑使用直连路径或封装 | Calico/Flannel/Cilium 支持的模式，各自有不同的先决条件 |

### Service 网络

Service 描述一组逻辑端点（通常是 Pod）以及访问这些端点的方式。ClusterIP 默认提供稳定的虚拟 IP；headless Service 不提供该虚拟 IP，而 ExternalName 使用 DNS CNAME 映射。Service 也可以在没有 Pod selector 的情况下管理端点。

![ClusterIP、NodePort、LoadBalancer 和 ExternalName Service 的典型入口机制；图中区分了 DNS 映射和数据包转发。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

这些是典型的暴露机制，并非安全保证。NodePort 范围和可访问的节点地址均可配置；LoadBalancer 也可以是内部的。ExternalName 返回 DNS 别名，不会创建转发代理。

#### Service 类型特征

在 `default` 命名空间中创建标签匹配 `app: my-app`、并监听所示目标端口的 Pod。NodePort 默认分配范围为 30000–32767，也可以配置。外部可达性仍取决于地址、路由和访问控制。

LoadBalancer 示例明确选择了 **AWS Load Balancer Controller**，并使用 EC2 instance targets 和分配的 NodePort。请先安装/配置该 Controller 及其 IAM/子网先决条件。EKS Auto Mode 使用不同的 Controller/class。此处的端口 443 只是选择了一个 TCP 端口；必须由后端在 8443 上提供 TLS，或在负载均衡器上单独配置 TLS。

这些端口映射展示的是通用 Kubernetes Service API。AWS 当前文档还列出了 EKS 原生网络策略的其他要求：Service 端口必须与容器端口匹配，并且由 Controller 管理、带有 `metadata.ownerReferences` 的 Pod 才能可靠地实施策略。测试该策略实现前，请根据这些要求调整示例。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-nodeport-service
  namespace: default
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
    nodePort: 30080
---
apiVersion: v1
kind: Service
metadata:
  name: my-loadbalancer-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
  namespace: default
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - protocol: TCP
    port: 443
    targetPort: 8443
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: true
```

### Ingress 网络

Ingress 资源需要 Controller 及其数据平面。此 HTTP 示例使用 AWS LBC、`spec.ingressClassName: alb` 和 IP targets。所引用的 `api-v1`、`api-v2` 和 `web-frontend` Service 必须存在于 `default` 中、暴露端口 80，并拥有就绪且 VPC 可路由的 Pod 端点。如有需要，请单独配置 HTTPS/证书。有关安装和 target 先决条件，请参阅 [LBC 指南](03-aws-lb-controller.md)。

Ingress 定义将 HTTP/HTTPS 流量路由到集群内部 Service 的规则。

![将 Ingress 主机/路径逻辑路由到 Service 后端和 Pod。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

方框表示 Ingress 数据平面功能。AWS LBC 会配置 ALB；应用流量不会经过 Controller 的协调过程。根据 target 模式，数据平面可以访问 Pod IP 或 NodePort，而不一定会把 Service 虚拟 IP 当作一个实际的额外跳点经过。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
  namespace: default
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: api-v1
            port:
              number: 80
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: api-v2
            port:
              number: 80
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-frontend
            port:
              number: 80
  ingressClassName: alb
```

## CNI（容器网络接口）

CNI 通过标准化接口，让运行时能够配置容器网络。对于当前 Kubernetes，kubelet 通过 CRI 请求 Pod 沙箱操作，**容器运行时负责管理 CNI**。Kubernetes 1.24 已移除 kubelet 过去用于直接管理 CNI 的标志。

### 运行时和插件职责

| 参与方 | 职责 |
|---|---|
| kubelet | 通过容器运行时接口请求创建/移除沙箱 |
| 容器运行时 | 选择网络配置并调用 CNI 插件链 |
| CNI 插件 | 接收配置，执行 ADD/DEL 和其他支持的操作，并返回结果 |
| IPAM 实现 | 分配/释放地址；可以是委派插件，也可以是特定提供商代理的一部分 |
| 可选节点代理 | 维护特定提供商的路由、策略、IP 池或数据平面状态 |

运行时通过 CNI 接口将配置传递给插件；并非每个插件都必须配备单独的长期运行代理或 IPAM 二进制文件。接口类型也各不相同：veth 对很常见，但并非唯一的实现方式。

## CNI 对比

| 项目 / 范围 | 网络和策略 | 需要区分的特性和限制 |
|---|---|---|
| **Cilium 1.20.3** | eBPF 网络；相关 L7 功能使用 Envoy；Cilium 网络策略和 Hubble | Linux 工作节点数据平面，要求 AMD64/Arm64。Windows CLI 可用不代表支持 Windows CNI。WireGuard/IPsec 和 Beta ztunnel mTLS 的适用范围不同。 |
| **Calico Open Source 3.32.2 示例；当前版本 3.33.0** | 路由/封装选项；iptables、nftables 和 eBPF 选项；有序策略层级以及主机/工作负载策略 | Calico 3.33.0 已在 Kubernetes 1.35–1.37 上测试。升级前请查看其发布说明。Windows 有单独的限制，包括不支持 Linux eBPF 或 WireGuard 数据平面。Whisker/Goldmane 流量可观测性以 Tech Preview 形式提供。付费功能请参阅版本矩阵。 |
| **Flannel 0.28.10** | 主机子网分配和节点间传输；VXLAN、host-gw 和其他后端 | `flanneld` 本身不实施 NetworkPolicy；chart 中可选的 `netpol.enabled` 会部署 SIGs 策略 Controller。WireGuard 是有文档说明的后端；IPsec 属于实验性功能。Windows VXLAN 有特定设置/限制。 |
| **AWS VPC CNI 上游/Helm 示例 1.23.2；EKS add-on `v1.23.1-eksbuild.1`** | VPC 地址分配和 EC2 ENI/前缀；在受支持的 Linux EC2 节点上提供 EKS standard 和 Admin 网络策略功能 | AWS 为 Kubernetes 1.31–1.37 列出了此托管 add-on build；请确认区域可用性和集群的实际版本。EKS Auto Mode 是托管网络实现，并提供额外的 DNS 策略功能。Windows、Fargate、自定义网络、前缀委派和多 NIC 支持各有不同条件。 |
| **原始 Weave Net 项目** | 历史上的覆盖网络实现 | 原始 `weaveworks/weave` 仓库已归档。不要将其描述为新集群中仍在积极维护且受支持的默认选项。 |

### 策略、加密和可观测性

- Cilium 通过适用的 L7 组件和集群范围/主机策略提供 HTTP/DNS 感知策略。其拒绝/允许语义与 Calico 有序 Tier API 不同。
- Calico Open Source 包含分层策略 tier 和主机策略。当前产品矩阵将应用层策略、DNS/FQDN 策略和 Cluster Mesh 列为 Cloud/Enterprise 功能；不应在未说明的情况下将这些功能归属于开源版本。Calico 文档说明的传输中加密使用 WireGuard。
- Amazon EKS 为 Auto Mode 和受支持的 EC2/VPC-CNI 安装提供 `ClusterNetworkPolicy` Admin/Baseline 控制。AWS 描述的 DNS/FQDN `ApplicationNetworkPolicy` 功能适用于 **Auto Mode**。其名称并不意味着当前支持检查 HTTP 方法/正文。
- Flannel 的可选策略 Controller 有自身的要求；仅选择网络后端并不会启用策略实施。
- 节点间加密、经过身份验证的工作负载身份和应用 mTLS 是不同的控制措施。网络流量可见性也不同于应用跟踪或进程/文件实施。

### 路由和性能

Calico 和 Cilium 可以通过 BGP 通告路由；但这本身不提供多集群服务发现、策略同步或加密。Flannel host-gw 使用直连路由，因此需要合适的二层连接。覆盖网络会增加封装和 MTU 方面的考量，但无法仅凭 CNI 名称推断其普遍性能排名。

之前给出的 100/98/95/85/80/75 百分比吞吐量没有可复现的工作负载、版本或测量来源。请使用可比的硬件、内核、数据包/请求大小、并发数、加密/策略设置、吞吐量、丢包率和尾延迟进行比较。单独的 [Pod 基准测试](06-pod-network-benchmark.md)保留了自身的历史环境和测量结果。

## CNI 选择指南

首先确定所需的路由、策略、操作系统和支持模式，然后测试该组合。

| 需求 | 评估路径 |
|---|---|
| 标准 EKS VPC 寻址和受支持的网络策略 | 在添加第二个策略引擎之前，先评估 AWS VPC CNI/EKS 功能。 |
| 有序策略 tier、主机策略或基础设施 BGP | 评估相关 Calico 版本/数据平面及路由先决条件。 |
| Cilium 策略、Hubble 或选定的 mesh 功能 | 检查 Linux/内核/平台兼容性以及 [Cilium mesh 指南](../service-mesh/cilium-service-mesh/README.md)。适用的 L7 路径仍会使用 Envoy。 |
| 功能需求有限的小型网络 | 根据实际需求评估 Flannel 后端和可选策略 Controller。 |
| 进程、系统调用或文件实施 | 单独评估 Tetragon 等运行时安全组件，而不是将其等同于网络策略。 |

### EKS 托管 add-on 配置

以下是一个**配置负载**示例，并非同时在相同工作负载上安装 Calico 和 VPC CNI 策略引擎的指示：

```json
{
  "enableNetworkPolicy": "true"
}
```

此设置的文档类型是字符串 `"true"`。请为现有 Kubernetes 版本选择兼容的 EKS add-on build，并检查该 build 的配置架构：

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

上游 1.23.2 发布版本号与 EKS `eksbuild` 版本是不同的标识符。AWS 当前的 add-on 表为 Kubernetes 1.31–1.37 列出了 `v1.23.1-eksbuild.1`；请在目标区域使用 `describe-addon-versions` 选择兼容的 build。将更改合并到预期的托管 add-on 配置中；不要盲目选择 `latest` 或替换无关值。从第三方策略实现迁移时，还需要移除其现有实施状态，并制定经过测试的节点/工作负载迁移计划。

## EKS 网络基础

### EKS 默认网络架构

| 位置 / 组件 | 职责 |
|---|---|
| EKS 管理的 VPC | AWS 在多个可用区运行托管 Kubernetes 控制平面。 |
| 客户集群 VPC | 工作节点网络、所选子网以及 EKS 管理的跨账户 ENI 提供通往控制平面的已配置路径。 |
| 所选客户 VPC 子网中的 ALB/NLB | 提供所选的公有或内部应用入口；Internet Gateway/NAT Gateway 不能替代该路由配置。 |
| NAT Gateway 或私有服务端点 | 提供工作负载设计所需的特定出站路径。 |

之前的图将控制平面放在客户 VPC 内、将负载均衡器放在其外部；现已改用以上所有权边界来说明。

### 不同计算模式下的 DNS 和网络

| 计算模式 | DNS / 组件位置 |
|---|---|
| 标准 EC2 节点 | 通常使用已配置的 CoreDNS Deployment 和已安装的网络组件；替代实现需要各自受支持的配置。 |
| 纯 EKS Auto Mode | CoreDNS、VPC CNI 和 kube-proxy 功能作为托管节点 systemd 服务运行。这些节点不需要 CoreDNS Deployment/add-on。 |
| Auto Mode 与非 Auto 节点混用 | 非 Auto 节点仍需保留 CoreDNS Deployment；它们不能使用其他节点的 Auto Mode DNS 服务。 |

Auto Mode 的首个 DNS 解析器位于节点本地。上游转发和控制平面通信仍可能需要网络访问；这并不保证所有 DNS 相关数据包都留在节点上。AWS 同时为 Auto Mode 说明了 Admin 和 DNS 策略，而标准 EC2 VPC-CNI Admin 策略有自身的版本/启用要求。

### VPC CNI 的工作方式

AWS VPC CNI 根据所选 IPAM 模式为普通 Pod 分配可通过 VPC 路由的地址。辅助 IPv4 地址、委派前缀、branch ENI 和多 NIC 配置各不相同；host-network Pod 共享节点网络。

![从 EC2 ENI 向 Pod 分配辅助 IPv4 地址的示意图，其中包含可选的预留接口。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

此图仅展示辅助 IP 模式。Warm ENI 是可配置的分配策略，并不意味着每个节点都必须始终准确预留一个 ENI。前缀委派、自定义网络和 branch ENI 具有不同的分配规则。

#### ENI 和 IP 限制

| 实例类型 | 最大 ENI 数 | 每个 ENI 的 IPv4 槽位数 | 旧版辅助 IP 引导值 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

这些值已根据 VPC CNI 1.23.2 的实例限制和旧版 max-Pods 表核实。历史计算公式为 `ENIs × (IPv4 slots per ENI − 1) + 2`；这并非当前通用建议。前缀委派、自定义网络、branch ENI 和多个网卡会改变地址容量。Kubernetes 调度还受 kubelet `maxPods` 和资源限制。对于 vCPU 少于 30 个的实例，EKS 托管节点组将 `maxPods` 上限设为 110；其他实例的上限为 250。可用 IP 数量本身不会突破该上限。

### EKS 网络注意事项

#### IP 地址管理

对于 **Linux VPC CNI**，请通过所选 add-on/Helm/DaemonSet 管理机制配置文档中说明的环境变量。以下是 EKS add-on 配置片段。旧版 `amazon-vpc-cni` ConfigMap 中的 `enable-prefix-delegation` 不会以这种方式配置 Linux IPAMD。应用更改时，请保留其他预期的 add-on 值。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

也可以调整总分配下限和空闲 IP 目标。配置 `MINIMUM_IP_TARGET` 或 `WARM_IP_TARGET` 后，它们的优先级高于 `WARM_PREFIX_TARGET`；这些是互相替代的策略，而非四个彼此独立、累加的目标。分配仍以整个前缀为单位进行。Nitro 支持、IPv4 所需的连续 `/28` 地址空间以及合适的 kubelet Pod 限制，都是独立的先决条件。

Windows 前缀分配使用不同的配置路径：AWS 文档说明应在 `amazon-vpc-cni` ConfigMap 中配置 `enable-windows-prefix-delegation` 及其 warm-target 键。不要将 Linux 环境变量配置步骤原样用于 Windows。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "MINIMUM_IP_TARGET": "5",
    "WARM_IP_TARGET": "2"
  }
}
```

#### 自定义网络

这些 IPv4 示例需要在目标 AZ 和 VPC 中填入真实的子网/安全组 ID。启用自定义网络，并通过节点的 zone 标签选择每个节点的 ENIConfig。显式的 ENIConfig 节点注解优先级高于该标签。以下示例名称在两种语言中都使用同一区域；请替换为实际的节点可用区。仅安装 ENIConfig 对象并不会激活自定义网络。

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-fedcba9876543210f
```

## 高级网络概念

本概述的其他部分会顺带提及以下内容。完整的设置步骤和实测数据位于相应的深入介绍页面；本节将按层说明这些组件的差异和适用场景。

### L2–L7，以及路由器与负载均衡器的区别

“路由器”和“负载均衡器”经常出现在同一句话里，但它们解决的是不同问题。路由器通常为单个目标选择一条路径；负载均衡器则使用分配算法，从多个等价候选项中选择一个目标。

| 层 | 设备/功能 | 决策依据 | Kubernetes/AWS 对应项 |
|---|---|---|---|
| L2（链路层） | 交换机、网桥 | 目标 MAC 地址 | CNI 创建的 veth 对和 Linux 网桥、ENI 暴露的虚拟 NIC |
| L3（网络层） | 路由器或透明设备插入 | 根据目标 IP 路由；根据流标识选择设备 | VPC 隐式路由器、TGW；GWLB 封装发往设备的 IP 数据包 |
| L4（传输层） | L4 负载均衡器 | 连接/流标识，通常为五元组 | NLB；kube-proxy（iptables、IPVS、nftables）；独立的 eBPF Service 实现 |
| L7（应用层） | L7 负载均衡器/反向代理 | 每个请求的主机、路径、标头；协议感知 | ALB、Ingress/Gateway API 实现、服务网格 sidecar（Envoy） |

关键区别在于**分配单位**。L4 负载均衡器通常为一个 TCP 连接或经过跟踪的 UDP 流选择目标。L7 代理可以为每个受支持的应用请求选择目标，即使多个请求共享同一连接也可以。GWLB 会将封装后的 IP 流分配到安全设备，而不是解析应用请求。流粘滞性取决于配置的超时、健康状态和故障转移行为；它并不保证流永远不会重新分配或中断。

> 📎 L2/L3 概念的协议级定义见[网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)；ALB/NLB target 类型和实际配置见 [AWS Load Balancer Controller](03-aws-lb-controller.md)。

### 跨账户/VPC 连接：TGW、VPC Peering、GWLB、PrivateLink、Lattice

这五种连接方式在层级和流量模型上各不相同。有关 TGW RAM 共享、VPC Peering、PrivateLink、TGW Peering 和 VPC Lattice 的实测延迟，请参阅[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。本节新增了该对比表中没有的 GWLB，并按层重新梳理这五种方式。

| 连接方式 | 层级/模型 | 特征 |
|---|---|---|
| VPC Peering | L3，双向 IP 路由 | 不具备传递性；不能在 CIDR 重叠的 VPC 之间配置 |
| Transit Gateway (TGW) | L3，中心辐射型 IP 路由 | 通过一个或多个 TGW 路由表中的 attachment 关联和传播来工作；可通过 RAM 跨账户共享 |
| Gateway Load Balancer (GWLB) | L3，透明设备插入 | 使用 GENEVE（UDP 6081）封装原始数据包；通过 VPC endpoint service 模型将使用方流量连接到提供方的设备集群 |
| PrivateLink | 私有端点连接 | NLB 支持的 endpoint service 是一种模式；也支持 resource endpoint。使用方/提供方 CIDR 可以重叠 |
| VPC Lattice | 应用和资源网络 | HTTP/HTTPS Service 支持 L7 路由和可选的 IAM 授权；TLS 直通和资源配置具有不同的功能 |

GWLB 通过 Gateway Load Balancer endpoint 将防火墙和 IDS/IPS 等检查设备插入 IP 路径。其默认流粘滞性使用五个字段；受支持的配置也可以改用两个或三个字段。请验证正向和返回路由、设备健康状态、封装 MTU、NACL，以及实际工作负载/设备的安全组。GWLB 本身没有类似 ALB 的安全组，流粘滞性也不能代替故障测试。

安全设计请参阅 [WAF/源站保护](../security/14-waf-edge-api-security.md)、[Palo Alto/Fortinet NGFW](../security/15-ngfw-paloalto-fortinet.md) 和 [GWLB/GENEVE 路径及故障](../security/16-gwlb-geneve-inspection.md)。GWLBE 也不支持 SG。对于所有 target 均不健康的情况，AWS 说明会按流选择 target，并在恢复前丢弃流量，不会直接绕过设备。请综合审查缩减元组粘滞性、跨区、NAT 和 TGW appliance mode。

> 📎 完整的 EKS/VPC Lattice 集成（Gateway API Controller、IAM 授权、路由）见 [VPC Lattice](02-vpc-lattice.md)。

### DNS Resolver 和路由表的实际行为

**DNS 解析器**：AmazonProvidedDNS **就是 Route 53 Resolver**。其地址包括 VPC IPv4 主网络地址加二（对于 `10.0.0.0/16`，即 `10.0.0.2`）以及 `169.254.169.253`；它根据 Resolver 规则解析关联的私有区域和公有名称。CoreDNS 通常提供已配置的 Kubernetes 集群域名，常见的是 `cluster.local`；`kube-dns` 是它的 Service 名称，而不是命名空间或 DNS 区域。外部转发遵循 Corefile 以及 DNS Pod 可见的 resolver 文件。请检查这些设置，不要假定节点的 resolver 文件会未经修改地直接使用。在 Resolver endpoint 设计中，inbound endpoint 接收来自本地部署环境的查询，而 outbound endpoint 和关联的规则会将选定的 VPC 查询转发到本地部署 DNS。Auto Mode 的节点本地解析器不会消除对上游的依赖。

**路由表**：VPC 路由评估通常使用最长前缀匹配。AWS 允许替换 `local` 路由的目标，并添加受支持的、更具体的子网路由以实现设备路由；`local` 并不总是最具体的路由。目标相同的情况下，VPC 静态路由优先于从 virtual private gateway 传播的路由。目标为 TGW 的 VPC 路由是静态路由；TGW 内部的传播属于其独立路由表。无效目标可能导致流量被丢弃的 `blackhole` 条目，因此除了目标地址外，还要检查路由状态。未显式关联路由表的子网会使用 VPC 的主路由表。

> 📎 TGW/Peering 路由优先级和静态路由配置示例见[跨组织 VPC 连接的运维发现](05-cross-org-vpc-connectivity.md#operational-findings)。

### 内核数据平面：iptables、IPVS、eBPF 和数据包过滤

Linux Service 转发和网络策略实施可以使用不同机制。Netfilter 提供 iptables 和 nftables 使用的数据包路径挂钩点。eBPF 实现可以挂载到 XDP、tc 或 socket 挂钩点，并在那里执行 Service 选择。这并不意味着启用了 eBPF 的集群中的每个数据包都会绕过 Netfilter 或连接跟踪；数据包路径取决于 CNI、内核、路由和功能配置。

| 实现 | 所在位置 | 特征 |
|---|---|---|
| iptables | netfilter 挂钩点上的顺序规则链 | 评估耗时随规则数量增长（O(n)）；是 kube-proxy 长期使用的默认模式 |
| IPVS | 内核原生 L4 负载均衡器，是 netfilter 扩展 | 基于哈希查找（接近 O(1)）；从 Kubernetes 1.35 开始不再推荐将其作为 kube-proxy 模式 |
| nftables | netfilter 中取代 iptables 的后继框架 | 自 1.33 起成为 kube-proxy 的稳定模式；请先检查内核/CNI 兼容性 |
| eBPF（例如 Cilium） | 已配置的 XDP、tc 和 socket 挂钩点 | 可以替代 kube-proxy 的 Service 处理；这是独立实现，其 Netfilter/conntrack 行为取决于具体路径 |

切换实现可能会遗留内核规则和活动连接。请遵循发行版/CNI 的迁移步骤，按需清空工作负载，并在清理需要时规划节点重启。以基于 eBPF 的 CNI 替换 kube-proxy 时，也需要按照受支持的顺序切换，避免不同实现争抢相同的 Service 流量。

> 📎 IPVS 弃用时间线和 nftables 稳定版过渡见[《Kubernetes 简介》](../basics/04-kubernetes-introduction.md)；Cilium 的 eBPF kube-proxy 替代方案见 [Cilium eBPF](cilium/02-ebpf.md)；Calico 的 eBPF 数据平面及其迁移步骤见 [Calico eBPF](calico/06-ebpf-dataplane.md)。

### 计算密集型网络：ENI、EFA、NVLink 和光收发器

ENI、EFA 和 NVLink 服务于不同路径。**ENI** 是连接到某个可用区内 EC2 实例的虚拟网络接口；在路由和策略允许时，其普通 IP 流量可以到达其他 AZ 和互联的 VPC（见 [VPC CNI](01-vpc-cni.md)）。**EFA** 提供一种通过 libfabric 供兼容 MPI/NCCL 软件使用的操作系统旁路设备。**EFA 设备流量不可路由，不能跨越 VPC/AZ 边界**；通过带 EFA-with-ENA 接口的 ENA 设备发送的普通 IP 流量仍然可以路由。仅 EFA 接口没有 ENA 设备或 IP 寻址。**NVLink** 在受支持的系统内连接 GPU，包括受支持的机架级 NVLink 域。请根据所选硬件、集合通信操作和放置方式进行测量，而不要假定相对于 EFA 存在固定加速比。

**光收发器**是数据中心网络中的通用概念。铜质 DAC（直连铜缆）适用于短距离连接；光模块和光纤则适用于其他距离和带宽需求。QSFP 和 OSFP 描述的是模块外形规格，并不保证使用光介质。请将此内容视为一般背景知识：它不能说明特定 AWS 工作负载使用的物理布线。

> 📎 面向拓扑的 NVLink/IMEX 调度和 GPU Pod 放置示例见 [AI/ML 基础设施](../ai-ml/06-ai-infrastructure.md)；EFA 的 VPC/AZ 边界限制和测量结果见[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。

### 下一代协议对 Kubernetes 的意义：HTTP/3、gRPC、QUIC

HTTP/3（RFC 9114）及其 QUIC 传输协议（RFC 9000）的协议机制见[网络基础第 2 部分](../basics/06-network-fundamentals-part2.md)和[第 3 部分](../basics/06-network-fundamentals-part3.md)。这里仅介绍实际影响 Kubernetes 流量分配的内容。

- **gRPC 和 L4 负载均衡器**：gRPC 会通过 HTTP/2 连接多路复用请求。L4 负载均衡器通常会让已建立的 TCP 连接继续使用其选定的端点；如果该端点是代理，它还可以进一步决定如何路由。仅增加 Pod 不会重新分配现有连接。按 RPC 分配需要兼容的 L7 代理或客户端策略。流式 RPC 仍是一次调用；其中的单条消息不会单独进行负载均衡。
- **Gateway API 的 GRPCRoute**：Ingress 没有专用于 gRPC 的资源，但 Gateway API 通过 `GRPCRoute` 标准化了服务/方法级路由。支持情况因实现而异（例如支持多少种标头匹配、重试策略等），因此请查看 Controller 自身的文档。
- **HTTP/3/QUIC 在集群中的实际覆盖范围**：客户端与边缘入口（CDN、负载均衡器）之间是否支持 HTTP/3，与集群内部或 Ingress 到后端连接是否支持 HTTP/3，是两个不同的问题。许多 Ingress/Gateway 实现与后端通信时仍使用 HTTP/1.1 或 HTTP/2；端到端 HTTP/3 是否受支持因实现和版本而异，因此不要一概而论；请查阅实际使用的 Controller 文档。

## 网络子页面

本节详细介绍以下主题：

### [从零开始学习 Linux 网络](beginner/README.md) {#beginner-course}

如果你刚接触 Linux 或网络，请从[初学者课程](beginner/README.md)开始。课程的八节课将 CLI、寻址、DNS、SSH、防火墙、监控和综合实践串联起来。下面的学习路径将在此基础上扩展到协议、内核和集群实现。

### [专家网络学习路径](expert/README.md) {#expert-course}

完成初学者课程后，请使用[专家网络学习路径](expert/README.md)，将协议项目、路由策略、EVPN、Linux 性能、云设计和自动化评估串联起来。请先检查每本练习手册的环境、证据和恢复标准。

### [Linux 网络诊断实践](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

在学习 CNI 实现前，先将[内核套接字和数据包路径概念](../kernel/02-network-stack.md)与实际观测结果联系起来。使用[诊断测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)检查你的解读是否正确。

### [VPC CNI](01-vpc-cni.md)
介绍使用 VPC 地址为普通 Pod 提供网络的 EKS 网络，以及特定模式下 IPAM/策略的先决条件。

### [深入了解 Cilium](cilium/README.md)
基于高性能 eBPF 的 CNI 解决方案，提供 L7 Network Policy、Service Mesh 和可观测性（Hubble）等高级功能。

### [深入了解 Calico](calico/README.md)
应用最广泛的 CNI 之一，具有强大的 Network Policy、BGP 支持和企业功能。涵盖简介、架构、网络模式、BGP 深入介绍、Network Policy、eBPF、高级主题、EKS 集成和运维指南。

### [VPC Lattice](02-vpc-lattice.md)
AWS 托管的应用网络服务，支持跨 VPC、跨账户的服务间通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
将 Kubernetes Service 和 Ingress 与 AWS ELB（ALB/NLB）集成。

### [Gateway API](04-gateway-api.md)
新一代 Kubernetes ingress API，提供标准化资源模型和基于角色的配置。

### [Pod 网络基准测试](06-pod-network-benchmark.md)
在 EKS 上测量同节点、同 AZ 和跨 AZ 场景下 Pod 到 Pod 的 RTT、HTTP 延迟和吞吐量，并测量 DNS `ndots:5` 查询放大效应。

## 网络故障排查

### 常见问题和解决方案

#### Pod 到 Pod 通信失败

```bash
NAMESPACE=default
POD_NAME=iperf-client  # An existing diagnostic Pod with nslookup/curl
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get pods -o wide
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- nslookup "$SERVICE_NAME"
kubectl -n "$NAMESPACE" exec "$POD_NAME" -- \
  curl --connect-timeout 3 --max-time 5 -v "http://$SERVICE_NAME:80/"
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=100
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --tail=100
```

请从已安装所列工具的现有 Pod 中运行诊断。只查询集群中实际安装的 CNI；Auto Mode 系统服务并不是这些 DaemonSet。DNS 成功、TCP 可达和应用返回 HTTP 响应是不同的检查。ICMP 可能被阻止或需要额外权限，因此单独的 ping 失败不能证明 TCP Service 无法访问。

#### Service 无法访问

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

当前端点诊断请使用 EndpointSlice。检查 Service selector、目标端口、端点就绪状态、地址族和适用策略。只有在 kube-proxy 实际负责 Service 转发时才检查其日志；eBPF 替代实现或 Auto Mode 需要使用各自的诊断方法。

#### 网络策略调试

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium 命令会检查由 DaemonSet 引用选中的一个 Agent；跟踪事件时，请选择受影响节点上的 Agent。使用 Calico 原生 API 的安装可能会公开不同的 API group，因此请检查该安装实际提供的资源。Kubernetes、Calico 和 AWS 扩展策略属于不同资源，其优先级也可能不同。

### 网络性能测试

这个有限范围的 TCP 测试使用镜像发布者固定的 Netshoot v0.16 镜像索引，其中包含 Linux AMD64 和 Arm64 镜像；其 Dockerfile 中包含 `iperf3`。请在允许 TCP 5201 的测试环境中创建这些 Pod。它只是示意性工作负载，不是 CNI 对比测量结果。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: iperf-server
  namespace: default
  labels:
    app: iperf-server
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - iperf3
    - -s
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    ports:
    - containerPort: 5201
      protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: iperf-client
  namespace: default
  labels:
    app: iperf-client
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  containers:
  - name: netshoot
    image: nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
    command:
    - sleep
    - '3600'
    workingDir: /tmp
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 256Mi
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
```

```bash
kubectl -n default wait --for=condition=Ready pod/iperf-server pod/iperf-client --timeout=120s
IPERF_SERVER_IP="$(kubectl -n default get pod iperf-server -o jsonpath='{.status.podIP}')"
test -n "$IPERF_SERVER_IP"
kubectl -n default exec iperf-client -- iperf3 -c "$IPERF_SERVER_IP" -t 10 -b 10M
```

客户端会休眠一小时；该命令会将发送流量限制为 10 Mbit/s，持续十秒。这项测试检验所选路径，而不是最大吞吐量。解读结果前，请记录实际 Pod/节点/AZ 放置情况、资源限制和策略。Windows 节点请选用适用于 Windows 的工具。完成后只删除你创建的测试资源。

这些独立诊断 Pod 用于连接测试。对于 EKS 原生网络策略实施测试，请使用由 Deployment/Job 管理的 Pod，并遵循文档中关于 Service/容器端口的要求。

## 最佳实践

### 1. IP 地址规划

- 设计足够大的 CIDR 网段
- 将 Pod 网络与 Service 网络分开
- 设计子网时考虑未来扩展

### 2. 应用网络策略

使用此示例前，先创建隔离的 `networking-demo` 命名空间。按照标准 Kubernetes NetworkPolicy 语义，该示例会选中其中的所有 Pod，并同时隔离入站和出站流量；所需 DNS 和应用流量需要显式添加允许规则。实施策略需要受支持的策略引擎。额外的集群/管理员策略 API 可能会改变优先级；仅凭此清单并不能构成完整的零信任架构。

- 应用默认拒绝策略（零信任）
- 仅显式允许必需流量
- 隔离命名空间

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: networking-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 3. 性能优化

- 选择合适的 CNI（与工作负载匹配）
- 优化 MTU
- 调整内核参数

### 4. 安全强化

- 选择受支持的传输加密方式，并确认其覆盖的流量范围。
- 按需配置工作负载/应用身份和 mTLS；不要将这些与基于 DNS/IP 的允许列表混为一谈。
- 定期审查策略、证书和访问控制变更。

### 5. 确保可观测性

- 收集网络指标
- 启用流日志
- 实施分布式跟踪

## 后续步骤

完成[初学者课程](beginner/README.md)后，继续学习[内核网络协议栈](../kernel/02-network-stack.md)，然后学习 [Linux 网络诊断实践](07-linux-network-diagnostics.md)及其[测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)。[学习路径](#learning-path)会在介绍下方的 CNI 和 AWS 主题之前，将这些基础知识与容器和 Service 联系起来。

1. [VPC CNI](01-vpc-cni.md) - EKS 默认 CNI
2. [深入了解 Cilium](cilium/README.md) - 基于 eBPF 的网络
3. [深入了解 Calico](calico/README.md) - 路由、策略和数据平面
4. [VPC Lattice](02-vpc-lattice.md) - AWS 托管网络
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 集成
6. [Gateway API](04-gateway-api.md) - 新一代 ingress
7. [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) - 跨 AWS Organizations 连接 VPC（经现场验证）
8. [Pod 网络基准测试](06-pod-network-benchmark.md) - 按节点/AZ 边界测量的延迟和吞吐量

---

## 参考资料

- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [容器运行时和 CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI 规范](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico 产品版本](https://docs.tigera.io/calico/latest/about)
- [Calico Open Source 3.33.0 发布版本](https://github.com/projectcalico/calico/releases/tag/v3.33.0)
- [Calico 策略 tier](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker 流日志](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows 限制](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.10 网络和策略](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.10/README.md)
- [Flannel 后端](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.10/Documentation/backends.md)
- [原始 Weave 仓库状态](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.2](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.2/README.md)
- [Amazon EKS 最新 VPC CNI add-on 版本](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS 网络策略配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard 和 Admin 网络策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS 前缀委派和 maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin 和 DNS 策略部署模式](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode 网络](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on 要求](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS 控制平面架构](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 镜像元数据](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon 运行时安全](https://tetragon.io/docs/overview/)
- [AWS LBC 3.6 NLB 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/nlb.md)
- [AWS LBC 3.6 Ingress 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer 概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE 封装（RFC 8926）](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS 解析器](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoints 和规则](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC 路由表评估顺序](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local 路由和更具体的子网路由](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [静态路由和传播路由的优先级](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS 地址和行为](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB 流粘滞性和故障转移](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service 虚拟 IP 和 kube-proxy 模式](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service 名称和转发配置](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables 项目文档](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC 传输协议（RFC 9000）](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3（RFC 9114）](https://www.rfc-editor.org/rfc/rfc9114)
- [基于 HTTP/2 的 gRPC 和负载均衡](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
