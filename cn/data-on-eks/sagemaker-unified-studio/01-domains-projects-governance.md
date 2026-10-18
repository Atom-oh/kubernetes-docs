# 第 4 部分：域、项目和成员治理

> 文档审阅日期：2026-09-12。Qwen 置备结果属于历史记录；本次未重新检查当前账户状态。

记录在案的第三次 Qwen 置备尝试报告称，项目已创建，随后因调用者成员身份而无法读取/删除。训练尚未开始。
不要将该记录泛化为每个域当前的状态，也不要泛化为所有授权失败。

## 1. 区分对象和身份

| 对象/角色 | 含义 |
| --- | --- |
| Unified domain / domain unit | 治理边界和组织层级 |
| Project profile / blueprint | 工具/环境置备，以及允许使用的账户/区域 |
| Project | 协作、工具和共享资源 |
| User/group profile | SSO 身份或注册 IAM 角色的服务表示 |
| Membership designation | 项目级角色，例如 PROJECT_OWNER 和 PROJECT_CONTRIBUTOR |
| Project execution role | 为项目访问 AWS 数据/计算资源的身份 |
| Catalog asset | 受管治理的元数据，例如描述、架构和位置 |

首先识别配置和登录方式是基于 IAM 还是 Identity Center。
成员角色和执行角色用途不同，即使它们的 ARN 相同也是如此。基于 IAM 的项目成员通过项目执行角色共享数据/计算访问权限；owner 身份不会自动隔离每个用户的数据权限。使用基于身份的授权/Trusted Identity Propagation 时，应单独验证。

AWS 用户管理文档区分了已注册 IAM 角色的 group profile，以及通过该角色登录的用户所创建的 session user profile。
成员关系可以使用角色 group profile。使用 rolePrincipalARN 调用 CreateGroupProfile **只会注册 profile，并不会创建 IAM 角色本身**。
项目执行角色的自动处理方式不一定等同于自动化调用方的授权方式。

## 2. Profile 名称不能证明工具已就绪

All capabilities 会为蓝图指定模板。Profiles 可以在创建项目时置备蓝图，也可以稍后按需提供蓝图。应检查所需服务、账户、区域、网络以及使用该 profile 的权限。

应选择预期的 profile ID/配置，而不要盲目采用第一个名称匹配项。较小的能力集可能适用于 Qwen 实验，但仍需经过组织批准并满足实际依赖项。还要区分这种工作流与不使用 Unified Studio 项目的常规 SageMaker/EKS 训练路径。

## 3. IAM、成员身份和数据授权

获准的 IAM 操作本身不会赋予项目所有权。项目所有权也不能绕过 IAM、SCP、资源策略或数据权限限制。普通成员/贡献者不会自动获得删除授权。应验证删除路径要求的是项目所有者权限还是管理员权限。

当前的 CreateProject API 接受 membershipAssignments。
以下是一个**请求结构示例**：请在获得授权访问后，将域/profile/group 标识符替换为实际值。

```json
{
  "domainIdentifier": "dzd-1111111111111111",
  "name": "docs-governance-example",
  "projectProfileId": "c1111111111111",
  "membershipAssignments": [
    {
      "member": {
        "groupIdentifier": "11111111-1111-1111-1111-111111111111"
      },
      "designation": "PROJECT_OWNER"
    }
  ]
}
```


member 是一个 tagged union：只能设置 groupIdentifier 或 userIdentifier **其中一个**。
在同一个请求中包含成员信息可以减少另行后续请求造成的时间差，但不能保证所有项目/环境置备都以事务方式回滚。应读取并核实项目和成员关系。如果请求超时，应对照原始请求和资源清单进行核对，而不是反复按名称创建项目。

## 4. 项目和工具就绪顺序

1. 验证预期账户/区域、域类型和 profile ID。
2. 区分调用方登录/profile、所需的 owner/admin 权限和执行角色权限。
3. 确定创建时置备与按需置备的蓝图，并准备获准的依赖项。
4. 保存并回读 CreateProject 和成员关系的结果。
5. 分别检查 projectStatus 和 environmentDeploymentDetails。
6. 验证所需环境/工具就绪，并在继续下一步计算操作前检查实际读写权限。

projectStatus=ACTIVE 并不表示每个环境/工具都已就绪。
overallDeploymentStatus 包括 PENDING_DEPLOYMENT、IN_PROGRESS、SUCCESSFUL、
FAILED_VALIDATION 和 FAILED_DEPLOYMENT。不要将有意未置备的按需工具视为失败；应验证**此工作负载实际需要什么**。

## 5. 标签失败与目录披露

当前 API 支持 resourceTags。旧实验中的拒绝结果是针对特定域/请求的观测，并不能证明 Unified Studio 不支持标签。检查实际策略、值和错误。清理时仅处理本次运行创建且获准清理的资源；不能只凭名称前缀就删除共享存储桶或角色。

公开文档可以包含必要的实验数量、合成数据架构/记录数量、生成器版本/种子/哈希，以及资源所有权/保留原则。
不要在公开制品中放入真实 PII、凭证、预签名 URL 或重新识别映射。

受访问控制的**内部目录**可能需要存储位置和资源标识符以便发现/访问。公开文档中的脱敏并不意味着禁止内部位置元数据。元数据发布、订阅审批和实际数据授权是不同步骤。

## 6. 删除与确认资源不存在

1. 确定需要保留的数据，以及本次运行拥有的资源/依赖项。
2. 使用获准的 owner/admin 身份停止项目工作，并明确清理范围。
3. 根据项目、环境和托管资源的生命周期执行删除。
4. 检查 DELETING/DELETE_FAILED 状态和错误，并确认删除完成。
5. 根据清单核对相关账户/区域中剩余的外部 Apps、S3、IAM 和计算资源。

GetProject 返回 AccessDenied 并不能证明资源不存在。
如果可见性、过滤器或分页受到限制，ListProjects 返回空结果也不足以证明不存在。应验证域/身份和每一页结果，并结合获准的 get/list 证据与外部资源清单。删除项目并不能保证删除所有外部服务资源；应分别验证资源所有权和保留要求。

## 7. Qwen 验证的历史范围

已存储的验证 JSON 日期为 **2026-09-01**。
它记录了三次尝试的 trainingStarted=false，第三次尝试后仍有一个项目，并清理了实验 App/S3/IAM 资源。9 月 2 日的文档记录了当时重新检查时状态为 ACTIVE。本次审阅将这些记录与当前公开 API 文档进行比较；但它不能确定该项目是否仍存在于当前账户中，或是否已删除。

恢复操作前，应验证当前资源清单和所有权。
此次审阅没有创建/删除项目、成员关系、IAM 或 GPU 资源。
该请求示例通过了**本地 AWS CLI 输出 skeleton 输入验证**；
同时设置两种成员身份类型的变体则被 ParameterValidation 拒绝。
这并不能证明实时授权或环境置备成功。

## 参考资料

- [基于 IAM 的域](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [项目成员和执行角色](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [用户和 group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject 请求和部署状态](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [所有能力 profiles 和按需置备](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [项目删除和外部资源](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Qwen 置备验证记录](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[上一部分：SageMaker AI / MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

[下一部分：验证结果](../../ai-ml/sagemaker-ai/04-validation-results.md)

[测验](../../quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
