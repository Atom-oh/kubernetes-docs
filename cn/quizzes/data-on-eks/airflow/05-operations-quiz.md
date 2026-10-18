# 第 5 部分：运维与安全测验

检查 Airflow 3.3.1 的运维和恢复边界。

1. 在 Airflow 3 中分离 DAG processor，是否能消除所有 scheduler 数据库争用？

<details>
<summary>显示答案</summary>

**答案**：不能。Airflow 2 也支持高可用性；版本 3 仍需检查数据库锁、连接数和执行容量。

**解释：**`replicas=2` 并不会自动提供部署位置分散、数据库故障转移或完整的服务高可用性。

</details>

2. 停止 scheduler、processor 和 triggerer，是否能在迁移前暂停所有数据库写入？

<details>
<summary>显示答案</summary>

**答案**：不能。还需协调入口流量、排空流程，以及 worker/task、API server 和外部自动化程序发起的写入。

**解释**：应测试数据库恢复以及 Fernet/外部数据恢复；只使用一条迁移路径，并准备经过验证的回滚方案。

</details>

3. 是否所有 Airflow 组件都必须使用相同的 Secrets Manager 前缀？

<details>
<summary>显示答案</summary>

**答案**：不需要。针对 worker 的后端配置以及 Execution API 解析行为可能是有意如此设计的。

**解释**：应核实实际查询顺序、权限、回退和缓存行为。有些路径会记录异常；并非所有失败都会被静默处理。

</details>

4. `S3 remote_logging=True` 是否会立即上传每个组件的每一行日志？

<details>
<summary>显示答案</summary>

**答案**：不会。它用于配置任务日志；经审阅的 supervisor 会在任务执行结束后上传日志。

**解释**：服务的 stdout/stderr 可能需要单独采集。若上传前发生强制终止，最近的日志可能会丢失。

</details>

5. 在配置 Fernet 的 metastore 中，Connection/Variable 值是否全是明文？

<details>
<summary>显示答案</summary>

**答案**：不是。密码/extra 字段和 Variable 值会加密，但并非所有元数据或日志都会加密。

**解释**：应保留并轮换 Fernet 密钥。外部后端也是可选方案；AWS Secrets Manager 并非生产环境唯一必选方案。

</details>

6. 对 Celery KEDA 查询而言，统计所有 queued/running 任务是否足够？

<details>
<summary>显示答案</summary>

**答案**：还应考虑队列、executor、别名、worker 并发度和副本数量限制。

**解释**：Worker 可以使用 Deployment 或 StatefulSet；是否能缩容到零取决于实际配置。

</details>

7. 为什么不能把 Celery worker-pool 扩缩容配置原样用于 KubernetesExecutor？

<details>
<summary>显示答案</summary>

**答案**：KubernetesExecutor 会直接创建任务 Pod，并不存在等效的固定 worker pool。

**解释**：这并不表示 KEDA 只支持 Deployment。还应单独检查节点自动扩缩容容量、配额和中断约束。

</details>

8. 为共享的 Celery worker 指定 IAM role，是否会自动隔离每个任务的 AWS 权限？

<details>
<summary>显示答案</summary>

**答案**：不会。该 worker 上的多个任务可能共享其执行权限。

**解释**：有隔离要求时，应使用实际边界，例如单独的 pool、executor 或 KPO 子任务，并检查凭证来源。

</details>

9. `db clean` 自动化应如何预览变更并发现失败？

<details>
<summary>显示答案</summary>

**答案**：先使用 `--dry-run`，并审查截止时间和表；同时使用 `--error-on-cleanup-failure` 并检查日志。

**解释**：删除操作应单独执行。默认归档会占用数据库空间，级联操作也需考虑；清理并不总能释放磁盘或加快所有迁移。

</details>

10. 仅配置 NetworkPolicy 和 OTLP endpoint，是否就完成了安全与可观测性工作？

<details>
<summary>显示答案</summary>

**答案**：不能。应核实 CNI 策略执行、实际允许的路径、身份验证、Collector 的接收器/导出器、存储和告警。

**解释**：NetworkPolicy 不能替代 IAM/RBAC/TLS。Prometheus 也不会直接抓取 OTLP/HTTP endpoint。

</details>

---

[返回学习资料](../../../data-on-eks/airflow/05-operations.md) | [Airflow](../../../data-on-eks/airflow/README.md)
