# Spark Operator 测验

基线版本：Kubeflow 2.5.2 和 Apache operator 1.0.0 / chart 1.8.0。

## 1. 两种 Spark operator 之间是什么关系？

- A) 同一个 chart 的重命名版本
- B) Kubeflow 停止支持后的替代项目
- C) 使用不同 API 和生命周期模型的独立项目
- D) 只更改 apiVersion 就能完全兼容

<details>
<summary>显示答案</summary>

**答案：C**

Kubeflow 使用 sparkoperator.k8s.io/v1beta2；本章使用 Apache spark.apache.org/v1。迁移时也需要审查字段、状态和重试行为。

</details>

## 2. 经评审的 Apache operator 1.0.0 配套使用哪个 chart？

- A) 必须使用 1.0.0
- B) 与 Kubeflow 一样使用 2.5.2
- C) 与 Spark 一样使用 4.2.0
- D) 1.8.0

<details>
<summary>显示答案</summary>

**答案：D**

Chart 版本和应用版本彼此独立。应检查发布/chart 元数据和渲染出的资源。

</details>

## 3. 使用 Comet 或 Gluten 需要什么？

- A) 兼容的插件、镜像、类路径和配置
- B) 只需安装 Apache operator
- C) 所有架构和 Spark 版本上的行为都相同
- D) Kubeflow 永远无法运行此类工作负载

<details>
<summary>显示答案</summary>

**答案：A**

官方示例有额外的前置条件。仅选择 operator 并不能保证加速效果或插件兼容性。

</details>

## 4. 关于直接使用 spark-submit，哪项说法正确？

- A) 它总是提交后即返回，不等待结果
- B) 它可以等待并显示日志；operator 的 CR 调和是单独的功能
- C) 它无法创建 executor Pod
- D) 它的配置无法在 Git 中进行版本控制

<details>
<summary>显示答案</summary>

**答案：B**

原生提交方式提供状态、日志和 UI 访问。Operator 则增加了 CR 生命周期管理、计划任务控制器和应用重试。

</details>

## 5. Kubeflow 2.5.2 的 webhook.enable 默认值是什么？

- A) false
- B) 会随 Spark 版本自动更改
- C) true
- D) 仅在默认安装命名空间中为 true

<details>
<summary>显示答案</summary>

**答案：C**

示例明确指定了默认值。如果禁用，请检查依赖该准入路径的功能。

</details>

## 6. 经评审的两个 chart 在准入方面有什么区别？

- A) 两者都安装相同的 Pod mutator
- B) Webhook 会将 Pod 放置到节点上
- C) Webhook 会分配 Spark 任务
- D) Apache 不会安装与 Kubeflow 等效的 Pod 变更 webhook

<details>
<summary>显示答案</summary>

**答案：D**

图中展示的是 Kubeflow。Kubernetes 调度和 Spark driver 任务分配仍然是不同的职责。

</details>

## 7. 在 spark-jobs 命名空间运行作业需要满足什么？

- A) 使监听的命名空间、作业命名空间和 RBAC 相互匹配
- B) 所有作业都只能提交到安装命名空间
- C) 使用 ClusterRole 后就无需考虑监听范围
- D) 监听 default 会自动包含所有命名空间

<details>
<summary>显示答案</summary>

**答案：A**

安装命名空间和工作负载命名空间可以不同。默认监听范围不会自动包含新的作业命名空间。

</details>

## 8. Kubeflow 中自定义卷应配置在哪里？

- A) 仅在 spec.driver.volumes 中
- B) 在 spec.volumes 中定义，并通过 driver/executor.volumeMounts 挂载
- C) 仅在 spec.executor.volumes 中
- D) 在 status.volumes 中

<details>
<summary>显示答案</summary>

**答案：B**

经评审的 CRD 没有 driver.volumes 或 executor.volumes 字段。在 spec.volumes 中声明共享卷定义，再按需挂载。

</details>

## 9. spark-local-dir- 卷有什么特殊之处？

- A) 会自动创建物理 NVMe 磁盘
- B) 会将所有卷转换为 S3
- C) 会将其转换为 Spark 原生本地卷配置
- D) 必须仅通过 webhook 实现

<details>
<summary>显示答案</summary>

**答案：C**

通用卷 mutator 会跳过这些本地目录卷；提交配置负责处理它们。emptyDir 本身并不会选择物理存储。

</details>

## 10. Kubeflow 2.5.2 中哪些 serviceAccount 字段有效？

- A) 仅 driver.serviceAccount
- B) 仅 executor.serviceAccount
- C) 两者都必须包含 AWS IAM ARN
- D) driver.serviceAccount 和 executor.serviceAccount 都有效

