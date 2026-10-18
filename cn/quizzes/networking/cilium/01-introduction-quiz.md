# Cilium 介绍与基本概念测验

> **基准版本**：Cilium 1.20.3 / CLI 0.20.1。**最后更新**：October 16, 2026

## 选择题

1. 哪种技术为 Cilium 提供可编程的内核数据路径？
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>
<summary>显示答案</summary>

**答案：B) eBPF**

**解释：**
Cilium 会在受支持的内核钩子处加载经过验证的 eBPF 程序。这使网络和可观测性功能得以实现，但并不保证性能一定优于所有替代方案；请针对所选工作负载和配置进行测量。

</details>

2. 在具备所需集成的情况下，Cilium 可以支持哪些策略层？
   - A) 仅 L3
   - B) 仅 L3–L4
   - C) L3/L4 和受支持的 L7 协议
   - D) 仅 L2–L3

<details>
<summary>显示答案</summary>

**答案：C) L3/L4 和受支持的 L7 协议**

**解释：**
HTTP 和 DNS 策略使用受支持的代理路径；加密的 HTTP 流量需要适当的终止/集成方式。Kafka 感知型 L7 规则已在 1.20 中移除。L4 策略仍可控制 Kafka 连接。

</details>

3. Cilium 的哪个组件可提供网络流可见性？
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>
<summary>显示答案</summary>

**答案：B) Hubble**

**解释：**
Hubble 可观测网络/代理流量，并显示服务间的关系。HTTP 可见性取决于代理路径。它不会自动生成完整的应用程序跟踪；Prometheus 指标和分布式跟踪用途不同。

</details>

4. 在受支持的配置中，Cilium 可以替代哪个 Kubernetes Service 组件？
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>
<summary>显示答案</summary>

**答案：B) kube-proxy**

**解释：**
kubeProxyReplacement 用于请求由 Cilium 处理 Service。API/引导访问和迁移前提仍然重要，而 DSR/Maglev/XDP 是单独的选项，并不自动保证性能更好。

</details>

5. 哪一组选项列出了 Cilium 的透明网络加密模式？
   - A) IPsec 和 WireGuard
   - B) TLS 和 SSH
   - C) GRE 和 HTTP
   - D) DNS 和 VXLAN

<details>
<summary>显示答案</summary>

**答案：A) IPsec 和 WireGuard**

**解释：**
IPsec 和 WireGuard 是本题中已经成熟的模式组合。同一个 `encryption.type` 键也接受 beta 版 `ztunnel`，用于工作负载 mTLS，但它有自己的命名空间注册、CA/引导、流量和策略前提。这些是同一个键下的不同模式；声称 Cilium 从不使用 TLS 是不正确的。

</details>

6. Cilium 的多集群连接功能叫什么？
   - A) Cluster Federation
   - B) ClusterMesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>
<summary>显示答案</summary>

**答案：B) ClusterMesh**

**解释：**
ClusterMesh 使用已配置的身份、信任关系和网络可达性连接兼容的集群。它不会创建整个底层网络，也不会自动让所有服务都可从全局访问。

</details>

7. Cilium 可以使用哪种技术来加速可选的早期数据包处理/负载均衡？
   - A) DPDK
   - B) XDP
   - C) RDMA
   - D) SR-IOV

<details>
<summary>显示答案</summary>

**答案：B) XDP**

**解释：**
XDP 可以在受支持的钩子/驱动程序处较早处理选定的流量。并非所有 Cilium 数据包路径都会使用它；启用 XDP 既不能保证特定的数据包每秒处理量，也不能实现全面的 DDoS 防护。

</details>

8. Cilium 1.20 标准上游 Linux 内核的基线版本是多少（不包括文档中列明的供应商回移等效版本）？
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>
<summary>显示答案</summary>

**答案：D) 5.10**

**解释：**
当前要求规定 Linux 5.10+，并列出了诸如 RHEL 8.10 回移版本 4.18 这样的等效版本。个别功能可能需要更新的内核。请检查节点/VM 的内核，而不只是工作站操作系统。

</details>

9. 哪个选项无需使用 Cilium 的 eBPF 数据平面即可提供 VXLAN/host-gw 连接？
   - A) Cilium 原生路由
   - B) Calico BPF 模式
   - C) Flannel VXLAN/host-gw
   - D) Cilium netkit 模式

<details>
<summary>显示答案</summary>

**答案：C) Flannel VXLAN/host-gw**

**解释：**
Flannel 的连接后端采用不同的实现方式。其可选策略控制器或其他策略集成需要单独评估；应避免对资源/性能进行一概而论的排名。

</details>

10. CiliumNetworkPolicy 的 API 版本是什么？
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

<details>
<summary>显示答案</summary>

**答案：C) cilium.io/v2**

**解释：**
CiliumNetworkPolicy 是独立于标准 Kubernetes NetworkPolicy 的 CRD/API。功能是否可用仍取决于 Cilium 版本以及数据平面/代理配置。

</details>

## 简答题

11. 哪个组件在每个节点上运行，并对端点和 eBPF 策略进行编程？

<details>
<summary>显示答案</summary>

**答案：Cilium Agent**

**解释：**
Agent 负责节点本地的工作。容器运行时/CNI 插件、operator、代理和主机操作系统各自承担其他职责；并非所有网络操作都由 Agent 负责。

</details>

12. 哪个组件负责协调集群级别的分配/控制器工作？

<details>
<summary>显示答案</summary>

**答案：Cilium Operator**

**解释：**
Operator 可以运行多个副本；经审查的 chart 默认使用两个副本，并为适用的工作启用领导者选举。其职责取决于 IPAM/身份模式。它并非天然只能有一个实例，也不是所有 ClusterMesh 连接的唯一管理者。

