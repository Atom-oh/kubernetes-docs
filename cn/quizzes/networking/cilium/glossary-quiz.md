# 术语测验

本测验用于检验你对 Cilium、eBPF、Kubernetes 和网络相关关键术语及概念的理解。

## 选择题

1. eBPF 的全称是什么？
   * A) Enhanced Berkeley Packet Filter
   * B) Extended Berkeley Packet Filter
   * C) Embedded BPF Filter
   * D) External Berkeley Protocol Filter

<details>

<summary>显示答案</summary>

**答案：B) Extended Berkeley Packet Filter**

**说明：** eBPF 是 Extended Berkeley Packet Filter 的缩写，是最初为网络数据包捕获而开发的 BPF (Berkeley Packet Filter) 的扩展版本。eBPF 是一种允许程序在 Linux kernel 内安全运行的技术，可用于网络数据包处理、系统调用跟踪和性能监控等多种用途。Cilium 将 eBPF 作为其核心技术，以提供高性能网络、安全性和可观测性功能。

</details>

2. 在 Cilium 中，应用网络策略的基本单位是什么？
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>显示答案</summary>

**答案：C) Endpoint**

**说明：** 在 Cilium 中，Endpoint 指应用网络策略的网络端点，通常对应一个 Kubernetes Pod。每个 Endpoint 都有唯一的 ID，Cilium 基于这些 Endpoint 应用网络策略并控制流量。Endpoint 由 Cilium Agent 管理，并会在 Pod 创建时自动创建。你可以使用 `cilium endpoint list` 命令查看当前 Node 上的所有 Endpoint。

</details>

3. XDP (eXpress Data Path) 的主要特性是什么？
   * A) L7 协议分析
   * B) 在网络驱动程序层处理数据包
   * C) TLS 加密
   * D) DNS 解析

<details>

<summary>显示答案</summary>

**答案：B) 在网络驱动程序层处理数据包**

**说明：** XDP (eXpress Data Path) 是一种基于 eBPF 的技术，可在网络驱动程序层（中断上下文）处理数据包。这绕过了 kernel 网络协议栈，从而实现极高性能的数据包处理（每秒数百万个数据包）。XDP 可以通过 DROP、PASS、TX（发送）和 REDIRECT 等操作处理数据包。Cilium 使用 XDP 实现 DDoS 防护、高性能负载均衡和数据包过滤。

</details>

4. Cilium 的网络可观测性平台名称是什么？
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>显示答案</summary>

**答案：C) Hubble**

**说明：** Hubble 是 Cilium 的网络可观测性平台，使用 eBPF 实时监控和分析网络流。Hubble 的主要功能包括网络流监控、Service 依赖关系图生成、网络策略违规检测、性能指标收集和安全事件跟踪。Hubble 同时提供 CLI 和基于 Web 的 UI，并可与 Prometheus 和 Grafana 集成以可视化指标。

</details>

5. VXLAN 的全称和主要用途是什么？
   * A) Virtual Extended LAN - 虚拟网络创建
   * B) Virtual Extensible LAN - L2 覆盖网络
   * C) Very Extended LAN - 大规模网络扩展
   * D) Variable Extensible LAN - 动态网络配置

<details>

<summary>显示答案</summary>

**答案：B) Virtual Extensible LAN - L2 覆盖网络**

**说明：** VXLAN (Virtual Extensible LAN) 是一种网络虚拟化技术，可在 Layer 3 (L3) 网络之上覆盖 Layer 2 (L2) 网络。VXLAN 使用 UDP 封装进行隧道传输，并通过 24-bit VNI (VXLAN Network Identifier) 支持多达约 1,600 万个网络分段。在 Cilium 中，VXLAN 用作 Node 间 Pod 通信的覆盖网络模式。替代方案包括 GENEVE 或原生路由模式。

</details>

6. BPF Maps 的主要作用是什么？
   * A) 网络路由表管理
   * B) eBPF 程序之间的数据共享和存储
   * C) DNS 记录缓存
   * D) TLS 证书存储

<details>

<summary>显示答案</summary>

**答案：B) eBPF 程序之间的数据共享和存储**

