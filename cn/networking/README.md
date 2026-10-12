# Kubernetes 网络

> **最后更新**: October 12, 2026
>
> **固定示例版本**: Cilium 1.20.1、Calico Open Source 3.32.2、Flannel 0.28.9，以及上游 AWS VPC CNI/Helm chart 1.23.0。
>
> **当前版本信息**: AWS 列出的 Kubernetes 1.31–1.37 的 EKS 托管 VPC CNI add-on 为 `v1.23.1-eksbuild.1`。Calico 3.33.0 是最新的 Open Source 版本，并已在 Kubernetes 1.35–1.37 上测试。更改固定示例前请查阅其发行说明。
>
> 这些版本并非经过联合测试的集群配置。安装前请检查每个产品的 Kubernetes/平台兼容矩阵。

## 概述

Kubernetes 网络是使容器化应用程序能够通信的核心基础设施层。本节涵盖从基础 Kubernetes 网络概念到 AWS EKS 环境中的高级 CNI (Container Network Interface) 解决方案和网络模式的全部内容。

## 学习路径 {#learning-path}

完成入门课程后，使用[专家网络路径](expert/README.md)，将协议项目、路由策略、EVPN、Linux 性能、云设计和自动化评估串联起来。请先检查每个工作簿的环境、证据和恢复标准。

如果你刚接触 Linux 或网络，请从[入门课程](beginner/README.md)开始。其八节课程将 CLI、地址分配、DNS、SSH、防火墙、监控和综合项目串联起来。下方路径会将这一基础扩展到协议、内核和集群实现。

从协议概念到观测结果逐步构建，再将其关联到容器、集群和云责任。使用先决条件选择切入点，并在继续前用预期结果检查理解程度。

| 阶段 | 角色 | 先决条件 | 结果 | 阅读 / 实践 |
|---|---|---|---|---|
| 协议、地址分配、HTTP | 建立术语体系 | 基本命令行使用 | 跟踪一个请求，并区分地址分配、传输和应用行为 | 网络基础[第 1 部分](../basics/06-network-fundamentals-part1.md)、[第 2 部分](../basics/06-network-fundamentals-part2.md)、[第 3 部分](../basics/06-network-fundamentals-part3.md)、[第 4 部分](../basics/06-network-fundamentals-part4.md) |
| Linux socket、VFS、数据包路径 | 将 API 连接到内核 | TCP/IP 基础 | 区分 FD、socket 缓冲区、窗口和队列 | [内核网络栈](../kernel/02-network-stack.md) |
| Linux 网络诊断 | 用证据检验假设 | socket 和数据包路径概念 | 关联 socket、数据包和应用观测 | [诊断实践](07-linux-network-diagnostics.md) · [测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md) |
| Docker 和容器网络 | 定位 namespace 边界 | Linux 数据包路径和基本诊断 | 解释 bridge 网络、发布的端口和容器名称解析 | [容器技术](../basics/03-container-technology.md) |
| Kubernetes Service、DNS、Ingress | 映射集群抽象 | 容器网络 | 跟踪一个名称如何经由 Service 到达其 endpoint，并识别 ingress 角色 | [服务与网络](../core/03-services-networking.md) · [实验](../labs/core/03-services-networking-lab.md) |
| eBPF、CNI、策略 | 比较实现职责 | Pod 和 Service 路径 | 区分数据包转发、策略执行和可观测性 | [eBPF 基础](../basics/05-ebpf-fundamentals.md) · [Cilium](cilium/README.md) · [Calico](calico/README.md) |
| AWS 网络边界和性能 | 将模型应用于云路径 | CNI 概念和测量技能 | 识别 VPC、节点和 AZ 边界，并在上下文中解读测量结果 | [VPC CNI](01-vpc-cni.md) · [AWS Load Balancer Controller](03-aws-lb-controller.md) · [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) · [Pod 网络基准测试](06-pod-network-benchmark.md) |

## Kubernetes 网络模型

当前 Kubernetes 模型提供了一个 Pod 网络，Pod 可在节点之间直接通信，无需地址转换或代理，**但受有意设置的网络分段约束**。kubelet 等节点 Agent 必须能够访问其所在节点上的 Pod。网络策略、路由和应用监听器仍决定特定连接是否成功。

普通 Pod 有自己的网络 namespace 和集群范围地址；同一 Pod 中的容器共享该 namespace 和 localhost。host-network Pod 共享节点网络，而 dual-stack 或多网络配置需要更精确的地址处理。重新创建 Pod 可能会分配不同 IP；重启同一 Pod 内的容器不一定会重新创建其网络 sandbox。

| 组件 | 角色 |
|---|---|
| Pod 网络 | 工作负载网络 namespace 之间的地址分配和连接性 |
| Service/发现 | 在不断变化的 endpoint 之上提供稳定的服务名称或虚拟地址 |
| Ingress/Gateway 实现 | 配置的外部入口和应用路由 |
| 网络策略引擎 | 执行所选实现支持的策略 |

这些角色不构成强制性的串行数据包路径。Service 转换、L7 代理和工作负载策略都可能改变特定请求穿越网络的方式。

### Pod 网络

