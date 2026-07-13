# EKS 网络测验 - 第 2 部分

本测验检验你对 Amazon EKS 中高级网络概念、AWS Load Balancer Controller、Ingress 资源、Service Mesh 和网络安全的理解。

## 选择题

### 1. AWS Load Balancer Controller 默认会为 Kubernetes Ingress 资源预置哪种类型的 AWS load balancer？

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>显示答案</summary>

**答案: C. Application Load Balancer (ALB)**

**解析:** AWS Load Balancer Controller 默认会为 Kubernetes Ingress 资源预置 Application Load Balancer (ALB)。ALB 是第 7 层 load balancer，可处理 HTTP/HTTPS 流量，并提供基于路径的路由、基于主机的路由和 TLS 终止等功能，以满足 Ingress 资源的需求。

**主要特性:**

1. **基于路径的路由**: ALB 可以根据 URL 路径将流量路由到不同 Service，适合在 Ingress 中实现基于路径的路由规则。
2. **基于主机的路由**: 可以使用单个 ALB 处理多个域名，支持包含多个 host 规则的 Ingress。
3. **TLS 终止**: ALB 可以管理 SSL/TLS 证书并终止 HTTPS 流量。
4. **WebSockets 支持**: ALB 支持 WebSockets 协议，适合实时应用。
5. **身份验证集成**: 可与 Amazon Cognito 或 OIDC 集成，以提供应用级身份验证。

**配置示例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**关键 Annotations:**

* `kubernetes.io/ingress.class: alb`: 指定使用 ALB Ingress Controller
* `alb.ingress.kubernetes.io/scheme: internet-facing`: 创建面向互联网的 ALB
* `alb.ingress.kubernetes.io/target-type: ip`: 使用 pod IP 作为目标（而不是 instance）
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`: 配置监听器端口
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`: 指定 SSL 证书

其他选项的问题:

* **A. Classic Load Balancer (CLB)**: AWS Load Balancer Controller 不会将 CLB 用于 Ingress 资源。CLB 被视为旧版 load balancer。
* **B. Network Load Balancer (NLB)**: NLB 主要用于 Service 类型 LoadBalancer，默认不用于 Ingress 资源。
* **D. Gateway Load Balancer (GWLB)**: GWLB 用于网络虚拟设备，不与 Kubernetes Ingress 资源一起使用。

</details>

### 2. 在 Amazon EKS 中，使用 AWS Load Balancer Controller 创建内部 Application Load Balancer 时，应向 Ingress 资源添加什么 annotation？

A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` B. `alb.ingress.kubernetes.io/scheme: internal` C. `kubernetes.io/ingress.class: internal-alb` D. `aws-load-balancer-type: internal`

<details>

<summary>显示答案</summary>

**答案: B. `alb.ingress.kubernetes.io/scheme: internal`**

**解析:** 要在 Amazon EKS 中使用 AWS Load Balancer Controller 创建内部 Application Load Balancer，必须向 Ingress 资源添加 `alb.ingress.kubernetes.io/scheme: internal` annotation。此 annotation 会将 ALB 配置为仅可在 VPC 内访问。

**内部 ALB 配置示例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
spec:
  rules:
  - host: internal.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```

**关键注意事项:**

1.  **Subnet 选择**: 内部 ALB 会创建在私有 subnet 中。可以显式指定 subnet:

    ```yaml
    alb.ingress.kubernetes.io/subnets: subnet-0123456789abcdef0,subnet-0123456789abcdef1
    ```
2.  **Security Groups**: 可以将特定 Security Groups 应用于内部 ALB:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
3.  **入站 CIDR 限制**: 可以仅允许来自特定 CIDR blocks 的访问:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
4.  **内部 DNS**: 内部 ALB 可以与 VPC 内的 Route 53 private hosted zones 集成:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: routing.http.drop_invalid_header_fields.enabled=true,access_logs.s3.enabled=true
    ```

**内部 ALB 的使用场景:**

* 微服务之间的内部通信
* 后端 API Service
* 管理界面
* 开发和测试环境
* 有合规要求的工作负载

**验证 AWS Load Balancer Controller 安装:**

```bash
kubectl get deployment -n kube-system aws-load-balancer-controller
```

其他选项的问题:

* **A. `service.beta.kubernetes.io/aws-load-balancer-internal: "true"`**: 此 annotation 用于 Service 类型 LoadBalancer，不适用于 Ingress 资源。
* **C. `kubernetes.io/ingress.class: internal-alb`**: 正确的 ingress.class 是 'alb'；'internal-alb' 不是有效值。
* **D. `aws-load-balancer-type: internal`**: 此 annotation 不存在。

</details>

### 3. 在 Amazon EKS 中，使用什么 annotation 配置 AWS Load Balancer Controller 直接使用 pod IP 作为目标？

A. `alb.ingress.kubernetes.io/target-type: pod` B. `alb.ingress.kubernetes.io/target-type: ip` C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip` D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>

<summary>显示答案</summary>

**答案: B. `alb.ingress.kubernetes.io/target-type: ip`**

