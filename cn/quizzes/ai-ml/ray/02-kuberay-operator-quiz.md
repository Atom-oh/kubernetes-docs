# KubeRay Operator 测验

## 选择题

1. 安装 KubeRay operator 会启动什么？
   - A) 自动启动每个 Ray workload
   - B) 启动 reconciler；仍需要创建 workload CR
   - C) 启动每个 GPU 节点
   - D) 为每个 worker 创建一个 Deployment

<details>
<summary>显示答案</summary>

**答案：B**

Operator 的安装与创建 RayCluster、RayJob 或 RayService 资源是相互独立的。
</details>

2. chart 1.7.0 会安装什么，以及 RayCronJob 的默认状态是什么？
   - A) 仅存在三个 CRD
   - B) 已安装的 RayCronJob CRD 始终启用调度
   - C) 四个 CRD，且 RayCronJob feature gate 默认禁用
   - D) 不存在 v1 API

<details>
<summary>显示答案</summary>

**答案：C**

区分 RayCluster、RayJob、RayService 和 RayCronJob。
</details>

3. RayJob 的默认清理行为是什么？
   - A) 省略 shutdownAfterJobFinishes 会启用清理
   - B) TTL 0 会删除每个 EC2 实例和 PVC
   - C) shutdownAfterJobFinishes 默认为 false；请配置清理和保留策略
   - D) 外部集群始终会被删除

<details>
<summary>显示答案</summary>

**答案：C**

检查 TTL、deletionStrategy，以及共享集群和已创建集群的所有权。
</details>

4. RayService 增量升级需要什么？
   - A) 仅凭 feature gate 即可保证无停机
   - B) Strategy、Gateway API/implementation、容量、就绪状态和流量排空
   - C) 仅编辑一个现有 Pod 镜像
   - D) 必须使用 RayJob

<details>
<summary>显示答案</summary>

**答案：B**

它会在集群之间转移流量；这并不只是原地进行 Pod 滚动更新。
</details>

5. 哪种扩缩容顺序是合适的？
   - A) Ray autoscaler 直接预置所有 EC2 容量
   - B) Ray 需求 → KubeRay Pod reconciliation → Kubernetes 调度/容量预置
   - C) Karpenter 调用 Ray actor 方法
   - D) 两个 controller 共同拥有完全相同的资源

<details>
<summary>显示答案</summary>

**答案：B**

与镜像、PVC 或授权相关的 Pending 状态并不能仅通过添加节点来解决。
</details>

6. 应如何理解 idleTimeoutSeconds 60？
   - A) 每个 worker 会在恰好 60 秒后消失
   - B) 应审查全局默认值；考虑 group 覆盖、边界、活动情况和排空条件
   - C) 整个 RayJob 的 TTL
   - D) Karpenter 的固定预置时间

<details>
<summary>显示答案</summary>

**答案：B**

配置的持续时间与实际完成删除的时间并不相同。
</details>

7. 关于 GPU 资源优先级，哪项说法准确？
   - A) 仅使用 Pod limits；忽略 overrides
   - B) 结构化 group resources 和 rayStartParams 可以覆盖 limits
   - C) 每个 Pod 始终拥有一个 GPU
   - D) 逻辑设置会创建更多物理 GPU

<details>
<summary>显示答案</summary>

**答案：B**

使 Ray 逻辑资源与 device plugins、drivers 和可见硬件保持一致。
</details>

8. Helm chart 升级会自动更新现有 CRD schema 吗？
   - A) 它始终会升级并删除它们
   - B) 不会；请检查已存储 CR 的兼容性以及单独的 CRD 更新流程
   - C) CRD 是普通 Pod
   - D) 先删除 CRD 始终是安全的

<details>
<summary>显示答案</summary>

**答案：B**

了解 Helm crds/ 生命周期限制以及删除 CRD 的影响。
</details>

## 简答题

9. 为什么 worker replica 数量和 Ray Pod 数量并不总是相等？

<details>
<summary>显示答案</summary>

使用 numOfHosts 时，一个 group replica 可以对应多个 host/Pod。请比较实际 spec 与生成的资源。
</details>

10. 为什么启用 Ray token authentication 并不代表安全配置已完成？

<details>
<summary>显示答案</summary>

它独立于 TLS，且不能替代对每个应用程序 endpoint 的 authentication/authorization。请审查访问路径、secret 交付、版本支持和组织策略。
</details>

---

[返回学习资料](../../../ai-ml/ray/02-kuberay-operator.md)
