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
启用 `syncPolicy.automated` 后，每当 ArgoCD 检测到实际状态偏离 Git 中定义的期望状态时，都会自动同步应用程序。

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
在自动同步中设置 `prune: true` 时，ArgoCD 会自动删除集群中存在但 Git 仓库中不再定义的 Kubernetes 资源。

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
自我修复可确保如果有人在集群中（Git 之外）手动更改资源，ArgoCD 会自动将其还原，使之与 Git 中的期望状态一致。

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
`Replace=true` 同步选项会告知 ArgoCD 使用 `kubectl replace` 而不是 `kubectl apply`，从而完全替换资源，而非对其应用补丁。这在处理不可变字段时非常有用。

</details>
