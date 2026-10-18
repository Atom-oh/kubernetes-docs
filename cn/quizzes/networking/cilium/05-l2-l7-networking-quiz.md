# Cilium L2–L7 网络与负载均衡测验

> **Cilium 1.20.3 · CLI 0.20.1 · 2026-10-16**

## 选择题

1. **HTTP、DNS 和 gRPC 应用行为在概念上属于 OSI 哪一层？**
   - A) L1
   - B) L2
   - C) L3
   - D) L7

   <details>
   <summary>显示答案</summary>

   **答案：D) L7**

   从概念上说，应用协议映射到 L7。这并不意味着 Cilium 为每种应用协议都提供原生策略解析器；Kafka L7 规则已移除。

   </details>

2. **DSR 的直接返回特性是什么？**
   - A) 它会加密每个响应
   - B) 远程后端可以在不经由入口负载均衡节点返回的情况下响应
   - C) 它会验证客户端 IP
   - D) 它会恢复已被上游代理改写的客户端 IP

   <details>
   <summary>显示答案</summary>

   **答案：B) 远程后端可以在不经由入口负载均衡节点返回的情况下响应**

   网络必须支持非对称返回路径。DSR 可以减少响应路径上的跳数；性能和客户端 IP 保留情况取决于实际拓扑。

   </details>

3. **哪个组件负责处理 Cilium 支持的 HTTP/gRPC 策略？**
   - A) kube-proxy
   - B) Hubble Relay
   - C) Envoy
   - D) CoreDNS

   <details>
   <summary>显示答案</summary>

   **答案：C) Envoy**

   Envoy 是否部署取决于安装配置值。DNS 策略使用 Cilium 的 DNS 代理，而声明不受支持的 Kafka 规则并不会安装 Kafka 解析器。

   </details>

4. **哪一组选项描述了 Cilium 文档中所述的 BPF Service 后端选择算法？**
   - A) 轮询和最少连接
   - B) 随机和 Maglev
   - C) 源 IP 哈希和加权响应时间
   - D) 所有 Envoy 算法

   <details>
   <summary>显示答案</summary>

   **答案：B) 随机和 Maglev**

   BPF 选择和 Envoy L7 负载均衡属于不同的组件。Maglev 在指定的外部路径上受支持；普通的 socket-LB E–W 流量不适用该算法。

   </details>

5. **关于伪装实现，哪项说法正确？**
   - A) 对所有工作负载而言，BPF 总是更快
   - B) 所有 Linux 内核都支持当前版本的 Cilium
   - C) 两种实现都在内核中运行，并且都有配置和平台要求
   - D) 选择 BPF 后就不再需要路由

   <details>
   <summary>显示答案</summary>

   **答案：C) 两种实现都在内核中运行，并且都有配置和平台要求**

   仅凭产品名称或在内核中执行，并不能得出性能结论。此版本的 BPF 伪装有功能和设备依赖项，IPv6 支持仍处于 beta 阶段。

   </details>

6. **哪个当前值可以启用 kube-proxy 替换？**
   - A) kubeProxyReplacement: partial
   - B) kubeProxyReplacement: true
   - C) kubeProxyReplacement: strict
   - D) kubeProxyReplacement: hybrid

   <details>
   <summary>显示答案</summary>

   **答案：B) kubeProxyReplacement: true**

   使用布尔值/当前的 true 值，并满足完整替换所需的前提条件，包括 API 可达性。旧的 strict/partial 术语不属于当前约定。

   </details>

7. **以下哪项不是内置的 Cilium HTTP 策略谓词？**
   - A) 方法
   - B) 路径
   - C) 受支持的标头条件
   - D) 任意请求正文内容

   <details>
   <summary>显示答案</summary>

   **答案：D) 任意请求正文内容**

   方法/路径表达式与受支持的标头条件有所不同。带有值的 headers 字符串是字面匹配，并非通用的标头值正则表达式。检查负载需要单独设计应用或代理功能。

   </details>

