# SageMaker AI 与 MLflow 执行测验

## 选择题

1. 新的托管式 MLflow 部署使用哪种资源？
   - A) 仅使用旧版 Tracking Server
   - B) SageMaker MLflow App
   - C) 公有 EKS LoadBalancer
   - D) 仅使用本地 SQLite 文件

<details>
<summary>显示答案</summary>

**答案：B**

托管路径使用当前 SageMaker MLflow App API。
</details>

2. 执行完整流程前必须满足什么条件？
   - A) 冒烟测试已完成，并且已扫描原始 PII 日志
   - B) 移除项目成员资格
   - C) 立即执行最大步数
   - D) 禁用资源拆除

<details>
<summary>显示答案</summary>

**答案：A**

首先检查冒烟测试是否完成、日志是否安全、聚合结果以及适配器清单。
</details>

3. EKS Job 的失败/截止时间契约是什么？
   - A) 不限次数重试且没有截止时间
   - B) `backoffLimit: 0` 和 `activeDeadlineSeconds: 10800`
   - C) 重试十次且运行一小时
   - D) 永久运行的 Deployment

<details>
<summary>显示答案</summary>

**答案：B**

这是重试和 Job 截止时间设置。控制器或节点故障可能延迟资源回收；这些设置不能保证所有资源在三小时内消失，也不能限制总成本。
</details>

4. 在什么情况下必须让清理验证失败？
   - A) 没有剩余资源
   - B) 仍有资源，或错误导致无法确认资源状态
   - C) 冒烟测试成功
   - D) 数据集哈希匹配

<details>
<summary>显示答案</summary>

**答案：B**

查询失败时，仅确认剩余资源为零并不足够。应保留未知状态；如果旧清单只有名称而缺少所有权证据，就拒绝删除。
</details>

5. 9 月 1 日实际执行了哪些操作？
   - A) 完整的 SageMaker Training Job
   - B) 完整的 EKS GPU Job
   - C) 资源配置与清理流程
   - D) 微调模型评估

<details>
<summary>显示答案</summary>

**答案：C**

两个 GPU Job 都在提交前停止。
</details>

6. 截至 2026 年 9 月 12 日，GPU 执行为何受阻？
   - A) 固定使用的 PyTorch 2.8 DLC 于 8 月 6 日结束补丁支持
   - B) 打包源代码会产生费用
   - C) 所有 MLflow App 都已删除
   - D) 本地单元测试需要 GPU

<details>
<summary>显示答案</summary>

**答案：A**

请验证受支持的 DLC、torch、依赖版本组合和 GPU 冒烟测试。仅移除日期检查并不算完成升级。
</details>

7. SageMaker 启动器在没有 `--execute` 时会做什么？
   - A) 立即提交完整 Job
   - B) 只写入请求 JSON
   - C) 删除现有 Job
   - D) 保证成本估算

<details>
<summary>显示答案</summary>

**答案：B**

默认只预览请求。实际提交需要通过运行时支持检查，并另行审查。
</details>

8. 保存 EKS MLflow 指标/参数 JSON 是否足够？
   - A) 足够，它会自动包含适配器权重
   - B) 下载最终适配器和聚合构件，然后验证哈希
   - C) `emptyDir` 会在集群删除后保留
   - D) 可以通过日志尾部还原模型

<details>
<summary>显示答案</summary>

**答案：B**

导出元数据不同于保留文件。如果导出失败后集群仍然保留，也需要关注成本并在之后进行清理。
</details>

---

[返回学习材料](../../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
