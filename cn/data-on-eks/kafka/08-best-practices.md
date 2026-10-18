# 第 8 部分：最佳实践

> **审查基线**：Kafka 4.3.1，Strimzi 1.3.0\
> **最近审查日期**：October 16, 2026

本章将前文中的示例转化为需要验证的运维决策。
后续是[基准测试章节](./09-kafka-benchmark.md)；清单不能替代针对实际工作负载和故障的测试。

## 分区设计与测量

对于传统消费者组，同一时间，一个分区最多分配给该组的一个成员。因此，若要让 20 个独立消费的成员都保持繁忙，至少需要 20 个分区。此外，还要测量每个分区的吞吐量、键倾斜、记录大小、复制开销、恢复时间以及 broker/controller 容量。共享组和应用内部并行处理的语义不同；不要把这条规则当作对所有消费者 API 的普遍描述。

分区增多会增加元数据、副本、缓冲区和恢复方面的工作。其成本不符合某个通用的每分区内存/文件描述符公式。历史上的 4,000/200,000 经验法则并非当前普遍适用的限制。应依据测得的稳态和故障行为选择分区数量，包括每个 broker 上的副本分配情况，而不仅仅是逻辑 topic 分区数。

### 统计分区数，而不是 topic 标题行数

`grep -c "PartitionCount"` 统计的是**topic 摘要行**，而不是分区。将以下内容保存为 `partition_summary.py`。它会读取当前 CLI 的分区行（包括 `Leader: none`），并分别报告逻辑分区、副本放置情况和领导权。

```python
import collections
import json
from pathlib import Path
import re
import sys

def summarize(text):
    pattern = re.compile(
        r"^\s*Topic:\s+(\S+)\s+Partition:\s+(\d+)\s+Leader:\s+(none|-?\d+)"
        r"\s+Replicas:[ \t]*([\d,]*)[ \t]+Isr:[ \t]*([\d,]*)"
    )
    partitions = {}
    topics = collections.Counter()
    leaders = collections.Counter()
    replicas = collections.Counter()
    offline = []
    for line in text.splitlines():
        if not re.search(r"\bPartition:", line):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError("Unrecognized partition row; check Kafka CLI version/output.")
        topic, partition, leader, replica_text, _ = match.groups()
        key = (topic, int(partition))
        if key in partitions:
            raise ValueError("Duplicate topic/partition row.")
        replica_ids = [int(x) for x in replica_text.split(",") if x]
        if not replica_ids or len(set(replica_ids)) != len(replica_ids):
            raise ValueError("Missing or duplicate replica IDs.")
        partitions[key] = True
        topics[topic] += 1
        replicas.update(replica_ids)
        if leader == "none" or int(leader) < 0:
            offline.append({"topic": topic, "partition": int(partition)})
        else:
            leaders[int(leader)] += 1
    if not partitions:
        raise ValueError("No partition rows; empty visibility is not proof of a healthy cluster.")
    return {
        "visible_topics": len(topics),
        "logical_partitions": len(partitions),
        "replica_assignments": sum(replicas.values()),
        "partitions_by_topic": dict(sorted(topics.items())),
        "leaders_by_broker": dict(sorted(leaders.items())),
        "replicas_by_broker": dict(sorted(replicas.items())),
        "offline_partitions": offline,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 partition_summary.py topics.txt")
    print(json.dumps(summarize(Path(sys.argv[1]).read_text()), indent=2))
```

```bash
set -euo pipefail
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
# Run from a Kafka 4.3.1 client installation. admin.properties is local to this client.
bin/kafka-topics.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe > topics.txt
python3 partition_summary.py topics.txt
```

结果仅涵盖调用身份可见的 topic，以及命令筛选器返回的 topic（包括返回的内部 topic）。查询失败或结果为空，并不能证明集群没有分区或运行正常。使用适用于此管理读取操作的凭据；不要假定 broker Pod ID 或明文的 `localhost:9092` 监听器。

### 保留键的含义

Java producer 默认的键控映射使用**序列化后的键字节**，并按 `toPositive(murmur2(keyBytes)) % partitionCount` 计算；除非显式指定分区、自定义 partitioner，或使用忽略键的配置改变这一行为。如果映射一致性很重要，其他客户端也必须使用兼容的 partitioner/serializer。

高基数本身并不能保证流量均衡：一个非常活跃的客户仍可能占据主导地位。随机加盐或按时间戳加盐会改变每个键的顺序、连接和压缩身份。只有在数据契约允许这些变化时才使用；如有需要，还应明确制定重新组合/排序策略。

增加分区数可能会重新映射部分键，但不会重新分配旧记录。这可能破坏跨分区的键顺序以及共分区连接的假设。具体要求取决于连接/拓扑；并非所有 Streams 连接都使用相同的共分区方式。对于对顺序敏感或有状态的工作负载，应规划并测试重新分区/迁移，通常需要使用新 topic。