8. **本指南中 Cilium/Istio 集成的预期模式是什么？**
   - A) 自动绕过 Istio sidecar
   - B) 保留 Istio 拦截，并结合 Cilium 网络控制与 Istio 的 L7/mTLS 职责
   - C) 自动禁用 mTLS
   - D) 让每条 Cilium HTTP 规则都检查加密的 Istio 流量

   <details>
   <summary>显示答案</summary>

   **答案：B) 保留 Istio 拦截，并结合 Cilium 网络控制与 Istio 的 L7/mTLS 职责**

   配置 CNI/socket-LB 互操作性，并测试拓扑。此示例保留 Istio mTLS，并使用 Cilium L3/L4 策略，而不是对加密流量执行明文 HTTP 检查。

   </details>

9. **套接字级负载均衡可以做什么？**
   - A) 在受支持的套接字钩子处、构造数据包之前选择后端
   - B) 自动验证 HTTP 标头
   - C) 解密所有流量
   - D) 创建外部负载均衡器

   <details>
   <summary>显示答案</summary>

   **答案：A) 在受支持的套接字钩子处、构造数据包之前选择后端**

   TCP connect 和受支持的 UDP 套接字路径可以提前将 Service 转换为后端。这并不保证普遍降低延迟；与 sidecar 拦截配合时可能还需要特殊处理。

   </details>

10. **以下哪项是恰当的分片处理原则？**
    - A) 跟踪可保证防御所有分片攻击
    - B) 规划有效路径 MTU，并验证所需的错误信令
    - C) 必须始终丢弃所有分片
    - D) Cilium 的 MTU 始终表示最终的 Pod 负载大小

    <details>
    <summary>显示答案</summary>

    **答案：B) 规划有效路径 MTU，并验证所需的错误信令**

    Cilium 的 MTU 会覆盖底层网络的值。分片跟踪保留 L4 上下文，但不负责重组负载，也不保证防止攻击；如果所需的信令或路径行为异常，PMTUD 可能会失效。

    </details>

## 简答题

11. **说出当前内置的 L7 策略组，并说明 gRPC 属于哪一类。**

<details>
<summary>显示答案</summary>

HTTP 和 DNS。受支持的 gRPC 约束通过 Envoy 使用 HTTP/2 路径/标头匹配。DNS 使用 Cilium 的 DNS 代理；Kafka L7 规则已移除。必须配置 TLS 可见性，不能想当然地认为它已具备。

</details>

12. **区分 Service 后端就绪状态与通用主动健康检查引擎。**

<details>
<summary>显示答案</summary>

Kubernetes endpoint/readiness 状态会影响后端是否符合条件，但具体取决于 Service 和终止语义，并存在传播延迟。这并不意味着每个 BPF Service 都会独立执行 TCP/HTTP 健康探测。Cilium 连通性健康检查、应用探测和代理健康检查是不同的机制。

</details>

13. **对于外部路径，哪个操作会改变 Pod 的出站源地址？**

<details>
<summary>显示答案</summary>

源 NAT / 伪装。它不同于将目标地址转换为 Service 后端。所选接口、排除的 CIDR、节点例外情况以及后续的云 NAT 都可能影响实际观察到的源地址；仅凭外部 HTTP 请求成功，并不能证明具体使用了哪种实现。

</details>

14. **说明 Maglev 和 sessionAffinity: ClientIP 为什么不能互换。**

<details>
<summary>显示答案</summary>

Maglev 会在其支持的路径上，使用兼容的表/状态/种子提供一致的后端选择。ClientIP 亲和性则维护单独的客户端 Service 亲和性和超时行为，并使用 IP 或适用的 socket-LB 命名空间 cookie。两者都无法将会话保留在已失败或已移除的后端上。

</details>

15. **什么是 L4？TCP 和 UDP 之间哪项可靠性差异值得注意？**

<details>
<summary>显示答案</summary>

L4 是传输层。TCP 提供可靠、有序的字节流；UDP 提供数据报，但不保证送达或顺序。UDP 并非对每种应用都自动更快，而端口/协议策略也不能提供应用身份验证。

</details>

## 动手题

16. **为 `l7-exercise` 中监听 TCP8080 的 API 编写策略：仅允许 frontend 执行 GET /api/v1/users 和 POST /api/v1/data，并且必须包含 X-Auth-Token。**

