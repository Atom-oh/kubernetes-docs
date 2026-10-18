# SageMaker Qwen 验证结果事实测验

## 选择题

1. 9 月 2 日的复查发现了什么？
   - A) 没有剩余资源
   - B) 仍有一个 Unified Studio 项目处于 `ACTIVE` 状态
   - C) 有一个正在运行的 EKS GPU 集群
   - D) 已完成一个 Training Job

<details>
<summary>显示答案</summary>

**答案：B**

历史记录报告称，App、S3 和 IAM 资源已回收，但仍剩余一个项目。9 月 12 日的文档审查没有重新查询 AWS 当前状态。
</details>

2. 第三次尝试的关键失败是什么？
   - A) 模型 ID 拼写错误
   - B) 缺少项目成员资格
   - C) 数据集哈希不匹配
   - D) CUDA 显存不足

<details>
<summary>显示答案</summary>

**答案：B**

未将调用方角色组配置文件分配为所有者/成员。
</details>

3. 哪些结果没有发布？
   - A) 记录数
   - B) MLflow App 版本
   - C) 微调后的 F1 和 GPU 成本
   - D) Python 测试数量

<details>
<summary>显示答案</summary>

**答案：C**

未执行 GPU 训练，因此没有测量这些对比数值。这并不意味着 MLflow App 和 S3 等资源的总成本为零。
</details>

4. 重新运行的第一道关卡是什么？
   - A) 提交完整 Job
   - B) 核对资源清单并处理剩余或状态未知的实验自有资源
   - C) 创建 EKS 集群
   - D) 发布微调后的指标

<details>
<summary>显示答案</summary>

**答案：B**

权限错误或列表中没有资源，都不能证明资源已删除。资源名称使用相同前缀，也不代表可以删除他人拥有的资源。
</details>

5. 目标架构与实际工作流有何不同？
   - A) 两者都能证明工作已完成
   - B) 一个是重新运行的设计，另一个记录了实际停止点
   - C) 两者都是成本报告
   - D) 实际工作流展示了已完成的 GPU 训练

<details>
<summary>显示答案</summary>

**答案：B**

历史工作流在 GPU 训练前停止。它不能证明账户当前状态，也不能证明实验总成本为零。
</details>

---

[返回学习材料](../../../ai-ml/sagemaker-ai/04-validation-results.md)
