# 第 4 部分：架构注册表

> **审查基线**：Karapace 6.2.4、Apicurio Registry 3.3.3、Strimzi 1.3.0 / Kafka 4.3.1\
> **最后审阅**：October 16, 2026

## 为什么要使用架构注册表？

Kafka 将记录键和值存储为字节。因此，生产者和消费者可能会对值的结构或含义产生分歧。并非每次添加字段都会破坏消费者：结果取决于编码方式、读取方和兼容性规则。

注册表会为架构添加版本，并在注册架构时检查配置的兼容性规则。应用程序必须使用相应的序列化器和验证路径。注册表不会自动检查每条 Kafka 记录，也不会强制执行诸如货币或时间戳含义之类的业务规则。

JSON 同样可以有契约：无论是否使用注册表，都可以使用 JSON Schema、CI 检查和带版本的规范。集中式注册表有助于分发和治理该契约；二进制编码则是另一项选择。在声称能节省载荷大小或存储成本之前，请先比较经过测量和压缩的记录。

### 记录中传输的内容是什么？

采用常见的 Confluent **架构 ID 载荷封装**时，值以一个魔数字节和一个四字节架构 ID 开头：总计五个字节，后面跟着编码后的值。Protobuf 变体还包含消息索引。JSON Schema 序列化器仍会将值编码为 JSON。其他序列化器模式、基于标头的标识符以及 Apicurio 原生编码都需要各自的配置。

序列化器会注册或查找架构，反序列化器则通过架构标识符检索写入方架构。客户端通常会缓存架构，因此不一定每条记录都要发起 HTTP 请求。冷缓存或新架构仍可能需要访问注册表。只要对应的 Kafka 数据、归档和灾难恢复副本仍需保持可读，就应保留 ID 到架构的映射。

## 实现方案比较

| 实现 | 相关架构格式 | API 和存储 |
| --- | --- | --- |
| Karapace 6.2.4 | Avro、JSON Schema、**Protobuf** | 与 Confluent 兼容的 REST API；基于 Kafka 的架构存储；还提供 REST 代理 |
| Apicurio Registry 3.3.3 | Avro、Protobuf、JSON Schema；其他制品类型 | 原生 API，以及 `/apis/ccompat/v7` 和 `/apis/ccompat/v8`；KafkaSQL 和 SQL 存储选项 |
| Confluent Schema Registry | Avro、Protobuf、JSON Schema | Confluent API；自托管部署中使用基于 Kafka 的存储 |

Karapace 和 Apicurio 发布时采用 Apache-2.0 许可证。该许可证包含一些条件，包括保留所需声明；这并不意味着“没有限制”。Confluent 的代码库区分了采用 Community 许可证的服务器模块和采用 Apache-2.0 许可证的客户端/Avro 模块。请检查实际组件许可证及任何支持合同，不要根据集群大小推断商业条款。

API 兼容性很有用，但**只更改 URL 并不构成迁移计划**。请针对保留的记录测试架构 ID、引用、主题命名、身份验证、客户端版本和线上编码。例如，Apicurio 的兼容性 API 并未实现 Confluent 的所有导出器/加密功能；接受可选请求字段并不一定意味着会强制执行其规则。
Apicurio 能够存储的制品类型，并不代表每个 Kafka 序列化器都支持它。Karapace 也需要配置 broker、身份验证和架构主题；基于 Kafka 并不意味着无需配置。

## 序列化格式

### Avro

