# Kafka Connect 和 MirrorMaker 测验

本测验用于检验你对 Kafka Connect 的 source/sink connector 模型、distributed mode、Strimzi 的 `KafkaConnect`/`KafkaConnector` CRD，以及 MirrorMaker 2 架构和灾难恢复模式的理解。

## 选择题

1. 像 Debezium 这样的 connector 会读取数据库的 WAL/binlog，并将变更事件流式写入 Kafka，它属于哪种 connector？
   - A) Sink connector
   - B) Source connector
   - C) Filter connector
   - D) Transform connector

<details>

<summary>显示答案</summary>

**答案：B) Source connector**

**说明：**
Source connectors 会从外部系统将数据拉取到 Kafka 中。Debezium 是 CDC（Change Data Capture）source connector 的典型示例：它读取数据库的 write-ahead log（或 binlog），并将行级变更事件流式写入 Kafka。Sink connectors 则相反——它们将数据从 Kafka 推送到 S3 或 Elasticsearch 等外部系统。
</details>

2. S3 Sink Connector 和 Elasticsearch Sink Connector 的共同点是什么？
   - A) 它们从外部系统拉取数据到 Kafka
   - B) 它们将数据从 Kafka topic 推送到外部系统
   - C) 它们在 topic 之间复制数据
   - D) 它们管理 consumer group offsets

<details>

<summary>显示答案</summary>

**答案：B) 它们将数据从 Kafka topic 推送到外部系统**

**说明：**
S3 Sink Connector 和 Elasticsearch Sink Connector 都是 sink connectors，这意味着它们会将 Kafka topic 中积累的数据推送到外部系统。S3 Sink Connector 会以 JSON 或 Parquet 等格式将 topic 数据写入 S3 bucket，而 Elasticsearch Sink Connector 会为搜索和分析对 topic 数据建立索引。
</details>

3. 在 Kafka Connect 的 distributed mode 中，当一个 worker 失效时会发生什么？
   - A) 整个 Connect cluster 停止
   - B) 失效 worker 的任务会自动重新均衡到其他存活的 worker 上
   - C) connector 会自动切换到 standalone mode
   - D) 所有 offset 信息都会被重置

<details>

<summary>显示答案</summary>

**答案：B) 失效 worker 的任务会自动重新均衡到其他存活的 worker 上**

**说明：**
在 distributed mode 中，多个 worker 进程会组成一个 group，作为单个 Connect cluster 运行，并由 group coordinator 将 connectors 和 tasks 分布到各个 workers 上。如果一个 worker 失效，coordinator 会检测到它，并自动将该 worker 的任务重新均衡到其余 workers 上，以保持可用性。这是它与 standalone mode 的关键区别；standalone mode 作为单进程运行，不具备高可用性。
</details>

4. 为什么在 Kubernetes/Strimzi 环境中从不使用 Kafka Connect 的 standalone mode？
   - A) 它不支持 REST API
   - B) 它没有高可用性或水平扩展能力
   - C) 它只支持 source connectors
   - D) 它不支持 TLS

<details>

<summary>显示答案</summary>

**答案：B) 它没有高可用性或水平扩展能力**

**说明：**
Standalone mode 作为单进程运行，并使用基于文件的 offset store，面向本地开发和测试。由于只有一个 worker，如果它失败，就没有其他 worker 可以接管，而且工作负载也无法分布到多个节点上。由于这些限制，Kubernetes/Strimzi 环境始终运行 distributed mode，并由多个 worker Pods 支撑。
</details>

5. 在 Strimzi 中使用 `KafkaConnector` CRD 的主要优势是什么？
   - A) 它允许你通过 GitOps 以声明式方式管理 connectors，而不是直接调用 REST API
   - B) 它会自动为你编写 connector plugin 代码
   - C) 它会将 distributed mode 转换为 standalone mode
   - D) 它消除了对 offset storage topic 的需求

<details>

<summary>显示答案</summary>