**说明：** BPF Maps 是供 eBPF 程序存储和检索数据的键值存储。BPF Maps 还用于 kernel space 与 user space 之间的数据共享。主要类型包括 Hash Map（键值存储）、Array Map（基于索引的数组）、LRU Map（最近最少使用缓存）和 Ring Buffer（环形缓冲区）。Cilium 使用 BPF Maps 存储 service maps、backend maps、连接跟踪表等。

</details>

7. 在 Cilium 中，表示 Pod 安全身份的数字标识符称为什么？
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>显示答案</summary>

**答案：C) Identity**

**说明：** Cilium Identity 是根据 Pod 的 label 集合生成的数字标识符。具有相同 labels 的所有 Pod 共享相同的 Identity。基于 Identity 的策略使用 Identity 而非 IP addresses 来应用网络策略，因此即使 Pod IP 发生变化，策略也能保持一致。这种方法具有很高的可扩展性，即使在大型集群中也能高效运行。Endpoint ID 用于标识特定的 Pod 实例，与 Identity 不同。

</details>

8. IPAM 的全称及其在 Cilium 中的作用是什么？
   * A) IP Address Management - IP 地址分配和管理
   * B) Internet Protocol Access Manager - Internet 访问管理
   * C) IP Assignment Module - IP 分配模块
   * D) Internal Protocol Address Mapper - 内部协议地址映射

<details>

<summary>显示答案</summary>

**答案：A) IP Address Management - IP 地址分配和管理**

**说明：** IPAM (IP Address Management) 是负责规划、分配、跟踪和管理 IP 地址的系统。Cilium 支持多种 IPAM 模式：Cluster Pool（集群范围的 IP 池管理）、Kubernetes（使用 Kubernetes Node CIDR）、AWS ENI（使用 AWS Elastic Network Interface）、Azure（Azure 网络集成）和 GKE（Google Kubernetes Engine 集成）。IPAM 模式的选择取决于集群环境和网络要求。

</details>

9. WireGuard 的主要特性及其在 Cilium 中的用途是什么？
   * A) 数据包捕获工具 - 网络分析
   * B) 现代 VPN 协议 - Node 间流量加密
   * C) 负载均衡算法 - 流量分配
   * D) DNS 代理 - 名称解析

<details>

<summary>显示答案</summary>

**答案：B) 现代 VPN 协议 - Node 间流量加密**

**说明：** WireGuard 是一种现代、快速且安全的 VPN (Virtual Private Network) 隧道协议。它比 IPsec 更简单、更快，且代码库更小，因此更易于进行安全审计。在 Cilium 中，WireGuard 用于 Node 间流量加密。启用 WireGuard 后，集群中 Pod 之间的所有流量都会被透明加密。Cilium 可以使用 IPsec 或 WireGuard 实现加密。

</details>

10. CNI 的全称和作用是什么？
    * A) Container Network Interface - 容器网络插件的标准接口
    * B) Cloud Native Infrastructure - 云原生基础设施
    * C) Cluster Network Integration - 集群网络集成
    * D) Container Node Interconnect - 容器 Node 连接

<details>

<summary>显示答案</summary>

**答案：A) Container Network Interface - 容器网络插件的标准接口**

**说明：** CNI (Container Network Interface) 是一个 CNCF 项目，定义了容器运行时与网络插件之间的标准接口。在 Kubernetes 中，kubelet 通过 CNI 接口与网络插件（Cilium、Calico、Flannel 等）通信。CNI 为添加/移除容器时的网络配置定义了标准 API，从而能够通过插件架构集成各种网络解决方案。Cilium 是 CNI 实现之一。

</details>

## 简答题

11. 在 Cilium 中，提供 L7 proxy 和 service mesh 功能的开源组件名称是什么？

<details>

<summary>显示答案</summary>

**答案：** Envoy

**说明：** Envoy 是一个开源边缘和服务代理，用作 L7 proxy 和通信总线。Cilium 集成 Envoy 来实现 L7 网络策略。当你在 CiliumNetworkPolicy 中定义 L7 规则（HTTP、gRPC、Kafka、DNS 等）时，Cilium 会自动透明地部署 Envoy proxy。Envoy 还提供高级负载均衡、流量拆分和指标收集功能。

</details>

12. 在每个 Node 上运行并负责 eBPF program 加载、网络策略实施和 Endpoint 管理的 Cilium 组件名称是什么？

<details>

