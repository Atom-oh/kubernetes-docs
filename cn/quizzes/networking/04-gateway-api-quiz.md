# Gateway API 测验

本测验测试您对 Kubernetes Gateway API 资源模型、实现方式以及从 Ingress 迁移的理解。

## 测验题目

### 1. 以下哪项不是 Gateway API 相较于现有 Ingress API 的改进方式？

A. 基于角色的资源分离（基础设施提供商、集群运维人员、应用开发人员）
B. 原生支持 TCP、UDP、gRPC 等多种协议
C. 通过标准化字段而非注解实现功能
D. 将所有网络功能集成到单一资源中

<details>
<summary>显示答案</summary>

**答案：D. 将所有网络功能集成到单一资源中**

**说明：**
Gateway API 的改进：
- **角色分离**：职责划分为 GatewayClass（基础设施）、Gateway（运维人员）和 Routes（开发人员）
- **多种协议**：HTTPRoute、GRPCRoute、TCPRoute、TLSRoute、UDPRoute
- **标准化**：通过显式字段定义功能，无需注解
- **可扩展性**：可基于 CRD 轻松添加新功能

Gateway API 被拆分为多个资源，因此“集成到单一资源中”是不正确的。

</details>

### 2. 在 Gateway API 的角色分离中，谁负责管理 GatewayClass？

A. 应用开发人员
B. 集群运维人员
C. 基础设施提供商
D. 安全管理员

<details>
<summary>显示答案</summary>

**答案：C. 基础设施提供商**

**说明：**
Gateway API 角色分离：

| 角色 | 管理的资源 | 职责 |
|------|------------------|----------------|
| **基础设施提供商** | GatewayClass | 定义基础设施基本配置，指定 controller |
| **集群运维人员** | Gateway、ReferenceGrant | Load balancer 配置、namespace 权限管理 |
| **应用开发人员** | HTTPRoute、GRPCRoute 等 | 定义应用路由规则 |

GatewayClass 由云服务提供商或网络团队定义。

</details>

### 3. Gateway 中 TLS termination 和 passthrough 的正确区别是什么？

A. Terminate 将 TLS 传递给 backend，Passthrough 在 Gateway 处终止 TLS
B. Terminate 在 Gateway 处终止 TLS，Passthrough 将 TLS 传递给 backend
C. 两种模式的行为完全相同
D. Terminate 仅支持 HTTP，Passthrough 仅支持 HTTPS

<details>
<summary>显示答案</summary>

**答案：B. Terminate 在 Gateway 处终止 TLS，Passthrough 将 TLS 传递给 backend**

**说明：**
TLS 模式：

| 模式 | 描述 | 使用场景 |
|------|-------------|----------|
| **Terminate** | TLS 在 Gateway 处终止，backend 接收明文 | 标准 HTTPS、集中式证书管理 |
| **Passthrough** | TLS 原样透传至 backend | 端到端加密、backend 管理证书 |

```yaml
listeners:
  - name: https
    protocol: HTTPS
    tls:
      mode: Terminate  # or Passthrough
```

</details>

### 4. 如何在 HTTPRoute 中实现流量拆分（权重）？

A. 使用 `trafficSplit` 字段
B. 在多个 `backendRefs` 上指定 `weight` 字段
C. 使用 `canary` 注解
D. 创建单独的 TrafficSplit CRD

<details>
<summary>显示答案</summary>

**答案：B. 在多个 `backendRefs` 上指定 `weight` 字段**

**说明：**
HTTPRoute 中的流量拆分：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
spec:
  rules:
    - backendRefs:
        - name: app-stable
          port: 80
          weight: 90  # 90%
        - name: app-canary
          port: 80
          weight: 10  # 10%
```

使用场景：
- Canary 部署
- A/B 测试
- 蓝绿部署

权重之和无需为 100；它们按比例计算。

</details>

### 5. ReferenceGrant 的主要目的是什么？

A. Gateway 资源权限管理
B. 允许跨 namespace 引用
C. API 版本兼容性管理
D. TLS 证书授权

<details>
<summary>显示答案</summary>

**答案：B. 允许跨 namespace 引用**

**说明：**
ReferenceGrant 用法：

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes
  namespace: backend-services
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend
  to:
    - group: ""
      kind: Service
```

使用场景：
- 允许引用其他 namespace 中的 Service
- Gateway 引用其他 namespace 中的 Secret（TLS 证书）
- 为安全性进行显式授权

默认会阻止跨 namespace 引用。

</details>

### 6. 以下哪项不是 Gateway API Standard channel 中包含的资源？

A. GatewayClass
B. Gateway
C. HTTPRoute
D. TCPRoute

<details>
<summary>显示答案</summary>

**答案：D. TCPRoute**

**说明：**
Gateway API channel 分类：

**Standard Channel (GA)**：
- GatewayClass
- Gateway
- HTTPRoute
- ReferenceGrant

**Experimental Channel (Beta/Alpha)**：
- GRPCRoute
- TCPRoute
- TLSRoute
- UDPRoute

Standard channel 资源使用 `gateway.networking.k8s.io/v1` API 版本，Experimental 使用 `v1alpha2` 或 `v1beta1`。

</details>

### 7. 哪种 HTTPRoute filter 类型会将请求更改为不同的 URL？

