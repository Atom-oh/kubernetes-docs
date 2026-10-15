# 使用 SageMaker AI 针对 PII 微调 Qwen

> **最后更新**: September 15, 2026

包含基于合成数据的 CPU 练习和 QLoRA 指导。AWS 资源开通相关的观察记录为 2026 年 9 月 1 日的历史记录。

本指南讲解如何训练并评估一个从文档中提取 PII 候选项的模型。内容包括定义标注约定、在不发生数据泄漏的前提下切分与增强数据、选择 QLoRA 配置，以及同时衡量漏检与过度脱敏。

模型输出 `TYPE<TAB>ORIGINAL` 形式的候选项。由 Python 代码负责校验与替换；模型不会重写整篇文档。这种职责分离有助于区分检测错误与替换逻辑的缺陷。

## 从实践学习路径开始

| 顺序 | 章节 | 学完后你应当能够解释的内容 |
| --- | --- | --- |
| 1 | [合成数据与数据增强](06-data-augmentation-workshop.md) | 标注约定、家族隔离、仅对训练集做增强、来源/标签审计 |
| 2 | [QLoRA 训练与 SageMaker 工作流](05-qlora-finetuning-workshop.md) | NF4、LoRA、loss mask、实际的 target modules、batch/step 预算、调优与诊断 |
| 3 | [PII 评估与脱敏流水线](07-pii-evaluation-release.md) | Recall/F1、残留 PII、对负样本文档的脱敏、最终评估与验收 |
| 4 | [SageMaker AI 与 MLflow 执行约定](03-sagemaker-mlflow-execution.md) | 源码包、S3 通道、Training Job、产物与资源清理 |

如果你能使用 Python 3.12 和 JSONL，建议从数据与评估入手。两个 CPU 练习都不需要 AWS 账户或模型权重。训练演练和 GPU 检查流程与"已完成 GPU 训练"的证据是两回事。

新增的数据增强练习会先切分 40 个合成家族，然后仅对训练集做增强。它使用独立的数据集，不会覆盖历史 generator 1.0.0 语料中的 2,200 条记录。小规模练习或 oracle 分数不能作为真实场景下的模型性能结论。

## SageMaker 执行准备情况

历史版本的软件包提出通过托管的 SageMaker Training Job 或临时的 EKS GPU Job 来训练 Qwen/Qwen3-30B-A3B-Instruct-2507。这两条 GPU 路径都没有端到端成功的记录。

固定使用的 PyTorch 2.8 DLC 已于 2026-08-06 结束补丁支持，因此资源创建与 GPU 执行均被阻塞。请参考 [QLoRA 运行时讨论](05-qlora-finetuning-workshop.md)和[执行约定](03-sagemaker-mlflow-execution.md)，将镜像、依赖与 MLflow 的配套关系一并验证。仅仅移除支持状态检查并不构成一套迁移流程。

## 深入阅读设计与实现

| 文档 | 用途 |
| --- | --- |
| [第 1 部分：平台架构](01-platform-architecture.md) | 模型、数据、Python 处理与 MLflow 各自的职责 |
| [第 2 部分：数据与确定性分词](02-pii-data-tokenization.md) | 历史版本的九种类型数据、替换区间以及精确的指标定义 |
| [第 3 部分：执行](03-sagemaker-mlflow-execution.md) | SageMaker/EKS 作业提交、持久化、恢复与清理 |
| [第 4 部分：Unified Studio 治理](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/项目/成员管理 |
| [第 5 部分：事实性验证记录](04-validation-results.md) | 已执行的工作、未执行的工作以及历史残留资源 |

## 如何解读验证记录

- 新的数据/评估命令是在 CPU 上使用合成输入验证的。已训练模型的 F1、GPU 峰值显存和训练时长需要单独测量。
- 2026-09-12 的评审补充了针对分词、评估、执行与清理的本地回归测试覆盖。
- 2026-09-01 的 AWS 记录涵盖配额以及 MLflow App/项目开通的失败路径；它在提交 GPU 作业之前就停止了。
- 该记录清理了实验用的 App/S3/IAM 资源，但遗留了一个 Unified Studio 项目。需要重新盘点资源才能确认其当前状态。

不要将源文档、抽取出的取值、token 映射关系或原始的模型输出发送到通用日志或 MLflow 的 parameters/tags 中。同时也要检查执行环境中的 autolog/tracing 以及产物内容。可逆的映射关系、训练得到的 adapter 以及私有资源清单属于不同类型的产物，各自有独立的保留期与访问权限要求。

示例软件包：`examples/ai-ml/qwen-pii-finetuning/`。每个 workshop 都提供了确切的 CLI 命令与输出示例。

## 参考资料

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 论文](https://arxiv.org/abs/2305.14314)
- [实验配置](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [历史资源开通结果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
