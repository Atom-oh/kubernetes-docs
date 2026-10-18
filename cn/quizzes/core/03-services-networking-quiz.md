# Services 和网络测验

本测验将测试你对 Kubernetes 网络概念的理解，包括 Service 类型、Ingress、网络策略和服务发现。

## 选择题

1. Kubernetes 中默认的 Service 类型是什么？
   - A) NodePort
   - B) LoadBalancer
   - C) ClusterIP
   - D) ExternalName
   
<details>

<summary>显示答案</summary>

**答案：C) ClusterIP**

**说明：**
ClusterIP 是 Kubernetes 中默认的 Service 类型，它会提供一个只能在集群内部访问的 IP 地址。此 Service 允许集群内的其他应用访问它，但无法从集群外部访问。
</details>

2. 哪种 API 对象可以将集群外部的 HTTP 和 HTTPS 路由暴露给集群内的 Service？
   - A) Service
   - B) Ingress
   - C) Endpoint
   - D) NetworkPolicy
   
<details>

<summary>显示答案</summary>

**答案：B) Ingress**

**说明：**
Ingress 是一种 API 对象，可以将集群外部的 HTTP 和 HTTPS 路由暴露给集群内的 Service。Ingress 提供负载均衡、SSL 终止和基于名称的虚拟主机功能。
</details>

3. 以下哪两项是 Kubernetes 内置的服务发现机制？（选择两项。）
   - A) 环境变量
   - B) DNS
   - C) Service Mesh
   - D) ConfigMap
   
<details>

<summary>显示答案</summary>

**答案：A) 环境变量和 B) DNS**

**说明：**
Kubernetes 提供两种主要的服务发现方法：环境变量和 DNS。ConfigMap 用于存储配置数据，不属于服务发现机制。
</details>

4. Kubernetes 中哪种 Service 类型可让服务通过所有节点上的特定端口进行访问？
   - A) ClusterIP
   - B) NodePort
   - C) LoadBalancer
   - D) ExternalName
   
<details>

<summary>显示答案</summary>

**答案：B) NodePort**

**说明：**
NodePort Service 可让服务通过所有节点上的特定端口进行访问。此 Service 类型允许通过每个节点的 IP 地址和 NodePort 值访问服务（默认分配范围为 30000-32767）。
</details>

5. 哪种类型的 Service 没有集群 IP，并会为每个 Pod 创建 DNS 记录？
   - A) NodePort Service
   - B) LoadBalancer Service
   - C) Headless Service
   - D) ExternalName Service
   
<details>

<summary>显示答案</summary>

**答案：C) Headless Service**

**说明：**
Headless Service 是一种配置了 `clusterIP: None` 的 Service，它不会分配集群 IP，并会为每个 Pod 创建 DNS 记录。当客户端需要直接访问该 Service 后端的特定 Pod 时，这种方式很有用。
</details>

6. 哪种资源可以控制 Kubernetes 中 Pod 之间的通信？
   - A) Service
   - B) Ingress
   - C) NetworkPolicy
   - D) EndpointSlice
   
<details>

<summary>显示答案</summary>

**答案：C) NetworkPolicy**

**说明：**
NetworkPolicy 可以控制 Pod 之间的通信。通过使用网络策略，你可以限制 Pod 之间的入站和出站流量。
</details>

7. Kubernetes 集群使用什么作为 DNS 服务器？
   - A) kube-dns
   - B) CoreDNS
   - C) NodeDNS
   - D) ClusterDNS
   
<details>

<summary>显示答案</summary>

**答案：B) CoreDNS**

**说明：**
CoreDNS 是一种灵活且可扩展的 DNS 服务器，被用作 Kubernetes 集群的 DNS 服务器。CoreDNS 在 Kubernetes 1.11 中达到 GA，并从 1.13 起成为默认 DNS 服务器。
</details>

8. Cilium 使用哪种 Linux 内核技术？
   - A) iptables
   - B) netfilter
   - C) eBPF
   - D) nftables
   