**答案：A) 它允许你通过 GitOps 以声明式方式管理 connectors，而不是直接调用 REST API**

**说明：**
使用 `KafkaConnector` CRD 时，你不需要直接调用 Connect REST API 来创建、删除或重新配置 connectors——你在 YAML manifest 中声明期望状态，Strimzi Operator 会将其与实际 connector 状态进行协调。这支持 GitOps 工作流：connector 配置可以在 Git repository 中进行版本控制，并通过 code review/CI pipelines 部署。
</details>

6. 要为 `KafkaConnect` resource 启用 `KafkaConnector` CRD，需要在其上添加什么 annotation？
   - A) `strimzi.io/kraft: enabled`
   - B) `strimzi.io/node-pools: enabled`
   - C) `strimzi.io/use-connector-resources: "true"`
   - D) `strimzi.io/connect-mode: distributed`

<details>

<summary>显示答案</summary>

**答案：C) `strimzi.io/use-connector-resources: "true"`**

**说明：**
在 `KafkaConnect` resource 的 metadata 中添加 `strimzi.io/use-connector-resources: "true"` annotation，会告诉 Strimzi Operator 监视以该 Connect cluster 为目标的 `KafkaConnector` resources，并将它们协调为真实的 connectors。没有这个 annotation，创建 `KafkaConnector` resources 不会产生任何效果。
</details>

7. Strimzi 推荐的通过 `KafkaConnect.spec.build` 构建带有 connector plugins 的自定义 image 的方式有什么特点？
   - A) 你必须手写 Dockerfile
   - B) 你声明 plugin artifact URLs，Operator 会构建 image 并推送到你指定的 registry
   - C) Images 只能推送到 Docker Hub
   - D) 它只适用于 standalone mode

<details>

<summary>显示答案</summary>

**答案：B) 你声明 plugin artifact URLs，Operator 会构建 image 并推送到你指定的 registry**

**说明：**
Strimzi 推荐的模式是以声明式方式填充 `KafkaConnect.spec.build`，其中包含一个 `output`（目标 registry image 和 push secret）以及一个 `plugins` 列表（每个 plugin 指定 tgz/zip/jar artifact URLs 或 Maven coordinates）。不需要 Dockerfile——Strimzi Operator 会自行执行 build，并将生成的 image 推送到 Amazon ECR 等 registry。
</details>

8. 在 MirrorMaker 2 中，哪个 connector 负责将 source cluster 的 consumer group offsets 转换为 target cluster 上的等效 offsets？
   - A) MirrorSourceConnector
   - B) MirrorHeartbeatConnector
   - C) MirrorCheckpointConnector
   - D) MirrorTopicConnector

<details>

<summary>显示答案</summary>

**答案：C) MirrorCheckpointConnector**

**说明：**
MirrorCheckpointConnector 会定期将 source cluster 的 consumer group offsets 转换为 target cluster 上的等效 offsets，并将其记录在 checkpoint topic 中。这种 offset translation 让 consumer group 在故障转移到 DR cluster 并需要恢复消费时，能够知道“它已经处理到哪里”。MirrorSourceConnector 负责实际复制 messages、topics 和 ACLs，而 MirrorHeartbeatConnector 发送 heartbeats 来表明 replication pipeline 仍然存活。
</details>

9. MirrorMaker 2 的默认 `DefaultReplicationPolicy` 对 remote topics 使用什么命名约定？
   - A) `<topic>.<source-cluster-alias>`
   - B) `<source-cluster-alias>.<topic>`
   - C) `mirror-<topic>`
   - D) 原始 topic 名称保持不变

<details>

<summary>显示答案</summary>

**答案：B) `<source-cluster-alias>.<topic>`**

**说明：**
`DefaultReplicationPolicy` 会将 remote topics 命名为 `<source-cluster-alias>.<topic>`。例如，从别名为 `us-east-1` 的 cluster 复制 `orders` topic，会在 target cluster 上生成名为 `us-east-1.orders` 的 remote topic。若要保持原始名称不变，则需要使用 `IdentityReplicationPolicy`，但这会使 active-active 设置中的 loop prevention 更难实现。
</details>

