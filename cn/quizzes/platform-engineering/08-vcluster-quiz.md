# vCluster 测验

1. vCluster 相比传统基于 Namespace 的多租户方式有什么优势？
   - A) vCluster 会创建额外的物理集群
   - B) 在共享宿主集群资源的同时，为每个租户提供完整的 Kubernetes API
   - C) vCluster 会完全隔离网络
   - D) vCluster 需要专用节点

<details>
<summary>查看答案</summary>

**答案：B) 在共享宿主集群资源的同时，为每个租户提供完整的 Kubernetes API**

**解释：**
vCluster 通过虚拟控制平面为每个租户提供独立的 Kubernetes API（安装 CRD、管理 RBAC、创建 Namespace 等）。实际工作负载运行在宿主集群上，在不增加额外物理集群成本的情况下提供强隔离。

</details>

---

2. vCluster 的 Syncer 组件的核心作用是什么？
   - A) 管理虚拟集群 DNS
   - B) 将虚拟集群资源同步到宿主集群，并将宿主状态反映回来
   - C) 连接虚拟集群之间的网络
   - D) 收集虚拟集群日志

<details>
<summary>查看答案</summary>

**答案：B) 将虚拟集群资源同步到宿主集群，并将宿主状态反映回来**

**解释：**
Syncer 是 vCluster 的核心组件，它会将在虚拟集群中创建的资源（Pods、Services、ConfigMaps 等）转换为宿主集群上的实际资源。它还会将宿主信息（Nodes、StorageClasses 等）同步回虚拟集群，从而执行双向资源管理。

</details>

---

3. 使用 vCluster 创建每个 PR 的预览环境有什么优势？
   - A) 无需合并 PR 即可将代码部署到生产环境
   - B) 为每个 PR 快速创建/删除隔离的 Kubernetes 环境，以进行集成测试
   - C) 向 PR 审阅者授予 cluster admin 权限
   - D) 减少 CI 流水线执行时间

<details>
<summary>查看答案</summary>

**答案：B) 为每个 PR 快速创建/删除隔离的 Kubernetes 环境，以进行集成测试**

**解释：**
vCluster 可以在 30 秒内创建，使 CI/CD 流水线能够为每个 PR 预置隔离的 Kubernetes 环境。当 PR 被合并或关闭时，会删除 vCluster 以回收资源，从而可以在独立环境中对每个 PR 的变更进行集成测试。

</details>

---

4. vCluster 的 Sleep Mode 功能的目的是什么？
   - A) 增强虚拟集群安全性
   - B) 释放未使用虚拟集群的资源以降低成本
   - C) 备份虚拟集群数据
   - D) 优化虚拟集群性能

<details>
<summary>查看答案</summary>

**答案：B) 释放未使用虚拟集群的资源以降低成本**

**解释：**
Sleep Mode 会自动停止在指定时间段内处于非活动状态的 vCluster 中的工作负载。当收到 API 请求时，vCluster 会自动唤醒。这可以显著降低夜间和周末未使用的开发/测试 vCluster 的成本。

</details>

---

5. 如何在虚拟集群中使用宿主集群的 StorageClass？
   - A) 在虚拟集群中重新创建 StorageClass
   - B) 使用 syncFromHost 设置将宿主的 StorageClass 同步到虚拟集群
   - C) 手动挂载 PV
   - D) 在虚拟集群中单独安装 CSI drivers

<details>
<summary>查看答案</summary>

**答案：B) 使用 syncFromHost 设置将宿主的 StorageClass 同步到虚拟集群**

**解释：**
vCluster 的 `syncFromHost` 配置会同步宿主集群资源，例如 StorageClasses、IngressClasses 和 Nodes，使它们在虚拟集群中可见。虚拟集群中的 PVCs 使用宿主集群的 StorageClasses 来预置实际的 PVs。

</details>

---

6. 在 Backstage + vCluster 集成中，开发者自助服务工作流是如何运作的？
   - A) 开发者直接使用 kubectl 创建 vClusters
   - B) Backstage Template 生成 vCluster 请求 → 推送到 GitOps repo → ArgoCD 同步以预置 vCluster
   - C) Backstage 直接调用 Kubernetes API 创建 vClusters
   - D) Admins 手动创建 vClusters 并分配给开发者

<details>
<summary>查看答案</summary>

**答案：B) Backstage Template 生成 vCluster 请求 → 推送到 GitOps repo → ArgoCD 同步以预置 vCluster**

**解释：**
当开发者在 Backstage Template 中输入参数（环境名称、资源大小等）时，Template 会生成 vCluster Helm Release manifests 并将其推送到 GitOps repository。ArgoCD 检测到变更后会将其同步到集群，从而自动预置 vCluster。

</details>

---

7. NetworkPolicy 在 vCluster 安全隔离中的作用是什么？
   - A) 限制虚拟集群之间的 CPU 使用量
   - B) 通过网络隔离，防止虚拟集群 Pods 访问其他 vCluster Pods 或宿主集群资源
   - C) 加密虚拟集群的 Ingress 流量
   - D) 过滤 DNS 查询

<details>
<summary>查看答案</summary>

**答案：B) 通过网络隔离，防止虚拟集群 Pods 访问其他 vCluster Pods 或宿主集群资源**

**解释：**
由于 vCluster Pods 运行在宿主集群上，如果没有 NetworkPolicies，它们可以通过网络访问其他 vCluster 中的 Pods。对每个 vCluster 的 namespace 应用 NetworkPolicies，仅允许 namespace 内通信并阻止外部访问，可以实现强网络隔离。

</details>

---

8. 什么时候应该选择 vCluster 而不是物理集群？
   - A) 当需要完整硬件隔离时
   - B) 当需要快速预置、成本效率和 CRD 隔离，但不需要完整节点隔离时
   - C) 当法规要求强制使用单独的 AWS 账户时
   - D) 当运行 GPU 工作负载时

<details>
<summary>查看答案</summary>

**答案：B) 当需要快速预置、成本效率和 CRD 隔离，但不需要完整节点隔离时**

**解释：**
vCluster 提供 30 秒内创建、通过共享宿主集群资源实现成本效率，以及 CRD/RBAC/Namespace 隔离。它非常适合开发/测试环境、CI/CD 临时环境和培训环境。对于需要法规合规、完整硬件隔离或专用网络隔离的生产工作负载，物理集群更合适。

</details>
