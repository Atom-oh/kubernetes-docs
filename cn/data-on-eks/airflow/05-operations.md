# 第 5 部分：运维与安全

> 已核对版本：Airflow 3.3.1、Helm chart 1.22.0、Amazon provider 9.34.0 / Kubernetes provider 10.21.0。
> 已检查的上游最新补丁版本：3.3.2；运维示例仍基于 3.3.1 · 2026 年 10 月 12 日。

本章介绍第 2 部分自管理 EKS 部署的高可用、升级、Secret、日志、可观测性和恢复。运维的判断标准是：**发生故障后，执行状态、数据和日志都可以恢复**，而不只是配置项已经存在。对于 MWAA，请使用第 4 部分中适用于托管环境 / CloudWatch 的流程。

## 1. 将调度器高可用与数据库一并验证

Airflow 2 已支持调度器高可用和独立 DAG 处理器。
Airflow 3 强制拆分处理器，从而明确了资源与职责边界，但这并不能消除数据库争用，也不能保证线性扩展。调度器使用序列化 DAG 和数据库行锁来协调调度关键区。无需单独的调度器领导者选举服务。

```yaml
scheduler:
  replicas: 2
```

此设置只会更改副本数量。还应验证节点 / AZ 放置、数据库故障转移和连接数限制、API / 处理器可用性、探针 / PDB 以及执行器 / broker 健康状态。在节点 / AZ 故障和数据库故障转移期间，测量调度延迟、重试和外部写入重复情况。调度器页面上关于 SQL 功能的说明并非完整的受支持数据库矩阵；请遵循第 1 部分的版本指导。使用 triggers（包括可延迟任务）时需要 Triggerer。

## 2. 备份、恢复和迁移

元数据数据库存储执行状态和许多 Airflow 设置。外部 Secret 和对象存储 XCom 后端意味着并非所有值都在数据库中。除了数据库，还应保留 Fernet 密钥、DAG / bundle 历史、镜像 / provider、外部数据、日志和 Secret。没有解密密钥，仅恢复加密行是不够的。

应在特定于环境的迁移运行手册中验证以下顺序：

1. 检查受支持的升级路径和破坏性变更。使用真实程度足够的数据库副本进行演练，以测量耗时、锁定、磁盘空间和 DAG / provider 兼容性。
2. 使用数据库的一致性保证执行热备份，并测试恢复。快照请求成功并不能证明备份已经完成或能够恢复。
3. 控制新任务执行，并排空或有意终止现有任务。协调所有相关的数据库写入方，包括 worker / task、API Server 和外部自动化。仅停止调度器、处理器和 Triggerer 并不能停止所有写入。
4. 确定备份 / 恢复点，并只使用一种迁移机制。不要让 Helm 迁移 Job / hook 与手动运行的 airflow db migrate 命令相互竞争。
5. 在重新开放流量前，验证数据库状态、新任务执行、重试、日志和 Secret 查找。迁移 schema 后重新部署旧镜像并不足以构成回滚计划。

### 应用明确的历史保留策略

不要在每次升级前无条件删除固定天数之前的记录。请先检查审计 / 重放 / depends_on_past 需求和外键级联。以下命令只用于**预览，不会删除数据**：

```bash
# Preview only: replace the cutoff and table selection with your retention policy.
airflow db clean \
  --clean-before-timestamp '2026-07-01T00:00:00+00:00' \
  --tables dag_run,task_instance \
  --dry-run \
  --error-on-cleanup-failure
```

只有在检查截止时间 / 表并完成备份之后，才单独执行清理。默认归档表仍占用同一个数据库的空间，因此清理不能保证立即释放磁盘，也不能保证每次迁移都会更快。在 3.3.1 中，某些清理失败可能被零退出状态掩盖；自动化应使用 --error-on-cleanup-failure 并检查结果 / 日志。

## 3. Fernet 和 Secret 解析路径

