# SageMaker Unified Studio 治理

> 文档审阅日期：2026-09-12。实验结果对应 2026-09-01 的记录及 9 月 2 日的历史文档。

Amazon SageMaker Unified Studio 为数据/AI 团队管理协作、工具和目录资产。本节说明 EKS 管道资产、用户和执行权限的域/项目边界。
此处的 **Unified Studio/DataZone 项目**不同于 SageMaker AI MLOps Project 或 SageMaker AI Studio 域这一类 API 对象。

## 本指南涵盖的边界

| 主题 | 需要核实的内容 |
| --- | --- |
| 域类型 | 基于 IAM 与基于 IAM Identity Center 的登录/管理方式 |
| 项目配置文件/蓝图 | 创建时预置的工具与按需启用的工具 |
| 成员/执行角色 | 门户/项目访问身份与 AWS 资源执行身份 |
| 成员资格/数据访问 | 管理层面的指定与 IAM、Lake Formation 及目录数据权限 |
| 生命周期 | 项目是否存在、环境是否就绪、工具是否实际可用，以及所属资源是否已清理 |

[第 4 部分：域、项目和成员资格](01-domains-projects-governance.md) 根据这些边界解释了 Qwen 实验记录的失败。Unified Studio 项目是本指南采用的治理方案，并非每个 SageMaker Training Job 或 EKS 训练工作负载都必须依赖它。

## 区分历史证据与当前状态

存档的 2026-09-01 验证 JSON 记录了训练开始前停止实验、清理实验 App/S3/IAM 资源，以及仍有一个 Unified Studio 项目未清理的情况。9 月 2 日的文档记录了当时重新检查后状态为 ACTIVE。
**本次文档审阅没有重新查询 AWS 账户，也不表示目前仍有一个项目未清理。**

恢复该实验前，获得授权的操作人员必须核实当前资源清单、成员资格和清理状态。不要把历史失败泛化为自动授予新权限或删除共享资源的依据。

相关指南：

- [SageMaker Qwen PII 指南](../../ai-ml/sagemaker-ai/README.md)
- [第 3 部分：SageMaker AI 和 MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [第 5 部分：事实验证结果](../../ai-ml/sagemaker-ai/04-validation-results.md)

## 参考资料

- [基于 IAM 的域](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [项目成员和执行角色](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [用户和组配置文件](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject 请求和部署状态](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [所有功能配置文件和按需预置](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [删除项目和外部资源](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [记录的 Qwen 预置验证](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
