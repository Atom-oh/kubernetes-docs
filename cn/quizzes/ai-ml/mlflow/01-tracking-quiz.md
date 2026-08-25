# MLflow Tracking 测验

本测验用于测试你对 MLflow Tracking 核心概念、MLflow 3 向一等 LoggedModel 的转变、autologging、GenAI tracing，以及 backend/artifact store 分离的理解。

## 多项选择题

1. 什么是 MLflow Experiment？
   - A) 一次训练代码的单独执行，具有自己的 params 和 metrics
   - B) 一个具有名称的 Run 集合
   - C) 存储 MLflow metadata 的数据库
   - D) 一个序列化的 model 文件

<details>

<summary>显示答案</summary>

**答案：B) 一个具有名称的 Run 集合**

**解释：**
Experiment 是 Run 的命名分组，通常每个 project 或正在迭代的每个 model 对应一个。Run 是训练代码的一次单独执行，具有自己的 params、metrics、tags 和 artifacts——这是不同的概念（选项 A）。
</details>

2. 在 MLflow 1.x/2.x 以 Run 为中心的模型中，记录的 model 通常如何表示？
   - A) 作为独立于任何 Run 的 `LoggedModel` entity
   - B) 作为嵌套在生成它的 Run 下的 artifact
   - C) 作为 backend store metrics table 中的一行
   - D) 作为独立的 experiment

<details>

<summary>显示答案</summary>

**答案：B) 作为嵌套在生成它的 Run 下的 artifact**

**解释：**
在 MLflow 3 之前，记录的 model 只是存储在 run 的 artifact directory 中的另一个 artifact。要查找 model，你必须先找到生成它的 run。MLflow 3 通过引入 `LoggedModel` 作为其自身的一等 entity 改变了这一点。
</details>

3. MLflow 3 的 `LoggedModel` entity 实现了哪项早期嵌套在 Run 中的 model 不具备的关键能力？
   - A) 无需活动的 `mlflow.start_run()` context，直接调用 `mlflow.sklearn.log_model(...)`
   - B) 无需 tracking server 即可记录 metrics
   - C) 无需 Python 即可运行训练代码
   - D) 无需 artifact store 即可存储 artifacts

<details>

<summary>显示答案</summary>

**答案：A) 无需活动的 `mlflow.start_run()` context，直接调用 `mlflow.sklearn.log_model(...)`**

**解释：**
由于 `LoggedModel` 现在是独立于 Run 的一等 entity，因此不再需要嵌套在活动 run 下才能被跟踪。这使 model versioning 和比较不再依赖于任何单一训练 run。
</details>

4. `mlflow.autolog()` 的作用是什么？
   - A) 自动将训练完成的 model 部署到 serving endpoint
   - B) 为受支持的 ML libraries 添加 instrumentation，从而在训练期间自动记录 params、metrics 和 artifacts，无需手动 logging calls
   - C) 自动删除旧 run 以节省 storage
   - D) 将 Run 转换为 LoggedModel

<details>

<summary>显示答案</summary>

**答案：B) 为受支持的 ML libraries 添加 instrumentation，从而在训练期间自动记录 params、metrics 和 artifacts，无需手动 logging calls**

**解释：**
Autologging 会自动捕获受支持 framework 的常见训练数据。MLflow 还提供 framework-specific autolog functions（例如适用于 scikit-learn 或 PyTorch），用于仅为一个 library 而不是每个检测到的 framework 启用 autologging。
</details>

5. 在 MLflow 3 中，“tracing”主要用于什么？
   - A) 记录经典 scikit-learn 训练 run 的 parameters 和 metrics
   - B) 捕获 LLM/agent calls 的内部步骤（spans）、token usage 和 cost，以实现 GenAI observability
   - C) 跟踪 artifact store 的 disk usage
   - D) 完全替代 Experiments/Runs 视图

<details>

<summary>显示答案</summary>

**答案：B) 捕获 LLM/agent calls 的内部步骤（spans）、token usage 和 cost，以实现 GenAI observability**

