# 第 2 部分：MLflow 模型注册表

> **审查基线**：MLflow 3.16.0 · 2026-09-12

## 实验环境设置

使用 Python 3.10 或更高版本以及 `mlflow==3.16.0`。注册表 API 也可与本地 SQLite 配合使用；不强制要求单独的 HTTP 服务器。有关团队部署，请参阅[第 3 部分](03-eks-deployment.md)；有关 Tracking 设置，请参阅[第 1 部分](01-tracking.md)。本章介绍开源版（OSS）MLflow。Databricks Unity Catalog 等托管注册表可能具有不同的权限、复制和保留行为。

## 什么是模型注册表

注册表管理逻辑模型名称、编号版本、别名和元数据。记录候选模型、批准晋升以及部署端点是彼此独立的操作。拥有注册表并不会自动实现批准或服务行为。

## 核心概念

| 实体 | 含义和变更边界 |
|---|---|
| 注册模型 | 位于逻辑名称下的版本集合，例如 `fraud-detector` |
| 模型版本 | 包含源信息的编号记录；描述、标签、阶段/别名关系可以更改 |
| 别名 | 指向一个版本的可变名称；多个别名可以指向同一版本 |
| LoggedModel | 独立的 Tracking 模型实体；不同于注册模型和模型版本 |

### 模型版本

新的模型结果通常应成为新版本。但是，**并非每个版本字段和工件字节都是不可变的**。`update_model_version` 会更改描述；版本标签同样可变。拥有写入权限的人员可以更改外部 `source` URI 中的文件。注册表版本号并不强制对象不可变性或内容哈希。

`run_id` 和 `model_id` 在 `create_model_version` 中是可选的。从直接源 URI 注册时可以没有训练运行链接。注册是指针、复制工件，还是使用其他存储位置，取决于注册表后端和操作；请验证实际行为。

### 别名

`models:/fraud-detector@champion` 会在**解析/加载发生时**找到该别名对应的版本。`models:/fraud-detector/7` 是显式版本引用。移动别名不会自动替换已加载到内存或缓存中的模型。请分别实现服务控制器的部署、重新加载和缓存策略，并记录实际为请求提供服务的版本。

`champion` 和 `challenger` 是由团队定义的名称。它们不会配置实时/影子流量百分比，也不会自行运行评估。别名更新并不能证明已获得质量或安全批准。

### 旧版阶段模型

旧版阶段包括 `None`、`Staging`、`Production` 和 `Archived`。`transition_model_version_stage` 自 2.9.0 起已被**弃用**，并且仍存在于 3.16.0 API 中。不要将其描述为已从所有当前版本中移除。新工作流可以将别名和标签与环境特定的注册模型以及显式权限相结合。阶段名称或标签不是访问控制。

## 注册模型

记录实际风味模型后，调用 `mlflow.register_model(model_uri, name)`，或者将 `registered_model_name` 传递给该风味的 `log_model` 调用。更底层的 `MlflowClient.create_model_version` API 可以直接指定源。注册和别名重新分配是独立操作。

此**注册表元数据练习**不会创建可进行推理的模型。它已使用 Python 3.12、MLflow 3.16.0 和 SQLite 验证。

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".registry-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
client = MlflowClient()
name = "registry-contract-demo"
# Run once in a fresh demo DB. Inspect the existing name before repeating.
client.create_registered_model(name)
versions = []
for number in (1, 2):
    source = root / f"candidate-{number}"
    source.mkdir(exist_ok=True)
    (source / "metadata.json").write_text('{"fixture": true}')
    versions.append(client.create_model_version(name, source=source.as_uri()))

first, second = versions
assert first.run_id is None
client.update_model_version(name, first.version, description="metadata fixture")
client.set_model_version_tag(name, first.version, "review_state", "demo-only")
client.set_registered_model_alias(name, "champion", first.version)
snapshot = client.get_model_version_by_alias(name, "champion")
client.set_registered_model_alias(name, "champion", second.version)
assert snapshot.version == first.version
assert client.get_model_version_by_alias(name, "champion").version == second.version
```

`READY` 是注册状态。如上所示，没有模型风味或权重的元数据固定装置也可以注册；请单独测试推理兼容性和评估标准。该练习会将其本地数据库和固定装置保留在 `.registry-demo` 中。

## 治理与交接工作流

1. 记录实际源工件、模型/代码/数据哈希、依赖项以及运行/模型引用。
2. 评估质量、安全性和业务标准；保留批准证据。
3. 授权主体调用 `set_registered_model_alias`。完成训练并不等于自动批准。
4. 服务系统解析新引用并执行重新加载或部署。在需要可复现性和回滚时，固定版本号和工件哈希。

将候选模型创建与晋升分离需要身份验证、授权和运行管道。仅有 `review_state=approved` 这样的标签并不会限制写入权限，也无法使批准证据防篡改。请协调来自多个部署作业的并发别名更新。

![消费者将 champion 和 challenger 别名解析为模型版本引用。别名解析不会路由流量，也不会自动替换已经加载的模型。](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## 血缘与可复现性

血缘的完整性仅取决于所记录和保留的信息。注册表无法在事后重建缺失的 `run_id`、`model_id`、代码修订或数据集哈希。已更改的源文件、已删除的运行/模型版本以及工件清理也会留下不完整的链接。

审计需要实际提供服务的版本/模型 ID、工件哈希和位置、源提交、数据集快照、依赖项，以及评估/批准记录。请共同维护元数据数据库和工件存储的备份与保留策略。别名不是所有更改的永久审计日志。

## 后续步骤

[第 3 部分：EKS 部署](03-eks-deployment.md)介绍服务器、数据库和工件权限边界。

## 主要来源

- [模型注册表](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [3.16.0 注册表客户端 API](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [ModelVersion 字段](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [OSS SQL 注册表实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
