# ArgoCD ApplicationSets 测验

本测验旨在测试你对用于模板化应用程序生成的 ArgoCD ApplicationSets 的理解。

1. ApplicationSet 的主要用途是什么？
   - A) 对现有 Applications 进行分组
   - B) 根据模板自动生成多个 Applications
   - C) 创建应用程序备份
   - D) 管理应用程序密钥

<details>
<summary>显示答案</summary>

**答案：B) 根据模板自动生成多个 Applications**

**说明：**
ApplicationSets 使用 generators 和 templates 自动创建和管理多个 ArgoCD Applications。它们非常适合在多个 clusters 或环境中部署应用程序。

</details>

2. 若要为 ArgoCD 中注册的每个 cluster 创建 Applications，应使用哪种 generator？
   - A) Git generator
   - B) List generator
   - C) Cluster generator
   - D) Matrix generator

<details>
<summary>显示答案</summary>

**答案：C) Cluster generator**

**说明：**
Cluster generator 会为 ArgoCD 中注册的每个 cluster 自动生成 Applications。它可以使用 label selectors 定位特定 clusters。

</details>

3. Git directory generator 的作用是什么？
   - A) 根据 Git branches 创建 Applications
   - B) 为指定路径中的每个 directory 创建 Applications
   - C) 同步 Git 凭据
   - D) 管理 Git webhooks

<details>
<summary>显示答案</summary>

**答案：B) 为指定路径中的每个 directory 创建 Applications**

**说明：**
Git directory generator 会扫描 Git repository 中的指定 directory，并为找到的每个 subdirectory 创建一个 Application。这对于 monorepo 设置非常有用。

</details>

4. 如何在 ApplicationSet 中组合多个 generators？
   - A) 使用 Merge generator
   - B) 使用 Matrix generator
   - C) 使用 Combine generator
   - D) A 和 B 都可以

<details>
<summary>显示答案</summary>

**答案：D) A 和 B 都可以**

**说明：**
Matrix generator 会创建来自多个 generators 的参数组合（笛卡尔积）。Merge generator 会组合来自多个 generators 的参数，并合并匹配的条目。两者都可用于组合 generators。

</details>

5. ApplicationSet templates 中 `goTemplate` field 的用途是什么？
   - A) 启用 Go 编程
   - B) 使用 Go template syntax 进行更复杂的模板化
   - C) 编译 Go applications
   - D) 启用调试

<details>
<summary>显示答案</summary>

**答案：B) 使用 Go template syntax 进行更复杂的模板化**

**说明：**
设置 `goTemplate: true` 会启用 Go template syntax，与默认的简单变量替换相比，它提供了更强大的模板化功能，例如 conditionals、loops 和 functions。

</details>

6. 若要根据 pull requests 创建 Applications，应使用哪种 generator？
   - A) Git generator
   - B) Pull Request generator
   - C) SCM Provider generator
   - D) Webhook generator

<details>
<summary>显示答案</summary>

**答案：B) Pull Request generator**

**说明：**
Pull Request generator 会为 repository 中每个已打开的 pull request 创建 Applications，从而为代码审查提供 preview environments。它支持 GitHub、GitLab、Bitbucket 和 Gitea。

</details>

7. 默认情况下，删除 ApplicationSet 时会发生什么？
   - A) 不发生任何操作，生成的 Applications 会保留
   - B) 所有生成的 Applications 都会被删除
   - C) Applications 会成为孤立资源
   - D) 会创建备份

<details>
<summary>显示答案</summary>

**答案：B) 所有生成的 Applications 都会被删除**

**说明：**
默认情况下，ApplicationSets 采用级联删除策略，这意味着删除 ApplicationSet 时，它生成的所有 Applications 也会被删除。可以使用 `preserveResourcesOnDeletion` 策略更改此行为。

</details>

8. 如何防止在移除 ApplicationSet 时删除其生成的 Applications？
   - A) 设置 `syncPolicy.preserveResourcesOnDeletion: true`
   - B) 使用 `orphan` finalizer
   - C) 设置 deletion policy annotation
   - D) 手动移除 owner reference

<details>
<summary>显示答案</summary>

**答案：A) 设置 `syncPolicy.preserveResourcesOnDeletion: true`**

**说明：**
在 ApplicationSet 的 syncPolicy 中设置 `preserveResourcesOnDeletion: true`，可确保在删除 ApplicationSet 时保留生成的 Applications（及其部署的 resources）。

</details>
