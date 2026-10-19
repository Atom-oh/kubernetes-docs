# 第 5 部分：Kafka Connect 和 MirrorMaker

> **审核基线**：Strimzi 1.3.0、Kafka 4.3.1、Debezium PostgreSQL 3.6.3.Final、Aiven S3 sink 3.4.3\
> **最后审核日期**：2026 年 10 月 16 日

## Connect 工作器和连接器

Kafka Connect 运行插件，在 Kafka 和外部系统之间移动数据。
只有在已有合适插件，并且数据库/存储权限、格式和网络前提均已满足时，
仅配置才足够。

| 方向 | 示例 | 重要区别 |
| --- | --- | --- |
| 源：外部系统 → Kafka | Debezium PostgreSQL CDC | 初始快照和逻辑 WAL 流式传输不同于 JDBC 轮询 |
| Sink：Kafka → 外部系统 | Aiven S3 sink | 支持的格式和交付行为取决于具体插件 |

在分布式模式下，**Kafka broker** 协调工作器组；当选的工作器 leader 负责计算分配方案。工作器故障会触发重新分配，这可能需要时间并导致重放。连接器任务故障不等同于工作器故障；请检查故障并配置重启行为。

Standalone Connect 可以在容器或 Kubernetes 上运行，但没有分布式工作器故障转移。Strimzi 的 `KafkaConnect` 管理分布式模式。三个工作器不会让单任务 PostgreSQL 连接器运行三个任务。

分布式 Connect 使用压缩的 config、source-offset 和 status 主题。config 主题需要**一个分区**。为每个 Connect 部署指定单独的 group ID 和主题名称。这里以 RF=3 为基准，因为有三个 broker；这不是适用于 broker 数量更少集群的通用最低值。复制不是备份。Sink consumer offsets 通常位于 Kafka consumer groups 中，而非 source-offset 存储主题中。

## Strimzi v1 不只是更改 apiVersion

Strimzi 1.3.0 提供 `kafka.strimzi.io/v1` API。升级前请按照该版本的迁移流程转换旧资源；不要只是将 `v1beta2` 改名。

| 资源 | 当前 v1 字段 |
| --- | --- |
| KafkaConnect 工作器组 | `spec.groupId` |
| KafkaConnect 内部主题名称 | `spec.configStorageTopic`、`spec.offsetStorageTopic`、`spec.statusStorageTopic` |
| KafkaMirrorMaker2 目标和工作器存储 | `spec.target`，并具有自己的 `groupId` 和三个主题名称字段 |
| KafkaMirrorMaker2 源连接 | `spec.mirrors[].source` |

旧版 MM2 的 `connectCluster`、`clusters`、`sourceCluster`、`targetCluster` 和
`heartbeatConnector` 字段不在此 v1 schema 中。Apache MM2 包含 heartbeat connector 实现，但这并不意味着它是可配置的 `KafkaMirrorMaker2` v1 字段。

## 准备 Connect 示例

使用[第 2 部分](./02-strimzi-operator.md)中的三 broker `my-cluster`，其启用了 TLS/SCRAM 和 Topic/User Operators。部署前请替换示例中的 ECR 账户/仓库以及 DB/S3 名称。准备以下额外依赖：

- `debezium-db-credentials`：包含 `password` 键的 Kubernetes Secret。
- `rds-ca`：包含 `ca.crt` 的 Secret，其中存放受信任的 PostgreSQL/RDS CA 证书链。
- 一个现有 ECR 仓库、一个最新的 `kubernetes.io/dockerconfigjson` 类型 push Secret（名为 `ecr-registry-credentials`），以及节点的镜像拉取权限。
- 为 **Connect Pod** 配置 AWS 工作负载身份，并将权限限制在目标 S3 bucket/prefix 范围内。配置 Pod Identity 或 IRSA，并验证插件实际使用的凭证链。构建推送身份和运行时 S3 身份是分开的。

