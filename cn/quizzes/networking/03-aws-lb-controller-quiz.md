# AWS Load Balancer Controller 测验

本测验用于检验您对 AWS Load Balancer Controller 架构、ALB/NLB 配置和运维的理解。

## 测验问题

### 1. AWS Load Balancer Controller 替代了哪个现有 Kubernetes 组件？

A. kube-proxy
B. 内置 AWS cloud provider
C. CoreDNS
D. CNI plugin

<details>
<summary>显示答案</summary>

**答案：B. 内置 AWS cloud provider**

**说明：**
AWS Load Balancer Controller 替代了现有 Kubernetes 内置 AWS cloud provider 的 load balancer 功能：
- 更多功能（高级 ALB、NLB 配置）
- 更快的更新和 bug 修复
- 与 AWS 服务更好地集成

内置 provider 仅支持基础 ELB Classic，而 AWS Load Balancer Controller 支持 ALB 和 NLB 的全部功能。

</details>

### 2. ALB Ingress 中 `ip` 和 `instance` target-type annotation 的正确区别是什么？

A. `ip` 直接指向 Pod IP，`instance` 通过 NodePort 路由
B. `ip` 通过 NodePort 路由，`instance` 直接指向 Pod IP
C. 两个选项的行为相同
D. `ip` 仅支持 IPv4，`instance` 仅支持 IPv6

<details>
<summary>显示答案</summary>

**答案：A. `ip` 直接指向 Pod IP，`instance` 通过 NodePort 路由**

**说明：**
Target Type 对比：

| Target Type | 行为 | 优点 | 缺点 |
|-------------|----------|------|------|
| `ip` | 直接注册 Pod IP | 低延迟，高效 | 需要 VPC CNI |
| `instance` | 路由到 Node 的 NodePort | 通用 | 额外一跳 |

使用 `ip` 类型时，需要 AWS VPC CNI，并且会将 Pod IP 直接注册到 Target Group 中。

</details>

### 3. 为什么 AWS Load Balancer Controller 需要 IRSA (IAM Roles for Service Accounts)？

A. 用于 Pod 到 Pod 通信
B. 用于让 controller 调用 AWS API 以创建/管理资源
C. 用于 Kubernetes API server 身份验证
D. 用于 TLS certificate 管理

<details>
<summary>显示答案</summary>

**答案：B. 用于让 controller 调用 AWS API 以创建/管理资源**

**说明：**
AWS Load Balancer Controller 需要调用 AWS API 来：
- 创建和管理 ALB/NLB
- 创建 Target Group 并注册 target
- 配置 Listener 和规则
- 管理 security group
- 查询 ACM certificate

通过 IRSA 将 IAM Role 关联到 Service Account：
- Pod 可以向 AWS API 进行身份验证
- 应用最小权限原则
- 向特定 Pod 而非整个 Node 授予权限

</details>

### 4. 如何将多个 Ingress 资源整合到单个 ALB 中？

A. 部署在同一个 namespace 中
B. 使用 `alb.ingress.kubernetes.io/group.name` annotation
C. 使用相同的 IngressClass
D. ALB 始终只支持一个 Ingress

<details>
<summary>显示答案</summary>

**答案：B. 使用 `alb.ingress.kubernetes.io/group.name` annotation**

**说明：**
Ingress Group 功能：

```yaml
# Ingress 1
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "1"
---
# Ingress 2
metadata:
  annotations:
    alb.ingress.kubernetes.io/group.name: my-app-group
    alb.ingress.kubernetes.io/group.order: "2"
```

优点：
- 节省 ALB 成本（多个 Service 共享一个 ALB）
- 集中管理
- 通过指定 order 控制规则优先级

</details>

### 5. 在 NLB Service 上实现 TLS termination 的 annotation 是什么？

A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`
B. `alb.ingress.kubernetes.io/certificate-arn`
C. `service.beta.kubernetes.io/aws-load-balancer-tls-termination`
D. `nlb.kubernetes.io/ssl-certificate`

<details>
<summary>显示答案</summary>

**答案：A. `service.beta.kubernetes.io/aws-load-balancer-ssl-cert`**

**说明：**
NLB TLS termination 配置：

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:..."
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8080
```

`alb.ingress.kubernetes.io/certificate-arn` 是用于 ALB Ingress 的 annotation。

</details>

### 6. TargetGroupBinding CRD 的主要用途是什么？

A. 自动创建新的 Target Group
B. 将现有 AWS Target Group 连接到 Kubernetes Service
C. 定义 ALB Listener 规则
D. 自动创建 security group

<details>
<summary>显示答案</summary>

**答案：B. 将现有 AWS Target Group 连接到 Kubernetes Service**

**说明：**
TargetGroupBinding 使用场景：
1. 迁移现有基础设施 - 利用现有 Target Group
2. 多集群共享 - 在多个集群间使用一个 ALB/NLB
3. 需要直接管理 Target Group 时

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:...
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

</details>

### 7. 将 WAF v2 与 ALB Ingress 集成的 annotation 是什么？

