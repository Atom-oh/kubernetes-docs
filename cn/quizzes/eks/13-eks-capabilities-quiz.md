# Amazon EKS 功能测验

> **最后更新**：2026年10月23日

请参阅[源章节](../../eks/13-eks-capabilities.md)，区分实测结果与仅在文档中陈述的内容。

1. EKS 功能中的 Argo CD、kro 和 ACK 控制器运行在哪里？

   - A) 作为 DaemonSet 运行在每个工作节点上
   - B) 作为 Deployment 运行在 `kube-system` 命名空间中
   - C) 运行在 AWS 所有的基础设施上，工作节点上没有 Pod
   - D) 运行在 VPC 中自动创建的 Fargate 配置文件上

<details>
<summary>显示答案</summary>

**答案：C) 运行在 AWS 所有的基础设施上，工作节点上没有 Pod**

这三项功能在工作节点上都没有创建任何 Pod。控制器通过功能角色和 EKS 访问条目调用 API 服务器，因此即使 API 端点仅供私有访问，它们也能正常工作。出于同样的原因，无法通过 `kubectl logs` 查看日志；请使用 Vended Logs。

</details>

---

2. 创建托管 Argo CD 后，如果要立即将 Application 同步到本地集群，需要做什么？

   - A) 什么都不用做；本地集群会自动注册
   - B) 使用 EKS ARN 创建集群 Secret，并在功能角色的访问条目上授予部署权限
   - C) 运行 `argocd cluster add`
   - D) 始终需要 `system:masters`

<details>
<summary>显示答案</summary>

**答案：B) 使用 EKS ARN 创建集群 Secret，并在功能角色的访问条目上授予部署权限**

自动创建的访问条目本身会报错 `podtemplates is forbidden`。Argo CD 会列出每种资源类型来构建缓存，因此仅有 `AmazonEKSEditPolicy` 并不足够；添加 `AmazonEKSAdminViewPolicy` 后，同步才能正常工作。无需 cluster-admin。

</details>

---

3. 如何消除托管 Argo CD 从提交到状态变为 Synced 之间长达数分钟的延迟？

   - A) 将 `argocd-cm` 中的 `timeout.reconciliation` 调低到 30 秒
   - B) 每次都重新创建功能
   - C) 在功能服务器 URL 的 `/api/webhook` 路径注册 GitHub webhook
   - D) 增加节点

<details>
<summary>显示答案</summary>

**答案：C) 在功能服务器 URL 的 `/api/webhook` 路径注册 GitHub webhook**

默认轮询测得的时间为 342–697 秒，而且托管功能上没有可配置的轮询间隔键。使用 webhook 后，同步耗时为 7.0–7.3 秒。服务器 URL 由 AWS 托管，因此无需单独的公共端点。

</details>

---

4. 将 RGD 应用到托管 kro 后，如果看到 `ControllerReady=False` 和 "cache sync timeout"，最可能的原因是什么？

   - A) AWS 侧的控制器发生故障
   - B) `AmazonEKSKROPolicy` 缺少对 RGD 生成的 API 及其子资源的权限
   - C) RGD 中存在 CEL 语法错误
   - D) 节点内存压力

<details>
<summary>显示答案</summary>

**答案：B) `AmazonEKSKROPolicy` 缺少对 RGD 生成的 API 及其子资源的权限**

默认策略仅涵盖 `kro.run` 组和 CRD。由于报错信息不是 "forbidden"，很容易误以为是控制器故障。可在访问条目中添加 Kubernetes 组，为每个 RGD 绑定一个 ClusterRole，并在应用 RGD 之前应用该 ClusterRole；这样就避免了等待（实测为 228 秒，推测是控制器的重试间隔）。

</details>

---

5. 测试中，当 ACK Table CR 已存在，且其名称与 kro 实例的子资源名称相同时，发生了什么？

   - A) kro 拒绝创建该实例
   - B) kro 接管已有 CR 并更改 `spec.tableName`，原有表则变为未受管理状态
   - C) 这只会发生在托管 kro 上，在 OSS 上无法复现
   - D) ACK 自动合并了两个 CR

<details>
<summary>显示答案</summary>

**答案：B) kro 接管已有 CR 并更改 `spec.tableName`，原有表则变为未受管理状态**

kro 使用服务器端 apply 覆盖了该 CR，并为其添加了 `kro.run/owned=true` 标签。删除实例时，被接管的 CR 也会一并删除。OSS 0.9.4 的行为相同，因此这是上游行为。可通过为每个 RGD 使用专属名称后缀并将其放在不同的命名空间中来缓解这一问题。

</details>

---

