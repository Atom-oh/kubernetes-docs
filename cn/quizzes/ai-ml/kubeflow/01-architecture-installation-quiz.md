# EKS 上的 Kubeflow 架构与安装测验

基线：Community Distribution 26.03.1 / Dashboard 2.0.0 / KFP 2.16.1。

## 单项选择题

1. Kubeflow 于 2026 年 8 月 17 日从 CNCF 毕业确立了什么？

   - A) 每个 EKS 部署都自动合规
   - B) 项目的成熟度与治理水平，包括一次独立的安全审计
   - C) 不再需要任何安全更新
   - D) 无需配置即可保证租户隔离

<details>
<summary>显示答案</summary>

**答案：B) 项目的成熟度与治理水平，包括一次独立的安全审计**

毕业针对的是项目本身。部署安全性、隔离性以及法规合规性仍需各自进行评估。
</details>

2. 本章使用哪个发布基线？

   - A) AWS Kubeflow 1.7 与 Community 26.03.1 完全相同
   - B) Community 26.03.1，其中包含 KFP 2.16.1 与 Dashboard 2.0.0
   - C) 每个组件都使用 26.03.1 版本
   - D) 未固定发布版本的 master 分支

<details>
<summary>显示答案</summary>

**答案：B) Community 26.03.1，其中包含 KFP 2.16.1 与 Dashboard 2.0.0**

发行版版本与组件版本并不相同。社区发布日历计划每年大约两个基础版本，并将支持描述为尽力而为，而非 SLA。
</details>

3. 当省略 Profile 的 resourceQuotaSpec.hard 时会发生什么？

   - A) 控制器设置默认的 GPU 配额
   - B) Istio 提供等效的 CPU 配额
   - C) Profile 控制器不会创建对应的 ResourceQuota
   - D) 该 namespace 获得无限制的 AWS IAM 权限

<details>
<summary>显示答案</summary>

**答案：C) Profile 控制器不会创建对应的 ResourceQuota**

配额是可选的。清空 hard 会移除由控制器管理的配额。RBAC、network policy、存储以及 AWS 访问是各自独立的边界。
</details>

4. 在遵循旧版 AWS 发行版安装指南之前必须检查什么？

   - A) 仅检查仓库近期的活动情况
   - B) dashboard 的 logo 是否有变化
   - C) 该版本是否兼容，以及其所需镜像是否仍然可用
   - D) 是否每个组件都是 CRD

<details>
<summary>显示答案</summary>

**答案：C) 该版本是否兼容，以及其所需镜像是否仍然可用**

所查阅的 v1.7.0-aws-b1.0.3 版本明确警告：已移除的 OIDC 镜像不再可用，会导致新安装失败。它并不是经过验证的 26.03.1 方案。
</details>

5. 关于当前 KFP 的 S3 身份认证，哪一项说法有依据？

   - A) KFPv2 普遍要求使用静态的 IAM 用户密钥
   - B) fromEnv 只接受静态 access key
   - C) 当前指南记录的是 IRSA；实际的 SDK、ServiceAccount 与角色信任关系仍需验证
   - D) Profile 会自动创建 Pod Identity 关联

<details>
<summary>显示答案</summary>

**答案：C) 当前指南记录的是 IRSA；实际的 SDK、ServiceAccount 与角色信任关系仍需验证**

KFP 2.16.1 将 fromEnv 委托给 Go Cloud，其固定的默认实现使用 AWS SDK v2 凭证链。此次源码查阅并不能证明 EKS Pod Identity 部署方式可行。
</details>

6. dashboard 承担什么角色？

   - A) 自动训练并部署每个模型
   - B) 提供指向各组件界面的导航
   - C) 替代所有应用层授权
   - D) 将每个 pipeline 制品存储在 CRD 中

<details>
<summary>显示答案</summary>

**答案：B) 提供指向各组件界面的导航**

工作负载控制器和应用 API 各自执行自身的操作。KFP API 也使用持久化存储；其 Run 与 Experiment 概念并非普遍以 CRD 形式存在。
</details>

## 简答题

7. 在 Dashboard v2 迁移过程中，为什么要保留 Profile 对象及其 CRD？

<details>
<summary>显示答案</summary>

Profile 控制器设置 namespace 的归属关系。删除 Profile 可能会级联删除其 namespace 及相关资源。应按照特定版本的说明清理旧控制器资源，同时不要删除租户的 Profile 或 namespace。
</details>

8. 成功渲染 Profile overlay 能证明什么，还有什么仍未得到验证？

<details>
<summary>显示答案</summary>

它证明所选的 Kustomize 输入能够生成 manifest；所审阅的 overlay 生成了 14 个资源，并使用 Dashboard 2.0.0 镜像。但它并不能证明 API admission、控制器就绪状态、租户隔离，或在 EKS 上的 S3 访问能力。以托管服务进行替换时，同样需要检查身份认证、兼容性、网络、成本与迁移方面的问题。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/01-architecture-installation.md) | [下一测验：Pipelines](02-pipelines-quiz.md)
