# ArgoCD 安装测验

本测验用于测试您对 ArgoCD 安装和配置的理解。

1. 在生产环境中安装 ArgoCD 的推荐方法是什么？
   - A) 从原始 GitHub URL 使用 kubectl apply
   - B) 使用自定义值的 Helm chart
   - C) Docker Compose
   - D) 手动安装二进制文件

<details>
<summary>显示答案</summary>

**答案：B) 使用自定义值的 Helm chart**

**说明：**
虽然可以使用官方 manifests 通过 kubectl apply 安装 ArgoCD，但建议在生产环境中使用 Helm chart，因为它可以更轻松地自定义、升级和管理配置值。

</details>

2. ArgoCD 默认通常安装到哪个 namespace？
   - A) default
   - B) kube-system
   - C) argocd
   - D) gitops

<details>
<summary>显示答案</summary>

**答案：C) argocd**

**说明：**
按照惯例，ArgoCD 安装在 `argocd` namespace 中。这样可以将 ArgoCD 组件隔离开，并更容易管理 RBAC 和资源配额。

</details>

3. ArgoCD Repo Server 组件的用途是什么？
   - A) 存储应用程序状态
   - B) 克隆 Git repositories 并生成 Kubernetes manifests
   - C) 提供 Web UI
   - D) 管理用户身份验证

<details>
<summary>显示答案</summary>

**答案：B) 克隆 Git repositories 并生成 Kubernetes manifests**

**说明：**
Repo Server 负责克隆 Git repositories 并从各种来源（Helm、Kustomize、普通 YAML）生成 Kubernetes manifests。它会缓存 repository 数据以提升性能。

</details>

4. 安装 ArgoCD 后，如何获取初始 admin 密码？
   - A) 安装期间会打印出来
   - B) 从名为 argocd-initial-admin-secret 的 Secret 中获取
   - C) 从 ArgoCD ConfigMap 中获取
   - D) 始终是 "admin"

<details>
<summary>显示答案</summary>

**答案：B) 从名为 argocd-initial-admin-secret 的 Secret 中获取**

**说明：**
初始 admin 密码会自动生成，并存储在名为 `argocd-initial-admin-secret` 的 Kubernetes Secret 中。您可以使用以下命令获取它：`kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

</details>

5. 哪种 ArgoCD 安装模式使用更少的资源，但功能有限？
   - A) HA mode
   - B) Core mode
   - C) Lite mode
   - D) Minimal mode

<details>
<summary>显示答案</summary>

**答案：B) Core mode**

**说明：**
ArgoCD Core mode 只安装必要组件（Application Controller 和 Repo Server），不包括 API Server、UI 或 Dex。该模式适用于完全通过 Git 和 CLI 管理 ArgoCD 的环境。

</details>
