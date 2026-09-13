# Kubernetes 网络

> **最后更新**：2026 年 9 月 13 日。功能参考包括 Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9 和 AWS VPC CNI 1.23.0。安装前请检查各产品的 Kubernetes/平台矩阵；这些版本并非经过联合测试的集群配置。

## 概述

Kubernetes 网络是实现容器化应用之间通信的核心基础设施层。本节涵盖 Kubernetes 网络基本概念、高级 CNI（容器网络接口）方案以及 AWS EKS 环境中的网络模式。

## Kubernetes 网络模型

当前 Kubernetes 模型提供 Pod 网络，Pod 可跨节点直接通信，无需地址转换或代理，**但受有意设置的网络分段约束**。kubelet 等节点代理必须能访问本节点上的 Pod。网络策略、路由和应用监听器仍决定具体连接能否成功。

普通 Pod 具有自己的网络命名空间和集群范围地址；同一 Pod 中的容器共享该命名空间和 localhost。主机网络 Pod 共享节点网络，双栈或多网络配置需要更精确的地址处理。重新创建 Pod 可能分配不同 IP；重启同一 Pod 内的容器不一定会重新创建其网络沙箱。

| 组件 | 作用 |
|---|---|
| Pod 网络 | 工作负载网络命名空间之间的寻址与连接 |
| Service/发现 | 在端点变化时提供稳定服务名或虚拟地址 |
| Ingress/Gateway 实现 | 配置外部入口和应用路由 |
| 网络策略引擎 | 强制实施所选实现支持的策略 |

这些职责不构成强制串行的数据包路径。Service 转换、L7 代理和工作负载策略可能改变具体请求的网络路径。

### Pod 网络

Pod 网络为 Pod 通信提供寻址和路由。下图展示普通 IPv4 Pod；其中连接假定适用策略和网络控制允许通信。

