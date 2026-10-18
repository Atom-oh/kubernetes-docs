# 基础设施配置测验

> **相关文档**: [基础设施配置](../../ops/01-infrastructure-setup.md)

## 选择题

### 1. 本指南采用哪三个运维层？

- A) Network → Cluster → Platform
- B) Foundation → Workload → Database
- C) VPC → Pod → Container
- D) 所有资源都放在同一个 state 中

<details>
<summary>显示答案</summary>

**答案：A) Network → Cluster → Platform**

00-shared 是独立的引导层。Network 层负责 VPC，Cluster 层负责 EKS，Platform 层负责 CoreDNS、Pod Identity 和团队访问。将 state 分开并不能阻止 VPC 或 DNS 故障影响其他层。

</details>

### 2. 哪项设置可在 Terraform 1.10 或更高版本中启用原生 S3 后端锁定？

- A) use_lockfile = true
- B) 始终创建 DynamoDB 表
- C) 只启用存储桶版本控制
- D) 所有层都使用相同的 key

<details>
<summary>显示答案</summary>

**答案：A) use_lockfile = true**

原生锁定使用 S3 条件写入。对于现有配置和锁机制迁移，DynamoDB 锁定仍可能相关，但启用原生 S3 锁定并不需要 DynamoDB。仅更改锁定机制不会迁移 state 的存储位置。

</details>

### 3. 关于 terraform_remote_state 的安全性，哪项说法正确？

- A) 读取者只能访问 outputs
- B) 访问后端可能暴露整个 state 快照，因此应考虑信任边界
- C) sensitive=true 会撤销 IAM 读取权限
- D) state 中不会包含敏感值

<details>
<summary>显示答案</summary>

**答案：B) 访问后端可能暴露整个 state 快照，因此应考虑信任边界**

该表达式会暴露根模块 outputs，但底层 state 还包含更多信息。跨越信任边界时，应考虑只单独发布必需的值。

</details>

### 4. 关于标准区域级 EKS 集群和内置 Auto Mode 节点池，哪项说法正确？

- A) 控制平面只需一个可用区中的子网
- B) 名为 blue 的标签会把工作节点固定在 AZ-a
- C) EKS 子网至少需要分布在两个不同的可用区；工作节点放置约束另行设计
- D) Cluster=blue 子网标签会固定节点位置

<details>
<summary>显示答案</summary>

**答案：C) EKS 子网至少需要分布在两个不同的可用区；工作节点放置约束另行设计**

内置节点池可以使用多个已配置的可用区。若工作节点单元需要限制在单个可用区，必须通过 NodePool/NodeClass 设计放置约束，并在其他单元预留恢复容量。

</details>

### 5. 如果将 gpu 添加为 compute_config.node_pools 名称，会发生什么？

- A) 创建官方内置 GPU 节点池
- B) gpu 不是内置节点池名称；应配置合适的自定义 NodePool
- C) 现有节点会立即变成 GPU 节点
- D) 所有集群都会变成仅运行 GPU 节点的集群

<details>
<summary>显示答案</summary>

**答案：B) gpu 不是内置节点池名称；应配置合适的自定义 NodePool**

内置名称为 general-purpose 和 system。该输入是名称列表，不是用于定义 GPU 节点池的任意映射。自定义 NodePool 属于本指南的 GitOps 部分。

</details>

### 6. EKS Pod Identity 的用途和要求是什么？

- A) 自动修复 Pod 从 ECR 拉取镜像的问题
- B) 始终需要 OIDC provider
- C) 为受支持的 SDK 调用提供角色凭证，并需要配置关联、信任和节点支持
- D) 关联操作会安装 ServiceAccount 和 ESO

<details>
<summary>显示答案</summary>

**答案：C) 为受支持的 SDK 调用提供角色凭证，并需要配置关联、信任和节点支持**

Auto Mode 包含所需的 agent 功能；普通 EKS 节点可能需要单独安装该 agent。应配置匹配的 namespace/SA，并区分 kubelet 拉取镜像所需的权限与应用程序进行 SDK 调用所需的权限。

</details>

### 7. 按环境和集群颜色隔离 state 时，应如何设置？

- A) 只用不同的 TF_DATA_DIR 就能分隔共用的 S3 key
- B) 选择不同的后端 bucket/key，并使用相应的初始化目录
- C) 更改环境变量就会把 prod state 移到 dev
- D) 禁用 S3 版本控制

<details>
<summary>显示答案</summary>

**答案：B) 选择不同的后端 bucket/key，并使用相应的初始化目录**

后端配置决定实际的 state 存储位置。TF_DATA_DIR 用于隔离初始化元数据、模块和 provider 缓存，不能替代 state key。还应按账户和环境分别隔离引导阶段的本地 state。

</details>

### 8. 本 Auto Mode 示例如何处理 CoreDNS 和 StorageClass？

- A) 两者都会自动创建，无需配置
- B) 纯 Auto Mode 使用节点本地 DNS；混合节点集群需要 CoreDNS Deployment；StorageClass 需单独创建
- C) 始终重复安装 EBS CSI 和 Pod Identity agent
- D) 将 CoreDNS 版本固定为 latest

<details>
<summary>显示答案</summary>

**答案：B) 纯 Auto Mode 使用节点本地 DNS；混合节点集群需要 CoreDNS Deployment；StorageClass 需单独创建**

纯 Auto Mode 将 CoreDNS 用作节点系统服务。混合集群仍使用 CoreDNS Deployment；应检查 Kubernetes 版本与区域的兼容性，并固定该附加组件的版本。Auto Mode 的 StorageClass 使用 ebs.csi.eks.amazonaws.com。

</details>

### 9. 仅创建管理员访问条目是否就足以使用 kubectl？

- A) 它还会授予 IAM DescribeCluster 权限和网络访问
- B) 不足：必须以该主体进行身份验证，并准备 IAM 权限和私有 API 连通性
- C) Terraform 调用者始终会自动成为管理员
- D) 必须在 Platform 层重新创建同一个条目

<details>
<summary>显示答案</summary>

**答案：B) 不足：必须以该主体进行身份验证，并准备 IAM 权限和私有 API 连通性**

本示例关闭了自动授予创建者管理员权限的功能。EKS access policy 管理 Kubernetes 权限，这些权限与 IAM 权限彼此独立。每个主体的访问条目应由一个层负责管理。

</details>

### 10. 哪种冒烟测试失败处理方式正确？

- A) 用 || true 隐藏 Pod 创建错误
- B) 始终删除预先存在的冒烟测试 namespace
- C) 失败时返回非零状态，并且只清理已确认是临时创建的 namespace
- D) 将所有处于 Running 阶段的 Pod 都视为健康

<details>
<summary>显示答案</summary>

**答案：C) 失败时返回非零状态，并且只清理已确认是临时创建的 namespace**

该测试检查工作负载能否调度以及集群 DNS 是否正常，不覆盖外部负载均衡器流量或所有应用依赖。容器的 READY 计数和 Pod Ready condition 也不是同一概念。

</details>
