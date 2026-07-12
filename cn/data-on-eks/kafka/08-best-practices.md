# 第 8 部分：最佳实践

> **支持的版本**: Apache Kafka 3.9, Strimzi 0.45+\
> **最后更新**: July 9, 2026

在本次深入讲解中，我们介绍了 Kafka 基础、Strimzi 运维、schema registry、Kafka Connect/MirrorMaker、MSK 集成以及监控。本文档作为最后一部分，按类别汇总生产就绪最佳实践，并将前七个部分中的关键项目整合成一份上线检查清单。

## 1. Partition 设计

### 规划 partition 数量

从某个 topic 的**预期最大 consumer 并行度**开始规划。在给定 consumer group 内，一个 partition 同一时间只能被一个 consumer 实例消费，因此需要先决定你期望将 consumer group 扩展到什么规模，并至少配置这么多 partition。如果你计划在峰值时扩展到 20 个 consumer 实例，那么至少需要 20 个 partition。

过度分区会带来实际成本，应避免这样做：

- **更多打开的文件句柄**：每个 partition 都会保持多个 log segment 文件（`.log`、`.index`、`.timeindex`）打开，因此每个 broker 的打开文件描述符数量会随 partition 数量线性增长。
- **更大的内存压力**：producer/consumer 批处理缓冲区以及 broker 上每个 replication thread 的缓冲区都会随 partition 数量扩展。
- **更慢的 rebalance 和故障切换**：broker 故障时 controller 必须执行的 leader election 工作量会随 partition 数量扩展，consumer group rebalance 也会花费更长时间。

Confluent 的经典经验法则曾经是一个软上限：**每个 broker 大约 4,000 个 partition，每个 cluster 200,000 个 partition**——这是 ZooKeeper-based controller 作为 metadata 瓶颈时代的指导。KRaft-based cluster（Kafka 3.x+ controller quorum）借助快得多的 controller metadata 路径，可以处理高得多的 partition 数量，但原则仍然成立：不要仅仅因为可以就过度分区，并且要通过真实负载测试验证你的 workload 的实际上限。

```bash
# Check total partition count and distribution per broker
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe | grep -c "PartitionCount"

# Inspect partition/leader distribution for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
```

### 选择 partition key

选择具有**高基数且分布均匀**的 key，以避免 hot partition。默认 partitioner 会使用 murmur2 对 key 进行哈希，并对 partition 数量取模，因此低基数 key（例如只有少量不同值的 `country` 或 `status`）会让匹配主要流量值的少数 partition 过载，而其他 partition 处于空闲状态。优先选择具有足够高基数的字段（例如 `user_id`），或者对低基数 key 加盐（追加随机或基于时间戳生成的后缀）以强制更均匀地分布。

### 谨慎处理 partition 数量变更

增加**带 key** topic 的 partition 数量会破坏 key 到 partition 的映射。由于 `hash(key) % partition_count` 会在 `partition_count` 改变后立即变化，同一个 key 在变更之后可能落到与之前不同的 partition。这会造成两个具体问题：

- **破坏顺序性**：Kafka 只保证 partition 内的顺序，因此一旦同一 key 的消息被拆分到多个 partition，consumer 就无法再依赖 key 级别的顺序。
- **破坏共分区**：Kafka Streams（以及类似系统）中的 join 要求被 join 的 topic 具有相同的 partition 数量和分区方案。只在 join 的一侧变更 partition 会破坏 join。

在容量规划期间为 partition 数量预留余量；如果某个生产 topic 已经依赖基于 key 的顺序或 join，相比增加现有 topic 的 partition，更建议迁移到新 topic。

## 2. Producer 调优

| Setting | Recommended value | Purpose |
|---------|--------------------|---------|
| `acks` | `all`（用于对持久性要求关键的 topic） | 等待所有 in-sync replicas（ISR）的确认，避免 broker 故障导致数据丢失 |
| `min.insync.replicas`（topic/broker 设置） | `2`（当 replication.factor=3 时） | 与 `acks=all` 结合使用，要求写入至少到达 2 个副本后才算成功——应设置在 topic（`kafka-configs.sh --entity-type topics`）或 broker 默认值上，而不是作为 producer client 属性 |
| `linger.ms` | `5`–`20` | 用少量延迟换取更大的批次和更高的吞吐量 |
| `batch.size` | `32768`–`65536`（32–64KB） | 提高每个批次的最大字节数，以增加每个请求的吞吐量 |
| `enable.idempotence` | `true` | 防止 producer 重试导致重复写入 |
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

