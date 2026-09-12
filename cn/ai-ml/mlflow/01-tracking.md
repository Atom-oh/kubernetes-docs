# 第 1 部分：MLflow Tracking

> **审阅基线**：MLflow 3.16.0 · 2026-09-12

## 实验环境设置

使用 Python 3.10 或更高版本安装 `mlflow==3.16.0`。以下示例已使用 Python 3.12、SQLite 和本地 artifact store 验证。它不需要 GPU、已训练模型或远程服务器。[第 3 部分](03-eks-deployment.md)涵盖团队 HTTP 服务器和 EKS 操作。

## 什么是 MLflow Tracking？

Tracking 为实验、运行、参数、指标、artifacts、已记录模型和 traces 提供 API 与 UI。SDK 可以连接 HTTP tracking server，或直接连接本地文件/SQL backend。并非每次使用都需要单独的服务器进程。

即使使用远程服务器，元数据和 artifact 传输也可能采用不同路径。元数据经由 Tracking API 传输；artifacts 可以由服务器代理，也可以在客户端与 S3 等存储之间直接传输。下文将区分这些配置。

## 核心概念：Experiments 和 Runs

一个 **Experiment** 对 runs 及相关结果进行分组。一个 **Run** 除了可以表示训练，也可以表示评估、预处理或比较。在同一个 run 内，参数键不能改为不同的值。指标可以包含带有步骤的多个时间戳观测值；请区分当前汇总与完整历史记录。

以下值是 **Tracking API 固定示例，并非测量得到的模型准确率**。该示例会创建自己的 JSON artifact，而不依赖未定义的图像文件。

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".mlflow-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'mlflow.db'}")
client = MlflowClient()
experiment = client.get_experiment_by_name("tracking-demo")
experiment_id = (
    experiment.experiment_id if experiment else
    client.create_experiment(
        "tracking-demo", artifact_location=(root / "artifacts").as_uri()
    )
)
mlflow.set_experiment(experiment_id=experiment_id)

with mlflow.start_run(run_name="demo") as run:
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("demo_score", 0.92, step=0)
    mlflow.log_metric("demo_score", 0.95, step=1)
    mlflow.log_dict({"synthetic_example": True}, "summary.json")
    run_id = run.info.run_id

assert client.get_run(run_id).info.status == "FINISHED"
assert len(client.get_metric_history(run_id, "demo_score")) == 2
```

正常退出上下文会将 run 结束为 `FINISHED`；代码块内发生异常会将其结束为 `FAILED`。结束 run 不会备份 artifacts，也不会验证整个训练过程是否成功。重复执行该示例会向同一个 experiment 添加 run。该条件判断不会更改现有 experiment 的 artifact location。

### Autologging

`mlflow.autolog()` 会配置受支持的集成。所捕获的值、受支持的 framework 版本、模型记录和输入示例收集因集成而异。不要假设普通的 PyTorch 循环和 Lightning workflow 会获得完全相同的自动 instrumentation。请检查特定 framework 的 API 和版本支持；手动记录其他指标。

启用 autologging 前，请审查输入、输出、模型和数据样本的存储位置。启用该功能既不会移除 PII，也不会为每个自定义代码路径添加 instrumentation。

## MLflow 3 的转变：模型作为一等实体

一个 `LoggedModel` 具有自己的 `model_id`、状态、artifact location 和元数据。它可通过 `source_run_id` 引用训练 run，并与其他评估 runs、指标和 traces 建立关系。它不同于 Registered Models 和 Model Versions。

**在没有显式 `start_run()` 块的情况下调用 `log_model()` 本身并不是 3.x 的新特性。** 2.22.0 中的 `Model.log()` 已在必要时使用 `_get_or_start_run()`；3.16.0 的模型记录路径仍保留此行为。重要变化在于独立的模型身份和关系追踪。

完成上述 Tracking 设置后，以下代码会创建没有活动 run 的模型元数据：

```python
model = mlflow.initialize_logged_model(
    name="metadata-only", model_type="demo"
)
assert mlflow.active_run() is None
assert model.source_run_id is None
print(model.model_id, model.status)  # PENDING
```

它尚未包含可用的模型权重或模型 flavor。使用前请完成实际模型记录、artifact 保留和最终确定。`READY` 并不代表已获得部署批准、通过质量审核或安全审查。

## GenAI 和 LLM 可观测性：Tracing

MLflow Tracing 于 **2024-06-17 的 2.14.0** 中推出。3.x 扩展了模型、评估和 GenAI UI 集成；3.16.0 增加了 span links 和重新设计的 trace UI。Tracing 并非首次在版本 3 中成为可能。

一个 trace 通过 spans 表示检索、工具执行和 LLM 调用等请求步骤。请区分父/子结构与 span links。token 收集取决于集成和 provider 响应；检索或工具 spans 不一定具有 LLM token 或成本字段。成本估算需要模型标识、用量和价格信息，并非经核对的计费总额。

请在适当情况下结合自动 instrumentation 和手动 spans。输入、输出、异常、工具参数和推理过程可能包含敏感信息；请定义收集范围、访问、脱敏和保留策略。安装集成并不能确保路径覆盖完整或成本核算完备。

## Backend Store 与 Artifact Store

| Store 或默认值 | 含义 |
|---|---|
| Backend | experiment/run/parameter/metric/model 元数据；SQLite、PostgreSQL、MySQL 及其他受支持的 SQL stores |
| Artifact | 模型文件、图表、JSON 及其他文件；本地路径、S3 及其他 stores |
| 默认值 | 新的 3.16.0 环境使用 `sqlite:///mlflow.db`；如果 `./mlruns` 已存在，请检查兼容性行为 |
| 旧版文件 backend | 处于维护模式；为新的操作选择显式 SQL backend 和迁移计划 |

SQLite 也是关系数据库。它适用于小型本地练习；并发写入者、多个服务器副本、备份和高可用性需要单独评估。元数据数据库备份不会自动包含 artifact 文件。

### 使用远程服务器的两条 Artifact 路径

- **代理模式：**客户端使用 `mlflow-artifacts:` location，并通过服务器发送文件，服务器持有 artifact-store 权限。客户端可能不需要自己的 S3 访问权限，因此 tracking-server 身份验证和授权非常重要。
- **直接模式：**使用 `--no-serve-artifacts` 和直接的 `s3://...` artifact root 时，客户端自行访问存储。它们需要相关的 AWS 权限、网络访问和 libraries。

更改服务器 flags 不会追溯性地重写现有 experiment artifact URIs。请检查实际的 experiment/run URI。浏览器 UI 查询服务器 HTTP APIs；它不会直接连接 PostgreSQL。

![客户端和 web UI 连接到 Tracking server API，后者访问 SQL 元数据和 artifact storage。在直接 artifact 模式下，获得授权的客户端使用单独的文件传输路径访问 storage。](../../.gitbook/assets/en-ai-ml-mlflow-01-tracking-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-01-tracking-0.html)

## 后续步骤

[第 2 部分](02-model-registry.md)涵盖注册、版本和 aliases。[第 3 部分](03-eks-deployment.md)涵盖 EKS storage 和访问控制。仅更改 alias 不会自动重新部署每个 serving process。

## 主要来源

- [MLflow 3.16.0 发布](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
- [Artifact store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/artifact-store/)
- [2.22.0 模型记录实现](https://github.com/mlflow/mlflow/blob/v2.22.0/mlflow/models/model.py)
- [3.16.0 Tracking API 实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/fluent.py)
- [Tracing 于 2.14.0 中推出](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)

[返回主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/01-tracking-quiz.md)