<details>
<summary>显示答案</summary>

**答案：D**

两个字段都指定 Kubernetes service account。API RBAC 和 AWS 数据权限需分别配置。

</details>

## 11. 如何安排 ScheduledSparkApplication 每天在 UTC 02:00 运行？

- A) 设置 schedule: "0 2 * * *" 并将 timeZone 设为 UTC
- B) 始终依赖控制器本地时间
- C) 不支持 timeZone
- D) 只设置 executor Pod 的 TZ

<details>
<summary>显示答案</summary>

**答案：A**

2.5.2 版本支持 timeZone，默认值为 Local。明确指定计划时区可避免依赖控制器环境。

</details>

## 12. concurrencyPolicy: Forbid 会阻止什么？

- A) 所有系统中的重复写入
- B) 某个计划资源的上一次运行与下一次计划运行重叠
- C) 所有应用重试
- D) 所有手动提交

<details>
<summary>显示答案</summary>

**答案：B**

其他调度器、手动运行和重试仍可能造成重复副作用。应设计幂等或事务性输出。

</details>

## 13. suspend: true 会做什么？

- A) 必然终止当前运行的子作业
- B) 回滚已写入的数据
- C) 停止未来的计划触发
- D) 删除 operator 部署

<details>
<summary>显示答案</summary>

**答案：C**

应单独检查或终止当前运行。挂起并不等于数据回滚或备份。

</details>

## 14. 只将 sparkVersion 更改为 4.2.0 能保证什么？

- A) 控制器运行时会自动升级
- B) 与每个 Spark 插件兼容
- C) Kubernetes 会自动升级
- D) 不能保证控制器的 spark-submit 已升级

<details>
<summary>显示答案</summary>

**答案：D**

Kubeflow 实验与其控制器提交运行时 4.0.4 保持一致。其他提交器/工作负载组合需要单独测试。

</details>

## 15. Operator 会监控哪些 Pod 状态？

- A) driver 和 executor 都会监控
- B) 仅监控 driver
- C) 仅监控 executor
- D) 不监控 Pod 状态

<details>
<summary>显示答案</summary>

**答案：A**

控制器还会更新 executor 状态并执行清理。Spark driver 会请求 executor 并分配 Spark 任务。

</details>

## 16. 使用 OnFailure 重试时，重要的是什么？

- A) 会自动实现恰好一次写入
- B) 应用重新运行可能会重复产生输出副作用
- C) 只会重启同一个容器
- D) 每个失败的外部事务都会回滚

<details>
<summary>显示答案</summary>

**答案：B**

提交/应用尝试与容器重启是不同概念。除了重试次数和间隔，还要验证数据语义。

</details>

## 17. IRSA 和 EKS Pod Identity 有什么区别？

- A) 两者都只需要相同的注释
- B) Kubernetes Role 会授予 S3 访问权限
- C) IRSA 使用 OIDC/角色注释；Pod Identity 使用关联关系及其 Agent
- D) S3 URI 会完成身份验证

<details>
<summary>显示答案</summary>

**答案：C**

应配置 AWS 权限、信任关系或关联，以及兼容的凭证提供程序。还要在实际 Pod 中验证生效的身份和访问权限。

</details>

## 18. Chart 默认在 8080 上提供的 Prometheus 端点会暴露什么？

- A) 自动收集每个 Spark JVM 的 JMX 指标
- B) 所有 Spark History Server 日志
- C) S3 数据验证结果
- D) Operator 指标

<details>
<summary>显示答案</summary>

**答案：D**

工作负载 JMX 需要单独配置应用 exporter JAR、配置和抓取方式。

</details>

## 19. Helm 升级时应如何处理 CRD？

- A) 检查 CRD 迁移，并显式启用 hook.upgradeCrd
- B) 普通 helm upgrade 总会替换 CRD
- C) 始终先删除现有 CRD
- D) CRD 不会影响应用资源

<details>
<summary>显示答案</summary>

**答案：A**

普通升级不会自动替换 crds/ 中的 CRD。删除 CRD 会影响其自定义资源，不应作为常规升级步骤。

</details>

## 20. Helm 渲染成功并通过 CRD 检查能证明什么？

- A) 已证明实时 webhook 连通性
- B) 已验证资源形状和配置路径；实际工作负载是否成功需要另行检查
- C) 已证明 S3 访问和数据正确性
- D) 已证明与所有 Spark 版本兼容

<details>
<summary>显示答案</summary>

**答案：B**

还要检查实际 Pod、状态、输出、重试行为和权限。仅有 COMPLETED 并不能证明外部数据正确。

</details>

[正文 / 指南](../../../data-on-eks/spark/02-spark-operator.md)
