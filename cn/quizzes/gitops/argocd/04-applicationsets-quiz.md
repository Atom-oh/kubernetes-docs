# ArgoCD ApplicationSets 测验

本测验用于测试你对 ArgoCD ApplicationSets 根据模板生成应用程序的理解。

1. ApplicationSet 的主要用途是什么？
   - A) 对现有 Applications 进行分组
   - B) 根据模板自动生成多个 Applications
   - C) 创建应用程序备份
   - D) 管理应用程序密钥

<details>
<summary>显示答案</summary>

**答案：B) 根据模板自动生成多个 Applications**

**说明：**
ApplicationSets 使用生成器和模板自动创建和管理多个 ArgoCD Applications，适合在多个集群或环境中部署应用程序。

</details>

2. 若要为 ArgoCD 中注册的每个集群创建 Applications，应使用哪种生成器？
   - A) Git 生成器
   - B) List 生成器
   - C) Cluster 生成器
   - D) Matrix 生成器

<details>
<summary>显示答案</summary>

**答案：C) Cluster 生成器**

**说明：**
Cluster 生成器会为 ArgoCD 中注册的每个集群自动生成 Applications，也可以使用标签选择器指定特定集群。

</details>

3. Git 目录生成器的作用是什么？
   - A) 根据 Git 分支创建 Applications
   - B) 为指定路径中的每个目录创建 Applications
   - C) 同步 Git 凭据
   - D) 管理 Git webhooks

<details>
<summary>显示答案</summary>

**答案：B) 为指定路径中的每个目录创建 Applications**

**说明：**
Git 目录生成器扫描 Git 仓库中的指定目录，并为符合已配置的 glob 匹配模式和排除规则的每个目录创建一个 Application。这适用于单体仓库布局。

</details>

4. 如何在 ApplicationSet 中组合多个生成器？
   - A) 使用 Merge 生成器
   - B) 使用 Matrix 生成器
   - C) 使用 Combine 生成器
   - D) A 和 B 都可以

<details>
<summary>显示答案</summary>

**答案：D) A 和 B 都可以**

**说明：**
Matrix 生成器恰好组合两个子生成器的参数，生成笛卡尔积。Merge 生成器组合多个生成器的参数，并合并匹配的条目。两者都可用于组合生成器。

</details>

5. ApplicationSet 模板中的 `goTemplate` 字段有什么用途？
   - A) 启用 Go 编程
   - B) 使用 Go 模板语法进行更复杂的模板处理
   - C) 编译 Go 应用程序
   - D) 启用调试

<details>
<summary>显示答案</summary>

**答案：B) 使用 Go 模板语法进行更复杂的模板处理**

**说明：**
设置 `goTemplate: true` 会启用 Go 模板语法，相较于默认的简单替换，它支持条件、循环和函数等更强的模板处理能力。每个字符串字段均独立求值；控制语句不能跨 YAML 字段，布尔值/对象字段也不能直接使用模板。

</details>

6. 若要根据拉取请求创建 Applications，应使用哪种生成器？
   - A) Git 生成器
   - B) Pull Request 生成器
   - C) SCM Provider 生成器
   - D) Webhook 生成器

<details>
<summary>显示答案</summary>

**答案：B) Pull Request 生成器**

**说明：**
Pull Request 生成器会为仓库中每个打开的拉取请求创建 Applications，为代码审查提供预览环境。它支持 GitHub、GitLab、Bitbucket 和 Gitea。

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
默认情况下，ApplicationSets 采用级联删除策略，删除 ApplicationSet 时，它生成的所有 Applications 也会被删除。`preserveResourcesOnDeletion` 控制的是已部署资源的清理，而不是 Application 对象是否被垃圾回收。

</details>

8. 如何防止在移除 ApplicationSet 时删除其生成的 Applications？
   - A) 使用 `kubectl delete applicationset NAME --cascade=orphan` 删除
   - B) 仅设置 `syncPolicy.preserveResourcesOnDeletion: true`
   - C) 设置删除策略注解
   - D) 将 ApplicationSet 控制器缩容到零

<details>
<summary>显示答案</summary>

**答案：A) 使用 `kubectl delete applicationset NAME --cascade=orphan` 删除**

**说明：**
`--cascade=orphan` 会在移除父对象时保留生成的 Application 对象。`preserveResourcesOnDeletion: true` 会阻止添加用于删除已部署资源的 finalizer；它不会让 Application 对象免于垃圾回收。带有现存 finalizer 的孤立 Application 在之后被删除时，仍可能删除其资源。

</details>
