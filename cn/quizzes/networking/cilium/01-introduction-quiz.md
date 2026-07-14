# Cilium 简介与基本概念测验

本测验用于检验您对 Cilium 基本概念、eBPF 技术、架构、关键组件以及 CNI 对比的理解。

## 选择题

1. Cilium 在内核中提供可编程数据路径的核心技术是什么？
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>

<summary>查看答案</summary>

**答案：B) eBPF**

**说明：**
eBPF（extended Berkeley Packet Filter）是一种允许程序在 Linux 内核中安全运行的技术。Cilium 利用 eBPF 在内核层实现网络、安全和可观测性功能。与基于 iptables 的解决方案相比，这提供了更高的性能和灵活性，并且无需重新编译内核即可动态应用网络策略。
</details>

2. Cilium 的网络策略支持哪个层级？
   - A) 仅 L3（网络层）
   - B) L3-L4（网络层和传输层）
   - C) L3-L7（网络层到应用层）
   - D) L2-L3（数据链路层和网络层）

<details>

<summary>查看答案</summary>

**答案：C) L3-L7（网络层到应用层）**

**说明：**
Cilium 支持从 L3（IP）、L4（TCP/UDP 端口）到 L7（应用层）的网络策略。这意味着它可以过滤 HTTP 方法、路径、标头、gRPC 方法、Kafka 主题等应用层流量。这种感知 API 的网络功能对于在微服务架构中实施细粒度安全策略非常有用。
</details>

3. Cilium 中哪个工具提供网络可见性和监控？
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>

<summary>查看答案</summary>

**答案：B) Hubble**

**说明：**
Hubble 是 Cilium 的网络可观测性层，使用 eBPF 实时监控和分析网络流。Hubble 提供服务依赖关系图生成、网络策略违规检测、HTTP/gRPC/DNS 请求跟踪以及网络延迟测量等功能。Prometheus 和 Grafana 是指标收集和可视化工具，而 Jaeger 是分布式追踪工具。
</details>

4. Cilium 的分布式负载均衡功能可以替代哪个 Kubernetes 组件？
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>

<summary>查看答案</summary>

**答案：B) kube-proxy**

**说明：**
Cilium 提供基于 eBPF 的 Service 负载均衡，可以完全替代 kube-proxy。kube-proxy 使用 iptables 或 IPVS 将 Service 流量路由到后端 Pod，而 Cilium 使用 eBPF 提供更高的性能和可扩展性。启用 Cilium 的 kube-proxy 替代模式后，还可使用 DSR（Direct Server Return）、Maglev 哈希和套接字层负载均衡等高级功能。
</details>

5. 以下哪项不是 Cilium 支持的节点间流量加密方式？
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) 两者均受支持（A 和 B）

<details>

<summary>查看答案</summary>

**答案：C) TLS**

**说明：**
Cilium 支持两种节点间流量加密方式：IPsec 和 WireGuard。IPsec 是广泛使用的传统 VPN 协议套件，而 WireGuard 是一种更现代、更简单、更快速的 VPN 协议。TLS 是应用层加密协议，其用途不同于 Cilium 的网络层加密。在 Cilium 中，您可以通过配置选项选择 IPsec 或 WireGuard 来实现透明网络加密。
</details>

6. Cilium 的多集群网络功能叫什么？
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>

<summary>查看答案</summary>

**答案：B) Cluster Mesh**

**说明：**
Cluster Mesh 是 Cilium 的多集群网络功能，可将多个 Kubernetes 集群连接为一个网络运行。借助 Cluster Mesh，可以实现跨集群 Service 发现、负载均衡和网络策略执行。此功能适用于混合云、多云和灾难恢复场景，使每个集群中的 Pod 能够直接访问其他集群中的 Service。
</details>

7. Cilium 使用什么技术来优化数据包处理性能？
   - A) DPDK
   - B) XDP (eXpress Data Path)
   - C) RDMA
   - D) SR-IOV

<details>

<summary>查看答案</summary>

**答案：B) XDP (eXpress Data Path)**

**说明：**
XDP (eXpress Data Path) 是一种基于 eBPF 的技术，允许在网络驱动程序层处理数据包。XDP 会绕过内核网络协议栈，从而实现极高性能的数据包处理（每秒数百万个数据包）。Cilium 使用 XDP 实现 DDoS 防御、高性能负载均衡和数据包过滤。DPDK、RDMA 和 SR-IOV 也是高性能网络技术，但 Cilium 的核心技术是 eBPF/XDP。
</details>

8. Cilium 1.18 支持的最低 Linux 内核版本是什么？
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>

<summary>查看答案</summary>

**答案：C) 4.19**

