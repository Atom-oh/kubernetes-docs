# 第 5 部分：Kafka Connect 和 MirrorMaker

> **支持的版本**：Strimzi 0.45+、Kafka 3.9、MirrorMaker 2\
> **最后更新**：July 9, 2026

## Kafka Connect 概述

Kafka Connect 是一个无需编写自定义集成代码，即可在 Kafka 与外部系统（数据库、对象存储、搜索引擎等）之间移动数据的框架。你可以通过 connector 配置以声明式方式描述数据管道，其余工作由 Connect 处理。

根据数据流动方向，connector 分为两类：

* **Source connector** 从外部系统将数据拉取到 Kafka 中。Debezium 是典型示例：它读取数据库的预写日志（或 binlog），并将行级变更事件以 CDC（Change Data Capture）管道的形式流式传输到 Kafka。JDBC Source Connector 采用更简单的基于查询的方法，定期轮询表并将结果写入 Kafka。
* **Sink connector** 将数据从 Kafka 推送到外部系统。S3 Sink Connector 会将 topic 数据以 JSON 或 Parquet 等格式写入 S3，而 Elasticsearch Sink Connector 会为 topic 记录建立索引，用于搜索和分析。

Kafka Connect 支持两种运行模式：

* **Distributed mode**：多个 worker 进程（Pod）组成一个组，并作为单个 Connect cluster 运行。一个 worker 担任组协调器，在组内分配 connector 及其 task；如果某个 worker 失效，其 task 会自动重新平衡到仍存活的 worker。connector 生命周期——创建、删除、重新配置——通过 REST API 驱动（默认端口为 8083）。这是 Kubernetes 中唯一使用的模式。
* **Standalone mode**：单个进程配合基于文件的 offset 存储，适用于本地开发。它不具备高可用性或水平扩展能力，因此绝不会用于 Kubernetes。

Distributed worker 会将 offset、connector/task 配置和 task 状态持久化到三个内部 topic（`offset.storage.topic`、`config.storage.topic`、`status.storage.topic`）中。如果这些 topic 丢失，cluster 中的每个 connector 都会失去状态，因此生产部署应始终将其 replication factor 设置为至少 3。

## 在 Strimzi 上部署 Kafka Connect

Strimzi 通过 `KafkaConnect` CRD 管理 Distributed Connect cluster 本身，并通过 `KafkaConnector` CRD 管理运行在其上的各个 connector 实例。使用 `KafkaConnector` resource 意味着 connector 可以通过 GitOps 部署和进行版本控制，而无需手动调用 REST API。要让 Strimzi 调谐 `KafkaConnector` resource，`KafkaConnect` resource 需要 `strimzi.io/use-connector-resources: "true"` annotation。

connector plugin 不包含在基础 Strimzi Kafka Connect image 中，因此你需要自定义 image。Strimzi 推荐的模式无需手写 Dockerfile：你可以在 `KafkaConnect.spec.build` 下声明 plugin artifact（tgz/zip/jar 或 Maven 坐标），Strimzi Operator 会构建 image 并将其推送到你指定的 registry——例如 Amazon ECR。

### KafkaConnect 构建规范

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

每当 `spec.build` 发生变化——例如添加 plugin、升级版本等——Operator 都会自动重新构建 image 并滚动发布 Deployment。`pushSecret` 引用的 Secret 需要包含 registry 凭证（`docker-registry` 类型的 Secret），ECR 推送才能成功；如果需要，你可以通过 IRSA 授予该访问权限。

### KafkaConnector —— Debezium PostgreSQL source 示例

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

### KafkaConnector —— S3 sink 示例

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

`kubectl get kafkaconnector -n kafka` 会显示各个 connector 的状态；`Ready: True` condition 表示其 task 已分配给 worker 且正在运行。

## MirrorMaker 2 架构

MirrorMaker 2（MM2）是一个构建在 Kafka Connect 框架之上的 topic 级 cluster 到 cluster 的复制工具。它不仅复制消息：还会保留 source cluster 的 partition，并转换 consumer group offset，这使得在灾难恢复期间实现干净的 consumer failover 成为可能。在内部，MM2 由三个 connector 组成：

* **MirrorSourceConnector**：执行实际的消息复制，同时同步 topic 配置和 ACL。
* **MirrorCheckpointConnector**：定期将 source cluster 的 consumer group offset 转换为 target cluster 上对应的 offset，并将其记录在 checkpoint topic 中。这种 offset 转换使 failover 到 DR cluster 的 consumer 能够知道“它已处理到什么位置”。
* **MirrorHeartbeatConnector**：定期发送 heartbeat 消息，以证明 source cluster 存活且复制管道正常运行；这些消息可用于检测复制 lag 或完全断开连接。