## Producer 调优

将此配置视为经过测量的起始配置，并将其添加到现有的已认证客户端配置中，而不是视为通用的最佳配置。

```properties
acks=all
enable.idempotence=true
max.in.flight.requests.per.connection=5
compression.type=lz4
linger.ms=10
batch.size=32768
delivery.timeout.ms=120000
```

- `acks=all` 会等待当前 ISR。RF=3 且 topic/broker 的 `min.insync.replicas=2` 时，如果 ISR 少于两个，写入会被拒绝，而不是无限期等待第二个副本。只有在剩余副本/仲裁以及其他依赖项仍满足要求时，才能容忍一次故障。
- `enable.idempotence=true` 会抑制受支持的 producer 重试所产生的重复记录。它要求 acks、重试次数和 `max.in.flight.requests.per.connection` 设置彼此兼容。显式设置兼容的属性不会禁用它。
- Kafka 4.3 的默认 linger 为 5 ms；此处的 10 ms 和 32 KiB 是示例调优值。`batch.size` 是每分区的批处理/分配设置，不是记录或请求大小的硬性上限。排队时间和交付期限也会影响延迟。
- 使用具有代表性的数据、CPU 和延迟对比 lz4、zstd、gzip 或不压缩的情况。不要假定某种编解码器的总成本始终最低。

`min.insync.replicas` 属于 topic/broker 配置，而不是 producer 属性。`delivery.timeout.ms` 限制交付尝试的时长；重试次数很高并不意味着交付时间无限。始终监控发送失败。

幂等性不会对任意应用程序重新提交操作或外部数据库副作用进行去重。Kafka 的消费-转换-生产精确一次处理还需要适当的事务生命周期、原子提交输出/输入偏移量、fencing，以及 read-committed 消费者。仅设置 `transactional.id` 字符串并不足够。

## Consumer 处理与成员关系

此配置明确使用 **`group.protocol=classic`**，以便客户端心跳/会话设置生效。使用 `group.protocol=consumer` 时，这些时间间隔由 broker 的消费者组配置控制。

```properties
group.id=order-processor
group.protocol=classic
enable.auto.commit=false
max.poll.records=200
max.poll.interval.ms=600000
session.timeout.ms=45000
heartbeat.interval.ms=15000
```

应限制实际处理时间，而不仅仅是记录数量。处理一条缓慢的记录仍可能超过 `max.poll.interval.ms`。动态成员和静态成员的重新分配时机并不完全相同：静态成员可能在 poll 超时后停止发送心跳，而重新分配会推迟到其会话过期之后。

### 持久处理后再提交

自动提交并不知道异步外部操作何时完成。顺序正确的同步循环可以使用自动提交，但不要以为它能跟踪工作线程池的进度。以下 helper 展示了禁用自动提交后，显式执行“同步处理后再提交”的方法。

```java
import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;

public final class ConsumerExamples {
    public static void setStaticIdentity(Properties props, String instanceId) {
        if (instanceId == null || instanceId.isBlank() || instanceId.contains("${")) {
            throw new IllegalArgumentException("Supply a resolved, stable, unique consumer instance ID.");
        }
        props.setProperty(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
    }

    public static int processOneBatch(
            Consumer<String, String> consumer,
            java.util.function.Consumer<ConsumerRecord<String, String>> processDurably) {
        var records = consumer.poll(Duration.ofMillis(500));
        for (var record : records) {
            processDurably.accept(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();
        }
        return records.count();
    }
}
```

```java
// props already includes bootstrap, TLS/SCRAM, deserializers and the profile below.
try (var consumer = new KafkaConsumer<String, String>(props)) {
    consumer.subscribe(List.of("orders"));
    while (!Thread.currentThread().isInterrupted()) {
        ConsumerExamples.processOneBatch(consumer, application::processDurably);
    }
}
```

`application.processDurably` 是应用代码，只有在所需操作成功后才能返回。处理/提交失败时，应停止并恢复，或显式跳转到正确的位置；**不要捕获错误后继续 poll，越过处理失败的记录**。重启可能会重放已处理的记录，因此外部操作需要合适的幂等/事务策略。使用 KafkaConsumer 支持的 wakeup/close 模式配置关闭流程。

KafkaConsumer 通常不是线程安全的。将工作交给其他线程需要有界队列、分区顺序、在 consumer 线程上执行 pause/resume、跟踪连续完成的偏移量，以及处理重新均衡。仅仅将工作移到线程池并不能提高可靠性。

### 解析稳定的静态成员 ID

Java `Properties` **不会**展开 `group.instance.id=${POD_NAME}`。
在创建 consumer 之前，应在应用程序/配置代码中解析环境变量：