Pod 网络为 Pod 通信提供地址分配和路由。下图展示了普通 IPv4 Pod；其中的连接假定适用策略和网络控制允许这些连接。

![两个节点上说明性的直接 IPv4 Pod 路径；连接性取决于已配置的策略和路由。](../.gitbook/assets/en-networking-readme-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-1.html)

这些地址是说明性的普通 Pod 地址。有意隔离以及 host-network 或多网络配置需要单独解读。

#### Pod 网络实现方法

| 方法 | 描述 | 示例 CNI |
|--------|-------------|-------------|
| **Overlay Network** | 通过现有网络封装流量 | Flannel VXLAN、Calico VXLAN/IPIP、Cilium VXLAN/Geneve |
| **Native Routing** | 使用底层网络中的路由，而不使用该 overlay 封装 | AWS VPC CNI、Calico routing/BGP、Cilium native routing |
| **Conditional Encapsulation** | 根据已配置拓扑使用直连路径或封装 | 支持的 Calico/Flannel/Cilium 模式，具有不同先决条件 |

### Service 网络

Service 描述一组逻辑 endpoint（通常为 Pod）及其访问方式。ClusterIP 默认提供稳定的虚拟 IP；headless Service 省略该虚拟 IP，而 ExternalName 使用 DNS CNAME 映射。Service 也可以管理不带 Pod selector 的 endpoint。

![ClusterIP、NodePort、LoadBalancer 和 ExternalName Service 的典型入口机制；DNS 映射与数据包转发有所区分。](../.gitbook/assets/en-networking-readme-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-2.html)

这些是典型的暴露机制，而非安全保证。NodePort 范围和可访问的节点地址可配置；LoadBalancer 可以是内部的。ExternalName 返回 DNS 别名，且不会创建转发代理。

#### Service 类型特性

在 `default` 中创建带有匹配 `app: my-app` 的 Pod，并使其监听所示 target port。NodePort 默认分配范围为 30000–32767，且可配置。外部可达性仍取决于地址、路由和访问控制。

LoadBalancer 示例明确选择 **AWS Load Balancer Controller**，并使用 EC2 instance target 和分配的 NodePort。请先安装/配置该 controller 及其 IAM/subnet 先决条件。EKS Auto Mode 使用不同的 controller/class。此处端口 443 仅选择一个 TCP port；TLS 必须由 8443 上的 backend 提供，或在 load balancer 上单独配置。

这些端口映射展示通用 Kubernetes Service API。AWS 当前记录了额外的原生 EKS network-policy 要求：Service port 必须与 container port 匹配，且由 controller 管理、带有 `metadata.ownerReferences` 的 Pod 可提供可靠执行。在测试该策略实现之前，请将示例调整为符合这些要求。

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

Ingress 资源需要 controller 及其数据平面。此 HTTP 示例使用带有 `spec.ingressClassName: alb` 和 IP target 的 AWS LBC。引用的 `api-v1`、`api-v2` 和 `web-frontend` Service 必须存在于 `default` 中，暴露端口 80，并具有就绪的、可由 VPC 路由的 Pod endpoint。必要时请单独配置 HTTPS/certificate。其安装和 target 先决条件请参见 [LBC 指南](03-aws-lb-controller.md)。

Ingress 定义将 HTTP/HTTPS 流量路由到内部集群 Service 的规则。

![到 Service backend 和 Pod 的逻辑 Ingress host/path 路由。](../.gitbook/assets/en-networking-readme-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-3.html)

此框表示 Ingress 数据平面功能。AWS LBC 配置 ALB；应用流量不会穿过 controller 的协调过程。根据 target mode，数据平面可直接到达 Pod IP 或 NodePort，而不是将 Service 虚拟 IP 作为字面意义上的额外跳点穿越。

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

CNI 将 runtime 配置容器网络时所用的接口标准化。对于当前 Kubernetes，kubelet 通过 CRI 请求 Pod-sandbox 操作，并由 **container runtime 管理 CNI**。Kubernetes 1.24 中已移除 kubelet 旧有的直接 CNI 管理 flags。

### Runtime 和 Plugin 职责

| 参与方 | 职责 |
|---|---|
| kubelet | 通过 container runtime interface 请求创建/删除 sandbox |
| Container runtime | 选择网络配置并调用 CNI plugin chain |
| CNI plugin | 接收配置，执行 ADD/DEL 及其他支持的操作，并返回结果 |
| IPAM 实现 | 分配/释放地址；可以是委托的 plugin，也可以是 provider-specific Agent 的一部分 |
| 可选节点 Agent | 维护 provider-specific 路由、策略、IP pool 或 datapath 状态 |

runtime 通过 CNI 接口将配置传递给 plugin；并非每个 plugin 都必须有独立的长运行 Agent 或 IPAM binary。接口类型也各有不同：veth pair 很常见，但并非唯一实现。

## CNI 对比