**解析:** 要在 Amazon EKS 中配置 AWS Load Balancer Controller 直接使用 pod IP 作为目标，必须使用 `alb.ingress.kubernetes.io/target-type: ip` annotation。此设置允许 load balancer 将流量直接路由到 pod IP，而不是 node IP。

**目标类型选项:**

1. **instance**:（默认）使用 node IP 和 NodePort 路由流量。
2. **ip**: 使用 pod IP 和 container port 将流量直接路由到 pods。

**IP 模式配置示例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```

**IP 模式的优势:**

1. **Node 故障韧性**: 即使 node 发生故障，流量也会继续路由到其他 node 上的 pods。
2. **直接路由**: 流量会直接传递到 pods，无需通过 NodePort 进行额外跳转。
3. **Fargate 兼容性**: 运行在 AWS Fargate 上的 pods 必须使用此模式。
4. **Security Group 集成**: 可以在 pod 级别应用 Security Groups。

**IP 模式要求:**

1. **VPC CNI**: 需要 Amazon VPC CNI plugin。
2. **Subnet 配置**: pods 运行所在的 subnets 必须可路由到 load balancer subnets。
3. **Security Group 规则**: load balancer 的 security group 必须允许到 pod IP 的流量。

**IP 模式与 Instance 模式比较:**

| 特性            | IP 模式            | Instance 模式                      |
| --------------- | ------------------ | ----------------------------------- |
| 目标            | Pod IP             | Node IP                             |
| 端口            | Container port     | NodePort                            |
| 流量路径        | LB -> Pod          | LB -> Node -> Pod                   |
| Node 故障时     | 无影响             | 该 node 上的 Pods 不可访问          |
| 性能            | 性能更好           | 由于额外跳转有轻微开销              |
| Fargate 支持    | 支持               | 不支持                              |

**其他配置选项:**

```yaml
# Target group attributes setting
alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30,stickiness.enabled=true

# Health check settings
alb.ingress.kubernetes.io/healthcheck-path: /health
alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
alb.ingress.kubernetes.io/success-codes: '200'
alb.ingress.kubernetes.io/healthy-threshold-count: '2'
alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'
```

其他选项的问题:

* **A. `alb.ingress.kubernetes.io/target-type: pod`**: 正确值是 'ip'，不是 'pod'。
* **C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`**: 此 annotation 用于 Service 类型 LoadBalancer，不适用于 Ingress 资源。
* **D. `aws-load-balancer-target-node-labels: ip-mode=true`**: 此 annotation 不存在。

</details>

### 4. 在 Amazon EKS 中，使用什么 annotation 将 Kubernetes Service 与 AWS PrivateLink 集成，以创建 VPC endpoint service？

A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb` B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"` C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`

<details>

<summary>显示答案</summary>

**答案: C. `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip`**

**解析:** 要在 Amazon EKS 中将 Kubernetes Service 与 AWS PrivateLink 集成并创建 VPC endpoint service，必须使用 `service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip` annotation。此 annotation 会创建 IP 模式的 Network Load Balancer (NLB)，这是与 AWS PrivateLink 集成的前提条件。

**VPC Endpoint Service 配置步骤:**

1. **使用 NLB-IP 模式创建 Kubernetes Service:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: my-app
```

2. **使用 AWS CLI 创建 VPC Endpoint Service:**

```bash
# Get NLB ARN
NLB_ARN=$(aws elbv2 describe-load-balancers --names $(kubectl get svc privatelink-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | cut -d- -f1) --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create VPC endpoint service
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns $NLB_ARN \
  --acceptance-required \
  --private-dns-name service.example.com
```

3. **配置 VPC Endpoint Service 允许列表:**

```bash
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-id vpce-svc-0123456789abcdef0 \
  --add-allowed-principals arn:aws:iam::111122223333:root
```

**关键注意事项:**

1. **内部 NLB 要求**: PrivateLink 要求使用内部 NLB，因此还需要 `service.beta.kubernetes.io/aws-load-balancer-internal: "true"` annotation。
2. **IP 模式的重要性**: NLB-IP 模式通过直接使用 pod IP 作为目标，提供对 node 故障的韧性。
3. **Service 名称解析**: 可以配置 Private DNS names，以简化 VPC 内的 service name resolution。
4. **访问控制**: 可以使用 `acceptance-required` 标志手动批准 endpoint connection requests。
5. **Network ACLs 和 Security Groups**: 确保配置了适当的 network ACL 和 security group 规则。

**PrivateLink 集成的优势:**

* **增强安全性**: 流量保留在 AWS network 内，不经过公共互联网。
* **合规性**: 满足数据主权和合规要求。
* **简化网络**: 无需 VPC peering、Transit Gateway 或 VPN 连接即可访问 Service。
* **可扩展性**: 可以从数千个 VPC 访问 Service。

**客户端配置:**

```bash
# Create VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-0123456789abcdef0 \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-0123456789abcdef0 subnet-0123456789abcdef1 \
  --security-group-ids sg-0123456789abcdef0
```

其他选项的问题:

