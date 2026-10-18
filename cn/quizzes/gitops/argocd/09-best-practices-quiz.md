# ArgoCD 最佳实践测验

本测验用于检验您对 ArgoCD 最佳实践和运维模式的理解。

1. 哪种模式使用管理员拥有的根仓库来声明多个子 Application？
   - A) 通过 UI 手动配置
   - B) App of Apps
   - C) 直接使用 kubectl apply
   - D) 配置永远不应更改

<details>
<summary>显示答案</summary>

**答案：B) App of Apps**

**说明：**
App of Apps 使用根 Application 管理子 Application。它不等同于让 Argo CD 管理自身，也并非每次安装都必须采用。应将其视为管理员能力，限制仓库写入权限，并保留独立的引导/恢复路径。

</details>

2. GitOps 推荐的仓库结构是什么？
   - A) 将应用程序代码和清单文件混合在同一仓库中
   - B) 为应用程序代码和部署清单文件使用独立的仓库
   - C) 将所有内容存储在单个文件中
   - D) 仅使用来自公共仓库的 Helm chart

<details>
<summary>显示答案</summary>

**答案：B) 为应用程序代码和部署清单文件使用独立的仓库**

**说明：**
将应用程序代码与部署清单文件分离可提供更清晰的审计记录，让不同团队分别管理它们，并可能避免因仅涉及部署的变更而重新构建应用程序代码。CI 触发器、路径过滤器和仓库边界仍需明确设计。

</details>

3. 如何在表达特定环境的配置值时复用通用清单？
   - A) 为每个环境创建独立的 Application
   - B) 为每个环境使用 Kustomize overlay 或 Helm values 文件
   - C) 在清单文件中硬编码值
   - D) 在 Pod 中使用环境变量

<details>
<summary>显示答案</summary>

**答案：B) 为每个环境使用 Kustomize overlay 或 Helm values 文件**

**说明：**
使用 Kustomize overlay 或 Helm values 文件可让您维护通用基础配置，同时为每个环境自定义特定值（副本数、资源、域名）。

</details>

4. 在不同环境之间推进变更的推荐方法是什么？
   - A) 直接提交到生产分支
   - B) 从预发布环境到生产环境使用经过审查的 Pull Request
   - C) 在 UI 中手动同步
   - D) 无需审查即可自动推进变更

<details>
<summary>显示答案</summary>

**答案：B) 从预发布环境到生产环境使用经过审查的 Pull Request**

**说明：**
使用 Pull Request 推进变更可确保变更在进入生产环境前经过审查，提供审计记录，并允许在合并前执行自动检查（测试、策略验证）。

</details>

5. 在 GitOps 工作流中应如何处理 Secret？
   - A) 将明文 Secret 提交到 Git
   - B) 使用加密 Secret（Sealed Secrets、SOPS）或外部 Secret 管理器
   - C) 在每个集群中手动创建 Secret
   - D) 将 Secret 存储在环境变量中

<details>
<summary>显示答案</summary>

**答案：B) 使用加密 Secret（Sealed Secrets、SOPS）或外部 Secret 管理器**

**说明：**
绝不应将 Secret 以明文形式存储在 Git 中。请使用 Sealed Secrets 或 SOPS 等加密工具，或者使用 HashiCorp Vault 等外部 Secret 管理器，并结合 External Secrets Operator。

</details>
