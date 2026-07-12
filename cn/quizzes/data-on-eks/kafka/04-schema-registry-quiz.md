# Schema Registry 测验

本测验考查你对 Schema Registry 存在原因、Avro/Protobuf 序列化取舍、四种兼容性模式，以及主要实现（Karapace、Apicurio、Confluent）之间许可证差异的理解。

## 选择题

1. Kafka broker 从不验证消息内容这一事实导致的最根本问题是什么？
   - A) Broker 吞吐量下降
   - B) Producer 和 consumer 可以在不了解彼此变更的情况下演进各自的 schema，从而导致反序列化失败
   - C) 你不能创建多个 topic
   - D) Partition 再均衡变得不可能

<details>

<summary>显示答案</summary>

**答案：B) Producer 和 consumer 可以在不了解彼此变更的情况下演进各自的 schema，从而导致反序列化失败**

**解释：**
Kafka 将每条消息都视为不透明的字节数组，并且不强制任何数据格式。由于 producer 和 consumer 通常是独立部署、发布节奏也不同的应用，一侧的 schema 变更可能在无声无息中破坏另一侧——导致反序列化失败或值损坏。Schema Registry 通过集中管理契约并强制执行兼容性来解决这个问题。
</details>

2. 与无 schema 的 JSON 相比，将 Avro/Protobuf 这样的二进制格式与 Schema Registry 结合使用的最大优势是什么？
   - A) 更容易让人直接阅读
   - B) Payload 更小，并且 schema 变更会被集中验证
   - C) 它会自动调整 partition 数量
   - D) Consumer group 变得不再必要

<details>

<summary>显示答案</summary>

**答案：B) Payload 更小，并且 schema 变更会被集中验证**

**解释：**
Avro/Protobuf 使用紧凑的二进制编码，不会重复字段名，因此 payload 比 JSON 更小。此外，消息只携带 schema ID，而不是完整 schema——实际 schema 由 registry 管理，并在注册新版本时验证兼容性。相比之下，JSON 仍然更容易让人直接阅读。
</details>

3. 使用 Schema Registry 时，线上传输的实际消息包含什么？
   - A) 完整的 schema 定义
   - B) 一个包含 schema ID 的短 header，后面跟着二进制编码的数据
   - C) Schema Registry 的 URL
   - D) Consumer group ID

<details>

<summary>显示答案</summary>

**答案：B) 一个包含 schema ID 的短 header，后面跟着二进制编码的数据**

**解释：**
Producer 会向 registry 注册（或查找）schema，并将返回的 schema ID（通常还包含一个 magic byte）添加到序列化消息的前部。完整的 schema 定义本身永远不会包含在消息中——只有 registry 会存储它——这正是 payload 能保持较小的原因。Consumer 读取这个 ID，并从 registry 获取匹配的 schema 来反序列化剩余部分。
</details>

4. 以下哪个 Schema Registry 实现是在 Apache License 2.0 下分发的？
   - A) Confluent Schema Registry
   - B) Karapace 和 Apicurio Registry 都是
   - C) 只有 Karapace
   - D) 只有 Apicurio Registry

<details>

<summary>显示答案</summary>

**答案：B) Karapace 和 Apicurio Registry 都是**

**解释：**
Karapace（Aiven）和 Apicurio Registry（Red Hat）都是在 Apache License 2.0 下分发的纯开源项目。Confluent Schema Registry 自 2018 年以来一直受 Confluent Community License 约束，该许可证对某些商业用途施加限制，并不是完全开源的许可证。
</details>

5. 对于自管理的 EKS + Strimzi stack，建议使用哪种组合来避免许可证摩擦？
   - A) 只使用 Confluent Schema Registry
   - B) Karapace 或 Apicurio Registry
   - C) 不使用 Schema Registry——只使用 JSON
   - D) 只有 AWS Glue Schema Registry 可行

<details>

<summary>显示答案</summary>

**答案：B) Karapace 或 Apicurio Registry**

**解释：**
Karapace 和 Apicurio Registry 都采用 Apache-2.0 许可证，可以不受限制地自托管。Confluent Schema Registry 的 Confluent Community License 引入了一些条款，在自管理使用前需要进行许可证审查。这两个开源替代方案都与 Confluent 的 API 兼容，因此 client 可以在不修改代码的情况下切换。
</details>