将以下规范示例保存为 `order.avsc`。Avro 使用名称、默认值、别名和已定义的类型提升规则，将写入方架构与读取方架构进行解析。时间戳的 `logicalType` 属于其**类型对象**，而不是与字段的 `name` 并列。字段属性放错位置时，可能仍能通过解析，却无法声明逻辑时间戳。

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    {
      "name": "orderId",
      "type": "string"
    },
    {
      "name": "customerId",
      "type": "string"
    },
    {
      "name": "amount",
      "type": "double"
    },
    {
      "name": "currency",
      "type": "string",
      "default": "USD"
    },
    {
      "name": "createdAt",
      "type": {
        "type": "long",
        "logicalType": "timestamp-millis"
      }
    }
  ]
}
```

这里的 `amount` 只是一个示例性 double。实际契约必须定义单位、精度和舍入规则；需要精确十进制金额时，应使用合适的整数或十进制表示。

### Protobuf 和 JSON Schema

Protobuf 使用带编号的字段，以及特定于语言的生成代码/运行时 API。请明确指定时间单位；仅有 `int64` 并不能声明逻辑时间戳。不要重复使用已删除的字段编号；应酌情保留已移除的编号和名称。

```protobuf
syntax = "proto3";
package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at_millis = 5;
}
```

JSON Schema 用于验证 JSON。不同注册表对草案版本和兼容性分析的支持各不相同；支持验证并不代表能够针对每个关键字进行完整的演进分析。这些是不同的契约，不能互换编码。

| 格式 | 线上表示 | 演进注意事项 |
| --- | --- | --- |
| Avro | 使用写入方架构解释的二进制数据 | 读取方/写入方解析、默认值、名称和类型提升 |
| Protobuf | 带编号字段的二进制数据 | 保留字段编号和线上类型；检查应用程序语义 |
| JSON Schema | JSON | 接受的实例集合、必需字段、附加属性和草案支持情况 |

## 兼容性和部署顺序

在与 Confluent 兼容的 API 中，可在**主题**级别配置兼容性（或继承全局默认值）。使用默认的 `TopicNameStrategy` 时，主题 `orders` 中的值使用主题 `orders-value`；其他策略可以让多个主题共用一个主题，也可以在同一主题中分离不同的记录类型。

| 模式 | 必需关系 | 典型架构发布顺序 |
| --- | --- | --- |
| BACKWARD | 新读取方可以读取上一版本写入方的数据 | 先部署消费者 |
| FORWARD | 上一版本读取方可以读取新版本写入方的数据 | 先部署生产者 |
| FULL | 两个方向都兼容 | 对于受检查的架构关系，任一顺序均可 |
| NONE | 不进行兼容性检查 | 明确协调并测试 |

非传递模式会与之前的最新版本进行比较。它们的 `_TRANSITIVE` 变体会与所有先前版本进行比较。若要重放更早的保留记录，只检查最新版本可能并不足够。`FULL` 不保证业务语义、应用程序行为或与所有历史版本兼容；`FULL_TRANSITIVE` 扩展的是架构比较范围，并不扩展该保证。

对于 Avro，添加以下字段后，新读取方可以为旧记录提供 `null`：

```json
{"name":"discountCode","type":["null","string"],"default":null}
```

默认值是一条**读取方解析**规则，并不意味着写入方可以省略任意必需字段。

| Avro 更改 | 重要条件 |
| --- | --- |
| 添加一个没有读取方默认值的字段 | 新读取方无法读取缺少该字段的旧记录 |
| 删除字段 | 向后兼容；向前兼容性取决于旧读取方是否有默认值 |
| 将 `double` 更改为 `string` | 不兼容；这不是 Avro 数值类型提升 |
| 将 `int` 更改为 `long` | 新读取方可以接受旧整数值；反向则不同 |
| 重命名字段 | 读取方别名或适用的默认值会影响结果；请测试两个方向 |

除了注册表的兼容性端点，还应使用有代表性的历史数据运行读取方/写入方测试。它们可以捕获不同类型的故障。

## 使用 Strimzi 基线部署 Apicurio

这是一个**私有实验室部署**，不是经过身份验证的公共注册表。
它假定 [第 2 部分](./02-strimzi-operator.md) 中的 `my-cluster` 位于命名空间 `kafka`，有三个 broker、Topic/User Operator，以及位于端口 9093 的 TLS/SCRAM 监听器。
下面的 HTTP API 没有应用程序身份验证。当 CNI 强制执行 NetworkPolicy 时，该 NetworkPolicy 仅允许来自同一命名空间中带有标签的 Pod 访问端口 8080。请限制能够创建或标记这些 Pod 的人员。若要用于共享生产环境，请单独配置 API TLS、身份验证和授权，不要与 Kafka SASL 混为一谈；仅使用内部 Service 并不能提供这些控制。

### 存储主题和 Kafka 身份

保存为 `registry-storage.yaml`。应用程序身份只对三个指定主题和其消费者组前缀进行读写。主题由 Topic Operator 预先创建，因此应用程序不需要创建主题的权限。

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-journal
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: kafkasql-snapshots
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: registry-events
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 1
  replicas: 3
  config:
    cleanup.policy: delete
    retention.ms: -1
    retention.bytes: -1
    min.insync.replicas: 2
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: apicurio-registry
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
          name: kafkasql-journal
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: kafkasql-snapshots
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: topic
          name: registry-events
          patternType: literal
        operations: [Read, Write, Describe, DescribeConfigs]
      - resource:
          type: group
          name: apicurio-registry-
          patternType: prefix
        operations: [Read]
      - resource:
          type: cluster
        operations: [IdempotentWrite]
```

