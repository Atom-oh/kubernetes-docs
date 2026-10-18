# Kubeflow Pipelines 测验

本测验将考查你对 Kubeflow Pipelines 架构、KFP v2 IR YAML 编译模型、核心概念（Pipeline、Component、Run、Experiment、Artifact、MLMD）、EKS artifact 存储注意事项以及缓存行为的理解。

## 单项选择题

1. 在此处使用的开源 KFP 2.16.1 后端中，哪个引擎负责管理工作流顺序和 Pod 创建？
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 直接使用 Kubernetes CronJobs，不使用底层工作流引擎

<details>

<summary>显示答案</summary>

**答案：B) Argo Workflows**

**解释：**
此后端会将 Run 的 IR 转换为 Argo Workflow 资源。Argo 负责管理顺序和 Pod 创建；Kubernetes 调度器负责将 Pod 放置到节点上。仅上传 pipeline 并不会创建 Run。
</details>

2. KFP v1 SDK 编译器与 KFP v2 SDK 编译器在架构上的关键区别是什么？
   - A) v1 编译为 IR YAML；v2 直接编译为 Argo Workflow YAML
   - B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示（IR）YAML
   - C) 两者没有区别；输出完全相同
   - D) v2 不再需要编译

<details>

<summary>显示答案</summary>

**答案：B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示（IR）YAML**

**解释：**
v1 SDK 的 `dsl-compile` 会直接生成特定于 Argo 的 `Workflow` YAML 清单。v2 SDK 会编译为与后端无关的 IR YAML（`PipelineSpec`），用于描述 DAG、组件和类型化 artifact；创建 Run 时，此后端会转换 IR，但需考虑后端版本和平台扩展的兼容性。
</details>

3. Kubeflow Pipelines 的哪个组件负责记录已注册的执行及其输入/输出 artifact 关系，从而在 KFP UI 中实现 lineage 跟踪？
   - A) Argo Workflow Controller
   - B) ML Metadata (MLMD) 存储
   - C) MinIO artifact 存储
   - D) KFP SDK 编译器

<details>

<summary>显示答案</summary>

**答案：B) ML Metadata (MLMD) 存储**

**解释：**
MLMD 存储已注册的执行/artifact 关系，而不是每一种外部副作用或文件字节的完整性。为确保可复现性，请记录代码/数据版本和哈希值。
</details>

4. 在 KFP v2 SDK 中，组件如何声明其会生成一个类型为 `Dataset` 的 artifact，供下游组件使用？
   - A) 返回普通 Python 字典
   - B) 声明一个类型为 `Output[Dataset]` 的参数
   - C) 写入硬编码的 `/tmp/dataset.csv` 路径，且不声明类型
   - D) 设置名为 `DATASET` 的环境变量

<details>

<summary>显示答案</summary>

**答案：B) 声明一个类型为 `Output[Dataset]` 的参数**

**解释：**
KFP v2 为 artifact 提供了一级类型（`Dataset`、`Model`、`Metrics` 等）。类型为 `Output[Dataset]` 的组件参数会声明类型和连接关系；运行时会准备路径，并将该 artifact 传递给声明了匹配的 `Input[Dataset]` 参数的任何下游组件。
</details>

5. 在所评审的默认安装中，若要使用 S3 而非 MinIO，需要做什么？
   - A) 默认使用 S3；该模式会将其切换为 MinIO
   - B) 配置 pipeline root、provider 和凭证链，以使用 S3 替代捆绑的 MinIO
   - C) 默认没有 artifact 存储；必须始终手动配置
   - D) 默认使用 EFS；该模式会将其切换为 EBS

<details>

<summary>显示答案</summary>

**答案：B) 配置 pipeline root、provider 和凭证链，以使用 S3 替代捆绑的 MinIO**

**解释：**
默认捆绑包包含 MinIO，但其他安装方式和导入的 artifact URI 可能有所不同。请使用当前的 KFP 对象存储指南。S3 会产生存储、请求和传输费用；旧版 AWS 发行版指南并非经过验证的当前版本安装说明。
</details>

6. 将 KFP 的 artifact 存储指向 S3，而非集群内的 MinIO 时，哪种身份机制会直接关系到实际 Run 执行 ServiceAccount 和访问 artifact 的组件？
   - A) 无：S3 访问不需要任何 AWS 身份配置
   - B) IRSA 或 Pod Identity，并验证 SDK、信任关系、运行时支持和限定范围的 S3 权限
   - C) 将硬编码的 AWS 访问密钥嵌入每个组件的容器镜像
   - D) 仅 Kubernetes RBAC 就足以访问 S3

<details>

<summary>显示答案</summary>

**答案：B) IRSA 或 Pod Identity，并验证 SDK、信任关系、运行时支持和限定范围的 S3 权限**

**解释：**
当 artifact 读写直接访问 AWS，而不是集群内的 MinIO 端点时，运行 KFP pipeline Pod 所使用的 ServiceAccount 需要关联一个具有该 S3 bucket 权限的 IRSA 角色或 EKS Pod Identity。
</details>