6. Avro 序列化中实现 schema 演进的核心机制是什么？
   - A) 基于字段编号的映射
   - B) Writer schema 与 reader schema 之间的解析规则
   - C) JSON Schema `$ref` 引用
   - D) 编译时代码生成

<details>

<summary>显示答案</summary>

**答案：B) Writer schema 与 reader schema 之间的解析规则**

**解释：**
即使 writer schema（写入数据时使用的 schema）和 reader schema（读回数据时使用的 schema）不同，Avro 仍然可以通过应用已定义的解析规则来正确解码数据——例如按名称匹配字段、应用默认值等。基于字段编号的映射是 Protobuf 的特征，不是 Avro 的特征。
</details>

7. Protobuf 相对于 Avro 在哪里具有相对优势？
   - A) 它的 payload 总是更小
   - B) 显式字段编号和更严格的类型系统能够生成质量更高的跨语言代码
   - C) 它不需要 Schema Registry
   - D) 它比 JSON 更适合人类阅读

<details>

<summary>显示答案</summary>

**答案：B) 显式字段编号和更严格的类型系统能够生成质量更高的跨语言代码**

**解释：**
Protobuf 会在其 `.proto` IDL 中为每个字段分配显式编号，并强制使用严格的类型系统，这通常会通过 `protoc` 在多种语言中生成更清晰的 client 代码。Payload 大小通常与 Avro 相当，而且 Protobuf 和 Avro 一样，常常与 Schema Registry 搭配使用。
</details>

8. 在配置为 BACKWARD 兼容性的 topic 上，哪一侧可以安全地先升级？
   - A) Producer
   - B) Consumer
   - C) Broker
   - D) ZooKeeper 或 KRaft controller

<details>

<summary>显示答案</summary>

**答案：B) Consumer**

**解释：**
BACKWARD 兼容性意味着“使用新 schema 的 reader 必须能够读取使用旧 schema 写入的数据。”这意味着 consumer 可以先升级到新 schema，即使 producer 仍在使用旧 schema 写入——升级后的 consumer 也能正确读取旧数据。相比之下，FORWARD 才是适合先部署 producer 的模式。
</details>

9. 哪个陈述正确描述了 FORWARD 兼容性？
   - A) 使用旧 schema 的 reader 必须能够读取使用新 schema 写入的数据
   - B) 使用新 schema 的 reader 必须能够读取使用旧 schema 写入的数据
   - C) 完全不执行兼容性检查
   - D) Consumer 必须始终先升级

<details>

<summary>显示答案</summary>

**答案：A) 使用旧 schema 的 reader 必须能够读取使用新 schema 写入的数据**

**解释：**
FORWARD 意味着“旧 schema（作为 reader）可以读取使用新 schema 写入的数据。”在此模式下，producer 可以先升级到新 schema，而仍运行旧 schema 的 consumer 会继续正确读取。B 描述的是 BACKWARD，C 描述的是 NONE，D 是 BACKWARD 下的安全顺序，而不是 FORWARD。
</details>

10. 以下哪种 schema 变更违反 BACKWARD 兼容性？
    - A) 添加一个带默认值的可选字段
    - B) 添加一个没有默认值的必填字段
    - C) 给字段添加 doc 注释
    - D) 在不更改字段名称或类型的情况下重新排序字段

<details>

<summary>显示答案</summary>

**答案：B) 添加一个没有默认值的必填字段**

**解释：**
添加没有默认值的必填字段意味着使用新 schema 的 reader 在读取旧数据（旧数据从未包含该字段）时，会期望有一个值却找不到——从而导致读取失败。相比之下，删除字段是向后兼容的，因为新 schema 的 reader 根本不会查找它（尽管这会破坏 FORWARD 兼容性）。添加带默认值的可选字段是 BACKWARD 兼容变更的经典示例，而添加 doc 注释或重新排序字段（Avro 按名称匹配）不会影响实际数据结构。
</details>

## 简答题

11. Consumer 从消息中读取哪一项信息，以找到用于反序列化该消息的正确 schema？

<details>

<summary>显示答案</summary>

**答案：Schema ID**

**解释：**
序列化时，producer 只包含 registry 发放的 schema ID（通常编码在消息前部、并带有 magic byte），而不是完整 schema。Consumer 读取这个 ID，向 registry 查询匹配的 schema，并使用它反序列化剩余的二进制 payload。
</details>

12. 要求 BACKWARD 和 FORWARD 兼容性同时成立的兼容性模式叫什么？

<details>

<summary>显示答案</summary>

