# Kubeflow Pipelines 测验

本测验用于检验你对 Kubeflow Pipelines 架构、KFP v2 IR YAML 编译模型、核心概念（Pipeline、Component、Run、Experiment、Artifact、MLMD）、EKS Artifact 存储注意事项以及缓存行为的理解。

## 选择题

1. Kubeflow Pipelines 后端实际上使用哪个工作流引擎来调度和运行 Pipeline 各步骤的 Pods？
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 直接使用 Kubernetes CronJobs，不使用底层工作流引擎

<details>

<summary>显示答案</summary>

**答案：B) Argo Workflows**

**说明：**
KFP 的后端构建于 Argo Workflows 之上。编译后的 Pipeline 到达 KFP API server 后，会被转换为 Argo `Workflow` 资源，随后 Argo 的 controller 会创建并按顺序执行 Pods。KFP 在其上提供 Python SDK、UI、Experiment/Run 跟踪以及 MLMD store。
</details>

2. KFP v1 SDK compiler 和 KFP v2 SDK compiler 在架构上的关键差异是什么？
   - A) v1 编译为 IR YAML；v2 直接编译为 Argo Workflow YAML
   - B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示（IR）YAML
   - C) 没有差异——两者生成完全相同的输出
   - D) v2 完全不再需要编译

<details>

<summary>显示答案</summary>

**答案：B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示（IR）YAML**

**说明：**
v1 SDK 的 `dsl-compile` 会直接生成 Argo 专用的 `Workflow` YAML manifest。v2 SDK 编译为与后端无关的 IR YAML（`PipelineSpec`），其中描述 DAG、Components 和类型化 Artifacts；KFP 后端会在提交时将该 IR 转换为 Argo `Workflow`。
</details>

3. Kubeflow Pipelines 的哪个组件负责记录每次 Component 执行、其输入/输出以及所涉及的 Artifacts，从而支持在 KFP UI 中进行 lineage 追踪？
   - A) Argo Workflow Controller
   - B) ML Metadata (MLMD) store
   - C) MinIO artifact store
   - D) KFP SDK Compiler

<details>

<summary>显示答案</summary>

**答案：B) ML Metadata (MLMD) store**

**说明：**
MLMD（通常由 MySQL 支持）会记录每次 Component 执行及其输入、输出和所涉及的 Artifacts。正是这一机制使 KFP UI 能够跨 Run 回溯已训练模型所使用的确切数据集和生成它的代码。
</details>

4. 在 KFP v2 SDK 中，Component 如何声明自己会生成供下游 Components 使用的 `Dataset` 类型 Artifact？
   - A) 返回一个普通 Python dictionary
   - B) 声明一个类型为 `Output[Dataset]` 的参数
   - C) 写入硬编码的 `/tmp/dataset.csv` 路径而不进行类型声明
   - D) 设置名为 `DATASET` 的环境变量

<details>

<summary>显示答案</summary>

**答案：B) 声明一个类型为 `Output[Dataset]` 的参数**

**说明：**
KFP v2 为 Artifacts 提供一等类型（`Dataset`、`Model`、`Metrics` 等）。类型为 `Output[Dataset]` 的 Component 参数会让 SDK 配置存储路径，并将该 Artifact 连接到任何声明了匹配 `Input[Dataset]` 参数的下游 Component。
</details>

5. 如果不进行任何重新配置，KFP 默认使用什么 Artifact 存储后端？`awslabs/kubeflow-manifests` 项目的 S3 方案对其做了什么改变？
   - A) 默认使用 S3；该方案将其切换为 MinIO
   - B) 默认使用集群内 MinIO deployment；该方案重新配置 pipeline root 和 artifact store credentials，改为使用 S3
   - C) 没有默认 artifact store——必须始终手动配置
   - D) 默认使用 EFS；该方案将其切换为 EBS

<details>

<summary>显示答案</summary>

**答案：B) 默认使用集群内 MinIO deployment；该方案重新配置 pipeline root 和 artifact store credentials，改为使用 S3**

**说明：**
KFP 附带集群内 MinIO deployment 作为默认 artifact store。在 EKS 上，这意味着要运行一个额外的 stateful service，而 S3 已经提供了相同能力。`awslabs/kubeflow-manifests` 说明了如何重新配置 pipeline root 和 artifact credentials，使 Components 直接从 S3 读取和写入。
</details>

6. 当 KFP 的 artifact store 指向 S3 而非集群内 MinIO 时，哪种身份机制会与 KFP pipeline pods（例如 `pipeline-runner` ServiceAccount）直接相关？
   - A) 无——无需任何 AWS 身份配置即可访问 S3
   - B) IRSA 或 EKS Pod Identity，为 ServiceAccount 授予 S3 bucket 权限
   - C) 将硬编码的 AWS access key 打包到每个 Component 的 container image 中
   - D) 仅 Kubernetes RBAC 就足以访问 S3

<details>

<summary>显示答案</summary>

**答案：B) IRSA 或 EKS Pod Identity，为 ServiceAccount 授予 S3 bucket 权限**

