# AWS 集成

本文介绍如何在 Amazon EKS 环境中将 Istio 与 AWS 服务集成。

## 目录

本文于 2026 年 9 月 11 日审核，适用于由 Linux EC2 实例提供支持的 EKS 节点以及 AWS Load Balancer Controller。下文的 NLB 透传、ALB 终止 TLS 和 NLB 终止 TLS 是互为替代的设计；不要同时部署彼此重叠的 Service 和 Gateway 资源。网关 Pod 标签和目标端口必须与[安装指南](01-installation.md)中的安装配置一致。Service 变更应合并到实际负责管理配置的 Helm 或 istioctl 配置中。EKS Auto Mode 使用自己的负载均衡集成和受支持的注解；Fargate 无法运行 Istio CNI 或 ztunnel。

1. [AWS 负载均衡器集成](04-aws-integration.md#aws-load-balancer-integration)
2. [Istio 与其他方案对比](04-aws-integration.md#istio-vs-other-solutions-comparison)
3. [EKS 专属优化](04-aws-integration.md#eks-specific-optimization)
4. [最佳实践](04-aws-integration.md#best-practices)

## AWS 负载均衡器集成 {#aws-load-balancer-integration}

Istio Ingress Gateway 可以接入 AWS 负载均衡器，以处理外部流量。

### Network Load Balancer (NLB) 集成

NLB 是第 4 层（TCP/UDP）负载均衡器，适用于需要高性能和低延迟的场景。

#### NLB 架构

![客户端的 HTTPS 请求到达 AWS Network Load Balancer；NLB 将 TCP 443 流量转发到 EKS 集群中的两个 Istio Ingress Gateway Envoy Pod，每个网关再将 HTTP/HTTPS 流量路由至 Service A 和 Service B 的 Pod。](../../.gitbook/assets/en-service-mesh-istio-04-aws-integration-0.png)

[🔍 查看交互式架构图](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-04-aws-integration-0.html)

#### NLB 配置

**1. 安装 AWS Load Balancer Controller**

```bash
# Create IAM policy
curl -fsSL -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

# Associate the cluster OIDC provider once before creating IRSA
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# IRSA setup
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn="arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy" \
  --override-existing-serviceaccounts \
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --version 3.5.0 \
  --set clusterName=my-cluster \
  --set region=us-west-2 \
  --set vpcId="<VPC_ID>" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**2. 为 NLB 配置 Istio Ingress Gateway**

```yaml
# istio-ingress-nlb.yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # NLB configuration
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"

    # TCP passthrough: TLS terminates at Istio; no ACM TLS listener here

    # Health check configuration
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: "http"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "15021"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/healthz/ready"

    # Additional configuration
    service.beta.kubernetes.io/aws-load-balancer-attributes: "load_balancing.cross_zone.enabled=true"
spec:
  type: LoadBalancer
  selector:
    app: istio-ingressgateway
    istio: ingressgateway
  ports:
  - name: http2
    port: 80
    protocol: TCP
    targetPort: 8080
  - name: https
    port: 443
    protocol: TCP
    targetPort: 8443
```

**3. 配置 Gateway 资源**

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: my-tls-secret
    hosts:
    - "myapp.example.com"
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true
```

#### NLB 的优势

* **高性能**：每秒可处理数百万个请求
* **低延迟**：运行于第 4 层，响应迅速
* **静态 IP**：可分配 Elastic IP
* **协议支持**：TCP、UDP、TLS
* **容量规划**：测量连接数和流量字节数，并与所在区域的费率对照

#### NLB 的适用场景

* WebSocket、gRPC 等长连接
* 每秒需要处理数百万个请求
* 需要静态 IP
* 需要在 Istio 处终止 TLS

### Application Load Balancer (ALB) 集成

ALB 是第 7 层（HTTP/HTTPS）负载均衡器，适用于需要高级路由功能的场景。

#### ALB 架构

在此示例中，客户端 HTTPS 流量到达 ALB；ALB 使用 ACM 终止 TLS，再将 HTTP/1.1 流量转发到 Istio 网关，随后由 Envoy 将请求路由至应用。

#### ALB 配置

**1. 使用 Ingress 资源创建 ALB**

```yaml
# istio-ingress-alb.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: istio-ingress
  namespace: istio-system
  annotations:
    # ALB configuration
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'

    # ACM certificate
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/cert-id

    # Health check
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-port: '15021'
    alb.ingress.kubernetes.io/healthcheck-path: /healthz/ready
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/success-codes: '200'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '2'

    # Additional configuration
    alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=60
    alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30
spec:
  ingressClassName: alb
  rules:
  - host: "myapp.example.com"
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
```

在此 ALB 设计中，应将网关 Service 配置为 ClusterIP，这样它就不会另外创建 NLB。ALB 终止 TLS，默认转发 HTTP/1.1；网关应使用此 HTTP 配置，不要添加 HTTPS 重定向。为应用路由创建一个绑定到 `my-alb-gateway` 的 VirtualService。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-alb-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
```

**2. 按路径路由**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: istio-ingress-path-based
  namespace: istio-system
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: "api.example.com"
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
  - host: "admin.example.com"
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: istio-ingressgateway
            port:
              number: 80
```

#### ALB 的优势

* **高级路由**：可基于路径、Header 和查询字符串进行路由
* **WAF 集成**：通过 AWS WAF 加强安全防护
* **身份验证集成**：可集成 Cognito、OIDC
* **ACM 集成**：自动管理证书
* **针对容器优化**：针对 ECS、EKS 优化

#### ALB 的适用场景

* 仅处理 HTTP/HTTPS 流量
* 需要基于路径的路由
* 需要 WAF 安全防护
* 需要通过单个负载均衡器处理多个域名

### NLB 与 ALB 对比

| 属性 | NLB | ALB |
| --- | --- | --- |
| **OSI 层** | 第 4 层（TCP/UDP） | 第 7 层（HTTP/HTTPS） |
| **容量** | 取决于流量和容量设置 | 取决于流量和容量设置 |
| **延迟** | 极低 | 低 |
| **静态 IP** | 支持（Elastic IP） | 不支持 |
| **TLS 终止** | TCP 透传，或由 NLB 的 TLS 侦听器终止 | 可在 ALB 处终止 |
| **路由** | 基于 IP/端口 | 基于路径、Host、Header |
| **WAF 集成** | 不支持 | 支持 |
| **成本** | 按 NLCU 用量和区域费率计费 | 按 LCU 用量和区域费率计费 |
| **WebSocket** | 原生支持 | 支持 |
| **gRPC** | 原生支持 | 需要 HTTP/2 |
| **推荐用途** | 高性能、WebSocket、gRPC | HTTP 路由、WAF、身份验证 |

## Istio 与其他方案对比 {#istio-vs-other-solutions-comparison}

### Istio 与 VPC Lattice

VPC Lattice 是 AWS 托管的应用网络服务。

#### 架构对比

![并排对比 Istio 与 AWS VPC Lattice：Istio 控制平面向 Envoy sidecar 下发配置，sidecar 通过 mTLS 直接组成网格；VPC Lattice 则通过托管服务网络，在不带 sidecar 的应用 Pod 之间路由普通 HTTP 流量。](../../.gitbook/assets/en-service-mesh-istio-04-aws-integration-2.png)

[🔍 查看交互式架构图](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-04-aws-integration-2.html)

#### 功能对比

| 属性 | Istio | VPC Lattice |
| --- | --- | --- |
| **管理方式** | 自行管理 | AWS 管理（全托管） |
| **Sidecar** | Sidecar 模式下使用 sidecar；ambient 模式下不使用 | 不需要 |
| **资源开销** | 取决于 sidecar 或 ambient 拓扑 | 低（无 sidecar） |
| **复杂度** | 高 | 低 |
| **学习曲线** | 陡峭 | 平缓 |
| **流量管理** | 功能高级、控制粒度细 | 基础功能，足以满足常见需求 |
| **mTLS** | 管理工作负载身份和证书 | 应用自行管理，TLS 透传 |
| **可观测性** | 指标和追踪丰富 | 基础指标 |
| **故障注入** | 支持 | 不支持 |
| **断路器** | 控制粒度细 | 没有等效的 Istio 策略 API；服务配额是另一类机制 |
| **速率限制** | 本地和全局 | 没有等效的 Istio 策略 API；服务配额是另一类机制 |
| **多集群** | 支持完善 | 跨 VPC 连接 |
| **跨账户** | 配置复杂 | 简单（原生支持） |
| **成本** | 计算资源成本（EC2） | 服务使用费 |
| **供应商锁定** | 无（开源） | 依赖 AWS |
| **仅限 Kubernetes** | 否（支持虚拟机） | 否（也支持 EC2、Lambda 等） |

VPC Lattice 的 TLS 透传会保留应用自身的 TLS/mTLS，但不能在该侦听器上强制执行基于 IAM 身份的身份验证，也不能使用 Lambda 目标。HTTPS 侦听器和 TLS 透传具备不同的安全能力。

#### 何时选择 Istio

**以下情况适合选择 Istio：**

1. **需要细粒度的流量控制**
   * 金丝雀发布、A/B 测试、流量镜像
   * 复杂路由规则（例如基于 Header、Cookie）
   * 用于混沌工程的故障注入
2. **安全要求较高**
   * 服务间自动启用 mTLS 加密
   * 细粒度授权策略
   * JWT 验证、RBAC
3. **需要高级可观测性**
   * 详细指标（延迟 P50/P95/P99）
   * 分布式追踪（Jaeger、Zipkin）
   * 服务拓扑可视化（Kiali）
4. **需要多集群网格**
   * 多个 EKS 集群之间通信
   * 跨集群故障转移
   * 全局负载均衡
5. **需要避免依赖单一供应商**
   * 可迁移到其他云或本地环境
   * 使用 Kubernetes 标准

**示例：Istio 的高级流量管理**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  # Header-based routing
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # Canary deployment (10%)
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
      weight: 10
    - destination:
        host: reviews
        subset: v2
      weight: 90
  # Traffic Mirroring
  - route:
    - destination:
        host: reviews
        subset: v2
    mirror:
      host: reviews
      subset: v3
    mirrorPercentage:
      value: 100
```

#### 何时选择 VPC Lattice

**以下情况适合选择 VPC Lattice：**

1. **只需简单的服务连接**
   * 只需要基础负载均衡和路由
   * 快速实施很重要
2. **希望降低运维开销**
   * 倾向于使用 AWS 托管服务
   * 不想承担 sidecar 管理负担
3. **需要跨 VPC 或跨账户通信**
   * 连接位于多个 AWS 账户中的服务
   * 无需 VPC 对等连接即可通信
4. **环境由多种计算平台组成**
   * EKS、EC2、Lambda 混合部署
   * 使用 Kubernetes 以外的计算类型
5. **需要优化成本**
   * 降低 sidecar 资源成本
   * 服务规模较小

#### 同时使用 Istio 与 VPC Lattice

两种方案并不互斥，可以组合使用：

![图示：AWS 账户 1 中的一个 EKS 集群使用 Istio 配置 sidecar 和 mTLS；VPC Lattice 服务网络则跨账户将该集群的流量路由到 AWS 账户 2 中不带 sidecar 的服务和 Lambda 函数。](../../.gitbook/assets/en-service-mesh-istio-04-aws-integration-3.png)

[🔍 查看交互式架构图](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-04-aws-integration-3.html)

**适用场景：**

* **集群内部**：使用 Istio 实现细粒度流量管理和安全控制
* **跨集群或跨账户**：使用 VPC Lattice 建立简单连接
* **混合环境**：使用 VPC Lattice 连接 Istio 集群与 Lambda、EC2

### Istio 与 Cilium（基于 eBPF）

Cilium 是使用 eBPF 实现的 Kubernetes 网络和安全解决方案。

#### 架构对比

| 属性 | Istio | Cilium |
| --- | --- | --- |
| **技术栈** | Envoy Proxy（sidecar） | eBPF（内核层） |
| **主要用途** | Service Mesh | CNI + Service Mesh |
| **网络** | 构建在 Kubernetes CNI 之上 | 自身提供 CNI |
| **性能** | 良好 | 优秀（内核层处理） |
| **资源使用** | 高（sidecar） | 低（内核层处理） |
| **L7 功能** | 强大 | 基础 |
| **可观测性** | 丰富 | Hubble（基础） |
| **学习曲线** | 陡峭 | 陡峭 |
| **成熟度** | 高 | 中等（Service Mesh 功能） |

#### 功能对比

| 功能 | Istio | Cilium |
| --- | --- | --- |
| **网络策略** | Kubernetes + Istio | Kubernetes + Cilium（功能更强） |
| **L7 负载均衡** | 控制粒度很细 | 基础 |
| **mTLS** | 自动提供工作负载间 mTLS | 相互身份验证与 WireGuard/IPsec 加密是彼此独立的功能 |
| **流量管理** | 功能高级 | 基础 |
| **可观测性** | Prometheus、Jaeger、Kiali | Hubble |
| **性能** | 良好 | 优秀 |
| **多集群** | 支持完善 | Cluster Mesh |

#### 如何选择

**选择 Istio：**

* L7 流量管理是核心需求
* 需要强大的服务网格功能
* 需要丰富的可观测性和调试工具

**选择 Cilium：**

* 正在考虑替换 CNI
* 网络安全是主要关注点
* 性能优化很重要
* 希望利用 eBPF 技术

**组合使用：**

* 可以用 Cilium 作为 CNI、用 Istio 作为 Service Mesh
* 但要考虑功能重叠和复杂度增加

## EKS 专属优化 {#eks-specific-optimization}

对于使用 VPC CNI Pod ENI trunking 和 SecurityGroupPolicy 的 ambient 工作负载，请查看 [EKS ambient 前置条件](https://istio.io/latest/docs/ambient/install/platform-prerequisites/#amazon-elastic-kubernetes-service-eks)：严格执行 Pod 安全组策略可能会阻断链路本地健康探测。文档列出的选项包括标准 enforcing 模式或 exec 探测；更改 CNI 模式前，应评估其对策略的影响。

### IAM Roles for Service Accounts (IRSA) 集成

对于由 EC2 节点提供支持的集群，EKS Pod Identity 也是一种受支持的 AWS API 凭证方案。它需要 Pod Identity Agent 和兼容的 AWS SDK，且不使用 IRSA 角色注解。IRSA 和 Pod Identity 都不能替代 Istio SPIFFE 工作负载身份。

配置 IRSA，使 Istio 工作负载能够安全访问 AWS 服务。

#### IRSA 配置

```bash
# 1. Create OIDC provider
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. Create IAM policy
cat <<EOF > app-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-bucket",
                "arn:aws:s3:::my-bucket/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name MyAppS3Policy \
    --policy-document file://app-policy.json

# 3. Link IAM Role to Service Account
eksctl create iamserviceaccount \
    --cluster my-cluster \
    --namespace default \
    --name my-app-sa \
    --role-name my-app-role \
    --attach-policy-arn "arn:aws:iam::<ACCOUNT_ID>:policy/MyAppS3Policy" \
    --approve
```

#### 在 Istio 中使用 IRSA

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<ACCOUNT_ID>:role/my-app-role
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-sa  # Using IRSA
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: AWS_REGION
          value: us-west-2
```

### AWS Certificate Manager (ACM) 集成

本节介绍如何在 Istio Gateway 中使用 ACM 证书。

#### 在 NLB 处终止 TLS

```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/cert-id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"
spec:
  type: LoadBalancer
  selector:
    istio: ingressgateway
  ports:
  - name: https
    port: 443
    targetPort: 8080
```

这是另一种独立方案：ACM 在 NLB 处终止 TLS，目标端收到明文 HTTP。将 TLS Gateway 替换为此 HTTP 侦听器，并在 Service 端口 443 上提供服务；后端不要使用 SIMPLE TLS，也不要配置 HTTPS 重定向。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: nlb-terminated-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: http-after-nlb
      protocol: HTTP
    hosts:
    - "myapp.example.com"
```

#### 在 Istio 处终止 TLS（ACM Private CA）

```bash
# Generate a private key and CSR locally; clients must trust this private CA
openssl req -new -newkey rsa:2048 -nodes \
  -keyout private-key.pem -out csr.pem \
  -subj '/CN=myapp.example.com' -addext 'subjectAltName=DNS:myapp.example.com'

CA_ARN='arn:aws:acm-pca:region:account:certificate-authority/ca-id'
CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$CA_ARN" \
  --csr fileb://csr.pem \
  --signing-algorithm SHA256WITHRSA \
  --validity Value=365,Type=DAYS \
  --query CertificateArn --output text)
aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$CA_ARN" --certificate-arn "$CERT_ARN"
aws acm-pca get-certificate \
  --certificate-authority-arn "$CA_ARN" --certificate-arn "$CERT_ARN" \
  --output json > issued-certificate.json
jq -r '.Certificate + "\n" + .CertificateChain' issued-certificate.json > certificate-chain.pem
kubectl create secret tls my-tls-secret \
  --cert=certificate-chain.pem --key=private-key.pem -n istio-system
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: my-tls-secret  # ACM certificate
    hosts:
    - "myapp.example.com"
```

仅签发证书并不会安装或续订 Secret。应自动化证书续订和 Secret 更新；不能直接将 ACM ARN 用作 Istio 的 `credentialName`。

### CloudWatch Container Insights 集成

将 Istio 指标发送到 CloudWatch，以实现统一监控。

#### CloudWatch Agent 配置

```bash
# For EC2-backed EKS; OIDC association is required for this IRSA path
kubectl create namespace amazon-cloudwatch --dry-run=client -o yaml | kubectl apply -f -
eksctl create iamserviceaccount \
  --cluster my-cluster --namespace amazon-cloudwatch --name cwagent-prometheus \
  --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy --approve
curl -fsSL -o prometheus-eks.yaml \
  https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/service/cwagent-prometheus/prometheus-eks.yaml
# Review/pin this manifest; merge the Istio scrape jobs and EMF declarations below before applying
kubectl apply -f prometheus-eks.yaml
kubectl rollout status deployment/cwagent-prometheus -n amazon-cloudwatch
```

仅创建命名空间和 ServiceAccount 并不会部署 agent。官方清单包含 Deployment、RBAC 和挂载的 ConfigMap。如果部署工具会替换 ServiceAccount，请保留 IRSA 注解。对于已安装的 agent，应修改其所属配置，不要再部署第二个采集器。

#### Prometheus 指标抓取

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: amazon-cloudwatch
data:
  prometheus.yaml: |
    global:
      scrape_interval: 1m
      scrape_timeout: 10s

    scrape_configs:
    # Istio Control Plane metrics
    - job_name: 'istiod'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app, __meta_kubernetes_pod_container_port_name]
        action: keep
        regex: istiod;http-monitoring

    # Envoy sidecar metrics
    - job_name: 'envoy-stats'
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_container_port_name]
        action: keep
        regex: '.*-envoy-prom'
```

将声明合并到 `prometheus-cwagentconfig` 中的 `logs.metrics_collected.prometheus.emf_processor.metric_declaration` 下；仅创建抓取用的 ConfigMap 并不会将自定义 CloudWatch 指标发布出去。保留清单中的 `prometheus_config_path` 和其他设置，然后重新部署或重启 agent。示例：

```json
{
  "source_labels": ["job"],
  "label_matcher": "^envoy-stats$",
  "dimensions": [["ClusterName", "job"]],
  "metric_selectors": ["^istio_requests_total$", "^istio_tcp_received_bytes_total$"]
}
```

#### CloudWatch Logs Insights 查询

请分别运行以下查询。查询依赖由日志采集器写入的代理日志；Prometheus 采集不会收集访问日志。延迟查询假定日志为结构化 JSON，且包含数值类型的 `request_duration_ms` 字段（可通过 Envoy `%DURATION%` 配置该字段，或先按实际日志格式解析）。

```text
# Istio error log analysis
fields @timestamp, @message
| filter @logStream like /istio-proxy/
| filter @message like /error/
| sort @timestamp desc
| limit 100

```

```text
# Request latency analysis
fields @timestamp, request_duration_ms
| filter @logStream like /istio-proxy/
| stats avg(request_duration_ms), max(request_duration_ms), pct(request_duration_ms, 95) by bin(5m)
```

### EKS 优化设置

#### 1. 优化 Pod 资源

```yaml
# Envoy sidecar resource optimization
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      concurrency: 2  # Envoy worker threads, not a connection-pool limit
      proxyMetadata:
        # EKS optimization
        ISTIO_META_DNS_CAPTURE: "true"
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 2000m
            memory: 1024Mi
```

#### 2. Cluster Autoscaler 注意事项

HPA 用于扩缩副本数，需要 Metrics Server 和资源请求；Cluster Autoscaler/Karpenter 用于扩缩节点。应配置现有的、由 chart 管理的 HPA，不要再创建一个与之竞争的 HPA。

```yaml
# Istio Gateway Autoscaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: istio-ingressgateway
  namespace: istio-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: istio-ingressgateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 3. Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: istio-ingressgateway
  namespace: istio-system
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: istio-ingressgateway
```

## 最佳实践 {#best-practices}

### 1. 如何选择负载均衡器

**使用 NLB：**

* gRPC、WebSocket 等长连接
* 每秒需要处理数百万个请求
* 需要静态 IP
* 在 Istio 处终止 TLS

**使用 ALB：**

* 仅处理 HTTP/HTTPS
* 需要按路径路由
* 需要 WAF 安全防护
* 需要集成 Cognito 身份验证

### 2. TLS 终止位置

**在负载均衡器处终止：**

* ACM 证书自动续订
* 管理简单
* 降低 Istio 的负载

**在 Istio 处终止：**

* 需要端到端加密
* 需要细粒度 TLS 策略控制
* 使用 mTLS

### 3. 优化成本

* **Spot Instances**：用于 Istio Gateway 工作负载
* **Graviton Instances**：使用基于 ARM 的实例以节省成本
* **资源限制**：为 sidecar 设置合适的资源限制
* **Ambient Mode**：考虑使用 ambient 模式以消除 sidecar 开销

### 4. 安全

* **IRSA**：使用 IAM 角色访问 AWS 服务
* **安全组**：遵循最小权限原则
* **mTLS**：启用服务间加密
* **网络策略**：使用 Amazon VPC CNI、Cilium 或 Calico 启用策略执行；同时确认平台支持情况

### 5. 监控

* **CloudWatch**：统一收集日志和指标
* **X-Ray**：分布式追踪
* **Prometheus + Grafana**：详细指标
* **Kiali**：服务网格可视化

## 后续步骤

完成 AWS 集成后，可参阅以下文档：

1. [**流量管理**](traffic-management/README.md)：高级流量管理功能
2. [**安全**](security/README.md)：mTLS、身份验证和授权
3. [**可观测性**](observability/README.md)：指标、日志和追踪采集

## 参考资料

* [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
* [EKS 最佳实践 - 网络](https://docs.aws.amazon.com/eks/latest/best-practices/networking.html)
* [VPC Lattice 文档](https://docs.aws.amazon.com/vpc-lattice/)
* [Cilium 文档](https://docs.cilium.io/)
* [AWS Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)

* [注解](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
* [Ingress 注解](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
* [v3.5.0](https://github.com/kubernetes-sigs/aws-load-balancer-controller/releases/tag/v3.5.0)
* [AWS Load Balancer Controller chart 元数据](https://raw.githubusercontent.com/aws/eks-charts/master/stable/aws-load-balancer-controller/Chart.yaml)
* [使用 Helm 安装 AWS Load Balancer Controller - Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html)
* [VPC Lattice 服务的 TLS 侦听器 - Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html)
* [issue-certificate 命令](https://docs.aws.amazon.com/cli/latest/reference/acm-pca/issue-certificate.html)
* [get-certificate 命令](https://docs.aws.amazon.com/cli/latest/reference/acm-pca/get-certificate.html)
* [Container Insights Prometheus 配置](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights-Prometheus-Setup.html)
* [抓取其他 Prometheus 源并导入其指标 - Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights-Prometheus-Setup-configure.html)
* [了解 EKS Pod Identity 如何向 Pod 授予 AWS 服务访问权限 - Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
* [使用 Kubernetes 网络策略限制 Pod 流量 - Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [DNS 代理](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
