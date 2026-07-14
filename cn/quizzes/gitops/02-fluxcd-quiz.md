# FluxCD 测验

本测验用于测试您对 FluxCD 及其组件的理解。

1. FluxCD 拥有哪种 CNCF 状态？
   - A) Sandbox
   - B) Incubating
   - C) Graduated
   - D) Archived

<details>
<summary>显示答案</summary>

**答案：C) Graduated**

**说明：**
FluxCD 于 2022 年 11 月从 CNCF 毕业，这表明它已达到成熟度，并在生产环境中得到广泛采用。

</details>

2. 哪个 FluxCD controller 负责从 Git repository 获取 artifacts？
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>显示答案</summary>

**答案：C) Source Controller**

**说明：**
Source Controller 负责从外部来源获取 artifacts，包括 Git repositories (GitRepository)、Helm repositories (HelmRepository)、OCI registries (OCIRepository) 和 S3 buckets (Bucket)。

</details>

3. FluxCD 使用哪个 CRD 来部署 Kustomize configurations？
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>显示答案</summary>

**答案：B) Kustomization**

**说明：**
Kustomization CRD 用于定义应如何将 Kustomize overlays 应用到 cluster。它引用一个 source (GitRepository)，并指定 Kustomize configuration 的 path。

</details>

4. FluxCD 如何处理 Helm chart deployments？
   - A) 使用 Application CRD
   - B) 使用 HelmRelease CRD
   - C) 直接使用 helm CLI
   - D) 不支持 Helm

<details>
<summary>显示答案</summary>

**答案：B) 使用 HelmRelease CRD**

**说明：**
HelmRelease CRD 用于以声明式方式管理 Helm chart releases。它指定 chart source、version、values 以及 upgrade/rollback policies。

</details>

5. FluxCD 的 ImageUpdateAutomation 的用途是什么？
   - A) 扫描 image vulnerabilities
   - B) 检测到新版本时自动更新 Git 中的 image tags
   - C) 构建 container images
   - D) 管理 image pull secrets

<details>
<summary>显示答案</summary>

**答案：B) 检测到新版本时自动更新 Git 中的 image tags**

**说明：**
ImageUpdateAutomation 与 ImageRepository 和 ImagePolicy 协同工作，以检测新的 container image tags，并自动将更新 commit 到 Git repository，从而实现 automated deployments。

</details>

6. 使用哪个命令在 cluster 上 bootstrap FluxCD？
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>显示答案</summary>

**答案：B) flux bootstrap**

**说明：**
`flux bootstrap` 命令会安装 FluxCD components，并配置 Git repository 来管理 cluster。它支持 GitHub、GitLab 和 generic Git servers 等多种 Git providers。

</details>

7. FluxCD 如何支持 multi-tenancy？
   - A) 使用类似 ArgoCD 的 Projects
   - B) 使用 namespace isolation 和 Kubernetes RBAC
   - C) 不支持 multi-tenancy
   - D) 使用 central admin tenant

<details>
<summary>显示答案</summary>

**答案：B) 使用 namespace isolation 和 Kubernetes RBAC**

**说明：**
FluxCD 通过 namespace isolation 支持 multi-tenancy，其中每个 tenant 都拥有包含 Flux resources 的独立 namespace，并结合 Kubernetes 原生 RBAC 进行 access control。

</details>

8. FluxCD 中 Notification Controller 的用途是什么？
   - A) 发送 SMS messages
   - B) 处理 events 并向 external services 发送 alerts
   - C) 仅管理 Git webhooks
   - D) 监控 Pod logs

<details>
<summary>显示答案</summary>

**答案：B) 处理 events 并向 external services 发送 alerts**

**说明：**
Notification Controller 同时处理 outbound notifications（发往 Slack、Teams 等的 Alerts）和 inbound webhooks (Receivers)。当发生 external events 时，inbound webhooks 会触发 reconciliation。

</details>