6. 如何通过托管 ACK 为团队设置不同的 IAM 权限？

   - A) 为每个服务控制器的 ServiceAccount 关联 IRSA
   - B) 仅向功能角色授予 AssumeRole 权限，并使用 `IAMRoleSelector` 将命名空间映射到团队角色
   - C) 启用 CARM，并使用命名空间注释设置账户
   - D) 托管功能无法实现团队间隔离

<details>
<summary>显示答案</summary>

**答案：B) 仅向功能角色授予 AssumeRole 权限，并使用 `IAMRoleSelector` 将命名空间映射到团队角色**

team-b 中的一个 Bucket 使用的角色仅允许 SQS 操作，因此请求失败并返回 `AccessDenied`，且报错信息指出了所用角色。在 OSS 控制器上采用相同设置时，需要同时设置 `featureGates.IAMRoleSelector=true` 和 `enableCARM=false`；如果保持 CARM 启用，就会导致 CrashLoopBackOff。

</details>

---

7. 测试显示，通过 ACK 之外的方式（使用 CLI）更改 SQS 属性后，会发生什么？

   - A) 托管 ACK 总会在一分钟内将其恢复
   - B) 托管 ACK 和 OSS ACK 在 25 分钟内都没有定期将其恢复；只观察到托管 ACK 在看似控制器重启时恢复了更改
   - C) OSS ACK 会通过实时事件立即将其恢复
   - D) 托管同步间隔通过 `disabledServices` 设置

<details>
<summary>显示答案</summary>

**答案：B) 托管 ACK 和 OSS ACK 在 25 分钟内都没有定期将其恢复；只观察到托管 ACK 在看似控制器重启时恢复了更改**

ACK 不会实时监视 AWS 侧的更改。OSS 的默认重新同步间隔为 10 小时，且可以调整；托管版的间隔未公开，且固定不变。如果快速恢复很重要，请使用 SCP 或 IAM 条件阻止带外更改。

</details>

---

8. 关于托管功能控制器版本，哪项陈述正确？

   - A) 可以通过 `create-capability --version` 固定版本
   - B) 回滚集群版本也会回滚功能版本
   - C) AWS 选择并滚动更新版本，版本可能独立于集群升级而变化；可在 `describe-capability` 的 `version` 字段中查看
   - D) 只有升级集群的 Kubernetes 版本时，功能版本才会变化

<details>
<summary>显示答案</summary>

**答案：C) AWS 选择并滚动更新版本，版本可能独立于集群升级而变化；可在 `describe-capability` 的 `version` 字段中查看**

创建和更新 API 都没有版本参数；相隔一天创建的 Argo CD 功能分别报告了 `3.4.6-eks-2` 和 `3.4.7-eks-1`。请记录版本变更，保留一个验证集群，并做好临时回退到基于 RETAIN 的自我管理方案的准备。如果固定版本是硬性要求，请选择自我管理方案。

</details>

---

9. 如果要让中心集群的 Argo CD 功能在仅供私有访问的辐射集群上部署一个设置了 `CreateNamespace=true` 的应用，需要什么？

   - A) Transit Gateway 和入站安全组规则
   - B) 为中心集群的功能角色创建访问条目，并授予 Edit、AdminView 和 `AmazonEKSArgoCDClusterPolicy`
   - C) 为辐射集群创建自己的 Argo CD 功能
   - D) 公共 API 端点

<details>
<summary>显示答案</summary>

**答案：B) 为中心集群的功能角色创建访问条目，并授予 Edit、AdminView 和 `AmazonEKSArgoCDClusterPolicy`**

无需进行任何网络设置，连接和身份验证就能成功，但仅有 Edit 和 AdminView 会报错 `namespaces is forbidden`。中心集群会自动获得此策略；远程集群需要手动附加该策略。自动重试耗尽后，需要手动同步。

</details>

---

10. 在什么情况下，自我管理方案比托管功能更合适？

   - A) 构建一个可向多个私有 EKS 集群部署应用的中心集群
   - B) 组织已通过 Identity Center 集中管理登录
   - C) 依赖 Argo CD Notifications 或 CMP 或 ACK FieldExport，并且还要部署到非 EKS 集群
   - D) 管理多个 AWS 服务，但运行各服务自己的控制器会带来负担

<details>
<summary>显示答案</summary>

**答案：C) 依赖 Argo CD Notifications 或 CMP 或 ACK FieldExport，并且还要部署到非 EKS 集群**

托管功能不支持 Notifications、CMP、`argocd admin`、Lua 标准库和 FieldExport，而且集群 Secret 仅接受 EKS ARN。其他选项都属于托管功能适用的场景。

</details>
