# 第 8 部分：最佳实践

> **支持的版本**：Apache Kafka 3.9、Strimzi 0.45+\
> **最后更新**：July 9, 2026

在本系列深入讲解中，我们涵盖了 Kafka 基础知识、Strimzi 运维、schema registry、Kafka Connect/MirrorMaker、MSK 集成以及监控。本最终文档按类别汇总了生产就绪最佳实践，并将前面七个部分的关键内容整合为一份上线检查清单。

## 1. 分区设计

### 确定分区数量

从某个 topic **预期的最大 consumer 并行度**开始考虑。给定 consumer group 中的一个分区在同一时刻只能由一个 consumer 实例消费，因此应确定预计将 consumer group 扩展到什么规模，并至少配置相同数量的分区。如果计划在峰值时扩展至 20 个 consumer 实例，则至少需要 20 个分区。

过度分区会带来实际成本，应予以避免：

- **更多打开的文件句柄**：每个分区都会保持多个日志段文件（`.log`、`.index`、`.timeindex`）处于打开状态，因此每个 broker 的打开文件描述符数量会随分区数量线性增长。
- **更大的内存压力**：broker 上的 producer/consumer 批处理缓冲区及每个复制线程缓冲区都会随分区数量增加。
- **更慢的再平衡和故障转移**：broker 故障时 controller 必须执行的 leader 选举工作量会随分区数量增加，consumer group 再平衡也会耗时更长。

Confluent 的经典经验法则是，每个 broker 约 **4,000 个分区、每个 cluster 约 200,000 个分区**作为软上限——这是 ZooKeeper controller 是元数据瓶颈时期的指导建议。得益于更快的 controller 元数据路径，基于 KRaft 的 cluster（Kafka 3.x+ controller quorum）可处理更高得多的分区数量；但原则依然成立：不要仅仅因为可以就过度分区，并应通过真实负载测试验证工作负载的实际上限。

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### 选择分区键

选择具有**高基数且分布均匀**的键，以避免热点分区。默认 partitioner 使用 murmur2 对键进行哈希，并对分区数量取模；因此低基数的键（例如仅有少数几个不同取值的 `country` 或 `status`）会使与主要流量值对应的少数分区过载，而其他分区则处于空闲状态。优先选择具有足够高基数的字段（例如 `user_id`），或者为低基数键添加盐值（追加随机后缀或由时间戳派生的后缀）以实现更均匀的分布。

### 谨慎处理分区数量变更

增加**带键** topic 的分区数量会破坏键到分区的映射。由于 `partition_count` 一旦发生改变，`hash(key) % partition_count` 的结果也会改变，因此同一个键在变更后可能落到与之前不同的分区。这会导致两个具体问题：

- **顺序被破坏**：Kafka 仅保证分区内的顺序，因此同一键的消息一旦被拆分到多个分区，consumer 就无法再依赖键级别的顺序。
- **共分区被破坏**：Kafka Streams（以及类似工具）中的 join 要求被连接的 topic 共享相同的分区数量和分区方案。仅变更 join 一侧的分区会导致其失效。

在容量规划时应预留分区数量余量；如果生产 topic 已依赖基于键的顺序或 join，则与其增加现有 topic 的分区，不如迁移到新的 topic。

## 2. Producer 调优

| 设置 | 推荐值 | 目的 |
|---------|--------------------|---------|
| `acks` | `all`（适用于持久性至关重要的 topic） | 等待所有同步副本（ISR）的确认，以便 broker 故障时不会丢失数据 |
| `min.insync.replicas`（topic/broker 设置） | `2`（使用 replication.factor=3 时） | 与 `acks=all` 结合时，要求写入至少到达 2 个副本后才成功——在 topic（`kafka-configs.sh --entity-type topics`）或 broker 默认设置中配置，而非作为 producer client 属性 |
| `linger.ms` | `5`–`20` | 用少量延迟换取更大的批次和更高吞吐量 |
| `batch.size` | `32768`–`65536`（32–64KB） | 提高每批次的最大字节数，以增加每个请求的吞吐量 |
| `enable.idempotence` | `true` | 防止由 producer 重试引起的重复写入 |
| `compression.type` | `lz4` 或 `zstd` | 降低网络和存储成本 |

```properties
# Producer settings for durability-critical topics (orders, payments, etc.)
# (min.insync.replicas is a topic/broker setting, not a producer property — shown here for reference only)
acks=all
enable.idempotence=true
compression.type=lz4
linger.ms=10
batch.size=32768
retries=2147483647
delivery.timeout.ms=120000
```

