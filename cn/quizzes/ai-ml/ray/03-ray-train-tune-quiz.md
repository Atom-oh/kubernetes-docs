# Ray Train / Tune 测验

## 多项选择题

1. Ray Train 不会自动编写什么？
   - A) 底层 worker 协调
   - B) 框架的进程组设置
   - C) 所有模型/数据分区/状态保存与恢复逻辑
   - D) Ray 资源请求

<details>
<summary>显示答案</summary>

**答案：C**

准备模型/data-loader 集成，以及实际的模型、optimizer 和 checkpoint 逻辑。
</details>

2. 2.58.0 中经过审查的 Train V2 默认行为是什么？
   - A) 未设置环境变量时使用 V2
   - B) 只能运行 V1
   - C) 已移除 TorchTrainer import
   - D) Ray extras 会自动安装 PyTorch

<details>
<summary>显示答案</summary>

**答案：A**

明确区分显式选择旧版实现的运行。框架是独立依赖项。
</details>

3. 在 V2 中设置旧版 trainer_resources 时会发生什么？
   - A) 它始终为控制器预留更多 CPU
   - B) 会引发弃用错误
   - C) GPU 数量增加
   - D) Tune trial 数量改变

<details>
<summary>显示答案</summary>

**答案：B**

控制器、训练 worker 和 Tune driver 各自的资源范围不同。
</details>

4. Checkpoint.from_directory 的作用是什么？
   - A) 自动捕获每个模型/optimizer/RNG 状态
   - B) 引用用户准备的 checkpoint 目录中的文件
   - C) 部署模型
   - D) 对数据集进行匿名化

<details>
<summary>显示答案</summary>

**答案：B**

准备恢复所需的状态数据，并加载由 get_checkpoint 返回的 checkpoint。
</details>

5. 2.58.0 V2 的 report 参与规则是什么？
   - A) 仅 rank 0 调用它
   - B) 每个 worker 以相同次数到达 barrier
   - C) 每项 metric 都会自动取平均值
   - D) 没有 checkpoint 时不能调用它

<details>
<summary>显示答案</summary>

**答案：B**

即使仅 rank 0 保存文件，其他 worker 也会报告 checkpoint=None。
</details>

6. max_failures=0 会禁用所有重试吗？
   - A) 会
   - B) 不会；控制器重试和抢占重试有各自独立的设置
   - C) 它始终表示无限重试
   - D) 它只禁用 Karpenter 重试

<details>
<summary>显示答案</summary>

**答案：B**

经过审查的 controller_failure_limit 和 max_preemption_failures 默认值均为 -1。
</details>

7. 当前的 V2 Train/Tune 集成模式是什么？
   - A) 将 V2 Trainer 实例直接传递给 Tuner
   - B) 在 function trainable 中构造并 fit 一个 Trainer；按需连接 callbacks
   - C) 这些库无法组合使用
   - D) 始终需要单独的 Kubernetes 集群

<details>
<summary>显示答案</summary>

**答案：B**

在原生检查中，直接输入 V2 Trainer 会引发 TuneError。集成需要连接配置和资源规划。
</details>

8. TuneReportCallback 会转发什么？
   - A) 自动取平均值的 worker metric
   - B) 第二次 checkpoint 上传
   - C) 第一个 worker 的 metric dictionary 和现有 checkpoint path
   - D) 它始终可以在 Tune session 外部运行

<details>
<summary>显示答案</summary>

**答案：C**

在 Tune session 中构造它。单独执行 metric 聚合。
</details>

## 简答题

9. 为什么要统筹规划 trial driver 和 Train worker 的资源？

<details>
<summary>显示答案</summary>

Driver 可能占用其嵌套 worker 或 placement group 所需的资源。请一并检查并发度、worker 资源包、集群资源上下限，以及单个节点的资源是否满足要求。
</details>

10. 成功的标量 Tune 示例不能证明什么？

<details>
<summary>显示答案</summary>

它不能证明模型准确性、PyTorch/DDP 或 GPU 性能、多节点 checkpoint 恢复，或 EKS autoscaling。它检查 API 以及两个标量 trial 结果的收集。
</details>

---

[返回学习资料](../../../ai-ml/ray/03-ray-train-tune.md)