除非你显式地以与其不兼容的方式覆盖 `acks` 或 `retries`，否则 `enable.idempotence=true` 自 **Kafka 3.0 起一直是默认值**。它会为 producer 分配唯一的 producer ID 和每个 partition 的 sequence number，使 broker 能够透明地去重由瞬时网络错误导致的重试。这不同于完整的 exactly-once 语义——idempotence 只会移除 producer 到 broker 这一跳上的重复；真正端到端的 exactly-once 还需要 transactional API（`transactional.id`）。

对于大多数 workload，`lz4` 在 CPU 开销和压缩率之间提供了良好平衡。`zstd` 压缩效果更好——适用于 JSON/text-heavy payload——但代价是 CPU 使用量略高。`gzip` 压缩效果不错，但 CPU 开销较高，因此通常不建议用于高吞吐 producer。

## 3. Consumer 调优

### 避免 rebalance storm

如果处理耗时超过 `max.poll.interval.ms`（默认 5 分钟），consumer 会被强制从 group 中驱逐，从而触发 rebalance。当多个 consumer 同时变慢时，这可能级联成反复 group 中断的“rebalance storm”。

```properties
# Tune poll-related settings around your actual per-batch processing time
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

降低 `max.poll.records` 会减少单次 `poll()` 调用返回的 record 数量，从而缩短两次 poll 之间的处理窗口。提高 `max.poll.interval.ms` 可以在驱逐之前为慢处理提供更多余量。更稳健的修复是架构性的：将繁重处理完全移出 poll loop，放入单独的 worker thread pool，只通过 polling 获取并分派工作。

### 手动提交 offset

对于需要 at-least-once 处理的 pipeline（订单处理、支付），auto-commit（`enable.auto.commit=true`）可能会在对应 record 实际完成处理之前提交 offset——如果 consumer 在此期间崩溃，从 pipeline 的角度看，该 record 实际上已经丢失，即便它已经被“提交”。

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

### 静态 group membership

Kubernetes 上的 consumer Pod 经常重启——rolling deploy、OOMKilled 重启、node 替换。默认情况下，consumer 离开并重新加入 group 会触发完整 rebalance，因此频繁的短暂重启会导致整个 group 反复出现不必要的处理暂停。设置 `group.instance.id` 可以启用 static membership：如果 consumer 在 `session.timeout.ms` 内重新连接，它会保留之前的 partition assignment 继续运行，完全不发生 rebalance。

```properties
group.instance.id=${POD_NAME}
session.timeout.ms=45000
```

`group.instance.id` 必须对每个 Pod 唯一——通常来源于 StatefulSet Pod 名称，或通过 downward API 注入。

## 4. 安全

### mTLS（传输加密 + 双向认证）

部署 Kafka cluster 时，Strimzi 会自动配置并轮换自己的 cluster CA。将 listener 的 type 设置为 `tls` 会加密 client-broker 流量，而为 `KafkaUser` 设置 `tls` authentication type 会让 Strimzi 签发由该 cluster CA 签名的 client certificate。

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

对于分发和轮换 client certificate 不切实际的环境（legacy app、third-party tool），基于 username/password 的 SASL/SCRAM（`scram-sha-512`）是可靠的替代方案。将 listener 的 authentication type 设置为 `scram-sha-512`，并给匹配的 `KafkaUser` 设置相同的 `authentication.type`；Strimzi 会自动将凭证生成到 Secret 中。

### 声明式 ACL 管理

如上面的 `KafkaUser` 示例所示，`authorization.type: simple` 加上 `acls` 列表，可以让你通过 GitOps 将 ACL 作为代码管理，而不是手动针对 broker 运行 `kafka-acls.sh`。将新服务接入某个 topic 只需要提交新的 `KafkaUser` resource。

### Network policy

Strimzi listener 支持 `networkPolicyPeers`，用于限制哪些 Pod 可以访问给定的 listener port（例如 9092/9093/9094）。

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

Strimzi 会在幕后将其转换为标准 Kubernetes `NetworkPolicy`，因此只有匹配指定 selector 的 Pod 才能访问该 listener port。

### 静态加密

EBS volume encryption **不是** EBS CSI driver 会自动应用的功能——你需要通过以下方式之一显式选择启用：

- 启用 account/region 级别的 **“EBS encryption by default”** 设置，使之后创建的每个 volume 都自动加密。
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

由于 Kafka cluster 通常承载合规敏感数据，应将给 broker PVC 显式使用加密 `StorageClass` 视为默认要求，而不是事后补充。

## 5. 成本优化

### 合理选择 instance type

大多数 Kafka workload 对**内存——尤其是 OS page cache——的敏感度远高于 CPU**。Kafka 被设计为从 page cache 提供大多数读取，因此在 consumer 读取近期数据这一常见场景中，broker heap（通常 4–8GB 已经足够）之外剩余的 RAM 会直接决定吞吐量。基于这个原因，memory-optimized instance（例如 `r6g`/`r7g` Graviton 系列）通常比 compute-optimized instance 提供更好的性价比。

### Tiered storage

KIP-405 定义的 tiered storage 会将较旧的 log segment 从本地磁盘卸载到 S3 等 remote storage，从而减少每个 broker 所需的本地 EBS 容量。它早在 Apache Kafka 3.6 中以 early access 形式落地，并在 **Kafka 3.9 中成为生产就绪（GA）**，但默认并未启用——它仍是你必须显式开启的 opt-in 功能（`remote.log.storage.system.enable=true`）。在 Strimzi 中依赖它之前，请检查该 Strimzi release 关于 tiered storage 的支持和成熟度说明，并先在非生产 cluster 上进行充分验证。

### 调整 log retention

根据实际业务需求为每个 topic 设置 `retention.ms`/`retention.bytes`，而不是保留默认值，因为在 EBS 上过度保留数据会产生直接且持续的成本。只需要保留每个 key 最新值的 topic（state snapshot、cache-like data）应使用 `cleanup.policy=compact`，以避免存储无限增长。

```bash
# Example: tighten retention for a specific topic
kubectl exec -n kafka my-cluster-broker-0 -c kafka -- \
  bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

