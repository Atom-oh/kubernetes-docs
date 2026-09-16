# 使用 SageMaker AI 对 Qwen 进行 PII 微调

> **最后更新**: September 16, 2026

包含合成数据 CPU 练习和 QLoRA 说明。独立运行环境已于 September 16, 2026 完成一次实际 GPU 冒烟运行。September 1 的资源预置观察结果仍作为历史记录保留。

本指南介绍如何训练和评估一个从文档中提取 PII 候选项的模型。定义标注契约，在无数据泄漏的前提下拆分和扩增数据，选择 QLoRA 设置，并衡量遗漏和过度掩码两种情况。

模型输出 `TYPE<TAB>ORIGINAL` 候选项。Python 代码对其进行验证和替换；模型不会重写整个文档。这种分离有助于区分检测错误与替换 bug。

## 从实用的学习路径开始

| 顺序 | 章节 | 之后应能够说明的内容 |
| --- | --- | --- |
| 1 | [合成数据和扩增](06-data-augmentation-workshop.md) | 标注契约、家族隔离、仅训练集扩增、源数据/标签审计 |
| 2 | [QLoRA 训练和 SageMaker 工作流程](05-qlora-finetuning-workshop.md) | NF4、LoRA、损失掩码、实际目标模块、批次/步骤预算、调优和诊断 |
| 3 | [PII 评估和脱敏流水线](07-pii-evaluation-release.md) | 召回率/F1、残留 PII、在负例文档上掩码、最终评估和验收 |
| 4 | [SageMaker AI 和 MLflow 执行契约](03-sagemaker-mlflow-execution.md) | 源代码包、S3 通道、Training Jobs、产物和清理 |

如果可以使用 Python 3.12 和 JSONL，请从数据和评估开始。两项 CPU 练习都不需要 AWS 账户或模型权重。训练演练和 GPU 检查流程与已完成 GPU 训练的证据相互独立。

新的扩增练习会先拆分 40 个合成家族，再仅对训练数据进行扩增。其独立数据集不会覆盖包含 2,200 条记录的历史生成器 1.0.0 语料库。微型练习或预言机分数并非真实世界模型性能的声明。

## SageMaker 执行就绪性

[实际 GPU 冒烟收据](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/execution-smoke-20260916.json)记录了一条独立的 PyTorch 2.11/AL2023/CUDA 13 路径，执行日期为 September 16, 2026。它以 NF4 加载相同的 Qwen 模型，并将 rank-16 LoRA 应用于四个注意力投影。四个优化器步骤生成了发生变化的适配器权重，且保存/重新加载后的状态一致。1,140 个可计费秒数意味着 GPU 计算费用约为 USD 1.46，不包括存储、日志、税费和调整项。

生成仅覆盖四份合成验证文档。基线的实体 F1 为 1.0000，但只有 2/4 响应的格式正确。微调模型的 F1 为 0.8125，且 4/4 响应格式正确，但额外产生了六对假阳性实体。**成功执行并不意味着质量得到提升。** 当天已提交一个 600 步完整作业；此收据不包含最终测试结果。完整作业会先依据验证损失选择 checkpoint，再评估一个独立的 400 文档测试集。请参阅[执行设置和产物保留](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/README.md#recorded-gpu-execution-september-16-2026)。

历史包建议通过受管 SageMaker Training Job 或临时 EKS GPU Job 对 Qwen/Qwen3-30B-A3B-Instruct-2507 进行训练。两条 GPU 路径均没有已记录的端到端成功结果。

该历史路径固定的 PyTorch 2.8 DLC 已于 2026-08-06 结束补丁支持，因此其资源创建和 GPU 执行仍受阻。请同时遵循 [QLoRA 运行时讨论](05-qlora-finetuning-workshop.md)和[执行契约](03-sagemaker-mlflow-execution.md)，一并验证镜像、依赖项和 MLflow 配对。仅移除支持检查并不是迁移流程。

## 深入阅读设计和实现

| 文档 | 用途 |
| --- | --- |
| [第 1 部分：平台架构](01-platform-architecture.md) | 模型、数据、Python 处理和 MLflow 的职责 |
| [第 2 部分：数据和确定性分词](02-pii-data-tokenization.md) | 历史九类型数据、替换跨度和精确指标定义 |
| [第 3 部分：执行](03-sagemaker-mlflow-execution.md) | SageMaker/EKS 提交、持久化、恢复和清理 |
| [第 4 部分：Unified Studio 治理](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Domain/project/membership |
| [第 5 部分：事实验证记录](04-validation-results.md) | 已执行工作、未执行工作和历史残留资源 |

## 解读验证记录

- 新的数据/评估命令使用合成输入在 CPU 上进行检查。已训练模型 F1、GPU 峰值内存和训练时长需要单独测量。
- 2026-09-12 审查为分词、评估、执行和清理新增了本地回归覆盖。
- 2026-09-01 AWS 记录涵盖配额以及 MLflow App/project 资源预置失败路径；在 GPU 提交之前停止。
- 该记录清理了实验 App/S3/IAM 资源，但保留了一个 Unified Studio project。需要进行新的清单盘点以确定其当前状态。

不要将源数据、提取值、token 映射或原始补全内容发送到通用日志或 MLflow parameters/tags。还应检查执行环境中的 autolog/tracing 和产物内容。可逆映射、已训练适配器和私有资源清单属于不同的产物，具有各自独立的保留/访问要求。

示例包：`examples/ai-ml/qwen-pii-finetuning/`。每个 workshop 都提供其准确的 CLI 和输出示例。

## 参考资料

- [Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 论文](https://arxiv.org/abs/2305.14314)
- [实验配置](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [历史资源预置结果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