**解释：**
Tracing 将 LLM 或 agent call 捕获为一个 spans tree，其中每个 span 表示一个步骤，例如 retrieval call 或 tool invocation，并包含 token usage 和 cost。它将 MLflow Tracking 扩展为涵盖 GenAI/agent observability 的核心功能，而无需单独的工具。
</details>

6. 除 LangChain 之外，下列哪项是 MLflow 提供 auto-tracing integration 的 framework 示例？
   - A) Kubernetes
   - B) PostgreSQL
   - C) PydanticAI
   - D) Terraform

<details>

<summary>显示答案</summary>

**答案：C) PydanticAI**

**解释：**
MLflow 为包括 LangChain 在内的常用 LLM/agent frameworks 提供 auto-instrumentation，并为 PydanticAI 和 smolagents 等 frameworks 提供较新的 auto-tracing integrations。
</details>

7. 为什么 backend store 在团队规模下通常需要真正的 relational database（例如 PostgreSQL 或 MySQL）？
   - A) 因为它存储大型二进制 model 文件，而 database 比 object storage 更擅长处理这些文件
   - B) 因为它保存结构化 metadata——params、metrics、tags 以及 run/experiment/model records——这些数据受益于超出快速本地实验范围的 database
   - C) 因为 MLflow 需要 SQL database 来渲染其 UI
   - D) 因为 object storage 完全无法存储任何 metadata

<details>

<summary>显示答案</summary>

**答案：B) 因为它保存结构化 metadata——params、metrics、tags 以及 run/experiment/model records——这些数据受益于超出快速本地实验范围的 database**

**解释：**
backend store 保存的结构化 metadata 适合 relational database 的大量小型结构化写入和查询。相比之下，artifact store 保存大型二进制 objects，通常是 S3-compatible bucket 等 object storage。
</details>

8. 在 tracking flow（training script -> Tracking API -> tracking server -> backend store + artifact store）中，Tracking UI 的作用是什么？
   - A) 直接写入 training script 的 local disk
   - B) 从 backend store 和 artifact store 中读取，以渲染 experiments、runs、logged models 和 traces
   - C) 绕过 tracking server，仅查询 backend store
   - D) 仅显示 artifacts，从不显示 metadata

<details>

<summary>显示答案</summary>

**答案：B) 从 backend store 和 artifact store 中读取，以渲染 experiments、runs、logged models 和 traces**

**解释：**
training script 仅与 Tracking API 通信；tracking server 将 metadata writes 路由到 backend store，并将 file writes 路由到 artifact store。UI 从这两个 store 中读取，以显示所需的全部内容。
</details>

## 简答题

9. MLflow 3 跟踪 `LoggedModel` 与其关联的 runs、traces、prompts 和 evaluation metrics 之间的 lineage，具有怎样的实际优势？

<details>

<summary>显示答案</summary>

**答案：model 不再永久绑定到训练它的单个 run——它可以关联到训练它的 run、评估它的 runs，以及由 serving 它所生成的任何 traces。**

**解释：**
由于 `LoggedModel` 是一等 entity，而不是嵌套在一个 run 下的 file，MLflow 3 可以表示 model 与其关联的一切之间更丰富的 relationships。当一个 model 在多个 runs 中反复迭代，或在传统 training loop 之外生成时，这一点尤为重要，例如使用 custom logic 封装现有 LLM。
</details>

10. 为什么 MLflow 将经典 ML experiment tracking 和 GenAI/agent observability 视为一个系统，而不是两个独立的工具？

<details>

<summary>显示答案</summary>

**答案：因为 MLflow 3 将同一个 Tracking system（及其 UI）扩展为同时涵盖二者——用于 GenAI/agent calls 的 tracing 使用与经典 training runs 的 params/metrics/artifacts 相同的 tracking server、UI 和 lineage model。**

**解释：**
同时进行经典 ML training 和 LLM/agent development 的团队可以使用一个 MLflow Tracking deployment 来处理二者，而无需仅为 GenAI 方面部署单独的 observability tool。
</details>

---

[返回学习材料](../../../ai-ml/mlflow/01-tracking.md) | [下一个测验：Model Registry](./02-model-registry-quiz.md)