MM2 不会在 target cluster 中逐字复用 source topic 的名称。默认的 `DefaultReplicationPolicy` 将远程 topic 命名为 `<source-cluster-alias>.<topic>`。例如，从别名为 `us-east-1` 的 cluster 复制 `orders` topic，会在 target 上生成名为 `us-east-1.orders` 的远程 topic。该命名约定让 consumer 仅通过 topic 名称就能区分本地生成的消息与镜像消息，同时它也是防止双向设置中发生无限复制循环的机制。

## 灾难恢复模式

### Active-Passive

这是最常见的模式：复制单向运行，从主 Region cluster 到 DR Region cluster。正常运行时，应用程序只与主 cluster 通信，而 DR cluster 保持空闲状态并持续累积复制的数据。当发生区域故障时，你可以使用 MirrorCheckpointConnector 记录的 offset 转换，将 consumer group 迁移到 DR cluster，并从最近可用的 checkpoint 恢复消费。这并非完美的 exactly-once 切换——具体取决于 checkpoint 相对于故障的创建时机，少量消息可能会被重新处理；并且由于 MM2 复制是异步的，故障发生时尚未复制到 DR cluster 的任何消息都会丢失（RPO 受复制 lag 限制，并非为零）——但其核心优势是能够快速恢复，并将数据丢失降至该 lag 窗口内。

### Active-Active

两个 Region 都承载流量，且每个 cluster 都向另一个 cluster 进行双向复制。这带来了实际风险：除非明确阻止，否则从 A → B 镜像的 topic（作为 `A.orders`）可能会从 B → A 立刻再次镜像，从而无限循环。Strimzi/MM2 会通过在 `replication.policy.class` 中设置的命名策略来防止这种情况（默认的 `DefaultReplicationPolicy`，或者当你希望远程 topic 保持原始名称时使用 `IdentityReplicationPolicy`）——已带有远程 cluster 前缀（如 `A.orders`）的 topic 会被排除在进一步镜像之外。将 `topicsPattern` 缩小为仅包含实际需要跨 Region 复制的 topic，可提供第二层保护以防止意外的复制循环。

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

`connectCluster: dr-region` 告诉 MM2 worker Pod 应使用哪个 cluster（此处为 DR Region）来存储 Connect 自身的内部 topic。启用 `sync.group.offsets.enabled: "true"` 后，MirrorCheckpointConnector 会定期将其转换后的 offset 写入 DR cluster 的 `__consumer_offsets`，这样发生 failover 的 consumer 无需先手动提交 offset 即可恢复消费。

## 跨 Region 复制注意事项

* **网络成本和延迟**：跨 Region（甚至跨 AZ）复制会产生数据传输成本和往返延迟。通常会在 target Region 中运行 MM2 worker，从 source cluster 拉取数据。调整 batch size（`producer.override.batch.size`）和 compression（`producer.override.compression.type: zstd`）可减少实际传输的数据量，从而直接降低跨 Region 数据传输成本。
* **`sync.topic.acls.enabled`**：控制是否同时将 source cluster 的 topic ACL 同步到 target。启用后无需维护两套访问控制策略；但如果两个 cluster 的安全态势不同——例如 DR cluster 要求比主 cluster 更严格的访问权限——禁用它并在每一端独立管理 ACL 可能更安全。
* **监控复制 lag**：MM2 会公开自身的复制健康度 metric。`replication-latency-ms` 报告消息从在 source 上生成到完全复制到 target 的时间，而 checkpoint connector 的 lag 相关 metric 则显示 offset 转换的实时程度。将这些 metric 抓取到 Prometheus 中，并基于 SLA（例如“复制 lag 低于 5 分钟”）设置告警，可让你持续验证 DR cluster 确实处于可供 failover 的状态。

## 后续步骤

Kafka Connect 和 MirrorMaker 2 为数据移动和灾难恢复就绪后，下一步是了解此工作负载如何与全托管的 Amazon MSK 服务集成，或如何与其进行比较。相关内容请参阅[第 6 部分：MSK 集成](./06-msk-integration.md)。

[返回主页](./README.md)

## 测验

要测试你在本章所学的内容，请尝试[Topic 测验](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)。
