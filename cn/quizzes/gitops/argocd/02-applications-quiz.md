# ArgoCD Applications 测验

本测验用于测试你对 ArgoCD Applications 及其配置的理解。

1. ArgoCD Application 资源的主要用途是什么？
   - A) 定义用户访问控制
   - B) 指定应用程序的期望状态及其同步设置
   - C) 配置通知
   - D) 管理机密信息

<details>
<summary>显示答案</summary>

**答案：B) 指定应用程序的期望状态及其同步设置**

**说明：**
ArgoCD Application 是一种 Kubernetes 自定义资源，用于定义应用程序的源（Git 仓库、路径、修订版本）、目标（集群、命名空间）及同步策略。健康状态由控制器报告；自定义资源的健康检查需在 argocd-cm 中单独配置。

</details>

2. Application 规约中的哪个字段定义了应将清单部署到何处？
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>显示答案</summary>

**答案：C) destination**

**说明：**
`destination` 字段指定应用程序资源应部署到的目标集群（通过服务器 URL 或名称指定）和命名空间。

</details>

3. 对于以 Git 为源的 Application，`spec.source.path` 指定什么？
   - A) ArgoCD 的安装路径
   - B) Git 仓库中包含清单的目录
   - C) 本地文件系统路径
   - D) API 服务器路径

<details>
<summary>显示答案</summary>

**答案：B) Git 仓库中包含清单的目录**

**说明：**
`source` 下的 `path` 字段指定 Git 仓库中包含 Kubernetes 清单、Helm chart 或 Kustomize 配置的目录。

</details>

4. 哪个内置同步选项会让 Argo CD 自动创建 destination.namespace？
   - A) 先手动创建命名空间
   - B) 在 syncPolicy.syncOptions 中使用 CreateNamespace=true
   - C) 无法做到
   - D) 使用同步前钩子

<details>
<summary>显示答案</summary>

**答案：B) 在 syncPolicy.syncOptions 中使用 CreateNamespace=true**

**说明：**
在 `syncPolicy.syncOptions` 中设置 `CreateNamespace=true`，会让 ArgoCD 在同步前自动创建目标命名空间，但仍受 AppProject/RBAC 授权约束。它不会创建清单中指定的每一个不同命名空间。

</details>

5. `targetRevision: HEAD` 和 `targetRevision: main` 之间有什么区别？
   - A) 没有区别
   - B) HEAD 跟随远程 HEAD；main 指定一个具体分支
   - C) HEAD 更快
   - D) main 支持 webhooks，HEAD 不支持

<details>
<summary>显示答案</summary>

**答案：B) HEAD 跟随远程 HEAD；main 指定一个具体分支**

**说明：**
`HEAD` 是指向仓库默认分支的符号引用，而 `main` 明确指定 main 分支。默认分支变更可能影响部署目标。对于要求可复现的发布，应采用经过验证的提交/标签策略。

</details>

6. 要从 Helm 仓库（而非 Git）部署 Helm chart，应使用哪种源类型？
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>显示答案</summary>

**答案：B) helm**

**说明：**
从 Helm 仓库部署时，需设置 `source.chart` 和 `source.repoURL` 以指向 Helm 仓库，ArgoCD 会将其视为 Helm 源而非 Git 源。

</details>

7. 设置 `spec.source.helm.releaseName` 后会发生什么？
   - A) 创建一个新的 Helm 仓库
   - B) 覆盖默认的发布名称（即 Application 名称）
   - C) 启用 Helm hooks
   - D) 设置 chart 版本

<details>
<summary>显示答案</summary>

**答案：B) 覆盖默认的发布名称（即 Application 名称）**

**说明：**
默认情况下，ArgoCD 使用 Application 名称作为 Helm 发布名称。releaseName 更改的是模板中的 Release.Name；资源生命周期仍由 Argo CD 管理，而不是通过维护普通的 Helm release 来管理。如果采用基于标签的跟踪方式，应检查 chart 选择器与跟踪标签之间的相互影响。

</details>

8. 如何在 ArgoCD Application 中指定 Helm values？
   - A) 仅通过仓库中的 values 文件
   - B) 仅以内联方式写在 Application 规约中
   - C) 可同时通过 values 文件和内联 values 指定
   - D) values 必须存储在 ConfigMap 中

<details>
<summary>显示答案</summary>

**答案：C) 可同时通过 values 文件和内联 values 指定**

**说明：**
ArgoCD 支持通过 `spec.source.helm.valueFiles`（引用仓库中的文件）和/或 `spec.source.helm.values`（内联 YAML）指定 Helm values。两者可以组合使用。完整优先级为 parameters > valuesObject > values > valueFiles > chart 默认值；宜只采用一种内联表示方式，避免在 valuesObject 与 values 中重复配置。

</details>
