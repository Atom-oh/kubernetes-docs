# 第 1 部分：MLflow 跟踪

> **审查基线**：MLflow 3.16.0；已检查最新补丁 3.16.1 · 2026-10-12

## 实验环境设置

使用 Python 3.10 或更高版本安装 `mlflow==3.16.0`。以下示例已在 Python 3.12、SQLite 和本地 artifact 存储环境中验证。它不需要 GPU、已训练模型或远程服务器。

补丁 3.16.1 已可用，但本示例尚未使用它重新运行。[第 3 部分](03-eks-deployment.md)介绍团队 HTTP 服务器和 EKS 操作。

## 什么是 MLflow Tracking？

Tracking 为实验、运行、参数、指标、artifact、已记录模型和 trace 提供 API 与 UI。SDK 可连接到 HTTP 跟踪服务器，或直接连接到本地文件/SQL 后端。并非每次使用都需要单独的服务器进程。

即使使用远程服务器，元数据和 artifact 的传输也可能采用不同路径。元数据通过跟踪 API 传递；artifact 可以由服务器代理，也可在客户端与 S3 等存储之间直接传输。下文将区分这些配置。

## 核心概念：实验和运行

**Experiment** 将运行及相关结果分组。除了训练之外，**Run** 还可以表示评估、预处理或比较。一个参数键在同一运行中不能更改为不同的值。指标可以具有带步骤的多个带时间戳观测值；请区分当前摘要与完整历史记录。

以下值是 **Tracking API 固定示例数据，而非实测的模型准确率**。该示例创建其 JSON artifact，而不是依赖一个未定义的图像文件。

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

正常退出上下文会使运行以 `FINISHED` 结束；代码块中发生异常会使其以 `FAILED` 结束。运行终止不会备份 artifact，也不会验证整个训练过程是否成功。重复该示例会向同一实验添加一次运行。此条件判断不会更改现有实验的 artifact 位置。

### 自动记录

`mlflow.autolog()` 会配置受支持的集成。捕获的值、受支持的框架版本、模型记录和输入示例收集因集成而异。不要假定普通的 PyTorch 循环和 Lightning 工作流会获得相同的自动插桩。请检查特定框架的 API 和版本支持，并手动记录额外指标。

启用自动记录前，请审查输入、输出、模型和数据样本的存储位置。启用此功能既不会移除 PII，也不会为每条自定义代码路径添加插桩。

## MLflow 3 的转变：模型作为一等实体

`LoggedModel` 有自己的 `model_id`、状态、artifact 位置和元数据。它可通过 `source_run_id` 引用训练运行，并可与其他评估运行、指标和 trace 建立关系。它不同于 Registered Models 和 Model Versions。

**在没有显式 `start_run()` 代码块的情况下调用 `log_model()` 本身并不是 3.x 中的新功能。** 2.22.0 中的 `Model.log()` 已在必要时使用 `_get_or_start_run()`；3.16.0 的模型记录路径仍保持此行为。重要变化是独立的模型标识和关系跟踪。

完成以上跟踪设置后，以下代码会在没有活动运行的情况下创建模型元数据：

```python
model = mlflow.initialize_logged_model(
    name="metadata-only", model_type="demo"
)
assert mlflow.active_run() is None
assert model.source_run_id is None
print(model.model_id, model.status)  # PENDING
```

它尚不包含可用的模型权重或模型 flavor。请在使用前完成实际的模型记录、artifact 保留和最终确定。`READY` 并不代表已获得部署批准、质量认可或安全审查。

## GenAI 和 LLM 可观测性：追踪

MLflow Tracing 于 **2024-06-17 的 2.14.0** 中引入。3.x 扩展了模型、评估和 GenAI UI 集成；3.16.0 增加了 span 链接和重新设计的 trace UI。Tracing 并非在版本 3 中才首次可用。

一个 trace 表示检索、工具执行和 LLM 调用等请求步骤，并包含 span。请区分父/子结构与 span 链接。token 收集取决于集成和提供程序响应；检索或工具 span 不一定具有 LLM token 或成本字段。成本估算需要模型标识、用量和价格信息，且不等同于核对后的账单总额。

在适当处将自动插桩与手动 span 结合使用。输入、输出、异常、工具参数和推理可能包含敏感信息；请定义收集范围、访问权限、脱敏和保留策略。安装集成并不能确保完整的路径覆盖或成本核算。

## Backend Store 与 Artifact Store

| 存储类型或默认值 | 含义 |
|---|---|
| Backend | 实验/运行/参数/指标/模型元数据；SQLite、PostgreSQL、MySQL 及其他受支持的 SQL 存储 |
| Artifact | 模型文件、绘图、JSON 及其他文件；本地路径、S3 及其他存储 |
| 默认值 | 新的 3.16.0 环境使用 `sqlite:///mlflow.db`；如果 `./mlruns` 已存在，请检查兼容性行为 |
| 旧版文件后端 | 处于维护模式；对于新操作，请选择明确的 SQL 后端和迁移计划 |

SQLite 也是关系数据库。它适合小型本地练习；并发写入者、多个服务器副本、备份和高可用性需要单独评估。元数据数据库备份不会自动包含 artifact 文件。

### 使用远程服务器的两条 Artifact 路径

- **代理模式：**客户端使用 `mlflow-artifacts:` 位置并通过服务器发送文件，服务器持有 artifact 存储权限。客户端可能不需要自己的 S3 访问权限，因此跟踪服务器的身份验证和授权非常重要。
- **直接模式：**使用 `--no-serve-artifacts` 和直接的 `s3://...` artifact 根路径时，客户端自行访问存储。它们需要相关的 AWS 权限、网络访问和库。

更改服务器标志不会追溯性地重写现有实验的 artifact URI。请检查实际的实验/运行 URI。浏览器 UI 查询服务器 HTTP API；它不会直接连接到 PostgreSQL。

![客户端和 Web UI 连接到 Tracking server API，后者访问 SQL 元数据和 artifact 存储。在直接 artifact 模式下，已授权客户端通过单独的文件传输路径访问存储。](../../.gitbook/assets/en-ai-ml-mlflow-01-tracking-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-01-tracking-0.html)

## 后续步骤

[第 2 部分](02-model-registry.md)介绍注册、版本和别名。[第 3 部分](03-eks-deployment.md)介绍 EKS 存储和访问控制。仅更改别名不会自动重新部署每个服务进程。

## 主要来源

- [MLflow 3.16.0 发布说明](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
- [Artifact store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/artifact-store/)
- [2.22.0 模型记录实现](https://github.com/mlflow/mlflow/blob/v2.22.0/mlflow/models/model.py)
- [3.16.0 Tracking API 实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/fluent.py)
- [2.14.0 中引入 Tracing](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)

[返回主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/01-tracking-quiz.md)