Connection 和 Variable 并非默认全部以明文存储。配置 Fernet 后，Connection 的 password / extra 字段以及 Variable 值会加密。这不会加密每个元数据字段或所有日志；请妥善保留 / 轮换密钥并控制访问权限。AWS Secrets Manager 是受支持的外部后端选项之一。

```ini
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

通用的服务端查找顺序为：自定义后端 → 环境变量 → metastore。Airflow UI 不会列出所有外部值。在 UI 中编辑重复的键，较高优先级的外部值仍可能继续生效。

Airflow 3 支持 worker 专用的 [workers] secrets_backend 和 secrets_backend_kwargs。普通 Task SDK 任务上下文也可以通过 supervisor 和 Execution API 解析服务端值。因此，各组件不需要完全相同的前缀，也不一定需要直接访问数据库。

请记录预期的解析路径，并分别测试 API 侧查找、worker 覆盖行为，以及日志 supervisor 的解析 / 缓存。已审查的代码会先记录后端异常，再尝试后续路径；并非所有失败都是静默的。应测试意外的回退值和显式查找失败。不要将 Secret 内容打印到诊断日志中。

## 4. S3 任务日志不会即时流式传输每个组件的所有日志

```ini
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
delete_local_logs = False
```

Secret 示例名称：airflow/connections/airflow_remote_logging_conn。示例值：

```json
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

此 Connection 不包含静态密钥。请为实际 S3 读取 / 写入方配置 IRSA 或 Pod Identity 以及 SDK 凭证选择逻辑，并配置 bucket 前缀 / KMS 权限和网络。通过 API 接收 Connection 元数据，并不会转移 API Server 的 AWS 凭证。请同时测试 API / UI 读取和 task / supervisor 写入。

经审查的 3.3.1 supervisor 会在 task 子进程结束后上传远程日志。Amazon S3 handler 也会通过 close / upload 路径存储文件。不能保证每一行都立即写入 S3。请测试成功和失败的 task、worker 被强制终止的情况，以及 Pod 删除后的 UI 日志检索。如果 SIGKILL 或节点故障发生在最终上传之前，最近的日志可能会丢失。

S3 remote_logging 配置的是**Airflow 任务日志路径**。它不会自动把所有 scheduler / API / processor 服务日志发送到同一个 S3 位置。单独收集 stdout / stderr（例如使用 Fluent Bit）可以补充该功能。如果 task 只写文件，收集容器 stdout 并不会自动收集这些文件。PVC 或独立采集器可能在 Pod 删除后继续保留日志；请检查实际存储、保留规则和数据丢失边界。

对于 KPO，调用方的 get_logs 行为会将子进程输出带入 Airflow task 日志。在不含 Airflow 的任意子镜像中复制 airflow.cfg，并不会因此启用远程日志。

## 5. 指标传输和采集

使用带有匹配 OTel 依赖项的镜像，并选择指标后端。以下配置会选择 OTel：

```ini
[metrics]
statsd_on = False
otel_on = True
```

为每个发出指标的进程设置示例环境变量：

```dotenv
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector.monitoring.svc:4318/v1/metrics
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf
OTEL_METRIC_EXPORT_INTERVAL=30000
OTEL_SERVICE_NAME=airflow
```

在 3.3.1 中，旧的 otel_host、otel_port 和 otel_interval_milliseconds 设置已弃用，应改用标准 OTel 环境变量。此端点是内部 OTLP / HTTP 示例。请确保与 Collector HTTP receiver、Service 端口、网络策略以及所需的 TLS / 身份验证匹配。

Prometheus 不会直接抓取 OTLP 端点。请配置完整的指标流水线，例如抓取 Collector Prometheus exporter，或使用带身份验证且适用的 remote-write exporter。对于 AMP，请验证 workspace 端点和 AWS 身份验证。对于 StatsD，还要检查 exporter 映射和实际指标序列。

