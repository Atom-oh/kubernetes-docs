# 第 3 部分：SageMaker AI 与 MLflow 执行

如需动手学习路径，请从 [QLoRA 训练工作坊](05-qlora-finetuning-workshop.md)开始。本章记录现有实现和运维约定。

> **最后更新**：2026 年 9 月 12 日

## 执行通知

**当前已提交的 GPU 执行路径因镜像已到补丁支持期限而被阻止**。官方目录将 `2026-08-06` 列为 `2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` 的补丁支持截止日期。`src/runtime_contract.py` 会在预检、资源预置、Training Job 提交、EKS 创建和训练之前检查此边界。应同时升级镜像、`torch` 和依赖项版本组合，并验证 GPU 冒烟测试；仅删除日期检查并不等于升级运行时。

本章介绍 `examples/ai-ml/qwen-pii-finetuning/` 中已修正的约定。本地测试、请求预览和自有资源清理仍然可用。2026 年 9 月 1 日的 AWS 实验**在提交训练之前停止**。本次审查也未创建 AWS 资源或运行 GPU 训练。

AWS 建议新建 SageMaker 托管 MLflow 部署时采用 **MLflow Apps**。现有 Tracking Server 是另一种独立资源。目前 App 文档列出 MLflow `3.10`；本历史示例将客户端和 EKS Server 固定为 `3.1.4`。本地成功导出 3.1.4 制品并不能验证它与托管 App 的完整兼容性。运行时升级验证时应包含这一版本组合。

## 托管路径的八个步骤

### 1. 只读预检

激活 **Python 3.12 虚拟环境**并安装软件包 README 所列依赖项后，运行以下命令。

```bash
cd examples/ai-ml/qwen-pii-finetuning
export AWS_REGION=ap-northeast-2
python3 src/runtime_contract.py --check-execution
```

当前此命令应以补丁支持到期说明失败。将示例升级到受支持的运行时后，设置由管理员验证的 `EXPECTED_ACCOUNT_ID`、`DATAZONE_DOMAIN_ID`、`DATAZONE_PROJECT_PROFILE_ID` 和 `DATAZONE_OWNER_GROUP_ID`，然后运行 `./launch/aws/preflight.sh`。这些变量包含资源标识符，不是密码或服务账户密钥。

预检会检查工具、调用方、区域、配额、DLC 和现有实验名称冲突。它不会根据显示名称或 STS 角色字符串重建 domain、profile 或 group。空列表既不能证明绝对不存在，也不能证明之后有权限创建。应检查共享同一前缀资源的所有者；不要不加区分地删除它们。

### 2. 构建源代码包

```bash
./launch/aws/build_source_bundle.sh
```

该包包含 `src/*.py`、`config/experiment.yaml`、`requirements.lock` 以及内容相同的 `requirements.txt`。它不会递归打包数据或本地凭证文件。它不会检测直接嵌入源代码或配置中的敏感值，因此请检查打包内容。其 SHA-256 用于标识**该次构建**；tar 时间戳不保证可复现。

### 3. 创建 MLflow App 和 Unified Studio 项目

此步骤会**修改 AWS 并创建计费资源**，只有在运行时和权限验证完成后才能执行。

```bash
./launch/aws/provision.sh
```

该步骤会创建实验 bucket、执行角色和 MLflow 角色、MLflow App，以及包含所有者成员资格的项目。bucket 启用了 Block Public Access、AES-256 和版本控制；IAM policy 会使用 Access Analyzer 检查。App 就绪状态为 `Created` / `Updated`。项目状态为 `ACTIVE` 并不代表项目的每个环境都已成功部署。

私有清单会区分创建意图和成功响应。名称冲突或响应丢失并不授权按名称删除。错误清理只会处理所有权已确认的资源；创建状态未知时必须先协调确认。进程或实例被强制停止时，shell trap 可能根本不会执行。

### 4. 上传数据集

上传前先创建 bucket 并检查清单。验证以下五个输入：

```bash
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json
# Actual S3 upload and SHA-256 readback verification:
python3 -m launch.aws.upload_inputs \
  --inventory results/resource-inventory.json --execute
```

输入包括 `generated/source.tar.gz`、`data/{train,validation,test}.jsonl` 和 `data/dataset-manifest.json`。辅助程序会检查数据拆分哈希、bucket 账户所有权和实验标签，然后写入本次执行专用的 `qwen-pii/<experiment-id>/source/` 和 `dataset/` 前缀。它会回读对象并比较 SHA-256。此小型合成示例将每个文件限制为 64 MiB。上传失败时可能留下部分对象，因此应保留清单。