<details>

<summary>显示答案</summary>

**答案：C) eBPF**

**说明：**
Cilium 使用 Linux 内核的 eBPF（扩展伯克利数据包过滤器）技术，为容器化应用提供网络连接、安全性和可观测性。
</details>

9. 以下哪项不是 Service Mesh 的主要功能？
   - A) 服务发现
   - B) 负载均衡
   - C) 提供持久化存储
   - D) 加密通信
   
<details>

<summary>显示答案</summary>

**答案：C) 提供持久化存储**

**说明：**
Service Mesh 是管理微服务之间通信的基础设施层，可提供服务发现、负载均衡、加密、身份验证、授权和可观测性等功能。提供持久化存储并不是 Service Mesh 的主要功能。
</details>

10. Kubernetes 中哪种 Service 类型可为外部服务提供别名？
    - A) ClusterIP
    - B) NodePort
    - C) LoadBalancer
    - D) ExternalName
    
<details>

<summary>显示答案</summary>

**答案：D) ExternalName**

**说明：**
ExternalName Service 可为外部服务提供别名。此 Service 类型会将一个 DNS 名称映射到外部服务的 DNS 名称。
</details>

## 简答题

1. Kubernetes 中哪种资源用于存储 Service 指向的 Pod 的 IP 地址和端口？

<details>

<summary>显示答案</summary>

**答案：EndpointSlice**

**说明：**
EndpointSlice 用于存储 Service 后端的地址和端口。对于基于选择器的 Service，控制器会管理这些资源。旧版 Endpoints 用途类似，但自 v1.33 起已弃用。
</details>

2. 在 AWS EKS 中，用于配置 Application Load Balancer 的 Ingress 控制器叫什么？

<details>

<summary>显示答案</summary>

**答案：AWS Load Balancer Controller**

**说明：**
AWS Load Balancer Controller 是用于在 AWS EKS 中配置 Application Load Balancer 的 Ingress 控制器。该控制器会将 Kubernetes Ingress 资源转换为 AWS ALB。
</details>

3. Kubernetes 中哪种 Pod DNS 策略会继承 Pod 所运行节点的 DNS 设置？

<details>

<summary>显示答案</summary>

**答案：Default**

**说明：**
`Default` DNS 策略会继承 Pod 所运行节点的 DNS 设置。这意味着 Pod 会原样使用节点的 `/etc/resolv.conf` 文件。
</details>

4. Cilium 中使用 eBPF 监控网络流并排查问题的可观测性层叫什么？

<details>

<summary>显示答案</summary>

**答案：Hubble**

**说明：**
Hubble 是 Cilium 的可观测性层，它使用 eBPF 监控网络流并排查问题。Hubble 提供网络流监控、服务依赖关系映射、安全观测、性能分析和故障排查等功能。
</details>

5. Kubernetes 中哪种资源是 Endpoints 的可扩展替代方案，并能在大型集群中提供更好的性能？

<details>

<summary>显示答案</summary>

**答案：EndpointSlice**

**说明：**
EndpointSlice 是 Endpoints 的可扩展替代方案，能在大型集群中提供更好的性能。EndpointSlice 会将大型 Service 的端点拆分到多个切片中进行管理，从而提升性能。
</details>

## 高级问题

1. 说明如何使用 Service Mesh（例如 Istio）管理 Kubernetes 中微服务之间的通信，以及它有哪些优势。

<details>

<summary>显示答案</summary>

**答案：**

Service Mesh 是管理微服务之间通信的基础设施层，具体实现方式如下：

1. **Sidecar 模式**：将代理容器（例如 Envoy）注入每个 Pod，以拦截和控制所有网络流量。

2. **控制平面**：集中式管理组件（例如 Istio 的 istiod）负责配置和管理所有 Sidecar 代理。

