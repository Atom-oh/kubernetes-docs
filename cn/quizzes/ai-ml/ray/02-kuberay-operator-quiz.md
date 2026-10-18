# KubeRay Operator 测验

## 选择题

1. 安装 KubeRay operator 会启动什么？
   - A) 自动启动每个 Ray 工作负载
   - B) Reconciler；仍需创建工作负载 CR
   - C) 每个 GPU 节点
   - D) 为每个 worker 创建一个 Deployment

<details>
<summary>显示答案</summary>

**答案：B**

安装 Operator 与创建 RayCluster、RayJob 或 RayService 资源是分开的。
</details>

2. chart 1.7.1 会安装什么？RayCronJob 的默认状态是什么？
   - A) 只存在三个 CRD
   - B) 已安装的 RayCronJob CRD 始终会启用调度
   - C) 四个 CRD，且 RayCronJob 功能门默认处于禁用状态
   - D) 不存在 v1 API

<details>
<summary>显示答案</summary>

**答案：C**

请区分 RayCluster、RayJob、RayService 和 RayCronJob。
</details>

3. RayJob 的默认清理行为是什么？
   - A) 省略 shutdownAfterJobFinishes 会启用清理
   - B) TTL 0 会删除所有 EC2 实例和 PVC
   - C) shutdownAfterJobFinishes 默认为 false；需配置清理和保留策略
   - D) 外部集群总是会被删除

<details>
<summary>显示答案</summary>

**答案：C**

检查 TTL、deletionStrategy，以及共享集群与创建的集群分别由谁所有。
</details>

4. RayService 增量升级需要什么？
   - A) 仅启用功能门就能保证零停机
   - B) 策略、Gateway API/实现、容量、就绪状态和连接排空
   - C) 只需编辑一个现有 Pod 的镜像
   - D) 必须使用 RayJob

<details>
<summary>显示答案</summary>

**答案：B**

它会在集群之间转移流量；并非简单的原地 Pod 滚动更新。
</details>

5. 哪种扩缩容顺序是合适的？
   - A) Ray autoscaler 直接配置所有 EC2 容量
   - B) Ray 需求 → KubeRay Pod 调和 → Kubernetes 放置/容量配置
   - C) Karpenter 调用 Ray actor 方法
   - D) 两个控制器共同管理完全相同的资源

<details>
<summary>显示答案</summary>

**答案：B**

仅添加节点无法解决由镜像、PVC 或授权相关问题导致的 Pending 状态。
</details>

6. 应如何理解 idleTimeoutSeconds 60？
   - A) 每个 worker 都会在恰好 60 秒后消失
   - B) 经审查的全局默认值；还需考虑组级覆盖、上下限、活动状态和排空条件
   - C) 整个 RayJob 的 TTL
   - D) Karpenter 固定的配置时间

<details>
<summary>显示答案</summary>

**答案：B**

配置的持续时间与实际完成删除的时间并不相同。
</details>

7. 关于 GPU 资源优先级，哪项说法准确？
   - A) 只使用 Pod limits；忽略覆盖设置
   - B) 结构化组资源和 rayStartParams 可以覆盖 limits
   - C) 每个 Pod 始终都有一个 GPU
   - D) 逻辑设置会创建更多物理 GPU

<details>
<summary>显示答案</summary>

**答案：B**

确保 Ray 逻辑资源与设备插件、驱动程序和可见硬件相匹配。
</details>

8. Helm chart 升级会自动更新现有 CRD schema 吗？
   - A) 它总会升级并删除这些 schema
   - B) 不会；检查已存储 CR 的兼容性以及单独的 CRD 更新流程
   - C) CRD 是普通的 Pod
   - D) 始终先删除 CRD 是安全的

<details>
<summary>显示答案</summary>

**答案：B**

了解 Helm crds/ 的生命周期限制以及删除 CRD 的影响。
</details>

## 简答题

9. 为什么 worker 副本数与 Ray Pod 数量不总是相同？

<details>
<summary>显示答案</summary>

使用 numOfHosts 时，一个组副本可能对应多个主机/Pod。请对照实际 spec 与生成的资源。
</details>

10. 为什么启用 Ray token 身份验证并不意味着安全配置已完成？

<details>
<summary>显示答案</summary>

它与 TLS 是分开的，也不能取代对每个应用端点的身份验证/授权。请检查访问路径、密钥交付、版本支持和组织策略。
</details>

---

[返回学习资料](../../../ai-ml/ray/02-kuberay-operator.md)
