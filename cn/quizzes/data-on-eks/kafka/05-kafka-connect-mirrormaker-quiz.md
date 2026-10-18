# Kafka Connect 和 MirrorMaker 测验

回顾本章的 Strimzi v1 配置、实际插件、复制和恢复条件。

## 1. Debezium PostgreSQL 和 S3 sink 分别沿哪个方向移动数据？

<details>
<summary>显示答案</summary>

Debezium 是源连接器，会将快照/WAL 变更发送到 Kafka；S3 接收端连接器（sink）会将 Kafka 记录发送到 S3。请检查每个插件的格式和投递行为。

</details>

## 2. 使用 Aiven S3 sink 归档 Debezium 记录，能否自动重建当前数据库表？

<details>
<summary>显示答案</summary>

不能。示例会归档包含操作以及变更前后数据的 CDC 事件。要物化当前状态，需要处理键、删除/墓碑记录（tombstone）、顺序和重放。

</details>

## 3. 分布式 Connect 组协调器和 worker leader 有何不同？

<details>
<summary>显示答案</summary>

Kafka broker 会协调该组；选出的主工作进程（worker leader）会计算分配方案。工作进程故障可能触发延迟重新分配和重放，这与任务故障不同。

</details>

## 4. 是否无法在 Kubernetes 上运行 standalone Connect？

<details>
<summary>显示答案</summary>

可以运行，但不具备分布式工作进程故障转移能力。Strimzi KafkaConnect 管理分布式模式。增加工作进程不会自动让只使用一个任务的连接器并行化。

</details>

## 5. 当 KafkaConnector CR 管理 connector 时，直接通过 REST 编辑 connector 可能会发生什么？

<details>
<summary>显示答案</summary>

Operator 可能会将连接器协调回 CR 中的期望状态。请使用 CR 作为变更途径，并限制 Kubernetes 更新和 Connect REST 访问。

</details>

## 6. 哪个 annotation 会启用 KafkaConnector 协调？此处使用的 API 版本是什么？

<details>
<summary>显示答案</summary>

`strimzi.io/use-connector-resources: "true"` 和 `kafka.strimzi.io/v1`。v1 迁移包含 groupId 和内部主题名称等字段；仅更改 apiVersion 并不足够。

</details>

## 7. spec.build 中应固定并检查哪些内容？如何处理 ECR 身份验证？

<details>
<summary>显示答案</summary>

指定插件版本、URL、校验和以及输出镜像标签。维护有效的推送 Secret 和镜像拉取权限；ECR 令牌会在 12 小时后过期。运行时 S3 身份与构建推送身份验证是分开的。

</details>

## 8. MM2 offset-sync 映射和 checkpoint 有什么用途？

<details>
<summary>显示答案</summary>

MirrorSourceConnector 会生成源/目标偏移量映射；MirrorCheckpointConnector 使用这些映射来转换源消费组提交的偏移量。不能假定源和目标偏移量相等。

</details>

## 9. DefaultReplicationPolicy 如何命名远程 topic 并检测循环？

<details>
<summary>显示答案</summary>

它使用 `<source-alias>.<topic>`，并检测是否循环回到来源链中已存在的目标别名。它不会排除所有带前缀的主题；向第三个集群进行多跳复制可能是合理的。

</details>

## 10. 除了 MM2 之外，主备故障切换还需要做哪些准备？

<details>
<summary>显示答案</summary>

阻止旧写入方继续写入，测量复制数据与检查点的更新及时性，验证目标权限和数据模式（schema），更改端点/订阅，并验证恢复后的消费位置。如果源无法恢复，未复制的数据可能会丢失；还要测量重复重放情况。

</details>

## 11. Apache MirrorHeartbeatTask 的 heartbeat 能否证明源数据复制正常？

<details>
<summary>显示答案</summary>

不能。该任务可以在不读取源数据的情况下发送心跳。还要检查分区进度、错误和检查点是否及时更新。请区分这个 Apache 类与 Strimzi 1.3 的 v1 CRD 所支持的字段。

</details>

## 12. Connect v1 的内部 topic 字段是什么？它们对分区/保留有什么要求？

<details>
<summary>显示答案</summary>

`spec.configStorageTopic`、`spec.offsetStorageTopic` 和 `spec.statusStorageTopic`。配置主题应采用日志压实（compaction）策略，且分区数为 1。使用 spec.groupId 设置工作进程组；接收端消费组的偏移量则是独立的。

</details>

## 13. sync.topic.acls.enabled=true 是否会原样复制整个源安全策略？

<details>
<summary>显示答案</summary>

不会。Kafka 4.3.1 会处理选定的字面量（literal）主题 ACL，排除 ALLOW WRITE，并将 ALLOW ALL 降级为 READ。它不会迁移所有用户、集群策略或外部 IAM 策略。示例会单独管理目标策略。

</details>

## 14. 解读 replication-latency-ms 和跨区域压缩时，哪些因素很重要？

<details>
<summary>显示答案</summary>

它测量目标确认时间减去记录时间戳，结果会受到时钟偏差、时间戳模式和重放的影响。在目标区域工作进程的目标生产者上启用压缩，无法减少已经跨区域传输的源数据拉取流量。

</details>

## 15. 在 KafkaMirrorMaker2 v1 中，目标和源连接定义在哪里？

<details>
<summary>显示答案</summary>

`spec.target` 和 `spec.mirrors[].source`。目标需要 alias、bootstrapServers、groupId 和三个内部主题名称。不要使用旧的 connectCluster/clusters/heartbeatConnector 结构。

</details>

## 16. 写出本章中的 Debezium PostgreSQL KafkaConnector，并说明其前提条件。

<details>
<summary>显示答案</summary>

```yaml
apiVersion: kafka.strimzi.io/v1
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
    database.hostname: orders-db.REPLACE.ap-northeast-2.rds.amazonaws.com
    database.port: 5432
    database.user: debezium
    database.password: "${dir:/mnt/debezium:password}"
    database.dbname: orders
    database.sslmode: verify-full
    database.sslrootcert: /mnt/rds-ca/ca.crt
    topic.prefix: orders-db
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: debezium_orders_pub
    publication.autocreate.mode: disabled
    table.include.list: 'public[.]orders,public[.]order_items'
    snapshot.mode: initial
```

准备逻辑复制、权限、发布对象（publication）和合适的复制标识（replica identity）。通过获准的 Secret 目录凭据提供器读取密码，并验证数据库 TLS 主机名。它使用一个任务；请监控停滞的复制槽保留的 WAL。

</details>

## 17. 本章 v1 MM2 示例中，组 offset 同步的关键条件是什么？

<details>
<summary>显示答案</summary>

匹配源连接器/检查点连接器的复制策略和 offset-syncs 位置，并启用 `sync.group.offsets.enabled=true`。需要有效的映射/检查点和相应权限，而且目标消费组必须处于非活动状态或不存在。不会覆盖活动消费者。请使用本章 mm2.yaml 中的目标/源结构。

</details>

## 18. IdentityReplicationPolicy 和 topicsPattern 能否让任意双向写入变得安全？

<details>
<summary>显示答案</summary>

不能。Identity 会丢失来源前缀信息，也不具备默认策略中等效的循环检测能力。请按复制方向明确主题归属，并设计过滤器、写入策略和切换方案。主题过滤器不会自动解决数据冲突或重复问题。

</details>

---

[返回学习资料](../../../data-on-eks/kafka/05-kafka-connect-mirrormaker.md) | [下一个测验](./06-msk-integration-quiz.md)