ECR 授权令牌会在 12 小时后过期。请在构建前维护/刷新 push Secret。仅分配 IRSA 角色并不能确保所选镜像构建器能够登录 ECR。Strimzi 1.3 使用 Buildah 构建 Connect 镜像；请检查实际节点上的构建 Pod 要求。

将以下内容保存为 `create-topics.py`，运行该脚本，然后应用 `connect-topics.json`。
七天的数据保留期是实验环境中的选择；依赖此管道前，请根据故障和恢复要求设定保留期。

```python
import json
from pathlib import Path

topics = [
    ("connect-cluster-configs", 1, "compact"),
    ("connect-cluster-offsets", 3, "compact"),
    ("connect-cluster-status", 3, "compact"),
    ("orders-db.public.orders", 3, "delete"),
    ("orders-db.public.order_items", 3, "delete"),
]
items = []
for name, partitions, cleanup in topics:
    config = {"cleanup.policy": cleanup, "min.insync.replicas": 2}
    if cleanup == "delete":
        config["retention.ms"] = 604800000
    items.append({
        "apiVersion": "kafka.strimzi.io/v1", "kind": "KafkaTopic",
        "metadata": {"name": name, "namespace": "kafka",
                     "labels": {"strimzi.io/cluster": "my-cluster"}},
        "spec": {"partitions": partitions, "replicas": 3, "config": config},
    })
Path("connect-topics.json").write_text(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
```

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: connect-cluster
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: connect-cluster-
          patternType: prefix
        operations: [Read, Write, Create, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: orders-db.
          patternType: prefix
        operations: [Read, Write, Describe]
      - resource:
          type: group
          name: connect-cluster
          patternType: literal
        operations: [Read]
      - resource:
          type: group
          name: connect-orders-s3-sink
          patternType: literal
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

将用户资源保存为 `connect-user.yaml`。创建权限仅限于 Connect 内部主题前缀；五个主题由 Topic Operator 使用显式设置预先创建。自动创建源数据主题已禁用。新增表/主题需要进行显式的匹配更新。

## 构建并部署 Connect

保存为 `connect.yaml`。两个下载的插件构件均提供 SHA-512 校验和。
`spec.build` 是一种受支持的选项；预构建且经过测试的镜像或受支持的插件镜像卷也是其他选项。构建成功并不能证明 DB/S3 可访问。

目录配置提供程序会从允许的路径读取挂载的 Secret；它不需要读取 Kubernetes API Secret 的 RBAC 权限。此方式取代了不完整的 `${secrets:...}` 示例，那个示例既没有配置提供程序，也没有访问权限。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnect
metadata:
  name: connect-cluster
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 4.3.1
  replicas: 3
  bootstrapServers: my-cluster-kafka-bootstrap.kafka.svc:9093
  groupId: connect-cluster
  configStorageTopic: connect-cluster-configs
  offsetStorageTopic: connect-cluster-offsets
  statusStorageTopic: connect-cluster-status
  tls:
    trustedCertificates:
      - secretName: my-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-cluster
    passwordSecret:
      secretName: connect-cluster
      password: password
  config:
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    offset.flush.interval.ms: 60000
    topic.creation.enable: false
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    config.providers: dir
    config.providers.dir.class: org.apache.kafka.common.config.provider.DirectoryConfigProvider
    config.providers.dir.param.allowed.paths: /mnt/debezium
  template:
    pod:
      volumes:
        - name: debezium-credentials
          secret:
            secretName: debezium-db-credentials
        - name: rds-ca
          secret:
            secretName: rds-ca
    connectContainer:
      volumeMounts:
        - name: debezium-credentials
          mountPath: /mnt/debezium
          readOnly: true
        - name: rds-ca
          mountPath: /mnt/rds-ca
          readOnly: true
  build:
    output:
      type: docker
      image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/connect-cluster:kafka4.3.1-deb3.6.3-s3-3.4.3
      pushSecret: ecr-registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo.maven.apache.org/maven2/io/debezium/debezium-connector-postgres/3.6.3.Final/debezium-connector-postgres-3.6.3.Final-plugin.tar.gz
            sha512sum: 400495c485a1da532c5d7e2dcc3bbb1b7f7dcdbcdc74c82529309cb89a2c37298319ea45ea00414b3ce750a51ad01084e104725e810c55c1a7c1981baff201a0
      - name: aiven-s3
        artifacts:
          - type: zip
            url: https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/releases/download/v3.4.3/s3-sink-connector-for-apache-kafka-3.4.3.zip
            sha512sum: d355c7d41713dab83384a51e28b6670f63775a0aa394eb0d9e99172d862f53d9e42c54534369cdcfefadfeb4f50e7ffac2029c65dd878f0def3db33058627758
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 2Gi
```

```bash
python3 create-topics.py
kubectl apply -f connect-topics.json -f connect-user.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s kafkauser/connect-cluster
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/connect-cluster-configs kafkatopic/connect-cluster-offsets \
  kafkatopic/connect-cluster-status kafkatopic/orders-db.public.orders \
  kafkatopic/orders-db.public.order_items
kubectl apply -f connect.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=900s kafkaconnect/connect-cluster
```

设置 `strimzi.io/use-connector-resources: "true"` 后，应通过 CR 管理连接器变更；直接进行 REST 修改可能会被协调过程覆盖。限制对 Connect REST API 的访问以及 Kubernetes 更新权限。此工作器部署中的所有插件共用其挂载的 Secret 和工作负载身份；不同信任域应隔离在不同的 Connect 部署中。

## PostgreSQL CDC 源

应用 `source.yaml` 前，请启用 PostgreSQL 逻辑复制，并配置所需的复制槽/WAL sender、复制用户和表权限。对于 RDS PostgreSQL，启用逻辑复制参数可能需要重启。请按照实际引擎版本的流程操作。监控保留的 WAL：停滞的复制槽可能会占满存储。不要将删除复制槽作为常规重启步骤。

有权限的表所有者在 `orders` 数据库中创建 publication：

```sql
CREATE PUBLICATION debezium_orders_pub
FOR TABLE public.orders, public.order_items;
```

请确保更新/删除事件所需的表具有合适的主键/replica identity。连接器会执行初始快照，然后流式传输 WAL。PostgreSQL 连接器使用一个任务；`tasksMax` 是最大值，不保证并行度。

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

挂载的密码不会显示在清单中。请测试凭证轮换以及重启/重新配置行为，不要假定现有 DB 连接会立即采用更改后的 Secret。

## Aiven S3 sink

保存为 `sink.yaml`。实际的 3.4.3 连接器类是
`io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector`。
旧示例中的类 `io.aiven.kafka.connect.s3.S3SinkConnector` 不在该构件中。`flush.size` 和 `rotate.schedule.interval.ms` 也不是它的配置键；不得从其他厂商的 S3 连接器复制这些配置。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaConnector
metadata:
  name: orders-s3-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: connect-cluster
spec:
  class: io.aiven.kafka.connect.s3.AivenKafkaConnectS3SinkConnector
  tasksMax: 3
  config:
    topics: orders-db.public.orders
    aws.s3.bucket.name: REPLACE-WITH-YOUR-BUCKET
    aws.s3.region: ap-northeast-2
    key.converter: org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable: true
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: true
    format.output.type: jsonl
    format.output.fields: key,value,offset,timestamp
    file.compression.type: gzip
    file.max.records: 10000
```

此配置存储的是 **CDC 事件信封**，包括操作和 before/after 数据，而不是自动物化的当前状态表。源和 sink 使用启用了 schema 信封的 JSON converter。转换器设置应与实际 Kafka 记录保持一致。`file.max.records` 控制记录分组，而工作器的 `offset.flush.interval.ms` 会影响定期刷新；这并不保证每个对象都会在固定期限内到达。

未提供显式凭证选项时，将使用 AWS 默认凭证链。仅为目标位置以及任何所需的 KMS key 授予插件所需的对象/分段上传操作权限。在将归档视为恢复来源之前，请测试正常事件、删除、tombstone、重试和重启重放。S3 对象不会自动提供端到端的 exactly-once 行为。

```bash
kubectl apply -f source.yaml -f sink.yaml
kubectl -n kafka get kafkaconnector orders-db-source orders-s3-sink -o yaml
```

检查当前 generation、conditions、`status.connectorStatus.connector.state` 以及每个任务的 state/trace。还要检查源和目标的实际进度。`Ready=True` 是操作器状态观察结果，并不能证明数据是最新的。

## MirrorMaker 2 和灾难恢复

MM2 在写入新的目标 offsets 时会保留记录字节和分区编号。它不会保留源 offset 编号，也不会自动迁移 schema registry ID、应用事务、外部 sink 状态或所有安全策略。

| 组件 | 职责和限制 |
| --- | --- |
| MirrorSourceConnector | 复制记录并生成 offset-sync 映射；主题/配置/ACL 同步取决于设置 |
| MirrorCheckpointConnector | 转换源 group offsets 并生成 checkpoints；可以更新符合条件的非活动目标组 |
| Apache MirrorHeartbeatConnector | 生成 heartbeat 记录；即使不读取源数据，它的任务也可以生成记录，因此仅有 heartbeat 并不能证明源健康或复制完整 |

主动-被动模式使用单向复制，并需要明确的切换操作手册。
如果源无法恢复，故障发生前未复制的记录可能会丢失。重放的记录可能重复；重放窗口不一定很短。测量复制和 checkpoint 的新鲜度，隔离旧写入方，验证目标权限/schema 可用性，更改应用端点/主题订阅，并测试恢复后的消费位置。MM2 不会执行这些应用层步骤。

在主动-主动模式下，`DefaultReplicationPolicy` 会为远程主题添加前缀，并检测**返回到其来源链中已有别名的循环**。它不会排除所有带前缀的主题：向第三个集群进行多跳复制可能是合理的。`IdentityReplicationPolicy` 会丢失此命名信息，也不提供等效的循环保护。请使用明确的方向性过滤规则和所有权管理；它不是适用于两个写入方的通用冲突解决系统。

## 当前 KafkaMirrorMaker2 v1 示例

此单向模板需要可用的跨集群 DNS/网络访问、三个目标 broker、位于 `kafka` namespace 中列出的源/目标 Secret，以及单独准备的 Kafka ACL。端点字符串是占位符。请在能够访问两个集群的位置运行工作器；`spec.target` 选择的是 Kafka 存储，而不是 Kubernetes 区域。

| 身份 | 需要规划的权限范围 |
| --- | --- |
| 源 | 读取/描述所选主题，描述所选 group offsets |
| 目标 | 连接内部主题和工作器组；写入/创建目标远程主题和 MM2 内部主题；读取 offset 映射/checkpoints；更新所选非活动组的 offsets |

请预先创建具有适当压缩/分区设置的内部主题，或授予所选配置所需的特定创建权限。源和目标凭证可以不同。此示例将 offset-syncs 存储在目标端，并禁用 ACL/配置复制，以便显式管理目标策略。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaMirrorMaker2
metadata:
  name: primary-to-dr
  namespace: kafka
spec:
  version: 4.3.1
  replicas: 3
  target:
    alias: dr-region
    bootstrapServers: dr-kafka-bootstrap.REPLACE.example.com:9093
    groupId: primary-to-dr
    configStorageTopic: primary-to-dr-configs
    offsetStorageTopic: primary-to-dr-offsets
    statusStorageTopic: primary-to-dr-status
    tls:
      trustedCertificates:
        - secretName: dr-cluster-ca-cert
          certificate: ca.crt
    authentication:
      type: scram-sha-512
      username: mm2-target
      passwordSecret:
        secretName: mm2-target
        password: password
    config:
      config.storage.replication.factor: 3
      offset.storage.replication.factor: 3
      status.storage.replication.factor: 3
  mirrors:
    - source:
        alias: us-east-1
        bootstrapServers: primary-kafka-bootstrap.REPLACE.example.com:9093
        tls:
          trustedCertificates:
            - secretName: primary-cluster-ca-cert
              certificate: ca.crt
        authentication:
          type: scram-sha-512
          username: mm2-source
          passwordSecret:
            secretName: mm2-source
            password: password
      sourceConnector:
        tasksMax: 5
        config:
          replication.factor: 3
          offset-syncs.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.topic.acls.enabled: false
          sync.topic.configs.enabled: false
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      checkpointConnector:
        config:
          checkpoints.topic.replication.factor: 3
          offset-syncs.topic.location: target
          sync.group.offsets.enabled: true
          sync.group.offsets.interval.seconds: 60
          emit.checkpoints.interval.seconds: 60
          replication.policy.class: org.apache.kafka.connect.mirror.DefaultReplicationPolicy
      topicsPattern: 'orders[.].*|payments[.].*'
      groupsPattern: 'orders-consumer-.*'
```

该模式匹配 `orders.` 和 `payments.` 前缀；不包括裸名称 `orders`、`payments` 或 `orders-db.public.orders`。请根据实际主题清单进行调整。源连接器和 checkpoint 连接器必须使用一致的 replication policy、分隔符和 offset-syncs 位置。

`sync.group.offsets.enabled=true` 只会使用可转换的 offsets 更新符合条件的**非活动/不存在**的目标组；它不会覆盖正在主动消费的组。consumer 成员关系、权限、映射/checkpoint 是否可用以及已提交的目标位置都会影响结果。切勿仅根据此设置或操作器的 Ready 条件推断故障转移成功。

## 网络和监控

对于运行在目标区域的工作器，源到工作器的 fetch 流量会跨区域传输。压缩工作器的**目标 producer** 不会追溯压缩这些 fetch 流量；源 producer/主题的压缩方式和部署位置很重要。请测量网络两端的流量、CPU 和延迟，不要承诺只调整一个参数就能节省成本。

`replication-latency-ms` 是在目标确认记录时测量的相对于记录时间戳的延迟。时间戳模式、历史重放和时钟偏差都会影响该值。`record-age-ms` 在读取路径上观测。还要监控每个分区的进度、错误、数据新鲜度和 checkpoint 新鲜度；停止或为空的流可能产生过时/缺失的样本。Prometheus 指标名称取决于 exporter 映射，因此 Kafka 指标名称不会自动成为 PromQL 名称。

## 参考资料和验证

这些示例依据已发布的 v1 CRD 和原生连接器配置定义进行检查。本地 MM2 行为检查并不能证明实际的跨区域连接、数据库权限、ECR 构建、S3 交付或成功的灾难恢复切换。

- [Strimzi 1.3.0 CRD：权威资源字段](https://github.com/strimzi/strimzi-kafka-operator/tree/1.3.0/install/cluster-operator)
- [Strimzi 1.3.0 部署指南](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Debezium 3.6 PostgreSQL 连接器](https://debezium.io/documentation/reference/3.6/connectors/postgresql.html)
- [Aiven S3 connector 3.4.3](https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka/blob/v3.4.3/s3-sink-connector/README.md)
- [ECR 授权令牌有效期](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_GetAuthorizationToken.html)
- [Kafka 4.3.1 MirrorSourceConnector](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceConnector.java)
- [Kafka 4.3.1 MirrorCheckpointTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorCheckpointTask.java)
- [Kafka 4.3.1 MirrorHeartbeatTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorHeartbeatTask.java)
- [Kafka 4.3.1 MirrorSourceTask](https://github.com/apache/kafka/blob/4.3.1/connect/mirror/src/main/java/org/apache/kafka/connect/mirror/MirrorSourceTask.java)

## 后续步骤

[第 6 部分：MSK 集成](./06-msk-integration.md)比较托管选项。

[返回主页](./README.md)

## 测验

[主题测验](../../quizzes/data-on-eks/kafka/05-kafka-connect-mirrormaker-quiz.md)