| 项目 / 范围 | 网络和策略 | 需要区分的功能与限制 |
|---|---|---|
| **Cilium 1.20.1** | eBPF 网络；适用 L7 功能使用 Envoy；Cilium 网络策略和 Hubble | Linux worker dataplane，具有 AMD64/Arm64 要求。Windows CLI 可用性不代表支持 Windows CNI。WireGuard/IPsec 与 Beta ztunnel mTLS 的范围不同。 |
| **Calico Open Source 3.32.2 示例；3.33.0 当前版本** | 路由/封装选择；iptables、nftables 和 eBPF 选项；有序策略 tier 以及 host/workload 策略 | Calico 3.33.0 已在 Kubernetes 1.35–1.37 上测试。升级前请查阅发行说明。Windows 有独立限制，包括不支持 Linux eBPF 或 WireGuard dataplane。Whisker/Goldmane flow 可观测性为 Tech Preview。付费功能请查阅 edition matrix。 |
| **Flannel 0.28.9** | host subnet 分配和节点间传输；VXLAN、host-gw 和其他 backend | `flanneld` 本身不执行 NetworkPolicy；chart 的可选 `netpol.enabled` 部署 SIGs policy controller。WireGuard 是已记录的 backend；IPsec 是实验性功能。Windows VXLAN 有特定设置/限制。 |
| **AWS VPC CNI 1.23.0 上游/Helm 示例；EKS add-on `v1.23.1-eksbuild.1`** | VPC 地址分配和 EC2 ENI/prefix；受支持 Linux EC2 节点上的 EKS standard 和 Admin network-policy 功能 | AWS 为 Kubernetes 1.31–1.37 列出此托管 add-on build；请验证区域可用性和集群实际版本。EKS Auto Mode 是具有额外 DNS 策略功能的托管网络实现。Windows、Fargate、custom networking、prefix delegation 和 multi-NIC 支持各有条件。 |
| **原始 Weave Net 项目** | 历史 overlay 网络实现 | 原始 `weaveworks/weave` repository 已归档。请勿将其描述为新集群中活跃、受支持的默认选项。 |

### 策略、加密和可观测性

- Cilium 通过适用的 L7 组件提供 HTTP/DNS 感知策略，以及 cluster-wide/host 策略。其 deny/allow 语义不同于 Calico 的有序 Tier API。
- Calico Open Source 包含分层策略 tier 和 host 策略。当前产品矩阵将 application-layer 策略、DNS/FQDN 策略和 Cluster Mesh 划为 Cloud/Enterprise；不得将这些功能默认为开源版功能。Calico 记录的传输中加密使用 WireGuard。
- Amazon EKS 为 Auto Mode 和受支持的 EC2/VPC-CNI 安装提供 `ClusterNetworkPolicy` Admin/Baseline 控制。AWS 所述 DNS/FQDN `ApplicationNetworkPolicy` 功能适用于 **Auto Mode**。其名称并不表示当前支持 HTTP method/body 检查。
- Flannel 的可选策略 controller 有自身要求；仅选择网络 backend 不会启用执行。
- 节点间加密、经认证的工作负载身份和应用 mTLS 是不同的控制措施。网络流可见性也不同于应用 tracing 或进程/文件执行。

### 路由和性能

Calico 和 Cilium 可以使用 BGP 宣告路由；这本身不提供多集群 Service 发现、策略同步或加密。Flannel host-gw 使用直连路由，并需要合适的 layer-2 连接。overlay 会增加封装和 MTU 考量，但不能仅从 CNI 名称推断通用性能排名。

先前的 100/98/95/85/80/75 percent 吞吐量数字没有可复现实验负载、版本或测量来源。请使用可比硬件、kernel、数据包/请求大小、并发量、加密/策略设置、吞吐量、丢包和 tail latency。单独的 [Pod 基准测试](06-pod-network-benchmark.md)保留自身的历史环境和测量数据。

## CNI 选择指南

先选择所需的路由、策略、操作系统和支持模型，然后测试该组合。

| 需求 | 评估路径 |
|---|---|
| 标准 EKS VPC 地址分配和受支持网络策略 | 在添加第二个策略引擎前，评估 AWS VPC CNI/EKS 功能。 |
| 有序策略 tier、host 策略或基础设施 BGP | 评估相关 Calico edition/dataplane 和路由先决条件。 |
| Cilium 策略、Hubble 或选定 mesh 功能 | 检查 Linux/kernel/平台兼容性和 [Cilium mesh 指南](../service-mesh/cilium-service-mesh/README.md)。Envoy 仍是适用 L7 路径的一部分。 |
| 功能集有限的小型网络 | 根据实际需求评估 Flannel 的 backend 和可选策略 controller。 |
| 进程、syscall 或文件执行 | 将 Tetragon 等 runtime-security 组件与网络策略分开评估。 |

### EKS 托管 Add-on 配置

以下是 **configuration payload** 示例，而不是让你在相同工作负载上同时安装 Calico 和 VPC CNI 策略引擎的说明：

```json
{
  "enableNetworkPolicy": "true"
}
```

字符串 `"true"` 是此设置记录的类型。为现有 Kubernetes 版本选择兼容的 EKS add-on build，并检查该 build 的配置 schema：

```bash
EKS_REGION=ap-northeast-2
KUBERNETES_MINOR=1.35  # Replace with the existing cluster's minor version
aws eks describe-addon-versions --region "$EKS_REGION" --addon-name vpc-cni \
  --kubernetes-version "$KUBERNETES_MINOR"
: "${VPC_CNI_ADDON_VERSION:?Set the compatible eksbuild version selected from metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION"
```

