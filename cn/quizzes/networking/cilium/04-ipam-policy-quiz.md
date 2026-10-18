# Cilium IPAM 与网络策略测验

> **Cilium 1.20.3 · 2026-10-16**

## IPAM

1. **未指定平台覆盖项时，通用默认的 IPAM 模式和分配模型是什么？**
   - A) kubernetes；每个 Pod 都向 Kubernetes API 请求一个 IP
   - B) cluster-pool；Operator 分配节点 CIDR，agent 分配本地 Pod IP
   - C) crd；每个 Pod 都会创建一个 CiliumPodIPPool
   - D) 在所有平台上都是 eni

   <details>
   <summary>显示答案</summary>

   **答案：B) cluster-pool；Operator 分配节点 CIDR，agent 分配本地 Pod IP**

   cluster-pool 使用 CiliumNode 节点前缀分配。它不是为每个 Pod 单独向中心请求地址，而且平台配置文件可以选择其他后端。

   </details>

2. **哪种模式会从 Kubernetes Node 状态获取节点前缀，而不是通过 Cilium Operator 的 cluster-pool 分配？**
   - A) cluster-pool
   - B) kubernetes（host scope）
   - C) 仅 multi-pool
   - D) 仅 eni

   <details>
   <summary>显示答案</summary>

   **答案：B) kubernetes（host scope）**

   Kubernetes 提供所需的节点 CIDR，agent 在其中分配地址。host scope 和 cluster-pool 都会在本地分配单个地址；两者都不会消除前缀协调。

   </details>

3. **在已准备好的 EC2 节点安装中，由 Cilium 自行管理 AWS ENI 和 VPC 地址时，使用哪种后端？**
   - A) kubernetes
   - B) cluster-pool
   - C) eni
   - D) 所有 AWS 节点都使用 delegated-plugin

   <details>
   <summary>显示答案</summary>

   **答案：C) eni**

   这是 ENI IPAM。AWS VPC CNI 链式配置仍由 AWS VPC CNI 负责 IP 分配；Hybrid Nodes 使用单独的路径，而 Fargate/Auto Mode 不支持这种替换配置。

   </details>

4. **哪些 Kubernetes 字段与 host-scope IPAM 相关？**
   - A) Node.spec.podCIDRs 和旧版/单栈的 Node.spec.podCIDR
   - B) Node.spec.subnet
   - C) Service.spec.podCIDR
   - D) CiliumPodIPPool.spec.selector

   <details>
   <summary>显示答案</summary>

   **答案：A) Node.spec.podCIDRs 和旧版/单栈的 Node.spec.podCIDR**

   这些是 Kubernetes Node 字段。cluster-pool 则使用 CiliumNode.spec.ipam.podCIDRs；权威状态取决于所选模式。

   </details>

5. **应如何调查实际生效的 IPAM 配置？**
   - A) 把任何包含 ipam 的 grep 行都视为完整配置
   - B) 只使用 Pod 就绪状态
   - C) 始终使用第一个 CiliumNode 地址和 CIDR
   - D) 将期望值/节点覆盖项以及实际的 agent/operator 状态，与所选分配器的资源进行比较

   <details>
   <summary>显示答案</summary>

   **答案：D) 将期望值/节点覆盖项以及实际的 agent/operator 状态，与所选分配器的资源进行比较**

   Helm/ConfigMap 值、节点覆盖项和分配状态可以互为补充。CiliumNode 并非所有 IPAM 模式的通用权威来源，而地址在数组中的位置也不能确定下一跳。

   </details>

## 策略基础

6. **本指南中 CiliumNetworkPolicy 的资源 API 版本是什么？**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>显示答案</summary>

   **答案：C) cilium.io/v2**

   CiliumNetworkPolicy 使用 cilium.io/v2。不要将它与 CiliumPodIPPool v2alpha1 API 或普通 Kubernetes NetworkPolicy 混淆。

   </details>

7. **在命名空间级别的 CiliumNetworkPolicy 中，endpointSelector 会选择什么？**
   - A) 该命名空间中作为策略主体的端点
   - B) 要创建的 Kubernetes Service
   - C) 任意命名空间中的主机节点
   - D) 要继承的其他策略

   <details>
   <summary>显示答案</summary>

   **答案：A) 该命名空间中作为策略主体的端点**

   它会选择策略适用的端点。资源作用域和选择器与 ingress/egress 中描述的流量对端是不同的概念。

   </details>

