# MLflow Model Registry 测验

## 选择题

1. 什么是 Registered Model？
   - A) 一个 GPU endpoint
   - B) 在逻辑名称下的 Model Versions 集合
   - C) 一份训练数据副本
   - D) 仅允许一次 Run 的记录

<details>
<summary>显示答案</summary>

**答案：B**

例如，fraud-detector 将版本和 aliases 归在同一个名称下。
</details>

2. 哪项关于 Model Version 变更的说法是准确的？
   - A) 每个字段和源字节都永久不可变
   - B) 它会获得一个版本号；描述和标签可以更改，artifact 保留是独立的
   - C) 每个版本都会在 30 天后过期
   - D) 每个新模型都会合并到前一个版本中

<details>
<summary>显示答案</summary>

**答案：B**

应将对新结果进行版本控制的做法与存储层面的不可变性区分开来。
</details>

3. 每个 Model Version 都有训练 Run 链接吗？
   - A) 始终有，而且该链接无法删除
   - B) model_id 会自动保留数据集快照
   - C) 不会；create_model_version 的 run_id/model_id 字段是可选的
   - D) registry 从不支持来源链接

<details>
<summary>显示答案</summary>

**答案：C**

允许使用直接的源 URI。完整的 lineage 需要显式记录和保留。
</details>

4. 什么是 alias？
   - A) 跨多个版本的内置流量百分比
   - B) 指向一个版本的可变名称
   - C) 固定的数据库地址
   - D) 不可更改的内容哈希

<details>
<summary>显示答案</summary>

**答案：B**

多个 aliases 可以引用一个版本，而且 alias 可以移动到另一个版本。
</details>

5. legacy stage API 的状态是什么？
   - A) 自 2.9.0 起已弃用，但在 3.16.0 中仍然存在
   - B) 已从所有 MLflow 版本中移除
   - C) 是与 aliases 等价的访问控制策略
   - D) 仅支持 Production

<details>
<summary>显示答案</summary>

**答案：A**

Legacy stages 包括 None/Staging/Production/Archived。请使用 aliases/tags 和显式权限来设计新流程。
</details>

6. 在记录模型时如何进行注册？
   - A) 仅设置一个 tag
   - B) 将 registered_model_name 传递给 flavor log_model
   - C) 删除一个 alias
   - D) 将文件重命名为 champion

<details>
<summary>显示答案</summary>

**答案：B**

在记录后使用 register_model 进行注册是另一种方式。注册本身不会移动 alias。
</details>

7. 什么控制 champion 晋升？
   - A) MLflow 自动批准最大的版本
   - B) 仅凭 review_state tag 即可完成权限分离
   - C) 评估/批准证据，以及执行者的身份验证/授权
   - D) 每个训练者都会更改 alias

<details>
<summary>显示答案</summary>

**答案：C**

一个 tag 字符串无法取代批准工作流或访问控制。
</details>

8. alias 更改后，已加载的模型会立即发生什么？
   - A) 它始终会立即被替换
   - B) 它会自动重新训练
   - C) 会自动出现影子流量
   - D) 在 reload/deployment/cache 策略改变它之前，它可能会继续提供服务

<details>
<summary>显示答案</summary>

**答案：D**

新的解析结果与现有已加载实例的生命周期是相互独立的。
</details>

## 简答题

9. 仅凭 READY 能证明推理兼容性和模型质量吗？

<details>
<summary>显示答案</summary>

不能。它是注册状态；metadata fixtures 可以是 READY。请分别验证实际 flavors、weights、依赖项加载和质量。
</details>

10. 为什么 registry 不一定总能重建精确的代码和数据 lineage？

<details>
<summary>显示答案</summary>

Run/model 链接是可选的，并且源文件、Runs 或 artifacts 可能发生变化或消失。请保留 serving version、哈希、commit、数据集快照、依赖项和批准信息。
</details>

---

[返回学习资料](../../../ai-ml/mlflow/02-model-registry.md)