</details>

13. 哪条 CLI 命令会运行 Cilium 的连通性测试工作负载？

<details>
<summary>显示答案</summary>

**答案：cilium connectivity test**

**解释：**
该命令会创建工作负载/策略，需要在获准的测试环境中运行并具备相应权限。只读检查可从 cilium status、端点诊断和 Hubble 开始。管理命令 cilium monitor 并非当前的 Agent 诊断接口。

</details>

14. 与端点安全相关标签关联的数字标识符是什么？

<details>
<summary>显示答案</summary>

**答案：安全身份（Cilium identity）**

**解释：**
只有相关/选定的标签集才会在其分配范围内决定身份。由命名空间派生的标签可能不同；仅有相同的应用标签并不能证明身份相同。该数字 ID 是分配得到的，并非永久且具有全局意义的哈希值。

</details>

15. 哪项规范定义了容器网络插件接口？

<details>
<summary>显示答案</summary>

**答案：CNI（Container Network Interface）**

**解释：**
kubelet 通过 CRI 与运行时通信，运行时再调用 CNI。CNI 负责交换网络配置/结果并处理网络的设置/移除；kubelet 过去用于 CNI 配置的标志已在 Kubernetes 1.24 中移除。

</details>

## 实践题

16. 使用已安装的 CLI、准备好的实验值和明确指定的 context，展示一个全新的 Cilium 1.20.3 安装。

<details>
<summary>显示答案</summary>

**答案：**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium version --client
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

**解释：**
请满足指南中预先验证的环境/CNI 所有权、CIDR 和 values 前提条件。如果已有发行版本，请跳过安装，并使用其所有者的升级流程。状态检查不能替代正向/负向流量测试。

</details>

17. 编写实验策略，允许 cilium-intro-demo 中 frontend Pod 向 backend Pod 发起 TCP 8080 入站流量。

<details>
<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

**解释：**
命名空间和工作负载必须已存在。明确指定对端命名空间可避免向其他具有相同标签的命名空间授予访问权限。其他 allow/deny 策略和主机流量会影响结果；此规则不是 HTTP 过滤规则，也不限制出站流量。

</details>

18. 展示一个部分 values 示例，请求使用 Geneve 分发的 kube-proxy 替换和原生路由 DSR。还需要准备什么？

<details>
<summary>显示答案</summary>

**答案：**

```yaml
kubeProxyReplacement: true
k8sServiceHost: api.lab.example.internal
k8sServicePort: 443
routingMode: native
tunnelProtocol: geneve
ipv4NativeRoutingCIDR: 10.244.0.0/16
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

**解释：**
这是单独的原生配置方案，并非要求在 VXLAN 实验中启用 DSR。请将 API 主机/端口和原生路由 CIDR 替换为实际准备好的值。确保 API/引导 DNS 访问、底层网络中的 Pod 路由、Geneve/MTU 以及返回/源地址路径均已就绪，然后遵循受支持的 kube-proxy 迁移流程。静态值不能保证与云负载均衡器兼容，也不能消除所有瓶颈。

</details>

19. 展示集群状态、所选 backend 端点的本地状态，以及预期的策略资源。

<details>
<summary>显示答案</summary>

**答案：**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
CILIUM_LAB_NS=cilium-intro-demo
BACKEND_POD=replace-with-actual-backend-pod
cilium status --context "$CILIUM_LAB_CONTEXT" --verbose
kubectl --context "$CILIUM_LAB_CONTEXT" get pod "$BACKEND_POD" -n "$CILIUM_LAB_NS" -o wide
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent on the backend Pod's node.
CILIUM_AGENT_POD=replace-with-agent-pod-on-that-node
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint list
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint get "pod-name:$CILIUM_LAB_NS:$BACKEND_POD"
kubectl --context "$CILIUM_LAB_CONTEXT" get networkpolicy -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get ccnp -o yaml
```

**解释：**
端点标识符和已实现的状态属于所选 Agent/节点；请使用 cilium-dbg 支持的 Pod 标识符。kubectl 读取的是预期的策略资源，不能证明策略已生效。cilium-dbg policy get 已弃用，管理端的 cilium endpoint/policy/monitor 命令也不等同于上述命令。

</details>

20. 为现有实验发行版本启用 Hubble，并使用已安装的客户端工具观察流量。

<details>
<summary>显示答案</summary>

**答案：**

```bash
# Terminal 1; the lab Cilium release and client tools must already exist.
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium hubble enable --context "$CILIUM_LAB_CONTEXT" --ui
cilium hubble port-forward --context "$CILIUM_LAB_CONTEXT" --port-forward 4245
```

```bash
# Terminal 2, with the port-forward still running.
BACKEND_POD=replace-with-actual-backend-pod
hubble observe --server 127.0.0.1:4245 --namespace cilium-intro-demo
hubble observe --server 127.0.0.1:4245 --pod "cilium-intro-demo/$BACKEND_POD"
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
```

**解释：**
如果发行版本由 GitOps 管理，请修改其所有者的 Helm values，而不要通过命令式 CLI 更新；如果已启用，则跳过 enable。保持前台运行的 port-forward 持续活动；如果 Relay 使用客户端 TLS，也要配置客户端 TLS。HTTP 事件需要受支持的 L7 代理路径，而 DROPPED 并不涵盖所有应用程序故障。要访问 UI，请在另一个终端中使用相同的明确 context 运行 cilium hubble ui。

</details>

[返回学习资料](../../../networking/cilium/01-introduction.md) | [下一份测验：eBPF 基础](02-ebpf-quiz.md)
