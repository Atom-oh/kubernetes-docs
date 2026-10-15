# 第 2 部分：Kubeflow Pipelines

> **支持的版本**：Kubeflow Pipelines 2.16.1, Kubeflow Community Distribution 26.03.1
> **已检查的最新独立发布版本**：KFP 2.17.2 (September 4, 2026; PyPI 上最新的 `kfp` SDK：2.17.0)，检查日期为 October 12, 2026；示例使用 2.16.1
> **最后更新**：October 12, 2026

## 实验环境设置

本地编译需要 Python 和 `kfp==2.16.1`；本章使用 Python 3.12 进行了检查。上游 KFP 2.17.2 已可用（PyPI 上最新的 `kfp` SDK 包为 2.17.0），但此固定版本与 Community Distribution 26.03.1 相匹配。它并未验证新的 SDK/backend 组合。

编译不会连接到 cluster。远程执行需要兼容的 KFP backend、已认证的 client 和 namespace 权限。S3 还要求执行用 ServiceAccount 具备 workload identity，并要求访问 artifact 的组件拥有相应配置。

## Kubeflow Pipelines 是什么

KFP 使用带类型的 parameter/artifact 连接组件并跟踪 Run。此处使用的开源 KFP 2.16.1 backend 会将 IR 转换为 Argo Workflows。Argo 管理 workflow 顺序和 Pod 创建；Kubernetes scheduler 将 Pod 放置到 node 上。缓存的 task、importer 和嵌套 DAG 意味着每个逻辑 task 并不对应一次单独的用户 container 执行。

## KFP v2 架构：IR YAML 与 Backend 执行

Community Distribution 26.03.1 捆绑了 KFP 2.16.1。旧版 v1 默认编译路径生成 Argo Workflow YAML；v2 `Compiler().compile(...)` 生成基于 PipelineSpec 的 IR YAML。上传/存储 Pipeline 与创建 Run 是不同的操作。仅上传不会执行它。

IR 避免直接编写 Argo object，但它不保证能无约束地移植到每个 backend。IR/SDK 版本、支持的特性、Kubernetes platform extension、authentication 和 storage 必须与目标相匹配。`kfp` 包还提供 client API 和 Python component 执行支持；它的作用并不止于编译。

## 核心概念

| 概念 | 角色和范围 |
| --- | --- |
| Pipeline | 使用 `@dsl.pipeline` 编写的图；上传的定义/版本与执行是分开的 |
| Component / Task | 可复用 component 定义与图调用；轻量级 Python 是与 container/importer/graph 并列的一种形式 |
| Run / Experiment | 带输入的执行和一组相关 Run；不同于 Katib 的 Experiment CRD |
| Parameter | 字符串、数字和小型结构化输入/输出值 |
| Artifact | 带 URI、类型和 metadata 的 Dataset/Model/Metrics 类 object；不一定是单个文件 |
| MLMD | 已登记的 execution、artifact 和关系；不会自动记录每个外部 side effect 或文件完整性 |

Metadata 记录与 artifact 字节是分开的。当可复现性和内容验证很重要时，请记录 code/image/data revision 和 hash。

## Pipeline Run 如何流经系统

![Kubeflow Pipelines Run 流程：Python DSL Pipeline 被编译为 IR YAML 并提交至 KFP API server，随后转换为运行 component Pod 的 Argo Workflow；这些 Pod 将 artifact 写入 S3/MinIO，并将 metadata 记录到 MLMD。](../../.gitbook/assets/en-ai-ml-kubeflow-02-pipelines-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-02-pipelines-0.html)

编译在本地进行。创建 Run 后，API server、Argo、KFP driver/launcher 和用户 container 协同工作。launcher/runtime 处理 artifact path、传输和 metadata。Kubernetes node placement 仍与 Argo 的 workflow sequencing 分离。

## EKS 专用 Artifact Storage

所审阅的 distribution 默认安装包含 MinIO，但并非每个 KFP installation 或 artifact URI 都使用它。请检查 pipeline root、导入的 URI 和 provider configuration。诸如 Metrics 这类面向 metadata 的 artifact 不一定是 metric 文件。

对于 S3，请使用[当前 object-store 指南](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/)配置 `pipeline_root`、provider 和 credential chain。S3 会产生 storage、request 和 transfer 费用；它不是免费的默认 artifact service。

