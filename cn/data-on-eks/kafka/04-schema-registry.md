# 第 4 部分：Schema Registry

> **支持的版本**：Karapace 4.x、Apicurio Registry 3.x、Confluent Schema Registry（兼容 API）\
> **最后更新**：July 9, 2026

## 为什么需要 Schema Registry

Kafka 本身会把每条消息都视为不透明的字节数组。它并不关心生产者写入这个数组的格式是什么。问题在于，生产者和消费者通常是独立的应用，由不同团队负责，并按不同节奏部署。只要生产者添加了一个字段或更改了一个类型，任何不了解该变更的消费者要么无法反序列化消息，要么读取到错误的值。

### 无 Schema JSON 的问题

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

像这样的原始 JSON payload 对人类可读，但也带来实际成本：

* **没有强制执行的契约**：没有任何机制阻止生产者悄悄把 `amount` 变成字符串。
* **只能在运行时验证**：缺失字段或类型不匹配，只有在消费者尝试解析 payload 时才会暴露。
* **Payload 大小**：字段名会在每条消息中重复出现，这比二进制格式更大，在高吞吐场景下会变成真实的网络/存储成本。
* **没有版本历史**：无法回答“这个 topic 的 schema 第 3 版是什么样的？”

### Schema Registry 解决了什么

Schema Registry 是一个独立服务，用于集中存储结构化格式（如 Avro、Protobuf 和 JSON Schema）的 schema 并对其进行版本管理，同时在版本之间强制执行兼容性规则。流程大致如下：

1. 在发送消息之前，生产者向 registry 注册（或查找）它的 schema。
2. Registry 返回一个 schema ID，生产者只把该 ID 前置到 payload 中（通常是 5 字节的 magic-byte + ID header），而不是附带完整 schema，然后进行序列化。
3. 消费者读取消息中嵌入的 schema ID，从 registry 获取匹配的 schema，并据此反序列化。
4. 当注册新的 schema 版本时，registry 会根据兼容性规则进行检查；如果违反规则，会直接拒绝注册。

这让生产者和消费者可以独立演进，**无需知道彼此的部署计划**。这也意味着 wire payload 只携带 schema ID，因此 Avro/Protobuf 的二进制编码会比 JSON 小得多。

## 主要实现对比

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **供应商** | Aiven | Red Hat | Confluent |
| **许可证** | Apache License 2.0 | Apache License 2.0 | Confluent Community License（自 2018 年以来并非完全开源） |
| **支持的格式** | Avro、JSON Schema | Avro、Protobuf、JSON Schema、OpenAPI、AsyncAPI、GraphQL、Kafka Connect schemas 等 | Avro、Protobuf、JSON Schema |
| **API 兼容性** | 兼容 Confluent REST API | Confluent 兼容模式（`ccompat`） | 原始 API（事实标准） |
| **存储后端** | Kafka topic | Kafka topic 或 SQL（例如 PostgreSQL） | Kafka topic |
| **捆绑的 REST Proxy** | 是（Karapace REST Proxy） | 否（仅 registry） | 独立的商业 REST Proxy |
| **商业支持条款** | 通过 Aiven 托管服务，或社区支持 | 通过 Red Hat 订阅 | 在一定规模下需要 Confluent Platform 授权 |
| **对 EKS/Strimzi 的适配** | 强 — 纯开源、轻量 | 强 — 多格式、多后端 | 需要进行许可证审查 |

**对于自管理的 EKS + Strimzi 栈，我们推荐 Karapace 或 Apicurio Registry。** 两者都以 Apache-2.0 许可证发布，对再分发或修改没有限制。相比之下，Confluent Schema Registry 的 Confluent Community License 明确禁止将其作为竞争性的托管服务提供 — 它自 2018 年以来就不是完全开源的。`kafka-avro-serializer` 等客户端库仍由 Confluent 发布，但由于 REST API 兼容，通常只需把 `schema.registry.url` 指向 Karapace 或 Apicurio，就可以无需修改代码而正常工作。

## 序列化格式

### Avro

Avro 使用 JSON 定义 schema，并把数据序列化为紧凑的二进制格式。它是 Kafka 生态系统中最广泛使用的格式，最突出的特性是 **schema resolution**：**writer schema**（写入数据时使用）和 **reader schema**（读回数据时使用）不必完全匹配 — Avro 会根据明确定义的规则解析差异。

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    { "name": "orderId", "type": "string" },
    { "name": "customerId", "type": "string" },
    { "name": "amount", "type": "double" },
    { "name": "currency", "type": "string", "default": "USD" },
    { "name": "createdAt", "type": "long", "logicalType": "timestamp-millis" }
  ]
}
```

### Protobuf

Protobuf schema 定义在 `.proto` 文件中，并通过 `protoc` 编译，为每种目标语言生成代码。和 Avro 一样，它生成紧凑的二进制编码，但它会分配显式的字段编号，并拥有更严格的类型系统，因此通常能在不同语言中生成质量更高的代码。Protobuf 在 Kafka 生态系统中的采用率一直在稳步增长。

```protobuf
syntax = "proto3";