```java
// One consumer instance per stable logical member in this example.
ConsumerExamples.setStaticIdentity(props, System.getenv("KAFKA_GROUP_INSTANCE_ID"));
```

对于每个 StatefulSet Pod 运行一个 consumer 的情况，可以使用来自 `metadata.name` 的 Downward API 值作为稳定的逻辑身份。Deployment 的 Pod 名称在许多发布过程中都会变化；一个 Pod 中的多个 consumer 需要使用不同的 ID。每个活动 consumer 实例都需要唯一 ID，只有由替代实例接替时才应有意复用 ID。活动 ID 重复可能导致成员被 fencing。

对于兼容的短暂重启，静态成员关系可以避免不必要的重新均衡；但它并不保证 Pod 在计时器到期前返回时分配情况一定不变。拓扑、成员关系和订阅也会影响结果，而较长的会话超时时间会延迟真正故障成员的恢复。

## 身份验证、授权与网络

### 区分两种 CA 和监听器属性

使用 Strimzi 管理的默认 CA 时：

- **cluster CA** 为 broker/内部组件证书签名；客户端信任相应的服务器证书链。
- **clients CA** 为用于 mTLS 的 `KafkaUser` 客户端证书签名。
- `user.crt`/`user.key` 是客户端凭据。用户 Secret 中的 clients-CA 证书不能替代 broker 信任链。

监听器的网络暴露类型包括 `type: internal`、`loadbalancer` 等。
加密配置为 `tls: true`，客户端身份验证配置为
`authentication.type: tls`。不存在名为 `tls` 的监听器暴露类型。

以下内容是现有 `spec.kafka.listeners` 数组中的**一个附加监听器条目**，不是 Part 2 中 TLS/SCRAM 监听器的替代项。添加前请检查完整的目标 Kafka 资源：

```yaml
name: mtls
port: 9094
type: internal
tls: true
authentication:
  type: tls
networkPolicyPeers:
- namespaceSelector:
    matchLabels:
      kubernetes.io/metadata.name: kafka-clients
  podSelector:
    matchLabels:
      app: order-service
```

两个选择器位于**同一个 peer** 中，因此 Pod 必须满足 `app=order-service` **并且**位于 `kafka-clients` 命名空间。两个独立的 peer 条目表示 OR 关系：匹配策略所在命名空间中的 Pod，或者所选命名空间中的所有 Pod。NetworkPolicy 的规则是叠加的，需要 CNI 执行策略，而且不能覆盖另一条同样允许流量的策略。还应考虑 egress 以及实际的外部/节点流量路径。

此独立的 mTLS 用户会保留现有 SCRAM 用户的身份：

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: order-service-mtls
  namespace: kafka
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
      operations:
      - Read
      - Write
      - Describe
    - resource:
        type: group
        name: order-processor-mtls
        patternType: literal
      operations:
      - Read
    - resource:
        type: cluster
      operations:
      - IdempotentWrite
```

User Operator 必须对其进行协调，而且必须启用 broker 的 simple authorizer。通过受控的轮换流程，将用户凭据和 broker 信任证书分发到应用程序所在的命名空间；Kubernetes 不能直接挂载另一个命名空间中的 Secret。确认当前 generation、TLS/身份验证成功，以及允许/拒绝的操作。仅提交 YAML 并不会授予可用的访问权限。

现有 SCRAM 路径仍需要 TLS 来加密连接，并需要密码轮换。Kafka ACL 和 NetworkPolicy 互不能替代对方。

### 明确加密新配置的持久存储

对于标准 EBS CSI driver，请使用加密的 StorageClass，和/或账户/Region 级别的 EBS 默认加密设置。此示例还会保留卷，并等待调度后再选择 AZ：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-kafka-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: 'true'
```

对于 Auto Mode，请使用独立的 `ebs.csi.eks.amazonaws.com` provisioner 和 Part 2 中的拓扑约束，同时指定 `encrypted: "true"`。不要根据 Auto Mode 关于节点/临时磁盘加密的说明推断动态 PVC 已加密；其 StorageClass 参数参考中 `encrypted` 的默认值为 false。请确认实际创建的 EBS 卷是否加密，以及使用了哪个 KMS key。

客户管理的密钥需要提供实际 ARN 和相应的角色/密钥授权，而不是 `key/xxxxxxxx`。更改 StorageClass 或启用账户默认设置不会追溯加密现有卷。替换持久存储之前，应规划受支持的数据/快照迁移，并验证恢复访问权限。

## 容量、分层与保留期

Kafka 能从 page cache 中受益，但 CPU（包括 TLS/压缩）、网络、存储吞吐量/IOPS 和 cgroup 内存限制中的任何一项都可能成为主要瓶颈。测量时应将 heap、off-heap、page cache 和其他工作负载都纳入考虑。不存在通用的“4–8 GB heap 就够了”结论，也不存在内存优化型实例在成本上必胜的说法。

