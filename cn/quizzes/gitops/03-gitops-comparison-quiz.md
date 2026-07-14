# GitOps 工具对比测验

本测验检验你对 GitOps 工具的理解，以及如何在它们之间进行选择。

1. 哪个 GitOps 工具开箱即提供内置 Web UI？
   - A) FluxCD
   - B) ArgoCD
   - C) 两者都有
   - D) 两者都没有

<details>
<summary>显示答案</summary>

**答案：B) ArgoCD**

**说明：**
ArgoCD 包含一个功能丰富的内置 Web UI，用于管理应用程序。FluxCD 以 CLI 为主，且不包含内置 UI，不过可以添加 Weave GitOps 等第三方 UI。

</details>

2. 哪个工具对 OCI 制品作为部署源提供了更好的原生支持？
   - A) ArgoCD
   - B) FluxCD
   - C) 两者提供同等支持
   - D) 两者都不支持 OCI

<details>
<summary>显示答案</summary>

**答案：B) FluxCD**

**说明：**
FluxCD 通过其 OCIRepository 源类型为 OCI 制品提供一等支持，使你能够从兼容 OCI 的 registry 存储和部署。ArgoCD 对 OCI 的支持仅限于 Helm chart。

</details>

3. 哪个工具提供内置镜像自动化（针对新镜像自动更新 Git）？
   - A) ArgoCD（原生）
   - B) FluxCD（原生）
   - C) 两者都提供原生支持
   - D) 两者都不提供原生支持

<details>
<summary>显示答案</summary>

**答案：B) FluxCD（原生）**

**说明：**
FluxCD 通过其 Image Reflector 和 Image Automation controllers 提供内置 Image Automation。ArgoCD 需要单独的 Argo Image Updater 项目才能实现类似功能。

</details>

4. 对于哪种使用场景，ArgoCD 是更好的选择？
   - A) 不需要 UI 的 CLI 驱动型工作流
   - B) 需要可视化部署管理和 SSO 集成的团队
   - C) 对资源占用要求极低
   - D) 基于 OCI 制品的部署

<details>
<summary>显示答案</summary>

**答案：B) 需要可视化部署管理和 SSO 集成的团队**

**说明：**
ArgoCD 在团队需要通过其 Web UI 获得可视化反馈、全面的 RBAC 以及与企业身份提供商进行 SSO 集成的环境中表现出色。

</details>

5. ArgoCD 和 FluxCD 可以在同一个 cluster 中一起使用吗？
   - A) 不可以，它们互相排斥
   - B) 可以，它们可以相互补充
   - C) 仅限开发环境
   - D) 仅可通过特殊配置实现

<details>
<summary>显示答案</summary>

**答案：B) 可以，它们可以相互补充**

**说明：**
ArgoCD 和 FluxCD 可以一起使用。一种常见模式是使用 FluxCD 进行基础设施管理和镜像自动化，同时使用 ArgoCD 通过其 UI 进行应用程序部署。

</details>
