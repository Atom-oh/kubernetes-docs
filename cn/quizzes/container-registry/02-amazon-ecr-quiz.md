# Amazon ECR 测验
> **最后更新**：2026 年 9 月 11 日

1. Amazon ECR Private 与 Amazon ECR Public 的主要区别是什么？
   - A) ECR Private 免费，ECR Public 付费
   - B) 所有 ECR Private 操作都需要身份验证，而 ECR Public 允许匿名拉取
   - C) ECR Private 仅支持 Docker 镜像，ECR Public 支持所有格式
   - D) ECR Private 是区域级服务，ECR Public 仅在 us-east-1 提供

<details>
<summary>显示答案</summary>

**答案**：B) 所有 ECR Private 操作都需要身份验证，而 ECR Public 允许匿名拉取

**说明**：向私有仓库推送/拉取都需要身份验证。公共镜像允许匿名拉取，但发布和管理仍需身份验证。公共 API 端点列在 us-east-1 和 us-west-2，镜像则通过全球 URL 分发。

</details>

2. 哪个 CLI 命令会直接输出 ECR 密码，以便通过 `docker login --password-stdin` 使用？
   - A) `aws ecr get-authorization-token`
   - B) `aws ecr get-login-password`
   - C) `aws ecr login`
   - D) `aws ecr authenticate`

<details>
<summary>显示答案</summary>

**答案**：B) `aws ecr get-login-password`

**说明：**`get-login-password` 会输出适用于标准输入的密码。`get-authorization-token` 也是有效的 API/CLI 操作，但它返回的是编码后的授权令牌，需要先解码。

</details>

3. ECR 生命周期策略中的多条规则同时匹配同一镜像时，由什么决定应用哪条规则？
   - A) `rulePriority` 数值最低的规则优先
   - B) `rulePriority` 数值最高的规则优先
   - C) 按字母顺序应用规则
   - D) 同时应用所有匹配规则

<details>
<summary>显示答案</summary>

**答案**：A) `rulePriority` 数值最低的规则优先

**说明**：系统会先评估所有规则，然后按优先级应用其结果。数字越低，优先级越高；如果镜像匹配高优先级规则的标签要求，低优先级规则就不能将其过期删除。这并不是按顺序执行规则、匹配后即停止的逻辑。

</details>

4. ECR 生命周期策略的 `tagPatternList` 使用哪种模式语法？
   - A) 正则表达式
   - B) 文档指定的 `*` 通配符模式
   - C) SQL LIKE 模式
   - D) 仅精确字符串匹配

<details>
<summary>显示答案</summary>

**答案**：B) 文档指定的 `*` 通配符模式

**说明**：请使用文档指定的 `*` 通配符，每个字符串中最多四个星号。不要假设它支持正则表达式、字符类或完整的 Unix glob 行为。`v*` 可选择某个前缀；CI 应验证发布版本格式。

</details>

5. ECR 生命周期策略在规则逻辑上有什么主要限制？
   - A) 规则不能超过 5 条
   - B) 单条规则无法表达标签模式之间的 OR/并集逻辑
   - C) 无法删除未标记的镜像
   - D) imageCountMoreThan 不能与 countType 一起使用

<details>
<summary>显示答案</summary>

**答案**：B) 单条规则无法表达标签模式之间的 OR/并集逻辑

**说明**：一条包含多个 `tagPatternList` 模式的 ECR 生命周期规则使用 AND 逻辑（镜像必须匹配所有模式）。若要实现 OR 逻辑（匹配任意模式），必须为每个模式创建单独的规则。当想对匹配不同标签模式的镜像应用相同的保留策略时，应谨慎设计规则。

</details>

6. ECR 的策略 A（每个环境单独使用仓库）的主要优势是什么？
   - A) 每个仓库保留需求一致，因此生命周期策略更简单
   - B) 存储成本更低
   - C) 镜像拉取速度更快
   - D) 自动跨区域复制

<details>
<summary>显示答案</summary>

**答案**：A) 每个仓库保留需求一致，因此生命周期策略更简单

**说明**：策略 A 为每个环境使用单独的仓库（例如 `myapp-dev`、`myapp-prod`）。由于每个仓库中的镜像保留要求一致，生命周期策略更容易管理。代价是要维护多个仓库，并且可能需要在仓库间复制镜像。

</details>

7. 用于定义 ECR 生命周期策略的 Terraform 资源是什么？
   - A) `aws_ecr_repository`
   - B) `aws_ecr_lifecycle_policy`
   - C) `aws_ecr_repository_policy`
   - D) `aws_ecr_retention_policy`

<details>
<summary>显示答案</summary>

**答案**：B) `aws_ecr_lifecycle_policy`

**说明：**`aws_ecr_lifecycle_policy` Terraform 资源会为 ECR 仓库附加生命周期策略。它需要 `repository` 名称和一份用于定义生命周期规则的 `policy` JSON 文档。`aws_ecr_repository_policy` 是不同的资源，用于配置控制仓库访问权限的 IAM 资源策略。

</details>

8. 对于基于 EC2 的 EKS 节点，通常由哪个身份提供初始的 ECR 镜像拉取权限？
   - A) 使用存储在 Secret 中的静态访问密钥
   - B) kubelet 直接使用节点的 IAM 角色
   - C) Pod 通过 OIDC 联合身份承担 IAM 角色并使用临时凭证
   - D) 在 ConfigMap 中预置 ECR 令牌

<details>
<summary>显示答案</summary>

**答案**：B) kubelet 直接使用节点的 IAM 角色

**说明**：应用程序启动前，kubelet 会使用节点的镜像拉取凭证来拉取镜像。Fargate 使用 Pod 执行角色。IRSA/Pod Identity 会在 Pod 启动后提供工作负载 SDK 凭证，但不会替代启动阶段的镜像拉取身份。

</details>

9. 启用 ECR 仓库的不可变标签会阻止什么？
   - A) 删除仓库中的任何镜像
   - B) 使用已有镜像的同一标签推送新镜像
   - C) 未经身份验证拉取镜像
   - D) 创建生命周期策略

<details>
<summary>显示答案</summary>

**答案**：B) 使用已有镜像的同一标签推送新镜像

**说明**：不可变标签可防止覆盖现有镜像标签。镜像以某个指定标签推送后，该标签不能再用于指向不同的镜像摘要。这可以确保部署标签稳定，并避免意外或恶意替换镜像。镜像仍可删除，也可以继续推送新的唯一标签。

</details>

10. 关于 ECR 跨区域复制，哪种描述正确？
    - A) 仅复制镜像清单
    - B) 符合条件的镜像及标签会异步复制；目标端设置需单独管理
    - C) 所有内容都会复制，包括生命周期策略和权限
    - D) 所有预先存在的镜像都会自动回填

<details>
<summary>显示答案</summary>

**答案**：B) 符合条件的镜像及标签会异步复制；目标端设置需单独管理

**说明**：配置复制之后推送或恢复的镜像符合复制条件。已有内容不会自动回填。目标仓库的设置、权限和生命周期策略需独立配置，例如使用创建模板。在依赖复制进行恢复之前，应验证目标端是否存在所需的镜像摘要。

</details>