监测调度器心跳 / 调度延迟、解析错误 / 耗时、排队任务时长、worker / Triggerer 健康状态、数据库连接 / 锁、Pending / OOM / 磁盘压力状况以及日志上传失败情况。建立告警前，应检查导出的指标名称 / 标签，并通过受控故障测试通知是否送达。

## 6. 自动扩缩与安全边界

Celery KEDA 查询必须区分队列、执行器和别名，并按照第 2 部分考虑并发度和副本限制。根据持久化要求，worker 可以使用 Deployment 或 StatefulSet。缩容到零取决于最小副本数、触发器和冷却时间；这不会消除所有服务空闲成本。

KubernetesExecutor 会直接创建 task Pod，因此不需要相同的 Celery worker 池扩缩模式。这不意味着 KEDA 只支持 Deployment。task 结束后，节点自动扩缩器也不会立即移除每个节点。还需考虑容量、配额、PDB、中断策略和其他工作负载。

| 边界 | 验证内容 |
| --- | --- |
| AWS 身份 | 同一共享 Celery worker 上运行的 task 共用该 worker 的角色。应使用实际执行隔离边界，例如独立的 pool / executor / KPO 子 Pod |
| Kubernetes RBAC | 仅向需要权限的 KubernetesExecutor 或 KPO 调用方授权。仅解析 DAG 并不需要创建 Pod 的权限 |
| Namespace / 准入控制 | 创建 Pod 的权限可能允许选择其他 ServiceAccount 或危险配置；应检查信任边界和准入控制 |
| NetworkPolicy | 验证 CNI 执行情况，以及 DNS、Execution API、DB / broker、Kubernetes API、凭证 / Secret / 日志端点 |

NetworkPolicy 会限制 L3 / L4 连通性。它不能替代 IAM / RBAC / TLS 身份验证，也不能保证阻止所有横向移动。应用默认拒绝策略前，应放行实际依赖，但不要因此扩大 task 对数据库的不必要访问。

## 7. 运维验收

- [ ] 记录受支持的运行时 / provider、执行器选择以及 DAG 分发 / 重跑版本策略。
- [ ] 针对合适的生产数据库测试备份 / 恢复以及 Fernet / 外部数据恢复。RDS 是一种选择，但不是唯一选择。
- [ ] 测试调度器 / API / 处理器及必需 Triggerer 的故障 / 恢复行为和容量限制。
- [ ] 使用真实程度足够的数据库副本演练迁移、新任务接纳、排空和回滚。
- [ ] 验证预期的 Secret 解析，以及 IAM / RBAC / 准入 / 网络边界。
- [ ] 在任务成功、失败、强制终止和 Pod 删除后检查日志，并记录日志丢失限制。
- [ ] 将指标、服务 / task 日志和告警关联到负责响应的人员及流程。
- [ ] 在目标负载和故障条件下测量延迟、重试、外部写入重复情况和恢复时间。

勾选框不能保证可靠性。请将测量结果和未解决的限制与要求的 SLO、恢复时间和保留目标进行对照。

## 验证范围和参考资料

已检查官方文档和发布的源代码，以核对配置、Secret 解析路径和上传时机。已验证 S3 上传方法的示例结构和本地文件行为。未执行真实数据库迁移、AWS Secret / S3 调用、Collector 数据接收或故障恢复演练。


- [调度器高可用与数据库协调](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/scheduler.html)
- [数据库升级](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/upgrading.html)
- [数据库维护 CLI](https://airflow.apache.org/docs/apache-airflow/3.3.1/cli-and-env-variables-ref.html)
- [Fernet 加密](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/fernet.html)
- [Secret 后端和 worker 配置](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/secrets-backend/index.html)
- [任务日志](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/logging-tasks.html)
- [指标配置](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/metrics.html)
- [Amazon provider 9.34.0 S3 日志实现](https://github.com/apache/airflow/blob/providers-amazon/9.34.0/providers/amazon/src/airflow/providers/amazon/aws/log/s3_task_handler.py)

[README](README.md)

[测验](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)