* **A. `service.beta.kubernetes.io/aws-load-balancer-type: nlb`**: 此 annotation 会创建 instance 模式的 NLB，不适合 PrivateLink 集成优化。
* **B. `service.beta.kubernetes.io/aws-load-balancer-private-link: "true"`**: 此 annotation 不存在。
* **D. `service.beta.kubernetes.io/aws-vpc-endpoint-service: "true"`**: 此 annotation 不存在。

</details>

### 5. 可以将哪个附加组件与 Amazon VPC CNI 一起使用，以在 Amazon EKS 中实现 Kubernetes NetworkPolicy 资源？

A. AWS Network Firewall B. Calico C. AWS Security Groups for Pods D. VPC Flow Logs

<details>

<summary>显示答案</summary>

**答案: B. Calico**

**解析:** Calico 是可与 Amazon VPC CNI 一起使用、用于在 Amazon EKS 中实现 Kubernetes NetworkPolicy 资源的附加组件。Calico 是一个开源网络和网络安全解决方案，支持 Kubernetes NetworkPolicy API，并与 Amazon VPC CNI 协同工作，在 EKS clusters 中应用细粒度网络策略。

**Calico 安装和配置:**

1. **安装 Calico:**

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

2. **验证安装:**

```bash
kubectl get pods -n calico-system
```

3. **基本 NetworkPolicy 示例:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Calico 的主要特性:**

1. **Kubernetes NetworkPolicy 支持**: 完整实现标准 Kubernetes NetworkPolicy API。
2. **扩展策略特性**: 通过 Calico 的 GlobalNetworkPolicy 和 NetworkSet 等自定义资源，提供超出 Kubernetes NetworkPolicy 的高级网络策略。
3. **细粒度控制**: 可根据协议、端口、CIDR blocks、service accounts 等过滤流量。
4. **日志记录和监控**: 可以记录和监控网络策略违规。
5. **Host Endpoint 保护**: 可以将网络策略应用到 Kubernetes nodes 本身。

**Calico 高级策略示例:**

```yaml
# GlobalNetworkPolicy example (cluster-wide policy)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-cluster-internal-traffic
spec:
  selector: all()
  types:
  - Ingress
  - Egress
  ingress:
  - action: Allow
    source:
      selector: all()
  egress:
  - action: Allow
    destination:
      selector: all()

# Restrict access to specific IP ranges
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-services
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.0/24
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-services
  namespace: app
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    - ipBlock:
        cidr: 198.51.100.0/24
```

**Amazon VPC CNI 与 Calico 的集成:**

1. **网络模式**: 与 Amazon VPC CNI 一起使用时，Calico 以 policy-only 模式运行，而不是 overlay 模式。
2. **性能**: 在利用 Calico 网络策略功能的同时，保持 Amazon VPC CNI 原生 VPC 网络性能。
3. **兼容性**: Calico 与所有 Amazon VPC CNI 功能兼容（prefix delegation、custom networking 等）。
4. **升级**: Calico 和 Amazon VPC CNI 可以独立升级。

**最佳实践:**

* 从默认拒绝策略开始，并仅显式允许必要通信。
* 为 namespace 之间的通信定义清晰策略。
* 在应用策略前，先在日志模式下测试策略。
* 始终允许与 cluster 基础组件通信。
* 定期审查和更新策略。

其他选项的问题:

* **A. AWS Network Firewall**: AWS Network Firewall 是 VPC 级别的 firewall service，不与 Kubernetes NetworkPolicy 直接集成。
* **C. AWS Security Groups for Pods**: Security Groups for Pods 是将 AWS security groups 应用到 pods 的功能，但不实现 Kubernetes NetworkPolicy API。
* **D. VPC Flow Logs**: VPC Flow Logs 是用于监控网络流量的工具，不应用网络策略。

</details>

## 简答题

### 6. 使用 AWS Load Balancer Controller 在 Amazon EKS 中创建 Application Load Balancer 时，使用什么 annotation 将特定 security groups 分配给该 Application Load Balancer？

<details>

<summary>显示答案</summary>

**答案:** `alb.ingress.kubernetes.io/security-groups: sg-xxxx,sg-yyyy`

**详细解析:**

使用 AWS Load Balancer Controller 创建 Application Load Balancer (ALB) 时，可以使用 `alb.ingress.kubernetes.io/security-groups` annotation 来分配特定 security groups。此 annotation 指定要附加到 ALB 的 security group IDs，并以逗号分隔。

**实现方法:**

