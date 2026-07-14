# ArgoCD Applications 测验

本测验用于测试你对 ArgoCD Applications 及其配置的理解。

1. ArgoCD Application resource 的主要目的是什么？
   - A) 定义用户访问控制
   - B) 指定应用程序的期望状态及其同步设置
   - C) 配置通知
   - D) 管理 secrets

<details>
<summary>显示答案</summary>

**答案：B) 指定应用程序的期望状态及其同步设置**

**说明：**
ArgoCD Application 是一种 Kubernetes custom resource，用于定义应用程序的源（Git 仓库、路径、revision）和目标（cluster、namespace），以及同步策略和运行状况检查。

</details>

2. Application spec 中的哪个字段定义了应将 manifests 部署到何处？
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>显示答案</summary>

**答案：C) destination**

**说明：**
`destination` 字段指定应部署应用程序 resources 的目标 cluster（通过 server URL 或名称）和 namespace。

</details>

3. Application 中的 `spec.source.path` 字段指定什么？
   - A) ArgoCD 安装路径
   - B) Git 仓库中包含 manifests 的目录
   - C) 本地文件系统路径
   - D) API server 路径

<details>
<summary>显示答案</summary>

**答案：B) Git 仓库中包含 manifests 的目录**

**说明：**
`source` 下的 `path` 字段指定 Git 仓库中包含 Kubernetes manifests、Helm chart 或 Kustomize 配置的目录。

</details>

4. 如何将应用程序部署到一个尚不存在的特定 namespace？
   - A) 先手动创建 namespace
   - B) 使用带有 CreateNamespace=true 的 syncPolicy.syncOptions
   - C) 无法做到
   - D) 使用 pre-sync hook

<details>
<summary>显示答案</summary>

**答案：B) 使用带有 CreateNamespace=true 的 syncPolicy.syncOptions**

**说明：**
在 `syncPolicy.syncOptions` 中设置 `CreateNamespace=true` 会指示 ArgoCD 在同步应用程序 resources 之前，如果目标 namespace 不存在则自动创建它。

</details>

5. `targetRevision: HEAD` 和 `targetRevision: main` 之间有什么区别？
   - A) 没有区别
   - B) HEAD 始终指向默认 branch，而 main 是显式指定的
   - C) HEAD 更快
   - D) main 支持 webhooks，HEAD 不支持

<details>
<summary>显示答案</summary>

**答案：B) HEAD 始终指向默认 branch，而 main 是显式指定的**

**说明：**
`HEAD` 是一个 symbolic reference，指向仓库的默认 branch；而 `main` 明确指定 main branch。如果默认 branch 发生变化，使用 `HEAD` 会更灵活。

</details>

6. 要从 Helm repository（而非 Git）部署 Helm chart，应使用哪种 source type？
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>显示答案</summary>

**答案：B) helm**

**说明：**
从 Helm repository 部署时，需设置 `source.chart` 和 `source.repoURL` 以指向 Helm repository，ArgoCD 会将其视为 Helm source 而非 Git source。

</details>

7. 设置 `spec.source.helm.releaseName` 后会发生什么？
   - A) 创建一个新的 Helm repository
   - B) 覆盖默认 release name（即 Application 名称）
   - C) 启用 Helm hooks
   - D) 设置 chart version

<details>
<summary>显示答案</summary>

**答案：B) 覆盖默认 release name（即 Application 名称）**

**说明：**
默认情况下，ArgoCD 使用 Application 名称作为 Helm release name。显式设置 `releaseName` 可让你为 Helm release 使用不同的名称。

</details>

8. 如何在 ArgoCD Application 中指定 Helm values？
   - A) 仅通过仓库中的 values files
   - B) 仅以内联方式写在 Application spec 中
   - C) 可同时通过 values files 和内联 values 指定
   - D) values 必须存储在 ConfigMap 中

<details>
<summary>显示答案</summary>

**答案：C) 可同时通过 values files 和内联 values 指定**

**说明：**
ArgoCD 支持通过 `spec.source.helm.valueFiles`（引用仓库中的文件）和/或 `spec.source.helm.values`（内联 YAML）指定 Helm values。两者可以同时使用，其中内联 values 优先。

</details>