KafkaSQL 3.3.3 会初始化 journal、snapshots 和 events 主题。默认情况下，其 journal 和 snapshot 主题检查要求 `cleanup.policy=delete`、`retention.ms=-1` 和 `retention.bytes=-1`。不要对它们应用通用的 `_schemas` 压缩配置，也不要设置普通的七天事件保留期。这会无限期保留记录，因此要监控磁盘增长，并规划经过测试的备份和清理方案。

KafkaSQL 会根据 journal 和任何可用的 snapshot 重建本地 SQL 状态。snapshots 主题包含的是**快照文件路径**，而不是完整的快照文件。以下实验会禁用定期快照并保留完整 journal；如果 Pod 丢失，就必须重放数据，启动时间也可能很长。持久化/共享快照存储、备份、恢复和 journal 裁剪需要单独设计恢复方案。
组前缀可以配置，但固定的 `group.id` 并不是保留 KafkaSQL 状态的办法：此版本会生成唯一组，以确保启动时进行重放。

### 部署和 Service

保存为 `registry.yaml`。CA 和 JAAS 值来自 Strimzi Secrets。
此处显式设置了主机名验证。资源大小和十分钟的启动等待时间是实验室的初始设置；请测量内存用量和重放时间。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apicurio-registry
  template:
    metadata:
      labels:
        app: apicurio-registry
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: registry
          image: quay.io/apicurio/apicurio-registry:3.3.3
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9000
          env:
            - name: APICURIO_STORAGE_KIND
              value: kafkasql
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: my-cluster-kafka-bootstrap.kafka.svc:9093
            - name: APICURIO_KAFKASQL_TOPIC_AUTO_CREATE
              value: "false"
            - name: APICURIO_KAFKASQL_CONSUMER_GROUP_PREFIX
              value: apicurio-registry-
            - name: APICURIO_KAFKASQL_SNAPSHOT_SCHEDULED_ENABLED
              value: "false"
            - name: APICURIO_KAFKA_COMMON_SECURITY_PROTOCOL
              value: SASL_SSL
            - name: APICURIO_KAFKA_COMMON_SASL_MECHANISM
              value: SCRAM-SHA-512
            - name: APICURIO_KAFKA_COMMON_SASL_JAAS_CONFIG
              valueFrom:
                secretKeyRef:
                  name: apicurio-registry
                  key: sasl.jaas.config
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_TYPE
              value: PKCS12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_LOCATION
              value: /etc/kafka-ca/ca.p12
            - name: APICURIO_KAFKA_COMMON_SSL_TRUSTSTORE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: my-cluster-cluster-ca-cert
                  key: ca.password
            - name: APICURIO_KAFKA_COMMON_SSL_ENDPOINT_IDENTIFICATION_ALGORITHM
              value: HTTPS
          volumeMounts:
            - name: kafka-ca
              mountPath: /etc/kafka-ca
              readOnly: true
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
          startupProbe:
            httpGet:
              path: /health/ready
              port: management
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /health/ready
              port: management
          livenessProbe:
            httpGet:
              path: /health/live
              port: management
      volumes:
        - name: kafka-ca
          secret:
            secretName: my-cluster-cluster-ca-cert
            items:
              - key: ca.p12
                path: ca.p12
---
apiVersion: v1
kind: Service
metadata:
  name: apicurio-registry
  namespace: kafka
spec:
  selector:
    app: apicurio-registry
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apicurio-registry-ingress
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      app: apicurio-registry
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              docs.example.com/registry-client: "true"
      ports:
        - protocol: TCP
          port: 8080
```

```bash
kubectl apply -f registry-storage.yaml
kubectl -n kafka wait --for=condition=Ready --timeout=180s \
  kafkatopic/kafkasql-journal kafkatopic/kafkasql-snapshots kafkatopic/registry-events \
  kafkauser/apicurio-registry
