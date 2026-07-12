# 第 5 部分：Kafka Connect 和 MirrorMaker

> **支持的版本**：Strimzi 0.45+、Kafka 3.9、MirrorMaker 2\
> **最后更新**：July 9, 2026

## Kafka Connect 概览

Kafka Connect 是一个在 Kafka 与外部系统之间移动数据的框架，例如数据库、对象存储、搜索引擎等，而无需编写自定义集成代码。你通过 connector 配置以声明式方式描述数据管道，Connect 会处理其余工作。

Connector 根据数据流向分为两类：

* **Source connectors** 从外部系统将数据拉取到 Kafka 中。Debezium 是典型示例：它读取数据库的 write-ahead log（或 binlog），并将行级变更事件作为 CDC（Change Data Capture）管道流式写入 Kafka。JDBC Source Connector 采用更简单的基于查询的方法，定期轮询表并将结果写入 Kafka。
* **Sink connectors** 将数据从 Kafka 推送到外部系统。S3 Sink Connector 会把 topic 数据以 JSON 或 Parquet 等格式写入 S3，而 Elasticsearch Sink Connector 会为 topic 记录建立索引，用于搜索和分析。

Kafka Connect 支持两种运行模式：

* **Distributed mode**：多个 worker 进程（Pod）组成一个组，并作为单个 Connect cluster 运行。一个 worker 充当 group coordinator，在组内分发 connector 及其 task；如果某个 worker 失效，它的 task 会自动重新平衡到仍存活的 worker 上。Connector 的生命周期（创建、删除、重新配置）通过 REST API 驱动（默认端口为 8083）。这是 Kubernetes 中唯一使用的模式。
* **Standalone mode**：单个进程，使用基于文件的 offset store，面向本地开发。它没有高可用性或水平扩展能力，因此绝不会在 Kubernetes 上使用。

Distributed worker 会将 offset、connector/task 配置以及 task 状态持久化到三个内部 topic（`offset.storage.topic`、`config.storage.topic`、`status.storage.topic`）中。如果这些 topic 丢失，集群上的每个 connector 都会丢失其状态，因此生产部署应始终将它们的 replication factor 设置为至少 3。

## 在 Strimzi 上部署 Kafka Connect

Strimzi 通过 `KafkaConnect` CRD 管理 distributed Connect cluster 本身，并通过 `KafkaConnector` CRD 管理运行在其上的各个 connector 实例。使用 `KafkaConnector` 资源意味着 connector 可以通过 GitOps 部署和进行版本控制，而不是手动调用 REST API。要让 Strimzi reconcile `KafkaConnector` 资源，`KafkaConnect` 资源需要添加 `strimzi.io/use-connector-resources: "true"` annotation。

Connector plugin 不会随基础 Strimzi Kafka Connect 镜像一起捆绑，因此你需要自定义镜像。Strimzi 推荐的模式避免手写 Dockerfile：你在 `KafkaConnect.spec.build` 下声明 plugin artifact（tgz/zip/jar，或 Maven coordinates），然后 Strimzi Operator 构建镜像并将其推送到你指定的 registry，例如 Amazon ECR。

### KafkaConnect build spec

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 3.9.0
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-cluster-offsets
    config.storage.topic: connect-cluster-configs
    status.storage.topic: connect-cluster-status
    offset.storage.replication.factor: 3
    config.storage.replication.factor: 3
    status.storage.replication.factor: 3
    key.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter: org.apache.kafka.connect.json.JsonConverter
  build:
    output:
      type: docker
      image: <account-id>.dkr.ecr.<region>.amazonaws.com/connect-cluster:latest
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.7.3.Final/debezium-connector-postgres-2.7.3.Final-plugin.tar.gz
      - name: aiven-s3-sink
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.0/s3-sink-connector-for-apache-kafka-3.4.0.zip
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

每当 `spec.build` 发生变化（添加 plugin、升级版本等）时，Operator 都会自动重新构建镜像并滚动更新 Deployment。`pushSecret` 引用的 Secret 需要包含 registry 凭证（`docker-registry` 类型 Secret），ECR push 才能成功；如果需要，你也可以通过 IRSA 授予该访问权限。

### KafkaConnector — Debezium PostgreSQL source 示例

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

### KafkaConnector — S3 sink 示例

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.S3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: orders-data-lake
    aws.s3.region: us-east-1
    format.output.type: jsonl
    file.compression.type: gzip
    flush.size: 10000
    rotate.schedule.interval.ms: 300000
