# Backstage IDP 测验

[Backstage](../../platform-engineering/06-backstage-idp.md)

最初的八个主题已更新为面向 Backstage 1.54.7 的复习内容。

## 1. 哪种 catalog（目录）kind 代表一个微服务？

<details>
<summary>显示答案</summary>

Component，其 spec.type 为 service 之类的值。catalog 中的 Resource 用于描述基础设施；它并不是用来置备 AWS 资源的控制器。

</details>

## 2. Software Template 实际会创建什么？

<details>
<summary>显示答案</summary>

只会创建由已注册的 actions 和所提供的 skeletons 实现的文件与外部操作。指南中的小示例创建了三个 catalog/TechDocs 文件，而不是应用运行时或数据库。Golden path（黄金路径）并不能替代授权或强制性策略。

</details>

## 3. Kubernetes 工作负载如何与 catalog 实体进行匹配？

<details>
<summary>显示答案</summary>

将 backstage.io/kubernetes-id 或受支持的 label-selector 注解与实际的工作负载标签相匹配。此外还需要 Namespace/集群的选择、凭证以及 RBAC。元数据匹配并不等同于按用户的授权。

</details>

## 4. 在 EKS 上应如何准备 PostgreSQL 和 secrets？

<details>
<summary>显示答案</summary>

当选择 RDS 等外部 PostgreSQL 时，应禁用内置数据库，并配置 TLS、网络、schema、迁移和备份。使用经过批准的 secret 文件挂载，并保持 $file 路径一致。仅有托管数据库并不足以完成 HA/恢复验证。

</details>

## 5. TechDocs 是如何构建和提供服务的？

<details>
<summary>显示答案</summary>

使用 MkDocs 和 techdocs-core。采用外部构建器时，由 CI 发布到 S3 等存储，Backstage 后端再读取它以供 UI 使用。需要对齐实体键/根路径，并分离 publisher 与 reader 的权限；无需公开开放存储桶的访问。

</details>

## 6. 在渐进式采用过程中应当建立什么？

<details>
<summary>显示答案</summary>

先从一个小而准确的 catalog 以及可信的所有权/来源开始，然后再扩展 templates 和 TechDocs。认证、授权和信任边界应从一开始就建立起来。

</details>

## 7. 是什么将 GitHub 发布与 ArgoCD actions 连接起来？

<details>
<summary>显示答案</summary>

注册 action 模块，并配置凭证、权限以及真实的输入/输出 schema。Roadie 1.8.1 的 argocd:create-resources 接受部署 namespace，且没有 revision 输入。不要在刚刚为尚未合并的 PR 开启之后，就立即注册 main 分支上的 catalog 文件。

</details>

## 8. 如何按所有权限制 catalog 的删除操作？

<details>
<summary>显示答案</summary>

注册一个真实的 PermissionPolicy 模块，对 catalog 删除返回 IS_ENTITY_OWNER 条件，并让 catalog 后端来对其进行评估。该示例在没有显式授权的情况下会拒绝操作。catalog 所有权、GitHub 写入权限和 ArgoCD 部署权限是相互独立的；同时也要保护 Group/User 的来源。

</details>
