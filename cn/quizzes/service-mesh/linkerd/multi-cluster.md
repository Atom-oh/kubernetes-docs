# Linkerd 多集群测验

本测验用于测试您对 Linkerd 多集群功能的理解。

## 测验问题

### 1. Linkerd 多集群架构的核心概念是什么？

A. Mesh 联邦
B. Service 镜像
C. Cluster 合并
D. 全局负载均衡器

<details>
<summary>显示答案</summary>

**答案：B. Service 镜像**

**说明：**
Linkerd 使用 Service 镜像架构。来自远程 Cluster 的已导出 Service 会在本地 Cluster 中显示为镜像 Service，并且可以像本地 Service 一样访问。

</details>

### 2. 两个 Cluster 之间进行 mTLS 通信必须共享什么？

A. Identity Issuer
B. Trust Anchor
C. Workload 证书
D. Kubernetes Secret

<details>
<summary>显示答案</summary>

**答案：B. Trust Anchor**

**说明：**
为了让两个 Cluster 相互信任，它们必须共享同一个 Trust Anchor（Root CA）。每个 Cluster 可以拥有独立的 Identity Issuer，但它们必须由同一个 Trust Anchor 签名。

</details>

### 3. 使用什么标签将 Service 导出到其他 Cluster？

A. linkerd.io/exported: "true"
B. mirror.linkerd.io/exported: "true"
C. multicluster.linkerd.io/export: "enabled"
D. linkerd.io/multicluster: "export"

<details>
<summary>显示答案</summary>

**答案：B. mirror.linkerd.io/exported: "true"**

**说明：**
向 Service 添加 `mirror.linkerd.io/exported: "true"` 标签后，其他已链接的 Cluster 会为其创建镜像。

</details>

### 4. 镜像 Service 的命名格式是什么？

A. `<service>.<cluster>`
B. `<service>-<cluster>`
C. `<cluster>-<service>`
D. `<service>@<cluster>`

<details>
<summary>显示答案</summary>

**答案：B. `<service>-<cluster>`**

**说明：**
镜像 Service 使用 `<original-service-name>-<original-cluster-name>` 格式创建。示例：west Cluster 中的 web Service 会在 east Cluster 中镜像为 web-west。

</details>

### 5. `linkerd multicluster link` 命令的用途是什么？

A. 在两个 Cluster 之间建立网络连接
B. 在本地注册远程 Cluster 凭证
C. 配置 Service 间流量路由
D. 交换证书

<details>
<summary>显示答案</summary>

**答案：B. 在本地注册远程 Cluster 凭证**

**说明：**
`linkerd multicluster link --cluster-name <name>` 会生成当前 Cluster 的凭证（gateway 地址、Service Account token 等），以便在另一个 Cluster 中注册。

</details>

### 6. 哪个命令可检查多集群 gateway 的状态？

A. `linkerd multicluster status`
B. `linkerd multicluster gateways`
C. `linkerd multicluster check`
D. `kubectl get gateway`

<details>
<summary>显示答案</summary>

**答案：B. `linkerd multicluster gateways`**

**说明：**
`linkerd multicluster gateways` 显示已链接 Cluster 的 gateway 状态。它会显示 ALIVE、NUM_SVC（镜像 Service 的数量）和 LATENCY。

</details>

### 7. EKS 多集群中 gateway 的推荐配置是什么？

A. ClusterIP Service
B. NodePort Service
C. NLB（Network Load Balancer）
D. ALB（Application Load Balancer）

<details>
<summary>显示答案</summary>

**答案：C. NLB（Network Load Balancer）**

**说明：**
建议在 EKS 的多集群 gateway 中使用 NLB。它针对 TCP/TLS 流量进行了优化，并通过 `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation 配置。

</details>

### 8. 使用 TrafficSplit 在本地和远程 Cluster 之间拆分流量时，会使用哪些后端 Service？

A. 本地 Service 和远程 gateway
B. 本地 Service 和镜像 Service
C. 仅本地 Service
D. 直接引用远程 Service

<details>
<summary>显示答案</summary>

**答案：B. 本地 Service 和镜像 Service**

**说明：**
TrafficSplit 后端指定本地 Service（例如 web）和镜像 Service（例如 web-west）。发送到镜像 Service 的流量会自动路由到远程 Cluster 的 gateway。

</details>

### 9. 在多集群环境中，以下哪项不是镜像 controller 的职责？

A. 监视远程 Service
B. 创建/更新镜像 Service
C. 签发证书
D. 同步 endpoint

<details>
<summary>显示答案</summary>

**答案：C. 签发证书**

**说明：**
Service mirror controller 会监视远程 Cluster 中已导出的 Service，在本地创建/更新镜像 Service，并同步 endpoint。证书签发是 Identity Controller 的职责。

</details>

### 10. 哪种 AWS Service 用于两个 EKS Cluster 之间的私有连接？

A. 仅 Direct Connect
B. VPC Peering 或 Transit Gateway
C. 仅 Route 53
D. CloudFront

<details>
<summary>显示答案</summary>

**答案：B. VPC Peering 或 Transit Gateway**

**说明：**
要在 EKS Cluster 之间实现私有连接，请使用 VPC Peering（两个 VPC 之间的直接连接）或 Transit Gateway（hub-and-spoke 模型）。使用内部 NLB 配置 gateway。

</details>

### 11. 如何在多集群环境中仅允许访问特定远程 Service？

A. NetworkPolicy
B. 带有 SPIFFE ID 的 ServerAuthorization
C. AWS Security Group
D. Kubernetes RBAC

<details>
<summary>显示答案</summary>

**答案：B. 带有 SPIFFE ID 的 ServerAuthorization**

**说明：**
通过在 ServerAuthorization 的 meshTLS.identities 中指定远程 Cluster 的特定 SPIFFE ID 来控制访问。示例：`spiffe://root.linkerd.cluster.local/ns/production/sa/api-gateway`

</details>

### 12. `linkerd multicluster check` 命令不会验证什么？

A. Link resource 状态
B. Gateway 连通性
C. 应用程序业务逻辑
D. Service mirror controller 状态

<details>
<summary>显示答案</summary>

**答案：C. 应用程序业务逻辑**

**说明：**
`linkerd multicluster check` 会验证多集群基础设施状态，包括 Link resource、gateway、Service mirror controller 和证书。它不会验证应用程序逻辑。

</details>