3. **流量管理**：
```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
    - reviews
  http:
    - match:
      - headers:
          end-user:
            exact: jason
      route:
        - destination:
            host: reviews
            subset: v2
    - route:
      - destination:
          host: reviews
          subset: v1
```

4. **安全策略**：
```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: foo
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
    - from:
      - source:
          principals: ["cluster.local/ns/default/sa/sleep"]
      to:
        - operation:
            methods: ["GET"]
            paths: ["/info*"]
```

**优势**：

1. **流量管理**：支持高级路由、负载均衡、流量拆分、金丝雀部署等功能。

2. **安全性**：提供服务间的双向 TLS (mTLS) 加密、身份验证和授权。

3. **可观测性**：通过分布式追踪、指标收集和日志记录来监控服务间的通信。

4. **弹性**：通过断路器、重试、超时和故障注入提升系统弹性。

5. **策略实施**：可以应用速率限制、配额和访问控制等策略。

6. **平台独立性**：无需更改应用代码即可添加这些功能。

Service Mesh 抽象了复杂微服务架构中服务间通信的复杂性，使开发人员能够专注于业务逻辑。
</details>

2. 说明与传统网络方法（例如 iptables）相比，Cilium 的 eBPF 技术有哪些优势，并提出在 AWS EKS 中优化 Cilium 的方法。

<details>

<summary>显示答案</summary>

**答案：**

**Cilium eBPF 技术的优势**：

1. **性能**：eBPF 直接在内核中运行，以优化数据包处理路径，性能远高于 iptables。尤其是当规则较多时，iptables 会执行线性搜索，而 eBPF 可以使用哈希表等高效数据结构。

2. **可扩展性**：即使在大型集群中，eBPF 也能保持稳定的性能。随着规则数量增加，iptables 的性能会迅速下降。

3. **可编程性**：eBPF 可以使用类似 C 语言的语言进行编程，从而实现复杂的网络逻辑。iptables 仅支持有限的一组规则。

4. **可观测性**：eBPF 可以收集有关网络流的详细指标，便于故障排查和性能优化。

5. **L7 策略**：Cilium 将 eBPF 与用户空间中的 Envoy 结合，用于 HTTP/L7 检查；这项工作并非完全由内核中的 eBPF 完成。

**在 AWS EKS 中优化 Cilium 的方法**：

1. **审慎选择 IPAM 和路由模式**：AWS VPC CNI chaining 会保留 `aws-node`；Cilium ENI 模式需要 EC2 权限，并且需要谨慎管理 ENI 所有权的转换。使用本章审核过的 Helm values 和官方安装流程。

2. **合理配置节点网络**：检查实例实际的 ENI/IP 限制、子网容量和 Pod 密度；仅凭实例系列名称不足以判断。

3. **先测量，再调优**：在适用情况下，当前 Helm values 使用 `routingMode: native` 和布尔值 `kubeProxyReplacement: true`，而不是已移除的 `tunnel=disabled` 或 `kubeProxyReplacement=strict`。启用替换还需要连接 API server 并制定迁移计划。DSR 和 XDP 需要兼容的 AWS 网络、NIC/内核支持以及经测量验证；启用所有设置并不是通用的优化方案。

4. **启用 Hubble**：
```bash
cilium hubble enable --ui
```
启用 Hubble，以提供网络流监控和故障排查能力。

5. **跨集群连接**：
配置 Cilium Cluster Mesh，以便在多个 EKS 集群之间实现无缝网络连接。

6. **集成监控**：
设置 Prometheus 和 Grafana，以收集并可视化 Cilium 指标。

这些优化可以最大限度地提升 Cilium 在 AWS EKS 中的性能、安全性和可观测性。
</details>

## 总结

通过本测验，你检验了自己对 Kubernetes Service 和网络的理解。涉及的概念包括 Service 类型、Ingress、网络策略、服务发现、CoreDNS 和 Cilium。理解并运用这些概念，可以帮助你构建安全且可扩展的 Kubernetes 应用。
