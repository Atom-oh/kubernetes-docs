# Grafana Loki 测验

> **最后更新**: 2026 年 9 月 13 日

基于[指南](../../../observability/logging/01-loki.md)中的 Loki 3.7.7/chart 18.12.1 示例。

---

1. 在 TSDB/数据块模型中，Loki 主要索引什么？

   - A) 每条日志行中的每个词
   - B) 流标签
   - C) 仅请求 ID
   - D) 仅时间戳

<details>
<summary>查看答案</summary>

**答案：B**

标签可缩小需要扫描的流范围。这并不能证明固定的 10× 成本优势，也不能消除解析/数据块读取成本。

</details>

---

2. 哪个组件会缓冲日志流、在启用时写入 WAL，并刷写数据块？

   - A) Distributor
   - B) Query frontend
   - C) Ingester
   - D) Index gateway

<details>
<summary>查看答案</summary>

**答案：C**

Ingester 也提供近期数据。WAL 需要持久化存储，其本身并不能保证无损交付或 HA。

</details>

---

3. 哪项说法符合本章节采用的当前部署指导？

   - A) SSD 永远是所有生产 EKS 集群的默认选项
   - B) 任意三个 Pod 都能保证跨三个可用区的容错能力
   - C) SingleBinary 是唯一的 chart 18.12.1 模式名称
   - D) SSD 已弃用；生产扩展/HA 指导建议使用 Distributed，并进行明确的运维规划

<details>
<summary>查看答案</summary>

**答案：D**

SSD 计划在 Loki 4.0 中移除。容量和可用性取决于工作负载、存储、拓扑以及经过测试的故障处理，而非固定的 GB/天表格。

</details>

---

4. 哪个查询会返回五分钟内匹配 error 日志行的每秒速率？

   - A) `rate({app="nginx"} |= "error" [5m])`
   - B) `count({app="nginx"} |= "error")`
   - C) `sum({app="nginx"} |= "error")`
   - D) `increase(count_over_time({app="nginx"}[5m]))`

<details>
<summary>查看答案</summary>

**答案：A**

这是每个流的日志行速率，并不会自动成为 HTTP 请求错误比率。LogQL 支持 count 向量聚合，但 B 未提供所需的指标向量输入。

</details>

---

5. 调查时需要唯一的请求 ID。更好的起点是什么？

   - A) 索引每个请求 ID 以加快查询
   - B) 在访问/隐私控制下，将必要的 ID 保留在日志内容或结构化元数据中
   - C) 删除所有集群/命名空间标签
   - D) 假设总流数始终等于标签基数的乘积

<details>
<summary>查看答案</summary>

**答案：B**

高基数索引值会创建许多流。结构化元数据并不是脱敏，基数乘积也只是已观测组合数的上限。

</details>

---

6. 在 IRSA 示例中，如何保持 ServiceAccount 所有权一致？

   - A) eksctl 和 Helm 都创建相同的 ServiceAccount
   - B) 将 S3 访问密钥放入 Helm values
   - C) 使用 eksctl --role-only；Helm 创建匹配的带注释 ServiceAccount
   - D) 授予所有节点存储桶策略并禁用身份验证

<details>
<summary>查看答案</summary>

**答案：C**

角色信任策略必须与确切的集群 OIDC 提供商、受众（audience）和命名空间/服务账户主体（subject）相匹配。当其平台/SDK 前提条件满足时，Pod Identity 也是一种选择。

</details>

---

7. 哪个查询可筛选 JSON 字段并排除解析失败？

   - A) `{app="api"} | json | level="error" | __error__=""`
   - B) `{app="api"} | json | where level="error"`
   - C) `{app="api"} | json | select level="error"`
   - D) `{app="api"} | json | filter level="error"`

<details>
<summary>查看答案</summary>

**答案：A**

LogQL 在解析后使用标签筛选阶段。对于通过 unwrap 提取的数值指标，请将错误过滤器置于 unwrap 之后，以同时排除转换错误。

</details>

---

8. Compactor 在此 TSDB 部署中的作用是什么？

   - A) 对网关用户进行身份验证
   - B) 接收所有客户端推送请求
   - C) 保证所有日志会在摄取后恰好 31 天过期
   - D) 启用保留策略时合并整理索引文件，并异步删除已标记的数据块

<details>
<summary>查看答案</summary>

**答案：D**

它并非通用的小日志数据块合并器。保留策略需要兼容的数据模式/索引周期、已启用的处理、用于删除操作的存储以及持久化的标记状态；31 天只是一个示例策略。

</details>

---

9. 收到摄取 429 响应后，首先应做什么？

   - A) 在未测量容量的情况下提高所有限制
   - B) 区分租户字节速率/突发额度、每个流的速率和活动流数量限制，然后检查容量/客户端重试
   - C) 仅增加查询超时
   - D) 永久禁用所有限制

<details>
<summary>查看答案</summary>

**答案：B**

摄取速率和突发限制位于 limits_config 下。提高限制可能会使后端过载，重试需要退避机制以及有界的丢失/缓冲策略。

</details>

---

10. 哪项说法正确描述了 chunk_idle_period 和 /flush？

   - A) 两者都是只读状态端点
   - B) chunk_idle_period 是日志保留期
   - C) chunk_idle_period 控制空闲刷写；POST /flush 会主动触发刷写
   - D) 降低 chunk_idle_period 总是会降低总成本

<details>
<summary>查看答案</summary>

**答案：C**

更短的空闲时间可能产生更多小数据块和对象请求。刷写操作不是健康检查，就绪状态也不能证明端到端持久性。

</details>
