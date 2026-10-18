# 账户结构与 IAM 边界

> **最后更新**：2026 年 9 月 13 日

## 1. 应以什么为依据划分账户？

划分账户时，最常见的候选维度是团队、品牌、领域和环境（生产 / 非生产）。但**判断账户边界时，应看相关工作负载共同具有的安全要求、服务配额、成本 / 归属关系和生命周期，而不是团队名称**。团队可能因重组而频繁变动，领域（业务能力）则相对稳定，因而更适合作为账户划分候选。

| 方案 | 配置 | 优点 | 缺点 |
|---|---|---|---|
| 领域 × 环境 | 每个领域分别使用生产 / 非生产账户 | 易于将成本、配额、权限和归属关系关联到领域 | 即使领域规模很小，也要承担固定成本；领域重组会直接导致迁移 |
| 品牌 × 环境 | 每个品牌和环境使用各自账户，每个账户可包含多个领域 | 通过账户边界管理品牌级成本、配额、权限、隔离和转移 | 跨品牌共享功能的归属关系会变得模糊；品牌生命周期变化会直接触发账户重组 |
| 少量中心工作负载账户 | 将多个领域 / 团队的工作负载放入少数几个共享账户 | 初期运维简单，小型工作负载易于接入 | 配额、权限和故障影响范围会扩大，之后也难以拆分 |
| **混合组合** | 小型工作负载放入共享账户；安全、监管或配额边界严格的工作负载使用专用账户 | 根据需求组合使用共享、领域专属和专用账户 | 判断标准不严谨会迅速增加例外情况 |

实践中常见的做法是以混合组合起步，并在每次决策时使用可复现的决策矩阵判断采用共享还是专用账户（矩阵的设计方法见[决策框架](./06-decision-framework-and-poc.md)）。

如果品牌维度的目的只是区分成本，就应将品牌作为元数据处理；只有在存在强边界（监管、独立配额、权限或拆分可能性）时，才应将其提升为账户划分维度。若一个工作负载跨领域汇总数据并通过 API 提供服务，且具有独立的 SLO、配额、数据访问权限和生命周期，则可考虑为其设置单独的工作负载账户。**账户分开不一定意味着 EKS 集群也要分开。**

> **拆分规划**：一个 Organization 内支持子网共享。离开前应准备独立的网络迁移。取消共享后，现有资源可能仍会继续运行，但可能影响新建资源以及托管服务的替换 / 扩缩容。取消共享不会立即删除或停止所有资源。

## 2. 账户与 EKS 运行时的关系

确定账户划分后，还要决定由哪个账户中的 EKS 集群运行 Kubernetes 工作负载。

| 方案 | 配置 | 优点 | 缺点 |
|---|---|---|---|
| 每个工作负载账户配一个专用 EKS | 每个工作负载账户拥有自己的 EKS 集群 | 账户归属与运行时归属 / 故障影响范围一致 | 即使是小型工作负载，也需要一个集群，因此要管理更多集群和闲置容量 |
| **工作负载账户 + 共享集群账户** | Lambda / SQS / DB 等资源位于各自的工作负载账户中，Kubernetes 工作负载则运行在另一个账户中的共享 EKS 集群 | 可分别决定账户边界和需要管理的 EKS 集群数量 | 跨账户身份、网络和集群归属管理会更复杂 |

在第二种模式中，应区分集群账户的 IAM 角色与访问其他账户数据的权限。使用共享 VPC 时，创建 EKS 的参与账户是**集群账户**；数据库或队列等资源的所有者则可能是工作负载账户。请根据情况选择 Pod Identity 目标角色链、服务资源策略或 IRSA。

### EKS 相关配额：哪些有余量，哪些会碰到上限

| 配额 | 默认值 | 可调整 |
|---|---|---|
| 集群 / 区域 | 100 | 是 |
| 托管节点组 / 集群 | 30 | 是 |
| 节点 / 节点组 | 450 | 是 |
| 控制平面安全组 / 集群 | 4 | 否 |
| 允许访问公有端点的 CIDR / 集群 | 40 | 否 |
| **Access Entry / 集群** | **3,000** | **否** |

多数 EKS 配额仍有余量，但**每个集群 3,000 个 Access Entry 的不可调整上限**是真实限制。如果几十个团队按“每个工作负载 × 每个环境”分别创建 CI/CD 角色，很快就会接近上限。建议将访问路径整合到 Permission Set 或团队级角色中，并按主体类型分组创建 Access Entry。

30 个托管节点组是可调整的默认配额，并非固定的 30 个租户上限。Karpenter NodePool 和 taint / toleration 用于控制放置位置，但其自身并不构成强安全边界。应综合评估已应用的配额、权限、共享内核和节点代理权限。

## 3. 人员访问 AWS（员工 IAM）

