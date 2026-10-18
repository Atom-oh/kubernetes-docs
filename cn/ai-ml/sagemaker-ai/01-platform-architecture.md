# 第 1 部分：SageMaker Qwen PII 平台架构

> **最后更新**：2026 年 9 月 12 日。该图展示的是目标设计；历史 AWS 记录中并未执行任何一条 GPU 训练路径。

由于固定使用的 PyTorch 2.8 DLC 已结束补丁支持，GPU 执行目前受阻。请先按照[执行章节](03-sagemaker-mlflow-execution.md)中的要求升级到受支持的运行时。

![目标设计：托管式和 EKS 执行、候选实体提取、确定性处理、聚合跟踪以及自有资源清理。](../../.gitbook/assets/en-ai-ml-sagemaker-ai-01-platform-architecture-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-sagemaker-ai-01-platform-architecture-0.html)

## 1. 职责与记录边界

| 组件 | 职责与限制 |
| --- | --- |
| 合成数据生成器 | 配置为 1,600/200/400 的数据划分，共 2,200 条记录；跟踪生成器、随机种子和哈希值 |
| S3 / 数据交付 | 存储源数据、数据集和构件；分别管理 IAM、加密、保留策略和传输 |
| Qwen + QLoRA | 用于实体候选项的适配器训练设计；最终替换与完整检测是不同的问题 |
| Python 处理/评估 | 执行类型/来源检查、替换/还原和聚合；不会自动找回模型漏检的实体 |
| MLflow | 比较配置、版本和聚合结果；验证服务器访问权限以及日志/构件内容 |
| Unified Studio | 本实验选用的治理方案，并非 QLoRA、EKS 或 Training Jobs 的强制依赖项 |
| 资源登记 / 清理 | 在私有清单中记录标识符、所有权和依赖关系；导出、清理并验证结果 |

请控制包含源文本或令牌映射的构件。借助映射进行替换可以还原，但不等于加密。日志策略属于设计/约定，并不能证明已测试每个库、回调、异常和自动跟踪路径。
资源 ID/ARN 可能需要记录在私有清单中，应与公开报告区分开来。

## 2. 不同环境共用的契约

| 方面 | SageMaker AI 路径 | EKS 路径 |
| --- | --- | --- |
| 执行 | 托管式 Training Job | 为本实验准备的 GPU Job/集群 |
| 跟踪 | SageMaker MLflow App | ClusterIP MLflow |
| 数据 | S3 输入通道 | 使用限定于 ServiceAccount 的 AWS 权限，通过 S3 SDK 下载 |
| 生命周期 | 区分作业终止与外部 App/存储桶的清理 | 导出结果，然后回收自有临时资源 |

Training Job 或命名空间/Job 边界本身并不能完成安全隔离。请验证实际的 IAM/ServiceAccount、网络、存储、端点/MLflow 访问权限和容器配置。EKS 路径通过其 ServiceAccount 和 SDK 凭证链使用工作负载身份。它不会把预签名 URL（持有该链接即可凭其访问资源）放入 Pod 环境变量；它会验证输入清单 SHA-256 和存储桶所有权。

要进行比较，需要提供配置、数据划分哈希、训练/评估代码和步数，以及模型/分词器修订版本、镜像摘要、传递依赖、CUDA/驱动/硬件和解码设置。固定随机种子并不能保证不同环境中的 GPU 结果完全一致。`requirements.lock` 固定了直接依赖包，但不包含完整的传递依赖环境。

## 3. 模型与建议的 QLoRA 设置

基线模型为 Qwen/Qwen3-30B-A3B-Instruct-2507。其模型卡说明这是一个**总计 30.5B / 激活参数 3.3B**的 MoE 模型，采用非思考模式。
激活参数不代表全部存储权重或所需的 GPU 内存。
本文并未将其称为最新模型，也未声称它已被证明适用于某种特定 GPU。

评审时观察到的模型仓库修订版本为 `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe`。
当前加载器/配置使用模型 ID，但没有显式固定该修订版本。
在声称执行结果可复现之前，请固定模型/分词器修订版本和构件。

| 设置 | 建议配置 |
| --- | --- |
| 量化 / 计算精度 | 4-bit NF4、双重量化 / bfloat16 |
| LoRA 秩 / alpha / dropout | 16 / 32 / 0.05 |
| 序列长度 | 1,024 |
| 设备批次 / 梯度累积 | 1 / 8 |
| 冒烟测试 / 完整训练 | 10 / 80 步 |
| 作业运行时设置 | 10,800 秒 |

这些数值并不代表训练成功、质量足够或 GPU 峰值内存已得到测量。作业截止时间不等于端到端的资源配置/跟踪/存储生命周期，也不等于成本上限。QLoRA 使用低精度基座权重并训练适配器；执行期间仍需验证实际模块覆盖范围、优化器、内存和模型兼容性。

## 4. 治理与执行准备情况

本实验会在提交 GPU 作业前检查预期的域/项目配置方案（profile）、调用方成员资格和 MLflow 访问权限。`CreateProject` 的 `membershipAssignments` 可以在同一请求中指定所有权，但无法保证所有资源配置失败时都能原子回滚。
还必须分别检查项目是否为 ACTIVE，以及所需工具/环境是否已就绪。

历史尝试表明，项目失败前可能已经创建了 App 等资源。请将权限预检查与创建后的资源登记和补偿操作结合起来。清理范围仅限本次运行所拥有的资源；不要根据旧记录推断当前仍有哪些遗留资源。有关身份与删除边界，请参阅 [Unified Studio 章节](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)。

## 验证范围

已对照检查配置、训练器源代码、公开模型卡和历史报告。在最初的 30 项本地测试之后，又补充了分词、执行和清理方面的回归测试覆盖。
未下载模型权重；未执行 GPU 训练、推理质量评估或当前 AWS 资源检查。

## 参考资料

- [Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA 论文](https://arxiv.org/abs/2305.14314)
- [实验配置](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [已记录的配置结果](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[下一篇：PII 数据与令牌化](02-pii-data-tokenization.md)

[测验](../../quizzes/ai-ml/sagemaker-ai/01-platform-architecture-quiz.md)