8. **ingress 规则描述什么？**
   - A) 进入所选端点的流量
   - B) 从所选端点发出的流量
   - C) 新建 IP 池
   - D) 路由通告

   <details>
   <summary>显示答案</summary>

   **答案：A) 进入所选端点的流量**

   Ingress 是相对于所选对象端点而言的。应用相应的对端、端口和受支持的协议限制。

   </details>

9. **egress 规则描述什么？**
   - A) 进入所选端点的流量
   - B) 从所选端点发出的流量
   - C) 任何位置的所有流量
   - D) 仅来自 Kubernetes 外部的流量

   <details>
   <summary>显示答案</summary>

   **答案：B) 从所选端点发出的流量**

   Egress 控制从所选端点发出的流量。应有意保留必要的 DNS 和应用依赖。

   </details>

10. **可选的 Cilium 规则 spec.labels 有什么用途？**
    - A) 用来选择主体 Pod，取代 endpointSelector
    - B) 用于规则标识和元数据
    - C) 继承任何具有相同标签的策略
    - D) 分配 Pod IP

    <details>
    <summary>显示答案</summary>

    **答案：B) 用于规则标识和元数据**

    规则标签可用于标识/查找，且不要求唯一。它们不会引用或继承其他策略；Kubernetes metadata.labels 用于标记资源本身。

    </details>

## 对端选择

11. **toCIDR/toCIDRSet 的用途和默认边界是什么？**
    - A) 选择 IP 前缀，主要用于外部对端；对受管理 Pod/节点的匹配有文档说明的默认限制
    - B) HTTP URL 过滤
    - C) 自动创建 Service
    - D) 从这些前缀分配地址

    <details>
    <summary>显示答案</summary>

    **答案：A) 选择 IP 前缀，主要用于外部对端；对受管理 Pod/节点的匹配有文档说明的默认限制**

    对普通受管理 Pod 的策略应使用端点选择器。该版本文档说明了针对 Pod/节点的选择性启用 Beta CIDR 匹配及其身份消耗影响；不得将默认行为描述为无条件的 IP 匹配器。

    </details>

12. **toFQDNs 授权什么？**
    - A) 自动允许所有 DNS 查询
    - B) 域名下的任意 HTTP URL
    - C) 到已为所选名称学习到的 IP 的流量，但仍受策略端口和限制条件约束
    - D) 仅允许静态配置的 IP

    <details>
    <summary>显示答案</summary>

    **答案：C) 到已为所选名称学习到的 IP 的流量，但仍受策略端口和限制条件约束**

    需要单独的 DNS 代理规则来观察名称到 IP 的映射。仅允许端口 53 并不能启用这种学习，而且允许 IP 并不等同于 HTTP 主机名或应用用户授权检查。

    </details>

13. **world 实体表示什么？**
    - A) 不加区分地包含所有本地和远程 Pod
    - B) 广义的集群外部身份类别
    - C) 仅控制平面节点
    - D) 仅公共 Internet 地址

    <details>
    <summary>显示答案</summary>

    **答案：B) 广义的集群外部身份类别**

    world 可以包含私有外部对端，并不等同于 all 实体，也不是指定远程集群的选择器。必要时应使用明确的对端和范围更窄的规则。

    </details>

14. **toServices 如何工作？**
    - A) 将 Kubernetes Service 选择器或无选择器的 EndpointSlice 地址解析为策略选择器
    - B) 自动创建 Service 并配置路由
    - C) 使所有 DNS 名称都可访问
    - D) 替代所有 kube-apiserver 实体规则

    <details>
    <summary>显示答案</summary>

    **答案：A) 将 Kubernetes Service 选择器或无选择器的 EndpointSlice 地址解析为策略选择器**

    无选择器的 Service 使用从 CIDR 派生的选择器，并受其限制影响。不要假设特殊的 default/kubernetes Service 与普通工作负载选择器行为相同。

    </details>

