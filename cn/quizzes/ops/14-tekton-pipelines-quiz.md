# Tekton Pipelines 测验

1. 哪项正确描述了 Task、TaskRun 和 Workspace？
   - A) Task 定义本身就是一个正在运行的 Pod
   - B) TaskRun 执行一个 Task；Workspace 是一个卷绑定字段
   - C) Workspace 始终是一个独立的 CRD
   - D) 同一 Pod 中的 Steps 彼此完全隔离

<details>
<summary>显示答案</summary>

**答案：B) TaskRun 执行一个 Task；Workspace 是一个卷绑定字段**

Tasks/Pipelines 是定义，Runs 是执行过程。同一 Pod 中的 Steps 共享网络和卷，因此它们不是信任边界。

</details>

---

2. 在 TaskRuns 之间共享源代码时，哪项正确？
   - A) emptyDir 会在多个 Pod 之间共享相同的文件
   - B) 可以使用每次运行专属的 PVC；RWO/RWX 本身不是信任边界
   - C) 使用不同的 subPaths，就能安全地让外部 PR 和发布共用一个 PVC
   - D) Results 始终是无限长度的字符串

<details>
<summary>显示答案</summary>

**答案：B) 可以使用每次运行专属的 PVC；RWO/RWX 本身不是信任边界**

使用 volumeClaimTemplate 为每次运行提供存储，并在不同信任级别之间隔离可写数据。小型值使用 Results，大型报告使用制品存储。

</details>

---

3. GitHub HMAC 验证通过后，应如何处理外部 PR？
   - A) 使用发布流水线的 IRSA 和签名权限
   - B) 使用权限受限的独立执行信任级别
   - C) 由于 HMAC 验证通过，直接将其 shell 命令插入脚本
   - D) 已验证的请求始终是来自 main 分支的推送

<details>
<summary>显示答案</summary>

**答案：B) 使用权限受限的独立执行信任级别**

HMAC 验证的是交付来源，而非代码是否有权部署。本章中具有特权的 CI 路径仅限于获准仓库受保护的 main 分支推送。

</details>

---

4. Chains 的 slsa/v1 格式化器会生成哪个版本的来源证明？
   - A) SLSA 来源证明 v1.0
   - B) SLSA 来源证明 v0.2；v1.0 使用 slsa/v2alpha3 或 slsa/v2alpha4
   - C) 签名密钥会自动选择任意版本
   - D) 始终与 Kubernetes v1 API 版本相同

<details>
<summary>显示答案</summary>

**答案：B) SLSA 来源证明 v0.2；v1.0 使用 slsa/v2alpha3 或 slsa/v2alpha4**

格式化器名称与 SLSA 规范版本并不相同。Pipeline 级别的来源证明会在 Pipeline 完成后创建，并且需要单独进行验证/晋级。

</details>

---

5. 关于 finally Tasks，哪项说法正确？
   - A) 遇到任何错误、取消和超时时，它们都会执行
   - B) 它们会在普通 Tasks 之后运行，但缺少 Results、取消或超时可能导致它们被跳过/无法执行
   - C) 它们始终按声明顺序依次执行
   - D) 它们会自动为缺失的 image Results 提供默认值

<details>
<summary>显示答案</summary>

**答案：B) 它们会在普通 Tasks 之后运行，但缺少 Results、取消或超时可能导致它们被跳过/无法执行**

最终报告只引用运行名称和 tasks.status。不要假设 finally Tasks 之间存在执行顺序；应考虑超时行为。

</details>

---

6. CI 成功并观察到 chains.tekton.dev/signed=true 后，还需要做什么？
   - A) 立即将任意标签部署到生产环境
   - B) 验证可信密钥、摘要、构建器和源代码来源证明，然后审核 GitOps 变更
   - C) 只需对签名 JSON 进行 base64 解码，无需验证
   - D) 检查 ArgoCD 本身是否拉取了应用镜像

<details>
<summary>显示答案</summary>

**答案：B) 验证可信密钥、摘要、构建器和源代码来源证明，然后审核 GitOps 变更**

签名注解不等于经过密码学验证或批准。ArgoCD 同步清单；kubelet/运行时负责拉取镜像。

</details>

---

7. 在 Pipelines 1.17 中，控制器的 ServiceMonitor 端口和计数器分别是什么？
   - A) metrics / pipelinerun_count
   - B) http-metrics / tekton_pipelines_controller_pipelinerun_total
   - C) http / 每个命名空间的自动计数器
   - D) 9097 / 运行时长直方图

<details>
<summary>显示答案</summary>

**答案：B) http-metrics / tekton_pipelines_controller_pipelinerun_total**

请匹配实际的 Service 标签/端口和 Prometheus 选择器。当前的完成计数器仅包含状态，不包含命名空间标签。

</details>

---

8. 对于 coschedule=workspaces 的 volumeClaimTemplate PVC，默认的完成后行为是什么？
   - A) 始终立即删除
   - B) 保留；可以使用值精确为 true 的自动清理注解，在完成后清理
   - C) 用户预先提供的 PVC 也始终会被删除
   - D) PipelineRuns 默认有七天的 TTL

<details>
<summary>显示答案</summary>

**答案：B) 保留；可以使用值精确为 true 的自动清理注解，在完成后清理**

其他 coschedule 模式和预先存在的 PVC 有不同的生命周期。在删除运行记录前，请检查完成时间、保留策略以及日志/签名归档。

</details>