1.  **指定 Security Group IDs:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0,sg-0123456789abcdef1
    spec:
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example-service
                port:
                  number: 80
    ```
2.  **指定 Security Group Names（替代方法）:**

    ```yaml
    alb.ingress.kubernetes.io/security-groups: my-security-group-name
    ```
3.  **自动创建 Security Groups:**

    ```yaml
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```

**关键注意事项:**

1. **Security Group 规则:**
   * 入站规则: 必须允许客户端流量（通常是 HTTP/80、HTTPS/443）。
   * 出站规则: 必须允许到 target groups（pods 或 nodes）的流量。
2. **默认行为:** 未指定 annotation 时，AWS Load Balancer Controller 会自动创建 security group 并配置必要规则。
3. **权限要求:** AWS Load Balancer Controller 的 IAM role 需要以下权限:
   * ec2:CreateSecurityGroup
   * ec2:DeleteSecurityGroup
   * ec2:DescribeSecurityGroups
   * ec2:AuthorizeSecurityGroupIngress
   * ec2:RevokeSecurityGroupIngress
4.  **Security Group 管理:**

    ```yaml
    # Set controller to manage security group rules
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    ```
5.  **标记:** 可以向创建的 security groups 添加 tags:

    ```yaml
    alb.ingress.kubernetes.io/tags: Environment=prod,Team=devops
    ```

**最佳实践:**

1. **最小权限原则:** 使用限制性 security group 规则，只允许必要流量。
2. **Security Group 复用:** 在多个 Ingress 资源中复用相同 security groups，以简化管理。
3. **文档化:** 记录所使用的 security groups 及其规则，便于跟踪。
4. **定期审查:** 定期审查 security group 规则，移除不必要的访问。
5. **监控:** 监控被拒绝的连接，以评估 security group 规则的有效性。

**相关 Annotations:**

*   **入站 CIDR 限制:**

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 10.0.0.0/16,192.168.0.0/16
    ```
*   **Security Group Tags:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **SSL Policy:**

    ```yaml
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    ```

使用 AWS Load Balancer Controller 可以通过 Kubernetes Ingress 资源对 ALB security groups 进行细粒度控制，这有助于增强 cluster 的网络安全态势。

</details>

### 7. 在 Amazon EKS 中，将 Kubernetes Service 资源公开为 Network Load Balancer 时，使用什么 annotation 保留客户端 IP 地址？

<details>

<summary>显示答案</summary>

**答案:** `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`

**详细解析:**

在 Amazon EKS 中将 Kubernetes Service 资源公开为 Network Load Balancer (NLB) 时，必须使用 `service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true` annotation 来保留客户端 IP 地址。此设置使 NLB 保持原始客户端 IP 地址。

**实现方法:**

1.  **基本 NLB Service 配置:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```
2.  **与 IP 模式 NLB 一起使用:**

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: example-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb-ip
        service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: example
    ```

**保留客户端 IP 的重要性:**

1. **安全和访问控制:**
   * 实现基于客户端 IP 的访问控制
   * 阻止可疑 IP 地址
   * 应用基于 IP 的速率限制
2. **日志记录和审计:**
   * 跟踪请求来源
   * 调查安全事件
   * 满足合规要求
3. **基于地理位置的功能:**
   * 提供区域特定内容
   * 执行地理分析

**工作原理:**

1. **Instance 模式 (aws-load-balancer-type: nlb):**
   * 对于 TCP 流量，会自动保留客户端 IP。
   * 对于 UDP 流量，需要 preserve\_client\_ip.enabled=true 设置。
2. **IP 模式 (aws-load-balancer-type: nlb-ip):**
   * TCP 和 UDP 流量都需要 preserve\_client\_ip.enabled=true 设置。

**限制和注意事项:**

1. **Proxy Protocol:** 客户端 IP 保留通过直接数据包路由完成，不使用 proxy protocol。
2. **Target Group 类型:**
   * Instance 模式: 使用 node IP 和 NodePort。
   * IP 模式: 直接使用 pod IP 和 port。
3. **性能影响:** 客户端 IP 保留可能带来轻微性能开销。
4. **兼容性:** 某些旧版应用可能不兼容客户端 IP 保留。

**在应用中访问客户端 IP:**

1.  **HTTP 应用:**

    ```python
    # Python Flask example
    from flask import Flask, request

    app = Flask(__name__)

    @app.route('/')
    def index():
        client_ip = request.remote_addr
        return f"Your IP address is: {client_ip}"
    ```
2.  **TCP/UDP 应用:**

    ```go
    // Go example
    package main

    import (
        "fmt"
        "net"
    )

    func handleConnection(conn net.Conn) {
        addr := conn.RemoteAddr().String()
        fmt.Printf("Client connected from: %s\n", addr)
        // ...
    }
    ```

**相关 Annotations:**

*   **内部 NLB 配置:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    ```
*   **跨区域 Load Balancing:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: load_balancing.cross_zone.enabled=true
    ```
*   **TCP 连接 Keep-Alive:**

    ```yaml
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true,deregistration_delay.timeout_seconds=30
    ```

客户端 IP 保留对于安全、日志记录和访问控制等多种用途都很重要，并且可以在 EKS clusters 中使用适当 annotation 轻松配置。

</details>

### 8. 在 Amazon EKS 中，使用什么 annotation 将 AWS WAF (Web Application Firewall) 附加到 Kubernetes Ingress 资源？

<details>

<summary>显示答案</summary>

**答案:** `alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:region:account-id:global/webacl/name/id`

**详细解析:**

要在 Amazon EKS 中将 AWS WAF (Web Application Firewall) 附加到 Kubernetes Ingress 资源，必须使用 `alb.ingress.kubernetes.io/wafv2-acl-arn` annotation。此 annotation 会将 AWS WAF WebACL 附加到 AWS Load Balancer Controller 创建的 Application Load Balancer (ALB)。

**实现方法:**

