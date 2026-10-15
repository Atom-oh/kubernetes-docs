# 第 2 部分：MLflow 模型注册表

> **审查基线**：MLflow 3.16.0；已检查最新补丁 3.16.1 · 2026-10-12

## 实验环境设置

使用 Python 3.10 或更高版本以及 `mlflow==3.16.0`。注册表 API 也可与本地 SQLite 配合使用；不强制要求单独的 HTTP 服务器。补丁 3.16.1 已可用，但本章示例使用 3.16.0，且尚未在 3.16.1 上重新运行。

有关团队部署，请参阅[第 3 部分](03-eks-deployment.md)；有关 Tracking 设置，请参阅[第 1 部分](01-tracking.md)。本章介绍 OSS MLflow。Databricks Unity Catalog 等托管注册表可能具有不同的权限、复制和保留行为。

## 什么是模型注册表

注册表管理逻辑模型名称、编号版本、别名和元数据。记录候选模型、批准晋级和部署端点是彼此独立的操作。拥有注册表不会自动实施审批或服务行为。

## 核心概念

| 实体 | 含义与变更边界 |
|---|---|
| Registered Model | 逻辑名称下的版本集合，例如 `fraud-detector` |
| Model Version | 包含源信息的编号记录；描述、标签、stage/alias 关系可以更改 |
| Alias | 指向某个版本的可变名称；多个别名可以指向同一版本 |
| LoggedModel | 独立的 Tracking 模型实体；不同于 Registered Models 和 Model Versions |

### 模型版本

新的模型结果通常应成为新版本。但是，**并非每个版本字段和每个 artifact 字节都是不可变的**。`update_model_version` 会更改描述；版本标签同样可变。具有写入权限的人员可以更改外部 `source` URI 中的文件。注册表版本号并不强制对象不可变性或内容哈希。

`run_id` 和 `model_id` 在 `create_model_version` 中是可选的。从直接源 URI 注册可能没有训练运行链接。注册是指针、复制 artifact，还是使用其他存储位置，取决于注册表后端和操作；请验证实际行为。

### 别名

`models:/fraud-detector@champion` 会在**发生解析/加载时**找到该别名的版本。`models:/fraud-detector/7` 是显式版本引用。移动别名不会自动替换已加载到内存或缓存中的模型。请分别实施服务控制器的部署、重新加载和缓存策略，并记录实际为请求提供服务的版本。

`champion` 和 `challenger` 是团队定义的名称。它们不会配置实时/影子流量百分比，也不会自行运行评估。别名更新并非质量或安全审批的证据。

### 旧版 Stage 模型

旧版 stage 包括 `None`、`Staging`、`Production` 和 `Archived`。`transition_model_version_stage` 自 2.9.0 起已被**弃用**，且仍存在于 3.16.0 API 中。不要将其描述为已从所有当前版本中移除。新工作流可将别名和标签与特定环境的 Registered Models 及显式权限结合使用。stage 名称或标签不是访问控制。

## 注册模型

记录实际 flavor 模型后，调用 `mlflow.register_model(model_uri, name)`，或者将 `registered_model_name` 传递给该 flavor 的 `log_model` 调用。较低层级的 `MlflowClient.create_model_version` API 可以直接指定源。注册和重新分配别名是独立操作。

此**注册表元数据练习**不会创建可用于推理的模型。它已使用 Python 3.12、MLflow 3.16.0 和 SQLite 进行检查。

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

`READY` 是一种注册状态。如上所示，没有模型 flavor 或权重的元数据 fixture 可以注册；请单独测试推理兼容性和评估标准。该练习会将本地数据库和 fixture 保留在 `.registry-demo` 中。

## 治理与交接工作流

1. 记录实际的源 artifact、模型/代码/数据哈希、依赖项以及运行/模型引用。
2. 评估质量、安全和业务标准；保留审批证据。
3. 获授权的执行者调用 `set_registered_model_alias`。完成训练并不等于自动获得审批。
4. 服务系统解析新引用并执行重新加载或部署。在需要可复现性和回滚时，固定版本号和 artifact 哈希。

将候选模型创建与晋级分离需要身份验证、授权和运行管道。仅有 `review_state=approved` 这样的标签并不会限制写入权限，也不会使审批证据防篡改。请协调来自多个部署作业的并发别名更新。

![使用者将 champion 和 challenger 别名解析为 Model Version 引用。别名解析不会路由流量，也不会自动替换已加载的模型。](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## 血缘与可复现性

血缘的完整程度取决于已记录和保留的信息。注册表无法在之后重建缺失的 `run_id`、`model_id`、代码修订版本或数据集哈希。已更改的源文件、已删除的 Runs/Model Versions 和 artifact 清理也可能留下不完整的链接。

审计需要实际提供服务的版本/模型 ID、artifact 哈希和位置、源提交、数据集快照、依赖项以及评估/审批记录。请一并管理元数据数据库和 artifact 存储的备份与保留策略。别名并非所有变更的永久审计日志。

## 后续步骤

[第 3 部分：EKS 部署](03-eks-deployment.md)介绍服务器、数据库和 artifact 权限边界。

## 主要来源

- [模型注册表](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [3.16.0 注册表客户端 API](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [ModelVersion 字段](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [OSS SQL 注册表实现](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[返回主页](README.md) · [测验](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