<summary>显示答案</summary>

**答案：** Cilium Agent

**说明：** Cilium Agent 是 Cilium 的核心组件，在每个 Kubernetes Node 上作为 DaemonSet 运行。Agent 的主要职责包括将 eBPF programs 加载和管理到 kernel 中、实施和应用网络策略、执行 Service 负载均衡、IP 地址管理 (IPAM)、网络 Endpoint 管理、指标和日志收集，以及与 Kubernetes API server 通信。每个 Node 上的本地网络操作均由该 Node 的 Cilium Agent 处理。

</details>

13. OSI model 中负责使用 IP addresses 路由数据包的层名称和编号是什么？

<details>

<summary>显示答案</summary>

**答案：** L3 (Network Layer)

**说明：** L3 (Network Layer) 是 OSI model 的第 3 层，负责使用 IP addresses 进行逻辑寻址和数据包路由。IP (Internet Protocol) 和 ICMP (Internet Control Message Protocol) 在该层运行。Cilium L3 策略可以根据 IP addresses 和 CIDR blocks 过滤流量。L2 (Data Link Layer) 使用 MAC addresses，而 L4 (Transport Layer) 使用 port numbers。

</details>

14. 为一组 Pod 提供稳定网络端点的 Kubernetes resource 名称是什么？

<details>

<summary>显示答案</summary>

**答案：** Service

**说明：** Kubernetes Service 是一种抽象，可为一组 Pod 提供稳定的网络端点（ClusterIP、DNS name）。Pod 会被动态创建/删除，其 IP 也可能变化，但 Service 提供固定的 IP 和 DNS names，以实现一致的客户端访问。Cilium 通过 eBPF 实现 Service 负载均衡，能够替代 kube-proxy。Service 类型包括 ClusterIP、NodePort、LoadBalancer 和 ExternalName。

</details>

15. 修改数据包 source IP address 的 NAT 类型名称是什么？

<details>

<summary>显示答案</summary>

**答案：** SNAT (Source NAT) 或 Masquerading

**说明：** SNAT (Source Network Address Translation) 是一种将数据包的 source IP address 转换为另一个 IP address 的 NAT 类型。Masquerading 是 SNAT 的一种特殊形式，会自动将 source IP 转换为出站 interface 的 IP。在 Cilium 中，masquerading 用于将集群内 Pod 出站流量的 source IP 转换为 Node IP。相反，DNAT (Destination NAT) 会修改 destination IP。

</details>

## 实践题

16. 将以下 Cilium 相关术语与其定义匹配：Cluster Mesh、CRD、FQDN、mTLS

<details>

<summary>显示答案</summary>

**答案：**

* **Cluster Mesh**：Cilium 的多集群网络功能。连接多个 Kubernetes 集群，以实现跨集群 Service 发现、负载均衡和网络策略执行。
* **CRD (Custom Resource Definition)**：通过定义自定义 resource 扩展 Kubernetes API 的方法。Cilium 使用 CRD 定义 CiliumNetworkPolicy、CiliumEndpoint 等。
* **FQDN (Fully Qualified Domain Name)**：主机的完整 domain name（例如，www.example.com）。Cilium FQDN 策略按 domain name 而非 IP 控制对外部 Service 的访问。
* **mTLS (mutual TLS)**：TLS 的扩展形式，client 和 server 都使用 certificates 对彼此进行身份验证。通过双向认证提供更强的安全性。

**说明：** 这些术语在 Cilium 和 Kubernetes 网络中经常使用。Cluster Mesh 适用于混合云/多云环境，CRD 是 Kubernetes 可扩展性的关键，FQDN 策略对于访问具有动态 IP 的外部 Service 的访问控制至关重要，而 mTLS 对于安全的 Service 间通信很重要。

</details>

17. 编写使用 Cilium CLI 查询当前集群中所有 Identity 及其 labels 的命令。

<details>

<summary>显示答案</summary>

**答案：**

```bash
# Query all Identities
cilium identity list

# Or query CiliumIdentity CRD using kubectl
kubectl get ciliumidentity -A

# Query detailed information for a specific Identity
cilium identity get <identity_id>

# Query detailed information in JSON format
kubectl get ciliumidentity <identity_id> -o json

# Filter Identities with specific labels
kubectl get ciliumidentity -o json | jq '.items[] | select(.metadata.labels."k8s:app" == "frontend")'

# Check Identity from Endpoints
cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
```

