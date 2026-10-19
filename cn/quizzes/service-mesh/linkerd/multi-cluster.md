# Linkerd 多集群测验

基于[多集群指南](../../../service-mesh/linkerd/06-multi-cluster.md)，于 2026 年 9 月 11 日审核。

### 1. Linkerd 多集群的核心机制是什么？

- A. 合并 Kubernetes 集群
- B. Service 镜像
- C. 自动复制每次应用写入
- D. 强制使用全局负载均衡器

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：源 controller 通过目标 Kubernetes API 监视选定的 Service 信息，并创建本地发现资源。这不是请求影子流量或数据复制。分层、扁平和联邦模式有不同的网络要求。

</details>

### 2. Mesh mTLS 需要各集群信任什么？

- A. 同一个 issuer 私钥
- B. 相关的公有信任锚 bundle 和 issuer 证书链
- C. 一个共享的工作负载私钥
- D. 所有集群中完全相同的 Kubernetes Secret 对象

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：共用一个根证书是最简单的配置；合适的共享 bundle 也可以包含多个根证书。各集群的 issuer 可以使用不同的密钥。现有 proxy 需要协调信任 bundle 的迁移；还要区分公有根证书和签名密钥。

</details>

### 3. 分层 gateway 模式镜像 Service 的默认导出标签是什么？

- A. `linkerd.io/exported: "true"`
- B. `mirror.linkerd.io/exported: "true"`
- C. `multicluster.linkerd.io/export: "enabled"`
- D. `linkerd.io/multicluster: "export"`

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：默认的分层 selector 会匹配 `mirror.linkerd.io/exported=true`。扁平模式使用 `remote-discovery`，联邦成员关系使用 `mirror.linkerd.io/federated=member`。标签会影响匹配的 Link/RBAC 发现逻辑，但不是访问控制边界。

</details>

### 4. 镜像 Service 通常叫什么名字？

- A. `<service>.<cluster>`
- B. `<service>-<Link cluster name>`
- C. `<cluster>-<service>`
- D. `<service>@<cluster>`

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：Link 名为 `west` 时，从该集群导入的 web Service 通常会在对应命名空间中命名为 `web-west`。Link 的集群名称是一个别名，不一定与 EKS 物理集群名称相同。默认不会自动创建命名空间。

</details>

### 5. 当前的 `link-gen` 命令会生成什么？

- A. VPC 路由和 gateway 负载均衡器
- B. 为源集群生成一个 Link 和两个凭证 Secret
- C. 复制的应用数据库
- D. 为每个 Pod 生成新的工作负载证书

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：使用 `west` context 生成并应用到 `east` 后，East 才能发现 West。chart 的 `controllers` 列表用于指定源 mirror controller。旧的 `link` 命令已弃用。生成的 kubeconfig 数据属于敏感信息，必须包含可达的 API 端点和可用的 CA 数据。

</details>

### 6. 哪个命令会报告目标 gateway 探测统计信息？

- A. `linkerd multicluster status`
- B. `linkerd multicluster gateways`
- C. `kubectl get gateway`
- D. `linkerd gateway inspect`

<details>
<summary>显示答案</summary>

**答案：B**

**解释：**`gateways` 会报告已配置的目标 gateway 探测结果，并不代表每个应用都健康。该探测由源 mirror controller 执行。仅使用扁平模式的 Link 不需要 gateway；应针对这类连接检查 Link、端点和 Pod 连通性。

</details>

### 7. 指南中的 AWS Load Balancer Controller 示例使用哪种负载均衡器配置？

- A. 终止 mesh TLS 的公有 ALB
- B. 自动跨 Region 可达的任意 ClusterIP
- C. 通过 `service.k8s.aws/nlb` 选择的内部 TCP NLB
- D. 旧版 nlb annotation 自动证明由 IP target 所有

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：此示例假设已配置该 controller、受支持的 annotation 和私有连通性。EKS Auto Mode 使用不同的 class/owner。必须分别检查 gateway 数据流、探测流量和远程 Kubernetes API 路径是否可达。

</details>

### 8. 当前的 HTTPRoute 示例可使用哪些后端在本地和远端之间分配流量？

- A. 本地 Service 和另一个 API Server 中任意远程 Pod 的 IP
- B. 本地 backend Service 和本地导入的镜像 Service
- C. 仅本地 Service
- D. 自动创建的数据库副本集

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：示例通过 apex Service 使用 `web-local` 和 `web-west`。相对权重不是自动备用策略；将权重设为 100/0 并不会在故障时自动切换到权重为零的 backend。SMI/Failover 扩展已弃用；扁平联邦有各自的要求和行为。

</details>

### 9. 哪项不是 mirror controller 的职责？

- A. 监视选定的远程 Service
- B. 创建或更新本地镜像
- C. 签发工作负载证书
- D. 维护符合模式要求的发现/端点信息

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：Identity 负责签发工作负载证书。选定的 mirror controller 仍会为分层 Service 维护旧式 Endpoints；而远程发现模式可以有意移除本地 Endpoints，并依赖目标端发现远程端点。

</details>

### 10. 正确配置时，哪种方式可提供经过路由的私有 VPC 连通性？

- A. 仅使用 Route53
- B. VPC peering 或配置适当路由的 Transit Gateway
- C. 仅使用 CloudFront
- D. EKS 管理接口端点会自动提供扁平 Pod 路由

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：仍需正确配置路由、唯一且可达的地址、DNS 和安全控制。PrivateLink 为选定服务/资源提供访问，与 VPC peering 不同。EKS 接口端点不是集群的 Kubernetes API 端点。

</details>

### 11. 最终 server 如何授权保留的远程工作负载身份？

- A. 将 AWS 账户名称视为隐式 mesh 身份
- B. 在扁平/联邦模式中使用 Linkerd authorization，匹配实际的 DNS 格式身份
- C. 通过任意 gateway 使用过时的 SPIFFE URI 示例
- D. 假设公有导出标签能够验证调用方

<details>
<summary>显示答案</summary>

**答案：B**

**解释**：分层 gateway 到达最终 server 时会丢失原始调用方身份；扁平/联邦路径会保留该身份。多个集群中的 ServiceAccount、命名空间和 trust domain 名称可能相同；该 policy 不会自动证明调用来自 East 集群。

</details>

### 12. 多集群基础设施检查不能证明什么？

- A. Link 配置是否存在可检测到的错误
- B. 已配置的远程访问/探测是否存在可检测到的故障
- C. 应用业务逻辑正确，或区域故障后一定能恢复
- D. mirror 组件配置是否存在可检测到的问题

<details>
<summary>显示答案</summary>

**答案：C**

**解释**：这些检查有助于诊断配置、凭证和基础设施问题，但不能证明数据一致性、安全写入重试、容量或故障转移后的业务行为。请另行验证实际工作负载的结果。

</details>