kubectl apply -f registry.yaml
kubectl -n kafka rollout status deployment/apicurio-registry --timeout=600s
kubectl -n kafka port-forward --address=127.0.0.1 service/apicurio-registry 8080:8080
```

端口转发需要 Kubernetes 访问权限，并且会在前台持续运行。更改由 Secret 提供的环境变量后，请重启工作负载。对于 SQL 存储，单独设置 `APICURIO_STORAGE_KIND=sql` 并不能完成 PostgreSQL 配置：需要选择 SQL 类型，并提供专用数据库、TLS、凭据和恢复流程。默认的内存 H2 数据库不是持久化的生产存储。

## 注册与应用程序使用的同一架构

在另一个终端中，将 `order.avsc` 注册到 `orders-value` 下。这避免了旧示例中带命名空间的多字段架构与藏在 curl 字符串中的不同单字段架构不匹配的问题。第一个请求会显式配置主题的兼容性；HTTP 请求失败时，curl 会以非零状态退出。

```bash
# Run from a directory containing the order.avsc above.
# Keep kubectl port-forward running in a separate terminal.
REGISTRY_URL="http://127.0.0.1:8080/apis/ccompat/v7"
python3 - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path("order.avsc").read_text())
Path("register-order.json").write_text(json.dumps({
    "schemaType": "AVRO",
    "schema": json.dumps(schema)
}) + "\n")
PY
curl --fail-with-body --silent --show-error \
  -X PUT "$REGISTRY_URL/config/orders-value" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary '{"compatibility":"BACKWARD_TRANSITIVE"}'
curl --fail-with-body --silent --show-error \
  -X POST "$REGISTRY_URL/subjects/orders-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data-binary @register-order.json
curl --fail-with-body --silent --show-error \
  "$REGISTRY_URL/subjects/orders-value/versions/latest"
```

## 生产者和消费者设置

以下是应用程序的**附加**属性；这些应用程序已经配置了第 2 部分中的 broker 地址、TLS 信任和各自的 Kafka 身份。注册表 HTTP 凭据与 Kafka SASL 凭据相互独立。请在应用程序中加入版本固定且兼容的 Confluent Avro 序列化器依赖；安装 Kafka 或 Strimzi 并不会自动提供该依赖。

生产者：

```properties
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
auto.register.schemas=false
```

消费者：

```properties
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v7
specific.avro.reader=false
```

生产者示例要求先注册匹配的架构。
当 `specific.avro.reader=false` 时，消费者会使用通用 Avro 记录；使用生成的 SpecificRecord 类则需要匹配的代码和读取方设置。默认主题策略假定应用程序的 Kafka 主题为 `orders`。

更换注册表之前，请使用冷缓存消费者测试保留记录、新版本注册、兼容性拒绝、架构引用以及重启/恢复流程。保留原始架构 ID 映射，或执行明确且受支持的数据/标识符迁移。HTTP 健康检查成功并不等同于序列化测试成功。

## 参考资料和验证

本章示例已根据固定版本的发布配置和 Strimzi/Kubernetes 架构进行检查，并通过本地 Avro 读取方/写入方测试。这些检查不能取代部署镜像、连接实际 TLS broker，或测试应用程序所用的确切序列化器版本。

- [Apache Avro 规范](https://avro.apache.org/docs/1.12.0/specification/)
- [Protocol Buffers：更新消息类型](https://protobuf.dev/programming-guides/proto3/#updating)
- [Confluent 兼容性规则](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Confluent 序列化器和线上格式](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html)
- [Karapace 6.2.4](https://github.com/Aiven-Open/karapace/tree/6.2.4)
- [Apicurio Registry 3.3.3](https://github.com/Apicurio/apicurio-registry/tree/3.3.3)
- [Apicurio 兼容性 API 支持矩阵](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/ccompat/rest/README.md)
- [Apicurio KafkaSQL 配置](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/kafkasql/KafkaSqlConfiguration.java)
- [Apicurio 主题配置验证](https://github.com/Apicurio/apicurio-registry/blob/3.3.3/app/src/main/java/io/apicurio/registry/storage/impl/util/KafkaAdminUtil.java)
- [Confluent 组件许可证](https://github.com/confluentinc/schema-registry/blob/master/LICENSE)

## 接下来

[第 5 部分](./05-kafka-connect-mirrormaker.md)将介绍外部集成和跨集群复制。架构存储和 ID 迁移必须与记录复制一并考虑。

[返回主页](./README.md)

## 测验

[主题测验](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)
