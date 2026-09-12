# MLflow EKS 部署测验

## 选择题

1. 在 EKS 上自托管的主要权衡是什么？
   - A) 成本始终低于托管服务
   - B) 可以复用 Kubernetes 模式，但需要自己运维服务器、存储和访问控制
   - C) 托管服务无法跟踪实验
   - D) S3 和数据库会自动创建

<details>
<summary>显示答案</summary>

**答案：B**

请比较运维工作量、功能、支持的版本以及实测负载。
</details>

2. 关于 SQLite 并发，哪种说法是准确的？
   - A) 第二个用户一定会立即导致其崩溃
   - B) 可以支持多进程和串行化写入，但存在写入者、锁和共享文件方面的限制
   - C) 它不是关系型数据库
   - D) 各个 Pod 本地的独立文件会自动组成一个共享数据库

<details>
<summary>显示答案</summary>

**答案：B**

要区分 SQLite 自身的能力与多 Pod 存储拓扑。
</details>

3. 所审阅的社区 chart 1.11.7 中，元数据存储的默认值是什么？
   - A) 强制使用 RDS PostgreSQL
   - B) S3 对象
   - C) backendStore.defaultSqlitePath 为 :memory:
   - D) 自动预配的持久化 PVC

<details>
<summary>显示答案</summary>

**答案：C**

该 chart 的覆盖值与上游 CLI 新的 SQLite 文件默认值不同。
</details>

4. 使用外部的 tracking PostgreSQL 数据库是否会自动共享所有其他状态？
   - A) 是，包括所有认证数据库和缓存
   - B) 是，包括所有 worker 内存
   - C) 是，包括所有会话密钥
   - D) 不会；需要分别检查独立的认证数据库、secret、队列和缓存

<details>
<summary>显示答案</summary>

**答案：D**

在增加副本数之前，请先检查已启用功能的共享状态。
</details>

5. 应该如何处理 chart、镜像和源码版本？
   - A) 它们始终共用同一个版本号
   - B) 存在源码标签就保证 OCI 包一定存在
   - C) 逐一核实，并下载/渲染实际的包
   - D) 使用 latest 标签就无需检查镜像摘要

<details>
<summary>显示答案</summary>

**答案：C**

所审阅的上游 chart 源码版本与 appVersion 同样存在差异。
</details>

6. ServiceAccount 通过 IAM 获得 S3 访问权限后，是否自动允许登录 PostgreSQL？
   - A) 总是允许
   - B) 不会；需要单独配置数据库网络、TLS、用户/凭证或 IAM 数据库认证
   - C) 只有存储桶名称匹配时才允许
   - D) 把数据库密码放进镜像里

<details>
<summary>显示答案</summary>

**答案：B**

这是相互独立的授权层与认证层。
</details>

7. EKS Pod Identity 需要哪些条件？
   - A) 无条件支持所有 Fargate 和 Windows Pod
   - B) 只需要一个 ServiceAccount 名称
   - C) Linux EC2 工作节点、Agent、关联配置、受支持的 SDK 以及相关设置
   - D) 一个静态的 root 访问密钥

<details>
<summary>显示答案</summary>

**答案：C**

请分别确认 IRSA 与 Pod Identity 的支持情况和配置方式。
</details>

8. 仅依靠 SecretKeyRef 和 allowed_hosts 就能完成安全防护吗？
   - A) 它们消除了环境变量暴露风险，并实现了所有用户授权
   - B) 不能；需要分别审查 secret 的下发方式以及应用层的认证/授权
   - C) 它们会自动备份数据库
   - D) 必须允许所有 CORS 来源

<details>
<summary>显示答案</summary>

**答案：B**

要理解运行时 secret 注入与主机校验各自的边界。
</details>

## 简答题

9. /health 返回 200 能否证明 RDS 和 S3 都是健康的？

<details>
<summary>显示答案</summary>

不能。经核实的实现只是返回 OK、200，用于表示 HTTP 进程可响应。数据库、S3、授权以及实际工作负载路径需要单独持续检查。
</details>

10. 在评估高频日志写入与 Aurora Serverless v2 时，需要关注什么？

<details>
<summary>显示答案</summary>

需要测量批处理、事务、指标历史、trace 负载，以及跨副本/worker 的连接池。Aurora 存在容量、连接数、I/O 和事务方面的限制，并不保证能无限吸收突发流量或达到最低成本。
</details>

---

[返回学习资料](../../../ai-ml/mlflow/03-eks-deployment.md)