### 使用 Spot instance

对于 dev/staging 环境或关键性较低的 Strimzi cluster，在 Spot instance 上运行 broker node pool 可以显著降低成本。不过，**KRaft controller node pool 应保持在 On-Demand 上**。丢失 controller quorum 的多数成员会使整个 cluster 的 metadata 管理停摆，这个风险不值得为了 Spot 节省而承担。使用 Pod topology spread constraint 将 broker node pool 分散到多个 AZ/node，避免一次 Spot 回收事件同时带走同一 partition 的多个 replica。

## 6. 上线检查清单

将本深入讲解第 1 到第 8 部分的关键项目汇总为一份单一的预生产检查清单：

- [ ] **架构**：运行在 KRaft 模式下，并且 controller 和 broker node pool 分离（第 1、2 部分）
- [ ] **复制**：生产 topic 使用 `replication.factor=3` 和 `min.insync.replicas=2`，可容忍单个 broker 故障（第 1 部分）
- [ ] **Partition 设计**：partition 数量按预期最大 consumer 并行度规划，而不是过度拆分（第 8 部分）
- [ ] **Strimzi 版本固定**：Operator 和 Kafka 版本被显式固定，而不是任由 auto-upgrade 漂移（第 2 部分）
- [ ] **存储**：broker `StorageClass` 使用 gp3（或 io2）并启用加密（`encrypted: "true"`）（第 3、8 部分）
- [ ] **PodDisruptionBudget**：PDB 在 rolling restart 和 node 替换期间保证 quorum/majority 可用（第 3 部分）
- [ ] **Rolling upgrade 演练**：rolling upgrade 程序已经在 staging 中实际演练过（第 3 部分）
- [ ] **Schema compatibility**：schema registry compatibility mode（BACKWARD/FORWARD/FULL）根据每个 topic 的需求有意设置（第 4 部分）
- [ ] **DR/复制**：基于 Kafka Connect/MirrorMaker2 的 disaster recovery 或跨区域复制已有文档记录，并且已测试 failover（第 5 部分）
- [ ] **MSK vs. self-managed 决策**：托管 MSK 与 Strimzi self-managed 之间的选择已记录，并包含其运维与成本理由（第 6 部分）
- [ ] **监控/告警**：存在用于 broker metric 和 consumer lag 的 dashboard 与 alert rule（第 7 部分）
- [ ] **自动扩缩**：consumer workload 通过 KEDA 或等效机制基于 lag 扩缩（第 7 部分）
- [ ] **Producer/consumer 配置审查**：`acks`、`enable.idempotence`、offset commit 策略以及 static group membership 都已根据 workload 需求完成审查（第 8 部分）
- [ ] **安全**：mTLS 或 SASL/SCRAM、基于 `KafkaUser` 的 ACL，以及 listener `NetworkPolicy` 都已到位（第 8 部分）
- [ ] **成本审查**：instance type、retention policy 和 Spot 使用情况会被定期重新评估（第 8 部分）
- [ ] **负载测试**：broker 和 consumer 扩展能力已经按预期峰值吞吐量完成实际负载测试

满足这份检查清单，是判断该 cluster 已准备好在 EKS 上运行生产 workload 的合理标准。

---

[返回主页](./)

## 测验

要测试你在本章中学到的内容，请尝试 [主题测验](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)。