1.  **创建 AWS WAF WebACL:** 首先，使用 AWS Management Console、AWS CLI 或 AWS CloudFormation 创建 WAF WebACL。

    ```bash
    # AWS CLI example
    aws wafv2 create-web-acl \
      --name "eks-ingress-protection" \
      --scope "REGIONAL" \
      --default-action Allow={} \
      --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-protection \
      --region us-west-2
    ```
2.  **在 Ingress 资源中指定 WAF WebACL ARN:**

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: example-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef
    spec:
      rules:
      - host: example.com
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example-service
                port:
                  number: 80
    ```

**AWS WAF 的主要保护功能:**

1. **常见 Web 漏洞防御:**
   * SQL injection 攻击
   * Cross-site scripting (XSS)
   * Path traversal 攻击
   * Command injection
2. **Bot 流量控制:**
   * 阻止恶意 bots
   * 防止 scraping
   * 防止 credential stuffing 攻击
3. **速率限制:**
   * 缓解 DDoS 攻击
   * 防止 brute force 攻击
4. **地理限制:**
   * 限制来自特定国家或地区的访问
5. **IP 声誉过滤:**
   * 阻止已知恶意 IP 地址

**AWS WAF Rule Group 示例:**

1. **AWS Managed Rules:**
   * AWS Core rule set (CRS)
   * SQL database rules
   * Linux operating system rules
   * PHP application rules
2.  **自定义 Rules:**

    ```json
    {
      "Name": "block-specific-uri-paths",
      "Priority": 1,
      "Action": { "Block": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "block-specific-uri-paths"
      },
      "Statement": {
        "ByteMatchStatement": {
          "SearchString": "/admin",
          "FieldToMatch": { "UriPath": {} },
          "TextTransformations": [
            { "Priority": 0, "Type": "NONE" }
          ],
          "PositionalConstraint": "STARTS_WITH"
        }
      }
    }
    ```

**监控和日志记录:**

1.  **启用 CloudWatch Logs:**

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```
2.  **配置 WAF 日志记录:**

    ```bash
    aws wafv2 put-logging-configuration \
      --logging-configuration ResourceArn=arn:aws:wafv2:us-west-2:111122223333:regional/webacl/eks-ingress-protection/a1b2c3d4-5678-90ab-cdef,LogDestinationConfigs=arn:aws:firehose:us-west-2:111122223333:deliverystream/aws-waf-logs \
      --region us-west-2
    ```

**权限要求:**

AWS Load Balancer Controller 的 IAM role 需要以下权限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

**最佳实践:**

1. **纵深防御:** 将 WAF 与网络安全、身份验证和授权等其他安全控制结合使用。
2. **定期更新规则:** 定期审查并更新 WAF 规则，以响应新威胁。
3. **日志记录和监控:** 分析 WAF logs，以识别攻击模式并改进规则。
4. **测试:** 在应用到生产环境前，在测试环境中验证 WAF 规则。
5. **Count 模式:** 首次部署新规则时，设置为 count mode 而不是 block，以监控误报。

AWS WAF 与 EKS Ingress 的集成是增强应用安全性的强大方式，并且可以使用适当的 annotation 轻松配置。

</details>

## 实践题

### 9. 编写一个 Ingress 资源，在 Amazon EKS cluster 中使用 AWS Load Balancer Controller 创建 Application Load Balancer，并根据特定路径将流量路由到不同 Service。

<details>

<summary>显示答案</summary>

**答案:** 以下是一个 Ingress 资源，它使用 AWS Load Balancer Controller 创建 Application Load Balancer，并根据特定路径将流量路由到不同 Service:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**详细解析:**

1. **Ingress 资源组件说明**:
   * **metadata.annotations**: 指定 AWS Load Balancer Controller 的配置选项。
     * `kubernetes.io/ingress.class: alb`: 指定使用 AWS Load Balancer Controller。
     * `alb.ingress.kubernetes.io/scheme: internet-facing`: 创建可从互联网访问的 ALB。
     * `alb.ingress.kubernetes.io/target-type: ip`: 使用 pod IP 作为目标。
     * `alb.ingress.kubernetes.io/listen-ports`: 同时监听 HTTP(80) 和 HTTPS(443) 端口。
     * `alb.ingress.kubernetes.io/certificate-arn`: 为 HTTPS 指定 ACM 证书。
     * `alb.ingress.kubernetes.io/ssl-redirect`: 将 HTTP 流量重定向到 HTTPS。
     * `alb.ingress.kubernetes.io/healthcheck-*`: 配置健康检查设置。
   * **spec.rules**: 定义基于 host 和 path 的路由规则。
     * `/api` 路径路由到 `api-service`。
     * `/admin` 路径路由到 `admin-service`。
     * `/`（root）路径路由到 `frontend-service`。