上游 1.23.0 release number 与 EKS `eksbuild` version 是不同标识符。AWS 当前 add-on 表为 Kubernetes 1.31–1.37 列出 `v1.23.1-eksbuild.1`；请在目标 Region 中使用 `describe-addon-versions` 选择兼容 build。将更改合并到预期的托管 add-on 配置中；不要盲选 `latest` 或替换无关值。从第三方策略实现迁移还需要移除其现有执行状态，并制定经过测试的节点/工作负载过渡计划。

## EKS 网络基础

### EKS 默认网络架构

| 位置 / 组件 | 职责 |
|---|---|
| EKS-managed VPC | AWS 在多个 Availability Zone 中运行托管 Kubernetes control plane。 |
| Customer cluster VPC | Worker 网络、选定 subnet 和 EKS-managed cross-account ENI 提供到 control plane 的已配置路径。 |
| 选定 customer VPC subnet 中的 ALB/NLB | 提供所选的公共或内部应用入口；internet gateway/NAT gateway 不能替代该路由配置。 |
| NAT gateway 或 private service endpoint | 提供工作负载设计所需的特定出站路径。 |

先前图表将 control plane 放在 customer VPC 内并将 load balancer 放在其外；现已由这些所有权边界替代。

### 按 Compute Mode 划分的 DNS 和网络

| Compute mode | DNS / 组件位置 |
|---|---|
| Standard EC2 node | 通常使用已配置的 CoreDNS Deployment 和已安装网络组件；替代方案需要自身受支持的配置。 |
| Pure EKS Auto Mode | CoreDNS、VPC CNI 和 kube-proxy 功能作为托管 node systemd service 运行。这些节点不需要 CoreDNS Deployment/add-on。 |
| Auto Mode 与非 Auto node 混合 | 为非 Auto node 保留 CoreDNS Deployment；它们不能使用另一节点的 Auto Mode DNS service。 |

Auto Mode 的第一个 DNS resolver 位于节点本地。上游转发和 control-plane 通信仍可能需要网络访问；这并不保证每个 DNS 相关数据包都留在节点上。AWS 记录了 Auto Mode 的 Admin 和 DNS 策略，而 standard EC2 VPC-CNI Admin 策略有自身的版本/启用要求。

### VPC CNI 的工作方式

AWS VPC CNI 使用选定的 IPAM mode 为普通 Pod 提供可由 VPC 路由的地址。secondary IPv4 address、delegated prefix、branch ENI 和 multi-NIC 配置各不相同；host-network Pod 共享节点网络。

![从 EC2 ENI 向 Pod 分配 secondary-IPv4 的说明图，包含可选的 warm interface。](../.gitbook/assets/en-networking-readme-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-readme-9.html)

此图仅描述 secondary-IP mode。warm ENI 是可配置的分配策略，而非每个节点始终恰好保留一个的要求。prefix delegation、custom networking 和 branch ENI 有不同的分配规则。

#### ENI 和 IP 限制

| Instance Type | 最大 ENI 数 | 每个 ENI 的 IPv4 slot | 旧版 secondary-IP bootstrap 值 |
|---------------|----------|--------------|------------------------|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |

这些值已根据 VPC CNI 1.23.0 instance limits 和旧版 max-Pods 表验证。历史计算为 `ENIs × (IPv4 slots per ENI − 1) + 2`；它不是当前通用建议。prefix delegation、custom networking、branch ENI 和多张 network card 会改变地址容量。Kubernetes 调度还受 kubelet `maxPods` 和资源约束。EKS managed node group 对少于 30 vCPU 的 instance 将 `maxPods` 限制为 110，否则为 250；仅有可用 IP 数量无法突破该上限。

### EKS 网络注意事项

#### IP 地址管理

对于 **Linux VPC CNI**，通过所选 add-on/Helm/DaemonSet 管理机制配置已记录的环境变量。以下是 EKS add-on 配置片段。旧的带有 `enable-prefix-delegation` 的 `amazon-vpc-cni` ConfigMap 不会以这种方式配置 Linux IPAMD。应用更改时保留其他预期 add-on 值。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

或者，调整总分配下限和 free-IP target。当配置 `MINIMUM_IP_TARGET` 或 `WARM_IP_TARGET` 任一项时，其优先于 `WARM_PREFIX_TARGET`；这些是替代策略，而不是四个独立的累加 target。分配仍以 prefix-sized unit 发生。Nitro 支持、IPv4 的连续 `/28` 空间以及合适的 kubelet Pod limit 是独立的先决条件。

Windows prefix allocation 是不同配置路径：AWS 在 `amazon-vpc-cni` ConfigMap 中记录 `enable-windows-prefix-delegation` 及其 warm-target key。请勿将 Linux 环境变量过程不加修改地复制到 Windows。

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

这些 IPv4 示例在目标 AZ 和 VPC 中需要真实 subnet/security-group ID。启用 custom networking，并通过每个节点的 zone label 选择其 ENIConfig。显式 ENIConfig node annotation 的优先级高于该 label。下方示例名称在两种语言中使用相同 region；请将其替换为实际 node zone。仅安装 ENIConfig object 不会激活 custom networking。

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

