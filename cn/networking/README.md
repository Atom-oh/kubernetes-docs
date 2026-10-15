# Kubernetes 网络

> **最后更新**: September 15, 2026。功能引用包括 Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9 和 AWS VPC CNI 1.23.0。安装前请检查每个产品的 Kubernetes/平台矩阵；它们并非经过联合测试的集群配置。

## 概述

Kubernetes 网络是实现容器化应用程序之间通信的核心基础设施层。本节涵盖从基本 Kubernetes 网络概念到高级 CNI (Container Network Interface) 解决方案，以及 AWS EKS 环境中的网络模式。

## 学习路径 {#learning-path}

如果你刚接触 Linux 或网络，请从[入门课程](beginner/README.md)开始。其八节课程将 CLI、寻址、DNS、SSH、防火墙、监控和综合项目串联起来。下方路径在这一基础上延伸至协议、内核和集群实现。

从协议概念逐步构建到观测，再将它们连接到容器、集群和云的职责。使用先决条件选择切入点，并在继续前使用学习成果检查理解程度。

| 阶段 | 角色 | 先决条件 | 学习成果 | 阅读 / 练习 |
|---|---|---|---|---|
| 协议、寻址、HTTP | 建立术语体系 | 基本命令行使用 | 跟踪一个请求，并区分寻址、传输和应用程序行为 | 网络基础[第 1 部分](../basics/06-network-fundamentals-part1.md)、[第 2 部分](../basics/06-network-fundamentals-part2.md)、[第 3 部分](../basics/06-network-fundamentals-part3.md)、[第 4 部分](../basics/06-network-fundamentals-part4.md) |
| Linux socket、VFS、数据包路径 | 将 API 连接到内核 | TCP/IP 基础 | 区分 FD、socket 缓冲区、窗口和队列 | [内核网络栈](../kernel/02-network-stack.md) |
| Linux 网络诊断 | 使用证据检验假设 | Socket 和数据包路径概念 | 关联 socket、数据包和应用程序观测结果 | [诊断练习](07-linux-network-diagnostics.md) · [测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker 和容器网络 | 定位 namespace 边界 | Linux 数据包路径和基本诊断 | 解释 bridge 网络、发布端口和容器名称解析 | [容器技术](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | 映射集群抽象 | 容器网络 | 跟踪名称如何经由 Service 到达其 endpoints，并识别 ingress 角色 | [服务与网络](../core/03-services-networking.md) · [实验](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、策略 | 比较实现职责 | Pod 和 Service 路径 | 区分数据包转发、策略执行和可观测性 | [eBPF 基础](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS 网络边界和性能 | 将模型应用于云路径 | CNI 概念和测量技能 | 识别 VPC、节点和 AZ 边界，并结合上下文解读测量结果 | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) · [Pod 网络基准测试](06-pod-network-benchmark.md) |

## Kubernetes 网络模型

当前 Kubernetes 模型提供了一个 Pod 网络，其中 Pod 可以跨节点直接通信，无需地址转换或代理，**但须遵从有意设置的网络分段**。kubelet 等节点 agent 必须能够访问其自身节点上的 Pod。网络策略、路由和应用程序监听器仍决定特定连接是否成功。

普通 Pod 拥有自己的网络 namespace 和集群范围地址；一个 Pod 中的容器共享该 namespace 和 localhost。host-network Pod 共享节点网络，dual-stack 或 multi-network 配置需要更精确的地址处理。重新创建 Pod 可能会分配不同的 IP；在同一 Pod 内重启容器不一定会重新创建其网络 sandbox。

| 组件 | 角色 |
|---|---|
| Pod 网络 | 工作负载网络 namespace 之间的寻址和连接性 |
| Service/服务发现 | 在不断变化的 endpoints 之上提供稳定的服务名称或虚拟地址 |
| Ingress/Gateway 实现 | 配置外部入口和应用程序路由 |
| 网络策略引擎 | 执行所选实现支持的策略 |

这些角色并不构成强制性的串行数据包路径。Service 转换、L7 代理和工作负载策略可以改变特定请求穿过网络的方式。

### Pod 网络

Pod 网络为 Pod 通信提供寻址和路由。下图显示普通 IPv4 Pod；其连接假定适用的策略和网络控制允许这些连接。

![两个节点上直接 IPv4 Pod 路径的示意图，连接性受已配置策略和路由的约束。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

这些地址是示例性的普通 Pod 地址。有意隔离以及 host-network 或 multi-network 配置需要各自进行解释。

#### Pod 网络实现方法

| 方法 | 描述 | 示例 CNI |
|--------|-------------|-------------|
| **Overlay Network** | 在现有网络上封装流量 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | 在底层网络中使用路由，无需该 overlay 封装 | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 根据已配置拓扑使用直接路径或封装 | 支持的 Calico/Flannel/Cilium 模式，具有不同的先决条件 |

### Service 网络

Service 描述一组逻辑 endpoints（通常为 Pod）以及如何访问它们。ClusterIP 默认提供稳定的虚拟 IP；headless Service 省略该虚拟 IP，ExternalName 使用 DNS CNAME 映射。Service 还可以拥有无需 Pod selector 管理的 endpoints。

![ClusterIP、NodePort、LoadBalancer 和 ExternalName Service 的典型入口机制；DNS 映射与数据包转发有所区分。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

这些是典型的暴露机制，而非安全保证。NodePort 范围和可访问的节点地址可配置；LoadBalancer 可以是内部的。ExternalName 返回 DNS 别名，不会创建转发代理。

#### Service 类型特性

在 `default` 中创建匹配 `app: my-app` 的 Pod，并监听所示 target port。NodePort 默认分配范围为 30000–32767，且可配置。外部可达性仍取决于地址、路由和访问控制。

LoadBalancer 示例明确选择 **AWS Load Balancer Controller**，使用 EC2 instance target 和已分配的 NodePort。请先安装/配置该 controller 及其 IAM/subnet 先决条件。EKS Auto Mode 使用不同的 controller/class。这里的端口 443 仅选择一个 TCP port；TLS 必须由 backend 在 8443 上提供，或在 load balancer 上单独配置。

这些端口映射说明通用 Kubernetes Service API。AWS 当前记录了额外的原生 EKS 网络策略要求：Service port 必须匹配容器端口，并且由 controller 管理、带有 `metadata.ownerReferences` 的 Pod 可提供可靠执行。在测试该策略实现之前，请调整示例以符合这些要求。

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

Ingress 资源需要 controller 及其 data plane。此 HTTP 示例使用 AWS LBC、`spec.ingressClassName: alb` 和 IP targets。引用的 `api-v1`、`api-v2` 和 `web-frontend` Service 必须存在于 `default` 中，暴露端口 80，并拥有就绪且 VPC 可路由的 Pod endpoints。需要时请单独配置 HTTPS/certificates。请参阅 [LBC 指南](03-aws-lb-controller.md)了解其安装和 target 先决条件。

Ingress 定义将 HTTP/HTTPS 流量路由至内部集群 Service 的规则。

![到 Service backend 和 Pod 的逻辑 Ingress host/path 路由。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

该框表示 Ingress data-plane 功能。AWS LBC 配置 ALB；应用程序流量不会穿过 controller 的协调过程。根据 target mode，data plane 可以访问 Pod IP 或 NodePort，而不是作为字面上的额外跳转穿过 Service 虚拟 IP。

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

## CNI (Container Network Interface)

CNI 标准化了 runtime 配置容器网络时所通过的接口。对于当前 Kubernetes，kubelet 通过 CRI 请求 Pod-sandbox 操作，且 **container runtime 管理 CNI**。kubelet 旧的直接 CNI 管理 flags 已在 Kubernetes 1.24 中移除。

### Runtime 和插件职责

| 参与者 | 职责 |
|---|---|
| kubelet | 通过 container runtime interface 请求创建/移除 sandbox |
| Container runtime | 选择网络配置并调用 CNI plugin chain |
| CNI plugin | 接收配置，执行 ADD/DEL 和其他受支持操作，并返回结果 |
| IPAM 实现 | 分配/释放地址；可能是委托的 plugin，或 provider-specific agent 的一部分 |
| 可选节点 agent | 维护 provider-specific 路由、策略、IP pools 或 datapath 状态 |

runtime 通过 CNI interface 将配置传递给 plugin；每个 plugin 并非都必须使用单独的长期运行 agent 或 IPAM binary。接口类型也不同：veth pairs 很常见，但并非唯一实现。

## CNI 对比

| 项目 / 范围 | 网络和策略 | 需要区分的功能和限制 |
|---|---|---|
| **Cilium 1.20.1** | eBPF 网络；用于相关 L7 功能的 Envoy；Cilium network policies 和 Hubble | Linux worker dataplane，具有 AMD64/Arm64 要求。Windows CLI 可用性并不等于 Windows CNI 支持。WireGuard/IPsec 和 Beta ztunnel mTLS 具有不同范围。 |
| **Calico Open Source 3.32** | 路由/封装选项；iptables、nftables 和 eBPF 选项；有序策略 tiers 以及 host/workload policy | Windows 有单独限制，包括不支持 Linux eBPF 或 WireGuard dataplane。Whisker/Goldmane flow observability 以 Tech Preview 提供。请查阅版本矩阵了解付费功能。 |
| **Flannel 0.28.9** | Host subnet 分配和节点间传输；VXLAN、host-gw 及其他 backends | `flanneld` 本身不执行 NetworkPolicy；chart 的可选 `netpol.enabled` 会部署 SIGs policy controller。WireGuard 是文档化的 backend；IPsec 是实验性的。Windows VXLAN 有特定设置/限制。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC 地址分配和 EC2 ENIs/prefixes；在受支持的 Linux EC2 节点上提供 EKS standard 和 Admin 网络策略功能 | EKS Auto Mode 是一种托管网络实现，具有额外 DNS 策略功能。Windows、Fargate、custom networking、prefix delegation 和 multi-NIC 支持具有各自条件。 |
| **Original Weave Net project** | 历史上的 overlay 网络实现 | 原始 `weaveworks/weave` repository 已归档。不要将其描述为新集群活跃、受支持的默认方案。 |

### 策略、加密和可观测性

- Cilium 通过适用的 L7 组件提供 HTTP/DNS 感知策略，以及 cluster-wide/host policy。其 deny/allow 语义并非 Calico 的有序 Tier API。
- Calico Open Source 包括分层策略 tiers 和 host policy。当前产品矩阵将 application-layer policy、DNS/FQDN policy 和 Cluster Mesh 分配给 Cloud/Enterprise；不得悄然将这些功能归因于开源版本。Calico 文档化的 in-transit encryption 使用 WireGuard。
- Amazon EKS 为 Auto Mode 和受支持的 EC2/VPC-CNI 安装提供 `ClusterNetworkPolicy` Admin/Baseline 控制。AWS 所述的 DNS/FQDN `ApplicationNetworkPolicy` 功能适用于 **Auto Mode**。其名称并不意味着当前支持 HTTP-method/body 检查。
- Flannel 的可选 policy controller 有自己的要求；仅选择网络 backend 不会启用执行。
- 节点到节点加密、经过验证的 workload identity 和应用程序 mTLS 是不同的控制措施。网络 flow visibility 也不同于应用程序 tracing 或 process/file enforcement。

### 路由和性能

Calico 和 Cilium 可以使用 BGP 宣告路由；这本身并不提供 multi-cluster 服务发现、策略同步或加密。Flannel host-gw 使用直接路由，并要求适合的 layer-2 连接性。overlay 会增加封装和 MTU 考量，但不能根据 CNI 名称推断出通用性能排名。

之前的 100/98/95/85/80/75 percent 吞吐量数据没有可复现的工作负载、版本或测量来源。请使用可比硬件、内核、数据包/请求大小、并发度、加密/策略设置、吞吐量、丢包和尾延迟。单独的 [Pod 基准测试](06-pod-network-benchmark.md)保留了其自身的历史环境和测量结果。

## CNI 选择指南

首先选择所需的路由、策略、operating-system 和支持模型，然后测试该组合。

| 需求 | 评估路径 |
|---|---|
| 标准 EKS VPC 寻址和受支持的网络策略 | 在添加第二个策略引擎前评估 AWS VPC CNI/EKS 功能。 |
| 有序策略 tiers、host policy 或 infrastructure BGP | 评估相关 Calico 版本/dataplane 和路由先决条件。 |
| Cilium policy、Hubble 或选定的 mesh 功能 | 检查 Linux/kernel/platform 兼容性和 [Cilium mesh 指南](../service-mesh/cilium-service-mesh/README.md)。Envoy 仍是适用 L7 路径的一部分。 |
| 功能有限的小型网络 | 根据实际需求评估 Flannel 的 backend 和可选 policy controller。 |
| Process、syscall 或 file enforcement | 将 Tetragon 等 runtime-security 组件与网络策略分开评估。 |

### EKS Managed Add-on 配置

以下是一个 **configuration payload** 示例，而不是要求在同一工作负载上同时安装 Calico 和 VPC CNI policy engine 的说明：

```json
{
  "enableNetworkPolicy": "true"
}
```

字符串 `"true"` 是此设置所记录的类型。为现有 Kubernetes 版本选择兼容的 EKS add-on build，并检查该 build 的配置 schema：

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

upstream 1.23.0 release number 和 EKS `eksbuild` version 是不同的 identifiers。请将变更与预期的 managed add-on configuration 合并；不要盲目选择 `latest` 或替换无关值。从 third-party policy implementation 迁移还需要移除其现有 enforcement state，以及经过测试的节点/工作负载转换计划。

## EKS 网络基础

### EKS 默认网络架构

| 位置 / 组件 | 职责 |
|---|---|
| EKS-managed VPC | AWS 跨 Availability Zones 运行托管 Kubernetes control plane。 |
| Customer cluster VPC | Worker 网络、选定的 subnets 和 EKS-managed cross-account ENIs 提供通往 control plane 的已配置路径。 |
| 选定 customer VPC subnets 中的 ALB/NLB | 提供选定的 public 或 internal 应用程序入口点；internet gateway/NAT gateway 不能替代该路由配置。 |
| NAT gateway 或 private service endpoints | 提供工作负载设计所需的特定 outbound 路径。 |

之前的图将 control plane 放在 customer VPC 内部，并将 load balancers 放在其外部；现已由这些所有权边界取代。

### 按 Compute Mode 划分的 DNS 和网络

| Compute mode | DNS / 组件部署位置 |
|---|---|
| Standard EC2 nodes | 通常使用已配置的 CoreDNS Deployment 和已安装的网络组件；替代方案需要其自身受支持的配置。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI 和 kube-proxy 功能以托管节点 systemd services 运行。这些节点不需要 CoreDNS Deployment/add-on。 |
| Auto Mode 与 non-Auto nodes 混合 | 为 non-Auto nodes 保留 CoreDNS Deployment；它们不能使用另一个节点的 Auto Mode DNS service。 |

Auto Mode 的第一个 DNS resolver 是 node-local 的。upstream forwarding 和 control-plane communication 仍可能需要网络访问；这并不能保证每个与 DNS 相关的数据包都停留在节点上。AWS 为 Auto Mode 记录了 Admin 和 DNS policies，而 standard EC2 VPC-CNI Admin policy 具有其自身的版本/启用要求。

### VPC CNI 的工作方式

AWS VPC CNI 使用选定的 IPAM mode 为普通 Pod 提供 VPC-routable addresses。secondary IPv4 addresses、delegated prefixes、branch ENIs 和 multi-NIC configurations 各不相同；host-network Pod 共享节点网络。

![从 EC2 ENIs 向 Pod 分配 secondary-IPv4 的示意图，包括可选的 warm interface。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

这仅描述 secondary-IP mode。warm ENI 是一种可配置的分配策略，而非要求每个节点始终恰好预留一个。prefix delegation、custom networking 和 branch ENIs 具有不同的分配规则。

#### ENI 和 IP 限制

| Instance Type | Max ENIs | 每个 ENI 的 IPv4 slots | 旧版 secondary-IP bootstrap value |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

这些值已依据 VPC CNI 1.23.0 instance limits 和旧版 max-Pods table 验证。历史计算公式为 `ENIs × (IPv4 slots per ENI − 1) + 2`；这并非当前的通用建议。prefix delegation、custom networking、branch ENIs 和 multiple network cards 会改变地址容量。Kubernetes 调度还受到 kubelet `maxPods` 和资源的限制。EKS managed node groups 对少于 30 vCPUs 的实例将 `maxPods` 限制为 110，否则为 250；仅可用 IP 数量不会覆盖此限制。

### EKS 网络注意事项

#### IP 地址管理

对于 **Linux VPC CNI**，请通过选定的 add-on/Helm/DaemonSet 管理机制配置文档化的 environment variables。以下是一个 EKS add-on configuration fragment。带有 `enable-prefix-delegation` 的旧 `amazon-vpc-cni` ConfigMap 不会以这种方式配置 Linux IPAMD。应用变更时保留其他预期的 add-on values。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

或者，调整总分配下限和 free-IP target。配置 `MINIMUM_IP_TARGET` 或 `WARM_IP_TARGET` 中任一项时，它会优先于 `WARM_PREFIX_TARGET`；这些是替代策略，而不是四个彼此独立的累加 targets。分配仍以 prefix-sized units 发生。Nitro 支持、用于 IPv4 的连续 `/28` 空间以及适当的 kubelet Pod limit 是另外的先决条件。

Windows prefix allocation 是不同的配置路径：AWS 在 `amazon-vpc-cni` ConfigMap 中记录了 `enable-windows-prefix-delegation` 及其 warm-target keys。不要将 Linux environment-variable 流程原样复制到 Windows。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "MINIMUM_IP_TARGET": "5",
    "WARM_IP_TARGET": "2"
  }
}
```

#### Custom Networking

这些 IPv4 示例在预期的 AZ 和 VPC 中需要真实 subnet/security-group IDs。启用 custom networking，并通过每个节点的 zone label 选择其 ENIConfig。显式 ENIConfig node annotation 优先于该 label。以下示例名称在两种语言中使用相同 region；请将其替换为实际节点 zones。仅安装 ENIConfig objects 不会激活 custom networking。

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

以下项目会在本概述的其他地方被顺带提及。完整设置流程和测量数据位于链接的深入页面；本节按层次整理这些部分的差异及其适用位置。

### L2–L7 以及 Routers 与 Load Balancers 的区别

“Router”和“load balancer”经常出现在同一句话中，但它们回答的是不同问题。router（通常）会选择通往单个 destination 的一条路径；load balancer 使用分配算法从多个等效 candidates 中选择一个 target。

| Layer | Device/function | 决策依据 | Kubernetes/AWS 映射 |
|---|---|---|---|
| L2 (link) | Switch、bridge | Destination MAC address | CNI 创建的 veth pairs 和 Linux bridges，以及 ENI 暴露的 virtual NIC |
| L3 (network) | Router 或 transparent appliance insertion | 用于路由的 Destination IP；用于 appliance selection 的 flow identity | VPC 的隐式 router、TGW；GWLB 为 appliances 封装 IP packets |
| L4 (transport) | L4 load balancer | Connection/flow identity，通常为 5-tuple | NLB；kube-proxy (iptables、IPVS、nftables)；独立 eBPF Service implementations |
| L7 (application) | L7 load balancer/reverse proxy | 每个请求的 host、path、headers；protocol-aware | ALB、Ingress/Gateway API implementations、service-mesh sidecars (Envoy) |

关键区别在于 **分配单位**。L4 load balancer 通常为 TCP connection 或被跟踪的 UDP flow 选择 target。L7 proxy 可以为每个受支持的应用程序请求选择 target，包括共享同一 connection 的请求。GWLB 将 encapsulated IP flows 分配给 security appliances，而不是解析应用程序请求。flow stickiness 取决于已配置的 timeout、health 和 failover behavior；它并不保证 flow 永远不会被重新分配或中断。

> 📎 L2/L3 概念的协议级定义位于[网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)；ALB/NLB target types 和实际配置位于 [AWS Load Balancer Controller](03-aws-lb-controller.md)。

### Cross-Account/VPC 连接：TGW、VPC Peering、GWLB、PrivateLink、Lattice

这五种连接选项在 layer 和 traffic model 上有所不同。通过 TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering 和 VPC Lattice 测得的延迟见[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。本节添加了不在该对比表中的 GWLB，并按层次重新构建全部五种方案。

| Connectivity | Layer/model | 特性 |
|---|---|---|
| VPC Peering | L3，双向 IP 路由 | 不可传递；无法跨重叠 CIDRs 配置 |
| Transit Gateway (TGW) | L3，hub-and-spoke IP 路由 | 使用一个或多个 TGW route tables 上的 attachment associations 和 propagation；通过 RAM 跨账户共享 |
| Gateway Load Balancer (GWLB) | L3，transparent appliance insertion | 将原始 packet 封装在 GENEVE (UDP 6081) 中；VPC endpoint service model 将 consumer traffic 连接到 provider 的 appliance fleet |
| PrivateLink | Private endpoint connectivity | 由 NLB 支持的 endpoint service 是一种模型；也存在 resource endpoints。Consumer/provider CIDRs 可以重叠 |
| VPC Lattice | Application 和 resource networking | HTTP/HTTPS services 支持 L7 routing 和可选 IAM authorization；TLS passthrough 和 resource configurations 具有不同功能 |

GWLB 通过 Gateway Load Balancer endpoint 将 firewall 和 IDS/IPS 等 inspection appliances 插入 IP path。其默认 flow stickiness 使用五个字段；受支持的配置可改用两个或三个字段。请验证正向和返回路由、appliance health、encapsulation MTU、NACLs 以及实际 workloads/appliances 的 security groups。GWLB 本身没有 ALB 风格的 security group，并且 flow stickiness 不能替代 failure testing。

> 📎 完整 EKS/VPC Lattice 集成（Gateway API Controller、IAM authorization、routing）位于 [VPC Lattice](02-vpc-lattice.md)。

### DNS Resolver 和 Route Tables 实际如何工作

**DNS resolver：**AmazonProvidedDNS **即 Route 53 Resolver**。其地址包括主 VPC IPv4 网络地址加二（对于 `10.0.0.0/16` 为 `10.0.0.2`）以及 `169.254.169.253`；它根据 Resolver rules 解析关联的 private zones 和 public names。CoreDNS 通常提供已配置的 Kubernetes cluster domain，通常为 `cluster.local`；`kube-dns` 是其 Service name，而不是 namespace 或 DNS zone。外部 forwarding 遵循 Corefile 和 DNS Pod 可见的 resolver file。请检查这些设置，而不是假设节点的 resolver file 原样使用。在 Resolver endpoint 设计中，inbound endpoints 接收 on-premises queries，而 outbound endpoints 和关联 rules 将选定 VPC queries 转发至 on-premises DNS。Auto Mode 的 node-local resolver 不会消除 upstream dependencies。

**Route tables：**VPC route evaluation 通常使用 longest-prefix matching。AWS 允许替换 `local` route 的 target，并添加受支持的更具体 subnet routes 用于 appliance routing；`local` 并非无条件最具体的 route。对于相同 destinations，static VPC routes 优先于从 virtual private gateway 传播的 routes。以 TGW 为目标的 VPC route 是 static；TGW 内的 propagation 属于其单独的 route tables。无效 targets 可能留下会丢弃流量的 `blackhole` entries，因此除了 destination 外还应检查 route state。没有显式 route-table association 的 subnet 使用 VPC 的 main route table。

> 📎 TGW/Peering route priority 和 static-route configuration examples 位于[跨组织 VPC 连接的操作发现](05-cross-org-vpc-connectivity.md#operational-findings)。

### 内核 Data Plane：iptables、IPVS、eBPF 和 Packet Filtering

Linux Service forwarding 和 network-policy enforcement 可以使用不同机制。Netfilter 提供 iptables 和 nftables 使用的 packet-path hooks。eBPF implementations 可以附加到 XDP、tc 或 socket hooks，并在那里执行 Service selection。这并不意味着 eBPF-enabled cluster 中的每个 packet 都绕过 Netfilter 或 connection tracking；路径取决于 CNI、kernel、routing 和 feature configuration。

| 实现 | 所在位置 | 特性 |
|---|---|---|
| iptables | netfilter hooks 上的顺序 rule chains | 评估时间随 rule count 扩展 (O(n))；kube-proxy 长期默认 mode |
| IPVS | Kernel-native L4 load balancer，netfilter extension | 基于 hash 的查找（接近 O(1)）；从 Kubernetes 1.35 开始作为 kube-proxy mode 被弃用 |
| nftables | netfilter 的后继 framework，取代 iptables | 自 1.33 起为 kube-proxy stable mode；请先检查 kernel/CNI compatibility |
| eBPF (例如 Cilium) | 已配置的 XDP、tc 和 socket hooks | 可以替代 kube-proxy Service handling；它是独立实现，具有 path-specific Netfilter/conntrack behavior |

切换实现可能会留下 kernel rules 和 active connections。请遵循 distribution/CNI migration procedure，按要求 drain workloads，并在清理需要时计划 node restarts。用基于 eBPF 的 CNI 替换 kube-proxy 还需要受支持的 cutover order，以免实现争夺相同的 Service traffic。

> 📎 IPVS deprecation timeline 和 nftables stable transition 见[ Kubernetes 简介](../basics/04-kubernetes-introduction.md)；Cilium 的 eBPF kube-proxy replacement 见 [Cilium eBPF](cilium/02-ebpf.md)；Calico 的 eBPF data plane 及其 migration procedure 见 [Calico eBPF](calico/06-ebpf-dataplane.md)。

### Compute-Intensive Networking：ENI、EFA、NVLink 和 Optical Transceivers

ENI、EFA 和 NVLink 服务于不同路径。**ENI** 是附加到一个 Availability Zone 中 EC2 instance 的 virtual network interface；当 routing 和 policy 允许时，其普通 IP traffic 可以访问其他 AZs 和已连接 VPCs（见 [VPC CNI](01-vpc-cni.md)）。**EFA** 通过 libfabric 为兼容的 MPI/NCCL software 提供 OS-bypass device。**EFA device traffic 不可路由，且无法跨 VPC/AZ 边界**；EFA-with-ENA interface 的 ENA device 提供的普通 IP traffic 仍可路由。EFA-only interfaces 没有 ENA device 或 IP addressing。**NVLink** 在受支持系统内连接 GPUs，包括受支持的 rack-scale NVLink domains。请测量所选硬件、collective operations 和 placement，而不要假定其相对于 EFA 有固定 speedup。

**Optical transceivers** 是通用 data-center networking 概念。Copper DAC (Direct Attach Copper) cables 适合短距离；optical modules 和 fiber 支持其他距离和带宽需求。QSFP 和 OSFP 描述 module form factors，而非保证使用 optical media。请将此视为一般背景：它不能证明某个 AWS workload 的物理布线。

> 📎 NVLink/IMEX topology-aware scheduling 和 GPU Pod placement examples 位于 [AI/ML Infrastructure](../ai-ml/06-ai-infrastructure.md)；EFA 的 VPC/AZ boundary constraint 和测量结果位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。

### 下一代协议对 Kubernetes 的意义：HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) 及其 QUIC transport (RFC 9000) 的协议机制在[网络基础第 2 部分](../basics/06-network-fundamentals-part2.md)和[第 3 部分](../basics/06-network-fundamentals-part3.md)中介绍。此处仅涵盖实际影响 Kubernetes traffic distribution 的内容。

- **gRPC 和 L4 load balancers：**gRPC 通过 HTTP/2 connections multiplexes requests。L4 balancer 通常将已建立的 TCP connection 保持在其选定 endpoint；若该 endpoint 是 proxy，它可以进一步做出 routing decisions。仅添加 Pod 不会重新分配现有 connections。每 RPC 分配需要兼容的 L7 proxy 或 client-side policy。streaming RPC 仍是一次 call；其中的单个 messages 不会被独立均衡。
- **Gateway API 的 GRPCRoute：**Ingress 没有 gRPC-specific resource，但 Gateway API 使用 `GRPCRoute` 标准化 service/method-level routing。支持因 implementation 而异（可匹配的 header 数量、retry policies 等），因此请查阅 controller 自身文档。
- **HTTP/3/QUIC 实际深入集群的程度：**客户端和 edge（CDN、load balancer）之间的 HTTP/3 支持，与集群内部或 Ingress backend connection 上的 HTTP/3 支持是不同问题。许多 Ingress/Gateway implementations 仍对 backend 使用 HTTP/1.1 或 HTTP/2，是否支持端到端 HTTP/3 因 implementation 和 version 而异——请勿概括；请检查实际使用 controller 的文档。

## 网络子页面

本节详细涵盖以下主题：

### [从零开始的 Linux 网络](beginner/README.md) {#beginner-course}

如果你刚接触 Linux 或网络，请从[入门课程](beginner/README.md)开始。其八节课程将 CLI、寻址、DNS、SSH、防火墙、监控和综合项目串联起来。下方路径在这一基础上延伸至协议、内核和集群实现。

### [Linux 网络诊断练习](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

在学习 CNI implementations 前，请将[内核 socket 和数据包路径概念](../kernel/02-network-stack.md)连接到观测结果。使用[诊断测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)检查你的解读。

### [VPC CNI](01-vpc-cni.md)
EKS 网络使用适用于普通 Pod 的 VPC addresses，以及特定模式的 IPAM/policy 先决条件。

### [Cilium 深入解析](cilium/README.md)
基于 eBPF 的高性能 CNI 解决方案。提供 L7 Network Policy、Service Mesh 和可观测性（Hubble）等高级功能。

### [Calico 深入解析](calico/README.md)
最广泛使用的 CNI 之一。强大的 Network Policy、BGP 支持和企业功能。涵盖简介、架构、网络模式、BGP 深入解析、Network Policy、eBPF、高级主题、EKS 集成和运维指南。

### [VPC Lattice](02-vpc-lattice.md)
AWS 托管应用程序网络服务。跨 VPC、跨账户的 service-to-service 通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
将 Kubernetes Services 和 Ingress 与 AWS ELB (ALB/NLB) 集成。

### [Gateway API](04-gateway-api.md)
下一代 Kubernetes ingress API。标准化资源模型和基于角色的配置。

### [Pod 网络基准测试](06-pod-network-benchmark.md)
在 EKS 上测量的 Pod-to-pod RTT、HTTP latency 和 throughput，涵盖同一节点、同一 AZ 和跨 AZ，以及 DNS `ndots:5` query amplification。

## 网络故障排除

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

从安装了指定 tools 的现有 Pod 运行诊断。仅查询集群中安装的 CNI；Auto Mode system services 不是这些 DaemonSets。DNS 成功、TCP 可达性和应用程序 HTTP response 是不同检查。ICMP 可能被阻止或需要额外 privileges，因此仅 ping 失败不能证明 TCP service 不可达。

#### Service 不可达

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

使用 EndpointSlice 进行当前 endpoint 诊断。检查 Service selectors、target ports、endpoint readiness、address family 和适用 policy。仅在该 component 实际拥有 Service forwarding 时检查 kube-proxy logs；eBPF replacement 或 Auto Mode 需要其自身诊断。

#### Network Policy 调试

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium commands 检查由 DaemonSet reference 选定的一个 Agent；追踪 incident 时请选择受影响节点的 Agent。Calico native API installations 可能暴露不同 API group，因此请检查该 installation 提供的 resources。Kubernetes、Calico 和 AWS extension policies 是不同 resources，且可能具有不同 precedence。

### 网络性能测试

这个有界 TCP 练习使用发布者固定的 Netshoot v0.16 image index，其中包含 Linux AMD64 和 Arm64 images；其 Dockerfile 包含 `iperf3`。在允许 TCP 5201 的测试环境中创建这些 Pod。这是示例性工作负载，而不是经过测量的 CNI comparison。

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

client 会休眠一小时，命令将提供流量限制为每秒 10 Mbit，持续十秒。这会测试选定路径，而非最大 throughput。解读结果前，请记录实际 Pod/node/AZ placement、resource limits 和 policy。对于 Windows nodes，请选择 Windows-specific tools。完成后仅移除你创建的 test resources。

这些独立 diagnostic Pods 用于 connectivity tests。对于原生 EKS network-policy enforcement tests，请使用 Deployment/Job-managed Pods 以及文档化的 Service/container-port requirements。

## 最佳实践

### 1. IP 地址规划

- 设计足够大的 CIDR blocks
- 将 Pod network 与 Service network 分离
- 设计 subnets 时考虑未来扩展

### 2. 应用 Network Policies

使用此示例前，请创建隔离的 `networking-demo` namespace。它会选择其中的每个 Pod，并根据标准 Kubernetes NetworkPolicy 语义隔离 ingress 和 egress；所需 DNS 和应用程序 flows 需要显式 allow rules。执行需要支持的 policy engine。额外 cluster/admin policy APIs 可能改变 precedence，并且这一个 manifest 并非完整的 zero-trust architecture。

- 应用 default deny policies (Zero Trust)
- 仅显式允许所需流量
- 隔离 namespaces

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

- 选择适当的 CNI（匹配工作负载）
- MTU 优化
- Kernel parameter 调优

### 4. 安全加固

- 选择受支持的 transport encryption，并验证其覆盖哪些流量。
- 在需要时配置 workload/application identity 和 mTLS；将其与基于 DNS/IP 的 allowlists 分开。
- 定期审查 policy、certificate 和 access-control changes。

### 5. 确保可观测性

- 收集网络指标
- 启用 flow logs
- 实现 distributed tracing

## 后续步骤

完成[入门课程](beginner/README.md)后，继续学习[内核网络栈](../kernel/02-network-stack.md)，然后是 [Linux 网络诊断练习](07-linux-network-diagnostics.md)及其[测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)。[学习路径](#learning-path)会在下方 CNI 和 AWS 主题之前，将这些基础知识连接到容器和 Services。

1. [VPC CNI](01-vpc-cni.md) - 默认 EKS CNI
2. [Cilium 深入解析](cilium/README.md) - 基于 eBPF 的网络
3. [Calico 深入解析](calico/README.md) - 路由、策略和 dataplanes
4. [VPC Lattice](02-vpc-lattice.md) - AWS 托管网络
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 集成
6. [Gateway API](04-gateway-api.md) - 下一代 ingress
7. [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) - 跨 AWS Organizations 连接 VPCs（现场验证）
8. [Pod 网络基准测试](06-pod-network-benchmark.md) - 按 node/AZ boundary 测量的 latency 和 throughput

---

## 参考资料

- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime 和 CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico 产品版本](https://docs.tigera.io/calico/latest/about)
- [Calico policy tiers](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow logs](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows 限制](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 网络和策略](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backends](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [Original Weave repository 状态](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS network policy 配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard 和 Admin network policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation 和 maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin 和 DNS policy deployment models](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on requirements](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane architecture](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer 概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE encapsulation (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoints 和 rules](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table evaluation order](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local routes 和更具体的 subnet routes](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static 和 propagated route priority](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS 地址和行为](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness 和 failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service virtual IPs 和 kube-proxy modes](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service names 和 forwarding configuration](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables 项目文档](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC over HTTP/2 和 load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
