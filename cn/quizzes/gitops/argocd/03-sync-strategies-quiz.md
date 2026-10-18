# ArgoCD 同步策略测验

本测验用于检验你对 ArgoCD 同步策略和选项的理解。

1. 在 ArgoCD 中，“Sync”和“Refresh”有什么区别？
   - A) 它们是相同的操作
   - B) Refresh 将当前状态与 Git 进行比较；Sync 应用更改以使二者一致
   - C) Sync 是手动的，Refresh 是自动的
   - D) Refresh 删除资源，Sync 创建资源

<details>
<summary>显示答案</summary>

**答案：B) Refresh 将当前状态与 Git 进行比较；Sync 应用更改以使二者一致**

**说明：**
Refresh 操作从 Git 获取最新的清单，并将其与实际状态进行比较，从而更新 Application 状态。Sync 操作会实际将更改应用到集群，使实际状态与 Git 中的期望状态保持一致。

</details>

2. 启用 `automated` 同步策略有什么作用？
   - A) 自动删除应用程序
   - B) 当期望状态与实际状态不同时启用自动同步
   - C) 启用自动回滚
   - D) 自动创建备份

<details>
<summary>显示答案</summary>

**答案：B) 当期望状态与实际状态不同时启用自动同步**

**说明：**
启用 `syncPolicy.automated` 后，Argo CD 会按策略应用处于 OutOfSync 状态的变更。期望状态未变而实际状态发生漂移时，需要 selfHeal；删除资源需要 prune；同一提交同步失败后不会无条件地无限重试。

</details>

3. 自动同步中的 `prune` 选项有什么用途？
   - A) 清理旧的 Git 分支
   - B) 自动删除 Git 中不再定义的资源
   - C) 移除失败的部署
   - D) 删除应用程序本身

<details>
<summary>显示答案</summary>

**答案：B) 自动删除 Git 中不再定义的资源**

**说明：**
在自动同步中设置 `prune: true` 时，Argo CD 会删除属于此 Application、已被跟踪且从期望源中消失的资源，而不是删除集群中所有未受管理的资源。

</details>

4. 同步策略中的 `selfHeal: true` 有什么作用？
   - A) 自动修复 YAML 语法错误
   - B) 当实际状态因手动更改而偏离期望状态时自动同步
   - C) 重启不健康的 Pod
   - D) 修复损坏的 Git 仓库

<details>
<summary>显示答案</summary>

**答案：B) 当实际状态因手动更改而偏离期望状态时自动同步**

**说明：**
启用自动同步后，当期望状态未变而实际状态发生漂移时，selfHeal 会根据比较结果进行协调，但仍受同步窗口、授权和忽略规则的约束。它不会恢复丢失的数据，也不会修复 YAML 错误。

</details>

5. 若要替换资源而不是应用补丁，应使用哪个同步选项？
   - A) Force=true
   - B) Replace=true
   - C) Recreate=true
   - D) Update=true

<details>
<summary>显示答案</summary>

**答案：B) Replace=true**

**说明：**
`Replace=true` 同步选项会告知 ArgoCD 使用 `kubectl replace` 而不是 `kubectl apply`，从而完全替换资源，而非对其应用补丁。replace/create 不会自动绕过不可变字段限制。Force=true 与 Replace=true 配合使用时可能删除并重建资源，这并不是 PVC 迁移的捷径。

</details>