<details>
<summary>显示答案</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-http
  namespace: l7-exercise
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: l7-exercise
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/v1/users$
        - method: ^POST$
          path: ^/api/v1/data$
          headerMatches:
          - name: x-auth-token
```

工作负载标签/命名空间和监听端口是前提条件。只指定名称的 headerMatches 条目会检查标头是否存在；它不会验证令牌。旧的 `X-Auth-Token: .*` 字符串表示按字面值匹配，并非匹配任意值。请检查其他适用策略和实际生效的代理状态。

</details>

17. **在新建且已准备好的无 kube-proxy IPv4 测试集群上，安装文档所述的 DSR/Maglev 配置。**

<details>
<summary>显示答案</summary>

**lb-values.yaml**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```

```bash
: "${API_SERVER_HOST:?Set the real reachable API server host}"
: "${API_SERVER_PORT:?Set its actual port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.3 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

此配置使用 Geneve 覆盖网络和 Geneve DSR 分发。必须预先准备好 API 端点、网络返回路径和持久化的通用 Maglev 种子。65521 是允许的表大小，并非通用要求。不要在任意安装之后删除 kube-proxy，也不要为了走捷径测试而切换运行中集群的转发模式。

</details>

18. **需求是 order-service 需要 orders-produce 权限，payment-processor 需要 payments-consume 权限。当前 Cilium 策略可以实施什么控制？Broker 必须实施什么控制？**

<details>
<summary>显示答案</summary>

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: broker-connectivity
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: order-service
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: messaging
        k8s:app: payment-processor
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

这只允许这两个源工作负载访问假定的 Broker 监听器 TCP9092；请将端口替换为实际配置的监听端口。它无法实施主题操作权限。在 Kafka 中验证不同的 Broker 主体身份，并配置所需的生产/消费权限和消费者组授权。`rules.kafka` 已移除，因此将旧 YAML 作为完整授权配置是不正确的。

</details>

19. **给出一段 BPF 伪装配置，用于排除目标位于实际可路由的 10.0.0.0/8 范围内的流量。**

<details>
<summary>显示答案</summary>

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```

将其合并到适当的预备配置中。BPF NodePort/设备前提条件和返回路由仍然适用。ipv4NativeRoutingCIDR 控制相关的伪装排除；它不会创建路由，也不会切换 routingMode。请检查所选节点上的 `cilium-dbg status --verbose` 和 `cilium-dbg bpf nat list`，并进行受控的外部观察。

</details>

20. **给出一个不会造成中断的排查步骤序列，用于调查意外的 L7 策略行为。**

<details>
<summary>显示答案</summary>

```bash
cilium status --verbose
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system get pods -l k8s-app=cilium-envoy -o wide
kubectl -n cilium-l2l7-demo get pods -o wide
export APP_POD=REPLACE-WITH-APP1-POD
export CILIUM_POD=REPLACE-WITH-AGENT-ON-APP-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "pod-name:cilium-l2l7-demo:$APP_POD"
kubectl -n cilium-l2l7-demo get cnp -o yaml
kubectl get ccnp -o yaml
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --tail=100
```

对于显式启用的 Envoy DaemonSet：

```bash
export ENVOY_POD=REPLACE-WITH-ENVOY-POD-ON-APP-NODE
kubectl -n kube-system logs "$ENVOY_POD" --all-containers=true --tail=100
```

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

选择工作负载所在节点上的 agent/Envoy Pod，而不是随意选择一个 DaemonSet Pod。对于显式部署的 Envoy DaemonSet，请检查该 Pod 有限范围内的日志；对于内嵌 Envoy，请检查 agent 已配置的日志。将 Relay 转发进程保留在单独的终端中。比较期望规则和实际生效规则、明文/TLS 可见性、应用响应和流量。HTTP403 不等于数据包被丢弃，缺少观察结果也可能是过滤或丢失所致。策略 trace 已移除，强制重新生成 endpoint 也不是必要的首要步骤。

</details>

---

[返回学习资料](../../../networking/cilium/05-l2-l7-networking.md) | [下一测验：安全与可见性](./06-security-visibility-quiz.md)
