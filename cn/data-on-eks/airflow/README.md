# EKS 上的 Airflow 深入指南

> **审查基线**：Airflow 3.3.1 · 官方 Helm chart 1.22.0
> **已核实的最新上游补丁版本**：Airflow 3.3.2（2026 年 9 月 17 日）；示例仍使用 3.3.1 · 2026 年 10 月 12 日

Apache Airflow 将工作流依赖定义为 DAG，并负责调度、运行和观察其中的任务。在 EKS 上，每个任务的 Pod 行为取决于 **executor 和 operator**，而不只是是否安装了 Helm chart。

Airflow 2 已于 2026 年 4 月 22 日结束生命周期（EOL）。新部署应使用仍受维护的 3.x 版本。Chart 1.22.0 默认使用 **Airflow 3.2.2**，因此应分别核实 chart、镜像和 Airflow 配置的版本。本系列审查 3.3.1 的行为，并通过覆盖版本配置来渲染 chart。

上游 3.3.2 于 2026 年 9 月 17 日发布。显式提供的 Bearer token 优先于会话 cookie；即使 cookie 有效，只要 Bearer token 无效，请求仍会被拒绝。这会影响同时混用浏览器 cookie 与服务凭证的 API 客户端。

本系列的示例和 Helm 检查仍基于 3.3.1，尚未在 3.3.2 上重新验证。

## 核心架构

- Scheduler 和 executor 决定并提交任务工作，同时更新元数据状态。
- 必需的 DAG processor 会解析并序列化 DAG bundle。Worker 也必须通过相应的 bundle 或代码分发路径获取任务代码。
- API server 提供 UI、REST API 和 Task Execution API 路径。受监督的 Python Task SDK 运行时通过该 API 访问状态以及 Connection/Variable/XCom。
- 可延迟任务等待期间，triggerer 会运行 **triggers**。不使用延迟执行的精简部署可以不启用它。
- 元数据后端包括 PostgreSQL 和 MySQL。本系列以 PostgreSQL 为例，并非表示只有这一种选择。Redis 也不是 Celery 唯一可用的 broker。

![Airflow 控制组件、元数据、任务执行 API 和可选的 executor 路径。](../../.gitbook/assets/en-data-on-eks-airflow-readme-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-readme-0.html)

DAG bundle 并不会在所有情况下取代 git-sync。官方 chart 仍支持 git-sync；应区分代码交付方式和 bundle 版本管理。将解析器分离也无法消除所有延迟、数据库瓶颈或高可用性问题。

## 系列内容

1. [Kubernetes 上的 Airflow 架构](01-architecture.md)：组件、Execution API、数据库/broker 和 executor。
2. [Helm 部署与 executor 选择](02-helm-deployment.md)：官方 chart、版本、连接和 worker 扩缩容。
3. [DAG 模式与 KubernetesPodOperator](03-dag-patterns.md)：Pod、代码交付、bundle 以及 Spark/dbt。
4. [Amazon MWAA 集成](04-mwaa-integration.md)：托管范围、EKS 集成、版本和成本。
5. [运维与安全](05-operations.md)：高可用性、迁移、密钥、日志、观测和恢复检查。

- [Airflow 3.3.1 架构](https://airflow.apache.org/docs/apache-airflow/3.3.1/core-concepts/overview.html)
- [Airflow 3.3.2 发布说明](https://airflow.apache.org/docs/apache-airflow/3.3.2/release_notes.html)
- [支持的版本和生命周期](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/supported-versions.html)
- [Airflow 前置条件](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/prerequisites.html)
- [Executor 配置和历史](https://airflow.apache.org/docs/apache-airflow/3.3.1/core-concepts/executor/index.html)
- [DAG bundle](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/dag-bundles.html)
- [可延迟 operator 和 trigger](https://airflow.apache.org/docs/apache-airflow/3.3.1/authoring-and-scheduling/deferring.html)

[测验](../../quizzes/data-on-eks/airflow/01-architecture-quiz.md)
