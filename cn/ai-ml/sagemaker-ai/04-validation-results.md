# 第 5 部分：SageMaker Qwen PII 验证结果事实记录

> **最后更新**：2026 年 9 月 12 日
> **AWS 验证日期**：2026 年 9 月 1 日
> **历史状态**：GPU 训练前受阻；剩余资源记录日期为 9 月 2 日

## 结论

本章介绍仓库中记录的 **2026 年 9 月 1 日至 2 日实验情况**。它保留了当时观察到的本地检查、AWS 资源配置尝试和部分清理情况；这不是对账户当前状态的重新查询。9 月 12 日的源代码审查发现，令牌化、评估、执行和清理方面还存在原先 30 项测试未能发现的问题。

第三次资源配置尝试遗漏了项目成员资格，导致调用方无法删除已创建的项目。随后停止了进一步创建资源，因此 **SageMaker Training Job 和 EKS GPU Job 均未执行**。

## 已核实事实

| 项目 | 结果 |
|---|---|
| 基础模型 | `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| 合成记录 | 2,200 |
| 训练 / 验证 / 测试 | 1,600 / 200 / 400 |
| 韩语 / 英语 | 80% / 20% |
| 历史 Python 契约与回归测试 | 30 项通过；这不能证明 GPU 已执行，也不能证明不存在其他缺陷 |
| 提取契约 | `TYPE<TAB>ORIGINAL` |
| 观察到的 SageMaker MLflow App 版本 | `3.10.1` |
| 是否执行 SageMaker 训练 | `false` |
| 是否执行 EKS 训练 | `false` |
| 2026 年 9 月 2 日剩余项目 | 1 个，状态为 `ACTIVE` |

## 实际执行轨迹

该图展示了存储记录中的**本地检查、AWS 预检、三次资源配置尝试、清理过程和停止点**。流程在 GPU 训练前终止。没有执行 GPU 并不意味着实验总成本为零。

![实际验证工作流：先进行本地验证，再尝试三次 SageMaker 和 Unified Studio 资源配置，随后部分清理；最终有一个 ACTIVE 项目，且未执行 GPU 训练。](../../.gitbook/assets/en-ai-ml-sagemaker-ai-04-validation-results-0.png)

[🔍 查看交互式验证工作流](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-sagemaker-ai-04-validation-results-0.html)

## 三次资源配置尝试

| 尝试 | 实际结果 | GPU 训练 | 清理 |
|---|---|---|---|
| 1 | MLflow App 达到 `Created` 状态，但初始脚本等待了 App 并不存在的 `ACTIVE` 状态 | 未启动 | 已回收 App、S3 和 IAM 资源；剩余 0 个 |
| 2 | Unified Studio 域拒绝了自定义项目资源标签 | 未启动 | 已回收 App、S3 和 IAM 资源；剩余 0 个 |
| 3 | 创建项目时，未将调用方角色组配置文件加入项目成员 | 未启动 | 已回收 App、S3 和 IAM 资源；剩余 1 个项目 |

## 已应用的修正

历史报告记录了对 App 就绪状态、项目标签处理、所有者成员资格和重试逻辑所做的更改。这些记录不能证明当前自动化已经完善。

9 月 12 日的后续检查发现，系统可能删除预先存在的资源、将权限错误当作资源不存在、使用错误的配置路径、丢失 EKS 适配器，以及存在中断处理缺口。请按照[执行章节](03-sagemaker-mlflow-execution.md)中的修正后执行和导出流程操作。新增检查使用本地测试装置和模拟 API；它们不代表重新执行了 AWS 操作。

仅凭 `ListProjects` 中没有项目，无法证明项目已删除。请检查可见性、筛选条件和分页，然后通过经授权的直接查询或管理员确认。权限错误和超时都应视为**未知**。

## 2026 年 9 月 2 日的清理状态

存储记录中 9 月 2 日的只读复查结果：

| 资源类型 | 状态 |
|---|---|
| SageMaker MLflow App | 无剩余资源 |
| 实验 S3 存储桶 | 无剩余资源 |
| 实验 IAM 角色 | 无剩余资源 |
| EKS 集群 / GPU 实例 | 从未创建 |
| Unified Studio `qwen-pii-*` 项目 | 1 个，状态为 `ACTIVE` |

如果该状态至今仍然存在，域管理员和现有项目所有者必须先核实权限与所有权，再进行清理。不要根据新的角色名称推断历史成员资格或所有权。

## 未测量的项目

| 项目 | 未发布结果的原因 |
|---|---|
| 微调后的实体 F1 | 未执行适配器训练和微调后评估 |
| 相对基线的提升 | 没有来自同一 GPU 环境的基线/微调结果对 |
| 训练时长 | 未执行 SageMaker 或 EKS Training Job |
| GPU 峰值内存 | 未执行 GPU 进程 |
| GPU 成本 | 未启动 GPU Job，因此没有可比较的实测结果 |
| 实验总成本 | 没有针对 MLflow App 和 S3 等其他资源的账单核对报告 |

已配置的最长运行时间或步数只是设计输入，并非观测结果。

## 重新运行条件

请按顺序完成每项条件：

1. 将旧清单与实际资源核对，并处理剩余或状态未知的**实验自有资源**。名称使用相同前缀并不代表可以删除。
2. 重新检查当前账户、区域、配额、镜像、域、配置文件和所有者成员资格。
3. 固定经过审查的配置、源代码和数据集哈希；验证已上传对象。
4. 运行会产生费用的 SageMaker 冒烟作业，并保留其结果文件。
5. 检查 CloudWatch 和 MLflow 是否泄露原始数据。仅有成功状态或符合要求的文件名不足以通过此检查。
6. 根据已验证的冒烟测试证据，决定是否执行完整 Job。

完成 SageMaker 冒烟测试并固定其结果和数据集哈希后，再单独执行 EKS 对比测试的冒烟/完整流程。

## 证据位置

- 结构化结果：`examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json`
- 详细验证记录：`docs/superpowers/reports/2026-09-01-sagemaker-qwen-pii-validation.md`
- 可运行程序包：`examples/ai-ml/qwen-pii-finetuning/`

上一页：[第 4 部分：Unified Studio 治理](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)

从头开始：[SageMaker Qwen PII 指南](README.md)
