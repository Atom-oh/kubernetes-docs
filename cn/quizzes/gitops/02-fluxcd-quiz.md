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

2. 哪个 FluxCD 控制器负责从 Git 仓库获取制品？
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>显示答案</summary>

**答案：C) Source Controller**

**说明：**
Source Controller 负责从外部来源获取制品，包括 Git 仓库（GitRepository）、Helm 仓库（HelmRepository）、OCI 注册表（OCIRepository）和 S3 存储桶（Bucket）。

</details>

3. FluxCD 使用哪个 CRD 来部署 Kustomize 配置？
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>显示答案</summary>

**答案：B) Kustomization**

**说明：**
Kustomization CRD 定义如何将 Kustomize overlay 应用到集群。它引用来源（GitRepository），并指定 Kustomize 配置的路径。

</details>

4. FluxCD 如何处理 Helm chart 部署？
   - A) 使用 Application CRD
   - B) 使用 HelmRelease CRD
   - C) 直接使用 helm CLI
   - D) 不支持 Helm

<details>
<summary>显示答案</summary>

**答案：B) 使用 HelmRelease CRD**

**说明：**
HelmRelease CRD 用于以声明式方式管理 Helm chart 发布。它指定 chart 来源、版本、values，以及升级/回滚策略。

</details>

5. FluxCD 的 ImageUpdateAutomation 的用途是什么？
   - A) 扫描镜像漏洞
   - B) 检测到新版本时自动更新 Git 中的镜像标签
   - C) 构建容器镜像
   - D) 管理镜像拉取密钥

<details>
<summary>显示答案</summary>

**答案：B) 检测到新版本时自动更新 Git 中的镜像标签**

**说明：**
image-reflector-controller 扫描 ImageRepository 的标签并评估 ImagePolicy。image-automation-controller 根据选定结果和 YAML 策略标记修改 Git。两个控制器、Git 写权限和标记都不可缺少。推送到单独的分支时，还需要额外的 PR/合并工作流。

</details>

6. 使用哪个命令在集群上引导安装 FluxCD？
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>显示答案</summary>

**答案：B) flux bootstrap**

**说明：**
`flux bootstrap` 命令会安装 FluxCD 组件，并配置用于管理集群的 Git 仓库。它支持 GitHub、GitLab 和通用 Git 服务器等多种 Git 托管平台。

</details>

7. FluxCD 如何支持多租户？
   - A) 使用类似 ArgoCD 的 Projects
   - B) 使用命名空间隔离和 Kubernetes RBAC
   - C) 不支持多租户
   - D) 使用中央管理员租户

<details>
<summary>显示答案</summary>

**答案：B) 使用命名空间隔离和 Kubernetes RBAC**

**说明：**
Flux 将租户命名空间与 Kubernetes RBAC 结合使用。仅分离命名空间并不足够：还需通过 spec.serviceAccountName 配置身份模拟，并设置控制器的跨命名空间引用限制。

</details>

8. FluxCD 中 Notification Controller 的用途是什么？
   - A) 发送短信
   - B) 处理事件并向外部服务发送告警
   - C) 仅管理 Git webhooks
   - D) 监控 Pod 日志

<details>
<summary>显示答案</summary>

**答案：B) 处理事件并向外部服务发送告警**

**说明：**
Notification Controller 同时处理出站通知（发送到 Slack、Teams 等的 Alerts）和入站 Webhook（Receivers）。外部事件发生时，入站 Webhook 会触发协调。

</details>
