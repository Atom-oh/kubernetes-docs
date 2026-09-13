# Kubeflow Pipelines 测验

本测验用于检验您对 Kubeflow Pipelines 的架构、KFP v2 IR YAML 编译模型、核心概念（Pipeline、Component、Run、Experiment、Artifact、MLMD）、EKS Artifact 存储注意事项以及缓存行为的理解。

## 选择题

1. 此处使用的开源 KFP 2.16.1 后端中，哪个引擎负责管理工作流编排和 Pod 创建？
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 直接使用 Kubernetes CronJobs，不使用底层工作流引擎

<details>

<summary>显示答案</summary>

**答案：B) Argo Workflows**

**说明：**
此后端将 Run 的 IR 转换为 Argo Workflow 资源。Argo 管理顺序和 Pod 创建；Kubernetes 调度器将 Pods 安排到节点上。仅上传 pipeline 不会创建 Run。
</details>

2. KFP v1 SDK 编译器与 KFP v2 SDK 编译器的关键架构差异是什么？
   - A) v1 编译为 IR YAML；v2 直接编译为 Argo Workflow YAML
   - B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示形式（IR）YAML
   - C) 没有差异——两者生成完全相同的输出
   - D) v2 完全取消了编译需求

<details>

<summary>显示答案</summary>

**答案：B) v1 直接编译为 Argo Workflow YAML；v2 编译为与后端无关的中间表示形式（IR）YAML**

**说明：**
v1 SDK 的 `dsl-compile` 直接生成特定于 Argo 的 `Workflow` YAML manifest。v2 SDK 编译为与后端无关的 IR YAML（`PipelineSpec`），其中描述了 DAG、components 和类型化 artifacts；此后端会在创建 Run 时转换 IR，前提是后端版本和平台扩展兼容。
</details>

3. 哪个 Kubeflow Pipelines component 负责记录已注册的执行及其输入/输出 artifact 关系，从而支持在 KFP UI 中进行 lineage 追踪？
   - A) Argo Workflow Controller
   - B) ML Metadata (MLMD) store
   - C) MinIO artifact store
   - D) KFP SDK Compiler

<details>

<summary>显示答案</summary>

**答案：B) ML Metadata (MLMD) store**

**说明：**
MLMD 存储已注册的 execution/artifact 关系，而不是每个外部副作用或文件字节的完整性。请记录代码/数据修订版本和哈希值以实现可复现性。
</details>

4. 在 KFP v2 SDK 中，component 如何声明它会生成供下游 components 使用的 `Dataset` 类型 artifact？
   - A) 返回一个普通 Python dictionary
   - B) 声明一个类型为 `Output[Dataset]` 的参数
   - C) 写入硬编码的 `/tmp/dataset.csv` 路径，但不声明类型
   - D) 设置一个名为 `DATASET` 的环境变量

<details>

<summary>显示答案</summary>

**答案：B) 声明一个类型为 `Output[Dataset]` 的参数**

**说明：**
KFP v2 为 artifacts 提供了一等类型（`Dataset`、`Model`、`Metrics` 等）。类型为 `Output[Dataset]` 的 component 参数声明了类型和连接关系；运行时会准备路径，并将该 artifact 传递给声明了匹配 `Input[Dataset]` 参数的所有下游 component。
</details>

5. 在已审查的默认安装中，若要使用 S3 而不是 MinIO，需要什么？
   - A) 默认是 S3；该模式会切换为 MinIO
   - B) 为 S3 而不是内置的 MinIO 配置 pipeline root、provider 和 credential chain
   - C) 没有默认 artifact store——必须始终手动配置一个
   - D) 默认是 EFS；该模式会切换为 EBS

<details>

<summary>显示答案</summary>

**答案：B) 为 S3 而不是内置的 MinIO 配置 pipeline root、provider 和 credential chain**

**说明：**
默认 bundle 包含 MinIO，但其他安装和导入的 artifact URIs 可能不同。请使用当前的 KFP object-store 指南。S3 会产生存储、请求和传输费用；旧版 AWS distribution 指南不是经过验证的当前版本安装方案。
</details>

6. 当 KFP 的 artifact store 指向 S3 而非集群内 MinIO 时，对于实际执行 Run 的 ServiceAccount 和访问 artifact 的 components，哪种身份机制变得直接相关？
   - A) 无——S3 访问不需要任何 AWS 身份配置
   - B) IRSA 或 Pod Identity，并经过验证的 SDK、信任关系、运行时支持和范围受限的 S3 权限
   - C) 将硬编码的 AWS access key 嵌入每个 component 的 container image
   - D) 仅 Kubernetes RBAC 就足以访问 S3

<details>

<summary>显示答案</summary>

**答案：B) IRSA 或 Pod Identity，并经过验证的 SDK、信任关系、运行时支持和范围受限的 S3 权限**

**说明：**
当 artifact 读取/写入直接面向 AWS 而不是集群内的 MinIO endpoint 时，KFP pipeline Pods 运行所使用的 ServiceAccount 需要具有该 S3 bucket 权限的 IRSA role 或 EKS Pod Identity association。
</details>

