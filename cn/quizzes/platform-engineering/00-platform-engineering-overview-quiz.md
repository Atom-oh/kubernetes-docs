# Platform Engineering 概述测验

[相关指南](../../platform-engineering/00-platform-engineering-overview.md)

## 1. Platform Engineering 的核心目标是什么？

<details>
<summary>答案与说明</summary>

理解开发人员需求，并将经过批准的自助式 API、CLI、门户、模板和运维支持作为内部产品提供。它不会消除运维团队，也不假定每个应用程序的所有责任都由平台承担。
</details>

## 2. 应如何理解 Start、Advance、Excel 和工具映射？

<details>
<summary>答案与说明</summary>

它们用于组织 AWS Platform Engineering 指南中的改进任务。Advance 涵盖 IaC/自助式自动化；本指南中的 Kubernetes 映射是教学示例，而非官方认证分数或通用的实施顺序。
</details>

## 3. Platform Engineering、DevOps 和 SRE 之间有什么关系？

<details>
<summary>答案与说明</summary>

它们是互补的：平台侧重于开发人员体验和可复用产品，DevOps 侧重于协作和交付，SRE 侧重于可靠性和运维工程。团队结构和层级并非放之四海皆准。
</details>

## 4. IDP 的层次以及 Backstage 门户的范围是什么？

<details>
<summary>答案与说明</summary>

界面、编排、资源和基础设施构成一个参考模型。Backstage 风格的门户属于界面的一部分，而不是预置、策略、运行时、文档和支持的替代品。
</details>

## 5. 偏离 Golden Path 能否绕过强制性安全策略？

<details>
<summary>答案与说明</summary>

不能。它是一条受支持的推荐路径，但例外情况仍须遵循组织审批和强制性的安全/数据策略。它并不保证对每种情况都是最优选择。
</details>

## 6. 一个 WebApplication 是否总会让 kro 创建 Deployment、RDS 和 IAM？

<details>
<summary>答案与说明</summary>

不会。WebApplication 是一个需要 RGD/CRD 的自定义 API 示例。kro 管理声明的 Kubernetes 资源；经授权的 ACK 服务控制器调用 AWS API。资源组合、就绪状态和删除策略取决于具体定义。
</details>

## 7. 当前的 DORA 指标有哪些，应如何使用？

<details>
<summary>答案与说明</summary>

变更前置时间、部署频率、失败部署恢复时间、变更失败率和部署返工率。应改进服务/团队的交付和稳定性，而不是用其替代通用 MTTR 或个人排名。衡量可以在达到 Excel 之前开始。
</details>

## 8. Guardrails 是否会自动保证安全与合规？

<details>
<summary>答案与说明</summary>

不会。应通过审计和恢复机制来执行并验证策略、绕过/例外处理、权限和变更。Guardrails 不能替代应用程序的数据处理责任，也不能替代对法律要求的评估。
</details>