Kafka 分层存储自 3.9 起已可用于生产，并受 Strimzi 1.3 支持。它仍然需要兼容的 **RemoteStorageManager 插件**、镜像中包含其依赖项、远程访问凭据/权限，以及保留、清理和恢复配置。Strimzi 的自定义集成通过 `spec.kafka.tieredStorage` 配置插件类/路径/参数。单独启用 `remote.log.storage.system.enable` 并不会将 Kafka 连接到 S3。请阅读相应版本的功能限制，并测试远程存储不可用和恢复的情况。

### 保留期是一项数据决策

以下示例会将现有 topic 的保留期更改为三天或**每个分区 50 GiB**，以先达到的限制为准。删除按 segment 粒度异步进行，并非立即达到精确的字节上限。

```bash
: "${KAFKA_BOOTSTRAP_SERVERS:?Set the reachable TLS bootstrap endpoints}"
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --describe \
  --entity-type topics --entity-name application-logs
# After reviewing retention/recovery requirements: shortening retention can delete data.
bin/kafka-configs.sh --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --command-config admin.properties --alter \
  --entity-type topics --entity-name application-logs \
  --add-config retention.ms=259200000,retention.bytes=53687091200
```

降低保留期可能会不可逆地删除重放或恢复所需的记录。对于 `cleanup.policy=compact`，清理是异步的，并会在 tombstone/cleaner 行为允许的范围内保留每个键的最新值；高键基数以及活动中/尚未清理的 segment 仍可能持续增长。压缩不是硬性的存储上限。`compact,delete` 还会应用删除保留策略，这可能会删除旧键的最后一个值。应明确设计状态重建和 tombstone 保留要求。

### Spot 与中断

在此生产基线中，应让 controller quorum 运行在适当且可靠的容量上。对于能够承受其风险的工作负载，可以考虑使用 Broker Spot 容量，但仅分散 Pod 并不能防止相关联的回收事件。应结合 broker 感知机架的副本放置、节点/AZ 分布、EBS 卷所在 AZ 中的替代容量，以及经过测试的恢复和余量。

Strimzi 1.3 的 PDB 覆盖 Kafka 集群的 Pod，并限制自愿驱逐。它无法保证在强制删除、节点故障、Spot 回收或每一种 Operator 滚动操作期间都能维持 quorum。RF=3/minISR=2、PDB 和 On-Demand controller 都是设计输入，并不能证明不会丢失数据或发生停机。

## 投入生产使用前应保留的证据

- 版本/API 兼容性、升级/回滚以及证书轮换演练。
- 故障条件下测得的分区、副本、CPU/内存/网络/存储限制。
- 经过测试的授权边界、客户端身份以及 Secret/信任证书轮换。
- Schema/历史数据兼容性、处理/提交行为和重复处理。
- 具有实测 RPO/RTO 以及所需 Schema/key 的恢复/故障切换证据。
- 抓取/告警/通知覆盖情况、consumer 容量和应用 SLO。
- 保留策略、存储加密、成本假设以及明确指定的运维负责人。

根据工作负载应用相关控制，并记录仍然存在的限制。完成通用清单不能证明已满足生产就绪要求。

## 参考资料与验证

这些示例通过 Kafka 4.3.1 配置类、实际的键控 partitioner 和 MockConsumer 处理/提交测试，以及已发布的资源 Schema 和 topic 输出样例进行了检查。它们不能替代真实的 TLS/CNI 执行验证、加密卷检查、故障恢复或应用正确性测试。

- [Kafka 4.3 producer 配置](https://kafka.apache.org/43/configuration/producer-configs/)
- [Kafka 4.3 consumer 配置](https://kafka.apache.org/43/configuration/consumer-configs/)
- [Kafka 4.3 分层存储](https://kafka.apache.org/43/operations/tiered-storage/)
- [Kafka 4.3.1 键控 partitioner](https://github.com/apache/kafka/blob/4.3.1/clients/src/main/java/org/apache/kafka/clients/producer/internals/BuiltInPartitioner.java)
- [Kafka 4.3.1 topic 描述输出](https://github.com/apache/kafka/blob/4.3.1/tools/src/main/java/org/apache/kafka/tools/TopicCommand.java)
- [Strimzi 1.3.0 部署、TLS 和分层存储指南](https://strimzi.io/docs/operators/1.3.0/deploying.html)
- [Kubernetes NetworkPolicy 选择器语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [默认启用 EBS 加密](https://docs.aws.amazon.com/ebs/latest/userguide/encryption-by-default.html)
- [EKS Auto Mode StorageClass 参数](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

## 后续步骤

[第 9 部分：Kafka 基准测试](./09-kafka-benchmark.md)

[返回主页](./README.md)

## 测验

[Topic 测验](../../quizzes/data-on-eks/kafka/08-best-practices-quiz.md)
