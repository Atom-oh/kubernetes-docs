# Tekton Pipelines 测验

1. 与 Jenkins 或 GitHub Actions 相比，Tekton 在 Kubernetes 环境中有什么优势？
   - A) Tekton 提供更多插件
   - B) 基于 CRD 的 pipelines 作为 Kubernetes resources 进行管理，从而支持 GitOps、RBAC 和 namespace 隔离
   - C) Tekton 提供更快的执行速度
   - D) Tekton 是免费的，而其他工具是付费的

<details>
<summary>显示答案</summary>

**答案：B) 基于 CRD 的 pipelines 作为 Kubernetes resources 进行管理，从而支持 GitOps、RBAC 和 namespace 隔离**

**解释：**
Tekton 将 Tasks、Pipelines 和 PipelineRuns 定义为 Kubernetes CRDs。这支持在 Git 中进行声明式 pipeline 管理（GitOps）、通过 Kubernetes RBAC 进行访问控制、namespace 级别隔离，以及通过 kubectl 进行管理。每个 Step 都在单独的 container 中运行，以实现强隔离。

</details>

---

2. 如何在 Tekton Pipeline 中的 Tasks 之间共享数据？
   - A) 通过 environment variables 传递
   - B) 通过 Workspaces (PVC) 共享 file systems，并通过 Results 传递小型数据
   - C) 存储在 ConfigMaps 中
   - D) Tasks 之间进行直接 network communication

<details>
<summary>显示答案</summary>

**答案：B) 通过 Workspaces (PVC) 共享 file systems，并通过 Results 传递小型数据**

**解释：**
Workspaces 是基于 PVC 的 Tasks 之间 file system 共享方式，非常适合先 clone source code 再 build 之类的模式。Results 用于在 Tasks 之间传递小型 string 数据（image tags、commit SHAs 等），引用方式为 `$(tasks.task-name.results.result-name)`。

</details>

---

3. Tekton Triggers 的 EventListener 做什么？
   - A) 生成 events 并将它们发送到 external systems
   - B) 接收 webhook requests，并通过 TriggerBinding/TriggerTemplate 自动创建 PipelineRuns
   - C) 监控 pipeline 执行结果
   - D) 定期轮询 Git repositories

<details>
<summary>显示答案</summary>

**答案：B) 接收 webhook requests，并通过 TriggerBinding/TriggerTemplate 自动创建 PipelineRuns**

**解释：**
EventListener 是一个 HTTP endpoint，用于接收 webhook requests（GitHub Push、PR events 等）。Interceptors 会验证/过滤 request，TriggerBinding 从 payload 中提取 parameters，TriggerTemplate 使用这些 parameters 创建 PipelineRun。

</details>

---

4. Tekton Chains 提供了什么 Supply Chain Security 功能？
   - A) 扫描 container images 中的 vulnerabilities
   - B) 自动签名 TaskRun/PipelineRun artifacts（images）并生成 SLSA Provenance
   - C) 加密 network traffic
   - D) 自动生成 RBAC policies

<details>
<summary>显示答案</summary>

**答案：B) 自动签名 TaskRun/PipelineRun artifacts（images）并生成 SLSA Provenance**

**解释：**
Tekton Chains 会在 TaskRun 完成后，使用 Cosign/Sigstore 自动签名 OCI images，并生成 SLSA Provenance（build metadata、source information、build steps 等）。这可以增强 software supply chain security，并支持验证 image 的来源和完整性。

</details>

---

5. Tekton Pipeline 中 `finally` Tasks 的用途是什么？
   - A) 作为 pipeline 中的第一个 Task 执行
   - B) 无论 pipeline 成功还是失败，始终最后运行的 cleanup tasks
   - C) 条件执行的 Tasks
   - D) 并行运行的 Tasks

<details>
<summary>显示答案</summary>

**答案：B) 无论 pipeline 成功还是失败，始终最后运行的 cleanup tasks**

**解释：**
`finally` Tasks 会在 pipeline 中所有其他 Tasks 完成后运行，无论成功还是失败。由于它们即使在 build 失败时也会执行，因此非常适合 temporary resource cleanup、发送 notifications 和 test result reporting。类似于 try-catch-finally 模式。

</details>

---

6. 为什么在 ArgoCD + Tekton 集成架构中要分离 CI/CD？
   - A) 因为 Tekton 不支持 CD
   - B) 分离 CI（build/test）和 CD（deploy）关注点可以提升 security、auditing 和 rollback
   - C) 因为 ArgoCD 不支持 CI
   - D) 因为这些工具的 licenses 不同

<details>
<summary>显示答案</summary>

**答案：B) 分离 CI（build/test）和 CD（deploy）关注点可以提升 security、auditing 和 rollback**

**解释：**
Tekton 处理 CI（source clone、test、build、image push），而 ArgoCD 处理 CD（基于 Git 的声明式 deployment）。CI 将 image tag 提交到 Git，ArgoCD 检测到此 change 后进行 deploy。这支持 deployment permission 分离、基于 Git 的 audit trails，以及声明式 rollback。

</details>

---

7. Tekton 中 CEL Interceptor 的一个 use case 是什么？
   - A) 验证 GitHub signatures
   - B) 使用 CEL expressions（特定 branches、file paths 等）过滤和转换 webhook payloads
   - C) 验证 GitLab tokens
   - D) 处理 Bitbucket events

<details>
<summary>显示答案</summary>

**答案：B) 使用 CEL expressions（特定 branches、file paths 等）过滤和转换 webhook payloads**

**解释：**
CEL（Common Expression Language）Interceptor 使用 CEL expressions 对 webhook payloads 进行过滤和转换。例如，`body.ref == 'refs/heads/main'` 只过滤 main branch pushes，或者 `body.commits.exists(c, c.modified.exists(f, f.startsWith('src/')))` 仅在特定 path 变更时触发。

</details>

---

8. Tekton PipelineRuns 的适当 cleanup strategy 是什么？
   - A) 永久保留所有 PipelineRuns
   - B) 设置基于 TTL 的 auto-deletion，并为 success/failure 使用不同 retention periods 来管理 resources
   - C) 仅手动删除
   - D) PipelineRuns 会自动删除

<details>
<summary>显示答案</summary>

**答案：B) 设置基于 TTL 的 auto-deletion，并为 success/failure 使用不同 retention periods 来管理 resources**

**解释：**
PipelineRuns 和 TaskRuns 在执行后会保留在 etcd 中并消耗 storage。使用 Tekton 的 cleanup settings（`keep`、`keep-since`）或基于 CronJob 的 cleanup scripts 来自动删除旧的 execution records。Failed runs 通常会保留更长时间，以便 debugging。

</details>
