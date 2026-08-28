# 在 EKS 上部署 MLflow 测验

本测验检验你对 EKS 上 MLflow tracking server 架构的理解：backend store、artifact store、IAM 访问模式，以及将 tracking server 作为团队共享服务运行时的运维注意事项。

## 选择题

1. 在 EKS 上自行托管 MLflow tracking server，而不是使用像 SageMaker 的 MLflow-compatible tracking capability 这样的托管替代方案，主要的权衡是什么？
   - A) 无论团队规模如何，自行托管始终更便宜
   - B) 已经使用 EKS 的团队可复用现有的部署、observability 和 IAM 模式，但需要自行运维 tracking server、backend store 和 artifact store
   - C) 托管替代方案完全无法记录 metrics 或 parameters
   - D) 没有任何权衡；这两个选项在功能上完全相同

<details>

<summary>显示答案</summary>

**答案：B) 已经使用 EKS 的团队可复用现有的部署、observability 和 IAM 模式，但需要自行运维 tracking server、backend store 和 artifact store**

**解释：**
自行托管让团队能够复用其已用于其他工作负载的 Kubernetes 部署、observability 和 IAM（IRSA/Pod Identity）模式，但代价是需要直接运维 tracking server、其 backend database 和 artifact store，而不是将这些工作委托给托管替代方案。
</details>

2. 为什么 MLflow 默认的 SQLite backend store 不适合作为团队共享的 tracking server？
   - A) SQLite 无法存储浮点型 metric 值
   - B) SQLite 不支持团队共享 tracking server 所需级别的并发写入
   - C) SQLite 需要单独的 EKS node group
   - D) SQLite artifact 会在 30 天后过期

<details>

<summary>显示答案</summary>

**答案：B) SQLite 不支持团队共享 tracking server 所需级别的并发写入**

**解释：**
SQLite 对单个实验人员而言运行良好，但一旦多个进程需要并发写入，它就会失效——它不支持团队共享 tracking server 所需规模的并发写入者。因此，在生产环境中会使用真正的数据库（如 RDS PostgreSQL 或 Aurora Serverless v2）来替代它。
</details>

3. 与 artifact store 相比，backend store 存储什么类型的数据？
   - A) backend store 存储序列化模型等大型二进制对象；artifact store 存储结构化 metadata
   - B) backend store 存储结构化 metadata（experiments、runs、params、metrics、registered models、versions、aliases）；artifact store 存储大型二进制对象（models、plots、datasets）
   - C) 两个 store 都保存所有数据的相同副本以实现冗余
   - D) backend store 仅保存用户名和密码

<details>

<summary>显示答案</summary>

**答案：B) backend store 存储结构化 metadata（experiments、runs、params、metrics、registered models、versions、aliases）；artifact store 存储大型二进制对象（models、plots、datasets）**

**解释：**
backend store 是一个关系数据库，保存可使用 SQL 查询的所有内容——experiments、runs、params、metrics、registered models、versions 和 aliases。artifact store（在 AWS 上为 S3）保存 backend store 未保存的大型二进制对象，例如已记录的 models、plots 和 datasets。
</details>

4. 在 AWS 上，生产环境中 MLflow backend store 的两种标准选择是哪两个服务？
   - A) DynamoDB 和 EFS
   - B) 用于 PostgreSQL 的 Amazon RDS 和 Aurora Serverless v2
   - C) ElastiCache 和 S3
   - D) Redshift 和 Glacier

<details>

<summary>显示答案</summary>

**答案：B) 用于 PostgreSQL 的 Amazon RDS 和 Aurora Serverless v2**

**解释：**
两者都是真正支持并发写入者的关系数据库。尤其值得考虑 Aurora Serverless v2，因为它可以随突发 tracking 负载扩缩容，而无需让数据库全年都按峰值负载配置容量。
</details>

5. 文中提到的、用于在 Kubernetes 上部署 MLflow 的社区 Helm chart 是什么，如何添加其 repository？
   - A) `bitnami/mlflow`，通过 `helm repo add bitnami https://charts.bitnami.com/bitnami` 添加
   - B) `community-charts/mlflow`，通过 `helm repo add community-charts https://community-charts.github.io/helm-charts` 添加
   - C) MLflow 没有受维护的社区 chart
   - D) `mlflow/mlflow-operator`，仅通过 `kubectl apply -f` 安装

<details>

<summary>显示答案</summary>

**答案：B) `community-charts/mlflow`，通过 `helm repo add community-charts https://community-charts.github.io/helm-charts` 添加**

**解释：**
`community-charts/helm-charts` 维护一个 MLflow chart，支持可配置的 backend database 和 object storage 设置，为手动编写自己的 Deployment/Service/Ingress manifests 提供了一种实用的替代方案。
</details>