**答案：FULL**

**解释：**
FULL 兼容性要求 BACKWARD（新 schema 的 reader 可以读取旧数据）和 FORWARD（旧 schema 的 reader 可以读取新数据）同时成立。这使得 producer/consumer 的升级顺序无关紧要，但从允许哪些 schema 变更来看，它也是四种模式中最严格的一种。
</details>

13. Apicurio Registry 支持哪两种 storage backend 类型？

<details>

<summary>显示答案</summary>

**答案：基于 Kafka topic 的 backend（kafkasql）和基于 SQL 的 backend（sql，例如 PostgreSQL）**

**解释：**
Apicurio Registry 允许你通过 `APICURIO_STORAGE_KIND` 环境变量选择 backend：`kafkasql` 将 schema 元数据存储在 Kafka topic 中，而 `sql` 将其存储在关系数据库（如 PostgreSQL）中。相比之下，Karapace 始终使用 Kafka topic（`_schemas`）作为其唯一的存储选项。
</details>

14. Confluent 在 2018 年前后将关键组件（包括 Schema Registry）切换到了哪种许可证，使它们不再是完全开源？

<details>

<summary>显示答案</summary>

**答案：Confluent Community License**

**解释：**
2018 年前后，Confluent 将包括 Schema Registry 在内的多个核心组件迁移到 Confluent Community License。该许可证让源代码保持可见，但禁止某些用途——例如将其作为竞争性托管服务提供——而这些用途在 OSI 批准的开源许可证下本来是允许的。
</details>

15. Kafka client 设置哪个属性，以便 Avro serializer/deserializer 知道在哪里找到 Schema Registry？

<details>

<summary>显示答案</summary>

**答案：schema.registry.url**

**解释：**
`schema.registry.url` 属性告诉 `KafkaAvroSerializer`/`KafkaAvroDeserializer`（及其等价组件）使用哪个 REST endpoint 来注册和查找 schema。只更改这个属性，就可以在 Karapace、Apicurio 和 Confluent 之间切换，而无需修改任何应用代码。
</details>

## 实践题

16. 编写一个 Avro 字段定义，以 BACKWARD 兼容的方式向现有 `Order` schema 添加一个可选的 `discountCode` 字段。

<details>

<summary>显示答案</summary>

**答案：**
```json
{ "name": "discountCode", "type": ["null", "string"], "default": null }
```

**解释：**
将 union type `["null", "string"]` 与 `default: null` 结合使用，意味着使用新 schema 的 reader 在读取缺少此字段的旧数据时，会自动收到 `null`。添加没有默认值的必填字段会破坏 BACKWARD 兼容性，因此要保持与现有数据的兼容性，始终需要指定默认值。
</details>

17. 编写一个 curl 调用，通过 Confluent-compatible REST API 在 `orders-value` subject 下注册新的 Avro schema。

<details>

<summary>显示答案</summary>

**答案：**
```bash
curl -X POST http://apicurio-registry.kafka.svc:8080/apis/ccompat/v6/subjects/orders-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"orderId\",\"type\":\"string\"}]}"}'
```

**解释：**
向 `/subjects/<subject>/versions` 发送 `POST` 请求会注册 schema。`<topic>-value` 是 Confluent 针对给定 topic 的 value payload 所使用的标准 subject 命名约定。请求体中的 `schema` 字段以转义 JSON 字符串的形式携带实际 Avro schema。注册时，registry 会根据配置的兼容性模式，将新 schema 与以前的版本进行验证。
</details>

18. 为使用 Kafka topic 作为 storage backend、并与 Strimzi Kafka cluster 运行在同一 namespace 中的 Apicurio Registry Deployment 编写核心 container spec（image、环境变量）。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
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
```

**解释：**
`APICURIO_STORAGE_KIND=kafkasql` 告诉 Apicurio 将 schema 元数据持久化到 Kafka topic 中，而不是要求单独的数据库。`APICURIO_KAFKASQL_BOOTSTRAP_SERVERS` 必须指向 Strimzi 创建的 bootstrap service（`<cluster-name>-kafka-bootstrap`）。如果要改用 SQL backend，请设置 `APICURIO_STORAGE_KIND=sql`，并同时配置相应的数据源连接设置。
</details>

---

[返回学习资料](../../../data-on-eks/kafka/04-schema-registry.md) | [下一测验：Kafka Connect and MirrorMaker](./05-kafka-connect-mirrormaker-quiz.md)