2.  **实现步骤**:

    a. **创建所需 Service**:

    ```yaml
    # api-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: api-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: api
    ---
    # admin-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: admin-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: admin
    ---
    # frontend-service.yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: frontend-service
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: frontend
    ```

    b. **为 Service 创建 Deployments**:

    ```yaml
    # api-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: api-deployment
    spec:
      replicas: 2
      selector:
        matchLabels:
          app: api
      template:
        metadata:
          labels:
            app: api
        spec:
          containers:
          - name: api
            image: nginx
            ports:
            - containerPort: 8080
            readinessProbe:
              httpGet:
                path: /health
                port: 8080
    ```

    （admin 和 frontend deployments 需要类似配置）

    c. **验证 AWS Load Balancer Controller 安装**:

    ```bash
    kubectl get deployment -n kube-system aws-load-balancer-controller
    ```

    d. **应用 Ingress 资源**:

    ```bash
    kubectl apply -f multi-path-ingress.yaml
    ```

    e. **检查 Ingress 状态**:

    ```bash
    kubectl get ingress multi-path-ingress
    ```
3.  **测试方法**:

    a. **DNS 设置**: 获取 Ingress 创建的 ALB 的 DNS 名称:

    ```bash
    kubectl get ingress multi-path-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    ```

    将此 DNS 名称设置为 `example.com` 的 CNAME 记录。

    b. **测试基于路径的路由**:

    ```bash
    # Test API service
    curl https://example.com/api

    # Test admin service
    curl https://example.com/admin

    # Test frontend service
    curl https://example.com/
    ```
4.  **说明和注意事项**:

    a. **SSL 证书**: 要使用 HTTPS，需要有效的 SSL 证书。在 AWS Certificate Manager (ACM) 中创建证书，并在 annotation 中指定 ARN。

    b. **IAM 权限**: AWS Load Balancer Controller 需要适当 IAM 权限来创建和管理 ALB 及相关资源。

    c. **健康检查**: 每个 Service 都必须提供健康检查 endpoint（`/health`）。

    d. **Target Group 设置**: 使用 `target-type: ip` 意味着直接使用 pod IP 作为目标。这提供了对 node 故障的韧性，并支持 Fargate pods。

    e. **Security Groups**: 如有需要，可以将特定 security groups 应用于 ALB:

    ```yaml
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    ```
5.  **其他配置选项**:

    a. **启用 Session Stickiness**:

    ```yaml
    alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
    ```

    b. **启用 Access Logs**:

    ```yaml
    alb.ingress.kubernetes.io/load-balancer-attributes: access_logs.s3.enabled=true,access_logs.s3.bucket=my-alb-logs,access_logs.s3.prefix=ingress-logs
    ```

    c. **基于 IP 的限制**:

    ```yaml
    alb.ingress.kubernetes.io/inbound-cidrs: 192.168.0.0/16,10.0.0.0/8
    ```

    d. **加权路由**:

    ```yaml
    alb.ingress.kubernetes.io/actions.weighted-routing: >
      {"Type":"forward","ForwardConfig":{"TargetGroups":[{"ServiceName":"service-v1","ServicePort":"80","Weight":80},{"ServiceName":"service-v2","ServicePort":"80","Weight":20}]}}
    ```

使用 AWS Load Balancer Controller 和 Ingress 资源，可以在 EKS clusters 中实现复杂路由规则，并利用各种 ALB 功能来提高应用可用性、可扩展性和安全性。

</details>

## 高级题

### 10. 说明在 Amazon EKS cluster 中实现 Service Mesh（例如 Istio、AWS App Mesh）时的关键注意事项和网络架构变化。同时说明 Service Mesh 如何与 EKS 的默认网络模型集成。

<details>

<summary>显示答案</summary>

**答案:** 以下说明在 Amazon EKS cluster 中实现 Service Mesh（例如 Istio、AWS App Mesh）时的关键注意事项和网络架构变化，以及 Service Mesh 如何与 EKS 的默认网络模型集成:

### 1. Service Mesh 概述和关键组件

**什么是 Service Mesh？** Service Mesh 是一个基础设施层，用于管理微服务之间的通信，提供 service discovery、流量管理、安全性和可观测性等功能。

**关键组件:**

1. **Data Plane**:
   * Sidecar proxies（通常是 Envoy）会注入到每个 pod 中。
   * 拦截并处理所有入站和出站流量。
2. **Control Plane**:
   * 管理策略和配置。
   * 配置 data plane proxies。
   * 提供 service discovery 和路由信息。

### 2. EKS 网络架构变化

**默认 EKS 网络模型:**

* 使用 Amazon VPC CNI 为 pods 分配 VPC IP 地址。
* Pods 在 VPC 内直接通信。
* Kubernetes Service 资源提供 service discovery 和 load balancing。

**引入 Service Mesh 后的变化:**

1.  **流量路径变化**:

    ```
    Default EKS: Client -> Service -> Target Pod
    Service Mesh: Client -> Client Sidecar -> Service -> Target Sidecar -> Target Pod
    ```
2. **网络拓扑**:
   * Sidecar containers 会添加到每个 pod。
   * 应用和 sidecar 通过 pod 内本地网络通信。
   * Sidecar 到 sidecar 的通信仍使用 VPC CNI。
3. **端口分配**:
   * Sidecar proxies 使用额外端口（管理、metrics、健康检查等）。
   * 端口重定向发生在 pod 内部。

### 3. 主要 Service Mesh 选项比较

#### Istio

**架构集成:**