15. **在哪里使用 nodeSelector 来选择主机防火墙的作用对象？**
    - A) 在任何无前置条件的命名空间级 CiliumNetworkPolicy 中
    - B) 在已配置主机防火墙的 CiliumClusterwideNetworkPolicy 中
    - C) 在 CiliumPodIPPool 中分配每个 Pod IP
    - D) 在 Service 注解中

    <details>
    <summary>显示答案</summary>

    **答案：B) 在已配置主机防火墙的 CiliumClusterwideNetworkPolicy 中**

    Rule API 仅允许在 CiliumClusterwideNetworkPolicy 中使用 nodeSelector。它不同于 endpointSelector，也不同于 fromNodes/toNodes 对端选择。

    </details>

## L7 策略

16. **受支持的 Cilium L7 规则可以限制哪些 HTTP 请求属性？**
    - A) Path
    - B) Method
    - C) Headers
    - D) 以上全部

    <details>
    <summary>显示答案</summary>

    **答案：D) 以上全部**

    Envoy 会对可见的 HTTP 流量应用这些规则。另行配置的不受限制的 L4 允许规则可能绕过重叠的 L7 限制；策略允许也不保证应用能够成功运行。

    </details>

17. **关于 Cilium 1.20.3 中的 rules.kafka，哪项说法正确？**
    - A) 默认提供 topic 授权
    - B) 将 apiVersion 改为 v2alpha1 即可启用
    - C) 会自动加密 broker 连接
    - D) 内置的 Kafka L7 API 已移除；应使用适当的网络控制和 broker 授权

    <details>
    <summary>显示答案</summary>

    **答案：D) 内置的 Kafka L7 API 已移除；应使用适当的网络控制和 broker 授权**

    不要使用已废弃的 topic/API-key/client-ID 策略。L4 连通性应使用 broker 实际的监听端口，并使用其原生身份验证/授权机制。

    </details>

18. **哪种通配符说明符合该版本的实现？**
    - A) `*.example.com` 也能匹配 example.com 和 a.b.example.com
    - B) `*.example.com` 匹配一个子域标签；`**.example.com` 匹配一个或多个层级，且两者都不匹配根域名本身
    - C) 每个星号都始终可以匹配点号
    - D) matchName 和 matchPattern 会分配 DNS 地址

    <details>
    <summary>显示答案</summary>

    **答案：B) `*.example.com` 匹配一个子域标签；`**.example.com` 匹配一个或多个层级，且两者都不匹配根域名本身**

    实现会对规范化后的 DNS 名称进行锚定匹配。精确名称、单标签通配符和多层级前缀的含义各不相同；单独使用 matchName 可以匹配根域名本身。

    </details>

19. **如何表达受支持的 gRPC 服务/方法和元数据限制？**
    - A) 使用 rules.grpc 的 protobuf 字段过滤器
    - B) 仅使用 L3 CIDR 匹配
    - C) 通过受支持的 Envoy 路径匹配 HTTP/2 路径和标头
    - D) 将 CNI 替换为 kube-proxy

    <details>
    <summary>显示答案</summary>

    **答案：C) 通过受支持的 Envoy 路径匹配 HTTP/2 路径和标头**

    gRPC 服务/方法名称会出现在其 HTTP/2 路径中，元数据则位于标头中。这并不意味着可以检查任意 protobuf 负载；TLS 可见性也仍然很重要。

    </details>

20. **哪项关于组件的区分是正确的？**
    - A) kube-proxy 会执行所有 L7 规则
    - B) Envoy 处理受支持的 HTTP/gRPC 规则；Cilium 的 DNS 代理处理 DNS 策略
    - C) DNS 策略必须使用 NGINX Ingress
    - D) 所有 L7 解析器都只在内核 BPF 中运行

    <details>
    <summary>显示答案</summary>

    **答案：B) Envoy 处理受支持的 HTTP/gRPC 规则；Cilium 的 DNS 代理处理 DNS 策略**

    默认情况下，DNS 代理位于 agent 内；另有单独文档说明的 Alpha 独立模式。不要认为每条 DNS 规则都需要 Envoy，也不要假设加密后负载仍然可见。

    </details>

[查看指南](../../../networking/cilium/04-ipam-policy.md).