**说明：**
一旦 Artifact 读取/写入直接面向 AWS 而非集群内 MinIO endpoint，运行 KFP pipeline pods 的 ServiceAccount 就需要拥有对该 S3 bucket 具备权限的 IRSA role 或 EKS Pod Identity association。
</details>

7. 在示例的两步 Pipeline（`prepare_data` -> `train_model`）中，如何将 `Dataset` Artifact 从第一个 Component 传递给第二个？
   - A) 写入由两个 Components 共享的全局变量
   - B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个 Component 声明的输出连接到第二个 Component 的类型化输入
   - C) 将其存储在环境变量中
   - D) 两个 Components 无法共享数据；必须合并为一个 Component

<details>

<summary>显示答案</summary>

**答案：B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个 Component 声明的输出连接到第二个 Component 的类型化输入**

**说明：**
在由 `@dsl.pipeline` 装饰的函数中，`prep_task.outputs["output_dataset"]` 指向 `prepare_data` 声明的 `Output[Dataset]` 参数；将其传入 `train_model` 的 `input_dataset: Input[Dataset]` 参数，即可让 SDK 在这两个独立运行的 Pods 之间连接 Artifact dependency。
</details>

8. KFP 如何决定复用缓存结果而不是重新运行 Component？
   - A) 无论输入如何，它始终重新运行每个 Component
   - B) 它会对 Component 的输入（参数值、输入 Artifact 内容以及 Component 自身定义）进行哈希，并在与先前成功执行的哈希匹配时复用缓存的输出
   - C) 仅当 Pipeline 名称发生变化时才重新运行 Components
   - D) 缓存仅基于距上次 Run 的实际时间

<details>

<summary>显示答案</summary>

**答案：B) 它会对 Component 的输入（参数值、输入 Artifact 内容以及 Component 自身定义）进行哈希，并在与先前成功执行的哈希匹配时复用缓存的输出**

**说明：**
KFP 通过对 Component 的输入进行哈希来缓存其执行。后续 Run 提交具有匹配输入哈希的 Component 时，会跳过重新执行并复用之前缓存的输出。
</details>

## 简答题

9. 请列出本章介绍的两种禁用 KFP 缓存行为的方法。

<details>

<summary>显示答案</summary>

**答案：针对单个 Component，在任务上使用 `set_caching_options(enable_caching=False)`；针对单个 Run，使用 KFP UI 的 Run 提交对话框中提供的缓存开关。**

**说明：**
`prep_task.set_caching_options(enable_caching=False)` 会在 Pipeline 函数中禁用一个特定 Component task 的缓存。或者，也可以在 Run 提交时禁用整个 Pipeline submission 的缓存，而不是逐个 Component 禁用。
</details>

10. KFP SDK 的编译步骤实际生成什么？该输出到达 KFP API server 后会发生什么？

<details>

<summary>显示答案</summary>

**答案：它生成中间表示（IR）YAML——与后端无关的 `PipelineSpec`。到达 API server 后，后端会将该 IR YAML 转换为 Argo `Workflow`，之后 Argo 的 controller 会将其调度为 Pods。**

**说明：**
KFP SDK 的职责止于生成 IR YAML。从 API server 开始的一切——转换为 Argo Workflow 和 Pod 调度——均由后端负责，这也是 IR YAML 原则上能够与后端无关的原因。
</details>

## 实操题

11. 编写一个名为 `prepare_data` 的 `@dsl.component` 函数，声明一个 `Output[Dataset]` 参数，并将 pandas DataFrame 以 CSV 格式写入其中。

<details>

<summary>显示答案</summary>

**答案：**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.11-slim")
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**说明：**
`output_dataset: Output[Dataset]` 声明了一个类型化 Artifact 输出；SDK 会将 `output_dataset.path` 配置为 Component 写入的存储位置，下游 Components 随后可将其声明为 `Input[Dataset]`。
</details>

12. 编写一个 `@dsl.pipeline` 函数，将 `prepare_data` 的输出连接到 `train_model` Component 的 `input_dataset` 参数。

<details>

<summary>显示答案</summary>

**答案：**
```python
from kfp import dsl

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])
```

**说明：**
`prep_task.outputs["output_dataset"]` 引用由 `prepare_data` 的 `Output[Dataset]` 参数（名为 `output_dataset`）生成的 Artifact；将其作为 `train_model` 的 `input_dataset` 参数传入，会在两个 Components 之间创建 DAG edge。
</details>

13. 编写代码，为名为 `prep_task` 的单个 Pipeline task 禁用缓存。

<details>

<summary>显示答案</summary>

**答案：**
```python
prep_task.set_caching_options(enable_caching=False)
```

**说明：**
在 Pipeline 函数中对 task object 调用 `set_caching_options(enable_caching=False)`，会禁用该特定 Component 执行的缓存，即使存在先前 Run 中匹配的缓存结果，也会强制其重新运行。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/02-pipelines.md) | [下一份测验：Notebooks](./03-notebooks-quiz.md)