package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  string currency = 4;
  int64 created_at = 5;
}
```

### JSON Schema

JSON Schema 为 JSON payload 本身定义验证规则。它对人类可读，也易于调试，但由于字段名会在每条消息中重复出现，payload 最终会比 Avro 或 Protobuf 大得多。它适合需要 schema 验证、但对吞吐量或存储成本不那么敏感的工作负载。

### 三种格式对比

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema 定义 | JSON | `.proto` IDL | JSON Schema |
| Payload 大小 | 小 | 小 | 大 |
| 人类可读性 | 仅 schema | 仅 schema | Payload 也可读 |
| 跨语言代码生成 | 好 | 优秀 | 好 |
| Kafka 生态系统采用度 | 非常高 | 高（持续增长） | 中等 |
| Schema 演进规则 | Writer/reader resolution | 基于字段编号 | JSON Schema 验证规则 |

## 兼容性策略

当注册新的 schema 版本时，registry 会根据配置的兼容模式，将其与上一个版本进行检查。正确理解这四种模式很重要 — 这是 schema 管理中最常被混淆的概念。

| Mode | 含义 | 部署顺序 |
| --- | --- | --- |
| **BACKWARD** | 使用**新** schema 的 reader 必须能够读取用**旧** schema 写入的数据 | 先升级**消费者** |
| **FORWARD** | 使用**旧** schema 的 reader 必须能够读取用**新** schema 写入的数据 | 先升级**生产者** |
| **FULL** | 同时满足 BACKWARD 和 FORWARD | 任一顺序都安全 |
| **NONE** | 不进行兼容性检查 | 需要手动协调 |

人们最常弄反的是：

* **BACKWARD** 表示“新 schema（作为 reader）可以读取旧数据”。在实践中，这意味着你可以安全地**先部署使用新 schema 的消费者** — 即使生产者仍在使用旧 schema 写入，升级后的消费者也能正常读取。
* **FORWARD** 表示“旧 schema（作为 reader）可以读取新数据”。这意味着你可以安全地**先把生产者升级到新 schema** — 仍在运行旧 schema 的消费者会继续正常工作。

### 向后兼容变更示例

向 `Order` schema 添加带默认值的可选字段是 BACKWARD 兼容的：

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

使用新 schema 的消费者读取旧数据（其中缺少该字段）时，只会得到 `default` 值（`null`）— 不会失败。

### 破坏性变更示例

以下是典型的 BACKWARD 兼容性违规：

* **添加没有默认值的必填字段**：添加没有默认值的新 `discount_code` 字段，意味着新 schema reader 期望旧数据上存在这个字段，而旧数据从未包含它，因此会失败。（相反，*移除*字段是 BACKWARD 兼容的，但会破坏 FORWARD — 旧 schema reader 仍会期望新数据上存在这个已被移除的必填字段。）
* **更改字段类型**：将 `amount` 从 `double` 切换为 `string`，意味着现有的二进制编码数据无法再按新类型解码。
* **重命名字段**（没有 alias）：reader 会按新名称查找字段，但旧数据只在旧名称下包含它。

## 在 Strimzi/EKS 上部署

### 部署 Apicurio Registry（Kafka-Topic 存储）

假设 Strimzi 管理的 Kafka 集群已经在运行，你可以在同一 namespace 中将 Apicurio Registry 部署为 Deployment，并使用 Kafka-topic 存储引擎作为后端。

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
      containers:
        - name: apicurio-registry
          image: quay.io/apicurio/apicurio-registry:3.0.6
          ports:
            - containerPort: 8080
          env:
            - name: APICURIO_STORAGE_KIND
              value: "kafkasql"
            - name: APICURIO_KAFKASQL_BOOTSTRAP_SERVERS
              value: "my-kafka-cluster-kafka-bootstrap.kafka.svc:9092"
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
    - port: 8080
      targetPort: 8080
```

Apicurio 还支持使用 SQL 后端（`APICURIO_STORAGE_KIND=sql`）而不是 `kafkasql`，因此如果你已经运行 PostgreSQL/RDS 实例，也可以把 registry 指向那里。相比之下，Karapace 始终把 schema 存储在 Kafka topic（`_schemas`）中，并且不需要单独的后端配置。

### 注册 Schema

Registry 运行后，可以通过其 REST API（使用 Confluent 兼容 endpoint）注册 schema：

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### 客户端配置

Kafka 生产者/消费者应用把它们的 serializer 指向 registry URL：

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

同一个 `KafkaAvroSerializer` 类也可以用于 Karapace — 只需把 `schema.registry.url` 指向 Karapace 的 REST endpoint（默认端口 8081）。当你替换 registry 实现时，应用代码不需要更改，这正是 Confluent 兼容 API 所提供的价值。

## 接下来

本部分介绍了 Schema Registry 如何在生产者和消费者独立演进时，保证它们之间的数据契约安全。第 5 部分将进入 Kafka Connect 和 MirrorMaker — 与外部系统集成，并在集群之间复制数据。

[返回主页面](./)

## 测验

要测试你在本章学到的内容，请尝试完成 [Topic Quiz](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)。
