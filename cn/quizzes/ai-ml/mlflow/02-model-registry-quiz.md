# MLflow 模型注册表测验

本测验检验您对 MLflow 模型注册表的理解：注册模型、模型版本、别名，以及注册如何与 Tracking 关联。

## 选择题

1. MLflow 中的注册模型是什么？
   - A) 训练 Run 指标的快照
   - B) 模型版本的具名、带版本集合，使模型拥有独立于任何单次 Run 的稳定标识
   - C) 根据模型 artifact 构建的容器镜像
   - D) Tracking server 数据库的已保存副本

<details>

<summary>显示答案</summary>

**答案：B) 模型版本的具名、带版本集合，使模型拥有独立于任何单次 Run 的稳定标识**

**说明：**
注册模型由名称（例如 `fraud-detector`）标识，并在其生命周期内累积模型版本、别名、标签和描述。它的存在正是为了让“该模型”拥有超越任意一次训练 Run 或 Experiment 的标识。
</details>

2. 模型版本一旦创建，会发生什么？
   - A) 随着模型改进，可以直接编辑
   - B) 它是不可变的——新的训练结果会成为新版本，而不是对旧版本的编辑
   - C) 30 天后会自动删除
   - D) 它会与以相同名称注册的下一个版本合并

<details>

<summary>显示答案</summary>

**答案：B) 它是不可变的——新的训练结果会成为新版本，而不是对旧版本的编辑**

**说明：**
每个模型版本都有编号（版本 1、版本 2 等），并且一旦注册便不会更改。新的候选模型始终会在相同的注册模型名称下成为一个新版本。
</details>

3. 模型版本会保留什么来将其与 Tracking（第 1 部分）关联起来？
   - A) 存储在注册表内的训练数据集副本
   - B) 指向其来源的底层 `LoggedModel` 或 Run 的引用
   - C) 集群节点配置的快照
   - D) 不保留任何内容——模型版本完全独立于 Tracking

<details>

<summary>显示答案</summary>

**答案：B) 指向其来源的底层 `LoggedModel` 或 Run 的引用**

**说明：**
每个模型版本都会指向生成它的 Run（以及第 1 部分中介绍的 `LoggedModel` 实体），这正是实现血缘追踪和可复现性的基础。
</details>

4. MLflow 模型注册表中的别名是什么？
   - A) 在创建模型时分配的永久且不可更改的标签
   - B) 指向特定模型版本的可变具名指针，例如 `champion` 或 `challenger`
   - C) Tracking server URL 的简写
   - D) 注册模型名称的同义词

<details>

<summary>显示答案</summary>

**答案：B) 指向特定模型版本的可变具名指针，例如 `champion` 或 `challenger`**

**说明：**
与版本号不同，别名可以随时间移动以指向不同的模型版本——例如，在新版本通过评估后，将 `champion` 从版本 4 重新指向版本 7。
</details>

5. 为什么别名在当前 MLflow 中取代了较早的基于阶段的生命周期模型（Staging/Production/Archived）？
   - A) 所有版本的 MLflow 都不再支持阶段
   - B) 别名更灵活：一个版本可以拥有多个别名或没有别名，而且别名名称不受限于固定的一组生命周期标签
   - C) 别名比阶段占用更少磁盘空间
   - D) 无法通过 API 查询阶段

<details>

<summary>显示答案</summary>

**答案：B) 别名更灵活：一个版本可以拥有多个别名或没有别名，而且别名名称不受限于固定的一组生命周期标签**

**说明：**
阶段模型将每个版本绑定到固定的一组标签之一（`Staging`、`Production`、`Archived`）。别名与标签结合使用，可以实现更灵活的自定义命名，并让一个版本同时拥有多个别名。读者在较旧的 MLflow 部署中仍可能遇到阶段模型，但这是一种旧式方法。
</details>