在私有运维记录中使用标识符和哈希值。预签名 URL 携带访问权限，不能发布到公开文档或日志中。

### 5. 提交 SageMaker Training Job 请求

```bash
python3 -m launch.sagemaker_train \
  --mode smoke --inventory results/resource-inventory.json
```

默认情况下，此操作会在 `results/previews/` 下写入唯一命名的 JSON 文件，而不会提交到 AWS。它不会覆盖已提交的 `<job-name>-request.json` 或 `<job-name>-job.json`。验证受支持的运行时后，添加 `--execute` 才会提交。完整执行还需要单独指定 `--mode full --execute`。启动器不会自动批准冒烟测试证据或输入哈希。

配置从源代码包中的 `/opt/ml/code/config/experiment.yaml` 读取。四个数据文件位于 `/opt/ml/input/data/dataset/`。本地 `--config` 和源代码包必须由同一份源代码构建，确保两者一致。

提交前，启动器会在清理工具共用的锁下同时预留请求和作业日志。若作业创建成功后出现监控失败或中断，会尝试发出停止请求。`stop_requested` 并不表示已确认终止。遇到 `submission_unknown`、`stop_unconfirmed` 或主机丢失后，应核对 AWS 状态和资源所有权；不要覆盖现有日志或孤立请求后再提交。

历史配置指定一台 `ml.g6e.4xlarge`、300 GiB、冒烟测试 10 步 / 完整训练 80 步，以及 `MaxRuntimeInSeconds: 10800`。此上限不限制包含终止、上传、MLflow、S3 和其他资源在内的总成本。

### 6. 冒烟测试 / 完整训练门槛

重新启用执行之前，应验证镜像、依赖项和 MLflow 版本组合均受支持。之后检查冒烟测试的最终状态、数据集哈希、指标和 adapter 文件。审查日志与 MLflow 中是否含有源文本、实体值、映射或原始补全内容。**制品文件名白名单不能证明其内容安全**。本流程并不表示已经实现自动化 PII 扫描器。

### 7. 导出汇总结果

| 文件 | 含义 |
|---|---|
| `dataset-manifest.json` | 生成器设置、计数、数据拆分哈希 |
| `resolved-config.json` | 实际设置、环境、步数 |
| `dependency-versions.json` | 观测到的已安装版本；不能保证它等同于完整 lock 文件 |
| `baseline-metrics.json`、`tuned-metrics.json` | 在相同测试拆分上进行的汇总评估 |
| `run-summary.json` | 阶段耗时、指标、adapter 清单 |
| `adapter/adapter_config.json`、`adapter/adapter_model.safetensors` | 保存在 MLflow 中的最终 adapter |

SageMaker `/opt/ml/model` 输出和 MLflow 制品位于不同的存储位置。删除 bucket 或 App 前，应下载并验证所需结果。分享 adapter 前，应检查其内容和访问权限。不会导出原始预测、令牌映射或所有中间 checkpoint。

`peak_gpu_memory_bytes` 是模型加载后重置默认 CUDA 设备的 PyTorch 已分配内存峰值。它不是 GPU 总内存、加载期间的峰值，也不是多设备内存之和。目前没有训练结果可用于支持性能提升或成本比较的结论。

### 8. 拆除和验证

```bash
./launch/aws/teardown.sh
./launch/aws/verify_cleanup.sh
```

先检查并停止已记录的 Training Job。如果有训练记录，拆除流程会再次停止作业，防止在导出之前删除其制品 bucket。只有在单独保留所需 SageMaker / MLflow 制品后，才能继续执行：

```bash
./launch/aws/teardown.sh results/resource-inventory.json \
  --discard-training-artifacts
```

此标志不会执行备份。如果自有 EKS 资源仍然存在，共享拆除流程也会停止。应先通过 EKS 路径或下方手动恢复流程完成已验证的导出 / 删除。然后才会清理所有权已确认的 App、项目、S3 和 IAM 资源。AWS `AccessDenied`、传输失败、删除超时和单个 S3 对象错误都不能视为资源不存在。缺少所有权证据的旧清单需要管理员协调确认。此工具不会删除共享的 TrainingJobs 日志组或无关资源。

若仍有剩余或未知状态，验证将失败。成功结论仅适用于被查询的账户、区域、清单和检查项；不能证明整个 AWS 账户为空。清理不完整或集群残留仍可能继续产生费用。