```yaml
# Istio sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        sidecar.istio.io/inject: "true"  # Automatic sidecar injection
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**网络功能:**

* 高级流量管理（加权路由、canary deployments）
* Circuit breakers 和 fault injection
* 通过 mTLS 实现 service-to-service 加密
* 细粒度访问控制

**EKS 集成注意事项:**

* 资源要求高（尤其是 control plane）
* 与 Fargate 的兼容性有限
* 设置和管理复杂

#### AWS App Mesh

**架构集成:**

```yaml
# App Mesh sidecar injection example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-app
  labels:
    app: example
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example
  template:
    metadata:
      labels:
        app: example
      annotations:
        appmesh.k8s.aws/mesh: my-mesh  # App Mesh mesh name
        appmesh.k8s.aws/virtualNode: example-vn  # Virtual node name
    spec:
      containers:
      - name: example
        image: example:latest
        ports:
        - containerPort: 8080
```

**网络功能:**

* 与 AWS services 无缝集成
* 支持跨账户和 hybrid mesh
* 与 AWS X-Ray 集成
* 设置相对简单

**EKS 集成注意事项:**

* 与 AWS services 集成优秀
* 兼容 Fargate
* 某些高级功能可能受限

### 4. 网络注意事项

#### 性能影响

1. **延迟**:
   * 由于通过 sidecar proxies 进行额外跳转，延迟略有增加（通常 <10ms）
   *   优化技术:

       ```yaml
       # Istio example: Proxy resource optimization
       apiVersion: v1
       kind: ConfigMap
       metadata:
         name: istio-sidecar-injector
         namespace: istio-system
       data:
         values: |-
           pilot:
             resources:
               requests:
                 cpu: 500m
                 memory: 2048Mi
       ```
2. **资源使用量**:
   * 每个 pod 额外 CPU 和 memory 开销（通常 10-15%）
   * 可能降低 node 密度

#### Network Policy 集成

1. **与 Kubernetes NetworkPolicy 的关系**:
   * Service Mesh 提供 L7 策略，而 NetworkPolicy 提供 L3/L4 策略。
   * 两种策略类型可以一起使用，以实现纵深防御。
2.  **策略示例**:

    ```yaml
    # Istio authentication policy
    apiVersion: security.istio.io/v1beta1
    kind: PeerAuthentication
    metadata:
      name: default
      namespace: istio-system
    spec:
      mtls:
        mode: STRICT
    ---
    # Kubernetes NetworkPolicy
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-same-namespace
    spec:
      podSelector: {}
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: default
    ```

### 5. Service Mesh 实施步骤

#### 1. 验证前提条件

* 检查 cluster 版本兼容性
* 评估资源需求
* 审查网络模型

#### 2. 安装 Control Plane

**Istio 示例:**

```bash
istioctl install --set profile=default
```

**App Mesh 示例:**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace
```

#### 3. 配置 Sidecar Injection

**自动注入:**

```yaml
# Add label to namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  labels:
    istio-injection: enabled  # Istio
    appmesh.k8s.aws/sidecarInjectorWebhook: enabled  # App Mesh
```

#### 4. 定义 Service Mesh 资源

**Istio Virtual Service 和 Destination Rule:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**App Mesh Virtual Service 和 Virtual Router:**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualService
metadata:
  name: reviews
  namespace: my-app
spec:
  awsName: reviews.my-app.svc.cluster.local
  provider:
    virtualRouter:
      virtualRouterRef:
        name: reviews-router
---
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: reviews-router
  namespace: my-app
spec:
  listeners:
    - portMapping:
        port: 9080
        protocol: http
  routes:
    - name: reviews-route
      httpRoute:
        match:
          prefix: /
        action:
          weightedTargets:
            - virtualNodeRef:
                name: reviews-v1
              weight: 90
            - virtualNodeRef:
                name: reviews-v2
              weight: 10
```

### 6. 监控和可观测性

#### Metrics 收集

**Prometheus 集成:**

```yaml
# Istio Prometheus configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  addonComponents:
    prometheus:
      enabled: true
```

#### Distributed Tracing

**X-Ray 集成 (App Mesh):**

```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: Mesh
metadata:
  name: my-mesh
spec:
  serviceDiscovery:
    ipPreference: IPv4_PREFERRED
  egressFilter:
    type: ALLOW_ALL
  tracing:
    awsXRay:
      logLevel: INFO