6. 以下哪项会在记录模型的同时创建一个新的模型版本？
   - A) 在记录后调用 `mlflow.register_model(model_uri, name)`
   - B) 向特定 flavor 的 `log_model` 调用传递 `registered_model_name`
   - C) 手动将模型文件复制到 Tracking server 的 artifact store 中
   - D) 为现有模型版本设置标签

<details>

<summary>显示答案</summary>

**答案：B) 向特定 flavor 的 `log_model` 调用传递 `registered_model_name`**

**说明：**
向类似 `mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")` 的调用传递 `registered_model_name`，会在记录模型的同一调用中注册一个新的模型版本。`mlflow.register_model(model_uri, name)` 是替代路径，用于注册已在较早步骤中记录的模型。
</details>

7. 在典型的治理工作流中，什么会将 `champion` 别名移至新版本？
   - A) 训练脚本会在 Run 完成后立即自动执行此操作
   - B) 评估或审批流程——通常是 CI/CD pipeline 的一部分——仅在候选版本通过其关卡后执行
   - C) Serving system 首次解析 `models:/fraud-detector@champion` 时执行
   - D) MLflow 根据更高的版本号自动执行

<details>

<summary>显示答案</summary>

**答案：B) 评估或审批流程——通常是 CI/CD pipeline 的一部分——仅在候选版本通过其关卡后执行**

**说明：**
注册表的治理价值来自于将“生成候选项”与“提升候选项”分离。移动 `champion` 别名是一项有意执行的操作，通常在审批 pipeline 中自动化，并以通过评估标准为关卡。
</details>

8. 与 `models:/fraud-detector/7` 相比，Serving system 通过解析 `models:/fraud-detector@champion` 能获得什么？
   - A) 更快的推理延迟
   - B) 一个稳定引用，无需修改代码即可自动选取当前持有 `champion` 别名的任意版本
   - C) 访问不同 Tracking server 的权限
   - D) 自动模型重新训练

<details>

<summary>显示答案</summary>

**答案：B) 一个稳定引用，无需修改代码即可自动选取当前持有 `champion` 别名的任意版本**

**说明：**
基于别名的 URI 将模型使用方与任何特定版本号解耦。当 `champion` 被重新指向新验证的版本时，对该 URI 的下一次解析会直接选取新版本。
</details>

## 简答题

9. 说明模型版本与别名之间的区别，以及该区别为何对 Serving system 很重要。

<details>

<summary>显示答案</summary>

**答案：**
模型版本是不可变且有编号的——一旦创建便永远不会更改，新的训练结果始终成为新版本，而非对现有版本的编辑。别名是可变的：它是一个具名指针（如 `champion` 或 `challenger`），可以随时重新指向不同的模型版本。

这对 Serving system 很重要，因为它可以一次编写完成，以解析如 `models:/fraud-detector@champion` 这样的稳定名称，而非硬编码的版本号。当别名移动到新批准的版本时，Serving system 会在下一次解析时自动获取变更，无需更新代码或配置。
</details>

10. 描述模型版本的血缘如何支持如下审计问题：“哪一份确切的代码和数据生成了当前在生产环境中提供服务的模型？”

<details>

<summary>显示答案</summary>

**答案：**
每个模型版本都会保留指向生成它的 Run 的引用（以及第 1 部分介绍的底层 `LoggedModel`）。沿着这条链路——从 `champion` 别名到它所指向的模型版本，再从该版本回到其来源 Run——可以追溯到该 Run 在 Tracking 期间记录的参数、代码引用和数据集信息。

由于模型版本不可变且这条血缘链接永远不会丢失，审计人员始终可以将当前别名为 `champion` 的模型追溯到创建它的确切训练 Run，而不是依赖单独的记录或团队记忆。
</details>

---

[返回学习材料](../../../ai-ml/mlflow/02-model-registry.md) | [下一份测验：EKS Deployment](./03-eks-deployment-quiz.md)