不要假设 `pipeline-runner` 在每个环境中都是执行用 ServiceAccount。请检查 Run 所选的 account 和实际 Pod，以及 API server/launcher 所需的访问权限。当前指南中记录了 IRSA。Pod Identity 需要验证 SDK、agent、association 和 runtime support；本章未执行 AWS integration。[第 1 部分](01-architecture-installation.md)解释了这些边界以及旧版 AWS distribution 的 installation limitation。

## 一个简单的两步 Pipeline

以下内容使用 KFP v2 SDK 的 decorator 展示了一个最小化的 `data-prep -> train` Pipeline，其中带类型的 `Dataset` artifact 从第一个 component 传递到第二个：

```python
from kfp import dsl, compiler
from kfp.dsl import Dataset, Model, Output, Input

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    # In a real pipeline this would read from S3 or another source
    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)

@dsl.component(base_image="python:3.12-slim", packages_to_install=["scikit-learn==1.7.2", "pandas==2.3.3"])
def train_model(input_dataset: Input[Dataset], output_model: Output[Model]):
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    import pickle

    df = pd.read_csv(input_dataset.path)
    clf = LogisticRegression().fit(df[["feature"]], df["label"])
    with open(output_model.path, "wb") as f:
        pickle.dump(clf, f)

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])

compiler.Compiler().compile(
    pipeline_func=data_prep_train_pipeline,
    package_path="data_prep_train_pipeline.yaml",
)
```

`Output[Dataset]` 到 `Input[Dataset]` 的连接记录了 graph dependency 和 artifact type。实际的 `.path` 准备和传输发生在 runtime。编译不会验证 storage 或 training。

这些是轻量级 Python component。`@dsl.component` 会提取 function code；它不会自动构建 image。`packages_to_install` 在 base image 中的执行时安装 dependency。先前的示例遗漏了 prepare_data 的 pandas；现在两个 component 都声明了各自的 dependency，并且其 function body 已在本地检查。对于 production，请将 dependency 预构建到 container 中，固定其 digest，并单独测试该 container。这里的 Python image tag 和 transitive dependency 并非完全锁定的 build。

只加载由本练习生成的可信 pickle。加载外部 pickle 可能执行任意 code。这个小型 model 演示 API，并非 model quality validation result。

## Caching 行为

在 2.16.1 中，该 key 包括 input parameter value、input artifact **name/ID**、output specification、container image string、command/argument 和 PVC name。Cache lookup 的作用域是 Pipeline name 和 namespace。它不会在每次 lookup 时读取并 hash input artifact file byte。

因此，修改同一 artifact ID 背后的文件、image tag 或外部 database/API state 可能使 key 保持不变。现有的 cache metadata 也不能确保已删除的 output object 在下游仍可读取。请将 data version/hash 作为显式 parameter 传递，并考虑为可变的外部 state 或 side effect 禁用 caching。

```python
# Inside the pipeline function, disable caching for this task.
prep_task.set_caching_options(enable_caching=False)
```

已认证 client 的 `create_run_from_pipeline_package(..., enable_caching=False)` 会覆盖 Run 的 task caching；`None` 保留已编译的 task setting。CLI default 和 `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT` 也可以更改 compilation default；请在导入 KFP 前设置 environment variable。

## 验证与来源

IR 使用 Python 3.12 / KFP 2.16.1 编译，并检查了 dependency、type 和 caching setting。function body 已在本地 CPU 上使用 pandas 2.3.3 / scikit-learn 1.7.2 执行。未测试 Docker、Argo、cluster cache reuse、S3 和 Pod Identity execution。

- [2.16.1 cache-key 实现](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/cacheutils/cache.go)
- [2.16.1 cache lookup 和 reuse](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/driver/cache.go)
- [官方 caching 指南](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/caching/)
- [轻量级 Python component](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/)

## 后续步骤

在 Pipeline 被编写、编译和运行后，接下来的问题通常是这些 Pipeline component 背后的交互式开发工作最初在哪里进行。[第 3 部分：Kubeflow Notebooks](./03-notebooks.md)介绍团队用来编写并迭代最终打包为 Pipeline component 的 code 的每用户 notebook environment；而在本系列的后续内容中，[第 6 部分：KServe — Kubernetes 上的 Model Serving](./06-kserve.md)介绍这些 Pipeline 最终生成的 model 的 serving。

[返回主页面](./README.md)

## 测验

要测试你在本章所学的内容，请尝试[主题测验](../../quizzes/ai-ml/kubeflow/02-pipelines-quiz.md)。
