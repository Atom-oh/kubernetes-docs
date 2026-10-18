# Amazon EMR on EKS 测验

基于 2026 年 10 月 16 日审查的指南。

## 1. 什么是虚拟集群？

<details>
<summary>显示答案</summary>

它是向 EMR 注册 EKS 命名空间的一种逻辑对象。它本身不创建计算容量，但初次设置时可能会配置服务关联角色和 CAM 访问条目/策略。

</details>

## 2. StartJobRun 与通过 EMR Spark Operator 提交有何区别？

<details>
<summary>显示答案</summary>

StartJobRun 是面向虚拟集群的 AWS API。另行安装的 Operator 接收 SparkApplication CR；它不是 StartJobRun 内部的委派选项。

</details>

## 3. 通过 Operator 提交的 CR 会自动获得 EMR 作业 ID 吗？

<details>
<summary>显示答案</summary>

不要假设会获得。应通过 Operator 路径观察 CR 状态、日志和重试；这与 EMR 作业 API 的生命周期分开处理。

</details>

## 4. EMR Spark Operator 从哪个版本开始受支持，如何安装？

<details>
<summary>显示答案</summary>

EMR 6.10.0+。安装文档指定的 EMR Chart 和兼容运行时，然后使用 kubectl apply 提交。不要将它与第 2 部分介绍的当前上游 Chart 视为相同发行版。

</details>

## 5. emr-spark-8.0.0 中包含哪个 Apache Spark 版本？

<details>
<summary>显示答案</summary>

4.0.2-amzn-0。此版本于 2026 年 5 月发布，提供 Spark 4.x 正式版；8.0.0 是 EMR 运行时发行版名称。

</details>

## 6. -latest 和带日期的后缀有何区别？

<details>
<summary>显示答案</summary>

-latest 会随该发行版的安全更新而变化，并不固定到完全相同的镜像字节。带日期的后缀有助于复现某个发行版，但之后仍需审查后续更新。

</details>

## 7. 后续作业会使用 CreateVirtualCluster 响应中的哪个值？

<details>
<summary>显示答案</summary>

使用 id 字段。将其设置为 StartJobRun 的 virtualClusterId，并验证注册的命名空间和 RUNNING 状态。

</details>

## 8. 执行角色的数据权限是否等同于调用方权限？

<details>
<summary>显示答案</summary>

不等同。执行角色授予工作负载访问 S3、KMS、日志等资源的权限。调用方需要 API 权限和使用指定角色的权限；应检查 ExecutionRoleArn 条件以及适用的 PassRole 权限。

</details>

## 9. update-role-trust-policy 会做什么？

<details>
<summary>显示答案</summary>

对于 IRSA，它会更新执行角色的信任策略，使其信任集群 OIDC 提供方、命名空间和 EMR 管理的服务账户身份。它不会自动授予 S3 权限或调用方权限。

</details>

## 10. StartJobRun 可以使用 Pod Identity 吗？

<details>
<summary>显示答案</summary>

可以，从 EMR 7.3.0 开始支持。需要 Agent、节点 EKS Auth 权限、对 pods.eks.amazonaws.com 的信任以及服务账户关联。IRSA 注释不能替代这些配置。

</details>

## 11. create-role-associations 会准备哪些关联？

<details>
<summary>显示答案</summary>

在执行角色与 EMR 提交器、driver 和 executor 服务账户之间创建三个关联。使用当前 CLI 辅助工具；命名空间/角色退役后，应单独清理不再使用的关联。

</details>

## 12. maxConcurrentJobRuns=2 是否设置了命名空间的 CPU 上限？

<details>
<summary>显示答案</summary>

没有。它限制作业数量；maxInQueueJobRuns 限制排队作业。CPU/内存配额和每个作业的 executor 上限是独立配置。

</details>

## 13. StartJobRun 成功返回后，作业就完成了吗？

<details>
<summary>显示答案</summary>

没有。应使用返回的作业 ID 检查最终状态和日志。冒烟测试示例会同时检查 COMPLETED 和 SMOKE_OK rows=10 total=45。

</details>

## 14. 重用 clientToken 能保证数据输出恰好一次吗？

<details>
<summary>显示答案</summary>

它会对 API 请求去重，但不会去重应用程序重试或外部副作用。每次有意发起新的运行时都应使用新令牌。

</details>

## 15. 可以自定义 EMR Pod 模板或镜像吗？

<details>
<summary>显示答案</summary>

可以，通过受支持的 Pod 模板/自定义镜像路径实现。请遵守各发行版的限制，不要随意覆盖由 StartJobRun 管理的命名空间、服务账户或 Pod 名称。

</details>

## 16. CloudWatch 和 Step Functions 集成是否无需配置即可完整工作？

<details>
<summary>显示答案</summary>

不可以。需要配置日志监控和执行角色权限，以及状态机和其角色。服务指标也不等同于完整的 Spark JVM 遥测数据。

</details>

## 17. EMR Studio 如何运行交互式工作负载？

<details>
<summary>显示答案</summary>

CreateManagedEndpoint 端点使用 Jupyter Enterprise Gateway 管理内核。这与常规的 StartJobRun 批处理调用不同，还需要配置私有网络、ALB 和角色。同一端点上的用户/内核共享其角色。

</details>

## 18. 为什么删除虚拟集群不代表彻底清理？

<details>
<summary>显示答案</summary>

应先检查并清理指定的作业/端点。EKS、命名空间、S3、日志、IAM 角色和 Pod Identity 关联都有各自的生命周期；还应检查删除状态和权限错误。

</details>

[指南](../../../data-on-eks/spark/03-emr-on-eks.md)