| 方案 | 配置 | 优点 | 缺点 |
|---|---|---|---|
| **Identity Center + RBAC** | 用户通过 Identity Center 登录，并通过基于角色的 Permission Set 访问账户 | 临时凭证、集中撤销 / 审计 | 团队 × 领域 × 环境组合可能导致 Permission Set 数量膨胀 |
| RBAC + 有限 ABAC | 在每个 RBAC 角色的权限上限内，使用标签进一步缩小资源范围 | 结合权限上限与可扩展性 | 需要测试 RBAC 和 ABAC，并控制有权分配标签的主体 |
| 以 ABAC 为核心 | 主要在用户标签与资源标签匹配时授予权限 | 随着账户 / 工作负载增长，可减少策略重复 | 标签授权控制较弱时，权限蔓延和排错难度会增加 |

建议完全不将每账户 IAM 用户纳入常规方案。只在 Identity Center 不可用时，将其作为紧急访问例外，并明确记录用途、负责人、使用条件、凭证存储方式、定期审查和终止条件。

### IAM Identity Center 的实际配额上限

| 配额 | 默认值 | 可调整 |
|---|---|---|
| Permission Set 总数 | 3,500 | 是 |
| 每个账户预置的 Permission Set | 500 | 是 |
| 每个 Permission Set 的托管策略数 | 25；另有单独的 IAM 角色默认值 10，需按需提高 | Permission Set 限制：否 |
| 每个 Permission Set 的内联策略 | 32,768 字节；其中非空白字符 10,240 字节 | 否 |
| **每个账户的单个 Permission Set 可分配的组数** | **100** | **否** |
| 可配置账户数 | 7,000 | 是 |
| Identity Center API 限流 | 总计 20 TPS；读取请求的上限可通过支持渠道提高 | 检查其他 API 专属限制 |

100 个组的限制适用于**特定账户中的特定 Permission Set 组合**，并非某账户内所有组的总限制。不要将不同 Permission Set 的组数相加，再把 100 当作账户级 RBAC 上限。

> **设计提案**：比较简化 RBAC、采用 ABAC 和拆分账户之前，先测量每个 Permission Set 的分配数量和策略重复情况。达到 50 时发出警告可以作为本地阈值，但这既不是 AWS 要求，也不是必须启用 ABAC 的触发条件。

## 4. 工作负载（应用程序 / 自动化）访问 AWS

以下选项并不互斥；应根据执行环境以及是否需要跨账户访问，将它们组合使用。

| 方式 | 配置 | 适用场景 |
|---|---|---|
| 运行时角色 | 将 IAM 角色附加到执行环境（EC2 / Lambda / ECS 等） | 非 EKS 工作负载 |
| **EKS Pod Identity** | 通过 Pod Identity association 将 Pod 关联到 IAM 角色 | 支持的 EKS 工作负载（推荐方向） |
| IRSA | Kubernetes ServiceAccount token + IAM OIDC provider | 需要兼容现有集群 / 工具链的场景 |
| **跨账户目标角色** | 源角色代入目标账户角色 | 需要以目标角色权限执行的路径 |

仅在不支持角色或联合身份的旧式集成场景中，才将静态访问密钥作为例外使用，并记录用途、负责人、过期时间和轮换安排。

主要的 Pod Identity association 角色位于集群账户中。设置 `targetRoleArn` 会形成两个角色的链；受支持的资源策略也可以直接授权该源角色。IRSA 也可以直接联合到目标账户的 OIDC provider / 角色。角色复用方式以及会话标签 / 策略设计会影响角色数量；“每个工作负载恰好两个”并非通用规律。用于 AWS API 的工作负载角色与用于 Kubernetes API 访问的 Access Entry 应分别计数。

## 5. Kubernetes API 访问

| 方式 | 配置 | 状态 |
|---|---|---|
| **EKS Access Entry** | 使用 Access Entry 按 IAM 主体管理集群访问；可选择 Access Policy，或通过 Kubernetes group 映射到 RBAC | 推荐方向 |
| aws-auth ConfigMap | 通过集群的 `aws-auth` ConfigMap 管理 IAM 主体到 Kubernetes 身份的映射 | 仅在旧集群迁移期间作为例外保留 |

**权限并集**：Access Policy 授予的权限与 Kubernetes RBAC 授予的权限会合并；任一方都不会限制另一方。请记录每个主体的主要访问路径和有意配置的额外授权，并审查两者的重叠。自动化检查是可选的实现方式，并非使用该 API 的前置要求。

## 后续阅读

确定账户和 IAM 边界后，下一步应决定运行多少个 EKS 集群以及如何实现高可用 → [多账户、多集群 EKS 架构](./03-eks-multi-account-multi-cluster.md)

## 参考资料

- [IAM Identity Center 配额](https://docs.aws.amazon.com/singlesignon/latest/userguide/limits.html)
- [IAM Identity Center ABAC](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)
- [EKS Access Entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS IAM 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [EKS Pod Identity 目标角色](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-assign-target-role.html)
- [适用于 Service Account 的 IAM 角色（IRSA）](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS 多账户策略](https://docs.aws.amazon.com/eks/latest/best-practices/multi-account-strategy.html)
- [EKS 配额](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [EKS 共享子网要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [取消子网共享](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-sharing-share-subnet-working-with.html)
- [EKS 资源策略模式](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