**说明：**
Cilium 1.18 要求使用 Linux 内核 4.19 或更高版本。这是因为 Cilium 所使用的 eBPF 功能在此版本及更高版本中得到完整支持。使用更新的内核版本（5.x 及以上）可获得额外的 eBPF 功能和更好的性能。例如，XDP 原生模式、BPF 到 BPF 函数调用和 BTF（BPF Type Format）等高级功能在较新的内核中支持得更好。
</details>

9. 以下哪个 CNI 插件不是基于 eBPF 的？
   - A) Cilium
   - B) Calico（eBPF 模式）
   - C) Flannel
   - D) 两者都不是基于 eBPF 的（仅 C）

<details>

<summary>查看答案</summary>

**答案：C) Flannel**

**说明：**
Flannel 是一种使用 VXLAN 或 host-gw 的简单覆盖网络解决方案，不使用 eBPF。相比之下，Cilium 从一开始就设计为基于 eBPF，Calico 在较新版本中也支持 eBPF 数据平面模式。Flannel 配置简单且资源占用较低，但不提供 L7 网络策略或高级可观测性功能。
</details>

10. Cilium Network Policy 的 API 版本是什么？
    - A) networking.k8s.io/v1
    - B) cilium.io/v1
    - C) cilium.io/v2
    - D) policy.cilium.io/v1

<details>

<summary>查看答案</summary>

**答案：C) cilium.io/v2**

**说明：**
CiliumNetworkPolicy 使用 `cilium.io/v2` API 版本。这是独立于标准 Kubernetes NetworkPolicy（`networking.k8s.io/v1`）的 CRD（Custom Resource Definition），用于支持 Cilium 的高级功能（L7 策略、基于 DNS 的策略、端点选择器等）。Cilium 也支持标准 Kubernetes NetworkPolicy，但使用 CiliumNetworkPolicy 可以进行更细粒度的控制。
</details>

## 简答题

11. 在 Cilium 中，运行在每个节点上、加载 eBPF 程序并实施网络策略的核心组件名称是什么？

<details>

<summary>查看答案</summary>

**答案：Cilium Agent**

**说明：**
Cilium Agent 是 Cilium 的核心组件，作为 DaemonSet 运行在每个 Kubernetes 节点上。Agent 的主要职责包括在内核中加载和管理 eBPF 程序、实施和执行网络策略、执行 Service 负载均衡、IP 地址管理（IPAM）、网络端点管理、指标和日志收集，以及与 API server 通信。Cilium Agent 处理本地节点上的所有网络操作。
</details>

12. Cilium 中哪个组件在整个集群范围内运行，并执行 CRD 同步和 IP 分配协调等任务？

<details>

<summary>查看答案</summary>

**答案：Cilium Operator**

**说明：**
Cilium Operator 是一个 Kubernetes Operator，以单个实例在整个集群中运行。Agent 处理每个节点上的本地操作，而 Operator 处理集群范围级别的操作。其关键功能包括 CiliumIdentity 和 CiliumEndpoint CRD 管理、集群级 IPAM 管理、节点间 CIDR 分配协调、垃圾回收（清理未使用的资源）以及 Cluster Mesh 连接管理。
</details>

13. 在 Cilium 中，用于诊断连通性问题的 CLI 命令是什么？

<details>

<summary>查看答案</summary>

**答案：cilium connectivity test**

**说明：**
`cilium connectivity test` 命令会全面测试 Cilium 集群中的网络连通性。该命令会自动测试多种场景，包括 Pod 到 Pod 通信、Service 连通性、外部连通性和网络策略执行。测试结果以成功/失败显示，并为失败的测试提供详细信息。此外，您可以使用 `cilium status` 检查 Cilium 状态，并使用 `cilium monitor` 监控实时流量。
</details>

14. 在 Cilium 中，表示 Pod 安全身份的数字标识符是什么？

<details>

<summary>查看答案</summary>

**答案：Identity（或 Security Identity、Cilium Identity）**

**说明：**
Cilium Identity 是根据 Pod 的标签集生成的数字标识符。具有相同标签的所有 Pod 共享相同的 Identity。这种方法允许使用 Identity 而非 IP 地址来应用网络策略，因此即使 Pod IP 发生变化，策略仍保持一致。基于 Identity 的策略具有很高的可扩展性，即使在大型集群中也能高效运行。
</details>

15. 定义容器运行时与网络插件之间标准接口的 CNCF 项目缩写是什么？

<details>

<summary>查看答案</summary>

**答案：CNI（Container Network Interface）**

**说明：**
CNI（Container Network Interface）是一个 CNCF 项目，定义了容器运行时与网络插件之间的标准接口。在 Kubernetes 中，kubelet 通过 CNI 接口与网络插件（Cilium、Calico、Flannel 等）通信。CNI 为添加/删除容器时的网络配置定义了标准 API，并且可通过插件架构集成各种网络解决方案。
</details>

