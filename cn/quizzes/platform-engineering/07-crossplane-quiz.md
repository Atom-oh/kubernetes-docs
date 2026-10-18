# Crossplane 测验

[Crossplane](../../platform-engineering/07-crossplane.md)

以下八个主题已根据 Crossplane 2.4 重新核对。

## 1. Composition 提供什么？

<details>
<summary>显示答案</summary>

Function 流水线会把 XR 的输入映射为期望资源。它不会让多个 AWS 操作成为原子事务，也不保证这些资源已经就绪。

</details>

## 2. v2 XR 与旧版 Claim 有什么区别？

<details>
<summary>显示答案</summary>

XRD v2 默认使用 Namespaced 范围，用户可以直接创建 XR。旧版 v1 `LegacyCluster` XRD 仍使用集群范围的 XR 和命名空间范围的 Claim。当前并非所有 XR/MR 都是集群范围。

</details>

## 3. 选择 IRSA 或 Pod Identity 是否就实现了最小权限？

<details>
<summary>显示答案</summary>

不是。还要配置 ServiceAccount、OIDC audience/subject 或 Pod Identity association，以及角色策略。也要限制运行时所有权、ProviderConfig 访问权限和 AssumeRole 边界。

</details>

## 4. Terraform 与 Crossplane 的主要区别是什么？

<details>
<summary>显示答案</summary>

两者都围绕声明式状态工作；Terraform 以 plan/apply 工作流为中心，Crossplane 则以持续协调为中心。Terraform 也可以自动化；Crossplane 同样受 Provider 支持范围、策略、配额和错误的限制。

</details>

## 5. ACK 与 Crossplane 如何共存？

<details>
<summary>显示答案</summary>

应分别明确外部资源的所有权。ACK 还提供命名空间范围的 CR 和引用，并可与 kro 组合使用。不要让多个控制器争相修改同一个 AWS 资源。

</details>

## 6. v2 如何提供连接 Secret？

<details>
<summary>显示答案</summary>

MR 上仍可使用 `writeConnectionSecretToRef`，但已移除核心内置的 XR Secret 发布功能。可以组合出一个 Secret，或使用受支持的 Function 聚合信息。示例只聚合 endpoint 和 username，password 则来自事先准备好的独立 Secret。

</details>

## 7. Backstage/GitOps 工作流是什么？

<details>
<summary>显示答案</summary>

使用预先准备的模板骨架和 action 渲染 XR YAML，提交经审查的 PR，再通过 ArgoCD 和 Crossplane/Provider 进行协调，最后验证资源是否实际就绪。创建 PR、注册目录项和完成 AWS 资源预置是不同的状态。

</details>

## 8. 哪些设置控制漂移修正和资源保留？

<details>
<summary>显示答案</summary>

检查 Provider 支持的字段、`managementPolicies` 和轮询设置。v2 命名空间范围的 MR 可通过不包含 `Delete` 来保留外部资源；这与旧版 `deletionPolicy: Orphan` 不同。保留资源后，仍须负责备份、凭证、成本和所有权管理。

</details>
