# Feature Flags 与 OpenFeature 测验

1. OpenFeature 的 Provider 模型的关键优势是什么？
   - A) Vendor lock-in 可提供最佳性能
   - B) Vendor-neutral API 可自由切换 Feature Flag 后端
   - C) 必须运行自己的 Feature Flag 服务器
   - D) 仅支持 REST API

<details>
<summary>显示答案</summary>

**答案：B) Vendor-neutral API 可自由切换 Feature Flag 后端**

**说明：**
OpenFeature 是一项 CNCF 标准，提供 Vendor-neutral SDK API。通过 Provider 接口，只需更改 Provider 配置，即可在 flagd、LaunchDarkly、Flagsmith 等后端之间切换——无需修改应用程序代码。

</details>

---

2. 在 Kubernetes 上运行 flagd 时，Sidecar 和 Standalone 部署模式有什么区别？
   - A) Sidecar 性能更好，Standalone 更易于管理
   - B) Sidecar 注入到每个 Pod 中以最小化延迟，Standalone 作为中央服务运行
   - C) Sidecar 仅支持 TCP，Standalone 仅支持 HTTP
   - D) Sidecar 使用 CRD，Standalone 仅使用 ConfigMap

<details>
<summary>显示答案</summary>

**答案：B) Sidecar 注入到每个 Pod 中以最小化延迟，Standalone 作为中央服务运行**

**说明：**
在 Sidecar 模式下，OpenFeature Operator 会向每个 Pod 注入一个 flagd 容器，以实现低延迟的本地通信。在 Standalone 模式下，flagd 作为独立的 Deployment 运行并由中央统一管理，资源效率更高，但需要进行网络调用。

</details>

---

3. Feature Flag 的 Evaluation Context 中包含的信息有什么作用？
   - A) 传递构建信息，以便在编译时确定 Flag
   - B) 使用用户 ID、区域和环境等 Context 评估目标规则
   - C) 传递数据库连接信息
   - D) 传递 Kubernetes Node 信息

<details>
<summary>显示答案</summary>

**答案：B) 使用用户 ID、区域和环境等 Context 评估目标规则**

**说明：**
Evaluation Context 是在 Flag 评估期间动态传递的元数据。其中包括用户 ID、区域、环境（dev/staging/prod）和用户组等信息。目标规则使用这些信息为特定用户或组启用功能。

</details>

---

4. 在 Dark Launch 模式中，Feature Flag 的作用是什么？
   - A) 完全隐藏服务并阻止访问
   - B) 部署新功能代码，但通过 Flag 将其禁用，使用户无法看到它
   - C) 将服务器切换到深色模式
   - D) 仅在夜间执行部署

<details>
<summary>显示答案</summary>

**答案：B) 部署新功能代码，但通过 Flag 将其禁用，使用户无法看到它**

**说明：**
Dark Launch 会将新功能代码部署到生产环境，但通过 Feature Flag 使其对用户不可见。随后逐步为一部分用户启用该 Flag 进行测试；如果没有出现问题，再向所有用户推广。这是将部署与发布分离的关键模式。

</details>

---

5. Feature Flag as Code（GitOps）的优势是什么？
   - A) Flag 只能通过 GUI 管理
   - B) 通过 Git PR 管理 Flag 变更，可实现审查、审计和回滚
   - C) Flag 评估会变得更快
   - D) 节省服务器资源

<details>
<summary>显示答案</summary>

**答案：B) 通过 Git PR 管理 Flag 变更，可实现审查、审计和回滚**

**说明：**
Feature Flag as Code 会在 Git 仓库中管理 FeatureFlag CR，并应用基于 PR 的审查和批准流程。变更历史记录在 Git 中以供审计，出现问题时可通过 Git revert 快速回滚。ArgoCD 或 Flux 会自动同步这些变更。

</details>

---

6. 防止 Feature Flag 产生技术债务的最佳实践是什么？
   - A) 永久保留所有 Flag
   - B) 为 Flag 设置过期日期，并在发布完成后清理 Flag 代码
   - C) 不限制数量，随意创建 Flag
   - D) 不要在 Flag 名称中包含日期

<details>
<summary>显示答案</summary>

**答案：B) 为 Flag 设置过期日期，并在发布完成后清理 Flag 代码**

**说明：**
Feature Flag 通常用作临时的发布工具。发布完成后，应清理 Flag 及相关条件代码，以防止技术债务累积。为 Flag 添加过期日期和负责人标签，并运行流程定期检测和移除未使用的 Flag。

</details>

---

7. OpenFeature Operator 在 Kubernetes 上提供的核心功能是什么？
   - A) 自动将 flagd Sidecar 注入 Pod，并管理 FeatureFlag CRD
   - B) 审计 Kubernetes 集群安全性
   - C) 自动构建容器镜像
   - D) 自动配置 HPA

<details>
<summary>显示答案</summary>

**答案：A) 自动将 flagd Sidecar 注入 Pod，并管理 FeatureFlag CRD**

**说明：**
OpenFeature Operator 是用于在 Kubernetes 中原生管理 Feature Flag 的 Operator。它通过 FeatureFlag CRD 以声明式方式管理 Flag，通过 FeatureFlagSource CRD 定义 Flag 源，并自动将 flagd Sidecar 容器注入具有相应注解的 Pod。

</details>

---

8. 在 Flagger + Feature Flag 组合中，基于指标的自动推广如何运作？
   - A) Feature Flag 直接控制流量
   - B) Flagger 负责 Canary 流量迁移，而 Feature Flag 在应用程序层面控制功能的渐进式暴露
   - C) Feature Flag 完全替代 Flagger
   - D) 两种工具使用完全相同的指标

<details>
<summary>显示答案</summary>

**答案：B) Flagger 负责 Canary 流量迁移，而 Feature Flag 在应用程序层面控制功能的渐进式暴露**

**说明：**
Flagger 和 Feature Flag 在不同层级运行。Flagger 在基础设施层面分流，并分析指标来控制部署。Feature Flag 在应用程序层面控制单项功能的启用/禁用。将它们结合使用，可将部署（Flagger）与发布（Feature Flag）完全分离。

</details>