10. active-passive 和 active-active DR 模式的核心区别是什么？
    - A) Active-passive 压缩数据，而 active-active 不压缩
    - B) Active-passive 只进行单向复制，而 active-active 进行双向复制并需要 loop prevention
    - C) Active-active 不使用 MirrorMaker 2
    - D) 只有 active-passive 使用 KafkaConnector CRD

<details>

<summary>显示答案</summary>

**答案：B) Active-passive 只进行单向复制，而 active-active 进行双向复制并需要 loop prevention**

**说明：**
active-passive 模式进行单向复制，从 primary cluster 复制到 DR cluster，而 DR cluster 通常处于空闲状态。active-active 模式在两个 clusters 之间进行双向复制，因此两个 region 都可以服务流量；但这也意味着一个已复制的 topic 可能被镜像回其原始 cluster，从而造成无限循环，除非通过 `replication.policy.class` 和 topic filters 显式防止这种情况。
</details>

## 简答题

11. MirrorMaker 2 中会定期发送 heartbeat messages，以表明 source cluster 存活且 replication pipeline 正常运行的 connector 叫什么？

<details>

<summary>显示答案</summary>

**答案：MirrorHeartbeatConnector**

**说明：**
MirrorHeartbeatConnector 会定期发送 heartbeat messages，表明 source cluster 正常运行且 replication pipeline 未中断。如果这些 heartbeats 在一段时间内停止到达，这种缺失可用作检测 replication lag 或与 source cluster 连接断开的信号。
</details>

12. Strimzi Kafka Connect 的 distributed workers 用于存储 offsets、connector/task configuration 和 task status 的三个 internal topic configuration keys 分别叫什么？（例如，offset.storage.topic）

<details>

<summary>显示答案</summary>

**答案：`offset.storage.topic`, `config.storage.topic`, `status.storage.topic`**

**说明：**
Distributed-mode Connect workers 使用三个 internal topics：`offset.storage.topic` 用于 offsets，`config.storage.topic` 用于 connector/task configuration，`status.storage.topic` 用于 task status。如果这些 topics 丢失，cluster 上的每个 connector 都会丢失其状态，因此生产部署必须将它们的 replication factor 设置为至少 3。
</details>

13. 哪个 configuration key 控制 MirrorMaker 2 是否也将 source cluster 的 topic ACLs 同步到 target cluster？

<details>

<summary>显示答案</summary>

**答案：`sync.topic.acls.enabled`**

**说明：**
将 `sync.topic.acls.enabled` 设置为 `true` 会使 source cluster 的 topic ACLs 也同步到 target cluster，因此不需要维护两套 access control policy。不过，如果两个 clusters 具有不同的 security posture——例如，如果 DR cluster 需要更严格的 access control——则禁用此项并在每一侧独立管理 ACLs 可能更安全。
</details>

14. MirrorMaker 2 暴露的哪个 metric 用于报告从 message 在 source cluster 上产生，到它完全复制到 target 所经过的时间？

<details>

<summary>显示答案</summary>

**答案：`replication-latency-ms`**

**说明：**
`replication-latency-ms` 是 MirrorMaker 2 暴露的核心 metrics 之一，用于报告从 message 在 source cluster 上产生，到它完全复制到 target cluster 所经过的时间。将其抓取到 Prometheus 并基于它设置告警，可以持续验证 replication lag SLA。
</details>

15. 在 Strimzi 中，`KafkaMirrorMaker2` resource 上的哪个 `spec` field 指定 MM2 worker Pods 应使用已配置 clusters 中的哪一个来存储自己的 internal topics（offsets、configuration 等）？

<details>

<summary>显示答案</summary>

**答案：`connectCluster`**

**说明：**
`KafkaMirrorMaker2.spec.connectCluster` 指向 `spec.clusters` 中定义的某个 cluster alias，决定 MM2 worker Pods 使用哪个 cluster 来存储自己的 Kafka Connect internal topics（offset、configuration 和 status storage topics）。这通常设置为 DR 或 target cluster。
</details>

