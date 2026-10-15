# Kubernetes 网络

> **最后更新**：September 14, 2026。功能引用包括 Cilium 1.20.1、Calico Open Source 3.32、Flannel 0.28.9 和 AWS VPC CNI 1.23.0。安装前请检查每个产品的 Kubernetes/平台矩阵；这些并非经过联合测试的集群配置。

## 概述

Kubernetes 网络是支持容器化应用程序之间通信的核心基础设施层。本节涵盖从基本 Kubernetes 网络概念到高级 CNI（Container Network Interface）解决方案，以及 AWS EKS 环境中的网络模式。

## 学习路径 {#learning-path}

从协议概念和观测开始，再将其关联到容器、集群和云的职责。利用前置条件选择切入点，并在继续之前根据学习成果检查理解情况。

| 阶段 | 作用 | 前置条件 | 学习成果 | 阅读 / 实践 |
|---|---|---|---|---|
| 协议、寻址、HTTP | 建立术语体系 | 基本命令行使用 | 跟踪一个请求并区分寻址、传输和应用行为 | 网络基础[第 1 部分](../basics/06-network-fundamentals-part1.md)、[第 2 部分](../basics/06-network-fundamentals-part2.md)、[第 3 部分](../basics/06-network-fundamentals-part3.md)、[第 4 部分](../basics/06-network-fundamentals-part4.md) |
| Linux socket、VFS、数据包路径 | 将 API 连接到内核 | TCP/IP 基础 | 区分 FD、socket 缓冲区、窗口和队列 | [内核网络栈](../kernel/02-network-stack.md) |
| Linux 网络诊断 | 用证据验证假设 | Socket 和数据包路径概念 | 关联 socket、数据包和应用程序观测结果 | [诊断练习](07-linux-network-diagnostics.md) · [测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker 和容器网络 | 定位命名空间边界 | Linux 数据包路径和基本诊断 | 解释桥接网络、发布的端口和容器名称解析 | [容器技术](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | 映射集群抽象 | 容器网络 | 跟踪名称经由 Service 到达其 endpoint，并识别 Ingress 的角色 | [服务与网络](../core/03-services-networking.md) · [实验](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、策略 | 比较实现职责 | Pod 和 Service 路径 | 区分数据包转发、策略执行和可观测性 | [eBPF 基础](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS 网络边界和性能 | 将模型应用到云路径 | CNI 概念和测量技能 | 识别 VPC、节点和 AZ 边界，并结合上下文解读测量值 | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) · [Pod 网络基准测试](06-pod-network-benchmark.md) |

## Kubernetes 网络模型

当前 Kubernetes 模型提供一个 Pod 网络，其中 Pod 可以跨节点直接通信，无需地址转换或代理，**但须接受有意的网络分段约束**。kubelet 等节点 Agent 必须能够访问自身节点上的 Pod。网络策略、路由和应用程序监听器仍决定特定连接是否成功。

普通 Pod 具有自己的网络命名空间和集群范围地址；同一 Pod 中的容器共享该命名空间和 localhost。Host-network Pod 共享节点网络，双栈或多网络配置需要更精确的地址处理。重新创建 Pod 可能会分配不同的 IP；重启同一 Pod 内的容器并不一定会重新创建其网络沙箱。

| 组件 | 作用 |
|---|---|
| Pod 网络 | 工作负载网络命名空间之间的寻址和连接 |
| Service/服务发现 | 在不断变化的 endpoint 之上提供稳定的服务名称或虚拟地址 |
| Ingress/Gateway 实现 | 配置外部入口和应用程序路由 |
| 网络策略引擎 | 执行所选实现支持的策略 |

这些角色并不构成强制性的串行数据包路径。Service 转换、L7 代理和工作负载策略都可能改变特定请求穿过网络的方式。

### Pod 网络

Pod 网络为 Pod 通信提供寻址和路由。下图展示普通 IPv4 Pod；其连接假定适用的策略和网络控制允许这些连接。

![跨两个节点的示意性直接 IPv4 Pod 路径；连接受配置的策略和路由约束。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

这些地址是示意性的普通 Pod 地址。有意隔离以及 host-network 或多网络配置需要各自独立解读。

#### Pod 网络实现方法

| 方法 | 描述 | CNI 示例 |
|--------|-------------|-------------|
| **Overlay Network** | 在现有网络上封装流量 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | 在底层网络中使用路由，而不使用该 Overlay 封装 | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 根据已配置拓扑使用直接路径或封装 | 支持的 Calico/Flannel/Cilium 模式，具有不同前置条件 |

### Service 网络

Service 描述一组逻辑 endpoint（通常是 Pod）以及如何访问它们。ClusterIP 默认提供稳定的虚拟 IP；headless Service 省略该虚拟 IP，ExternalName 使用 DNS CNAME 映射。Service 也可以管理不带 Pod selector 的 endpoint。

![ClusterIP、NodePort、LoadBalancer 和 ExternalName Service 的典型入口机制；DNS 映射与数据包转发相区分。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

这些是典型的暴露机制，并非安全保证。NodePort 范围和可访问的节点地址可配置；LoadBalancer 可以是内部的。ExternalName 返回 DNS 别名，且不创建转发代理。

#### Service 类型特征

在 `default` 中创建匹配 `app: my-app` 的 Pod，并在所示 target port 上监听。NodePort 默认分配范围为 30000–32767，且可以配置。外部可达性仍取决于地址、路由和访问控制。

LoadBalancer 示例明确选择 **AWS Load Balancer Controller**，使用 EC2 instance target 和已分配的 NodePort。请先安装/配置该 Controller 及其 IAM/subnet 前置条件。EKS Auto Mode 使用不同的 Controller/class。此处端口 443 仅选择一个 TCP 端口；必须由后端在 8443 上提供 TLS，或在负载均衡器上单独配置。

这些端口映射说明通用 Kubernetes Service API。AWS 当前记录了其他原生 EKS 网络策略要求：Service port 必须与 container port 匹配，并且由 Controller 管理、具有 `metadata.ownerReferences` 的 Pod 可提供可靠执行。在测试该策略实现之前，请先使示例适应这些要求。

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

Ingress 资源需要 Controller 及其数据平面。此 HTTP 示例使用具有 `spec.ingressClassName: alb` 和 IP target 的 AWS LBC。引用的 `api-v1`、`api-v2` 和 `web-frontend` Service 必须存在于 `default` 中、暴露端口 80，并具有就绪且可由 VPC 路由的 Pod endpoint。需要时请单独配置 HTTPS/certificate。有关安装和 target 前置条件，请参阅 [LBC 指南](03-aws-lb-controller.md)。

Ingress 定义将 HTTP/HTTPS 流量路由到内部集群 Service 的规则。

![到 Service 后端和 Pod 的逻辑 Ingress host/path 路由。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

该框表示 Ingress 数据平面功能。AWS LBC 配置 ALB；应用程序流量不穿过 Controller 的协调过程。根据 target 模式，数据平面可以访问 Pod IP 或 NodePort，而不是将 Service 虚拟 IP 作为字面上的额外一跳穿过。

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

CNI 将 runtime 配置容器网络时使用的接口标准化。对于当前 Kubernetes，kubelet 通过 CRI 请求 Pod-sandbox 操作，而**容器 runtime 管理 CNI**。Kubernetes 1.24 已移除 kubelet 旧的直接 CNI 管理 flag。

### Runtime 和 Plugin 职责

| 参与者 | 职责 |
|---|---|
| kubelet | 通过 container runtime interface 请求创建/删除 sandbox |
| Container runtime | 选择网络配置并调用 CNI plugin chain |
| CNI plugin | 接收配置、执行 ADD/DEL 和其他受支持操作，并返回结果 |
| IPAM 实现 | 分配/释放地址；可以是委派的 plugin，也可以是 provider-specific Agent 的一部分 |
| 可选节点 Agent | 维护 provider-specific 路由、策略、IP pool 或 datapath state |

Runtime 通过 CNI 接口将配置传递给 plugin；并非每个 plugin 都必须有单独的长期运行 Agent 或 IPAM 二进制文件。接口类型也各不相同：veth pair 很常见，但并非唯一实现。

## CNI 对比

| 项目 / 范围 | 网络和策略 | 需要区分的功能和限制 |
|---|---|---|
| **Cilium 1.20.1** | eBPF 网络；适用于相关 L7 功能的 Envoy；Cilium 网络策略和 Hubble | Linux worker dataplane，具有 AMD64/Arm64 要求。Windows CLI 可用性不等于 Windows CNI 支持。WireGuard/IPsec 和 Beta ztunnel mTLS 的范围不同。 |
| **Calico Open Source 3.32** | 路由/封装选择；iptables、nftables 和 eBPF 选项；有序策略层级以及 host/workload 策略 | Windows 有单独限制，包括不支持 Linux eBPF 或 WireGuard dataplane。Whisker/Goldmane 流可观测性作为 Tech Preview 提供。请参阅 edition matrix 了解付费能力。 |
| **Flannel 0.28.9** | Host subnet 分配和节点间传输；VXLAN、host-gw 和其他 backend | `flanneld` 本身不执行 NetworkPolicy；chart 的可选 `netpol.enabled` 会部署 SIGs policy controller。WireGuard 是已记录的 backend；IPsec 是实验性的。Windows VXLAN 有特定设置/限制。 |
| **AWS VPC CNI 1.23.0 / EKS** | VPC 地址分配以及 EC2 ENI/prefix；受支持 Linux EC2 节点上的 EKS standard 和 Admin 网络策略能力 | EKS Auto Mode 是具有额外 DNS 策略能力的托管网络实现。Windows、Fargate、custom networking、prefix delegation 和 multi-NIC 支持具有单独条件。 |
| **原始 Weave Net 项目** | 历史 Overlay 网络实现 | 原始 `weaveworks/weave` repository 已归档。不要将其描述为新集群中活跃且受支持的默认选择。 |

### 策略、加密和可观测性

- Cilium 通过适用的 L7 组件提供 HTTP/DNS 感知策略，以及集群范围/host 策略。其 deny/allow 语义并非 Calico 的有序 Tier API。
- Calico Open Source 包含分层策略 tier 和 host 策略。当前产品矩阵将 application-layer 策略、DNS/FQDN 策略和 Cluster Mesh 分配给 Cloud/Enterprise；不得将它们默认归因于开源 edition。Calico 已记录的传输中加密使用 WireGuard。
- Amazon EKS 为 Auto Mode 和受支持的 EC2/VPC-CNI 安装提供 `ClusterNetworkPolicy` Admin/Baseline 控制。AWS 所描述的 DNS/FQDN `ApplicationNetworkPolicy` 功能适用于 **Auto Mode**。其名称并不意味着当前支持 HTTP method/body 检查。
- Flannel 的可选 policy controller 有自身要求；仅选择 networking backend 并不会启用执行。
- 节点间加密、经过认证的 workload identity 和应用程序 mTLS 是不同的控制措施。网络流可见性也不同于应用程序 tracing 或 process/file 执行。

### 路由和性能

Calico 和 Cilium 可以使用 BGP 宣告路由；这本身并不提供多集群 Service discovery、策略同步或加密。Flannel host-gw 使用直接路由，并需要合适的二层连接。Overlay 会增加封装和 MTU 考量，但不能从 CNI 名称推断通用性能排名。

原先的 100/98/95/85/80/75 percent throughput 数据没有可复现的 workload、版本或测量来源。请使用可比较的硬件、kernel、数据包/请求大小、并发度、加密/策略设置、吞吐量、丢包和尾延迟。单独的 [Pod benchmark](06-pod-network-benchmark.md) 保留其自身的历史环境和测量值。

## CNI 选择指南

首先选择所需的路由、策略、操作系统和支持模型，然后测试该组合。

| 需求 | 评估路径 |
|---|---|
| 标准 EKS VPC 寻址和受支持的网络策略 | 在添加第二个策略引擎前，评估 AWS VPC CNI/EKS 能力。 |
| 有序策略 tier、host 策略或基础设施 BGP | 评估相关 Calico edition/dataplane 和路由前置条件。 |
| Cilium 策略、Hubble 或选定 mesh 功能 | 检查 Linux/kernel/platform 兼容性及 [Cilium mesh 指南](../service-mesh/cilium-service-mesh/README.md)。Envoy 仍是适用 L7 路径的一部分。 |
| 功能集有限的小型网络 | 根据实际要求评估 Flannel 的 backend 和可选 policy controller。 |
| Process、syscall 或 file 执行 | 将 Tetragon 等 runtime-security 组件与网络策略分开评估。 |

### EKS 托管 Add-on 配置

以下是一个**配置 payload**示例，并非要求在相同 workload 上同时安装 Calico 和 VPC CNI policy engine：

```json
{
  "enableNetworkPolicy": "true"
}
```

字符串 `"true"` 是此设置已记录的类型。为现有 Kubernetes 版本选择兼容的 EKS add-on build，并检查该 build 的配置 schema：

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

上游 1.23.0 release number 和 EKS `eksbuild` version 是不同标识符。请将变更与预期的托管 add-on 配置合并；不要盲目选择 `latest` 或替换无关值。从第三方策略实现迁移还需要移除现有执行状态，并制定经过测试的节点/workload 过渡计划。

## EKS 网络基础

### EKS 默认网络架构

| 位置 / 组件 | 职责 |
|---|---|
| EKS-managed VPC | AWS 跨 Availability Zone 运行托管 Kubernetes control plane。 |
| Customer cluster VPC | Worker 网络、选定 subnet 和 EKS-managed cross-account ENI 提供到 control plane 的已配置路径。 |
| 选定 customer VPC subnet 中的 ALB/NLB | 提供所选的 public 或 internal 应用程序入口点；internet gateway/NAT gateway 不能替代该路由配置。 |
| NAT gateway 或 private service endpoint | 提供 workload 设计需要的特定 outbound 路径。 |

原图将 control plane 置于 customer VPC 内、将 load balancer 置于其外；现已由这些所有权边界取代。

### 按 Compute Mode 划分的 DNS 和网络

| Compute mode | DNS / 组件放置 |
|---|---|
| Standard EC2 node | 通常使用已配置的 CoreDNS Deployment 和已安装的网络组件；替代方案需要自己的受支持配置。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI 和 kube-proxy 功能作为托管节点 systemd service 运行。这些节点不需要 CoreDNS Deployment/add-on。 |
| Auto Mode 与 non-Auto node 混合 | 为 non-Auto node 保留 CoreDNS Deployment；它们不能使用另一节点的 Auto Mode DNS service。 |

Auto Mode 的第一个 DNS resolver 是 node-local。上游转发和 control-plane 通信仍可能需要网络访问；这并不保证每个 DNS 相关数据包都留在节点上。AWS 为 Auto Mode 记录了 Admin 和 DNS 策略，而 standard EC2 VPC-CNI Admin 策略有自身的版本/启用要求。

### VPC CNI 的工作方式

AWS VPC CNI 使用所选 IPAM mode 为普通 Pod 提供可由 VPC 路由的地址。Secondary IPv4 address、delegated prefix、branch ENI 和 multi-NIC 配置各不相同；host-network Pod 共享节点网络。

![从 EC2 ENI 向 Pod 分配 secondary IPv4 的示意图，包括可选的 warm interface。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

这仅描绘 secondary-IP mode。Warm ENI 是可配置的分配策略，并非要求每个节点始终恰好保留一个。Prefix delegation、custom networking 和 branch ENI 具有不同的分配规则。

#### ENI 和 IP 限制

| Instance Type | 最大 ENI 数 | 每个 ENI 的 IPv4 slot | Legacy secondary-IP bootstrap 值 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

这些值已根据 VPC CNI 1.23.0 instance limits 和 legacy max-Pods table 验证。历史计算为 `ENIs × (IPv4 slots per ENI − 1) + 2`；这不是当前通用建议。Prefix delegation、custom networking、branch ENI 和多个网卡会改变地址容量。Kubernetes scheduling 还受 kubelet `maxPods` 和资源限制。EKS managed node group 对少于 30 vCPU 的 instance 将 `maxPods` 限制为 110，否则为 250；可用 IP 数量本身不能覆盖该上限。

### EKS 网络注意事项

#### IP 地址管理

对于 **Linux VPC CNI**，请通过所选的 add-on/Helm/DaemonSet 管理机制配置已记录的 environment variable。以下是 EKS add-on configuration fragment。旧的带有 `enable-prefix-delegation` 的 `amazon-vpc-cni` ConfigMap 不会以这种方式配置 Linux IPAMD。应用变更时请保留其他预期的 add-on 值。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

或者，调整总分配下限和 free-IP target。配置 `MINIMUM_IP_TARGET` 或 `WARM_IP_TARGET` 中任一项时，它优先于 `WARM_PREFIX_TARGET`；这些是替代策略，而不是四个独立的累加 target。分配仍以 prefix-sized unit 进行。Nitro 支持、用于 IPv4 的连续 `/28` 空间和合适的 kubelet Pod limit 是单独前置条件。

Windows prefix allocation 是不同的配置路径：AWS 在 `amazon-vpc-cni` ConfigMap 中记录 `enable-windows-prefix-delegation` 及其 warm-target key。请勿将 Linux environment-variable 过程原样复制到 Windows。

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

这些 IPv4 示例要求在预期 AZ 和 VPC 中使用真实的 subnet/security-group ID。启用 custom networking，并通过每个节点的 zone label 选择其 ENIConfig。显式的 ENIConfig 节点 annotation 优先于该 label。以下示例名称在两种语言中使用相同区域；请将其替换为实际节点 zone。仅安装 ENIConfig object 不会激活 custom networking。

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

以下项目在本概述其他位置被顺带提及。完整设置过程和测量数据位于链接的深入页面；本节按层组织这些部分如何不同，以及各自适用的位置。

### L2–L7 和 Router 与 Load Balancer 的区别

“Router”和“load balancer”经常出现在同一句话中，但它们回答的是不同问题。Router（通常）为单一目的地选择一条路径；load balancer 使用分配算法从多个等效候选目标中选择一个。

| 层 | 设备/功能 | 决策依据 | Kubernetes/AWS 映射 |
|---|---|---|---|
| L2（链路） | Switch、bridge | 目的 MAC 地址 | 由 CNI 创建的 veth pair 和 Linux bridge、ENI 暴露的 virtual NIC |
| L3（网络） | Router 或 transparent appliance insertion | 用于路由的目的 IP；用于 appliance 选择的 flow identity | VPC 的 implicit router、TGW；GWLB 为 appliance 封装 IP 数据包 |
| L4（传输） | L4 load balancer | Connection/flow identity，通常是 5-tuple | NLB；kube-proxy（iptables、IPVS、nftables）；独立 eBPF Service 实现 |
| L7（应用） | L7 load balancer/reverse proxy | 每个请求的 host、path、header；协议感知 | ALB、Ingress/Gateway API 实现、service-mesh sidecar（Envoy） |

关键区别是**分配单位**。L4 load balancer 通常为一个 TCP connection 或被跟踪的 UDP flow 选择 target。L7 proxy 可以为每个受支持的应用程序请求选择 target，包括共享一个 connection 的请求。GWLB 将封装后的 IP flow 分配给 security appliance，而不是解析应用程序请求。Flow stickiness 取决于配置的 timeout、health 和 failover 行为；它并不保证 flow 永远不会被重新分配或中断。

> 📎 L2/L3 概念的协议级定义请参阅[网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)；ALB/NLB target type 和实际配置请参阅 [AWS Load Balancer Controller](03-aws-lb-controller.md)。

### Cross-Account/VPC 连接：TGW、VPC Peering、GWLB、PrivateLink、Lattice

这五种连接选项在层和流量模型上不同。跨 TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering 和 VPC Lattice 的测量延迟位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。本节增加了不在该比较表中的 GWLB，并按层重新构建所有五项。

| 连接方式 | 层/模型 | 特征 |
|---|---|---|
| VPC Peering | L3、双向 IP 路由 | 不可传递；不能跨重叠 CIDR 配置 |
| Transit Gateway (TGW) | L3、hub-and-spoke IP 路由 | 在一个或多个 TGW route table 中使用 attachment association 和 propagation；通过 RAM 进行 cross-account sharing |
| Gateway Load Balancer (GWLB) | L3、transparent appliance insertion | 在 GENEVE（UDP 6081）中封装原始数据包；VPC endpoint service model 将 consumer 流量连接到 provider 的 appliance fleet |
| PrivateLink | Private endpoint connectivity | NLB-backed endpoint service 是一种模型；resource endpoint 也存在。Consumer/provider CIDR 可以重叠 |
| VPC Lattice | Application 和 resource networking | HTTP/HTTPS service 支持 L7 路由和可选 IAM authorization；TLS passthrough 和 resource configuration 具有不同能力 |

GWLB 通过 Gateway Load Balancer endpoint 将 firewall 和 IDS/IPS 等 inspection appliance 插入 IP 路径。其默认 flow stickiness 使用五个字段；受支持配置也可以改用两个或三个字段。请验证正向和返回路由、appliance health、encapsulation MTU、NACL 以及实际 workload/appliance 的 security group。GWLB 本身没有 ALB 风格的 security group，flow stickiness 也不能替代故障测试。

> 📎 完整的 EKS/VPC Lattice 集成（Gateway API Controller、IAM authorization、routing）请参阅 [VPC Lattice](02-vpc-lattice.md)。

### DNS Resolver 和 Route Table 的实际行为

**DNS resolver：**AmazonProvidedDNS **就是 Route 53 Resolver**。其地址包括主 VPC IPv4 网络地址加二（对于 `10.0.0.0/16` 为 `10.0.0.2`）以及 `169.254.169.253`；它根据 Resolver rule 解析关联的 private zone 和 public name。CoreDNS 通常服务配置的 Kubernetes cluster domain，通常为 `cluster.local`；`kube-dns` 是其 Service 名称，而不是 namespace 或 DNS zone。外部转发遵循 DNS Pod 可见的 Corefile 和 resolver file。请检查这些设置，而不要假定节点的 resolver file 未经改变地被使用。在 Resolver endpoint 设计中，inbound endpoint 接受 on-premises query，而 outbound endpoint 及关联 rule 将选定的 VPC query 转发到 on-premises DNS。Auto Mode 的 node-local resolver 不会消除上游依赖。

**Route table：**VPC route evaluation 通常使用 longest-prefix matching。AWS 允许替换 `local` route 的 target，并为 appliance routing 添加受支持的 more-specific subnet route；`local` 并非无条件最特定路由。对于相同 destination，static VPC route 优先于由 virtual private gateway propagated 的 route。以 TGW 为 target 的 VPC route 是静态的；TGW 内部的 propagation 属于其单独的 route table。无效 target 可能留下会丢弃流量的 `blackhole` entry，因此除 destination 外还应检查 route state。没有显式 route-table association 的 subnet 使用 VPC 的 main route table。

> 📎 TGW/Peering route priority 和 static-route configuration 示例请参阅[跨组织 VPC 连接的操作发现](05-cross-org-vpc-connectivity.md#operational-findings)。

### Kernel Data Plane：iptables、IPVS、eBPF 和 Packet Filtering

Linux Service forwarding 和网络策略执行可以使用不同机制。Netfilter 提供供 iptables 和 nftables 使用的 packet-path hook。eBPF 实现可以附加到 XDP、tc 或 socket hook 并在其中执行 Service 选择。这并不意味着 eBPF-enabled 集群中的每个数据包都会绕过 Netfilter 或 connection tracking；路径取决于 CNI、kernel、routing 和 feature configuration。

| 实现 | 所在位置 | 特征 |
|---|---|---|
| iptables | netfilter hook 上的顺序 rule chain | 评估时间随 rule 数量扩展（O(n)）；kube-proxy 长期默认模式 |
| IPVS | Kernel-native L4 load balancer，netfilter extension | Hash-based lookup（接近 O(1)）；从 Kubernetes 1.35 开始作为 kube-proxy mode 弃用 |
| nftables | netfilter 的 iptables 后继 framework | 自 1.33 起 kube-proxy 的稳定 mode；请先检查 kernel/CNI 兼容性 |
| eBPF（例如 Cilium） | 已配置的 XDP、tc 和 socket hook | 可替代 kube-proxy Service handling；这是一种独立实现，具有 path-specific Netfilter/conntrack 行为 |

切换实现可能遗留 kernel rule 和 active connection。请遵循 distribution/CNI 迁移过程，按要求 drain workload，并在清理需要时规划节点重启。以 eBPF-based CNI 替代 kube-proxy 也需要受支持的 cutover order，以避免实现竞争相同的 Service 流量。

> 📎 IPVS 弃用时间线和 nftables stable transition 位于 [Kubernetes 简介](../basics/04-kubernetes-introduction.md)；Cilium 的 eBPF kube-proxy replacement 位于 [Cilium eBPF](cilium/02-ebpf.md)；Calico 的 eBPF data plane 及迁移过程位于 [Calico eBPF](calico/06-ebpf-dataplane.md)。

### Compute-Intensive Networking：ENI、EFA、NVLink 和 Optical Transceiver

ENI、EFA 和 NVLink 服务于不同路径。**ENI** 是附加到单个 Availability Zone 中 EC2 instance 的 virtual network interface；当 routing 和 policy 允许时，其正常 IP traffic 可以到达其他 AZ 和已连接的 VPC（参阅 [VPC CNI](01-vpc-cni.md)）。**EFA** 提供由兼容 MPI/NCCL software 通过 libfabric 使用的 OS-bypass device。**EFA device traffic 不可路由，且不能跨 VPC/AZ 边界**；EFA-with-ENA interface 的 ENA device 上的正常 IP traffic 仍可路由。EFA-only interface 没有 ENA device 或 IP addressing。**NVLink** 连接受支持系统内的 GPU，包括受支持的 rack-scale NVLink domain。请测量所选硬件、collective operation 和 placement，而不要假定相对 EFA 的固定加速比。

**Optical transceiver** 是通用数据中心网络概念。Copper DAC（Direct Attach Copper）cable 适用于短距离；optical module 和 fiber 支持其他距离和带宽要求。QSFP 和 OSFP 描述 module form factor，并不保证采用 optical media。请将此视为通用背景：它并不说明特定 AWS workload 的物理布线。

> 📎 NVLink/IMEX topology-aware scheduling 和 GPU Pod placement 示例位于 [AI/ML Infrastructure](../ai-ml/06-ai-infrastructure.md)；EFA 的 VPC/AZ 边界约束和测量位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。

### 下一代协议对 Kubernetes 的意义：HTTP/3、gRPC、QUIC

HTTP/3（RFC 9114）及其 QUIC transport（RFC 9000）的协议机制位于[网络基础第 2 部分](../basics/06-network-fundamentals-part2.md)和[第 3 部分](../basics/06-network-fundamentals-part3.md)。此处只涵盖实际影响 Kubernetes traffic distribution 的内容。

- **gRPC 和 L4 load balancer：**gRPC 在 HTTP/2 connection 上 multiplex request。L4 balancer 通常将已建立 TCP connection 保持在其选定 endpoint；如果该 endpoint 是 proxy，它可以做出进一步 routing decision。仅添加 Pod 不会重新分配现有 connection。每 RPC 分配需要兼容的 L7 proxy 或 client-side policy。Streaming RPC 仍是一项 call；其各个 message 不会被独立平衡。
- **Gateway API 的 GRPCRoute：**Ingress 没有 gRPC-specific resource，但 Gateway API 使用 `GRPCRoute` 标准化 service/method-level routing。支持因实现而异（header match 数量、retry policy 等），因此请检查 Controller 自身文档。
- **HTTP/3/QUIC 实际深入集群的程度：**Client 和 edge（CDN、load balancer）之间的 HTTP/3 支持，与集群内部或 Ingress backend connection 上的 HTTP/3 支持是不同问题。许多 Ingress/Gateway 实现仍对 backend 使用 HTTP/1.1 或 HTTP/2，是否支持 end-to-end HTTP/3 因实现和版本而异——请勿泛化；检查实际使用 Controller 的文档。

## 网络子页面

本节详细涵盖以下主题：

### [Linux 网络诊断练习](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

在研究 CNI 实现前，将[内核 socket 和 packet-path 概念](../kernel/02-network-stack.md)与观测关联。使用[诊断测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)检查你的解读。

### [VPC CNI](01-vpc-cni.md)
EKS 网络：为普通 Pod 提供 VPC 地址以及 mode-specific IPAM/policy 前置条件。

### [Cilium 深入解析](cilium/README.md)
高性能 eBPF-based CNI 解决方案。提供 L7 Network Policy、Service Mesh 和可观测性（Hubble）等高级功能。

### [Calico 深入解析](calico/README.md)
最广泛使用的 CNI 之一。强大的 Network Policy、BGP 支持和企业功能。涵盖简介、架构、网络模式、BGP 深入解析、Network Policy、eBPF、高级主题、EKS 集成和操作指南。

### [VPC Lattice](02-vpc-lattice.md)
AWS 托管 application networking service。跨 VPC、跨账户的 service-to-service 通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
将 Kubernetes Service 和 Ingress 与 AWS ELB（ALB/NLB）集成。

### [Gateway API](04-gateway-api.md)
下一代 Kubernetes ingress API。标准化资源模型和基于角色的配置。

### [Pod 网络基准测试](06-pod-network-benchmark.md)
在 EKS 上测量同一节点、同一 AZ 和跨 AZ 的 Pod-to-Pod RTT、HTTP 延迟和吞吐量，另含 DNS `ndots:5` query amplification。

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

从具有所述工具的现有 Pod 运行诊断。只查询集群中已安装的 CNI；Auto Mode system service 并不是这些 DaemonSet。DNS 成功、TCP 可达性和应用程序 HTTP response 是不同检查。ICMP 可能被阻止或需要额外权限，因此仅 ping 失败并不能证明 TCP service 不可达。

#### Service 不可达

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

使用 EndpointSlice 进行当前 endpoint 诊断。检查 Service selector、target port、endpoint readiness、address family 和适用策略。仅当该组件实际负责 Service forwarding 时才检查 kube-proxy log；eBPF replacement 或 Auto Mode 需要自己的诊断。

#### Network Policy 调试

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium 命令检查由 DaemonSet reference 选择的一个 Agent；追踪事件时请选择受影响节点的 Agent。Calico native API installation 可能公开不同 API group，因此请检查安装提供的 resource。Kubernetes、Calico 和 AWS extension policy 是不同 resource，可能具有不同优先级。

### 网络性能测试

此有界 TCP 练习使用发布者固定的 Netshoot v0.16 image index，其中包含 Linux AMD64 和 Arm64 image；其 Dockerfile 包含 `iperf3`。在允许 TCP 5201 的测试环境中创建这些 Pod。这是示例 workload，并非测量后的 CNI 比较。

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

Client 休眠一小时，该命令将十秒内提供的流量上限设为 10 Mbit/s。这会测试选定路径，而非最大吞吐量。解释结果前，请记录实际 Pod/node/AZ placement、resource limit 和 policy。Windows node 请选择 Windows-specific 工具。完成后仅移除你创建的测试 resource。

这些独立 diagnostic Pod 用于 connectivity test。对于原生 EKS network-policy enforcement test，请使用 Deployment/Job-managed Pod 以及已记录的 Service/container-port 要求。

## 最佳实践

### 1. IP 地址规划

- 设计足够大的 CIDR block
- 将 Pod network 与 Service network 分开
- 设计 subnet 时考虑未来扩展

### 2. 应用 Network Policy

使用此示例前，请创建隔离的 `networking-demo` namespace。它选择其中每个 Pod，并按标准 Kubernetes NetworkPolicy 语义隔离 ingress 和 egress；所需 DNS 和应用程序 flow 需要显式 allow rule。执行需要受支持的 policy engine。额外的 cluster/admin policy API 可以改变优先级，而此 manifest 并非完整的 zero-trust architecture。

- 应用默认 deny policy（Zero Trust）
- 仅明确允许所需流量
- 隔离 namespace

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

- 选择合适的 CNI（与 workload 匹配）
- MTU 优化
- Kernel parameter 调优

### 4. 安全加固

- 选择受支持的 transport encryption，并验证它覆盖哪些 traffic。
- 在需要时配置 workload/application identity 和 mTLS；使它们与基于 DNS/IP 的 allowlist 保持分离。
- 定期审查 policy、certificate 和 access-control 变更。

### 5. 确保可观测性

- 收集网络指标
- 启用 flow log
- 实现 distributed tracing

## 后续步骤

从[内核网络栈](../kernel/02-network-stack.md)开始，然后学习 [Linux 网络诊断练习](07-linux-network-diagnostics.md)及其[测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)。[学习路径](#learning-path)将这些基础知识连接到容器和 Service，然后再进入下方的 CNI 和 AWS 主题。

1. [VPC CNI](01-vpc-cni.md) - 默认 EKS CNI
2. [Cilium 深入解析](cilium/README.md) - eBPF-based 网络
3. [Calico 深入解析](calico/README.md) - 路由、策略和 dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS 托管网络
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 集成
6. [Gateway API](04-gateway-api.md) - 下一代 ingress
7. [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) - 跨 AWS Organization 连接 VPC（现场验证）
8. [Pod 网络基准测试](06-pod-network-benchmark.md) - 按 node/AZ 边界测量的延迟和吞吐量

---

## 参考资料

- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime 和 CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico 产品 edition](https://docs.tigera.io/calico/latest/about)
- [Calico policy tier](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow log](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows 限制](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 networking 和 policy](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backend](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [原始 Weave repository 状态](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [EKS network policy 配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard 和 Admin network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation 和 maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin 和 DNS policy deployment model](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on 要求](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane 架构](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress 配置](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer 概念](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE 封装（RFC 8926）](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoint 和 rule](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table evaluation order](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local route 和 more-specific subnet route](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static 和 propagated route priority](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS 地址和行为](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness 和 failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service virtual IP 和 kube-proxy mode](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service 名称和 forwarding configuration](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables 项目文档](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol（RFC 9000）](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3（RFC 9114）](https://www.rfc-editor.org/rfc/rfc9114)
- [HTTP/2 上的 gRPC 和 load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
