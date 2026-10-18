# Airflow 架构测验

Airflow 3.3.1 / Helm chart 1.22.0 · 2026 年 9 月。

## 1. 关于 Airflow 2 的 DAG 解析，哪项描述正确？

- A) 所有文件都只在 scheduler 的同一个循环中解析
- B) DAG 只从 Redis 读取
- C) 早已有文件处理子进程和可选的独立 DAG 处理
- D) 不经解析就会执行任务

<details>
<summary>显示答案</summary>

**C**

Scheduler 可以启动一个 manager，由它为每个文件创建子进程；也可以使用独立的 DAG 处理。序列化 DAG 调度和多 scheduler 高可用性也早于 Airflow 3。

</details>

## 2. Airflow 3 的 DAG processor 有什么作用？

- A) 执行每个 operator
- B) 只为 UI 用户签发 JWT
- C) 替代 Celery broker
- D) 解析/序列化 bundle 中的 DAG，并更新相关元数据

<details>
<summary>显示答案</summary>

**D**

它是 Airflow 3 中必需的独立角色。Worker 也需要执行代码/依赖；只将 DAG 代码放在 processor 上是不够的。

</details>

## 3. 分离 DAG processor 能带来什么？

- A) 可以更独立地部署和调优解析与调度
- B) 消除所有调度延迟
- C) 消除数据库瓶颈
- D) 只要增加副本就保证高可用

<details>
<summary>显示答案</summary>

**A**

新 DAG 的解析延迟、共享资源/数据库负载和过高并发仍可能影响调度。角色分离不能取代运维验证。

</details>

## 4. 在由 supervisor 进程管理的正常 Python Task SDK 运行中，由谁调用 API？

- A) 用户任务代码直接执行元数据 SQL
- B) Worker 一侧的 supervisor 使用 task JWT 调用 Execution API
- C) Redis 负责传递所有状态访问
- D) Kubernetes 存储 XCom

<details>
<summary>显示答案</summary>

**B**

Task runner 和 supervisor 通过 socket 通信。Worker 到 API 的寻址、身份验证和网络配置都很重要；Celery result backend 等 executor 内部组件应单独检查。

</details>

## 5. 关于 triggerer，哪项说法正确？

- A) 它运行每个完整的 operator
- B) 所有精简部署都必须使用它
- C) 它运行延迟任务的 trigger；任务之后会在 worker 上恢复
- D) 所有异步任务都会释放 worker slot

<details>
<summary>显示答案</summary>

**C**

不使用延迟执行的部署可以不启用它。延迟任务会释放 worker slot，通常也会释放 pool slot；pool 行为可以配置。

</details>

## 6. 关于元数据数据库和 Celery broker，哪项说法正确？

- A) 每种部署都必须使用 PostgreSQL 和 Redis
- B) SQLite 是标准的生产环境建议
- C) MariaDB 和 MySQL 的支持完全相同
- D) PostgreSQL/MySQL 受支持，而且 Celery 除 Redis 外还有其他 broker 选项

<details>
<summary>显示答案</summary>

**D**

本系列以 PostgreSQL 为例。SQLite 用于开发/测试；MariaDB 不受支持；KubernetesExecutor 本身不需要 Celery broker。

</details>

## 7. Airflow 3.0 不再支持哪些固定的混合 executor 类？

- A) LocalKubernetesExecutor 和 CeleryKubernetesExecutor
- B) LocalExecutor 和 CeleryExecutor
- C) KubernetesExecutor 和所有 broker
- D) DAG processor 和 triggerer

<details>
<summary>显示答案</summary>

**A**

固定的双路混合类不同于并发 executor 配置。应显式配置兼容的 executor，并按任务选择。

</details>

## 8. 并发 executor 和 DAG 默认值如何工作？

- A) 仅在 3.3 中引入；未安装的 executor 也能使用
- B) 自 2.10.0 起受支持；在 DAG `default_args` 和任务覆盖项中设置 executor
- C) 任意时刻都只能使用一个
- D) 所有选择都只能使用 Redis 队列名称

<details>
<summary>显示答案</summary>

**B**

第一个配置的 executor 是默认值。任务会选择已配置的名称/别名，而 DAG `default_args` 可以提供任务默认值。

</details>

## 9. DAG bundle 与 git-sync 有什么关系？

- A) Airflow 3 移除了 git-sync
- B) 启用 S3 versioning 后，每个 S3DagBundle 都会自动版本化
- C) git-sync 仍受支持；是否版本化取决于 bundle
- D) Worker 永远不需要 DAG 代码

<details>
<summary>显示答案</summary>

**C**

GitDagBundle 支持版本化；经审查的 Local/S3/GCS bundle 则不支持。应核实代码交付方式以及重试时实际使用的代码版本。

</details>

[指南](../../../data-on-eks/airflow/01-architecture.md)
