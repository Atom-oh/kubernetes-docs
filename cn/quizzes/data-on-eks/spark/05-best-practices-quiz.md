# 第 5 部分：最佳实践与安全测验

Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4。

## 1. 哪些 Hadoop/S3A 版本与经审查的 Spark 4.2 发行版匹配？

<details>
<summary>显示答案</summary>

Hadoop 客户端和 hadoop-aws 都使用 3.5.0，配合 AWS SDK v2 bundle 2.35.4 及解析出的运行时依赖。对于其他镜像或 EMR，应重新检查捆绑版本。

</details>

## 2. 这套 SDK v2 组合应使用哪个 IRSA provider？

<details>
<summary>显示答案</summary>

software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider。在此组合中，旧的 com.amazonaws.auth.WebIdentityTokenCredentialsProvider 不会自动映射到新 provider。

</details>

## 3. 使用 Pod Identity 时需要做哪些调整？

<details>
<summary>显示答案</summary>

使用 ContainerCredentialsProvider，配置服务账户关联、对 pods.eks.amazonaws.com 的信任，以及 Agent/节点权限。IRSA 注释和 OIDC 配置不能替代这条路径。

</details>

## 4. 默认的 S3A 凭证链会自动使用 IRSA 吗？

<details>
<summary>显示答案</summary>

经审查的 Hadoop 3.5.0 凭证链包含容器/实例包装器，但不包含 web-identity provider。应指定所需 provider，并验证实际身份和前缀访问权限。

</details>

## 5. 为什么要分别为 driver、executor 和 History Server 配置服务账户？

<details>
<summary>显示答案</summary>

这样可以将 driver 的 Kubernetes 管理权限与各进程的 S3 数据访问权限分开。禁用清理器后，History Server 可以从只读角色开始运行。

</details>

## 6. 命名空间级 Role 是否会将 driver 限制为只能访问自己的 executor？

<details>
<summary>显示答案</summary>

不会。它会在整个命名空间范围内授予相应资源/动词权限，不包含基于 Pod 标签的所有权条件。应结合准入和信任边界，限制 Pod 创建、其他服务账户的使用及主机访问。

</details>

## 7. 使用 ClusterRole 是否总意味着拥有集群范围的权限？

<details>
<summary>显示答案</summary>

不是。引用 ClusterRole 的 RoleBinding 可以将命名空间资源权限限制在该绑定所在的命名空间。应检查规则以及绑定类型/范围。

</details>

## 8. spark.authenticate=true 能提供 Spark UI 登录验证吗？

<details>
<summary>显示答案</summary>

不能。它用于验证内部连接。Kubernetes 生成的应用程序 Secret 可能会通过 executor 环境变量传播，因此读取 Pod 的权限很重要。UI 身份验证、授权和 TLS 是彼此独立的配置。

</details>

## 9. 仅按角色标签选择的 NetworkPolicy 有什么问题？

<details>
<summary>显示答案</summary>

命名空间中其他作业的 executor 也会匹配。示例会在 driver/executor 标签和策略中共享唯一的运行 ID。标签本身不是身份验证；应考虑能够伪造标签的 Pod 创建者。

</details>

## 10. 应用此 NetworkPolicy 是否会阻断所有其他流量路径？

<details>
<summary>显示答案</summary>

不会。策略是累加生效的，并且需要 CNI 强制执行。此示例仅限制 ingress。应分别检查 egress、节点/hostNetwork 行为、其他允许策略、DNS/API/AWS 端点和附加插件。

</details>

## 11. 为什么要将端口固定并设置 spark.port.maxRetries=0？

<details>
<summary>显示答案</summary>

端口冲突时会直接启动失败，而不会静默改用策略之外的端口。额外端点应单独配置端口和安全策略。

</details>

## 12. PrometheusServlet 和 executor 聚合端点是否相同？

<details>
<summary>显示答案</summary>

不同。/metrics/prometheus/ 提供 driver 的 Dropwizard registry；/metrics/executors/prometheus/ 提供由 driver 收集的 executor 聚合数据。每个 executor 都不会各自获得一个 Spark UI；应比较实际的序列、标签和单位。

</details>

## 13. JMX Java agent 和 Operator Chart 指标的关系是什么？

<details>
<summary>显示答案</summary>

Agent 运行在 JVM 内部，而不是作为另一个进程。默认的 Operator Chart 指标描述 Operator 本身；Chart 不会自动在每个 Spark JVM 中安装 Agent。

</details>

## 14. 创建 PodMonitor 就足以采集指标了吗？

<details>
<summary>显示答案</summary>

Prometheus 标签/命名空间选择器、服务发现 RBAC、Pod 端口/路径和 NetworkPolicy 必须彼此匹配。应检查 UP targets 和实际指标序列；短作业可能在抓取之前就已结束。

</details>

## 15. 作业结束后保留 driver Pod 对象，是否就能继续访问其 UI？

<details>
<summary>显示答案</summary>

不能。JVM 结束后，实时 UI 也会停止。History Server 根据单独持久化的事件日志重建历史记录，而不是使用 stdout/stderr 或检查点。

</details>

## 16. 仅挂载 History Server 配置文件是否就会加载它？

<details>
<summary>显示答案</summary>

不会。示例会显式使用 spark-class org.apache.spark.deploy.history.HistoryServer --properties-file，并以前台方式运行。还要验证路径、日志目录和 S3 身份。

</details>

## 17. History Server 是否会恢复每个历史作业的全部细节？

<details>
<summary>显示答案</summary>

前提是事件日志确实得到保留并且可读取。事件缺失、损坏、未刷新、被删除或压缩都会限制重建效果。事件日志不是数据恢复检查点，也不是输出备份。

</details>

## 18. Operator、cluster mode 和 IRSA 是否是生产环境的唯三选项？

<details>
<summary>显示答案</summary>

不是。应根据需求选择经过验证的直接提交方式、Operator 或 EMR、合适的 client/cluster mode，以及 IRSA/Pod Identity。在实际环境中测试权限、数据正确性、恢复、网络、资源和成本。

</details>

[指南](../../../data-on-eks/spark/05-best-practices.md)

[README](../../../data-on-eks/spark/README.md)