A. `alb.ingress.kubernetes.io/waf-acl-id`
B. `alb.ingress.kubernetes.io/wafv2-acl-arn`
C. `alb.ingress.kubernetes.io/web-acl`
D. `alb.ingress.kubernetes.io/firewall-rules`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/wafv2-acl-arn`**

**说明：**
AWS WAF v2 集成：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-east-1:ACCOUNT:regional/webacl/my-acl/xxx
```

WAF v2 功能：
- SQL injection、XSS 防护
- Rate limiting
- 基于 IP 的阻止/允许
- 自定义规则

安装 controller 时需要设置 `enableWafv2: true`。

</details>

### 8. AWS Load Balancer Controller 自动发现 subnet 所需的 tag 是什么？

A. `kubernetes.io/cluster/<cluster-name>=owned`
B. `kubernetes.io/role/elb=1`（public），`kubernetes.io/role/internal-elb=1`（private）
C. `aws:cloudformation:stack-name`
D. `Name=kubernetes-subnet`

<details>
<summary>显示答案</summary>

**答案：B. `kubernetes.io/role/elb=1`（public），`kubernetes.io/role/internal-elb=1`（private）**

**说明：**
Subnet tagging 规则：

```bash
# Public subnets (for internet-facing ALB/NLB)
kubernetes.io/role/elb=1

# Private subnets (for internal ALB/NLB)
kubernetes.io/role/internal-elb=1

# Cluster ownership (optional)
kubernetes.io/cluster/<cluster-name>=shared or owned
```

如果没有这些 tag，controller 可能无法找到合适的 subnet，导致 load balancer 创建失败。

</details>

### 9. 在 ALB Ingress 中启用 Sticky Sessions 的 annotation 是什么？

A. `alb.ingress.kubernetes.io/sticky-sessions=true`
B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`
C. `alb.ingress.kubernetes.io/session-affinity=cookie`
D. `alb.ingress.kubernetes.io/cookie-based-routing=true`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true`**

**说明：**
Sticky Session 配置：

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/target-group-attributes: >-
      stickiness.enabled=true,
      stickiness.lb_cookie.duration_seconds=3600
```

配置为 Target Group attribute：
- `stickiness.enabled=true` - 启用
- `stickiness.lb_cookie.duration_seconds` - Cookie 有效期
- `stickiness.type` - lb_cookie 或 app_cookie

Sticky Sessions 对于需要保持 session state 的 legacy application 很有用。

</details>

### 10. 如何在 NLB 中保留 client source IP？

A. 使用 `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"`
B. 使用 externalTrafficPolicy: Local
C. 两种方法都可以
D. NLB 始终保留 client IP

<details>
<summary>显示答案</summary>

**答案：C. 两种方法都可以**

**说明：**
保留 client IP 的方法：

1. **Proxy Protocol v2**:
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: proxy_protocol_v2.enabled=true
```
- Application 必须支持 Proxy Protocol

2. **externalTrafficPolicy: Local**:
```yaml
spec:
  externalTrafficPolicy: Local
```
- 仅路由到同一 Node 上的 Pod，无额外跳转
- 可能导致流量分布不均

3. **IP Target Type**（ip mode）：
```yaml
annotations:
  service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
```

</details>

### 11. 在 ALB Ingress 中将 HTTP 重定向到 HTTPS 的 annotation 是什么？

A. `alb.ingress.kubernetes.io/actions.ssl-redirect`
B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`
C. `alb.ingress.kubernetes.io/force-ssl-redirect: "true"`
D. `alb.ingress.kubernetes.io/http-to-https: "true"`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/ssl-redirect: "443"`**

**说明：**
SSL redirect 配置：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
```

行为：
- 将访问 HTTP(80) 的请求以 301 重定向到 HTTPS(443)
- 推荐作为安全最佳实践
- 需要 ACM certificate

</details>

### 12. 当 AWS Load Balancer Controller 未创建 ALB 时，以下哪项不是需要检查的内容？

A. 检查 IAM 权限
B. 检查 subnet tag
C. 检查 IngressClass specification
D. 检查 kube-proxy log

<details>
<summary>显示答案</summary>

**答案：D. 检查 kube-proxy log**

**说明：**
ALB 创建失败时需要检查的内容：

1. **IAM 权限**：Service Account 的 IAM Role 是否具有所需权限
2. **Subnet tag**：`kubernetes.io/role/elb=1` 或 `kubernetes.io/role/internal-elb=1`
3. **IngressClass**：指定 `ingressClassName: alb` 或通过 annotation 指定
4. **Controller log**：`kubectl logs -n kube-system deployment/aws-load-balancer-controller`
5. **Ingress event**：`kubectl describe ingress <name>`

kube-proxy 负责 Service ClusterIP/NodePort 路由，与 ALB 创建无关。

</details>

---

## 其他学习资源

- [AWS Load Balancer Controller 文档](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [EKS 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [ALB Annotation 参考](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.8/guide/ingress/annotations/)