除非以与之不兼容的方式显式覆盖 `acks` 或 `retries`，否则 `enable.idempotence=true` **自 Kafka 3.0 起一直为默认值**。它会为 producer 分配唯一的 producer ID 和每分区序列号，使 broker 能够透明地去除由瞬态网络错误引发的重试重复项。这不同于完整的 exactly-once 语义——幂等性仅消除 producer 到 broker 跳转期间的重复；真正的端到端 exactly-once 还需要使用事务 API（`transactional.id`）。

对于大多数工作负载，`lz4` 在 CPU 开销和压缩比之间提供了良好平衡。`zstd` 的压缩效果更佳——适用于 JSON/文本占比较高的 payload——但会带来稍高的 CPU 使用率。`gzip` 压缩效果良好，但 CPU 开销很大，因此通常不建议用于高吞吐量 producer。

## 3. Consumer 调优

### 避免再平衡风暴

如果处理耗时超过 `max.poll.interval.ms`（默认 5 分钟），consumer 会被强制从其 group 中移除，从而触发再平衡。当多个 consumer 同时变慢时，这可能会级联为反复中断 group 的“再平衡风暴”。

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

降低 `max.poll.records` 会减少单次 `poll()` 调用返回的记录数量，从而缩短两次 poll 之间的处理窗口。提高 `max.poll.interval.ms` 可在移除 consumer 前为慢处理留出更多余量。更稳健的解决方案是从架构上将繁重处理完全移出 poll 循环，交由独立的 worker thread pool 执行，而 poll 只负责获取并移交工作。

### 手动提交 offset

对于 at-least-once 处理至关重要的 pipeline（订单处理、支付），自动提交（`enable.auto.commit=true`）可能会在相应记录实际完成处理之前提交 offset——如果 consumer 在两者之间崩溃，从 pipeline 的角度看，该记录实际上就丢失了，尽管它已被“提交”。

```properties
enable.auto.commit=false
```

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> record : records) {
        process(record);          // business logic
    }
    consumer.commitSync();        // commit only after processing succeeds
}
```

### 静态 group 成员资格

Kubernetes 上的 Consumer Pod 经常重启——滚动部署、OOMKilled 重启、节点替换。默认情况下，consumer 离开并重新加入 group 会触发完整再平衡，因此频繁的短暂重启会导致整个 group 反复发生不必要的处理暂停。设置 `group.instance.id` 可启用静态成员资格：如果 consumer 在 `session.timeout.ms` 内重新连接，它将恢复之前的分区分配，完全不会发生再平衡。

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` 必须对每个 Pod 唯一——通常来自 StatefulSet Pod 名称或通过 downward API 注入。

## 4. 安全性

### mTLS（传输加密 + 双向认证）

部署 Kafka cluster 时，Strimzi 会自动配置并轮换自己的 cluster CA。将 listener 的类型设置为 `tls` 会加密 client-broker 流量，而为 `KafkaUser` 指定 `tls` 认证类型会使 Strimzi 签发由该 cluster CA 签名的 client 证书。

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: order-service
  labels:
    strimzi.io/cluster: my-cluster
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: ["Read", "Write", "Describe"]
      - resource:
          type: group
          name: order-service-group
        operations: ["Read"]
```

### SASL/SCRAM

对于分发和轮换 client 证书不切实际的环境（旧版应用、第三方工具），基于用户名/密码的 SASL/SCRAM（`scram-sha-512`）是可靠的替代方案。将 listener 的认证类型设置为 `scram-sha-512`，并为相应的 `KafkaUser` 设置相同的 `authentication.type`；Strimzi 会自动将凭证生成到 Secret 中。

### 声明式 ACL 管理

如上面的 `KafkaUser` 示例所示，`authorization.type: simple` 加上 `acls` 列表使你能够通过 GitOps 将 ACL 作为代码管理，而不是手动对 broker 执行 `kafka-acls.sh`。为 topic 接入新服务只需提交一个新的 `KafkaUser` 资源。

### 网络策略

Strimzi listener 支持 `networkPolicyPeers`，可限制哪些 Pod 能够访问给定 listener 端口（例如 9092/9093/9094）。

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    networkPolicyPeers:
      - podSelector:
          matchLabels:
            app: order-service
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kafka-clients
```

Strimzi 会在后台将其转换为标准 Kubernetes `NetworkPolicy`，因此只有匹配指定 selector 的 Pod 才能访问该 listener 端口。

### 静态加密

EBS 卷加密**并非** EBS CSI driver 自动应用的功能——需要通过以下任一种方式显式启用：

