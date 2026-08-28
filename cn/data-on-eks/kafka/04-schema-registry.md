# 第 4 部分：Schema Registry

> **支持的版本**：Karapace 4.x、Apicurio Registry 3.x、Confluent Schema Registry（兼容 API）\
> **最后更新**：July 9, 2026

## 为什么需要 Schema Registry

Kafka 本身将每条消息都视为不透明的字节数组。它不关心生产者以何种格式将内容写入该数组。问题在于，生产者和消费者通常是由不同团队负责、按不同计划部署的独立应用程序。一旦生产者添加字段或更改类型，任何不了解该变更的消费者要么无法反序列化消息，要么会读取到损坏的值。

### 无 Schema JSON 的问题

```json
{"orderId": "ORD-1001", "amount": 42.5, "currency": "USD"}
```

像这样的原始 JSON 载荷具有人类可读性，但也带来了实际成本：

* **没有强制执行的契约**：没有任何机制能阻止生产者悄悄地将 `amount` 变为字符串。
* **仅在运行时验证**：只有当消费者尝试解析载荷时，才会暴露缺失字段或类型不匹配的问题。
* **载荷大小**：字段名称会在每条消息中重复出现，相比二进制格式更大，并且在高吞吐量下会产生实际的网络/存储成本。
* **没有版本历史**：无法回答“此 Topic 的 Schema 第 3 版是什么样子？”

### Schema Registry 解决的问题

Schema Registry 是一项独立服务，用于集中存储并对 Avro、Protobuf 和 JSON Schema 等结构化格式的 Schema 进行版本管理，同时在不同版本之间强制执行兼容性规则。其流程大致如下：

1. 在发送消息前，生产者向 Registry 注册（或查询）其 Schema。
2. Registry 返回一个 Schema ID，生产者仅在载荷前添加该 ID（通常是一个 5 字节的 magic-byte + ID 头部）来序列化载荷，而不是附带完整 Schema。
3. 消费者读取消息中嵌入的 Schema ID，从 Registry 获取匹配的 Schema，并据此反序列化。
4. 注册新 Schema 版本时，Registry 会依据兼容性规则进行检查；如果违反规则，会直接拒绝注册。

这使生产者和消费者可以在**不了解彼此部署计划**的情况下独立演进。这也意味着线上的载荷只携带一个 Schema ID，因此 Avro/Protobuf 二进制编码相比 JSON 小得多。

## 主要实现方案对比

| | Karapace | Apicurio Registry | Confluent Schema Registry |
| --- | --- | --- | --- |
| **供应商** | Aiven | Red Hat | Confluent |
| **许可证** | Apache License 2.0 | Apache License 2.0 | Confluent Community License（自 2018 年起不再完全开源） |
| **支持的格式** | Avro、JSON Schema | Avro、Protobuf、JSON Schema、OpenAPI、AsyncAPI、GraphQL、Kafka Connect Schema 等 | Avro、Protobuf、JSON Schema |
| **API 兼容性** | 兼容 Confluent REST API | Confluent 兼容模式（`ccompat`） | 原始 API（事实标准） |
| **存储后端** | Kafka Topic | Kafka Topic 或 SQL（例如 PostgreSQL） | Kafka Topic |
| **内置 REST Proxy** | 是（Karapace REST Proxy） | 否（仅 Registry） | 独立的商业 REST Proxy |
| **商业支持条款** | 通过 Aiven 的托管服务或社区提供 | 通过 Red Hat 订阅提供 | 大规模使用时需要 Confluent Platform 许可证 |
| **与 EKS/Strimzi 的适配性** | 强 — 纯开源、轻量 | 强 — 多格式、多后端 | 需要审查许可证 |

**对于自主管理的 EKS + Strimzi 技术栈，我们建议使用 Karapace 或 Apicurio Registry。** 两者均采用 Apache-2.0 许可证发布，对再分发或修改没有限制。相较之下，Confluent Schema Registry 的 Confluent Community License 明确禁止将其作为竞争性的托管服务提供——自 2018 年起它已不再完全开源。`kafka-avro-serializer` 等客户端库仍由 Confluent 发布，但由于 REST API 兼容，通常只需将 `schema.registry.url` 指向 Karapace 或 Apicurio，无需修改代码。

## 序列化格式

### Avro

Avro 使用 JSON 定义其 Schema，并将数据序列化为紧凑的二进制格式。它是 Kafka 生态系统中使用最广泛的格式，其突出特性是**Schema 解析**：**写入者 Schema**（数据写入时所用）和**读取者 Schema**（数据读取时所用）不必完全匹配——Avro 会根据定义明确的规则解析其中的差异。

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

Protobuf Schema 在 `.proto` 文件中定义，并使用 `protoc` 编译，为每种目标语言生成代码。与 Avro 一样，它生成紧凑的二进制编码，但会分配显式字段编号，并且拥有更严格的类型系统，因此通常能在各种语言中生成质量更高的代码。Protobuf 在 Kafka 生态系统中的采用率一直在稳步增长。

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