```

### 7. Service Mesh 采用最佳实践

1. **渐进式采用**:
   * 从非业务关键工作负载开始
   * 分阶段扩展
2. **资源规划**:
   * 考虑增加 node 大小和数量
   * 为 control plane 使用专用 node groups
3. **网络优化**:
   * 避免不必要的 sidecar injection
   * 配置适当的 timeouts 和 retry policies
4. **安全增强**:
   * 渐进式采用 mTLS
   * 应用最小权限原则
5. **监控策略**:
   * 比较采用 Service Mesh 前后的性能
   * 配置关键 metrics dashboards

### 8. EKS 特定注意事项

1. **Fargate 兼容性**:
   * Istio: 支持有限（某些功能不可用）
   * App Mesh: 完全支持
2. **AWS Load Balancer Controller 集成**:
   *   Ingress gateway 和 ALB 集成:

       ```yaml
       apiVersion: networking.k8s.io/v1
       kind: Ingress
       metadata:
         annotations:
           kubernetes.io/ingress.class: alb
           alb.ingress.kubernetes.io/scheme: internet-facing
           alb.ingress.kubernetes.io/target-type: ip
       ```
3. **IAM Roles 和权限**:
   * App Mesh controller 所需 IAM 权限:
     * appmesh:\*
     * servicediscovery:\*
     * cloudmap:\*
4. **VPC CNI 设置**:
   * 由于 Service Mesh，需要考虑额外 ENI 和 IP 地址需求
   *   建议启用 prefix delegation:

       ```bash
       kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
       ```

### 9. Service Mesh 选择指南

| 因素                  | Istio                   | AWS App Mesh             |
| --------------------- | ----------------------- | ------------------------ |
| 功能集                | 非常全面                | 专注于核心功能           |
| AWS 集成              | 第三方集成              | 原生集成                 |
| 复杂性                | 高                      | 中                       |
| 资源要求              | 高                      | 中                       |
| Fargate 支持          | 有限                    | 完全支持                 |
| 社区                  | 非常活跃                | 正在增长                 |
| Hybrid/Multi-cloud    | 支持强                  | 以 AWS 为中心            |

Service Mesh 会给 EKS clusters 的网络架构带来显著变化，但也为管理微服务架构的复杂性提供强大工具。与默认 EKS 网络模型的集成通过 sidecar pattern 完成，可在不更改现有应用代码的情况下添加高级网络功能。采用 Service Mesh 时，应仔细考虑性能影响、运维复杂性和资源需求，并建议采用渐进式方法。

</details>

### 11. Kubernetes Gateway API 中用于 L7 load balancing (ALB) 的路由资源是什么？

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>显示答案</summary>

**答案: B. HTTPRoute**

**解析:** 在 Kubernetes Gateway API 中，HTTPRoute 资源用于 L7 load balancing。HTTPRoute 定义将 HTTP/HTTPS 流量路由到 Service 的规则，并且与 AWS Load Balancer Controller 一起使用时，会通过 ALB 分发流量。

**Gateway API 资源层级:**

1. **GatewayClass**: 定义 load balancer 类型（例如 `amazon-alb`、`amazon-nlb`）
2. **Gateway**: 实际 load balancer instance（listener ports、TLS settings 等）
3. **HTTPRoute**: L7 路由规则（host、path、基于 header 的路由）
4. **TCPRoute**: L4 路由规则（TCP 流量）

**HTTPRoute 主要特性:**

* 基于 path 和 host 的路由
* 原生基于权重的流量拆分
* Header 和 query parameter 匹配
* 路由到多个 backend services

其他选项的问题:

* **A. IngressRoute**: 这不是标准 Gateway API 资源。
* **C. VirtualService**: 这是 Istio service mesh 中的资源。
* **D. ServiceRoute**: 此资源不存在。

</details>

### 12. 在 AWS Load Balancer Controller 中启用 Gateway API 需要什么 feature gate flag？

A. `--enable-gateway-api` B. `--feature-gates=EnableGatewayAPI=true` C. `--gateway-api-enabled=true` D. `--enable-feature=gateway-api`

<details>

<summary>显示答案</summary>

**答案: B. `--feature-gates=EnableGatewayAPI=true`**

**解析:** 要在 AWS Load Balancer Controller 中启用 Gateway API，必须在部署 controller 时添加 `--feature-gates=EnableGatewayAPI=true` flag。此 feature gate 使 controller 能够 watch 和处理 Gateway API 资源（GatewayClass、Gateway、HTTPRoute、TCPRoute 等）。

**启用 Gateway API 的完整前提条件:**

1. 安装 AWS Load Balancer Controller v2.13.0 或更高版本
2. 添加 `--feature-gates=EnableGatewayAPI=true` flag
3. 安装 Gateway API Standard CRDs
4. 安装 Experimental CRDs（使用 TCPRoute 等时）
5. 安装 AWS LBC-specific CRDs

其他选项的问题:

* **A, C, D**: 这些 flag 格式不正确，AWS Load Balancer Controller 不使用。

</details>

### 13. Gateway API 中使用什么资源通过 NLB 路由 L4 级别的 TCP 流量？

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>显示答案</summary>

**答案: C. TCPRoute**

**解析:** 在 Gateway API 中，TCPRoute 资源用于路由 L4 级别的 TCP 流量。与 AWS Load Balancer Controller 一起使用时，TCPRoute 会通过 NLB (Network Load Balancer) 将 TCP 流量转发到 backend services。

**TCPRoute 配置示例:**

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: TCPRoute
metadata:
  name: db-route
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Gateway API 路由资源用法:**

| 资源      | 协议       | AWS LB 类型 |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

其他选项的问题:

* **A. HTTPRoute**: 用于通过 ALB 处理 HTTP/HTTPS L7 流量。
* **B. TLSRoute**: 用于 TLS 流量路由，但 TCPRoute 更适合 TCP 级别路由。
* **D. GRPCRoute**: 专门用于 gRPC 协议的路由资源。

</details>