## EKS + MLflow 对比路径

运行时升级后，入口为 `./launch/eks/run.sh smoke`；另行审查通过后，才能运行 `./launch/eks/run.sh full`。目前这两个入口都会在补丁支持截止检查处停止。

| 项目 | 示例约定和限制 |
|---|---|
| 集群 | 模板使用 EKS `1.36`、一个 `g6e.4xlarge`；需重新检查区域可用性和支持情况 |
| GPU 插件 | 固定版本 `0.20.0`；应与新 DLC、AMI 和驱动一并验证 |
| kubeconfig | 每次运行单独生成文件并显式指定 context；拒绝与现有集群发生名称冲突 |
| MLflow | ClusterIP、SQLite、`emptyDir`；没有应用身份验证、持久化存储或租户隔离 |
| 数据 | 使用带 ServiceAccount 级 AWS 权限的 S3 SDK；验证清单 SHA-256 和 bucket 账户 |
| 作业 | `backoffLimit: 0`、`activeDeadlineSeconds: 10800`；故障期间无法保证所有资源都能在三小时内回收 |
| 导出 | 对已完成运行导出的八种制品及 SHA-256 进行验证，并匹配实验、集群和执行 ID |
| 关闭 | 导出 / 哈希验证后清理自有集群；导出失败时可能保留集群用于恢复 |

输入加载器会从 ConfigMap 读取代码和上传哈希，然后使用 EKS Pod Identity 只下载五个 S3 对象。ServiceAccount 为 `qwen-input-reader`；需要 Pod Identity Agent、受支持的 SDK 和关联配置。已禁用 EC2 实例元数据凭证回退。此配置不会解除已过期 DLC 对执行的阻止。

训练和 MLflow Pod 的 `emptyDir` 数据会随 Pod 或集群删除而消失。每次运行生成的 `results/eks-<mode>.<suffix>/mlflow-export-<mode>.tar.gz` 和导出回执都是本地文件，不是异地备份。应将它们复制到单独获批的存储位置，并验证清理结果。

如果训练失败且没有已完成的运行 / 导出，则无法满足自动删除条件。应根据 AWS 中的账户、集群 ARN、创建时间、所有权标签和 stack ID 核对私有清单；恢复或明确放弃所需结果，然后**只删除该自有集群**，命令为 `eksctl delete cluster --name ... --region ... --wait`。部分创建或响应丢失时也需要手动协调确认。之后运行 `verify_cleanup.sh` 并调查 stack 删除后残留的资源。不要伪造所有权标志绕过验证。

## 已观察到的错误和停止条件

| 情况 | 处理方式 |
|---|---|
| DLC 已到补丁支持截止日期 | 阻止资源创建 / 训练；升级整个运行时组合 |
| 配置路径错误 | 从源代码包中读取配置 |
| 名称冲突或创建响应丢失 | 所有权未确认前，拒绝自动删除 |
| 导出缺失或失败 | 验证 adapter 和汇总文件之前，不要宣告成功 |
| 查询授权错误或删除超时 | 记录为未知 / 失败 |
| 历史项目遗漏成员资格 | 与 domain 管理员和项目所有者协调确认 |

## 路径选择

SageMaker 减少 Training Job 和 MLflow 的运维工作量，但制品保留、权限和实验清理仍需处理。EKS 提供 Kubernetes 控制能力，但也增加了集群、GPU 插件和 MLflow 存储的运维责任。比较两者时，应一起记录配置、数据哈希、模型修订、实际依赖项和 GPU 环境。

## 主要来源

- [AWS DLC PyTorch 2.8 目录和补丁支持截止日期](https://github.com/aws/deep-learning-containers/blob/main/docs/src/data/pytorch-training/2.8-gpu-sagemaker.yml)
- [SageMaker Training Toolkit 代码目录](https://github.com/aws/sagemaker-training-toolkit/blob/master/src/sagemaker_training/entry_point.py)
- [MLflow App 设置](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow-app-setup.html)
- [SageMaker MLflow 版本](https://docs.aws.amazon.com/sagemaker/latest/dg/mlflow.html)
- [S3 预签名 URL 到期时间](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [EKS Pod Identity 行为和限制](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Kubernetes Job 故障和终止](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

上一页：[第 2 部分：合成 PII 数据和令牌化](02-pii-data-tokenization.md)

下一页：[第 4 部分：Unified Studio 治理](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md)