JSON Schema 为 JSON 载荷本身定义验证规则。它具有人类可读性且易于调试，但由于字段名称会在每条消息中重复出现，载荷最终会比 Avro 或 Protobuf 大得多。它适合需要 Schema 验证、但对吞吐量或存储成本不太敏感的工作负载。

### 三种格式对比

| | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Schema 定义 | JSON | `.proto` IDL | JSON Schema |
| 载荷大小 | 小 | 小 | 大 |
| 人类可读 | 仅 Schema | 仅 Schema | 载荷也是 |
| 跨语言代码生成 | 良好 | 出色 | 良好 |
| Kafka 生态系统采用率 | 非常高 | 高（增长中） | 中等 |
| Schema 演进规则 | 写入者/读取者解析 | 基于字段编号 | JSON Schema 验证规则 |

## 兼容性策略

注册新的 Schema 版本时，Registry 会根据配置的兼容模式，将其与上一个版本进行检查。正确理解这四种模式非常重要——这是 Schema 管理中最常被混淆的概念。

| 模式 | 含义 | 部署顺序 |
| --- | --- | --- |
| **BACKWARD** | 使用**新** Schema 的读取者必须能够读取使用**旧** Schema 写入的数据 | 先升级**消费者** |
| **FORWARD** | 使用**旧** Schema 的读取者必须能够读取使用**新** Schema 写入的数据 | 先升级**生产者** |
| **FULL** | 同时满足 BACKWARD 和 FORWARD | 任意顺序都安全 |
| **NONE** | 不进行兼容性检查 | 需要手动协调 |

人们最常弄反的部分是：

* **BACKWARD** 表示“新 Schema（作为读取者）可以读取旧数据”。在实践中，这意味着可以安全地**先部署使用新 Schema 的消费者**——即使生产者仍在使用旧 Schema 写入，已升级的消费者也能正常读取。
* **FORWARD** 表示“旧 Schema（作为读取者）可以读取新数据”。这意味着可以安全地**先将生产者升级到新 Schema**——仍在运行旧 Schema 的消费者会继续正常工作。

### 向后兼容变更示例

向 `Order` Schema 添加一个具有默认值的可选字段与 BACKWARD 兼容：

```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

使用新 Schema 的消费者读取缺少此字段的旧数据时，只会得到 `default` 值（`null`）——不会失败。

### 破坏性变更示例

以下是经典的 BACKWARD 兼容性违规：

* **添加没有默认值的必填字段**：添加一个没有默认值的新 `discount_code` 字段，意味着新 Schema 的读取者会期望旧数据中存在该字段，但旧数据从未有过该字段，因此会失败。（反过来，*移除*字段与 BACKWARD 兼容，但会破坏 FORWARD——旧 Schema 的读取者仍会期望新数据中包含现已移除的必填字段。）
* **更改字段类型**：将 `amount` 从 `double` 改为 `string`，意味着现有的二进制编码数据无法再按新类型解码。
* **重命名字段**（不使用别名）：读取者会以新名称查找字段，但旧数据中只有旧名称。

## 在 Strimzi/EKS 上部署

### 部署 Apicurio Registry（Kafka-Topic Storage）

假设由 Strimzi 管理的 Kafka 集群已经在运行，您可以将 Apicurio Registry 作为 Deployment 部署在同一 namespace 中，并由 Kafka-topic 存储引擎提供后端支持。

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

Apicurio 也支持使用 SQL 后端（`APICURIO_STORAGE_KIND=sql`）代替 `kafkasql`，因此如果您已经运行 PostgreSQL/RDS 实例，可以改为将 Registry 指向该实例。相比之下，Karapace 始终将 Schema 存储在 Kafka Topic（`_schemas`）中，不需要单独配置后端。

### 注册 Schema

Registry 运行后，可通过其 REST API 注册 Schema（使用 Confluent 兼容端点）：

```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

### 客户端配置

Kafka 生产者/消费者应用程序将其序列化器指向 Registry URL：

```properties
value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer
schema.registry.url=http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6
```

相同的 `KafkaAvroSerializer` 类也适用于 Karapace——只需将 `schema.registry.url` 指向 Karapace 的 REST 端点（默认端口为 8081）。切换 Registry 实现时不需要更改应用程序代码，这正是 Confluent 兼容 API 提供的价值。

## 下一步

本部分介绍了当生产者和消费者各自独立演进时，Schema Registry 如何保障它们之间的数据契约安全。第 5 部分将转向 Kafka Connect 和 MirrorMaker——与外部系统集成，以及在集群之间复制数据。

[返回主页](./README.md)

## 测验

要测试您在本章中学到的内容，请尝试 [Topic 测验](../../quizzes/data-on-eks/kafka/04-schema-registry-quiz.md)。