```

`kubectl get kafkaconnector -n kafka` 会显示每个 connector 的状态；`Ready: True` condition 表示其 task 已分配给 worker 并正在运行。

## MirrorMaker 2 架构

MirrorMaker 2（MM2）是一个基于 Kafka Connect 框架构建的 topic 级、cluster-to-cluster 复制工具。它不只是复制消息：它会保留源 cluster 的 partitioning，并转换 consumer group offset，这正是灾难恢复期间实现干净的 consumer failover 的关键。在内部，MM2 由三个 connector 组成：

* **MirrorSourceConnector**：执行实际的消息复制，并同步 topic 配置和 ACL。
* **MirrorCheckpointConnector**：定期将源 cluster 的 consumer group offset 转换为目标 cluster 上等价的 offset，并记录到 checkpoint topic 中。这种 offset 转换让故障转移到 DR cluster 的 consumer 能够知道“它已经处理到哪里”。
* **MirrorHeartbeatConnector**：发送定期 heartbeat 消息，证明源 cluster 仍然存活且复制管道正在正常运行，用于检测 replication lag 或完全断连。

MM2 不会在目标 cluster 上逐字复用源 topic 的名称。默认的 `DefaultReplicationPolicy` 会将远程 topic 命名为 `<source-cluster-alias>.<topic>`。例如，从别名为 `us-east-1` 的 cluster 复制 `orders` topic，会在目标上生成名为 `us-east-1.orders` 的远程 topic。这个命名约定让 consumer 仅凭 topic 名称就能区分本地产生的消息和镜像过来的消息，同时它也是在双向设置中防止无限复制循环的机制。

## 灾难恢复模式

### Active-Passive

这是最常见的模式：复制单向运行，从主区域 cluster 到 DR 区域 cluster。在正常运行时，应用只与主 cluster 通信，而 DR cluster 处于空闲状态，持续累积复制过来的数据。当区域故障发生时，你可以使用 MirrorCheckpointConnector 记录的 offset translation 将 consumer group 移动到 DR cluster，并从最近可用的 checkpoint 恢复消费。这并不是完美的 exactly-once 切换——取决于 checkpoint 相对于故障发生的具体时间，少量消息可能会被重新处理；并且由于 MM2 复制是异步的，任何在故障时尚未复制到 DR cluster 的消息都会丢失（RPO 受 replication lag 限制，而不是零）——但关键收益是能够快速恢复，并将数据丢失最小化到该 lag 窗口。

### Active-Active

两个区域都承载流量，并且每个 cluster 都双向复制到另一个 cluster。这会引入一个真实风险：从 A → B 镜像的 topic（如 `A.orders`）可能又被从 B → A 镜像回来，从而无限循环，除非显式阻止。Strimzi/MM2 通过 `replication.policy.class` 中设置的命名策略（默认的 `DefaultReplicationPolicy`，或者如果你希望远程 topic 保持原始名称则使用 `IdentityReplicationPolicy`）来防护这种情况——已经带有远程 cluster 前缀（如 `A.orders`）的 topic 会被排除，不再继续镜像。将 `topicsPattern` 缩小到实际需要跨区域复制的 topic，可作为防止意外复制循环的第二层保护。

### KafkaMirrorMaker2 CR 示例

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
      tls:
        trustedCertificates:
          - secretName: primary-cluster-ca-cert
            certificate: ca.crt
      authentication:
        type: tls
        certificateAndKey:
          secretName: mm2-user
          certificate: user.crt
          key: user.key
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

`connectCluster: dr-region` 告诉 MM2 worker Pod 应该使用哪个 cluster（这里是 DR 区域）来存储 Connect 自身的内部 topic。启用 `sync.group.offsets.enabled: "true"` 会让 MirrorCheckpointConnector 定期将其转换后的 offset 写入 DR cluster 的 `__consumer_offsets`，这样故障转移后的 consumer 就可以先不手动提交 offset，而直接恢复消费。

## 跨区域复制注意事项

* **网络成本和延迟**：跨区域（甚至跨 AZ）复制会产生数据传输成本和往返延迟。常见做法是在目标区域运行 MM2 worker，从源 cluster 拉取数据。调优 batch size（`producer.override.batch.size`）和压缩（`producer.override.compression.type: zstd`）可以减少实际传输的数据量，从而直接降低跨区域数据传输成本。
* **`sync.topic.acls.enabled`**：控制是否也将源 cluster 的 topic ACL 同步到目标 cluster。启用它意味着你不必维护两套访问控制策略，但如果两个 cluster 的安全态势不同——例如 DR cluster 要求比主 cluster 更严格的访问控制——那么禁用它并在两侧独立管理 ACL 可能更安全。
* **监控 replication lag**：MM2 暴露自身的复制健康指标。`replication-latency-ms` 报告消息从在源端产生到完全复制到目标端所经过的时间，而 checkpoint connector 的 lag 相关指标显示 offset translation 的新鲜程度。将这些指标采集到 Prometheus 中，并基于 SLA（例如“replication lag 小于 5 分钟”）设置告警，可以让你持续验证 DR cluster 是否实际处于可故障转移的状态。

## 下一步

在使用 Kafka Connect 和 MirrorMaker 2 完成数据移动与灾难恢复之后，下一步是了解这个工作负载如何与完全托管的 Amazon MSK 服务集成，或两者如何比较。这将在[第 6 部分：MSK 集成](./06-msk-integration.md)中介绍。

[返回主页](./)

## 测验

要测试你在本章学到的内容，请尝试[Topic 测验](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)。