6. 对于新部署，哪种 EKS 机制被认为是将 IAM role 绑定到 tracking server 的 ServiceAccount 的更现代默认选择？
   - A) 存储在 ConfigMap 中的静态 IAM access keys
   - B) EKS Pod Identity；对于已经在其上实现标准化的 clusters，IRSA 仍然有效
   - C) 直接附加到 worker node EC2 instances 的 instance profiles
   - D) 烘焙到 container image 中的共享 root AWS account credential

<details>

<summary>显示答案</summary>

**答案：B) EKS Pod Identity；对于已经在其上实现标准化的 clusters，IRSA 仍然有效**

**解释：**
EKS Pod Identity 是将 IAM roles 绑定到 Pods 的较新机制，并且正日益成为在 EKS 上进行新的 IAM-to-Pod 绑定时推荐的默认选择。IRSA 仍是有效选择，尤其适合已在其上实现标准化的团队或 clusters。
</details>

7. 为什么以 Postgres 为后端的 MLflow tracking server 可以安全地运行多个 replicas，而以 SQLite 为后端的默认配置完全无法横向扩展？
   - A) Postgres replicas 会自动在 Pods 之间同步内存中的状态
   - B) 当使用 Postgres 和 S3 作为后端时，tracking server 是无状态的，因为所有共享状态都位于 Pod 外部；而 SQLite 无法容忍并发写入者
   - C) SQLite 比 Postgres 需要更多 CPU，因此将其横向扩展是一种浪费
   - D) Kubernetes 禁止运行任何使用数据库的 Deployment 的多个 replicas

<details>

<summary>显示答案</summary>

**答案：B) 当使用 Postgres 和 S3 作为后端时，tracking server 是无状态的，因为所有共享状态都位于 Pod 外部；而 SQLite 无法容忍并发写入者**

**解释：**
由于所有持久状态都位于 backend store 和 artifact store 中，而非 Pod 中，以 Postgres 为后端的 tracking server 是无状态的，可以安全地水平扩展。SQLite 缺乏并发写入者支持，因此单进程默认配置完全无法安全地横向扩展。
</details>

8. 当模型具有 registered version 或 alias 后，文中描述的自然下一步是什么，为什么它不在本系列的范围内？
   - A) 重新运行 training job；它不在范围内是因为第 1 部分已经介绍了 training
   - B) 将该 model version 加载到 serving system（KServe、custom wrapper、SageMaker 等）中；它不在范围内是因为 serving infrastructure 本身是一个广泛的主题
   - C) 删除该 model version；它不在范围内是因为 MLflow 不支持删除
   - D) 将 backend store 迁移到 DynamoDB；它不在范围内是因为不支持 DynamoDB

<details>

<summary>显示答案</summary>

**答案：B) 将该 model version 加载到 serving system（KServe、custom wrapper、SageMaker 等）中；它不在范围内是因为 serving infrastructure 本身是一个广泛的主题**

**解释：**
模型具有 registered version 或 alias 后，许多团队会继续将其加载到 serving system 中，例如 KServe、自定义 FastAPI/Flask wrapper 或 SageMaker。该 serving layer 本身就是一个广泛的主题，且被明确排除在这个由三部分组成的系列范围之外。
</details>

## 简答题

9. 请列出要使 MLflow 作为团队共享服务在 EKS 上运行而必须部署的三个核心架构部分，并简要说明每部分存储什么或执行什么功能。

<details>

<summary>显示答案</summary>

**答案：**
- MLflow Tracking Server：运行 `mlflow server` 的无状态 container，公开 REST API 和 UI。
- backend store：关系数据库（例如 RDS PostgreSQL 或 Aurora Serverless v2），保存结构化 metadata——experiments、runs、params、metrics、registered models、versions 和 aliases。
- artifact store：object storage（在 AWS 上为 S3），保存已记录的 models、plots 和 datasets 等大型二进制对象。

**解释：**
一旦不止一个人共享 tracking server，这三者缺一不可——tracking server 需要可靠的位置来写入其结构化 metadata 和大型 artifacts，并且这两者都不应存放在 tracking server Pod 本身中。
</details>

10. 请解释为什么 readiness 和 liveness probes 对 tracking server Deployment 很重要，以及为什么本文档未指定精确的 health-check endpoint path。

<details>

<summary>显示答案</summary>

**答案：**
readiness 和 liveness probes 让 Service 仅将流量路由到实际能够处理请求的 Pods，并让 Kubernetes 自动重启已停止响应的 Pod——这是任何长时间运行的 Kubernetes service 的标准实践。本文档未指定精确的 health-check path，因为它可能因 MLflow version 而异，因此应针对所部署的特定 version 进行确认，而非想当然地假定。

**解释：**
针对虚构或 version 不匹配的 endpoint path 进行探测，要么会将健康的 Pods 标记为未就绪，要么无法检测出真正卡住的 Pod，因此确认你的 MLflow version 的实际 path 是更安全的方法。
</details>

---

[返回学习材料](../../../ai-ml/mlflow/03-eks-deployment.md)
