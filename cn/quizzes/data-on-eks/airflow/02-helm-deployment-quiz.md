# Helm 部署与 Executor 选型测验

Chart 1.22.0 / Airflow 3.3.1 / KEDA 2.20。

## 1. 本指南使用哪个 Chart 和仓库别名？

<details>
<summary>显示答案</summary>

Apache Airflow 项目的官方 Chart。将仓库注册为 apache-airflow 后，命令使用 apache-airflow/airflow。不要混用独立社区 Chart 的 values。

</details>

## 2. Chart 1.22.0 实际的 Airflow/Executor 默认值是什么？

<details>
<summary>显示答案</summary>

Airflow 3.2.2 和 CeleryExecutor。本指南显式覆盖这些默认值，使用 Airflow 3.3.1/KubernetesExecutor 配置。

</details>

## 3. Chart.yaml 是否强制执行所有文档中说明的最低版本要求？

<details>
<summary>显示答案</summary>

不要这样假设。请使用 Helm 3.19.0+ 以及兼容的 Kubernetes/Airflow 版本。Chart 1.16 的 README 指定 Kubernetes 1.29+；即使审查中的 1.22 模板能针对 1.29 渲染，也不能证明该版本受支持。

</details>

## 4. 仅凭 Executor 就能确定 Redis 和 worker 的资源类型吗？

<details>
<summary>显示答案</summary>

Executor 会影响资源类型，但 Redis/外部 broker 配置和 worker 持久化方式也很重要。Worker 可以是 Deployment 或 StatefulSet，Celery 也可以使用外部 broker。

</details>

## 5. 禁用 PostgreSQL 后就配置了外部数据库吗？

<details>
<summary>显示答案</summary>

没有。还要准备数据库、迁移权限、URI/TLS 以及诸如 metadataSecretName 的连接引用。设置该 Secret 后，metadataConnection 就不再是权威配置来源。

</details>

## 6. 升级时应重新生成 Fernet/API/JWT 密钥吗？

<details>
<summary>显示答案</summary>

常规升级时应保留这些密钥。丢失 Fernet 密钥可能导致无法访问加密数据，JWT 变更也可能影响正在运行的任务身份验证。应有计划地处理备份和轮换。

</details>

## 7. 本示例如何避免使用默认的 admin/admin？

<details>
<summary>显示答案</summary>

它禁用 createUserJob，并针对所选 FAB auth manager 交互式运行 airflow users create，提示输入两次密码。其他 auth manager/SSO 需要各自的操作流程。

</details>

## 8. KubernetesExecutor 是否总要等待 1–2 分钟才会启动？

<details>
<summary>显示答案</summary>

不是。应测量镜像缓存/拉取、Kubernetes API/调度器、节点可用性/配置速度、配额和运行时初始化。Celery 在缩容到零后同样有冷启动时间。

</details>

## 9. KubernetesExecutor 能否使用任意 GPU/CLI worker 镜像？

<details>
<summary>显示答案</summary>

Worker 需要兼容的 Airflow 任务运行时以及 DAG/provider 依赖。这与 KubernetesPodOperator 使用工作负载镜像启动子 Pod 不同。

</details>

## 10. 没有 worker Pod 是否意味着 Airflow 总闲置成本为零？

<details>
<summary>显示答案</summary>

控制平面、数据库、broker、节点、存储和日志仍可能产生费用。按 Pod 计费或缩容到零并不保证总成本为零，也不代表完全安全隔离。

</details>

## 11. Chart 中 KEDA 的默认计时参数与示例配置分别是什么？

<details>
<summary>显示答案</summary>

默认值为 pollingInterval=5s 和 cooldownPeriod=30s。示例显式设置为 10s/300s。应区分缩容到零的冷却时间，以及高于零时 HPA 的扩缩容/稳定窗口。

</details>

## 12. SQL 中的 worker_concurrency 应替换成什么？

<details>
<summary>显示答案</summary>

替换为 Chart 渲染出的数值（本示例中为 4），而不是名为 worker_concurrency 的数据库列。统计该 worker 的队列/Executor 中相关的运行中和排队任务数量，除以并发度后向上取整。

</details>

## 13. 为什么 k8s 别名可能导致混合 Executor 的扩缩容错误？

<details>
<summary>显示答案</summary>

TaskInstance 会存储 task.executor。如果 Chart 只排除字面值 KubernetesExecutor，以 k8s 存储的任务就可能被计入 Celery 数量。过滤条件应匹配实际存储的值。

</details>

## 14. 如果查询结果为 25，而 maxReplicaCount=20，该怎么办？

<details>
<summary>显示答案</summary>

最大副本数会限制 worker，因此不能立即满足所有需求。应一并检查积压、并发、worker 资源、数据库/broker 负载和节点容量。

</details>

## 15. 为 Airflow Pod 配置 TLS 就足以让 KEDA 访问数据库吗？

<details>
<summary>显示答案</summary>

不够。KEDA 是独立的数据库客户端，需要 DNS、网络、权限、兼容的 URI 和 CA。URI 中的 sslrootcert 路径必须能被 scaler 读取；Chart 不会自动复制该文件。

</details>

## 16. KEDA 是否仅支持 Deployment？

<details>
<summary>显示答案</summary>

不是。Chart 会根据 Celery 的持久化配置管理 Deployment 或 StatefulSet。KubernetesExecutor 任务 Pod 不属于同一种副本池模式，但这并不妨碍将 KEDA 用于其他场景。

</details>

## 17. Helm --wait 成功是否代表验证已完成？

<details>
<summary>显示答案</summary>

还要检查迁移是否成功、长期运行组件是否 Ready、DAG 是否送达、worker 是否执行、Execution API、结果和日志。对于 KEDA 配置，还要测试由工作负载驱动的扩缩容、回到空闲状态和恢复。

</details>

## 18. Helm 卸载后是否会立即删除所有 PostgreSQL 数据？

<details>
<summary>显示答案</summary>

Pod 删除与 PVC/PV 数据生命周期并不相同。应分别检查 PVC 保留设置、StorageClass 回收策略，以及外部数据库的删除/备份；不要不加区分地删除共享命名空间、Secret 和数据库。

</details>

[指南](../../../data-on-eks/airflow/02-helm-deployment.md)

[上一份测验](./01-architecture-quiz.md)