以下项目在本概述的其他部分会被简略提及。完整设置流程和测量数据位于链接的深入页面；本节按层组织这些部分的差异及各自适用位置。

### L2–L7 以及 Router 和 Load Balancer 的区别

“Router”和“load balancer”经常出现在同一句话中，但它们回答不同的问题。router 为单个 destination 选择（通常）一条路径；load balancer 则使用分配算法从多个等效 candidate 中选出一个 target。

| Layer | 设备/功能 | 决策依据 | Kubernetes/AWS 映射 |
|---|---|---|---|
| L2 (link) | Switch、bridge | destination MAC address | CNI 创建的 veth pair 和 Linux bridge、ENI 暴露的 virtual NIC |
| L3 (network) | Router 或透明 appliance insertion | 用于路由的 destination IP；用于 appliance 选择的 flow identity | VPC 的隐式 router、TGW；GWLB 为 appliance 封装 IP packet |
| L4 (transport) | L4 load balancer | connection/flow identity，通常为 5-tuple | NLB；kube-proxy (iptables、IPVS、nftables)；独立 eBPF Service 实现 |
| L7 (application) | L7 load balancer/reverse proxy | 每个 request 的 host、path、header；协议感知 | ALB、Ingress/Gateway API 实现、service-mesh sidecar (Envoy) |

关键区别是 **分配单元**。L4 load balancer 通常为 TCP connection 或被跟踪的 UDP flow 选择 target。L7 proxy 可为每个受支持的 application request 选择 target，包括共享一个 connection 的 request。GWLB 在 security appliance 间分配封装的 IP flow，而不是解析 application request。flow stickiness 取决于配置的 timeout、health 和 failover 行为；它不保证 flow 绝不会被重新分配或中断。

> 📎 L2/L3 概念的协议级定义位于[网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)；ALB/NLB target type 和实际配置位于[AWS Load Balancer Controller](03-aws-lb-controller.md)。

### Cross-Account/VPC 连接：TGW、VPC Peering、GWLB、PrivateLink、Lattice

这五个连接选项在 layer 和流量模型上有所不同。TGW RAM sharing、VPC Peering、PrivateLink、TGW Peering 和 VPC Lattice 的测量延迟位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。本节增加了不在该对比表中的 GWLB，并按 layer 重新阐述全部五种选项。

| 连接方式 | Layer/模型 | 特性 |
|---|---|---|
| VPC Peering | L3、双向 IP 路由 | 不可传递；无法跨重叠 CIDR 配置 |
| Transit Gateway (TGW) | L3、hub-and-spoke IP 路由 | 使用一个或多个 TGW route table 的 attachment association 和 propagation；通过 RAM 跨账户共享 |
| Gateway Load Balancer (GWLB) | L3、透明 appliance insertion | 将原始 packet 封装在 GENEVE (UDP 6081) 中；VPC endpoint service model 将 consumer 流量连接到 provider 的 appliance fleet |
| PrivateLink | Private endpoint 连接 | NLB-backed endpoint service 是一种模型；也存在 resource endpoint。consumer/provider CIDR 可重叠 |
| VPC Lattice | Application 和 resource 网络 | HTTP/HTTPS service 支持 L7 路由和可选 IAM authorization；TLS passthrough 和 resource configuration 具有不同功能 |

GWLB 通过 Gateway Load Balancer endpoint 将 firewall 和 IDS/IPS 等 inspection appliance 插入 IP 路径。其默认 flow stickiness 使用五个字段；支持的配置可改用两个或三个字段。请验证转发和返回路由、appliance health、encapsulation MTU、NACL，以及实际 workload/appliance 的 security group。GWLB 本身没有 ALB 式 security group，flow stickiness 也不能替代故障测试。

> 📎 完整 EKS/VPC Lattice 集成（Gateway API Controller、IAM authorization、routing）位于[VPC Lattice](02-vpc-lattice.md)。

### DNS Resolver 和 Route Table 的实际行为

**DNS resolver：**AmazonProvidedDNS **即 Route 53 Resolver**。其地址包括主 VPC IPv4 network address 加二（对于 `10.0.0.0/16` 为 `10.0.0.2`）及 `169.254.169.253`；它按照 Resolver rule 解析关联的 private zone 和 public name。CoreDNS 通常为已配置 Kubernetes cluster domain（通常为 `cluster.local`）提供服务；`kube-dns` 是其 Service name，而不是 namespace 或 DNS zone。外部转发遵循 Corefile 及 DNS Pod 可见的 resolver file。请检查这些设置，而不要假设节点的 resolver file 未经修改地使用。在 Resolver endpoint 设计中，inbound endpoint 接受 on-premises query，而 outbound endpoint 和关联 rule 将选定 VPC query 转发到 on-premises DNS。Auto Mode 的 node-local resolver 不会消除上游依赖。

**Route table：**VPC 路由评估通常使用 longest-prefix matching。AWS 允许替换 `local` route 的 target，并添加受支持的 more-specific subnet route 用于 appliance routing；`local` 并非无条件最具体路由。对于相同 destination，静态 VPC route 优先于 virtual private gateway 传播的 route。以 TGW 为 target 的 VPC route 是静态的；TGW 内的 propagation 属于其独立 route table。无效 target 可能留下会丢弃流量的 `blackhole` entry，因此除 destination 外还应检查 route state。未显式关联 route table 的 subnet 使用 VPC main route table。