![两个节点之间直接 IPv4 Pod 路径的示意，连通性受配置的策略和路由约束。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

这些是用于示意的普通 Pod 地址。有意隔离、主机网络或多网络配置需要各自的解释。

#### Pod 网络实现方法

| 方法 | 描述 | CNI 示例 |
|--------|-------------|-------------|
| **覆盖网络** | 在现有网络上封装流量 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **原生路由** | 使用底层网络路由，无需上述覆盖封装 | AWS VPC CNI、Calico 路由/BGP、Cilium 原生路由 |
| **条件封装** | 按配置拓扑使用直接路径或封装 | 受支持的 Calico/Flannel/Cilium 模式，前提条件各不相同 |

### Service 网络

Service 描述一组逻辑端点（通常为 Pod）及访问方式。ClusterIP 默认提供稳定虚拟 IP；无头 Service 不提供该虚拟 IP，ExternalName 使用 DNS CNAME 映射。Service 也可以具有不通过 Pod 选择器管理的端点。

![ClusterIP、NodePort、LoadBalancer 和 ExternalName Service 的典型入口机制；区分 DNS 映射与数据包转发。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

这些是典型暴露机制，不是安全保证。NodePort 范围和可访问的节点地址可配置；LoadBalancer 可以是内部的。ExternalName 返回 DNS 别名，不创建转发代理。

#### Service 类型特性

在 `default` 中创建匹配 `app: my-app` 的 Pod，并监听所示目标端口。NodePort 默认分配范围为 30000–32767，可配置。外部可达性仍取决于地址、路由和访问控制。

LoadBalancer 示例显式选择 **AWS Load Balancer Controller**，使用 EC2 实例目标和已分配的 NodePort。先安装/配置该控制器及其 IAM/子网前提条件。EKS Auto Mode 使用不同的控制器/类。此处端口 443 仅选择 TCP 端口；TLS 必须由后端在 8443 上提供，或在负载均衡器上单独配置。

这些端口映射演示通用 Kubernetes Service API。AWS 当前为原生 EKS 网络策略规定了额外要求：Service 端口必须匹配容器端口，并由具有 `metadata.ownerReferences` 的控制器管理 Pod 提供可靠执行。在测试该策略实现前，请按这些要求调整示例。

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

Ingress 资源需要控制器及其数据平面。此 HTTP 示例使用 AWS LBC，设置 `spec.ingressClassName: alb` 并使用 IP 目标。引用的 `api-v1`、`api-v2` 和 `web-frontend` Service 必须存在于 `default`，暴露端口 80，并具有就绪且可由 VPC 路由的 Pod 端点。需要时单独配置 HTTPS/证书。安装和目标前提条件参阅 [LBC 指南](03-aws-lb-controller.md)。

Ingress 定义将 HTTP/HTTPS 流量路由到集群内部 Service 的规则。

![Ingress 按主机/路径路由到 Service 后端和 Pod 的逻辑示意。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

方框代表 Ingress 数据平面功能。AWS LBC 配置 ALB；应用流量不经过控制器协调流程。根据目标模式，数据平面可直接访问 Pod IP 或 NodePort，不必将 Service 虚拟 IP 作为实际额外跳点。

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

CNI 标准化运行时配置容器网络的接口。在当前 Kubernetes 中，kubelet 通过 CRI 请求 Pod 沙箱操作，由**容器运行时管理 CNI**。kubelet 旧的直接 CNI 管理标志已在 Kubernetes 1.24 中移除。

### 运行时和插件职责

| 参与方 | 职责 |
|---|---|
| kubelet | 通过容器运行时接口请求创建/移除沙箱 |
| 容器运行时 | 选择网络配置并调用 CNI 插件链 |
| CNI 插件 | 接收配置，执行 ADD/DEL 及其他受支持操作，并返回结果 |
| IPAM 实现 | 分配/释放地址；可以是委托插件，也可以是提供方专属代理的一部分 |
| 可选节点代理 | 维护提供方专属路由、策略、IP 池或数据路径状态 |

运行时通过 CNI 接口向插件传递配置；并非每个插件都必须有独立的长期运行代理或 IPAM 二进制程序。接口类型也不同：veth 对很常见，但不是唯一实现。

## CNI 比较

| 项目 / 范围 | 网络和策略 | 需要区分的功能与限制 |
|---|---|---|
| **Cilium 1.20.1** | eBPF 网络；相关 L7 功能使用 Envoy；Cilium 网络策略和 Hubble | Linux 工作节点数据平面，具有 AMD64/Arm64 要求。Windows CLI 可用不代表支持 Windows CNI。WireGuard/IPsec 和 Beta ztunnel mTLS 的范围不同。 |
| **Calico Open Source 3.32** | 多种路由/封装选择；iptables、nftables 和 eBPF 选项；有序策略层及主机/工作负载策略 | Windows 有独立限制，包括不支持 Linux eBPF 或 WireGuard 数据平面。Whisker/Goldmane 流量可观测性作为技术预览提供。付费能力请查阅版本矩阵。 |
| **Flannel 0.28.9** | 主机子网分配和节点间传输；VXLAN、host-gw 等后端 | `flanneld` 本身不执行 NetworkPolicy；chart 的可选 `netpol.enabled` 部署 SIGs 策略控制器。WireGuard 是文档列出的后端；IPsec 为实验性。Windows VXLAN 有专属设置/限制。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC 地址分配和 EC2 ENI/前缀；在受支持 Linux EC2 节点上提供 EKS 标准和 Admin 网络策略能力 | EKS Auto Mode 是托管网络实现，另有 DNS 策略能力。Windows、Fargate、自定义网络、前缀委派和多网卡支持各有条件。 |
| **原始 Weave Net 项目** | 历史覆盖网络实现 | 原始 `weaveworks/weave` 仓库已归档。不要将其描述为新集群的活跃、受支持默认选项。 |

### 策略、加密和可观测性

- Cilium 通过适用的 L7 组件提供 HTTP/DNS 感知策略，以及集群范围/主机策略。其拒绝/允许语义不是 Calico 的有序 Tier API。
- Calico Open Source 包含分层策略层和主机策略。当前产品矩阵将应用层策略、DNS/FQDN 策略及 Cluster Mesh 列为 Cloud/Enterprise 功能；不能默默归入开源版。Calico 文档规定的传输中加密使用 WireGuard。
- Amazon EKS 为 Auto Mode 和受支持的 EC2/VPC-CNI 安装提供 `ClusterNetworkPolicy` Admin/Baseline 控制。AWS 介绍的 DNS/FQDN `ApplicationNetworkPolicy` 功能适用于 **Auto Mode**。其名称不意味着当前支持 HTTP 方法/正文检查。
- Flannel 的可选策略控制器有自己的要求；仅选择网络后端不会启用策略执行。
- 节点间加密、经验证的工作负载身份和应用 mTLS 是不同控制。网络流量可见性也不同于应用追踪或进程/文件执行控制。

### 路由和性能

Calico 和 Cilium 可以通过 BGP 通告路由；这本身不提供多集群服务发现、策略同步或加密。Flannel host-gw 使用直接路由，需要合适的二层连通性。覆盖网络增加封装和 MTU 考量，但不能仅根据 CNI 名称推断通用性能排名。

之前的 100/98/95/85/80/75 百分比吞吐量图没有可复现工作负载、版本或测量来源。应使用可比较的硬件、内核、数据包/请求大小、并发度、加密/策略设置、吞吐量、丢包率和尾延迟。独立的 [Pod 基准测试](06-pod-network-benchmark.md)保留了其历史环境和测量结果。

## CNI 选择指南

先选择所需路由、策略、操作系统和支持模型，再测试该组合。

| 需求 | 评估路径 |
|---|---|
| 标准 EKS VPC 寻址和受支持的网络策略 | 添加第二个策略引擎前，先评估 AWS VPC CNI/EKS 能力。 |
| 有序策略层、主机策略或基础设施 BGP | 评估相关 Calico 版本/数据平面及路由前提条件。 |
| Cilium 策略、Hubble 或所选网格功能 | 检查 Linux/内核/平台兼容性及 [Cilium 网格指南](../service-mesh/cilium-service-mesh/README.md)。Envoy 仍是适用 L7 路径的一部分。 |
| 功能需求有限的小型网络 | 根据实际需求评估 Flannel 后端及可选策略控制器。 |
| 进程、系统调用或文件执行控制 | 将 Tetragon 等运行时安全组件与网络策略分开评估。 |

### EKS 托管插件配置

以下是**配置载荷**示例，不是要求在相同工作负载上同时安装 Calico 和 VPC CNI 策略引擎：

```json
{
  "enableNetworkPolicy": "true"
}
```

字符串 `"true"` 是文档规定的该设置类型。为现有 Kubernetes 版本选择兼容的 EKS 插件构建，并检查该构建的配置模式：

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

上游 1.23.0 发布版本号与 EKS `eksbuild` 版本是不同标识符。将更改合并到预期托管插件配置；不要盲选 `latest` 或替换无关值。从第三方策略实现迁移时，还需清除其现有执行状态，并制定经过测试的节点/工作负载转换计划。

## EKS 网络基础

### EKS 默认网络架构

| 位置 / 组件 | 职责 |
|---|---|
| EKS 托管 VPC | AWS 跨可用区运行托管 Kubernetes 控制平面。 |
| 客户集群 VPC | 工作节点网络、所选子网和 EKS 托管的跨账户 ENI 提供配置的控制平面访问路径。 |
| 位于所选客户 VPC 子网中的 ALB/NLB | 提供所选公有或内部应用入口；互联网网关/NAT 网关不能替代该路由配置。 |
| NAT 网关或私有服务端点 | 提供工作负载设计所需的特定出站路径。 |

之前的图将控制平面置于客户 VPC 内，负载均衡器置于其外；现已用这些所有权边界替代。

### 不同计算模式的 DNS 和网络

| 计算模式 | DNS / 组件位置 |
|---|---|
| 标准 EC2 节点 | 通常使用已配置的 CoreDNS Deployment 和已安装网络组件；替代方案需要各自受支持的配置。 |
| 纯 EKS Auto Mode | CoreDNS、VPC CNI 和 kube-proxy 功能作为托管节点 systemd 服务运行。这些节点无需 CoreDNS Deployment/插件。 |
| Auto Mode 与非 Auto 节点混合 | 为非 Auto 节点保留 CoreDNS Deployment；它们不能使用其他节点的 Auto Mode DNS 服务。 |

Auto Mode 的首个 DNS 解析器位于节点本地。上游转发和控制平面通信仍可能需要网络访问；这不保证每个 DNS 相关数据包都留在节点内。AWS 为 Auto Mode 记录了 Admin 和 DNS 策略，而标准 EC2 VPC-CNI Admin 策略有自己的版本/启用要求。

### VPC CNI 如何工作

AWS VPC CNI 使用所选 IPAM 模式为普通 Pod 提供 VPC 可路由地址。辅助 IPv4 地址、委派前缀、分支 ENI 和多网卡配置各有不同；主机网络 Pod 共享节点网络。

![从 EC2 ENI 向 Pod 分配辅助 IPv4 地址的示意，包括可选的预热接口。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

此图仅展示辅助 IP 模式。预热 ENI 是可配置的分配策略，不要求每个节点始终恰好预留一个。前缀委派、自定义网络和分支 ENI 有不同的分配规则。

#### ENI 和 IP 限制

| 实例类型 | 最大 ENI 数 | 每个 ENI 的 IPv4 槽位数 | 旧版辅助 IP 引导值 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

这些值已对照 VPC CNI 1.23.0 实例限制和旧版最大 Pod 数表验证。历史公式为 `ENIs × (IPv4 slots per ENI − 1) + 2`；它不是当前通用建议。前缀委派、自定义网络、分支 ENI 和多网卡会改变地址容量。Kubernetes 调度还受 kubelet `maxPods` 和资源限制。EKS 托管节点组对少于 30 个 vCPU 的实例将 `maxPods` 上限设为 110，其他实例为 250；仅有可用 IP 数量不会覆盖该上限。

### EKS 网络注意事项

#### IP 地址管理

对于 **Linux VPC CNI**，通过所选插件/Helm/DaemonSet 管理机制配置文档规定的环境变量。以下是 EKS 插件配置片段。旧的带 `enable-prefix-delegation` 的 `amazon-vpc-cni` ConfigMap 不会以此方式配置 Linux IPAMD。应用更改时保留其他预期插件值。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

也可调整总分配下限和空闲 IP 目标。配置 `MINIMUM_IP_TARGET` 或 `WARM_IP_TARGET` 中任一项后，它优先于 `WARM_PREFIX_TARGET`；这些是备选策略，不是四个独立相加的目标。分配仍以前缀大小为单位。Nitro 支持、IPv4 连续 `/28` 空间和合适的 kubelet Pod 限制是独立前提条件。

Windows 前缀分配采用不同配置路径：AWS 在 `amazon-vpc-cni` ConfigMap 中定义 `enable-windows-prefix-delegation` 及其预热目标键。不要将 Linux 环境变量流程原样用于 Windows。

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

这些 IPv4 示例需要目标可用区和 VPC 中真实的子网/安全组 ID。启用自定义网络，并通过可用区标签选择各节点的 ENIConfig。显式 ENIConfig 节点注解优先于该标签。以下示例名称在两种语言中使用相同区域；请替换为实际节点可用区。仅安装 ENIConfig 对象不会激活自定义网络。

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

以下各项在本概述其他位置有所提及。完整设置流程和实测数据位于链接的深入指南；本节按层整理这些组件的区别及各自适用位置。

### L2–L7 以及路由器与负载均衡器的区别

“路由器”和“负载均衡器”常出现在同一句话中，但解决的问题不同。路由器通常为单一目的地选择一条路径；负载均衡器使用分配算法，从多个等价候选中选择一个目标。

| 层 | 设备/功能 | 决策依据 | Kubernetes/AWS 对应项 |
|---|---|---|---|
| L2（链路） | 交换机、网桥 | 目的 MAC 地址 | CNI 创建的 veth 对和 Linux 网桥、ENI 暴露的虚拟网卡 |
| L3（网络） | 路由器或透明设备插入 | 路由依据目的 IP；设备选择依据流标识 | VPC 隐式路由器、TGW；GWLB 为设备封装 IP 数据包 |
| L4（传输） | L4 负载均衡器 | 连接/流标识，通常为五元组 | NLB；kube-proxy（iptables、IPVS、nftables）；独立 eBPF Service 实现 |
| L7（应用） | L7 负载均衡器/反向代理 | 每个请求的主机、路径、标头；理解协议 | ALB、Ingress/Gateway API 实现、服务网格 Sidecar（Envoy） |

关键区别是**分配单位**。L4 负载均衡器通常为 TCP 连接或受跟踪的 UDP 流选择目标。L7 代理可以为每个受支持的应用请求选择目标，包括共享连接的请求。GWLB 在安全设备间分配封装 IP 流，不解析应用请求。流粘性取决于配置的超时、健康和故障转移行为；不保证流永不重新分配或中断。

> 📎 L2/L3 概念的协议级定义参阅[网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)；ALB/NLB 目标类型和实际配置参阅 [AWS Load Balancer Controller](03-aws-lb-controller.md)。

### 跨账户/VPC 连接：TGW、VPC Peering、GWLB、PrivateLink、Lattice

这五种连接选项在层次和流量模型上不同。TGW RAM 共享、VPC Peering、PrivateLink、TGW Peering 和 VPC Lattice 的实测延迟位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。本节补充该比较表未列出的 GWLB，并按层重新说明五种选项。

| 连接方式 | 层次/模型 | 特点 |
|---|---|---|
| VPC Peering | L3，双向 IP 路由 | 不具传递性；不能在重叠 CIDR 之间配置 |
| Transit Gateway（TGW） | L3，中心辐射式 IP 路由 | 在一个或多个 TGW 路由表中使用附件关联和传播；通过 RAM 跨账户共享 |
| Gateway Load Balancer（GWLB） | L3，透明设备插入 | 将原始数据包封装在 GENEVE（UDP 6081）中；VPC 端点服务模型将使用方流量连接到提供方设备集群 |
| PrivateLink | 私有端点连接 | NLB 支持的端点服务是其中一种模型；也存在资源端点。使用方/提供方 CIDR 可重叠 |
| VPC Lattice | 应用和资源网络 | HTTP/HTTPS 服务支持 L7 路由及可选 IAM 授权；TLS 透传和资源配置具有不同能力 |

GWLB 通过 Gateway Load Balancer 端点将防火墙和 IDS/IPS 等检查设备插入 IP 路径。默认流粘性使用五个字段；受支持配置也可使用两个或三个。验证正向和返回路由、设备健康、封装 MTU、NACL 及实际工作负载/设备的安全组。GWLB 本身没有 ALB 式安全组，流粘性不能替代故障测试。

> 📎 完整 EKS/VPC Lattice 集成（Gateway API Controller、IAM 授权、路由）参阅 [VPC Lattice](02-vpc-lattice.md)。

### DNS 解析器和路由表的实际行为

**DNS 解析器：** AmazonProvidedDNS **就是 Route 53 Resolver**。其地址包括 VPC 主 IPv4 网络地址加二（`10.0.0.0/16` 对应 `10.0.0.2`）和 `169.254.169.253`；它按 Resolver 规则解析关联私有区域和公共名称。CoreDNS 通常服务于配置的 Kubernetes 集群域，常为 `cluster.local`；`kube-dns` 是其 Service 名，不是命名空间或 DNS 区域。外部转发遵循 Corefile 及 DNS Pod 可见的解析器文件。应检查这些设置，不要假定节点解析器文件被原样使用。在 Resolver 端点设计中，入站端点接受本地网络查询，出站端点及关联规则将选定 VPC 查询转发到本地 DNS。Auto Mode 的节点本地解析器不会消除上游依赖。

**路由表：** VPC 路由评估通常采用最长前缀匹配。AWS 允许替换 `local` 路由目标，并添加受支持的更具体子网路由以供设备路由使用；`local` 并非无条件最具体。目的地相同时，静态 VPC 路由优先于从虚拟私有网关传播的路由。以 TGW 为目标的 VPC 路由是静态路由；TGW 内部传播属于其独立路由表。无效目标可能留下丢弃流量的 `blackhole` 条目，因此不仅要检查目的地，还要检查路由状态。未显式关联路由表的子网使用 VPC 主路由表。

> 📎 TGW/对等连接路由优先级和静态路由配置示例参阅[跨组织 VPC 连接的运维发现](05-cross-org-vpc-connectivity.md#operational-findings)。

### 内核数据平面：iptables、IPVS、eBPF 和数据包过滤

Linux Service 转发和网络策略执行可使用不同机制。Netfilter 提供供 iptables 和 nftables 使用的数据包路径钩子。eBPF 实现可挂载到 XDP、tc 或套接字钩子并在那里选择 Service。这不意味着启用 eBPF 的集群中每个数据包都绕过 Netfilter 或连接跟踪；路径取决于 CNI、内核、路由和功能配置。

| 实现 | 所处位置 | 特点 |
|---|---|---|
| iptables | netfilter 钩子上的顺序规则链 | 评估时间随规则数增长（O(n)）；kube-proxy 长期默认模式 |
| IPVS | 内核原生 L4 负载均衡器，netfilter 扩展 | 基于哈希查找（接近 O(1)）；从 Kubernetes 1.35 起作为 kube-proxy 模式弃用 |
| nftables | netfilter 中接替 iptables 的框架 | 自 1.33 起成为 kube-proxy 稳定模式；先检查内核/CNI 兼容性 |
| eBPF（如 Cilium） | 配置的 XDP、tc 和套接字钩子 | 可替代 kube-proxy 的 Service 处理；是独立实现，Netfilter/conntrack 行为因路径而异 |

切换实现可能遗留内核规则和活动连接。遵循发行版/CNI 迁移流程，按需排空工作负载，清理需要时规划节点重启。用基于 eBPF 的 CNI 替换 kube-proxy 也需要受支持的切换顺序，避免各实现争夺同一 Service 流量。

> 📎 IPVS 弃用时间线和 nftables 转为稳定的过程参阅 [Kubernetes 简介](../basics/04-kubernetes-introduction.md)；Cilium 的 eBPF kube-proxy 替代方案参阅 [Cilium eBPF](cilium/02-ebpf.md)；Calico eBPF 数据平面及迁移流程参阅 [Calico eBPF](calico/06-ebpf-dataplane.md)。

### 计算密集型网络：ENI、EFA、NVLink 和光收发器

ENI、EFA 和 NVLink 服务于不同路径。**ENI** 是附加到单个可用区内 EC2 实例的虚拟网络接口；在路由和策略允许时，其普通 IP 流量可到达其他可用区和已连接 VPC（参阅 [VPC CNI](01-vpc-cni.md)）。**EFA** 提供操作系统旁路设备，供兼容 MPI/NCCL 软件通过 libfabric 使用。**EFA 设备流量不可路由，不能跨越 VPC/可用区边界**；带 ENA 的 EFA 接口中，经 ENA 设备传输的普通 IP 流量仍可路由。仅 EFA 接口没有 ENA 设备或 IP 寻址。**NVLink** 连接受支持系统内的 GPU，包括受支持的机架级 NVLink 域。应测量所选硬件、集合通信操作和放置，不要假定相对 EFA 有固定加速比。

**光收发器**是通用数据中心网络概念。铜质 DAC（直连铜缆）适合短距离；光模块和光纤支持其他距离和带宽需求。QSFP 和 OSFP 描述模块外形规格，不保证使用光介质。应将其视为一般背景，不能据此确定特定 AWS 工作负载的物理布线。

> 📎 NVLink/IMEX 拓扑感知调度和 GPU Pod 放置示例参阅 [AI/ML 基础设施](../ai-ml/06-ai-infrastructure.md)；EFA 的 VPC/可用区边界约束及测量参阅[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。

### 下一代协议对 Kubernetes 的意义：HTTP/3、gRPC、QUIC

HTTP/3（RFC 9114）及其 QUIC 传输（RFC 9000）的协议机制参阅[网络基础第 2 部分](../basics/06-network-fundamentals-part2.md)和[第 3 部分](../basics/06-network-fundamentals-part3.md)。这里仅介绍实际影响 Kubernetes 流量分配的内容。

- **gRPC 和 L4 负载均衡器：** gRPC 在 HTTP/2 连接上复用请求。L4 均衡器通常让已建立 TCP 连接保持在所选端点；若该端点是代理，还可进一步作出路由决策。仅添加 Pod 不会重新分配现有连接。按 RPC 分配需要兼容的 L7 代理或客户端策略。流式 RPC 仍是一次调用；其中各条消息不会独立均衡。
- **Gateway API 的 GRPCRoute：** Ingress 没有 gRPC 专属资源，但 Gateway API 用 `GRPCRoute` 标准化服务/方法级路由。支持因实现而异（标头匹配数量、重试策略等），因此应查阅控制器自身文档。
- **HTTP/3/QUIC 实际深入集群的程度：** 客户端与边缘（CDN、负载均衡器）之间的 HTTP/3 支持，与集群内部或 Ingress 后端连接上的 HTTP/3 支持是不同问题。许多 Ingress/Gateway 实现仍使用 HTTP/1.1 或 HTTP/2 连接后端，是否支持端到端 HTTP/3 因实现和版本而异；不要泛化，应检查实际使用控制器的文档。

## 网络子页面

本节详细介绍以下主题：

### [VPC CNI](01-vpc-cni.md)

使用普通 Pod 的 VPC 地址，以及模式专属 IPAM/策略前提条件的 EKS 网络。

### [深入了解 Cilium](cilium/README.md)

基于 eBPF 的高性能 CNI 方案。提供 L7 网络策略、服务网格和可观测性（Hubble）等高级功能。

### [深入了解 Calico](calico/README.md)

使用最广泛的 CNI 之一。具有强大网络策略、BGP 支持和企业功能。涵盖简介、架构、网络模式、BGP 深入解析、网络策略、eBPF、高级主题、EKS 集成和运维指南。

### [VPC Lattice](02-vpc-lattice.md)

AWS 托管应用网络服务。支持跨 VPC、跨账户的服务间通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)

将 Kubernetes Service 和 Ingress 与 AWS ELB（ALB/NLB）集成。

### [Gateway API](04-gateway-api.md)

下一代 Kubernetes 入口 API。标准化资源模型和基于角色的配置。

### [Pod 网络基准测试](06-pod-network-benchmark.md)

在 EKS 上测量同节点、同可用区和跨可用区的 Pod 间 RTT、HTTP 延迟和吞吐量，以及 DNS `ndots:5` 查询放大。

## 网络故障排除

### 常见问题与解决方案

#### Pod 间通信失败

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

从包含所列工具的现有 Pod 运行诊断。仅查询集群实际安装的 CNI；Auto Mode 系统服务不是这些 DaemonSet。DNS 成功、TCP 可达性和应用 HTTP 响应是不同检查。ICMP 可能被阻止或需要额外权限，因此仅 ping 失败不能证明 TCP 服务不可达。

#### Service 不可达

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

当前端点诊断应使用 EndpointSlice。检查 Service 选择器、目标端口、端点就绪状态、地址族和适用策略。仅当 kube-proxy 实际负责 Service 转发时检查其日志；eBPF 替代方案或 Auto Mode 需要各自诊断方式。

#### 网络策略调试

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium 命令检查通过 DaemonSet 引用选中的一个 Agent；调查事件时应选择受影响节点的 Agent。Calico 原生 API 安装可能暴露不同 API 组，因此应检查安装实际提供的资源。Kubernetes、Calico 和 AWS 扩展策略是不同资源，优先级也可能不同。

### 网络性能测试

此有界 TCP 练习使用发布方固定的 Netshoot v0.16 镜像索引，其中包含 Linux AMD64 和 Arm64 镜像；Dockerfile 包含 `iperf3`。在允许 TCP 5201 的测试环境创建这些 Pod。它是示例工作负载，不是实测 CNI 比较。

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

客户端休眠一小时，命令将发送流量限制为 10 Mbit/s，持续十秒。它测试所选路径，不测试最大吞吐量。解释结果前，记录实际 Pod/节点/可用区放置、资源限制和策略。Windows 节点使用 Windows 专属工具。完成后仅移除自己创建的测试资源。

这些独立诊断 Pod 用于连接测试。测试原生 EKS 网络策略执行时，使用 Deployment/Job 管理的 Pod，并满足文档规定的 Service/容器端口要求。

## 最佳实践

### 1. IP 地址规划

- 设计足够大的 CIDR 块
- 分离 Pod 网络与 Service 网络
- 设计子网时考虑未来扩展

### 2. 应用网络策略

使用此示例前，创建隔离的 `networking-demo` 命名空间。它选择其中每个 Pod，并按标准 Kubernetes NetworkPolicy 语义隔离入站和出站流量；所需 DNS 和应用流量需要显式允许规则。执行需要支持该功能的策略引擎。额外的集群/管理员策略 API 可改变优先级，单个清单并非完整零信任架构。

- 应用默认拒绝策略（零信任）
- 仅显式允许所需流量
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

- 选择适合工作负载的 CNI
- 优化 MTU
- 调整内核参数

### 4. 安全加固

- 选择受支持的传输加密，并验证其覆盖的流量。
- 按需配置工作负载/应用身份和 mTLS；将其与基于 DNS/IP 的允许列表分开。
- 定期审核策略、证书和访问控制更改。

### 5. 确保可观测性

- 收集网络指标
- 启用流日志
- 实现分布式追踪

## 后续步骤

1. [VPC CNI](01-vpc-cni.md) - EKS 默认 CNI
2. [深入了解 Cilium](cilium/README.md) - 基于 eBPF 的网络
3. [深入了解 Calico](calico/README.md) - 路由、策略和数据平面
4. [VPC Lattice](02-vpc-lattice.md) - AWS 托管网络
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 集成
6. [Gateway API](04-gateway-api.md) - 下一代入口
7. [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) - 连接跨 AWS Organizations 的 VPC（现场验证）
8. [Pod 网络基准测试](06-pod-network-benchmark.md) - 跨节点/可用区边界的实测延迟和吞吐量

---

## 参考资料

- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [容器运行时和 CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI 规范](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico 产品版本](https://docs.tigera.io/calico/latest/about)
- [Calico 策略层](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker 流日志](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows 限制](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 网络和策略](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel 后端](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [原始 Weave 仓库状态](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS 网络策略配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS 标准和 Admin 网络策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS 前缀委派和 maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin 和 DNS 策略部署模型](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode 网络](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS 插件要求](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS 控制平面架构](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 镜像元数据](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon 运行时安全](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer 概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE 封装（RFC 8926）](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS 解析器](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver 端点和规则](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC 路由表评估顺序](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [本地路由和更具体的子网路由](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [静态与传播路由的优先级](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS 地址和行为](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB 流粘性和故障转移](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service 虚拟 IP 和 kube-proxy 模式](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service 名称和转发配置](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink 资源端点](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables 项目文档](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC 传输协议（RFC 9000）](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3（RFC 9114）](https://www.rfc-editor.org/rfc/rfc9114)
- [基于 HTTP/2 的 gRPC 和负载均衡](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