7. 在示例双步骤 pipeline（`prepare_data` -> `train_model`）中，`Dataset` artifact 如何从第一个 component 传递给第二个？
   - A) 通过写入两个 components 共享的全局变量
   - B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个 component 声明的输出连接到第二个 component 的类型化输入
   - C) 通过将其存储在环境变量中
   - D) 两个 components 无法共享数据；必须合并为一个 component

<details>

<summary>显示答案</summary>

**答案：B) 通过 `train_model(input_dataset=prep_task.outputs["output_dataset"])`，将第一个 component 声明的输出连接到第二个 component 的类型化输入**

**说明：**
在使用 `@dsl.pipeline` 装饰的函数内，`prep_task.outputs["output_dataset"]` 指向 `prepare_data` 声明的 `Output[Dataset]` 参数，而将其传入 `train_model` 的 `input_dataset: Input[Dataset]` 参数，就是 SDK 在两个独立运行的 Pods 之间连接 artifact 依赖关系的方式。
</details>

8. KFP 如何决定复用缓存结果而不是重新运行 component？
   - A) 无论输入如何，它始终重新运行每个 component
   - B) 它对 component 的输入（参数值、输入 artifact 名称/IDs、container image/command、输出规格和相关配置）进行哈希，并在与之前成功 execution 的哈希匹配时复用缓存输出
   - C) 仅当 pipeline 名称变更时才重新运行 components
   - D) 缓存仅基于自上次运行以来的实际时间

<details>

<summary>显示答案</summary>

**答案：B) 它对 component 的输入（参数值、输入 artifact 名称/IDs、container image/command、输出规格和相关配置）进行哈希，并在与之前成功 execution 的哈希匹配时复用缓存输出**

**说明：**
2.16.1 的 key 使用参数值、artifact IDs 和 container/output 配置，而不是文件字节的新鲜哈希。修改字节或 image tag 可能会使 key 保持不变。查找范围限定在 pipeline 名称和 namespace 内。

文件内容、可变 image tags 和外部状态不会自动使 key 失效。请将数据版本/哈希作为显式输入记录，或者禁用缓存。
</details>

## 简答题

9. 请列出本章节介绍的两种禁用 KFP 缓存行为的方法。

<details>

<summary>显示答案</summary>

**答案：按 component，通过在 task 上使用 `set_caching_options(enable_caching=False)`；按 run，通过经身份验证的 client 提交时使用 `enable_caching=False`。**

**说明：**
`prep_task.set_caching_options(enable_caching=False)` 会在 pipeline 函数中禁用一个特定 component task 的缓存。或者，可以在 Run 提交时禁用整个 pipeline 提交的缓存，而不必逐个 component 禁用。
</details>

10. KFP SDK 的编译步骤实际生成什么，且该输出到达 KFP API server 后会发生什么？

<details>

<summary>显示答案</summary>

**答案：它生成中间表示形式（IR）YAML——与后端无关的 `PipelineSpec`。上传并创建 Run 后，此后端将 IR YAML 转换为 Argo `Workflow`，其 Pod 创建由 Argo 管理，节点放置由 Kubernetes 管理。**

**说明：**
编译会生成 IR；该 package 还提供 client APIs 和 Python runtime 支持。创建 Run 会触发后端工作流处理。后端 IR 版本和平台扩展必须兼容。
</details>

## 动手实践题

11. 编写一个名为 `prepare_data` 的 `@dsl.component` 函数，该函数声明一个 `Output[Dataset]` 参数，并将 pandas DataFrame 作为 CSV 写入其中。

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

**说明：**
`output_dataset: Output[Dataset]` 声明了类型化 artifact 输出；运行时会将 `output_dataset.path` 准备为 component 写入的存储位置，然后下游 components 可以将其声明为 `Input[Dataset]`。
</details>

12. 编写一个 `@dsl.pipeline` 函数，将 `prepare_data` 的输出连接到 `train_model` component 的 `input_dataset` 参数。

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
`prep_task.outputs["output_dataset"]` 引用由 `prepare_data` 的 `Output[Dataset]` 参数（名为 `output_dataset`）生成的 artifact，并将其作为 `train_model` 的 `input_dataset` 参数传递，从而在两个 components 之间创建 DAG edge。
</details>

13. 编写代码以禁用名为 `prep_task` 的单个 pipeline task 的缓存。

<details>

<summary>显示答案</summary>

**答案：**
```python
prep_task.set_caching_options(enable_caching=False)
```

**说明：**
在 pipeline 函数中对 task object 调用 `set_caching_options(enable_caching=False)`，会禁用该已编译 task 的缓存。Run 提交时的显式 enable_caching 值可以覆盖它；将该选项保留为 None 以保留已编译的设置。
</details>

---

[返回学习材料](../../../ai-ml/kubeflow/02-pipelines.md) | [下一测验：Notebooks](./03-notebooks-quiz.md)