## 动手练习题

16. 编写一个用于 Debezium PostgreSQL source connector 的 `KafkaConnector` resource，它运行在名为 `connect-cluster` 的 `KafkaConnect` cluster 上（该 cluster 已设置 `strimzi.io/use-connector-resources: "true"` annotation）。将其限制为单个 task。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-db-source
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: orders-db.xxxxxxx.us-east-1.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${secrets:kafka/debezium-db-credentials:password}"
    database.dbname: orders
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    table.include.list: public.orders,public.order_items
```

**说明：**
`metadata.labels.strimzi.io/cluster: connect-cluster` label 会告诉 Strimzi Operator 这个 `KafkaConnector` 应运行在哪个 `KafkaConnect` cluster 上。`spec.class` 指定实际的 connector implementation class（Debezium PostgreSQL connector），而 `plugin.name: pgoutput` 指定 PostgreSQL 的 logical replication output plugin。`tasksMax: 1` 反映了 PostgreSQL source connector 只能使用单个 replication slot，因此其工作无法跨多个 tasks 并行化。
</details>

17. 编写一个 `KafkaMirrorMaker2` resource，用于将匹配 `orders.*` 和 `payments.*` 的 topics 从别名为 `us-east-1` 的 cluster 单向复制到别名为 `dr-region` 的 cluster，同时同步 consumer group offsets。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 3.9.0
  replicas: 3
  connectCluster: dr-region
  clusters:
    - alias: us-east-1
      bootstrapServers: primary-kafka-bootstrap.us-east-1.example.com:9093
    - alias: dr-region
      bootstrapServers: dr-kafka-bootstrap.us-west-2.example.com:9093
      config:
        config.storage.replication.factor: 3
        offset.storage.replication.factor: 3
        status.storage.replication.factor: 3
  mirrors:
    - sourceCluster: us-east-1
      targetCluster: dr-region
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          sync.topic.acls.enabled: "true"
      heartbeatConnector:
        config:
          heartbeats.topic.replication.factor: 3
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          sync.group.offsets.enabled: "true"
      topicsPattern: "orders.*|payments.*"
      groupsPattern: "orders-consumer-.*"
```

**说明：**
`mirrors` 列表中的每个条目定义一个复制方向（`sourceCluster` 到 `targetCluster`）。`topicsPattern` 将复制限制为 `orders.*` 和 `payments.*`，并且设置 `checkpointConnector.config.sync.group.offsets.enabled: "true"` 会使转换后的 consumer group offsets 写入 target cluster 的 `__consumer_offsets`。`connectCluster: dr-region` 将 DR region 指定为 MM2 workers 存储其 internal topics 的 cluster。
</details>

18. 请说明你会检查哪两个设置，以防止在 active-active configuration 中某个 topic 被无限循环镜像（A 到 B 到 A 到 B……）。

<details>

<summary>显示答案</summary>

**答案：**
1. `replication.policy.class` — 使用默认的 `DefaultReplicationPolicy` 时，已经带有 remote-cluster prefix（`<alias>.<topic>`）的 topics 会自动排除在进一步 mirroring 之外。
2. `topicsPattern` — 在每个 mirror direction 上收窄 pattern，明确只包含确实需要复制的 topics，可防止意外 topics 被卷入 replication cycle。

**说明：**
`DefaultReplicationPolicy` 的命名约定（`<source-cluster-alias>.<topic>`）本身就是防止 loops 的第一道防线：如果 cluster B 尝试将像 `A.orders` 这样的 topic 镜像回 cluster A，MM2 会识别它是已经带前缀的 remote topic，并且不会重新镜像它。除此之外，为每个 mirror direction 显式收窄 `topicsPattern`，可以降低配置错误或异常 topic 命名模式意外触发 replication loop 的风险。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [下一个测验：MSK Integration](./06-msk-integration-quiz.md)