## 实操题

16. 使用 Cilium CLI 在 Kubernetes 集群上安装 Cilium 1.18.0 的命令是什么？

<details>

<summary>查看答案</summary>

**答案：**
```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

**说明：**
上述命令首先将 Cilium CLI 二进制文件下载并安装到 `/usr/local/bin`。然后，`cilium install` 命令会在 Kubernetes 集群上安装指定版本的 Cilium。安装后，使用 `cilium status` 验证所有组件是否正常运行，并使用 `cilium connectivity test` 验证网络连通性。也可以使用 Helm 安装，从而提供更细粒度的配置选项。
</details>

17. 编写一个 CiliumNetworkPolicy，仅允许从 frontend Pod 到 backend Pod 8080 端口的 TCP 流量。

<details>

<summary>查看答案</summary>

**答案：**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

**说明：**
此 CiliumNetworkPolicy 仅允许带有 `app: frontend` 标签的 Pod 向带有 `app: backend` 标签的 Pod 发起 TCP 8080 端口入站流量。`endpointSelector` 选择策略适用的目标 Pod，`ingress` 部分定义允许的入站流量。`fromEndpoints` 指定源 Pod，`toPorts` 指定允许的端口和协议。应用此策略后，其他 Pod 发往 backend 的流量将被阻止。
</details>

18. 编写启用 kube-proxy 替代模式安装 Cilium 的命令，以及启用 DSR（Direct Server Return）模式的配置。

<details>

<summary>查看答案</summary>

**答案：**
```bash
# Install Cilium with kube-proxy replacement and DSR mode
cilium install --version 1.18.0 \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr

# Or installation using Helm
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=<API_SERVER_PORT>

# Verify installation
cilium status --verbose
```

**说明：**
`kubeProxyReplacement=true` 选项将 Cilium 配置为替代全部 kube-proxy 功能。在此模式下，必须移除或禁用现有 kube-proxy。`loadBalancer.mode=dsr` 启用 Direct Server Return 模式，使响应流量无需经过负载均衡器而直接发送给客户端。DSR 模式可消除负载均衡器瓶颈并节省带宽，在处理大型响应时尤其有效。
</details>

19. 编写检查 Cilium 状态、查询特定 Pod 端点信息以及查看已应用网络策略的命令。

<details>

<summary>查看答案</summary>

**答案：**
```bash
# Check overall Cilium status
cilium status

# Check detailed status (all components)
cilium status --verbose

# List all endpoints
cilium endpoint list

# Get detailed information for a specific endpoint (using endpoint ID)
cilium endpoint get <endpoint_id>

# Query endpoint by pod name
kubectl exec -n kube-system <cilium-agent-pod> -- cilium endpoint list | grep <pod-name>

# Query applied network policies
cilium policy get

# Query policies applied to a specific endpoint
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# Real-time traffic monitoring
cilium monitor
```

**说明：**
`cilium status` 显示所有组件的状态，包括 Cilium Agent、Operator 和 Hubble。`cilium endpoint list` 列出当前节点上的所有端点（Pod），您可以查看每个端点的 ID、状态、标签和 Identity。`cilium policy get` 查询集群中已应用的所有网络策略。`cilium monitor` 实时监控网络流量，以检查数据包流、策略应用和被丢弃的数据包。
</details>

20. 编写启用 Hubble 并使用 Hubble CLI 观察网络流的命令。

<details>

<summary>查看答案</summary>

**答案：**
```bash
# Install Cilium with Hubble enabled
cilium install --version 1.18.0 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Enable Hubble on existing Cilium
cilium hubble enable

# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble port forwarding
cilium hubble port-forward &

# Observe network flows
hubble observe

# Observe flows in a specific namespace
hubble observe --namespace default

# Observe flows for a specific pod
hubble observe --pod default/frontend

# Filter HTTP traffic only
hubble observe --protocol http

# Observe only dropped packets
hubble observe --verdict DROPPED

# Access Hubble UI (separate terminal)
cilium hubble ui
```

**说明：**
Hubble 是 Cilium 的可观测性层，使用 eBPF 实时监控网络流。`hubble.enabled=true` 启用 Hubble，`hubble.relay.enabled=true` 启用 Hubble Relay 以收集整个集群中的流，`hubble.ui.enabled=true` 启用基于 Web 的 UI。`hubble observe` 命令提供各种过滤选项，可按特定 namespace、Pod、协议、判定结果等过滤流量。
</details>

---

[返回学习材料](../../../networking/cilium/01-introduction.md) | [下一测验：eBPF 基础](./02-ebpf-quiz.md)
