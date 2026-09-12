# MLflow Tracking 测验

## 多项选择题

1. Experiments 和 Runs 之间有什么关系？
   - A) 一个 Experiment 对 Runs 进行分组；一个 Run 可以表示训练或评估
   - B) 一个 Experiment 就是一个 GPU
   - C) 一个 Run 始终是已部署的模型
   - D) 它们是同一个实体

<details>
<summary>显示答案</summary>

**答案：A**

Runs 还可以记录预处理和比较工作。
</details>

2. 在新的 MLflow 3.16.0 环境中，默认的元数据后端是什么？
   - A) 一个 S3 bucket
   - B) sqlite:///mlflow.db
   - C) 浏览器 localStorage
   - D) 必需使用 PostgreSQL

<details>
<summary>显示答案</summary>

**答案：B**

SQLite 是默认设置；如果 ./mlruns 已存在，请检查兼容性行为。显式 URI 可消除歧义。
</details>

3. MLflow 3 中 LoggedModel 的重要变更是什么？
   - A) 独立的 model_id、状态和关系跟踪
   - B) 首次可以在没有 start_run 块的情况下调用 log_model
   - C) 不再需要 artifacts
   - D) 注册后立即部署到 GPU

<details>
<summary>显示答案</summary>

**答案：A**

2.22.0 中的 Model.log 已会在需要时隐式启动一个 Run。独立的模型身份不同于省略显式 Run 上下文。
</details>

4. 哪项 autologging 说法是正确的？
   - A) 它会捕获任意代码中的所有内容
   - B) 它始终会移除 PII
   - C) 审查每个集成所支持的版本以及收集的输入/输出
   - D) 它会自动完成部署

<details>
<summary>显示答案</summary>

**答案：C**

行为取决于框架和选项。请检查输入示例、原始数据以及模型 artifact 收集。
</details>

5. 哪项有关 tracing 和成本的说法是准确的？
   - A) Tracing 首次出现于 3.x
   - B) 每个工具 span 都有 LLM 成本
   - C) 基于 token 推导的成本始终等于账单
   - D) Tracing 在 2.14.0 中推出；使用情况收集取决于集成

<details>
<summary>显示答案</summary>

**答案：D**

请区分后续扩展与最初引入。没有模型、使用情况和定价信息，无法保证成本准确。
</details>

6. 即使使用远程 tracking server，客户端何时仍可能需要 S3 权限？
   - A) 使用直接 S3 artifact URI 的非代理模式
   - B) 仅在读取 SQLite 参数时
   - C) 无论模式如何，它都永远不需要权限
   - D) 每次别名名称查找都需要 S3 访问权限

<details>
<summary>显示答案</summary>

**答案：A**

元数据路径与 artifact 路径不同。直接模式要求客户端具备存储权限和网络访问能力。
</details>

7. 如何检查在步骤 0 和 1 记录的 metric？
   - A) 参数会自动更改
   - B) 只有第二个值会被永久保留
   - C) 使用 get_metric_history 检查两次观测
   - D) 会自动注册两个模型

<details>
<summary>显示答案</summary>

**答案：C**

请区分当前摘要与带时间戳和步骤的 metric 历史记录。
</details>

8. 合适的 Tracking web UI 查询路径是什么？
   - A) 浏览器直接连接到 PostgreSQL
   - B) 浏览器调用 server HTTP API
   - C) UI 始终直接从训练 Pods 读取文件
   - D) 浏览器需要数据库管理员密码

<details>
<summary>显示答案</summary>

**答案：B**

server 访问其后端。artifact 代理配置是另一个需要考虑的问题。
</details>

## 简答题

9. PENDING 的 initialize_logged_model 结果能否立即执行推理？

<details>
<summary>显示答案</summary>

不能。它可能仅包含元数据；仍需要实际的 flavor、权重、artifact 记录和最终确定。READY 不代表质量或部署已获批准。
</details>

10. 为什么在 server artifact flags 更改后，现有 experiment 仍可能直接访问 S3？

<details>
<summary>显示答案</summary>

已记录的 experiment/Run artifact URI 不会被追溯性重写。请检查该 URI 以及实际的权限和传输路径。
</details>

---

[返回学习材料](../../../ai-ml/mlflow/01-tracking.md)
