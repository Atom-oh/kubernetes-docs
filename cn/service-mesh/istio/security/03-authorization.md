# 授权

AuthorizationPolicy 可让你精细控制服务访问权限。

## 目录

1. [授权概述](#authorization-overview)
2. [基本策略](#basic-policies)
3. [高级策略](#advanced-policies)
4. [实用示例](#practical-examples)
5. [最佳实践](#best-practices)

## 授权概述 {#authorization-overview}

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Istio Authorization" width="700">
</p>

Istio AuthorizationPolicy 为服务提供精细化访问控制。上图展示了 Authorization Policy 的工作方式：

1. **接收请求**：Envoy 接收入站请求
2. **策略评估**：先匹配 CUSTOM 策略，然后是 DENY，最后是 ALLOW；与 YAML 中的创建顺序无关
3. **访问决策**：应用 ALLOW、DENY 或 CUSTOM 操作
4. **审计日志记录**：需要配置访问日志/审计日志；AUDIT 本身只会标记请求

**支持的条件**：
- **来源**：请求来源（ServiceAccount、Namespace、IP）
- **操作**：HTTP 方法、路径、端口
- **条件**：自定义条件（标头、JWT 声明等）

![流程图展示 Istio AuthorizationPolicy 如何依次通过三项检查（Service Account、Namespace 和 HTTP Method）来评估请求；全部匹配时允许请求，任何一项不匹配都会立即拒绝请求。](../../../.gitbook/assets/en-service-mesh-istio-security-03-authorization-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-03-authorization-0.html)

## 基本策略 {#basic-policies}

该图展示了一条要求所有条件同时满足的规则。同一规则中的 from/to/when 约束按“且”关系组合；不同规则以及适用的 ALLOW 策略之间则是“或”关系。如果某个工作负载没有 ALLOW 策略，请求将被允许，除非被 CUSTOM/DENY 拒绝。一旦有 ALLOW 策略适用于该工作负载，请求就必须至少匹配一条 ALLOW 规则。以下示例是供选择的不同配置方案；允许所有请求会放宽仅允许 GET 请求的策略。

### 默认拒绝（拒绝所有）

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []  # Default deny with room for specific ALLOW exceptions
```

### 默认允许（允许所有）

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-all
  namespace: default
spec:
  action: ALLOW
  rules:
  - {}  # Allow all requests
```

### 基于 HTTP 方法

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin-get-only
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - to:
    - operation:
        methods: ["GET"]  # Allow only GET
```

## 高级策略 {#advanced-policies}

### 基于 Service Account

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ratings-sa-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]  # Allow only reviews SA
```

### 基于 Namespace

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: db-namespace-policy
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgresql
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production", "staging"]  # Specific namespaces only
```

### 基于路径

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: path-based-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
  - to:
    - operation:
        paths: ["/api/public/*"]  # Allow only public API
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/admin"]
    to:
    - operation:
        paths: ["/api/admin/*"]  # admin SA can access admin API
```

### 基于 JWT 声明

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: jwt-claims-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[role]
      values: ["admin", "superuser"]  # role claim is admin or superuser
```

## 实用示例 {#practical-examples}

若要设置默认拒绝并配置例外，请应用空的 ALLOW 策略，并仅添加预期的特定 ALLOW 规则。包含 rules: [{}] 的显式 DENY 会形成无法被任何 ALLOW 覆盖的硬性阻止。不带 selector 的策略会应用于其所在的 Namespace；根 Namespace 和 targetRefs 附加规则需要分别谨慎处理。

基于 Service Account/Namespace 的匹配要求经过身份验证的 mTLS 对端身份。JWT 角色示例要求配置匹配的 RequestAuthentication，并验证预期的签发者/受众。客户端标头不能替代这两种身份。对于原生 TCP，应匹配身份/IP/端口，而不是 HTTP 方法或 JWT 声明；DENY 规则中缺少 HTTP 属性时，可能会意外匹配 TCP 流量。

## 最佳实践 {#best-practices}

- 将策略范围限定为预期的工作负载/资源，并一并检查所有适用的 ALLOW 规则。
- 对 ambient L7 策略使用 waypoint targetRefs；sidecar selector 不是 waypoint 附加方式。
- 验证无策略、无匹配、显式拒绝和允许请求等情况，包括 Namespace 边界。
- 明确配置日志记录，并使用 `istioctl x authz check <pod> -n <namespace>` 检查生效的策略。

## 参考资料

- [Istio Authorization Policy](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Authorization Examples](https://istio.io/latest/docs/tasks/security/authorization/)