A. RequestHeaderModifier
B. ResponseHeaderModifier
C. URLRewrite
D. RequestMirror

<details>
<summary>显示答案</summary>

**答案：C. URLRewrite**

**说明：**
HTTPRoute filter 类型：

| Filter | 描述 |
|--------|-------------|
| RequestHeaderModifier | 添加、修改或删除请求 header |
| ResponseHeaderModifier | 添加、修改或删除响应 header |
| **URLRewrite** | 更改 URL path 或 host |
| RequestRedirect | 重定向到其他 URL（3xx 响应） |
| RequestMirror | 镜像流量（复制到 shadow Service） |

```yaml
filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /new-api
      hostname: "new-api.example.com"
```

</details>

### 8. 以下哪项不是支持 Gateway API 的实现？

A. Istio
B. Cilium
C. kube-proxy
D. Envoy Gateway

<details>
<summary>显示答案</summary>

**答案：C. kube-proxy**

**说明：**
Gateway API 实现：

| 实现 | Controller |
|----------------|------------|
| **Istio** | istio.io/gateway-controller |
| **Cilium** | io.cilium/gateway-controller |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller |
| **Contour** | projectcontour.io/gateway-controller |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller |

kube-proxy 处理 Service ClusterIP/NodePort 路由，与 Gateway API 无关。

</details>

### 9. 从 Ingress 迁移到 Gateway API 时，哪项 Gateway API 功能对应于 Ingress 注解？

A. Gateway metadata
B. HTTPRoute matches 和 filters
C. GatewayClass parameters
D. ReferenceGrant spec

<details>
<summary>显示答案</summary>

**答案：B. HTTPRoute matches 和 filters**

**说明：**
Ingress 注解 → Gateway API 映射：

| Ingress 注解 | Gateway API |
|-------------------|-------------|
| `nginx.ingress.kubernetes.io/rewrite-target` | HTTPRoute filter: URLRewrite |
| `nginx.ingress.kubernetes.io/ssl-redirect` | HTTPRoute filter: RequestRedirect |
| `nginx.ingress.kubernetes.io/canary-weight` | HTTPRoute backendRefs weight |
| 基于 path 的路由 | HTTPRoute matches path |
| 基于 header 的路由 | HTTPRoute matches headers |

Gateway API 使用显式字段而非注解，以提供更好的可移植性。

</details>

### 10. 在 Gateway 中，仅允许来自特定 namespace 的 Routes 的配置是什么？

A. `allowedRoutes.namespaces.from: All`
B. `allowedRoutes.namespaces.from: Same`
C. `allowedRoutes.namespaces.from: Selector`
D. B 和 C 都可以

<details>
<summary>显示答案</summary>

**答案：D. B 和 C 都可以**

**说明：**
Gateway allowedRoutes 配置：

```yaml
listeners:
  - name: https
    allowedRoutes:
      namespaces:
        from: All  # All namespaces
        # or
        from: Same  # Only same namespace as Gateway
        # or
        from: Selector  # Select by label selector
        selector:
          matchLabels:
            gateway-access: "true"
```

- **All**：允许来自所有 namespace 的 Routes
- **Same**：仅允许与 Gateway 位于同一 namespace 的 Routes
- **Selector**：仅允许来自具有特定 label 的 namespace 的 Routes

</details>

### 11. 在 GRPCRoute 中，路由到特定 Service 的特定 method 的 matches 配置是什么？

A. `path.service` 和 `path.method`
B. `method.service` 和 `method.method`
C. `grpc.service` 和 `grpc.method`
D. `rpc.service` 和 `rpc.method`

<details>
<summary>显示答案</summary>

**答案：B. `method.service` 和 `method.method`**

**说明：**
GRPCRoute 匹配：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
spec:
  rules:
    - matches:
        - method:
            service: "myapp.UserService"
            method: "GetUser"
      backendRefs:
        - name: user-service
          port: 50051
```

gRPC 路由选项：
- 仅 Service：该 Service 的所有 method
- Service + method：仅特定 method
- 也支持基于 header 的路由

</details>

### 12. 以下 Gateway API 与 Ingress API 的比较中，哪项不正确？

A. Gateway API 支持基于角色的分离，Ingress 不支持
B. Gateway API 原生支持 TCP/UDP，Ingress 不支持
C. Gateway API 原生支持流量拆分，Ingress 需要注解
D. Gateway API 使用的资源类型比 Ingress 少

<details>
<summary>显示答案</summary>

**答案：D. Gateway API 使用的资源类型比 Ingress 少**

**说明：**
Gateway API 与 Ingress：

| 功能 | Ingress | Gateway API |
|---------|---------|-------------|
| 资源数量 | 1 (Ingress) | 多个（GatewayClass、Gateway、Routes 等） |
| 角色分离 | 无 | 3 层分离 |
| TCP/UDP | 不支持 | 原生支持 |
| 流量拆分 | 注解 | 原生（weight） |
| 可扩展性 | 有限 | 基于 CRD |

Gateway API 使用更多资源类型，但这提供了角色分离和灵活性。

</details>

---

## 补充学习资源

- [Gateway API 官方文档](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [特定实现指南](https://gateway-api.sigs.k8s.io/implementations/)