> 📎 TGW/Peering route priority 和 static-route 配置示例位于[跨组织 VPC 连接的运维发现](05-cross-org-vpc-connectivity.md#operational-findings)。

### Kernel Data Plane：iptables、IPVS、eBPF 和 Packet Filtering

Linux Service 转发和 network-policy 执行可以使用不同机制。Netfilter 提供 iptables 和 nftables 使用的数据包路径 hook。eBPF 实现可附加在 XDP、tc 或 socket hook，并在那里执行 Service 选择。这并不意味着 eBPF-enabled cluster 中的每个 packet 都绕过 Netfilter 或 connection tracking；路径取决于 CNI、kernel、routing 和 feature 配置。

| 实现 | 所在位置 | 特性 |
|---|---|---|
| iptables | netfilter hook 上的顺序 rule chain | 评估时间随 rule 数量增长 (O(n))；kube-proxy 长期默认 mode |
| IPVS | kernel-native L4 load balancer，netfilter extension | 基于 hash 的查找（接近 O(1)）；自 Kubernetes 1.35 起不再推荐作为 kube-proxy mode |
| nftables | netfilter 的 iptables 后继 framework | 自 1.33 起 kube-proxy 的 stable mode；先检查 kernel/CNI 兼容性 |
| eBPF（如 Cilium） | 已配置的 XDP、tc 和 socket hook | 可替代 kube-proxy Service handling；它是独立实现，具有 path-specific Netfilter/conntrack 行为 |

切换实现可能遗留 kernel rule 和活动 connection。请遵循 distribution/CNI 迁移过程，按需 drain workload，并在清理需要时规划 node restart。以基于 eBPF 的 CNI 替换 kube-proxy 还需要受支持的 cutover 顺序，以避免实现争用相同 Service 流量。

> 📎 IPVS 弃用时间线和 nftables stable 转换位于[Kubernetes 简介](../basics/04-kubernetes-introduction.md)；Cilium 的 eBPF kube-proxy replacement 位于[Cilium eBPF](cilium/02-ebpf.md)；Calico 的 eBPF data plane 及其迁移过程位于[Calico eBPF](calico/06-ebpf-dataplane.md)。

### 计算密集型网络：ENI、EFA、NVLink 和 Optical Transceiver

ENI、EFA 和 NVLink 服务于不同路径。**ENI** 是附加到一个 Availability Zone 中 EC2 instance 的 virtual network interface；当 routing 和 policy 允许时，其普通 IP traffic 可到达其他 AZ 和已连接 VPC（参见 [VPC CNI](01-vpc-cni.md)）。**EFA** 通过兼容 MPI/NCCL software 的 libfabric 提供 OS-bypass device。**EFA device traffic 不可路由，且无法跨 VPC/AZ 边界**；EFA-with-ENA interface 的 ENA device 上的普通 IP traffic 仍可路由。EFA-only interface 没有 ENA device 或 IP addressing。**NVLink** 连接受支持系统内的 GPU，包括受支持的 rack-scale NVLink domain。请测量选定硬件、collective operation 和 placement，而不要假定相对 EFA 有固定加速比。

**Optical transceiver** 是通用数据中心网络概念。Copper DAC (Direct Attach Copper) cable 适合短距离；optical module 和 fiber 支持其他距离和带宽要求。QSFP 和 OSFP 描述 module form factor，并不保证使用 optical media。请将此视为通用背景：它不能确定某个 AWS workload 的物理布线。

> 📎 NVLink/IMEX topology-aware scheduling 和 GPU Pod placement 示例位于[AI/ML 基础设施](../ai-ml/06-ai-infrastructure.md)；EFA 的 VPC/AZ 边界约束和测量数据位于[跨组织 VPC 连接](05-cross-org-vpc-connectivity.md)。

### 新一代协议对 Kubernetes 的意义：HTTP/3、gRPC、QUIC

HTTP/3 (RFC 9114) 的协议机制及其 QUIC transport (RFC 9000) 已在[网络基础第 2 部分](../basics/06-network-fundamentals-part2.md)和[第 3 部分](../basics/06-network-fundamentals-part3.md)中介绍。这里仅涵盖实际影响 Kubernetes 流量分配的内容。

- **gRPC 和 L4 load balancer：**gRPC 在 HTTP/2 connection 上多路复用 request。L4 balancer 通常将已建立 TCP connection 保留在选定 endpoint；如果该 endpoint 是 proxy，它可以作出进一步 routing 决策。仅添加 Pod 不会重新分配现有 connection。每 RPC 分配需要兼容的 L7 proxy 或 client-side policy。streaming RPC 保持为一次 call；其各 message 不会被独立负载均衡。
- **Gateway API 的 GRPCRoute：**Ingress 没有特定于 gRPC 的 resource，但 Gateway API 通过 `GRPCRoute` 标准化了 service/method-level routing。不同实现的支持各异（header match 数量、retry policy 等），因此请检查 controller 自身文档。
- **HTTP/3/QUIC 实际到达集群内部的程度：**client 与 edge（CDN、load balancer）之间的 HTTP/3 support，和集群内部或 Ingress backend connection 上的 HTTP/3 support 是不同问题。许多 Ingress/Gateway 实现仍通过 HTTP/1.1 或 HTTP/2 与 backend 通信，是否支持端到端 HTTP/3 因实现和版本而异——请勿概括；应检查实际使用 controller 的文档。

## 网络子页面

本节详细涵盖以下主题：

### [从头学习 Linux 网络](beginner/README.md) {#beginner-course}

如果你刚接触 Linux 或网络，请从[入门课程](beginner/README.md)开始。其八节课程将 CLI、地址分配、DNS、SSH、防火墙、监控和综合项目串联起来。下方路径会将这一基础扩展到协议、内核和集群实现。

### [专家网络路径](expert/README.md) {#expert-course}

完成入门课程后，使用[专家网络路径](expert/README.md)，将协议项目、路由策略、EVPN、Linux 性能、云设计和自动化评估串联起来。请先检查每个工作簿的环境、证据和恢复标准。

### [Linux 网络诊断实践](07-linux-network-diagnostics.md) {#linux-network-diagnostics}

在学习 CNI 实现前，将[内核 socket 和数据包路径概念](../kernel/02-network-stack.md)与观测结果关联起来。使用[诊断测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)检查你的解读。

### [VPC CNI](01-vpc-cni.md)
使用普通 Pod 的 VPC 地址及特定 mode 的 IPAM/策略先决条件进行 EKS 网络。

### [Cilium 深入解析](cilium/README.md)
基于 eBPF 的高性能 CNI 解决方案。提供 L7 Network Policy、Service Mesh 和可观测性（Hubble）等高级功能。

### [Calico 深入解析](calico/README.md)
最广泛使用的 CNI 之一。强大的 Network Policy、BGP 支持和企业功能。涵盖简介、架构、网络 mode、BGP 深入解析、Network Policy、eBPF、高级主题、EKS 集成和运维指南。

### [VPC Lattice](02-vpc-lattice.md)
AWS 托管 application networking service。跨 VPC、跨账户的 service-to-service 通信。

### [AWS Load Balancer Controller](03-aws-lb-controller.md)
将 Kubernetes Service 和 Ingress 与 AWS ELB (ALB/NLB) 集成。

### [Gateway API](04-gateway-api.md)
下一代 Kubernetes ingress API。标准化 resource model 和基于角色的配置。

### [Pod 网络基准测试](06-pod-network-benchmark.md)
在 EKS 上针对同一节点、同一 AZ 和跨 AZ 测量的 Pod-to-pod RTT、HTTP latency 和 throughput，以及 DNS `ndots:5` query amplification。

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

从具有指定工具的现有 Pod 运行诊断。只查询集群中已安装的 CNI；Auto Mode system service 并非这些 DaemonSet。DNS 成功、TCP 可达性和应用 HTTP response 是不同检查。ICMP 可能被阻止或需要额外权限，因此仅 ping 失败并不能证明 TCP service 不可达。

#### Service 不可达

```bash
NAMESPACE=default
SERVICE_NAME=my-service
kubectl -n "$NAMESPACE" get service "$SERVICE_NAME" -o yaml
kubectl -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl -n kube-system logs -l k8s-app=kube-proxy --tail=100
```

使用 EndpointSlice 进行当前 endpoint 诊断。检查 Service selector、target port、endpoint ready 状态、address family 和适用策略。仅当该组件实际负责 Service forwarding 时检查 kube-proxy log；eBPF replacement 或 Auto Mode 需要自身诊断。

#### Network Policy 调试

```bash
kubectl get networkpolicies.networking.k8s.io -A
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg endpoint list
# For a Calico installation using its standard CRD datastore:
kubectl get networkpolicies.crd.projectcalico.org -A
kubectl get globalnetworkpolicies.crd.projectcalico.org
```

Cilium command 检查由 DaemonSet reference 选择的一个 Agent；在追踪 incident 时选择受影响 node 的 Agent。Calico native API installation 可能公开不同 API group，因此请检查该 installation 提供的 resource。Kubernetes、Calico 和 AWS extension policy 是不同 resource，且其优先级可能不同。

### 网络性能测试

此有界 TCP 练习使用发布者固定的 Netshoot v0.16 image index，其中包含 Linux AMD64 和 Arm64 image；其 Dockerfile 包含 `iperf3`。在允许 TCP 5201 的 test environment 中创建这些 Pod。这是说明性 workload，而不是已测量的 CNI 对比。

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

client 休眠一小时，该 command 将提供流量限制为十秒内 10 Mbit/s。这会测试所选路径，而非最大 throughput。在解读结果前，记录实际 Pod/node/AZ placement、resource limit 和 policy。Windows node 请选用 Windows-specific tool。完成后仅删除你创建的 test resource。

这些独立诊断 Pod 用于连接性测试。对于原生 EKS network-policy execution 测试，请使用 Deployment/Job-managed Pod 和已记录的 Service/container-port 要求。

## 最佳实践

### 1. IP 地址规划

- 设计足够大的 CIDR block
- 将 Pod network 与 Service network 分开
- 设计 subnet 时考虑未来扩展

### 2. 应用网络策略

使用此示例前，请创建隔离的 `networking-demo` namespace。它选择其中的每个 Pod，并按标准 Kubernetes NetworkPolicy 语义隔离 ingress 和 egress；所需的 DNS 和 application flow 需要明确 allow rule。执行需要受支持的 policy engine。额外 cluster/admin policy API 可能改变优先级，且此 manifest 不是完整的 zero-trust architecture。

- 应用默认拒绝策略（Zero Trust）
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

- 选择合适的 CNI（匹配工作负载）
- MTU 优化
- Kernel 参数调优

### 4. 安全加固

- 选择受支持的 transport encryption，并验证其覆盖哪些流量。
- 必要时配置 workload/application identity 和 mTLS；将其与基于 DNS/IP 的 allowlist 分开。
- 定期审查 policy、certificate 和 access-control 变更。

### 5. 确保可观测性

- 收集网络指标
- 启用 flow log
- 实施 distributed tracing

## 后续步骤

完成[入门课程](beginner/README.md)后，继续学习[内核网络栈](../kernel/02-network-stack.md)，然后是[Linux 网络诊断实践](07-linux-network-diagnostics.md)及其[测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)。[学习路径](#learning-path)将这些基础关联到下方 CNI 和 AWS 主题之前的 container 和 Service。

1. [VPC CNI](01-vpc-cni.md) - 默认 EKS CNI
2. [Cilium 深入解析](cilium/README.md) - 基于 eBPF 的网络
3. [Calico 深入解析](calico/README.md) - 路由、策略和 dataplane
4. [VPC Lattice](02-vpc-lattice.md) - AWS 托管网络
5. [AWS Load Balancer Controller](03-aws-lb-controller.md) - ELB 集成
6. [Gateway API](04-gateway-api.md) - 下一代 ingress
7. [跨组织 VPC 连接](05-cross-org-vpc-connectivity.md) - 跨 AWS Organizations 连接 VPC（现场验证）
8. [Pod 网络基准测试](06-pod-network-benchmark.md) - 按 node/AZ 边界测量的 latency 和 throughput

---

## 参考资料

- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Container runtime 和 CNI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI specification](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Calico product edition](https://docs.tigera.io/calico/latest/about)
- [Calico Open Source 3.33.0 release](https://github.com/projectcalico/calico/releases/tag/v3.33.0)
- [Calico policy tier](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/tiered-policy)
- [Calico Whisker flow log](https://docs.tigera.io/calico/latest/observability/view-flow-logs)
- [Calico Windows limitation](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Flannel 0.28.9 networking 和 policy](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/README.md)
- [Flannel backend](https://raw.githubusercontent.com/flannel-io/flannel/v0.28.9/Documentation/backends.md)
- [原始 Weave repository 状态](https://api.github.com/repos/weaveworks/weave)
- [AWS VPC CNI 1.23.0](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [Amazon EKS 最新 VPC CNI add-on version](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS network policy 配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS standard 和 Admin network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS prefix delegation 和 maxPods](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
- [EKS Admin 和 DNS policy deployment model](https://aws.amazon.com/blogs/containers/enhance-amazon-eks-network-security-posture-with-dns-and-admin-network-policies/)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS add-on requirement](https://docs.aws.amazon.com/eks/latest/userguide/workloads-add-ons-available-eks.html)
- [EKS control plane architecture](https://docs.aws.amazon.com/eks/latest/best-practices/control-plane.html)
- [Netshoot v0.16 image metadata](https://hub.docker.com/v2/repositories/nicolaka/netshoot/tags/v0.16)
- [Netshoot v0.16 Dockerfile](https://raw.githubusercontent.com/nicolaka/netshoot/v0.16/Dockerfile)
- [Tetragon runtime security](https://tetragon.io/docs/overview/)
- [AWS LBC 3.5 NLB configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 Ingress configuration](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress/annotations.md)
- [Gateway Load Balancer concept](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-load-balancers.html)
- [GENEVE encapsulation (RFC 8926)](https://www.rfc-editor.org/rfc/rfc8926)
- [VPC DNS resolver](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)
- [Route 53 Resolver endpoint 和 rule](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- [VPC route table evaluation order](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [Local route 和 more-specific subnet route](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)
- [Static 和 propagated route priority](https://docs.aws.amazon.com/vpc/latest/userguide/route-tables-priority.html)
- [AmazonProvidedDNS 地址和行为](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [GWLB flow stickiness 和 failover](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/edit-target-group-attributes.html)
- [Kubernetes Service virtual IP 和 kube-proxy mode](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [CoreDNS Service name 和 forwarding configuration](https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/)
- [PrivateLink resource endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-resources.html)
- [Netfilter/iptables project documentation](https://www.netfilter.org/documentation/index.html)
- [EC2 Elastic Fabric Adapter](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [QUIC transport protocol (RFC 9000)](https://www.rfc-editor.org/rfc/rfc9000)
- [HTTP/3 (RFC 9114)](https://www.rfc-editor.org/rfc/rfc9114)
- [gRPC over HTTP/2 和 load balancing](https://grpc.io/blog/grpc-load-balancing/)
- [Gateway API GRPCRoute](https://gateway-api.sigs.k8s.io/guides/user-guides/grpc-routing/)
