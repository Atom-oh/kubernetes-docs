# Schema Registry 测验

复习数据模式（Schema）契约、编码、兼容性、恢复和部署示例。

## 1. 为什么 Kafka 的基本记录存储不强制执行 Schema 合约？

<details>
<summary>显示答案</summary>

键和值以字节形式存储。结构和业务验证取决于序列化器、应用程序和验证路径。添加字段不一定会使消费者不兼容或无法正常工作。

</details>

## 2. 没有 Registry，能否在运行时之前对 JSON 进行版本管理和验证？

<details>
<summary>显示答案</summary>

可以。JSON Schema、CI 检查和版本化规范可以提供契约。注册中心（Registry）负责集中治理和分发；二进制编码则是另一种独立选择。

</details>

## 3. 常见的 Confluent Schema ID 载荷封装格式中的前五个字节是什么？

<details>
<summary>显示答案</summary>

一个魔数字节（magic byte）和一个四字节的 Schema ID，后面跟着值。Protobuf 还包含消息索引。这并非适用于每种注册中心或编码的通用规则。

</details>

## 4. Karapace 6.2.4 支持哪些主要 Schema 格式？

<details>
<summary>显示答案</summary>

Avro、JSON Schema 和 Protobuf。请分别检查 JSON Schema 草案/关键字验证以及兼容性分析支持情况。

</details>

## 5. 检查 Apache-2.0 和 Confluent 组件许可证时，哪些事项很重要？

<details>
<summary>显示答案</summary>

Apache-2.0 包含保留所需声明等条件。Confluent Server 和客户端/Avro 模块的许可证可能不同。请检查实际使用的组件和支持合同，不要根据规模推断条款。

</details>

## 6. 什么支持 Avro 演进？字段默认值的用途是什么？

<details>
<summary>显示答案</summary>

写入端与读取端的 Schema 解析。如果写入端 Schema 中缺少某个字段，读取端会使用默认值。它并不允许写入端省略任意必需字段。

</details>

## 7. 已删除的 Protobuf 字段编号能否用于表示其他含义？

<details>
<summary>显示答案</summary>

不要重复使用。旧数据或客户端可能会按原来的含义解释该编号。应根据需要保留已删除的编号/名称，并检查线格式类型和应用语义。

</details>

## 8. 向后兼容的 Schema 变更通常按什么顺序发布？

<details>
<summary>显示答案</summary>

先升级消费者：新的读取端必须能够读取此前写入端写入的数据。还要测试业务行为，并记住兼容性是针对注册主题（subject）配置的，而不是 Kafka 主题（topic）固有的属性。

</details>

## 9. FORWARD 兼容性检查哪个方向？

<details>
<summary>显示答案</summary>

之前的读取端必须能够读取新的写入端写入的数据，这通常意味着可以先升级生产者。但这本身并不能验证新的读取端是否能重放旧数据。

</details>

## 10. 删除 Avro 字段是否总会破坏前向兼容性？

<details>
<summary>显示答案</summary>

不会。如果旧读取端有默认值，就可以为新写入端数据中缺少的字段提供该值。如果没有默认值，则会失败。请将此情况与向后兼容方向区分开来；在向后兼容方向中，新的读取端不再要求该字段。

</details>

## 11. 冷缓存消费者和 Registry 迁移需要检查哪些内容？

<details>
<summary>显示答案</summary>

保留记录中的标识符必须能解析为相同的写入端 Schema。请验证 ID 映射、引用、注册主题（subject）策略、编码、身份验证和客户端版本。仅更改 URL 并不足以证明迁移成功。

</details>

## 12. 哪种模式同时要求 BACKWARD 和 FORWARD？它的 TRANSITIVE 变体增加了什么？

<details>
<summary>显示答案</summary>

FULL。FULL_TRANSITIVE 会针对所有先前版本检查两个 Schema 方向。普通 FULL 只与最近的前一个版本比较。两者都无法保证业务语义或应用程序行为。

</details>

## 13. Apicurio KafkaSQL 会在 snapshots topic 中存储完整快照文件吗？

<details>
<summary>显示答案</summary>

不会。它记录的是文件路径。文件的持久性、共享和恢复需要单独设计。该实验会禁用定时快照，并保留完整日志，以便在重启后重放。

</details>

## 14. 哪些设置符合 KafkaSQL 3.3.3 对 journal/snapshots topic 的默认检查？

<details>
<summary>显示答案</summary>

`cleanup.policy=delete`、`retention.ms=-1` 和 `retention.bytes=-1`。使用无限期保留时要监控增长。不要照搬通用的 `_schemas` 日志压实（compaction）配置或较短的事件保留期。

</details>

## 15. 生产者和消费者使用的 Avro 属性有哪些不同？

<details>
<summary>显示答案</summary>

生产者使用 `value.serializer=io.confluent.kafka.serializers.KafkaAvroSerializer`；消费者使用 `value.deserializer=io.confluent.kafka.serializers.KafkaAvroDeserializer`。两者都需要注册中心 URL、Broker 的 TLS/SASL 配置和库依赖。

</details>

## 16. 编写 Avro 定义，包含一个 timestamp-millis 字段和一个带默认值的 discountCode 字段。

<details>
<summary>显示答案</summary>

```json
[
  {"name":"createdAt","type":{"type":"long","logicalType":"timestamp-millis"}},
  {"name":"discountCode","type":["null","string"],"default":null}
]
```

这些是记录 `fields` 数组中的定义。逻辑类型应放在 type 对象内；新读取端读取旧数据时，新增字段的 null 默认值会生效。

</details>

## 17. 如何将本章的 order.avsc 注册到 orders-value subject 下？

<details>
<summary>显示答案</summary>

按照本章的 `register.sh` 示例操作：解析 JSON，并创建一个包含 Schema 字符串和 `schemaType: AVRO` 的请求文件。将其 POST 到 `/apis/ccompat/v7/subjects/orders-value/versions`，并检查 HTTP 错误。先配置兼容性，然后获取最新版本。默认的 TopicNameStrategy 假定 topic 名为 `orders`。

</details>

## 18. 描述本章的 Apicurio 部署与前面的 Strimzi 环境之间的连接方式。

<details>
<summary>显示答案</summary>

使用镜像 3.3.3、`APICURIO_STORAGE_KIND=kafkasql`、`my-cluster-kafka-bootstrap.kafka.svc:9093`、SASL_SSL/SCRAM-SHA-512、CA 信任库（truststore）、由 Secret 提供的 JAAS 配置以及显式主机名验证。预先创建三个存储主题（topic）和用户 ACL，并禁用自动创建主题。请区分管理端口 9000 上的运行状况检查与 HTTP API 端口 8080。HTTP API 身份验证与 Kafka 身份验证相互独立；该实验并非公共服务。

</details>

---

[返回学习材料](../../../data-on-eks/kafka/04-schema-registry.md) | [下一份测验](./05-kafka-connect-mirrormaker-quiz.md)