- 启用账户/区域级别的 **“默认 EBS 加密”**设置，以便此后创建的每个卷都会自动加密。
- 在 `StorageClass` 上设置 `encrypted: "true"`（以及可选的 `kmsKeyId`）。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx
```

由于 Kafka cluster 通常承载对合规性敏感的数据，因此应将用于 broker PVC 的显式加密 `StorageClass` 作为默认配置，而非事后补救。

## 5. 成本优化

### 合理调整实例类型大小

大多数 Kafka 工作负载对**内存——尤其是 OS page cache——的敏感度远高于 CPU**。Kafka 旨在从 page cache 为大多数读取提供服务，因此在 consumer 读取近期数据这一常见场景中，broker heap 之后剩余的 RAM（通常 4–8GB 已足够）直接决定吞吐量。因此，内存优化实例（例如 `r6g`/`r7g` Graviton 系列）通常比计算优化实例提供更好的性价比。

### 分层存储

由 KIP-405 定义的分层存储会将较旧的日志段从本地磁盘卸载到 S3 等远程存储，从而降低每个 broker 所需的本地 EBS 容量。它早在 Apache Kafka 3.6 中作为早期访问功能推出，并在 **Kafka 3.9 中达到生产就绪（GA）**，但默认未启用——它仍是必须显式开启（`remote.log.storage.system.enable=true`）的可选功能。在 Strimzi 中依赖它之前，请查看该 Strimzi 发布版本对分层存储的支持和成熟度说明，并首先在非生产 cluster 中进行全面验证。

### 调整日志保留

应根据实际业务需求为每个 topic 设置 `retention.ms`/`retention.bytes`，而不是保留默认值，因为在 EBS 上过度保留数据会产生直接且持续的成本。仅需要每个键最新值的 topic（状态快照、类似缓存的数据）应使用 `cleanup.policy=compact`，以避免存储无限增长。

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### 使用 Spot 实例

对于开发/预发布环境或关键性较低的 Strimzi cluster，在 Spot 实例上运行 broker node pool 可显著降低成本。但是，**KRaft controller node pool 应保留在 On-Demand 实例上**。失去 controller quorum 的多数节点会使整个 cluster 的元数据管理停止，这一风险不值得为节省 Spot 成本而承担。使用 Pod topology spread constraints 将 broker node pool 分散到多个 AZ/节点上，以避免 Spot 回收事件一次性移除同一分区的多个副本。

## 6. 上线检查清单

将本系列深入讲解第 1 至第 8 部分的关键项目汇总为一份生产前检查清单：

- [ ] **架构**：以 KRaft 模式运行，且 controller 和 broker node pool 分离（第 1、2 部分）
- [ ] **复制**：生产 topic 使用 `replication.factor=3` 和 `min.insync.replicas=2`，可容忍单个 broker 故障（第 1 部分）
- [ ] **分区设计**：分区数量按预期最大 consumer 并行度确定，而非过度拆分（第 8 部分）
- [ ] **Strimzi 版本固定**：Operator 和 Kafka 版本被显式固定，不会在自动升级时漂移（第 2 部分）
- [ ] **存储**：broker `StorageClass` 使用带加密（`encrypted: "true"`）的 gp3（或 io2）（第 3、8 部分）
- [ ] **PodDisruptionBudget**：PDB 确保在滚动重启和节点替换期间保持 quorum/多数派可用性（第 3 部分）
- [ ] **滚动升级演练**：已在预发布环境实际执行过滚动升级流程（第 3 部分）
- [ ] **Schema 兼容性**：根据每个 topic 的需求，有意设置 schema registry 兼容模式（BACKWARD/FORWARD/FULL）（第 4 部分）
- [ ] **DR/复制**：已记录基于 Kafka Connect/MirrorMaker2 的灾难恢复或跨区域复制方案，并且已测试故障转移（第 5 部分）
- [ ] **MSK 与自管理决策**：托管 MSK 与 Strimzi 自管理之间的选择已记录，并说明了运维和成本依据（第 6 部分）
- [ ] **监控/告警**：已为 broker 指标和 consumer lag 配置 dashboard 和告警规则（第 7 部分）
- [ ] **自动扩缩容**：consumer 工作负载通过 KEDA 或等效机制根据 lag 扩缩容（第 7 部分）
- [ ] **Producer/consumer 配置审查**：已根据工作负载需求审查 `acks`、`enable.idempotence`、offset 提交策略和静态 group 成员资格（第 8 部分）
- [ ] **安全性**：已部署 mTLS 或 SASL/SCRAM、基于 `KafkaUser` 的 ACL，以及 listener `NetworkPolicy`（第 8 部分）
- [ ] **成本审查**：定期重新评估实例类型、保留策略和 Spot 使用情况（第 8 部分）
- [ ] **负载测试**：已按预期峰值吞吐量对 broker 和 consumer 扩展能力进行实际负载测试

满足此检查清单是判定 cluster 已准备好在 EKS 上投入生产运行的合理标准。

---

[返回主页](./README.md)

## 测验

要测试你在本章所学内容，请尝试[Topic 测验](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)。