**说明：** Cilium Identity 是根据 Pod 的 label 集合生成的数字标识符。`cilium identity list` 命令显示当前集群中所有 Identity 及其 labels。CiliumIdentity 作为 CRD 存储，因此也可以使用 kubectl 查询。Identity 是网络策略的基础，所有具有相同 labels 的 Pod 都共享相同的 Identity。

</details>

18. 编写查询 BPF Map 内容的命令，以检查 Service 负载均衡 maps 和连接跟踪表。

<details>

<summary>显示答案</summary>

**答案：**

```bash
# Query BPF maps from Cilium Agent pod

# Service map (Service -> Backend mapping)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# Backend map (backend pod information)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list --backends

# Connection Tracking table
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global

# NAT map (masquerading/SNAT information)
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list

# Policy map (Identity-based policies)
kubectl exec -n kube-system ds/cilium -- cilium bpf policy get --all

# Endpoint map
kubectl exec -n kube-system ds/cilium -- cilium bpf endpoint list

# List all BPF maps
kubectl exec -n kube-system ds/cilium -- cilium bpf map list
```

**说明：** BPF Maps 是 Cilium data plane 中使用的核心数据结构。`cilium bpf lb list` 显示 Service 负载均衡信息，使你能够检查 Service IP/port 与 backend Pod IP/port 之间的映射。`cilium bpf ct list` 显示连接跟踪表，你可以在其中检查当前活动连接状态。这些命令对于网络故障排除和性能分析非常有用。

</details>

19. 编写一个使用基于 FQDN 的网络策略的 CiliumNetworkPolicy，使 Pod 仅能与外部的 `api.example.com` 和 `*.googleapis.com` domains 通信。

<details>

<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-egress-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  # Allow DNS queries (required for FQDN policy to work)
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"
  # Allow HTTPS traffic to specific FQDNs
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.googleapis.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**说明：** 基于 FQDN (Fully Qualified Domain Name) 的策略按 domain name 而不是 IP address 控制对外部 Service 的访问。要使此策略生效，必须允许 DNS 查询（第一条 egress 规则）。在 `toFQDNs` 中，`matchName` 指定精确的 domain name，`matchPattern` 指定使用 wildcards 的模式匹配。`*.googleapis.com` 允许所有 Google API subdomains。FQDN 策略尤其适用于访问具有动态 IP 的外部 Service 的访问控制。

</details>

20. 说明 Cilium Operator 的作用及其与 Cilium Agent 的差异，并编写检查 Operator 状态的命令。

<details>

<summary>显示答案</summary>

**答案：**

```bash
# Check Cilium Operator status
kubectl -n kube-system get deployment cilium-operator

# Check Operator pod status
kubectl -n kube-system get pods -l name=cilium-operator

# Check Operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Operator in overall Cilium status
cilium status --verbose

# Check CiliumIdentity resources (managed by Operator)
kubectl get ciliumidentity -A

# Check CiliumEndpoint resources
kubectl get ciliumendpoint -A
```

**Cilium Operator 与 Cilium Agent 职责比较：**

| 组件 | 运行位置 | 主要职责 |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cilium Agent** | 每个 Node (DaemonSet) | <p>- eBPF program 加载/管理<br>- 网络策略执行<br>- 本地 Endpoint 管理<br>- Service 负载均衡<br>- Node 级 IPAM</p> |
| **Cilium Operator** | 集群 (Deployment，1-2 个实例) | <p>- CiliumIdentity CRD 管理<br>- 集群级 IPAM<br>- CiliumEndpoint 同步<br>- 垃圾回收<br>- Cluster Mesh 连接管理</p> |

**说明：** Cilium Agent 在每个 Node 上运行并处理该 Node 的网络操作。相比之下，Cilium Operator 以单个实例（或为了 HA 而运行 2 个实例）的形式在整个集群中运行，并处理集群级协调任务。Operator 维护整个集群中的 Identity 一致性，清理未使用的 resources，并管理集群级 IPAM。

</details>

***

[返回学习材料](../../../networking/cilium/glossary.md) | [Cilium 测验列表](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/networking/cilium/README.md)