7. 在两步示例 pipeline（`prepare_data` -> `train_model`）中，`Dataset` artifact 如何从第一个组件传递到第二个组件？
   - A) 通过写入两个组件共享的全局变量
   - B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个组件声明的输出连接到第二个组件的类型化输入
   - C) 将其存储在环境变量中
   - D) 两个组件无法共享数据；必须合并为一个组件

<details>

<summary>显示答案</summary>

**答案：B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个组件声明的输出连接到第二个组件的类型化输入**

**解释：**
在由 `@dsl.pipeline` 装饰的函数中，`prep_task.outputs["output_dataset"]` 指向 `prepare_data` 声明的 `Output[Dataset]` 参数；将其传入 `train_model` 的 `input_dataset: Input[Dataset]` 参数，即可在两个独立运行的 Pod 之间连接 artifact 依赖关系。
</details>

8. KFP 如何决定是复用缓存结果，还是重新运行某个组件？
   - A) 无论输入是什么，始终重新运行每个组件
   - B) 对组件的输入（参数值、输入 artifact 名称/ID、容器镜像/命令、输出规格及相关配置）进行哈希，并在哈希值与先前成功执行的匹配时复用缓存输出
   - C) 仅当 pipeline 名称发生变化时才重新运行组件
   - D) 缓存仅取决于自上次运行以来经过的实际时间

<details>

<summary>显示答案</summary>

**答案：B) 对组件的输入（参数值、输入 artifact 名称/ID、容器镜像/命令、输出规格及相关配置）进行哈希，并在哈希值与先前成功执行的匹配时复用缓存输出**

**解释：**
2.16.1 的键会使用参数值、artifact ID 和容器/输出配置，而不会重新计算文件字节的哈希。修改文件字节或镜像标签可能不会改变键。查找范围限定在 pipeline 名称和命名空间内。

文件内容、可变镜像标签和外部状态不会自动使键失效。请将数据版本/哈希作为显式输入记录，或禁用缓存。
</details>

## 简答题

9. 写出本章介绍的两种禁用 KFP 缓存行为的方法。

<details>

<summary>显示答案</summary>

**答案：对单个组件，可在任务上调用 `set_caching_options(enable_caching=False)`；对单次运行，可在经过身份验证的客户端提交时设置 `enable_caching=False`。**

**解释：**
在 pipeline 函数中，对某个特定组件任务调用 `prep_task.set_caching_options(enable_caching=False)`，即可禁用该任务的缓存。另一种方式是在提交 Run 时禁用整个 pipeline 提交的缓存，而不是逐个组件禁用。
</details>

10. KFP SDK 的编译步骤实际会生成什么？该输出到达 KFP API server 后会发生什么？

<details>

<summary>显示答案</summary>

**答案：它会生成中间表示（IR）YAML，即与后端无关的 `PipelineSpec`。上传并创建 Run 后，此后端会将 IR YAML 转换为 Argo `Workflow`；Pod 创建由 Argo 管理，节点放置由 Kubernetes 管理。**

**解释：**
编译会生成 IR；该软件包还提供客户端 API 和 Python 运行时支持。创建 Run 会触发后端工作流处理。后端 IR 版本和平台扩展必须兼容。
</details>

## 实践题

11. 编写一个名为 `prepare_data` 的 `@dsl.component` 函数，声明单个 `Output[Dataset]` 参数，并将 pandas DataFrame 以 CSV 格式写入该参数。

<details>

<summary>显示答案</summary>

**答案：**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**解释：**
`output_dataset: Output[Dataset]` 声明了一个类型化 artifact 输出；运行时会将 `output_dataset.path` 准备为组件写入数据的存储位置，下游组件随后可以将其声明为 `Input[Dataset]`。
</details>

12. 编写一个 `@dsl.pipeline` 函数，将 `prepare_data` 的输出连接到 `train_model` 组件的 `input_dataset` 参数。

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

**解释：**
`prep_task.outputs["output_dataset"]` 引用 `prepare_data` 的 `Output[Dataset]` 参数（名为 `output_dataset`）所生成的 artifact；将其作为 `train_model` 的 `input_dataset` 参数传入，即可在两个组件之间创建 DAG 边。
</details>

13. 编写代码，为名为 `prep_task` 的单个 pipeline 任务禁用缓存。

<details>

<summary>显示答案</summary>

**答案：**
```python
prep_task.set_caching_options(enable_caching=False)
```

**解释：**
在 pipeline 函数中的任务对象上调用 `set_caching_options(enable_caching=False)`，即可在编译后的任务中禁用缓存。Run 提交时显式指定的 enable_caching 值可以覆盖此设置；将该选项留为 None 可保留编译时的设置。
</details>

---

[返回学习资料](../../../ai-ml/kubeflow/02-pipelines.md) | [下一个测验：Notebooks](./03-notebooks-quiz.md)
